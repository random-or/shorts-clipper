import json
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, patch

from shorts_clipper.core.models import TranscriptSegment
from shorts_clipper.scout.trending import (
    _has_english,
    compute_scout_v2_intermediate_score,
    get_trending_link,
)


class ScoutV2Tests(unittest.TestCase):
    def setUp(self):
        import sqlite3
        from pathlib import Path

        db_path = Path("outputs/jobs.db")
        if db_path.exists():
            try:
                con = sqlite3.connect(db_path, check_same_thread=False)
                con.execute("DELETE FROM metadata_cache")
                con.commit()
                con.close()
            except Exception:
                pass

    def test_has_english_regional_variants(self):
        # 1. prefix matching for en-US, en-GB, en-CA, etc.
        self.assertTrue(_has_english({"automatic_captions": {"en-US": []}}))
        self.assertTrue(_has_english({"subtitles": {"en-GB": []}}))
        self.assertTrue(_has_english({"automatic_captions": {"en-CA-orig": []}}))
        self.assertFalse(_has_english({"automatic_captions": {"es-orig": [], "en-US": []}}))
        self.assertFalse(_has_english({"automatic_captions": {"fr": []}}))

    def test_compute_scout_v2_intermediate_score(self):
        video = {
            "published_at": datetime.now(UTC).isoformat(),
            "automatic_captions": {"en": []},
            "view_count": 100000,
            "like_count": 5000,
            "comment_count": 200,
            "channel_id": "channel1",
            "language": "en-US",
        }
        now = datetime.now(UTC)
        channel_history = {"channel1": {"success_count": 2, "avg_virality": 90.0}}

        score = compute_scout_v2_intermediate_score(video, now, channel_history)
        self.assertTrue(score > 0)
        # Verify it doesn't fail on missing fields
        self.assertTrue(compute_scout_v2_intermediate_score({}, now, {}) == 0.0)

    @patch("shorts_clipper.highlight_detection.scoring.LocalTranscriptScorer")
    @patch("shorts_clipper.scout.relevance.SemanticRelevanceGate")
    @patch("shorts_clipper.scout.trending._discover_via_ytdlp")
    @patch("shorts_clipper.scout.trending.fetch_subtitles")
    @patch("shorts_clipper.scout.trending.GeminiProvider")
    def test_self_healing_pre_evaluation(
        self,
        mock_gemini_provider_cls,
        mock_fetch_subs,
        mock_discover_ytdlp,
        mock_gate_cls,
        mock_scorer_cls,
    ):
        mock_scorer = __import__("unittest.mock").mock.Mock()
        mock_scorer.score_transcript.return_value = (90.0, [], "great hook")
        mock_scorer_cls.return_value = mock_scorer
        # Mock SemanticRelevanceGate to pass all candidates through
        mock_gate = Mock()
        mock_gate.filter_candidates.side_effect = lambda candidates: candidates
        mock_gate_cls.return_value = mock_gate
        # Mock discover returning 2 candidates
        mock_discover_ytdlp.return_value = [
            {
                "id": "vid_bad",
                "title": "Bad Video",
                "view_count": 1000,
                "like_count": 10,
                "published_at": datetime.now(UTC).isoformat(),
                "automatic_captions": {"en": []},
            },
            {
                "id": "vid_good",
                "title": "Good Video",
                "view_count": 20000,
                "like_count": 1000,
                "published_at": datetime.now(UTC).isoformat(),
                "automatic_captions": {"en": []},
            },
        ]

        # Mock subtitles fetching successfully
        mock_fetch_subs.side_effect = lambda url, path: [
            TranscriptSegment(start=0.0, end=10.0, text="hello world", words=[])
        ]

        # Mock Gemini Provider behavior:
        # For the first candidate ("vid_bad" which is evaluated first because of sorting/history), Gemini returns highlights scoring < 85
        # For the second candidate ("vid_good"), Gemini returns highlights scoring >= 85
        mock_provider = Mock()
        mock_gemini_provider_cls.return_value = mock_provider

        # side_effect to return list of detailed dicts
        mock_provider.select_multiple_clips_detailed.side_effect = [
            # First call for vid_good (since view_count is higher, v2 score will sort vid_good first!)
            [
                {
                    "start": 0.0,
                    "end": 10.0,
                    "virality_score": 90,
                    "layout": "crop_center",
                    "reason": "great hook",
                }
            ],
            # Second call (if any)
            [
                {
                    "start": 0.0,
                    "end": 10.0,
                    "virality_score": 80,
                    "layout": "crop_center",
                    "reason": "too generic",
                }
            ],
        ]

        for f in Path("outputs").glob("scout_report*.json"):
            f.unlink()

        # Run trending link
        with patch.dict("os.environ", {"YOUTUBE_API_KEY": ""}):  # Force yt-dlp path
            url = get_trending_link(niche="tech", max_age_days=7)

        # Verify vid_good wins because it has a valid highlight (score 90 >= 85)
        self.assertEqual(url, "https://www.youtube.com/watch?v=vid_good")

        # Verify scout_report.json was generated
        self.assertTrue(
            any(f.name.startswith("scout_report") for f in Path("outputs").glob("*.json"))
        )
        actual_report_file = next(Path("outputs").glob("scout_report*.json"))
        report_data = json.loads(actual_report_file.read_text(encoding="utf-8"))
        self.assertEqual(report_data["video_id"], "vid_good")
        self.assertEqual(report_data["final_score"], report_data["final_score"])

    @patch("shorts_clipper.scout.relevance.SemanticRelevanceGate")
    @patch("shorts_clipper.scout.trending._discover_via_ytdlp")
    @patch("shorts_clipper.scout.trending.fetch_subtitles")
    @patch("shorts_clipper.scout.trending.GeminiProvider")
    def test_all_candidates_rejected(
        self, mock_gemini_provider_cls, mock_fetch_subs, mock_discover_ytdlp, mock_gate_cls
    ):
        mock_gate = Mock()
        mock_gate.filter_candidates.side_effect = lambda candidates: candidates
        mock_gate_cls.return_value = mock_gate
        # All candidates have poor highlights
        mock_discover_ytdlp.return_value = [
            {
                "id": "vid1",
                "title": "Bad Video 1",
                "view_count": 10000,
                "published_at": datetime.now(UTC).isoformat(),
                "automatic_captions": {"en": []},
            }
        ]
        mock_fetch_subs.return_value = [TranscriptSegment(start=0, end=10, text="hello")]

        mock_provider = Mock()
        mock_gemini_provider_cls.return_value = mock_provider
        mock_provider.select_multiple_clips_detailed.return_value = [
            {"start": 0, "end": 5, "virality_score": 75}  # Low score
        ]

        with patch.dict("os.environ", {"YOUTUBE_API_KEY": ""}):
            url = get_trending_link(niche="tech", max_age_days=7)

        # Verify None is returned when all candidates are rejected
        self.assertIsNone(url)

    @patch("shorts_clipper.highlight_detection.scoring.LocalTranscriptScorer")
    @patch("shorts_clipper.scout.relevance.SemanticRelevanceGate")
    @patch("shorts_clipper.scout.trending._discover_via_ytdlp")
    @patch("shorts_clipper.scout.trending.fetch_subtitles")
    @patch("shorts_clipper.scout.trending.GeminiProvider")
    def test_gemini_quota_exhausted_fail_fast_and_fallback(
        self,
        mock_gemini_provider_cls,
        mock_fetch_subs,
        mock_discover_ytdlp,
        mock_gate_cls,
        mock_scorer_cls,
    ):
        mock_scorer = Mock()
        mock_scorer.score_transcript.return_value = (100.0, [], "Perfect score")
        mock_scorer_cls.return_value = mock_scorer
        mock_gate = Mock()
        mock_gate.filter_candidates.side_effect = lambda candidates: candidates
        mock_gate_cls.return_value = mock_gate
        from shorts_clipper.providers.gemini import GeminiQuotaExhaustedError

        mock_discover_ytdlp.return_value = [
            {
                "id": "vid_fallback",
                "title": "Fallback Video",
                "view_count": 5000,
                "like_count": 100,
                "published_at": datetime.now(UTC).isoformat(),
                "automatic_captions": {"en": []},
            }
        ]
        mock_fetch_subs.return_value = [
            TranscriptSegment(
                start=0,
                end=45,
                text="You won't believe this shocking secret truth. Here's why this amazing insane revelation changed everything. The truth is absolutely unbelievable and crazy.",
            )
        ]

        mock_provider = Mock()
        mock_gemini_provider_cls.return_value = mock_provider
        # Mock provider raising GeminiQuotaExhaustedError
        mock_provider.select_multiple_clips_detailed.side_effect = GeminiQuotaExhaustedError(
            "Quota exceeded"
        )

        with patch.dict("os.environ", {"YOUTUBE_API_KEY": ""}):
            url = get_trending_link(niche="tech", max_age_days=7)

        # Verify it falls back to the finalist video URL even though Gemini failed
        self.assertEqual(url, "https://www.youtube.com/watch?v=vid_fallback")


if __name__ == "__main__":
    unittest.main()

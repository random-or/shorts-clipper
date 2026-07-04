import json
import unittest
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from shorts_clipper.core.settings import Settings
from shorts_clipper.pipeline.runner import run


@dataclass
class MockSegment:
    start: float
    end: float
    text: str
    words: list = None


class FallbackMetadataTests(unittest.TestCase):
    @patch("shorts_clipper.pipeline.runner.download_clip")
    @patch("shorts_clipper.pipeline.runner.process_to_vertical")
    @patch("shorts_clipper.pipeline.runner.burn_subtitles")
    @patch("shorts_clipper.pipeline.runner.transcribe_clip")
    @patch("shorts_clipper.pipeline.runner.PublishingEngine")
    @patch("shorts_clipper.pipeline.runner.GeminiProvider")
    @patch("shorts_clipper.core.cache.get_cached")
    @patch("shorts_clipper.pipeline.runner.fetch_subtitles")
    def test_gemini_fallback_success(
        self,
        mock_fetch_subs,
        mock_get_cached,
        mock_gemini_cls,
        mock_engine_cls,
        mock_transcribe,
        mock_burn,
        mock_process,
        mock_download,
    ):
        # Setup mock cache
        mock_get_cached.return_value = {
            "title": "A Great Source Video",
            "channel_title": "Source Channel",
        }

        # Setup mock transcript
        segments = [
            MockSegment(0, 5, "What an incredible day to test things!"),
            MockSegment(5, 10, "I couldn't believe it when the money failed."),
            MockSegment(10, 15, "Stop doing this wrong right now."),
        ]
        mock_transcribe.return_value = segments

        # Scenario 1: Gemini Provider throws Exception (429 or Timeout) during Metadata
        mock_provider = MagicMock()
        from shorts_clipper.core.models import ClipWindow

        # For Pass 2 metadata generation
        mock_provider.generate_clip_metadata.side_effect = Exception("429 RESOURCE_EXHAUSTED")
        mock_gemini_cls.return_value = mock_provider

        settings = Settings.from_env()

        # Mock upload success
        from shorts_clipper.publishers.models import PublishResult

        mock_engine = mock_engine_cls.return_value
        mock_engine.publish.return_value = {
            "youtube": PublishResult(
                "youtube",
                True,
                "https://youtube.com/shorts/fake_yt_id",
                "fake_yt_id",
                "2026-06-27T00:00:00Z",
            )
        }

        # Run pipeline
        with patch.dict("os.environ", {"YOUTUBE_API_KEY": "fake"}):
            with patch("shorts_clipper.highlight_detection.scoring.LocalTranscriptScorer") as mock_scorer_cls:
                mock_scorer = MagicMock()
                mock_scorer.score_transcript.return_value = (90.0, [MockSegment(0, 15, "test")], "reason")
                mock_scorer_cls.return_value = mock_scorer
                
                with patch("shorts_clipper.attention.engine.SimulationEngine") as mock_sim_cls:
                    mock_sim = MagicMock()
                    mock_sim.optimize_clip.return_value = MagicMock(
                        winner_id="base",
                        base_variant=MagicMock(start_time=0.0, end_time=15.0),
                        variants=[MagicMock(variant_id="base", start_time=0.0, end_time=15.0)]
                    )
                    mock_sim_cls.return_value = mock_sim

                    output = run(
                        url="https://www.youtube.com/watch?v=fallback123",
                        settings=settings,
                    count=1,
                    upload=True,
                )

        # Verify Fallback was used
        json_path = output.with_suffix(".json")
        self.assertTrue(json_path.exists())

        with open(json_path, encoding="utf-8") as f:
            meta = json.load(f)

        self.assertIsNotNone(meta["title"])
        self.assertIsNotNone(meta["description"])
        self.assertTrue(len(meta["tags"]) > 0)
        self.assertEqual(meta["publish_status"], "partial_success")
        self.assertEqual(meta["publish_results"]["youtube"]["platform_id"], "fake_yt_id")

        print("Generated Title:", meta["title"])
        print("Generated Description:", meta["description"])
        print("Generated Tags:", meta["tags"])


if __name__ == "__main__":
    unittest.main()

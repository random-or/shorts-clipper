"""Tests for the new package modules added in session 2."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shorts_clipper.captions.generator import (
    _ass_header,
    _build_ass_chunks,
    _seconds_to_ass_time,
)
from shorts_clipper.core.models import TranscriptSegment, TranscriptWord
from shorts_clipper.scout.trending import (
    _has_english,
    _is_suitable,
    _load_cache,
    _save_cache,
)


class ASSTimestampTests(unittest.TestCase):
    def test_zero_seconds(self):
        self.assertEqual(_seconds_to_ass_time(0.0), "0:00:00.00")

    def test_one_minute_thirty(self):
        self.assertEqual(_seconds_to_ass_time(90.5), "0:01:30.50")

    def test_over_one_hour(self):
        self.assertEqual(_seconds_to_ass_time(3661.25), "1:01:01.25")


class ASSHeaderTests(unittest.TestCase):
    def test_header_contains_required_sections(self):
        header = _ass_header()
        self.assertIn("[Script Info]", header)
        self.assertIn("[V4+ Styles]", header)
        self.assertIn("[Events]", header)
        self.assertIn("PlayResX: 1080", header)
        self.assertIn("PlayResY: 1920", header)

    def test_header_is_string(self):
        self.assertIsInstance(_ass_header(), str)


class ASSChunkTests(unittest.TestCase):
    def _make_segment(self, start, end, text, words=None):
        w = []
        if words:
            for ws, we, wt in words:
                w.append(TranscriptWord(start=ws, end=we, word=wt))
        return TranscriptSegment(start=start, end=end, text=text, words=w)

    def test_word_level_chunks_use_actual_timing(self):
        seg = self._make_segment(
            10.0,
            14.0,
            "this is great",
            words=[(10.0, 10.5, "this"), (10.6, 11.0, "is"), (11.1, 11.8, "great")],
        )
        chunks = _build_ass_chunks([seg], start_offset=10.0)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["text"], "THIS IS GREAT")
        self.assertAlmostEqual(chunks[0]["start"], 0.0)

    def test_fallback_chunks_distribute_time_evenly(self):
        seg = self._make_segment(0.0, 6.0, "one two three four five six")
        chunks = _build_ass_chunks([seg], start_offset=0.0)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["text"], "ONE TWO THREE")
        self.assertAlmostEqual(chunks[0]["start"], 0.0)
        self.assertAlmostEqual(chunks[0]["end"], 3.0)
        self.assertEqual(chunks[1]["text"], "FOUR FIVE SIX")
        self.assertAlmostEqual(chunks[1]["start"], 3.0)
        self.assertAlmostEqual(chunks[1]["end"], 6.0)

    def test_empty_segment_produces_no_chunks(self):
        seg = self._make_segment(0.0, 1.0, "")
        chunks = _build_ass_chunks([seg], start_offset=0.0)
        self.assertEqual(chunks, [])

    def test_pacing_scales_timing(self):
        seg = self._make_segment(
            10.0,
            14.0,
            "this is great",
            words=[(10.0, 11.15, "this"), (11.15, 12.3, "is"), (12.3, 13.45, "great")],
        )
        chunks = _build_ass_chunks([seg], start_offset=10.0, pacing=1.15)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["text"], "THIS IS GREAT")
        self.assertAlmostEqual(chunks[0]["start"], 0.0)
        self.assertAlmostEqual(chunks[0]["end"], 3.0)

        # Fallback path pacing test
        seg_fallback = self._make_segment(10.0, 15.75, "hello world")
        chunks_fb = _build_ass_chunks([seg_fallback], start_offset=10.0, pacing=1.15)
        self.assertEqual(len(chunks_fb), 1)
        self.assertEqual(chunks_fb[0]["text"], "HELLO WORLD")
        self.assertAlmostEqual(chunks_fb[0]["end"], 5.0)


class ScoutCacheTests(unittest.TestCase):
    def test_cache_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "cache.json"
            with patch("shorts_clipper.scout.trending._CACHE_FILE", cache_path):
                import time

                now = time.time()
                seen = {"abc123": now, "def456": now}
                _save_cache(seen)
                loaded = _load_cache()
            self.assertEqual(loaded, seen)

    def test_load_cache_returns_empty_set_if_missing(self):
        with patch(
            "shorts_clipper.scout.trending._CACHE_FILE",
            Path("/nonexistent/path/cache.json"),
        ):
            result = _load_cache()
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 0)


class ScoutFilterTests(unittest.TestCase):
    def _make_info(self, duration=300, en_subs=True, vid_id="abc123"):
        info = {"id": vid_id, "duration": duration}
        if en_subs:
            info["automatic_captions"] = {"en": []}
        else:
            info["automatic_captions"] = {}
            info["subtitles"] = {}
        return info

    def test_has_english_detects_auto_captions(self):
        self.assertTrue(_has_english({"automatic_captions": {"en": []}}))
        self.assertTrue(_has_english({"subtitles": {"en-orig": []}}))
        self.assertFalse(_has_english({"automatic_captions": {"fr": []}, "subtitles": {}}))

    def test_has_english_rejects_non_english_language_field(self):
        self.assertFalse(_has_english({"language": "hi", "automatic_captions": {"en": []}}))
        self.assertFalse(_has_english({"language": "es", "subtitles": {"en": []}}))
        self.assertTrue(_has_english({"language": "en-US", "automatic_captions": {"en": []}}))

    def test_has_english_rejects_non_english_orig(self):
        self.assertFalse(_has_english({"automatic_captions": {"es-orig": [], "en": []}}))
        self.assertFalse(_has_english({"automatic_captions": {"hi-orig": [], "en": []}}))
        self.assertTrue(_has_english({"automatic_captions": {"en-orig": [], "en": []}}))

    def test_is_suitable_rejects_seen_ids(self):
        info = self._make_info()
        self.assertFalse(_is_suitable(info, seen={"abc123": 1.0}))

    def test_is_suitable_rejects_short_videos(self):
        info = self._make_info(duration=60)
        self.assertFalse(_is_suitable(info, seen={}))

    def test_is_suitable_rejects_very_long_videos(self):
        info = self._make_info(duration=7200)
        self.assertFalse(_is_suitable(info, seen={}))

    def test_is_suitable_rejects_no_english(self):
        info = self._make_info(en_subs=False)
        self.assertFalse(_is_suitable(info, seen={}))

    def test_is_suitable_passes_valid_video(self):
        info = self._make_info(duration=300, en_subs=True, vid_id="xyz789")
        self.assertTrue(_is_suitable(info, seen={}))


class DownloaderTests(unittest.TestCase):
    @patch("shorts_clipper.downloader.yt_dlp.subprocess.run")
    def test_download_audio_full(self, mock_run):
        from shorts_clipper.downloader.yt_dlp import download_audio

        url = "https://www.youtube.com/watch?v=test"
        output_path = "/tmp/test_audio.m4a"
        download_audio(url, output_path)

        # Check command structure
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn("yt-dlp", args)
        self.assertIn("--extract-audio", args)
        self.assertIn("--audio-format", args)
        self.assertIn("m4a", args)
        self.assertIn(output_path, args)
        self.assertIn(url, args)
        self.assertNotIn("--download-sections", args)

    @patch("shorts_clipper.downloader.yt_dlp.subprocess.run")
    def test_download_audio_section(self, mock_run):
        from shorts_clipper.downloader.yt_dlp import download_audio

        url = "https://www.youtube.com/watch?v=test"
        output_path = "/tmp/test_audio.m4a"
        download_audio(url, output_path, start_time=10.0, end_time=120.0)

        # Check command structure
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn("yt-dlp", args)
        self.assertIn("--extract-audio", args)
        self.assertIn("--audio-format", args)
        self.assertIn("m4a", args)
        self.assertIn(output_path, args)
        self.assertIn(url, args)
        self.assertIn("--download-sections", args)
        self.assertIn("*10.0-120.0", args)


class ScoutQueryTests(unittest.TestCase):
    @patch("shorts_clipper.scout.trending._scout_pool")
    def test_scout_by_channel(self, mock_scout_pool):
        from shorts_clipper.scout.trending import get_trending_link

        mock_scout_pool.return_value = []

        # Test with a handle
        get_trending_link(channel="@MrBeast", cache=False, max_retries=1)
        mock_scout_pool.assert_called_with("https://www.youtube.com/@MrBeast/videos", {}, 30)

        # Test with a handle string without @
        get_trending_link(channel="MrBeast", cache=False, max_retries=1)
        mock_scout_pool.assert_called_with("https://www.youtube.com/@MrBeast/videos", {}, 30)

        # Test with full URL
        get_trending_link(
            channel="https://www.youtube.com/c/MrBeast/videos",
            cache=False,
            max_retries=1,
        )
        mock_scout_pool.assert_called_with("https://www.youtube.com/c/MrBeast/videos", {}, 30)

    def test_is_suitable_enforces_max_age_days(self):
        from datetime import datetime, timedelta

        from shorts_clipper.scout.trending import _is_suitable

        # Mock video uploaded 10 days ago (suitable under 30 days)
        date_10_days_ago = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d")
        info_new = {
            "id": "vid123",
            "duration": 300,
            "upload_date": date_10_days_ago,
            "automatic_captions": {"en": []},
        }
        self.assertTrue(_is_suitable(info_new, {}, max_age_days=30))

        # Mock video uploaded 40 days ago (unsuitable under 30 days)
        date_40_days_ago = (datetime.now() - timedelta(days=40)).strftime("%Y%m%d")
        info_old = {
            "id": "vid456",
            "duration": 300,
            "upload_date": date_40_days_ago,
            "automatic_captions": {"en": []},
        }
        self.assertFalse(_is_suitable(info_old, {}, max_age_days=30))

    @patch("shorts_clipper.scout.trending._get_current_trending_keywords")
    @patch("shorts_clipper.scout.trending._scout_pool")
    def test_scout_by_niche_rotation(self, mock_scout_pool, mock_get_kws):
        from datetime import datetime

        from shorts_clipper.scout.trending import get_trending_link

        mock_scout_pool.return_value = []
        mock_get_kws.return_value = ["podcast", "drama"]

        now = datetime.now()
        day_str = now.strftime("%A")
        week_str = f"week {now.isocalendar()[1]}"

        # Call first time
        get_trending_link(niche="cooking", cache=False, max_retries=1)
        first_call_queries = [call.args[0] for call in mock_scout_pool.call_args_list]
        expected = f"ytsearch5:viral cooking podcast english {day_str} today"
        self.assertIn(expected, first_call_queries)

        mock_scout_pool.reset_mock()
        # Call second time to ensure rotation index changed
        get_trending_link(niche="cooking", cache=False, max_retries=1)
        second_call_queries = [call.args[0] for call in mock_scout_pool.call_args_list]
        expected = f"ytsearch5:best cooking podcast highlights english this week {week_str}"
        self.assertIn(expected, second_call_queries)

    @patch("shorts_clipper.scout.trending._scout_pool")
    def test_scout_by_keyword_multi_platform(self, mock_scout_pool):
        from shorts_clipper.scout.trending import get_trending_link

        mock_scout_pool.return_value = []

        get_trending_link(keyword="clash", cache=False, max_retries=1)
        queries = [call.args[0] for call in mock_scout_pool.call_args_list]

        self.assertIn("ytsearch5:clash", queries)
        self.assertIn("scsearch5:clash", queries)
        self.assertIn("gvsearch5:clash", queries)
        self.assertIn("yvsearch5:clash", queries)

    def test_is_suitable_rejects_low_resolution(self):
        from shorts_clipper.scout.trending import _is_suitable

        # Video with low resolution (480p) should be rejected
        info_low = {
            "id": "vid_low",
            "duration": 300,
            "upload_date": "20260520",
            "automatic_captions": {"en": []},
            "height": 480,
        }
        self.assertFalse(_is_suitable(info_low, {}))

        # Video with high resolution (1080p) should be accepted
        info_high = {
            "id": "vid_high",
            "duration": 300,
            "upload_date": "20260520",
            "automatic_captions": {"en": []},
            "height": 1080,
        }
        self.assertTrue(_is_suitable(info_high, {}))


if __name__ == "__main__":
    unittest.main()

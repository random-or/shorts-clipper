"""Tests for the new package modules added in session 2."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

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
            10.0, 14.0, "this is great",
            words=[(10.0, 10.5, "this"), (10.6, 11.0, "is"), (11.1, 11.8, "great")],
        )
        chunks = _build_ass_chunks([seg], start_offset=10.0, words_per_chunk=2)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["text"], "THIS IS")
        self.assertAlmostEqual(chunks[0]["start"], 0.0)

    def test_fallback_chunks_distribute_time_evenly(self):
        seg = self._make_segment(0.0, 6.0, "one two three four five six")
        chunks = _build_ass_chunks([seg], start_offset=0.0, words_per_chunk=2)
        self.assertEqual(len(chunks), 3)
        # Each chunk should span 2 seconds
        for chunk in chunks:
            self.assertAlmostEqual(chunk["end"] - chunk["start"], 2.0, places=5)

    def test_empty_segment_produces_no_chunks(self):
        seg = self._make_segment(0.0, 1.0, "")
        chunks = _build_ass_chunks([seg], start_offset=0.0)
        self.assertEqual(chunks, [])


class ScoutCacheTests(unittest.TestCase):
    def test_cache_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "cache.json"
            with patch("shorts_clipper.scout.trending._CACHE_FILE", cache_path):
                seen = {"abc123", "def456"}
                _save_cache(seen)
                loaded = _load_cache()
            self.assertEqual(loaded, seen)

    def test_load_cache_returns_empty_set_if_missing(self):
        with patch(
            "shorts_clipper.scout.trending._CACHE_FILE",
            Path("/nonexistent/path/cache.json"),
        ):
            result = _load_cache()
        self.assertIsInstance(result, set)
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

    def test_is_suitable_rejects_seen_ids(self):
        info = self._make_info()
        self.assertFalse(_is_suitable(info, seen={"abc123"}))

    def test_is_suitable_rejects_short_videos(self):
        info = self._make_info(duration=60)
        self.assertFalse(_is_suitable(info, seen=set()))

    def test_is_suitable_rejects_very_long_videos(self):
        info = self._make_info(duration=7200)
        self.assertFalse(_is_suitable(info, seen=set()))

    def test_is_suitable_rejects_no_english(self):
        info = self._make_info(en_subs=False)
        self.assertFalse(_is_suitable(info, seen=set()))

    def test_is_suitable_passes_valid_video(self):
        info = self._make_info(duration=300, en_subs=True, vid_id="xyz789")
        self.assertTrue(_is_suitable(info, seen=set()))


if __name__ == "__main__":
    unittest.main()

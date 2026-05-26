import os
import tempfile
import unittest
from pathlib import Path

from shorts_clipper.core.settings import Settings
from shorts_clipper.core.models import ClipWindow, TranscriptSegment, TranscriptWord
from shorts_clipper.highlight_detection.scoring import RuleBasedHighlightScorer
from shorts_clipper.providers.base import parse_clip_window
from shorts_clipper.transcription.formatting import format_transcript


class SettingsTests(unittest.TestCase):
    def test_loads_env_file_without_overwriting_existing_environment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "GEMINI_API_KEY=from_file\n"
                "SHORTS_WHISPER_MODEL=base.en\n"
                "SHORTS_OUTPUT_DIR=custom_output\n",
                encoding="utf-8",
            )
            old_key = os.environ.get("GEMINI_API_KEY")
            os.environ["GEMINI_API_KEY"] = "from_env"
            try:
                settings = Settings.from_env(env_path=env_path)
            finally:
                if old_key is None:
                    os.environ.pop("GEMINI_API_KEY", None)
                else:
                    os.environ["GEMINI_API_KEY"] = old_key

            self.assertEqual(settings.gemini_api_key, "from_env")
            self.assertEqual(settings.whisper_model, "base.en")
            self.assertEqual(settings.output_dir, Path("custom_output"))


class TranscriptFormattingTests(unittest.TestCase):
    def test_formats_segments_for_llm_prompt(self):
        segments = [
            TranscriptSegment(start=1.234, end=2.5, text="hello world"),
            TranscriptSegment(start=3, end=4.125, text="next line"),
        ]

        self.assertEqual(
            format_transcript(segments),
            "[1.23s -> 2.50s]: hello world\n[3.00s -> 4.12s]: next line",
        )


class ProviderParsingTests(unittest.TestCase):
    def test_parses_first_two_timestamps_from_provider_response(self):
        window = parse_clip_window("Best clip: 41.62, 75.20", min_start=0, max_end=120)

        self.assertEqual(window, ClipWindow(start=41.62, end=75.2))

    def test_rejects_out_of_bounds_or_reversed_timestamps(self):
        with self.assertRaises(ValueError):
            parse_clip_window("90,30", min_start=0, max_end=120)
        with self.assertRaises(ValueError):
            parse_clip_window("5,200", min_start=0, max_end=120)


class HighlightScoringTests(unittest.TestCase):
    def test_scores_hooks_emotion_and_caption_density(self):
        exciting = TranscriptSegment(
            start=0,
            end=8,
            text="You will not believe this secret trick! This changed everything!",
            words=[
                TranscriptWord(start=0, end=0.5, word="You"),
                TranscriptWord(start=0.6, end=1.0, word="will"),
                TranscriptWord(start=1.1, end=1.6, word="not"),
                TranscriptWord(start=1.7, end=2.1, word="believe"),
            ],
        )
        dull = TranscriptSegment(start=9, end=18, text="and then we continued with the next part")

        scorer = RuleBasedHighlightScorer()
        exciting_score = scorer.score_segment(exciting)
        dull_score = scorer.score_segment(dull)

        self.assertGreater(exciting_score.total, dull_score.total)
        self.assertGreater(exciting_score.hook, 0)
        self.assertGreater(exciting_score.emotion, 0)
        self.assertGreater(exciting_score.caption_density, 0)


if __name__ == "__main__":
    unittest.main()

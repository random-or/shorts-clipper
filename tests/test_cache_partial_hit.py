from unittest import mock

from shorts_clipper.core.models import ClipWindow
from shorts_clipper.core.settings import Settings
from shorts_clipper.pipeline.runner import run


@mock.patch("shorts_clipper.core.cache.get_cached")
@mock.patch("shorts_clipper.pipeline.runner.fetch_subtitles")
@mock.patch("shorts_clipper.pipeline.runner.GeminiProvider")
@mock.patch("shorts_clipper.pipeline.runner.download_audio")
@mock.patch("shorts_clipper.pipeline.runner.transcribe_clip")
@mock.patch("shorts_clipper.pipeline.runner.download_clip")
@mock.patch("shorts_clipper.pipeline.runner.process_to_vertical")
@mock.patch("shorts_clipper.pipeline.runner.burn_subtitles")
def test_cache_partial_hit_behavior(
    mock_burn,
    mock_process,
    mock_download_clip,
    mock_transcribe,
    mock_download_audio,
    mock_provider_cls,
    mock_fetch_subs,
    mock_get_cached,
    tmp_path,
):
    settings = Settings(gemini_api_key="dummy", youtube_api_key="dummy")

    mock_get_cached.return_value = {
        "selected_clips": [
            {"start": 10.0, "end": 20.0, "layout": "crop_center"},
            {"start": 30.0, "end": 40.0, "layout": "split_screen"},
        ]
    }

    mock_fetch_subs.return_value = [{"start": 0.0, "end": 100.0, "text": "Dummy text"}]

    mock_provider_instance = mock.Mock()
    mock_provider_instance.select_multiple_clips.return_value = [
        (ClipWindow(start=50.0, end=60.0), "crop_center")
    ]
    mock_provider_cls.return_value = mock_provider_instance

    mock_transcribe.return_value = []

    mock_process.return_value = tmp_path / "cropped.mp4"
    mock_burn.return_value = tmp_path / "final.mp4"

    # Run the pipeline with count=3
    # With the bug present, this will ignore the cache completely and request 3 clips from Gemini
    # Once fixed, it will use 2 from cache, and request 1 from Gemini
    with mock.patch("shorts_clipper.pipeline.runner.EditorialFinisher") as MockFinisher:
        mock_finisher_inst = MockFinisher.return_value
        mock_finisher_inst.snap_boundaries.side_effect = lambda *args, **kwargs: ClipWindow(
            start=args[0], end=args[1]
        )

        result = run("https://youtube.com/watch?v=dummy", settings=settings, count=3, upload=False)

        assert len(result) == 3

        # Verify provider was called with count=1 (partial hit behavior)
        mock_provider_instance.select_multiple_clips.assert_called_once()
        _, kwargs = mock_provider_instance.select_multiple_clips.call_args
        assert kwargs.get("count") == 1

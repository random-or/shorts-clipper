# Production Roadmap

## Current repository snapshot

The tracked project is intentionally small: six Python modules plus `.gitignore`.

- `pipeline.py` orchestrates download, transcription, Gemini highlight selection, crop/render, subtitle burn-in, and cleanup.
- `transcribe.py` downloads audio with `yt-dlp` and transcribes with `faster-whisper`.
- `analyzer.py` sends a transcript prompt to Gemini and expects `start,end` text back.
- `editor.py` downloads source video and renders a centered 9:16 crop with MoviePy.
- `subtitles.py` burns 2-3 word uppercase captions with MoviePy `TextClip`.
- `scout.py` finds a fallback/trending YouTube URL with `yt-dlp`.

There are no tracked tests, dependency metadata, README, package structure, settings layer, API, Docker, CI, or typed domain models yet. Runtime artifacts and a local virtualenv/model cache exist but are ignored by git.

## Technical debt

1. Flat script architecture couples orchestration, I/O, AI calls, rendering, and CLI behavior.
2. No typed domain models for transcripts, words, clips, render settings, provider results, or job state.
3. No tests; changes to timestamp parsing, transcript formatting, crop math, and subtitle grouping can silently regress.
4. Configuration is hard-coded or read directly from `os.environ`; no `.env` loading or validated settings object.
5. Provider lock-in: highlight detection is coupled to Google GenAI and a fragile raw string response.
6. Broad exception handling hides provider failures and falls back to hard-coded timestamps.
7. MoviePy rendering loads full clips into Python and re-encodes multiple times.
8. Temporary filenames are global (`temp_audio.mp3`, `raw_video.mp4`, `output_short.mp4`) and unsafe for concurrent/batch jobs.
9. Console UX is print-based; no structured logging, progress model, dry-run, JSON export, resume, or batch orchestration.
10. API/web/devops surfaces are absent.

## Bottlenecks and reliability risks

1. Rendering pipeline: video is downloaded after audio, then rendered once for crop and again for subtitles. This doubles encode time and quality loss.
2. MoviePy: convenient but RAM-heavy for large media and slower than direct ffmpeg filter graphs.
3. Transcription: no transcript cache keyed by source URL/media hash/settings, so every run redoes Whisper work.
4. Highlight selection: one LLM response controls the clip; no deterministic fallback scorer, validation, or multi-candidate ranking.
5. Cropping: centered crop misses speakers/faces and does not support multi-person framing or smooth movement.
6. Subtitles: `TextClip` can fail due to font/ImageMagick environment and currently just skips failed phrases.
7. Temporary file handling: fixed names cause collisions, failed resume, and accidental deletion in concurrent runs.
8. API credentials: missing keys cause late pipeline exits rather than early settings validation.

## Prioritized improvement roadmap

### Phase 1: Safe foundations

- Add a package skeleton without deleting existing scripts, preserving backward compatibility.
- Add typed dataclasses for transcript words/segments, clip windows, scores, and settings.
- Add settings loader with `.env` support using only the standard library initially.
- Add structured logging helper.
- Add deterministic transcript formatting, timestamp parsing, and highlight scoring helpers.
- Add unit tests for pure logic.

### Phase 2: Modular pipeline [IN PROGRESS]

- Move orchestration into `shorts_clipper.pipeline` services.
- Replace global temp filenames with per-job work directories. [DONE]
- Add a job manifest so interrupted jobs can resume.
- Make existing top-level scripts thin compatibility wrappers. [DONE]
- Add dry-run and JSON export modes.

### Phase 3: Performance/rendering [IN PROGRESS]

- Introduce an ffmpeg command builder that uses argument lists, not shell strings. [DONE]
- Combine trim, crop, scale, captions, and audio into a single ffmpeg pass where possible. [DONE]
- Add hardware encoder selection (`h264_nvenc`, `h264_vaapi`, `h264_videotoolbox`, fallback `libx264`).
- Add multiprocessing for multiple candidate renders or batch URLs.
- Cache transcripts and scene metadata by source fingerprint.

### Phase 4: AI quality

- Implement provider interface with Gemini, OpenAI-compatible, Claude-compatible, and Ollama adapters.
- Generate multiple candidate clip windows and score them with hook, emotion, silence, retention, topic, speaker emphasis, caption density, and virality features.
- Validate LLM output against transcript boundaries and deterministic scoring.
- Add title, hook intro, hashtags, thumbnail frame suggestion, and platform export metadata.

### Phase 5: Video quality

- Add face/person detection abstraction with optional OpenCV/MediaPipe extras.
- Implement dynamic smart crop tracks with smoothing and active-speaker zoom.
- Add subtitle style templates and TikTok/Reels presets.
- Add multi-person framing and safe subtitle placement zones.

### Phase 6: UX/API/DevOps

- Add a modern CLI with progress bars and batch mode.
- Add FastAPI backend with REST jobs, WebSocket progress, and OpenAPI docs.
- Add optional lightweight dashboard.
- Add Docker, docker-compose, pre-commit, lint/format config, GitHub Actions, unit/integration tests.
- Rewrite README with architecture, examples, API docs, benchmarks, screenshots, and roadmap.

## First implementation slice

The first slice should not rewrite the working scripts. It should add safe foundations that future refactors can use immediately:

1. Package skeleton under `shorts_clipper/` with modules matching the requested domains.
2. Standard-library dataclass models and settings.
3. Provider-agnostic timestamp parsing and deterministic highlight scoring.
4. Unit tests using `unittest` so the project does not need a new test dependency yet.
5. A small compatibility improvement in `analyzer.py` to parse/validate Gemini timestamps through the new helper while preserving its public function.

# Shorts Clipper

Open-source AI shorts generation toolkit in active refactor toward a modular, production-quality clipping system.

The current CLI pipeline still works through the existing scripts while new production modules are introduced incrementally under `shorts_clipper/`.

## Current pipeline

1. Download audio with `yt-dlp`.
2. Transcribe locally with `faster-whisper`.
3. Ask Gemini for a high-value clip window.
4. Download the source video.
5. Crop/render a 9:16 short.
6. Burn captions into the final video.

## Architecture direction

```text
shorts_clipper/
  core/                 settings, dataclasses, exceptions, logging
  pipeline/             orchestration and resumable jobs
  transcription/        Whisper adapters, transcript cache, formatting
  highlight_detection/  deterministic scoring and candidate ranking
  rendering/            ffmpeg/MoviePy render backends
  captions/             subtitle grouping and style presets
  cropping/             smart crop and face/person framing
  providers/            Gemini/OpenAI/Ollama/Claude-compatible adapters
  api/                  FastAPI backend
  ui/                   CLI and optional dashboard
  utils/                shared utilities
```

See `docs/ROADMAP.md` for the prioritized production roadmap, technical debt, and bottleneck analysis.

## Install

```bash
python -m venv env
source env/bin/activate
pip install -e .
```

You also need `ffmpeg` and `yt-dlp` available on PATH. Some caption rendering paths may require fonts installed locally.

## Configuration

Environment variables are read directly and can also be placed in `.env`:

```env
GEMINI_API_KEY=your-key
SHORTS_WHISPER_MODEL=tiny.en
SHORTS_WHISPER_DEVICE=cpu
SHORTS_WHISPER_COMPUTE_TYPE=int8
SHORTS_OUTPUT_DIR=outputs
SHORTS_CACHE_DIR=.cache/shorts-clipper
```

Existing environment variables win over `.env` values.

## Usage

Run against an explicit URL:

```bash
python pipeline.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

Run without a URL to use the current scout fallback/trending behavior:

```bash
python pipeline.py
```

## Tests

The foundation tests use only the Python standard library:

```bash
python -m unittest discover -v
```

## Roadmap

High-priority next steps:

- Move top-level scripts into package modules while keeping compatibility wrappers.
- Add per-job work directories and resumable manifests.
- Replace double MoviePy rendering with a single ffmpeg filter graph.
- Add transcript and scene-analysis caches.
- Add provider abstractions and multi-candidate highlight scoring.
- Add FastAPI, WebSocket progress, Docker, CI, linting, and integration tests.

<div align="center">

# Shorts Clipper

### Open-source AI video clipping for YouTube Shorts, TikTok, and Instagram Reels

Turn long-form video into vertical, captioned, high-retention short clips with local transcription, AI-assisted highlight detection, and a production-ready **single-pass ffmpeg render engine**.

[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Tests](https://github.com/random-or/shorts-clipper/actions/workflows/ci.yml/badge.svg)](https://github.com/random-or/shorts-clipper/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-production%20ready-green.svg)](#roadmap)

</div>

---

## ⚡ Why it's Sexy (Features)

Shorts Clipper is built for speed, quality, and concurrency:

- **Single-Pass Rendering:** Trims, crops, scales, and burns subtitles in ONE ffmpeg pass. No double-encoding quality loss.
- **Isolated Workflows:** Uses unique temporary work directories for every job. Safe for batch processing and concurrent runs.
- **Local Transcription:** Powered by `faster-whisper` for fast, private, word-level timestamps.
- **AI Highlight Detection:** Uses Gemini 2.0 Flash to find the most viral segments with smart fallbacks.
- **Robustness:** Validates video metadata and handles edge cases (like videos without speech) with deterministic fallbacks.
- **Clean Architecture:** Modular Python package with typed domain models and unit tests.

---

## 🚀 Quick Start

### 1. Requirements

You need `ffmpeg` (with `libass` for subtitles) and `yt-dlp` installed on your system.

### 2. Install

```bash
python -m venv env
source env/bin/activate
pip install -e .
```

### 3. Configure

```bash
cp .env.example .env
# Add your GEMINI_API_KEY to .env
```

### 4. Run the Pipeline

```bash
# Clip a specific video
python pipeline.py "https://www.youtube.com/watch?v=jNQXAC9IVRw"

# Or let it find something trending for you
python pipeline.py
```

The final video will be saved as `final_output.mp4` in your current directory.

---

## 🏗️ Architecture

The project is moving toward a modular production architecture:

- `shorts_clipper/core`: Settings, typed models, and exceptions.
- `shorts_clipper/rendering`: Safe ffmpeg command builders.
- `shorts_clipper/transcription`: Whisper adapters and SRT formatting.
- `shorts_clipper/utils`: Video metadata and utility helpers.

---

## 🧪 Development & Testing

Run the test suite:

```bash
python -m unittest discover -v
```

Check for compilation errors:

```bash
python -m compileall -q .
```

---

## 🗺️ Roadmap

Detailed roadmap and technical debt analysis can be found in [docs/ROADMAP.md](docs/ROADMAP.md).

---

## License

MIT License. See `LICENSE`.

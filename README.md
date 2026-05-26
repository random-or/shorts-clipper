# 🎬 Shorts Clipper

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://github.com/random-or/shorts-clipper/actions/workflows/ci.yml/badge.svg)](https://github.com/random-or/shorts-clipper/actions/workflows/ci.yml)
[![Status](https://img.shields.io/badge/status-production--ready-success.svg)](#)

**Shorts Clipper** is a high-performance, AI-driven automation factory for transforming long-form video into viral, high-retention vertical clips for TikTok, YouTube Shorts, and Instagram Reels.

It combines autonomous content scouting, intelligent transcript analysis, and professional-grade video editing into a seamless, single-command pipeline.

---

## ⚡ Core Capabilities

- 🛰️ **Autonomous Scouting:** Automatically identifies trending, high-signal global English content from YouTube using advanced filtering.
- 🧠 **AI Oracle (Gemini):** Leverages Gemini 2.5 Flash to identify the most engaging hooks and viral moments with pinpoint accuracy.
- 📝 **Hybrid Transcription:** 
    - **Smart Fetch:** Pulls native high-quality English subtitles directly from the source.
    - **Local Whisper:** Seamless fallback to `faster-whisper` for word-level precision when native subs are unavailable.
- 📐 **Dynamic Visual Framing:** Supports multiple AI-selected layouts:
    - `crop_center` (Standard)
    - `crop_left` / `crop_right` (Focus)
    - `split_screen` (Maximum Retention)
- 🚀 **Production Pipeline:** 
    - **Isolated Workdirs:** Each job runs in a clean, temporary environment for safe batch processing.
    - **Single-Pass Rendering:** Optimized ffmpeg/MoviePy paths to preserve video quality.
    - **Type-Safe Core:** Built on a modular Python package under `shorts_clipper/`.

---

## 🏗️ Architecture

The project follows a modular domain-driven design:

```text
shorts_clipper/
├── core/                # Data models (TranscriptSegment), settings, and exceptions.
├── rendering/           # Ffmpeg command builders and layout logic.
├── transcription/       # Whisper adapters and SRT formatting.
├── highlight_detection/ # Scoring models and AI provider adapters.
├── cropping/            # Geometry calculations and smart-crop logic.
└── utils/               # Video metadata and filesystem helpers.
```

---

## 🚀 Quick Start

### 1. Prerequisites

- **FFmpeg** (with `libass` support)
- **Python 3.11+**
- **yt-dlp**

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/random-or/shorts-clipper.git
cd shorts_clipper

# Setup environment
python -m venv env
source env/bin/activate
pip install -e .
```

### 3. Configuration

Create a `.env` file from the example:

```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 4. Run the Factory

```bash
# Clip a specific video
python pipeline.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Engage Autonomous Mode (Scouts trending content automatically)
python pipeline.py
```

The final viral clip will be saved as `final_output.mp4`.

---

## 🧪 Development & Quality

We maintain high standards through automated testing and linting:

- **Run Tests:** `python -m unittest discover -v`
- **Linting:** `pre-commit run --all-files`
- **Docker:** `docker-compose up --build`

---

## 🗺️ Roadmap & Contributing

We are actively refactoring toward a fully asynchronous FastAPI backend. See [docs/ROADMAP.md](docs/ROADMAP.md) for planned features and [CONTRIBUTING.md](CONTRIBUTING.md) for our development standards.

---

## 🛡️ Security & License

- **Security:** Please see [SECURITY.md](SECURITY.md) for reporting vulnerabilities.
- **License:** Distributed under the MIT License. See `LICENSE` for more information.

<div align="center">
  <sub>Built with ❤️ by the Shorts Clipper Contributors</sub>
</div>

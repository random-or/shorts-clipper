<div align="center">

# 🎬 Shorts Clipper

### AI-Powered Viral Shorts Factory

*Scout trending videos → Extract the best moments → Render vertical clips → Publish to YouTube — fully automated.*

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-40%20passed-22c55e?style=for-the-badge&logo=pytest&logoColor=white)](#testing)
[![Docker Ready](https://img.shields.io/badge/docker-ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](#docker)

</div>

---

## What It Does

Shorts Clipper takes any long-form YouTube video and turns it into publish-ready 9:16 vertical shorts with word-level animated captions — in one command or from a sleek web dashboard.

**The full pipeline:**

```
Scout Trending Video → Download → Transcribe (Whisper) → AI Clip Selection (Gemini) → Vertical Crop → Burn Captions → Publish to YouTube
```

**Core capabilities:**
- 🔍 **Trending Scout** — Finds viral-potential videos using view-velocity scoring
- 🧠 **Gemini AI Director** — Picks the most engaging 30-60s windows with virality scoring
- 🎙️ **Whisper Transcription** — Word-level timestamps for animated captions
- 🎬 **FFmpeg Rendering** — Vertical crop + subtitle burn in a single optimized pass
- 📤 **YouTube Auto-Publish** — Upload directly to YouTube Shorts via OAuth2
- 🖥️ **Web Dashboard** — Dark-mode console with real-time pipeline tracking

---

## Quick Start

### Prerequisites

| Tool | Why |
|------|-----|
| **Python 3.11+** | Runtime |
| **FFmpeg** | Video processing |
| **Gemini API Key** | AI clip selection — [get one free](https://aistudio.google.com/) |

### Install

```bash
# Clone
git clone https://github.com/random-or/shorts-clipper.git
cd shorts-clipper

# Virtual environment
python -m venv env
source env/bin/activate   # Windows: env\Scripts\activate

# Dependencies
pip install -e .

# Configure
cp .env.example .env
# Edit .env and paste your GEMINI_API_KEY
```

### Run

**Web Dashboard** (recommended):
```bash
python -m shorts_clipper web --port 8000
# Open http://localhost:8000
```

**CLI — Clip a specific video:**
```bash
python -m shorts_clipper clip "https://youtube.com/watch?v=VIDEO_ID" --count 3
```

**CLI — Full autopilot** (scout + clip automatically):
```bash
python -m shorts_clipper autopilot --niche "podcast debates" --count 2 --upload
```

**CLI — Scout only** (print trending URLs):
```bash
python -m shorts_clipper scout --niche "tech news" --count 5
```

---

## Web Dashboard

The built-in web console gives you three modes:

| Mode | Description |
|------|-------------|
| **Autopilot Launchpad** | Set a niche, hit launch — it scouts, clips, and publishes on its own |
| **Interactive Clipper** | Paste a URL, review AI-scored highlights, preview clips, then render |
| **Clip Library** | Browse rendered clips, preview them, publish to YouTube with one click |

The dashboard includes a real-time pipeline tracker, live log stream, upload progress with speed/ETA, and YouTube channel integration.

---

## YouTube Upload Setup

To enable direct publishing to YouTube Shorts:

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → Create a project
2. Enable **YouTube Data API v3**
3. Create **OAuth 2.0 credentials** (Desktop app)
4. Download `client_secret.json` → place it in the project root
5. Connect your channel from the web dashboard sidebar

---

## Docker

```bash
docker build -t shorts-clipper .
docker run -p 8000:8000 --env-file .env shorts-clipper
```

---

## Project Structure

```
shorts_clipper/
├── api/          # FastAPI server + SSE log streaming
├── scout/        # Trending video discovery engine
├── providers/    # Gemini AI highlight detection
├── downloader/   # yt-dlp integration
├── transcription/# Whisper speech-to-text
├── rendering/    # Vertical crop + FFmpeg processing
├── captions/     # Word-level subtitle generation + burning
├── social/       # YouTube upload adapter
├── pipeline/     # Orchestration runner
├── ui/           # Web dashboard (single-page dark-mode console)
└── core/         # Settings, logging, models, job queue
```

---

## Configuration

All settings live in `.env` (see [`.env.example`](.env.example)):

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | **Required.** Your Google Gemini API key |
| `SHORTS_WHISPER_MODEL` | `tiny.en` | Whisper model (`tiny.en` → `large-v3`) |
| `SHORTS_WHISPER_DEVICE` | `cpu` | `cpu` or `cuda` |
| `SHORTS_VIDEO_CODEC` | `libx264` | FFmpeg codec (`libx264` or `h264_nvenc`) |
| `SHORTS_ENABLE_GPU` | `false` | Enable NVENC + CUDA acceleration |

---

## Testing

```bash
pip install -e ".[dev]"
pytest
ruff check shorts_clipper
```

---

## License

[MIT](LICENSE) — use it, fork it, ship it.

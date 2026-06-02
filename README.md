<div align="center">

# 🎬 Shorts Clipper

### **AI-Powered Viral Shorts Factory**

*Transform any long-form video into scroll-stopping vertical clips — fully automated, from scouting to publishing.*

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-40%20passed-22c55e?style=for-the-badge&logo=pytest&logoColor=white)](#-testing)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-f5a623?style=for-the-badge)](https://docs.astral.sh/ruff/)
[![Docker Ready](https://img.shields.io/badge/docker-ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](#-docker-deployment)

<br/>

<p>
  An open-source, end-to-end automation pipeline that takes any long-form landscape video and autonomously produces polished, captioned, 9:16 vertical shorts ready for <strong>YouTube Shorts</strong>, <strong>TikTok</strong>, and <strong>Instagram Reels</strong>.
</p>

<p>
  Features a Gemini-powered virality scoring engine, word-level animated subtitles, a self-healing trending video scout, native YouTube auto-publishing, and a stunning dark-mode web dashboard — all in one package.
</p>

<br/>

**[⚡ Quick Start](#-quick-start) · [🖥️ Web Console](#%EF%B8%8F-web-console) · [🧠 How It Works](#-how-it-works) · [🐳 Docker](#-docker-deployment) · [🧩 Architecture](#-project-structure)**

</div>

<br/>

---

<br/>

## ✨ Feature Highlights

<table>
<tr>
<td width="50%">

### 🤖 Autonomous Scout Engine
Hunts trending videos across YouTube and **Twitch VOD highlights** using a **view-velocity scoring algorithm** with self-healing age filters, parallel metadata fetching, and smart deduplication cache (7-day TTL). Supports channel targeting, niche rotation, and keyword search.

</td>
<td width="50%">

### 🧠 Gemini AI Director
Analyzes full transcripts with **Gemini 2.5 Flash** to isolate the single best 30–60 second window with the highest emotional density and hook quality. Each clip is strictly graded on retention, clip-ability, and niche relevance. Multi-clip extraction supported.

</td>
</tr>
<tr>
<td width="50%">

### ⚡ Two-Pass FFmpeg Pipeline
**Pass 1** scales + crops to 1080×1920 vertical. **Pass 2** burns animated **ASS subtitles** with word-level karaoke timing and applies **1.15× pacing** to cut dead air — both in single FFmpeg calls. No triple-encoding. GPU acceleration supported via `h264_nvenc`.

</td>
<td width="50%">

### 📤 YouTube Auto-Publishing
Clips are automatically uploaded to **YouTube Shorts** (defaulting to Private for review) with AI-generated titles, descriptions, and tags. OAuth2 token is cached locally so you only authenticate once.

</td>
</tr>
<tr>
<td width="50%">

### 🖥️ Premium Web Dashboard
A stunning dark-mode Web UI with real-time SSE log streaming, an interactive clipper studio, media library with thumbnails, one-click publishing, clip deletion, and full settings management — all served by FastAPI.

</td>
<td width="50%">

### 📊 Performance Analytics
Built-in SQLite-backed feedback system tracks views, likes, shares, watch time, and retention percentage for every clip. Performance scores are computed automatically to help the AI learn what works.

</td>
</tr>
</table>

<br/>

---

<br/>

## ⚡ Quick Start

### Prerequisites

| Tool | Version | Purpose |
|:-----|:--------|:--------|
| **Python** | 3.11+ | Runtime |
| **FFmpeg** | Latest (with `libass`) | Video processing & subtitle burning |
| **yt-dlp** | 2024.1.0+ | Video downloading (installed automatically) |

### Step 1 — Clone & Install

```bash
# Clone the repository
git clone https://github.com/random-or/shorts-clipper.git
cd shorts-clipper

# Create & activate virtual environment
python -m venv env
source env/bin/activate          # Linux / macOS
# env\Scripts\activate           # Windows

# Install the package (editable mode for development)
pip install -e ".[dev]"
```

### Step 2 — Configure API Key

```bash
cp .env.example .env
```

Open `.env` and paste your **Gemini API key** ([get one free here](https://aistudio.google.com/)).

```env
GEMINI_API_KEY=your_key_here
```

### Step 3 — Run It 🚀

**Option A — Web Console (recommended)**
```bash
python -m shorts_clipper web --port 8000
```
Open **http://localhost:8000** in your browser.

**Option B — CLI Autopilot**
```bash
# Scout a trending video and generate 3 clips automatically
python -m shorts_clipper autopilot --niche twitch --count 3

# Clip a specific YouTube URL
python -m shorts_clipper clip https://www.youtube.com/watch?v=VIDEO_ID

# Just scout without rendering
python -m shorts_clipper scout --niche drama --count 5
```

<br/>

---

<br/>

## 🖥️ Web Console

The self-hosted web dashboard is the command center for the entire pipeline:

- **Autopilot Launchpad** — Select a niche (Drama, Motivation, Gaming, **Twitch VOD Highlights**), target a specific channel, or enter a keyword. Toggle auto-upload to YouTube. Hit launch.
- **Interactive Clipper Studio** — Paste any YouTube URL, view the full transcript, let Gemini score highlight candidates, and render specific segments.
- **Clips Library** — Browse all generated clips with video thumbnails, preview playback, one-click **Publish to YouTube**, and **Delete** to clean up.
- **Console Settings** — Configure Gemini API key, Whisper model, GPU mode, and video encoding presets directly from the browser.
- **Live Log Stream** — Real-time Server-Sent Events terminal showing exactly what FFmpeg and Gemini are doing.

<br/>

---

<br/>

## 🧠 How It Works

```
┌─────────────┐    ┌──────────────┐    ┌──────────────────┐    ┌───────────────┐
│   SCOUT     │───▶│  TRANSCRIBE  │───▶│   GEMINI SELECT  │───▶│   DOWNLOAD    │
│  trending   │    │  rough pass  │    │  best 60s window │    │  micro-clip   │
└─────────────┘    └──────────────┘    └──────────────────┘    └───────┬───────┘
                                                                      │
┌─────────────┐    ┌──────────────┐    ┌──────────────────┐           │
│   PUBLISH   │◀───│  BURN SUBS   │◀───│  VERTICAL CROP   │◀──────────┘
│  to YouTube │    │  ASS + pace  │    │  1080×1920       │
└─────────────┘    └──────────────┘    └──────────────────┘
```

1. **Scout** — Parallel search across multiple query pools with virality scoring and smart caching.
2. **Rough Transcript** — Fetch native subtitles or transcribe a 5-minute audio sample with tiny Whisper.
3. **AI Selection** — Gemini analyzes the transcript and picks the highest-impact 30–60 second window.
4. **Precision Download** — Only the selected micro-clip is downloaded (not the full video).
5. **Vertical Crop** — FFmpeg scales and crops to 9:16 (1080×1920) in a single pass.
6. **Burn Subtitles** — Animated ASS subtitles with 1.15× pacing baked in one FFmpeg call.
7. **Thumbnail** — A frame at 25% duration is extracted as a JPEG cover image.
8. **Publish** — Optionally auto-upload to YouTube Shorts with AI-generated metadata.

<br/>

---

<br/>

## 🧩 Project Structure

```
shorts-clipper/
├── shorts_clipper/
│   ├── api/                   # FastAPI server, REST endpoints, SSE streaming
│   ├── ui/                    # Web Console frontend (HTML/CSS/JS)
│   ├── core/                  # Settings, models, SQLite job queue, logging
│   ├── pipeline/              # Main orchestrator (runner.py — the brain)
│   ├── scout/                 # Trending video discovery & virality scoring
│   ├── providers/             # Gemini AI highlight evaluation
│   ├── transcription/         # Whisper transcription (local + Gemini fallback)
│   ├── downloader/            # yt-dlp download utilities
│   ├── rendering/             # FFmpeg vertical crop processor
│   ├── captions/              # ASS subtitle generator & burner
│   ├── render/                # Thumbnail extraction
│   ├── cropping/              # Geometry calculations for crop framing
│   ├── social/                # YouTube upload integration (OAuth2)
│   ├── analyze/               # Performance feedback & analytics
│   └── utils/                 # Video metadata helpers
├── tests/                     # 40+ unit & integration tests
├── Dockerfile                 # Production container image
├── docker-compose.yml         # One-command deployment
├── pyproject.toml             # Dependencies & tool configuration
└── .env.example               # Environment variable template
```

<br/>

---

<br/>

## 🎯 CLI Reference

```bash
# ── Autopilot Mode ──────────────────────────────────────────
python -m shorts_clipper autopilot                          # Scout + render 1 clip
python -m shorts_clipper autopilot --niche twitch --count 3 # 3 Twitch highlights
python -m shorts_clipper autopilot --channel @JoeRogan      # Target a channel
python -m shorts_clipper autopilot --keyword "heated debate" # Keyword search
python -m shorts_clipper autopilot --upload                 # Auto-publish to YouTube

# ── Manual Clipping ─────────────────────────────────────────
python -m shorts_clipper clip <URL>                         # Clip a specific video
python -m shorts_clipper clip <URL> --count 3               # Extract 3 clips
python -m shorts_clipper clip <URL> --upload                # Clip + upload

# ── Scout Only ──────────────────────────────────────────────
python -m shorts_clipper scout                              # Print 1 trending URL
python -m shorts_clipper scout --niche drama --count 5      # Print 5 drama URLs

# ── Web Console ─────────────────────────────────────────────
python -m shorts_clipper web                                # Start on localhost:8000
python -m shorts_clipper web --host 0.0.0.0 --port 3000    # Custom bind
```

<br/>

---

<br/>

## 🐳 Docker Deployment

Deploy the full stack anywhere with a single command:

```bash
# 1. Configure your environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 2. Build and launch
docker-compose up --build

# The web console is now live at http://localhost:8000
```

The Docker setup:
- Installs FFmpeg, yt-dlp, and all Python dependencies automatically.
- Mounts `outputs/`, `models/`, and `.cache/` as persistent volumes.
- Exposes port 8000 for the web dashboard.
- Works on any VPS (DigitalOcean, Hetzner, Railway, Render, etc.)

<br/>

---

<br/>

## 📤 YouTube Auto-Publishing Setup

To enable automatic uploading to YouTube Shorts:

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a project.
2. Enable the **YouTube Data API v3**.
3. Create **OAuth 2.0 credentials** (Desktop application type).
4. Download the credentials JSON and save it as `client_secret.json` in the project root.
5. Run with `--upload` flag. On first run, a browser window will open for Google sign-in.
6. After authentication, a token is cached locally — you won't need to sign in again.

```bash
python -m shorts_clipper autopilot --niche twitch --upload
```

Videos are uploaded as **Private** by default so you can review them before publishing.

<br/>

---

<br/>

## 🧪 Testing

The project has comprehensive test coverage with 40 tests across 3 test files:

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run the full test suite
python -m pytest tests/ -v

# Code quality checks
ruff check .
ruff format --check .
```

<br/>

---

<br/>

## 🗺️ Roadmap

- [x] Multi-pool trending scout with virality scoring
- [x] Gemini-powered clip selection with multi-clip support
- [x] Two-pass FFmpeg pipeline (crop → burn subs + pacing)
- [x] Word-level animated ASS subtitles
- [x] Full Web Console with SSE live logs
- [x] SQLite job queue and performance analytics
- [x] YouTube Shorts auto-publishing
- [x] Twitch VOD highlight hunting
- [x] Thumbnail generation
- [x] Docker deployment ready
- [ ] TikTok & Instagram Reels auto-publishing
- [ ] B-Roll overlay engine
- [ ] Scheduled cron autopilot (run every N hours)
- [ ] Multi-language subtitle support
- [ ] Advanced analytics dashboard with charts

<br/>

---

<br/>

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Fork, clone, and install dev dependencies
pip install -e ".[dev]"

# Run tests before submitting
python -m pytest tests/ -v
ruff check .
```

<br/>

<div align="center">

## 📄 License
Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

<br/>

**Built with ❤️ and way too much FFmpeg debugging.**

</div>

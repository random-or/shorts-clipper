<div align="center">

# 🎬 Shorts Clipper

### **AI-Powered Viral Shorts Factory**

*Easily transform long-form videos into scroll-stopping vertical clips — fully automated with a state-of-the-art web dashboard.*

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/random-or/shorts-clipper/ci.yml?branch=main&style=for-the-badge&label=CI&logo=github)](https://github.com/random-or/shorts-clipper/actions)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-f5a623?style=for-the-badge)](https://docs.astral.sh/ruff/)

<br/>

<p>
  <strong>Shorts Clipper</strong> is an open-source, end-to-end automation pipeline that takes any long-form landscape video and autonomously produces polished, captioned, 9:16 vertical shorts ready for <strong>TikTok</strong>, <strong>YouTube Shorts</strong>, and <strong>Instagram Reels</strong>. It features a complete SQLite-backed job queue, Gemini-powered engagement scoring, and a beautiful full-stack web dashboard.
</p>

<br/>

**[⚡ Quick Start](#-quick-start) · [🖥️ Web Dashboard](#%EF%B8%8F-web-console) · [🧠 How It Works](#-how-it-works) · [🧩 Modules](#-project-structure)**

</div>

<br/>

---

<br/>

## ✨ Highlights

<table>
<tr>
<td width="50%">

### 🖥️ Web Console
A stunning, fully-featured dark-mode Web UI with a 3-column "Descript-like" layout. Track server-side job progress, configure environment variables in-browser, launch Autopilot targeting, and view your rendered clip media library with embedded performance feedback.

</td>
<td width="50%">

### 🤖 Autonomous Scout & Queue
Hunts trending videos using a **view-velocity scoring algorithm** with self-healing age filtering to avoid stale content. Features a thread-safe, resilient SQLite job queue so your clip generation never blocks or crashes mid-render.

</td>
</tr>
<tr>
<td width="50%">

### 🧠 Gemini AI Virality Scoring
Analyzes transcripts with **Gemini 2.5 Flash / Pro** to isolate the single best 30–60 second window with the highest emotional density and hook quality. Each clip is strictly graded out of 100 on retention, clip-ability, and niche relevance.

</td>
<td width="50%">

### ⚡ One-Pass FFmpeg Rendering
Scales, crops, burns animated **ASS subtitles** with word-level karaoke timing, and applies **1.15× pacing** to cut dead air — all executed in a **single GPU-accelerated FFmpeg pass** to guarantee maximum quality and speed.

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
| **yt-dlp** | 2024.1.0+ | Video downloading |

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/random-or/shorts-clipper.git
cd shorts-clipper

# 2. Create & activate virtual environment
python -m venv env
source env/bin/activate          # Linux / macOS

# 3. Install the package
pip install -r requirements.txt
pip install -e .
```

### Setup API Keys

```bash
cp .env.example .env
```
Open `.env` and add your **Gemini API key** ([get one free here](https://aistudio.google.com/)).

### Launch the Web Console 🚀

```bash
uvicorn shorts_clipper.api.server:app --reload --port 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser to access the Shorts Clipper Console. From here you can launch autopilot searches, process custom videos, and view the live streaming log console.

Alternatively, use the terminal CLI:
```bash
python -m shorts_clipper autopilot --count 3
```

<br/>

---

<br/>

## 🖥️ Web Console

The new web-based dashboard serves as the command center for the pipeline. It is entirely self-hosted and features:
- **Interactive Clipper Studio:** Paste a YouTube URL, retrieve a full transcript, and render specific selections.
- **Autopilot Launchpad:** Target niches or specific keywords to automatically scout and download the best trending videos on YouTube.
- **Media Library:** Preview rendered MP4 videos, retrieve dynamic thumbnails, and view performance telemetry.
- **System Settings:** Modify the underlying `.env` configuration (such as Whisper models or GPU settings) directly from the UI.
- **Live Output Stream:** A built-in terminal stream using Server-Sent Events to show exactly what FFmpeg and Gemini are thinking in real-time.

<br/>

---

<br/>

## 🧩 Project Structure

```
shorts-clipper/
├── shorts_clipper/
│   ├── api/                   # FastAPI Web Server & REST/SSE Endpoints
│   ├── ui/                    # Web Console Frontend (HTML/JS/CSS)
│   ├── core/                  # SQLite Job Queue, Settings, Logging
│   ├── scout/                 # YouTube Discovery & Virality Selection
│   ├── analyze/               # Clip Performance Feedback & Analytics
│   ├── render/                # FFmpeg Subtitle Rendering & Thumbnails
│   ├── providers/             # Gemini AI highlight evaluation
│   ├── transcription/         # Whisper local / API transcription
│   └── pipeline/              # Main orchestrator uniting the engine
├── tests/                     # Unit & Integration Pytests (40+ tests)
├── .github/workflows/         # CI/CD: Ruff formatting & pytest matrix
└── pyproject.toml             # Dependencies & configurations
```

<br/>

---

<br/>

## 🧪 Testing & Code Quality

The system is fully covered by automated testing:

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run the test suite
python -m pytest tests/ -v

# Code Quality & Format Checks
ruff check .
ruff format --check .
```

<br/>

---

<br/>

## 🤝 Contributing & Roadmap

We have just completed **Phase 7** of the Deployment-Grade Architecture Roadmap.
Recent improvements include:
- ✅ **SQLite Job Queue:** Persistent tracking of all render jobs.
- ✅ **Performance Tracking:** Analytics module for views and retention scores.
- ✅ **UI Redesign:** A strict, premium flat UI design system (no glassmorphism).
- ✅ **CI/CD Stabilization:** Linting and formatting strictness enforced by Ruff.

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

<br/>

<div align="center">

## 📄 License
Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

</div>

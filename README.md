<div align="center">

# 🎬 Shorts Clipper

### **AI-Powered Viral Shorts Factory**

*Transform long-form videos into scroll-stopping vertical clips — fully automated.*

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/random-or/shorts-clipper/ci.yml?branch=main&style=for-the-badge&label=CI&logo=github)](https://github.com/random-or/shorts-clipper/actions)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-f5a623?style=for-the-badge)](https://docs.astral.sh/ruff/)

<br/>

<p>
  <strong>Shorts Clipper</strong> is an open-source, end-to-end automation pipeline that takes any long-form landscape video — podcasts, livestreams, debates, talk shows, video essays — and autonomously produces polished, captioned, 9:16 vertical shorts ready for <strong>TikTok</strong>, <strong>YouTube Shorts</strong>, and <strong>Instagram Reels</strong>.
</p>

<br/>

**[⚡ Quick Start](#-quick-start) · [📖 How It Works](#-how-it-works) · [🧩 Modules](#-project-structure) · [🐳 Docker](#-docker) · [🤝 Contributing](#-contributing)**

</div>

<br/>

---

<br/>

## ✨ Highlights

<table>
<tr>
<td width="50%">

### 🤖 Autonomous Scout
Hunts trending videos across multiple search pools using a **view-velocity scoring algorithm**. Filters by language, duration, and virality — then auto-selects the best candidate. Supports channel targeting, niche rotation, and multi-platform keyword search.

</td>
<td width="50%">

### 🧠 AI Highlight Detection
Uses **Gemini 2.5 Flash** to analyze transcripts and isolate the single best 30–60 second window with the highest emotional density, a strong hook in the first 2 seconds, and maximum virality potential. Scores clips on a 100-point scale.

</td>
</tr>
<tr>
<td width="50%">

### 🎙️ Dual-Engine Transcription
Primary: Gemini API transcription with word-level timestamps. Fallback: local **faster-whisper** models (`tiny.en` → `large-v3`) with optional GPU acceleration via `float16` quantization. Always delivers precision word-level timing.

</td>
<td width="50%">

### ⚡ One-Pass FFmpeg Rendering
Burns styled, animated, dual-color **ASS subtitles** with word-level karaoke timing, applies **1.15× pacing** to cut dead air, and compresses audio — all in a **single FFmpeg pass** to prevent quality degradation.

</td>
</tr>
<tr>
<td width="50%">

### 📐 Smart Crop Layouts
Intelligent geometry math converts widescreen → vertical. Supports **center crop** (single subject), **left/right crop** (offset subjects), layout auto-selected by the AI based on video content analysis.

</td>
<td width="50%">

### 🎨 Styled Animated Captions
Word-level animated subtitles with micro-scale pop effects, fade transitions, blur, and **emotional trigger word highlighting** (random accent colors on words like *INSANE*, *BRO*, *CRAZY*). Feels native to TikTok/Reels.

</td>
</tr>
</table>

<br/>

---

<br/>

## 🔥 How It Works

Shorts Clipper uses a **2-pass architecture** to minimize bandwidth, API cost, and processing time:

```mermaid
graph LR
    A["🔍 Scout"] -->|YouTube URL| B["📝 Pass 1: Rough Transcript"]
    B -->|SRT or Whisper Tiny| C["🧠 Gemini AI Analysis"]
    C -->|Time Window + Layout| D["📥 Pass 2: Micro-Download"]
    D -->|30-60s HD Clip| E["🎙️ Whisper Word-Level"]
    E -->|Precision Timestamps| F["📐 Vertical Crop"]
    F -->|9:16 MP4| G["🔥 Subtitle Burn + Pacing"]
    G -->|Final Short| H["✅ Output"]

    style A fill:#6366f1,stroke:none,color:#fff
    style B fill:#8b5cf6,stroke:none,color:#fff
    style C fill:#a855f7,stroke:none,color:#fff
    style D fill:#c084fc,stroke:none,color:#fff
    style E fill:#d946ef,stroke:none,color:#fff
    style F fill:#ec4899,stroke:none,color:#fff
    style G fill:#f43f5e,stroke:none,color:#fff
    style H fill:#22c55e,stroke:none,color:#fff
```

| Pass | What Happens | Why |
|:-----|:-------------|:----|
| **Pass 1 — Analysis** | Fetches native subtitles (or downloads a low-bandwidth 5-min audio slice for tiny Whisper). Gemini evaluates the transcript to find the most viral window. | Avoids downloading the full video. Saves bandwidth and time. |
| **Pass 2 — Execution** | Uses `yt-dlp --download-sections` to grab **only** the selected 30–60s in high resolution. Runs full Whisper for word-level timestamps. Crops, burns subtitles, applies pacing. | Cuts total processing time by up to **90%**. |

<br/>

---

<br/>

## ⚡ Quick Start

### Prerequisites

| Tool | Version | Purpose |
|:-----|:--------|:--------|
| **Python** | 3.11+ | Runtime |
| **FFmpeg** | Latest (with `libass`) | Video processing & subtitle burning |
| **yt-dlp** | 2024.1.0+ | Video downloading (installed via pip) |

<details>
<summary><b>📦 Install FFmpeg</b> (click to expand)</summary>

<br/>

**Ubuntu / Debian:**
```bash
sudo apt update && sudo apt install ffmpeg libass-dev -y
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
```powershell
winget install Gyan.FFmpeg
```
Or download a static build from [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/).

</details>

<br/>

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/random-or/shorts-clipper.git
cd shorts-clipper

# 2. Create & activate virtual environment
python -m venv env
source env/bin/activate          # Linux / macOS
# env\Scripts\activate.bat       # Windows CMD
# .\env\Scripts\Activate.ps1     # Windows PowerShell

# 3. Install the package
pip install -r requirements.txt
pip install -e .
```

### Set Up Your API Key

```bash
# Copy the example config
cp .env.example .env
```

Open `.env` and add your **Gemini API key** (free from [Google AI Studio](https://aistudio.google.com/)):

```env
GEMINI_API_KEY=your_api_key_here
```

### Run Your First Clip 🎉

```bash
# Clip a specific video
python -m shorts_clipper clip "https://www.youtube.com/watch?v=VIDEO_ID"

# Or let the AI find a trending video and clip it automatically
python -m shorts_clipper autopilot
```

Your polished vertical short will appear in the `outputs/` folder. That's it.

<br/>

---

<br/>

## 💻 CLI Reference

Shorts Clipper exposes three subcommands:

### `clip` — Process a Specific Video

```bash
python -m shorts_clipper clip <youtube_url> [options]
```

| Flag | Description |
|:-----|:------------|
| `<url>` | YouTube video URL *(required)* |
| `-o, --output PATH` | Custom output file path (default: `outputs/clip_TIMESTAMP.mp4`) |

```bash
# Example: clip with custom output path
python -m shorts_clipper clip "https://youtu.be/dQw4w9WgXcQ" -o ./clips/my_short.mp4
```

### `autopilot` — Fully Automated Pipeline

```bash
python -m shorts_clipper autopilot [options]
```

| Flag | Description |
|:-----|:------------|
| `--channel CHANNEL` | Target a specific channel's recent uploads |
| `--niche NICHE` | Generate 5 targeted search queries around a topic and rotate |
| `--keyword KEYWORD` | Search for a specific term across multiple platforms |

```bash
# Auto-find and clip a trending podcast moment
python -m shorts_clipper autopilot --niche "podcast drama"

# Clip from a specific channel
python -m shorts_clipper autopilot --channel "JRE Clips"
```

### `scout` — Dry-Run Discovery

```bash
python -m shorts_clipper scout [options]
```

| Flag | Description |
|:-----|:------------|
| `-n, --count N` | Number of URLs to find (default: 1) |
| `--channel CHANNEL` | Target a specific channel |
| `--niche NICHE` | Search within a niche topic |
| `--keyword KEYWORD` | Search by keyword |

```bash
# Find 3 trending video URLs without clipping
python -m shorts_clipper scout -n 3
```

### Global Options

| Flag | Description |
|:-----|:------------|
| `--log-level LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`) |
| `--env FILE` | Path to `.env` config file (default: `.env`) |

<br/>

---

<br/>

## ⚙️ Configuration

All settings are controlled via environment variables in your `.env` file:

### 🔑 AI Provider

| Variable | Default | Description |
|:---------|:--------|:------------|
| `GEMINI_API_KEY` | — | **Required.** Your Google Gemini API key ([get one free](https://aistudio.google.com/)) |
| `SHORTS_PROVIDER` | `gemini` | LLM provider for highlight detection |

### 🎙️ Transcription

| Variable | Default | Description |
|:---------|:--------|:------------|
| `SHORTS_WHISPER_MODEL` | `large-v3` | Whisper model size: `tiny.en` · `base.en` · `small.en` · `medium.en` · `large-v3` |
| `SHORTS_WHISPER_DEVICE` | `cpu` | Compute device: `cpu` or `cuda` |
| `SHORTS_WHISPER_COMPUTE_TYPE` | `int8` | Quantization: `int8` (CPU) · `float16` (GPU) · `float32` |
| `SHORTS_ENABLE_GPU` | `false` | Enable GPU for both Whisper and FFmpeg |

### 📂 Paths

| Variable | Default | Description |
|:---------|:--------|:------------|
| `SHORTS_OUTPUT_DIR` | `outputs` | Where final shorts are saved |
| `SHORTS_MODELS_DIR` | `models` | Where Whisper model weights are cached |
| `SHORTS_CACHE_DIR` | `.cache/shorts-clipper` | Seen-video database (prevents re-processing) |
| `SHORTS_LOG_LEVEL` | `INFO` | Logging verbosity |

> [!TIP]
> For quick testing, use `SHORTS_WHISPER_MODEL=tiny.en` — it's 10× faster than `large-v3`. Switch to `large-v3` for production-quality captions.

<br/>

---

<br/>

## 🧩 Project Structure

```
shorts-clipper/
├── shorts_clipper/
│   ├── core/                  # Settings, logging, data models, exceptions
│   ├── scout/                 # Trending video discovery & virality scoring
│   ├── downloader/            # yt-dlp video/audio/subtitle fetching
│   ├── transcription/         # Whisper + Gemini transcription engines
│   ├── highlight_detection/   # Rule-based highlight scoring heuristics
│   ├── providers/             # AI provider ABC + Gemini adapter
│   ├── cropping/              # Aspect-ratio geometry calculations
│   ├── captions/              # ASS subtitle generation & word-level animation
│   ├── rendering/             # FFmpeg crop & render command builders
│   ├── pipeline/              # Main orchestrator (wires everything together)
│   ├── api/                   # 🚧 Planned REST API (see docs/API.md)
│   └── ui/                    # 🚧 Planned web dashboard
├── tests/                     # Unit tests (unittest + mock)
├── docs/                      # API spec & roadmap
│   ├── API.md                 # Planned REST/WebSocket API contract
│   └── ROADMAP.md             # 6-phase production roadmap
├── .github/
│   └── workflows/ci.yml       # CI: lint (Ruff) + test matrix (3.11, 3.12)
├── requirements.txt           # Production dependencies
├── pyproject.toml             # Package metadata & dev extras
├── Dockerfile                 # Container build
├── docker-compose.yml         # One-command deployment
└── .env.example               # Configuration template
```

<br/>

---

<br/>

## 🐳 Docker

Run the entire pipeline in a container — no local setup required (besides Docker):

```bash
# 1. Configure your API key
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 2. Build & run
docker-compose build
docker-compose up
```

Output shorts are mounted to `./outputs/` on your host machine.

<details>
<summary><b>🔧 Docker Compose Details</b></summary>

The compose file mounts three volumes:

| Host Path | Container Path | Purpose |
|:----------|:---------------|:--------|
| `./outputs` | `/app/outputs` | Final rendered shorts |
| `./models` | `/app/models` | Cached Whisper model weights |
| `./.cache` | `/app/.cache` | Seen-video database |

</details>

<br/>

---

<br/>

## 🧪 Testing & Code Quality

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run the test suite
python -m pytest tests/ -v

# Lint checks
ruff check .

# Format checks
ruff format --check .

# Compile check (catches syntax errors)
python -m compileall -q shorts_clipper/
```

CI runs automatically on every push and PR to `main` — testing against Python **3.11** and **3.12**.

<br/>

---

<br/>

## 🔧 Troubleshooting

<details>
<summary><b>❌ <code>ffmpeg: libass not found</code></b></summary>

Your FFmpeg installation is missing the ASS subtitle library.

**Fix:** Reinstall FFmpeg from your system package manager (`apt`, `brew`, `winget`) — they include `libass` by default. Or download a full static build.
</details>

<details>
<summary><b>❌ <code>Cache load failed: Permission denied</code></b></summary>

The cache directory is pointing to a location without write permissions.

**Fix:** Ensure `SHORTS_CACHE_DIR` in your `.env` points to a writable path within the project directory:
```env
SHORTS_CACHE_DIR=.cache/shorts-clipper
```
</details>

<details>
<summary><b>❌ <code>yt-dlp download sections error</code></b></summary>

Your yt-dlp version doesn't support section-based downloads.

**Fix:** Upgrade to the latest version:
```bash
pip install --upgrade yt-dlp
```
</details>

<details>
<summary><b>❌ Whisper model download is slow / fails</b></summary>

Large Whisper models can take time to download on first run.

**Fix:** Start with a smaller model for testing, then upgrade:
```env
SHORTS_WHISPER_MODEL=tiny.en
```
</details>

<br/>

---

<br/>

## 🗺️ Roadmap

| Status | Milestone |
|:-------|:----------|
| ✅ Done | Modular pipeline architecture, Gemini highlight detection, ASS subtitle rendering |
| ✅ Done | Autonomous scout with virality scoring, 2-pass download optimization |
| ✅ Done | CI/CD, unit tests, Docker support |
| 🔜 Next | REST API (`POST /jobs`, WebSocket progress events) |
| 🔜 Next | Web dashboard for job management |
| 🔜 Next | Multi-provider support (OpenAI, Anthropic, Ollama) |

See the full [roadmap](docs/ROADMAP.md) for detailed plans.

<br/>

---

<br/>

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Quick dev setup
git clone https://github.com/random-or/shorts-clipper.git
cd shorts-clipper
python -m venv env && source env/bin/activate
pip install -e ".[dev]"
pip install pre-commit && pre-commit install
```

Please read our [Security Policy](SECURITY.md) before submitting vulnerability reports.

<br/>

---

<br/>

<div align="center">

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

<br/>

---

<br/>

**Built with 🔥 by [random-or](https://github.com/random-or)**

*If this project helped you, consider giving it a ⭐*

</div>

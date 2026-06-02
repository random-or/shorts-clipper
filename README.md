<div align="center">

# 🎬 Shorts Clipper
### **AI-Powered Viral Shorts Factory**

*Autonomously discover, crop, transcribe, caption, and publish viral vertical clips from long-form landscape videos.*

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-40%20passed-22c55e?style=for-the-badge&logo=pytest&logoColor=white)](#-testing--code-quality)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-f5a623?style=for-the-badge)](https://docs.astral.sh/ruff/)
[![Docker Ready](https://img.shields.io/badge/docker-ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](#-docker-deployment)
[![Powered by Gemini](https://img.shields.io/badge/AI-Gemini%202.5%20Flash-blue?style=for-the-badge&logo=google-gemini&logoColor=white)](https://ai.google.dev/)

<br/>

**Shorts Clipper** is an open-source, production-grade automation pipeline designed to transform standard landscape videos into polished, word-level animated captioned, 9:16 vertical clips ready for **YouTube Shorts**, **TikTok**, and **Instagram Reels**. 

Features an advanced view-velocity trending scout, Gemini-powered virality evaluation, high-performance pure FFmpeg subtitle burning, and an interactive dark-mode web console with dynamic YouTube auto-publishing.

---

**[⚡ Quick Start](#-quick-start) · [🖥️ Web Console](#-web-console) · [🧠 How It Works](#-how-it-works) · [🐳 Docker Setup](#-docker-deployment) · [🔑 OAuth Configuration](#-youtube-data-api-v3--oauth2-setup) · [🧪 Testing](#-testing--code-quality)**

</div>

<br/>

---

## ✨ Features & Architecture Highlights

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

---

## ⚡ Quick Start

### System Prerequisites

Make sure your machine meets the following environment specifications:

*   **Python**: Version `3.11` or higher.
*   **FFmpeg**: Latest version built with `--enable-libass` (required for caption rendering).
*   **yt-dlp**: Installed automatically, keeps itself up-to-date.

### Step 1: Clone & Install

```bash
# Clone the repository
git clone https://github.com/random-or/shorts-clipper.git
cd shorts-clipper

# Create and activate virtual environment
python -m venv env
source env/bin/activate          # Linux / macOS
# env\Scripts\activate           # Windows

# Install the package with dev dependencies (editable mode)
pip install -e ".[dev]"
```

### Step 2: Configure Environment

Copy the example environment file:
```bash
cp .env.example .env
```

Open `.env` in your editor and input your **Gemini API key** ([get one free here](https://aistudio.google.com/)):
```env
GEMINI_API_KEY=AIzaSy...
```

### Step 3: Run the Application 🚀

You can run Shorts Clipper in either interactive Web UI mode or CLI mode.

#### **Option A: Redesigned Web Console (Recommended)**
```bash
python -m shorts_clipper web --port 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

#### **Option B: Command Line Autopilot**
```bash
# Scout trending content and render 3 viral clips automatically
python -m shorts_clipper autopilot --niche twitch --count 3

# Clip a specific video by URL
python -m shorts_clipper clip https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Discover and print trending URLs without rendering
python -m shorts_clipper scout --niche gaming --count 5
```

---

## 🖥️ Web Console

The self-hosted FastAPI web dashboard acts as the unified command center for your viral shorts factory:

*   **Autopilot Launchpad**: Launch full pipelines in one click. Select your target niche (Gaming, Drama, Motivation, Twitch Highlights), target specific channels, customize keyword queries, and toggle YouTube Auto-Upload.
*   **Interactive Clipper Studio**: Paste any URL, view the complete transcript, preview Gemini highlight scores, and manually adjust start/end times before initiating a render.
*   **Clips Library**: Two-tab interactive view separating draft clips from finished posts:
    *   📂 **Ready to Publish**: Local drafts and video previews with direct visibility controls.
    *   🚀 **Published to YouTube**: Live uploaded clips with subscriber growth monitoring and direct links to YouTube Shorts.
*   **Console Settings**: Real-time interactive overrides for your Gemini Key, Whisper model settings, GPU/CPU paths, and rendering presets.
*   **Live Log Terminal**: Real-time streaming logs using Server-Sent Events (SSE) detailing every FFmpeg step, Whisper transcription pass, and AI scoring event.

---

## 🔑 YouTube Data API v3 & OAuth2 Setup

Shorts Clipper supports a browser-redirect OAuth2 flow. This headless-safe approach works out of the box on remote VPS servers, local development nodes, or Docker containers.

### Step 1: Create a Google Cloud Project & Credentials
1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g., `Shorts-Clipper`).
3. Search for the **YouTube Data API v3** in the API library and click **Enable**.
4. Go to **APIs & Services** > **Credentials**.
5. Click **Create Credentials** > **OAuth client ID**.
6. Set the **Application type** to **Desktop application** (or **Web application**).
7. Download the credentials JSON, rename it to `client_secret.json`, and place it in your project's root folder.

### Step 2: Configure Test Users (Fixes the 403 / Access Blocked Error) ⚠️
Because your Google Cloud app is in development status, Google restricts access. **You must explicitly authorize your channel's email address:**
1. In the Google Cloud Console, click the **OAuth consent screen** tab.
2. Scroll down to the **Test users** section.
3. Click **+ ADD USERS**.
4. Enter the Google/Gmail address of the YouTube channel you want to publish to.
5. **Crucial**: Click **Save** at the bottom of the page to apply the settings.

### Step 3: Link Account via the Dashboard
1. Open the Web Console ([http://localhost:8000](http://localhost:8000)).
2. Click the red **Link Account** button on the sidebar.
3. Complete the Google authentication flow. Once allowed, you will be redirected back.
4. **Instant Synchronization**: The sidebar card will instantly show your YouTube profile avatar, channel name, and subscriber count.
5. **Unlink / Logout**: Click the red **Power** disconnect button on your sidebar card to securely delete cached tokens and logout.

---

## 🎨 Premium Web UI Features

Our redesigned dashboard is packed with elite UI/UX improvements to streamline your workflow:

### 🔒 Secure Channel Logout
Disconnect your YouTube channel instantly using the **Power** button in the sidebar card, purging cached local credential tokens.

### 🌍 Dynamic Visibility Settings
Set the audience reach for your clips using the dropdown selectors on any ready video card before sending it to YouTube:
*   🔒 **Private**: (Default) Secure upload for manual description formatting and title review in YouTube Studio.
*   🔗 **Unlisted**: Shared via direct URL link only.
*   🌍 **Public**: Instantly pushed live directly onto the global YouTube Shorts feed.

### 📊 Real-Time Upload Monitor
Painless tracking of background upload tasks with high-precision metrics:
*   **Glowing Progress Bar**: Smoothly updating visual progress indicator.
*   **Dynamic Speed Tracking**: Real-time bandwidth upload velocity (e.g. `3.4 MB/s`).
*   **Smart ETA Estimator**: Dynamically forecasts remaining upload time (e.g. `24s remaining`).

### 📦 Dual-Catalog Library Tabs
Clips slide smoothly between states inside the library:
*   **"Ready to Publish"**: Local draft shorts, preview playback, and visibility dropdown options.
*   **"Published to YouTube"**: Uploaded clips, displaying active subscriber milestones and direct links to live short URLs.

---

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

1.  **Autonomous Scout**: Filters potential content using a view-velocity trending formula, removing duplicates and outdated videos (7-day TTL caching).
2.  **Transcription Pass**: Fetches native captions or performs a rapid, lightweight transcription using local Whisper (`tiny`).
3.  **Gemini AI Evaluation**: Transcripts are passed to **Gemini 2.5 Flash**, evaluating structural retention, high-emotion highlights, and contextual hooks to pick the optimal 30-60 second window.
4.  **Precision Download**: Downloads only the targeted slice (instead of full Gigabyte landscape files) to save bandwidth and compute time.
5.  **Dynamic Geometry Cropping**: Scales and crops video layout to a sleek vertical 9:16 aspect ratio (1080×1920).
6.  **ASS Subtitle Engine**: Generates customized Advanced SubStation Alpha subtitling with high-accuracy word-level karaoke synchronization. Subtitles are burned into the video alongside a **1.15× pacing factor** to remove dead air—all processed in a single FFmpeg call.
7.  **Thumbnail Extraction**: Grabs a high-impact cover thumbnail at 25% of the clip duration.
8.  **Automated Publishing**: Uploads the finished vertical clip to YouTube Shorts with optimized titles, descriptions, and tags.

---

## 🎯 CLI Command Reference

Execute complex pipelines directly from your terminal:

```bash
# ── Autopilot Operations ──────────────────────────────────────────
# Scout and render a single trending clip
python -m shorts_clipper autopilot

# Scout and render 3 trending Twitch highlights
python -m shorts_clipper autopilot --niche twitch --count 3

# Target a specific YouTube channel
python -m shorts_clipper autopilot --channel @JoeRogan

# Scout using customized search keywords
python -m shorts_clipper autopilot --keyword "scientific breakthrough"

# Scout, clip, and instantly publish public Shorts to YouTube
python -m shorts_clipper autopilot --upload

# ── Manual Video Clipping ──────────────────────────────────────────
# Clip a specific video by its direct URL
python -m shorts_clipper clip https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Extract the top 3 viral segments from a single video URL
python -m shorts_clipper clip https://www.youtube.com/watch?v=dQw4w9WgXcQ --count 3

# Clip a video and queue it directly for YouTube upload
python -m shorts_clipper clip https://www.youtube.com/watch?v=dQw4w9WgXcQ --upload

# Specify custom file output paths
python -m shorts_clipper clip https://www.youtube.com/watch?v=dQw4w9WgXcQ --output ./outputs/custom.mp4

# ── Raw Discovery Scouting ──────────────────────────────────────────
# Discover and output one trending video URL
python -m shorts_clipper scout

# Print 5 trending gaming-niche video URLs
python -m shorts_clipper scout --niche gaming --count 5

# ── Web UI Launching ────────────────────────────────────────────────
# Start the web console on localhost:8000
python -m shorts_clipper web

# Bind to a custom host and port for public access
python -m shorts_clipper web --host 0.0.0.0 --port 3000
```

---

## 🐳 Docker Deployment

Run the complete pipeline, FastAPI server, and background worker queue anywhere with a single Docker command.

### 1. Pre-configure Local Directories & Keys
Ensure your API keys and client secrets are present:
```bash
cp .env.example .env
# Edit .env and enter your GEMINI_API_KEY

# Ensure your client_secret.json is in the project root if using YouTube uploading
```

### 2. Build and Launch using Compose
```bash
docker-compose up --build -d
```
The console will boot up and be accessible at **[http://localhost:8000](http://localhost:8000)**.

### Docker Features:
*   Bundles pre-compiled FFmpeg with full libass and standard codecs.
*   Automates package installations, python runtimes, and local dependencies.
*   Binds persistent Docker volumes for `outputs/`, `.cache/`, and local model cache to retain data across restarts.
*   Tailored for headless production VPS deployment (DigitalOcean, Railway, Hetzner, AWS, etc.).

---

## 🧩 Project Structure

```
shorts-clipper/
├── shorts_clipper/
│   ├── api/                   # FastAPI backend endpoints & SSE event streaming
│   ├── ui/                    # Premium dark-mode dashboard (HTML/CSS/JS)
│   ├── core/                  # Global Settings, SQLite workers, logger, schemas
│   ├── pipeline/              # Main orchestrator (runner.py)
│   ├── scout/                 # Niche targeting, trending discovery, and caching
│   ├── providers/             # Gemini 2.5 Flash highlight scoring & API
│   ├── transcription/         # Whisper local transcript generator
│   ├── downloader/            # yt-dlp downloader helper
│   ├── rendering/             # Core FFmpeg geometric crop & scale filters
│   ├── captions/              # ASS subtitle generation & styler
│   ├── render/                # Frame thumbnail extractor
│   ├── cropping/              # Aspect ratio & frame adjustments
│   ├── social/                # YouTube OAuth2 publisher & metadata generation
│   ├── analyze/               # SQLite feedback database & stats analyzer
│   └── utils/                 # Subprocess, network, & path helpers
├── tests/                     # Comprehensive Pytest suite
├── Dockerfile                 # Multi-stage production container configuration
├── docker-compose.yml         # One-click service composition
├── pyproject.toml             # Project packages, dependencies, and Ruff config
└── .env.example               # Template configuration environment
```

---

## 🧪 Testing & Code Quality

Shorts Clipper maintains a strict standard of test coverage and code styles.

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run the complete test suite (40+ unit/integration tests)
python -m pytest tests/ -v

# Perform code quality check (Ruff)
ruff check .

# Validate code formatting
ruff format --check .
```

---

## 🗺️ Roadmap & Achievements

*   `[x]` Multi-pool trending scout with velocity scoring.
*   `[x]` Gemini-powered clip selection with multi-clip support.
*   `[x]` Two-pass FFmpeg pipeline (crop → burn subs + pacing).
*   `[x]` Word-level animated ASS subtitles (3-5x faster than MoviePy loops).
*   `[x]` Redesigned Web Console with dynamic SSE logs.
*   `[x]` SQLite job queue and performance analytics.
*   `[x]` Dynamic YouTube Shorts OAuth2 credentials flow.
*   `[x]` Real-time YouTube upload progress, speed tracking, and ETA metrics.
*   `[x]` Dual-catalog sorting tabs (Drafts vs Live).
*   `[x]` Multi-threaded/Parallel trending scout operations.
*   `[x]` Pre-configured Docker Compose support.
*   `[ ]` TikTok & Instagram Reels auto-publishing.
*   `[ ]` Automated B-Roll video insertion.
*   `[ ]` Scheduled auto-publishing cron jobs.
*   `[ ]` Multi-language caption translations.

---

## 🤝 Contributing

Contributions are welcome! Please review [CONTRIBUTING.md](CONTRIBUTING.md) to understand coding styles, testing compliance, and pull request procedures.

---

## 📄 License

Distributed under the **MIT License**. Check out [LICENSE](LICENSE) for more details.

<div align="center">

**Built with ❤️, Python, and a massive amount of FFmpeg magic.**

</div>

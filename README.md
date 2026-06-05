---
title: Shorts Clipper
emoji: 🎬
colorFrom: red
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

<div align="center">

# 🎬 Shorts Clipper

### **The Enterprise-Grade AI Shorts Factory**

*Scout trending videos → Extract viral highlights → Render vertical crops → Burn animated captions → Auto-publish to YouTube.*

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-40%20passed-22c55e?style=for-the-badge&logo=pytest&logoColor=white)](#-testing-and-linting)
[![Docker Ready](https://img.shields.io/badge/docker-ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](#-docker--cloud-deployment)

---

<p align="center">
  <img src="https://raw.githubusercontent.com/random-or/shorts-clipper/assets/docs/images/dashboard_preview.png" alt="Shorts Clipper Dashboard Preview" width="800px" style="border-radius: 10px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.45);"/>
</p>

</div>

---

## 📖 System Overview & Architecture

**Shorts Clipper** is a production-grade, AI-driven automation pipeline that transforms standard 16:9 landscape videos (podcasts, webinars, gaming streams) into high-retention 9:16 vertical shorts. It automatically transcribes audio, selects viral hooks using AI, renders vertical crops, generates customized animated word-level subtitles, and publishes the final cuts.

### 📐 Component Flow & Architecture

```mermaid
flowchart TD
    %% Styling
    classDef main fill:#0d0e1b,stroke:#00d2ff,stroke-width:2px,color:#fff;
    classDef engine fill:#131427,stroke:#dfb23f,stroke-width:1px,color:#fff;
    classDef external fill:#030408,stroke:#6b7280,stroke-width:1px,stroke-dasharray: 5 5,color:#aaa;
    
    %% Elements
    A[Web Console / CLI Client]:::main
    B[FastAPI Server <br> api/server.py]:::main
    C[(SQLite Job Database <br> core/queue.py)]:::engine
    D[Pipeline Orchestrator <br> pipeline/runner.py]:::main

    %% Pipeline Processes
    subgraph Pipeline [Automated Clipping Pipeline]
        E[1. Trending Scout <br> scout/trending.py]:::engine
        F[2. Smart Downloader <br> downloader/yt_dlp.py]:::engine
        G[3. Audio Transcriber <br> transcription/whisper.py]:::engine
        H[4. Highlight AI Agent <br> providers/gemini.py]:::engine
        I[5. Render Engine <br> rendering/crop.py]:::engine
        J[6. Subtitle Burner <br> captions/generator.py]:::engine
        K[7. YouTube Publisher <br> social/youtube.py]:::engine
    end

    %% External APIs
    YT_API[YouTube Data API]:::external
    GEMINI_API[Google Gemini API]:::external
    WHISPER_LIB[faster-whisper Engine]:::external
    FFMPEG_SYS[FFmpeg & libass]:::external

    %% Connections
    A -->|1. Triggers Job| B
    B -->|2. Writes Status| C
    B -->|3. Launches Task| D
    
    D --> E
    D --> F
    D --> G
    D --> H
    D --> I
    D --> J
    D --> K

    E -->|Scouts Metadata| YT_API
    F -->|Downloads Sections| YT_API
    G -->|Tries Cloud Transcribe| GEMINI_API
    G -.->|Local Fallback| WHISPER_LIB
    H -->|Scores Highlights & Title| GEMINI_API
    I -->|Scale & Center Crop| FFMPEG_SYS
    J -->|Burn ASS Subtitles <br> & Apply 1.15x Speed| FFMPEG_SYS
    K -->|Uploads Short| YT_API

    D -.->|4. Updates Progress| C
    B -.->|5. SSE Live logs & Updates| A
```

---

## 🚀 Key Features

*   **🛡️ Anti-Blocking Web Scraper (New):** Integrated `curl-cffi` browser impersonation (`--impersonate Chrome`) and automated **client-side proxy rotation** supporting multi-proxy pools via `SHORTS_PROXY` environment variables to successfully bypass YouTube cloud IP bans.
*   **🔄 Self-Healing Autopilot Daemon:** Smart scouting queue handles consecutive failures gracefully, implements exponential retry backoff, and automatically falls back to curated viral videos, reusing them when the cache is saturated to guarantee 100% server uptime.
*   **⚙️ Decoupled Job queue:** Database-backed background worker queue powered by SQLite ensures long-running rendering, transcription, and uploads are resilient to web server restarts.
*   **⚡ Piped Encoding & Speedup:** Directs `yt-dlp` output to FFmpeg crops in single-pass runs, applying a **1.15× speedup** during subtitle burn-ins to eliminate double-transcoding overhead and reduce disk writes.
*   **👤 Smart safe-Zone & Face Cropping:** Adjustable horizontal offsets with interactive 9:16 safe-zone indicators. Choose between `Center`, `Left`, or `Right` crops.
*   **🎨 Custom Caption Studio:** Burn stylized word-level animated subtitles. Choose preset themes (e.g., *MrBeast Pop*, *Hormozi Glow*, *Minimal Clean*, *Gold Premium*) or design your own fonts, outline colors, and glow offsets.
*   **🧠 Gemini AI Video Editor:** Google Gemini 2.5 Pro selects high-retention highlights based on **Hook Strength**, **Emotional Peak**, and **Dialogue Flow**, co-writing engaging hooks, titles, and tags.

---

## ⚡ Pipeline Mechanics

### 1. 🔍 Trending Scout
Scans channels, topics, or niches (e.g., *debates*, *tech reviews*). Calculates view velocity scores while maintaining a local cache of already-processed video IDs with a 7-day TTL to avoid duplicates.

### 2. 📥 Smart Downloader
Uses `yt-dlp`'s `--download-sections` flag to download only the designated clip window. Avoids wasteful multi-gigabyte downloads of full hours-long videos.

### 3. 🎙️ Dual-Engine Transcription
Primary transcription runs via Gemini 2.5 Flash for high-speed cloud-based word-level timestamp generation. Automatically falls back to local `faster-whisper` running on CPU or GPU if the cloud API is throttled.

### 4. 🧠 Highlight Analysis
Generates exact crop layouts (`crop_center`, `crop_left`, `crop_right`) and timestamps based on emotional peaks, keeping context and narrative complete.

### 5. 🎬 Burn & Render
Renders crops at `1080x1920` (9:16 aspect ratio), overlaying styled `.ass` captions with FFmpeg's hardware-accelerated subtitle renderer.

---

## 🖥️ Web Console Dashboard

Start the local server to access a fully dark-themed, dashboard interface:

| Panel | Function | Features |
|---|---|---|
| **Autopilot Launchpad** | Zero-touch production | Set a niche/topic, schedule, and let the daemon scout, crop, and upload. |
| **Interactive Studio** | Granular control | Manual URL insertion, highlight scoring preview, real-time safety overlay, and custom typography edits. |
| **Asset Library** | Media Manager | Browse rendered MP4 exports, modify descriptions, and post to YouTube via OAuth2. |

---

## 🛠️ Quick Start

### 📋 Prerequisites
*   **Python 3.11+**
*   **FFmpeg** (compiled with `--enable-libass` support)
*   **Gemini API Key** (from [Google AI Studio](https://aistudio.google.com/))

### ⬇️ Installation

```bash
# 1. Clone repository
git clone https://github.com/random-or/shorts-clipper.git
cd shorts-clipper

# 2. Setup environment
python -m venv env
source env/bin/activate  # Windows: env\Scripts\activate

# 3. Install packages in editable mode
pip install -e .

# 4. Initialize config
cp .env.example .env
```

Open the `.env` file and input your variables. At minimum, you must supply `GEMINI_API_KEY`.

### 🚀 Running the Application

#### **1. Launch the Web Console**
```bash
python -m shorts_clipper web --host 127.0.0.1 --port 8000
# Open http://localhost:8000 in your browser
```

#### **2. CLI Commands**
*   **Clip specific video:**
    ```bash
    python -m shorts_clipper clip "https://youtube.com/watch?v=VIDEO_ID" --count 1
    ```
*   **Run Autopilot:**
    ```bash
    python -m shorts_clipper autopilot --niche "motivation" --count 2 --upload
    ```
*   **Scout trends:**
    ```bash
    python -m shorts_clipper scout --niche "gaming" --count 5
    ```

---

## ⚙️ Configuration Reference (`.env`)

| Variable | Default Value | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(None)* | **Required.** Your Google Gemini API key. |
| `SHORTS_PROXY` | *(None)* | Optional. Comma-separated list of HTTP proxies (`http://user:pass@ip:port`). |
| `SHORTS_WHISPER_MODEL` | `tiny.en` | Local Whisper model size (`tiny.en`, `base.en`, `small.en`, `large-v3`). |
| `SHORTS_WHISPER_DEVICE` | `cpu` | Device for local Whisper running (`cpu` or `cuda`). |
| `SHORTS_VIDEO_CODEC` | `libx264` | Video encoder encoder: standard `libx264` or hardware GPU `h264_nvenc`. |
| `SHORTS_ENABLE_GPU` | `false` | Enable hardware acceleration toggles for both Whisper and FFmpeg. |
| `SHORTS_OUTPUT_DIR` | `./outputs` | Folder where generated vertical MP4 clips are stored. |

---

## 🔑 YouTube Upload Configuration

To authorize direct-to-YouTube publishing:
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the **YouTube Data API v3** in your project.
3. Create OAuth 2.0 Credentials (select "Desktop app" as application type).
4. Download the credentials JSON, rename it to `client_secret.json`, and place it in the root folder of this project.
5. Launch the Web UI, click the sidebar avatar, and connect your channel.

---

## 🐳 Docker & Cloud Deployment

### 1. Local Container
```bash
# Build
docker build -t shorts-clipper .

# Run
docker run -p 8000:7860 --env-file .env shorts-clipper
```

### 2. Hugging Face Spaces Deployment (Free Cloud Hosting)
Shorts Clipper is optimized for Hugging Face Spaces out of the box:
1. Create a **New Space** on [Hugging Face](https://huggingface.co/new-space).
2. Select **Docker** as the SDK (use the **Blank** template).
3. In your Space's **Settings**, add your secrets under **Variables and secrets**:
   * `GEMINI_API_KEY` (Required)
   * `SHORTS_PROXY` (Highly Recommended to bypass cloud rate limits. Format: `http://user:pass@ip:port,http://user2:pass2@ip2:port2,...`)
4. Push the codebase (or upload the files) to the Hugging Face Space repository. It will automatically build and launch on port `7860`.

---

## 🖥️ Production Daemonizing (systemd)

To run the web service persistently in production:

Create `/etc/systemd/system/shorts-clipper.service`:
```ini
[Unit]
Description=Shorts Clipper Web Console Service
After=network.target

[Service]
User=random
WorkingDirectory=/home/random/shorts-clipper
ExecStart=/home/random/shorts-clipper/env/bin/python -m shorts_clipper web --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
EnvironmentFile=/home/random/shorts-clipper/.env

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable shorts-clipper.service
sudo systemctl start shorts-clipper.service
```

---

## ❓ Troubleshooting & FAQ

### **Q: FFmpeg crashes with `No such filter: 'ass'`**
* **Cause:** Your system FFmpeg binary was not compiled with `libass` subtitle renderer support.
* **Solution:**
  * **Ubuntu/Debian:** `sudo apt-get update && sudo apt-get install ffmpeg`
  * **macOS (Homebrew):** `brew install ffmpeg`
  * **Windows:** Download a full shared build containing extra filters from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/).

### **Q: Subtitles burn successfully but text characters are missing/blank**
* **Cause:** The host environment lacks basic Arial/Montserrat fonts referenced in the caption styler.
* **Solution:**
  * **Ubuntu/Debian:** 
    ```bash
    sudo apt-get install ttf-mscorefonts-installer fontconfig
    sudo fc-cache -fv
    ```

### **Q: Local Whisper execution runs out of memory (OOM)**
* **Cause:** Running larger Whisper models (like `small` or `large-v3`) on CPU or systems with low VRAM.
* **Solution:** Set `SHORTS_WHISPER_MODEL=tiny.en` in `.env` for standard CPU execution, or enable GPU configurations (`SHORTS_WHISPER_DEVICE=cuda`, `SHORTS_ENABLE_GPU=true`).

---

## 🧪 Testing and Linting

Verify formatting and test suites pass before pushing updates:

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Code style checks
ruff check .
ruff format --check .
```

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

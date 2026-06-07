---
title: Shorts Clipper
emoji: 🎬
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

<div align="center">

# 🎬 Shorts Clipper

### **Automated AI Video Highlight & Clipping Pipeline**

*Scout trending videos → Extract viral highlights → Render vertical crops → Burn animated captions → Auto-publish to YouTube.*

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge)](LICENSE)
[![Docker Ready](https://img.shields.io/badge/docker-ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](#-docker-deployment)

</div>

---

## 📖 Overview

**Shorts Clipper** is a production-grade, AI-driven automation pipeline designed to transform standard 16:9 landscape videos (e.g., podcasts, webinars, and streams) into highly engaging 9:16 vertical shorts. 

The system leverages Google Gemini for intelligent highlight detection, Whisper for accurate timestamped transcriptions, and FFmpeg for hardware-accelerated rendering and dynamic subtitle burn-ins.

---

## ✨ System Features

* **Intelligent Highlight Detection:** Uses Gemini 2.5 to analyze transcriptions for emotional peaks, strong hooks, and logical dialogue flow, ensuring clips maintain narrative context.
* **Anti-Blocking Download Engine:** Integrates `curl-cffi` browser impersonation to bypass YouTube's anti-bot detection and `429 Too Many Requests` rate-limiting.
* **Dynamic Crop & Subtitle Burn-in:** Automatically reframes 16:9 videos into 9:16 vertical orientation, applying customizable word-level animated subtitles via FFmpeg `.ass` generation.
* **Autonomous Scouting Daemon:** Operates an intelligent polling queue to scout trending videos within specific niches, preventing duplicate processing and falling back gracefully on API errors.
* **Database-Backed Task Queue:** Background worker processes are managed via an SQLite-backed queue, ensuring long-running render jobs are fully resilient.
* **Direct YouTube Integration:** OAuth 2.0 integration allows the pipeline to auto-publish rendered clips directly to your YouTube channel as Shorts.

---

## 🛠️ Installation & Setup

### Prerequisites
- **Python 3.11** or higher
- **FFmpeg** (must be compiled with `--enable-libass` support)
- **Google Gemini API Key**

### 1. Local Environment Setup

```bash
# Clone the repository
git clone https://github.com/random-or/shorts-clipper.git
cd shorts-clipper

# Create and activate a virtual environment
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate

# Install the application and dependencies
pip install -e .
```

### 2. Configuration

Copy the example environment variables file and insert your API keys:

```bash
cp .env.example .env
```

**Required `.env` Variables:**
* `GEMINI_API_KEY`: Your Google Gemini API key.
* `SHORTS_PROXY` (Optional): A comma-separated list of HTTP proxies to rotate through.
* `SHORTS_WHISPER_MODEL`: The local Whisper model size (default: `tiny.en`).

---

## 🚀 Usage

### Starting the Web Console

Launch the interactive web dashboard for monitoring jobs and initiating manual pipelines.

```bash
python -m shorts_clipper web --host 127.0.0.1 --port 8000
```
Navigate to `http://127.0.0.1:8000` in your browser.

### Command Line Interface

The application can also be operated entirely head-less via the CLI:

**1. Clip a specific video:**
```bash
python -m shorts_clipper clip "https://youtube.com/watch?v=VIDEO_ID" --count 1
```

**2. Run the Autopilot (Scout & Clip):**
```bash
python -m shorts_clipper autopilot --niche "technology" --count 2 --upload
```

**3. Scout for trending videos:**
```bash
python -m shorts_clipper scout --niche "gaming" --count 5
```

---

## 🐳 Docker Deployment

For containerized environments, you can easily deploy Shorts Clipper using Docker.

```bash
# Build the Docker image
docker build -t shorts-clipper .

# Run the container
docker run -p 8000:7860 --env-file .env shorts-clipper
```

---

## 📄 License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

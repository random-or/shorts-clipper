# 🎬 Shorts Clipper

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Shorts Clipper** is an experimental, fully automated pipeline that searches for trending YouTube videos, downloads them, finds the best moments, and renders **9:16 vertical shorts with dynamic burned-in subtitles**—ready to be uploaded to TikTok, YouTube Shorts, or Instagram Reels.

> **⚠️ EXPERIMENTAL WARNING:** The core infrastructure (downloading, vertical cropping, transcription, and FFmpeg rendering) works flawlessly. However, the **AI Highlight Selection engine is currently experimental**. The AI may sometimes struggle to select the absolute most viral or engaging moment. Expect accurate rendering, but double-check the AI's content choices!

---

## 🚀 What It Does

1. **Scouts Content:** Searches YouTube for videos in a specific niche (e.g., "tech", "finance") using the YouTube Data API and `yt-dlp`.
2. **Filters & Selects:** Analyzes transcripts to find high-retention segments (using Google Gemini).
3. **Downloads & Transcribes:** Downloads the video securely and extracts/transcribes the audio (falling back to local Whisper AI if YouTube subtitles are missing).
4. **Renders:**
- 📱 **Multi-Platform Publishing**: Automatically distribute rendered clips to YouTube Shorts and Instagram Reels with a single execution.
- ⚙️ **Publishing Engine**: A highly extensible registry-based publishing architecture. Easy to add TikTok or Facebook Reels in the future.
- 💬 **Smart Subtitles**: Burns animated, word-level subtitles into the video.
5. **(Optional) Publishes:** Can upload the finished clip directly to your YouTube channel using OAuth.

---

## ⚙️ Prerequisites

Before installing, you must have the following system dependencies installed:

* **Python 3.10+**
* **FFmpeg** (Required for video rendering)
  * **Ubuntu/Debian:** `sudo apt-get install ffmpeg`
  * **macOS:** `brew install ffmpeg`
  * **Windows:** Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) and add it to your system PATH.

---

## 🛠️ Installation

**1. Clone the repository:**
```bash
git clone https://github.com/random-or/shorts-clipper.git
cd shorts-clipper
```

**2. Create and activate a virtual environment:**
```bash
# macOS / Linux
python3 -m venv env
source env/bin/activate

# Windows
python -m venv env
env\Scripts\activate
```

**3. Install dependencies:**
```bash
pip install -r requirements.txt
```

---

## 🔑 Configuration & API Keys

To use Shorts Clipper, you need a few free API keys. Copy the `.env.example` file to create your own `.env` file:

```bash
cp .env.example .env
```

Open the `.env` file and fill in the following keys:

### 1. Google Gemini API Key (Required for Highlight Selection)
* **Get it here:** [Google AI Studio](https://aistudio.google.com/app/apikey)
* **Cost:** Free tier available.

### 2. YouTube Data API v3 Key (Required for Video Discovery)
* **Get it here:** [Google Cloud Console - YouTube API](https://console.cloud.google.com/apis/library/youtube.googleapis.com)
* Click **Enable**, then go to **Credentials** -> **Create Credentials** -> **API Key**.

### 3. YouTube OAuth Client ID (Required for Auto-Uploading)
*If you only want to generate clips locally, you can skip this step.*
* **Get it here:** [Google Cloud Console - Credentials](https://console.cloud.google.com/apis/credentials)
* Click **Create Credentials** -> **OAuth client ID**.
* Select **Desktop App**.
* Download the resulting JSON file.
* Rename it to `client_secret.json` and place it directly in the root `shorts-clipper` folder.

---

## 💻 Usage

Make sure your virtual environment is activated (`source env/bin/activate`), then use the CLI tool or the Web UI!

### Command Line Interface (CLI)

**1. Scout a niche:**
Search for trending video ideas without downloading them.
```bash
python -m shorts_clipper scout --niche "tech" --keyword "AI"
```

**2. Clip a specific video:**
Pass a YouTube URL directly to generate a vertical short.
```bash
python -m shorts_clipper clip https://youtu.be/VIDEO_ID
```

**3. Autopilot Mode:**
Run the entire pipeline automatically (Scout -> Download -> Transcribe -> Render).
```bash
python -m shorts_clipper autopilot --niche "science" --count 1
```

> **Where do my videos go?** 
> Finished `.mp4` clips and thumbnails are saved automatically in the `outputs/` folder!

### Web UI Dashboard

Prefer a graphical interface? You can launch the local web dashboard:
```bash
python -m shorts_clipper web
```
*(Open your browser to the URL printed in the terminal to interact with the visual dashboard).*

---

## 📁 Project Structure

* `shorts_clipper/` - Core Python engine (scouting, rendering, API logic).
* `tests/` - Pytest validation suite.
* `outputs/` - Generated 9:16 `.mp4` clips, `.ass` subtitles, and thumbnails.
* `env/` - Your local Python environment.

---

## 🤝 Roadmap & Known Limitations

* **Highlight AI:** The AI frequently struggles to pick the climax of a story. We are actively working on improving the "Attention Engine" to better recognize hooks, pacing, and emotional payoff.
* **Quota Exhaustion:** Heavy users might hit Google Gemini's free tier limits quickly.

---

*Built for creators to scale short-form content seamlessly.*

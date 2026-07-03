# Shorts Clipper V3.2

Welcome to **Shorts Clipper**, an enterprise-grade automated pipeline designed to transform long-form content (e.g., podcasts, interviews) into highly viral, perfectly paced, and beautifully captioned short-form videos for platforms like YouTube Shorts and Instagram Reels.

## 🚀 Overview

Shorts Clipper is a fully automated, local-first engine that handles every step of the short-form video creation process:
1. **Discovery (Scout V2):** Finds highly trending videos across specific niches.
2. **Editorial Engine:** A deterministic, local evaluation engine that identifies the most engaging hooks and clips based on speech patterns, pacing, and emotional context.
3. **Transcription & Rendering:** Uses local `faster-whisper` for precise transcription and `ffmpeg` for flawless vertical cropping and subtitle burning.
4. **Publishing:** Automatically uploads the finished product to YouTube Shorts and Instagram Reels with SEO-optimized titles and descriptions.

With **V3.2**, the platform transitions to a deterministic, local-first **Editorial Engine**, demoting expensive and rate-limited LLMs (like Gemini) to a supporting role for semantic validation and metadata generation, drastically reducing API costs and increasing processing speed.

---

## 🧠 Architecture at a Glance

The pipeline operates in 6 distinct stages:

1. **Scout V2 Discovery:** Scrapes trending metrics to identify videos with high momentum and engagement.
2. **Feature Extraction:** Downloads rough subtitles and extracts features (words per second, pauses, question density).
3. **Editorial Engine (Local-First):** Evaluates clips using a suite of plugins (Hook, Silence, Context, Emotion, Length) to find the perfect segment deterministically, without relying on LLMs.
4. **Precision Cropping:** Uses `yt-dlp` to download only the high-quality segment of the video, and `ffmpeg` to crop it vertically (1080x1920).
5. **Subtitle Burning:** Utilizes `faster-whisper` for word-level transcription and `ffmpeg` to burn highly-stylized ASS subtitles onto the video with dynamic pacing adjustments.
6. **Publishing Engine:** Authenticates and dispatches the final video to YouTube and Instagram.

---

## ⚙️ Installation

### Prerequisites
- Python 3.10+
- `ffmpeg` installed and available in your system's PATH.
- (Optional but Recommended) NVIDIA GPU with CUDA support for accelerated local transcription.

### Setup
1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/shorts-clipper.git
   cd shorts-clipper
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Install FFmpeg (if not already installed):**
   - **Ubuntu/Debian:** `sudo apt install ffmpeg`
   - **MacOS:** `brew install ffmpeg`
   - **Windows:** Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or use `winget install ffmpeg`.

---

## 🔧 Configuration & API Keys

Shorts Clipper requires several API keys to operate at full capacity. 

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and fill in the required values:

- **Gemini API Key (`GEMINI_API_KEY`):** Used for semantic relevance gating and generating SEO metadata. Get it from [Google AI Studio](https://aistudio.google.com/).
- **YouTube OAuth (`YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`):** Required for the YouTube Publisher. Set up a project in Google Cloud Console with the YouTube Data API v3 enabled.
- **Instagram Credentials:** Provide your `INSTAGRAM_USERNAME` and `INSTAGRAM_PASSWORD` (or `INSTAGRAM_SESSION_ID`) for automated Reel uploads.

---

## 🛠 Usage

### 1. The Vanguard Console (UI)
The easiest way to monitor and interact with the system is via the Vanguard Console:
```bash
uvicorn api.server:app --reload
```
Navigate to `http://localhost:8000` to view the live dashboard and queue.

### 2. Autopilot Mode (CLI)
To run the full end-to-end pipeline continuously:
```bash
python -m shorts_clipper.cli autopilot --niche "tech podcast"
```

### 3. Worker Queue
To run a decoupled worker that processes jobs from the SQLite queue:
```bash
python -m shorts_clipper.core.worker
```

---

## 🤝 Contributing
Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, the local-first architectural philosophy, and the process for submitting pull requests.

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

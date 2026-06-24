# Shorts Clipper (Experimental)

An automated pipeline for discovering YouTube videos, downloading them, and rendering 9:16 vertical shorts with burned-in subtitles.

> **⚠️ EXPERIMENTAL WARNING:** The core infrastructure (downloading, cropping, rendering, API integrations) is fully functional. However, the **Attention Engine and Highlight Selection are fundamentally broken**. The system currently struggles to select the most engaging or viral moments from source videos. Do not expect production-ready highlight curation.

## What It Does
Shorts Clipper automates the mechanical process of creating short-form content. It can accept a YouTube keyword, locate a video, transcribe the audio, extract a 20-60 second clip, crop it to a vertical aspect ratio, and burn dynamic word-level subtitles onto the video using FFmpeg.

## Architecture

```
SCOUT ENGINE
  │
  ├── Discovery ─────── YouTube API / yt-dlp search
  ├── Filtering ─────── Duration, age, views, language
  ├── Selection ─────── Evaluates candidates (Currently inaccurate)
  │
  └── Clip Pipeline
        ├── Download ── yt-dlp with anti-ban
        ├── Transcribe ─ Whisper (fallback if no subs)
        ├── Render ──── FFmpeg 9:16 crop + subtitle burn
        └── Publish ─── YouTube OAuth upload
```

## Verified Features

- Automated content discovery via YouTube Data API and yt-dlp.
- Configurable hard-filtering (duration, views, age, language).
- Subtitle extraction and local Whisper transcription fallback.
- 9:16 vertical video cropping.
- Single-pass FFmpeg rendering with animated word-level `.ass` subtitles.
- Basic YouTube OAuth upload capability.
- CLI and Web UI dashboard.

## Installation

```bash
git clone https://github.com/random-or/shorts-clipper.git
cd shorts-clipper
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

**System Dependencies:**
FFmpeg is required for video rendering.
- Ubuntu/Debian: `sudo apt-get install ffmpeg`
- macOS: `brew install ffmpeg`

## Configuration

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```
2. Add your **Gemini API Key** from Google AI Studio.
3. Add your **YouTube Data API v3 Key** from Google Cloud Console.
4. Set up an OAuth 2.0 Client ID in Google Cloud Console and download the `client_secret.json` file into the root directory (Required for YouTube uploads).

## Running Locally

**CLI Commands:**
```bash
# Scout: Search for a video based on a niche
python -m shorts_clipper scout --niche "tech" --keyword "AI"

# Clip: Process a specific YouTube URL
python -m shorts_clipper clip https://youtu.be/VIDEO_ID

# Autopilot: Search, clip, and render in one step
python -m shorts_clipper autopilot --niche "science" --count 1
```

**Web UI:**
Launch the background FastAPI dashboard:
```bash
python -m shorts_clipper web
```

## Example Workflow

```bash
# 1. Start an autopilot job
python -m shorts_clipper autopilot --niche "history" --keyword "rome"

# 2. Wait for downloading, transcription, and FFmpeg rendering.
# Output will be generated in the outputs/ directory:
# outputs/clip_YYYYMMDD_HHMMSS.mp4
```

## Project Structure
* `shorts_clipper/` - Core Python application module.
* `tests/` - Unit and integration tests.
* `outputs/` - Generated `.mp4` clips, thumbnails, and SQLite cache databases.
* `docs/` - System documentation.

## Known Limitations

1. **Highlight Selection:** The system routinely fails to pick the climax or most engaging segment of a video. It will often select setups without payoffs.
2. **Quota Exhaustion:** The pipeline is heavily reliant on Gemini API free tiers, which frequently exhaust and cause the system to fall back to less reliable local scoring.
3. **Secret Management:** OAuth configuration requires manual setup of `client_secret.json` which is complex for new users.

## Roadmap
- Fix the core Attention Engine to reliably identify story peaks and emotional climaxes.
- Reduce dependency on remote LLM APIs for rapid candidate evaluation.
- Improve OAuth onboarding flow.

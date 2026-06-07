# Shorts Clipper

AI-powered video clipping pipeline that automatically extracts, processes, subtitles, and prepares short-form content for TikTok, Reels, and YouTube Shorts.

---

## Overview

Content creators and media agencies face a massive time sink when attempting to repurpose long-form videos (podcasts, streams, webinars) into highly engaging vertical short-form content. Manual editing requires hours of scrubbing, transcription, layout reframing, and subtitle synchronization.

**Shorts Clipper** solves this by fully automating the pipeline. It intelligently scouts trending topics, securely bypasses bot detection to ingest the raw footage, utilizes Gemini AI to locate emotionally resonant hooks, and leverages FFmpeg to reframe and burn stylized subtitles in a highly optimized single-pass render.

It is built for developers, agencies, and creators who need a scalable, API-first, self-healing pipeline capable of running completely on autopilot.

---

## Key Features

*   **Intelligent Highlight Detection**: Gemini 2.5 analyzes transcriptions to pinpoint exact timestamps for high-retention clips based on emotional peaks and dialogue flow.
*   **Anti-Blocking Download Engine**: Utilizes `curl-cffi` to impersonate standard browsers and bypass YouTube's strict `429 Too Many Requests` rate limiting.
*   **Single-Pass Subtitle Burn-In**: Renders the 9:16 vertical crop, applies 1.15× speed pacing, and burns word-level `.ass` animated subtitles all within a single FFmpeg execution to minimize resource cost.
*   **Persistent SQLite Task Queue**: Robust, database-backed background worker queue ensures long-running transcoding and upload jobs survive server restarts.
*   **Dual-Engine Transcription**: Employs `faster-whisper` for offline precision transcription with selectable models (`tiny.en` to `large-v3`) and hardware acceleration support.
*   **YouTube OAuth Publisher**: Connects securely via Google OAuth 2.0 to upload rendered clips directly to a designated YouTube channel.
*   **Autonomous Scout Daemon**: Auto-discovers trending videos based on targeted niches, caching historical lookups (TTL up to 90 days) to prevent duplicate processing.

---

## Demo

![Web UI Dashboard Placeholder](https://via.placeholder.com/800x450.png?text=Vanguard+Clipper+Web+Console)

*(Vanguard Clipper Web Console showing active background tasks, SQLite job queue, and clip studio)*

---

## Architecture Overview

```mermaid
flowchart TD
    A[Web Console / CLI Client] -->|Triggers Job| B[FastAPI Backend]
    B -->|Writes State| C[(SQLite Job Queue)]
    
    subgraph Background Worker Pipeline
        D[Scout Engine] --> E[Anti-Ban Downloader yt-dlp + curl-cffi]
        E --> F[Transcriber faster-whisper]
        F --> G[Highlight AI Gemini 2.5]
        G --> H[FFmpeg Single-Pass Render crop + ASS burn + pacing]
        H --> I[YouTube OAuth Uploader]
    end
    
    B -.->|Polls DB| Background Worker Pipeline
    C -.->|Maintains State| Background Worker Pipeline
```

---

## Processing Pipeline

1.  **Input Ingestion**: The user or the autonomous scout provides a 16:9 YouTube video URL.
2.  **Rough Transcription**: If native subtitles are absent, the downloader grabs a 5-minute audio sample and runs a fast Whisper pass to generate a base transcript.
3.  **AI Clip Selection**: The transcript is forwarded to Gemini, which analyzes narrative structure and scores moments to return exact timestamp windows and layout recommendations.
4.  **Precision Transcription**: The specific micro-clip is downloaded at full quality. A high-accuracy Whisper pass generates exact word-level timings for subtitle generation.
5.  **Video Operations (Single-Pass)**: The system dynamically generates an Advanced SubStation Alpha (`.ass`) file for styled captions. FFmpeg crops the video to 9:16 and burns the subtitles directly into the video stream while applying a 1.15× speed pacing.
6.  **Output Generation**: The final `mp4` is saved alongside a sidecar `.json` metadata file containing auto-generated titles, descriptions, and hashtags. Optionally, the pipeline initiates a direct YouTube upload.

---

## Tech Stack

| Category         | Technology |
| ---------------- | ---------- |
| Language         | Python 3.11+ |
| Framework        | FastAPI, Uvicorn |
| AI / LLM         | Google Gemini (`google-genai`), `faster-whisper` |
| Video Processing | FFmpeg, `yt-dlp` |
| Database         | SQLite (WAL mode) |
| Infrastructure   | Docker, `curl-cffi` (TLS Impersonation) |

---

## Installation

### Linux / macOS

```bash
# 1. Clone the repository
git clone https://github.com/random-or/shorts-clipper.git
cd shorts-clipper

# 2. Setup virtual environment
python -m venv env
source env/bin/activate

# 3. Install dependencies
pip install -e .

# 4. Initialize configuration
cp .env.example .env
```

### Windows

```powershell
git clone https://github.com/random-or/shorts-clipper.git
cd shorts-clipper
python -m venv env
.\env\Scripts\activate
pip install -e .
copy .env.example .env
```

---

## Configuration

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `GEMINI_API_KEY` | Yes | Google Gemini API Key for highlight extraction. |
| `SHORTS_PROXY` | No | Comma-separated proxies (`http://user:pass@ip:port`) to bypass rate limits. |
| `SHORTS_ENABLE_GPU` | No | Enable hardware acceleration for Whisper and FFmpeg (`true`/`false`). |
| `SHORTS_WHISPER_MODEL` | No | Model size for Whisper (default: `tiny.en`). |
| `SHORTS_WHISPER_DEVICE` | No | Target execution device (`cpu` or `cuda`). |
| `SHORTS_VIDEO_CODEC` | No | Output video codec (default: `libx264`, or `h264_nvenc` if GPU enabled). |

---

## Usage

### Web Console
Launch the FastAPI server and interactive dashboard:
```bash
python -m shorts_clipper web --host 127.0.0.1 --port 8000
```

### CLI Execution
Run the complete pipeline on a target video:
```bash
python -m shorts_clipper clip "https://youtube.com/watch?v=YOUR_ID" --count 2 --upload
```

Run the autopilot daemon to find trending content and process it:
```bash
python -m shorts_clipper autopilot --niche "technology" --count 1
```

---

## CLI Reference

### `clip`
Extract clips from a specific video.
*   **Syntax**: `python -m shorts_clipper clip <url> [options]`
*   **Options**:
    *   `-c, --count <int>`: Number of clips to extract.
    *   `-o, --output <path>`: Specific output file path.
    *   `--upload`: Immediately upload the rendered clips to YouTube.

### `autopilot`
Automatically scout trending videos and execute the clipping pipeline.
*   **Syntax**: `python -m shorts_clipper autopilot [options]`
*   **Options**:
    *   `--niche <string>`: Target a specific content niche.
    *   `--channel <string>`: Target a specific channel.
    *   `-c, --count <int>`: Number of clips to extract.
    *   `--upload`: Automatically upload results.

### `scout`
Search for trending links without clipping.
*   **Syntax**: `python -m shorts_clipper scout [options]`

---

## API Reference

### Endpoints

*   `GET /api/jobs`
    List all background tasks from the SQLite queue.
*   `DELETE /api/jobs/{job_id}`
    Cancel and remove a pending or active job.
*   `GET /api/clips`
    Retrieve metadata and paths for all successfully generated clips.
*   `POST /api/clips/{clip_name}/publish`
    Push a locally rendered clip to the authenticated YouTube channel.
*   `POST /api/clips/{clip_name}/autogen-title`
    Re-run the transcript through Gemini to generate new viral titles and metadata.
*   `GET /api/youtube/connect`
    Generates the OAuth 2.0 URL to link a YouTube account.

---

## Project Structure

```text
shorts_clipper/
├── api/          # FastAPI server, REST endpoints, and SSE logging
├── captions/     # Advanced SubStation Alpha (.ass) generator and styling logic
├── core/         # SQLite queue, data models, exception handling, and settings
├── downloader/   # Wrapper for yt-dlp with curl-cffi impersonation
├── pipeline/     # The primary orchestration brain (runner.py)
├── providers/    # API integrations (Gemini for highlight detection)
├── rendering/    # FFmpeg crop and processing logic
├── scout/        # Intelligent polling and caching for trending topics
├── social/       # YouTube Data API upload integration
└── transcription/# faster-whisper word-level timings
```

---

## Engineering Decisions

*   **SQLite for Job Queuing**: Chose SQLite (in WAL mode) over Redis/Celery to remove external dependencies while retaining high durability for long-running rendering tasks. If the FastAPI process dies, the worker recovers gracefully.
*   **`curl-cffi` Injection**: By hijacking `yt-dlp`'s underlying HTTP layer with TLS fingerprint impersonation, the system successfully routes around YouTube's aggressive bot-detection schemas without immediately requiring expensive residential proxies.
*   **Single-Pass FFmpeg Rendering**: Instead of rendering a crop, re-encoding for 1.15× speed, and re-encoding again for subtitles, the pipeline injects the `.ass` payload and pacing parameters into a single complex filtergraph. This drastically reduces CPU overhead and avoids generation loss.

---

## Performance

*   **Transcription Bottlenecks**: Utilizing `tiny.en` on CPU allows processing to remain relatively fast, but utilizing the optional CUDA configurations (`SHORTS_ENABLE_GPU=true`) reduces transcription time by up to 80%.
*   **Optimized Downloading**: By leveraging `yt-dlp`'s `--download-sections` argument, the system only downloads the specific timestamp bounds required for the micro-clip rather than wasting gigabytes of bandwidth on the entire 2-hour podcast.

---

## Reliability

*   **Resilient Fallbacks**: If the Gemini API hits a rate limit or fails, the pipeline logs the error into the database job tracker and updates the Web UI in real-time. The Autopilot mode uses exponential backoff and rotates through keyword variations to guarantee 100% uptime.
*   **Stateful Error Handling**: Every stage of the pipeline updates the SQLite queue, ensuring users are precisely aware of whether a job failed during transcription, AI analysis, or rendering.

---

## Security

*   **OAuth Management**: Client secrets and pickled OAuth tokens are strictly ignored in `.gitignore` and handled safely inside the `.cache` directory.
*   **Secrets Exposure**: All keys are tightly scoped via `.env` injection managed through `pydantic`-style settings dataclasses, ensuring no tokens are ever hardcoded or printed in standard logging output.

---

## Testing

The project uses `pytest` for unit testing.

```bash
# Run the test suite
pytest

# Enforce formatting and linting
ruff format .
ruff check .
```

---

## Deployment

### Docker Deployment

A `Dockerfile` is provided for immediate containerized execution.

```bash
# Build
docker build -t shorts-clipper .

# Run with local environment variables mapped
docker run -p 8000:7860 --env-file .env shorts-clipper
```
*Note: Ensure the mapped volume includes the outputs and `.cache` directory for database and OAuth persistence.*

---

## Roadmap

*   Add local LLM support via Ollama for entirely offline highlight detection.
*   Implement TikTok and Instagram Reels publishing integrations.
*   Extend `.ass` caption generation to include multi-speaker color-coding.

---

## Contributing

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m 'feat: Add amazing feature'`).
4. Ensure `pytest` and `ruff` pass.
5. Push to the branch (`git push origin feature/amazing-feature`).
6. Open a Pull Request.

---

## License

Distributed under the MIT License. See `LICENSE` for more information.

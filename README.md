# 🎬 Shorts Clipper

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 1. Project Overview
Shorts Clipper is an **Autonomous Content Intelligence System**. It is a fully automated, experimental pipeline that searches for trending YouTube videos, downloads them, finds the highest-retention moments using AI, and renders **9:16 vertical shorts with dynamic burned-in subtitles**. It is built for scale, enabling unattended discovery, editing, and publishing directly to YouTube Shorts and Instagram Reels.

## 2. Features
- **Intelligent Scouting**: Searches for trending videos using the YouTube Data API and `yt-dlp` based on niche and momentum.
- **AI Highlight Extraction**: Analyzes transcripts with Google Gemini to identify the most engaging and viral segments.
- **Automated Rendering**: Precision clipping, 9:16 vertical cropping, and 1.15x pacing using FFmpeg.
- **Dynamic Subtitles**: Burns in animated, word-level `.ass` subtitles automatically.
- **Multi-Platform Publishing**: Extensible registry-based engine that automatically distributes to YouTube Shorts and Instagram Reels (via official Meta Graph API).
- **Production-Ready Reliability**: Built with circuit breakers, retry mechanisms, and cache-aware fallbacks for uninterrupted autonomous execution.

## 3. Architecture Overview
Shorts Clipper is designed around a multi-stage, modular pipeline:
1. **Scout Module**: Discovers trending content and filters for suitability (e.g., english language, recency).
2. **Transcription Engine**: Uses native YouTube subtitles or falls back to local `faster-whisper`.
3. **AI Extractor**: Passes transcripts to Gemini to reason about the best hooks and narrative arcs.
4. **Editorial Finisher**: Downloads the micro-clip and snaps precise clip boundaries to audio segments.
5. **Rendering Pipe**: Uses FFmpeg for hardware-accelerated video formatting and subtitle burn-in.
6. **Publishing Registry**: Uploads final assets and metadata asynchronously.

## 4. Complete Pipeline Flow
`Discover → Understand → Reason → Select → Edit → Render → Publish`

1. **Discover**: Scout searches niche keywords for trending videos.
2. **Understand**: Fetch or transcribe audio to text.
3. **Reason**: LLM scores segments for Context, Hook, Curiosity, and Standalone Understanding.
4. **Select**: Highest scoring segment is selected.
5. **Edit**: High-precision boundaries are created using forced-alignment.
6. **Render**: Video is cropped, resized, and subtitled.
7. **Publish**: The resulting clip is uploaded to configured social platforms.

## 5. Why this project exists
Shorts Clipper was built to test the limits of Autonomous AI Agents in content creation. It is no longer just "an AI clipper"; it is an exercise in building a robust, self-healing system capable of functioning without human intervention for 10,000 creators simultaneously.

## 6. Reliability & Production Features
- **Circuit Breakers**: Prevents cascading failures when external APIs (like YouTube or Gemini) go down.
- **Retry Logic**: Injectable, backoff-aware retries for network calls and API quota limits (429s).
- **Cache-aware Fallbacks**: Subtitles and scout reports are cached locally in SQLite to survive crashes and avoid duplicate processing.
- **Graceful Degradation**: If an LLM provider fails completely, the system falls back to heuristic-based or regex-based clipping.
- **Self-hosted Instagram Publishing**: Direct integration with the Meta Graph API.
- **Worker Architecture**: Concurrency-safe SQLite queues to handle multiple publishing jobs asynchronously.

## 7. Installation

**Prerequisites:**
* **Python 3.11+**
* **FFmpeg** (Required for video rendering)
  * Ubuntu/Debian: `sudo apt-get install ffmpeg`
  * macOS: `brew install ffmpeg`

**Setup:**
```bash
git clone https://github.com/random-or/shorts-clipper.git
cd shorts-clipper
python3 -m venv env
source env/bin/activate  # Windows: env\Scripts\activate
pip install -r requirements.txt
```

## 8. Environment Variables
Copy `.env.example` to `.env` and configure:

```env
# AI Providers
GEMINI_API_KEY=your_key
# OPENAI_API_KEY=your_key (Optional)
# ANTHROPIC_API_KEY=your_key (Optional)

# API & Platform Auth
YOUTUBE_API_KEY=your_key
IG_ACCESS_TOKEN=your_token
IG_ACCOUNT_ID=your_id
PUBLIC_URL=https://your-domain.com  # Required for Instagram Publishing

# Core Settings
SHORTS_PROVIDER=gemini
SHORTS_WHISPER_MODEL=tiny.en
SHORTS_WHISPER_DEVICE=cpu
SHORTS_WHISPER_COMPUTE_TYPE=int8
SHORTS_VIDEO_CODEC=libx264
SHORTS_VIDEO_PRESET=ultrafast
SHORTS_OUTPUT_DIR=outputs
SHORTS_ENABLE_GPU=false
SHORTS_PUBLISH_PLATFORMS=youtube,instagram
```
*(A `client_secret.json` must be placed in the root directory for YouTube OAuth uploads).*

## 9. Running the CLI

**Scout a niche (Discovery only):**
```bash
python -m shorts_clipper scout --niche "tech" --keyword "AI"
```

**Clip a specific video:**
```bash
python -m shorts_clipper clip https://youtu.be/VIDEO_ID
```

**Autopilot Mode (End-to-End):**
```bash
python -m shorts_clipper autopilot --niche "science" --count 1
```

## 10. Running the Web Dashboard
Launch the FastAPI web server to view the queue, trigger jobs, and monitor SSE live logs:
```bash
python -m shorts_clipper web
```

## 11. Example Commands
- **Full GPU acceleration**: 
  `SHORTS_ENABLE_GPU=true python -m shorts_clipper clip https://youtu.be/xyz`
- **Publish only to YouTube**:
  `SHORTS_PUBLISH_PLATFORMS=youtube python -m shorts_clipper autopilot --niche "finance"`

## 12. Testing
The project features a comprehensive `pytest` suite ensuring pipeline integrity.
```bash
pip install ruff pytest
pytest tests/ -v
ruff check shorts_clipper/ tests/
```

## 13. Project Structure
- `shorts_clipper/` - Core engine (api, core, downloader, pipeline, providers, publishers, rendering, scout, transcription).
- `tests/` - Validation suite (68+ tests covering regressions, fallbacks, and publishers).
- `outputs/` - Default directory for generated `.mp4` clips and thumbnails.

## 14. Performance Notes
- **GPU Acceleration**: Setting `SHORTS_ENABLE_GPU=true` switches FFmpeg to `h264_nvenc` and Whisper to CUDA/float16, dramatically reducing rendering time.
- **Partial Downloads**: The system uses precise `yt-dlp` section downloads (`--download-sections`) to avoid downloading entire 3-hour podcasts when only a 60-second clip is needed.

## 15. Known Limitations
- **AI Extraction Consistency**: LLMs can occasionally misidentify the climax of a story or fail to provide a structurally valid JSON response under severe rate limits.
- **YouTube API Quotas**: Searching and downloading heavily can quickly exhaust YouTube Data API daily limits.
- **Instagram Publishing Restrictions**: Meta's Graph API requires video URLs to be publicly accessible. Local development requires a reverse proxy (e.g., ngrok) configured via `PUBLIC_URL`.

## 16. Roadmap

**Completed (V3.1):**
- Full static analysis and linting (Ruff).
- Resolution of SQLite file locking leaks.
- Mitigation of concurrent scout report race conditions.
- Strict fallback integration for Gemini 429 quota exhaustion.
- Formalized Publisher Registry for multi-platform distribution.

**Future (V4):**
- Transition to fully autonomous 24/7 background worker loops.
- Expanded platform support (TikTok, Facebook Reels).
- Advanced visual analysis (scene detection) for intelligent center-cropping.

## 17. Contributing
Contributions are welcome. Please ensure that you run `ruff check` and `pytest tests/` before submitting pull requests. New publishing targets should implement the `Publisher` base class in `shorts_clipper/publishers/base.py`.

## 18. License
This project is licensed under the MIT License.

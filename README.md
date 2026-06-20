# Shorts Clipper

Autonomous attention-ranking engine for discovering, evaluating, and clipping high-potential content.

## Why This Exists

Most clipping tools assume humans already know what to clip. They wait for you to choose a video, scrub through it, and manually select the interesting part.

**Shorts Clipper inverts this.** It starts from the question most tools ignore:

> Which content deserves attention in the first place?

Scout — the core engine — autonomously searches, filters, scores, and ranks video candidates. It evaluates multiple finalists against each other before committing to a single winner. The clipping pipeline then executes on Scout's decision.

The result: a system that goes from zero input to a published vertical short, without human intervention.

## Architecture

```
SCOUT ENGINE
  │
  ├── Discovery ─────── YouTube API / yt-dlp search
  │
  ├── Filtering ─────── Duration, age, views, language
  │
  ├── Scoring ──────── Multi-dimensional virality ranking
  │
  ├── Evaluation ────── Transcript analysis + Gemini AI
  │
  ├── Selection ─────── Compare finalists, pick winner
  │
  └── Clip Pipeline
        ├── Download ── yt-dlp with anti-ban
        ├── Transcribe ─ Whisper (fallback if no subs)
        ├── Highlight ── Gemini 2.5 attention detection
        ├── Render ──── FFmpeg 9:16 crop + subtitle burn
        └── Publish ─── YouTube OAuth upload
```

## Scout V2

Scout V2 is a multi-stage attention-ranking engine. It does not accept the first passing video — it evaluates multiple finalists and selects the strongest.

**How it works:**

1. **Discovery** — Generates targeted search queries from niche and keyword inputs. Uses the YouTube Data API when available, falls back to yt-dlp flat search when quota is exhausted.

2. **Filtering** — Rejects candidates that are too short (<60s), too long (>20min), too old, or below a minimum view threshold. Deduplicates across queries.

3. **Intermediate Scoring** — Ranks survivors using a capped multi-dimensional score: view velocity, engagement ratio (likes + comments), recency decay, and channel history bonus from prior successful runs.

4. **Finalist Selection** — Takes the top N candidates (configurable, default 15) into a deep evaluation pool.

5. **Transcript Acquisition** — For each finalist, fetches native YouTube subtitles. If unavailable, downloads a 90-second audio sample and runs Whisper transcription in a sandboxed subprocess with a configurable timeout.

6. **Highlight Analysis** — Scores each transcript using a rule-based scorer (hook detection, emotional language, caption density). Then queries Gemini 2.5 for AI-assisted highlight selection with virality scoring.

7. **Winner Selection** — Computes a weighted final score combining AI highlights (40%), rule-based signals, view velocity, engagement ratio, subtitle confidence, and channel history bonus. Compares all passing candidates and selects the highest-scoring one.

**Fallback behavior:** If Gemini quota is exhausted, Scout switches to metadata-only scoring for remaining candidates. If no candidate scores above the quality bar, Scout aborts cleanly rather than producing a poor clip.

## Production Hardening

Scout V2 includes significant reliability work:

- **Keyword propagation** — Niche and keyword parameters correctly flow through the full discovery → query → filter → evaluation pipeline.
- **Multi-candidate ranking** — Scout evaluates and compares multiple finalists instead of accepting the first passing video.
- **Quota handling** — Gemini quota exhaustion triggers automatic fallback to rule-based scoring. YouTube API quota exhaustion falls back to yt-dlp.
- **Timeout protection** — Whisper transcription runs in a separate process with a configurable timeout (`SCOUT_MAX_TRANSCRIPTION_SECONDS`). Hung processes are terminated.
- **Subtitle recovery** — Three-tier subtitle confidence scoring (native > whisper > none). Native subtitles are preferred, Whisper is a fallback, missing subtitles cause rejection.
- **yt-dlp resilience** — Circuit breaker pattern for repeated yt-dlp failures. Browser TLS fingerprint impersonation via curl-cffi.
- **Cache improvements** — Metadata and transcript caching with configurable TTL. Cache hits skip expensive subtitle fetching and transcription.
- **Resource leak fixes** — Temporary directories for evaluation are cleaned up via context managers. Subprocess transcription prevents orphaned Whisper processes.
- **Evaluation budget** — Configurable limit on how many candidates are deeply evaluated (`SCOUT_EVALUATION_BUDGET`), preventing runaway API costs.

## Features

- Autonomous content discovery via YouTube Data API and yt-dlp
- Multi-stage candidate ranking with intermediate scoring
- Configurable filtering (duration, views, age, language)
- Gemini 2.5 highlight detection with virality scoring
- Rule-based fallback scoring (hooks, emotion, caption density)
- Whisper transcription fallback with timeout protection
- Native subtitle detection and validation
- Channel history feedback loop (learning from successful picks)
- 9:16 vertical crop with animated word-level `.ass` subtitles
- Single-pass FFmpeg rendering (crop + subtitle burn + pacing)
- YouTube OAuth upload
- Web dashboard (FastAPI + background worker)
- CLI with `scout`, `clip`, `autopilot`, and `web` commands
- Scout explainability reports (`outputs/scout_report.json`)

## Quick Start

### Installation

```bash
git clone https://github.com/random-or/shorts-clipper.git
cd shorts-clipper
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
sudo apt-get install ffmpeg  # required for rendering
```

### Configuration

```bash
cp .env.example .env
```

**Required:**
- `GEMINI_API_KEY` — Get from [Google AI Studio](https://aistudio.google.com/). Used for highlight detection.
- `YOUTUBE_API_KEY` — Get from [Google Cloud Console](https://console.cloud.google.com/). Used for fast discovery (optional but recommended).

**Optional:**
- `SHORTS_WHISPER_MODEL` — Transcription model (`tiny.en`, `base.en`, `small.en`). Default: `tiny.en`.
- `SHORTS_SCOUT_MAX_AGE_DAYS` — Discovery time window. Default: `90`.
- `SHORTS_ENABLE_GPU` — Enable CUDA for Whisper and NVENC for FFmpeg. Default: `false`.

### Commands

```bash
# Scout: find the best video for a niche
python -m shorts_clipper scout --niche "tech" --keyword "AI"

# Autopilot: scout + clip + render in one step
python -m shorts_clipper autopilot --niche "football" --count 1

# Clip a specific video
python -m shorts_clipper clip https://youtu.be/VIDEO_ID

# Launch the web dashboard
python -m shorts_clipper web
```

### Example Workflow

```bash
# 1. Scout discovers and evaluates candidates
python -m shorts_clipper scout --niche "science" --keyword "space"
# Output: https://www.youtube.com/watch?v=...

# 2. Autopilot runs the full pipeline
python -m shorts_clipper autopilot --niche "science" --keyword "space"
# Output: outputs/clip_20260620_123456.mp4

# 3. Review the scout decision
cat outputs/scout_report.json
```

## Current Status

Scout V2 is stable and undergoing manual ranking-quality validation.

The core pipeline — discovery, filtering, scoring, evaluation, clipping, and rendering — is functional in production. Current focus is on attention selection quality: ensuring Scout consistently picks videos that produce engaging shorts.

Automated tests cover scoring logic, filtering rules, Gemini integration, subtitle handling, cache behavior, and rendering geometry. Integration testing with live YouTube data is manual.

## Roadmap

**Scout V3** (planned):
- Historical learning from clip performance feedback
- Attention prediction from thumbnail and title signals
- Adaptive scoring weights based on niche-specific patterns

## License

MIT License. See [LICENSE](file:///home/random/shorts-clipper/LICENSE) for details.

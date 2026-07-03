# System Architecture: Shorts Clipper V3.2

## 1. High-Level Topology

Shorts Clipper is built as a highly modular, decoupled system designed to ingest long-form videos and autonomously produce viral short-form content.

```text
[ Scout V2 ] --> [ Editorial Engine ] --> [ Media Render ] --> [ Publisher ]
```

## 2. Core Modules

### 2.1 Scout (Discovery)
Located in `shorts_clipper/scout/`.
Responsible for polling YouTube data APIs and niche keyword mappings to discover trending content. Evaluates momentum, engagement, and recency.
- **Semantic Gating:** Uses Gemini to ensure the discovered content aligns with the user's target niche before proceeding.

### 2.2 Editorial Engine (The Brains)
Located in `shorts_clipper/editorial/`.
The major addition in V3.2. This module replaces previous LLM-heavy editing with a deterministic local pipeline:
- **Feature Store:** Parses `TranscriptSegment` lists to compute metrics (speech rate, pauses).
- **Pipeline:** Runs candidates through 6 stages:
  1. Feature Extraction
  2. Stage 1 (Hard Rejections)
  3. Stage 2 (Plugin Scoring - Hook, Silence, Emotion, Context)
  4. Stage 3 (Confidence Aggregation)
  5. Stage 4 (Ranking)
  6. Final Selection
- **Resilience:** Operates locally. If a single plugin crashes, it is disabled for that run, and confidence math redistributes the weights.

### 2.3 Rendering Engine
Located in `shorts_clipper/rendering/`.
- **Cropping:** Determines geometry boundaries to convert 16:9 to 9:16.
- **Transcription:** Uses `faster-whisper` (running locally on CPU/GPU) to get highly accurate, word-level timestamps.
- **FFmpeg Integration:** Performs pass 1 (video crop) and pass 2 (subtitle burn with `.ass` files, applying pacing adjustments).

### 2.4 Publisher
Located in `shorts_clipper/publishers/`.
- Pluggable architecture.
- **YouTube:** Uses standard Google OAuth2 flow.
- **Instagram:** Uses session ID injection and staging via tmpfiles.org for Graph API uploads.

### 2.5 Job Management & API
- **Worker:** Decoupled `worker.py` loops over a persistent SQLite-backed job queue.
- **API Server:** FastAPI production server providing the Vanguard Console UI, exposing real-time SSE logs.

## 3. Data Persistence
Currently optimized for local power-user operation:
- **Queue/Jobs:** SQLite (`core/queue.py`)
- **Cache:** SQLite (`core/cache.py`) for caching metadata, AI selections, and transcription artifacts to save time and API quota.

## 4. Path to SaaS (V4.0)
To transition to a multi-tenant SaaS architecture, the following architectural shifts are mapped out:
1. Replace SQLite with PostgreSQL.
2. Replace local queue loop with Redis + Celery workers.
3. Secure the FastAPI interface with JWT authentication.

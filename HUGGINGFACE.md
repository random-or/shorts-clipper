---
title: Shorts Clipper
emoji: ✂️
colorFrom: purple
colorTo: blue
sdk: docker
pinned: false
license: mit
---

# Shorts Clipper

An AI-powered video clipping pipeline designed to automatically extract, process, subtitle, and repurpose long-form videos into highly engaging vertical short-form content.

## Model Description

Shorts Clipper orchestrates several distinct models and APIs:
- **Language Models (Gemini/OpenAI):** Utilized for intelligent highlight detection. Analyzes transcription text to pinpoint exact timestamps for high-retention clips based on emotional peaks and dialogue flow.
- **Speech-to-Text (Faster-Whisper):** Employs offline precision transcription (`tiny.en` through `large-v3`) with hardware acceleration to generate accurate transcripts for clipping and `.ass` subtitles.
- **Scout Pipeline:** Autonomous discovery engine to ingest and rank trending videos dynamically.

## Intended Uses & Limitations

**Intended Uses:**
- Repurposing podcasts, streams, and webinars into TikToks, Reels, and Shorts.
- Automated content curation for media agencies and creators.
- Fast, single-pass video rendering with burned-in subtitles.

**Limitations:**
- Hardware intensive if using large Whisper models without GPU acceleration.
- Relies on external LLM APIs (Gemini/OpenAI) for highlight detection. Rate limits on those APIs will throttle pipeline throughput.
- YouTube bot-detection updates may periodically break `yt-dlp` scraping; updating dependencies regularly is required.

## Usage Instructions

To run Shorts Clipper using Docker (recommended for Hugging Face Spaces):

```bash
docker-compose up --build
```

You must inject the following environment variables:
- `YOUTUBE_API_KEY`: For trending topic discovery.
- `GEMINI_API_KEY`: For highlight detection.

## Evaluation

Shorts Clipper has been evaluated on its end-to-end processing speed:
- **Scout Discovery:** Sub-second latency utilizing the YouTube Data API.
- **Rendering:** High-speed single-pass rendering applying 9:16 vertical crop, 1.15x speed pacing, and `.ass` subtitle burn-in via FFmpeg.

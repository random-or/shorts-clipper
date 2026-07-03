# Release Notes: Shorts Clipper V3.2

**Release Date:** 2026-07-03

We are thrilled to announce **Shorts Clipper V3.2**, a transformative release that fundamentally shifts the architectural paradigm of the platform from an LLM-dependent pipeline to a lightning-fast, local-first deterministic engine.

## 🌟 Major Highlights

### The Local-First Editorial Engine
The biggest change in V3.2 is the introduction of the new **Editorial Engine** (`shorts_clipper.editorial`). Previously, Shorts Clipper relied heavily on the Gemini API to act as the primary video editor—reading transcripts and guessing the best timestamp. This approach was slow, expensive, and subject to quota exhaustion.

V3.2 codifies human editorial principles (pacing, tension, hook quality, dead air) into a robust, deterministic plugin system. 
- **Feature Store:** Computes transcript and audio features (words per second, pauses, sentence boundaries) once per video.
- **Scoring Pipeline:** A multi-stage scoring system filters out bad clips (hard rejections) and ranks candidates using specialized judges (Hook, Silence, Length, Context, Emotion).
- **Gemini Demotion:** Gemini is now demoted to an optional "validator" and metadata generator, drastically reducing API dependency.

### Scout V2 Pipeline Fixes
We patched a critical architectural leak where `scout/trending.py` was bypassing the new Editorial Engine by returning cached LLM timestamps. The scout now correctly delegates final timestamp evaluation to the local Editorial Engine, ensuring 100% deterministic, quota-free operation.

### Instagram Publisher Reliability
The Instagram publishing pipeline was previously failing due to the deprecation of the Catbox temporary host. V3.2 migrates to a robust integration utilizing `tmpfiles.org` for media staging before initializing the Graph API upload.

## 🚀 Upgrade Instructions
If you are upgrading from V3.1:
1. `git pull` to retrieve the latest main branch.
2. Ensure you have the latest dependencies: `pip install -r requirements.txt`.
3. Check your `.env` against the new `.env.example` as new cache configurations have been introduced.

We are incredibly excited for you to experience the speed and reliability of V3.2!

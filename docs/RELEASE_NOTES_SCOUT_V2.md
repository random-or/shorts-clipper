# Scout V2 Release Notes

**Release Candidate — June 2026**

## Summary

Scout V2 is a ground-up redesign of the content discovery and ranking engine. The previous version accepted the first video that passed basic filtering. V2 evaluates multiple finalists, scores them across multiple dimensions, and selects the strongest candidate.

This release focuses on ranking quality, production resilience, and operational reliability.

---

## Major Fixes

### Keyword Propagation
- Niche and keyword parameters now correctly propagate through the full pipeline: query generation → API discovery → yt-dlp fallback → filtering → evaluation.
- Previously, keywords were lost during query construction, causing Scout to discover irrelevant content.

### Discovery Fixes
- YouTube Data API path uses structured search with proper date filtering and view count thresholds.
- yt-dlp flat search fallback correctly parses upload dates in both ISO-8601 and `YYYYMMDD` formats.
- Deduplication across multiple search queries prevents the same video from being evaluated twice.

### Ranking Fixes
- Replaced single-pass accept-first-valid logic with multi-candidate comparison.
- Intermediate scoring uses capped multi-dimensional formula: view velocity, engagement ratio, recency decay, and channel history bonus.
- Final scoring weights AI highlights (40%), rule-based signals (hook, emotion, virality), subtitle confidence, and metadata signals.
- Channel history feedback loop gives a bonus to channels that previously produced successful clips.

### Quota Handling
- Gemini API quota exhaustion is detected via `GeminiQuotaExhaustedError` and triggers automatic fallback to metadata-only scoring for remaining candidates.
- YouTube API quota exhaustion falls back to yt-dlp without interrupting the pipeline.
- Evaluation budget (`SCOUT_EVALUATION_BUDGET`) caps the number of deep evaluations per run.

### Timeout Protection
- Whisper transcription runs in a sandboxed `multiprocessing.Process` with configurable timeout (`SCOUT_MAX_TRANSCRIPTION_SECONDS`, default 120s).
- Hung transcription processes are terminated and the candidate is skipped.
- Prevents single slow videos from blocking the entire scout run.

### Resource Leak Fixes
- Evaluation uses `tempfile.TemporaryDirectory` for all intermediate audio files, ensuring cleanup on both success and failure.
- Subprocess-based transcription prevents orphaned Whisper model processes from consuming GPU memory.
- SQLite connections in channel history loading are properly closed.

### Subtitle Scoring
- Three-tier subtitle confidence system: native subtitles (10 points), Whisper fallback (2 points), no transcript (0 points, candidate rejected).
- Native subtitle detection checks both YouTube captions API and yt-dlp subtitle metadata.
- English language detection handles regional variants (`en-US`, `en-GB`, `en-CA`, etc.).

### yt-dlp Hardening
- Circuit breaker pattern tracks consecutive yt-dlp failures and reduces retry attempts.
- Browser TLS fingerprint impersonation via curl-cffi to bypass datacenter IP blocks.
- Configurable proxy support (`SHORTS_PROXY`) with comma-separated rotation.

---

## Performance Improvements

- **Evaluation window reduced**: Pre-filtering removes zero-engagement candidates and below-threshold scores before expensive transcript/AI evaluation.
- **Transcription timeout**: 120-second default timeout prevents indefinite blocking on large audio files.
- **Metadata caching**: Transcripts and video metadata are cached with configurable TTL (`SCOUT_METADATA_CACHE_TTL`), eliminating redundant subtitle fetches on re-evaluation.
- **Fallback optimization**: Gemini quota exhaustion triggers immediate switch to rule-based scoring — no retries against an exhausted API.
- **Finalist pool**: Configurable pool size (`SCOUT_FINALIST_LIMIT`, default 15) controls how many candidates enter deep evaluation.

---

## Production Readiness

- **46 automated tests** covering: scoring logic, filtering rules, Gemini provider integration, cache round-trips, subtitle detection, rendering geometry, and FFmpeg command construction.
- **Lint clean**: Zero warnings from Ruff (`E`, `F`, `I`, `UP`, `B` rule sets).
- **Structured logging**: Scout emits finalist tables, evaluation timing breakdowns, and performance summaries to assist manual quality review.
- **Explainability reports**: Each scout run writes `outputs/scout_report.json` with score breakdowns for the winning candidate.

---

## Known Limitations

1. **Ranking quality is not validated at scale.** Scout V2 scoring weights were tuned manually. Whether the current formula consistently selects attention-worthy content across niches is under evaluation.

2. **Gemini highlight scoring threshold is fixed at 85.** This may be too aggressive for some content types, rejecting candidates that would produce acceptable shorts.

3. **Whisper fallback adds significant latency.** Each fallback transcription downloads a 90-second audio clip and runs inference — typically 15–60 seconds depending on model size and hardware.

4. **No feedback loop from clip performance.** Scout V2 uses channel history from prior runs, but does not incorporate downstream metrics (view count on published shorts, watch-through rate). This is planned for V3.

5. **Single-niche evaluation.** Each scout run evaluates one niche. Cross-niche comparison or multi-niche scheduling requires external orchestration.

6. **YouTube-only discovery.** Scout currently only searches YouTube. Multi-platform discovery (TikTok, Instagram Reels) is not implemented.

7. **No GPU auto-detection.** GPU acceleration must be manually enabled via `SHORTS_ENABLE_GPU=true` and requires compatible FFmpeg (h264_nvenc) and CUDA installations.

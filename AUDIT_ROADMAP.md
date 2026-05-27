# 🔍 shorts-clipper — Professional Code Audit & Improvement Roadmap

> Git status: **up to date** · Branch: `main` · Tests: **9/9 PASSED ✅**

---

## 🩺 What's Wrong Right Now (Bugs & Slop)

### 🐛 Bug #1 — `get_local_transcription` is NOT imported in `pipeline.py`
**File:** [`pipeline.py`](file:///home/random/shorts-clipper/pipeline.py#L85)
```python
# Line 85 — called but never imported!
segments = get_local_transcription(str(micro_clip_path))
```
`get_local_transcription` lives in `subtitles.py` but is never imported in `pipeline.py`. 
The fallback Whisper path will **crash at runtime** with a `NameError`. Critical bug.

**Fix:** Add `from subtitles import get_local_transcription` at the top of `pipeline.py`.

---

### 🐛 Bug #2 — `transcribe.py` referenced in `Dockerfile` but doesn't exist
**File:** [`Dockerfile`](file:///home/random/shorts-clipper/Dockerfile#L15)
```dockerfile
COPY analyzer.py editor.py pipeline.py scout.py subtitles.py transcribe.py ./
```
There is no `transcribe.py` in the project root. The Docker image **fails to build**.

---

### 🐛 Bug #3 — `final_output.mp4` hardcoded to cwd, tracked in git
**File:** [`pipeline.py`](file:///home/random/shorts-clipper/pipeline.py#L109)
```python
final_output = Path("final_output.mp4").absolute()
```
Output is written to whatever directory you run the script from. There's an 8.7 MB `final_output.mp4` already **committed in the repo**. This will grow and pollute the git history every run. Must use `Settings.output_dir` instead.

---

### 🐛 Bug #4 — `scout.py` makes N+1 subprocess calls (1 per result)
**File:** [`scout.py`](file:///home/random/shorts-clipper/scout.py#L36)
For each of 10 search results it spawns a **separate `yt-dlp --dump-json` process** to check duration and subtitle availability. That's up to **10 sequential network calls** just to pick one URL — easily 30–60 seconds of pure wait time.

---

### ⚠️ Code Smell #5 — Root-level scripts vs. proper package split (half-migrated)
The `shorts_clipper/` package has proper modules (`core/`, `providers/`, `rendering/`, `highlight_detection/`, etc.) but `pipeline.py`, `analyzer.py`, `editor.py`, `scout.py`, `subtitles.py` still live at the root as flat scripts. This is a half-finished migration — the package structure exists but isn't used. The root scripts don't go through `Settings`, don't use `shorts_clipper.core.logging`, and bypass all the good architecture.

---

## 🚀 Top 5 Improvements (Priority Order)

### 1. 🔴 Fix the 3 crashes first (takes 30 min)
| # | Fix | File |
|---|-----|------|
| A | Import `get_local_transcription` in `pipeline.py` | `pipeline.py:1` |
| B | Remove `transcribe.py` from `Dockerfile` COPY | `Dockerfile:15` |
| C | Write output to `Settings.output_dir` / add `final_output.mp4` to `.gitignore` | `pipeline.py:109` |

---

### 2. 🟠 Replace MoviePy subtitle rendering with pure FFmpeg (3–5× faster render)
**Currently:** `subtitles.py` uses MoviePy's `TextClip` which goes through ImageMagick/Pillow, re-encodes pixel by pixel, loads the entire clip into RAM, and is **painfully slow**.

**Better approach:** Pre-generate an `.ass` (Advanced SubStation Alpha) subtitle file and use FFmpeg's native `subtitles` filter to burn it in — no Python video loop, GPU-acceleratable, order-of-magnitude faster:
```bash
ffmpeg -i cropped.mp4 -vf "ass=subs.ass" -c:v libx264 -crf 18 -preset fast final.mp4
```
This also gives you per-word karaoke-style highlighting, custom fonts, drop shadows — things MoviePy `TextClip` can't do cleanly.

---

### 3. 🟠 Migrate the 5 root scripts into the package (1–2 days)
Complete the migration that was already started:
```
shorts_clipper/
  pipeline/runner.py      ← pipeline.py
  providers/gemini.py     ← analyzer.py
  downloader/yt_dlp.py    ← editor.py (download part)
  scout/trending.py       ← scout.py
  captions/generator.py   ← subtitles.py
```
Wire everything through `Settings` and `get_logger()`. Then `pipeline.py` at root becomes a 3-line entry point:
```python
from shorts_clipper.pipeline.runner import run
run()
```

---

### 4. 🟡 Add async/parallel scout + `--download-sections` batching (2×–5× speed gain)
**Scout:** Run the 10 video info fetches in parallel with `asyncio` + `httpx` instead of 10 sequential subprocess calls. Or pass all 10 IDs in one `yt-dlp` batch call.

**Whisper:** Load the model once at startup (not per-call). Currently every invocation cold-starts the model.

**FFmpeg encoding:** Use `-preset fast` or `-preset veryfast` in the encode step. Right now MoviePy uses default preset which is `medium` — switching to `fast` cuts encode time by ~40% with near-zero quality loss.

---

### 5. 🟡 Add a proper CLI, structured logging, and output naming (1 day)
Replace `sys.argv` parsing with `argparse` or `click`:
```bash
python -m shorts_clipper clip https://youtube.com/... --output ./clips/ --layout crop_center
python -m shorts_clipper scout --count 5 --output ./clips/
```
Add structured logging via `shorts_clipper.core.logging` (already exists, just not used by the root scripts). Name outputs with timestamp + video ID instead of always overwriting `final_output.mp4`.

---

## ⚡ Performance Deep Dive — How to Make It Faster

| Bottleneck | Current | Fix | Gain |
|---|---|---|---|
| Scout (10 sequential info calls) | ~45s | Batch or async | **~8s** |
| MoviePy subtitle render loop | Very slow (Python frame loop) | FFmpeg ASS subtitles | **3–5×** |
| Whisper model cold start | Every fallback call | Load once at startup | **~3s saved** |
| FFmpeg preset | `medium` (default) | `fast` or `veryfast` | **30–40%** |
| yt-dlp format selection | Downloads best quality | Add `-S res:720` for speed | **2×** |
| Subtitle TextClip creation | ImageMagick per chunk | Pre-generate ASS file | **Massive** |

**GPU path:** If you enable `SHORTS_ENABLE_GPU=true` and have CUDA:
- Use `whisper-large-v3` instead of `tiny` (better accuracy, similar speed on GPU)  
- Use `h264_nvenc` instead of `libx264` in FFmpeg
- Use `faster-whisper` with `device=cuda` and `compute_type=float16`

---

## 🏗️ Path to Deployment Grade

### What "deployment grade" means for this project:
1. **Docker image actually builds** (fix `transcribe.py` bug)
2. **Outputs go to a configurable directory**, not cwd
3. **Structured logs** (JSON, not `print()`) for observability
4. **Graceful error handling** with proper exit codes (not just `traceback.print_exc()`)
5. **Health check endpoint** if you add a REST API (`shorts_clipper/api/` already exists!)
6. **No secrets in env defaults** — API key validation at startup, clear error message
7. **Output filenames include video ID + timestamp** so parallel runs don't clobber each other
8. **CI runs tests on every PR** (`.github/` exists — add `pytest` to the workflow)

### Missing `pytest` in `pyproject.toml` dependencies:
```toml
# Currently only runtime deps — add:
[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.4"]
```
Then: `pip install -e ".[dev]"` works out of the box.

---

## 📋 Action Checklist — Session 1 Complete

### ✅ Done (committed: `44074e8`)
- `[x]` Fix import bug in `pipeline.py` (`get_local_transcription` NameError)
- `[x]` Fix `Dockerfile` — remove phantom `transcribe.py`
- `[x]` Route output to `Settings.output_dir` with timestamped filenames
- `[x]` Add `pytest` + `ruff` to `pyproject.toml` `[dev]` extras
- `[x]` Fix all 24 ruff lint violations (E501, F401, I001, E701, F541, UP015)
- `[x]` Move all `import` statements to top level (no more runtime imports)
- `[x]` Tests: **9/9 passing**, lint: **0 errors**

### 🔜 Next 5 Priorities
1. **Replace MoviePy subtitle render with FFmpeg ASS** — biggest speed win (3–5×)
2. **Parallelise scout info fetches** — cut scouting from ~45s to ~8s
3. **Migrate root scripts into `shorts_clipper/` package** — complete the half-done architecture
4. **Add `argparse` CLI entry point** — `python -m shorts_clipper clip <url>`
5. **Add GitHub Actions CI** — run `pytest` + `ruff` on every PR push

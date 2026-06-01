"""FastAPI production web server for Vanguard Clipper Console.

Integrates the SQLite job queue for persistent job tracking,
performance feedback, and SSE live log streaming.
"""

from __future__ import annotations

import logging
import queue
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import anyio
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from shorts_clipper.analyze.feedback import ClipFeedback, FeedbackStore
from shorts_clipper.core.queue import JobQueue, JobStatus
from shorts_clipper.core.settings import Settings
from shorts_clipper.downloader.yt_dlp import download_audio, fetch_subtitles
from shorts_clipper.pipeline.runner import run, run_autopilot
from shorts_clipper.providers.gemini import GeminiProvider
from shorts_clipper.transcription.whisper import transcribe_clip

# ---------------------------------------------------------------------------
# App & Logging Setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Vanguard Clipper Server",
    description="SaaS-grade automation backend for shorts-clipper.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

log_queue: queue.Queue[str] = queue.Queue(maxsize=2000)

class SSELogHandler(logging.Handler):
    """Custom logging handler to stream logging entries via SSE."""
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            log_queue.put_nowait(msg)
        except Exception:
            pass

# Attach SSE logging handler to shorts_clipper logger
logger = logging.getLogger("shorts_clipper")
sse_handler = SSELogHandler()
sse_formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
sse_handler.setFormatter(sse_formatter)
logger.addHandler(sse_handler)

# Singletons — initialized once at import
_job_queue = JobQueue()
_feedback_store = FeedbackStore()

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class AutopilotRequest(BaseModel):
    niche: str | None = None
    keyword: str | None = None
    channel: str | None = None
    count: int = Field(default=3, ge=1, le=10)

class CustomClipRequest(BaseModel):
    url: str
    count: int = Field(default=1, ge=1, le=10)

class TranscriptRequest(BaseModel):
    url: str

class SegmentModel(BaseModel):
    start: float
    end: float
    text: str

class HighlightsRequest(BaseModel):
    segments: list[SegmentModel]
    count: int = Field(default=3, ge=1, le=10)

class CustomClipRenderRequest(BaseModel):
    url: str
    start: float
    end: float
    layout: str = "crop_center"

class SettingsModel(BaseModel):
    gemini_api_key: str | None = None
    whisper_model: str = "tiny.en"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    video_codec: str = "libx264"
    video_preset: str = "ultrafast"
    scout_max_age_days: int = 90
    enable_gpu: bool = False

class FeedbackModel(BaseModel):
    clip_name: str
    views: int = 0
    likes: int = 0
    shares: int = 0
    comments: int = 0
    watch_time_avg: float = 0.0
    retention_pct: float = 0.0
    notes: str = ""

# ---------------------------------------------------------------------------
# API Routes — Jobs
# ---------------------------------------------------------------------------

@app.get("/api/jobs")
def list_jobs(status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """List all jobs, optionally filtered by status."""
    if status:
        try:
            st = JobStatus(status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}") from exc
        jobs = _job_queue.list_by_status(st, limit=limit)
    else:
        jobs = _job_queue.list_all(limit=limit)
    return [j.to_dict() for j in jobs]

@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    """Get a specific job by ID."""
    job = _job_queue.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()

@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str) -> dict[str, str]:
    """Delete a job from the queue."""
    if _job_queue.delete(job_id):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Job not found")

# ---------------------------------------------------------------------------
# API Routes — Clips
# ---------------------------------------------------------------------------

@app.get("/api/clips")
def list_clips() -> list[dict[str, Any]]:
    """Scan outputs directory and return generated vertical video clips."""
    settings = Settings.from_env()
    out_dir = Path(settings.output_dir)
    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)
    
    clips = []
    for path in sorted(out_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime).isoformat()
        # Check for thumbnail
        thumb = path.with_suffix(".jpg")
        clips.append({
            "name": path.name,
            "path": f"/clips/{path.name}",
            "thumbnail": f"/clips/{thumb.name}" if thumb.exists() else None,
            "size": stat.st_size,
            "created_at": mtime,
        })
    return clips

@app.get("/api/settings", response_model=SettingsModel)
def get_settings() -> SettingsModel:
    """Read configuration from environment variables."""
    s = Settings.from_env()
    return SettingsModel(
        gemini_api_key=s.gemini_api_key,
        whisper_model=s.whisper_model,
        whisper_device=s.whisper_device,
        whisper_compute_type=s.whisper_compute_type,
        video_codec=s.video_codec,
        video_preset=s.video_preset,
        scout_max_age_days=s.scout_max_age_days,
        enable_gpu=s.enable_gpu,
    )

@app.post("/api/settings")
def save_settings(payload: SettingsModel) -> dict[str, str]:
    """Write configuration changes to the active .env file."""
    try:
        env_lines = []
        # Construct .env file lines
        env_lines.append(f"GEMINI_API_KEY={payload.gemini_api_key or ''}")
        env_lines.append(f"SHORTS_WHISPER_MODEL={payload.whisper_model}")
        env_lines.append(f"SHORTS_WHISPER_DEVICE={payload.whisper_device}")
        env_lines.append(f"SHORTS_WHISPER_COMPUTE_TYPE={payload.whisper_compute_type}")
        env_lines.append(f"SHORTS_VIDEO_CODEC={payload.video_codec}")
        env_lines.append(f"SHORTS_VIDEO_PRESET={payload.video_preset}")
        env_lines.append(f"SHORTS_SCOUT_MAX_AGE_DAYS={payload.scout_max_age_days}")
        env_lines.append(f"SHORTS_ENABLE_GPU={'true' if payload.enable_gpu else 'false'}")
        
        Path(".env").write_text("\n".join(env_lines), encoding="utf-8")
        return {"status": "success", "message": "Settings saved to .env file successfully."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {exc}") from exc

# ---------------------------------------------------------------------------
# API Routes — Pipeline Triggers (with Job Queue)
# ---------------------------------------------------------------------------

@app.post("/api/autopilot")
def trigger_autopilot(payload: AutopilotRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Trigger Autopilot mode with job tracking."""
    job = _job_queue.create("autopilot", payload.model_dump())

    def task_worker() -> None:
        try:
            _job_queue.update_status(job.id, JobStatus.RUNNING, progress=5)
            logger.info("🤖 Starting Autopilot background task (job %s)...", job.id)
            settings = Settings.from_env()
            result = run_autopilot(
                settings=settings,
                channel=payload.channel,
                niche=payload.niche,
                keyword=payload.keyword,
                count=payload.count,
            )
            output_paths = []
            if result:
                if isinstance(result, list):
                    output_paths = [str(p) for p in result]
                else:
                    output_paths = [str(result)]

            _job_queue.update_status(
                job.id, JobStatus.DONE,
                progress=100,
                output_paths=output_paths,
                result={"clip_count": len(output_paths)},
            )
            logger.info("✅ Autopilot background task finished successfully!")
        except Exception as err:
            logger.exception("❌ Autopilot background task failed")
            _job_queue.update_status(job.id, JobStatus.FAILED, error=str(err))

    background_tasks.add_task(task_worker)
    return {"status": "started", "job_id": job.id, "message": "Autopilot pipeline triggered."}

@app.post("/api/clip")
def trigger_clip(payload: CustomClipRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Run standard clipper for a specific YouTube URL with job tracking."""
    job = _job_queue.create("clip", payload.model_dump())

    def task_worker() -> None:
        try:
            _job_queue.update_status(job.id, JobStatus.RUNNING, progress=5)
            logger.info("🎬 Starting Custom Clip background task for URL: %s (job %s)...", payload.url, job.id)
            settings = Settings.from_env()
            result = run(payload.url, settings=settings, count=payload.count)
            output_paths = []
            if isinstance(result, list):
                output_paths = [str(p) for p in result]
            else:
                output_paths = [str(result)]

            _job_queue.update_status(
                job.id, JobStatus.DONE,
                progress=100,
                output_paths=output_paths,
                result={"clip_count": len(output_paths)},
            )
            logger.info("✅ Custom Clip background task finished successfully!")
        except Exception as err:
            logger.exception("❌ Custom Clip background task failed")
            _job_queue.update_status(job.id, JobStatus.FAILED, error=str(err))

    background_tasks.add_task(task_worker)
    return {"status": "started", "job_id": job.id, "message": "Clipper pipeline triggered."}

@app.post("/api/scout/transcript")
def trigger_scout_transcript(payload: TranscriptRequest) -> dict[str, Any]:
    """Fetch native subtitles or transcribe a 5-min rough audio sample to return rough transcript."""
    logger.info("🔍 Fetching rough transcript for: %s", payload.url)
    try:
        settings = Settings.from_env()
        with tempfile.TemporaryDirectory(prefix="vanguard_scout_") as temp_dir:
            work_path = Path(temp_dir)
            rough_segments = fetch_subtitles(payload.url, work_path)
            
            if not rough_segments:
                logger.info("No native English subtitles. Downloading 5-min audio sample...")
                audio_path = work_path / "rough_audio.m4a"
                download_audio(payload.url, audio_path, start_time=0.0, end_time=300.0)
                logger.info("Transcribing audio sample with fast Whisper...")
                rough_segments = transcribe_clip(
                    audio_path,
                    model_size="tiny.en",
                    device=settings.whisper_device,
                    compute_type=settings.whisper_compute_type,
                )
                
            return {
                "url": payload.url,
                "segments": [
                    {"start": s.start, "end": s.end, "text": s.text}
                    for s in rough_segments
                ]
            }
    except Exception as exc:
        logger.error("Failed to fetch transcript: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.post("/api/scout/highlights")
def trigger_scout_highlights(payload: HighlightsRequest) -> dict[str, Any]:
    """Send transcript segments to Gemini and retrieve scored candidate highlight clips."""
    logger.info("🧠 Consulting Gemini to select highlights...")
    try:
        from shorts_clipper.core.models import TranscriptSegment
        segments = [
            TranscriptSegment(start=s.start, end=s.end, text=s.text)
            for s in payload.segments
        ]
        settings = Settings.from_env()
        provider = GeminiProvider(api_key=settings.gemini_api_key)
        
        # We consult the multi-clip selection logic
        clips = provider.select_multiple_clips(segments, count=payload.count)
        
        return {
            "highlights": [
                {
                    "start": window.start,
                    "end": window.end,
                    "layout": layout,
                    "duration": round(window.end - window.start, 1)
                }
                for window, layout in clips
            ]
        }
    except Exception as exc:
        logger.error("Failed to fetch highlights from Gemini: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.post("/api/clip/render")
def trigger_clip_render(payload: CustomClipRenderRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Force rendering a specific custom timestamp window from a video."""
    job = _job_queue.create("render", payload.model_dump())

    def task_worker() -> None:
        try:
            _job_queue.update_status(job.id, JobStatus.RUNNING, progress=5)
            logger.info("🎬 Rendering precise custom clip window: %.1fs–%.1fs [%s] from %s (job %s)...", 
                        payload.start, payload.end, payload.layout, payload.url, job.id)
            
            settings = Settings.from_env()
            
            with tempfile.TemporaryDirectory(prefix="vanguard_render_") as work_dir:
                work_path = Path(work_dir)
                clip_work_dir = work_path / "clip_1"
                clip_work_dir.mkdir(parents=True, exist_ok=True)
                
                micro_path = clip_work_dir / "micro_clip.mp4"
                logger.info("⬇ Downloading precise section %.1fs–%.1fs...", payload.start, payload.end)
                
                from shorts_clipper.downloader.yt_dlp import download_clip
                download_clip(payload.url, micro_path, start_time=payload.start, end_time=payload.end)
                _job_queue.update_progress(job.id, 30)
                
                logger.info("Transcribing micro-clip for word timing...")
                precision_segments = transcribe_clip(
                    micro_path,
                    model_size=settings.whisper_model,
                    device=settings.whisper_device,
                    compute_type=settings.whisper_compute_type,
                )
                _job_queue.update_progress(job.id, 50)
                
                logger.info("Cropping to vertical layout...")
                cropped_path = clip_work_dir / "cropped.mp4"
                from shorts_clipper.rendering.crop import process_to_vertical
                process_to_vertical(
                    micro_path,
                    cropped_path,
                    layout=payload.layout,
                    video_codec=settings.video_codec,
                    preset=settings.video_preset,
                )
                _job_queue.update_progress(job.id, 70)
                
                logger.info("Burning subtitles + pacing...")
                from shorts_clipper.captions.generator import burn_subtitles
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                current_output_path = settings.output_dir / f"custom_{ts}.mp4"
                settings.output_dir.mkdir(parents=True, exist_ok=True)
                
                burn_subtitles(
                    cropped_path,
                    precision_segments,
                    start_offset=0.0,
                    output_path=current_output_path,
                    pacing=1.15,
                    video_codec=settings.video_codec,
                    preset=settings.video_preset,
                )
                _job_queue.update_progress(job.id, 90)

                # Extract thumbnail
                try:
                    from shorts_clipper.render.thumbnailer import extract_thumbnail
                    extract_thumbnail(current_output_path)
                except Exception as thumb_err:
                    logger.warning("Thumbnail extraction failed: %s", thumb_err)

                _job_queue.update_status(
                    job.id, JobStatus.DONE,
                    progress=100,
                    output_paths=[str(current_output_path)],
                )
                logger.info("✅ Custom rendered clip ready at: %s", current_output_path)
        except Exception as err:
            logger.exception("❌ Precision render task failed")
            _job_queue.update_status(job.id, JobStatus.FAILED, error=str(err))

    background_tasks.add_task(task_worker)
    return {"status": "started", "job_id": job.id, "message": "Precision render task triggered."}

# ---------------------------------------------------------------------------
# API Routes — Feedback
# ---------------------------------------------------------------------------

@app.get("/api/feedback")
def list_feedback(limit: int = 50) -> list[dict[str, Any]]:
    """List all feedback entries sorted by performance score."""
    return [fb.to_dict() for fb in _feedback_store.list_all(limit=limit)]

@app.get("/api/feedback/{clip_name}")
def get_feedback(clip_name: str) -> dict[str, Any]:
    """Get feedback for a specific clip."""
    fb = _feedback_store.get(clip_name)
    if fb is None:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return fb.to_dict()

@app.post("/api/feedback")
def submit_feedback(payload: FeedbackModel) -> dict[str, Any]:
    """Submit or update performance feedback for a clip."""
    fb = ClipFeedback(
        clip_name=payload.clip_name,
        views=payload.views,
        likes=payload.likes,
        shares=payload.shares,
        comments=payload.comments,
        watch_time_avg=payload.watch_time_avg,
        retention_pct=payload.retention_pct,
        notes=payload.notes,
    )
    result = _feedback_store.upsert(fb)
    return {"status": "saved", "performance_score": result.performance_score, "data": result.to_dict()}

@app.delete("/api/feedback/{clip_name}")
def delete_feedback(clip_name: str) -> dict[str, str]:
    """Delete feedback for a clip."""
    if _feedback_store.delete(clip_name):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Feedback not found")

# ---------------------------------------------------------------------------
# SSE Log Streaming
# ---------------------------------------------------------------------------

@app.get("/api/logs/stream")
async def stream_logs() -> StreamingResponse:
    """Stream live logs generated by python clipper backend via SSE."""
    async def log_generator():
        while True:
            try:
                # Flush the entire queue
                lines = []
                while not log_queue.empty():
                    lines.append(log_queue.get_nowait())
                if lines:
                    joined = "\n".join(lines)
                    yield f"data: {joined}\n\n"
                await anyio.sleep(0.5)
            except Exception:
                break
    return StreamingResponse(log_generator(), media_type="text/event-stream")

# ---------------------------------------------------------------------------
# Static Files & UI Serving
# ---------------------------------------------------------------------------

# Mount clips folder to serve generated mp4s
settings = Settings.from_env()
outputs_dir_path = Path(settings.output_dir).absolute()
outputs_dir_path.mkdir(parents=True, exist_ok=True)
app.mount("/clips", StaticFiles(directory=str(outputs_dir_path)), name="clips")

# Served Vanguard HTML UI
@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    ui_html_path = Path("shorts_clipper/ui/index.html")
    if ui_html_path.exists():
        return HTMLResponse(content=ui_html_path.read_text(encoding="utf-8"))
    
    # Fallback premium stub if ui/index.html is missing
    return HTMLResponse(content="""
    <html>
        <head><title>Vanguard Console</title></head>
        <body style="background:#0b0d19; color:white; font-family:sans-serif; text-align:center; padding-top:100px;">
            <h1>Vanguard Clipper Console</h1>
            <p style="color:#7e87ab;">Frontend is loading or missing in shorts_clipper/ui/index.html.</p>
        </body>
    </html>
    """)

# Serve the rest of the UI as static assets if needed
ui_dir_path = Path("shorts_clipper/ui").absolute()
if ui_dir_path.exists():
    app.mount("/ui", StaticFiles(directory=str(ui_dir_path)), name="ui")

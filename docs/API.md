# Planned API Contract

The FastAPI backend is planned for `shorts_clipper/api`. This file documents the target contract so contributors can build toward a stable interface.

## REST endpoints

### `POST /jobs`

Create a clipping job.

Request:

```json
{
  "source_url": "https://www.youtube.com/watch?v=...",
  "provider": "gemini",
  "preset": "reels_default",
  "max_clips": 3,
  "dry_run": false
}
```

Response:

```json
{
  "job_id": "01HZY...",
  "status": "queued",
  "events_url": "/jobs/01HZY.../events"
}
```

### `GET /jobs/{job_id}`

Read job status.

Response:

```json
{
  "job_id": "01HZY...",
  "status": "running",
  "progress": 0.42,
  "current_step": "transcribing",
  "created_at": "2026-05-26T00:00:00Z",
  "updated_at": "2026-05-26T00:01:30Z"
}
```

### `GET /jobs/{job_id}/result`

Read output metadata.

Response:

```json
{
  "job_id": "01HZY...",
  "clips": [
    {
      "path": "outputs/job-id/final_001.mp4",
      "start": 41.62,
      "end": 75.2,
      "title": "The moment everything changed",
      "hashtags": ["#shorts", "#viral", "#ai"],
      "thumbnail_time": 48.4
    }
  ]
}
```

## WebSocket endpoint

### `WS /jobs/{job_id}/events`

Progress event format:

```json
{
  "job_id": "01HZY...",
  "type": "progress",
  "step": "rendering",
  "message": "Rendering clip 1 of 3",
  "progress": 0.78
}
```

Terminal event format:

```json
{
  "job_id": "01HZY...",
  "type": "completed",
  "message": "Job completed",
  "result_url": "/jobs/01HZY.../result"
}
```

## Implementation notes

- Validate URLs and local paths before starting jobs.
- Store a manifest per job so interrupted jobs can resume.
- Never build shell commands with string interpolation; use argv lists.
- Keep output metadata JSON-serializable.
- WebSocket updates should be best-effort and not required for job completion.

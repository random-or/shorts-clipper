"""YouTube upload integration for Shorts Clipper."""

from __future__ import annotations

import logging
import pickle
from pathlib import Path

log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def get_youtube_service(client_secret_file: Path | str = "client_secret.json"):
    """Authenticate and return the YouTube service object."""
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None
    token_path = Path(".cache/shorts-clipper/token.pickle")

    if token_path.exists():
        with open(token_path, "rb") as token:
            creds = pickle.load(token)  # noqa: S301

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                token_path.parent.mkdir(parents=True, exist_ok=True)
                with open(token_path, "wb") as token:
                    pickle.dump(creds, token)
            except Exception as e:
                raise RuntimeError(
                    f"YouTube credentials expired and could not be refreshed: {e}"
                ) from e
        else:
            raise RuntimeError(
                "YouTube channel is not connected. Please link your YouTube account from the Web UI sidebar first!"
            )

    return build("youtube", "v3", credentials=creds)


def upload_short(
    video_path: Path | str,
    title: str,
    description: str = "#Shorts",
    tags: list[str] | None = None,
) -> str:
    """Upload a video to YouTube as a Short.

    Returns:
        The YouTube video ID of the uploaded video.
    """
    from googleapiclient.http import MediaFileUpload

    log.info("Uploading %s to YouTube...", video_path)

    youtube = get_youtube_service()

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or ["Shorts", "Trending", "Viral"],
            "categoryId": "24",  # Entertainment
        },
        "status": {
            "privacyStatus": "private",  # Default to private for review
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            log.info("Uploaded %d%%...", int(status.progress() * 100))

    log.info("✅ Upload Complete! Video ID: %s", response.get("id"))
    return response.get("id")

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY shorts_clipper ./shorts_clipper

RUN python -m pip install --upgrade pip \
    && pip install -e .

EXPOSE 8000
CMD ["uvicorn", "shorts_clipper.api.server:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY shorts_clipper ./shorts_clipper
COPY analyzer.py editor.py pipeline.py scout.py subtitles.py transcribe.py ./
COPY tests ./tests

RUN python -m pip install --upgrade pip \
    && pip install -e .

CMD ["python", "pipeline.py"]

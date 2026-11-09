FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PYTHONUTF8=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./

RUN python -m pip install --upgrade pip \
    && python -m pip install "nemo_text_processing==1.2.0"

COPY src ./src

RUN python -m pip install .

EXPOSE 8765

CMD ["audiobook-maker", "ui", "--host", "0.0.0.0", "--port", "8765"]


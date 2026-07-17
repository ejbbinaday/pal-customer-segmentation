# PAL Customer Segmentation — reproducible environment for the pipeline + dashboard.
# Python is pinned to 3.11 (broad scientific-wheel coverage) so the image builds
# identically regardless of the host's Python.
#
# Build:  docker build -t pal-segmentation .
# Dashboard (default):  docker run --rm -p 8501:8501 pal-segmentation
# Run a pipeline script (persist figures to the host):
#   docker run --rm -v "$PWD/outputs:/app/outputs" pal-segmentation python src/hdbscan_final.py
FROM python:3.11-slim

# build-essential is a safety net for any dependency without a prebuilt wheel.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg

# Install dependencies first so this layer is cached across code changes.
COPY requirements.txt requirements-pipeline.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements-pipeline.txt -r requirements.txt

# Application code, data, and docs (see .dockerignore for what is excluded).
COPY . .

EXPOSE 8501

# Default entrypoint serves the executive dashboard.
CMD ["streamlit", "run", "src/dashboard.py", \
     "--server.port=8501", "--server.address=0.0.0.0"]

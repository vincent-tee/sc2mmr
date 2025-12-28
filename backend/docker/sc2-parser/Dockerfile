# SC2 Replay Parser Docker Image
# 
# Uses the pre-built SC2 Docker image that has all game data properly configured.
# This enables PyCommandCenter to parse replays and extract high-fidelity metrics.
#
# Build: docker build -t sc2-parser -f docker/sc2-parser/Dockerfile .
# Run:   docker run --rm -v /path/to/replays:/replays sc2-parser /replays/game.SC2Replay

FROM byblo/sc2docker:4.10.0-linux as sc2base

# Use Python 3.10 as final image
FROM python:3.10-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libxrender1 \
    libxext6 \
    libsm6 \
    && rm -rf /var/lib/apt/lists/*

# Copy SC2 from the sc2docker image
COPY --from=sc2base /root/StarCraftII /opt/StarCraftII
ENV SC2PATH=/opt/StarCraftII

# Set up Python app
WORKDIR /app

# Copy PyCommandCenter library
COPY app/lib/library.so /app/lib/

# Install Python dependencies  
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ /app/app/

# Set environment
ENV PYTHONPATH=/app:/app/lib

# Simple entrypoint script for replay parsing
COPY docker/sc2-parser/parse_replay.py /app/parse_replay.py
ENTRYPOINT ["python", "/app/parse_replay.py"]

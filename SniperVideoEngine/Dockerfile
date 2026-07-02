FROM python:3.11-slim

# System dependencies: ffmpeg for video, espeak-ng for Kokoro TTS
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    espeak-ng \
    libstdc++6 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser (Chromium for YouTube upload)
RUN playwright install --with-deps chromium || true

# Copy application
COPY . .

# Create output directories
RUN mkdir -p outputs/temp assets/music

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]

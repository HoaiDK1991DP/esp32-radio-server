FROM python:3.11-slim

# Cài đặt ffmpeg + Node.js 20 (JS runtime cho yt-dlp EJS)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Kiểm tra phiên bản Node.js
RUN node --version

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Cài yt-dlp với EJS solver scripts (bắt buộc cho n challenge)
RUN pip install --no-cache-dir --upgrade "yt-dlp[default]"

COPY . .

EXPOSE 5000

CMD ["python", "main.py"]

FROM python:3.11-slim

# Cài đặt ffmpeg, curl và Node.js 20 (yêu cầu cho EJS solver)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Kiểm tra phiên bản Node.js (phải >= 20)
RUN node --version

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Cài đặt yt-dlp bản đầy đủ (kèm EJS solver scripts)
RUN pip install --no-cache-dir --upgrade "yt-dlp[default]"

COPY . .

EXPOSE 5000

CMD ["python", "main.py"]

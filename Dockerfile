FROM python:3.11-slim

# Cài đặt ffmpeg (xử lý audio), nodejs + npm (JavaScript runtime cho yt-dlp)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Nâng cấp yt-dlp lên bản mới nhất (ghi đè bản trong requirements.txt)
RUN pip install --no-cache-dir --upgrade yt-dlp

COPY . .

EXPOSE 5000

CMD ["python", "main.py"]

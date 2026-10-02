import os
import subprocess
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn

app = FastAPI()

# 1. MẬT KHẨU BẢO MẬT
SECRET_TOKEN = "pvt_123456"

# 2. DANH SÁCH ĐÀI RADIO
RADIO_GROUPS = {
    "vov1": "https://str.vov.gov.vn/vovlive/vov1.sdp_aac/playlist.m3u8",
    "vovgt_hn": "https://play.vovgiaothong.vn/live/gthn/playlist.m3u8",
    "vovgt_hcm": "https://play.vovgiaothong.vn/live/gthcm/playlist.m3u8",
    "vov2": "https://str.vov.gov.vn/vovlive/vov2.sdp_aac/playlist.m3u8",
    "voh956": "https://stream.voh.com.vn/voh/fm956.sdp/playlist.m3u8"
}

def generate_mp3_stream(source_url: str):
    """
    Sử dụng FFmpeg đọc luồng HLS, chuyển mã sang MP3 
    xuất ra stdout cho ESP32 / Trình duyệt.
    """
    command = [
        'ffmpeg',
        '-reconnect', '1',
        '-reconnect_streamed', '1',
        '-reconnect_delay_max', '3',
        '-i', source_url,
        '-vn',
        '-acodec', 'libmp3lame',
        '-ab', '128k',
        '-ar', '44100',
        '-f', 'mp3',
        'pipe:1'
    ]
    
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=10**6
    )
    
    try:
        while True:
            chunk = process.stdout.read(4096)
            if not chunk:
                break
            yield chunk
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait()

@app.get("/stream")
async def stream_radio(
    token: Optional[str] = Query(None),
    station: Optional[str] = Query("vovgt_hn")
):
    # Kiểm tra Token
    if token != SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Token khong hop le!")

    # Lấy URL đài được chọn (mặc định lấy vovgt_hn nếu gõ sai)
    station_key = station.lower() if station else "vovgt_hn"
    source_url = RADIO_GROUPS.get(station_key, RADIO_GROUPS["vovgt_hn"])

    return StreamingResponse(
        generate_mp3_stream(source_url),
        media_type="audio/mpeg"
    )

@app.get("/")
async def root():
    return {"message": "Radio Transcoding Server is running"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
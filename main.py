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
    "vov2": "https://str.vov.gov.vn/vovlive/vov2.sdp_aac/playlist.m3u8",
    "vov3": "https://str.vov.gov.vn/vovlive/vov3.sdp_aac/playlist.m3u8",
    "vovgt_hn": "https://play.vovgiaothong.vn/live/gthn/playlist.m3u8",
    "vovgt_hcm": "https://play.vovgiaothong.vn/live/gthcm/playlist.m3u8",
    "voh956": "https://stream.voh.com.vn/voh/fm956.sdp/playlist.m3u8",
    "voh999": "https://stream.voh.com.vn/voh/fm999.sdp/playlist.m3u8",
    "hanoi90": "http://14.162.146.90:8000/HANOI90"
}

def generate_mp3_stream(source_url: str):
    """
    Sử dụng FFmpeg đọc luồng HLS, chuyển mã sang MP3 
    tối ưu triệt để bộ nhớ & giải phóng tiến trình trên Render.
    """
    command = [
        'ffmpeg',
        '-user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        '-reconnect', '1',
        '-reconnect_streamed', '1',
        '-reconnect_delay_max', '3',
        '-i', source_url,
        '-vn',
        '-acodec', 'libmp3lame',
        '-ab', '96k',         # Bitrate 96k nhẹ máy chủ, truyền mượt qua WiFi ESP32
        '-ar', '32000',       # Sample rate tối ưu cho loa ESP32
        '-ac', '1',           # Mono audio nhẹ luồng truyền
        '-f', 'mp3',
        'pipe:1'
    ]
    
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=1024 * 32     # Bộ đệm 32KB phản hồi tức thì
    )
    
    try:
        while True:
            chunk = process.stdout.read(2048)
            if not chunk:
                break
            yield chunk
    except Exception:
        pass
    finally:
        # Buộc tiêu diệt triệt để ffmpeg khi người dùng / ESP32 ngắt kết nối
        if process.poll() is None:
            process.kill()
            process.wait()

@app.get("/stream")
async def stream_radio(
    token: Optional[str] = Query(None),
    station: Optional[str] = Query("vovgt_hn")
):
    # Kiểm tra Token
    if token != SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Token khong hop le!")

    # Lấy URL đài được chọn (mặc định vovgt_hn)
    station_key = station.lower() if station else "vovgt_hn"
    source_url = RADIO_GROUPS.get(station_key, RADIO_GROUPS["vovgt_hn"])

    return StreamingResponse(
        generate_mp3_stream(source_url),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive"
        }
    )

@app.get("/")
async def root():
    return {"message": "Radio Transcoding Server is running"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
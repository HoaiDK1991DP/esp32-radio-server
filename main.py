import os
import subprocess
from typing import Optional, List
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn

app = FastAPI(
    title="ESP32 Private Radio Transcoder",
    description="Server chuyển mã HLS/AAC sang MP3 cho ESP32 kèm Token bảo mật và Fallback",
    version="3.6"
)

# ---------------------------------------------------------
# 1. MẬT KHẨU BẢO MẬT (TOKEN)
# ---------------------------------------------------------
SECRET_TOKEN = "pvt_123456"

# ---------------------------------------------------------
# 2. DANH SÁCH ĐÀI RADIO & DỰ PHÒNG (FALLBACK GROUPS)
# ---------------------------------------------------------
RADIO_GROUPS = {
    "vov1": [
        "https://str.vov.gov.vn/vovlive/vov1vov5Vietnamese.sdp_aac/playlist.m3u8",
        "https://str.vov.gov.vn/vovlive/vov1.sdp_aac/playlist.m3u8"
    ],
    "hanoi90": [
        "http://14.162.146.90:8000/HANOI90"
    ],
    "vovgt_hcm": [
        "https://play.vovgiaothong.vn/live/gthcm/playlist.m3u8",
        "https://play.vovgiaothong.vn/live/gthn/playlist.m3u8"
    ],
    "vov2": [
        "https://audio-lss.vov.vn/live/vov2.m3u8",
        "https://str.vov.gov.vn/vovlive/vov2.sdp_aac/playlist.m3u8"
    ]
}

DEFAULT_FALLBACK_LIST = RADIO_GROUPS["vov1"]

# ---------------------------------------------------------
# 3. HÀM TRANSCODE DÒNG MÂM THANH MP3
# ---------------------------------------------------------
def generate_fallback_mp3_stream(urls: List[str]):
    """Đọc luồng âm thanh và xuất ra định dạng MP3 128kbps."""
    for url in urls:
        print(f"[RADIO LOG] Đang thử kết nối phát đài: {url}")

        command = [
            'ffmpeg',
            '-reconnect', '1',
            '-reconnect_at_eof', '1',
            '-reconnect_streamed', '1',
            '-reconnect_delay_max', '3',
            '-i', url,
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

        has_data = False
        try:
            while True:
                chunk = process.stdout.read(4096)
                if not chunk:
                    break
                has_data = True
                yield chunk
        except GeneratorExit:
            if process.poll() is None:
                process.terminate()
            return
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()

        if has_data:
            print(f"[RADIO LOG] Luồng {url} bị đứt, chuyển link tiếp theo...")

# ---------------------------------------------------------
# 4. ENDPOINTS API
# ---------------------------------------------------------
@app.get("/stream")
async def stream_radio(
    token: Optional[str] = Query(None, description="Token bảo mật"),
    url: Optional[str] = Query(None, description="URL stream direct (phân cách bằng dấu phẩy)"),
    station: Optional[str] = Query(None, description="Mã đài (vov1, hanoi90, vovgt_hcm, vov2)")
):
    if token != SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Xác thực thất bại! Token không hợp lệ.")

    target_urls = []

    if url:
        target_urls = [u.strip() for u in url.split(",") if u.strip()]
    elif station:
        station_key = station.lower()
        if station_key in RADIO_GROUPS:
            target_urls = RADIO_GROUPS[station_key]
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Mã đài '{station}' không hợp lệ. Danh sách: {list(RADIO_GROUPS.keys())}"
            )
    else:
        target_urls = DEFAULT_FALLBACK_LIST

    return StreamingResponse(
        generate_fallback_mp3_stream(target_urls),
        media_type="audio/mpeg",
        headers={
            "Accept-Ranges": "none",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )

@app.get("/groups")
async def get_groups(token: Optional[str] = Query(None)):
    if token != SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập!")
    return {"status": "success", "groups": RADIO_GROUPS}

@app.get("/")
async def root():
    return {"message": "Server Radio ESP32 đang hoạt động bình thường."}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
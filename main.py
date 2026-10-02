import os
import subprocess
from typing import Optional, List
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn

app = FastAPI(
    title="ESP32 Radio Server",
    version="4.0"
)

SECRET_TOKEN = "pvt_123456"

# Danh sách đài cập nhật link stream trực tiếp ổn định nhất
RADIO_GROUPS = {
    "voh956": [
        "https://stream.voh.com.vn/voh/fm956.sdp/playlist.m3u8",
        "https://stream.voh.com.vn/voh/fm999.sdp/playlist.m3u8"
    ],
    "vov1": [
        "https://str.vov.gov.vn/vovlive/vov1.sdp_aac/playlist.m3u8",
        "https://str.vov.gov.vn/vovlive/vov1vov5Vietnamese.sdp_aac/playlist.m3u8"
    ],
    "vovgt_hcm": [
        "https://play.vovgiaothong.vn/live/gthcm/playlist.m3u8"
    ],
    "vov2": [
        "https://str.vov.gov.vn/vovlive/vov2.sdp_aac/playlist.m3u8"
    ]
}

def generate_mp3_stream(urls: List[str]):
    for url in urls:
        print(f"[LOG] Dang thiet lap ket noi toi: {url}")
        
        command = [
            'ffmpeg',
            '-headers', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n',
            '-i', url,
            '-vn',
            '-acodec', 'libmp3lame',
            '-ab', '96k',
            '-ar', '22050',
            '-ac', '1',
            '-f', 'mp3',
            'pipe:1'
        ]

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=1024*64
        )

        try:
            while True:
                chunk = process.stdout.read(2048)
                if not chunk:
                    break
                yield chunk
        except Exception as e:
            print(f"[LOG] Error: {e}")
        finally:
            if process.poll() is None:
                process.kill()

@app.get("/stream")
async def stream_radio(
    token: Optional[str] = Query(None),
    station: Optional[str] = Query("voh956")
):
    if token != SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid Token")

    station_key = station.lower() if station else "voh956"
    target_urls = RADIO_GROUPS.get(station_key, RADIO_GROUPS["voh956"])

    return StreamingResponse(
        generate_mp3_stream(target_urls),
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
    return {"status": "online"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
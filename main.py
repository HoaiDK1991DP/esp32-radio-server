import os
import subprocess
import tempfile
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
import uvicorn
import yt_dlp

app = FastAPI()

# 1. MẬT KHẨU BẢO MẬT CHUNG CHO TOÀN BỘ HỆ THỐNG
SECRET_TOKEN = "pvt_123456"

# 2. DANH SÁCH ĐÀI RADIO TRUYỀN THỐNG 
RADIO_GROUPS = {
    "vov3": "https://str.vov.gov.vn/vovlive/vov3.sdp_aac/playlist.m3u8",
    "vovgt_hn": "https://play.vovgiaothong.vn/live/gthn/playlist.m3u8",
    "vovgt_hcm": "https://play.vovgiaothong.vn/live/gthcm/playlist.m3u8",
    "voh956": "http://71.4.56.20/3rdout/radio.hou.std2/icecast.audio",
    "hanoi90": "https://lzlive.vojs.cn/jAmO6Ng/92/live.m3u8"
}

# Biến toàn cục quản lý Playlist vĩnh viễn & Vị trí bài đang phát
PLAYLIST_ITEMS = []
CURRENT_INDEX = 0
ACTIVE_FFMPEG_PROCESS = None


def get_cookie_file():
    """Tạo file cookie tạm từ biến môi trường YT_COOKIES_B64, trả về đường dẫn hoặc None"""
    cookies_content = os.getenv("YT_COOKIES_B64")
    if not cookies_content:
        print("[CẢNH BÁO] Không tìm thấy biến YT_COOKIES_B64 trên Render.")
        return None
    try:
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        f.write(cookies_content)
        f.close()
        print(f"[INFO] Đã tạo file cookie tạm tại: {f.name}")
        return f.name
    except Exception as e:
        print(f"[LỖI] Không tạo được file cookie tạm: {e}")
        return None


def get_youtube_audio_url(youtube_url: str):
    """Dùng yt-dlp để lấy link stream audio trực tiếp từ YouTube"""
    ydl_opts = {
        'format': 'bestaudio/bestaudio*/best/worst',
        'noplaylist': True,
        'quiet': False,
        # Chỉ định JS runtime cho EJS n challenge solver
        'js_runtimes': {'node': {}},
        # Tự động tải EJS solver script từ GitHub
        'remote_components': ['ejs:github'],
        'extractor_args': {
            'youtube': {
                'player_client': ['web_safari', 'web'],
            }
        },
        # Chống rate-limit: tăng thời gian chờ
        'sleep_interval': 5,
        'max_sleep_interval': 10,
        'sleep_interval_requests': 1,
        'retries': 5,
        'fragment_retries': 5,
    }

    cookie_path = get_cookie_file()
    if cookie_path:
        ydl_opts['cookiefile'] = cookie_path

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            return info['url']
    except Exception as e:
        print(f"[LỖI YOUTUBE]: Không thể trích xuất link từ {youtube_url} -> Chi tiết: {e}")
        raise e
    finally:
        if cookie_path and os.path.exists(cookie_path):
            try:
                os.remove(cookie_path)
            except:
                pass
# =======================================================
# GIAO DIỆN WEB REMOTE CONTROL (TRANG CHỦ)
# =======================================================
@app.get("/", response_class=HTMLResponse)
async def control_panel():
    return """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ESP32 Radio Remote Control</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-900 text-white min-h-screen flex flex-col items-center justify-center p-4">
        <div class="bg-gray-800 p-6 rounded-2xl shadow-xl w-full max-w-md border border-gray-700">
            <h1 class="text-2xl font-bold text-center mb-6 text-cyan-400">📻 ESP32 Radio Remote</h1>
            
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-300 mb-1">Mật khẩu (Token):</label>
                <input type="password" id="token" value="pvt_123456" class="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-cyan-500">
            </div>

            <div class="mb-6 border-t border-gray-700 pt-4">
                <label class="block text-sm font-medium text-gray-300 mb-1">Link YouTube hoặc Playlist:</label>
                <input type="text" id="ytUrl" placeholder="Dán link vào đây..." class="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white mb-3 focus:outline-none focus:border-cyan-500">
                <div class="flex gap-2">
                    <button onclick="changeYoutube()" class="flex-1 bg-cyan-600 hover:bg-cyan-500 font-semibold py-2 px-4 rounded-lg transition duration-200">▶ Phát / Lưu List</button>
                    <button onclick="skipTrack()" class="bg-amber-600 hover:bg-amber-500 font-semibold py-2 px-4 rounded-lg transition duration-200">⏭ Next</button>
                </div>
            </div>

            <div class="border-t border-gray-700 pt-4">
                <label class="block text-sm font-medium text-gray-300 mb-2">Đài Radio Truyền Thống:</label>
                <div class="grid grid-cols-2 gap-2">
                    <button onclick="alert('Hãy trỏ ESP32 tới /stream?station=vov3')" class="bg-gray-700 hover:bg-gray-600 py-2 px-3 rounded-lg text-sm font-medium">VOV 3</button>
                    <button onclick="alert('Hãy trỏ ESP32 tới /stream?station=vovgt_hn')" class="bg-gray-700 hover:bg-gray-600 py-2 px-3 rounded-lg text-sm font-medium">VOV GT HN</button>
                    <button onclick="alert('Hãy trỏ ESP32 tới /stream?station=vovgt_hcm')" class="bg-gray-700 hover:bg-gray-600 py-2 px-3 rounded-lg text-sm font-medium">VOV GT HCM</button>
                    <button onclick="alert('Hãy trỏ ESP32 tới /stream?station=voh956')" class="bg-gray-700 hover:bg-gray-600 py-2 px-3 rounded-lg text-sm font-medium">VOH 95.6</button>
                    <button onclick="alert('Hãy trỏ ESP32 tới /stream?station=hanoi90')" class="bg-gray-700 hover:bg-gray-600 py-2 px-3 rounded-lg text-sm font-medium col-span-2">Hà Nội 90 MHz</button>
                </div>
            </div>

            <div id="status" class="mt-4 p-3 rounded-lg bg-gray-700 text-xs text-gray-300 text-center hidden"></div>
        </div>

        <script>
            function showStatus(msg, isError=false) {
                const el = document.getElementById('status');
                el.innerText = msg;
                el.className = `mt-4 p-3 rounded-lg text-xs text-center ${isError ? 'bg-red-900 text-red-200' : 'bg-green-900 text-green-200'}`;
                el.classList.remove('hidden');
            }

            async function changeYoutube() {
                const url = document.getElementById('ytUrl').value.trim();
                const token = document.getElementById('token').value.trim();
                if(!url) { alert('Vui lòng nhập link YouTube!'); return; }
                
                showStatus('Đang xử lý link và lưu vào bộ nhớ...', false);
                try {
                    const res = await fetch(`/youtube/change?url=${encodeURIComponent(url)}&token=${token}`);
                    const data = await res.json();
                    if(res.ok) {
                        showStatus(data.message);
                    } else {
                        showStatus(data.detail || 'Lỗi hệ thống', true);
                    }
                } catch(e) {
                    showStatus('Không kết nối được server!', true);
                }
            }

            async function skipTrack() {
                const token = document.getElementById('token').value.trim();
                showStatus('Đang chuyển sang bài tiếp theo...', false);
                try {
                    const res = await fetch(`/youtube/skip?token=${token}`);
                    const data = await res.json();
                    if(res.ok) {
                        showStatus(data.message);
                    } else {
                        showStatus(data.detail || data.message, true);
                    }
                } catch(e) {
                    showStatus('Không kết nối được server!', true);
                }
            }
        </script>
    </body>
    </html>
    """


# =======================================================
# PHẦN 1: STREAM ĐÀI RADIO TRUYỀN THỐNG
# =======================================================
def generate_mp3_stream(source_url: str):
    command = [
        'ffmpeg',
        '-user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        '-reconnect', '1',
        '-reconnect_streamed', '1',
        '-reconnect_delay_max', '3',
        '-i', source_url,
        '-vn',
        '-acodec', 'libmp3lame',
        '-ab', '96k',
        '-ar', '32000',
        '-ac', '1',
        '-f', 'mp3',
        'pipe:1'
    ]

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=1024 * 32
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
        if process.poll() is None:
            process.kill()
            process.wait()


@app.get("/stream")
async def stream_radio(
    token: Optional[str] = Query(None),
    station: Optional[str] = Query("vovgt_hn")
):
    if token != SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Token khong hop le!")

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


# =======================================================
# PHẦN 2: HỆ THỐNG YOUTUBE PLAYLIST & VÒNG LẶP VĨNH VIỄN
# =======================================================
@app.get("/youtube/change")
async def change_youtube_link(
    url: str = Query(...),
    token: Optional[str] = Query(None)
):
    global PLAYLIST_ITEMS, CURRENT_INDEX, ACTIVE_FFMPEG_PROCESS

    if token != SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Token khong hop le!")

    if "list=" in url:
        ydl_opts = {
            'extract_flat': True,
            'quiet': True,
        }
        cookie_path = get_cookie_file()
        if cookie_path:
            ydl_opts['cookiefile'] = cookie_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info:
                    PLAYLIST_ITEMS = [
                        entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
                        for entry in info['entries'] if entry.get('url') or entry.get('id')
                    ]
                else:
                    PLAYLIST_ITEMS = [url]
        finally:
            if cookie_path and os.path.exists(cookie_path):
                try:
                    os.remove(cookie_path)
                except:
                    pass
    else:
        PLAYLIST_ITEMS = [url]

    # Reset về bài đầu tiên
    CURRENT_INDEX = 0

    if ACTIVE_FFMPEG_PROCESS and ACTIVE_FFMPEG_PROCESS.poll() is None:
        ACTIVE_FFMPEG_PROCESS.kill()

    return {
        "status": "success",
        "message": f"Đã lưu thành công {len(PLAYLIST_ITEMS)} bài vào danh sách vòng lặp.",
        "total_tracks": len(PLAYLIST_ITEMS)
    }


@app.get("/youtube/stream")
async def stream_dynamic_youtube(token: Optional[str] = Query(None)):
    if token != SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Token khong hop le!")

    def generate_dynamic_stream():
        global ACTIVE_FFMPEG_PROCESS, PLAYLIST_ITEMS, CURRENT_INDEX

        if not PLAYLIST_ITEMS:
            return

        while True:
            current_vid_url = PLAYLIST_ITEMS[CURRENT_INDEX]

            try:
                source_url = get_youtube_audio_url(current_vid_url)
            except Exception as e:
                print(f"[LỖI GET URL]: {e}")
                CURRENT_INDEX = (CURRENT_INDEX + 1) % len(PLAYLIST_ITEMS)
                continue

            command = [
                'ffmpeg',
                '-user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '3',
                '-i', source_url,
                '-vn', '-acodec', 'libmp3lame', '-ab', '96k', '-ar', '32000', '-ac', '1', '-f', 'mp3',
                'pipe:1'
            ]

            ACTIVE_FFMPEG_PROCESS = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
            )

            try:
                while True:
                    chunk = ACTIVE_FFMPEG_PROCESS.stdout.read(2048)
                    if not chunk:
                        break
                    yield chunk
            except Exception as ex:
                print(f"[LỖI STREAM]: {ex}")
                break
            finally:
                if ACTIVE_FFMPEG_PROCESS and ACTIVE_FFMPEG_PROCESS.poll() is None:
                    ACTIVE_FFMPEG_PROCESS.kill()
                    ACTIVE_FFMPEG_PROCESS.wait()

            if PLAYLIST_ITEMS:
                CURRENT_INDEX = (CURRENT_INDEX + 1) % len(PLAYLIST_ITEMS)

    return StreamingResponse(
        generate_dynamic_stream(),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive"
        }
    )


@app.get("/youtube/skip")
async def skip_track(token: Optional[str] = Query(None)):
    global ACTIVE_FFMPEG_PROCESS, PLAYLIST_ITEMS, CURRENT_INDEX

    if token != SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Token khong hop le!")

    if ACTIVE_FFMPEG_PROCESS and ACTIVE_FFMPEG_PROCESS.poll() is None:
        next_idx = (CURRENT_INDEX + 1) % len(PLAYLIST_ITEMS) if PLAYLIST_ITEMS else 0
        ACTIVE_FFMPEG_PROCESS.kill()
        return {
            "status": "success",
            "message": f"Đang chuyển sang bài {next_idx + 1}/{len(PLAYLIST_ITEMS)}"
        }
    else:
        return {"status": "error", "message": "Không có luồng YouTube nào đang chạy."}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)

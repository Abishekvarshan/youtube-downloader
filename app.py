from flask import Flask, render_template, request, send_file, jsonify
import yt_dlp
import os
from threading import Thread
import shutil

app = Flask(__name__)

# ---------------------------
# Global progress dictionary
# ---------------------------
progress_data = {"progress": 0, "status": ""}

# ---------------------------
# Progress hook for yt-dlp
# ---------------------------
def progress_hook(d):
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '0%').replace('%', '').strip()
        try:
            progress_data["progress"] = float(percent)
        except:
            progress_data["progress"] = 0
        progress_data["status"] = "Downloading..."
    elif d['status'] == 'finished':
        progress_data["progress"] = 100
        progress_data["status"] = "Processing..."

# ---------------------------
# Cookies File (Render Secret File)
# ---------------------------
SECRET_COOKIE_PATH = "/etc/secrets/cookies.txt"
WORKING_COOKIE_PATH = "/tmp/cookies.txt"  # yt-dlp needs writable file

if os.path.exists(SECRET_COOKIE_PATH):
    shutil.copy(SECRET_COOKIE_PATH, WORKING_COOKIE_PATH)
    print("[INFO] cookies.txt loaded and copied to /tmp.")
else:
    WORKING_COOKIE_PATH = None
    print("[WARNING] cookies.txt not found. Download may fail for age-restricted/private videos.")

# ---------------------------
# Download function
# ---------------------------
def download_video(url, download_path):
    os.makedirs(download_path, exist_ok=True)

    # Check if cookies file exists and is readable
    cookie_file = WORKING_COOKIE_PATH
    if cookie_file and not os.path.exists(cookie_file):
        cookie_file = None
        print("[WARNING] Cookies file not found. Some videos may fail.")

    # yt-dlp options
    ydl_opts = {
        'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook],
        'format': 'mp4',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'cookiefile': cookie_file,
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/142.0.0.0 Safari/537.36'
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as de:
        # Detect bot/cookies issues
        if "Sign in to confirm" in str(de):
            progress_data["status"] = ("Error: YouTube requires login. "
                                       "Your cookies may be expired or invalid.")
        else:
            progress_data["status"] = f"Download Error: {de}"
        progress_data["progress"] = 0
    except Exception as e:
        progress_data["status"] = f"Unexpected Error: {e}"
        progress_data["progress"] = 0

# ---------------------------
# Routes
# ---------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start-download", methods=["POST"])
def start_download():
    url = request.form.get("url")
    download_path = "downloads"

    # Reset progress
    progress_data["progress"] = 0
    progress_data["status"] = "Starting..."

    Thread(target=download_video, args=(url, download_path)).start()

    return jsonify({"message": "started"})

@app.route("/progress")
def progress():
    return jsonify(progress_data)

@app.route("/download-file")
def download_file():
    download_path = "downloads"
    files = os.listdir(download_path) if os.path.exists(download_path) else []
    if not files:
        return "File not found", 404
    file_path = os.path.join(download_path, files[0])
    return send_file(file_path, as_attachment=True)

# ---------------------------
# Main app
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

from flask import Flask, render_template, request, send_file, jsonify
import yt_dlp
import os
from threading import Thread

app = Flask(__name__)

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
# Prepare cookies file from environment variable
# ---------------------------
COOKIE_FILE_PATH = "cookies/cookies.txt"
os.makedirs("cookies", exist_ok=True)

cookie_content = os.environ.get("YOUTUBE_COOKIES", "")
if cookie_content:
    with open(COOKIE_FILE_PATH, "w") as f:
        f.write(cookie_content)
else:
    print("[WARNING] Environment variable YOUTUBE_COOKIES is not set. YouTube downloads may fail for age-restricted/private videos.")


# ---------------------------
# Background download function
# ---------------------------
def download_video(url, download_path):
    ydl_opts = {
        'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook],
        'format': 'mp4',
        'cookiefile': COOKIE_FILE_PATH,  # Use cookies from env
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


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
    os.makedirs(download_path, exist_ok=True)

    # Reset progress
    progress_data["progress"] = 0
    progress_data["status"] = "Starting..."

    # Download in background thread
    Thread(target=download_video, args=(url, download_path)).start()

    return jsonify({"message": "started"})


@app.route("/progress")
def progress():
    return jsonify(progress_data)


@app.route("/download-file")
def download_file():
    files = os.listdir("downloads")
    if not files:
        return "File not found", 404
    file_path = os.path.join("downloads", files[0])
    return send_file(file_path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)

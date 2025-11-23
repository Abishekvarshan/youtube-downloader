from flask import Flask, render_template, request, send_file, jsonify
import yt_dlp
import os
from threading import Thread

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

# Path where Render stores secret files
COOKIE_FILE_PATH = "/etc/secrets/cookies.txt"

# Check if file exists
if not os.path.exists(COOKIE_FILE_PATH):
    print("[WARNING] cookies.txt not found inside /etc/secrets/.")
else:
    print("[INFO] cookies.txt loaded successfully.")


# ---------------------------
# Background download function
# ---------------------------
def download_video(url, download_path):
    ydl_opts = {
        'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook],
        'format': 'mp4',
        'cookiefile': COOKIE_FILE_PATH,   # use the secret file cookies
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

    progress_data["progress"] = 0
    progress_data["status"] = "Starting..."

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


# ---------------------------
# Main app
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

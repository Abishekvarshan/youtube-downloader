import os
import uuid
import threading
import time
from flask import Flask, render_template, request, jsonify, send_file, abort
import yt_dlp

app = Flask(__name__, static_folder='static', template_folder='templates')

DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

jobs = {}  # job_id -> status/log/output

# -----------------------------
# Progress hook for yt-dlp
# -----------------------------
def make_hook(job_id):
    def hook(d):
        j = jobs.get(job_id)
        if not j:
            return
        if d.get("status") == "downloading":
            j["status"] = "downloading"
            j["progress"] = d.get("_percent_str") or "0%"
            j["log"].append(f"[{time.strftime('%H:%M:%S')}] Downloading: {d.get('filename','')} {d.get('_percent_str','')}")
        elif d.get("status") == "finished":
            j["status"] = "finished_download"
            j["log"].append(f"[{time.strftime('%H:%M:%S')}] Finished download")
        elif d.get("status") == "error":
            j["status"] = "error"
            j["log"].append(f"[{time.strftime('%H:%M:%S')}] ERROR: {d}")
    return hook

# -----------------------------
# Background download function
# -----------------------------
def run_download(job_id, url):
    job = jobs[job_id]
    job["log"].append(f"[{time.strftime('%H:%M:%S')}] Starting download: {url}")
    out_template = os.path.join(DOWNLOAD_FOLDER, f"{job_id}.%(ext)s")
    ydl_opts = {
        "format": "best",
        "outtmpl": out_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [make_hook(job_id)],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        job["status"] = "done"
        job["output"] = find_output_file(job_id)
        job["log"].append(f"[{time.strftime('%H:%M:%S')}] Download completed")
    except Exception as e:
        job["status"] = "error"
        job["log"].append(f"[ERROR] {str(e)}")

def find_output_file(job_id):
    for f in os.listdir(DOWNLOAD_FOLDER):
        if f.startswith(job_id):
            return os.path.join(DOWNLOAD_FOLDER, f)
    return None

# -----------------------------
# Routes
# -----------------------------
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start():
    url = request.form.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "queued", "progress": "0%", "log": [], "output": None}

    threading.Thread(target=run_download, args=(job_id, url)).start()
    return jsonify({"job_id": job_id})

@app.route("/status/<job_id>")
def status(job_id):
    j = jobs.get(job_id)
    if not j:
        abort(404)
    return jsonify(j)

@app.route("/download/<job_id>")
def download(job_id):
    j = jobs.get(job_id)
    if not j or not j.get("output"):
        abort(404)
    return send_file(j["output"], as_attachment=True)

if __name__ == "__main__":
    print("Starting Flask server on http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)

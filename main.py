import os
import asyncio
import json
import uuid
import gc
from queue import Queue, Empty
from threading import Thread
from urllib.parse import parse_qs, urlparse
from flask import Flask, request, jsonify, Response, stream_with_context, render_template, redirect, url_for
from dotenv import load_dotenv

from src.pipelines.agribusiness_pipeline import run_agribusiness_pipeline
from src.pipelines.report_followup_pipeline import run_report_followup
from src.pipelines.government_policy_pipeline import run_government_policy_search
from database.db import init_app_db, create_tables # Using db.py from reference if applicable, else mock

load_dotenv()

app = Flask(__name__)

VIDEO_LIBRARY_FILE = os.path.join(app.root_path, "database", "video_library_urls.txt")
STARTUP_LIBRARY_FILE = os.path.join(
    app.root_path, "database", "startup_reference_library.txt"
)


def _extract_youtube_video_id(url: str) -> str | None:
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return None

    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    path = parsed.path.strip("/")
    video_id = None

    if host == "youtu.be":
        video_id = path.split("/")[0] if path else None
    elif host.endswith("youtube.com"):
        if path == "watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        elif path.startswith("shorts/") or path.startswith("embed/") or path.startswith("live/"):
            parts = path.split("/")
            video_id = parts[1] if len(parts) > 1 else None

    if not video_id:
        return None

    video_id = video_id.strip().split("?")[0].split("&")[0]
    if len(video_id) != 11:
        return None
    return video_id


def _parse_video_line(line: str, index: int) -> dict | None:
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return None

    title = ""
    url = ""
    if "|" in raw:
        first, second = [part.strip() for part in raw.split("|", 1)]
        if first.lower().startswith("http"):
            url = first
            title = second
        else:
            title = first
            url = second
    else:
        url = raw

    if not url.lower().startswith("http"):
        return None

    video_id = _extract_youtube_video_id(url)
    if not video_id:
        return None

    if not title:
        title = f"Video {index}"

    return {
        "title": title,
        "url": url,
        "video_id": video_id,
        "embed_url": f"https://www.youtube.com/embed/{video_id}",
    }


def load_video_library(file_path: str = VIDEO_LIBRARY_FILE) -> list[dict]:
    videos = []
    if not os.path.exists(file_path):
        return videos

    with open(file_path, "r", encoding="utf-8") as f:
        for index, line in enumerate(f, start=1):
            parsed = _parse_video_line(line, index)
            if parsed:
                videos.append(parsed)

    return videos


def read_library_text(file_path: str) -> str:
    if not os.path.exists(file_path):
        return ""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def write_library_text(file_path: str, content: str) -> None:
    normalized = (content or "").replace("\r\n", "\n")
    if len(normalized) > 120000:
        raise ValueError("Library content is too large.")

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(normalized.strip() + "\n" if normalized.strip() else "")


def _parse_startup_line(line: str, index: int) -> dict | None:
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return None

    parts = [part.strip() for part in raw.split("|")]
    parts = [part for part in parts if part]
    if len(parts) < 2:
        return None

    name = parts[0]
    leverage = parts[1]
    description = ""
    url = ""

    if len(parts) >= 3:
        third = parts[2]
        if third.lower().startswith("http"):
            url = third
        else:
            description = third

    if len(parts) >= 4:
        url = parts[3]

    if url and not url.lower().startswith("http"):
        url = ""

    return {
        "id": index,
        "name": name,
        "leverage": leverage,
        "description": description,
        "url": url,
    }


def load_startup_library(file_path: str = STARTUP_LIBRARY_FILE) -> list[dict]:
    startups = []
    if not os.path.exists(file_path):
        return startups

    with open(file_path, "r", encoding="utf-8") as f:
        for index, line in enumerate(f, start=1):
            parsed = _parse_startup_line(line, index)
            if parsed:
                startups.append(parsed)

    return startups

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/videos")
def videos():
    video_items = load_video_library()
    saved = request.args.get("saved") == "1"
    return render_template(
        "videos.html",
        videos=video_items,
        library_file="database/video_library_urls.txt",
        library_raw=read_library_text(VIDEO_LIBRARY_FILE),
        save_success=saved,
    )


@app.route("/startups")
def startups():
    startup_items = load_startup_library()
    saved = request.args.get("saved") == "1"
    return render_template(
        "startups.html",
        startup_refs=startup_items,
        startup_file="database/startup_reference_library.txt",
        startup_raw=read_library_text(STARTUP_LIBRARY_FILE),
        save_success=saved,
    )


@app.route("/policies", methods=["GET", "POST"])
def policies():
    form = {
        "location": "",
        "crops": "",
        "language": "en",
    }
    policy_report = ""
    policy_sources = []
    policy_error = ""

    if request.method == "POST":
        form["location"] = str(request.form.get("location", "")).strip()
        form["crops"] = str(request.form.get("crops", "")).strip()
        form["language"] = str(request.form.get("language", "en")).strip() or "en"

        if not form["location"] or not form["crops"]:
            policy_error = "Please enter both location and crops."
        else:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    run_government_policy_search(
                        location=form["location"],
                        crops=form["crops"],
                        language=form["language"],
                    )
                )
                policy_report = result.get("report_markdown", "")
                policy_sources = result.get("sources", [])
            except Exception as e:
                import traceback
                traceback.print_exc()
                policy_error = str(e)
            finally:
                _graceful_close_loop(loop)

    return render_template(
        "policies.html",
        form=form,
        policy_report=policy_report,
        policy_sources=policy_sources,
        policy_error=policy_error,
    )


@app.route("/library/videos/save", methods=["POST"])
def save_video_library():
    content = request.form.get("library_content", "")
    try:
        write_library_text(VIDEO_LIBRARY_FILE, content)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return redirect(url_for("videos", saved=1))


@app.route("/library/startups/save", methods=["POST"])
def save_startup_library():
    content = request.form.get("library_content", "")
    try:
        write_library_text(STARTUP_LIBRARY_FILE, content)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return redirect(url_for("startups", saved=1))
# Basic config
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key')

# Simple in-memory job store for MVP
JOBS = {}
JOB_QUEUES = {}

def _graceful_close_loop(loop: asyncio.AbstractEventLoop):
    """Drain pending async cleanup tasks before closing the thread-local loop."""
    try:
        # Trigger GC so sdk destructors can enqueue any close tasks on this loop.
        gc.collect()
        loop.run_until_complete(asyncio.sleep(0))

        pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
        if pending:
            done, pending = loop.run_until_complete(asyncio.wait(pending, timeout=2))
            if pending:
                for task in pending:
                    task.cancel()
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

        loop.run_until_complete(loop.shutdown_asyncgens())
        if hasattr(loop, "shutdown_default_executor"):
            loop.run_until_complete(loop.shutdown_default_executor())
    except Exception:
        import traceback
        traceback.print_exc()
    finally:
        asyncio.set_event_loop(None)
        loop.close()

def _run_job_background(job_id, user_input, language='en'):
    q = JOB_QUEUES[job_id]
    
    def progress_cb(data):
        q.put(data)
        
    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(
            run_agribusiness_pipeline(user_input, progress_cb, language=language)
        )
        JOBS[job_id]["status"] = "completed"
        JOBS[job_id]["report"] = result
        q.put({"event": "complete", "result": result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = str(e)
        q.put({"event": "error", "message": str(e)})
    finally:
        _graceful_close_loop(loop)

@app.route('/health')
def health():
    return jsonify({"status": "ok", "model": os.environ.get("GEMINI_MODEL_ID")})

@app.route('/api/plan', methods=['POST'])
def create_plan():
    data = request.json
    user_input = data.get('message', '')
    language = data.get('language', 'en') # Default to English
    
    if not user_input:
        return jsonify({"error": "message is required"}), 400
        
    job_id = str(uuid.uuid4())
    JOB_QUEUES[job_id] = Queue()
    JOBS[job_id] = {"status": "started", "report": None, "followups": []}
    
    # Start background thread
    t = Thread(target=_run_job_background, args=(job_id, user_input, language))
    t.start()
    
    return jsonify({"job_id": job_id})

@app.route('/api/plan/<job_id>/stream')
def stream_plan(job_id):
    if job_id not in JOB_QUEUES:
        return jsonify({"error": "Job not found"}), 404
        
    q = JOB_QUEUES[job_id]
    
    def generate():
        print(f"DEBUG: Starting stream for job {job_id}")
        while True:
            try:
                # Wait for data
                data = q.get(timeout=60) # 1 min timeout for keepalive
                
                if data.get("step"):
                    step_name = data.get("step")
                    status = data.get("status")
                    print(f"DEBUG: Agent Step: {step_name} [{status}]")
                
                yield f"data: {json.dumps(data)}\n\n"
                
                if data.get("event") in ["complete", "error"]:
                    print(f"DEBUG: Job {job_id} finished with {data.get('event')}")
                    break
            except Empty:
                print(f"DEBUG: Timeout waiting for data for {job_id}, sending keep-alive")
                yield ": keep-alive\n\n"
            except Exception as e:
                print(f"DEBUG: Generator error for {job_id}: {e}")
                import traceback
                traceback.print_exc()
                # Try to send error to client
                yield f"data: {json.dumps({'event': 'error', 'message': 'Server generator error: ' + str(e)})}\n\n"
                break
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@app.route('/api/followup', methods=['POST'])
def followup_question():
    data = request.get_json(silent=True) or {}
    job_id = str(data.get('job_id', '')).strip()
    question = str(data.get('question', '')).strip()
    language = str(data.get('language', 'en')).strip() or 'en'
    history = data.get('history') if isinstance(data.get('history'), list) else []

    if not job_id:
        return jsonify({"error": "job_id is required"}), 400
    if not question:
        return jsonify({"error": "question is required"}), 400

    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if not job.get("report"):
        return jsonify({"error": "Report is not ready for this job yet"}), 409

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        answer = loop.run_until_complete(
            run_report_followup(
                report_markdown=job["report"],
                question=question,
                language=language,
                history=history,
            )
        )
        job.setdefault("followups", []).append(
            {"question": question, "answer": answer, "language": language}
        )
        return jsonify({"answer": answer})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        _graceful_close_loop(loop)

if __name__ == '__main__':
    # Ensure src is in path if needed, though usually python adds current dir
    print("Starting AgriBusiness OS...")
    print(f"Model: {os.environ.get('GEMINI_MODEL_ID', 'default')}")
    # Disable reloader to prevent restarting loops on site-package changes
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

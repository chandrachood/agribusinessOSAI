import os
import asyncio
import json
import uuid
import gc
import importlib
from datetime import datetime, timezone
from functools import lru_cache
from queue import Queue, Empty
from threading import Thread, Lock
from time import perf_counter
from urllib.parse import parse_qs, urlparse
from flask import Flask, request, jsonify, Response, stream_with_context, render_template, redirect, url_for
from dotenv import load_dotenv
from database.db import init_app_db, create_tables # Using db.py from reference if applicable, else mock

load_dotenv()

app = Flask(__name__)

VIDEO_LIBRARY_FILE = os.path.join(app.root_path, "database", "video_library_urls.txt")
STARTUP_LIBRARY_FILE = os.path.join(
    app.root_path, "database", "startup_reference_library.txt"
)


@lru_cache(maxsize=None)
def _load_runtime_callable(module_path: str, attr_name: str):
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as exc:
        missing = exc.name or module_path
        raise RuntimeError(
            f"Missing dependency '{missing}'. Install the project requirements in the active environment before using this feature."
        ) from exc

    try:
        return getattr(module, attr_name)
    except AttributeError as exc:
        raise RuntimeError(
            f"Application misconfiguration: '{module_path}.{attr_name}' is unavailable."
        ) from exc


def _get_agribusiness_pipeline():
    return _load_runtime_callable(
        "src.pipelines.agribusiness_pipeline",
        "run_agribusiness_pipeline",
    )


def _get_report_followup_pipeline():
    return _load_runtime_callable(
        "src.pipelines.report_followup_pipeline",
        "run_report_followup",
    )


def _get_government_policy_pipeline():
    return _load_runtime_callable(
        "src.pipelines.government_policy_pipeline",
        "run_government_policy_search",
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


def load_video_library(file_path: str | None = None) -> list[dict]:
    file_path = file_path or VIDEO_LIBRARY_FILE
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


def load_startup_library(file_path: str | None = None) -> list[dict]:
    file_path = file_path or STARTUP_LIBRARY_FILE
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
    save_error = str(request.args.get("error", "")).strip()
    return render_template(
        "videos.html",
        videos=video_items,
        library_file="database/video_library_urls.txt",
        library_raw=read_library_text(VIDEO_LIBRARY_FILE),
        save_success=saved,
        save_error=save_error,
    )


@app.route("/startups")
def startups():
    startup_items = load_startup_library()
    saved = request.args.get("saved") == "1"
    save_error = str(request.args.get("error", "")).strip()
    return render_template(
        "startups.html",
        startup_refs=startup_items,
        startup_file="database/startup_reference_library.txt",
        startup_raw=read_library_text(STARTUP_LIBRARY_FILE),
        save_success=saved,
        save_error=save_error,
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
            try:
                run_government_policy_search = _get_government_policy_pipeline()
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
                finally:
                    _graceful_close_loop(loop)
            except RuntimeError as e:
                policy_error = str(e)
            except Exception as e:
                import traceback
                traceback.print_exc()
                policy_error = str(e)

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
    except OSError:
        app.logger.exception("Failed to save video library: %s", VIDEO_LIBRARY_FILE)
        return redirect(
            url_for("videos", error="Unable to save video library. Check file permissions.")
        )
    return redirect(url_for("videos", saved=1))


@app.route("/library/startups/save", methods=["POST"])
def save_startup_library():
    content = request.form.get("library_content", "")
    try:
        write_library_text(STARTUP_LIBRARY_FILE, content)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except OSError:
        app.logger.exception("Failed to save startup library: %s", STARTUP_LIBRARY_FILE)
        return redirect(
            url_for(
                "startups",
                error="Unable to save startup library. Check file permissions.",
            )
        )
    return redirect(url_for("startups", saved=1))
# Basic config
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key')

# Simple in-memory job store for MVP
JOBS = {}
JOB_QUEUES = {}
TRACE_LOCK = Lock()
TRACE_MAX_EVENTS = int(os.environ.get("TRACE_MAX_EVENTS", "800"))
TRACE_INCLUDE_INPUT_PREVIEW = os.environ.get("TRACE_INCLUDE_INPUT_PREVIEW", "0") == "1"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_excerpt(text: str, max_len: int = 220) -> str:
    value = (text or "").replace("\n", " ").strip()
    return value[:max_len] + ("..." if len(value) > max_len else "")


def _trace(job_id: str, event: str, **fields):
    record = {
        "ts": _utc_now_iso(),
        "event": event,
        **fields,
    }
    with TRACE_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return
        traces = job.setdefault("trace", [])
        traces.append(record)
        if len(traces) > TRACE_MAX_EVENTS:
            del traces[:-TRACE_MAX_EVENTS]
    app.logger.info(
        "trace job=%s event=%s fields=%s",
        job_id,
        event,
        json.dumps(fields, ensure_ascii=False, default=str),
    )

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
    started_at = perf_counter()
    step_started: dict[str, float] = {}

    def progress_cb(data):
        q.put(data)
        step = str(data.get("step", "")).strip()
        status = str(data.get("status", "")).strip()
        if not step:
            return

        if status == "running":
            step_started[step] = perf_counter()
            _trace(job_id, "agent_step_running", step=step)
            return

        if status == "completed":
            started = step_started.pop(step, None)
            duration_ms = round((perf_counter() - started) * 1000, 2) if started else None
            output_chars = len(str(data.get("output", "") or ""))
            _trace(
                job_id,
                "agent_step_completed",
                step=step,
                duration_ms=duration_ms,
                output_chars=output_chars,
            )
            return

        _trace(job_id, "agent_step_update", step=step, status=status)
        
    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _trace(job_id, "job_runner_started", language=language, input_chars=len(user_input or ""))

    try:
        run_agribusiness_pipeline = _get_agribusiness_pipeline()
        result = loop.run_until_complete(
            run_agribusiness_pipeline(user_input, progress_cb, language=language)
        )
        JOBS[job_id]["status"] = "completed"
        JOBS[job_id]["report"] = result
        q.put({"event": "complete", "result": result})
        _trace(
            job_id,
            "job_runner_completed",
            duration_ms=round((perf_counter() - started_at) * 1000, 2),
            report_chars=len(result or ""),
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = str(e)
        q.put({"event": "error", "message": str(e)})
        _trace(
            job_id,
            "job_runner_failed",
            duration_ms=round((perf_counter() - started_at) * 1000, 2),
            error=str(e),
        )
    finally:
        _graceful_close_loop(loop)

@app.route('/health')
def health():
    return jsonify({"status": "ok", "model": os.environ.get("GEMINI_MODEL_ID")})

@app.route('/api/trace/<job_id>')
def get_trace(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    limit_raw = request.args.get("limit", "300")
    try:
        limit = int(limit_raw)
    except ValueError:
        limit = 300
    limit = max(1, min(limit, 2000))

    all_events = job.get("trace", [])
    events = all_events[-limit:]

    step_metrics = []
    for event in all_events:
        if event.get("event") == "agent_step_completed":
            step_metrics.append(
                {
                    "step": event.get("step"),
                    "duration_ms": event.get("duration_ms"),
                    "output_chars": event.get("output_chars"),
                }
            )

    return jsonify(
        {
            "job_id": job_id,
            "status": job.get("status"),
            "error": job.get("error"),
            "event_count": len(all_events),
            "events": events,
            "step_metrics": step_metrics,
        }
    )

@app.route('/api/plan', methods=['POST'])
def create_plan():
    data = request.json
    user_input = data.get('message', '')
    language = data.get('language', 'en') # Default to English
    
    if not user_input:
        return jsonify({"error": "message is required"}), 400

    try:
        _get_agribusiness_pipeline()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
        
    job_id = str(uuid.uuid4())
    JOB_QUEUES[job_id] = Queue()
    JOBS[job_id] = {"status": "started", "report": None, "followups": [], "trace": []}
    trace_fields = {
        "language": language,
        "input_chars": len(user_input),
    }
    if TRACE_INCLUDE_INPUT_PREVIEW:
        trace_fields["input_preview"] = _safe_excerpt(user_input)
    _trace(job_id, "job_created", **trace_fields)
    
    # Start background thread
    t = Thread(target=_run_job_background, args=(job_id, user_input, language))
    t.start()
    
    return jsonify({"job_id": job_id, "trace_url": f"/api/trace/{job_id}"})

@app.route('/api/plan/<job_id>/stream')
def stream_plan(job_id):
    if job_id not in JOB_QUEUES:
        return jsonify({"error": "Job not found"}), 404
        
    q = JOB_QUEUES[job_id]
    
    def generate():
        _trace(job_id, "stream_connected")
        print(f"DEBUG: Starting stream for job {job_id}")
        try:
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
                        terminal_event = str(data.get("event"))
                        _trace(job_id, "stream_terminal_event", event_type=terminal_event)
                        print(f"DEBUG: Job {job_id} finished with {terminal_event}")
                        break
                except Empty:
                    print(f"DEBUG: Timeout waiting for data for {job_id}, sending keep-alive")
                    yield ": keep-alive\n\n"
                except Exception as e:
                    print(f"DEBUG: Generator error for {job_id}: {e}")
                    import traceback
                    traceback.print_exc()
                    _trace(job_id, "stream_generator_error", error=str(e))
                    # Try to send error to client
                    yield f"data: {json.dumps({'event': 'error', 'message': 'Server generator error: ' + str(e)})}\n\n"
                    break
        finally:
            _trace(job_id, "stream_disconnected")
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@app.route('/api/followup', methods=['POST'])
def followup_question():
    data = request.get_json(silent=True) or {}
    job_id = str(data.get('job_id', '')).strip()
    question = str(data.get('question', '')).strip()
    language = str(data.get('language', 'en')).strip() or 'en'
    incoming_history = data.get('history') if isinstance(data.get('history'), list) else []

    if not job_id:
        return jsonify({"error": "job_id is required"}), 400
    if not question:
        return jsonify({"error": "question is required"}), 400

    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if not job.get("report"):
        return jsonify({"error": "Report is not ready for this job yet"}), 409

    # Build durable history from server-side memory first.
    server_history = []
    for item in job.get("followups", []):
        q = str(item.get("question", "")).strip()
        a = str(item.get("answer", "")).strip()
        if q:
            server_history.append({"role": "user", "content": q})
        if a:
            server_history.append({"role": "assistant", "content": a})

    # Merge client + server history, de-duplicate exact role/content pairs, keep recency.
    merged_history = []
    seen_pairs = set()
    for turn in server_history + incoming_history:
        if not isinstance(turn, dict):
            continue
        role = str(turn.get("role", "")).strip().lower()
        content = str(turn.get("content", "")).strip()
        if role not in {"user", "assistant"} or not content:
            continue
        pair = (role, content)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        merged_history.append({"role": role, "content": content})

    # Keep a larger but bounded memory window.
    merged_history = merged_history[-40:]
    _trace(
        job_id,
        "followup_received",
        language=language,
        question_chars=len(question),
        client_history_turns=len(incoming_history),
        merged_history_turns=len(merged_history),
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        run_report_followup = _get_report_followup_pipeline()
        answer = loop.run_until_complete(
            run_report_followup(
                report_markdown=job["report"],
                question=question,
                language=language,
                history=merged_history,
            )
        )
        job.setdefault("followups", []).append(
            {"question": question, "answer": answer, "language": language}
        )
        _trace(job_id, "followup_answered", answer_chars=len(answer))
        return jsonify({"answer": answer})
    except Exception as e:
        import traceback
        traceback.print_exc()
        _trace(job_id, "followup_failed", error=str(e))
        return jsonify({"error": str(e)}), 500
    finally:
        _graceful_close_loop(loop)

if __name__ == '__main__':
    # Ensure src is in path if needed, though usually python adds current dir
    print("Starting AgriBusiness OS...")
    print(f"Model: {os.environ.get('GEMINI_MODEL_ID', 'default')}")
    # Disable reloader to prevent restarting loops on site-package changes
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

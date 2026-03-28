import os
import tempfile
import unittest
from unittest import mock

import main


class ImmediateThread:
    def __init__(self, target=None, args=(), kwargs=None):
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}

    def start(self):
        if self._target:
            self._target(*self._args, **self._kwargs)


class AppFlowRoutesTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.video_file = os.path.join(self.temp_dir.name, "video_library_urls.txt")
        self.startup_file = os.path.join(
            self.temp_dir.name,
            "startup_reference_library.txt",
        )
        self.video_patch = mock.patch.object(main, "VIDEO_LIBRARY_FILE", self.video_file)
        self.startup_patch = mock.patch.object(
            main,
            "STARTUP_LIBRARY_FILE",
            self.startup_file,
        )
        self.video_patch.start()
        self.startup_patch.start()
        main.JOBS.clear()
        main.JOB_QUEUES.clear()
        self.client = main.app.test_client()
        main.write_library_text(
            self.video_file,
            "Seed Video | https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )
        main.write_library_text(
            self.startup_file,
            "Seed Startup | Supply chain | Example startup description | https://example.com/startup",
        )

    def tearDown(self):
        main.JOBS.clear()
        main.JOB_QUEUES.clear()
        self.video_patch.stop()
        self.startup_patch.stop()
        self.temp_dir.cleanup()

    def _install_completed_plan_job(self):
        async def fake_pipeline(user_input, progress_cb, session_service=None, language="en"):
            progress_cb(
                {
                    "step": "pipeline_start",
                    "status": "running",
                    "message": f"Starting AgriBusiness OS AI Analysis in {language}",
                }
            )
            progress_cb({"step": "cultivator", "status": "running"})
            progress_cb(
                {
                    "step": "cultivator",
                    "status": "completed",
                    "output": f"Profile for {user_input}",
                }
            )
            progress_cb({"step": "final_consolidator", "status": "running"})
            progress_cb(
                {
                    "step": "final_consolidator",
                    "status": "completed",
                    "output": "# Final Report",
                }
            )
            return "# Final Report\n\n## Executive Summary\n- Viable crop plan"

        with mock.patch("main._get_agribusiness_pipeline", return_value=fake_pipeline):
            with mock.patch("main.Thread", ImmediateThread):
                response = self.client.post(
                    "/api/plan",
                    json={"message": "5 acres in Dharwad", "language": "en"},
                )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("job_id", data)
        return data["job_id"], data["trace_url"]

    def test_index_and_health_routes_render(self):
        index_response = self.client.get("/")
        health_response = self.client.get("/health")

        self.assertEqual(index_response.status_code, 200)
        self.assertIn(b"AgriBusiness OS AI", index_response.data)
        self.assertEqual(health_response.status_code, 200)
        self.assertEqual(health_response.get_json()["status"], "ok")

    def test_video_library_save_flow_succeeds(self):
        payload = (
            "Video One | https://www.youtube.com/watch?v=dQw4w9WgXcQ\n"
            "https://youtu.be/3JZ_D3ELwOQ"
        )

        response = self.client.post(
            "/library/videos/save",
            data={"library_content": payload},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/videos?saved=1"))
        self.assertEqual(main.read_library_text(self.video_file), payload + "\n")

        page = self.client.get("/videos")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Video One", page.data)

    def test_video_library_save_flow_handles_validation_and_write_errors(self):
        with mock.patch("main.write_library_text", side_effect=ValueError("Library content is too large.")):
            response = self.client.post(
                "/library/videos/save",
                data={"library_content": "x" * 200000},
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "Library content is too large."})

        with mock.patch("main.write_library_text", side_effect=OSError("denied")):
            response = self.client.post(
                "/library/videos/save",
                data={"library_content": "Video"},
            )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/videos?error=", response.headers["Location"])

    def test_create_plan_requires_message(self):
        response = self.client.post("/api/plan", json={"message": "", "language": "en"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "message is required"})

    def test_create_plan_stream_and_trace_flow(self):
        job_id, trace_url = self._install_completed_plan_job()

        self.assertEqual(trace_url, f"/api/trace/{job_id}")
        self.assertEqual(main.JOBS[job_id]["status"], "completed")
        self.assertIn("Executive Summary", main.JOBS[job_id]["report"])

        stream_response = self.client.get(f"/api/plan/{job_id}/stream")
        stream_text = stream_response.get_data(as_text=True)
        self.assertEqual(stream_response.status_code, 200)
        self.assertIn('"step": "cultivator"', stream_text)
        self.assertIn('"event": "complete"', stream_text)

        trace_response = self.client.get(trace_url)
        trace_body = trace_response.get_json()
        self.assertEqual(trace_response.status_code, 200)
        self.assertEqual(trace_body["status"], "completed")
        self.assertGreaterEqual(trace_body["event_count"], 3)
        self.assertTrue(
            any(metric["step"] == "cultivator" for metric in trace_body["step_metrics"])
        )

    def test_stream_and_trace_return_not_found_for_unknown_job(self):
        stream_response = self.client.get("/api/plan/missing-job/stream")
        trace_response = self.client.get("/api/trace/missing-job")

        self.assertEqual(stream_response.status_code, 404)
        self.assertEqual(stream_response.get_json(), {"error": "Job not found"})
        self.assertEqual(trace_response.status_code, 404)
        self.assertEqual(trace_response.get_json(), {"error": "Job not found"})

    def test_followup_validates_required_state(self):
        missing_job_id = self.client.post("/api/followup", json={"question": "Next?"})
        missing_question = self.client.post("/api/followup", json={"job_id": "job-1"})
        not_found = self.client.post(
            "/api/followup",
            json={"job_id": "job-404", "question": "Next?"},
        )

        main.JOBS["job-pending"] = {"status": "started", "report": None, "followups": [], "trace": []}
        not_ready = self.client.post(
            "/api/followup",
            json={"job_id": "job-pending", "question": "Next?"},
        )

        self.assertEqual(missing_job_id.status_code, 400)
        self.assertEqual(missing_job_id.get_json(), {"error": "job_id is required"})
        self.assertEqual(missing_question.status_code, 400)
        self.assertEqual(missing_question.get_json(), {"error": "question is required"})
        self.assertEqual(not_found.status_code, 404)
        self.assertEqual(not_found.get_json(), {"error": "Job not found"})
        self.assertEqual(not_ready.status_code, 409)
        self.assertEqual(
            not_ready.get_json(),
            {"error": "Report is not ready for this job yet"},
        )

    def test_followup_flow_merges_history_and_persists_answer(self):
        captured = {}
        main.JOBS["job-followup"] = {
            "status": "completed",
            "report": "# Report",
            "followups": [
                {
                    "question": "What is the best crop?",
                    "answer": "Banana fits best.",
                    "language": "en",
                }
            ],
            "trace": [],
        }

        async def fake_followup(report_markdown, question, language="en", history=None):
            captured["report_markdown"] = report_markdown
            captured["question"] = question
            captured["language"] = language
            captured["history"] = history
            return "Focus on banana and drip irrigation."

        with mock.patch("main._get_report_followup_pipeline", return_value=fake_followup):
            response = self.client.post(
                "/api/followup",
                json={
                    "job_id": "job-followup",
                    "question": "What should I do next?",
                    "language": "en",
                    "history": [
                        {"role": "assistant", "content": "Banana fits best."},
                        {"role": "user", "content": "Can I store it?"},
                    ],
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {"answer": "Focus on banana and drip irrigation."},
        )
        self.assertEqual(captured["report_markdown"], "# Report")
        self.assertEqual(captured["question"], "What should I do next?")
        self.assertEqual(captured["language"], "en")
        self.assertEqual(
            captured["history"],
            [
                {"role": "user", "content": "What is the best crop?"},
                {"role": "assistant", "content": "Banana fits best."},
                {"role": "user", "content": "Can I store it?"},
            ],
        )
        self.assertEqual(
            main.JOBS["job-followup"]["followups"][-1],
            {
                "question": "What should I do next?",
                "answer": "Focus on banana and drip irrigation.",
                "language": "en",
            },
        )

    def test_followup_returns_server_error_when_pipeline_fails(self):
        main.JOBS["job-followup-error"] = {
            "status": "completed",
            "report": "# Report",
            "followups": [],
            "trace": [],
        }

        async def failing_followup(report_markdown, question, language="en", history=None):
            raise RuntimeError("follow-up model unavailable")

        with mock.patch("main._get_report_followup_pipeline", return_value=failing_followup):
            response = self.client.post(
                "/api/followup",
                json={
                    "job_id": "job-followup-error",
                    "question": "What now?",
                },
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json(), {"error": "follow-up model unavailable"})

    def test_policy_page_validates_inputs(self):
        response = self.client.post(
            "/policies",
            data={"location": "", "crops": "", "language": "en"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Please enter both location and crops.", response.data)

    def test_policy_search_flow_renders_report_and_sources(self):
        async def fake_policy_search(location, crops, language="en"):
            self.assertEqual(location, "Mysuru, Karnataka")
            self.assertEqual(crops, "banana, maize")
            self.assertEqual(language, "hi")
            return {
                "report_markdown": "## Subsidies\n- Example subsidy",
                "sources": [
                    {
                        "title": "Official Portal",
                        "url": "https://example.gov.in/scheme",
                    }
                ],
            }

        with mock.patch("main._get_government_policy_pipeline", return_value=fake_policy_search):
            response = self.client.post(
                "/policies",
                data={
                    "location": "Mysuru, Karnataka",
                    "crops": "banana, maize",
                    "language": "hi",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Example subsidy", response.data)
        self.assertIn(b"Official Portal", response.data)
        self.assertIn(b"Mysuru, Karnataka", response.data)

    def test_policy_search_dependency_error_is_rendered(self):
        with mock.patch(
            "main._get_government_policy_pipeline",
            side_effect=RuntimeError("Missing dependency 'google.genai'."),
        ):
            response = self.client.post(
                "/policies",
                data={
                    "location": "Mysuru, Karnataka",
                    "crops": "banana",
                    "language": "en",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Missing dependency", response.data)


if __name__ == "__main__":
    unittest.main()

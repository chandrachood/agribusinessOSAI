import os
import tempfile
import unittest
from unittest import mock

import main


class ResourceLibraryRoutesTest(unittest.TestCase):
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
        self.client = main.app.test_client()

    def tearDown(self):
        self.video_patch.stop()
        self.startup_patch.stop()
        self.temp_dir.cleanup()

    def test_resource_pages_render_without_loading_ai_pipelines(self):
        main.write_library_text(
            self.video_file,
            "Seed Video | https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )
        main.write_library_text(
            self.startup_file,
            "Seed Startup | Supply chain | Example startup description | https://example.com/startup",
        )

        with mock.patch("main._load_runtime_callable", side_effect=AssertionError("unexpected import")):
            video_response = self.client.get("/videos")
            startup_response = self.client.get("/startups")

        self.assertEqual(video_response.status_code, 200)
        self.assertIn(b"Seed Video", video_response.data)
        self.assertEqual(startup_response.status_code, 200)
        self.assertIn(b"Seed Startup", startup_response.data)
        self.assertIn(b"Expand details", startup_response.data)
        self.assertIn(b"Visit website", startup_response.data)
        self.assertIn(b"https://example.com/startup", startup_response.data)

    def test_startup_library_save_writes_expected_content(self):
        payload = (
            "DeHaat | Full-stack platform | Advisory and market linkage\n"
            "Ninjacart | Supply chain | Buyer-seller logistics"
        )

        response = self.client.post(
            "/library/startups/save",
            data={"library_content": payload},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/startups?saved=1"))
        self.assertEqual(main.read_library_text(self.startup_file), payload + "\n")

    def test_startup_library_save_shows_error_when_write_fails(self):
        with mock.patch("main.write_library_text", side_effect=OSError("denied")):
            response = self.client.post(
                "/library/startups/save",
                data={"library_content": "Example | Leverage"},
                follow_redirects=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Unable to save startup library. Check file permissions.", response.data)

    def test_create_plan_fails_fast_when_ai_dependency_is_missing(self):
        with mock.patch(
            "main._get_agribusiness_pipeline",
            side_effect=RuntimeError("Missing dependency 'google.adk'."),
        ):
            response = self.client.post(
                "/api/plan",
                json={"message": "Farm in Dharwad", "language": "en"},
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.get_json(),
            {"error": "Missing dependency 'google.adk'."},
        )


if __name__ == "__main__":
    unittest.main()

"""Locust. Command: ``locust -f tests/load_test.py``.

Use ``USE_STATIC_EXAMPLE_VIDEO=1`` on the API so ElevenLabs is not used.
"""

import uuid

from locust import HttpUser, task


class GenerateVideoUser(HttpUser):
    host = "http://127.0.0.1:8000"

    def on_start(self) -> None:
        self.login = uuid.uuid4().hex

    @task
    def generate_video(self) -> None:
        with self.client.post(
            "/api/v1/generate/",
            json={"login": self.login, "text": "short script"},
            catch_response=True,
            timeout=120,
        ) as response:
            if response.status_code != 200:
                response.failure(f"status {response.status_code}")
                return
            ctype = response.headers.get("content-type", "")
            if "video/mp4" not in ctype:
                response.failure(f"bad content-type: {ctype!r}")
                return
            if not response.content:
                response.failure("empty body")
                return
            response.success()

"""A stand-in OpenAI-compatible model server (and job boards) for end-to-end tests.

Run with the backend as LLM_PROVIDER=local, LLM_BASE_URL=http://127.0.0.1:<port>/v1:
the real OpenAI SDK request, structured-output parsing and grounding all execute, but
the "model" answers with the scripted resume parse (tests.resume_fixtures) or, when
asked for a job analysis, the scripted analysis (tests.job_fixtures).

It also serves the fake Greenhouse/Lever boards of tests.job_fixtures under their real
API paths; point GREENHOUSE_API_BASE and LEVER_API_BASE at this server.

    python -m tests.fake_llm_server 8766
"""

from __future__ import annotations

import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.ai.resume.extraction_schema import from_parsed
from tests.job_fixtures import FakeBoards, job_analysis
from tests.resume_fixtures import parsed_resume

BOARDS = FakeBoards()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path.startswith(("/v1/boards/", "/v0/postings/")):
            status, body = BOARDS.respond(self.path.split("?")[0])
            self._send(status, body)
            return
        self._send(200, {"status": "ok"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        request = json.loads(self.rfile.read(length) or b"{}")
        if not self.path.endswith("/chat/completions"):
            self._send(404, {"error": {"message": "not found"}})
            return
        schema = (request.get("response_format") or {}).get("json_schema") or {}
        if schema.get("name") == "JobAnalysisExtraction":
            content = job_analysis().model_dump_json()
        else:
            content = from_parsed(parsed_resume()).model_dump_json()
        self._send(
            200,
            {
                "id": "chatcmpl-fake",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": request.get("model", "fake"),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content, "refusal": None},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    def _send(self, status: int, body: object) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args: object) -> None:  # keep test output quiet
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8766
    print(f"fake LLM listening on {port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()

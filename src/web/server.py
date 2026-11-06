"""
Standalone HTTP Web Server for Log Summarizer Dashboard.
Uses Python standard library (http.server) with no external dependencies required.
"""

from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any

from src.summarizer import LogSummarizer
from src.benchmark import BenchmarkRunner

STATIC_DIR = Path(__file__).parent / "static"
SAMPLE_LOGS_DIR = Path(__file__).parent.parent.parent / "data" / "sample_logs"


class LogSummarizerHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for Log Summarizer Web UI & API."""

    def _send_json(self, data: Dict[str, Any], status: int = 200) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        url_path = self.path.split("?")[0]

        if url_path == "/" or url_path == "/index.html":
            self._serve_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
        elif url_path.startswith("/static/"):
            rel_file = url_path.replace("/static/", "")
            target_path = STATIC_DIR / rel_file
            mime_type, _ = mimetypes.guess_type(target_path)
            self._serve_file(target_path, mime_type or "text/plain")
        elif url_path == "/api/presets":
            self._handle_get_presets()
        elif url_path == "/api/benchmark":
            runner = BenchmarkRunner(provider="offline")
            results = runner.run_all()
            self._send_json({"status": "success", "results": results})
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")

    def do_POST(self) -> None:
        url_path = self.path.split("?")[0]

        if url_path == "/api/summarize":
            content_len = int(self.headers.get("Content-Length", 0))
            if content_len == 0:
                self._send_json({"error": "Empty body"}, 400)
                return

            body = self.rfile.read(content_len).decode("utf-8")
            try:
                data = json.loads(body)
            except Exception as e:
                self._send_json({"error": f"Invalid JSON payload: {e}"}, 400)
                return

            log_text = data.get("log_text", "")
            provider = data.get("provider", "offline")
            api_key = data.get("api_key") or None
            model = data.get("model") or None

            try:
                summarizer = LogSummarizer(
                    provider=provider,
                    api_key=api_key,
                    model=model,
                )
                result = summarizer.analyze(log_text)
                self._send_json({"status": "success", "data": result.to_dict(), "markdown": result.to_markdown()})
            except Exception as ex:
                self._send_json({"status": "error", "message": str(ex)}, 500)
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def _handle_get_presets(self) -> None:
        presets = []
        if SAMPLE_LOGS_DIR.exists():
            for f in sorted(SAMPLE_LOGS_DIR.glob("*.log")):
                try:
                    with open(f, "r", encoding="utf-8", errors="replace") as fh:
                        content = fh.read()
                    presets.append({
                        "name": f.name.replace(".log", "").replace("_", " ").title(),
                        "filename": f.name,
                        "content": content,
                    })
                except Exception:
                    pass
        self._send_json({"status": "success", "presets": presets})

    def _serve_file(self, file_path: Path, content_type: str) -> None:
        if not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        try:
            with open(file_path, "rb") as f:
                data = f.read()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))


def start_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    server_address = (host, port)
    httpd = HTTPServer(server_address, LogSummarizerHandler)
    print(f"\n=======================================================")
    print(f" 🚀 Log Summarizer Web Dashboard running at:")
    print(f"    http://{host}:{port}/")
    print(f"=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()


if __name__ == "__main__":
    start_server()

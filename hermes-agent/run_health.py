#!/usr/bin/env python3
"""Healthcheck server + Hermes gateway launcher.

Starts a minimal HTTP server on port 9119 to respond to Railway healthchecks,
then launches the Hermes gateway as a subprocess.
"""
import json
import os
import signal
import subprocess
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler


HERMES_HOME = os.environ.get("HERMES_HOME", "/opt/data")
GATEWAY_CMD = [
    "/opt/hermes/.venv/bin/hermes",
    "gateway",
]


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/v1/models":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "object": "list",
                "data": [
                    {"id": "hermes-agent", "object": "model", "created": 0, "owned_by": "dezafira"}
                ]
            }).encode())
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # silent


def run_health_server():
    server = HTTPServer(("0.0.0.0", 9119), HealthHandler)
    server.serve_forever()


def main():
    print("[Dezafira] Iniciando healthcheck server na porta 9119...")

    # Start healthcheck server in a daemon thread
    t = threading.Thread(target=run_health_server, daemon=True)
    t.start()

    print("[Dezafira] Iniciando Hermes gateway...")
    sys.stdout.flush()

    # Start gateway
    proc = subprocess.Popen(GATEWAY_CMD)

    def sigterm_handler(signum, frame):
        print("[Dezafira] Recebido sinal, desligando...")
        proc.terminate()
        proc.wait(timeout=10)
        sys.exit(0)

    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGINT, sigterm_handler)

    proc.wait()
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()

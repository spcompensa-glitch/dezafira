#!/usr/bin/env python3
"""Healthcheck server + Hermes gateway launcher."""
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler


HERMES_HOME = os.environ.get("HERMES_HOME", "/opt/data")
GATEWAY_CMD = ["/opt/hermes/.venv/bin/hermes", "gateway"]


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/v1/models":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "object": "list",
                "data": [{"id": "hermes-agent", "object": "model", "created": 0, "owned_by": "dezafira"}]
            }).encode())
        elif self.path in ("/health", "/"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def run_server(port):
    try:
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        print(f"[Dezafira] Healthcheck em 0.0.0.0:{port}")
        sys.stdout.flush()
        server.serve_forever()
    except Exception as e:
        print(f"[Dezafira] ERRO porta {port}: {e}", file=sys.stderr)
        sys.stderr.flush()


def main():
    print("[Dezafira] Iniciando healthcheck server...")
    sys.stdout.flush()

    # Listen on PORT env (Railway default) AND 9119 (our default)
    ports_to_listen = set()
    ports_to_listen.add(9119)
    railway_port = os.environ.get("PORT")
    if railway_port:
        ports_to_listen.add(int(railway_port))

    print(f"[Dezafira] Portas: {sorted(ports_to_listen)}")
    sys.stdout.flush()

    for port in ports_to_listen:
        t = threading.Thread(target=run_server, args=(port,), daemon=True)
        t.start()

    time.sleep(1)

    print("[Dezafira] Iniciando Hermes gateway...")
    sys.stdout.flush()

    proc = subprocess.Popen(
        GATEWAY_CMD,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    def sigterm_handler(signum, frame):
        print("[Dezafira] Sinal recebido, desligando...")
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGINT, sigterm_handler)

    while True:
        if proc.poll() is not None:
            print(f"[Dezafira] Gateway encerrou (código {proc.returncode})")
            sys.stdout.flush()
            print("[Dezafira] Reiniciando gateway...")
            sys.stdout.flush()
            proc = subprocess.Popen(
                GATEWAY_CMD,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
        time.sleep(5)


if __name__ == "__main__":
    main()

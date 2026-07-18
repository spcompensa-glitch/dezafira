#!/usr/bin/env python3
"""Healthcheck server + Hermes gateway launcher with reverse proxy."""
import http.client
import json
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

HERMES_HOME = os.environ.get("HERMES_HOME", "/opt/data")
GATEWAY_CMD = ["/opt/hermes/.venv/bin/hermes", "gateway"]
GATEWAY_PORT = 9119


class ProxyHandler(BaseHTTPRequestHandler):
    def _health(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "object": "list",
            "data": [{"id": "hermes-agent", "object": "model", "created": 0, "owned_by": "dezafira"}]
        }).encode())

    def _ping(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')

    def _proxy(self, method):
        try:
            body = None
            content_length = self.headers.get("Content-Length")
            if content_length:
                body = self.rfile.read(int(content_length))

            conn = http.client.HTTPConnection("127.0.0.1", GATEWAY_PORT, timeout=120)
            conn.request(
                method,
                self.path,
                body=body,
                headers={k: v for k, v in self.headers.items()
                         if k.lower() not in ("host", "content-length")}
            )
            resp = conn.getresponse()
            data = resp.read()

            self.send_response(resp.status)
            for k, v in resp.getheaders():
                if k.lower() not in ("transfer-encoding", "content-encoding"):
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)
            conn.close()
        except Exception as e:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_GET(self):
        if self.path == "/v1/models":
            return self._health()
        if self.path in ("/health", "/"):
            return self._ping()
        return self._proxy("GET")

    def do_POST(self):
        if self.path == "/v1/chat/completions":
            return self._proxy("POST")
        if self.path == "/v1/completions":
            return self._proxy("POST")
        return self._proxy("POST")

    def do_PUT(self):
        return self._proxy("PUT")

    def do_DELETE(self):
        return self._proxy("DELETE")

    def log_message(self, format, *args):
        pass


def run_server(port):
    try:
        server = HTTPServer(("0.0.0.0", port), ProxyHandler)
        print(f"[Dezafira] Proxy server em 0.0.0.0:{port} -> 127.0.0.1:{GATEWAY_PORT}")
        sys.stdout.flush()
        server.serve_forever()
    except Exception as e:
        print(f"[Dezafira] ERRO porta {port}: {e}", file=sys.stderr)
        sys.stderr.flush()


def main():
    print("[Dezafira] Iniciando proxy + gateway...")
    sys.stdout.flush()

    ports_to_listen = set()
    ports_to_listen.add(GATEWAY_PORT)
    railway_port = os.environ.get("PORT")
    if railway_port:
        ports_to_listen.add(int(railway_port))

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

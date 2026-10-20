"""HTTP server for the docs Q&A API, run as a pod on the demo EKS cluster (see k8s/ask-docs.yaml).

The internal ALB forwards /kubernetes-docs/api/* straight to this server, which writes the answer as it
is generated, so it reaches the browser while Bedrock is still streaming it. (An ALB Lambda target
cannot stream, which is why this runs on EKS rather than Lambda.)

POST .../ask with "Accept: text/event-stream" gets server-sent events (meta, delta..., done | error);
any other POST gets the buffered JSON response. WARMUP=1 loads the search index before the server
starts listening, so the readiness probe only passes once the first question can be answered fast.
"""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import app

MAX_BODY_BYTES = 16 * 1024  # WAF already blocks bodies over 4KB at CloudFront
# Cost control that Lambda's reserved concurrency used to provide: each in-flight question is a Bedrock
# call, so refuse (429) beyond this many at once per pod. Replicas are fixed, so the total is bounded.
MAX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT", "5"))
_slots = threading.BoundedSemaphore(MAX_CONCURRENT)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # chunked responses, and the adapter reuses the connection

    def log_message(self, format, *args):  # app.py logs one structured line per question instead
        pass

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/healthz":  # readiness/liveness probes
            self._send_json(200, {"ok": True})
        else:
            self._send_json(405, {"error": "method not allowed"})

    def do_POST(self):
        if not self.path.split("?", 1)[0].rstrip("/").endswith("/ask"):
            return self._send_json(404, {"error": "not found"})
        try:
            length = int(self.headers.get("content-length") or 0)
        except ValueError:
            length = -1
        if not 0 <= length <= MAX_BODY_BYTES:
            self.close_connection = True  # the body was not read
            return self._send_json(413, {"error": "request body too large"})
        raw = self.rfile.read(length).decode("utf-8", "replace")
        try:
            request = app.parse_request(raw)
        except app.RequestError as exc:
            return self._send_json(exc.status, {"error": exc.message})

        if not _slots.acquire(blocking=False):
            return self._send_json(429, {"error": "too many requests in progress, try again shortly"})
        try:
            events = app.ask(request)
            if "text/event-stream" in (self.headers.get("accept") or ""):
                self._stream(events)
            else:
                self._send_json(*app.collect(events))
        finally:
            _slots.release()

    def _stream(self, events):
        self.send_response(200)
        self.send_header("content-type", "text/event-stream; charset=utf-8")
        self.send_header("cache-control", "no-store")
        self.send_header("transfer-encoding", "chunked")
        self.end_headers()
        try:
            # A comment line first: the stream opens at once, before retrieval (a few seconds) starts.
            self._chunk(b": ok\n\n")
            for name, data in events:
                self._chunk(f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode())
            self._chunk(b"")  # last chunk
        except (BrokenPipeError, ConnectionResetError):
            events.close()  # stop generating; ask() then does not store the turn
            self.close_connection = True

    def _chunk(self, data):
        self.wfile.write(b"%x\r\n%s\r\n" % (len(data), data))  # wfile is unbuffered

    def _send_json(self, status, body):
        payload = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("cache-control", "no-store")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    port = int(os.environ.get("AWS_LWA_PORT") or os.environ.get("PORT") or 8080)
    if os.environ.get("WARMUP") == "1":  # load the search index before the readiness probe passes
        app._get_index()
    ThreadingHTTPServer((os.environ.get("HOST", "127.0.0.1"), port), Handler).serve_forever()

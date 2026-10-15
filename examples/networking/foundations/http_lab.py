#!/usr/bin/env python3
"""A bounded, loopback-only HTTP/1.1 server for observing message structure."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socket
import threading
from urllib.parse import urlsplit

HELLO = b"hello\n"
MAX_BODY = 4096


class LessonHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "NetworkLesson/1"
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, *_):
        # Do not log request headers, bodies, or query strings.
        pass

    def reject(self, code, reason):
        self.close_connection = True
        self.send_error(code, reason)

    def body_length(self, required=False):
        hosts = self.headers.get_all("Host", [])
        if self.request_version == "HTTP/1.1" and (
                len(hosts) != 1 or not hosts[0].strip()):
            self.reject(400, "One Host field is required for HTTP/1.1")
            return None
        if self.headers.get_all("Transfer-Encoding"):
            self.reject(400, "This lesson accepts Content-Length framing only")
            return None
        fields = self.headers.get_all("Content-Length", [])
        if not fields:
            if required:
                self.reject(411, "Content-Length required for this lesson")
                return None
            return 0
        value = fields[0].strip()
        if len(fields) != 1 or not value.isascii() or not value.isdecimal():
            self.reject(400, "One decimal Content-Length is required")
            return None
        if len(value) > 8:
            self.reject(413, "Lesson Content-Length field is too large")
            return None
        length = int(value)
        if length > MAX_BODY:
            self.reject(413, "Lesson request body exceeds 4096 bytes")
            return None
        return length

    def respond(self, payload, content_type, head_only=False):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if not head_only:
            self.wfile.write(payload)

    def get_lesson(self, head_only=False):
        length = self.body_length()
        if length is None:
            return
        if length:
            self.reject(400, "Use POST /echo for a lesson request body")
            return
        if urlsplit(self.path).path != "/lesson":
            self.reject(404, "Only /lesson and POST /echo are available")
            return
        self.respond(HELLO, "text/plain; charset=utf-8", head_only)

    def do_GET(self):
        self.get_lesson()

    def do_HEAD(self):
        self.get_lesson(head_only=True)

    def do_POST(self):
        length = self.body_length(required=True)
        if length is None:
            return
        if urlsplit(self.path).path != "/echo":
            self.reject(404, "Only /lesson and POST /echo are available")
            return
        try:
            payload = self.rfile.read(length)
        except (socket.timeout, OSError):
            self.reject(408, "Timed out reading the lesson body")
            return
        if len(payload) != length:
            self.reject(400, "Request body ended before Content-Length")
            return
        self.respond(payload, "application/octet-stream")


def make_server(port=0):
    server = ThreadingHTTPServer(("127.0.0.1", port), LessonHandler)
    server.daemon_threads = True
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--duration", type=float, default=120,
                        help="Stop automatically after this many seconds (0.1–600)")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    if not 0.1 <= args.duration <= 600:
        parser.error("--duration must be between 0.1 and 600 seconds")
    with make_server(args.port) as server:
        stop = threading.Timer(args.duration, server.shutdown)
        stop.daemon = True
        stop.start()
        print(f"HTTP lesson: http://127.0.0.1:{server.server_port}/lesson", flush=True)
        print(f"GET/HEAD /lesson; POST /echo; automatic stop in {args.duration:g}s",
              flush=True)
        try:
            server.serve_forever(poll_interval=0.1)
        except KeyboardInterrupt:
            pass
        finally:
            stop.cancel()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Read-only live page for the workload identity demo (stdlib only).

Runs inside the demo namespace. A background thread polls the Kubernetes API
every 2 seconds (newest Running Pod of each orders copy: last log line and the
names of injected AWS_* variables) and keeps the result in memory. HTTP
requests are served from memory only, so viewers never trigger API calls:

  GET /            the page
  GET /api/state   JSON state (Cache-Control: max-age=1)
  GET /healthz     200

The ServiceAccount has no IAM role and its Role can only list Pods and read
their logs in this namespace. Because the page is reachable from the internet,
a NetworkPolicy (demo.sh) limits egress to DNS and TCP 443, so the Pod cannot
reach IMDS or the Pod Identity Agent and get the node role's credentials. Nothing secret is exposed: role names and
results come from app.sh output, which never prints credentials or tokens.
"""
import json
import os
import ssl
import threading
import time
import urllib.request
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SA = "/var/run/secrets/kubernetes.io/serviceaccount"
API = "https://kubernetes.default.svc"
TRACKS = ("legacy", "irsa", "podid")
OWN_VARS = {"AWS_REGION", "AWS_MAX_ATTEMPTS", "AWS_METADATA_SERVICE_TIMEOUT",
            "AWS_METADATA_SERVICE_NUM_ATTEMPTS"}
NAMESPACE = open(f"{SA}/namespace").read().strip()
CTX = ssl.create_default_context(cafile=f"{SA}/ca.crt")

state = {"updated": None, "namespace": NAMESPACE, "copies": {}, "error": None}
history = {t: deque(maxlen=60) for t in TRACKS}
lock = threading.Lock()


def api(path, raw=False):
    token = open(f"{SA}/token").read().strip()  # kubelet rotates it; re-read each time
    req = urllib.request.Request(API + path, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, context=CTX, timeout=5) as r:
        body = r.read().decode()
    return body if raw else json.loads(body)


def poll_once():
    pods = api(f"/api/v1/namespaces/{NAMESPACE}/pods?labelSelector=app%3Dorders")["items"]
    copies = {}
    for t in TRACKS:
        running = [p for p in pods if p["metadata"]["labels"].get("track") == t
                   and p["status"].get("phase") == "Running"
                   and not p["metadata"].get("deletionTimestamp")]
        running.sort(key=lambda p: p["metadata"]["creationTimestamp"])
        if not running:
            copies[t] = {"pod": None}
            continue
        pod = running[-1]
        name = pod["metadata"]["name"]
        line = api(f"/api/v1/namespaces/{NAMESPACE}/pods/{name}/log?tailLines=1", raw=True).strip()
        try:
            last = json.loads(line.splitlines()[-1]) if line else {}
        except (ValueError, IndexError):
            last = {}
        env = [e["name"] for e in pod["spec"]["containers"][0].get("env", [])
               if e["name"].startswith("AWS_") and e["name"] not in OWN_VARS]
        copies[t] = {"pod": name, "started": pod["metadata"]["creationTimestamp"],
                     "src": last.get("src"), "role": last.get("role"), "s3": last.get("s3"),
                     "at": last.get("t"), "env": env}
        if last.get("t") and (not history[t] or history[t][-1]["at"] != last["t"]):
            history[t].append({"at": last["t"], "s3": last.get("s3"), "src": last.get("src")})
    return copies


def poller():
    while True:
        try:
            copies = poll_once()
            with lock:
                state.update(copies=copies, error=None,
                             updated=time.strftime("%H:%M:%S", time.gmtime()))
                for t in TRACKS:
                    state["copies"][t]["history"] = list(history[t])
        except Exception as exc:  # keep serving the last good state
            with lock:
                state["error"] = type(exc).__name__
        time.sleep(2)


PAGE = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.html"), "rb").read()


class Handler(BaseHTTPRequestHandler):
    server_version = "wid-dashboard"
    sys_version = ""

    def _send(self, code, body, ctype, cache):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            self._send(200, PAGE, "text/html; charset=utf-8", "max-age=60")
        elif path == "/api/state":
            with lock:
                body = json.dumps(state).encode()
            self._send(200, body, "application/json", "max-age=1")
        elif path == "/healthz":
            self._send(200, b"ok", "text/plain", "no-store")
        else:
            self._send(404, b"not found", "text/plain", "max-age=60")

    do_HEAD = do_GET

    def log_message(self, *args):  # keep Pod logs quiet
        pass


if __name__ == "__main__":
    threading.Thread(target=poller, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()

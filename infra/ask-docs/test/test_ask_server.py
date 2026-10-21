"""Tests for the streaming docs Q&A server (lambda/ask). boto3 is replaced with fakes, so they run
without AWS access: python3 -m unittest discover -s infra/ask-docs/test"""
import gzip
import http.client
import json
import os
import sys
import threading
import types
import unittest
from http.server import ThreadingHTTPServer

LAMBDA_DIR = os.path.join(os.path.dirname(__file__), "..", "lambda", "ask")

CHUNKS = [
    {"locale": "ko", "url": "/kubernetes-docs/ko/autoscaling/karpenter#install", "title": "Karpenter", "heading": "설치", "text": "Karpenter는 노드를 자동으로 프로비저닝합니다."},
    {"locale": "ko", "url": "/kubernetes-docs/ko/autoscaling/hpa", "title": "HPA", "heading": "HPA", "text": "HPA는 파드 수를 조정합니다."},
]


class FakeBedrock:
    def __init__(self):
        self.deltas = ["Karpenter는 ", "노드를 ", "프로비저닝합니다 [1]."]
        self.fail_after = None  # raise after this many deltas

    def converse(self, system, **kwargs):  # follow-up rewrite, query expansion and rerank
        reply = "Karpenter 설치 방법\nkarpenter 설치" if "standalone" in system[0]["text"] else "1"
        return {"output": {"message": {"content": [{"text": reply}]}}}

    def converse_stream(self, **kwargs):
        def stream():
            yield {"messageStart": {"role": "assistant"}}
            for i, text in enumerate(self.deltas):
                if self.fail_after is not None and i == self.fail_after:
                    raise RuntimeError("modelStreamErrorException")
                yield {"contentBlockDelta": {"delta": {"text": text}, "contentBlockIndex": 0}}
            yield {"messageStop": {"stopReason": "end_turn"}}
            yield {"metadata": {"usage": {"inputTokens": 10, "outputTokens": 5}}}
        return {"stream": stream()}


class FakeS3:
    def head_object(self, **kwargs):
        return {"ETag": '"1"'}

    def get_object(self, **kwargs):
        raw = gzip.compress(json.dumps({"chunks": CHUNKS}).encode())
        return {"Body": types.SimpleNamespace(read=lambda: raw)}


class FakeDynamoDb:
    def __init__(self):
        self.items = {}

    def get_item(self, TableName, Key, **kwargs):
        item = self.items.get(Key["cid"]["S"])
        return {"Item": item} if item else {}

    def put_item(self, TableName, Item):
        self.items[Item["cid"]["S"]] = Item


FAKES = {"bedrock-runtime": FakeBedrock(), "s3": FakeS3(), "dynamodb": FakeDynamoDb()}


def load_modules():
    boto3 = types.ModuleType("boto3")
    boto3.client = lambda name, **kwargs: FAKES[name]
    botocore = types.ModuleType("botocore")
    botocore_config = types.ModuleType("botocore.config")
    botocore_config.Config = lambda **kwargs: None
    sys.modules.update({"boto3": boto3, "botocore": botocore, "botocore.config": botocore_config})
    os.environ.update({"INDEX_BUCKET": "bucket", "MODEL_ID": "model", "CONVERSATION_TABLE": "table"})
    sys.path.insert(0, LAMBDA_DIR)
    import app  # noqa: E402
    import server  # noqa: E402
    return app, server


app, server = load_modules()


def parse_sse(text):
    events = []
    for block in text.split("\n\n"):
        lines = [line for line in block.split("\n") if line and not line.startswith(":")]
        if not lines:
            continue
        name = next(line[6:].strip() for line in lines if line.startswith("event:"))
        data = "".join(line[5:].strip() for line in lines if line.startswith("data:"))
        events.append((name, json.loads(data)))
    return events


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def setUp(self):
        FAKES["bedrock-runtime"].fail_after = None
        FAKES["dynamodb"].items.clear()

    def post(self, body, accept=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.httpd.server_address[1], timeout=5)
        headers = {"content-type": "application/json"}
        if accept:
            headers["accept"] = accept
        conn.request("POST", "/api/ask", body=json.dumps(body).encode(), headers=headers)
        res = conn.getresponse()
        text = res.read().decode()
        conn.close()
        return res, text

    def test_streams_server_sent_events(self):
        res, text = self.post({"question": "Karpenter 설치", "locale": "ko"}, accept="text/event-stream")
        self.assertEqual(res.status, 200)
        self.assertEqual(res.getheader("content-type"), "text/event-stream; charset=utf-8")
        self.assertEqual(res.getheader("transfer-encoding"), "chunked")
        events = parse_sse(text)
        names = [name for name, _ in events]
        self.assertEqual(names, ["meta", "delta", "delta", "delta", "done"])
        meta = events[0][1]
        self.assertRegex(meta["conversationId"], r"^[0-9a-f]{32}$")
        self.assertEqual(meta["sources"][0]["url"], "/kubernetes-docs/ko/autoscaling/karpenter#install")
        self.assertEqual("".join(d["text"] for n, d in events if n == "delta"), "Karpenter는 노드를 프로비저닝합니다 [1].")
        # The finished turn is stored, without its [n] citations.
        turns = json.loads(FAKES["dynamodb"].items[meta["conversationId"]]["turns"]["S"])
        self.assertEqual(turns[1], {"role": "assistant", "content": "Karpenter는 노드를 프로비저닝합니다."})

    def test_follow_up_continues_the_conversation(self):
        _, text = self.post({"question": "Karpenter 설치", "locale": "ko"}, accept="text/event-stream")
        cid = parse_sse(text)[0][1]["conversationId"]
        _, text = self.post({"question": "그건 어떻게 해?", "locale": "ko", "conversationId": cid}, accept="text/event-stream")
        self.assertEqual(parse_sse(text)[0][1]["conversationId"], cid)
        self.assertEqual(len(json.loads(FAKES["dynamodb"].items[cid]["turns"]["S"])), 4)

    def test_buffered_json_without_event_stream_accept(self):
        res, text = self.post({"question": "Karpenter 설치", "locale": "ko"})
        self.assertEqual(res.status, 200)
        body = json.loads(text)
        self.assertEqual(body["answer"], "Karpenter는 노드를 프로비저닝합니다 [1].")
        self.assertEqual(len(body["sources"]), 1)
        self.assertRegex(body["conversationId"], r"^[0-9a-f]{32}$")

    def test_generation_error_mid_stream(self):
        FAKES["bedrock-runtime"].fail_after = 1
        _, text = self.post({"question": "Karpenter 설치", "locale": "ko"}, accept="text/event-stream")
        events = parse_sse(text)
        self.assertEqual([n for n, _ in events], ["meta", "delta", "error"])
        self.assertEqual(FAKES["dynamodb"].items, {})  # an unfinished answer is not stored
        res, text = self.post({"question": "Karpenter 설치", "locale": "ko"})
        self.assertEqual(res.status, 502)

    def test_rejects_invalid_requests(self):
        for body in ({"question": ""}, {"question": "x" * 501}, {"question": "q", "locale": "fr"}, ["q"]):
            res, _ = self.post(body, accept="text/event-stream")
            self.assertEqual(res.status, 400, body)

    def test_refuses_questions_beyond_the_concurrency_cap(self):
        held = 0
        while server._slots.acquire(blocking=False):  # take every free slot
            held += 1
        try:
            res, text = self.post({"question": "What is a Pod?"})
            self.assertEqual(res.status, 429)
            self.assertIn("too many requests", text)
        finally:
            for _ in range(held):
                server._slots.release()
        res, _ = self.post({"question": "What is a Pod?"})
        self.assertEqual(res.status, 200)

    def test_health_check(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.httpd.server_address[1], timeout=5)
        conn.request("GET", "/healthz")
        self.assertEqual(conn.getresponse().status, 200)
        conn.close()

    def test_closed_stream_does_not_store_the_turn(self):
        events = app.ask({"question": "Karpenter 설치", "locale": "ko", "conversationId": ""})
        self.assertEqual(next(events)[0], "meta")
        self.assertEqual(next(events)[0], "delta")
        events.close()  # what server.py does when the client disconnects
        self.assertEqual(FAKES["dynamodb"].items, {})


if __name__ == "__main__":
    unittest.main()

import datetime
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import ssl
import tempfile
import threading
import unittest
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

MODULE = Path(__file__).resolve().parents[1] / "inventory.py"
spec = importlib.util.spec_from_file_location("oncall_inventory", MODULE)
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


class Handler(BaseHTTPRequestHandler):
    mode = "normal"
    requests = []

    def log_message(self, *_):
        pass

    def do_GET(self):
        type(self).requests.append({"path": self.path, "authorization": self.headers.get("Authorization"),
                                    "stack": self.headers.get("X-Grafana-URL")})
        mode = type(self).mode
        if mode in ("unauthorized", "redirect"):
            self.send_response(401 if mode == "unauthorized" else 302)
            if mode == "redirect":
                self.send_header("Location", "https://untrusted.invalid/steal")
            self.end_headers()
            return
        second = urllib.parse.urlsplit(self.path).query == "page=2"
        page = {"count": 2, "results": [{"id": "second" if second else "first"}],
                "next": None if second else "?page=2"}
        if mode == "foreign":
            page["next"] = "https://untrusted.invalid/api/v1/teams/"
        elif mode == "other-collection":
            page["next"] = "/api/v1/users/?page=2"
        elif mode == "loop":
            page["next"] = "/api/v1/teams/"
        elif mode == "missing-next":
            del page["next"]
        elif mode == "bad-count":
            page["count"] = True
        elif mode == "changing-count" and second:
            page["count"] = 3
        elif mode == "truncated":
            page["next"] = None
        elif mode == "bad-results":
            page["results"] = "not-a-list"
        data = json.dumps(page).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class InventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="oncall-inventory-test-")
        cls.directory = Path(cls.temp.name)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "local-audit-only")])
        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
                .public_key(key.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(now - datetime.timedelta(minutes=1))
                .not_valid_after(now + datetime.timedelta(days=1))
                .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), False)
                .add_extension(x509.BasicConstraints(ca=True, path_length=None), True)
                .sign(key, hashes.SHA256()))
        cls.ca = cls.directory / "ca.pem"
        cls.ca.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        private = cls.directory / "key.pem"
        private.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                              serialization.PrivateFormat.TraditionalOpenSSL,
                                              serialization.NoEncryption()))
        private.chmod(0o600)
        server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_context.load_cert_chain(cls.ca, private)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.server.socket = server_context.wrap_socket(cls.server.socket, server_side=True)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "https://127.0.0.1:" + str(cls.server.server_port)
        context = ssl.create_default_context(cafile=str(cls.ca))
        cls.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                                 inventory.NoRedirect(),
                                                 urllib.request.HTTPSHandler(context=context))

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        cls.temp.cleanup()

    def setUp(self):
        Handler.mode = "normal"
        Handler.requests = []

    def export(self, **kwargs):
        return inventory.export_collection(self.opener, self.base, "synthetic-token", "teams", **kwargs)

    def test_real_tls_raw_auth_and_all_pages(self):
        data = self.export(stack_url="https://example.grafana.net")
        self.assertEqual([x["id"] for x in data], ["first", "second"])
        self.assertEqual(len(Handler.requests), 2)
        self.assertTrue(all(x["authorization"] == "synthetic-token" for x in Handler.requests))
        self.assertTrue(all(x["stack"] == "https://example.grafana.net" for x in Handler.requests))

    def test_untrusted_ca_is_rejected(self):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), inventory.NoRedirect(),
                                             urllib.request.HTTPSHandler(context=ssl.create_default_context()))
        with self.assertRaises(inventory.InventoryError):
            inventory.export_collection(opener, self.base, "synthetic-token", "teams")
        self.assertEqual(Handler.requests, [])

    def test_foreign_pagination_never_receives_token(self):
        Handler.mode = "foreign"
        with self.assertRaisesRegex(inventory.InventoryError, "origin or collection"):
            self.export()
        self.assertEqual(len(Handler.requests), 1)

    def test_cross_collection_pagination_rejected(self):
        Handler.mode = "other-collection"
        with self.assertRaises(inventory.InventoryError):
            self.export()
        self.assertEqual(len(Handler.requests), 1)

    def test_redirect_not_followed(self):
        Handler.mode = "redirect"
        with self.assertRaisesRegex(inventory.InventoryError, "HTTP302"):
            self.export()
        self.assertEqual(len(Handler.requests), 1)

    def test_unauthorized_is_not_retried(self):
        Handler.mode = "unauthorized"
        with self.assertRaisesRegex(inventory.InventoryError, "HTTP401"):
            self.export()
        self.assertEqual(len(Handler.requests), 1)

    def test_pagination_loop_is_rejected(self):
        Handler.mode = "loop"
        with self.assertRaisesRegex(inventory.InventoryError, "loop"):
            self.export()
        self.assertEqual(len(Handler.requests), 1)

    def test_page_bound_is_enforced(self):
        with self.assertRaisesRegex(inventory.InventoryError, "page bound"):
            self.export(max_pages=1)

    def test_missing_or_invalid_response_fields_fail(self):
        for mode in ["missing-next", "bad-count", "bad-results", "truncated", "changing-count"]:
            with self.subTest(mode=mode):
                Handler.mode = mode
                with self.assertRaises(inventory.InventoryError):
                    self.export()

    def test_invalid_base_and_token_fail_before_request(self):
        for base, token in [("http://127.0.0.1", "token"), (self.base + "/api", "token"),
                            (self.base, "bad\ntoken"), (self.base, "")]:
            with self.subTest(base=base), self.assertRaises(inventory.InventoryError):
                inventory.export_collection(self.opener, base, token, "teams")
        self.assertEqual(Handler.requests, [])

    def test_write_is_private_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "inventory.json"
            inventory.write_private_json(destination, {"synthetic": True})
            self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(destination.read_text()), {"synthetic": True})
            with self.assertRaises(inventory.InventoryError):
                inventory.write_private_json(destination, {"different": True})
            self.assertEqual(json.loads(destination.read_text()), {"synthetic": True})
            self.assertEqual([x.name for x in Path(directory).iterdir()], ["inventory.json"])

    def test_collection_allowlist(self):
        with self.assertRaises(inventory.InventoryError):
            inventory.export_collection(self.opener, self.base, "synthetic-token", "make_call")
        self.assertEqual(Handler.requests, [])


if __name__ == "__main__":
    unittest.main()

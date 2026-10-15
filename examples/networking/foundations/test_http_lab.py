import http.client
from pathlib import Path
import subprocess
import sys
import threading
import unittest

from http_lab import HELLO, MAX_BODY, make_server


class HttpLessonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server()
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def setUp(self):
        self.client = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=2)
        self.addCleanup(self.client.close)

    def test_loopback_binding_and_message_length(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        self.client.request("GET", "/lesson")
        response = self.client.getresponse()
        self.assertEqual(response.version, 11)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader("Content-Length"), "6")
        self.assertEqual(response.getheader("Content-Type"), "text/plain; charset=utf-8")
        self.assertEqual(response.read(), HELLO)

    def test_head_does_not_consume_the_next_response(self):
        self.client.request("HEAD", "/lesson")
        response = self.client.getresponse()
        self.assertEqual(response.getheader("Content-Length"), "6")
        self.assertEqual(response.read(), b"")
        connection = self.client.sock
        self.client.request("GET", "/lesson")
        self.assertIs(self.client.sock, connection)
        self.assertEqual(self.client.getresponse().read(), HELLO)

    def test_post_counts_bytes_and_preserves_persistent_connection(self):
        self.client.request("GET", "/lesson")
        self.assertEqual(self.client.getresponse().read(), HELLO)
        connection = self.client.sock
        payload = "네트워크".encode("utf-8")
        self.client.request("POST", "/echo", body=payload)
        response = self.client.getresponse()
        self.assertIs(self.client.sock, connection)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader("Content-Length"), str(len(payload)))
        self.assertEqual(response.read(), payload)

    def test_oversized_body_is_rejected_before_reading(self):
        self.client.putrequest("POST", "/echo")
        self.client.putheader("Content-Length", str(MAX_BODY + 1))
        self.client.endheaders()
        response = self.client.getresponse()
        self.assertEqual(response.status, 413)
        self.assertEqual(response.getheader("Connection"), "close")
        response.read()

    def test_duplicate_lengths_are_not_accepted_as_two_messages(self):
        self.client.putrequest("POST", "/echo")
        self.client.putheader("Content-Length", "0")
        self.client.putheader("Content-Length", "3")
        self.client.endheaders()
        response = self.client.getresponse()
        self.assertEqual(response.status, 400)
        self.assertEqual(response.getheader("Connection"), "close")
        response.read()

    def test_transfer_encoding_is_outside_the_lesson_contract(self):
        self.client.putrequest("POST", "/echo")
        self.client.putheader("Transfer-Encoding", "chunked")
        self.client.endheaders()
        response = self.client.getresponse()
        self.assertEqual(response.status, 400)
        response.read()

    def test_http11_requires_one_host_field(self):
        self.client.putrequest("GET", "/lesson", skip_host=True)
        self.client.endheaders()
        response = self.client.getresponse()
        self.assertEqual(response.status, 400)
        response.read()

    def test_long_decimal_length_is_rejected_without_integer_conversion(self):
        self.client.putrequest("POST", "/echo")
        self.client.putheader("Content-Length", "9" * 1000)
        self.client.endheaders()
        response = self.client.getresponse()
        self.assertEqual(response.status, 413)
        response.read()

    def test_missing_length_and_unknown_path_are_explicit(self):
        self.client.putrequest("POST", "/echo")
        self.client.endheaders()
        response = self.client.getresponse()
        self.assertEqual(response.status, 411)
        response.read()
        self.client.close()
        self.client.request("GET", "/../../etc/passwd")
        response = self.client.getresponse()
        self.assertEqual(response.status, 404)
        self.assertNotIn(b"root:", response.read())

    def test_command_stops_without_leaving_a_server(self):
        script = Path(__file__).with_name("http_lab.py")
        result = subprocess.run(
            [sys.executable, str(script), "--port", "0", "--duration", "0.2"],
            capture_output=True, text=True, timeout=3)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("http://127.0.0.1:", result.stdout)


if __name__ == "__main__":
    unittest.main()

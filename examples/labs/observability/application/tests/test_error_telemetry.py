"""Exercise failure paths with input that must not enter logs or traces."""

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from api import create_app
from storage import Store
from telemetry import Telemetry


class ErrorTelemetryTest(unittest.TestCase):
    def test_database_and_unexpected_errors_exclude_inputs(self):
        sentinel = "SYNTHETIC_PRIVATE_CUSTOMER_272"
        for failure in ("missing_table", "unexpected"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                store = Store("sqlite:///" + str(Path(directory) / "empty.db"))
                exporter = InMemorySpanExporter()
                output = io.StringIO()
                telemetry = Telemetry(
                    "order-service", "error-test",
                    exporter=exporter, log_stream=output,
                )
                client = TestClient(
                    create_app("order-service", store, telemetry),
                    raise_server_exceptions=False,
                )
                try:
                    payload = {
                        "customer_id": sentinel, "product_id": "private-product",
                        "quantity": 1,
                    }
                    if failure == "unexpected":
                        with patch.object(store, "create_order", side_effect=RuntimeError(sentinel)):
                            response = client.post("/orders", json=payload)
                    else:
                        response = client.post("/orders", json=payload)
                    self.assertEqual(response.status_code, 500)
                    spans = exporter.get_finished_spans()
                    self.assertEqual(len(spans), 2)
                    self.assertTrue(all(s.status.status_code == StatusCode.ERROR for s in spans))
                    exported = json.dumps([json.loads(s.to_json()) for s in spans])
                    self.assertNotIn(sentinel, exported)
                    self.assertNotIn("private-product", exported)
                    self.assertNotIn("exception.stacktrace", exported)
                    self.assertNotIn(sentinel, output.getvalue())
                    self.assertNotIn(sentinel, response.text)
                    self.assertIn('status="500"', telemetry.metrics().decode())
                finally:
                    client.close()
                    telemetry.close()
                    store.close()


if __name__ == "__main__":
    unittest.main()

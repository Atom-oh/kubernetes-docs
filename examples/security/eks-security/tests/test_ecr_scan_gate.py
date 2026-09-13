import copy
import datetime
import importlib.util
from pathlib import Path
import unittest

import boto3
from botocore.stub import Stubber

MODULE = Path(__file__).resolve().parents[1] / "ecr_scan_gate.py"
spec = importlib.util.spec_from_file_location("ecr_scan_gate", MODULE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
REGISTRY = "123456789012"
REPOSITORY = "audit-example"
DIGEST = "sha256:" + "a" * 64
PARAMETERS = {"registryId": REGISTRY, "repositoryName": REPOSITORY,
              "imageId": {"imageDigest": DIGEST}, "maxResults": 1}


def response(status="ACTIVE"):
    return {
        "registryId": REGISTRY, "repositoryName": REPOSITORY,
        "imageId": {"imageDigest": DIGEST}, "imageScanStatus": {"status": status},
        "imageScanFindings": {
            "imageScanCompletedAt": datetime.datetime(2026, 9, 13, tzinfo=datetime.timezone.utc),
            "findingSeverityCounts": {},
        },
    }


class FakeTime:
    def __init__(self):
        self.now = 0

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class ScanGateTests(unittest.TestCase):
    def check(self, value, **kwargs):
        return gate.inspect_response(value, REGISTRY, REPOSITORY, DIGEST, **kwargs)

    def test_completed_empty_map_is_zero(self):
        for status in ["ACTIVE", "COMPLETE"]:
            with self.subTest(status=status):
                self.assertEqual(self.check(response(status))["critical"], 0)

    def test_active_without_completion_cannot_pass(self):
        value = response()
        del value["imageScanFindings"]["imageScanCompletedAt"]
        self.assertIsNone(self.check(value))

    def test_missing_findings_or_counts_cannot_pass(self):
        for value in [dict(response(), imageScanFindings=None),
                      dict(response(), imageScanFindings={})]:
            self.assertIsNone(self.check(value))

    def test_critical_and_high_findings_fail(self):
        for counts in [{"CRITICAL": 1}, {"HIGH": 1}, {"UNDEFINED": 1}]:
            value = response()
            value["imageScanFindings"]["findingSeverityCounts"] = counts
            with self.assertRaises(gate.ScanGateError):
                self.check(value)

    def test_explicit_high_threshold_is_recorded(self):
        value = response()
        value["imageScanFindings"]["findingSeverityCounts"] = {"HIGH": 2}
        self.assertEqual(self.check(value, max_high=2)["maxHigh"], 2)
        with self.assertRaises(gate.ScanGateError):
            self.check(value, max_high=1)

    def test_invalid_counts_fail(self):
        for counts in [{"HIGH": -1}, {"HIGH": "0"}, {"HIGH": True}, {"UNKNOWN": 1}, []]:
            value = response()
            value["imageScanFindings"]["findingSeverityCounts"] = counts
            with self.assertRaises(gate.ScanGateError):
                self.check(value)

    def test_mismatched_artifact_fails(self):
        for field, value in [("registryId", "999999999999"), ("repositoryName", "other"),
                             ("imageId", {"imageDigest": "sha256:" + "b" * 64})]:
            changed = response()
            changed[field] = value
            with self.assertRaises(gate.ScanGateError):
                self.check(changed)

    def test_unavailable_or_unknown_status_fails(self):
        for status in ["FAILED", "UNSUPPORTED_IMAGE", "SCAN_ELIGIBILITY_EXPIRED",
                       "FINDINGS_UNAVAILABLE", "LIMIT_EXCEEDED", None, "NEW_UNKNOWN"]:
            with self.subTest(status=status), self.assertRaises(gate.ScanGateError):
                self.check(response(status))

    def test_pending_waits(self):
        for status in ["IN_PROGRESS", "PENDING"]:
            self.assertIsNone(self.check(response(status)))

    def client(self):
        return boto3.client("ecr", region_name="ap-northeast-2",
                            aws_access_key_id="synthetic-testing",
                            aws_secret_access_key="synthetic-testing")

    def test_native_sdk_waits_for_initial_completion(self):
        client = self.client()
        timer = FakeTime()
        incomplete = response()
        del incomplete["imageScanFindings"]["imageScanCompletedAt"]
        with Stubber(client) as stub:
            stub.add_client_error("describe_image_scan_findings", service_error_code="ScanNotFoundException",
                                  expected_params=PARAMETERS)
            stub.add_response("describe_image_scan_findings", incomplete, PARAMETERS)
            stub.add_response("describe_image_scan_findings", response(), PARAMETERS)
            actual = gate.wait_for_scan(client, REGISTRY, REPOSITORY, DIGEST,
                                        timeout=30, interval=10, clock=timer.clock, sleep=timer.sleep)
            self.assertEqual(actual["digest"], DIGEST)
            self.assertEqual(timer.now, 20)
            stub.assert_no_pending_responses()

    def test_native_sdk_timeout_never_returns_zero(self):
        client = self.client()
        timer = FakeTime()
        with Stubber(client) as stub:
            for _ in range(3):
                stub.add_response("describe_image_scan_findings", response("PENDING"), PARAMETERS)
            with self.assertRaisesRegex(gate.ScanGateError, "Timed out"):
                gate.wait_for_scan(client, REGISTRY, REPOSITORY, DIGEST,
                                   timeout=20, interval=10, clock=timer.clock, sleep=timer.sleep)
            stub.assert_no_pending_responses()

    def test_native_sdk_access_denied_fails_without_retry(self):
        client = self.client()
        timer = FakeTime()
        with Stubber(client) as stub:
            stub.add_client_error("describe_image_scan_findings", service_error_code="AccessDeniedException",
                                  expected_params=PARAMETERS)
            with self.assertRaisesRegex(gate.ScanGateError, "AccessDeniedException"):
                gate.wait_for_scan(client, REGISTRY, REPOSITORY, DIGEST,
                                   clock=timer.clock, sleep=timer.sleep)
            self.assertEqual(timer.now, 0)
            stub.assert_no_pending_responses()


if __name__ == "__main__":
    unittest.main()

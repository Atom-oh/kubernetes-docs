#!/usr/bin/env python3
"""Check a specific ECR image scan without treating missing results as success."""
import argparse
import datetime
import json
import re
import time

import boto3
from botocore.exceptions import ClientError


class ScanGateError(RuntimeError):
    pass


def inspect_response(response, registry_id, repository, digest, *, max_high=0):
    if response.get("registryId") != registry_id or response.get("repositoryName") != repository:
        raise ScanGateError("Scan response does not match the requested registry/repository")
    if response.get("imageId", {}).get("imageDigest") != digest:
        raise ScanGateError("Scan response does not match the requested image digest")
    status = response.get("imageScanStatus", {}).get("status")
    if status in {"IN_PROGRESS", "PENDING"}:
        return None
    if status not in {"COMPLETE", "ACTIVE"}:
        raise ScanGateError(f"Scan is unavailable or unsuccessful: {status!r}")
    findings = response.get("imageScanFindings")
    if not isinstance(findings, dict):
        return None
    completed = findings.get("imageScanCompletedAt")
    counts = findings.get("findingSeverityCounts")
    # ACTIVE denotes continuous scanning; it does not alone prove that the
    # initial scan produced a complete result.
    if completed is None or counts is None:
        return None
    if not isinstance(completed, datetime.datetime):
        raise ScanGateError("SDK scan completion timestamp is invalid")
    if completed.tzinfo is None:
        completed = completed.replace(tzinfo=datetime.timezone.utc)
    if completed.timestamp() <= 0:
        raise ScanGateError("Scan completion timestamp is invalid")
    if not isinstance(counts, dict):
        raise ScanGateError("Severity counts must be an explicit map")
    allowed = {"INFORMATIONAL", "LOW", "MEDIUM", "HIGH", "CRITICAL", "UNDEFINED"}
    for severity, count in counts.items():
        if severity not in allowed or type(count) is not int or count < 0:
            raise ScanGateError("Severity count is invalid or unknown")
    if counts.get("UNDEFINED", 0):
        raise ScanGateError("Undefined-severity findings require review")
    critical, high = counts.get("CRITICAL", 0), counts.get("HIGH", 0)
    if critical or high > max_high:
        raise ScanGateError(f"Vulnerability policy failed: CRITICAL={critical}, HIGH={high}")
    return {"digest": digest, "status": status, "scanCompletedAt": completed.isoformat(),
            "critical": critical, "high": high, "maxHigh": max_high}


def wait_for_scan(client, registry_id, repository, digest, *, timeout=600, interval=10,
                  max_high=0, clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + timeout
    while True:
        try:
            response = client.describe_image_scan_findings(
                registryId=registry_id, repositoryName=repository,
                imageId={"imageDigest": digest}, maxResults=1,
            )
            result = inspect_response(response, registry_id, repository, digest, max_high=max_high)
            if result is not None:
                return result
        except ClientError as error:
            error_code = error.response["Error"]["Code"]
            if error_code != "ScanNotFoundException":
                raise ScanGateError(f"ECR scan request failed ({error_code})") from error
        remaining = deadline - clock()
        if remaining <= 0:
            raise ScanGateError("Timed out waiting for a completed scan with explicit severity counts")
        sleep(min(interval, remaining))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True)
    parser.add_argument("--registry-id", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--digest", required=True)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--max-high", type=int, default=0)
    args = parser.parse_args()
    if not re.fullmatch(r"\d{12}", args.registry_id):
        parser.error("--registry-id must be a 12-digit account ID")
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", args.digest):
        parser.error("--digest must be an immutable SHA-256 digest")
    if not 1 <= args.timeout <= 3600 or not 1 <= args.interval <= 60 or args.max_high < 0:
        parser.error("Invalid timeout, interval or vulnerability threshold")
    client = boto3.client("ecr", region_name=args.region)
    try:
        result = wait_for_scan(client, args.registry_id, args.repository, args.digest,
                               timeout=args.timeout, interval=args.interval, max_high=args.max_high)
    except ScanGateError as error:
        parser.exit(1, f"Scan gate failed: {error}\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()

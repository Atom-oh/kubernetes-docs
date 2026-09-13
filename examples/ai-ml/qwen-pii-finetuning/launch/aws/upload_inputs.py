"""Validate the five experiment inputs; upload only with --execute."""

import argparse
import base64
import hashlib
import json
import re
from pathlib import Path


def build_upload_plan(data: Path, source: Path, experiment_id: str) -> list[dict]:
    if not re.fullmatch(r"qwen-pii-[A-Za-z0-9-]+", experiment_id):
        raise ValueError("Invalid experiment ID")
    manifest_path = data / "dataset-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = [
        (data / f"{split}.jsonl", f"dataset/{split}.jsonl", manifest["sha256"][split])
        for split in ("train", "validation", "test")
    ] + [(manifest_path, "dataset/dataset-manifest.json", None),
         (source, "source/source.tar.gz", None)]
    plan = []
    for path, key, expected in files:
        if not path.is_file() or path.is_symlink():
            raise ValueError("Inputs must be regular files")
        if path.stat().st_size > 64 * 1024 * 1024:
            raise ValueError("This small synthetic example limits each input to 64 MiB")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if expected and digest != expected:
            raise ValueError(f"Dataset hash mismatch: {path.name}")
        plan.append({
            "path": path,
            "key": f"qwen-pii/{experiment_id}/{key}",
            "sha256": digest,
        })
    return plan


def upload_and_verify(client, inventory: dict, plan: list[dict]) -> list[dict]:
    bucket = inventory["bucket_name"]
    owner = inventory["account_id"]
    if (
        inventory.get("schema_version") != 2
        or not inventory.get("ownership_token")
        or not inventory.get("resources", {}).get("bucket", {}).get("created")
    ):
        raise ValueError("Confirmed bucket ownership inventory is required")
    if not re.fullmatch(r"[0-9]{12}", owner):
        raise ValueError("A verified inventory account_id is required")
    response = client.get_bucket_tagging(Bucket=bucket, ExpectedBucketOwner=owner)
    tags = {tag["Key"]: tag["Value"] for tag in response["TagSet"]}
    expected_tags = {
        "ExperimentId": inventory["experiment_id"],
        "OwnershipToken": inventory["ownership_token"],
        "Experiment": "qwen-pii-finetuning",
    }
    if any(tags.get(key) != value for key, value in expected_tags.items()):
        raise ValueError("Bucket ownership tag does not match this experiment")
    verified = []
    for item in plan:
        # Recheck after planning, before any transfer of this file.
        body = item["path"].read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        if digest != item["sha256"]:
            raise ValueError("Input changed after upload planning")
        client.put_object(
            Bucket=bucket, Key=item["key"], Body=body,
            ExpectedBucketOwner=owner, ServerSideEncryption="AES256",
            ChecksumSHA256=base64.b64encode(bytes.fromhex(digest)).decode("ascii"),
        )
        remote = client.get_object(
            Bucket=bucket, Key=item["key"], ExpectedBucketOwner=owner
        )["Body"]
        remote_hash = hashlib.sha256()
        try:
            for chunk in iter(lambda: remote.read(1024 * 1024), b""):
                remote_hash.update(chunk)
        finally:
            remote.close()
        if remote_hash.hexdigest() != digest:
            raise ValueError("Remote object hash mismatch")
        verified.append({"key": item["key"], "sha256": digest})
    return verified


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--source", type=Path, default=Path("generated/source.tar.gz"))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    plan = build_upload_plan(args.data, args.source, inventory["experiment_id"])
    if not args.execute:
        print("Validated five local inputs; no AWS request made. Use --execute to upload.")
        return
    import boto3
    from botocore.config import Config

    client = boto3.Session(region_name=inventory["region"]).client(
        "s3", config=Config(
            retries={"total_max_attempts": 5, "mode": "adaptive"},
            connect_timeout=10, read_timeout=60,
        )
    )
    verified = upload_and_verify(client, inventory, plan)
    report = args.inventory.parent / "uploaded-inputs.json"
    report.write_text(
        json.dumps({"verified": verified}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report.chmod(0o600)
    print("Five inputs uploaded and verified by SHA-256 readback.")


if __name__ == "__main__":
    main()

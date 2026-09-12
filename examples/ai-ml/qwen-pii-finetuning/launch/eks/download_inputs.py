"""Download the five verified inputs using the Pod's AWS workload identity."""

import argparse
import hashlib
import json
import re
from pathlib import Path


FILES = {
    "source/source.tar.gz": "source.tar.gz",
    "dataset/train.jsonl": "data/train.jsonl",
    "dataset/validation.jsonl": "data/validation.jsonl",
    "dataset/test.jsonl": "data/test.jsonl",
    "dataset/dataset-manifest.json": "data/dataset-manifest.json",
}
MAX_FILE_BYTES = 64 * 1024 * 1024


def download_inputs(
    client, *, bucket: str, prefix: str, account_id: str,
    manifest: dict, output_dir: Path,
) -> None:
    if not re.fullmatch(r"\d{12}", account_id):
        raise ValueError("Invalid expected bucket account")
    if not re.fullmatch(r"qwen-pii/qwen-pii-[A-Za-z0-9-]+", prefix):
        raise ValueError("Invalid experiment prefix")
    entries = manifest.get("verified", [])
    expected = {f"{prefix}/{relative}": target for relative, target in FILES.items()}
    if (
        len(entries) != len(expected)
        or {entry["key"] for entry in entries} != set(expected)
        or not all(re.fullmatch(r"[a-f0-9]{64}", entry["sha256"]) for entry in entries)
    ):
        raise ValueError("Input manifest does not match this experiment's five inputs")
    for entry in entries:
        output = Path(output_dir) / expected[entry["key"]]
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(output.name + ".part")
        body = client.get_object(
            Bucket=bucket, Key=entry["key"], ExpectedBucketOwner=account_id
        )["Body"]
        digest, total = hashlib.sha256(), 0
        temporary_created = False
        try:
            with temporary.open("xb") as stream:
                temporary_created = True
                for chunk in iter(lambda: body.read(1024 * 1024), b""):
                    total += len(chunk)
                    if total > MAX_FILE_BYTES:
                        raise ValueError("Input exceeds the 64 MiB example limit")
                    digest.update(chunk)
                    stream.write(chunk)
            if digest.hexdigest() != entry["sha256"]:
                raise ValueError("Input hash differs from the verified upload")
            temporary.replace(output)
        finally:
            body.close()
            if temporary_created:
                temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--region", default="ap-northeast-2")
    args = parser.parse_args()
    import boto3
    from botocore.config import Config

    # Web-identity/container credentials come from the standard SDK chain.
    # No static keys or presigned bearer URLs are accepted by this helper.
    client = boto3.Session(region_name=args.region).client(
        "s3", config=Config(
            retries={"total_max_attempts": 4, "mode": "adaptive"},
            connect_timeout=10, read_timeout=60,
        )
    )
    download_inputs(
        client, bucket=args.bucket, prefix=args.prefix, account_id=args.account_id,
        manifest=json.loads(args.manifest.read_text(encoding="utf-8")),
        output_dir=args.output_dir,
    )
    print("Verified five experiment inputs.")


if __name__ == "__main__":
    main()

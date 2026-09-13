import hashlib
import io
import json
from unittest.mock import Mock

import pytest

from launch.aws.upload_inputs import build_upload_plan, upload_and_verify


def inventory():
    return {
        "bucket_name": "test-bucket", "account_id": "123456789012",
        "experiment_id": "qwen-pii-unit-test", "schema_version": 2,
        "ownership_token": "owned-fixture",
        "resources": {"bucket": {"created": True}},
    }


def dataset(tmp_path):
    manifest = {"sha256": {}}
    for split in ("train", "validation", "test"):
        value = f'{{"id":"{split}"}}\n'.encode()
        (tmp_path / f"{split}.jsonl").write_bytes(value)
        manifest["sha256"][split] = hashlib.sha256(value).hexdigest()
    (tmp_path / "dataset-manifest.json").write_text(json.dumps(manifest))
    (tmp_path / "source.tar.gz").write_bytes(b"source")
    return tmp_path


def test_only_declared_inputs_are_uploaded(tmp_path):
    root = dataset(tmp_path)
    (root / "private.txt").write_text("do not upload")
    plan = build_upload_plan(root, root / "source.tar.gz", "qwen-pii-unit-test")
    assert len(plan) == 5
    assert {item["path"].name for item in plan} == {
        "train.jsonl", "validation.jsonl", "test.jsonl",
        "dataset-manifest.json", "source.tar.gz",
    }


def test_invalid_split_digest_blocks_upload(tmp_path):
    root = dataset(tmp_path)
    (root / "train.jsonl").write_text("modified")
    with pytest.raises(ValueError, match="train"):
        build_upload_plan(root, root / "source.tar.gz", "qwen-pii-unit-test")


def test_remote_readback_must_match(tmp_path):
    root = dataset(tmp_path)
    plan = build_upload_plan(root, root / "source.tar.gz", "qwen-pii-unit-test")
    client = Mock()
    client.get_bucket_tagging.return_value = {
        "TagSet": [
            {"Key": "ExperimentId", "Value": "qwen-pii-unit-test"},
            {"Key": "OwnershipToken", "Value": "owned-fixture"},
            {"Key": "Experiment", "Value": "qwen-pii-finetuning"},
        ]
    }
    client.get_object.return_value = {"Body": io.BytesIO(b"different")}
    with pytest.raises(ValueError, match="Remote"):
        upload_and_verify(client, inventory(), plan)
    assert client.get_object.call_args.kwargs["ExpectedBucketOwner"] == "123456789012"


def test_bucket_owner_tag_mismatch_blocks_all_writes(tmp_path):
    root = dataset(tmp_path)
    plan = build_upload_plan(root, root / "source.tar.gz", "qwen-pii-unit-test")
    client = Mock()
    client.get_bucket_tagging.return_value = {"TagSet": []}
    with pytest.raises(ValueError, match="ownership"):
        upload_and_verify(
            client,
            inventory(),
            plan,
        )
    client.put_object.assert_not_called()

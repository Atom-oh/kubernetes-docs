import hashlib
import io
from unittest.mock import Mock

import pytest

from launch.eks.download_inputs import download_inputs


PREFIX = "qwen-pii/qwen-pii-fixture"
RELATIVE = (
    "source/source.tar.gz", "dataset/train.jsonl", "dataset/validation.jsonl",
    "dataset/test.jsonl", "dataset/dataset-manifest.json",
)


def fixture():
    bodies = {f"{PREFIX}/{key}": key.encode() for key in RELATIVE}
    manifest = {"verified": [
        {"key": key, "sha256": hashlib.sha256(body).hexdigest()}
        for key, body in bodies.items()
    ]}
    client = Mock()
    client.get_object.side_effect = lambda **kw: {"Body": io.BytesIO(bodies[kw["Key"]])}
    return client, manifest


def test_inputs_use_workload_identity_and_verified_owner_hashes(tmp_path):
    client, manifest = fixture()
    download_inputs(
        client, bucket="fixture-bucket", prefix=PREFIX, account_id="123456789012",
        manifest=manifest, output_dir=tmp_path,
    )
    assert (tmp_path / "source.tar.gz").read_bytes() == b"source/source.tar.gz"
    assert (tmp_path / "data/train.jsonl").read_bytes() == b"dataset/train.jsonl"
    assert client.get_object.call_count == 5
    for call in client.get_object.call_args_list:
        assert call.kwargs["ExpectedBucketOwner"] == "123456789012"


def test_another_experiments_manifest_is_rejected_before_aws(tmp_path):
    client, manifest = fixture()
    manifest["verified"][0]["key"] = "qwen-pii/other/source/source.tar.gz"
    with pytest.raises(ValueError):
        download_inputs(
            client, bucket="fixture", prefix=PREFIX, account_id="123456789012",
            manifest=manifest, output_dir=tmp_path,
        )
    client.get_object.assert_not_called()


def test_tampered_object_never_becomes_a_training_input(tmp_path):
    client, manifest = fixture()
    client.get_object.side_effect = lambda **kw: {"Body": io.BytesIO(b"tampered")}
    with pytest.raises(ValueError, match="hash"):
        download_inputs(
            client, bucket="fixture", prefix=PREFIX, account_id="123456789012",
            manifest=manifest, output_dir=tmp_path,
        )
    assert not (tmp_path / "source.tar.gz").exists()
    assert not list(tmp_path.rglob("*.part"))

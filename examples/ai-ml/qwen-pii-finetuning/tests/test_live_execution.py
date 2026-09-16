"""Budget and identity failures must stop real cloud submission."""

from datetime import date
from decimal import Decimal
import copy
import json
import hashlib
import io
from pathlib import Path
from types import SimpleNamespace

import pytest

from launch import live_execution as live


def config():
    return json.loads(
        (Path(__file__).parents[1] / "config/execution-20260916.json").read_text()
    )


def test_cost_reserves_launch_overhead_and_incidentals():
    assert live.reservation_usd(config(), 3600) == Decimal("18.8508125000")


@pytest.mark.parametrize("seconds", [0, -1, True, 1.5, 500_000])
def test_invalid_runtime_is_rejected(seconds):
    with pytest.raises(ValueError):
        live.reservation_usd(config(), seconds)


def test_budget_includes_all_past_attempts_and_refuses_overspend():
    with pytest.raises(ValueError, match="budget"):
        live.check_budget(config(), [{"reserved_usd": "299"}], 3600)


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "0"])
def test_invalid_live_price_cannot_authorize_job(value):
    cfg = config()
    cfg["budget"]["hourly_usd"] = value
    with pytest.raises(ValueError):
        live.check_budget(cfg, [], 3600)


def test_modified_budget_cannot_expand_user_authorization():
    cfg = config()
    cfg["budget"]["reservation_limit_usd"] = "1000"
    with pytest.raises(ValueError):
        live.check_budget(cfg, [], 3600)


def test_wrong_identity_is_rejected():
    with pytest.raises(ValueError):
        live.verify_identity({"Account": "180294183052", "Arn": "anything"})


def test_wrong_role_in_correct_account_is_rejected():
    with pytest.raises(ValueError):
        live.verify_identity({
            "Account": "061525506239",
            "Arn": "arn:aws:sts::061525506239:assumed-role/Other/test",
        })


def test_supported_image_expires_fail_closed():
    with pytest.raises(ValueError, match="support"):
        live.check_runtime(config(), today=date(2027, 5, 1))


def test_request_is_single_instance_bounded_and_uses_immutable_image():
    cfg = config()
    inv = {"experiment_id": "qwen-pii-20260916-test", "bucket": "owned",
           "role_arn": "arn:aws:iam::061525506239:role/owned"}
    req = live.build_request(cfg, inv, "smoke", "qwen-pii-20260916-test-smoke-01",
                             3600, 4, "a" * 64)
    assert req["StoppingCondition"] == {"MaxRuntimeInSeconds": 3600}
    assert req["ResourceConfig"]["InstanceCount"] == 1
    assert "@sha256:" in req["AlgorithmSpecification"]["TrainingImage"]
    assert "KeepAlivePeriodInSeconds" not in req["ResourceConfig"]
    assert req["EnableManagedSpotTraining"] is False
    assert {x["ChannelName"] for x in req["InputDataConfig"]} == {"code", "dataset"}
    assert req["Environment"]["SOURCE_SHA256"] == "a" * 64


def test_mismatched_runtime_and_parallel_gpu_count_fail():
    cfg = config()
    cfg["compute"]["instance_count"] = 2
    with pytest.raises(ValueError):
        live.check_runtime(cfg)
    cfg = config()
    cfg["runtime"]["torch"] = "2.8.0"
    with pytest.raises(ValueError):
        live.check_runtime(cfg)


def test_multiple_active_jobs_prevent_new_submission():
    with pytest.raises(ValueError, match="active"):
        live.assert_no_active_jobs([{"status": "InProgress"}])
    live.assert_no_active_jobs([{"status": "Completed"}, {"status": "Failed"}])


def test_full_run_requires_successful_smoke_evidence():
    with pytest.raises(ValueError, match="smoke"):
        live.validate_stage("full", [])
    live.validate_stage("smoke", [])
    live.validate_stage("full", [
        {"mode": "smoke", "status": "Completed", "smoke_verified": True}
    ])


def test_other_evidence_directory_cannot_reset_authorization_budget(tmp_path):
    with pytest.raises(ValueError, match="canonical"):
        live.validate_evidence(tmp_path / "another-budget")
    live.validate_evidence(live.canonical_evidence())


def test_prepare_refuses_existing_jobs_before_mutating_evidence(tmp_path, monkeypatch):
    inv = {"jobs": [{"name": "submitted"}], "state": "ready",
           "source_sha256": "old-source"}
    path = tmp_path / "inventory.json"
    live.write_json(path, inv)
    original = path.read_bytes()
    monkeypatch.setattr(live, "make_bundle",
                        lambda evidence: pytest.fail("bundle changed before guard"))
    args = SimpleNamespace(evidence=tmp_path, config=live.PACKAGE / "config/execution-20260916.json",
                           execute=False, dataset_dir=None)
    with pytest.raises(ValueError, match="submitted"):
        live.provision(args, config())
    assert path.read_bytes() == original


def test_ready_preview_does_not_rewrite_verified_inputs(tmp_path, monkeypatch):
    path = tmp_path / "inventory.json"
    live.write_json(path, {"jobs": [], "state": "ready",
                          "experiment_id": "owned", "source_sha256": "old-source"})
    original = path.read_bytes()
    monkeypatch.setattr(live, "make_bundle",
                        lambda evidence: pytest.fail("preview rebuilt verified bundle"))
    args = SimpleNamespace(evidence=tmp_path, config=live.PACKAGE / "config/execution-20260916.json",
                           execute=False, dataset_dir=None)
    live.provision(args, config())
    assert path.read_bytes() == original


def test_provision_failure_cannot_leave_ready_status(tmp_path, monkeypatch):
    args = SimpleNamespace(evidence=tmp_path, config=live.PACKAGE / "config/execution-20260916.json",
                           execute=True, dataset_dir=tmp_path / "dataset")
    inv = {"jobs": [], "state": "ready", "experiment_id": "owned", "source_sha256": "old"}
    live.write_json(tmp_path / "inventory.json", inv)
    monkeypatch.setattr(live, "session", lambda: pytest.fail("ready resources must not be reprovisioned"))
    with pytest.raises(ValueError, match="ready"):
        live.provision(args, config())
    assert live.read_json(tmp_path / "inventory.json") == inv


def test_nonpackaged_config_is_rejected_before_source_creation(tmp_path, monkeypatch):
    altered = config()
    altered["training"]["learning_rate"] = 0.001
    path = tmp_path / "different.json"
    path.write_text(json.dumps(altered))
    args = SimpleNamespace(evidence=tmp_path, config=path, execute=False, dataset_dir=None)
    monkeypatch.setattr(live, "make_bundle", lambda evidence: pytest.fail("incorrect config bundled"))
    with pytest.raises(ValueError, match="packaged"):
        live.provision(args, altered)


def test_connection_failure_leaves_provisioning_blocked(tmp_path, monkeypatch):
    from data import execution_dataset

    args = SimpleNamespace(evidence=tmp_path, config=live.PACKAGE / "config/execution-20260916.json",
                           execute=True, dataset_dir=tmp_path / "dataset")
    monkeypatch.setattr(execution_dataset, "audit_execution_dataset",
                        lambda path: {"sha256": {"train": "a", "validation": "b", "test": "c"}})
    monkeypatch.setattr(live, "make_bundle", lambda evidence: (tmp_path / "source.tar.gz", "a" * 64))

    def disconnected():
        raise TimeoutError("Cloud connection interrupted")

    monkeypatch.setattr(live, "session", disconnected)
    with pytest.raises(TimeoutError):
        live.provision(args, config())
    inv = live.read_json(tmp_path / "inventory.json")
    assert inv["state"] == "provisioning"
    assert inv["jobs"] == []


def test_real_sdk_stream_hash_closes_body_and_verifies_all_bytes():
    from botocore.response import StreamingBody

    content = b"validated-input" * 100_000
    raw = io.BytesIO(content)
    body = StreamingBody(raw, len(content))
    assert live.hash_s3_body(body) == hashlib.sha256(content).hexdigest()
    assert raw.closed


def test_stream_hash_closes_body_when_download_is_incomplete():
    from botocore.response import StreamingBody
    from botocore.exceptions import IncompleteReadError

    raw = io.BytesIO(b"partial")
    body = StreamingBody(raw, 100)
    with pytest.raises(IncompleteReadError):
        live.hash_s3_body(body)
    assert raw.closed

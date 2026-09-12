"""Offline regression tests for submission and interruption boundaries."""

import json
from unittest.mock import Mock

import pytest
from botocore.exceptions import WaiterError

from launch import sagemaker_train
from test_sagemaker_request import build_request


def test_config_is_loaded_from_the_source_bundle():
    assert build_request()["HyperParameters"]["config"] == (
        "/opt/ml/code/config/experiment.yaml"
    )


def test_long_experiment_names_keep_mode_and_unique_identity():
    first = sagemaker_train.training_job_name("qwen-pii-" + "a" * 70, "smoke")
    second = sagemaker_train.training_job_name("qwen-pii-" + "a" * 69 + "b", "smoke")
    full = sagemaker_train.training_job_name("qwen-pii-" + "a" * 70, "full")
    assert len(first) <= 63
    assert first.endswith("-smoke")
    assert len({first, second, full}) == 3


def test_submission_journal_survives_interruption(tmp_path):
    client = Mock()
    request = build_request()
    journal = tmp_path / "job.json"

    def create(**kwargs):
        assert json.loads(journal.read_text())["state"] == "submitting"
        return {"TrainingJobArn": "arn:example"}

    client.create_training_job.side_effect = create
    client.get_waiter.return_value.wait.side_effect = KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        sagemaker_train.submit_and_wait(
            request, "ap-northeast-2", journal_path=journal, client=client
        )
    client.stop_training_job.assert_called_once_with(
        TrainingJobName=request["TrainingJobName"]
    )
    assert json.loads(journal.read_text())["state"] == "stop_requested"


def test_failed_creation_does_not_stop_a_preexisting_job(tmp_path):
    client = Mock()
    client.create_training_job.side_effect = RuntimeError("already exists")
    with pytest.raises(RuntimeError):
        sagemaker_train.submit_and_wait(
            build_request(), "ap-northeast-2",
            journal_path=tmp_path / "job.json", client=client
        )
    client.stop_training_job.assert_not_called()


def test_wait_timeout_records_requested_stop(tmp_path):
    client = Mock()
    client.get_waiter.return_value.wait.side_effect = WaiterError(
        name="test", reason="Max attempts exceeded", last_response={}
    )
    client.describe_training_job.return_value = {"TrainingJobStatus": "InProgress"}
    journal = tmp_path / "job.json"
    with pytest.raises(WaiterError):
        sagemaker_train.submit_and_wait(
            build_request(), "ap-northeast-2", journal_path=journal, client=client
        )
    assert json.loads(journal.read_text())["state"] == "stop_requested"
    client.stop_training_job.assert_called_once()


def test_an_existing_journal_is_not_overwritten(tmp_path):
    journal = tmp_path / "job.json"
    journal.write_text('{"state":"submitting"}')
    client = Mock()
    with pytest.raises(FileExistsError):
        sagemaker_train.submit_and_wait(
            build_request(), "ap-northeast-2", journal_path=journal, client=client
        )
    client.create_training_job.assert_not_called()


def test_preview_preserves_the_request_of_a_submitted_job(tmp_path, monkeypatch):
    from types import SimpleNamespace

    request = build_request()
    name = request["TrainingJobName"]
    submitted = tmp_path / f"{name}-request.json"
    submitted.write_text(json.dumps({"original": True}))
    journal = tmp_path / f"{name}-job.json"
    journal.write_text(json.dumps({"state": "submitted"}))
    inventory_path = tmp_path / "resource-inventory.json"
    inventory_path.write_text(json.dumps({"region": "ap-northeast-2", "source_s3_uri": "s3://new/source"}))
    config_path = tmp_path / "config.yaml"
    config_path.write_text("{}")
    monkeypatch.setattr(sagemaker_train, "build_training_job_request", lambda *args: request)
    monkeypatch.setattr(sagemaker_train, "parse_args", lambda: SimpleNamespace(
        execute=False, inventory=inventory_path, config=config_path,
        mode="smoke", source_s3_uri=None,
    ))
    assert sagemaker_train.main() == 0
    assert json.loads(submitted.read_text()) == {"original": True}
    assert json.loads(journal.read_text()) == {"state": "submitted"}
    assert len(list((tmp_path / "previews").glob("*.json"))) == 1


def test_orphan_request_blocks_a_new_submission(tmp_path):
    request = build_request()
    path = tmp_path / f"{request['TrainingJobName']}-request.json"
    path.write_text('{"original": true}')
    client = Mock()
    with pytest.raises(FileExistsError):
        sagemaker_train.submit_and_wait(
            request, "ap-northeast-2",
            journal_path=tmp_path / f"{request['TrainingJobName']}-job.json",
            client=client,
        )
    client.create_training_job.assert_not_called()
    assert json.loads(path.read_text()) == {"original": True}


def test_submission_holds_the_shared_cleanup_lock_through_acceptance(tmp_path):
    import fcntl

    request = build_request()
    inventory_path = tmp_path / "resource-inventory.json"
    client = Mock()
    client.describe_training_job.return_value = {"TrainingJobStatus": "Completed"}

    def create(**kwargs):
        saved = tmp_path / f"{request['TrainingJobName']}-request.json"
        assert json.loads(saved.read_text()) == request
        with open(str(inventory_path) + ".lock", "a") as lock:
            with pytest.raises(BlockingIOError):
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return {}

    client.create_training_job.side_effect = create
    sagemaker_train.submit_and_wait(
        request, "ap-northeast-2",
        journal_path=tmp_path / f"{request['TrainingJobName']}-job.json",
        inventory_path=inventory_path, client=client,
    )

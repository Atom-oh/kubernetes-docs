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

"""Offline lifecycle regressions: injected clients never contact AWS."""
import json
from pathlib import Path

import pytest
from botocore.exceptions import ClientError

from launch.aws.lifecycle import Lifecycle, RecoveryRequired, initialize, validate_inputs


def error(code):
    return ClientError({"Error": {"Code": code, "Message": "fixture"}}, "Fixture")


class Client:
    def __init__(self, **answers):
        self.answers = answers
        self.calls = []

    def __getattr__(self, name):
        def call(**kwargs):
            self.calls.append((name, kwargs))
            answer = self.answers[name]
            if isinstance(answer, Exception):
                raise answer
            if callable(answer):
                return answer(**kwargs)
            return answer
        return call

    def get_paginator(self, name):
        client = self
        class Pages:
            def paginate(self, **kwargs):
                yield getattr(client, name)(**kwargs)
        return Pages()


def inventory(tmp_path):
    path = tmp_path / "resource-inventory.json"
    initialize(path, {
        "account_id": "111122223333", "region": "ap-northeast-2",
        "experiment_id": "qwen-pii-fixture", "bucket_name": "fixture-bucket",
        "execution_role_name": "fixture-exec", "mlflow_role_name": "fixture-mlflow",
        "unified_domain_id": "dzd_fixture", "project_profile_id": "profile",
        "project_owner_group_id": "group",
    })
    return path


def lifecycle(tmp_path, **clients):
    path = inventory(tmp_path)
    clients["sts"] = Client(get_caller_identity={"Account": "111122223333"})
    return Lifecycle(path, clients=clients, sleep=lambda _: None)


def test_legacy_inventory_refuses_before_any_cloud_call(tmp_path):
    path = tmp_path / "old.json"
    path.write_text('{"experiment_id":"qwen-pii-old"}')
    with pytest.raises(RecoveryRequired, match="legacy"):
        Lifecycle(path, clients={})


def test_inventory_is_exclusive_and_private(tmp_path):
    path = inventory(tmp_path)
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        initialize(path, {})


def test_role_collision_never_becomes_owned(tmp_path):
    iam = Client(get_role={"Role": {"Arn": "existing", "RoleId": "old"}})
    lc = lifecycle(tmp_path, iam=iam)
    with pytest.raises(RecoveryRequired, match="exists"):
        lc.create("execution_role", {"RoleName": "fixture-exec"})
    assert not lc.data["resources"]["execution_role"]["created"]
    assert [n for n, _ in iam.calls] == ["get_role"]


def test_create_intent_precedes_mutation_and_lost_response_is_unknown(tmp_path):
    def lost(**kwargs):
        disk = json.loads(lc.path.read_text())
        assert disk["resources"]["execution_role"]["state"] == "creating"
        assert disk["resources"]["execution_role"]["created"] is False
        raise TimeoutError("lost response")
    iam = Client(get_role=error("NoSuchEntity"), create_role=lost)
    lc = lifecycle(tmp_path, iam=iam)
    with pytest.raises(TimeoutError):
        lc.create("execution_role", {"RoleName": "fixture-exec"})
    assert json.loads(lc.path.read_text())["resources"]["execution_role"]["state"] == "unknown"


def test_auth_error_is_not_absence(tmp_path):
    lc = lifecycle(tmp_path, iam=Client(get_role=error("AccessDenied")))
    with pytest.raises(ClientError):
        lc.create("execution_role", {"RoleName": "fixture-exec"})
    assert not lc.data["resources"]["execution_role"]["created"]


def test_account_mismatch_blocks_mutations(tmp_path):
    lc = lifecycle(tmp_path)
    lc.clients["sts"] = Client(get_caller_identity={"Account": "999900001111"})
    with pytest.raises(RecoveryRequired, match="account"):
        lc.account()


def test_unknown_resource_blocks_cleanup(tmp_path):
    lc = lifecycle(tmp_path)
    lc.data["resources"]["bucket"]["state"] = "unknown"
    lc.save()
    with pytest.raises(RecoveryRequired, match="unknown"):
        lc.teardown()


def test_datazone_inputs_required_before_queries():
    with pytest.raises(RecoveryRequired, match="DATAZONE"):
        validate_inputs({}, {})


def test_s3_partial_error_terminates_loop(tmp_path):
    s3 = Client(
        list_object_versions={"Versions": [{"Key": "x", "VersionId": "1"}]},
        delete_objects={"Errors": [{"Key": "x", "Code": "AccessDenied"}]},
    )
    lc = lifecycle(tmp_path, s3=s3)
    with pytest.raises(RecoveryRequired, match="object"):
        lc.empty_bucket()
    assert [n for n, _ in s3.calls] == ["list_object_versions", "delete_objects"]


def test_s3_repeated_versions_are_bounded(tmp_path):
    s3 = Client(
        list_object_versions={"Versions": [{"Key": "x", "VersionId": "1"}]},
        delete_objects={},
    )
    lc = lifecycle(tmp_path, s3=s3)
    with pytest.raises(RecoveryRequired, match="progress"):
        lc.empty_bucket()
    assert len(s3.calls) <= 4


def write_job(lc, state):
    name = "qwen-pii-fixture-smoke"
    (lc.path.parent / f"{name}-job.json").write_text(json.dumps({
        "training_job_name": name, "region": lc.data["region"], "state": state,
    }))
    (lc.path.parent / f"{name}-request.json").write_text(json.dumps({
        "TrainingJobName": name,
        "RoleArn": "arn:aws:iam::111122223333:role/fixture-exec",
        "Tags": [{"Key": "ExperimentId", "Value": lc.data["experiment_id"]}],
    }))
    lc.data["execution_role_arn"] = "arn:aws:iam::111122223333:role/fixture-exec"
    return name


def test_ambiguous_job_submission_is_never_stopped(tmp_path):
    lc = lifecycle(tmp_path, sagemaker=Client())
    write_job(lc, "submission_unknown")
    with pytest.raises(RecoveryRequired, match="submission_unknown"):
        lc.training_jobs(stop=True)
    assert not lc.clients["sagemaker"].calls


def test_job_tags_must_match_before_stop(tmp_path):
    sm = Client(
        describe_training_job={
            "TrainingJobArn": "arn:aws:sagemaker:ap-northeast-2:111122223333:training-job/qwen-pii-fixture-smoke",
            "RoleArn": "arn:aws:iam::111122223333:role/fixture-exec",
            "TrainingJobStatus": "InProgress",
        },
        list_tags={"Tags": [{"Key": "ExperimentId", "Value": "someone-else"}]},
    )
    lc = lifecycle(tmp_path, sagemaker=sm)
    write_job(lc, "submitted")
    with pytest.raises(RecoveryRequired, match="ownership"):
        lc.training_jobs(stop=True)
    assert "stop_training_job" not in [n for n, _ in sm.calls]


def test_verification_records_unknown_and_is_not_clean(tmp_path):
    lc = lifecycle(tmp_path, iam=Client(get_role=error("AccessDenied")))
    lc.data["resources"]["execution_role"].update(
        state="owned", created=True, identity={"Arn": "arn", "RoleId": "id"}
    )
    report = lc.verify()
    assert report["unknown"]
    assert not report["clean"]


def test_confirmed_job_is_stopped_before_storage_deletion(tmp_path):
    statuses = iter(["InProgress", "Stopping", "Stopped"])
    sm = Client(
        describe_training_job=lambda **_: {
            "TrainingJobArn": "arn:aws:sagemaker:ap-northeast-2:111122223333:training-job/qwen-pii-fixture-smoke",
            "RoleArn": "arn:aws:iam::111122223333:role/fixture-exec",
            "TrainingJobStatus": next(statuses),
        },
        list_tags={"Tags": [{"Key": "ExperimentId", "Value": "qwen-pii-fixture"}]},
        stop_training_job={},
    )
    lc = lifecycle(tmp_path, sagemaker=sm)
    name = write_job(lc, "submitted")
    with pytest.raises(RecoveryRequired, match="Export SageMaker"):
        lc.teardown()
    journal = json.loads((tmp_path / f"{name}-job.json").read_text())
    assert journal["state"] == "Stopped"
    assert "stop_training_job" in [n for n, _ in sm.calls]


def test_stop_timeout_keeps_storage_and_roles(tmp_path):
    sm = Client(
        describe_training_job={
            "TrainingJobArn": "arn:aws:sagemaker:ap-northeast-2:111122223333:training-job/qwen-pii-fixture-smoke",
            "RoleArn": "arn:aws:iam::111122223333:role/fixture-exec",
            "TrainingJobStatus": "InProgress",
        },
        list_tags={"Tags": [{"Key": "ExperimentId", "Value": "qwen-pii-fixture"}]},
        stop_training_job={},
    )
    lc = lifecycle(tmp_path, sagemaker=sm)
    write_job(lc, "submitted")
    with pytest.raises(RecoveryRequired, match="unconfirmed"):
        lc.teardown(discard_artifacts=True)
    assert len([n for n, _ in sm.calls if n == "describe_training_job"]) == 61


def test_supplied_datazone_ids_are_queried_directly():
    dz = Client(
        get_domain={"id": "dzd_fixture", "status": "AVAILABLE"},
        get_project_profile={"id": "profile", "status": "ENABLED"},
        get_group_profile={"id": "group", "status": "ASSIGNED"},
    )
    clients = {"sts": Client(get_caller_identity={"Account": "111122223333"}), "datazone": dz}
    env = dict(EXPECTED_ACCOUNT_ID="111122223333", DATAZONE_DOMAIN_ID="dzd_fixture",
               DATAZONE_PROJECT_PROFILE_ID="profile", DATAZONE_OWNER_GROUP_ID="group")
    assert validate_inputs(clients, env) == env["EXPECTED_ACCOUNT_ID"]
    assert dz.calls[-1] == ("get_group_profile", {
        "domainIdentifier": "dzd_fixture", "groupIdentifier": "group"})


def test_successful_role_create_records_immutable_identity(tmp_path):
    iam = Client(get_role=error("NoSuchEntity"), create_role={"Role": {
        "Arn": "arn:aws:iam::111122223333:role/fixture-exec", "RoleId": "unique-role-id",
    }})
    lc = lifecycle(tmp_path, iam=iam)
    lc.create("execution_role", {"RoleName": "fixture-exec"})
    owned = json.loads(lc.path.read_text())["resources"]["execution_role"]
    assert owned["created"] and owned["state"] == "owned"
    assert owned["identity"]["RoleId"] == "unique-role-id"
    assert iam.calls[-1][1]["Tags"] == lc.tags()

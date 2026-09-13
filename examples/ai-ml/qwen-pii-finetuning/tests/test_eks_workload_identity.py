"""CPU-only credential delivery and owned-identity cleanup regressions."""
import json
from pathlib import Path

import pytest

from launch.aws.lifecycle import RecoveryRequired
from test_eks_manifests import load_documents
from test_lifecycle_safety import Client, error, lifecycle


def test_no_bearer_values_and_sdk_uses_workload_identity():
    job = load_documents("training-job.yaml")[0]
    pod = job["spec"]["template"]["spec"]
    container = pod["containers"][0]
    env = {entry["name"]: entry["value"] for entry in container["env"]}
    assert pod["serviceAccountName"] == "qwen-input-reader"
    assert env["AWS_EC2_METADATA_DISABLED"] == "true"
    assert env["AWS_DEFAULT_REGION"] == "ap-northeast-2"
    assert all(key not in env for key in (
        "SOURCE_URL", "TRAIN_URL", "VALIDATION_URL", "TEST_URL", "MANIFEST_URL",
        "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"))
    assert all("X-Amz-" not in str(value) for value in env.values())
    assert all(env[key] for key in ("QWEN_EXPERIMENT_ID", "QWEN_CLUSTER_NAME", "QWEN_EXECUTION_ID"))
    command = container["args"][0]
    assert "/opt/qwen/bootstrap/download_inputs.py" in command
    assert "tar -xzf /workspace/source.tar.gz" in command
    assert "urllib" not in command
    assert any(v.get("configMap", {}).get("name") == "qwen-pii-input-loader" for v in pod["volumes"])
    assert any(v["mountPath"] == "/opt/qwen/bootstrap" and v["readOnly"]
               for v in container["volumeMounts"])


def test_workload_policy_has_exact_inputs_and_no_node_s3_grant():
    config = load_documents("cluster.yaml")[0]
    assert config["iam"]["withOIDC"] is False
    assert config["addons"] == [{"name": "eks-pod-identity-agent"}]
    association = config["iam"]["podIdentityAssociations"][0]
    assert association["namespace"] == "qwen-pii"
    assert association["serviceAccountName"] == "qwen-input-reader"
    assert association["createServiceAccount"] is True
    assert association["disableSessionTags"] is False
    statement = association["permissionPolicy"]["Statement"]
    assert len(statement) == 1
    statement = statement[0]
    assert statement["Action"] == "s3:GetObject"
    expected = {"arn:aws:s3:::qwen-fixture/qwen-pii/qwen-pii-unit-test/" + key for key in (
        "source/source.tar.gz", "dataset/train.jsonl", "dataset/validation.jsonl",
        "dataset/test.jsonl", "dataset/dataset-manifest.json")}
    assert set(statement["Resource"]) == expected
    assert all("*" not in arn for arn in statement["Resource"])
    condition = statement["Condition"]["StringEquals"]
    assert condition["s3:ResourceAccount"] == "111122223333"
    assert condition["aws:PrincipalTag/kubernetes-service-account"] == "qwen-input-reader"
    assert condition["aws:PrincipalTag/kubernetes-namespace"] == "qwen-pii"
    assert condition["aws:PrincipalTag/eks-cluster-arn"].endswith(":cluster/qwen-pii-unit-test")
    node = config["managedNodeGroups"][0]
    assert node["disablePodIMDS"] is True
    assert "s3:" not in json.dumps(node)
    launcher = (Path(__file__).resolve().parents[1] / "launch/eks/run.sh").read_text()
    assert "s3 presign" not in launcher
    assert "--expected-provenance" in launcher


def test_input_manifest_projects_only_expected_hashes(tmp_path):
    lc = lifecycle(tmp_path)
    prefix = "qwen-pii/qwen-pii-fixture/"
    entries = [{"key": prefix + key, "sha256": "a" * 64, "private_extra": "must-not-propagate"}
               for key in ("source/source.tar.gz", "dataset/train.jsonl", "dataset/validation.jsonl",
                           "dataset/test.jsonl", "dataset/dataset-manifest.json")]
    receipt = tmp_path / "uploaded-inputs.json"
    receipt.write_text(json.dumps({"verified": entries, "unrelated": "private"}))
    output = tmp_path / "projected.json"
    lc.input_manifest(output)
    projected = json.loads(output.read_text())
    assert len(projected["verified"]) == 5
    assert "private" not in output.read_text()
    assert lc.clients["sts"].calls == []
    entries[0]["key"] = "qwen-pii/another-experiment/source/source.tar.gz"
    receipt.write_text(json.dumps({"verified": entries}))
    with pytest.raises(RecoveryRequired):
        lc.input_manifest(output)


def identity_record():
    return {
        "name": "qwen-pii-fixture-smoke-eks",
        "workload_identity": {
            "role_name": "qwen-input-fixture", "namespace": "qwen-pii",
            "service_account": "qwen-input-reader", "addon_name": "eks-pod-identity-agent",
            "role": {"Arn": "arn:aws:iam::111122223333:role/qwen-input-fixture", "RoleId": "AROAFIXTURE"},
            "association": {
                "associationId": "a-fixture", "associationArn": "arn:association-fixture",
                "roleArn": "arn:aws:iam::111122223333:role/qwen-input-fixture",
                "namespace": "qwen-pii", "serviceAccount": "qwen-input-reader",
            },
            "addon": {"addonArn": "arn:addon-fixture", "createdAt": "fixture-time"},
        },
    }


def test_deleted_cluster_does_not_hide_remaining_workload_role(tmp_path):
    record = identity_record()
    eks = Client(describe_pod_identity_association=error("ResourceNotFoundException"),
                 describe_addon=error("ResourceNotFoundException"))
    lc = lifecycle(tmp_path, eks=eks, iam=Client(get_role={"Role": record["workload_identity"]["role"]}))
    assert lc.probe_workload_identity(record) is True


def test_unknown_workload_identity_read_never_means_absent(tmp_path):
    lc = lifecycle(tmp_path, iam=Client(get_role=error("AccessDenied")))
    with pytest.raises(Exception):
        lc.probe_workload_identity(identity_record())


def test_all_recorded_workload_resources_must_be_absent(tmp_path):
    lc = lifecycle(tmp_path, iam=Client(get_role=error("NoSuchEntity")),
                   eks=Client(describe_pod_identity_association=error("ResourceNotFoundException"),
                              describe_addon=error("ResourceNotFoundException")))
    assert lc.probe_workload_identity(identity_record()) is False


def test_association_mismatch_refuses_cleanup(tmp_path):
    record = identity_record()
    association = dict(record["workload_identity"]["association"], roleArn="foreign-role")
    lc = lifecycle(tmp_path, iam=Client(get_role={"Role": record["workload_identity"]["role"]}),
                   eks=Client(describe_pod_identity_association={"association": association}))
    with pytest.raises(RecoveryRequired, match="ownership"):
        lc.probe_workload_identity(record)


def test_confirm_records_role_association_agent_and_three_stacks(tmp_path):
    lc = lifecycle(tmp_path, eks=Client(describe_cluster=error("ResourceNotFoundException")),
                   iam=Client(get_role=error("NoSuchEntity")))
    lc.stack = lambda _: None
    name = "qwen-pii-fixture-smoke-eks"
    lc.eks_plan(name, tmp_path / "kubeconfig")
    record = lc.data["resources"]["eks:" + name]
    role_name = record["workload_identity"]["role_name"]
    role_arn = "arn:aws:iam::111122223333:role/" + role_name
    created = "2026-09-12T00:00:00Z"
    tags = {t["Key"]: t["Value"] for t in lc.tags()}
    lc.clients["iam"] = Client(get_role={"Role": {"Arn": role_arn, "RoleId": "AROANEW"}})
    lc.clients["eks"] = Client(
        describe_cluster={"cluster": {
            "arn": "arn:aws:eks:ap-northeast-2:111122223333:cluster/" + name,
            "createdAt": created, "endpoint": "https://fixture.invalid", "tags": tags,
        }},
        list_pod_identity_associations={"associations": [{"associationId": "a-new"}]},
        describe_pod_identity_association={"association": {
            "associationId": "a-new", "associationArn": "arn:association-new",
            "roleArn": role_arn, "namespace": "qwen-pii",
            "serviceAccount": "qwen-input-reader", "tags": tags,
        }},
        describe_addon={"addon": {
            "status": "ACTIVE", "addonArn": "arn:addon-new", "createdAt": created,
        }},
    )
    lc.stack = lambda n: {
        "StackId": n, "StackStatus": "CREATE_COMPLETE", "CreationTime": created, "Tags": lc.tags(),
    }
    lc.stack_resources = lambda _: [{"ResourceType": "AWS::IAM::Role", "PhysicalResourceId": role_name}]
    lc.eks_confirm(name)
    saved = json.loads(lc.path.read_text())["resources"]["eks:" + name]
    assert saved["created"] is True
    assert len(saved["identity"]["stacks"]) == 3
    assert saved["workload_identity"]["role"]["RoleId"] == "AROANEW"
    assert saved["workload_identity"]["association"]["associationId"] == "a-new"
    assert saved["workload_identity"]["addon"]["addonArn"] == "arn:addon-new"
    assert saved["expected_export"] == record["expected_export"]

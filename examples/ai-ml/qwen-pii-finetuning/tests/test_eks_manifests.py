from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
EKS = ROOT / "launch" / "eks"


def load_documents(name: str) -> list[dict]:
    text = (EKS / name).read_text()
    replacements = {
        "${EXPERIMENT_ID}": "qwen-pii-unit-test",
        "${MODE}": "smoke",
        "${STEPS}": "10",
        "${SOURCE_URL}": "https://example.com/source",
        "${TRAIN_URL}": "https://example.com/train",
        "${VALIDATION_URL}": "https://example.com/validation",
        "${TEST_URL}": "https://example.com/test",
        "${MANIFEST_URL}": "https://example.com/manifest",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return [document for document in yaml.safe_load_all(text) if document]


def test_cluster_uses_one_ephemeral_g6e_managed_node():
    cluster = load_documents("cluster.yaml")[0]
    node_group = cluster["managedNodeGroups"][0]

    assert cluster["metadata"]["name"] == "qwen-pii-unit-test"
    assert cluster["metadata"]["region"] == "ap-northeast-2"
    assert cluster["metadata"]["version"] == "1.36"
    assert node_group["instanceType"] == "g6e.4xlarge"
    assert node_group["desiredCapacity"] == 1
    assert node_group["minSize"] == 1
    assert node_group["maxSize"] == 1
    assert node_group["volumeSize"] == 300
    assert node_group["amiFamily"] == "AmazonLinux2023"
    assert node_group["disablePodIMDS"] is True
    assert node_group["labels"]["workload"] == "qwen-pii-training"


def test_mlflow_is_internal_and_uses_ephemeral_proxied_artifacts():
    documents = load_documents("mlflow.yaml")
    deployment = next(doc for doc in documents if doc["kind"] == "Deployment")
    service = next(doc for doc in documents if doc["kind"] == "Service")
    args = deployment["spec"]["template"]["spec"]["containers"][0]["args"]

    assert service["spec"]["type"] == "ClusterIP"
    assert "--serve-artifacts" in args
    assert "--artifacts-destination=/mlflow/artifacts" in args
    assert deployment["spec"]["replicas"] == 1


def test_training_job_requests_one_gpu_and_disables_automatic_retries():
    job = load_documents("training-job.yaml")[0]
    pod_spec = job["spec"]["template"]["spec"]
    container = pod_spec["containers"][0]

    assert job["spec"]["backoffLimit"] == 0
    assert job["spec"]["activeDeadlineSeconds"] == 10800
    assert pod_spec["restartPolicy"] == "Never"
    assert pod_spec["nodeSelector"]["workload"] == "qwen-pii-training"
    assert container["resources"]["limits"]["nvidia.com/gpu"] == 1
    assert container["image"].endswith(
        "pytorch-training:2.8.0-gpu-py312-cu129-ubuntu22.04-sagemaker"
    )
    assert container["env"][0]["name"] == "SOURCE_URL"

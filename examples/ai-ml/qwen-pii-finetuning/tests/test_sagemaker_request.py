import yaml
from botocore.session import get_session
from botocore.validate import ParamValidator

from launch.sagemaker_train import build_training_job_request


def build_request():
    config = yaml.safe_load(
        """
experiment_name: qwen-pii-finetuning
model_id: Qwen/Qwen3-30B-A3B-Instruct-2507
training:
  smoke_steps: 10
  max_steps: 80
  max_runtime_seconds: 10800
compute:
  sagemaker: ml.g6e.4xlarge
"""
    )
    inventory = {
        "experiment_id": "unit-test",
        "region": "ap-northeast-2",
        "bucket_name": "sagemaker-qwen-pii-unit-test",
        "execution_role_arn": "arn:aws:iam::111122223333:role/qwen-pii-exec",
        "mlflow_app_arn": (
            "arn:aws:sagemaker:ap-northeast-2:111122223333:"
            "mlflow-app/app-123"
        ),
    }

    return build_training_job_request(
        config,
        inventory,
        "smoke",
        "s3://sagemaker-qwen-pii-unit-test/source/source.tar.gz",
    )


def test_training_job_request_uses_approved_compute_image_and_limits():
    request = build_request()

    assert request["AlgorithmSpecification"]["TrainingImage"].endswith(
        "pytorch-training:2.8.0-gpu-py312-cu129-ubuntu22.04-sagemaker"
    )
    assert request["ResourceConfig"] == {
        "InstanceType": "ml.g6e.4xlarge",
        "InstanceCount": 1,
        "VolumeSizeInGB": 300,
    }
    assert request["StoppingCondition"]["MaxRuntimeInSeconds"] == 10800
    assert request["RoleArn"] == (
        "arn:aws:iam::111122223333:role/qwen-pii-exec"
    )
    assert request["Environment"]["RUN_ENVIRONMENT"] == "sagemaker"
    assert request["Environment"]["MLFLOW_TRACKING_URI"] == (
        "arn:aws:sagemaker:ap-northeast-2:111122223333:"
        "mlflow-app/app-123"
    )
    assert request["Environment"]["SAGEMAKER_PROGRAM"] == "src/train.py"
    assert request["HyperParameters"]["steps"] == "10"
    assert request["HyperParameters"]["mode"] == "smoke"
    assert request["Tags"] == [
        {"Key": "Experiment", "Value": "qwen-pii-finetuning"},
        {"Key": "ExperimentId", "Value": "unit-test"},
    ]
    assert request["InputDataConfig"][0]["ChannelName"] == "dataset"


def test_training_job_request_matches_the_botocore_service_model():
    service_model = get_session().get_service_model("sagemaker")
    operation = service_model.operation_model("CreateTrainingJob")

    report = ParamValidator().validate(build_request(), operation.input_shape)

    assert not report.has_errors(), report.generate_report()

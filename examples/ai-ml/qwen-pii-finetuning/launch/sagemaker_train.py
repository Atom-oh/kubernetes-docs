"""Submit and monitor the SageMaker AI Qwen PII training job."""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

import yaml


DLC_ACCOUNT = "763104351884"
DLC_TAG = "2.8.0-gpu-py312-cu129-ubuntu22.04-sagemaker"


def _image_uri(region: str) -> str:
    return (
        f"{DLC_ACCOUNT}.dkr.ecr.{region}.amazonaws.com/"
        f"pytorch-training:{DLC_TAG}"
    )


def build_training_job_request(
    config: dict,
    inventory: dict,
    mode: str,
    source_s3_uri: str,
) -> dict:
    """Build a reproducible SageMaker Training Job API request."""
    if mode not in {"smoke", "full"}:
        raise ValueError(f"unsupported mode: {mode}")
    experiment_id = inventory["experiment_id"]
    region = inventory["region"]
    bucket = inventory["bucket_name"]
    steps = (
        config["training"]["smoke_steps"]
        if mode == "smoke"
        else config["training"]["max_steps"]
    )
    job_name = f"{experiment_id}-{mode}"[:63].rstrip("-")
    dataset_root = "/opt/ml/input/data/dataset"
    return {
        "TrainingJobName": job_name,
        "AlgorithmSpecification": {
            "TrainingImage": _image_uri(region),
            "TrainingInputMode": "File",
        },
        "RoleArn": inventory["execution_role_arn"],
        "InputDataConfig": [
            {
                "ChannelName": "dataset",
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": (
                            f"s3://{bucket}/qwen-pii/{experiment_id}/dataset/"
                        ),
                        "S3DataDistributionType": "FullyReplicated",
                    }
                },
                "InputMode": "File",
            }
        ],
        "OutputDataConfig": {
            "S3OutputPath": (
                f"s3://{bucket}/qwen-pii/{experiment_id}/training-output/"
            )
        },
        "ResourceConfig": {
            "InstanceType": config["compute"]["sagemaker"],
            "InstanceCount": 1,
            "VolumeSizeInGB": 300,
        },
        "StoppingCondition": {
            "MaxRuntimeInSeconds": int(
                config["training"]["max_runtime_seconds"]
            )
        },
        "EnableManagedSpotTraining": False,
        "HyperParameters": {
            "config": f"{dataset_root}/experiment.yaml",
            "train-jsonl": f"{dataset_root}/train.jsonl",
            "validation-jsonl": f"{dataset_root}/validation.jsonl",
            "test-jsonl": f"{dataset_root}/test.jsonl",
            "dataset-manifest": f"{dataset_root}/dataset-manifest.json",
            "output-dir": "/opt/ml/model",
            "steps": str(steps),
            "environment": "sagemaker",
            "mode": mode,
            "evaluation-batch-size": "4",
        },
        "Environment": {
            "RUN_ENVIRONMENT": "sagemaker",
            "MLFLOW_TRACKING_URI": inventory["mlflow_app_arn"],
            "MLFLOW_EXPERIMENT_NAME": config["experiment_name"],
            "SAGEMAKER_PROGRAM": "src/train.py",
            "SAGEMAKER_SUBMIT_DIRECTORY": source_s3_uri,
            "SAGEMAKER_CONTAINER_LOG_LEVEL": "20",
            "SAGEMAKER_REGION": region,
            "AWS_DEFAULT_REGION": region,
            "AWS_SDK_UA_APP_ID": "AWSSkill-SageMaker",
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "HF_HOME": "/opt/ml/input/data/hf-cache",
        },
        "Tags": [
            {"Key": "Experiment", "Value": "qwen-pii-finetuning"},
            {"Key": "ExperimentId", "Value": experiment_id},
        ],
    }


def _json_safe(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def _sanitized_description(description: dict) -> dict:
    resource = description.get("ResourceConfig", {})
    return {
        "training_job_name": description["TrainingJobName"],
        "status": description["TrainingJobStatus"],
        "secondary_status": description.get("SecondaryStatus"),
        "failure_reason": description.get("FailureReason"),
        "instance_type": resource.get("InstanceType"),
        "instance_count": resource.get("InstanceCount"),
        "volume_size_gb": resource.get("VolumeSizeInGB"),
        "creation_time": description.get("CreationTime"),
        "training_start_time": description.get("TrainingStartTime"),
        "training_end_time": description.get("TrainingEndTime"),
        "training_time_seconds": description.get("TrainingTimeInSeconds"),
        "billable_time_seconds": description.get("BillableTimeInSeconds"),
    }


def submit_and_wait(request: dict, region: str) -> dict:
    """Submit one training job and return its terminal description."""
    import boto3
    from botocore.config import Config
    from botocore.exceptions import WaiterError

    client = boto3.Session(region_name=region).client(
        "sagemaker",
        config=Config(
            retries={"total_max_attempts": 5, "mode": "adaptive"},
            connect_timeout=10,
            read_timeout=60,
        ),
    )
    client.create_training_job(**request)
    waiter = client.get_waiter("training_job_completed_or_stopped")
    try:
        waiter.wait(
            TrainingJobName=request["TrainingJobName"],
            WaiterConfig={"Delay": 30, "MaxAttempts": 370},
        )
    except WaiterError:
        description = client.describe_training_job(
            TrainingJobName=request["TrainingJobName"]
        )
        if description["TrainingJobStatus"] not in {
            "Completed",
            "Failed",
            "Stopped",
        }:
            raise
        return description
    return client.describe_training_job(
        TrainingJobName=request["TrainingJobName"]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "full"), required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "config"
        / "experiment.yaml",
    )
    parser.add_argument("--source-s3-uri")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    source_s3_uri = args.source_s3_uri or inventory["source_s3_uri"]
    request = build_training_job_request(
        config, inventory, args.mode, source_s3_uri
    )
    description = submit_and_wait(request, inventory["region"])
    result_path = (
        Path(__file__).resolve().parents[1]
        / "results"
        / f"sagemaker-{args.mode}.json"
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(
            _sanitized_description(description),
            default=_json_safe,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    status = description["TrainingJobStatus"]
    print(f"Training job {request['TrainingJobName']} finished with {status}.")
    return 0 if status == "Completed" else 1


if __name__ == "__main__":
    sys.exit(main())

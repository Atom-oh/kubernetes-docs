"""Submit and monitor the SageMaker AI Qwen PII training job."""

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
import re
import signal
import sys
import uuid
from datetime import date, datetime
from pathlib import Path

import yaml

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.runtime_contract import require_supported_baseline


DLC_ACCOUNT = "763104351884"
DLC_TAG = "2.8.0-gpu-py312-cu129-ubuntu22.04-sagemaker"


def training_job_name(experiment_id: str, mode: str) -> str:
    if mode not in {"smoke", "full"} or not re.fullmatch(
        r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", experiment_id
    ):
        raise ValueError("Invalid experiment ID or mode")
    name = f"{experiment_id}-{mode}"
    if len(name) <= 63:
        return name
    digest = hashlib.sha256(experiment_id.encode()).hexdigest()[:12]
    prefix = experiment_id[: 63 - len(digest) - len(mode) - 2].rstrip("-")
    return f"{prefix}-{digest}-{mode}"


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
    job_name = training_job_name(experiment_id, mode)
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
            "config": "/opt/ml/code/config/experiment.yaml",
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


def _write_journal(path: Path, value: dict, *, create: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    target = path if create else path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    with os.fdopen(os.open(target, flags, 0o600), "w", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    if not create:
        target.replace(path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


@contextmanager
def _submission_lock(journal_path: Path, inventory_path: Path | None):
    lock_path = (
        Path(str(inventory_path) + ".lock")
        if inventory_path else journal_path.with_suffix(".lock")
    )
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with os.fdopen(os.open(lock_path, os.O_WRONLY | os.O_CREAT, 0o600), "w") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def submit_and_wait(
    request: dict, region: str, *, journal_path: Path,
    inventory_path: Path | None = None, client=None
) -> dict:
    """Record intent before submission; stop confirmed new jobs on monitor failure.

    A requested stop is asynchronous. Host loss/SIGKILL cannot run handlers.
    The journal must be reconciled with DescribeTrainingJob before any retry.
    """
    import boto3
    from botocore.config import Config
    from botocore.exceptions import WaiterError

    if client is None:
        require_supported_baseline()
        client = boto3.Session(region_name=region).client(
            "sagemaker",
            config=Config(
                retries={"total_max_attempts": 5, "mode": "adaptive"},
                connect_timeout=10,
                read_timeout=60,
            ),
        )
    journal = {
        "training_job_name": request["TrainingJobName"],
        "region": region,
        "state": "submitting",
    }
    request_path = journal_path.parent / f"{request['TrainingJobName']}-request.json"
    # Share the lifecycle lock through acceptance so cleanup cannot run in
    # the gap between request reservation and a confirmed submission record.
    with _submission_lock(journal_path, inventory_path):
        if journal_path.exists() or request_path.exists():
            raise FileExistsError("Submission evidence already exists; reconcile before retrying")
        _write_journal(request_path, request, create=True)
        _write_journal(journal_path, journal, create=True)
        try:
            client.create_training_job(**request)
        except BaseException:
            # A lost response may hide successful creation; do not stop a
            # name that could refer to a preexisting job.
            journal["state"] = "submission_unknown"
            _write_journal(journal_path, journal)
            raise
        journal["state"] = "submitted"
        _write_journal(journal_path, journal)
    try:
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
                "Completed", "Failed", "Stopped"
            }:
                raise
        else:
            description = client.describe_training_job(
                TrainingJobName=request["TrainingJobName"]
            )
    except BaseException:
        try:
            client.stop_training_job(TrainingJobName=request["TrainingJobName"])
            journal["state"] = "stop_requested"
        except Exception as error:
            journal["state"] = "stop_unconfirmed"
            journal["error_type"] = type(error).__name__
        _write_journal(journal_path, journal)
        raise
    journal["state"] = description["TrainingJobStatus"]
    _write_journal(journal_path, journal)
    return description


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
    parser.add_argument(
        "--execute", action="store_true",
        help="Submit the billable job. Without this flag only write its request.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.execute:
        require_supported_baseline()
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    source_s3_uri = args.source_s3_uri or inventory["source_s3_uri"]
    request = build_training_job_request(
        config, inventory, args.mode, source_s3_uri
    )
    if not args.execute:
        preview_path = (
            args.inventory.parent / "previews"
            / f"{request['TrainingJobName']}-{uuid.uuid4().hex}.json"
        )
        _write_journal(preview_path, request, create=True)
        print(f"Preview written to {preview_path}; no job submitted.")
        return 0
    # Python's default SIGTERM exits without running the monitoring handler.
    def interrupted(_signum, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupted)
    description = submit_and_wait(
        request, inventory["region"],
        journal_path=args.inventory.parent / f"{request['TrainingJobName']}-job.json",
        inventory_path=args.inventory,
    )
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

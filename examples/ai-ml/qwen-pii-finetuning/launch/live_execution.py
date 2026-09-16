"""Budgeted, journaled SageMaker execution using the samples assumed role.

This entry is independent of the blocked historical PyTorch 2.8 experiment.
All cloud calls require the explicit samples-atomoh profile and identity check.
The local evidence directory must survive interruptions and is never committed.
"""

import argparse
from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import uuid


ACCOUNT = "061525506239"
REGION = "ap-northeast-2"
PROFILE = "samples-atomoh"
ROLE_PREFIX = f"arn:aws:sts::{ACCOUNT}:assumed-role/atomoh/"
IMAGE = (
    "763104351884.dkr.ecr.ap-northeast-2.amazonaws.com/pytorch"
    "@sha256:ecb2d8361928ee5465c615ae970f32c475ca3fcbfe57fdcb2f9415aac227f84a"
)
PACKAGE = Path(__file__).resolve().parents[1]
TERMINAL = {"Completed", "Failed", "Stopped"}


def canonical_evidence():
    """One durable ledger for this approval, shared by every linked worktree."""
    common = Path(subprocess.check_output(
        ["git", "rev-parse", "--git-common-dir"], cwd=PACKAGE, text=True,
    ).strip())
    if not common.is_absolute():
        common = PACKAGE / common
    return (common.resolve().parent
            / ".vitepress/cache/qlora-execution-20260916/evidence/run")


def validate_evidence(path):
    if Path(path).resolve() != canonical_evidence().resolve():
        raise ValueError("This approval requires its canonical evidence directory and ledger")


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex)
    with os.fdopen(os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w") as f:
        json.dump(value, f, indent=2, sort_keys=True, default=str)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    temp.replace(path)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def read_json(path):
    return json.loads(Path(path).read_text())


@contextmanager
def locked(evidence):
    Path(evidence).mkdir(parents=True, exist_ok=True)
    with (Path(evidence) / "execution.lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def verify_identity(identity):
    if identity.get("Account") != ACCOUNT or not identity.get("Arn", "").startswith(ROLE_PREFIX):
        raise ValueError("samples account or assumed atomoh role mismatch")


def session():
    import boto3
    from botocore.config import Config
    result = boto3.Session(profile_name=PROFILE, region_name=REGION)
    client_config = Config(
        retries={"total_max_attempts": 3, "mode": "standard"},
        connect_timeout=10, read_timeout=30,
    )
    verify_identity(result.client("sts", config=client_config).get_caller_identity())
    return result, client_config


def positive_decimal(value):
    try:
        number = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError("Invalid monetary amount") from error
    if not number.is_finite() or number <= 0:
        raise ValueError("Invalid monetary amount")
    return number


def reservation_usd(config, seconds):
    if type(seconds) is not int or not 60 <= seconds <= 86400:
        raise ValueError("Invalid bounded runtime")
    budget = config["budget"]
    rate = positive_decimal(budget["hourly_usd"])
    # Floors protect against an edited config weakening the recorded envelope.
    if rate < Decimal("4.6169375"):
        raise ValueError("Rate is below verified training price")
    overhead = budget["overhead_seconds_per_job"]
    if type(overhead) is not int or overhead < 7200:
        raise ValueError("Invalid overhead reserve")
    incidental = positive_decimal(budget["incidental_usd_per_job"])
    if incidental < 5:
        raise ValueError("Incidental allowance is too small")
    return rate * Decimal(seconds + overhead) / Decimal(3600) + incidental


def check_budget(config, jobs, seconds):
    budget = config["budget"]
    ceiling = positive_decimal(budget["reservation_limit_usd"])
    if ceiling > 300 or positive_decimal(budget["user_limit_usd"]) != 500:
        raise ValueError("Configured budget exceeds authorized envelope")
    reserved = sum((positive_decimal(job["reserved_usd"]) for job in jobs), Decimal(0))
    amount = reservation_usd(config, seconds)
    if reserved + amount > ceiling:
        raise ValueError("Cumulative budget reservations would exceed limit")
    return amount


def check_runtime(config, today=None):
    current = today or datetime.now(timezone.utc).date()
    runtime = config["runtime"]
    if (runtime["patch_end"] != "2027-04-30"
            or current > date.fromisoformat(runtime["patch_end"])):
        raise ValueError("DLC patch support expired or unsupported support date")
    if (runtime["image_uri"] != IMAGE or runtime["torch"] != "2.11.0"
            or runtime["cuda"] != "13.0" or runtime["python"] != "3.12"):
        raise ValueError("Runtime differs from the reviewed supported combination")
    if (config["compute"]["instance_type"] != "ml.g6e.4xlarge"
            or type(config["compute"]["instance_count"]) is not int
            or config["compute"]["instance_count"] != 1):
        raise ValueError("Only one reviewed GPU instance is allowed")


def assert_no_active_jobs(jobs):
    if any(job.get("status") not in TERMINAL for job in jobs):
        raise ValueError("An active or unresolved job prevents new submission")


def validate_stage(mode, jobs):
    if mode not in {"smoke", "full"}:
        raise ValueError("Unknown execution mode")
    if mode == "full" and not any(
        job.get("mode") == "smoke" and job.get("status") == "Completed"
        and job.get("smoke_verified") is True for job in jobs
    ):
        raise ValueError("A completed verified GPU smoke run is required")


def build_request(config, inventory, mode, name, seconds, steps, source_sha):
    check_runtime(config)
    reservation_usd(config, seconds)
    if (mode not in {"smoke", "full"} or type(steps) is not int
            or not 1 <= steps <= 2000):
        raise ValueError("Invalid mode or optimizer step count")
    if not re.fullmatch(r"[0-9a-f]{64}", source_sha):
        raise ValueError("Invalid source bundle digest")
    bucket = inventory["bucket"]
    prefix = inventory["experiment_id"]
    channels = []
    for channel in ("code", "dataset"):
        channels.append({
            "ChannelName": channel,
            "DataSource": {"S3DataSource": {
                "S3DataType": "S3Prefix",
                "S3Uri": f"s3://{bucket}/{prefix}/{channel}/",
                "S3DataDistributionType": "FullyReplicated",
            }},
            "InputMode": "File",
        })
    return {
        "TrainingJobName": name,
        "RoleArn": inventory["role_arn"],
        "AlgorithmSpecification": {
            "TrainingImage": IMAGE,
            "TrainingInputMode": "File",
            "ContainerEntrypoint": ["python3", "/opt/ml/input/data/code/bootstrap.py"],
        },
        "InputDataConfig": channels,
        "OutputDataConfig": {"S3OutputPath": f"s3://{bucket}/{prefix}/output/"},
        "ResourceConfig": {
            "InstanceType": "ml.g6e.4xlarge", "InstanceCount": 1,
            "VolumeSizeInGB": 200,
        },
        "StoppingCondition": {"MaxRuntimeInSeconds": seconds},
        "EnableManagedSpotTraining": False,
        "Environment": {
            "RUN_MODE": mode, "RUN_STEPS": str(steps),
            "SOURCE_SHA256": source_sha,
            "HF_HOME": "/opt/ml/input/hf-cache",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "PYTHONUNBUFFERED": "1",
            "AWS_DEFAULT_REGION": REGION,
        },
        "Tags": tags(prefix),
    }


def tags(experiment):
    return [
        {"Key": "ExperimentId", "Value": experiment},
        {"Key": "ManagedBy", "Value": "Codex-Qwen-Execution"},
        {"Key": "UserBudgetUSD", "Value": "500"},
    ]


def hash_s3_body(body):
    """Retain StreamingBody's length checks and close it even on read failure."""
    digest = hashlib.sha256()
    try:
        for chunk in iter(lambda: body.read(1024 * 1024), b""):
            digest.update(chunk)
    finally:
        body.close()
    return digest.hexdigest()


def policies(inventory):
    experiment = inventory["experiment_id"]
    bucket = inventory["bucket"]
    trust = {"Version": "2012-10-17", "Statement": [{
        "Effect": "Allow", "Principal": {"Service": "sagemaker.amazonaws.com"},
        "Action": "sts:AssumeRole",
        "Condition": {
            "StringEquals": {"aws:SourceAccount": ACCOUNT},
            "ArnLike": {"aws:SourceArn": f"arn:aws:sagemaker:{REGION}:{ACCOUNT}:training-job/{experiment}-*"},
        },
    }]}
    permissions = {"Version": "2012-10-17", "Statement": [
        {"Effect": "Allow", "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
         "Resource": f"arn:aws:s3:::{bucket}"},
        {"Effect": "Allow", "Action": ["s3:GetObject"],
         "Resource": [f"arn:aws:s3:::{bucket}/{experiment}/code/*",
                      f"arn:aws:s3:::{bucket}/{experiment}/dataset/*"]},
        {"Effect": "Allow", "Action": ["s3:PutObject", "s3:AbortMultipartUpload"],
         "Resource": f"arn:aws:s3:::{bucket}/{experiment}/output/*"},
        {"Effect": "Allow",
         "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
         "Resource": f"arn:aws:logs:{REGION}:{ACCOUNT}:log-group:/aws/sagemaker/TrainingJobs:log-stream:{experiment}-*"},
        {"Effect": "Allow", "Action": "logs:CreateLogGroup",
         "Resource": f"arn:aws:logs:{REGION}:{ACCOUNT}:log-group:/aws/sagemaker/TrainingJobs"},
        {"Effect": "Allow", "Action": "ecr:GetAuthorizationToken", "Resource": "*",
         "Condition": {"StringEquals": {"aws:RequestedRegion": REGION}}},
        {"Effect": "Allow",
         "Action": ["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"],
         "Resource": f"arn:aws:ecr:{REGION}:763104351884:repository/pytorch"},
    ]}
    return trust, permissions


def make_bundle(evidence):
    path = evidence / "source.tar.gz"
    files = [
        "src/__init__.py", "src/dataset.py", "src/pii_tokens.py", "src/metrics.py",
        "src/train_execution.py", "config/execution-20260916.json",
        "requirements-execution.txt",
    ]
    if (PACKAGE / "src/execution_metrics.py").is_file():
        files.append("src/execution_metrics.py")
    with tarfile.open(path, "w:gz") as tar:
        for name in files:
            file = PACKAGE / name
            if not file.is_file() or file.is_symlink():
                raise ValueError("Source file missing or not regular: " + name)
            tar.add(file, arcname=name, recursive=False)
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def provision(args, cfg):
    evidence = args.evidence
    inventory_path = evidence / "inventory.json"
    check_runtime(cfg)
    if args.config.read_bytes() != (PACKAGE / "config/execution-20260916.json").read_bytes():
        raise ValueError("Selected configuration differs from the packaged configuration")
    if inventory_path.exists():
        inv = read_json(inventory_path)
        # These guards precede bundle/hash/policy writes, including previews.
        if inv["jobs"]:
            raise ValueError("Do not replace inputs after any submitted job")
        if inv.get("state") == "ready":
            if args.execute:
                raise ValueError("Inputs are already ready; re-provisioning is prohibited")
            print(json.dumps({"state": "ready", "experiment": inv["experiment_id"],
                              "source_sha256": inv["source_sha256"]}))
            return
        if not args.execute:
            print(json.dumps({"state": inv["state"], "experiment": inv["experiment_id"],
                              "source_sha256": inv.get("source_sha256")}))
            return
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        experiment = "qwen-pii-" + stamp
        inv = {
            "experiment_id": experiment, "region": REGION, "account": ACCOUNT,
            "bucket": f"{experiment}-{ACCOUNT}",
            "role_name": experiment + "-training",
            "role_arn": f"arn:aws:iam::{ACCOUNT}:role/{experiment}-training",
            "jobs": [], "state": "planned",
        }
        write_json(inventory_path, inv)
    if args.dataset_dir is None:
        raise ValueError("A validated dataset directory is required")
    from data.execution_dataset import audit_execution_dataset
    dataset_audit = audit_execution_dataset(args.dataset_dir)
    inv["state"] = "preparing"
    write_json(inventory_path, inv)
    bundle, source_sha = make_bundle(evidence)
    trust, permissions = policies(inv)
    write_json(evidence / "trust-policy.json", trust)
    write_json(evidence / "execution-policy.json", permissions)
    inv["source_sha256"] = source_sha
    inv["config_sha256"] = hashlib.sha256(args.config.read_bytes()).hexdigest()
    inv["dataset_sha256"] = dataset_audit["sha256"]
    write_json(inventory_path, inv)
    if not args.execute:
        print(json.dumps({"state": "preview", "experiment": inv["experiment_id"],
                          "source_sha256": source_sha}))
        return
    inv["state"] = "provisioning"
    write_json(inventory_path, inv)
    cloud, client_cfg = session()
    s3 = cloud.client("s3", config=client_cfg)
    iam = cloud.client("iam", config=client_cfg)
    # Recovery never adopts another bucket or role merely because a name matches.
    if not inv.get("bucket_created"):
        s3.create_bucket(Bucket=inv["bucket"],
                         CreateBucketConfiguration={"LocationConstraint": REGION},
                         ObjectOwnership="BucketOwnerEnforced")
        inv["bucket_created"] = True
        write_json(inventory_path, inv)
    s3.put_public_access_block(
        Bucket=inv["bucket"], ExpectedBucketOwner=ACCOUNT,
        PublicAccessBlockConfiguration={k: True for k in (
            "BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")},
    )
    s3.put_bucket_encryption(
        Bucket=inv["bucket"], ExpectedBucketOwner=ACCOUNT,
        ServerSideEncryptionConfiguration={"Rules": [
            {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]},
    )
    s3.put_bucket_tagging(Bucket=inv["bucket"], ExpectedBucketOwner=ACCOUNT,
                          Tagging={"TagSet": tags(inv["experiment_id"])})
    s3.put_bucket_lifecycle_configuration(
        Bucket=inv["bucket"], ExpectedBucketOwner=ACCOUNT,
        LifecycleConfiguration={"Rules": [{
            "ID": "experiment-artifact-retention", "Status": "Enabled", "Filter": {"Prefix": ""},
            "Expiration": {"Days": 30},
            "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
        }]},
    )
    if not inv.get("role_created"):
        iam.create_role(RoleName=inv["role_name"], AssumeRolePolicyDocument=json.dumps(trust),
                        Tags=tags(inv["experiment_id"]), MaxSessionDuration=3600)
        inv["role_created"] = True
        write_json(inventory_path, inv)
    actual_tags = {t["Key"]: t["Value"] for t in iam.list_role_tags(RoleName=inv["role_name"])["Tags"]}
    if actual_tags.get("ExperimentId") != inv["experiment_id"]:
        raise ValueError("Role ownership mismatch")
    iam.put_role_policy(RoleName=inv["role_name"], PolicyName="ExperimentOnly",
                        PolicyDocument=json.dumps(permissions))
    upload_files = [
        (bundle, "code/source.tar.gz"),
        (PACKAGE / "launch/execution_bootstrap.py", "code/bootstrap.py"),
    ]
    for file in sorted(args.dataset_dir.iterdir()):
        if file.name in {"train.jsonl", "validation.jsonl", "test.jsonl",
                         "execution-manifest.json", "dataset-manifest.json"}:
            upload_files.append((file, "dataset/" + file.name))
    if not all(any(path.name == name for path, _ in upload_files)
               for name in ("train.jsonl", "validation.jsonl", "test.jsonl")):
        raise ValueError("Missing dataset split")
    uploaded = []
    for path, suffix in upload_files:
        key = inv["experiment_id"] + "/" + suffix
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        s3.upload_file(str(path), inv["bucket"], key,
                       ExtraArgs={"ServerSideEncryption": "AES256", "ExpectedBucketOwner": ACCOUNT,
                                  "Metadata": {"sha256": digest}})
        remote = hash_s3_body(s3.get_object(
            Bucket=inv["bucket"], Key=key, ExpectedBucketOwner=ACCOUNT,
        )["Body"])
        if remote != digest:
            raise ValueError("Uploaded input checksum mismatch")
        uploaded.append({"key": key, "sha256": digest, "bytes": path.stat().st_size})
    inv.update(state="ready", uploaded=uploaded)
    write_json(inventory_path, inv)
    print(json.dumps({"state": "ready", "experiment": inv["experiment_id"],
                      "uploaded_files": len(uploaded)}))


def refresh(inv, sm):
    for job in inv["jobs"]:
        if job.get("status") in TERMINAL:
            continue
        # Not-found and communication errors intentionally remain unresolved.
        result = sm.describe_training_job(TrainingJobName=job["name"])
        job["status"] = result["TrainingJobStatus"]
        job["description"] = {
            key: result.get(key) for key in (
                "SecondaryStatus", "FailureReason", "TrainingTimeInSeconds",
                "BillableTimeInSeconds", "TrainingStartTime", "TrainingEndTime",
                "ModelArtifacts", "CreationTime", "SecondaryStatusTransitions",
            )
        }


def submit(args, cfg):
    inventory_path = args.evidence / "inventory.json"
    inv = read_json(inventory_path)
    if inv.get("state") != "ready":
        raise ValueError("Provisioning is not ready")
    if hashlib.sha256(args.config.read_bytes()).hexdigest() != inv["config_sha256"]:
        raise ValueError("Configuration changed after source upload")
    check_runtime(cfg)
    cloud, client_cfg = session()
    sm = cloud.client("sagemaker", config=client_cfg)
    refresh(inv, sm)
    write_json(inventory_path, inv)
    assert_no_active_jobs(inv["jobs"])
    validate_stage(args.mode, inv["jobs"])
    reserve = check_budget(cfg, inv["jobs"], args.seconds)
    name = f"{inv['experiment_id']}-{args.mode}-{len(inv['jobs']) + 1:02d}"
    request = build_request(cfg, inv, args.mode, name, args.seconds, args.steps, inv["source_sha256"])
    write_json(args.evidence / (name + "-request.json"), request)
    if not args.execute:
        print(json.dumps({"state": "preview", "job": name, "reserved_usd": str(reserve)}))
        return
    # Persist intent BEFORE the API call. SDK retries retain this exact name;
    # ambiguous responses never authorize another application submission.
    job = {"name": name, "mode": args.mode, "status": "Submitting",
           "reserved_usd": str(reserve), "max_runtime_seconds": args.seconds,
           "steps": args.steps, "source_sha256": inv["source_sha256"]}
    inv["jobs"].append(job)
    write_json(inventory_path, inv)
    sm.create_training_job(**request)
    job["status"] = "InProgress"
    write_json(inventory_path, inv)
    print(json.dumps({"job": name, "status": job["status"], "reserved_usd": str(reserve)}))


def status(args, cfg):
    inv = read_json(args.evidence / "inventory.json")
    cloud, client_cfg = session()
    refresh(inv, cloud.client("sagemaker", config=client_cfg))
    write_json(args.evidence / "inventory.json", inv)
    print(json.dumps(inv["jobs"], indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "submit", "status"))
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=PACKAGE / "config/execution-20260916.json")
    parser.add_argument("--dataset-dir", type=Path)
    parser.add_argument("--mode", choices=("smoke", "full"), default="smoke")
    parser.add_argument("--seconds", type=int, default=3600)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    validate_evidence(args.evidence)
    with locked(args.evidence):
        {"prepare": provision, "submit": submit, "status": status}[args.action](
            args, read_json(args.config))


if __name__ == "__main__":
    main()

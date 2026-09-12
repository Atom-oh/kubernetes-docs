# Part 3: SageMaker AI and MLflow Execution

> **Documentation Reviewed**: September 12, 2026

## Execution Notice

**The committed GPU execution path is currently blocked because its image reached end of patch.** The official catalog gives `2026-08-06` as the patch end for `2.8.0-gpu-py312-cu129-ubuntu22.04-sagemaker`. `src/runtime_contract.py` checks this boundary before preflight, provisioning, Training Job submission, EKS creation, and training. Update the image, `torch`, and dependency cohort together and validate a GPU smoke run; removing the date check alone is not a runtime upgrade.

This chapter describes the corrected contract in `examples/ai-ml/qwen-pii-finetuning/`. Local tests, request previews, and owned-resource cleanup remain available. The September 1, 2026 AWS experiment **stopped before training submission**. This review also performed no AWS resource creation or GPU training.

AWS recommends **MLflow Apps** for new SageMaker managed MLflow deployments. Existing Tracking Servers are a separate resource. Current App documentation lists MLflow `3.10`; this historical example pins its client and EKS server to `3.1.4`. A successful local 3.1.4 artifact export does not validate full compatibility with the managed App. Include that pairing in the runtime upgrade validation.

## Eight Steps on the Managed Path

### 1. Read-Only Preflight

Run these commands with the **Python 3.12 virtual environment activated** and the package README's dependencies installed.

```bash
cd examples/ai-ml/qwen-pii-finetuning
export AWS_REGION=ap-northeast-2
python3 src/runtime_contract.py --check-execution
```

Today this command should fail with the end-of-patch explanation. After upgrading the example to a supported runtime, set administrator-verified `EXPECTED_ACCOUNT_ID`, `DATAZONE_DOMAIN_ID`, `DATAZONE_PROJECT_PROFILE_ID`, and `DATAZONE_OWNER_GROUP_ID`, then run `./launch/aws/preflight.sh`. These variables contain resource identifiers, not passwords or service-account keys.

Preflight checks tools, caller, Region, quotas, DLC, and existing experiment collisions. It does not reconstruct a domain, profile, or group from a display name or STS role string. An empty list proves neither universal absence nor permission for later creation. Review ownership of resources sharing a prefix; do not delete them indiscriminately.

### 2. Build the Source Bundle

```bash
./launch/aws/build_source_bundle.sh
```

The bundle includes `src/*.py`, `config/experiment.yaml`, `requirements.lock`, and an identical `requirements.txt`. It does not recursively package data or local credential files. It does not detect sensitive values embedded directly in source or configuration, so inspect the bundle. Its SHA-256 identifies **that build**; tar timestamps are not guaranteed reproducible.

### 3. Create the MLflow App and Unified Studio Project

This is an **AWS mutation and billable-resource step**, available only after runtime and permission validation.

```bash
./launch/aws/provision.sh
```

It creates an experiment bucket, execution and MLflow roles, an MLflow App, and a project with owner membership. The bucket uses Block Public Access, AES-256, and versioning; IAM policies are checked with Access Analyzer. App readiness is `Created`/`Updated`. Project `ACTIVE` does not establish successful deployment of every project environment.

The private inventory distinguishes creation intent from successful responses. A name collision or lost response does not authorize deletion by name. Error cleanup operates on confirmed ownership; unknown creation requires reconciliation. A forcibly stopped process or instance may never execute a shell trap.

### 4. Upload the Dataset

Create the bucket and inventory before uploading. Validate the five inputs:

```bash
python3 -m launch.aws.upload_inputs \
  --inventory results/resource-inventory.json
# Actual S3 upload and SHA-256 readback verification:
python3 -m launch.aws.upload_inputs \
  --inventory results/resource-inventory.json --execute
```

Inputs are `generated/source.tar.gz`, `data/{train,validation,test}.jsonl`, and `data/dataset-manifest.json`. The helper checks split hashes, bucket account ownership, and experiment tags, then writes the execution-specific `qwen-pii/<experiment-id>/source/` and `dataset/` prefixes. It reads objects back to compare SHA-256. This small synthetic example limits each file to 64 MiB. A failed upload may leave some objects, so preserve the inventory.

Use identifiers and hashes in private operational records. Presigned URLs carry access authority and must not be posted in public documentation or logs.

### 5. Submit the SageMaker Training Job Request

```bash
python3 -m launch.sagemaker_train \
  --mode smoke --inventory results/resource-inventory.json
```

By default this writes a uniquely named JSON file under `results/previews/` without submitting to AWS. It does not overwrite the submitted `<job-name>-request.json` or `<job-name>-job.json`. After validating a supported runtime, add `--execute` to submit. Full execution separately requires `--mode full --execute`. The launcher does not automatically approve smoke evidence or input hashes.

The config is read from `/opt/ml/code/config/experiment.yaml` in the source bundle. The four data files live in `/opt/ml/input/data/dataset/`. Build the local `--config` and bundle from the same source so they agree.

Before submission, the launcher reserves both request and job journal under the cleanup tool's shared lock. For a job whose creation succeeded, monitor failure or interruption triggers a stop request attempt. `stop_requested` does not mean termination is confirmed. Reconcile AWS state and ownership after `submission_unknown`, `stop_unconfirmed`, or host loss; do not overwrite an existing journal or orphan request to resubmit.

The historical config specifies one `ml.g6e.4xlarge`, 300 GiB, smoke 10/full 80 steps, and `MaxRuntimeInSeconds: 10800`. That limit does not cap total cost including termination, uploads, MLflow, S3, and other resources.

### 6. Smoke/Full Gate

Before re-enabling execution, validate the supported image, dependencies, and MLflow pairing. Then inspect smoke terminal status, dataset hashes, metrics, and adapter files. Review logs and MLflow for source text, entity values, mappings, or raw completions. **An artifact filename allowlist does not prove safe contents.** This procedure does not imply an automated PII scanner has been implemented.

### 7. Export Aggregate Results

| File | Meaning |
|---|---|
| `dataset-manifest.json` | generator settings, counts, split hashes |
| `resolved-config.json` | actual settings, environment, steps |
| `dependency-versions.json` | observed installed versions; not a complete lock guarantee |
| `baseline-metrics.json`, `tuned-metrics.json` | aggregate evaluation on the same test split |
| `run-summary.json` | phase timings, metrics, adapter inventory |
| `adapter/adapter_config.json`, `adapter/adapter_model.safetensors` | final adapters preserved in MLflow |

SageMaker `/opt/ml/model` output and MLflow artifacts have different storage locations. Download and verify required results before deleting the bucket or App. Review adapter contents and access permissions before sharing them. Raw predictions, token mappings, and all intermediate checkpoints are not exported.

`peak_gpu_memory_bytes` is the default CUDA device's PyTorch allocated-memory peak after a reset following model loading. It is not total GPU memory, load-time peak, or a sum across devices. No training results exist to justify publishing performance gains or a cost comparison.

### 8. Teardown and Verification

```bash
./launch/aws/teardown.sh
./launch/aws/verify_cleanup.sh
```

Check and stop recorded training jobs first. When training records exist, teardown stops again to prevent deleting their artifact bucket before export. Only after separately preserving required SageMaker/MLflow artifacts should you proceed with:

```bash
./launch/aws/teardown.sh results/resource-inventory.json \
  --discard-training-artifacts
```

This flag does not perform a backup. Shared teardown also stops while owned EKS resources remain. Complete verified export/deletion through the EKS path or the manual recovery below first. It then cleans up confirmed-owned App, project, S3, and IAM resources. AWS `AccessDenied`, transport failures, deletion timeouts, and per-object S3 errors must not count as absence. Old inventories without ownership evidence require administrator reconciliation. This tool does not delete the shared TrainingJobs log group or unrelated resources.

Remaining or unknown states fail verification. Success is scoped to the queried account, Region, inventory, and checks; it does not prove an empty AWS account. Incomplete cleanup or a retained cluster can continue incurring charges.

## EKS + MLflow Comparison Path

After the runtime upgrade, entry points are `./launch/eks/run.sh smoke` and, after separate review, `./launch/eks/run.sh full`. Today they stop at the end-of-patch guard.

| Item | Example contract and limitation |
|---|---|
| Cluster | template EKS `1.36`, one `g6e.4xlarge`; recheck regional availability and support |
| GPU plugin | `0.20.0` pin; validate with the new DLC, AMI, and driver |
| kubeconfig | per-run file and explicit context; reject preexisting cluster collisions |
| MLflow | ClusterIP, SQLite, `emptyDir`; no application authentication, durable storage, or tenant isolation |
| Data | S3 SDK with ServiceAccount-scoped AWS permissions; verify manifest SHA-256 and bucket account |
| Job | `backoffLimit: 0`, `activeDeadlineSeconds: 10800`; not guaranteed reclamation of all resources within three hours during failures |
| Export | verify eight artifacts and SHA-256 from a completed run matching the experiment, cluster, and execution IDs |
| Shutdown | clean up the owned cluster after export/hash verification; an export failure can retain it for recovery |

The input loader reads code and upload hashes from a ConfigMap, then uses EKS Pod Identity to download only five S3 objects. The ServiceAccount is `qwen-input-reader`; the Pod Identity Agent, supported SDK, and association are required. EC2 instance metadata credential fallback is disabled. This does not remove the expired-DLC execution gate.

Training and MLflow Pod `emptyDir` data disappears with Pod or cluster deletion. The per-run `results/eks-<mode>.<suffix>/mlflow-export-<mode>.tar.gz` and export receipt are local files, not an off-host backup. Copy them to separate approved storage and verify cleanup.

A failed training run with no completed run/export cannot meet the automatic deletion condition. Reconcile the private inventory's account, cluster ARN, creation time, ownership tags, and stack IDs with AWS; recover or explicitly discard required results, then delete **that owned cluster only** with `eksctl delete cluster --name ... --region ... --wait`. Partial creation or lost responses also require manual reconciliation. Run `verify_cleanup.sh` afterward and investigate resources retained by stack deletion. Do not fabricate ownership flags to bypass verification.

## Observed Errors and Stop Conditions

| Condition | Handling |
|---|---|
| DLC reached end of patch | block creation/training; upgrade the runtime cohort |
| wrong config path | read config from the source bundle |
| name collision or lost creation response | refuse automatic deletion without ownership |
| missing or failed export | do not declare success before verifying adapters and aggregate files |
| query authorization error or deletion timeout | record unknown/failure |
| historical project membership omission | reconcile with domain administrator and project owner |

## Choosing a Path

SageMaker reduces Training Job and MLflow operational work, while artifact retention, permissions, and experiment cleanup still require action. EKS provides Kubernetes control and adds responsibility for clusters, GPU plugins, and MLflow storage. Record configuration, data hashes, model revision, actual dependencies, and GPU environment together when comparing them.

## Primary Sources

- [AWS DLC PyTorch 2.8 catalog and patch end](https://github.com/aws/deep-learning-containers/blob/main/docs/src/data/pytorch-training/2.8-gpu-sagemaker.yml)
- [SageMaker Training Toolkit code directory](https://github.com/aws/sagemaker-training-toolkit/blob/master/src/sagemaker_training/entry_point.py)
- [MLflow App setup](https://docs.aws.amazon.com/sagemaker/latest/dg/mlflow-app-setup.html)
- [SageMaker MLflow versions](https://docs.aws.amazon.com/sagemaker/latest/dg/mlflow.html)
- [S3 presigned URL expiration](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html)
- [EKS Pod Identity behavior and restrictions](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [Kubernetes Job failure and termination](https://kubernetes.io/docs/concepts/workloads/controllers/job/)

Previous: [Part 2 — Synthetic PII data and tokenization](02-pii-data-tokenization.md)

Next: [Part 4 — Unified Studio governance](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md)

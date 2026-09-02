# Part 3: SageMaker AI and MLflow Execution

> **Last Updated**: September 2, 2026

## Execution Notice

The commands in this chapter describe committed implementation under `examples/ai-ml/qwen-pii-finetuning/`. The recorded September 1, 2026 validation nevertheless **stopped before Training Job submission**. Runnable implementation is not evidence of completed GPU training.

For new managed MLflow deployments, the path uses a **SageMaker MLflow App**, not the legacy Tracking Server resource. The App is a standalone HTTP server for tracking runs and experiments and is connected here to an S3 artifact store through a scoped IAM role.

## Eight Steps on the Managed Path

### 1. Read-Only Preflight

```bash
cd examples/ai-ml/qwen-pii-finetuning
export AWS_REGION=ap-northeast-2
./launch/aws/preflight.sh
```

Preflight checks the required tools, caller identity, Region, `ml.g6e.4xlarge` Training Job quota, EC2 GPU vCPU quota, PyTorch DLC, and collisions with existing `qwen-pii-*` Apps, clusters, buckets, IAM roles, and Unified Studio projects.

It refuses to begin when an old `results/resource-inventory.json` or experiment resource remains.

### 2. Build the Source Bundle

```bash
./launch/aws/build_source_bundle.sh
```

The bundle contains only:

- `src/*.py`
- `config/experiment.yaml`
- `requirements.lock` and an identical `requirements.txt`

Datasets, raw predictions, and local credentials are excluded.

### 3. Upload the Dataset

The inventory created by `provision.sh` records an execution-specific prefix and `source_s3_uri`. An approved CI artifact publisher uploads the bundle and four data files under this layout:

```text
qwen-pii/<experiment-id>/source/source.tar.gz
qwen-pii/<experiment-id>/dataset/train.jsonl
qwen-pii/<experiment-id>/dataset/validation.jsonl
qwen-pii/<experiment-id>/dataset/test.jsonl
qwen-pii/<experiment-id>/dataset/dataset-manifest.json
```

Compare remote object hashes with the split SHA-256 values in `data/dataset-manifest.json`. Never publish the bucket name or presigned URLs in documentation or logs.

### 4. Create the MLflow App and Unified Studio Project

```bash
./launch/aws/provision.sh
```

The script:

1. creates a temporary S3 bucket with Block Public Access, AES-256 encryption, and versioning;
2. creates the SageMaker execution and MLflow roles;
3. validates IAM policies with Access Analyzer;
4. creates the App with `create-mlflow-app`;
5. waits for `Created` or `Updated`;
6. finds an enabled `All capabilities` project profile;
7. finds the caller role's DataZone group profile and assigns `PROJECT_OWNER` membership during project creation;
8. writes every created resource to the inventory.

An error or interrupt writes the latest inventory and invokes teardown.

### 5. Submit the SageMaker Training Job Request

Smoke request:

```bash
python3 launch/sagemaker_train.py \
  --mode smoke \
  --inventory results/resource-inventory.json
```

Only after smoke completion and log-safety review:

```bash
python3 launch/sagemaker_train.py \
  --mode full \
  --inventory results/resource-inventory.json
```

Both modes use the same `ml.g6e.4xlarge`, 300 GiB volume, `10,800`-second maximum runtime, source bundle, dataset channel, and MLflow App. The intended difference is `10` versus `80` steps.

> **Recorded result**: neither Training Job command was executed during the September 1 validation.

### 6. Smoke/Full Gate

A successful smoke Job alone is insufficient. Require all of the following:

- terminal Training Job status is `Completed`;
- CloudWatch contains no source text, entity values, mappings, or raw completions;
- MLflow parameters and tags contain only non-sensitive configuration;
- aggregate metrics and dataset hashes were exported;
- the adapter inventory contains only allowed files;
- leakage and round-trip evaluation completed without errors.

### 7. Export Aggregate Results

The training entry point is designed to produce:

| File | Contents |
|---|---|
| `resolved-config.json` | resolved environment and step count |
| `dependency-versions.json` | pinned dependency versions |
| `baseline-metrics.json` | aggregate base-model evaluation |
| `tuned-metrics.json` | aggregate adapter evaluation |
| `run-summary.json` | timing, peak GPU memory, aggregate metrics, adapter inventory |

Raw prediction JSONL and token mappings are not publishable result artifacts.

### 8. Teardown and Verification

```bash
./launch/aws/teardown.sh
./launch/aws/verify_cleanup.sh
```

Inventory-driven teardown removes the MLflow App, Unified Studio project, Training Job log streams, versioned S3 objects and bucket, and IAM inline policies and roles. Verification rechecks the App, project, bucket, roles, EKS clusters, EC2 instances, and tagged resources; it fails if anything remains.

## EKS + MLflow Comparison Path

The Kubernetes entry point uses the same source and dataset:

```bash
./launch/eks/run.sh smoke
```

Only after smoke approval:

```bash
./launch/eks/run.sh full
```

| Item | Implementation |
|---|---|
| Cluster | ephemeral Amazon EKS `1.36` |
| GPU node | one `g6e.4xlarge` with encrypted 300 GiB gp3 |
| GPU plugin | NVIDIA device plugin `0.20.0` |
| MLflow | namespace-internal ClusterIP, not public |
| Data | the same S3 objects through four-hour presigned URLs |
| Job retries | `backoffLimit: 0` |
| Deadline | `activeDeadlineSeconds: 10800` |
| Export | build aggregate JSON inside the MLflow Pod, then `kubectl cp` |
| Shutdown | a shell trap deletes the cluster on success, failure, or interrupt |

The EKS path must also keep source text and raw completions out of stdout. The `run.sh` log tail assumes the training code emits only safety-reviewed aggregate logs.

> **Recorded result**: the EKS GPU cluster and Job were also not executed during the September 1 validation.

## Observed Errors and Stop Conditions

| Condition | Observation or Guard | Handling |
|---|---|---|
| MLflow App status | `Created`/`Updated` are ready; `Deleted` is terminal | do not wait for a nonexistent App `ACTIVE` status |
| custom project tags | a domain can reject custom resource tags | remove prohibited project tags |
| project membership | a caller without membership cannot manage the project | assign the role group profile as `PROJECT_OWNER` at creation |
| Service Quotas throttling | repeated queries can be throttled | adaptive retry with bounded attempts |
| partial creation failure | an error can occur after some resources exist | update inventory at each stage and trap teardown |
| remaining project | deletion is impossible without owner authorization | stop before GPU creation and require domain-owner action |

## Choosing a Path

- Choose SageMaker AI when you want managed Training Job and current managed MLflow App lifecycles.
- Choose EKS when Kubernetes policy, scheduling, and shared observability outweigh direct cluster and MLflow operations.
- For a comparison, freeze configuration and dataset hashes and vary only the execution environment.

Previous: [Part 2 — Synthetic PII data and tokenization](02-pii-data-tokenization.md)

Next: [Part 4 — Unified Studio governance](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md)

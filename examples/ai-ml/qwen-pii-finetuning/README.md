# Qwen PII Fine-Tuning Experiment

This package defines the same QLoRA experiment for two execution paths:

1. Amazon SageMaker AI Training with SageMaker managed MLflow.
2. An ephemeral Amazon EKS GPU Job with MLflow running inside the cluster.

The model learns to emit one `TYPE<TAB>ORIGINAL` PII entity per line.
Deterministic Python code performs replacement with tokens such as
`[PERSON_1]` and `[PHONE_1]`; the model does not generate the final masked
document.
Replacement and round-trip tests do not prove complete PII detection or
anonymity. Neither GPU execution path completed in the recorded AWS validation.

**Resource creation and GPU execution are currently blocked.** The pinned
PyTorch 2.8 SageMaker DLC reached end of patch on **2026-08-06** according to
the upstream `aws/deep-learning-containers` image catalog. Upgrade the DLC,
torch/dependencies, and MLflow pairing together and validate GPU smoke behavior
before re-enabling execution. Do not remove the support check alone.

## Safety and reproducibility

- The dataset is fully synthetic and generated with seed `42`.
- The package contains no model weights or real PII.
- Source text, extracted values, mappings, and raw model completions must not
  be written to stdout, CloudWatch, or MLflow parameters and tags.
- Both paths use `requirements.lock` and `config/experiment.yaml`. These are
  direct dependency pins; the model/tokenizer revision, image digest,
  transitive environment and GPU runtime also need pinning/verification.
- Apply the experiment tags where supported and permitted by policy.
  Unified Studio project tags were rejected in a historical attempt.
- Track private resource identifiers and ownership in inventory. Export results,
  clean up only owned experiment resources, and verify completion; cleanup
  previously left one project and must not be described as universally successful.

## Local contract test

Run from this package directory with Python 3.12:

```bash
QWEN_TEST_ENV="${XDG_CACHE_HOME:-$HOME/.cache}/qwen-pii-contract"
python3.12 -m venv "$QWEN_TEST_ENV"
"$QWEN_TEST_ENV/bin/python" -m pip install pytest==8.4.2 PyYAML==6.0.3 boto3==1.42.97
"$QWEN_TEST_ENV/bin/python" -m pytest tests -q --basetemp "$QWEN_TEST_ENV/test-output"
```

The September 12, 2026 review reran the original 30 tests and added regression
coverage for tokenization, metrics, submission, export, and lifecycle failures.
It did not load model weights, run GPU training, or call AWS services.

Build the bundle locally with `./launch/aws/build_source_bundle.sh`. With a
private inventory, `python3 -m launch.sagemaker_train --mode smoke --inventory
results/resource-inventory.json` writes a unique preview under `results/previews/`.
It never replaces request/journal evidence for a submitted job. Actual submission
requires `--execute` and a supported runtime.

Provisioning requires explicit administrator-verified `EXPECTED_ACCOUNT_ID`, `DATAZONE_DOMAIN_ID`,
`DATAZONE_PROJECT_PROFILE_ID`, and `DATAZONE_OWNER_GROUP_ID`. Create the
bucket/inventory before running `python3 -m launch.aws.upload_inputs --inventory
results/resource-inventory.json --execute`. The upload helper checks split
hashes, bucket ownership tags, and remote SHA-256 readback.

Preserve submission journals and the ownership inventory across interruptions.
Cleanup is not guaranteed by shell traps; query errors remain unknown and
old inventories without ownership evidence require manual reconciliation.
EKS exports aggregate artifacts and final adapters before cluster deletion.
An export failure can retain the cluster for recovery, with continuing charges.
EKS input downloads use ServiceAccount-scoped AWS permissions and verify the
five uploaded inputs against their manifest hashes and expected bucket account.
Export metadata must match the inventory's experiment, cluster, and execution
identifiers before it can authorize cleanup.
Shared teardown refuses remaining EKS resources. After preserving SageMaker
results, use `./launch/aws/teardown.sh results/resource-inventory.json
--discard-training-artifacts` to acknowledge removal of the experiment bucket.
This flag does not make a backup.

Generated datasets and raw predictions are runtime artifacts. Only aggregate
metrics, hashes, non-sensitive plots, and teardown evidence are committed.

## Validation result

The AWS validation performed on September 1, 2026 stopped before GPU training
because the created SageMaker Unified Studio project did not grant the caller
project membership. The factual result, cleanup status, and remaining owner
action are recorded in the repository-internal report at
`docs/superpowers/reports/2026-09-01-sagemaker-qwen-pii-validation.md`.
That record is historical; verify current project ownership and residual
resources before resuming the experiment.

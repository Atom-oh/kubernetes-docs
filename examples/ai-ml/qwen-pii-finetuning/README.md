# Qwen PII Fine-Tuning Experiment

This package runs the same QLoRA experiment through two execution paths:

1. Amazon SageMaker AI Training with SageMaker managed MLflow.
2. An ephemeral Amazon EKS GPU Job with MLflow running inside the cluster.

The model learns to emit one `TYPE<TAB>ORIGINAL` PII entity per line.
Deterministic Python code performs replacement with tokens such as
`[PERSON_1]` and `[PHONE_1]`; the model does not generate the final masked
document.

## Safety and reproducibility

- The dataset is fully synthetic and generated with seed `42`.
- The package contains no model weights or real PII.
- Source text, extracted values, mappings, and raw model completions must not
  be written to stdout, CloudWatch, or MLflow parameters and tags.
- Both paths use the dependency versions in `requirements.lock` and the
  configuration in `config/experiment.yaml`.
- Every AWS resource uses the tags
  `Experiment=qwen-pii-finetuning` and an execution-specific `ExperimentId`.
- All experiment-specific AWS resources are deleted after result export.

## Local contract test

```bash
python3 -m venv /tmp/qwen-pii-plan-venv
/tmp/qwen-pii-plan-venv/bin/pip install pytest==8.4.2 PyYAML==6.0.3
/tmp/qwen-pii-plan-venv/bin/pytest tests/test_config_parity.py -q
```

Generated datasets and raw predictions are runtime artifacts. Only aggregate
metrics, hashes, non-sensitive plots, and teardown evidence are committed.

## Validation result

The AWS validation performed on September 1, 2026 stopped before GPU training
because the created SageMaker Unified Studio project did not grant the caller
project membership. The factual result, cleanup status, and remaining owner
action are recorded in the repository-internal report at
`docs/superpowers/reports/2026-09-01-sagemaker-qwen-pii-validation.md`.

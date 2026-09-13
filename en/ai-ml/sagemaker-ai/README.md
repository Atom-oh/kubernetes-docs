# Fine-Tuning Qwen for PII with SageMaker AI

> Documentation reviewed: 2026-09-12. AWS provisioning outcomes refer to the historical 2026-09-01 experiment.

This guide describes a QLoRA experiment design and component-tested package for
Qwen/Qwen3-30B-A3B-Instruct-2507. Managed SageMaker Training Jobs and ephemeral EKS
GPU Jobs are configured to share source, synthetic data and evaluation code.
**It is not evidence of successful end-to-end GPU training on either path.**

The pinned PyTorch 2.8 DLC reached end of patch on 2026-08-06, so **resource creation and GPU execution are blocked**. Upgrade the image/dependency cohort; the [execution chapter](03-sagemaker-mlflow-execution.md) explains local checks and resumption requirements.

The model emits `TYPE<TAB>ORIGINAL` candidates; Python code validates, replaces and
restores them. Deterministic replacement or successful round trips do not guarantee
complete PII detection, masking or anonymity. Evaluate missed and misclassified
entities separately.

## Five-part learning path

| Part | Topic |
| --- | --- |
| [1](01-platform-architecture.md) | Platform responsibilities and target architecture |
| [2](02-pii-data-tokenization.md) | Synthetic data, replacement and evaluation limits |
| [3](03-sagemaker-mlflow-execution.md) | SageMaker/EKS execution contracts and MLflow |
| [4](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md) | Unified Studio domains/projects/membership |
| [5](04-validation-results.md) | What ran and what was not measured |

## Validation record

| Evidence | Scope |
| --- | --- |
| 2026-09-12 local recheck | Initial 30 tests followed by added tokenization, evaluation, execution, and cleanup regressions; no GPU or AWS API execution |
| 2026-09-01 AWS record | Quotas, MLflow App and project-provisioning failure paths |
| Unexecuted in that record | SageMaker Training Job / EKS GPU Job |
| Historical cleanup | Experiment App/S3/IAM resources reclaimed; one Unified Studio project remained |

The current AWS account was not queried, so this does not assert that the project
still exists. Verify current ownership/inventory before resuming. Fine-tuned F1,
GPU peak memory, training duration and cost are not reported as measured results.

## Experiment policy and limits

- Use seed-42 synthetic data and record split hashes.
- Design ordinary logs/MLflow to exclude source text, extracted values, mappings
  and raw completions. Validate autologging/tracing and artifact contents during actual execution.
- Private inventory can retain resource IDs/ARNs needed for cleanup; public reports summarize them.
  Treat presigned URLs as temporary access credentials.
- Base smoke/full progression on reviewed execution results and limit cleanup to this run's owned resources.
- Model IDs, seeds and direct dependency pins do not ensure complete reproducibility
  or equivalent security across environments.

Example package: `examples/ai-ml/qwen-pii-finetuning/`.

## References

- [Qwen model card](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)
- [QLoRA paper](https://arxiv.org/abs/2305.14314)
- [Experiment configuration](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/config/experiment.yaml)
- [Recorded provisioning result](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)

# Fine-tuning Qwen for PII with SageMaker AI

> **Last Updated**: September 15, 2026

Includes synthetic-data CPU exercises and QLoRA instruction. AWS provisioning observations are historical records from September 1, 2026.

This guide teaches how to train and evaluate a model that extracts PII candidates from documents. Define the annotation contract, split and augment data without leakage, choose QLoRA settings, and measure both omissions and excessive masking.

The model emits `TYPE<TAB>ORIGINAL` candidates. Python code validates and replaces them; the model does not rewrite the entire document. This separation helps distinguish detection errors from replacement bugs.

## Start with the practical learning path

| Order | Chapter | What you should be able to explain afterward |
| --- | --- | --- |
| 1 | [Synthetic data and augmentation](06-data-augmentation-workshop.md) | Annotation contracts, family separation, train-only augmentation, source/label audits |
| 2 | [QLoRA training and the SageMaker workflow](05-qlora-finetuning-workshop.md) | NF4, LoRA, loss masks, actual target modules, batch/step budgets, tuning and diagnosis |
| 3 | [PII evaluation and redaction pipelines](07-pii-evaluation-release.md) | Recall/F1, residual PII, masking on negative documents, final evaluation and acceptance |
| 4 | [SageMaker AI and MLflow execution contracts](03-sagemaker-mlflow-execution.md) | Source bundles, S3 channels, Training Jobs, artifacts, and cleanup |

Start with data and evaluation if you can use Python 3.12 and JSONL. Neither CPU exercise needs an AWS account or model weights. The training walkthrough and GPU-check procedure are distinct from evidence of completed GPU training.

The new augmentation exercise splits 40 synthetic families before augmenting training only. Its separate dataset does not overwrite the historical generator 1.0.0 corpus of 2,200 records. Tiny exercise or oracle scores are not real-world model-performance claims.

## SageMaker execution readiness

The historical package proposes Qwen/Qwen3-30B-A3B-Instruct-2507 training through a managed SageMaker Training Job or an ephemeral EKS GPU Job. Neither GPU path has a recorded end-to-end success.

The pinned PyTorch 2.8 DLC ended patch support on 2026-08-06, so resource creation and GPU execution are blocked. Follow the [QLoRA runtime discussion](05-qlora-finetuning-workshop.md) and [execution contract](03-sagemaker-mlflow-execution.md) to validate the image, dependencies, and MLflow pairing together. Removing only the support check is not a migration procedure.

## Read the design and implementation in depth

| Document | Purpose |
| --- | --- |
| [Part 1: platform architecture](01-platform-architecture.md) | Responsibilities of model, data, Python processing, and MLflow |
| [Part 2: data and deterministic tokenization](02-pii-data-tokenization.md) | Historical nine-type data, replacement spans, and exact metric definitions |
| [Part 3: execution](03-sagemaker-mlflow-execution.md) | SageMaker/EKS submission, persistence, recovery, and cleanup |
| [Part 4: Unified Studio governance](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md) | Domain/project/membership |
| [Part 5: factual validation records](04-validation-results.md) | Executed work, unexecuted work, and historical residual resources |

## Interpreting the validation records

- New data/evaluation commands are checked on CPU with synthetic inputs. Trained-model F1, GPU peak memory, and training duration require separate measurements.
- The 2026-09-12 review added local regression coverage for tokenization, evaluation, execution, and cleanup.
- The 2026-09-01 AWS record covers quotas and MLflow App/project provisioning failure paths; it stopped before GPU submission.
- That record cleaned experiment App/S3/IAM resources but left one Unified Studio project. A fresh inventory is needed to establish its current state.

Do not send sources, extracted values, token mappings, or raw completions to general logs or MLflow parameters/tags. Check autolog/tracing and artifact contents in the execution environment too. Reversible mappings, trained adapters, and private resource inventories are different artifacts with separate retention/access requirements.

Example package: `examples/ai-ml/qwen-pii-finetuning/`. Each workshop provides its exact CLI and output example.

## References

- [Qwen model card](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)
- [QLoRA paper](https://arxiv.org/abs/2305.14314)
- [Experiment configuration](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/config/experiment.yaml)
- [Historical provisioning result](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)

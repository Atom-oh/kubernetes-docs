# Part 1: SageMaker Qwen PII Platform Architecture

> Reviewed: 2026-09-12. The diagram is a target design; neither GPU training path executed in the historical AWS record.

GPU execution is blocked because the pinned PyTorch 2.8 DLC reached end of patch. First follow the supported-runtime upgrade requirements in the [execution chapter](03-sagemaker-mlflow-execution.md).

![Target design: managed and EKS execution, candidate extraction, deterministic processing, aggregate tracking and owned-resource cleanup.](../../.gitbook/assets/en-ai-ml-sagemaker-ai-01-platform-architecture-0.png)

[Interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-sagemaker-ai-01-platform-architecture-0.html)

## 1. Responsibility and recording boundaries

| Component | Responsibility and limit |
| --- | --- |
| Synthetic generator | Configured 1,600/200/400 splits, 2,200 records; track generator, seed and hashes |
| S3 / data delivery | Store source/data/artifacts; separately manage IAM, encryption, retention and transport |
| Qwen + QLoRA | Adapter-training design for entity candidates; final replacement and complete detection are separate concerns |
| Python processing/evaluation | Type/source checks, replacement/restoration and aggregates; it does not automatically recover entities the model missed |
| MLflow | Compare configurations, versions and aggregates; verify server access and log/artifact contents |
| Unified Studio | This experiment's governance choice, not a mandatory dependency of QLoRA, EKS or Training Jobs |
| Inventory / teardown | Privately record identifiers, ownership and dependencies; export, clean up and verify |

Control artifacts containing source text or token mappings. Replacement is reversible
with its mapping and is not encryption. Logging policy is a design/contract, not
proof that every library, callback, exception and automatic trace was tested.
Resource IDs/ARNs can be necessary in private inventory, distinct from public reports.

## 2. A shared contract in different environments

| Aspect | SageMaker AI path | EKS path |
| --- | --- | --- |
| Execution | Managed Training Job | GPU Job/cluster prepared for this experiment |
| Tracking | SageMaker MLflow App | ClusterIP MLflow |
| Data | S3 input channel | Expiring presigned URLs used by the example launcher |
| Lifecycle | Distinguish job termination from cleanup of external Apps/buckets | Export results, then reclaim owned temporary resources |

A Training Job or namespace/Job boundary does not automatically complete security
isolation. Verify actual IAM/service accounts, networking, storage, endpoint/MLflow
access and container configuration. EKS can also use IRSA/Pod Identity; presigned
URLs are this example's choice and require expiry/retry/exposure handling.

Comparison requires configuration, split hashes, training/evaluation code and
step counts, plus model/tokenizer revisions, image digests, transitive dependencies,
CUDA/drivers/hardware and decoding settings. A fixed seed does not guarantee identical
GPU results across environments. requirements.lock pins direct packages, not the
entire transitive environment.

## 3. Model and proposed QLoRA settings

The baseline is Qwen/Qwen3-30B-A3B-Instruct-2507. Its model card describes a
**30.5B-total / 3.3B-active-parameter** MoE with non-thinking behavior.
Active parameters do not represent all stored weights or required GPU memory.
This is not presented as the latest model or as proven to fit a particular GPU.

The model repository revision observed during review was `0d7cf23991f47feeb3a57ecb4c9cee8ea4a17bfe`.
The current loader/config uses the model ID without explicitly pinning that revision.
Pin model/tokenizer revisions and artifacts before claiming reproducible execution.

| Setting | Proposed configuration |
| --- | --- |
| Quantization / compute | 4-bit NF4, double quantization / bfloat16 |
| LoRA rank / alpha / dropout | 16 / 32 / 0.05 |
| Sequence length | 1,024 |
| Device batch / gradient accumulation | 1 / 8 |
| Smoke / full | 10 / 80 steps |
| Job runtime setting | 10,800 seconds |

These are not measurements of successful training, sufficient quality or GPU peak
memory. A job deadline is not an end-to-end provisioning/tracking/storage lifetime
or cost cap. QLoRA uses low-precision base weights and trains adapters; verify actual
module coverage, optimizers, memory and model compatibility during execution.

## 4. Governance and execution readiness

This experiment checks intended domain/profile, caller membership and MLflow access
before GPU submission. CreateProject membershipAssignments can carry ownership in
the same request but do not guarantee atomic rollback of all provisioning.
Project ACTIVE and required tool/environment readiness must also be checked separately.

As historical attempts show, resources such as an App can exist before a project
failure. Combine permission prechecks with post-creation inventory and compensation.
Limit cleanup to this run's owned resources and do not infer current leftovers from
old records. Follow the [Unified Studio chapter](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md)
for identity and deletion boundaries.

## Validation scope

Configuration, trainer source, the public model card and historical reports were
compared. The initial 30 local tests were followed by added tokenization, execution, and cleanup regression coverage.
No model weights were downloaded; no GPU training, inference-quality evaluation or
current AWS resource inspection was performed.

## References

- [Qwen model card](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)
- [QLoRA paper](https://arxiv.org/abs/2305.14314)
- [Experiment configuration](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/config/experiment.yaml)
- [Recorded provisioning result](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)

[Next: PII data and tokenization](02-pii-data-tokenization.md)

[Quiz](../../quizzes/ai-ml/sagemaker-ai/01-platform-architecture-quiz.md)

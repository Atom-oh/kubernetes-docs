# Part 5: Factual SageMaker Qwen PII Validation Results

> **Documentation Reviewed**: September 12, 2026
> **AWS Validation Date**: September 1, 2026
> **Historical Status**: blocked before GPU training; residual-resource record dated September 2

## Conclusion

This chapter describes the repository's **September 1–2, 2026 experiment records**. It preserves the local checks, AWS provisioning attempts, and partial cleanup observed then; it is not a fresh account-state query. The September 12 source review found additional tokenization, evaluation, execution, and cleanup defects that the original 30 tests did not catch.

The third provisioning attempt omitted project membership, leaving the caller unable to delete the created project. Further resource creation stopped, so **neither the SageMaker Training Job nor the EKS GPU Job was executed**.

## Verified Facts

| Item | Result |
|---|---|
| Base model | `Qwen/Qwen3-30B-A3B-Instruct-2507` |
| Synthetic records | 2,200 |
| Train / Validation / Test | 1,600 / 200 / 400 |
| Korean / English | 80% / 20% |
| Historical Python contract and regression tests | 30 passed; not evidence of GPU execution or absence of all defects |
| Extraction contract | `TYPE<TAB>ORIGINAL` |
| Observed SageMaker MLflow App version | `3.10.1` |
| SageMaker training executed | `false` |
| EKS training executed | `false` |
| Remaining project on September 2, 2026 | 1, `ACTIVE` |

## Actual Execution Trace

The figure shows the **local checks, AWS preflight, three provisioning attempts, cleanup, and stop point** in the stored records. It terminates before GPU training. No GPU execution does not imply zero total experiment cost.

![Actual validation workflow showing local validation, three SageMaker and Unified Studio provisioning attempts, partial cleanup, one ACTIVE project, and GPU training not executed.](../../.gitbook/assets/en-ai-ml-sagemaker-ai-04-validation-results-0.png)

[🔍 View the interactive validation workflow](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-sagemaker-ai-04-validation-results-0.html)

## Three Provisioning Attempts

| Attempt | Actual Outcome | GPU Training | Cleanup |
|---|---|---|---|
| 1 | the MLflow App reached `Created`, but the initial script waited for a nonexistent App `ACTIVE` state | not started | App, S3, and IAM reclaimed; 0 remaining |
| 2 | the Unified Studio domain rejected custom project resource tags | not started | App, S3, and IAM reclaimed; 0 remaining |
| 3 | the project was created without project membership for the caller role group profile | not started | App, S3, and IAM reclaimed; 1 project remaining |

## Corrections Applied

The historical report recorded changes to App readiness, project-tag handling, owner membership, and retries. That statement does not prove the current automation is complete.

The September 12 follow-up found possible deletion of preexisting resources, permission errors treated as absence, a wrong config path, lost EKS adapters, and interruption gaps. Follow the corrected execution and export procedure in the [execution chapter](03-sagemaker-mlflow-execution.md). The new checks use local fixtures and mocked APIs; they are not an AWS rerun.

Absence from `ListProjects` alone does not prove deletion. Check visibility, filters, and pagination, then use an authorized direct query or administrator confirmation. Permission errors and timeouts remain **unknown**.

## September 2, 2026 Cleanup State

Stored September 2 read-only recheck:

| Resource Type | State |
|---|---|
| SageMaker MLflow App | none remaining |
| experiment S3 bucket | none remaining |
| experiment IAM roles | none remaining |
| EKS cluster / GPU instance | never created |
| Unified Studio `qwen-pii-*` project | 1 `ACTIVE` |

If that state still exists, the domain administrator and existing project owner must verify permissions and ownership before cleanup. Do not infer historical membership or ownership from a new role name.

## What Was Not Measured

| Item | Why No Result Is Published |
|---|---|
| fine-tuned entity F1 | adapter training and tuned evaluation were not executed |
| improvement over baseline | no baseline/tuned pair from the same GPU environment |
| training duration | no SageMaker or EKS training Job executed |
| peak GPU memory | no GPU process executed |
| GPU cost | no GPU Job started, so there is no comparable measured result |
| Total experiment cost | no reconciled billing report for other resources such as the MLflow App and S3 |

A configured maximum runtime or step count is a design input, not an observed result.

## Rerun Gate

Complete every condition in order:

1. Reconcile the old inventory with actual resources and resolve remaining or unknown **experiment-owned resources**. A shared name prefix does not authorize deletion.
2. Recheck the current account, Region, quotas, image, domain, profile, and owner membership.
3. Freeze the reviewed configuration, source, and dataset hashes; verify uploaded objects.
4. Run the billable SageMaker smoke job and preserve its result files.
5. Review CloudWatch and MLflow for raw-data leakage. Success status or allowed filenames alone do not satisfy this check.
6. Decide whether to execute the full Job from the verified smoke evidence.

Run the EKS comparison as a separate smoke/full sequence after freezing the SageMaker smoke result and dataset hashes.

## Evidence Locations

- Structured result: `examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json`
- Detailed validation record: `docs/superpowers/reports/2026-09-01-sagemaker-qwen-pii-validation.md`
- Runnable package: `examples/ai-ml/qwen-pii-finetuning/`

Previous: [Part 4 — Unified Studio governance](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md)

Start over: [SageMaker Qwen PII guidebook](README.md)

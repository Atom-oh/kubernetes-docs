# Qwen PII Fine-Tuning Experiment

The historical package defines the same QLoRA experiment for two execution paths:

1. Amazon SageMaker AI Training with SageMaker managed MLflow.
2. An ephemeral Amazon EKS GPU Job with MLflow running inside the cluster.

The model learns to emit one `TYPE<TAB>ORIGINAL` PII entity per line.
Deterministic Python code performs replacement with tokens such as
`[PERSON_1]` and `[PHONE_1]`; the model does not generate the final masked
document.
Replacement and round-trip tests do not prove complete PII detection or
anonymity. Neither GPU execution path completed in the recorded AWS validation.

**Those historical resource-creation and GPU paths remain blocked.** The pinned
PyTorch 2.8 SageMaker DLC reached end of patch on **2026-08-06** according to
the upstream `aws/deep-learning-containers` image catalog. Upgrade the DLC,
torch/dependencies, and MLflow pairing together and validate GPU smoke behavior
before re-enabling execution. Do not remove the support check alone.

## Recorded GPU execution: September 16, 2026

The separate `src/train_execution.py` path completed a real SageMaker GPU smoke
job with the same Qwen model, pinned model revision, and a supported PyTorch 2.11
AL2023/CUDA 13 image. Its [configuration](config/execution-20260916.json) uses
NF4, BF16 computation, and rank-16 LoRA on `q_proj`, `k_proj`, `v_proj`, and
`o_proj`: 13,369,344 trainable attention parameters. It uses SageMaker Training
Jobs directly, with no Studio project, EKS cluster, or managed MLflow dependency.
This is a separate execution path; the historical seven-module configuration
and runtime support guard are unchanged.

The [aggregate smoke receipt](results/execution-smoke-20260916.json) records
four optimizer steps on 32 training records, validation loss on eight records,
and paired generation on four validation records. All 384 adapter tensors
changed; saved/reloaded state hashes matched exactly. The final adapter weights
are 53,528,920 bytes and remain private. Peak PyTorch allocated memory through
training was 21.39 GiB. AWS reported 1,140 billable seconds, an estimated
USD 1.46 of GPU compute at the recorded Seoul price; this excludes storage,
logging, taxes, and billing adjustments.

This smoke run **does not demonstrate better extraction quality**. Across two
positive and two negative validation documents, baseline entity F1 was 1.0000
with only 2/4 correctly formatted responses. The tuned adapter had F1 0.8125 and
4/4 formatted responses, but added six false-positive entity pairs on the
negative documents. Format, omissions, and excessive masking need separate
interpretation; four documents are not a representative performance benchmark.

The new `data/execution_dataset.py` creates a separate 1,600/200/400 corpus
covering all nine entity types in Korean and English. It splits source families
before augmentation, augments training only, and audits exact NFC-source
separation. Names and templates are partly shared across splits, so the corpus
does not establish unseen-domain generalization. The 40-family CPU lab and
historical generator remain separate.

At 11:12 UTC on September 16, a 600-step full job was submitted with a 36-hour
server runtime limit. This is a **submission record**, not a full-training result.
The job selects a checkpoint using validation loss, then evaluates the base model
and selected adapter on the 400 test documents and writes aggregate JSON plus
`final_adapter/` to its private SageMaker model output. It does not deploy an endpoint.
The smoke and full reservations total USD 199.2944375 against the user's USD 500
authorization; reservations include a two-hour overhead and USD 5 incidental
allowance per job and are not actual spending.

The dated launcher is restricted to `samples-atomoh` and one canonical ledger
under the primary checkout's `.vitepress/cache/qlora-execution-20260916/evidence/run`.
It is this account owner's execution record, not an unrestricted deployment
script for another account. A different evidence path cannot reset the budget.
The launcher refuses to replace submitted inputs or launch full training without
verified smoke evidence. Private inventories, generated data, adapters, and
observer logs must not be committed. The dedicated S3 bucket expires objects
after 30 days; training instances terminate with their jobs.

Direct training versions are pinned and the complete installed package inventory
is saved in SageMaker's separate `output.tar.gz`. An unused preinstalled S3FS
package reported an FSSpec version conflict; the reviewed execution uses local
File channels and in-memory datasets, not that optional backend. Do not infer a
fully locked dependency closure or working S3FS integration from this run.

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

## Hands-on CPU workshops

The [learning path](../../../en/ai-ml/sagemaker-ai/README.md) now includes
[QLoRA training](../../../en/ai-ml/sagemaker-ai/05-qlora-finetuning-workshop.md),
[data augmentation](../../../en/ai-ml/sagemaker-ai/06-data-augmentation-workshop.md),
and [PII evaluation](../../../en/ai-ml/sagemaker-ai/07-pii-evaluation-release.md).
Korean versions are available from the
[Korean learning path](../../../ko/ai-ml/sagemaker-ai/README.md).

Run the following from this package directory with Python 3.12:

```bash
mkdir -p "${XDG_CACHE_HOME:-$HOME/.cache}/qwen-pii-lab"
PII_AUG_RUN="$(mktemp -d "${XDG_CACHE_HOME:-$HOME/.cache}/qwen-pii-lab/run.XXXXXX")"
python3 -m data.augmentation_lab --output-dir "$PII_AUG_RUN/dataset" --seed 42
python3 -m data.augmentation_lab --audit-dir "$PII_AUG_RUN/dataset"
```

The output directory must not already exist. The lab creates a separate
40-family, three-label synthetic dataset, assigns families before augmentation,
and augments training only. It preserves the existing JSONL learning fields
while adding provenance and an `augmentation-manifest.json`. It uses no AWS
services, model weights, GPU packages, or external generation APIs.

The audit validates this deterministic lab's schema, family/parent relationships,
split and exact-source separation, labels/TSV, counts, and hashes. It is not a
general validator for arbitrary customer annotations or unseen-template quality.
Templates and some entities are shared between splits. The historical generator
1.0.0 and its committed manifest remain unchanged; the lab manifest is not a
drop-in replacement for the existing uploader's dataset manifest.

The evaluation workshop uses manually constructed predictions to demonstrate
better recall with worse masking on a negative document. Those fixture scores
are not trained-model results. The historical trainer reads test records on every
run; a real tuning loop must separate validation-based selection from final test
evaluation rather than repeatedly selecting against that test.

## Validation result

The AWS validation performed on September 1, 2026 stopped before GPU training
because the created SageMaker Unified Studio project did not grant the caller
project membership. The factual result, cleanup status, and remaining owner
action are recorded in the repository-internal report at
`docs/superpowers/reports/2026-09-01-sagemaker-qwen-pii-validation.md`.
That record is historical; verify current project ownership and residual
resources before resuming the experiment.

# SageMaker Qwen PII Fine-Tuning and Unified Studio Design

## Goal

Add Korean and English training content that explains and demonstrates:

- Amazon SageMaker AI as a managed model-training platform;
- Amazon SageMaker Unified Studio as the governed data and AI workspace;
- parameter-efficient fine-tuning of a 20–30B-class Qwen model for PII
  extraction;
- the same experiment executed through SageMaker AI and through an ephemeral
  Amazon EKS environment with MLflow;
- measured accuracy, runtime, and cost results from both execution paths.

The implementation must run the experiment in AWS rather than publish
fabricated or expected results. After results are downloaded, all temporary
cloud resources must be deleted.

## Approved Requirements

- Use `ap-northeast-2`.
- Use Korean synthetic examples for 80% of the dataset and English synthetic
  examples for 20%.
- Use only generated PII. Do not copy real customer, employee, or repository
  data into the dataset.
- Cover at least `PERSON`, `RRN`, `DOB`, `REL`, `ADDRESS`, `PHONE`, `EMAIL`,
  `ACCOUNT`, and `CARD`.
- Use the same dataset, model, dependency versions, seed, training
  hyperparameters, and evaluation code in both execution environments.
- Execute one SageMaker AI Training Job and one EKS Kubernetes Job.
- Track the SageMaker run with SageMaker managed MLflow and the EKS run with an
  ephemeral MLflow server running on EKS.
- Record baseline and fine-tuned results.
- Delete the SageMaker MLflow App, EKS cluster and GPU node, Unified Studio
  test project, S3 objects and bucket, IAM experiment roles, and other
  experiment-specific cloud resources after exporting results.
- Preserve only non-sensitive result summaries, plots, hashes, and
  reproducibility metadata in this repository.

## Architecture Decision

Fine-tune Qwen as a PII **extractor**, not as a free-form text redactor.

The model input is an instruction plus a source document. The model target is a
newline-delimited TSV list:

```text
PERSON	김민수
RRN	850315-1234567
PHONE	010-2345-6789
```

A deterministic post-processor converts these extracted entities into tokens:

```text
고객명: [PERSON_1], 주민번호: [RRN_1], 연락처: [PHONE_1]
```

This is adapted from the existing `aws-fsi-demo` contract:

- source prompt and parser:
  `/home/atomoh/aws-fsi-demo/src/backend/app/pipeline.py`;
- deterministic token mapping:
  `/home/atomoh/aws-fsi-demo/src/backend/pii/pseudonymizer.py`;
- Qwen-to-pseudonymizer interface:
  `/home/atomoh/aws-fsi-demo/src/backend/pii/main.py`;
- tokenization and parser regression tests:
  `/home/atomoh/aws-fsi-demo/tests/backend/test_pseudonymizer.py` and
  `/home/atomoh/aws-fsi-demo/tests/backend/test_pipeline_helpers.py`.

The new example will be self-contained. It may adapt the algorithms and test
cases, but it must not import code from the sibling repository at runtime and
must not modify or deploy the `aws-fsi-demo` worktree.

### Alternatives rejected

1. **Train Qwen to emit the fully redacted document.**
   This creates non-deterministic token numbering, makes exact reassembly
   difficult, and mixes entity detection errors with generation errors.
2. **Replace Qwen with a token-classification NER model.**
   This would be cheaper, but it would not satisfy the requested Qwen
   fine-tuning example or demonstrate instruction fine-tuning of an LLM.
3. **Use one shared MLflow server for both runtimes.**
   Direct side-by-side comparison would be convenient, but it would fail to
   demonstrate both SageMaker managed MLflow and MLflow operated on EKS.

## Model and Fine-Tuning Design

Use `Qwen/Qwen3-30B-A3B-Instruct-2507`.

The model is a 30B-class mixture-of-experts model and fits the requested
20–30B lightweight category through its smaller active parameter count. It is
also old enough to have established Transformers, PEFT, TRL, and vLLM support,
unlike newly released model families whose training support may still change.

Use QLoRA rather than full-parameter fine-tuning:

| Setting | Value |
|---|---|
| Quantization | 4-bit NF4 with double quantization |
| Compute dtype | BF16 |
| LoRA rank | 16 |
| LoRA alpha | 32 |
| LoRA dropout | 0.05 |
| Target modules | `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj` |
| Maximum sequence length | 1024 tokens |
| Per-device batch size | 1 |
| Gradient accumulation | 8 |
| Learning rate | `2e-4` |
| Scheduler | cosine |
| Warmup ratio | 0.03 |
| Maximum training steps | 80 |
| Evaluation interval | 20 steps |
| Seed | 42 |
| Gradient checkpointing | enabled |

The first smoke test uses 10 training steps. The full 80-step run starts only
after the smoke test proves that model loading, quantization, forward/backward
passes, checkpointing, MLflow logging, and artifact upload work.

Each job has a hard runtime limit of 10,800 seconds. A failed full run may be
retried once only after its cause is identified. Do not blindly resubmit an
unchanged failed job.

## Dataset Design

Generate the dataset deterministically with seed 42:

| Split | Records |
|---|---:|
| Train | 1,600 |
| Validation | 200 |
| Test | 400 |

Each split contains 80% Korean and 20% English records. A source record has:

```json
{
  "id": "ko-insurance-0001",
  "language": "ko",
  "domain": "insurance",
  "source_text": "고객 김민수의 연락처는 010-2345-6789입니다.",
  "entities": [
    {"type": "PERSON", "original": "김민수"},
    {"type": "PHONE", "original": "010-2345-6789"}
  ],
  "target_tsv": "PERSON\t김민수\nPHONE\t010-2345-6789"
}
```

### Dataset composition

Include:

- financial-document prose, forms, Markdown tables, key-value text, support
  messages, and OCR-like line breaks;
- repeated PII values that must receive one stable token;
- multiple people and multiple values of the same type;
- spacing, hyphen, dot, tab, newline, NFC/NFD, and OCR-style variants;
- overlapping strings such as a short address within a longer address;
- negative examples containing company phone numbers, business registration
  numbers, document numbers, dates, monetary values, and ordinary names of
  organizations;
- no-PII documents whose target is an empty string;
- adversarial examples based on the failure categories already documented in
  `aws-fsi-demo/docs/pii/ner-benchmark-2026-04-17.md`.

Generated resident registration numbers, account numbers, cards, and other
identifiers must be deliberately invalid for real-world use. Where an
identifier has a checksum, the generator must reject checksum-valid values.
Synthetic names and addresses must use clearly fictional organizations and
locations.

### Versioning

The generator writes:

- `train.jsonl`, `validation.jsonl`, and `test.jsonl`;
- `dataset-manifest.json` with generator version, seed, record counts,
  per-language counts, per-type counts, and SHA-256 hashes;
- a small human-review sample with at least two examples per entity type and
  language where applicable.

Only the generator, manifest, and review sample are committed. The complete
generated dataset is uploaded to an experiment-specific S3 bucket and deleted
after the experiment.

## Deterministic Tokenization Contract

The post-processor must preserve the safety properties learned from
`aws-fsi-demo`:

1. Accept only whitelisted entity types.
2. Strip `<think>...</think>` content and ignore non-TSV prose lines.
3. Validate that every extracted value occurs in the normalized source text or
   matches an approved formatting variant.
4. Normalize source text and extracted values to Unicode NFC.
5. Deduplicate identical values.
6. Resolve multiple labels for one value with a fixed priority order.
7. Assign token numbers by the value's first source-text offset, not model
   output order.
8. Break equal-offset ties by longer value first and then lexical order.
9. Give literal originals priority over generated formatting variants.
10. Replace all values in one `re.sub` pass, longest pattern first.
11. Apply digit boundaries to purely numeric values so a date or ID does not
    replace a substring inside a longer number.
12. Emit only tokens matching `\[[A-Z_]+_\d+\]`.
13. Verify deterministic round-trip reassembly in tests.
14. Never write raw PII values to stdout, CloudWatch, MLflow parameters, or
    MLflow tags. Aggregate counts and synthetic record IDs are sufficient.

## Common Training Package

Create one package used by both execution paths:

```text
examples/ai-ml/qwen-pii-finetuning/
├── README.md
├── requirements.lock
├── config/
│   └── experiment.yaml
├── data/
│   ├── generate_dataset.py
│   └── review-sample.jsonl
├── src/
│   ├── dataset.py
│   ├── pii_tokens.py
│   ├── train.py
│   ├── evaluate.py
│   ├── metrics.py
│   └── export_results.py
├── launch/
│   ├── sagemaker_train.py
│   └── eks/
│       ├── namespace.yaml
│       ├── mlflow.yaml
│       └── training-job.yaml
├── tests/
│   ├── test_dataset.py
│   ├── test_pii_tokens.py
│   ├── test_metrics.py
│   └── test_config_parity.py
└── results/
    ├── experiment-summary.json
    └── README.md
```

`train.py` reads configuration from arguments and environment variables, but
the resolved configuration is written to `resolved-config.json` and logged as
an artifact. Both launchers must produce an identical resolved configuration
except for environment labels and infrastructure identifiers.

## Execution Path A: SageMaker AI

1. Reuse the existing account and `ap-northeast-2`.
2. Create a least-privilege experiment role for S3 inputs/outputs, CloudWatch
   Logs, and SageMaker managed MLflow access.
3. Create an experiment-specific S3 bucket with default encryption, Block
   Public Access, and a deletion policy suitable for teardown.
4. Create a SageMaker managed MLflow App with automatic model registration
   disabled and without making it the account default.
5. Submit a SageMaker Training Job on one `ml.g6e.4xlarge`, with a 300 GB
   training volume and `MaxRuntimeInSeconds=10800`.
6. Use the common `train.py`, dependency lock, dataset hashes, and experiment
   configuration.
7. Log baseline evaluation, fine-tuning metrics, final evaluation, resource
   metadata, and artifacts to managed MLflow.
8. Download the result export before deleting the MLflow App.

SageMaker infrastructure management, automatic job shutdown, CloudWatch Logs,
and managed MLflow are the subject of the SageMaker AI example.

## Execution Path B: EKS with MLflow

Do not deploy the experiment into the shared `fsi-demo-cluster`. Its repository
requires GitOps changes and the user supplied it only as a tokenization
reference.

1. Create an ephemeral EKS cluster named with the experiment timestamp.
2. Use one on-demand `g6e.4xlarge` accelerated node with sufficient root volume
   for the Qwen model cache.
3. Install the NVIDIA device plugin and verify `nvidia.com/gpu: 1`.
4. Deploy an internal-only MLflow server in an experiment namespace.
5. Run the common training package as a Kubernetes Job requesting one GPU.
6. Log the same resolved parameters, baseline results, training metrics, final
   results, and artifacts to the EKS MLflow server.
7. Export the MLflow experiment through a port-forward before cluster deletion.

The EKS path demonstrates operational responsibility: cluster creation, GPU
device enablement, MLflow deployment, job scheduling, log collection, artifact
export, and teardown.

## SageMaker Unified Studio Validation

Use the existing SageMaker Unified Studio V2 domain in `ap-northeast-2` that
has the enabled **All capabilities** project profile.

Create an ephemeral project for the experiment and validate:

- project creation and membership;
- access to the versioned S3 dataset from the project;
- the relationship between Unified Studio projects, SageMaker AI Training,
  and MLflow experiment tracking;
- discovery of the generated dataset metadata and result artifacts;
- cleanup behavior when the experiment project is deleted.

The project is a governed workspace demonstration, not a third training
runtime. The same SageMaker Training Job remains the compute execution path.

## Evaluation Design

Evaluate the untouched base model and the fine-tuned adapter on the same frozen
test set.

### Accuracy and safety metrics

- exact entity precision, recall, and F1 for `(type, normalized original)`;
- per-type precision, recall, and F1;
- document leak rate: percentage of documents where any ground-truth PII
  remains after deterministic tokenization;
- leaked entity rate;
- over-redaction rate on annotated non-PII negative spans;
- hallucinated entity rate: extracted values absent from the source;
- TSV parse success rate;
- deterministic tokenization rate across repeated, shuffled entity order;
- round-trip reassembly success rate.

### Operational metrics

- model download and initialization time;
- training wall-clock time;
- evaluation wall-clock time;
- peak GPU memory;
- samples per second;
- MLflow logging success;
- billable GPU duration;
- estimated GPU cost from recorded duration and the current AWS Price List API.

All calculations must be performed by code and exported to JSON. Do not
calculate percentages or costs manually in prose.

### Result interpretation

The final documentation must publish actual values even if fine-tuning does
not improve every metric. It must distinguish:

- base model versus fine-tuned model;
- SageMaker execution behavior versus EKS execution behavior;
- model-quality differences from infrastructure differences;
- PII extraction errors from deterministic replacement errors.

Desired acceptance targets are:

- TSV parse success at least 99%;
- deterministic tokenization and round-trip reassembly at 100%;
- fine-tuned micro-F1 at least five percentage points above the base model;
- lower document leak rate than the base model;
- no raw PII values in training or infrastructure logs.

Failure to meet an accuracy target is not hidden. It becomes a documented
finding with the relevant per-type failure analysis.

## Documentation Structure

### AI/ML

Create:

- `ko/ai-ml/sagemaker-ai/README.md`
- `ko/ai-ml/sagemaker-ai/01-training-architecture.md`
- `ko/ai-ml/sagemaker-ai/02-qwen-pii-finetuning.md`
- `ko/ai-ml/sagemaker-ai/03-results-and-operations.md`
- matching English pages under `en/ai-ml/sagemaker-ai/`;
- one quiz per numbered page in both locales;
- `ko/ai-ml/mlflow/04-qwen-pii-finetuning-on-eks.md`;
- `en/ai-ml/mlflow/04-qwen-pii-finetuning-on-eks.md`;
- matching MLflow quizzes.

The SageMaker series explains the managed path. MLflow Part 4 explains the EKS
path using the same experiment and directly links to the measured comparison.

### Data

Create:

- `ko/data-on-eks/sagemaker-unified-studio/README.md`
- `ko/data-on-eks/sagemaker-unified-studio/01-domains-projects-catalog.md`
- `ko/data-on-eks/sagemaker-unified-studio/02-pii-dataset-workflow.md`
- matching English pages;
- one quiz per numbered page in both locales.

Although Unified Studio is managed rather than an EKS-hosted application, it
belongs in the existing Data section as the managed workspace and governance
counterpart to the EKS-operated data tools. The section introduction must make
this boundary explicit.

### Navigation and cross-links

Update:

- `ko/SUMMARY.md`, `en/SUMMARY.md`;
- `ko/README.md`, `en/README.md`;
- `ko/data-on-eks/README.md`, `en/data-on-eks/README.md`;
- `ko/ai-ml/mlflow/README.md`, `en/ai-ml/mlflow/README.md`;
- relevant SageMaker, training, MLflow, Kubeflow, and Data on EKS comparison
  links.

Do not hand-edit `cn/`, `jp/`, or `es/`.

## Result Artifacts

Commit only:

- generator and training/evaluation source;
- dependency lock and resolved experiment configuration;
- dataset manifest and small review sample;
- aggregate metrics JSON;
- result comparison CSV;
- non-sensitive plots;
- documentation tables derived from the JSON;
- a teardown report listing every created resource and its deletion status.

Do not commit:

- model weights or LoRA adapters;
- full generated training data;
- MLflow backend databases;
- raw CloudWatch logs;
- credentials, account IDs, role session identifiers, or presigned URLs.

## Error Handling and Safety

- Run a local CPU-only dataset/tokenization test suite before provisioning AWS
  resources.
- Run a 10-step GPU smoke test before each full run.
- Treat a non-parseable model response as an evaluation failure, not an empty
  correct result.
- Stop the run if model outputs contain a non-whitelisted entity type at an
  unexpected rate or if tokenization round-trip tests fail.
- Stop and diagnose CUDA OOM, dependency mismatch, model download corruption,
  MLflow authentication failure, or missing GPU scheduling before retrying.
- Use a unique experiment tag on every AWS resource.
- Maintain a machine-readable resource inventory from creation through
  deletion.
- Cleanup must run after success or failure. Then use read-only AWS queries to
  prove that no experiment-tagged compute, MLflow, project, S3, IAM, or log
  resource remains.

## Validation

Before claiming completion:

1. Run all unit and contract tests for the common experiment package.
2. Verify dataset split isolation and deterministic SHA-256 hashes.
3. Complete both AWS runs and export both MLflow experiments.
4. Generate the result summary from exported JSON.
5. Run the new documentation content-contract test.
6. Run `npm run docs:validate`.
7. Build Korean and English VitePress sites separately.
8. Run `git diff --check`.
9. Execute teardown.
10. Query AWS for tagged leftovers and attach the empty result to the teardown
    report.

## Primary Sources

- [What is Amazon SageMaker? — Unified Studio](https://docs.aws.amazon.com/next-generation-sagemaker/latest/userguide/what-is-sagemaker.html)
- [Track experiments using MLflow](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/userguide/sagemaker-experiments.xml.html)
- [SageMaker distributed training](https://docs.aws.amazon.com/sagemaker/latest/dg/distributed-training.html)
- [Qwen3 repository](https://github.com/QwenLM/Qwen3)
- [Qwen3-30B-A3B-Instruct-2507 model card](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)

## Non-Goals

- training on real PII;
- deploying the fine-tuned model as a permanent production endpoint;
- modifying the `aws-fsi-demo` application or its shared EKS cluster;
- comparing Qwen against Amazon Comprehend, Bedrock Guardrails, or the PIILOT
  NER model as separate production alternatives;
- retaining temporary AWS infrastructure after the result export;
- translating the new pages manually into Chinese, Japanese, or Spanish.

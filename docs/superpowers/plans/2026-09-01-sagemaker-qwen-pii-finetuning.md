# SageMaker Qwen PII Fine-Tuning and Unified Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add reproducible Korean and English SageMaker AI, SageMaker Unified Studio, and EKS+MLflow training content backed by two real Qwen3-30B-A3B PII fine-tuning runs and verified teardown.

**Architecture:** Build one self-contained experiment package that generates a versioned synthetic dataset, fine-tunes Qwen with QLoRA, parses `TYPE<TAB>ORIGINAL` output, and performs deterministic token replacement. Execute the identical package first as a SageMaker AI Training Job tracked by SageMaker managed MLflow and then as an ephemeral EKS GPU Job tracked by MLflow on EKS; export aggregate results, delete every experiment resource, and publish the measured comparison in mirrored ko/en documentation.

**Tech Stack:** Python 3.12 in AWS PyTorch DLC 2.8.0, PyTorch 2.8.0, Transformers 4.57.6, PEFT 0.17.1, TRL 0.24.0, bitsandbytes 0.48.2, MLflow 3.1.4, SageMaker managed MLflow, Amazon S3, Amazon SageMaker AI Training Jobs, Amazon SageMaker Unified Studio/DataZone V2, Amazon EKS 1.36, NVIDIA L40S (`g6e.4xlarge`), Kubernetes, Node.js content-contract tests, VitePress.

**Spec:** `docs/superpowers/specs/2026-09-01-sagemaker-qwen-pii-finetuning-design.md`

## Global Constraints

- Work from an isolated git worktree created from `origin/main`; do not mix this feature into the current `docs/mermaid-diagram-migration` branch.
- Do not modify `/home/atomoh/aws-fsi-demo`; it is a read-only behavioral reference.
- Do not deploy into `fsi-demo-cluster` or any existing `mall-*` cluster.
- Use region `ap-northeast-2`.
- Use model `Qwen/Qwen3-30B-A3B-Instruct-2507`.
- Use seed `42`, 1,600 train records, 200 validation records, and 400 frozen test records.
- Keep each split at 80% Korean and 20% English.
- Use only deliberately invalid synthetic identifiers; no real PII or copied repository PII.
- Train the model to emit TSV entity rows; deterministic code performs token replacement.
- Use the same model, dataset hashes, dependency versions, hyperparameters, evaluation code, and `763104351884.dkr.ecr.ap-northeast-2.amazonaws.com/pytorch-training:2.8.0-gpu-py312-cu129-ubuntu22.04-sagemaker` image in both environments.
- Run one 10-step smoke test before each 80-step full run.
- Limit every GPU job to 10,800 seconds and diagnose before the single permitted retry.
- Do not log source text, extracted PII values, mappings, or model completions containing PII to stdout, CloudWatch, MLflow params/tags, or committed artifacts.
- Export actual values even when targets are missed; do not invent or smooth results.
- Delete all experiment-specific AWS resources after downloading results.
- Edit only `ko/` and `en/`; never hand-edit `cn/`, `jp/`, or `es/`.

---

### Task 1: Create the isolated feature worktree and experiment package contract

**Files:**
- Create: `examples/ai-ml/qwen-pii-finetuning/README.md`
- Create: `examples/ai-ml/qwen-pii-finetuning/requirements.lock`
- Create: `examples/ai-ml/qwen-pii-finetuning/config/experiment.yaml`
- Create: `examples/ai-ml/qwen-pii-finetuning/tests/test_config_parity.py`
- Create: `examples/ai-ml/qwen-pii-finetuning/src/__init__.py`
- Copy approved artifacts into the worktree:
  - `docs/superpowers/specs/2026-09-01-sagemaker-qwen-pii-finetuning-design.md`
  - `docs/superpowers/plans/2026-09-01-sagemaker-qwen-pii-finetuning.md`

**Interfaces:**
- Produces: `load_experiment_config(path: Path) -> dict` contract consumed by dataset, training, launch, and evaluation tasks.
- Produces: one immutable dependency lock and one canonical experiment configuration.

- [ ] **Step 1: Create an isolated worktree**

Use `superpowers:using-git-worktrees`, then create a feature branch from current `origin/main`:

```bash
git fetch origin
git worktree add ../kubernetes-docs-sagemaker-qwen -b feat/sagemaker-qwen-pii-finetuning origin/main
```

Expected: a clean worktree at `/home/atomoh/kubernetes-docs-sagemaker-qwen` on `feat/sagemaker-qwen-pii-finetuning`.

- [ ] **Step 2: Add the approved spec and plan to the feature worktree**

Read the two approved files from the original worktree and use `apply_patch`
with the feature-worktree absolute paths to add byte-identical copies. Verify
identity with:

```bash
sha256sum \
  docs/superpowers/specs/2026-09-01-sagemaker-qwen-pii-finetuning-design.md \
  ../kubernetes-docs-sagemaker-qwen/docs/superpowers/specs/2026-09-01-sagemaker-qwen-pii-finetuning-design.md
sha256sum \
  docs/superpowers/plans/2026-09-01-sagemaker-qwen-pii-finetuning.md \
  ../kubernetes-docs-sagemaker-qwen/docs/superpowers/plans/2026-09-01-sagemaker-qwen-pii-finetuning.md
```

Expected: each source/destination pair has an identical SHA-256 hash and the
feature worktree lists only those two new files.

- [ ] **Step 3: Write the failing configuration parity test**

```python
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_experiment_config_contains_the_approved_constants():
    config = yaml.safe_load((ROOT / "config/experiment.yaml").read_text())
    assert config["model_id"] == "Qwen/Qwen3-30B-A3B-Instruct-2507"
    assert config["seed"] == 42
    assert config["dataset"] == {"train": 1600, "validation": 200, "test": 400}
    assert config["languages"] == {"ko": 0.8, "en": 0.2}
    assert config["training"]["max_steps"] == 80
    assert config["training"]["smoke_steps"] == 10
    assert config["training"]["max_runtime_seconds"] == 10800
    assert config["compute"]["sagemaker"] == "ml.g6e.4xlarge"
    assert config["compute"]["eks"] == "g6e.4xlarge"
```

- [ ] **Step 4: Run the test and verify RED**

Run:

```bash
python3 -m venv /tmp/qwen-pii-plan-venv
/tmp/qwen-pii-plan-venv/bin/pip install pytest==8.4.2 PyYAML==6.0.3
/tmp/qwen-pii-plan-venv/bin/pytest \
  examples/ai-ml/qwen-pii-finetuning/tests/test_config_parity.py -q
```

Expected: FAIL because `config/experiment.yaml` does not exist.

- [ ] **Step 5: Add the pinned dependency lock**

Write `requirements.lock` exactly as:

```text
accelerate==1.10.1
bitsandbytes==0.48.2
boto3==1.42.97
datasets==3.6.0
hf-transfer==0.1.9
huggingface-hub==0.36.0
mlflow==3.1.4
peft==0.17.1
PyYAML==6.0.3
safetensors==0.7.0
sagemaker-mlflow==0.5.0
sentencepiece==0.2.2
torch==2.8.0
transformers==4.57.6
trl==0.24.0
```

- [ ] **Step 6: Add the canonical experiment configuration**

```yaml
experiment_name: qwen-pii-finetuning
model_id: Qwen/Qwen3-30B-A3B-Instruct-2507
seed: 42
dataset:
  train: 1600
  validation: 200
  test: 400
languages:
  ko: 0.8
  en: 0.2
entity_types:
  - PERSON
  - RRN
  - DOB
  - REL
  - ADDRESS
  - PHONE
  - EMAIL
  - ACCOUNT
  - CARD
training:
  quantization: nf4
  double_quant: true
  compute_dtype: bfloat16
  lora_rank: 16
  lora_alpha: 32
  lora_dropout: 0.05
  max_sequence_length: 1024
  per_device_batch_size: 1
  gradient_accumulation_steps: 8
  learning_rate: 0.0002
  scheduler: cosine
  warmup_ratio: 0.03
  smoke_steps: 10
  max_steps: 80
  evaluation_interval: 20
  max_runtime_seconds: 10800
compute:
  sagemaker: ml.g6e.4xlarge
  eks: g6e.4xlarge
```

- [ ] **Step 7: Verify GREEN**

Run the focused pytest command from Step 4.

Expected: PASS.

- [ ] **Step 8: Add the package README**

Document the two execution paths, the TSV contract, local test command, generated artifacts, resource tag `Experiment=qwen-pii-finetuning`, and teardown requirement. State explicitly that the package contains no model weights or real PII.

- [ ] **Step 9: Commit**

```bash
git add docs/superpowers examples/ai-ml/qwen-pii-finetuning
git commit -m "docs: define SageMaker Qwen PII experiment"
```

---

### Task 2: Implement the deterministic synthetic dataset generator

**Files:**
- Create: `examples/ai-ml/qwen-pii-finetuning/.gitignore`
- Create: `examples/ai-ml/qwen-pii-finetuning/data/generate_dataset.py`
- Create: `examples/ai-ml/qwen-pii-finetuning/data/review-sample.jsonl`
- Create: `examples/ai-ml/qwen-pii-finetuning/tests/test_dataset.py`
- Create at runtime, do not commit: `examples/ai-ml/qwen-pii-finetuning/generated/`

**Interfaces:**
- Produces: `generate_dataset(output_dir: Path, config_path: Path) -> dict[str, Path]`.
- Produces JSONL records with fields `id`, `language`, `domain`, `source_text`, `entities`, and `target_tsv`.
- Produces: `dataset-manifest.json` with SHA-256 hashes consumed by both launchers.

- [ ] **Step 1: Write failing dataset tests**

```python
import hashlib
import json
from pathlib import Path

from data.generate_dataset import generate_dataset, luhn_valid, rrn_checksum_valid


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def test_generator_is_deterministic_and_split_safe(tmp_path):
    first = generate_dataset(tmp_path / "first")
    second = generate_dataset(tmp_path / "second")
    for split in ("train", "validation", "test"):
        assert first[split].read_bytes() == second[split].read_bytes()
    train = read_jsonl(first["train"])
    validation = read_jsonl(first["validation"])
    test = read_jsonl(first["test"])
    assert (len(train), len(validation), len(test)) == (1600, 200, 400)
    assert len({r["id"] for r in train} & {r["id"] for r in test}) == 0
    assert sum(r["language"] == "ko" for r in train) == 1280
    assert sum(r["language"] == "en" for r in train) == 320


def test_identifiers_are_deliberately_invalid(tmp_path):
    paths = generate_dataset(tmp_path)
    for record in read_jsonl(paths["train"]):
        for entity in record["entities"]:
            digits = "".join(ch for ch in entity["original"] if ch.isdigit())
            if entity["type"] == "RRN":
                assert not rrn_checksum_valid(digits)
            if entity["type"] == "CARD":
                assert not luhn_valid(digits)
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
PYTHONPATH=examples/ai-ml/qwen-pii-finetuning \
  /tmp/qwen-pii-plan-venv/bin/pytest \
  examples/ai-ml/qwen-pii-finetuning/tests/test_dataset.py -q
```

Expected: FAIL because `generate_dataset.py` does not exist.

- [ ] **Step 3: Implement checksum guards and record generation**

Implement these exact checksum guards:

```python
def luhn_valid(digits: str) -> bool:
    if not digits.isdigit() or len(digits) < 2:
        return False
    total = 0
    parity = len(digits) % 2
    for index, char in enumerate(digits):
        value = int(char)
        if index % 2 == parity:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def rrn_checksum_valid(digits: str) -> bool:
    if not digits.isdigit() or len(digits) != 13:
        return False
    weights = (2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5)
    check = (11 - sum(int(d) * w for d, w in zip(digits[:12], weights))) % 10
    return check == int(digits[-1])
```

Expose `build_record(rng: random.Random, language: str, domain: str, index:
int) -> dict` and `generate_dataset(output_dir: Path, config_path: Path | None
= None) -> dict[str, Path]` with the behaviors below.

The implementation must:

- construct names, fictional addresses, email domains under `example.com`,
  invalid RRN/card/account values, phones, relationships, and DOB values from
  deterministic lists;
- generate prose, key-value, Markdown table, support-message, and OCR-like
  templates;
- create negative examples for business registration numbers, organization
  switchboard phones, document numbers, monetary values, and clean text;
- include NFC/NFD, whitespace, hyphen, dot, tab, and newline variants;
- shuffle with `random.Random(42)`;
- allocate exact split and language counts;
- reject checksum-valid RRN and card candidates;
- write JSON with `ensure_ascii=False`, sorted keys, and one record per line;
- write hashes using `hashlib.sha256(path.read_bytes()).hexdigest()`.

- [ ] **Step 4: Generate and review the fixed sample**

Run:

```bash
PYTHONPATH=examples/ai-ml/qwen-pii-finetuning \
  python3 examples/ai-ml/qwen-pii-finetuning/data/generate_dataset.py \
  --output-dir examples/ai-ml/qwen-pii-finetuning/generated
```

Expected:

- `train.jsonl`: 1,600 lines;
- `validation.jsonl`: 200 lines;
- `test.jsonl`: 400 lines;
- manifest contains the exact counts and three hashes;
- `review-sample.jsonl` contains at least two examples per entity type and language where that entity applies.

- [ ] **Step 5: Verify GREEN**

Run the focused tests and:

```bash
git status --short examples/ai-ml/qwen-pii-finetuning/generated
```

Expected: tests PASS and the generated directory is ignored rather than staged.

- [ ] **Step 6: Commit**

```bash
git add examples/ai-ml/qwen-pii-finetuning/data \
  examples/ai-ml/qwen-pii-finetuning/tests/test_dataset.py \
  examples/ai-ml/qwen-pii-finetuning/.gitignore
git commit -m "feat: generate synthetic bilingual PII dataset"
```

---

### Task 3: Implement deterministic TSV parsing, tokenization, and reassembly

**Files:**
- Create: `examples/ai-ml/qwen-pii-finetuning/src/pii_tokens.py`
- Create: `examples/ai-ml/qwen-pii-finetuning/tests/test_pii_tokens.py`

**Interfaces:**
- Produces: `Entity(type: str, original: str)`.
- Produces: `parse_tsv(content: str, source_text: str) -> list[Entity]`.
- Produces: `pseudonymize_text(text: str, entities: list[Entity]) -> TokenizationResult`.
- Produces: `reassemble_text(masked_text: str, mapping: dict[str, str]) -> str`.

- [ ] **Step 1: Write the failing parser and tokenization tests**

```python
from src.pii_tokens import Entity, parse_tsv, pseudonymize_text, reassemble_text


def test_tsv_parser_filters_prose_think_blocks_and_unknown_types():
    content = "<think>hidden</think>\n설명\nPERSON\t김민수\nNAME\t버림\nPHONE\t010-2345-6789"
    assert parse_tsv(content, "김민수 010-2345-6789") == [
        Entity("PERSON", "김민수"),
        Entity("PHONE", "010-2345-6789"),
    ]


def test_token_numbers_follow_source_order_not_model_order():
    text = "김민수 고객과 이서연 고객"
    reversed_entities = [Entity("PERSON", "이서연"), Entity("PERSON", "김민수")]
    result = pseudonymize_text(text, reversed_entities)
    assert result.masked_text == "[PERSON_1] 고객과 [PERSON_2] 고객"
    assert result.mapping == {"PERSON_1": "김민수", "PERSON_2": "이서연"}
    assert reassemble_text(result.masked_text, result.mapping) == text


def test_literal_original_wins_over_another_entities_variant():
    text = "전화 01012345678 계좌 010-1234-5678"
    result = pseudonymize_text(
        text,
        [Entity("PHONE", "01012345678"), Entity("ACCOUNT", "010-1234-5678")],
    )
    assert "[PHONE_1]" in result.masked_text
    assert "[ACCOUNT_1]" in result.masked_text
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
PYTHONPATH=examples/ai-ml/qwen-pii-finetuning \
  /tmp/qwen-pii-plan-venv/bin/pytest \
  examples/ai-ml/qwen-pii-finetuning/tests/test_pii_tokens.py -q
```

Expected: FAIL because `pii_tokens.py` does not exist.

- [ ] **Step 3: Implement the parser contract**

Use:

```python
VALID_TYPES = frozenset(
    {"PERSON", "RRN", "DOB", "REL", "ADDRESS", "PHONE", "EMAIL", "ACCOUNT", "CARD"}
)
TOKEN_PATTERN = re.compile(r"\[[A-Z_]+_\d+\]")
```

`parse_tsv` must remove `<think>...</think>`, accept only two-column tab rows,
strip whitespace, reject empty values, reject non-whitelisted types, normalize
to NFC, and reject a value that is absent from the normalized source and all
approved formatting variants.

- [ ] **Step 4: Implement deterministic replacement**

Adapt the reviewed `aws-fsi-demo` behavior:

- fixed label priority;
- source-offset numbering;
- longer-first and lexical tie breaking;
- originals before variants;
- one combined `re.sub` pass;
- digit-only boundary guards;
- global replacement;
- stable `TOKEN_PATTERN`;
- no raw value logging.

Return:

```python
@dataclass(frozen=True)
class TokenizationResult:
    masked_text: str
    mapping: dict[str, str]
```

- [ ] **Step 5: Add regression coverage**

Add tests for NFD/NFC, repeated entities, equal offsets, values not found
verbatim but represented by formatting variants, short numeric fragments,
longer number boundaries, RRN/phone/card/account/DOB formatting, empty entity
lists, and exact round-trip reassembly.

- [ ] **Step 6: Verify GREEN**

Run all tests under `examples/ai-ml/qwen-pii-finetuning/tests/`.

Expected: dataset, config, and tokenization tests PASS.

- [ ] **Step 7: Commit**

```bash
git add examples/ai-ml/qwen-pii-finetuning/src/pii_tokens.py \
  examples/ai-ml/qwen-pii-finetuning/tests/test_pii_tokens.py
git commit -m "feat: add deterministic PII tokenization"
```

---

### Task 4: Implement deterministic evaluation and cost metrics

**Files:**
- Create: `examples/ai-ml/qwen-pii-finetuning/src/metrics.py`
- Create: `examples/ai-ml/qwen-pii-finetuning/src/evaluate.py`
- Create: `examples/ai-ml/qwen-pii-finetuning/tests/test_metrics.py`

**Interfaces:**
- Produces: `score_entities(expected, predicted) -> EntityMetrics`.
- Produces: `evaluate_predictions(records, predictions) -> dict`.
- Produces: `compute_cost(duration_seconds: float, hourly_usd: Decimal) -> Decimal`.
- Produces aggregate JSON without raw PII.

- [ ] **Step 1: Write failing metric tests**

```python
from decimal import Decimal

from src.metrics import compute_cost, score_entities
from src.pii_tokens import Entity


def test_entity_metrics_use_exact_normalized_pairs():
    expected = [Entity("PERSON", "김민수"), Entity("PHONE", "010-1234-5678")]
    predicted = [Entity("PERSON", "김민수"), Entity("EMAIL", "kim@example.com")]
    metrics = score_entities(expected, predicted)
    assert metrics.tp == 1
    assert metrics.fp == 1
    assert metrics.fn == 1
    assert metrics.precision == 0.5
    assert metrics.recall == 0.5
    assert metrics.f1 == 0.5


def test_cost_uses_decimal_and_seconds():
    assert compute_cost(7200, Decimal("4.6169375000")) == Decimal("9.2338750000")
```

- [ ] **Step 2: Run tests and verify RED**

Expected: FAIL because the metrics module does not exist.

- [ ] **Step 3: Implement exact metric formulas**

Use set operations on `(type, NFC-normalized original)` pairs. Handle zero
denominators as `0.0`. Export:

- micro precision/recall/F1;
- per-type counts and scores;
- parse success;
- hallucinated entity count;
- leaked entity count;
- document leak count/rate;
- over-redacted negative span count/rate;
- deterministic tokenization count/rate;
- round-trip count/rate.

Compute all rates in Python, never in Markdown.

- [ ] **Step 4: Implement evaluation input/output**

`evaluate.py` must accept:

```text
--predictions-jsonl
--test-jsonl
--output-json
--environment
--phase
--duration-seconds
--hourly-usd
```

It must write sorted JSON containing `environment`, `phase`, dataset hash,
model ID, counts, metrics, duration, and cost. It must not include
`source_text`, `target_tsv`, completion text, or mapping values.

- [ ] **Step 5: Verify GREEN and commit**

```bash
PYTHONPATH=examples/ai-ml/qwen-pii-finetuning \
  /tmp/qwen-pii-plan-venv/bin/pytest \
  examples/ai-ml/qwen-pii-finetuning/tests -q
git add examples/ai-ml/qwen-pii-finetuning/src \
  examples/ai-ml/qwen-pii-finetuning/tests/test_metrics.py
git commit -m "feat: score PII extraction and leakage"
```

---

### Task 5: Implement the common QLoRA training entry point

**Files:**
- Create: `examples/ai-ml/qwen-pii-finetuning/src/dataset.py`
- Create: `examples/ai-ml/qwen-pii-finetuning/src/train.py`
- Create: `examples/ai-ml/qwen-pii-finetuning/tests/test_training_contract.py`

**Interfaces:**
- Consumes: canonical YAML config and generated JSONL files.
- Consumes: `MLFLOW_TRACKING_URI`, `MLFLOW_EXPERIMENT_NAME`, `RUN_ENVIRONMENT`.
- Produces: LoRA adapter under `/opt/ml/model` on SageMaker or configured output directory on EKS.
- Produces: baseline and fine-tuned prediction JSONL locally, then aggregate metrics only.

- [ ] **Step 1: Write a failing dry-run contract test**

```python
from pathlib import Path

from src.train import build_resolved_config, format_training_text


def test_resolved_config_changes_only_environment_fields():
    sm = build_resolved_config(Path("config/experiment.yaml"), "sagemaker", 10)
    eks = build_resolved_config(Path("config/experiment.yaml"), "eks", 10)
    assert sm["model_id"] == eks["model_id"]
    assert sm["training"] == eks["training"]
    assert sm["dataset"] == eks["dataset"]
    assert sm["run_environment"] == "sagemaker"
    assert eks["run_environment"] == "eks"


def test_sft_text_uses_instruction_source_and_tsv_target():
    record = {
        "source_text": "고객 김민수",
        "target_tsv": "PERSON\t김민수",
    }
    text = format_training_text(record)
    assert "TYPE<TAB>ORIGINAL" in text
    assert "고객 김민수" in text
    assert text.rstrip().endswith("PERSON\t김민수")
```

- [ ] **Step 2: Run tests and verify RED**

Expected: FAIL because the training module does not exist.

- [ ] **Step 3: Implement lazy heavy imports and CLI**

Keep `torch`, `transformers`, `trl`, `peft`, `datasets`, and `mlflow` imports
inside `main()` so contract tests run without GPU dependencies.

Support:

```text
--config
--train-jsonl
--validation-jsonl
--test-jsonl
--output-dir
--steps
--environment
--dataset-manifest
```

- [ ] **Step 4: Implement model and trainer creation**

Use:

```python
BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
)
```

and:

```python
LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
)
```

Configure gradient checkpointing, BF16, batch size 1, accumulation 8, cosine
scheduler, warmup 0.03, seed 42, max sequence length 1024, and the caller's
smoke/full step count.

- [ ] **Step 5: Implement safe MLflow logging**

Log:

- resolved configuration;
- dependency versions;
- dataset hashes and counts;
- training/evaluation loss;
- aggregate baseline and tuned metrics;
- durations and peak GPU memory;
- adapter file inventory without file contents.

Do not log source rows, completions, extracted values, or token mappings.

- [ ] **Step 6: Evaluate baseline and adapter**

Before training, generate predictions for the frozen test set with the base
model. After training, generate predictions with the attached LoRA adapter.
Store raw prediction files only in the job's temporary filesystem; pass them
to `evaluate.py`, upload only aggregate metrics, and delete raw predictions
before job completion.

- [ ] **Step 7: Verify contract tests and commit**

```bash
PYTHONPATH=examples/ai-ml/qwen-pii-finetuning \
  /tmp/qwen-pii-plan-venv/bin/pytest \
  examples/ai-ml/qwen-pii-finetuning/tests -q
git add examples/ai-ml/qwen-pii-finetuning/src \
  examples/ai-ml/qwen-pii-finetuning/tests/test_training_contract.py
git commit -m "feat: add common QLoRA training entry point"
```

---

### Task 6: Add SageMaker launcher and tagged resource lifecycle scripts

**Files:**
- Create: `examples/ai-ml/qwen-pii-finetuning/launch/sagemaker_train.py`
- Create: `examples/ai-ml/qwen-pii-finetuning/launch/aws/preflight.sh`
- Create: `examples/ai-ml/qwen-pii-finetuning/launch/aws/provision.sh`
- Create: `examples/ai-ml/qwen-pii-finetuning/launch/aws/teardown.sh`
- Create: `examples/ai-ml/qwen-pii-finetuning/launch/aws/verify_cleanup.sh`
- Create: `examples/ai-ml/qwen-pii-finetuning/tests/test_sagemaker_request.py`

**Interfaces:**
- Produces: a tagged S3 bucket, SageMaker execution role, MLflow role, MLflow App, and Unified Studio project.
- Produces: `examples/ai-ml/qwen-pii-finetuning/results/resource-inventory.json`.
- Produces: one SageMaker Training Job request from the canonical config.
- Deletes every inventory entry.

- [ ] **Step 1: Write the failing SageMaker request test**

Use `unittest.mock` to verify that
`build_training_job_request(config, inventory, mode, source_s3_uri)` returns:

```python
assert request["AlgorithmSpecification"]["TrainingImage"].endswith(
    "pytorch-training:2.8.0-gpu-py312-cu129-ubuntu22.04-sagemaker"
)
assert request["ResourceConfig"] == {
    "InstanceType": "ml.g6e.4xlarge",
    "InstanceCount": 1,
    "VolumeSizeInGB": 300,
}
assert request["StoppingCondition"]["MaxRuntimeInSeconds"] == 10800
assert request["Environment"]["RUN_ENVIRONMENT"] == "sagemaker"
assert request["Tags"] == [
    {"Key": "Experiment", "Value": "qwen-pii-finetuning"},
    {"Key": "ExperimentId", "Value": "unit-test"},
]
```

- [ ] **Step 2: Run test and verify RED**

Expected: FAIL because the launcher does not exist.

- [ ] **Step 3: Implement preflight**

`preflight.sh` must fail unless:

- caller identity succeeds;
- region resolves to `ap-northeast-2`;
- SageMaker `ml.g6e.4xlarge for training job usage` quota is at least 1;
- EC2 Running On-Demand G/VT quota is at least 16 vCPUs;
- `aws`, `kubectl`, `eksctl`, `helm`, `docker`, `jq`, and `python3` exist;
- the SageMaker PyTorch DLC tag exists in regional ECR;
- no resource with the generated `ExperimentId` already exists.

- [ ] **Step 4: Implement least-privilege provisioning**

`provision.sh` must:

1. set `EXPERIMENT_ID="qwen-pii-$(date -u +%Y%m%d%H%M%S)"`;
2. discover account ID with STS;
3. create a unique encrypted S3 bucket with Block Public Access;
4. create a SageMaker execution role scoped to the bucket prefix, CloudWatch
   Logs, the regional DLC, and managed MLflow access;
5. create a separate MLflow service role scoped to the artifact prefix;
6. create an MLflow App with `AutoModelRegistrationDisabled` and account
   default status `DISABLED`;
7. discover the Unified Studio V2 domain named `sagemaker_hyper`;
8. discover the enabled project profile named `All capabilities`;
9. create a project whose name is exactly `${EXPERIMENT_ID}`;
10. write IDs, ARNs, names, tags, and creation times to
    `results/resource-inventory.json`.

Every create call must be followed by a describe/get poll until the service
reports a ready state or a bounded timeout expires.

- [ ] **Step 5: Implement the Training Job launcher**

Use boto3 with adaptive retries:

```python
Config(retries={"max_attempts": 5, "mode": "adaptive"})
```

Create the request with the common DLC, `/opt/ml/input/data` S3 channel,
`/opt/ml/model` output, the locked requirements and source directory, managed
MLflow ARN, 300 GB volume, one `ml.g6e.4xlarge`, tags, and runtime limit.

Wait for `Completed`, `Failed`, or `Stopped`; write sanitized aggregate output
to `results/sagemaker-${MODE}.json`.

- [ ] **Step 6: Implement teardown and cleanup verification**

`teardown.sh` reads only
`examples/ai-ml/qwen-pii-finetuning/results/resource-inventory.json` and
deletes in dependency order:

1. delete the MLflow App;
2. delete Unified Studio project and poll terminal deletion;
3. empty all versioned and unversioned S3 objects, then delete bucket;
4. detach/delete inline policies and delete experiment roles;
5. delete experiment-specific CloudWatch log groups after result export.

`verify_cleanup.sh` must query tagged SageMaker, EC2/EKS, DataZone, S3, IAM,
CloudWatch, and Resource Groups Tagging API resources and write
`results/teardown-report.json`. It exits nonzero if any experiment resource
remains.

- [ ] **Step 7: Verify tests and shell syntax**

```bash
PYTHONPATH=examples/ai-ml/qwen-pii-finetuning \
  /tmp/qwen-pii-plan-venv/bin/pytest \
  examples/ai-ml/qwen-pii-finetuning/tests -q
bash -n examples/ai-ml/qwen-pii-finetuning/launch/aws/*.sh
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add examples/ai-ml/qwen-pii-finetuning/launch \
  examples/ai-ml/qwen-pii-finetuning/tests/test_sagemaker_request.py
git commit -m "feat: add SageMaker experiment lifecycle"
```

---

### Task 7: Add the ephemeral EKS and MLflow manifests

**Files:**
- Create: `examples/ai-ml/qwen-pii-finetuning/launch/eks/cluster.yaml`
- Create: `examples/ai-ml/qwen-pii-finetuning/launch/eks/namespace.yaml`
- Create: `examples/ai-ml/qwen-pii-finetuning/launch/eks/mlflow.yaml`
- Create: `examples/ai-ml/qwen-pii-finetuning/launch/eks/training-job.yaml`
- Create: `examples/ai-ml/qwen-pii-finetuning/launch/eks/run.sh`
- Create: `examples/ai-ml/qwen-pii-finetuning/tests/test_eks_manifests.py`

**Interfaces:**
- Produces: one isolated EKS 1.36 cluster with one `g6e.4xlarge` managed node.
- Produces: internal-only MLflow service `mlflow.qwen-pii.svc.cluster.local:5000`.
- Produces: one Kubernetes Job requesting `nvidia.com/gpu: 1`.

- [ ] **Step 1: Write failing manifest tests**

Assert:

```python
assert cluster["metadata"]["name"] == "${EXPERIMENT_ID}"
assert cluster["managedNodeGroups"][0]["instanceType"] == "g6e.4xlarge"
assert cluster["managedNodeGroups"][0]["desiredCapacity"] == 1
assert training["spec"]["template"]["spec"]["restartPolicy"] == "Never"
assert container["resources"]["limits"]["nvidia.com/gpu"] == 1
assert container["image"].endswith(
    "pytorch-training:2.8.0-gpu-py312-cu129-ubuntu22.04-sagemaker"
)
assert mlflow_service["spec"]["type"] == "ClusterIP"
```

- [ ] **Step 2: Run tests and verify RED**

Expected: FAIL because manifests do not exist.

- [ ] **Step 3: Implement the cluster config**

Use:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ${EXPERIMENT_ID}
  region: ap-northeast-2
  version: "1.36"
managedNodeGroups:
  - name: gpu
    instanceType: g6e.4xlarge
    desiredCapacity: 1
    minSize: 1
    maxSize: 1
    volumeSize: 300
    amiFamily: AmazonLinux2023
    labels:
      workload: qwen-pii-training
    tags:
      Experiment: qwen-pii-finetuning
      ExperimentId: ${EXPERIMENT_ID}
```

Render `${EXPERIMENT_ID}` into a temporary file before passing it to `eksctl`.

- [ ] **Step 4: Implement MLflow on EKS**

Use `ghcr.io/mlflow/mlflow:v3.1.4`. Run:

```text
mlflow server
--backend-store-uri=sqlite:////mlflow/mlflow.db
--default-artifact-root=/mlflow/artifacts
--host=0.0.0.0
--port=5000
```

Mount an `emptyDir` at `/mlflow`, expose only a ClusterIP service, and add
readiness/liveness probes. The export must occur before deletion because the
backend is intentionally ephemeral.

- [ ] **Step 5: Implement the training Job**

The job must:

- request one GPU;
- select `workload=qwen-pii-training`;
- mount an empty model cache volume;
- install the pinned lock;
- download the S3 dataset;
- execute `src/train.py` with the same config and step count as SageMaker;
- set `MLFLOW_TRACKING_URI=http://mlflow.qwen-pii.svc.cluster.local:5000`;
- set `RUN_ENVIRONMENT=eks`;
- use `backoffLimit: 0` so Kubernetes does not create uncontrolled retries;
- set `activeDeadlineSeconds: 10800`;
- avoid printing source text or predictions.

- [ ] **Step 6: Implement `run.sh`**

The script must:

1. create the cluster;
2. install NVIDIA device plugin chart version `0.20.0`;
3. wait until a GPU appears in node allocatable resources;
4. run `nvidia-smi` in a short validation pod;
5. deploy MLflow and wait Ready;
6. render and start the smoke or full Job;
7. wait for completion with the runtime deadline;
8. run the aggregate exporter inside the MLflow Pod and copy out its sanitized
   JSON without exposing the ClusterIP service;
9. delete the EKS cluster even when the Job fails.

Use a shell `trap` that calls `eksctl delete cluster --wait`.

- [ ] **Step 7: Verify GREEN and commit**

```bash
PYTHONPATH=examples/ai-ml/qwen-pii-finetuning \
  /tmp/qwen-pii-plan-venv/bin/pytest \
  examples/ai-ml/qwen-pii-finetuning/tests -q
bash -n examples/ai-ml/qwen-pii-finetuning/launch/eks/run.sh
git add examples/ai-ml/qwen-pii-finetuning/launch/eks \
  examples/ai-ml/qwen-pii-finetuning/tests/test_eks_manifests.py
git commit -m "feat: add ephemeral EKS MLflow training path"
```

---

### Task 8: Run local verification and freeze the dataset

**Files:**
- Create: `examples/ai-ml/qwen-pii-finetuning/data/dataset-manifest.json`
- Modify: `examples/ai-ml/qwen-pii-finetuning/data/review-sample.jsonl`
- Create at runtime: `examples/ai-ml/qwen-pii-finetuning/generated/*.jsonl`

**Interfaces:**
- Produces immutable hashes consumed by both AWS runs.

- [ ] **Step 1: Run the complete local Python test suite**

```bash
PYTHONPATH=examples/ai-ml/qwen-pii-finetuning \
  /tmp/qwen-pii-plan-venv/bin/pytest \
  examples/ai-ml/qwen-pii-finetuning/tests -q
```

Expected: all tests PASS.

- [ ] **Step 2: Generate the final dataset**

Run the generator with seed 42 and the canonical config. Copy only the manifest
and review sample into tracked `data/`.

Expected manifest:

```json
{
  "seed": 42,
  "counts": {"train": 1600, "validation": 200, "test": 400},
  "languages": {
    "train": {"ko": 1280, "en": 320},
    "validation": {"ko": 160, "en": 40},
    "test": {"ko": 320, "en": 80}
  }
}
```

The real manifest also contains per-type counts and SHA-256 values.

- [ ] **Step 3: Run privacy assertions**

Search the generated data for:

- non-`example.com` email domains;
- checksum-valid cards/RRNs;
- account IDs, ARNs, access-key patterns, or repository paths;
- duplicate IDs across splits.

Expected: zero findings.

- [ ] **Step 4: Commit the frozen manifest**

```bash
git add examples/ai-ml/qwen-pii-finetuning/data
git commit -m "test: freeze Qwen PII dataset manifest"
```

---

### Task 9: Provision and execute the SageMaker AI experiment

**Files:**
- Create at runtime: `examples/ai-ml/qwen-pii-finetuning/results/resource-inventory.json`
- Create: `examples/ai-ml/qwen-pii-finetuning/results/sagemaker-smoke.json`
- Create: `examples/ai-ml/qwen-pii-finetuning/results/sagemaker-full.json`

**Interfaces:**
- Produces measured managed-training results and exported MLflow metadata.

- [ ] **Step 1: Run preflight**

```bash
bash examples/ai-ml/qwen-pii-finetuning/launch/aws/preflight.sh
```

Expected: PASS for credentials, tools, quotas, DLC, and collision checks.

- [ ] **Step 2: Provision tagged resources**

```bash
bash examples/ai-ml/qwen-pii-finetuning/launch/aws/provision.sh
```

Expected:

- bucket is encrypted and private;
- MLflow App reaches `Created`;
- Unified Studio project reaches `ACTIVE`;
- inventory contains every resource created.

- [ ] **Step 3: Upload the exact dataset and source bundle**

Upload the three JSONL files, manifest, config, lock, and source tarball under:

```text
s3://${BUCKET_NAME}/qwen-pii/${EXPERIMENT_ID}/
```

Read back the objects and verify their SHA-256 metadata matches the local
manifest before submitting a training job.

- [ ] **Step 4: Run the 10-step SageMaker smoke job**

```bash
PYTHONPATH=examples/ai-ml/qwen-pii-finetuning \
  python3 examples/ai-ml/qwen-pii-finetuning/launch/sagemaker_train.py \
  --mode smoke \
  --inventory examples/ai-ml/qwen-pii-finetuning/results/resource-inventory.json
```

Expected:

- Training Job status `Completed`;
- model loads in 4-bit;
- one backward pass and checkpoint completes;
- baseline and tuned aggregate metrics exist;
- MLflow contains one `sagemaker-smoke` run;
- no raw PII appears in CloudWatch logs.

- [ ] **Step 5: Inspect failure evidence before continuing**

If smoke fails, capture the sanitized failure reason, CloudWatch error class,
GPU memory peak, and package versions. Fix the root cause, rerun local tests,
commit the fix, and use the one allowed retry.

- [ ] **Step 6: Run the 80-step full job**

Use `--mode full`.

Expected:

- status `Completed`;
- MLflow contains baseline and tuned metrics;
- `sagemaker-full.json` records durations, metrics, instance type, dataset hash,
  and training job ARN without account ID;
- adapter weights remain in S3 only until export/teardown.

- [ ] **Step 7: Export managed MLflow results**

Use the MLflow App ARN through `sagemaker-mlflow`, download aggregate
metric artifacts and run metadata, and verify the exported dataset hash equals
the committed manifest.

- [ ] **Step 8: Stop and delete managed MLflow after export**

Delete the MLflow App and poll until it no longer appears in
`list-mlflow-apps`. Preserve its entry in the inventory with
`deleted_at`.

- [ ] **Step 9: Commit sanitized SageMaker results**

```bash
git add examples/ai-ml/qwen-pii-finetuning/results/sagemaker-*.json
git commit -m "test: record SageMaker Qwen PII results"
```

---

### Task 10: Execute the EKS with MLflow experiment

**Files:**
- Create: `examples/ai-ml/qwen-pii-finetuning/results/eks-smoke.json`
- Create: `examples/ai-ml/qwen-pii-finetuning/results/eks-full.json`
- Create: `examples/ai-ml/qwen-pii-finetuning/results/eks-mlflow-export.json`

**Interfaces:**
- Produces measured Kubernetes/MLflow results for the same dataset and config.

- [ ] **Step 1: Run the EKS smoke workflow**

```bash
bash examples/ai-ml/qwen-pii-finetuning/launch/eks/run.sh smoke
```

Expected:

- new cluster name matches the experiment ID;
- no existing cluster is touched;
- one L40S GPU is allocatable;
- MLflow is Ready and ClusterIP-only;
- smoke Job completes;
- MLflow export is downloaded;
- the cluster is deleted by the trap.

- [ ] **Step 2: Verify cluster deletion before the full run**

Run:

```bash
aws eks describe-cluster \
  --region ap-northeast-2 \
  --name "$EXPERIMENT_ID-smoke"
```

Expected: `ResourceNotFoundException`.

- [ ] **Step 3: Inspect smoke metrics and logs**

Verify the EKS smoke run uses the same:

- model ID;
- dependency lock hash;
- train/validation/test hashes;
- QLoRA hyperparameters;
- seed;
- evaluation code version.

Search logs for all generated review-sample PII literals. Expected: no matches.

- [ ] **Step 4: Run the EKS full workflow**

```bash
bash examples/ai-ml/qwen-pii-finetuning/launch/eks/run.sh full
```

Expected: Job completes, MLflow export downloads, and the full cluster is
deleted.

- [ ] **Step 5: Verify full cluster deletion**

Expected: EKS cluster and its managed node group are absent; no running EC2
instance carries the experiment ID.

- [ ] **Step 6: Commit sanitized EKS results**

```bash
git add examples/ai-ml/qwen-pii-finetuning/results/eks-*.json
git commit -m "test: record EKS MLflow Qwen PII results"
```

---

### Task 11: Aggregate results and prove cloud teardown

**Files:**
- Create: `examples/ai-ml/qwen-pii-finetuning/src/export_results.py`
- Create: `examples/ai-ml/qwen-pii-finetuning/results/experiment-summary.json`
- Create: `examples/ai-ml/qwen-pii-finetuning/results/comparison.csv`
- Create: `examples/ai-ml/qwen-pii-finetuning/results/README.md`
- Create: `examples/ai-ml/qwen-pii-finetuning/results/teardown-report.json`
- Create: `scripts/__tests__/sagemaker-qwen-pii-results.test.mjs`

**Interfaces:**
- Consumes the four full/smoke result files and live Price List API values.
- Produces the only values permitted in documentation tables.
- Produces proof that no experiment resources remain.

- [ ] **Step 1: Write the failing result contract**

The Node test must assert:

```js
assert.equal(summary.modelId, 'Qwen/Qwen3-30B-A3B-Instruct-2507')
assert.deepEqual(summary.dataset.counts, { train: 1600, validation: 200, test: 400 })
assert.ok(Number.isFinite(summary.sagemaker.tuned.microF1))
assert.ok(Number.isFinite(summary.eks.tuned.microF1))
assert.equal(summary.tokenization.roundTripRate, 1)
assert.equal(summary.teardown.remainingResourceCount, 0)
```

- [ ] **Step 2: Run test and verify RED**

Expected: FAIL because the summary does not exist.

- [ ] **Step 3: Implement deterministic aggregation**

`export_results.py` must:

- load result JSON and reject mismatched dataset/config hashes;
- query the Price List API for current Seoul
  `ml.g6e.4xlarge-Training`, `g6e.4xlarge`, and MLflow App usage/storage rates;
- use `Decimal` for cost math;
- calculate base-to-tuned deltas in code;
- write sorted JSON and stable CSV;
- exclude account IDs, ARNs, bucket names, cluster names, and PII values.

- [ ] **Step 4: Run final AWS teardown**

```bash
bash examples/ai-ml/qwen-pii-finetuning/launch/aws/teardown.sh
bash examples/ai-ml/qwen-pii-finetuning/launch/aws/verify_cleanup.sh
```

Expected:

- Unified Studio project deleted;
- S3 bucket absent;
- IAM roles absent;
- managed MLflow absent;
- CloudWatch experiment log groups absent;
- EKS/EC2 experiment resources absent;
- `remainingResourceCount` equals 0.

- [ ] **Step 5: Generate and validate summary**

Run `export_results.py`, then:

```bash
node --test scripts/__tests__/sagemaker-qwen-pii-results.test.mjs
```

Expected: PASS.

- [ ] **Step 6: Write the result README**

Explain:

- actual base and tuned quality;
- whether the five-point F1 target was met;
- per-type gains/regressions;
- leak and over-redaction behavior;
- SageMaker versus EKS operational differences;
- measured durations and calculated costs;
- teardown evidence.

Do not claim equivalence if the two runs differ due to startup, cache, or
infrastructure effects.

- [ ] **Step 7: Commit**

```bash
git add examples/ai-ml/qwen-pii-finetuning/results \
  examples/ai-ml/qwen-pii-finetuning/src/export_results.py \
  scripts/__tests__/sagemaker-qwen-pii-results.test.mjs
git commit -m "docs: publish Qwen PII experiment results"
```

---

### Task 12: Add the bilingual SageMaker AI deep dive

**Files:**
- Create: `ko/ai-ml/sagemaker-ai/README.md`
- Create: `ko/ai-ml/sagemaker-ai/01-training-architecture.md`
- Create: `ko/ai-ml/sagemaker-ai/02-qwen-pii-finetuning.md`
- Create: `ko/ai-ml/sagemaker-ai/03-results-and-operations.md`
- Create matching files under `en/ai-ml/sagemaker-ai/`
- Create six matching quiz files under `ko/quizzes/ai-ml/sagemaker-ai/` and `en/quizzes/ai-ml/sagemaker-ai/`

**Interfaces:**
- Consumes only `experiment-summary.json`, comparison CSV, package source, and primary AWS/Qwen documentation.
- Produces a managed SageMaker learning path.

- [ ] **Step 1: Add the series README in both locales**

Cover:

- SageMaker AI versus EKS responsibility boundaries;
- training jobs, storage, roles, managed MLflow, and teardown;
- series navigation;
- prerequisites and actual tested region/date;
- links to the runnable package.

- [ ] **Step 2: Write Part 1 — training architecture**

Include:

- SageMaker AI terminology and architecture;
- the exact S3 → Training Job → model output → managed MLflow flow;
- IAM and log redaction requirements;
- why QLoRA is used for the 30B-class model;
- a decision table comparing SageMaker, EKS, and notebook-only execution;
- links to current primary AWS documentation.

- [ ] **Step 3: Write Part 2 — Qwen PII fine-tuning**

Include:

- synthetic dataset schema and generator;
- TSV extractor target;
- deterministic tokenization stages;
- exact locked configuration;
- smoke/full launch commands;
- MLflow metrics;
- failure diagnosis for OOM, parse failure, download failure, and tracking
  authentication;
- no model weights or real PII in the repository.

- [ ] **Step 4: Write Part 3 — measured results and operations**

Generate every numeric table from `experiment-summary.json`. Include:

- base versus tuned metrics;
- per-type results;
- leak/over-redaction/parse/round-trip metrics;
- runtime, peak memory, and cost;
- SageMaker versus EKS operational comparison;
- teardown proof;
- honest explanation of unmet targets.

- [ ] **Step 5: Add quizzes**

Each numbered page gets five questions covering architecture, QLoRA,
TSV-versus-direct-redaction, metric interpretation, IAM/logging, and cleanup.
Use the repository's `<details><summary>` conventions.

- [ ] **Step 6: Validate links and commit**

```bash
node scripts/validate-local-links.mjs
git add ko/ai-ml/sagemaker-ai en/ai-ml/sagemaker-ai \
  ko/quizzes/ai-ml/sagemaker-ai en/quizzes/ai-ml/sagemaker-ai
git commit -m "docs: add SageMaker AI Qwen fine-tuning guide"
```

---

### Task 13: Add the bilingual MLflow on EKS experiment chapter

**Files:**
- Modify: `ko/ai-ml/mlflow/README.md`
- Modify: `en/ai-ml/mlflow/README.md`
- Create: `ko/ai-ml/mlflow/04-qwen-pii-finetuning-on-eks.md`
- Create: `en/ai-ml/mlflow/04-qwen-pii-finetuning-on-eks.md`
- Create: `ko/quizzes/ai-ml/mlflow/04-qwen-pii-finetuning-on-eks-quiz.md`
- Create: `en/quizzes/ai-ml/mlflow/04-qwen-pii-finetuning-on-eks-quiz.md`

**Interfaces:**
- Consumes the common package and measured EKS MLflow export.
- Produces the self-managed comparison path requested by the user.

- [ ] **Step 1: Extend the MLflow series navigation**

Add Part 4 to both MLflow READMEs with a clear transition from tracking server
deployment to a real LLM fine-tuning run.

- [ ] **Step 2: Write the EKS chapter**

Cover:

- ephemeral cluster architecture;
- GPU AMI/driver/device plugin checks;
- internal MLflow server and why it is deliberately ephemeral;
- Kubernetes Job resource limits, deadline, and retry policy;
- common config parity with SageMaker;
- experiment export before deletion;
- measured EKS results;
- operational trade-offs versus managed MLflow.

- [ ] **Step 3: Add the quiz**

Use five questions about MLflow's role, GPU scheduling, `backoffLimit: 0`,
artifact export, and differences between managed and self-hosted MLflow.

- [ ] **Step 4: Commit**

```bash
git add ko/ai-ml/mlflow en/ai-ml/mlflow \
  ko/quizzes/ai-ml/mlflow en/quizzes/ai-ml/mlflow
git commit -m "docs: add EKS MLflow Qwen experiment"
```

---

### Task 14: Add the bilingual SageMaker Unified Studio data deep dive

**Files:**
- Create: `ko/data-on-eks/sagemaker-unified-studio/README.md`
- Create: `ko/data-on-eks/sagemaker-unified-studio/01-domains-projects-catalog.md`
- Create: `ko/data-on-eks/sagemaker-unified-studio/02-pii-dataset-workflow.md`
- Create matching files under `en/data-on-eks/sagemaker-unified-studio/`
- Create four matching quiz files under `ko/quizzes/data-on-eks/sagemaker-unified-studio/` and `en/quizzes/data-on-eks/sagemaker-unified-studio/`
- Modify: `ko/data-on-eks/README.md`
- Modify: `en/data-on-eks/README.md`

**Interfaces:**
- Consumes actual project creation/deletion evidence and the versioned dataset manifest.
- Produces the managed data/AI workspace counterpart within the Data section.

- [ ] **Step 1: Write the section README**

State explicitly that Unified Studio is a managed AWS workspace, not an
application hosted on EKS. Explain why it appears in Data on EKS: it governs
and connects the data assets consumed by EKS and SageMaker workloads.

- [ ] **Step 2: Write Part 1 — domains, project profiles, projects, and catalog**

Cover:

- V2 domain and project boundaries;
- All capabilities project profile;
- user/project membership;
- catalog and governed asset discovery;
- SageMaker AI, EMR, Glue, Athena, Redshift, and Bedrock relationships;
- least-privilege and project deletion behavior;
- actual validation steps performed in the experiment.

- [ ] **Step 3: Write Part 2 — PII dataset workflow**

Use the Qwen experiment to show:

- deterministic synthetic dataset creation;
- manifest/hash publication;
- S3 asset access from a project;
- SageMaker Training consumption;
- MLflow result discovery;
- lineage boundaries;
- deletion and retention;
- why raw PII and model completions are excluded from catalog metadata.

- [ ] **Step 4: Update Data overview**

Add a fifth category for governed data and AI workspace, update “Currently
Covered” and “Next Steps,” and preserve the explanation that managed and EKS
approaches are complementary.

- [ ] **Step 5: Add quizzes and commit**

```bash
git add ko/data-on-eks en/data-on-eks \
  ko/quizzes/data-on-eks/sagemaker-unified-studio \
  en/quizzes/data-on-eks/sagemaker-unified-studio
git commit -m "docs: add SageMaker Unified Studio data guide"
```

---

### Task 15: Update navigation, cross-links, and bilingual content contracts

**Files:**
- Modify: `ko/SUMMARY.md`
- Modify: `en/SUMMARY.md`
- Modify: `ko/README.md`
- Modify: `en/README.md`
- Modify: relevant cross-links in `ko/ai-ml/05-model-training.md`, `en/ai-ml/05-model-training.md`, Kubeflow comparison pages, and MLflow pages
- Create: `scripts/__tests__/sagemaker-qwen-pii-content.test.mjs`

**Interfaces:**
- Produces matched ko/en navigation and enforceable result/content requirements.

- [ ] **Step 1: Write the failing bilingual content contract**

Assert both locales contain:

- SageMaker AI series and all three numbered pages;
- Unified Studio series and both numbered pages;
- MLflow Part 4;
- matching quiz links;
- exact model ID;
- `TYPE<TAB>ORIGINAL` explanation;
- leak rate, F1, cost, and teardown result headings;
- no draft markers, “expected result” prose, or fabricated numeric values.

- [ ] **Step 2: Run test and verify RED**

```bash
node --test scripts/__tests__/sagemaker-qwen-pii-content.test.mjs
```

Expected: FAIL before navigation and cross-links are complete.

- [ ] **Step 3: Update SUMMARY and root README files**

Add the same hierarchy and learning/quiz links in Korean and English. Keep
existing numbering stable and append the new deep dives after MLflow and Flink
respectively.

- [ ] **Step 4: Add comparison cross-links**

From model training and Kubeflow pages, link to SageMaker AI as the managed
alternative. From Data on EKS, link to Unified Studio. From both experiment
chapters, cross-link the counterpart environment and shared result page.

- [ ] **Step 5: Verify GREEN and commit**

```bash
node --test scripts/__tests__/sagemaker-qwen-pii-content.test.mjs
git add ko en scripts/__tests__/sagemaker-qwen-pii-content.test.mjs
git commit -m "docs: integrate SageMaker AI and Unified Studio navigation"
```

---

### Task 16: Run full verification and final teardown audit

**Files:**
- Modify only if verification exposes a defect in approved scope.
- Verify: all experiment, documentation, result, and teardown files.

- [ ] **Step 1: Run all Python experiment tests**

```bash
PYTHONPATH=examples/ai-ml/qwen-pii-finetuning \
  /tmp/qwen-pii-plan-venv/bin/pytest \
  examples/ai-ml/qwen-pii-finetuning/tests -q
```

Expected: PASS.

- [ ] **Step 2: Run focused Node contracts**

```bash
node --test scripts/__tests__/sagemaker-qwen-pii-results.test.mjs
node --test scripts/__tests__/sagemaker-qwen-pii-content.test.mjs
```

Expected: PASS.

- [ ] **Step 3: Run repository validation**

```bash
npm run docs:validate
```

Expected: all Node tests, local-link checks, and image checks PASS.

- [ ] **Step 4: Build Korean and English independently**

```bash
VITEPRESS_BUILD_LOCALE=ko NODE_OPTIONS=--max-old-space-size=8192 \
  node node_modules/vitepress/bin/vitepress.js build . \
  --outDir /tmp/vitepress-sagemaker-qwen-ko
VITEPRESS_BUILD_LOCALE=en NODE_OPTIONS=--max-old-space-size=8192 \
  node node_modules/vitepress/bin/vitepress.js build . \
  --outDir /tmp/vitepress-sagemaker-qwen-en
```

Expected: both builds exit 0 and generate the new SageMaker AI, MLflow, and
Unified Studio pages.

- [ ] **Step 5: Re-run cleanup proof**

```bash
bash examples/ai-ml/qwen-pii-finetuning/launch/aws/verify_cleanup.sh
```

Expected: `remainingResourceCount: 0`.

- [ ] **Step 6: Audit committed content for sensitive data**

Run searches for:

- 12-digit AWS account IDs;
- `AKIA` access-key patterns;
- ARNs;
- experiment bucket/cluster names;
- review-sample raw values outside the approved sample;
- model weights and adapter file extensions.

Expected: no secrets, account identifiers, cloud resource names, full dataset,
or model weights are committed.

- [ ] **Step 7: Review final diff**

```bash
git diff --check origin/main...HEAD
git status --short
git diff --stat origin/main...HEAD
```

Expected: no whitespace errors, a clean worktree, and only approved ko/en docs,
quizzes, experiment package, tests, spec, and plan.

- [ ] **Step 8: Commit verification fixes if any**

```bash
git add docs/superpowers examples/ai-ml/qwen-pii-finetuning scripts/__tests__ \
  ko en
git commit -m "test: verify SageMaker Qwen PII documentation"
```

Skip the commit when verification produces no changes.

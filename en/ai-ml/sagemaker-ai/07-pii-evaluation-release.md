# Workshop: evaluating PII models and redaction pipelines

> **Last Updated**: September 15, 2026

The executable example uses synthetic records and manually constructed predictions on CPU. Its numbers are not trained-model performance.

A falling training loss does not establish good PII removal. A model may find names but miss emails, or mask document numbers that the annotation policy considers non-sensitive. This chapter evaluates **both entity extraction and the resulting replacements**, then connects errors to the next data experiment.

Read the [QLoRA workshop](05-qlora-finetuning-workshop.md) and [augmentation workshop](06-data-augmentation-workshop.md) first. Commands start at the repository root and use Python 3.12.

## 1. Separate model and processing responsibilities

The example model emits `TYPE<TAB>ORIGINAL` candidates rather than rewriting the entire document.

| Stage | Input → output | What to check |
| --- | --- | --- |
| Extraction | Source → type/value candidates | Omissions, wrong types, invented values |
| Validation | Candidates → allowed source-matching candidates | Syntax, length, allowed types, source match |
| Replacement | Source/candidates → masked text, mapping, spans | Repetition, partial coverage, collisions, overlaps |
| Residual checks | Masked result → approval or review | Separate rules/detectors, policy, unsupported inputs |
| Delivery | Approved document → downstream system | Mapping exclusion, access control, logging scope |

Source matching establishes that a candidate occurs in the source. It does not establish its semantic type or the absence of other PII. Combining detectors also does not make their errors independent.

`pseudonymize_text()` creates reversible token mappings. Keeping a mapping for `[PERSON_1]` serves a different purpose from removing a value without a restoration feature. Discarding a mapping alone does not establish that the remaining context cannot identify someone.

## 2. Assign training, validation, and final-test roles

1. **Train:** update parameters and apply training augmentation.
2. **Validation:** select rank, learning rate, epochs/steps, data mixtures, and output rules.
3. **Locked test:** evaluate the selected model and processing policy.
4. **Challenge set:** examine OCR, long documents, unfamiliar templates, rare types, embedded instructions, and other difficult conditions separately.

If failures on a final test influence the next model selection, that test has entered development. Record the change and prepare another evaluation version. Document whether separation is by document family, customer, template, time, or another axis.

**The historical `src/train.py` evaluates baseline and tuned predictions on `test_records` in every run.** Do not use that behavior unchanged as a repeated HPO loop. A tuning implementation needs validation-based candidate selection and a separate, recorded final-test step. The CPU exercise below does not run that launcher.

## 3. Reproduce “higher F1, remaining problems” on CPU

Use two documents:

- A positive document whose synthetic name and `example.com` email are annotated.
- A negative document whose document number is not PII under this policy.

The baseline finds only the name. The candidate finds the name and email but incorrectly labels the negative document's number as an account. Predictions are constructed manually, without invoking a model, so the metric arithmetic can be checked. Both language editions use the same synthetic Korean fixture.

```bash
cd examples/ai-ml/qwen-pii-finetuning
mkdir -p "${XDG_CACHE_HOME:-$HOME/.cache}"
export PII_EVAL_DIR="$(mktemp -d "${XDG_CACHE_HOME:-$HOME/.cache}/pii-evaluation.XXXXXX")"
python3 - <<'PY'
import json
import os
from pathlib import Path

out = Path(os.environ["PII_EVAL_DIR"])
records = [
    {
        "id": "positive-1",
        "source_text": "담당자 김가상, 이메일 synthetic.ko.01@example.com",
        "entities": [
            {"type": "PERSON", "original": "김가상"},
            {"type": "EMAIL", "original": "synthetic.ko.01@example.com"},
        ],
        "target_tsv": "PERSON\t김가상\nEMAIL\tsynthetic.ko.01@example.com",
    },
    {
        "id": "negative-1",
        "source_text": "문서번호 DOC-2026-001의 처리 상태를 확인합니다.",
        "entities": [],
        "target_tsv": "",
    },
]
baseline = [
    {"id": "positive-1", "content": "PERSON\t김가상", "parse_success": True},
    {"id": "negative-1", "content": "", "parse_success": True},
]
candidate = [
    {
        "id": "positive-1",
        "content": records[0]["target_tsv"],
        "parse_success": True,
    },
    {
        "id": "negative-1",
        "content": "ACCOUNT\tDOC-2026-001",
        "parse_success": True,
    },
]
for name, rows in (
    ("gold", records), ("baseline", baseline), ("candidate", candidate)
):
    with (out / f"{name}.jsonl").open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
PY

for phase in baseline candidate; do
  python3 -m src.evaluate \
    --test-jsonl "$PII_EVAL_DIR/gold.jsonl" \
    --predictions-jsonl "$PII_EVAL_DIR/$phase.jsonl" \
    --output-json "$PII_EVAL_DIR/$phase-metrics.json" \
    --environment cpu-demo --phase "$phase-demo" \
    --model-id synthetic-fixture-no-model \
    --duration-seconds 0 --hourly-usd 0
done

python3 - <<'PY'
import json
import os
from pathlib import Path

out = Path(os.environ["PII_EVAL_DIR"])
for phase in ("baseline", "candidate"):
    m = json.loads((out / f"{phase}-metrics.json").read_text())["metrics"]
    print(phase, json.dumps({
        "entity": m["entity"],
        "leaked_documents": m["documents"]["leaked"],
        "extra_pairs": m["entities"]["over_redacted"],
        "round_trip": m["tokenization"]["round_trip_rate"],
    }))
PY
```

`--test-jsonl` is the evaluation CLI's argument name. Here it points to a hand-written exercise file, not a production final holdout.

Expected results:

| Metric | Baseline | Candidate |
| --- | ---: | ---: |
| TP / FP / FN | 1 / 0 / 1 | 2 / 1 / 0 |
| Precision | 1 | 2/3 |
| Recall | 1/2 | 1 |
| Entity F1 | 2/3 | 0.8 |
| Documents with uncovered gold | 1 of 2 | 0 of 2 |
| Extra extraction pairs | 0 | 1 |
| Round-trip rate | 1 | 1 |

The candidate improves F1 but introduces document-number masking. Both predictions round-trip correctly: **restoration success cannot substitute for PII detection quality.** Zero duration and hourly price describe this manual fixture; they do not claim GPU training is free.

## 4. Check the unit behind each metric

The package's `entity` and `per_type` metrics compare document-level `(TYPE, ORIGINAL)` sets. Repeated identical pairs within a document count once. This is not NER F1 based on independent span annotations.

| Metric | Use | Limitation to inspect |
| --- | --- | --- |
| Per-type recall | Find omitted PII categories | Report the number of evaluated rare entities |
| Per-type precision | Identify non-sensitive text being masked | Requires consistent annotation policy |
| Document leak rate | Documents with any uncovered gold | Cannot measure PII absent from the gold labels |
| Entity leak rate | Coverage of all matched occurrences of a gold value | Infers spans by value search rather than offset gold |
| `over_redaction_rate` | FP / predicted pairs | Not the fraction of unnecessarily removed characters |
| `hallucination_rate` | Allowed TSV candidates absent from the source | Excludes disallowed types and ordinary prose from its denominator |
| Parse success | Caller-provided format-processing status | The current helper accepts some outputs with only a subset of valid rows |

Design a strict serving parser to validate every row and return explicit failures for malformed rows, truncated completions, and input-length violations. Silently dropping bad rows must not turn into “no PII found.” The current `parse.success_rate` does not prove that strict behavior is implemented.

Without gold annotations on live documents, the same gold-based leak rate is unavailable. Observe reviewed samples, residual detectors, and abstention/review rates while identifying what each actually measures.

## 5. Turn errors into the next data experiment

Investigate document-level errors in an access-controlled evaluation workspace. General logs should carry error categories, length buckets, language, template IDs, and aggregates rather than source text.

| Observed error | Inspect first | Next experiment |
| --- | --- | --- |
| Finds names but misses accounts | Per-type counts and missing annotation | Add account-context training cases |
| Fails on spaced names or OCR | Source/label surface-form alignment | Augment source and labels together |
| Labels document numbers as accounts | Negative coverage and contextual contrasts | Add matched positive/negative numeric contexts |
| Misses PII at the end of long documents | Prompt truncation and completion budget | Evaluate chunk boundaries, overlap, and offset reconstruction |
| Poor results on unfamiliar names | Entity overlap between train/test | Entity-held-out evaluation and new training families |
| Poor results on new layouts | Template separation | Template-held-out evaluation and approved training templates |
| Follows instructions embedded in the source | Treatment of documents as data | Synthetic embedded-instruction cases and output-schema checks |
| Loss decreases while recall declines | Contaminated validation, overfitting, output limits | Compare checkpoints and early-stopping criteria |

Do not copy failed test examples into training and advertise improvements on the same test. Record that the error-analysis set has influenced development and identify a new final evaluation set.

## 6. Design training and inference length together

`max_sequence_length=1024` does not mean 1,024 document characters. Chat templates, system instructions, source text, and target completions consume the tokenizer's budget. Korean, English, and numbers do not have identical character-to-token ratios.

- Verify that truncation does not remove all supervised target tokens during training.
- Do not treat PII in a truncated-away input region as absent during inference.
- Chunking requires source offsets, duplicate reconciliation, boundary-spanning entities, and repeated-occurrence handling.
- Test deliberately boundary-crossing PII rather than assuming overlap is sufficient.
- Report input overflow and incomplete output explicitly rather than labeling a partial result complete.

## 7. Write an acceptance table before measuring

The following is a **template for a team's evidence and criteria**, not achieved repository performance or universal numeric thresholds.

| Area | Evidence | Action when insufficient |
| --- | --- | --- |
| Labels and separation | Annotation version, family/split/hash, subgroup counts | Rebuild evaluation |
| Candidate selection | Validation comparisons, changed variable, decision | Run another controlled experiment |
| Final quality | Locked-test per-type results and error counts | Hold deployment |
| Output contract | Empty, malformed, and truncated response tests | Fix parsing/abstention |
| Processing policy | Replacement spans, mapping lifecycle, residual checks | Fix policy or processing |
| Operational behavior | Latency, memory, timeouts, throughput by length | Adjust capacity and length limits |
| Reproduction/recovery | Base/tokenizer revision, adapter hash, environment, prior version | Complete packaging |

Choose task-specific F1, recall, and latency criteria **before evaluation**. Zero observed errors in a small sample do not establish a zero real error rate. Show numerators and denominators for subgroup results.

## 8. From SageMaker artifacts to a serving package

A Training Job reaching `Completed` describes training-job termination. Endpoint creation, adapter loading, output validation, and approval of the redacted result are separate steps.

1. Preserve adapters, configuration, and aggregate results from `/opt/ml/model` and MLflow.
2. Record the exact base model/tokenizer revision, chat template, quantization settings, and parser version alongside the adapter.
3. Test reloading and deterministic decoding in the intended environment. An adapter alone is not a complete standalone base model.
4. Observe length, output format, and error rates in a shadow or limited canary workflow.
5. Version the **model + tokenizer + parser + policy** combination so it can be rolled back together.

This chapter does not implement or deploy an endpoint or strict release wrapper. A real deployment must also test source/completion/mapping exposure through CloudWatch, MLflow autolog/tracing, errors, and request tracing. Adapters are influenced by their training data and need their own sharing review.

## Check your understanding

1. Why not immediately deploy the higher-F1 candidate? **It adds masking on a negative document, and two synthetic documents are not representative evaluation.**
2. Does 100% round-trip mean all PII was removed? **No. Only restoration of the replaced values may have succeeded.**
3. What if the same test selected several ranks? **It participated in selection and is no longer an independent final test.**
4. Is a source-matching candidate necessarily PII? **No; the document number is a counterexample.**
5. Can this evaluator's leak rate be calculated from model outputs alone on unlabelled traffic? **No; it requires gold annotations.**

## References

- [Repository evaluation CLI](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/src/evaluate.py)
- [Actual metric implementation](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/src/metrics.py)
- [Replacement and reconstruction](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/src/pii_tokens.py)
- [PEFT checkpoint format](https://huggingface.co/docs/peft/v0.17.0/en/developer_guides/checkpoint)
- [SageMaker container directories](https://docs.aws.amazon.com/sagemaker/latest/dg/amazon-sagemaker-toolkits.html)
- [Presidio Anonymizer operations and restoration](https://github.com/microsoft/presidio/blob/main/presidio-anonymizer/README.md)

Previous: [Data augmentation workshop](06-data-augmentation-workshop.md) · [Learning path](README.md)

[Workshop quiz](../../quizzes/ai-ml/sagemaker-ai/07-pii-evaluation-release-quiz.md)

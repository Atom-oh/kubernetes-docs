# Workshop: synthetic PII data and augmentation

> Reviewed on 2026-09-15. This synthetic-data exercise runs with Python 3.12 and needs no model weights, AWS account, or GPU.

Augmentation should add **input conditions on which the system actually fails**, rather than merely increase the number of files. Duplicating documents or generating misaligned labels can increase training work while making evaluation less trustworthy.

Define the annotation policy, split document families first, then apply label-preserving transformations. Start with the small CPU exercise and use the final sections to plan a larger domain dataset.

## 1. Define the learning target

Source text, entity annotations, and the model's target must agree.

```json
{
  "id": "synthetic-train-example",
  "source_text": "신청인 김가상, 이메일 synthetic.01@example.com",
  "entities": [
    {"type": "PERSON", "original": "김가상"},
    {"type": "EMAIL", "original": "synthetic.01@example.com"}
  ],
  "target_tsv": "PERSON\t김가상\nEMAIL\tsynthetic.01@example.com"
}
```

`source_text` is the input document; `target_tsv` is the assistant completion to supervise. `entities` supports auditing and evaluation. This is different from training a model to generate the entire masked document.

Write an annotation guide first.

| Decision | Example | Failure if left ambiguous |
| --- | --- | --- |
| Type semantics | Personal contact is PHONE; a company switchboard is negative under this policy | Conflicting labels for similar strings |
| Exact boundaries | Preserve name spacing and phone separators from the source | Source/target mismatch |
| Contextual classification | Distinguish document numbers from accounts | Treating all numbers as sensitive |
| Repetition/overlap | Repeated names, names inside addresses | Annotation/replacement disagreement |
| No entities | `entities=[]`, `target_tsv=""` | Learning to extract something from every document |
| Uncertain cases | Unreadable or unsupported inputs, ambiguous context | Guessed gold enters training |

The switchboard rule is this example's policy, not a universal organizational rule. Document-level `(TYPE, ORIGINAL)` labels cannot independently annotate different occurrences of the same string. If occurrences have different meanings, extend the offset/span schema, evaluator, and replacement code together.

## 2. Distinguish synthesis from augmentation

- **Synthesis:** create new documents from templates, synthetic values, or a generative model.
- **Augmentation:** change values, wording, layout, or noise while preserving the intended labels of an approved training example.
- **Validation:** check that transformed source and targets still agree. Successful generation does not guarantee correct labels.

Treat external model outputs as candidate data too. Do not default to sending source values to an external API or accepting generated outputs as gold without review.

## 3. Split families before augmenting

Group an original and its translations, OCR variants, and paraphrases under one `family_id`. Assign the family to train/validation/test first, then generate descendants only for training families.

```text
family-001 → train      → base + context + layout
family-002 → validation → base
family-003 → test       → base
```

Randomly splitting after augmentation can put nearly identical documents in training and test. A grouping key requires provenance: assigning a new record ID does not create an independent customer or source family.

| Separation axis | Leakage it addresses | Additional evaluation |
| --- | --- | --- |
| Family | Original and descendants cross splits | New transformations/noise |
| Entity/customer | Same people/identifiers appear on both sides | Unseen names, identifiers, customers |
| Template | Memorization of layouts | Unseen templates |
| Domain/time | Reliance on a business/time distribution | New domains or future periods |

This CPU exercise checks **family separation and exact NFC-source duplicates**. Some names, templates, and domains are shared; it does not establish entity/template/domain independence.

## 4. Run the small augmentation exercise

Start at the repository root. The generator accepts only a new output directory, so do not pass an already-created directory itself to `--output-dir`.

```bash
cd examples/ai-ml/qwen-pii-finetuning
mkdir -p "${XDG_CACHE_HOME:-$HOME/.cache}/qwen-pii-lab"
export PII_AUG_RUN="$(mktemp -d "${XDG_CACHE_HOME:-$HOME/.cache}/qwen-pii-lab/run.XXXXXX")"
export PII_AUG_DIR="$PII_AUG_RUN/dataset"

python3 -m data.augmentation_lab --output-dir "$PII_AUG_DIR" --seed 42
python3 -m data.augmentation_lab --audit-dir "$PII_AUG_DIR"

python3 - <<'PY'
import json
import os
from collections import Counter
from pathlib import Path

root = Path(os.environ["PII_AUG_DIR"])
for split in ("train", "validation", "test"):
    rows = [
        json.loads(line)
        for line in (root / f"{split}.jsonl").read_text().splitlines()
    ]
    print(split, {
        "records": len(rows),
        "families": len({r["provenance"]["family_id"] for r in rows}),
        "negative": sum(not r["entities"] for r in rows),
        "languages": dict(Counter(r["language"] for r in rows)),
    })
PY
```

Outputs are `train.jsonl`, `validation.jsonl`, `test.jsonl`, and `augmentation-manifest.json`.

| Split | Families | Records | Korean / English | Negative records |
| --- | ---: | ---: | ---: | ---: |
| train | 24 | 72 | 36 / 36 | 36 |
| validation | 8 | 8 | 4 / 4 | 4 |
| test | 8 | 8 | 4 / 4 | 4 |

The 40 families are stratified by language and positive/negative status, assigning 6/2/2 families in each stratum. Training includes a base and two variants; validation/test retain bases only. The 50% negative and 50/50 language mix make the exercise comparable; they are not estimates of production prevalence.

The compact exercise covers PERSON, EMAIL, and PHONE. It has a different purpose from the historical nine-type generator. It cannot evaluate quality on RRN, CARD, or other types absent from this small set.

## 5. Read the lineage and transformations

Keep the existing loader's fields and add `provenance`.

| Field | Meaning |
| --- | --- |
| `id` | Distinct ID for each variant |
| `language`, `domain` | Aggregation/error-analysis categories |
| `provenance.family_id` | Shared family of original and variants |
| `provenance.split` | Assignment made before variants exist |
| `provenance.parent_id` | Base record from which a variant derives |
| `provenance.augmentation` | Applied transformation name |

Provenance and positive/negative status are audit metadata. As in the existing
loader, put only `source_text` in the user prompt; do not append split, gold
presence, or gold-label hints. Put `target_tsv` in the supervised assistant completion.

The executable has two variant kinds:

1. **Context wrapper:** change synthetic surrounding context while retaining PII values and annotation meaning.
2. **Layout/Unicode:** change field order/layout and use NFD for Korean variants. Render source and originals together, then regenerate TSV in the new source order.

NFD uses a decomposed representation, including Hangul jamo; NFC uses canonical
composition. Visually identical text can have different bytes, so exact-source
comparison first normalizes to NFC.

Negative records retain empty annotations and targets after transformation. Reordering or Unicode normalization must not invent entities. These variants do not claim to reproduce a real scanner or OCR engine's noise distribution.

## 6. Re-render source and labels for entity substitution

The following is a minimal same-type synthetic substitution pattern for a new training candidate. It is not a generic unrestricted string-replacement routine.

```python
def render_training_candidate(person, email):
    source = f"신청인: {person}\n이메일: {email}"
    entities = [
        {"type": "PERSON", "original": person},
        {"type": "EMAIL", "original": email},
    ]
    target = "\n".join(
        f"{entity['type']}\t{entity['original']}" for entity in entities
    )
    assert all(entity["original"] in source for entity in entities)
    return {"source_text": source, "entities": entities, "target_tsv": target}

base = render_training_candidate("김가상", "synthetic.base@example.com")
variant = render_training_candidate("이샘플", "synthetic.variant@example.com")
assert base["source_text"] != variant["source_text"]
```

In a real augmentation pipeline, use an approved training entity bank and record family, parent, seed, and operator version. Importing holdout values or failures into that bank can defeat the separation policy. This standalone teaching example is not an additional third operator automatically run by the preceding CLI.

## 7. Extend operators with explicit label checks

| Method | Failure condition to target | Required checks |
| --- | --- | --- |
| Same-type substitution | Memorized names/numbers | Preserve type and update every occurrence/gold |
| Layout rendering | Tables, forms, and support narratives | Field order/TSV agreement and missing-field checks |
| Bounded OCR/spacing | Separators, line breaks, Unicode forms | Gold and boundaries in the transformed source |
| Context paraphrasing | Reliance on one sentence template | Added/removed PII and semantic consistency |
| Back-translation | Limited phrasing | Changed names/addresses/numbers and reannotation |
| Hard negatives | Document numbers/amounts misclassified | Similar surface form with different context |
| Rare-type enrichment | Sparse RRN/CARD examples | Counts and contextual diversity per supported type |
| Long/boundary cases | Truncation and chunk-boundary misses | Token lengths, offsets, duplicates/boundaries |
| Embedded instructions | Following source text as instructions | Treat source as data; preserve TSV contract |

Paraphrases and back-translations can retain annotation errors beyond automated checks. Source-string presence does not prove semantic correctness or complete gold coverage. Review and approve candidates before including them in training.

## 8. Understand what the audit rejects

`--audit-dir` checks this lab's generated-data contract:

- File hashes/manifest and split/language/negative counts.
- Duplicate IDs and exact NFC-normalized sources.
- Family split ownership and parent/transformation relationships.
- Training variants incorrectly placed in validation/test.
- Allowed labels, source presence, and entities/TSV agreement.
- Agreement with deterministic regeneration from the seed.

The final check can reject an omitted gold label even when file hashes are recomputed. This is **reproducibility checking for a fixed synthetic exercise**, not a general gold validator for arbitrary customer documents. Hashes are not signatures authenticating the data producer.

Failing these conditions before training avoids misdiagnosing contaminated data as a model problem later. Near duplicates, annotation meaning, tokenizer lengths, and complete PII coverage still need separate checks.

## 9. Interpret the historical 2,200-record corpus

[Part 2](02-pii-data-tokenization.md) preserves generator 1.0.0, seed 42, and the original split hashes. CPU regeneration in this review reproduced those hashes.

Comparing full NFC-normalized sources reveals these exact intersections in the historical corpus:

| Split pair | Shared NFC sources |
| --- | ---: |
| train / validation | 22 |
| train / test | 36 |
| validation / test | 9 |

There are 51 unique source groups spanning two or more splits. Pairwise intersections count sources present in all three splits more than once, so their sum is not the unique-group total. This is a concrete reason not to relabel the historical corpus as a leakage-free evaluation set.

The new exercise neither overwrites historical data nor publishes revised model performance. A nine-type production dataset needs family/customer/template provenance and a new manifest/evaluation version, rather than a blind random repartition of old values/templates.

## 10. Extend the data into a SageMaker input release

The lab JSONL includes fields consumed by the existing `src.dataset` prompt/completion helpers. Its augmentation manifest is not a drop-in replacement for the uploader's `dataset-manifest.json`.

Prepare the following together for an actual training release:

1. Approved train/validation/test and annotation/augmentation policies.
2. The uploader's input manifest with actual counts and SHA-256 values.
3. A `config/experiment.yaml` reflecting dataset size, model, and training budget.
4. A source bundle containing that configuration and a matching local submission configuration.
5. A validated supported runtime and in-job observations of input hashes/counts.

The current bundler/uploader use fixed package paths. Generating `--output-dir` does not automatically wire that directory into SageMaker training. Integrate and validate a new dataset release in a separate working copy, then follow the [QLoRA workshop](05-qlora-finetuning-workshop.md) and [execution contract](03-sagemaker-mlflow-execution.md).

Compare original versus augmented training with the same validation set, decoding, and comparison budget. Identical step counts can still expose different numbers of examples or tokens when data size/length changes; record example/token budgets too.

## Check your understanding

1. Why is splitting after augmentation risky? **Variants of the same source can cross training/holdout boundaries.**
2. Does a new ID eliminate customer leakage? **No; check customer and source lineage.**
3. Can a name change leave TSV untouched? **No; source and gold must change together.**
4. Does this lab establish performance on unseen templates? **No; templates are shared and no model is evaluated.**
5. What if more augmentation hurts quality? **Inspect labels, duplicates, distribution changes, and training budgets; compare on validation.**

## References

- [Train/test separation and preprocessing leakage](https://scikit-learn.org/stable/common_pitfalls.html)
- [Grouped cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html)
- [Dai and Adel: data augmentation for NER](https://aclanthology.org/2020.coling-main.343/)
- [CheckList: behavioral testing of NLP models](https://aclanthology.org/2020.acl-main.442/)
- [Historical data and replacement implementation](02-pii-data-tokenization.md)

Next: [QLoRA training](05-qlora-finetuning-workshop.md) · [Evaluation and redaction](07-pii-evaluation-release.md)

[Workshop quiz](../../quizzes/ai-ml/sagemaker-ai/06-data-augmentation-workshop-quiz.md)

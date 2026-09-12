# Part 2: Synthetic PII Data and Deterministic Tokenization

> Implementation and documentation reviewed: 2026-09-12. Generator 1.0.0, seed 42 and existing dataset hashes are preserved.

## Extraction is separate from replacement

The model emits candidate `TYPE<TAB>ORIGINAL` rows:

```text
PERSON	Taylor Sample
EMAIL	synthetic.en.1494@example.com
```

These are synthetic examples. The model does not edit the source document.
Type and source-match checks reject some invalid candidates, but do not prove
that a value is PII, its type is correct, or every PII entity was found.
Treat the replacement mapping as sensitive.

## Dataset and evaluation scope

The dataset has 2,200 records with an 80/20 Korean/English split in each partition.
Regeneration after the implementation changes preserved all manifest hashes.

| Split | Records | Korean | English | SHA-256 |
| --- | ---: | ---: | ---: | --- |
| train | 1,600 | 1,280 | 320 | `b98429fef0b103f24e8eaded069cbd2f6def5fbf8c083a5c7baf366c9fc1d21a` |
| validation | 200 | 160 | 40 | `25ca38198d38e04be181e15b4e21a3c96d672f46f775ae1bc6c422ee4514f820` |
| test | 400 | 320 | 80 | `6f6ef9a6b42297738b292d5149f2e6e323f7bcd6f2325b6bfbc04ae6d9d0ec21` |

The nine labels are PERSON, RRN, DOB, REL, ADDRESS, PHONE, EMAIL, ACCOUNT and CARD.
These are experiment-specific annotation rules. For example, relationship words
can be positive, while company-switchboard strings appear in negative documents.
They are not a universal sensitivity taxonomy.

The generator uses fixed templates, small name vocabularies and synthetic numbers.
RRN/CARD values fail the example checksum functions; that alone does not establish
official identifier validity or non-assignment. PHONE values are synthetic
placeholders, not validated national formats or official reserved ranges.
No customer data is used, but that differs from authoritative identifier validation.

Different records and hashes do not ensure independent templates or entity
vocabularies across train/validation/test. Do not present this dataset as a
real-workload generalization benchmark. Use separate holdouts and reviewed
annotations for that purpose.

## Reversible source-spelling replacement

The implementation now follows this sequence:

1. Normalize source/values to NFC and trim outer type/value whitespace.
2. Remove complete `<think>...</think>` blocks, then read tab-separated allowed types and nonempty values.
3. Deduplicate candidates and require a literal or limited variant to match the source.
   Parsing and replacement use the same numeric boundaries.
4. Prefer literal predictions over variants generated from other predictions.
   A fixed type priority resolves multiple types for one value; it does not infer semantic truth.
5. Scan the source once, with longer patterns first.
6. Assign tokens in actual source order by **type and matched NFC spelling**.
   Identical spellings reuse a token; different spacing/separators receive separate tokens.
7. Skip token names already present in the original source.
8. Store the actual matched spelling in the mapping and record half-open
   `[start, end)` replacement spans in NFC source coordinates.

```text
Source: 김가상 / 김 가 상 / [PERSON_1]
Candidate: PERSON	김가상
Masked: [PERSON_2] / [PERSON_3] / [PERSON_1]
```

The original marker remains unchanged and each source spelling can be restored.
Token numbering need not start at one. Token equality is not real-world entity
identity resolution.

`PERSON` variants cover limited uniform spacing/tab/newline forms for names of
2–6 characters after whitespace removal. Numeric variants only normalize the
permitted digit/whitespace/separator characters. They no longer discard invented
letters to manufacture a source match: an absent `alias123456` is not accepted
merely because `123456` occurs in the source. An alphanumeric original can still
match literally. These rules are not official phone/account/identity validators.

`reassemble_text` performs one replacement pass for known tokens and preserves
unknown tokens. The evaluator checks round trips. Equality is against NFC source
text, not byte-identical restoration of an original NFD representation.

## Measure remaining source spans, not placeholder contents

The earlier evaluator searched for complete gold strings in the masked text.
This produced two incorrect results:

- Masking only `Alpha` in the gold entity `Alpha Beta` removed the complete
  string and incorrectly reported no leakage.
- Masking a literal gold value `PERSON` produced `[PERSON_1]`, whose label was
  incorrectly counted as leaked source text.

The corrected evaluator checks whether the union of actual replacement spans
fully covers every matched occurrence of each gold value or permitted variant.
It examines repeated occurrences too. Partial coverage, including an uncovered
separator, counts as uncovered under this conservative metric. Characters inside
generated token names are not treated as source exposure.

Gold records have values rather than annotation offsets, so these spans are
inferred through source matching. This is not new PII detection and can match a
contextually non-sensitive occurrence of the same string. Interpret coverage
against the annotation policy, not as a privacy guarantee.

## Exact meanings of the metrics

| Result field | Calculation |
| --- | --- |
| entity/per_type precision, recall, F1 | Sum TP/FP/FN over per-document normalized `(TYPE, ORIGINAL)` sets |
| documents.leak_rate | Documents with an uncovered gold span divided by all documents |
| entities.leak_rate | Unique gold pairs with any uncovered occurrence divided by unique gold pairs |
| entities.over_redaction_rate | Legacy field name for **extra predicted-pair rate**: FP / predicted pairs |
| entities.hallucination_rate | Nonempty allowed-type TSV rows without a source match divided by those rows |
| parse.success_rate | Fraction of documents whose caller-provided parse_success flag is True |
| tokenization.deterministic_rate | Fraction with identical masked text, mapping and spans after reversing candidate order |
| tokenization.round_trip_rate | Fraction restoring to the NFC source |

Entity F1 is not span-level NER F1. Duplicate pairs within a document are removed;
the same pair in different documents counts separately. Types are trimmed and
uppercased; values are trimmed and NFC-normalized. A valid variant can mask the
source completely while differing from the gold's exact spelling and producing
FP/FN. The legacy over-redaction field therefore does not directly measure
unnecessarily removed characters.

Hallucination uses source matching independently of the parse flag. Unknown types
and ordinary prose are outside its row denominator. The current inference helper
marks an empty output or an output containing at least one usable source-matching
row as parseable; this is **not strict validation of every output line**.
The evaluator excludes entity predictions when that flag is False.

Zero denominators return zero, including F1 for empty entity sets. Duplicate
record/prediction IDs, predictions for unknown records and gold annotations that
cannot match the source are rejected. Errors do not echo raw entity values.

## Training records and validation

JSONL records contain `source_text`, `entities` and `target_tsv`. The loader
constructs system/user prompts and assistant completions. The trainer requests
completion-only loss; validate the actual tokenizer/template, truncation and loss
mask during execution. Keep source, completions and mappings out of ordinary
logs and MLflow parameters/tags.

Regression tests reproduced token collisions, lossy variant restoration, numeric
variant over-acceptance and evaluation errors before the fixes.
All 50 local tests pass. A 2,200-record ground-truth oracle check also verifies
hash preservation, determinism, restoration and coverage.
**Oracle sanity results are not model predictions or fine-tuned F1 measurements.**
No GPU training or real-customer PII processing was performed.

## References

- [Synthetic generator](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/data/generate_dataset.py)
- [Dataset manifest](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/data/dataset-manifest.json)
- [Parser and replacement](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/src/pii_tokens.py)
- [Evaluation implementation](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/src/metrics.py)

[Previous: Platform architecture](01-platform-architecture.md)

[Next: SageMaker / MLflow execution](03-sagemaker-mlflow-execution.md)

[Quiz](../../quizzes/ai-ml/sagemaker-ai/02-pii-data-tokenization-quiz.md)

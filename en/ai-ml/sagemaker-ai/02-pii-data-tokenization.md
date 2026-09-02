# Part 2: Synthetic PII Data and Deterministic Tokenization

> **Last Updated**: September 2, 2026

## Training Contract

The prompt restricts the model to finding allowed PII types and copying each value **exactly as it appears** in the document. The output contract is one `TYPE<TAB>ORIGINAL` row per entity.

```text
PERSON	Taylor Sample
EMAIL	synthetic.en.1494@example.com
```

These are fully synthetic values from the repository's `review-sample.jsonl`. Numeric identifiers are deliberately omitted from the published example.

Model output is not allowed to edit the document directly:

- A value invented by the model can be rejected by source-containment validation.
- Source position and string length determine replacement order, controlling overlaps and partial matches.
- The token mapping can remain in memory instead of being logged.

## Dataset Composition

The generator version is `1.0.0` and the seed is `42`.

| Split | Records | Korean | English | SHA-256 |
|---|---:|---:|---:|---|
| Train | 1,600 | 1,280 | 320 | `b98429fef0b103f24e8eaded069cbd2f6def5fbf8c083a5c7baf366c9fc1d21a` |
| Validation | 200 | 160 | 40 | `25ca38198d38e04be181e15b4e21a3c96d672f46f775ae1bc6c422ee4514f820` |
| Test | 400 | 320 | 80 | `6f6ef9a6b42297738b292d5149f2e6e323f7bcd6f2325b6bfbc04ae6d9d0ec21` |
| **Total** | **2,200** | **1,760 (80%)** | **440 (20%)** | fixed per split |

A reproducible rerun must match all three split hashes, not merely the row counts.

## Nine Entity Types

| Type | Meaning | Synthetic Pattern |
|---|---|---|
| `PERSON` | person name | `Kim Example`, `Taylor Sample` |
| `RRN` | Korean resident-number shape with an invalid checksum | full values are not published |
| `DOB` | date of birth | synthetic date |
| `REL` | family/applicant relationship | `guardian`, `parent` |
| `ADDRESS` | address | fictional city and example address |
| `PHONE` | phone number | reserved or fictional range |
| `EMAIL` | email address | `synthetic.*@example.com` |
| `ACCOUNT` | account-number shape | synthetic digits, not a real account |
| `CARD` | card-number shape | deliberately fails the Luhn check |

The dataset also contains documents with no PII so the evaluation can detect a model that always extracts something. Korean examples include OCR spacing, delimiter variants, and NFD strings.

## Deterministic Replacement Pipeline

`src/pii_tokens.py` applies these steps:

1. Normalize the source text and completion to NFC.
2. Remove `<think>...</think>` blocks and read only rows containing a tab.
3. Enforce the type whitelist and remove empty or duplicate rows.
4. Confirm that each value or an allowed variant is present in the source text.
5. Sort entities by first source position, then prefer longer strings.
6. Create per-type tokens such as `[PERSON_1]` and `[EMAIL_1]`.
7. Combine original forms and limited variants into one regular expression and replace once.
8. Reassemble with the in-memory mapping and verify an NFC-identical round trip.

Example:

```text
Input:  Name Taylor Sample / Email synthetic.en.1494@example.com
Output: Name [PERSON_1] / Email [EMAIL_1]
```

Only bounded variants are accepted: spacing/tab variants for `PERSON`, and delimiter variants for RRN-shaped values, phones, cards, accounts, and dates. Unbounded fuzzy matching is avoided because it increases false positives and over-redaction.

## Evaluation Metrics

| Metric | Definition | What Failure Means |
|---|---|---|
| entity precision / recall / F1 | TP/FP/FN over `(TYPE, NFC ORIGINAL)` sets | missed or incorrect extraction |
| document leakage rate | documents retaining at least one expected original value | masking failure |
| entity leakage rate | expected entities still present after replacement | partial leakage |
| over-redaction rate | predicted entities absent from the answer set | excessive masking |
| hallucination rate | TSV-like rows whose values are absent from the source | model hallucination |
| parse success rate | documents whose output satisfies the parsing contract | unstable format |
| deterministic rate | identical output when entity order is reversed | order-dependent bug |
| round-trip rate | restored text equals the original | lossy replacement |

The metric implementation passed local tests, but no fine-tuned measurements exist because GPU training was not executed.

## Training Record Shape

Each JSONL record contains `source_text`, source-ordered `entities`, and `target_tsv`. Training converts it into a system/user prompt and assistant completion, with loss applied only to the completion.

```text
System: Extract only allowed types as TYPE<TAB>ORIGINAL
User:   synthetic document
Assistant:
PERSON	Taylor Sample
EMAIL	synthetic.en.1494@example.com
```

Raw source text and completions are runtime inputs and are never written to MLflow parameters or tags.

Previous: [Part 1 — Platform architecture](01-platform-architecture.md)

Next: [Part 3 — SageMaker AI and MLflow execution](03-sagemaker-mlflow-execution.md)

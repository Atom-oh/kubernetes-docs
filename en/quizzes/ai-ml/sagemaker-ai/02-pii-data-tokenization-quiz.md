# Synthetic PII Data and Tokenization Quiz

## Multiple Choice Questions

1. What is the model output contract and its limit?

   - A) Always generate a correct anonymous document
   - B) Every source string is PII
   - C) Candidate TYPE/TAB/ORIGINAL rows; evaluate omissions/misclassification separately
   - D) Return project membership

<details>
<summary>Show Answer</summary>

**Answer: C**

Source matching establishes occurrence, not semantic correctness or complete detection.

</details>

2. How are differently spaced names and a preexisting [PERSON_1] handled?

   - A) Overwrite every spelling with one mapping value
   - B) Use reversible per-spelling tokens and avoid existing marker names
   - C) Always restore the old marker as a new name
   - D) Arbitrarily shorten the source

<details>
<summary>Show Answer</summary>

**Answer: B**

Identical type/spelling reuses a token; different spellings get separate tokens mapped to actual source text.

</details>

3. Which statement about splits and validation scope is correct?

   - A) There are 1,600/200/400 records; templates/names may be shared across splits
   - B) Different hashes prove real-workload generalization
   - C) Checksum failure proves official non-assignment
   - D) Every PHONE is an officially reserved number

<details>
<summary>Show Answer</summary>

**Answer: A**

Existing generator-1.0.0 hashes are retained; distinguish synthetic-template tests from real-workload evaluation.

</details>

4. How does corrected leakage evaluation handle masking only Alpha in gold Alpha Beta?

   - A) Always report zero because the full string disappeared
   - B) Detect an uncovered part of the gold source span
   - C) Search only placeholder names
   - D) Override leakage to zero after a successful round trip

<details>
<summary>Show Answer</summary>

**Answer: B**

It checks complete source-span coverage by the union of replacements. Restoration and complete detection are separate metrics.

</details>

5. What does the 2,200-record oracle check using answer TSV establish?

   - A) Measured fine-tuned model F1
   - B) GPU throughput
   - C) Evaluator/restoration/hash sanity, not model-output quality
   - D) Guaranteed detection of all real PII

<details>
<summary>Show Answer</summary>

**Answer: C**

Fifty local tests and the oracle check passed; no GPU training or fine-tuned evaluation ran.

</details>

---

[Return to Learning Materials](../../../ai-ml/sagemaker-ai/02-pii-data-tokenization.md)

# Synthetic PII Data and Tokenization Quiz

## Multiple Choice Questions

1. What is the model output contract?
   - A) Free-form Markdown
   - B) A JSON object
   - C) One `TYPE<TAB>ORIGINAL` row per entity
   - D) The final masked document

<details>
<summary>Show Answer</summary>

**Answer: C**

Each allowed type and exact source value are separated by a tab.
</details>

2. What is the purpose of source-containment validation?
   - A) Accept invented values
   - B) Reject hallucinated values absent from the source
   - C) Compress the dataset
   - D) Measure GPU memory

<details>
<summary>Show Answer</summary>

**Answer: B**

A value or allowed variant must occur in the source before replacement.
</details>

3. What are the dataset splits?
   - A) 1,600 / 200 / 400
   - B) 2,000 / 100 / 100
   - C) 1,100 / 550 / 550
   - D) 400 / 200 / 1,600

<details>
<summary>Show Answer</summary>

**Answer: A**

Train/validation/test contain 1,600/200/400 records, for 2,200 total.
</details>

4. Which check belongs to deterministic tokenization?
   - A) Reversed entity order must produce a different result
   - B) Mapping-based restoration must reproduce the source
   - C) Unlimited fuzzy matching
   - D) Logging token mappings as MLflow tags

<details>
<summary>Show Answer</summary>

**Answer: B**

Round-trip validation detects lossy replacement.
</details>

5. Why is there no fine-tuned F1 result?
   - A) No F1 implementation exists
   - B) No test set exists
   - C) GPU training and tuned evaluation were not executed
   - D) Only one entity type exists

<details>
<summary>Show Answer</summary>

**Answer: C**

The metric code was validated, but no tuned run was produced.
</details>

---

[Return to learning materials](../../../ai-ml/sagemaker-ai/02-pii-data-tokenization.md)

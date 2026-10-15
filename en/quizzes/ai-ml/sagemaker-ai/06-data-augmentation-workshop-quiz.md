# Synthetic PII Data and Augmentation Quiz

> **Last Updated**: September 15, 2026

## Multiple-choice questions

1. What is the correct order for paraphrases and OCR variants of the same source?

   - A) Generate every variant, then split random record IDs
   - B) Assign source families to splits, then augment training only
   - C) Assign each variant to a different split
   - D) Copy test failures into training first

<details>
<summary>Show Answer</summary>

**Answer: B**

All descendants must remain with their source family to prevent cross-split source/variant leakage.

</details>

2. How many training records result from 24 families with one base and two variants each?

   - A) 24
   - B) 48
   - C) 72
   - D) 120

<details>
<summary>Show Answer</summary>

**Answer: C**

24 × 3 = 72. Each of the eight validation/test families retains only its base.

</details>

3. What is required when substituting a synthetic name?

   - A) Change only the record ID
   - B) Change the source but keep TSV
   - C) Change TSV but keep the source
   - D) Update source, entities, and TSV together and record lineage

<details>
<summary>Show Answer</summary>

**Answer: D**

Regenerate gold against the transformed source. String presence alone still does not prove semantic correctness or complete annotation.

</details>

4. What does the lab establish through family and exact-source separation?

   - A) Families and identical NFC sources do not cross splits
   - B) All people and identifiers are split-disjoint
   - C) All templates are split-disjoint
   - D) Real-world generalization is validated

<details>
<summary>Show Answer</summary>

**Answer: A**

Some names, templates, and domains are shared. Entity/template/domain holdouts need separate design.

</details>

5. After transforming a negative document containing only a switchboard excluded by this policy, what should its target be?

   - A) Add the switchboard as PHONE
   - B) Keep entities and target_tsv empty
   - C) Add an UNKNOWN type
   - D) Add all numbers as ACCOUNT

<details>
<summary>Show Answer</summary>

**Answer: B**

No-entity examples matter. Define negatives for the domain and verify EOS supervision for empty answers in actual training.

</details>

6. Why can this lab reject an omitted label even after file hashes are recomputed?

   - A) Hashes authenticate the producer
   - B) It finds every PII item in arbitrary customer documents
   - C) It also rechecks content against the seed and fixed family recipe
   - D) It automatically measures model F1

<details>
<summary>Show Answer</summary>

**Answer: C**

This checks reproducibility of the fixed synthetic exercise, not arbitrary annotations or producer identity.

</details>

7. What should be held constant or recorded when comparing original and augmented training?

   - A) Select the best result by repeatedly inspecting test
   - B) Compare only file counts
   - C) Compare only generation success
   - D) Use the same validation/decoding and record example/token/step budgets

<details>
<summary>Show Answer</summary>

**Answer: D**

Equal steps can still expose different lengths and amounts of data. Use validation for candidate selection.

</details>

8. Why does summing historical pairwise overlaps 22, 36, and 9 differ from 51 unique cross-split source groups?

   - A) Sources in all three splits appear in multiple pairwise intersections
   - B) NFC sources always identify different documents
   - C) All record IDs are identical
   - D) 51 is the trained model error count

<details>
<summary>Show Answer</summary>

**Answer: A**

The sum of pairwise intersections is not the unique-source-group count. These are CPU data observations, not model-performance numbers.

</details>

---

[Return to learning materials](../../../ai-ml/sagemaker-ai/06-data-augmentation-workshop.md)

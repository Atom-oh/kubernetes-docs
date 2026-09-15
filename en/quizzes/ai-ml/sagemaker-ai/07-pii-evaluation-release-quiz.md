# PII Evaluation and Redaction Pipeline Quiz

> **Last Updated**: September 15, 2026

## Multiple-choice questions

1. The fixture candidate improves F1 to 0.8. Why not deploy it immediately?

   - A) Its recall is zero
   - B) It masks a negative document number as an account, and evaluation has only two synthetic documents
   - C) It misses every gold entity
   - D) Round-trip failed

<details>
<summary>Show Answer</summary>

**Answer: B**

TP/FP/FN are 2/1/0. Evaluate the higher aggregate score together with the new masking error.

</details>

2. What does a round-trip rate of 1.0 establish?

   - A) All real PII was detected
   - B) The source contained no PII
   - C) The mapping reconstructed the NFC source from the masked result
   - D) The model generalizes to new customers

<details>
<summary>Show Answer</summary>

**Answer: C**

Restoration can succeed while omitted PII remains visible in the source.

</details>

3. What is the current entities.over_redaction_rate calculation?

   - A) Unnecessarily masked characters / all characters
   - B) Leaked documents / all documents
   - C) FN / gold pairs
   - D) FP pairs / predicted pairs

<details>
<summary>Show Answer</summary>

**Answer: D**

Despite its historical name, it measures extra extracted pairs, not character-level excessive deletion.

</details>

4. What should a strict serving parser do?

   - A) Validate every row/type/length/truncation and return explicit failures
   - B) Accept the whole response if one row is valid
   - C) Drop bad rows and report no PII
   - D) Invent additional missing candidates

<details>
<summary>Show Answer</summary>

**Answer: A**

Current tolerant parse success differs from a strict contract. Do not label truncated results complete.

</details>

5. What is the role of a test set repeatedly inspected to select rank?

   - A) Still an independent final test
   - B) An evaluation set used in development/selection
   - C) Unaffected because gradients did not use it
   - D) Independent because its hash is fixed

<details>
<summary>Show Answer</summary>

**Answer: B**

Selection can compromise final-test independence even without gradient updates. Separate validation and locked test.

</details>

6. How should data design interpret max_sequence_length=1024?

   - A) Count only 1,024 document characters
   - B) Korean and English share a character/token ratio
   - C) Check tokenizer budgets for template, instruction, source, and completion
   - D) The setting is ignored if the model supports a larger context

<details>
<summary>Show Answer</summary>

**Answer: C**

Check for truncated targets/source PII and evaluate boundaries and offset reconstruction when chunking.

</details>

7. What remains after a SageMaker Training Job reaches Completed?

   - A) Immediately attach an endpoint without quality checks
   - B) Infer with only an adapter and no base model
   - C) Attach mappings to all downstream logs
   - D) Reload, evaluate, and approve the exact base/tokenizer/adapter/parser combination

<details>
<summary>Show Answer</summary>

**Answer: D**

Job termination is separate from service quality and redaction approval. Version the complete rollback combination.

</details>

8. Can this evaluator compute the same leak rate on production documents without gold?

   - A) No; distinguish reviewed annotations, residual checks, and their measurement scope
   - B) Yes; use all model outputs as gold
   - C) Yes; round-trip success means zero leakage
   - D) Yes; empty output means every PII item was removed

<details>
<summary>Show Answer</summary>

**Answer: A**

The metric checks uncovered gold values. Without gold, the same completeness measure is unavailable.

</details>

---

[Return to learning materials](../../../ai-ml/sagemaker-ai/07-pii-evaluation-release.md)

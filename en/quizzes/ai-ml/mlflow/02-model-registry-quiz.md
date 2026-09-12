# MLflow Model Registry Quiz

## Multiple Choice Questions

1. What is a Registered Model?
   - A) A GPU endpoint
   - B) A collection of Model Versions under a logical name
   - C) A training-data copy
   - D) A record allowing only one run

<details>
<summary>Show Answer</summary>

**Answer: B**

For example, fraud-detector groups versions and aliases under one name.
</details>

2. Which Model Version mutation statement is accurate?
   - A) Every field and source byte is permanently immutable
   - B) It receives a version number; descriptions/tags can change and artifact preservation is separate
   - C) Every version expires after 30 days
   - D) Every new model is merged into the previous version

<details>
<summary>Show Answer</summary>

**Answer: B**

Separate the practice of versioning new results from storage-level immutability.
</details>

3. Does every Model Version have a training-run link?
   - A) Always, and the link cannot be deleted
   - B) model_id automatically preserves the dataset snapshot
   - C) No; create_model_version run_id/model_id fields are optional
   - D) The registry never supports origin links

<details>
<summary>Show Answer</summary>

**Answer: C**

Direct source URIs are allowed. Complete lineage requires explicit recording and retention.
</details>

4. What is an alias?
   - A) A built-in traffic percentage across several versions
   - B) A mutable name pointing to one version
   - C) A fixed database address
   - D) An unchangeable content hash

<details>
<summary>Show Answer</summary>

**Answer: B**

Multiple aliases can reference one version, and an alias can move to another version.
</details>

5. What is the legacy stage API status?
   - A) Deprecated since 2.9.0, still present in 3.16.0
   - B) Removed from every MLflow version
   - C) An access-control policy equivalent to aliases
   - D) Only Production is supported

<details>
<summary>Show Answer</summary>

**Answer: A**

Legacy stages are None/Staging/Production/Archived. Design new flows with aliases/tags and explicit permissions.
</details>

6. How can registration happen when a model is logged?
   - A) Set a tag only
   - B) Pass registered_model_name to flavor log_model
   - C) Delete an alias
   - D) Rename a file to champion

<details>
<summary>Show Answer</summary>

**Answer: B**

Registering after logging with register_model is another path. Registration does not itself move an alias.
</details>

7. What controls champion promotion?
   - A) MLflow automatically approves the largest version
   - B) A review_state tag alone completes permission separation
   - C) Evaluation/approval evidence and authentication/authorization for the actor
   - D) Every trainer always changes the alias

<details>
<summary>Show Answer</summary>

**Answer: C**

A tag string replaces neither approval workflow nor access control.
</details>

8. What happens to an already-loaded model immediately after an alias changes?
   - A) It is always replaced instantly
   - B) It retrains automatically
   - C) Shadow traffic appears automatically
   - D) It may keep serving until reload/deployment/cache policy changes it

<details>
<summary>Show Answer</summary>

**Answer: D**

New resolution and the lifecycle of an existing loaded instance are separate.
</details>

## Short Answer Questions

9. Does READY alone prove inference compatibility and model quality?

<details>
<summary>Show Answer</summary>

No. It is a registration status; metadata fixtures can be READY. Validate real flavors, weights, dependency loading, and quality separately.
</details>

10. Why can the registry not always reconstruct exact code and data lineage?

<details>
<summary>Show Answer</summary>

Run/model links are optional and source files, Runs, or artifacts can change or disappear. Preserve the serving version, hashes, commit, dataset snapshot, dependencies, and approvals.
</details>

---

[Return to Learning Materials](../../../ai-ml/mlflow/02-model-registry.md)

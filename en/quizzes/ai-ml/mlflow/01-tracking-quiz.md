# MLflow Tracking Quiz

## Multiple Choice Questions

1. How are Experiments and Runs related?
   - A) An Experiment groups runs; a run can represent training or evaluation
   - B) An Experiment is one GPU
   - C) A Run is always a deployed model
   - D) They are the same entity

<details>
<summary>Show Answer</summary>

**Answer: A**

Runs can also record preprocessing and comparison work.
</details>

2. What is the default metadata backend in a new MLflow 3.16.0 environment?
   - A) An S3 bucket
   - B) sqlite:///mlflow.db
   - C) Browser localStorage
   - D) Mandatory PostgreSQL

<details>
<summary>Show Answer</summary>

**Answer: B**

SQLite is the default; inspect compatibility behavior if ./mlruns already exists. Explicit URIs remove ambiguity.
</details>

3. What is the important MLflow 3 LoggedModel change?
   - A) Independent model_id, status, and relationship tracking
   - B) First-ever ability to call log_model without a start_run block
   - C) Artifacts are no longer needed
   - D) Immediate GPU deployment upon registration

<details>
<summary>Show Answer</summary>

**Answer: A**

Model.log in 2.22.0 already started a run implicitly when needed. Independent model identity is different from omitting an explicit run context.
</details>

4. Which autologging statement is correct?
   - A) It captures everything in arbitrary code
   - B) It always removes PII
   - C) Review each integration’s supported versions and collected inputs/outputs
   - D) It automatically completes deployment

<details>
<summary>Show Answer</summary>

**Answer: C**

Behavior depends on the framework and options. Check input examples, raw data, and model-artifact collection.
</details>

5. Which tracing and cost statement is accurate?
   - A) Tracing first appeared in 3.x
   - B) Every tool span has LLM cost
   - C) Token-derived cost always equals the invoice
   - D) Tracing arrived in 2.14.0; usage collection depends on integration

<details>
<summary>Show Answer</summary>

**Answer: D**

Separate later expansion from initial introduction. Cost cannot be guaranteed without model, usage, and pricing information.
</details>

6. When can a client need S3 permissions despite using a remote tracking server?
   - A) Non-proxy mode with a direct S3 artifact URI
   - B) Only reading SQLite parameters
   - C) It never needs permissions regardless of mode
   - D) Every alias-name lookup requires S3 access

<details>
<summary>Show Answer</summary>

**Answer: A**

Metadata and artifact paths differ. Direct mode requires client storage permissions and network access.
</details>

7. How do you inspect a metric logged at steps 0 and 1?
   - A) The parameter changes automatically
   - B) Only the second value is retained forever
   - C) Use get_metric_history to inspect both observations
   - D) Two models are registered automatically

<details>
<summary>Show Answer</summary>

**Answer: C**

Distinguish the current summary from timestamped, stepped metric history.
</details>

8. What is an appropriate Tracking web UI query path?
   - A) The browser connects directly to PostgreSQL
   - B) The browser calls server HTTP APIs
   - C) The UI always reads files directly from training Pods
   - D) The browser needs a database administrator password

<details>
<summary>Show Answer</summary>

**Answer: B**

The server accesses its backend. Artifact proxy configuration is a separate concern.
</details>

## Short Answer Questions

9. Can a PENDING initialize_logged_model result immediately perform inference?

<details>
<summary>Show Answer</summary>

No. It can be metadata only; actual flavor, weights, artifact logging, and finalization are still required. READY is not quality or deployment approval.
</details>

10. Why might an existing experiment still access S3 directly after server artifact flags change?

<details>
<summary>Show Answer</summary>

The recorded experiment/run artifact URI is not rewritten retroactively. Inspect that URI and the actual permissions and transfer path.
</details>

---

[Return to Learning Materials](../../../ai-ml/mlflow/01-tracking.md)

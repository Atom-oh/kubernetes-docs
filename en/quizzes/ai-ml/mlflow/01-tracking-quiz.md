# MLflow Tracking Quiz

This quiz tests your understanding of MLflow Tracking's core concepts, the MLflow 3 shift to first-class logged models, autologging, GenAI tracing, and the backend/artifact store split.

## Multiple Choice Questions

1. What is an MLflow Experiment?
   - A) A single execution of training code, with its own params and metrics
   - B) A named collection of Runs
   - C) The database that stores MLflow's metadata
   - D) A serialized model file

<details>

<summary>Show Answer</summary>

**Answer: B) A named collection of Runs**

**Explanation:**
An Experiment is a named grouping of Runs, typically one per project or per model being iterated on. A Run is the single execution of training code with its own params, metrics, tags, and artifacts — that's a different concept (option A).
</details>

2. In MLflow 1.x/2.x's run-centric model, how was a logged model typically represented?
   - A) As a `LoggedModel` entity independent of any run
   - B) As an artifact nested under the Run that produced it
   - C) As a row in the backend store's metrics table
   - D) As a standalone experiment

<details>

<summary>Show Answer</summary>

**Answer: B) As an artifact nested under the Run that produced it**

**Explanation:**
Before MLflow 3, a logged model was just another artifact stored inside the run's artifact directory. To find a model, you had to first find the run that produced it. MLflow 3 changed this by introducing `LoggedModel` as its own first-class entity.
</details>

3. What is a key capability that MLflow 3's `LoggedModel` entity enables, which the earlier run-nested model did not?
   - A) Calling `mlflow.sklearn.log_model(...)` directly, without an active `mlflow.start_run()` context
   - B) Logging metrics without a tracking server
   - C) Running training code without Python
   - D) Storing artifacts without an artifact store

<details>

<summary>Show Answer</summary>

**Answer: A) Calling `mlflow.sklearn.log_model(...)` directly, without an active `mlflow.start_run()` context**

**Explanation:**
Because a `LoggedModel` is now a first-class entity separate from Runs, it no longer needs to be nested under an active run to be tracked. This decouples model versioning and comparison from any single training run.
</details>

4. What does `mlflow.autolog()` do?
   - A) It automatically deploys a trained model to a serving endpoint
   - B) It instruments supported ML libraries so params, metrics, and artifacts are logged automatically during training, without manual logging calls
   - C) It automatically deletes old runs to save storage
   - D) It converts a Run into a LoggedModel

<details>

<summary>Show Answer</summary>

**Answer: B) It instruments supported ML libraries so params, metrics, and artifacts are logged automatically during training, without manual logging calls**

**Explanation:**
Autologging captures common training data automatically for supported frameworks. MLflow also provides framework-specific autolog functions (for example, for scikit-learn or PyTorch) for enabling autologging on just one library rather than every detected framework.
</details>

5. In MLflow 3, what is "tracing" primarily used for?
   - A) Logging parameters and metrics for classic scikit-learn training runs
   - B) Capturing the internal steps (spans), token usage, and cost of LLM/agent calls for GenAI observability
   - C) Tracking disk usage of the artifact store
   - D) Replacing the Experiments/Runs view entirely

<details>

<summary>Show Answer</summary>

**Answer: B) Capturing the internal steps (spans), token usage, and cost of LLM/agent calls for GenAI observability**

**Explanation:**
Tracing captures an LLM or agent call as a tree of spans, each representing a step such as a retrieval call or tool invocation, along with token usage and cost. It extends MLflow Tracking to cover GenAI/agent observability as a core feature rather than requiring a separate tool.
</details>

6. Which of the following is an example of a framework MLflow provides auto-tracing integration for, alongside LangChain?
   - A) Kubernetes
   - B) PostgreSQL
   - C) PydanticAI
   - D) Terraform

<details>

<summary>Show Answer</summary>

**Answer: C) PydanticAI**

**Explanation:**
MLflow provides auto-instrumentation for popular LLM/agent frameworks including LangChain, with newer auto-tracing integrations for frameworks such as PydanticAI and smolagents.
</details>

7. Why does the backend store typically need a real relational database (such as PostgreSQL or MySQL) at team scale?
   - A) Because it stores large binary model files that databases handle better than object storage
   - B) Because it holds structured metadata — params, metrics, tags, and run/experiment/model records — which benefits from a database beyond quick local experimentation
   - C) Because MLflow requires a SQL database to render its UI
   - D) Because object storage cannot store any metadata at all

<details>

<summary>Show Answer</summary>

**Answer: B) Because it holds structured metadata — params, metrics, tags, and run/experiment/model records — which benefits from a database beyond quick local experimentation**

**Explanation:**
The backend store holds structured metadata suited to a relational database's many small structured writes and queries. The artifact store, by contrast, holds large binary objects and is typically object storage such as an S3-compatible bucket.
</details>

8. In the tracking flow (training script -> Tracking API -> tracking server -> backend store + artifact store), what does the Tracking UI do?
   - A) It writes directly to the training script's local disk
   - B) It reads from both the backend store and the artifact store to render experiments, runs, logged models, and traces
   - C) It bypasses the tracking server and queries the backend store only
   - D) It only displays artifacts, never metadata

<details>

<summary>Show Answer</summary>

**Answer: B) It reads from both the backend store and the artifact store to render experiments, runs, logged models, and traces**

**Explanation:**
The training script only talks to the Tracking API; the tracking server routes metadata writes to the backend store and file writes to the artifact store. The UI reads from both stores to display everything it needs.
</details>

## Short Answer Questions

9. What is the practical benefit of MLflow 3 tracking lineage between a `LoggedModel` and the runs, traces, prompts, and evaluation metrics associated with it?

<details>

<summary>Show Answer</summary>

**Answer: A model is no longer permanently tied to the single run that trained it — it can be linked to the run that trained it, the runs that evaluated it, and any traces generated by serving it.**

**Explanation:**
Because a `LoggedModel` is a first-class entity rather than a file nested under one run, MLflow 3 can represent richer relationships between a model and everything connected to it. This matters most when a model is iterated on across many runs, or produced outside a traditional training loop, such as wrapping an existing LLM with custom logic.
</details>

10. Why does MLflow frame classic ML experiment tracking and GenAI/agent observability as one system rather than two separate tools?

<details>

<summary>Show Answer</summary>

**Answer: Because MLflow 3 extended the same Tracking system (and its UI) to cover both — tracing for GenAI/agent calls uses the same tracking server, UI, and lineage model as params/metrics/artifacts for classic training runs.**

**Explanation:**
A team doing both classic ML training and LLM/agent development can use one MLflow Tracking deployment for both, instead of standing up a separate observability tool just for the GenAI side.
</details>

---

[Return to Learning Materials](../../../ai-ml/mlflow/01-tracking.md) | [Next Quiz: Model Registry](./02-model-registry-quiz.md)

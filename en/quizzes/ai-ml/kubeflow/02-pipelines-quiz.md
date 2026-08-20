# Kubeflow Pipelines Quiz

This quiz tests your understanding of Kubeflow Pipelines' architecture, the KFP v2 IR YAML compilation model, core concepts (Pipeline, Component, Run, Experiment, Artifact, MLMD), EKS artifact storage considerations, and caching behavior.

## Multiple Choice Questions

1. What workflow engine does the Kubeflow Pipelines backend use under the hood to actually schedule and run the Pods for a pipeline's steps?
   - A) Apache Airflow
   - B) Argo Workflows
   - C) Tekton Pipelines
   - D) Kubernetes CronJobs directly, with no underlying workflow engine

<details>

<summary>Show Answer</summary>

**Answer: B) Argo Workflows**

**Explanation:**
KFP's backend is built on Argo Workflows. Once a compiled pipeline reaches the KFP API server, it's translated into an Argo `Workflow` resource, and Argo's controller creates and sequences the Pods. KFP layers a Python SDK, UI, Experiment/Run tracking, and the MLMD store on top of that.
</details>

2. What is the key architectural difference between the KFP v1 SDK compiler and the KFP v2 SDK compiler?
   - A) v1 compiles to IR YAML; v2 compiles directly to Argo Workflow YAML
   - B) v1 compiles directly to Argo Workflow YAML; v2 compiles to a backend-agnostic Intermediate Representation (IR) YAML
   - C) There is no difference — both produce identical output
   - D) v2 removed the need for compilation entirely

<details>

<summary>Show Answer</summary>

**Answer: B) v1 compiles directly to Argo Workflow YAML; v2 compiles to a backend-agnostic Intermediate Representation (IR) YAML**

**Explanation:**
The v1 SDK's `dsl-compile` produced an Argo-specific `Workflow` YAML manifest directly. The v2 SDK compiles to a backend-agnostic IR YAML (`PipelineSpec`) describing the DAG, components, and typed artifacts; the KFP backend translates that IR into an Argo `Workflow` at submission time.
</details>

3. Which Kubeflow Pipelines component is responsible for recording every component execution, its inputs/outputs, and the artifacts it touched — enabling lineage tracing in the KFP UI?
   - A) The Argo Workflow Controller
   - B) The ML Metadata (MLMD) store
   - C) The MinIO artifact store
   - D) The KFP SDK Compiler

<details>

<summary>Show Answer</summary>

**Answer: B) The ML Metadata (MLMD) store**

**Explanation:**
MLMD (typically MySQL-backed) records every component execution along with its inputs, outputs, and touched artifacts. This is what lets the KFP UI trace a trained model backward through the exact dataset and code that produced it, across runs.
</details>

4. In the KFP v2 SDK, how does a component declare that it produces a typed artifact of kind `Dataset` for downstream components to consume?
   - A) By returning a plain Python dictionary
   - B) By declaring a parameter typed as `Output[Dataset]`
   - C) By writing to a hardcoded `/tmp/dataset.csv` path with no type declaration
   - D) By setting an environment variable named `DATASET`

<details>

<summary>Show Answer</summary>

**Answer: B) By declaring a parameter typed as `Output[Dataset]`**

**Explanation:**
KFP v2 gives artifacts first-class types (`Dataset`, `Model`, `Metrics`, etc.). A component parameter typed `Output[Dataset]` tells the SDK to provision a storage path and wire that artifact into any downstream component that declares a matching `Input[Dataset]` parameter.
</details>

5. What is KFP's default artifact storage backend if nothing is reconfigured, and what does the `awslabs/kubeflow-manifests` project's S3 pattern change about it?
   - A) The default is S3; the pattern switches it to MinIO
   - B) The default is an in-cluster MinIO deployment; the pattern reconfigures the pipeline root and artifact store credentials to use S3 instead
   - C) There is no default artifact store — one must always be configured manually
   - D) The default is EFS; the pattern switches it to EBS

<details>

<summary>Show Answer</summary>

**Answer: B) The default is an in-cluster MinIO deployment; the pattern reconfigures the pipeline root and artifact store credentials to use S3 instead**

**Explanation:**
KFP ships with an in-cluster MinIO deployment as its default artifact store. On EKS, that means running an extra stateful service duplicating what S3 already provides. `awslabs/kubeflow-manifests` documents reconfiguring the pipeline root and artifact credentials so components read/write directly to S3.
</details>

6. When KFP's artifact store is pointed at S3 instead of in-cluster MinIO, what identity mechanism becomes directly relevant for the KFP pipeline pods (e.g., the `pipeline-runner` ServiceAccount)?
   - A) None — S3 access works without any AWS identity configuration
   - B) IRSA or EKS Pod Identity, granting the ServiceAccount permissions on the S3 bucket
   - C) A hardcoded AWS access key baked into every component's container image
   - D) Kubernetes RBAC alone is sufficient for S3 access

<details>

<summary>Show Answer</summary>

**Answer: B) IRSA or EKS Pod Identity, granting the ServiceAccount permissions on the S3 bucket**

**Explanation:**
Once artifact reads/writes go straight to AWS rather than to the in-cluster MinIO endpoint, the ServiceAccount the KFP pipeline pods run under needs an IRSA role or EKS Pod Identity association with permissions on that S3 bucket.
</details>

7. In the example two-step pipeline (`prepare_data` -> `train_model`), how is the `Dataset` artifact passed from the first component to the second?
   - A) By writing to a global variable shared across both components
   - B) Via `train_model(input_dataset=prep_task.outputs["output_dataset"])`, wiring the first component's declared output to the second's typed input
   - C) By storing it in an environment variable
   - D) The two components cannot share data; they must be merged into one component

<details>

<summary>Show Answer</summary>

**Answer: B) Via `train_model(input_dataset=prep_task.outputs["output_dataset"])`, wiring the first component's declared output to the second's typed input**

**Explanation:**
Inside the `@dsl.pipeline`-decorated function, `prep_task.outputs["output_dataset"]` refers to `prepare_data`'s declared `Output[Dataset]` parameter, and passing it into `train_model`'s `input_dataset: Input[Dataset]` parameter is how the SDK wires the artifact dependency between the two independently-running Pods.
</details>

8. How does KFP decide whether to reuse a cached result instead of re-running a component?
   - A) It always re-runs every component regardless of inputs
   - B) It hashes the component's inputs (parameter values, input artifact content, and the component's own definition) and reuses cached outputs on a matching hash from a previous successful execution
   - C) It re-runs components only if the pipeline name has changed
   - D) Caching is based solely on wall-clock time since the last run

<details>

<summary>Show Answer</summary>

**Answer: B) It hashes the component's inputs (parameter values, input artifact content, and the component's own definition) and reuses cached outputs on a matching hash from a previous successful execution**

**Explanation:**
KFP caches a component's execution by hashing its inputs. A later run submitting a component with a matching input hash skips re-execution and reuses the previously cached outputs.
</details>

## Short Answer Questions

9. Name the two ways described in this chapter to disable KFP's caching behavior.

<details>

<summary>Show Answer</summary>

**Answer: Per component, via `set_caching_options(enable_caching=False)` on the task; per run, via the caching toggle exposed in the KFP UI's Run submission dialog.**

**Explanation:**
`prep_task.set_caching_options(enable_caching=False)` disables caching for one specific component task within the pipeline function. Alternatively, the entire pipeline submission's caching can be disabled at Run-submission time rather than component-by-component.
</details>

10. What does the KFP SDK's compilation step actually produce, and what happens to that output once it reaches the KFP API server?

<details>

<summary>Show Answer</summary>

**Answer: It produces an Intermediate Representation (IR) YAML — a backend-agnostic `PipelineSpec`. Once at the API server, the backend translates that IR YAML into an Argo `Workflow`, which Argo's controller then schedules as Pods.**

**Explanation:**
The KFP SDK's job ends at producing IR YAML. Everything from the API server onward — translation to Argo Workflow and Pod scheduling — is the backend's responsibility, which is what makes the IR YAML backend-agnostic in principle.
</details>

## Hands-on Questions

11. Write a `@dsl.component` function named `prepare_data` that declares a single `Output[Dataset]` parameter and writes a pandas DataFrame to it as CSV.

<details>

<summary>Show Answer</summary>

**Answer:**
```python
from kfp import dsl
from kfp.dsl import Dataset, Output

@dsl.component(base_image="python:3.11-slim")
def prepare_data(output_dataset: Output[Dataset]):
    import pandas as pd

    df = pd.DataFrame({"feature": [1, 2, 3, 4], "label": [0, 1, 0, 1]})
    df.to_csv(output_dataset.path, index=False)
```

**Explanation:**
`output_dataset: Output[Dataset]` declares a typed artifact output; the SDK provisions `output_dataset.path` as the storage location the component writes to, which downstream components can then declare as an `Input[Dataset]`.
</details>

12. Write a `@dsl.pipeline` function that wires `prepare_data`'s output into a `train_model` component's `input_dataset` parameter.

<details>

<summary>Show Answer</summary>

**Answer:**
```python
from kfp import dsl

@dsl.pipeline(name="data-prep-train-pipeline")
def data_prep_train_pipeline():
    prep_task = prepare_data()
    train_task = train_model(input_dataset=prep_task.outputs["output_dataset"])
```

**Explanation:**
`prep_task.outputs["output_dataset"]` references the artifact produced by `prepare_data`'s `Output[Dataset]` parameter (named `output_dataset`), and passing it as `train_model`'s `input_dataset` argument creates the DAG edge between the two components.
</details>

13. Write the code to disable caching on a single pipeline task named `prep_task`.

<details>

<summary>Show Answer</summary>

**Answer:**
```python
prep_task.set_caching_options(enable_caching=False)
```

**Explanation:**
Calling `set_caching_options(enable_caching=False)` on a task object within the pipeline function disables caching for that specific component's execution, forcing it to re-run even if a matching cached result from a prior run exists.
</details>

---

[Return to Learning Materials](../../../ai-ml/kubeflow/02-pipelines.md) | [Next Quiz: Notebooks](./03-notebooks-quiz.md)

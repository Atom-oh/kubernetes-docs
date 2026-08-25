# MLflow Model Registry Quiz

This quiz tests your understanding of the MLflow Model Registry: Registered Models, Model Versions, aliases, and how registration connects to Tracking.

## Multiple Choice Questions

1. What is a Registered Model in MLflow?
   - A) A snapshot of a training Run's metrics
   - B) A named, versioned collection of model versions that gives a model a stable identity independent of any single run
   - C) A container image built from a model artifact
   - D) A saved copy of the tracking server's database

<details>

<summary>Show Answer</summary>

**Answer: B) A named, versioned collection of model versions that gives a model a stable identity independent of any single run**

**Explanation:**
A Registered Model is identified by a name (for example, `fraud-detector`) and accumulates Model Versions, aliases, tags, and descriptions over its lifetime. It exists precisely so that "the model" has an identity that outlives any one training Run or Experiment.
</details>

2. What happens to a Model Version once it is created?
   - A) It can be edited in place as the model improves
   - B) It is immutable — a new training result becomes a new version, not an edit to an old one
   - C) It is automatically deleted after 30 days
   - D) It is merged with the next version registered under the same name

<details>

<summary>Show Answer</summary>

**Answer: B) It is immutable — a new training result becomes a new version, not an edit to an old one**

**Explanation:**
Each Model Version is numbered (version 1, version 2, and so on) and, once registered, does not change. A new candidate model always becomes a new version under the same Registered Model name.
</details>

3. What does a Model Version retain that connects it back to Tracking (Part 1)?
   - A) A copy of the training dataset stored inside the registry
   - B) A reference back to the underlying `LoggedModel` or Run it came from
   - C) A snapshot of the cluster's node configuration
   - D) Nothing — Model Versions are fully independent of Tracking

<details>

<summary>Show Answer</summary>

**Answer: B) A reference back to the underlying `LoggedModel` or Run it came from**

**Explanation:**
Every Model Version points back to the Run (and the `LoggedModel` entity covered in Part 1) that produced it, which is what makes lineage and reproducibility possible.
</details>

4. What is an alias in the MLflow Model Registry?
   - A) A permanent, unchangeable label assigned at model creation
   - B) A mutable, named pointer to a specific Model Version, such as `champion` or `challenger`
   - C) A shorthand for the tracking server's URL
   - D) A synonym for a Registered Model's name

<details>

<summary>Show Answer</summary>

**Answer: B) A mutable, named pointer to a specific Model Version, such as `champion` or `challenger`**

**Explanation:**
Unlike a version number, an alias can be moved to point at a different Model Version over time — for example, repointing `champion` from version 4 to version 7 after a new version passes evaluation.
</details>

5. Why have aliases superseded the older stage-based lifecycle model (Staging/Production/Archived) in current MLflow?
   - A) Stages are no longer supported by any version of MLflow
   - B) Aliases are more flexible: a version can hold multiple aliases or none, and alias names are not restricted to a fixed set of lifecycle labels
   - C) Aliases require less disk space than stages
   - D) Stages could not be queried through the API

<details>

<summary>Show Answer</summary>

**Answer: B) Aliases are more flexible: a version can hold multiple aliases or none, and alias names are not restricted to a fixed set of lifecycle labels**

**Explanation:**
The stage model tied every version to one of a fixed set of labels (`Staging`, `Production`, `Archived`). Aliases combined with tags allow more flexible, custom naming and let a version carry more than one alias at a time. Readers may still encounter the stage model in older MLflow deployments, but it is a legacy approach.
</details>

6. Which of the following creates a new Model Version at the same time a model is logged?
   - A) Calling `mlflow.register_model(model_uri, name)` after logging
   - B) Passing `registered_model_name` to a flavor-specific `log_model` call
   - C) Manually copying model files into the tracking server's artifact store
   - D) Setting a tag on an existing Model Version

<details>

<summary>Show Answer</summary>

**Answer: B) Passing `registered_model_name` to a flavor-specific `log_model` call**

**Explanation:**
Passing `registered_model_name` to a call like `mlflow.sklearn.log_model(..., registered_model_name="fraud-detector")` registers a new Model Version in the same call that logs the model. `mlflow.register_model(model_uri, name)` is the alternative path, used to register a model that was already logged in an earlier step.
</details>

7. In the typical governance workflow, what moves the `champion` alias to a new version?
   - A) The training script, automatically, as soon as a run finishes
   - B) An evaluation or approval process — often part of a CI/CD pipeline — only after the candidate version passes its gates
   - C) The serving system, the first time it resolves `models:/fraud-detector@champion`
   - D) MLflow automatically, based on the version number being higher

<details>

<summary>Show Answer</summary>

**Answer: B) An evaluation or approval process — often part of a CI/CD pipeline — only after the candidate version passes its gates**

**Explanation:**
The registry's governance value comes from separating "produce a candidate" from "promote a candidate." Moving the `champion` alias is a deliberate action, typically automated in an approval pipeline, gated on passing evaluation criteria.
</details>

8. What does a serving system gain by resolving `models:/fraud-detector@champion` instead of `models:/fraud-detector/7`?
   - A) Faster inference latency
   - B) A stable reference that automatically picks up whichever version currently holds the `champion` alias, without a code change
   - C) Access to a different tracking server
   - D) Automatic model retraining

<details>

<summary>Show Answer</summary>

**Answer: B) A stable reference that automatically picks up whichever version currently holds the `champion` alias, without a code change**

**Explanation:**
An alias-based URI decouples the consumer of a model from any specific version number. When `champion` is repointed at a newly validated version, the next resolution against that URI simply picks up the new version.
</details>

## Short Answer Questions

9. Explain the difference between a Model Version and an alias, and why that difference matters for a serving system.

<details>

<summary>Show Answer</summary>

**Answer:**
A Model Version is immutable and numbered — once created, it never changes, and a new training result always becomes a new version rather than an edit to an existing one. An alias is mutable: it is a named pointer (such as `champion` or `challenger`) that can be repointed at a different Model Version at any time.

This matters for a serving system because it can be written once to resolve a stable name like `models:/fraud-detector@champion` rather than a hardcoded version number. When the alias is moved to a newly approved version, the serving system automatically picks up the change on its next resolution, with no code or configuration update required.
</details>

10. Describe how a Model Version's lineage supports an audit question like "which exact code and data produced the model currently serving in production."

<details>

<summary>Show Answer</summary>

**Answer:**
Each Model Version retains a reference back to the Run (and the underlying `LoggedModel`, as covered in Part 1) that produced it. Following that chain — from the `champion` alias to the Model Version it points at, and from that version back to its originating Run — leads to the parameters, code references, and dataset information that Run logged during Tracking.

Because a Model Version is immutable and this lineage link is never dropped, an auditor can always trace the model currently aliased as `champion` back to the exact training run that created it, rather than relying on separate records or team memory.
</details>

---

[Return to Learning Materials](../../../ai-ml/mlflow/02-model-registry.md) | [Next Quiz: EKS Deployment](./03-eks-deployment-quiz.md)

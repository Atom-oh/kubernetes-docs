# Part 2: MLflow Model Registry

> **Supported Versions**: MLflow 3.15.1
> **Last Updated**: August 19, 2026

## Lab Environment Setup

To follow along with the examples in this document, you will need the following tools and environment:

### Required Tools and Resources
- Python 3.10 or higher
- `pip install mlflow`
- Access to a running MLflow tracking server with registry access (see [Part 1: MLflow Tracking](01-tracking.md) for how to stand one up, or [Part 3: Deploying MLflow on EKS](03-eks-deployment.md) for a cluster-hosted server)

## What the Model Registry Is

[Part 1](01-tracking.md) covered Tracking: logging parameters, metrics, artifacts, and `LoggedModel` entities against Runs and Experiments. A Run is a record of one training attempt. It is not a good handle for "the model we ship," because a Run's identity is tied to when and how it happened, not to what it means to the business.

The Model Registry solves this by introducing **Registered Models**: named, versioned collections of model versions that give a model a stable identity independent of any single training run or experiment. Instead of asking "which run produced the model currently in production," a team can ask "what is `fraud-detector` right now," and get a consistent answer regardless of how many experiments have run since.

The registry exists to manage a model's lifecycle from development through production: registration, review, promotion, and eventual retirement, all tracked against one durable name.

## Core Concepts

### Registered Model

A Registered Model is a name — for example, `fraud-detector`. It is the top-level entity in the registry. All the versions, aliases, tags, and descriptions attached to a model accumulate under this one name over the model's lifetime.

### Model Version

A Model Version is an immutable, numbered version registered under a Registered Model's name (`fraud-detector` version 1, version 2, and so on). Each version is created once and never changes afterward; a new training result becomes a new version, not an edit to an old one.

Every Model Version points back to the underlying `LoggedModel` (or the Run that produced it) it came from. This is what connects the registry back to Tracking: the version is a pointer into a specific point in a Run's history, not a copy that has drifted away from its origin.

### Aliases

An alias is a mutable, named pointer to a specific Model Version — for example, `champion` or `challenger`. Unlike a version number, an alias can be moved: today `champion` might point at version 4, and after a successful evaluation, a team can repoint it at version 7 without touching anything that consumes the alias.

Aliases are the current, primary mechanism for representing a model's role or lifecycle stage in the registry. A serving system or downstream job can be written once to resolve `models:/fraud-detector@champion`, and it will always load whichever version currently holds that alias, with no code change required when the underlying version changes.

### The Legacy Stage Model (For Reference Only)

Older MLflow deployments used a different mechanism: each Model Version carried a **stage**, one of `Staging`, `Production`, or `Archived`, and moving a model forward meant transitioning its stage. This model has been superseded by aliases combined with tags, which are more flexible because a single version can hold multiple aliases (or none), and an alias name is not restricted to a fixed set of lifecycle labels. New work should use aliases and tags rather than stages. Readers who encounter an older MLflow deployment using stage transitions are looking at this legacy approach.

## Registering a Model

A Model Version is created in one of two ways, both building on what Part 1 covers.

**Register after logging.** After a training run logs a model as an artifact (or as a `LoggedModel`, per Part 1), it can be registered separately by calling `mlflow.register_model(model_uri, name)`, where `model_uri` points at the already-logged model and `name` is the Registered Model to register it under. This is a good fit when the decision to register a model is separate from the training step itself — for example, a review step that only registers models meeting an evaluation threshold.

**Register at logging time.** Alternatively, the `registered_model_name` parameter on a flavor-specific `log_model` call (for example, `mlflow.sklearn.log_model(..., registered_model_name="fraud-detector")`) registers the model as a new Model Version in the same call that logs it. This is a good fit when every run of a given training script is meant to produce a candidate version automatically.

Either path creates a new, immutable Model Version under the named Registered Model. Neither path moves an alias — that is a separate, deliberate action described below.

## Governance and the Handoff Workflow

The registry's main organizational value is as the handoff point between two different concerns: producing a candidate model, and deciding which candidate is trustworthy enough to serve.

A typical workflow looks like this:

1. A data science team trains models and registers each promising result as a new Model Version under a shared Registered Model name, using either registration path above.
2. An evaluation or approval process — automated in CI/CD, manual, or both — reviews a candidate version against test data, fairness checks, or business metrics.
3. Only after a version passes those gates does something move the `champion` alias to point at it, typically via the client API (`set_registered_model_alias`) from an automated pipeline rather than by hand.
4. Serving infrastructure, which is out of scope for this part, is written once to resolve `models:/fraud-detector@champion` and never needs to hardcode a version number. When `champion` moves, the next resolution simply picks up the new version.

This separation means the people or systems producing candidate models never need direct control over what serves in production, and the systems consuming a model never need to track version numbers by hand. A `challenger` alias is commonly used alongside `champion` to mark a version under evaluation for promotion, without disturbing what is currently serving.

![Diagram showing a serving system resolving the champion alias of the fraud-detector registered model (bound to Version 2) to route live production traffic, while separately evaluating the challenger alias (bound to Version 4) among four registered model versions.](../../.gitbook/assets/en-ai-ml-mlflow-02-model-registry-0.png)

## Lineage and Reproducibility

Because every Model Version retains its link back to the Run (and, through it, the parameters, code, and dataset references from Part 1) that produced it, a team can always answer an audit question like "which exact code and data produced the model currently serving as `champion`." The chain is: alias, to Model Version, to Run, to the logged parameters and artifacts of that Run.

Model Versions also support their own tags and descriptions, independent of the tags on the underlying Run. This is useful for recording registry-specific context — for example, who approved a version for promotion, or a link to the evaluation report that justified moving an alias — without mixing that information into the training run's own metadata.

## Next Steps

Part 2 covered the registry itself: Registered Models, Model Versions, aliases as the current lifecycle mechanism, and how registration connects back to [Part 1: MLflow Tracking](01-tracking.md). Loading a registered model into an actual inference endpoint is a separate concern, out of scope for this series — [Part 3: Deploying MLflow on EKS](03-eks-deployment.md) instead covers setting up the tracking server and backing stores that both Tracking and the Model Registry rely on.

[Return to Main Page](./README.md)

## Quiz

Test your understanding with the [Model Registry quiz](../../quizzes/ai-ml/mlflow/02-model-registry-quiz.md).

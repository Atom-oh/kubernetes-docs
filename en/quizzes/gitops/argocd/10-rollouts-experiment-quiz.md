# Argo Rollouts Experiments Quiz

This quiz tests your understanding of the Argo Rollouts Experiment CRD: its resource hierarchy, traffic isolation, analysis verdicts, and result propagation.

1. What is the core purpose of the Experiment CRD?
   - A) Shifting all production traffic to a new version
   - B) Validating a new version with ephemeral ReplicaSets and analyses
   - C) Storing a Rollout's revision history
   - D) Load testing cluster nodes

<details>
<summary>Show Answer</summary>

**Answer: B) Validating a new version with ephemeral ReplicaSets and analyses**

**Explanation:**
An Experiment launches ephemeral ReplicaSets and scales them down to 0 when it finishes. Service selectors and routers must provide the intended isolation. Separate ReplicaSets alone do not guarantee that real users are unaffected.

</details>

2. What happens when an experiment step ends Failed or Error in a Rollout's canary strategy?
   - A) The step is skipped and the Rollout proceeds to the next step
   - B) The failed experiment is retried automatically
   - C) The Rollout is aborted and the stable version stays in place
   - D) The Rollout waits in a paused state

<details>
<summary>Show Answer</summary>

**Answer: C) The Rollout is aborted and the stable version stays in place**

**Explanation:**
The experiment step is a blocking step. The Rollout only proceeds when the Experiment finishes Successful; Failed/Error aborts the Rollout into Degraded. Inconclusive instead sets an InconclusiveExperiment pause for investigation and an operator decision. Abort does not undo database changes or external side effects.

</details>

3. When the `demo-app` Rollout's revision 2 update creates an experiment at its first step (index 0), which base name format is correct when there is no name collision? (The new version's PodTemplateHash is `74d8d8b4fb`.)
   - A) `demo-app-experiment-1`
   - B) `demo-app-74d8d8b4fb-2-0`
   - C) `experiment-demo-app-0-2`
   - D) `demo-app-2-0-74d8d8b4fb`

<details>
<summary>Show Answer</summary>

**Answer: B) `demo-app-74d8d8b4fb-2-0`**

**Explanation:**
An Experiment is named `<rollout-name>-<new-version PodTemplateHash>-<revision>-<step-index>`. The ReplicaSets it creates are named `<experiment-name>-<template-name>` (e.g., `demo-app-74d8d8b4fb-2-0-baseline`), and AnalysisRuns are named `<experiment-name>-<analysis-name>`.

</details>

4. When the example Service selects traffic-class=production and experiment Pods have traffic-class=experiment, why are those Pods excluded from that Service?
   - A) Experiment Pods are created in a separate namespace
   - B) Experiment Pods are blocked by a NetworkPolicy
   - C) The Service selector’s traffic-class differs from the experiment Pod label
   - D) Experiment Pods are configured with an always-failing readinessProbe

<details>
<summary>Show Answer</summary>

**Answer: C) The Service selector’s traffic-class differs from the experiment Pod label**

**Explanation:**
The example explicitly separates selection sets using labels/selectors. Another Service selecting only the app label could still include experiment Pods. To intentionally send traffic, either set the `service` attribute on a template to create an experiment-scoped Service, or use `weight` on a Rollout that has trafficRouting configured.

</details>

5. What is the prerequisite for sending real traffic to experiment Pods via a template's `weight` field?
   - A) The Rollout must have trafficRouting that supports weighted Experiments
   - B) The template's replicas must equal the stable replicas
   - C) The AnalysisTemplate must use the web provider
   - D) The Experiment must be created standalone, without a Rollout

<details>
<summary>Show Answer</summary>

**Answer: A) The Rollout must have trafficRouting that supports weighted Experiments**

**Explanation:**
Weight belongs to each Rollout experiment-step template. A supporting router such as ALB/Istio is required; ordinary canary weighting does not imply Experiment splitting support. Without trafficRouting, create an experiment-scoped Service via the `service` attribute and wire up routing yourself.

</details>

6. With `failureLimit: 1` on an AnalysisTemplate metric, when does the whole AnalysisRun become Failed?
   - A) Immediately after 1 failed measurement
   - B) After 2 failed measurements (failed > failureLimit)
   - C) Only after 1 consecutive failure
   - D) Only after all measurements specified by count have finished

<details>
<summary>Show Answer</summary>

**Answer: B) After 2 failed measurements (failed > failureLimit)**

**Explanation:**
`failureLimit` is the number of allowed failures; the AnalysisRun is assessed Failed the moment the failure count exceeds it. The 1.10.0 implementation compares `failed > failureLimit`. Likewise, exceeding `inconclusiveLimit` yields Inconclusive, and exceeding `consecutiveErrorLimit` (consecutive collection errors, default 4) yields Error.

</details>

7. When does an Experiment's `duration` timer start?
   - A) Immediately when the Experiment resource is created
   - B) When the first AnalysisRun measurement succeeds
   - C) When all ReplicaSets from spec.templates become healthy (available)
   - D) Right before the Rollout reaches the experiment step

<details>
<summary>Show Answer</summary>

**Answer: C) When all ReplicaSets from spec.templates become healthy (available)**

**Explanation:**
The Experiment controller first creates the per-template ReplicaSets and waits until all Pods are available. The duration timer and AnalysisRun creation start only after that, so slow Pod startup does not eat into the experiment window.

</details>

8. What happens to the experiment's ReplicaSets when the Experiment completes (regardless of success or failure)?
   - A) They are kept for the next experiment
   - B) They are scaled down to 0, and any Service created via the `service` attribute is cleaned up
   - C) They are promoted to the stable ReplicaSet
   - D) They remain until deleted manually

<details>
<summary>Show Answer</summary>

**Answer: B) They are scaled down to 0, and any Service created via the `service` attribute is cleaned up**

**Explanation:**
An Experiment is ephemeral. After completion, the default thirty-second scale-down delay precedes scaling replicas to zero. Generated Services are removed after available replicas reach zero. ReplicaSet/AnalysisRun objects may remain under retention policies. Successful advances, Failed/Error aborts, and Inconclusive pauses.

</details>

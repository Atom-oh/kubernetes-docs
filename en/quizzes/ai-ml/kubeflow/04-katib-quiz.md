# Part 4: Katib — Hyperparameter Tuning and AutoML Quiz

This quiz tests your understanding of Katib's Experiment/Trial/Suggestion architecture, the search algorithms it supports, early stopping, metrics collection, and the resource-pressure considerations of running Katib on EKS.

## Multiple Choice Questions

1. In Katib's architecture, what is the relationship between an Experiment, a Trial, and a Suggestion?
   - A) They are three interchangeable names for the same CRD
   - B) A Suggestion owns many Experiments, each of which owns one Trial
   - C) An Experiment owns many Trials, each running a specific hyperparameter combination, while a Suggestion service proposes those combinations
   - D) A Trial owns many Experiments, coordinated by a single global Suggestion

<details>
<summary>Show Answer</summary>

**Answer: C) An Experiment owns many Trials, each running a specific hyperparameter combination, while a Suggestion service proposes those combinations**

**Explanation:**
An Experiment CRD describes one tuning run and owns up to `maxTrialCount` Trials over its lifetime. Each Trial is a single training run with one specific hyperparameter combination. The Suggestion service implements the search algorithm and proposes which combinations each Trial should try, based on prior results.
</details>

2. Which search algorithm builds a probabilistic model of how hyperparameters map to the objective metric, using that model to pick the next most promising point(s) to try?
   - A) Grid search
   - B) Random search
   - C) Bayesian optimization
   - D) Hyperband

<details>
<summary>Show Answer</summary>

**Answer: C) Bayesian optimization**

**Explanation:**
Bayesian optimization builds a probabilistic model relating hyperparameters to the objective and uses it to select the next candidate(s) most likely to improve on the best result seen so far. Random search samples independently with no memory of past trials; grid search exhaustively enumerates discrete combinations; Hyperband allocates a small budget broadly and reallocates it to early survivors.
</details>

3. What tradeoff does Hyperband make compared to giving every configuration a full, equal training budget?
   - A) It trains every configuration to full completion before comparing them
   - B) It gives many configurations a small budget, discards the worst performers early, and reallocates freed budget to the survivors
   - C) It only ever tries a single configuration at a time
   - D) It ignores intermediate performance entirely and picks configurations at random

<details>
<summary>Show Answer</summary>

**Answer: B) It gives many configurations a small budget, discards the worst performers early, and reallocates freed budget to the survivors**

**Explanation:**
Hyperband trades exhaustive per-configuration information for early pruning: it runs many configurations cheaply at first, aggressively discards the ones that look weakest, and gives the freed-up resource budget to the configurations that are still promising.
</details>

4. In an Experiment's spec, what does the `objective` field define?
   - A) The container image used to run each Trial
   - B) The metric to optimize and whether to maximize or minimize it
   - C) The number of Trials that can run in parallel
   - D) The search algorithm's internal hyperparameters

<details>
<summary>Show Answer</summary>

**Answer: B) The metric to optimize and whether to maximize or minimize it**

**Explanation:**
`objective` names the metric (e.g., accuracy or loss) and the goal (maximize or minimize), and can optionally include a target value that allows the Experiment to stop early once reached. The search space is defined separately, under `parameters`, and how each Trial's job is run is defined under `trialTemplate`.
</details>

5. What does the median-stopping rule do, conceptually?
   - A) It stops the Experiment entirely once the median Trial finishes
   - B) It compares a Trial's intermediate objective value against the median of its peers at the same point in training, and stops the Trial early if it's meaningfully behind
   - C) It only allows exactly half of all proposed Trials to run
   - D) It selects the median hyperparameter value as the final answer

<details>
<summary>Show Answer</summary>

**Answer: B) It compares a Trial's intermediate objective value against the median of its peers at the same point in training, and stops the Trial early if it's meaningfully behind**

**Explanation:**
Median-stopping is a form of early stopping: rather than letting a clearly underperforming Trial run to completion, its intermediate value is compared against the median of other Trials at the same training point, and it's terminated early if it's falling significantly short — saving the compute it would otherwise consume for an unlikely-to-be-competitive result.
</details>

6. How does Katib typically get the objective metric value out of a running Trial's training container?
   - A) The training container must call a Katib API directly from inside its code
   - B) A metrics-collector sidecar tails logs/stdout or scrapes a metrics endpoint and reports the parsed value back to Katib
   - C) Katib pauses the container and inspects its memory directly
   - D) The Kubernetes scheduler extracts the metric automatically from resource usage

<details>
<summary>Show Answer</summary>

**Answer: B) A metrics-collector sidecar tails logs/stdout or scrapes a metrics endpoint and reports the parsed value back to Katib**

**Explanation:**
A metrics-collector sidecar is injected into the Trial pod alongside the training container. It observes the training container's output — typically parsing stdout/log files or scraping an exposed metrics endpoint — and reports the objective metric back to Katib, keeping the training code itself largely unaware of Katib.
</details>

7. Why does a high `parallelTrialCount` create sharper resource pressure on an EKS cluster than the same `maxTrialCount` run at low concurrency?
   - A) `parallelTrialCount` has no effect on how many pods are created
   - B) High parallelism means many Trials (and their resource requests, e.g. GPUs) hit the cluster at the same time rather than spread out, producing a short, sharp demand spike
   - C) EKS caps `parallelTrialCount` at 1 by default
   - D) Parallel Trials always run on the same node, so there is no additional demand

<details>
<summary>Show Answer</summary>

**Answer: B) High parallelism means many Trials (and their resource requests, e.g. GPUs) hit the cluster at the same time rather than spread out, producing a short, sharp demand spike**

**Explanation:**
Each concurrent Trial is a full training job. A `parallelTrialCount` of 8 means 8 concurrent resource requests (e.g., GPU requests) all at once, rather than spread over time — which can spike demand sharply even for an Experiment whose total `maxTrialCount` looks modest.
</details>

8. On EKS, what is a likely explanation if newly created Trial pods sit pending for a while right after a high-`parallelTrialCount` Experiment starts?
   - A) The Suggestion service has crashed
   - B) Karpenter is provisioning new GPU-backed nodes in response to the burst of pending pods, and GPU instance types often have longer provisioning lead times
   - C) Katib always pauses new Trials for a fixed warm-up period
   - D) The metrics-collector sidecar is blocking pod startup

<details>
<summary>Show Answer</summary>

**Answer: B) Karpenter is provisioning new GPU-backed nodes in response to the burst of pending pods, and GPU instance types often have longer provisioning lead times**

**Explanation:**
A burst of pending Trial pods from a high `parallelTrialCount` typically triggers Karpenter to provision new nodes. GPU instance types can take longer to provision than general-purpose ones, so Trials may sit waiting on node capacity — worth checking via Trial pod events before assuming the search algorithm itself is slow.
</details>

## Short Answer Questions

9. Name two of the search algorithms Katib supports and, in one sentence each, describe what problem each is best suited for.

<details>
<summary>Show Answer</summary>

**Answer:** Any two of: random search (cheap baseline for large/poorly understood search spaces), grid search (exhaustive coverage of small, low-dimensional discrete spaces), Bayesian optimization (reducing total Trials needed when each Trial is expensive, via a probabilistic model of the objective), Hyperband (pruning underperforming configurations early using a cheap, informative early signal), or CMA-ES/population-based approaches (continuous or higher-dimensional spaces suited to evolving a population of candidates).

**Explanation:**
Each algorithm trades off exploration cost against search efficiency differently, and the right choice depends on how expensive a single Trial is and how much structure the search space has.
</details>

10. What is the difference between what Hyperband does and what early stopping (e.g., the median-stopping rule) does, given that both aim to avoid wasting compute?

<details>
<summary>Show Answer</summary>

**Answer:** Hyperband is a search strategy that decides up front how much resource budget to give each configuration; early stopping is a runtime check applied to a Trial already in progress, based on how it's performing relative to its peers at that point in training.

**Explanation:**
The two operate at different levels: Hyperband's pruning is part of the search algorithm's overall budget-allocation strategy, while early stopping is a per-Trial decision made while that Trial is running, independent of which search algorithm proposed it.
</details>

## Hands-on / Applied Question

11. You are configuring an Experiment where each Trial requests one GPU, and the cluster has a Karpenter NodePool for GPU instances that typically takes several minutes to provision new capacity. You set `maxTrialCount: 60` and are deciding on `parallelTrialCount`. Explain, in a few sentences, the tradeoff between setting it high (e.g., 20) versus low (e.g., 4) in this environment.

<details>
<summary>Show Answer</summary>

**Answer:** A high `parallelTrialCount` (e.g., 20) finishes all 60 Trials in fewer sequential rounds but produces a sharp burst of 20 simultaneous GPU requests, which can outrun how fast Karpenter can provision GPU nodes — leaving early Trials pending rather than training, and potentially spiking shared cluster capacity if other workloads are competing for the same GPU NodePool. A low `parallelTrialCount` (e.g., 4) spreads the same 60 Trials over more rounds, giving Karpenter time to provision incrementally and reducing the risk of a capacity spike, at the cost of the Experiment taking longer overall to reach `maxTrialCount`.

**Explanation:**
`parallelTrialCount` and `maxTrialCount` need to be tuned together with cluster autoscaling behavior in mind, not treated as independent settings — especially when Trials request scarce or slow-to-provision resources like GPUs.
</details>

---

[Return to Learning Materials](../../../ai-ml/kubeflow/04-katib.md)

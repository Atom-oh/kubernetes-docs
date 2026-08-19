# Part 6: KServe — Model Serving on Kubernetes Quiz

This quiz tests your understanding of KServe's relationship to Kubeflow, the `InferenceService` components, the Serverless vs. Raw Deployment trade-off, autoscaling mechanics, canary rollouts, and GPU inference on EKS.

## Multiple Choice Questions

1. What is the historical relationship between KServe and Kubeflow?
   - A) KServe was always a fully independent project with no connection to Kubeflow
   - B) KServe began inside Kubeflow as KFServing, then spun out into its own top-level standalone project
   - C) Kubeflow is a subcomponent of KServe
   - D) KServe is a rebranding of Katib

<details>
<summary>Show Answer</summary>

**Answer: B) KServe began inside Kubeflow as KFServing, then spun out into its own top-level standalone project**

**Explanation:**
KServe started as KFServing, a component inside Kubeflow responsible for turning trained models into inference endpoints. It later became an independent, standalone project that can be installed on any Kubernetes cluster without Kubeflow, while Kubeflow continues to bundle it as its default model-serving layer.
</details>

2. Why can't you assume the KServe controller/CRD version matches the version printed for the KServe web app in the Kubeflow dashboard?
   - A) The Kubeflow dashboard never displays any KServe version information
   - B) KServe has its own independent release cadence separate from the Kubeflow Community Distribution's calendar-versioned release train, so a platform team can upgrade the controller independently of the web app
   - C) KServe is deprecated and no longer receives version updates
   - D) The Kubeflow web app and the KServe controller are always the exact same binary

<details>
<summary>Show Answer</summary>

**Answer: B) KServe has its own independent release cadence separate from the Kubeflow Community Distribution's calendar-versioned release train, so a platform team can upgrade the controller independently of the web app**

**Explanation:**
The Kubeflow Community Distribution 26.03 bundles the KServe web app at v0.16.1, but that number describes the dashboard integration, not necessarily the underlying KServe controller/CRD version running on the cluster, since the controller can be upgraded on its own schedule.
</details>

3. Which `InferenceService` component is required, with the others being optional?
   - A) Explainer
   - B) Transformer
   - C) Predictor
   - D) All three are required

<details>
<summary>Show Answer</summary>

**Answer: C) Predictor**

**Explanation:**
The predictor is the model server itself and is the only mandatory component of an `InferenceService`. The transformer (pre/post-processing) and explainer (model explanations) are both optional add-ons used only when the use case calls for them.
</details>

4. What is the defining capability of KServe's Serverless deployment mode, and what does it cost?
   - A) It uses a plain Deployment and HPA, with no trade-off at all
   - B) It scales pods to zero via Knative when idle, at the cost of cold-start latency on scale-up
   - C) It requires no Kubernetes cluster at all
   - D) It eliminates the need for a predictor

<details>
<summary>Show Answer</summary>

**Answer: B) It scales pods to zero via Knative when idle, at the cost of cold-start latency on scale-up**

**Explanation:**
Serverless mode delegates pod lifecycle to Knative Serving, which can scale predictor (and transformer/explainer) pods all the way to zero when there's no traffic, saving idle GPU cost. The trade-off is cold-start latency: scheduling a new pod, starting the container, and loading the model artifact all take time before the first request after a scale-from-zero can be answered.
</details>

5. What is the key difference between Raw Deployment mode and Serverless mode?
   - A) Raw Deployment mode manages a plain Deployment/Service (and optional HPA) with no Knative dependency and no scale-to-zero
   - B) Raw Deployment mode requires Knative Serving but adds a transformer automatically
   - C) Raw Deployment mode is only available for SKLearn models
   - D) Raw Deployment mode always runs more replicas than Serverless mode

<details>
<summary>Show Answer</summary>

**Answer: A) Raw Deployment mode manages a plain Deployment/Service (and optional HPA) with no Knative dependency and no scale-to-zero**

**Explanation:**
Raw Deployment mode is operationally simpler (no Knative to install/upgrade) and avoids cold starts entirely, but it never scales below the Deployment's configured minimum replica count, so at least that many predictor pods (and their GPUs, if any) are always running regardless of traffic.
</details>

6. How does autoscaling differ between the two deployment modes?
   - A) Both modes use exactly the same HPA-based CPU scaling
   - B) Serverless mode scales on Knative's concurrency/RPS-based signals; Raw Deployment mode scales on a standard HPA using CPU/memory or custom metrics
   - C) Serverless mode never scales at all
   - D) Raw Deployment mode scales based on Knative concurrency, and Serverless mode uses HPA

<details>
<summary>Show Answer</summary>

**Answer: B) Serverless mode scales on Knative's concurrency/RPS-based signals; Raw Deployment mode scales on a standard HPA using CPU/memory or custom metrics**

**Explanation:**
Knative's autoscaler in Serverless mode reacts to request-level signals like concurrency or requests-per-second, which tends to react faster to bursty inference traffic than a resource-utilization signal. Raw Deployment mode instead relies on a standard Kubernetes HorizontalPodAutoscaler, the same autoscaling model used by any other Deployment on the cluster.
</details>

7. How does KServe's built-in canary rollout mechanism relate to the Istio/Argo Rollouts traffic-splitting patterns covered elsewhere in this documentation?
   - A) They are the exact same mechanism, just with different names
   - B) KServe's canary rollout is a separate, model-serving-specific mechanism built into the KServe control plane, distinct from service-mesh or progressive-delivery-controller traffic-splitting
   - C) KServe has no canary rollout capability and must use Argo Rollouts instead
   - D) Istio traffic-splitting replaces the need for an InferenceService entirely

<details>
<summary>Show Answer</summary>

**Answer: B) KServe's canary rollout is a separate, model-serving-specific mechanism built into the KServe control plane, distinct from service-mesh or progressive-delivery-controller traffic-splitting**

**Explanation:**
KServe can split traffic between a stable and canary `InferenceService` revision on its own, gradually shifting traffic as confidence grows. This operates at the level of `InferenceService` revisions specifically, and is a different tool from the Istio- or Argo Rollouts-based traffic-splitting patterns used for other workloads on the platform — not a replacement requirement, but a distinct, model-serving-specific path.
</details>

8. What role does Karpenter play when an `InferenceService` predictor requests a GPU on EKS?
   - A) Karpenter configures the KServe predictor's inference protocol
   - B) Karpenter provisions a matching GPU-backed EC2 instance when the pod's GPU request can't be satisfied by existing nodes, and can consolidate/reclaim that capacity once it's no longer needed
   - C) Karpenter replaces the need for a GPU device plugin
   - D) Karpenter only works with Raw Deployment mode, never Serverless mode

<details>
<summary>Show Answer</summary>

**Answer: B) Karpenter provisions a matching GPU-backed EC2 instance when the pod's GPU request can't be satisfied by existing nodes, and can consolidate/reclaim that capacity once it's no longer needed**

**Explanation:**
GPU inference on EKS follows the standard Kubernetes resource request model against the GPU device plugin's advertised resource; Karpenter's GPU node pools react to unschedulable GPU requests by provisioning matching capacity, and its consolidation behavior can reclaim that capacity once a predictor (especially one that scales to zero in Serverless mode) no longer needs it — a two-tier autoscaling pattern used elsewhere on EKS as well.
</details>

## Short Answer Questions

9. In one or two sentences, explain why choosing Serverless mode is a good fit for a model with spiky, intermittent inference traffic, but a poor fit for one requiring consistently low latency on every request.

<details>
<summary>Show Answer</summary>

**Answer: Serverless mode's scale-to-zero saves GPU cost during idle periods, which suits spiky/intermittent traffic where the model sits idle much of the time. But scaling back up from zero incurs cold-start latency (pod scheduling, container start, model load), which is unacceptable for workloads that need consistently low latency on every single request.**

**Explanation:**
The trade-off is fundamentally cost (idle GPU savings) versus latency predictability (no cold starts). Raw Deployment mode inverts this trade-off by always keeping the minimum replica count warm, at the cost of paying for that capacity even when idle.
</details>

10. What distinguishes the predictor's built-in framework support from a custom container predictor in KServe?

<details>
<summary>Show Answer</summary>

**Answer: Built-in predictor servers (e.g., for SKLearn, XGBoost, PyTorch via TorchServe, or NVIDIA Triton) let a predictor spec simply point at a model artifact location and get a working server with no serving code written. A custom container predictor is used for anything outside those built-in frameworks, and must itself implement KServe's inference protocol.**

**Explanation:**
This distinction determines how much serving-side implementation work is needed: built-in servers cover common frameworks out of the box, while anything else requires a hand-written container that speaks KServe's protocol.
</details>

11. Describe the two-tier autoscaling relationship between KServe's own scaling decisions and Karpenter's response to them.

<details>
<summary>Show Answer</summary>

**Answer: KServe (via Knative in Serverless mode, or HPA in Raw Deployment mode) decides how many predictor pods are needed based on request-level or resource-utilization signals — a pod-level decision with no knowledge of nodes. Karpenter reacts separately to the resulting pod scheduling state (unschedulable GPU requests, or empty GPU nodes) to decide how much EC2 GPU capacity to provision or reclaim — a node-level decision with no knowledge of why the pods exist.**

**Explanation:**
These are two independent control loops, coupled only through pod count/scheduling state — the same general two-tier autoscaling pattern (job/pod-level decision first, node-level decision reacting to it) used for other autoscaled workloads on EKS elsewhere in this documentation.
</details>

---

[Return to Learning Materials](../../../ai-ml/kubeflow/06-kserve.md)

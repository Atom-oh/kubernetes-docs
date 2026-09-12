# KServe Quiz

Baseline: KServe 0.18.0 / Community Distribution 26.03.1.

## Multiple Choice Questions

1. How is KServe related to Kubeflow?

   - A) It evolved from KFServing and can run independently with its dependencies
   - B) It is a new name for Katib
   - C) It always requires the entire Kubeflow distribution
   - D) It replaces Kubernetes

<details>
<summary>Show Answer</summary>

**Answer: A) It evolved from KFServing and can run independently with its dependencies**

Full Kubeflow and the Models Web Application are not prerequisites for every KServe installation.
</details>

2. Which versions does this chapter review?

   - A) Only the web app at 0.16.1
   - B) KServe and web app 0.18.0 in Community 26.03.1; latest inspected KServe is 0.20.0
   - C) All components must have different versions
   - D) The web-app label determines all installed CRDs

<details>
<summary>Show Answer</summary>

**Answer: B) KServe and web app 0.18.0 in Community 26.03.1; latest inspected KServe is 0.20.0**

Controller, CRDs and web app are separate artifacts. Their actual compatibility and revisions must be recorded.
</details>

3. Which InferenceService component is required?

   - A) Explainer
   - B) Transformer
   - C) Predictor
   - D) All three

<details>
<summary>Show Answer</summary>

**Answer: C) Predictor**

Transformer and explainer are optional; runtime/protocol compatibility and actual explanation routes still matter.
</details>

4. Does selecting Knative automatically scale every idle predictor to zero?

   - A) Yes, with no configuration
   - B) No; KServe defaults minReplicas to 1 and scale-to-zero requires supported autoscaler/policy settings such as minReplicas 0
   - C) Yes, and EC2 billing immediately stops
   - D) No Knative installation is needed

<details>
<summary>Show Answer</summary>

**Answer: B) No; KServe defaults minReplicas to 1 and scale-to-zero requires supported autoscaler/policy settings such as minReplicas 0**

Scale-from-zero includes capacity, image and model loading. Pod zero does not guarantee node termination.
</details>

5. Which statement about Standard mode is correct?

   - A) It guarantees a warm healthy replica at all times
   - B) It uses Deployment/Service; default HPA retains at least 1, while a configured KEDA path can support zero
   - C) It always requires Knative
   - D) It supports no autoscaling options

<details>
<summary>Show Answer</summary>

**Answer: B) It uses Deployment/Service; default HPA retains at least 1, while a configured KEDA path can support zero**

KEDA needs installation, valid metrics/triggers and an activation path. Restart/rollout/scale-out startup latency remains in either mode.
</details>

6. What are the modern mode names in 0.18.0?

   - A) Serverless and RawDeployment are the only valid names
   - B) Knative and Standard; old names are deprecated aliases
   - C) HPA and GPU
   - D) Predictor and Transformer

<details>
<summary>Show Answer</summary>

**Answer: B) Knative and Standard; old names are deprecated aliases**

Inspect the actual annotation and config. Code fallback is Standard; the inspected OCI resource chart defaults to Knative.
</details>

7. What implements the verified canaryTrafficPercent path?

   - A) The KServe controller proxies all requests itself
   - B) KServe sets Knative revision traffic targets; Knative networking routes requests
   - C) Every Standard Deployment automatically has the same revision splitting
   - D) Argo Rollouts is mandatory

<details>
<summary>Show Answer</summary>

**Answer: B) KServe sets Knative revision traffic targets; Knative networking routes requests**

Standard rolling update is not the same revision-percentage mechanism. Promotion/rollback and retained artifacts need separate validation.
</details>

8. Does requesting nvidia.com/gpu guarantee GPU inference?

   - A) Yes for every model
   - B) No; drivers, image/backend and model/device configuration must also match
   - C) It automatically installs all required drivers
   - D) It removes the need for node capacity

<details>
<summary>Show Answer</summary>

**Answer: B) No; drivers, image/backend and model/device configuration must also match**

Resource allocation and actual model execution are distinct. Karpenter supplies eligible capacity subject to policies, quotas and availability.
</details>

## Short Answer Questions

9. Why is always-warm versus scale-to-zero not an absolute distinction between the two modes?

<details>
<summary>Show Answer</summary>

Knative can retain warm replicas through minimum settings, and Standard can use KEDA with a suitable external signal. Neither mode guarantees availability or latency; test readiness, loading, capacity and recovery.
</details>

10. Why is an artifact URI alone insufficient, and how should TorchServe be treated?

<details>
<summary>Show Answer</summary>

The runtime, model format/layout, library version, credentials, ports and protocol must match. TorchServe says it is no longer actively maintained with no planned security fixes, so an old runtime catalog entry is not evidence of a maintained default.
</details>

11. How do Pod autoscaling and EC2 scaling interact?

<details>
<summary>Show Answer</summary>

Knative/HPA/KEDA or another configured scaler determines desired Pods. Kubernetes scheduling and Karpenter capacity policies affect node provisioning/reclamation. Other workloads or disruption rules can keep EC2 nodes billed after model Pods reach zero.
</details>

---

[Return to Learning Materials](../../../ai-ml/kubeflow/06-kserve.md)

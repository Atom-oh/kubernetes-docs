# Part 6: KServe — Model Serving on Kubernetes

> **Review baseline**: KServe 0.18.0 / Models Web Application 0.18.0 / Community Distribution 26.03.1
> **Last Updated**: September 12, 2026

## Lab Environment Setup

Use compatible Kubernetes, KServe controller/CRDs, ServingRuntime, storage access and an authenticated network path. Full Kubeflow is not required; the web app is optional. Knative mode needs Knative Serving/networking; Standard's KEDA path needs KEDA and metric providers. GPUs are workload-dependent.

## KServe and Kubeflow

KServe evolved from KFServing into an independent serving project. This chapter reviews **KServe and Models Web Application 0.18.0** bundled in Community Distribution 26.03.1. The latest public KServe release inspected was **0.20.0 (August 6, 2026)**; it is not the same as the distribution's 0.18.0 baseline.

Controller, CRDs and web app are separate artifacts requiring compatibility checks. Their version numbers need not always match or always differ. Record actual images, CRD schemas and web-app revisions.

`InferenceService` is the serving API covered here, not the whole KServe architecture. ServingRuntime/ClusterServingRuntime, ModelMesh and the separate LLMInferenceService API have different dependencies and operating models.

## InferenceService: Predictor, Transformer, Explainer

InferenceService has a required predictor and optional transformer/explainer. Predictor configures the model server, transformer provides pre/post-processing, and explainer handles explanation requests. Explanations are not automatically attached to every prediction; runtime/protocol support matters.

Match modelFormat, ServingRuntime, file layout/library version, URI/credentials, ports/probes and request protocol. A URI alone cannot make every model servable. Custom containers must satisfy the client contract and KServe routing/health-check requirements too.

The official runtime-config chart emits no resources by default. Rendering with `kserve.servingruntime.enabled=true` produces 12 ClusterServingRuntimes. Catalog presence does not establish image currency, security support or model compatibility.

TorchServe's [project notice](https://github.com/pytorch/serve) states that no new features, bug fixes or security patches are planned. Its presence in an older runtime catalog does not make it a maintained default for new production use. Validate a maintained runtime for the model format and GPU requirements.

## Deployment Modes: Knative and Standard

The 0.18.0 names are **Knative** and **Standard**. Serverless and RawDeployment annotation values are deprecated aliases normalized to those names. Inspect serving.kserve.io/deploymentMode and installed inferenceservice-config. The code fallback is Standard, while the downloaded OCI resource chart defaults to Knative. Do not infer installation defaults from terminology alone.

| Item | Knative | Standard |
| --- | --- | --- |
| Workload resources | Knative Service/Revision path | Deployment/Service and selected autoscaler |
| Scaling down | Zero is possible with KPA/policy support and minReplicas=0 | Default HPA path retains at least one; KEDA can support zero with suitable external activation signals |
| Default minReplicas | KServe defaults to one; choosing Knative alone does not enable zero | HPA clamps a requested zero to at least one |
| Dependencies | Knative Serving/networking and selected autoscaler | Chosen ingress/gateway, HPA metrics or KEDA, etc. |
| Startup latency | Scheduling/image/model loading when starting from zero | Restarts, rollouts and scale-out still incur startup latency despite warm replicas |

Neither mode guarantees available replicas or a latency SLA. Validate model loading, readiness, capacity, timeouts and recovery. KEDA scale-from-zero requires a signal observable without running Pods and a reactivation path; CPU/memory metrics alone do not imply request-driven activation.

![InferenceService reconciliation is separate from requests to running model servers; Knative and Standard paths show conditional autoscaling behavior.](../../.gitbook/assets/en-ai-ml-kubeflow-06-kserve-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-06-kserve-0.html)

## Autoscaling and Metrics

Knative KPA supports concurrency/RPS, while Knative's HPA class is another path. Standard selects hpa, keda or external/none through serving.kserve.io/autoscalerClass. Not every Standard deployment creates an HPA.

CPU, external or supported Pod metrics need actual metrics-server/adapter/provider dependencies. GPU requests do not automatically create GPU metrics. Response speed depends on observation intervals, stabilization and model behavior; concurrency metrics are not universally faster.

## Gradual Updates and Canary Traffic

This version's canaryTrafficPercent was verified in the **Knative Revision traffic-splitting path**. KServe sets the previous rolled-out revision and new revision as Knative Service traffic targets; Knative networking distributes requests. The KServe controller is not the proxy for every inference call.

Do not equate a Standard Deployment rolling update with that revision-percentage routing. Weighted routing in Standard needs separately designed services/gateway/mesh or rollout tooling and clear ownership. When using [Istio traffic management](../../service-mesh/istio/traffic-management/04-traffic-splitting.md) or [Argo Rollouts](../../service-mesh/istio/advanced/08-argo-rollouts.md), avoid conflicting ownership of KServe-managed objects.

A percentage alone does not validate quality or automate promotion/rollback. Check comparison metrics, errors/latency, retained revisions/model artifacts and route readiness.

## GPU Inference on EKS

A Pod's nvidia.com/gpu request enables scheduling/device allocation. Actual GPU inference requires compatible CUDA/drivers, server image, model backend and device configuration. Review Triton model configuration or framework device selection; a GPU request does not automatically move a CPU model to GPU.

Karpenter provisions for eligible Pending Pods, NodePools, quotas and available capacity. KServe/Knative/HPA/KEDA Pod scaling and EC2 provisioning/reclamation are separate loops. Even at zero model Pods, other workloads or disruption policies can keep nodes and costs running.

## Validation and Sources

Official 0.18.0 OCI CRD/resource/runtime-config charts were pulled and rendered locally for schema/config inspection. Mode aliasing, HPA minimums, KEDA ScaledObject and Knative traffic code were reviewed. No model download/serving, GPU, cluster autoscaling or live canary request was executed.

- [0.18.0 mode names and defaults](https://github.com/kserve/kserve/blob/v0.18.0/pkg/constants/constants.go)
- [HPA minimum replica handling](https://github.com/kserve/kserve/blob/v0.18.0/pkg/controller/v1beta1/inferenceservice/reconcilers/hpa/hpa_reconciler.go)
- [KEDA ScaledObject handling](https://github.com/kserve/kserve/blob/v0.18.0/pkg/controller/v1beta1/inferenceservice/reconcilers/keda/keda_reconciler.go)
- [Knative traffic handling](https://github.com/kserve/kserve/blob/v0.18.0/pkg/controller/v1beta1/inferenceservice/reconcilers/knative/ksvc_reconciler.go)
- [0.20.0 release](https://github.com/kserve/kserve/releases/tag/v0.20.0)

## Next Steps

Connect this serving path to the architecture, Pipelines, Notebooks, Katib and Trainer chapters in the [Kubeflow series](README.md), while treating model-artifact deployment and validation as separate steps.

---

[Return to Main Page](./README.md)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/ai-ml/kubeflow/06-kserve-quiz.md).

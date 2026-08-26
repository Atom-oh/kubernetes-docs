# Part 6: KServe — Model Serving on Kubernetes

> **Supported Versions**: KServe (bundled web app v0.16.1 in Kubeflow Community Distribution 26.03)
> **Last Updated**: August 19, 2026

## Lab Environment Setup

To follow along with the examples in this document, you will need the following tools and environment:

### Required Tools

* kubectl v1.34 or later, a working EKS cluster
* Kubeflow installed (Part 1), with the KServe web app visible in the Central Dashboard
* [Karpenter](../../autoscaling/02-karpenter.md) with a GPU-capable `NodePool`/`EC2NodeClass` pair, if you plan to serve GPU-backed models
* Knative Serving installed on the cluster, if you plan to use KServe's Serverless deployment mode

## What Is KServe, and How Does It Relate to Kubeflow?

Parts 1-5 covered Kubeflow's overall architecture, Pipelines, Notebooks, Katib, and the Kubeflow Trainer — everything needed to get a model *trained* on EKS. This final part covers what happens after training: serving that model as a scalable, production-grade inference endpoint with **KServe**.

KServe did not start life as an independent project. It began inside Kubeflow as **KFServing**, the component responsible for turning a trained model into a running inference endpoint. As the project matured, it was spun out into its own top-level, standalone repository and renamed **KServe** — it is no longer a Kubeflow-only subcomponent, and it can be installed and operated on any Kubernetes cluster with no Kubeflow present at all.

Kubeflow, in turn, still bundles KServe as its default model-serving layer: the Central Dashboard's model-serving web app is a thin UI on top of the KServe CRDs, and the Kubeflow Community Distribution pins a specific version of that web app alongside the rest of the distribution's components.

This split matters for one practical reason: **the KServe controller/CRD version and the Kubeflow web-app UI version are not the same number, and they don't move in lockstep.** KServe has its own independent release cadence, driven by its own maintainers and its own roadmap, separate from the Kubeflow Community Distribution's calendar-versioned release train (the `26.03` in this document's version line refers to the distribution, not to KServe itself). The Kubeflow Community Distribution 26.03 release bundles the KServe web application at **v0.16.1** — but that number describes the dashboard integration, not necessarily the version of the underlying KServe controller and CRDs a given cluster is running. A platform team can, and often does, upgrade the KServe controller independently of the Kubeflow web app that talks to it. When you're troubleshooting an `InferenceService`, check the controller/CRD version installed on the cluster directly (for example, via the KServe controller manager's image tag) rather than assuming it matches whatever version is printed in the Kubeflow dashboard.

The core abstraction KServe exposes, regardless of which version is installed, is the **`InferenceService`** custom resource — a single Kubernetes object that describes a model, how to serve it, and how it should scale.

## InferenceService Anatomy: Predictor, Transformer, Explainer

An `InferenceService` is built from up to three logical components, only one of which is required:

* **Predictor** (required) — the model server itself. This is the component that actually loads the model artifact and answers inference requests. KServe ships built-in predictor support for common frameworks — SKLearn, XGBoost, PyTorch (via TorchServe), and NVIDIA Triton Inference Server are typical examples — so a predictor spec for one of these frameworks can point at a model artifact location and get a working server without writing any serving code. For anything outside those built-in servers, a predictor can instead run a **custom container** that implements KServe's inference protocol itself.
* **Transformer** (optional) — a pre/post-processing step that sits in front of the predictor. A transformer typically handles input feature engineering before a request reaches the model, and/or reshapes the model's raw output into whatever format downstream consumers expect. Splitting this out from the predictor keeps the model server itself generic and reusable across different client contracts.
* **Explainer** (optional) — a component that produces model explanations (for example, feature-importance or counterfactual explanations) alongside or instead of a plain prediction, useful where a consuming application needs to justify a model's output rather than just receive it.

Only the predictor is mandatory; many production `InferenceService` objects consist of a predictor alone, adding a transformer or explainer only when the use case specifically calls for pre/post-processing or explainability.

## Deployment Modes: Serverless vs. Raw Deployment

KServe supports two distinct deployment modes for how an `InferenceService`'s pods actually get created and managed on the cluster. Choosing between them is one of the most consequential decisions when running KServe on EKS.

### Serverless mode (Knative-based)

In Serverless mode, KServe delegates pod lifecycle management to **Knative Serving**. Knative sits between the `InferenceService` and the underlying Deployment, watching request traffic and scaling the predictor (and any transformer/explainer) pods up and down — including all the way down to **zero pods** when there is no traffic at all. This is the headline feature of Serverless mode: a model that receives requests intermittently doesn't need to keep any pods, and therefore no GPU, running while it's idle.

The trade-off is **cold-start latency**. When a request arrives for a model currently scaled to zero, Knative has to schedule a new pod, wait for the container to start, and wait for the model server to load the model artifact into memory before that first request can be answered. For large models on GPU-backed instances, this cold start can be substantial — model artifact download and GPU driver/runtime initialization both add real time before the pod is ready to serve.

### Raw Deployment mode

In Raw Deployment mode, KServe manages a plain Kubernetes **Deployment**, **Service**, and (optionally) **HorizontalPodAutoscaler** directly — no Knative dependency at all. This mode is simpler operationally (one less system to install, upgrade, and reason about on the cluster) and avoids Knative's cold-start behavior entirely, since it never scales below the Deployment's configured minimum replica count. The cost is that Raw Deployment mode has **no scale-to-zero**: at least the minimum number of predictor pods (and their GPUs, if any) are always running, whether or not there's traffic.

### Choosing between them

| Consideration | Serverless (Knative) | Raw Deployment |
| --- | --- | --- |
| Scale-to-zero | Yes | No |
| Cold-start latency on scale-up from zero | Present, can be significant for large/GPU models | Not applicable |
| Extra cluster dependency | Requires Knative Serving installed | None |
| Best fit | Spiky, intermittent, or low-traffic inference workloads where idle GPU cost matters | Latency-sensitive or steady-traffic workloads where a warm pod must always be available |

The practical rule of thumb: if a model's GPU cost sitting idle between requests is a real budget concern and the workload can tolerate an occasional cold-start delay, Serverless mode's scale-to-zero is worth the added Knative dependency. If the workload needs consistently low latency on every request, or already has steady enough traffic that pods are rarely idle anyway, Raw Deployment mode's simplicity and warm-pod guarantee are usually the better fit.

![Flowchart of a KServe InferenceService: a client request enters the InferenceService, optionally passes through a transformer and/or explainer, then a deployment-mode decision routes it to either a scale-to-zero Knative pod (serverless) or a plain Deployment with HPA (raw), after which the model server loads the artifact and returns a response.](../../.gitbook/assets/en-ai-ml-kubeflow-06-kserve-0.png)

## Autoscaling: Knative Concurrency/RPS vs. HPA

The two deployment modes don't just differ in whether they can scale to zero — they use fundamentally different autoscaling mechanics while a workload is running at all.

* **Serverless mode** uses **Knative's own autoscaler**, which scales pods based on request-level signals — typically **concurrency** (how many requests are being handled by a pod at once) or **requests per second (RPS)** — rather than resource utilization. This tends to be a more direct fit for inference workloads, where a slow model saturates on concurrent requests well before it saturates CPU, and scaling on the request-level signal reacts faster to a burst of traffic than a CPU-based signal would.
* **Raw Deployment mode** relies on a standard Kubernetes **HorizontalPodAutoscaler**, scaling on CPU/memory utilization or custom metrics (for example, a GPU utilization metric surfaced through a metrics adapter) — the same autoscaling model used by any other Kubernetes Deployment on the cluster.

Neither mechanism is universally "better" — the right choice tracks the same deployment-mode decision from "Deployment Modes: Serverless vs. Raw Deployment" above. Concurrency/RPS-based scaling suits bursty inference traffic where request-level backpressure is the real bottleneck; HPA-based scaling suits workloads where CPU/GPU utilization is already a reliable proxy for load and the team doesn't want to introduce Knative just to get request-level signals.

## Canary Rollouts for Gradual Model Updates

Rolling out a new model version safely — verifying it on a fraction of real traffic before committing to it fully — is a core serving concern, and KServe has a built-in mechanism for it. An `InferenceService` can be updated to point at a new model revision, and KServe splits live traffic between the previous (stable) revision and the new (canary) revision according to a configured percentage. From there, traffic can gradually shift more to the new revision as confidence grows, or roll back to the previous revision by simply reverting the traffic split if the new one misbehaves.

This is a different mechanism from the Istio- and Argo Rollouts-based traffic-splitting patterns covered elsewhere in this documentation site (see the [Istio traffic management](../../service-mesh/istio/traffic-management/04-traffic-splitting.md) and [Argo Rollouts](../../service-mesh/istio/advanced/08-argo-rollouts.md) material) — KServe's canary rollout operates at the level of `InferenceService` revisions specifically, built into the KServe control plane itself, rather than through a service mesh's traffic-splitting primitives or a general-purpose progressive-delivery controller. A platform team already standardized on Istio or Argo Rollouts for every other workload's canary releases should be aware that KServe's own mechanism is a separate, model-serving-specific path — not a replacement requirement, but a distinct tool worth knowing about when the workload in question is specifically an `InferenceService`.

## GPU Inference on EKS

Serving a model on a GPU is a matter of the predictor spec requesting GPU resources the same way any Kubernetes pod would — through the container's resource requests/limits against the GPU device plugin's advertised resource (for example, an NVIDIA GPU resource type). KServe's built-in predictor servers for frameworks like PyTorch and Triton are GPU-aware out of the box, so once a predictor spec requests a GPU, the underlying model server uses it for inference without further KServe-specific configuration.

The node-provisioning side of that request is where [Karpenter's GPU node pools](../../autoscaling/02-karpenter.md) become directly relevant, as covered in this site's autoscaling material. An `InferenceService` predictor pod requesting a GPU resource that no existing node can satisfy triggers Karpenter to provision a matching GPU-backed EC2 instance. Karpenter's consolidation behavior can then right-size or reclaim that capacity once the pod no longer needs it — particularly relevant in Serverless mode, where a predictor scaling to zero means the GPU node backing it becomes a consolidation candidate rather than sitting reserved indefinitely. The interaction between KServe's own scaling decisions (see "Autoscaling: Knative Concurrency/RPS vs. HPA" above) and Karpenter's node-level response to them follows the same general two-tier autoscaling pattern used elsewhere in this documentation for other autoscaled workloads on EKS — one control loop decides how many pods are needed, and a separate, independent control loop decides how many nodes are needed to run them.

## Next Steps

KServe turns a trained model into a Kubernetes-native inference endpoint through a single `InferenceService` resource, built around a required predictor and optional transformer/explainer components. The most consequential operational decision is Serverless (Knative-backed, scale-to-zero, concurrency/RPS autoscaling, cold-start risk) versus Raw Deployment (plain Deployment/HPA, always-warm, no Knative dependency) — a decision that should be driven by whether idle GPU cost or consistent low latency matters more for a given model's traffic pattern. Built-in canary rollouts give KServe its own model-specific progressive-delivery path, distinct from the Istio/Argo Rollouts mechanisms used elsewhere on the platform, and GPU-backed predictors compose directly with Karpenter's GPU node pools for right-sized inference capacity on EKS.

This closes out the six-part Kubeflow on EKS series: architecture and installation (Part 1), Pipelines (Part 2), Notebooks (Part 3), Katib (Part 4), the Kubeflow Trainer (Part 5), and this part's model-serving layer with KServe.

---

[Return to Main Page](./README.md)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/ai-ml/kubeflow/06-kserve-quiz.md).

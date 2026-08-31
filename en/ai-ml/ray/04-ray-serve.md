# Part 4: Ray Serve

> **Supported Versions**: Ray 2.57.0
> **Last Updated**: August 20, 2026

## Lab Environment Setup

To follow along with the examples in this document, you will need the following tools and environment:

### Required Tools

* Python 3.10+
* `pip install "ray[serve]"` for general Ray Serve deployments, or `pip install "ray[llm]"` instead if you plan to follow the Ray Serve LLM section below — it pulls in vLLM and related dependencies that `ray[serve]` does not include
* kubectl v1.34 or later, pointed at a working Amazon EKS cluster, if you plan to test the RayService path
* A GPU-capable `NodePool`/`EC2NodeClass` pair provisioned via Karpenter, if you plan to serve GPU-backed models

## What Ray Serve Is

[Part 1](01-architecture.md) introduced the actor as Ray's primitive for stateful, addressable Python objects that keep state in memory between calls. Ray Serve is a model-serving library built directly on that primitive: a Serve deployment is implemented as a Ray actor, or a group of actor replicas, and Ray Serve routes incoming HTTP or gRPC requests to those replicas. A model that's loaded once into a replica's memory can then answer many requests without reloading it, which is exactly the pattern actors were designed for.

A single deployment scales horizontally simply by adding more actor replicas behind Ray Serve's request router, the same way any actor-backed service scales in Ray. More interestingly, Ray Serve lets multiple deployments compose into one serving pipeline, called an application. A common example is a two-step pipeline: one deployment handles preprocessing (tokenization, image resizing, feature extraction) and hands its output to a second deployment that runs the actual model inference. Each deployment in that pipeline can be scaled, versioned, and resourced independently, because each is still just a group of actor replicas underneath.

![A client request flows through Ray Serve Ingress into Preprocess and Model Inference actor deployments and back as a response, while a bottom-up autoscaling chain of the Ray Serve Autoscaler, the Ray/KubeRay Autoscaler, and Karpenter watches queue depth and pending Pods to scale replicas, worker Pods, and nodes in turn.](../../../assets/diagrams/rendered/en-ai-ml-ray-04-ray-serve-0.svg)

## Ray Serve LLM

Serving large language models is enough of a distinct pattern — continuous batching, token streaming, an OpenAI-compatible request shape — that Ray provides a dedicated set of building blocks for it: the `ray.serve.llm` module. Rather than hand-assembling a deployment that manages a vLLM engine instance itself, `ray.serve.llm` gives you higher-level constructs purpose-built for LLM serving, layered on top of Ray Serve's general deployment model described above.

`ray.serve.llm` documents vLLM as its supported inference engine, and its OpenAI-compatible API is designed to line up closely with vLLM's own OpenAI-compatible server, so most `engine_kwargs` that work with a plain `vllm serve` invocation carry over. In practice, that means the same production Ray Serve capabilities — autoscaling, multi-model serving, and Ray's usual distributed-actor placement — apply to LLM serving too, while the LLM-specific plumbing (loading and configuring the vLLM engine, exposing an OpenAI-compatible endpoint) is handled by `ray.serve.llm` rather than something you build by hand. Check the current `docs.ray.io/en/latest/serve/llm/` documentation for the exact configuration surface before depending on specific field names, since this is one of Ray Serve's more actively evolving areas.

## Autoscaling a Serve Deployment

Ray Serve deployments have their own autoscaling layer, separate from the cluster-level autoscaling covered in [Part 2](02-kuberay-operator.md). Where the Ray/KubeRay autoscaler decides how many worker Pods a RayCluster needs, Ray Serve's autoscaler answers a narrower question one layer up: how many actor replicas does *this specific deployment* need right now, based on the request load it's actually seeing? Ray Serve compares the number of ongoing requests per replica — queued plus in-flight — against a target value, and scales replicas up or down to keep actual load close to that target, within a configured minimum and maximum replica count.

That gives this documentation site's now-familiar three-tier autoscaling picture for a Serve application running on EKS:

1. **Ray Serve's autoscaler** decides how many actor replicas a deployment needs, based on request load.
2. **The Ray/KubeRay autoscaler** (covered in [Part 2](02-kuberay-operator.md)) decides how many Ray worker Pods the underlying RayCluster needs, based on pending actor placement — including the replicas Ray Serve's autoscaler just asked for.
3. **Karpenter** decides how many EC2 nodes are needed to actually run those worker Pods, the same mechanism described in [Karpenter](../../autoscaling/02-karpenter.md).

Each layer only sees the layer immediately below it. Ray Serve's autoscaler has no idea whether a new replica lands on an existing node or triggers a new one; it just asks for more replicas. Whether that request turns into a new EC2 node — and how long that takes — is Karpenter's problem, one layer further down.

## GPU Inference

A model-inference deployment that needs a GPU requests one the same way any other Ray workload does: through Ray's normal per-actor resource request, the same mechanism [Part 3](03-ray-train-tune.md) covers for Ray Train and Ray Tune workers. Ray Serve schedules that deployment's actor replicas onto workers that can satisfy the requested GPU count, and — as covered in [Part 2](02-kuberay-operator.md) — the worker group's Pod spec is what actually advertises GPU capacity to the Ray scheduler in the first place.

This is also where Ray Serve's autoscaling and Karpenter's node-provisioning lead time interact in exactly the way they do for other GPU workloads on this site: when Ray Serve's autoscaler decides an inference deployment needs another replica and none of the existing GPU worker Pods have room, that replica request turns into a pending Pod, and Karpenter has to provision a new GPU-backed EC2 node before the replica can actually start serving traffic. A serving application that scales its GPU replica count aggressively should account for that provisioning lead time — see [Karpenter](../../autoscaling/02-karpenter.md) for how node provisioning latency for GPU instance types works in more depth.

## RayService in Production

Running a Serve application by itself, outside Kubernetes, is fine for local development, but production deployments on EKS use the `RayService` CRD introduced in [Part 2](02-kuberay-operator.md). RayService manages the underlying RayCluster and the Serve application deployed on top of it as one unit, and it's specifically the resource that supports rolling out a new application version, or a changed RayCluster spec, aimed at not dropping in-flight requests — check the current KubeRay release notes for this upgrade path's maturity and prerequisites. This document doesn't re-explain RayService's CRD mechanics; see Part 2 for that.

In practice, this means the deployment topology described earlier in this document — an application composed of one or more deployments, each autoscaling its own actor replica count — is what a `RayService` object manages the lifecycle of on a real EKS cluster, while the Ray/KubeRay and Karpenter autoscaling tiers keep operating underneath it exactly as they do for any other RayCluster.

## Next Steps

That's the end of this four-part Ray series. [Part 1](01-architecture.md) covered Ray's core primitives — tasks, actors, and the object store. [Part 2](02-kuberay-operator.md) covered running Ray clusters declaratively on Kubernetes through KubeRay's `RayCluster`, `RayJob`, and `RayService` CRDs, and the Ray/KubeRay-plus-Karpenter autoscaling split. [Part 3](03-ray-train-tune.md) covered distributed training and hyperparameter tuning on top of that cluster. This part closed the loop with Ray Serve: deployments built on the actor primitive from Part 1, composed into applications, autoscaled on their own request-load metric, and — in production — managed end to end through the RayService CRD from Part 2.

[Return to Main Page](./README.md)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/ai-ml/ray/04-ray-serve-quiz.md).

# Ray Serve Quiz

This quiz tests your understanding of Ray Serve's deployment model, Ray Serve LLM, Serve-level autoscaling, GPU inference, and how RayService manages a production Serve application on EKS.

## Multiple Choice Questions

1. What is a Ray Serve deployment implemented as, underneath Ray Serve's routing layer?
   - A) A standalone container with no relation to Ray's core primitives
   - B) A Ray actor, or a group of actor replicas, that Ray Serve routes HTTP/gRPC requests to
   - C) A Kubernetes CronJob that runs on a fixed schedule
   - D) A single Ray task that re-executes for every incoming request

<details>

<summary>Show Answer</summary>

**Answer: B) A Ray actor, or a group of actor replicas, that Ray Serve routes HTTP/gRPC requests to**

**Explanation:**
Ray Serve is built directly on Ray's actor primitive. A deployment is one actor or a group of actor replicas, and Ray Serve routes incoming HTTP/gRPC requests to those replicas — which is why a model loaded once into a replica's memory can answer many requests without reloading.
</details>

2. What is an "application" in Ray Serve terms?
   - A) A single deployment with no ability to scale
   - B) One or more composed deployments — for example, a preprocessing deployment feeding a model-inference deployment — forming a serving pipeline
   - C) A RayJob that runs once and tears itself down
   - D) The Kubernetes namespace a RayCluster runs in

<details>

<summary>Show Answer</summary>

**Answer: B) One or more composed deployments — for example, a preprocessing deployment feeding a model-inference deployment — forming a serving pipeline**

**Explanation:**
Ray Serve lets multiple deployments compose into one serving pipeline called an application, such as a preprocessing step feeding its output into a model-inference step. Each deployment in that pipeline can still scale, version, and be resourced independently.
</details>

3. What is `ray.serve.llm`, and which inference engine does it document as its supported engine?
   - A) A generic batch-processing module with no relation to LLMs; it supports any engine
   - B) A dedicated set of building blocks for LLM serving, built on top of Ray Serve's general deployment model, documenting vLLM as its supported inference engine
   - C) A replacement for Ray Serve that does not use actors
   - D) A module exclusive to training LLMs, not serving them

<details>

<summary>Show Answer</summary>

**Answer: B) A dedicated set of building blocks for LLM serving, built on top of Ray Serve's general deployment model, documenting vLLM as its supported inference engine**

**Explanation:**
`ray.serve.llm` provides higher-level constructs tailored for LLM serving patterns, layered on Ray Serve's general deployment model. It documents vLLM as its supported inference engine and offers an OpenAI-compatible API designed to line up closely with vLLM's own OpenAI-compatible server.
</details>

4. What does Ray Serve's own autoscaler decide, and what does it compare to make that decision?
   - A) How many EC2 nodes Karpenter should provision, based on billing data
   - B) How many actor replicas a specific deployment needs, by comparing ongoing requests per replica (queued plus in-flight) against a target value
   - C) How many worker Pods a RayCluster needs, based on pending task placement
   - D) Which AWS region to deploy the RayCluster into

<details>

<summary>Show Answer</summary>

**Answer: B) How many actor replicas a specific deployment needs, by comparing ongoing requests per replica (queued plus in-flight) against a target value**

**Explanation:**
Ray Serve's autoscaler is a layer separate from cluster-level autoscaling. It compares the ongoing requests per replica against a target and scales that deployment's replica count up or down within a configured minimum and maximum.
</details>

5. In the three-tier autoscaling picture for a Ray Serve application on EKS, which layer sits directly above Karpenter?
   - A) The AWS Load Balancer Controller
   - B) The Ray/KubeRay autoscaler, which decides worker Pod count based on pending actor placement
   - C) A separate Kubernetes Horizontal Pod Autoscaler watching CPU usage
   - D) The client application making requests

<details>

<summary>Show Answer</summary>

**Answer: B) The Ray/KubeRay autoscaler, which decides worker Pod count based on pending actor placement**

**Explanation:**
The three tiers are: Ray Serve's autoscaler decides replica count, the Ray/KubeRay autoscaler decides worker Pod count based on pending actor placement (including replicas Serve's autoscaler requested), and Karpenter decides node count to run those Pods.
</details>

6. How does a GPU-backed Ray Serve deployment request a GPU?
   - A) Through a separate GPU reservation API unique to Ray Serve
   - B) Through Ray's normal per-actor resource request mechanism, the same one used by Ray Train and Ray Tune workers
   - C) By manually SSHing into a worker node and setting an environment variable
   - D) GPUs cannot be requested by Ray Serve deployments at all

<details>

<summary>Show Answer</summary>

**Answer: B) Through Ray's normal per-actor resource request mechanism, the same one used by Ray Train and Ray Tune workers**

**Explanation:**
A model-inference deployment that needs a GPU requests one through the same actor-level resource request mechanism Ray Train and Ray Tune use, and the worker group's Pod spec is what advertises GPU capacity to the Ray scheduler.
</details>

7. What happens when Ray Serve's autoscaler requests a new GPU replica but no existing GPU worker Pod has room for it?
   - A) The request is silently dropped and no new replica is ever created
   - B) The replica request becomes a pending Pod, and Karpenter must provision a new GPU-backed EC2 node before that replica can start serving traffic
   - C) Ray Serve automatically falls back to running the model on CPU
   - D) The Ray autoscaler bypasses Karpenter entirely and creates the EC2 instance itself

<details>

<summary>Show Answer</summary>

**Answer: B) The replica request becomes a pending Pod, and Karpenter must provision a new GPU-backed EC2 node before that replica can start serving traffic**

**Explanation:**
Ray Serve's autoscaling and Karpenter's node-provisioning lead time interact the same way they do for other GPU workloads: a pending Pod triggers Karpenter to provision a matching node, and a serving application scaling GPU replicas aggressively should account for that lead time.
</details>

8. What does the RayService CRD manage in production, and what capability does it specifically support?
   - A) Only the Serve application, with no relationship to the underlying RayCluster
   - B) The underlying RayCluster and the Serve application deployed on top of it together, supporting zero-downtime rolling upgrades
   - C) Only batch jobs that run once and tear down, with no serving capability
   - D) A static, unchangeable snapshot of a Ray cluster that cannot be upgraded

<details>

<summary>Show Answer</summary>

**Answer: B) The underlying RayCluster and the Serve application deployed on top of it together, supporting zero-downtime rolling upgrades**

**Explanation:**
RayService manages a RayCluster together with its Serve application as one unit, and is the resource that supports zero-downtime rolling upgrades for rolling out a new application version or RayCluster spec without dropping in-flight requests -- check the current KubeRay release notes for that upgrade path's maturity before relying on it in production.
</details>

## Short Answer Questions

9. Explain why Ray Serve's autoscaler and the Ray/KubeRay autoscaler are described as separate layers that "only see the layer immediately below" them.

<details>

<summary>Show Answer</summary>

**Answer:**
Ray Serve's autoscaler only decides how many actor replicas a specific deployment needs, based on request load; it has no visibility into whether a new replica lands on an existing worker Pod or requires a new one. The Ray/KubeRay autoscaler, one layer down, only reacts to pending actor placement (including the replicas Serve's autoscaler asked for) to decide worker Pod count, without knowing anything about request-level metrics. Karpenter, another layer down, only reacts to pending Pods to decide node count.

**Explanation:**
Each control loop answers a narrower question than the one above it, and the layers communicate only indirectly — through the ordinary state each layer produces (replica requests become pending Pods, pending Pods become pending nodes) — not through direct coordination.
</details>

10. A team is deploying a two-step Ray Serve application (preprocessing, then GPU-backed model inference) to production on EKS. Describe how the deployment topology, autoscaling, and lifecycle management described in this document fit together for that application.

<details>

<summary>Show Answer</summary>

**Answer:**
The application is composed of two deployments — a preprocessing deployment and a model-inference deployment — each implemented as actor replicas, with the preprocessing deployment's output feeding the inference deployment. Each deployment autoscales its own replica count independently via Ray Serve's autoscaler, based on its own request load. The inference deployment's actor replicas request GPUs through Ray's normal per-actor resource mechanism, and if Ray Serve's autoscaler needs more GPU replicas than existing worker Pods can host, the Ray/KubeRay autoscaler requests more worker Pods and Karpenter provisions matching GPU-backed EC2 nodes. In production, a `RayService` object manages the whole application's RayCluster and Serve rollout together, including zero-downtime upgrades when the application or cluster spec changes.

**Explanation:**
This ties together every concept in the document: the actor-based deployment/application model, Serve's own autoscaling layer, the three-tier autoscaling split with Ray/KubeRay and Karpenter, GPU resource requests, and RayService as the production lifecycle manager for all of it.
</details>

---

[Return to Learning Materials](../../../ai-ml/ray/04-ray-serve.md)

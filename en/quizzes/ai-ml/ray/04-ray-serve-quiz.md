# Ray Serve Quiz

## Multiple Choice Questions

1. How does a Serve Deployment relate to a Kubernetes Deployment?
   - A) They are identical
   - B) It is a logical actor-replica unit, not one-to-one with Pods
   - C) Each replica requires one EC2 node
   - D) Serve does not use actors

<details>
<summary>Show Answer</summary>

**Answer: B**

One Ray Pod can host several replica actors.
</details>

2. What is the 2.58.0 default proxy location?
   - A) Always one on the head
   - B) EveryNode on nodes hosting replicas
   - C) Every EC2 node unconditionally
   - D) Always Disabled

<details>
<summary>Show Answer</summary>

**Answer: B**

HeadOnly and Disabled are explicit choices. Distinguish stale architecture prose from the current API.
</details>

3. How does the default deployment differ from num_replicas="auto"?
   - A) Both immediately start 100 replicas
   - B) Default fixed 1; auto applies min 1/max 100/target 2
   - C) Default GPU 1; auto GPU 100
   - D) Neither supports autoscaling

<details>
<summary>Show Answer</summary>

**Answer: B**

A directly constructed AutoscalingConfig defaults max to 1, so specify the intended bound.
</details>

4. What is the max_queued_requests scope?
   - A) One cluster-global queue
   - B) Each caller, such as a proxy or handle
   - C) GPU KV-cache capacity
   - D) RayCluster Pod count

<details>
<summary>Show Answer</summary>

**Answer: B**

Default -1 is unlimited; exceeding a configured bound can reject HTTP requests or raise handle BackPressureError.
</details>

5. Does a pending replica actor always create a new Pod and EC2 node?
   - A) Always one-to-one
   - B) No; existing capacity, group bounds, placement, and autoscaler enablement matter
   - C) It automatically becomes a CPU model
   - D) Serve directly creates EC2 nodes

<details>
<summary>Show Answer</summary>

**Answer: B**

Inspect actor placement, Pod size, and node provisioning separately.
</details>

6. What was verified about 2.58.0 LLM backends?
   - A) Only vLLM exists
   - B) vLLM and SGLang backends exist; check their dependencies/configuration separately
   - C) Every engine kwarg is identical across engines
   - D) ray[serve]includes all LLM weights

<details>
<summary>Show Answer</summary>

**Answer: B**

Inference dependencies and model access/downloads are separate. CPU checks did not validate LLM execution.
</details>

7. Which RayService update statement is accurate?
   - A) Mandatory for every EKS deployment with guaranteed no downtime
   - B) An optional lifecycle path; validate strategy, Gateway, capacity, readiness, and draining
   - C) Always only edits an existing Pod image
   - D) All long streams are always preserved

<details>
<summary>Show Answer</summary>

**Answer: B**

Distinguish application changes, cluster transitions, and actor reconfiguration.
</details>

8. What did the local Echo test verify?
   - A) GPU performance
   - B) LLM quality
   - C) HTTP 200 and DeploymentHandle calls
   - D) Multi-node autoscaling

<details>
<summary>Show Answer</summary>

**Answer: C**

It was a tiny single-node CPU test without a model, LLM, GPU, or cloud deployment.
</details>

## Short Answer Questions

9. Why distinguish max ongoing, autoscaling target, and caller queue limit?

<details>
<summary>Show Answer</summary>

They control different things: requests assigned to replicas, target load for scaling, and waiting requests per caller. One setting does not establish all other bounds or latency guarantees.
</details>

10. Why do cluster tokens or ClusterIP not complete application security?

<details>
<summary>Show Answer</summary>

Verify TLS, each entry point’s authentication/authorization, model-artifact permissions, sensitive request/log handling, and resource/queue/timeout policies separately.
</details>

---

[Return to Learning Materials](../../../ai-ml/ray/04-ray-serve.md)

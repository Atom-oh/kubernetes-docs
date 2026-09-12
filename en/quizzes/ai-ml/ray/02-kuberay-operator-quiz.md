# KubeRay Operator Quiz

## Multiple Choice Questions

1. What does installing the KubeRay operator start?
   - A) Every Ray workload automatically
   - B) The reconciler; workload CRs still need to be created
   - C) Every GPU node
   - D) A Deployment for every worker

<details>
<summary>Show Answer</summary>

**Answer: B**

Operator installation is separate from creating RayCluster, RayJob, or RayService resources.
</details>

2. What does chart 1.7.0 install, and what is RayCronJob’s default state?
   - A) Only three CRDs exist
   - B) An installed RayCronJob CRD always enables scheduling
   - C) Four CRDs, with the RayCronJob feature gate disabled by default
   - D) No v1 API exists

<details>
<summary>Show Answer</summary>

**Answer: C**

Distinguish RayCluster, RayJob, RayService, and RayCronJob.
</details>

3. What is RayJob’s default cleanup behavior?
   - A) Omitted shutdownAfterJobFinishes enables cleanup
   - B) TTL 0 deletes every EC2 instance and PVC
   - C) shutdownAfterJobFinishes defaults false; configure cleanup and preservation
   - D) External clusters are always deleted

<details>
<summary>Show Answer</summary>

**Answer: C**

Check TTL, deletionStrategy, and ownership of shared versus created clusters.
</details>

4. What does RayService incremental upgrade require?
   - A) A feature gate alone guarantees no downtime
   - B) Strategy, Gateway API/implementation, capacity, readiness, and draining
   - C) Only editing one existing Pod image
   - D) A mandatory RayJob

<details>
<summary>Show Answer</summary>

**Answer: B**

It shifts traffic between clusters; it is not simply an in-place Pod rolling update.
</details>

5. Which scaling sequence is appropriate?
   - A) Ray autoscaler directly provisions all EC2 capacity
   - B) Ray demand → KubeRay Pod reconciliation → Kubernetes placement/capacity provisioning
   - C) Karpenter calls Ray actor methods
   - D) Both controllers own the identical resource

<details>
<summary>Show Answer</summary>

**Answer: B**

Image, PVC, or authorization-related Pending states are not fixed solely by adding nodes.
</details>

6. How should idleTimeoutSeconds 60 be interpreted?
   - A) Every worker disappears exactly 60 seconds later
   - B) Reviewed global default; consider group overrides, bounds, activity, and drain conditions
   - C) Whole-RayJob TTL
   - D) Karpenter’s fixed provisioning time

<details>
<summary>Show Answer</summary>

**Answer: B**

Configuration duration and actual deletion completion are different.
</details>

7. Which GPU resource precedence statement is accurate?
   - A) Only Pod limits are used; overrides are ignored
   - B) Structured group resources and rayStartParams can override limits
   - C) Every Pod always has one GPU
   - D) Logical settings create more physical GPUs

<details>
<summary>Show Answer</summary>

**Answer: B**

Align Ray logical resources with device plugins, drivers, and visible hardware.
</details>

8. Does a Helm chart upgrade automatically update existing CRD schemas?
   - A) It always upgrades and deletes them
   - B) No; check stored CR compatibility and the separate CRD update procedure
   - C) CRDs are ordinary Pods
   - D) Always deleting CRDs first is safe

<details>
<summary>Show Answer</summary>

**Answer: B**

Understand Helm crds/ lifecycle limits and the impact of CRD deletion.
</details>

## Short Answer Questions

9. Why are worker replica count and Ray Pod count not always equal?

<details>
<summary>Show Answer</summary>

With numOfHosts, one group replica can correspond to multiple hosts/Pods. Compare the actual spec with generated resources.
</details>

10. Why does enabling Ray token authentication not complete security configuration?

<details>
<summary>Show Answer</summary>

It is separate from TLS and does not replace authentication/authorization for every application endpoint. Review access paths, secret delivery, version support, and organizational policy.
</details>

---

[Return to Learning Materials](../../../ai-ml/ray/02-kuberay-operator.md)

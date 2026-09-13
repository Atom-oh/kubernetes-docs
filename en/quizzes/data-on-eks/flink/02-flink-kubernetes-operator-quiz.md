# Flink Kubernetes Operator Quiz

Check installation, state recovery and autoscaling for Operator 1.15.0 / Flink 2.2.1.

1. How do Deployment and SessionJob differ?

<details>
<summary>Show Answer</summary>

**Answer:** Deployment defines an Application/Session cluster; SessionJob defines a job on an existing managed Session cluster.

**Explanation:** Separate SessionJob management does not isolate shared cluster resources or failures.

</details>

2. Is a historical Kubernetes 1.21+ minimum enough to validate a current EKS deployment?

<details>
<summary>Show Answer</summary>

**Answer:** No. Check current EKS support, client skew and Operator/webhook/CRD compatibility.

**Explanation:** The introduction date of namespace labeling is not a complete support or feature-validation matrix.

</details>

3. Does a blue/green CR automatically switch Kafka/S3 writes without duplicates?

<details>
<summary>Show Answer</summary>

**Answer:** No. Design consumer groups, transactional IDs, sink output and state compatibility separately.

**Explanation:** Managing transitions between child deployments is different from end-to-end data guarantees and needs extra transition capacity.

</details>

4. Is a savepoint upgrade always the safest, slowest, stop-the-world choice?

<details>
<summary>Show Answer</summary>

**Answer:** No universal ranking applies; timing, restorability and fallback depend on the job and state changes.

**Explanation:** Creating a snapshot does not prove serializer, UID or connector compatibility.

</details>

5. What does last-state recovery of an unhealthy job require?

<details>
<summary>Show Answer</summary>

**Answer:** Accessible HA metadata/checkpoints, compatible state, credentials and storage.

**Explanation:** It may avoid a new savepoint, but does not automatically solve metadata loss or stale checkpoints.

</details>

6. Does setting last-state in SessionJob YAML complete stateful-upgrade preparation?

<details>
<summary>Show Answer</summary>

**Answer:** No. The effective Session/job configuration needs checkpointing, storage and recovery prerequisites.

**Explanation:** Check the validator and restore path, not just the mode string.

</details>

7. What is the main scaling target of the Flink autoscaler?

<details>
<summary>Show Answer</summary>

**Answer:** Parallelism of individual job-graph vertices.

**Explanation:** This differs from HPA replica scaling; actual pod/node counts depend on slot allocation and resource-management layers.

</details>

8. Is a downstream target rate just the sum of current upstream output rates?

<details>
<summary>Show Answer</summary>

**Answer:** It combines upstream target rates multiplied by edge output ratios and propagates backlog-processing targets.

**Explanation:** Output selectivity and required future capacity matter.

</details>

9. Does the autoscaler ignore every CPU/memory signal?

<details>
<summary>Show Answer</summary>

**Answer:** The main parallelism model uses rates/busy time, but memory/GC pressure, quotas and optional memory tuning also exist.

**Explanation:** Memory tuning defaults to false; this is still different from CPU-based HPA.

</details>

10. Must Flink parallelism always be a divisor of maximum parallelism?

<details>
<summary>Show Answer</summary>

**Answer:** No. Autoscaler alignment preferences for balanced key groups/partitions differ from Flink's allowed range.

**Explanation:** Check alignment mode, keyed inputs and source partitions. Changing maximum parallelism for existing state needs compatibility review.

</details>

11. Is every autoscaler rescale a full last-state upgrade?

<details>
<summary>Show Answer</summary>

**Answer:** No. Where possible it uses in-place resource-requirements APIs; conditions can require redeployment.

**Explanation:** In-place scaling does not guarantee absence of task restarts or state-recovery costs.

</details>

12. Why do these examples use Flink 2.2.1 rather than the latest 2.3.0?

<details>
<summary>Show Answer</summary>

**Answer:** To pin an integration baseline checked alongside published Operator/connector compatibility tables.

**Explanation:** A newer value accepted by a CRD enum does not prove runtime compatibility.

</details>

13. Does a chart logging configuration prove reporter JARs and collection servers are installed?

<details>
<summary>Show Answer</summary>

**Answer:** No. Distinguish chart files, runtime-image JARs, reporter activation and the collection backend.

**Explanation:** The 1.15 chart includes Log4j/Logback configuration, but YAML alone does not create an entire metrics pipeline.

</details>

14. What else should be checked when setting watchNamespaces?

<details>
<summary>Show Answer</summary>

**Answer:** Target namespace existence, generated job service accounts/Roles/RoleBindings and other grants.

**Explanation:** An empty list watches all namespaces. Watch scope alone does not fully isolate tenants.

</details>

15. Is a ten-minute metrics window optimal for every workload?

<details>
<summary>Show Answer</summary>

**Answer:** No. Tune the window, stabilization and scale-down interval together with actual SLOs.

**Explanation:** Short windows can amplify noise; long ones can delay response. Use observation and load tests.

</details>

16. Does the default webhook installation require cert-manager?

<details>
<summary>Show Answer</summary>

**Answer:** Yes. The reviewed chart creates Certificate and Issuer resources and has no internal certificate-generation Job.

**Explanation:** Check controllers/webhook/cainjector and Certificate readiness, not only CRD existence.

</details>

17. Can a default Flink image run a fictitious order-events JAR?

<details>
<summary>Show Answer</summary>

**Answer:** Not unless the JAR was packaged into it. The chapter uses the bundled StateMachineExample to verify the execution path.

**Explanation:** A stateless demo is separate from durable-checkpoint/HA recovery validation.

</details>

18. Which settings collect recommendations without applying scaling?

<details>
<summary>Show Answer</summary>

**Answer:** job.autoscaler.enabled=true and job.autoscaler.scaling.enabled=false.

**Explanation:** Use current utilization.target/min/max keys and validate recommendations, state recovery and quotas before enabling actions.

</details>

19. Which condition is used to wait for initial FlinkDeployment readiness?

<details>
<summary>Show Answer</summary>

**Answer:** Running, not Available.

**Explanation:** It reflects observed job/JM state. After updates, distinguish a stale condition from actual reconciliation of the new spec.

</details>

20. For 6,000 backlog records, how does reducing catch-up.duration from 600 to 60 seconds change the extra target rate?

<details>
<summary>Show Answer</summary>

**Answer:** It increases from 10 to 100 records/second.

**Explanation:** A shorter recovery target requires more capacity. This is not a grace period for ignoring backlog; zero disables backlog-based scaling.

</details>

---

[Return to Learning Materials](../../../data-on-eks/flink/02-flink-kubernetes-operator.md)

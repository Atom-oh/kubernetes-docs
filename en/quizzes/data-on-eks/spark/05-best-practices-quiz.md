# Part 5: Best Practices and Security Quiz

Spark 4.2.0 / Hadoop 3.5.0 / AWS SDK v2 2.35.4.

## 1. Which Hadoop/S3A versions match the reviewed Spark 4.2 distribution?

<details>
<summary>Show answer</summary>

Hadoop client and hadoop-aws both use 3.5.0, with AWS SDK v2 bundle 2.35.4 and the resolved runtime dependencies. Recheck bundled versions for another image or EMR.

</details>

## 2. Which IRSA provider fits this SDK v2 combination?

<details>
<summary>Show answer</summary>

software.amazon.awssdk.auth.credentials.WebIdentityTokenFileCredentialsProvider. The old com.amazonaws.auth.WebIdentityTokenCredentialsProvider is not automatically mapped in this combination.

</details>

## 3. What changes when using Pod Identity?

<details>
<summary>Show answer</summary>

Use ContainerCredentialsProvider, service-account associations, trust for pods.eks.amazonaws.com and Agent/node permissions. IRSA annotations and OIDC setup do not replace this path.

</details>

## 4. Does the default S3A chain automatically use IRSA?

<details>
<summary>Show answer</summary>

The reviewed Hadoop 3.5.0 chain includes the container/instance wrapper but not the web-identity provider. Specify the required provider and verify effective identity and prefix access.

</details>

## 5. Why separate driver, executor and History Server service accounts?

<details>
<summary>Show answer</summary>

To separate driver Kubernetes-management rights from each process's S3 data rights. History Server can start with a read-only role when its cleaner is disabled.

</details>

## 6. Does a namespaced Role restrict a driver to only its own executors?

<details>
<summary>Show answer</summary>

No. It grants resource/verb permissions across the namespace without pod-label ownership conditions. Combine admission and trust boundaries to restrict pod creation, other service accounts and host access.

</details>

## 7. Does ClusterRole always mean cluster-wide permission?

<details>
<summary>Show answer</summary>

No. A RoleBinding referencing a ClusterRole can scope namespaced resource permissions to the binding's namespace. Inspect both rules and the binding type/scope.

</details>

## 8. Does spark.authenticate=true provide Spark UI login?

<details>
<summary>Show answer</summary>

No. It authenticates internal connections. Kubernetes-generated app secrets can be propagated through executor environments, making pod-read permissions important. UI authentication, authorization and TLS are separate.

</details>

## 9. What is wrong with a role-label-only NetworkPolicy?

<details>
<summary>Show answer</summary>

Executors from other jobs in the namespace also match. The example shares a unique run ID between driver/executor labels and policies. Labels are not authentication; consider pod creators able to forge them.

</details>

## 10. Does applying this NetworkPolicy block every other path?

<details>
<summary>Show answer</summary>

Policies are additive and require CNI enforcement. This example limits ingress only. Review egress, node/hostNetwork behavior, other allow policies, DNS/API/AWS endpoints and additional plugins separately.

</details>

## 11. Why combine fixed ports with spark.port.maxRetries=0?

<details>
<summary>Show answer</summary>

A collision fails startup instead of silently moving to a port outside the policy. Configure ports and security separately for additional endpoints.

</details>

## 12. Are PrometheusServlet and the executor aggregate endpoint identical?

<details>
<summary>Show answer</summary>

No. /metrics/prometheus/ serves the driver's Dropwizard registry; /metrics/executors/prometheus/ serves driver-collected executor aggregates. Executors do not each get a Spark UI; compare actual series, labels and units.

</details>

## 13. What is correct about a JMX Java agent and operator chart metrics?

<details>
<summary>Show answer</summary>

The agent runs inside the JVM rather than as another process. Default operator chart metrics describe the operator itself; the chart does not automatically install an agent in every Spark JVM.

</details>

## 14. Is creating a PodMonitor sufficient for collection?

<details>
<summary>Show answer</summary>

Prometheus label/namespace selectors, discovery RBAC, pod ports/paths and NetworkPolicy must agree. Verify UP targets and actual series; short jobs can finish between scrapes.

</details>

## 15. Does retaining the driver pod object retain its UI after the job ends?

<details>
<summary>Show answer</summary>

The live UI stops with its JVM. History Server reconstructs from separately persisted event logs, not stdout/stderr or checkpoints.

</details>

## 16. Does merely mounting a History Server configuration file load it?

<details>
<summary>Show answer</summary>

No. The example explicitly uses spark-class org.apache.spark.deploy.history.HistoryServer --properties-file and runs in the foreground. Verify the path, log directory and S3 identity.

</details>

## 17. Does History Server restore every detail of every past job?

<details>
<summary>Show answer</summary>

Event logs must actually be retained and readable. Missing, corrupt, unflushed, deleted or compacted events limit reconstruction. Event logs are not data-recovery checkpoints or output backups.

</details>

## 18. Are an operator, cluster mode and IRSA the only production choices?

<details>
<summary>Show answer</summary>

No. Choose validated direct submission, an operator or EMR, suitable client/cluster mode and IRSA/Pod Identity for the requirements. Test permissions, data correctness, recovery, networking, resources and costs in the actual environment.

</details>

[Guide](../../../data-on-eks/spark/05-best-practices.md)

[README](../../../data-on-eks/spark/README.md)

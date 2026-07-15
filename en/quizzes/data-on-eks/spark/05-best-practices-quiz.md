# Part 5: Best Practices and Security Quiz

This quiz tests your understanding of production-readiness best practices for Spark on EKS: IRSA-based S3 access, observability options, the Spark History Server, resource sizing philosophy, and security hardening beyond IAM.

## Multiple Choice Questions

1. What class must `spark.hadoop.fs.s3a.aws.credentials.provider` be set to so driver/executor pods get S3 access via IRSA?
   - A) `com.amazonaws.auth.EnvironmentVariableCredentialsProvider`
   - B) `com.amazonaws.auth.WebIdentityTokenCredentialsProvider`
   - C) `com.amazonaws.auth.InstanceProfileCredentialsProvider`
   - D) `org.apache.spark.SparkS3CredentialsProvider`

<details>

<summary>Show Answer</summary>

**Answer: B) `com.amazonaws.auth.WebIdentityTokenCredentialsProvider`**

**Explanation:**
This provider reads the web identity token that the EKS Pod Identity webhook projects into the pod (based on the service account's `eks.amazonaws.com/role-arn` annotation) and exchanges it for temporary AWS credentials via STS `AssumeRoleWithWebIdentity`, refreshing them automatically as they expire. This means no static AWS access keys ever need to exist in a Secret, ConfigMap, or container image.
</details>

2. Which Spark configuration keys point the driver and executor pods at an IRSA-bound service account?
   - A) `spark.kubernetes.driver.serviceAccountName` / `spark.kubernetes.executor.serviceAccountName`
   - B) `spark.kubernetes.authenticate.driver.serviceAccountName` / `spark.kubernetes.authenticate.executor.serviceAccountName`
   - C) `spark.hadoop.fs.s3a.serviceAccountName`
   - D) `spark.driver.iamRole` / `spark.executor.iamRole`

<details>

<summary>Show Answer</summary>

**Answer: B) `spark.kubernetes.authenticate.driver.serviceAccountName` / `spark.kubernetes.authenticate.executor.serviceAccountName`**

**Explanation:**
These `spark-submit` configuration keys tell Spark which Kubernetes service account to run the driver and executor pods as. When that service account is annotated with `eks.amazonaws.com/role-arn`, the pods automatically get the projected web identity token needed for IRSA.
</details>

3. What is the main operational advantage of Spark's native `PrometheusServlet` over the JmxSink + JMX Prometheus Exporter pattern?
   - A) It collects a completely different set of metrics
   - B) It requires no external JAR or separate Java agent — it reuses Spark's existing UI port
   - C) It only works with the Spark Operator
   - D) It replaces the need for event logging

<details>

<summary>Show Answer</summary>

**Answer: B) It requires no external JAR or separate Java agent — it reuses Spark's existing UI port**

**Explanation:**
`PrometheusServlet` (available since Spark 3.0) exposes Spark's metrics in Prometheus format directly on the existing UI port. The JmxSink + JMX Prometheus Exporter pattern (what the Spark Operator's Helm chart wires up by default) requires an extra `-javaagent` attached to the JVM and an extra JAR shipped in the image. Both approaches expose the same underlying Spark metrics — they differ in transport and packaging, not in what's measured.
</details>

4. When would you deliberately keep using the JmxSink + JMX Prometheus Exporter pattern instead of switching to `PrometheusServlet`?
   - A) Never — `PrometheusServlet` is strictly better in every case
   - B) When you want to keep using the Spark Operator's default chart wiring or rely on the broader, more mature ecosystem of community Grafana dashboards built around it
   - C) When running Spark outside of Kubernetes
   - D) When `spark.eventLog.enabled` is set to `false`

<details>

<summary>Show Answer</summary>

**Answer: B) When you want to keep using the Spark Operator's default chart wiring or rely on the broader, more mature ecosystem of community Grafana dashboards built around it**

**Explanation:**
The two approaches trade off differently: `PrometheusServlet` is operationally simpler (nothing extra to attach to the JVM), while the JMX exporter pattern already has a mature, wide-ranging set of pre-built Grafana dashboards and is what the Spark Operator's chart wires up out of the box. Neither is universally "better" — the choice depends on what you already have running.
</details>

5. Why can't you just check the live Spark UI to debug a job that finished last night?
   - A) The Spark UI is disabled by default on Kubernetes
   - B) The driver pod that hosted the UI has likely already been reclaimed by Kubernetes
   - C) The Spark UI only shows currently running stages, never historical ones, regardless of pod lifetime
   - D) Live UIs are only available in client deploy mode

<details>

<summary>Show Answer</summary>

**Answer: B) The driver pod that hosted the UI has likely already been reclaimed by Kubernetes**

**Explanation:**
Because the driver pod does its own scheduling and hosts the live Spark UI, once a job finishes (or crashes) and Kubernetes reclaims that pod, the UI disappears along with it. This is exactly the gap the Spark History Server fills — it serves a reconstructed UI from persisted event logs regardless of whether the original driver pod still exists.
</details>

6. What two Spark configuration properties does the Spark History Server need to read a job's persisted event logs from S3?
   - A) `spark.eventLog.enabled` and `spark.history.fs.logDirectory` pointing at the same S3 path used for `spark.eventLog.dir`
   - B) `spark.dynamicAllocation.enabled` and `spark.decommission.enabled`
   - C) `spark.kubernetes.authenticate.driver.serviceAccountName` only
   - D) `spark.metrics.conf` and `spark.ui.port`

<details>

<summary>Show Answer</summary>

**Answer: A) `spark.eventLog.enabled` and `spark.history.fs.logDirectory` pointing at the same S3 path used for `spark.eventLog.dir`**

**Explanation:**
Jobs must have `spark.eventLog.enabled=true` and `spark.eventLog.dir=s3a://...` set so they actually write event logs to S3. The History Server instance then needs `spark.history.fs.logDirectory` set to that same S3 location (plus its own IRSA-bound service account to read it) so it can periodically rescan and serve a reconstructed UI for completed jobs.
</details>

7. According to the resource sizing philosophy recapped in this document, what should driver sizing prioritize?
   - A) Maximum throughput, the same as executors
   - B) Stability — enough headroom that the driver doesn't become a bottleneck or get OOMKilled and take the job down
   - C) Minimum cost, even at the risk of driver instability
   - D) Matching the executor's `spark.executor.memory` value exactly

<details>

<summary>Show Answer</summary>

**Answer: B) Stability — enough headroom that the driver doesn't become a bottleneck or get OOMKilled and take the job down**

**Explanation:**
The driver coordinates the job and tracks task state rather than doing the heavy data processing itself, so its sizing goal is stability. Executors, where the actual processing happens, are sized for throughput instead, tuned against the job's real shuffle volume and per-task memory needs. Neither has a universal numeric default — both should come from benchmarking the actual workload.
</details>

8. Why does the Spark driver's Kubernetes service account need pod-management permissions at all?
   - A) It doesn't — only executors need pod permissions
   - B) The driver creates, watches, and deletes its own executor pods by calling the Kubernetes API directly
   - C) It's required for S3A credential resolution
   - D) It's only needed when using the Spark Operator, not plain `spark-submit`

<details>

<summary>Show Answer</summary>

**Answer: B) The driver creates, watches, and deletes its own executor pods by calling the Kubernetes API directly**

**Explanation:**
As covered in Part 1, the driver acts as its own scheduler on Kubernetes — there's no separate cluster-manager daemon creating executor pods on its behalf. This means the driver's service account needs enough RBAC permissions to manage pods, but the least-privilege version scopes that to a namespaced `Role` limited to exactly the verbs the driver uses, not a cluster-wide `ClusterRole`.
</details>

9. What is wrong with granting the Spark driver's service account a `ClusterRole` with broad pod permissions?
   - A) `ClusterRole` objects don't support `RoleBinding`
   - B) It violates least privilege — a compromised or misbehaving driver could then affect pods outside its own namespace
   - C) `ClusterRole` cannot grant `create`/`delete` verbs
   - D) It would prevent the driver from creating executor pods at all

<details>

<summary>Show Answer</summary>

**Answer: B) It violates least privilege — a compromised or misbehaving driver could then affect pods outside its own namespace**

**Explanation:**
The driver only ever needs to manage pods, services, and configmaps within its own namespace. Scoping its permissions to a namespaced `Role` bound only in that namespace means a compromised or misbehaving driver's blast radius stays contained to that one namespace, instead of being able to reach pods cluster-wide.
</details>

10. What is the purpose of pinning `spark.driver.port` and `spark.blockManager.port` to fixed values before writing a `NetworkPolicy`?
    - A) To improve shuffle compression ratios
    - B) So the `NetworkPolicy` can allow traffic to specific, known ports instead of an unpredictable range
    - C) To enable Dynamic Resource Allocation
    - D) To satisfy IRSA's trust policy requirements

<details>

<summary>Show Answer</summary>

**Answer: B) So the `NetworkPolicy` can allow traffic to specific, known ports instead of an unpredictable range**

**Explanation:**
Without pinning these ports, Spark may bind to arbitrary ports, making it impossible to write a `NetworkPolicy` that allows exactly the ports driver-executor and executor-executor communication needs. Fixing `spark.driver.port` and `spark.blockManager.port` (and the executor-side equivalent) to known values lets the policy restrict traffic to just those ports between driver and executor pods.
</details>

## Short Answer Questions

11. What token does `WebIdentityTokenCredentialsProvider` rely on, and where does that token come from?

<details>

<summary>Show Answer</summary>

**Answer: The web identity token projected into the pod by the EKS Pod Identity webhook, based on the pod's service account annotation (`eks.amazonaws.com/role-arn`)**

**Explanation:**
As long as the service account carries the correct role-arn annotation, EKS automatically projects this token into the pod. `WebIdentityTokenCredentialsProvider` reads it and calls STS `AssumeRoleWithWebIdentity` to obtain temporary AWS credentials, refreshing them as they expire — no static credentials required anywhere.
</details>

12. Name the two Spark metrics/observability approaches discussed in this document and one reason to pick each.

<details>

<summary>Show Answer</summary>

**Answer: (1) Native `PrometheusServlet` — simpler, no extra agent/JAR, good default for new pipelines. (2) JmxSink + JMX Prometheus Exporter Java agent — worth keeping if already wired up by the Spark Operator's default chart, or to leverage its broader, more mature Grafana dashboard ecosystem.**

**Explanation:**
Both expose the same underlying Spark metrics; the choice is about operational overhead versus existing tooling/dashboard investment, not about what gets measured.
</details>

13. Why is the Spark History Server necessary given how driver pods behave on Kubernetes?

<details>

<summary>Show Answer</summary>

**Answer: Because the driver pod hosts the only live Spark UI, and Kubernetes reclaims that pod once the job finishes — taking the UI with it. The History Server reconstructs a UI from persisted S3 event logs instead of a live driver connection.**

**Explanation:**
This is the direct consequence of the driver-does-its-own-scheduling architecture covered in Part 1: no separate long-lived process keeps a job's UI around after the driver pod is gone, so a mechanism that reads durable event logs is the only way to debug a job after the fact.
</details>

14. What does `spark.dynamicAllocation.shuffleTracking.enabled` protect against, and why does this matter more on Kubernetes than on YARN?

<details>

<summary>Show Answer</summary>

**Answer: It prevents Dynamic Resource Allocation from removing an executor that's still holding shuffle blocks other tasks need. This matters more on Kubernetes because, unlike YARN's External Shuffle Service, Kubernetes has no daemon that can keep serving shuffle blocks after the executor that produced them is gone.**

**Explanation:**
This was introduced in Part 1 as a prerequisite for safely using DRA on Kubernetes, and remains part of the resource-management picture that a production checklist needs to verify before go-live.
</details>

15. What two Kubernetes-native mechanisms (beyond IRSA) does this document cover for hardening a Spark-on-EKS deployment, and what does each restrict?

<details>

<summary>Show Answer</summary>

**Answer: (1) `NetworkPolicy` — restricts which pods can reach the driver/executor pods and on which ports. (2) Namespace-scoped RBAC `Role`/`RoleBinding` — restricts what the driver's service account can do via the Kubernetes API, limited to its own namespace and only the verbs it needs.**

**Explanation:**
IRSA controls access to AWS resources outside the cluster; `NetworkPolicy` and RBAC control what pods can do to each other and to the Kubernetes API inside the cluster. All three are needed for defense in depth.
</details>

## Hands-on Questions

16. Write the `spark-submit` configuration needed so both the driver and executor pods authenticate to S3 via an IRSA-bound service account named `spark-s3-sa` in namespace `spark-jobs`.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
spark-submit \
  --master k8s://https://<EKS_API_SERVER_ENDPOINT>:443 \
  --deploy-mode cluster \
  --conf spark.kubernetes.namespace=spark-jobs \
  --conf spark.kubernetes.authenticate.driver.serviceAccountName=spark-s3-sa \
  --conf spark.kubernetes.authenticate.executor.serviceAccountName=spark-s3-sa \
  --conf spark.hadoop.fs.s3a.aws.credentials.provider=com.amazonaws.auth.WebIdentityTokenCredentialsProvider \
  local:///opt/spark/jobs/etl-job.jar
```

**Explanation:**
Both `spark.kubernetes.authenticate.driver.serviceAccountName` and the executor equivalent must point at the IRSA-bound service account, and `spark.hadoop.fs.s3a.aws.credentials.provider` must be set so the S3A connector actually uses the web identity token instead of looking for static credentials.
</details>

17. Write a `NetworkPolicy` that only allows Spark executor pods (`spark-role: executor`) to reach a driver pod (`spark-role: driver`) on the driver port (7078) and block manager port (7079), in namespace `spark-jobs`.

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: spark-driver-executor-only
  namespace: spark-jobs
spec:
  podSelector:
    matchLabels:
      spark-role: driver
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              spark-role: executor
      ports:
        - protocol: TCP
          port: 7078
        - protocol: TCP
          port: 7079
```

**Explanation:**
The `podSelector` targets driver pods, and the single `ingress` rule only allows traffic from pods labeled `spark-role: executor`, restricted to the driver port and block manager port. This requires `spark.driver.port`/`spark.driver.blockManager.port` to be pinned to fixed values so the policy's port numbers stay valid.
</details>

18. Write a namespace-scoped `Role` and `RoleBinding` granting the Spark driver's service account (`spark-s3-sa` in `spark-jobs`) exactly the permissions it needs to manage its own executor pods, without using a `ClusterRole`.

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: spark-driver-role
  namespace: spark-jobs
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["create", "get", "list", "watch", "delete"]
  - apiGroups: [""]
    resources: ["pods/log"]
    verbs: ["get"]
  - apiGroups: [""]
    resources: ["services", "configmaps"]
    verbs: ["create", "get", "list", "watch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: spark-driver-rolebinding
  namespace: spark-jobs
subjects:
  - kind: ServiceAccount
    name: spark-s3-sa
    namespace: spark-jobs
roleRef:
  kind: Role
  name: spark-driver-role
  apiGroup: rbac.authorization.k8s.io
```

**Explanation:**
Using a namespaced `Role` (not a `ClusterRole`) bound only within `spark-jobs`, with verbs limited to what the driver actually does — create/list/watch/delete its own executor pods, read their logs, and manage the headless service/configmaps used for executor discovery — keeps a compromised or misbehaving driver's blast radius contained to its own namespace.
</details>

---

[Return to Learning Materials](../../../data-on-eks/spark/05-best-practices.md) | [Back to Spark Deep Dive Home](../../../data-on-eks/spark/README.md)

# Part 5: Best Practices and Security

> **Last Updated**: July 15, 2026

Across this five-part series we covered Spark on Kubernetes fundamentals (Part 1), deploying and managing jobs declaratively with the Spark Operator (Part 2), Amazon EMR on EKS as a managed alternative (Part 3), and performance/cost tuning including driver/executor resource sizing (Part 4). This final document rounds things out with what's left before a Spark-on-EKS pipeline is genuinely production-ready: secure, credential-free access to S3, observability that survives a driver pod disappearing, a recap of resource sizing philosophy, and security hardening beyond IAM.

## Lab Environment Setup

To follow along with the examples in this document, you will need:

* kubectl v1.30 or later, pointed at a working Amazon EKS cluster
* An IAM OIDC provider enabled on the cluster (required for IRSA)
* An S3 bucket for Spark event logs / checkpoint data, plus permission to create IAM roles and policies
* Helm 3, if deploying the Spark History Server via a chart rather than a plain `Deployment` manifest
* A Prometheus/Grafana stack (e.g. the `kube-prometheus-stack` chart), only needed if you want to actually scrape and visualize the metrics endpoints covered below

## 1. Secure S3 Access with IRSA

Driver and executor pods routinely need to talk to S3 — reading input data, writing output, and (as covered in Part 4 and again below) writing checkpoint and event log data. The production-grade way to grant that access on EKS is **IAM Roles for Service Accounts (IRSA)**: bind the Kubernetes service account the driver/executor pods run as to an IAM role, and configure Spark's Hadoop S3A connector to pick up credentials from that binding automatically. No static AWS access keys ever need to exist in a Secret, a ConfigMap, or a container image.

The S3A connector doesn't do this by default — you have to point it explicitly at the credentials provider that knows how to exchange the pod's projected service account token for temporary AWS credentials:

```properties
spark.hadoop.fs.s3a.aws.credentials.provider=com.amazonaws.auth.WebIdentityTokenCredentialsProvider
```

`WebIdentityTokenCredentialsProvider` reads the web identity token that the EKS Pod Identity webhook automatically projects into the pod (as long as the pod's service account is annotated correctly) and calls STS `AssumeRoleWithWebIdentity` behind the scenes, refreshing the resulting temporary credentials as they expire.

Putting it together, a driver/executor service account looks like this:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: spark-s3-sa
  namespace: spark-jobs
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/spark-s3-access
```

```bash
spark-submit \
  --master k8s://https://<EKS_API_SERVER_ENDPOINT>:443 \
  --deploy-mode cluster \
  --conf spark.kubernetes.namespace=spark-jobs \
  --conf spark.kubernetes.authenticate.driver.serviceAccountName=spark-s3-sa \
  --conf spark.kubernetes.authenticate.executor.serviceAccountName=spark-s3-sa \
  --conf spark.hadoop.fs.s3a.aws.credentials.provider=com.amazonaws.auth.WebIdentityTokenCredentialsProvider \
  --conf spark.hadoop.fs.s3a.endpoint.region=us-east-1 \
  local:///opt/spark/jobs/etl-job.jar
```

The IAM role (`spark-s3-access` above) itself needs a trust policy scoped to the cluster's OIDC provider and the specific namespace/service-account subject, plus a permissions policy scoped to only the S3 bucket(s) and prefixes the job actually needs — not a blanket `s3:*` on `*`.

## 2. Observability: Two Ways to Get Prometheus Metrics

Part 2 covered the Spark Operator's Helm chart, which by default wires up metrics through the older pattern: a `JmxSink` inside Spark exposing metrics over JMX, scraped by a standalone **JMX Prometheus Exporter** Java agent (`-javaagent:...jmx_prometheus_javaagent.jar`) attached to the JVM, which translates JMX MBeans into a Prometheus-scrapable HTTP endpoint. It works well and has a mature ecosystem of ready-made Grafana dashboards, but it's an extra moving part: an extra JAR to ship in the image, an extra agent config file, and an extra process attached to each JVM.

Since Spark 3.0, there's a lower-friction alternative built directly into Spark: the native **`PrometheusServlet`**. It exposes metrics in Prometheus text format directly on Spark's existing UI port — no external JAR, no separate agent, nothing extra to attach to the JVM.

```properties
# metrics.properties
*.sink.prometheusServlet.class=org.apache.spark.metrics.sink.PrometheusServlet
*.sink.prometheusServlet.path=/metrics/prometheus
master.sink.prometheusServlet.path=/metrics/master/prometheus
applications.sink.prometheusServlet.path=/metrics/applications/prometheus
```

```bash
spark-submit \
  --conf spark.metrics.conf=/opt/spark/conf/metrics.properties \
  ...
```

(`metrics.properties` is typically mounted into the driver/executor pods from a `ConfigMap`.)

**Which one to reach for:**

- **`PrometheusServlet`** — simpler operationally (no extra agent/JAR, one less thing to version and patch), a good default for new pipelines that don't already depend on the JMX exporter's dashboard ecosystem.
- **JmxSink + JMX Prometheus Exporter** — worth keeping if you're already using the Spark Operator's default chart wiring from Part 2, or if you want the broader, more mature set of community Grafana dashboards built specifically around the JMX exporter's metric naming.

Both approaches expose Spark's own metrics (executor task counts, shuffle read/write, JVM GC, etc.) — they differ in transport and packaging, not in what's measured.

## 3. Debugging Finished Jobs with the Spark History Server

Part 1 covered how the driver pod itself does the scheduling — and that also means the driver pod is where the live Spark UI lives. Once a job finishes (or crashes), Kubernetes eventually reclaims that pod, and the UI goes with it. If someone asks "why did last night's job run slowly?" after the driver pod is long gone, there is no live UI left to check.

The **Spark History Server** solves this by reading persisted event logs instead of talking to a live driver. Enable event logging on every job, writing to S3 (using the same IRSA setup from Section 1):

```properties
spark.eventLog.enabled=true
spark.eventLog.dir=s3a://my-spark-bucket/spark-events/
```

Then run a History Server instance — typically a small, always-on `Deployment` on EKS — pointed at the same location:

```properties
# spark-history-server.conf, mounted into the History Server pod
spark.history.fs.logDirectory=s3a://my-spark-bucket/spark-events/
spark.hadoop.fs.s3a.aws.credentials.provider=com.amazonaws.auth.WebIdentityTokenCredentialsProvider
```

The History Server's own pod needs the same kind of IRSA-bound service account as driver/executor pods, since it's reading the same S3 bucket. Once it's running, it periodically rescans the event log directory and serves a reconstructed UI — job stages, SQL plans, executor timelines — for every completed job, regardless of whether that job's driver pod still exists. This turns "debug a job that already finished" from "impossible, the UI is gone" into "open the History Server and pick the application ID."

## 4. Resource Sizing: A Quick Recap

Part 4 covered this in depth, but it's worth restating as a philosophy going into production: **driver and executor pods are sized for different goals.** The driver isn't doing the heavy data processing — it's coordinating the job, tracking task state, and driving scheduling decisions — so driver sizing prioritizes *stability*: enough memory and CPU headroom that the driver itself never becomes the bottleneck or, worse, gets OOMKilled and takes the whole job down with it. Executors are where the actual work happens, so executor sizing (`spark.executor.memory`, `spark.executor.cores`, mapped onto Kubernetes `resources.requests`/`resources.limits` as covered in Part 1) is tuned for *throughput* against your job's actual shuffle volume and per-task memory footprint.

There still isn't a universal numeric default that fits every job here — the right values come out of benchmarking your actual workload under realistic data volumes, not out of copying another team's `spark-submit` flags.

## 5. Security Beyond IRSA

IRSA locks down what a pod can do *outside* the cluster (in AWS). Two more pieces lock down what pods can do *inside* the cluster.

### Network Policies

By default, any pod in the namespace (or cluster, depending on your CNI's defaults) can reach a Spark driver or executor pod on any port. Driver-executor and executor-executor communication only ever needs a small, fixed set of ports, so pin those ports explicitly and restrict traffic to them:

```properties
spark.driver.port=7078
spark.driver.blockManager.port=7079
spark.blockManager.port=7079
```

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

A matching policy on executor pods, scoped to `spark-role: driver` and `spark-role: executor` peers on the block manager port, closes off the rest: nothing outside the job's own driver/executor pods can reach these ports at all.

### Least-Privilege RBAC for the Driver's Service Account

The driver pod creates and manages its own executor pods by calling the Kubernetes API directly (Part 1) — which means its service account needs *some* pod-management permissions. The mistake is granting that role cluster-wide, or granting more verbs than the driver actually uses. Scope it to exactly what's needed, in exactly the driver's own namespace:

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

A `Role` (namespace-scoped) rather than a `ClusterRole`, with verbs limited to what the driver actually does — create/list/watch/delete its own executor pods, read their logs, and manage the headless service and configmaps it uses for executor discovery — means a compromised or misbehaving driver pod can only affect its own namespace, not the rest of the cluster.

## 6. Checklist

Rolling up the key production-readiness items from Parts 1 through 5 of this deep dive:

- [ ] **Cluster-mode submission**: jobs submit with `--deploy-mode cluster`, and the driver's service account can create/watch/delete the executor pods it needs (Part 1)
- [ ] **Dynamic Resource Allocation**: `spark.dynamicAllocation.shuffleTracking.enabled` is set alongside `spark.dynamicAllocation.enabled` wherever DRA is used, given Kubernetes has no External Shuffle Service (Part 1)
- [ ] **Graceful decommissioning**: `spark.decommission.enabled`/`spark.storage.decommission.enabled` are on for Spot-backed executor pools (Part 1)
- [ ] **Declarative job management**: production jobs run through the Spark Operator's CRDs rather than ad hoc `spark-submit` invocations (Part 2)
- [ ] **Resource sizing**: driver sizing is tuned for stability, executor sizing for throughput, and both were validated by benchmarking the actual workload rather than copied from another job (Part 4, Part 5)
- [ ] **S3 access**: driver/executor pods use IRSA-bound service accounts and `WebIdentityTokenCredentialsProvider` — no static AWS credentials anywhere (Part 5)
- [ ] **Metrics**: either `PrometheusServlet` or the JMX exporter pattern is wired up and actually being scraped (Part 5)
- [ ] **Post-hoc debuggability**: the Spark History Server is deployed against the same S3 event log location every job writes to, so finished jobs remain inspectable after their driver pod is gone (Part 5)
- [ ] **Network policies**: driver↔executor and executor↔executor traffic is restricted to the fixed Spark ports actually in use (Part 5)
- [ ] **RBAC**: the driver's service account has a namespace-scoped `Role`, not a `ClusterRole`, limited to the verbs it actually needs (Part 5)

Satisfying this checklist is a reasonable bar for saying a Spark-on-EKS pipeline is ready to run in production.

---

[Return to Main Page](./)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/data-on-eks/spark/05-best-practices-quiz.md).

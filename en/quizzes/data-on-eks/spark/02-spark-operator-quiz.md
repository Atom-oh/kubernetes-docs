# Spark Operator Quiz

This quiz tests your understanding of the two Spark-on-Kubernetes operator options, what an operator gives you over raw `spark-submit`, the mutating admission webhook, core CRDs, and EKS deployment considerations.

## Multiple Choice Questions

1. What is the relationship between apache/spark-kubernetes-operator and the older Kubeflow community operator?
   - A) It is a rebrand of the exact same codebase
   - B) It is a fork that reuses most of kubeflow/spark-operator's code
   - C) It is a new operator built from scratch under Apache Software Foundation governance, not a revival of the Kubeflow project
   - D) It replaced kubeflow/spark-operator, which is no longer maintained

<details>

<summary>Show Answer</summary>

**Answer: C) It is a new operator built from scratch under Apache Software Foundation governance, not a revival of the Kubeflow project**

**Explanation:**
apache/spark-kubernetes-operator was proposed via an SPIP (Spark Improvement Proposal) in November 2023 and built independently under ASF governance. It is a distinct project from kubeflow/spark-operator, which remains separately maintained and actively released (e.g., v2.5.0).
</details>

2. Which statement best describes the current state of kubeflow/spark-operator as of its v2.5.0 release?
   - A) It has been deprecated in favor of the ASF operator
   - B) It is still actively developed, adding features like namespace-label watching and SparkConnect webhook validation
   - C) It only supports Spark versions older than 3.0
   - D) It requires Kubernetes 1.34+ to run

<details>

<summary>Show Answer</summary>

**Answer: B) It is still actively developed, adding features like namespace-label watching and SparkConnect webhook validation**

**Explanation:**
kubeflow/spark-operator v2.5.0 shipped alpha feature gates, namespace-label–based watching, generated Python APIs, and SparkConnect webhook validation, and has distributed via Helm as its primary install method for years. It runs on Kubernetes 1.28+, not 1.34+.
</details>

3. A team already standardizing on Spark 4 with Apache DataFusion Comet acceleration is choosing an operator. Which option is the better fit based on this document?
   - A) kubeflow/spark-operator, because it is older
   - B) apache/spark-kubernetes-operator, because it ships native Spark 4 acceleration integrations
   - C) Neither operator supports Spark 4
   - D) It makes no difference which operator is chosen

<details>

<summary>Show Answer</summary>

**Answer: B) apache/spark-kubernetes-operator, because it ships native Spark 4 acceleration integrations**

**Explanation:**
apache/spark-kubernetes-operator, being built by the Spark project itself, provides first-class integrations for Spark 4's acceleration engines (Apache DataFusion Comet and Apache Gluten). kubeflow/spark-operator has broader adoption but isn't acceleration-specific.
</details>

4. What is the main limitation of running Spark jobs with plain `spark-submit` (no operator) on Kubernetes?
   - A) It cannot create executor Pods at all
   - B) It has no Kubernetes-native concept of retrying a failed driver or reporting status through a CRD
   - C) It only works with Java applications
   - D) It requires a separate Kubernetes cluster per job

<details>

<summary>Show Answer</summary>

**Answer: B) It has no Kubernetes-native concept of retrying a failed driver or reporting status through a CRD**

**Explanation:**
`spark-submit` is fire-and-forget: once the driver Pod is created, nothing resubmits it if it fails, and there's no CRD to check status against. An Operator adds a `restartPolicy` and surfaces state through the `SparkApplication` CR's `.status` field.
</details>

5. What component is responsible for injecting volumes, sidecars, affinity rules, and secrets declared under `spec.driver`/`spec.executor` into the actual running Pods?
   - A) The Kubernetes scheduler
   - B) A mutating admission webhook registered by the operator
   - C) The `spark-submit` CLI
   - D) The EBS CSI driver

<details>

<summary>Show Answer</summary>

**Answer: B) A mutating admission webhook registered by the operator**

**Explanation:**
Both Spark operators register a mutating admission webhook that intercepts driver/executor Pod creation requests and injects the customizations declared in the `SparkApplication` spec — this is what lets you declare pod-level customization directly in the CRD instead of hand-building a `--conf spark.kubernetes.driver.podTemplateFile` pod template.
</details>

6. In kubeflow/spark-operator's Helm installation, what does `--set webhook.enable=true` control?
   - A) Whether the CRDs are installed
   - B) Whether the mutating admission webhook that applies pod customizations is active
   - C) Whether S3 access is enabled
   - D) Whether the Spark History Server is deployed

<details>

<summary>Show Answer</summary>

**Answer: B) Whether the mutating admission webhook that applies pod customizations is active**

**Explanation:**
Without `webhook.enable=true`, pod-template customizations declared under `spec.driver`/`spec.executor` (volumes, sidecars, affinity, secrets) are silently ignored because there's no webhook to apply them.
</details>

7. Which CRD lets you run a recurring Spark job on a cron schedule without an external `CronJob` calling `spark-submit`?
   - A) `SparkApplication`
   - B) `SparkCronJob`
   - C) `ScheduledSparkApplication`
   - D) `SparkPipeline`

<details>

<summary>Show Answer</summary>

**Answer: C) `ScheduledSparkApplication`**

**Explanation:**
`ScheduledSparkApplication` wraps a `SparkApplication` template with a cron `schedule` field and a `concurrencyPolicy` (e.g., `Forbid` to skip a run if the previous one hasn't finished), removing the need for an external scheduler.
</details>

8. On EKS, how do driver and executor Pods typically obtain AWS credentials to read/write S3 data in a `SparkApplication`?
   - A) Static access keys embedded directly in the SparkApplication spec
   - B) A ServiceAccount annotated for IRSA (or an EKS Pod Identity association), referenced via `spec.driver.serviceAccount`/`spec.executor.serviceAccount`
   - C) AWS credentials are not needed for S3 access
   - D) A hardcoded IAM user's `~/.aws/credentials` file baked into the Spark image

<details>

<summary>Show Answer</summary>

**Answer: B) A ServiceAccount annotated for IRSA (or an EKS Pod Identity association), referenced via `spec.driver.serviceAccount`/`spec.executor.serviceAccount`**

**Explanation:**
A ServiceAccount annotated with `eks.amazonaws.com/role-arn` (IRSA) is referenced from the driver/executor spec. The EKS Pod Identity webhook injects temporary AWS credentials automatically, so no static keys ever need to appear in the job spec.
</details>

9. What does `spark.local.dir` default to if not explicitly configured, and why might that matter on EKS?
   - A) An S3 bucket, which is too slow for shuffle
   - B) An `emptyDir` backed by the node's root EBS volume, which can bottleneck or fill up on shuffle-heavy jobs
   - C) A ConfigMap, which has a strict 1MB size limit
   - D) It is always backed by instance-store NVMe automatically

<details>

<summary>Show Answer</summary>

**Answer: B) An `emptyDir` backed by the node's root EBS volume, which can bottleneck or fill up on shuffle-heavy jobs**

**Explanation:**
Spark's shuffle and spill data writes to `spark.local.dir`, which defaults to an `emptyDir` on the node's root EBS volume unless configured otherwise. Shuffle-heavy jobs benefit from a dedicated `emptyDir`, ideally backed by instance-store NVMe.
</details>

10. Where is the full setup for the JMX Prometheus Exporter metrics integration covered in this documentation series?
    - A) It isn't covered anywhere
    - B) Part 1: Spark on Kubernetes
    - C) Part 5: Best Practices
    - D) It's covered fully within this Spark Operator chapter

<details>

<summary>Show Answer</summary>

**Answer: C) Part 5: Best Practices**

**Explanation:**
This chapter only introduces that kubeflow/spark-operator's Helm chart can wire up the JMX Prometheus Exporter Java agent on driver/executor JVMs out of the box; the full metrics setup and recommended dashboards are covered in Part 5: Best Practices.
</details>

## Short Answer Questions

11. Name the two actively maintained Spark-on-Kubernetes operators discussed in this chapter.

<details>

<summary>Show Answer</summary>

**Answer: apache/spark-kubernetes-operator and kubeflow/spark-operator**

**Explanation:**
apache/spark-kubernetes-operator is a new ASF-governed project (latest release 0.9.0), while kubeflow/spark-operator is the older, more widely adopted community project (latest release v2.5.0). Both are independently maintained as of 2026.
</details>

12. What API group does apache/spark-kubernetes-operator use for its CRDs, in contrast to kubeflow/spark-operator's `sparkoperator.k8s.io`?

<details>

<summary>Show Answer</summary>

**Answer: `spark.apache.org`**

**Explanation:**
The two operators define their CRDs under different API groups and are not designed to coexist watching the same namespace — you pick one operator per cluster (or per namespace, if deliberately running both).
</details>

13. What field on the `SparkApplication` spec controls whether a failed driver is automatically resubmitted, and how many times?

<details>

<summary>Show Answer</summary>

**Answer: `restartPolicy` (with `type: OnFailure` and `onFailureRetries`)**

**Explanation:**
`restartPolicy.type` can be `Never`, `OnFailure`, or `Always`. `onFailureRetries` sets the retry count and `onFailureRetryInterval` sets the back-off interval between attempts — capabilities that plain `spark-submit` has no equivalent for.
</details>

14. What Kubernetes-native feature does the operator use to track and expose a Spark job's current state (e.g., `RUNNING`, `COMPLETED`, `FAILED`)?

<details>

<summary>Show Answer</summary>

**Answer: The `SparkApplication` CR's `.status` field**

**Explanation:**
The Operator writes the job's current state to the CR's `.status` field, which `kubectl get sparkapplication` or `kubectl describe sparkapplication` surfaces directly — information that plain `spark-submit` provides no equivalent for.
</details>

15. What `concurrencyPolicy` value on a `ScheduledSparkApplication` prevents a new scheduled run from starting while the previous run is still in progress?

<details>

<summary>Show Answer</summary>

**Answer: `Forbid`**

**Explanation:**
`concurrencyPolicy: Forbid` skips a new run if the previous scheduled run hasn't finished — useful for jobs where overlapping runs would corrupt shared output.
</details>

## Hands-on Questions

16. Write the full command sequence to install kubeflow/spark-operator via Helm into the `spark-operator` namespace with the mutating admission webhook enabled.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
# Add the Spark Operator Helm repository
helm repo add spark-operator https://kubeflow.github.io/spark-operator
helm repo update

# Install into the spark-operator namespace
helm install spark-operator spark-operator/spark-operator \
  --namespace spark-operator \
  --create-namespace \
  --version 2.5.0 \
  --set webhook.enable=true

# Verify the installation
kubectl get pods -n spark-operator
kubectl get crd | grep sparkoperator
```

**Explanation:**
`--set webhook.enable=true` is required for pod-template customizations under `spec.driver`/`spec.executor` to actually be applied; without it, they are silently ignored. `--create-namespace` creates `spark-operator` if it doesn't already exist.
</details>

17. Write a minimal `SparkApplication` that runs a Scala word-count job in cluster mode with 1 driver core, 2 executor instances of 2 cores each, and automatic retry up to 3 times on failure.

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
apiVersion: sparkoperator.k8s.io/v1beta2
kind: SparkApplication
metadata:
  name: word-count
  namespace: spark-operator
spec:
  type: Scala
  mode: cluster
  image: "apache/spark:3.5.3"
  mainClass: org.apache.spark.examples.JavaWordCount
  mainApplicationFile: "local:///opt/spark/examples/jars/spark-examples.jar"
  sparkVersion: "3.5.3"
  restartPolicy:
    type: OnFailure
    onFailureRetries: 3
    onFailureRetryInterval: 10
  driver:
    cores: 1
    memory: "1g"
  executor:
    cores: 2
    instances: 2
    memory: "2g"
```

**Explanation:**
`restartPolicy.type: OnFailure` with `onFailureRetries: 3` gives the driver up to 3 automatic resubmission attempts. `executor.instances: 2` combined with `executor.cores: 2` provisions two executor Pods, each requesting 2 CPU cores.
</details>

18. Write a `ScheduledSparkApplication` that runs a daily ETL job at 2 AM and skips a new run if the previous one is still in progress.

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
apiVersion: sparkoperator.k8s.io/v1beta2
kind: ScheduledSparkApplication
metadata:
  name: daily-etl
  namespace: spark-operator
spec:
  schedule: "0 2 * * *"
  concurrencyPolicy: Forbid
  template:
    type: Scala
    mode: cluster
    image: "apache/spark:3.5.3"
    mainClass: com.example.DailyEtlJob
    mainApplicationFile: "s3a://my-bucket/jars/daily-etl.jar"
    sparkVersion: "3.5.3"
    driver:
      cores: 1
      memory: "2g"
    executor:
      cores: 2
      instances: 4
      memory: "4g"
```

**Explanation:**
`schedule: "0 2 * * *"` is standard cron syntax for 2 AM daily. `concurrencyPolicy: Forbid` ensures a new run is skipped entirely if the previous scheduled run hasn't completed yet, avoiding overlapping writes to the same output location.
</details>

19. Create a ServiceAccount annotated for IRSA that grants S3 access, and reference it from a `SparkApplication`'s driver and executor specs.

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: spark-driver
  namespace: spark-operator
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/spark-s3-access
```

```yaml
spec:
  driver:
    serviceAccount: spark-driver
  executor:
    serviceAccount: spark-driver
```

**Explanation:**
The `eks.amazonaws.com/role-arn` annotation is what tells the EKS Pod Identity webhook to inject temporary AWS credentials for the annotated IAM role into any Pod using this ServiceAccount. Referencing `spark-driver` from both `driver.serviceAccount` and `executor.serviceAccount` gives both the S3 access needed to read input and write output.
</details>

20. Add a dedicated `emptyDir` volume for `spark.local.dir` scratch space to both the driver and executor of a `SparkApplication`.

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
spec:
  driver:
    volumes:
      - name: spark-local-dir
        emptyDir: {}
  executor:
    volumes:
      - name: spark-local-dir
        emptyDir: {}
```

**Explanation:**
Declaring `volumes` under `spec.driver`/`spec.executor` relies on the mutating admission webhook to actually attach the volume to the running Pods. A dedicated `emptyDir` here (ideally on instance-store NVMe nodes) avoids shuffle/spill I/O competing with the node's root EBS volume.
</details>

---

[Return to Learning Materials](../../../data-on-eks/spark/02-spark-operator.md) | [Next Quiz: EMR on EKS](./03-emr-on-eks-quiz.md)

# Part 2: Spark Operator

> **Supported Versions**: Kubernetes 1.34+ (apache/spark-kubernetes-operator 0.9.0) or Kubernetes 1.28+ (kubeflow/spark-operator 2.5.0)\
> **Last Updated**: July 15, 2026

## Lab Environment Setup

To follow along with the examples in this document, you will need the following tools and environment:

### Required Tools

* kubectl v1.28 or later (v1.34+ if you choose the apache/spark-kubernetes-operator)
* Helm v3.12 or later
* A working Kubernetes cluster (Amazon EKS recommended)
* An IRSA role or EKS Pod Identity association granting S3 access (for reading input data and writing job output)

## Two Operators, One Decision

Running `spark-submit --master k8s://...` directly works for a one-off job, but it gives you no Kubernetes-native way to track status, retry a failed driver, or declaratively version a job spec in Git. A Spark Operator closes that gap by wrapping a Spark application in a CRD: you `kubectl apply` the desired job, and the Operator takes care of submission, retries, and status reporting.

As of mid-2026, there are two actively maintained options, and choosing between them is a real decision rather than a formality:

### apache/spark-kubernetes-operator

Proposed via an SPIP (Spark Improvement Proposal) in November 2023 and built from scratch under Apache Software Foundation governance, this is a new operator — not a revival of the older Kubeflow-community project. Its latest release, 0.9.0 (May 2026), supports Kubernetes v1.34–v1.36 and Spark 3.5, 4.0, and 4.1 (tested against the 4.2.0 preview). Because it's built by the Spark project itself, it ships native integrations for Spark 4's acceleration engines — Apache DataFusion Comet and Apache Gluten — without extra glue code.

### kubeflow/spark-operator

The older, more mature, and far more widely adopted community operator. It's still very much alive: v2.5.0 shipped alpha feature gates, namespace-label–based watching, generated Python APIs, and SparkConnect webhook validation, and it has distributed via Helm as its primary install method for years.

### Which One Should You Use?

| Consideration | apache/spark-kubernetes-operator | kubeflow/spark-operator |
|---|---|---|
| Governance | Apache Software Foundation, Spark-native | CNCF-adjacent community project |
| Maturity / adoption | Newer, smaller install base | Mature, widely deployed in production |
| Spark version alignment | First-class support for Spark 4 acceleration (Comet, Gluten) | Broad support across Spark 3.x/4.x, not acceleration-specific |
| Kubernetes version floor | 1.34+ | 1.28+ |
| Best fit | Teams already standardizing on Spark 4 and DataFusion Comet/Gluten | Teams that want a proven operator or are already using the Kubeflow ecosystem |

Neither is universally "better" — this section covers both, but uses kubeflow/spark-operator for the hands-on examples since it's the more commonly deployed choice today.

## What the Operator Gives You Over `spark-submit`

`spark-submit` is fire-and-forget: once the driver Pod is created, Kubernetes has no built-in concept of "this is a Spark job that should be retried if it fails." If the driver crashes, nothing resubmits it, and there's no CRD to `kubectl get` for status.

An operator changes this in two ways:

* **Lifecycle management** — Submitting a `SparkApplication` hands control to the Operator, which watches the driver Pod and applies the `restartPolicy` declared in the spec (`Never`, `OnFailure`, or `Always`, with configurable retry counts and back-off intervals). Job state — `SUBMITTED`, `RUNNING`, `COMPLETED`, `FAILED` — is surfaced on the CR's `.status` field, so `kubectl get sparkapplication` tells you what `spark-submit` alone never could.
* **Mutating admission webhook** — Both operators register a mutating admission webhook that intercepts driver/executor Pod creation and injects the customizations declared under `spec.driver`/`spec.executor` — extra volumes, sidecars, affinity rules, secret mounts, environment variables. This is why you can declare a volume mount directly in the `SparkApplication` YAML instead of hand-building a `--conf spark.kubernetes.driver.podTemplateFile` pod template and passing it through `spark-submit`.

## Installation

### Option 1: kubeflow/spark-operator via Helm (Recommended)

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

`--set webhook.enable=true` turns on the mutating admission webhook described above; without it, pod-template customizations under `spec.driver`/`spec.executor` are silently ignored.

### Option 2: apache/spark-kubernetes-operator via Helm

If your cluster is on Kubernetes 1.34+ and you want first-class Spark 4/DataFusion Comet support instead, install the ASF operator:

```bash
# Add the ASF Spark Kubernetes Operator Helm repository
helm repo add spark-kubernetes-operator https://apache.github.io/spark-kubernetes-operator
helm repo update

# Install into the spark-operator namespace
# Chart version 1.7.0 packages app version 0.9.0 -- the operator's Helm chart
# and app versions are tracked separately, so pin the chart version here.
helm install spark-kubernetes-operator spark-kubernetes-operator/spark-kubernetes-operator \
  --namespace spark-operator \
  --create-namespace \
  --version 1.7.0

# Verify the installation
kubectl get pods -n spark-operator
kubectl get crd | grep spark.apache.org
```

The two operators are not designed to coexist watching the same namespace — pick one per cluster (or per namespace, if you deliberately want to run both side by side). The ASF operator defines its CRDs under the `spark.apache.org` API group rather than kubeflow's `sparkoperator.k8s.io`; the rest of this document uses kubeflow/spark-operator's CRDs since they're the ones most examples in the wild are written against.

## Core CRDs

### SparkApplication

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
  imagePullPolicy: IfNotPresent
  mainClass: org.apache.spark.examples.JavaWordCount
  mainApplicationFile: "local:///opt/spark/examples/jars/spark-examples.jar"
  arguments:
    - "s3a://my-bucket/input/sample.txt"
  sparkVersion: "3.5.3"
  restartPolicy:
    type: OnFailure
    onFailureRetries: 3
    onFailureRetryInterval: 10
    onSubmissionFailureRetries: 3
    onSubmissionFailureRetryInterval: 20
  driver:
    cores: 1
    memory: "1g"
    serviceAccount: spark-driver
  executor:
    cores: 1
    instances: 2
    memory: "2g"
```

`type` and `mode` mirror `spark-submit`'s `--class`/language and `--deploy-mode` flags. `restartPolicy` is where the Operator earns its keep: `OnFailure` combined with `onFailureRetries` gives the driver automatic resubmission attempts that plain `spark-submit` has no concept of.

### ScheduledSparkApplication

For recurring jobs (a daily ETL run, for example), `ScheduledSparkApplication` wraps a `SparkApplication` template with a cron schedule instead of requiring an external scheduler like a `CronJob` calling `spark-submit`:

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
    restartPolicy:
      type: OnFailure
      onFailureRetries: 2
      onFailureRetryInterval: 30
    driver:
      cores: 1
      memory: "2g"
      serviceAccount: spark-driver
    executor:
      cores: 2
      instances: 4
      memory: "4g"
```

`concurrencyPolicy: Forbid` skips a new run if the previous scheduled run hasn't finished yet — useful for jobs where overlapping runs would corrupt output.

## How It Works

![A cyclic flowchart of the Spark Operator control loop: a kubectl apply of a SparkApplication CR is watched by the Operator Controller, which routes through a mutating admission webhook to create a driver pod that requests executor pods to run the Spark job, after which the operator writes progress back to the CR's status field and the controller reconciles again.](../../.gitbook/assets/en-data-on-eks-spark-02-spark-operator-0.png)

The Operator's control loop only ever touches the driver Pod directly; the driver itself talks to the Kubernetes API to request its own executors, exactly as it would under plain `spark-submit`. The Operator's value-add is the layer around that: submission, the webhook-driven pod customization, restart handling, and status reporting.

## EKS Deployment Considerations

### 1. S3 Access via IRSA

Spark jobs on EKS typically read/write data from S3 rather than local/EBS storage, so both the driver and executor Pods need AWS credentials. Rather than embedding static keys, annotate a dedicated ServiceAccount with an IAM role and reference it from the `SparkApplication` spec:

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

The EKS Pod Identity webhook (or an EKS Pod Identity association, if you're using that mechanism instead of IRSA) injects the temporary AWS credentials into both driver and executor Pods automatically — no `spark.hadoop.fs.s3a.access.key` style static credentials need to appear anywhere in the job spec.

### 2. Shuffle and Scratch Storage

Spark's shuffle and spill operations write to `spark.local.dir`, which defaults to an `emptyDir` volume backed by the node's root EBS volume unless configured otherwise. Shuffle-heavy jobs can easily exhaust that space or bottleneck on its throughput. Mount a dedicated `emptyDir` (ideally backed by instance-store NVMe on nodes that have it) instead:

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

The mutating admission webhook is what makes this declarative `volumes` block under `spec.driver`/`spec.executor` actually land on the running Pods.

### 3. Monitoring Integration

The kubeflow/spark-operator Helm chart can wire up the JMX Prometheus Exporter Java agent onto driver and executor JVMs out of the box, exposing Spark's internal metrics (task counts, shuffle read/write, GC pauses) in Prometheus format without any manual `-javaagent` flag on your Spark image. This section only flags that the integration point exists — the full metrics setup and recommended dashboards are covered in [Part 5: Best Practices](./05-best-practices.md).

## Deployment Procedure

```bash
# 1. Verify the Operator is running
kubectl get pods -n spark-operator

# 2. Apply the SparkApplication
kubectl apply -f word-count.yaml -n spark-operator

# 3. Check status (wait for the state to reach COMPLETED)
kubectl get sparkapplication -n spark-operator -w
kubectl describe sparkapplication word-count -n spark-operator

# 4. View driver logs
kubectl logs word-count-driver -n spark-operator

# 5. Clean up
kubectl delete sparkapplication word-count -n spark-operator
```

`kubectl describe sparkapplication` surfaces the same driver/executor state transitions and events that you'd otherwise have to piece together from `kubectl get pods` and raw driver logs — this is the CRD-native status tracking that plain `spark-submit` doesn't give you.

## Next Steps

Once you can submit and monitor jobs through the Operator, the next question is usually build-vs-buy: how does this compare to letting AWS manage the Spark runtime for you? That trade-off, along with EMR on EKS's virtual cluster model, is covered in [Part 3: EMR on EKS](./03-emr-on-eks.md).

[Return to Main Page](./README.md)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/data-on-eks/spark/02-spark-operator-quiz.md).

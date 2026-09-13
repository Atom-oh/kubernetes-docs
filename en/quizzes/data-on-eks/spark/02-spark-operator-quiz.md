# Spark Operator Quiz

Baseline: Kubeflow 2.5.2 and Apache operator 1.0.0 / chart 1.8.0.

## 1. How are the two Spark operators related?

- A) A rename of the same chart
- B) A replacement after Kubeflow support ended
- C) Separate projects with different APIs and lifecycle models
- D) Fully compatible after changing only apiVersion

<details>
<summary>Show answer</summary>

**Answer: C**

Kubeflow uses sparkoperator.k8s.io/v1beta2; this chapter uses Apache spark.apache.org/v1. Fields, status and retry behavior also need migration review.

</details>

## 2. Which chart accompanies the reviewed Apache operator 1.0.0?

- A) Necessarily 1.0.0
- B) 2.5.2 like Kubeflow
- C) 4.2.0 like Spark
- D) 1.8.0

<details>
<summary>Show answer</summary>

**Answer: D**

Chart and application versions are separate. Check release/chart metadata and the rendered resources.

</details>

## 3. What is needed for Comet or Gluten?

- A) Compatible plugins, images, classpaths and configuration
- B) Only installing the Apache operator
- C) Identical behavior on every architecture and Spark version
- D) Kubeflow can never run such workloads

<details>
<summary>Show answer</summary>

**Answer: A**

The official examples have additional prerequisites. An operator choice alone does not guarantee acceleration or plugin compatibility.

</details>

## 4. Which statement about plain spark-submit is correct?

- A) It is always fire-and-forget
- B) It can wait and expose logs; operator CR reconciliation is separate
- C) It cannot create executor pods
- D) Its configuration cannot be versioned in Git

<details>
<summary>Show answer</summary>

**Answer: B**

Native submission offers status, logs and UI access. An operator adds CR lifecycle management, scheduled controllers and application retry.

</details>

## 5. What is the Kubeflow 2.5.2 webhook.enable default?

- A) false
- B) It changes automatically with Spark version
- C) true
- D) true only in the default installation namespace

<details>
<summary>Show answer</summary>

**Answer: C**

The example makes the default explicit. If disabled, review the features that depend on that admission path.

</details>

## 6. How do the reviewed charts differ in admission?

- A) Both install the same pod mutator
- B) Webhooks place pods on nodes
- C) Webhooks assign Spark tasks
- D) Apache does not install the equivalent Kubeflow pod-mutating webhook

<details>
<summary>Show answer</summary>

**Answer: D**

The diagram illustrates Kubeflow. Kubernetes scheduling and Spark driver task assignment remain separate responsibilities.

</details>

## 7. What is required for jobs in spark-jobs?

- A) Align watched namespace, job namespace and RBAC
- B) Submit all jobs only to the installation namespace
- C) A ClusterRole makes watch scope irrelevant
- D) Watching default automatically includes every namespace

<details>
<summary>Show answer</summary>

**Answer: A**

Installation and workload namespaces may differ. The default watch scope does not automatically include a new job namespace.

</details>

## 8. Where do Kubeflow custom volumes belong?

- A) Only spec.driver.volumes
- B) spec.volumes with driver/executor.volumeMounts
- C) Only spec.executor.volumes
- D) status.volumes

<details>
<summary>Show answer</summary>

**Answer: B**

The reviewed CRD has no driver.volumes or executor.volumes fields. Declare shared volume definitions at spec.volumes and mount them where required.

</details>

## 9. What is special about spark-local-dir- volumes?

- A) They automatically create physical NVMe disks
- B) They convert all volumes to S3
- C) They are translated into native Spark local-volume configuration
- D) The webhook must be their only implementation path

<details>
<summary>Show answer</summary>

**Answer: C**

The generic volume mutator skips these local-directory volumes; submission configuration handles them. emptyDir does not itself select physical storage.

</details>

## 10. Which serviceAccount fields are valid in Kubeflow 2.5.2?

- A) Only driver.serviceAccount
- B) Only executor.serviceAccount
- C) Both must contain AWS IAM ARNs
- D) Both driver.serviceAccount and executor.serviceAccount

<details>
<summary>Show answer</summary>

**Answer: D**

Both fields name Kubernetes service accounts. API RBAC and AWS data permissions are configured separately.

</details>

## 11. How should a ScheduledSparkApplication run daily at 02:00 UTC?

- A) Use schedule: "0 2 * * *" and timeZone: UTC
- B) Always depend on controller local time
- C) timeZone is unsupported
- D) Set only the executor pod TZ

<details>
<summary>Show answer</summary>

**Answer: A**

Version 2.5.2 supports timeZone, defaulting to Local. An explicit schedule timezone avoids relying on the controller environment.

</details>

## 12. What does concurrencyPolicy: Forbid prevent?

- A) Duplicate writes across every system
- B) Overlap between a scheduled resource's prior run and its next scheduled run
- C) Every application retry
- D) All manual submissions

<details>
<summary>Show answer</summary>

**Answer: B**

Other schedulers, manual runs and retries can still cause duplicate side effects. Design idempotent or transactional outputs.

</details>

## 13. What does suspend: true do?

- A) Necessarily terminate the active child job
- B) Roll back data already written
- C) Stop future scheduled triggers
- D) Delete the operator deployment

<details>
<summary>Show answer</summary>

**Answer: C**

Inspect or terminate current runs separately. Suspension is not data rollback or backup.

</details>

## 14. What does changing only sparkVersion to 4.2.0 guarantee?

- A) Automatic controller runtime upgrade
- B) Compatibility with every Spark plugin
- C) Automatic Kubernetes upgrade
- D) It does not guarantee upgrading the controller's spark-submit

<details>
<summary>Show answer</summary>

**Answer: D**

The Kubeflow lab aligns with its controller submission runtime, 4.0.4. Test other submitter/workload combinations separately.

</details>

## 15. Which pod states does the operator observe?

- A) Both driver and executor
- B) Only driver
- C) Only executor
- D) No pod states

<details>
<summary>Show answer</summary>

**Answer: A**

The controller also updates executor state and performs cleanup. The Spark driver requests executors and assigns Spark tasks.

</details>

## 16. What matters when using OnFailure retries?

- A) Exactly-once writes are automatic
- B) Application reruns can repeat output side effects
- C) Only the same container is ever restarted
- D) Every failed external transaction is rolled back

<details>
<summary>Show answer</summary>

**Answer: B**

Submission/application attempts differ from container restarts. Validate data semantics as well as retry counts and intervals.

</details>

## 17. How do IRSA and EKS Pod Identity differ?

- A) Both need only the same annotation
- B) A Kubernetes Role grants S3 access
- C) IRSA uses OIDC/role annotations; Pod Identity uses associations and its Agent
- D) An S3 URI completes authentication

<details>
<summary>Show answer</summary>

**Answer: C**

Configure AWS permissions, trust or association, and compatible credential providers. Verify effective identity and access in the actual pods.

</details>

## 18. What does the chart's default Prometheus endpoint on 8080 expose?

- A) Automatic JMX collection from every Spark JVM
- B) All Spark History Server logs
- C) S3 data-validation results
- D) Operator metrics

<details>
<summary>Show answer</summary>

**Answer: D**

Workload JMX needs its own application exporter JAR, configuration and scrape setup.

</details>

## 19. How should CRDs be handled during Helm upgrades?

- A) Review CRD migration and the explicit hook.upgradeCrd opt-in
- B) Normal helm upgrade always replaces them
- C) Always delete existing CRDs first
- D) They cannot affect application resources

<details>
<summary>Show answer</summary>

**Answer: A**

Normal upgrades do not automatically replace CRDs from crds/. Deleting a CRD affects its custom resources and is not a routine upgrade step.

</details>

## 20. What do successful Helm rendering and CRD checks establish?

- A) Proof of live webhook connectivity
- B) Resource shape and configuration paths; live workload success is separate
- C) Proof of S3 access and data correctness
- D) Compatibility with every Spark version

<details>
<summary>Show answer</summary>

**Answer: B**

Also inspect real pods, status, outputs, retry behavior and permissions. COMPLETED alone does not establish external data correctness.

</details>

[본문 / Guide](../../../data-on-eks/spark/02-spark-operator.md)

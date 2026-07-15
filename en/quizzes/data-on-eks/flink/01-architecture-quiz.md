# Flink Architecture on Kubernetes Quiz

This quiz tests your understanding of the JobManager/TaskManager cluster model, Flink's three deployment modes, and the difference between native Kubernetes deployment and standalone-on-Kubernetes.

## Multiple Choice Questions

1. Which component is responsible for building the job graph, coordinating checkpoints, and scheduling work onto TaskManagers?
   - A) TaskManager
   - B) JobManager
   - C) Kubernetes ResourceManager (kube-scheduler)
   - D) Task Slot

<details>

<summary>Show Answer</summary>

**Answer: B) JobManager**

**Explanation:**
The JobManager is the control plane of a Flink cluster. It builds the job graph from a submitted application, coordinates distributed checkpoints, schedules operator subtasks onto the task slots of available TaskManagers, and serves the REST API and Web UI. The TaskManager, by contrast, is the worker process that actually executes the scheduled subtasks.

</details>

2. What does a Flink "task slot" represent?
   - A) A dedicated network port used for shuffle traffic between TaskManagers
   - B) A fixed slice of a TaskManager's resources reserved for exactly one operator subtask at a time
   - C) A checkpoint storage location on durable disk
   - D) A Kubernetes node reserved exclusively for the JobManager

<details>

<summary>Show Answer</summary>

**Answer: B) A fixed slice of a TaskManager's resources reserved for exactly one operator subtask at a time**

**Explanation:**
Each TaskManager offers one or more task slots, and each slot is a fixed portion of that TaskManager's resources (primarily memory) dedicated to running one parallel instance of an operator subtask. A TaskManager with 4 slots can run up to 4 subtasks concurrently.

</details>

3. Why is Application Mode recommended as the default for production Flink workloads on Kubernetes?
   - A) It uses less memory than Session Mode in every case
   - B) It gives each job a dedicated cluster with full resource isolation and fencing from other jobs
   - C) It is the only mode that supports checkpointing
   - D) It eliminates the need for a JobManager entirely

<details>

<summary>Show Answer</summary>

**Answer: B) It gives each job a dedicated cluster with full resource isolation and fencing from other jobs**

**Explanation:**
In Application Mode, a dedicated cluster is created per job and the job's `main()` runs inside the JobManager itself. This means each job gets its own JobManager and TaskManager pods, so a misbehaving or resource-hungry job cannot starve or destabilize any other job's cluster — an important property on a shared EKS cluster running many Flink workloads.

</details>

4. What is the key operational difference between Session Mode and Application Mode?
   - A) Session Mode cannot run on Kubernetes at all
   - B) Session Mode runs multiple jobs on a single shared, long-lived cluster, trading isolation for lower per-job startup latency
   - C) Session Mode requires a separate ZooKeeper ensemble that Application Mode does not
   - D) Session Mode only supports batch jobs, never streaming jobs

<details>

<summary>Show Answer</summary>

**Answer: B) Session Mode runs multiple jobs on a single shared, long-lived cluster, trading isolation for lower per-job startup latency**

**Explanation:**
Session Mode submits jobs independently to a cluster that already exists and stays running, so new jobs avoid cluster startup overhead. The tradeoff is that jobs share the same JobManager and compete for the same TaskManager pool, so a single noisy job can affect the whole session cluster — unlike Application Mode's per-job isolation.

</details>

5. Why won't you find Per-Job Mode recommended for Flink on Kubernetes?
   - A) It was merged into Session Mode in Flink 2.0
   - B) It is not supported by native Kubernetes deployment, making it effectively unavailable on EKS
   - C) It requires a minimum of 10 TaskManagers per job
   - D) It only works with the legacy ZooKeeper-based JobManager

<details>

<summary>Show Answer</summary>

**Answer: B) It is not supported by native Kubernetes deployment, making it effectively unavailable on EKS**

**Explanation:**
Per-Job Mode is a legacy mode where the client executed `main()` locally and submitted a pre-built job graph to a dedicated cluster. Native Kubernetes deployment never implemented this mode, so it simply isn't an available option on Kubernetes/EKS. Application Mode achieves the same per-job isolation goal without the legacy client-side submission path.

</details>

6. In native Kubernetes deployment, what component is responsible for dynamically requesting and releasing TaskManager pods?
   - A) The Kubernetes Cluster Autoscaler alone, with no involvement from Flink
   - B) A DaemonSet running on every node
   - C) The Kubernetes ResourceManager integration running inside the JobManager
   - D) A cron job that polls job parallelism every 5 minutes

<details>

<summary>Show Answer</summary>

**Answer: C) The Kubernetes ResourceManager integration running inside the JobManager**

**Explanation:**
In native Kubernetes deployment, the JobManager's own Kubernetes ResourceManager talks directly to the Kubernetes API server to request new TaskManager pods when more task slots are needed, and release them when a job's parallelism shrinks or the job finishes. This is what makes native mode elastic, unlike standalone-on-Kubernetes.

</details>

7. What is the fundamental difference between native Kubernetes deployment and standalone-on-Kubernetes?
   - A) Standalone-on-Kubernetes doesn't support checkpointing
   - B) Native deployment dynamically requests/releases TaskManager pods via Flink's own ResourceManager, while standalone-on-Kubernetes runs a fixed number of pods defined via plain Deployment/YAML manifests
   - C) Native deployment only works with Session Mode
   - D) Standalone-on-Kubernetes is only for batch workloads

<details>

<summary>Show Answer</summary>

**Answer: B) Native deployment dynamically requests/releases TaskManager pods via Flink's own ResourceManager, while standalone-on-Kubernetes runs a fixed number of pods defined via plain Deployment/YAML manifests**

**Explanation:**
Native Kubernetes deployment gives Flink direct visibility into and control over Kubernetes, letting the JobManager elastically scale TaskManager pod count. Standalone-on-Kubernetes predates this integration — it just runs JobManager and TaskManager as plain containers with a fixed pod count and no elastic resource requests, requiring manual YAML edits to change TaskManager count.

</details>

8. What does the Flink Kubernetes Operator (covered in Part 2) build on top of?
   - A) Standalone-on-Kubernetes, since it requires a fixed pod count
   - B) Per-Job Mode's client-side submission model
   - C) Native Kubernetes deployment, adding a CRD layer (`FlinkDeployment`, `FlinkSessionJob`) for declarative lifecycle management
   - D) A completely independent scheduler that bypasses the JobManager

<details>

<summary>Show Answer</summary>

**Answer: C) Native Kubernetes deployment, adding a CRD layer (`FlinkDeployment`, `FlinkSessionJob`) for declarative lifecycle management**

**Explanation:**
The Flink Kubernetes Operator is built on top of native Kubernetes deployment's dynamic resource allocation. It adds Kubernetes-native custom resources (`FlinkDeployment` for Application/Session clusters, `FlinkSessionJob` for jobs submitted to a session cluster) so that cluster lifecycle, upgrades, and savepoint-based redeploys can be managed declaratively instead of through manual `flink run` commands.

</details>

---

[Return to Learning Materials](../../../data-on-eks/flink/01-architecture.md)

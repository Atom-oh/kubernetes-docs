# Spark on Kubernetes Fundamentals Quiz

Review deploy modes, responsibility boundaries, resources, dynamic allocation and termination conditions.

## 1. Which Kubernetes deployment modes and prerequisite apply to Spark 4.2?

<details>
<summary>Show answer</summary>

Both cluster and client modes are supported; Spark 4.2 documents Kubernetes 1.34+. Client mode dates from 2.4 and is not notebook-only. kubectl must be compatible with the actual API server.

</details>

## 2. Who requests executor pods, places/starts pods and assigns Spark tasks?

<details>
<summary>Show answer</summary>

The driver requests executor pods through the API. Kubernetes scheduler chooses nodes and kubelets start containers. The driver's Spark schedulers assign tasks to registered executors. Neither the API server nor driver replaces Kubernetes scheduling.

</details>

## 3. Does removing the YARN layer eliminate infrastructure operations or driver permissions?

<details>
<summary>Show answer</summary>

No. Nodes, Kubernetes, images, networking, storage and observability remain. The submitter's API authentication and driver's namespace RBAC are required. The example uses a separate executor service account; AWS data permissions and Kubernetes RBAC are distinct.

</details>

## 4. Must both dynamic-allocation/shuffle-tracking flags always be explicitly set?

<details>
<summary>Show answer</summary>

No. Enable dynamic allocation, but shuffle tracking already defaults true in 4.2 and dates from 3.0. Stock Kubernetes ESS is unsupported; decommission-based preservation or suitable reliable ShuffleDataIO are alternatives with conditions. Overlapping mechanisms can delay removal.

</details>

## 5. What termination path is added when decommission is enabled?

<details>
<summary>Show answer</summary>

Spark 4.2 injects a preStop hook running /opt/decom.sh. The official image includes it; it signals the executor JVM with SIGPWR and waits. Block migration also needs storage decommission settings plus actual destinations, time and capacity.

</details>

## 6. Does increasing terminationGracePeriodSeconds to 60 guarantee migration of every block?

<details>
<summary>Show answer</summary>

No. Spark 4.2 overrides the template value, so also set spark.kubernetes.executor.terminationGracePeriodSeconds=60s. Both the default 30 seconds and configured 60 include preStop and are only budgets; forced termination, Spot deadlines or insufficient destination capacity can prevent completion.

</details>

## 7. How does allocation.batch.size differ from initial/minimum executor counts?

<details>
<summary>Show answer</summary>

batch.size controls batches of pod requests. Min/initial/max define executor bounds/start count, with existing executor.instances also considered. The example min2/initial3/instances3 starts at three; node provisioning is separate.

</details>

## 8. How should Spark cores, CPU limits, memory and pod templates be interpreted?

<details>
<summary>Show answer</summary>

Cores relate to default CPU requests and executor task capacity; CPU limits require limit.cores. The JVM example's 1 GiB heap plus 384 MiB minimum overhead yields 1408 MiB request/limit. Templates are read by the submitter and composed by Spark, not incomplete pods to kubectl apply.

</details>

## 9. What must still be verified with shuffle tracking and decommissioning?

<details>
<summary>Show answer</summary>

Check tracking/idle timeouts, forced termination, node capacity and recomputation. Client mode also needs reachable driver endpoints and a real driver-pod owner when applicable. Preserving intermediate blocks does not replace checkpoints, driver recovery or end-to-end exactly-once.

</details>

---

[Return to learning material](../../../data-on-eks/spark/01-spark-fundamentals.md)

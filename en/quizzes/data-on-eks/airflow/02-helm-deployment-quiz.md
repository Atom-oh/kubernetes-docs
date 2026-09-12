# Helm Deployment and Executor Choice Quiz

Chart 1.22.0 / Airflow 3.3.1 / KEDA 2.20.

## 1. Which chart and repository alias does this guide use?

<details>
<summary>Show answer</summary>

The Apache Airflow project's official chart. With the repository registered as apache-airflow, commands use apache-airflow/airflow. Do not mix independent community-chart values.

</details>

## 2. What are chart 1.22.0's actual Airflow/executor defaults?

<details>
<summary>Show answer</summary>

Airflow 3.2.2 and CeleryExecutor. The guide explicitly overrides them for its 3.3.1/KubernetesExecutor profile.

</details>

## 3. Does Chart.yaml enforce every documented minimum version?

<details>
<summary>Show answer</summary>

Do not assume so. Use Helm 3.19.0+ and compatible Kubernetes/Airflow. Chart 1.16's README specified Kubernetes 1.29+; even the reviewed 1.22 templates rendered for 1.29, which is not proof of support.

</details>

## 4. Does executor alone determine Redis and worker resource kinds?

<details>
<summary>Show answer</summary>

It influences them, but Redis/external-broker settings and worker persistence also matter. Workers can be Deployments or StatefulSets, and Celery can use an external broker.

</details>

## 5. Does disabling PostgreSQL configure an external database?

<details>
<summary>Show answer</summary>

No. Prepare the database, migration privileges, URI/TLS and a connection reference such as metadataSecretName. With that Secret set, metadataConnection is not the authoritative source.

</details>

## 6. Should Fernet/API/JWT keys be regenerated on upgrades?

<details>
<summary>Show answer</summary>

Preserve them during ordinary upgrades. Fernet-key loss can break access to encrypted data, and JWT changes can affect active task authentication. Handle backup and rotation deliberately.

</details>

## 7. How does the example avoid default admin/admin?

<details>
<summary>Show answer</summary>

It disables createUserJob and uses interactive airflow users create for the selected FAB auth manager, prompting twice for the password. Other auth managers/SSO need their own procedures.

</details>

## 8. Does KubernetesExecutor always take 1–2 minutes to start?

<details>
<summary>Show answer</summary>

No. Measure image cache/pull, Kubernetes API/scheduler, node availability/provisioning, quotas and runtime initialization. Celery also has cold starts after scale-to-zero.

</details>

## 9. Can KubernetesExecutor use an arbitrary GPU/CLI worker image?

<details>
<summary>Show answer</summary>

The worker needs a compatible Airflow task runtime and DAG/provider dependencies. This differs from KubernetesPodOperator launching a child pod with a workload image.

</details>

## 10. Does having no worker pods make total Airflow idle cost zero?

<details>
<summary>Show answer</summary>

Control-plane, database, broker, node, storage and logging costs can remain. Per-pod execution or scale-to-zero does not guarantee zero total cost or complete security isolation.

</details>

## 11. What are the chart KEDA timing defaults versus the example?

<details>
<summary>Show answer</summary>

Defaults are pollingInterval=5s and cooldownPeriod=30s. The example explicitly chooses 10s/300s. Distinguish scale-to-zero cooldown from HPA scaling/stabilization above zero.

</details>

## 12. What should worker_concurrency become in the SQL?

<details>
<summary>Show answer</summary>

A numeric value rendered by the chart, 4 in this example—not a database column named worker_concurrency. Count the relevant running/queued tasks for the worker's queues/executors, divide and round up.

</details>

## 13. Why can a k8s alias cause mixed-executor scaling errors?

<details>
<summary>Show answer</summary>

TaskInstance stores task.executor. If the chart excludes only the literal KubernetesExecutor, tasks stored as k8s can enter the Celery count. Use filters matching actual stored values.

</details>

## 14. What if the query returns 25 with maxReplicaCount=20?

<details>
<summary>Show answer</summary>

The maximum bounds workers, so not all demand is immediately satisfied. Inspect backlog, concurrency, worker resources, database/broker load and node capacity together.

</details>

## 15. Is Airflow-pod TLS configuration enough for KEDA database access?

<details>
<summary>Show answer</summary>

KEDA is a separate database client needing DNS, networking, permissions, a compatible URI and CA. A URI's sslrootcert path must be readable by the scaler; the chart does not copy it automatically.

</details>

## 16. Is KEDA limited to Deployments?

<details>
<summary>Show answer</summary>

No. The chart targets a Deployment or StatefulSet according to Celery persistence. KubernetesExecutor task pods are not the same replica-pool pattern, but that does not prohibit other KEDA uses.

</details>

## 17. Does successful Helm --wait finish validation?

<details>
<summary>Show answer</summary>

Check successful migrations, Ready long-running components, DAG delivery, worker execution, Execution API, results and logs. Test workload-driven scaling, return to idle and recovery for KEDA profiles.

</details>

## 18. Does Helm uninstall immediately delete all PostgreSQL data?

<details>
<summary>Show answer</summary>

Pod removal and PVC/PV data lifecycles differ. Review PVC retention, StorageClass reclaim policy and external-database deletion/backups separately; do not indiscriminately remove shared namespaces, Secrets and databases.

</details>

[Guide](../../../data-on-eks/airflow/02-helm-deployment.md)

[Previous quiz](./01-architecture-quiz.md)

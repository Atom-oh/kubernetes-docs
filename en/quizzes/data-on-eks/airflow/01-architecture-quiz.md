# Airflow Architecture Quiz

Airflow 3.3.1 / Helm chart 1.22.0 · September 2026.

## 1. Which description of Airflow 2 DAG parsing is correct?

- A) All files were parsed only in the scheduler's same loop
- B) DAGs were read only from Redis
- C) File-processing subprocesses and optional standalone DAG processing already existed
- D) Tasks executed without parsing

<details>
<summary>Show answer</summary>

**C**

The scheduler could start a manager with per-file subprocesses, or use standalone processing. Serialized DAG scheduling and multi-scheduler HA also predated Airflow 3.

</details>

## 2. What does the Airflow 3 DAG processor do?

- A) Execute every operator
- B) Only issue UI-user JWTs
- C) Replace the Celery broker
- D) Parse/serialize bundle DAGs and update related metadata

<details>
<summary>Show answer</summary>

**D**

It is a required separate role in Airflow 3. Workers also need execution code/dependencies; placing DAG code only on the processor is insufficient.

</details>

## 3. What does separating the DAG processor enable?

- A) More independent deployment and tuning of parsing and scheduling
- B) Elimination of all scheduling latency
- C) Elimination of database bottlenecks
- D) Guaranteed HA by increasing replicas

<details>
<summary>Show answer</summary>

**A**

Fresh-DAG parse delay, shared resources/database load and excessive concurrency can still affect scheduling. Separation does not replace operational validation.

</details>

## 4. Who calls the API in a normal supervised Python Task SDK run?

- A) User task code directly executes metadata SQL
- B) The worker-side supervisor calls the Execution API with a task JWT
- C) Redis carries all state access
- D) Kubernetes stores XCom

<details>
<summary>Show answer</summary>

**B**

The task runner and supervisor communicate over a socket. Worker-to-API addressing/authentication/networking matters; inspect executor internals such as Celery result backends separately.

</details>

## 5. Which statement about the triggerer is correct?

- A) It runs every complete operator
- B) It is mandatory in every minimal deployment
- C) It runs deferred tasks' triggers; tasks later resume on workers
- D) All async tasks release worker slots

<details>
<summary>Show answer</summary>

**C**

A deployment without deferral can omit it. Deferred tasks release worker slots and normally pool slots, with pool behavior configurable.

</details>

## 6. Which statement about metadata databases and Celery brokers is correct?

- A) PostgreSQL and Redis are mandatory for every deployment
- B) SQLite is the standard production recommendation
- C) MariaDB and MySQL have identical support
- D) PostgreSQL/MySQL are supported and Celery has broker alternatives to Redis

<details>
<summary>Show answer</summary>

**D**

This series uses PostgreSQL as an example. SQLite is for development/testing, MariaDB is unsupported, and KubernetesExecutor does not inherently need a Celery broker.

</details>

## 7. Which fixed hybrid classes became unsupported in Airflow 3.0?

- A) LocalKubernetesExecutor and CeleryKubernetesExecutor
- B) LocalExecutor and CeleryExecutor
- C) KubernetesExecutor and every broker
- D) DAG processor and triggerer

<details>
<summary>Show answer</summary>

**A**

Fixed two-way hybrid classes differ from concurrent executor configuration. Configure compatible executors explicitly and choose them per task.

</details>

## 8. How do concurrent executors and DAG defaults work?

- A) Introduced only in 3.3; uninstalled executors also work
- B) Supported since 2.10.0; use executor in DAG default_args and task overrides
- C) Only one is ever allowed
- D) All choices use only Redis queue names

<details>
<summary>Show answer</summary>

**B**

The first configured executor is the default. Tasks select a configured name/alias, and DAG default_args can provide task defaults.

</details>

## 9. How do DAG bundles relate to git-sync?

- A) Airflow 3 removed git-sync
- B) Every S3DagBundle becomes versioned by enabling S3 versioning
- C) git-sync remains supported; versioning depends on the bundle
- D) Workers never need DAG code

<details>
<summary>Show answer</summary>

**C**

GitDagBundle supports versioning, while the reviewed Local/S3/GCS bundles do not. Verify delivery and the code version used on retries.

</details>

[Guide](../../../data-on-eks/airflow/01-architecture.md)

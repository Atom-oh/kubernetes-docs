# Airflow Architecture on Kubernetes Quiz

This quiz tests your understanding of Airflow 3's service decomposition, why DAG parsing moved out of the scheduler, the role of the dag-processor, and why the Airflow 2 hybrid executors were removed.

## Multiple Choice Questions

1. In Airflow 2, what was the scheduler process responsible for, in addition to scheduling task instances?
   - A) Serving the web UI
   - B) Parsing DAG files to keep its in-memory DAG representation current
   - C) Running deferrable operators
   - D) Managing the Celery worker pool

<details>

<summary>Show Answer</summary>

**Answer: B) Parsing DAG files to keep its in-memory DAG representation current**

**Explanation:**
In Airflow 2, the scheduler both scheduled task instances and parsed DAG files itself. Under load — many DAGs, deeply nested DAGs, or expensive top-level code in DAG files — this parsing work could starve the scheduler's actual scheduling loop, directly hurting the core reliability guarantee of getting ready tasks queued on time. Serving the UI was the webserver's job, not the scheduler's.
</details>

2. What is the primary responsibility of the `airflow dag-processor` service in Airflow 3?
   - A) Serving the REST API and authentication
   - B) Running Celery worker pods
   - C) Parsing DAG files and writing the result to the `serialized_dag` table
   - D) Electing the active controller for cluster metadata

<details>

<summary>Show Answer</summary>

**Answer: C) Parsing DAG files and writing the result to the `serialized_dag` table**

**Explanation:**
The dag-processor's sole job is to parse DAG files and persist the parsed structure to the metadata database's `serialized_dag` table. The scheduler then reads DAG structure from that table instead of re-parsing files itself, which is what lets DAG parsing and scheduling scale independently of each other.
</details>

3. Why did Airflow 3 make the dag-processor a mandatory service instead of the optional, opt-in process it was in Airflow 2?
   - A) To reduce the total number of Kubernetes pods needed
   - B) To fully remove DAG parsing from the scheduler's loop so it can no longer degrade scheduling latency
   - C) To eliminate the need for a metadata database
   - D) To allow DAGs to be written in languages other than Python

<details>

<summary>Show Answer</summary>

**Answer: B) To fully remove DAG parsing from the scheduler's loop so it can no longer degrade scheduling latency**

**Explanation:**
Making the dag-processor mandatory guarantees that DAG parsing always happens outside the scheduler's process, regardless of deployment configuration. This is Airflow 3's headline high-availability improvement: a spike in DAG count or a slow DAG file can no longer starve the scheduler's ability to queue ready tasks for every other DAG.
</details>

4. After the Airflow 3 architecture split, what does the scheduler read from the metadata database to know a DAG's structure?
   - A) The raw `.py` DAG file, parsed on each scheduling loop
   - B) The `serialized_dag` table, populated by the dag-processor
   - C) A cached copy of the DAG stored in Redis
   - D) The Celery broker's task queue

<details>

<summary>Show Answer</summary>

**Answer: B) The `serialized_dag` table, populated by the dag-processor**

**Explanation:**
The scheduler no longer parses DAG files at all in Airflow 3. It reads the already-parsed, serialized DAG structure from the `serialized_dag` table in Postgres, which the dag-processor keeps up to date. This is the mechanism that decouples scheduling throughput from DAG parsing cost.
</details>

5. Which Airflow 3 service replaced the Flask-based `webserver` from Airflow 2?
   - A) `airflow scheduler`
   - B) `airflow dag-processor`
   - C) `airflow api-server`
   - D) `airflow triggerer`

<details>

<summary>Show Answer</summary>

**Answer: C) `airflow api-server`**

**Explanation:**
The `airflow api-server` is a new FastAPI-based service that serves the UI, the REST API v2, and owns authentication — replacing the Flask-based webserver that handled these responsibilities in Airflow 2.
</details>

6. What is the role of the `airflow triggerer` service?
   - A) It parses DAG files on a schedule
   - B) It runs deferrable operators, resuming tasks asynchronously when an external event fires
   - C) It serves the Airflow REST API
   - D) It elects which scheduler replica is active

<details>

<summary>Show Answer</summary>

**Answer: B) It runs deferrable operators, resuming tasks asynchronously when an external event fires**

**Explanation:**
The triggerer's role is unchanged from Airflow 2: it runs deferrable operators, which release their worker slot while waiting on an external event (an API response, a file arriving, another job completing) and resume asynchronously once that event occurs, rather than blocking a worker the whole time.
</details>

7. Which two executors did Airflow 3.0 remove?
   - A) `KubernetesExecutor` and `CeleryExecutor`
   - B) `LocalExecutor` and `SequentialExecutor`
   - C) `CeleryKubernetesExecutor` and `LocalKubernetesExecutor`
   - D) `DebugExecutor` and `DaskExecutor`

<details>

<summary>Show Answer</summary>

**Answer: C) `CeleryKubernetesExecutor` and `LocalKubernetesExecutor`**

**Explanation:**
Airflow 3.0 removed both hybrid executor classes, `CeleryKubernetesExecutor` and `LocalKubernetesExecutor`. These existed in Airflow 2 to route some tasks to Celery workers and others to Kubernetes pods based on a task-level queue name.
</details>

8. What replaced the hybrid executors in Airflow 3?
   - A) A single new `HybridExecutor` class covering all combinations
   - B) The ability to configure multiple executors concurrently and assign one per task or per DAG
   - C) Removing the option to use `CeleryExecutor` at all
   - D) A requirement that every task run on `KubernetesExecutor`

<details>

<summary>Show Answer</summary>

**Answer: B) The ability to configure multiple executors concurrently and assign one per task or per DAG**

**Explanation:**
Instead of hard-coding one specific two-way split between Celery and Kubernetes, Airflow 3 lets a deployment configure multiple executors at once and assign an executor explicitly to a task or a whole DAG (for example, one task using `KubernetesExecutor` while the rest of the DAG uses the deployment default). This generalizes the hybrid-executor idea to any combination of executors, without a dedicated class per pairing.
</details>

9. Which backing service is required only when using `CeleryExecutor`, not for a baseline Airflow 3 deployment?
   - A) PostgreSQL
   - B) Redis
   - C) The dag-processor
   - D) The api-server

<details>

<summary>Show Answer</summary>

**Answer: B) Redis**

**Explanation:**
PostgreSQL is always required as the metadata database, and the dag-processor and api-server are core services in every Airflow 3 deployment. Redis (or RabbitMQ) is only needed to back the Celery task broker when `CeleryExecutor` is in use — a `KubernetesExecutor`-only deployment doesn't need it.
</details>

---

[Return to Learning Materials](../../../data-on-eks/airflow/01-architecture.md)

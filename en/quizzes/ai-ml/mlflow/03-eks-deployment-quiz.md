# Deploying MLflow on EKS Quiz

This quiz tests your understanding of MLflow's tracking server architecture on EKS: the backend store, the artifact store, IAM access patterns, and operational considerations for running the tracking server as a shared team service.

## Multiple Choice Questions

1. What is the main trade-off of self-hosting MLflow's tracking server on EKS instead of using a managed alternative like SageMaker's MLflow-compatible tracking capability?
   - A) Self-hosting is always cheaper regardless of team size
   - B) A team already on EKS reuses existing deployment, observability, and IAM patterns, but takes on operating the tracking server, backend store, and artifact store itself
   - C) Managed alternatives cannot log metrics or parameters at all
   - D) There is no trade-off; the two options are functionally identical

<details>

<summary>Show Answer</summary>

**Answer: B) A team already on EKS reuses existing deployment, observability, and IAM patterns, but takes on operating the tracking server, backend store, and artifact store itself**

**Explanation:**
Self-hosting lets a team reuse the same Kubernetes deployment, observability, and IAM (IRSA/Pod Identity) patterns it already uses for other workloads, in exchange for operating the tracking server, its backend database, and its artifact store directly, rather than delegating that to a managed alternative.
</details>

2. Why is MLflow's default SQLite backend store unsuitable for a shared team tracking server?
   - A) SQLite cannot store floating-point metric values
   - B) SQLite does not support the level of concurrent writes a shared tracking server needs
   - C) SQLite requires a separate EKS node group
   - D) SQLite artifacts expire after 30 days

<details>

<summary>Show Answer</summary>

**Answer: B) SQLite does not support the level of concurrent writes a shared tracking server needs**

**Explanation:**
SQLite works fine for a single experimenter, but breaks down once more than one process needs to write concurrently — it doesn't support the concurrent-writer scale a shared team tracking server requires. This is why a real database such as RDS PostgreSQL or Aurora Serverless v2 replaces it in production.
</details>

3. What kind of data does the backend store hold, as opposed to the artifact store?
   - A) The backend store holds large binary objects like serialized models; the artifact store holds structured metadata
   - B) The backend store holds structured metadata (experiments, runs, params, metrics, registered models, versions, aliases); the artifact store holds large binary objects (models, plots, datasets)
   - C) Both stores hold identical copies of all data for redundancy
   - D) The backend store only holds usernames and passwords

<details>

<summary>Show Answer</summary>

**Answer: B) The backend store holds structured metadata (experiments, runs, params, metrics, registered models, versions, aliases); the artifact store holds large binary objects (models, plots, datasets)**

**Explanation:**
The backend store is a relational database holding everything queryable with SQL — experiments, runs, params, metrics, registered models, versions, and aliases. The artifact store (S3 on AWS) holds the large binary objects the backend store does not, such as logged models, plots, and datasets.
</details>

4. On AWS, which two services are the standard choices for MLflow's backend store in production?
   - A) DynamoDB and EFS
   - B) Amazon RDS for PostgreSQL and Aurora Serverless v2
   - C) ElastiCache and S3
   - D) Redshift and Glacier

<details>

<summary>Show Answer</summary>

**Answer: B) Amazon RDS for PostgreSQL and Aurora Serverless v2**

**Explanation:**
Both are real relational databases that support concurrent writers. Aurora Serverless v2 is worth considering specifically because it can scale with bursty tracking load rather than requiring the database to be sized for peak load year-round.
</details>

5. What is the community Helm chart mentioned for deploying MLflow on Kubernetes, and how is its repository added?
   - A) `bitnami/mlflow`, added via `helm repo add bitnami https://charts.bitnami.com/bitnami`
   - B) `community-charts/mlflow`, added via `helm repo add community-charts https://community-charts.github.io/helm-charts`
   - C) There is no maintained community chart for MLflow
   - D) `mlflow/mlflow-operator`, installed only via `kubectl apply -f`

<details>

<summary>Show Answer</summary>

**Answer: B) `community-charts/mlflow`, added via `helm repo add community-charts https://community-charts.github.io/helm-charts`**

**Explanation:**
`community-charts/helm-charts` maintains an MLflow chart supporting configurable backend database and object storage settings, offering a practical alternative to writing your own Deployment/Service/Ingress manifests by hand.
</details>

6. Which EKS mechanism is presented as the more modern default choice for binding an IAM role to the tracking server's ServiceAccount on a new deployment?
   - A) Static IAM access keys stored in a ConfigMap
   - B) EKS Pod Identity, with IRSA remaining valid for clusters already standardized on it
   - C) Instance profiles attached directly to worker node EC2 instances
   - D) A shared root AWS account credential baked into the container image

<details>

<summary>Show Answer</summary>

**Answer: B) EKS Pod Identity, with IRSA remaining valid for clusters already standardized on it**

**Explanation:**
EKS Pod Identity is the newer mechanism for binding IAM roles to pods and is increasingly the recommended default for new IAM-to-pod bindings on EKS generally. IRSA remains a valid choice, particularly for teams or clusters already standardized on it.
</details>

7. Why can a Postgres-backed MLflow tracking server safely run multiple replicas, while the SQLite-backed default cannot be scaled out at all?
   - A) Postgres replicas automatically synchronize in-memory state between Pods
   - B) The tracking server is stateless when backed by Postgres and S3, since all shared state lives outside the Pod, whereas SQLite cannot tolerate concurrent writers
   - C) SQLite requires more CPU than Postgres, so scaling it out is wasteful
   - D) Kubernetes forbids running more than one replica of any Deployment using a database

<details>

<summary>Show Answer</summary>

**Answer: B) The tracking server is stateless when backed by Postgres and S3, since all shared state lives outside the Pod, whereas SQLite cannot tolerate concurrent writers**

**Explanation:**
Because all durable state lives in the backend store and artifact store rather than in the Pod, a Postgres-backed tracking server is stateless and safe to scale horizontally. SQLite's lack of concurrent-writer support makes the single-process default unsafe to scale out at all.
</details>

8. What is described as the natural next step after a model has a registered version or alias, and why is it out of scope for this series?
   - A) Re-running the training job; it's out of scope because training was already covered in Part 1
   - B) Loading that model version into a serving system (KServe, a custom wrapper, SageMaker, etc.); it's out of scope because serving infrastructure is its own broad topic
   - C) Deleting the model version; it's out of scope because deletion isn't supported by MLflow
   - D) Migrating the backend store to DynamoDB; it's out of scope because DynamoDB isn't supported

<details>

<summary>Show Answer</summary>

**Answer: B) Loading that model version into a serving system (KServe, a custom wrapper, SageMaker, etc.); it's out of scope because serving infrastructure is its own broad topic**

**Explanation:**
Once a model has a registered version or alias, many teams move on to loading it into a serving system such as KServe, a custom FastAPI/Flask wrapper, or SageMaker. That serving layer is a broad topic in its own right and is explicitly out of scope for this three-part series.
</details>

## Short Answer Questions

9. Name the three core architecture pieces that must be deployed for MLflow to run as a shared team service on EKS, and briefly state what each one stores or does.

<details>

<summary>Show Answer</summary>

**Answer:**
- The MLflow Tracking Server: a stateless container running `mlflow server`, exposing the REST API and UI.
- The backend store: a relational database (e.g., RDS PostgreSQL or Aurora Serverless v2) holding structured metadata — experiments, runs, params, metrics, registered models, versions, and aliases.
- The artifact store: object storage (S3 on AWS) holding large binary objects such as logged models, plots, and datasets.

**Explanation:**
None of the three is optional once more than one person is sharing the tracking server — the tracking server needs somewhere durable to write both its structured metadata and its large artifacts, and neither belongs in the tracking server Pod itself.
</details>

10. Explain why readiness and liveness probes matter for a tracking server Deployment, and why this document does not specify an exact health-check endpoint path.

<details>

<summary>Show Answer</summary>

**Answer:**
Readiness and liveness probes let the Service route traffic only to Pods that can actually serve requests, and let Kubernetes automatically restart a Pod that has stopped responding — standard practice for any long-running Kubernetes service. This document doesn't name an exact health-check path because it can vary by MLflow version, so it should be confirmed against the specific version being deployed rather than assumed.

**Explanation:**
Probing against a made-up or version-mismatched endpoint path would either mark healthy Pods as unready or fail to catch a genuinely wedged Pod, so verifying the real path for your MLflow version is the safer approach.
</details>

---

[Return to Learning Materials](../../../ai-ml/mlflow/03-eks-deployment.md)

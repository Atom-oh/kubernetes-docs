# MLflow EKS Deployment Quiz

## Multiple Choice Questions

1. What is the main EKS self-hosting trade-off?
   - A) Always lower cost than managed services
   - B) Reuse Kubernetes patterns while operating servers, stores, and access controls
   - C) Managed services cannot track experiments
   - D) S3 and databases are created automatically

<details>
<summary>Show Answer</summary>

**Answer: B**

Compare operational work, features, supported versions, and measured load.
</details>

2. Which SQLite concurrency statement is accurate?
   - A) The second user always breaks it immediately
   - B) Multiple processes and serialized writes are possible, with writer/locking/shared-file limits
   - C) It is not relational
   - D) Separate Pod-local files automatically form one shared DB

<details>
<summary>Show Answer</summary>

**Answer: B**

Distinguish SQLite capabilities from multi-Pod storage topology.
</details>

3. What is the reviewed community chart 1.11.7 metadata default?
   - A) Mandatory RDS PostgreSQL
   - B) S3 objects
   - C) backendStore.defaultSqlitePath is :memory:
   - D) An automatically provisioned durable PVC

<details>
<summary>Show Answer</summary>

**Answer: C**

The chart override differs from the upstream CLI’s new SQLite-file default.
</details>

4. Does an external tracking PostgreSQL database automatically share every other state?
   - A) Yes, every auth DB and cache
   - B) Yes, all worker memory
   - C) Yes, every session secret
   - D) No; inspect separate auth DBs, secrets, queues, and caches

<details>
<summary>Show Answer</summary>

**Answer: D**

Check shared state for enabled features before increasing replicas.
</details>

5. How should chart, image, and source versions be handled?
   - A) They always share one number
   - B) A source tag guarantees the OCI package exists
   - C) Verify each and download/render the actual package
   - D) A latest tag removes the need to review image digests

<details>
<summary>Show Answer</summary>

**Answer: C**

The reviewed upstream chart source and appVersion also differed.
</details>

6. Does ServiceAccount IAM access to S3 automatically allow PostgreSQL login?
   - A) Always
   - B) No; separately configure DB networking, TLS, users/credentials or IAM DB auth
   - C) Only if the bucket name matches
   - D) Put the DB password in the image

<details>
<summary>Show Answer</summary>

**Answer: B**

These are separate authorization and authentication layers.
</details>

7. What does EKS Pod Identity require?
   - A) Unconditional support for all Fargate and Windows Pods
   - B) Only a ServiceAccount name
   - C) Linux EC2 workers, Agent, association, supported SDK, and related setup
   - D) A static root access key

<details>
<summary>Show Answer</summary>

**Answer: C**

Check IRSA and Pod Identity support and configuration separately.
</details>

8. Do SecretKeyRef and allowed_hosts alone complete security?
   - A) They eliminate environment exposure and implement all user authorization
   - B) No; review secret delivery and application authentication/authorization separately
   - C) They automatically back up databases
   - D) All CORS origins must be allowed

<details>
<summary>Show Answer</summary>

**Answer: B**

Understand runtime secret injection and host-validation boundaries.
</details>

## Short Answer Questions

9. Does /health returning 200 prove RDS and S3 are healthy?

<details>
<summary>Show Answer</summary>

No. The verified implementation returns OK, 200 for HTTP process responsiveness. Check ongoing database, S3, authorization, and actual workload paths separately.
</details>

10. What matters when assessing frequent logging and Aurora Serverless v2?

<details>
<summary>Show Answer</summary>

Measure batching, transactions, metric history, trace payloads, and pools across replicas/workers. Aurora has capacity, connection, I/O, and transaction limits; unlimited burst absorption or minimum cost is not guaranteed.
</details>

---

[Return to Learning Materials](../../../ai-ml/mlflow/03-eks-deployment.md)

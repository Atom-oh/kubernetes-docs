# Amazon EMR on EKS Quiz

This quiz tests your understanding of EMR on EKS virtual clusters, the StartJobRun submission model, job execution IAM roles, and when to choose EMR on EKS versus a self-managed Spark Operator.

## Multiple Choice Questions

1. What is a virtual cluster in EMR on EKS?
   - A) A separate, isolated Kubernetes cluster created just for EMR
   - B) The mapping between an EMR control-plane concept and a real EKS namespace
   - C) A virtual machine that hosts the Spark driver
   - D) A snapshot of an EKS cluster's node group

<details>

<summary>Show Answer</summary>

**Answer: B) The mapping between an EMR control-plane concept and a real EKS namespace**

**Explanation:**
A virtual cluster registers an existing EKS namespace with the EMR control plane. It doesn't provision any new infrastructure by itself — it's a pointer, not a cluster. Every job submitted against that virtual cluster ID lands as driver/executor pods inside the namespace it points to, subject to whatever quotas and RBAC already apply there.
</details>

2. What is the fundamental UX difference between EMR on EKS and the self-managed Spark Operator approach?
   - A) EMR on EKS doesn't run on Kubernetes at all
   - B) Jobs are submitted via the StartJobRun API rather than `kubectl apply` of a `SparkApplication` CR
   - C) The Spark Operator cannot run on EKS, only on-premises
   - D) EMR on EKS only supports batch jobs, never streaming

<details>

<summary>Show Answer</summary>

**Answer: B) Jobs are submitted via the StartJobRun API rather than `kubectl apply` of a `SparkApplication` CR**

**Explanation:**
The Spark Operator approach defines a job as a `SparkApplication` Kubernetes object and applies it with `kubectl` (often via GitOps), with a controller reconciling that CRD. EMR on EKS instead exposes submission as a regular AWS API — callable from the CLI, SDK, console, or Step Functions — with no `kubectl` access needed to launch a job.
</details>

3. What must happen before a job execution IAM role can be used with a virtual cluster?
   - A) Nothing — any IAM role in the account can be used automatically
   - B) The role must be onboarded, updating its trust policy so EMR on EKS can assume it for pods in that namespace
   - C) The role must be attached directly to the EKS worker node instance profile
   - D) The role must be deleted and recreated for every job run

<details>

<summary>Show Answer</summary>

**Answer: B) The role must be onboarded, updating its trust policy so EMR on EKS can assume it for pods in that namespace**

**Explanation:**
A job execution role is scoped per job (to specific S3 buckets, a Data Catalog, a KMS key, etc.) and passed explicitly on each `start-job-run` call. Before that works, its trust policy must be updated — via `update-role-trust-policy` — so EMR on EKS can assume it on behalf of pods running in the virtual cluster's namespace, bound through an IRSA-style OIDC trust relationship.
</details>

4. Which statement about EMR release labels is correct?
   - A) They follow the pattern `emr-x.x.x-latest` and pin a specific, AWS-patched Spark build
   - B) They only control the EKS Kubernetes version, not the Spark version
   - C) A release label must be rebuilt manually as a Docker image before use
   - D) Release labels are identical to upstream Apache Spark version numbers with no AWS patches

<details>

<summary>Show Answer</summary>

**Answer: A) They follow the pattern `emr-x.x.x-latest` and pin a specific, AWS-patched Spark build**

**Explanation:**
A release label like `emr-7.6.0-latest` maps to a specific Spark build such as Spark 3.5.3-amzn-0 — the `-amzn-N` suffix indicating AWS's own patches (S3 connector tuning, AQE and shuffle improvements) layered on top of the open-source release. Passing the release label to `start-job-run` selects both the Spark version and the container image used for the job's pods.
</details>

5. Since which EMR version can EMR on EKS submit jobs through the open-source Spark Operator as a submission-model choice?
   - A) EMR 5.0
   - B) EMR 6.10
   - C) EMR 7.6
   - D) This is not possible at any version — the two are always mutually exclusive

<details>

<summary>Show Answer</summary>

**Answer: B) EMR 6.10**

**Explanation:**
Since EMR 6.10, EMR on EKS can delegate job submission to the Spark Operator's CRD-based reconciliation instead of its own native pod-creation path, while still using EMR's AWS-optimized Spark runtime and release-label versioning. This means EMR on EKS and the self-managed Spark Operator aren't strictly either/or.
</details>

6. What is EMR Studio?
   - A) A CLI tool for tagging EMR clusters
   - B) A notebook/IDE-style interface for developing and submitting Spark code against EKS virtual clusters
   - C) A billing dashboard for EMR on EKS costs
   - D) A replacement for the `start-job-run` API that cannot run interactive code

<details>

<summary>Show Answer</summary>

**Answer: B) A notebook/IDE-style interface for developing and submitting Spark code against EKS virtual clusters**

**Explanation:**
EMR Studio gives you a Jupyter-style interactive development loop against the same virtual clusters that back scheduled `start-job-run` pipelines, using the same underlying virtual-cluster/execution-role model.
</details>

7. Which of the following is an advantage of EMR on EKS over the self-managed Spark Operator?
   - A) Full control over the exact Spark build, including non-AWS forks
   - B) Native CloudWatch Logs/Metrics, Step Functions, and EventBridge integration without building it yourself
   - C) Jobs are Kubernetes manifests that fit directly into any GitOps pipeline
   - D) No AWS control plane or API dependency at all

<details>

<summary>Show Answer</summary>

**Answer: B) Native CloudWatch Logs/Metrics, Step Functions, and EventBridge integration without building it yourself**

**Explanation:**
EMR on EKS ships with built-in AWS service integration for logging, metrics, and orchestration. The self-managed Spark Operator, by contrast, gives you full control over the Spark/Kubernetes version pairing and fits naturally into a manifest-based GitOps pipeline, but you have to wire up observability and orchestration integrations yourself.
</details>

8. Why might a team stay with the self-managed Spark Operator instead of EMR on EKS?
   - A) They need to run a Spark build or fork that hasn't landed in any EMR release label yet
   - B) They want managed CloudWatch integration
   - C) They want to avoid ever writing a `SparkApplication` manifest
   - D) They want AWS to control their Spark version upgrade schedule

<details>

<summary>Show Answer</summary>

**Answer: A) They need to run a Spark build or fork that hasn't landed in any EMR release label yet**

**Explanation:**
EMR release labels curate a specific set of AWS-patched Spark versions. If a team needs a newer upstream release, a custom fork, or a non-AWS-patched build, or needs full control over upgrade timing and portability to non-EKS clusters, the self-managed Spark Operator remains the better fit.
</details>

9. What happens to the pods running underneath a job submitted via EMR on EKS's StartJobRun API?
   - A) They run in a separate, hidden cluster invisible to `kubectl`
   - B) They are ordinary EKS pods in the virtual cluster's namespace, visible via `kubectl get pods`
   - C) They run entirely outside of Kubernetes, on AWS Fargate for EMR
   - D) They are only visible through the EMR console, never through the Kubernetes API

<details>

<summary>Show Answer</summary>

**Answer: B) They are ordinary EKS pods in the virtual cluster's namespace, visible via `kubectl get pods`**

**Explanation:**
Even though you submit the job through an AWS API rather than `kubectl apply`, the resulting driver and executor pods are regular pods scheduled in the namespace the virtual cluster points to — you can inspect them with `kubectl get pods -n <namespace>` like any other workload, you just don't author their spec directly.
</details>

10. Deleting a virtual cluster does which of the following?
    - A) Deletes the underlying EKS namespace and everything running in it
    - B) Deletes only the EMR registration; the namespace and its running workloads are untouched
    - C) Deletes the entire EKS cluster
    - D) Automatically deletes all job execution IAM roles onboarded to it

<details>

<summary>Show Answer</summary>

**Answer: B) Deletes only the EMR registration; the namespace and its running workloads are untouched**

**Explanation:**
A virtual cluster is a pointer/registration, not new infrastructure. Deleting it removes the mapping between the EMR control plane and the EKS namespace, but the namespace itself and anything running inside it are unaffected.
</details>

## Short Answer Questions

11. What AWS API call do you use to submit a Spark job to EMR on EKS, as opposed to applying a Kubernetes manifest?

<details>

<summary>Show Answer</summary>

**Answer: `StartJobRun`**

**Explanation:**
`StartJobRun` (called via `aws emr-containers start-job-run`) is the API used to submit a job to a virtual cluster. It takes the virtual cluster ID, an execution role ARN, a release label, and a job driver definition, and can be called from the CLI, any AWS SDK, the console, or orchestration tools like Step Functions.
</details>

12. What IAM concept must be scoped per job and passed explicitly on every `start-job-run` call?

<details>

<summary>Show Answer</summary>

**Answer: The job execution role**

**Explanation:**
Unlike a role attached once to a cluster, EMR on EKS's job execution role is scoped to what a specific job is allowed to access and must be passed via `--execution-role-arn` on each `start-job-run` call. It must first be onboarded to the virtual cluster by updating its trust policy.
</details>

13. What naming pattern do EMR release labels follow?

<details>

<summary>Show Answer</summary>

**Answer: `emr-x.x.x-latest`**

**Explanation:**
For example, `emr-7.0.0-latest` maps to Spark 3.5.0-amzn-0, and `emr-7.6.0-latest` maps to Spark 3.5.3-amzn-0. The label selects both the Spark version and the container image used for the job's driver/executor pods.
</details>

14. Which upcoming EMR release line brings Spark 4.0 to GA across EMR on EC2, EMR Serverless, and EMR on EKS?

<details>

<summary>Show Answer</summary>

**Answer: The `emr-spark-8.0` release line**

**Explanation:**
The `emr-spark-8.0` release line is the one that brings Spark 4.0 GA uniformly across all three EMR deployment targets — EC2, Serverless, and EKS.
</details>

15. Since EMR 6.10, what alternate job-submission mechanism can EMR on EKS delegate to internally?

<details>

<summary>Show Answer</summary>

**Answer: The open-source Spark Operator**

**Explanation:**
Since EMR 6.10, EMR on EKS can submit jobs through the open-source Spark Operator's CRD-based reconciliation as a submission-model choice, instead of only through its own native pod-creation path — while still using EMR's optimized Spark runtime and release-label versioning.
</details>

## Hands-on Questions

16. Write the AWS CLI command that registers an existing EKS namespace `emr-spark` on cluster `my-eks-cluster` as an EMR virtual cluster named `my-spark-vc`.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
aws emr-containers create-virtual-cluster \
  --name my-spark-vc \
  --container-provider '{
    "id": "my-eks-cluster",
    "type": "EKS",
    "info": {
      "eksInfo": {
        "namespace": "emr-spark"
      }
    }
  }'
```

**Explanation:**
`create-virtual-cluster` registers the namespace `emr-spark` on EKS cluster `my-eks-cluster` with the EMR control plane. The call returns a `virtualClusterId` used in every subsequent `start-job-run` call. No new infrastructure is provisioned by this call — it only creates the registration.
</details>

17. Write the AWS CLI command that grants the EMR on EKS service permission to assume the job execution role `my-job-execution-role` for pods in namespace `emr-spark` on cluster `my-eks-cluster`.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
aws emr-containers update-role-trust-policy \
  --cluster-name my-eks-cluster \
  --namespace emr-spark \
  --role-name my-job-execution-role
```

**Explanation:**
`update-role-trust-policy` onboards the role to the virtual cluster by updating its trust policy so EMR on EKS can assume it on behalf of pods running in that namespace, bound through an IRSA-style OIDC trust relationship. This must succeed before the role can be passed as `--execution-role-arn` on a `start-job-run` call.
</details>

18. Write the AWS CLI command to submit a PySpark job (`s3://my-bucket/jobs/etl-job.py`) to virtual cluster `abcd1234efgh5678ijkl9012mnop` using execution role `arn:aws:iam::111122223333:role/my-job-execution-role` and release label `emr-7.6.0-latest`.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
aws emr-containers start-job-run \
  --virtual-cluster-id abcd1234efgh5678ijkl9012mnop \
  --name my-etl-job \
  --execution-role-arn arn:aws:iam::111122223333:role/my-job-execution-role \
  --release-label emr-7.6.0-latest \
  --job-driver '{
    "sparkSubmitJobDriver": {
      "entryPoint": "s3://my-bucket/jobs/etl-job.py",
      "sparkSubmitParameters": "--conf spark.executor.instances=4 --conf spark.executor.memory=4G"
    }
  }'
```

**Explanation:**
`--virtual-cluster-id` targets the namespace the job runs in, `--execution-role-arn` scopes what the job can access, and `--release-label` selects the Spark version and container image. The `--job-driver` argument's `sparkSubmitJobDriver.entryPoint` and `sparkSubmitParameters` mirror the arguments you'd otherwise pass directly to `spark-submit`.
</details>

---

[Return to Learning Materials](../../../data-on-eks/spark/03-emr-on-eks.md)

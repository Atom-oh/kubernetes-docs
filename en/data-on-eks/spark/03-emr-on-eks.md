# Part 3: Amazon EMR on EKS

> **Last Updated**: July 15, 2026

## Lab Environment Setup

To follow along with the examples in this document, you will need the following tools and environment:

### Required Tools

* AWS CLI v2 (for registering virtual clusters and calling `emr-containers` APIs)
* A working Amazon EKS cluster (v1.30 or later recommended)
* IAM permissions to create the EMR virtual cluster's IAM role and each job's execution role
* kubectl v1.30 or later (for inspecting the namespace EMR on EKS targets)

Part 1 covered running `spark-submit` directly against Kubernetes, and Part 2 covers wrapping that same submission model in the open-source Spark Operator's CRD-based workflow. This part covers a third option: Amazon EMR on EKS, AWS's managed Spark runtime that runs on top of your own EKS cluster rather than replacing it.

## What EMR on EKS Actually Changes

EMR on EKS doesn't give you a different cluster — your driver and executor pods still land on the same EKS nodes as everything else. What it changes is the **submission model and the Spark runtime**. Instead of running `kubectl apply` against a `SparkApplication` custom resource (the Part 2 approach) or calling `spark-submit` yourself (the Part 1 approach), you call the **StartJobRun API**, and AWS's control plane translates that into pods running an AWS-optimized Spark build.

### Virtual Clusters: the Core Abstraction

A **virtual cluster** is the mapping between an EMR concept and a real Kubernetes object: it registers a single EKS namespace with the EMR control plane. Nothing is provisioned inside the namespace at registration time — a virtual cluster is a pointer, not new infrastructure. Every job you submit against that virtual cluster ID lands as driver/executor pods inside the namespace it points to, governed by whatever `ResourceQuota`, `LimitRange`, and RBAC already apply to that namespace.

```bash
# Register an existing EKS namespace as an EMR virtual cluster
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

This call returns a `virtualClusterId` — an opaque identifier you'll pass to every subsequent `start-job-run` call. Deleting a virtual cluster only deletes the registration; it does not touch the namespace or anything running in it.

### Job Execution IAM Roles

Every job run needs a **job execution role**: an IAM role scoped to what that specific job is allowed to touch (an S3 bucket, a Glue Data Catalog, a KMS key), passed explicitly on each `start-job-run` call rather than attached once to the cluster. The role must first be **onboarded** to the virtual cluster — its trust policy has to allow the EMR on EKS service to assume it for pods running in that namespace, bound to a Kubernetes service account via an IRSA-style OIDC trust relationship. This mirrors IRSA's mechanics from Part 2's IAM discussion, but the binding is between the execution role and EMR-managed pods rather than a service account you create and manage yourself.

```bash
# Grant the EMR on EKS service permission to assume the job execution role
aws emr-containers update-role-trust-policy \
  --cluster-name my-eks-cluster \
  --namespace emr-spark \
  --role-name my-job-execution-role
```

## Submitting a Job: StartJobRun vs. kubectl apply

This is the fundamental UX difference from Part 2. The Spark Operator approach submits a job by writing a `SparkApplication` YAML manifest and applying it with `kubectl` (or a GitOps tool syncing it from Git) — the job's entire definition lives as a Kubernetes object, reconciled by a controller watching that CRD. EMR on EKS instead exposes job submission as a **regular AWS API**, callable from the CLI, any AWS SDK, the console, or a Step Functions state machine — no `kubectl` access to the cluster is required to run a job at all.

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
  }' \
  --configuration-overrides '{
    "monitoringConfiguration": {
      "cloudWatchMonitoringConfiguration": {
        "logGroupName": "/emr-containers/my-spark-vc",
        "logStreamNamePrefix": "etl-job"
      }
    }
  }'
```

![Sequence diagram showing a client starting an EMR job run, EMR's control plane binding the request to a virtual cluster mapped to an EKS namespace, that namespace creating a driver pod under the job's IAM execution role, the driver requesting executor pods, and status/logs/metrics reporting back to EMR.](../../.gitbook/assets/en-data-on-eks-spark-03-emr-on-eks-0.png)

The pods that eventually run are ordinary EKS pods — they show up under `kubectl get pods -n emr-spark` like anything else — but you never author their spec directly. The `release-label` you pass (`emr-7.6.0-latest`, for example) selects both the Spark version and the container image EMR uses for the driver/executor pods, so there's no Dockerfile to build and push yourself.

### EMR Release Labels

EMR on EKS versions its Spark runtime through **release labels**, following the pattern `emr-x.x.x-latest`. Each release label pins a specific, AWS-patched Spark build:

| Release Label | Spark Version |
| --- | --- |
| `emr-7.0.0-latest` | Spark 3.5.0-amzn-0 |
| `emr-7.6.0-latest` | Spark 3.5.3-amzn-0 |

The `-amzn-N` suffix signals that this isn't stock upstream Spark — it's the open-source release plus AWS's own patches (S3 connector tuning, AQE and shuffle improvements, and other performance backports) layered on top. The `emr-spark-8.0` release line is the one that brings **Spark 4.0** to GA across EMR on EC2, EMR Serverless, and EMR on EKS uniformly.

### EMR Studio

**EMR Studio** is a notebook/IDE-style interface for developing and running Spark code against your virtual clusters interactively, instead of packaging a job and calling `start-job-run` from the CLI every time. It's the same virtual-cluster/execution-role model underneath — Studio submits through the same APIs — but gives you a Jupyter-style development loop for exploration before a job graduates into a scheduled `start-job-run` pipeline.

## EMR on EKS and the Spark Operator Aren't Mutually Exclusive

It's tempting to read EMR on EKS and Part 2's self-managed Spark Operator as two competing, either-or submission paths. Since **EMR 6.10**, that's no longer strictly true: EMR on EKS can itself submit jobs *through* the open-source Spark Operator as a job-submission-model choice, rather than only through its own native driver/executor pod creation. In that mode, you still get EMR's AWS-optimized Spark runtime and release-label versioning, but the underlying reconciliation follows the Spark Operator's CRD-based lifecycle instead of EMR's own internal pod management. This matters if you've already standardized your GitOps pipeline around `SparkApplication` manifests and don't want to give that up just to get EMR's managed runtime and job-run API.

## Comparing EMR on EKS vs. the Self-Managed Spark Operator

| Aspect | Amazon EMR on EKS | Self-Managed Spark Operator (Part 2) |
| --- | --- | --- |
| **Spark runtime** | AWS-optimized build (`-amzn-N`) with backported performance/AQE improvements | Vanilla upstream Spark, or any custom build you choose |
| **Job submission** | `StartJobRun` API (CLI/SDK/console/Step Functions) | `kubectl apply` of a `SparkApplication` CR, typically via GitOps |
| **Version control** | Pick a `release-label`; AWS curates the Spark/runtime pairing | You choose the exact Spark and Kubernetes versions, upgraded on your own schedule |
| **Operational burden** | AWS manages the runtime image and much of the submission plumbing | You own the Operator's lifecycle, CRD versions, and upgrade timing |
| **AWS service integration** | Native CloudWatch Logs/Metrics, Step Functions, EventBridge integration built in | Requires wiring your own Prometheus/Grafana/EventBridge integration |
| **GitOps fit** | Jobs are API calls, not manifests — needs a wrapper (Lambda, Step Functions) to fit a GitOps pipeline cleanly | `SparkApplication` is a native Kubernetes object; fits directly into Argo CD/Flux like any other manifest |
| **Portability** | AWS-specific control plane and APIs | Portable to any Kubernetes cluster running the Operator |
| **Interactive development** | EMR Studio notebooks against virtual clusters | Bring your own notebook/IDE integration |
| **Submission-model flexibility** | Can delegate to the Spark Operator underneath (EMR 6.10+) for CRD-based reconciliation while keeping the managed runtime | N/A — it's the CRD-based model itself |

### Why choose EMR on EKS

* You want AWS's optimized Spark runtime and don't want to track upstream performance patches yourself
* You want to submit and monitor jobs through a managed API/console, wired into Step Functions or EventBridge for orchestration, rather than maintaining your own submission tooling
* You want CloudWatch Logs/Metrics for job observability without building that integration yourself
* Your team wants an interactive notebook experience (EMR Studio) against the same EKS infrastructure that runs production jobs

### Why stay with the self-managed Spark Operator anyway

* You need to run a specific Spark build (a newer upstream release, a custom fork, or a non-AWS-patched version) that hasn't landed in an EMR release label yet
* Your platform is already fully GitOps-driven around Kubernetes manifests, and adding an AWS-API submission path would fragment that pipeline
* You want full control over the exact Kubernetes and Spark version pairing, upgraded on your own timeline rather than AWS's release-label cadence
* You need portability to a non-EKS Kubernetes cluster

In practice, EMR 6.10+'s ability to run EMR on EKS jobs through the Spark Operator means this isn't always a hard choice — you can get AWS's managed runtime and job-run API while still reconciling through the same `SparkApplication` CRD your GitOps pipeline already watches.

## Decision Guide

Use this checklist to narrow down between EMR on EKS and the self-managed Spark Operator.

* **Do you want AWS to curate the Spark build and patch cadence for you?** → Yes: EMR on EKS / No: self-managed Spark Operator gives you the exact version you choose
* **Do jobs need to be triggered from Step Functions, EventBridge, or another AWS orchestration service without custom glue code?** → Yes: EMR on EKS's `StartJobRun` API / No: either fits
* **Is your platform already fully GitOps-driven around Kubernetes manifests?** → Yes: the Spark Operator (or EMR on EKS running through it, since 6.10) / No: EMR on EKS's API-based submission is simpler to adopt
* **Do you need a Spark build EMR hasn't shipped a release label for yet (a bleeding-edge upstream version or a custom fork)?** → Yes: self-managed Spark Operator / No: EMR on EKS's release labels are enough
* **Do you want an interactive notebook experience against the same infrastructure that runs production jobs?** → Yes: EMR Studio (EMR on EKS) / No: bring your own notebook integration

As with MSK vs. Strimzi in the Kafka series, the two aren't always exclusive — since EMR 6.10, choosing EMR on EKS doesn't have to mean giving up the Spark Operator's CRD-based workflow.

## Next Steps

Part 1 and Part 2 covered running Spark yourself on EKS — directly via `spark-submit` or declaratively via the Spark Operator. This part covered EMR on EKS, AWS's managed alternative that layers a job-run API, an optimized runtime, and native AWS service integration on top of the same underlying EKS infrastructure. The next part in this series turns to performance tuning and cost optimization that applies across all three submission models.

[Return to Main Page](./README.md)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/data-on-eks/spark/03-emr-on-eks-quiz.md).

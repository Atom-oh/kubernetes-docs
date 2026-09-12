# Amazon EMR on EKS Quiz

Based on the September 2026 reviewed guide.

## 1. What is a virtual cluster?

<details>
<summary>Show answer</summary>

A logical registration of an EKS namespace with EMR. It creates no compute capacity, but initial service-linked-role and CAM access-entry/policy setup can occur.

</details>

## 2. How do StartJobRun and EMR Spark Operator submission differ?

<details>
<summary>Show answer</summary>

StartJobRun is an AWS API targeting a virtual cluster. The separately installed operator receives SparkApplication CRs; it is not an internal delegation option of StartJobRun.

</details>

## 3. Does an operator-submitted CR automatically get an EMR job ID?

<details>
<summary>Show answer</summary>

Do not assume so. Observe CR status, logs and retries through the operator path, separately from the EMR job API lifecycle.

</details>

## 4. When did EMR Spark Operator support begin, and how is it installed?

<details>
<summary>Show answer</summary>

EMR 6.10.0+. Install the documented EMR chart and compatible runtime, then submit with kubectl apply. Do not treat it as the same distribution as Part 2's current upstream charts.

</details>

## 5. Which Apache Spark version is in emr-spark-8.0.0?

<details>
<summary>Show answer</summary>

4.0.2-amzn-0. This April 2026 release provides Spark 4.x GA; 8.0.0 names the EMR runtime release.

</details>

## 6. How do -latest and dated suffixes differ?

<details>
<summary>Show answer</summary>

-latest follows security updates for the release and does not pin identical image bytes. A dated suffix helps reproduce a release but still requires subsequent update review.

</details>

## 7. Which CreateVirtualCluster response value is used for subsequent jobs?

<details>
<summary>Show answer</summary>

The id field. Set StartJobRun's virtualClusterId to it and verify the registered namespace and RUNNING state.

</details>

## 8. Are execution-role data permissions the same as caller permissions?

<details>
<summary>Show answer</summary>

No. The execution role grants workload access to S3, KMS, logs and similar resources. The caller needs API and allowed-role permissions; review ExecutionRoleArn conditions and applicable PassRole permissions.

</details>

## 9. What does update-role-trust-policy do?

<details>
<summary>Show answer</summary>

For IRSA, it updates execution-role trust for the cluster OIDC provider, namespace and EMR-managed service-account identity. It does not automatically grant S3 or caller permissions.

</details>

## 10. Can StartJobRun use Pod Identity?

<details>
<summary>Show answer</summary>

Yes, from EMR 7.3.0. It needs the Agent, node EKS Auth permissions, trust for pods.eks.amazonaws.com and service-account associations. An IRSA annotation is not a substitute.

</details>

## 11. Which associations does create-role-associations prepare?

<details>
<summary>Show answer</summary>

Three associations between the execution role and the EMR submitter, driver and executor service accounts. Use the current CLI helper and clean up unused associations separately when their namespace/role is retired.

</details>

## 12. Does maxConcurrentJobRuns=2 set the namespace CPU ceiling?

<details>
<summary>Show answer</summary>

No. It limits job count; maxInQueueJobRuns limits queued jobs. CPU/memory quotas and per-job executor caps are separate.

</details>

## 13. Is a job finished when StartJobRun returns successfully?

<details>
<summary>Show answer</summary>

No. Inspect final state and logs using the accepted job ID. The smoke example checks both COMPLETED and SMOKE_OK rows=10 total=45.

</details>

## 14. Does reusing a clientToken guarantee exactly-once data output?

<details>
<summary>Show answer</summary>

It deduplicates the API request, not application retries or external side effects. Use a new token for a new intended run.

</details>

## 15. Can EMR pod templates or images be customized?

<details>
<summary>Show answer</summary>

Yes, through supported pod-template/custom-image paths. Respect release-specific restrictions and do not arbitrarily override StartJobRun-managed namespaces, service accounts or pod names.

</details>

## 16. Are CloudWatch and Step Functions integrations complete without configuration?

<details>
<summary>Show answer</summary>

No. Configure log monitoring and execution-role permissions, plus the state machine and its role. Service metrics also differ from complete Spark JVM telemetry.

</details>

## 17. How does EMR Studio run interactive workloads?

<details>
<summary>Show answer</summary>

A CreateManagedEndpoint endpoint uses Jupyter Enterprise Gateway to manage kernels. This differs from ordinary StartJobRun batch calls and needs private networking, ALB and role setup. Users/kernels of the same endpoint share its role.

</details>

## 18. Why is virtual-cluster deletion not complete cleanup?

<details>
<summary>Show answer</summary>

Inspect and clean up the intended jobs/endpoints first. EKS, namespaces, S3, logs, IAM roles and Pod Identity associations have separate lifecycles; also inspect deletion state and permission failures.

</details>

[Guide](../../../data-on-eks/spark/03-emr-on-eks.md)

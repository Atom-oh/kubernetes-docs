# MWAA Integration Quiz

Check management boundaries and EKS connectivity for provisioned MWAA 3.3.1/Python 3.12.

1. Can kubectl in the customer EKS cluster inspect the MWAA scheduler?

<details>
<summary>Show Answer</summary>

**Answer:** No. It uses AWS-managed Fargate infrastructure connected to private subnets in the customer VPC.

**Explanation:** This does not make MWAA unrelated to the VPC. Users still manage DAGs, IAM, networking, capacity choices and upgrades.

</details>

2. Which three boundaries must be checked when MWAA submits pods to EKS?

<details>
<summary>Show Answer</summary>

**Answer:** Network reachability, IAM-based EKS authentication and Kubernetes RBAC.

**Explanation:** A kubeconfig and in_cluster=False do not themselves provide endpoint connectivity or namespace permissions.

</details>

3. Does adding an aws-auth mapping grant access in EKS API authentication mode?

<details>
<summary>Show Answer</summary>

**Answer:** No. Use an access entry in this mode.

**Explanation:** Access entries also work in API_AND_CONFIG_MAP. Match the group to the real RoleBinding and inspect other grants.

</details>

4. Does MWAA prohibit installing Linux runtimes or system dependencies?

<details>
<summary>Show Answer</summary>

**Answer:** Supported runtime installation is possible through startup scripts.

**Explanation:** Official examples include sudo. Validate startup time, networking and version constraints; this is different from replacing the managed base image freely.

</details>

5. Does Git → CI → S3 → MWAA guarantee execution immediately after merging?

<details>
<summary>Show Answer</summary>

**Answer:** No. File synchronization and DAG parsing must finish.

**Explanation:** The documented S3 baseline does not by itself prove every Airflow bundle capability unavailable. Check support for separate configuration against the chosen release.

</details>

6. What latest Airflow release and MWAA availability date appear in the support table reviewed on 2026-09-12?

<details>
<summary>Show Answer</summary>

**Answer:** Airflow 3.3.1, available since 2026-09-01, with Python 3.12.

**Explanation:** Upstream 3.3.1 was released on 2026-08-12, so a fixed three-month lag is incorrect. Check existing environment versions separately.

</details>

7. Is MWAA only suitable for PyPI-only or low-importance pipelines?

<details>
<summary>Show Answer</summary>

**Answer:** No. It can run external EKS workload images; decide using operational, functional and recovery requirements.

**Explanation:** A KPO child image differs from MWAA's own runtime. Also distinguish provisioned MWAA from YAML-based MWAA Serverless.

</details>

8. Should a fixed 30–60% self-hosting saving be used for cost comparisons?

<details>
<summary>Show Answer</summary>

**Answer:** Not without evidence and equivalent conditions.

**Explanation:** Compare the same throughput/latency targets and include worker ranges, EKS, database, storage, NAT, logging and engineering effort.

</details>

9. How is the Kubernetes provider pinned for the chapter's 3.3.1/Python 3.12 environment?

<details>
<summary>Show Answer</summary>

**Answer:** Use matching Airflow/Python constraints and apache-airflow-providers-cncf-kubernetes==10.21.0.

**Explanation:** Inspect the base image first. After S3 upload, verify the environment's requirements object version and installation logs.

</details>

10. What must be checked before delivering a locally generated kubeconfig to MWAA?

<details>
<summary>Show Answer</summary>

**Answer:** Check the cluster, context, CA, exec.command and IAM credential selection, removing local AWS_PROFILE references.

**Explanation:** Do not embed static tokens or long-lived keys. Verify aws get-token execution and target endpoint access from MWAA.

</details>

11. Which binding connects a Kubernetes group to a Role only in data-processing?

<details>
<summary>Show Answer</summary>

**Answer:** Use a RoleBinding in that namespace.

**Explanation:** A ClusterRoleBinding does not express the namespace boundary. Other grants are additive; pod creation also raises service-account selection considerations.

</details>

12. If MWAA_EKS_OK never appears and the child pod has ImagePullBackOff, should the MWAA role's S3 permissions be expanded first?

<details>
<summary>Show Answer</summary>

**Answer:** No. Inspect the EKS node/Fargate image-pull identity, registry connectivity and image availability.

**Explanation:** The child does not automatically inherit the MWAA execution role. Configure actual workload data permissions separately.

</details>

---

[Return to Learning Materials](../../../data-on-eks/airflow/04-mwaa-integration.md)

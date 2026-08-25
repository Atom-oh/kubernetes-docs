# Kubeflow Architecture and Installation on EKS Quiz

This quiz tests your understanding of Kubeflow's component architecture, its CNCF graduation, the Kubeflow Community Distribution's release model, EKS-specific installation patterns, and the IAM access pattern for Pipelines artifact storage.

## Multiple Choice Questions

1. What milestone did Kubeflow reach with CNCF on August 17, 2026?
   - A) It was accepted as a CNCF sandbox project
   - B) It moved from sandbox to incubating status
   - C) It graduated — CNCF's highest maturity tier — after a security audit and forming a steering committee
   - D) It was archived by CNCF due to inactivity

<details>
<summary>Show Answer</summary>

**Answer: C) It graduated — CNCF's highest maturity tier — after a security audit and forming a steering committee**

**Explanation:**
Kubeflow entered CNCF as an incubating project in 2023 and [graduated on August 17, 2026](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/), after passing an independent third-party security audit and establishing a formal steering committee for project governance. Graduation is CNCF's highest maturity tier.
</details>

2. What versioning scheme does the Kubeflow Community Distribution use, and roughly how often does it ship a base release?
   - A) Semantic versioning (major.minor.patch), shipped continuously
   - B) Calendar versioning (YY.MM.patch), roughly twice a year
   - C) A single rolling "latest" tag with no discrete releases
   - D) LTS versioning, once every three years

<details>
<summary>Show Answer</summary>

**Answer: B) Calendar versioning (YY.MM.patch), roughly twice a year**

**Explanation:**
The Kubeflow Community Distribution uses calendar versioning in the form YY.MM.patch, with roughly two base releases per year. The 26.03 release is the latest base release at the time of writing (a 26.03.1 patch has since shipped with newer component versions).
</details>

3. In Kubeflow's architecture, what is a "Kubeflow Profile"?
   - A) A user's personal dashboard theme and layout preferences
   - B) A Kubernetes namespace plus RBAC bindings, resource quotas, and Istio AuthorizationPolicy objects, reconciled by the Profile Controller
   - C) A YAML file listing which components a cluster has installed
   - D) A billing construct used only by managed Kubeflow vendors

<details>
<summary>Show Answer</summary>

**Answer: B) A Kubernetes namespace plus RBAC bindings, resource quotas, and Istio AuthorizationPolicy objects, reconciled by the Profile Controller**

**Explanation:**
A Kubeflow Profile is the multi-tenancy boundary: a namespace bundled with RBAC bindings, quotas, and Istio authorization policy, all reconciled from a single Profile custom resource by the Profile Controller. Other components (Notebooks, Pipelines, Katib) create their resources inside a user's profile namespace.
</details>

4. Which three AWS-native services does `awslabs/kubeflow-manifests` substitute for Kubeflow's default Dex, in-cluster MySQL, and MinIO?
   - A) IAM, DynamoDB, and EFS
   - B) Cognito, RDS, and S3
   - C) Secrets Manager, Aurora Serverless, and EBS
   - D) SSO, Redshift, and Glacier

<details>
<summary>Show Answer</summary>

**Answer: B) Cognito, RDS, and S3**

**Explanation:**
`awslabs/kubeflow-manifests` replaces Dex with Amazon Cognito for authentication, the bundled in-cluster MySQL with Amazon RDS for Pipelines/Katib metadata, and MinIO with Amazon S3 for Pipelines artifact storage. Both a kustomize-based manifest deployment and a Terraform-based deployment document this pattern.
</details>

5. What is the documented history of IRSA support for granting Kubeflow Pipelines pods access to S3, specifically for KFPv2?
   - A) IRSA has always fully supported KFPv2 with no caveats
   - B) IRSA was never available on EKS for any Kubeflow Pipelines version
   - C) IRSA support historically lagged for KFPv2, with an IAM-user-based workaround documented in the interim, while EKS Pod Identity is the broader direction of travel for IAM-to-pod bindings
   - D) KFPv2 requires disabling IAM entirely and using anonymous S3 access

<details>
<summary>Show Answer</summary>

**Answer: C) IRSA support historically lagged for KFPv2, with an IAM-user-based workaround documented in the interim, while EKS Pod Identity is the broader direction of travel for IAM-to-pod bindings**

**Explanation:**
`kubeflow-manifests` guidance historically noted IRSA was supported for KFPv1 but not yet for KFPv2, recommending a dedicated IAM user with static credentials as an interim workaround. Separately, EKS Pod Identity has become the increasingly recommended default mechanism for new IAM-to-pod bindings on EKS generally — but the current state of KFPv2-specific Pod Identity support should be checked against live documentation rather than assumed.
</details>

6. According to the "why run this on EKS instead of a managed alternative" trade-off discussed in this document, which condition most strongly favors running Kubeflow on EKS rather than using a fully managed platform like SageMaker?
   - A) The team wants to avoid ever touching Kubernetes controllers or CRDs
   - B) The team already runs mixed workloads on EKS and wants ML to share the same node pools, autoscaling, and observability stack
   - C) The team has no existing Kubernetes operational experience
   - D) The team wants the absolute minimum operational overhead regardless of portability

<details>
<summary>Show Answer</summary>

**Answer: B) The team already runs mixed workloads on EKS and wants ML to share the same node pools, autoscaling, and observability stack**

**Explanation:**
Kubeflow on EKS is most justified when a team already operates other workloads on EKS and can avoid maintaining a second, parallel operational model for ML — along with needing portability/avoiding lock-in or fine-grained control over training/serving internals. Teams without existing Kubernetes capacity, or those prioritizing minimum operational overhead, are usually better served by a fully managed platform.
</details>

## Short Answer Questions

7. In one sentence, explain what CNCF graduation (announced August 17, 2026) signals about Kubeflow's project maturity, and name one concrete requirement the project had to meet to reach it.

<details>
<summary>Show Answer</summary>

**Answer:**
Graduation signals that a CNCF project has demonstrated production-grade maturity, broad adoption, and sound governance; to reach it, Kubeflow underwent an independent third-party security audit and formed a formal steering committee for project governance. See the [CNCF announcement](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/) for the full details.
</details>

8. Why does the `awslabs/kubeflow-manifests` deployment pattern replace the in-cluster MinIO artifact store and bundled Dex authentication with S3 and Cognito respectively, when deploying Kubeflow on EKS?

<details>
<summary>Show Answer</summary>

**Answer:**
Because EKS already has managed, durable, IAM-integrated equivalents for both — S3 for object storage and Cognito for identity — running the bundled in-cluster alternatives instead would mean operating extra stateful services that duplicate capabilities AWS already provides, without gaining anything Kubeflow specifically needs from the self-hosted versions.
</details>

---

[Return to Learning Materials](../../../ai-ml/kubeflow/01-architecture-installation.md) | [Next Quiz: Pipelines](./02-pipelines-quiz.md)

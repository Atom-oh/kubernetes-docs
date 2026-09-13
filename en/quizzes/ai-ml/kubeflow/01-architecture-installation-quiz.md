# Kubeflow Architecture and Installation on EKS Quiz

Baseline: Community Distribution 26.03.1 / Dashboard 2.0.0 / KFP 2.16.1.

## Multiple Choice Questions

1. What does Kubeflow’s August 17, 2026 CNCF graduation establish?

   - A) Automatic compliance of every EKS deployment
   - B) Project maturity and governance, including an independent security audit
   - C) No further security updates are needed
   - D) Guaranteed tenant isolation without configuration

<details>
<summary>Show Answer</summary>

**Answer: B) Project maturity and governance, including an independent security audit**

Graduation concerns the project. Deployment security, isolation and regulatory compliance still require their own assessment.
</details>

2. Which release baseline is used by this chapter?

   - A) AWS Kubeflow 1.7 and Community 26.03.1 are identical
   - B) Community 26.03.1, including KFP 2.16.1 and Dashboard 2.0.0
   - C) Every component uses version 26.03.1
   - D) The master branch without a release pin

<details>
<summary>Show Answer</summary>

**Answer: B) Community 26.03.1, including KFP 2.16.1 and Dashboard 2.0.0**

Distribution and component versions differ. The community calendar release plans roughly two base releases per year and describes support as best effort, not an SLA.
</details>

3. What happens when Profile resourceQuotaSpec.hard is omitted?

   - A) The controller sets a default GPU quota
   - B) Istio supplies an equivalent CPU quota
   - C) The Profile controller does not create its ResourceQuota
   - D) The namespace receives unlimited AWS IAM permissions

<details>
<summary>Show Answer</summary>

**Answer: C) The Profile controller does not create its ResourceQuota**

Quota is optional. Emptying hard removes the controller-managed quota. RBAC, network policy, storage and AWS access are separate boundaries.
</details>

4. What must be checked before following the old AWS distribution installation guide?

   - A) Only recent repository activity
   - B) Whether the dashboard logo changed
   - C) Whether the release is compatible and its required images remain available
   - D) Whether every component is a CRD

<details>
<summary>Show Answer</summary>

**Answer: C) Whether the release is compatible and its required images remain available**

The inspected v1.7.0-aws-b1.0.3 release explicitly warns that removed OIDC image availability breaks new installations. It is not a verified 26.03.1 recipe.
</details>

5. Which statement about current KFP S3 identity is supported?

   - A) KFPv2 universally requires a static IAM-user key
   - B) fromEnv accepts only static access keys
   - C) The current guide documents IRSA; actual SDK, ServiceAccount and role trust still need validation
   - D) A Profile automatically creates a Pod Identity association

<details>
<summary>Show Answer</summary>

**Answer: C) The current guide documents IRSA; actual SDK, ServiceAccount and role trust still need validation**

KFP 2.16.1 delegates fromEnv to Go Cloud, whose pinned default uses the AWS SDK v2 credential chain. This source inspection does not prove an EKS Pod Identity deployment.
</details>

6. Which role does the dashboard perform?

   - A) Automatically trains and deploys every model
   - B) Provides navigation to component interfaces
   - C) Replaces all application authorization
   - D) Stores every pipeline artifact in a CRD

<details>
<summary>Show Answer</summary>

**Answer: B) Provides navigation to component interfaces**

Workload controllers and application APIs perform their own operations. KFP APIs also use persistence; its Run and Experiment concepts are not universally CRDs.
</details>

## Short Answer Questions

7. Why preserve Profile objects and their CRD during the Dashboard v2 migration?

<details>
<summary>Show Answer</summary>

The Profile controller sets namespace ownership. Deleting a Profile can cascade to its namespace and resources. Follow the release-specific cleanup of old controller resources without deleting tenant Profiles or namespaces.
</details>

8. What does a successful Profile overlay render prove, and what remains unverified?

<details>
<summary>Show Answer</summary>

It proves that the selected Kustomize inputs generate manifests; the reviewed overlay produced 14 resources with Dashboard 2.0.0 images. It does not prove API admission, controller readiness, tenant isolation, or S3 access on EKS. Managed-service substitutions also need identity, compatibility, network, cost and migration checks.
</details>

---

[Return to Learning Materials](../../../ai-ml/kubeflow/01-architecture-installation.md) | [Next Quiz: Pipelines](02-pipelines-quiz.md)

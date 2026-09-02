# Unified Studio Domain and Project Governance Quiz

## Multiple Choice Questions

1. What is a project profile?
   - A) A GPU driver
   - B) A project template composed of blueprints
   - C) An MLflow run
   - D) An S3 object version

<details>
<summary>Show Answer</summary>

**Answer: B**

It defines the tools and capabilities available to projects created from it.
</details>

2. Is IAM permission for `DeleteProject` sufficient?
   - A) Yes
   - B) No, project owner/member authorization is also required
   - C) An EKS cluster is sufficient
   - D) An S3 tag is sufficient

<details>
<summary>Show Answer</summary>

**Answer: B**

IAM API permission and Unified Studio/DataZone membership are separate layers.
</details>

3. How should `All capabilities` be interpreted safely?
   - A) Every blueprint is ready in every Region
   - B) Verify profile enablement and blueprint/Region readiness
   - C) Every user may create projects
   - D) It provides strong isolation automatically

<details>
<summary>Show Answer</summary>

**Answer: B**

The name alone does not prove readiness or authorization.
</details>

4. What should happen when custom project tags are rejected?
   - A) Start the GPU Job
   - B) Correct the project request and reclaim existing resources
   - C) Copy every tag to the IAM role
   - D) Ignore remaining resources

<details>
<summary>Show Answer</summary>

**Answer: B**

Inventory-driven teardown handles the partially created App, S3, and IAM resources.
</details>

5. What proves project deletion is complete?
   - A) One successful delete response
   - B) Absence from `ListProjects` and a zero-resource inventory
   - C) A `GetProject` authorization error
   - D) A closed MLflow UI

<details>
<summary>Show Answer</summary>

**Answer: B**

An authorization error is not evidence that the project is absent.
</details>

---

[Return to learning materials](../../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md)

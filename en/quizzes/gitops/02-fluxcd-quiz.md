# FluxCD Quiz

This quiz tests your understanding of FluxCD and its components.

1. Which CNCF status does FluxCD hold?
   - A) Sandbox
   - B) Incubating
   - C) Graduated
   - D) Archived

<details>
<summary>Show Answer</summary>

**Answer: C) Graduated**

**Explanation:**
FluxCD graduated from the CNCF in November 2022, indicating it has reached maturity and is widely adopted in production environments.

</details>

2. Which FluxCD controller is responsible for fetching artifacts from Git repositories?
   - A) Kustomize Controller
   - B) Helm Controller
   - C) Source Controller
   - D) Notification Controller

<details>
<summary>Show Answer</summary>

**Answer: C) Source Controller**

**Explanation:**
The Source Controller is responsible for acquiring artifacts from external sources including Git repositories (GitRepository), Helm repositories (HelmRepository), OCI registries (OCIRepository), and S3 buckets (Bucket).

</details>

3. What CRD does FluxCD use to deploy Kustomize configurations?
   - A) Application
   - B) Kustomization
   - C) KustomizeConfig
   - D) Deployment

<details>
<summary>Show Answer</summary>

**Answer: B) Kustomization**

**Explanation:**
The Kustomization CRD is used to define how Kustomize overlays should be applied to the cluster. It references a source (GitRepository) and specifies the path to the Kustomize configuration.

</details>

4. How does FluxCD handle Helm chart deployments?
   - A) Using the Application CRD
   - B) Using the HelmRelease CRD
   - C) Using helm CLI directly
   - D) Helm is not supported

<details>
<summary>Show Answer</summary>

**Answer: B) Using the HelmRelease CRD**

**Explanation:**
The HelmRelease CRD is used to declaratively manage Helm chart releases. It specifies the chart source, version, values, and upgrade/rollback policies.

</details>

5. What is the purpose of FluxCD's ImageUpdateAutomation?
   - A) To scan images for vulnerabilities
   - B) To automatically update image tags in Git when new versions are detected
   - C) To build container images
   - D) To manage image pull secrets

<details>
<summary>Show Answer</summary>

**Answer: B) To automatically update image tags in Git when new versions are detected**

**Explanation:**
ImageUpdateAutomation works with ImageRepository and ImagePolicy to detect new container image tags and automatically commit updates to the Git repository, enabling automated deployments.

</details>

6. Which command is used to bootstrap FluxCD on a cluster?
   - A) flux install
   - B) flux bootstrap
   - C) flux init
   - D) flux setup

<details>
<summary>Show Answer</summary>

**Answer: B) flux bootstrap**

**Explanation:**
The `flux bootstrap` command installs FluxCD components and configures the Git repository to manage the cluster. It supports various Git providers like GitHub, GitLab, and generic Git servers.

</details>

7. How does FluxCD support multi-tenancy?
   - A) Using Projects like ArgoCD
   - B) Using namespace isolation and Kubernetes RBAC
   - C) Multi-tenancy is not supported
   - D) Using a central admin tenant

<details>
<summary>Show Answer</summary>

**Answer: B) Using namespace isolation and Kubernetes RBAC**

**Explanation:**
FluxCD supports multi-tenancy through namespace isolation, where each tenant has their own namespace with Flux resources, combined with Kubernetes native RBAC for access control.

</details>

8. What is the purpose of the Notification Controller in FluxCD?
   - A) To send SMS messages
   - B) To handle events and send alerts to external services
   - C) To manage Git webhooks only
   - D) To monitor pod logs

<details>
<summary>Show Answer</summary>

**Answer: B) To handle events and send alerts to external services**

**Explanation:**
The Notification Controller handles both outbound notifications (Alerts to Slack, Teams, etc.) and inbound webhooks (Receivers) that trigger reconciliation when external events occur.

</details>

# Harbor Quiz
> **Last Updated**: February 25, 2025

1. What is Harbor's status within the Cloud Native Computing Foundation (CNCF)?
   - A) Sandbox project
   - B) Incubating project
   - C) Graduated project
   - D) Archived project

<details>
<summary>Show Answer</summary>

**Answer: C) Graduated project**

**Explanation:**
Harbor is a CNCF Graduated project, which is the highest maturity level in the CNCF. This status indicates that Harbor has demonstrated thriving adoption, an open governance process, and a strong commitment to community sustainability and security. Harbor graduated in 2020.

</details>

2. Which component is Harbor's default vulnerability scanner?
   - A) Clair
   - B) Trivy
   - C) Anchore
   - D) Snyk

<details>
<summary>Show Answer</summary>

**Answer: B) Trivy**

**Explanation:**
Starting with Harbor 2.2, Trivy replaced Clair as the default vulnerability scanner. Trivy is an open-source scanner from Aqua Security that provides comprehensive vulnerability detection for container images, including OS packages and application dependencies. Harbor still supports pluggable scanners if you prefer alternatives.

</details>

3. What is the recommended method for installing Harbor in a Kubernetes environment?
   - A) Docker Compose
   - B) Manual YAML manifests
   - C) Helm chart
   - D) Operator pattern

<details>
<summary>Show Answer</summary>

**Answer: C) Helm chart**

**Explanation:**
The official Harbor Helm chart is the recommended installation method for Kubernetes environments. It handles all the complex dependencies (database, Redis, storage) and provides extensive configuration options. Docker Compose is suitable for non-Kubernetes deployments or quick testing but is not recommended for production Kubernetes deployments.

</details>

4. In Harbor's RBAC model, what permissions does a Project Maintainer have compared to a Developer?
   - A) Maintainer can push images; Developer cannot
   - B) Maintainer can manage project members and configurations; Developer can only push/pull images
   - C) Maintainer and Developer have identical permissions
   - D) Developer has more permissions than Maintainer

<details>
<summary>Show Answer</summary>

**Answer: B) Maintainer can manage project members and configurations; Developer can only push/pull images**

**Explanation:**
Harbor's project-level RBAC defines several roles: Project Admin, Maintainer, Developer, and Guest. Maintainers can manage project configurations, labels, and replication rules but cannot manage members. Developers can push and pull images but cannot modify project settings. Project Admins have full control including member management.

</details>

5. What are Harbor robot accounts used for?
   - A) Automated administrative tasks
   - B) Providing non-human service accounts with limited, scoped credentials for CI/CD systems
   - C) Managing Harbor's internal components
   - D) Replicating images between Harbor instances

<details>
<summary>Show Answer</summary>

**Answer: B) Providing non-human service accounts with limited, scoped credentials for CI/CD systems**

**Explanation:**
Robot accounts provide system-to-system authentication for automated workflows like CI/CD pipelines. They have configurable expiration, scoped permissions (push/pull per repository or project), and don't require human user credentials. This follows security best practices by avoiding shared credentials and enabling credential rotation.

</details>

6. What is the difference between Harbor's push-based and pull-based replication modes?
   - A) Push-based is faster; pull-based is more reliable
   - B) Push-based sends images to remote registries; pull-based fetches from remote registries
   - C) Push-based requires manual triggers; pull-based is automatic
   - D) There is no difference; they are aliases

<details>
<summary>Show Answer</summary>

**Answer: B) Push-based sends images to remote registries; pull-based fetches from remote registries**

**Explanation:**
Push-based replication proactively sends images from Harbor to remote registries (useful for distributing images to edge locations). Pull-based replication fetches images from remote registries into Harbor (useful for mirroring external registries or disaster recovery). Both can be triggered manually, on schedule, or by events.

</details>

7. Which tool does Harbor integrate with for image signing and verification?
   - A) GPG
   - B) Notary (with Cosign support)
   - C) OpenSSL
   - D) HashiCorp Vault

<details>
<summary>Show Answer</summary>

**Answer: B) Notary (with Cosign support)**

**Explanation:**
Harbor historically integrated with Notary for image signing using Docker Content Trust. Modern Harbor versions also support Cosign (from the Sigstore project) for keyless signing and verification. Cosign has become the preferred approach due to its simpler workflow and integration with transparency logs for supply chain security.

</details>

8. What is Harbor's proxy cache feature used for?
   - A) Caching DNS queries
   - B) Acting as a pull-through cache for remote registries like Docker Hub
   - C) Caching Helm chart dependencies
   - D) Accelerating internal Harbor operations

<details>
<summary>Show Answer</summary>

**Answer: B) Acting as a pull-through cache for remote registries like Docker Hub**

**Explanation:**
Harbor's proxy cache creates a caching proxy for external registries. When users pull images through Harbor, the images are cached locally. Subsequent pulls for the same image are served from Harbor's cache, reducing external bandwidth usage, improving pull performance, and avoiding rate limits from upstream registries like Docker Hub.

</details>

9. When deploying Harbor in an air-gapped environment, which component requires special consideration for vulnerability database updates?
   - A) The Harbor core service
   - B) The database (PostgreSQL)
   - C) The vulnerability scanner (Trivy)
   - D) The Redis cache

<details>
<summary>Show Answer</summary>

**Answer: C) The vulnerability scanner (Trivy)**

**Explanation:**
In air-gapped environments, Trivy cannot download vulnerability database updates from the internet. You must manually download the Trivy database on a connected machine, transfer it to the air-gapped environment, and configure Trivy to use the offline database. Without this, vulnerability scanning will use stale data or fail entirely.

</details>

10. What triggers Harbor's garbage collection process?
    - A) It runs automatically every hour
    - B) It must be manually triggered or scheduled through the Harbor UI/API
    - C) It runs after every image deletion
    - D) It runs when storage reaches 80% capacity

<details>
<summary>Show Answer</summary>

**Answer: B) It must be manually triggered or scheduled through the Harbor UI/API**

**Explanation:**
Harbor's garbage collection (GC) is not automatic. It must be triggered manually through the Harbor admin UI or API, or configured as a scheduled job. GC removes image layers (blobs) that are no longer referenced by any manifest. Running GC reclaims storage but should be scheduled during low-activity periods as it can impact registry performance.

</details>

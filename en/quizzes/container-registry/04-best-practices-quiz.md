# Container Registry Best Practices Quiz
> **Last Updated**: February 25, 2026

1. Why is tag immutability considered a best practice for container registries?
   - A) It reduces storage costs
   - B) It ensures a tag always refers to the same image content, providing deployment reproducibility
   - C) It speeds up image pulls
   - D) It is required by Kubernetes

<details>
<summary>Show Answer</summary>

**Answer: B) It ensures a tag always refers to the same image content, providing deployment reproducibility**

**Explanation:**
Tag immutability guarantees that once an image is pushed with a specific tag, that tag cannot be overwritten with a different image. This ensures deployment reproducibility (the same tag always deploys the same code), enables reliable rollbacks, and prevents accidental or malicious image replacement. It's a fundamental supply chain security practice.

</details>

2. What is the primary risk of using the `:latest` tag in production Kubernetes deployments?
   - A) The image will not be cached
   - B) Kubernetes cannot pull images with the latest tag
   - C) The actual image content is unpredictable and may change between deployments
   - D) Latest tags are deprecated

<details>
<summary>Show Answer</summary>

**Answer: C) The actual image content is unpredictable and may change between deployments**

**Explanation:**
The `:latest` tag is mutable and typically points to the most recently pushed image. Using it in production means you cannot guarantee which version of the code is running, rollbacks become unreliable, and debugging is difficult since you don't know what code was deployed. Best practice is to use semantic versioning or Git SHA-based tags.

</details>

3. What is the primary benefit of configuring a registry mirror or pull-through cache?
   - A) It improves image build times
   - B) It reduces external network traffic, improves pull latency, and mitigates rate limiting
   - C) It automatically updates images
   - D) It provides vulnerability scanning

<details>
<summary>Show Answer</summary>

**Answer: B) It reduces external network traffic, improves pull latency, and mitigates rate limiting**

**Explanation:**
Registry mirrors and pull-through caches store copies of external images locally. Benefits include: reduced bandwidth costs and external dependencies, faster pull times from local network, avoidance of rate limits (like Docker Hub's limits), and improved reliability when external registries are unavailable. They're essential for large clusters and air-gapped environments.

</details>

4. In a multi-region Kubernetes deployment, what is the recommended disaster recovery strategy for container registries?
   - A) Use a single global registry
   - B) Replicate images to registries in each region and update deployments to use region-local registries
   - C) Store all images in S3 and pull directly
   - D) Use image caching on each node

<details>
<summary>Show Answer</summary>

**Answer: B) Replicate images to registries in each region and update deployments to use region-local registries**

**Explanation:**
For DR and high availability, images should be replicated to registries in each deployment region. This ensures that a regional registry outage doesn't prevent deployments in other regions, reduces cross-region network latency for pulls, and provides independence from external registry availability. Deployments should reference the region-local registry endpoint.

</details>

5. Which approach helps optimize container registry storage costs?
   - A) Disable image scanning
   - B) Implement lifecycle policies to automatically delete old and unused images
   - C) Use larger base images
   - D) Store images uncompressed

<details>
<summary>Show Answer</summary>

**Answer: B) Implement lifecycle policies to automatically delete old and unused images**

**Explanation:**
Lifecycle policies automate cleanup of images based on age, count, or tag patterns. This prevents unbounded storage growth from development iterations, old releases, and abandoned experiments. Combine with multi-stage builds and minimal base images to reduce per-image size. Regular garbage collection reclaims space from deleted image layers.

</details>

6. At what stage in the CI/CD pipeline should container image vulnerability scanning occur?
   - A) Only in production
   - B) As early as possible, ideally during the build stage before pushing to the registry
   - C) Only during manual security audits
   - D) After deployment to Kubernetes

<details>
<summary>Show Answer</summary>

**Answer: B) As early as possible, ideally during the build stage before pushing to the registry**

**Explanation:**
Shift-left security means scanning images during the CI build phase, before they're pushed to the registry. This catches vulnerabilities early when they're cheapest to fix, prevents vulnerable images from ever entering the registry, and provides fast feedback to developers. Additional scanning should occur in the registry and at admission time for defense in depth.

</details>

7. How can Kubernetes admission controllers enhance container registry security?
   - A) By speeding up image pulls
   - B) By validating that images come from allowed registries and meet security requirements before Pod creation
   - C) By automatically updating images
   - D) By compressing images

<details>
<summary>Show Answer</summary>

**Answer: B) By validating that images come from allowed registries and meet security requirements before Pod creation**

**Explanation:**
Admission controllers like Gatekeeper/OPA, Kyverno, or cloud-provider solutions can enforce policies at deployment time: requiring images from approved registries, verifying image signatures, checking that images have passed vulnerability scans, and blocking images with specific tags like `:latest`. This provides a final security gate before workloads run.

</details>

8. What is a recommended naming convention for container image tags?
   - A) Random UUIDs
   - B) Semantic version (v1.2.3) or Git commit SHA, optionally with build metadata
   - C) Timestamps only
   - D) Developer initials

<details>
<summary>Show Answer</summary>

**Answer: B) Semantic version (v1.2.3) or Git commit SHA, optionally with build metadata**

**Explanation:**
Good tag naming enables traceability from deployed image to source code. Semantic versions (v1.2.3) communicate release significance. Git SHAs provide exact commit traceability. Combining them (v1.2.3-abc1234) or adding build numbers (v1.2.3-build.456) provides comprehensive lineage. This supports debugging, auditing, and rollback decisions.

</details>

9. What distinguishes a pull-through cache from a full registry mirror?
   - A) A pull-through cache stores all images proactively; a mirror fetches on demand
   - B) A pull-through cache fetches and caches images on demand; a mirror proactively syncs all images
   - C) They are identical concepts
   - D) Pull-through caches only work with Docker Hub

<details>
<summary>Show Answer</summary>

**Answer: B) A pull-through cache fetches and caches images on demand; a mirror proactively syncs all images**

**Explanation:**
A pull-through cache only stores images after they're first requested, caching them for subsequent pulls. A full mirror proactively replicates all (or selected) images from the source registry regardless of whether they're needed. Pull-through caches use less storage but have a cold-start latency; mirrors ensure all images are immediately available locally.

</details>

10. In a multi-registry strategy, when should an organization consider using multiple container registries?
    - A) Never; one registry is always sufficient
    - B) When different security, compliance, geographic, or operational requirements exist for different image categories
    - C) Only when costs are too high
    - D) Only for backup purposes

<details>
<summary>Show Answer</summary>

**Answer: B) When different security, compliance, geographic, or operational requirements exist for different image categories**

**Explanation:**
Multiple registries are justified when: separating public and private images, meeting compliance requirements (e.g., regulated data in specific regions), optimizing latency for global deployments, isolating production from development images, or using specialized registries for different purposes (e.g., ECR for AWS workloads, Harbor for on-premises). The trade-off is increased operational complexity.

</details>

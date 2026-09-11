# Amazon ECR Quiz
> **Last Updated**: September 11, 2026

1. What is the primary difference between Amazon ECR Private and Amazon ECR Public?
   - A) ECR Private is free, ECR Public is paid
   - B) ECR Private requires authentication for all operations, ECR Public allows anonymous pulls
   - C) ECR Private only supports Docker images, ECR Public supports all formats
   - D) ECR Private is regional, ECR Public is only available in us-east-1

<details>
<summary>Show Answer</summary>

**Answer: B) ECR Private requires authentication for all operations, ECR Public allows anonymous pulls**

**Explanation:**
Private push/pull operations require authentication. Public images allow anonymous pulls, while publishing and management require authentication. Public API endpoints are listed for us-east-1 and us-west-2 and images are distributed through global URLs.

</details>

2. Which CLI command emits the ECR password directly for use with `docker login --password-stdin`?
   - A) `aws ecr get-authorization-token`
   - B) `aws ecr get-login-password`
   - C) `aws ecr login`
   - D) `aws ecr authenticate`

<details>
<summary>Show Answer</summary>

**Answer: B) `aws ecr get-login-password`**

**Explanation:**
`get-login-password` prints the password suitable for stdin. `get-authorization-token` is also a valid API/CLI operation, but returns an encoded authorization token requiring decoding.

</details>

3. In ECR lifecycle policies, what determines which rule is applied when multiple rules match the same image?
   - A) The rule with the lowest `rulePriority` number wins
   - B) The rule with the highest `rulePriority` number wins
   - C) Rules are applied in alphabetical order
   - D) All matching rules are applied simultaneously

<details>
<summary>Show Answer</summary>

**Answer: A) The rule with the lowest `rulePriority` number wins**

**Explanation:**
All rules are evaluated first, then their results are applied by priority. Lower numbers have higher priority; an image matching a higher-priority rule's tagging requirements cannot be expired by a lower-priority rule. This is not an ordered short-circuit evaluation of the rules themselves.

</details>

4. Which pattern syntax does ECR lifecycle policy `tagPatternList` use?
   - A) Regular expressions (regex)
   - B) The documented `*` wildcard pattern
   - C) SQL LIKE patterns
   - D) Exact string matching only

<details>
<summary>Show Answer</summary>

**Answer: B) The documented `*` wildcard pattern**

**Explanation:**
Use the documented `*` wildcard, with at most four stars per string. Do not assume regex, character classes or full Unix glob behavior. `v*` selects a prefix; CI must validate the release version format.

</details>

5. What is a key limitation of ECR lifecycle policies regarding rule logic?
   - A) Cannot have more than 5 rules
   - B) Cannot express OR/union logic across tag patterns in a single rule
   - C) Cannot delete untagged images
   - D) Cannot use countType with imageCountMoreThan

<details>
<summary>Show Answer</summary>

**Answer: B) Cannot express OR/union logic across tag patterns in a single rule**

**Explanation:**
A single ECR lifecycle rule with multiple patterns in `tagPatternList` applies AND logic (image must match all patterns). To achieve OR logic (match any pattern), you must create separate rules for each pattern. This limitation requires careful rule design when you want to apply the same retention policy to images matching different tag patterns.

</details>

6. In the Strategy A (separate repositories per environment) approach for ECR, what is a primary advantage?
   - A) Simpler lifecycle policies since each repo has uniform retention needs
   - B) Lower storage costs
   - C) Faster image pulls
   - D) Automatic cross-region replication

<details>
<summary>Show Answer</summary>

**Answer: A) Simpler lifecycle policies since each repo has uniform retention needs**

**Explanation:**
Strategy A uses separate repositories per environment (e.g., `myapp-dev`, `myapp-prod`). This simplifies lifecycle policies because each repository contains images with uniform retention requirements. The trade-off is managing multiple repositories and potentially duplicating images across repositories.

</details>

7. Which Terraform resource is used to define ECR lifecycle policies?
   - A) `aws_ecr_repository`
   - B) `aws_ecr_lifecycle_policy`
   - C) `aws_ecr_repository_policy`
   - D) `aws_ecr_retention_policy`

<details>
<summary>Show Answer</summary>

**Answer: B) `aws_ecr_lifecycle_policy`**

**Explanation:**
The `aws_ecr_lifecycle_policy` Terraform resource attaches a lifecycle policy to an ECR repository. It requires the `repository` name and a `policy` JSON document defining the lifecycle rules. Note that `aws_ecr_repository_policy` is different and is used for IAM resource-based policies controlling access to the repository.

</details>

8. Which identity normally supplies initial ECR image-pull permissions on EC2-backed EKS nodes?
   - A) Using a static access key stored in a Secret
   - B) The kubelet directly uses the node's IAM role
   - C) Pods assume an IAM role via OIDC federation and use temporary credentials
   - D) ECR tokens are pre-provisioned in ConfigMaps

<details>
<summary>Show Answer</summary>

**Answer: B) The kubelet directly uses the node's IAM role**

**Explanation:**
Kubelet pulls the image before the application starts, using the node's image-pull credentials. Fargate uses its Pod execution role. IRSA/Pod Identity supply workload SDK credentials after the Pod starts; they do not replace that bootstrap image-pull identity.

</details>

9. What does enabling immutable tags on an ECR repository prevent?
   - A) Deleting any images from the repository
   - B) Pushing new images with the same tag as an existing image
   - C) Pulling images without authentication
   - D) Creating lifecycle policies

<details>
<summary>Show Answer</summary>

**Answer: B) Pushing new images with the same tag as an existing image**

**Explanation:**
Immutable tags prevent overwriting existing image tags. Once an image is pushed with a specific tag, that tag cannot be reused for a different image digest. This ensures tag stability for deployments and prevents accidental or malicious image replacement. Images can still be deleted, and new unique tags can still be pushed.

</details>

10. Which description of ECR cross-region replication is correct?
    - A) Only image manifests
    - B) Eligible images and tags are replicated asynchronously; destination settings are managed separately
    - C) Everything including lifecycle policies and permissions
    - D) All pre-existing images are automatically backfilled

<details>
<summary>Show Answer</summary>

**Answer: B) Eligible images and tags are replicated asynchronously; destination settings are managed separately**

**Explanation:**
Images pushed or restored after replication configuration are eligible. Existing content is not automatically backfilled. Destination repository settings, permissions and lifecycle policies are configured independently, for example using creation templates. Verify the required destination digest before relying on replication for recovery.

</details>

# Amazon ECR Quiz
> **Last Updated**: February 25, 2025

1. What is the primary difference between Amazon ECR Private and Amazon ECR Public?
   - A) ECR Private is free, ECR Public is paid
   - B) ECR Private requires authentication for all operations, ECR Public allows anonymous pulls
   - C) ECR Private only supports Docker images, ECR Public supports all formats
   - D) ECR Private is regional, ECR Public is only available in us-east-1

<details>
<summary>Show Answer</summary>

**Answer: B) ECR Private requires authentication for all operations, ECR Public allows anonymous pulls**

**Explanation:**
Amazon ECR Private requires AWS authentication for all push and pull operations, making it suitable for proprietary images. ECR Public (public.ecr.aws) allows anonymous pulls for publicly shared images while still requiring authentication to push. ECR Public is hosted in us-east-1 but serves content globally.

</details>

2. Which command retrieves an authentication token for Amazon ECR?
   - A) `aws ecr get-authorization-token`
   - B) `aws ecr get-login-password`
   - C) `aws ecr login`
   - D) `aws ecr authenticate`

<details>
<summary>Show Answer</summary>

**Answer: B) `aws ecr get-login-password`**

**Explanation:**
The `aws ecr get-login-password` command retrieves a temporary authentication token that can be piped to `docker login`. The full command is typically: `aws ecr get-login-password --region REGION | docker login --username AWS --password-stdin ACCOUNT.dkr.ecr.REGION.amazonaws.com`. The older `get-authorization-token` returns a base64-encoded token requiring additional processing.

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
ECR lifecycle policy rules are evaluated by `rulePriority`, where lower numbers have higher priority. When multiple rules could match the same image, only the rule with the lowest priority number is applied. This allows you to create exception rules (low priority number) that protect specific images from more general cleanup rules (higher priority numbers).

</details>

4. Which pattern syntax does ECR lifecycle policy `tagPatternList` use?
   - A) Regular expressions (regex)
   - B) Glob patterns with wildcards (* and ?)
   - C) SQL LIKE patterns
   - D) Exact string matching only

<details>
<summary>Show Answer</summary>

**Answer: B) Glob patterns with wildcards (* and ?)**

**Explanation:**
ECR lifecycle policy `tagPatternList` uses glob-style pattern matching, not regex. The `*` matches any sequence of characters and `?` matches any single character. For example, `prod-*` matches `prod-v1`, `prod-release`, etc. This is a common source of confusion since many other AWS services use regex.

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

8. How does EKS authenticate to ECR when using IAM Roles for Service Accounts (IRSA)?
   - A) Using a static access key stored in a Secret
   - B) The kubelet directly uses the node's IAM role
   - C) Pods assume an IAM role via OIDC federation and use temporary credentials
   - D) ECR tokens are pre-provisioned in ConfigMaps

<details>
<summary>Show Answer</summary>

**Answer: C) Pods assume an IAM role via OIDC federation and use temporary credentials**

**Explanation:**
With IRSA, Pods are associated with a Kubernetes ServiceAccount that is linked to an IAM role via OIDC federation. When a Pod needs to pull from ECR, it assumes the IAM role and receives temporary credentials. This provides fine-grained access control without storing long-term credentials and follows the principle of least privilege.

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

10. When configuring ECR cross-region replication, what is replicated to the destination region?
    - A) Only image manifests
    - B) Images, tags, and repository settings (but not lifecycle policies)
    - C) Everything including lifecycle policies and permissions
    - D) Only images pushed after replication is enabled

<details>
<summary>Show Answer</summary>

**Answer: B) Images, tags, and repository settings (but not lifecycle policies)**

**Explanation:**
ECR cross-region replication copies images and their tags to destination regions, and repositories are created automatically if they don't exist. However, lifecycle policies and repository permissions (resource-based policies) are NOT replicated and must be configured separately in each region. Replication applies to images pushed after the rule is created; existing images can be replicated by re-pushing them.

</details>

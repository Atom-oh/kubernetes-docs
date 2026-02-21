# Infrastructure Setup Quiz

> **Related Document**: [Infrastructure Setup](../../ops/01-infrastructure-setup.md)

## Multiple Choice Questions

### 1. What is the primary purpose of the Terraform 3-Layer architecture?

- A) To reduce the number of Terraform files
- B) To separate infrastructure by lifecycle and blast radius
- C) To enable faster deployment times
- D) To eliminate the need for state management

<details>
<summary>Show Answer</summary>

**Answer: B) To separate infrastructure by lifecycle and blast radius**

**Explanation:**
The 3-Layer architecture separates infrastructure into Foundation (VPC, IAM), Platform (EKS cluster), and Workload (applications) layers. Each layer has different change frequencies and blast radii, allowing safer and more manageable infrastructure changes.

</details>

### 2. In Terraform S3 backend configuration, what is the purpose of the DynamoDB table?

- A) To store Terraform state files
- B) To provide state locking and consistency
- C) To backup Terraform configurations
- D) To log Terraform operations

<details>
<summary>Show Answer</summary>

**Answer: B) To provide state locking and consistency**

**Explanation:**
The DynamoDB table enables state locking to prevent concurrent modifications to the same state file. This prevents race conditions when multiple users or CI/CD pipelines attempt to modify infrastructure simultaneously.

</details>

### 3. What does `terraform_remote_state` data source allow you to do?

- A) Store state files in a remote location
- B) Reference outputs from another Terraform state
- C) Migrate state between backends
- D) Encrypt state files automatically

<details>
<summary>Show Answer</summary>

**Answer: B) Reference outputs from another Terraform state**

**Explanation:**
The `terraform_remote_state` data source allows one Terraform configuration to read output values from another state file. This enables cross-layer references, such as the Platform layer reading VPC ID from the Foundation layer.

</details>

### 4. Which VPC CIDR block size is recommended for production EKS clusters?

- A) /24 (256 addresses)
- B) /20 (4,096 addresses)
- C) /16 (65,536 addresses)
- D) /8 (16 million addresses)

<details>
<summary>Show Answer</summary>

**Answer: C) /16 (65,536 addresses)**

**Explanation:**
A /16 CIDR block provides 65,536 IP addresses, which is recommended for production EKS clusters. This accommodates pod IP allocation (especially with VPC CNI), future growth, and multi-AZ deployments without IP exhaustion concerns.

</details>

### 5. What is the key characteristic of EKS Auto Mode compared to Managed Node Groups?

- A) Auto Mode requires manual node provisioning
- B) Auto Mode automatically manages node lifecycle and scaling
- C) Auto Mode only supports Spot instances
- D) Auto Mode eliminates the need for pods

<details>
<summary>Show Answer</summary>

**Answer: B) Auto Mode automatically manages node lifecycle and scaling**

**Explanation:**
EKS Auto Mode automatically handles node provisioning, scaling, and lifecycle management based on workload demands. Unlike Managed Node Groups, operators don't need to configure Auto Scaling Groups or manage node updates manually.

</details>

### 6. How does Pod Identity differ from IRSA (IAM Roles for Service Accounts)?

- A) Pod Identity doesn't support IAM roles
- B) Pod Identity uses EKS-managed credentials without OIDC provider setup
- C) Pod Identity requires manual token rotation
- D) Pod Identity only works with Fargate

<details>
<summary>Show Answer</summary>

**Answer: B) Pod Identity uses EKS-managed credentials without OIDC provider setup**

**Explanation:**
Pod Identity simplifies IAM integration by eliminating the need to configure an OIDC provider. AWS manages the credential injection through the Pod Identity Agent, making it easier to set up and maintain compared to IRSA.

</details>

### 7. In the 3-Layer architecture, which layer contains the EKS cluster resource?

- A) Foundation Layer
- B) Platform Layer
- C) Workload Layer
- D) Network Layer

<details>
<summary>Show Answer</summary>

**Answer: B) Platform Layer**

**Explanation:**
The Platform Layer contains the EKS cluster, node groups, and cluster add-ons. It depends on the Foundation Layer (VPC, subnets) and provides the platform for the Workload Layer (applications, services).

</details>

### 8. What should be enabled on S3 buckets storing Terraform state?

- A) Public access
- B) Versioning and encryption
- C) Static website hosting
- D) Cross-region replication only

<details>
<summary>Show Answer</summary>

**Answer: B) Versioning and encryption**

**Explanation:**
Terraform state files contain sensitive information and should be protected with versioning (to recover from corruption or accidental changes) and encryption (to protect secrets at rest). Public access should always be blocked.

</details>

### 9. When using Terraform workspaces for multi-environment management, what is a key limitation?

- A) Workspaces cannot use variables
- B) All environments share the same backend configuration
- C) Workspaces don't support modules
- D) Only two workspaces are allowed

<details>
<summary>Show Answer</summary>

**Answer: B) All environments share the same backend configuration**

**Explanation:**
Terraform workspaces share the same backend configuration and code, which can lead to accidental changes to production when working on development. Many teams prefer separate directories or repositories per environment for stronger isolation.

</details>

### 10. What is the recommended approach for managing Terraform provider versions?

- A) Always use the latest version without constraints
- B) Use exact version constraints in required_providers block
- C) Let Terraform auto-update providers
- D) Avoid specifying provider versions

<details>
<summary>Show Answer</summary>

**Answer: B) Use exact version constraints in required_providers block**

**Explanation:**
Specifying exact or pessimistic version constraints (e.g., `~> 5.0`) in the `required_providers` block ensures reproducible deployments and prevents unexpected breaking changes from provider updates. This is especially important in production environments.

</details>

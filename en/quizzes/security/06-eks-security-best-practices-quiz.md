# EKS Security Best Practices Quiz

> **Last Updated**: September 13, 2026

Test your understanding of Amazon EKS security best practices with the following questions.

***

## Questions

<span id="_1-what-authentication-method-does-a-pod-use-when-calling-aws-apis-with-irsa-iam-roles-for-service-accounts"></span>

### 1. How does a Pod obtain temporary AWS credentials through IRSA?

* A) IAM User Access Key
* B) EC2 Instance Profile
* C) OIDC token-based AssumeRoleWithWebIdentity
* D) Credentials stored in Kubernetes Secret

<details>

<summary>Show Answer</summary>

**Answer: C) OIDC token-based AssumeRoleWithWebIdentity**

**Explanation:** The Kubernetes API server issues the projected ServiceAccount JWT. A supported SDK exchanges it with STS AssumeRoleWithWebIdentity; STS checks the trusted issuer/JWKS, audience and subject and returns temporary AWS credentials. The IAM OIDC provider object is not the token issuer, and the JWT is not directly substituted for AWS API credentials.

</details>

***

### 2. What is the main advantage of EKS Pod Identity compared to IRSA?

* A) Stronger encryption
* B) Faster performance
* C) No OIDC Provider setup required, simplified management
* D) Support for more AWS services

<details>

<summary>Show Answer</summary>

**Answer: C) No OIDC Provider setup required, simplified management**

**Explanation:** Pod Identity avoids per-cluster IAM OIDC-provider setup and uses an association, supported agent/SDK and EKS Auth. Roles still require trust and least-privilege permissions. Auto Mode includes the agent; other platforms and cross-account/chained roles have specific requirements. It does not retire IRSA or automatically strengthen every application's security.

</details>

***

<span id="_3-which-is-not-a-requirement-for-using-security-groups-for-pods"></span>

### 3. Which is NOT required for the EC2-backed Security Groups for Pods path?

* A) Supported trunking-compatible EC2 instance types
* B) Amazon VPC CNI plugin
* C) Fargate profile
* D) SecurityGroupPolicy configuration

<details>

<summary>Show Answer</summary>

**Answer: C) Fargate profile**

**Explanation:** For the EC2-backed path, use a trunking-compatible supported instance type, compatible Amazon VPC CNI and SecurityGroupPolicy. Not every Nitro instance qualifies. The VPC Resource Controller policy belongs to the cluster role. Fargate has a separate supported model; Windows and Auto Mode are excluded by current Pod-SG documentation. ENIConfig is not a substitute for SecurityGroupPolicy.

</details>

***

### 4. What is the impact of setting the EKS cluster's Kubernetes API server endpoint to private only?

* A) Cannot use kubectl at all
* B) Accessible only from within VPC or connected networks
* C) Cannot manage cluster from AWS Console
* D) Worker nodes cannot connect to API server

<details>

<summary>Show Answer</summary>

**Answer: B) Accessible only from within VPC or connected networks**

**Explanation:** Private API reachability needs a connected network, DNS, routes and security groups plus IAM authentication/Kubernetes authorization. Test operator, CI and recovery access before removing public access. An EKS management PrivateLink endpoint does not replace the private Kubernetes API endpoint.

</details>

***

### 5. Which threat type is NOT detected by AWS GuardDuty EKS Protection?

* A) Communication with malicious IPs
* B) Cryptocurrency mining activity
* C) Pod resource usage exceeding limits
* D) Tor network connections

<details>

<summary>Show Answer</summary>

**Answer: C) Pod resource usage exceeding limits**

**Explanation:** Distinguish EKS audit analysis, agent-based Runtime Monitoring and foundational GuardDuty sources. Coverage varies by enabled plan and platform; ECS Fargate support is not EKS Fargate support. CPU/memory limit monitoring belongs to operational metrics tooling, and a quiet detector does not prove the absence of compromise.

</details>

***

<span id="_6-which-aws-service-does-not-require-vpc-endpoints-in-an-eks-cluster"></span>

### 6. What is the correct way to reason about DNS and private AWS API access?

* A) An EKS management endpoint replaces the Kubernetes API
* B) Pod Identity always uses the global STS endpoint
* C) Every AWS Region supports the same endpoint names
* D) Distinguish DNS resolution from Route 53 management API PrivateLink

<details>

<summary>Show Answer</summary>

**Answer: D) Distinguish DNS resolution from Route 53 management API PrivateLink**

**Explanation:** Ordinary DNS resolution uses the configured resolver/network path. Route 53 management API calls are different; current EKS private-cluster documentation lists a Route 53 PrivateLink service. EKS Auth, regional STS, OIDC discovery and ECR/S3 also have distinct paths, so verify actual service/Region requirements.

</details>

***

### 7. What benchmark is used when checking EKS cluster security with kube-bench?

* A) PCI-DSS
* B) The applicable CIS Amazon EKS benchmark profile
* C) NIST Cybersecurity Framework
* D) SOC 2

<details>

<summary>Show Answer</summary>

**Answer: B) The applicable CIS Amazon EKS benchmark profile**

**Explanation:** Choose the CIS Amazon EKS benchmark edition and kube-bench profile appropriate to the environment. kube-bench0.16.0 includes several EKS profiles; a single mutable upstream Job is not proof of fleet coverage. Manual/not-applicable checks and managed-control-plane limits remain, and a quiz/tool score is not certification.

</details>

***

### 8. What security benefit does Service Account Token Volume Projection provide in EKS?

* A) Reduced token size
* B) Bound tokens and expiration time settings
* C) Token encryption
* D) Automatic token backup

<details>

<summary>Show Answer</summary>

**Answer: B) Bound tokens and expiration time settings**

**Explanation:** Projection supports an audience and requested lifetime with object binding. Check the token's actual expiry and receiver validation; do not assume every token expires exactly one hour later. A stolen bearer token may still be replayed while accepted, so projection does not remove token-protection requirements. Projection alone is not a complete IRSA configuration.

</details>

***

### 9. What does Amazon Inspector scan in an EKS environment?

* A) Kubernetes manifests
* B) Container image vulnerabilities
* C) IAM policies
* D) Network traffic

<details>

<summary>Show Answer</summary>

**Answer: B) Container image vulnerabilities**

**Explanation:** ECR enhanced scanning uses Inspector for supported image package vulnerabilities. Running-image usage information differs from runtime behavior detection. Gate the exact digest only after a successful status, completion timestamp and explicit findings-count map; pending/missing/error results must not become zero vulnerabilities.

</details>

***

### 10. Which log type CANNOT be enabled when sending EKS cluster Control Plane logs to CloudWatch?

* A) api
* B) audit
* C) controllerManager
* D) kubelet

<details>

<summary>Show Answer</summary>

**Answer: D) kubelet**

**Explanation:** The five EKS control-plane categories are api, audit, authenticator, controllerManager and scheduler. Kubelet/container logs require a separate node/runtime collection path. Enable exports through the cluster owner, inspect the asynchronous update and actual arrival, and configure retention and access.

</details>

***

### 11. Why should Node IAM Role and Pod IAM Role (IRSA) be separated in EKS?

* A) Cost savings
* B) Applying least privilege principle
* C) Performance improvement
* D) Reduced network latency

<details>

<summary>Show Answer</summary>

**Answer: B) Applying least privilege principle**

**Explanation:** Workload roles limit application permissions independently of node responsibilities. Node-role exposure depends on metadata reachability and privilege; not every Pod always has access. IRSA alone does not block IMDS. Review IMDSv2, network controls, hostNetwork/privileged workloads, SDK credential precedence and node compromise.

</details>

***

<span id="_12-which-component-is-responsible-for-integrating-kubernetes-rbac-with-aws-iam-in-eks"></span>

### 12. Which approach grants an EKS developer only the required namespace access?

* A) Add every developer to system:masters
* B) Share the node role with all developers
* C) Use an access entry with scoped access policy or group/RBAC mapping
* D) Disable API authentication

<details>

<summary>Show Answer</summary>

**Answer: C) Use an access entry with scoped access policy or group/RBAC mapping**

**Explanation:** Use an access entry with the required scoped EKS access policy or Kubernetes group/RBAC mapping. Authentication and authorization are separate. The aws-auth ConfigMap is a legacy path, and authentication-mode migration has one-way constraints. Avoid system:masters for ordinary developers; either EKS access policies or RBAC may independently allow an operation.

</details>

***

## Score Calculation

Calculate 1 point per question.

| Score | Rating                                                     |
| ----- | ---------------------------------------------------------- |
| 11-12 | Review complete; validate operational scenarios next                      |
| 8-10  | Good - Basic concepts understood, review advanced features |
| 5-7   | Average - Additional study recommended                     |
| 0-4   | Basic learning needed                                      |

***

## Related Documentation

* [EKS Security Best Practices](../../security/06-eks-security-best-practices.md)
* [Pod Security Standards](../../security/03-pod-security-standards.md)
* [Secrets Management](../../security/05-secrets-management.md)

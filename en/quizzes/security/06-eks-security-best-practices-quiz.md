# EKS Security Best Practices Quiz

Test your understanding of Amazon EKS security best practices with the following questions.

***

## Questions

### 1. What authentication method does a Pod use when calling AWS APIs with IRSA (IAM Roles for Service Accounts)?

* A) IAM User Access Key
* B) EC2 Instance Profile
* C) OIDC token-based AssumeRoleWithWebIdentity
* D) Credentials stored in Kubernetes Secret

<details>

<summary>Show Answer</summary>

**Answer: C) OIDC token-based AssumeRoleWithWebIdentity**

**Explanation:** How IRSA works:

1. EKS cluster's OIDC Provider issues ServiceAccount token
2. Pod calls AWS STS `AssumeRoleWithWebIdentity` API
3. OIDC token is validated and temporary credentials are issued
4. Pod calls AWS APIs with temporary credentials

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-reader
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/S3ReaderRole
```

IRSA enables fine-grained permission management at Pod level rather than node level.

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

**Explanation:** Benefits of EKS Pod Identity:

* No OIDC Provider setup required
* Simplified IAM Role Trust Policy
* Automatic credential management through Pod Identity Agent
* Simplified cross-account access

```bash
# Pod Identity association (simple CLI setup)
aws eks create-pod-identity-association \
  --cluster-name my-cluster \
  --namespace production \
  --service-account myapp-sa \
  --role-arn arn:aws:iam::123456789012:role/MyAppRole
```

IRSA requires OIDC Provider setup and complex Trust Policy for each cluster.

</details>

***

### 3. Which is NOT a requirement for using Security Groups for Pods?

* A) Nitro-based instance types
* B) Amazon VPC CNI plugin
* C) Fargate profile
* D) ENIConfig or SecurityGroupPolicy CRD

<details>

<summary>Show Answer</summary>

**Answer: C) Fargate profile**

**Explanation:** Security Groups for Pods requirements:

* **Required**: Nitro-based EC2 instances (m5, c5, r5, etc.)
* **Required**: Amazon VPC CNI plugin v1.7.7+
* **Required**: SecurityGroupPolicy CRD configuration
* **Optional**: Fargate (separate configuration method)

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: db-access-policy
spec:
  podSelector:
    matchLabels:
      app: backend
  securityGroups:
    groupIds:
      - sg-0123456789abcdef0
```

Fargate assigns ENI to each Pod automatically, requiring separate configuration.

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

**Explanation:** When private endpoint is configured:

* Accessible from within VPC
* Accessible from networks connected via VPN, Direct Connect, VPC Peering
* Not accessible from public internet

```bash
# Endpoint configuration
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config \
    endpointPublicAccess=false,endpointPrivateAccess=true
```

Using private endpoint only is recommended for security.

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

**Explanation:** Threats detected by GuardDuty EKS Protection:

* Communication with malicious IP addresses
* Cryptocurrency mining (Kubernetes API abuse)
* Tor network connections
* DNS Rebinding attacks
* Privilege escalation attempts
* Abnormal API call patterns

Resource usage monitoring is performed by:

* Kubernetes Metrics Server
* Prometheus/Grafana
* CloudWatch Container Insights

</details>

***

### 6. Which AWS service does NOT require VPC endpoints in an EKS cluster?

* A) ECR (dkr, api)
* B) S3
* C) STS
* D) Route 53

<details>

<summary>Show Answer</summary>

**Answer: D) Route 53**

**Explanation:** Recommended VPC endpoints for EKS:

* **ECR (dkr, api)**: Container image pulls
* **S3**: Image layer storage
* **STS**: IRSA/Pod Identity authentication
* **CloudWatch Logs**: Log transmission
* **EC2, ELB, Auto Scaling**: Node management

Route 53 is a global DNS service that uses standard DNS resolution, not VPC endpoints.

```bash
# Create required VPC endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxx \
  --service-name com.amazonaws.region.ecr.dkr \
  --vpc-endpoint-type Interface
```

</details>

***

### 7. What benchmark is used when checking EKS cluster security with kube-bench?

* A) PCI-DSS
* B) CIS Kubernetes Benchmark
* C) NIST Cybersecurity Framework
* D) SOC 2

<details>

<summary>Show Answer</summary>

**Answer: B) CIS Kubernetes Benchmark**

**Explanation:** kube-bench checks cluster security against the CIS (Center for Internet Security) Kubernetes Benchmark:

```bash
# Run kube-bench on EKS node
kubectl apply -f https://raw.githubusercontent.com/aquasecurity/kube-bench/main/job-eks.yaml

# Check results
kubectl logs job/kube-bench
```

Inspection items:

* Control Plane configuration (some N/A as EKS managed)
* Worker Node configuration
* Policies and Pod security
* Network policies
* Logging and auditing

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

**Explanation:** Security benefits of Service Account Token Volume Projection:

* **Bound tokens**: Valid only for specific Pod
* **Expiration time**: Automatic token expiration (default 1 hour)
* **Audience specification**: Valid only for specific audience

```yaml
spec:
  containers:
    - name: app
      volumeMounts:
        - name: token
          mountPath: /var/run/secrets/tokens
  volumes:
    - name: token
      projected:
        sources:
          - serviceAccountToken:
              path: token
              expirationSeconds: 3600
              audience: sts.amazonaws.com
```

Legacy tokens never expired, posing risks if leaked.

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

**Explanation:** Amazon Inspector's EKS integration:

* Scan container images stored in ECR
* Scan images of running workloads
* Detect OS package vulnerabilities
* Detect application package vulnerabilities (npm, pip, etc.)

```bash
# Enable Inspector
aws inspector2 enable \
  --resource-types ECR

# Check scan results
aws inspector2 list-findings \
  --filter-criteria resourceType=AWS_ECR_CONTAINER_IMAGE
```

Continuous scanning provides alerts when new CVEs are discovered.

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

**Explanation:** EKS Control Plane log types:

* **api**: API server logs
* **audit**: Audit logs (who did what)
* **authenticator**: IAM authentication logs
* **controllerManager**: Controller manager logs
* **scheduler**: Scheduler logs

kubelet logs are generated on worker nodes and are not Control Plane logs.

```bash
# Enable Control Plane logging
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

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

**Explanation:** Importance of permission separation:

**Node IAM Role (broad scope):**

* Accessible by all Pods (Instance Metadata)
* Only basic permissions like ECR pull, CloudWatch logs

**IRSA (narrow scope):**

* Connected to specific ServiceAccount only
* Grant only permissions needed per application

```yaml
# Wrong example: S3 full access on Node Role
# -> All Pods can access S3

# Correct example: Grant permissions only to specific Pod via IRSA
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-processor
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::xxx:role/S3ProcessorRole
```

</details>

***

### 12. Which component is responsible for integrating Kubernetes RBAC with AWS IAM in EKS?

* A) kube-apiserver
* B) aws-auth ConfigMap
* C) aws-iam-authenticator
* D) kube-proxy

<details>

<summary>Show Answer</summary>

**Answer: C) aws-iam-authenticator**

**Explanation:** EKS authentication flow:

1. kubectl obtains token from AWS STS
2. aws-iam-authenticator validates IAM credentials
3. aws-auth ConfigMap maps IAM -> Kubernetes user/group
4. Kubernetes RBAC determines permissions

```yaml
# aws-auth ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: arn:aws:iam::123456789012:role/DevTeamRole
      username: dev-user
      groups:
        - dev-team
  mapUsers: |
    - userarn: arn:aws:iam::123456789012:user/admin
      username: admin
      groups:
        - system:masters
```

</details>

***

## Score Calculation

Calculate 1 point per question.

| Score | Rating                                                     |
| ----- | ---------------------------------------------------------- |
| 11-12 | Excellent - EKS security expert level                      |
| 8-10  | Good - Basic concepts understood, review advanced features |
| 5-7   | Average - Additional study recommended                     |
| 0-4   | Basic learning needed                                      |

***

## Related Documentation

* [EKS Security Best Practices](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/security/06-eks-security-best-practices.md)
* [Pod Security Standards](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/security/03-pod-security-standards.md)
* [Secrets Management](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/security/05-secrets-management.md)

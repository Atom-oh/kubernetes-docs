# AWS Controllers for Kubernetes (ACK) Quiz

This quiz tests your understanding of AWS Controllers for Kubernetes (ACK) concepts, architecture, installation, security, and operations.

## Multiple Choice Questions

1. What is the main purpose of ACK (AWS Controllers for Kubernetes)?
   - A) Manage AWS resources only through the AWS console
   - B) Declaratively manage AWS resources through the Kubernetes API
   - C) Run Kubernetes clusters only on AWS
   - D) Automatically reduce AWS costs

<details>

<summary>Show Answer</summary>

**Answer: B) Declaratively manage AWS resources through the Kubernetes API**

**Explanation:**
ACK is a project that enables Kubernetes users to manage AWS services and resources directly using familiar Kubernetes APIs and tools (kubectl, Helm, etc.). This allows integration with GitOps workflows and management of AWS infrastructure as code through declarative configuration.
</details>

2. In ACK architecture, which component is installed individually for each AWS service?
   - A) Kubernetes API Server
   - B) Service controller
   - C) etcd database
   - D) kubelet

<details>

<summary>Show Answer</summary>

**Answer: B) Service controller**

**Explanation:**
ACK provides separate service controllers for each AWS service (S3, RDS, DynamoDB, etc.). For example, to manage S3 buckets you install the S3 controller, and to manage RDS databases you install the RDS controller. This modular approach allows you to install controllers only for the services you need.
</details>

3. What is the recommended method for setting IAM permissions for ACK controllers to manage AWS resources?
   - A) Use only EC2 instance profiles
   - B) Store AWS access keys in ConfigMap
   - C) Use IRSA (IAM Roles for Service Accounts)
   - D) Use root account with all AWS permissions

<details>

<summary>Show Answer</summary>

**Answer: C) Use IRSA (IAM Roles for Service Accounts)**

**Explanation:**
IRSA (IAM Roles for Service Accounts) is the recommended method for granting AWS resource management permissions to ACK controllers by associating IAM roles with Kubernetes service accounts. This approach follows the principle of least privilege, enables secure credential management, and allows granting only necessary permissions to each controller.
</details>

4. What annotation should you use in ACK to keep the AWS resource when deleting the Kubernetes resource?
   - A) services.k8s.aws/keep-resource: "true"
   - B) services.k8s.aws/deletion-policy: "orphan"
   - C) services.k8s.aws/preserve: "true"
   - D) services.k8s.aws/no-delete: "true"

<details>

<summary>Show Answer</summary>

**Answer: B) services.k8s.aws/deletion-policy: "orphan"**

**Explanation:**
By default, ACK deletes the corresponding AWS resource when the Kubernetes resource is deleted. However, setting the `services.k8s.aws/deletion-policy: "orphan"` annotation keeps the AWS resource even when the Kubernetes resource is deleted. This is useful for preventing accidental deletion of important resources in production environments.
</details>

5. How do you import existing AWS resources into Kubernetes using ACK?
   - A) Use kubectl import command
   - B) Use export feature from AWS console
   - C) Add services.k8s.aws/resource-imported: "true" annotation to the resource manifest
   - D) Use ACK CLI import command

<details>

<summary>Show Answer</summary>

**Answer: C) Add services.k8s.aws/resource-imported: "true" annotation to the resource manifest**

**Explanation:**
To import existing AWS resources into ACK, create the resource manifest and add the `services.k8s.aws/resource-imported: "true"` annotation. This causes the ACK controller to connect to the existing AWS resource instead of creating a new one. This enables gradual migration of existing infrastructure to GitOps workflows.
</details>

6. Which maturity level of ACK service controllers is suitable for production use?
   - A) Alpha
   - B) Beta
   - C) GA (Generally Available)
   - D) Preview

<details>

<summary>Show Answer</summary>

**Answer: C) GA (Generally Available)**

**Explanation:**
ACK service controllers go through three maturity levels: Alpha, Beta, and GA. Alpha is the early development stage where API changes may occur, Beta means functionality is complete but API changes are still possible. GA (Generally Available) is the stage ready for production use, providing stable APIs and complete functionality.
</details>

7. What Condition type indicates that an ACK resource has been successfully synchronized?
   - A) ACK.Ready
   - B) ACK.ResourceSynced
   - C) ACK.Healthy
   - D) ACK.Available

<details>

<summary>Show Answer</summary>

**Answer: B) ACK.ResourceSynced**

**Explanation:**
ACK resource status can be checked in the `status.conditions` field. When the `ACK.ResourceSynced` Condition is True, it means the desired state (spec) of the Kubernetes resource has been successfully synchronized with the actual AWS resource state. This allows you to verify whether the resource was correctly created or updated.
</details>

8. What is the recommended method for isolating permissions for multiple teams or environments in ACK?
   - A) Manage all environments with a single controller
   - B) Isolation using separate namespaces and IAM roles
   - C) Use only AWS Organizations
   - D) Use only VPC isolation

<details>

<summary>Show Answer</summary>

**Answer: B) Isolation using separate namespaces and IAM roles**

**Explanation:**
To isolate permissions for multiple teams or environments (development, staging, production) in ACK, it's recommended to use separate Kubernetes namespaces and IAM roles for each. Install separate controllers for each namespace and associate roles with appropriate IAM policies for that environment. Additionally, Kubernetes RBAC can be used to control user access to ACK resources.
</details>

## Short Answer Questions

9. What is the pattern called where ACK controllers call AWS APIs to create, update, and delete resources while detecting and resolving differences between desired and actual states?

<details>

<summary>Show Answer</summary>

**Answer: Reconciliation Loop or Reconciliation Pattern**

**Explanation:**
The reconciliation loop is a core pattern of Kubernetes controllers, and ACK is also based on this pattern. ACK controllers continuously compare the desired state (spec) of Kubernetes resources with the actual state of AWS resources. When differences are detected, the controller calls AWS APIs to match the actual state with the desired state. This process is automatically repeated to detect and correct drift.
</details>

10. What Kubernetes extension mechanism does ACK use to define AWS resources through the Kubernetes API?

<details>

<summary>Show Answer</summary>

**Answer: CRD (Custom Resource Definition)**

**Explanation:**
ACK uses CRD (Custom Resource Definition) to define AWS resources through the Kubernetes API. For example, when you install the S3 controller, CRDs like `Bucket` and `BucketPolicy` are created, allowing you to manage S3 buckets like Kubernetes resources. Each service controller provides CRDs for resources of the corresponding AWS service.
</details>

11. When checking the status of an ACK resource, in which field can you find the ARN (Amazon Resource Name) of the AWS resource?

<details>

<summary>Show Answer</summary>

**Answer: status.ackResourceMetadata.arn**

**Explanation:**
When an ACK resource is successfully created, the ARN of the corresponding AWS resource is stored in the `status.ackResourceMetadata.arn` field. You can see this information when checking resource status with the `kubectl describe` command. You can also check the AWS account ID that owns the resource in the `status.ackResourceMetadata.ownerAccountID` field.
</details>

12. What is the feature called that allows referencing the same AWS resource from multiple clusters or managing resources in different AWS accounts in ACK?

<details>

<summary>Show Answer</summary>

**Answer: Cross-Account Resource Management or Multi-Cluster Support**

**Explanation:**
ACK provides functionality to reference the same AWS resource from multiple Kubernetes clusters or manage resources in different AWS accounts. To do this, configure IAM role chaining or cross-account IAM policies so that ACK controllers can access resources in other accounts. This feature enables centralized resource management in multi-cluster or multi-account environments.
</details>

## Hands-on Questions

13. Write a Kubernetes manifest to create an S3 bucket using ACK. The bucket name is "my-ack-demo-bucket-2025" and add the tag Environment: Development.

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: my-ack-demo-bucket
  namespace: default
spec:
  name: my-ack-demo-bucket-2025
  tagging:
    tagSet:
      - key: Environment
        value: Development
  createBucketConfiguration:
    locationConstraint: us-west-2
```

**Explanation:**
This is a manifest for creating an S3 bucket using the ACK S3 controller. `metadata.name` is the Kubernetes resource name, and `spec.name` is the actual AWS S3 bucket name. Since bucket names must be globally unique, use a unique name in actual use. AWS resource tags can be set through `tagging.tagSet`, and `createBucketConfiguration.locationConstraint` specifies the region where the bucket will be created.
</details>

14. Write commands to install the ACK S3 controller using Helm and configure IRSA. Use cluster name "my-eks-cluster" and namespace "ack-system".

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
# 1. Add Helm chart repository
helm repo add aws-controllers-k8s https://aws.github.io/eks-charts
helm repo update

# 2. Create IAM service account for IRSA
eksctl create iamserviceaccount \
  --cluster=my-eks-cluster \
  --namespace=ack-system \
  --name=ack-s3-controller \
  --attach-policy-arn=arn:aws:iam::aws:policy/AmazonS3FullAccess \
  --approve \
  --override-existing-serviceaccounts

# 3. Install S3 controller
helm install ack-s3-controller \
  aws-controllers-k8s/s3-chart \
  --namespace ack-system \
  --create-namespace \
  --set serviceAccount.create=false \
  --set serviceAccount.name=ack-s3-controller \
  --set aws.region=us-west-2
```

**Explanation:**
First, add the ACK Helm chart repository. Then use eksctl to create an IAM service account for IRSA configuration. The required IAM policy for S3 management is attached to this service account. Finally, install the S3 controller using Helm, configured to use the already created service account. For production environments, it's better to use a custom policy with least privilege instead of AmazonS3FullAccess.
</details>

15. Write commands to check controller logs and inspect resource status for troubleshooting ACK-created resources.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
# 1. Check ACK controller logs
kubectl logs -n ack-system -l app.kubernetes.io/name=ack-s3-controller

# 2. Check specific resource status and events
kubectl describe bucket my-ack-demo-bucket

# 3. Check detailed resource status (JSON format)
kubectl get bucket my-ack-demo-bucket -o json | jq '.status'

# 4. Check resource-related events
kubectl get events --field-selector involvedObject.name=my-ack-demo-bucket

# 5. Check CRD installation status
kubectl get crd | grep services.k8s.aws

# 6. Check controller deployment status
kubectl get deployment -n ack-system
```

**Explanation:**
When troubleshooting ACK resource creation issues, check multiple aspects. First, check controller logs to identify AWS API call errors or permission issues. Use `kubectl describe` to check resource status and Conditions, and track recent changes through events. Also verify that CRDs are correctly installed and controller pods are running normally. Common issues include insufficient IAM permissions, incorrect region settings, and resource name conflicts.
</details>

---

**Scoring:**
- 13-15 correct: Excellent (ACK expert level)
- 10-12 correct: Good (practical application capable)
- 7-9 correct: Average (additional learning recommended)
- 0-6 correct: Insufficient (basic concepts review needed)

[Return to Learning Materials](../../tools/03-ack.md)

# Secrets Management Quiz

> **Last Updated**: September 13, 2026

This quiz tests your understanding of Kubernetes Secrets, AWS Secrets Manager, External Secrets Operator, and encryption.

## Quiz Questions

### 1. What is the default encoding method for Kubernetes Secrets?

A. AES-256 encryption
B. Base64 encoding
C. SHA-256 hash
D. RSA encryption

<details>
<summary>Show Answer</summary>

**Answer: B. Base64 encoding**

**Explanation:**
The serialized Secret `data` field uses Base64. Encoding is not encryption. Protect API authorization, storage and the consuming application; an external store does not eliminate these requirements.

</details>

### 2. Which AWS service is used for etcd encryption in EKS?

A. AWS Secrets Manager
B. AWS KMS (Key Management Service)
C. AWS Certificate Manager
D. AWS CloudHSM

<details>
<summary>Show Answer</summary>

**Answer: B. AWS KMS (Key Management Service)**

**Explanation:**
EKS 1.28+ defaults to KMS envelope encryption of all Kubernetes API data with an AWS-owned key. A customer-managed-key option exists. This differs from configuring a self-managed API server; do not assume a plaintext EKS default or a customer-managed key is always required.

</details>

### 3. Which resources reference AWS Secrets Manager secrets in External Secrets Operator?

A. SecretStore
B. ExternalSecret
C. ClusterSecretStore
D. A and B or C and B

<details>
<summary>Show Answer</summary>

**Answer: D. A and B or C and B**

**Explanation:**
SecretStore/ClusterSecretStore describes provider access and identity; ExternalSecret selects external values and defines the target Secret. A namespaced store references a ServiceAccount in that namespace. A ClusterSecretStore needs an explicit reference namespace and usage restrictions.

</details>

### 4. Which is NOT a way to use Secrets in a Pod?

A. Inject as environment variables
B. Mount as volumes
C. Image pull secrets
D. Convert to ConfigMap

<details>
<summary>Show Answer</summary>

**Answer: D. Convert to ConfigMap**

**Explanation:**
Pods can consume Secrets through key references, volumes and imagePullSecrets. A ConfigMap is a distinct object, not a secret-protection mechanism. Environment variables do not refresh in running containers; volume refresh and application reload are separate.

</details>

<span id="_5-which-aws-service-is-used-to-configure-automatic-rotation-in-aws-secrets-manager"></span>

### 5. Which AWS service executes a custom Lambda-based Secrets Manager rotation function?

A. AWS EventBridge
B. AWS Lambda
C. AWS Step Functions
D. AWS SNS

<details>
<summary>Show Answer</summary>

**Answer: B. AWS Lambda**

**Explanation:**
A custom Lambda-based rotation workflow uses a Lambda function with target update logic, permissions and network access. Secrets Manager also has managed-rotation integrations; not every rotation uses an operator-managed Lambda. ESO synchronizes values but does not rotate the database credential itself.

</details>

### 6. What is the main feature of Sealed Secrets?

A. Encryption in etcd
B. Safe to store in Git
C. AWS only
D. Automatic rotation support

<details>
<summary>Show Answer</summary>

**Answer: B. Safe to store in Git**

**Explanation:**
Sealed Secrets encrypts values for storage in Git using a trusted certificate. Anyone holding a suitable private key, including an authorized recovery operator, can decrypt. Metadata stays visible; key renewal does not rotate the application credential or erase old Git ciphertext.

</details>

### 7. What is the role of ExternalSecret's refreshInterval field?

A. Set secret expiration time
B. Set synchronization interval with external secret
C. Set cache retention time
D. Set retry interval

<details>
<summary>Show Answer</summary>

**Answer: B. Set synchronization interval with external secret**

**Explanation:**
With refreshPolicy Periodic and a positive refreshInterval, ESO periodically reconciles external values. It is not a guaranteed completion deadline and differs from OnChange/CreatedOnce. Provider errors, backoff and application reload still need handling.

</details>

### 8. What happens when Kubernetes Secret's immutable field is set to true?

A. Secret cannot be deleted
B. Secret data cannot be modified
C. Secret cannot be read
D. Secret cannot be copied

<details>
<summary>Show Answer</summary>

**Answer: B. Secret data cannot be modified**

**Explanation:**
Immutable prevents changes to Secret data and cannot be reverted to mutable. Metadata can still change, and deletion is still possible. Prefer a newly named Secret with a controlled rollout when replacing a live dependency.

</details>

### 9. What is the main function of CSI Secrets Store Driver?

A. Encrypt secrets in etcd
B. Mount external secrets as volumes
C. Auto-generate secrets
D. Backup secrets

<details>
<summary>Show Answer</summary>

**Answer: B. Mount external secrets as volumes**

**Explanation:**
The Secrets Store CSI Driver and a supported provider mount external values as files. Kubernetes Secret synchronization is optional and requires the sync feature and a consuming mount. Rotation, file propagation and application reload remain separate; platform support varies.

</details>

### 10. What is the advantage of using External Secrets with IRSA (IAM Roles for Service Accounts)?

A. Faster secret access
B. No need to hardcode IAM credentials in Pods
C. Automatic secret rotation
D. Free usage

<details>
<summary>Show Answer</summary>

**Answer: B. No need to hardcode IAM credentials in Pods**

**Explanation:**
IRSA exchanges a projected identity token for temporary AWS credentials through an exact role trust binding. It avoids hardcoded long-lived access keys, not credentials altogether. ESO Pod Identity uses the controller identity and cannot be substituted into serviceAccountRef impersonation.

</details>

### 11. What is the characteristic of defining Secret data with stringData?

A. Encrypted
B. No Base64 encoding required
C. More secure
D. Compressed

<details>
<summary>Show Answer</summary>

**Answer: B. No Base64 encoding required**

**Explanation:**
stringData accepts plaintext input without manual Base64 conversion, then merges it into data. It is not encryption or additional access protection; API reads expose the data representation to authorized readers. Avoid actual values in tracked YAML and note server-side-apply limitations.

</details>

### 12. Which is NOT a secrets management best practice?

A. Enable etcd encryption
B. Restrict Secret access with RBAC
C. Commit plaintext credentials to source code
D. Use external secrets management system

<details>
<summary>Show Answer</summary>

**Answer: C. Commit plaintext credentials to source code**

**Explanation:**
Never commit plaintext credentials or private decryptor keys. Encrypted SOPS/SealedSecret artifacts and value-free ESO references can be stored in Git with reviewed recipients, protected keys, recovery tests and access controls. No tool alone guarantees security or compliance.

</details>

---

[Secrets management guide](../../security/05-secrets-management.md)

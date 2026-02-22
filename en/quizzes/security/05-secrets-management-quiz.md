# Secrets Management Quiz

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
Kubernetes Secrets are Base64 encoded by default. Base64 is simple encoding, not encryption, so you should enable etcd encryption or use an external secrets management system.

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
EKS uses AWS KMS to encrypt Kubernetes Secrets stored in etcd. Envelope encryption can be enabled during cluster creation or afterwards:
```bash
aws eks associate-encryption-config \
  --cluster-name my-cluster \
  --encryption-config '[{"resources":["secrets"],"provider":{"keyArn":"arn:aws:kms:..."}}]'
```

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
External Secrets Operator components:
- **SecretStore/ClusterSecretStore**: External secret store connection settings
- **ExternalSecret**: Actual secret reference and Kubernetes Secret creation

SecretStore is namespace-scoped, ClusterSecretStore is cluster-scoped.

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
Ways to use Secrets in a Pod:
1. **Environment variables**: `envFrom.secretRef` or `env.valueFrom.secretKeyRef`
2. **Volume mount**: Mount as files
3. **Image pull secrets**: `imagePullSecrets`

Secrets are not automatically converted to ConfigMaps. They are separate resources.

</details>

### 5. Which AWS service is used to configure automatic rotation in AWS Secrets Manager?

A. AWS EventBridge
B. AWS Lambda
C. AWS Step Functions
D. AWS SNS

<details>
<summary>Show Answer</summary>

**Answer: B. AWS Lambda**

**Explanation:**
AWS Secrets Manager automatic rotation uses Lambda functions. AWS provides pre-built rotation functions for RDS, Redshift, etc., and custom rotation can be implemented with Lambda.

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
Sealed Secrets encrypts secrets with a public key so they can be safely stored in Git repositories. Only the Sealed Secrets controller in the cluster can decrypt with the private key. It's suitable for GitOps workflows.

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
`refreshInterval` defines how often External Secrets Operator synchronizes with the external secret store:
```yaml
spec:
  refreshInterval: 1h  # Sync every 1 hour
```

When secrets change externally, the Kubernetes Secret is updated according to this interval.

</details>

### 8. What happens when Kubernetes Secret's immutable field is set to true?

A. Secret cannot be deleted
B. Secret cannot be modified
C. Secret cannot be read
D. Secret cannot be copied

<details>
<summary>Show Answer</summary>

**Answer: B. Secret cannot be modified**

**Explanation:**
`immutable: true` setting prevents modification after the Secret is created:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
immutable: true
data:
  password: cGFzc3dvcmQ=
```

To change it, you must delete and recreate the Secret. This prevents accidental changes and improves performance.

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
Secrets Store CSI Driver mounts external secrets from AWS Secrets Manager, Azure Key Vault, etc. directly as CSI volumes. Pods can use secrets without creating Kubernetes Secrets.

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
IRSA allows attaching IAM roles to Service Accounts. External Secrets Operator Pods can securely access AWS Secrets Manager without AWS credentials. This is a security best practice.

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
The `stringData` field allows specifying values in plain text:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
stringData:
  password: mypassword  # Plain text, auto Base64 encoded
```

Kubernetes automatically handles Base64 encoding. However, when queried, it appears as Base64 in the data field.

</details>

### 12. Which is NOT a secrets management best practice?

A. Enable etcd encryption
B. Restrict Secret access with RBAC
C. Commit secrets to source code
D. Use external secrets management system

<details>
<summary>Show Answer</summary>

**Answer: C. Commit secrets to source code**

**Explanation:**
Secrets management best practices:
- Enable etcd encryption
- Restrict Secret access with RBAC
- Use external secrets management systems (AWS Secrets Manager, HashiCorp Vault, etc.)
- Enable audit logging
- Regular secret rotation

Never commit secrets to source code. Plain text secrets would be exposed in version control systems.

</details>

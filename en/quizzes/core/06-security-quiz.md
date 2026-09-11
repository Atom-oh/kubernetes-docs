# Security Quiz

This quiz tests your understanding of Kubernetes security concepts including authentication, authorization, network policies, security contexts, and secret management.

## Multiple Choice Questions

1. Which authentication method is NOT supported by Kubernetes for user authentication?
   - A) X.509 certificates
   - B) Service account tokens
   - C) OpenID Connect ID tokens
   - D) Built-in user database
   
<details>
<summary>Show Answer</summary>

**Answer: D) Built-in user database**

**Explanation:**
Kubernetes does not provide a built-in user database. Instead, it supports authentication methods such as X.509 certificates, service account tokens, OIDC ID tokens, and webhook token authentication. Arbitrary OAuth access tokens require an appropriate configured authenticator. User management is typically done through integration with external systems (e.g., LDAP, Active Directory).
</details>

2. Which is NOT a main component of RBAC (Role-Based Access Control) in Kubernetes?
   - A) Role
   - B) ClusterRole
   - C) RoleBinding
   - D) SecurityPolicy
   
<details>
<summary>Show Answer</summary>

**Answer: D) SecurityPolicy**

**Explanation:**
The main components of Kubernetes RBAC are Role, ClusterRole, RoleBinding, and ClusterRoleBinding. Role and ClusterRole define sets of permissions, while RoleBinding and ClusterRoleBinding associate these permissions with users, groups, or service accounts. SecurityPolicy is not an RBAC component; PodSecurityPolicy was removed in v1.25. Pod Security Standards are policy definitions enforced by Pod Security Admission, not a PodSecurityStandard API resource.
</details>

3. What CANNOT be configured through a pod's Security Context in Kubernetes?
   - A) Container user ID (UID)
   - B) Container group ID (GID)
   - C) Container network policy
   - D) Container privilege escalation capability
   
<details>
<summary>Show Answer</summary>

**Answer: C) Container network policy**

**Explanation:**
Security Context defines privilege and access control settings at the pod or container level. This includes user ID (runAsUser), group ID (runAsGroup), privilege escalation capability (allowPrivilegeEscalation), privileged containers (privileged), and capabilities. However, network policies are defined through separate NetworkPolicy resources, not Security Context.
</details>

4. What is the main purpose of a ServiceAccount in Kubernetes?
   - A) Authentication for users outside the cluster
   - B) Providing identity for pods to communicate with the API server
   - C) Encrypting communication between nodes
   - D) Granting cluster administrator privileges
   
<details>
<summary>Show Answer</summary>

**Answer: B) Providing identity for pods to communicate with the API server**

**Explanation:**
Service accounts provide identity for processes running inside pods to communicate with the Kubernetes API server. Each namespace has a default service account, and pods use this default service account unless explicitly specified otherwise. Service accounts can be used with RBAC to limit what operations pods can perform.
</details>

5. What is the main purpose of NetworkPolicy in Kubernetes?
   - A) Routing traffic from outside the cluster to inside
   - B) Controlling and restricting communication between pods
   - C) Encrypting communication between nodes
   - D) Providing service discovery
   
<details>
<summary>Show Answer</summary>

**Answer: B) Controlling and restricting communication between pods**

**Explanation:**
NetworkPolicy provides a way to control communication between groups of pods. Through this, you can specify which pods can communicate with which other pods, and which ports and protocols can be used. Network policies are important for fine-grained control of service-to-service communication and enhanced security in microservice architectures.
</details>

6. Which is the most restrictive of the three policy levels in Pod Security Standards?
   - A) Privileged
   - B) Baseline
   - C) Restricted
   - D) Enforced
   
<details>
<summary>Show Answer</summary>

**Answer: C) Restricted**

**Explanation:**
Pod Security Standards define three policy levels:
  - Privileged: No restrictions, all privileges allowed
  - Baseline: Prevents known privilege escalation paths
  - Restricted: Most restrictive policy with enhanced security settings applied

The Restricted policy is the most restrictive, following the principle of least privilege and applying security best practices. This policy prohibits privileged containers, host namespace sharing, host path mounts, and more.
</details>

7. Which option encrypts Secret data at rest in etcd?
   - A) Base64 encoding
   - B) etcd encryption configuration
   - C) Namespace isolation
   - D) Adding labels
   
<details>
<summary>Show Answer</summary>

**Answer: B) etcd encryption configuration**

**Explanation:**
Secret data in Kubernetes is stored encoded in Base64 by default, but this is simple encoding, not encryption. Using etcd encryption configuration encrypts Secret data before it's stored in etcd, protecting sensitive information from unauthorized access to the etcd database. Namespace isolation and labels can help with access control but don't protect the data itself.
</details>

8. Which is NOT a method for enhancing container image security in Kubernetes?
   - A) Image vulnerability scanning
   - B) Using trusted registries
   - C) Image signing and verification
   - D) Granting root privileges to containers
   
<details>
<summary>Show Answer</summary>

**Answer: D) Granting root privileges to containers**

**Explanation:**
Granting root privileges to containers weakens security. Methods for enhancing container image security include image vulnerability scanning, using trusted registries, image signing and verification, applying the principle of least privilege, removing unnecessary packages, and running containers as non-root users.
</details>

9. What is the main purpose of Audit Logging in Kubernetes?
   - A) Collecting pod logs
   - B) Recording API server requests
   - C) Monitoring node status
   - D) Analyzing network traffic
   
<details>
<summary>Show Answer</summary>

**Answer: B) Recording API server requests**

**Explanation:**
Audit logging is a mechanism that records requests to the Kubernetes API server. This allows tracking who did what in the cluster, useful for security incident investigation, compliance requirements, and troubleshooting. Audit logs can include information such as request time, user, request content, and response.
</details>

10. Which is NOT a characteristic of privileged containers in Kubernetes?
    - A) Access to all host devices
    - B) Granting all Linux capabilities
    - C) Ability to load host kernel modules
    - D) Automatic access to resources in other namespaces
    
<details>
<summary>Show Answer</summary>

**Answer: D) Automatic access to resources in other namespaces**

**Explanation:**
Privileged containers can access almost all host capabilities, but they do not automatically have access to Kubernetes resources in other namespaces. Cross-namespace access is controlled by RBAC permissions. `privileged: true` does not itself set `hostNetwork: true`. It removes major host isolation barriers; host compromise can expose credentials and bypass intended isolation, so RBAC is not a protection against a compromised privileged workload.
</details>

## Short Answer Questions

1. What is the main difference between 'Role' and 'ClusterRole' in Kubernetes RBAC?

<details>
<summary>Show Answer</summary>

**Answer:**
Role is a namespaced permission definition. ClusterRole is a cluster-scoped definition that may cover namespaced or cluster-scoped resources. A RoleBinding can grant a ClusterRole's namespaced permissions in one namespace; a ClusterRoleBinding grants permissions cluster-wide. Defining either role alone grants nobody access.
</details>

2. Explain three methods for applying the 'principle of least privilege' in Kubernetes.

<details>
<summary>Show Answer</summary>

**Answer:**
1. Use RBAC to grant only the minimum necessary permissions
2. Run containers as non-root users in pod security context
3. Use network policies to allow only necessary communication
4. Restrict use of privileged containers
5. Restrict container capabilities
6. Apply Pod Security Standards Restricted profile

(Only three of the above need to be explained)
</details>

3. What is the main difference between Secret and ConfigMap from a security perspective in Kubernetes?

<details>
<summary>Show Answer</summary>

**Answer:**
Secret is for storing sensitive information (passwords, tokens, keys, etc.), while ConfigMap is for storing general configuration data. Secret `data` uses base64 in API representations, not encryption. Full Secret volumes on Linux use memory-backed storage and can receive updates after Pod creation; applications must reread them. Encryption at rest is cluster-dependent (EKS 1.28+ encrypts API data by default). RBAC and least-privilege Pod access remain necessary.
</details>

4. What is the purpose and benefit of 'service account token volume projection' in Kubernetes?

<details>
<summary>Show Answer</summary>

**Answer:**
Service account token volume projection provides additional security features for service account tokens mounted to pods, such as time limits and audience restrictions. This allows limiting token lifetime and ensuring only specific API servers accept the token, reducing risk in case of token leakage. Kubelet rotates the projected token; applications must reread it and the recipient must validate its audience and expiry. Rotation alone does not update a token cached forever by an application.
</details>

5. What is 'container sandboxing' in Kubernetes, and what technologies can be used to implement it?

<details>
<summary>Show Answer</summary>

**Answer:**
Container sandboxing is a technique that enhances security by isolating containers from the host system and other containers. Technologies for implementing this include:
1. Linux namespaces and cgroups: Provide basic container isolation
2. seccomp: Restricts system calls
3. AppArmor/SELinux: Mandatory access control
4. gVisor: Additional isolation through user-space kernel implementation
5. Kata Containers: Hardware-level isolation using lightweight VMs
6. Firecracker: MicroVM-based isolation

These technologies limit the impact containers can have on the host system and reduce the risk of container escape attacks.
</details>

## Hands-on Questions

1. Create RBAC resources that meet the following requirements:
   - A Role that can read pods in the 'monitoring' namespace
   - A RoleBinding that binds this Role to the 'monitoring-team' service account

<details>
<summary>Show Answer</summary>

**Answer:**

```yaml
# monitoring-role.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: monitoring
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
---
# monitoring-rolebinding.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: monitoring
subjects:
- kind: ServiceAccount
  name: monitoring-team
  namespace: monitoring
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

How to apply:
```bash
kubectl apply -f monitoring-role.yaml
kubectl apply -f monitoring-rolebinding.yaml
```
</details>

2. Create a NetworkPolicy that meets the following requirements:
   - Applies to all pods in the 'backend' namespace
   - Allow incoming traffic only from pods in the 'frontend' namespace on port 8080
   - Allow all outgoing traffic

<details>
<summary>Show Answer</summary>

**Answer:**

```yaml
# backend-network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-allow-frontend
  namespace: backend
spec:
  podSelector: {}  # Apply to all pods
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - {}  # Allow all outgoing traffic
```

How to apply:
```bash
kubectl apply -f backend-network-policy.yaml
```

The built-in `kubernetes.io/metadata.name: frontend` namespace label selects the `frontend` namespace without requiring a custom label. Other additive policies and the source Pod's egress policy still affect reachability.
</details>

3. Create a pod with the following security context requirements:
   - Container runs as UID 1000
   - Privilege escalation not allowed
   - Read-only root filesystem

<details>
<summary>Show Answer</summary>

**Answer:**

```yaml
# secure-pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  containers:
  - name: secure-container
    image: busybox:1.36
    command: ["sh", "-c", "sleep 3600"]
    securityContext:
      runAsUser: 1000
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
```

How to apply:
```bash
kubectl apply -f secure-pod.yaml
```
</details>

4. Create a Secret and mount it as a volume to a pod with the following requirements:
   - Secret named 'db-credentials'
   - Contains 'username=admin' and 'password=s3cr3t'
   - Mounted at '/etc/db-credentials' path in the pod

<details>
<summary>Show Answer</summary>

**Answer:**

Create Secret:
```bash
kubectl create secret generic db-credentials \
  --from-literal=username=admin \
  --from-literal=password=s3cr3t
```

Or as YAML:
```yaml
# db-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
data:
  username: YWRtaW4=  # base64 encoding of 'admin'
  password: czNjcjN0  # base64 encoding of 's3cr3t'
```

Mount to pod:
```yaml
# pod-with-secret.yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-with-secret
spec:
  containers:
  - name: app
    image: nginx
    volumeMounts:
    - name: secret-volume
      mountPath: "/etc/db-credentials"
      readOnly: true
  volumes:
  - name: secret-volume
    secret:
      secretName: db-credentials
```

How to apply:
```bash
kubectl apply -f db-secret.yaml
kubectl apply -f pod-with-secret.yaml
```
</details>

## Advanced Topics

1. Provide three examples of policies that can be implemented using OPA (Open Policy Agent) Gatekeeper in Kubernetes and explain them.

<details>
<summary>Show Answer</summary>

**Answer:**

OPA Gatekeeper is a powerful tool for applying policies to Kubernetes clusters. Install Gatekeeper and the matching ConstraintTemplates from the official policy library before creating these constraints. Constraint kinds are not built-in Kubernetes APIs, and registry allow-listing alone does not verify image signatures. Here are examples of policies that can be applied:

1. **Image Registry Restriction**: Force images to only be pulled from approved registries, preventing use of images from untrusted sources.
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sAllowedRepos
   metadata:
     name: allowed-repos
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       repos:
         - "docker.io/company/"
         - "gcr.io/company/"
   ```

2. **Prevent Privileged Containers**: Prohibit use of privileged containers to reduce security risks.
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sPSPPrivilegedContainer
   metadata:
     name: prevent-privileged-containers
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
   ```

3. **Enforce Resource Limits**: Force all containers to have CPU and memory limits set to prevent resource exhaustion attacks.
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sRequiredResources
   metadata:
     name: container-must-have-limits
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       limits:
         - cpu
         - memory
   ```

OPA Gatekeeper can also apply various other policies such as requiring specific labels on namespaces, restricting ingress hostnames, limiting volume types, and preventing host path mounts.
</details>

2. Explain how to implement mTLS (mutual TLS) in Kubernetes and its benefits.

<details>
<summary>Show Answer</summary>

**Answer:**

mTLS (mutual TLS) is a method where both client and server authenticate each other using certificates. Here's how to implement mTLS in Kubernetes and its benefits:

**Implementation Methods:**

1. **Using Service Mesh**: Service meshes like Istio and Linkerd automatically implement mTLS through sidecar proxies.
   ```yaml
   # Istio example
   apiVersion: security.istio.io/v1
   kind: PeerAuthentication
   metadata:
     name: default
     namespace: istio-system
   spec:
     mtls:
       mode: STRICT
   ```

2. **Use with Network Policies**: NetworkPolicy restricts L3/L4 reachability; the mesh authenticates certificates. Enroll workloads, enforce mTLS, and apply mesh authorization to restrict authenticated identities.

3. **Certificate Management**: Use tools like cert-manager to manage certificate lifecycle.
   ```yaml
   apiVersion: cert-manager.io/v1
   kind: Certificate
   metadata:
     name: service-cert
     namespace: default
   spec:
     secretName: service-tls
     issuerRef:
       name: ca-issuer
       kind: ClusterIssuer
     commonName: service.default.svc.cluster.local
     dnsNames:
     - service.default.svc.cluster.local
   ```

**Benefits:**

1. **Mutual Authentication**: Client and server authenticate each other, preventing man-in-the-middle attacks
2. **Encrypted Communication**: All service-to-service traffic is encrypted, preventing eavesdropping
3. **Fine-grained Access Control**: Certificate-based identity enables fine-grained access control
4. **Zero Trust Architecture**: Require authentication for all communication regardless of network location
5. **Compliance Support**: Helps meet compliance requirements like PCI DSS, HIPAA

mTLS is an important method for enhancing security of service-to-service communication in microservice architectures.
</details>

3. Explain methods for enhancing 'supply chain security' in Kubernetes.

<details>
<summary>Show Answer</summary>

**Answer:**

Methods for enhancing supply chain security in Kubernetes include:

1. **Image Signing and Verification**:
   - Sign container images using tools like Cosign, Notary
   - Apply policies to ensure only signed images are deployed (e.g., OPA Gatekeeper, Kyverno)
   ```bash
   cosign sign --key cosign.key "${IMAGE_REF:?Set repository@sha256:digest}"
   ```

2. **Software Bill of Materials (SBOM) Generation and Verification**:
   - Generate SBOMs using tools like Syft, Anchore
   - Track all software components included in images
   ```bash
   syft "${IMAGE_REF:?Set repository@sha256:digest}" -o spdx-json > sbom.json
   ```

3. **Vulnerability Scanning**:
   - Scan images for vulnerabilities using tools like Trivy, Clair
   - Integrate scanning into CI/CD pipelines
   ```bash
   trivy image "${IMAGE_REF:?Set repository@sha256:digest}"
   ```

4. **Use Minimal Base Images**:
   - Use minimal images like distroless, scratch to reduce attack surface
   ```dockerfile
   FROM gcr.io/distroless/java21-debian13:nonroot
   COPY app.jar /app.jar
   CMD ["app.jar"]
   ```

5. **Apply Image Policies**:
   - Apply policies based on image age, vulnerability severity, registry source, etc.
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sAllowedRepos
   metadata:
     name: trusted-images
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       repos:
         - "docker.io/company/"
         - "gcr.io/verified/"
   ```

6. **Supply Chain Levels for Software Artifacts (SLSA)**:
   - Track build provenance
   - Ensure reproducible builds
   - Verify build integrity

7. **Continuous Monitoring and Auditing**:
   - Use runtime security tools to detect anomalous behavior
   - Perform regular security audits

Combining these methods helps protect Kubernetes environments from software supply chain attacks.
</details>

4. Explain the approach for implementing a 'zero trust security model' in Kubernetes.

<details>
<summary>Show Answer</summary>

**Answer:**

The zero trust security model is based on the principle of "never trust, always verify." Here's the approach for implementing zero trust in Kubernetes:

1. **Fine-grained Identity and Access Management**:
   - Implement strong RBAC policies
   - Grant minimum necessary permissions to service accounts
   - Integrate with external ID providers (OIDC, LDAP, etc.)
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     namespace: default
     name: minimal-access
   rules:
   - apiGroups: [""]
     resources: ["pods"]
     verbs: ["get"]
     resourceNames: ["app-pod"]
   ```

2. **Network Segmentation**:
   - Deny all traffic by default
   - Apply network policies that only allow explicitly required communication
   - Implement microsegmentation
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: default-deny
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     - Egress
   ```

3. **Apply Mutual TLS (mTLS)**:
   - Use service mesh (Istio, Linkerd, etc.) to apply mTLS to all service-to-service communication
   - Certificate-based service identity verification
   ```yaml
   apiVersion: security.istio.io/v1
   kind: PeerAuthentication
   metadata:
     name: default
     namespace: istio-system
   spec:
     mtls:
       mode: STRICT
   ```

4. **Continuous Verification and Authentication**:
   - Continuous authentication and authorization for all requests
   - Context-based access control (time, location, device state, etc.)
   - Dynamic policy application using OPA Gatekeeper or Kyverno

5. **Encryption**:
   - Data at rest encryption (etcd encryption, encrypted PVs, etc.)
   - Data in transit encryption (TLS, mTLS)
   - Secret management tool integration (Vault, Sealed Secrets, etc.)

6. **Threat Detection and Response**:
   - Deploy runtime security monitoring tools
   - Detect anomalous behavior and alert
   - Implement automated response mechanisms

7. **Least Privilege Workload Configuration**:
   - Run containers as non-root users
   - Use read-only filesystems
   - Apply security context restrictions
   ```yaml
   spec:
     securityContext:
       runAsUser: 1000
       runAsGroup: 3000
       fsGroup: 2000
       runAsNonRoot: true
       seccompProfile:
         type: RuntimeDefault
     containers:
     - name: app
       image: busybox:1.36
       command: ["sh", "-c", "sleep 3600"]
       securityContext:
         readOnlyRootFilesystem: true
         allowPrivilegeEscalation: false
         capabilities:
           drop: ["ALL"]
   ```

8. **Continuous Security Posture Assessment**:
   - Regular vulnerability scanning
   - Penetration testing and security audits
   - Compliance monitoring

The zero trust model is not a single solution but an approach combining multiple security layers, based on continuous verification and the principle of least privilege.
</details>

5. Compare and explain tools and technologies for 'runtime security' in Kubernetes.

<details>
<summary>Show Answer</summary>

**Answer:**

Major tools and technologies for runtime security in Kubernetes include:

1. **Falco**:
   - **How it works**: Monitors system calls to detect anomalous behavior
   - **Features**: 
     - Operates at kernel level to monitor container internal activity
     - Custom rules for detecting various security threats
     - Real-time alerting and response support
   - **Example rule**:
     ```yaml
     - rule: Terminal shell in container
       desc: A shell was spawned by a container
       condition: spawned_process and container and proc.name = bash and proc.tty != 0
       output: Shell opened in container (user=%user.name container=%container.name)
       priority: WARNING
     ```

2. **Seccomp (Secure Computing Mode)**:
   - **How it works**: Restricts system calls that containers can use
   - **Features**:
     - Uses built-in Linux kernel feature
     - Only allowed system calls can execute
     - Reduces attack surface
   - **Implementation example**:
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: seccomp-pod
     spec:
       securityContext:
         seccompProfile:
           type: Localhost
           localhostProfile: profiles/audit.json
       containers:
       - name: app
         image: busybox:1.36
         command: ["sh", "-c", "sleep 3600"]
     ```

3. **AppArmor**:
   - **How it works**: Applies per-program access control profiles
   - **Features**:
     - Fine-grained access control for files, network, capabilities, etc.
     - Requires a Linux node with AppArmor enabled and the profile preloaded
     - Per-container profile application possible
   - **Implementation example**:
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: apparmor-pod
     spec:
       containers:
       - name: container1
         image: busybox:1.36
         command: ["sh", "-c", "sleep 3600"]
         securityContext:
           appArmorProfile:
             type: Localhost
             localhostProfile: restricted
     ```

4. **SELinux**:
   - **How it works**: Applies Mandatory Access Control (MAC) policies
   - **Features**:
     - Fine-grained label-based security policies
     - Enforces the configured host SELinux policy
     - Complex configuration required
   - **Implementation example**:
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: selinux-pod
     spec:
       securityContext:
         seLinuxOptions:
           level: "s0:c123,c456"
       containers:
       - name: app
         image: busybox:1.36
         command: ["sh", "-c", "sleep 3600"]
     ```

5. **OPA Gatekeeper**:
   - **How it works**: Admission-time enforcement and periodic audit of API objects; not syscall monitoring
   - **Features**:
     - Declarative policy definition
     - Wide policy application scope
     - Audit and enforcement mode support

6. **Commercial Tools (Aqua, Sysdig, StackRox, etc.)**:
   - **How it works**: Provide comprehensive container security platforms
   - **Features**:
     - Integrated vulnerability scanning, runtime protection, compliance monitoring
     - Machine learning-based anomaly detection
     - Dashboard and reporting features

7. **gVisor**:
   - **How it works**: Provides user-space kernel between application and host kernel
   - **Features**:
     - Additional isolation layer between container and host
     - System call interception and emulation
     - Performance overhead exists
   - **Implementation example**:
     ```yaml
     apiVersion: node.k8s.io/v1
     kind: RuntimeClass
     metadata:
       name: gvisor
     handler: runsc
     ```

8. **Kata Containers**:
   - **How it works**: Runs containers using lightweight VMs
   - **Features**:
     - Hardware-level isolation
     - OCI compatibility maintained
     - Higher overhead than regular containers

The seccomp Localhost profile must exist under the kubelet seccomp profile directory on eligible nodes; an audit-only profile logs calls rather than blocking them. AppArmor/SELinux require host support and configured profiles/labels. RuntimeClass handlers (`runsc`, `kata`) must already be installed and configured in the CRI runtime, and Pods must select `runtimeClassName`; creating a RuntimeClass does not install a runtime. The Java Dockerfile assumes a compatible prebuilt `app.jar` in the build context.

**Comparison and Selection Criteria**:
  - **Security level**: Kata Containers and gVisor add isolation boundaries; choose against a threat model
  - **Performance impact**: Measure startup, I/O, memory, and syscall overhead for the actual workload
  - **Implementation complexity**: Seccomp and AppArmor are relatively easy, SELinux is complex
  - **Monitoring vs Prevention**: Falco is primarily monitoring, others provide preventive protection
  - **Integration ease**: OPA Gatekeeper integrates closely with Kubernetes

Choose the appropriate tool combination based on your organization's security requirements, performance goals, and operational complexity tolerance.
</details>

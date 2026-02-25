# SPIFFE/SPIRE Quiz

Test your understanding of SPIFFE/SPIRE workload identity with the following questions.

---

## Questions

### 1. What is the correct format for a SPIFFE ID?

- A) spiffe://workload/trust-domain/path
- B) spiffe://trust-domain/path
- C) trust-domain://spiffe/path
- D) https://spiffe/trust-domain/path

<details>
<summary>Show Answer</summary>

**Answer: B) spiffe://trust-domain/path**

**Explanation:**
SPIFFE ID format is a URI with the following structure:

```
spiffe://trust-domain/path
```

Examples:
```
spiffe://example.org/ns/production/sa/frontend
spiffe://cluster.local/k8s/ns/default/pod/nginx-abc123
spiffe://acme.com/region/us-east-1/service/payment
```

Components:
- **spiffe://**: Required scheme
- **trust-domain**: Organization's identity namespace (e.g., example.org)
- **path**: Hierarchical identifier for the workload

</details>

---

### 2. What is the key difference between X.509-SVID and JWT-SVID?

- A) X.509-SVID is for authentication, JWT-SVID is for authorization
- B) X.509-SVID is for mTLS connections, JWT-SVID is for API authentication
- C) They are identical in function
- D) X.509-SVID expires faster than JWT-SVID

<details>
<summary>Show Answer</summary>

**Answer: B) X.509-SVID is for mTLS connections, JWT-SVID is for API authentication**

**Explanation:**
SPIFFE supports two SVID (SPIFFE Verifiable Identity Document) types:

**X.509-SVID:**
- Used for mTLS (mutual TLS) connections
- Contains SPIFFE ID in SAN (Subject Alternative Name) URI
- Long-lived (hours to days)
- Best for: Service-to-service mTLS

**JWT-SVID:**
- Used for API authentication (HTTP headers)
- Contains SPIFFE ID in `sub` claim
- Short-lived (minutes)
- Best for: REST APIs, serverless, cross-network calls

```yaml
# X.509-SVID use case
service-a --mTLS--> service-b

# JWT-SVID use case
service-a --HTTP + JWT Bearer--> API Gateway
```

</details>

---

### 3. What is the primary role of the SPIRE Server?

- A) Running workloads
- B) Issuing SVIDs and managing workload registration
- C) Load balancing traffic
- D) Storing application secrets

<details>
<summary>Show Answer</summary>

**Answer: B) Issuing SVIDs and managing workload registration**

**Explanation:**
SPIRE Server responsibilities:

```
┌─────────────────────────────────────────────┐
│              SPIRE Server                    │
├─────────────────────────────────────────────┤
│  - Manages trust domain CA                   │
│  - Issues X.509 and JWT SVIDs               │
│  - Stores workload registration entries     │
│  - Performs node attestation                │
│  - Maintains federation relationships       │
└─────────────────────────────────────────────┘
                    │
         ┌─────────┴─────────┐
         ▼                   ▼
   SPIRE Agent          SPIRE Agent
     (Node 1)             (Node 2)
```

Key functions:
- Certificate Authority for the trust domain
- Registration API for workload entries
- Node and workload attestation verification
- SVID signing and rotation

</details>

---

### 4. What is the primary role of the SPIRE Agent?

- A) Managing cluster networking
- B) Running on nodes to attest workloads and deliver SVIDs locally
- C) Storing cluster secrets
- D) Scheduling pods

<details>
<summary>Show Answer</summary>

**Answer: B) Running on nodes to attest workloads and deliver SVIDs locally**

**Explanation:**
SPIRE Agent runs as a DaemonSet on each node:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: spire-agent
  namespace: spire
spec:
  template:
    spec:
      containers:
      - name: spire-agent
        image: ghcr.io/spiffe/spire-agent:1.8
        volumeMounts:
        - name: spire-agent-socket
          mountPath: /run/spire/sockets
```

Agent responsibilities:
- Attests to the SPIRE Server (node attestation)
- Verifies local workload identity (workload attestation)
- Fetches and caches SVIDs from Server
- Exposes Workload API (Unix domain socket) to local workloads
- Handles SVID rotation

</details>

---

### 5. Which node attestation method is recommended for Amazon EKS?

- A) aws_iid
- B) k8s_sat
- C) k8s_psat
- D) join_token

<details>
<summary>Show Answer</summary>

**Answer: C) k8s_psat**

**Explanation:**
Node attestation methods for Kubernetes:

**k8s_psat (Projected Service Account Token)** - Recommended for EKS:
```yaml
# SPIRE Server configuration
nodeAttestor "k8s_psat" {
    plugin_data {
        clusters = {
            "eks-cluster" = {
                service_account_allow_list = ["spire:spire-agent"]
                kube_config_file = ""
                allowed_node_label_keys = ["topology.kubernetes.io/zone"]
            }
        }
    }
}
```

Why k8s_psat for EKS:
- Uses projected service account tokens (more secure)
- Tokens are audience-bound and time-limited
- Works with EKS OIDC provider
- No need for cloud provider credentials on agents

Alternatives:
- **k8s_sat**: Legacy service account tokens (less secure)
- **aws_iid**: EC2 instance identity (for non-EKS)

</details>

---

### 6. What selector types does k8s workload attestation support?

- A) Container image only
- B) Namespace, service account, pod labels, and container image
- C) IP address only
- D) Node name only

<details>
<summary>Show Answer</summary>

**Answer: B) Namespace, service account, pod labels, and container image**

**Explanation:**
Kubernetes workload attestation selectors:

```bash
# Create registration entry with selectors
spire-server entry create \
    -spiffeID spiffe://example.org/ns/production/sa/frontend \
    -parentID spiffe://example.org/agent/node1 \
    -selector k8s:ns:production \
    -selector k8s:sa:frontend \
    -selector k8s:pod-label:app:frontend \
    -selector k8s:container-image:nginx:1.25
```

Available selectors:
| Selector | Example | Description |
|----------|---------|-------------|
| k8s:ns | k8s:ns:production | Namespace |
| k8s:sa | k8s:sa:frontend | ServiceAccount |
| k8s:pod-label | k8s:pod-label:app:web | Pod labels |
| k8s:container-image | k8s:container-image:nginx | Container image |
| k8s:pod-name | k8s:pod-name:nginx-xyz | Specific pod |
| k8s:pod-uid | k8s:pod-uid:abc-123 | Pod UID |

</details>

---

### 7. What is the purpose of the SPIFFE CSI Driver?

- A) Managing persistent volumes
- B) Mounting SVIDs directly into pods without sidecars
- C) Encrypting node storage
- D) Network policy enforcement

<details>
<summary>Show Answer</summary>

**Answer: B) Mounting SVIDs directly into pods without sidecars**

**Explanation:**
The SPIFFE CSI Driver provides a sidecar-less approach to SVID delivery:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-workload
spec:
  containers:
  - name: app
    image: my-app:latest
    volumeMounts:
    - name: spiffe
      mountPath: /run/spiffe/certs
      readOnly: true
  volumes:
  - name: spiffe
    csi:
      driver: "csi.spiffe.io"
      readOnly: true
```

Benefits:
- No sidecar container needed
- SVIDs automatically mounted as files
- Transparent certificate rotation
- Reduced pod complexity
- Works with any application expecting file-based certificates

The CSI driver communicates with the SPIRE Agent to fetch and mount SVIDs.

</details>

---

### 8. What does SPIFFE Federation enable?

- A) Database replication
- B) Cross-trust-domain communication between separate SPIFFE deployments
- C) Pod scheduling across clusters
- D) Secret synchronization

<details>
<summary>Show Answer</summary>

**Answer: B) Cross-trust-domain communication between separate SPIFFE deployments**

**Explanation:**
SPIFFE Federation allows workloads in different trust domains to authenticate:

```
┌─────────────────────┐      Federation      ┌─────────────────────┐
│  Trust Domain A     │◄──────────────────►│  Trust Domain B      │
│  example.org        │     Bundle Exchange │  partner.com         │
├─────────────────────┤                      ├─────────────────────┤
│  spiffe://example.  │                      │  spiffe://partner.   │
│  org/service/api    │   ─── mTLS ───►     │  com/service/db      │
└─────────────────────┘                      └─────────────────────┘
```

Configuration:
```yaml
# SPIRE Server federation config
federatesWith "partner.com" {
    bundleEndpointURL = "https://spire.partner.com:8443"
    bundleEndpointProfile "https_spiffe" {
        endpointSPIFFEID = "spiffe://partner.com/spire/server"
    }
}
```

Use cases:
- Multi-cloud deployments
- Partner integrations
- Mergers and acquisitions
- Zero-trust cross-organization communication

</details>

---

### 9. How does SPIFFE/SPIRE compare to IAM Roles for Service Accounts (IRSA)?

- A) IRSA is platform-agnostic, SPIFFE is AWS-only
- B) SPIFFE provides platform-agnostic identity, IRSA is AWS-specific
- C) They are identical technologies
- D) SPIFFE only works with Azure

<details>
<summary>Show Answer</summary>

**Answer: B) SPIFFE provides platform-agnostic identity, IRSA is AWS-specific**

**Explanation:**
SPIFFE/SPIRE vs IRSA comparison:

| Feature | SPIFFE/SPIRE | IRSA |
|---------|--------------|------|
| Platform | Any (multi-cloud) | AWS only |
| Identity Format | SPIFFE ID (URI) | IAM Role ARN |
| Credential Type | X.509/JWT SVID | AWS STS token |
| Service-to-Service | Native mTLS | Not supported |
| AWS Service Access | Via JWT exchange | Direct |
| Setup Complexity | Higher | Lower (EKS native) |

When to use each:
- **IRSA**: AWS-native workloads accessing AWS services
- **SPIFFE/SPIRE**: Multi-cloud, service mesh, mTLS requirements

You can use both together:
```
Pod --SPIFFE--> Service Mesh (mTLS)
Pod --IRSA--> AWS Services (S3, DynamoDB)
```

</details>

---

### 10. What are best practices for naming trust domains in SPIFFE?

- A) Use random strings
- B) Use IP addresses
- C) Use DNS-style names that your organization controls
- D) Use sequential numbers

<details>
<summary>Show Answer</summary>

**Answer: C) Use DNS-style names that your organization controls**

**Explanation:**
Trust domain naming best practices:

**Recommended patterns:**
```
# Organization domain
spiffe://example.com/...

# Environment-specific
spiffe://prod.example.com/...
spiffe://staging.example.com/...

# Region-specific
spiffe://us-east.example.com/...
```

**Best practices:**
1. Use domains you own (prevents collision)
2. Keep trust domains stable (changing is disruptive)
3. Consider environment separation
4. Plan for federation from the start

**Anti-patterns to avoid:**
```
# Bad: Generic names
spiffe://cluster/...
spiffe://kubernetes/...

# Bad: Temporary names
spiffe://test123/...

# Bad: IP addresses
spiffe://10.0.0.1/...
```

Trust domain names appear in all SVIDs and logs, so choose meaningful, stable identifiers.

</details>

---

## Score Calculation

- **9-10 correct**: Excellent - You have a deep understanding of SPIFFE/SPIRE.
- **7-8 correct**: Good - You have a solid grasp of the key concepts.
- **5-6 correct**: Fair - There are areas that need additional study.
- **4 or fewer**: Please review the documentation again.

## Related Documentation

- [Workload Identity with SPIFFE/SPIRE](../../security/12-spiffe-spire.md)

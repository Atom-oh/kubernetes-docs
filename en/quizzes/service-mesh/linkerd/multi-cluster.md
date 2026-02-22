# Linkerd Multi-cluster Quiz

This quiz tests your understanding of Linkerd multi-cluster features.

## Quiz Questions

### 1. What is the core concept of Linkerd multi-cluster architecture?

A. Mesh federation
B. Service mirroring
C. Cluster merging
D. Global load balancer

<details>
<summary>Show Answer</summary>

**Answer: B. Service mirroring**

**Explanation:**
Linkerd uses a service mirroring architecture. Exported services from remote clusters appear as mirror services in the local cluster, accessible like local services.

</details>

### 2. What must be shared for mTLS communication between two clusters?

A. Identity Issuer
B. Trust Anchor
C. Workload certificates
D. Kubernetes Secret

<details>
<summary>Show Answer</summary>

**Answer: B. Trust Anchor**

**Explanation:**
For two clusters to mutually trust each other, they must share the same Trust Anchor (Root CA). Each cluster can have separate Identity Issuers, but they must be signed by the same Trust Anchor.

</details>

### 3. What label is used to export a service to other clusters?

A. linkerd.io/exported: "true"
B. mirror.linkerd.io/exported: "true"
C. multicluster.linkerd.io/export: "enabled"
D. linkerd.io/multicluster: "export"

<details>
<summary>Show Answer</summary>

**Answer: B. mirror.linkerd.io/exported: "true"**

**Explanation:**
Adding the `mirror.linkerd.io/exported: "true"` label to a service makes it mirrored by other linked clusters.

</details>

### 4. What is the naming format for mirror services?

A. <service>.<cluster>
B. <service>-<cluster>
C. <cluster>-<service>
D. <service>@<cluster>

<details>
<summary>Show Answer</summary>

**Answer: B. <service>-<cluster>**

**Explanation:**
Mirror services are created in the format `<original-service-name>-<original-cluster-name>`. Example: The web service from the west cluster is mirrored as web-west in the east cluster.

</details>

### 5. What is the purpose of the `linkerd multicluster link` command?

A. Network connection between two clusters
B. Register remote cluster credentials locally
C. Configure service-to-service traffic routing
D. Certificate exchange

<details>
<summary>Show Answer</summary>

**Answer: B. Register remote cluster credentials locally**

**Explanation:**
`linkerd multicluster link --cluster-name <name>` generates the current cluster's credentials (gateway address, service account token, etc.) to be registered in another cluster.

</details>

### 6. What command checks the status of multi-cluster gateways?

A. `linkerd multicluster status`
B. `linkerd multicluster gateways`
C. `linkerd multicluster check`
D. `kubectl get gateway`

<details>
<summary>Show Answer</summary>

**Answer: B. `linkerd multicluster gateways`**

**Explanation:**
`linkerd multicluster gateways` shows the gateway status of linked clusters. It displays ALIVE, NUM_SVC (number of mirrored services), and LATENCY.

</details>

### 7. What is the recommended configuration for gateways in EKS multi-cluster?

A. ClusterIP service
B. NodePort service
C. NLB (Network Load Balancer)
D. ALB (Application Load Balancer)

<details>
<summary>Show Answer</summary>

**Answer: C. NLB (Network Load Balancer)**

**Explanation:**
NLB is recommended for multi-cluster gateways on EKS. It's optimized for TCP/TLS traffic and configured with the `service.beta.kubernetes.io/aws-load-balancer-type: "nlb"` annotation.

</details>

### 8. What backend services are used when splitting traffic between local and remote clusters with TrafficSplit?

A. Local service and remote gateway
B. Local service and mirror service
C. Local service only
D. Direct reference to remote service

<details>
<summary>Show Answer</summary>

**Answer: B. Local service and mirror service**

**Explanation:**
TrafficSplit backends specify the local service (e.g., web) and mirror service (e.g., web-west). Traffic to the mirror service is automatically routed to the remote cluster's gateway.

</details>

### 9. What is NOT a role of the mirror controller in multi-cluster environments?

A. Watch remote services
B. Create/update mirror services
C. Issue certificates
D. Synchronize endpoints

<details>
<summary>Show Answer</summary>

**Answer: C. Issue certificates**

**Explanation:**
The service mirror controller watches exported services in remote clusters, creates/updates mirror services locally, and synchronizes endpoints. Certificate issuance is the Identity Controller's role.

</details>

### 10. What AWS service is used for private connectivity between two EKS clusters?

A. Direct Connect only
B. VPC Peering or Transit Gateway
C. Route 53 only
D. CloudFront

<details>
<summary>Show Answer</summary>

**Answer: B. VPC Peering or Transit Gateway**

**Explanation:**
For private connectivity between EKS clusters, use VPC Peering (direct connection between two VPCs) or Transit Gateway (hub-and-spoke model). Configure the gateway with an internal NLB.

</details>

### 11. How do you allow access only to specific remote services in a multi-cluster environment?

A. NetworkPolicy
B. ServerAuthorization with SPIFFE ID
C. AWS Security Group
D. Kubernetes RBAC

<details>
<summary>Show Answer</summary>

**Answer: B. ServerAuthorization with SPIFFE ID**

**Explanation:**
Control access by specifying specific SPIFFE IDs from the remote cluster in ServerAuthorization's meshTLS.identities. Example: `spiffe://root.linkerd.cluster.local/ns/production/sa/api-gateway`

</details>

### 12. What does the `linkerd multicluster check` command NOT verify?

A. Link resource status
B. Gateway connectivity
C. Application business logic
D. Service mirror controller status

<details>
<summary>Show Answer</summary>

**Answer: C. Application business logic**

**Explanation:**
`linkerd multicluster check` verifies multi-cluster infrastructure status including Link resources, gateways, service mirror controller, and certificates. It does not verify application logic.

</details>

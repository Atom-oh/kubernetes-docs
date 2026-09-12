# Linkerd Multi-cluster Quiz

Based on the [multi-cluster guide](../../../service-mesh/linkerd/06-multi-cluster.md), reviewed September 11, 2026.

### 1. What is a core mechanism in Linkerd multicluster?

- A. Merging Kubernetes clusters
- B. Service mirroring
- C. Automatically replicating every application write
- D. A mandatory global load balancer

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** A source controller watches selected service information through a target Kubernetes API and creates local discovery resources. This is not request shadowing or data replication. Hierarchical, flat and federated modes have different network requirements.

</details>

### 2. What must the clusters trust for mesh mTLS?

- A. The same issuer private key
- B. The relevant public trust-anchor bundle and issuer chains
- C. One shared workload private key
- D. Identical Kubernetes Secret objects everywhere

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** A common root is the simplest setup; a suitable shared bundle may contain multiple roots. Per-cluster issuers can have separate keys. Existing proxies need a coordinated trust-bundle transition, and public roots must be distinguished from signing keys.

</details>

### 3. Which is the default export label for hierarchical gateway-mode mirroring?

- A. linkerd.io/exported: "true"
- B. mirror.linkerd.io/exported: "true"
- C. multicluster.linkerd.io/export: "enabled"
- D. linkerd.io/multicluster: "export"

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** The default hierarchical selector matches mirror.linkerd.io/exported=true. Flat mode uses remote-discovery and federated membership uses mirror.linkerd.io/federated=member. Labels affect discovery for matching Links/RBAC; they are not an access-control boundary.

</details>

### 4. What is the usual mirrored Service name?

- A. `<service>.<cluster>`
- B. `<service>-<Link cluster name>`
- C. `<cluster>-<service>`
- D. `<service>@<cluster>`

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** The web Service imported from a Link named west normally becomes web-west in the corresponding namespace. The Link cluster name is an alias and need not equal an EKS physical cluster name. Namespace creation is not enabled by default.

</details>

### 5. What does the current link-gen command produce?

- A. VPC routes and gateway load balancers
- B. A Link and two credential Secrets for the source cluster
- C. A replicated application database
- D. New workload certificates for every Pod

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Generating with context west and applying to east lets East discover West. The chart’s controllers list supplies the source mirror controller. The old link command is deprecated. Generated kubeconfig data is sensitive and must contain a reachable API endpoint and usable CA data.

</details>

### 6. Which command reports target gateway probe statistics?

- A. linkerd multicluster status
- B. linkerd multicluster gateways
- C. kubectl get gateway
- D. linkerd gateway inspect

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** gateways reports the configured target gateway probe, not every application’s health. The probe is run by the source mirror controller. Flat-only links do not require a gateway, so use Link/endpoint/Pod connectivity diagnostics for them.

</details>

### 7. Which load-balancer setup is used in the guide’s AWS Load Balancer Controller example?

- A. A public ALB terminating the mesh’s TLS
- B. An arbitrary ClusterIP reachable automatically across Regions
- C. An internal TCP NLB selected with service.k8s.aws/nlb
- D. The legacy nlb annotation automatically proves IP-target ownership

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** The example assumes that controller, supported annotations and prepared private connectivity. EKS Auto Mode has a different class/owner. Reachability of gateway data, probe and remote Kubernetes API paths must be checked separately.

</details>

### 8. What backends can the current HTTPRoute example use for local/remote distribution?

- A. A local Service and an arbitrary remote Pod IP in another API server
- B. A local backend Service and a locally imported mirror Service
- C. Only the local Service
- D. An automatic database replica set

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** The example uses web-local and web-west through an apex Service. Relative weights are not an automatic standby policy; 100/0 does not independently switch to the zero-weight backend on failure. SMI/Failover extensions are deprecated; flat federation has separate requirements and behavior.

</details>

### 9. Which is not a mirror controller’s role?

- A. Watch selected remote Services
- B. Create/update local mirrors
- C. Issue workload certificates
- D. Maintain mode-appropriate discovery/endpoint information

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Identity issues workload certificates. The selected mirror controller still maintains legacy Endpoints for hierarchical services, while remote-discovery mode can intentionally remove local Endpoints and rely on destination-side remote discovery.

</details>

### 10. Which can provide routed private VPC connectivity when configured appropriately?

- A. Route53 alone
- B. VPC peering or suitable Transit Gateway routing
- C. CloudFront alone
- D. An EKS management interface endpoint automatically supplies flat Pod routing

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Routes, unique reachable addresses, DNS and security controls still matter. PrivateLink supplies access to selected services/resources and is not the same as VPC peering. An EKS interface endpoint is not the cluster’s Kubernetes API endpoint.

</details>

### 11. How can a final server authorize a preserved remote workload identity?

- A. Treat the AWS account name as an implicit mesh identity
- B. Use Linkerd authorization with the actual DNS-form identity in flat/federated mode
- C. Use the obsolete SPIFFE URI example through any gateway
- D. Assume a public export label authenticates callers

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Hierarchical gateways lose the original caller identity at the final server. Flat/federated paths preserve it. Same ServiceAccount/namespace/trust-domain names can identify workloads in more than one cluster; the policy does not automatically prove an East-only origin.

</details>

### 12. What does multicluster infrastructure checking not establish?

- A. Whether Link configuration has detectable errors
- B. Whether configured remote access/probes have detectable failures
- C. Application business correctness or guaranteed regional recovery
- D. Whether mirror components have detectable configuration problems

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** The checks help diagnose configuration, credentials and infrastructure. They do not establish data consistency, safe write retries, capacity or business behavior after failover. Verify actual workload outcomes separately.

</details>

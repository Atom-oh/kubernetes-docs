# Linkerd Security Quiz

This quiz tests your understanding of Linkerd security features.

## Quiz Questions

### 1. How is mTLS enabled in Linkerd?

A. Manual configuration required for each service
B. Automatically applied to all mesh traffic
C. Configuration via Kubernetes Secrets required
D. Must be enabled per namespace

<details>
<summary>Show Answer</summary>

**Answer: B. Automatically applied to all mesh traffic**

**Explanation:**
One of Linkerd's core values is "security by default." All traffic between services in the mesh automatically has mTLS applied without any configuration.

</details>

### 2. What is the role of the Server resource?

A. Define external server connections
B. Define inbound traffic port and protocol
C. Store server certificates
D. Configure load balancers

<details>
<summary>Show Answer</summary>

**Answer: B. Define inbound traffic port and protocol**

**Explanation:**
The Server resource defines inbound traffic for specific Pods. It specifies target Pods with podSelector, port with port, and protocol (HTTP/1, HTTP/2, gRPC, opaque) with proxyProtocol.

</details>

### 3. What does meshTLS.serviceAccounts specify in ServerAuthorization?

A. ServiceAccount for the server to use
B. Client ServiceAccounts allowed to access
C. ServiceAccount with certificate issuance permission
D. ServiceAccount with metrics collection permission

<details>
<summary>Show Answer</summary>

**Answer: B. Client ServiceAccounts allowed to access**

**Explanation:**
ServerAuthorization's meshTLS.serviceAccounts specifies which client ServiceAccounts can access the Server. Only workloads with the specified ServiceAccounts are allowed access.

</details>

### 4. How is traffic allowed in default-deny policy mode?

A. All traffic is automatically allowed
B. Explicit ServerAuthorization definition required
C. Allow via namespace labels
D. Configure whitelist in ConfigMap

<details>
<summary>Show Answer</summary>

**Answer: B. Explicit ServerAuthorization definition required**

**Explanation:**
In default-deny mode, all traffic is denied by default. To allow traffic, Server and ServerAuthorization must be explicitly defined. This is a zero-trust security model.

</details>

### 5. What is the recommended validity period for Trust Anchor?

A. 24 hours
B. 1 year
C. 1-10 years
D. Unlimited

<details>
<summary>Show Answer</summary>

**Answer: C. 1-10 years**

**Explanation:**
Trust Anchor (Root CA) should be valid for a long period. 1-10 years is generally recommended. Since Trust Anchor replacement is complex, set a sufficiently long validity period, adjusting for security requirements.

</details>

### 6. What ServerAuthorization setting allows unauthenticated clients (outside mesh)?

A. `meshTLS.identities: ["*"]`
B. `unauthenticated: true`
C. `external: allowed`
D. `client: any`

<details>
<summary>Show Answer</summary>

**Answer: B. `unauthenticated: true`**

**Explanation:**
Setting `client.unauthenticated: true` allows access from clients without mTLS authentication (outside mesh). This is used for traffic from health checks or ingress.

</details>

### 7. What is required when renewing the Identity Issuer certificate?

A. All proxies must be restarted
B. Trust Anchor must also be replaced
C. Update Kubernetes Secret and restart Identity Controller
D. Full cluster restart required

<details>
<summary>Show Answer</summary>

**Answer: C. Update Kubernetes Secret and restart Identity Controller**

**Explanation:**
When renewing Identity Issuer: 1) Update Secret with new certificate, 2) Restart Identity Controller. Proxies automatically renew with the new certificate. No Trust Anchor replacement needed if it remains the same.

</details>

### 8. Which policy mode allows only mTLS traffic from within the mesh?

A. deny
B. all-unauthenticated
C. all-authenticated
D. cluster-unauthenticated

<details>
<summary>Show Answer</summary>

**Answer: C. all-authenticated**

**Explanation:**
`all-authenticated` mode allows only mTLS-authenticated traffic from within the mesh. Unauthenticated traffic from outside the mesh is denied.

</details>

### 9. What setting is required in cert-manager Certificate resource for Linkerd integration?

A. isCA: false
B. isCA: true
C. usages: [digital signature]
D. algorithm: RSA

<details>
<summary>Show Answer</summary>

**Answer: B. isCA: true**

**Explanation:**
The Linkerd Identity Issuer acts as an intermediate CA, so cert-manager Certificate must have `isCA: true`. This certificate signs workload certificates.

</details>

### 10. What can be verified with the linkerd viz edges command?

A. Network edge router status
B. Service-to-service mTLS connection status
C. Cluster boundary policies
D. DNS edge cache status

<details>
<summary>Show Answer</summary>

**Answer: B. Service-to-service mTLS connection status**

**Explanation:**
`linkerd viz edges` shows connections (edges) between services, with the SECURED column indicating mTLS status. Traffic from outside the mesh shows X in SECURED.

</details>

### 11. What is the correct relationship between Linkerd security and application security?

A. Linkerd handles all security so application security is unnecessary
B. Linkerd handles transport layer, applications handle business logic security
C. Application security alone is sufficient, Linkerd security is optional
D. Both securities are completely independent with no interaction

<details>
<summary>Show Answer</summary>

**Answer: B. Linkerd handles transport layer, applications handle business logic security**

**Explanation:**
Following defense-in-depth principles, Linkerd handles transport encryption (mTLS) and service authorization, while applications handle business logic security like user authentication (JWT), RBAC, and input validation.

</details>

### 12. Which is NOT a Linkerd security metric to monitor with Prometheus alerts?

A. Certificate expiration time
B. Non-mTLS traffic ratio
C. Application login failure count
D. Authorization denied request count

<details>
<summary>Show Answer</summary>

**Answer: C. Application login failure count**

**Explanation:**
Linkerd security metrics include: certificate expiration time, non-mTLS traffic ratio, authorization denied request count. Application login failures are application-level metrics outside Linkerd's scope.

</details>

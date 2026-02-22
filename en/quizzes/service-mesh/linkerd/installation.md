# Linkerd Installation Quiz

This quiz tests your understanding of Linkerd installation and setup.

## Quiz Questions

### 1. What is the correct command to install the Linkerd CLI?

A. `apt-get install linkerd`
B. `curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh`
C. `kubectl install linkerd`
D. `helm install linkerd`

<details>
<summary>Show Answer</summary>

**Answer: B. `curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh`**

**Explanation:**
The Linkerd CLI is installed through the official installation script. This script detects the operating system and downloads the appropriate binary. Homebrew (`brew install linkerd`) or Chocolatey (`choco install linkerd2`) can also be used, but the official script is the most common method.

</details>

### 2. What command verifies cluster requirements before Linkerd installation?

A. `linkerd check`
B. `linkerd check --pre`
C. `linkerd verify`
D. `linkerd install --dry-run`

<details>
<summary>Show Answer</summary>

**Answer: B. `linkerd check --pre`**

**Explanation:**
The `linkerd check --pre` command verifies that the cluster meets requirements before Linkerd installation. It validates Kubernetes API accessibility, version compatibility, and necessary permissions. After installation, use `linkerd check` to verify full status.

</details>

### 3. What must be provided when installing Linkerd with Helm?

A. Envoy proxy image
B. Trust Anchor and Identity Issuer certificates
C. Prometheus configuration file
D. Kubernetes version information

<details>
<summary>Show Answer</summary>

**Answer: B. Trust Anchor and Identity Issuer certificates**

**Explanation:**
Unlike CLI installation, Helm installation does not auto-generate certificates. Users must create and provide Trust Anchor (Root CA) and Identity Issuer (Intermediate CA) certificates themselves. This allows better control over certificate management in production environments.

</details>

### 4. What is the recommended number of control plane replicas for Linkerd HA installation?

A. 1
B. 2
C. 3
D. 5

<details>
<summary>Show Answer</summary>

**Answer: C. 3**

**Explanation:**
HA configuration recommends 3 replicas each for Destination, Identity, and Proxy Injector. Three replicas can maintain quorum even if one fails and ensure availability during rolling updates.

</details>

### 5. Which is NOT a main feature of the Viz extension?

A. Web dashboard
B. Prometheus metrics collection
C. Automatic canary deployment
D. Real-time traffic tap

<details>
<summary>Show Answer</summary>

**Answer: C. Automatic canary deployment**

**Explanation:**
The Viz extension provides web dashboard, Prometheus-based metrics collection, Grafana dashboards, and real-time traffic tap functionality. Automatic canary deployment is implemented through separate tools like Flagger.

</details>

### 6. What load balancer type is recommended for Multicluster gateway on EKS?

A. Classic Load Balancer
B. Application Load Balancer (ALB)
C. Network Load Balancer (NLB)
D. Internal Load Balancer

<details>
<summary>Show Answer</summary>

**Answer: C. Network Load Balancer (NLB)**

**Explanation:**
NLB is optimized for TCP/TLS traffic, making it suitable for Linkerd's mTLS gateway traffic. ALB is optimized for HTTP/HTTPS, and since the Linkerd gateway operates at the TCP level, NLB is recommended.

</details>

### 7. What is the correct order for Linkerd upgrade?

A. Data plane → CRD → Control plane
B. CRD → Control plane → Data plane
C. Control plane → CRD → Data plane
D. CRD → Data plane → Control plane

<details>
<summary>Show Answer</summary>

**Answer: B. CRD → Control plane → Data plane**

**Explanation:**
The correct upgrade order is: 1) CLI upgrade, 2) CRD upgrade, 3) Control plane upgrade, 4) Data plane (proxy) upgrade. CRDs must be upgraded first to use new API versions.

</details>

### 8. What is the purpose of the `linkerd install --crds` command?

A. Install Linkerd CLI
B. Install Custom Resource Definitions
C. Generate certificates
D. Inject proxies

<details>
<summary>Show Answer</summary>

**Answer: B. Install Custom Resource Definitions**

**Explanation:**
`linkerd install --crds` installs only the CRDs (Custom Resource Definitions) used by Linkerd. This includes CRDs for ServiceProfile, Server, ServerAuthorization, etc. The control plane is installed separately with `linkerd install`.

</details>

### 9. What is the command to install the Jaeger extension?

A. `linkerd install jaeger`
B. `linkerd jaeger install | kubectl apply -f -`
C. `kubectl apply -f jaeger.yaml`
D. `helm install jaeger linkerd/jaeger`

<details>
<summary>Show Answer</summary>

**Answer: B. `linkerd jaeger install | kubectl apply -f -`**

**Explanation:**
Linkerd extensions generate manifests in the format `linkerd <extension> install` and apply them with kubectl. The Jaeger extension provides distributed tracing functionality.

</details>

### 10. What is the correct order to completely remove Linkerd?

A. Control plane → Extensions → CRD
B. Extensions → Control plane → CRD
C. CRD → Control plane → Extensions
D. All can be removed simultaneously

<details>
<summary>Show Answer</summary>

**Answer: B. Extensions → Control plane → CRD**

**Explanation:**
The removal order is the reverse of installation: 1) Remove extensions like Viz, Jaeger, Multicluster, 2) Remove control plane, 3) Remove CRDs. This is because extensions depend on the control plane, and the control plane depends on CRDs.

</details>

### 11. What does the `linkerd check` command NOT verify?

A. Kubernetes API connection
B. Certificate validity
C. Application business logic
D. Control plane Pod status

<details>
<summary>Show Answer</summary>

**Answer: C. Application business logic**

**Explanation:**
`linkerd check` only verifies Linkerd infrastructure status: Kubernetes API connection, certificate validity, control plane Pod status, proxy status, etc. It does not verify application business logic or functionality.

</details>

### 12. What annotation must be added to a namespace for automatic proxy injection?

A. `linkerd.io/inject: enabled`
B. `linkerd.io/proxy: true`
C. `sidecar.linkerd.io/inject: true`
D. `linkerd/auto-inject: yes`

<details>
<summary>Show Answer</summary>

**Answer: A. `linkerd.io/inject: enabled`**

**Explanation:**
Adding the `linkerd.io/inject: enabled` annotation to a namespace automatically injects linkerd-proxy into all new Pods in that namespace. The same annotation can be used on individual Pods.

</details>

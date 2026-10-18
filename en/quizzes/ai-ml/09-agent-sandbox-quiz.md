# Agent Sandbox on EKS Quiz

This quiz checks the Agent Sandbox v1.0.6 API (`v1beta1`) and how its defaults behave on Amazon EKS. Related chapter: [Agent Sandbox on EKS](../../ai-ml/09-agent-sandbox.md).

## Multiple Choice Questions

### 1. What does Agent Sandbox itself provide for isolating untrusted code?

- A. A built-in microVM hypervisor for every Sandbox
- B. Orchestration of Pods; isolation comes from the Pod's `RuntimeClass` (for example gVisor or Kata Containers)
- C. A seccomp profile that makes `runc` safe for any untrusted code
- D. Automatic placement on dedicated EC2 instances

<details>
<summary>Show Answer</summary>

**Answer: B. Orchestration of Pods; isolation comes from the Pod's `RuntimeClass` (for example gVisor or Kata Containers)**

**Explanation:**
The project describes itself as a sandbox orchestrator. Its threat model mitigates container escape by recommending a secure runtime selected with `runtimeClassName`, ideally set in a `SandboxTemplate` so users cannot remove it. With the default `runc`, sandboxed code shares the node kernel.

</details>

### 2. A template omits `networkPolicy` and keeps `networkPolicyManagement: Managed`. Which statement about the generated policy is correct?

- A. It allows all egress, including to CoreDNS
- B. It allows ingress only from `sandbox-router` Pods in `agent-sandbox-system`, and egress to non-private IPv4 and IPv6 ranges; CoreDNS is not allowed
- C. It allows ingress from every Pod in the same namespace
- D. It allows egress only to the VPC CIDR

<details>
<summary>Show Answer</summary>

**Answer: B. It allows ingress only from `sandbox-router` Pods in `agent-sandbox-system`, and egress to non-private IPv4 and IPv6 ranges; CoreDNS is not allowed**

**Explanation:**
The default excludes `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` and `169.254.0.0/16` from `0.0.0.0/0`, and `fc00::/7` and `fe80::/10` from `::/0`. Blocking CoreDNS is intentional to prevent internal service discovery, so public hostnames do not resolve until you change the policy or the Pod's resolver.

</details>

### 3. In an IPv4 EKS cluster, which address can a sandbox still reach under the default managed policy, unless you add an exception?

- A. IMDS at `169.254.169.254`
- B. The EKS Pod Identity Agent at `169.254.170.23`
- C. A Pod in a `100.64.0.0/10` secondary CIDR used for VPC CNI custom networking
- D. A Pod at `10.0.12.34`

<details>
<summary>Show Answer</summary>

**Answer: C. A Pod in a `100.64.0.0/10` secondary CIDR used for VPC CNI custom networking**

**Explanation:**
The default exception list covers RFC1918 and link-local ranges only. `100.64.0.0/10` is not RFC1918, so those internal addresses fall under the allowed `0.0.0.0/0` rule. IMDS and the Pod Identity Agent are in `169.254.0.0/16` and `10.0.12.34` is in `10.0.0.0/8`, so all three are blocked. In IPv6 clusters the picture differs: IPv4 rules are ignored, VPC global unicast addresses are not excluded, and IPv4 egress through `ENABLE_V4_EGRESS` is not filtered.

</details>

### 4. An agent Pod in namespace `agent-orchestrator` uses the SDK's in-cluster mode to connect straight to a sandbox Pod created from a managed-policy template. What happens?

- A. It works, because in-cluster traffic is never filtered
- B. It is blocked until the template's policy adds an ingress rule for that namespace (with an enforcing CNI)
- C. It works only over IPv6
- D. The SDK automatically falls back to a public Gateway

<details>
<summary>Show Answer</summary>

**Answer: B. It is blocked until the template's policy adds an ingress rule for that namespace (with an enforcing CNI)**

**Explanation:**
The default ingress rule admits only the router. Direct connections by Service DNS or Pod IP bypass the router, so they need an explicit ingress rule. On EKS this assumes network policy enforcement is enabled in the VPC CNI; without enforcement the policy blocks nothing.

</details>

### 5. Which `SandboxClaim` fields force a cold start instead of adopting a warm Sandbox?

- A. `warmPoolRef`
- B. `lifecycle.shutdownTime`
- C. `env` or `volumeClaimTemplates`
- D. `lifecycle.ttlSecondsAfterFinished`

<details>
<summary>Show Answer</summary>

**Answer: C. `env` or `volumeClaimTemplates`**

**Explanation:**
Environment variables and volumes must exist before the Pod is created, and a warm Pod already exists. A claim that sets either is cold-created from the pool's template. The template must also allow it: both `envVarsInjectionPolicy` and `volumeClaimTemplatesPolicy` default to `Disallowed`.

</details>

### 6. You want Kata Containers on EKS without bare-metal instances. Which approach matches the documented capabilities?

- A. EKS Auto Mode with a custom containerd runtime
- B. Fargate, because each Pod already runs in a VM and the managed NetworkPolicy is enforced there
- C. Karpenter v1.13.0+ with `EC2NodeClass.spec.cpuOptions.nestedVirtualization: enabled` on a supported family such as M8i, C8i or R8i, plus a RuntimeClass bound to those nodes
- D. Any Graviton instance, because they all expose nested virtualization

<details>
<summary>Show Answer</summary>

**Answer: C. Karpenter v1.13.0+ with `EC2NodeClass.spec.cpuOptions.nestedVirtualization: enabled` on a supported family such as M8i, C8i or R8i, plus a RuntimeClass bound to those nodes**

**Explanation:**
EC2 supports nested virtualization on specific Intel families (M7i/C7i/R7i, M8i/C8i/R8i and others). Karpenter filters instance types to those reporting `nested-virtualization`. Auto Mode owns the AMI and container runtime, so you cannot add Kata there. The VPC CNI cannot apply network policies to Fargate Pods. Bind the RuntimeClass with `scheduling` so Pods land only on prepared nodes.

</details>

### 7. What happens to a Sandbox when `operatingMode` changes from `Running` to `Suspended`?

- A. The Sandbox object, Pod and PVCs are all deleted
- B. The Pod is deleted; the Sandbox object and its PVCs remain, and the `Suspended` condition moves from `PodTerminating` to `PodTerminated`
- C. The Pod is frozen in memory on the same node
- D. Only the headless Service is deleted

<details>
<summary>Show Answer</summary>

**Answer: B. The Pod is deleted; the Sandbox object and its PVCs remain, and the `Suspended` condition moves from `PodTerminating` to `PodTerminated`**

**Explanation:**
Suspend is PVC-based: compute stops and storage stays. `Ready` becomes False with reason `SandboxSuspended`. On EKS, EBS volumes are zonal, so the resumed Pod must schedule in the volume's Availability Zone.

</details>

### 8. Before upgrading a cluster running Agent Sandbox v0.4.x to v1.0.6, what must you do?

- A. Nothing; `kubectl apply` of v1.0.6 converts objects automatically
- B. Upgrade to v0.5.2 or later, migrate stored objects to `v1beta1`, and confirm each CRD's `status.storedVersions` lists only `v1beta1`
- C. Delete all CRDs and re-create them
- D. Re-enable the conversion webhook in v1.0.6

<details>
<summary>Show Answer</summary>

**Answer: B. Upgrade to v0.5.2 or later, migrate stored objects to `v1beta1`, and confirm each CRD's `status.storedVersions` lists only `v1beta1`**

**Explanation:**
v1.0.0 removed `v1alpha1` and the conversion webhook, and direct upgrades from below v0.5.0 are not supported. If `v1alpha1` remains in `storedVersions`, the API server rejects the upgrade. Deleting the CRDs would cascade-delete every Sandbox, claim, template and pool.

</details>

### 9. You need browser access to sandboxes through `sandbox-router`. Which design fits the EKS guidance in the chapter?

- A. A `Service` of type `LoadBalancer` with an internet-facing NLB, using the router's default `AllowAll` authorizer
- B. CloudFront → CloudFront VPC origin → internal ALB → `sandbox-router-svc`, with scoped-token v2 authorization and rate limits at the ALB or Envoy tier
- C. A public IP on each sandbox Pod
- D. Port-forwarding from every user's laptop in production

<details>
<summary>Show Answer</summary>

**Answer: B. CloudFront → CloudFront VPC origin → internal ALB → `sandbox-router-svc`, with scoped-token v2 authorization and rate limits at the ALB or Envoy tier**

**Explanation:**
Only CloudFront is public; the ALB is internal and its security group admits only the CloudFront VPC-origin security group or managed prefix list. The router's default authorizer is `AllowAll`, and it does not enforce connection limits on upgraded connections such as WebSockets, so authorization and limits must be configured before exposure.

</details>

### 10. What does v1.0.6 change for a Sandbox with a 70-character name and `spec.service: true`?

- A. Nothing; it keeps working as before
- B. A CEL rule rejects it at admission, and an existing object fails every update until `spec.service` is unset or the Sandbox is re-created with a name of 63 characters or fewer
- C. The controller truncates the Service name automatically
- D. The Sandbox is converted to `v1alpha1`

<details>
<summary>Show Answer</summary>

**Answer: B. A CEL rule rejects it at admission, and an existing object fails every update until `spec.service` is unset or the Sandbox is re-created with a name of 63 characters or fewer**

**Explanation:**
The headless Service takes the Sandbox's name, and a Service name is a DNS-1035 label of at most 63 characters, so such Sandboxes never became Ready. v1.0.6 reports the failure at admission. The rule covers the whole object and does not exempt existing objects, so status updates fail too.

</details>

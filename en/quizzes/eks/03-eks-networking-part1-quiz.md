# EKS Networking Quiz - Part 1

> **Last Updated**: September 11, 2026

This quiz reviews EKS networking, address planning, policies and controller ownership. Examples use conventional Linux EC2 networking unless stated otherwise. APIs/configuration were checked against official sources and local schemas; no cloud networking changes or live packet tests were performed.

## Multiple Choice Questions

1. What is the default CNI for conventional EKS EC2 nodes?
   * A) Calico
   * B) Flannel
   * C) Amazon VPC CNI
   * D) Weave Net

<details>
<summary>Show Answer</summary>

**Answer: C) Amazon VPC CNI**

Conventional EKS EC2 nodes use Amazon VPC CNI. Auto Mode provides managed networking capabilities and Hybrid Nodes use a supported alternative CNI, so “every EKS cluster runs this DaemonSet” is too broad.

The CNI configures ordinary Pod networking using VPC addresses, with different secondary-IP, prefix and security-group-for-Pod paths. A routable address does not bypass routes, security groups, NACLs or policies, and avoiding an overlay is not a measured performance guarantee.

For Linux, the old `amazon-vpc-cni` ConfigMap with lower-case `warm-ip-target`/`enable-pod-eni` keys is not the configuration mechanism shown here. Use the actual add-on schema/Helm values or supported `aws-node` environment variables through their owner. Inspect the installed build first:

```bash
set -euo pipefail
CNI_ADDON_VERSION=$(aws eks describe-addon --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --addon-name vpc-cni --query addon.addonVersion --output text)
aws eks describe-addon-configuration --region "$EXAMPLE_REGION" --addon-name vpc-cni \
  --addon-version "$CNI_ADDON_VERSION" --query configurationSchema --output text
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n kube-system get daemonset aws-node \
  -o jsonpath='{range .spec.template.spec.containers[*]}{.name}{": "}{.image}{"\n"}{end}'
```
For example, the following is an **add-on configuration fragment**, not a Kubernetes ConfigMap. The values are illustrative warm-pool targets; merge them with reviewed existing settings and check the selected version’s schema. Windows IPAM ConfigMap settings are a different interface.

```json
{"env":{"WARM_IP_TARGET":"5","MINIMUM_IP_TARGET":"10"}}
```
Pod security groups and native NetworkPolicy each have additional prerequisites. Do not enable them as unrelated side effects of an IP-pool example or apply an unconfigured second CNI over a working cluster.

</details>

2. How are ordinary Pods addressed in IPv4 secondary-IP mode?
   * A) One dedicated VPC per Pod
   * B) An address from the node ENI/IP pool
   * C) An overlay address only
   * D) A separate subnet for every Pod

<details>
<summary>Show Answer</summary>

**Answer: B) An address from the node ENI/IP pool**

In ordinary IPv4 secondary-IP mode, IPAMD manages ENI/IP pools on the node and CNI setup assigns a pool address to the Pod network namespace. After CNI cleanup and any applicable reuse delay, addresses can return to the warm pool; they are not necessarily immediately unassigned from EC2.

The conventional max-Pods calculation below is for that mode. Each ENI's primary address is reserved; the historical extra two account for host-network system Pods:

```text
ENIs × (IPv4 addresses per ENI − 1) + 2
m5.large: 3 × (10 − 1) + 2 = 29
```
This is not a universal workload limit. Subnet space, kubelet maxPods, compute resources, custom networking and branch-ENI limits also matter. Prefix mode allocates a /28 to an ENI address slot, not exactly one prefix per ENI; Pod security groups use a separate branch-ENI path. Host-network Pods share node networking and are another exception to a simple one-secondary-IP-per-Pod description.

</details>

3. What enables the ordinary VPC CNI intra-VPC routing model?
   * A) All Pods must use one subnet
   * B) All Pods share host networking
   * C) VPC-routable Pod addresses with the required routes and controls
   * D) A mandatory service mesh

<details>
<summary>Show Answer</summary>

**Answer: C) VPC-routable Pod addresses with the required routes and controls**

For the ordinary VPC CNI path, Pods have VPC-routable addresses. Cross-node traffic can use node/ENI and VPC routing; same-node traffic can remain in the host networking stack. SGs, NACLs, policy rules and custom inspection routes still determine reachability.

The example `10.0.1.23 → 10.0.2.45` describes an ordinary intra-VPC path, not proof that every packet always traverses a VPC route table or never follows a configured appliance route. Same-node Pod traffic is not fully visible in VPC Flow Logs. Most Pods have their own network namespace; hostNetwork Pods are an exception.

Do not infer guaranteed latency/throughput improvements from the absence of an overlay. Measure the actual path and account for cross-AZ transfer, target type, SNAT and workload behavior. A service mesh is an optional additional layer, not a prerequisite for ordinary Pod routing.

</details>

4. Which Kubernetes resource expresses Pod ingress/egress policy?
   * A) Service
   * B) Ingress
   * C) NetworkPolicy
   * D) SecurityContext

<details>
<summary>Show Answer</summary>

**Answer: C) NetworkPolicy**

NetworkPolicy selects Pods and isolates only the specified traffic directions. Without a policy selecting a Pod/direction, it is non-isolated. Policies are additive: an extra restrictive-looking policy cannot remove traffic already allowed by another policy.

Use a compatible enforcement implementation. Current Amazon VPC CNI supports native network policies when enabled; the old statement that it cannot enforce them is incorrect. The managed add-on uses an `enableNetworkPolicy` configuration field, not the assumed `ENABLE_NETWORK_POLICY` environment variable:

```json
{"enableNetworkPolicy":"true"}
```
This is a fragment to merge through the selected add-on version/schema. Verify the policy agent and AWS compute/kernel/Pod-owner/interface limitations before testing. Standard startup mode can briefly allow traffic before policy attachment; strict startup mode needs all required system/DNS allowances. Do not install floating Calico manifests and native policy enforcement together without a supported migration design.

The following is for reviewed lab namespaces and controller-managed workloads. Namespace and Pod selectors in the **same peer item are ANDed**; separate peer items would be ORed. The DNS exception is explicit:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-allow
  namespace: policy-lab
spec:
  podSelector:
    matchLabels: {app: api}
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: frontend-lab
      podSelector:
        matchLabels: {role: frontend}
    ports:
    - {protocol: TCP, port: 8080}
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: database-lab
      podSelector:
        matchLabels: {app: database}
    ports:
    - {protocol: TCP, port: 5432}
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels: {k8s-app: kube-dns}
    ports:
    - {protocol: UDP, port: 53}
    - {protocol: TCP, port: 53}
```
Use actual namespace/Pod labels and listener ports. NodeLocal DNSCache or other DNS paths need different allowances. A Service/Ingress routes traffic; it does not replace these L3/L4 access rules. SecurityContext controls workload privileges, not a declarative network allow list.

</details>

5. Which DNS component is normally configured for conventional EKS cluster service discovery?
   * A) Route 53 private hosted zones alone
   * B) CoreDNS
   * C) A mandatory legacy kube-dns deployment
   * D) Cloud Map alone

<details>
<summary>Show Answer</summary>

**Answer: B) CoreDNS**

Conventional EKS uses CoreDNS for cluster DNS. Do not assume every EKS mode automatically creates a visible CoreDNS Deployment: Auto Mode supplies managed DNS, and tools that disable default bootstrap add-ons must configure their selected add-ons explicitly.

For an EKS-managed CoreDNS add-on, preserve custom configuration through its supported `corefile` configuration value and exact-version schema. Direct ConfigMap edits can be overwritten by the add-on. For self-managed CoreDNS, change configuration through its manifest/GitOps owner. Review required `ready`, forwarding, Kubernetes zones and reload behavior rather than replacing the whole ConfigMap with a generic sample.

DNS answers depend on resource type:

| Resource | Typical DNS behavior |
| --- | --- |
| Ordinary Service | `<service>.<namespace>.svc.<cluster-domain>` resolves to the Service IP family |
| Headless Service | Endpoint addresses, subject to readiness/publication settings |
| ExternalName Service | CNAME to the configured external name |
| Legacy IPv4 Pod record | A dashed address such as `10-0-1-23.<namespace>.pod.<cluster-domain>`, depending on the CoreDNS `pods` mode |

`cluster.local` is a common default, not a universal domain. `pods insecure` provides legacy IP-based answers without verifying Pod existence; it is not a security guarantee. Test DNS from an approved in-cluster diagnostic workload, not an arbitrary laptop resolver.

EKS managed CoreDNS supports configured autoscaling for compatible add-on versions. Keep one owner for replica count; a manual `kubectl scale` is not the right control loop when managed autoscaling/HPA is active.

The following **Corefile fragment** replaces an existing cache stanza after review; it is not YAML. CoreDNS 1.14.7 accepts `denial 1000` but normalizes it to a minimum effective capacity of 1024. The example makes that capacity explicit; `success 10000` is rounded down to 9984:

```text
cache {
    success 10000
    denial 1024
    prefetch 10 10m 20%
}
```
Cache capacities/TTL/prefetch settings require workload measurements; this is not a performance benchmark. Observe DNS errors, cache behavior and CPU/memory after a controlled change.

</details>

## Short Answer Questions

6. What limits Pod density, and how does prefix delegation change it?

<details>
<summary>Show Answer</summary>

Separate three limits: EC2 interface/address capacity, available subnet addresses and Kubernetes/compute capacity. In ordinary IPv4 secondary-IP mode the historical formula is `ENIs × (IPs per ENI − 1) + 2`: t3.small gives 11, m5.large 29 and c5.4xlarge 234. These are formula results, not the effective limit of every managed group.

In IPv4 prefix mode, one `/28` contributes 16 addresses and occupies one secondary-address slot. Multiple prefixes can occupy an ENI. The old “one prefix per ENI minus one address” calculation yielding 47 for m5.large was incorrect. Compatible managed groups cap maxPods at 110 for fewer than 30 vCPUs and 250 otherwise; CPU/memory and the actual CNI configuration may limit usable workload capacity further.

An example managed add-on configuration fragment is:

```json
{"env":{"ENABLE_PREFIX_DELEGATION":"true","WARM_PREFIX_TARGET":"1"}}
```
Review the exact-version schema and existing configuration before merging it. WARM_PREFIX_TARGET is spare prefix capacity, not a maximum of one prefix per ENI. WARM_IP_TARGET/MINIMUM_IP_TARGET override its behavior when configured. Prefix mode needs contiguous /28 space and a supported instance/CNI; it does not expand the subnet.

Prefix delegation and security groups for Pods can coexist. Branch-ENI Pods still use their own per-instance branch capacity and do not gain prefix density. Plan new/recycled nodes and PDB-aware migration rather than toggling variables and assuming all running Pods/maxPods changed. Custom AL2023 AMIs may need reviewed NodeConfig maxPods; raising kubelet limits alone creates no IPs or CPU.

```bash
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -o custom-columns=NAME:.metadata.name,PODS:.status.allocatable.pods,POD_ENI:.status.allocatable.vpc\\.amazonaws\\.com/pod-eni
```
Inspect actual allocatable capacity and CNI/EC2 allocation. Do not assume the aws-node container includes curl; use the documented introspection/debug path for the installed build and selected node.

</details>

7. How are security groups assigned to selected Pods on conventional EKS EC2 nodes?

<details>
<summary>Show Answer</summary>

Security Groups for Pods uses a **trunk ENI on the node and branch ENIs for selected Pods**. The EKS VPC resource controller creates/manages that path using permissions on the **cluster IAM role**, including `AmazonEKSVPCResourceController`; these are not simply per-Pod ServiceAccount permissions.

For the conventional Linux EC2 example, verify a trunking-compatible instance type (not every Nitro type qualifies), a compatible VPC CNI and `ENABLE_POD_ENI=true` through its configuration owner. Review `POD_SECURITY_GROUP_ENFORCING_MODE`, DNS/probes, routes and SG rules. Strict and standard modes differ in SNAT and which SGs apply, especially outside the VPC and on node-local paths.

Create a dedicated `sgp-lab` namespace and replace the SG placeholder with an approved group in the correct VPC. This controller-managed sleeping client demonstrates selection, not successful database access:

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: db-client-policy
  namespace: sgp-lab
spec:
  podSelector:
    matchLabels: {role: db-client}
  securityGroups:
    groupIds: [sg-REPLACE_WITH_APPROVED_GROUP]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: db-client
  namespace: sgp-lab
spec:
  replicas: 1
  selector:
    matchLabels: {role: db-client}
  template:
    metadata:
      labels: {role: db-client}
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: client
        image: public.ecr.aws/docker/library/busybox:1.37.0
        command: [sleep, '3600']
        resources:
          requests: {cpu: 10m, memory: 16Mi}
          limits: {cpu: 100m, memory: 32Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
```
Use either a podSelector or serviceAccountSelector as appropriate. Verify the newly created Pod, CNINode/branch capacity and allowed/denied application connections. Changing SecurityGroupPolicy selection does not retrofit running Pods; separate SG rule changes have their own connection-tracking behavior. Host-network Pods use node networking.

Prefix delegation is compatible but does not enlarge branch-ENI Pod capacity. The traditional SecurityGroupPolicy feature is not the Auto Mode NodeClass Pod-subnet/SG selection feature; follow the applicable compute-specific API instead of treating them as identical.

</details>

8. Which load balancer does AWS Load Balancer Controller create for a LoadBalancer Service, and how is ownership configured?

<details>
<summary>Show Answer</summary>

AWS Load Balancer Controller reconciles a LoadBalancer Service to an **NLB**, not a CLB. The old quiz mixed it with the legacy in-tree service controller. Current LBC uses `service.k8s.aws/nlb` for explicit ownership and has defaulted new NLBs to **internal** since v2.2. Configure the intended scheme explicitly.

This is a new Service for an existing reviewed `app=echo` workload in `lb-lab`, after installing/authorizing the controller and validating eligible subnets/SG rules. It provisions a billable internal NLB; do not apply it casually to a production namespace:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: echo-nlb
  namespace: lb-lab
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  allocateLoadBalancerNodePorts: false
  selector: {app: echo}
  ports:
  - name: http
    port: 8080
    targetPort: 8080
    protocol: TCP
```
IP targets send traffic to eligible Pod IPs; instance targets use node/NodePort paths. The example disables unused NodePort allocation for IP mode. Auto Mode uses its own ownership class (`eks.amazonaws.com/nlb`) and supported configuration set. Do not mutate controller-selection annotations/classes on an existing legacy Service to attempt an unreviewed migration; this can leak or expose resources.

**Configuration choices** must match the selected controller version and listener design: Annotation names in the table omit the common `service.beta.kubernetes.io/` prefix.

| Requirement | Current configuration / consideration |
| --- | --- |
| Internal or public scheme | `aws-load-balancer-scheme: internal` or `internet-facing`; routes/subnets must match |
| IP targets | `aws-load-balancer-nlb-target-type: ip` |
| Custom frontend SGs | `aws-load-balancer-security-groups`; review backend rule management and health-check paths |
| Explicit subnets | `aws-load-balancer-subnets`; still subject to eligibility/AZ/IP constraints |
| Cross-zone behavior | `aws-load-balancer-attributes` with `load_balancing.cross_zone.enabled`; evaluate availability, topology and cost |
| Legacy S3 access logs | `aws-load-balancer-attributes` with `access_logs.s3.*`; NLB access logs cover TLS requests only and need the reviewed bucket/delivery permissions |
| TLS termination | `aws-load-balancer-ssl-cert` and matching Service listener ports via `aws-load-balancer-ssl-ports`; this is NLB TLS termination, not ALB HTTP routing |

The old `aws-load-balancer-internal`, cross-zone and access-log annotations are deprecated in favor of scheme/attribute settings. Current NLB also offers enhanced CloudWatch log delivery; select its documented integration rather than assuming S3 annotations configure it. Access logs are best effort, not a complete request ledger.
**ALB alternative:** use an Ingress with a configured `alb` IngressClass and IP targets to a ClusterIP backend. This avoids accidentally creating both an NLB and ALB for the same example backend:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: echo-backend
  namespace: lb-lab
spec:
  type: ClusterIP
  selector: {app: echo}
  ports:
  - {port: 8080, targetPort: 8080, protocol: TCP}
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: echo-alb
  namespace: lb-lab
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
spec:
  ingressClassName: alb
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: echo-backend
            port: {number: 8080}
```
Before installation, prepare the controller ServiceAccount and scoped IAM permissions. The reviewed chart 3.5.0 contains controller v3.5.0; region/VPC are explicit for environments where IMDS discovery is unavailable. Render and inspect before deployment:

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
helm template aws-load-balancer-controller eks/aws-load-balancer-controller \
  --version 3.5.0 --kube-version 1.36.0 --namespace kube-system \
  --set-string clusterName="${EXAMPLE_CLUSTER:?}" \
  --set-string region="${EXAMPLE_REGION:?}" --set-string vpcId="${EXAMPLE_VPC_ID:?}" \
  --set serviceAccount.create=false --set-string serviceAccount.name=aws-load-balancer-controller \
  > lbc-reviewed.yaml
```
| Capability | CLB (legacy) | NLB | ALB |
| --- | --- | --- | --- |
| Main routing layer | L4/L7 legacy listeners | L4 | HTTP/HTTPS L7 |
| Direct IP targets | No | Yes | Yes |
| Per-AZ static address option | No | Yes | No native static frontend IP |
| HTTP path routing | No | No | Yes |

NLB currently supports TCP, TLS, UDP, TCP_UDP, QUIC and TCP_QUIC listeners. Controller support/configuration must be checked separately (LBC 3.5 documents QUIC port annotations). The old qualitative “good/very good” performance table was not a benchmark. Choose and measure against the application; neither universal cross-zone enablement nor a blanket latency ranking is a production rule.

</details>

## Hands-on Questions

9. Implement and validate same-namespace traffic with a DNS exception and blocked cross-namespace TCP paths.

<details>
<summary>Show Answer</summary>

Use a policy selecting all Pods in the intended namespace, allowing same-namespace peers plus an explicit DNS exception. This is L3/L4 policy, not proof of complete tenant or node isolation.

**Prerequisites:** an approved conventional IPv4 Linux test cluster with native VPC CNI NetworkPolicy already enabled through its supported owner/configuration, controller-managed test Pods, working CoreDNS and no conflicting organization-wide policy. Do not install Calico or toggle an invented `ENABLE_NETWORK_POLICY` variable as part of this lab.

Create two new namespaces and record their UIDs. Use one Bash session for the following snippets:

```bash
set -euo pipefail
umask 077
: "${EXAMPLE_KUBECONFIG:?Use the reviewed IPv4 Linux lab cluster kubeconfig}"
NP_LAB_DIR=$(mktemp -d /tmp/eks-network-policy.XXXXXX)
NP_LAB_ID="$(date +%s)-$$"
NP_NAMESPACE_A="np-a-$NP_LAB_ID"
NP_NAMESPACE_B="np-b-$NP_LAB_ID"
for ns in "$NP_NAMESPACE_A" "$NP_NAMESPACE_B"; do
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" create namespace "$ns" -o json \
    > "$NP_LAB_DIR/$ns-created.json"
  jq -e '.metadata.uid | type == "string" and length > 0' \
    "$NP_LAB_DIR/$ns-created.json" >/dev/null
done
```
The HTTP servers also provide a known Python TCP diagnostic. Each Service and container use port 8080. These are test workloads, not production sizing; record image digests for repeatability.

```bash
for ns in "$NP_NAMESPACE_A" "$NP_NAMESPACE_B"; do
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$ns" create -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: network-probe
spec:
  replicas: 1
  selector:
    matchLabels: {app: network-probe}
  template:
    metadata:
      labels: {app: network-probe}
    spec:
      automountServiceAccountToken: false
      nodeSelector: {kubernetes.io/os: linux}
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: probe
        image: python:3.13-alpine
        command: [python, -m, http.server, "8080", --directory, /tmp]
        ports:
        - containerPort: 8080
        readinessProbe:
          tcpSocket: {port: 8080}
        resources:
          requests: {cpu: 50m, memory: 64Mi}
          limits: {cpu: 200m, memory: 128Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
---
apiVersion: v1
kind: Service
metadata:
  name: network-probe
spec:
  type: ClusterIP
  selector: {app: network-probe}
  ports:
  - {port: 8080, targetPort: 8080, protocol: TCP}
EOF
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$ns" \
    rollout status deployment/network-probe --timeout=180s
done
```
**Baseline:** require same-namespace and cross-namespace TCP connections to succeed before applying a policy. DNS/exec failures are different from denied TCP connections. ICMP ping is not a portable NetworkPolicy enforcement test.

```bash
check_tcp() {
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$1" exec deployment/network-probe \
    -c probe -- python -c '
import socket, sys
try:
    address = socket.gethostbyname(sys.argv[1])
except OSError as error:
    print("DNS failed:", error, file=sys.stderr)
    sys.exit(43)
try:
    connection = socket.create_connection((address, 8080), timeout=3)
    connection.close()
except OSError as error:
    print("TCP failed:", error, file=sys.stderr)
    sys.exit(42)
print("TCP succeeded")
' "network-probe.$2"
}

# All four paths must work before applying the policy.
check_tcp "$NP_NAMESPACE_A" "$NP_NAMESPACE_A"
check_tcp "$NP_NAMESPACE_B" "$NP_NAMESPACE_B"
check_tcp "$NP_NAMESPACE_A" "$NP_NAMESPACE_B"
check_tcp "$NP_NAMESPACE_B" "$NP_NAMESPACE_A"
```
**Apply to namespace A only:** an empty peer podSelector selects Pods in that policy namespace. The DNS peer combines the kube-system namespace with the CoreDNS Pod label. Adapt it for NodeLocal DNSCache or other DNS paths. Standard policy attachment is asynchronous, so test propagation with positive controls and both blocked directions:

```bash
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NP_NAMESPACE_A" create -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: namespace-boundary
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - podSelector: {}
  egress:
  - to:
    - podSelector: {}
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - {protocol: UDP, port: 53}
    - {protocol: TCP, port: 53}
EOF

expect_tcp_block() {
  if check_tcp "$1" "$2"; then
    return 1
  else
    result=$?
    [ "$result" -eq 42 ] || {
      printf '%s\n' 'DNS or exec failure is not proof of policy denial.' >&2
      exit 1
    }
    return 0
  fi
}
NP_VERIFIED=false
for attempt in $(seq 1 30); do
  check_tcp "$NP_NAMESPACE_A" "$NP_NAMESPACE_A"
  check_tcp "$NP_NAMESPACE_B" "$NP_NAMESPACE_B"
  if expect_tcp_block "$NP_NAMESPACE_A" "$NP_NAMESPACE_B" &&
     expect_tcp_block "$NP_NAMESPACE_B" "$NP_NAMESPACE_A"; then
    # Repeat positive controls after observing both blocked cross-namespace paths.
    check_tcp "$NP_NAMESPACE_A" "$NP_NAMESPACE_A"
    check_tcp "$NP_NAMESPACE_B" "$NP_NAMESPACE_B"
    NP_VERIFIED=true
    break
  fi
  sleep 2
done
[ "$NP_VERIFIED" = true ] || {
  printf '%s\n' 'Expected policy behavior was not observed; inspect the enforcement path.' >&2
  exit 1
}
```
Success means the tested TCP paths behaved as expected while DNS and server availability checks passed. It does not prove every protocol/interface is filtered. Preserve the platform’s node, metadata-service and security-group controls separately.

**Extensions:** to allow only particular same-namespace Pods or ports, replace/review the broad same-namespace allowances. Adding a narrower policy cannot remove an existing broad allow. For a reviewed external API, an additional egress policy can select the required CIDR/port; this documentation prefix is not a live destination:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-reviewed-external-api
  namespace: app-namespace
spec:
  podSelector:
    matchLabels: {app: web}
  policyTypes: [Egress]
  egress:
  - to:
    - ipBlock:
        cidr: 203.0.113.0/24
    ports:
    - {protocol: TCP, port: 443}
```
Standard NetworkPolicy does not provide an FQDN allow list. NAT/endpoint selection can affect which IP is evaluated. A blanket `0.0.0.0/0` excluding only RFC1918 ranges is neither a specific external-service rule nor complete protection for link-local metadata endpoints.

Clean up only the recorded namespaces after testing:

```bash
for ns in "${NP_NAMESPACE_A:?}" "${NP_NAMESPACE_B:?}"; do
  expected_uid=$(jq -er '.metadata.uid' "${NP_LAB_DIR:?}/$ns-created.json") || exit 1
  current_uid=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get namespace "$ns" \
    --ignore-not-found -o jsonpath='{.metadata.uid}') || exit 1
  if [ -z "$current_uid" ]; then
    continue
  elif [ "$current_uid" = "$expected_uid" ]; then
    kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" delete namespace "$ns" --wait=true || exit 1
  else
    printf '%s\n' 'Namespace UID changed; no deletion attempted for this namespace.' >&2
    exit 1
  fi
done
```

</details>

## Advanced Questions

10. Compare remedies for VPC CNI address exhaustion and distinguish node density from total address space.

<details>
<summary>Show Answer</summary>

First identify the exhausted resource: subnet addresses, contiguous prefix blocks, per-node ENI slots, branch ENIs, kubelet maxPods or compute capacity. They need different remedies. The old “prefix delegation is always the simplest solution” conclusion was too broad.

| Approach | Helps with | Important limitation |
| --- | --- | --- |
| Prefix delegation | More Pod addresses per ordinary ENI slot; allocation efficiency | Needs contiguous /28s; does not enlarge IPv4 space or branch-ENI capacity |
| Warm/minimum pool tuning | Unused preallocated addresses | Trades allocation readiness/API calls for address use |
| Custom networking | Separates node and Pod subnet demand | Same VPC/AZ requirements, routes/SGs and planned node migration |
| Additional VPC CIDRs/subnets | More allocatable address space | Overlap/quotas/routing/control-plane reconciliation must be reviewed |
| Larger new subnet ranges | Planned address growth | Existing subnets cannot simply be resized; ranges must fit associated VPC CIDRs |
| IPv6 cluster design | Removes most shared IPv4 Pod-address pressure | New-cluster/IP-family planning, supported compute/CNI and egress requirements |
| Alternative CNI | Different IPAM/routing model | Requires a supported, tested migration; not an in-place manifest toggle |
| Fargate | Delegates node/IP allocation operations | Each Pod still consumes subnet/VPC addresses; does not fix an exhausted subnet |

**Prefix mode:** ordinary IPv4 prefixes are /28 blocks, each consuming one address slot. The original “up to 5x” value is an unverified generic claim, not a benchmark; use actual instance/CNI/kubelet limits. Security groups for Pods can coexist, but branch Pods retain their own limits. Inspect fragmentation and reserve prefix space or use new subnets if needed; do not assume free individual IP count proves a contiguous block exists.

**Warm pools:** `WARM_IP_TARGET` is free-address headroom and `MINIMUM_IP_TARGET` is minimum total allocation. They can override prefix/ENI warm-target behavior. The example values 5/10 must be tuned to the workload and API-call budget:

```json
{"env":{"WARM_IP_TARGET":"5","MINIMUM_IP_TARGET":"10"}}
```
`MAX_ENI` limits the node allocation up to the EC2 instance-type ceiling; setting it to 5 does not create support for five ENIs on a type that supports fewer. Review actual allocation metrics before changing limits.

**Custom networking:** merge this configuration through the existing CNI owner after preparing same-VPC, same-AZ Pod subnets and SGs. The stable zone label is `topology.kubernetes.io/zone`, not the deprecated beta label:

```json
{
  "env": {
    "AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG": "true",
    "ENI_CONFIG_LABEL_DEF": "topology.kubernetes.io/zone"
  }
}
```

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  subnet: subnet-REPLACE_WITH_POD_SUBNET_IN_SAME_VPC_AND_AZ
  securityGroups:
  - sg-REPLACE_WITH_APPROVED_POD_GROUP
```
Create a matching ENIConfig for every used AZ. Node annotation overrides must be reviewed. Replacement nodes with the correct zone label can reuse the existing ENIConfig; they do not require recreating it every time. Existing Pods do not all change networking immediately. Validate replacement nodes and migrate with capacity, PDB and data checks.

**CIDR/subnet changes:** add eligible non-overlapping CIDRs and associated subnets through their IaC owner, then review routes, security, endpoints and discovery tags. EKS can take up to an hour to recognize a newly associated VPC CIDR for control-plane operations. Creating a /16 subnet also requires an available associated /16 range; “larger” does not bypass VPC limits.

**Alternative CNI/IPv6:** plan the complete control-plane, DNS, service/load-balancer, policy, bootstrap and rollback path. Do not apply a floating Calico overlay manifest and disable aws-node on a running cluster as a generic cutover. An existing EKS cluster’s IP family cannot simply be toggled to IPv6. Support and AWS integration depend on the specific compute/CNI mode.

**Fargate:** a namespace label does not create a profile, and `eks.amazonaws.com/v1alpha1 kind: FargateProfile` is not a built-in Kubernetes API. Use the EKS API or eksctl (or an explicitly installed supported controller). This API example requires an unused profile name, reviewed private subnets and execution role:

```bash
# New profile example; this does not create or enlarge subnet address space.
aws eks create-fargate-profile --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --fargate-profile-name "${NEW_FARGATE_PROFILE:?}" \
  --pod-execution-role-arn "${FARGATE_EXECUTION_ROLE_ARN:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --selectors '[{"namespace":"ipam-fargate"}]'
```
Create the matching namespace/workloads separately and verify profile activation. Fargate changes operational responsibility, not the finite address capacity of the chosen subnets. Compare the remedies against measured demand instead of applying every strategy together. No network migration or performance benchmark was executed in this audit.

</details>


## VPC Foundation Checks

11. Which private subnet pair is aligned and avoids public 10.0.0.0/24 and 10.0.1.0/24?
   * A) 10.0.2.0/22 and 10.0.6.0/22
   * B) 10.0.4.0/22 and 10.0.8.0/22
   * C) 10.0.0.0/22 and 10.0.1.0/22
   * D) Any two different strings

<details>
<summary>Show Answer</summary>

**Answer: B) 10.0.4.0/22 and 10.0.8.0/22**

A /22 starts on a four-value boundary in the third octet. Canonicalization of 10.0.2.0/22 produces 10.0.0.0/22, which overlaps the public ranges.

</details>

12. How many addresses can be assigned in an ordinary AWS IPv4 /24 subnet before resource use?
   * A) 256
   * B) 254
   * C) 251
   * D) Always 240

<details>
<summary>Show Answer</summary>

**Answer: C) 251**

AWS reserves the first four and last address per ordinary subnet. The total is 256 and assignable count 251; BYOIP has documented exceptions.

</details>

13. Does an elb subnet role tag create an Internet Gateway route?
   * A) Yes
   * B) No; route configuration and controller discovery are separate
   * C) Only in a private subnet
   * D) It also opens all security groups

<details>
<summary>Show Answer</summary>

**Answer: B) No; route configuration and controller discovery are separate**

Tags can influence discovery, subject to controller/version/feature gates. They do not create routes or constitute a security boundary.

</details>

14. Is a public internet path mandatory for every EKS node?
   * A) Yes, always through a NAT gateway
   * B) Yes, always through an IGW
   * C) No; required service access can use appropriate private endpoints/mirrors
   * D) No network access is needed

<details>
<summary>Show Answer</summary>

**Answer: C) No; required service access can use appropriate private endpoints/mirrors**

Plan actual API, registry, DNS and workload dependencies. The AWS EKS service endpoint is different from the Kubernetes cluster API endpoint.

</details>

15. Which is the normal kubelet destination port for control-plane traffic?
   * A) Every TCP port 1025–65535
   * B) TCP 10250
   * C) Every NodePort by default
   * D) UDP 53 only

<details>
<summary>Show Answer</summary>

**Answer: B) TCP 10250**

Review private API TCP443, DNS TCP/UDP53, actual webhook/workload ports and real SG associations separately. Stateful SG return traffic differs from stateless NACL rules.

</details>

## References

- [VPC/subnet requirements](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)
- [VPC CNI 1.23.0](https://github.com/aws/amazon-vpc-cni-k8s/blob/v1.23.0/README.md)
- [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [EKS native policies](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [LBC 3.5 Service annotations](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/service/annotations.md)
- [LBC subnet discovery](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/deploy/subnet_discovery.md)
- [NLB listeners](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)
- [NLB logs](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-access-logs.html)
- [CoreDNS cache](https://coredns.io/plugins/cache/)
- [CoreDNS cache implementation](https://github.com/coredns/coredns/blob/v1.14.7/plugin/pkg/cache/cache.go)

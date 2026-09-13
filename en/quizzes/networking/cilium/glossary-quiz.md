# Glossary Quiz

> **Review baseline**: Cilium 1.20.1.
> **Last reviewed**: September 12, 2026.

This quiz tests your understanding of key terms and concepts related to Cilium, eBPF, Kubernetes, and networking.

## Multiple Choice Questions

1. What is the full name of eBPF?

   - A) Enhanced Berkeley Packet Filter
   - B) Extended Berkeley Packet Filter
   - C) Embedded BPF Filter
   - D) External Berkeley Protocol Filter

<details>

<summary>Show Answer</summary>

**Answer: B) Extended Berkeley Packet Filter**

**Explanation:** eBPF extends classic BPF and is used for networking, tracing and other kernel hooks. The verifier checks program properties; it does not make the kernel or verifier immune to implementation bugs.

</details>

2. What is the basic unit to which network policies are applied in Cilium?

   - A) Pod
   - B) Node
   - C) Endpoint
   - D) Service

<details>

<summary>Show Answer</summary>

**Answer: C) Endpoint**

**Explanation:** A Cilium endpoint commonly corresponds to a managed Pod. Its endpoint ID is local to its agent; security identities can be shared. Use `cilium-dbg endpoint list` inside the owning agent.

</details>

3. Where does native XDP execute on a supporting network device?

   - A) L7 protocol analysis
   - B) Packet processing at network driver level
   - C) TLS encryption
   - D) DNS resolution

<details>

<summary>Show Answer</summary>

**Answer: B) Packet processing at network driver level**

**Explanation:** Native XDP executes on the receive path of a supporting driver. PASS continues into the stack; DROP, TX and REDIRECT take other actions. Generic/offloaded modes differ. Cilium service acceleration is conditional, not a universal packet-rate or built-in DDoS protection guarantee.

</details>

4. What is the name of Cilium's network observability platform?

   - A) Prometheus
   - B) Grafana
   - C) Hubble
   - D) Jaeger

<details>

<summary>Show Answer</summary>

**Answer: C) Hubble**

**Explanation:** Hubble exposes flow records, verdicts and supported protocol metrics through CLI/UI and configured integrations. Relay is not durable storage; external alerting and retention require configuration, and events can be lost.

</details>

5. What is the full name and main purpose of VXLAN?

   - A) Virtual Extended LAN - Virtual network creation
   - B) Virtual Extensible LAN - L2 overlay network
   - C) Very Extended LAN - Large-scale network expansion
   - D) Variable Extensible LAN - Dynamic network configuration

<details>

<summary>Show Answer</summary>

**Answer: B) Virtual Extensible LAN - L2 overlay network**

**Explanation:** VXLAN carries an L2 overlay over an IP underlay using UDP and a 24-bit VNI. The field has about 16 million possible values; this is not a Cilium capacity promise. Cilium also carries identity information in overlay metadata.

</details>

6. What is the main role of BPF Maps?

   - A) Network routing table management
   - B) Data sharing and storage between eBPF programs
   - C) DNS record caching
   - D) TLS certificate storage

<details>

<summary>Show Answer</summary>

**Answer: B) Data sharing and storage between eBPF programs**

**Explanation:** BPF maps share kernel-managed state/events with programs and userspace. Hash/array maps use keys, while ring buffers and some other map types do not support ordinary lookup/update/delete operations.

</details>

7. What is the numeric identifier representing a pod's security identity in Cilium called?

   - A) Pod ID
   - B) Security Context
   - C) Identity
   - D) Endpoint ID

<details>

<summary>Show Answer</summary>

**Answer: C) Identity**

**Explanation:** Security-relevant labels determine identity; not every metadata label participates. Endpoints can share an identity within its allocation scope. The numeric endpoint ID is agent-local and is a different identifier.

</details>

8. What is the full name of IPAM and its role in Cilium?

   - A) IP Address Management - IP address allocation and management
   - B) Internet Protocol Access Manager - Internet access management
   - C) IP Assignment Module - IP assignment module
   - D) Internal Protocol Address Mapper - Internal protocol address mapping

<details>

<summary>Show Answer</summary>

**Answer: A) IP Address Management - IP address allocation and management**

**Explanation:** IPAM allocates and tracks addresses. Cilium supports mode-specific ownership such as cluster-pool, multi-pool, Kubernetes host-scope and ENI. GKE is a platform, not a universal standalone ipam.mode value; check the managed-platform integration.

</details>

9. What is the main characteristic of WireGuard and its use in Cilium?

   - A) Packet capture tool - Network analysis
   - B) Modern VPN protocol - Inter-node traffic encryption
   - C) Load balancing algorithm - Traffic distribution
   - D) DNS proxy - Name resolution

<details>

<summary>Show Answer</summary>

**Answer: B) Modern VPN protocol - Inter-node traffic encryption**

**Explanation:** Cilium WireGuard protects supported cross-node traffic. Same-node Pod traffic does not traverse its node tunnel, and external/node traffic has separate conditions. It is not always faster than IPsec; compare equivalent workloads and protection settings.

</details>

10. What is the full name and role of CNI?

    - A) Container Network Interface - Standard interface for container network plugins
    - B) Cloud Native Infrastructure - Cloud native infrastructure
    - C) Cluster Network Integration - Cluster network integration
    - D) Container Node Interconnect - Container node connection

<details>

<summary>Show Answer</summary>

**Answer: A) Container Network Interface - Standard interface for container network plugins**

**Explanation:** CNI specifies the interface between the runtime and network plugins. In current Kubernetes, kubelet uses CRI and the container runtime manages CNI invocation. kubelet's direct CNI management flags were removed in Kubernetes 1.24.

</details>

## Short Answer Questions

11. What is the name of the open-source component that provides L7 proxy and service mesh functionality in Cilium?

<details>

<summary>Show Answer</summary>

**Answer:** Envoy

**Explanation:** Envoy provides configured HTTP/gRPC proxy functions. DNS policy uses Cilium's DNS proxy, and Kafka L7 rules were removed. The proxy's deployment/lifecycle follows the installation configuration, not one automatic proxy deployment per arbitrary L7 rule.

</details>

12. What is the name of the Cilium component that runs on each node and is responsible for eBPF program loading, network policy implementation, and endpoint management?

<details>

<summary>Show Answer</summary>

**Answer:** Cilium Agent

**Explanation:** The agent manages node-local endpoints, BPF programs and policy/datapath state on eligible Cilium-managed nodes. IPAM responsibilities are split between the agent, operator and/or platform according to mode.

</details>

13. What is the name and number of the OSI model layer responsible for packet routing using IP addresses?

<details>

<summary>Show Answer</summary>

**Answer:** L3 (Network Layer)

**Explanation:** L3 (Network Layer) is the 3rd layer of the OSI model, responsible for logical addressing using IP addresses and packet routing. IP (Internet Protocol) and ICMP (Internet Control Message Protocol) operate at this layer. Cilium L3 policies can filter traffic based on IP addresses and CIDR blocks. L2 (Data Link Layer) uses MAC addresses, and L4 (Transport Layer) uses port numbers.

</details>

14. What is the name of the Kubernetes resource that provides stable network endpoints for a set of pods?

<details>

<summary>Show Answer</summary>

**Answer:** Service

**Explanation:** Service provides a logical backend access abstraction. Ordinary ClusterIP Services have a virtual IP, headless Services do not, and ExternalName uses DNS aliasing. Selectorless Services can represent manually managed or external endpoints.

</details>

15. What is the name of the NAT type that modifies the source IP address of a packet?

<details>

<summary>Show Answer</summary>

**Answer:** SNAT (Source Network Address Translation)

**Explanation:** SNAT changes the source address. Masquerading chooses an address associated with the outgoing path/interface; exclusions and selected gateway IPs matter. Not every outbound Pod packet is necessarily translated. DNAT changes the destination.

</details>

## Hands-on Questions

16. Match ClusterMesh, CRD, FQDN and mTLS to their definitions.

<details>

<summary>Show Answer</summary>

**Answer:**

- **ClusterMesh**: Cross-cluster network metadata/connectivity; it does not automatically replicate all policy resources.
- **CRD**: A definition that adds a custom resource kind to the Kubernetes API.
- **FQDN**: An absolute name in the DNS tree. toFQDNs permits learned IPs.
- **mTLS**: TLS with mutual peer authentication. Authentication is distinct from application authorization.

</details>


17. Query CRD-allocated identities and filter the real security labels; distinguish the agent's local view.

<details>

<summary>Show Answer</summary>

**Answer:**

```bash
set -euo pipefail
kubectl get ciliumidentities -o json > identities.json
jq '.items[]
| select(.["security-labels"]["k8s:app"] == "frontend")
| {id: .metadata.name, labels: .["security-labels"]}' identities.json
: "${CILIUM_POD:?Select the Cilium agent Pod on the node being inspected}"
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg identity list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint list
```

This assumes CRD allocation mode. CiliumIdentity is cluster-scoped and `security-labels` is the source of truth, distinct from `metadata.labels`. Reserved/node-local identities are not all represented as CRDs. The agent view has a different scope. Set `CILIUM_POD` using the [target-node selection procedure](../../../networking/cilium/07-advanced-topics.md).

</details>


18. Inspect the selected agent's service, CT, NAT, policy and endpoint maps.

<details>

<summary>Show Answer</summary>

**Answer:**

```bash
set -eu
: "${CILIUM_POD:?Select the Cilium agent Pod on the node being inspected}"
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf lb list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf lb list --backends
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf ct list global
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf nat list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf policy get --all
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf endpoint list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg map list
```

Select the owning node's agent first. `--backends` and policy-map `--all` are valid flags. Full CT/policy dumps can be large, so use them deliberately on the affected node. `map list` lists the agent's open maps; it is not an exhaustive kernel-map inventory or proof of every active application connection.

</details>


19. Write a policy allowing TCP 443 to IPs learned for api.example.com and one-level *.googleapis.com names, with a DNS exception. State its limits.

<details>

<summary>Show Answer</summary>

**Answer:**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: fqdn-egress-policy
  namespace: cilium-glossary-demo
spec:
  endpointSelector:
    matchLabels:
      app: external-client
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
      rules:
        dns:
        - matchPattern: '*'
  - toFQDNs:
    - matchName: api.example.com
    - matchPattern: '*.googleapis.com'
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

This is a policy-only exercise. Prepare the namespace, labeled client and actual CoreDNS path separately. It allows TCP/UDP DNS and DNS proxy observation. `*.googleapis.com` matches one subdomain level, not the apex or `a.b.googleapis.com`. DNS `*` permits all query names. toFQDNs produces IP allowances, not an HTTPS Host constraint on shared IPs or remote-server authentication. Check overlapping allow policies and TLS validation.

</details>


20. Compare Operator and Agent responsibilities and inspect Operator status.

<details>

<summary>Show Answer</summary>

**Answer:**

```bash
kubectl -n kube-system get deployment cilium-operator
kubectl -n kube-system get pods -l name=cilium-operator
kubectl -n kube-system logs -l name=cilium-operator -c cilium-operator --prefix --since=10m --tail=100
cilium status --verbose
kubectl get ciliumidentities
kubectl get ciliumendpoints --all-namespaces
```

| Component | Scope and responsibilities |
| --- | --- |
| Agent | Managed node endpoints, BPF programs, policy/datapath state and mode-dependent local IPAM work. |
| Operator | Cluster-level CRD registration, mode-dependent IPAM/LB IPAM, orphan/identity collection and enabled Ingress/Gateway translation. |

`name=cilium-operator` is valid in the current chart. `operator.replicas` is configurable beyond one or two instances. Agents create identities by default; operator identity management is a separate Beta mode. Enabled features can also add ClusterMesh EndpointSlice/MCS synchronization, so responsibilities should not be treated as one unconditional list.

</details>


***

[Return to Learning Materials](../../../networking/cilium/glossary.md) | [Cilium Quiz List](../../README.md#cilium)

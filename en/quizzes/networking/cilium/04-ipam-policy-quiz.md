# Cilium IPAM and Network Policy Quiz

> **Cilium 1.20.1 · 2026-09-12**

## IPAM

1. **Without a platform override, what is the generic default IPAM mode and allocation model?**
   - A) kubernetes; every Pod asks the Kubernetes API for an IP
   - B) cluster-pool; the Operator assigns node CIDRs and agents allocate local Pod IPs
   - C) crd; every Pod creates a CiliumPodIPPool
   - D) eni on every platform

   <details>
   <summary>Show Answer</summary>

   **Answer: B) cluster-pool; the Operator assigns node CIDRs and agents allocate local Pod IPs**

   Cluster-pool uses CiliumNode node-prefix allocation. It is not a central address request for every Pod, and platform profiles can choose another backend.

   </details>

2. **Which mode obtains node prefixes from Kubernetes Node state rather than Cilium Operator cluster-pool allocation?**
   - A) cluster-pool
   - B) kubernetes (host scope)
   - C) multi-pool only
   - D) eni only

   <details>
   <summary>Show Answer</summary>

   **Answer: B) kubernetes (host scope)**

   Kubernetes supplies the required node CIDRs and the agent allocates within them. Both host scope and cluster-pool allocate individual addresses locally; neither eliminates prefix coordination.

   </details>

3. **Which backend applies when Cilium itself manages AWS ENIs and VPC addresses on a prepared EC2-node installation?**
   - A) kubernetes
   - B) cluster-pool
   - C) eni
   - D) delegated-plugin for all AWS nodes

   <details>
   <summary>Show Answer</summary>

   **Answer: C) eni**

   This is ENI IPAM. AWS VPC CNI chaining keeps IP allocation with AWS VPC CNI; Hybrid Nodes use a separate path, and Fargate/Auto Mode do not support this replacement configuration.

   </details>

4. **Which Kubernetes fields are relevant to host-scope IPAM?**
   - A) Node.spec.podCIDRs and the legacy/single-family Node.spec.podCIDR
   - B) Node.spec.subnet
   - C) Service.spec.podCIDR
   - D) CiliumPodIPPool.spec.selector

   <details>
   <summary>Show Answer</summary>

   **Answer: A) Node.spec.podCIDRs and the legacy/single-family Node.spec.podCIDR**

   These are Kubernetes Node fields. Cluster-pool instead uses CiliumNode.spec.ipam.podCIDRs; the authoritative state depends on the selected mode.

   </details>

5. **How should effective IPAM configuration be investigated?**
   - A) Treat any grep line containing ipam as complete configuration
   - B) Use only Pod readiness
   - C) Always use the first CiliumNode address and CIDR
   - D) Compare desired values/node overrides and actual agent/operator state with the selected allocator's resource

   <details>
   <summary>Show Answer</summary>

   **Answer: D) Compare desired values/node overrides and actual agent/operator state with the selected allocator's resource**

   Helm/ConfigMap values, node overrides and allocation status are complementary. CiliumNode is not the universal authority for every IPAM mode, and an address's array position does not establish a next hop.

   </details>

## Policy Basics

6. **What is the resource API version for CiliumNetworkPolicy in this guide?**
   - A) networking.k8s.io/v1
   - B) cilium.io/v1
   - C) cilium.io/v2
   - D) policy.cilium.io/v1

   <details>
   <summary>Show Answer</summary>

   **Answer: C) cilium.io/v2**

   CiliumNetworkPolicy uses cilium.io/v2. Do not confuse it with the CiliumPodIPPool v2alpha1 API or ordinary Kubernetes NetworkPolicy.

   </details>

7. **What does endpointSelector select in a namespaced CiliumNetworkPolicy?**
   - A) The subject endpoints in that namespace
   - B) A Kubernetes Service to create
   - C) Host nodes in any namespace
   - D) Other policies to inherit

   <details>
   <summary>Show Answer</summary>

   **Answer: A) The subject endpoints in that namespace**

   It selects endpoints to which the policy applies. Resource scope and selectors are separate from the traffic peers described in ingress/egress.

   </details>

8. **What does an ingress rule describe?**
   - A) Traffic into selected endpoints
   - B) Traffic out of selected endpoints
   - C) A new IP pool
   - D) A route advertisement

   <details>
   <summary>Show Answer</summary>

   **Answer: A) Traffic into selected endpoints**

   Ingress is relative to the selected subject endpoint. Apply the corresponding peer, port and supported protocol constraints.

   </details>

9. **What does an egress rule describe?**
   - A) Traffic into selected endpoints
   - B) Traffic out of selected endpoints
   - C) All traffic everywhere
   - D) Only traffic from outside Kubernetes

   <details>
   <summary>Show Answer</summary>

   **Answer: B) Traffic out of selected endpoints**

   Egress controls outgoing traffic from the selected endpoint. Preserve necessary DNS and application dependencies deliberately.

   </details>

10. **What are optional Cilium rule spec.labels used for?**
    - A) Selecting subject Pods instead of endpointSelector
    - B) Rule identification and metadata
    - C) Inheriting any policy with the same labels
    - D) Allocating Pod IPs

    <details>
    <summary>Show Answer</summary>

    **Answer: B) Rule identification and metadata**

    Rule labels can support identification/lookups and are not required to be unique. They do not reference or inherit other policies; Kubernetes metadata.labels labels the resource itself.

    </details>

## Peer Selection

11. **What is the purpose and default boundary of toCIDR/toCIDRSet?**
    - A) IP-prefix selection, primarily for external peers; managed Pod/node matching has documented default limits
    - B) HTTP URL filtering
    - C) Automatic Service creation
    - D) Allocation of addresses from those prefixes

    <details>
    <summary>Show Answer</summary>

    **Answer: A) IP-prefix selection, primarily for external peers; managed Pod/node matching has documented default limits**

    Use endpoint selectors for ordinary managed-Pod policy. The release documents opt-in beta CIDR matching for pods/nodes with identity-consumption implications; default behavior must not be described as an unconditional IP matcher.

    </details>

12. **What does toFQDNs authorize?**
    - A) Every DNS query automatically
    - B) Any HTTP URL under the domain
    - C) Traffic to IPs learned for selected names, subject to the policy's ports and constraints
    - D) Only statically configured IPs

    <details>
    <summary>Show Answer</summary>

    **Answer: C) Traffic to IPs learned for selected names, subject to the policy's ports and constraints**

    A separate DNS proxy rule provides name-to-IP observation. Port53 permission alone does not enable that learning, and IP allowance is not an HTTP hostname or application-user authorization check.

    </details>

13. **What does the world entity represent?**
    - A) All local and remote Pods without distinction
    - B) A broad outside-cluster identity category
    - C) Only control-plane nodes
    - D) Only public Internet addresses

    <details>
    <summary>Show Answer</summary>

    **Answer: B) A broad outside-cluster identity category**

    World can include private external peers and is not the all entity or a named remote-cluster selector. Use explicit peers and narrower rules when required.

    </details>

14. **How does toServices work?**
    - A) It resolves Kubernetes Service selectors or selectorless EndpointSlice addresses into policy selectors
    - B) It creates a Service and routes automatically
    - C) It makes all DNS names reachable
    - D) It is a replacement for all kube-apiserver entity rules

    <details>
    <summary>Show Answer</summary>

    **Answer: A) It resolves Kubernetes Service selectors or selectorless EndpointSlice addresses into policy selectors**

    Selectorless Services use CIDR-derived selectors and inherit their limits. The special default/kubernetes Service should not be assumed to behave like an ordinary workload selector.

    </details>

15. **Where is nodeSelector used to select host-firewall subjects?**
    - A) In any namespaced CiliumNetworkPolicy without prerequisites
    - B) In CiliumClusterwideNetworkPolicy with host firewall configured
    - C) In CiliumPodIPPool to allocate every Pod IP
    - D) In Service annotations

    <details>
    <summary>Show Answer</summary>

    **Answer: B) In CiliumClusterwideNetworkPolicy with host firewall configured**

    The Rule API restricts nodeSelector to CiliumClusterwideNetworkPolicy. It is distinct from endpointSelector and from fromNodes/toNodes peer selection.

    </details>

## L7 Policy

16. **Which HTTP request attributes can supported Cilium L7 rules constrain?**
    - A) Path
    - B) Method
    - C) Headers
    - D) All of the above

    <details>
    <summary>Show Answer</summary>

    **Answer: D) All of the above**

    Envoy applies the rules to visible HTTP traffic. A separate unrestricted L4 allow can bypass overlapping L7 restrictions; policy allowance also does not guarantee application success.

    </details>

17. **What is true about rules.kafka in Cilium1.20.1?**
    - A) It provides topic authorization by default
    - B) It is enabled by changing apiVersion to v2alpha1
    - C) It automatically encrypts the broker connection
    - D) The built-in Kafka L7 API is removed; use appropriate network controls and broker authorization

    <details>
    <summary>Show Answer</summary>

    **Answer: D) The built-in Kafka L7 API is removed; use appropriate network controls and broker authorization**

    Do not apply the obsolete topic/API-key/client-ID policy. Use the broker's actual listener port for L4 connectivity and its native authentication/authorization facilities.

    </details>

18. **Which wildcard statement matches the release's implementation?**
    - A) `*.example.com` also matches example.com and a.b.example.com
    - B) `*.example.com` matches one subdomain label; `**.example.com` matches one or more levels, and both exclude the apex
    - C) Every asterisk always matches dots
    - D) matchName and matchPattern allocate DNS addresses

    <details>
    <summary>Show Answer</summary>

    **Answer: B) `*.example.com` matches one subdomain label; `**.example.com` matches one or more levels, and both exclude the apex**

    The implementation anchors the normalized DNS name. Exact names, one-label wildcards and the multi-level prefix have different meanings; a separate matchName can include the apex.

    </details>

19. **How are supported gRPC service/method and metadata constraints expressed?**
    - A) A rules.grpc protobuf-field filter
    - B) Only an L3 CIDR match
    - C) HTTP/2 path and header matching through the supported Envoy path
    - D) By replacing the CNI with kube-proxy

    <details>
    <summary>Show Answer</summary>

    **Answer: C) HTTP/2 path and header matching through the supported Envoy path**

    gRPC service/method names appear in its HTTP/2 path and metadata in headers. This is not arbitrary protobuf-payload inspection, and TLS visibility still matters.

    </details>

20. **Which component distinction is correct?**
    - A) kube-proxy enforces all L7 rules
    - B) Envoy handles supported HTTP/gRPC rules; Cilium's DNS proxy handles DNS policy
    - C) NGINX Ingress is mandatory for DNS policy
    - D) All L7 parsers run only in kernel BPF

    <details>
    <summary>Show Answer</summary>

    **Answer: B) Envoy handles supported HTTP/gRPC rules; Cilium's DNS proxy handles DNS policy**

    The DNS proxy is in-agent by default, with a separately documented alpha standalone mode. Do not require Envoy for every DNS rule or assume encryption makes payloads visible.

    </details>

[Review the guide](../../../networking/cilium/04-ipam-policy.md).

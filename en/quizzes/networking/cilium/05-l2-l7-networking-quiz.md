# Cilium L2–L7 Networking and Load Balancing Quiz

> **Cilium 1.20.1 · CLI 0.20.0 · 2026-09-12**

## Multiple Choice Questions

1. **Which conceptual OSI layer contains HTTP, DNS and gRPC application behavior?**
   - A) L1
   - B) L2
   - C) L3
   - D) L7

   <details>
   <summary>Show Answer</summary>

   **Answer: D) L7**

   Application protocols map to L7 conceptually. This does not imply that Cilium has a native policy parser for every application protocol; Kafka L7 rules are removed.

   </details>

2. **What is the direct-return property of DSR?**
   - A) It encrypts every response
   - B) A remote backend can reply without returning through the ingress load-balancing node
   - C) It authenticates client IPs
   - D) It restores client IPs already rewritten by an upstream proxy

   <details>
   <summary>Show Answer</summary>

   **Answer: B) A remote backend can reply without returning through the ingress load-balancing node**

   The network must support the asymmetric return path. DSR can reduce a response-path hop; performance and client-IP preservation depend on the actual topology.

   </details>

3. **Which component handles supported Cilium HTTP/gRPC policy?**
   - A) kube-proxy
   - B) Hubble Relay
   - C) Envoy
   - D) CoreDNS

   <details>
   <summary>Show Answer</summary>

   **Answer: C) Envoy**

   Envoy deployment depends on the installation values. DNS policy uses Cilium's DNS proxy, and declaring an unsupported Kafka rule does not install a Kafka parser.

   </details>

4. **Which pair describes Cilium's documented BPF service backend-selection algorithms?**
   - A) Round Robin and Least Connection
   - B) Random and Maglev
   - C) Source-IP Hash and Weighted Response Time
   - D) Every Envoy algorithm

   <details>
   <summary>Show Answer</summary>

   **Answer: B) Random and Maglev**

   BPF selection and Envoy L7 load balancing are different components. Maglev is supported on specified external paths; ordinary socket-LB E–W traffic is not subject to it.

   </details>

5. **Which statement about masquerading implementations is correct?**
   - A) BPF is always faster for every workload
   - B) Every Linux kernel supports current Cilium
   - C) Both implementations operate in the kernel and have configuration/platform requirements
   - D) Selecting BPF removes routing requirements

   <details>
   <summary>Show Answer</summary>

   **Answer: C) Both implementations operate in the kernel and have configuration/platform requirements**

   Neither a product name nor kernel execution alone establishes a performance result. BPF masquerading in this release has feature/device dependencies, and IPv6 support is beta.

   </details>

6. **Which current value enables kube-proxy replacement?**
   - A) kubeProxyReplacement: partial
   - B) kubeProxyReplacement: true
   - C) kubeProxyReplacement: strict
   - D) kubeProxyReplacement: hybrid

   <details>
   <summary>Show Answer</summary>

   **Answer: B) kubeProxyReplacement: true**

   Use the boolean/current true value and the full replacement prerequisites, including API reachability. The old strict/partial vocabulary is not the current contract.

   </details>

7. **Which is not a built-in Cilium HTTP policy predicate?**
   - A) Method
   - B) Path
   - C) Supported header conditions
   - D) Arbitrary request-body contents

   <details>
   <summary>Show Answer</summary>

   **Answer: D) Arbitrary request-body contents**

   Method/path expressions and supported header conditions differ. A valued headers string is literal, not a general header-value regex. Payload inspection requires a separately designed application/proxy facility.

   </details>

8. **What is the intended Cilium/Istio integration model in the guide?**
   - A) Automatically bypass Istio's sidecars
   - B) Preserve Istio interception and combine Cilium network controls with Istio L7/mTLS responsibility
   - C) Automatically disable mTLS
   - D) Make every Cilium HTTP rule inspect encrypted Istio traffic

   <details>
   <summary>Show Answer</summary>

   **Answer: B) Preserve Istio interception and combine Cilium network controls with Istio L7/mTLS responsibility**

   Configure CNI/socket-LB interoperability and test the topology. The example keeps Istio mTLS and uses Cilium L3/L4 policy rather than applying plaintext HTTP inspection to encrypted traffic.

   </details>

9. **What can socket-level load balancing do?**
   - A) Choose a backend before packet construction at supported socket hooks
   - B) Automatically authenticate HTTP headers
   - C) Decrypt all traffic
   - D) Create an external load balancer

   <details>
   <summary>Show Answer</summary>

   **Answer: A) Choose a backend before packet construction at supported socket hooks**

   TCP connect and supported UDP socket paths can translate a Service to a backend early. This is not a universal latency guarantee and can require special handling with sidecar interception.

   </details>

10. **Which is an appropriate fragmentation principle?**
    - A) Tracking guarantees protection from all fragment attacks
    - B) Plan the effective path MTU and verify required error signaling
    - C) All fragments must always be dropped
    - D) Cilium's MTU always means final Pod payload size

    <details>
    <summary>Show Answer</summary>

    **Answer: B) Plan the effective path MTU and verify required error signaling**

    Cilium's MTU overrides the underlying-network value. Fragment tracking preserves L4 context, not payload reassembly or an attack-prevention guarantee; PMTUD can fail when required signaling/path behavior is broken.

    </details>

## Short Answer Questions

11. **Name the current built-in L7 policy groups and explain where gRPC fits.**

<details>
<summary>Show Answer</summary>

HTTP and DNS. Supported gRPC constraints use HTTP/2 path/header matching through Envoy. DNS uses Cilium's DNS proxy; Kafka L7 rules are removed. TLS visibility must be configured rather than assumed.

</details>

12. **Distinguish Service backend readiness from a generic active health-check engine.**

<details>
<summary>Show Answer</summary>

Kubernetes endpoint/readiness state influences backend eligibility, subject to Service and termination semantics and propagation delay. It does not mean every BPF Service performs independent TCP/HTTP health probes. Cilium connectivity health, application probes and proxy health checks are different mechanisms.

</details>

13. **Which operation changes a Pod's outbound source address for an external path?**

<details>
<summary>Show Answer</summary>

Source NAT / masquerading. It is distinct from destination translation to a Service backend. The selected interface, excluded CIDRs, node exceptions and later cloud NAT can affect the observed source; successful external HTTP alone does not prove the implementation.

</details>

14. **Explain why Maglev and sessionAffinity: ClientIP are not interchangeable.**

<details>
<summary>Show Answer</summary>

Maglev provides consistent backend selection for its supported paths, using compatible tables/state/seed. ClientIP affinity maintains separate per-client Service affinity and timeout behavior, using an IP or applicable socket-LB namespace cookie. Neither preserves a session to a failed/removed backend.

</details>

15. **What is L4, and what reliability distinction matters between TCP and UDP?**

<details>
<summary>Show Answer</summary>

L4 is the transport layer. TCP provides a reliable ordered byte stream; UDP provides datagrams without delivery/order guarantees. UDP is not automatically faster for every application, and port/protocol policy does not provide application authentication.

</details>

## Hands-on Questions

16. **Write a policy for an API listening on TCP8080 in l7-exercise: allow frontend GET /api/v1/users and POST /api/v1/data only when X-Auth-Token is present.**

<details>
<summary>Show Answer</summary>

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: api-http
  namespace: l7-exercise
spec:
  endpointSelector:
    matchLabels:
      app: backend-api
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: l7-exercise
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/api/v1/users$
        - method: ^POST$
          path: ^/api/v1/data$
          headerMatches:
          - name: x-auth-token
```

The workload labels/namespace and listener are prerequisites. A name-only headerMatches entry checks presence; it does not validate a token. The old `X-Auth-Token: .*` string means a literal valued match, not any value. Inspect other applicable policies and realized proxy state.

</details>

17. **Install the documented DSR/Maglev profile on a fresh prepared kube-proxy-free IPv4 test cluster.**

<details>
<summary>Show Answer</summary>

**lb-values.yaml**

```yaml
kubeProxyReplacement: true
routingMode: tunnel
tunnelProtocol: geneve
ipv4:
  enabled: true
ipv6:
  enabled: false
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
loadBalancer:
  mode: dsr
  dsrDispatch: geneve
  algorithm: maglev
  acceleration: disabled
maglev:
  tableSize: 65521
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
l7Proxy: true
envoy:
  enabled: true
hubble:
  enabled: true
  relay:
    enabled: true
```

```bash
: "${API_SERVER_HOST:?Set the real reachable API server host}"
: "${API_SERVER_PORT:?Set its actual port}"
: "${MAGLEV_SEED:?Set the persisted base64 encoding of 12 random bytes}"
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
helm install cilium cilium/cilium --version 1.20.1 --namespace kube-system \
  --values lb-values.yaml \
  --set-string k8sServiceHost="$API_SERVER_HOST" \
  --set k8sServicePort="$API_SERVER_PORT" \
  --set-string maglev.hashSeed="$MAGLEV_SEED"
cilium status --wait
```

The profile uses Geneve overlay with Geneve DSR dispatch. API endpoint, network return path and a persisted common Maglev seed must already be prepared. 65521 is an allowed table size, not a universal requirement. Do not delete kube-proxy after an arbitrary installation or switch a running cluster's forwarding mode as a test shortcut.

</details>

18. **The requirement is orders-produce for order-service and payments-consume for payment-processor. What can current Cilium policy enforce, and what must the broker enforce?**

<details>
<summary>Show Answer</summary>

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: broker-connectivity
  namespace: messaging
spec:
  endpointSelector:
    matchLabels:
      app: kafka-broker
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: messaging
        k8s:app: order-service
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: messaging
        k8s:app: payment-processor
    toPorts:
    - ports:
      - port: '9092'
        protocol: TCP
```

This only permits the two source workloads to the assumed broker listener TCP9092; replace the port with the real configured listener. It does not enforce the topic operations. Authenticate distinct broker principals and configure the required produce/consume and consumer-group authorization in Kafka. `rules.kafka` is removed, so presenting the old YAML as complete authorization would be incorrect.

</details>

19. **Provide a BPF masquerading fragment excluding destinations in a genuinely routable 10.0.0.0/8 range.**

<details>
<summary>Show Answer</summary>

```yaml
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
ipv4NativeRoutingCIDR: 10.0.0.0/8
```

Merge this into the appropriate prepared configuration. BPF NodePort/device prerequisites and return routes still apply. ipv4NativeRoutingCIDR controls the relevant masquerade exclusion; it does not create routes or switch the routingMode. Verify selected-node `cilium-dbg status --verbose` and `cilium-dbg bpf nat list`, plus a controlled external observation.

</details>

20. **Give a non-disruptive sequence to investigate unexpected L7 policy behavior.**

<details>
<summary>Show Answer</summary>

```bash
cilium status --verbose
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
kubectl -n kube-system get pods -l k8s-app=cilium-envoy -o wide
kubectl -n cilium-l2l7-demo get pods -o wide
export APP_POD=REPLACE-WITH-APP1-POD
export CILIUM_POD=REPLACE-WITH-AGENT-ON-APP-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg endpoint get "pod-name:cilium-l2l7-demo:$APP_POD"
kubectl -n cilium-l2l7-demo get cnp -o yaml
kubectl get ccnp -o yaml
kubectl -n kube-system logs "$CILIUM_POD" -c cilium-agent --tail=100
```

For the explicitly enabled Envoy DaemonSet:

```bash
export ENVOY_POD=REPLACE-WITH-ENVOY-POD-ON-APP-NODE
kubectl -n kube-system logs "$ENVOY_POD" --all-containers=true --tail=100
```

```bash
cilium hubble port-forward
```

```bash
hubble observe --namespace cilium-l2l7-demo --protocol http --last 20
hubble observe --namespace cilium-l2l7-demo --verdict DROPPED --last 20
```

Choose agent/Envoy Pods on the workload node, not a random DaemonSet Pod. For an explicit Envoy DaemonSet, inspect that Pod's bounded logs; for embedded Envoy, inspect the agent's configured logs. Keep the Relay forward in a separate terminal. Compare desired/realized rules, plaintext/TLS visibility, application responses and flows. HTTP403 is not the same as a packet drop, and missing observations can reflect filters/loss. Removed policy trace and forced endpoint regeneration are not required first steps.

</details>

---

[Return to Learning Materials](../../../networking/cilium/05-l2-l7-networking.md) | [Next Quiz: Security and Visibility](./06-security-visibility-quiz.md)

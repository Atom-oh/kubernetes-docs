# Istio Comparison Quiz

> **Supported Versions**: Istio 1.30 / EKS 1.36
> **Last Updated**: August 21, 2026

This quiz tests your understanding of the sidecar vs. ambient mode selection criteria, especially the EKS 1.36 test results.

## Multiple Choice Questions (1-6)

### Question 1: Root cause of ambient waypoint 503s

What is the root cause of intermittent 503s on the waypoint path during rollouts in ambient mode?

A. Duplicate IP assignment when a pod restarts
B. The waypoint reuses connections keyed by destination IP:Port, and ztunnel does not notify the waypoint when a pod terminates
C. NetworkPolicy blocks waypoint traffic
D. STRICT mTLS is not supported on the waypoint

<details>
<summary>Answer & Explanation</summary>

**Answer: B**

**Explanation:**

The waypoint (Envoy) manages and reuses a connection pool keyed by destination IP:Port. ztunnel does not explicitly notify the waypoint when a target pod terminates. If the terminated pod's IP is reassigned to a new pod, the waypoint may reuse a now-invalid connection and return a 503. This is the mechanism behind the concern — **connection lifecycle management**, not duplicate IP assignment — and the measured 503 rates in §4 are consistent with it.

**References:**
- [Sidecar vs Ambient Mode Selection Guide](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Ambient Mode: Waypoint Proxy](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>

---

### Question 2: Interpreting the EKS 1.36 test results

Under a 100 qps x 600s (60,000 request) load with repeated rollouts on a dedicated single-tenant EKS 1.36 cluster, sidecar showed a 503 rate of 0.5%, ambient-L4 (no waypoint) showed zero actual 503s (but 0.3% TCP errors instead), and ambient-L7 (with waypoint) showed 2.6%. What is the correct interpretation?

A. Ambient is always more stable than sidecar
B. Routing through a waypoint produces a higher 503 rate than sidecar, but using L4 only (no waypoint) produces no actual 503s
C. Ambient-L4's TCP errors (0.3%) are the same phenomenon as the waypoint's 503s
D. The mode with the lowest socket usage is the most stable

<details>
<summary>Answer & Explanation</summary>

**Answer: B**

**Explanation:**

The data shows that "ambient" is neither universally better nor worse than sidecar — whether traffic goes through a **waypoint** is the deciding variable. Ambient-L7 (with a waypoint) had roughly 5x sidecar's 503 rate (2.6% vs 0.5%), while ambient-L4 (no waypoint) had zero actual 503s. That doesn't mean ambient-L4 is failure-free, though — it surfaced a different failure mode instead: TCP-level connection drops (0.3%), which is not the same as the waypoint forwarding a request onto a dead connection and returning a 503 (making C incorrect). Socket usage is not a stability metric, just a proxy for how often connections were re-established (making D incorrect) — in fact, ambient-L4 consumed the *most* sockets yet had zero 503s.

**References:**
- [Sidecar vs Ambient Mode Selection Guide: Zero-Downtime Rollout Results](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### Question 3: NetworkPolicy and ambient

In a cluster using port-based NetworkPolicies, traffic is not reaching ambient-mode pods. The application listens on port 8080. What is the most likely cause and fix?

A. Ambient doesn't support NetworkPolicy, so the NetworkPolicy should be removed
B. Real traffic arrives over the HBONE tunnel (TCP 15008), so the NetworkPolicy needs an inbound allow rule for 15008
C. PeerAuthentication should be changed to PERMISSIVE
D. The istio-cni DaemonSet needs to be restarted

<details>
<summary>Answer & Explanation</summary>

**Answer: B**

**Explanation:**

In ambient mode, ztunnel wraps pod traffic in an HBONE (mTLS) tunnel and delivers it on port 15008. A NetworkPolicy that only allows the application port (8080) blocks the 15008 traffic that actually arrives. The fix is to add an inbound allow rule for TCP 15008 on the target pods. Sidecar doesn't need this extra rule because the sidecar shares the same pod network namespace as the application.

**References:**
- [Sidecar vs Ambient Mode Selection Guide: NetworkPolicy](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### Question 4: Non-idempotent APIs and retry policies

Why is it recommended not to enable mesh-level retry (e.g., waypoint retry, VirtualService retries) by default on non-idempotent API paths like order creation?

A. Retry adds too much CPU overhead
B. When a waypoint forwards a request onto a dead connection and returns a 503, a retry can re-execute a request that had already completed server-side, causing duplicate execution (e.g., a duplicate order)
C. Retry is incompatible with STRICT mTLS
D. Retry is not supported in ambient mode

<details>
<summary>Answer & Explanation</summary>

**Answer: B**

**Explanation:**

A 503 is a client-visible failure, but hidden inside that failure category are cases where the request actually reached the server and finished processing — only the *response* was lost, due to a race between the connection dropping and the application completing its work. In that case, a mesh retry resends the same logical request over a different connection, and if the server doesn't guarantee idempotency, the request gets processed twice. This risk is especially severe for irreversible operations like order creation, so it's safer not to enable retry by default and to verify it separately. A follow-up test (T2) ran 300s of continuous rollout churn against both sidecar and ambient-L7 waypoint retry and found zero duplicate executions in that run — which lowers confidence that the race is *common*, but does not establish that it is *safe*, since it requires a very narrow timing window that a longer or higher-throughput test could still catch.

**References:**
- [Sidecar vs Ambient Mode Selection Guide: The Risk of Retry as a Mitigation](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### Question 5: Fairly comparing sidecar and ambient rollouts

Sidecar produced fewer client-visible 503s than ambient in a rollout test. Which experiment best determines whether that reflects an inherently more stable data plane?

A. Send only GET requests and compare final 200 counts
B. Keep the default retry on sidecar but disable retry on ambient
C. Set write-route retry to `attempts: 0` in both modes and separately record raw HTTP/TCP failures, retry counts, and final outcomes
D. Treat the mode with lower average CPU usage as more stable

<details>
<summary>Answer & Explanation</summary>

**Answer: C**

**Explanation:**

Sidecar Envoy and waypoint Envoy can hide a raw failure from the client through an L7 retry, while ztunnel is an L4 proxy that cannot interpret an HTTP 503 or replay an HTTP request. Disable write retries equivalently and record HTTP 503, TCP reset/EOF, `upstream_rq_retry`, actual upstream deliveries, and final client outcomes separately. Otherwise the test cannot distinguish "fewer failures occurred" from "retry hid more failures."

**References:**
- [Sidecar vs Ambient Mode Selection Guide: raw failure measurement](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Retry and Timeout](../../../service-mesh/istio/traffic-management/05-retry-timeout.md)

</details>

---

### Question 6: Cilium authentication and encryption

Which statement is correct for an established Cilium data plane with mutual authentication set to `required`?

A. Every application payload is automatically encrypted with workload TLS
B. Endpoint identity authentication and payload encryption are separate; confidentiality requires WireGuard/IPsec or supported native ztunnel mTLS
C. It is identical to Istio `PeerAuthentication STRICT` in implementation, maturity, and operational semantics
D. Enabling mutual authentication removes the need for CiliumNetworkPolicy

<details>
<summary>Answer & Explanation</summary>

**Answer: B**

**Explanation:**

Established Cilium mutual authentication verifies peer identity through an out-of-band handshake separate from the application data path. The authentication policy alone does not automatically encrypt payloads, so select WireGuard/IPsec separately or validate the native ztunnel mTLS preview on a supported platform. Evaluate identity authorization, peer authentication, and encryption in transit separately instead of treating the result as identical to Istio `STRICT` workload mTLS.

**References:**
- [Cilium Service Mesh Security](../../../service-mesh/cilium-service-mesh/03-security.md)

</details>

---

## Scoring

- Count how many of the 6 questions you got right.
- 6/6: You can explain sidecar, ambient, and Cilium selection plus retry risk using measured evidence.
- 4-5/6: Review either raw-failure measurement or the authentication-versus-encryption distinction.
- 0-3/6: Re-read the [Sidecar vs Ambient Mode Selection Guide](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md) from the start.

## Learning Resources

- [Sidecar vs Ambient Mode Selection Guide](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Ambient Mode](../../../service-mesh/istio/advanced/01-ambient-mode.md)
- [mTLS](../../../service-mesh/istio/security/01-mtls.md)
- [Cilium Service Mesh Security](../../../service-mesh/cilium-service-mesh/03-security.md)

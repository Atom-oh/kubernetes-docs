# Istio Comparison Quiz

> **Historical report**: Istio 1.30.2 / EKS 1.36.2; not a current support matrix
> **Reviewed**: September 11, 2026

This quiz tests your understanding of the sidecar vs. ambient mode selection criteria, especially the limitations of the reported EKS measurements. The audit did not recreate those experiments.

## Multiple Choice Questions (1-6)

### Question 1: Evidence for ambient waypoint 503s

What can be concluded about the cause of the reported waypoint 503s from the aggregate rollout counts alone?

A. Duplicate IP assignment was proven

B. A connection-lifecycle race is a hypothesis; proxy response flags and endpoint/connection timelines are needed to establish the cause

C. NetworkPolicy was proven to cause every failure

D. The counts prove that STRICT mTLS is unsupported

<details>
<summary>Answer & Explanation</summary>

**Answer: B**

**Explanation:**

Aggregate HTTP status counts do not establish a root cause. Pod termination, endpoint propagation, application/proxy draining, timeouts and connection pools can all contribute. The original IP-reuse/ztunnel-notification explanation was not backed by a retained diagnostic timeline. Investigate actual upstream hosts, response flags, Pod UIDs and connection events rather than teaching that hypothesis as a proven mechanism.

**References:**

- [Sidecar vs Ambient Mode Selection Guide](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Ambient Mode: Waypoint Proxy](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>

---

### Question 2: Interpreting the reported EKS results

The untuned samples recorded 324 HTTP 503s and 2 non-HTTP errors out of 60,000 calls for sidecar; 0 and 195 out of 60,000 for ambient L4; and 1,528 and 84 out of 59,913 for ambient L7. Which interpretation is supported?

A. Ambient is always more stable

B. The L7 sample had a higher observed HTTP 503 fraction, while zero L4 HTTP 503s still left 195 non-HTTP failures

C. The same underlying cause was proven for all error categories

D. Fortio SocketCount directly measures the waypoint's upstream pool

<details>
<summary>Answer & Explanation</summary>

**Answer: B**

**Explanation:**

The measured fractions are 0.54% for sidecar and about 2.55% for L7, a ratio of about 4.72 in these samples. This is not an intrinsic product multiplier. Zero HTTP 503s is not zero total failures. Fortio's non-HTTP code -1 does not identify a specific reset/EOF/timeout cause without the error details. SocketCount concerns client sockets; L7 had the most sockets (2,486), not L4 (1,652). Requested QPS multiplied by duration does not guarantee an exact completed-call count, and different rollout counts limit a causal comparison.

**References:**

- [Sidecar vs Ambient Mode Selection Guide: Zero-Downtime Rollout Results](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### Question 3: NetworkPolicy and ambient

In the reported VPC CNI experiment, enforcement was verified and an ingress rule allowing only 8080 blocked the observed HBONE path. What should be checked next?

A. Remove all NetworkPolicies

B. Allow the required TCP 15008 tunnel path with appropriate scope, then verify source, identity and inner-port policy boundaries

C. Change mTLS to PERMISSIVE

D. Restart the CNI and assume the policy is correct

<details>
<summary>Answer & Explanation</summary>

**Answer: B**

**Explanation:**

The reported flow recovered after TCP 15008 was allowed. This is evidence for that tested path, not proof that every CNI or existing policy behaves identically. An outer-tunnel allowance is not a complete least-privilege policy for traffic inside the tunnel. Verify source selectors, waypoint traversal, DNS/control-plane dependencies and actual enforcement. Sidecar's observed application-port result is likewise a scoped observation.

**References:**

- [Sidecar vs Ambient Mode Selection Guide: NetworkPolicy](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### Question 4: Non-idempotent APIs and retry

Why should mesh retries be explicitly disabled by default on non-idempotent command paths such as order creation?

A. Retries always consume more CPU than the application

B. A failed or lost response can leave the server-side outcome unknown, so replay may repeat an already committed command

C. Retries are incompatible with STRICT mTLS

D. Ambient has no L7 retry capability

<details>
<summary>Answer & Explanation</summary>

**Answer: B**

**Explanation:**

A timeout, reset or error response does not always prove that the command had no effect. Replaying an ambiguous write can duplicate work unless the server provides suitable durable idempotency/transaction semantics. This risk does not depend on proving one particular waypoint race. The old T2 report's zero duplicate count cannot establish safety or even a reliable frequency estimate: the client was unbounded, reported counts conflicted with the stated duration/rate, and observer errors could be hidden. A revised bounded observer is still not a business transaction ledger. Measure stable command IDs and response-loss cases with complete observation.

**References:**

- [Sidecar vs Ambient Mode Selection Guide: The Risk of Retry as a Mitigation](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### Question 5: Comparing data-plane behavior fairly

Which experiment is a necessary starting point for separating failures from failures hidden by retries?

A. Compare only final GET success counts

B. Keep sidecar retries but disable ambient retries

C. Set write routes to attempts: 0 in both modes and collect raw HTTP/non-HTTP errors, retry counters, upstream deliveries and final outcomes

D. Choose the mode with the lowest average CPU

<details>
<summary>Answer & Explanation</summary>

**Answer: C**

**Explanation:**

Sidecar and waypoint Envoy can perform L7 retries; ztunnel cannot interpret HTTP 503 or replay HTTP requests. Disable write retries equivalently and record upstream_rq_retry, actual deliveries, stable command IDs and client accounting. Also control load, versions, resources and rollout exposure, and repeat the experiment. This separates observations more fairly; one run still does not prove inherent product stability.

**References:**

- [Sidecar vs Ambient Mode Selection Guide: raw failure measurement](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Retry and Timeout](../../../service-mesh/istio/traffic-management/05-retry-timeout.md)

</details>

---

### Question 6: Cilium authentication and encryption

For Cilium's documented out-of-band mutual-authentication mechanism, what does setting authentication to required imply?

A. Every payload automatically uses workload TLS

B. The out-of-band peer-identity handshake and payload encryption are separate; encryption must be configured and verified separately

C. It is identical to Istio PeerAuthentication STRICT in implementation and maturity

D. Authorization policy is no longer needed

<details>
<summary>Answer & Explanation</summary>

**Answer: B**

**Explanation:**

The released Cilium 1.20.1 documentation labels this mechanism Beta and describes an out-of-band handshake separate from the application data path. The authentication policy alone does not encrypt application payloads. Evaluate supported WireGuard/IPsec encryption separately, including its platform and traffic-coverage limits. Cilium 1.20.1 also has a separate ztunnel encryption beta with namespace enrollment, TCP-only and policy/platform restrictions. It is not activated by this out-of-band authentication policy setting.

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

## Official evidence

- [Istio ambient L7 feature status](https://github.com/istio/istio.io/blob/release-1.30/content/en/docs/ambient/usage/l7-features/index.md)
- [Cilium 1.20.1 mutual authentication](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)

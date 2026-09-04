# Latency Impact Analysis Quiz

This quiz tests your understanding of the degrading and improving latency factors in a Lattice migration and how to design a PoC measurement.

## Multiple Choice Questions

1. Why can't the latency impact of a Lattice migration be stated in advance as "it adds N milliseconds"?
   - A) AWS does not publish latency figures
   - B) The reduction in proxy traversals (improvement) and the added network traversal (degradation) compete in the same magnitude range, and which one wins depends on the environment
   - C) Lattice is not yet GA
   - D) Latency is determined solely by region

<details>

<summary>Show Answer</summary>

**Answer: B) The reduction in proxy traversals (improvement) and the added network traversal (degradation) compete in the same magnitude range, and which one wins depends on the environment**

**Explanation:**
Both factors compete in the same range — hundreds of microseconds to a few milliseconds. Which one wins depends on how much node CPU your Envoy sidecars consume, request length (the relative weight of fixed overhead), whether keepalive is used, whether IAM Auth is enabled, and what fraction of calls cross an AZ. Those values differ per organization. Hence the conclusion is "measure it," and the sign of the result can change with the environment.
</details>

2. What does it mean that p50 and p99 have different factor compositions?
   - A) p99 is always worse than p50, so looking at p50 alone is enough
   - B) Degradation (added path) likely dominates p50 while improvement (removed Envoy CPU contention) may dominate p99, so judging from a single average hides the structure
   - C) p50 and p99 are affected by the same factors, so measuring one is enough
   - D) p99 is noise and should be ignored

<details>

<summary>Show Answer</summary>

**Answer: B) Degradation (added path) likely dominates p50 while improvement (removed Envoy CPU contention) may dominate p99, so judging from a single average hides the structure**

**Explanation:**
Envoy sidecar CPU contention barely shows in the average and shows heavily in the tail — most requests are scheduled immediately while some wait milliseconds to tens of milliseconds. Removing the sidecar removes that contention, so p99 may improve on clusters with tight node CPU. Meanwhile the added VPC traversal is reflected directly in p50 as well. Measuring both percentiles is required to understand the real impact.
</details>

3. Which client setting was noted as potentially mattering more than one proxy hop?
   - A) DNS cache TTL
   - B) keepalive and connection pool settings
   - C) Log level
   - D) Request timeout value

<details>

<summary>Show Answer</summary>

**Answer: B) keepalive and connection pool settings**

**Explanation:**
In the Pod network benchmark, disabling keepalive raised p50 from 0.461 → 1.079 ms same-AZ and 0.704 → 1.517 ms cross-AZ — more than double. Every new connection adds an extra RTT and a TLS handshake per request. In AS-IS, Envoy managed connections on the application's behalf; once that layer is gone, the application's HTTP client configuration is exposed. This is a client configuration issue, not a Lattice characteristic.
</details>

4. In the PoC measurement matrix, what does the delta between `IAM Auth on` and `IAM Auth off` tell you?
   - A) The cost of cross-AZ traversal
   - B) The pure cost of SigV4 signing and verification
   - C) The effect of removing Envoy CPU contention
   - D) The pure effect of the path change

<details>

<summary>Show Answer</summary>

**Answer: B) The pure cost of SigV4 signing and verification**

**Explanation:**
The matrix exists to isolate factors. The `IAM Auth on` vs `off` delta is the cost of introducing authentication alone, and the `AS-IS (App Mesh)` vs `IAM Auth off` delta is the effect of the path change alone. Obtaining those two separately is the point of including IAM Auth as an axis. Note that SigV4's real cost may be less the crypto itself and more the part that appears in the p99 tail when credential refresh blocks the request path.
</details>

5. Which statement about cross-AZ traffic is correct?
   - A) It is both a latency degradation factor and a separate additional billing factor
   - B) It is a latency degradation factor, but traffic through Lattice incurs no separate inter-AZ charge — it is included in the data processing charge
   - C) It affects neither latency nor billing
   - D) Lattice always selects a Target in the caller's AZ, so it need not be considered

<details>

<summary>Show Answer</summary>

**Answer: B) It is a latency degradation factor, but traffic through Lattice incurs no separate inter-AZ charge — it is included in the data processing charge**

**Explanation:**
Cross-AZ increases latency due to physical distance (measured baseline: same-AZ 0.339 ms vs cross-AZ 0.544 ms), but on the billing side Lattice does not charge a separate inter-AZ fee — it is folded into data processing. D is wrong: whether Lattice's Target selection considers the caller's AZ is not confirmed in official documentation and must be measured in a PoC, which is exactly why the matrix includes an AZ axis.
</details>

6. Why is warm-up needed in the measurement design, and why should first-request latency still be recorded separately?
   - A) Warm-up is unnecessary; measuring the first request is enough
   - B) Without warm-up, credential acquisition and connection setup costs are mixed in and do not represent steady state — but for workloads with frequent cold starts the first-request value is actually the important one
   - C) Warm-up improves only p50 and has no effect on p99
   - D) The first request always fails

<details>

<summary>Show Answer</summary>

**Answer: B) Without warm-up, credential acquisition and connection setup costs are mixed in and do not represent steady state — but for workloads with frequent cold starts the first-request value is actually the important one**

**Explanation:**
The first request includes both an STS call and a TLS handshake, so it is not representative of steady state; steady-state numbers should come from after adequate warm-up. However, for workloads with frequent cold starts — Lambda, or services that scale out often — the latency users actually experience is closer to the first-request value, so record it as a separate item and evaluate both.
</details>

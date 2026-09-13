# Latency Impact Analysis Quiz

This quiz tests your understanding of the degrading and improving latency factors in a Lattice migration and how to design a PoC measurement.

## Multiple Choice Questions

1. Why can't the latency impact of a Lattice migration be stated in advance as "it adds N milliseconds"?
   - A) AWS does not publish latency figures
   - B) Proxy work, network paths, TLS reuse and authentication change together, so measure the actual workload
   - C) Lattice is not yet GA
   - D) Latency is determined solely by region

<details>

<summary>Show Answer</summary>

**Answer: B) Proxy work, network paths, TLS reuse and authentication change together, so measure the actual workload**

**Explanation:**
No Lattice latency measurements are supplied here. The direction and magnitude depend on the tested configuration; do not present microsecond estimates or guaranteed improvement as observations.
</details>

2. What does it mean that p50 and p99 have different factor compositions?
   - A) p99 is always worse than p50, so looking at p50 alone is enough
   - B) The median and tail can react differently to contention, cold starts and routing, so measure both
   - C) p50 and p99 are affected by the same factors, so measuring one is enough
   - D) p99 is noise and should be ignored

<details>

<summary>Show Answer</summary>

**Answer: B) The median and tail can react differently to contention, cold starts and routing, so measure both**

**Explanation:**
Different percentile responses are hypotheses to investigate, not a guarantee that p50 worsens while p99 improves. Keep errors, throughput and workload conditions alongside the distributions.
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
The cited benchmark shows that connection reuse mattered in that workload. New TCP connections add setup; TLS handshakes apply when TLS is used. That is not a Lattice latency measurement.
</details>

4. In the PoC measurement matrix, what does the delta between `IAM Auth on` and `IAM Auth off` tell you?
   - A) The cost of cross-AZ traversal
   - B) The combined effect of signing, credential handling and enabled-policy evaluation under matched conditions
   - C) The effect of removing Envoy CPU contention
   - D) The pure effect of the path change

<details>

<summary>Show Answer</summary>

**Answer: B) The combined effect of signing, credential handling and enabled-policy evaluation under matched conditions**

**Explanation:**
Auth on/off does not isolate HMAC alone. Repeat matched runs, keep load and connection settings constant, and report credential refresh, failures and throughput.
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

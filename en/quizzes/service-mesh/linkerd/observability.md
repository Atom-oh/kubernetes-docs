# Linkerd Observability Quiz

Based on the [observability guide](../../../service-mesh/linkerd/05-observability.md), reviewed September 11, 2026.

### 1. Which is not one of Linkerd’s three core HTTP service metrics?

- A. Success rate
- B. Request rate
- C. Latency
- D. CPU utilization

<details>
<summary>Show Answer</summary>

**Answer: D**

**Explanation:** The three are proxy-classified success rate, request rate and latency. CPU/capacity is additional operational information; this does not mean a proxy or another collector cannot expose process/resource metrics. Opaque TCP does not automatically provide HTTP service metrics.

</details>

### 2. Which is not a standard linkerd viz stat table column?

- A. SUCCESS
- B. RPS
- C. LATENCY_P99
- D. ERROR_TYPE

<details>
<summary>Show Answer</summary>

**Answer: D**

**Explanation:** The selected release includes MESHED, SUCCESS, RPS, percentiles and TCP_CONN. Wide output adds transport byte rates rather than a proxy-version inventory. Use appropriate policy, Tap, logs and metrics to investigate errors.

</details>

### 3. What does linkerd viz tap provide?

- A. Complete network packet capture
- B. A live observation stream of supported requests
- C. Automatic proxy policy changes
- D. Certificate renewal

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Tap is limited/sampled traffic observation, not a complete audit. max-rps limits the tapped rate and does not throttle all application traffic. Current tap has no --from or --show-headers flag; use supported selectors and protect access to request metadata.

</details>

### 4. What does a legacy ServiceProfile’s route naming enable?

- A. Disk I/O accounting
- B. Per-route metrics
- C. Automatic complete distributed traces
- D. Mandatory retries on every method

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** ServiceProfiles support route metrics and the viz routes view. They remain a compatibility interface and can supersede current outbound HTTPRoute reliability settings. Adding a profile for observability must not silently enable unsafe retries or override an existing policy.

</details>

### 5. How does the guide access the existing default Viz Prometheus locally?

- A. Expose an unauthenticated NodePort
- B. Create a public LoadBalancer
- C. Use kubectl port-forward bound to loopback
- D. Assume a public URL exists

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** The example forwards the existing Prometheus Service to 127.0.0.1. It does not install Prometheus or configure public authentication. Access from other workloads also needs the applicable network and Linkerd authorization settings.

</details>

### 6. Which pair is W3C trace context, used by the application examples?

- A. x-request-id and Authorization
- B. x-b3-traceid and x-b3-spanid
- C. traceparent and tracestate
- D. x-linkerd-proxy and Cookie

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Linkerd supports W3C and B3, preferring W3C when both exist. x-request-id is a correlation ID, not a required trace format. Propagating headers alone does not create application spans or configure sampling/export; use an appropriate tracing library for those tasks.

</details>

### 7. What does linkerd viz top summarize?

- A. Pods ranked by CPU usage
- B. Tapped live request paths/routes
- C. All historic error messages
- D. Latest container logs

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** top summarizes live traffic, with sampling/rate limits and supported filters. hide-sources controls the source column, not headers. Its observations do not replace retained Prometheus metrics or a complete request audit.

</details>

### 8. Which annotation changes proxy diagnostic log level?

- A. config.linkerd.io/log-level
- B. config.linkerd.io/proxy-log-level
- C. linkerd.io/proxy-log
- D. proxy.linkerd.io/log-level

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** proxy-log-level controls the diagnostic filter, and proxy-log-format controls diagnostic formatting. HTTP access logging is separately enabled with config.linkerd.io/access-log:json or apache. A partial Pod template is a patch/fragment, not a complete Deployment.

</details>

### 9. How should a windowed success ratio be calculated?

- A. Divide lifetime cumulative success and total counters without a rate
- B. Use the invented success_total counter
- C. Divide successful response rate by total response rate with matching scope, missing-success handling and a positive total
- D. Average an invented success_rate metric

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Use one intended observation direction and workload/cluster scope. An all-failure window with no success series must still produce ratio 0; missing/idle data must not become 100% success. Proxy HTTP classification can count 400 as success, so match the business SLI deliberately.

</details>

### 10. What role can Jaeger play in the current tracing setup?

- A. Replace Kubernetes metrics discovery
- B. Aggregate application access logs only
- C. Collect/store/query distributed traces as a separately managed backend
- D. Automatically split traffic

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** The Linkerd-Jaeger extension was removed in 2.19. Current Linkerd configures an OpenTelemetry-compatible collector and, in the shown chart path, its mesh identity. A backend UI alone does not prove that application/proxy spans arrive or form complete traces.

</details>

### 11. Which information should be obtained through kubectl logs or a logging system rather than assuming Viz is a container-log viewer?

- A. Workload topology
- B. Deployment metrics
- C. Pod container logs
- D. ServiceProfile route metrics

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Viz provides workload/traffic views, topology and Tap. Diagnostic/access logs are separate data. A workflow that checks those views still needs a cause, a fix and verification; it does not automatically resolve an incident.

</details>

### 12. Which setting links Viz to an existing browser-accessible external Grafana?

- A. grafana.external:true
- B. grafana.externalUrl:https://grafana.example.com/
- C. grafana.enabled:false
- D. monitoring:external

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Current Viz does not install Grafana. externalUrl supplies the external link; grafana.url is the in-cluster reverse-proxy option with additional root/subpath configuration. Neither setting creates Grafana, configures its datasource or grants Prometheus access.

</details>

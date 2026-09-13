# Datadog Quiz

> **Last Updated**: September 13, 2026

1. What remains the team's responsibility with Datadog SaaS?

   - A) Nothing after installing the Agent
   - B) Only selecting a dashboard color
   - C) Collectors, identity, instrumentation, data handling, monitors and cost
   - D) Datadog's physical database servers

<details>
<summary>Show Answer</summary>

**Answer: C**

SaaS manages the backend. APM, profiling, logs and other products have distinct entitlements and billing; an Agent does not include everything.

</details>

2. Which credential/integration statement is correct?

   - A) Baseline Agent ingestion needs an API key; application keys and AWS account roles serve additional, specific features
   - B) Every Agent needs an application key and broad AWS read role
   - C) Adding IRSA automatically configures Datadog SaaS AWS integration
   - D) A guessed service-account name is sufficient

<details>
<summary>Show Answer</summary>

**Answer: A**

The external metrics provider needs additional API permissions/key configuration. SaaS AWS integration uses an authorized cross-account role/external ID. Resolve the actual rendered Agent SA.

</details>

3. Does admission.datadoghq.com/enabled=true alone prove APM SDK injection?

   - A) Yes, including every language/version automatically
   - B) No; configure SDK annotations or SSI targets, then verify newly admitted pods and actual trace data
   - C) Yes, even in the Cluster Agent namespace
   - D) Yes, if a trace socket exists

<details>
<summary>Show Answer</summary>

**Answer: B**

Mutation/connection settings and library injection are distinct. Current local injection excludes kube-system and the Cluster Agent namespace. Library, runtime, mount and security compatibility still matter.

</details>

4. How should an application pod reach the node DogStatsD Agent?

   - A) Always use the application's localhost
   - B) Put the API key in every UDP packet
   - C) Create an unrelated ConfigMap
   - D) Use the configured reachable endpoint, such as a mounted Linux UDS directory

<details>
<summary>Show Answer</summary>

**Answer: D**

The application localhost is not a node Agent. UDS paths, permissions and SDK argument formats must match. Datagrams do not acknowledge SaaS ingestion; counters are not an exactly-once ledger.

</details>

5. Which metric interpretation is correct?

   - A) kubernetes.cpu.usage.total is percent
   - B) All missing legacy-catalogue metrics were removed
   - C) kubernetes.cpu.usage.total is nanocores; Kubelet restart metrics are cumulative gauges
   - D) Summing repeated restart samples counts new restarts

<details>
<summary>Show Answer</summary>

**Answer: C**

system.cpu.idle is percent. Kubelet and State Core have different valid metric names and tags. The example restart monitor explicitly evaluates a total; recent increases need reset-aware validation.

</details>

6. What does the .as_count() error-ratio path calculate?

   - A) The ratio of time-aggregated error and total counts
   - B) A sum of every time-bucket ratio
   - C) A global p95
   - D) Automatic 100% success for zero traffic

<details>
<summary>Show Answer</summary>

**Answer: A**

Use sum aggregation and matching groups. The helper emits zero good/error counts explicitly. Zero traffic, missing data and error-free traffic remain different states.

</details>

7. Which OpenMetrics/log configuration statement is correct?

   - A) Any ConfigMap is automatically mounted
   - B) Use matching container annotations/current check fields; Logs Grok rules use match_rules/support_rules
   - C) prometheus.enabled at chart root configures everything
   - D) Grok camelCase keys and snake_case keys are equivalent

<details>
<summary>Show Answer</summary>

**Answer: B**

The current OpenMetrics check uses openmetrics_endpoint. datadog.confd provides chart-owned mounting; standalone ConfigMaps do not self-install. Request-schema validation is not a live scrape or Grok parse.

</details>

8. What should manual trace-log correlation preserve?

   - A) Only dd.trace_id, deleting all other MDC fields
   - B) An arbitrary numeric cast of a 128-bit ID
   - C) A hardcoded successful trace ID
   - D) The caller's prior MDC context, string IDs and actual instrumentation/data prerequisites

<details>
<summary>Show Answer</summary>

**Answer: D**

The helper restores context even when application code raises. It is synchronous. Automatic injection/parsing, consistent service tags and available traces are separate requirements.

</details>

9. What is wrong with pricing 50 services as 50 APM hosts?

   - A) APM is always free
   - B) Log ingestion is the whole log bill
   - C) Services and billable hosts are different units; product/contract allotments and usage must be counted
   - D) Every cluster has one host

<details>
<summary>Show Answer</summary>

**Answer: C**

The old estimate was not a measured bill. Indexing/retention, span allotments, custom metrics and other products matter. nonLocalTraffic is reachability, not a cost quota.

</details>

10. Which Watchdog/SLO/diagnostic practice is correct?

   - A) A Watchdog insight proves a page was delivered
   - B) Match the SLO model and good/total policy, test routing, and inspect local diagnostic bundles before sharing
   - C) A local flare automatically authorizes upload
   - D) Dump every DD_ environment value when traces are missing

<details>
<summary>Show Answer</summary>

**Answer: B**

Datadog supports metric-, monitor- and time-slice SLOs. Notification and no-data behavior need validation. env dumps can expose keys; --local keeps the initial flare collection local.

</details>

---

[Return to the guide](../../../observability/metrics/05-datadog.md)

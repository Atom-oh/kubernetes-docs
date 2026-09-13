# Observability Lab 02 Quiz

<span id="observability-lab-part-2-observability-stack-quiz"></span>

> **Last Updated**: September 13, 2026

1. What endpoint should cross-cluster collection use?
   - A) Only the other cluster’s service DNS.
   - B) A private endpoint with actual routing, DNS and TLS.
   - C) Always disable TLS verification.
   - D) Use the kubeconfig file as a URL.

<details>
<summary>Show answer</summary>

**Answer: B) A private endpoint with actual routing, DNS and TLS.**

The NLB forwards TCP and the server validates client certificates.

</details>

---

2. What is the CRI log parsing order?
   - A) Only a Docker JSON parser.
   - B) Container/CRI parser followed by JSON parsing.
   - C) Treat the entire prefix as a JSON field.
   - D) Make every trace ID a stream label.

<details>
<summary>Show answer</summary>

**Answer: B) Container/CRI parser followed by JSON parsing.**

Verify preservation of service/level/trace_id from the app body.

</details>

---

3. How should mTLS Prometheus be probed?
   - A) Default HTTPS probes without certificates always succeed.
   - B) A promtool exec probe using client-certificate configuration.
   - C) Delete all probes.
   - D) Always return readiness true.

<details>
<summary>Show answer</summary>

**Answer: B) A promtool exec probe using client-certificate configuration.**

Actual Operator merging and Prometheus TLS ready/healthy behavior were tested.

</details>

---

4. Which Tempo3 configuration change matters?
   - A) Copy only old Tempo2 ingester values.
   - B) Use live-store/backend scheduler/worker and current chart values.
   - C) Copy Loki configuration.
   - D) Chart and app versions are always identical.

<details>
<summary>Show answer</summary>

**Answer: B) Use live-store/backend scheduler/worker and current chart values.**

Check chart rendering separately from actual binary configuration/startup.

</details>

---

5. What does the single-instance Loki/Tempo baseline mean?
   - A) Production HA is automatic.
   - B) A durable lab instance, not an HA/capacity guarantee.
   - C) No storage costs.
   - D) Backups are automatically guaranteed.

<details>
<summary>Show answer</summary>

**Answer: B) A durable lab instance, not an HA/capacity guarantee.**

Verify retention, PVCs, cleanup and failure impact.

</details>

---

6. What JSON does the AIOps CloudWatch path need?
   - A) Only query strings.
   - B) Structured logs preserving service/level/trace_id.
   - C) All plaintext passwords.
   - D) Traces automatically create logs.

<details>
<summary>Show answer</summary>

**Answer: B) Structured logs preserving service/level/trace_id.**

raw_log behavior and actual exporter PutLogEvents messages were checked locally.

</details>

---

7. What is required for Grafana correlation?
   - A) Only enable a UI option.
   - B) Matching UIDs, field names, actual data and retention.
   - C) Only match display names.
   - D) Always uppercase trace_id.

<details>
<summary>Show answer</summary>

**Answer: B) Matching UIDs, field names, actual data and retention.**

Align prometheus/loki/tempo UIDs and escaped derived-field expressions.

</details>

---

8. How are exemplars handled by service Prometheus remote-write?
   - A) Always automatically retained.
   - B) Verify sendExemplars, receiving/storage and datasource linking.
   - C) A label automatically creates a trace.
   - D) Every request is necessarily stored.

<details>
<summary>Show answer</summary>

**Answer: B) Verify sendExemplars, receiving/storage and datasource linking.**

Verify the representative trace exists, not just the transport option.

</details>

---

9. How should node-log DaemonSet permissions be treated?
   - A) Always enable hostPID and every capability.
   - B) Allow only scoped read-only host mounts, read RBAC and the explicit root exception.
   - C) Full cluster-admin.
   - D) Host-log paths have no permission implications.

<details>
<summary>Show answer</summary>

**Answer: B) Allow only scoped read-only host mounts, read RBAC and the explicit root exception.**

Validate namespace admission and actual file permissions together.

</details>

---

10. How should optional backends and durable queues be described?
   - A) All backends are already deployed.
   - B) They require separate validation; the baseline does not guarantee persistent offsets/queues.
   - C) Loss/duplicates are impossible on restart.
   - D) 24-hour retention proves a30-day SLO.

<details>
<summary>Show answer</summary>

**Answer: B) They require separate validation; the baseline does not guarantee persistent offsets/queues.**

Record only actual configuration and validation as successful.

</details>

---

[Return to the guide](../../../labs/observability/02-observability-stack-lab.md)

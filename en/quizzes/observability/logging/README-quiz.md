# Logging Overview Quiz

> **Last Updated**: September 13, 2026

1. Which statement about structured JSON logs is correct?

   - A) They need no parsing
   - B) They always use fewer bytes
   - C) Explicit fields help analysis, but decoding, framing and field mapping still matter
   - D) They automatically redact all sensitive data

<details>
<summary>Show Answer</summary>

**Answer: C**

Use a tested event schema and usually one encoded event per line. JSON may be larger than plain text, and raw/parsed copies both need a data-handling policy.

</details>

2. Are TRACE through FATAL universally numbered 0 through 5?

   - A) No; frameworks differ, and OpenTelemetry uses severity ranges 1–24 with 0 unspecified
   - B) Yes, in every language
   - C) Yes, only in Kubernetes
   - D) FATAL is always 0

<details>
<summary>Show Answer</summary>

**Answer: A**

Map severity meaning rather than copying a made-up numeric scale. A log level alone does not decide recoverability, and raising all production logs to WARN can lose evidence.

</details>

3. What is the common default Linux container-log layout?

   - A) Actual files in /var/log/containers; symlinks in /var/log/pods
   - B) Actual files in /var/log/pods; compatibility symlinks in /var/log/containers
   - C) Every runtime writes to /var/lib/docker only
   - D) kubectl logs contains an unlimited archive

<details>
<summary>Show Answer</summary>

**Answer: B**

The original paths were reversed. podLogsDir/OS/runtime can change the layout. Rotation and --previous do not create a central historical archive.

</details>

4. What is required for a fair backend cost comparison?

   - A) Only the S3 GB price
   - B) Always select Loki for the lowest bill
   - C) Assume self-managed queries are free
   - D) Compare ingestion, retained/indexed data, compute, queries, requests, network, recovery and operations on the same workload

<details>
<summary>Show Answer</summary>

**Answer: D**

The old 2025 and 100-GB figures mixed units and lacked a reproducible configuration. They were not measured production results; updating only the date does not fix them.

</details>

5. How should trace context be attached to a log?

   - A) Generate unrelated IDs for every record
   - B) Use the actual active context; the shown trace/span IDs have 32/16 hex characters and cannot be all zero
   - C) Require trace IDs in every startup record
   - D) Use session tokens as span IDs

<details>
<summary>Show Answer</summary>

**Answer: B**

Trace-less events are valid. JSON field names require mapping to the destination model; IDs alone do not create distributed traces or prove correlation.

</details>

6. Which processing choice is safer for the illustrated pipeline?

   - A) Drop every line containing HealthCheck
   - B) Trust application JSON as the tenant identity
   - C) Separate app fields from trusted metadata and validate redaction/filtering, offsets, buffers and retries
   - D) Assume buffering prevents all loss and duplicates

<details>
<summary>Show Answer</summary>

**Answer: C**

The Fluent Bit sample is a classic-format filter fragment. Keep_Log retains another copy to redact. Failing health checks can be valuable evidence, and delivery guarantees depend on the full path.

</details>

7. How should regulatory retention be chosen?

   - A) By applicable record type, jurisdiction, contracts, legal holds and approved policy
   - B) Seven years for all financial logs
   - C) Six years for all healthcare logs
   - D) A named backend proves compliance

<details>
<summary>Show Answer</summary>

**Answer: A**

An industry label is not a complete legal rule. Include replicas, object versions, backups and exports in retention/deletion/access plans and test restoration.

</details>

8. What is true about sidecars and DaemonSets?

   - A) Both guarantee tenant isolation
   - B) emptyDir survives pod deletion
   - C) A DaemonSet proves all node logs were delivered
   - D) Sidecars can help file-only apps; scheduling, shared storage, lifecycle and security still need validation

<details>
<summary>Show Answer</summary>

**Answer: D**

emptyDir survives container restarts within a pod, not pod deletion. DaemonSets target eligible nodes and can have rollout overlap; multiple routes can duplicate records.

</details>

9. Which storage/client statement is correct?

   - A) OpenSearch only uses S3 for snapshots in every deployment
   - B) Deployment/index/query design matters; UltraWarm uses S3/cache and Promtail needs migration after its stated EOL
   - C) All CloudWatch log classes have identical features
   - D) A compression ranking is valid without a dataset

<details>
<summary>Show Answer</summary>

**Answer: B**

Compare actual deployment models and query needs. Promtail EOL is 2026-03-02; the notice treats lambda-promtail separately. Choosing a backend does not guarantee cost or compliance.

</details>

10. What does enabling EKS control-plane audit logging establish?

   - A) Every request and body is recorded without loss
   - B) Worker DaemonSets read the managed API-server host
   - C) Audit records follow policy and a best-effort CloudWatch delivery path that must be verified
   - D) Application stdout collection is automatically complete

<details>
<summary>Show Answer</summary>

**Answer: C**

Check asynchronous update status, actual streams and retention/access. Fargate uses its managed router; Container Insights performance logs are distinct from application stdout/stderr.

</details>

---

[Return to the guide](../../../observability/logging/README.md)

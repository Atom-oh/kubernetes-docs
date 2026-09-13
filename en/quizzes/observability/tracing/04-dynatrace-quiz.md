# Dynatrace Quiz

> **Last Updated**: September 13, 2026

---

1. Which statement about OneAgent is incorrect?
   - A) It can discover supported processes.
   - B) It can instrument supported technologies.
   - C) Installation eliminates every permission, scope and connectivity prerequisite.
   - D) Coverage depends on deployment mode and technology support.

<details>
<summary>Show Answer</summary>

**Answer: C) Installation eliminates every permission, scope and connectivity prerequisite.**

Automatic discovery does not remove installation privileges, supported-runtime requirements, egress, token configuration, injection selection or data-privacy decisions. It does not promise every method/request will be captured.

</details>

---

2. Which component manages DynaKube resources and Dynatrace workloads in Kubernetes?
   - A) A standalone kubectl binary.
   - B) Dynatrace Operator.
   - C) Only the OneAgent process.
   - D) An automatically created Lambda function.

<details>
<summary>Show Answer</summary>

**Answer: B) Dynatrace Operator.**

Helm or manifests install the Operator; they are not competing monitoring modes. The reviewed Operator/chart is 1.10.2. Its released CRD serves v1beta5 and v1beta6, with v1beta6 as storage; the old v1beta2 example is not a current served API. Component versions and update behavior still need review.

</details>

---

3. Which outcome is not implied by enabling problem detection and root-cause analysis?
   - A) Baseline and anomaly analysis.
   - B) Topology-aware investigation.
   - C) Unreviewed production code changes are automatically authorized.
   - D) Impact analysis using collected evidence.

<details>
<summary>Show Answer</summary>

**Answer: C) Unreviewed production code changes are automatically authorized.**

Davis terminology remains in older material; current documentation uses Dynatrace Intelligence. Approved agentic actions/workflows can be configured, including Preview features, so 'AI can never take action' is also too broad. Detection alone does not grant remediation authority or prove that a diagnosis is correct.

</details>

---

4. What does cloudNativeFullStack combine?
   - A) Only Windows monitoring.
   - B) Host monitoring and webhook-based application code-module injection.
   - C) Application-only monitoring without a host component.
   - D) A guarantee of lower overhead in every workload.

<details>
<summary>Show Answer</summary>

**Answer: B) Host monitoring and webhook-based application code-module injection.**

The released Operator describes cloudNativeFullStack as combining hostMonitoring and applicationMonitoring, using its CSI infrastructure. It is not merely an application sidecar. classicFullStack is still present in the reviewed release; do not call it removed. Mode, OS and CSI permissions determine suitability.

</details>

---

5. What capability is associated with PurePath?
   - A) Log compression.
   - B) Distributed tracing with supported code-level context.
   - C) A universal packet capture appliance.
   - D) Database backup.

<details>
<summary>Show Answer</summary>

**Answer: B) Distributed tracing with supported code-level context.**

Trace and code visibility depend on supported technologies, instrumentation, capture/sampling settings and available telemetry. 'Complete path' is not proof that every request, method or asynchronous relationship is retained.

</details>

---

6. Which measure does current DPS host-based Full-Stack Monitoring use?
   - A) vCPU plus RAM.
   - B) Monitored memory-GiB-hours under the applicable rate card.
   - C) max(RAM/16, vCPU/1.5) Host Units.
   - D) One flat unit per Kubernetes namespace.

<details>
<summary>Show Answer</summary>

**Answer: B) Monitored memory-GiB-hours under the applicable rate card.**

The vendor documents 15-minute billing intervals, RAM rounding to 0.25 GiB and a 4 GiB host minimum. Container-based application-only monitoring has different memory/minimum rules. The old CPU/RAM maximum formula is not the current DPS calculation. Usage arithmetic is not an invoice: commitment, rate card, allowances and separately billed capabilities matter.

</details>

---

7. Which is not ActiveGate's role?
   - A) Routing telemetry.
   - B) Configured Kubernetes API monitoring.
   - C) Acting as the long-term analytics data lakehouse.
   - D) Providing an approved connectivity path to the environment.

<details>
<summary>Show Answer</summary>

**Answer: C) Acting as the long-term analytics data lakehouse.**

Routing/monitoring and local buffering are different from long-term backend storage. Some containerized ActiveGate ingestion configurations require a PVC. A SaaS route still needs connectivity; a proxy does not make a completely disconnected network able to reach SaaS.

</details>

---

8. What does oneAgent.cloudNativeFullStack.namespaceSelector select?
   - A) Namespaces to create.
   - B) Namespaces eligible for the configured webhook injection.
   - C) A network-isolation boundary.
   - D) The complete scope of host and Kubernetes API monitoring.

<details>
<summary>Show Answer</summary>

**Answer: B) Namespaces eligible for the configured webhook injection.**

The selector and pod injection annotations control webhook injection. They do not restrict OneAgent host monitoring or ActiveGate Kubernetes API monitoring. Metadata enrichment and OTLP exporter auto-configuration have their own selectors. Protect label and DynaKube update permissions; selectors are not RBAC or a billing cap.

</details>

---

9. Which transport does the documented native Dynatrace SaaS/ActiveGate OTLP API accept?
   - A) gRPC only.
   - B) HTTP with binary Protocol Buffers.
   - C) gRPC and HTTP/JSON interchangeably.
   - D) Only a proprietary non-OTLP format.

<details>
<summary>Show Answer</summary>

**Answer: B) HTTP with binary Protocol Buffers.**

The native endpoint supports HTTP/protobuf, not gRPC or protobuf JSON. A Collector can accept gRPC and export HTTP to Dynatrace. Use the correct /api/v2/otlp base and signal suffix, TLS and the token type/scopes required by the selected endpoint. Do not substitute an .apps browser URL.

</details>

---

10. What does Smartscape provide?
   - A) A universal alert mute switch.
   - B) Topology and dependency mapping from observed data.
   - C) Automatic authorization for scaling.
   - D) Source-code review.

<details>
<summary>Show Answer</summary>

**Answer: B) Topology and dependency mapping from observed data.**

The dependency graph supports impact analysis and investigation. Its coverage depends on the monitored technologies and telemetry; absent relationships or data gaps must not be treated as proof that no dependency exists.

</details>

---

[Return to the guide](../../../observability/tracing/04-dynatrace.md)

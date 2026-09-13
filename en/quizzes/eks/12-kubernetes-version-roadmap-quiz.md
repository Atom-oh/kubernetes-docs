# Kubernetes Version Features and Roadmap Quiz

> **Last Updated**: September 12, 2026

Use the [source chapter](../../eks/12-kubernetes-version-roadmap.md) for version-specific prerequisites and the limits of the audit evidence.

1. What is the Kubernetes minor-release cadence?

   - A) One feature release per year
   - B) About three minor releases per year, roughly four months apart
   - C) Monthly minor releases
   - D) A schedule fixed to AWS conferences

<details>
<summary>Show Answer</summary>

**Answer: B) About three minor releases per year, roughly four months apart**

Upstream minor releases normally arrive about three times per year; patch releases have a separate cadence. The upstream patch-support policy is roughly 14 months (12 normal +2 maintenance). EKS standard support also lasts14 months, but starts from EKS availability, so the two calendars must not be conflated.

</details>

---

2. How do EKS standard and extended version-support fees differ?

   - A) Standard is free
   - B) Standard:14 months at $0.10/cluster-hour; extended:12 more months at $0.60 total/cluster-hour
   - C) Extended means every old version is supported forever
   - D) Extended has no security patches

<details>
<summary>Show Answer</summary>

**Answer: B) Standard:14 months at $0.10/cluster-hour; extended:12 more months at $0.60 total/cluster-hour**

These are version-support fees, not the total compute/storage/network bill. EXTENDED is the default upgrade policy; STANDARD can lead to automatic upgrade after standard support ends. Extended support also receives relevant security patches. Use the current release calendar and consider the actual support-end date and workload risk.

</details>

---

3. When did native sidecar containers become stable?

   - A) 1.28
   - B) 1.31
   - C) 1.33
   - D) 1.35

<details>
<summary>Show Answer</summary>

**Answer: C) 1.33**

The path is alpha 1.28 → beta 1.29 → stable 1.33. Restartable init containers use restartPolicy:Always. Startup sequencing depends on started/startupProbe state, and graceful shutdown uses the Pod’s shared termination budget. GA does not guarantee every helper exits gracefully or that a proxy image is configured correctly.

</details>

---

4. What does container in-place resize provide, and when did it become stable?

   - A) Replica scaling;1.30
   - B) CPU/memory allocation changes for an existing Pod;1.35, with restart/runtime constraints
   - C) PVC expansion;1.31
   - D) An image update without restarting its process;1.34

<details>
<summary>Show Answer</summary>

**Answer: B) CPU/memory allocation changes for an existing Pod;1.35, with restart/runtime constraints**

The feature was alpha 1.27, beta 1.33 and stable 1.35. Container resizePolicy controls restart behavior and resources can remain pending/infeasible. An accepted PATCH or unchanged containerID is not proof of completed cgroup actuation or zero disruption. Compare desired and reported resources, generation and conditions. VPA modes have their own versions and gates.

</details>

---

5. Which statement correctly describes DRA in Kubernetes 1.31?

   - A) Classic DRA was replaced by Device Plugins v2
   - B) DRA was still alpha; structured APIs evolved while classic allocation remained behind a separate gate
   - C) DRA was already GA
   - D) Stable v1 request syntax was identical to every older alpha API

<details>
<summary>Show Answer</summary>

**Answer: B) DRA was still alpha; structured APIs evolved while classic allocation remained behind a separate gate**

The1.31 release and source retain DRAControlPlaneController as a disabled alpha gate. It is removed in 1.32; DRA core becomes beta in 1.32 and stable in 1.34. The original quiz’s removal-in 1.31 answer was wrong. Current v1 requests use exactly, and actual drivers/ResourceSlices/attributes must be verified.

</details>

---

6. Which feature became stable in 1.30 for native CEL admission validation?

   - A) OPA Gatekeeper v4
   - B) A mandatory parameter CRD
   - C) ValidatingAdmissionPolicy
   - D) Every mutating admission mechanism

<details>
<summary>Show Answer</summary>

**Answer: C) ValidatingAdmissionPolicy**

ValidatingAdmissionPolicy uses a policy and binding, with optional parameter objects that need not be CRDs. It avoids an external validation webhook for suitable logic, but errors/failurePolicy can still affect requests. Scope the binding and distinguish Audit from Deny. MAP mutation is a separate feature that became stable in 1.36.

</details>

---

7. What is KYAML, according to the verified release history?

   - A) An API-server validator that rejects all ordinary YAML anchors
   - B) A kubectl output format: alpha 1.34, beta 1.35–1.36, stable 1.37
   - C) A new EKS server-side feature enabled by support ticket
   - D) A requirement to convert every input manifest to YAML1.2

<details>
<summary>Show Answer</summary>

**Answer: B) A kubectl output format: alpha 1.34, beta 1.35–1.36, stable 1.37**

KYAML is KEP-5295. Native kubectl 1.36.2 tests accepted ordinary YAML anchors and emitted KYAML. KUBECTL_KYAML=false disabled that output printer, while KYAML input still parsed with JSON output. Formatting is separate from schema/admission validation. Upstream1.37 was already released by this review date; this does not imply EKS 1.37 availability.

</details>

---

8. Which EKS upgrade planning approach is appropriate?

   - A) Skip minor versions to save time
   - B) Rehearse each minor step, verify actual compatibility/ownership and prepare recovery
   - C) Treat a scanner exit0 as complete proof
   - D) Always update every addon in one fixed order after the control plane

<details>
<summary>Show Answer</summary>

**Answer: B) Rehearse each minor step, verify actual compatibility/ownership and prepare recovery**

Use the current support calendar, manifest/client-usage evidence, exact addon compatibility and compute-specific sequencing. Some prerequisites belong before the control-plane update. Track the actual update ID; validate readiness/data and distinguish Pod resize, node replacement and scaling. Native EKS rollback is conditional within 7 days of a completed in-place upgrade; it is not a database rollback or permission to bypass all controls.

</details>

---

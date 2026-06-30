# Kubernetes Version Features and Roadmap Quiz

1. What is the Kubernetes release cadence?
   - A) Once per year with major features
   - B) Approximately 3 releases per year, every ~4 months
   - C) Monthly patch releases with quarterly feature releases
   - D) Twice per year aligned with AWS re:Invent and Summit

<details>
<summary>Show Answer</summary>

**Answer: B) Approximately 3 releases per year, every ~4 months**

**Explanation:**
Kubernetes follows a ~4-month release cycle, producing approximately 3 minor version releases per year. Each release goes through an enhancement freeze, code freeze, and release candidate phase. Recent releases: 1.33 (Apr 2025), 1.34 (Aug 2025), 1.35 (Dec 2025), 1.36 (Apr 2026). Each version is then maintained with patch releases for approximately 14 months.

</details>

---

2. What is the difference between EKS Standard Support and Extended Support?
   - A) Standard is free, Extended requires an Enterprise license
   - B) Standard lasts 14 months at $0.10/cluster/hour; Extended adds 12 more months at $0.60/cluster/hour
   - C) Standard supports 3 versions, Extended supports all versions
   - D) Standard provides patches monthly, Extended provides patches weekly

<details>
<summary>Show Answer</summary>

**Answer: B) Standard lasts 14 months at $0.10/cluster/hour; Extended adds 12 more months at $0.60/cluster/hour**

**Explanation:**
Each Kubernetes version on EKS receives 14 months of standard support ($0.10/cluster/hour), followed by 12 months of extended support ($0.60/cluster/hour — 6x the cost). Total support is 26 months per version. Extended support is enabled by default. When a version exits extended support, clusters are auto-upgraded. This pricing difference incentivizes staying on supported versions.

</details>

---

3. In which Kubernetes version did Sidecar Containers graduate to GA?
   - A) 1.28 (when first introduced as alpha)
   - B) 1.31
   - C) 1.33
   - D) 1.35

<details>
<summary>Show Answer</summary>

**Answer: C) 1.33**

**Explanation:**
Native Sidecar Containers (KEP-753) followed this graduation path: alpha in v1.28 (Aug 2023), beta in v1.29 (Dec 2023), GA in v1.33 (Apr 2025). Sidecars are defined as init containers with `restartPolicy: Always`, ensuring they start before application containers, run throughout the Pod lifecycle, and terminate after main containers — solving the long-standing "zombie sidecar" problem in Jobs.

</details>

---

4. What is the In-Place Pod Resize feature and when did it reach GA?
   - A) Ability to change Pod replicas without redeployment; GA in 1.30
   - B) Ability to modify CPU/memory requests and limits on running Pods without restart; GA in 1.35
   - C) Ability to resize PersistentVolumes online; GA in 1.31
   - D) Ability to change container images on running Pods; GA in 1.34

<details>
<summary>Show Answer</summary>

**Answer: B) Ability to modify CPU/memory requests and limits on running Pods without restart; GA in 1.35**

**Explanation:**
In-Place Pod Resize (KEP-1287) makes CPU and memory requests/limits mutable on running Pods. Graduation: alpha in v1.27, beta in v1.33, GA in v1.35 (Dec 2025). Starting from v1.33, modifications use the `/resize` subresource. The `resizePolicy` field controls whether a container restart is needed per resource type. This feature is transformative for VPA integration, enabling resource right-sizing without Pod disruption.

</details>

---

5. What major change happened to Dynamic Resource Allocation (DRA) in Kubernetes 1.31?
   - A) DRA was deprecated and replaced by Device Plugins v2
   - B) Classic DRA was removed; only Structured Parameters DRA remained (which later reached GA in 1.34)
   - C) DRA graduated directly from alpha to GA
   - D) DRA added support for network devices alongside GPUs

<details>
<summary>Show Answer</summary>

**Answer: B) Classic DRA was removed; only Structured Parameters DRA remained (which later reached GA in 1.34)**

**Explanation:**
DRA underwent a major redesign. Classic DRA (KEP-3063, alpha since v1.26) used opaque vendor parameters that the scheduler and cluster autoscaler couldn't reason about. Structured Parameters DRA (KEP-4381) replaced it with a Kubernetes-native format using `ResourceSlice` objects. In v1.31, classic DRA was removed entirely. Structured DRA progressed: beta in v1.32, GA in v1.34. This is critical for GPU/accelerator scheduling in AI/ML workloads.

</details>

---

6. Which feature graduated to GA in Kubernetes 1.30 that enables declarative admission control without webhooks?
   - A) OPA Gatekeeper v4
   - B) Kyverno Native Policies
   - C) ValidatingAdmissionPolicy using CEL expressions
   - D) Pod Security Standards enforcement

<details>
<summary>Show Answer</summary>

**Answer: C) ValidatingAdmissionPolicy using CEL expressions**

**Explanation:**
ValidatingAdmissionPolicy (KEP-3488) provides in-process validation using Common Expression Language (CEL) expressions, eliminating the need for external webhook servers. Graduation: alpha in v1.26, beta in v1.28, GA in v1.30 (Apr 2024). It uses three resource types: ValidatingAdmissionPolicy (rules), ValidatingAdmissionPolicyBinding (binding to resources), and optional parameter CRDs. This reduces latency, complexity, and failure domains compared to webhook-based admission control.

</details>

---

7. What is KYAML and what is its current status?
   - A) A Kubernetes YAML linter; GA in 1.35
   - B) A safer, less ambiguous YAML subset for Kubernetes using strict formatting; beta in 1.35, enabled by default
   - C) A YAML-to-JSON converter tool; alpha in 1.34
   - D) A Kubernetes manifest validation schema; stable since 1.30

<details>
<summary>Show Answer</summary>

**Answer: B) A safer, less ambiguous YAML subset for Kubernetes using strict formatting; beta in 1.35, enabled by default**

**Explanation:**
KYAML is a stricter YAML subset designed specifically for Kubernetes that eliminates YAML's notorious ambiguities. It uses curly brackets ({}) for maps, square brackets ([]) for lists, and double quotes for all strings. Introduced as alpha in v1.34, it graduated to beta in v1.35 (Dec 2025) and is enabled by default. It can be disabled with `KUBECTL_KYAML=false`. This addresses long-standing issues like "Norway problem" (NO being interpreted as boolean false) in YAML.

</details>

---

8. What is the recommended version upgrade planning strategy for EKS clusters?
   - A) Skip versions to minimize upgrade frequency (e.g., 1.29 → 1.33)
   - B) Upgrade one minor version at a time, test feature gates in staging, verify API compatibility and add-on alignment before production
   - C) Always use the latest version and rely on extended support for rollback
   - D) Wait until a version reaches extended support before upgrading to ensure stability

<details>
<summary>Show Answer</summary>

**Answer: B) Upgrade one minor version at a time, test feature gates in staging, verify API compatibility and add-on alignment before production**

**Explanation:**
EKS requires sequential minor version upgrades (1.33 → 1.34 → 1.35; skipping is not supported). Best practices: (1) Test new feature gates and API changes in staging environments first, (2) Verify add-on compatibility with the target version, (3) Run `kubectl convert` to check for deprecated APIs, (4) Upgrade control plane first, then add-ons, then node groups. Staying on standard support avoids the 6x cost increase of extended support and ensures access to the latest security patches.

</details>

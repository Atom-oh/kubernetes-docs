# Feature Flags and OpenFeature Quiz

1. What is the key advantage of OpenFeature's Provider model?
   - A) Vendor lock-in provides optimal performance
   - B) Vendor-neutral API allows freely switching Feature Flag backends
   - C) Requires running your own Feature Flag server
   - D) Only supports REST API

<details>
<summary>Show Answer</summary>

**Answer: B) Vendor-neutral API allows freely switching Feature Flag backends**

**Explanation:**
OpenFeature is a CNCF standard that provides a vendor-neutral SDK API. Through the Provider interface, you can swap between backends like flagd, LaunchDarkly, Flagsmith, and others by only changing the Provider configuration — no application code changes required.

</details>

---

2. What is the difference between Sidecar and Standalone deployment modes for flagd on Kubernetes?
   - A) Sidecar has better performance, Standalone is easier to manage
   - B) Sidecar is injected into each Pod minimizing latency, Standalone runs as a central service
   - C) Sidecar only supports TCP, Standalone only supports HTTP
   - D) Sidecar uses CRDs, Standalone only uses ConfigMaps

<details>
<summary>Show Answer</summary>

**Answer: B) Sidecar is injected into each Pod minimizing latency, Standalone runs as a central service**

**Explanation:**
In Sidecar mode, the OpenFeature Operator injects a flagd container into each Pod, enabling local communication with minimal latency. In Standalone mode, flagd runs as a separate Deployment managed centrally, which is more resource-efficient but requires network calls.

</details>

---

3. What is the role of information included in a Feature Flag's Evaluation Context?
   - A) Pass build information to determine Flags at compile time
   - B) Evaluate targeting rules using context like user ID, region, and environment
   - C) Pass database connection information
   - D) Pass Kubernetes node information

<details>
<summary>Show Answer</summary>

**Answer: B) Evaluate targeting rules using context like user ID, region, and environment**

**Explanation:**
Evaluation Context is metadata dynamically passed during flag evaluation. It includes information such as user ID, region, environment (dev/staging/prod), and user groups. Targeting rules use this information to enable features for specific users or groups.

</details>

---

4. What is the role of Feature Flags in the Dark Launch pattern?
   - A) Completely hide a service and block access
   - B) Deploy new feature code but disable it via Flag so users don't see it
   - C) Switch servers to dark mode
   - D) Execute deployments only at night

<details>
<summary>Show Answer</summary>

**Answer: B) Deploy new feature code but disable it via Flag so users don't see it**

**Explanation:**
Dark Launch deploys new feature code to production but keeps it invisible to users via Feature Flags. The Flag is then gradually enabled for a subset of users for testing, and if no issues arise, it's rolled out to all users. This is a key pattern for separating deployment from release.

</details>

---

5. What is the advantage of Feature Flag as Code (GitOps)?
   - A) Flags can only be managed via GUI
   - B) Flag changes managed via Git PRs enable review, audit, and rollback
   - C) Flag evaluation becomes faster
   - D) Server resources are saved

<details>
<summary>Show Answer</summary>

**Answer: B) Flag changes managed via Git PRs enable review, audit, and rollback**

**Explanation:**
Feature Flag as Code manages FeatureFlag CRs in a Git repository, applying PR-based review and approval processes. Change history is recorded in Git for auditing, and issues can be quickly rolled back via Git revert. ArgoCD or Flux automatically syncs the changes.

</details>

---

6. What is the best practice for preventing technical debt from Feature Flags?
   - A) Keep all Flags permanently
   - B) Set expiration dates on Flags and clean up Flag code after release completion
   - C) Create Flags freely without limiting the count
   - D) Don't include dates in Flag names

<details>
<summary>Show Answer</summary>

**Answer: B) Set expiration dates on Flags and clean up Flag code after release completion**

**Explanation:**
Feature Flags are often used as temporary release tools. After a release is complete, the Flag and related conditional code should be cleaned up to prevent technical debt accumulation. Tag Flags with expiration dates and owners, and operate a process to regularly detect and remove unused Flags.

</details>

---

7. What is the core functionality provided by the OpenFeature Operator on Kubernetes?
   - A) Automatically inject flagd sidecars into Pods and manage FeatureFlag CRDs
   - B) Audit Kubernetes cluster security
   - C) Automatically build container images
   - D) Automatically configure HPA

<details>
<summary>Show Answer</summary>

**Answer: A) Automatically inject flagd sidecars into Pods and manage FeatureFlag CRDs**

**Explanation:**
The OpenFeature Operator is an Operator for natively managing Feature Flags in Kubernetes. It declaratively manages Flags via FeatureFlag CRDs, defines Flag sources via FeatureFlagSource CRDs, and automatically injects flagd sidecar containers into Pods with the appropriate annotations.

</details>

---

8. How does metrics-based auto-rollout work in the Flagger + Feature Flag combination?
   - A) Feature Flag directly controls traffic
   - B) Flagger handles Canary traffic shifting while Feature Flag controls gradual feature exposure at the application level
   - C) Feature Flag completely replaces Flagger
   - D) Both tools use identical metrics

<details>
<summary>Show Answer</summary>

**Answer: B) Flagger handles Canary traffic shifting while Feature Flag controls gradual feature exposure at the application level**

**Explanation:**
Flagger and Feature Flags operate at different levels. Flagger splits traffic at the infrastructure level and analyzes metrics to control deployment. Feature Flags control individual feature activation/deactivation at the application level. Using them together completely separates deployment (Flagger) from release (Feature Flags).

</details>

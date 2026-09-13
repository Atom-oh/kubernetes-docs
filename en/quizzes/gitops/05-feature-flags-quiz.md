# Feature Flags and OpenFeature Quiz

1. What is the key advantage of OpenFeature's Provider model?
   - A) Vendor lock-in provides optimal performance
   - B) A vendor-neutral evaluation API reduces code changes when switching backends
   - C) Requires running your own Feature Flag server
   - D) Only supports REST API

<details>
<summary>Show Answer</summary>

**Answer: B) A vendor-neutral evaluation API reduces code changes when switching backends**

**Explanation:**
OpenFeature's vendor-neutral SDK API reduces evaluation-code changes when switching backends. Flag keys, variants, targeting rules, context semantics, credentials, caching, and event behavior still require migration and testing.

</details>

---

2. What is the difference between Sidecar and Standalone deployment modes for flagd on Kubernetes?
   - A) Sidecar has better performance, Standalone is easier to manage
   - B) Sidecar runs inside an application Pod, while standalone serves evaluations through a shared Service
   - C) Sidecar only supports TCP, Standalone only supports HTTP
   - D) Sidecar uses CRDs, Standalone only uses ConfigMaps

<details>
<summary>Show Answer</summary>

**Answer: B) Sidecar runs inside an application Pod, while standalone serves evaluations through a shared Service**

**Explanation:**
RPC can call a sidecar locally or a shared Deployment through a Service. Measure actual latency and resource usage. Sidecar/shared deployment describes placement; RPC/in-process describes where evaluation happens. An in-process provider can synchronize rules and evaluate them inside the application.

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
Evaluation Context is metadata dynamically passed during flag evaluation. It includes information such as user ID, region, environment (dev/staging/prod), and user groups. Targeting rules use this information to enable features for specific users or groups. Use server-verified attributes for entitlement-related decisions; feature flags do not replace authentication or authorization.

</details>

---

4. What is the role of Feature Flags in the Dark Launch pattern?
   - A) Completely hide a service and block access
   - B) Return the existing result while testing new logic through side-effect-free shadow execution
   - C) Switch servers to dark mode
   - D) Execute deployments only at night

<details>
<summary>Show Answer</summary>

**Answer: B) Return the existing result while testing new logic through side-effect-free shadow execution**

**Explanation:**
Shadow validation returns the existing result and compares read-only calculations or isolated replays. It must not charge, write business records, or send notifications twice. Bound asynchronous concurrency and give background work its own timeout. This differs from a gradual release that actually exposes the new result to selected users.

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
Managing FeatureFlag CRs in Git provides PR review, change history, and Git revert. Consumers still need ArgoCD/Flux reconciliation, source synchronization, and SDK state updates. Self-healing can undo an emergency manual patch, so ownership and reconciliation behavior must be considered together.

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
Record owners and review dates, and check older application versions and other consumers before removing code and configuration. Expiration metadata does not itself delete a flag. Permanent operational flags may need periodic review rather than deletion.

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
The Operator manages resources including FeatureFlag and FeatureFlagSource. Pod injection uses the openfeature.dev/enabled and openfeature.dev/featureflagsource annotations. File-source ConfigMap volumes, direct Kubernetes access, and proxy sources follow different synchronization paths. The application still needs SDK integration.

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
Flagger controls workload delivery and traffic; feature flags control application behavior. They do not automatically form one transaction. Coordinated flag changes and rollback need real webhook or Git automation, authorization, and failure handling. Canary traffic percentages and user-cohort percentages also describe different populations.

</details>

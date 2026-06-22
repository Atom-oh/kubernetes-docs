# Flagger Progressive Delivery Quiz

1. In Flagger's Canary deployment, what does `stepWeight: 10`, `maxWeight: 50` mean?
   - A) Start traffic at 10% and incrementally increase to 50%, then promote to 100%
   - B) Create 10 Pods and scale up to a maximum of 50
   - C) Shift traffic to 50% at 10-second intervals
   - D) Allow up to 10% error rate and rollback at 50%

<details>
<summary>Show Answer</summary>

**Answer: A) Start traffic at 10% and incrementally increase to 50%, then promote to 100%**

**Explanation:**
`stepWeight` is the traffic percentage to increase at each analysis step, and `maxWeight` is the maximum traffic percentage the Canary can receive. Traffic increases 10% → 20% → 30% → 40% → 50%, and if all metrics pass, it promotes to 100%.

</details>

---

2. Under what condition does Flagger automatically rollback a Canary deployment?
   - A) When CPU usage exceeds 80%
   - B) When metric thresholds are exceeded for the configured number of consecutive failures
   - C) When Pod count exceeds maxReplicas
   - D) When deployment time exceeds 30 minutes

<details>
<summary>Show Answer</summary>

**Answer: B) When metric thresholds are exceeded for the configured number of consecutive failures**

**Explanation:**
Flagger evaluates defined metrics (request-success-rate, request-duration, etc.) at each analysis step. When the consecutive failure count reaches the `threshold`, it automatically performs a rollback, reverting Canary traffic to 0% and maintaining the original version.

</details>

---

3. What is the key difference between Flagger and Argo Rollouts?
   - A) Flagger only supports Canary, while Argo Rollouts only supports Blue-Green
   - B) Flagger integrates with the Flux ecosystem, while Argo Rollouts integrates with the Argo ecosystem
   - C) Flagger only supports Istio, while Argo Rollouts supports all meshes
   - D) Flagger doesn't support metrics analysis

<details>
<summary>Show Answer</summary>

**Answer: B) Flagger integrates with the Flux ecosystem, while Argo Rollouts integrates with the Argo ecosystem**

**Explanation:**
Flagger is part of the Flux/Flagger ecosystem and naturally integrates into GitOps workflows with FluxCD. Argo Rollouts is part of the Argo ecosystem alongside ArgoCD. Both support Canary, Blue-Green, and A/B Testing strategies, and both work with various service meshes and ingress controllers.

</details>

---

4. What is the role of `spec.analysis.mirror: true` in Flagger's Blue-Green deployment?
   - A) Mirror logs between Blue and Green environments
   - B) Replicate production traffic to the Canary (Green) for testing with real traffic
   - C) Mirror the database for synchronization
   - D) Keep configurations identical between both environments

<details>
<summary>Show Answer</summary>

**Answer: B) Replicate production traffic to the Canary (Green) for testing with real traffic**

**Explanation:**
`mirror: true` sends a copy of production traffic to the new version (Green) for testing with real traffic patterns. Mirrored responses are not returned to clients, allowing verification of the new version's behavior without impacting users.

</details>

---

5. What is the role of `templateRef` when using Custom Metrics analysis in Flagger?
   - A) Reference a Helm chart template
   - B) Reference a MetricTemplate CR to execute Prometheus/Datadog queries
   - C) Reference a Deployment template to create Pods
   - D) Reference a ConfigMap template

<details>
<summary>Show Answer</summary>

**Answer: B) Reference a MetricTemplate CR to execute Prometheus/Datadog queries**

**Explanation:**
`templateRef` references a MetricTemplate Custom Resource that contains Prometheus PromQL or Datadog queries. During the analysis phase, Flagger executes these queries and compares results against thresholds. This enables deployment decisions based on business metrics beyond standard HTTP metrics.

</details>

---

6. What is the purpose of pre-rollout testing using Flagger Webhooks?
   - A) Execute database migrations before deployment
   - B) Run load tests or conformance tests before traffic shifting to validate the new version
   - C) Create tags in the Git repository
   - D) Send Slack notifications

<details>
<summary>Show Answer</summary>

**Answer: B) Run load tests or conformance tests before traffic shifting to validate the new version**

**Explanation:**
Pre-rollout webhooks are invoked before traffic shifting begins. Typically, they run load tests (hey, wrk) or Helm tests via the Flagger loadtester to verify the new version performs basic operations correctly before exposing it to real users.

</details>

---

7. What is the correct sequence when using FluxCD Image Automation with Flagger?
   - A) New image tag detected → Git commit → Flux sync → Flagger Canary analysis
   - B) Flagger Canary analysis → New image tag detected → Git commit
   - C) Git commit → New image tag detected → Flux sync
   - D) Flux sync → Flagger Canary analysis → New image tag detected

<details>
<summary>Show Answer</summary>

**Answer: A) New image tag detected → Git commit → Flux sync → Flagger Canary analysis**

**Explanation:**
Flux Image Automation detects new image tags in the registry and creates a commit updating the manifests in the Git repository. When Flux syncs this change, the Deployment is updated, and Flagger detects the change to automatically begin the Canary analysis process.

</details>

---

8. How does header-based routing in Flagger's A/B Testing differ from regular Canary deployments?
   - A) A/B Testing exposes the new version to all users
   - B) Only requests matching specific HTTP header/cookie conditions are routed to the new version
   - C) A/B Testing doesn't support rollback
   - D) Header-based routing only applies to TCP traffic

<details>
<summary>Show Answer</summary>

**Answer: B) Only requests matching specific HTTP header/cookie conditions are routed to the new version**

**Explanation:**
In A/B Testing, traffic is classified based on HTTP header or cookie conditions defined in `spec.analysis.match`. Only requests matching these conditions are routed to the new version, allowing exposure of new features to specific user groups (beta testers, internal employees, etc.) while other users continue using the stable version.

</details>

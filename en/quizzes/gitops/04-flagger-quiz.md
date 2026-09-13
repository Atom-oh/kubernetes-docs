# Flagger Progressive Delivery Quiz

1. In Flagger's Canary deployment, what does `stepWeight: 10`, `maxWeight: 50` mean?
   - A) Increase analysis traffic by 10% up to 50%, then run promotion
   - B) Create 10 Pods and scale up to a maximum of 50
   - C) Shift traffic to 50% at 10-second intervals
   - D) Allow up to 10% error rate and rollback at 50%

<details>
<summary>Show Answer</summary>

**Answer: A) Increase analysis traffic by 10% up to 50%, then run promotion**

**Explanation:**
StepWeight is the analysis weight increment and maxWeight is its analysis target. Checks advance through 10→20→30→40→50%, followed by primary update/traffic promotion. Canary can temporarily receive all traffic during promotion; 50% is not a lifetime traffic ceiling.

</details>

---

2. Under what condition does Flagger automatically rollback a Canary deployment?
   - A) When CPU usage exceeds 80%
   - B) When failed checks for a revision reach threshold
   - C) When Pod count exceeds maxReplicas
   - D) When deployment time exceeds 30 minutes

<details>
<summary>Show Answer</summary>

**Answer: B) When failed checks for a revision reach threshold**

**Explanation:**
Flagger evaluates defined metrics (request-success-rate, request-duration, etc.) at each analysis step. Failed checks accumulate for a revision rather than resetting on every success. Reaching threshold causes rollback on subsequent reconciliation. Primary-promotion failures can require different recovery, including retaining the healthy canary.

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
Flagger is part of the Flux/Flagger ecosystem and naturally integrates into GitOps workflows with FluxCD. Argo Rollouts is part of the Argo ecosystem alongside ArgoCD. These ecosystem associations are not exclusive requirements. Flagger controls an existing workload through Canary, while Argo Rollouts uses Rollout and workloadRef support. Specific routing/experiment capabilities depend on the provider.

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
`mirror: true` sends a copy of production traffic to the new version (Green) for testing with real traffic patterns. Responses are discarded, but database writes, messages, payments, and extra load can still occur. Use verified read-only requests or isolation/idempotency controls.

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
Pre-rollout webhooks are invoked before traffic shifting begins. Run smoke/conformance tests with prepared tools and permissions. Asynchronous cmd load-test acceptance is not a quality verdict; blocking tests such as bash must complete within their timeout.

</details>

---

7. What is the correct sequence when using FluxCD Image Automation with Flagger?
   - A) Image selected → reviewed/merged Git change → Flux apply → Flagger analysis
   - B) Flagger Canary analysis → New image tag detected → Git commit
   - C) Git commit → New image tag detected → Flux sync
   - D) Flux sync → Flagger Canary analysis → New image tag detected

<details>
<summary>Show Answer</summary>

**Answer: A) Image selected → reviewed/merged Git change → Flux apply → Flagger analysis**

**Explanation:**
Image-reflector evaluates tags/policy and image-automation edits marked YAML. A separate push branch requires PR review/merge before Flux applies the source branch and Flagger observes the workload change. Flagger does not directly reconcile HelmRelease objects.

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
In A/B Testing, traffic is classified based on HTTP header or cookie conditions defined in `spec.analysis.match`. Only requests matching these conditions are routed to the new version, allowing cohort routing while other requests use stable. Client-controlled headers/cookies are not employee authorization or protection for sensitive features.

</details>

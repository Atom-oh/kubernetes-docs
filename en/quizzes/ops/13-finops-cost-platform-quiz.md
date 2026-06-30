# FinOps Cost Visibility Platform Quiz

1. What is the correct order of the three FinOps operating cycle phases?
   - A) Optimize → Inform → Operate
   - B) Inform → Optimize → Operate
   - C) Operate → Inform → Optimize
   - D) Inform → Operate → Optimize

<details>
<summary>Show Answer</summary>

**Answer: B) Inform → Optimize → Operate**

**Explanation:**
The FinOps cycle iterates through Inform (establish cost visibility) → Optimize (reduce costs) → Operate (governance). First understand who spends what and how much, then optimize, then manage with policies.

</details>

---

2. What is the primary reason for integrating AWS CUR (Cost and Usage Report) with Kubecost?
   - A) To reduce Kubecost license costs
   - B) To track AWS service costs outside Kubernetes
   - C) To improve Pod-level cost accuracy by matching actual AWS billing data
   - D) To enable multi-cluster federation

<details>
<summary>Show Answer</summary>

**Answer: C) To improve Pod-level cost accuracy by matching actual AWS billing data**

**Explanation:**
Kubecost estimates costs based on public list prices. CUR integration matches these estimates with actual billing data that reflects Savings Plans, Reserved Instances, and negotiated rates, significantly improving cost accuracy.

</details>

---

3. When enforcing cost labels with Kyverno, what does `validationFailureAction: Enforce` mean?
   - A) Show warnings for workloads without labels
   - B) Block deployment of workloads without required labels
   - C) Automatically add labels
   - D) Modify labels on existing workloads

<details>
<summary>Show Answer</summary>

**Answer: B) Block deployment of workloads without required labels**

**Explanation:**
`validationFailureAction: Enforce` blocks creation/modification of resources that violate the policy. Deployments without team, service, and cost-center labels will be rejected. It's recommended to start with `Audit` mode for warnings, then switch to `Enforce` when teams are ready.

</details>

---

4. Why set VPA to `updateMode: "Off"`?
   - A) To disable VPA entirely
   - B) To provide recommendations only without automatically restarting Pods
   - C) To adjust CPU only while keeping memory fixed
   - D) To prevent conflicts with HPA

<details>
<summary>Show Answer</summary>

**Answer: B) To provide recommendations only without automatically restarting Pods**

**Explanation:**
`updateMode: "Off"` makes VPA analyze resource usage and provide recommendations without automatically restarting Pods to apply changes. This supports a safe workflow where recommendations are reviewed and applied manually via PRs. The Goldilocks dashboard also leverages this mode.

</details>

---

5. What is the difference between Showback and Chargeback?
   - A) Showback displays costs, Chargeback hides costs
   - B) Showback provides cost visibility, Chargeback actually charges departments/teams
   - C) Showback is real-time, Chargeback is monthly
   - D) Showback is cloud-only, Chargeback is on-premises only

<details>
<summary>Show Answer</summary>

**Answer: B) Showback provides cost visibility, Chargeback actually charges departments/teams**

**Explanation:**
Showback shows each team/service how much they spend to raise awareness, while Chargeback actually deducts costs from department budgets. Most organizations start with Showback to establish a cost-aware culture before transitioning to Chargeback.

</details>

---

6. What label must a namespace have for Goldilocks to display resource recommendations?
   - A) goldilocks.fairwinds.com/vpa-enabled=true
   - B) goldilocks.fairwinds.com/enabled=true
   - C) vpa.kubernetes.io/enabled=true
   - D) monitoring.goldilocks.com/watch=true

<details>
<summary>Show Answer</summary>

**Answer: B) goldilocks.fairwinds.com/enabled=true**

**Explanation:**
Goldilocks automatically creates VPAs for all Deployments in namespaces labeled with `goldilocks.fairwinds.com/enabled=true` and visualizes recommended resource values in its web dashboard.

</details>

---

7. What does `aggregate=label:team` mean in the Kubecost Allocation API?
   - A) Filter only Pods with a team label
   - B) Group and sum costs by team label values
   - C) Create separate API calls per team
   - D) Automatically add team labels

<details>
<summary>Show Answer</summary>

**Answer: B) Group and sum costs by team label values**

**Explanation:**
`aggregate=label:team` instructs Kubecost to group all Pod costs by `team` label values (e.g., team-commerce, team-platform) and sum them, providing total cost, CPU cost, and memory cost per team in a single query.

</details>

---

8. Why does the cost anomaly alert require 30 minutes of sustained high cost before firing?
   - A) Prometheus scrape interval is 30 minutes
   - B) To prevent false positives from temporary spikes (deployments, autoscaling)
   - C) To avoid Slack API rate limits
   - D) Kubecost data refresh cycle is 30 minutes

<details>
<summary>Show Answer</summary>

**Answer: B) To prevent false positives from temporary spikes (deployments, autoscaling)**

**Explanation:**
Deployments, autoscaling events, and batch jobs can cause temporary cost spikes. The `for: 30m` condition ensures alerts fire only when costs remain elevated for 30+ minutes, reducing noise from normal operational activities.

</details>

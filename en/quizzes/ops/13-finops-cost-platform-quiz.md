# FinOps Cost Visibility Platform Quiz

1. Which best describes Inform → Optimize → Operate?
   - A) A one-time engineering-only cost cut
   - B) An iterative practice of visibility, improvement and shared ownership for technology value
   - C) A sequence every organization completes within six months
   - D) A finance process that automatically terminates all Pods

<details>
<summary>Show Answer</summary>

**Answer: B) An iterative practice of visibility, improvement and shared ownership for technology value**

Product, business, engineering and finance collaborate; service levels and unit economics matter alongside spending.

</details>

---

2. What does bucket identify in the OpenCost Cloud Cost Athena configuration?
   - A) Only the CUR source bucket
   - B) The Athena query-results bucket and prefix
   - C) Kubeconfig storage
   - D) A public bucket shared by all accounts

<details>
<summary>Show Answer</summary>

**Answer: B) The Athena query-results bucket and prefix**

Source reads and result writes need separate permissions. The real Glue table and importer freshness must also be verified.

</details>

---

3. Which statement about ValidatingPolicy validationActions: [Audit] is correct?
   - A) It deletes every existing Pod
   - B) It does not block violations; review reports before changing selected policies to Deny
   - C) It automatically adds missing labels
   - D) It ignores namespaceSelector

<details>
<summary>Show Answer</summary>

**Answer: B) It does not block violations; review reports before changing selected policies to Deny**

Audit and user-facing Warn are distinct. A local CLI test failure is not equivalent to admission denial.

</details>

---

4. What do VPA Off mode and this chapter's recommendation script actually do?
   - A) Immediately reduce node counts and bills
   - B) Observe recommendations and output proposals matched by container name
   - C) Automatically create and merge PRs
   - D) Apply upperBound as every container's limit

<details>
<summary>Show Answer</summary>

**Answer: B) Observe recommendations and output proposals matched by container name**

Manifest edits, PRs, performance tests and deployment are separate steps. Request reduction does not guarantee savings, so estimated billing savings are null.

</details>

---

5. What distinguishes showback from chargeback?
   - A) Showback provides visibility; chargeback allocates and bills under agreed rules
   - B) Showback is real-time and chargeback is always annual
   - C) Showback only supports AWS
   - D) Chargeback can ignore rounding and credits

<details>
<summary>Show Answer</summary>

**Answer: A) Showback provides visibility; chargeback allocates and bills under agreed rules**

Agree on periods, currency, shared/idle/unallocated costs, taxes, refunds and rounding. Model values do not automatically become internal invoices.

</details>

---

6. What does a panel multiplying the current Prometheus cost rate by 730 represent?
   - A) The finalized AWS bill for the month
   - B) An estimate assuming the current rate persists for a fixed 730 hours
   - C) An exact sum of observed daily costs
   - D) A final accounting amount including every discount and tax

<details>
<summary>Show Answer</summary>

**Answer: B) An estimate assuming the current rate persists for a fixed 730 hours**

Distinguish current rates, windowed model cost and billing cost. A linear month-end estimate is also sensitive to gaps and changing demand.

</details>

---

7. Does a team namespace variable in Grafana guarantee data isolation?
   - A) Yes, variables are datasource authorization
   - B) No; server-side datasource permissions or tenant isolation and denial tests are needed
   - C) Yes, an internal ALB also removes the need for authentication
   - D) Only if the label name is sufficiently long

<details>
<summary>Show Answer</summary>

**Answer: B) No; server-side datasource permissions or tenant isolation and denial tests are needed**

Dashboard filters and folders organize views. Verify whether users can issue different queries to the same datasource.

</details>

---

8. Which statement about for: 30m on a cost-rate alert is correct?
   - A) It changes the scrape interval to 30 minutes
   - B) It requires the condition to persist, reducing short-spike noise without eliminating false positives
   - C) It immediately refreshes AWS billing data
   - D) It guarantees exactly-once Slack delivery

<details>
<summary>Show Answer</summary>

**Answer: B) It requires the condition to persist, reducing short-spike noise without eliminating false positives**

Condition duration, data refresh, model accuracy and delivery guarantees are separate concerns. Missing metrics are not zero spending.

</details>

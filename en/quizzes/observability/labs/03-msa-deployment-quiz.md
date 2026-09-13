# Observability Lab 03 Quiz

<span id="observability-lab-part-3-msa-deployment-and-canary-quiz"></span>

> **Last Updated**: September 13, 2026

1. What is the order/outbox transaction boundary?
   - A) Commit the order then ignore failed messaging.
   - B) Both commit or roll back in one DB transaction.
   - C) SNS and DB are automatically atomic.
   - D) Initialize the DB for every request.

<details>
<summary>Show answer</summary>

**Answer: B) Both commit or roll back in one DB transaction.**

Validate DB rollback and retention of unpublished outbox records.

</details>

---

2. Who owns the payment workload?
   - A) Deployment and Rollout simultaneously.
   - B) A single Rollout.
   - C) KEDA and Rollout compete over replicas.
   - D) Grafana.

<details>
<summary>Show answer</summary>

**Answer: B) A single Rollout.**

Keep controller ownership and Git desired state explicit.

</details>

---

3. Why separate notification and analytics queues?
   - A) Competing on one queue is fanout.
   - B) So each consumer independently receives the same event.
   - C) SQS supports only one queue.
   - D) It eliminates all duplicates.

<details>
<summary>Show answer</summary>

**Answer: B) So each consumer independently receives the same event.**

SNS fanout and each consumer’s event-ID dedup are separate responsibilities.

</details>

---

4. What happens to an identical repeated synthetic payment?
   - A) Always create a new payment.
   - B) Reuse the stored result; conflicting values return409.
   - C) Charge a real card.
   - D) Always succeed even without an order.

<details>
<summary>Show answer</summary>

**Answer: B) Reuse the stored result; conflicting values return409.**

The lab implements no real payment gateway.

</details>

---

5. What if a crash occurs after SNS publication but before the DB mark?
   - A) Exactly once is automatic.
   - B) Redelivery is possible, so consumers need deduplication.
   - C) Delete every outbox row.
   - D) Always acknowledge the message.

<details>
<summary>Show answer</summary>

**Answer: B) Redelivery is possible, so consumers need deduplication.**

External side effects require additional idempotency contracts.

</details>

---

6. Which workload scales with SQS backlog?
   - A) Always only the API producer.
   - B) That queue’s consumer.
   - C) The database admin.
   - D) The NLB.

<details>
<summary>Show answer</summary>

**Answer: B) That queue’s consumer.**

KEDA reads queue attributes; it does not consume messages.

</details>

---

7. What should the canary success query select?
   - A) All stable and canary traffic.
   - B) Only the new pod-template revision.
   - C) Every namespace.
   - D) Only the predeployment average.

<details>
<summary>Show answer</summary>

**Answer: B) Only the new pod-template revision.**

Do not let large stable traffic hide a failing canary.

</details>

---

8. How should empty/NaN/Inf results be treated?
   - A) Always100% success.
   - B) Do not pass the success condition.
   - C) Convert all to zero and pass.
   - D) Metrics are unnecessary.

<details>
<summary>Show answer</summary>

**Answer: B) Do not pass the success condition.**

Check minimum request counts and observability together.

</details>

---

9. Which labels belong in metrics?
   - A) Every order ID.
   - B) Service, bounded route, status and revision.
   - C) Customer/card data.
   - D) The full request body.

<details>
<summary>Show answer</summary>

**Answer: B) Service, bounded route, status and revision.**

Unique IDs create cardinality/privacy problems; use trace/log correlation appropriately.

</details>

---

10. What does Rollout abort mean?
   - A) Git automatically reverts.
   - B) It is separate from Git revert or desired-image restoration; restore the source of truth explicitly.
   - C) All DB writes roll back.
   - D) The new image is permanently deleted.

<details>
<summary>Show answer</summary>

**Answer: B) It is separate from Git revert or desired-image restoration; restore the source of truth explicitly.**

Do not use direct Helm and ArgoCD as simultaneous owners.

</details>

---

[Return to the guide](../../../labs/observability/03-msa-deployment-lab.md)

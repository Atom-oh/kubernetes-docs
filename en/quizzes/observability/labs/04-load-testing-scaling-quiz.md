# Observability Lab Part 4 Quiz

> **Last Updated**: September 13, 2026

1. How do k6 VUs relate to RPS?
   - A) One VU always equals one RPS.
   - B) VUs are concurrent execution contexts; RPS also depends on requests, latency and sleep.
   - C) VUs equal the node count.
   - D) RPS is independent of response time.

<details>
<summary>Show answer</summary>

**Answer: B) VUs are concurrent execution contexts; RPS also depends on requests, latency and sleep.**

Equal VUs do not imply equal throughput across different workloads and waits.

</details>

---

2. How should failed k6 checks fail CI?
   - A) Calling check always exits with code 1.
   - B) Set a checks/failure-rate threshold and inspect the exit code.
   - C) A summary JSON file proves success.
   - D) Count only HTTP 200 responses.

<details>
<summary>Show answer</summary>

**Answer: B) Set a checks/failure-rate threshold and inspect the exit code.**

HTTP success and business success differ; assert JSON, IDs and payment state too.

</details>

---

3. Which order IDs should the load test read?
   - A) Random IDs from 1 to 1000.
   - B) IDs actually created by the test.
   - C) Customer IDs.
   - D) HTTP status codes.

<details>
<summary>Show answer</summary>

**Answer: B) IDs actually created by the test.**

Use creation-response IDs so random 404s do not contaminate the workload.

</details>

---

4. What should scale directly with SQS backlog?
   - A) Always only the API producer.
   - B) The consumer processing that queue.
   - C) Alertmanager replicas.
   - D) The queue name.

<details>
<summary>Show answer</summary>

**Answer: B) The consumer processing that queue.**

KEDA reads queue attributes and manages scaling with HPA; it does not consume messages.

</details>

---

5. When does KEDA cooldownPeriod apply?
   - A) Every 10-to-9 replica change.
   - B) When scaling to zero after the last active trigger.
   - C) EC2 boot delay.
   - D) Log retention.

<details>
<summary>Show answer</summary>

**Answer: B) When scaling to zero after the last active trigger.**

Inspect HPA behavior and stabilization windows for scaling within 1..N replicas.

</details>

---

6. What does an HPA scale-down stabilization window do?
   - A) Freezes all nodes.
   - B) Considers the highest replica recommendation within the window.
   - C) Uses only instantaneous CPU.
   - D) Deletes a Pod every configured interval.

<details>
<summary>Show answer</summary>

**Answer: B) Considers the highest replica recommendation within the window.**

It is not simply an unconditional fixed delay; policies and recommendation history matter.

</details>

---

7. Which problem can Karpenter normally address?
   - A) A misspelled image name.
   - B) An unschedulable Pod needing capacity compatible with its NodePool.
   - C) An application syntax error.
   - D) An incorrect database password.

<details>
<summary>Show answer</summary>

**Answer: B) An unschedulable Pod needing capacity compatible with its NodePool.**

More nodes do not fix image pulls or application bugs; inspect scheduling reasons first.

</details>

---

8. What does kube_deployment_status_replicas measure?
   - A) Always ready replicas.
   - B) Total Deployment replicas, distinct from ready replicas.
   - C) All controller replicas including Rollouts.
   - D) Node count.

<details>
<summary>Show answer</summary>

**Answer: B) Total Deployment replicas, distinct from ready replicas.**

Use kube_deployment_status_replicas_ready for ready replicas; Rollouts need their own state/exporter.

</details>

---

9. How should Running Pods be counted from phase metrics?
   - A) Count all Running series without filtering values.
   - B) Sum Running series whose value equals 1.
   - C) Sum Pod-name lengths.
   - D) Always return three.

<details>
<summary>Show answer</summary>

**Answer: B) Sum Running series whose value equals 1.**

Running phase series can exist with value zero, so an unfiltered count overcounts.

</details>

---

10. What is evidence of a successful load experiment?
   - A) A table copied from expected documentation numbers.
   - B) Measured requests, errors, latency, queue, replicas, nodes and exit status.
   - C) Successful Job creation.
   - D) Only a lower node count.

<details>
<summary>Show answer</summary>

**Answer: B) Measured requests, errors, latency, queue, replicas, nodes and exit status.**

Do not present unmeasured throughput, availability or cost savings as results.

</details>

---

[Return to the guide](../../../labs/observability/04-load-testing-scaling-lab.md)

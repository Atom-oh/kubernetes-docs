# EKS Spot Production Experiments Quiz

> **Related guide**: [EKS Spot Production Experiments and Result Assessment](../../ops/17-spot-production-experiments.md)

## 1. A drain test passes on a Spot node with a PDB. What does this establish?

- A) Actual Spot reclamation always preserves the same availability
- B) The voluntary eviction path works; actual reclamation needs a separate test
- C) EC2 waits for the PDB before terminating the instance
- D) The application always receives two minutes to exit

<details>
<summary>Show Answer</summary>

**Answer: B) The voluntary eviction path works; actual reclamation needs a separate test**

**Explanation:** A PDB cannot prevent EC2 instance loss. Test notice delivery, eviction delay, forced termination, and service impact through actual reclamation and loss without notice.

</details>

## 2. A Pending Pod has a Spot-only selector. What happens if you add an On-Demand node?

- A) The Pod moves immediately regardless of its selector
- B) The PDB changes the selector to On-Demand
- C) The Pod remains ineligible for the On-Demand node
- D) NodePool weight overrides the selector

<details>
<summary>Show Answer</summary>

**Answer: C) The Pod remains ineligible for the On-Demand node**

**Explanation:** Fallback requires both available capacity and compatible Pod constraints. Broadening NodePool capacity types alone does not remove a Spot-only Pod selector.

</details>

## 3. A service starts after changing a NodePool to On-Demand-only. What did the drill verify?

- A) Automatic fallback after EC2 returns insufficient Spot capacity
- B) Configuration-based transition, scheduling, and startup on On-Demand
- C) Guaranteed Spot supply in every AZ
- D) Immediate relocation of all existing Spot Pods

<details>
<summary>Show Answer</summary>

**Answer: B) Configuration-based transition, scheduling, and startup on On-Demand**

**Explanation:** The drill did not inject a capacity error. Verify the actual provisioning path's error handling and fallback separately; leave it unverified if it cannot be reproduced.

</details>

## 4. FIS reports `completed` and the replacement node is Ready. What establishes a service-level pass?

- A) The FIS state alone
- B) Node Ready alone
- C) Client errors, latency, throughput, and correctness all meet the criteria
- D) No LB 5xx responses, ignoring client timeouts

<details>
<summary>Show Answer</summary>

**Answer: C) Client errors, latency, throughput, and correctness all meet the criteria**

**Explanation:** FIS completion describes injection. Service recovery also requires Pod readiness, LB target health, actual request success, and work correctness.

</details>

## 5. Which comparison correctly assesses Spot savings?

- A) Report the Spot discount as the service saving
- B) Compare effective cost per unique successful operation passing correctness checks under equivalent conditions
- C) Exclude retry and On-Demand replacement costs
- D) Count replacement overlap in both the EC2 bill and an additional-cost line

<details>
<summary>Show Answer</summary>

**Answer: B) Compare effective cost per unique successful operation passing correctness checks under equivalent conditions**

**Explanation:** Include overhead, commitment discounts, replacements, and retries without counting charges twice. Label short-run monthly extrapolations as estimates.

</details>

## 6. How should results be recorded when no experiment data exists?

- A) Enter expected recovery times as measurements
- B) Enter zero errors and pass
- C) Record NOT RUN and missing measurements; hold production expansion
- D) Treat official documentation as a completed experiment

<details>
<summary>Show Answer</summary>

**Answer: C) Record NOT RUN and missing measurements; hold production expansion**

**Explanation:** Documented behavior, hypotheses, and measurements are different evidence. Missing run IDs and raw results cannot establish production readiness.

</details>

## 7. E2's mixed path had 0.0556% overall errors and 0.8333% in its worst full 60-second window. If the 60-second criterion is 0.1%, what follows?

- A) Pass because the overall error rate is low
- B) Ignore failures because p99 is low
- C) The window criterion failed; address the configuration and repeat testing
- D) Spot cannot be used in any production service

<details>
<summary>Show Answer</summary>

**Answer: C) The window criterion failed; address the configuration and repeat testing**

**Explanation:** A long healthy tail can lower the overall error rate. Match the assessment window to the actual business SLO, and do not generalize one synthetic run to every configuration.

</details>

## 8. A Pod is Guaranteed from creation. Its target regular container's CPU request and limit both decrease from 200m to 50m. Memory request=limit stays at 64Mi, and all other containers retain Guaranteed resource settings. What follows?

- A) Reducing CPU necessarily changes the Pod to Burstable
- B) The Pod preserves its original Guaranteed class, with equal CPU and memory requests and limits after downscale
- C) The same resize can also turn a Pod created as Burstable into Guaranteed
- D) Equal CPU values preserve Guaranteed even when the memory request and limit differ

<details>
<summary>Show Answer</summary>

**Answer: B) The Pod preserves its original Guaranteed class, with equal CPU and memory requests and limits after downscale**

**Explanation:** QoS class is determined at creation and cannot change through resize. This container-level design keeps each applicable container's CPU and memory requests equal to their corresponding positive limits, reducing the target CPU request and limit together. Preserving Guaranteed neither proves application SLOs after downscale nor prevents Spot reclamation.

</details>

## 9. What evidence establishes initialization completion, applied CPU downscale, and service quality after downscale in E10?

- A) A Running Pod satisfies all three conditions
- B) A successful pods/resize PATCH proves initialization, completed downscale, and SLO compliance
- C) Verify a real startupProbe and started=true, desired versus reported resources, generations and resize status, plus application SLOs after downscale
- D) An unchanged containerID and Guaranteed class make request-error and latency checks unnecessary

<details>
<summary>Show Answer</summary>

**Answer: C) Verify a real startupProbe and started=true, desired versus reported resources, generations and resize status, plus application SLOs after downscale**

**Explanation:** Running or the started value alone does not establish initialization completion; every target needs a startupProbe that checks actual initialization. PATCH success is request acceptance, so check kubelet-reported resources, observed generations, PodResizePending, and PodResizeInProgress. Once the resize has been applied, assess quality separately using readiness/LB status and application SLO evidence, including errors, p99, throughput, and throttling.

</details>

## 10. What can the 2026-09-12 Spot measurements and published initial template establish about phase-aware CPU resize?

- A) E2's low overall p99 proves the benefit of increased startup CPU
- B) The initial template and measurements lack the phase-aware configuration and required evidence, so E10 remains NOT RUN
- C) The initial template alone establishes observed Pod resources and QoS after admission
- D) The roadmap's historical report and local prototype checks also complete the combined Spot experiment

<details>
<summary>Show Answer</summary>

**Answer: B) The initial template and measurements lack the phase-aware configuration and required evidence, so E10 remains NOT RUN**

**Explanation:** The three initial Deployments request 50m/64Mi with limits of 500m/256Mi; those settings themselves do not meet Guaranteed requirements. They lack phase-aware resize opt-in, resizePolicy, and startupProbe, and there is no before/after evidence of actual resources, QoS, or comparative warmup performance. The initial template is not a Pod observation after admission. Keep the historical roadmap report, local prototype checks, and Spot measurements distinct, and run E10 separately.

</details>

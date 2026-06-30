# Event Capacity Planning Playbook Quiz

1. When multiple triggers (Cron + Prometheus + SQS) are configured on a KEDA ScaledObject, how is the final replica count determined?
   - A) Average of all trigger values
   - B) Lowest value (MIN)
   - C) Highest value (MAX)
   - D) Value from the first trigger

<details>
<summary>Show Answer</summary>

**Answer: C) Highest value (MAX)**

**Explanation:**
When multiple triggers are configured, KEDA selects the highest desired replica count among all triggers. This enables the "cron sets the floor, metrics determine the ceiling" pattern. For example, if cron requests 100 and Prometheus requests 150, the result is 150.

</details>

---

2. In the Pause Pod pattern, what mechanism causes Pause Pods to be evicted when real workloads arrive?
   - A) Pods are automatically replaced due to small resource requests
   - B) Low PriorityClass value triggers Preemption
   - C) DaemonSet automatically redistributes Pods
   - D) TTL expiration causes automatic deletion

<details>
<summary>Show Answer</summary>

**Answer: B) Low PriorityClass value triggers Preemption**

**Explanation:**
Pause Pods are assigned a PriorityClass with value: -10. When real workloads (default priority 0 or higher) need to be scheduled and there isn't enough capacity, the Kubernetes Scheduler preempts lower-priority Pods to free up space. This allows real workloads to be scheduled instantly on already-provisioned Nodes.

</details>

---

3. Why is the KEDA cron trigger set to fire 30 minutes before the flash sale starts?
   - A) KEDA's polling interval is 30 minutes
   - B) Cron triggers don't fire at exact times
   - C) Node provisioning and Pod scheduling require lead time
   - D) To avoid AWS API throttling

<details>
<summary>Show Answer</summary>

**Answer: C) Node provisioning and Pod scheduling require lead time**

**Explanation:**
When KEDA scales up Pods, Karpenter needs 60-90 seconds to provision new Nodes, plus additional time for Pod scheduling and container startup. Starting the scale-up 30 minutes early ensures all Pods are in Ready state before the first traffic surge hits.

</details>

---

4. Why is the EC2 Capacity Reservation set with `instance_match_criteria = "targeted"`?
   - A) To reduce costs
   - B) To restrict only specific Karpenter NodePools to use the reservation
   - C) To enable use with Spot instances
   - D) For multi-AZ deployment

<details>
<summary>Show Answer</summary>

**Answer: B) To restrict only specific Karpenter NodePools to use the reservation**

**Explanation:**
The `targeted` setting ensures only instances that explicitly reference the Capacity Reservation can use it. This prevents general workloads from consuming the reserved capacity meant for the event-specific Karpenter NodePool (matched via capacityReservationSelectorTerms).

</details>

---

5. What is the effect of a high `weight` value on a Karpenter NodePool?
   - A) Nodes are provisioned faster
   - B) The NodePool is preferred over other NodePools
   - C) More Nodes can be provisioned
   - D) Lower-cost instances are selected

<details>
<summary>Show Answer</summary>

**Answer: B) The NodePool is preferred over other NodePools**

**Explanation:**
When multiple NodePools can satisfy a Pending Pod's requirements, Karpenter selects the NodePool with the highest weight. Setting weight: 100 on the event NodePool ensures it is used before the default NodePool (e.g., weight: 10), applying the event-specific configuration (instance types, capacity types, etc.).

</details>

---

6. In HPA scaleDown behavior, what does `type: Percent, value: 10, periodSeconds: 120` mean?
   - A) Scale down to 10% of total within 120 seconds
   - B) Reduce by 10% of current Pods every 120 seconds
   - C) Remove 120 Pods every 10 seconds
   - D) Maintain minimum 10 Pods then remove all after 120 seconds

<details>
<summary>Show Answer</summary>

**Answer: B) Reduce by 10% of current Pods every 120 seconds**

**Explanation:**
This policy allows reducing up to 10% of the current replica count every 120 seconds (2 minutes). With 200 Pods, this means removing at most 20 Pods every 2 minutes, preventing service instability from sudden scale-down.

</details>

---

7. Why does the capacity planning worksheet add a 30% safety margin?
   - A) To account for AWS instance price fluctuations
   - B) To cover prediction errors, Pod startup time, and uneven load distribution
   - C) To account for Kubernetes system Pod resource usage
   - D) Due to network bandwidth limitations

<details>
<summary>Show Answer</summary>

**Answer: B) To cover prediction errors, Pod startup time, and uneven load distribution**

**Explanation:**
The 30% safety margin absorbs multiple uncertainties: (1) traffic predictions may be inaccurate, (2) Pods don't all become ready simultaneously, (3) load isn't perfectly distributed across Pods, (4) some Nodes/Pods may fail. The margin can be adjusted based on post-mortem data from previous events.

</details>

---

8. Why does the image pre-caching DaemonSet use initContainers?
   - A) To run and terminate images to save resources
   - B) To download (pull) images to the Node cache and exit, leaving only the cache
   - C) To validate image versions
   - D) To authenticate with the Container Registry

<details>
<summary>Show Answer</summary>

**Answer: B) To download (pull) images to the Node cache and exit, leaving only the cache**

**Explanation:**
DaemonSet initContainers run on every Node and pull the container images. They execute only `echo cached` and exit, but the images remain in the Node's local cache. When actual workload Pods are later scheduled, they skip the image pull phase (which can take tens of seconds to minutes), significantly reducing Pod startup time.

</details>

---

9. Why does the D-30 timeline call for load testing at 120% of the target RPM?
   - A) To get pre-approval from AWS for high traffic
   - B) To verify system stability beyond target traffic and discover bottlenecks early
   - C) To accurately calculate KEDA trigger thresholds
   - D) To improve cost estimation accuracy

<details>
<summary>Show Answer</summary>

**Answer: B) To verify system stability beyond target traffic and discover bottlenecks early**

**Explanation:**
Actual event traffic may exceed predictions, so testing at 120% helps: (1) confirm system stability above target, (2) discover bottlenecks in DB connections, network bandwidth, API gateways, etc., and (3) validate the actual scaling chain (KEDA → HPA → Karpenter) behavior before the real event.

</details>

---

10. Which situation most warrants using On-Demand instances instead of Spot for an event?
    - A) Event duration exceeds 4 hours
    - B) Spot savings exceed 60%
    - C) Revenue-critical service where interruptions are not acceptable
    - D) Workload has retry logic implemented

<details>
<summary>Show Answer</summary>

**Answer: C) Revenue-critical service where interruptions are not acceptable**

**Explanation:**
Spot instances can be reclaimed by AWS with 2-minute notice. Revenue-critical services like order processing during a flash sale should use On-Demand to guarantee availability. Auxiliary services like email notifications or log processing can use Spot if they have retry logic, saving costs while maintaining resilience.

</details>

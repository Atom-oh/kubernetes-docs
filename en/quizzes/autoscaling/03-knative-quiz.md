# Knative Quiz

> **Last Updated**: September 11, 2026

1. How does Scale-to-Zero work in Knative Serving?
   - A) Delete Pods and recreate the Deployment on new requests
   - B) Activator buffers eligible requests while the autoscaling path activates ready replicas
   - C) Shut down Nodes and have Karpenter provision new ones on request
   - D) Pause containers and resume them on request

<details>
<summary>Show Answer</summary>

**Answer: B) Activator buffers eligible requests while the autoscaling path activates ready replicas**

**Explanation:**
At zero replicas, the routing path uses the Activator, which buffers within its capacity and timeout limits while activation creates ready capacity. Failures, exhausted buffers or client/request timeouts can still cause errors. A positive min-scale avoids normal idle scale-to-zero, but does not eliminate initialization for new Revisions, restarts or additional replicas.

</details>

---

2. What distinguishes the KPA and HPA integrations in Knative Serving?
   - A) KPA is CPU-based only, HPA is memory-based only
   - B) KPA scales based on concurrency and supports Scale-to-Zero, while HPA scales based on CPU/memory
   - C) KPA scales nodes, HPA scales Pods
   - D) KPA is manual scaling, HPA is automatic scaling

<details>
<summary>Show Answer</summary>

**Answer: B) KPA scales based on concurrency and supports Scale-to-Zero, while HPA scales based on CPU/memory**

**Explanation:**
Knative KPA supports concurrency/RPS and its Activator-based zero path. The optional Knative HPA extension supports CPU, memory and supported custom Pod metrics, and does not implement that zero path. This is not a universal claim about Kubernetes HPA: upstream Kubernetes1.37 has beta scale-to-zero for object/external metrics. In the1.23 HPA implementation CPU targets are percentage utilization of CPU requests, memory targets are MiB, and custom metrics use per-Pod average values.

</details>

---

3. What is the role of a Trigger in Knative Eventing's Broker/Trigger pattern?
   - A) A source that generates events
   - B) Filters events from the Broker and routes them to specific services
   - C) Persistent storage for events
   - D) A gateway that sends events to external systems

<details>
<summary>Show Answer</summary>

**Answer: B) Filters events from the Broker and routes them to specific services**

**Explanation:**
A Trigger describes filtering and a subscriber for one Broker; controllers and the Broker dataplane implement delivery. Several matching Triggers may deliver copies of the same event, and retry/backing-store behavior depends on the implementation and policy. A Trigger is not a persistent event store or a generic consumer autoscaler.

</details>

---

4. What happens when you set `containerConcurrency: 1` on a Knative Service?
   - A) Only 1 Pod is created per container
   - B) Queue Proxy forwards at most one concurrent request per Pod, with bounded waiting and asynchronous scaling
   - C) Only one request per second is allowed
   - D) Only one Revision is maintained

<details>
<summary>Show Answer</summary>

**Answer: B) Queue Proxy forwards at most one concurrent request per Pod, with bounded waiting and asynchronous scaling**

**Explanation:**
Queue Proxy limits the number of concurrent requests forwarded to the receiving container in each Pod. Extra requests may wait in bounded queues, be sent to available capacity, or fail. Autoscaling is asynchronous and constrained by limits and node capacity. This is not one request per second, one global request across all replicas, or a guarantee that every extra request gets a new Pod.

</details>

---

5. What is an appropriate scenario for using KEDA and Knative together?
   - A) The two tools are incompatible; use only one
   - B) Use Knative Serving for HTTP workloads and KEDA for queue/stream-based async workloads
   - C) Let KEDA and KPA independently scale the same Knative-generated Deployment
   - D) Every Knative Service automatically installs KEDA and uses it as its default autoscaler

<details>
<summary>Show Answer</summary>

**Answer: B) Use Knative Serving for HTTP workloads and KEDA for queue/stream-based async workloads**

**Explanation:**
Use Knative Serving for suitable HTTP services and KEDA for independently managed background workers. Configure queue retention/acknowledgements, activation metrics and worker idempotency. Do not let KEDA and KPA independently control the same generated Deployment. SinkBinding configures event producers; it does not wake an arbitrary HTTP consumer scaled to zero.

</details>

---

6. How do you implement Canary deployments using traffic splitting in Knative?
   - A) Adjust Deployment replicas
   - B) Specify traffic percentages per Revision in the Knative Service's spec.traffic
   - C) Manually create an Istio VirtualService
   - D) Adjust HPA minReplicas

<details>
<summary>Show Answer</summary>

**Answer: B) Specify traffic percentages per Revision in the Knative Service's spec.traffic**

**Explanation:**
spec.traffic contains explicit revisionName targets or latestRevision: true with percentages. @latest is a kn CLI shorthand, not a revisionName value or an API tag that means latest. Referenced Revisions must exist and be ready; route reconciliation is not an instantaneous global cutover, and existing requests can continue on the old Revision.

</details>

---

7. What is the purpose of a Dead Letter Sink in Knative?
   - A) Archive deleted Knative Services
   - B) Attempt delivery to a configured alternative destination when subscriber delivery fails
   - C) Clean up expired Revisions
   - D) Store debug logs

<details>
<summary>Show Answer</summary>

**Answer: B) Attempt delivery to a configured alternative destination when subscriber delivery fails**

**Explanation:**
A configured DLS is an alternative destination after the delivery policy cannot deliver to the subscriber. The DLS itself can fail; event retention and successful persistence depend on the transport and handler. Acknowledge only after the intended storage/processing succeeds and deduplicate by the CloudEvent source plus id where required.

</details>

---

8. Which combination can reduce cold-start latency while keeping an explicit warm-capacity policy?
   - A) Reduce container image size infinitely
   - B) Maintain minimum instances with `minScale` annotation and use lightweight images with fast-starting frameworks
   - C) Completely disable Scale-to-Zero
   - D) Always keep Nodes at maximum count

<details>
<summary>Show Answer</summary>

**Answer: B) Maintain minimum instances with `minScale` annotation and use lightweight images with fast-starting frameworks**

**Explanation:**
A positive autoscaling.knative.dev/min-scale keeps baseline capacity for ordinary idle periods, while initial-scale applies when a Revision is first created. Image size, node availability, image cache, startup and readiness behavior affect latency. New Revisions, restarts and scale-out beyond the warm baseline can still cold-start; measure representative traffic instead of promising elimination.

</details>

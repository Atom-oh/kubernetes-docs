# Knative Quiz

1. How does Scale-to-Zero work in Knative Serving?
   - A) Delete Pods and recreate the Deployment on new requests
   - B) Activator buffers traffic while Autoscaler scales replicas from 0 to 1
   - C) Shut down Nodes and have Karpenter provision new ones on request
   - D) Pause containers and resume them on request

<details>
<summary>Show Answer</summary>

**Answer: B) Activator buffers traffic while Autoscaler scales replicas from 0 to 1**

**Explanation:**
When replicas are at 0, incoming requests are buffered by the Activator. The Activator requests a scale-up from the Autoscaler, and once Pods are ready, buffered requests are forwarded. This process is the "cold start," which can be prevented by setting `minScale` to maintain minimum instances.

</details>

---

2. What is the key difference between KPA (Knative Pod Autoscaler) and HPA?
   - A) KPA is CPU-based only, HPA is memory-based only
   - B) KPA scales based on concurrency and supports Scale-to-Zero, while HPA scales based on CPU/memory
   - C) KPA scales nodes, HPA scales Pods
   - D) KPA is manual scaling, HPA is automatic scaling

<details>
<summary>Show Answer</summary>

**Answer: B) KPA scales based on concurrency and supports Scale-to-Zero, while HPA scales based on CPU/memory**

**Explanation:**
KPA scales based on concurrent requests or RPS measured by Queue Proxy and natively supports Scale-to-Zero. HPA scales based on CPU/memory metrics but requires at least 1 replica at all times.

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
Triggers are registered with a Broker and filter CloudEvents based on attributes (type, source, etc.). Only matching events are delivered to the specified Subscriber (Knative Service, Kubernetes Service, etc.). Multiple Triggers can be registered on a single Broker to route events to different services.

</details>

---

4. What happens when you set `containerConcurrency: 1` on a Knative Service?
   - A) Only 1 Pod is created per container
   - B) Each container processes one request at a time; additional requests are routed to new Pods
   - C) Only one request per second is allowed
   - D) Only one Revision is maintained

<details>
<summary>Show Answer</summary>

**Answer: B) Each container processes one request at a time; additional requests are routed to new Pods**

**Explanation:**
`containerConcurrency: 1` configures the Queue Proxy in each Pod to forward only one concurrent request to the container. When additional requests arrive, the Autoscaler creates new Pods. This is useful for CPU-intensive tasks or non-thread-safe applications.

</details>

---

5. What is an appropriate scenario for using KEDA and Knative together?
   - A) The two tools are incompatible; use only one
   - B) Use Knative Serving for HTTP workloads and KEDA for queue/stream-based async workloads
   - C) Use KEDA for Scale-to-Zero and Knative for event routing
   - D) Knative uses KEDA internally

<details>
<summary>Show Answer</summary>

**Answer: B) Use Knative Serving for HTTP workloads and KEDA for queue/stream-based async workloads**

**Explanation:**
Knative Serving is optimized for HTTP request-based serverless workloads with Scale-to-Zero and concurrency-based scaling. KEDA excels at scaling based on queue metrics from SQS, Kafka, Redis, etc. Using both together allows scaling synchronous and asynchronous workloads optimally.

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
The `spec.traffic` field in a Knative Service allows specifying traffic percentages per Revision. For example, assign 90% to the existing Revision and 10% to the new Revision for a canary deployment. Use `@latest` to reference the latest Revision or specify Revision names directly.

</details>

---

7. What is the purpose of a Dead Letter Sink in Knative?
   - A) Archive deleted Knative Services
   - B) Send failed events to a separate destination to prevent event loss
   - C) Clean up expired Revisions
   - D) Store debug logs

<details>
<summary>Show Answer</summary>

**Answer: B) Send failed events to a separate destination to prevent event loss**

**Explanation:**
A Dead Letter Sink forwards events to a designated destination (another Knative Service, Kubernetes Service, etc.) when delivery fails after retries. This prevents event loss and enables analysis or reprocessing of failed events.

</details>

---

8. What is the most effective way to minimize cold starts in Knative Serving?
   - A) Reduce container image size infinitely
   - B) Maintain minimum instances with `minScale` annotation and use lightweight images with fast-starting frameworks
   - C) Completely disable Scale-to-Zero
   - D) Always keep Nodes at maximum count

<details>
<summary>Show Answer</summary>

**Answer: B) Maintain minimum instances with `minScale` annotation and use lightweight images with fast-starting frameworks**

**Explanation:**
Setting `autoscaling.knative.dev/min-scale` to 1 or higher prevents cold starts. Combining this with lightweight base images (distroless, alpine), fast-starting frameworks like GraalVM Native Image, and `initialScale` settings minimizes cold start latency.

</details>

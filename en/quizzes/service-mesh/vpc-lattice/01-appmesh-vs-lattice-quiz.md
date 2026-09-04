# App Mesh vs VPC Lattice Architecture Quiz

This quiz tests your understanding of the structural differences between the sidecar and managed data plane models, resource mapping, and feature gaps.

## Multiple Choice Questions

1. What is the fundamental reason VPC Lattice does not provide circuit breaking and outlier detection?
   - A) AWS simply has not implemented them yet and will add them soon
   - B) Lattice's proxy sits in front of the service and holds no per-caller state
   - C) Those features do not work over HTTP/2
   - D) They are unnecessary because IAM policies can replace them

<details>

<summary>Show Answer</summary>

**Answer: B) Lattice's proxy sits in front of the service and holds no per-caller state**

**Explanation:**
Circuit breaking requires counting concurrent connections and pending requests on the caller side, and outlier detection requires remembering per-caller upstream failure history. In the sidecar model the proxy lives inside the calling Pod and naturally has that state; Lattice's proxy sits at the infrastructure layer in front of the service and does not maintain "what failures has this particular caller recently seen" per caller. This is not a missing feature but the necessary consequence of a design choice, and the alternative is application libraries such as Resilience4j.
</details>

2. Why is App Mesh's VirtualNode said not to map one-to-one onto a VPC Lattice Target Group?
   - A) You can create many VirtualNodes but only one Target Group
   - B) The identity, backend, connection pool, and outlier detection attributes VirtualNode carried either scatter to several places or disappear
   - C) Target Groups do not support Lambda
   - D) VirtualNode depends on Cloud Map, making conversion impossible

<details>

<summary>Show Answer</summary>

**Answer: B) The identity, backend, connection pool, and outlier detection attributes VirtualNode carried either scatter to several places or disappear**

**Explanation:**
A VirtualNode packed "who this workload is (identity), where it goes (backends), and where it receives (listeners, health checks, connection pools, outlier detection)" into a single resource. In Lattice only the target set and health checks become a Target Group; "where it goes" becomes a matter of auth policies and IAM permissions; "who it is" becomes an IAM Role; and connection pools and outlier detection have no corresponding resource at all. The mapping table maps resource names, not capabilities.
</details>

3. Which feature gap is most often underestimated in practice, and why?
   - A) Circuit breaking — it is the hardest to implement
   - B) Observability (distributed trace spans) — what came for free without touching application code in AS-IS becomes an instrumentation project in TO-BE
   - C) Traffic mirroring — there is no alternative at all
   - D) Fault injection — it is essential for production incident response

<details>

<summary>Show Answer</summary>

**Answer: B) Observability (distributed trace spans) — what came for free without touching application code in AS-IS becomes an instrumentation project in TO-BE**

**Explanation:**
Circuit breaking and retries have a clear alternative ("add a library") with an estimable cost. But the spans Envoy produced automatically required no application code changes; getting the same tracing requires OpenTelemetry instrumentation in every service, which becomes an application-team work item. Moreover, the Lattice hop itself has no span, so it remains a blank gap in the trace graph where network latency and Lattice processing latency are mixed and cannot be separated.
</details>

4. What happens if the AWS Gateway API Controller stops?
   - A) All traffic is blocked immediately
   - B) Traffic keeps flowing, but newly started Pods are not registered as Targets and dead Pods are not deregistered
   - C) Lattice Services are automatically deleted
   - D) IAM authentication is disabled

<details>

<summary>Show Answer</summary>

**Answer: B) Traffic keeps flowing, but newly started Pods are not registered as Targets and dead Pods are not deregistered**

**Explanation:**
The controller's core job is keeping Kubernetes' declared state and Lattice's actual target list in sync — it watches endpoint changes on the Services referenced by `backendRefs` and registers/deregisters Targets. If it stops, Lattice keeps forwarding traffic using the last known target list, but that list goes stale. This is why the availability and IAM permissions of the controller Deployment are directly tied to data path reliability.
</details>

5. In an environment that also runs ingress-nginx, which statement about the migration scope is correct?
   - A) ingress-nginx must also be replaced by Lattice
   - B) The AWS Gateway API Controller currently focuses only on East-West traffic through Lattice, so the North-South traffic ingress-nginx handles is out of scope and the two paths coexisting is the normal outcome
   - C) ingress-nginx and Lattice cannot be used at the same time
   - D) The Gateway API Controller handles North-South traffic too, so ingress-nginx should be removed immediately

<details>

<summary>Show Answer</summary>

**Answer: B) The AWS Gateway API Controller currently focuses only on East-West traffic through Lattice, so the North-South traffic ingress-nginx handles is out of scope and the two paths coexisting is the normal outcome**

**Explanation:**
The Kubernetes Gateway API was designed to cover both North-South (Ingress) and East-West (Mesh) traffic, but the AWS Gateway API Controller currently focuses only on East-West. ALB/NLB-style North-South features belong to the AWS Load Balancer Controller. So the ingress path ingress-nginx serves is not in scope for this migration; only East-West traffic moves to Lattice, and a configuration where both paths coexist is the expected result.
</details>

6. Why use a Pod readiness gate in a Lattice environment?
   - A) To cap a Pod's CPU usage
   - B) So a Pod is not marked Ready until its Lattice Target Group health is Healthy, preventing a rolling update from terminating old Pods before new ones are healthy
   - C) To block traffic until IAM credentials are ready
   - D) To wait for Envoy sidecar injection

<details>

<summary>Show Answer</summary>

**Answer: B) So a Pod is not marked Ready until its Lattice Target Group health is Healthy, preventing a rolling update from terminating old Pods before new ones are healthy**

**Explanation:**
Kubernetes may consider a Pod Ready while the Lattice Target Group does not yet see it as Healthy. If a rolling update terminates old Pods in that state, there is a window with no healthy Target. A Pod readiness gate ties Lattice's view of health to the Pod's Ready condition, preventing this — an important mechanism for zero-downtime during migration.
</details>

# ArgoCD Traffic Management Quiz

This quiz tests your understanding of progressive delivery and traffic management with ArgoCD and Argo Rollouts.

1. What is Argo Rollouts?
   - A) A logging solution for ArgoCD
   - B) A Kubernetes controller for progressive delivery strategies
   - C) A Git branch management tool
   - D) A traffic monitoring dashboard

<details>
<summary>Show Answer</summary>

**Answer: B) A Kubernetes controller for progressive delivery strategies**

**Explanation:**
Argo Rollouts is a Kubernetes controller that provides advanced deployment capabilities like canary deployments, blue-green deployments, and progressive delivery with automated analysis.

</details>

2. Which strategy validates a new version through explicit traffic-weight steps and analysis gates?
   - A) Recreate
   - B) Rolling Update
   - C) Canary
   - D) Blue-Green

<details>
<summary>Show Answer</summary>

**Answer: C) Canary**

**Explanation:**
Canary deployments gradually shift traffic from the old version to the new version in increments (e.g., 10%, 25%, 50%, 100%), allowing for testing and validation at each step.

</details>

3. In a Blue-Green deployment with Argo Rollouts, what happens during promotion?
   - A) The blue environment is deleted
   - B) The active Service selector is changed to the new ReplicaSet
   - C) Both versions run simultaneously forever
   - D) A new environment is created

<details>
<summary>Show Answer</summary>

**Answer: B) The active Service selector is changed to the new ReplicaSet**

**Explanation:**
In Blue-Green deployments, promotion switches traffic from the current stable version to the preview version by updating the active service selector. Old ReplicaSet scale-down follows analysis and delay settings; data-plane propagation is not instantaneous.

</details>

4. What is an AnalysisTemplate in Argo Rollouts?
   - A) A template for creating new applications
   - B) A definition of metrics and success criteria for automated canary analysis
   - C) A logging configuration
   - D) A resource quota template

<details>
<summary>Show Answer</summary>

**Answer: B) A definition of metrics and success criteria for automated canary analysis**

**Explanation:**
AnalysisTemplates define metrics to query (from Prometheus, Datadog, etc.) and success/failure criteria. During a rollout, AnalysisRuns execute these templates to automatically determine if a deployment should proceed.

</details>

5. Which providers have native traffic-management integrations in Argo Rollouts?
   - A) Traefik only
   - B) NGINX Ingress only
   - C) Multiple including NGINX, ALB, Istio, and Traefik
   - D) None, manual configuration is required

<details>
<summary>Show Answer</summary>

**Answer: C) Multiple including NGINX, ALB, Istio, and Traefik**

**Explanation:**
Argo Rollouts has native traffic management integrations with multiple ingress controllers and service meshes including AWS ALB, Istio, Traefik and APISIX. Retained ingress-nginx/SMI API support does not mean those projects remain maintained; there is no separate native Linkerd field.

</details>

6. With a traffic router and default maxTrafficWeight=100, what does setWeight configure?
   - A) Sets the CPU weight for pods
   - B) Sets the percentage of traffic to route to the canary version
   - C) Sets the importance of the deployment
   - D) Sets the rollback threshold

<details>
<summary>Show Answer</summary>

**Answer: B) Sets the percentage of traffic to route to the canary version**

**Explanation:**
The `setWeight` step in a canary strategy configures what percentage of traffic should be routed to the canary (new) version. For example, setWeight:20 requests relative weight20/100. Observed percentages vary with samples, connections and cookies. Without a router, it approximates the ratio using Pod counts.

</details>

7. What happens when an analysis linked to the Rollout reaches AnalysisRun phase Failed?
   - A) The deployment continues regardless
   - B) An alert is sent but nothing else happens
   - C) The rollout is aborted and traffic returns to stable
   - D) The cluster is shut down

<details>
<summary>Show Answer</summary>

**Answer: C) The rollout is aborted and traffic returns to stable**

**Explanation:**
When an AnalysisRun fails (metrics exceed failure thresholds), Argo Rollouts aborts the rollout and returns traffic to stable. It does not revert Git or database changes. failureLimit distinguishes failed measurements from a failed AnalysisRun; Inconclusive pauses for investigation.

</details>

8. How can you pause a Rollout at a specific step for manual verification?
   - A) Using the `pause` step with no duration
   - B) Using the `stop` step
   - C) Using the `wait` step with duration: forever
   - D) It's not possible

<details>
<summary>Show Answer</summary>

**Answer: A) Using the `pause` step with no duration**

**Explanation:**
Adding a `pause` step without a duration creates an indefinite pause that requires manual promotion (via CLI or UI) to continue. This is useful for manual verification gates in the deployment process.

</details>

9. How do you split canary traffic through the Kong Ingress Controller?
   - A) Use the `trafficRouting.kong` field directly
   - B) Manipulate an HTTPRoute via the Gateway API plugin (`trafficRouting.plugins`)
   - C) Kong cannot be integrated with Argo Rollouts
   - D) Route around it using an Istio VirtualService

<details>
<summary>Show Answer</summary>

**Answer: B) Manipulate an HTTPRoute via the Gateway API plugin (`trafficRouting.plugins`)**

**Explanation:**
Kong has no native Argo Rollouts integration — there is no `trafficRouting.kong` field. This chapter uses argoproj-labs' Gateway API plugin, which manipulates a standard HTTPRoute resource. Other Gateway API-compliant controllers, such as Traefik and kgateway, use the same plugin.

</details>

10. What resource does the Argo Rollouts Gateway API plugin actually update at each canary weight step?
    - A) The Service's `selector` labels
    - B) The Ingress's `canary-weight` annotation
    - C) The HTTPRoute's `backendRefs[].weight`
    - D) The DestinationRule's subset labels

<details>
<summary>Show Answer</summary>

**Answer: C) The HTTPRoute's `backendRefs[].weight`**

**Explanation:**
The Gateway API plugin directly updates the standard Gateway API HTTPRoute resource's `backendRefs[].weight` values at each setWeight step. This mechanism can work with compatible controllers; verify the installed CRDs, supported Route features and actual data-plane convergence.

</details>

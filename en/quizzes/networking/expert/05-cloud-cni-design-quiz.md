# Cloud and CNI Design Quiz

[Workbook](../../../networking/expert/05-cloud-cni-design.md)

1. DNS answers but TCP connection fails. What is the appropriate next step?

   - A) Declare the backend healthy from DNS alone
   - B) Inspect actual target, port, routes, controls and listener
   - C) Open every security group
   - D) Conclude that no resource exists

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** DNS supplies name-resolution evidence. TCP and HTTP require separate path, policy and application evidence.

</details>

2. What is AWS Load Balancer Controller?

   - A) The data plane traversed by every HTTP request
   - B) Every Pod default gateway
   - C) A control-plane reconciler using AWS APIs to manage load-balancer resources
   - D) The DNS cache itself

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Requests traverse load balancers and their actual targets. Investigate controller state separately from data-plane communication.

</details>

3. EndpointSlice is ready but the LB target is unhealthy. How should you interpret it?

   - A) Correlate registration, port, health-check conditions and path because the states can differ
   - B) The observation is impossible because they mean the same thing
   - C) Changing DNS TTL always fixes it
   - D) Delete the EndpointSlice

<details>
<summary>Show Answer</summary>

**Answer: A**

**Explanation:** Readiness and LB health checks have different observers and conditions. Correlate each endpoint address with its conditions and actual target.

</details>

4. What else is needed when a NetworkPolicy object exists?

   - A) Nothing; existence proves enforcement
   - B) Move every Pod to hostNetwork
   - C) Administrator rights in every AWS account
   - D) Selected Pods, direction, supported API, engine activation and actual flow evidence

<details>
<summary>Show Answer</summary>

**Answer: D**

**Explanation:** An object list does not guarantee selection or enforcement. Other managed policies or CRDs may also apply.

</details>

5. Which TGW distinction is correct?

   - A) Both are the same firewall rule
   - B) Association selects the attachment lookup table; propagation identifies tables learning routes
   - C) Propagation always makes the attachment use that table
   - D) An attachment associates with every table

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** An attachment associates with one table and may propagate into several. Check both lookup and return paths separately.

</details>

6. A query returns AccessDenied and you cannot obtain endpoints. What is the result?

   - A) Traffic denial successfully validated
   - B) Automatically attach an administrator policy
   - C) Evidence unavailable; obtain approved minimal access or supplied evidence
   - D) No backend exists

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Permission failure is not resource or network state. Do not convert unknown into allow, deny or absence.

</details>

7. How should a Service ClusterIP be represented in a packet path?

   - A) Distinguish logical selection from actual proxy and target forwarding
   - B) Always as another physical hop behind the node
   - C) As mandatory for every IP-target request
   - D) Omit the return path

<details>
<summary>Show Answer</summary>

**Answer: A**

**Explanation:** Forwarding depends on target type, proxy implementation and policy. Turning object relationships into mandatory wire hops distorts diagnosis.

</details>

8. You reviewed only a hybrid routing design without an account. What completion label applies?

   - A) Live failover validated
   - B) Performance guaranteed
   - C) Every policy enforced
   - D) Design review complete; live observations unverified

<details>
<summary>Show Answer</summary>

**Answer: D**

**Explanation:** Design, supplied-evidence analysis and actual experiments are different evidence levels. Bound conclusions to what was performed.

</details>

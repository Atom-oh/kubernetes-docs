# Kernel Datapath Quiz

This quiz tests your understanding of the kernel layer of link-local interception, iptables collisions, and conntrack behavior.

## Multiple Choice Questions

1. Why is Lattice's use of the link-local range described as "not strictly following link-local semantics"?
   - A) The addresses are actually public IPs
   - B) `169.254.0.0/16` is nominally non-routable, yet Lattice traffic must reach an ingress endpoint inside the VPC, so the infrastructure steers it there
   - C) Only IPv4 is supported
   - D) DNS does not resolve that range

<details>

<summary>Show Answer</summary>

**Answer: B) `169.254.0.0/16` is nominally non-routable, yet Lattice traffic must reach an ingress endpoint inside the VPC, so the infrastructure steers it there**

**Explanation:**
Lattice does not use the link-local range in its original sense of "non-routable addresses" — it **reuses the range as a signal meaning "the infrastructure intercepts this."** The packet genuinely has to reach an ingress endpoint inside the VPC. For the same reason, IPv6 uses a routable ULA (`fd00:ec2:80::/64`) rather than link-local (`fe80::/10`) — link scope would be insufficient.
</details>

2. At exactly which kernel point does the collision between a sidecar mesh and Lattice traffic occur?
   - A) `POSTROUTING` in the node net namespace
   - B) The `OUTPUT` hook of the Pod net namespace — Lattice traffic is also outbound, so it matches the REDIRECT rule
   - C) The NIC driver's ring buffer
   - D) The node's routing table

<details>

<summary>Show Answer</summary>

**Answer: B) The `OUTPUT` hook of the Pod net namespace — Lattice traffic is also outbound, so it matches the REDIRECT rule**

**Explanation:**
The mesh init container installs iptables rules inside the Pod's net namespace that REDIRECT all outbound traffic to Envoy's port. Lattice-bound traffic is also outbound, so it matches, and Envoy cannot find `169.254.171.x` in its cluster configuration and fails. This collision happens inside the Pod because netfilter rules are per net namespace.
</details>

3. Why is this collision easier to diagnose than conntrack exhaustion?
   - A) It triggers a kernel panic
   - B) When Envoy does not know the destination it returns an error immediately and the request appears in its access log — it is not a silent drop
   - C) The Pod immediately enters CrashLoopBackOff
   - D) kube-proxy logs a warning

<details>

<summary>Show Answer</summary>

**Answer: B) When Envoy does not know the destination it returns an error immediately and the request appears in its access log — it is not a silent drop**

**Explanation:**
Envoy usually returns a connection refusal or 503 immediately for an unknown destination, so the symptom is unambiguous. Unlike conntrack exhaustion's silent drops, it appears in Envoy's access log as a request to an unknown cluster. So **check the Envoy sidecar logs first** when Lattice calls fail — requests bound for `169.254.171.x` there mean interception is the cause.
</details>

4. You registered the exception CIDR but it still fails "occasionally." What is the most likely cause?
   - A) Wrong rule ordering
   - B) A missing IPv6 range (`fd00:ec2:80::/64`) — on dual-stack, a client connecting over IPv6 is still intercepted
   - C) Pods were not restarted
   - D) A missing Security Group rule

<details>

<summary>Show Answer</summary>

**Answer: B) A missing IPv6 range (`fd00:ec2:80::/64`) — on dual-stack, a client connecting over IPv6 is still intercepted**

**Explanation:**
Excluding only IPv4 on a dual-stack cluster means a client that receives an AAAA record and connects over IPv6 is still intercepted. **The symptom being "occasional failure" is characteristic**, because it depends on DNS response ordering and the client's address selection. C can also be a real cause, but then that Pod fails consistently rather than "occasionally."
</details>

5. Why is a UID-based exception rule mandatory in the egress proxy approach?
   - A) Security policy requires the proxy to run as a non-privileged UID
   - B) The packet the proxy sends out signed is also destined for the Lattice range, so without a UID exception it is redirected to itself and loops
   - C) SigV4 signatures include UID information
   - D) conntrack distinguishes entries by UID

<details>

<summary>Show Answer</summary>

**Answer: B) The packet the proxy sends out signed is also destined for the Lattice range, so without a UID exception it is redirected to itself and loops**

**Explanation:**
The signed packet the proxy emits is also destined for `169.254.171.x`. Without the UID exception it matches the REDIRECT rule again and loops. So the proxy runs under a dedicated UID (101 in the reference implementation) and traffic from it is `RETURN`ed via netfilter's `owner` match (`-m owner --uid-owner`). **The proxy container's `runAsUser` and the iptables UID must match** — the most fragile link when customizing manifests.
</details>

6. Why does the egress proxy approach put more load on conntrack than the shared-library approach?
   - A) The proxy holds connections open longer
   - B) The REDIRECT in the Pod net namespace is DNAT and must be remembered to undo, plus the proxy→Lattice connection adds entries
   - C) The proxy also uses UDP
   - D) The proxy increases conntrack timeouts

<details>

<summary>Show Answer</summary>

**Answer: B) The REDIRECT in the Pod net namespace is DNAT and must be remembered to undo, plus the proxy→Lattice connection adds entries**

**Explanation:**
NAT creates conntrack entries. With the egress proxy, you get the REDIRECT (DNAT) entry in the Pod net namespace, the proxy's outbound connection to Lattice, and the node namespace SNAT entry. The shared-library approach has no REDIRECT and so avoids this extra load — which is why the node's conntrack headroom should be weighed when choosing a signing approach in high-connection environments.
</details>

7. If `tcpdump` captures no outbound packets at all, what should you suspect?
   - A) conntrack exhaustion
   - B) A problem inside the Pod — routing, interception, DNS. Traffic blocked by a Security Group never reaches the kernel so it is invisible to `tcpdump` too, making SG and routing candidates as well
   - C) qdisc drops
   - D) Lattice authentication failure

<details>

<summary>Show Answer</summary>

**Answer: B) A problem inside the Pod — routing, interception, DNS. Traffic blocked by a Security Group never reaches the kernel so it is invisible to `tcpdump` too, making SG and routing candidates as well**

**Explanation:**
A Security Group is not kernel netfilter but AWS's stateful firewall applied to the ENI at the VPC level, enforced outside the instance. So `iptables -L` on the node shows no SG rules, and traffic blocked by an SG never reaches the node kernel — invisible to `tcpdump`. Conversely, something dropped after reaching the kernel leaves a counter. So **"nothing is captured" is itself diagnostic information.**
</details>

8. What does the pattern "Lattice calls fail only on some nodes" tell you?
   - A) A Lattice service misconfiguration
   - B) Node state divergence — SG differences, mixed kernel versions, differing conntrack settings, clock synchronization, whether Pods were restarted
   - C) An auth policy misconfiguration
   - D) DNS propagation delay

<details>

<summary>Show Answer</summary>

**Answer: B) Node state divergence — SG differences, mixed kernel versions, differing conntrack settings, clock synchronization, whether Pods were restarted**

**Explanation:**
Total failure points to configuration or authentication; **node-scoped failure points to node state divergence.** Candidates are per-node-group SG differences, mixed 6.1/6.18 kernels from `kernel-default` AMIs, differing conntrack settings depending on bootstrap timing, clock synchronization causing the `x-amz-date` 5-minute skew, and annotation changes not applied to old Pods. The "some nodes" pattern itself narrows the search.
</details>

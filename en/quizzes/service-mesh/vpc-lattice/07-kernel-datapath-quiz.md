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

3. How should an intercepted request be diagnosed?
   - A) It triggers a kernel panic
   - B) Inspect the actual Envoy outbound policy, route and error; unknown destinations can be forwarded or rejected
   - C) The Pod immediately enters CrashLoopBackOff
   - D) kube-proxy logs a warning

<details>

<summary>Show Answer</summary>

**Answer: B) Inspect the actual Envoy outbound policy, route and error; unknown destinations can be forwarded or rejected**

**Explanation:**
Seeing a request in a proxy log proves traversal, not a unique failure cause. Verify the chosen bypass/signing behavior rather than assuming an immediate failure.
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
A signing proxy creates local and upstream connection segments, while pooling and namespace/NAT choices change the tracking cost. Inspect Pod/node tables and eBPF maps rather than assuming a fixed increase in the node table.
</details>

7. What does packet-capture visibility establish?
   - A) conntrack exhaustion
   - B) Interpret packet capture by sender/receiver, direction, interface and namespace, then correlate other evidence
   - C) qdisc drops
   - D) Lattice authentication failure

<details>

<summary>Show Answer</summary>

**Answer: B) Interpret packet capture by sender/receiver, direction, interface and namespace, then correlate other evidence**

**Explanation:**
An inbound packet rejected before delivery is absent at the receiver. An outbound packet may be visible at the sender before an external SG drops it. Missing responses alone do not prove SG failure.
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

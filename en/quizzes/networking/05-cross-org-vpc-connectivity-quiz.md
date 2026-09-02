# Cross-Org VPC Connectivity Quiz

This quiz tests your understanding of the five options for connecting VPCs across different AWS Organizations.

## Multiple Choice Questions

1. What is required to share a Transit Gateway with an account in a different Organization?
   - A) Merging the two Organizations into one
   - B) The `--allow-external-principals` option and invitation acceptance on the receiving side
   - C) A VPN connection between both Organizations' management accounts
   - D) Manual approval through an AWS Support ticket

<details>

<summary>Show Answer</summary>

**Answer: B) The `--allow-external-principals` option and invitation acceptance on the receiving side**

**Explanation:**
Sharing resources with an account outside your Organization via AWS RAM requires `--allow-external-principals` on the resource share, and the resource stays invisible until the receiving account runs `accept-resource-share-invitation`. Unlike OU-based automatic sharing within an Organization, cross-org sharing enforces explicit account-ID targeting plus explicit acceptance.
</details>

2. What happens when an account in another Organization creates a VPC attachment to a shared TGW?
   - A) It becomes available immediately
   - B) It stalls at pendingAcceptance until the TGW-owning account accepts it
   - C) The request is rejected and no attachment can be created
   - D) It activates automatically after 24 hours

<details>

<summary>Show Answer</summary>

**Answer: B) It stalls at pendingAcceptance until the TGW-owning account accepts it**

**Explanation:**
With auto-accept disabled (the default), a foreign account's attachment stays at `pendingAcceptance` until the TGW owner runs `accept-transit-gateway-vpc-attachment`. This is where the "TGW owner centrally controls the network" model is enforced at the API level. The account receiving the share can only create attachments — it cannot modify route tables.
</details>

3. Based on live measurements within the same AZ, how much latency does each Transit Gateway hop add (p50)?
   - A) About 0.02 ms — effectively zero
   - B) About 0.4–0.6 ms — sub-millisecond
   - C) About 3–5 ms
   - D) 10 ms or more

<details>

<summary>Show Answer</summary>

**Answer: B) About 0.4–0.6 ms — sub-millisecond**

**Explanation:**
Measured with c7g.large, a plain EC2 responder, and persistent TCP_RR (1,500 samples/path), one TGW hop cost +0.571 ms (TCP_RR) / +0.410 ms (ICMP). For reference, VPC Peering's cost was zero within measurement limits (equal to the same-VPC baseline), and an NLB hop (+0.79 ms) actually costs more than a TGW hop. Measurements using burstable instances or multi-stage proxy chains bury this sub-ms signal in noise, so measurement design matters.
</details>

4. What is the common pitfall in the Security Group configuration of a VPC Lattice target instance?
   - A) All outbound rules must be opened
   - B) The Lattice data plane arrives from link-local (169.254.171.0/24), so the managed prefix list must be allowed
   - C) NACLs must be used instead of SGs
   - D) Only port 443 needs to be allowed

<details>

<summary>Show Answer</summary>

**Answer: B) The Lattice data plane arrives from link-local (169.254.171.0/24), so the managed prefix list must be allowed**

**Explanation:**
VPC Lattice traffic (including health checks) arrives from the link-local range 169.254.171.0/24, not from the VPC CIDR. If the target SG only allows the VPC CIDR, every health check reports UNHEALTHY. The fix is adding the managed prefix list `com.amazonaws.<region>.vpc-lattice` to the SG's inbound rules.
</details>

5. Which options can connect VPCs in two Organizations whose IP CIDRs overlap?
   - A) VPC Peering and TGW Peering
   - B) TGW RAM Sharing
   - C) PrivateLink and VPC Lattice
   - D) None of the options can

<details>

<summary>Show Answer</summary>

**Answer: C) PrivateLink and VPC Lattice**

**Explanation:**
VPC Peering, TGW RAM sharing, and TGW Peering are all L3-routing based, so overlapping CIDRs rule them out. PrivateLink operates through an ENI inside the consumer VPC, and VPC Lattice uses link-local addressing, so both work regardless of CIDR overlap. In situations like M&A or MSP migration where IP redesign is impossible, these two are the only choices.
</details>

6. Which statement about routing in a TGW Peering setup is correct?
   - A) Routes propagate automatically via BGP
   - B) BGP is not supported, so static routes must be added manually to both TGW route tables
   - C) Only the VPC route tables need modification
   - D) No routing configuration is needed at all

<details>

<summary>Show Answer</summary>

**Answer: B) BGP is not supported, so static routes must be added manually to both TGW route tables**

**Explanation:**
TGW peering attachments do not support BGP, so there is no automatic route propagation. Static routes toward the peer's CIDRs must be added to both TGW route tables — in live testing, no traffic flowed until the static routes were in place. Also note operationally that static TGW routes take priority over propagated routes, and that the peering attachment ID differs between the requester and accepter sides.
</details>

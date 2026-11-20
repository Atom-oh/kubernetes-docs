# 07. WAN and Hybrid Connectivity Design Quiz

> **Last Updated**: November 19, 2026

Return to the [workbook](../../../networking/expert/07-wan-hybrid-connectivity.md).
Choose one answer per question and explain which rule in the workbook supports it.
These are design reasoning exercises, not claims that a connection was built.

1. A Transit Gateway receives `10.10.0.0/16` from both a Direct Connect gateway attachment and a BGP VPN attachment. On-premises prepends AS_PATH three times on the DX advertisement. Where does VPC-to-on-premises traffic go?
   - A) VPN, because its AS_PATH is shorter.
   - B) DX, because for the same CIDR the attachment-type order comes before any AS_PATH comparison, and DX gateway-propagated routes outrank VPN-propagated routes.
   - C) ECMP across both paths.

<details>
<summary>Show Answer</summary>

**Answer: B) DX, because for the same CIDR the attachment-type order comes before any AS_PATH comparison, and DX gateway-propagated routes outrank VPN-propagated routes.**

**Explanation:** The TGW picks the longest prefix first; for the same CIDR from different types it prefers static, system, prefix list, VPC-propagated, DX gateway-propagated, Connect, then VPN routes. AS_PATH and MED are compared only within one type, and ECMP is not supported between different attachment types.

</details>

2. While building a backup VPN, you add a **static route** `10.10.0.0/16` → VPN attachment to the TGW route table. The DX gateway propagates the same route. What happens in the normal state?
   - A) DX stays primary, because DX always beats VPN.
   - B) The TGW alternates between the two routes.
   - C) The static route outranks the propagated route, so the VPN silently becomes primary.

<details>
<summary>Show Answer</summary>

**Answer: C) The static route outranks the propagated route, so the VPN silently becomes primary.**

**Explanation:** Static routes are the first step of the TGW evaluation order, and a propagated route with the same destination does not even appear in the table. Build the backup VPN with BGP so that it ranks below the DX gateway-propagated route.

</details>

3. The DX gateway's allowed prefix is summarized as `10.0.0.0/8`, while the VPN advertises `10.20.0.0/16` from the TGW route table. The on-premises router sets LOCAL_PREF 200 on DX-learned routes and 100 on VPN routes. Where does traffic to `10.20.1.10` go?
   - A) VPN: the longer prefix `10.20.0.0/16` matches first, and LOCAL_PREF only compares paths for the same prefix.
   - B) DX, because its LOCAL_PREF is higher.
   - C) Both paths drop it.

<details>
<summary>Show Answer</summary>

**Answer: A) VPN: the longer prefix `10.20.0.0/16` matches first, and LOCAL_PREF only compares paths for the same prefix.**

**Explanation:** For a Transit Gateway association the allowed prefixes are advertised exactly as entered, so the router learns `10.0.0.0/8` (DX) and `10.20.0.0/16` (VPN) as different routes. Forwarding follows longest-prefix match and leaks onto the VPN. Match the allowed prefix length to the VPN side or summarize the VPN-learned routes the same way.

</details>

4. You want two DX VIFs to run active/passive for traffic returning from AWS to on-premises. What is the correct configuration?
   - A) A lower MED on the primary VIF only.
   - B) `7224:7300` on the primary VIF's prefixes and `7224:7100` on the backup VIF's prefixes, as standard communities.
   - C) Route-target extended communities that mark the priority.

<details>
<summary>Show Answer</summary>

**Answer: B) `7224:7300` on the primary VIF's prefixes and `7224:7100` on the backup VIF's prefixes, as standard communities.**

**Explanation:** For private and transit VIFs AWS compares longest prefix, local preference community, AS_PATH, then MED, and the communities are evaluated before AS_PATH. MED has the lowest priority and AWS does not recommend it. Extended communities are not evaluated for preference and may be removed.

</details>

5. Which statement about BFD on Direct Connect is correct?
   - A) It is enabled automatically on the AWS side, so it works without router configuration.
   - B) Direct Connect does not support BFD, so only the BGP hold time applies.
   - C) Asynchronous BFD is enabled automatically on the AWS side but takes effect only when configured on your router; the default minimum interval is 300 ms with a multiplier of 3.

<details>
<summary>Show Answer</summary>

**Answer: C) Asynchronous BFD is enabled automatically on the AWS side but takes effect only when configured on your router; the default minimum interval is 300 ms with a multiplier of 3.**

**Explanation:** Without BFD, BGP drops the session only after a 90-second hold time without keepalives. That is why the exercise's "BFD not configured" scenario misses the 5-second objective.

</details>

6. BFD at 300 ms × 3 detects a failure in about 0.9 seconds. Which sentence is justified in a design document?
   - A) Detection takes about 0.9 seconds; route withdrawal and propagation, FIB programming on both routers and the reverse-direction switch are assumptions until measured.
   - B) Failover takes 0.9 seconds.
   - C) Even with BFD, the path changes only after the 90-second BGP hold time.

<details>
<summary>Show Answer</summary>

**Answer: A) Detection takes about 0.9 seconds; route withdrawal and propagation, FIB programming on both routers and the reverse-direction switch are assumptions until measured.**

**Explanation:** In RFC 5880, detection time is the multiplier times the negotiated interval. Detection is only part of recovery, and AWS publishes no fixed values for the remaining steps. When BFD tears down the session, BGP does not wait for the hold time.

</details>

7. Which statement about a Direct Connect LAG is correct?
   - A) Bundling connections from two different DX locations into one LAG protects against a location failure.
   - B) It bundles same-bandwidth dedicated connections at one endpoint (up to 4 below 100 Gbps, up to 2 at 100 or 400 Gbps) and does not support MLAG, so it adds capacity but not location redundancy.
   - C) Hosted connections can join a LAG.

<details>
<summary>Show Answer</summary>

**Answer: B) It bundles same-bandwidth dedicated connections at one endpoint (up to 4 below 100 Gbps, up to 2 at 100 or 400 Gbps) and does not support MLAG, so it adds capacity but not location redundancy.**

**Explanation:** All LAG members must be dedicated connections terminating at the same Direct Connect endpoint. Location redundancy comes from spreading connections across locations, as in the Resiliency Toolkit's High and Maximum resiliency models. Setting the minimum-links attribute (default 0) prevents overloading the surviving members.

</details>

8. What is wrong with a report saying "one Site-to-Site VPN connection has two tunnels, so redundancy is done"?
   - A) Nothing; the two tunnels make everything up to the customer gateway redundant.
   - B) AWS sends on both tunnels with ECMP, so no asymmetric-routing setting is needed.
   - C) The two tunnels only make the AWS-side endpoint redundant across Availability Zones; a single shared customer gateway and circuit remain single points of failure.

<details>
<summary>Show Answer</summary>

**Answer: C) The two tunnels only make the AWS-side endpoint redundant across Availability Zones; a single shared customer gateway and circuit remain single points of failure.**

**Explanation:** Each tunnel has a unique public IP and terminates in a different Availability Zone. AWS-to-on-premises traffic prefers one tunnel, so the customer gateway must allow asymmetric routing. For customer-side redundancy, add another customer gateway and VPN connection.

</details>

9. A TCP connection running over DX with a transit VIF MTU of 8500 fails over to a VPN (AES-GCM, NAT-T disabled). Which design prevents large packets from disappearing?
   - A) Clamp the MSS on your router to the backup-path value (1406 for this combination), or keep the VIF at 1500 while VPN is the backup.
   - B) Leave it; the TGW supports PMTUD on every attachment.
   - C) Enable jumbo frames on the VPN.

<details>
<summary>Show Answer</summary>

**Answer: A) Clamp the MSS on your router to the backup-path value (1406 for this combination), or keep the VIF at 1500 while VPN is the backup.**

**Explanation:** Site-to-Site VPN supports an MTU of up to 1446 and an MSS of 1406, with no jumbo frames and no PMTUD. TGW PMTUD applies only to traffic entering on VPC and Connect attachments. In a failover design, the backup path's MTU is the one that matters.

</details>

10. An on-premises router advertises 150 IPv4 prefixes over one transit VIF BGP session with the default prefix allocation. What happens?
   - A) AWS accepts the first 100 and ignores the rest.
   - B) The allocation (default 100) is exceeded, so the BGP session goes idle and is reported DOWN.
   - C) AWS summarizes them automatically.

<details>
<summary>Show Answer</summary>

**Answer: B) The allocation (default 100) is exceeded, so the BGP session goes idle and is reported DOWN.**

**Explanation:** A private or transit VIF BGP session accepts a default of 100 routes each for IPv4 and IPv6, raisable to 1,000 each with prefix controls. Exceeding the count is a session outage, which is why the exercise starts by checking the advertisement table against quotas.

</details>

11. How should the Direct Connect gateway appear in a topology drawing?
   - A) As a hop that forwards packets between the VIF and the Transit Gateway.
   - B) As part of the Transit Gateway route table.
   - C) As a distributed BGP route reflector outside the data path, connected by session lines only.

<details>
<summary>Show Answer</summary>

**Answer: C) As a distributed BGP route reflector outside the data path, connected by session lines only.**

**Explanation:** AWS describes the DX gateway as a distributed set of route reflectors operating outside the data traffic path, so it is not a single point of failure. In the animation, too, the packet dwells only at the DX location and the Transit Gateway.

</details>

12. How do you restate "SD-WAN detects failures quickly" precisely in control-plane and data-plane terms?
   - A) BFD detects connection failures on the IPsec data connections between routers; controller redundancy is a separate design item.
   - B) The Controllers' OMP sessions measure packet loss on the data tunnels directly.
   - C) MEF 70.2 sets the BFD timer values.

<details>
<summary>Show Answer</summary>

**Answer: A) BFD detects connection failures on the IPsec data connections between routers; controller redundancy is a separate design item.**

**Explanation:** In Cisco Catalyst SD-WAN the Controllers orchestrate the control plane and the Validator handles device authentication and control connections. Data flows over IPsec connections between routers, and BFD runs automatically on them. MEF 70.2 defines service attributes such as tunnels and policy.

</details>

Completion: explain every answer with a rule from the workbook, and attach the exercise's scenario table or label the work **design review**.

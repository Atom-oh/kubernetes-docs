# Quiz 2. Addresses, subnets, and interfaces

> **Supported Versions**: Ubuntu Server 24.04 LTS (primary), Rocky Linux 9 (alternate)
> **Last Updated**: September 15, 2026

[Return to lesson](../../../networking/beginner/02-addressing-interfaces.md) | [Course preparation](../../../networking/beginner/README.md)

Use the isolated two-VM lab contract. Choose an answer before opening its explanation. The examples are for interpretation, not host reconfiguration.

1. The client sends an HTTP request directly to the server at `192.0.2.20:8080`. Which description is correct?

   - A) `8080` is the server's MAC address.
   - B) Ethernet uses MAC addresses on the local link, IP identifies routed endpoints, and TCP port `8080` identifies a transport endpoint where a service must listen.
   - C) Assigning the server IP automatically starts HTTP.
   - D) TCP and UDP port `8080` always reach the same program.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** A local Ethernet frame carries an IP packet, which carries transport information and application data. Ports are protocol-specific numbers, not cables. Address configuration alone creates no listener. ICMP echo success also does not prove that TCP `8080` is open.

</details>

2. What are the network, broadcast, and ordinary host range for `192.0.2.10/24`?

   - A) Network `.10`, broadcast `.24`, hosts `.1`–`.9`.
   - B) Network `192.0.2.0`, broadcast `192.0.2.255`, hosts `.1`–`.254`.
   - C) Network `192.0.0.0`, broadcast `192.0.255.255`, hosts `.0`–`.255`.
   - D) All 256 addresses are ordinary host addresses in this lab.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** `/24` reserves 24 network bits, leaving 8 host bits and 256 addresses. For this ordinary subnet, all-zero and all-one host bits identify the network and broadcast addresses, leaving 254 host addresses. `/31` and `/32` have special uses and should not be forced into this calculation.

</details>

3. Which destination shares the subnet of `192.0.2.70/26`, and why?

   - A) `.130`, because the first three octets match.
   - B) `.100`, because the `.64/26` block spans `.64`–`.127`, with hosts `.65`–`.126`.
   - C) `.20`, because any documentation address is local.
   - D) `.127`, because a subnet's broadcast address is the recommended server address.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** `/26` leaves 6 host bits, so blocks contain 64 addresses and start at `.0`, `.64`, `.128`, and `.192`. `.70` and `.100` belong to the second block. `.130` belongs to the third. Compare the actual prefix rather than assuming every network is `/24`.

</details>

4. The client has a management default route and a connected `192.0.2.0/24` route on the lab NIC. Where should a packet for `.20` go?

   - A) Through the management default because default always has priority.
   - B) Directly through the lab NIC because `/24` is a longer matching prefix than `/0`.
   - C) Through `.1`, which is automatically a gateway.
   - D) Nowhere until DNS is configured on the lab NIC.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** The connected route is more specific. No lab gateway or DNS is needed for same-subnet literal-IP traffic. Preserve the existing management default route. A gateway must actually exist and be reachable; an address ending in `.1` is not inherently a router.

</details>

5. Which assignment of responsibilities is correct?

   - A) DHCP forwards every packet, DNS assigns the client's MAC, and ARP resolves names.
   - B) DHCP can lease address/configuration, DNS answers name-record queries, and ARP resolves an IPv4 next-hop neighbor to a MAC on the link.
   - C) DNS success proves every service is reachable.
   - D) ARP discovers the MAC of any server across the Internet.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** For a remote IPv4 destination reached through a router, ARP normally resolves the router's local-link MAC, not the remote server's. DHCP is configuration exchange. DNS is name resolution. These answer different questions and can succeed or fail independently.

</details>

6. Before adding an address, which evidence identifies the lab NIC reliably?

   - A) It is always `eth1`.
   - B) It is the second non-loopback line in `ip a`.
   - C) Its full MAC matches the hypervisor's recorded NIC attached to the internal-only network.
   - D) It already has the default route.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Guest names and ordering vary. Record management and lab MACs separately for each VM and match them against `ip -br link`. A default route often identifies the management path, which must remain untouched. The lab NIC must also meet the no-existing-IPv4 precondition before this exercise adds an address.

</details>

7. What does `ip a` do, and what can `UP` without `LOWER_UP` mean?

   - A) `ip a` adds an address, and `UP` proves Internet access.
   - B) `ip a` lists addresses; an administratively enabled link may still lack lower-layer carrier.
   - C) Both expressions mean that DNS works.
   - D) `UNKNOWN` on loopback always means the guest is broken.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** `a` abbreviates the address object; adding requires the `add` operation. Administrative enablement, carrier, address assignment, routing, and service reachability are separate observations. For missing carrier, inspect the virtual cable and network attachment before modifying IP settings.

</details>

8. `ip -4 route get 192.0.2.20` selects the lab NIC with source `.10`, but ping receives no replies. What has the route lookup proved?

   - A) The peer received a packet.
   - B) The kernel would select that route/source; no probe packet was sent by this lookup.
   - C) The firewall permits ICMP and TCP.
   - D) ARP has necessarily resolved the peer.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Route selection is local evidence. After a bounded ping, inspect neighbors to distinguish unresolved local-link delivery from a path where the MAC resolves but ICMP may be filtered. Do not treat a routing decision as end-to-end success or disable a firewall to hide the symptom.

</details>

9. After traffic, a neighbor entry has the expected peer MAC and state `STALE`. What does it mean?

   - A) The interface is permanently unusable.
   - B) A mapping is cached and will need reconfirmation when used; this is not immediate failure.
   - C) Someone necessarily spoofed the peer.
   - D) All neighbor entries must be flushed.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Neighbor state changes with reachability confirmation. `REACHABLE` is recently confirmed, `INCOMPLETE` is resolving, and `FAILED` is failed resolution. An empty table before traffic can be normal. Compare MACs with your records and use traffic observations rather than demanding that every cached entry always read `REACHABLE`.

</details>

10. A manually added address displays `valid_lft forever`. Will it survive reboot, and what should cleanup remove?

   - A) Yes; delete the guest's entire address table.
   - B) No persistence is implied; delete the exact successfully added IP/prefix from its identified lab NIC, and restore down only if that NIC was originally down.
   - C) Yes; only reinstalling Linux can remove it.
   - D) Delete the management default route first.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** `forever` means no runtime expiry timer, not saved configuration. With the lesson's empty-IPv4 precondition, removing its only lab IPv4 address also removes its automatically created connected route. If a reboot or manager already removed the address, confirm absence and skip deletion. Recover recorded variables and original state rather than guessing.

</details>

11. You see an IPv6 address beginning `fe80:` on the lab NIC. Which response is appropriate?

   - A) Disable IPv6 globally to make IPv4 work.
   - B) Treat it as likely link-local, leave existing IPv6 unchanged, and continue the IPv4 exercise.
   - C) Assume Internet access because every IPv6 address is global.
   - D) Configure an IPv4 ARP entry for it.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** IPv6 has 128-bit addresses; link-local scope is limited to its link and may require an interface zone when used as a destination. IPv6 uses Neighbor Discovery rather than ARP and has no IPv4-style broadcast. A link-local address alone does not establish Internet reachability.

</details>

12. Which completion statement is honest and complete?

   - A) “The examples were live-tested because I read the commands.”
   - B) “The lab address exists, so every TCP service works.”
   - C) “I verified the two lab NICs by MAC, addresses/routes and limited reachability evidence, preserved management, then removed only my address and restored recorded link state.”
   - D) “A host-only network is always isolated and never has DHCP.”

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** The contract includes configuration, evidence, and recovery. Internal-only lab networking has no DHCP/uplink; host-only defaults must not be assumed equivalent. The examples in the lesson are illustrative, not live-test transcripts. The next lesson establishes persistent configuration without depending on leftover variables.

</details>

Revisit any uncertain result in the [lesson](../../../networking/beginner/02-addressing-interfaces.md), then continue to [persistent configuration](../../../networking/beginner/03-persistent-configuration.md).

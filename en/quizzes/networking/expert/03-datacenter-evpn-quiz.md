# 03. Datacenter EVPN — Quiz

> **Last Updated**: September 15, 2026

Return to the [workbook](../../../networking/expert/03-datacenter-evpn.md).
Choose one answer and name the positive control that would distinguish a valid negative test from a broken lab.

1. A fabric has an unexpected blocked access path. Which prerequisite should be investigated before assuming EVPN is at fault?
   - A) VLAN membership, actual STP state and LAG member state where those features are instantiated.
   - B) Only BGP hold timers.
   - C) Whether a single flow uses every LACP member at once.

<details>
<summary>Show Answer</summary>

**Answer: A**

**Explanation:** Tenant attachment and local forwarding are prerequisites for an overlay. LACP hashing does not promise all members carry one flow. The selected small labs instantiate neither LACP nor a redundant STP topology, so they cannot substantiate a claim that those features were tested.

</details>

2. In a VXLAN packet carrying h1 traffic to h2, what normally identifies the remote encapsulation endpoint?
   - A) h2's tenant IP must be the outer destination.
   - B) The remote VTEP's IP is the outer destination, while the VNI identifies the virtual segment.
   - C) The RD is placed in the outer IP destination field.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Distinguish outer transport from inner tenant traffic. Capture the VTEP pair, VNI and inner addresses, then compare them with the mapping table. A management ping never substitutes for this tenant-path evidence.

</details>

3. Two advertisements have different RDs but carry an RT imported by the same VRF. Which statement is correct?
   - A) Different RDs force them into different VPNs.
   - B) A matching RD is required for the VRF to import them.
   - C) RDs distinguish route identities; matching import/export RT policy can place both in the same VPN.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Route identity and membership are different functions. RT policy controls import, while the RD disambiguates otherwise overlapping routes. Still verify the imported route, FIB and traffic; an RT is not a packet firewall or a forwarding guarantee.

</details>

4. Which route-type mapping is correct?
   - A) Type 2 carries MAC/optional IP, Type 3 supplies IMET participation information, Type 5 carries an IP prefix.
   - B) Type 2 carries only an underlay OSPF route; Type 3 guarantees routed tenant service.
   - C) Type 5 must appear in every bridging-only lab.

<details>
<summary>Show Answer</summary>

**Answer: A**

**Explanation:** Relate each route type to the service model. Generate host traffic before expecting host learning, inspect replication/FDB state for L2, and trace Type-5 import for Stage B. A type not required by the chosen model can be justified N/A, not falsely passed.

</details>

5. What distinguishes symmetric IRB from the mere presence of EVPN BGP?
   - A) Any EVPN session automatically enables an anycast gateway.
   - B) Symmetric IRB requires tenant routing at both ends with an L3VNI between them.
   - C) Symmetric IRB means the two VTEPs use identical RDs.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** IRB concerns forwarding at bridge/routing boundaries, not only the BGP address family. Verify the relevant SVI/VRF/VNI bindings. Stage B is L3-only with routed host links, so it does not by itself test access-VLAN anycast IRB or mobility.

</details>

6. The upstream Stage A topology selects EOS/Cumulus, but you want the workbook's FRR path. What is required?
   - A) Use any old FRR container; every provider has the same dataplane.
   - B) Change the image label without preparing Linux bridge/VTEP interfaces.
   - C) Explicitly override s1 and s2 to FRR, use the supported clab/kernel combination, record versions/digests and verify generated dataplane objects.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** The provider, image, netlab templates and VM kernel jointly implement the lab. FRR learns Linux interface state rather than creating all interfaces itself. A restricted environment without required kernel support is blocked, even if the BGP daemon starts.

</details>

7. h1 cannot reach h3 in Stage A, but neither same-VLAN pair works. How should the result be classified?
   - A) Not a successful isolation test; investigate the failed positive controls first.
   - B) PASS because any failed cross-VLAN probe proves isolation.
   - C) PASS because the EVPN session is established.

<details>
<summary>Show Answer</summary>

**Answer: A**

**Explanation:** A dead host or failed fabric can produce the same negative probe. Require both intended pairs, correct attachment and an explained blocked path. Missing routes or probes do not independently prove the requested service/isolation contract.

</details>

8. Why does the RT experiment add an unused manual import RT before removing the original one?
   - A) To change the RD while hiding the change.
   - B) To prevent an empty manual list from reverting to an automatic RT; the effective list must still be checked.
   - C) To shut down every EVPN peer.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Automatic RT behavior can invalidate a naive deletion experiment. Check that the original membership is no longer effective and the temporary RT matches no exported route. Restore by adding the original RT and then removing only the temporary entry on s1's red import list.

</details>

9. After lowering s1's underlay MTU, small probes pass and larger probes still pass with outer fragmentation visible. What should the report say?
   - A) No MTU effect occurred because there was no loss.
   - B) A guaranteed black hole occurred because inner DF was set.
   - C) Fragmentation was the observed effect; inner DF did not establish outer DF behavior.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Record encapsulation size, outer fragmentation, errors and adjacency changes. The model and implementation determine the effect; a workbook must not invent a fixed loss outcome. Restore the known 1600-byte interface prestate and repeat both sizes and the VRF controls.

</details>

10. Which evidence supports successful RT fault injection and recovery?
   - A) During the fault the global route remains, red import/probe fails, blue and h2's local gateway work; after restoration the original RT set, route and red probe return.
   - B) An empty global table alone.
   - C) Repeated initialization and global pruning eventually leave no errors.

<details>
<summary>Show Answer</summary>

**Answer: A**

**Explanation:** The working controls distinguish an import-policy fault from general unavailability. Exact restoration is required on the named object. FRR VLAN/VRF initialization is not assumed idempotent, and missing telemetry or broad cleanup is not evidence of recovery.

</details>

Completion: submit the L2, L3, RT and MTU evidence matrix with revisions and restoration results, or explicitly mark the practical work **not executed**.

# 03. Datacenter EVPN: Isolation and Dataplane Evidence

> **Last Updated**: September 15, 2026
> **Lab boundary**: Separately prepared, owned, disposable Linux fabric VMs; no production fabric or cloud resources.
> **Verification status**: Official documentation, upstream topology and FRR CLI/template sources checked; these labs were **not run** while authoring.

An established EVPN BGP session is a starting observation, not a working-fabric certificate.
This workbook asks you to trace a frame or packet through its VLAN, VNI, VRF and underlay, then demonstrate isolation and restoration.
Complete [the eight beginner lessons](../beginner/README.md) and [routing policy](02-routing-policy-convergence.md) first.
Use [Linux network-stack fundamentals](../../kernel/02-network-stack.md) to interpret bridge, neighbor and kernel route evidence.

## 1. Read the architecture in layers

| Primary reading | Deliverable before touching the lab |
|---|---|
| [netlab EVPN module](https://netlab.tools/module/evpn/) | A feature/provider checklist for the selected devices |
| [netlab platform support](https://netlab.tools/platforms/) and [FRR caveats](https://netlab.tools/caveats/#frrouting) | Explain why FRR in a container still depends on the VM kernel |
| [FRR EVPN](https://docs.frrouting.org/en/latest/evpn.html) | Map a Linux bridge, VXLAN interface, SVI and VRF to EVPN concepts |
| [RFC 7348](https://www.rfc-editor.org/rfc/rfc7348.html), [RFC 7432](https://www.rfc-editor.org/rfc/rfc7432.html) | Draw encapsulation and distinguish route identity from import policy |
| [RFC 9135](https://www.rfc-editor.org/rfc/rfc9135.html), [RFC 9136](https://www.rfc-editor.org/rfc/rfc9136.html) | Explain IRB and why prefix advertisements differ from host advertisements |

**VLAN** defines local Layer-2 membership; an access-port VLAN and an allowed trunk VLAN are not interchangeable settings.
**LACP** negotiates a link aggregation group: member state and hashing determine usable capacity; one flow need not use every member.
**STP** protects a bridged topology from loops; an unexpected blocking port can explain missing traffic before EVPN enters the picture.
Read [netlab VLAN](https://netlab.tools/module/vlan/), [LAG](https://netlab.tools/module/lag/) and [STP](https://netlab.tools/module/stp/) alongside this checklist.
The selected small labs do **not** build LACP or a redundant STP topology. Mark them “not instantiated,” not “tested successfully.”
Before adapting the exercises to another fabric, require correct access/trunk membership, intended LAG members and the expected STP forwarding topology.

The **underlay** supplies IP reachability between VTEPs. Its routing, return path and usable MTU must work independently of tenant addressing.
The **overlay** carries tenant traffic between those VTEPs; VXLAN adds an outer Ethernet/IP/UDP/VXLAN encapsulation.
The outer destination is a remote VTEP, not the tenant host; the VNI identifies a virtual segment in the VXLAN header.
VLAN IDs are locally significant; their mapping to VNIs must be verified rather than assumed numerically equal.

## 2. Separate identifiers, routes and forwarding

| Concept | Meaning | Evidence to seek |
|---|---|---|
| VTEP | Encapsulation/decapsulation endpoint | Local address, remote reachability, VXLAN interface |
| L2VNI / MAC-VRF | Bridged tenant segment | VLAN/bridge mapping, learned remote MAC and VTEP |
| L3VNI / IP-VRF | Routed tenant context | VRF table, transit VNI and remote prefix |
| RD | Distinguishes otherwise overlapping VPN route identities | Originating route's RD |
| RT | Extended-community membership used for import/export policy | Advertised export RT and effective receiver import RT set |
| SVI / IRB | Routing at a bridge-domain boundary | Gateway address/MAC, SVI-to-VRF binding and routed probe |

Different RDs can belong to the same VPN; matching RDs do not grant membership.
An RT is not a packet firewall. An unintended imported route can create reachability, but a route alone still does not prove forwarding.
In asymmetric IRB, ingress routes and the remote side bridges into the destination segment; the participating gateways need the relevant destination L2 state.
In symmetric IRB, both ends perform tenant routing using an L3VNI between them.
Do not infer symmetric IRB just because BGP has an EVPN address family.

| EVPN route | Role in this workbook | What its presence cannot prove |
|---|---|---|
| Type 2: MAC/IP advertisement | Advertises a MAC, optionally with its associated IP; supports remote host knowledge | Every advertised MAC is installed in the correct bridge |
| Type 3: IMET | Announces participation used to construct BUM delivery, such as ingress replication | Unicast host forwarding or tenant routing succeeds |
| Type 5: IP prefix | Carries tenant IP reachability independent of a particular host MAC advertisement | The receiver imports the prefix or can reach its VTEP |

BUM means broadcast, unknown unicast and multicast; a VTEP's replication state matters alongside its Type-3 route.
Keep global EVPN routes, imported per-VNI/VRF state and actual forwarding evidence separate in your report.

## 3. Select reproducible upstream labs

Use the examples repository linked from [netlab's home page](https://netlab.tools/), revision **`7c4fa0dac160d3cc2eac41e11f20b74d083bb896`**:

| Stage | Exact upstream path | Intended baseline |
|---|---|---|
| A: L2 | [EVPN/vxlan-bridging](https://github.com/ipspace/netlab-examples/tree/7c4fa0dac160d3cc2eac41e11f20b74d083bb896/EVPN/vxlan-bridging) | h1↔h2 in red; h3↔h4 in blue; no inter-VLAN routing |
| B: L3 | [EVPN/l3vpn](https://github.com/ipspace/netlab-examples/tree/7c4fa0dac160d3cc2eac41e11f20b74d083bb896/EVPN/l3vpn) | Routed h1↔h2 in red VRF; h3↔h4 in blue VRF; no cross-VRF import |

Both use `clab`, two switches s1/s2, four Linux hosts and an OSPF underlay with AS65000 EVPN.
Stage A upstream explicitly selects EOS and Cumulus; Stage B defaults to EOS.
**Our declared selection overrides s1 and s2 to `frr` individually**, using the documented `-s nodes.s1.device=frr -s nodes.s2.device=frr` [startup options](https://netlab.tools/netlab/up/).
The [EVPN support matrix](https://netlab.tools/module/evpn/#platform-support) lists FRR for VLAN-based EVPN, symmetric IRB and iBGP/IGP.
That matrix does not guarantee every old image or provider combination works.

Prepare **one exclusive VM per stage**, or restore an owned empty VM checkpoint between stages after exporting evidence.
Do not start both copies with colliding node/lab identities on a shared host.
Stage B has routed host links and transit VNIs; it is an L3VPN exercise, **not** an access-VLAN anycast-gateway or host-mobility exercise.
Study the IRB distinction using the readings; do not report Type-2/3 or anycast tests as passed when the selected L3-only model does not require them.

## 4. Lab-specific prerequisites and recording

- Use an owned x86-64 Ubuntu 24.04 Linux VM with console access. Budget 4 vCPU, 8 GiB RAM and 20 GiB free disk **per active six-container stage** as a planning allowance; measure actual use.
- Complete [netlab Ubuntu setup](https://netlab.tools/install/ubuntu/) and [containerlab provider setup](https://netlab.tools/labs/clab/) before the workbook, including Docker, Ansible dependencies and node images.
- Use a netlab release that advertises the selected FRR EVPN/VXLAN/VRF capabilities. Record its exact release, the example revision and both node overrides.
- The inspected netlab [FRR device definition](https://github.com/ipspace/netlab/blob/4d85d13365caf3962a72ba59ec57a2e4450f365f/netsim/devices/frr.yml) selects `quay.io/frrouting/frr:10.6.1`; CLI examples here were checked against FRR 10.6.1. Record the actual installed release's image and digest rather than assuming it matches.
- FRR/clab needs VM-kernel support for bridge, VXLAN and, for Stage B, VRF. Upstream setup may load modules on **this owned VM**. A restricted Codespace that cannot load required modules is not a substitute.
- Prepare iproute2, iputils, tcpdump and GNU `timeout` on the VM. Use VM iputils inside a recorded node namespace for DF/size probes; an Alpine host image's BusyBox `ping` is not assumed to support those options.
- FRR and the selected Linux host images do not require commercial router licenses. Keeping EOS/Cumulus instead is a different platform selection with its own image access, licensing and CLI requirements.
- The VM owner supplies Docker/provider privileges; `vtysh` and namespace operations require appropriate lab privileges. Do not change management interfaces, workstation routes or cloud settings.

In the **Stage A VM shell**, with the destination absent:

```bash
test ! -e "$HOME/expert-fabric-examples"
git clone --no-checkout https://github.com/ipspace/netlab-examples.git "$HOME/expert-fabric-examples"
git -C "$HOME/expert-fabric-examples" checkout --detach 7c4fa0dac160d3cc2eac41e11f20b74d083bb896
cd "$HOME/expert-fabric-examples/EVPN/vxlan-bridging"
git rev-parse HEAD
git status --short
sha256sum topology.yml
python3 -c 'from importlib.metadata import version; print(version("networklab"))'
containerlab version
docker version
ansible --version
uname -r
```

Stop on a failed absence check. The clone is a new owned object, retained with the evidence until this VM is disposed of.
Repeat this clone/revision procedure on the separate Stage B VM, then use `EVPN/l3vpn` as its working directory.
The owner must complete the official startup procedure with provider `clab` and the two FRR node overrides before either stage's observations.
Record the empty-VM checkpoint, generated lab identity, exact launch options and a healthy pre-experiment checkpoint.
This setup owns the bridge/VTEP/VRF creation: [FRR itself does not create the Linux interfaces](https://docs.frrouting.org/en/latest/evpn.html#the-linux-vxlan-dataplane).
Do not paste standalone BGP settings into an empty container and call it a working overlay.

## 5. Verify identities and dataplane readiness

In the active stage's **VM shell**:

```bash
netlab status
netlab inspect nodes.s1.interfaces
netlab inspect nodes.s2.interfaces
netlab connect --dry-run s1
netlab connect s1 --show version
netlab connect s1 --show running-config
netlab connect s1 --show ip ospf neighbor
netlab connect s1 --show bgp l2vpn evpn summary
netlab connect s1 --show evpn vni
netlab connect s1 --show bgp l2vpn evpn vni
netlab connect s1 ip -d link show
netlab connect s1 bridge link show
netlab connect s1 bridge fdb show
netlab connect s1 ip route show
```

Repeat the read-only state checks on s2. Use the [inspect](https://netlab.tools/netlab/inspect/) and [connect](https://netlab.tools/netlab/connect/) references to interpret node/interface mappings.
`netlab connect s1` enters the **FRR container's Linux shell**; type `vtysh` to enter the FRR CLI.
`s1#` means FRR operational mode; `configure terminal` enters configuration mode, `end` leaves it, and `exit` from operational mode returns to Linux.
Use `ip`/`bridge` in Linux and `show` in FRR, or the VM-side `--show` wrapper as above.

Record each exact container's image with `docker inspect --format '{{.Config.Image}} {{.Image}}' CONTAINER`; inspect named lab objects individually.
Require real VXLAN interfaces with local VTEP addresses, bridge membership, operational VNIs and remote VTEP reachability.
On Stage B also require `show vrf vni`, Linux VRF devices/tables and host-link membership in red or blue.
The current [FRR caveats](https://netlab.tools/caveats/#frrouting) warn that VLAN/VRF initialization is not idempotent and configuration collection omits Linux interface state.
Do not repair a failed precondition by repeatedly replaying initialization; preserve the failure and return to the owned setup checkpoint.

Build this mapping from actual output; never fill it from memory:

| Host | Data IP/prefix | Access VLAN or routed link | VRF | L2VNI / L3VNI | Local / remote VTEP | Capture interface |
|---|---|---|---|---|---|---|
| h1 | Record | Stage A red / Stage B routed | Record | Record or justified N/A | Record | Record |
| h2 | Record | Stage A red / Stage B routed | Record | Record or justified N/A | Record | Record |
| h3/h4 | Record individually | Blue | Record | Record or justified N/A | Record | Record |

## 6. Stage A: prove L2 forwarding and separation

Read h1/h2/h3/h4 data addresses with `netlab connect h1 ip -br address`, substituting one exact host at a time.
Use data addresses, not management addresses or an unresolved hostname that could select management.
In the VM shell, replace these placeholders from your mapping:

```bash
fabric_h2='REPLACE_WITH_H2_DATA_IPV4'
fabric_h3='REPLACE_WITH_H3_DATA_IPV4'
fabric_h4='REPLACE_WITH_H4_DATA_IPV4'
netlab connect h1 ping -c 5 -W 1 "$fabric_h2"
netlab connect h3 ping -c 5 -W 1 "$fabric_h4"
netlab connect h1 ping -c 5 -W 1 "$fabric_h3"
netlab connect s1 --show bgp l2vpn evpn route type 2
netlab connect s1 --show bgp l2vpn evpn route type 3
netlab connect s1 bridge fdb show
```

Generate intended host traffic before expecting remote Type-2/MAC learning.
Pair each remote MAC with the correct VNI and VTEP; Type-3/replication state must correspond to the intended segment.
The first two probes should succeed. The cross-VLAN probe should fail under this no-routing design.
That failure alone is insufficient: require both positive controls, correct host attachment and absence of an unintended routing path.
Record whether the negative probe failed locally for lack of a route or reached a dataplane boundary; those are different observations.

Confirm s1's inter-switch interface from inventory; for the pinned Stage A FRR mapping it is `eth3`.
While repeating an allowed probe in another terminal, capture only that owned interface:

```bash
timeout 20s netlab capture s1 eth3 -nn -e -vv -l -c 30 udp port 4789
```

Save the outer VTEP pair, VNI and inner MAC/IP pair. Missing output, a capture error or management traffic is not proof.
Explain how the observed encapsulation agrees with the route and FDB evidence.
Do not expect a Type-5 tenant prefix in this bridging-only exercise merely to satisfy a checklist.

## 7. Stage B: prove routed VRF service

Switch to the separately prepared Stage B VM and rebuild the identity/address mapping.
Reassign the `fabric_h2`, `fabric_h3`, `fabric_h4` variables to **Stage B** addresses; Stage A values are not reusable evidence.
Repeat the three probes from section 6: red and blue pairs should work, cross-VRF traffic should not.
Also inspect:

```bash
netlab connect s1 --show vrf vni
netlab connect s1 --show bgp l2vpn evpn route type 5
netlab connect s1 --show bgp vrf red ipv4 unicast
netlab connect s1 --show ip route vrf red
netlab connect s1 ip -d link show type vrf
netlab connect s1 ip route show vrf red
```

Identify h2's actual remote subnet in the Type-5 table, its RD/export RT, its import into red, and the corresponding Linux route.
Check blue separately. Confirm red does not import blue, and inspect the return route on s2.
Capture the underlay as in section 6 using **Stage B's actual interface**, which need not be `eth3`.
Connect the transit VNI to the VRF; a successful management ping does not count as routed tenant service.

## 8. Stage B: remove one import membership, then restore it

Owned object: **s1's red VRF EVPN import-RT list**. Preserve its exact running configuration and effective RT list.
Use `netlab connect s1 --show bgp l2vpn evpn vni RED_L3VNI`, substituting red's recorded numeric transit VNI, to inspect its import/export RT details.
Prestate requires one explicit import RT, named `RED_RT` below, with no wildcard or additional automatic import admitting the same routes.
Choose `BAD_RT` as `65000:424242` only after proving no lab route exports it and no existing list uses it.
If the prestate differs, do not improvise deletion of other entries.
Use the actual `RED_RT`, not the literal placeholder, in s1's **FRR CLI**:

```text
configure terminal
router bgp 65000 vrf red
 address-family l2vpn evpn
  route-target import 65000:424242
  no route-target import RED_RT
 exit-address-family
end
```

Adding the unused RT before removing the original keeps an explicit list present.
Deleting the sole manual RT without this guard can restore an automatic RT and invalidate the experiment.
FRR releases have different automatic-RT controls; verify the **effective** import set using VNI detail and the [runtime-matching RT documentation](https://docs.frrouting.org/en/latest/bgp.html).
If the original RT remains effective, classify the injection as not achieved and restore; do not claim isolation was tested.

Expect the global Type-5 advertisement and BGP session to remain, but h2's remote prefix to leave s1's red VRF/FIB and the red probe to fail.
Require the blue pair still to work and h2 to reach its local red gateway; a dead host or broken underlay cannot prove RT isolation.
Read the exact prefix in the global and imported tables and preserve the negative probe's exit/output.
Restore the same object, adding the original membership before removing the temporary one:

```text
configure terminal
router bgp 65000 vrf red
 address-family l2vpn evpn
  route-target import RED_RT
  no route-target import 65000:424242
 exit-address-family
end
```

Require the original effective RT set, remote route, red probe and blue control to recover; do not change the RD, neighbor or export RT.

## 9. Stage B: measure underlay MTU behavior

Owned object: **s1's inter-switch data interface MTU**. The upstream Stage B link requests 1600; verify the actual value is 1600 on the chosen interface before proceeding.
Record that it is not a management/access/bridge/VXLAN interface and that its peer is s2.
Keep a second VM terminal for restoration. Substitute the interface, h1 namespace and h2 data address from this stage's mapping:

```bash
fabric_underlay='REPLACE_WITH_S1_TO_S2_INTERFACE'
fabric_h1_ns='REPLACE_WITH_THIS_LABS_H1_NAMESPACE'
fabric_h2='REPLACE_WITH_H2_DATA_IPV4'
netlab connect s1 ip -d link show dev "$fabric_underlay"
sudo ip netns exec "$fabric_h1_ns" ip -br address
sudo ip netns exec "$fabric_h1_ns" ping -n -M do -s 1200 -c 5 -W 1 "$fabric_h2"
sudo ip netns exec "$fabric_h1_ns" ping -n -M do -s 1400 -c 5 -W 1 "$fabric_h2"
```

Confirm both baseline sizes succeed. The VM's [iputils ping](https://github.com/iputils/iputils/blob/master/doc/ping.xml) supplies `-M do`; no package installation inside the host container is assumed.
For untagged Ethernet with outer IPv4, a 1400-byte ICMP payload produces 1428 bytes of inner IP and roughly 1478 bytes of outer IP after encapsulation.
Record actual tags/headers; IPv6 transport or extra encapsulation changes the budget.

Change only the recorded MTU, then repeat both probes and capture the underlay concurrently:

```bash
netlab connect s1 ip link set dev "$fabric_underlay" mtu 1400
timeout 20s netlab capture s1 "$fabric_underlay" -nn -vv -l -c 30 'ip proto 17 or icmp'
```

The small probe may survive while the larger one drops or outer packets fragment; inner DF does not by itself guarantee outer DF behavior.
The IPv4 protocol filter includes later UDP fragments that a port-only filter could miss; identify VXLAN using the recorded VTEP pair and first fragment.
OSPF can also react to MTU mismatch. Record neighbor state, errors, fragments and any ICMP feedback instead of insisting that BGP must stay established.
If no size-sensitive effect appears, report that observation and investigate encapsulation/fragmentation/offload; do not invent a black hole.
Restore immediately after the bounded collection:

```bash
netlab connect s1 ip link set dev "$fabric_underlay" mtu 1600
netlab connect s1 ip -d link show dev "$fabric_underlay"
```

Recheck OSPF/BGP, both probe sizes, both VRF positive controls and the cross-VRF negative assertion.
Do not flush routes, neighbor tables or all bridges to obtain a clean-looking result.

## 10. Evidence and completion

| Test | Positive control | Intended negative evidence | Restoration proof |
|---|---|---|---|
| L2 segmentation | Both same-VLAN pairs pass, correct VXLAN/FDB | Cross-VLAN blocked with no routing service | Original mappings and repeat probes |
| L3 VPN | Type-5 imported into correct VRF, tenant probe passes | Other VRF absent from import/FIB and probe blocked | Original route/probe matrix |
| RT mismatch | Blue works, target host/local gateway alive | Global route present but red import missing and red probe fails | Exact RT list, route and red probe return |
| MTU reduction | Baseline sizes and known underlay | Measured size/fragmentation/adjacency effect, or explicit non-reproduction | MTU 1600 and full baseline repeated |

For each row retain phase, timestamp, VM/lab identity, upstream revision, tool/image versions, node/interface, expected result, actual output and conclusion.
Use **PASS**, **FAIL**, **BLOCKED** or justified **N/A**; an empty route table, absent probe or missing capture cannot independently be PASS.
Record type/feature N/A from the chosen model, not as a workaround for a broken mandatory test.
All active changes must be reversed on their named objects; if that fails, preserve evidence and restore only the recorded owned VM checkpoint.
Leave experimental changes unsaved; do not replay non-idempotent initialization or perform all-lab teardown/global pruning.
Complete when you can trace L2 and L3 service, explain RD/RT and route types, show isolation with working controls, and demonstrate restoration.
Continue with [Linux performance](04-linux-performance.md), [cloud/CNI design](05-cloud-cni-design.md), the [automation capstone](06-automation-capstone.md) and the [quiz](../../quizzes/networking/expert/03-datacenter-evpn-quiz.md).

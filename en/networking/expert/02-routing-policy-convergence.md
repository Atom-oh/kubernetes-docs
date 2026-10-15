# 02. Routing Policy and Measured Convergence

> **Last Updated**: September 15, 2026
> **Lab boundary**: One separately prepared, owned, disposable Linux routing VM; local FRRouting containers only.
> **Verification status**: Upstream documentation, topology and CLI sources checked; the routing lab was **not executed** while writing this chapter.

After this workbook, you should be able to explain why a prefix was selected, prove that its next hop is usable, and measure what traffic experienced during a controlled failure.
Complete all [eight beginner lessons](../beginner/README.md), including the [container/cloud capstone](../beginner/08-container-cloud-capstone.md), first.
Revisit [Linux forwarding](../../kernel/02-network-stack.md) when a route in a protocol table does not explain the packet path.

## 1. Read with a question to answer

| Reading | Question to answer in your own words |
|---|---|
| [BGP Labs overview](https://bgplabs.net/) and [FRRouting introduction](https://bgplabs.net/basic/0-frrouting/) | Which actions belong in the Linux shell, and which belong in `vtysh`? |
| [Local-preference lab](https://bgplabs.net/policy/5-local-preference/) | Why does a preference set on one edge influence the other edge? |
| [FRR BGP manual](https://docs.frrouting.org/en/latest/bgp.html) | When is a received path eligible, selected, advertised and installed? |
| [FRR OSPF manual](https://docs.frrouting.org/en/latest/ospfd.html) | What does an adjacency prove, and which prefixes does the IGP carry? |
| [RFC 4271](https://www.rfc-editor.org/rfc/rfc4271.html) and [RFC 4456](https://www.rfc-editor.org/rfc/rfc4456.html) | How do ordinary iBGP advertisement rules differ from route reflection? |

Read the selected sections before configuring anything. Produce a diagram with routing sessions and forwarding links drawn separately.
A BGP session is a TCP connection between speakers; it does not mean every advertised destination is reachable through that connection.

## 2. Build the control-plane model

**IGP and BGP solve different problems.** OSPF distributes link-state information within an administrative domain and computes paths using costs.
In this lab it supplies internal reachability, including the loopbacks used for iBGP.
BGP exchanges destination reachability with attributes and applies policy; it is not simply a shortest-hop replacement for OSPF.
Blindly redistributing everything between the protocols introduces extra routes, policy ambiguity and possible feedback.

**eBGP** normally exchanges routes between different autonomous systems; **iBGP** distributes BGP information inside one AS.
AS_PATH helps detect AS-level loops, while ordinary iBGP advertisement restrictions prevent simple internal re-advertisement loops.
An iBGP-learned route is not ordinarily advertised to another iBGP peer; a full mesh, route reflectors or another deliberate design is needed.
Do not infer forwarding topology from that session mesh.

**Next-hop resolution precedes useful forwarding.** A BGP route can be visible but unusable because its next hop has no reachable route.
An iBGP next hop may remain an external address unless the design changes it, for example with next-hop-self.
Check the actual received NEXT_HOP, then recursively resolve it through the routing table to an interface and neighbor.
An OSPF adjacency alone does not prove that the required next-hop prefix was advertised.

| Layer | Evidence | What that evidence does not establish |
|---|---|---|
| BGP session | State and negotiated address families | An intended prefix was accepted |
| BGP RIB | Candidate paths, attributes, validity and best-path marker | The selected route reached the forwarding plane |
| Zebra routing table | Selected route and installation status | Packets actually left the intended interface |
| Linux FIB lookup | Route, outgoing interface and next hop for a destination | Return-path reachability or absence of packet filtering |
| Packet observation | Source-specific probes and interface capture | Every application, packet size or ECMP path works |

Use “BGP table” and “kernel forwarding table” explicitly in reports rather than calling both “the routing table.”
FRR passes routing decisions through Zebra; Linux performs forwarding in this selected software dataplane.

## 3. Explain the policy before testing it

| Mechanism | Operational purpose | Common wrong inference |
|---|---|---|
| Prefix filter | Admit or advertise only intended prefixes and lengths | Permitting a `/24` automatically permits all more-specific routes |
| LOCAL_PREF | Express an AS-internal exit preference; larger is preferred | It tells an external AS which entrance to use |
| Weight | Local implementation-specific preference on one router | It propagates to other routers as a BGP attribute |
| AS_PATH / prepending | Describe AS traversal; influence path selection where policy permits | A shorter path always wins over a higher local preference |
| MED | Suggest an entrance preference under the receiver's comparison rules | It is universally compared across every neighboring AS |
| Community | Carry a label that a receiving policy can interpret | The label enforces a behavior without a matching policy |
| Route reflector | Reduce iBGP session requirements through reflection | It supplies a missing next-hop route or necessarily carries transit packets |

A reflector's ORIGINATOR_ID and CLUSTER_LIST support loop prevention; its path selection can hide alternatives from clients.
For a reflected path, inspect the client, reflector and next-hop reachability separately.
Use [the route-reflector lab](https://bgplabs.net/ibgp/3-rr/) as a later, separately prepared exercise rather than adding a reflector to this workbook's topology.

Write this filter design without deploying it: export only `192.168.42.0/24` toward an upstream.
An exact `/24` match should accept that route, reject `192.168.42.0/25`, and reject the learned provider prefix `192.168.100.0/24`.
Also reject `0.0.0.0/0` unless a separately stated contract permits it.
Explain implicit deny, evaluation order and the direction of attachment.
Continue with [Filter Advertised Prefixes](https://bgplabs.net/policy/3-prefix/) for an active filter exercise; this lab's existing policy is not assumed to implement your proposed filter.

## 4. Prepare this particular lab

The selected upstream is **`bgplab/bgplab`, `policy/5-local-preference/topology.yml`**, revision **`5a9fab68658ce69317b147396481714ee3478482`**.
Its four routers are c1/c2 in AS65000 and x1/x2 in AS65100.
The topology configures OSPF, eBGP, iBGP and advertisements; the learner changes customer policy.
The [source topology](https://github.com/bgplab/bgplab/blob/5a9fab68658ce69317b147396481714ee3478482/policy/5-local-preference/topology.yml) requires **netlab 2.0.0 or newer**.

The supplied `https://bgplabs.net/install/` returned 404 on the check date; use the official [Installation and Setup](https://bgplabs.net/1-setup/) page.
Follow its [Ubuntu installation prerequisite](https://netlab.tools/install/ubuntu/) on this separate VM before this workbook.
Do not reuse the beginner VM, a shared Docker host or a Kubernetes node.

- Allocate an owned x86-64 Ubuntu 24.04 VM. A **planning allowance**, not an upstream minimum or benchmark, is 4 vCPU, 8 GiB RAM and 20 GiB free disk for four FRR containers and tools.
- Prepare netlab, its Ansible dependencies, Docker and containerlab (`clab` provider), Git, iproute2, iputils `ping`, GNU `timeout` and tcpdump using upstream instructions.
- Record the installed netlab release and provider versions. Use the FRR image selected by that installed netlab release; record its tag, image ID/digest and actual `show version`.
- The CLI examples were checked against FRR **10.6.1** source. A different runtime release requires checking its command help before mutation; a generic “FRR image” is not a compatibility guarantee.
- FRR is open source; no commercial router license is required for this selection. Image download and tool preparation still require network access.
- Provider administration requires privilege on this disposable VM; FRR containers use root for the Linux shell/`vtysh`. Keep the VM console available and leave management interfaces alone.
- Establish exclusive ownership of the VM, clone directory and lab name. The customer/provider links are simulated local links, not connections to an ISP or the Internet.

In the **lab VM shell**, create one new clone; the destination must not already exist:

```bash
test ! -e "$HOME/expert-routing-bgplab"
git clone --no-checkout https://github.com/bgplab/bgplab.git "$HOME/expert-routing-bgplab"
git -C "$HOME/expert-routing-bgplab" checkout --detach 5a9fab68658ce69317b147396481714ee3478482
cd "$HOME/expert-routing-bgplab/policy/5-local-preference"
git rev-parse HEAD
git status --short
sha256sum topology.yml
python3 -c 'from importlib.metadata import version; print(version("networklab"))'
containerlab version
docker version
ansible --version
uname -r
```

Stop if the absence check fails; do not run the remaining clone commands over an existing directory.
Record these outputs in the evidence record outside the clone.
Preparation is complete only after the owner follows the upstream startup procedure in this directory with `provider=clab`, customer device `frr` and external device `frr`.
The upstream start operation creates/configures the lab; it is a prerequisite, not a read-only command.
Have the VM owner record the generated node/container identities and save an owned pre-experiment VM checkpoint.
No startup, installation, host configuration or teardown was performed by this chapter's author.

## 5. Readiness and terminal boundaries

Run these from the **same lab directory in the VM shell**:

```bash
netlab defaults --project
netlab status
netlab connect --dry-run c1
netlab connect c1 --show version
netlab connect c1 --show running-config
netlab connect c2 --show bgp ipv4 unicast summary
netlab connect c1 --show ip ospf neighbor
netlab connect c2 --show ip ospf neighbor
```

`netlab defaults --project` requires netlab 2.0.1 or newer; on 2.0.0 inspect the cloned `defaults.yml` instead.
The [connect reference](https://netlab.tools/netlab/connect/) documents both single-node access and `--show`.
`netlab connect c1` opens **c1's Linux shell** for this FRR/clab selection; entering `vtysh` opens **c1's FRR CLI**.
The prompts below are labels, not text to paste:

```text
lab-vm$ netlab connect c1
c1-linux# vtysh
c1# show version
c1# show running-config
c1# exit
c1-linux# exit
```

Run `ip`, `ping` and shell commands in Linux, not at `c1#`.
`configure terminal` enters FRR configuration mode; `end` returns to the FRR operational prompt.
From the VM, `netlab connect c1 --show ip route` runs the correct FRR wrapper; do not send bare `show` commands to a Linux shell.

Readiness requires actual established iBGP/eBGP sessions, the intended OSPF neighbors, two eligible provider paths on c2, and successful bounded probes.
Inspect the images of the **recorded c1, c2, x1 and x2 container identities individually** with `docker inspect --format '{{.Config.Image}} {{.Image}}' CONTAINER`.
Do not substitute a host-wide container listing as proof of these nodes' versions.

## 6. Baseline: predict, observe, explain

At the pinned revision, c1's external peer is `10.1.0.2`; c2's is `10.1.0.6`.
The iBGP loopbacks are `10.0.0.1` and `10.0.0.2`; the customer segment is `192.168.42.0/24`.
Verify those values against the running configuration before using them.
The probe target `192.168.100.10` is x1's address on the simulated provider segment.

```bash
netlab connect c2 --show bgp ipv4 unicast 192.168.100.0/24
netlab connect c2 --show ip route 10.0.0.1/32
netlab connect c2 --show ip route 192.168.100.0/24
netlab connect c2 ip route get 192.168.100.10
netlab connect c2 ping -I 192.168.42.2 -c 5 -W 1 192.168.100.10
netlab connect c1 --show bgp ipv4 unicast neighbors 10.1.0.2 advertised-routes
```

Record both candidate paths, next hops, AS_PATH, LOCAL_PREF, best-path reason and the kernel lookup.
Explain whether c2 selected its directly attached upstream or the exit through c1.
In the advertisement output, classify each actual prefix against your proposed export allowlist; unexpected advertisements are findings, not evidence that the proposed filter ran.
Check x1's route back to `192.168.42.0/24` before blaming outbound policy for missing replies.

## 7. Change one customer's exit preference

Prestate: c1's AS65000 instance has **no explicit** `bgp default local-preference`, the effective default is 100, and no inbound policy overrides the examined provider routes.
c2 also has the baseline effective value 100. Preserve both configurations.
If these conditions differ, stop and establish an appropriate baseline rather than deleting an existing policy.

The owned object is **c1's AS65000 BGP instance**; inverse: remove only the setting introduced here.
In c1's **FRR CLI**:

```text
configure terminal
router bgp 65000
 bgp default local-preference 200
end
show bgp ipv4 unicast 192.168.100.0/24
```

This FRR command is verified in [the 10.6.1 CLI implementation](https://github.com/FRRouting/frr/blob/frr-10.6.1/bgpd/bgp_vty.c); that implementation also reprocesses inbound routes on this instance.
Do not copy upstream wildcard clear examples into a shared environment.
Re-run section 6 on c2: expect the eligible path through c1 to carry 200 and win over the path with 100, followed by the corresponding FIB and packet path.
If attributes do not change, inspect inbound policy, next-hop validity and the actual runtime version; a configuration line alone is not PASS.
This workbook intentionally changes only c1, so the upstream validator's separate expectation of c2=50 is **not** this workbook's acceptance criterion.

## 8. Measure one peer failure

Keep the preference experiment active. Prestate: **c1's neighbor `10.1.0.2`** is established and has no `shutdown` setting.
Inverse: `no neighbor 10.1.0.2 shutdown` in the same BGP instance.
This is an administrative peer failure, not a cable cut, silent packet loss or BFD experiment.

For timestamped probes, use the VM's iputils inside **c2's recorded container network namespace**.
Obtain the name from this lab's inventory/provider mapping and confirm it exists with `ip netns list`; never select by a loose wildcard.
Replace the placeholder before running in a second VM terminal:

```bash
routing_c2_ns='REPLACE_WITH_THIS_LABS_C2_NAMESPACE'
sudo ip netns exec "$routing_c2_ns" ip -br address
sudo ip netns exec "$routing_c2_ns" ping -D -O -n -I 192.168.42.2 -i 0.2 -c 150 -w 40 -W 1 192.168.100.10
```

Require the displayed addresses to match c2. Establish several successful replies before fault injection.
The [iputils `-O` option](https://github.com/iputils/iputils/blob/master/doc/ping.xml) reports outstanding replies; correlate sequence numbers with later replies rather than treating every outstanding report as permanent loss.
In c1's FRR CLI, record the intervention time, then apply:

```text
configure terminal
router bgp 65000
 neighbor 10.1.0.2 shutdown
end
```

From the VM, sample c2's BGP prefix and kernel route from section 6 during the bounded probe window.
In another terminal, use the [capture command](https://netlab.tools/netlab/capture/) on **c2's confirmed backup data interface**; the pinned FRR topology maps it to `eth2`:

```bash
timeout 20s netlab capture c2 eth2 -nn -l -c 40 icmp
```

A timeout bounds collection; no matching packets or an access error is not a successful capture.
Expect c2 to select x2, then reach x1 through the provider's internal segment.
Distinguish `t_action`, first observed route withdrawal/change, FIB change, last failed probe and first sustained recovery.
Define sustained recovery beforehand, for example five consecutive replies; report sampling interval and uncertainty.
Use the same VM clock for probe and intervention records; record a VM-shell `date -u +%FT%T.%NZ` immediately before the CLI action and include manual terminal latency in the uncertainty.
Zero observed losses means no outage was resolved at this sampling rate, not zero convergence time.
Hold timers, BFD, graceful restart, failure detection, route processing and FIB programming can all affect results; do not assert a universal fixed convergence time.

## 9. Restore, repeat and submit

Restore the **peer first**, in c1's FRR CLI:

```text
configure terminal
router bgp 65000
 no neighbor 10.1.0.2 shutdown
end
```

Verify the peer re-establishes, the preferred route returns and probes recover.
Then restore the **policy object**:

```text
configure terminal
router bgp 65000
 no bgp default local-preference
end
```

Recheck running configuration, both candidate routes, effective preference, FIB lookup and the original source-specific probe.
Do not save experimental settings to startup configuration, restart FRR or run broad cleanup commands.
If recovery fails, stop further experiments and report the differing object; the owner can restore the recorded checkpoint of this single disposable VM after exporting evidence.
The new clone remains as evidence; eventual disposal is limited to this owned VM under the owner's lifecycle procedure.

| Phase | Required positive evidence | Negative/failure evidence to preserve |
|---|---|---|
| Baseline | Two eligible paths, usable next hop, successful probe | Missing return route, unresolved next hop or setup error |
| Preference | c1-derived LOCAL_PREF 200, selected exit, matching forwarding | Attribute unchanged or RIB/FIB disagreement |
| Peer failure | Observed alternate path and sustained probe recovery | Loss interval, absent alternate route, capture errors |
| Restoration | Original configuration and forwarding behavior | Remaining shutdown, policy drift or persistent loss |

Repeat the failure measurement three times only after each restoration passes; report individual samples and the observed range.
Keep raw timestamps and outputs rather than only an average. Label all results as measured, planned or blocked.
A missing route, absent probe record or empty capture cannot satisfy a positive assertion.
Complete the chapter when you can explain policy, recursive next-hop resolution, a counterexample to “session up means service up,” measurement limits and verified restoration.
Continue to [EVPN](03-datacenter-evpn.md), then use [Calico BGP](../calico/04-bgp-deep-dive.md) as the Kubernetes specialist continuation.
Submit your matrix to the [automation capstone](06-automation-capstone.md) and complete the [quiz](../../quizzes/networking/expert/02-routing-policy-convergence-quiz.md).

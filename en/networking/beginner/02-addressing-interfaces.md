# 2. Addresses, subnets, and network interfaces

> **Supported Versions**: Ubuntu Server 24.04 LTS (primary), Rocky Linux 9 (alternate)
> **Last Updated**: September 15, 2026

[Previous: Linux terminal](01-linux-cli.md) | [Course preparation](README.md) | [Quiz](../../quizzes/networking/beginner/02-addressing-interfaces-quiz.md) | [Next: Persistent configuration](03-persistent-configuration.md)

A network interface can have a cable, an address, and still fail to reach a service. Those are different layers of the problem. This lesson first follows a message across those layers, then builds one small local IPv4 network so you can see the distinction yourself.

## Prerequisites and outcomes

Complete [lesson 1](01-linux-cli.md): use a normal account, `sudo`, variables, a unique scratch directory, and the VM console confidently. Start with two disposable local VMs. Both may run Ubuntu Server 24.04 LTS, or use Rocky Linux 9 as the alternate administration path. These commands use `iproute2` (`iproute` package on Rocky) and `ping` from iputils; have them available before the exercise. No packages are installed in this lesson.

Prepare the following in the hypervisor as described in [course preparation](README.md). “Internal-only” means both virtual NICs attach to the **same isolated virtual network**, without a DHCP server, router, or external uplink. A host-only network is not automatically equivalent: hypervisors may give it host access or DHCP.

| Guest role | Existing management NIC | Separate internal lab NIC |
| --- | --- | --- |
| Client | Existing NAT/DHCP connection, unchanged | `192.0.2.10/24`, no gateway or DNS |
| Server | Existing NAT/DHCP connection, unchanged | `192.0.2.20/24`, no gateway or DNS |

Record **both NICs' MAC addresses for each guest** from the hypervisor settings, plus which virtual network each attaches to. Use distinct MAC addresses for the two guests. Keep their consoles open. The `192.0.2.0/24` block is reserved for documentation (RFC 5737); use it only in this isolated lab, never as a real Internet destination. Do not bridge the lab NIC to your home, company, or cloud network.

By the end, you should be able to:

- Separate Ethernet frames, IP packets, transport ports, and application services.
- Calculate a subnet boundary and decide whether a destination is local or requires a router.
- Explain what gateways, DHCP, DNS, ARP, and IPv6 neighbor discovery each do.
- Match a guest interface to the correct hypervisor NIC without guessing a name.
- Inspect links, addresses, routes, and neighbors, add one temporary IPv4 address to each lab NIC, and undo precisely those changes.

**Execution contract:** run commands only **inside the named practice VM**, as a normal user unless a line includes `sudo`. Never configure the physical host or documentation host. Commands labelled “each VM” mean repeat separately in its own console; variables are local to that shell. Examples are illustrative, **not live-tested VM results**. Stop on an unexpected error before continuing.

## Follow one message from application to cable

Imagine a future exercise where the client asks the server for a web page at TCP port `8080`. A web server must actually listen there; assigning an IP address does not create one.

| Layer | What it carries or identifies | Example in our local lab |
| --- | --- | --- |
| Application | Meaning of the request and response | An HTTP request for a page |
| Transport | TCP or UDP communication endpoints using port numbers | Client's temporary TCP source port to server TCP port `8080` |
| Internet | IP packet with source/destination addresses for routing | `192.0.2.10` to `192.0.2.20` |
| Local link | Ethernet frame with source/destination MAC addresses | Client lab NIC MAC to server lab NIC MAC |

The sender wraps application data in transport information, then an IP packet, then a frame for the current link. The receiver removes those wrappers. Frames carry traffic on a link; routers forward IP packets between networks. At a router, the link-layer frame is replaced for the next link. This simple lab does not need a router between the guests.

A **MAC address** identifies an Ethernet interface on its link; a virtual NIC also has one. An **IP address plus prefix** tells the host how to locate an interface in an IP network. A NIC may have several addresses. Neither address is proof of a person's identity.

A **port** is a 16-bit number in TCP or UDP, not the physical connector on the VM. TCP port `8080` and UDP port `8080` are different endpoints. The protocol, source IP/port, and destination IP/port distinguish a conversation. A reachable IP does not mean that a chosen port is listening or permitted by a firewall. ICMP, used by `ping`, does not use TCP/UDP port numbers. We will test application services in later lessons.

## Work out IPv4 and CIDR instead of memorizing them

IPv4 addresses have 32 bits, usually written as four decimal octets, each `0`–`255`. A **prefix length**, written after `/`, tells you how many leading bits describe the network. The remaining bits distinguish addresses within it. This slash notation is called CIDR notation.

For `192.0.2.10/24`, the first 24 bits are the network and 8 bits remain:

| Calculation | Result |
| --- | --- |
| Prefix mask: 24 one-bits then 8 zero-bits | `255.255.255.0` |
| Address with host bits all zero | Network address `192.0.2.0` |
| Address with host bits all one | Broadcast address `192.0.2.255` |
| Number of addresses | `2^(32-24) = 256` |
| Ordinary host range in this subnet | `192.0.2.1`–`192.0.2.254` |

Here the two end addresses are not assigned to ordinary hosts, leaving 254 host addresses. Special `/31` point-to-point and `/32` cases follow different rules and are outside this first lab. Both `.10/24` and `.20/24` are in `192.0.2.0/24`. `192.0.3.20` is outside it, even though its first two octets match.

For a less obvious example, consider **`192.0.2.70/26`**:

1. `/26` leaves 6 host bits, giving `2^6 = 64` addresses per block.
2. The mask is `255.255.255.192`. Its last octet is binary `11000000`.
3. The last octet of `.70` is binary `01000110`. Keeping its first two bits and zeroing the rest gives `01000000`, or `.64`.
4. Blocks therefore start at `.0`, `.64`, `.128`, and `.192`. The `.70` address falls in the `.64` block.
5. Its network is `192.0.2.64/26`, broadcast is `.127`, and ordinary host range is `.65`–`.126` (62 host addresses).

Thus `.100/26` shares that subnet with `.70/26`; `.130/26` does not. Matching the first three octets is insufficient unless the prefix is `/24`. A larger prefix number gives a smaller address block. Use `/24` in the actual lab, not the `/26` calculation example.

## Gateway, DHCP, DNS, and neighbors answer different questions

A **route** tells the kernel where to send a packet. A directly connected route says “this destination is on that interface's link.” A route containing `via` selects a next-hop router, commonly called a **gateway**. If several routes match, the longest matching prefix wins first. A **default route** (`0.0.0.0/0`, displayed as `default`) is the fallback when no more specific route applies.

For `.10` sending to `.20` in our `/24`, the connected route is more specific than a management default route. The client sends directly on the lab link. There is **no lab gateway to enter**, and `.1` is not automatically a router. Keep the existing management default route where it is.

| Mechanism | Question it answers | What it does not prove |
| --- | --- | --- |
| DHCP | “Can a configuration server lease me an address and supply options such as routes/DNS?” | That a web service is running |
| DNS | “What address or other record belongs to this name?” | That a route or listening service exists |
| IPv4 ARP | “Which MAC address currently corresponds to this IPv4 neighbor on my link?” | That the neighbor accepts a TCP connection |

DHCP is configuration exchange, not the act of forwarding every packet. DNS resolves names; it does not assign the client's own IP address. On an off-subnet IPv4 journey, ARP normally finds the **next-hop gateway's MAC**, not a remote server's MAC across the Internet.

Our lab NIC has no DHCP server and needs neither gateway nor DNS for literal-IP communication. The separate management NIC can continue using its existing DHCP configuration. We will change neither its address nor its resolver settings.

IPv6 uses **128-bit** addresses written in hexadecimal groups separated by colons. Leading zeroes in a group may be omitted, and `::` can compress one run of all-zero groups. `::1` is loopback; an address beginning `fe80:` is commonly a link-local address, usable only on its link. Multiple interfaces may have link-local addresses, so a destination may require a zone such as `%interface-name` to identify the link. Interface names must come from the guest, not this example.

`2001:db8::/32` is IPv6 documentation space (RFC 3849), not an address to configure here. Ordinary IPv6 LAN prefixes are commonly `/64`. IPv6 uses ICMPv6 Neighbor Discovery instead of ARP and has no IPv4-style broadcast. Router advertisements, SLAAC, and DHCPv6 are separate configuration topics. A link-local IPv6 address alone does not prove Internet access. Leave existing IPv6 settings enabled and unchanged while learning the IPv4 exercise.

## Inspect before selecting an interface

The modern `ip` command groups related objects: `link` for devices, `address` (also `addr` or `a`) for addresses, `route` for routing, and `neigh` for the neighbor table. Reading these normally needs no `sudo`.

**Each VM, normal user; inspect only:**

```bash
hostname
ip -br link
ip -br address
ip a
ip -4 route
ip neigh
```

`-br` requests brief output. `-4` limits the command to IPv4; without it, `ip a` also displays IPv6. `ip a` is short for `ip address`, not a command to add an address.

Illustrative brief output **with labels substituted for actual interface names**:

```text
lo            UNKNOWN  00:00:00:00:00:00 <LOOPBACK,UP,LOWER_UP>
<management>  UP       02:00:00:00:01:10 <BROADCAST,MULTICAST,UP,LOWER_UP>
<lab>         DOWN     02:00:00:00:02:10 <BROADCAST,MULTICAST>
```

Read a row as interface name, operational state, MAC address, then flags. Match the **full MAC** against the hypervisor record, separately for each guest. NIC order, PCI attachment, image settings, and OS naming rules can change names. Neither “the second row” nor a guessed `eth1`/`ens19` is reliable. `lo` is loopback inside the guest and is not a virtual Ethernet NIC.

The flag `UP` means administratively enabled. `LOWER_UP` indicates lower-layer carrier. A device may be administratively up but lack carrier; in that case inspect the virtual cable and internal-network attachment. The displayed operational state `UNKNOWN`, especially on loopback, is not automatically failure. Save the original administrative state before changing anything.

## Record the boundary and baseline on each VM

**Each VM, normal user; type the actual names when prompted:**

```bash
read -r -p 'Lab NIC name matched by MAC: ' LAB_IF
read -r -p 'Management NIC name matched by MAC: ' MGMT_IF
ip -br link show dev "$LAB_IF"
ip -br link show dev "$MGMT_IF"
ip -4 address show dev "$LAB_IF"
ip -4 route show table main
```

`read` stores your input in a shell variable; it does not change an interface. If a name is empty, a device is missing, the names are equal, or either MAC differs from your record, stop and redo the identification. Do not continue merely because a command accepts a name.

**Pre-change gate:** the lab NIC must have **no IPv4 address already assigned**, and the guest must have no existing IPv4 route overlapping `192.0.2.0/24` except the management default (`default`), which is expected. An existing IPv6 link-local address is fine. If the lab NIC already has an IPv4 address or an unexpected route appears, stop and reconcile the course preparation; do not delete unknown state or reuse an address owned by a network manager. The guests' managed networking may later replace manual state, which is why this exercise is temporary.

Create a place to keep the baseline. Do this independently on both guests.

**Each VM, normal user:**

```bash
NET_NOTE_DIR=$(mktemp -d "$HOME/network-beginner-ip.XXXXXX")
printf '%s\n' "$NET_NOTE_DIR"
```

Record this exact path. Stop if creation fails or the value is empty. Then capture the baseline:

```bash
ip -details link show dev "$LAB_IF" > "$NET_NOTE_DIR/lab-link.before"
ip -4 -br address show dev "$MGMT_IF" > "$NET_NOTE_DIR/management-addresses.before"
ip -4 route show table main > "$NET_NOTE_DIR/routes.before"
cat "$NET_NOTE_DIR/lab-link.before"
```

`>` writes output to the named file, replacing an existing file of that name; here the directory is new. In the link flags, determine whether the **standalone `UP` flag** is present. `LOWER_UP` alone is not the answer. Record your result with **one** of these assignments, in that VM's shell:

```bash
# Use this only if the standalone UP flag was present:
LAB_LINK_WAS=up
```

```bash
# Otherwise use this:
LAB_LINK_WAS=down
```

Record the original state, MACs, interface names, and baseline directory outside the shell as well. Cleanup needs them if the session is lost.

## Add the two temporary addresses

Choose **one role block per VM**. These assignments only store text. The client and server addresses must not be swapped accidentally or assigned to both guests.

**Client VM only, normal user:**

```bash
LAB_IP=192.0.2.10
LAB_CIDR=192.0.2.10/24
LAB_PEER=192.0.2.20
```

**Server VM only, normal user:**

```bash
LAB_IP=192.0.2.20
LAB_CIDR=192.0.2.20/24
LAB_PEER=192.0.2.10
```

Check the target once more before elevation.

**Each VM, normal user:**

```bash
printf 'guest=%s lab=%s management=%s address=%s original-link=%s\n' \
  "$(hostname)" "$LAB_IF" "$MGMT_IF" "$LAB_CIDR" "$LAB_LINK_WAS"
ip -br link show dev "$LAB_IF"
```

Compare with your role and recorded MAC. Then, **each VM, normal user invoking sudo**, add only this VM's lab address:

```bash
sudo ip link set dev "$LAB_IF" up
sudo ip address add "$LAB_CIDR" dev "$LAB_IF"
```

`link set ... up` enables the identified lab NIC administratively; it does not modify the management NIC. `address add` assigns an additional address to the guest **on its secondary NIC**. This is not “add a second IPv4 address to the management NIC,” nor a requirement for Linux to display a `secondary` flag.

A successful add normally prints nothing. If you see `File exists`, inspect the addresses and stop instead of switching to `replace` or flushing the interface. If you enabled an initially down lab NIC but the add failed, the link-state part of cleanup below still applies; remove an address only if your own add succeeded.

This `ip` change updates the kernel's current state, not Netplan or NetworkManager configuration. A reboot removes manually added state; a network manager may remove or recreate addresses earlier. An address lifetime displayed as `forever` means no expiry timer on this runtime address, **not** persistence across reboot. Persistent configuration is the next lesson.

## Interpret the result at each layer

**Each VM, normal user; inspect only:**

```bash
ip -br link show dev "$LAB_IF"
ip -4 address show dev "$LAB_IF"
ip -4 route show dev "$LAB_IF"
ip -4 route get "$LAB_PEER"
```

On the client, illustrative relevant lines might be:

```text
inet 192.0.2.10/24 scope global <lab-name>
    valid_lft forever preferred_lft forever
192.0.2.0/24 dev <lab-name> proto kernel scope link src 192.0.2.10
192.0.2.20 dev <lab-name> src 192.0.2.10 uid 1000
```

The address says “this NIC owns `.10/24`.” `scope global` is Linux's address-scope label; it does not turn a documentation address into a globally reachable address. By default, adding the address also creates a route for its connected prefix. `proto kernel` identifies that automatically created route, `scope link` says no next-hop router is needed, and `src` gives a preferred source address. The server should similarly own `.20/24` and select `.20` as its source.

`ip route get` asks the kernel how it would route to one destination; **it sends no probe packet**. For the peer it should select the lab NIC, the correct local source, and no `via` gateway. A route through the management NIC indicates a setup error even if some other connectivity works. If a connected route is missing or an address disappears, inspect link state and manager ownership; do not add a competing default route.

After configuring **both** guests, generate a small amount of traffic so ARP has a reason to resolve the peer.

**Each VM, normal user:**

```bash
ping -4 -c 3 -W 2 -I "$LAB_IF" "$LAB_PEER"
ip -4 neigh show dev "$LAB_IF"
```

`ping -4` uses IPv4 ICMP echo, `-c 3` limits it to three requests, `-W 2` sets the reply timeout in seconds, and `-I` selects the lab interface. The usual iputils packaging allows this echo test as a normal user. A permission error concerns tool/capability configuration, not proof that the network is down.

Expect replies and a summary of transmitted/received packets on a correctly configured path that allows ICMP. Timing varies; do not copy a claimed latency from a sample. An illustrative neighbor entry is:

```text
192.0.2.20 dev <lab-name> lladdr 02:00:00:00:02:20 REACHABLE
```

Compare `lladdr` with the **peer lab NIC's MAC** recorded in the hypervisor. `REACHABLE` means recently confirmed; `STALE` means a cached mapping exists but needs reconfirmation when used, not immediate failure. An empty table before any traffic is normal. `INCOMPLETE` means resolution is in progress; `FAILED` means it failed. Entries are dynamic, so the state can change while you read.

| Observation | Next check within this lesson |
| --- | --- |
| No carrier / no `LOWER_UP` | Hypervisor virtual cable and attachment to the correct internal network |
| Wrong or missing IPv4 address | Role variables, add result, and whether a manager changed the NIC |
| Peer route uses management NIC | Prefix, lab address, and the route lookup |
| Neighbor stays `INCOMPLETE`/`FAILED` | Both VMs running, same internal network, peer address, unique MACs and IPs |
| Neighbor MAC resolves but ping has no replies | Peer status and ICMP filtering; ARP success is not ICMP/service success |

Do not disable firewalls or IPv6 to make this first test pass. Save the evidence and continue with the diagnostic method in lesson 4 and firewall policy in lesson 6 as needed.

## Success check and exact cleanup

Before undoing anything, verify on **both guests** that:

1. MAC matching identifies separate management and lab interfaces.
2. The lab NIC has the role's exact `/24` address and a connected `192.0.2.0/24` route.
3. The peer route uses the lab NIC and correct source without a gateway.
4. Neighbor evidence is understood; successful ICMP replies establish this limited IP test, not an open TCP service.
5. The management address, default route, and original management access still match the recorded baseline.

**Each VM, normal user; compare the saved/current management data:**

```bash
cat "$NET_NOTE_DIR/management-addresses.before"
ip -4 -br address show dev "$MGMT_IF"
cat "$NET_NOTE_DIR/routes.before"
ip -4 route show table main
```

The new lab connected route is expected; a new lab default route is not. DHCP may independently renew the management lease, so compare interface, address, gateway, and route purpose rather than treating every dynamic detail as a change made by the lab.

Practice rollback now, independently on each VM. If the shell was lost, first re-identify the NICs by recorded MAC and restore `LAB_IF`, `MGMT_IF`, `LAB_IP`, `LAB_CIDR`, `LAB_LINK_WAS`, and `NET_NOTE_DIR` from **that guest's** record. Inspect live state; variables do not survive automatically. Do not guess an address to delete.

**Each VM, normal user; verify that your successfully added address is still present:**

```bash
ip -4 address show dev "$LAB_IF"
```

**Each VM, normal user invoking sudo; delete only its own added address:**

```bash
sudo ip address del "$LAB_CIDR" dev "$LAB_IF"
```

Run the delete only if your add succeeded and the address is still present. If you already rebooted or a manager removed it, skip deletion after confirming absence. This is a targeted inverse: it specifies the exact IP, prefix, and interface. No address or route is flushed. Given the empty-IPv4 precondition, deleting the sole lab IPv4 address also removes its automatically created connected route.

**Each VM, same shell, normal user invoking sudo only when required:**

```bash
if [ "$LAB_LINK_WAS" = down ]; then
  sudo ip link set dev "$LAB_IF" down
fi
```

This conditional restores a link that **you** brought up from down. If it was already up, leave it up. `[` tests the recorded value; only the `down` branch executes the privileged command. If that value is missing, recover your record rather than inventing an original state.

**Each VM, normal user; verify recovery:**

```bash
ip -br link show dev "$LAB_IF"
ip -4 address show dev "$LAB_IF"
ip -4 route show dev "$LAB_IF"
ip -4 -br address show dev "$MGMT_IF"
ip -4 route show default
```

Expect no lab IPv4 address or connected route, the original administrative link state, and the original management configuration/access. Dynamically learned neighbor entries may age out; do not flush a table to make it look empty. If an address reappears, a manager may own it: pause and investigate persistent configuration rather than repeatedly deleting it.

Once the baseline is no longer needed, remove only its three files and the empty directory.

**Each VM, normal user:**

```bash
rm -i -- "$NET_NOTE_DIR/lab-link.before" \
  "$NET_NOTE_DIR/management-addresses.before" "$NET_NOTE_DIR/routes.before"
rmdir -- "$NET_NOTE_DIR"
test ! -e "$NET_NOTE_DIR"
echo $?
unset LAB_IF MGMT_IF LAB_IP LAB_CIDR LAB_PEER LAB_LINK_WAS NET_NOTE_DIR
```

Confirm only your three snapshot text files. Exit status `0` from the existence check means cleanup succeeded; inspect exact remaining filenames if `rmdir` fails. No persistent network configuration was edited. [Lesson 3](03-persistent-configuration.md) will re-establish the same addresses under the actual network manager; it must not depend on variables or temporary state left by this shell.

## References and further reading

Primary documentation checked September 14–15, 2026:

- [Ubuntu 24.04 `ip-address` manual](https://manpages.ubuntu.com/manpages/noble/man8/ip-address.8.html), [`ip-link`](https://manpages.ubuntu.com/manpages/noble/man8/ip-link.8.html), [`ip-route`](https://manpages.ubuntu.com/manpages/noble/man8/ip-route.8.html), and [`ip-neighbour`](https://manpages.ubuntu.com/manpages/noble/man8/ip-neighbour.8.html) — command syntax, connected routes, address lifetimes, and neighbor states.
- [Ubuntu 24.04 `ping` manual](https://manpages.ubuntu.com/manpages/noble/man8/ping.8.html) — bounded echo tests and interface selection.
- [IETF RFC 1122](https://www.rfc-editor.org/rfc/rfc1122.html), [RFC 4632](https://www.rfc-editor.org/rfc/rfc4632.html), and [RFC 826](https://www.rfc-editor.org/rfc/rfc826.html) — Internet layers, CIDR, and IPv4 address resolution.
- [IETF RFC 2131](https://www.rfc-editor.org/rfc/rfc2131.html) and [RFC 1034](https://www.rfc-editor.org/rfc/rfc1034.html) — DHCP and DNS have different responsibilities.
- [IETF RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.html) and [RFC 3849](https://www.rfc-editor.org/rfc/rfc3849.html) — reserved documentation address blocks.
- [IETF RFC 4291](https://www.rfc-editor.org/rfc/rfc4291.html) and [RFC 4861](https://www.rfc-editor.org/rfc/rfc4861.html) — IPv6 addressing and Neighbor Discovery.

Try the [quiz](../../quizzes/networking/beginner/02-addressing-interfaces-quiz.md), then continue to [Persistent configuration](03-persistent-configuration.md).

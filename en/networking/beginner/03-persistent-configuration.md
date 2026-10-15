# 03. Persistent Network Configuration

> **Supported Versions**: Ubuntu Server 24.04 LTS (primary), Rocky Linux 9 (alternative)
> **Last Updated**: September 15, 2026

An address added with `ip address add` changes the running kernel configuration. It is not an instruction for the next boot. In this chapter you give the network's configuration owner a durable instruction, then compare the saved configuration with what the VM actually uses.

## Prerequisites and outcomes

Complete [addressing and interfaces](02-addressing-interfaces.md) and prepare the [course lab](README.md). Use two disposable VMs and their hypervisor consoles. Both VMs may run Ubuntu; learning Rocky at the same time is optional.

| Item | Required state |
|---|---|
| Client lab NIC | `192.0.2.10/24` after this lesson |
| Server lab NIC | `192.0.2.20/24` after this lesson |
| Lab network | Same internal virtual network, no DHCP server, router or uplink |
| Management NIC | Separate existing NAT/DHCP connection; preserve its address, routes and DNS configuration |
| Identity | Record each NIC's MAC in the hypervisor and match it inside the guest |
| Access and tools | Guest console, sudo access, an editor, `ip`, and the installed network manager's tools |

Run the commands **inside the named VM**, never on the workstation hosting the VMs. Do not install or enable a second network manager to follow an alternative branch. If a required tool is absent, return to lab preparation.

You will be able to identify configuration ownership, persist a static address, explain when DHCP/gateway/DNS settings are appropriate, verify after reboot, and undo only your lab changes. First take a VM snapshot and keep the console open. Perform each step separately; an error means inspect it before proceeding.

## 1. Identify the NIC and the owner

On **each VM**, read the inventory without changing anything:

```bash
cat /etc/os-release
ip -br link
ip -br address
ip -4 route show
ip -6 route show default
systemctl is-active systemd-networkd NetworkManager
```

`ip -br link` pairs interface names with MAC addresses. Match the hypervisor's **lab** MAC, not the first interface in the list. The NAT/DHCP NIC normally carries the management default route. Record its identity and current route/DNS settings before continuing. `systemctl is-active` may return a nonzero status because one of the two services is absent or inactive; that alone is not a fault.

Throughout this chapter, replace `REPLACE_WITH_LAB_NIC` with the name you just verified. Variables belong to the current shell; independent blocks repeat them. Never assign a lab value to shell variables such as `HOME` or `PATH`.

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
ip link show dev "$LAB_IF"
ip -4 address show dev "$LAB_IF"
ip -4 route show dev "$LAB_IF"
```

The second command shows the kernel's current addresses; it does not identify who will recreate them. Finish chapter 02's targeted cleanup of its temporary address before starting here. A newly added lab NIC should have no remaining temporary IPv4 address. Do not remove an address owned by an existing profile just because you did not expect it.

Choose the owner from evidence:

| Evidence | Configuration owner and action |
|---|---|
| Ubuntu Netplan YAML selects `networkd`; `networkctl status` identifies the corresponding network file | Follow branch A |
| Rocky NetworkManager reports a managed device and its profiles | Follow branch B |
| Netplan selects `NetworkManager` | Netplan is an upstream source of configuration too; inspect the YAML and generated profile before editing |
| cloud-init, a provisioning tool, direct `.network` files, wildcard matches, or multiple definitions own the same NIC | Resolve ownership before adding another definition; use a clean course VM if the source is unclear |

Netplan translates YAML into backend configuration. `systemd-networkd` and NetworkManager apply configuration to devices; `nmcli` and `nmtui` both talk to NetworkManager. A running service does not prove it owns every NIC. The Ubuntu Server path used here is not a claim about every Ubuntu image, Ubuntu Desktop, or Debian installation.

### Branch A ownership checks: Ubuntu Netplan/networkd

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
sudo netplan get
sudo ls -l /etc/netplan
networkctl status "$LAB_IF"
sudo ls -l /etc/systemd/network /run/systemd/network
resolvectl status
```

`netplan get` displays the merged configuration; inspect the actual YAML files with `sudo less /etc/netplan/ACTUAL_FILE.yaml`, using a filename from the listing. Also inspect any existing `/lib/netplan` and `/run/netplan` directories. `networkctl status` shows the matching network file, if any. `resolvectl status` records the existing DNS servers and links.

Netplan combines differently named YAML files in lexical order: later scalar values replace earlier ones, but lists can be **concatenated**. Adding a later file with an empty address/DNS list is not a general way to erase an earlier list. A differently named definition can also match the same NIC. See [Netplan file merging](https://netplan.readthedocs.io/en/stable/netplan-generate/).

The procedure below requires a lab NIC with **no existing persistent definition**, including wildcard matches in direct networkd files. If an installer already defined it, inspect that file's owner and take a backup before deliberately editing its exact lab stanza instead; do not paste this file over the installer file or keep two definitions. A cloud-init comment is a reason to inspect the provisioning source, not to disable cloud-init globally. For a first lab, adding the internal NIC after the OS's initial setup avoids many such conflicts.

### Branch B ownership checks: Rocky NetworkManager

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
nmcli --version
nmcli device status
nmcli -f GENERAL,IP4,IP6,CONNECTIONS device show "$LAB_IF"
nmcli -f NAME,UUID,TYPE,DEVICE,AUTOCONNECT connection show
```

`device` describes the NIC; `connection` describes a saved profile. Their names need not match. `GENERAL.CON-UUID` identifies the currently active profile, if one exists. `CONNECTIONS` helps identify compatible profiles, including inactive ones. Record the previous lab profile's UUID and whether it was active; preserve the management profile.

Inspect each compatible profile with `nmcli connection show uuid ACTUAL_UUID`. Record its `connection.interface-name`, `802-3-ethernet.mac-address`, `connection.autoconnect`, and `connection.autoconnect-priority`. Empty device/MAC bindings can allow an Ethernet profile to match multiple NICs. Do not change such a shared profile merely to simplify the lab.

Rocky 9 supports NetworkManager's keyfile configuration and may also have older ifcfg profiles. Do not infer the storage format solely from an interface name. The [versioned Rocky 9 guide](https://docs.rockylinux.org/9/guides/network/basic_network_configuration/) covers that release; the [unversioned guide](https://docs.rockylinux.org/guides/network/basic_network_configuration/) now discusses Rocky 10.

## 2A. Persist the address with Netplan/networkd

Use this branch only after branch A's ownership checks. Repeat it on the client and server with **their own MAC and address**.

### Back up and create one owned file

On each **Ubuntu VM**, create a new recovery directory. If it already exists, stop and inspect that earlier attempt; do not replace its backup.

```bash
sudo mkdir -m 700 /root/network-beginner-03
sudo cp -a /etc/netplan /root/network-beginner-03/netplan-before
sudo sh -c 'umask 077; set -C; : > /etc/netplan/90-beginner-lab.yaml'
sudoedit /etc/netplan/90-beginner-lab.yaml
```

`cp -a` preserves the original files and permissions. The small `sh` command creates a root-only empty file; `set -C` refuses to overwrite an existing file. `sudoedit` opens an editable copy using your configured editor.

Paste this **complete YAML document**, using spaces rather than tabs. Replace the example MAC with the client's actual lab MAC. On the server, replace the MAC with the server's lab MAC and change the address to `192.0.2.20/24`.

```yaml
network:
  version: 2
  ethernets:
    beginner-lab:
      renderer: networkd
      match:
        macaddress: "02:00:00:00:00:10"
      dhcp4: false
      dhcp6: false
      accept-ra: false
      link-local: []
      addresses:
        - 192.0.2.10/24
      optional: true
```

| Setting | Meaning in this lab |
|---|---|
| `version: 2` | Netplan's configuration schema version |
| `beginner-lab` | A definition ID; MAC matching selects the NIC without renaming it |
| Device-level `renderer` | Select networkd for this definition without changing the global renderer |
| `dhcp4: false` | No DHCP request on a network that has no DHCP server |
| IPv6 and link-local settings | Keep this isolated exercise IPv4-only on this NIC; this is not a host-wide IPv6 recommendation |
| `addresses` | One address with a `/24` prefix; the connected subnet needs no gateway |
| `optional: true` | networkd does not hold up boot waiting for this lab NIC; it still configures it |

There is deliberately no `routes` or `nameservers` block. Neither VM is a router or DNS server. Guessing `192.0.2.1` as a gateway would not create one. The management NIC retains its original configuration.

### Validate, try, and observe

```bash
sudo chmod 600 /etc/netplan/90-beginner-lab.yaml
sudo netplan generate
sudo netplan get
```

`chmod 600` allows only root to read/write the file. `generate` checks and generates backend configuration without applying it in this normal, already booted session. Success is usually silent. Check the merged output: exactly the intended lab address/MAC, no added lab gateway/DNS, and the original management definition. A valid YAML document can still contain the wrong MAC or address.

From the **VM console**, start the trial:

```bash
sudo netplan try --timeout 120
```

While the confirmation prompt waits, use a second console/login to inspect:

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
ip -4 address show dev "$LAB_IF"
ip -4 route show dev "$LAB_IF"
ip -4 route show default
ip -6 route show default
networkctl status "$LAB_IF"
resolvectl status
```

Expect the local `192.0.2.0/24` route, the correct `.10` or `.20` address, no default route/DNS introduced by the lab NIC, and the original management path still available. Confirm the trial only after those checks. Configure both VMs before requiring a successful peer ping.

`try` and `apply` operate on the **merged configuration**, not only the new file, and can reapply networking across devices. Console access remains necessary even when the management definition was not edited. `try` intends to revert an unconfirmed trial, but [Netplan documents rollback bugs](https://netplan.readthedocs.io/en/stable/netplan-try/). Timeout or Ctrl+C is **not proof of recovery**; inspect runtime state and the files on disk.

### Netplan recovery and rollback

Keep the working lab configuration for later lessons. To abandon this change, recover from the **console**:

1. Inspect `/etc/netplan/90-beginner-lab.yaml` and confirm it is the file created here.
2. Move only that file outside Netplan's input directories.
3. Generate and apply the remaining, previously working configuration.

```bash
sudo mv -i /etc/netplan/90-beginner-lab.yaml /root/network-beginner-03/90-beginner-lab.failed.yaml
sudo netplan generate
sudo netplan apply
```

`mv -i` asks before replacing a previous failure copy. If `generate` fails, stop before `apply`. If you chose to edit an existing owner file instead of using the fresh-NIC path, compare it with its corresponding file in `netplan-before` and restore **that exact edited file**, then generate/apply; do not replace the entire directory.

Recheck addresses, routes and management access. A now-unmanaged lab NIC can retain runtime state. **Only if this lesson's exact address is still present**, remove that address:

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
LAB_CIDR='192.0.2.10/24'
sudo ip address del "$LAB_CIDR" dev "$LAB_IF"
```

On the server set `LAB_CIDR='192.0.2.20/24'`. If the initial inventory recorded the lab NIC administratively down, restore that state with `sudo ip link set dev "$LAB_IF" down` in the same shell. Do not delete management routes or flush interfaces. Before rebooting as a final recovery step, verify that the disk configuration is the restored one. If ownership or recovery is unclear, restore the pre-lesson VM snapshot.

## 2B. Persist the address with NetworkManager

On each **Rocky VM**, use branch B's inventory. This path creates `beginner-lab-static` on each guest. It must be a new name; if that name already exists, inspect the previous attempt instead of adding a duplicate.

Keep compatible older profiles as recovery options. For predictable reboot selection, disable autoconnect **only for profiles exclusively bound to the lab NIC**, recording each original value first:

```bash
OLD_LAB_UUID='REPLACE_WITH_CONFIRMED_LAB_PROFILE_UUID'
nmcli -f connection connection show uuid "$OLD_LAB_UUID"
sudo nmcli connection modify uuid "$OLD_LAB_UUID" connection.autoconnect no
```

Skip this block if there is no old lab profile. Repeat for any other lab-only candidates; leave the current activation alone for now. If a candidate is unbound/shared or its ownership is uncertain, resolve that ambiguity before proceeding. `DEVICE=--` only means inactive, not harmless.

Create the new profile; this block first **saves it without autoactivation**:

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
LAB_MAC='REPLACE_WITH_LAB_MAC'
LAB_CIDR='192.0.2.10/24'
sudo nmcli connection add type ethernet con-name beginner-lab-static \
  ifname "$LAB_IF" 802-3-ethernet.mac-address "$LAB_MAC" \
  connection.autoconnect no \
  ipv4.method manual ipv4.addresses "$LAB_CIDR" \
  ipv4.gateway "" ipv4.dns "" ipv4.never-default yes \
  ipv6.method disabled
nmcli -f connection,802-3-ethernet,ipv4,ipv6 connection show id beginner-lab-static
```

Use `.20/24` on the server. `manual` requires an address/prefix. The interface and MAC bindings restrict which device can use this profile; `mac-address` matches the permanent MAC rather than changing it. Empty gateway/DNS and `never-default yes` keep it local. IPv6 is disabled only in this lab profile. `connection add` saves persistently by default; **saved does not yet mean active**.

Record the new UUID from the output. Activate this exact profile, then inspect runtime state:

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
LAB_UUID='REPLACE_WITH_NEW_LAB_PROFILE_UUID'
sudo nmcli --wait 30 connection up uuid "$LAB_UUID" ifname "$LAB_IF"
nmcli -f GENERAL,IP4,IP6 device show "$LAB_IF"
ip -4 route show
```

Activation can replace the previous active profile on this NIC. Expect the intended address, connected subnet route and no lab gateway/DNS. Compare the management route with the initial inventory. Inspect `journalctl -u NetworkManager -b -n 50 --no-pager` if activation fails. A timeout does not prove the saved profile disappeared.

After successful observations, enable activation on subsequent boots:

```bash
LAB_UUID='REPLACE_WITH_NEW_LAB_PROFILE_UUID'
sudo nmcli connection modify uuid "$LAB_UUID" connection.autoconnect yes
nmcli -f connection.id,connection.uuid,connection.autoconnect connection show uuid "$LAB_UUID"
```

### The same profile in nmtui

If `nmtui` is already available, open the **existing dedicated profile**:

```bash
sudo nmtui edit beginner-lab-static
```

Use Tab to move, arrow keys to choose, Space to toggle and Enter to accept. Check profile name/device, set IPv4 to **Manual**, expand it, and verify the single `.10/24` or `.20/24` address. Keep Gateway, DNS servers and search domains empty; select **Never use this network for default route** in Routes where offered. Keep IPv6 **Disabled** and automatic connection enabled after validation.

Choose **Cancel** for inspection only or **OK** to save intended edits. Saving changes the same NetworkManager profile as `nmcli`; it is not a separate configuration layer. After saving, inspect with `nmcli connection show`, then activate the recorded UUID using the previous block. Menus vary by package version; if a property is absent, set it with `nmcli` and verify. Do not use a general deactivate/reactivate action on the management connection.

### NetworkManager recovery and rollback

From the **console**, inspect the recorded new UUID, then remove only your profile. If creation never succeeded, skip this new-profile block and still restore any previous autoconnect values you changed:

```bash
LAB_UUID='REPLACE_WITH_NEW_LAB_PROFILE_UUID'
nmcli -f connection,ipv4 connection show uuid "$LAB_UUID"
sudo nmcli connection modify uuid "$LAB_UUID" connection.autoconnect no
sudo nmcli connection down uuid "$LAB_UUID"
sudo nmcli connection delete uuid "$LAB_UUID"
```

An “already inactive” result from `down` is acceptable after you have verified the UUID; an unrelated error requires investigation. Other compatible profiles may autoactivate when a connection goes down, so inspect the device again.

If an older lab profile existed, restore every autoconnect value you recorded. Reactivate it **only if it was active before the lesson**:

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
OLD_LAB_UUID='REPLACE_WITH_PREVIOUS_LAB_PROFILE_UUID'
OLD_AUTOCONNECT='yes'
sudo nmcli connection modify uuid "$OLD_LAB_UUID" connection.autoconnect "$OLD_AUTOCONNECT"
sudo nmcli --wait 30 connection up uuid "$OLD_LAB_UUID" ifname "$LAB_IF"
```

Use the recorded `yes` or `no`, not a guessed value. If the previous profile was inactive, omit the `up` line. If no previous profile existed, no old profile needs restoring: verify that the lesson address is gone. Return the lab link's original up/down state if necessary, and compare management addressing/routes/DNS with the initial record. Do not delete all Ethernet profiles or restart networking globally.

## 3. DHCP, gateways and DNS: when the settings belong

Static addressing assigns the administrator's chosen address. DHCP requests a lease from an actual DHCP server, which may also supply routes and DNS. Enabling DHCP on the internal course network will not produce a lease. A DNS server answers name questions; a gateway forwards packets beyond an on-link network. One device may provide both services, but neither role follows just from its IP ending in `.1`.

The following are **optional adaptation examples, not changes to the two-VM course lab**. Use a separate disposable practice VM/interface identified by its hypervisor MAC, with console access, no conflicting owner, and an existing DHCP-enabled virtual network or an administrator-specified routed network. Never substitute either course VM's management NIC.

### DHCP on a network that actually provides it

For a spare **networkd-owned NIC** on a DHCP-enabled practice network, a complete Netplan definition is:

```yaml
network:
  version: 2
  ethernets:
    practice-dhcp:
      renderer: networkd
      match:
        macaddress: "02:00:00:00:00:30"
      dhcp4: true
      dhcp4-overrides:
        use-routes: false
        use-dns: false
        use-domains: false
      dhcp6: false
      accept-ra: false
      link-local: []
      optional: true
```

Replace the example MAC with the spare NIC's MAC. These overrides request an address while declining DHCP routes, DNS and search domains, preserving the practice VM's existing management path. It still gets the connected subnet route. On an intentionally selected primary uplink, an administrator may instead accept DHCP routes and DNS; this course does not change an existing uplink.

Use the same new-file/backup procedure with a distinct file such as `90-beginner-dhcp.yaml`, mode 600, `generate`, merged-output inspection and `try`. Check `networkctl status` and `ip address` for a lease. If none arrives, inspect carrier, the virtual-network selection and DHCP service/scope availability. Remove only this new file and apply the restored configuration to undo it; check for residual lab addresses as in branch A.

For an otherwise unconfigured **NetworkManager-owned spare NIC**, the equivalent saved profile is:

```bash
PRACTICE_IF='REPLACE_WITH_SPARE_NIC'
PRACTICE_MAC='REPLACE_WITH_SPARE_MAC'
sudo nmcli connection add type ethernet con-name beginner-practice-dhcp \
  ifname "$PRACTICE_IF" 802-3-ethernet.mac-address "$PRACTICE_MAC" \
  connection.autoconnect no ipv4.method auto \
  ipv4.never-default yes ipv4.ignore-auto-routes yes ipv4.ignore-auto-dns yes \
  ipv6.method disabled
sudo nmcli --wait 60 connection up id beginner-practice-dhcp ifname "$PRACTICE_IF"
nmcli -f GENERAL,IP4,DHCP4 device show "$PRACTICE_IF"
```

The name must be unused. Record its UUID and use branch B's UUID-based rollback to delete only this new profile. Because this example is `autoconnect no`, the settings are saved but activation is manual after a reboot. If adapting an existing **dedicated practice profile** from static to DHCP, set `ipv4.method auto` and clear `ipv4.addresses`, `ipv4.gateway`, `ipv4.routes`, `ipv4.dns` and `ipv4.dns-search` in the same `connection modify` operation; otherwise old static values can coexist with DHCP. Record the old values first and restore them to undo that adaptation.

### Durable gateway and DNS settings on a routed practice network

Suppose a **separate practice VM**, not either course VM, has an administrator-assigned `10.77.0.10/24`, a real on-link router `10.77.0.1`, and a reachable resolver `10.77.0.53` serving `training.example`. Its exercise NIC must be the explicitly chosen default uplink, with **no competing management default route**; use the hypervisor console. The administrator must ensure these sample values describe that practice network before you use them.

For Netplan/networkd, the complete definition would be:

```yaml
network:
  version: 2
  ethernets:
    practice-uplink:
      renderer: networkd
      match:
        macaddress: "02:00:00:00:00:40"
      dhcp4: false
      dhcp6: false
      accept-ra: false
      link-local: []
      addresses:
        - 10.77.0.10/24
      routes:
        - to: default
          via: 10.77.0.1
      nameservers:
        addresses:
          - 10.77.0.53
        search:
          - training.example
```

`to: default` supplies a route for destinations without a more specific match. `via` is the router's on-link address. `nameservers.addresses` selects the resolver; `search` can expand a short name such as `web` to `web.training.example`. It does not create DNS records. Use a separately backed-up, owned file, replace the MAC, and repeat branch A's permission/validation/trial/recovery process.

With NetworkManager, on the equivalent fresh, owned practice NIC:

```bash
PRACTICE_IF='REPLACE_WITH_PRACTICE_UPLINK'
PRACTICE_MAC='REPLACE_WITH_PRACTICE_MAC'
sudo nmcli connection add type ethernet con-name beginner-practice-routed \
  ifname "$PRACTICE_IF" 802-3-ethernet.mac-address "$PRACTICE_MAC" \
  connection.autoconnect no \
  ipv4.method manual ipv4.addresses 10.77.0.10/24 \
  ipv4.gateway 10.77.0.1 ipv4.never-default no \
  ipv4.dns 10.77.0.53 ipv4.dns-search training.example \
  ipv6.method disabled
sudo nmcli --wait 30 connection up id beginner-practice-routed ifname "$PRACTICE_IF"
nmcli -f GENERAL,IP4 device show "$PRACTICE_IF"
```

Inspect the new profile before activation, record its UUID, and enable autoconnect only after successful checks if boot activation is wanted. Remove it by UUID to roll back as in branch B. For either backend, verify `ip route get 10.77.0.53`, the default route, and an administrator-provided DNS record. Inspect `resolvectl status` where resolved is active, or NetworkManager's active DNS and `/etc/resolv.conf` otherwise. Do not hand-edit a generated `resolv.conf` or treat a temporary `resolvectl dns` command as a durable profile change.

## 4. Verify the course lab after a reboot

Return to the two course VMs' static configuration. Save your work, then reboot each **disposable guest** from its console with `sudo reboot`. After login, rematch the NIC MACs; shell variables do not survive reboot.

On the **client**:

```bash
LAB_IF='REPLACE_WITH_CLIENT_LAB_NIC'
ip -4 address show dev "$LAB_IF"
ip -4 route get 192.0.2.20
ip -4 route show default
ping -n -c 3 -W 2 192.0.2.20
```

On the **server**, inspect `.20/24` and run `ip -4 route get 192.0.2.10` plus `ping -n -c 3 -W 2 192.0.2.10`. Route lookup should select the lab NIC and local lab source address, without `via`. The management default route can still exist and should match the original configuration. DHCP lease details can legitimately renew.

| Observation | First investigation |
|---|---|
| Address absent after reboot | Wrong MAC, unsaved file/profile, disabled autoconnect, or competing owner |
| Extra lab address/DNS/default route | Merged YAML lists, another matching definition/profile, or leftover temporary state |
| `NO-CARRIER` | Hypervisor cable/adapter state and internal-network attachment |
| Correct route, no ping reply | Peer address, same internal network, neighbor discovery and ICMP policy; continue to chapter 04 |
| Management access changed | Use the console and the relevant rollback; do not flush routes |

## Completion check

- Identify the lab and management NICs from MAC evidence on both VMs.
- Explain which file/profile owns the lab NIC and distinguish saved from active state.
- Verify `.10/24` and `.20/24` survive reboot with an on-link peer route.
- Show that the lab NIC added no gateway/DNS and management configuration is preserved.
- Record peer-ping results and investigate failures rather than inventing a gateway.
- Identify the exact new file/profile to undo and the previous state to restore.
- Explain why the optional DHCP/routed examples require a different prepared network.

Leave the working static lab addresses in place for the next lesson. Keep backup notes until the course is complete.

## Primary sources and further reading

- [Ubuntu Server: configuring networks](https://documentation.ubuntu.com/server/explanation/networking/configuring-networks/)
- [Netplan examples](https://netplan.readthedocs.io/en/stable/examples/), [YAML reference](https://netplan.readthedocs.io/en/stable/netplan-yaml/), [file permissions](https://netplan.readthedocs.io/en/stable/security/)
- [Netplan generate and merging](https://netplan.readthedocs.io/en/stable/netplan-generate/), [Netplan try and recovery caveats](https://netplan.readthedocs.io/en/stable/netplan-try/)
- [NetworkManager nmcli examples](https://www.networkmanager.dev/docs/api/latest/nmcli-examples.html), [nmcli manual](https://www.networkmanager.dev/docs/api/latest/nmcli.html), [profile properties](https://www.networkmanager.dev/docs/api/latest/nm-settings-nmcli.html), [nmtui](https://www.networkmanager.dev/docs/api/latest/nmtui.html)
- [Rocky Linux 9 network configuration](https://docs.rockylinux.org/9/guides/network/basic_network_configuration/)

[Previous: addressing and interfaces](02-addressing-interfaces.md) · [Quiz](../../quizzes/networking/beginner/03-persistent-configuration-quiz.md) · [Next: DNS and connectivity](04-dns-connectivity.md)

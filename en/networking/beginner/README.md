# Linux Networking from the Beginning

> **Learning baseline**: Ubuntu Server 24.04 LTS, with an alternate Rocky Linux 9 path
>
> **Last Updated**: September 15, 2026

This course starts at your first terminal. Create files and install programs, then configure IP and DNS, connect with SSH, apply firewall rules, and observe packets. Finish by diagnosing a small web service and connecting what you learned to Docker, Kubernetes, and cloud networking.

You do not need to memorize every command. The goal is to explain **which machine you are changing, what demonstrates success, and how to restore the previous state**.

## Course map {#course-map}

Start at lesson 1 if you are new. Experienced Linux users still need the shared lab environment and interface identification in lesson 2. Times are planning estimates including individual practice; actual time depends on experience.

| Order | Lesson | What you will be able to do | Estimated time |
|---|---|---|---|
| 1 | [Linux and the CLI](01-linux-cli.md) · [Quiz](../../quizzes/networking/beginner/01-linux-cli-quiz.md) | Identify a distribution and work with files, editors, packages and services | 2–3 hours |
| 2 | [Addresses and interfaces](02-addressing-interfaces.md) · [Quiz](../../quizzes/networking/beginner/02-addressing-interfaces-quiz.md) | Distinguish IP, subnet, gateway and DNS roles and identify a NIC | 2–3 hours |
| 3 | [Persistent network configuration](03-persistent-configuration.md) · [Quiz](../../quizzes/networking/beginner/03-persistent-configuration-quiz.md) | Configure Netplan or NetworkManager and verify reboot/recovery behavior | 3–4 hours |
| 4 | [DNS and connectivity](04-dns-connectivity.md) · [Quiz](../../quizzes/networking/beginner/04-dns-connectivity-quiz.md) | Investigate names, routes, ports and HTTP separately | 2–3 hours |
| 5 | [Remote access with SSH](05-ssh-access.md) · [Quiz](../../quizzes/networking/beginner/05-ssh-access-quiz.md) | Verify host keys, sign in with a user key and check effective settings | 2–3 hours |
| 6 | [Firewalls and host security](06-firewalls-host-security.md) · [Quiz](../../quizzes/networking/beginner/06-firewalls-host-security-quiz.md) | Allow required traffic and explain SELinux and Fail2ban | 3–4 hours |
| 7 | [Monitoring and performance](07-monitoring-performance.md) · [Quiz](../../quizzes/networking/beginner/07-monitoring-performance-quiz.md) | Observe sockets, packets and traffic and explain measurement limits | 2–3 hours |
| 8 | [Capstone and cloud connections](08-container-cloud-capstone.md) · [Quiz](../../quizzes/networking/beginner/08-container-cloud-capstone-quiz.md) | Reproduce, isolate and recover from small failures and choose a next step | 3–4 hours |

Meet each lesson's completion criteria and explain its quiz answers in your own words before continuing. After learning package operations in lesson 1, return to [guest tool preparation](#guest-tools) before lessons 2–4. Kernel tuning and CNI implementation comparisons come after the core exercises.

## Prepare the lab VMs {#lab-environment}

### Start with one VM

1. Use a virtualization application supported on your PC. Match the OS image to its supported virtual CPU architecture. For example, Arm machines need an Arm image supported by that virtualization tool.
2. Select a **24.04 LTS** image from the [official Ubuntu Server downloads](https://ubuntu.com/download/server). If you use another version, recheck package and service defaults. Follow the [installation guide](https://documentation.ubuntu.com/server/tutorial/basic-installation/) and create a regular user with a password. Examples use `student`; substitute your own username.
3. A starting allocation is 2 vCPUs, 2 GiB memory and 20 GiB disk per VM. This is a lab planning suggestion, not a performance guarantee or a minimum specification for every hypervisor.
4. Attach the first NIC to the hypervisor's **NAT network with DHCP**. It provides installation and package-download connectivity and stays unchanged in subsequent exercises.
5. Sign in through the hypervisor's **console window**. SSH is not needed yet. Shut the guest down normally and take a snapshot of the clean installation.

Lesson 1 needs only one VM. A regular container does not substitute for a complete VM's systemd and network managers. WSL can support shell practice, but its later network/firewall environment must not be assumed identical.

### Prepare two VMs for lesson 2 onward

Using Ubuntu on both guests lets you focus on one distribution. Rocky Linux 9 is an alternate path. Use [official Rocky images](https://rockylinux.org/download) and [documentation](https://docs.rockylinux.org/); you do not need to learn both distributions simultaneously.

1. Install the second VM independently and identify the guests as `net-client` and `net-server`. A simple clone can duplicate machine identifiers and SSH host keys, so use separate installations initially.
2. Shut down both guests normally and add a **second NIC** to each.
3. Attach both second NICs to the same **internal virtual network**, for example `linux-net-lab`. Do not connect a DHCP server or external uplink to that network. “Bridged”, “NAT” and “host-only” settings are not interchangeable: check what the selected mode actually connects.
4. Record each NIC's MAC address in the hypervisor settings. Start the guests and match those addresses to `ip -br link` in lesson 2. Names such as `eth1`, `enp0s8` and `ens19` vary; do not copy an interface name blindly.
5. Configure IP addresses in lessons 2 and 3. Do not add an arbitrary gateway or DNS server to the second NIC in the installer.

| Item | Client VM | Server VM |
|---|---|---|
| Role | Sends SSH and curl requests | Receives SSH and HTTP requests |
| Management NIC | Retain existing NAT/DHCP setup | Retain existing NAT/DHCP setup |
| Lab NIC | `192.0.2.10/24` | `192.0.2.20/24` |
| Lab NIC gateway/DNS | None | None |
| Recovery access | Hypervisor console and snapshot | Hypervisor console and snapshot |

```text
Client lab NIC                       Server lab NIC
192.0.2.10/24 ── internal virtual network ── 192.0.2.20/24
      |                                       |
Separate NAT/DHCP management NIC     Separate NAT/DHCP management NIC
```

`192.0.2.0/24` is a documentation range used here only on the isolated local network, not as a publicly routed network design. The management NICs still connect the guests to another network, so this does not make the whole VM an air gap.

## Prepare guest tools after lesson 1 {#guest-tools}

First learn the [lesson-1 package workflow](01-linux-cli.md), then complete this checkpoint **inside each disposable guest before lessons 2–4**. Use its existing NAT/DHCP management connection for repositories; do not give the internal lab NIC an uplink, gateway, or DNS server. A minimal image may omit diagnostic tools even when its network works.

### Identify missing commands and their packages

**Each guest, normal user; inspect only:**

```bash
hostname
cat /etc/os-release
command -v ip ss ping getent grep timeout dig tracepath traceroute python3 curl nc ncat
```

A printed executable path means the command is available. For an unclear result, query one name, for example `command -v dig`. No path/nonzero status for a missing alternative is normal. Record missing commands needed for **that guest's selected exercises**, not every absent name.

| Command / use | Ubuntu Server 24.04 package | Rocky Linux 9 package | Needed where |
|---|---|---|---|
| `ip`, `ss`: interfaces, routes, sockets | `iproute2` | `iproute` | Both guests |
| `ping`: bounded ICMP checks | `iputils-ping` | `iputils` | Both guests |
| `dig`: DNS protocol queries | `bind9-dnsutils` | `bind-utils` | Client in lesson 4 |
| `tracepath`: default trace choice | `iputils-tracepath` | `iputils` | Client; choose this or the next row |
| Linux `traceroute`: alternative trace choice | `traceroute` | `traceroute` | Client, only if selecting this alternative |
| `python3`: temporary HTTP server | `python3` (pulls in the interpreter packages) | `python3` | Server |
| `curl`: HTTP requests | `curl` | Existing `curl-minimal` **or** `curl` provider | Client and server self-checks |
| OpenBSD `nc` / Ncat `ncat`: TCP probe | `netcat-openbsd` → use `nc` | `nmap-ncat` → use `ncat` | Client |

This checkpoint chooses **`tracepath` by default**; an already installed Linux `traceroute` can be used instead with lesson 4's corresponding commands. Do not require both. On Rocky, `iputils` supplies both `ping` and `tracepath`. Use the indicated netcat implementation: similar command names do not guarantee identical options.

`getent`, `grep`, `timeout`, sudo, and the editor belong to the guest/lesson-1 baseline. If those checks fail, resolve that baseline first. Do not install a second network manager or resolver to satisfy this table. On an **already NetworkManager-managed Rocky guest**, optional `nmtui` is supplied by `NetworkManager-tui`; inspect/install it through the same selected-package workflow only if you choose that interface. A networkd guest does not need it.

### Preview and install only selected missing tooling

Before a first installation, take a guest snapshot `before-guest-tools` and record installed package/provider state. Use **only your distribution's branch** below. Each example assumes **`dig` was missing**. If it is already available, skip that installation. For a different missing selected command, replace `TOOL_PACKAGE` with its one package from the table and repeat the candidate/transaction checks; do not paste the whole matrix into an install command.

**Ubuntu guest, normal user; sudo only on marked lines:**

```bash
TOOL_PACKAGE=bind9-dnsutils
dpkg-query -W "$TOOL_PACKAGE"
sudo apt update
apt-cache policy "$TOOL_PACKAGE"
sudo apt-get --simulate install "$TOOL_PACKAGE"
```

“No packages found” in the local query is expected for an absent package. After a successful repository-index refresh, inspect the `Candidate` version and simulated dependencies, upgrades, and removals. No candidate or repository errors mean stop and check the configured Ubuntu repositories/management path. If a package is already installed but its command is missing, investigate its files and command search path rather than installing a conflicting provider.

Only when that **selected command is absent** and the preview contains the intended package/dependencies, install on the **Ubuntu guest**:

```bash
sudo apt install "$TOOL_PACKAGE"
```

Review the real prompt too; metadata can change between preview and installation. Do not automatically confirm unexpected upgrades/removals.

**Rocky guest, normal user:** check the curl provider separately before selecting any package.

```bash
command -v curl
rpm -q curl curl-minimal
```

One of the package queries may report “not installed”; that is normal. If `curl` already works, **keep whichever provider owns it** and do not request the other package. You can identify the owner with `rpm -qf "$(command -v curl)"` after the availability check succeeds. For these HTTP exercises, existing `curl-minimal` is sufficient. `curl` and `curl-minimal` conflict; do not use `--allowerasing` or a package swap to follow this course.

If `curl` is absent and **neither provider is installed**, select `curl-minimal` through the workflow below. If a provider is installed but the command cannot be found, inspect its files/PATH instead of replacing it.

**Rocky guest, normal user; example only for a missing `dig`:**

```bash
TOOL_PACKAGE=bind-utils
rpm -q "$TOOL_PACKAGE"
dnf info "$TOOL_PACKAGE"
sudo dnf --assumeno install "$TOOL_PACKAGE"
```

Check the available package, architecture, repository, and proposed dependencies/removals. `--assumeno` declines the transaction without installing; a nonzero status for the declined transaction is not a failed network probe. No candidate means investigate the configured Rocky 9 repositories. The mandatory table does not require EPEL. Then, **only for the selected missing command**, install on the **Rocky guest**:

```bash
sudo dnf install "$TOOL_PACKAGE"
```

Review the final transaction before confirming. Preserve installed curl providers and the existing network manager. Package candidates/versions are guest observations, not values guaranteed by this document.

### Recheck commands and keep a recovery record

**Both guests, normal user:** `command -v ip ss ping getent grep timeout` must find the baseline tools. For this checkpoint's default selections, check the following on the indicated guest:

```bash
# Client, either distribution; substitute traceroute only if you selected it:
command -v dig tracepath curl
```

```bash
# Ubuntu client only:
command -v nc
```

```bash
# Rocky client only:
command -v ncat
```

```bash
# Server, either distribution:
command -v python3 curl
python3 --version
```

Expect paths for your selected tools and Python 3.9 or later. Record which packages you added; these checks establish availability, not successful network communication. Return here if lesson 4 finds a missing required tool.

Keep the tools for later lessons. Removing named packages is not an exact reversal of dependencies, configuration, caches, or logs; never remove a pre-existing provider or run broad autoremove as cleanup. For a complete rollback of this preparation, restore `before-guest-tools` after dependent exercises are finished, understanding that the snapshot also discards later guest work.

Package mappings checked against primary distribution sources on September 15, 2026: Ubuntu Noble file lists for [iproute2](https://packages.ubuntu.com/noble/amd64/iproute2/filelist), [ping](https://packages.ubuntu.com/noble/amd64/iputils-ping/filelist), [dig](https://packages.ubuntu.com/noble/amd64/bind9-dnsutils/filelist), [tracepath](https://packages.ubuntu.com/noble/amd64/iputils-tracepath/filelist), [traceroute](https://packages.ubuntu.com/noble/amd64/traceroute/filelist), [netcat](https://packages.ubuntu.com/noble/amd64/netcat-openbsd/filelist), [curl](https://packages.ubuntu.com/noble/amd64/curl/filelist), and [Python package dependencies](https://packages.ubuntu.com/noble/python3); Rocky 9 package specifications for [iproute](https://git.rockylinux.org/staging/rpms/iproute/-/blob/r9/SPECS/iproute.spec), [iputils](https://git.rockylinux.org/staging/rpms/iputils/-/blob/r9/SPECS/iputils.spec), [BIND utilities](https://git.rockylinux.org/staging/rpms/bind/-/blob/r9/SPECS/bind.spec), [Ncat](https://git.rockylinux.org/staging/rpms/nmap/-/blob/r9/SPECS/nmap.spec), and [curl providers](https://git.rockylinux.org/staging/rpms/curl/-/blob/r9/SPECS/curl.spec). Live guest queries select the appropriate architecture/version; an example x86_64 file listing is not a requirement to use that architecture.

## Reading the commands {#command-conventions}

- **Client**, **server** and **both** identify where to run a command. Check the hostname first.
- Command blocks omit `$` and `#` prompts. `sudo` requests administrator privileges for that command.
- Uppercase names such as `LAB_IF` are variables in the current shell. Set them again in a new terminal, after identifying the real NIC as instructed.
- YAML and INI blocks are configuration-file contents, not commands to paste into the shell.
- “Illustrative output” does not guarantee the result of your run. Compare addresses, interfaces, counters and times with your own environment.
- Record the previous state and configuration before changing it. Change one thing at a time and use the lesson's recovery procedure when a check fails.

These exercises run on your disposable VMs. They do not ask you to change the network or firewall of your reading device or a remote production server.

## Starter glossary {#starter-glossary}

| Term | Initial meaning |
|---|---|
| Kernel / user space | The core that manages hardware and resources / the shells and programs above it |
| NIC / interface | A communication device / the OS name and settings used to operate it |
| MAC / IP | An address for frame delivery on a link / an address used to deliver packets across networks |
| Subnet / prefix | An address range sharing leading bits / the length of those bits |
| Gateway / route | The next router to forward to / a forwarding rule selected for a destination |
| DHCP / DNS | Leases network configuration / looks up information associated with a name |
| TCP / UDP / port | Two transport protocols / a number identifying a communication endpoint on a host |
| HTTP / SSH | Web request/response protocol / authenticated, encrypted remote-access protocol |
| Socket / listener | A program's communication endpoint / a socket waiting for new connections |
| Firewall / SELinux | Traffic rules / policy controlling processes' access to resources |
| NAT / CNI | Address translation / an interface and implementation ecosystem for container network setup |

## Completion criteria {#completion}

Completion should mean more than “the command ran”.

- Explain your distribution and package manager, and edit a file.
- Distinguish lab and management NICs and locate the owners of IP, route and DNS settings.
- Verify SSH host identity, key login, effective configuration and recovery.
- Allow the lab service only to its intended client and undo the rules you added.
- Distinguish DNS failure, TCP connection failure and HTTP errors using observations.
- Combine socket, packet and application evidence in a [capstone report](08-container-cloud-capstone.md#capstone-report).

Continue with [protocol details](../../basics/06-network-fundamentals-part1.md), [kernel packet paths](../../kernel/02-network-stack.md), [deeper Linux diagnostics](../07-linux-network-diagnostics.md), and the [Kubernetes Service lab](../../labs/core/03-services-networking-lab.md). Installing a CNI product need not be your first step.

## Using external courses {#further-study}

External courses are optional. [Bootlin's Linux networking course](https://bootlin.com/training/networking/) can support later kernel networking study; the [Linux Foundation networking catalog](https://training.linuxfoundation.org/networking/) helps you find a specialist continuation. Check scope, prices and schedules with the provider.

When reading CentOS 7 material or older `ifconfig`-based lessons, separate the concepts from the execution environment. This course uses `ip`, `ss`, and the distributions identified above.

**Start:** [Lesson 1 — Linux and the CLI](01-linux-cli.md)

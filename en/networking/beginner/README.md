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

Meet each lesson's completion criteria and explain its quiz answers in your own words before continuing. Kernel tuning and CNI implementation comparisons come after the core exercises.

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

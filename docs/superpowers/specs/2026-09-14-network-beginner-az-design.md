# Linux networking from first terminal to cloud

## Problem and audience

The existing network material assumes command-line fluency and jumps from protocol summaries to kernel/CNI details. A reader new to Linux cannot yet follow a continuous path through interface configuration, DNS, SSH, host firewalls, mandatory access control and troubleshooting. The user explicitly requests an A–Z beginner path covering these foundations before optional expert topics.

## Structure

Add `ko/networking/beginner/` and `en/networking/beginner/` with a course README and eight lessons. Each lesson has a mirrored quiz under `quizzes/networking/beginner/`. The README provides lab preparation, a glossary, prerequisite and outcome maps, estimated study time, and completion criteria. Preserve the existing deeper documents and link to them at the appropriate stage.

1. `01-linux-cli.md`: kernel, libraries, distributions, terminal, files, editors, permissions, package managers, processes and service logs.
2. `02-addressing-interfaces.md`: frames/packets/ports, IPv4/CIDR, IPv6 awareness, DHCP, gateways, MAC/ARP, modern `ip` commands and temporary configuration.
3. `03-persistent-configuration.md`: renderer ownership, Netplan/networkd and NetworkManager/nmcli/nmtui, static and dynamic addressing, routes, DNS, validation and rollback.
4. `04-dns-connectivity.md`: resolver versus routing failures, `getent`, `dig`, `ping`, `traceroute`/`tracepath`, TCP/HTTP tests and an evidence-led decision tree.
5. `05-ssh-access.md`: server setup, host identity, key generation and installation, permissions, second-session testing, configuration precedence and safe password-login hardening.
6. `06-firewalls-host-security.md`: inbound/outbound/forwarding distinction, mutually exclusive UFW/firewalld paths, runtime/persistent state, SELinux modes and labels, limited Fail2ban exercise and recovery.
7. `07-monitoring-performance.md`: socket state/queues, `ss`, legacy netstat, bounded `tcpdump`/`iftop`, latency/throughput/loss, kernel/I/O study, measurement before tuning.
8. `08-container-cloud-capstone.md`: diagnose a small HTTP service, controlled reversible faults, report/rubric, Docker bridge/overlay, Kubernetes CNI/Service/DNS, AWS boundaries and specialist next steps.

## Shared lab contract

- Documentation-only changes; never reconfigure this repository host or create cloud resources.
- Primary teaching baseline is Ubuntu Server 24.04 LTS; the alternate host administration path is Rocky Linux 9. Debian is explained as part of the distribution family without claiming every Ubuntu renderer/service default applies to it.
- Start with a disposable local VM and hypervisor console. Later two-VM exercises use a client at `192.0.2.10/24` and a server at `192.0.2.20/24` on a dedicated internal virtual network with no DHCP server or uplink. Retain the separate existing NAT/DHCP management NIC. These documentation addresses are only for the isolated lab.
- A user records NIC MAC addresses in the hypervisor and maps them to `ip -br link`; the lab NIC has no default gateway or DNS. Never substitute the management interface. Do not assume real interface names.
- Both guests may use Ubuntu; Rocky is an alternative, not a requirement to learn two operating systems at once.
- Explain execution location and privileges, expected observations, how to interpret failure, and cleanup/rollback for each mutation. Start each lesson with its own prerequisites; shell variables do not implicitly persist between sessions.
- Never flush routes/firewalls, disable SELinux globally, blindly overwrite renderer configuration, enable competing firewall managers, or disable SSH password access before verified key access and console recovery.
- Host firewall access examples are limited to the lab interface/client. Keep shell commands separate from YAML/INI examples and mark illustrative output.
- No copied course/video transcript; authoritative project and distribution documentation grounds operational details. User-provided courses may appear only as optional further study with explicit scope, not as prerequisites.

## Integration and acceptance

Put the beginner entry first in the Networking sections of both SUMMARY and README files. Add all lessons and quizzes to SUMMARY, and link from the networking overview, existing Linux basics, and existing Linux diagnostics. Existing paths continue to work. Do not hand-edit `cn/`, `jp/`, or `es/`.

Each lesson must include explicit learning outcomes, practical steps, a completion check, further reading, and a quiz with explanations. Topics listed by the user must map to concrete lessons, not just a list of external links. Content reviewers must check beginner usability, technical accuracy, both language versions, command safety and full changed-file coverage. Content quality must score at least 85/100 before deployment.

Run repository documentation validation and existing network example tests. Verify rendered navigation and quiz interactions on desktop and mobile. Retain truthful evidence: static checks and existing reference runs are not claimed as new Ubuntu/Rocky VM experiments. Review the latest PR HEAD, resolve Critical/Major findings, require all checks, verify target/HEAD, and merge under the user's standing authorization.

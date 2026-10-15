# Beginner Networking A–Z Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide a complete Korean/English learning path from a first Linux terminal through network administration and a container/cloud handoff.

**Architecture:** A dedicated beginner subtree contains eight sequential lessons and a course landing page. Existing advanced material remains the specialist continuation; navigation and quizzes connect both tracks.

**Tech Stack:** Markdown, GitBook/VitePress, existing Node documentation validation and Python example tests.

**Spec:** `docs/superpowers/specs/2026-09-14-network-beginner-az-design.md`

## Global Constraints

- Documentation-only changes; never reconfigure this repository host or create cloud resources.
- Primary teaching baseline is Ubuntu Server 24.04 LTS; the alternate host administration path is Rocky Linux 9.
- Two-VM lab: client `192.0.2.10/24`, server `192.0.2.20/24`, dedicated internal virtual network without DHCP/uplink, separate untouched NAT/DHCP management NIC.
- Match lab NICs through recorded hypervisor MAC addresses; no default gateway or DNS on the lab NIC.
- Each lesson contains prerequisites, learning outcomes, explained commands, expected observations, completion checks and recovery for mutations.
- Korean/English topic parity is mandatory; do not edit Chinese/Japanese/Spanish mirrors.
- No new code or unit tests are necessary for this documentation change. Use existing link, image, parity and renderer checks.
- Content quality at least 85/100, full latest-HEAD review coverage, no unresolved Critical/Major findings and mandatory CI are required before merge/deployment.

## Task 1: Linux and addressing foundations

**Files:** Create `{ko,en}/networking/beginner/{01-linux-cli,02-addressing-interfaces}.md` and the four matching `quizzes/networking/beginner/*-quiz.md` files.

**Interfaces:** Consumes README lab contract; produces prerequisite knowledge for persistent network configuration. Previous/next links use the numbered filenames in the spec.

- [ ] Write beginner explanations and bounded filesystem/interface exercises covering all specified commands.
- [ ] Add at least six questions per lesson with answer explanations, including practical interpretation.
- [ ] Check commands against upstream/distribution manuals and self-review ko/en parity.

## Task 2: Network configuration and diagnosis

**Files:** Create paired lessons/quizzes for `03-persistent-configuration` and `04-dns-connectivity`.

**Interfaces:** Uses the shared two-NIC VM contract and addresses. Provides an operational server/client subnet for SSH and firewall lessons.

- [ ] Explain ownership detection, complete Netplan and NetworkManager paths, DHCP/static differences, validation and exact rollback.
- [ ] Teach DNS, routes, ICMP, TCP and HTTP diagnosis with local evidence before external probes.
- [ ] Add at least six quiz questions per lesson and cross-check commands with primary sources.

## Task 3: Remote access and host security

**Files:** Create paired lessons/quizzes for `05-ssh-access` and `06-firewalls-host-security`.

**Interfaces:** Uses the shared lab server/client addresses; chooses UFW on the Ubuntu path or firewalld/SELinux on the Rocky path.

- [ ] Provide complete key setup and host verification, second-session tests, effective-config verification and rollback.
- [ ] Provide source-scoped temporary/permanent firewall examples and narrowly scoped SELinux/Fail2ban exercises.
- [ ] Add at least six quiz questions per lesson, checking lockout and manager-precedence risks.

## Task 4: Course spine, monitoring and capstone

**Files:** Create paired beginner READMEs, `07-monitoring-performance.md`, `08-container-cloud-capstone.md` and matching quizzes. Modify both locale README/SUMMARY files, networking READMEs, `basics/01-linux-basics.md`, and `networking/07-linux-network-diagnostics.md`.

**Interfaces:** Connects all eight lessons and existing protocol/kernel/container/Kubernetes/AWS sources.

- [ ] Write environment setup, glossary, optional pacing, entry/exit criteria and topic coverage table.
- [ ] Add bounded monitoring exercises and a reversible HTTP troubleshooting capstone with grading criteria.
- [ ] Register every new lesson/quiz and place the beginner path before the Kubernetes overview.
- [ ] Validate using `npm run docs:validate` and `python3 -B -m unittest discover -s examples/networking/foundations -p 'test_*.py' -v`.

## Task 5: Review, publish and verify

**Files:** Add review/validation evidence under `docs/reviews/2026-09-14/` as appropriate.

- [ ] Run independent full content reviews of each task and whole-branch integration; resolve material findings.
- [ ] Verify rendered Korean/English navigation, heading links and quiz answer disclosure on desktop/mobile.
- [ ] Commit, push and open a PR with the final scope and truthful verification evidence.
- [ ] Review the latest HEAD and inline comments; fix/retest/repush as required.
- [ ] Require CI, verify reviewed/current HEAD and main target, merge, then confirm deployment and published pages.

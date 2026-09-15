# Quiz 6. Firewalls and host security

> **Supported Versions**: Ubuntu Server 24.04 LTS (primary), Rocky Linux 9 (alternate)
> **Last Updated**: September 15, 2026

[Lesson and primary sources](../../../networking/beginner/06-firewalls-host-security.md) | [Course](../../../networking/beginner/README.md)

Use the client `.10`, server `.20`, separate management NIC, and console recovery contract. Choose before revealing the explanation.

1. A client opens SSH to this server. Is that inbound, outbound, or forwarded traffic from the server firewall's perspective?

   - A) Forwarded, because all remote connections make the server a router.
   - B) Outbound, because the server sends a response.
   - C) Inbound for the new connection; replies belong to that conversation, while routing another host's traffic would be forwarding.
   - D) None; SSH bypasses firewalls.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Direction depends on the observation host and packet path. Our server is the destination, not a router. Stateful reply handling also explains why an old SSH connection can survive when new ones are denied. No NAT or forwarding change is needed for this lab.

</details>

2. UFW already has a broad SSH allow. Does adding an allow from `.10` alone restrict access to `.10`?

   - A) No. Existing broader allows remain; inspect ordering and earlier custom rules, then use the lesson's scoped allow followed by its same-endpoint deny.
   - B) Yes. Any newer rule automatically erases older ones.
   - C) Yes, if its comment contains “secure.”
   - D) Only if firewalld is enabled too.

<details>
<summary>Show Answer</summary>

**Answer: A**

**Explanation:** A narrow allow is additive, not a revocation. The lesson inserts separate client allows for TCP 22 and 8000 before a deny on the same lab NIC/destination/ports. This allows HTTP permission to be removed independently of SSH. Custom `before.rules` can still affect results, so inspect actual ownership and earlier processing. Two competing managers make reasoning harder rather than more secure.

</details>

3. What is true of the lesson's UFW rule changes and cleanup?

   - A) They are runtime-only and expire after ten minutes.
   - B) Deleting by an old remembered rule number is always exact.
   - C) Cleanup must disable UFW even if it was active before the lesson.
   - D) Rules are saved and applied; delete the exact successfully added rule specifications and restore inactive state only if the lesson enabled an originally inactive UFW.

<details>
<summary>Show Answer</summary>

**Answer: D**

**Explanation:** This UFW workflow does not have firewalld's per-rule permanent/runtime split. Positions can change, while interface/source/destination/protocol/ports define the intended rule. An HTTP-only fault removes just the independent TCP 8000 allow; restoring it must insert it ahead of the remaining lab deny. Do not remove the TCP 22 allow for that experiment. Initial activation also needs a management-access check: unchanged NIC configuration alone does not preserve every inbound service.

</details>

4. Why put the Rocky lab interface in a new empty firewalld zone?

   - A) A zone makes MAC addresses unnecessary.
   - B) The default or existing zone may already permit SSH broadly; a dedicated lab-only zone makes the intended accepts easier to establish without moving the management NIC.
   - C) Every zone automatically blocks all ICMP and IPv6.
   - D) Zones remove the need to inspect source bindings or policies.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** An empty NetworkManager `connection.zone` uses the default zone. Existing services, targets, source bindings, policies, and direct rules can change effective acceptance. Record the active lab profile UUID and original zone, including an empty value, and leave the management profile alone.

</details>

5. A rich rule was added with `--timeout=600`. What happens on reload?

   - A) The runtime-only rule is lost; reload uses saved policy, and the interface-to-zone binding is a separate change.
   - B) The timeout automatically becomes permanent.
   - C) All NetworkManager addresses are erased.
   - D) Nothing changes because runtime always overrides permanent.

<details>
<summary>Show Answer</summary>

**Answer: A**

**Explanation:** The trial rule expires after its timeout and is also lost on reload. A saved rule needs an explicit permanent change and loading into runtime. Reload can discard unrelated runtime changes too; do not use it casually or copy all unknown state with `--runtime-to-permanent`. Console recovery is still needed if the lab zone no longer allows new SSH.

</details>

6. The allowed client receives HTTP 200 from `.20:8000`. Which claim is supported?

   - A) Every unapproved source has been tested and denied.
   - B) There cannot be another broad allow.
   - C) This client reached this listening service during this test; source restriction still requires policy inspection and any separately performed denial tests.
   - D) SELinux permits every application to read every file.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** A successful allowed-path test has a limited scope. A server-self/localhost request is not a denied external-client test. Compare listener, route, interface/zone, and rules, and report what you actually measured. The bounded Python server and scratch file should be stopped/removed independently of the firewall policy.

</details>

7. A file has a deliberately wrong SELinux type. Which recovery fits the lesson?

   - A) Disable SELinux globally.
   - B) Grant everyone write permissions recursively.
   - C) Generate a broad allow policy for every audit record.
   - D) Compare the path's expected context, preview `restorecon -n`, restore that file's policy label, and verify with `matchpathcon -V`.

<details>
<summary>Show Answer</summary>

**Answer: D**

**Explanation:** Unix modes and SELinux contexts are independent checks. `chcon` changes a current label; it does not create a durable path mapping. `restorecon` uses the policy's file-context rules. A custom permanent path may need an intentional `semanage fcontext` mapping, but the scratch-file exercise does not.

</details>

8. `ausearch` returns no matching AVCs, and Fail2ban reports zero bans. What is a sound interpretation?

   - A) Both tools prove that attacks are impossible.
   - B) The queried records/counters are empty; filters, time range, journal metadata, permissions, and actual events determine what evidence exists.
   - C) Turn off enforcing mode until errors appear.
   - D) Run a brute-force loop to create a nonzero score.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** The label exercise does not deliberately trigger confined access, so an AVC is not promised. Fail2ban may be correctly idle or incorrectly configured. Inspect the real journal unit, backend/filter/action, and startup logs. The optional lesson explicitly does not use brute force or claim enforcement was live-tested.

</details>

9. Which optional package setup matches Rocky Linux 9?

   - A) Record existing state, enable the appropriate CRB prerequisite and EPEL 9 through distribution guidance, verify candidates/signatures, and install only needed packages.
   - B) Use any EPEL major version with signature checking disabled.
   - C) Install Ubuntu packages if DNF cannot resolve a dependency.
   - D) Disable existing CRB/EPEL after installation even when other packages rely on them.

<details>
<summary>Show Answer</summary>

**Answer: A**

**Explanation:** EPEL provides optional software while CRB supplies dependencies. The correct EL major release, repository identity, and guest architecture matter. The same preparation supports optional `iftop` in lesson 7. Disabling a repository does not undo packages; complete optional-install rollback uses the recorded snapshot.

</details>

10. Which Fail2ban setup and cleanup follow the lab boundary?

   - A) Use `backend=systemd` plus a guessed `/var/log/auth.log`, then flush every ban.
   - B) Reuse any existing production jail and stop it without inspection.
   - C) Verify a dedicated journal-backed SSH jail and lab-scoped action, inspect status, unban only listed course addresses, stop that jail, remove its two owned files, then clean up its firewall zone.
   - D) Assume the service being active proves the filter and firewall action work.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** The journal backend uses `journalmatch`, not `logpath`. The action must precede the lab allow and be limited to the lab interface/zone, `.20`, TCP 22. Test interpreted configuration and inspect action expansion. Restore exact accidental bans and stop the jail before removing its zone; never flush unrelated firewall state. Without additional evidence, report configuration/startup verification, not proven attack detection.

</details>

[Return to lesson](../../../networking/beginner/06-firewalls-host-security.md) | [Next: Monitoring](../../../networking/beginner/07-monitoring-performance.md)

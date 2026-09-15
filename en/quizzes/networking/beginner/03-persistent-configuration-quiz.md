# Persistent Network Configuration Quiz

> **Last Updated**: September 15, 2026

Use the [lesson](../../../networking/beginner/03-persistent-configuration.md) to explain the reasoning, not just the option letter. The lab has client `.10/24` and server `.20/24` on `192.0.2.0/24`, no DHCP/router/DNS on that internal network, and a separate unchanged management NIC.

## Questions

1. A VM has two interfaces with unfamiliar names. Which one should receive `192.0.2.10/24`?
   - A) The first interface listed by `ip`
   - B) The interface with the current default route
   - C) The interface whose MAC matches the hypervisor's recorded internal-lab adapter
   - D) Any interface currently marked UP

<details>
<summary>Show Answer</summary>

**Answer: C) The interface whose MAC matches the hypervisor's recorded internal-lab adapter**

**Explanation:** Interface names and listing order are not a reliable role assignment. Map the recorded MAC to `ip -br link`, then inspect addressing and routes. Preserve the separate management NIC even if it has a more familiar name.

</details>

2. `systemd-networkd` is active, but a Netplan definition selects NetworkManager for the lab NIC. What should you do?
   - A) Assume networkd owns all interfaces because its service is running
   - B) Inspect the matching Netplan definition and generated profile before choosing the owner to edit
   - C) Create a direct `.network` file for the same NIC as well
   - D) Disable both services and use only `ip address add`

<details>
<summary>Show Answer</summary>

**Answer: B) Inspect the matching Netplan definition and generated profile before choosing the owner to edit**

**Explanation:** Service state and per-device ownership are different. Netplan can generate backend configuration, and a direct competing definition can conflict with it. An `ip` command alone is a runtime change, not a durable boot instruction.

</details>

3. An earlier Netplan file already has a DNS address list for the lab NIC. A later file supplies `nameservers: {addresses: []}`. Is this a safe general way to remove the old list?
   - A) Yes; the filename with the highest number always erases every earlier value
   - B) Yes; lists always behave like scalar values
   - C) No; move all Netplan files out of the directory instead
   - D) No; inspect the merged configuration and the owning definition because lists can be concatenated

<details>
<summary>Show Answer</summary>

**Answer: D) No; inspect the merged configuration and the owning definition because lists can be concatenated**

**Explanation:** A late overlay is not a universal reset. Inspect `netplan get`, actual input files, matching IDs/MACs and any provisioning source. Edit the confirmed lab owner with a backup, or use the fresh-NIC path without an existing definition. Never replace the management configuration to solve a lab conflict.

</details>

4. Which persistent IPv4 configuration fits the course's client lab NIC?
   - A) `192.0.2.10/24`, no gateway or DNS on that NIC, DHCP disabled
   - B) `192.0.2.10/24`, gateway `192.0.2.1` because subnets always have a `.1` router
   - C) DHCP enabled and a public DNS address so a lease will appear
   - D) `192.0.2.20/24`, the same address as the server

<details>
<summary>Show Answer</summary>

**Answer: A) `192.0.2.10/24`, no gateway or DNS on that NIC, DHCP disabled**

**Explanation:** The peer is directly connected within the `/24`. No router or DHCP/DNS service exists on this internal network. A guessed gateway does not create a router, and DNS does not provide DHCP leases. The separate management connection retains its own settings.

</details>

5. `netplan generate` succeeds, then an unconfirmed `netplan try` times out. What is justified?
   - A) Syntax success proves the chosen MAC and management path are correct
   - B) Timeout guarantees both disk files and runtime state are restored
   - C) Inspect runtime and disk state from the console; use the exact-file recovery if needed
   - D) Reboot immediately without reading the files

<details>
<summary>Show Answer</summary>

**Answer: C) Inspect runtime and disk state from the console; use the exact-file recovery if needed**

**Explanation:** `generate` checks/generates configuration; it does not prove connectivity. `try` is intended to revert unconfirmed changes but has documented rollback caveats. Verify the saved configuration before rebooting, move only the owned file for rollback, and check whether the exact lab address remains in runtime state.

</details>

6. You created `beginner-lab-static` with `connection.autoconnect no`. What does this mean?
   - A) The profile disappears when nmcli exits
   - B) The profile is saved, but automatic activation is disabled; explicitly activate and verify it before enabling autoconnect
   - C) It is already active on every Ethernet NIC
   - D) It changes only the management connection

<details>
<summary>Show Answer</summary>

**Answer: B) The profile is saved, but automatic activation is disabled; explicitly activate and verify it before enabling autoconnect**

**Explanation:** Saved settings and active device state are separate. The lesson binds the profile to the verified NIC/MAC, activates its recorded UUID, checks runtime address/routes, then enables autoconnect for reboot. A saved profile alone is not proof of successful activation.

</details>

7. An older lab profile shows `DEVICE=--`. What should you do before relying on your new profile after reboot?
   - A) Delete every inactive profile
   - B) Ignore it because inactive profiles can never activate
   - C) Increase every profile's autoconnect priority
   - D) Inspect compatibility and bindings, record original state, and disable autoconnect only for confirmed lab-only competitors

<details>
<summary>Show Answer</summary>

**Answer: D) Inspect compatibility and bindings, record original state, and disable autoconnect only for confirmed lab-only competitors**

**Explanation:** Inactive describes the current state. A compatible saved profile may activate later. An unbound profile might also serve the management NIC, so do not change it blindly. Preserve previous UUIDs, autoconnect values and activation state for targeted restoration.

</details>

8. You save an edit to `beginner-lab-static` through nmtui. What should happen next?
   - A) Inspect the same NetworkManager profile with nmcli and reactivate its recorded lab UUID when appropriate
   - B) Write a second Netplan definition to make nmtui's settings persistent
   - C) Restart every network service
   - D) Deactivate the management connection to refresh all interfaces

<details>
<summary>Show Answer</summary>

**Answer: A) Inspect the same NetworkManager profile with nmcli and reactivate its recorded lab UUID when appropriate**

**Explanation:** nmtui and nmcli are interfaces to the same manager. Saving profile settings is distinct from applying them to an already active device. Limit activation to the dedicated lab profile and verify its gateway/DNS/default-route behavior.

</details>

9. Where is the lesson's example `10.77.0.1` default gateway and `10.77.0.53` resolver appropriate?
   - A) On the existing NAT/DHCP management NIC as an automatic improvement
   - B) On the isolated course NIC even though those services do not exist
   - C) On a separate prepared practice VM whose administrator confirms those services and whose practice uplink has no competing management default route
   - D) On any NIC after flushing default routes

<details>
<summary>Show Answer</summary>

**Answer: C) On a separate prepared practice VM whose administrator confirms those services and whose practice uplink has no competing management default route**

**Explanation:** Gateway and DNS examples need real, branch-specific prerequisites. Likewise, the DHCP example needs a DHCP-enabled network. They are not instructions to retrofit services onto the isolated course lab or reconfigure its management connection. A search domain expands names; it does not create records.

</details>

10. You want to undo the NetworkManager exercise. Which rollback preserves unrelated configuration?
   - A) Delete all Ethernet profiles and reboot
   - B) Verify and delete the new lab UUID, restore each previous lab profile's recorded autoconnect value, and reactivate only the previously active profile
   - C) Flush all addresses and default routes
   - D) Delete the management profile because it was created first

<details>
<summary>Show Answer</summary>

**Answer: B) Verify and delete the new lab UUID, restore each previous lab profile's recorded autoconnect value, and reactivate only the previously active profile**

**Explanation:** Recovery needs the exact owned profile and a record of the old state. A previously inactive profile should remain inactive. Inspect the resulting lab address/link state and unchanged management configuration; other compatible profiles can activate when a connection goes down.

</details>

---

[Back to the lesson](../../../networking/beginner/03-persistent-configuration.md) · [Next lesson: DNS and connectivity](../../../networking/beginner/04-dns-connectivity.md)

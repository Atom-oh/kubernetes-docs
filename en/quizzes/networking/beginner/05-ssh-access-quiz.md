# Quiz 5. Remote access with SSH

> **Supported Versions**: Ubuntu Server 24.04 LTS (primary), Rocky Linux 9 (alternate)
> **Last Updated**: September 15, 2026

[Lesson and primary sources](../../../networking/beginner/05-ssh-access.md) | [Course](../../../networking/beginner/README.md)

Choose the safest justified answer, then explain the evidence you would inspect. Commands here are interpretation exercises for the disposable VMs.

1. Ubuntu 24.04 shows an active `ssh.socket`, while a Rocky guide mentions `sshd.service`. What should you do?

   - A) Disable all sockets so both distributions look identical.
   - B) Use `sshd.service` everywhere because the executable is `sshd`.
   - C) Inspect the guest's installed units; Ubuntu uses `ssh.service` and may use socket activation, while Rocky uses `sshd.service`.
   - D) Change the SSH port before checking any listener.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Executable and service-unit names need not match. Ubuntu socket activation can own the listener, so blindly disabling it or changing bindings can break access. This lesson checks syntax, service/socket state, and TCP 22 without changing existing listen addresses.

</details>

2. On first connection, the client displays an ED25519 host fingerprint. Which comparison establishes the intended trust?

   - A) Compare the whole fingerprint against the server's public host key shown through its hypervisor console.
   - B) Compare it with the user's newly generated public key.
   - C) Accept it because the IP ends in `.20`.
   - D) Run `ssh-keyscan` over the same untrusted path and accept whatever it returns.

<details>
<summary>Show Answer</summary>

**Answer: A**

**Explanation:** Host keys identify the server; user keys authenticate a user account. A trusted console provides an independent comparison path. A scan can collect a key but not authenticate its owner. On a mismatch, investigate the VM/address and possible changed identity rather than bypassing checks.

</details>

3. Which item belongs on the server when installing your user key?

   - A) The private `id_ed25519` file and its passphrase.
   - B) The server's private host key copied into your home directory.
   - C) A screenshot of your account password.
   - D) The public `id_ed25519.pub` line, appended to the correct account's authorized keys without replacing other entries.

<details>
<summary>Show Answer</summary>

**Answer: D**

**Explanation:** The private key stays on the client and is protected by a nonempty passphrase. `ssh-copy-id -i` selects the public key to install using existing authentication. If bootstrap SSH is unavailable, append the public line through the console; do not enable passwords or transmit the private key just to copy it.

</details>

4. You already have one SSH session open. What must happen before disabling password and keyboard-interactive authentication?

   - A) Nothing; an existing connection proves future login works.
   - B) A second independent key-only connection must succeed, with connection sharing disabled; required management SSH paths must also be verified.
   - C) Delete all authorized keys except whichever is listed first.
   - D) Close the console to ensure the test is realistic.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Existing authenticated or multiplexed sessions can hide a broken new-login path. Use the explicit key, `IdentitiesOnly`, public-key-only authentication, and no shared connection. The private-key passphrase is local and remains expected. Keep the console and original session open for recovery.

</details>

5. A late drop-in says `PasswordAuthentication no`, but `sshd -T -C` still prints `yes` for the lab user. What is the correct response?

   - A) Investigate earlier values, Include order, and applicable Match blocks; do not reload expecting the filename alone to win.
   - B) Assume the printed effective result is irrelevant.
   - C) Add the same setting to ten more files.
   - D) Restart networking to force SSH to read the drop-in.

<details>
<summary>Show Answer</summary>

**Answer: A**

**Explanation:** OpenSSH's first-value behavior and connection-specific Match rules differ from “last file wins.” `-C` supplies the user, source, and local endpoint used to evaluate effective settings. A syntax check alone cannot prove the desired policy is effective. Remove only the course-created file if its intended precedence cannot be established.

</details>

6. Which statement about hardening is correct?

   - A) `PasswordAuthentication no` also always disables keyboard-interactive authentication.
   - B) `PermitRootLogin no` means sudo no longer works.
   - C) Check password, keyboard-interactive, public-key, and root-login values explicitly, preserving normal-user key access and sudo.
   - D) Turning off PAM globally is necessary for key login.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Password and keyboard-interactive methods are distinct. Direct root SSH login and a normal user's authorized sudo access are also distinct. The lesson does not disable PAM. Global authentication changes require checking all necessary management accounts/paths, not just the lab IP.

</details>

7. Reload succeeded, but a new login fails. Which recovery is appropriately scoped?

   - A) Flush the firewall and delete `/etc/ssh`.
   - B) Restore the entire old SSH directory over any newer administrator changes.
   - C) Reboot immediately and discard the console.
   - D) Use the server console to remove only the owned drop-in, validate syntax and effective baseline, reload, and retest a fresh connection.

<details>
<summary>Show Answer</summary>

**Answer: D**

**Explanation:** The owned-file approach gives an exact inverse without replacing unrelated configuration. Compare effective results for normal, root, and recorded management cases. If there were concurrent changes, reconcile them rather than blindly restoring an old directory. Existing sessions alone do not validate recovery.

</details>

8. The course public key was added to an existing `authorized_keys`. How should final cleanup handle it?

   - A) Delete `~/.ssh` recursively.
   - B) Remove only the line identified by the course comment and fingerprint, preserve other keys, restore recorded permissions, then delete the dedicated client key files after revocation.
   - C) Overwrite it with an empty file because the lesson is finished.
   - D) Delete the client's private key first and assume server authorization is automatically revoked.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Removing a client copy does not revoke a public key installed on a server. Revoke the exact server entry first and preserve unrelated changes. A directory is removed only if the lesson created it and it is empty. Package installation rollback is separate and uses the guest snapshot if complete restoration is required.

</details>

[Return to lesson](../../../networking/beginner/05-ssh-access.md) | [Next: Host security](../../../networking/beginner/06-firewalls-host-security.md)

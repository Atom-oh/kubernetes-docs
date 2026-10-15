# 5. Remote access with SSH

> **Supported Versions**: Ubuntu Server 24.04 LTS (primary), Rocky Linux 9 (alternate)
> **Last Updated**: September 15, 2026

[Previous: DNS and connectivity](04-dns-connectivity.md) | [Course](README.md) | [Quiz](../../quizzes/networking/beginner/05-ssh-access-quiz.md) | [Next: Host security](06-firewalls-host-security.md)

SSH gives you an encrypted terminal on another computer. Encryption alone is insufficient: the client must identify the server, and the server must authenticate your account. We establish those two identities separately before changing login policy.

## Prerequisites, outcomes, and recovery boundary

Complete lessons 1–4. Client `192.0.2.10/24` and server `192.0.2.20/24` use their MAC-verified internal-only NICs with no lab DHCP, gateway, or uplink. Separate NAT/DHCP management NICs remain unchanged. Use normal accounts and **keep the server's hypervisor console open throughout**. You need sudo on the server, its normal account password or console access to install a public key, and the existing management connection for package downloads.

You will install/check the SSH tools, verify a host fingerprint, create a passphrase-protected user key, install only its public part, prove a second independent key-only login, check effective server configuration, and undo your changes. All examples are illustrative, **not live-tested VM transcripts**. Every command below is for the specified guest, never the physical/documentation host. Stop at any unexpected error.

Take snapshots of both guests named `before-ssh-lesson`. Record existing SSH listeners and service/socket states before installation. A snapshot is the complete rollback for package/dependency changes; removing a package is not an exact inverse. Do not replace existing keys or configuration files to make a sample match.

## 1. Find the client and the server

The **SSH client** is the `ssh` command you run to connect. The **SSH server** is `sshd`, which waits for connections, normally TCP 22. A **host key** belongs to the server and proves its identity. A **user key** belongs to you and proves permission to use an account. A fingerprint is a short representation of a public key, suitable for comparison through a trusted channel.

**Both guests, normal user; inspect first:**

```bash
hostname
cat /etc/os-release
ip -br link
ip -4 -br address
command -v ssh
```

Match NIC MACs with the hypervisor records and confirm the role addresses. On the client, `ip -4 route get 192.0.2.20` should select the lab NIC and source `.10`; see lesson 2 for interpretation.

**Ubuntu server, normal user; record state, then install only if missing:**

```bash
dpkg-query -W openssh-server
systemctl status ssh.service ssh.socket --no-pager
```

If absent, use `sudo apt update` followed by `sudo apt install openssh-server`. Ubuntu 24.04 installations can use `ssh.socket` socket activation; `ssh.service` is still the service name. Inspect both instead of disabling the socket. This lesson keeps the existing listen addresses/port, so it does not require changing socket bindings.

**Rocky server, normal user; record state, then install only if missing:**

```bash
rpm -q openssh-server
systemctl status sshd.service --no-pager
```

If absent, use `sudo dnf install openssh-server`. On an Ubuntu client, the tools are supplied by `openssh-client`; on a Rocky client, by `openssh-clients`. If missing, install that named package using the distribution's package-manager procedure in lesson 1. Review transactions; do not add repositories for OpenSSH.

On the **server**, set one service variable after checking the distribution:

```bash
# Ubuntu server only:
SSH_UNIT=ssh.service
```

```bash
# Rocky server only:
SSH_UNIT=sshd.service
```

**Server, normal user invoking sudo where shown:**

```bash
sudo /usr/sbin/sshd -t
sudo systemctl start "$SSH_UNIT"
systemctl cat "$SSH_UNIT"
systemctl status "$SSH_UNIT" --no-pager
sudo ss -ltnp 'sport = :22'
```

`sshd -t` checks configuration and key sanity; success normally prints nothing. Do not start/reload after a validation error. `start` affects current runtime, not boot enablement. `systemctl cat` reveals the unit and overrides: this procedure assumes the normal configuration path. If custom `ExecStart`/environment options supply `-f` or `-o`, mirror those options in later validation/effective checks rather than testing a different configuration. A listener on `0.0.0.0:22`/`[::]:22` covers more than the lab address; it is not source restriction. Do not change network bindings here, because that could remove management access. Lesson 6 restricts lab traffic by source and interface.

If a firewall currently blocks the lab connection, complete **only the matching firewall branch in lesson 6** to allow `.10` to `.20` TCP 22, then return. Keep console access; do not turn off the firewall. “Connection refused” often means no listener/rejection; a timeout can indicate filtering or a path failure. Follow lesson 4's evidence sequence.

## 2. Verify the server's host key through its console

**Server hypervisor console, normal user invoking sudo:**

```bash
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Record the full `SHA256:...` fingerprint and that it is the **ED25519 host key**. This path is the public host key, not your future user key. Never print or copy `/etc/ssh/ssh_host_ed25519_key`, its private counterpart. This path assumes the normal non-FIPS guest baseline; a crypto policy that disallows Ed25519 needs an approved algorithm path, not a disabled security policy.

**Client, normal user:**

```bash
SSH_LAB_DIR=$(mktemp -d "$HOME/network-beginner-ssh.XXXXXX")
printf '%s\n' "$SSH_LAB_DIR"
read -r -p 'Normal account name on the server: ' SERVER_USER
```

Record the directory and account; stop if creation fails, the path is empty, or the account is root. This private directory holds a dedicated course key and host record, leaving existing `~/.ssh` client files alone.

**Client, normal user:**

```bash
ssh -o HostKeyAlgorithms=ssh-ed25519 \
  -o UserKnownHostsFile="$SSH_LAB_DIR/known_hosts" \
  -o StrictHostKeyChecking=ask \
  "$SERVER_USER@192.0.2.20"
```

At the first host-key prompt, compare the **entire fingerprint** with the server console. Only an exact match justifies typing `yes`. If it differs, stop and check the VM/address; do not disable host-key checking or blindly delete a saved record. `ssh-keyscan` can collect a key but cannot by itself prove who supplied it.

If password login is allowed, enter the **server account password** and check `hostname`, `whoami`, and `printf '%s\n' "$SSH_CONNECTION"` remotely, then `exit` to the client. `SSH_CONNECTION` contains client IP/port and server IP/port; expect lab `.10` and `.20`. Keep the independent hypervisor console available. If password login is already disabled, host-key verification can still finish before authentication fails; use the console installation alternative below without enabling passwords.

## 3. Create your user key and prepare server permissions

**Client, normal user, same shell:**

```bash
ssh-keygen -t ed25519 -a 64 -f "$SSH_LAB_DIR/id_ed25519" \
  -C "network-beginner-$(basename "$SSH_LAB_DIR")"
ssh-keygen -lf "$SSH_LAB_DIR/id_ed25519.pub"
ls -l "$SSH_LAB_DIR"
```

Enter a nonempty passphrase twice. It encrypts the private key on disk; it is not the server account password. `-a 64` selects the key derivation work factor. `id_ed25519` stays on the client; only `id_ed25519.pub` goes to the server. The unique directory prevents accidental replacement of an existing key. Stop rather than answering yes to an unexpected overwrite prompt.

Before installation, prepare a recovery record for the **same normal server account** used in `SERVER_USER`.

**Server console, logged in as that normal account:**

```bash
SERVER_NOTE=$(mktemp -d "$HOME/network-beginner-ssh-state.XXXXXX")
printf '%s\n' "$SERVER_NOTE"
stat -c '%a %U %n' "$HOME"
ls -ld "$HOME/.ssh" "$HOME/.ssh/authorized_keys"
```

Stop if directory creation failed or the printed path is empty. Record the new path and original home mode. “No such file” for `.ssh` or `authorized_keys` is normal on a fresh account; record which was absent. If they exist, record their numeric modes with `stat -c '%a %U %n'` and inspect ownership. If either is a symlink, has another owner, has unexpected ACLs, or is managed by another system, stop and reconcile ownership instead of changing it recursively.

If `authorized_keys` already exists, **server normal user**: `cp -p -- "$HOME/.ssh/authorized_keys" "$SERVER_NOTE/authorized_keys.before"` makes a backup in the new directory. Also record `.ssh`'s mode before changing it. Create `.ssh` only if absent with `mkdir -m 700 -- "$HOME/.ssh"`. For this account, use `chmod go-w "$HOME"` and `chmod 700 "$HOME/.ssh"`; record original modes so they can be restored. OpenSSH's strict checks reject unsafe ownership or group/world-writable paths. Do not use recursive `chmod` or move someone else's keys.

## 4. Install the public key and prove key-only access

**Client, normal user:**

```bash
ssh-copy-id -i "$SSH_LAB_DIR/id_ed25519.pub" \
  -o UserKnownHostsFile="$SSH_LAB_DIR/known_hosts" \
  -o StrictHostKeyChecking=yes \
  "$SERVER_USER@192.0.2.20"
```

`ssh-copy-id` uses an existing authentication method to append the selected public key to the server account's `~/.ssh/authorized_keys`; it does not copy your private key. Read the added-key count. It should add your one key or report it already installed. Do not use a forced mode to add duplicates.

**Console alternative when password/bootstrap SSH is unavailable:** on the client, display only `cat "$SSH_LAB_DIR/id_ed25519.pub"`. On the server console as the target user, open `nano "$HOME/.ssh/authorized_keys"` and **append that entire single public-key line**, preserving existing lines. Save, then compare `ssh-keygen -lf "$HOME/.ssh/authorized_keys"` with the client user-key fingerprint. This is not the host-key fingerprint from step 2.

**Server console, normal target user:**

```bash
chmod 600 "$HOME/.ssh/authorized_keys"
ls -ld "$HOME" "$HOME/.ssh"
ls -l "$HOME/.ssh/authorized_keys"
ssh-keygen -lf "$HOME/.ssh/authorized_keys"
```

Expect the target account as owner, private `.ssh` permissions, and the new public-key fingerprint among any existing entries. On Rocky with SELinux enforcing, also use `sudo restorecon -v "$HOME/.ssh" "$HOME/.ssh/authorized_keys"` when standard home-path labels are wrong; lesson 6 explains why Unix permissions alone are not the whole policy.

**Client console A, normal user; open and keep this session:**

```bash
ssh -i "$SSH_LAB_DIR/id_ed25519" -o IdentitiesOnly=yes \
  -o PreferredAuthentications=publickey \
  -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no \
  -o ControlMaster=no -o ControlPath=none \
  -o UserKnownHostsFile="$SSH_LAB_DIR/known_hosts" \
  -o StrictHostKeyChecking=yes "$SERVER_USER@192.0.2.20"
```

The private-key passphrase prompt is expected. A prompt for the remote account password is not part of this key-only test. `IdentitiesOnly` limits keys offered, and disabling connection sharing ensures you test a fresh authentication rather than reuse a multiplexed session.

In that **remote server session**, run `whoami` and `printf '%s\n' "$SSH_CONNECTION"` and leave it open. Now open **client console B**, set `SSH_LAB_DIR` to the recorded exact client directory and `SERVER_USER` to the same account, and repeat the **full key-only command above**. Confirm account and `.10`→`.20` connection again. Only a successful second independent login completes this gate.

If you already use SSH over the **management NIC**, repeat the key-only test for every management account/path that must remain usable before disabling server-wide password authentication. An existing session alone is insufficient. If you cannot verify a required path, keep the present authentication policy and finish preparation; the NIC's unchanged IP does not guarantee unchanged login access.

## 5. Inspect configuration precedence before hardening

**Server console, normal user invoking sudo:**

```bash
sudo cat /etc/ssh/sshd_config
sudo ls -la /etc/ssh/sshd_config.d
sudo grep -RnsE '^[[:space:]]*(Include|Match|PasswordAuthentication|KbdInteractiveAuthentication|PermitRootLogin|PubkeyAuthentication|AuthenticationMethods|AuthorizedKeysFile)' \
  /etc/ssh/sshd_config /etc/ssh/sshd_config.d
```

Read the actual included files, including other paths named by `Include`; `grep` is an aid, not a complete parser. OpenSSH normally uses the **first obtained value** for a keyword. Includes are processed where they occur and globbed filenames in lexical order. A matching `Match` block can override global values for that connection; among applicable Match assignments, ordering matters again. A late `99-...conf` file is not a reliable override.

This exercise uses a **new, global-only drop-in**, requiring an active `/etc/ssh/sshd_config.d/*.conf` Include in the global part of the main file. Check that no earlier assignment defeats it. Do not put `Match` blocks in this course drop-in or edit unrelated include files to force precedence. If the installed layout cannot support the new file as intended, stop the hardening step and investigate the owner/layout while retaining working access.

**Server console; set the target account again in this shell:**

```bash
read -r -p 'Normal SSH account on this server: ' SERVER_USER
SSH_CASE="user=$SERVER_USER,addr=192.0.2.10,host=net-client,laddr=192.0.2.20,lport=22"
sudo /usr/sbin/sshd -T -C "$SSH_CASE"
```

`-T` prints effective configuration; `-C` supplies a hypothetical connection so Match rules are evaluated. `host` describes the connecting host for hostname matches, not the server hostname. This course does not depend on hostname-based Match rules; if your configuration does, use the actual name sshd evaluates. Check `pubkeyauthentication`, `passwordauthentication`, `kbdinteractiveauthentication`, `permitrootlogin`, `authenticationmethods`, and `authorizedkeysfile`. A valid configuration can still reject your account because of `AllowUsers`, `DenyUsers`, group restrictions, PAM, or account state.

Save the effective baseline before adding anything:

```bash
sudo /usr/sbin/sshd -T -C "$SSH_CASE" > "$SERVER_NOTE/effective.before"
sudo /usr/sbin/sshd -T -C \
  'user=root,addr=192.0.2.10,host=net-client,laddr=192.0.2.20,lport=22' \
  > "$SERVER_NOTE/root-effective.before"
```

Record equivalent baselines for any existing management SSH paths, using their real source/local addresses and accounts. No example address should replace an actual management endpoint.

## 6. Add one owned policy file, validate, reload, and retest

Proceed only after the second key-only login and required management-path tests succeeded. These settings change **server-wide authentication**, subject to effective Match rules; they do not change NIC configuration.

**Server console, normal user invoking sudo; exclusive creation:**

```bash
sudo sh -c 'umask 077; set -C; : > /etc/ssh/sshd_config.d/00-network-beginner.conf'
sudoedit /etc/ssh/sshd_config.d/00-network-beginner.conf
```

`set -C` refuses to overwrite an existing file. If it fails, stop: do not edit or delete an earlier attempt without its recovery record. Put only this **configuration text** into your newly created file:

```text
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
```

`PasswordAuthentication no` alone does not disable password-like keyboard-interactive/PAM authentication. Keeping normal-user key login plus sudo avoids direct root SSH login. Do not disable PAM globally.

**Server console, normal user invoking sudo:**

```bash
sudo /usr/sbin/sshd -t
sudo /usr/sbin/sshd -T -C "$SSH_CASE"
sudo /usr/sbin/sshd -T -C \
  'user=root,addr=192.0.2.10,host=net-client,laddr=192.0.2.20,lport=22'
```

Continue only if syntax passes and the intended connections show `pubkeyauthentication yes`, both password/keyboard-interactive `no`, and `permitrootlogin no`. Repeat effective checks for required management paths. If an earlier setting or Match wins, **do not reload**: remove only your new file, validate the restored configuration, and investigate precedence. Renaming files randomly is not a fix.

**Server console, normal user invoking sudo:**

```bash
sudo systemctl reload "$SSH_UNIT"
systemctl status "$SSH_UNIT" --no-pager
sudo journalctl -u "$SSH_UNIT" -b -n 30 --no-pager
```

Reload asks the running daemon to reread its configuration. It is not a firewall reload or a socket-binding change. Keep the console and original sessions open, then create **another fresh client key-only login** using step 4 and recheck management SSH paths. The continued existence of an old authenticated session does not prove new logins work.

## Completion and exact recovery

Success means verified host fingerprint, dedicated passphrase-protected user key, correct ownership/permissions, a second fresh login before hardening, expected `-T -C` results for relevant accounts/paths, and a fresh successful login **after** reload. Explain why authentication failure differs from a refused TCP connection.

Practice policy rollback from the **server console**:

```bash
sudo rm -i -- /etc/ssh/sshd_config.d/00-network-beginner.conf
sudo /usr/sbin/sshd -t
sudo /usr/sbin/sshd -T -C "$SSH_CASE" > "$SERVER_NOTE/effective.restored"
diff -u "$SERVER_NOTE/effective.before" "$SERVER_NOTE/effective.restored"
sudo /usr/sbin/sshd -T -C \
  'user=root,addr=192.0.2.10,host=net-client,laddr=192.0.2.20,lport=22' \
  > "$SERVER_NOTE/root-effective.restored"
diff -u "$SERVER_NOTE/root-effective.before" "$SERVER_NOTE/root-effective.restored"
```

Confirm deletion only of the file you created. No diff output means the normal-account effective baseline matches; check the root and recorded management cases too. If other administrators/configuration managers changed state meanwhile, investigate the difference rather than restoring an entire old directory. Reload `$SSH_UNIT` **only after** syntax and intended restored values pass, then verify a new login. If new logins failed after hardening, this same console procedure is the recovery path.

You may reapply the owned drop-in with the same validation gates if retaining the hardened course setup. Otherwise, finish cleanup in this order:

1. **Server target account:** open `~/.ssh/authorized_keys` in nano and remove only the single key line identified by the course comment and recorded user-key fingerprint. Preserve all unrelated keys. Compare with `"$SERVER_NOTE/authorized_keys.before"` if it existed. Restore its recorded numeric mode. If it was originally absent and now empty, remove only this empty file; remove `.ssh` with `rmdir` only if you created it and it is empty. Restore recorded home/`.ssh` modes where those paths originally existed. On a shared account, reconcile concurrent changes instead of overwriting them with the backup.
2. **Client:** after closing course sessions and revoking the public key, remove only `id_ed25519`, `id_ed25519.pub`, and `known_hosts` inside the recorded `SSH_LAB_DIR` using `rm -i`, then `rmdir "$SSH_LAB_DIR"`. If an extra file exists, inspect its exact name; do not use recursive deletion. Existing client SSH files were never replaced.
3. **Server:** remove the exact lesson-created baseline/backup files from `SERVER_NOTE` once verified, then remove that empty directory. Record any management baseline filenames you created so cleanup stays explicit.
4. Restore the **recorded** service/socket runtime state only if you changed it and no later lesson needs SSH. If Ubuntu socket activation was originally active, preserve that socket; do not disable it merely because the service was initially inactive. If you newly installed packages, keeping them for later lessons is reasonable; complete package rollback uses the snapshots, which also discard later guest work.

## Primary references

Checked September 15, 2026:

- [Ubuntu Server OpenSSH](https://documentation.ubuntu.com/server/how-to/security/openssh-server/) — installation, `ssh.service`, and include precedence.
- [Ubuntu 24.04 release notes](https://discourse.ubuntu.com/t/noble-numbat-release-notes/39890) — OpenSSH socket activation and the socket configuration generator.
- [Rocky Linux OpenSSH key setup](https://docs.rockylinux.org/9/guides/security/ssh_public_private_keys/) — Rocky's OpenSSH workflow.
- [OpenSSH `ssh`](https://man.openbsd.org/ssh), [`ssh-keygen`](https://man.openbsd.org/ssh-keygen), [`sshd`](https://man.openbsd.org/sshd), and [`sshd_config`](https://man.openbsd.org/sshd_config) — identity, keys, validation, Include/Match, and effective settings.
- [Ubuntu 24.04 `ssh-copy-id`](https://manpages.ubuntu.com/manpages/noble/man1/ssh-copy-id.1.html) — selected-key installation and existing-key handling.

[Quiz](../../quizzes/networking/beginner/05-ssh-access-quiz.md) | [Continue to host security](06-firewalls-host-security.md)

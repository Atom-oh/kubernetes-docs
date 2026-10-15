# Quiz 1. Your first Linux terminal

> **Supported Versions**: Ubuntu Server 24.04 LTS (primary), Rocky Linux 9 (alternate)
> **Last Updated**: September 15, 2026

[Return to lesson](../../../networking/beginner/01-linux-cli.md) | [Course preparation](../../../networking/beginner/README.md)

Choose an answer before opening its explanation. These scenarios use the disposable guest and private notebook from lesson 1. Commands in questions are for interpretation, not instructions to run on your host.

1. `cat /etc/os-release` identifies Ubuntu 24.04, while `uname -r` prints a different version number. Which explanation fits?

   - A) One of the commands must be broken because Linux has only one version number.
   - B) Ubuntu is a library and `uname` identifies the terminal.
   - C) Ubuntu is a distribution; `uname -r` reports the running kernel. Libraries and the shell are separate user-space components.
   - D) Installing a new editor always replaces the kernel.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** A distribution assembles a kernel, libraries, tools, repositories, and configuration. The kernel manages resources and exposes system calls; a library supplies reusable functions, some of which use those calls. Bash interprets commands in user space. Their versions need not match the distribution release. Debian is the family from which Ubuntu derives, but that relationship does not guarantee identical defaults.

</details>

2. Your working directory is your unique scratch root. You run `cp -i notes/draft.txt notes/copy.txt`, followed by `mv -i notes/copy.txt archive/saved.txt`. What should exist after both succeed?

   - A) Only `archive/saved.txt`; `cp` removed the draft.
   - B) `notes/draft.txt` and `archive/saved.txt`; `notes/copy.txt` is gone.
   - C) All three files; `mv` is another spelling of copy.
   - D) Files in `/notes` and `/archive`, because relative paths start at `/`.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** `cp` leaves the source in place and creates a copy; `mv` changes the copy's location/name. Relative paths start at the working directory, which is why checking `pwd` matters. `-i` asks before overwriting an existing destination; it does not provide a general undo history. The saved copy can recover the draft later.

</details>

3. You want an empty practice file and run `touch notes/draft.txt`, forgetting that it already contains your notes. What does `touch` normally do?

   - A) Empty the file and preserve its old timestamps.
   - B) Create a directory with that name.
   - C) Update the existing file's timestamps while preserving its contents.
   - D) Move the file to your home directory.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** `touch` creates an empty file only when that path does not exist. On an existing file it normally changes access/modification timestamps, not its text. Use `cat` to inspect contents and `ls -l` to inspect size. This is also why the lesson starts in a unique directory rather than assuming a familiar filename is unused.

</details>

4. You have unsaved edits in vi and want to discard them. Which action is correct?

   - A) Type `:q!` at the Bash prompt.
   - B) Press Esc, type `:q!`, and press Enter inside vi.
   - C) Press `i`, then type `:wq`.
   - D) Press Ctrl+O, which saves and exits every editor.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Esc returns vi to normal mode; `:q!` discards changes since the last save and exits. `:wq` saves and exits, while `:q` protects unsaved work by refusing to quit. In nano, Ctrl+O writes after filename confirmation and Ctrl+X exits. To discard unsaved nano changes, exit and decline its save prompt. Editor commands must be entered in the editor, not the shell.

</details>

5. A file's basic mode is `640` (`-rw-r-----`). Which interpretation is correct?

   - A) The owner can read/write, the group can read, and others have no basic file permissions.
   - B) Everyone can read/write because `6` is the largest digit.
   - C) The owner can execute because `6` means read plus execute.
   - D) Nobody can delete it because its execute bit is absent.

<details>
<summary>Show Answer</summary>

**Answer: A**

**Explanation:** Read=4, write=2, execute=1, so owner `6` means read+write and group `4` means read. Directory permissions and other controls affect access and deletion of directory entries; file write permission alone is not the deletion rule. To undo the lesson's `chmod 600`, restore the recorded original numeric mode, not an assumed `644`.

</details>

6. Saving your notebook reports “Permission denied.” What is the best first response?

   - A) Run a recursive permission change over `/home`.
   - B) Start a root shell and repeat every remaining lesson command.
   - C) Check `pwd`, `id`, and the relevant directory/file ownership and permissions.
   - D) Disable the guest's firewall.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** You may be in the wrong directory or editing a file owned by another account. The notebook lives in your own scratch directory and normally needs no elevation. `sudo` elevates a permitted command, root by default; it is not a diagnosis. `sudo whoami` followed by `whoami` shows that a single elevated command does not permanently turn the normal shell into root.

</details>

7. On Ubuntu, `sudo apt update` completes successfully. Has it upgraded all installed packages and ensured nano is installed?

   - A) Yes; `update` means install every available update and missing editor.
   - B) No; it refreshed repository package indexes. A separate package transaction is needed to install or upgrade software.
   - C) It changed only the currently running kernel.
   - D) It enabled every newly discovered service.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** `apt update` refreshes information about available packages; `apt install nano` requests an installation and dependency resolution, while `apt upgrade` has a different purpose. On the guest, review a proposed transaction before confirming it. A local `dpkg-query` checks installed package records. Removing a package later is not an exact reversal of all dependency, cache, log, or configuration changes; the optional installation's full recovery uses the recorded VM snapshot.

</details>

8. A Rocky Linux 9 guest needs an editor. Which preparation path matches the lesson?

   - A) Add Ubuntu repositories and run APT.
   - B) Use `rpm -q` for local package inventory and DNF for installation; `yum` compatibility exists, but there is no need to run both.
   - C) Use `systemctl install nano` because all software is a service.
   - D) Rebuild the kernel before installing any package.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Rocky uses RPM packages and DNF dependency management. The lesson's alternate editor packages are `nano` and `vim-minimal`; Ubuntu uses its own package family and package names. Distribution familiarity helps you select tools, but it is not permission to mix repositories or assume service/network defaults are identical.

</details>

9. What do `ps -p $$ -o pid,ppid,user,comm` and the `sleep 30` exercise help you observe?

   - A) The shell's process identity and a foreground process that temporarily occupies the shell.
   - B) Every package installed on the guest.
   - C) A permanent service created by every shell command.
   - D) A PID that will be the same on both VMs and after every reboot.

<details>
<summary>Show Answer</summary>

**Answer: A**

**Explanation:** `$$` expands to the current Bash PID; `PPID` identifies its parent. A process is an executing instance of a program, whereas a package is software installed on disk. `sleep` either finishes after 30 seconds or can be interrupted with Ctrl+C. No service was enabled, and you should not use a PID copied from a document to terminate an unknown process.

</details>

10. `systemctl is-active systemd-journald.service` reports `active`, while `is-enabled` reports `static`. Which conclusion is justified?

   - A) The logging service has failed because it is not `enabled`.
   - B) The unit is active now and has no ordinary enablement section; dependency/activation paths can start it.
   - C) `static` means logs are permanently frozen.
   - D) `enable` must be run repeatedly until both commands return the same word.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Runtime state and enablement are separate. `start` affects current operation, while `enable` creates enablement links and does not itself start a unit unless combined with `--now`. A static unit is not inherently broken. Read `Loaded`, `Active`, and relevant logs instead of changing system services to force a particular display.

</details>

11. What does `sudo journalctl -b -u systemd-journald.service -n 20 --no-pager` select?

   - A) The first 20 lines of every log file from all boots.
   - B) The latest 20 retained matching entries for that unit in the current boot, printed without a pager.
   - C) All entries and then deletes the last 20.
   - D) Only errors, because every journal message is an error.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** `-b` restricts the boot, `-u` the unit, and `-n` the number of recent entries. This is a read operation. Interpret timestamp and message context; an informational event is not a failure. No matching entries may reflect the filter or retention, and less-privileged readers may have incomplete visibility. Compare service status before concluding that logging is broken.

</details>

12. You reopened the VM console, and `LAB_DIR` is empty. What is the right cleanup procedure?

   - A) Delete all directories whose names start with `network-beginner`.
   - B) Assume the previous shell's current directory and run recursive removal.
   - C) Restore `LAB_DIR` from the exact recorded path, inspect it, remove only the named practice files, then remove empty directories.
   - D) Delete `/tmp` to remove all possible scratch files.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Variables do not automatically persist across sessions. The recorded unique path and explicit filenames bound the operation. `rmdir` refusing a nonempty directory is useful evidence: inspect leftover editor files or incomplete steps rather than escalating to broad deletion. A successful `test ! -e "$LAB_DIR"` returns status `0`, confirming that specific path is absent.

</details>

Use any missed explanation to revisit the matching exercise in the [lesson](../../../networking/beginner/01-linux-cli.md), then continue to [addresses and interfaces](../../../networking/beginner/02-addressing-interfaces.md).

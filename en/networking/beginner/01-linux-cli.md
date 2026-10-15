# 1. Your first Linux terminal

> **Supported Versions**: Ubuntu Server 24.04 LTS (primary), Rocky Linux 9 (alternate)
> **Last Updated**: September 15, 2026

[Course preparation](README.md) | [Quiz](../../quizzes/networking/beginner/01-linux-cli-quiz.md) | [Next: Addresses and interfaces](02-addressing-interfaces.md)

Network administration begins with being able to answer three questions: which machine am I using, which file am I changing, and how will I undo the change? This lesson builds those habits while you create a small notebook, edit it, inspect its permissions, and read a service's status.

## Prerequisites and outcomes

Use a disposable **local VM**, with a normal user account, its password, and permission to use `sudo`. Open the VM through the hypervisor console; a hypervisor is the application that runs your virtual machines. Ubuntu Server 24.04 LTS is the main path. Rocky Linux 9 is an alternative: you do not need to learn both at once. A typical container does not provide the complete booted systemd environment used here.

Have Bash, GNU core utilities, `ps`, systemd, `nano`, and a `vi` implementation available in the guest. If an editor is missing, use the package preparation section below before starting the notebook. No network configuration is required in this lesson. Keep the existing NAT/DHCP management interface as prepared in the course introduction.

By the end, you should be able to:

- Explain what the kernel, libraries, shell, and distribution contribute.
- Navigate paths and create, copy, move, edit, and remove your own practice files.
- Save or discard edits in nano and vi, and interpret basic ownership and permissions.
- Choose Ubuntu's or Rocky's package tools and distinguish installed software from a running service.
- Read process IDs, systemd state, and a bounded selection of journal messages.

**Execution contract:** every shell block below runs **inside the practice VM**, never on your laptop's host OS, this documentation checkout's host, or a cloud server. Blocks without `sudo` run as your normal user. A `sudo` line elevates only that command. Run one step at a time and stop on an unexpected error. Output samples are illustrative, **not transcripts of live-tested Ubuntu/Rocky VMs**.

## Understand the system you logged into

“Linux” can mean the **kernel** or, informally, the complete operating system. The kernel manages CPU time, memory, filesystems, device drivers, and network packets. It provides system calls through which programs request these services. Your shell and editor run in **user space**, outside the kernel.

A **library** provides reusable functions. For example, the GNU C Library (glibc) supplies facilities that many programs use for text, file I/O, and operating-system access. Some library functions call the kernel; others only work on data in memory. A library is neither an editor nor a second kernel. Package dependencies often exist because an application needs a particular library.

A **distribution** assembles the kernel, libraries, commands, installer, repositories, updates, and default configuration into an installable system. A repository here is a managed source of software packages; a package contains software plus information about its version and dependencies.

| Distribution | Relationship and package family | Meaning for this course |
| --- | --- | --- |
| Debian | Community distribution using `.deb` packages, APT, and dpkg | Explains the family Ubuntu comes from; Debian's network/service defaults are not automatically Ubuntu's |
| Ubuntu | Debian-derived distribution with its own releases and repositories | Follow the Ubuntu Server 24.04 LTS command path |
| Rocky Linux | Enterprise Linux distribution in the RHEL ecosystem; `.rpm` packages, DNF, and RPM | Follow the Rocky 9 alternate package path |

The **terminal** handles your keyboard and text display. The **shell**, Bash in this course, interprets what you type and runs commands. Typing `ls` asks a user-space program to list files; it is not a direct conversation with the kernel. These distinctions follow the Debian and GNU documentation listed in the references.

**Practice VM, normal user; inspect only:**

```bash
hostname
whoami
id
cat /etc/os-release
uname -r
pwd
```

`hostname` identifies the guest; compare it with the console window you opened. `whoami` identifies your account. `id` includes your numeric user ID (UID), group ID, and groups. If UID is `0`, you are root: return to the normal account for these exercises. `cat` displays a text file. In `/etc/os-release`, inspect `ID` and `VERSION_ID`: the main path should identify Ubuntu and `24.04`, the alternate Rocky and `9.x`. `uname -r` reports the **running kernel version**, which is not the distribution release number. `pwd` prints your current working directory.

An illustrative prompt is `learner@client:~$`: account, machine, current directory, then the prompt marker. `~` represents your home directory. `$` usually marks an ordinary shell and `#` often marks root, but prompts are customizable; trust `id`. **Do not type the prompt marker.** In command blocks, a line beginning with `#` is an explanatory Bash comment.

## Read commands before running them

In `ls -la notes`, `ls` is the command, `-l` and `-a` are options, and `notes` is the path argument. `-l` requests details; `-a` includes names beginning with a dot. Press Enter to run a command, Tab to complete a partly typed path, and the up arrow to recall a previous command. Inspect recalled commands before pressing Enter.

Linux paths form a tree rooted at `/`. An **absolute** path begins there, such as `/home/learner`; a **relative** path begins at the working directory, such as `notes/draft.txt`. `.` means the current directory and `..` its parent. On the ordinary Linux filesystems used here, `Notes` and `notes` are different names.

`/etc` holds system configuration, `/var/log` holds many logs, and `/home` holds normal users' home directories. We read system information but write practice files only under a newly created private directory.

**Practice VM, normal user; built-in/local help:**

```bash
help cd
ls --help
man ls
```

`cd` is a shell built-in, so Bash's `help` explains it. `--help` prints command usage. If the optional `man` program/manual pages are installed, `man ls` opens a manual in a pager: Space moves forward, `/permission` searches, and `q` exits. If `man` is unavailable, `ls --help` and the references still work. `Ctrl+C` cancels an unfinished shell line or interrupts many foreground programs; it is not a universal “save and exit” command.

## Package preparation: choose one distribution

Package management is how you obtain an editor, including its required libraries, from configured repositories. First inspect what is already installed. These queries use the local package database and need no repository connection or elevated privileges.

**Ubuntu practice VM only, normal user:**

```bash
dpkg-query -W bash coreutils nano vim-tiny iproute2
```

**Rocky practice VM only, normal user:**

```bash
rpm -q bash coreutils nano vim-minimal iproute
```

Each installed package produces its name/version. A “not installed” or “no packages found” message identifies a missing package; it is not an invitation to replace the whole system. Different package names may supply the same command, so also inspect the commands directly.

**Either practice VM, normal user:**

```bash
command -v nano
command -v vi
```

An executable path such as `/usr/bin/vi` means the command is available. No path means it was not found in the shell's command search path.

If an editor is missing, the following is an **optional guest preparation operation**. Use only the appropriate distribution block, through the already working management connection. First take a named VM snapshot in the hypervisor, for example `before-cli-editors`, so you can restore the complete pre-installation state. Read the proposed transaction and confirm only the expected editor and dependencies; answer `n` to cancel an unexpected removal or upgrade.

**Ubuntu practice VM only, normal user invoking sudo:**

```bash
sudo apt update
sudo apt install nano vim-tiny
```

`apt update` refreshes the available-package index; it does **not** upgrade all installed software. Proceed to installation only when the index refresh succeeds without repository errors. `apt install` installs the named packages and resolves dependencies. `apt upgrade` has the different purpose of upgrading installed packages; it is not needed for this lesson.

**Rocky practice VM only, normal user invoking sudo:**

```bash
sudo dnf install nano vim-minimal
```

DNF resolves RPM package dependencies and refreshes repository metadata when needed. Rocky 9 also provides `yum` compatibility for familiar commands, but this course uses `dnf`. Do not run both command families on the same guest or add third-party repositories to make an example work.

After preparation, repeat the local package query and `command -v` checks. Failure to download packages concerns the management connection/repository access; it is unrelated to the isolated lab NIC introduced next lesson.

**Recovery:** `apt remove` or `dnf remove` removes packages, but is not an exact inverse of installation: dependency changes, caches, logs, and some configuration may remain. Do not remove an editor that was already installed. Keep the editors for subsequent lessons, or restore `before-cli-editors` when finished with the guest; a snapshot also discards all work performed after it. No package removal or `autoremove` is required for notebook cleanup.

## Build a notebook in a unique scratch directory

First create the exercise boundary. `$HOME` already names your home directory; do not redefine it. `LAB_DIR` is a new variable for this lesson. `$(...)` captures the output of a command, and the double quotes keep a path together even if it contains spaces.

**Practice VM, normal user:**

```bash
LAB_DIR=$(mktemp -d "$HOME/network-beginner-cli.XXXXXX")
printf '%s\n' "$LAB_DIR"
```

`mktemp -d` creates a new directory and replaces the six `X` characters with a unique suffix. `printf '%s\n'` prints the stored path and a newline. Expect a path such as `/home/learner/network-beginner-cli.aB12Cd`, with **your** account and suffix. Record the actual path before continuing. If creation fails or the printed value is empty, stop; do not run the file exercises.

**Same VM and shell, normal user:**

```bash
cd -- "$LAB_DIR"
pwd
ls -la
```

Continue only if `pwd` matches your recorded directory. `cd` changes where relative paths begin; it does not move files. `--` ends option parsing. The initial listing contains `.` and `..`, and the new directory is private to your account.

**Same VM and shell, normal user, from that directory:**

```bash
mkdir notes archive
touch notes/draft.txt notes/vi.txt
ls -l notes
cd notes
pwd
cd ..
pwd
```

`mkdir` creates directories. `touch` creates the two empty files because they do not exist yet; on an existing file it updates timestamps without emptying the contents. Both files initially have size `0`. The first `pwd` ends in `/notes`; the second returns to the scratch root. A successful `mkdir`, `touch`, or `cd` usually prints nothing. Silence is normal; inspect the result with `ls` or `pwd`.

## Edit, save, copy, and move

**Same practice VM, normal user, scratch root:**

```bash
nano notes/draft.txt
```

Type these two lines **in the editor**, not at the shell:

```text
I am learning Linux networking.
This file belongs to my practice notebook.
```

In nano, `^O` on the help bar means **Ctrl+O**, not the characters `^` and `O`. Press Ctrl+O, check the filename, and press Enter to write. Press Ctrl+X to exit. To discard edits made since the last save, press Ctrl+X and choose `N` when asked to save; localized prompts may use a different displayed key. Choosing `Y` writes your changes after filename confirmation.

**Back at the shell, same VM, normal user:**

```bash
cat notes/draft.txt
cp -i -- notes/draft.txt notes/copy.txt
mv -i -- notes/copy.txt archive/saved.txt
ls -l notes archive
```

`cat` should display what you saved. `cp` copies content to a second file; the original remains. `mv` moves or renames a file: `notes/copy.txt` becomes `archive/saved.txt`. For both commands `-i` asks before overwriting an existing destination; answer `n` if you did not expect one. Expect `draft.txt` and `vi.txt` in `notes`, and `saved.txt` in `archive`. This saved copy now lets you recover the draft if a later edit goes wrong.

For recovery, from this same scratch root as the normal user, `cp -i -- archive/saved.txt notes/draft.txt` replaces only the draft; confirm only when you intend to discard its newer contents.

**Same practice VM, normal user, scratch root:**

```bash
vi notes/vi.txt
```

`vi` commonly runs a Vim variant on these guests. It starts in **normal mode**, where keys are commands. Press `i` to enter insert mode, type `I can save and exit vi.`, then press Esc to return to normal mode.

| Keys after Esc | Result |
| --- | --- |
| `:w` then Enter | Save and continue editing |
| `:wq` then Enter | Save and exit this single-file session |
| `:q` then Enter | Exit when no unsaved changes remain |
| `:q!` then Enter | Discard changes since the last save and exit |

Practice `:wq`, reopen the file, type an extra word after pressing `i`, and discard that extra edit with Esc, `:q!`, Enter. Back at the shell, `cat notes/vi.txt` should still contain only the saved sentence. The colon commands belong **inside vi**, not in Bash. A “No write since last change” message from `:q` is protecting your unsaved work.

## Permissions and sudo

Every file has an owner and a group. The basic permission sets apply to owner, group, and everyone else, in that order. In illustrative output `-rw-r--r--`, the first `-` indicates a regular file; the next triplets mean owner can read/write, group can read, and others can read. A directory starts with `d`. An extra `.` or `+` may indicate security metadata or ACLs; those additional controls are beyond this first exercise.

For files, `r` reads contents, `w` changes contents, and `x` permits execution. For directories, `r` lists names, `x` permits traversal/access, and `w` together with traversal permits creating/removing entries, subject to other controls. A file's write permission alone does not decide whether its directory entry can be deleted.

**Same practice VM, normal user, scratch root; change only your draft:**

```bash
ls -l notes/draft.txt
LAB_DRAFT_MODE=$(stat -c '%a' notes/draft.txt)
printf '%s\n' "$LAB_DRAFT_MODE"
chmod 600 notes/draft.txt
ls -l notes/draft.txt
```

`stat` records the original numeric mode; keep that value. For each triplet, read=4, write=2, execute=1. Thus `600` gives the owner `4+2`, the group `0`, and others `0`: expect `-rw-------`. The enclosing scratch directory already limits access, so this is an interpretation exercise rather than a need to make a real secret file.

**Undo now, same VM and shell, normal user:**

```bash
chmod "$LAB_DRAFT_MODE" notes/draft.txt
stat -c '%a' notes/draft.txt
```

The resulting number should equal your recorded mode. We restore the recorded value instead of assuming every system originally used `644`. No `sudo` is needed to change the mode of this file you own.

`sudo` runs a permitted command as another user, root by default. It normally asks for **your account password**, which may show no characters while typed. It is not a general cure for “Permission denied.”

**Practice VM, normal user; demonstrate identity with one elevated query:**

```bash
sudo whoami
whoami
```

Expect `root`, then your normal username. If you are not authorized, stop and use the account prepared for the course; do not edit `sudoers` blindly. If writing your notebook fails, check `pwd`, `id`, and `ls -ld` for the relevant directory first. Avoid broad recursive permission changes: they hide the cause and affect unrelated files.

## Programs, processes, services, and logs

A **program** is software stored on disk. A **process** is a running instance with a process ID (PID), an owner, and memory. Installing a program does not necessarily start it. A **service** is work managed in the background, often by systemd; one service may have several processes.

**Practice VM, normal user; inspect only:**

```bash
ps -p $$ -o pid,ppid,user,comm
ps -p 1 -o pid,comm
```

`$$` expands to this Bash shell's PID. `-p` selects a PID and `-o` selects displayed columns. `PPID` is the parent process ID; `COMM` is the command name. Expect your shell in the first result and systemd as PID 1 in these booted guests. PID numbers other than 1 vary. If PID 1 is not systemd, return to the full VM environment before following the service exercise.

**Practice VM, normal user; a bounded foreground process:**

```bash
sleep 30
```

The prompt waits while `sleep` is running. Press Ctrl+C to interrupt it and regain the prompt, or let it finish after 30 seconds. There is no file or service configuration to clean up. This is safer practice than terminating an unfamiliar process. `kill` sends a signal to a specified process; using a copied PID from a document can target somebody else's work.

Systemd manages **units**, including `.service` units. The journal collects messages from systemd and services. Start with the logging service that both guest paths use.

**Practice VM, normal user; inspect only:**

```bash
systemctl status systemd-journald.service --no-pager
systemctl is-active systemd-journald.service
systemctl is-enabled systemd-journald.service
```

In `status`, `Loaded` says whether a unit definition was found; `Active` describes its current state; `Main PID` identifies its main process when applicable. The journal service should normally be active. `is-enabled` can report `static`: that means there is no ordinary enablement section, **not** that the service is broken. Units can be brought in by dependencies or activation.

| Operation to recognize | What it changes |
| --- | --- |
| `start` / `stop` | Current runtime state |
| `restart` | Stop/start cycle; may interrupt users |
| `enable` / `disable` | Enablement links used for activation, often at boot; does not itself start/stop |
| `enable --now` | Enable and also start |
| `reload` | Ask a supporting service to reread its configuration |

These are concepts for later administration; **do not stop or restart the logging or networking services for this exercise**. An enabled service can have failed, and a disabled service can currently be running. Check runtime and enablement separately.

**Practice VM, normal user invoking sudo to read system logs:**

```bash
sudo journalctl -b -u systemd-journald.service -n 20 --no-pager
```

`-b` restricts to the current boot, `-u` selects a unit, and `-n 20` limits the output to the latest 20 matching entries. `--no-pager` returns directly to the shell. Read timestamp, machine, process/unit, and message together. A journal entry is evidence of an event; it is not necessarily an error. No entries may mean there are no retained messages matching this filter; without sufficient permissions, you may also see less of the journal. Compare with `status` before concluding the service failed.

## Completion check and cleanup

Before removing the notebook, use `cat` and `ls -l` from its root to verify that:

1. `notes/draft.txt` and `archive/saved.txt` contain your two sentences, and `notes/copy.txt` is absent.
2. `notes/vi.txt` retains the saved sentence but not the discarded extra word.
3. The draft's mode matches the recorded original value, and you can explain each permission triplet.
4. You can identify the guest distribution, running kernel, normal account, shell PID, and journald's active state without confusing them.
5. You can explain why refreshing a package index, starting a service, and enabling it are three different operations.

Now remove only the files made here. If you opened another shell, the variables are **not** automatically present: set `LAB_DIR` to the exact path you recorded, inspect its contents, and then continue. Never guess a suffix or select every directory with a wildcard.

**Practice VM, normal user, using your recorded `LAB_DIR`:**

```bash
cd -- "$LAB_DIR"
pwd
ls -la notes archive
```

After confirming this is your scratch directory:

```bash
rm -i -- notes/draft.txt notes/vi.txt archive/saved.txt
rmdir -- notes archive
cd -- "$HOME"
rmdir -- "$LAB_DIR"
```

`rm -i` asks about each named file; confirm only those practice files. `rmdir` removes **empty** directories. If it refuses, inspect the remaining files, including editor backup/swap files or an unfinished `copy.txt`, and remove only your identified practice files by exact name. Do not switch to recursive deletion. An already missing file after partial cleanup is not a reason to widen the deletion.

**Practice VM, normal user; verify cleanup:**

```bash
test ! -e "$LAB_DIR"
echo $?
unset LAB_DIR LAB_DRAFT_MODE
sudo -k
```

`test ! -e` checks that the recorded path no longer exists; `echo $?` should print `0`, meaning the immediately preceding check succeeded. A `1` means it still exists. `unset` removes lesson variables; `sudo -k` invalidates your cached sudo authorization so a later elevated command may ask again. Guest system configuration was only inspected; any optional editor installation remains until you choose the snapshot recovery described above.

## References and further reading

Primary documentation checked September 14–15, 2026. These explain the tools used here; they are not prerequisites or substitutes for the exercises.

- [Debian: About Debian](https://www.debian.org/intro/about) — distribution, kernel, utilities, and packages.
- [GNU C Library introduction](https://www.gnu.org/software/libc/manual/html_node/Introduction.html) — what a system library supplies.
- [Debian Reference, GNU/Linux tutorials](https://www.debian.org/doc/manuals/debian-reference/ch01.en.html) — shell, filesystems, permissions, and processes.
- [GNU Coreutils manual](https://www.gnu.org/software/coreutils/manual/coreutils.html), especially [mktemp](https://www.gnu.org/software/coreutils/manual/html_node/mktemp-invocation.html) — file operations and private scratch directories.
- [GNU nano shortcuts](https://www.nano-editor.org/dist/latest/cheatsheet.html) and [Vim first steps](https://vimhelp.org/usr_02.txt.html) — editor modes, writing, and quitting.
- [Ubuntu Server package management](https://ubuntu.com/server/docs/how-to/software/package-management/) and [Rocky Linux 9 DNF guide](https://docs.rockylinux.org/9/guides/package_management/dnf_package_manager/) — the two package paths.
- [systemd systemctl manual](https://www.freedesktop.org/software/systemd/man/systemctl.html) and [journalctl manual](https://www.freedesktop.org/software/systemd/man/journalctl.html) — runtime state, enablement, and log filters.

Continue with [Addresses and interfaces](02-addressing-interfaces.md), after checking your understanding in the [lesson quiz](../../quizzes/networking/beginner/01-linux-cli-quiz.md).

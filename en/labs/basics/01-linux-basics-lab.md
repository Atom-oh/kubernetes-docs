# Linux Basics Lab Guide

> **Difficulty**: Beginner
> **Estimated Time**: 45 minutes
> **Last Updated**: September 11, 2026

## Learning Objectives
- Practice Linux process management commands
- Directly observe the isolation effect of Linux namespaces
- Understand resource limits through cgroups
- Practice file permissions and ownership management

## Prerequisites
- [ ] A maintained Linux VM with Bash, systemd and cgroup v2 for Exercise3
- [ ] Tools: coreutils, procps/procps-ng, util-linux, iproute2/iproute and Python3
- [ ] sudo privileges
- [ ] Completed [Linux Basics](../../basics/01-linux-basics.md) learning

Run the blocks in order in the same Bash terminal so the lab variables remain available. Use an isolated VM for the sudo namespace/cgroup exercises. A container or restricted environment can lack the required capabilities even with sudo. Outputs below are illustrative; privileged exercises were not executed during this audit.

---

## Exercise 1: Process Management

### Goal
Practice process listing, background execution, and signal sending.

### Steps

**Step 1.1: Check currently running processes**
```bash
# Snapshot of processes visible in the current PID namespace
ps aux | head -20

# View process relationships in tree format
ps auxf | head -30
```

**Step 1.2: Run a background process**
```bash
sleep 300 &
LINUX_LAB_SLEEP_PID=$!
printf 'Lab child PID: %s\n' "$LINUX_LAB_SLEEP_PID"
jobs -l
```

**Step 1.3: Send a signal to a process**
```bash
# Run in the same Bash session as Step 1.2.
: "${LINUX_LAB_SLEEP_PID:?Run Step 1.2 first}"
if jobs -pr | grep -Fxq -- "$LINUX_LAB_SLEEP_PID"; then
  kill -TERM "$LINUX_LAB_SLEEP_PID"
fi
if wait "$LINUX_LAB_SLEEP_PID"; then
  LINUX_LAB_EXIT_STATUS=0
else
  LINUX_LAB_EXIT_STATUS=$?
fi
printf 'Lab child exit status: %s\n' "$LINUX_LAB_EXIT_STATUS"
unset LINUX_LAB_SLEEP_PID
```

<details>
<summary>Need a hint?</summary>

- Use `kill -l` to see a list of available signals
- `kill -9 PID` forcefully terminates with SIGKILL
- Keep the PID captured with `$!`; name patterns can match unrelated jobs.
</details>

### Verification
```bash
printf 'Recorded lab child exit status: %s\n' "${LINUX_LAB_EXIT_STATUS:?Complete Step 1.3}"
jobs -l
```

---

## Exercise 2: Linux Namespace Isolation

### Goal
Create namespaces to observe process and network isolation.

### Steps

**Step 2.1: Verify PID namespace isolation**
```bash
# Run bash in a new PID namespace
sudo unshare --mount --pid --fork --mount-proc bash -c '
echo "PID list inside the new namespace:"
ps aux
echo "Current process PID: $$"
'
```

Expected output:
```
PID list inside the new namespace:
USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1  0.0  0.0   ...   ...  ...      S    ...    0:00 bash -c ...
root         2  0.0  0.0   ...   ...  ...      R    ...    0:00 ps aux
Current process PID: 1
```

**Step 2.2: Network namespace isolation**
```bash
LINUX_LAB_NETNS="k8s-docs-netns-${UID}-$$"
(
  # Install cleanup only after creating this namespace successfully.
  sudo ip netns add "$LINUX_LAB_NETNS" || exit 1
  trap 'sudo ip netns delete "$LINUX_LAB_NETNS"' EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  sudo ip netns exec "$LINUX_LAB_NETNS" ip addr
)
```

<details>
<summary>Need a hint?</summary>

- Host network interfaces are not visible inside the network namespace
- Only the `lo` (loopback) interface exists, and it's DOWN by default
- This is the principle behind container network isolation
</details>

### Verification
```bash
if LINUX_LAB_NS_LIST=$(sudo ip netns list); then
  if printf '%s\n' "$LINUX_LAB_NS_LIST" | awk '{print $1}' | grep -Fxq -- "$LINUX_LAB_NETNS"; then
    printf 'Named handle still exists: %s\n' "$LINUX_LAB_NETNS"
  else
    printf 'Named handle is not listed: %s\n' "$LINUX_LAB_NETNS"
  fi
else
  printf 'Could not verify namespace handles\n' >&2
fi
```

---

Removing the named netns handle does not kill processes or destroy a namespace still held by a process/file descriptor. This example waits for its `ip addr` command to finish before cleanup.

## Exercise 3: cgroup Resource Limits

### Goal
Use cgroups to limit process memory usage.

### Steps

**Step 3.1: Check cgroup information**
```bash
# cgroup2fs identifies a cgroup v2 mount.
stat -fc '%T' /sys/fs/cgroup
cat /proc/self/cgroup
if [ -r /sys/fs/cgroup/cgroup.controllers ]; then
  cat /sys/fs/cgroup/cgroup.controllers
else
  printf 'Controllers are not readable here; inspect the mount and permissions\n'
fi
```

**Step 3.2: Check memory usage**
```bash
# System memory information
free -h

# Memory usage of specific processes
ps aux --sort=-%mem | head -10
```

**Step 3.3: Apply a limit to a transient service**

On a VM with systemd and the memory controller available in cgroup v2, this creates an automatically named service with a128MiB memory maximum and no swap allowance. It touches16MiB without deliberately causing OOM, then `--wait --collect` waits for completion and unloads the transient unit. Ancestor limits can be more restrictive.

```bash
sudo systemd-run --wait --collect --pipe \
  --property=MemoryMax=128M --property=MemorySwapMax=0 \
  python3 -c '
from pathlib import Path
entry = next(line for line in Path("/proc/self/cgroup").read_text().splitlines()
             if line.startswith("0::"))
group = Path("/sys/fs/cgroup") / entry.split(":", 2)[2].lstrip("/")
print("Configured memory.max:", (group / "memory.max").read_text().strip())
data = bytearray(16 * 1024 * 1024)
for offset in range(0, len(data), 4096):
    data[offset] = 1
print("Touched allocation bytes:", len(data))
'
```

The configured `memory.max` should be134217728 bytes for128M; the allocation is16777216 bytes. These are configuration/arithmetic expectations, not measured results from this audit. The next manifest is printed only and does not create a Kubernetes Pod.

**Step 3.4: Connection to Kubernetes resource limits**
```bash
# Linux container memory-limit example; this block only prints YAML
# Let's look at a Pod manifest example
cat << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: memory-demo
spec:
  containers:
  - name: memory-demo
    image: nginx:1.30.4
    resources:
      requests:
        memory: "64Mi"
      limits:
        memory: "128Mi"
EOF
```

<details>
<summary>Need a hint?</summary>

- For Linux containers, the runtime/kubelet configures memory cgroup limits.
- Memory pressure can cause reclaim, allocation failure or OOM killing depending on the allocation and OOM-group policy. A container terminated by OOM can report `OOMKilled`; not every allocation failure produces that status.
- `kubectl describe pod` shows requested limits and recorded container termination state, not proof of every kernel memory event.
</details>

---

## Exercise 4: File Permission Management

### Goal
Practice managing file permissions and ownership.

### Steps

**Step 4.1: Create a file and check permissions**
```bash
LINUX_LAB_DIR=$(mktemp -d /tmp/k8s-docs-linux-basics.XXXXXX)
: "${LINUX_LAB_DIR:?mktemp failed}"
printf 'Hello Linux\n' > "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
ls -ld "$LINUX_LAB_DIR"
ls -l "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
```

**Step 4.2: Change permissions**
```bash
# Add execute permission
chmod +x "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
ls -la "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"

# Set with numeric mode (read/write - read - none)
chmod 640 "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
ls -la "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"

# Set the same permissions as K8s Secret volume defaults
chmod 0644 "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
```

Adding the execute bit does not turn arbitrary text into a valid program. Mode0644 includes read permission for group/others when directory traversal is allowed; the private mktemp directory restricts access in this lab. Kubernetes Secret volumes default to0644, but real secret permissions must match the consuming user/group and required access.

**Step 4.3: Change ownership**
```bash
id
# Demonstrate an owner change only on the private lab file, then restore it.
sudo chown "root:$(id -g)" "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
stat -c '%a %U %G' "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
sudo chown "$(id -u):$(id -g)" "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
```

### Verification
```bash
# Expect mode644 and the restored user/group
stat -c "%a %U %G" "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
```

---

## Cleanup
```bash
# Delete only the file created by this lab; keep an unexpected nonempty directory.
if [[ -n ${LINUX_LAB_DIR:-} ]]; then
  rm -f -- "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
  if rmdir -- "$LINUX_LAB_DIR"; then
    unset LINUX_LAB_DIR
  fi
fi

# Only an unfinished job created in this Bash session may be terminated.
if [[ -n ${LINUX_LAB_SLEEP_PID:-} ]]; then
  if jobs -pr | grep -Fxq -- "$LINUX_LAB_SLEEP_PID"; then
    kill -TERM "$LINUX_LAB_SLEEP_PID"
  fi
  wait "$LINUX_LAB_SLEEP_PID" 2>/dev/null || true
  unset LINUX_LAB_SLEEP_PID
fi
```

## Troubleshooting

<details>
<summary>The unshare command is not found</summary>

Install the `util-linux` package:
```bash
sudo apt-get install util-linux   # Ubuntu/Debian
sudo dnf install util-linux       # Fedora/RHEL
```
</details>

<details>
<summary>The ip netns command does not work</summary>

The `iproute2` package is required:
```bash
sudo apt-get install iproute2     # Ubuntu/Debian
sudo dnf install iproute          # Fedora/RHEL
```
</details>


## References and validation scope

* [systemd-run](https://www.freedesktop.org/software/systemd/man/latest/systemd-run.html)
* [systemd memory resource control](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html)
* [Kernel cgroup v2 memory controller](https://docs.kernel.org/admin-guide/cgroup-v2.html)
* [unshare](https://man7.org/linux/man-pages/man1/unshare.1.html)
* [ip netns](https://man7.org/linux/man-pages/man8/ip-netns.8.html)
* [GNU mktemp manual](https://man7.org/linux/man-pages/man1/mktemp.1.html)

Only isolated unprivileged process/file checks and syntax checks were run for the audit. Namespace creation, ownership changes and cgroup/systemd operations were not executed.

## Next Steps
- [Linux Basics Quiz](../../quizzes/basics/01-linux-basics-quiz.md)
- [Linux Advanced Skills Lab](./02-linux-advanced-lab.md)

# Linux Basics Lab Guide

> **Difficulty**: Beginner
> **Estimated Time**: 45 minutes
> **Last Updated**: February 2025

## Learning Objectives
- Practice Linux process management commands
- Directly observe the isolation effect of Linux namespaces
- Understand resource limits through cgroups
- Practice file permissions and ownership management

## Prerequisites
- [ ] Linux terminal access (Ubuntu 20.04+ recommended)
- [ ] sudo privileges
- [ ] Completed [Linux Basics](../../basics/01-linux-basics.md) learning

---

## Exercise 1: Process Management

### Goal
Practice process listing, background execution, and signal sending.

### Steps

**Step 1.1: Check currently running processes**
```bash
# Processes in the current terminal
ps aux | head -20

# View process relationships in tree format
ps auxf | head -30
```

**Step 1.2: Run a background process**
```bash
# Run a sleep process in the background
sleep 300 &
echo "PID: $!"

# Check background jobs
jobs -l
```

**Step 1.3: Send a signal to a process**
```bash
# Get the process ID
SLEEP_PID=$(pgrep -f "sleep 300")
echo "Sleep PID: $SLEEP_PID"

# Request termination with SIGTERM
kill $SLEEP_PID

# Verify the process has terminated
ps aux | grep "sleep 300" | grep -v grep
```

<details>
<summary>Need a hint?</summary>

- Use `kill -l` to see a list of available signals
- `kill -9 PID` forcefully terminates with SIGKILL
- `pkill -f "pattern"` allows name-based termination
</details>

### Verification
```bash
# The sleep process should not exist
pgrep -f "sleep 300" && echo "Still running" || echo "Termination complete"
```

---

## Exercise 2: Linux Namespace Isolation

### Goal
Create namespaces to observe process and network isolation.

### Steps

**Step 2.1: Verify PID namespace isolation**
```bash
# Run bash in a new PID namespace
sudo unshare --pid --fork --mount-proc bash -c '
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
# Create a network namespace
sudo ip netns add test-ns

# List namespaces
sudo ip netns list

# Check network inside the isolated namespace
sudo ip netns exec test-ns ip addr

# Cleanup
sudo ip netns delete test-ns
```

<details>
<summary>Need a hint?</summary>

- Host network interfaces are not visible inside the network namespace
- Only the `lo` (loopback) interface exists, and it's DOWN by default
- This is the principle behind container network isolation
</details>

### Verification
```bash
# Verify the namespace has been deleted
sudo ip netns list | grep test-ns && echo "Still exists" || echo "Deletion complete"
```

---

## Exercise 3: cgroup Resource Limits

### Goal
Use cgroups to limit process memory usage.

### Steps

**Step 3.1: Check cgroup information**
```bash
# Check cgroup v2 mount
mount | grep cgroup

# Check cgroup of current process
cat /proc/self/cgroup

# Check cgroup controllers
cat /sys/fs/cgroup/cgroup.controllers 2>/dev/null || echo "Using cgroup v1"
```

**Step 3.2: Check memory usage**
```bash
# System memory information
free -h

# Memory usage of specific processes
ps aux --sort=-%mem | head -10
```

**Step 3.3: Connection to Kubernetes resource limits**
```bash
# This is how resources.limits works in K8s
# Let's look at a Pod manifest example
cat << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: memory-demo
spec:
  containers:
  - name: memory-demo
    image: nginx
    resources:
      requests:
        memory: "64Mi"
      limits:
        memory: "128Mi"
EOF
```

<details>
<summary>Need a hint?</summary>

- K8s `resources.limits.memory` is translated to cgroup memory limits for the container
- Exceeding the limit results in OOMKilled status
- You can check resource limits with `kubectl describe pod`
</details>

---

## Exercise 4: File Permission Management

### Goal
Practice managing file permissions and ownership.

### Steps

**Step 4.1: Create a file and check permissions**
```bash
# Create a test file
mkdir -p /tmp/linux-lab
echo "Hello Linux" > /tmp/linux-lab/test.txt

# Check current permissions
ls -la /tmp/linux-lab/test.txt
```

**Step 4.2: Change permissions**
```bash
# Add execute permission
chmod +x /tmp/linux-lab/test.txt
ls -la /tmp/linux-lab/test.txt

# Set with numeric mode (read/write - read - none)
chmod 640 /tmp/linux-lab/test.txt
ls -la /tmp/linux-lab/test.txt

# Set the same permissions as K8s Secret volume defaults
chmod 0644 /tmp/linux-lab/test.txt
```

**Step 4.3: Change ownership**
```bash
# Check current user and group
id

# Change group (if executable)
sudo chown $USER:root /tmp/linux-lab/test.txt
ls -la /tmp/linux-lab/test.txt
```

### Verification
```bash
# Verify permissions are -rw-r--r--
stat -c "%a %U %G" /tmp/linux-lab/test.txt
```

---

## Cleanup
```bash
# Delete test files
rm -rf /tmp/linux-lab

# Clean up remaining processes
pkill -f "sleep 300" 2>/dev/null
```

## Troubleshooting

<details>
<summary>The unshare command is not found</summary>

Install the `util-linux` package:
```bash
sudo apt-get install util-linux   # Ubuntu/Debian
sudo yum install util-linux       # CentOS/RHEL
```
</details>

<details>
<summary>The ip netns command does not work</summary>

The `iproute2` package is required:
```bash
sudo apt-get install iproute2     # Ubuntu/Debian
sudo yum install iproute          # CentOS/RHEL
```
</details>

## Next Steps
- [Linux Basics Quiz](../../quizzes/basics/01-linux-basics-quiz.md)
- [Linux Advanced Skills Lab](./02-linux-advanced-lab.md)

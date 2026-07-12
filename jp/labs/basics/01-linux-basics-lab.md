# Linux Basics Lab Guide

> **難易度**: 初級
> **推定時間**: 45 分
> **最終更新**: February 11, 2026

## Learning Objectives
- Linux のプロセス管理コマンドを練習する
- Linux namespaces の分離効果を直接確認する
- cgroups を通じてリソース制限を理解する
- ファイルのパーミッションと所有権の管理を練習する

## Prerequisites
- [ ] Linux ターミナルへのアクセス（Ubuntu 20.04+ 推奨）
- [ ] sudo 権限
- [ ] [Linux Basics](../../basics/01-linux-basics.md) の学習を完了していること

---

## Exercise 1: Process Management

### Goal
プロセス一覧表示、バックグラウンド実行、シグナル送信を練習します。

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
<summary>ヒントが必要ですか？</summary>

- `kill -l` を使うと、利用可能なシグナルの一覧を確認できます
- `kill -9 PID` は SIGKILL で強制終了します
- `pkill -f "pattern"` を使うと、名前ベースで終了できます
</details>

### Verification
```bash
# The sleep process should not exist
pgrep -f "sleep 300" && echo "Still running" || echo "Termination complete"
```

---

## Exercise 2: Linux Namespace Isolation

### Goal
namespaces を作成し、プロセスとネットワークの分離を確認します。

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
<summary>ヒントが必要ですか？</summary>

- ホストのネットワークインターフェイスは network namespace 内では表示されません
- `lo`（loopback）インターフェイスのみが存在し、デフォルトでは DOWN です
- これはコンテナのネットワーク分離の基礎となる仕組みです
</details>

### Verification
```bash
# Verify the namespace has been deleted
sudo ip netns list | grep test-ns && echo "Still exists" || echo "Deletion complete"
```

---

## Exercise 3: cgroup Resource Limits

### Goal
cgroups を使用してプロセスのメモリ使用量を制限します。

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
<summary>ヒントが必要ですか？</summary>

- K8s の `resources.limits.memory` はコンテナの cgroup メモリ制限に変換されます
- 制限を超えると OOMKilled ステータスになります
- リソース制限は `kubectl describe pod` で確認できます
</details>

---

## Exercise 4: File Permission Management

### Goal
ファイルのパーミッションと所有権の管理を練習します。

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
<summary>unshare コマンドが見つかりません</summary>

`util-linux` パッケージをインストールします:
```bash
sudo apt-get install util-linux   # Ubuntu/Debian
sudo yum install util-linux       # CentOS/RHEL
```
</details>

<details>
<summary>ip netns コマンドが動作しません</summary>

`iproute2` パッケージが必要です:
```bash
sudo apt-get install iproute2     # Ubuntu/Debian
sudo yum install iproute          # CentOS/RHEL
```
</details>

## Next Steps
- [Linux Basics Quiz](../../quizzes/basics/01-linux-basics-quiz.md)
- [Linux Advanced Skills Lab](./02-linux-advanced-lab.md)

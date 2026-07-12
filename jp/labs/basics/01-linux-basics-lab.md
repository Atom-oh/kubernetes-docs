# Linux 基礎ラボガイド

> **難易度**: 初級
> **推定時間**: 45分
> **最終更新**: February 11, 2026

## 学習目標
- Linux のプロセス管理コマンドを練習する
- Linux namespace（名前空間）による分離効果を直接観察する
- cgroups を通じて resource limits（リソース制限）を理解する
- ファイル権限と所有権の管理を練習する

## 前提条件
- [ ] Linux terminal へのアクセス（Ubuntu 20.04+ 推奨）
- [ ] sudo 権限
- [ ] [Linux 基礎](../../basics/01-linux-basics.md) の学習完了

---

## 演習 1: プロセス管理

### 目標
プロセスの一覧表示、バックグラウンド実行、signal 送信を練習します。

### 手順

**ステップ 1.1: 現在実行中のプロセスを確認する**
```bash
# Processes in the current terminal
ps aux | head -20

# View process relationships in tree format
ps auxf | head -30
```

**ステップ 1.2: バックグラウンドプロセスを実行する**
```bash
# Run a sleep process in the background
sleep 300 &
echo "PID: $!"

# Check background jobs
jobs -l
```

**ステップ 1.3: プロセスに signal を送信する**
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

- `kill -l` を使用して利用可能な signals の一覧を確認する
- `kill -9 PID` は SIGKILL で強制終了する
- `pkill -f "pattern"` を使用すると名前ベースで終了できる
</details>

### 検証
```bash
# The sleep process should not exist
pgrep -f "sleep 300" && echo "Still running" || echo "Termination complete"
```

---

## 演習 2: Linux Namespace 分離

### 目標
namespaces を作成して、プロセスとネットワークの分離を観察します。

### 手順

**ステップ 2.1: PID namespace 分離を確認する**
```bash
# Run bash in a new PID namespace
sudo unshare --pid --fork --mount-proc bash -c '
echo "PID list inside the new namespace:"
ps aux
echo "Current process PID: $$"
'
```

期待される出力:
```
PID list inside the new namespace:
USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1  0.0  0.0   ...   ...  ...      S    ...    0:00 bash -c ...
root         2  0.0  0.0   ...   ...  ...      R    ...    0:00 ps aux
Current process PID: 1
```

**ステップ 2.2: Network namespace 分離**
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

- ホストの network interface は network namespace 内では表示されない
- `lo` (loopback) interface のみが存在し、デフォルトでは DOWN になっている
- これは container の network 分離の原理です
</details>

### 検証
```bash
# Verify the namespace has been deleted
sudo ip netns list | grep test-ns && echo "Still exists" || echo "Deletion complete"
```

---

## 演習 3: cgroup Resource Limits

### 目標
cgroups を使用してプロセスのメモリ使用量を制限します。

### 手順

**ステップ 3.1: cgroup 情報を確認する**
```bash
# Check cgroup v2 mount
mount | grep cgroup

# Check cgroup of current process
cat /proc/self/cgroup

# Check cgroup controllers
cat /sys/fs/cgroup/cgroup.controllers 2>/dev/null || echo "Using cgroup v1"
```

**ステップ 3.2: メモリ使用量を確認する**
```bash
# System memory information
free -h

# Memory usage of specific processes
ps aux --sort=-%mem | head -10
```

**ステップ 3.3: Kubernetes resource limits との関連**
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

- K8s `resources.limits.memory` は container の cgroup memory limits に変換される
- limit を超えると OOMKilled status になる
- `kubectl describe pod` で resource limits を確認できる
</details>

---

## 演習 4: ファイル権限管理

### 目標
ファイル権限と所有権の管理を練習します。

### 手順

**ステップ 4.1: ファイルを作成して権限を確認する**
```bash
# Create a test file
mkdir -p /tmp/linux-lab
echo "Hello Linux" > /tmp/linux-lab/test.txt

# Check current permissions
ls -la /tmp/linux-lab/test.txt
```

**ステップ 4.2: 権限を変更する**
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

**ステップ 4.3: 所有権を変更する**
```bash
# Check current user and group
id

# Change group (if executable)
sudo chown $USER:root /tmp/linux-lab/test.txt
ls -la /tmp/linux-lab/test.txt
```

### 検証
```bash
# Verify permissions are -rw-r--r--
stat -c "%a %U %G" /tmp/linux-lab/test.txt
```

---

## クリーンアップ
```bash
# Delete test files
rm -rf /tmp/linux-lab

# Clean up remaining processes
pkill -f "sleep 300" 2>/dev/null
```

## トラブルシューティング

<details>
<summary>`unshare` コマンドが見つからない</summary>

`util-linux` パッケージをインストールします:
```bash
sudo apt-get install util-linux   # Ubuntu/Debian
sudo yum install util-linux       # CentOS/RHEL
```
</details>

<details>
<summary>`ip netns` コマンドが動作しない</summary>

`iproute2` パッケージが必要です:
```bash
sudo apt-get install iproute2     # Ubuntu/Debian
sudo yum install iproute          # CentOS/RHEL
```
</details>

## 次のステップ
- [Linux 基礎クイズ](../../quizzes/basics/01-linux-basics-quiz.md)
- [Linux 応用スキルラボ](./02-linux-advanced-lab.md)

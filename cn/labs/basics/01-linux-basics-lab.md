# Linux 基础实验指南

> **难度**: 初级
> **预计时间**: 45 分钟
> **最后更新**: February 11, 2026

## 学习目标
- 练习 Linux 进程管理命令
- 直接观察 Linux namespace（命名空间）的隔离效果
- 通过 cgroups 理解资源限制
- 练习文件权限和所有权管理

## 前置条件
- [ ] 可访问 Linux 终端（推荐 Ubuntu 20.04+）
- [ ] sudo 权限
- [ ] 已完成 [Linux 基础](../../basics/01-linux-basics.md) 学习

---

## 练习 1: 进程管理

### 目标
练习进程列表查看、后台执行和信号发送。

### 步骤

**步骤 1.1: 检查当前运行的进程**
```bash
# Processes in the current terminal
ps aux | head -20

# View process relationships in tree format
ps auxf | head -30
```

**步骤 1.2: 运行后台进程**
```bash
# Run a sleep process in the background
sleep 300 &
echo "PID: $!"

# Check background jobs
jobs -l
```

**步骤 1.3: 向进程发送信号**
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
<summary>需要提示？</summary>

- 使用 `kill -l` 查看可用信号列表
- `kill -9 PID` 使用 SIGKILL 强制终止
- `pkill -f "pattern"` 允许基于名称终止
</details>

### 验证
```bash
# The sleep process should not exist
pgrep -f "sleep 300" && echo "Still running" || echo "Termination complete"
```

---

## 练习 2: Linux Namespace 隔离

### 目标
创建 namespaces 以观察进程和网络隔离。

### 步骤

**步骤 2.1: 验证 PID namespace 隔离**
```bash
# Run bash in a new PID namespace
sudo unshare --pid --fork --mount-proc bash -c '
echo "PID list inside the new namespace:"
ps aux
echo "Current process PID: $$"
'
```

预期输出：
```
PID list inside the new namespace:
USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1  0.0  0.0   ...   ...  ...      S    ...    0:00 bash -c ...
root         2  0.0  0.0   ...   ...  ...      R    ...    0:00 ps aux
Current process PID: 1
```

**步骤 2.2: Network namespace 隔离**
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
<summary>需要提示？</summary>

- 在 network namespace 内部看不到主机网络接口
- 只有 `lo` (loopback) 接口存在，并且默认处于 DOWN 状态
- 这是容器网络隔离背后的原理
</details>

### 验证
```bash
# Verify the namespace has been deleted
sudo ip netns list | grep test-ns && echo "Still exists" || echo "Deletion complete"
```

---

## 练习 3: cgroup 资源限制

### 目标
使用 cgroups 限制进程内存使用量。

### 步骤

**步骤 3.1: 检查 cgroup 信息**
```bash
# Check cgroup v2 mount
mount | grep cgroup

# Check cgroup of current process
cat /proc/self/cgroup

# Check cgroup controllers
cat /sys/fs/cgroup/cgroup.controllers 2>/dev/null || echo "Using cgroup v1"
```

**步骤 3.2: 检查内存使用情况**
```bash
# System memory information
free -h

# Memory usage of specific processes
ps aux --sort=-%mem | head -10
```

**步骤 3.3: 与 Kubernetes 资源限制的关联**
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
<summary>需要提示？</summary>

- K8s `resources.limits.memory` 会被转换为容器的 cgroup 内存限制
- 超过限制会导致 OOMKilled 状态
- 可以使用 `kubectl describe pod` 检查资源限制
</details>

---

## 练习 4: 文件权限管理

### 目标
练习管理文件权限和所有权。

### 步骤

**步骤 4.1: 创建文件并检查权限**
```bash
# Create a test file
mkdir -p /tmp/linux-lab
echo "Hello Linux" > /tmp/linux-lab/test.txt

# Check current permissions
ls -la /tmp/linux-lab/test.txt
```

**步骤 4.2: 更改权限**
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

**步骤 4.3: 更改所有权**
```bash
# Check current user and group
id

# Change group (if executable)
sudo chown $USER:root /tmp/linux-lab/test.txt
ls -la /tmp/linux-lab/test.txt
```

### 验证
```bash
# Verify permissions are -rw-r--r--
stat -c "%a %U %G" /tmp/linux-lab/test.txt
```

---

## 清理
```bash
# Delete test files
rm -rf /tmp/linux-lab

# Clean up remaining processes
pkill -f "sleep 300" 2>/dev/null
```

## 故障排除

<details>
<summary>未找到 unshare 命令</summary>

安装 `util-linux` 包：
```bash
sudo apt-get install util-linux   # Ubuntu/Debian
sudo yum install util-linux       # CentOS/RHEL
```
</details>

<details>
<summary>ip netns 命令无法工作</summary>

需要 `iproute2` 包：
```bash
sudo apt-get install iproute2     # Ubuntu/Debian
sudo yum install iproute          # CentOS/RHEL
```
</details>

## 后续步骤
- [Linux 基础测验](../../quizzes/basics/01-linux-basics-quiz.md)
- [Linux 高级技能实验](./02-linux-advanced-lab.md)

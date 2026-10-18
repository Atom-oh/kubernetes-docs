# Linux 基础实验指南

> **难度**：初级
> **预计时间**：45 分钟
> **最后更新**：2026 年 10 月 16 日

## 学习目标
- 练习 Linux 进程管理命令
- 直接观察 Linux 命名空间的隔离效果
- 通过 cgroup 了解资源限制
- 练习文件权限和所有权管理

## 前提条件
- [ ] 一台已维护的 Linux VM，配备 Bash、systemd 和 cgroup v2，供练习 3 使用
- [ ] 工具：coreutils、procps/procps-ng、util-linux、iproute2/iproute 和 Python3
- [ ] sudo 权限
- [ ] 已完成 [Linux 基础知识](../../basics/01-linux-basics.md)学习

请在同一个 Bash 终端中按顺序运行各代码块，以便实验变量保持可用。请使用隔离的 VM 进行 sudo 命名空间/cgroup 练习。即使使用 sudo，容器或受限环境也可能缺少所需的能力。以下输出仅供参考；本次审查未执行需要特权的练习。

---

## 练习 1：进程管理

### 目标
练习列出进程、后台运行和发送信号。

### 步骤

**步骤 1.1：检查当前正在运行的进程**
```bash
# Snapshot of processes visible in the current PID namespace
ps aux | head -20

# View process relationships in tree format
ps auxf | head -30
```

**步骤 1.2：运行后台进程**
```bash
sleep 300 &
LINUX_LAB_SLEEP_PID=$!
printf 'Lab child PID: %s\n' "$LINUX_LAB_SLEEP_PID"
jobs -l
```

**步骤 1.3：向进程发送信号**
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
<summary>需要提示吗？</summary>

- 使用 `kill -l` 查看可用信号列表
- `kill -9 PID` 会使用 SIGKILL 强制终止进程
- 使用 `$!` 保存 PID；按名称模式匹配可能会匹配到无关任务。
</details>

### 验证
```bash
printf 'Recorded lab child exit status: %s\n' "${LINUX_LAB_EXIT_STATUS:?Complete Step 1.3}"
jobs -l
```

---

## 练习 2：Linux 命名空间隔离

### 目标
创建命名空间，以观察进程和网络隔离。

### 步骤

**步骤 2.1：验证 PID 命名空间隔离**
```bash
# Run bash in a new PID namespace
sudo unshare --mount --pid --fork --mount-proc bash -c '
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

**步骤 2.2：网络命名空间隔离**
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
<summary>需要提示吗？</summary>

- 主机网络接口在网络命名空间内不可见
- 其中只有 `lo`（环回）接口，且默认处于 DOWN 状态
- 这就是容器网络隔离背后的原理
</details>

### 验证
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

删除已命名的 netns 句柄不会终止进程，也不会销毁仍被进程/文件描述符持有的命名空间。本示例会等待 `ip addr` 命令完成后再进行清理。

## 练习 3：cgroup 资源限制

### 目标
使用 cgroup 限制进程的内存使用量。

### 步骤

**步骤 3.1：检查 cgroup 信息**
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

**步骤 3.2：检查内存使用量**
```bash
# System memory information
free -h

# Memory usage of specific processes
ps aux --sort=-%mem | head -10
```

**步骤 3.3：为临时服务应用限制**

在具有 systemd 且 cgroup v2 中启用了内存控制器的 VM 上，此操作会创建一个自动命名的服务，将最大内存设为128MiB，且不允许使用交换空间。它会访问16MiB 的内存，不会刻意造成 OOM；随后 `--wait --collect` 会等待任务完成并卸载临时单元。祖先级限制可能更严格。

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

配置的 `memory.max` 对于128M 应为134217728 字节；分配量为16777216 字节。这些是配置/算术预期值，并非本次审查测得的结果。接下来的清单只会被打印出来，不会创建 Kubernetes Pod。

**步骤 3.4：与 Kubernetes 资源限制的联系**
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
    image: nginx:1.30.6
    resources:
      requests:
        memory: "64Mi"
      limits:
        memory: "128Mi"
EOF
```

<details>
<summary>需要提示吗？</summary>

- 对于 Linux 容器，运行时/kubelet 会配置内存 cgroup 限制。
- 根据内存分配情况和 OOM 组策略，内存压力可能导致回收、分配失败或 OOM 终止。因 OOM 终止的容器可能会报告 `OOMKilled`；并非每次分配失败都会产生此状态。
- `kubectl describe pod` 会显示请求的限制和记录的容器终止状态，但不能证明发生过每一种内核内存事件。
</details>

---

## 练习 4：文件权限管理

### 目标
练习管理文件权限和所有权。

### 步骤

**步骤 4.1：创建文件并检查权限**
```bash
LINUX_LAB_DIR=$(mktemp -d /tmp/k8s-docs-linux-basics.XXXXXX)
: "${LINUX_LAB_DIR:?mktemp failed}"
printf 'Hello Linux\n' > "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
ls -ld "$LINUX_LAB_DIR"
ls -l "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
```

**步骤 4.2：更改权限**
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

添加执行位并不会让任意文本变成有效程序。只要允许遍历目录，模式0644 就包含授予组用户/其他用户的读取权限；本实验中的私有 mktemp 目录会限制访问。Kubernetes Secret 卷默认权限为0644，但实际密钥权限必须符合使用它的用户/组及所需的访问级别。

**步骤 4.3：更改所有权**
```bash
id
# Demonstrate an owner change only on the private lab file, then restore it.
sudo chown "root:$(id -g)" "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
stat -c '%a %U %G' "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
sudo chown "$(id -u):$(id -g)" "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
```

### 验证
```bash
# Expect mode644 and the restored user/group
stat -c "%a %U %G" "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
```

---

## 清理
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

## 故障排查

<details>
<summary>找不到 unshare 命令</summary>

安装 `util-linux` 软件包：
```bash
sudo apt-get install util-linux   # Ubuntu/Debian
sudo dnf install util-linux       # Fedora/RHEL
```
</details>

<details>
<summary>ip netns 命令无法运行</summary>

需要安装 `iproute2` 软件包：
```bash
sudo apt-get install iproute2     # Ubuntu/Debian
sudo dnf install iproute          # Fedora/RHEL
```
</details>


## 参考资料和验证范围

* [systemd-run](https://www.freedesktop.org/software/systemd/man/latest/systemd-run.html)
* [systemd 内存资源控制](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html)
* [内核 cgroup v2 内存控制器](https://docs.kernel.org/admin-guide/cgroup-v2.html)
* [unshare](https://man7.org/linux/man-pages/man1/unshare.1.html)
* [ip netns](https://man7.org/linux/man-pages/man8/ip-netns.8.html)
* [GNU mktemp 手册](https://man7.org/linux/man-pages/man1/mktemp.1.html)

本次审查仅运行了隔离的非特权进程/文件检查和语法检查。未执行命名空间创建、所有权更改以及 cgroup/systemd 操作。

## 后续步骤
- [Linux 基础知识测验](../../quizzes/basics/01-linux-basics-quiz.md)
- [Linux 高级技能实验](./02-linux-advanced-lab.md)

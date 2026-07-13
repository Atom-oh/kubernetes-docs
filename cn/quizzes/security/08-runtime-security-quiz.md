# 运行时安全测验

本测验考查你对 Falco、Seccomp、AppArmor、基于 eBPF 的安全以及 EKS 运行时安全的理解。

## 测验问题

### 1. Falco 使用什么技术检测运行时威胁？

A. 网络数据包分析
B. 系统调用（syscall）监控
C. 日志分析
D. 内存扫描

<details>
<summary>显示答案</summary>

**答案：B. 系统调用（syscall）监控**

**解释：**
Falco 使用 eBPF 或内核模块在内核级别监控系统调用。它实时检测进程执行、文件访问和网络连接等活动。

</details>

### 2. Seccomp 的主要功能是什么？

A. 网络流量过滤
B. 限制进程可以发起的系统调用
C. 文件系统加密
D. 用户身份验证

<details>
<summary>显示答案</summary>

**答案：B. 限制进程可以发起的系统调用**

**解释：**
Seccomp（Secure Computing Mode）使用白名单方式限制进程可以发起的系统调用。如果进程尝试未经授权的 syscall，则该进程会被终止。

</details>

### 3. Kubernetes 1.27+ 中推荐的默认 Seccomp profile 是什么？

A. Unconfined
B. RuntimeDefault
C. Localhost
D. Docker/default

<details>
<summary>显示答案</summary>

**答案：B. RuntimeDefault**

**解释：**
RuntimeDefault 是由容器运行时（containerd、CRI-O）提供的默认 Seccomp profile：
```yaml
securityContext:
  seccompProfile:
    type: RuntimeDefault
```

它为大多数工作负载提供适当的安全级别。

</details>

### 4. Falco 规则中的 priority 字段有什么作用？

A. 确定规则执行顺序
B. 指定告警的严重级别
C. 设置资源配额
D. 设置日志保留期限

<details>
<summary>显示答案</summary>

**答案：B. 指定告警的严重级别**

**解释：**
Falco 规则中的 priority 指定检测到的事件的严重级别：
- EMERGENCY, ALERT, CRITICAL, ERROR
- WARNING, NOTICE, INFORMATIONAL, DEBUG

```yaml
- rule: Shell in Container
  priority: WARNING
```

</details>

### 5. AppArmor 的 complain mode 会发生什么？

A. 阻止所有访问
B. 仅记录策略违规
C. 禁用 profile
D. 仅发送告警

<details>
<summary>显示答案</summary>

**答案：B. 仅记录策略违规**

**解释：**
AppArmor mode：
- **enforce**：发生策略违规时阻止并记录日志
- **complain**：发生策略违规时仅记录日志（用于调试）
- **unconfined**：未应用 profile

Complain mode 对测试新的 profile 很有用。

</details>

### 6. 哪一项不是 Amazon GuardDuty EKS Runtime Monitoring 检测到的威胁？

A. 加密货币挖矿
B. 权限提升
C. 代码质量问题
D. Container 逃逸尝试

<details>
<summary>显示答案</summary>

**答案：C. 代码质量问题**

**解释：**
GuardDuty EKS Runtime Monitoring 检测类型：
- PrivilegeEscalation
- Execution（恶意代码）
- CryptoCurrency（挖矿）
- CredentialAccess
- DefenseEvasion

代码质量是开发质量问题，不是安全威胁。

</details>

### 7. Cilium Tetragon 的主要功能是什么？

A. Container image 扫描
B. 基于 eBPF 的安全可观测性
C. 网络策略管理
D. Secrets 管理

<details>
<summary>显示答案</summary>

**答案：B. 基于 eBPF 的安全可观测性**

**解释：**
Tetragon 是 Cilium 基于 eBPF 的安全可观测性工具：
- 进程执行监控
- 网络活动跟踪
- 文件访问监控
- 基于策略的实时响应（例如，进程终止）

</details>

### 8. 在 Falco 中，什么条件会检测 container 内的 shell 执行？

A. container and shell_procs
B. spawned_process and container and shell_procs
C. exec and shell
D. process.name = bash

<details>
<summary>显示答案</summary>

**答案：B. spawned_process and container and shell_procs**

**解释：**
Falco 规则示例：
```yaml
- rule: Shell in Container
  condition: >
    spawned_process and
    container and
    shell_procs
  output: "Shell spawned in container"
  priority: WARNING
```

`spawned_process` 表示创建新进程，`container` 表示 container 环境，`shell_procs` 表示 shell 进程（bash、sh 等）。

</details>

### 9. 如何为 Pod 设置只读 root filesystem？

A. readOnlyRootFilesystem: true
B. rootfs: readonly
C. filesystem.readonly: true
D. immutableRoot: true

<details>
<summary>显示答案</summary>

**答案：A. readOnlyRootFilesystem: true**

**解释：**
```yaml
securityContext:
  readOnlyRootFilesystem: true
```

此设置会使 container 的 root filesystem 变为只读，从而防止恶意代码修改文件。为需要写入访问的路径挂载 emptyDir volume。

</details>

### 10. 在运行时安全中，“Defense in Depth” 策略是什么意思？

A. 依赖单一安全层
B. 应用多个重叠的安全层
C. 只关注防御
D. 只保护外部边界

<details>
<summary>显示答案</summary>

**答案：B. 应用多个重叠的安全层**

**解释：**
Defense in Depth 使用多个安全层：
1. 构建时：Image 扫描、漏洞分析
2. 部署时：Admission Control、PSS/PSA
3. 运行时：Falco、Seccomp、AppArmor

如果一层被突破，其他层会提供保护。

</details>

### 11. 哪个命令会显示 Hubble 中被策略阻止的流量？

A. hubble observe --blocked
B. hubble observe --verdict DROPPED
C. hubble observe --denied
D. hubble observe --policy-violation

<details>
<summary>显示答案</summary>

**答案：B. hubble observe --verdict DROPPED**

**解释：**
```bash
hubble observe --verdict DROPPED
```

`--verdict DROPPED` 会过滤被网络策略拒绝的流量。你可以实时监控和分析策略违规。

</details>

### 12. 哪一项不是运行时安全最佳实践？

A. 将 RuntimeDefault Seccomp 应用于所有工作负载
B. 在所有 node 上将 Falco 部署为 DaemonSet
C. 以 root 身份运行 container
D. 使用只读 root filesystem

<details>
<summary>显示答案</summary>

**答案：C. 以 root 身份运行 container**

**解释：**
运行时安全最佳实践：
- 应用 RuntimeDefault Seccomp
- 部署 Falco
- 只读 root filesystem
- **以非 root 用户运行**（runAsNonRoot: true）
- 移除不必要的 capabilities
- 启用 GuardDuty runtime monitoring

以 root 身份运行很危险，因为 container 逃逸会在 host 上获得提升后的权限。

</details>

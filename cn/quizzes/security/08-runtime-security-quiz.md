# 运行时安全测验

> **最近更新**：October 16, 2026

本测验用于测试你对 Falco、Seccomp、AppArmor、基于 eBPF 的安全机制以及 EKS 运行时安全的理解。

## 测验题目

### 1. Falco 使用什么技术来检测运行时威胁？

- A. 网络数据包分析
- B. 系统调用（syscall）监控
- C. 日志分析
- D. 内存扫描

<details>
<summary>显示答案</summary>

**答案：B. 系统调用（syscall）监控**

**说明：**
Falco 通常会根据规则评估 Linux syscall 事件；插件也可以提供其他事件源。在 0.45.0 中，容器字段来自容器插件。请确认 modern_ebpf 对内核/BTF 的要求以及元数据收集情况。

</details>

### 2. Seccomp 的主要功能是什么？

- A. 过滤网络流量
- B. 限制进程可执行的系统调用
- C. 文件系统加密
- D. 用户身份验证

<details>
<summary>显示答案</summary>

**答案：B. 限制进程可执行的系统调用**

**说明：**
Seccomp 会过滤系统调用。根据配置文件中的操作，被拒绝的调用可以返回 ERRNO、终止进程或发出通知；它并不总是会杀死进程。

</details>

### 3. Kubernetes 1.27+ 推荐的默认 Seccomp 配置文件是什么？

- A. Unconfined
- B. RuntimeDefault
- C. Localhost
- D. Docker/default

<details>
<summary>显示答案</summary>

**答案：B. RuntimeDefault**

**说明：**
RuntimeDefault 是由容器运行时提供的配置文件。请显式设置 seccompProfile，或确认 kubelet seccompDefault 配置。仅使用 Kubernetes 1.27+ 并不会自动将其应用于每个 Pod。

</details>

### 4. Falco 规则中 priority 字段的作用是什么？

- A. 确定规则的执行顺序
- B. 指定警报的严重性级别
- C. 设置资源配额
- D. 设置日志保留期限

<details>
<summary>显示答案</summary>

**答案：B. 指定警报的严重性级别**

**说明：**
priority 表示事件严重性，而不是评估顺序。标准级别包括 EMERGENCY、ALERT、CRITICAL、ERROR、WARNING、NOTICE、INFORMATIONAL 和 DEBUG。完整的规则还需要 desc、condition 和 output 等字段。

</details>

### 5. AppArmor 的 complain 模式下会发生什么？

- A. 阻止所有访问
- B. 记录一般违规；显式 deny 仍可能阻止访问
- C. 禁用配置文件
- D. 只发送警报

<details>
<summary>显示答案</summary>

**答案：B. 记录一般违规；显式 deny 仍可能阻止访问**

**说明：**
Complain 模式通常会记录策略违规，同时允许相关操作，但显式 deny 规则仍可能阻止访问。它并不意味着无条件允许所有访问。请确认内核支持情况以及已加载的配置文件。

</details>

### 6. 以下哪项不是 Amazon GuardDuty EKS Runtime Monitoring 检测的威胁？

- A. 加密货币挖矿
- B. 权限提升
- C. 代码质量问题
- D. 容器逃逸尝试

<details>
<summary>显示答案</summary>

**答案：C. 代码质量问题**

**说明：**
GuardDuty Runtime Monitoring 检测的是安全威胁，而非代码质量缺陷。目前 EKS 支持 EC2 和 Auto Mode，但不包括 EKS Hybrid Nodes 和 EKS Fargate。请检查操作系统/内核/代理要求以及覆盖运行状况。

</details>

### 7. Cilium Tetragon 的主要功能是什么？

- A. 容器镜像扫描
- B. 基于 eBPF 的安全可观测性
- C. 网络策略管理
- D. 密钥管理

<details>
<summary>显示答案</summary>

**答案：B. 基于 eBPF 的安全可观测性**

**说明：**
Tetragon 提供进程事件、文件/网络钩子以及受支持的操作。它不要求安装 Cilium CNI。请确认钩子支持情况、选择器范围和误报情况；在启用强制执行之前，先测试 Post/monitor 行为。

</details>

### 8. Falco 中的哪个条件可以检测容器内执行 shell？

- A. container and shell_procs
- B. spawned_process and container and shell_procs
- C. exec and shell
- D. process.name = bash

<details>
<summary>显示答案</summary>

**答案：B. spawned_process and container and shell_procs**

**说明：**
此表达式依赖规则集中已加载的 spawned_process、container 和 shell_procs 宏。执行 shell 可能是合法操作，并不能证明系统已遭入侵。本指南定义了相互独立的宏和唯一的规则名称。

</details>

### 9. 如何为 Pod 设置只读根文件系统？

- A. readOnlyRootFilesystem: true
- B. rootfs: readonly
- C. filesystem.readonly: true
- D. immutableRoot: true

<details>
<summary>显示答案</summary>

**答案：A. readOnlyRootFilesystem: true**

**说明：**
readOnlyRootFilesystem 属于容器的 securityContext。可以单独提供可写卷或 /tmp。它无法阻止对可写卷的恶意利用、网络访问或内存攻击。

</details>

### 10. 运行时安全中的“纵深防御”策略是什么意思？

- A. 依赖单一安全层
- B. 应用多个相互重叠的安全层
- C. 只关注防御
- D. 只保护外部边界

<details>
<summary>显示答案</summary>

**答案：B. 应用多个相互重叠的安全层**

**说明：**
结合多种控制措施，同时检查每一层的适用范围和失效模式。镜像/签名检查、准入/权限控制、seccomp/AppArmor、运行时检测、网络控制和恢复措施可以相互补充；仅仅安装更多工具并不能提供保证。

</details>

<span id="_11-what-command-shows-traffic-blocked-by-policies-in-hubble"></span>

### 11. 哪条 Hubble 命令可以筛选被丢弃的流量？

- A. hubble observe --blocked
- B. hubble observe --verdict DROPPED
- C. hubble observe --denied
- D. hubble observe --policy-violation

<details>
<summary>显示答案</summary>

**答案：B. hubble observe --verdict DROPPED**

**说明：**
--verdict DROPPED 用于筛选被丢弃的流量。并非所有丢弃都由 NetworkPolicy 拒绝造成；请检查丢弃原因和策略判定。仅凭该选项无法确定原问题所暗示的、由策略导致的具体原因。

</details>

### 12. 以下哪项不是运行时安全最佳实践？

- A. 检查工作负载兼容性后使用 RuntimeDefault
- B. 确认 Falco 在受支持的节点上正常收集数据
- C. 以 root 身份运行容器
- D. 使用只读根文件系统

<details>
<summary>显示答案</summary>

**答案：C. 以 root 身份运行容器**

**说明：**
减少不必要的 root 权限。RuntimeDefault 和 readOnlyRootFilesystem 仍需与工作负载/节点兼容。Falco DaemonSet 无法在 Fargate 等所有节点类型上运行。启用功能和确认 GuardDuty 覆盖正常是两项不同的检查。

</details>

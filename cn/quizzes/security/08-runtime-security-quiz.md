# 运行时安全测验

> **最后更新**: September 13, 2026

本测验测试你对 Falco、Seccomp、AppArmor、基于 eBPF 的安全以及 EKS 运行时安全的理解。

## 测验题目

### 1. Falco 使用哪种技术来检测运行时威胁？

- A. 网络数据包分析
- B. 系统调用（syscall）监控
- C. 日志分析
- D. 内存扫描

<details>
<summary>显示答案</summary>

**答案：B. 系统调用（syscall）监控**

**解析：**
Falco 通常根据规则评估 Linux syscall 事件；插件可以提供其他事件源。在 0.44.1 中，container 字段来自 container 插件。请确认 modern_ebpf 的内核/BTF 要求以及元数据采集情况。

</details>

### 2. Seccomp 的主要功能是什么？

- A. 网络流量过滤
- B. 限制进程可以发起的系统调用
- C. 文件系统加密
- D. 用户身份认证

<details>
<summary>显示答案</summary>

**答案：B. 限制进程可以发起的系统调用**

**解析：**
Seccomp 过滤系统调用。根据配置文件（profile）中的动作，拒绝行为可能返回 ERRNO、终止进程或发出通知；它并不总是终止进程。

</details>

### 3. 在 Kubernetes 1.27+ 中推荐的默认 Seccomp profile 是什么？

- A. Unconfined
- B. RuntimeDefault
- C. Localhost
- D. Docker/default

<details>
<summary>显示答案</summary>

**答案：B. RuntimeDefault**

**解析：**
RuntimeDefault 是由容器运行时提供的 profile。请显式设置 seccompProfile，或确认 kubelet 的 seccompDefault 配置。仅仅使用 Kubernetes 1.27+ 并不会自动将其应用到每个 Pod。

</details>

### 4. Falco 规则中 priority 字段的作用是什么？

- A. 决定规则的执行顺序
- B. 指定告警的严重级别
- C. 设置资源配额
- D. 设置日志保留期限

<details>
<summary>显示答案</summary>

**答案：B. 指定告警的严重级别**

**解析：**
priority 表示事件严重级别，而不是评估顺序。标准级别为 EMERGENCY、ALERT、CRITICAL、ERROR、WARNING、NOTICE、INFORMATIONAL 和 DEBUG。一条完整的规则还需要 desc、condition 和 output 等字段。

</details>

### 5. AppArmor 的 complain 模式下会发生什么？

- A. 阻止所有访问
- B. 记录一般性违规；显式 deny 仍然可以阻止访问
- C. 禁用 profile
- D. 仅发送告警

<details>
<summary>显示答案</summary>

**答案：B. 记录一般性违规；显式 deny 仍然可以阻止访问**

**解析：**
Complain 模式通常在允许操作的同时记录策略违规，但显式的 deny 规则仍然可以阻止访问。它并非无条件允许所有访问。请确认内核支持情况以及已加载的 profile。

</details>

### 6. 以下哪一项不是 Amazon GuardDuty EKS Runtime Monitoring 检测的威胁？

- A. 加密货币挖矿
- B. 权限提升
- C. 代码质量问题
- D. 容器逃逸尝试

<details>
<summary>显示答案</summary>

**答案：C. 代码质量问题**

**解析：**
GuardDuty Runtime Monitoring 检测安全威胁，而不是代码质量缺陷。当前对 EKS 的支持涵盖 EC2 和 Auto Mode，但不包括 EKS Hybrid Nodes 和 EKS Fargate。请检查操作系统/内核/代理的要求以及覆盖健康状况。

</details>

### 7. Cilium Tetragon 的主要功能是什么？

- A. 容器镜像扫描
- B. 基于 eBPF 的安全可观测性
- C. 网络策略管理
- D. Secrets 管理

<details>
<summary>显示答案</summary>

**答案：B. 基于 eBPF 的安全可观测性**

**解析：**
Tetragon 提供进程事件、文件/网络钩子以及受支持的动作。它不要求安装 Cilium CNI。请确认钩子支持情况、选择器范围和误报情况；在实施强制阻断之前先测试 Post/监控行为。

</details>

### 8. 在 Falco 中，哪个 condition 可以检测容器内的 shell 执行？

- A. container and shell_procs
- B. spawned_process and container and shell_procs
- C. exec and shell
- D. process.name = bash

<details>
<summary>显示答案</summary>

**答案：B. spawned_process and container and shell_procs**

**解析：**
该表达式依赖于规则集中已加载的 spawned_process、container 和 shell_procs 宏。shell 可能是合法的，并不能证明系统已被入侵。本指南定义了独立的宏和唯一的规则名称。

</details>

### 9. 如何为 Pod 设置只读根文件系统？

- A. readOnlyRootFilesystem: true
- B. rootfs: readonly
- C. filesystem.readonly: true
- D. immutableRoot: true

<details>
<summary>显示答案</summary>

**答案：A. readOnlyRootFilesystem: true**

**解析：**
readOnlyRootFilesystem 属于容器的 securityContext。可以单独提供可写卷或 /tmp。它无法防止对可写卷、网络访问或内存的恶意使用。

</details>

### 10. 在运行时安全中，"纵深防御（Defense in Depth）"策略意味着什么？

- A. 依赖单一安全层
- B. 应用多个相互重叠的安全层
- C. 只关注防御
- D. 只保护外部边界

<details>
<summary>显示答案</summary>

**答案：B. 应用多个相互重叠的安全层**

**解析：**
在组合各种控制手段时，要检查每一层的适用范围和失效模式。镜像/签名检查、准入控制/权限、seccomp/AppArmor、运行时检测、网络以及恢复能力相互补充；仅仅安装更多工具并不能提供保障。

</details>

<span id="_11-what-command-shows-traffic-blocked-by-policies-in-hubble"></span>

### 11. 哪个 Hubble 命令可以过滤被丢弃的流量？

- A. hubble observe --blocked
- B. hubble observe --verdict DROPPED
- C. hubble observe --denied
- D. hubble observe --policy-violation

<details>
<summary>显示答案</summary>

**答案：B. hubble observe --verdict DROPPED**

**解析：**
--verdict DROPPED 用于筛选被丢弃的流量。并非每次丢包都是 NetworkPolicy 拒绝导致的；请检查丢包原因和策略判定结果。仅凭该选项无法确定原题所暗示的特定策略原因。

</details>

### 12. 以下哪一项不是运行时安全的最佳实践？

- A. 在检查工作负载兼容性后使用 RuntimeDefault
- B. 在受支持的节点上验证 Falco 的采集情况
- C. 以 root 身份运行容器
- D. 使用只读根文件系统

<details>
<summary>显示答案</summary>

**答案：C. 以 root 身份运行容器**

**解析：**
应减少不必要的 root 权限。RuntimeDefault 和 readOnlyRootFilesystem 仍然需要工作负载/节点的兼容性。Falco DaemonSet 无法在所有类型的节点上运行，例如 Fargate。功能的启用与 GuardDuty 覆盖的健康状况是两项独立的检查。

</details>

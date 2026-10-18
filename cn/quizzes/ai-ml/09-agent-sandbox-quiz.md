# EKS 上的 Agent Sandbox 测验

本测验检查 Agent Sandbox v1.0.6 API（`v1beta1`）及其默认设置在 Amazon EKS 上的行为。相关章节：[EKS 上的 Agent Sandbox](../../ai-ml/09-agent-sandbox.md)。

## 选择题

### 1. Agent Sandbox 本身提供什么机制来隔离不可信代码？

- A. 为每个 Sandbox 内置微型虚拟机监控程序
- B. 对 Pod 进行编排；隔离由 Pod 的 `RuntimeClass` 提供（例如 gVisor 或 Kata Containers）
- C. 提供一个 seccomp 配置文件，使 `runc` 能安全运行任何不可信代码
- D. 自动将 Pod 放置到专用 EC2 实例上

<details>
<summary>显示答案</summary>

**答案：B. 对 Pod 进行编排；隔离由 Pod 的 `RuntimeClass` 提供（例如 gVisor 或 Kata Containers）**

**说明：**
该项目将自身描述为沙箱编排器。其威胁模型通过建议使用 `runtimeClassName` 选择安全运行时来降低容器逃逸风险；最好在 `SandboxTemplate` 中设置该字段，以免用户将其移除。使用默认的 `runc` 时，沙箱代码与节点共用内核。

</details>

### 2. 模板未设置 `networkPolicy`，并保留 `networkPolicyManagement: Managed`。关于生成的策略，哪项说法正确？

- A. 允许所有出站流量，包括到 CoreDNS 的流量
- B. 只允许来自 `agent-sandbox-system` 中 `sandbox-router` Pod 的入站流量，并允许到非私有 IPv4 和 IPv6 网段的出站流量；不允许访问 CoreDNS
- C. 允许来自同一命名空间内所有 Pod 的入站流量
- D. 只允许到 VPC CIDR 的出站流量

<details>
<summary>显示答案</summary>

**答案：B. 只允许来自 `agent-sandbox-system` 中 `sandbox-router` Pod 的入站流量，并允许到非私有 IPv4 和 IPv6 网段的出站流量；不允许访问 CoreDNS**

**说明：**
默认策略会从 `0.0.0.0/0` 中排除 `10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16` 和 `169.254.0.0/16`，并从 `::/0` 中排除 `fc00::/7` 和 `fe80::/10`。阻止访问 CoreDNS 是为了防止内部服务发现；因此，在更改策略或 Pod 的解析器之前，无法解析公共主机名。

</details>

### 3. 在 IPv4 EKS 集群中，除非添加例外规则，否则沙箱在默认托管策略下仍能访问哪个地址？

- A. IMDS 地址 `169.254.169.254`
- B. EKS Pod Identity Agent 地址 `169.254.170.23`
- C. 位于 VPC CNI 自定义联网所用辅助 CIDR `100.64.0.0/10` 中的 Pod
- D. 地址为 `10.0.12.34` 的 Pod

<details>
<summary>显示答案</summary>

**答案：C. 位于 VPC CNI 自定义联网所用辅助 CIDR `100.64.0.0/10` 中的 Pod**

**说明：**
默认例外列表仅涵盖 RFC1918 和链路本地网段。`100.64.0.0/10` 不属于 RFC1918，因此该网段中的内部地址会匹配允许 `0.0.0.0/0` 的规则。IMDS 和 Pod Identity Agent 位于 `169.254.0.0/16`，而 `10.0.12.34` 位于 `10.0.0.0/8`，因此这三者都会被阻止。在 IPv6 集群中情况有所不同：IPv4 规则会被忽略，VPC 全局单播地址不会被排除，而且不会过滤通过 `ENABLE_V4_EGRESS` 的 IPv4 出站流量。

</details>

### 4. `agent-orchestrator` 命名空间中的代理 Pod 使用 SDK 的集群内模式，直接连接由托管策略模板创建的沙箱 Pod。会发生什么？

- A. 连接成功，因为集群内流量从不经过过滤
- B. 连接会被阻止，直到模板策略为该命名空间添加入站规则（且 CNI 会强制执行该策略）
- C. 只有通过 IPv6 才能连接
- D. SDK 会自动回退到公共 Gateway

<details>
<summary>显示答案</summary>

**答案：B. 连接会被阻止，直到模板策略为该命名空间添加入站规则（且 CNI 会强制执行该策略）**

**说明：**
默认入站规则只允许路由器。通过 Service DNS 或 Pod IP 直接连接会绕过路由器，因此需要明确添加入站规则。在 EKS 上，这假定 VPC CNI 已启用网络策略强制执行；如果未启用，策略不会阻止任何流量。

</details>

### 5. 哪些 `SandboxClaim` 字段会强制冷启动，而不是采用预热的 Sandbox？

- A. `warmPoolRef`
- B. `lifecycle.shutdownTime`
- C. `env` 或 `volumeClaimTemplates`
- D. `lifecycle.ttlSecondsAfterFinished`

<details>
<summary>显示答案</summary>

**答案：C. `env` 或 `volumeClaimTemplates`**

**说明：**
环境变量和卷必须在创建 Pod 前就已存在，而预热的 Pod 已经创建。因此，设置其中任一字段的 claim 都会根据池的模板冷启动创建。模板还必须允许注入这些内容：`envVarsInjectionPolicy` 和 `volumeClaimTemplatesPolicy` 的默认值均为 `Disallowed`。

</details>

### 6. 希望在 EKS 上使用 Kata Containers，但不使用裸金属实例。哪种方案符合文档所述能力？

- A. 使用带自定义 containerd 运行时的 EKS Auto Mode
- B. 使用 Fargate，因为每个 Pod 已在虚拟机中运行，并且在那里会强制执行托管网络策略
- C. 使用 Karpenter v1.13.0+，在受支持的实例系列（例如 M8i、C8i 或 R8i）上设置 `EC2NodeClass.spec.cpuOptions.nestedVirtualization: enabled`，并将 RuntimeClass 绑定到这些节点
- D. 使用任意 Graviton 实例，因为它们都支持嵌套虚拟化

<details>
<summary>显示答案</summary>

**答案：C. 使用 Karpenter v1.13.0+，在受支持的实例系列（例如 M8i、C8i 或 R8i）上设置 `EC2NodeClass.spec.cpuOptions.nestedVirtualization: enabled`，并将 RuntimeClass 绑定到这些节点**

**说明：**
EC2 在特定的 Intel 实例系列上支持嵌套虚拟化（包括 M7i/C7i/R7i、M8i/C8i/R8i 等）。Karpenter 会筛选出报告支持 `nested-virtualization` 的实例类型。Auto Mode 管理 AMI 和容器运行时，因此无法在其中添加 Kata。VPC CNI 无法对 Fargate Pod 应用网络策略。应使用 `scheduling` 绑定 RuntimeClass，使 Pod 只会调度到已准备好的节点上。

</details>

### 7. 将 `operatingMode` 从 `Running` 更改为 `Suspended` 后，Sandbox 会发生什么？

- A. Sandbox 对象、Pod 和 PVC 都会被删除
- B. Pod 会被删除；Sandbox 对象及其 PVC 保留，`Suspended` 条件会从 `PodTerminating` 变为 `PodTerminated`
- C. Pod 会被冻结在同一节点的内存中
- D. 只有无头 Service 会被删除

<details>
<summary>显示答案</summary>

**答案：B. Pod 会被删除；Sandbox 对象及其 PVC 保留，`Suspended` 条件会从 `PodTerminating` 变为 `PodTerminated`**

**说明：**
挂起机制基于 PVC：计算资源停止，但存储保留。`Ready` 会变为 False，原因是 `SandboxSuspended`。在 EKS 上，EBS 卷属于可用区，因此恢复后的 Pod 必须调度到卷所在的可用区。

</details>

### 8. 将运行 Agent Sandbox v0.4.x 的集群升级到 v1.0.6 之前，必须做什么？

- A. 无需操作；执行 v1.0.6 的 `kubectl apply` 会自动转换对象
- B. 先升级到 v0.5.2 或更高版本，将已存储的对象迁移到 `v1beta1`，并确认每个 CRD 的 `status.storedVersions` 只列出 `v1beta1`
- C. 删除所有 CRD 并重新创建
- D. 在 v1.0.6 中重新启用转换 webhook

<details>
<summary>显示答案</summary>

**答案：B. 先升级到 v0.5.2 或更高版本，将已存储的对象迁移到 `v1beta1`，并确认每个 CRD 的 `status.storedVersions` 只列出 `v1beta1`**

**说明：**
v1.0.0 移除了 `v1alpha1` 和转换 webhook，且不支持从低于 v0.5.0 的版本直接升级。如果 `storedVersions` 中仍包含 `v1alpha1`，API 服务器会拒绝升级。删除 CRD 会级联删除所有 Sandbox、claim、模板和池。

</details>

### 9. 需要通过 `sandbox-router` 访问沙箱的浏览器。哪种设计符合本章的 EKS 指导？

- A. 使用类型为 `LoadBalancer` 的 `Service` 和面向互联网的 NLB，并采用路由器默认的 `AllowAll` 授权器
- B. CloudFront → CloudFront VPC origin → 内部 ALB → `sandbox-router-svc`，并使用作用域令牌 v2 授权，在 ALB 或 Envoy 层实施速率限制
- C. 为每个沙箱 Pod 分配公共 IP
- D. 在生产环境中让每位用户都从自己的笔记本电脑进行端口转发

<details>
<summary>显示答案</summary>

**答案：B. CloudFront → CloudFront VPC origin → 内部 ALB → `sandbox-router-svc`，并使用作用域令牌 v2 授权，在 ALB 或 Envoy 层实施速率限制**

**说明：**
只有 CloudFront 是公共端点；ALB 位于内部，其安全组只允许 CloudFront VPC origin 安全组或托管前缀列表中的流量。路由器默认的授权器是 `AllowAll`，并且不会限制 WebSocket 等已升级连接的数量，因此必须在暴露服务前配置授权和限制。

</details>

### 10. 对于名称为 70 个字符且 `spec.service: true` 的 Sandbox，v1.0.6 有何变化？

- A. 没有变化；它会像以前一样继续运行
- B. CEL 规则会在准入时拒绝它；对于已有对象，在取消设置 `spec.service` 或以不超过 63 个字符的名称重新创建 Sandbox 之前，每次更新都会失败
- C. 控制器会自动截断 Service 名称
- D. Sandbox 会转换为 `v1alpha1`

<details>
<summary>显示答案</summary>

**答案：B. CEL 规则会在准入时拒绝它；对于已有对象，在取消设置 `spec.service` 或以不超过 63 个字符的名称重新创建 Sandbox 之前，每次更新都会失败**

**说明：**
无头 Service 使用 Sandbox 的名称，而 Service 名称必须是最长 63 个字符的 DNS-1035 标签，因此这类 Sandbox 一直无法变为 Ready。v1.0.6 会在准入时报告失败。该规则覆盖整个对象，并不豁免已有对象，因此状态更新也会失败。

</details>

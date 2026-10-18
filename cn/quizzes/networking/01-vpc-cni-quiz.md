# Amazon VPC CNI 测验

根据 [VPC CNI 指南](../../networking/01-vpc-cni.md)及其主要参考资料于 2026 年 9 月 11 日审阅。

## 1. 在标准 EKS Linux EC2 节点上，IPAMD 的作用是什么？

- A. 管理每个 Pod 的 DNS 应用设置
- B. 维护用于 Pod 网络的常规 ENI/IP 分配池
- C. 替代网络策略控制器
- D. 加密所有节点间流量

<details>
<summary>显示答案</summary>

**答案：B. 维护用于 Pod 网络的常规 ENI/IP 分配池**

容器运行时会调用 CNI 二进制文件，该文件会请求地址并配置 Pod 沙箱。IPAMD 负责维护相关地址池。Windows、Fargate 和 Auto Mode 的管理路径有所不同。

</details>

## 2. 次要 IP 模式与前缀模式的 IPv4 分配方式有何不同？

- A. 只有次要 IP 模式支持 IPv6
- B. 次要 IP 模式分配单个地址；IPv4 前缀模式分配包含 16 个地址的 /28 块
- C. 前缀模式会取消 kubelet 的 Pod 限制
- D. 前缀模式会在已耗尽的子网中创建空闲空间

<details>
<summary>显示答案</summary>

**答案：B. 次要 IP 模式分配单个地址；IPv4 前缀模式分配包含 16 个地址的 /28 块**

前缀模式需要受支持的硬件和连续地址块。分配仍会占用子网空间，而预留目标可能会保留未使用的地址。IPv6 使用 /80 前缀；EKS 不提供双栈 Pod/Service。

</details>

## 3. 旧版 m5.large 次要 IPv4 引导计算如何得出 29？

- A. Kubernetes 始终将所有节点限制为 29
- B. 3 × (10 − 1) + 2 = 29
- C. 3 × 10 − 3 = 29
- D. 29 是每个子网的大小

<details>
<summary>显示答案</summary>

**答案：B. 3 × (10 − 1) + 2 = 29**

共有 3 个 ENI，每个有 10 个 IPv4 地址槽位。扣除每个 ENI 的主地址槽位后，剩下 27 个常规次要地址；历史公式再加上 2 个使用主机网络的系统 Pod。这不是适用于所有情况的当前容量上限；前缀、SGPP、kubelet 上限和资源都会改变其含义。

</details>

## 4. WARM_IP_TARGET 指定什么？

- A. Pod 数量的硬性上限
- B. 可用于常规分配的空闲地址目标数量
- C. 集群范围的地址配额
- D. 地址 TTL

<details>
<summary>显示答案</summary>

**答案：B. 可用于常规分配的空闲地址目标数量**

MINIMUM_IP_TARGET 是已分配地址总数的下限。这些 IP 目标会覆盖预留 ENI/前缀策略；分配仍按前缀大小进行。应根据测得的需求、变更频率、地址空间和 API 行为选择取值。

</details>

## 5. 关于 EKS 原生网络策略，哪项说法正确？

- A. VPC CNI 内部运行 Calico
- B. 标准 eBPF 策略在 1.14 中引入，但仍须满足当前平台/版本和选择启用的条件
- C. 它会自动覆盖 Windows 和 Fargate
- D. 启用后即可保证对每个独立 Pod 可靠地实施策略

<details>
<summary>显示答案</summary>

**答案：B. 标准 eBPF 策略在 1.14 中引入，但仍须满足当前平台/版本和选择启用的条件**

经审阅的 1.23 设置使用已配置的策略控制器和 aws-eks-nodeagent。当前 EKS 指南涵盖 EC2 Linux、由控制器管理的 Pod，以及 Service/容器端口条件。标准启动模式会在解析规则期间允许流量；严格启动行为是另一项有意选择的设置。

</details>

## 6. 使用 ENIConfig 的自定义网络能提供什么？

- A. 一个替代 DNS 服务器
- B. 从选定子网/安全组分配 Pod 地址，使其与节点的默认配置不同
- C. 添加 CIDR 后自动迁移现有 Pod
- D. 自动移除重叠路由

<details>
<summary>显示答案</summary>

**答案：B. 从选定子网/安全组分配 Pod 地址，使其与节点的默认配置不同**

配置实际位于同一可用区的资源，启用自定义网络，并通过预期的节点标签/注释选择 ENIConfig。显式注释的优先级高于标签。仅创建新的 CIDR/子网不会迁移现有 Pod，也不会自动提供所有路由和权限。

</details>

## 7. 在符合条件的 EC2 节点上，SGPP 的 trunk 和 branch 接口如何工作？

- A. trunk 始终是主 eth0 接口
- B. 控制器会附加额外的 trunk ENI，并关联供选定 Pod 使用的 branch 接口
- C. 这两个名称分别表示 IPv4 和 IPv6
- D. 前缀委派会将 branch Pod 上限提高 16 倍

<details>
<summary>显示答案</summary>

**答案：B. 控制器会附加额外的 trunk ENI，并关联供选定 Pod 使用的 branch 接口**

trunk 是额外接口，不是主 ENI。前提条件包括受支持的实例类型、控制器/IAM 和实际的安全组规则。Fargate 使用单独的托管路径。SGPP 不支持 Windows/Auto Mode；EKS 服务指南则说明在其规定条件下支持 IPv6。

</details>

## 8. 以下哪项是不恰当的 IP 耗尽默认应对措施？

- A. 考虑前缀委派前，先检查连续前缀空间和硬件
- B. 容量不足时，规划添加 CIDR/子网并让工作负载采用这些资源
- C. 将所有工作负载切换为 hostNetwork，以绕过常规 Pod 地址分配
- D. 考虑自定义网络和基于测量结果调整预留目标

<details>
<summary>显示答案</summary>

**答案：C. 将所有工作负载切换为 hostNetwork，以绕过常规 Pod 地址分配**

将所有工作负载切换为 hostNetwork 会改变隔离和端口行为，并不是通用的容量解决方案。应分别诊断地址耗尽、前缀碎片、ENI 限制、kubelet 容量和 API 错误。前缀委派无法创建缺失的子网地址。

</details>

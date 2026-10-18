# Calico 简介测验

> **相关文档**：[Calico 简介](../../../networking/calico/01-introduction.md)
> **最后更新**：2026 年 9 月 12 日

## 测验

1. Project Calico 最初于哪一年启动？
   - A) 2012
   - B) 2014
   - C) 2016
   - D) 2018

<details>
<summary>显示答案</summary>

**答案：B) 2014**

**说明**：
Project Calico 于 2014 年起源于 Metaswitch。Tigera 于 2016 年成立。不要把项目的起源年份与之后的产品发布或 Calico 版本发布日期混为一谈。

</details>

2. 哪家公司是 Calico 的主要维护方，并提供 Calico Enterprise 和 Calico Cloud？
   - A) Google
   - B) Red Hat
   - C) Tigera
   - D) VMware

<details>
<summary>显示答案</summary>

**答案：C) Tigera**

**说明**：
Tigera 与社区贡献者共同维护 Calico，并提供商业产品。“Metaswitch 创始人”指的是一群人，并非题目所问的公司名称。Calico 出现在 CNCF Landscape 上，并不表示该项目由 CNCF 管治。

</details>

3. 以下哪项关于默认 Calico 安装的说法不正确？
   - A) 使用基于 BGP 的路由
   - B) 自动为每个 Pod 注入 Istio sidecar
   - C) 支持 Kubernetes 标准网络策略和扩展网络策略
   - D) 支持 eBPF dataplane

<details>
<summary>显示答案</summary>

**答案：B) 自动为每个 Pod 注入 Istio sidecar**

**说明**：
Calico 提供网络、策略和可选的数据平面。Mesh 集成是单独的功能或配置；本实验的安装不会自动注入 Istio sidecar。Cilium 的 mesh 功能也需要单独配置；比较 CNI 时，不应暗示所有 mesh 功能默认都已启用。

</details>

4. 正确配置 BGP 和 underlay 路由后，不封装的 Calico 拓扑可以提供什么？
   - A) 更简单的配置
   - B) 更好的安全加密
   - C) 在 underlay 支持 Pod 路由的情况下，无需 overlay 封装头即可路由
   - D) 内置 DNS 解析

<details>
<summary>显示答案</summary>

**答案：C) 在 underlay 支持 Pod 路由的情况下，无需 overlay 封装头即可路由**

**说明**：
BGP 用于分发路由。如果 underlay 能够路由 Pod 地址，且禁用了封装，数据包就不需要 IPIP/VXLAN 封装头。BGP 也可以与 IPIP 共存，因此仅启用 BGP 并不会取消封装。BGP 既不加密流量，也不保证所有工作负载都能降低延迟。

</details>

5. 在哪些环境中可以使用适当配置的 Calico 及相应产品版本？
   - A) 仅云环境
   - B) 仅本地部署环境
   - C) 云、本地部署和混合环境
   - D) 仅 Kubernetes，不支持 VM

<details>
<summary>显示答案</summary>

**答案：C) 云、本地部署和混合环境**

**说明**：
Calico 可用于云、本地部署和混合环境，但仍受平台、内核、数据平面和产品版本限制。GKE Dataplane V2 使用的是 Cilium，而不是 Calico。VM 和 Windows 的功能并不等同于 Linux Kubernetes 的功能。

</details>

6. 以下哪一项列出了受支持的 Calico Linux 数据平面选项？
   - A) 仅 iptables
   - B) 仅 eBPF
   - C) iptables、nftables 和 eBPF
   - D) 仅 IPVS

<details>
<summary>显示答案</summary>

**答案：C) iptables、nftables 和 eBPF**

**说明**：
Calico 支持这些 Linux 数据平面选项。VXLAN/IPIP 等封装模式属于另一类选择；IPVS 是 kube-proxy 后端，并非完整的 Calico 数据平面。应根据内核、平台和功能要求进行选择；本实验明确使用 iptables。

</details>

7. calicoctl 是什么？
   - A) Calico 图形界面
   - B) 用于管理 Calico 资源的命令行工具
   - C) Calico Kubernetes operator
   - D) 监控仪表板

<details>
<summary>显示答案</summary>

**答案：B) 用于管理 Calico 资源的命令行工具**

**说明**：
calicoctl 可管理 Calico 资源，并提供 IPAM/BGP 操作等诊断功能。请使用匹配的客户端版本。许多日常资源操作也可通过 Calico API server 使用 kubectl 完成。calicoctl node status 需要适当的节点环境；仅使用笔记本电脑上的 kubeconfig 并不足够。

</details>

8. Calico OSS 与 Calico Enterprise 有什么关系？
   - A) 两者完全独立，不共享任何代码
   - B) Calico Enterprise 是基于 Calico OSS 构建的商业版本
   - C) Calico OSS 已弃用，由 Calico Enterprise 取代
   - D) Calico Enterprise 只能与 Calico Cloud 配合使用

<details>
<summary>显示答案</summary>

**答案：B) Calico Enterprise 是基于 Calico OSS 构建的商业版本**

**说明**：
Enterprise 基于 Calico 技术构建，并提供商业功能和支持。开源版本也包含策略层级以及 Goldmane/Whisker 可观测性功能，并可用于生产环境。请查阅当前功能矩阵；不要假设所有高级功能都需要付费，也不要认为 OSS 只适用于小型集群。

</details>

9. Calico 在哪一年引入了 eBPF dataplane 支持？
   - A) 2018
   - B) 2019
   - C) 2020
   - D) 2022

<details>
<summary>显示答案</summary>

**答案：C) 2020**

**说明**：
官方在 2020 年 2 月 25 日发布的公告中，将新版数据平面作为 Calico 3.13 的技术预览版推出。这并不是 GA（正式可用版）公告。eBPF 在 Linux 内核中执行，可以替代常规数据包处理流程中的一部分，而不是替代内核本身。性能表现取决于实际测量的工作负载。

</details>

10. Calico Cloud 是什么？
   - A) 托管 Kubernetes 服务
   - B) 面向 Calico 网络安全的 SaaS 平台
   - C) 云存储解决方案
   - D) 面向 Kubernetes 的 CDN 服务

<details>
<summary>显示答案</summary>

**答案：B) 面向 Calico 网络安全的 SaaS 平台**

**说明**：
Calico Cloud 是 Tigera 提供的网络安全和可观测性 SaaS 服务。它不是 Kubernetes 托管服务、对象存储或 CDN。它的功能和职责与自管理的 Enterprise 不同；仍需配置与集群的集成。此前未经支持的 2022 年发布日期与这一定义无关，无需保留。

</details>

---

[返回学习材料](../../../networking/calico/01-introduction.md) | [下一份测验：架构](02-architecture-quiz.md)

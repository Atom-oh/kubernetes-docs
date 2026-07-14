# Calico 简介测验

> **相关文档**: [Calico 简介](../../../networking/calico/01-introduction.md)
> **最后更新**: February 22, 2026

## 测验

1. Project Calico 最初于哪一年启动？
   - A) 2012
   - B) 2014
   - C) 2016
   - D) 2018

<details>
<summary>显示答案</summary>

**答案：B) 2014**

**说明：**
Project Calico 于 2014 年在 Metaswitch 启动。此后，它已发展成为全球使用最广泛的 Kubernetes CNI plugin 之一。2016 年，Tigera 成立以将 Calico 商业化；2019 年，Calico Enterprise 发布。

</details>

2. 是哪家公司创立了 Tigera 并将 Calico 商业化？
   - A) Google
   - B) Red Hat
   - C) Metaswitch 创始人
   - D) VMware

<details>
<summary>显示答案</summary>

**答案：C) Metaswitch 创始人**

**说明：**
Tigera 由 Metaswitch 的 Project Calico 原始创建者于 2016 年创立。Tigera 现在同时维护开源 Calico 项目，并提供包括 Calico Enterprise 和 Calico Cloud 在内的商业产品。

</details>

3. 以下哪项不是 Calico 的核心功能？
   - A) 基于 BGP 的路由
   - B) 内置带 sidecar 注入的 service mesh
   - C) Kubernetes 标准和扩展网络策略
   - D) 支持 eBPF dataplane

<details>
<summary>显示答案</summary>

**答案：B) 内置带 sidecar 注入的 service mesh**

**说明：**
Calico 通过基于 BGP 的路由、强大的网络策略（包括 Kubernetes 标准策略和 Calico 扩展策略）以及 eBPF dataplane 支持，提供高性能网络能力。但与 Cilium 不同，Calico 不包含内置的 service mesh。可通过 Calico Enterprise 单独获得 service mesh 功能，或与 Istio 等其他 service mesh 解决方案集成。

</details>

4. 与传统 overlay network 相比，Calico 基于 BGP 的网络的主要优势是什么？
   - A) 配置更简单
   - B) 更好的安全加密
   - C) 无封装开销的直接路由
   - D) 内置 DNS 解析

<details>
<summary>显示答案</summary>

**答案：C) 无封装开销的直接路由**

**说明：**
Calico 中基于 BGP 的网络可让数据包在节点之间直接路由，无需承担封装（如 VXLAN 或 IPIP）开销。这可带来更好的网络性能、更低的延迟，并且更容易与现有网络基础设施集成。传统 overlay network 会添加封装头，从而增加数据包大小和处理开销。

</details>

5. Calico 支持哪些环境？
   - A) 仅云环境
   - B) 仅本地环境
   - C) 云环境、本地环境和混合环境
   - D) 仅 Kubernetes，不支持 VM

<details>
<summary>显示答案</summary>

**答案：C) 云环境、本地环境和混合环境**

**说明：**
Calico 是一套多功能网络解决方案，支持多种环境，包括公有云（AWS、Azure、GCP）、本地数据中心和混合部署。它还可用于 virtual machine 和 bare-metal workload，而不仅限于 Kubernetes container。

</details>

6. Calico 支持哪些 dataplane 选项？
   - A) 仅 iptables
   - B) 仅 eBPF
   - C) iptables 和 eBPF
   - D) 仅 IPVS

<details>
<summary>显示答案</summary>

**答案：C) iptables 和 eBPF**

**说明：**
Calico 同时支持 iptables 和 eBPF dataplane。iptables dataplane 是传统且最成熟的选项，而 eBPF 模式于 2020 年引入，可在降低 CPU 使用率的同时提升性能。用户可以选择最符合其要求和 kernel version 支持情况的 dataplane。

</details>

7. 什么是 calicoctl？
   - A) Calico 的图形用户界面
   - B) 用于管理 Calico resource 的 command-line tool
   - C) Calico 的 Kubernetes operator
   - D) 监控仪表板

<details>
<summary>显示答案</summary>

**答案：B) 用于管理 Calico resource 的 command-line tool**

**说明：**
calicoctl 是一个 command-line interface tool，用于管理 Calico resource，例如网络策略、IP pool、BGP configuration 和节点。它提供对 Calico datastore 的直接访问，对于仅通过 kubectl 可能难以完成的故障排除、诊断和高级配置任务至关重要。

</details>

8. Calico OSS 和 Calico Enterprise 之间有什么关系？
   - A) 它们是完全独立的产品，没有共享代码
   - B) Calico Enterprise 是构建在 Calico OSS 之上的商业版本
   - C) Calico OSS 已弃用，由 Calico Enterprise 取代
   - D) Calico Enterprise 仅能与 Calico Cloud 一起使用

<details>
<summary>显示答案</summary>

**答案：B) Calico Enterprise 是构建在 Calico OSS 之上的商业版本**

**说明：**
Calico Enterprise 是 Tigera 基于开源 Calico 项目打造的商业产品。它增加了高级威胁检测、合规报告、多集群管理和商业支持等企业功能。两个版本共享核心网络和策略功能。

</details>

9. Calico 于哪一年引入 eBPF dataplane 支持？
   - A) 2018
   - B) 2019
   - C) 2020
   - D) 2022

<details>
<summary>显示答案</summary>

**答案：C) 2020**

**说明：**
Calico 于 2020 年引入 eBPF dataplane 支持。这是一个重要里程碑，使 Calico 能够提供更好的性能，同时具备 Direct Server Return (DSR)、connection-time load balancing 和替代 kube-proxy 等功能，并且使用的 CPU 少于 iptables dataplane。

</details>

10. 什么是 Calico Cloud？
    - A) 一项托管 Kubernetes 服务
    - B) 用于 Calico 网络安全的 SaaS 平台
    - C) 云存储解决方案
    - D) 面向 Kubernetes 的 CDN 服务

<details>
<summary>显示答案</summary>

**答案：B) 用于 Calico 网络安全的 SaaS 平台**

**说明：**
Calico Cloud 于 2022 年推出，是 Tigera 提供的 SaaS（Software as a Service）产品，以托管服务的形式提供 Calico Enterprise 功能。它简化了高级网络安全、可观测性和合规功能的部署与管理，无需承担自行管理企业组件的运维开销。

</details>

---

[返回学习资料](../../../networking/calico/01-introduction.md) | [下一测验：架构](./02-architecture-quiz.md)

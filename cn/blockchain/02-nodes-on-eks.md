# 在 EKS 上运行区块链节点

> **支持版本**：Kubernetes 1.33+（Amazon EKS）、Hyperledger Fabric 2.5 / 3.x
> **最后更新**：2026 年 9 月 13 日

## 本文涵盖内容

- 将[基础知识](./01-fundamentals.md)中的运行特性转化为实际 Kubernetes 配置：StatefulSet、存储和 P2P 暴露
- 如何将同步状态纳入健康检查，以及普通健康检查为何不适用
- Ethereum 节点与 Hyperledger Fabric 的运行差异，以及如何管理硬分叉计划

## 开篇问题：应该在 EKS 上运行吗？

在讨论配置前，先考虑这个问题。**区块链节点并不适合 Kubernetes 的某些优势特性。**

| Kubernetes 擅长的能力 | 对区块链节点的影响 |
|---|---|
| 快速调度和重新调度 | 重建状态的成本很高，因此重新调度代价大 |
| 为提升吞吐量而横向扩展 | 副本可以提高聚合 RPC/读取能力和可用性，但不会自动提升基础链的写入/共识能力 |
| 声明式滚动更新 | 硬分叉需要同步切换 |
| 在节点之间迁移 Pod | 节点绑定本地磁盘 |

仍然有一些理由可以选择 EKS。

| 原因 | 说明 |
|---|---|
| **运维标准化** | 如果已有工作负载都在 EKS 上运行，避免另建一套技术栈会更好 |
| **多个链/环境** | 可以用相同方式管理主网、测试网和多种协议 |
| **与周边组件集成** | 索引器、API 网关和监控已经在集群中 |
| **Fabric 的官方方向** | Hyperledger Fabric 已有成熟的 Kubernetes Operator 生态 |

**如果**只有少数节点（1–3 个）且没有其他集群工作负载，那么普通 EC2 会更好。此时 EKS 的抽象增加了复杂性，却没有带来好处。运行单个验证者并不需要 EKS。

**决策标准**：**区块链节点周围是否还有其他工作负载**？如果索引器、API 和监控也在集群中，把节点放在一起是合理的；如果节点独立运行，EC2 更简单。

## 基础配置：StatefulSet 与 Headless Service

### 为什么不用 Deployment

| 要求 | Deployment | StatefulSet |
|---|---|---|
| 稳定名称（P2P 身份） | ✗ 随机后缀 | ✓ `node-0`、`node-1` |
| 每个 Pod 固定卷 | ✗ 共享或随机 | ✓ 通过 `volumeClaimTemplates` 为每个 Pod 提供独立 PVC |
| 稳定 DNS | ✗ | ✓ 配合 Headless Service，例如 `node-0.svc...` |
| 有序启动/关闭 | ✗ | ✓ |

[基础知识](./01-fundamentals.md)中的“稳定对等节点身份”和“每 Pod 独立状态”要求，正是 StatefulSet 能提供的能力。

### 不完整、仅供测试的结构（不是可部署清单）

此片段省略了必要的 StatefulSet selector/template 标签、镜像/参数、Headless Service、StorageClass，以及 Merge 后执行层（EL）/共识层（CL）Engine API/JWT 配置。不要直接应用。请在隔离的测试环境中补全并验证这些资源，**不得使用真实资金或验证者签名密钥**。JSON-RPC 和 Engine API 必须保持私有并经过身份验证；P2P 可达性不得暴露 RPC 或签名端点。

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: eth-node
spec:
  serviceName: eth-node          # headless Service name
  replicas: 2
  template:
    spec:
      terminationGracePeriodSeconds: 300   # graceful shutdown needs time
      containers:
        - name: execution
          # ... execution client
          ports:
            - { name: p2p-tcp, containerPort: 30303, protocol: TCP }
            - { name: p2p-udp, containerPort: 30303, protocol: UDP }
            - { name: rpc,     containerPort: 8545 }
          volumeMounts:
            - { name: data, mountPath: /data }
  volumeClaimTemplates:
    - metadata: { name: data }
      spec:
        accessModes: [ReadWriteOnce]
        storageClassName: gp3-high-iops
        resources: { requests: { storage: 2Ti } }
```

与普通工作负载相比，有三点不同。

**① `terminationGracePeriodSeconds` 较长。区块链客户端关闭时必须将内存状态刷新到磁盘**。强制终止可能会**损坏数据库并要求重新同步**。默认的 30 秒通常不够。

**② P2P 端口同时使用 TCP 和 UDP**。许多协议将发现过程（UDP）与实际连接（TCP）分开。只开放其中一种，就会无法发现对等节点或无法连接。

**③ 卷很大**。下文存储部分会详细说明。

## 存储：最重要的设计决策

### 瓶颈是什么

区块链节点的磁盘访问模式以**大量随机读写**为特点，因为遍历和更新状态 Trie（Merkle Patricia Trie 及类似结构）会访问分散的键。

因此，**IOPS 会先于容量成为瓶颈**。即使磁盘容量充足，只要 IOPS 不够，同步就会落后；落后的节点无法提供服务。

| 要求 | 原因 |
|---|---|
| **高 IOPS** | 随机访问模式 |
| **低延迟** | 状态查询位于区块处理路径上 |
| **持续吞吐量** | 负载持续存在，而非突发 |

### 选择 EBS 卷

| 卷类型 | 适用性 |
|---|---|
| **gp3** | 默认选择。关键优势是 **IOPS 和吞吐量可与容量分开设置** |
| **io2 / io2 Block Express** | 需要更高 IOPS 和更稳定延迟时使用 |
| **gp2** | 不推荐：IOPS 与容量绑定，无法单独调整 |
| **实例存储（NVMe）** | 速度最快，但**实例停止时数据会丢失**；仅在可以接受重新同步时使用 |

**gp3 独立设置的意义**：gp2 按单位容量固定 IOPS，因此提高 IOPS 就意味着购买不需要的额外容量。gp3 可分别设置容量和 IOPS，因此**可以按实际需求配置**。具体差异见 [EBS gp2 与 gp3 基准测试](../storage/01-ebs-gp2-gp3-benchmark.md)。

**实例存储的取舍**很明确：性能最好，但状态可能消失。如果可以接受重新同步所需时间（已有快照恢复流程），并且运行多个节点，确保其中一个节点重新同步时不会影响服务，就可以选择它。

### 容量规划：增长是关键

链数据会**持续增长**。这会改变容量规划的性质。

| 项目 | 影响 |
|---|---|
| 持续增长 | **必须制定卷扩容计划**；最终一定会用到 |
| 增长速率取决于协议活动 | 预留空间并设置告警 |
| 剪枝选项 | 客户端提供的模式可以丢弃旧数据；不需要归档数据时可使用 |

**EBS 卷支持在线扩容**（之后还要扩展文件系统），因此标准做法是设置 `allowVolumeExpansion: true` 的 StorageClass，并配置磁盘使用率告警。

### 官方硬件建议：EIP-7870

将 [EIP-7870](https://eips.ethereum.org/EIPS/eip-7870) 和[运行节点指南](https://ethereum.org/developers/docs/nodes-and-clients/run-a-node/)作为**初始建议**，而不是对某种 EKS 实例或 EBS 卷的保证。应根据所选客户端、分叉、剪枝方式和实测增长情况进行验证。

| 项目 | 最低要求 | **建议配置（EIP-7870，全节点）** |
|---|---|---|
| **CPU** | 2+ 核 | 4+ 核（**验证时 8+ 核**） |
| **RAM** | 16 GB（建议 32 GB） | 32 GB（**验证时 64 GB**） |
| **磁盘** | **2 TB NVMe SSD** | **4 TB NVMe SSD**（不建议使用无 DRAM 和 QLC 硬盘） |
| **带宽** | 25+ Mbit/s | 下载 50 Mbit/s / 上传 15+ Mbit/s（**验证时上传 25+ Mbit/s**） |

阅读这些建议时要注意三点。

**① 瓶颈在磁盘**。ethereum.org 明确指出：“硬件瓶颈主要是磁盘空间。同步 Ethereum 区块链的 I/O 强度很高。”这就是前文先讨论 IOPS 的原因。

**② EIP-7870 是硬件建议，并不能证明某个 EBS 配置满足要求**。EC2/EBS 延迟、实例带宽和卷 IOPS/吞吐量与本地 NVMe 不同。应使用选定客户端和存储配置测量同步及稳定状态处理情况。

**③ 2 TB 最低值有过期时间**。ethereum.org 指出 2 TB “可能在 2027 年被超过”，这正是**必须将增长纳入容量计划的原因**。

::: warning 需要核实
以上数值针对**全节点**。**归档节点需要更多存储空间，实际用量会因客户端、剪枝配置和分叉而异。**

特别是 Fusaka 的 PeerDAS 改变了 Blob 处理方式，因此请检查客户端当前版本的发行说明，并在 PoC 中**自行测量增长速率**。
:::

### 快照策略

如[基础知识](./01-fundamentals.md)所述，**链数据可以从网络重新获取，但这需要时间**。因此，备份的目的不是“保存数据”，而是“**缩短恢复时间**”。

| 方法 | 特点 |
|---|---|
| **EBS 快照** | 整个卷；恢复时应考虑初始化延迟（延迟加载） |
| **客户端快照导出** | 由客户端提供的导出；可明确其一致性保证 |
| **重新同步** | 不做备份，从头开始同步（需要时间） |

**注意**：直接对运行中节点的卷创建快照，可能会捕获到**正在写入的数据库**。要创建一致性快照，必须先停止客户端，或使用客户端提供的一致性机制。

## 健康检查：普通方式为何失效

忽略同步状态的健康检查可能会将应用流量发送到落后的节点。这是需要测试的设计风险，并非对运维错误频率的测量排名。

### 问题

普通健康检查会询问“进程是否有响应？”对区块链节点来说，这**既不充分，也有风险**。

落后于同步进度的节点：

- RPC 端口开放且有响应 → liveness 通过
- 但**根据过期的链状态作答** → 返回错误数据
- Service 将流量发给它 → 应用看到错误的余额和状态

### 正确的划分

| 探针 | 应检查什么 |
|---|---|
| **startup** | 初次同步正在进行且耗时较长，因此设置**较大的 `failureThreshold`** |
| **liveness** | 进程正在运行且有响应；**不要在此检查同步状态**（重启落后的节点会导致它永远无法追上） |
| **readiness** | 与链头相差不超过 N 个区块，即判断能否提供服务 |

**liveness/readiness 的区分至关重要。**

- 在 liveness 中检查同步 → 落后的节点被重启 → 越来越落后 → 无限循环
- 不在 readiness 中检查同步 → 落后的节点继续接收流量并返回错误结果

### 实施方向

通过客户端 RPC 检查同步状态。不同协议和客户端的方法不同，因此通常会使用包装脚本或 sidecar 来判断。

```yaml
# Conceptual form: the actual judgment logic differs per client
readinessProbe:
  exec:
    command: ["/bin/sh", "-c", "/scripts/check-sync.sh"]   # block delta vs head
  periodSeconds: 15
  failureThreshold: 3

livenessProbe:
  httpGet: { path: /, port: rpc }     # responsiveness only
  periodSeconds: 30
  failureThreshold: 5

startupProbe:
  exec:
    command: ["/bin/sh", "-c", "/scripts/check-alive.sh"]
  periodSeconds: 30
  failureThreshold: 240               # allow a long initial sync
```

**N 个区块的阈值必须根据应用要求设置**。应结合[基础知识](./01-fundamentals.md)中的确认深度共同决定。

## P2P 暴露：接受入站连接

### 为什么入站连接重要

只使用出站连接也能同步，但接受入站连接可以：

- 增加对等节点数量，让**传播更快、更稳定**
- 为网络做贡献（在公共链上有互惠作用）

这对验证者尤其重要：区块传播延迟会直接影响表现（奖励）。

### 方法与取舍

| 方法 | 特点 |
|---|---|
| **`hostNetwork: true`** | 最简单。Pod 直接使用节点 IP 和端口；每节点只能有一个，此项需要安全审核 |
| **`hostPort`** | 只映射指定端口到节点；必须逐节点管理端口冲突 |
| **NodePort Service** | Kubernetes 标准方式；有端口范围限制和节点 IP 通告问题 |
| **每 Pod 一个 LoadBalancer（NLB）** | 地址稳定；**每个 Pod 都产生负载均衡器成本** |
| **不开放入站** | 仅出站；配置简单，但对等节点质量下降 |

### 常见陷阱：通告地址

P2P 协议会向其他对等节点**通告**自身地址。如果容器内看到的地址（Pod IP）与外部可达地址（节点公网 IP、LB 地址）不同，**其他对等节点将无法连接**。

多数客户端提供了指定通告地址的选项（例如 `--nat extip:<addr>`）。**如果不设置此项，开放入站也不会带来对等节点**。这是“端口开放了，但什么也没发生”的经典原因。

每个 Pod 都必须通告不同地址，因此需要初始化逻辑，让每个 Pod 通过 StatefulSet 序号或 Downward API 获取自己的地址。

## 资源：持续负载，而不是突发负载

区块链节点会持续使用 **CPU 和 IOPS**。区块不断到来，验证持续进行，状态也持续更新。

| 项目 | 建议 |
|---|---|
| **CPU limit** | **谨慎设置**。节流会造成区块处理延迟；对验证者而言，表现与奖励挂钩。参见[内核调优](../kernel/03-eks-node-tuning.md)中的节流诊断 |
| **内存** | 客户端会使用大量内存作为状态缓存。**限额应留有余量**，因为 OOM 可能导致数据库损坏 |
| **request = limit** | Guaranteed QoS 会降低被驱逐的优先级 |
| **专用节点** | 通过 taint/toleration 与其他工作负载隔离，避免 noisy neighbor |
| **文件描述符** | 每个对等连接都需要套接字；考虑提高上限（参见[内核调优](../kernel/03-eks-node-tuning.md)） |

**CPU limit 的判断最重要**。如[内核文档](../kernel/01-container-primitives.md)所述，CPU limit 是带宽限制，因此在一个周期内用完配额会强制暂停。如果区块处理恰好落入这个周期，就会出现延迟，而验证者会错失机会。

专用节点可减少租户间争用，但 kubelet、CNI/CSI、可观测性和 OS 服务仍共用该节点。即使不设置应用 CPU limit，也要保留资源预留和余量；并在持续负载下测试延迟、同步和节点健康状况。

## Ethereum 节点：双客户端结构

Ethereum 转向 PoS 后，一个节点由**两个进程组成**。

| 客户端 | 作用 | 示例 |
|---|---|---|
| **执行客户端（EL）** | 交易执行、状态管理、EVM | Geth、Nethermind、Besu、Erigon、Reth |
| **共识客户端（CL）** | PoS 共识、区块提议和证明 | Prysm、Lighthouse、Teku、Nimbus、Lodestar |

它们通过 **Engine API** 通信，并共享一个 JWT 密钥。

### 部署位置的选择

| 方案 | 优缺点 |
|---|---|
| **同一 Pod 中运行两个容器** | 可以简单地通过 `localhost` 通信，一起调度和重启；资源请求合并计算 |
| **分开的 StatefulSet** | 可独立扩缩容和升级；需要管理 Engine API 连接 |

**默认选择一个 Pod**：两个客户端按 1:1 配对运行，Engine API 延迟会影响性能，因此在一个 Pod 内使用 `localhost` 很自然。

**客户端多样性**也值得考虑。为了避免某个客户端的错误影响整个网络，社区建议分散使用不同客户端。如果运行多个节点，采用**不同的客户端组合**可以提高防御能力。

### 近期对协议产生运行影响的变更

以下是**有日期的协议事件**，并非未来固定更新周期。规划升级前，请检查[路线图](https://ethereum.org/roadmap/)、激活公告和所选客户端发行说明。

| 日期 | 升级 | 运行影响 |
|---|---|---|
| **2025 年 5 月 7 日** | 主网 **Pectra** | EIP-7251 将符合条件的验证者最高有效余额提高到 2,048 ETH；合并会改变验证者记录，但不一定改变进程/虚拟机数量 |
| **2025 年 12 月 3 日** | 主网 **Fusaka**（epoch 411392） | 主要变化是 **PeerDAS**（Peer Data Availability Sampling，对等数据可用性采样）：通过采样而非完整获取来验证 Blob 数据，并扩大 Blob 吞吐量 |

验证者身份/密钥**并不等同于独立进程或虚拟机**：一个验证者客户端可以在共享信标节点架构上管理许多密钥。EIP-7251 合并可以减少验证者记录/密钥管理工作，但不能证明基础设施或成本会按比例减少。应测量实际客户端拓扑，并在密钥迁移期间保留防双签保护。

**PeerDAS 会影响存储和带宽规划**。Blob 处理方式的改变会影响节点保留和传输的数据量，因此应重新评估既有容量基线。

## Hyperledger Fabric：运行许可链

Fabric 的性质不同。作为一个**参与者已知的联盟链**，它的共识和运行特征也不同，详见[基础知识](./01-fundamentals.md)。

### 组件

| 组件 | 作用 | Kubernetes 部署位置 |
|---|---|---|
| **Peer** | 保存账本、运行 chaincode、验证交易 | StatefulSet + 持久卷 |
| **Orderer** | 使用已配置共识对交易排序：CFT Raft，或 Fabric 3.x 中的 SmartBFT | StatefulSet + 持久存储；Peer 验证决定哪些状态更新有效 |
| **CA**（Fabric CA） | 签发成员证书 | Deployment + 持久卷 |
| **Chaincode** | 智能合约 | 外部构建器或独立 Pod |

### 运行要点

**① Orderer 的持久卷不可或缺**。丢失 Raft 日志会破坏共识状态。更新时 Pod 会重启，因此**没有持久卷运行就会丢失数据**。

**② 证书管理是核心工作**。Fabric 通过 MSP（Membership Service Provider，成员服务提供者）管理组织和身份，所有通信均使用 TLS。需要管理：

- MSP 签名证书和密钥
- TLS 证书（分别用于 Peer、Orderer 和 CA）
- **过期管理**：证书过期会导致实际服务中断

证书过期是重要的中断风险，但本文没有提供发生频率数据。应监控并演练 MSP 和 TLS 凭证续期，并验证 Operator/客户端版本之间的兼容性。

**③ 使用 Operator**。Fabric 已形成 Kubernetes Operator 生态。

| Operator | 特点 |
|---|---|
| [hyperledger-labs/fabric-operator](https://github.com/hyperledger-labs/fabric-operator) | CNCF Operator 模式；将 CA、Peer、Orderer 和 Console 声明为 CR |
| [bevel-operator-fabric](https://github.com/hyperledger-bevel/bevel-operator-fabric) | 来自 Hyperledger Bevel 项目；支持 Fabric 2.3–3.x |

Operator 可将重复配置变成声明式资源应用。**建议从 Operator 开始，而不是手工拼装 YAML**，因为 Fabric 配置复杂，手工管理容易出错。

### Ethereum 与 Fabric 对比

| 项目 | Ethereum 节点 | Hyperledger Fabric |
|---|---|---|
| **参与方式** | 无许可 | 许可制（MSP） |
| **共识** | PoS | 已配置的 Orderer 模式：Raft（CFT）或 SmartBFT（Fabric 3.x） |
| **最终性** | 在协议假设下基于检查点 | 在共识假设下排序结果具有最终性；Peer 仍会验证交易，排序后的交易也可能无效 |
| **主要运维负担** | 同步、磁盘增长、硬分叉 | **证书过期**、通道和策略管理 |
| **P2P 暴露** | 建议开放入站 | 组织间连接（已知端点） |
| **存储增长** | 大且持续增长 | 相对较小（取决于交易量） |
| **升级** | 外部设定计划（硬分叉） | 由联盟共识决定 |

**最大的运行差异**：Ethereum 必须遵循**外部设定的时间表**（硬分叉），Fabric 则允许**联盟制定计划**。相应地，Fabric 需要成员之间达成一致的流程。

## 管理硬分叉计划

[基础知识](./01-fundamentals.md)将硬分叉称为“有截止时间的迁移”。实际操作步骤如下：

| 步骤 | 内容 |
|---|---|
| **1. 订阅信息** | 协议官方博客、客户端发行说明、Operator 社区 |
| **2. 登记日期** | 将分叉区块/时间写入团队日历。**设定留有余量的目标日期** |
| **3. 在测试网上验证** | 测试网先于主网分叉；先在那里验证 |
| **4. 准备镜像** | 在支持该分叉的版本上构建并扫描镜像 |
| **5. 按顺序升级** | 在分叉点**之前完成**；有多个节点时一次升级一个 |
| **6. 在分叉时监控** | 链高度、对等节点数量、是否识别到分叉 |
| **7. 事后验证** | 确认所有节点都处于同一条链上 |

运行不兼容客户端的节点可能停止跟随规范链，或在激活后发生分叉。应从多个独立可信来源比较**相同区块高度和最终性状态**，并考虑正常传播/同步延迟；不要把不相关的最新链头当作必须立即一致的结果。

## 监控

| 类别 | 指标 | 原因 |
|---|---|---|
| **同步** | 与链头的区块差值 | 判断节点能否提供服务的核心指标 |
| **同步** | 区块处理延迟 | 开始落后的早期信号 |
| **P2P** | 对等节点数 | 数量骤降意味着网络或配置问题 |
| **P2P** | 入站/出站比例 | 入站为零意味着暴露配置失败 |
| **存储** | 磁盘使用率和增长率 | 预测扩容时间 |
| **存储** | IOPS、队列深度、延迟 | 确认瓶颈 |
| **共识** | 重组发生次数 | 必须告知应用 |
| **验证者** | 参与率、错过的职责 | 直接关系到奖励 |
| **Fabric** | **距离证书过期的剩余时间** | 防止服务中断 |
| **资源** | CPU throttling（`nr_throttled`） | 参见[内核文档](../kernel/01-container-primitives.md) |

“**与链头的区块差值”是最重要的单一指标**。当它开始增大时，必须找到原因（IOPS、CPU、对等节点、网络）；超过阈值后，节点应退出 readiness。

## 总结

- **首先决定是否在 EKS 上运行**。标准是节点周围是否还有其他工作负载；节点独立运行时 EC2 更简单。
- **StatefulSet + Headless Service + 持久卷**是基础结构，并且 `terminationGracePeriodSeconds` 必须足够长（强制终止可能损坏数据库）。
- 存储方面，**IOPS 先于容量成为瓶颈**。gp3 可独立设置容量和 IOPS，这是它的关键优势；必须制定卷扩容计划。
- 分开检查进程存活和同步就绪，并分别测试；本章没有提供中断频率排名。
- 开放入站 P2P 时，**忘记通告地址就不会有对等节点连接**。
- 资源使用是持续的，而不是突发的。**使用专用节点，并谨慎决定 CPU limit。**
- Ethereum 使用 EL 和 CL 客户端；验证者身份/密钥与进程、虚拟机数量是不同概念。合并本身不能证明节省成本。
- Fabric 的主要运维负担是**证书过期**。建议从 Operator 开始并自动续期。
- 硬分叉后，**与其他节点和区块链浏览器比较区块哈希**，确认处于同一条链上。

下一步：[Amazon Managed Blockchain](./03-managed-blockchain.md)将探讨托管服务可以承担多少运维工作。

## 参考资料

- [Ethereum：运行节点](https://ethereum.org/developers/docs/nodes-and-clients/run-a-node/)
- [EIP-7870：硬件与带宽建议](https://eips.ethereum.org/EIPS/eip-7870)：官方硬件建议
- [Ethereum 路线图](https://ethereum.org/roadmap/) / [Pectra](https://ethereum.org/roadmap/pectra/) / [Fusaka](https://ethereum.org/roadmap/fusaka/)
- [Pectra 主网公告（Ethereum Foundation）](https://blog.ethereum.org/2025/04/23/pectra-mainnet)
- [Fusaka 主网公告（Ethereum Foundation）](https://blog.ethereum.org/2025/11/06/fusaka-mainnet-announcement)
- [Hyperledger Fabric：部署生产网络](https://hyperledger-fabric.readthedocs.io/en/latest/deployment_guide_overview.html)
- [hyperledger-labs/fabric-operator](https://github.com/hyperledger-labs/fabric-operator) / [bevel-operator-fabric](https://github.com/hyperledger-bevel/bevel-operator-fabric)
- [EBS gp2 与 gp3 基准测试](../storage/01-ebs-gp2-gp3-benchmark.md) / [EKS 节点内核调优](../kernel/03-eks-node-tuning.md)

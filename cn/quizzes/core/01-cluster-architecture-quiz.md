# 集群架构测验

本测验将检验你对 Kubernetes 集群架构、主要组件、通信路径和高可用配置的理解。

## 选择题

1. 以下哪一项不是 Kubernetes control plane 的核心组件？
   - A) kube-apiserver
   - B) etcd
   - C) kube-proxy
   - D) kube-scheduler
   
<details>

<summary>显示答案</summary>

**答案：C) kube-proxy**

**解释：**
kube-proxy 是节点组件，而不是 control plane 组件。control plane 的核心组件包括 kube-apiserver、etcd、kube-scheduler、kube-controller-manager 和 cloud-controller-manager。kube-proxy 在每个节点上运行，用于维护网络规则并执行连接转发。
</details>

2. Kubernetes 中哪个组件充当存储 Kubernetes API 状态的“事实来源”？
   - A) kube-apiserver
   - B) etcd
   - C) kube-controller-manager
   - D) kubelet
   
<details>

<summary>显示答案</summary>

**答案：B) etcd**

**解释：**
etcd 是一个一致且高度可用的键值存储，用于存储 Kubernetes API 状态，并充当 Kubernetes 的“事实来源”。所有集群状态、配置和元数据都存储在 etcd 中，其他所有 control plane 组件都通过 kube-apiserver 与 etcd 交互，以读取和写入信息。
</details>

3. 以下哪一项不是 Kubernetes 节点组件？
   - A) kubelet
   - B) kube-proxy
   - C) 容器运行时
   - D) kube-controller-manager
   
<details>

<summary>显示答案</summary>

**答案：D) kube-controller-manager**

**解释：**
kube-controller-manager 是 control plane 组件，而不是节点组件。节点组件包括 kubelet、kube-proxy 和容器运行时（containerd、CRI-O 等）。kube-controller-manager 在 control plane 上运行，执行各种控制器进程，例如 node controller 和 replication controller。
</details>

4. Kubernetes 中哪个 control plane 组件负责选择运行新建 Pod 的节点？
   - A) kube-apiserver
   - B) kube-scheduler
   - C) kubelet
   - D) kube-controller-manager
   
<details>

<summary>显示答案</summary>

**答案：B) kube-scheduler**

**解释：**
kube-scheduler 是负责选择运行新建 Pod 的节点的 control plane 组件。调度过程包括筛选（识别能够运行 Pod 的节点）和打分（为符合条件的节点分配分数），最后将 Pod 分配给最合适的节点。kube-scheduler 会考虑资源需求、硬件/软件/策略约束、亲和性/反亲和性规范、数据本地性以及工作负载干扰。
</details>

5. 哪个 control plane 组件会与云服务提供商的 API 交互？
   - A) kube-apiserver
   - B) etcd
   - C) cloud-controller-manager
   - D) kubelet
   
<details>

<summary>显示答案</summary>

**答案：C) cloud-controller-manager**

**解释：**
cloud-controller-manager 是一个包含云服务提供商专用控制逻辑并与其 API 交互的 control plane 组件。这使 Kubernetes 核心能够与云服务提供商的 API 分离。cloud-controller-manager 会运行云服务提供商专用控制器，例如 node、route 和 service 控制器。CSI 控制器和节点插件负责处理存储配置、挂载和卸载。
</details>

6. 在每个节点上运行并管理 Pod 中容器执行的代理是什么？
   - A) kube-proxy
   - B) kubelet
   - C) containerd
   - D) kube-scheduler
   
<details>

<summary>显示答案</summary>

**答案：B) kubelet**

**解释：**
kubelet 是在每个节点上运行并管理 Pod 中容器执行的代理。kubelet 通过各种机制接收 PodSpec，并确保容器按照这些规范正常运行。其主要功能包括按照 PodSpec 运行容器、监控并报告容器状态、管理容器生命周期、管理卷挂载、报告节点状态以及执行容器健康检查。
</details>

7. Kubernetes 中哪个节点组件负责维护 Service IP 的网络规则并执行连接转发？
   - A) kubelet
   - B) kube-proxy
   - C) CNI 插件
   - D) containerd
   
<details>

<summary>显示答案</summary>

**答案：B) kube-proxy**

**解释：**
kube-proxy 是在每个节点上运行的网络代理，负责实现 Kubernetes 的 Service 概念。它会维护节点上的网络规则并执行连接转发。其主要功能包括维护 Service IP 和端口的网络规则、转发连接、实现负载均衡以及支持服务发现。kube-proxy 支持多种运行模式，包括 Linux 上的 iptables 和 nftables，以及 Windows 上的 kernelspace。IPVS 自 v1.35 起已弃用，userspace 模式已移除。
</details>

8. Kubernetes 中运行容器的标准接口是什么？
   - A) CRI（容器运行时接口）
   - B) CNI（容器网络接口）
   - C) CSI（容器存储接口）
   - D) CPI（容器平台接口）
   
<details>

<summary>显示答案</summary>

**答案：A) CRI（容器运行时接口）**

**解释：**
CRI（容器运行时接口）是 Kubernetes 中运行容器的标准接口。通过 CRI，Kubernetes 可以支持 containerd 和 CRI-O 等各种容器运行时。CRI 定义了 kubelet 与容器运行时之间通信的 API，从而支持创建、启动、停止和删除容器等操作。CNI（容器网络接口）是网络接口，CSI（容器存储接口）是存储接口。
</details>

9. Kubernetes 集群中用于实现 Pod 网络的接口是什么？
   - A) CRI（容器运行时接口）
   - B) CNI（容器网络接口）
   - C) CSI（容器存储接口）
   - D) API（应用程序编程接口）
   
<details>

<summary>显示答案</summary>

**答案：B) CNI（容器网络接口）**

**解释：**
CNI（容器网络接口）是 Kubernetes 中实现 Pod 网络的标准接口。CNI 插件负责将网络接口连接到 Pod 并分配 IP 地址。Calico、Cilium 和 Flannel 等多种 CNI 插件各有不同的功能和性能特点。借助 CNI，Kubernetes 可以支持各种网络解决方案。
</details>

10. Kubernetes 集群中，什么为存储系统提供标准接口？
    - A) CRI（容器运行时接口）
    - B) CNI（容器网络接口）
    - C) CSI（容器存储接口）
    - D) CPI（云服务提供商接口）
    
<details>

<summary>显示答案</summary>

**答案：C) CSI（容器存储接口）**

**解释：**
CSI（容器存储接口）为 Kubernetes 与存储系统之间提供标准接口。借助 CSI，存储提供商可以开发自己的存储驱动程序，而无需修改 Kubernetes 代码。CSI 定义了用于创建、删除、挂载和卸载卷等操作的标准化 API。现有多种 CSI 驱动程序，包括 AWS EBS CSI 驱动程序、Azure Disk CSI 驱动程序和 GCP PD CSI 驱动程序。
</details>

## 简答题

11. Kubernetes control plane 中运行多个控制器进程的组件叫什么？

<details>

<summary>显示答案</summary>

**答案：kube-controller-manager**

**解释：**
kube-controller-manager 是运行多个控制器进程的 control plane 组件。每个控制器负责管理集群的某个特定方面。主要控制器包括 node controller、replication controller、endpoint controller、service account & token controller、job controller、cronjob controller、daemonset controller、statefulset controller、PV controller、namespace controller 和垃圾回收器。
</details>

12. Kubernetes 使用什么共识算法来确保 etcd 数据的一致性？

<details>

<summary>显示答案</summary>

**答案：Raft**

**解释：**
etcd 使用 Raft 共识算法，确保分布式系统中的数据具有强一致性。Raft 通过领导者选举、日志复制和安全性机制在分布式系统中达成共识。etcd 集群通常由 3 个或 5 个节点组成，只要大多数节点（法定人数）正常运行，集群就可以继续运行。
</details>

13. 在 Linux 上未显式选择模式时，kube-proxy 的默认模式是什么？

<details>

<summary>显示答案</summary>

**答案：iptables**

**解释：**
kube-proxy 的默认运行模式是 iptables 模式。在此模式下，kube-proxy 使用 Linux iptables 实现 NAT，并将发往 Service IP 的流量路由到 Pod。nftables 是另一种 Linux 模式（自 v1.33 起稳定）；迁移前请检查内核和 CNI 的兼容性。IPVS 自 v1.35 起已弃用（计划在 v1.40 默认禁用，并在 v1.43 移除）；userspace 模式已移除。Windows 使用 kernelspace 模式。
</details>

14. Kubernetes 集群中用于与 API server 通信的配置文件叫什么？

<details>

<summary>显示答案</summary>

**答案：kubeconfig**

**解释：**
kubeconfig 是用于与 Kubernetes API server 通信的配置文件。此文件包含集群信息、身份验证信息（证书、令牌等）和上下文（集群与用户的组合）。kubectl 命令默认使用 $HOME/.kube/config 文件，但也可以通过 --kubeconfig 标志或 KUBECONFIG 环境变量指定其他文件。
</details>

15. 通常建议 Kubernetes 高可用集群至少配置多少个 control plane 节点？

<details>

<summary>显示答案</summary>

**答案：3**

**解释：**
通常建议 Kubernetes 高可用集群至少配置 3 个 control plane 节点。这是因为 etcd 集群以多数（法定人数）为基础运行。配置 3 个节点时，即使 1 个节点发生故障，集群仍可继续运行（2 个节点构成多数）。配置 5 个节点时，即使 2 个节点发生故障，集群仍可继续运行（3 个节点构成多数）。通常建议使用奇数个节点。
</details>

## 动手题

16. 编写一条命令来创建 etcd 数据库备份。备份文件应保存到 `/backup/etcd-snapshot-$(date +%Y%m%d).db`，etcd 端点为 `https://127.0.0.1:2379`，证书文件位于 `/etc/kubernetes/pki/etcd/` 目录中。

<details>

<summary>显示答案</summary>

**答案：**
```bash
ETCDCTL_API=3 etcdctl snapshot save /backup/etcd-snapshot-$(date +%Y%m%d).db \
--endpoints=https://127.0.0.1:2379 \
--cacert=/etc/kubernetes/pki/etcd/ca.crt \
--cert=/etc/kubernetes/pki/etcd/server.crt \
--key=/etc/kubernetes/pki/etcd/server.key
```

**解释：**
此命令将 ETCDCTL_API 环境变量设为 3，以使用 etcdctl v3 API，并通过 snapshot save 命令创建 etcd 数据库快照。--endpoints 标志用于指定 etcd server 端点，--cacert、--cert 和 --key 标志用于指定 TLS 身份验证所需的证书文件。备份文件保存在 /backup 目录中，文件名包含当前日期。
</details>

17. 编写一个满足以下要求的 kube-scheduler 配置文件（YAML）：
    - Scheduler 名称：custom-scheduler
    - 启用 leader election
    - 打分插件：将 NodeResourcesBalancedAllocation 的权重设为 2
    - 筛选插件：保持 NodeUnschedulable 启用，以便继续排除已隔离的节点

<details>

<summary>显示答案</summary>

**答案：**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
leaderElection:
  leaderElect: true

profiles:
  - schedulerName: custom-scheduler
    plugins:
      score:
        enabled:
          - name: NodeResourcesBalancedAllocation
            weight: 2
        disabled: []
```

**解释：**
此 YAML 文件定义了一个 KubeSchedulerConfiguration 对象。leaderElection.leaderElect: true 会启用 leader election，profiles 部分则定义了名为 custom-scheduler 的 Scheduler 配置文件。在 plugins 部分，打分插件中的 NodeResourcesBalancedAllocation 权重被设为 2，默认的 NodeUnschedulable 筛选插件仍保持启用。如果将其禁用，Pod 就可能被调度到已隔离的节点上。
</details>

18. 编写一条 etcd 启动命令，用于配置满足以下要求的高可用 etcd 集群：
    - 节点名称：etcd-1
    - 集群名称：etcd-cluster
    - Client URL：https://192.168.1.10:2379
    - Peer URL：https://192.168.1.10:2380
    - 初始集群：etcd-1=https://192.168.1.10:2380,etcd-2=https://192.168.1.11:2380,etcd-3=https://192.168.1.12:2380
    - 数据目录：/var/lib/etcd
    - 证书文件位于 /etc/kubernetes/pki/etcd/ 目录中

<details>

<summary>显示答案</summary>

**答案：**
```bash
etcd \
--name=etcd-1 \
--initial-advertise-peer-urls=https://192.168.1.10:2380 \
--listen-peer-urls=https://192.168.1.10:2380 \
--listen-client-urls=https://192.168.1.10:2379,https://127.0.0.1:2379 \
--advertise-client-urls=https://192.168.1.10:2379 \
--initial-cluster-token=etcd-cluster \
--initial-cluster=etcd-1=https://192.168.1.10:2380,etcd-2=https://192.168.1.11:2380,etcd-3=https://192.168.1.12:2380 \
--initial-cluster-state=new \
--data-dir=/var/lib/etcd \
--cert-file=/etc/kubernetes/pki/etcd/server.crt \
--key-file=/etc/kubernetes/pki/etcd/server.key \
--trusted-ca-file=/etc/kubernetes/pki/etcd/ca.crt \
--client-cert-auth=true \
--peer-cert-file=/etc/kubernetes/pki/etcd/peer.crt \
--peer-key-file=/etc/kubernetes/pki/etcd/peer.key \
--peer-trusted-ca-file=/etc/kubernetes/pki/etcd/ca.crt \
--peer-client-cert-auth=true
```

**解释：**
此命令会启动一个名为 etcd-1 的 etcd 节点。--initial-advertise-peer-urls 和 --listen-peer-urls 用于指定节点间通信的 URL，--listen-client-urls 和 --advertise-client-urls 用于指定客户端通信的 URL。--initial-cluster-token 用于指定集群的唯一标识符，--initial-cluster 用于列出集群中的所有节点。--initial-cluster-state=new 表示正在创建新集群。--data-dir 用于指定存储 etcd 数据的目录。最后，与证书相关的标志用于指定 TLS 通信所需的证书文件。
</details>

## 进阶题

19. 设计一个 Kubernetes 集群的高可用架构，并说明 control plane 组件和 etcd 的部署方式、负载均衡器配置，以及故障场景下的应对措施。

<details>

<summary>显示答案</summary>

**答案：**

**Kubernetes 高可用集群架构设计**

1. **Control Plane 组件部署**：
  - 至少将 3 个 control plane 节点分布在多个可用区
  - 在每个节点上部署 kube-apiserver、kube-scheduler、kube-controller-manager
  - 让 kube-scheduler 和 kube-controller-manager 以 leader election 模式运行（同一时间仅有一个实例处于活动状态）
  - kube-apiserver 可水平扩展（所有实例可同时处于活动状态）

2. **etcd 部署方式**：
  - 堆叠式拓扑：将 etcd 与 control plane 节点一起部署
  - 外部拓扑：将 etcd 部署在独立节点上（隔离性和可扩展性更高）
  - 至少将 3 个 etcd 节点分布在多个可用区（根据容错能力和延迟选择 3 个或 5 个）
  - etcd 集群使用 Raft 共识算法来确保数据一致性

3. **负载均衡器配置**：
  - 在 kube-apiserver 前端部署负载均衡器
  - 使用 L4 TCP 直通，以保留端到端 TLS 和客户端证书身份验证
  - 通过健康检查检测不健康的 kube-apiserver 实例，并停止向其转发流量
  - 在云环境中，使用云服务提供商托管的负载均衡器（AWS ELB、GCP Cloud Load Balancer 等）
  - 在本地环境中，使用 HAProxy、NGINX、keepalived 等

4. **故障场景和应对措施**：
  - **单个 control plane 节点故障**：
  - kube-apiserver：负载均衡器将流量路由到健康节点
  - kube-scheduler/kube-controller-manager：通过 leader election 激活其他节点上的实例
  - etcd：只要多数节点健康，集群就会继续运行（3 个节点中有 2 个，5 个节点中有 3 个）

  - **可用区故障**：
  - 将节点分布在多个可用区，以应对单个可用区故障
  - 同时将工作节点分布在多个可用区

  - **网络分区**：
  - etcd 按多数原则运行，以防止网络分区期间出现“脑裂”
  - 少数派无法提交写入或提供线性一致性读取；显式请求的可序列化读取可能会返回过时的本地数据

  - **etcd 数据损坏/丢失**：
  - 定期备份 etcd
  - 编写并测试从备份恢复的流程

5. **其他注意事项**：
  - **证书管理**：监控证书过期时间并自动续期
  - **审计日志**：为重要操作启用审计日志并将其存储在外部
  - **监控和告警**：为 control plane 组件状态设置监控和告警
  - **自动恢复**：实现自动恢复机制（例如 systemd 服务自动重启）

采用此高可用架构后，即使单个节点、单个可用区或某些组件发生故障，Kubernetes 集群仍可继续运行。
</details>

20. 说明 Kubernetes 集群的网络架构，描述 Pod 间通信、Service 网络和外部通信的工作方式，并解释 CNI 插件的作用。还要说明如何使用网络策略限制 Pod 间通信。

<details>

<summary>显示答案</summary>

**答案：**

**Kubernetes 网络架构**

1. **Kubernetes 网络模型**：
  - 所有 Pod 都有唯一的 IP 地址
  - Pod 之间可以在不使用 NAT 的情况下通信
  - 节点和 Pod 之间可以在不使用 NAT 的情况下通信
  - Pod 内的容器通过 localhost 通信

2. **Pod 间通信**：
  - **同一节点上的 Pod 之间**：通过本地数据平面通信（具体使用 bridge、路由或 eBPF 取决于插件）
  - **不同节点上的 Pod 之间**：通过覆盖网络或路由表通信
  - CNI 插件负责处理 Pod IP 地址分配和路由

3. **Service 网络**：
  - **ClusterIP**：仅能在集群内部访问的虚拟 IP
  - **kube-proxy**：将发往 Service IP 的流量路由到 Pod
  - iptables 模式：使用 Linux iptables 规则实现 NAT
  - nftables 模式：配置 Linux nftables 数据平面；IPVS 已弃用
  - **CoreDNS**：将 Service 名称解析为 ClusterIP 的 DNS 服务
  - **服务发现**：通过环境变量或 DNS 发现服务

4. **外部通信**：
  - **Ingress**：将 HTTP/HTTPS 流量路由到 Service
  - **NodePort**：通过节点上的特定端口公开 Service
  - **LoadBalancer**：通过云服务提供商的负载均衡器公开 Service
  - **ExternalName**：为外部服务创建 CNAME 记录

5. **CNI（容器网络接口）插件的作用**：
  - 将网络接口连接到 Pod
  - 分配和管理 IP 地址
  - 配置路由表
  - 实现网络策略
  - 主要的 CNI 插件：
  - **Calico**：基于 BGP 的网络，支持网络策略，性能高
  - **Cilium**：基于 eBPF 的网络和安全方案，支持 L3-L7 安全策略，性能高
  - **Flannel**：简单的覆盖网络，易于配置
  - **Weave Net**：多主机容器网络，支持加密

6. **使用网络策略限制 Pod 间通信**：
  - 使用 NetworkPolicy 资源控制 Pod 间通信
  - 默认情况下，所有 Pod 都可以互相通信（不存在任何策略时）
  - 网络策略的组成部分：
  - **podSelector**：选择策略适用的 Pod
  - **policyTypes**：Ingress（入站）、Egress（出站）或两者
  - **ingress**：入站流量规则
  - **egress**：出站流量规则

  - **默认拒绝策略示例**：
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

  - **仅允许特定 Pod 之间通信的策略示例**：
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Ingress
  ingress:
    - from:
      - podSelector:
          matchLabels:
            app: frontend
      ports:
        - protocol: TCP
          port: 8080
```

  - **控制命名空间间通信的示例**：
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-monitoring
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Ingress
  ingress:
    - from:
      - namespaceSelector:
          matchLabels:
            purpose: monitoring
      ports:
        - protocol: TCP
          port: 9090
```

7. **网络策略实施注意事项**：
  - 网络策略由 CNI 插件实现
  - 并非所有 CNI 插件都支持网络策略
  - 应先在测试环境中验证，再应用策略
  - 建议从默认拒绝策略开始，只允许必要的通信

Kubernetes 网络架构能够以灵活且可扩展的方式实现容器间通信，并通过网络策略提供细粒度的安全控制。
</details>

---

[返回学习资料](../../core/01-cluster-architecture.md) | [下一测验：Pod 和工作负载](../core/02-pods-and-workloads-quiz.md)

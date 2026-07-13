# Cluster Architecture Quiz

本测验用于检验你对 Kubernetes 集群架构、主要组件、通信路径以及高可用配置的理解。

## Multiple Choice Questions

1. 以下哪一项不是 Kubernetes control plane 的核心组件？
   - A) kube-apiserver
   - B) etcd
   - C) kube-proxy
   - D) kube-scheduler
   
<details>

<summary>显示答案</summary>

**答案：C) kube-proxy**

**解释：**
kube-proxy 是 node 组件，而不是 control plane 组件。核心 control plane 组件包括 kube-apiserver、etcd、kube-scheduler、kube-controller-manager 和 cloud-controller-manager。kube-proxy 在每个 node 上运行，维护网络规则并执行连接转发。
</details>

2. Kubernetes 中哪个组件充当保存所有集群数据的“事实来源”？
   - A) kube-apiserver
   - B) etcd
   - C) kube-controller-manager
   - D) kubelet
   
<details>

<summary>显示答案</summary>

**答案：B) etcd**

**解释：**
etcd 是一致且高可用的键值存储，用于保存所有集群数据，并充当 Kubernetes 的“事实来源”。所有集群状态、配置和元数据都存储在 etcd 中，所有其他 control plane 组件都通过 kube-apiserver 与 etcd 交互以读取和写入信息。
</details>

3. 以下哪一项不是 Kubernetes node 组件？
   - A) kubelet
   - B) kube-proxy
   - C) Container runtime
   - D) kube-controller-manager
   
<details>

<summary>显示答案</summary>

**答案：D) kube-controller-manager**

**解释：**
kube-controller-manager 是 control plane 组件，而不是 node 组件。node 组件包括 kubelet、kube-proxy 和 container runtime（containerd、CRI-O 等）。kube-controller-manager 在 control plane 上运行，并执行各种 controller 进程，例如 node controller 和 replication controller。
</details>

4. Kubernetes 中哪个 control plane 组件会选择用于运行新创建 pod 的 node？
   - A) kube-apiserver
   - B) kube-scheduler
   - C) kubelet
   - D) kube-controller-manager
   
<details>

<summary>显示答案</summary>

**答案：B) kube-scheduler**

**解释：**
kube-scheduler 是选择用于运行新创建 pod 的 node 的 control plane 组件。调度过程由过滤（识别可以运行该 pod 的 node）和评分（为合适的 node 分配分数）组成，最终将该 pod 分配给最优 node。kube-scheduler 会考虑资源需求、硬件/软件/策略约束、亲和性/反亲和性规范、数据局部性以及工作负载干扰。
</details>

5. 哪个 control plane 组件会与云提供商 API 交互？
   - A) kube-apiserver
   - B) etcd
   - C) cloud-controller-manager
   - D) kubelet
   
<details>

<summary>显示答案</summary>

**答案：C) cloud-controller-manager**

**解释：**
cloud-controller-manager 是包含特定于云的控制逻辑并与云提供商 API 交互的 control plane 组件。这允许 Kubernetes 核心与云提供商 API 分离。cloud-controller-manager 运行特定于云的 controller，例如 node controller、route controller、service controller 和 volume controller。
</details>

6. 在每个 node 上运行并管理 pod 内 container 执行的 agent 是什么？
   - A) kube-proxy
   - B) kubelet
   - C) containerd
   - D) kube-scheduler
   
<details>

<summary>显示答案</summary>

**答案：B) kubelet**

**解释：**
kubelet 是在每个 node 上运行并管理 pod 内 container 执行的 agent。kubelet 通过各种机制接收 PodSpec，并确保 container 按照这些规范健康运行。关键功能包括按照 PodSpec 运行 container、监控并报告 container 状态、管理 container 生命周期、管理 volume 挂载、报告 node 状态以及执行 container 健康检查。
</details>

7. Kubernetes 中哪个 node 组件维护 service IP 的网络规则并执行连接转发？
   - A) kubelet
   - B) kube-proxy
   - C) CNI plugin
   - D) containerd
   
<details>

<summary>显示答案</summary>

**答案：B) kube-proxy**

**解释：**
kube-proxy 是在每个 node 上运行的网络代理，负责实现 Kubernetes Service 概念。它在 node 上维护网络规则并执行连接转发。关键功能包括维护 service IP 和端口的网络规则、连接转发、实现负载均衡以及支持 service discovery。kube-proxy 支持多种运行模式，包括 userspace mode、iptables mode 和 IPVS mode。
</details>

8. 在 Kubernetes 中运行 container 的标准接口是什么？
   - A) CRI (Container Runtime Interface)
   - B) CNI (Container Network Interface)
   - C) CSI (Container Storage Interface)
   - D) CPI (Container Platform Interface)
   
<details>

<summary>显示答案</summary>

**答案：A) CRI (Container Runtime Interface)**

**解释：**
CRI (Container Runtime Interface) 是 Kubernetes 中运行 container 的标准接口。通过 CRI，Kubernetes 可以支持各种 container runtime，例如 containerd 和 CRI-O。CRI 定义了 kubelet 与 container runtime 之间通信的 API，从而支持创建、启动、停止和删除 container 等操作。CNI (Container Network Interface) 是用于网络的接口，CSI (Container Storage Interface) 是用于存储的接口。
</details>

9. Kubernetes 集群中用于实现 pod 网络的接口是什么？
   - A) CRI (Container Runtime Interface)
   - B) CNI (Container Network Interface)
   - C) CSI (Container Storage Interface)
   - D) API (Application Programming Interface)
   
<details>

<summary>显示答案</summary>

**答案：B) CNI (Container Network Interface)**

**解释：**
CNI (Container Network Interface) 是在 Kubernetes 中实现 pod 网络的标准接口。CNI plugin 负责将网络接口连接到 pod 并分配 IP 地址。存在多种 CNI plugin，包括 Calico、Cilium、Flannel 和 Weave Net，每种都有不同的功能和性能特征。通过 CNI，Kubernetes 可以支持各种网络解决方案。
</details>

10. 在 Kubernetes 集群中，什么为存储系统提供标准接口？
    - A) CRI (Container Runtime Interface)
    - B) CNI (Container Network Interface)
    - C) CSI (Container Storage Interface)
    - D) CPI (Cloud Provider Interface)
    
<details>

<summary>显示答案</summary>

**答案：C) CSI (Container Storage Interface)**

**解释：**
CSI (Container Storage Interface) 在 Kubernetes 与存储系统之间提供标准接口。通过 CSI，存储提供商可以在不修改 Kubernetes 代码的情况下开发自己的存储 driver。CSI 为 volume 创建、删除、挂载和卸载等操作定义了标准化 API。存在多种 CSI driver，包括 AWS EBS CSI driver、Azure Disk CSI driver 和 GCP PD CSI driver。
</details>

## Short Answer Questions

11. Kubernetes control plane 中运行多个 controller 进程的组件名称是什么？

<details>

<summary>显示答案</summary>

**答案：kube-controller-manager**

**解释：**
kube-controller-manager 是运行多个 controller 进程的 control plane 组件。每个 controller 管理集群的某个特定方面。主要 controller 包括 node controller、replication controller、endpoint controller、service account & token controller、job controller、cronjob controller、daemonset controller、statefulset controller、PV controller、namespace controller 和 garbage collector。
</details>

12. Kubernetes 使用什么共识算法来确保 etcd 数据的一致性？

<details>

<summary>显示答案</summary>

**答案：Raft**

**解释：**
etcd 使用 Raft 共识算法来确保分布式系统中数据的强一致性。Raft 通过 leader 选举、日志复制和安全性在分布式系统中达成共识。etcd 集群通常由 3 个或 5 个 node 组成，只要多数（quorum）node 正常运行，集群就可以继续运行。
</details>

13. Kubernetes 中 kube-proxy 的默认运行模式是什么？

<details>

<summary>显示答案</summary>

**答案：iptables**

**解释：**
kube-proxy 的默认运行模式是 iptables mode。在此模式下，kube-proxy 使用 Linux iptables 实现 NAT，并将发送到 service IP 的流量路由到 pod。其他运行模式包括 userspace mode（旧版）和 IPVS mode（高性能）。IPVS mode 为大型集群提供更好的性能，但需要 Linux kernel 中的 IPVS 模块。
</details>

14. Kubernetes 集群中用于与 API server 通信的配置文件名称是什么？

<details>

<summary>显示答案</summary>

**答案：kubeconfig**

**解释：**
kubeconfig 是用于与 Kubernetes API server 通信的配置文件。该文件包含集群信息、身份验证信息（证书、token 等）以及 context（集群和用户的组合）。kubectl 命令默认使用 $HOME/.kube/config 文件，但可以通过 --kubeconfig flag 或 KUBECONFIG 环境变量指定其他文件。
</details>

15. 在 Kubernetes 中配置高可用集群时，通常建议的最少 control plane node 数量是多少？

<details>

<summary>显示答案</summary>

**答案：3**

**解释：**
在 Kubernetes 中，高可用集群通常建议的最少 control plane node 数量是 3。这是因为 etcd 集群基于多数（quorum）机制运行。使用 3 个 node 时，即使 1 个 node 发生故障，集群也可以继续运行（2 是多数）。使用 5 个 node 时，即使 2 个 node 发生故障，集群也可以继续运行（3 是多数）。通常建议使用奇数数量的 node。
</details>

## Hands-on Questions

16. 编写一个命令来创建 etcd 数据库备份。备份文件应保存到 `/backup/etcd-snapshot-$(date +%Y%m%d).db`，etcd endpoint 为 `https://127.0.0.1:2379`，证书文件位于 `/etc/kubernetes/pki/etcd/` 目录中。

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
此命令将 ETCDCTL_API 环境变量设置为 3，以使用 etcdctl v3 API，并使用 snapshot save 命令创建 etcd 数据库的快照。--endpoints flag 指定 etcd server endpoint，--cacert、--cert、--key flag 指定 TLS 身份验证所需的证书文件。备份文件保存到 /backup 目录，文件名包含当前日期。
</details>

17. 编写一个符合以下要求的 kube-scheduler 配置文件 (YAML)：
    - Scheduler 名称：custom-scheduler
    - 启用 Leader election
    - Scoring plugin：将 NodeResourcesBalancedAllocation 权重设置为 2
    - Filtering plugin：禁用 NodeUnschedulable

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
        disabled: []
      filter:
        disabled:
          - name: NodeUnschedulable
```

**解释：**
此 YAML 文件定义了一个 KubeSchedulerConfiguration 对象。leaderElection.leaderElect: true 启用 leader election，profiles 部分定义了名为 custom-scheduler 的 scheduler profile。在 plugins 部分，NodeResourcesBalancedAllocation 的权重在 score plugins 中设置为 2，NodeUnschedulable 在 filter plugins 中被禁用。
</details>

18. 编写一个用于配置高可用 etcd 集群的 etcd 启动命令，满足以下要求：
    - Node 名称：etcd-1
    - 集群名称：etcd-cluster
    - Client URL：https://192.168.1.10:2379
    - Peer URL：https://192.168.1.10:2380
    - Initial cluster：etcd-1=https://192.168.1.10:2380,etcd-2=https://192.168.1.11:2380,etcd-3=https://192.168.1.12:2380
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
--peer-cert-file=/etc/kubernetes/pki/etcd/peer.crt \
--peer-key-file=/etc/kubernetes/pki/etcd/peer.key \
--peer-trusted-ca-file=/etc/kubernetes/pki/etcd/ca.crt
```

**解释：**
此命令启动名为 etcd-1 的 etcd node。--initial-advertise-peer-urls 和 --listen-peer-urls 指定 peer 通信使用的 URL，--listen-client-urls 和 --advertise-client-urls 指定 client 通信使用的 URL。--initial-cluster-token 指定集群的唯一标识符，--initial-cluster 列出集群中的所有 node。--initial-cluster-state=new 表示正在创建新集群。--data-dir 指定存储 etcd 数据的目录。最后，证书相关 flag 指定 TLS 通信所需的证书文件。
</details>

## Advanced Questions

19. 设计一个 Kubernetes 集群的高可用架构，并说明 control plane 组件和 etcd 的部署方法、load balancer 配置以及故障场景的应对措施。

<details>

<summary>显示答案</summary>

**答案：**

**高可用 Kubernetes 集群架构设计**

1. **Control Plane 组件部署**:
  - 将至少 3 个 control plane node 分布到多个 availability zone
  - 在每个 node 上部署 kube-apiserver、kube-scheduler、kube-controller-manager
  - 以 leader election mode 运行 kube-scheduler 和 kube-controller-manager（一次只有一个实例处于 active 状态）
  - kube-apiserver 可水平扩展（所有实例同时处于 active 状态）

2. **etcd 部署方法**:
  - Stacked topology：将 etcd 与 control plane node 一起部署
  - External topology：在单独的 node 上部署 etcd（隔离性和可扩展性更高）
  - 将至少 3 个 etcd node 分布到多个 availability zone（建议 5 个）
  - etcd 集群使用 Raft 共识算法确保数据一致性

3. **Load Balancer 配置**:
  - 将 load balancer 放置在 kube-apiserver 前面
  - load balancer 可以在 L4 (TCP) 或 L7 (HTTP/HTTPS) 级别运行
  - 通过 health check 检测不健康的 kube-apiserver 实例并排除流量
  - 在云环境中，使用云提供商的托管 load balancer（AWS ELB、GCP Cloud Load Balancer 等）
  - 在本地环境中，使用 HAProxy、NGINX、keepalived 等

4. **故障场景和应对措施**:
  - **单个 control plane node 故障**:
  - kube-apiserver：load balancer 将流量路由到健康的 node
  - kube-scheduler/kube-controller-manager：通过 leader election 激活另一个 node 上的实例
  - etcd：如果多数节点健康（3 个中的 2 个，5 个中的 3 个），集群继续运行

  - **Availability zone 故障**:
  - 将 node 分布到多个 availability zone，以处理单个 zone 故障
  - 也将 worker node 分布到多个 availability zone

  - **Network partition**:
  - etcd 基于多数机制运行，以防止网络分区期间出现“split brain”
  - 少数分区中的 etcd node 切换为只读模式

  - **etcd 数据损坏/丢失**:
  - 定期执行 etcd 备份
  - 记录并测试从备份恢复的过程

5. **其他注意事项**:
  - **证书管理**：监控证书过期时间并自动续期
  - **Audit logging**：为重要操作启用 audit log 并外部存储
  - **监控和告警**：为 control plane 组件状态设置监控和告警
  - **自动恢复**：实现自动恢复机制（例如 systemd service 自动重启）

借助这种高可用架构，即使单个 node、单个 availability zone 或某些组件发生故障，Kubernetes 集群也可以继续运行。
</details>

20. 说明 Kubernetes 集群的网络架构，描述 pod-to-pod communication、service networking 和 external communication 的工作方式，并说明 CNI plugin 的作用。同时说明如何使用 network policy 限制 pod-to-pod communication。

<details>

<summary>显示答案</summary>

**答案：**

**Kubernetes 网络架构**

1. **Kubernetes 网络模型**:
  - 所有 pod 都有唯一的 IP 地址
  - pod 可以在没有 NAT 的情况下通信
  - node 和 pod 可以在没有 NAT 的情况下通信
  - 同一 pod 内的 container 通过 localhost 通信

2. **Pod-to-Pod Communication**:
  - **同一 node 上的 pod 之间**：通过 node 的本地 bridge network 通信
  - **不同 node 上的 pod 之间**：通过 overlay network 或 routing table 通信
  - CNI plugin 处理 pod IP 地址分配和路由

3. **Service Networking**:
  - **ClusterIP**：仅可在集群内访问的虚拟 IP
  - **kube-proxy**：将发送到 service IP 的流量路由到 pod
  - iptables mode：使用 Linux iptables 规则实现 NAT
  - IPVS mode：使用 Linux kernel 的 IP Virtual Server 提供高性能负载均衡
  - **CoreDNS**：将 service name 解析为 ClusterIP 的 DNS service
  - **Service discovery**：通过环境变量或 DNS 发现 service

4. **External Communication**:
  - **Ingress**：将 HTTP/HTTPS 流量路由到 service
  - **NodePort**：通过 node 上的特定端口暴露 service
  - **LoadBalancer**：通过云提供商的 load balancer 暴露 service
  - **ExternalName**：为 external service 创建 CNAME record

5. **CNI (Container Network Interface) Plugin 的作用**:
  - 将网络接口连接到 pod
  - 分配和管理 IP 地址
  - 配置 routing table
  - 实现 network policy
  - 主要 CNI plugin：
  - **Calico**：基于 BGP 的网络、network policy 支持、高性能
  - **Cilium**：基于 eBPF 的网络和安全、L3-L7 安全策略、高性能
  - **Flannel**：简单的 overlay network，配置简单
  - **Weave Net**：多主机 container 网络，支持加密

6. **使用 Network Policy 限制 Pod-to-Pod Communication**:
  - 使用 NetworkPolicy resource 控制 pod-to-pod communication
  - 默认情况下，所有 pod 都可以彼此通信（不存在 policy 时）
  - Network policy 组件：
  - **podSelector**：选择该 policy 适用的 pod
  - **policyTypes**：Ingress（入站）、Egress（出站）或二者
  - **ingress**：入站流量规则
  - **egress**：出站流量规则

  - **默认拒绝 policy 示例**:
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

  - **仅允许特定 pod 之间通信的 policy 示例**:
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

  - **Namespace 到 namespace 通信控制示例**:
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

7. **Network Policy 实现注意事项**:
  - Network policy 由 CNI plugin 实现
  - 并非所有 CNI plugin 都支持 network policy
  - 在应用 policy 前先在测试环境中验证
  - 建议从默认拒绝 policy 开始，并仅允许必要通信

Kubernetes 网络架构以灵活且可扩展的方式支持 container 之间的通信，并通过 network policy 提供细粒度的安全控制。
</details>

---

[返回学习资料](../../core/01-cluster-architecture.md) | [下一个测验：Pods and Workloads](../core/02-pods-and-workloads-quiz.md)

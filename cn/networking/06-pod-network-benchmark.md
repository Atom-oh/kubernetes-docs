# Pod 网络基准测试：同节点、同 AZ、跨 AZ 与 DNS ndots

> **记录的测试环境**：Kubernetes 1.36（Amazon EKS）、Amazon VPC CNI v1.21.1、kube-proxy iptables 模式
> **测量日期**：2026 年 9 月 2 日 · **内容审核**：2026 年 9 月 12 日

本页保留了 2026 年 9 月 2 日对 `fsi-demo-cluster`（首尔）进行的基准测试报告：Pod 到 Pod 的 RTT、HTTP/gRPC 延迟、iperf3 吞吐量和 DNS 查询数。在这些测试中，跨 AZ 会增加延迟，而两条节点间路径的吞吐量相近。这并不能证明带宽保证与 AZ 无关。测量 1–2 中的应用流量直接使用 Pod IP；测量 3 对其成本进行建模，而测量 4 使用现有的 `kube-dns` ClusterIP。报告中的 10 次 DNS 查询过程取决于此解析器、搜索列表和响应序列，并不适用于每个 EKS Pod。历史版本和测量数据均予以保留；审核没有重新运行 EKS 基准测试，也没有核实账单。

![Client Pod 位于节点 A（ap-northeast-2a），访问同一节点上的 Server Pod、同一 AZ 中节点 B 上的 Server Pod，以及 ap-northeast-2b 中节点 C 上的 Server Pod（RTT 0.040 / 0.339 / 0.544 ms，单流 29.97 / 4.96 / 4.96 Gbps）。](../.gitbook/assets/en-networking-06-pod-network-benchmark-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-06-pod-network-benchmark-0.html)

该图记录了本次测试的拓扑。其中的 +0.21 ms 是这几次测试之间的差值；$4.47 是下文说明的历史十进制 GB 成本模型，并非经核实的费用，也不是适用于所有情况的每 AZ 成本。

## TL;DR：测量结果

1. **报告的 RTT**：同节点 **0.040 ms** → 同 AZ **0.339 ms** → 跨 AZ **0.544 ms**（ping，200 次探测的平均值）。观察到的两条节点间路径相差 +0.21 ms；与同节点路径相比，相差 +0.50 ms。
2. **HTTP p50 / p99**（fortio，100 qps、4 个连接、keepalive、60 s）：0.259 / 0.350 ms → 0.461 / 0.667 ms → 0.704 / 0.812 ms，应用侧观察到的延迟阶梯也相同。
3. **报告的带宽**：两条节点间路径的单 TCP 流均达到 **4.96 Gbps**；8 个流达到 **9.94 Gbps**，接近 m5.xlarge 10 Gbps 突发峰值。这与集群置放群组之外通常适用的 5 Gbps 单流限制相符。其他实例特性和路径可能有不同限制。
4. **同节点 Pod 到 Pod**：单流达到 **29.97 Gbps**（客户端进程 CPU 为 99.8%，与 CPU 压力相符），8 个流达到 **48.15 Gbps**。在此 VPC CNI 配置中，流量经由 Pod 的 veth 对和主机网络栈传输，不经过物理网卡。
5. **成本模型**：180 s 的跨 AZ 测试传输了 **223.4 十进制 GB**。原始的基于有效载荷的模型按每端 $0.01/GB 估算为 **$4.47**；这不是账单。在 180 s 内未观察到吞吐量逐步降至 1.25 Gbps 基线的现象。
6. **报告的 DNS 结果**：此 glibc Pod 在 `ndots:5` 下解析 `sts.ap-northeast-2.amazonaws.com` 时发送了 **10 次查询**（8 次 NXDOMAIN），预热后的中位数为 **3.78 ms**。名称末尾加点时为 **2 次查询** / 0.80 ms；`ndots:1` 时为 2 次 / 0.54 ms。这些时间是样本值，不是保证值。
7. **新建连接**：禁用 keepalive 后，p50 从 0.259 → 0.664、0.461 → 1.079 和 0.704 → **1.517 ms**。TCP 建连会造成这部分增幅，但测试没有单独测量握手、套接字和应用成本。

## 测试环境

| 项目 | 值 |
|---|---|
| 集群 | Amazon EKS `fsi-demo-cluster`，ap-northeast-2（首尔），控制平面 `v1.36.2-eks-bca9cf6`，使用两个 AZ（2a、2b） |
| 节点 | **3 × m5.xlarge**，由 Karpenter `system` NodePool 为本次测试全新启动：2a 中一个客户端节点、2a 中一个服务器节点、2b 中一个服务器节点。4 vCPU，Intel Xeon Platinum 8175M @ 2.50GHz |
| 节点操作系统 | Amazon Linux 2023.12.20260817，内核 `6.18.41-94.142.amzn2023.x86_64`，containerd 2.2.5，kubelet v1.36.3-eks-cb19647 |
| CNI | Amazon VPC CNI `v1.21.1-eksbuild.8`（+ network-policy-agent v1.3.4）；`ENABLE_PREFIX_DELEGATION=false`、`ENABLE_POD_ENI=false`、`AWS_VPC_K8S_CNI_EXTERNALSNAT=false`、`NETWORK_POLICY_ENFORCING_MODE=standard`、`WARM_ENI_TARGET=1`、`WARM_IP_TARGET=3` |
| kube-proxy | `v1.35.3-eksbuild.5`，`mode: "iptables"` |
| CoreDNS | `v1.14.2-eksbuild.4`，2 个副本，每个 AZ 各一个（`10.0.2.106` / 2a、`10.0.3.14` / 2b）；Service `kube-dns` ClusterIP `172.20.0.10`；Corefile `kubernetes cluster.local … { pods insecure }`、`forward . /etc/resolv.conf`、`cache 30`、`loadbalance`；**未启用 NodeLocal DNSCache**，未启用 `autopath` 插件 |
| Pod resolv.conf（默认） | `search bench-net.svc.cluster.local svc.cluster.local cluster.local ap-northeast-2.compute.internal` / `nameserver 172.20.0.10` / `options ndots:5` |
| Pod 网卡 | eth0 MTU **9001**（巨型帧），TCP 拥塞控制 `cubic`，iperf3 `tcp_mss_default: 8949` |
| EC2 网络规格 | m5.xlarge“最高 10 Gigabit”：基线 **1.25 Gbps**、峰值 **10 Gbps**、4 vCPU（对比：m5.large 基线 0.75 Gbps、峰值 10 Gbps、2 vCPU）。通过 `aws ec2 describe-instance-types` 验证；需要 ENA |
| 定价 | usagetype `APN2-DataTransfer-Regional-Bytes`，“Regional Data Transfer - in/out/between AZs or when using public IP or Elastic IP addresses”，**$0.01/GB**（通过 `aws pricing get-products --region us-east-1` 查询，查询时间为 2026-09） |
| 工具 | `nicolaka/netshoot:v0.14`（iperf **3.19**、fortio **1.69.5**、iputils ping 20250605、tcpdump 4.99.5）；DNS 客户端 `python:3.12-slim`（Debian 13、**glibc 2.41**、Python 3.12.14） |
| 测试时段 | 2026-09-02 07:58–08:40 UTC（首个 Pod 于 07:58:22Z 启动，DNS Pod 于 08:16:24Z 启动） |

AWS 将突发带宽描述为尽力而为，即使网络 I/O 积分仍有余额也是如此；入站和出站流量使用独立的积分池。新实例以最大积分启动，但峰值带宽的可用性和突发持续时间各不相同。本次 180 s 测试只能说明在测试时段内未观察到吞吐量降至基线的现象。记录的 m5.xlarge 1.25 Gbps 基线 / 10 Gbps 峰值也见于官方的 [M5 网络规格](https://docs.aws.amazon.com/ec2/latest/instancetypes/gp.html)；当前积分行为说明见 [EC2 带宽指南](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-network-bandwidth.html)。

测试期间的工作负载放置情况：

| Pod | IP | 节点 | 可用区 | 角色 / requests |
|---|---|---|---|---|
| `cli` | 10.0.2.109 | ip-10-0-2-128（nodeclaim `system-76r87`） | ap-northeast-2a | 客户端；2500m / 1Gi |
| `srv-same` | 10.0.2.72 | ip-10-0-2-128，与 `cli` 位于同一节点（通过 required podAffinity） | ap-northeast-2a | 服务器；200m / 256Mi |
| `srv-a` | 10.0.2.37 | ip-10-0-2-20（nodeclaim `system-ksrbg`，与 `cli` 使用 podAntiAffinity） | ap-northeast-2a | 服务器；2800m / 1Gi |
| `srv-b` | 10.0.3.65 | ip-10-0-3-32（nodeclaim `system-svdvk`） | ap-northeast-2b | 服务器；2500m / 1Gi |
| `dns-default` | 10.0.2.5 | ip-10-0-2-20（与 `srv-a` 使用 podAffinity） | ap-northeast-2a | glibc 解析器，默认 `ndots:5` |
| `dns-ndots1` | 10.0.2.143 | ip-10-0-2-20 | ap-northeast-2a | glibc 解析器，`dnsConfig.options ndots=1` |

服务器 Pod 运行 `sh -c "iperf3 -s -p 5201 & exec fortio server -http-port 8080 -grpc-port 8079 -tcp-port 8078"`，每个基准测试 Pod 都带有 `karpenter.sh/do-not-disrupt: "true"`。最初为 `srv-a` 请求的是 m5.large / 1500m，但 Karpenter 报告 `no instance type has enough resources`（DaemonSet 开销占用 m5.large 的 1930m 可分配资源中的 821m），因此改为 m5.xlarge / 2800m。

### 测试工作负载清单

以下内容是记录的测试工作负载，保留了其中的历史选择器、requests、镜像、命令和注解。它不包含任何应用 Service 对象。仅凭这些选择器本身无法保证使用全新或隔离的节点。重新测试前，请根据获批的测试 NodePool、可用 AZ 和资源预算调整副本；不要未经评估就将其部署到共享的 `system` 池。请记录镜像摘要和工具版本：可变镜像标签以及 netshoot 在构建时下载工具的做法，无法保证使用原始二进制文件。下文修订后的步骤与这份历史材料是分开的。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: bench-net
  labels:
    bench: net
---
# client: fresh m5.xlarge in ap-northeast-2a
apiVersion: v1
kind: Pod
metadata:
  name: cli
  namespace: bench-net
  labels: { app: cli, role: client }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  nodeSelector:
    topology.kubernetes.io/zone: ap-northeast-2a
    node.kubernetes.io/instance-type: m5.xlarge
    karpenter.sh/nodepool: system
  terminationGracePeriodSeconds: 5
  containers:
    - name: netshoot
      image: nicolaka/netshoot:v0.14
      command: ["sleep", "infinity"]
      resources:
        requests: { cpu: "2500m", memory: "1Gi" }
---
# same-node: co-located with cli through required podAffinity
apiVersion: v1
kind: Pod
metadata:
  name: srv-same
  namespace: bench-net
  labels: { app: srv-same, role: server, zone: a }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  affinity:
    podAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector: { matchLabels: { app: cli } }
          topologyKey: kubernetes.io/hostname
  terminationGracePeriodSeconds: 5
  containers:
    - name: netshoot
      image: nicolaka/netshoot:v0.14
      command: ["sh", "-c", "iperf3 -s -p 5201 & exec fortio server -http-port 8080 -grpc-port 8079 -tcp-port 8078"]
      ports: [{ containerPort: 8080 }, { containerPort: 5201 }]
      resources:
        requests: { cpu: "200m", memory: "256Mi" }
---
# same-AZ: same AZ as cli, different node (podAntiAffinity). m5.large did not fit because of DaemonSet overhead, hence m5.xlarge
apiVersion: v1
kind: Pod
metadata:
  name: srv-a
  namespace: bench-net
  labels: { app: srv-a, role: server, zone: a }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  nodeSelector:
    topology.kubernetes.io/zone: ap-northeast-2a
    node.kubernetes.io/instance-type: m5.xlarge
    karpenter.sh/nodepool: system
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector: { matchLabels: { app: cli } }
          topologyKey: kubernetes.io/hostname
  terminationGracePeriodSeconds: 5
  containers:
    - name: netshoot
      image: nicolaka/netshoot:v0.14
      command: ["sh", "-c", "iperf3 -s -p 5201 & exec fortio server -http-port 8080 -grpc-port 8079 -tcp-port 8078"]
      ports: [{ containerPort: 8080 }, { containerPort: 5201 }]
      resources:
        requests: { cpu: "2800m", memory: "1Gi" }
---
# cross-AZ: fresh m5.xlarge in ap-northeast-2b
apiVersion: v1
kind: Pod
metadata:
  name: srv-b
  namespace: bench-net
  labels: { app: srv-b, role: server, zone: b }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  nodeSelector:
    topology.kubernetes.io/zone: ap-northeast-2b
    node.kubernetes.io/instance-type: m5.xlarge
    karpenter.sh/nodepool: system
  terminationGracePeriodSeconds: 5
  containers:
    - name: netshoot
      image: nicolaka/netshoot:v0.14
      command: ["sh", "-c", "iperf3 -s -p 5201 & exec fortio server -http-port 8080 -grpc-port 8079 -tcp-port 8078"]
      ports: [{ containerPort: 8080 }, { containerPort: 5201 }]
      resources:
        requests: { cpu: "2500m", memory: "1Gi" }
```

报告称，两个 DNS Pod 与 `srv-a` 位于同一节点。报告中的 `app` 镜像为 Debian 13 / glibc 2.41；未测量 musl 和其他解析器。`sniffer` 与应用共享 Pod 网络命名空间，因此在集群允许抓包的情况下，它可以捕获匹配的应用 DNS 数据包。若要通过下例创建两个 DNS 对象，请复制此配置：将第二个对象的名称和 `app` 标签改为 `dns-ndots1`，并且仅在第二个对象中取消注释 `dnsConfig`。两个对象应使用相同镜像；重新测试时，请固定并记录镜像摘要。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: dns-default          # the second Pod is name: dns-ndots1 plus the dnsConfig block below
  namespace: bench-net
  labels: { app: dns-default, role: dns }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  affinity:
    podAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector: { matchLabels: { app: srv-a } }
          topologyKey: kubernetes.io/hostname
  # present only in dns-ndots1:
  # dnsConfig:
  #   options:
  #     - name: ndots
  #       value: "1"
  terminationGracePeriodSeconds: 5
  containers:
    - name: app
      image: python:3.12-slim
      command: ["sleep", "infinity"]
      resources: { requests: { cpu: "50m", memory: "64Mi" } }
    - name: sniffer
      image: nicolaka/netshoot:v0.14
      command: ["sleep", "infinity"]
      resources: { requests: { cpu: "50m", memory: "64Mi" } }
```

## 测量 1. RTT 和 HTTP 延迟：同节点 → 同 AZ → 跨 AZ

ICMP 探测（`ping -c 200 -i 0.05 -q`）用于刻画空闲路径，包括端点内核处理和调度。随后通过 HTTP/1.1 和 gRPC 测试相同路径。表中还列出了一次新建连接的 `curl` connect / total 时间，供参考。

| 路径 | RTT 最小值 / **平均值** / 最大值 / mdev (ms) | 丢包 | curl，1 次冷请求：connect / total |
|---|---|---|---|
| 同节点 → 10.0.2.72 | 0.021 / **0.040** / 0.089 / 0.007 | 0/200 | 0.194 ms / 0.497 ms |
| 同 AZ → 10.0.2.37 | 0.300 / **0.339** / 0.450 / 0.017 | 0/200 | 0.497 ms / 2.333 ms |
| 跨 AZ → 10.0.3.65 | 0.504 / **0.544** / 0.625 / 0.015 | 0/200 | 0.694 ms / 4.038 ms |

观察到的差值：同 AZ − 同节点 = +0.30 ms，跨 AZ − 同 AZ = **+0.21 ms**，跨 AZ − 同节点 = +0.50 ms。此样本中报告的 mdev 值最高为 0.017 ms。curl 的 `time_total` 测量的是传输操作，而不是进程启动；单次观测不足以刻画其分布。参见 [curl 计时定义](https://curl.se/docs/manpage.html)。

### HTTP/1.1：100 qps、4 个连接、keepalive、60 s（6,000 个请求），单位 ms

| 路径 | 平均值 | **p50** | p90 | p99 | p99.9 | 最大值 | 最小值 |
|---|---|---|---|---|---|---|---|
| 同节点 | 0.260 | **0.259** | 0.299 | 0.350 | 1.267 | 2.080 | 0.111 |
| 同 AZ | 0.468 | **0.461** | 0.560 | 0.667 | 0.783 | 2.823 | 0.336 |
| 跨 AZ | 0.706 | **0.704** | 0.782 | 0.812 | 1.150 | 4.581 | 0.551 |

### gRPC ping：100 qps、4 个连接、30 s（3,000 个请求），单位 ms

| 路径 | 平均值 | **p50** | p90 | p99 | p99.9 | 最大值 | 最小值 |
|---|---|---|---|---|---|---|---|
| 同节点 | 0.410 | **0.397** | 0.449 | 0.869 | 1.187 | 1.314 | 0.241 |
| 同 AZ | 0.601 | **0.592** | 0.687 | 0.889 | 1.052 | 1.105 | 0.448 |
| 跨 AZ | 0.878 | **0.865** | 0.967 | 1.209 | 2.582 | 2.826 | 0.692 |

报告描述的 HTTP 回显正文约为 75 字节，请求负载为空，所有测试均无错误。请分别检查每种协议的结果计数器：HTTP 状态码 200、gRPC Ping 结果和 gRPC 健康检查的 `SERVING` 是不同的响应；`-grpc -ping` 选择的是 Ping，而不是默认的健康检查工作负载。

**如何解读。** HTTP p50 比 ping 平均值高约 0.22 / 0.12 / 0.16 ms，但用不同协议的不同统计值相减，无法单独得出用户空间开销。观测到的 HTTP p50 增幅为 +0.202 ms 和 +0.243 ms；它们并不是固定的每节点或每 AZ 成本。在这些实现中，gRPC p50 比 HTTP p50 高 0.138 / 0.131 / 0.161 ms，但这并不能证明其中有多少来自 HTTP/2、序列化、调度或客户端/服务器代码。HTTP p99 为 0.350 → 0.667 → 0.812 ms；gRPC p99.9 为 1.187 → 1.052 → **2.582 ms**。这些是每个单元格各运行一次所报告的分布。

> **与服务网格基准测试对比。** [Istio sidecar 与 ambient 报告](../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)记录了其完整 sidecar 场景中 **+1.29 ms** 的 p50 差值（2.11 − 0.82 ms），并非单个代理的独立开销。该测试使用 Graviton 硬件、200 qps、16 个连接和 Fortio 1.69.4，与本次 M5 / 100 qps / 4 连接测试不同。这些数字不能相加，也不能作为普遍的“网格跳数”成本与“AZ 跳数”成本进行比较排序。

### 新建连接的成本：keepalive=false、100 qps、4 个连接、30 s（3,000 个请求），单位 ms

每个请求都新建一个 TCP 连接时（fortio `-keepalive=false`），延迟会怎样变化？

| 路径 | 平均值 | **p50** | p90 | p99 | p99.9 | 最大值 | 最小值 | 相对 keepalive p50 |
|---|---|---|---|---|---|---|---|---|
| 同节点 | 0.672 | **0.664** | 0.782 | 0.957 | 1.253 | 1.306 | 0.364 | **+0.405 ms** |
| 同 AZ | 1.066 | **1.079** | 1.185 | 1.369 | 1.582 | 1.795 | 0.769 | **+0.618 ms** |
| 跨 AZ | 1.530 | **1.517** | 1.678 | 1.796 | 1.981 | 2.009 | 1.300 | **+0.813 ms** |

观察到的增幅为 **+0.405 / +0.618 / +0.813 ms**。新建 TCP 连接会增加建连开销，但这些测量无法证明存在固定的“1 个 RTT + 0.3 ms”分解。连接复用值得结合真实工作负载进行测量优化；但它不是跨 AZ 正确运行的前提。根据连接关闭方式，连接频繁创建和销毁也可能增加主动关闭端的 TIME_WAIT 状态；本次未测量套接字和 TIME_WAIT。

### 固定连接池的最大 qps：延迟即吞吐量（闭环、16 个连接、20 s）

使用 `-qps 0`（无限制，闭环）时，16 个连接所能维持的最大请求速率会将延迟差异转化为吞吐量差异。

| 路径 | 请求数 | **达到的 qps** | 平均值 ms | p50 | p90 | p99 | p99.9 | 最大值 |
|---|---|---|---|---|---|---|---|---|
| 同节点 | 899,827 | **44,991** | 0.355 | 0.249 | 0.733 | 1.695 | 3.389 | 13.593 |
| 同 AZ | 770,156 | **38,507** | 0.415 | 0.396 | 0.537 | 0.728 | 1.147 | 4.502 |
| 跨 AZ | 512,060 | **25,602** | 0.624 | 0.597 | 0.770 | 0.949 | 1.293 | 4.725 |

对于稳定的闭环负载，若约有 16 个请求在途且客户端思考时间很短，根据 Little 定律，吞吐量 ≈ 并发数 / 平均延迟：16 / 0.000355 = 45,070（报告值为 44,991）、16 / 0.000415 = 38,554（38,507）以及 16 / 0.000624 = 25,641（25,602）。本次测试中，报告的跨 AZ 速率比同 AZ **低 33.5%**。这一关系无法确定延迟的唯一原因，也不能预测普遍适用的 AZ 额外开销。共享 CPU 争用或许能解释同节点路径尾延迟较差的现象，但本次没有通过性能分析确认这一原因。

## 测量 2. 吞吐量：5 Gbps 单流上限和 10 Gbps 实例上限

iperf3 3.19、TCP、每次运行 20 s、`-J`、客户端 `cli`。CPU 列是 iperf3 自身报告的进程数据，其中 100% = 1 个 vCPU。

| 路径 | 流数 (-P) | 发送 Gbps | 接收 Gbps | 重传次数 | 发送字节数 | 客户端 CPU | 服务器 CPU | 发送端 TCP 平均 RTT（流 1） | 最大 snd_cwnd |
|---|---|---|---|---|---|---|---|---|---|
| 同节点（cli→srv-same） | 1 | **29.97** | 29.97 | 13 | 74,921,541,632 | **99.8%** | 80.9% | 34 µs | 1,861,392 B |
| 同节点 | 8 | **48.15** | 48.08 | 14,567 | 120,375,083,008 | 179.0% | 186.9% | 201 µs / 767 µs（流 1、2） | 5,888,442 B |
| 同 AZ（cli→srv-a，2a→2a） | 1 | **4.96** | 4.96 | 4 | 12,411,731,968 | 19.5% | 15.4% | **5,641 µs** | 4,349,214 B |
| 同 AZ | 8 | **9.94** | 9.93 | 5,874 | 24,846,139,392 | 36.3% | 159.3% | 2,720 µs / 1,626 µs | 1,163,370 B |
| 跨 AZ（cli→srv-b，2a→2b） | 1 | **4.96** | 4.96 | 2 | 12,411,994,112 | 20.0% | 22.5% | **5,420 µs** | 4,304,469 B |
| 跨 AZ | 8 | **9.94** | 9.93 | 5,979 | 24,845,090,816 | 36.7% | 138.2% | 3,671 µs / 3,237 µs | 1,226,013 B |

这里有四点值得注意。

1. **同节点流量绕过了物理网卡。** 单流结果为 29.97 Gbps，客户端进程 CPU 为 99.8%；8 个流达到 48.15 Gbps。主机路由、两个 Pod 的 veth 路径、内核处理和 CPU 调度仍然会产生影响。这是一个有 CPU 压力证据的网络基准测试，而不是纯内存复制速度测量。
2. **两次节点间单流测试均达到 4.96 Gbps。** 这与集群置放群组之外通常适用的 5 Gbps 限制相符。AWS 还说明，集群置放群组内的流量最高可达 10 Gbps；同一 AZ 中符合条件的 ENA Express 路径最高可达 25 Gbps。iperf3 进程 CPU 较低，本身不足以排除所有主机/网络处理限制。
3. **两次 8 流测试均达到 9.94 Gbps。** 这表明在该时段内，两条路径的实测吞吐量相近。即使只有一个流也发生了重传（节点间路径分别为 4 / 2 次），8 个流时重传增加（5,874 / 5,979 次）；单靠重传次数无法判断是否发生了 ENA 限流，也无法确定丢包位置。未采集 ENA allowance 计数器。
4. **负载下的 TCP RTT 高于空闲 ICMP RTT。** 单流发送端报告约 **5.6 / 5.4 ms**，拥塞窗口约为 4.3 MB；空闲 ping 平均值则为 0.34 / 0.54 ms。排队可能是原因之一，但协议、采样和负载均不相同。本次没有测量队列位置，也没有测量每个多路复用 RPC 是否必然增加 5 ms。

报告中的 MSS 8949 与 9001 字节 MTU 及观测到的 IPv4/TCP 开销相符；有效 MSS 还取决于报头和路径 MTU。下方的发送字节数是应用传输量，并非经独立核实的计费使用量。

> 对于这种普通 EC2 路径，并行流相比单流更充分地利用了实例可用的突发带宽。提高并行度也会改变 CPU 负载、拥塞和成本。调整 Kafka fetcher 或传输并发数之前，应先检查实际实例/路径限制；这些测量既不支持“每个连接都被限制在 5 Gbps”，也不支持“一个 AZ 总能使带宽翻倍”。

### 3 分钟持续测试与突发积分

报告中的 m5.xlarge 基线为 1.25 Gbps，尽力而为的峰值最高可达 10 Gbps。历史上的四流跨 AZ 测试持续 180 s，并以 10 s 为间隔记录数据（`iperf3 -c 10.0.3.65 -p 5201 -t 180 -P 4 -i 10 -J`）。该 IP 属于记录中的测试工作负载；新测试前请先获取当前 Pod IP。

| 项目 | 值 |
|---|---|
| 每个 10 s 时间间隔的 Gbps（共 18 个间隔） | 9.94、9.93 ×12、9.92、9.93 ×4（**最小值 9.92，最大值 9.94**） |
| 总发送量 | 223,376,179,200 B = 180.0 s 内 **223.4 GB**（9.93 Gbps） |
| 重传次数 | 44,842（约 249/s；每个 10 s 间隔为 2,273–2,669 次） |
| CPU | 客户端 30.7%（system 30.1%），服务器 54.2%（system 52.2%） |

**在 180 s 内未观察到吞吐量降至 1.25 Gbps。** 这并不能证明积分无限，也不能保证带宽持续处于峰值。AWS 说明，突发为可变的尽力而为模式；积分耗尽后会限流至接近基线。规划长时间备份和重新平衡时，应依据适用的基线和实测工作负载需求，而不是从这次短时测试外推。

## 测量 3. 跨 AZ 数据传输成本模型

本节保留报告中的成本计算，作为估算值。基准测试提供了有效载荷字节数和公开标价，并未提供成本和使用情况报告（CUR）或发票。

对于同一 Region 内 AZ 之间通过 EC2 私有 IP 直接传输数据，[EC2 定价页面](https://aws.amazon.com/ec2/pricing/on-demand/)说明每端收费 $0.01/GB。报告中的公开 Pricing API 项目为 `APN2-DataTransfer-Regional-Bytes`，价格为 **$0.0100000000 USD/GB**。`get-products` 返回的是目录价格，不是特定账户的实付费率。单向有效载荷传输可能同时产生发送端“out”和接收端“in”费用；并不要求存在同等规模的反向传输。其他 AWS 服务路径可能遵循不同的计费规则。

| 场景 | 历史十进制 GB 模型中的有效载荷量 | 估算成本（模型 GB × $0.01 × 2） |
|---|---|---|
| 180 s 测试（测得的有效载荷；估算成本） | 223.4 GB | 223.4 × $0.01 ≈ **每端 $2.23，总计 $4.47** |
| 测量 2 中的跨 AZ iperf3 传输（12.41 + 24.85 + 223.38 GB） | 260.6 GB | 每端约 $2.61，**总计约 $5.21**（不含其他流量） |
| 30 天内平均每秒有 1 Gbps 跨 AZ 传输（**假设**） | 0.125 GB/s × 86,400 s × 30 天 = 324,000 GB ≈ **324 TB** | 324,000 × $0.02 ≈ **$6,480 / 月** |
| 横跨 3 个 AZ 的 RF3 StatefulSet，leader ingest 为 100 MiB/s（**假设**，仅计算复制流量） | 两个 follower 均位于其他 AZ → 2 × 100 MiB/s = 209,715,200 B/s × 2,592,000 s ≈ 543,600 GB ≈ **544 TB / 月** | 543,600 × $0.02 ≈ **$10,870 / 月** |

这四行成本均采用原始的**十进制换算方式，即 1 GB = 10⁹ 有效载荷字节**，作为建模假设。本次审核未能确认 EC2 的计费使用量是否采用相同换算方式。精确原始总量为：持续测试 223,376,179,200 B；全部三次跨 AZ iperf3 测试共 260,633,264,128 B。请根据 [CUR 数据传输记录](https://docs.aws.amazon.com/cur/latest/userguide/cur-data-transfers-charges.html)，核对实际计量单位、费率、两个计费端点、协议开销/重传以及适用的抵扣或折扣。后两行还假设 30 天内持续产生流量；复制流量不包括 producer/consumer 流量。**$4.47 和 $5.21 是估算值，并非已证实的实际支出。**

**运维人员应采取的措施。**

- **在适用情况下优先选择合适的本地端点。** 当前 Kubernetes 文档使用 `Service.spec.trafficDistribution: PreferSameZone`；`PreferClose` 是已弃用的别名。这只是优先策略，会在必要时回退，并非严格的 AZ 限制。请检查 API server、kube-proxy 版本和功能支持情况；本集群记录的是 1.36 控制平面搭配 1.35 kube-proxy。此偏好和应用 Service 路径均未经过测量，也不会影响直接使用 Pod IP 的流量。
- **在本地性与容错之间取得平衡。** 采用 AZ 感知型读取或客户端可减少不必要的数据传输，但将所有 RF3 副本迁移到一个 AZ 会失去 AZ 故障保护。请保留所需的副本/故障转移设计；参见 [Zonal Cluster Operations](../ops/15-zonal-operations-guide.md)。
- **测量两个计费端点。** 跟踪备份、重新平衡和重放的源/目标 AZ 及计量流量。汇总相关的“in”和“out”使用记录；这些记录可能属于不同账户。不要仅凭有效载荷字节数推断最终账单。

## 测量 4. DNS：ndots:5 导致的查询放大

![在 ndots:5 下，一次 glibc 查询会遍历四个搜索后缀，每个后缀分别查询 A+AAAA（8 次 NXDOMAIN，共 10 次查询），之后绝对名称才得到应答；名称末尾加点的查询则以 2 次查询结束。](../.gitbook/assets/en-networking-06-pod-network-benchmark-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-06-pod-network-benchmark-1.html)

该图展示了记录中的 glibc 搜索序列。其中的 4.37 ms 截止于报告的 A 记录响应，并非完整的 `getaddrinfo` 调用；指向上游的箭头仅作说明，因为 Pod 抓包未观测到该段路径。“cache 30”是 TTL 上限，并不保证缓存命中 30 秒。

记录中的 Pod 有四个搜索域，且设置了 `ndots:5`；该配置并非所有 EKS、DNS 策略、操作系统或节点设置都通用。对于此 glibc `AF_UNSPEC` 查询，每个候选名称都请求了 A 和 AAAA；四个搜索候选名称均返回 NXDOMAIN，之后绝对 STS 名称才解析成功。A/AAAA 的并发方式和查询数可能会随解析器选项、地址族、提前成功、重试和 TCP 回退而变化。历史抓包使用 `tcpdump -i eth0 -nn udp port 53`，只能观察 UDP DNS。报告描述了首次进程查询和随后 20 次计时重复查询；进程首次调用并不能证明 CoreDNS 或上游缓存当时处于冷状态。参见 [Kubernetes Pod DNS 配置](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)。

### 单次解析发送的查询数和预热延迟（重复 20 次），单位 ms

| Pod / ndots | 名称（点号数） | 发送的查询数 | NXDOMAIN 响应数 | 预热最小值 | **中位数** | p90 | 最大值 |
|---|---|---|---|---|---|---|---|
| default / 5 | `kubernetes.default`（1） | 4 | 2 | 0.87 | **1.71** | 1.97 | 2.61 |
| default / 5 | `kubernetes.default.svc.cluster.local`（4） | **10** | 8 | 1.53 | **3.63** | 4.45 | 6.41 |
| default / 5 | `kubernetes.default.svc.cluster.local.`（名称末尾有点） | 2 | 0 | 0.33 | **0.46** | 1.09 | 1.58 |
| default / 5 | `sts.ap-northeast-2.amazonaws.com`（3） | **10** | 8 | 3.08 | **3.78** | 4.66 | 4.84 |
| default / 5 | `sts.ap-northeast-2.amazonaws.com.`（名称末尾有点） | 2 | 0 | 0.42 | **0.80** | 1.25 | 2.17 |
| default / 5 | `www.amazon.com`（2） | **10** | 8 | 2.51 | **3.46** | 3.74 | 5.86 |
| ndots1 / 1 | `kubernetes.default`（1） | **6** | 4 | 1.16 | **2.04** | 2.80 | 4.54 |
| ndots1 / 1 | `kubernetes.default.svc.cluster.local`（4） | 2 | 0 | 0.35 | **0.97** | 1.08 | 1.35 |
| ndots1 / 1 | `kubernetes.default.svc.cluster.local.` | 2 | 0 | 0.34 | **0.40** | 0.97 | 1.17 |
| ndots1 / 1 | `sts.ap-northeast-2.amazonaws.com`（3） | 2 | 0 | 0.45 | **0.54** | 1.22 | 1.42 |
| ndots1 / 1 | `sts.ap-northeast-2.amazonaws.com.` | 2 | 0 | 0.47 | **0.75** | 1.20 | 1.30 |
| ndots1 / 1 | `www.amazon.com`（2） | 2 | 0 | 0.63 | **0.90** | 1.27 | 2.74 |

报告中的进程首次调用时间为：default / `sts` 6.22 ms、default / `sts.` 2.87 ms、default / `www.amazon.com` 9.58 ms、default / `kubernetes.default.svc.cluster.local` 7.40 ms、ndots1 / `kubernetes.default` 10.52 ms，以及 ndots1 / `sts` 2.84 ms。这些时间包含解析器初始化开销，与下方的网络数据包时间线不同。

**如何解读。** 在这些样本中，不带末尾点的外部名称和集群 FQDN 都产生了 **10 次查询 / 8 次 NXDOMAIN**。STS 名称末尾加点后，中位数从 3.78 降至 0.80 ms；集群 FQDN 从 3.63 降至 0.46 ms。`kubernetes.default` 在第二个搜索候选名称处解析成功，因此只需四次查询：搜索扩展并不总会遍历完整列表。[CoreDNS cache](https://coredns.io/plugins/cache/) 可以缓存否定响应，但 `cache 30` 设置的是 TTL 上限；响应 TTL 和最小值仍然适用，每个副本也有自己的缓存。除非另行配置，Kubernetes 插件的默认 TTL 为 5 s。即使命中缓存，顺序查询仍会发生，但本次抓包不能证明所有预热查询都避免了上游流量。

### 查询过程：对 `sts.ap-northeast-2.amazonaws.com` 进行一次冷解析（ndots:5，tcpdump，时间相对首个数据包，单位 ms）

| t (ms) | 发送到 172.20.0.10 的候选名称（并行查询 A + AAAA） | 响应 |
|---|---|---|
| 0.00 | `sts.ap-northeast-2.amazonaws.com.bench-net.svc.cluster.local.` | 0.92 / 1.14 时返回 NXDOMAIN（权威响应，CoreDNS kubernetes 插件） |
| 1.21 | `sts.ap-northeast-2.amazonaws.com.svc.cluster.local.` | 2.01 / 2.26 时返回 NXDOMAIN |
| 2.32 | `sts.ap-northeast-2.amazonaws.com.cluster.local.` | 3.15 / 3.41 时返回 NXDOMAIN |
| 3.47 | `sts.ap-northeast-2.amazonaws.com.ap-northeast-2.compute.internal.` | 3.68 / 3.93 时返回 NXDOMAIN（转发到 VPC 解析器，非权威响应） |
| 3.99 | `sts.ap-northeast-2.amazonaws.com.` | 4.37 时返回 **A 10.0.3.84、A 10.0.2.129**（AAAA：无数据） |

表中记录了 10 次查询和 8 次 NXDOMAIN。**4.37 ms** 是从第一个查询到报告的 A 响应之间的时间；未列出 AAAA 完成时间，因此这不是进程首次调用的完整 6.22 ms。各候选名称的 RTT 并非都为 0.8–1.1 ms：第四组查询耗时 0.21 / 0.46 ms，最后一个 A 查询耗时 0.38 ms。kube-proxy iptables 会为新的 conntrack 流选择一个端点，而不是为每个数据包独立选择；A/AAAA 请求可能共享同一流。若两个端点被等概率选中，那么一半新流会落到其中一个端点，这只是说明性预期，**并非实测的跨 AZ DNS 查询比例**。显示 Service VIP `172.20.0.10` 的 Pod 抓包无法确定所选后端的 AZ。原始报告将两个 STS 私有地址归因于接口端点 ENI，并记录了集群 FQDN 的转发候选名称耗时 2.2 ms / 网络传输过程耗时 5.6 ms，而名称末尾加点时为 0.4–0.5 ms；这些是不同的观测结果。

### `ndots:1` 的作用及其副作用

- **本次样本中的外部名称**：10 → **2 次查询**，中位数约从 3.5–3.8 降至 **0.5–0.9 ms**。收益取决于名称和解析器行为。
- **短名称可能会多出一次失败尝试。** 此处 `kubernetes.default` 含一个点，达到 `ndots:1` 的要求，因此 glibc 首先尝试了 `kubernetes.default.`。CoreDNS 将其转发并在报告的 1.6 ms 后收到 NXDOMAIN，随后尝试带命名空间后缀的名称，最后在 `svc.cluster.local` 下成功解析到 `172.20.0.1`：共 6 次查询、4 次 NXDOMAIN，中位数为 2.04 ms，而原来为 1.71 ms。这可能会将看似内部的名称泄露给上游。更改 `ndots` 前，请测试每个应用的 Service 命名方式；使用完整 Service 名称可以减少这种不确定性。
- **名称末尾加点可使解析器将其视为绝对名称**，从而在此解析器中避免搜索扩展。但这不能保证只产生两次网络查询，也不能保证在重试、地址族设置不同或使用缓存时延迟固定。

### 查询放大计算（推导值）

假设**响应模式相同**、应用没有 DNS 缓存且每个请求都执行一次解析，那么每秒 1,000 次解析 × 每次 10 次查询 = 每秒 10,000 次查询；两次查询的形式则为每秒 2,000 次。在 10,000 次查询中，8,000 次（80%）会收到 NXDOMAIN。这只是查询数量模型，并非 CoreDNS CPU 或跨 AZ 查询比例的测量值。观测到的中位数差异为：STS 3.78 − 0.80 = 2.98 ms，集群 FQDN 3.63 − 0.46 = 3.17 ms；它们不是固定的每请求额外开销。

**可使用实际应用测试以下选项：**

- 客户端支持时使用绝对 DNS 名称。不要不加判断地在 HTTPS 或 AWS SDK 端点 URL 后追加点号：Host 处理、SNI、证书验证和请求签名仍须正常工作。
- 结合短名称行为和应用 DNS 缓存，评估 `dnsConfig: {options: [{name: ndots, value: "1"}]}`。
- 适用时评估 [NodeLocal DNSCache](https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/)。缓存命中会留在本地；缓存未命中时仍可能向上游查询。当前的 [EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html) 已将 node-local CoreDNS 作为系统服务运行；纯 Auto Mode 集群不需要 CoreDNS Deployment，而混合集群中的非 Auto 节点仍然需要。
- [CoreDNS autopath](https://coredns.io/plugins/autopath/) 可以在服务器端完成搜索扩展，但其 Kubernetes 集成要求启用 `pods verified`、能够看到发起查询的 Pod IP，并具备相关的 Pod 监视权限/RBAC/内存。记录中的 `pods insecure` 配置不满足这些要求。本次未测试此优化。

## 如何复现：修订后的步骤

请在获批的隔离实验环境中，使用专用于本测试且未被占用的命名空间。将调整后的首个测试工作负载保存为 `bench-net.yaml`，并将两个 DNS 对象保存为 `bench-dns.yaml`；确保命名空间名称一致。应用配置前，请检查 NodePool 容量、AZ、调度和抓包权限。不要为了运行测试而放宽生产环境的准入或安全控制。这些限定时长的命令仍可能使节点饱和并产生费用。

所有命令都在**运维人员的 Bash shell** 中运行；不要进入 `cli` 的交互式 shell。审核检查了语法和部分本地工具行为，但没有部署此测试工作负载，也没有在 EKS 上运行这些网络负载。

**1. 部署调整后的测试工作负载并验证放置情况。**

```bash
set -euo pipefail
BENCH_NS=bench-net
kubectl apply -f bench-net.yaml
kubectl -n "$BENCH_NS" wait --for=condition=Ready \
  pod/cli pod/srv-same pod/srv-a pod/srv-b --timeout=300s
kubectl -n "$BENCH_NS" get pods -o wide
kubectl get nodes -L topology.kubernetes.io/zone,node.kubernetes.io/instance-type,karpenter.sh/nodepool

SAME_IP=$(kubectl -n "$BENCH_NS" get pod srv-same -o jsonpath='{.status.podIP}')
AZ_IP=$(kubectl -n "$BENCH_NS" get pod srv-a -o jsonpath='{.status.podIP}')
CROSS_IP=$(kubectl -n "$BENCH_NS" get pod srv-b -o jsonpath='{.status.podIP}')
: "${SAME_IP:?missing srv-same IP}" "${AZ_IP:?missing srv-a IP}" "${CROSS_IP:?missing srv-b IP}"
for bench_pod in srv-same srv-a srv-b; do
  kubectl -n "$BENCH_NS" logs "$bench_pod" --tail=30
  kubectl -n "$BENCH_NS" exec "$bench_pod" -- ss -lnt
done
for bench_ip in "$SAME_IP" "$AZ_IP" "$CROSS_IP"; do
  kubectl -n "$BENCH_NS" exec cli -- \
    curl --fail --silent --show-error --max-time 5 "http://$bench_ip:8080/" >/dev/null
done
```

继续前，请确认 `cli` 与 `srv-same` 位于同一节点，`srv-a` 位于同一 AZ 的不同节点，而 `srv-b` 位于另一个 AZ。检查服务器是否在 5201/8080/8079 端口上监听，以及是否有启动错误：Pod Ready 并不能证明这些进程正在监听，因为历史测试工作负载没有 readiness probe。请记录节点 ID、IP、镜像 ID 以及实际的 `iperf3 --version` / `fortio version`。如果 Pod 被重新创建，请停止测试并更新地址。

**2. RTT 和一次参考 HTTP 请求。**

```bash
for bench_ip in "$SAME_IP" "$AZ_IP" "$CROSS_IP"; do
  kubectl -n "$BENCH_NS" exec cli -- ping -c 200 -i 0.05 -q "$bench_ip"
done
kubectl -n "$BENCH_NS" exec cli -- curl --fail --silent --show-error --max-time 5 \
  -o /dev/null -w 'connect=%{time_connect} total=%{time_total}\n' "http://$CROSS_IP:8080/"
```

**3. 吞吐量测试，限制运行时长，并将输出文件保存在运维人员本地。**

```bash
for bench_ip in "$SAME_IP" "$AZ_IP" "$CROSS_IP"; do
  kubectl -n "$BENCH_NS" exec cli -- iperf3 -c "$bench_ip" -p 5201 -t 20 -P 1 -J > "t1-$bench_ip-P1.json"
  kubectl -n "$BENCH_NS" exec cli -- iperf3 -c "$bench_ip" -p 5201 -t 20 -P 8 -J > "t1-$bench_ip-P8.json"
done
kubectl -n "$BENCH_NS" exec cli -- \
  iperf3 -c "$CROSS_IP" -p 5201 -t 180 -P 4 -i 10 -J > t1-cross-sustained180-P4.json
```

除了退出状态，还要检查 JSON 错误。读取 `end.sum_sent.bits_per_second`、`end.sum_sent.retransmits`、`end.cpu_utilization_percent.host_total` / `remote_total` 以及 `end.streams[].sender.mean_rtt` / `max_snd_cwnd`。iperf3 3.19 的进程 CPU 中，一个 CPU 在整个运行时段内的时间占比 100% 即为 100%；多线程时数值可以超过 100%。TCP RTT 字段的单位为微秒。

**4. 请求延迟。对每个经验证的服务器地址重复执行。**

```bash
for bench_ip in "$SAME_IP" "$AZ_IP" "$CROSS_IP"; do
  kubectl -n "$BENCH_NS" exec cli -- fortio load -quiet -r 0.00001 -json - \
    -qps 100 -c 4 -t 60s "http://$bench_ip:8080/" > "http-$bench_ip.json"
  kubectl -n "$BENCH_NS" exec cli -- fortio load -quiet -r 0.00001 -json - \
    -qps 100 -c 4 -t 30s -keepalive=false "http://$bench_ip:8080/" > "new-connection-$bench_ip.json"
  kubectl -n "$BENCH_NS" exec cli -- fortio load -quiet -r 0.00001 -json - \
    -qps 0 -c 16 -t 20s "http://$bench_ip:8080/" > "closed-loop-$bench_ip.json"
  kubectl -n "$BENCH_NS" exec cli -- fortio load -quiet -r 0.00001 -json - \
    -grpc -ping -qps 100 -c 4 -t 30s "$bench_ip:8079" > "grpc-$bench_ip.json"
done
```

在 Fortio 1.69.5 中，`-r` 是直方图的最低桶分辨率，单位为秒：默认值 `0.001` 即 1 ms，`0.00001` 即 10 µs；较大的桶宽可能增大。百分位数在桶边界内插值，包括边缘处观测到的最小值/最大值。因此，只有一个桶有数据，**并不意味着 p50 = 0.5 ms**。报告舍弃了首次粗分辨率测试的百分位数，随后以 10 µs 分辨率重新运行；应保留这一过程记录，但不要因此称所有插值百分位数都是伪数据。表中的多个尾延迟值和新建连接中位数都超过 1 ms。请将完整直方图和错误计数器与平均值一并保存。

**5. DNS：将单次查询抓包与计时重复查询分开进行。**

```bash
kubectl apply -f bench-dns.yaml
kubectl -n "$BENCH_NS" wait --for=condition=Ready pod/dns-default pod/dns-ndots1 --timeout=300s
for bench_pod in dns-default dns-ndots1; do
  kubectl -n "$BENCH_NS" exec "$bench_pod" -c app -- cat /etc/resolv.conf
  kubectl -n "$BENCH_NS" exec "$bench_pod" -c app -- ldd --version
done
```

在终端 1 中，先启动抓包，再执行单次查询。此过滤器同时包含普通 UDP 和 TCP 的 53 端口 DNS 流量，但不包括加密 DNS 或 CoreDNS 的上游路径。完成该次查询后，使用 Ctrl-C 停止抓包，然后再进行预热重复查询。

```bash
kubectl -n bench-net exec -it dns-default -c sniffer -- \
  tcpdump -l -i eth0 -nn '(udp or tcp) and port 53'
```

在终端 2 中创建以下本地辅助脚本，并通过 **`kubectl exec -i`** 将其传入。第一种模式只执行一次解析器调用。预热模式先执行一次不计时的预热调用，再在同一进程中执行 20 次查询；此修订流程明确了抓包边界。

```bash
cat > dns-probe.py <<'PY'
import json
import socket
import statistics
import sys
import time

name, mode = sys.argv[1:3]
if mode not in ("first", "warm"):
    raise SystemExit("mode must be first or warm")

def one():
    started = time.perf_counter()
    socket.getaddrinfo(name, 80, socket.AF_UNSPEC, socket.SOCK_STREAM)
    return (time.perf_counter() - started) * 1000

first = one()
if mode == "first":
    print(json.dumps({"name": name, "first_process_ms": first}))
else:
    samples = [one() for _ in range(20)]
    ordered = sorted(samples)
    print(json.dumps({
        "name": name, "warmup_ms": first, "samples_ms": samples,
        "min_ms": ordered[0], "median_ms": statistics.median(ordered),
        "p90_ms": ordered[17], "max_ms": ordered[-1],
    }))
PY
BENCH_NS=bench-net
DNS_POD=dns-default
DNS_NAME=sts.ap-northeast-2.amazonaws.com
kubectl -n "$BENCH_NS" exec -i "$DNS_POD" -c app -- \
  python3 - "$DNS_NAME" first < dns-probe.py
```

停止抓包后：

```bash
kubectl -n "$BENCH_NS" exec -i "$DNS_POD" -c app -- \
  python3 - "$DNS_NAME" warm < dns-probe.py
```

对表中的名称重复测试，并将 `DNS_POD=dns-ndots1`，同时更改抓包目标。只统计首次查询时间窗口内的查询/响应对；不要把 21 次查询当作一次。请使用匹配的镜像摘要、解析器版本和配置，但需预期计时结果和缓存状态会有所不同。本页未提供原始镜像摘要以及完整的数据包/JSON 工件，因此无法保证精确复现。

**6. 仅清理本次测试创建的资源。** 如果 `bench-net` 专为本次测试创建，请在保存结果后使用 `kubectl delete namespace bench-net` 删除。请另行核实剩余节点和费用。Karpenter 是否整合节点取决于其策略、预算和其他工作负载；删除命名空间并不能保证节点会立即移除。`do-not-disrupt` 并不能防止所有强制中断方式。

## 注意事项

- **节点是全新启动的，但并非完全独占。** Karpenter 为本次测试启动三个 m5.xlarge 节点后不久，整合操作将其他命名空间中的少量 Pod 移到了这些节点上（一个移至 `cli` 节点，三个移至 `srv-b` 节点；这些是与基准测试流量无关、流量较低的内部服务和控制器）。测试期间它们处于空闲或低流量状态，负载也只以不超过 180 s 的突发形式运行。`cli` 节点的 CPU *requests* 为 3901m / 3920m（99%），但这并不能说明实际利用率。
- **单次运行（每个单元格 n = 1，测试一天）。** 没有独立重复测试来估算方差。由于样本量如此有限，排序、比例和因果解释也受到限制；这些结果都不是 SLA。
- **未测量应用 ClusterIP 和流量分配。** 报告称，在基准测试命名空间中创建 Service 失败，错误为 `failed calling webhook "mservice.elbv2.k8s.aws": … no endpoints available for service "aws-load-balancer-webhook-service"`。一个失败的 `failurePolicy: Fail` Webhook 会拒绝匹配的请求；其规则、命名空间/对象选择器和匹配条件决定影响范围。这一历史事件不代表当前集群无法创建任何 Service。基准测试没有绕过该 Webhook。DNS 仍使用现有的 `kube-dns` Service。参见[故障排查手册](../ops/16-troubleshooting-playbook.md)。
- **未采集 ENA allowance 计数器。** `ethtool -S` 必须在具备适当访问权限的情况下，针对主机实际的 ENA 接口运行；Pod 自身的 `eth0` 通常是 veth，仅使用 `hostNetwork` 并不能证明设备或权限正确。相关计数器包括 `bw_in_allowance_exceeded`、`bw_out_allowance_exceeded`、`pps_allowance_exceeded`、`conntrack_allowance_exceeded` 和 `linklocal_allowance_exceeded`。重传不能替代这些测量。
- **只是没有在 180 s 内观察到突发积分耗尽。** 对于“最高可达”类型的实例，持续时间更长的传输可能会被限流至接近基线（1.25 Gbps）。本次未测试超过 180 s 的情况。
- **DNS 缓存状态未受控。** 进程首次查询与重复查询有所不同，但 `cache 30` 并不能保证缓存命中 30 s。副本选择和上游状态都可能影响两组计时数据；报告中的比较是观察结果。
- **同节点 CPU 压力是合理推测。** 客户端进程 CPU 达到 99.8%，支持将 29.97 Gbps 结果作此解读；但这并不能确定所有瓶颈，也不能说明 29.97 / 48.15 Gbps 能推广到其他实例。
- **未比较其他 CNI 模式和策略执行情况。** 未启用前缀委派和 Pod 的安全组；该命名空间没有 NetworkPolicy。这些裸 Pod 也不能验证 VPC CNI 是否会对其支持的控制器管理型工作负载正确执行 NetworkPolicy。

## 延伸阅读

- [Amazon VPC CNI](./01-vpc-cni.md)：这些测量所涉及的数据平面（Pod 直接获得 VPC IP、前缀委派、ENI/IP 预热）
- [Zonal Cluster Operations](../ops/15-zonal-operations-guide.md)：与 AZ 对齐的放置和 AZ 故障转移设计，可降低测量 3 中的账单
- [故障排查手册](../ops/16-troubleshooting-playbook.md)：Webhook 故障诊断；此处的事件是历史事件
- [Sidecar 与 Ambient 模式选择指南](../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)：硬件/工作负载不同的独立实验；其中的 +1.29 ms 是整个场景的差值
- [EBS gp2 与 gp3 实测基准测试](../storage/01-ebs-gp2-gp3-benchmark.md)：同一集群中的存储路径实测
- [EKS 上的 Kafka 实测基准测试](../data-on-eks/kafka/09-kafka-benchmark.md)：复制流量、流限制和可用性权衡
- [指南路线图：实测基准测试系列](../roadmap.md)
- [测验：Pod 网络基准测试](../quizzes/networking/06-pod-network-benchmark-quiz.md)


### 审核中使用的主要参考资料

- [Fortio 1.69.5 直方图实现](https://github.com/fortio/fortio/blob/v1.69.5/stats/stats.go) · [CLI 标志](https://github.com/fortio/fortio/blob/v1.69.5/cli/fortio_main.go)
- [glibc 2.41 搜索顺序](https://github.com/bminor/glibc/blob/glibc-2.41/resolv/res_query.c) · [A/AAAA 传输](https://github.com/bminor/glibc/blob/glibc-2.41/resolv/res_send.c)
- [CoreDNS Kubernetes / autopath 要求](https://coredns.io/plugins/kubernetes/)
- [Kubernetes Service 流量分配](https://kubernetes.io/docs/concepts/services-networking/service/) · [虚拟 IP 处理](https://kubernetes.io/docs/reference/networking/virtual-ips/)
- [EC2 ENA 网络指标](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/monitoring-network-performance-ena.html)
- [Karpenter 中断和清理条件](https://karpenter.sh/docs/concepts/disruption/)

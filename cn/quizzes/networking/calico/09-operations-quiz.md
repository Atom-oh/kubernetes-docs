# Calico 运维测验

> **相关文档**: [运维](../../../networking/calico/09-operations.md)
> **最后更新**: February 22, 2026

## 测验

1. Calico 的三种主要安装方法是什么？
   - A) Docker、Podman、containerd
   - B) 基于清单的 (kubectl)、基于 Operator 的 (Tigera)、Helm
   - C) CLI、GUI、API
   - D) 二进制文件、包管理器、源代码编译

<details>
<summary>显示答案</summary>

**答案：B) 基于清单的 (kubectl)、基于 Operator 的 (Tigera)、Helm**

**说明：**
Calico 可通过以下方式安装：1) 使用 kubectl apply 应用 YAML 清单的基于清单的安装，2) 使用 Tigera Operator 的基于 Operator 的安装（推荐），或 3) 用于可自定义部署的 Helm chart。对于生产环境，通常推荐 Operator 方法，因为它会管理 Calico 生命周期。

</details>

2. 哪个 calicoctl 命令会显示 Calico Node 的状态，包括 BGP 对等体状态？
   - A) calicoctl get nodes
   - B) calicoctl node status
   - C) calicoctl describe node
   - D) calicoctl show peers

<details>
<summary>显示答案</summary>

**答案：B) calicoctl node status**

**说明：**
`calicoctl node status` 命令显示 Calico Node 的状态，包括 BGP 对等连接信息，展示哪些对等体已建立、其状态以及任何连接问题。这对于排查 BGP 路由问题至关重要。

</details>

3. 哪个命令会显示跨 Node 的 IPAM block 分配情况？
   - A) calicoctl ipam show --show-blocks
   - B) calicoctl get ipamblocks
   - C) kubectl get ipamblocks -o wide
   - D) calicoctl describe ipam

<details>
<summary>显示答案</summary>

**答案：A) calicoctl ipam show --show-blocks**

**说明：**
`calicoctl ipam show --show-blocks` 命令显示详细的 IPAM 信息，包括哪些 IP block 被分配给哪些 Node、每个 block 的利用率，以及整体 IP pool 统计信息。这对于诊断 IP 分配问题至关重要。

</details>

4. 哪个 Prometheus metrics endpoint 会公开 Felix 性能和 Policy 统计信息？
   - A) :9090/metrics
   - B) :9091/metrics
   - C) :9094/metrics
   - D) :8080/metrics

<details>
<summary>显示答案</summary>

**答案：B) :9091/metrics**

**说明：**
Felix 默认在 port 9091 上公开 Prometheus metrics。这些 metrics 包括 Policy rule 数量、dataplane 编程延迟、iptables/eBPF 统计数据和错误计数。必须在 FelixConfiguration 中通过 `prometheusMetricsEnabled: true` 启用此功能。

</details>

5. Typha 的 Prometheus metrics endpoint 使用哪个 port？
   - A) :9091/metrics
   - B) :9093/metrics
   - C) :9094/metrics
   - D) :9095/metrics

<details>
<summary>显示答案</summary>

**答案：B) :9093/metrics**

**说明：**
Typha 默认在 port 9093 上公开 Prometheus metrics。Typha metrics 包括与 Felix 实例的连接数量、datastore 同步延迟和 cache 统计信息。在大型 cluster 中，监控 Typha 对于了解 datastore fan-out 性能非常重要。

</details>

6. 一个 Pod 无法获得 IP address。首先应检查什么？
   - A) kube-proxy logs
   - B) IPPool 可用性和 IPAM block 分配
   - C) DNS 配置
   - D) Node CPU 使用率

<details>
<summary>显示答案</summary>

**答案：B) IPPool 可用性和 IPAM block 分配**

**说明：**
当 Pod 无法获得 IP 时，首先使用 `calicoctl ipam show` 检查 IPPool 是否有可用 address。确认 IPAM block 能否分配给该 Node，并且 IPPool selector 与该 Node 匹配。还应检查 Felix logs 中与 IPAM 相关的错误。

</details>

7. 当 Node 之间的 BGP 对等连接无法建立时，应验证什么？
   - A) Pod DNS 解析
   - B) BGP port (179) 上的网络连接、BGPConfiguration 和 Node selector
   - C) Persistent volume binding
   - D) Service account token

<details>
<summary>显示答案</summary>

**答案：B) BGP port (179) 上的网络连接、BGPConfiguration 和 Node selector**

**说明：**
对于 BGP 对等连接问题，请验证：1) Node 之间 TCP port 179 上的网络连接，2) BGPConfiguration 和 BGPPeer resource 是否已正确定义，3) Node selector 是否匹配预期的 Node，4) 检查 `calicoctl node status` 和 BIRD logs 以获取特定的对等连接错误。

</details>

8. 已应用 NetworkPolicy，但流量未被阻止。一个可能的原因是什么？
   - A) cluster 使用了过多内存
   - B) Policy selector 未匹配目标 Pod，或 Policy order/tier 不正确
   - C) Node 需要重启
   - D) Kubernetes 版本过旧

<details>
<summary>显示答案</summary>

**答案：B) Policy selector 未匹配目标 Pod，或 Policy order/tier 不正确**

**说明：**
当 Policy 未按预期工作时，请验证：1) Pod selector 是否正确匹配目标 Pod（检查 label），2) Namespace selector 是否正确，3) Policy tier 排序（更高优先级的 tier 会先评估），4) 评估顺序中是否较早存在冲突的 Allow Policy。使用 `calicoctl get policy` 查看已应用的 Policy。

</details>

9. 升级 Calico 版本的推荐流程是什么？
   - A) 删除所有 resource 并重新安装
   - B) 按照特定版本的迁移指南进行原地升级
   - C) 创建新 cluster 并迁移 workload
   - D) Calico 会随 Kubernetes 自动升级

<details>
<summary>显示答案</summary>

**答案：B) 按照特定版本的迁移指南进行原地升级**

**说明：**
Calico 升级应遵循适用于您的安装方法的官方升级文档。这通常涉及将 Operator 或清单更新到新版本。请查看特定版本的迁移说明，因为某些升级需要额外步骤。请先在非生产环境中测试。

</details>

10. Calico NetworkPolicy 的默认拒绝最佳实践是什么？
    - A) 永远不要使用拒绝 Policy
    - B) 将默认拒绝 Policy 应用于 Namespace，然后显式允许所需流量
    - C) 仅拒绝来自外部 source 的流量
    - D) 拒绝所有 egress，但允许所有 ingress

<details>
<summary>显示答案</summary>

**答案：B) 将默认拒绝 Policy 应用于 Namespace，然后显式允许所需流量**

**说明：**
安全最佳实践是应用默认拒绝 Policy，阻止流向 Namespace 中 Pod 的所有 ingress（以及可选的 egress）流量，然后创建特定 Policy，仅允许所需的流量流向。这实现了网络访问的最小权限原则。

</details>

11. 如何配置 Calico 以导出用于网络可见性的 flow log？
    - A) 在 kube-apiserver flag 中启用
    - B) 在 FelixConfiguration 中配置 FlowLogsFileReporter 或 FlowLogsNetworkReporter
    - C) flow log 默认始终启用
    - D) 安装单独的 flow log Operator

<details>
<summary>显示答案</summary>

**答案：B) 在 FelixConfiguration 中配置 FlowLogsFileReporter 或 FlowLogsNetworkReporter**

**说明：**
通过 FelixConfiguration 配置 flow log，方法是启用 FlowLogsFileReporter（写入 file）或 FlowLogsNetworkReporter（发送到 collector）。配置 log interval、aggregation level 和要捕获的 flow 等参数。注意：完整的 flow log 功能需要 Calico Enterprise。

</details>

12. calicoctl 连接到 datastore 必须设置哪些 environment variable？
    - A) CALICO_HOST 和 CALICO_PORT
    - B) DATASTORE_TYPE 和 KUBECONFIG（或用于 etcd datastore 的 ETCD_ENDPOINTS）
    - C) CALICO_API_SERVER 和 CALICO_TOKEN
    - D) CNI_PATH 和 CNI_CONFIG

<details>
<summary>显示答案</summary>

**答案：B) DATASTORE_TYPE 和 KUBECONFIG（或用于 etcd datastore 的 ETCD_ENDPOINTS）**

**说明：**
要让 calicoctl 连接到 datastore，请设置 `DATASTORE_TYPE=kubernetes`，并确保 KUBECONFIG 指向有效的 kubeconfig file。对于 etcd datastore，请设置 `DATASTORE_TYPE=etcdv3` 以及 `ETCD_ENDPOINTS`，并可选择设置与 TLS 相关的 variable 以实现安全连接。

</details>

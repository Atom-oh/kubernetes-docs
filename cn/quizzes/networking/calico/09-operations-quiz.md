# 运维测验

> **相关文档**: [运维](../../../networking/calico/09-operations.md)
> **最后更新**: 2026 年 9 月 12 日

## 测验

1. 哪项准确说明了 Calico 的安装管理方式？
   - A) 为实现冗余，同时安装清单和 Helm Operator
   - B) 根据平台选择由 Operator/Helm 或直接清单负责安装
   - C) 每种安装都必须启用 BPF
   - D) 全新的 Operator 清单会自动包含所有 Calico CRD

<details>
<summary>显示答案</summary>

**答案：B) 根据平台选择由 Operator/Helm 或直接清单负责安装**

**说明：**
Helm chart 会安装 Tigera Operator。应只选择一个安装管理者、固定版本、管理与版本匹配的 CRD，并选择实际使用的网络配置。这里的示例是在自管理 Linux 上使用完整 Calico CNI；EKS VPC CNI 的仅策略配置是另一种方案。

</details>

2. `calicoctl node status` 会检查什么？
   - A) kubeconfig 上下文中的每个节点
   - B) 本地节点的 BGP 状态，并要求具备相应的节点访问权限
   - C) 每个应用的 HTTP 就绪状态
   - D) 所有 IPAM 地址分配泄漏

<details>
<summary>显示答案</summary>

**答案：B) 本地节点的 BGP 状态，并要求具备相应的节点访问权限**

**说明：**
这是本地 BGP 诊断命令，不是集群范围的就绪探针。禁用 BGP 的配置不需要得到 BGP 成功结果。应选择受影响的节点，并在适用时检查该节点实际使用的 BIRD socket。

</details>

3. `calicoctl ipam show --show-blocks` 会提供什么信息？
   - A) Calico IPAM block 的使用情况；节点归属关系需另行检查
   - B) 自动安全释放空 block
   - C) 所有 VPC CNI ENI 的分配情况
   - D) 事务性 datastore 备份

<details>
<summary>显示答案</summary>

**答案：A) Calico IPAM block 的使用情况；节点归属关系需另行检查**

**说明：**
该命令会报告 IP block/pool 的使用情况。应通过 BlockAffinity 检查 block 与节点的对应关系。此命令适用于 Calico IPAM；若使用 VPC CNI 或 host-local，应检查相应的实际地址分配器。

</details>

4. 在所审查的版本中，`felix_int_dataplane_apply_time_seconds` 属于哪种指标类型？
   - A) 被拒绝数据包数量的 Counter
   - B) 必须包含 _bucket 系列的 Histogram
   - C) 包含分位数、_sum 和 _count 的 Summary
   - D) 已分配 IP block 数量的 Gauge

<details>
<summary>显示答案</summary>

**答案：C) 包含分位数、_sum 和 _count 的 Summary**

**说明：**
这是记录数据平面增量应用耗时的 Summary。单个实例的本地分位数不能代表整个集群的 p99。在存在观测值时，可用 sum/count 的速率计算平均值；不要臆造 Histogram bucket。

</details>

5. 关于 Typha 指标端口，哪项说法正确？
   - A) Typha 二进制程序默认使用 9091；指南明确将 Operator 管理的 Typha 指标端口配置为 9093
   - B) 每个 Typha 安装都会自动使用 9093
   - C) Typha 总是与 kube-controllers 共用 9094 端口
   - D) 只要创建 Service 就会启用指标

<details>
<summary>显示答案</summary>

**答案：A) Typha 二进制程序默认使用 9091；指南明确将 Operator 管理的 Typha 指标端口配置为 9093**

**说明：**
Typha 指标默认处于禁用状态。Operator 的 typhaMetricsPort 会启用/配置指标上报及其 Service。ServiceMonitor 必须选择匹配的 Service 端口，并且还必须被 Prometheus 选中。

</details>

6. Pod 没有 IP 地址时，应检查什么？
   - A) 立即释放一个地址并重启所有 Calico agent
   - B) 调度状态/事件、所选节点，以及实际使用的 CNI/IPAM 地址分配器
   - C) 只检查 DNS 记录
   - D) 检查所有 BGP 会话是否使用相同的 ASN

<details>
<summary>显示答案</summary>

**答案：B) 调度状态/事件、所选节点，以及实际使用的 CNI/IPAM 地址分配器**

**说明：**
处于 Pending 状态的 Pod 可能尚未完成调度。若确属地址分配失败，应检查 kubelet/CNI 和地址分配器的证据、符合条件的地址池，以及容量/归属约束。Felix 进程日志并不能解释所有 Pod 地址分配错误。

</details>

7. 排查 BGP 故障时应检查什么？
   - A) 只需确认 ping 成功
   - B) 受影响节点的会话状态、源地址、对端地址及各自的 ASN、TCP 179、身份验证/TTL 及过滤规则
   - C) 随机修改所有 ASN，直到会话建立
   - D) 不论节点位置如何，只查看集群中的第一个 Calico Pod

<details>
<summary>显示答案</summary>

**答案：B) 受影响节点的会话状态、源地址、对端地址及各自的 ASN、TCP 179、身份验证/TTL 及过滤规则**

**说明：**
TCP 连接成功并不能证明 BGP 已进入 Established 状态，也不能证明前缀已被接受。应检查预期路由以及正确的 IPv4/IPv6 BIRD socket。只有所选网络配置启用了 BGP 时，才需要执行这些检查。

</details>

8. 关于表面上的策略故障，哪项说法正确？
   - A) kube-proxy 和 Service 转换绝不会影响排查
   - B) Pod 注解会列出每项生效的策略决策
   - C) Felix Debug 日志会自动记录每个数据包的拒绝情况
   - D) 检查端点身份、选择器、方向、tier/order、既有流量，以及实际的 Service/数据平面路径

<details>
<summary>显示答案</summary>

**答案：D) 检查端点身份、选择器、方向、tier/order、既有流量，以及实际的 Service/数据平面路径**

**说明：**
Calico 负责执行策略，而 Service 转换、端点选择和源地址变更都可能影响实际评估的流量。应检查完整路径，并分别测试允许和拒绝的情况；不要先入为主地认为某个组件无关。

</details>

9. Calico 升级需要遵循什么流程？
   - A) 修改受管理的 DaemonSet，以移除所有 canary agent
   - B) 遵循与安装方式和版本相匹配的 CRD、Operator 及已存储数据迁移流程
   - C) 开始升级前总是设置 Installation.spec.version
   - D) 假定 Helm rollback 会撤销所有 CRD 和数据变更

<details>
<summary>显示答案</summary>

**答案：B) 遵循与安装方式和版本相匹配的 CRD、Operator 及已存储数据迁移流程**

**说明：**
应使用兼容的源版本和目标版本，更新现有安装管理者，并在需要新字段前管理好 CRD。还应测试升级过程和恢复方案。旧版 Operator 或原始 YAML 导出都不能保证可降级。

</details>

10. 应如何引入默认拒绝策略？
   - A) 先在选定的命名空间中验证，并明确放行其必需的依赖流量，再扩大范围
   - B) 立即对所有端点应用一个空的 GlobalNetworkPolicy
   - C) 根据臆造的 Pod 标签推断 API server 端点
   - D) 将端点数量为零视为拒绝策略有效的证据

<details>
<summary>显示答案</summary>

**答案：A) 先在选定的命名空间中验证，并明确放行其必需的依赖流量，再扩大范围**

**说明：**
应明确审查 DNS、API、身份、监控和应用流量路径。要测试正向和负向场景，保留恢复路径，并考虑工作负载端点策略与主机端点策略。

</details>

11. 哪项描述符合当前 OSS 流量可观测性？
   - A) FlowLogsFileReporter 是 OSS 必需的 API 字段
   - B) 每条流日志都恰好对应一个数据包记录
   - C) Operator/Helm 可部署 Goldmane 和 Whisker；当前流日志指南将该功能标记为技术预览
   - D) 流日志与 Felix 进程日志完全相同

<details>
<summary>显示答案</summary>

**答案：C) Operator/Helm 可部署 Goldmane 和 Whisker；当前流日志指南将该功能标记为技术预览**

**说明：**
Goldmane 会向 Whisker 提供聚合后的流数据。OSS 版本在满足文档所列安装前提时即可使用；旧的文件/DNS logger 字段不能替代该功能。应保护敏感流量数据，并评估该功能仍处于预览阶段这一情况。

</details>

12. 如何配置 calicoctl，以便访问 Kubernetes datastore？
   - A) 只设置 CNI_PATH
   - B) 使用 DATASTORE_TYPE=kubernetes 和适当的 kubeconfig 访问权限，或指定受支持的配置文件
   - C) 任意 ~/.config 路径都会被自动发现
   - D) Calico kubeconfig 可访问 EKS 托管的 etcd

<details>
<summary>显示答案</summary>

**答案：B) 使用 DATASTORE_TYPE=kubernetes 和适当的 kubeconfig 访问权限，或指定受支持的配置文件**

**说明：**
指南展示了常见的环境变量配置。显式指定 --config 文件也是受支持的方式。应选择预期的集群并配置相应的 RBAC；直接访问 etcdv3 属于单独的部署配置。

</details>

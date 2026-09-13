# vCluster 测验

[vCluster](../../platform-engineering/08-vcluster.md)

原有八个主题已对照 vCluster 0.37.0 审查。

## 1. 共享节点 vCluster 分离和共享什么？

<details>
<summary>显示答案</summary>

可分离虚拟 API、RBAC、控制器和存储，同时共享工作负载节点、内核、CNI 和 CSI。不保证完整硬件、网络或性能隔离。

</details>

## 2. Syncer 做什么？

<details>
<summary>显示答案</summary>

将配置的虚拟资源/引用转换为宿主资源，并将观测状态传播回来。默认值和命名因模式/版本而异；并非每个资源总是双向同步。

</details>

## 3. PR 预览需要什么？

<details>
<summary>显示答案</summary>

已验证配置、宿主容量、可信 CI 身份/事件、显式命名空间/上下文和清理。不保证 30 秒内创建或测试更快；不要把宿主凭证交给不可信 fork 代码。

</details>

## 4. 如何理解暂停和自动休眠？

<details>
<summary>显示答案</summary>

当前 pause 移除工作负载，resume 时重建，PVC/Service 独立保留。不是保留内存的挂起或备份。单独验证自动唤醒行为、许可和实际节省。

</details>

## 5. 共享节点中 StorageClass 和 PVC 如何工作？

<details>
<summary>显示答案</summary>

使用受支持 fromHost StorageClass 配置和宿主 CSI，将 PVC 同步到宿主。检查绑定模式、拓扑和回收/保留。0.37 支持快照同步，与已移除 deploy.volumeSnapshotController 不同。

</details>

## 6. 什么连接 Backstage 与 GitOps 预置？

<details>
<summary>显示答案</summary>

准备好的操作/骨架、已审核 PR、真实 ArgoCD 项目/目标/仓库权限和 values 来源。debug:log 不审批或等待部署。通过获准凭证渠道交付 kubeconfig。

</details>

## 7. 添加 NetworkPolicy 会阻止所有宿主访问吗？

<details>
<summary>显示答案</summary>

不会。允许规则可叠加，不能由另一拒绝策略削减。Syncer 需要宿主 API 访问。配置禁用工作负载公共出站，但保留控制平面端口允许，需要实际 CNI/路径验证。

</details>

## 8. 如何选择部署模式？

<details>
<summary>显示答案</summary>

评估 API 自主性、节点/内核/CNI/CSI、账户/管理员边界、性能及生命周期需求。比较共享节点、专用/私有节点、Standalone 和独立集群，不承诺未经测量的速度、成本或监管适用性。

</details>

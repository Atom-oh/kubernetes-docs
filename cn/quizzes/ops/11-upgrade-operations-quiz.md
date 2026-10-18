# EKS 升级运维测验

> **相关文档**：[EKS 升级](../../ops/11-upgrade-operations.md)

## 1. EKS 控制平面升级最多可以跳过多少个中间次要版本？

- A) 零个：每次都升级到下一个次要版本
- B) 一个
- C) 两个
- D) 不限

<details>
<summary>显示答案</summary>

**答案：A**

例如，1.34→1.36 必须经过 1.35。Kubelet 版本偏差允许范围与控制平面升级步骤是不同的概念。

</details>

## 2. 在纯 Auto Mode 中，如何理解 CoreDNS Deployment 缺失的情况？

- A) 这始终意味着 DNS 已损坏
- B) 检查节点系统服务 DNS 和实际行为
- C) 始终安装自管理的 Karpenter
- D) 从每个集群中删除 CoreDNS Deployment

<details>
<summary>显示答案</summary>

**答案：B**

混合集群必须保留非 Auto 节点所需的 DNS Deployment 和附加组件。

</details>

## 3. 关于 Velero 1.18.4 的 restore create -o json，哪项说法正确？

- A) 它会完成实际还原
- B) 它完全离线运行
- C) 它不会创建对象，但可能会执行发现操作/读取 Backup
- D) 只有与 --dry-run 一起使用才有效

<details>
<summary>显示答案</summary>

**答案：C**

restore create 没有这样的 --dry-run 标志。仅输出以供审查，与实际执行隔离还原测试是两回事。

</details>

## 4. 遇到 API 错误或 kubecontext 错误时，预检工具应该怎么做？

- A) 将空结果视为健康
- B) 将其判定为未知/上下文不匹配并进行调查
- C) 自动切换上下文并升级
- D) 删除 PDB

<details>
<summary>显示答案</summary>

**答案：B**

单独检查 Pod 是否运行，并不能确认其已就绪；Deployment 的 generation 和 rollout 状态也很重要。

</details>

## 5. EKS 原生回滚的基本资格条件是什么？

- A) 任何刚创建且版本为当前版本的集群
- B) 满足资格条件，包括在升级到上一个次要版本完成后的七天内启动回滚
- C) 随时回滚到任何先前版本
- D) etcd 备份可以绕过所有限制

<details>
<summary>显示答案</summary>

**答案：B**

还要检查目标版本是否受支持、EXTENDED 策略、ACTIVE 状态以及不兼容的 EKS 功能。

</details>

## 6. Auto Mode 节点回滚期间，如果集群状态为 ACTIVE，这意味着什么？

- A) 回滚已全部完成
- B) CP 仍可能提供当前版本的服务；请检查 update ID
- C) 无法回滚节点
- D) 立即删除之前的集群

<details>
<summary>显示答案</summary>

**答案：B**

Auto Mode 会先调整节点。节点超时默认为 720 分钟；客户端等待超时不会取消 AWS 端的操作。

</details>

## 7. rollback --force 会绕过什么？

- A) 七天期限和所有 PDB
- B) 所有中断风险和数据兼容性检查
- C) Insight 检查，但不会绕过资格条件或 Auto Mode 中断控制
- D) etcd 数据保留

<details>
<summary>显示答案</summary>

**答案：C**

ERROR/UNKNOWN 会阻止回滚，而 WARNING 仅作提示。Force 并非标准恢复路径。

</details>

## 8. 通过原生版本回滚不会自动还原到历史状态的是什么？

- A) API Server 次要版本
- B) Auto Mode 节点版本调整
- C) 附加组件、应用、etcd 对象和 PV 数据
- D) 控制平面组件版本

<details>
<summary>显示答案</summary>

**答案：C**

普通托管节点组需要单独处理 UpdateNodegroupVersion。版本回滚不同于快照还原。

</details>

## 9. 关于将 NLB 目标组权重设为零，哪项说法正确？

- A) 现有连接始终会保持到完成
- B) 现有连接可能会在短时间后关闭；请测试重试/会话行为
- C) 权重总和必须为 100
- D) NLB 不支持加权 TG

<details>
<summary>显示答案</summary>

**答案：B**

权重是 0–999 之间的相对值。要区分普通变更与切换到零权重的情形；TLS 侦听器不支持 TG 粘性会话。

</details>

## 10. 停用 Blue 前应该验证什么？

- A) 权重为零时立即销毁
- B) 检查共享资源/TG 引用、数据兼容性、恢复期和所有权
- C) 一个 HTTP 200 就能证明所有数据一致
- D) 共享 EFS 意味着无需检查并发写入者

<details>
<summary>显示答案</summary>

**答案：B**

请考虑删除 Auto Mode TGB/集群时的 TG 生命周期以及共享侦听器。更改 Namespace 并不能保证消费者/数据库/DNS 隔离。

</details>

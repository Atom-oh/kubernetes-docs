# 基础设施高级测验

> **相关文档**：[基础设施高级](../../ops/02-infrastructure-advanced.md)

## 选择题

### 1. NLB 权重比 5:5 表示什么？

- A) 在每个集群中创建五个节点
- B) 对新流量设置相同的相对分配比例
- C) 在五秒内迁移所有现有连接
- D) 总和不是 100，因此无效

<details>
<summary>显示答案</summary>

**答案：B) 对新流量设置相同的相对分配比例**

NLB 权重是 0–999 的相对整数。实际观测到的字节数或请求数可能因流大小、粘性以及观测时间窗口而不同。

</details>

### 2. 将 NLB 组权重降为零时，需要注意什么？

- A) 现有连接必须一直保留到自然关闭
- B) 当前指南说明现有连接也会在短时间后关闭，因此要测试重新连接
- C) 注销延迟可以保证所有切换时间
- D) API 返回成功就表示所有流量已经迁移

<details>
<summary>显示答案</summary>

**答案：B) 当前指南说明现有连接也会在短时间后关闭，因此要测试重新连接**

应区分普通权重调整和权重降为零时的转换。配置请求被接受与数据面完成收敛是两回事；请检查新建和活动流量、错误率及延迟。

</details>

### 3. 如果 blue 和 green 两个 DNS 名称指向同一个共享 NLB，DNS 权重能做什么？

- A) 独立选择各自的目标组
- B) 仅凭主机名就将请求固定到某个 AZ
- C) 选择的仍是同一个负载均衡器，不能选择特定集群的目标组
- D) 自动选择相同的数据库副本

<details>
<summary>显示答案</summary>

**答案：C) 选择的仍是同一个负载均衡器，不能选择特定集群的目标组**

基于 DNS 的选择需要使用不同的真实负载均衡器端点，并分别指向预期集群。监听器权重和 DNS 记录权重作用于不同层级。

</details>

### 4. 如何将工作负载调度到指定 AZ 中的 Auto Mode 节点？

- A) Pod 的 nodeSelector 会自行创建节点
- B) 将 subnet_ids 放入 NodePool
- C) 使 Pod 选择条件、NodePool requirements、NodeClass 子网选择和 tolerations 相互匹配
- D) 将集群命名为 blue

<details>
<summary>显示答案</summary>

**答案：C) 使 Pod 选择条件、NodePool requirements、NodeClass 子网选择和 tolerations 相互匹配**

NodeSelector/affinity 用于选择符合条件的节点；节点供给约束以及 taint/toleration 也必须匹配。还要区分工作节点的放置位置与区域级托管控制面。

</details>

### 5. 此外部管理目标组示例使用哪种 TGB 所有权模式？

- A) 内置 Auto Mode 的删除行为总是相同
- B) 单独安装的 LBC，使用 elbv2.k8s.aws/v1beta1，与内置 Auto Mode 不同
- C) 只需要 ARN，不需要 Service 或 targetPort 前提条件
- D) 通过 Terraform 注册永久不变的 Pod IP

<details>
<summary>显示答案</summary>

**答案：B) 单独安装的 LBC，使用 elbv2.k8s.aws/v1beta1，与内置 Auto Mode 不同**

内置 Auto Mode 使用 eks.amazonaws.com/v1，并有文档说明目标组的删除行为。此操作方案使用单独的控制器进行动态注册和网络规则管理。

</details>

### 6. 单个 PostgreSQL StatefulSet 加上 Retain PVC 能保证什么？

- A) 跨集群复制
- B) 跨 AZ 的零停机数据库故障转移
- C) 每个连接都能保持打开
- D) 它本身不能保证高可用、备份或恢复

<details>
<summary>显示答案</summary>

**答案：D) 它本身不能保证高可用、备份或恢复**

Retain 是一种回收策略。复制、备份、写入者所有权和恢复流程都需要另行设计。NLB 权重不会将 EBS 卷迁移到其他 AZ。

</details>

### 7. 为什么要将告警输入 SNS Topic 与决策通知 SNS Topic 分开？

- A) 防止通知重新作为输入触发额外执行或错误
- B) 无需 IAM 权限即可发布消息
- C) 使 Lambda 永远重试
- D) 消除 DNS TTL

<details>
<summary>显示答案</summary>

**答案：A) 防止通知重新作为输入触发额外执行或错误**

此处理程序接收 SNS 信封格式。直接传入 CloudWatch Lambda 事件的格式不同，因此不要同时连接这两种调用路径。即使通知失败，也不能因此重放已经成功完成的监听器修改。

</details>

### 8. 默认设置 automatic_failover=false 有什么作用？

- A) 立即将所有流量切换到 Green
- B) 提出变更方案，但不授予 ModifyListener 权限
- C) 跳过健康检查
- D) 修改所有可用监听器

<details>
<summary>显示答案</summary>

**答案：B) 提出变更方案，但不授予 ModifyListener 权限**

只有在验证容量、SLO、重新连接行为和写入者协调后，才启用自动模式。reserved concurrency=1 并不能串行化外部 Terraform 或人工写入操作。

</details>

### 9. 手动切换脚本应执行什么操作？

- A) 将原始用户字符串作为 Bash 算术表达式执行
- B) 始终假定初始状态为 100/0
- C) 验证权重和目标健康状况，然后展示完整计划并要求审批
- D) 使用 STEP=0 不断重复定时循环

<details>
<summary>显示答案</summary>

**答案：C) 验证权重和目标健康状况，然后展示完整计划并要求审批**

先验证数值范围，再使用预期的变量和后端。在每个阶段检查实际 SLO 和数据兼容性。API/apply 成功本身不能证明流量切换已经完成。

</details>

### 10. 关于 Route 53 权重和 TTL，哪项说法正确？

- A) 权重是 0–255 的整数；TTL 本身不能保证恢复时间
- B) 权重始终为 0–999
- C) 60 秒 TTL 就是 60 秒恢复 SLA
- D) 如果所有选项都不健康，DNS 必须不返回任何答案

<details>
<summary>显示答案</summary>

**答案：A) 权重是 0–255 的整数；TTL 本身不能保证恢复时间**

Alias 记录继承目标 TTL。还要考虑健康状况、解析器缓存、连接生命周期和回退行为。所有权重都设为零并不是可靠的停止流量机制。

</details>

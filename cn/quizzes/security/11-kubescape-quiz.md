# Kubescape 测验

> **最后更新**：October 16, 2026

## 问题

<span id="_1-what-is-kubescape-s-project-status-in-the-cncf"></span>

### 1. Kubescape 当前在 CNCF 中的成熟度级别是什么？

- A) 已毕业
- B) 孵化中
- C) 沙盒
- D) 已归档

<details>
<summary>显示答案</summary>

**答案：B) 孵化中**

Kubescape 于 2022 年 12 月 13 日加入 CNCF，并于 2025 年 1 月 13 日进入孵化阶段。这并不保证单个安装的安全性或可用性。

</details>

<span id="_2-which-security-frameworks-does-kubescape-support-for-compliance-scanning"></span>

### 2. 应如何核实框架名称和控制项数量？

- A) 始终使用旧的 CIS 别名
- B) 记录二进制文件/策略版本并检查实际列表
- C) NSA 控制项数量永远不会改变
- D) SOC2 扫描通过即完成认证

<details>
<summary>显示答案</summary>

**答案：B) 记录二进制文件/策略版本并检查实际列表**

使用 kubescape list frameworks 和 list controls --framework NSA。经审查的 NSA 快照包含 26 个控制项，具体适用性由输入内容决定。比较评分时应保留策略哈希值。

</details>

<span id="_3-what-is-the-correct-cli-syntax-to-scan-a-kubernetes-cluster-with-kubescape"></span>

### 3. 从 kubescape scan 中省略本地文件目标时会发生什么？

- A) 总是失败
- B) 可以扫描当前 kubeconfig 对应的集群
- C) 总是只扫描本地文件
- D) 总是执行试运行

<details>
<summary>显示答案</summary>

**答案：B) 可以扫描当前 kubeconfig 对应的集群**

CI 应传入一个已存在的显式本地文件，并拒绝空目标或缺失目标。--keep-local、隔离缓存和固定版本的策略都不能代替对输入范围的检查。

</details>

<span id="_4-what-is-the-key-difference-between-kubescape-operator-and-cli-modes"></span>

### 4. 哪项说法正确地区分了 Operator 和 CLI 的运行方式？

- A) Operator 只提供 GUI
- B) CLI 处理显式/临时扫描；Operator 运行已启用的持续/定期功能
- C) 安装 Operator 即可证明所有运行时功能都能正常工作
- D) CLI 和 Operator 镜像始终使用相同版本

<details>
<summary>显示答案</summary>

**答案：B) CLI 处理显式/临时扫描；Operator 运行已启用的持续/定期功能**

Chart 1.40.4 会渲染出扫描器镜像 4.0.13，而经过测试的本地 CLI 为 4.0.16。节点/镜像/运行时/修复的范围以及权限都需要分别选择和验证。

</details>

<span id="_5-how-does-kubescape-calculate-risk-scores-for-controls"></span>

### 5. score 和 complianceScore 有何关系？

- A) 它们始终相等
- B) 它们的总和始终为 100
- C) 它们是结果架构中的独立汇总值
- D) 两者都是 CVSS 平均值

<details>
<summary>显示答案</summary>

**答案：C) 它们是结果架构中的独立汇总值**

这个合成的不安全 Pod 得出的合规性为 55，score 为 62.5。读取 summaryDetails.complianceScore 和 summaryDetails.score。这些本地值并不能衡量真实集群的安全性。

</details>

<span id="_6-which-flag-enforces-a-compliance-threshold-in-ci-cd-pipelines"></span>

### 6. compliance 为 55 且使用 --compliance-threshold 56 时会发生什么？

- A) 通过，因为这是最高风险限制
- B) 退出码为 1，因为未达到最低合规性要求
- C) 始终以退出码 2 退出
- D) 等同于当前的 --fail-threshold 0 门禁

<details>
<summary>显示答案</summary>

**答案：B) 退出码为 1，因为未达到最低合规性要求**

在同一测试样例中，阈值为 55 时返回退出码 0，阈值为 56 时返回退出码 1。4.0.16 版本接受已弃用的 --fail-threshold，但会忽略其值；不要将其用作门禁。

</details>

<span id="_7-how-does-kubescape-differ-from-kube-bench"></span>

### 7. 比较 kube-bench 和 Kubescape 的可靠依据是什么？

- A) 仅凭名称就假定其中一个能替代所有检查
- B) 比较实际的节点/CIS 与工作负载/配置范围及访问权限
- C) 两者都能在没有访问权限的情况下检查每项控制平面设置
- D) Kubescape 扫描通过即是 CIS 认证

<details>
<summary>显示答案</summary>

**答案：B) 比较实际的节点/CIS 与工作负载/配置范围及访问权限**

托管 EKS 控制平面、本地清单和节点文件访问所能提供的可见性各不相同。应区分不可用/未评估的检查和通过的检查，并据此选择工具。

</details>

<span id="_8-what-feature-does-kubescape-provide-for-rbac-security-analysis"></span>

### 8. 关于 RBAC 控制项，哪项说法正确？

- A) C-0036 始终检查通配符 RBAC
- B) RoleBinding 会在所有命名空间中授予访问权限
- C) 核实当前控制项 ID/名称和采集范围
- D) scan rbac 是经审查的 CLI 中一个独立的子命令

<details>
<summary>显示答案</summary>

**答案：C) 核实当前控制项 ID/名称和采集范围**

经审查的软件包将 C-0035 对应到 Administrative Roles，将 C-0036/0039 对应到验证/变更型准入检查。RoleBinding 的作用范围是命名空间；静态分析不会自动验证外部 IAM。

</details>

<span id="_9-which-vulnerability-scanner-does-kubescape-integrate-with-for-image-scanning"></span>

### 9. 哪项说法正确地区分了镜像扫描和主机扫描？

- A) 主机扫描只检查镜像 CVE
- B) 显式镜像扫描需要注册表/数据库访问；主机扫描有独立的范围
- C) Grype 只生成 SBOM
- D) 镜像/平台/数据库版本无关紧要

<details>
<summary>显示答案</summary>

**答案：B) 显式镜像扫描需要注册表/数据库访问；主机扫描有独立的范围**

CLI 使用 Grype 和 Syft；Operator kubevuln 的版本则单独管理。主机扫描可能需要额外的资源/权限。本次审计未执行镜像拉取或主机扫描。

</details>

<span id="_10-how-does-kubescape-handle-control-exceptions"></span>

### 10. CLI 和集群内例外的正确格式是什么？

- A) CLI 可直接使用任意 ConfigMap
- B) 区分 CLI JSON 数组中的 alertOnly 和 v1beta1 SecurityException 中的 alert_only
- C) 每个 ignore 注解都会自动成为例外
- D) 记录例外即可修复问题

<details>
<summary>显示答案</summary>

**答案：B) 区分 CLI JSON 数组中的 alertOnly 和 v1beta1 SecurityException 中的 alert_only**

在测试中，alertOnly 会确认一项失败，但不会改变合规性。exclude-controls 会改变评估的分母。应将所有者、范围、到期时间和重新审查与问题修复分别跟踪。

</details>

## 评分计算

- 9–10：理解扎实
- 7–8：重新查看遗漏的范围/门禁概念
- 6 分或更低：复习指南和经过测试的示例

## 相关文档

- [Kubescape](../../security/11-kubescape.md)

# Kubescape 测验

> **最后更新**: September 13, 2026

## 问题

<span id="_1-what-is-kubescape-s-project-status-in-the-cncf"></span>

### 1. Kubescape 当前在 CNCF 中的成熟度级别是什么？

- A) 毕业项目
- B) 孵化项目
- C) Sandbox
- D) 已归档

<details>
<summary>显示答案</summary>

**答案：B) 孵化项目**

Kubescape 于 2022 年 12 月 13 日加入 CNCF，并于 2025 年 1 月 13 日成为孵化项目。这并不保证某个单独安装实例的安全性或可用性。

</details>

<span id="_2-which-security-frameworks-does-kubescape-support-for-compliance-scanning"></span>

### 2. 应如何验证框架名称和控制项数量？

- A) 始终使用旧版 CIS 别名
- B) 记录二进制文件/策略版本并检查实际列表
- C) NSA 控制项数量永远不会改变
- D) 通过 SOC2 扫描即可完成认证

<details>
<summary>显示答案</summary>

**答案：B) 记录二进制文件/策略版本并检查实际列表**

使用 kubescape list frameworks 和 list controls --framework NSA。经审查的 NSA 快照包含 26 个控制项，适用性由输入决定。比较评分时请保留策略哈希值。

</details>

<span id="_3-what-is-the-correct-cli-syntax-to-scan-a-kubernetes-cluster-with-kubescape"></span>

### 3. 在 kubescape scan 中省略本地文件目标时会发生什么？

- A) 它总是失败
- B) 它可以扫描当前 kubeconfig 集群
- C) 它总是只扫描本地文件
- D) 它总是执行 dry run

<details>
<summary>显示答案</summary>

**答案：B) 它可以扫描当前 kubeconfig 集群**

CI 应传入一个存在的明确本地文件，并拒绝空缺或缺失的目标。--keep-local、隔离的缓存和固定的策略不能替代对输入范围的检查。

</details>

<span id="_4-what-is-the-key-difference-between-kubescape-operator-and-cli-modes"></span>

### 4. 哪项陈述正确区分了 Operator 和 CLI 操作？

- A) Operator 只提供 GUI
- B) CLI 处理明确的/临时的扫描；Operator 运行已启用的持续/计划功能
- C) 安装 Operator 可证明所有运行时功能均可工作
- D) CLI 和 Operator 镜像始终使用相同版本

<details>
<summary>显示答案</summary>

**答案：B) CLI 处理明确的/临时的扫描；Operator 运行已启用的持续/计划功能**

Chart 1.40.4 渲染 scanner 镜像 4.0.13，而经过测试的本地 CLI 是 4.0.14。Node/镜像/运行时/修复的范围和权限需要分别选择并验证。

</details>

<span id="_5-how-does-kubescape-calculate-risk-scores-for-controls"></span>

### 5. score 和 complianceScore 有何关联？

- A) 它们始终相等
- B) 它们的总和始终为 100
- C) 它们是结果 schema 中独立的聚合值
- D) 它们都是平均 CVSS 值

<details>
<summary>显示答案</summary>

**答案：C) 它们是结果 schema 中独立的聚合值**

该合成的不安全 Pod 产生了 55 的 compliance 和 62.5 的 score。读取 summaryDetails.complianceScore 和 summaryDetails.score。这些本地值无法衡量真实集群的安全性。

</details>

<span id="_6-which-flag-enforces-a-compliance-threshold-in-ci-cd-pipelines"></span>

### 6. 当 compliance 为 55 且 --compliance-threshold 为 56 时会发生什么？

- A) 它会通过，因为这是最大风险限制
- B) 它以退出代码 1 退出，因为未达到最低 compliance
- C) 它始终以退出代码 2 退出
- D) 它等同于当前的 --fail-threshold 0 gate

<details>
<summary>显示答案</summary>

**答案：B) 它以退出代码 1 退出，因为未达到最低 compliance**

同一 fixture 在阈值为 55 时返回退出代码 0，在 56 时返回退出代码 1。版本 4.0.14 接受已弃用的 --fail-threshold，但会忽略其值；请勿将其用作 gate。

</details>

<span id="_7-how-does-kubescape-differ-from-kube-bench"></span>

### 7. 比较 kube-bench 和 Kubescape 的合理依据是什么？

- A) 根据名称假定其中一个可替代所有检查
- B) 比较实际的 Node/CIS 与 workload/config 范围和访问权限
- C) 两者无需访问权限即可检查每项 control-plane 设置
- D) Kubescape 通过即表示获得 CIS 证书

<details>
<summary>显示答案</summary>

**答案：B) 比较实际的 Node/CIS 与 workload/config 范围和访问权限**

托管 EKS control plane、本地 manifest 和 Node 文件访问提供不同的可见性。请区分不可用/未评估的检查与通过的检查，并据此选择工具。

</details>

<span id="_8-what-feature-does-kubescape-provide-for-rbac-security-analysis"></span>

### 8. 关于 RBAC 控制项，哪项陈述正确？

- A) C-0036 始终检查 wildcard RBAC
- B) RoleBinding 会授予所有 namespace 中的访问权限
- C) 验证当前 control ID/名称和收集范围
- D) 在经审查的 CLI 中，scan rbac 是一个独立子命令

<details>
<summary>显示答案</summary>

**答案：C) 验证当前 control ID/名称和收集范围**

经审查的 bundle 将 C-0035 映射到 Administrative Roles，并将 C-0036/0039 映射到 validating/mutating admission 检查。RoleBinding 具有 namespace 范围；静态分析不会自动验证外部 IAM。

</details>

<span id="_9-which-vulnerability-scanner-does-kubescape-integrate-with-for-image-scanning"></span>

### 9. 哪项陈述正确区分了镜像扫描和主机扫描？

- A) 主机扫描只检查镜像 CVE
- B) 明确的镜像扫描需要 registry/DB 访问权限；主机扫描具有独立范围
- C) Grype 只生成 SBOM
- D) 镜像/platform/database 版本无关紧要

<details>
<summary>显示答案</summary>

**答案：B) 明确的镜像扫描需要 registry/DB 访问权限；主机扫描具有独立范围**

CLI 使用 Grype 和 Syft；Operator kubevuln 具有独立版本。主机扫描可能需要额外资源/权限。本次审计未运行镜像拉取或主机扫描。

</details>

<span id="_10-how-does-kubescape-handle-control-exceptions"></span>

### 10. 正确的 CLI 和集群内例外格式是什么？

- A) CLI 直接使用任意 ConfigMap
- B) 区分 CLI JSON 数组中的 alertOnly 与 v1beta1 SecurityException 中的 alert_only
- C) 每个 ignore annotation 都会自动成为例外
- D) 记录例外即可修复问题

<details>
<summary>显示答案</summary>

**答案：B) 区分 CLI JSON 数组中的 alertOnly 与 v1beta1 SecurityException 中的 alert_only**

在测试中，alertOnly 确认了失败，但没有改变 compliance。exclude-controls 会改变评估分母。应将所有权、范围、到期时间和重新审查与修复分开跟踪。

</details>

## 评分计算

- 9–10：理解扎实
- 7–8：重新学习遗漏的范围/gate 概念
- 6 或以下：复习指南和经过测试的示例

## 相关文档

- [Kubescape](../../security/11-kubescape.md)

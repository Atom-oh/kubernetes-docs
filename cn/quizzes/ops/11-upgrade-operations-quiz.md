# 升级操作测验

> **相关文档**: [升级操作](../../ops/11-upgrade-operations.md)

## 选择题

### 1. AWS 在标准支持下为每个 EKS Kubernetes 版本提供多长时间的支持？

- A) 6 个月
- B) 12 个月
- C) 14 个月
- D) 24 个月

<details>
<summary>显示答案</summary>

**答案: C) 14 个月**

**解释:**
AWS 为 EKS 上的每个 Kubernetes 版本提供 14 个月的标准支持。之后，cluster 可以迁移到扩展支持（需要额外费用），或者必须升级。建议在标准支持窗口内规划升级。

</details>

### 2. 哪个工具可以检测 cluster 中已弃用的 Kubernetes API？

- A) kubectl
- B) Pluto
- C) Helm
- D) Terraform

<details>
<summary>显示答案</summary>

**答案: B) Pluto**

**解释:**
Pluto 会扫描 Kubernetes manifests、Helm releases 和实时 cluster，以查找已弃用或已移除的 API 版本。它有助于识别在升级到这些 API 不再存在的版本之前需要更新的资源。

</details>

### 3. 在 EKS 升级操作中，Velero 的用途是什么？

- A) 升级 Kubernetes 版本
- B) 在升级前备份和恢复 cluster 资源
- C) 监控 cluster 性能
- D) 管理 node groups

<details>
<summary>显示答案</summary>

**答案: B) 在升级前备份和恢复 cluster 资源**

**解释:**
Velero 为 Kubernetes 资源和 persistent volumes 提供备份与恢复能力。在升级前进行 Velero 备份，可以在升级导致问题时进行恢复，为操作提供安全保障。

</details>

### 4. 在 Terraform 3-Layer 架构中，正确的升级顺序是什么？

- A) Workload -> Platform -> Foundation
- B) Platform -> Foundation -> Workload
- C) Foundation -> Platform -> Workload
- D) 所有层同时进行

<details>
<summary>显示答案</summary>

**答案: C) Foundation -> Platform -> Workload**

**解释:**
升级顺序遵循依赖关系：首先是 Foundation（VPC、IAM），因为 Platform 依赖它；然后是 Platform（EKS cluster），因为 Workload 依赖它；最后是 Workload（应用程序）。这样可以确保每一层的依赖项都已完成升级。

</details>

### 5. 在 EKS Auto Mode 中，Kubernetes 版本升级期间 node 会发生什么？

- A) Node 原地升级且无需重启
- B) Node 会自动替换为新版本 node
- C) 必须手动删除 node
- D) Node 不受版本升级影响

<details>
<summary>显示答案</summary>

**答案: B) Node 会自动替换为新版本 node**

**解释:**
升级 EKS control plane 后，Auto Mode 会自动轮换 node 以匹配新版本。此过程会 cordon 旧 node、drain workloads，并使用更新后的 kubelet 版本预置新 node。

</details>

### 6. 升级前应验证 Pod Disruption Budgets (PDBs) 的什么内容？

- A) 确认不存在 PDBs
- B) 确认 PDBs 允许足够的 disruption，以进行滚动 node 替换
- C) 确认 PDBs 设置为零
- D) 确认 PDBs 引用了正确的 API 版本

<details>
<summary>显示答案</summary>

**答案: B) 确认 PDBs 允许足够的 disruption，以进行滚动 node 替换**

**解释:**
过于严格的 PDBs（例如 maxUnavailable: 0 且 minAvailable: 100%）可能会在升级期间阻止 node draining。升级前，确保 PDBs 允许足够的 disruption，使滚动替换过程能够继续进行。

</details>

### 7. EKS cluster 的 blue/green 升级策略是什么？

- A) 同时升级两个 cluster
- B) 使用新版本创建一个新 cluster，并逐步转移流量
- C) 原地升级并具备回滚能力
- D) 在相同 node 上运行两个版本

<details>
<summary>显示答案</summary>

**答案: B) 使用新版本创建一个新 cluster，并逐步转移流量**

**解释:**
Blue/green 升级会在现有的 “blue” cluster 旁边创建一个运行目标 Kubernetes 版本的新 “green” cluster。流量通过加权路由逐步转移；如果出现问题，可以通过将流量切回 blue 来轻松回滚。

</details>

### 8. 升级后应执行哪些验证？

- A) 仅检查 pods 是否正在运行
- B) 验证 node 状态、pod 健康状况、addon 功能和应用程序行为
- C) 不需要验证
- D) 只需再次运行 Pluto

<details>
<summary>显示答案</summary>

**答案: B) 验证 node 状态、pod 健康状况、addon 功能和应用程序行为**

**解释:**
升级后验证应包括：所有 node 均为 Ready、pods 处于 Running 状态、cluster addons（CoreDNS、kube-proxy、CNI）功能正常、ingress/egress 工作正常、storage 操作成功，以及应用程序特定的健康检查通过。

</details>

### 9. EKS 扩展支持与标准支持有何不同？

- A) 扩展支持是免费的
- B) 扩展支持以额外费用提供超出标准支持的更多月份
- C) 扩展支持仅涵盖安全补丁
- D) 扩展支持仅适用于 Fargate

<details>
<summary>显示答案</summary>

**答案: B) 扩展支持以额外费用提供超出标准支持的更多月份**

**解释:**
EKS 扩展支持允许 cluster 在 14 个月标准窗口之后继续运行较旧的 Kubernetes 版本，但会产生额外的每 cluster 小时费用。这为需要更多时间进行升级的组织提供了灵活性。

</details>

### 10. 升级时，为什么检查 addon 兼容性很重要？

- A) Addons 会自动升级
- B) 某些 addon 版本仅与特定 Kubernetes 版本兼容
- C) Addons 不影响升级
- D) 升级前必须移除 addons

<details>
<summary>显示答案</summary>

**答案: B) 某些 addon 版本仅与特定 Kubernetes 版本兼容**

**解释:**
EKS managed addons（VPC CNI、CoreDNS、kube-proxy）和 third-party addons 都有与 Kubernetes 版本对应的版本兼容性矩阵。升级到不兼容的 addon 版本可能会破坏 cluster 功能。请在 cluster 升级的同时检查并规划 addon 升级。

</details>

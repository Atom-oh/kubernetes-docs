# EKS Auto Mode 迁移指南测验

> **相关文档**: [迁移指南](../../eks-auto-mode/09-migration-guide.md)
> **最后更新**: 2026 年 9 月 12 日

## 选择题

### 1. 在启用或移除迁移容量之前，应先做什么？

- A) 删除旧节点组
- B) 清点工作负载、依赖项、所有权和恢复要求
- C) 驱逐所有 Pod
- D) 假设实例名称相同就代表兼容

<details>
<summary>显示答案</summary>

**答案：B) 清点工作负载、依赖项、所有权和恢复要求**

**说明：**
先确认账户、集群和旧节点组的身份，再检查放置、数据、IAM、网络、控制器、成本和应用健康状况。在缩容或删除之前逐批验证；最后的验证阶段不能代替前期健康检查。源文档会设置下方命令使用的私有 WORK_DIR 和 KUBE_CONTEXT。

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s \
  get deployments,statefulsets,daemonsets,jobs,cronjobs -A -o json |
jq '[.items[] | (.spec.template // .spec.jobTemplate.spec.template) as $t |
 {kind,namespace:.metadata.namespace,name:.metadata.name,uid:.metadata.uid,
  nodeSelector:$t.spec.nodeSelector,affinity:$t.spec.affinity,tolerations:$t.spec.tolerations,
  serviceAccountName:$t.spec.serviceAccountName,hostNetwork:$t.spec.hostNetwork,
  pvcNames:[$t.spec.volumes[]?.persistentVolumeClaim.claimName // empty]}]' \
  > "$WORK_DIR/workload-placement.json"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pods -A -o json |
jq '[.items[] | {namespace:.metadata.namespace,name:.metadata.name,node:.spec.nodeName,
  phase:.status.phase,deletionTimestamp:.metadata.deletionTimestamp,
  ready:([.status.conditions[]?|select(.type=="Ready")|.status]|first // "NotReported"),
  owners:[.metadata.ownerReferences[]?|{kind,name,controller}]}]' \
  > "$WORK_DIR/pod-state.json"
```

</details>

### 2. 如何让旧托管节点与 Auto Mode 可预测地共存？

- A) 两者不能共存
- B) 为每个工作负载显式指定放置规则和控制器所有权
- C) 只能使用单独的集群
- D) 只需匹配 AWS 资源标签

<details>
<summary>显示答案</summary>

**答案：B) 为每个工作负载显式指定放置规则和控制器所有权**

**说明：**
用特定的旧节点组选择器，以及精确的 Auto 节点池/计算类型选择器区分两类节点。通用 Karpenter 标签也可能匹配自管理的 Karpenter。在依赖尚未迁移前，保留混合节点环境中的 DNS/代理，以及现有存储和负载均衡控制器。以下只是 Pod spec 片段；指南中包含完整的 canary Deployment。

旧托管节点组：
```yaml
# Pod template spec fragment
nodeSelector:
  eks.amazonaws.com/nodegroup: REPLACE_WITH_OLD_NODEGROUP
tolerations: []
```

Auto canary：
```yaml
# Pod template spec fragment
nodeSelector:
  karpenter.sh/nodepool: migration-pool
  eks.amazonaws.com/compute-type: auto
tolerations:
- key: migration
  operator: Equal
  value: auto-mode
  effect: NoSchedule
```

</details>

### 3. 哪种顺序有助于降低迁移风险？

- A) 先迁移关键生产工作负载
- B) 先迁移有代表性的低风险工作负载，再逐步迁移更关键的依赖项
- C) 一次性迁移所有内容
- D) 随机安排顺序

<details>
<summary>显示答案</summary>

**答案：B) 先迁移有代表性的低风险工作负载，再逐步迁移更关键的依赖项**

**说明：**
当阶段能反映实际依赖关系时，可依次处理开发/暂存环境、非关键生产工作负载和关键生产工作负载。更新实际拥有工作负载的控制器/GitOps 放置配置，然后验证应用行为、存储、IAM、DNS 和流量。软性偏好或臆造的 `node-type=auto-mode` 标签都不能证明迁移已完成。遇到健康状态失败或未知时应停止；固定等待一段时间不等于完成验证。

</details>

### 4. 哪种回滚顺序能保留恢复路径？

- A) 先删除并重建集群
- B) 恢复兼容的旧容量和放置规则，验证健康后再退役明确归属的 Auto 资源
- C) 先删除 Auto NodePool
- D) 只需禁用 Auto Mode

<details>
<summary>显示答案</summary>

**答案：B) 恢复兼容的旧容量和放置规则，验证健康后再退役明确归属的 Auto 资源**

**说明：**
保留 Auto 节点池，直到旧容量变为 Ready。审查并恢复预期的放置规则，避免遗留冲突的 Auto 选择器，也不要清除无关的 affinity。除 Pod 外，还要验证数据和流量。只有随后才退役本次迁移所拥有的容量。删除 NodePool 可能级联删除节点；缩放配置的 JSON 不能重建已删除的节点组。这是工作负载迁移回滚，不是 Kubernetes 版本回滚。

</details>

### 5. 缩减旧托管节点组的期望容量之前需要做什么？

- A) 立即将容量设为零
- B) 验证已迁移的工作负载、cordon 并清空旧应用节点容量，同时与其所有者协调
- C) 始终将容量减半
- D) 只需等待五分钟

<details>
<summary>显示答案</summary>

**答案：B) 验证已迁移的工作负载、cordon 并清空旧应用节点容量，同时与其所有者协调**

**说明：**
MNG 缩放配置变更通过 ASG 缩容，不遵守 PDB。源文档会检查旧节点的 cordon 状态和仍在运行的非 DaemonSet Pod，并在查询失败时停止。还要检查系统依赖和已导出的作业结果，并防止控制器重新向旧节点填充工作负载。将容量减半并等待一段时间不能证明操作安全。原有 IaC/缩放所有权仍然适用。

</details>

### 6. 迁移期间应如何监控成本？

- A) 等到删除所有旧资源后再考虑成本
- B) 将当前节点数量视为精确账单成本
- C) 同时跟踪重叠运行的节点组和负载均衡器，并监控可用性与性能
- D) 假设 Auto Mode 会自动移除所有旧费用

<details>
<summary>显示答案</summary>

**答案：C) 同时跟踪重叠运行的节点组和负载均衡器，并监控可用性与性能**

**说明：**
共存期间，两套节点组和流量路径都可能产生费用。应使用实际账单数据及已配置的运维指标发布器。下表中的旧阈值仍是未经验证的规划示例，不是 Auto Mode 的默认指标或正常范围。

| 信号 | 先前的基线示例 | 先前的告警示例 |
|--------|------------------------|---------------------|
| Pending Pod 数量 | 0–5 | >10 持续 5 分钟 |
| 节点预置时间 | <90 秒 | >120 秒 |
| 可用性 | >99.9% | <99.5% |
| API 延迟 | <200 毫秒 | >500 毫秒 |

Pending 不等同于不可调度，Running 不代表应用已就绪，采集器没有数据也不代表故障为零。

</details>

### 7. 工作负载验证后，为保留回滚选项，可以延后哪项操作？

- A) 检查应用行为
- B) 检查预期放置位置
- C) 删除旧节点组定义
- D) 检查数据和控制器健康状况

<details>
<summary>显示答案</summary>

**答案：C) 删除旧节点组定义**

**说明：**
在有意设定的稳定观察期内保留旧定义/配置，同时考虑保留资源和相应成本。先前提到的一到两周只是示例，并非普遍要求。检查实际就绪状态和成功的 Job，不要要求每个 Pod 都必须处于 Running。只有完成数据、流量和工作负载验证后，才由原 IaC 所有者删除旧定义。

</details>

### 8. 已有自管理 Karpenter 控制器时，正确的做法是什么？

- A) 启用 Auto Mode 前始终先将其移除
- B) 共存期间保留兼容的 Karpenter，完成旧资源的终结流程后再卸载
- C) 删除所有共享的 Karpenter CRD
- D) 删除所有带有 Karpenter 标签的节点

<details>
<summary>显示答案</summary>

**答案：B) 共存期间保留兼容的 Karpenter，完成旧资源的终结流程后再卸载**

**说明：**
AWS 记录了直接共存迁移方式。v1.1 迁移最低版本不取代当前 Kubernetes 兼容性要求。应使用不同的 NodeClass 引用和带污点的 Auto 节点池。不要修改或删除共享的 NodePool/NodeClaim CRD。在现有控制器仍能完成终结流程时，退役旧的自有 NodePool/NodeClaim；确认实例及依赖资源已清理后，再移除仅属于该控制器的发布、IAM 和队列资源。

</details>

## 参考资料

- [托管节点组缩放与 PDB](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html)
- [Auto Mode 迁移参考](https://docs.aws.amazon.com/eks/latest/userguide/migrate-auto.html)
- [Karpenter 共存迁移](https://docs.aws.amazon.com/eks/latest/userguide/auto-migrate-karpenter.html)

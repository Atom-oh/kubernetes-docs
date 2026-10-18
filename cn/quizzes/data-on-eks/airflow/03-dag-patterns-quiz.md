# DAG 模式与 KubernetesPodOperator 测验

基于 Airflow 3.3.1 和 Kubernetes provider 10.21.0。请检查执行结构、合并行为、权限、Bundle 版本控制和验证范围。

## 概念

1. 使用 CeleryExecutor 的同步 KPO 任务由谁创建新的工作负载 Pod？

<details>
<summary>显示答案</summary>

**答案**：KPO 从现有 Celery worker 调用 Kubernetes API。

**说明**：工作负载运行在单独的 Pod 中。多个任务可以共用 worker Pod，工作负载镜像也不一定需要安装 Airflow。

</details>

2. 从 CeleryExecutor 切换到 KubernetesExecutor，如何改变新一次 KPO 执行时 Pod 的实际创建方式？

<details>
<summary>显示答案</summary>

**答案**：可能会分别创建任务执行器 Pod 和工作负载 Pod，而不是使用现有的 Celery worker。

**说明**：两个逻辑执行角色并不总是意味着会新建两个 Pod。重试、重新附加和延迟执行也会影响实际 Pod 数量。

</details>

3. 当同时提供 pod_template_file 和 pod_template_dict 时，provider 10.21.0 会依次合并二者吗？

<details>
<summary>显示答案</summary>

**答案**：不会。它会选择文件，而不会再合并本次调用提供的字典。

**说明**：所选模板会与 full_pod_spec 和 KPO 构建的 Pod 协调。这不是无条件合并五种来源。

</details>

4. 如果 container_resources 只提供 limits，模板中的 requests 会保留吗？

<details>
<summary>显示答案</summary>

**答案**：不要假设会保留：这种合并会替换整个 resources 对象并丢弃原有 requests。

**说明**：应指定所有必需的 requests 和 limits，并检查最终 Pod。其他字段的合并规则不同，包括列表拼接、按键合并标签，以及继承 falsy 值。

</details>

5. 仅设置 KPO 的 service_account_name 就能赋予 Pod 访问 S3 的权限吗？

<details>
<summary>显示答案</summary>

**答案**：不能。还需要相应的 IAM 信任或关联，以及兼容的凭证 provider。

**说明**：验证 IRSA 或 Pod Identity 设置、SDK 凭证选择，以及实际允许/拒绝的访问。KPO 调用方的 Kubernetes RBAC 与子 Pod 的 AWS 权限不同。

</details>

6. 仅设置 toleration 就能强制工作负载运行在专用的带污点 NodePool 上吗？

<details>
<summary>显示答案</summary>

**答案**：不能。它只表示允许使用带有该污点的节点；可能还需要选择器或 required affinity。

**说明**：KPO Pod 使用标准 Kubernetes 调度。专用节点池并不能消除节点故障、Spot 回收或磁盘压力。

</details>

7. 启用版本控制的 GitDagBundle，每次重新运行是否都必须使用先前的 commit？

<details>
<summary>显示答案</summary>

**答案**：不是。请求、DAG 和全局的 rerun 设置，再加上逐次调用的默认值，可能会选择最新版本。

**说明**：在 3.3.1 中，clear/rerun 未设置时的回退值是 False，而 backfill 的回退值是 True。禁用 Bundle 版本控制会移除运行版本跟踪；仅固定 commit 并不能固定数据或镜像。

</details>

8. LocalDagBundle、S3DagBundle 和 GCSDagBundle 是否能保证后续 worker 读取到解析器使用的完全相同快照？

<details>
<summary>显示答案</summary>

**答案**：不能。这些 Bundle 目前不提供每次运行的 Bundle 版本控制。

**说明**：解析后，文件或对象仍可能发生变化。相关文件的一致部署和分发需要单独管理。

</details>

9. git-sync sidecar 是否已从 Airflow 3 移除？

<details>
<summary>显示答案</summary>

**答案**：没有。官方 Helm Chart 仍支持它。

**说明**：GitDagBundle 版本控制是另一项独立功能。使用 git-sync 既不会强制迁移，也不会天然保留每次运行所使用的 commit。

</details>

10. 应用固定名称的 SparkApplication 后只等待 COMPLETED，可能会出什么问题？

<details>
<summary>显示答案</summary>

**答案**：可能会把上次的 COMPLETED 状态误认为新运行成功；可能会监听错误的命名空间；对 FAILED 的处理也可能延迟。

**说明**：应明确定义执行身份、命名空间、终态处理和清理契约。原生 Spark Operator 也需要根据目标 CRD 验证生成的 CR。

</details>

## 简答题

11. 写出 KubernetesPodOperator 的导入语句，并指出用于容器资源的参数。

<details>
<summary>显示答案</summary>

**答案：**`from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator`；容器资源使用 `container_resources`。

**说明**：应使用 Kubernetes V1ResourceRequirements。不要将通用的 resources 参数误认为相同配置项。

</details>

12. 在 10.21.0 中，单独设置 is_delete_operator_pod=False 能保证保留 Pod 吗？

<details>
<summary>显示答案</summary>

**答案**：不能。构造函数中仍有该参数，但它并未被使用；应另外配置 on_finish_action 和 on_kill_action。

**说明**：正常完成与终止属于不同路径。重新附加也不能保证外部写入恰好一次。

</details>

13. 命名空间级 KPO Role 是否会将调用方限制为只能操作属于自身任务的 Pod？

<details>
<summary>显示答案</summary>

**答案**：不会。示例 Role 可能会影响该命名空间中所有符合权限范围的 Pod 资源。

**说明**：要区分调用方和工作负载服务账户。对于可能选择其他身份或危险 spec 的不可信 DAG 作者，应使用准入控制和信任边界。

</details>

## 应用

14. 写出 kpo_smoke 参数，以便传入运行 ID，并在完成或终止后删除 Pod。

<details>
<summary>显示答案</summary>

**答案**：以下是完整 DAG 中的相关参数。

```python
run_smoke = KubernetesPodOperator(
    task_id="run_smoke",
cmds=["python", "-B", "-c"],
arguments=[
    "import sys; print('KPO_SMOKE_OK run_id=' + sys.argv[1])",
    "{{ run_id }}",
],
on_finish_action="delete_pod",
on_kill_action="delete_pod",
)
```

**说明**：应将 run_id 作为单独参数传入，而不是插入 shell 命令。不要假设由 asset 触发的运行有 ds。完整的 DAG、RBAC 和模板设置请参阅本章。

</details>

15. 将模板中的 automountServiceAccountToken=True 覆盖为 False 并检查 dry_run 后，还需要检查什么？

<details>
<summary>显示答案</summary>

**答案**：检查最终合并值和被准入的 Pod，然后分别验证渲染、任务实例标签和实际执行。

**说明**：经审查的合并函数可能会继承基础值 True，而不是 falsy 的 False。dry_run 不能证明准入通过或任务成功；本章的本地检查也不能替代集群执行。

</details>

---

[返回学习资料](../../../data-on-eks/airflow/03-dag-patterns.md)

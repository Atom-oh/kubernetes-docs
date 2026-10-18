# 第 3 部分：DAG 模式与 KubernetesPodOperator

> **审查基线**：Airflow 3.3.1 / cncf-kubernetes provider 10.21.0
> **已检查的上游最新补丁版本**：Airflow 3.3.2；示例仍基于 3.3.1 · 2026 年 10 月 12 日

## 1. 执行器、KPO 和实际 Pod 数量

KubernetesPodOperator（KPO）允许 Airflow task 创建并观测单独的工作负载 Pod。它可以通过 CeleryExecutor、KubernetesExecutor 或其他兼容执行器运行。Airflow task 环境需要安装 provider，但**工作负载 Pod 本身并不必然需要安装 Airflow**。

| 典型的新执行方式 | 新建的 Pod 和共享资源 |
| --- | --- |
| CeleryExecutor + KPO | 现有 worker 进程运行 KPO 并创建工作负载 Pod；多个 task 可共用 worker Pod |
| KubernetesExecutor + KPO | 创建 Airflow task-runner Pod 和单独的 KPO 工作负载 Pod |

因此，更改执行器可能会改变实际 Pod 数量。两个逻辑执行角色并不意味着 Pod 数量保持不变。重试 / 重新关联可能会复用 Pod，也可能创建新的尝试；可延迟模式可以释放 worker slot，同时由 Triggerer 继续观测。不能保证始终恰好有两个运行中的 Pod。

## 2. 优先级还包含合并行为

Provider 10.21.0 按以下方式构造 Pod：

1. 如果存在 pod_template_file，则选择它。同一次调用中不会再合并 pod_template_dict。
2. 否则选择 pod_template_dict，或从 full_pod_spec / 空 Pod 开始。
3. 将所选模板与 full_pod_spec 合并，再与 KPO 构造的 Pod 合并。
4. Airflow 标签、Secret / XCom 处理、pod_mutation_hook 以及服务端准入 / 默认处理还会继续影响结果。

通常，image / namespace 等非空值会覆盖模板值，但并非每个字段都是简单替换。执行已发布的合并方法可以确认以下行为：

| 输入 | 结果 |
| --- | --- |
| 非空 image | 覆盖模板镜像 |
| 空 command 或 tolerations | 可能保留模板值 |
| 用 false 覆盖模板中的 true automount 值 | falsy 覆盖值可能保留 True；应检查最终 Pod |
| env / volume_mounts 等列表 | 可能会串接；空列表不一定会清除基值 |
| 只包含 limits 的 container_resources | 不会保留先前的 requests |
| 非空 node_selector | 可能整体替换先前的选择器 |
| Metadata 标签 | 按键合并 |
| Init container | 合并名称相同的项，并追加其他项 |

Kubernetes 容器资源请使用 **container_resources=V1ResourceRequirements(...)**。不要把通用 resources 参数与此设置混淆。应检查 dry_run 输出和实际准入后的 Pod，而不能只检查原始模板。

## 3. 准备一个可运行的小型 DAG

首先准备第 2 部分介绍的 Airflow 和 DAG 分发路径。此示例只会打印 run ID，不访问 S3，因此不需要 AWS 数据角色。真实工作负载需要自己的镜像、软件包和数据权限。

在 workload-access.yaml 中，将 RoleBinding 主体设为**实际运行 KPO 的 Airflow worker service account**。示例使用 airflow 命名空间中的 airflow-worker。这与工作负载 Pod 自己的 service account 不同。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: airflow-workloads
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: workload-smoke
  namespace: airflow-workloads
automountServiceAccountToken: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: airflow-kpo
  namespace: airflow-workloads
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - create
  - get
  - list
  - watch
  - patch
  - delete
- apiGroups:
  - ''
  resources:
  - pods/log
  verbs:
  - get
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: airflow-kpo-worker
  namespace: airflow-workloads
subjects:
- kind: ServiceAccount
  name: airflow-worker
  namespace: airflow
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: airflow-kpo
```

Role 的范围限定为工作负载命名空间，但会影响该命名空间中所有匹配的 Pod 资源。应使用信任边界和准入控制，限制不可信 DAG 作者选择特权身份或危险 Pod spec。本同步示例不需要 XCom exec 权限。添加 XCom sidecar 或启用 deferral 时，需要审查 pods/exec 权限和 Triggerer 的观测权限。

将以下文件一起放入 DAG bundle 分发：

```text
dags/
  kpo_smoke.py
  templates/
    base-pod-template.yaml
```

templates/base-pod-template.yaml 会由 KPO 补全，不是一个独立的 Pod 部署。其资源、文件系统和 UID 设置适用于此示例工作负载。

```yaml
apiVersion: v1
kind: Pod
metadata:
  labels:
    app: airflow-kpo-smoke
spec:
  serviceAccountName: workload-smoke
  automountServiceAccountToken: false
  restartPolicy: Never
  securityContext:
    runAsNonRoot: true
    runAsUser: 65532
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: base
    image: python:3.12-slim
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
```

kpo_smoke.py 定义了实际可被发现的 DAG。它会在 worker 上根据 bundle 文件的相对位置解析模板，而不是假设存在通用的 /opt/airflow/dags 路径。

```python
from datetime import datetime, timedelta, timezone
from pathlib import Path

from airflow.sdk import Asset, DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from kubernetes.client import models as k8s

TEMPLATES = Path(__file__).parent / "templates"
smoke_completed = Asset("demo://kpo-smoke-completed")

with DAG(
    dag_id="kpo_smoke",
    schedule=None,
    start_date=datetime(2026, 9, 1, tzinfo=timezone.utc),
    catchup=False,
) as dag:
    run_smoke = KubernetesPodOperator(
        task_id="run_smoke",
        name="kpo-smoke",
        namespace="airflow-workloads",
        in_cluster=True,
        pod_template_file=str(TEMPLATES / "base-pod-template.yaml"),
        service_account_name="workload-smoke",
        image="python:3.12-slim",
        cmds=["python", "-B", "-c"],
        arguments=["import sys; print('KPO_SMOKE_OK run_id=' + sys.argv[1])", "{{ run_id }}"],
        container_resources=k8s.V1ResourceRequirements(
            requests={"cpu": "250m", "memory": "128Mi"},
            limits={"cpu": "500m", "memory": "256Mi"},
        ),
        random_name_suffix=True,
        reattach_on_restart=True,
        deferrable=False,
        get_logs=True,
        do_xcom_push=False,
        startup_timeout_seconds=120,
        active_deadline_seconds=180,
        execution_timeout=timedelta(minutes=5),
        on_finish_action="delete_pod",
        on_kill_action="delete_pod",
        outlets=[smoke_completed],
    )

if __name__ == "__main__":
    run_smoke.dry_run()
```

在安装了 provider 的 Airflow 环境中，运行 python kpo_smoke.py 会打印 Pod 配置。在 10.21.0 版本的 dry_run 路径中，显式指定 namespace 并禁用 XCom 可避免初始化在线 Kubernetes client。Jinja 参数和 task-instance 标签仍需要真实的执行上下文；dry_run 不等于最终准入，也不代表成功执行。

run_id 会作为单独的命令参数传递。由 Asset 触发的 DAG run 可能没有 logical_date / ds 等时间上下文，因此不能假设每个 task 都存在 `{{ ds }}`。

应用 namespace / RBAC，验证 DAG 已分发并成功解析，然后通过 UI 或 CLI 触发 kpo_smoke。检查 task 状态、KPO_SMOKE_OK 日志，以及实际 Pod 的镜像、service account 和资源。成功后删除 Pod 是已配置的行为；若需要持久日志，请配置第 5 部分介绍的远程日志记录。

### 删除、终止和重启

Provider 10.21.0 接受 is_delete_operator_pod 参数，但构造函数并未使用该参数。设置为 False 并不能可靠地要求保留 Pod。对于相应的流程，应配置 **on_finish_action** 和 **on_kill_action**。重新关联会在重启后继续观测已有 Pod；它不能保证外部写入恰好执行一次。

## 4. 专用节点和 AWS 访问

确有需要时，添加与已准备 NodePool 匹配的 selector / required affinity 和 toleration。Toleration 允许 Pod 在有 taint 的情况下放置到节点上，但不会强制放置。专用节点池无法避免 Spot 回收、节点故障、磁盘压力或中断；其他工作负载也可能容忍相同 taint。

如需实际访问 S3，应为工作负载 service account 准备 IRSA OIDC 信任或 Pod Identity 关联 / Agent、IAM 权限以及兼容的 SDK / provider。仅有注解或 service_account_name 字符串并不足以完成 S3 访问。还应检查环境变量、IMDS 和 SDK 默认凭证链等其他凭证来源。Pod 生命周期也不必与临时凭证到期时间一致。应区分 Kubernetes RBAC 与 AWS 数据权限，并测试允许和拒绝的访问。

## 5. DAG bundle 和重跑时的代码版本

Bundle 会向 processor 和 worker 提供 DAG 代码及相关文件。目前 LocalDagBundle 和 S3DagBundle / GCSDagBundle 不对 bundle 版本进行管理。这并不保证解析器读取的快照与 worker 后续读取的代码一致。GitDagBundle 支持版本管理；git-sync 也仍受支持。

即使使用带版本的 bundle，也不会强制每次重跑都使用原提交。在 3.3.1 中，选择顺序如下：

1. API 请求中明确指定的 run_on_latest_version。
2. DAG 的 rerun_with_latest_version 值。
3. 全局 [core] rerun_with_latest_version。
4. 如果未设置，则按调用类型回退：clear / rerun 使用 False，backfill 使用 True。

disable_bundle_versioning 会单独禁用 run 的版本跟踪；如果版本从未被跟踪，重跑默认值就无法保留该版本。即使保留 Git commit，镜像、软件包、外部数据或配置发生变化，也不能复现原有结果。应根据需要保留代码库历史 / 访问权限并固定执行依赖。

Bundle kwargs 可能会通过 Config API 暴露出来。请引用 Airflow Connection 或合适的凭证机制，不要把 token 嵌入 repo_url。

![Airflow worker running KPO, workload pod creation and observation, and Airflow state reporting.](../../.gitbook/assets/en-data-on-eks-airflow-03-dag-patterns-0.png)

[交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-data-on-eks-airflow-03-dag-patterns-0.html)

## 6. Spark、dbt 和 Asset 集成

KPO 可以运行打包好的 dbt 或其他 CLI 工作负载。Spark 有多种集成路径：

| 路径 | 要验证的内容 |
| --- | --- |
| SparkKubernetesOperator | SparkApplication API / CRD 与 provider 兼容性、调用方 RBAC、driver 观测 / 清理 |
| SparkSubmitOperator 或 KPO submitter 镜像 | spark-submit 运行时 / 身份验证、driver / executor 角色，以及完成 / 失败处理 |
| CustomObjects client 或提交服务 | 明确的命名空间、唯一执行标识，以及状态 / 重试 / 清理约定 |

旧方法使用固定名称的 SparkApplication，应用后只等待 COMPLETED，可能会把先前的 COMPLETED 状态误认为本次运行成功。它还可能在错误的命名空间中等待，并且无法及时处理终止失败。本页不会将这种组合用作可运行基线。

原生 Operator 并非自动兼容所有版本组合。审查过的 10.21.0 SparkKubernetesOperator 会在重新关联设置中添加 spec.labels，但 Spark 章节中的 Kubeflow 2.5.2 CRD 缺少该字段。服务端字段校验 / 剪枝可能影响行为：应验证**最终生成的 CR**。该版本的 kill 路径会删除 Spark CR；在该路径中，delete_on_termination=False 并不能保留它。只验证输入 YAML 不构成集成测试。

基础 DAG 中的 demo://kpo-smoke-completed 是成功时发出的**演示 Asset 事件**。它不会自动检测 S3 对象或验证数据。下游 DAG 可以使用 schedule=[smoke_completed]，但真实流水线只应在预期数据已提交后才发出其 outlet 事件。

## 验证范围

已使用真实 Kubernetes Python model 执行未修改的已发布合并函数，以检查合并行为。构造函数检查属于源码 / AST 检查。这不是完整的 Airflow task、Kubernetes API、IAM / S3 或 Spark 集群执行 / 恢复测试。


- [Kubernetes provider 10.21.0 operators](https://airflow.apache.org/docs/apache-airflow-providers-cncf-kubernetes/10.21.0/operators.html)
- [KPO 实现](https://github.com/apache/airflow/blob/providers-cncf-kubernetes/10.21.0/providers/cncf/kubernetes/src/airflow/providers/cncf/kubernetes/operators/pod.py)
- [已发布的 PodGenerator 合并实现](https://github.com/apache/airflow/blob/providers-cncf-kubernetes/10.21.0/providers/cncf/kubernetes/src/airflow/providers/cncf/kubernetes/pod_generator.py)
- [DAG bundle 和重跑版本选择](https://airflow.apache.org/docs/apache-airflow/3.3.1/administration-and-deployment/dag-bundles.html)
- [模板上下文和逻辑日期](https://airflow.apache.org/docs/apache-airflow/3.3.1/templates-ref.html)
- [SparkKubernetesOperator 实现](https://github.com/apache/airflow/blob/providers-cncf-kubernetes/10.21.0/providers/cncf/kubernetes/src/airflow/providers/cncf/kubernetes/operators/spark_kubernetes.py)
- [Kubeflow SparkApplication 2.5.2 CRD](https://github.com/kubeflow/spark-operator/blob/v2.5.2/config/crd/bases/sparkoperator.k8s.io_sparkapplications.yaml)

[第 4 部分：MWAA 集成](04-mwaa-integration.md)

[README](README.md)

[测验](../../quizzes/data-on-eks/airflow/03-dag-patterns-quiz.md)

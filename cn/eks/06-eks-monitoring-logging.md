# Amazon EKS 监控与日志记录

> **最后更新**：October 16, 2026

有效的监控与日志记录对于维护 Amazon EKS 集群的可靠性、可用性和性能至关重要。本文介绍在 EKS 集群中实施监控与日志记录的各种工具、技术和最佳实践。

## 目录

1. [监控与日志记录概述](#monitoring-and-logging-overview)
2. [EKS 控制平面日志记录](#eks-control-plane-logging)
3. [容器日志记录](#container-logging)
4. [集群监控](#cluster-monitoring)
5. [告警与事件管理](#alerting-and-event-management)
6. [日志分析与可视化](#log-analysis-and-visualization)
7. [监控与日志记录最佳实践](#monitoring-and-logging-best-practices)
8. [故障排除与调试](#troubleshooting-and-debugging)

## 监控与日志记录概述

### 监控与日志记录的重要性

在 Amazon EKS 集群中，监控与日志记录之所以重要，原因如下：

1. **可见性**：提供对集群状态、性能和行为的可见性
2. **问题检测**：在问题变得严重之前及早发现
3. **趋势分析**：识别随时间变化的性能和资源使用趋势
4. **容量规划**：预测并规划资源需求
5. **安全与审计**：支持调查，并提供适用控制所需的证据
6. **故障排除**：发生问题时能够快速诊断并解决

### 监控与日志记录架构

全面的 EKS 集群监控与日志记录架构由以下组件构成：

AWS 会将托管控制平面日志交付到 CloudWatch Logs。容器运行时会写入 CRI 日志文件；kubelet 负责管理日志轮转和日志访问，而节点采集器会读取这些文件。指标和跟踪数据使用各自配置的采集/导出路径。

<!-- Audit: parent diagram repair needed for direct control-plane delivery and runtime-versus-kubelet log responsibilities.
![Architecture diagram showing EKS control-plane logs, pod logs, and node metrics flowing through Fluent Bit and Prometheus into CloudWatch Logs/Metrics, Amazon OpenSearch, and Grafana/Alertmanager.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-0.html)
-->

### 监控与日志记录策略

按照以下步骤制定有效的监控与日志记录策略：

1. **定义目标**：定义监控与日志记录的目标和要求
2. **确定指标和日志**：确定要采集的关键指标和日志
3. **选择工具**：选择满足要求的监控与日志记录工具
4. **建立基线**：为正常行为建立基线
5. **配置告警**：为重要事件和阈值配置告警
6. **自动化**：尽可能自动化监控与日志记录流程
7. **定期审查**：定期审查并改进监控与日志记录策略

## EKS 控制平面日志记录

EKS 会将选定类型的托管控制平面日志导出到 CloudWatch Logs。节点端采集器不会抓取托管控制平面的文件系统。日志传输尽力而为；请配置访问权限和保留期，并检测日志缺失，然后验证日志是否实际到达。

### 控制平面日志类型

| 类型 | 用途 |
|---|---|
| `api` | API server 组件诊断信息 |
| `audit` | 审计策略和级别选定的 Kubernetes 请求 |
| `authenticator` | EKS IAM 身份验证诊断信息 |
| `controllerManager` | 核心 controller-manager 操作 |
| `scheduler` | 调度器决策和诊断信息 |

审计日志并不无条件记录每个请求正文或每项应用操作。与 Secret 相关的记录可能只有元数据，而且策略会排除某些事件。CloudTrail AWS API 记录和应用数据访问日志属于独立的证据来源。

### 检查并启用日志记录

更改前，请检查自有集群的 Region、ARN、当前日志记录设置和更新状态。日志记录变更需要符合文档规定的子网 IP 容量要求，并会产生 CloudWatch 摄取/存储费用。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{ARN:arn,Status:status,Logging:logging}'
```

对于已批准的变更，以下命令会启用五种日志类型，并检查返回的更新信息：

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the reviewed cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
UPDATE_ID=$(aws eks update-cluster-config \
  --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query 'update.id' --output text)
if [[ -z "$UPDATE_ID" || "$UPDATE_ID" == None ]]; then
  printf '%s\n' 'No update ID returned; inspect the request result.' >&2
  exit 1
fi
aws eks describe-update --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --update-id "$UPDATE_ID" \
  --query 'update.{ID:id,Status:status,Errors:errors}'
```

最后一条命令用于检查状态，并不是等待器。请重复运行 DescribeUpdate，直到状态为 Successful 或出现终止失败，然后确认实际生效的设置以及日志是否到达。更新 ID 并不能证明更新已完成。仅启用选定类型不一定会禁用其他现有类型；任何明确禁用操作都属于单独的保留期/可见性决策。

使用经过审查的 eksctl CLI 时，省略 --approve 会预览变更。将 CLUSTER_NAME 和 AWS_REGION 设置为同一个已验证集群的对应值，并检查预览：

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
eksctl utils update-cluster-logging \
  --region "$AWS_REGION" --cluster "$CLUSTER_NAME" \
  --enable-types api,audit,authenticator,controllerManager,scheduler
```

审查计划后，使用单独的应用命令：

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
eksctl utils update-cluster-logging \
  --region "$AWS_REGION" --cluster "$CLUSTER_NAME" \
  --enable-types api,audit,authenticator,controllerManager,scheduler --approve
```

### 查询控制平面日志

使用实际的 `/aws/eks/CLUSTER_NAME/cluster` 日志组。前两个示例是针对所选组件流的文本搜索启发式方法，并非完整的错误率测量。

**API 诊断信息：**

```text
fields @timestamp, @message
| filter @logStream like /kube-apiserver-/ and @logStream not like /audit/
| filter @message like /[Ee]rror/
| sort @timestamp desc
| limit 20
```

**IAM 身份验证诊断信息：**

```text
fields @timestamp, @message
| filter @logStream like /authenticator/
| filter @message like /[Ff]ailed|[Dd]enied|[Uu]nauthorized/
| sort @timestamp desc
| limit 20
```

**审计拒绝：**使用发现的 JSON 字段，而不是在原始 JSON 文本中搜索字面字符串 responseStatus.code。请在样例事件中确认字段结构。

```text
fields @timestamp, user.username, verb, objectRef.resource, objectRef.namespace, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code in [401, 403]
| sort @timestamp desc
| limit 20
```

### 保留期与成本管理

检查返回的前缀搜索中准确的日志组条目：

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
aws logs describe-log-groups --region "$AWS_REGION" \
  --log-group-name-prefix "/aws/eks/$CLUSTER_NAME/cluster" \
  --query 'logGroups[].{Name:logGroupName,RetentionDays:retentionInDays,KmsKey:kmsKeyId}'
```

如果已批准的策略要求保留 30 天，则变更命令为 `aws logs put-retention-policy --region "$AWS_REGION" --log-group-name "/aws/eks/$CLUSTER_NAME/cluster" --retention-in-days 30`。30 天只是策略示例，并非普遍适用的合规要求。缩短保留期可能导致较早的证据过期；延长保留期也无法恢复已删除的日志。仅设置保留期无法证明日志已归档、具备完整性或符合合规要求。

### EKS Capabilities 日志记录（GitOps、ACK、kro）

2026 年 6 月 4 日推出的功能受支持：ACK、kro 和 Argo CD capability 控制器在 AWS 管理的基础设施中运行，**位于集群之外**，并可通过 CloudWatch Vended Logs 传输结构化控制器日志。此功能使用按 capability 单独配置的传输，与五种标准控制平面日志类型分开。

| Capability | 日志类型 |
|---|---|
| ACK | `EKS_CAPABILITY_ACK_LOGS` |
| kro | `EKS_CAPABILITY_KRO_LOGS` |
| Argo CD | `EKS_CAPABILITY_ARGOCD_APPLICATION_LOGS`、`EKS_CAPABILITY_ARGOCD_APPLICATIONSET_LOGS`、`EKS_CAPABILITY_ARGOCD_COMMITSERVER_LOGS`、`EKS_CAPABILITY_ARGOCD_REPOSERVER_LOGS`、`EKS_CAPABILITY_ARGOCD_SERVER_LOGS` |

配置传输源之前，请先获取实际的 capability ARN：

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${CAPABILITY_NAME:?Set the actual capability name}"
aws eks describe-capability --region "$AWS_REGION" \
  --cluster-name "$CLUSTER_NAME" --capability-name "$CAPABILITY_NAME" \
  --query 'capability.capabilityArn' --output text
```

所有者使用该 ARN/日志类型配置 PutDeliverySource，使用已批准的目标配置 PutDeliveryDestination，并通过 CreateDelivery 将二者关联。启用传输之前，请审查目标策略、加密、跨账户权限和保留期。

CloudWatch Logs 目标支持 Logs Insights 查询。S3 目标是供所选 S3/Athena 工作流使用的对象；Firehose 会将记录发送到其配置的目标；这些目标不会自动通过 CloudWatch Logs Insights 查询。ACK 记录包含 controllerGroup，可用于按 service-controller 筛选。请确认实际传输和查询字段，并将 Vended Logs 费用纳入考虑。

参考资料：[EKS 控制平面日志记录](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)、[审计策略和查询示例](https://docs.aws.amazon.com/eks/latest/best-practices/auditing-and-logging.html)、[capability 控制器日志](https://docs.aws.amazon.com/eks/latest/userguide/capabilities-controller-logs.html)。

## 容器日志记录

容器运行时会将 stdout/stderr 写入节点的 CRI 日志文件。kubelet 负责管理日志轮转并提供 Pod 日志访问；采集器会跟踪这些文件，并将记录转发到所选后端。JSON 格式的应用消息仍然位于 CRI 封装中，不能把整条容器日志行当作 Docker JSON 来解析。

<!-- Audit: parent diagram repair needed for direct control-plane delivery and runtime-versus-kubelet log responsibilities.
![Architecture diagram showing container stdout/stderr picked up by kubelet, read by a log agent, and fanned out to CloudWatch Logs, Amazon OpenSearch, and Amazon S3.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-1.html)
-->

### 选择采集器所有者

CloudWatch Observability add-on 包含容器日志采集器；如果选择使用该技术栈，请通过其所属配置进行管理。下面独立的 Fluent Bit 示例则适用于独立管理的日志管道。除非有明确的重复采集和成本计划，否则不要在相同文件/目标上安装重叠的采集器。

### 已接线的 Fluent Bit 示例

此示例使用 AWS chart 0.2.0 和 image 3.4.14（Fluent Bit 5.0.9），已核对其已发布版本和配置。示例针对自有 Linux/containerd EC2 节点；affinity 会有意排除此示例中的 Fargate、Auto Mode 和 Hybrid 标签。这些模式需要各自受支持的采集/身份设计。采集器会容忍所选节点上的 taint，因此请审查其放置方式以及平台代理的准入权限。

准备 logging namespace、具有最小权限的 IRSA 角色 EKSLogWriter（适用于 service account logging/eks-log-collector），以及自有 CloudWatch 日志组。请在所有位置一致地替换账户、角色、Region 和集群专属日志组。按照安全章节中的说明配置 IAM OIDC provider/trust audience/subject。采集器需要 CloudWatch 流/写入权限，以及区域 STS/后端连接能力。这些 IAM 前提条件与 Kubernetes 元数据 RBAC 相互独立。

将以下内容保存为 fluent-bit-values.yaml：

```yaml
fullnameOverride: eks-log-collector
image:
  tag: 3.4.14
serviceAccount:
  create: true
  name: eks-log-collector
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/EKSLogWriter
nodeSelector:
  kubernetes.io/os: linux
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: eks.amazonaws.com/compute-type
          operator: NotIn
          values:
          - fargate
          - auto
          - hybrid
tolerations:
- operator: Exists
service:
  extraService: 'Flush 5

    Log_Level info

    Daemon Off

    HTTP_Server On

    HTTP_Listen 0.0.0.0

    HTTP_Port 2020

    Health_Check On

    storage.path /var/fluent-bit/state/storage

    storage.sync normal

    storage.checksum On

    storage.backlog.mem_limit 20M

    '
input:
  path: /var/log/containers/*.log
  db: /var/fluent-bit/state/tail.db
  multilineParser: cri
  skipLongLines: 'On'
  extraInputs: 'storage.type filesystem

    Read_from_Head On

    '
filter:
  kubeURL: https://kubernetes.default.svc:443
  mergeLog: 'On'
  mergeLogKey: data
  keepLog: 'On'
  k8sLoggingParser: 'Off'
  k8sLoggingExclude: 'Off'
  extraFilters: 'Use_Kubelet Off

    '
cloudWatch:
  enabled: false
cloudWatchLogs:
  enabled: true
  region: us-west-2
  logGroupName: /aws/eks/my-cluster/application
  logStreamPrefix: unmatched-
  logStreamTemplate: $kubernetes['namespace_name'].$kubernetes['pod_name'].$kubernetes['container_name']
  autoCreateGroup: false
  extraOutputs: 'auto_create_group false

    storage.total_limit_size 512M

    '
volumes:
- name: varlog
  hostPath:
    path: /var/log
    type: Directory
- name: state
  hostPath:
    path: /var/lib/eks-log-collector
    type: DirectoryOrCreate
volumeMounts:
- name: varlog
  mountPath: /var/log
  readOnly: true
- name: state
  mountPath: /var/fluent-bit/state
```

Chart 0.2.0 默认启用原生 cloudWatchLogs 输出，并禁用较旧的 cloudWatch 输出。因此，仅设置 cloudWatch.region 并不能配置当前启用的原生输出。上面的 values 设置了实际输出的 Region/group，并保留完整记录；log_key 只会发送选定值，可能会丢失 Kubernetes 上下文。

logStreamTemplate 使用 record-accessor 语法，并带有备用前缀。logStreamPrefix 是字面前缀，不是按记录解析的 Kubernetes 表达式。CRI 多行解析器负责处理容器封装，而 Merge_Log 会将 JSON 应用字段放在 data 下，并保留 log。工作负载注解不能选择解析器，也不能选择退出此示例的采集。

### 在渲染期间限制元数据 RBAC

已发布 chart 的宽泛 ClusterRole 包含 nodes/proxy 和旧版 PodSecurityPolicy 规则。此 API server 元数据模式会明确设置 Use_Kubelet Off，只需要对所选 Pod/Namespace 的读取权限，不需要 kubelet proxy 访问。将以下 Python 3 + PyYAML 后渲染器保存为 fluent-bit-rbac.py。如果 chart 身份与预期不符，它会拒绝继续，而不会悄悄保留其他宽泛角色：

```python
#!/usr/bin/env python3
"""Helm post-renderer for this pinned, owned metadata-only Fluent Bit setup."""
import sys
import yaml

objects = [obj for obj in yaml.safe_load_all(sys.stdin) if obj is not None]
roles = [obj for obj in objects if obj.get("kind") == "ClusterRole"]
bindings = [obj for obj in objects if obj.get("kind") == "ClusterRoleBinding"]
if len(roles) != 1 or roles[0].get("metadata", {}).get("name") != "eks-log-collector":
    raise SystemExit("Unexpected chart RBAC; review this renderer before proceeding")
if len(bindings) != 1 or bindings[0].get("roleRef", {}).get("name") != "eks-log-collector":
    raise SystemExit("Unexpected chart role binding")
subjects = bindings[0].get("subjects", [])
if len(subjects) != 1 or any(
    subjects[0].get(key) != value
    for key, value in {
        "kind": "ServiceAccount", "name": "eks-log-collector", "namespace": "logging"
    }.items()
):
    raise SystemExit("Unexpected collector identity")
if any(obj.get("kind") == "PodSecurityPolicy" for obj in objects):
    raise SystemExit("Obsolete PodSecurityPolicy output is not supported by this example")
roles[0]["rules"] = [{
    "apiGroups": [""],
    "resources": ["namespaces", "pods"],
    "verbs": ["get", "list", "watch"],
}]
yaml.safe_dump_all(objects, sys.stdout, sort_keys=False)
```

对于新的自有版本，请同时使用 values 和后渲染器进行安装：

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
chmod +x fluent-bit-rbac.py
helm install eks-log-collector eks/aws-for-fluent-bit \
  --version 0.2.0 --namespace logging --create-namespace \
  -f fluent-bit-values.yaml --post-renderer ./fluent-bit-rbac.py \
  --wait --timeout 5m
```

每次升级都使用相同且经过审查的后渲染器；更改 chart 版本、release 身份、namespace 或元数据模式时，重新验证该渲染器。实际 DaemonSet 会挂载渲染后的 ConfigMap；仅应用一个无关的 ConfigMap 不会更改其配置。账户/IRSA 角色和日志组是前提条件，并非由此 chart 示例创建的资源。

### 缓冲、轮转与故障行为

主机日志以只读方式读取；检查点和文件系统缓冲状态使用独立的节点本地目录。tail 数据库用于记录偏移量，本身并不是持久化的后端归档。节点替换可能会移除该状态。没有检查点时，Read_from_Head On 会读取保留文件中的内容，因此应规划回填和重复记录处理。

512M 输出队列限制和 backlog 内存设置只是示例分配。输出队列达到 storage.total_limit_size 时，Fluent Bit 可能会丢弃最旧的块。Skip_Long_Lines On 也会有意跳过超长记录。有限缓冲区、重试和节点本地状态无法保证无损或恰好一次传递。请监控重试、丢弃记录、磁盘容量和目标故障；根据实际日志速率和中断时间窗口验证这些限制。

### 可选的 OpenSearch 扇出

准备好自有 VPC domain 和采集器的 IAM/FGAC 映射后，将此 overlay 保存为 fluent-bit-opensearch-values.yaml，并替换 endpoint 主机名。在同一项经过审查的 Helm 操作中添加 `-f fluent-bit-opensearch-values.yaml`。保持 CloudWatch 启用会向两个目标发送副本；只有在有意仅选择 OpenSearch 时才设置 cloudWatchLogs.enabled=false。

```yaml
opensearch:
  enabled: true
  host: vpc-eks-logs-EXAMPLE.us-west-2.es.amazonaws.com
  port: '443'
  tls: 'On'
  awsAuth: 'On'
  awsRegion: us-west-2
  index: eks-logs
  generateId: 'On'
  suppressTypeName: 'On'
  extraOutputs: 'tls.verify On

    storage.total_limit_size 512M

    '
```

使用 TLS 证书/主机名验证以及固定、受治理的索引/滚动设计。按 Pod 设置索引模式可能会导致索引/分片数量过多。Generate_ID 可减少重试时的重复索引；但仍需验证独立输出和故障恢复。成功写入一个目标并不能证明数据已传送到另一个目标。

### 其他日志技术栈

如果自有部署提供所需的解析器/输出插件、主机挂载、身份和 TLS 配置，Fluentd 仍然是一种选择。通用 JSON 解析器无法解码 CRI 封装，禁用 ssl_verify 也不能解决证书错误。旧版 Elastic Helm chart 仓库已归档；部署 Elastic 时请使用维护中的产品/operator 安装路径。

loki-stack chart 已标记为弃用，Promtail agent 已于 2026 年 3 月 2 日结束生命周期。对于 Loki，请使用当前受支持的部署和受支持的客户端（例如 Alloy），并明确配置存储、访问控制和保留期。专用设置请参阅 [Loki 指南](../observability/logging/01-loki.md) 和 [采集器指南](../observability/logging/05-collectors.md)。Promtail agent 退役不包括单独维护的 lambda-promtail 客户端。

### 结构化应用日志

以下保留示例是合成应用数据，不是新的测量值，也不是本次审计的记录。其时间戳仍为原始示例值：

```json
{
  "timestamp": "2025-07-11T13:00:00Z",
  "level": "INFO",
  "message": "Request processed successfully",
  "request_id": "12345",
  "user_id": "user-789",
  "duration_ms": 45,
  "status_code": 200
}
```

在已配置的管道中，CRI 记录提供传输时间戳，应用 JSON 位于 data 下。使用应用字段覆盖时间戳之前，请验证时区和时钟行为。用户/会话标识符仍可能是敏感信息或可关联信息；请尽量减少此类数据，绝不要记录凭证或原始会话令牌。

以下示例假定使用此采集器的记录结构。其他采集器可能使用不同的字段路径：

```text
fields @timestamp, kubernetes.namespace_name, kubernetes.pod_name, data.level, log
| filter kubernetes.namespace_name = "production"
| filter data.level in ["ERROR", "error"]
| sort @timestamp desc
| limit 100
```

验证涵盖已发布的 chart/image 元数据、实际 Helm ConfigMap/DaemonSet 接线、原生 Kubernetes schema 和后渲染器故障场景。没有安装 image、启动采集器进程、向 AWS 发送日志或测试生产文件系统访问。发布前，请验证实际节点权限、IRSA 凭证和端到端日志传输。

参考资料：[AWS image 版本 3.4.14](https://github.com/aws/aws-for-fluent-bit/releases/tag/v3.4.14)、[CloudWatch 输出](https://docs.fluentbit.io/manual/data-pipeline/outputs/cloudwatch)、[Fluent Bit 缓冲](https://docs.fluentbit.io/manual/data-pipeline/buffering)、[Promtail 生命周期](https://grafana.com/docs/loki/latest/send-data/promtail/)。

## 集群监控

有效的集群监控对于跟踪 EKS 集群的状态、性能和资源使用情况至关重要。本节介绍监控 EKS 集群的各种工具和技术。

![Diagram mapping monitoring solutions (CloudWatch Container Insights with AMP/AMG, the Prometheus stack with kube-state-metrics, Node Exporter and Grafana, and X-Ray/OpenTelemetry tracing) to the cluster-, node-, and pod-level telemetry they cover in an EKS cluster.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-2.html)

### CloudWatch Container Insights

CloudWatch Observability add-on 集成了 Container Insights、容器日志采集和 Application Signals 功能。使用一个自有安装，并避免其 Fluent Bit 采集器与读取相同文件的其他采集器重叠。开始期待数据之前，请配置身份、受支持的节点访问权限和后端连接能力。

#### 检查集群和兼容的 add-on 版本

对于此标准 Linux EC2 示例，请准备适用的 EKS Pod Identity agent 和专用 CloudWatch 角色，并将信任范围限定为此集群以及 amazon-cloudwatch/cloudwatch-agent。操作员需要所需的 add-on/association 权限，以及传递已批准角色的权限。除了 EKS add-on 列表外，还请检查现有 Helm release、ServiceAccount 注解和 association；已有采集器需要遵循其所有者的迁移/升级流程。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
CLUSTER_VERSION=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.version --output text)
aws eks list-addons --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
aws eks describe-addon-versions --region "$AWS_REGION" \
  --addon-name amazon-cloudwatch-observability --kubernetes-version "$CLUSTER_VERSION"
```

请从目录中选择兼容且经过审查的版本，而不要降级到写死的 v5.0.0 示例。add-on 配置 schema 因版本而异。此处本地参考渲染使用 Helm chart 6.6.0，其中 Fluent Bit DaemonSet 使用与 agent 身份路径相同的 cloudwatch-agent ServiceAccount。

#### 明确配置 Auto Monitor

对于新安装示例，将以下内容保存为 cloudwatch-config.json。此配置保留默认容器日志配置，同时在审查应用 rollout 之前，禁用广泛的自动工作负载选择和自动重启：

```json
{
  "manager": {
    "applicationSignals": {
      "autoMonitor": {
        "monitorAllServices": false,
        "restartPods": false
      }
    }
  }
}
```

此配置控制 Auto Monitor 的选择/重启，不会控制所有可能的遥测来源。现有注解、自定义选择器或手动插桩的应用需要单独审查。若本地已安装 Python 3 和 jsonschema，请获取所选版本的 schema 并检查配置：

```bash
set -euo pipefail
: "${AWS_REGION:?Set the cluster Region}"
: "${CLOUDWATCH_ADDON_VERSION:?Choose a reviewed compatible add-on build}"
aws eks describe-addon-configuration --region "$AWS_REGION" \
  --addon-name amazon-cloudwatch-observability --addon-version "$CLOUDWATCH_ADDON_VERSION" \
  --output json > cloudwatch-addon-review.json
python3 - "$CLOUDWATCH_ADDON_VERSION" <<'PY'
import json
import sys
import jsonschema
with open("cloudwatch-addon-review.json") as stream:
    review = json.load(stream)
if review["addonName"] != "amazon-cloudwatch-observability" or review["addonVersion"] != sys.argv[1]:
    raise SystemExit("Returned schema does not match the selected add-on build")
schema = json.loads(review["configurationSchema"])
with open("cloudwatch-config.json") as stream:
    config = json.load(stream)
validator = jsonschema.validators.validator_for(schema)
validator.check_schema(schema)
validator(schema).validate(config)
PY
```

#### 创建新的自有安装

CloudWatch 角色必须预先具有所选功能所需的 CloudWatch/trace 权限。以下命令会重新检查经过审查的 schema/版本，拒绝已存在的 add-on 或采集器 association，并避免接管冲突资源：

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the reviewed cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${CLOUDWATCH_ADDON_VERSION:?Set the reviewed, schema-checked compatible build}"
: "${CLOUDWATCH_ROLE_ARN:?Set the prepared CloudWatch Pod Identity role ARN}"
python3 - "$CLOUDWATCH_ADDON_VERSION" <<'PY'
import json
import sys
import jsonschema
with open("cloudwatch-addon-review.json") as stream:
    review = json.load(stream)
if review["addonName"] != "amazon-cloudwatch-observability" or review["addonVersion"] != sys.argv[1]:
    raise SystemExit("Selected add-on build changed; review its schema again")
schema = json.loads(review["configurationSchema"])
with open("cloudwatch-config.json") as stream:
    config = json.load(stream)
jsonschema.validators.validator_for(schema)(schema).validate(config)
PY
EXISTING_ADDONS=$(aws eks list-addons --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" --output json)
python3 - "$EXISTING_ADDONS" <<'PY'
import json, sys
if "amazon-cloudwatch-observability" in json.loads(sys.argv[1])["addons"]:
    raise SystemExit("Add-on already exists; use its owner's reviewed upgrade procedure")
PY
EXISTING_ASSOCIATIONS=$(aws eks list-pod-identity-associations \
  --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --namespace amazon-cloudwatch --service-account cloudwatch-agent --output json)
python3 - "$EXISTING_ASSOCIATIONS" <<'PY'
import json, sys
if json.loads(sys.argv[1])["associations"]:
    raise SystemExit("Collector association already exists; inspect its owner before installation")
PY
ASSOCIATIONS=$(python3 - "$CLOUDWATCH_ROLE_ARN" <<'PY'
import json, sys
print(json.dumps([{"serviceAccount": "cloudwatch-agent", "roleArn": sys.argv[1]}]))
PY
)
aws eks create-addon --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --addon-name amazon-cloudwatch-observability --addon-version "$CLOUDWATCH_ADDON_VERSION" \
  --pod-identity-associations "$ASSOCIATIONS" \
  --configuration-values file://cloudwatch-config.json --resolve-conflicts NONE
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --addon-name amazon-cloudwatch-observability \
  --query 'addon.{Status:status,Version:addonVersion,Health:health.issues}'
```

CreateAddon 是异步操作。请检查状态/运行状况，直到 add-on 变为 ACTIVE，然后验证 agent/collector Pods、实际 ContainerInsights 数据点和预期日志组。请求成功、状态为 ACTIVE 或仅有仪表板，都不能证明数据已完整摄取。上面的最后一条 DescribeAddon 命令是检查命令，并非等待器。重试之前请先验证故障和权限；不要使用未经审查的覆盖操作，也不要为了强制安装而清除现有配置。

#### 版本 5.0.0 中的变更

2026 年 2 月 26 日关于默认 APM 的变更确实存在：5.0.0 及更高版本在新安装和升级时默认启用 Application Signals Auto Monitor。monitorAllServices 默认值为 true；restartPods 默认值为 false。其范围是受支持的、映射到服务的 Deployments、DaemonSets 和 StatefulSets，默认排除 kube-system 和 amazon-cloudwatch。范围内的新工作负载或重启的工作负载无需逐个添加注解即可进行插桩；但不能保证已经运行的 Pods 会立即重新插桩。

选择受支持的语言/工作负载，审查现有 OpenTelemetry/APM 集成、采样和成本，并控制任何重启 rollout。明确的排除项具有优先权。Container Insights 支持 Linux 和 Windows 配置，但 Application Signals 不支持 EKS Windows 节点。Fargate 和 Hybrid 节点采集/身份需要遵循各自文档规定的平台专属路径；不要从通用 DaemonSet 示例推断其受支持。

#### 指标、仪表板和告警

在 Container Insights 控制台视图中选择实际集群，并检查已发布的指标名称、维度和近期数据。节点 CPU/内存/文件系统指标描述节点使用情况。Pod CPU/内存利用率以节点 limits 为分母，而不是 Pod requests。文档定义的指标提供 namespace/service/cluster 汇总，但汇总百分比并不自动等于异构集群中按容量加权的利用率。

仪表板有助于检查数据，但不会创建所有告警，也不能保证通知送达。稍后的 CloudWatch Alarms 示例使用节点指标和 Maximum，并明确选择维度。请验证指标是否可用，并为工作负载配置适当的告警和传递路径。

验证使用了现有已发布 chart、其渲染后的默认日志配置和 Auto Monitor 参数，以及九种模拟 schema/所有权/故障流程的测试。合成测试 schema 仅用于检查辅助程序行为，不能代替上文针对实时版本的 schema。此次审计未启用 add-on、未对工作负载插桩、未导出遥测，也未操作 AWS 资源。

参考资料：[CloudWatch add-on 安装和 Auto Monitor](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html)、[默认 APM 公告](https://aws.amazon.com/about-aws/whats-new/2026/02/application-performance-monitoring-cloudwatch-eks/)、[Container Insights 指标](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)。

### EKS Node Monitoring Agent

EKS Node Monitoring Agent 会发布节点级系统、存储、网络和加速器运行状况条件。它于 2026 年 2 月 24 日开源，并已包含在 EKS Auto Mode 中。对于单独管理的 add-on 安装，在选择版本之前，请检查集群的实际版本、现有 add-on 和兼容的 agent 版本：

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
KUBERNETES_VERSION=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.version --output text)
aws eks list-addons --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
aws eks describe-addon-versions --addon-name eks-node-monitoring-agent \
  --kubernetes-version "$KUBERNETES_VERSION" --region "$AWS_REGION"
```

通过现有 add-on 所有者，使用经过审查的版本和受支持的节点配置进行安装或更新。add-on 创建命令并不是更新现有安装的流程。

仅凭条件名称无法判断节点是否不健康。请读取状态和原因，并正确理解每个条件的含义：Ready=False 与 MemoryPressure=False 并不相同。

```bash
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{range .status.conditions[*]}{"  "}{.type}{"="}{.status}{" reason="}{.reason}{"\n"}{end}{end}'
```

监控和修复启用是两个独立方面。Auto Mode 已启用自动节点修复；托管 node groups 使用 nodeRepairConfig，Karpenter 使用 NodeRepair feature gate。请先检查实际的托管 node group，再判断其修复行为是否由 agent 决定：

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${NODEGROUP_NAME:?Set an actual managed node group name}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-nodegroup --region "$AWS_REGION" \
  --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --query 'nodegroup.{Name:nodegroupName,Repair:nodeRepairConfig,Health:health.issues}'
```

修复是否适用取决于条件、原因、等待时间和相关防护措施。根据文档默认设置，MemoryPressure 和 DiskPressure 没有自动修复操作。不要把每个报告的条件或 agent 安装都视为节点将被替换的证明。自定义开源 agent 还需要针对所选修复配置测试其条件语义。

参考资料：[开源公告](https://aws.amazon.com/about-aws/whats-new/2026/02/amazon-eks-node-monitoring-agent-open-source/)、[自动节点修复](https://docs.aws.amazon.com/eks/latest/userguide/node-repair.html)。

### Prometheus 和 Grafana

Prometheus 是时序数据库和监控系统，Grafana 是用于可视化指标的仪表板工具。可以结合使用这两种工具，全面监控 EKS 集群。

#### Amazon Managed Service for Prometheus 和 Grafana

AMP 会存储并查询摄取的 Prometheus 指标；AMG 会查询已配置的数据源并呈现仪表板。创建任一 workspace 都不会自动部署 scraper、授予其 AWS 身份或连接数据源。此示例会检查已有的自有 workspace，并扩展下面的 kube-prometheus-stack release，避免再安装第二个 Prometheus。

**AMP 摄取身份和 values**

为 ServiceAccount monitoring/amp-writer 准备 IRSA 角色。其信任策略必须使用此集群的 OIDC provider，并设置精确的 sub=system:serviceaccount:monitoring:amp-writer 和 aud=sts.amazonaws.com 条件。授予其对目标 workspace ARN 的 aps:RemoteWrite 权限。Prometheus 进程必须能够获取投射的令牌并访问 STS 和 AMP endpoint；Kubernetes RBAC 是独立的权限路径。此示例中不要额外附加无关的 Pod Identity association 或静态 AWS 密钥。

以下命令读取 workspace，并为经过审查的 chart 92.9.0 写入一个 overlay。它接受有或没有 /api/v1/ 的文档化 endpoint 格式，并且仅追加一次 remote_write。需要 Python 3；不会创建 workspace：

```bash
set -euo pipefail
: "${AWS_REGION:?Set the AMP workspace Region}"
: "${AMP_WORKSPACE_ID:?Set the owned AMP workspace ID}"
: "${AMP_WRITE_ROLE_ARN:?Set the prepared IRSA writer role ARN}"
: "${CLUSTER_NAME:?Set the source cluster name}"
aws amp describe-workspace --region "$AWS_REGION" \
  --workspace-id "$AMP_WORKSPACE_ID" --output json > amp-workspace.json
python3 - "$AWS_REGION" "$AMP_WORKSPACE_ID" "$AMP_WRITE_ROLE_ARN" "$CLUSTER_NAME" <<'PY'
import json
import sys
from urllib.parse import urlsplit, urlunsplit

region, workspace_id, role_arn, cluster = sys.argv[1:]
with open("amp-workspace.json") as stream:
    workspace = json.load(stream)["workspace"]
if workspace["workspaceId"] != workspace_id or workspace["status"]["statusCode"] != "ACTIVE":
    raise SystemExit("Review the workspace identity and ACTIVE status")
arn = workspace["arn"].split(":", 5)
if len(arn) != 6 or arn[2] != "aps" or arn[3] != region or arn[5] != "workspace/" + workspace_id:
    raise SystemExit("Workspace ARN does not match the selected Region/ID")
endpoint = urlsplit(workspace["prometheusEndpoint"])
path = endpoint.path.rstrip("/")
if path.endswith("/api/v1"):
    path = path[:-7]
if (endpoint.scheme != "https" or not endpoint.hostname or endpoint.username
        or endpoint.password or endpoint.query or endpoint.fragment
        or path != "/workspaces/" + workspace_id):
    raise SystemExit("Inspect the workspace endpoint before configuring remote write")
remote_write = urlunsplit((endpoint.scheme, endpoint.netloc, path + "/api/v1/remote_write", "", ""))
values = {
    "prometheus": {
        "serviceAccount": {
            "create": True, "name": "amp-writer", "createTokenSecret": True,
            "annotations": {"eks.amazonaws.com/role-arn": role_arn},
        },
        "prometheusSpec": {
            "externalLabels": {"cluster": cluster},
            "remoteWrite": [{"url": remote_write, "sigv4": {"region": region}}],
        },
    },
}
with open("amp-values.json", "w") as stream:
    json.dump(values, stream, indent=2)
    stream.write("\n")
print("Wrote amp-values.json; review it with all existing release values")
PY
```

将 amp-values.json 与 monitoring-values.yaml 一起合并到所有者审查过的安装/升级 values 中。overlay 会替换 remoteWrite 列表；请有意保留任何现有目标和 external labels。对于新的 release，请在下面的安装命令中添加 -f amp-values.json。对于现有 release，请保留所有当前设置，并在通过所有者的升级流程应用之前审查渲染差异和 rollout。更改 ServiceAccount 会改变 Prometheus Pod 身份。Chart 92.9.0 使用显式 ServiceAccount token Secret，为默认 API server/kubelet ServiceMonitor 授权。请保护该 Secret，并遵循其轮换/撤销流程；它与短期、受 audience 限定的 IRSA 令牌不同。若禁用 createTokenSecret 但没有替换所有依赖该 Secret 的监控凭证，将导致渲染失败或身份验证失败。

对于多个副本，请配置 AMP 文档规定的 HA 去重标签和副本拓扑，而不要假定重复 scrape 不会产生额外成本。根据实际工作负载设置基数、保留期和摄取预算。检查 remote-write 故障/积压，并在目标 workspace 中查询近期数据；Helm rollout 成功并不能证明数据已摄取。

**AMG 身份验证和数据源连接**

```bash
set -euo pipefail
: "${AMG_REGION:?Set the Grafana workspace Region}"
: "${AMG_WORKSPACE_ID:?Set the owned Grafana workspace ID}"
aws grafana describe-workspace --region "$AMG_REGION" \
  --workspace-id "$AMG_WORKSPACE_ID" \
  --query 'workspace.{ID:id,Status:status,Version:grafanaVersion,Endpoint:endpoint,Role:workspaceRoleArn,Authentication:authentication,PermissionType:permissionType}'
```

Workspace 用户身份验证（IAM Identity Center/SAML）、Grafana 用户权限以及 workspace 的 AWS 数据源 IAM 角色是不同的控制项。Grafana service account 是 Grafana HTTP API 的身份；创建 ADMIN service account 不会创建 AMP 数据源，也不会授予 aps:QueryMetrics 权限。不要仅仅为了查看指标，就配置宽泛的 API 身份。

在 AMG 12 及更高版本中，请选择 Amazon Managed Service for Prometheus 数据源插件。在该 AMG 版本中，Core Prometheus 插件已移除 SigV4 支持，现有 AMP 数据源会迁移到 AMP 插件。请使用与 workspace 实际版本相匹配的文档。通过已批准的 workspace 配置选择目标账户/Region/workspace，配置其查询身份，并测试一个已知序列。文档中的 AWS 数据源配置流程使用服务托管权限；客户托管的 workspace 需要自己的、经过审查的 IAM 配置，而不会自动变更资源所有权。

查询角色通常需要限定到 workspace 的 aps:QueryMetrics、aps:GetSeries、aps:GetLabels 和 aps:GetMetricMetadata；发现或其他已启用功能可能需要额外操作。其查询 endpoint 不是 remote_write 摄取 URL。如果单独预置 workspace，CLI 使用 --workspace-name，并要求 --account-access-type、身份验证和权限配置；服务托管的 IAM 自动化与文档规定的控制台工作流绑定。在将 workspace 视为可用之前，请完成身份、用户分配和网络访问设置。

参考资料：[AMP remote write](https://docs.aws.amazon.com/prometheus/latest/userguide/AMP-onboard-ingest-metrics-existing-Prometheus.html)、[AMG AMP 插件](https://docs.aws.amazon.com/grafana/latest/userguide/amazon-prometheus-data-source.html)、[AWS 数据源配置](https://docs.aws.amazon.com/grafana/latest/userguide/amazon-AMP-adding-AWS-config.html)。此次审计未操作任何 workspace、身份验证流程或遥测摄取。

#### 自行管理 Prometheus 和 Grafana

此示例使用一个自有 kube-prometheus-stack release，其中包含 ServiceMonitor 和 PrometheusRule 示例所需的 Prometheus Operator。独立的 Prometheus chart 不会自动提供这些 CRD/控制器。安装前，请检查现有 operator、release 和 CRD 所有权；对于现有技术栈，请遵循所有者的升级流程。

经过审查的基线是 chart 92.9.0 / Operator 0.94.1，针对 EKS 1.36 渲染。此示例假定使用标准 Linux EC2 节点，以及已准备好的加密 ebs-gp3 StorageClass，并且 EBS CSI 权限可正常工作。对于 Auto Mode 或其他存储实现，请选择实际受支持的 class 和节点放置方式。以下保留期和 PVC 容量只是示例分配值，并非经过测量的容量保证。

通过已批准的 Secret 管理流程准备 monitoring namespace 和 Secret grafana-admin，其中包含 admin-user/admin-password 键。values 引用该 Secret，而不会将共享密码写入 Helm values 或命令参数。将以下内容保存为 monitoring-values.yaml：

```yaml
grafana:
  admin:
    existingSecret: grafana-admin
    userKey: admin-user
    passwordKey: admin-password
  service:
    type: ClusterIP
  rbac:
    namespaced: true
  sidecar:
    dashboards:
      searchNamespace: monitoring
    datasources:
      searchNamespace: monitoring
  persistence:
    enabled: true
    storageClassName: ebs-gp3
    size: 10Gi
    accessModes:
    - ReadWriteOnce
  deploymentStrategy:
    type: Recreate
prometheus:
  prometheusSpec:
    retention: 14d
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: ebs-gp3
          accessModes:
          - ReadWriteOnce
          resources:
            requests:
              storage: 20Gi
kubeEtcd:
  enabled: false
kubeControllerManager:
  enabled: false
kubeScheduler:
  enabled: false
kubeProxy:
  enabled: false
kubelet:
  serviceMonitor:
    tlsConfig:
      insecureSkipVerify: false
      ca:
        configMap:
          name: kubelet-serving-ca
          key: ca.crt
```

Grafana 的 dashboard/data-source sidecar 只监视 monitoring，并使用 namespaced 角色。其 ClusterIP service 通过本地端口转发访问。单副本 PVC 示例使用 Recreate，以避免 rollout 期间写入者重叠，因此替换时应规划 UI 停机时间；这不是高可用 Grafana 设计。

Chart 默认跳过 kubelet server 证书验证。此 values 则要求预先准备 monitoring/kubelet-serving-ca ConfigMap，并在 ca.crt 中包含受信任的 kubelet serving CA 证书链，同时证书 SAN 必须与 scrape endpoint 相匹配。请通过节点所有者的证书管理流程验证该信任关系；EKS API server CA 并不会自动成为 kubelet serving CA。如果无法满足此前提条件，请先解决证书配置，再启用采集。不要为了让失败的 target 显示为正常而悄悄将 insecureSkipVerify 恢复为启用状态。此次审计没有测试 kubelet TLS 握手。

此示例会禁用 etcd/controller-manager/scheduler/kube-proxy scrape job，因为设置中没有提供这些组件的直接 endpoint。只有在配置了实际可达且经过授权的 endpoint 后，才启用对应 job；API server 或 CloudWatch 指标是独立来源，无法让缺失的组件 ServiceMonitor target 正常工作。

对于新的自有 release：

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update prometheus-community
helm install monitoring prometheus-community/kube-prometheus-stack \
  --version 92.9.0 --namespace monitoring --create-namespace \
  -f monitoring-values.yaml --wait --timeout 10m
```

Helm 等待结束并不能证明所有由 operator 创建的资源、target 和通知路由均可正常工作。请检查生成的资源、PVC 绑定、Prometheus target 运行状况和指标数据：

```bash
kubectl get pods,svc,pvc -n monitoring
kubectl get prometheus,alertmanager -n monitoring
```

在此命令运行期间，通过 `http://127.0.0.1:3000` 访问 Grafana，并使用已批准 Secret 存储中的凭证：

```bash
kubectl port-forward --address 127.0.0.1 -n monitoring \
  svc/monitoring-grafana 3000:80
```

保护 Grafana 数据库/PVC 和导出的仪表板定义。请使用 Grafana 支持的凭证轮换流程；仅更改引导 Secret 并不能证明现有数据库用户的密码已更改。不要使用共享示例密码公开 UI。

Chart 渲染确认实际的 Prometheus service 为 monitoring-kube-prometheus-prometheus，Grafana service 为 monitoring-grafana，数据源 UID 为 prometheus。自定义 ServiceMonitors/PrometheusRules 必须与此 release 使用的 release=monitoring 选择器匹配。渲染后的清单和 schema 检查是本地证据；此次未在实时集群中操作技术栈、PVC 或登录。

参考资料：[kube-prometheus-stack chart 和升级指南](https://github.com/prometheus-community/helm-charts/tree/kube-prometheus-stack-92.9.0/charts/kube-prometheus-stack)。

#### 关键 Prometheus 指标

指标是否可用取决于实际 scrape target 和权限，而不仅仅是仪表板名称：

- Node exporter 会在受支持的节点上提供节点 CPU、内存、文件系统和网络序列。
- Kubelet/cAdvisor 提供容器资源指标；kube-state-metrics 提供 Kubernetes 对象状态，例如重启次数和就绪状态。
- API server 会公开经过授权的 API 指标。直接获取 etcd/controller-manager/scheduler 指标需要各自可访问的 endpoint；上述设置未启用这些 target。

序列缺失可能表示 exporter 不存在、scrape 失败、平台不受支持或指标已更改，并不自动意味着使用量为零或系统健康。

#### 实用 Grafana 仪表板

从经过审查的 kube-prometheus-stack release 附带的 Kubernetes、node-exporter 和 API-server 仪表板开始，并选择其 prometheus 数据源 UID。仅凭社区仪表板 ID 无法确认其指标/标签约定兼容。检查每个导入仪表板的查询、单位、所需 recording rules 和数据源引用。图表没有数据并不能证明受监控组件运行正常。

先前列出的社区 ID 仍然存在，但部分标题和暗示的用途不准确。目录核验结果如下；未测试导入/运行时兼容性：

| ID | 目录中的实际标题 | 范围说明 |
| --- | --- | --- |
| [15661](https://grafana.com/grafana/dashboards/15661-k8s-dashboard-en-20250125/) | K8S Dashboard | K8S 资源总体概览 |
| [1860](https://grafana.com/grafana/dashboards/1860-node-exporter-full/) | Node Exporter Full | 需要匹配的 node-exporter 序列 |
| [6417](https://grafana.com/grafana/dashboards/6417-kubernetes-cluster-prometheus/) | Kubernetes Cluster (Prometheus) | 集群/容器概览；目录最近一次更新于 2018 年 |
| [12006](https://grafana.com/grafana/dashboards/12006-kubernetes-apiserver/) | Kubernetes apiserver | API-server 延迟/缓存仪表板；目录最近一次更新于 2020 年 |
| [13770](https://grafana.com/grafana/dashboards/13770-1-kubernetes-all-in-one-cluster-monitoring-kr/) | 1 Kubernetes All-in-one Cluster Monitoring KR | 面向韩国用户的一体化仪表板，针对其书籍中的 VM 环境进行了优化 |

#### PromQL 查询示例

这些示例与经过审查的技术栈的 job 和 metrics_path 标签匹配。对于 Pod，请保留 namespace 身份；如果存在 cluster 标签，也应保留，尤其是在共享 AMP workspace 中。向外部发送数据时会附加 Prometheus external labels；它们不会自动出现在每个本地存储的序列上。max 聚合会合并同一已识别对象的重复观测，而不会合并不同工作负载。调整此模式之前，请检查标签。

跨 CPU 平均的节点 CPU 非 idle 百分比：

```promql
100 * (1 - avg by (cluster, instance) (max by (cluster, instance, cpu) (rate(node_cpu_seconds_total{job="node-exporter",mode="idle"}[5m]))))
```

按容器内存工作集字节数排序的前十个 Pods：

```promql
topk(10, sum by (cluster, namespace, pod) (max by (cluster, namespace, pod, container) (container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD"})))
```

每个 Pod UID 当前的重启计数器；这不是 CrashLoopBackOff 检测器：

```promql
sum by (cluster, namespace, pod, uid) (max by (cluster, namespace, pod, uid, container) (kube_pod_container_status_restarts_total{job="kube-state-metrics"}))
```

根文件系统不可用空间百分比，并排除大小为零的文件系统：

```promql
(100 * (1 - max by (cluster, instance, device, mountpoint, fstype) (node_filesystem_avail_bytes{job="node-exporter",mountpoint="/"}) / max by (cluster, instance, device, mountpoint, fstype) (node_filesystem_size_bytes{job="node-exporter",mountpoint="/"}))) and on (cluster, instance, device, mountpoint, fstype) (max by (cluster, instance, device, mountpoint, fstype) (node_filesystem_size_bytes{job="node-exporter",mountpoint="/"}) > 0)
```

这里的 CPU 百分比表示非 idle 时间，内存单位为字节，重启计数器表示当前 Pod/容器生命周期内的计数。查询计数器变化时，请对选定时间窗口使用 rate/increase。文件系统计算使用可用空间，其中可能包含为普通用户预留的空间。这些是用于调查的示例，并非通用告警阈值。

### 使用 AWS X-Ray 进行分布式跟踪

X-Ray 仍是受支持的跟踪后端。其 SDK 和 daemon 自 2026 年 2 月 25 日起进入仅提供安全修复的维护阶段；AWS 当前时间表未公布该阶段的结束日期。对于新的插桩，请使用受支持的 OpenTelemetry/ADOT 集成。X-Ray daemon 或 collector 无需 Kubernetes cluster-admin 权限即可提交跟踪数据，而该 Kubernetes 角色也不会授予 AWS 写入权限。

#### 采集器所有权和前提条件

选择一个插桩/采集所有者。上文的 CloudWatch add-on Application Signals 路径是另一种选择；如果进程已完成插桩，在审查重复 spans 和冲突之前，不要再添加另一个 SDK agent。以下明确示例使用 OpenTelemetry Operator 0.158.0 和 ADOT Collector 0.50.0，并配置仅跟踪数据的管道。

应用 collector 之前，请由相应所有者准备以下依赖项：

- 正常工作的 Operator，以及匹配的 CRD/webhook。上游发布清单使用 cert-manager；请按照其文档中的安装/升级路径操作。EKS ADOT add-on 是另一种所有权路径，并使用特定版本的 schema。Collector release 不包含 Operator 安装清单。
- 专用的 tracing-demo namespace 和 ServiceAccount adot-traces，并为此集群准备 IRSA trust，设置 sub=system:serviceaccount:tracing-demo:adot-traces 和 aud=sts.amazonaws.com。授予所需的 X-Ray 写入操作权限（此管道需要 PutTraceSegments），并提供 STS/X-Ray 连接能力。此 OTLP-only collector 不会发现 Kubernetes 对象，也不需要集群范围的 RBAC。
- Secret tracing-demo/otel-receiver-tls，包含 tls.crt/tls.key，且 server 证书对 adot-traces-collector.tracing-demo.svc 有效。将受信任的 CA 挂载到应用中。证书签发、续订以及 collector 重新加载/重启均由运维负责。
- 强制执行 NetworkPolicy 的 CNI 和经过审查的应用出口访问。此示例允许来自带有 app=my-app 标签的 default Pods 的入口流量；该策略适用于专用 tracing-demo namespace 中的每个 Pod。标签用于选择流量，不会验证工作负载身份，也不能替代对 Pod 创建者的 RBAC 控制。

请审查已发布的 [Operator release](https://github.com/open-telemetry/opentelemetry-operator/releases/tag/v0.158.0) 和 [ADOT release](https://github.com/aws-observability/aws-otel-collector/releases/tag/v0.50.0)，不要将 Collector URL 当作 Operator 清单应用。v1beta1 CRD 使用对象类型的 spec.config。更改示例 Region 时，请同时更改 env/exporter 字段：

```yaml
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: adot-traces
  namespace: tracing-demo
spec:
  mode: deployment
  replicas: 1
  image: public.ecr.aws/aws-observability/aws-otel-collector:v0.50.0
  serviceAccount: adot-traces
  env:
  - name: AWS_REGION
    value: us-west-2
  - name: AWS_EC2_METADATA_DISABLED
    value: "true"
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: "1"
      memory: 512Mi
  volumes:
  - name: receiver-tls
    secret:
      secretName: otel-receiver-tls
  volumeMounts:
  - name: receiver-tls
    mountPath: /etc/otel/tls
    readOnly: true
  config:
    receivers:
      otlp:
        protocols:
          http:
            endpoint: 0.0.0.0:4318
            tls:
              cert_file: /etc/otel/tls/tls.crt
              key_file: /etc/otel/tls/tls.key
    processors:
      memory_limiter:
        check_interval: 1s
        limit_percentage: 75
        spike_limit_percentage: 15
      batch: {}
    exporters:
      awsxray:
        region: us-west-2
        local_mode: true
        no_verify_ssl: false
        index_all_attributes: false
        telemetry:
          enabled: false
    extensions:
      health_check:
        endpoint: 0.0.0.0:13133
    service:
      extensions: [health_check]
      pipelines:
        traces:
          receivers: [otlp]
          processors: [memory_limiter, batch]
          exporters: [awsxray]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tracing-ingress
  namespace: tracing-demo
spec:
  podSelector: {}
  policyTypes: [Ingress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: default
      podSelector:
        matchLabels:
          app: my-app
    ports:
    - protocol: TCP
      port: 4318
```

Operator 会根据 OTLP/HTTP 端口生成 ClusterIP receiver Service：tracing-demo 中的 adot-traces-collector，使用 TCP 4318。receiver 不会验证用户身份或业务授权声明；此示例使用 server TLS 和所选网络边界。若需要更强隔离，可以要求 mTLS 或受支持的 receiver authenticator。扩大访问范围之前，请在两端一致地配置这些功能。

Collector 接收数据并不代表数据已存储。请检查生成的 Deployment/Service、TLS 握手、AWS 凭证选择、exporter 故障，以及 X-Ray 中的已知跟踪记录。此单副本、内存中的示例并非无损或高可用管道；请针对工作负载对缓冲、背压、重试行为和故障处理进行容量规划和测试。CRD schema 检查无法验证所有组件配置，也不能证明 collector 能够启动。

#### 对应用进行插桩并传播上下文

对于 Python 3.10 及更高版本的应用，请在应用依赖锁定文件中保持 opentelemetry-sdk==1.44.0 和 opentelemetry-exporter-otlp-proto-http==1.44.0 版本一致。分别配置每项服务；共享 collector 不应使用一个全局值覆盖所有传入的 service.name。HTTP exporter endpoint 包含 /v1/traces；使用 4317 的 gRPC endpoint 属于不同协议/配置。

```bash
export OTEL_SERVICE_NAME=my-app
export CLUSTER_NAME=my-owned-cluster
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://adot-traces-collector.tracing-demo.svc:4318/v1/traces
export OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE=/etc/otel/ca.crt
```

CA 文件必须挂载到应用容器中。在应用启动时创建一个 RequestTracing 实例，在真实 server handler 中调用 handle_request，传入经过规范化的入站标头名称，以及一个使用所提供出站标头的操作；优雅关机时调用 close。框架/客户端自动插桩也可以处理这些边界；避免对同一操作进行重复插桩：

```python
import os
from urllib.parse import urlsplit

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.trace import SpanKind
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


class RequestTracing:
    def __init__(self):
        endpoint = os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"]
        parsed = urlsplit(endpoint)
        if parsed.scheme != "https" or parsed.path != "/v1/traces":
            raise ValueError("Set the HTTPS OTLP/HTTP traces endpoint including /v1/traces")
        self.provider = TracerProvider(
            resource=Resource.create({
                "service.name": os.environ["OTEL_SERVICE_NAME"],
                "k8s.cluster.name": os.environ["CLUSTER_NAME"],
            }),
            sampler=ParentBased(TraceIdRatioBased(0.1)),
        )
        exporter = OTLPSpanExporter(
            endpoint=endpoint,
            certificate_file=os.environ["OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE"],
            timeout=10,
        )
        self.provider.add_span_processor(BatchSpanProcessor(exporter))
        self.tracer = self.provider.get_tracer("example.request-handler")
        self.propagator = TraceContextTextMapPropagator()

    def handle_request(self, incoming_headers, operation):
        parent = self.propagator.extract(incoming_headers)
        with self.tracer.start_as_current_span("request", context=parent, kind=SpanKind.SERVER):
            outgoing_headers = {}
            self.propagator.inject(outgoing_headers)
            return operation(outgoing_headers)

    def close(self):
        self.provider.shutdown()
```

此适配器展示 W3C tracecontext 传播和一个 server span；它没有实现 HTTP server 或所有 client spans。使用 X-Amzn-Trace-Id 的 AWS edge 集成需要采用受支持的 propagator/bridge，不能假定仅支持 W3C 的提取器会读取该标头。对于新的根 trace，10% 的头部采样是示例值，并会保留父级决策；但不能保证之后的每个错误或慢请求都会保留。尾部采样需要单独设计，确保同一条 trace 的所有 spans 都路由到一起，并有足够的缓冲空间。

#### Trace map 和调查

在账户可用的 X-Ray/CloudWatch 跟踪视图中检查 trace map、延迟分布和错误/故障详情。map 反映的是已插桩、已采样并成功传输的 spans；缺少边并不能证明服务之间从不通信。请将 trace ID 与适当保留的日志和指标关联，同时排除凭证、个人数据和不受限制的请求属性。

此次审计仅验证了已发布的 API/schema 和合成的本地行为，并不表示 collector 已部署、插桩已实时运行、跟踪数据已导出或生产容量已测试。参考资料：[X-Ray 维护时间表](https://aws.amazon.com/blogs/mt/aws-x-ray-sdks-daemon-migration-to-opentelemetry/)、[EKS ADOT 所有权](https://docs.aws.amazon.com/eks/latest/userguide/opentelemetry.html)、[AWS X-Ray exporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.158.0/exporter/awsxrayexporter)。

### Kubernetes Dashboard

[Kubernetes Dashboard 项目](https://github.com/kubernetes-retired/dashboard)已归档，不再维护。其维护者建议当前 UI 需求使用 Kubernetes SIG UI 下的 Headlamp。不应再使用旧版 Dashboard v2.7 的原始清单和 cluster-admin-token 配方作为当前安装方式。

请选择仍在维护的 UI，并审查其实际身份验证、TLS、授权和升级要求。使用预期的 IAM/RBAC 身份和 namespace 范围，并遵循安全章节中的 access-entry/RBAC 示例。UI 默认用户不需要不受限制的 cluster-admin ServiceAccount；公开管理员 bearer token 不能替代访问设计。

### 自定义指标和监控

可以针对应用专属指标实施自定义采集与监控方案：

#### 集成 Prometheus 客户端库

对于 Prometheus Java client 1.8.0 API，请使用当前的 io.prometheus.metrics 软件包和版本一致的依赖项。在现有 Gradle Java 项目中：

```groovy
dependencies {
    implementation(platform("io.prometheus:prometheus-metrics-bom:1.8.0"))
    implementation("io.prometheus:prometheus-metrics-core")
    implementation("io.prometheus:prometheus-metrics-exporter-httpserver")
}
```

将示例保存为 App.java。main 方法会在端口 9400 上公开指标并等待；应用的真实请求 handler 必须调用 processRequest，并传入其操作。仅启动指标 endpoint 并不代表业务请求数量。此处没有将合成请求计数作为测得的流量呈现：

```java
import io.prometheus.metrics.core.metrics.Counter;
import io.prometheus.metrics.core.metrics.Histogram;
import io.prometheus.metrics.exporter.httpserver.HTTPServer;
import java.io.IOException;

public class App {
    private static final Counter requests = Counter.builder()
        .name("app_requests_total").help("Requests processed by this application.")
        .register();
    private static final Histogram latency = Histogram.builder()
        .name("app_request_latency_seconds").help("Request processing time in seconds.")
        .register();

    public static void processRequest(Runnable operation) {
        requests.inc();
        long started = System.nanoTime();
        try {
            operation.run();
        } finally {
            latency.observe((System.nanoTime() - started) / 1_000_000_000.0);
        }
    }

    public static void main(String[] args) throws IOException, InterruptedException {
        HTTPServer server = HTTPServer.builder().port(9400).buildAndStart();
        Runtime.getRuntime().addShutdownHook(new Thread(server::close));
        Thread.currentThread().join();
    }
}
```

已根据已发布的客户端检查源 API 和依赖坐标；此次审计环境中没有 Java 编译器/运行时，因此未编译或执行此示例。部署前，请将其集成到应用构建、生命周期和请求路径中。请限制标签取值；请求 ID、用户 ID 和原始 URL 不适合作为默认指标维度。

#### 收集自定义指标

假设自有应用 Pods 位于 default，带有 app=my-app 标签，并且确实在 TCP 9400 上提供 /metrics。Service 通过选择器选择 Pods；ServiceMonitor 通过 Service 标签和命名端口选择 Service。release=monitoring 标签和 namespaceSelector 将其连接到上述技术栈：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app-metrics
  namespace: default
  labels:
    app: my-app
spec:
  type: ClusterIP
  selector:
    app: my-app
  ports:
  - name: metrics
    port: 9400
    targetPort: 9400
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: app-monitor
  namespace: monitoring
  labels:
    release: monitoring
spec:
  namespaceSelector:
    matchNames:
    - default
  selector:
    matchLabels:
      app: my-app
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
```

请验证 Service 的 EndpointSlices 和 Prometheus target 状态，并根据适用的网络策略/安全控制，仅允许预期的采集器访问。此集群内 HTTP 指标示例需要经过审查的网络边界；如果指标 endpoint 需要 TLS/身份验证，请进行配置。ServiceMonitor 不会对应用进行插桩，也不会创建缺失的指标服务器。

参考资料：[Java 客户端快速入门](https://prometheus.github.io/client_java/getting-started/quickstart/)、[Prometheus 配置](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)。

#### 自定义仪表板

在 Grafana 中创建自定义仪表板以可视化应用指标：

1. 登录 Grafana
2. 点击“+”图标并选择“Dashboard”
3. 点击“Add panel”
4. 选择“Prometheus”作为数据源
5. 编写 PromQL 查询（例如 `rate(app_requests_total[5m])`）
6. 配置面板标题、描述和可视化类型
7. 点击“Save”
## 告警与事件管理

有效的告警与事件管理对于快速检测并响应 EKS 集群中的问题至关重要。本节介绍管理 EKS 集群告警和事件的各种工具和技术。

![Architecture diagram showing CloudWatch metrics and logs, AWS events, Prometheus metrics and Loki logs, and Kubernetes and application events routed through CloudWatch Alarms, EventBridge, Prometheus Alertmanager, and an event router to SNS (Email and SQS subscriptions), Lambda, Slack and PagerDuty, and OpsGenie.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-3.html)

### CloudWatch Alarms

创建告警之前，请确认近期数据点以及准确的指标 namespace、名称和维度集合。这些示例使用文档规定的仅带 ClusterName 的 ContainerInsights 节点汇总指标和 Maximum。这有助于发现节点热点，但并不是整个集群按容量加权的利用率指标。请使用节点专属维度确定受影响的节点。

80/80/85% 阈值以及两个五分钟评估周期都是说明性的策略选择。两个周期中 Maximum 超过阈值，并不表示十分钟内每一秒都持续饱和。缺失数据仍然是缺失数据，并不能证明利用率正常。重复使用告警名称之前，请检查现有告警定义，因为 PutMetricAlarm 会更新现有告警。通知权限、订阅和传递测试是独立的前提条件。

#### 节点 CPU

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set the metric Region}"
: "${ALARM_PREFIX:?Set a reviewed alarm-name prefix owned by this workflow}"
: "${SNS_TOPIC_ARN:?Set the approved notification topic ARN}"
aws cloudwatch put-metric-alarm --region "$AWS_REGION" \
  --alarm-name "${ALARM_PREFIX}-node-cpu" \
  --alarm-description "Example: maximum reported node cpu utilization exceeds 80 percent" \
  --metric-name node_cpu_utilization --namespace ContainerInsights \
  --statistic Maximum --period 300 --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions "Name=ClusterName,Value=$CLUSTER_NAME" \
  --evaluation-periods 2 --datapoints-to-alarm 2 --treat-missing-data missing \
  --alarm-actions "$SNS_TOPIC_ARN"
```

#### 节点内存

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set the metric Region}"
: "${ALARM_PREFIX:?Set a reviewed alarm-name prefix owned by this workflow}"
: "${SNS_TOPIC_ARN:?Set the approved notification topic ARN}"
aws cloudwatch put-metric-alarm --region "$AWS_REGION" \
  --alarm-name "${ALARM_PREFIX}-node-memory" \
  --alarm-description "Example: maximum reported node memory utilization exceeds 80 percent" \
  --metric-name node_memory_utilization --namespace ContainerInsights \
  --statistic Maximum --period 300 --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions "Name=ClusterName,Value=$CLUSTER_NAME" \
  --evaluation-periods 2 --datapoints-to-alarm 2 --treat-missing-data missing \
  --alarm-actions "$SNS_TOPIC_ARN"
```

#### 节点文件系统

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set the metric Region}"
: "${ALARM_PREFIX:?Set a reviewed alarm-name prefix owned by this workflow}"
: "${SNS_TOPIC_ARN:?Set the approved notification topic ARN}"
aws cloudwatch put-metric-alarm --region "$AWS_REGION" \
  --alarm-name "${ALARM_PREFIX}-node-disk" \
  --alarm-description "Example: maximum reported node disk utilization exceeds 85 percent" \
  --metric-name node_filesystem_utilization --namespace ContainerInsights \
  --statistic Maximum --period 300 --threshold 85 \
  --comparison-operator GreaterThanThreshold \
  --dimensions "Name=ClusterName,Value=$CLUSTER_NAME" \
  --evaluation-periods 2 --datapoints-to-alarm 2 --treat-missing-data missing \
  --alarm-actions "$SNS_TOPIC_ARN"
```

这些告警命令未在 AWS 上执行。参考资料：[Container Insights 指标和维度](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)。

### Prometheus Alertmanager

Prometheus 负责评估告警规则；Alertmanager 负责对生成的告警进行分组、去重和路由。Operator 管理的 Alertmanager 不会自动使用任意名称的 ConfigMap。经过审查的技术栈使用 Alertmanager 0.34.0；请明确连接其配置和凭证文件。

#### Alertmanager 配置

对于 Slack 示例，请通过已批准的 Secret 管理流程准备 monitoring/notification-credentials，其中 slack-url 键包含真实 webhook URL。请勿将凭证放入 ConfigMap、仓库文本或 Helm 命令参数。将以下非机密路由定义保存为 alertmanager-config.yaml：

```yaml
global:
  resolve_timeout: 5m
route:
  group_by: [cluster, namespace, alertname]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: slack-notifications
  routes:
  - matchers:
    - alertname="Watchdog"
    receiver: discard
receivers:
- name: discard
- name: slack-notifications
  slack_configs:
  - api_url_file: /etc/alertmanager/secrets/notification-credentials/slack-url
    channel: "#eks-alerts"
    send_resolved: true
    title: '[{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}'
    text: '{{ range .Alerts }}{{ .Annotations.summary }} — {{ .Annotations.description }}{{ "\n" }}{{ end }}'
```

Webhook 必须已获准向预期 Slack 目标发送消息；channel 字段不会覆盖 Slack 应用权限。此示例会丢弃始终触发的 Watchdog 告警，以免定期向 Slack 发送消息。真实的 dead-man/heartbeat 监控需要单独配置 receiver 并通过外部系统检测缺失；丢弃 Watchdog 并不能测试告警传递。

使用匹配版本的 amtool 在本地验证文件，然后仅为新的自有安装创建配置 Secret。现有 Secret/release 需要遵循其所有者经过审查的更新流程：

```bash
amtool --no-version-check check-config alertmanager-config.yaml
kubectl create secret generic alertmanager-routing -n monitoring \
  --from-file=alertmanager.yaml=alertmanager-config.yaml
```

将以下内容保存为 alertmanager-values.yaml，并与 monitoring release 的所有已审查 values 合并。configSecret 用于选择 Secret，Operator 需要其中的 alertmanager.yaml 键；secrets 会将 notification-credentials 挂载到 /etc/alertmanager/secrets/notification-credentials。部署前请检查 monitoring 中由 release=monitoring 选择的其他 AlertmanagerConfig 资源：

```yaml
alertmanager:
  alertmanagerSpec:
    useExistingSecret: true
    configSecret: alertmanager-routing
    secrets:
    - notification-credentials
    alertmanagerConfigSelector:
      matchLabels:
        release: monitoring
    alertmanagerConfigNamespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: monitoring
```

请检查生成的配置/重新加载状态和通知故障，并在依赖寻呼功能之前，通过已批准的测试目标发送带标签的测试告警。本地解析和路由测试无法证明 Secret 可用、webhook 权限有效、SMTP 可连接或消息已实际送达。此单副本 chart 示例还需要单独设计可用性方案。

#### 配置告警规则

rule release 标签与 Prometheus 选择器匹配。请检查是否有等效的内置规则，以避免重复告警。CrashLoopBackOff 是 Kubernetes 等待原因；仅凭重启速率阈值无法确定该条件。以下示例需要所示 kube-state-metrics 序列，并使用 namespace/Pod UID/container 或 node 身份：

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: kubernetes-alerts
  namespace: monitoring
  labels:
    release: monitoring
spec:
  groups:
  - name: kubernetes-example
    rules:
    - alert: KubernetesPodCrashLooping
      expr: max by (cluster, namespace, pod, uid, container) (max_over_time(kube_pod_container_status_waiting_reason{job="kube-state-metrics",reason="CrashLoopBackOff"}[5m])) >= 1
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "CrashLoopBackOff observed for {{ $labels.namespace }}/{{ $labels.pod }}"
        description: "Inspect container {{ $labels.container }} logs and events; the rule tracks recent waiting reasons, not a restart-count guarantee."
    - alert: KubernetesNodeMemoryPressure
      expr: max by (cluster, node) (kube_node_status_condition{job="kube-state-metrics",condition="MemoryPressure",status="true"}) == 1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Node {{ $labels.node }} reports MemoryPressure"
        description: "Inspect node capacity and workloads; the observed condition has matched for five minutes."
    - alert: KubernetesNodeDiskPressure
      expr: max by (cluster, node) (kube_node_status_condition{job="kube-state-metrics",condition="DiskPressure",status="true"}) == 1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Node {{ $labels.node }} reports DiskPressure"
        description: "Inspect disk space and inodes; the observed condition has matched for five minutes."
```

CrashLoopBackOff 规则会检查最近多个五分钟窗口内是否反复出现该状态；它不是重启次数统计。节点压力是观测到的 kubelet 条件，与一般利用率百分比不同。缺失/陈旧序列可能导致告警不触发，因此请单独监控 scrape 健康状况和指标可用性。阈值和持续时间只是示例，并非事件响应保证。

### EventBridge 事件规则

使用事件发送服务发布的事件名称和载荷字段。EKS 直接事件目录包含 add-on 创建/更新/删除结果、add-on 运行状况下降/恢复事件和 Fargate 计划终止事件。目录并未发布旧示例中的通用 EKS Cluster State Change 或 EKS Node Group State Change 名称。通过 CloudTrail 传递的 EKS API 活动使用不同的 detail-type 和载荷。

#### 直接 add-on 运行状况事件和 CloudTrail API 活动

以下命令会写入两个针对所选账户和 Region 的备选模式。这些模式覆盖该账户/Region 中匹配的活动，并非仅针对一个集群。若要进一步缩小范围，请检查该特定事件类型的捕获事件并测试其文档字段；不要假设每个事件都包含 detail.clusterName。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the owned Region}"
: "${ACCOUNT_ID:?Set the owned 12-digit AWS account ID}"
python3 - "$AWS_REGION" "$ACCOUNT_ID" <<'PY'
import json
import re
import sys
region, account = sys.argv[1:]
if not re.fullmatch(r"[0-9]{12}", account):
    raise SystemExit("ACCOUNT_ID must contain 12 digits")
base = {"source": ["aws.eks"], "account": [account], "region": [region]}
patterns = {
    "eks-addon-health-pattern.json": dict(base, **{
        "detail-type": ["EKS Addon Health Degraded", "EKS Addon Health Restored"],
    }),
    "eks-update-api-pattern.json": dict(base, **{
        "detail-type": ["AWS API Call via CloudTrail"],
        "detail": {
            "eventSource": ["eks.amazonaws.com"],
            "eventName": ["UpdateClusterVersion", "UpdateNodegroupVersion"],
        },
    }),
}
for filename, pattern in patterns.items():
    with open(filename, "w") as stream:
        json.dump(pattern, stream, indent=2)
        stream.write("\n")
PY
```

CloudTrail 模式匹配 UpdateClusterVersion 和 UpdateNodegroupVersion API 事件，包括适用的升级/回滚请求。API 调用事件记录的是尝试或已接受的请求，而非异步更新的完成情况。请检查错误字段，并将成功请求与更新 ID 和 DescribeUpdate 状态关联起来。确保已配置相关 CloudTrail 管理事件的传递。直接传递和 CloudTrail 衍生传递都尽力而为，因此还应使用服务状态检查和故障监控。

#### 接入自有 SNS 目标

在同一账户/Region 中准备标准 SNS topic、已确认的订阅和 EventBridge target 执行角色。该角色必须信任 EventBridge，并允许 sns:Publish 到目标 topic；如果启用了加密，还需相应的 KMS 权限。操作员需要相应的规则/target 权限，以及传递已批准角色的权限。目前 EventBridge 支持 SNS target 的执行角色；资源型策略是另一种选择，而不会因为添加 target 就自动生成。

选择一个已生成的模式文件和一个新的自有规则名称。预检查会拒绝已经存在的名称，但 PutRule 是 upsert 操作，因此请协调资源所有权和并发变更。规则会以禁用状态创建；如果 PutTargets 部分失败，工作流会停止：

```bash
set -euo pipefail
: "${AWS_REGION:?Set the reviewed Region}"
: "${ACCOUNT_ID:?Set the reviewed account ID}"
: "${RULE_NAME:?Set a new owned rule name}"
: "${PATTERN_FILE:?Select one reviewed pattern JSON file}"
: "${SNS_TOPIC_ARN:?Set the prepared standard SNS topic ARN}"
: "${EVENTBRIDGE_ROLE_ARN:?Set the prepared EventBridge target execution role ARN}"
python3 - "$AWS_REGION" "$ACCOUNT_ID" "$RULE_NAME" "$PATTERN_FILE" \
  "$SNS_TOPIC_ARN" "$EVENTBRIDGE_ROLE_ARN" <<'PY'
import json
import re
import sys
region, account, name, path, topic, role = sys.argv[1:]
if not re.fullmatch(r"[0-9]{12}", account) or not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", name):
    raise SystemExit("Review the account ID and rule name")
with open(path) as stream:
    pattern = json.load(stream)
if pattern.get("account") != [account] or pattern.get("region") != [region] or pattern.get("source") != ["aws.eks"]:
    raise SystemExit("Pattern scope differs from the selected account/Region/service")
t, r = topic.split(":", 5), role.split(":", 5)
if (len(t) != 6 or len(r) != 6 or t[0] != "arn" or r[0] != "arn"
        or t[1] != r[1] or t[2:5] != ["sns", region, account]
        or r[2:5] != ["iam", "", account] or not r[5].startswith("role/")
        or not t[5] or t[5].endswith(".fifo")):
    raise SystemExit("Use the reviewed same-account standard topic and target role")
with open("eks-event-targets.json", "w") as stream:
    json.dump([{"Id": "ops-sns", "Arn": topic, "RoleArn": role}], stream)
PY
EXISTING=$(aws events list-rules --region "$AWS_REGION" --event-bus-name default \
  --name-prefix "$RULE_NAME" --query 'Rules[].Name' --output json)
python3 - "$RULE_NAME" "$EXISTING" <<'PY'
import json
import sys
if sys.argv[1] in json.loads(sys.argv[2]):
    raise SystemExit("Rule already exists; use its owner's reviewed update procedure")
PY
aws events put-rule --region "$AWS_REGION" --event-bus-name default \
  --name "$RULE_NAME" --state DISABLED --event-pattern "file://$PATTERN_FILE"
aws events put-targets --region "$AWS_REGION" --event-bus-name default \
  --rule "$RULE_NAME" --targets file://eks-event-targets.json \
  --output json > eks-event-targets-result.json
python3 - <<'PY'
import json
with open("eks-event-targets-result.json") as stream:
    result = json.load(stream)
if result["FailedEntryCount"] != 0:
    raise SystemExit("Target configuration failed; inspect FailedEntries before retrying")
print("Rule remains DISABLED; review the target and pattern before enabling")
PY
```

审查完整的 target 响应、角色、订阅、传递重试/死信策略和代表性的捕获事件。可以使用 TestEventPattern 检查模式匹配；但该操作不会测试 target 权限或消息传递。完成审查后再启用：

```bash
aws events enable-rule --region "$AWS_REGION" --event-bus-name default --name "$RULE_NAME"
```

启用后请监控匹配/失败调用，并验证已批准的端到端事件。规则、target 或成功的 API 响应本身都不能保证告警已送达。此次审计未创建 EventBridge/SNS 资源、事件或通知。

参考资料：[EKS EventBridge 事件目录](https://docs.aws.amazon.com/eventbridge/latest/ref/events-ref-eks.html)、[target 权限](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html)。

### Kubernetes 事件监控

Kubernetes Events 有助于调查调度、镜像拉取、重启和其他对象活动。它们是短期、尽力而为的观测结果，并且可能聚合重复发生的事件；它们并不是完整、持久的审计记录。请先检查目标 namespace：

```bash
kubectl events -n default --types=Warning
kubectl events -n default --types=Warning --watch
```

#### 采集器版本和所有权

最初的 Opsgenie exporter 已无人维护。其活跃分支已从 resmoio 转移到 mustafaakin/kubernetes-event-exporter。此处检查到的最新已发布版本是 2024 年 2 月的 v1.7，尽管仓库中还有较新的开发活动。仓库仍然活跃或最新标签较旧，并不能证明生产镜像已打上当前补丁。

以下参考配置已根据 v1.7 配置/监听器源码进行检查。它需要由自有构建流程审查并打补丁的镜像，并且该镜像必须保留此配置/CLI 约定、以 UID 65532 运行，并能在只读根文件系统中读取挂载的配置。渲染时请设置不可变 digest；本文未提供公共 latest 镜像或臆造的 digest。此次审计未执行镜像构建、漏洞审查或运行时兼容性测试。

#### Namespace 范围、RBAC 和配置

此示例在现有 monitoring namespace 中运行，但只监视 default 中的 core/v1 Events。omitLookup=true 会禁用用于丰富涉及对象标签/注解的单独 GET 请求，因此 Role 只授予对 default 中 event 的读取权限，而不是对 Secret 的通配读取权限或对所有 API 资源的读取权限。单副本不启用 leader election，因此不授予 lease 写入权限。调整范围时，应使 namespace、Role 和 RoleBinding 保持一致。

将以下内容保存为 event-exporter-template.yaml。它包含一个镜像标记，使用前必须先渲染。匹配规则指向一个命名 receiver；该 receiver 会将 JSON 输出到 stdout，现有自有容器日志管道可以采集这些内容。此配置仅导出 Warning 事件：

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: event-exporter
  namespace: monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: event-exporter-read
  namespace: default
rules:
- apiGroups: [""]
  resources: [events]
  verbs: [get, list, watch]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: event-exporter-read
  namespace: default
subjects:
- kind: ServiceAccount
  name: event-exporter
  namespace: monitoring
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: event-exporter-read
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: event-exporter-config
  namespace: monitoring
data:
  config.yaml: |
    logLevel: warn
    logFormat: json
    namespace: default
    omitLookup: true
    maxEventAgeSeconds: 60
    metricsNamePrefix: event_exporter_
    leaderElection:
      enabled: false
    route:
      routes:
      - match:
        - type: Warning
          receiver: event-log
    receivers:
    - name: event-log
      stdout:
        deDot: false
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: event-exporter
  namespace: monitoring
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: event-exporter
  template:
    metadata:
      labels:
        app: event-exporter
    spec:
      serviceAccountName: event-exporter
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: event-exporter
        image: REVIEWED_EVENT_EXPORTER_IMAGE
        args:
        - -conf=/etc/event-exporter/config.yaml
        - -metrics-address=127.0.0.1:2112
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 250m
            memory: 128Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: [ALL]
        volumeMounts:
        - name: config
          mountPath: /etc/event-exporter
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: event-exporter-config
```

渲染需要 Python 3 和 PyYAML。先检查现有 event-exporter 资源及其所有者；对于现有安装，请遵循所有者的升级流程：

```bash
set -euo pipefail
: "${EVENT_EXPORTER_IMAGE:?Set the reviewed, patched image reference including @sha256 digest}"
python3 - "$EVENT_EXPORTER_IMAGE" <<'PY'
import re
import sys
import yaml
image = sys.argv[1]
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[a-f0-9]{64}", image):
    raise SystemExit("Use a reviewed image pinned by SHA256 digest")
with open("event-exporter-template.yaml") as stream:
    objects = list(yaml.safe_load_all(stream))
deployment = next(obj for obj in objects if obj["kind"] == "Deployment")
container = deployment["spec"]["template"]["spec"]["containers"][0]
if container["image"] != "REVIEWED_EVENT_EXPORTER_IMAGE":
    raise SystemExit("Review the template before replacing its image")
container["image"] = image
with open("event-exporter-rendered.yaml", "w") as stream:
    yaml.safe_dump_all(objects, stream, sort_keys=False)
PY
```

对于新的自有安装，请先审查渲染后的清单、镜像拉取身份和 API 连接能力，再应用清单。Recreate 可避免 rollout 期间副本重叠，但会导致停机；这不是高可用采集器：

```bash
kubectl apply -f event-exporter-rendered.yaml
kubectl rollout status deployment/event-exporter -n monitoring --timeout=120s
kubectl logs -n monitoring deployment/event-exporter --tail=100
```

#### 丢失、重复事件和告警载荷

经检查的 v1.7 watcher 会处理添加通知，并忽略更新/删除回调。因此，重复 Event 的计数/系列更新不能作为可靠的导出发生次数计数器。maxEventAgeSeconds=60 是示例接纳截止时间，并非后端保留期：在启动、限流或停机期间，较旧事件可能会被丢弃。重新列出事件/重启也可能导致观测重复。在使用事件计数做运维决策之前，请选择并测试所需的更新处理、缓冲和持久化目标。

请同时检查 watch/discard 计数器和日志。此示例将 exporter 的指标监听器绑定到 loopback；经过授权的操作员可通过本地端口转发检查它。此配置不会自动将 endpoint 添加到 Prometheus：

```bash
kubectl port-forward --address 127.0.0.1 -n monitoring \
  deployment/event-exporter 2112:2112
```

端口转发期间，请读取 `http://127.0.0.1:2112/metrics` 上的 /metrics。rollout 或 stdout 记录本身并不能确认 CloudWatch/OpenSearch 已存储数据；请验证现有日志采集器和目标位置。事件消息可能包含敏感运维详情，请审查访问权限、筛选规则和保留期。

不要仅通过更改 webhook URL，就将原始 Kubernetes Event 对象发送到 Alertmanager。Alertmanager 当前的 /api/v2/alerts endpoint 需要符合其告警数组 schema 的内容；旧版 /api/v1/alerts 路径不是当前 API。应通过专门的适配器转换身份、标签、注解和解决语义。上面的 stdout/日志路径并未声称实现了该适配器。

参考资料：[维护中的 exporter 仓库](https://github.com/mustafaakin/kubernetes-event-exporter)、[v1.7 watcher](https://github.com/mustafaakin/kubernetes-event-exporter/blob/v1.7/pkg/kube/watcher.go)、[Alertmanager v2 API](https://github.com/prometheus/alertmanager/blob/v0.34.0/api/v2/openapi.yaml)。

### 通知渠道集成

请使用实际 Alertmanager 版本支持的 receiver。以下片段是 alertmanager-config.yaml 中 receivers 下的条目，并非 Kubernetes 资源。若要选择其中一项，请添加对应 receiver，并将 route.receiver 或匹配的子路由改为其准确名称，然后验证完整配置并更新所选 Secret。仅添加未使用的 receiver 条目不会路由任何告警。

#### Slack 集成

上面已接线的 Slack 示例使用挂载的 webhook 文件。请确认允许的 channel；在审查敏感数据之前，不要发布完整告警标签/注解。不要将真实 Slack token 或 webhook 放入已提交到仓库的 Provider/ConfigMap 示例。

#### PagerDuty 集成

对于 Events API v2 集成，请在 notification-credentials 中准备 pagerduty-routing-key 键。routing_key_file 指的是该集成密钥，而不是通用 PagerDuty REST API token。如果只应对 critical 告警发起寻呼，请通过经过审查的子路由将这些告警连接起来：

```yaml
name: pagerduty-notifications
pagerduty_configs:
- routing_key_file: /etc/alertmanager/secrets/notification-credentials/pagerduty-routing-key
  send_resolved: true
  severity: '{{ if eq .CommonLabels.severity "critical" }}critical{{ else }}warning{{ end }}'
  description: '{{ .CommonLabels.alertname }}'
```

#### 电子邮件集成

将保留的示例 SMTP 主机/地址/用户替换为已批准的邮件服务设置，并在同一个凭证 Secret 中准备 smtp-password。请保持 TLS 为必需，并验证服务器信任、发件人授权和邮件传递情况。这是 Alertmanager email receiver，而不是 Flux Provider：

```yaml
name: email-notifications
email_configs:
- to: oncall@example.com
  from: alerts@example.com
  smarthost: smtp.example.com:587
  auth_username: alerting-user
  auth_password_file: /etc/alertmanager/secrets/notification-credentials/smtp-password
  require_tls: true
  send_resolved: true
```

#### 原生 Amazon SNS 集成

Alertmanager 0.34.0 具有原生 SNS receiver；该路径不需要未定义的 sns-forwarder webhook service。请将示例 Region/账户/topic 替换为自有标准 topic。为实际 Alertmanager ServiceAccount 配置受支持的 AWS 身份，使其具有该 topic 的 sns:Publish 权限；如果 topic 已加密，还需要适用的 KMS 权限和网络连接能力。Prometheus 或应用角色不会自动成为 Alertmanager 角色。此处未嵌入静态 AWS 访问密钥：

```yaml
name: sns-notifications
sns_configs:
- sigv4:
    region: us-west-2
  topic_arn: arn:aws:sns:us-west-2:123456789012:eks-alerts
  send_resolved: true
  subject: 'EKS {{ .CommonLabels.alertname }}'
```

请分别确认 topic 订阅和目标策略，并测试消息传递。FIFO topic 还涉及其他去重/分组注意事项；此片段针对标准 topic。receiver 解析不会执行 IAM 操作，也不会发布到 SNS。

Flux notification Providers 会将 Flux reconciliation 事件与 Flux Alert 资源及选定事件源一起路由。仅仅因为 Provider 存在，并不意味着它会接收任意 Prometheus 告警或 Kubernetes Events。请将该工作流与此处所示的 Alertmanager receiver 配置分开管理。

参考资料：[Alertmanager 配置和 receivers](https://prometheus.io/docs/alerting/latest/configuration/)。

### 告警管理和升级

实施有效管理和升级告警的策略：

#### 告警严重级别

将告警分为以下严重级别：

- **严重**：需要立即处理的重大问题
- **警告**：需要关注但不需要立即处理的问题
- **信息**：信息性告警

#### 告警升级策略

使用 PagerDuty 等工具实施告警升级策略：

1. **首次响应**：通知值班工程师
2. **升级 1**：15 分钟后仍未响应则通知备用工程师
3. **升级 2**：30 分钟后仍未响应则通知团队负责人
4. **升级 3**：45 分钟后仍未响应则通知经理

#### 减少告警疲劳

实施以下策略以减少告警疲劳：

1. **告警分组**：将相关告警分组，以减少重复通知
2. **告警筛选**：仅传递重要告警
3. **告警限流**：限制重复告警的频率
4. **告警时间窗口**：仅在工作时间传递非业务关键告警
## 日志分析与可视化

日志分析与可视化对于诊断和解决 EKS 集群中出现的问题十分重要。本节介绍在 EKS 集群中分析和可视化日志的各种工具和技术。

![Architecture diagram of the log analysis and visualization pipeline: control plane and AWS service logs go directly to CloudWatch Logs, container and application logs pass through log collectors (Fluent Bit, Fluentd, Vector, CloudWatch Agent) into four stores (CloudWatch Logs, Amazon OpenSearch, Amazon S3, Grafana Loki), and each store feeds its paired analysis and visualization tool: CloudWatch Logs Insights, OpenSearch Dashboards, Athena with QuickSight, and Grafana Explore with dashboards.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-4.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-4.html)

### CloudWatch Logs Insights

查询之前，请选择实际的日志组和有限的时间窗口。容器、API/audit 和 authenticator 流具有不同的 schema。对于上文的独立 Fluent Bit values，解析后的应用 JSON 位于 data 下，Kubernetes 元数据位于 kubernetes 下，且原始 log 字段会保留。其他采集器/配置可能使用不同的字段路径；请先检查已存储的事件。

#### 容器日志查询

对于包含字符串 level 字段的结构化应用记录：

```
fields @timestamp, @log, kubernetes.pod_name, data.level, data.message, log
| filter kubernetes.namespace_name = "default"
| filter kubernetes.container_name = "app"
| filter toupper(data.level) = "ERROR"
| sort @timestamp desc
| limit 20
```

纯文本或 JSON 解析失败的记录不会有 data.level。请单独检查其 log 字段，而不要将空结果解释为“没有错误”。

#### 审计日志中的 API 错误响应

启用审计日志且记录包含 responseStatus 时，请使用数值响应代码，而不是在所有 API-server 文本中搜索单词 Error：

```
fields @timestamp, verb, objectRef.resource, responseStatus.code, user.username
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code >= 400
| sort @timestamp desc
| limit 20
```

此查询会查找所选审计流/时间窗口中记录的响应，并不包含每个尝试过的 API 请求。4xx 响应可能是调用方/授权问题，并不自动代表控制平面中断。审计策略、阶段、摄取和保留期都会影响覆盖范围。

#### 检查 Authenticator 事件

添加失败筛选条件之前，请检查当前的 authenticator 消息格式：

```
fields @timestamp, @message
| filter @logStream like /authenticator/
| sort @timestamp desc
| limit 50
```

固定的“身份验证失败”子字符串可能遗漏实际失败，也可能匹配无关文本。请比较实际观测到的消息/状态字段，并与审计 401/403 响应关联起来。身份验证和 Kubernetes 授权是不同的检查；一个日志流不足以完整证明两者。

#### 按级别统计日志数量

对于相同的结构化应用 schema：

```
fields toupper(data.level) as level, kubernetes.namespace_name
| filter ispresent(data.level)
| stats count(*) as log_records by @log, level, kubernetes.namespace_name
| sort log_records desc
```

这些是日志记录数量，而不是唯一请求数或错误率。重试、重复消息和采集器重复记录都会影响计数。解析假定以空格分隔的格式，无法可靠分类任意 JSON/容器/控制平面日志。

参考资料：[JSON 字段发现](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_AnalyzeLogData-discoverable-fields.html)、[查询函数](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax-operations-functions.html)。

### Amazon OpenSearch Service

使用 Amazon OpenSearch Service（前身为 Amazon Elasticsearch Service）存储、分析和可视化 EKS 集群日志：

#### 准备自有 OpenSearch domain

通过平台所有者审查过的预置流程准备 domain。根据工作负载选择受支持的引擎/版本、容量和保留策略。对于此日志示例，请使用 VPC domain，并配置已批准的网络路径、HTTPS、静态加密、节点间加密和精细访问控制（FGAC）。配置采集器之前，请检查实际的 domain：

```bash
set -euo pipefail
: "${AWS_REGION:?Set the owned domain Region}"
: "${OPENSEARCH_DOMAIN:?Set the owned domain name}"
aws opensearch describe-domain --region "$AWS_REGION" \
  --domain-name "$OPENSEARCH_DOMAIN" \
  --query 'DomainStatus.{ARN:ARN,Engine:EngineVersion,Endpoint:Endpoint,EndpointV2:EndpointV2,Endpoints:Endpoints,VPC:VPCOptions,HTTPS:DomainEndpointOptions.EnforceHTTPS,AtRest:EncryptionAtRestOptions.Enabled,NodeToNode:NodeToNodeEncryptionOptions.Enabled,FGAC:AdvancedSecurityOptions.Enabled}'
```

网络可达性、domain 访问策略和 FGAC 是不同层级。SigV4 采集器身份必须获得 domain/IAM 策略允许，并映射到权限受限的 OpenSearch 摄取角色。请将管理与摄取分开。内部用户数据库配置也可以映射 IAM 身份；不要在同一个请求中同时使用 HTTP basic 凭证和 SigV4 凭证。

通过已批准的身份/Secret 管理路径提供凭证。共享的已发布管理员密码和通配符公共访问策略都不适合用于日志记录。将现有公共 domain 移入 VPC 需要新建 domain 并迁移数据；这不是原地切换 endpoint。更改现有 Terraform 资源类型/地址也需要制定所有权/状态迁移计划。

在采集器配置中使用返回的 endpoint 主机名，并验证 CA/主机名和已授权摄取。仅检查 domain 并不能证明数据已摄取或系统已达到生产就绪状态。

参考资料：[OpenSearch FGAC](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/fgac.html)、[VPC domain 和迁移](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/vpc.html)。

#### 使用 Fluent Bit 将日志发送到 OpenSearch

请使用“容器日志记录”一节中的 Fluent Bit values、RBAC 后渲染器和 OpenSearch overlay。提供实际的自有 endpoint、SigV4 权限和 FGAC 摄取映射。应用无关的 fluent-bit-config ConfigMap，不会修改挂载了其他名称 ConfigMap 的 Helm release。

#### 使用 OpenSearch Dashboards 可视化日志

在 OpenSearch Dashboards 中创建以下可视化内容：

1. **日志浏览器**：搜索和筛选日志
2. **仪表板**：基于日志数据创建仪表板
3. **可视化**：基于日志数据创建图表和图形
4. **告警**：根据日志模式配置告警

### Grafana Loki

Grafana Loki 是一种采用类似 Prometheus 标签方式的日志聚合系统：

#### 安装 Loki

对于自有部署和受支持的客户端（例如 Alloy），请使用[当前 Loki 设置指南](../observability/logging/01-loki.md)。已弃用的 loki-stack/Promtail 组合不是当前安装路径。发送生产日志之前，请配置存储、身份验证和标签/保留策略。

#### LogQL 查询示例

以下查询假定采集器会创建 namespace 和 pod 流标签，并将应用 JSON 存储为顶层 level 字段。标签和 JSON 提取方式不会自动与 CloudWatch/Fluent Bit 数据封装保持一致：

```logql
{namespace="default"} |= "ERROR"

{namespace="default", pod=~"app-.*"} | json | __error__=""

sum by (level) (
  count_over_time(
    {namespace="default"} | json | __error__="" | level=~"INFO|WARN|ERROR" [5m]
  )
)
```

JSON 解析器错误筛选条件应放在解析之后。指标查询必须排除管道错误；还应单独调查被拒绝/格式错误的记录，以免筛选掩盖采集问题。示例级别与大写结构化日志样例相匹配；请根据实际数据调整字段/大小写。流标签应限制取值范围；请求 ID 和用户 ID 应放在受控日志字段中，而不是默认的高基数流标签中。

#### 创建 Grafana 仪表板

使用 Loki 数据源在 Grafana 中创建日志仪表板：

1. 登录 Grafana
2. 点击“+”图标并选择“Dashboard”
3. 点击“Add panel”
4. 选择“Loki”作为数据源
5. 编写 LogQL 查询
6. 配置面板标题、描述和可视化类型
7. 点击“Save”

### AWS CloudTrail

CloudTrail 会记录受支持的 AWS API 活动，例如 EKS cluster/add-on/node-group 管理活动。它不能替代 Kubernetes API 审计日志或应用请求日志。创建重复 trail 或使用尚未准备好的存储桶之前，请先检查账户中现有的组织级/账户级 trails：

```bash
set -euo pipefail
: "${AWS_REGION:?Set the Region to inspect}"
aws cloudtrail describe-trails --region "$AWS_REGION" --include-shadow-trails \
  --query 'trailList[].{Name:Name,ARN:TrailARN,HomeRegion:HomeRegion,Organization:IsOrganizationTrail,MultiRegion:IsMultiRegionTrail}'
```

选择自有 trail 及其 home Region 后：

```bash
set -euo pipefail
: "${TRAIL_ARN:?Choose the existing owned trail ARN}"
: "${TRAIL_HOME_REGION:?Use the home Region of the selected trail}"
aws cloudtrail get-trail-status --region "$TRAIL_HOME_REGION" --name "$TRAIL_ARN"
aws cloudtrail get-event-selectors --region "$TRAIL_HOME_REGION" --trail-name "$TRAIL_ARN"
```

请检查日志记录/传递错误和事件选择器。新建 trail 需要单独审查存储桶/传递策略、加密/密钥权限、保留期和所有权配置。仅有 trail 资源不能证明日志已到达存储位置；创建 trail 和启动日志记录是两个不同的操作。

#### 近期管理事件

无需创建 trail 即可使用 CloudTrail Event history；它涵盖所选 Region 过去 90 天内的管理事件。此只读示例查询过去一小时，并将显示的批次限制为 50 项：

```bash
set -euo pipefail
: "${AWS_REGION:?Set the Region to query}"
python3 - <<'PY'
import datetime
import json
end = datetime.datetime.now(datetime.timezone.utc)
request = {
    "LookupAttributes": [{"AttributeKey": "EventSource", "AttributeValue": "eks.amazonaws.com"}],
    "StartTime": (end - datetime.timedelta(hours=1)).isoformat(),
    "EndTime": end.isoformat(),
}
with open("cloudtrail-lookup.json", "w") as stream:
    json.dump(request, stream, indent=2)
PY
aws cloudtrail lookup-events --region "$AWS_REGION" \
  --cli-input-json file://cloudtrail-lookup.json --max-items 50 --output json
```

如果 CLI 返回 NextToken，请在相同请求/时间窗口下使用 --starting-token，继续检查其余结果。请解析 CloudTrailEvent JSON 字符串以获取完整身份/请求/错误字段；仅凭 Username 无法完整归属调用者。Event history 并非长期保留方案，也不包含所有数据事件类别。

#### 适用于符合条件的现有客户的 CloudTrail Lake

CloudTrail Lake 已于 2026 年 5 月 31 日停止接受新客户，目前仅接收关键错误/安全更新。现有客户可根据文档规定的条件继续使用。组织事件数据存储可以涵盖新的成员账户；现有账户级数据存储不会自动将 Lake 摄取范围扩展到新加入的账户。CloudTrail Trails、Insights 和 Aggregated Events 仍受支持。对于新的分析设计，请查看 AWS 当前的 CloudWatch 迁移/摄取指南，不要要求新注册 Lake。

对于符合条件的现有存储，请将 EVENT_DATA_STORE_ID 替换为 Lake 查询编辑器中选定的实际 ID。它不是 eks_events 这类任意表别名。以下示例保留了原始的 2025 年 7 月 1 日至 11 日示例时间范围；这不是本次审计执行的查询，而且存储必须实际保留该时间段：

```sql
SELECT eventTime, eventName, userIdentity.arn, requestParameters
FROM EVENT_DATA_STORE_ID
WHERE eventSource = 'eks.amazonaws.com'
  AND eventTime >= '2025-07-01 00:00:00'
  AND eventTime < '2025-07-12 00:00:00'
ORDER BY eventTime DESC
```

不包含上限的结束时间可涵盖最后一整天，并且无需假设时间戳只有整秒精度。查询会返回可用的 EKS AWS 管理活动；各个身份字段可能因调用者类型而异。执行查询可能产生服务费用。

参考资料：[CloudTrail Event history](https://aws.amazon.com/cloudtrail/features/)、[Lake 可用性变更](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-lake-service-availability-change.html)、[选择事件数据存储](https://docs.aws.amazon.com/help-panel/awscloudtrail/latest/console/query-editor-eds.html)。

### 日志分析最佳实践

有效分析 EKS 集群日志的最佳实践：

#### 结构化日志记录

在应用中使用结构化日志格式（例如 JSON）：

```json
{
  "timestamp": "2025-07-11T13:00:00Z",
  "level": "INFO",
  "message": "Request processed successfully",
  "request_id": "12345",
  "user_id": "user-789",
  "duration_ms": 45,
  "status_code": 200
}
```

#### 关联 ID

上面的 2025 年 JSON 示例仅用于说明，包括其时长和虚构标识符；它不是新的测量结果。即使用户/会话标识符是化名，仍可能属于敏感信息。仅保留必要字段，并配置适当的访问权限和保留期。

对于使用 SLF4J 和支持 MDC 的日志后端的 Java 应用，请使用取值范围受限的标识符，并为嵌套调用恢复之前的上下文。这个与框架无关的辅助程序移除了未定义的 Request 类型，并包含 UUID 导入：

```java
import java.util.UUID;
import java.util.regex.Pattern;
import org.slf4j.MDC;

public final class CorrelationContext {
    private static final Pattern SAFE_ID = Pattern.compile("[A-Za-z0-9._-]{1,128}");

    public static void run(String suppliedId, Runnable operation) {
        String correlationId = suppliedId != null && SAFE_ID.matcher(suppliedId).matches()
            ? suppliedId : UUID.randomUUID().toString();
        String previous = MDC.get("correlation_id");
        MDC.put("correlation_id", correlationId);
        try {
            operation.run();
        } finally {
            if (previous == null) {
                MDC.remove("correlation_id");
            } else {
                MDC.put("correlation_id", previous);
            }
        }
    }
}
```

使用提取出的请求标头和实际操作调用 CorrelationContext.run。配置 encoder/pattern 以包含 correlation_id；在 MDC 中放入值不会自动改变日志格式。调用方提供的关联 ID 是跟踪元数据，不是身份验证信息。MDC 上下文与线程绑定：跨 executor/reactive 边界传播和恢复上下文时，请使用后端/框架支持的机制。已审查此辅助程序的源代码；此处环境没有 Java 编译器/运行时。

参考资料：[SLF4J MDC API](https://www.slf4j.org/apidocs/org/slf4j/MDC.html)、[Logback MDC 和线程池](https://logback.qos.ch/manual/mdc.html)。

#### 使用日志级别

使用适当的日志级别表示日志的重要程度：

- **ERROR**：应用错误和异常
- **WARN**：潜在问题或意外情况
- **INFO**：一般应用事件
- **DEBUG**：有助于调试的详细信息
- **TRACE**：非常详细的调试信息

#### 日志保留策略

根据已批准的运维、数据访问和保存要求选择保留期。缩短保留期可能会使已存储的数据过期；某个时间长度并不代表符合合规要求或存在不可变保留锁定。对于自有 CloudWatch 日志组，以下命令会更改保留期，而不只是检查日志：

```bash
set -euo pipefail
: "${AWS_REGION:?Set the log group Region}"
: "${LOG_GROUP:?Set the reviewed owned log group}"
: "${RETENTION_DAYS:?Choose a supported approved retention value such as 30}"
aws logs put-retention-policy --region "$AWS_REGION" \
  --log-group-name "$LOG_GROUP" --retention-in-days "$RETENTION_DAYS"
```

对于 S3 通用存储桶，PutBucketLifecycleConfiguration 会替换整个生命周期配置。请检查并保留所有无关规则、版本控制/Object Lock 要求和转换最小对象大小设置。使用预期账户所有者以减少误操作到错误存储桶的风险：

```bash
set -euo pipefail
: "${LOG_BUCKET:?Set the owned general purpose S3 bucket}"
: "${ACCOUNT_ID:?Set its expected AWS account ID}"
aws s3api get-bucket-versioning --bucket "$LOG_BUCKET" --expected-bucket-owner "$ACCOUNT_ID"
aws s3api get-bucket-lifecycle-configuration --bucket "$LOG_BUCKET" \
  --expected-bucket-owner "$ACCOUNT_ID" --output json > current-lifecycle.json
```

只有当服务明确返回 NoSuchLifecycleConfiguration 时，才能确认生命周期配置不存在，并在新策略场景下将 current-lifecycle.json 初始化为 {"Rules":[]}。不要将 AccessDenied 或其他查询失败视为空策略。添加以下示例之前，请审查现有规则。

将此说明性 90 天当前对象策略保存为 log-lifecycle-example.json。它会在 30 天后将符合条件的日志转换为 Standard-IA，并在 90 天后过期。原先的“第 60 天转入 Glacier、第 90 天过期”组合只会在 Glacier Flexible Retrieval 中保留名义上的 30 天，而该存储类别的最低存储计费期限为 90 天，因此本示例省略了这一转换。

```json
{
  "Rules": [
    {
      "ID": "example-logs-expiry-90d",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "logs/"
      },
      "Expiration": {
        "Days": 90
      }
    },
    {
      "ID": "example-logs-standard-ia-30d",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "logs/"
      },
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        }
      ]
    }
  ]
}
```

这些规则按对象时长触发，包括已有对象，而且操作是异步的。实际转换时间、提前手动删除或覆盖仍可能产生最低期限费用。Standard-IA 的最低计费期限为 30 天；Glacier Flexible Retrieval 为 90 天；Deep Archive 为 180 天。规划更长的归档时间表时，应考虑这些限制以及实际访问/检索成本；这些是服务规则，不是经过测量的节省金额。

如需经过审查后添加规则，请将以下内容保存为 merge-log-lifecycle.py 并运行。此脚本会保留现有 Rules，并拒绝与示例规则 ID 冲突；它不会处理筛选条件重叠，也不会批准合并后的保留策略：

```python
import json

with open("current-lifecycle.json") as stream:
    current = json.load(stream)
with open("log-lifecycle-example.json") as stream:
    example = json.load(stream)
if not isinstance(current.get("Rules"), list) or not isinstance(example.get("Rules"), list):
    raise SystemExit("Both files must contain an explicitly reviewed Rules array")
existing_ids = {rule.get("ID") for rule in current["Rules"] if rule.get("ID")}
new_ids = [rule.get("ID") for rule in example["Rules"]]
if any(not name for name in new_ids) or len(new_ids) != len(set(new_ids)):
    raise SystemExit("Example rules need distinct nonempty IDs")
if existing_ids.intersection(new_ids):
    raise SystemExit("A rule ID already exists; review its owner and changes instead of replacing it")
merged = {"Rules": current["Rules"] + example["Rules"]}
if len(merged["Rules"]) > 1000:
    raise SystemExit("The merged configuration exceeds the lifecycle rule limit")
with open("reviewed-full-lifecycle.json", "w") as stream:
    json.dump(merged, stream, indent=2)
    stream.write("\n")
print("Wrote a candidate preserving existing Rules; review overlaps, retention impact and minimum-size setting")
```



```bash
python3 merge-log-lifecycle.py
```

检查完整候选配置，并与存储桶的最新配置进行比较；由于此 API 会替换整个配置，请协调其他写入者。自 2024 年 9 月以来，新建/修改的配置默认会阻止转换小于 128 KB 的对象。未修改的旧配置可能保留此前的行为。大小筛选器可以覆盖默认设置，而且该设置也可能影响其他保留的规则。请明确选择经过审查的 all_storage_classes_128K 或 varies_by_storage_class 值；如果 GET 响应中提供 TransitionDefaultMinimumObjectSize，该字段会显示此设置。

只有在审查完整配置及其对现有数据的影响之后，才提交完整文件：

```bash
set -euo pipefail
: "${LOG_BUCKET:?Set the reviewed owned bucket}"
: "${ACCOUNT_ID:?Set its expected AWS account ID}"
: "${TRANSITION_MINIMUM_OBJECT_SIZE:?Choose the reviewed minimum-size behavior}"
aws s3api put-bucket-lifecycle-configuration --bucket "$LOG_BUCKET" \
  --expected-bucket-owner "$ACCOUNT_ID" \
  --transition-default-minimum-object-size "$TRANSITION_MINIMUM_OBJECT_SIZE" \
  --lifecycle-configuration file://reviewed-full-lifecycle.json
```

在启用了版本控制的存储桶中，当前版本过期通常会创建删除标记，并保留非当前版本。非当前版本过期、删除标记清理以及 Object Lock/复制限制需要单独审查；此示例并未声称会删除所有版本或清空存储桶。不会发生转换的小对象仍可能符合过期规则。

此次审计未应用任何保留策略或对象生命周期操作。参考资料：[生命周期替换 API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketLifecycleConfiguration.html)、[转换限制](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html)、[过期/版本控制/最低期限](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-expire-general-considerations.html)。

## 监控与日志记录最佳实践

下面介绍在 EKS 集群中有效实施监控与日志记录的最佳实践。

### 监控最佳实践

#### 多层监控

监控 EKS 集群的所有层：

1. **基础设施层**：EC2 实例、VPC、子网、安全组
2. **集群层**：控制平面、节点、Pods、Services
3. **应用层**：应用性能、用户体验

#### 黄金信号监控

重点关注 Google SRE 手册建议的“4 个黄金信号”：

1. **延迟**：处理请求所需的时间
2. **流量**：系统收到的请求数量
3. **错误**：失败请求的比率
4. **饱和度**：系统的“满载”程度（例如内存使用情况）

#### 主动监控

使用趋势和异常识别正在形成的风险。预测只是估算，不能保证一定会提前预测到事件：

1. **趋势分析**：分析随时间变化的资源使用趋势
2. **异常检测**：检测异常模式
3. **预测分析**：预测未来的资源需求

#### 自动扩缩

此说明性 HPA 假定自有的 default/my-app Deployment、可正常工作的资源指标 API，以及适当配置的 CPU/memory requests。利用率目标是 requests 的百分比，而不是节点容量或容器 limits。配置多个指标时，HPA 会选择副本数建议值最大的指标；指标故障可能会阻止缩容。请检查 HPA 条件，并测试工作负载是否确实能够从水平扩缩中受益：

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

#### 业务指标监控

除技术指标外，还应监控业务指标：

1. **用户活动**：活跃用户数、会话时长
2. **交易**：交易数量、交易金额
3. **转化率**：用户转化率、流失率
4. **SLI/SLO 达成情况**：衡量指标及其定义的目标。SLA 是一项可能包含后果的协议；仅满足内部 SLO 并不能证明符合合同要求。

### 日志记录最佳实践

#### 集中式日志记录

将所需日志采集到已批准的目标位置，并明确配置访问权限、保留期和摄取故障监控：

1. **统一格式**：所有应用使用一致的日志格式
2. **集中式存储库**：使用 CloudWatch Logs、OpenSearch 或 Loki 等集中式日志存储库
3. **日志转发**：使用 Fluent Bit 或 Fluentd 等日志转发 agent

#### 包含上下文信息

在日志中包含充足的上下文信息：

1. **时间戳**：准确的时间戳（建议使用 ISO 8601 格式）
2. **请求 ID**：用于分布式系统请求跟踪的唯一 ID
3. **已批准的标识符**：用户/会话 ID 仍可能是敏感信息或身份信息。仅包含必要标识符，并配置适当的访问权限和保留期。
4. **服务信息**：服务名称、版本、实例 ID
5. **错误详情**：错误代码、错误消息、堆栈跟踪

#### 日志级别筛选

根据环境设置适当的日志级别：

1. **开发环境**：仅在调查时有意使用 DEBUG/TRACE；即使在测试中也应筛除 Secret。
2. **预发布环境**：INFO 级别
3. **生产环境**：选择有用的 INFO/WARN 覆盖范围；任何临时 DEBUG 时段都需要限制数据量/持续时间并筛除敏感数据。

#### 保护敏感信息

保护日志中的敏感信息：

1. **PII 遮蔽**：遮蔽个人身份信息（PII）
2. **排除凭证**：排除密码、令牌、API 密钥等凭证
3. **加密**：对静态和传输中的日志进行加密

### 告警最佳实践

#### 告警优先级

对告警排序以减少告警疲劳：

1. **P1（严重）**：需要立即处理的重大问题
2. **P2（高）**：重要问题，应在服务约定的响应窗口内处理；高紧急度并不意味着可以自动等到工作时间。
3. **P3（中）**：需要在计划维护期间处理的问题
4. **P4（低）**：信息性告警

#### 告警分组

将以下路由字段合并到上文完整的 Alertmanager 配置中，同时保留其 receiver 和子路由。按服务上下文分组，而不要自动为每个实例创建单独分组：

```yaml
route:
  group_by: ['cluster', 'namespace', 'alertname']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
```

#### 可操作的告警

在告警中包含足够的故障排除信息：

1. **清晰的标题**：能够明确描述问题的标题
2. **证据和影响**：描述观测到的症状和影响；未经验证的疑似原因应标记为假设。
3. **故障排除步骤**：提供故障排除步骤或链接
4. **相关指标和日志**：提供有助于诊断的指标和日志链接

#### 告警测试

定期测试告警系统：

1. **告警模拟**：生成测试告警
2. **升级测试**：测试升级路径
3. **故障注入**：在受控环境中注入故障

### 成本优化最佳实践

#### 优化日志量

优化日志量以降低成本：

1. **采样**：仅在所需覆盖范围允许的情况下采样，并记录覆盖缺口；保留必需的审计/错误证据。
2. **筛选**：筛除不必要的日志
3. **压缩**：压缩日志

#### 管理指标基数

管理指标基数以降低成本：

1. **标签值有界**：控制不同取值及标签组合，而不只是标签名称的数量。
2. **聚合**：将详细指标聚合到更高层级
3. **采集分辨率**：选择 scrape 间隔和聚合方式，以保留所需信号；过于粗略的采集可能会掩盖峰值。

#### 存储分层

实施经济高效的存储分层：

1. **热存储**：近期日志和经常访问的日志
2. **温存储**：不常访问的日志
3. **冷存储**：归档日志

## 故障排除与调试

下面介绍在 EKS 集群中排查和调试问题的各种技术。

![Diagram mapping three EKS troubleshooting areas (cluster issues, workload issues, common problems) to three debugging tool families: Kubernetes kubectl tools, AWS tools, and network diagnostic tools, with the kubectl tools at the center used by all three areas.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-5.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-5.html)

### 集群故障排除

#### 检查集群状态

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
LOG_GROUP="/aws/eks/$CLUSTER_NAME/cluster"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{ARN:arn,Status:status,Endpoint:endpoint,Logging:logging}'
aws logs describe-log-streams --region "$AWS_REGION" \
  --log-group-name "$LOG_GROUP" --order-by LastEventTime --descending \
  --max-items 10 --query 'logStreams[].{Name:logStreamName,LastEvent:lastEventTimestamp}'
```

对于有限的 GetLogEvents 读取，请选择实际返回的流，或使用上文的查询。此检查不会启用或禁用日志记录。如果未启用日志记录，请使用单独审查过的配置流程，并验证更新是否完成。

#### 节点故障排除

解释节点条件之前，请确认 Kubernetes context 并选择实际节点。节点 Ready 状态、是否可调度以及应用健康状况是不同的信号：

```bash
kubectl config current-context
kubectl get nodes
: "${NODE_NAME:?Choose the node to inspect}"
kubectl describe node "$NODE_NAME"
kubectl get node "$NODE_NAME" -o jsonpath='{.spec.providerID}{"\n"}{.status.nodeInfo.kubeletVersion}{"\n"}{.status.nodeInfo.containerRuntimeVersion}{"\n"}'
```

对于托管 node group，请选择其实际名称并检查状态/运行状况。此方法不适用于所有 Auto Mode、Fargate 或自行管理的节点：

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster}"
: "${AWS_REGION:?Set its Region}"
: "${NODEGROUP_NAME:?Choose the actual managed node group}"
aws eks describe-nodegroup --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --nodegroup-name "$NODEGROUP_NAME" \
  --query 'nodegroup.{Status:status,Version:version,Health:health.issues,Resources:resources}'
```

请使用节点所有者批准的访问/诊断路径。SSH 是否可用、登录用户和 systemd 工具取决于节点 OS 和配置，并非 EKS 的通用功能。Auto Mode、Fargate 和 Bottlerocket 必须遵循各自适用的托管/平台流程。对于通过授权会话连接到标准 Linux EC2 节点且该节点使用 systemd 的情况，可检查有限范围内的 kubelet 日志、磁盘空间和 inode：

```bash
sudo journalctl -u kubelet --since "30 minutes ago" --no-pager
df -h
df -i
```

对于可以访问的自有实例，EC2 控制台输出有助于排查启动问题，但它并不是完整的 kubelet/应用日志流。请使用报告的运行时及其文档说明的诊断方法，不要假设每个节点都运行 Docker。

#### Pod 故障排除

```bash
set -euo pipefail
: "${NAMESPACE:?Set the owned namespace}"
: "${POD_NAME:?Choose the actual Pod}"
: "${CONTAINER_NAME:?Choose its application container}"
kubectl get pod "$POD_NAME" -n "$NAMESPACE" -o wide
kubectl describe pod "$POD_NAME" -n "$NAMESPACE"
kubectl events -n "$NAMESPACE" --for="pod/$POD_NAME"
kubectl logs "$POD_NAME" -n "$NAMESPACE" -c "$CONTAINER_NAME" --tail=100
```

如果该容器有可用的上一个已终止实例，还可以检查其日志：

```bash
kubectl logs "$POD_NAME" -n "$NAMESPACE" -c "$CONTAINER_NAME" --previous --tail=100
```

只有存在上一个已终止的容器实例时，previous-log 命令才适用。它无法恢复任意更早的 Pods，也无法恢复随节点丢失的日志。请综合查看退出代码、最后一次终止原因、探针和资源事件；仅凭重启计数无法证明发生了 OOM 或确定某个根因。并非所有应用镜像都包含 /bin/bash 之类的 shell 命令。

### 网络故障排除

#### Service 故障排除

```bash
set -euo pipefail
: "${NAMESPACE:?Set the service namespace}"
: "${SERVICE_NAME:?Choose the actual Service}"
kubectl get service "$SERVICE_NAME" -n "$NAMESPACE" -o yaml
kubectl get endpointslices.discovery.k8s.io -n "$NAMESPACE" \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
kubectl get pods -n "$NAMESPACE" --show-labels
kubectl get networkpolicies -n "$NAMESPACE"
```

请使用 EndpointSlices 检查当前 endpoint；旧版 Endpoints API 已弃用，但并非在所有地方都已移除。检查选择器、就绪 endpoint 地址、Service 端口/targetPort 和协议。DNS 解析、endpoint 就绪状态和网络可达性是不同的检查项。

本地端口转发可以检查选定的 Service 端口，但它通过诊断路径访问，不能证明普通 Pod 到 Service 的流量或负载均衡器工作正常。请设置实际 Service 端口：

```bash
set -euo pipefail
: "${NAMESPACE:?Set the service namespace}"
: "${SERVICE_NAME:?Choose the Service}"
: "${SERVICE_PORT:?Choose its service port number}"
kubectl port-forward --address 127.0.0.1 -n "$NAMESPACE" \
  "svc/$SERVICE_NAME" "8080:$SERVICE_PORT"
```

#### Network Policy 和诊断上下文

请检查源端出口和目标端入口、namespace/Pod 选择器、DNS 访问和强制执行策略的 CNI。安全组、路由、网络 ACL、service mesh 策略和 TLS 也可能构成额外层级。来自任意临时 Pod 的探测可能使用与故障工作负载不同的标签、ServiceAccount、安全组或 sidecar。

进行授权调查时，请使用与受限安全配置兼容且经过审查的非 root 镜像，向选定 Pod 添加临时调试容器。DEBUG_IMAGE 应设置为已批准的 digest，而不是较旧的 BusyBox 标签或未经审查的 latest 镜像：

```bash
set -euo pipefail
: "${NAMESPACE:?Set the owned Pod namespace}"
: "${POD_NAME:?Choose the Pod}"
: "${CONTAINER_NAME:?Choose the target container}"
: "${DEBUG_IMAGE:?Set the reviewed non-root diagnostic image digest}"
kubectl debug "$POD_NAME" -n "$NAMESPACE" -it \
  --image="$DEBUG_IMAGE" --profile=restricted --target="$CONTAINER_NAME" -- sh
```

此操作会通过添加临时容器修改 Pod，并且需要相应的 RBAC/准入权限。记录会一直保留到 Pod 被移除；退出 shell 并不会删除临时容器条目。进程 namespace 目标功能取决于运行时支持情况。镜像必须包含预期工具，并能在不使用安全配置禁止的 capabilities 的情况下运行。不要为了绕过被拒绝的调试操作而悄悄切换到 privileged 配置文件。

在调试 shell 中，还需要在那里设置目标值；主机 shell 中的变量不会自动继承。选定镜像中包含相应工具时：

```bash
: "${SERVICE_DNS:?Set the intended service DNS name inside this shell}"
: "${SERVICE_PORT:?Set its port inside this shell}"
nslookup "$SERVICE_DNS"
nc -zv "$SERVICE_DNS" "$SERVICE_PORT"
```

需要使用 FQDN 时，请使用实际集群 DNS 后缀。TCP 连接成功不能验证 HTTP、应用身份验证或 TLS。数据包捕获和节点调试需要单独审查权限/上下文，并应限制捕获筛选条件、持续时间和存储；通用的非特权 tcpdump 命令并非在所有环境中都可用。即使输出已截断，数据包捕获也可能包含凭证或用户数据。此次审计未启动调试 Pod、临时容器、数据包捕获或节点会话。

### 日志记录和监控故障排除

#### Fluent Bit 故障排除

对于本章安装的独立采集器，渲染后的 DaemonSet 和 ConfigMap 在 logging 中均为 eks-log-collector：

```bash
kubectl get daemonset eks-log-collector -n logging
kubectl get pods -n logging -l app.kubernetes.io/instance=eks-log-collector
kubectl logs -n logging -l app.kubernetes.io/instance=eks-log-collector \
  -c aws-for-fluent-bit --prefix --tail=100
kubectl get configmap eks-log-collector -n logging -o yaml
```

如果由 CloudWatch add-on 负责采集，请检查 amazon-cloudwatch 及其实际资源。验证挂载配置、节点文件访问、IRSA/Pod Identity 选择、RBAC、输出连接能力以及缓冲/backlog/丢弃指标。不要创建无关的 kube-system/fluent-bit-config，并假定采集器会读取它。共享配置/日志输出前，请检查其中是否含有敏感数据。

#### Prometheus 故障排除

```bash
kubectl get prometheus,alertmanager -n monitoring
kubectl get pods,pvc -n monitoring
kubectl get servicemonitors,prometheusrules -n monitoring
kubectl port-forward --address 127.0.0.1 -n monitoring \
  svc/monitoring-kube-prometheus-prometheus 9090:9090
```

端口转发期间，请检查 `http://127.0.0.1:9090/targets`。检查实际 Pod 日志、target 错误、证书信任、命名 Service 端口、namespace/标签选择器、规则和近期样本。仅有 ServiceMonitor 对象并不能证明 Prometheus 已选择它，也不能证明其 endpoint 可达。对于 AMP，请单独检查 remote-write 故障/积压和目标 workspace。

#### Grafana 故障排除

```bash
kubectl get deployment monitoring-grafana -n monitoring
kubectl logs deployment/monitoring-grafana -n monitoring -c grafana --tail=100
kubectl port-forward --address 127.0.0.1 -n monitoring \
  svc/monitoring-grafana 3000:80
```

打开 `http://127.0.0.1:3000` 并检查已配置的数据源、凭证、时间范围和查询。此处本地技术栈的 Prometheus 数据源 UID 为 prometheus；AMG/AMP 有单独的插件和 IAM 要求。仪表板为空可能是因为数据源/标签/时间范围错误或摄取失败，而不是使用量为零。

### 常见问题及解决方案

#### ImagePullBackOff 错误

检查拉取错误、镜像仓库/digest、体系结构、registry 授权和节点网络路径。只要具备适当的私有 endpoint/路由，并不一定需要互联网访问。对于 ECR，请验证 EC2 节点或 Fargate Pod 执行身份和仓库策略；应用 IRSA/Pod Identity 不是 kubelet 镜像拉取身份。

对于使用 pull Secret 的私有 registry，请通过已批准的凭证流程准备受保护、自包含的 Docker auth JSON 文件。仅包含 credential-helper 引用的文件不足以用作 Kubernetes imagePullSecret。创建新的自有 Secret 时，请传入文件路径，而不是在命令参数中传递密码：

```bash
set -euo pipefail
: "${NAMESPACE:?Set the owned workload namespace}"
: "${DOCKER_CONFIG_JSON:?Set the protected self-contained registry auth JSON file}"
kubectl create secret generic regcred -n "$NAMESPACE" \
  --type=kubernetes.io/dockerconfigjson \
  --from-file=".dockerconfigjson=$DOCKER_CONFIG_JSON"
```

仅将其附加到目标自有工作负载。对于 Deployment，此 strategic patch 会将命名的 imagePullSecrets 条目与现有条目合并。该操作会更改 Pod 模板并触发 rollout；请先检查所有者的部署流程：

```bash
set -euo pipefail
: "${NAMESPACE:?Set the owned workload namespace}"
: "${DEPLOYMENT:?Set the owned Deployment name}"
kubectl patch deployment "$DEPLOYMENT" -n "$NAMESPACE" --type=strategic \
  -p '{"spec":{"template":{"spec":{"imagePullSecrets":[{"name":"regcred"}]}}}}'
```

对于现有 Secret，请遵循所有者的轮换流程，并保留其他 registry 引用。不要将 namespace 默认 ServiceAccount 作为一刀切修复方案。创建 Secret 本身不能验证 registry 登录、镜像是否存在或拉取是否成功。

#### CrashLoopBackOff 错误

将所选容器的当前/先前日志、退出代码、终止原因、启动/存活探针、配置和资源事件关联起来。OOMKilled、探针失败和应用退出是不同原因。缺失的启动依赖项或错误命令也可能导致容器重启。若常规镜像缺少工具，请使用上文范围明确的调试流程；收集证据前不要重启/删除工作负载。

#### 节点处于 NotReady 状态

通过适当的平台访问路径检查 Ready 状态/原因、节点/lease 新鲜度、压力条件以及实际运行时/kubelet 诊断信息。磁盘字节数、inode 耗尽、网络/API 可达性和运行时故障需要不同的处理方式。不要仅凭 NotReady 状态显示就推断会触发自动修复或可以安全地 drain 节点。

#### Service 连接问题

按照上文的 Service 到 EndpointSlice 再到 Pod 路径进行检查，然后检查源/目标网络控制以及应用监听的端口/协议。请从具有代表性的工作负载上下文进行测试。仅端口转发、DNS 查询或 TCP 握手成功，不能证明端到端 Service 健康。

### 调试工具

使用 kubectl 检查 Kubernetes 状态/事件，使用 AWS CLI 检查相应托管服务状态，并使用获准且符合上下文的网络工具检查连接能力。保留证据，并区分检查操作与创建 Pod、更改模板、drain 节点或更改日志记录配置等操作。

#### 获取 CloudWatch Logs Insights 查询结果

StartQuery 会返回异步查询 ID，而不是最终结果。此 Bash/Python 示例使用 UTC epoch 秒数，避免使用仅 macOS 支持的 date -v 选项，并进行有限次数的轮询；仅在查询状态为 Complete 时打印结果：

```bash
set -euo pipefail
: "${AWS_REGION:?Set the log group Region}"
: "${LOG_GROUP:?Set the owned log group to query}"
python3 - "$LOG_GROUP" <<'PY'
import datetime
import json
import sys
end = datetime.datetime.now(datetime.timezone.utc)
request = {
    "logGroupName": sys.argv[1],
    "startTime": int((end - datetime.timedelta(hours=1)).timestamp()),
    "endTime": int(end.timestamp()),
    "queryString": "fields @timestamp, @message | sort @timestamp desc | limit 50",
}
with open("logs-query-request.json", "w") as stream:
    json.dump(request, stream, indent=2)
PY
STARTED=$(aws logs start-query --region "$AWS_REGION" \
  --cli-input-json file://logs-query-request.json --output json)
QUERY_ID=$(python3 - "$STARTED" <<'PY'
import json
import sys
value = json.loads(sys.argv[1]).get("queryId")
if not isinstance(value, str) or not value:
    raise SystemExit("StartQuery did not return a query ID")
print(value)
PY
)
printf 'Started query %s\n' "$QUERY_ID" >&2
for ((query_attempt = 1; query_attempt <= 20; query_attempt++)); do
  aws logs get-query-results --region "$AWS_REGION" --query-id "$QUERY_ID" \
    --output json > logs-query-result.json
  QUERY_STATE=$(python3 - <<'PY'
import json
with open("logs-query-result.json") as stream:
    print(json.load(stream)["status"])
PY
)
  case "$QUERY_STATE" in
    Complete)
      cat logs-query-result.json
      exit 0
      ;;
    Scheduled|Running)
      if (( query_attempt < 20 )); then sleep 3; fi
      ;;
    *)
      printf 'Query %s ended with status %s; inspect logs-query-result.json\n' "$QUERY_ID" "$QUERY_STATE" >&2
      exit 1
      ;;
  esac
done
printf 'Query %s is still %s; inspect it again or stop it explicitly if no longer needed\n' "$QUERY_ID" "$QUERY_STATE" >&2
exit 2
```

轮询次数上限并不是服务超时。仍在运行的查询会继续活动；请再次检查，或者如果不再需要，则明确使用 StopQuery 停止。限定日志组/时间范围和所需 IAM 权限，并将查询成本纳入考虑。此次审计未执行 CloudWatch 查询或集群调试操作。

## 结论

本文介绍了在 Amazon EKS 集群中监控与日志记录的各种工具、技术和最佳实践。实施有效的监控与日志记录策略，能够让您持续了解集群状态、及早发现问题，并在出现故障时快速响应。

涵盖的主要主题：

1. **监控与日志记录概述**：监控与日志记录的重要性和架构
2. **EKS 控制平面日志记录**：控制平面日志类型以及启用方式
3. **容器日志记录**：使用 Fluent Bit 和 CloudWatch Container Insights 收集容器日志
4. **集群监控**：使用 CloudWatch、Prometheus 和 Grafana 监控集群
5. **告警与事件管理**：使用 CloudWatch alarms 和 Prometheus Alertmanager 配置告警
6. **日志分析与可视化**：使用 CloudWatch Logs Insights、OpenSearch 和 Grafana Loki 分析日志
7. **监控与日志记录最佳实践**：有效监控与日志记录的最佳实践
8. **故障排除与调试**：常见问题及解决方案

EKS 集群的监控与日志记录是一项持续工作，应不断改进，以满足集群和应用的要求。

## 参考资料

- [Amazon EKS 监控最佳实践](https://docs.aws.amazon.com/eks/latest/userguide/eks-observe.html)
- [Amazon EKS 日志记录最佳实践](https://docs.aws.amazon.com/prescriptive-guidance/latest/amazon-eks-observability-best-practices/logging-best-practices.html)
- [Kubernetes 监控架构](https://kubernetes.io/docs/tasks/debug-application-cluster/resource-usage-monitoring/)
- [Prometheus 文档](https://prometheus.io/docs/introduction/overview/)
- [Grafana 文档](https://grafana.com/docs/grafana/latest/)
- [Fluent Bit 文档](https://docs.fluentbit.io/manual/)
- [Amazon CloudWatch 文档](https://docs.aws.amazon.com/cloudwatch/)
- [Amazon OpenSearch Service 文档](https://docs.aws.amazon.com/opensearch-service/)

## 测验

要测试您对本章内容的掌握情况，请尝试[主题测验](../quizzes/eks/06-eks-monitoring-logging-quiz.md)。

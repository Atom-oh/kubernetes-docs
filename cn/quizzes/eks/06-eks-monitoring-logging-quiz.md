# Amazon EKS 监控与日志测验

> **最后更新**：October 16, 2026

本测验用于检验你对 Amazon EKS 监控和日志功能、工具及最佳实践的理解。

## 测验概览
- EKS 集群监控
- 容器和应用程序日志记录
- 性能指标收集与分析
- 告警和异常检测
- 监控与日志架构
- 最佳实践和工具

## 选择题

### 1. 哪项原则正确地指导了 EKS 监控解决方案的设计？

- A. CloudWatch 无法收集应用程序跟踪数据。
- B. 仅安装 Grafana 就会自动收集所有 Pod 指标。
- C. 选择所需信号，配置由你负责的收集器和数据源，并验证数据传送和覆盖范围。
- D. 安装 CloudWatch、Prometheus、Grafana 和 X-Ray 始终可以保证全面可见性。

<details>
<summary>显示答案</summary>

**答案：C. 选择并验证信号/收集器/后端设计。**

**说明：**

组合使用多种工具可能很有用，但所需信号和运维约束决定了设计。CloudWatch 支持的不只是基本基础设施指标，还包括受支持工作负载上的 Application Signals 跟踪/APM。Grafana 可以查询 AWS 和跟踪数据源，但 UI 本身不会收集所有信号。必须显式连接收集器、检测、身份、可访问的端点和兼容配置；任何产品清单都不能保证全面覆盖。

**保留有用的层次：**

| 层 | 信号示例 | 重要依赖项 |
| --- | --- | --- |
| 基础设施 | 节点 CPU/内存、磁盘、网络 | 受支持的节点收集器和正确的指标维度 |
| Kubernetes | 对象状态、就绪状态、API 活动 | Exporter/API/审计权限和实际目标 |
| 应用程序 | 请求延迟、错误、业务指标 | 应用程序检测和有界指标架构 |
| 分布式请求 | 跟踪 Span 和服务关系 | 上下文传播、采样和成功导出 |

**实施顺序：**

1. 按照[源章节](../../eks/06-eks-monitoring-logging.md)检查由你负责的 CloudWatch add-on 目录/架构/身份。必须检查 Version5+ Auto Monitor 和重启设置；在已检测的工作负载上再叠加其他代理之前，应先检查冲突。
2. 如果需要 Prometheus 收集/查询，请使用源文档中的 KPS92.9.0 值和已准备好的存储、Grafana Secret 及 kubelet 服务 CA 前提条件。Operator 提供 ServiceMonitor/PrometheusRule 处理能力；独立安装 Prometheus 并不等价。安装后验证实际目标。
3. 对于显式 ADOT 路径，请使用源文档中的 Operator0.158/Collector0.50 v1beta1 示例，该示例使用对象值配置、TLS 和已准备好的 ServiceAccount。Collector 发布包不包含 Operator 安装清单。这条仅跟踪数据的路径会将 Span 发送到 X-Ray；应用程序仍需检测和上下文传播。
4. 对于 AMP，请配置实际的工作区 remote-write 端点和写入者身份。单独配置 Grafana/AMG 数据源/查询身份；AMG12+ 使用 AMP 插件。awsemf exporter 通过 CloudWatch 发布数据，不会自动发布到 AMP。

**数据路径示例：**

```text
EKS control-plane logs -------------------------------> CloudWatch Logs
Container stdout/stderr -> chosen log collector ------> configured log store
Application spans ------> ADOT OTLP receiver ----------> X-Ray
Metric targets ----------> Prometheus -----------------> local TSDB
                              |-- SigV4 remote_write -> AMP
Grafana/AMG -- configured queries --> Prometheus / AMP / CloudWatch / X-Ray
```

这些是可选的数据路径，并不表示每个收集器都会将数据导出到每个后端。在依赖仪表板之前，请验证权限、TLS、发现/选择器、丢弃的数据和有代表性的查询。定义告警优先级/升级流程，并控制基数、采样和保留期；任何自动响应都应单独测试。

**Terraform 规划示例：**

以下资源示例使用 AWS provider 6.69.1。假设所选账户/Region、已有且经过审核的 Grafana 工作区角色、受支持的 AMG 版本，以及符合条件的 IAM Identity Center 设置均已准备就绪。已有资源需要遵循其所有者的导入/变更流程。应用程序日志组名称与源收集器路径相匹配；如果某个组已由 add-on 或其他堆栈管理，请勿再创建第二个所有者。

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
    }
  }
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Use the approved 12-digit AWS account ID."
  }
}

variable "cluster_name" {
  type = string
}

variable "grafana_workspace_role_arn" {
  type = string
}

variable "grafana_version" {
  type        = string
  description = "A reviewed AMG version supported in the selected Region."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

resource "aws_prometheus_workspace" "eks_monitoring" {
  alias = "${var.cluster_name}-monitoring"
}

resource "aws_grafana_workspace" "eks_monitoring" {
  name                     = "${var.cluster_name}-monitoring"
  account_access_type      = "CURRENT_ACCOUNT"
  authentication_providers = ["AWS_SSO"]
  permission_type          = "CUSTOMER_MANAGED"
  role_arn                 = var.grafana_workspace_role_arn
  grafana_version          = var.grafana_version
}

resource "aws_cloudwatch_log_group" "application" {
  name              = "/aws/containerinsights/${var.cluster_name}/application"
  log_group_class   = "STANDARD"
  retention_in_days = 30
}

output "amp_workspace_id" {
  value = aws_prometheus_workspace.eks_monitoring.id
}

output "amp_prometheus_endpoint" {
  value = aws_prometheus_workspace.eks_monitoring.prometheus_endpoint
}

output "grafana_workspace_id" {
  value = aws_grafana_workspace.eks_monitoring.id
}
```

这段配置定义了资源，但没有定义可正常运行的收集或登录路径。请为角色配置针对实际工作区 ARN 的查询权限，分配用户/组，添加数据源，并使用返回的 ID/端点连接收集器。CUSTOMER_MANAGED 明确表示 IAM 管理由所有者负责；旧的 SERVICE_MANAGED/data_sources 片段不能证明通过 API 创建的工作区已拥有这些角色和连接。请另行审核加密、保留期、访问权限和成本要求。本次审计没有执行 Terraform plan/apply、登录或实时遥测查询。

**其他选项为何不正确**：A 低估了 CloudWatch 当前的功能；B 混淆了可视化和收集；D 将安装误当作覆盖范围保证。当脚本的所有权、错误和范围明确时，自定义脚本仍可用于有界自动化和检查。

</details>

### 2. 哪种方法可以正确地将容器日志连接到集中式保留和分析？

- A. 将定期手动复制节点文件视为完整且持久的日志流水线。
- B. 假设容器内的文件始终能在容器和节点替换后保留。
- C. 使用由你负责的收集器，并配置正确的运行时解析器、权限、存储和后端。
- D. 为同一批文件安装两个收集器，并假设这样就能保证无损传送。

<details>
<summary>显示答案</summary>

**答案：C. 配置并验证由你负责的收集路径。**

**说明：**

应用程序通常应将适当的结构化记录写入 stdout/stderr，而平台则负责收集和保留。stdout 是一个良好的接口，但它本身不是持久的集中式存储。收集器可以添加解析、筛选、缓冲和路由；轮转、有限缓冲区、节点丢失和重试仍会影响覆盖范围并导致重复。应控制访问、敏感字段和保留期，而不要声称收集器能保证完整性或无损传送。

**已连线的 Fluent Bit 基线：**

请使用[源章节](../../eks/06-eks-monitoring-logging.md)，不要直接应用无关的 master 分支原始清单。其中的独立示例使用 AWS chart0.2.0/image3.4.14、原生 cloudWatchLogs 设置、CRI 解析、只读节点日志、独立状态/缓冲区，以及经过审核的 RBAC 后置渲染器。请准备实际日志组和 IAM 身份。如果 CloudWatch add-on 已负责管理 Fluent Bit，请使用该所有者的配置，而不要意外创建第二个读取器。

对于 OpenSearch 扇出，请在所有者的安装/升级流程中，将此源覆盖层与完整的基础值及后置渲染器结合使用：

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

请将端点/Region 替换为经过检查的域值。SigV4 权限、域策略、FGAC 角色映射和 TLS 验证是独立要求。不要在同一个请求中将基本身份验证凭证与 SigV4 混用。每个输出都有独立的成功/重试行为；CloudWatch 成功并不能证明 OpenSearch 已收到数据。请使用受支持的记录访问器模板和备用流名称；log_stream_prefix 不是可任意使用 shell 风格语法展开 Kubernetes 记录字段的配置项。

**Fluentd 替代方案：明确插件和输入约定：**

如果由你负责的镜像包含所需的解析器、Kubernetes 元数据和 OpenSearch 插件，Fluentd 仍然是一种选择。将应用程序正文视为 JSON 之前，必须先解码 containerd/CRI-O 封装。请配置 tail 输入、元数据权限、每个收集器的位置/缓冲区存储以及已挂载的配置；以下仅是 OpenSearch 输出片段，并非完整的 ConfigMap/DaemonSet 安装配置：

```text
<match kubernetes.**>
  @type opensearch
  ssl_verify true
  logstash_format false
  include_timestamp true
  index_name eks-logs
  suppress_type_name true
  <endpoint>
    url "#{ENV.fetch('OPENSEARCH_URL')}"
    region "#{ENV.fetch('AWS_REGION')}"
    assume_role_arn "#{ENV.fetch('AWS_ROLE_ARN')}"
    assume_role_web_identity_token_file "#{ENV.fetch('AWS_WEB_IDENTITY_TOKEN_FILE')}"
  </endpoint>
  <buffer>
    @type file
    path /var/lib/fluentd/opensearch
    total_limit_size 256m
    chunk_limit_size 2m
    retry_timeout 1h
    overflow_action block
  </buffer>
</match>
```

此配置使用官方 fluent-plugin-opensearch IRSA 端点字段和固定索引。请准备 OPENSEARCH_URL 以及 IRSA 注入的角色/令牌文件环境变量。设置 logstash_format=true 会忽略 index_name；任意的、按 Pod 定义的索引表达式不能取代经过验证的路由/保留设计。请选择有界索引/别名，并审核滚动策略。文件缓冲区需要适当且可写、隔离的存储路径；即使使用阻塞/重试，在轮转或节点丢失后仍可能丢失尚未读取的日志。本次审计未运行该插件/输入组合。

**所选组件支持 ADOT 日志收集：**

ADOT0.50.0 包含 filelog、file_storage 和 awscloudwatchlogs。对应的上游0.158 CloudWatch Logs exporter 被标记为 alpha；这是带有明确运行时前提条件的特定版本示例，并不代表已达到生产就绪状态。请将其用作所选数据集的替代收集器，避免意外与 Fluent Bit 重复收集。

请准备 Operator0.158、日志命名空间和 ServiceAccount adot-logs，并为其配置经过审核的 IRSA 角色和 AWS 日志写入权限。将信任范围限制为此集群的 OIDC provider、sub=system:serviceaccount:logging:adot-logs 和 aud=sts.amazonaws.com；并提供所需的 STS/Logs 网络路径。此示例适用于标准 Linux EC2 节点，并且需要允许以 root 运行节点代理的准入权限；该代理会只读挂载 /var/log/pods，并使用专用可写状态目录。默认命名空间包含过滤器限制了导出的数据；它不会将节点级 host 挂载变成文件系统安全边界。请审核节点放置/污点、文件所有权和命名空间策略。部署前请设置实际 Region/日志组值：

```yaml
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: adot-logs
  namespace: logging
spec:
  mode: daemonset
  image: public.ecr.aws/aws-observability/aws-otel-collector:v0.50.0
  serviceAccount: adot-logs
  nodeSelector:
    kubernetes.io/os: linux
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: eks.amazonaws.com/compute-type
            operator: NotIn
            values: [fargate, auto, hybrid]
  env:
  - name: AWS_REGION
    value: us-west-2
  - name: AWS_EC2_METADATA_DISABLED
    value: "true"
  - name: K8S_NODE_NAME
    valueFrom:
      fieldRef:
        fieldPath: spec.nodeName
  - name: LOG_GROUP_NAME
    value: /aws/containerinsights/my-owned-cluster/application
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: "1"
      memory: 512Mi
  podSecurityContext:
    runAsUser: 0
    runAsGroup: 0
    runAsNonRoot: false
    seccompProfile:
      type: RuntimeDefault
  securityContext:
    allowPrivilegeEscalation: false
    readOnlyRootFilesystem: true
    capabilities:
      drop: [ALL]
  volumes:
  - name: pod-logs
    hostPath:
      path: /var/log/pods
      type: Directory
  - name: collector-state
    hostPath:
      path: /var/lib/adot-logs
      type: DirectoryOrCreate
  volumeMounts:
  - name: pod-logs
    mountPath: /var/log/pods
    readOnly: true
  - name: collector-state
    mountPath: /var/lib/adot-logs
  config:
    extensions:
      file_storage:
        directory: /var/lib/adot-logs/checkpoints
        create_directory: true
      health_check:
        endpoint: 0.0.0.0:13133
    receivers:
      filelog:
        include: [/var/log/pods/default_*/*/*.log]
        include_file_path: true
        start_at: end
        storage: file_storage
        retry_on_failure:
          enabled: true
          max_elapsed_time: 5m
        operators:
        - type: container
          add_metadata_from_filepath: true
          max_log_size: 1MiB
    processors:
      memory_limiter:
        check_interval: 1s
        limit_mib: 384
        spike_limit_mib: 64
      batch: {}
    exporters:
      awscloudwatchlogs:
        region: us-west-2
        log_group_name: ${env:LOG_GROUP_NAME}
        log_stream_name: ${env:K8S_NODE_NAME}
        log_retention: 30
        raw_log: false
        sending_queue:
          num_consumers: 2
          queue_size: 100
    service:
      extensions: [file_storage, health_check]
      pipelines:
        logs:
          receivers: [filelog]
          processors: [memory_limiter, batch]
          exporters: [awscloudwatchlogs]
```

container operator 会处理 CRI 封装/部分记录，并从 log.file.path 派生 Pod 元数据。对原始 CRI 行使用通用 JSON 解析器是不正确的。流名称通过 Downward API 节点名称和 Collector 环境变量替换获取，而不是使用不受支持的 {pod_name}.{container_name} 占位符。

Exporter 可以创建日志组/流，log_retention 适用于新建的日志组；现有保留期应由日志组所有者配置。其文档所述的 EMF 处理可能覆盖已配置的组/流名称，因此应限制 IAM 目标范围并检查实际数据格式。单靠配置字符串不能形成授权边界。

file_storage 保存接收器偏移量，而不是每个尚未导出的批次。此示例使用内存发送队列和有限重试；检查点状态、批次和 hostPath 数据的故障/生命周期行为各不相同。首次读取时，start_at=end 会跳过已有内容，除非存在已保存的偏移量。请监控重试、队列/丢弃/存储错误和节点轮转。本次未测试 Collector 进程、挂载、AWS 凭证流或数据摄取。

**分析和基础设施检查：**

对于源 Fluent Bit 架构，请使用实际的命名空间/容器字段检查结构化错误。ADOT 包装器或其他收集器可能会生成不同的存储架构：

```
fields @timestamp, @log, kubernetes.pod_name, data.level, data.message
| filter kubernetes.namespace_name = "default"
| filter toupper(data.level) = "ERROR"
| sort @timestamp desc
| limit 100
```

以下独立 Terraform 检查示例读取一个已存在且经过批准的 OpenSearch 域：

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.69.1"
    }
  }
}

variable "aws_region" {
  type    = string
  default = "us-west-2"
}

variable "opensearch_domain_name" {
  type        = string
  description = "Existing domain approved for this workload's logs"
}

provider "aws" {
  region = var.aws_region
}

data "aws_opensearch_domain" "eks_logs" {
  domain_name = var.opensearch_domain_name
}

output "opensearch_endpoint" {
  value = coalesce(
    data.aws_opensearch_domain.eks_logs.endpoint_v2,
    data.aws_opensearch_domain.eks_logs.endpoint
  )
}

output "opensearch_domain_arn" {
  value = data.aws_opensearch_domain.eks_logs.arn
}
```

此数据源不会配置网络、IAM/域策略、FGAC 或数据传送。请将管理与数据摄取分开，不要在代码/状态中存放主密码，并审核任何资源/地址迁移。查询和访问测试需要真实环境；Terraform 验证不会执行这些检查。

**其他选项为何不正确**：手动检查文件有助于诊断，但不是完整的集中式流水线。文件能否保留取决于容器/节点生命周期和卷类型。重复读取器可能导致数据/成本重复，而且仍可能失败；必须测量缓冲和重试的容量，并进行故障测试。

参考资料：[ADOT 组件](https://github.com/aws-observability/aws-otel-collector/tree/v0.50.0)、[容器解析器](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.158.0/pkg/stanza/docs/operators/container.md)、[CloudWatch Logs exporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.158.0/exporter/awscloudwatchlogsexporter)、[Fluentd OpenSearch 插件](https://github.com/fluent/fluent-plugin-opensearch)。

</details>

### 3. 哪种方法可以为 EKS 构建有效且可验证的告警路径？

- A. 假设手动查看日志可以保证立即发现问题。
- B. 创建一个 CloudWatch 告警，并假设它可以覆盖所有 Kubernetes/应用程序故障。
- C. 创建任意 alertmanager-config ConfigMap，并假设 Operator 会使用它。
- D. 选择所需信号，将指标/事件规则连接到已授权的接收方，并测试每条传送路径。

<details>
<summary>显示答案</summary>

**答案：D. 连接并验证所需的告警路径。**

**说明：**

CloudWatch 告警、Prometheus/Alertmanager 和 EventBridge 分别满足不同的信号/路由需求，可以经过规划后组合使用。CloudWatch 也支持应用程序/自定义指标，而 Prometheus 可以使用适当的 AWS exporter；不应以笼统的“仅限基础设施”说法否定任何一方。仅安装工具并不能建立指标覆盖范围、正确阈值、发布者权限或成功传送能力。

**指标规则必须匹配实际序列和单位：**

以下 PrometheusRule 使用源章节中的 KPS 选择器和实际的 node-exporter/kube-state-metrics 序列。CPU 和可用内存计算结果明确为百分比，因此 80 阈值有意义。CrashLoopBackOff 使用 waiting reason，而非任意重启；包括处于 Running 状态但 Ready=false 的 Pod，同时排除终止状态的 Pod。合并多个集群时应添加稳定的集群标识，并在部署重复规则前检查是否已有等效的捆绑规则：

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: eks-observability-alerts
  namespace: monitoring
  labels:
    release: monitoring
spec:
  groups:
  - name: eks-observability-example
    rules:
    - alert: NodeHighCPU
      expr: (100 * (1 - avg by (cluster, instance) (max by (cluster, instance, cpu) (rate(node_cpu_seconds_total{job="node-exporter",mode="idle"}[5m]))))) > 80
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: High non-idle CPU on {{ $labels.instance }}
        description: The node-exporter percentage has exceeded the example threshold; inspect workload and metric health.
    - alert: NodeMemoryFilling
      expr: (100 * (1 - max by (cluster, instance) (node_memory_MemAvailable_bytes{job="node-exporter"}) / max by (cluster, instance) (node_memory_MemTotal_bytes{job="node-exporter"}))) > 80 and on (cluster, instance) (max by (cluster, instance) (node_memory_MemTotal_bytes{job="node-exporter"}) > 0)
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Low available memory on {{ $labels.instance }}
        description: This is a MemAvailable-based estimate, not a MemoryPressure condition or Pod request utilization.
    - alert: KubernetesPodCrashLooping
      expr: max by (cluster, namespace, pod, uid, container) (max_over_time(kube_pod_container_status_waiting_reason{job="kube-state-metrics",reason="CrashLoopBackOff"}[5m])) >= 1
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: CrashLoopBackOff observed for {{ $labels.namespace }}/{{ $labels.pod }}
        description: Inspect container {{ $labels.container }} logs and events; the rule tracks recent waiting reasons, not a restart-count guarantee.
    - alert: PodNotReady
      expr: (max by (cluster, namespace, pod, uid) (kube_pod_status_ready{job="kube-state-metrics",condition="true"}) == 0) and on (cluster, namespace, pod, uid) (max by (cluster, namespace, pod, uid) (kube_pod_status_phase{job="kube-state-metrics",phase=~"Pending|Running|Unknown"}) == 1)
      for: 15m
      labels:
        severity: warning
      annotations:
        summary: Active Pod {{ $labels.namespace }}/{{ $labels.pod }} is not ready
        description: Inspect Ready conditions and probes; terminal Succeeded/Failed Pods are excluded from this example.
```

这些阈值和持续时间仅供说明。MemAvailable 用于估算可回收的可用内存；它不是 kubelet 的 MemoryPressure 条件，也不是 Pod 请求量的百分比。缺失或过期的序列并不代表健康/用量为零。请单独监控抓取失败和规则评估。

**连接实际的 Alertmanager 配置：**

请使用源文档中的 alertmanager-routing Secret（其键为 alertmanager.yaml）、alertmanager-values.yaml 以及 notification-credentials 挂载。请在该 Secret 中准备实际的 Slack webhook 和 PagerDuty Events API v2 路由密钥。对于原生 SNS，请为实际的 Alertmanager ServiceAccount 准备 AWS 身份，并授予限定主题范围的发布权限和适用的 KMS 权限；其他组件的 IRSA 角色不会自动共享。

使用前请替换示例 SNS 账户/Region/主题。此完整路由示例会将严重告警发送到 PagerDuty，将警告发送到 Slack，并将未匹配告警发送到 SNS；示例 Watchdog 路由会被丢弃，直到单独配置心跳监视器：

```yaml
global:
  resolve_timeout: 5m
route:
  group_by:
  - cluster
  - namespace
  - alertname
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: sns-notifications
  routes:
  - matchers:
    - alertname="Watchdog"
    receiver: discard
  - matchers:
    - severity="critical"
    receiver: pagerduty-notifications
  - matchers:
    - severity="warning"
    receiver: slack-notifications
receivers:
- name: discard
- name: slack-notifications
  slack_configs:
  - api_url_file: /etc/alertmanager/secrets/notification-credentials/slack-url
    channel: '#eks-alerts'
    send_resolved: true
    title: '[{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}'
    text: "{{ range .Alerts }}{{ .Annotations.summary }} \u2014 {{ .Annotations.description }}{{ \"\\n\" }}{{ end }}"
- name: sns-notifications
  sns_configs:
  - sigv4:
      region: us-west-2
    topic_arn: arn:aws:sns:us-west-2:123456789012:eks-alerts
    send_resolved: true
    subject: EKS {{ .CommonLabels.alertname }}
- name: pagerduty-notifications
  pagerduty_configs:
  - routing_key_file: /etc/alertmanager/secrets/notification-credentials/pagerduty-routing-key
    send_resolved: true
    severity: '{{ if eq .CommonLabels.severity "critical" }}critical{{ else }}warning{{ end }}'
    description: '{{ .CommonLabels.alertname }}'
```

默认接收方是备用接收方；当子路由匹配时，它不会自动扇出通知。只有确实需要扇出时，才配置 continue/显式的同级路由。请使用匹配版本的 amtool 验证完整文件，并测试路由标签。不需要未定义的 sns-forwarder 服务或包含凭证的 ConfigMap。

**CloudWatch 和 EventBridge 发布者权限：**

- 对于 Container Insights 告警，请使用源章节中的实际指标和维度。托管节点组名称不一定是 EC2 Auto Scaling 组名称；不要编造 AWS/EC2 维度值。
- CloudWatch 告警发布者需要相应的 SNS 主题策略。如果主题经过加密，AWS 文档指出 alias/aws/sns 不足以供 CloudWatch 告警使用；应使用客户托管的 KMS 密钥，其策略允许所需的发布者操作并附带适当限制。
- EventBridge 使用已发布的 EKS add-on 运行状况事件或受支持的 CloudTrail API 事件。EKS Cluster Control Plane Health 不在 EKS 直接事件目录中。API 调用成功不等于更新已完成。
- 对于 SNS 目标，请准备 EventBridge 执行角色或文档所述的资源策略替代方案。检查 PutTargets 失败和传送指标。主题存在或规则 API 调用成功都不能证明已成功传送。

**Terraform 规划示例：**

此独立示例引用一个由现有所有者管理的标准 SNS 主题和已准备好的目标角色。主题/密钥策略、订阅和实际 ContainerInsights 数据都是前提条件。节点 CPU 告警对所选 ClusterName 序列取 Maximum，而 add-on 事件规则覆盖整个账户/Region。告警操作和规则均已禁用，以供审核：

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
    }
  }
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Use the approved 12-digit AWS account ID."
  }
}

variable "cluster_name" {
  type = string
}

variable "sns_topic_arn" {
  type        = string
  description = "Prepared standard SNS topic with reviewed publisher/subscription/key permissions."
}

variable "eventbridge_role_arn" {
  type        = string
  description = "Prepared target execution role allowed to publish to the selected topic."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

resource "aws_cloudwatch_metric_alarm" "node_cpu" {
  alarm_name          = "${var.cluster_name}-node-cpu-warning"
  alarm_description   = "Example node CPU Maximum threshold; confirm actual ContainerInsights data."
  namespace           = "ContainerInsights"
  metric_name         = "node_cpu_utilization"
  dimensions          = { ClusterName = var.cluster_name }
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = 80
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "missing"
  actions_enabled     = false
  alarm_actions       = [var.sns_topic_arn]
}

resource "aws_cloudwatch_event_rule" "addon_health" {
  name_prefix = "eks-addon-health-"
  description = "Account/Region add-on health events; not filtered to a single cluster."
  state       = "DISABLED"
  event_pattern = jsonencode({
    source      = ["aws.eks"]
    account     = [var.account_id]
    region      = [var.region]
    detail-type = ["EKS Addon Health Degraded", "EKS Addon Health Restored"]
  })
}

resource "aws_cloudwatch_event_target" "sns" {
  rule      = aws_cloudwatch_event_rule.addon_health.name
  target_id = "ops-sns"
  arn       = var.sns_topic_arn
  role_arn  = var.eventbridge_role_arn
}
```

CPU 示例要求两个五分钟最大值都超出阈值，并不表示 80% 用量持续了十分钟。缺失数据不会被自动视为健康。在通过所有者的受控变更启用之前，请审核资源所有权、发布者访问权限、指标数据和预期通知。此片段不会创建/替换主题策略，也不会配置订阅；本次审计未针对 AWS 执行 plan/apply。

**SNS 订阅和可选 Lambda 处理：**

电子邮件订阅需要确认。Lambda 订阅需要在函数上授予针对预期 SNS 主题的权限；仅创建订阅并不会授予调用权限。对于标准主题，SNS 会异步调用 Lambda，并且可能发生重复处理。自定义适配器需要实际的传送代码、打包依赖项、受保护的凭证、输入验证、幂等性、失败/重试处理和可观测结果。

不要部署旧的占位处理程序：其中的发送函数只有 pass，然后返回“处理成功”。对于异步 SNS 调用，类似 HTTP 的 statusCode 返回值不是通知确认。应正确呈现传送失败，检查文档所述的 SNS 记录格式，并且不要根据任意 AlarmName 子字符串推断严重性。应分别配置订阅传送失败和 Lambda 执行失败。SQS 缓冲是另一种可选设计，需要实际的队列/事件源映射及其自身故障控制；架构示意图并不意味着已配置这些内容。

**正确区分的路径：**

```text
CloudWatch alarm -----------------------------> SNS -> confirmed subscribers
EventBridge rule -- authorized target role ---> SNS -> confirmed subscribers
Prometheus -> Alertmanager -- default --------> SNS
                         |-- warning --------> Slack
                         |-- critical -------> PagerDuty
Optional SNS subscriber -> implemented Lambda adapter -> chosen external channel
```

对相关告警进行分组，限制重复通知频率，明确定义严重性/响应时限，包含证据和影响，并在获批的测试目标中测试具有代表性的触发/解决及故障路径。安装一组工具并不意味着实现了完整覆盖或成功传送。本次审计未创建/执行任何主题、订阅、告警、Lambda 调用或通知。

参考资料：[源章节](../../eks/06-eks-monitoring-logging.md)、[Alertmanager 接收方](https://prometheus.io/docs/alerting/latest/configuration/)、[EKS 事件](https://docs.aws.amazon.com/eventbridge/latest/ref/events-ref-eks.html)、[SNS/Lambda](https://docs.aws.amazon.com/lambda/latest/dg/with-sns.html)、[CloudWatch 告警使用加密 SNS](https://repost.aws/knowledge-center/cloudwatch-configure-alarm-sns)。

</details>

### 4. 哪种应用程序可观测性设计能够保留有用的证据？

- A. 将节点 CPU 单独视为能够证明所有应用程序延迟原因的依据。
- B. 将所有传入的 service.name 属性覆盖为同一个共享的 Collector 名称。
- C. 关联所选指标、日志和跟踪数据，同时保留服务身份并验证其实际路径。
- D. 假设 10% 的头部采样器始终会保留每个错误请求和慢请求。

<details>
<summary>显示答案</summary>

**答案：C. 关联经过验证的信号路径，同时不合并服务身份。**

**说明：**

指标描述速率/分布/资源状态，日志提供事件细节，跟踪数据则连接经过检测的操作。它们有助于调查，但不能保证全面可见性或证明根本原因。如果显式启用并审核，性能剖析可以补充 CPU/分配/堆证据；并非每个跟踪收集器都会自动提供此功能。

**使用正确的 Collector 和信号路由：**

使用源章节中由你负责的 Operator0.158/ADOT0.50 TLS 仅跟踪配置，以及问题 2 中单独限定范围的日志替代方案。Operator 清单来自 Operator 自身的发布包，而非 Collector 发布资源。应在应用程序边界保留 service.name；共享资源处理器不得用一个全局值覆盖 order-service、payment-service 和其他调用方的名称。

对于 Prometheus 指标，请使用源文档中已连线的 ServiceMonitor/Service 路径，或单独验证 Prometheus receiver。仅靠注解发现并不会配置正确的端口/路径、RBAC 或副本目标分布。awsemf 会导出到 CloudWatch，而 AMP 需要真实的 remote-write 端点和 SigV4 身份。如果配置中只有 awsemf，就不要画出 AMP 路径。

**Java 检测示例：**

OpenTelemetry Java agent 上游版本是 Spring Boot starter 的一种替代方案。经过检查的版本为 2.31.1；请通过应用程序构建流程准备经过审核的 JAR 和兼容的应用程序/JVM。这样可以避免在 Java 源代码块中混合 Gradle 声明和 application.properties，也避免复制与版本不匹配的 1.18-alpha starter。对于已由 CloudWatch Auto Monitor 或其他所有者检测的进程，不要再添加另一个 agent。

这是应用程序运行时配置，不是审计测试命令。它为源文档中的 TLS receiver 选择 OTLP/HTTP 跟踪数据，并关闭这些独立路径的 SDK 指标/日志导出。请挂载可信 CA，并保留其他必需的 JVM 启动选项：

```bash
set -euo pipefail
: "${OTEL_JAVA_AGENT_JAR:?Set the reviewed OpenTelemetry Java agent 2.31.1 JAR path}"
: "${APP_JAR:?Set the application JAR path}"
test -r "$OTEL_JAVA_AGENT_JAR"
test -r "$APP_JAR"
export OTEL_SERVICE_NAME=order-service
export OTEL_RESOURCE_ATTRIBUTES=k8s.cluster.name=my-owned-cluster
export OTEL_TRACES_EXPORTER=otlp
export OTEL_METRICS_EXPORTER=none
export OTEL_LOGS_EXPORTER=none
export OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://adot-traces-collector.tracing-demo.svc:4318/v1/traces
export OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE=/etc/otel/ca.crt
export OTEL_PROPAGATORS=tracecontext,baggage
export OTEL_TRACES_SAMPLER=parentbased_traceidratio
export OTEL_TRACES_SAMPLER_ARG=0.1
java "-javaagent:$OTEL_JAVA_AGENT_JAR" -jar "$APP_JAR"
```

Java agent2.x 默认使用 http/protobuf；此示例明确指定了该选择。特定信号的 HTTP 端点包含 /v1/traces。4317 gRPC 端点使用不同协议，不能只更改端口就代替使用。已验证发布/配置元数据；本次未运行 Java agent、JDK 或应用程序。

**Python 检测示例：**

请将源文档中的 RequestTracing 适配器与 Python3.10+ 及匹配的 SDK/HTTP exporter1.44.0 配合使用。在 payment 应用程序环境中设置以下值，替换示例集群名称并挂载可信 CA：

```bash
export OTEL_SERVICE_NAME=payment-service
export CLUSTER_NAME=my-owned-cluster
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://adot-traces-collector.tracing-demo.svc:4318/v1/traces
export OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE=/etc/otel/ca.crt
```

下面再次列出此适配器，以明确其生命周期和请求边界：

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

在应用程序启动时创建一个实例，在真实框架处理程序中使用规范化的传入标头名称和实际业务操作调用 handle_request，并在正常关闭时调用 close。这不是 Flask 服务器或支付业务实现；不会默认假设 app/request/jsonify/process_transaction 存在。应通过框架支持的机制，将给定上下文传播到真实的出站调用和异步工作中。

本次审计在禁用 SDK 导出的情况下测试了此适配器，包括业务结果/错误保留以及纯上下文传播/采样检查。这并不能证明实时 Span 导出或已部署 Collector 正常工作。

**匹配 IRSA 信任、权限和 ServiceAccount：**

以下独立 Terraform 示例与源 Collector 的 tracing-demo/adot-traces 身份相匹配。它使用声明的输入和一个针对实际集群签发者、已存在的 IAM OIDC provider。信任条件同时包含 sub 和 aud。X-Ray PutTraceSegments 没有资源级 ARN 范围，因此策略使用必需的通配符资源，同时限制操作/Region 并限定信任范围。此配置不会授予无关的 CloudWatch 或 AMP 权限：

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
    }
  }
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Use the approved 12-digit AWS account ID."
  }
}

variable "cluster_oidc_issuer_url" {
  type        = string
  description = "The actual EKS cluster OIDC issuer URL; its IAM OIDC provider must already exist."
  validation {
    condition     = startswith(var.cluster_oidc_issuer_url, "https://")
    error_message = "Use the HTTPS issuer returned by the owned cluster."
  }
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

data "aws_partition" "current" {}

locals {
  oidc_hostpath     = trimsuffix(trimprefix(var.cluster_oidc_issuer_url, "https://"), "/")
  oidc_provider_arn = "arn:${data.aws_partition.current.partition}:iam::${var.account_id}:oidc-provider/${local.oidc_hostpath}"
}

resource "aws_iam_role" "adot_traces" {
  name = "adot-traces-example"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = local.oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.oidc_hostpath}:aud" = "sts.amazonaws.com"
          "${local.oidc_hostpath}:sub" = "system:serviceaccount:tracing-demo:adot-traces"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "xray_write" {
  name = "xray-trace-write"
  role = aws_iam_role.adot_traces.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["xray:PutTraceSegments"]
      Resource = "*"
      Condition = {
        StringEquals = { "aws:RequestedRegion" = var.region }
      }
    }]
  })
}

resource "aws_xray_group" "applications" {
  group_name        = "EKS-Applications"
  filter_expression = "service(\"order-service\") OR service(\"payment-service\")"
}

output "adot_traces_role_arn" {
  value = aws_iam_role.adot_traces.arn
}
```

创建 Collector 之前，可以在已准备好的命名空间中以原子方式创建新的、由你负责的 ServiceAccount，并为其添加角色注解。已有 ServiceAccount/角色需要遵循其所有者的更新/导入流程；不要覆盖其他身份或关联不相关的 Pod Identity：

```bash
set -euo pipefail
: "${ADOT_ROLE_ARN:?Set the reviewed role ARN from the owned Terraform stack}"
python3 - "$ADOT_ROLE_ARN" <<'PY' | kubectl create -f -
import json
import sys
print(json.dumps({
    "apiVersion": "v1",
    "kind": "ServiceAccount",
    "metadata": {
        "name": "adot-traces",
        "namespace": "tracing-demo",
        "annotations": {"eks.amazonaws.com/role-arn": sys.argv[1]},
    },
}))
PY
```

更改注解不会将凭证追溯性地注入正在运行的 Pod；请审核是否需要重新部署。验证实际签发者/provider、令牌受众、被代入角色和网络路径。X-Ray group 会筛选匹配的跟踪数据；它不会检测应用程序，也不会授予 Collector 权限。请使用问题 1 中的工作区/数据源设置，而不要重复一个不完整的 AMG 创建命令。本次审计未创建 IAM 角色/group/ServiceAccount。

**Browser RUM 是独立路径：**

CloudWatch RUM web 客户端会将 PutRumEvents 数据发送到 CloudWatch RUM，而不会自动发送到 ADOT OTLP receiver。启用 X-Ray 跟踪时，它可以向允许的 HTTP 请求添加 X-Amzn-Trace-Id。客户端/服务器跟踪默认不会关联：请审核受支持的服务器传播/桥接方式和 CORS 允许的标头。上面的纯 W3C 示例不会自动使用 X-Ray 标头。通用 OpenTelemetry 浏览器客户端需要单独设计受支持的 OTLP 端点/身份验证/CORS。

```text
Browser CloudWatch RUM client -----> CloudWatch RUM
                 | optional X-Ray header/segment integration
Java order-service <--- propagated requests ---> Python payment-service
       | OTLP/HTTP TLS                              | OTLP/HTTP TLS
       +--------------> ADOT traces collector <-----+
                              |
                              v
                            X-Ray
Application metrics -> configured Prometheus -> optional SigV4 remote_write -> AMP
Application stdout  -> chosen log collector -> configured log store
Grafana/AMG         -> queries the configured data sources
```

**覆盖范围、采样和隐私：**

- 使用明确定义的样本总体/时间窗口测量延迟分布、吞吐量、错误率和饱和度。采样后的跟踪数据集不会自动成为无偏的指标分布。
- 使用有界服务名称、规范化路由、版本/环境以及集群/命名空间身份。客户/租户 ID 和原始请求 URL 可能导致基数和隐私问题；不应将它们设为默认指标标签。
- 头部采样会在请求最终结果确定之前做出决定，无法保证保留所有错误/慢请求；尾部采样也无法恢复已在上游丢弃的 Span。尾部采样需要按跟踪亲和性路由，并需要足够的缓冲区/时间窗口。
- RUM 会话/用户数据、日志、Span 和性能剖析数据需要适当的访问控制、同意/收集策略和保留期。关联 ID 是元数据，不是身份验证。
- 性能测试和性能剖析可补充运行时信号。此处示例不表示已取得任何新的基准测试或生产性能结果。

参考资料：[Java agent 配置](https://opentelemetry.io/docs/zero-code/java/agent/configuration/)、[Java SDK 配置](https://opentelemetry.io/docs/languages/java/configuration/)、[CloudWatch RUM/X-Ray](https://docs.aws.amazon.com/xray/latest/devguide/xray-services-RUM.html)、[源章节](../../eks/06-eks-monitoring-logging.md)。

</details>

### 5. 应如何监控 AWS 托管的 EKS 控制平面日志？

- A. 直接 SSH 到 AWS 托管的控制平面节点。
- B. 配置所需的 EKS 日志类型，验证日志是否传送到 CloudWatch Logs，并应用适当的查询/访问控制。
- C. 假设工作节点上的 DaemonSet 可以读取托管控制平面文件系统。
- D. 创建日志仪表板，并假设它会自动发布 ErrorCount 指标。

<details>
<summary>显示答案</summary>

**答案：B. 配置并验证托管日志路径。**

**说明：**

EKS 会将选定的控制平面日志类型直接发送到账户中的 CloudWatch Logs。工作节点收集器不是这些托管日志的来源。这样可以在无需 SSH 到控制平面的情况下获取诊断/审计证据，但不能保证记录每次 API 调用，也不能证明符合要求。审计策略、阶段、启用时间、摄取和保留期决定了哪些内容可用。

**日志类型及范围：**

| 类型 | 用途 |
| --- | --- |
| api | API server 诊断和错误；不是完整的请求/响应存档 |
| audit | 记录的 Kubernetes API 审计事件以及身份/资源/状态字段 |
| authenticator | IAM 身份验证/映射诊断；应区分身份验证和 RBAC 授权 |
| controllerManager | 控制器协调诊断 |
| scheduler | 调度决策/失败及相关诊断 |

请先检查现有集群配置。对于获批的全部五种类型变更，源章节中的更新操作会捕获更新 ID 并检查状态；请继续检查直到成功，然后验证实际日志传送：

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{ARN:arn,Status:status,Logging:logging}'
```



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

最后的 DescribeUpdate 调用只是状态检查，不是等待器或摄取测试。只选择部分类型时，请保留所有现有的必需类型；不要为了启用 api/audit 而复制一个显式禁用 authenticator/controllerManager/scheduler 的代码块。对于新集群，请在经过审核的创建/IaC 配置中包含日志记录设置。不要仅为了配置监控而再创建一个不完整的集群。源文档中说明了 EKS Capabilities controller logs 使用的独立传送路径。

**查询实际 JSON 字段：**

选择由你负责的 /aws/eks/CLUSTER/cluster 组和有界时间范围。以下是已记录的 5xx 响应示例：

```
fields @timestamp, auditID, user.username, verb, objectRef.resource, responseStatus.code
| filter apiVersion = "audit.k8s.io/v1" and stage = "ResponseComplete"
| filter responseStatus.code >= 500
| sort @timestamp desc
| limit 100
```

对于已知审计用户名，应使用嵌套 JSON 字段，而不是解析字面的 user.username 字符串。请将示例用户名替换为记录中实际观察到的身份：

```
fields @timestamp, auditID, user.username, verb, objectRef.resource, responseStatus.code
| filter apiVersion = "audit.k8s.io/v1"
| filter user.username = "example-user"
| sort @timestamp desc
| limit 100
```

在定义特定格式的失败筛选条件之前，请先检查 authenticator 记录。包含 failed/denied 的子字符串可能会漏掉实际案例或匹配无关文本；单独一条 IAM 身份验证消息也无法说明所有 Kubernetes 授权结果。

**仪表板不会发布指标：**

Logs Insights 小组件会运行查询。自定义指标上的告警需要实际发布者，例如指标筛选器。下面的独立 Terraform 示例将 STANDARD 日志组、筛选器、指标、告警和仪表板连接起来。使用此配置之前，请通过实际所有者管理/导入已有日志组；KMS 密钥以及 SNS 主题/发布者权限必须已准备好。它不会创建新的 EKS 集群或 KMS 密钥。

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
    }
  }
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
}

variable "cluster_name" {
  type = string
}

variable "logs_kms_key_arn" {
  type        = string
  description = "Prepared symmetric key in the log-group Region with reviewed Logs/caller permissions."
}

variable "sns_topic_arn" {
  type        = string
  description = "Prepared standard SNS topic with confirmed subscriptions and publisher/key permissions."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

locals {
  metric_namespace = "EKS/ControlPlane"
  metric_name      = "${var.cluster_name}-AuditResponse5xxCount"
  filter_pattern   = "{ ($.apiVersion = \"audit.k8s.io/v1\") && ($.stage = \"ResponseComplete\") && ($.responseStatus.code >= 500) }"
}

resource "aws_cloudwatch_log_group" "control_plane" {
  name              = "/aws/eks/${var.cluster_name}/cluster"
  log_group_class   = "STANDARD"
  retention_in_days = 90
  kms_key_id        = var.logs_kms_key_arn
}

resource "aws_cloudwatch_log_metric_filter" "audit_5xx" {
  name           = "${var.cluster_name}-audit-response-5xx"
  log_group_name = aws_cloudwatch_log_group.control_plane.name
  pattern        = local.filter_pattern

  metric_transformation {
    namespace     = local.metric_namespace
    name          = local.metric_name
    value         = "1"
    default_value = 0
    unit          = "Count"
  }
}

resource "aws_cloudwatch_metric_alarm" "audit_5xx" {
  alarm_name          = "${var.cluster_name}-audit-response-5xx"
  alarm_description   = "Example threshold for ingested audit ResponseComplete records with code>=500."
  namespace           = local.metric_namespace
  metric_name         = local.metric_name
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = 10
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "missing"
  actions_enabled     = false
  alarm_actions       = [var.sns_topic_arn]
}

resource "aws_cloudwatch_dashboard" "control_plane" {
  dashboard_name = "${var.cluster_name}-control-plane"
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "log"
        x      = 0
        y      = 0
        width  = 24
        height = 6
        properties = {
          region = var.region
          title  = "Recorded audit 5xx responses per five minutes"
          view   = "timeSeries"
          query  = "SOURCE '${aws_cloudwatch_log_group.control_plane.name}' | fields @timestamp\n| filter apiVersion = \"audit.k8s.io/v1\" and stage = \"ResponseComplete\" and responseStatus.code >= 500\n| stats count(*) as recordedResponses by bin(5m)"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 24
        height = 6
        properties = {
          region  = var.region
          title   = "Metric filter: new ingested audit 5xx records"
          view    = "timeSeries"
          metrics = [[local.metric_namespace, local.metric_name]]
          period  = 300
          stat    = "Sum"
        }
      }
    ]
  })
}
```

此筛选器会统计新摄取的、responseStatus.code>=500 的审计 ResponseComplete 记录。以集群名称为前缀的指标名称可以区分集群，而无需虚构审计 JSON 中不存在的 ClusterName 维度。筛选器、告警和指标小组件使用完全相同的命名空间/名称，且不带维度。仪表板查询可能涵盖较早记录，但指标筛选器不会回填历史数据。这些是已记录事件的计数，不是 API 错误率或去重后的请求总数；可能会发生重复传送。

当日志到达但没有任何匹配记录时，会发出 default_value 为 0 的值；没有传入日志时，数据仍可能缺失。指标筛选器不能同时使用默认值和维度。此处的告警会在禁用操作的情况下启动，明确处理缺失数据，并使用示例阈值。启用之前，请验证新的指标数据点、权限、订阅和受控传送测试。

jsonencode 避免了旧仪表板命令中错误的 shell 引号。如果改用 CLI，请传入有效 JSON 文件，并使用 --dashboard-body file://dashboard.json，然后检查 DashboardValidationMessages。PutDashboard 会替换现有内容；请保留其所有者的组件和配置。本地 HCL/JSON 验证并未执行 AWS 筛选器/查询引擎。

**KMS 和保留期：**

CloudWatch Logs 默认会加密日志数据。关联客户托管的对称 KMS 密钥会更改新摄取数据的加密方式；它并不是第一层加密，也不会重新加密旧记录。请使用位于日志组所在 Region 的密钥，在仍需要旧数据时保留旧密钥/权限，并区分关联密钥的权限和读取权限。取消关联后，新数据会恢复为默认加密方式；禁用/删除旧密钥可能会使其保留的数据无法读取。

Logs 区域服务需要使用密钥的权限。以下只是供密钥所有者合并到现有策略中的语句片段；请保留管理员/委派语句。请一致地替换每个示例标识符；不要将它用作完整替代密钥策略：

```json
{
  "Sid": "AllowLogsServiceForOneGroup",
  "Effect": "Allow",
  "Principal": {
    "Service": "logs.us-west-2.amazonaws.com"
  },
  "Action": [
    "kms:Encrypt",
    "kms:Decrypt",
    "kms:ReEncrypt*",
    "kms:GenerateDataKey*",
    "kms:DescribeKey"
  ],
  "Resource": "*",
  "Condition": {
    "ArnEquals": {
      "kms:EncryptionContext:aws:logs:arn": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/my-cluster/cluster"
    }
  }
}
```

加密上下文中的日志组 ARN 末尾没有 :*。关联密钥的操作者需要文档所述的 Logs 权限和 kms:DescribeKey。读取/写入调用方需要通过区域 Logs 服务获得其操作所需的 KMS 权限。轮换密钥或设置较短的删除等待期并不会消除为历史数据保留解密访问权限的要求。保留期 90 天仅为示例，并不代表符合规范或不可变保证。

**正确限定读取访问权限：**

以下示例身份策略允许访问选定组及其流，并允许通过 Logs 解密一个密钥。密钥策略也必须允许预期主体使用该密钥。它不会授予日志管理或密钥管理操作：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadAndQueryThisLogGroup",
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogStreams",
        "logs:FilterLogEvents",
        "logs:StartQuery",
        "logs:GetQueryResults"
      ],
      "Resource": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/my-cluster/cluster:*"
    },
    {
      "Sid": "ReadThisGroupStreams",
      "Effect": "Allow",
      "Action": "logs:GetLogEvents",
      "Resource": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/my-cluster/cluster:log-stream:*"
    },
    {
      "Sid": "DecryptThisGroupsDataViaLogs",
      "Effect": "Allow",
      "Action": "kms:Decrypt",
      "Resource": "arn:aws:kms:us-west-2:123456789012:key/11111111-2222-3333-4444-555555555555",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "logs.us-west-2.amazonaws.com"
        },
        "ArnEquals": {
          "kms:EncryptionContext:aws:logs:arn": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/my-cluster/cluster"
        }
      }
    }
  ]
}
```

当前 AWS 授权文档支持对 StartQuery 和 GetQueryResults 进行日志组范围限定；不要因旧假设而将其范围扩大到 Resource:*。DescribeLogStreams 和 FilterLogEvents 是组级操作，而 GetLogEvents 是流级操作。对于大多数 IAM 操作，AWS 的 LogGroup ARN 格式包含 :*；logGroupArn 以及加密上下文/标签用途则不包含。控制台/发现工作流可能需要额外的读取操作；DescribeLogGroups 是单独限定范围的权限，不支持资源级 ARN，且上面的策略并未隐式授予该权限。

本次审计未更改/执行集群日志、日志保留期、密钥策略、指标筛选器、仪表板、告警或云端查询。参考资料：[CloudWatch 指标筛选器](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/MonitoringLogData.html)、[LogGroup ARN 格式](https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_LogGroup.html)、[Logs IAM 操作](https://docs.aws.amazon.com/service-authorization/latest/reference/list_logs.html)、[KMS 日志加密](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/encrypt-log-data-kms.html)。

</details>

### 6. 哪种监控策略最有助于优化 Amazon EKS 的成本？

- A. 无论是否有用，都收集所有可用指标
- B. 结合资源使用情况、账单分摊和经所有者审核的浪费候选项
- C. 监控性能，但不检查支出
- D. 只查看最终月度账单

<details>
<summary>显示答案</summary>

**答案：B. 结合资源使用情况、账单分摊和经所有者审核的浪费候选项**

**说明**：将 CPU、内存、存储、请求、限制和工作负载趋势与分摊成本进行比较。与资源所有者一起调查异常和预算偏差。这些信号可以帮助发现优化机会，但不能保证节省成本，也不能证明可以删除某项资源。

**资源效率和成本分摊**

复用源指南中的 kube-prometheus-stack 安装、kube-state-metrics 和经过验证服务证书的 kubelet ServiceMonitor。cAdvisor 使用 kubelet HTTPS 指标端口上的 `/metrics/cadvisor`；它不是名为 `cadvisor` 的独立 Service 端口。不要添加重复的 monitor，也不要为了让抓取正常运行而禁用 TLS 验证。

以下 CPU 和内存表达式返回**每个容器的使用量/请求量比率**，而不是节点容量利用率或货币成本。比率可能大于 1。请求量为零/缺失时，不会产生比率，而不是产生零用量。`max` 会根据列出的身份信息删除重复抓取副本；请确认这些副本实际上代表同一工作负载。此示例针对单个集群的本地 Prometheus。对于共享后端，两个指标系列都必须带有一致的集群标签。解读时间范围时还需注意 Pod 名称重用和容器重启。这些容器指标并不描述 Pod 级资源、init 容器或 Pod 开销的完整调度预留量。

```promql
max by (cluster, namespace, pod, container) (
  rate(container_cpu_usage_seconds_total{job="kubelet",metrics_path="/metrics/cadvisor",namespace!="",container!="",container!="POD"}[5m])
)
/ on (cluster, namespace, pod, container)
(
  max by (cluster, namespace, pod, container) (
    kube_pod_container_resource_requests{job="kube-state-metrics",resource="cpu",unit="core",container!=""}
  ) > 0
)
```

```promql
max by (cluster, namespace, pod, container) (
  container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",namespace!="",container!="",container!="POD"}
)
/ on (cluster, namespace, pod, container)
(
  max by (cluster, namespace, pod, container) (
    kube_pod_container_resource_requests{job="kube-state-metrics",resource="memory",unit="byte",container!=""}
  ) > 0
)
```

在 Grafana 中使用现有的 Prometheus 数据源和这些查询创建两个面板；将仪表板命名为**资源使用量与请求量对比**，使用比率/百分比单位，并保留 cluster、namespace、Pod 和 container 身份。包含未指定 `cost-dashboard.json` 的 ConfigMap 不会创建可用的仪表板。使用源指南中的 Grafana sidecar 时，要通过预配方式提供经过审核的 JSON 仪表板，还必须使用已配置的 `grafana_dashboard: "1"` 标签。

**OpenCost 或 Kubecost**

对于使用源指南中现有 Prometheus 进行新的 OpenCost 评估，请将以下内容保存为 `opencost-values.yaml`。检查过的 chart 版本为 **2.5.31**，应用程序版本为 **1.121.2**。请设置实际集群 ID 和 Prometheus URL。其 ServiceMonitor 标签必须与 Prometheus 选择器匹配；命名空间选择范围必须允许 `opencost` 命名空间。此配置不会再安装一套 Prometheus/node exporter。

```yaml
service:
  type: ClusterIP
opencost:
  exporter:
    defaultClusterId: my-cluster
  prometheus:
    internal:
      enabled: false
    external:
      enabled: true
      url: http://monitoring-kube-prometheus-prometheus.monitoring.svc:9090
  metrics:
    serviceMonitor:
      enabled: true
      additionalLabels:
        release: monitoring
  cloudCost:
    enabled: false
  mcp:
    enabled: false
  ui:
    enabled: true
    ingress:
      enabled: false
```

```bash
helm repo add opencost https://opencost.github.io/opencost-helm-chart
helm repo update opencost
helm template opencost opencost/opencost --version 2.5.31 \
  --namespace opencost -f opencost-values.yaml > opencost-rendered.yaml
# After reviewing RBAC, images, resources, selectors, and network access:
helm install opencost opencost/opencost --version 2.5.31 \
  --namespace opencost --create-namespace -f opencost-values.yaml
kubectl -n opencost port-forward --address 127.0.0.1 svc/opencost 9090:9090
```

port-forward 运行时，请打开 `http://localhost:9090`。此基线使用临时 exporter 缓存，禁用 Cloud Cost 摄取和 MCP，并且只公开 ClusterIP Service。在共享使用之前，请审核持久性、容量、身份验证/网络访问、RBAC 和抓取运行状况；ClusterIP 不是租户授权边界。按需价格估算需要根据实际账单、折扣、Spot 价格、抵扣额、共享成本、存储和网络费用进行核对。AWS 账单集成需要单独配置；受支持的 AWS 服务账户/默认 SDK 身份验证不需要嵌入长期访问密钥。

Kubecost 是另一种独立选择。检查过的 **3.3.1** chart 来自 `https://kubecost.github.io/kubecost/` 中的 `kubecost/kubecost`。旧的 `cost-analyzer` 存储库和 2.x Prometheus 值并不是 3.x 安装方案：3.x 使用 ClickHouse 和 finops-agent 直接收集。请在安装或升级前审核其许可证、存储、Kubernetes 兼容性以及文档所述的 2.x 迁移。请参阅配套的 [FinOps 平台指南](../../ops/13-finops-cost-platform.md)和 [Kubecost chart 文档](https://github.com/kubecost/cost-analyzer-helm-chart)。

**标签、账单标签和类别**

命名空间标签有助于 Kubernetes 侧的分组：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
  labels:
    team: team-a
    cost-center: cc-123
    environment: production
```

这些标签不会自动标记 EC2/EBS 资源，也不会激活 AWS 账单标签。账单所有者必须应用实际的 AWS 资源标签，然后激活符合条件的成本分摊键。请考虑账单处理延迟，并在 Cost Explorer/CUR 中验证标签是否出现。AWS split cost allocation 是一条单独的选择启用路径，会生成 EKS Pod 级记录和 AWS 生成的属性（例如 `aws:eks:namespace`）；它不会将每个命名空间标签都变成 EC2 标签。请审核其数据源前提条件以及增加的报告量。

只在资源过去确实已标记的情况下，成本分摊标签回填才能涵盖最多 12 个月；它无法生成缺失的历史标签。Cost Category 使用经过审核的规则对账单记录分类；它不是仪表板。其 CLI 创建操作为 `aws ce create-cost-category-definition`，而非 `create-cost-category`。请使用账单数据集中实际出现的键和值，并单独配置已保存的 Cost Explorer 报告或仪表板。

**未挂载卷的只读清单**

仅在目标账户/Region 和已有所有权标签符合预期时运行以下命令。它会保留 AWS CLI 分页功能，并输出 JSON 候选列表。有限的标签语法是有意设置的；如果实际标签包含其他字符，请调整 JSON 筛选条件。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the reviewed Region}"
: "${EXPECTED_ACCOUNT_ID:?Set the reviewed 12-digit account ID}"
: "${OWNER_TAG_KEY:?Set an existing ownership tag key}"
: "${OWNER_TAG_VALUE:?Set its exact value}"
[[ "$EXPECTED_ACCOUNT_ID" =~ ^[0-9]{12}$ ]]
# This example accepts a restricted literal subset, excluding wildcards/shorthand separators.
[[ "$OWNER_TAG_KEY" =~ ^[a-zA-Z0-9_./:@+-]+$ ]]
[[ "$OWNER_TAG_VALUE" =~ ^[a-zA-Z0-9_./:@+-]+$ ]]
actual_account=$(aws sts get-caller-identity --region "$AWS_REGION" \
  --query Account --output text --no-cli-pager)
[[ "$actual_account" == "$EXPECTED_ACCOUNT_ID" ]] || {
  echo "Account mismatch" >&2
  exit 1
}
aws ec2 describe-volumes --region "$AWS_REGION" --page-size 100 \
  --filters Name=status,Values=available \
    "Name=tag:$OWNER_TAG_KEY,Values=$OWNER_TAG_VALUE" \
  --query 'Volumes[].{id:VolumeId,zone:AvailabilityZone,sizeGiB:Size,created:CreateTime,state:State}' \
  --output json --no-cli-pager
```

`available` 表示当前未挂载，不代表未使用或可以安全删除。创建时间不是最后使用时间。请与所有者一起检查 PV/PVC 所有权、回收策略、待处理工作负载、备份、快照和灾难恢复要求。同样，CPU/内存用量低（包括任意的 5% 截止值）并不能证明某个 Pod 或负载均衡器没有必要。请使用具有代表性的历史数据和应用程序/SLO 信号；不要将缺失指标替换为空的“空闲 Pod”结果。

**预算示例**

此独立 Terraform 示例使用真实且已激活的账单标签和经过批准的接收方。**每月 1,000 USD 限额和 80% 告警**仅为示例设置，并非观察到的成本。请导入/核对已有预算，而不是创建冲突的所有者。验证所选成本计算依据和标签覆盖情况；标签筛选器可能会漏掉未标记/共享费用。应用此示例会创建真实通知配置。

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
    }
  }
}

variable "account_id" {
  type = string
}

variable "region" {
  type = string
}

variable "budget_name" {
  type = string
}

variable "activated_tag_key" {
  type = string
}

variable "tag_value" {
  type = string
}

variable "notification_email" {
  type        = string
  description = "Approved budget owner; applying this example configures real email notifications."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

resource "aws_budgets_budget" "eks_monthly" {
  account_id   = var.account_id
  name         = var.budget_name
  budget_type  = "COST"
  limit_amount = "1000"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "TagKeyValue"
    values = [join("$", [var.activated_tag_key, var.tag_value])]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.notification_email]
  }
}
```

预算使用经过处理的账单数据，不会强制执行支出上限。Budget Actions 可以应用 IAM/SCP 控制或针对受支持的 EC2/RDS 实例执行操作，但需要单独的权限和运维审核。上面的资源效率仪表板不是账单仪表板。

请结合 VPA 建议以及峰值/SLO 历史审核请求，并协调 HPA 与节点扩缩容。只有在工作负载、中断、容量和干扰约束允许时，Karpenter/Cluster Autoscaler 和 Spot 才可能降低成本。仅缩小请求量并不会减少账单，除非已预置的容量或定价发生变化。请在定期所有者审核中跟踪商定的操作和测量结果。

其他选项无法形成此反馈闭环：收集所有数据会增加遥测成本/噪声；仅关注性能无法显示支出；等到最终月度账单才查看会错过及时调查的时机。

**主要参考资料：**[OpenCost 安装](https://opencost.io/docs/installation/helm)、[AWS 标签激活](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/activating-tags.html)、[标签回填](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-allocation-backfill.html)、[split cost allocation](https://docs.aws.amazon.com/cur/latest/userguide/split-cost-allocation-data.html)、[Budget Actions](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-controls.html)。

</details>

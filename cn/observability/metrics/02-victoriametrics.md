# VictoriaMetrics

> **审查基线**：VictoriaMetrics 1.151.0 · stack chart 0.92.1
> **最后更新**：2026 年 9 月 12 日

## 目录

- [简介](#introduction)
- [架构选项](#architecture-options)
- [单节点模式](#single-node-mode)
- [集群模式](#cluster-mode)
- [vmagent](#vmagent)
- [vmalert](#vmalert)
- [MetricsQL](#metricsql)
- [Helm 安装](#helm-installation)
- [长期存储配置](#long-term-storage-configuration)
- [降采样](#downsampling)
- [性能优化](#performance-optimization)
- [最佳实践](#best-practices)
- [故障排除](#troubleshooting)

## 简介 {#introduction}

VictoriaMetrics 用于存储和查询时间序列，并提供独立的采集工具（`vmagent`）和规则评估工具（`vmalert`）。它支持 Prometheus remote write，并提供兼容 Prometheus 的查询端点。**MetricsQL 有意与 PromQL 存在差异**，因此迁移时应使用实际查询和数据进行比较，不要假定两者结果相同，也不要假定 VictoriaMetrics 支持每个 Prometheus API。

本章审查 VictoriaMetrics **1.151.0** 和 **victoria-metrics-k8s-stack 0.92.1**。原生测试使用小型本地数据集；清单和 chart 经过检查或渲染。本章不声称在真实 EKS 上部署、执行云端备份、进行负载测试或验证故障恢复。

### 比较与测量

| 维度 | 比较要点 |
|---|---|
| 部署 | Prometheus 将抓取、本地 TSDB 和规则集中在一起；VictoriaMetrics 的单节点存储/查询及可选 agent 可分开部署。集群模式将写入、存储和查询拆分。 |
| 压缩与速度 | 使用相同的数据集、摄取速率、序列 churn、查询范围、缓存状态和硬件进行测量。不存在不依赖工作负载的 7 倍压缩、20 倍速度或节省 70% 的保证。 |
| 基数 | 活跃序列、churn、标签、查询扇出、RAM 和磁盘共同决定容量。两个产品都没有通用的“1000 万对 1 亿”序列分界线。 |
| 保留期 | Prometheus 默认保留期不是其最大保留期。VictoriaMetrics 的保留期可配置，但仍会消耗有限的存储空间。 |
| 查询语言 | MetricsQL 支持许多熟悉的 PromQL 表达式，但在 rate/increase、NaN、scalar 和指标名处理方面存在文档说明的差异。 |
| 租户与访问 | 集群租户 ID 用于区分数据命名空间，但不会验证调用者身份。应限制访问，并使用经过审查的身份验证/授权网关（例如 vmauth）。 |
| 降采样 | 区分 Enterprise 存储降采样、摄取时 stream aggregation，以及记录额外派生序列。 |

引用已发布的基准测试时，应保留其实际软件版本、数据集和日期。没有来源的比较数字不能用来确定容量。

## 架构选项 {#architecture-options}

| 需求 | 设计决策 |
|---|---|
| 工作负载适合一台服务器，且重视运维简单性 | 先评估单节点模式，并用测量结果确定容量和恢复目标。 |
| 需要分别扩展读/写/存储，或已达到单机限制 | 评估集群模式，并将查询扇出、复制成本和运维复杂度纳入考虑。 |
| 需要承受故障 | 设计独立故障域、冗余摄取、查询路由、持久存储和经过测试的恢复流程。仅运行两个进程或使用复制磁盘并不能构成服务高可用。 |
| 已知摄取量 | 换算为 samples/second、活跃序列、churn、保留期和查询负载；**每天 1 亿个样本不是产品模式选择阈值**。 |

两个彼此独立的单节点实例需要明确设计写入复制、查询和故障切换处理。不要把多个 `vmsingle` 进程指向同一个数据目录，作为高可用捷径。

## 单节点模式 {#single-node-mode}

单个存储/查询进程可以简化运维，但它并不具备所有采集、告警和高可用功能。容量取决于实际测得的工作负载。

后面的原始清单和 Helm 配置文件是**两种替代部署方式**，不能按顺序一起应用。它们假设使用 `monitoring` 命名空间、Linux EC2 worker，以及已经存在且兼容的 `gp3` StorageClass/EBS CSI 配置（包括相应权限和卷绑定）。EKS Auto Mode 存储使用自己的 provisioner；不要假定 Auto Mode、Fargate、Windows 或 Hybrid Nodes 使用相同的 StorageClass/driver。资源数值仅作示例。应限制 Pod 端点，只允许可信客户端访问；ClusterIP 不提供身份验证。

### StatefulSet 部署

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: vmsingle
  namespace: monitoring
spec:
  serviceName: vmsingle
  replicas: 1
  selector:
    matchLabels:
      app: vmsingle
  template:
    metadata:
      labels:
        app: vmsingle
    spec:
      containers:
      - name: vmsingle
        image: victoriametrics/victoria-metrics:v1.151.0
        args:
        - --storageDataPath=/storage
        - --httpListenAddr=:8428
        - --retentionPeriod=1y
        - --search.latencyOffset=30s
        - --search.maxUniqueTimeseries=1000000
        - --search.maxSamplesPerQuery=1000000000
        - --memory.allowedPercent=60
        ports:
        - containerPort: 8428
          name: http
        resources:
          requests:
            cpu: 500m
            memory: 2Gi
          limits:
            cpu: 2000m
            memory: 8Gi
        volumeMounts:
        - name: storage
          mountPath: /storage
        livenessProbe:
          httpGet:
            path: /health
            port: 8428
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8428
          initialDelaySeconds: 5
          periodSeconds: 15
      securityContext:
        fsGroup: 65534
        runAsNonRoot: true
        runAsUser: 65534
  volumeClaimTemplates:
  - metadata:
      name: storage
    spec:
      accessModes:
      - ReadWriteOnce
      storageClassName: gp3
      resources:
        requests:
          storage: 100Gi
---
apiVersion: v1
kind: Service
metadata:
  name: vmsingle
  namespace: monitoring
spec:
  selector:
    app: vmsingle
  ports:
  - port: 8428
    targetPort: 8428
    name: http
  type: ClusterIP
```

### 关键端点

| 端点 | 说明 |
|---|---|
| `/api/v1/write` | Prometheus Remote Write |
| `/api/v1/query` | 即时查询 |
| `/api/v1/query_range` | 范围查询 |
| `/api/v1/series` | 序列元数据 |
| `/api/v1/labels` | 标签列表 |
| `/api/v1/label/{name}/values` | 标签值列表 |
| `/vmui` | 内置 UI |
| `/metrics` | 自身指标 |

## 集群模式 {#cluster-mode}

适用于大规模环境的可扩展集群配置。

### 架构

![集群架构图：vmagent 和 Prometheus 通过 vminsert 向 vmstorage 集群写入；Grafana 和 vmalert 通过 vmselect 查询 vmstorage，vmstorage 是两条路径的共享枢纽。](../../.gitbook/assets/en-observability-metrics-02-victoriametrics-2.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-metrics-02-victoriametrics-2.html)

### 组件

| 组件 | 作用 | 扩展方式 |
|---|---|---|
| **vminsert** | 路由写入请求 | 水平扩展（Deployment） |
| **vmstorage** | 存储数据 | 水平扩展（StatefulSet） |
| **vmselect** | 处理查询 | 水平扩展（Deployment） |

图中的箭头表示**请求**，而非响应。此原始示例中的三个副本是拓扑选择，不是通用的最低数量或可用性保证。每个存储成员都有独立 PVC；硬性节点反亲和要求至少有三个符合条件的 Kubernetes 节点。

`vminsert -replicationFactor=2` 会请求保存两份副本。只有在所有相关数据实际按该复制因子写入时，才应相应配置 `vmselect`；提高此 flag 不会回填旧数据。存储不可用时，`vmselect` 可能返回部分响应。`-search.denyPartialResponse` 会拒绝被判定为部分响应的结果；声明的复制因子也会影响该判定。写入降级、较旧的未复制数据和多重故障都需要分别验证。

`1ms` 去重设置用于处理时间戳相同的复制样本，并且必须在 vmstorage 和 vmselect 之间一致。不同时间抓取的高可用 scraper 需要有意设置抓取间隔和相同的标识标签；`30s` 间隔每个离散窗口只保留一个样本，可能丢弃合法的更高分辨率样本。这不是压缩开关。增加 vmstorage 只会重新分配新写入，不会迁移全部历史数据。

### vmstorage Deployment

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: vmstorage
  namespace: monitoring
spec:
  serviceName: vmstorage
  replicas: 3
  selector:
    matchLabels:
      app: vmstorage
  template:
    metadata:
      labels:
        app: vmstorage
    spec:
      containers:
      - name: vmstorage
        image: victoriametrics/vmstorage:v1.151.0-cluster
        args:
        - --storageDataPath=/storage
        - --httpListenAddr=:8482
        - --vminsertAddr=:8400
        - --vmselectAddr=:8401
        - --retentionPeriod=1y
        - --dedup.minScrapeInterval=1ms
        ports:
        - containerPort: 8482
          name: http
        - containerPort: 8400
          name: vminsert
        - containerPort: 8401
          name: vmselect
        resources:
          requests:
            cpu: 500m
            memory: 2Gi
          limits:
            cpu: 2000m
            memory: 8Gi
        volumeMounts:
        - name: storage
          mountPath: /storage
        livenessProbe:
          httpGet:
            path: /health
            port: 8482
          initialDelaySeconds: 30
          periodSeconds: 30
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: vmstorage
            topologyKey: kubernetes.io/hostname
  volumeClaimTemplates:
  - metadata:
      name: storage
    spec:
      accessModes:
      - ReadWriteOnce
      storageClassName: gp3
      resources:
        requests:
          storage: 100Gi
---
apiVersion: v1
kind: Service
metadata:
  name: vmstorage
  namespace: monitoring
spec:
  selector:
    app: vmstorage
  clusterIP: None
  ports:
  - port: 8482
    name: http
  - port: 8400
    name: vminsert
  - port: 8401
    name: vmselect
```

### vminsert Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vminsert
  namespace: monitoring
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vminsert
  template:
    metadata:
      labels:
        app: vminsert
    spec:
      containers:
      - name: vminsert
        image: victoriametrics/vminsert:v1.151.0-cluster
        args:
          - "--httpListenAddr=:8480"
          - "--storageNode=vmstorage-0.vmstorage:8400"
          - "--storageNode=vmstorage-1.vmstorage:8400"
          - "--storageNode=vmstorage-2.vmstorage:8400"
          - "--replicationFactor=2"
        ports:
        - containerPort: 8480
          name: http
        resources:
          requests:
            cpu: 200m
            memory: 256Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8480
          initialDelaySeconds: 10
          periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: vminsert
  namespace: monitoring
spec:
  selector:
    app: vminsert
  ports:
  - port: 8480
    targetPort: 8480
    name: http
  type: ClusterIP
```

### vmselect Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vmselect
  namespace: monitoring
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vmselect
  template:
    metadata:
      labels:
        app: vmselect
    spec:
      containers:
      - name: vmselect
        image: victoriametrics/vmselect:v1.151.0-cluster
        args:
        - --httpListenAddr=:8481
        - --storageNode=vmstorage-0.vmstorage:8401
        - --storageNode=vmstorage-1.vmstorage:8401
        - --storageNode=vmstorage-2.vmstorage:8401
        - --search.maxUniqueTimeseries=1000000
        - --search.maxSamplesPerQuery=1000000000
        - --replicationFactor=2
        - --dedup.minScrapeInterval=1ms
        - --search.denyPartialResponse
        ports:
        - containerPort: 8481
          name: http
        resources:
          requests:
            cpu: 200m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8481
          initialDelaySeconds: 10
          periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: vmselect
  namespace: monitoring
spec:
  selector:
    app: vmselect
  ports:
  - port: 8481
    targetPort: 8481
    name: http
  type: ClusterIP
```

## vmagent {#vmagent}

vmagent 是用于采集和转发指标的轻量级 agent。

### 主要功能

- 兼容 Prometheus 抓取配置
- 支持多个 Remote Write 目标
- 缓冲数据并在需要时重传
- 资源占用低
- 重写和筛选标签

### 部署

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vmagent
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vmagent
  template:
    metadata:
      labels:
        app: vmagent
    spec:
      serviceAccountName: vmagent
      containers:
      - name: vmagent
        image: victoriametrics/vmagent:v1.151.0
        args:
        - --promscrape.config=/etc/vmagent/prometheus.yml
        - --remoteWrite.url=http://vminsert:8480/insert/0/prometheus/api/v1/write
        - --remoteWrite.tmpDataPath=/tmp/vmagent-remotewrite-data
        - --remoteWrite.maxDiskUsagePerURL=1GB
        ports:
        - containerPort: 8429
          name: http
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 1Gi
        volumeMounts:
        - name: config
          mountPath: /etc/vmagent
        - name: tmpdata
          mountPath: /tmp/vmagent-remotewrite-data
      volumes:
      - name: config
        configMap:
          name: vmagent-config
      - name: tmpdata
        emptyDir:
          sizeLimit: 2Gi
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: vmagent-config
  namespace: monitoring
data:
  prometheus.yml: "global:\n  scrape_interval: 30s\n  scrape_timeout: 10s\nscrape_configs:\n- job_name: kubernetes-pods\n  kubernetes_sd_configs:\n  - role: pod\n    namespaces:\n      names:\n      - example-app\n  relabel_configs:\n  - source_labels:\n    - __meta_kubernetes_pod_phase\n    action: keep\n    regex: Running\n  - source_labels:\n    - __meta_kubernetes_pod_container_port_protocol\n    action: keep\n    regex: TCP\n  - source_labels:\n    - __meta_kubernetes_pod_container_port_name\n    action: keep\n    regex: metrics\n  - source_labels:\n    - __meta_kubernetes_pod_annotation_prometheus_io_scrape\n    action: keep\n    regex: 'true'\n  - source_labels:\n    - __meta_kubernetes_pod_annotation_prometheus_io_path\n    action: replace\n    regex: (/.*)\n    target_label: __metrics_path__\n  - source_labels:\n    - __meta_kubernetes_namespace\n    target_label: namespace\n  - source_labels:\n    - __meta_kubernetes_pod_name\n    target_label: pod\n"
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: vmagent
  namespace: monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: vmagent-pod-discovery
  namespace: example-app
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - get
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: vmagent-pod-discovery
  namespace: example-app
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: vmagent-pod-discovery
subjects:
- kind: ServiceAccount
  name: vmagent
  namespace: monitoring
```

这个最小 agent 只会抓取现有 `example-app` 命名空间中处于 Running 状态的 Pod；这些 Pod 必须具有名为 `metrics` 的 TCP 端口，并设置 `prometheus.io/scrape: "true"`。服务发现会提供 IPv4/IPv6 地址；这里没有使用按冒号拆分的重写规则。命名空间 Role 只列出 Pod。抓取节点/kubelet 需要单独配置范围受限的 RBAC 和经过验证的服务证书；不要为了让示例运行而关闭 TLS 校验或授予 `nodes/proxy` 权限。

可选的 `prometheus.io/path` 注解只有以 `/` 开头时才会被使用；否则抓取路径仍为 `/metrics`。

示例队列使用 `emptyDir`：它能在同一 Pod 内的容器重启后保留，**但不能在 Pod 被删除或替换后保留**。当队列达到 `remoteWrite.maxDiskUsagePerURL` 时，会丢弃最旧的排队数据。需要持久缓冲时，应审查并采用持久卷/StatefulSet 或 operator 配置，为每个 URL 队列设定容量，并监控重试、丢弃和剩余空间。队列不是备份，也不保证无损交付。

### vmagent 分片

每个成员都需要相同的服务发现/重标记配置，以及从 `0` 到 `membersCount-1` 的唯一稳定序号。以该序号结尾的 StatefulSet 名称（例如 `vmagent-0`）也可用。**Deployment 的随机 Pod 名称不是稳定的分片编号**。上面的单副本清单有意不带分片 flag。以下内容是参数参考，并非第二个可部署工作负载。抓取复制与存储复制是不同的操作；重复的抓取流需要兼容的去重配置。

```yaml
args:
  - "--promscrape.cluster.membersCount=3"    # Total number of vmagents
  - "--promscrape.cluster.memberNum=0"       # Current instance number (0, 1, 2)
  - "--promscrape.cluster.replicationFactor=2"  # How many instances scrape each target
```

## vmalert {#vmalert}

vmalert 用于评估告警规则并生成告警。

### 部署

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vmalert
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vmalert
  template:
    metadata:
      labels:
        app: vmalert
    spec:
      containers:
      - name: vmalert
        image: victoriametrics/vmalert:v1.151.0
        args:
        - --datasource.url=http://vmselect:8481/select/0/prometheus
        - --remoteRead.url=http://vmselect:8481/select/0/prometheus
        - --remoteWrite.url=http://vminsert:8480/insert/0/prometheus
        - --notifier.url=http://alertmanager:9093
        - --rule=/etc/vmalert/rules/*.yaml
        - --evaluationInterval=30s
        - --external.url=http://vmalert:8880
        - --external.label=cluster=production
        ports:
        - containerPort: 8880
          name: http
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
        volumeMounts:
        - name: rules
          mountPath: /etc/vmalert/rules
        livenessProbe:
          httpGet:
            path: /health
            port: 8880
          initialDelaySeconds: 10
          periodSeconds: 30
      volumes:
      - name: rules
        configMap:
          name: vmalert-rules
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: vmalert-rules
  namespace: monitoring
data:
  kubernetes.yaml: "groups:\n- name: kubernetes\n  interval: 30s\n  rules:\n  - alert: NodeMemoryHigh\n    expr: '(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes)\n\n      / node_memory_MemTotal_bytes * 100 > 90\n\n      '\n    for: 5m\n    labels:\n      severity: warning\n    annotations:\n      summary: High memory usage on {{ $labels.instance }}\n      description: Memory usage is {{ printf \"%.2f\" $value }}%\n  - alert: PodRestartsHigh\n    expr: increase(kube_pod_container_status_restarts_total[1h]) > 5\n    for: 10m\n    labels:\n      severity: warning\n    annotations:\n      summary: 'Frequent restarts: {{ $labels.namespace }}/{{ $labels.pod }}'\n      description: Pod has restarted {{ $value }} times in the last hour\n- name: recording-rules\n  interval: 30s\n  rules:\n  - record: instance:node_cpu_utilization:ratio_rate5m\n    expr: 1 - avg by (instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m]))\n  - record: instance:node_memory_utilization:ratio\n    expr:\
    \ '1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes\n\n      '\n"
```

这些规则假定 node-exporter 和 kube-state-metrics 已经被抓取；上面的最小应用 Pod 服务发现并不会安装它们。重启计数不能证明 Pod 处于 `CrashLoopBackOff`，因此告警名称使用 `PodRestartsHigh`。CPU recording 使用 counter rate 并保存比率，而不是对累计 counter 求原始平均值。

`datasource.url` 和 `remoteRead.url` 使用 query API 的基础 URL；`remoteWrite.url` 使用 write API 的基础 URL，用于持久化 recording/alert-state 序列。名为 remoteRead 的 flag 并不表示实现了每种 Prometheus Remote Read 协议。Alertmanager 必须实际存在并可访问；通知路由是另一项配置。评估器的高可用还应检查 external labels、通知去重和告警状态恢复。

## MetricsQL {#metricsql}

MetricsQL 支持熟悉的 PromQL 语法，但有意存在语义差异：`rate`/`increase` 可将回看窗口之前的原始样本纳入考虑，且其外推方式与 Prometheus 不同；NaN 点会被移除；scalar/instant-vector 和指标名处理也可能不同。迁移时应使用已知输入数据比较 dashboard、告警表达式和 recording rule。不要仅凭查询语言兼容就推断完全兼容 Prometheus API。

### PromQL 风格查询

```promql
rate(http_requests_total[5m])
sum by (service) (rate(http_requests_total[5m]))
histogram_quantile(0.95, sum by (service, le) (rate(http_request_duration_seconds_bucket[5m])))
```

按所需标识以及 `le` 聚合直方图 rate，然后计算 quantile。先分别计算 quantile 再对这些 quantile 求 quantile，并不能得到全局请求分位数。

### MetricsQL 扩展

以下函数示例使用小型合成 gauge `audit_gauge`，它不是默认可用的 exporter 指标。

```promql
rate(http_requests_total)
keep_last_value(up)
missing_metric default 0
label_set(up, "env", "demo")
label_del(up, "instance")
label_copy(up, "instance", "node")
label_move(up, "instance", "node")
label_join(up, "dst", "-", "job", "instance")
label_transform(up, "job", "api", "frontend")
union(up{job="api"}, up{job="web"})
lag(audit_gauge[2m])
lifetime(audit_gauge[2m])
scrape_interval(audit_gauge[2m])
range_avg(audit_gauge)
range_max(audit_gauge)
range_min(audit_gauge)
range_sum(audit_gauge)
range_first(audit_gauge)
range_last(audit_gauge)
rollup(audit_gauge[2m])
rollup_rate(http_requests_total[5m])
rollup_delta(audit_gauge[2m])
zscore_over_time(audit_gauge[2m])
```

| 函数或运算符 | 实际含义与边界 |
|---|---|
| `rate(metric)` | 省略窗口时，会根据查询 step 和观测到的抓取间隔推导。为使规则可复现，应显式指定窗口。 |
| `keep_last_value(q)` | 在计算点缺失时填入较早的值。它可能掩盖抓取缺失；不要用它让可用性告警看起来健康。 |
| `q1 default q2` | 用对应的右侧表达式填充缺失点。它不能证明缺失数据等于零，也不能保证每种情况下都会生成预期服务标签，更不能让零流量比率变得有意义。 |
| `label_set/copy/move/join/transform` | 修改查询结果的标签，不会改写已存储的历史数据。正则表达式示例会改动 job 标签，不会拆分 IPv6 地址。 |
| `label_del` | 删除标识标签；检查输出序列是否冲突，并在合并身份时显式聚合。 |
| `union` | 合并查询结果，不是数值相加。 |
| `lag(metric[2m])` | 返回该窗口内最新原始样本到评估时间戳之间的秒数；不是两个样本之间的间隔。 |
| `lifetime(metric[2m])` | 返回**该窗口内**第一个和最后一个原始样本之间的秒数，不是序列完整的存储时长。 |
| `scrape_interval(metric[2m])` | 根据窗口内的原始样本估算间隔；它不会读取抓取配置。 |
| `range_avg/max/min/sum/first/last(q)` | 在选定查询范围内，针对每个结果序列的已计算点进行操作。step/分辨率会影响这些点；这些函数不是对全部存储历史进行聚合。 |
| `rollup`、`rollup_rate`、`rollup_delta` | 返回多种 rollup 变体（例如 min/max/avg）；需考虑新增的 `rollup` 标签和指标类型。 |
| `zscore_over_time` | 计算 gauge 窗口的统计 z-score，不是经过校准的异常概率，结果也不限制在 0–1。1.151.0 不支持 `anomaly_score` 函数。 |

### 错误率、缺失数据与直方图

先一致地移除 `status` 维度。仅当某服务存在 denominator 序列时，分子才回退为零；denominator 会过滤掉零流量：

```promql
(sum by (service) (rate(http_requests_total{status=~"5.."}[5m])) or 0 * sum by (service) (rate(http_requests_total[5m]))) / (sum by (service) (rate(http_requests_total[5m])) > 0)
```

此测试数据按 `service` 分组。如果 cluster 或 namespace 也是服务身份的一部分，应在分子和分母的每个聚合中一致地包含这些标签。

原生测试数据的健康/无 5xx 结果为 **0**，全为 5xx 的结果为 **1**，10% 故障的结果为 **0.1**。零流量和缺失服务不会产生值；应分别监控流量和遥测缺失。若不聚合带 status 标签的序列，5xx 分子可能只与同为 5xx 的分母匹配，结果为 1，而非真实服务错误率。附加 `default 0` 不能替代这些处理。

```promql
histogram_share(0.5, sum by (service, le) (rate(http_request_duration_seconds_bucket[5m])))
count(up)
count by (job) (up)
```

上面的 `histogram_share` 会估算近期窗口内不超过 500 ms 的请求占比。原始累计 bucket 表示自 counter reset 以来的累积值。`count(up)` 统计所选的 `up` 序列，不是数据库的总基数。应使用范围明确的 TSDB/基数诊断来检查该值。

## Helm 安装 {#helm-installation}

基于 operator 的 **victoria-metrics-k8s-stack 0.92.1** 会在根配置中使用 `vmsingle`、`vmcluster`、`vmagent` 和 `vmalert`。独立的 `victoria-metrics-single` 或 `victoria-metrics-cluster` chart 的 values 不会配置此 stack。Helm 可能接受未使用的 key，因此应检查渲染后的自定义资源。

固定版本的 chart 包含 operator chart **0.67.3 / operator 0.74.1**，并配置 VictoriaMetrics **1.151.0**。该 chart 的 Kubernetes `>=1.25.0-0` 版本限制并不是完整的产品/EKS 支持矩阵。下方 `--kube-version 1.35.0` 是渲染输入，不是 API server 测试。安装前应检查受支持的 EKS 版本、CSI provisioner，以及现有 operator/CRD 的所有权。

```bash
helm repo add vm https://victoriametrics.github.io/helm-charts/
helm repo update vm
helm pull vm/victoria-metrics-k8s-stack --version 0.92.1 --untar --untardir ./vendor
helm template vm-demo ./vendor/victoria-metrics-k8s-stack \
  --namespace monitoring --kube-version 1.35.0 --include-crds \
  -f values-single.yaml > rendered.yaml
```

### values-single.yaml

此起始配置启用存储，以及一个会选择带有 release 标签的 `VMServiceScrape` 对象的单副本 agent。在尚未配置相应目标、权限和凭据前，它有意关闭其他 collector、默认规则、Grafana 和通知服务。它不是完整的集群监控或生产级高可用配置。必须存在兼容存储配置的 `gp3`；资源大小仅作示例。

```yaml
fullnameOverride: vm-demo
victoria-metrics-operator:
  crds:
    cleanup:
      enabled: false
  operator:
    disable_prometheus_converter: true
grafana:
  enabled: false
defaultDashboards:
  enabled: false
defaultRules:
  enabled: false
alertmanager:
  enabled: false
vmalert:
  enabled: false
vmsingle:
  enabled: true
  spec:
    retentionPeriod: 90d
    storage:
      storageClassName: gp3
      accessModes:
      - ReadWriteOnce
      resources:
        requests:
          storage: 100Gi
    resources:
      requests:
        cpu: 500m
        memory: 2Gi
      limits:
        cpu: '2'
        memory: 8Gi
vmcluster:
  enabled: false
vmagent:
  enabled: true
  spec:
    replicaCount: 1
    selectAllByDefault: false
    serviceScrapeSelector:
      matchLabels:
        app.kubernetes.io/instance: vm-demo
    resources:
      requests:
        cpu: 100m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 1Gi
prometheus-node-exporter:
  enabled: false
kube-state-metrics:
  enabled: false
kubelet:
  enabled: false
kubeApiServer:
  enabled: false
kubeControllerManager:
  enabled: false
kubeDns:
  enabled: false
coreDns:
  enabled: false
kubeEtcd:
  enabled: false
kubeScheduler:
  enabled: false
kubeProxy:
  enabled: false
```

`serviceScrapeSelector` 选择的是 **VMServiceScrape 元数据**。该抓取资源随后才会选择 Service/endpoint；它不是直接选择应用 Pod 的 selector。命名空间选择范围和 agent RBAC 必须保持一致。对于 EKS 上的 node/kubelet/control-plane 指标，只启用所选平台实际提供的 endpoint，并验证 TLS。托管 control plane endpoint、Auto Mode、Fargate 和 Windows 并不会提供完全相同的抓取目标。

operator/CRD 应只有一个所有者。此配置关闭 chart 的 CRD 清理 hook 和 Prometheus 资源转换；这并不意味着可以任意删除 CRD。如果复用单独管理的 operator，应按该所有权配置 chart，而不是安装竞争的 controller。CRD 升级应与 Helm release 升级分开审查。

审查上下文、渲染结果、权限和已有资源后，使用相同版本和 values 进行安装：

```bash
helm upgrade --install vm-demo vm/victoria-metrics-k8s-stack \
  --version 0.92.1 --namespace monitoring --create-namespace \
  -f values-single.yaml
```

### 集群模式 Overlay

```yaml
vmsingle:
  enabled: false
vmcluster:
  enabled: true
  spec:
    retentionPeriod: 90d
    replicationFactor: 2
    vmstorage:
      replicaCount: 3
      extraArgs:
        dedup.minScrapeInterval: 1ms
      storage:
        volumeClaimTemplate:
          spec:
            storageClassName: gp3
            accessModes:
            - ReadWriteOnce
            resources:
              requests:
                storage: 100Gi
      resources:
        requests:
          cpu: 500m
          memory: 2Gi
        limits:
          cpu: '2'
          memory: 8Gi
    vmselect:
      replicaCount: 2
      extraArgs:
        dedup.minScrapeInterval: 1ms
        search.denyPartialResponse: 'true'
      resources:
        requests:
          cpu: 200m
          memory: 512Mi
        limits:
          cpu: '1'
          memory: 2Gi
      storage:
        volumeClaimTemplate:
          spec:
            storageClassName: gp3
            accessModes:
            - ReadWriteOnce
            resources:
              requests:
                storage: 2Gi
    vminsert:
      replicaCount: 2
      resources:
        requests:
          cpu: 200m
          memory: 256Mi
        limits:
          cpu: '1'
          memory: 1Gi
```

对一个**新建、独立的集群模式部署**，将此配置叠加到起始配置之上。不要把已有单节点 release 直接切换成集群模式当作数据迁移：关闭其 CR 可能移除正在运行的存储，而且 PVC/历史数据不会自动复制到集群中。

用 `-f values-single.yaml -f values-cluster.yaml` 渲染。原生检查确认生成 VMCluster、复制因子 2、三个存储副本、一致的 1ms 去重设置，以及 cluster tenant-0 写入 URL。operator 协调、PVC 绑定、故障域放置和实际可用性仍须在真实环境中测试。满足其他前提时，三个存储成员达到在一个成员不可用时仍保留 N=2 两份数据所需的 `2*N-1` 数量。

Grafana 可使用指向单节点基础 URL 的 Prometheus datasource，也可对原始集群使用 `http://vmselect:8481/select/0/prometheus`。启用可选 Grafana chart 前，应配置身份验证、持久化和 datasource 访问。vmalert 规则、Alertmanager 路由/接收方和 exporter 目标应一起配置；仅仅启用多个副本并不能保证告警送达。

## 长期存储配置 {#long-term-storage-configuration}

### 保留期与磁盘容量

选择**一个**保留期参数，不要重复设置多个 `args` 映射或互相竞争的 flag：

```yaml
args:
  - "--retentionPeriod=90d"
```

1.151.0 的默认值为一个月（31 天），最短为一天。裸数字表示月；为明确表达意图，应使用带单位的值。保留期不限制存储字节数，降低保留期也不保证立即回收空间。经审查的二进制版本不支持 `storage.maxDiskSpace` flag。低于可用空间阈值时，`storage.minFreeDiskSpaceBytes` 会停止接收新数据；它不会为了维持按大小计算的保留目标而驱逐数据。应为合并、快照和临时负载峰值预留空间。

### 快照备份与恢复

`vmbackup` 会从单节点/vmstorage 进程使用的**同一个存储目录**读取一致性快照。它支持 S3、GCS、Azure Blob、兼容 S3 的存储和本地文件系统。仅保留本地快照不构成独立备份；应保护远端副本、凭据和恢复流程。

上面的原始 StatefulSet 会生成 PVC **`storage-vmsingle-0`**（由 `claim-template`、`StatefulSet` 和序号组成），而不是 `vmsingle-storage-vmsingle-0`。operator 创建的名称会不同；应检查实际 Pod volume/PVC。不能假定随机 CronJob 可在另一节点挂载 EBS RWO 卷，或读取另一个 Pod 创建的快照。优先审查并使用同 Pod sidecar/工作流完成备份，并将快照 URL 指向那个确切的存储进程。

```bash
# Run only in the reviewed backup container with this storage directory mounted.
vmbackup -storageDataPath=/storage \
  -snapshot.createURL=http://127.0.0.1:8428/snapshot/create \
  -dst=s3://example-vm-backup/cluster-a/vmsingle-0/2026-09-12
```

上方 bucket/prefix 是占位符；该命令会创建存储快照并写入备份对象，**本次审查没有对 AWS 执行该命令**。避免多个写入者同时操作同一目标。复用目标会执行增量同步，本身并不构成不可变历史备份；应定义带版本的目标/保留策略并测试恢复。集群模式下，应将**每个 vmstorage 成员备份到各自独立的 prefix**，而不是备份 vminsert/vmselect 或任意负载均衡到的成员。应使用经审查且兼容的 `vmrestore` 流程，在目标数据库进程停止时恢复到经过审查的存储中。

为实际备份容器和 bucket/prefix 使用最小权限的 workload identity；还应配置其 AWS Region、TLS 和网络路由。经审查的源代码使用 AWS SDK for Go v2 的默认配置链；EKS Pod Identity 还需要 Agent/association 和受支持的 Linux EC2 平台，IRSA 是另一种受支持的集成方式。ServiceAccount 名称或仅有 S3 网络连通性都不会自动授予访问权限。应根据所选备份/保留工作流核实所需的读/写/列出/删除或 KMS 操作。不要把静态 AWS access key 注入 chart、CronJob 或镜像。

## 降采样 {#downsampling}

Enterprise 存储降采样与开源版本中的**记录额外派生序列**不是同一操作。recording rule 不会删除或压缩原始数据，还可能增加存储序列。摄取时的 stream aggregation 是另一种方案，需明确分组、reset 以及保留/丢弃输入样本的语义；丢弃原始样本前应评估这些影响。

### 记录派生序列

选择五分钟输出间隔时，请使用此组**替代**前面的 recording group；不要同时启用两个包含相同 record 名称的组。

CPU seconds 是 counter，因此应先计算 idle **rate**，再推导利用率。下面的一小时表达式会对记录的五分钟比率观测求平均值。应将直方图 quantile 保存在独立序列中；用 `or` 组合具有相同标签的 p50/p90/p99 表达式会保留第一个匹配序列并丢失其他结果。

```yaml
groups:
- name: derived-series
  interval: 5m
  rules:
  - record: instance:node_cpu_utilization:ratio_rate5m
    expr: 1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]))
  - record: instance:node_cpu_utilization:ratio_avg1h
    expr: avg_over_time(instance:node_cpu_utilization:ratio_rate5m[1h])
  - record: service:http_request_duration_seconds:p50_5m
    expr: histogram_quantile(0.5, sum by (service, le) (rate(http_request_duration_seconds_bucket[5m])))
  - record: service:http_request_duration_seconds:p90_5m
    expr: histogram_quantile(0.9, sum by (service, le) (rate(http_request_duration_seconds_bucket[5m])))
  - record: service:http_request_duration_seconds:p99_5m
    expr: histogram_quantile(0.99, sum by (service, le) (rate(http_request_duration_seconds_bucket[5m])))
```

这些 p50/p90/p99 值是派生 gauge，无法重建原始直方图，也不能在任意较长时间范围内计算出正确 quantile。如果之后还需要聚合，应保留 rate/count/bucket 信息。采用前应测试告警阈值、记录间隔、缺失输入和查询语义。

## 性能优化 {#performance-optimization}

| 控制项 | 实际限制范围 |
|---|---|
| `memory.allowedPercent` / `memory.allowedBytes` | 内部缓存，**不是进程总 RSS**；查询/摄取、Go 和操作系统内存还需额外余量。 |
| `search.maxMemoryPerQuery` | 限制单个查询；还需考虑并发请求和其他内存分配。 |
| `search.maxUniqueTimeseries`、`search.maxSamplesPerQuery` | 拒绝异常大的查询；不会降低摄取基数。 |
| `search.maxQueryDuration`、`search.maxPointsPerTimeseries` | 查询时间/输出范围限制。增大 range step 会改变评估分辨率，不会改写最初存储的样本。 |
| `storage.cacheSizeIndexDBDataBlocks`、`storage.cacheSizeIndexDBIndexBlocks` | 高级缓存覆盖项。覆盖自动 sizing 前，应测量 cache miss、CPU 和磁盘 I/O。 |
| `maxLabelsPerTimeseries`、`maxLabelValueLen` | 经审查的版本会拒绝超限序列，并增加 `vm_rows_ignored_total`；这不是无害的标签截断。 |
| `dedup.minScrapeInterval` | 对同一标签集的重复点，每个离散间隔保留一个；应结合复制/抓取频率有意选择，而不是当作通用压缩功能。 |

测量活跃序列和 churn、查询扇出、保留期、队列增长、缓存压力和剩余磁盘空间。固定资源示例或单次基准测试不能证明生产容量安全。应通过网络和应用访问控制保护管理端点和查询端点。

## 最佳实践 {#best-practices}

应先确定故障和恢复目标，再决定副本数量。分别考虑采集器高可用、存储复制、查询可用性和备份。明确租户路由/身份验证、TLS、workload identity、PVC 所有权以及升级/迁移责任。监控 insert failure、rejected row、队列丢弃、慢查询、内存和磁盘；编写规则前，应发现每个组件 `/metrics` 端点实际暴露的标签。

本地 1.151.0 的 `/metrics` 端点实际暴露了以下指标名称。抓取后，应使用真实的 job/instance 标签限定查询范围：

```promql
vm_app_version
rate(vm_rows_inserted_total[5m])
rate(vm_slow_queries_total[5m])
process_resident_memory_bytes
```

### 迁移指南

1. 保留当前 scraper，新增经过审查的 VictoriaMetrics remote-write 目标；验证队列状态和数据到达情况。
2. 使用已知输入，在两个存储中分别运行 Grafana 查询和告警规则，包括缺失/零流量、counter reset 和直方图聚合场景。
3. 如需导入历史数据，应创建并保留一致的 Prometheus snapshot。使用单独提供的 `vmctl` 将数据导入预期目标，并考虑保留期、重叠/去重、速率限制和权限。
4. 只有在替代 scraper/agent 已采集所有目标且数据已到达后，才停用旧写入路径。**仅更改 Grafana datasource 并不能替代指标采集**。保留回滚窗口，并明确备份责任。

```yaml
remote_write:
  - url: http://vmsingle.monitoring.svc:8428/api/v1/write
```

```bash
vmctl prometheus --prom-snapshot=/backup/prometheus-snapshot \
  --vm-addr=http://vmsingle.monitoring.svc:8428
```

这些是配置/命令参考，并不表示本次审查实际执行了迁移。上方 URL 名称对应原始单节点清单；Helm 配置应使用实际生成的 Service。集群导入/写入/查询路径与单节点路径不同。使用 `vmctl` 时，通过 `--vm-addr` 提供 vminsert 基础 URL，并通过 `--vm-account-id` 指定目标租户；不要把 remote-write URL 当作导入器的基础 URL。

## 故障排除 {#troubleshooting}

使用已知的单节点 Service 和本地 port-forward 执行只读诊断；对于 operator/Helm 部署，请替换为对应的 Service 名称：

```bash
kubectl port-forward -n monitoring svc/vmsingle 8428:8428
```

```bash
curl --fail --silent --show-error http://127.0.0.1:8428/api/v1/status/tsdb
curl --fail --silent --show-error http://127.0.0.1:8428/api/v1/status/active_queries
curl --fail --silent --show-error http://127.0.0.1:8428/api/v1/status/top_queries
curl --fail --silent --show-error http://127.0.0.1:8428/metrics
```

TSDB status 描述的是序列/基数，**不是文件系统剩余字节数或完整内存配置**。应分别检查进程/容器内存、PVC/文件系统指标、队列大小和存储健康状况。活跃查询/top-query endpoint 描述请求；它们可能需要启用 profiling flag 或经过一段采集时间才有用。查询过滤条件、范围、step 和并发数都会显著影响成本。

磁盘已满时需要制定存储/保留/摄取计划，而不是执行一条笼统的删除命令。`delete_series`、`/snapshot/create` 和 `/internal/force_merge` 都是会更改状态的管理操作。删除数据需要有效且范围严格受限的 selector，并须通过备份/保留审批；snapshot 可能保留磁盘块，force-merge 会消耗 I/O 且需要可用空间。因此，不应将这些操作放入可直接复制执行的只读诊断代码块。存储压力下停止入口流量可能使有限的 collector 队列溢出，应检查完整的数据路径。

## 参考资料

- [VictoriaMetrics 1.151.0](https://github.com/VictoriaMetrics/VictoriaMetrics/releases/tag/v1.151.0)
- [单节点模式](https://docs.victoriametrics.com/victoriametrics/single-server-victoriametrics/)
- [集群/复制](https://docs.victoriametrics.com/victoriametrics/cluster-victoriametrics/)
- [MetricsQL](https://docs.victoriametrics.com/victoriametrics/metricsql/)
- [vmagent](https://docs.victoriametrics.com/victoriametrics/vmagent/)
- [vmalert](https://docs.victoriametrics.com/victoriametrics/vmalert/)
- [vmbackup](https://docs.victoriametrics.com/victoriametrics/vmbackup/)
- [Prometheus snapshot 迁移](https://docs.victoriametrics.com/victoriametrics/vmctl/prometheus/)
- [Stream aggregation](https://docs.victoriametrics.com/victoriametrics/stream-aggregation/)
- [Stack 0.92.1 values](https://raw.githubusercontent.com/VictoriaMetrics/helm-charts/victoria-metrics-k8s-stack-0.92.1/charts/victoria-metrics-k8s-stack/values.yaml)
- [VMServiceScrape](https://docs.victoriametrics.com/operator/resources/vmservicescrape/)
- [EKS EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)
- [Pod Identity SDK 要求](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-minimum-sdk.html)
- [S3 备份实现](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.151.0/lib/backup/s3remote/s3.go)

## 测验

[VictoriaMetrics 测验](../../quizzes/observability/metrics/02-victoriametrics-quiz.md)

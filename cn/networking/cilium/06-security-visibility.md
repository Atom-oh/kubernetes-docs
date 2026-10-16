# 安全性与可观测性

> **审核基线**：Cilium 1.20.2；Cilium CLI 0.20.1；Hubble CLI 1.20.2。
> **最后审核**：October 15, 2026。Kubernetes 1.33–1.36 是 Cilium 1.20 的兼容性范围；请选择位于 API server 支持版本偏差范围内的 kubectl。

## 实验环境设置

使用一个现有的 Cilium 1.20.2 测试集群，其中至少有两个可调度的 Linux 节点、正常工作的 DNS，并且已启用策略执行。请遵循[安装和平台前提条件](README.md)，包括 EKS 限制和经过验证的 CLI 下载。这些示例不会安装或替换 CNI。它们需要 Helm、kubectl、Cilium 和 Hubble CLI，以及 jq。

本实验假定 `kube-system` 中的 CoreDNS Pod 带有 `k8s-app=kube-dns` 标签。请验证实际的解析器路径；NodeLocal DNS 或不同的发行版需要不同的目标/端口。集群中已存在的策略、代理配置和平台控制可能会影响结果。

### Hubble 安装与设置

保存 `hubble-values.yaml`。此片段启用本地服务器、Relay、UI 和选定的指标插件。请将它应用于**同一 Chart 版本的现有 release**；先检查保留的安装值。对于版本升级，请使用升级流程，而不是盲目复用旧值。

```yaml
# hubble-values.yaml
hubble:
  enabled: true
  relay:
    enabled: true
  ui:
    enabled: true
  metrics:
    enabled:
    - dns
    - drop
    - tcp
    - flow
    - httpV2
    serviceMonitor:
      enabled: false
```
```bash
helm upgrade cilium cilium/cilium --namespace kube-system \
  --version 1.20.2 --reuse-values --values hubble-values.yaml --wait
cilium status --wait
# Terminal 1: keep this process running; stop it with Ctrl-C.
cilium hubble port-forward
```

在另一个终端中，验证 API 连通性。端口转发仅保留在本地；它不会通过公共 LoadBalancer 发布 Relay 或 UI。

```bash
# Terminal 2
hubble status
hubble observe --last 20
# Optional UI; keep its local forwarding process running while using it.
cilium hubble ui
```

## Cilium 的安全功能

Cilium 将网络策略与 endpoint 身份和可选加密结合。Hubble 使由此产生的网络事件可观测。评估安全要求时，理解它们的边界至关重要。

### Cilium 安全架构

| 职责 | 组件与范围 |
| --- | --- |
| 网络微分段 | Cilium L3/L4 策略选择身份、地址、端口和方向。带命名空间的 CiliumNetworkPolicy 会选择其命名空间中的 endpoint。 |
| HTTP 策略 | 当代理能够看到 HTTP 时，Cilium 的 Envoy 集成会筛选方法、路径和 header。DNS 策略使用 DNS 代理。 |
| DNS/FQDN 控制 | DNS 规则控制查询；`toFQDNs` 允许从观察到的 DNS 响应中获知的目标 IP。这不是自动的恶意域名信誉源。 |
| 节点传输加密 | IPsec 或 WireGuard 可保护节点之间受支持的流量。覆盖范围取决于模式和配置。 |
| 网络调查 | Hubble 记录流元数据和策略 verdict；Relay、CLI 和 UI 会将其公开。 |
| 进程和 syscall 安全性 | **Tetragon** 是一个独立项目，用于运行时事件和已配置的执行。启用 Hubble 不会安装它。 |
| 威胁检测与响应 | 必须为预期的检测和操作配置外部告警规则、SIEM/WAF 和响应控制器。 |

### 网络与应用安全性

使用最小权限策略限制横向移动，并使用显式 egress 限制依赖项。安全身份源自与安全相关的标签；它们不一定对每个 Pod 唯一，也不会验证最终用户身份。

当前 Cilium 策略支持 HTTP 和 DNS L7 规则。当 gRPC 的 HTTP/2 流量可见时，可以使用 HTTP 方法/路径/header 规则。Kafka topic 策略已不再受支持。带值的 HTTP `headers` 条目是字面匹配，而非正则表达式身份验证。`Authorization` header 的存在或格式不会验证 JWT、其 issuer、签名或授权声明。请为此使用应用程序的身份验证层或已配置的 gateway。

端口 8443 上的 HTTP 规则不会解密 HTTPS。HTTP 策略必须先经由 TLS 终止或单独受支持的检查安排，才能评估加密的应用数据。不要仅为了让 L7 检查生效而绕过 service mesh 的加密。

### 身份、身份验证与加密

Cilium 基于 SPIRE 的**双向身份验证在 1.20 中虽为 Beta 但已弃用**（已在 1.21 预发布版中移除；升级说明指向 ztunnel 作为替代方案，因此不要在新设计中选择它）：它会为安全身份执行带外握手。仅该握手不会加密应用流量。其文档限制包括不支持 ClusterMesh，且不能与任意外部 mTLS 系统互操作。独立的**ztunnel workload mTLS 功能同样处于 Beta**；它有自己的注册和证书前提条件。这两个功能都不应被描述为身份选择器的自动结果。

### 加密配置

以下是**可替代的 Helm 片段**，而非应同时启用的两项设置。请选择一个用于计划中的安装/变更，并验证内核、路由和平台前提条件。

```yaml
# wireguard-values.yaml
encryption:
  enabled: true
  type: wireguard
  nodeEncryption: false
```
```yaml
# ipsec-values.yaml
encryption:
  enabled: true
  type: ipsec
  nodeEncryption: false
  ipsec:
    secretName: cilium-ipsec-keys
```

WireGuard 需要内核支持，以及节点到节点的 UDP 51871 端口路径。IPsec 在启用前需要在 Cilium 的命名空间中存在格式正确且经过安全管理的 `cilium-ipsec-keys` Secret；请遵循官方密钥创建和轮换流程。仅在 ConfigMap 中命名密钥文件不会供应该密钥或其卷。

默认情况下，这些模式保护跨节点的受支持且由 Cilium 管理的 Pod 流量；同节点流量不会由这些节点隧道加密。到任意外部目标的流量不会自动受到覆盖。WireGuard 节点到节点加密（`encryption.nodeEncryption`）是一个独立的 Beta 选项，在 1.21 预发布版中已弃用，并计划在 1.22 移除；默认情况下，control-plane 节点被排除在该扩展之外，但其由 Cilium 管理的跨节点 Pod 流量仍可以加密。请验证实际的数据包路径，并在需要时使用应用 TLS。Host firewall 兼容性也取决于加密模式：host 策略无法与 IPsec 配合工作（记录于 1.21 预发布版 host-policy 已知问题中）。

## 使用 Hubble 实现网络可观测性

Hubble 接收 datapath、代理和 agent 事件，并使用 Kubernetes 元数据对其进行扩充。它并不只是一个定期轮询所有 eBPF map 的读取器。

```text
Kernel/datapath events + proxy/agent events
                  |
                  v
       Hubble server in each Cilium agent
          |             |                |
   bounded flow      metric endpoint   optional file exporter
      buffer          TCP 9965            |
          |             ^             log collector/storage
     Relay query        | scrape
          ^          Prometheus <--- Grafana queries
          |
       CLI / UI
```

服务器会维护有限的内存历史记录。Relay 查询多个服务器；它不是持久化数据库。UI 提供流探索和服务依赖关系图，而 CLI 支持显式过滤器。没有匹配的记录可能意味着没有流量、过滤器错误、peer 不可用、缺少 L7 可见性，或事件被覆盖/丢失。

### Hubble CLI 使用示例

```bash
hubble observe --namespace cilium-security-demo --last 100
hubble observe --from-pod cilium-security-demo/frontend \
  --to-service cilium-security-demo/backend --last 100
hubble observe --namespace cilium-security-demo --protocol http \
  --http-status '4+' --http-status '5+' --last 100
hubble observe --namespace cilium-deny-demo --verdict DROPPED \
  --drop-reason-desc POLICY_DENIED --last 100
hubble observe --pod cilium-security-demo/frontend --follow
```

`--pod namespace/name` 与任一 endpoint 匹配；请使用 `--from-pod`/`--to-pod` 指定方向。Pod 名称不是标签选择器：按标签选择时请使用 `--from-label` 或 `--to-label`。不要将 `--namespace` 与 `--from-pod`/`--to-pod` 结合使用；CLI 会拒绝该组合。

`DROPPED` 是一个 verdict。`POLICY_DENIED` 是一个 drop reason，通过 `--drop-reason-desc` 选择。HTTP 状态前缀使用 `4+` 和 `5+`，而不是 `4..` 和 `5..`。HTTP 过滤器需要由代理派生的 L7 事件；被丢弃的 TCP 连接不一定有 HTTP 状态。

## 网络可观测性与监控

### Hubble 指标

已启用的插件会公开不同的观测结果：

| 插件 | 示例指标 | 含义与限制 |
| --- | --- | --- |
| `flow` | `hubble_flows_processed_total` | 按协议/类型/verdict 划分的已处理流事件；并非每条路径上的唯一请求或数据包。 |
| `drop` | `hubble_drop_total{reason="POLICY_DENIED"}` | 观察到的丢弃；reason 标签是 enum 名称。 |
| `tcp` | `hubble_tcp_flags_total` | 观察到的 TCP flag；不是通用的 RTT、重传或并发连接指标。 |
| `dns` | `hubble_dns_queries_total`, `hubble_dns_responses_total` | 观察到的 DNS 查询/响应和响应代码；不是通用 DNS 延迟直方图。 |
| `httpV2` | `hubble_http_requests_total`, `hubble_http_request_duration_seconds` | 从 HTTP 响应流派生的请求计数/状态和以秒为单位的持续时间。需要 HTTP 可见性。 |

不要同时启用 `http` 和 `httpV2`。请谨慎选择 source/destination 标签以控制基数，并且不要无故添加请求 header 或敏感身份。将缺失事件视为流量未发生的证据之前，请检查 `hubble_lost_events_total` 和 peer 可用性。

### Prometheus 集成

Chart 会在 Cilium 命名空间中创建 headless `hubble-metrics` Service，默认公开端口 **9965**。其 Service 标签 `k8s-app=hubble` 用于发现；该 Service 选择带有 `k8s-app=cilium` 标签的 agent Pod。Prometheus 应发现各个 endpoint，而不是依赖单个静态 DNS 目标。

对于现有的 Prometheus Operator 和 ServiceMonitor CRD，请将此片段合并到 release 值中。`release: monitoring` 只是一个示例：它必须与您的 Prometheus `serviceMonitorSelector` 匹配，并且其命名空间选择器必须包含 ServiceMonitor 的命名空间。Prometheus 未选择的资源不会被抓取。

```yaml
# hubble-servicemonitor-values.yaml
hubble:
  metrics:
    serviceMonitor:
      enabled: true
      labels:
        release: monitoring
```

Chart 的 ServiceMonitor 使用名为 `hubble-metrics` 的端口和 Cilium 命名空间的 endpoint。没有 Operator 时，请在实际的 Prometheus 配置中配置等效的 Kubernetes 服务发现。创建无关的 ConfigMap 不会配置 Prometheus。`*.hubble-metrics.cilium.io` 用于指标 TLS 身份配置；它不是端口 9091 上的公共抓取目标。

Grafana dashboard 查询 Prometheus 指标；Hubble UI 的服务图查询 Relay。导入与已启用插件和标签匹配的 dashboard。对于 HTTP payload 不可观测的流量，HTTP dashboard 将为空。

### 流导出与保留

对于节点本地的轮换文件，可选择合并 `hubble-export-values.yaml`。字段掩码特意保留网络元数据；它不会导出完整 HTTP header。

```yaml
# hubble-export-values.yaml
hubble:
  export:
    static:
      enabled: true
      filePath: /var/run/cilium/hubble/events.log
      fileMaxSizeMb: 10
      fileMaxBackups: 5
      fieldMask:
      - time
      - source.namespace
      - source.pod_name
      - destination.namespace
      - destination.pod_name
      - l4
      - IP
      - node_name
      - is_reply
      - verdict
      - drop_reason_desc
```

静态 exporter 在每个节点上写入文件，并根据其文件设置进行轮换。如果事件必须在节点丢失后仍然保留，请安排单独的 collector、访问控制和存储保留。静态配置变更需要 rollout agent；动态 exporter 支持不同的更新行为。Exporter 过滤器和字段掩码可以有意省略事件/字段，有限的 buffer 仍可能丢失观测结果。

## 实时威胁检测

Hubble 为调查提供证据；它不包含一个可使其成为完整 IDS、WAF 或自动隔离系统的开关。不存在名为 `enable-threat-detection`、`enable-anomaly-detection` 或 `alert-to-slack` 的受支持 Cilium 设置。

反复被拒绝的目标可能表明扫描；流量峰值可能有必要调查。这些观测结果不是攻击的证据。请将它们与应用身份验证日志、workload 变更、API audit 事件，以及在已部署的情况下 Tetragon 运行时事件关联起来。SQL injection、XSS 和 command injection 需要合适的应用/WAF/检测规则；单独的正常 HTTP 流记录不会对它们进行分类。

对于告警，请针对正常流量、缺失数据和事件丢失定义并测试外部 Prometheus/SIEM 规则。速率限制、firewall 隔离和响应自动化均为单独配置的控制措施。限定响应范围并提供恢复路径；不要自动隔离每一个记录了被丢弃数据包的 Pod。

## 实验：Hubble 安装与使用

本实验使用两个**全新且独立的命名空间**，以便宽泛的允许规则无法使 default-deny 练习失效。它不会创建数据库或外部 API。命令是用于测试集群的示例；文档审计检查了 schema 和本地 fixture，而非实时部署。

### 1. 创建并检查 Workload

保存 `visibility-app.yaml`。client 和 server 镜像与 Cilium CLI 的版本化测试默认值匹配。backend anti-affinity 需要第二个可调度节点，从而使 frontend 到 backend 的路径跨节点。

```yaml
# visibility-app.yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend
  labels:
    app: frontend
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: v1
kind: Pod
metadata:
  name: outsider
  labels:
    app: outsider
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      automountServiceAccountToken: false
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: frontend
            topologyKey: kubernetes.io/hostname
      containers:
      - name: http
        image: quay.io/cilium/json-mock:v1.4.1@sha256:6a66df90808a39c02e7a9d58af7bf0e54d8f8b7d4bc528f48c891969a7049195
        ports:
        - containerPort: 8080
          name: http
        readinessProbe:
          httpGet:
            path: /
            port: http
---
apiVersion: v1
kind: Service
metadata:
  name: backend
spec:
  selector:
    app: backend
  ports:
  - name: http
    port: 8080
    targetPort: http
    protocol: TCP
```
```bash
set -eu
for ns in cilium-security-demo cilium-deny-demo; do
  kubectl create namespace "$ns"
  kubectl label namespace "$ns" audit-lab=security-visibility
  kubectl --namespace "$ns" apply -f visibility-app.yaml
  kubectl --namespace "$ns" wait --for=condition=Ready pod/frontend pod/outsider --timeout=120s
  kubectl --namespace "$ns" rollout status deployment/backend --timeout=120s
  for client in frontend outsider; do
    kubectl --namespace "$ns" exec "$client" -- \
      curl --fail --silent --show-error --max-time 5 http://backend:8080/
  done
done
```

应用策略前，两个命名空间中的两个 client 都必须能够访问 backend。如果不能，请先解决就绪状态、调度、DNS 和网络问题。不要从任意 curl 错误推断出策略拒绝。

### 2. 应用并观察 HTTP 策略

保存 `backend-http.yaml`。它允许 `frontend` 身份向 backend TCP 8080 发出 `GET /`。不应有宽泛的 ingress 规则与此示例重叠：L4 allow 可以绕过预期的 L7 限制。

```yaml
# backend-http.yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-http
  namespace: cilium-security-demo
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-security-demo
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: GET
          path: /
```
```bash
kubectl apply -f backend-http.yaml
# After the endpoint has realized the policy:
kubectl -n cilium-security-demo exec frontend -- \
  curl --fail --silent --show-error --max-time 5 http://backend:8080/
# Display the HTTP response code; do not use --fail here.
kubectl -n cilium-security-demo exec frontend -- \
  curl --silent --show-error --max-time 5 --output /dev/null \
    --write-out '%{http_code}\n' --request POST http://backend:8080/
# A separate client is not in the allowed identity selector.
kubectl -n cilium-security-demo exec outsider -- \
  curl --silent --show-error --max-time 5 http://backend:8080/
hubble observe --namespace cilium-security-demo --verdict DROPPED --last 100
```

策略实现后，预计 frontend `GET /` 成功，其 `POST /` 收到代理的 HTTP 403。outsider 的新连接应在 L3/L4 被拒绝。关联请求时间、endpoint 和 Hubble 事件；DNS 错误、缺失的 container 和无关的 HTTP 错误并不是成功的拒绝测试。使用 Hubble UI 检查生成的依赖边和丢弃。

对于需要数据库和外部 API 的真实 backend，下面的**可选依赖策略**说明了 egress。此实验不会应用它：必须将 `database` 和 `api.example.com` 替换为实际依赖项。请先验证 DNS endpoint。

```yaml
# backend-dependencies.yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-dependencies
  namespace: cilium-security-demo
spec:
  endpointSelector:
    matchLabels:
      app: backend
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
      rules:
        dns:
        - matchPattern: '*'
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-security-demo
        k8s:app: database
    toPorts:
    - ports:
      - port: '3306'
        protocol: TCP
  - toFQDNs:
    - matchName: api.example.com
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

允许 TCP 和 UDP DNS，并且 DNS 代理规则让 Cilium 能够观察 `toFQDNs` 所用的响应。允许 DNS 查询不同于允许后续连接到其解析出的 IP。此策略的 DNS `*` 允许所有查询名称；它不是域名 blocklist。

### 3. 单独验证 Default Deny

保存 `deny-except-dns.yaml`。显式 `policyTypes` 会在两个方向激活隔离；`ingress: []` **不包含 ingress allow 规则**。唯一的 egress 例外仅允许到匹配解析器 Pod 的 DNS。

```yaml
# deny-except-dns.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-except-dns
  namespace: cilium-deny-demo
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```
```bash
kubectl apply -f deny-except-dns.yaml
kubectl -n cilium-deny-demo exec frontend -- \
  curl --silent --show-error --max-time 5 http://backend:8080/
hubble observe --namespace cilium-deny-demo --verdict DROPPED \
  --drop-reason-desc POLICY_DENIED --last 100
```

不要将空 ingress 列表替换为 `ingress: [{}]`：这是一条允许所有 ingress 的规则。标准 NetworkPolicy allow 是叠加的，因此另一个策略可能会开放流量。Cilium deny 规则和集群策略可以施加进一步限制。此命名空间练习并不声称隔离 host-network 流量或每一条源自主机的路径。

### 4. 检查 JSON 并导出本地摘要

将以下内容保存为 `flow-summary.jq`。`--output jsonpb` 提供带有 `.flow` 的 protobuf 响应信封；这避免依赖 CLI 旧版 `json` 兼容性设置。

```text
[.[] | select(.flow != null) | .flow] as $flows
| {
    flow_records: ($flows | length),
    other_records: (length - ($flows | length)),
    policy_denied_records: (
      [$flows[] | select(.verdict == "DROPPED"
                        and .drop_reason_desc == "POLICY_DENIED")] | length
    ),
    dropped_by_reason: (
      [$flows[] | select(.verdict == "DROPPED")]
      | group_by(.drop_reason_desc // "UNKNOWN")
      | map({reason: (.[0].drop_reason_desc // "UNKNOWN"), records: length})
    )
  }
```

```bash
set -eu
hubble observe --namespace cilium-deny-demo --last 100 --output jsonpb > flows.jsonl
jq --slurp --from-file flow-summary.jq flows.jsonl
```

结果统计的是**此有限样本中的流记录**，而不是唯一攻击、连接或所有集群数据包。它会单独统计非流记录；请检查它们以获取丢失/状态信息。对于实时本地过滤：

```bash
hubble observe --namespace cilium-deny-demo --follow --output jsonpb |
  jq --unbuffered -c 'select(.flow.verdict == "DROPPED"
    and .flow.drop_reason_desc == "POLICY_DENIED")'
```

此 pipeline 在本地输出。通知需要单独配置的集成、凭证、重试/去重策略以及对流失败的处理。

### 5. 清理测试命名空间

检查命名空间名称后，仅删除此实验的 workload 和策略。所有权检查会在查找失败或标签不同时停止。

```bash
set -eu
for ns in cilium-security-demo cilium-deny-demo; do
  LAB_OWNER=$(kubectl get namespace "$ns" -o jsonpath='{.metadata.labels.audit-lab}')
  test "$LAB_OWNER" = security-visibility
  kubectl delete namespace "$ns"
done
```

## 主要参考资料

- [Cilium 策略执行](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/security/policy/intro.rst)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [HTTP 策略](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/security/policy/layer7.rst)
- [DNS 策略](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/security/dns.rst)
- [Hubble 设置](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/observability/hubble/setup.rst)
- [指标](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/observability/metrics.rst)
- [流 exporter](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/observability/hubble/configuration/export.rst)
- [WireGuard](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/security/network/encryption-wireguard.rst)
- [IPsec](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/security/network/encryption-ipsec.rst)
- [双向身份验证](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
- [ztunnel](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/security/network/encryption-ztunnel.rst)
- [Tetragon](https://raw.githubusercontent.com/cilium/tetragon/main/README.md)
- [Hubble CLI 过滤器](https://raw.githubusercontent.com/cilium/hubble/v1.20.2/vendor/github.com/cilium/cilium/hubble/cmd/observe/flows.go)

[返回主页](README.md)

## 测验

在[主题测验](../../quizzes/networking/cilium/06-security-visibility-quiz.md)中测试策略、加密和可观测性的边界。

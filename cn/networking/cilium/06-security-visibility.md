# 安全与可见性

> **审查基线**：Cilium 1.20.3；Cilium CLI 0.20.1；Hubble CLI 1.20.2。
> **最后审核**：2026 年 10 月 16 日。Kubernetes 1.33–1.36 是 Cilium 1.20 的兼容版本范围；选择符合 API server 支持的版本偏差范围的 kubectl。

## 实验环境设置

使用现有的 Cilium 1.20.3 测试集群，该集群至少有两个可调度的 Linux 节点、正常工作的 DNS，并已启用策略执行。遵循[安装和平台先决条件](README.md)，包括 EKS 限制和经过验证的 CLI 下载。本示例不会安装或替换 CNI。需要 Helm、kubectl、Cilium 和 Hubble CLI，以及 jq。

本实验假设 `kube-system` 中有带 `k8s-app=kube-dns` 标签的 CoreDNS Pod。请确认实际的解析器路径；NodeLocal DNS 或其他发行版可能需要使用不同的目的地址/端口。集群中已有的策略、代理配置和平台控制措施都可能影响结果。

### 安装和设置 Hubble

保存 `hubble-values.yaml`。此片段会启用本地服务器、Relay、UI 和指定的指标插件。将其应用到**图表版本相同的现有 release**；请先检查保留的安装值。升级版本时，应使用升级流程，而不是盲目重复使用旧值。

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
  --version 1.20.3 --reuse-values --values hubble-values.yaml --wait
cilium status --wait
# Terminal 1: keep this process running; stop it with Ctrl-C.
cilium hubble port-forward
```

在另一个终端中验证 API 连通性。端口转发仅在本地运行；它不会通过公共 LoadBalancer 发布 Relay 或 UI。

```bash
# Terminal 2
hubble status
hubble observe --last 20
# Optional UI; keep its local forwarding process running while using it.
cilium hubble ui
```

## Cilium 的安全功能

Cilium 将网络策略与端点身份以及可选加密相结合。Hubble 可观测由此产生的网络事件。评估安全需求时，了解这些功能的边界很重要。

### Cilium 安全架构

| 职责 | 组件和范围 |
| --- | --- |
| 网络微分段 | Cilium L3/L4 策略根据身份、地址、端口和方向进行选择。命名空间范围的 CiliumNetworkPolicy 会选择其命名空间中的端点。 |
| HTTP 策略 | 当代理能够查看 HTTP 流量时，Cilium 的 Envoy 集成会筛选方法、路径和标头。DNS 策略使用 DNS 代理。 |
| DNS/FQDN 控制 | DNS 规则控制查询；`toFQDNs` 允许使用从已观测 DNS 答案中获知的目的 IP。这并不是自动的恶意域名信誉信息源。 |
| 节点传输加密 | IPsec 或 WireGuard 会保护节点之间受支持的流量。覆盖范围取决于模式和配置。 |
| 网络调查 | Hubble 记录流元数据和策略判定结果；Relay、CLI 和 UI 可用于查看这些信息。 |
| 进程和系统调用安全 | **Tetragon** 是一个独立项目，用于运行时事件和已配置的执行措施。启用 Hubble 不会安装它。 |
| 威胁检测和响应 | 必须配置外部警报规则、SIEM/WAF 和响应控制器，以实现预期的检测和操作。 |

### 网络和应用安全

使用最小特权策略限制横向移动，并通过明确的出站规则限制依赖项。安全身份来自与安全相关的标签；它们不一定是每个 Pod 唯一的身份，也不会验证最终用户身份。

当前的 Cilium 策略支持 HTTP 和 DNS L7 规则。如果能够查看 gRPC 的 HTTP/2 流量，则可使用 HTTP 方法/路径/标头规则。Kafka 主题策略已不再受支持。带值的 HTTP `headers` 条目是字面匹配，并非用于身份验证的正则表达式。`Authorization` 标头的存在与格式并不能验证 JWT、其颁发者、签名或授权声明。应使用应用的身份验证层或已配置的网关来完成验证。

端口 8443 上的 HTTP 规则不会解密 HTTPS。要让 HTTP 策略检查加密的应用数据，必须进行 TLS 终止，或采用单独支持的检查方案。不要仅为实现 L7 检查而绕过服务网格的加密。

### 身份、身份验证和加密

基于 SPIRE 的 Cilium **双向身份验证为 Beta，但在 1.20 中已弃用**（已在 1.21 预发行版中移除；1.20 升级说明将双向身份验证标记为已弃用，并指出 ztunnel 透明加密是替代方案，因此不要在新设计中选择它）：它会为安全身份执行带外握手。仅靠该握手并不会加密应用流量。其文档列出的限制包括不支持 ClusterMesh，且无法与任意外部 mTLS 系统互操作。单独的 **ztunnel 工作负载 mTLS 功能同样处于 Beta 阶段**；它有自己的注册和证书先决条件。不能将任一功能描述为身份选择器自动带来的结果。

### 加密配置

以下是**可选的 Helm 配置片段**，不可同时启用。请根据计划中的安装/更改选择其中一种，并验证内核、路由和平台先决条件。

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

WireGuard 需要内核支持，以及节点间端口 51871 上的 UDP 通路。启用 IPsec 前，必须在 Cilium 所在的命名空间中准备好格式正确且受到安全管理的 `cilium-ipsec-keys` Secret；请遵循官方密钥创建和轮换流程。仅在 ConfigMap 中填写密钥文件名，并不能配置该密钥或其卷。

默认情况下，这些模式会保护跨节点的、由 Cilium 管理且受支持的 Pod 流量；同一节点上的流量不会由这些节点隧道加密。发往任意外部目的地的流量不会自动受到保护。WireGuard 节点间加密（`encryption.nodeEncryption`）是一个独立的 Beta 选项，已在 1.21 预发行版中弃用，并计划在 1.22 中移除；默认情况下，控制平面节点不包含在该扩展范围内，但由 Cilium 管理的跨节点 Pod 流量仍可加密。请验证实际的数据包路径，并在需要时使用应用 TLS。主机防火墙兼容性也取决于加密模式：主机策略无法与 IPsec 配合使用（1.21 预发行版的主机策略已知问题中有相关说明）。

## 使用 Hubble 实现网络可见性

Hubble 会接收数据路径、代理和 agent 事件，并使用 Kubernetes 元数据丰富这些事件。它并非只是一个定期轮询所有 eBPF map 的读取器。

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

服务器会维护有界的内存历史记录。Relay 会查询多个服务器；它不是持久化数据库。UI 提供流量探索和服务依赖关系图，而 CLI 支持明确的筛选条件。没有匹配记录可能意味着没有流量、筛选条件错误、对等端不可用、缺少 L7 可见性，或者事件已被覆盖/丢失。

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

`--pod namespace/name` 会匹配任一端点；使用 `--from-pod`/`--to-pod` 指定方向。Pod 名称不是标签选择器：按标签选择时使用 `--from-label` 或 `--to-label`。不要将 `--namespace` 与 `--from-pod`/`--to-pod` 组合使用；CLI 会拒绝这种组合。

`DROPPED` 是一种判定结果。`POLICY_DENIED` 是丢弃原因，应使用 `--drop-reason-desc` 选择。HTTP 状态码前缀应使用 `4+` 和 `5+`，而不是 `4..` 和 `5..`。HTTP 筛选条件需要代理生成的 L7 事件；被丢弃的 TCP 连接不一定有 HTTP 状态码。

## 网络可见性和监控

### Hubble 指标

启用的插件提供不同类型的观测数据：

| 插件 | 指标示例 | 含义和限制 |
| --- | --- | --- |
| `flow` | `hubble_flows_processed_total` | 按协议/类型/判定结果统计已处理的流事件；并非唯一请求数，也不代表每条路径上的数据包数。 |
| `drop` | `hubble_drop_total{reason="POLICY_DENIED"}` | 已观测到的丢弃事件；原因标签为枚举名称。 |
| `tcp` | `hubble_tcp_flags_total` | 已观测到的 TCP 标志；不是通用的 RTT、重传或并发连接指标。 |
| `dns` | `hubble_dns_queries_total`、`hubble_dns_responses_total` | 已观测到的 DNS 查询/响应和响应码；不是通用的 DNS 延迟直方图。 |
| `httpV2` | `hubble_http_requests_total`、`hubble_http_request_duration_seconds` | 根据 HTTP 响应流得出的请求数/状态码和以秒为单位的持续时间。需要具备 HTTP 可见性。 |

不要同时启用 `http` 和 `httpV2`。谨慎选择源/目的地标签以控制基数；没有必要时，避免添加请求标头或敏感身份。在将缺失事件视为流量未发生的证明之前，请检查 `hubble_lost_events_total` 和对等端可用性。

### Prometheus 集成

该图表会在 Cilium 命名空间中创建无头的 `hubble-metrics` Service，默认公开端口 **9965**。其 Service 标签 `k8s-app=hubble` 用于服务发现；Service 会选择带有 `k8s-app=cilium` 标签的 agent Pod。Prometheus 应发现各个端点，而不是依赖单个静态 DNS 目标。

如果已有 Prometheus Operator 和 ServiceMonitor CRD，请将此片段合并到 release 值中。`release: monitoring` 只是示例：它必须与 Prometheus 的 `serviceMonitorSelector` 匹配，并且其命名空间选择器必须包含 ServiceMonitor 所在的命名空间。如果 Prometheus 未选择某个资源，就不会对其进行抓取。

```yaml
# hubble-servicemonitor-values.yaml
hubble:
  metrics:
    serviceMonitor:
      enabled: true
      labels:
        release: monitoring
```

图表的 ServiceMonitor 使用名为 `hubble-metrics` 的端口和 Cilium 命名空间中的端点。没有 Operator 时，请在实际的 Prometheus 配置中设置等效的 Kubernetes 服务发现。创建一个无关的 ConfigMap 并不能配置 Prometheus。`*.hubble-metrics.cilium.io` 用于指标 TLS 身份配置；它不是端口 9091 上的公共抓取目标。

Grafana 仪表板会查询 Prometheus 指标；Hubble UI 的服务图会查询 Relay。导入与已启用插件和标签相匹配的仪表板。对于 HTTP 负载不可观测的流量，HTTP 仪表板将没有数据。

### 流量导出和保留

对于节点本地的轮转文件，可选择合并 `hubble-export-values.yaml`。字段掩码会有意保留网络元数据；它不会导出完整的 HTTP 标头。

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

静态导出器会在每个节点上写入文件，并按照其文件设置轮转。如果需要在节点丢失后保留事件，请另外配置采集器、访问控制和存储保留策略。静态配置更改需要滚动更新 agent；动态导出器支持不同的更新行为。导出器筛选条件和字段掩码可能会有意省略事件/字段，而有限的缓冲区仍可能导致观测数据丢失。

## 实时威胁检测

Hubble 为调查提供证据；它没有一个开关可以让自己成为完整的 IDS、WAF 或自动隔离系统。Cilium 不支持名为 `enable-threat-detection`、`enable-anomaly-detection` 或 `alert-to-slack` 的设置。

重复出现的被拒目的地可能表示正在进行扫描；流量激增可能值得调查。这些观测并不能证明发生了攻击。应将其与应用身份验证日志、工作负载变更、API 审计事件，以及已部署时的 Tetragon 运行时事件进行关联。SQL 注入、XSS 和命令注入需要适当的应用/WAF/检测规则；单独的常规 HTTP 流记录无法对其分类。

如需告警，请针对正常流量、数据缺失和事件丢失定义并测试外部 Prometheus/SIEM 规则。速率限制、防火墙隔离和响应自动化都是需要单独配置的控制措施。请限制响应范围并提供恢复路径；不要仅因某个 Pod 记录到一个丢弃数据包就自动隔离它。

## 实验：安装和使用 Hubble

本实验使用两个**全新且相互独立的命名空间**，以避免宽泛的允许规则破坏默认拒绝练习。本实验不会创建数据库或外部 API。这些命令适用于测试集群；文档审计检查了架构和本地测试样例，并未检查实时部署。

### 1. 创建并检查工作负载

保存 `visibility-app.yaml`。客户端和服务器镜像与 Cilium CLI 的版本化测试默认值相匹配。后端反亲和性要求有第二个可调度节点，以确保前端到后端的路径跨节点。

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

在应用策略之前，两个命名空间中的两个客户端都必须能够访问后端。如果不能，请先解决就绪状态、调度、DNS 和网络问题。不要根据任意 curl 错误推断策略拒绝。

### 2. 应用并观测 HTTP 策略

保存 `backend-http.yaml`。该策略允许 `frontend` 身份向后端 TCP 8080 发送 `GET /` 请求。此示例不应与宽泛的入站规则重叠：L4 允许规则可能绕过预期的 L7 限制。

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

策略生效后，预期 frontend 的 `GET /` 会成功，而其 `POST /` 会收到代理返回的 HTTP 403。outsider 发起的新连接应在 L3/L4 被拒绝。请将请求时间、端点和 Hubble 事件进行关联；DNS 错误、容器缺失和无关的 HTTP 错误都不代表拒绝测试成功。使用 Hubble UI 检查生成的依赖关系边和丢弃事件。

对于需要数据库和外部 API 的真实后端，以下**可选依赖策略**展示了出站流量的配置方式。本实验不会应用该策略：必须将 `database` 和 `api.example.com` 替换为实际依赖项。请先确认 DNS 端点。

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

允许使用 TCP 和 UDP 进行 DNS 通信，并且 DNS 代理规则允许 Cilium 观测 `toFQDNs` 使用的答案。允许 DNS 查询与允许后续连接到解析出的 IP 是两回事。此策略中的 DNS `*` 会允许查询所有名称；它不是域名阻止列表。

### 3. 单独验证默认拒绝

保存 `deny-except-dns.yaml`。显式的 `policyTypes` 会在两个方向上启用隔离；`ingress: []` **不包含任何入站允许规则**。唯一的出站例外是允许连接到匹配的解析器 Pod 进行 DNS 通信。

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

不要将空的入站列表替换为 `ingress: [{}]`：那是一条允许所有入站流量的规则。标准 NetworkPolicy 的允许规则会叠加生效，因此其他策略可以开放流量。Cilium deny 规则和集群策略还可以施加更多限制。本命名空间练习并不声称能够隔离主机网络流量或所有源自主机的路径。

### 4. 检查 JSON 并导出本地摘要

将以下内容保存为 `flow-summary.jq`。`--output jsonpb` 会输出包含 `.flow` 的 protobuf 响应封装；这样就无需依赖 CLI 的旧版 `json` 兼容性设置。

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

结果统计的是**此有限样本中的流记录**，而不是唯一攻击、连接或集群中的所有数据包。它会单独统计非流记录；请检查这些记录以了解丢失/状态信息。若要实时应用本地筛选条件：

```bash
hubble observe --namespace cilium-deny-demo --follow --output jsonpb |
  jq --unbuffered -c 'select(.flow.verdict == "DROPPED"
    and .flow.drop_reason_desc == "POLICY_DENIED")'
```

此管道会在本地打印结果。通知需要单独配置集成、凭据、重试/去重策略，以及对流处理失败的处理方式。

### 5. 清理测试命名空间

检查命名空间名称后，只删除本实验的工作负载和策略。如果查找失败或标签不匹配，所有权检查就会停止。

```bash
set -eu
for ns in cilium-security-demo cilium-deny-demo; do
  LAB_OWNER=$(kubectl get namespace "$ns" -o jsonpath='{.metadata.labels.audit-lab}')
  test "$LAB_OWNER" = security-visibility
  kubectl delete namespace "$ns"
done
```

## 主要参考资料

- [Cilium 策略执行](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/policy/intro.rst)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [HTTP 策略](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/policy/layer7.rst)
- [DNS 策略](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/dns.rst)
- [Hubble 设置](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/observability/hubble/setup.rst)
- [指标](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/observability/metrics.rst)
- [流导出器](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/observability/hubble/configuration/export.rst)
- [WireGuard](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/network/encryption-wireguard.rst)
- [IPsec](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/network/encryption-ipsec.rst)
- [双向身份验证](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
- [ztunnel](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/network/encryption-ztunnel.rst)
- [Tetragon](https://raw.githubusercontent.com/cilium/tetragon/main/README.md)
- [Hubble CLI 筛选条件](https://raw.githubusercontent.com/cilium/hubble/v1.20.2/vendor/github.com/cilium/cilium/hubble/cmd/observe/flows.go)

[返回主页](README.md)

## 测验

通过[主题测验](../../quizzes/networking/cilium/06-security-visibility-quiz.md)测试你对策略、加密和可观测性边界的理解。

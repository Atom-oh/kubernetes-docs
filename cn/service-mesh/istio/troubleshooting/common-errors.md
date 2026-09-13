# Istio 常见错误及解决方案

> **最后更新**：2026 年 9 月 11 日 · CLI/配置检查：Istio 1.31.0

从观测故障、生效配置和工作负载模式入手。以下命令是诊断示例，不是重置网格的指令。针对 Kubernetes/EKS 版本检查[安装兼容性指南](../01-installation.md)。

示例使用现有应用命名空间 app、端口 8080 的 Deployment/Service myapp、入口命名空间 istio-ingress 和默认集群 DNS 后缀。替换为实际资源和域名。Deployment YAML 块是**现有 Deployment 的战略合并片段**，不是完整新应用。本次审查未执行集群部署或生产工作负载测试。

```bash
NS=app
GW_NS=istio-ingress
ISTIO_NS=istio-system
: "${POD:?Set the exact application Pod name}"
kubectl config current-context
istioctl version
kubectl -n "$NS" get pod "$POD" -o wide
```

## 目录

1. [Pod 终止期间的连接错误](#connection-errors-during-pod-termination)
2. [Sidecar 注入问题](#sidecar-injection-issues)
3. [mTLS 连接失败](#mtls-connection-failure)
4. [VirtualService 路由失败](#virtualservice-routing-failure)
5. [Gateway 配置问题](#gateway-configuration-issues)
6. [内存和性能问题](#memory-and-performance-issues)
7. [证书到期](#certificate-expiration)
8. [DNS 解析失败](#dns-resolution-failure)
9. [Envoy 初始化超时](#envoy-initialization-timeout)
10. [调试工具](#debugging-tools)

## Pod 终止期间的连接错误 {#connection-errors-during-pod-termination}

### 问题描述

关闭期间可能出现连接重置、管道断裂、EOF 和 HTTP 503。它们本身不能证明 Envoy 先退出。关联应用/代理日志、响应标志、Pod 删除时间和 EndpointSlice 变化。

### 根因

传统应用容器与列在 containers 下的 Sidecar 没有保证的关闭顺序。应用仍需代理时，代理可能已退出；应用也可能在现有请求完成前停止接收工作。Kubernetes 原生 Sidecar 则使用带 restartPolicy:Always 的 initContainers，并在主容器之后终止。

Pod 宽限期包括 preStop 执行。不总是 30 秒，已经退出的进程之后也不会再次被终止。端点更新、负载均衡器传播和长连接可产生额外故障窗口。

### 解决方案

#### 方法 1：规划应用和代理关闭预算

此注解配置代理排空；**不会**安装 preStop 钩子或无条件等待每个活动请求：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations:
        proxy.istio.io/config: |
          terminationDrainDuration: 30s
          holdApplicationUntilProxyStarts: true
      labels: {}
    spec:
      terminationGracePeriodSeconds: 60
```

30/60 秒是示例，不是通用最小值。同时规划应用关闭、钩子和代理排空。holdApplicationUntilProxyStarts 关乎**启动**，不是关闭顺序。ProxyConfig 更改需要新 Pod 才生效。

1.31 中，普通 terminationDrainDuration 路径基于时间。启用 EXIT_ON_ZERO_ACTIVE_CONNECTIONS 时，代理改为等待最小排空期，再轮询下游监听器连接数；该路径不将普通排空定时器作为固定上限。Kubernetes 宽限限制和缺失/错误统计仍适用。在代表性连接下验证所选行为。

#### 方法 2：考虑原生 Sidecar 顺序

对受支持 Kubernetes/Istio 组合，此注解为新建且符合注入条件的 Pod 选择原生注入：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations:
        sidecar.istio.io/nativeSidecar: 'true'
      labels: {}
    spec: {}
```

Kubernetes 功能自 1.33 起稳定；Istio 原生 Sidecar 注解在文档中为 Alpha。验证实际注入的 initContainers 和应用关闭行为。仅顺序不保证零失败请求，也不会无限等待超过 Pod 宽限期。Ambient 工作负载没有可如此配置的每 Pod Envoy。

没有文档规定的 sidecar.istio.io/terminationGracePeriodSeconds 注解。设置真实 spec.terminationGracePeriodSeconds 字段。

#### 方法 3：安装范围默认值

以下是 **istioctl 安装输入**，不是交给已移除的集群内 Istio Operator 协调的资源：

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      terminationDrainDuration: 30s
      holdApplicationUntilProxyStarts: true
```

通过安装所有者审核渲染更改，并有计划地滚动发布受影响工作负载。旧 shell/netstat preStop 循环无界、统计监听套接字，并假定代理镜像中存在工具。它不能可靠等待应用工作完成。

### 验证方法

```bash
kubectl -n "$NS" get pod "$POD" -o json
kubectl -n "$NS" logs -f "$POD" -c istio-proxy
kubectl -n "$NS" get events --field-selector "involvedObject.name=$POD"
kubectl -n "$NS" get endpointslices.discovery.k8s.io \
  -l kubernetes.io/service-name=myapp -o yaml
```

Pod 仍存在时捕获日志。--previous 获取同一 Pod 内前一容器实例；不表示“正在终止的当前容器”，也不恢复任意已删除 Pod 日志。

### 最佳实践

实现应用 SIGTERM 处理和真实就绪约定。除非应用或探针读取 /tmp/not-ready，否则创建该文件无任何影响。有界 preStop 延迟可提供传播时间，但不证明端点收敛，也不替代应用优雅关闭。不存在通用的应用 sleep 禁令或 60 秒最小值。禁用写入重试时测量原始 HTTP/非 HTTP 失败；参阅[滚动发布比较](../comparison/03-sidecar-vs-ambient.md)。

## Sidecar 注入问题 {#sidecar-injection-issues}

### 问题 1：未注入 Sidecar

判断代理缺失前，同时检查普通和原生 Sidecar 位置：

```bash
kubectl -n "$NS" get pod "$POD" -o jsonpath='{.spec.containers[*].name}{"\n"}{.spec.initContainers[*].name}{"\n"}'
kubectl get namespace "$NS" --show-labels
kubectl -n "$NS" get deployment myapp -o yaml
istioctl x check-inject "$POD" -n "$NS"
kubectl get mutatingwebhookconfigurations
kubectl -n "$ISTIO_NS" get pods -l app=istiod --show-labels
kubectl -n "$ISTIO_NS" logs -l app=istiod --all-containers=true --tail=200
```

Ambient 纳管有意不包含 istio-proxy 应用 Sidecar。Sidecar 模式中，检查命名空间修订/标签、Pod 模板标签、hostNetwork、webhook 选择器和准入事件。自动注入排除主机网络 Pod 和指定系统命名空间。

按[注入指南](../advanced/07-sidecar-injection.md)使用目标安装的修订/标签或旧注入标签。不要组合冲突的 istio-injection 和 istio.io/rev 选择。标签影响新建 Pod；不会改造现有 Pod。审核影响后，仅通过发布所有者重建目标工作负载。

首选每 Pod 覆盖是在工作负载 Pod 模板下设置**标签**：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations: {}
      labels:
        sidecar.istio.io/inject: 'true'
    spec: {}
```

对应注解已弃用。false 标签可能是有意排除，不是应盲目覆盖的错误。true 标签也不绕过全部 webhook 选择或平台限制。注入由 Istiod 提供；旧 app=sidecar-injector 日志选择器不标识当前集成注入器。

### 问题 2：Sidecar 资源不足

检查容器终止原因、事件、用量和节流。OOMKilled 可能表示内存 limit 问题；CrashLoopBackOff 是多种原因都可能导致的重启/退避状态。runAsNonRoot/非数值用户验证错误是安全上下文/镜像问题，增加 RAM 无法修复。

若测量证明需要资源更改，在 Pod 模板同时设置 requests 和 limits。这些示例数量需要按工作负载规划：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations:
        sidecar.istio.io/proxyCPU: 200m
        sidecar.istio.io/proxyCPULimit: 1000m
        sidecar.istio.io/proxyMemory: 256Mi
        sidecar.istio.io/proxyMemoryLimit: 512Mi
      labels: {}
    spec: {}
```

验证新注入资源设置及命名空间 LimitRange/ResourceQuota。不要仅为通过准入而覆盖镜像安全设置。

## mTLS 连接失败 {#mtls-connection-failure}

### 问题描述

上游连接错误、503 和 WRONG_VERSION_NUMBER 可由 TLS、协议、端点或网络引起。PeerAuthentication 控制**接受的入站 mTLS**。DestinationRule TLS 设置控制客户端 Envoy 的出站 TLS。将客户端 PeerAuthentication 设为 STRICT，本身不会强制客户端发起 mTLS。

### PeerAuthentication 和 DestinationRule

启用自动 mTLS 且没有显式 DestinationRule TLS 覆盖时，Istio 为已知网格端点选择工作负载 mTLS。显式 DISABLE 覆盖可能与要求 STRICT 的目标冲突。通过所有者移除非预期覆盖，或为有意配置的 Istio mTLS 目标使用 ISTIO_MUTUAL；不要强制用于任意外部 TLS/明文服务。

下方无选择器策略在调用方已准备好严格执行后，应用于 **app 命名空间**：

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: app
spec:
  mtls:
    mode: STRICT
```

配置的根命名空间（通常 istio-system）中无选择器策略具有网格范围，不只作用于该命名空间服务。执行前审核迁移影响。Ambient 不支持通过 PeerAuthentication DISABLE 禁用传输 mTLS。身份验证和 AuthorizationPolicy 独立；403 不自动表示 TLS 失败。

### 调试命令

```bash
istioctl x describe pod "$POD" -n "$NS"
kubectl get peerauthentication -A -o yaml
kubectl get destinationrule -A -o yaml
istioctl proxy-config clusters "$POD" -n "$NS" \
  --fqdn myapp.app.svc.cluster.local -o json
istioctl proxy-config secret "$POD" -n "$NS"
```

出站集群配置使用相关调用方代理，入站策略使用接收方代理。实验性 describe 命令是诊断辅助，不证明全部路径加密。检查证书有效期、身份、信任域、实际传输套接字和响应标志。Waypoint 与 ztunnel 诊断不同；参阅 [mTLS 指南](../security/01-mtls.md)。

## VirtualService 路由失败 {#virtualservice-routing-failure}

### 问题 1：流量未被路由

404 可来自 Envoy 或应用。更改路由前先识别来源及响应详情。VirtualService 的 hosts:myapp.example.com 路由到内部 Service myapp，在附加到适当网关且请求 Host/authority 匹配时是**有效的**。前端主机与后端服务名无需相同。

网格流量匹配请求的服务主机；入口流量匹配网关准入域名，并将 VirtualService 附加到该网关。短目标名相对于配置资源命名空间解析，因此显式 FQDN 可减少跨命名空间歧义。

### 问题 2：未找到子集或没有健康上游

这组完整资源展示到命名子集的网格路由：

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp
  namespace: app
spec:
  hosts:
  - myapp.app.svc.cluster.local
  http:
  - route:
    - destination:
        host: myapp.app.svc.cluster.local
        subset: v1
        port:
          number: 8080
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
  namespace: app
spec:
  host: myapp.app.svc.cluster.local
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

Service 必须实际选择带 version:v 1 标签的就绪端点。仅 DestinationRule 子集名称匹配不会创建 Pod、修复 Service 选择器或使端点健康。检查目标 Service 端口、协议选择、策略可见性和竞争路由。上述命名空间/主机示例假定默认 cluster.local 后缀。

### 调试

```bash
istioctl analyze -n "$NS"
istioctl proxy-config routes "$POD" -n "$NS"
istioctl proxy-config endpoints "$POD" -n "$NS"
kubectl -n "$NS" get svc myapp -o yaml
kubectl -n "$NS" get pods -l app=myapp --show-labels
kubectl -n "$NS" get endpointslices.discovery.k8s.io \
  -l kubernetes.io/service-name=myapp -o yaml
```

Analyze 是静态配置辅助；应在实际承载请求的代理检查生效路由/集群/端点。配置传播不是即时的。入口请求路由到 Service 后，不会自动继承另一仅网格 VirtualService 的子集选择。


## Gateway 配置问题 {#gateway-configuration-issues}

### 问题 1：流量未到达 Gateway

HTTP 响应前连接被拒绝或超时，可能表示 DNS、监听器/Service 端口不匹配、缺失负载均衡目标或网络过滤。先定位实际网关 Deployment/Service；命名空间和名称取决于安装方法。

```bash
kubectl -n "$GW_NS" get svc,pods --show-labels
kubectl -n "$GW_NS" get gateways.networking.istio.io -o yaml
kubectl -n "$NS" get virtualservice -o yaml
# For installations using Kubernetes Gateway API instead:
kubectl get gatewayclasses.gateway.networking.k8s.io
kubectl -n "$GW_NS" get gateways.gateway.networking.k8s.io -o yaml
kubectl -n "$NS" get httproutes.gateway.networking.k8s.io -o yaml
```

检查 Service 的 loadBalancer ingress 字段：提供商可发布 IP、主机名或两者。在 EKS，还要按控制器实际配置检查负载均衡目标健康、目标类型、安全组和网络路径；重启 Istiod 不修复不健康 AWS 目标。

Istio Gateway（networking.istio.io）和 Kubernetes Gateway API（gateway.networking.k 8s.io）是不同资源。Gateway API 应检查 Accepted、Programmed 和 HTTPRoute parent 条件（如 ResolvedRefs），并查看控制器事件。网关名称拼写错误、监听器不匹配或路由附加被拒绝，需要与外部连接失败不同的修复。

### 问题 2：HTTPS 和路由附加

此示例使用 **Istio Gateway API**。将选择器替换为实际网关 Pod 标签，使用自有域名和有效证书，确保 Deployment 的 Service 暴露 443。它使用前节定义的同一后端子集：

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: myapp-gateway
  namespace: istio-ingress
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: myapp-tls-secret
    hosts:
    - myapp.example.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp-ingress
  namespace: app
spec:
  hosts:
  - myapp.example.com
  http:
  - route:
    - destination:
        host: myapp.app.svc.cluster.local
        subset: v1
        port:
          number: 8080
    retries:
      attempts: 0
  gateways:
  - istio-ingress/myapp-gateway
```

此处 SIMPLE 终止下游 TLS，因此路由使用 http。TLS PASSTHROUGH 监听器则需要适当 TLS/SNI 路由。不要将终止 TLS 的监听器与仅 tls 路由混用，也不要期望在不透明透传流量中匹配 HTTP 路径。

credentialName 引用网关工作负载可访问的凭证。本示例网关 Pod 和 TLS Secret 位于 istio-ingress：

```bash
kubectl -n "$GW_NS" create secret tls myapp-tls-secret   --cert=path/to/fullchain.pem   --key=path/to/key.pem
```

若 Secret 已受管理，使用现有证书所有者的续订流程。此命令不获取证书，也不使自签签发者可信。检查域名/SAN 匹配、提供的证书链、到期、客户端信任和网关 SDS 状态。独立 Gateway 配置对象的命名空间不能普遍替代网关工作负载的凭证命名空间。

## 内存和性能问题 {#memory-and-performance-issues}

### 问题 1：Envoy 内存用量增加

比较实际容器内存/CPU、limits、连接、路由/集群/监听器和遥测基数。大型无关 ConfigMap 或 Secret 不会自动加载到每个代理；仅该代理使用的配置和数据可解释占用。内存泄漏需要版本专属证据。

未使用配置占主要部分时，限定范围的 Sidecar 资源可限制所选 **Sidecar** 工作负载导入的配置：

```yaml
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: myapp-scope
  namespace: app
spec:
  workloadSelector:
    labels:
      app: myapp
  egress:
  - hosts:
    - ./*
    - istio-system/*
```

示例仅包含 app 和 istio-system 中服务。缩小导入前清点实际跨命名空间/外部依赖，避免 Sidecar 选择器重叠。这是配置范围限定，不是出站防火墙或 Ambient waypoint 策略。使用前述 Pod 模板注解，根据观测行为规划内存 requests/limits。

### 问题 2：延迟高

P99 超过一秒仅相对于定义的工作负载预算才是症状。更改超时前，检查应用时间、上游延迟、饱和度、CPU 节流、连接池、载荷和重试放大。

以下是前述 myapp VirtualService 的**替代方案**，添加五秒路由期限并显式禁用重试：

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp
  namespace: app
spec:
  hosts:
  - myapp.app.svc.cluster.local
  http:
  - route:
    - destination:
        host: myapp.app.svc.cluster.local
        subset: v1
        port:
          number: 8080
    retries:
      attempts: 0
    timeout: 5s
```

期限限制等待；不会使后端更快。盲目重试可放大过载并重复结果不明的写入。若特定幂等操作适合重试，应根据端到端期限明确规划预算，并测量实际尝试。参阅[重试和超时](../traffic-management/05-retry-timeout.md)。

## 证书到期 {#certificate-expiration}

### 问题描述

x 509 到期和握手失败可能涉及工作负载叶证书、签名中间/根证书、入口证书或时钟偏差。有效期取决于 CA/提供程序和配置；“十年”或“24 小时”不是通用诊断。

### 诊断和恢复

检查实际公有信任包和已加载工作负载证书：

```bash
# Public trust bundle, not a private CA key.
kubectl -n "$NS" get configmap istio-ca-root-cert \
  -o jsonpath='{.data.root-cert\.pem}' > root-cert.pem
openssl crl2pkcs7 -nocrl -certfile root-cert.pem |
  openssl pkcs7 -print_certs -text -noout
istioctl proxy-config secret "$POD" -n "$NS"
kubectl -n "$ISTIO_NS" logs -l app=istiod --all-containers=true --tail=200
```

自定义集成可能使用不同于标准的信任 ConfigMap；检查配置的 CA 提供程序。PKCS7 检查显示 PEM 包内全部证书，不只是第一张。将有效期与当前 UTC 时间、CA/CSR 错误、身份令牌、Istiod/SDS 可达性和证书续订流程关联。

istioctl 1.31 没有 x ca root 命令。不要仅因叶证书到期就删除或重新生成 CA：无计划替换信任根可破坏所有依赖工作负载。修复实际续订/连接/提供程序问题，并使用受支持 CA 轮换流程及所需信任重叠。仅恢复流程需要时重启明确受影响的工作负载。

## DNS 解析失败 {#dns-resolution-failure}

### 问题描述

对于 no-such-host 或查询超时，区分应用 DNS、CoreDNS/上游 DNS、Service 存在性/搜索后缀和 Istio DNS 捕获。

```bash
kubectl -n kube-system get svc kube-dns
kubectl -n kube-system get pods -l k8s-app=kube-dns
kubectl -n kube-system get endpointslices.discovery.k8s.io \
  -l kubernetes.io/service-name=kube-dns
# Run from the affected app container only if it includes these tools.
kubectl -n "$NS" exec "$POD" -c myapp -- cat /etc/resolv.conf
kubectl -n "$NS" exec "$POD" -c myapp -- nslookup myapp.app.svc.cluster.local
```

不要假定最小应用或代理镜像包含诊断工具。必要时使用获准诊断容器。检查 NetworkPolicy 对 UDP/TCP 53 的设置、节点/解析器可达性及受影响 Pod 的 dnsPolicy/搜索配置。

ServiceEntry 在 Istio 注册外部服务；不修复 CoreDNS、不创建公共 DNS 记录，也不使无法解析的上游主机名变为可解析：

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
  namespace: app
spec:
  hosts:
  - api.example.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

将 api.example.com 替换为实际外部主机名。DNS 解析决定上游端点。依据模式、版本和配置，Istio DNS 捕获/IP 分配可用合成地址回答服务名；这仍不证明真实上游端点可解析或可达。查看 [DNS 捕获指南](../advanced/04-dns-cache.md)。对于已经发送 HTTPS 的应用，此处声明 HTTPS 不要求添加第二层 TLS 发起。

## Envoy 初始化超时 {#envoy-initialization-timeout}

### 问题描述

“等待 Envoy 代理就绪”可由 xDS/CA 连接、配置被拒绝、资源、证书/令牌问题或引导设置引起。提高探针延迟前，检查 Pod/初始化容器状态、代理/Istiod 日志、事件和 proxy-status。

holdApplicationUntilProxyStarts 将应用启动延迟到代理就绪；不修复无法就绪的 Envoy。仅含 initialDelaySeconds 的 readinessProbe 无效，因为没有探针动作。

若应用实际在 8080 实现 /ready，此片段提供具体启动/就绪约定：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations:
        proxy.istio.io/config: |
          holdApplicationUntilProxyStarts: true
      labels: {}
    spec:
      containers:
      - name: myapp
        startupProbe:
          httpGet:
            path: /ready
            port: 8080
          periodSeconds: 2
          failureThreshold: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          periodSeconds: 5
          failureThreshold: 3
```

按应用调整动作和阈值。StartupProbe 控制启动容忍度；readiness 控制端点资格。两者都不修复 Istiod 不可达。将应用探针失败归因于 Envoy 初始化前，检查注入探针重写和生效代理就绪设置。

## 调试工具 {#debugging-tools}

### istioctl 命令

```bash
istioctl analyze -A
istioctl proxy-status
istioctl proxy-config all "$POD" -n "$NS"
istioctl proxy-config log "$POD" -n "$NS"
# Temporarily change levels only on the selected Envoy.
istioctl proxy-config log "$POD" -n "$NS" --level http:debug
# Restore the previously recorded levels afterwards; --reset restores defaults.
istioctl bug-report --include "$NS" --duration 10m

# Ambient has ztunnel diagnostics; Envoy commands apply to waypoints.
istioctl ztunnel-config workloads -n "$ISTIO_NS"
istioctl ztunnel-config certificates -n "$ISTIO_NS"
```

实验命令可能变化，不能替代流量验证。临时调试前记录日志级别，之后恢复；reset 表示默认值，可能不同于之前自定义设置。限制诊断时长，共享 bug-report 归档前审核收集的配置/日志数据。

### Envoy Admin API

仅转发到回环地址：

```bash
# Keep this command running; use a second terminal for the HTTP requests.
kubectl -n "$NS" port-forward --address 127.0.0.1 "$POD" 15000:15000

```

在另一终端：

```bash
curl --fail --silent --show-error http://127.0.0.1:15000/clusters
curl --fail --silent --show-error http://127.0.0.1:15000/stats/prometheus
curl --fail --silent --show-error http://127.0.0.1:15000/config_dump
```

这些命令适用于 Envoy，包括 Sidecar 和 waypoint，不适用于 ztunnel 不同的管理接口。完成后关闭端口转发。日志更改优先使用上方选定代理的 istioctl 命令，并在之后恢复记录级别。

### 常见日志检查

```bash
kubectl -n "$NS" logs "$POD" -c myapp
kubectl -n "$NS" logs "$POD" -c istio-proxy
# Only when that container has a prior instance in this same Pod:
kubectl -n "$NS" logs "$POD" -c istio-proxy --previous
kubectl -n "$NS" logs -f "$POD" -c istio-proxy
```

从运行中/当前 Pod 采集日志不是已删除 Pod 的日志保留。将请求时间、trace/request ID、响应标志及相关端点/配置更改与事件证据一并保留。

## 参考资料

- [注入故障排除](https://istio.io/latest/docs/ops/common-problems/injection/)和[注入配置](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)
- [网络问题](https://istio.io/latest/docs/ops/common-problems/network-issues/)和 [TLS 方向/自动 mTLS](https://istio.io/latest/docs/ops/configuration/traffic-management/tls-configuration/)
- [Istio 注解](https://istio.io/latest/docs/reference/config/annotations/)和[发布的 1.31 代理关闭代码](https://github.com/istio/istio/blob/1.31.0/pkg/envoy/agent.go)
- [Kubernetes Pod 终止](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)和[原生 Sidecar](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/)
- [代理诊断](https://istio.io/latest/docs/ops/diagnostic-tools/proxy-cmd/)、[CA 集成](https://istio.io/latest/docs/tasks/security/cert-management/plugin-ca-cert/)和[安全入口](https://istio.io/latest/docs/tasks/traffic-management/ingress/secure-ingress/)
- [Kubernetes DNS 诊断](https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/)和 [Istio DNS 代理](https://istio.io/latest/docs/ops/configuration/traffic-management/dns-proxy/)
- [可观测性](../observability/README.md)、[安全](../security/README.md)、[流量管理](../traffic-management/README.md)

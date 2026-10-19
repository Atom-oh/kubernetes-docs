# Service 与网络

> **支持的版本**：Kubernetes 1.35、1.36、1.37
> **最后更新**：2026年10月16日

在 Kubernetes 中，Service 是一种抽象层，为一组 Pod 提供单一访问点。在本章中，我们将详细探索 Kubernetes 网络概念，包括各种 Service 类型、Ingress、网络策略等。

## 实验环境设置

要学习本文档中的示例，你需要以下工具和环境：

### 所需工具
- 与 API Server 相差不超过一个次要版本的 kubectl
- 可正常运行的 Kubernetes 集群（EKS、minikube、kind 等）

### 部署示例应用

```bash
# Create namespace
kubectl create namespace networking-demo

# Deploy a simple application
kubectl -n networking-demo apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  labels:
    app: web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: nginx
        image: nginx:1.30.6
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: web-service
spec:
  selector:
    app: web
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
EOF

# Verify services
kubectl -n networking-demo get svc,pods
```

## 目录

1. [Service 类型](#service-types)
2. [Ingress](#ingress)
3. [Endpoints](#endpoints)
4. [Service 发现](#service-discovery)
5. [CoreDNS](#coredns)
6. [网络策略](#network-policies)
7. [Service Mesh](#service-mesh)
8. [CNI（容器网络接口）](#cnicontainer-network-interface)
9. [Cilium](#cilium)
   - [Cilium 简介](#introduction-to-cilium)
   - [eBPF 技术](#ebpf-technology)
   - [Cilium 网络模型](#cilium-networking-model)
   - [Cilium 网络策略](#cilium-network-policies)
   - [使用 Hubble 实现网络可视化](#network-visibility-with-hubble)
   - [在 Amazon EKS 上配置 Cilium](#configuring-cilium-on-amazon-eks)

## Service 类型 {#service-types}

> **核心概念**：Kubernetes Service 为一组 Pod 提供稳定的网络端点，并通过多种类型控制内部和外部访问。

Kubernetes 提供多种类型的 Service，以支持以不同方式公开应用。

### Service 架构

![Service 网络：代理/负载均衡器使用 EndpointSlice 信息将流量路由到后端 Pod；CoreDNS 解析 Service 名称，ExternalName 则提供 DNS CNAME 别名。](../.gitbook/assets/en-core-03-services-networking-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-03-services-networking-0.html)

### Service 类型对比

| Service 类型 | 访问范围 | 外部 IP | 使用场景 | 特性 |
|-------------|-------------|-------------|----------|----------|
| **ClusterIP** | 集群内部 | 否 | 内部微服务通信 | 默认 Service 类型，仅能在集群内访问 |
| **NodePort** | 集群外部 | 否 | 开发和测试环境 | 通过所有节点上的指定端口（30000-32767）访问 |
| **LoadBalancer** | 集群外部 | 是 | 生产环境中的外部服务 | 创建云服务提供商的负载均衡器 |
| **ExternalName** | 集群内部 | 否 | 外部服务的内部别名 | 通过 DNS CNAME 记录重定向 |
| **Headless** | 集群内部 | 否 | 需要直接访问 Pod IP 时 | 不带 ClusterIP 的特殊 Service |

### ClusterIP

ClusterIP 是最基本的 Service 类型，提供仅能在集群内访问的固定 IP 地址。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  selector:
    app: MyApp
  ports:
  - protocol: TCP
    port: 80
    targetPort: 9376
  type: ClusterIP  # Default, can be omitted
```

### NodePort

NodePort Service 允许通过所有节点上的指定端口访问该 Service。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  selector:
    app: MyApp
  ports:
  - protocol: TCP
    port: 80        # Port used within cluster
    targetPort: 9376 # Pod's port
    nodePort: 30007  # Port exposed on nodes (30000-32767)
  type: NodePort
```

### LoadBalancer

LoadBalancer Service 会创建云服务提供商的负载均衡器，从而将 Service 暴露到外部。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: external
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    service.beta.kubernetes.io/aws-load-balancer-scheme: internet-facing
spec:
  selector:
    app: MyApp
  ports:
  - port: 80
    targetPort: 9376
  type: LoadBalancer
```

此示例需要 AWS Load Balancer Controller、相应的 IAM 权限、合适的子网和可路由的 Pod IP。它会创建一个面向互联网的 NLB。也可以使用内部负载均衡器；AWS 可能返回 DNS 主机名而不是 IP。EKS Auto Mode 使用单独的 Controller/Class 和配置。

### ExternalName

ExternalName Service 为外部服务提供别名。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  type: ExternalName
  externalName: my.database.example.com
```

此 Service 会将 DNS 名称 `my-service` 映射到 `my.database.example.com`。

### Headless Service

Headless Service 是一种没有集群 IP 的 Service，它会为每个 Pod 创建 DNS 记录。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  clusterIP: None  # Headless service
  selector:
    app: MyApp
  ports:
  - port: 80
    targetPort: 9376
```

此 Service 不会分配集群 IP，并会为每个 Pod 创建 DNS 记录。

### 外部 IP

`externalIPs` 会在已由管理员管理、且路由到节点的 IP 地址上公开此 Service；它不会分配地址，也不会选择外部后端。自 v1.36 起已弃用。对于新的配置，建议使用受支持的负载均衡器或 Gateway 实现。以下仅用于文档的地址必须替换为你控制的地址。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  selector:
    app: MyApp
  ports:
  - port: 80
    targetPort: 9376
  externalIPs:
  - 198.51.100.32
```

## Ingress

Ingress 是一种 API 对象，用于将集群外部的 HTTP 和 HTTPS 路由到集群内的 Service。Ingress 提供负载均衡、SSL 终止和基于名称的虚拟主机托管。

![Ingress 主机/路径规则会配置代理或负载均衡器，将请求路由到 Service A 或 Service B 的后端 Pod；Ingress API 对象本身是配置，不是流量经过的节点。](../.gitbook/assets/en-core-03-services-networking-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-03-services-networking-1.html)

### Ingress Controller

要使用 Ingress 资源，集群中必须运行 Ingress Controller。常见的 Ingress Controller 包括：

- AWS Load Balancer Controller
- GCE Ingress Controller
- Traefik
- HAProxy
- Istio Ingress

社区版 ingress-nginx 已于 2026 年 3 月退役（[通知](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/)）。以下通用示例假设已安装 Traefik Controller 和 `traefik` IngressClass。Ingress 是一种配置 API，而不是数据包处理节点；Controller 会配置实际的代理/负载均衡器。

### 基本 Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: minimal-ingress
spec:
  ingressClassName: traefik  # Ingress controller class to use
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example-service
            port:
              number: 80
```

此 Ingress 会将发往主机 `example.com` 的所有请求路由到 `example-service:80`。

### 基于路径的路由

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: path-based-ingress
spec:
  ingressClassName: traefik
  rules:
  - host: example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
      - path: /web
        pathType: Prefix
        backend:
          service:
            name: web-service
            port:
              number: 80
```

此 Ingress 会将以 `example.com/api` 开头的请求路由到 `api-service`，并将以 `example.com/web` 开头的请求路由到 `web-service`。

### 基于名称的虚拟主机托管

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: name-based-ingress
spec:
  ingressClassName: traefik
  rules:
  - host: foo.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: foo-service
            port:
              number: 80
  - host: bar.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: bar-service
            port:
              number: 80
```

此 Ingress 会将发往 `foo.example.com` 的请求路由到 `foo-service`，并将发往 `bar.example.com` 的请求路由到 `bar-service`。

### TLS 配置

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-ingress
spec:
  ingressClassName: traefik
  tls:
  - hosts:
    - example.com
    secretName: example-tls
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example-service
            port:
              number: 80
```

此 Ingress 使用存储在 `example-tls` Secret 中的 TLS 证书，终止与 `example.com` 的 HTTPS 连接。

创建 TLS Secret：

```bash
kubectl create secret tls example-tls --cert=path/to/cert.crt --key=path/to/key.key
```

### AWS Load Balancer Controller

在 AWS EKS 上，你可以使用 AWS Load Balancer Controller 创建 Application Load Balancer。

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: alb-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account-id:certificate/certificate-id
spec:
  ingressClassName: alb
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example-service
            port:
              number: 80
```

此 Ingress 使用 AWS ALB 处理发往 `example.com` 的请求。

## Endpoints

旧版 `v1/Endpoints` API 自 v1.33 起已弃用。对于新的集成，请使用 `discovery.k8s.io/v1` EndpointSlice。这些对象用于描述后端；流量不会经过 API 对象。

Endpoints 是用于存储 Service 所指向 Pod 的 IP 地址和端口的资源。当存在与 Service 选择器匹配的 Pod 时，Kubernetes 会自动创建并管理 Endpoints 对象。

```yaml
apiVersion: v1
kind: Endpoints
metadata:
  name: my-service
subsets:
- addresses:
  - ip: 192.168.1.1
  ports:
  - port: 9376
```

对于手动配置的后端，请创建一个**不带选择器**且端口匹配的、名为 `my-service` 的 Service；否则 Controller 可能会覆盖后端数据。建议使用如下的手动管理 EndpointSlice。

### EndpointSlice

EndpointSlice 是 Endpoints 的可扩展替代方案，在大型集群中性能更好。

```yaml
apiVersion: discovery.k8s.io/v1
kind: EndpointSlice
metadata:
  name: my-service-abc
  labels:
    kubernetes.io/service-name: my-service
    endpointslice.kubernetes.io/managed-by: docs.example.com
addressType: IPv4
ports:
- name: ""
  protocol: TCP
  port: 9376
endpoints:
- addresses:
  - "10.1.2.3"
  conditions:
    ready: true
  hostname: pod-1
  nodeName: node-1
  zone: us-west-2a
```

## Service 发现 {#service-discovery}

Kubernetes 提供两种主要的 Service 发现方式：

1. **环境变量**：创建 Pod 时，Kubernetes 会将活动 Service 的环境变量注入 Pod。
2. **DNS**：Kubernetes 通过集群 DNS 服务器为 Service 提供 DNS 记录。

### 环境变量

当 `enableServiceLinks: true` 时，kubelet 会在容器启动时，为 Pod 所在命名空间中已存在 ClusterIP 的 Service 添加变量。这些变量不会动态更新；对于之后创建的 Service，使用 DNS 更合适。例如，如果存在名为 `my-service` 的 Service，则会创建以下环境变量：

```
MY_SERVICE_SERVICE_HOST=10.0.0.11
MY_SERVICE_SERVICE_PORT=80
```

### DNS

Kubernetes DNS 会为 Service 创建 DNS 记录。Pod 可以使用 Service 名称访问 Service。

- 普通 Service：`my-service.my-namespace.svc.cluster.local`
- Headless Service 的 Pod：`pod-name.my-service.my-namespace.svc.cluster.local`

## CoreDNS

CoreDNS 是一种灵活且可扩展的 DNS 服务器，用作 Kubernetes 集群的 DNS 服务器。

### CoreDNS 配置

CoreDNS 通过 ConfigMap 配置：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health {
            lameduck 5s
        }
        ready
        kubernetes cluster.local in-addr.arpa ip6.arpa {
            pods insecure
            fallthrough in-addr.arpa ip6.arpa
            ttl 30
        }
        prometheus :9153
        forward . /etc/resolv.conf
        cache 30
        loop
        reload
        loadbalance
    }
```

此配置提供以下功能：

- `errors`：错误日志记录
- `health`：运行状况检查端点
- `ready`：就绪状态检查端点
- `kubernetes`：Kubernetes Service 和 Pod 的 DNS 记录
- `prometheus`：公开 Prometheus 指标
- `forward`：转发外部 DNS 查询
- `cache`：缓存 DNS 响应
- `loop`：循环检测
- `reload`：配置文件更改时自动重新加载
- `loadbalance`：负载均衡

### DNS 策略

可以通过 `dnsPolicy` 字段配置 Pod 的 DNS 策略：

- `ClusterFirst`：默认策略，优先使用 Kubernetes DNS 服务器；如果没有匹配项，则转发到上游名称服务器。
- `Default`：继承 Pod 所运行节点的 DNS 设置。
- `ClusterFirstWithHostNet`：对 `hostNetwork: true` 的 Pod，建议使用此策略。
- `None`：必须通过 `dnsConfig` 字段提供所有 DNS 设置。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: custom-dns
spec:
  containers:
  - name: nginx
    image: nginx
  dnsPolicy: "None"
  dnsConfig:
    nameservers:
    - 1.1.1.1
    - 8.8.8.8
    searches:
    - ns1.svc.cluster.local
    - my.dns.search.suffix
    options:
    - name: ndots
      value: "2"
    - name: edns0
```

## 网络策略 {#network-policies}

网络策略提供控制 Pod 之间通信的方式。要使用网络策略，网络插件必须支持该功能（例如 Calico、Cilium）。

![网络策略允许 Frontend Pod 访问 API Pod、API Pod 访问 Database Pod，也允许另一个命名空间中的 Monitoring Pod 访问 API Pod；同时直接阻止 Frontend Pod 和 Monitoring Pod 访问 Database Pod。](../.gitbook/assets/en-core-03-services-networking-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-03-services-networking-2.html)

### 基本网络策略

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
spec:
  podSelector: {}  # Applies to all Pods
  policyTypes:
  - Ingress
```

此策略会隔离其所在命名空间中 Pod 的入站流量。标准 NetworkPolicy 采用累加规则：其他策略允许的流量仍然会被允许。网络插件必须执行策略；一个连接必须同时获得源端出站策略和目标端入站策略的允许。节点流量存在文档中说明的例外情况。

### 允许流量进入指定 Pod

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-nginx-ingress
spec:
  podSelector:
    matchLabels:
      app: nginx
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          access: allowed
    ports:
    - protocol: TCP
      port: 80
```

此网络策略允许带有 `access: allowed` 标签的 Pod 通过 TCP 端口 80 向带有 `app: nginx` 标签的 Pod 发送入站流量。

### 基于命名空间的策略

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-prod-namespace
spec:
  podSelector:
    matchLabels:
      app: db
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          purpose: production
```

此网络策略允许带有 `purpose: production` 标签的命名空间中的所有 Pod 向带有 `app: db` 标签的 Pod 发送入站流量。

### 出站策略

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: limit-egress
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 8080
  - to:
    - namespaceSelector:
        matchLabels:
          purpose: monitoring
```

此网络策略允许带有 `app: frontend` 标签的 Pod 向带有 `app: api` 标签的 Pod 的 TCP 端口 8080 发送出站流量，并允许其向带有 `purpose: monitoring` 标签的命名空间中的所有 Pod 发送出站流量。

此出站示例还会阻止 DNS，除非另一个策略允许 DNS 流量。当应用使用 Service 名称时，请添加对集群 DNS 端点的 TCP/UDP 53 端口访问；如果已安装 NodeLocal DNS，也要将其纳入考虑。

### 基于 CIDR 的策略

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-external-traffic
spec:
  podSelector:
    matchLabels:
      app: web
  policyTypes:
  - Ingress
  ingress:
  - from:
    - ipBlock:
        cidr: 192.168.1.0/24
        except:
        - 192.168.1.1/32
```

此网络策略允许来自 `192.168.1.0/24` CIDR 网段（不包括 192.168.1.1）的入站流量访问带有 `app: web` 标签的 Pod。

## Service Mesh

Service Mesh 是用于管理微服务之间通信的基础设施层。Service Mesh 提供 Service 发现、负载均衡、加密、身份验证、授权和可观测性等功能。

![Istio 控制平面通过虚线控制通道向注入到三个 Pod 中的 sidecar 代理推送配置；每个 Service 只与自己的 sidecar 通信，sidecar 彼此交换 Service 到 Service 的流量，而不是让各 Service 直接连接。](../.gitbook/assets/en-core-03-services-networking-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-03-services-networking-3.html)

### Istio

Istio 是一种流行的 Service Mesh 实现。图中展示的是 Istio sidecar 模式，它会将 Envoy 注入已加入网格的 Pod。Istio 还提供采用不同数据平面的 ambient 模式。

#### Istio Virtual Service

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews
        subset: v2
  - route:
    - destination:
        host: reviews
        subset: v1
```

此 VirtualService 会将带有 `end-user: jason` 标头的请求路由到 `reviews` Service 的 `v2` 子集，并将所有其他请求路由到 `v1` 子集。

#### Istio Destination Rule

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      simple: RANDOM
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
    trafficPolicy:
      loadBalancer:
        simple: ROUND_ROBIN
```

此 DestinationRule 为 `reviews` Service 定义了两个子集（`v1` 和 `v2`），并为每个子集设置负载均衡策略。

### Linkerd

Linkerd 是一种轻量级 Service Mesh，以安装和使用简单为特点。

#### Linkerd Service Profile

这是一个旧版示例。自 Linkerd 2.16 起，Gateway API 类型已取代 ServiceProfiles；为保持兼容，ServiceProfiles 仍然可用。请参阅[当前参考文档](https://linkerd.io/2-edge/reference/service-profiles/)。

```yaml
apiVersion: linkerd.io/v1alpha2
kind: ServiceProfile
metadata:
  name: nginx.default.svc.cluster.local
  namespace: default
spec:
  routes:
  - name: GET /
    condition:
      method: GET
      pathRegex: /
    responseClasses:
    - condition:
        status:
          min: 500
          max: 599
      isFailure: true
  retryBudget:
    retryRatio: 0.2
    minRetriesPerSecond: 10
    ttl: 10s
```

此 ServiceProfile 为 `nginx` Service 定义了路由和重试策略。

<span id="cnicontainer-network-interface"></span>

## CNI（容器网络接口）

CNI 插件会配置 Pod 网络接口和 IP 地址分配。网络策略的执行是可选的，具体取决于插件。

## Cilium

![Kubernetes 通过容器网络接口将网络配置委托给 Cilium；Cilium 将 eBPF 程序加载到 Linux 内核中以实现数据路径，并向 Hubble 提供数据以实现网络流可观测性。](../.gitbook/assets/en-core-03-services-networking-4.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-03-services-networking-4.html)

[Cilium 详情](../networking/cilium/README.md)

### Cilium 简介 {#introduction-to-cilium}

Cilium 是一款开源软件，利用 Linux 内核中功能强大的 eBPF 技术，为容器化应用提供网络连接、安全性和可观测性。Cilium 当前与 Kubernetes 的集成通过 CNI 插件和 Controller 提供网络、安全和可观测性功能。

#### 主要特性

- **基于 eBPF**：通过内核中的可编程数据路径，提供高性能网络和安全功能
- **感知 API 的网络**：支持 L3-L7 层的感知 API 网络安全策略
- **Kubernetes 集成**：提供 Kubernetes CNI（容器网络接口）实现
- **分布式负载均衡**：通过分布式负载均衡实现高效的 Service 到 Service 通信
- **网络可视性**：通过 Hubble 监控和排查网络流问题
- **多集群支持**：支持跨集群网络和安全策略

#### Cilium 的差异化优势

与其他 CNI 解决方案相比，Cilium 具有一些独特优势。

**技术差异化**：
- **利用 eBPF**：通过内核中的可编程数据路径，实现高性能和灵活性
- **感知 API 的网络**：支持最高至 L7 层的网络策略
- **XDP（eXpress Data Path）**：优化数据包处理性能
- **替代 kube-proxy**：实现更高效的 Service 负载均衡
- **集成 Hubble**：强大的网络可观测性工具

**不同使用场景的优势**：
- **微服务架构**：细粒度网络策略和可观测性
- **多集群部署**：实现跨集群无缝网络连接
- **注重安全的环境**：强大的网络安全策略
- **高性能要求**：优化的数据路径
- **Service Mesh 集成**：与 Istio 等 Service Mesh 集成

### eBPF 技术 {#ebpf-technology}

eBPF（extended Berkeley Packet Filter）是一种允许程序在 Linux 内核中安全运行的技术。Cilium 使用 eBPF 实现网络、安全和可观测性功能。

#### eBPF 的主要特性

1. **内核内执行**：eBPF 程序直接在内核中执行，性能较高。
2. **安全性**：加载前，验证器会检查程序是否符合安全约束；但这并不能保证不存在内核缺陷或策略逻辑错误。
3. **动态加载**：无需重启内核即可加载和卸载 eBPF 程序。
4. **Map**：eBPF Map 用于存储数据并在用户空间与内核空间之间共享数据。

#### Cilium 中的 eBPF 用法

Cilium 通过以下方式使用 eBPF：

1. **网络数据路径**：eBPF 程序处理并路由网络数据包。
2. **策略执行**：eBPF 程序执行网络策略。
3. **负载均衡**：eBPF 程序为 Service 执行负载均衡。
4. **可观测性**：eBPF 程序收集网络流指标。

#### eBPF 与传统网络方案对比

| 特性 | eBPF | 传统方案（iptables） |
|---------|------|--------------------------------|
| 性能 | 非常高 | 中等 |
| 可扩展性 | 非常高 | 有限 |
| 可编程性 | 高 | 有限 |
| 可观测性 | 高 | 有限 |
| 实现复杂度 | 高 | 中等 |

### Cilium 网络模型 {#cilium-networking-model}

Cilium 支持多种网络模型，可以根据不同的环境和需求进行配置。

#### Overlay 网络

Cilium 默认使用 VXLAN 实现 Overlay 网络，同时也支持 Geneve 等其他封装协议。

**工作原理**：
1. 在源节点上生成数据包。
2. Cilium 通过在原始数据包外包裹封装标头来封装数据包。
3. 封装后的数据包通过物理网络传输到目标节点。
4. 在目标节点上，Cilium 解封装数据包以提取原始数据包。
5. 将提取的数据包传递到目标容器。

**优点**：
- 与现有网络基础设施兼容
- 不受网络拓扑限制
- Pod 地址与底层网络无关；但互联集群仍需要兼容且不重叠的地址规划

**缺点**：
- 封装开销会影响性能
- MTU 大小减少
- 增加 CPU 使用量

#### 原生路由

原生路由不使用封装，而是直接路由。在此模式下，底层网络基础设施必须能够路由 Pod IP 地址。

**工作原理**：
1. 每个节点公布在该节点上运行的 Pod 的 CIDR 网段。
2. 配置路由表，将每个 Pod CIDR 网段路由到相应节点。
3. 数据包无需封装即可直接路由到目标节点。

**优点**：
- 没有封装开销
- 提升网络性能
- 降低 CPU 使用量

**缺点**：
- 依赖底层网络基础设施
- 受网络拓扑限制
- IP 地址管理复杂

#### 路由模式选择

请为部署明确选择封装或原生路由。不要假设原生路由失败时会自动回退到隧道；请根据所选 Cilium 版本配置路由和任何迁移操作。

#### AWS ENI 模式

在 AWS EKS 上，Cilium 可以利用 AWS Elastic Network Interface（ENI）为 Pod 分配 VPC 原生 IP 地址。

**主要特性**：
- 为 Pod 分配 VPC 原生 IP 地址
- 无需 Overlay 网络即可实现 VPC 原生网络
- 集成 AWS 安全组和网络策略
- 提升网络性能

### Cilium 网络策略 {#cilium-network-policies}

Cilium 扩展了 Kubernetes 网络策略，支持在 L3-L7 层实施细粒度网络安全策略。

#### L3/L4 策略

Cilium 支持标准 Kubernetes 网络策略，可根据 IP 地址、端口和协议定义策略。

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "l3-l4-policy"
spec:
  endpointSelector:
    matchLabels:
      app: myapp
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "80"
        protocol: TCP
```

此策略允许带有 `app: frontend` 标签的 Pod 通过 TCP 端口 80 向带有 `app: myapp` 标签的 Pod 发送入站流量。

#### L7 策略

Cilium 通过结合使用用户空间 Envoy 代理和 eBPF 来支持 HTTP 规则等 L7 策略。L7 检查并非完全在内核中执行；请确认已安装版本的协议和加密限制。

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "l7-policy"
spec:
  endpointSelector:
    matchLabels:
      app: myapp
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "80"
        protocol: TCP
      rules:
        http:
        - method: "GET"
          path: "/api/v1/products"
```

此策略仅允许带有 `app: frontend` 标签的 Pod 向带有 `app: myapp` 标签的 Pod 发送针对 `/api/v1/products` 路径的 HTTP GET 请求。

#### 集群范围策略

Cilium 支持集群范围的网络策略，可用于定义适用于所有 Pod 的策略。

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: "cluster-wide-policy"
spec:
  endpointSelector:
    matchLabels: {}  # Applies to all Pods
  ingress:
  - fromEndpoints:
    - matchLabels:
        io.kubernetes.pod.namespace: kube-system
```

此策略允许来自 `kube-system` 命名空间中 Pod 的入站流量访问所有 Pod。

### 使用 Hubble 实现网络可视化 {#network-visibility-with-hubble}

Hubble 是 Cilium 的可观测性层，它使用 eBPF 监控网络流并排查问题。

#### Hubble 的主要特性

1. **网络流监控**：实时监控 Pod 到 Pod 的通信。
2. **Service 依赖关系映射**：可视化 Service 之间的依赖关系。
3. **安全性观察**：检测网络策略违规情况。
4. **性能分析**：分析网络延迟和吞吐量。
5. **故障排查**：诊断网络连接问题。

#### Hubble 架构

Hubble 由以下组件组成：

1. **Hubble Server**：嵌入 Cilium Agent 中的服务器，用于收集网络流数据。
2. **Hubble Relay**：聚合多个 Hubble Server 的数据。
3. **Hubble UI**：用于可视化网络流的 Web 界面。
4. **Hubble CLI**：用于查询网络流的命令行工具。

#### Hubble 用法示例

```bash
# Install Hubble CLI
curl -L --remote-name-all https://github.com/cilium/hubble/releases/latest/download/hubble-linux-amd64.tar.gz
sudo tar xzvfC hubble-linux-amd64.tar.gz /usr/local/bin
rm hubble-linux-amd64.tar.gz

# Enable Hubble
cilium hubble enable

# Run in a separate terminal and keep it open
cilium hubble port-forward

# Observe network flows
hubble observe

# Observe HTTP requests
hubble observe --protocol http

# Observe network flows for specific Pod
hubble observe --pod default/myapp-pod

# Observe network policy violations
hubble observe --verdict DROPPED
```

### 在 Amazon EKS 上配置 Cilium {#configuring-cilium-on-amazon-eks}

在 Amazon EKS 上配置 Cilium 有多种方式。下面介绍一些常见的配置方法。

#### 安装前选择 CNI 模式

请使用可随时销毁的 EKS 测试集群，并选择与其 Kubernetes 版本兼容的 Cilium 版本。请遵循[官方 EKS 安装指南](https://docs.cilium.io/en/stable/installation/k8s-install-helm/)；以下内容是 Helm **values 片段**，不是完整的安装或迁移命令。

对于 **AWS VPC CNI chaining**，保留 `aws-node` 作为 IPAM，并使用：

```yaml
cni:
  chainingMode: aws-cni
  exclusive: false
enableIPv4Masquerade: false
routingMode: native
```

必须通过受控的滚动更新重新创建现有 Pod，新的 CNI 链才能生效。启用 L7 策略或替换 kube-proxy 前，请检查 chaining 功能的限制。

对于 **Cilium ENI IPAM**，由 Cilium 而非 VPC CNI 管理 ENI：

```yaml
eni:
  enabled: true
ipam:
  mode: eni
routingMode: native
```

此模式需要 EC2 API 权限，并且必须按照官方迁移/安装流程阻止 `aws-node` 管理相同节点。未完成这些步骤前，不要在运行中的 VPC CNI 安装上应用此配置。EKS Auto Mode 和 Fargate 会单独管理其网络。

安装后，在隔离的测试集群中使用 `cilium status --wait` 和连通性测试进行验证。固定 Chart 版本，并在升级时保留经过审查的 values。

#### 启用 Hubble

```bash
# Enable Hubble
cilium hubble enable --ui

# Access Hubble UI
kubectl port-forward -n kube-system svc/hubble-ui 12000:80
```

#### Cilium 网络策略示例

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "eks-app-policy"
spec:
  endpointSelector:
    matchLabels:
      app: api
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
      rules:
        http:
        - method: "GET"
          path: "/api/v1/.*"
  egress:
  - toEndpoints:
    - matchLabels:
        app: database
    toPorts:
    - ports:
      - port: "3306"
        protocol: TCP
```

此策略仅允许带有 `app: frontend` 标签的 Pod 向带有 `app: api` 标签的 Pod 发送针对 `/api/v1/` 路径的 HTTP GET 请求；此外，还允许带有 `app: api` 标签的 Pod 向带有 `app: database` 标签的 Pod 通过 TCP 端口 3306 发送出站流量。

#### 在 EKS 上优化 Cilium

1. **节点组配置**：
   - 选择能提供足够 ENI 和 IP 地址的实例类型
   - 配置合适的 Pod 数量上限

2. **性能优化**：
   - 使用直接路由模式
   - 启用 XDP 加速
   - 启用 BBR 拥塞控制算法

3. **监控和日志记录**：
   - 启用 Hubble
   - 使用 Prometheus 收集指标
   - 与 CloudWatch 集成

## 总结

本章介绍了 Kubernetes Service 和网络。Service 为一组 Pod 提供稳定的端点，Ingress 则将外部流量路由到集群内的 Service。网络策略控制 Pod 之间的通信，Service Mesh 管理微服务架构中的 Service 间通信。我们还探讨了如何通过 CNI 和 Cilium 实现高级网络功能。

了解并利用 Kubernetes 网络功能，可以帮助你构建安全且可扩展的应用。

下一章将介绍 Kubernetes 存储选项。

## 参考资料

- [Kubernetes 官方文档 - Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Kubernetes 官方文档 - Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [Kubernetes 官方文档 - Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Kubernetes 官方文档 - DNS for Services and Pods](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)
- [Istio 官方文档](https://istio.io/latest/docs/)
- [Linkerd 官方文档](https://linkerd.io/2-edge/overview/)
- [Cilium 官方文档](https://docs.cilium.io/)
- [CNI 官方文档](https://github.com/containernetworking/cni)

## 测验

要检验你对本章内容的掌握情况，请尝试 [Service 与网络测验](../quizzes/core/03-services-networking-quiz.md)。

# 服务与网络

> **支持的版本**: Kubernetes 1.32, 1.33, 1.34
> **最后更新**: February 23, 2026

在 Kubernetes 中，Service 是一个抽象层，为一组 Pod 提供单一访问点。本章将详细探讨 Kubernetes 网络概念，包括各种 Service 类型、Ingress、网络策略等。

## 实验环境设置

要跟随本文档中的示例，您需要以下工具和环境：

### 所需工具
- kubectl v1.34 或更高版本
- 一个可用的 Kubernetes 集群（EKS、minikube、kind 等）

### 部署示例应用程序

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
        image: nginx:1.21
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
8. [CNI（Container Network Interface）](#cnicontainer-network-interface)
9. [Cilium](#cilium)
   - [Cilium 简介](#introduction-to-cilium)
   - [eBPF 技术](#ebpf-technology)
   - [Cilium 网络模型](#cilium-networking-model)
   - [Cilium 网络策略](#cilium-network-policies)
   - [使用 Hubble 实现网络可观测性](#network-visibility-with-hubble)
   - [在 Amazon EKS 上配置 Cilium](#configuring-cilium-on-amazon-eks)

## Service 类型

> **核心概念**：Kubernetes Service 为一组 Pod 提供稳定的网络端点，并通过各种类型控制内部和外部访问。

Kubernetes 提供多种 Service 类型，以支持以多种方式暴露应用程序。

### Service 架构

![外部客户端通过 LoadBalancer 或 NodePort 访问 ClusterIP，集群内部客户端通过 CoreDNS 解析名称并访问 ClusterIP，随后经由 Endpoints 路由到后端 Pod；而 ExternalName 则通过 DNS CNAME 为外部服务创建别名。](../.gitbook/assets/en-core-03-services-networking-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-03-services-networking-0.html)

### Service 类型比较

| Service 类型 | 访问范围 | 外部 IP | 使用场景 | 特性 |
|-------------|-------------|-------------|----------|----------|
| **ClusterIP** | 集群内部 | 否 | 内部微服务通信 | 默认 Service 类型，仅可在集群内访问 |
| **NodePort** | 集群外部 | 否 | 开发和测试环境 | 通过所有节点上的特定端口（30000-32767）访问 |
| **LoadBalancer** | 集群外部 | 是 | 生产环境外部服务 | 创建云提供商负载均衡器 |
| **ExternalName** | 集群内部 | 否 | 外部服务的内部别名 | 通过 DNS CNAME 记录重定向 |
| **Headless** | 集群内部 | 否 | 需要直接访问 Pod IP 时 | 没有 ClusterIP 的特殊 Service |

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

NodePort Service 允许通过所有节点上的特定端口访问该 Service。

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

ClusterIP 是默认的 Service 类型，提供仅能在集群内访问的 IP 地址。

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
  type: ClusterIP
```

可在集群内通过 `my-service:80` 访问此 Service。

### NodePort

NodePort Service 允许通过所有节点上的特定端口访问该 Service。

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
    nodePort: 30007  # Optional, auto-assigned from 30000-32767 if not specified
  type: NodePort
```

可在集群中的所有节点上通过 `<Node IP>:30007` 访问此 Service。

### LoadBalancer

LoadBalancer Service 会从云提供商创建一个负载均衡器，以将 Service 暴露到集群外部。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: nlb  # Use NLB on AWS
spec:
  selector:
    app: MyApp
  ports:
  - port: 80
    targetPort: 9376
  type: LoadBalancer
```

可通过云提供商的负载均衡器从外部访问此 Service。

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

此 Service 将 DNS 名称 `my-service` 映射到 `my.database.example.com`。

### Headless Service

Headless Service 是没有集群 IP 的 Service，它会为每个 Pod 创建 DNS 记录。

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

此 Service 不分配集群 IP，并会为每个 Pod 创建 DNS 记录。

### 外部 IP

Service 可以指定外部 IP，将外部资源作为 Kubernetes Service 暴露。

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
  - 80.11.12.10
```

## Ingress

Ingress 是一个 API 对象，它将集群外部的 HTTP 和 HTTPS 路由暴露给集群内的 Service。Ingress 提供负载均衡、SSL 终止和基于名称的虚拟主机功能。

![外部客户端的请求经过负载均衡器和 Ingress Controller，到达单个 Ingress 资源；其主机/路径规则分发到 Service A 和 Service B，而每个 Service 分别在其后端 Pod（A-1、A-2 / B-1、B-2）之间进行负载均衡。](../.gitbook/assets/en-core-03-services-networking-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-03-services-networking-1.html)

### Ingress Controller

要使用 Ingress 资源，集群中必须运行 Ingress Controller。常见的 Ingress Controller 包括：

- NGINX Ingress Controller
- AWS ALB Ingress Controller
- GCE Ingress Controller
- Traefik
- HAProxy
- Istio Ingress

### 基本 Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: minimal-ingress
spec:
  ingressClassName: nginx  # Ingress controller class to use
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

此 Ingress 会将发往 `example.com` 主机的所有请求路由到 `example-service:80`。

### 基于路径的路由

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: path-based-ingress
spec:
  ingressClassName: nginx
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

此 Ingress 将以 `example.com/api` 开头的请求路由到 `api-service`，并将以 `example.com/web` 开头的请求路由到 `web-service`。

### 基于名称的虚拟主机

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: name-based-ingress
spec:
  ingressClassName: nginx
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

此 Ingress 将发往 `foo.example.com` 的请求路由到 `foo-service`，并将发往 `bar.example.com` 的请求路由到 `bar-service`。

### TLS 配置

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-ingress
spec:
  ingressClassName: nginx
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

此 Ingress 使用存储在 `example-tls` Secret 中的 TLS 证书来终止与 `example.com` 的 HTTPS 连接。

创建 TLS Secret：

```bash
kubectl create secret tls example-tls --cert=path/to/cert.crt --key=path/to/key.key
```

### AWS ALB Ingress Controller

在 AWS EKS 上，您可以使用 AWS ALB Ingress Controller 创建 Application Load Balancer。

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: alb-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account-id:certificate/certificate-id
spec:
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

Endpoints 是存储 Service 指向的 Pod 的 IP 地址和端口的资源。当存在与 Service 的 selector 匹配的 Pod 时，Kubernetes 会自动创建和管理 Endpoints 对象。

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

此 Endpoints 使 `my-service` 指向 `192.168.1.1:9376`。

### EndpointSlice

EndpointSlice 是 Endpoints 的可扩展替代方案，在大型集群中提供更好的性能。

```yaml
apiVersion: discovery.k8s.io/v1
kind: EndpointSlice
metadata:
  name: my-service-abc
  labels:
    kubernetes.io/service-name: my-service
addressType: IPv4
ports:
- name: http
  protocol: TCP
  port: 80
endpoints:
- addresses:
  - "10.1.2.3"
  conditions:
    ready: true
  hostname: pod-1
  topology:
    kubernetes.io/hostname: node-1
    topology.kubernetes.io/zone: us-west-2a
```

## Service 发现

Kubernetes 提供两种主要的 Service 发现方法：

1. **环境变量**：Kubernetes 会在创建 Pod 时将活跃 Service 的环境变量注入其中。
2. **DNS**：Kubernetes 通过集群 DNS 服务器为 Service 提供 DNS 记录。

### 环境变量

创建 Pod 时，Kubernetes 会将当时已存在的所有 Service 的环境变量注入到 Pod 中。例如，如果存在名为 `my-service` 的 Service，则会创建以下环境变量：

```
MY_SERVICE_SERVICE_HOST=10.0.0.11
MY_SERVICE_SERVICE_PORT=80
```

### DNS

Kubernetes DNS 会为 Service 创建 DNS 记录。Pod 可以使用 Service 名称访问 Service。

- 常规 Service：`my-service.my-namespace.svc.cluster.local`
- Headless Service 的 Pod：`pod-name.my-service.my-namespace.svc.cluster.local`

## CoreDNS

CoreDNS 是一个灵活且可扩展的 DNS 服务器，用作 Kubernetes 集群的 DNS 服务器。

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

- `errors`：错误日志
- `health`：健康检查端点
- `ready`：就绪检查端点
- `kubernetes`：Kubernetes Service 和 Pod 的 DNS 记录
- `prometheus`：Prometheus 指标暴露
- `forward`：转发外部 DNS 查询
- `cache`：DNS 响应缓存
- `loop`：循环检测
- `reload`：配置文件变更时自动重新加载
- `loadbalance`：负载均衡

### DNS 策略

可通过 `dnsPolicy` 字段配置 Pod 的 DNS 策略：

- `ClusterFirst`：默认策略，优先使用 Kubernetes DNS 服务器；若未找到匹配项，则转发到上游名称服务器。
- `Default`：继承 Pod 所在节点的 DNS 设置。
- `ClusterFirstWithHostNet`：推荐用于具有 `hostNetwork: true` 的 Pod。
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

## 网络策略

网络策略提供了一种控制 Pod 之间通信的方式。要使用网络策略，网络插件必须支持它们（例如 Calico、Cilium、Weave Net）。

![网络策略允许 Frontend Pod 访问 API Pod，允许 API Pod 访问 Database Pod，也允许另一个 namespace 中的 Monitoring Pod 访问 API Pod；同时直接阻止 Frontend Pod 和 Monitoring Pod 访问 Database Pod。](../.gitbook/assets/en-core-03-services-networking-2.png)

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

此网络策略会阻止所有 Pod 的入站流量。

### 允许特定 Pod 的入站流量

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

此网络策略允许带有 `access: allowed` 标签的 Pod 向带有 `app: nginx` 标签的 Pod 发送 TCP 端口 80 的入站流量。

### 基于 Namespace 的策略

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

此网络策略允许带有 `purpose: production` 标签的 namespace 中的所有 Pod，向带有 `app: db` 标签的 Pod 发送入站流量。

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

此网络策略允许带有 `app: frontend` 标签的 Pod 向带有 `app: api` 标签的 Pod 的 TCP 端口 8080 发送出站流量，也允许向带有 `purpose: monitoring` 标签的 namespace 中的所有 Pod 发送出站流量。

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

此网络策略允许来自 `192.168.1.0/24` CIDR 块（不包括 192.168.1.1）的入站流量访问带有 `app: web` 标签的 Pod。

## Service Mesh

Service Mesh 是管理微服务之间通信的基础设施层。Service Mesh 提供 Service 发现、负载均衡、加密、身份验证、授权和可观测性等功能。

![Istio 控制平面通过虚线控制通道向注入三个 Pod 的 sidecar proxy 推送配置；每个 Service 仅与自身的 sidecar 通信，sidecar 之间交换服务到服务的流量，而非 Service 直接连接。](../.gitbook/assets/en-core-03-services-networking-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-03-services-networking-3.html)

### Istio

Istio 是一种流行的 Service Mesh 实现。Istio 使用 sidecar 模式将 Envoy proxy 注入到每个 Pod 中。

#### Istio Virtual Service

```yaml
apiVersion: networking.istio.io/v1alpha3
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

此 VirtualService 将带有 `end-user: jason` header 的请求路由到 `reviews` Service 的 `v2` subset，其他所有请求则路由到 `v1` subset。

#### Istio Destination Rule

```yaml
apiVersion: networking.istio.io/v1alpha3
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

此 DestinationRule 为 `reviews` Service 定义了两个 subset（`v1` 和 `v2`），并为每个 subset 设置负载均衡策略。

### Linkerd

Linkerd 是一种以安装和使用简单为特点的轻量级 Service Mesh。

#### Linkerd Service Profile

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

此 ServiceProfile 为 `nginx` Service 定义路由和重试策略。

## Cilium

![Kubernetes 通过 Container Network Interface 将网络功能委托给 Cilium，Cilium 将 eBPF 程序加载到 Linux kernel 中以实现数据路径，同时还将数据提供给 Hubble 用于网络流量可观测性。](../.gitbook/assets/en-core-03-services-networking-4.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-03-services-networking-4.html)

[Cilium 详情](../networking/cilium/README.md)

### Cilium 简介

Cilium 是开源软件，它利用 Linux kernel 中强大的 eBPF 技术，为容器化应用程序提供网络连接、安全性和可观测性。它旨在为 Kubernetes、Docker 和 Mesos 等容器编排平台提供网络、安全性和可观测性。

#### 主要特性

- **基于 eBPF**：通过 kernel 内的可编程数据路径提供高性能网络和安全功能
- **API 感知网络**：支持 L3-L7 层的 API 感知网络安全策略
- **Kubernetes 集成**：提供 Kubernetes CNI（Container Network Interface）实现
- **分布式负载均衡**：为高效的服务间通信提供分布式负载均衡
- **网络可观测性**：通过 Hubble 进行网络流量监控和故障排查
- **多集群支持**：支持跨集群网络和安全策略

#### Cilium 的差异化优势

与其他 CNI 解决方案相比，Cilium 提供了多项独特优势。

**技术差异化**：
- **eBPF 利用**：通过 kernel 内的可编程数据路径实现高性能和灵活性
- **API 感知网络**：支持最高到 L7 层的网络策略
- **XDP（eXpress Data Path）**：优化数据包处理性能
- **Kube-proxy 替代**：更高效的 Service 负载均衡
- **Hubble 集成**：强大的网络可观测性工具

**按使用场景划分的优势**：
- **微服务架构**：细粒度网络策略和可观测性
- **多集群部署**：跨集群无缝网络连接
- **安全重点环境**：强大的网络安全策略
- **高性能需求**：优化的数据路径
- **Service Mesh 集成**：与 Istio 等 Service Mesh 集成

### eBPF 技术

eBPF（extended Berkeley Packet Filter）是一种允许程序在 Linux kernel 内安全运行的技术。Cilium 使用 eBPF 实现网络、安全性和可观测性功能。

#### eBPF 的主要特性

1. **在 kernel 内执行**：eBPF 程序直接在 kernel 内执行，可提供高性能。
2. **安全性**：eBPF verifier 可确保程序不会损害 kernel。
3. **动态加载**：无需重启 kernel，即可加载和卸载 eBPF 程序。
4. **Maps**：eBPF map 用于存储数据，并在用户空间和 kernel 空间之间共享数据。

#### Cilium 中 eBPF 的使用方式

Cilium 以以下方式使用 eBPF：

1. **网络数据路径**：eBPF 程序处理和路由网络数据包。
2. **策略执行**：eBPF 程序执行网络策略。
3. **负载均衡**：eBPF 程序为 Service 执行负载均衡。
4. **可观测性**：eBPF 程序收集网络流量指标。

#### eBPF 与传统网络方法的对比

| 特性 | eBPF | 传统方法（iptables） |
|---------|------|--------------------------------|
| 性能 | 极高 | 中等 |
| 可扩展性 | 极高 | 有限 |
| 可编程性 | 高 | 有限 |
| 可观测性 | 高 | 有限 |
| 实现复杂度 | 高 | 中等 |

### Cilium 网络模型

Cilium 支持多种网络模型，可根据不同的环境和要求进行配置。

#### Overlay 网络

Cilium 默认使用 VXLAN 实现 Overlay 网络，但也支持 Geneve 等其他封装协议。

**工作原理**：
1. 数据包在源节点创建。
2. Cilium 通过使用封装 header 包装原始数据包来封装数据包。
3. 封装后的数据包通过物理网络传输到目标节点。
4. 在目标节点，Cilium 对数据包解封装以提取原始数据包。
5. 提取的数据包被交付给目标容器。

**优点**：
- 与现有网络基础设施兼容
- 独立于网络拓扑
- 防止多集群环境中的 IP 冲突

**缺点**：
- 封装开销导致性能受影响
- MTU 大小降低
- 额外的 CPU 使用量

#### 原生路由

原生路由使用不封装的直接路由。在此模式下，底层网络基础设施必须能够路由 Pod IP 地址。

**工作原理**：
1. 每个节点通告在该节点上运行的 Pod 的 CIDR 块。
2. 配置路由表，以将每个 Pod CIDR 块路由到相应节点。
3. 数据包无需封装，直接路由到目标节点。

**优点**：
- 没有封装开销
- 网络性能提升
- CPU 使用量更低

**缺点**：
- 依赖底层网络基础设施
- 网络拓扑限制
- IP 地址管理复杂性

#### 混合模式

Cilium 还支持结合 Overlay 网络和原生路由的混合模式。

**工作原理**：
1. 尽可能使用原生路由。
2. 当无法使用原生路由时，回退到 Overlay 网络。

**优点**：
- 灵活性和性能的平衡
- 支持各种网络拓扑
- 可逐步迁移

#### AWS ENI 模式

在 AWS EKS 上，Cilium 可以利用 AWS Elastic Network Interface（ENI）向 Pod 分配原生 VPC IP 地址。

**主要特性**：
- 向 Pod 分配 VPC 原生 IP 地址
- 无 Overlay 网络的 VPC 原生网络
- AWS security group 和网络策略集成
- 网络性能提升

### Cilium 网络策略

Cilium 扩展 Kubernetes 网络策略，以在 L3-L7 层提供细粒度网络安全策略。

#### L3/L4 策略

Cilium 支持标准 Kubernetes 网络策略，可基于 IP 地址、端口和协议定义策略。

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

此策略允许带有 `app: frontend` 标签的 Pod 向带有 `app: myapp` 标签的 Pod 发送 TCP 端口 80 的入站流量。

#### L7 策略

Cilium 支持 L7（应用层）策略，可为 HTTP、gRPC 和 Kafka 等协议定义细粒度策略。

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

此策略仅允许带有 `app: frontend` 标签的 Pod 向带有 `app: myapp` 标签的 Pod 发出访问 `/api/v1/products` 路径的 HTTP GET 请求。

#### 集群范围策略

Cilium 支持集群范围的网络策略，可定义适用于所有 Pod 的策略。

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

此策略允许来自 `kube-system` namespace 中 Pod 的入站流量访问所有 Pod。

### 使用 Hubble 实现网络可观测性

Hubble 是 Cilium 的可观测性层，它使用 eBPF 监控网络流量并排查问题。

#### Hubble 的主要特性

1. **网络流量监控**：实时监控 Pod 到 Pod 的通信。
2. **Service 依赖关系映射**：可视化服务间依赖关系。
3. **安全观测**：检测网络策略违规。
4. **性能分析**：分析网络延迟和吞吐量。
5. **故障排查**：诊断网络连接问题。

#### Hubble 架构

Hubble 由以下组件组成：

1. **Hubble Server**：嵌入在 Cilium agent 中、用于收集网络流量数据的服务器。
2. **Hubble Relay**：聚合来自多个 Hubble Server 的数据。
3. **Hubble UI**：用于可视化网络流量的 Web 界面。
4. **Hubble CLI**：用于查询网络流量的命令行工具。

#### Hubble 使用示例

```bash
# Install Hubble CLI
curl -L --remote-name-all https://github.com/cilium/hubble/releases/latest/download/hubble-linux-amd64.tar.gz
sudo tar xzvfC hubble-linux-amd64.tar.gz /usr/local/bin
rm hubble-linux-amd64.tar.gz

# Enable Hubble
cilium hubble enable

# Observe network flows
hubble observe

# Observe HTTP requests
hubble observe --protocol http

# Observe network flows for specific Pod
hubble observe --pod app=myapp

# Observe network policy violations
hubble observe --verdict DROPPED
```

### 在 Amazon EKS 上配置 Cilium

在 Amazon EKS 上配置 Cilium 有多种方式。下面将介绍一些常见的配置方法。

#### 基本安装

```bash
# Install Cilium CLI
curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz

# Install Cilium
cilium install

# Check installation status
cilium status

# Test connectivity
cilium connectivity test
```

#### AWS ENI 模式配置

```bash
# Install Cilium with AWS ENI mode
cilium install --config aws-eni-mode=true

# Or install using Helm
helm install cilium cilium/cilium \
  --namespace kube-system \
  --set eni.enabled=true \
  --set ipam.mode=eni \
  --set egressMasqueradeInterfaces=eth0 \
  --set tunnel=disabled
```

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

此策略仅允许带有 `app: frontend` 标签的 Pod 向带有 `app: api` 标签的 Pod 发出访问 `/api/v1/` 路径的 HTTP GET 请求，并允许带有 `app: api` 标签的 Pod 向带有 `app: database` 标签的 Pod 的 TCP 端口 3306 发送出站流量。

#### EKS 上的 Cilium 优化

1. **节点组配置**：
   - 选择提供足够 ENI 和 IP 地址的实例类型
   - 配置适当的最大 Pod 数量

2. **性能优化**：
   - 使用直接路由模式
   - 启用 XDP 加速
   - 启用 BBR 拥塞控制算法

3. **监控和日志**：
   - 启用 Hubble
   - 收集 Prometheus 指标
   - 与 CloudWatch 集成

## 总结

本章介绍了 Kubernetes Service 和网络。Service 为一组 Pod 提供稳定的端点，Ingress 将外部流量路由到集群内的 Service。网络策略控制 Pod 之间的通信，而 Service Mesh 管理微服务架构中的服务间通信。我们还探讨了如何通过 CNI 和 Cilium 实现高级网络功能。

理解并利用 Kubernetes 网络功能，能够帮助您构建安全且可扩展的应用程序。

下一章将学习 Kubernetes 存储选项。

## 参考资料

- [Kubernetes 官方文档 - Service](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Kubernetes 官方文档 - Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [Kubernetes 官方文档 - 网络策略](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Kubernetes 官方文档 - Service 和 Pod 的 DNS](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)
- [Istio 官方文档](https://istio.io/latest/docs/)
- [Linkerd 官方文档](https://linkerd.io/2.11/overview/)
- [Cilium 官方文档](https://docs.cilium.io/)
- [CNI 官方文档](https://github.com/containernetworking/cni)

## 测验

为测试本章所学内容，请尝试 [Service 和网络测验](../quizzes/core/03-services-networking-quiz.md)。

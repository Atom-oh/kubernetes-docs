# EKS 网络测验 - 第 3 部分

本测验测试你对 Amazon EKS 中高级网络概念的理解，包括 service mesh、VPC endpoints、多集群网络和网络安全。

## 多项选择题

### 1. 在 Amazon EKS 中实施 service mesh（例如 AWS App Mesh、Istio）时，会发生的主要架构变化是什么？

A. 所有 pod-to-pod 通信都会路由到 VPC 外部 B. 会向每个 pod 添加 sidecar proxy，以调解 service-to-service 通信 C. 不再使用 Kubernetes Service objects D. 所有网络流量都会通过 AWS Transit Gateway 路由

<details>

<summary>显示答案</summary>

**答案：B. 会向每个 pod 添加 sidecar proxy，以调解 service-to-service 通信**

**解释：** 实施 service mesh 时最重要的架构变化是会向每个 pod 添加一个 sidecar proxy（通常是 Envoy）。这个 sidecar proxy 会拦截并处理该 pod 的所有入站和出站流量，从而调解 service-to-service 通信。

**主要特性：**

1. **Sidecar Pattern**：一个 proxy container 会与每个 application container 一起部署。该 proxy 处理所有网络通信。
2. **流量流向变化**：
   * 传统方式：Client → Service → Target Pod
   * Service Mesh：Client → Client Sidecar → Service → Target Sidecar → Target Pod
3. **Data Plane 和 Control Plane**：
   * Data Plane：sidecar proxies 的集合
   * Control Plane：管理 proxy 配置并应用策略的中央组件
4. **无需更改 Application Code**：service mesh 的主要优势之一，是无需更改 application code 即可添加高级网络功能。

**Service Mesh 实施示例 (AWS App Mesh)：**

```yaml
# App Mesh sidecar injection example
apiVersion: apps/v1
kind: Deployment
metadata:
  name: example-app
  labels:
    app: example
spec:
  replicas: 3
  selector:
    matchLabels:
      app: example
  template:
    metadata:
      labels:
        app: example
      annotations:
        appmesh.k8s.aws/mesh: my-mesh  # App Mesh mesh name
        appmesh.k8s.aws/virtualNode: example-vn  # Virtual node name
    spec:
      containers:
      - name: example
        image: example:latest
        ports:
        - containerPort: 8080
```

**Service Mesh 提供的功能：**

* 流量管理（路由、负载均衡、circuit breaking）
* 安全性（mTLS、authentication、authorization）
* 可观测性（metrics、logs、distributed tracing）
* 策略执行

其他选项的问题：

* **A. 所有 pod-to-pod 通信都会路由到 VPC 外部**：Service mesh 通常在 cluster 内运行，不会将流量路由到 VPC 外部。
* **C. 不再使用 Kubernetes Service objects**：Service mesh 是对 Kubernetes Service objects 的补充，而不是替代。
* **D. 所有网络流量都会通过 AWS Transit Gateway 路由**：Service mesh 与 AWS Transit Gateway 无关，它管理 cluster 内的 service-to-service 通信。

</details>

### 2. 在 Amazon EKS 中使用 VPC endpoints 私有访问 AWS services 的主要好处是什么？

A. 为所有 AWS services 提供无限带宽 B. 无需 internet gateway 即可私有访问 AWS services C. 将 AWS service 使用成本降低 50% D. 为所有 AWS services 提供自动 authentication

<details>

<summary>显示答案</summary>

**答案：B. 无需 internet gateway 即可私有访问 AWS services**

**解释：** 在 Amazon EKS 中使用 VPC endpoints 的主要好处，是能够在没有 internet gateway 的情况下私有访问 AWS services。这可以增强安全性并降低数据传输成本。

**VPC Endpoint 类型：**

1. **Interface Endpoints (AWS PrivateLink)**：
   * 为大多数 AWS services 提供私有连接
   * 在每个 subnet 中创建 endpoint network interfaces (ENIs)
   * 示例：ECR、CloudWatch、SNS、SQS 等
2. **Gateway Endpoints**：
   * 为 S3 和 DynamoDB 提供私有连接
   * 向 route tables 添加路由
   * 无额外成本

**EKS 的 VPC Endpoint 配置示例：**

```yaml
# CloudFormation example
Resources:
  S3GatewayEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      ServiceName: !Sub com.amazonaws.${AWS::Region}.s3
      VpcId: !Ref VPC
      RouteTableIds:
        - !Ref PrivateRouteTable
      VpcEndpointType: Gateway

  ECRApiEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      ServiceName: !Sub com.amazonaws.${AWS::Region}.ecr.api
      VpcId: !Ref VPC
      SubnetIds:
        - !Ref PrivateSubnet1
        - !Ref PrivateSubnet2
      SecurityGroupIds:
        - !Ref EndpointSecurityGroup
      PrivateDnsEnabled: true
      VpcEndpointType: Interface
```

**EKS 需要 VPC Endpoints 的关键 AWS Services：**

* Amazon ECR（拉取 container images）
* Amazon S3（configuration files、backups 等）
* AWS KMS（encryption keys）
* Amazon CloudWatch（logging 和 monitoring）
* AWS STS（assume IAM roles）

**使用 VPC Endpoints 的好处：**

1. **增强安全性**：流量不会经过 public internet
2. **降低网络成本**：减少到 AWS services 的数据传输成本
3. **降低延迟**：在 AWS network 内直接路由
4. **合规性**：满足数据主权和监管要求

**Private Subnets 中的 EKS Node 配置：**

```bash
# Create node group in private subnets with eksctl
eksctl create nodegroup \
  --cluster my-cluster \
  --name private-ng \
  --node-private-networking \
  --vpc-private-subnets subnet-0123456789abcdef0,subnet-0123456789abcdef1
```

其他选项的问题：

* **A. 为所有 AWS services 提供无限带宽**：VPC endpoints 不提供无限带宽；根据 service 和 region，可能存在带宽限制。
* **C. 将 AWS service 使用成本降低 50%**：VPC endpoints 可以降低数据传输成本，但不会将 AWS service 使用成本降低 50%。
* **D. 为所有 AWS services 提供自动 authentication**：VPC endpoints 不会自动化 authentication；仍然需要适当的 IAM permissions。

</details>

### 3. 在 Amazon EKS 中实施多集群网络的最有效方法是什么？

A. 在每个 cluster 上使用 public load balancers 进行 inter-cluster communication B. 使用 AWS Transit Gateway 连接多个 VPCs 并配置 inter-cluster routing C. 将所有 clusters 部署在单个 VPC 中以降低网络复杂度 D. 在每个 cluster 上使用 NAT gateways 进行 inter-cluster communication

<details>

<summary>显示答案</summary>

**答案：B. 使用 AWS Transit Gateway 连接多个 VPCs 并配置 inter-cluster routing**

**解释：** 在 Amazon EKS 中实施多集群网络的最有效方法，是使用 AWS Transit Gateway 连接多个 VPCs，并配置 inter-cluster routing。此方法提供可扩展性、安全性和易管理性。

**使用 AWS Transit Gateway 的多集群网络：**

1. **架构概述**：
   * 每个 EKS cluster 部署在单独的 VPC 中
   * Transit Gateway 连接所有 VPCs
   * Inter-cluster communication 通过 Transit Gateway 路由
2.  **配置步骤**：

    ```bash
    # 1. Create Transit Gateway
    aws ec2 create-transit-gateway --description "EKS Multi-Cluster TGW"

    # 2. Attach VPC to Transit Gateway
    aws ec2 create-transit-gateway-vpc-attachment \
      --transit-gateway-id tgw-0123456789abcdef0 \
      --vpc-id vpc-0123456789abcdef0 \
      --subnet-ids subnet-0123456789abcdef0 subnet-0123456789abcdef1

    # 3. Update routing tables
    aws ec2 create-route \
      --route-table-id rtb-0123456789abcdef0 \
      --destination-cidr-block 10.1.0.0/16 \
      --transit-gateway-id tgw-0123456789abcdef0
    ```
3. **CIDR 规划**：
   * 为每个 cluster/VPC 分配不重叠的 CIDR blocks
   * 示例：Cluster1: 10.0.0.0/16, Cluster2: 10.1.0.0/16, Cluster3: 10.2.0.0/16

**多集群 Service Discovery 选项：**

1.  **AWS Cloud Map**：

    ```bash
    # Create namespace
    aws servicediscovery create-private-dns-namespace \
      --name multi-cluster.local \
      --vpc vpc-0123456789abcdef0

    # Register service
    aws servicediscovery register-instance \
      --service-id srv-0123456789abcdef0 \
      --instance-id api-service-cluster1 \
      --attributes AWS_INSTANCE_IPV4=10.0.1.123
    ```
2.  **Custom CoreDNS Configuration**：

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
            health
            kubernetes cluster.local in-addr.arpa ip6.arpa {
               pods insecure
               upstream
               fallthrough in-addr.arpa ip6.arpa
            }
            forward . /etc/resolv.conf
            cache 30
            loop
            reload
            loadbalance
        }
        cluster2.svc.local:53 {
            errors
            cache 30
            forward . 10.1.0.2
        }
    ```

**多集群网络安全注意事项：**

1. **Inter-VPC Traffic Control**：
   * 使用 Transit Gateway security groups 和 routing tables 限制流量
   * 仅允许必要的 ports 和 protocols
2.  **Network Policies**：

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: allow-cross-cluster
    spec:
      podSelector:
        matchLabels:
          app: api-service
      ingress:
      - from:
        - ipBlock:
            cidr: 10.1.0.0/16  # Cluster2's CIDR
      egress:
      - to:
        - ipBlock:
            cidr: 10.1.0.0/16  # Cluster2's CIDR
    ```

**多集群 Service Mesh 选项：**

1. **Istio Multi-Cluster**：
   * 使用单个 control plane 管理多个 clusters
   * 跨 cluster service discovery 和 load balancing
2. **AWS App Mesh**：
   * 创建跨多个 clusters 的 mesh
   * 通过 AWS Cloud Map 进行 service discovery

**成本优化注意事项：**

* 考虑 Transit Gateway 的小时费用和数据处理费用
* 尽量减少跨 cluster 数据传输
* 尽可能在同一个 availability zone 内通信

其他选项的问题：

* **A. 在每个 cluster 上使用 public load balancers 进行 inter-cluster communication**：此方法会增加安全风险、产生 internet data transfer costs，并增加延迟。
* **C. 将所有 clusters 部署在单个 VPC 中以降低网络复杂度**：在单个 VPC 中部署多个 clusters 可能导致 IP address space 限制、缺乏安全边界以及可扩展性问题。
* **D. 在每个 cluster 上使用 NAT gateways 进行 inter-cluster communication**：NAT gateways 用于 outbound internet traffic，不适合 inter-cluster communication。

</details>

### 5. 在 Amazon EKS 中优化 pod 网络性能的最有效方法是什么？

A. 对所有 pods 使用 host network mode B. 启用 Amazon VPC CNI 的 prefix delegation 功能 C. 对所有 pods 使用 NodePort services D. 对所有 intra-cluster communication 使用 AWS Global Accelerator

<details>

<summary>显示答案</summary>

**答案：B. 启用 Amazon VPC CNI 的 prefix delegation 功能**

**解释：** 在 Amazon EKS 中优化 pod 网络性能的最有效方法，是启用 Amazon VPC CNI 的 prefix delegation 功能。该功能会显著增加分配给每个 node 的 secondary IP addresses 数量，并减少 ENI (Elastic Network Interface) 创建频率，从而提升网络性能和可扩展性。

**Prefix Delegation 的工作原理：**

1. **Default VPC CNI vs Prefix Delegation**：
   * Default VPC CNI：为每个 ENI 分配单独的 secondary IP addresses
   * Prefix Delegation：为每个 ENI 分配 /28 CIDR blocks（16 个 IPs）
2.  **启用方法**：

    ```bash
    # Enable prefix delegation
    kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true

    # Verify prefix delegation
    kubectl describe daemonset aws-node -n kube-system | grep ENABLE_PREFIX_DELEGATION
    ```
3.  **其他配置选项**：

    ```bash
    # Set prefix allocation size (default: /28)
    kubectl set env daemonset aws-node -n kube-system WARM_PREFIX_TARGET=1

    # Threshold for requesting new prefix when available IPs are low
    kubectl set env daemonset aws-node -n kube-system WARM_IP_TARGET=5
    ```

**Prefix Delegation 的好处：**

1. **提升可扩展性**：
   * 增加每个 node 的最大 pods 数量（通常从 110 增加到 250+）
   * 因 ENI 创建调用减少而降低 API throttling
2. **更快的 Pod 启动时间**：
   * 减少为新 pods 分配 IP addresses 所需的 API calls
   * 改善大规模 pod deployments 的性能
3. **IP 地址效率**：
   * 用相同数量的 ENIs 支持更多 pods
   * 缓解 IP address exhaustion 问题

**每种 Instance Type 的最大 Pods 数量对比：**

| Instance Type | Default VPC CNI | Prefix Delegation Enabled |
| ------------- | --------------- | ------------------------- |
| t3.medium     | 17              | 110                       |
| m5.large      | 29              | 110                       |
| c5.xlarge     | 58              | 250                       |
| r5.2xlarge    | 58              | 250                       |

**配置示例 (ConfigMap)：**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: amazon-vpc-cni
  namespace: kube-system
data:
  enable-prefix-delegation: "true"
  warm-prefix-target: "1"
  warm-ip-target: "5"
```

**注意事项和限制：**

1. **Subnet Size**：
   * Prefix delegation 需要足够大的 subnets
   * 建议最小使用 /24 CIDR block
2. **Security Group Rules**：
   * 使用 prefix delegation 可以简化 security group rules
   * 可以引用 CIDR blocks，而不是单独的 IPs
3. **兼容性**：
   * 一些旧版 EC2 instance types 不支持 prefix delegation
   * 建议使用 Nitro-based instances
4. **IP Address Management**：
   * Prefix delegation 会更高效地使用 IP addresses，但仍然需要适当的 CIDR 规划

**监控和故障排查：**

```bash
# Check IP address allocation per node
kubectl exec -n kube-system aws-node-xxxxx -- curl -s http://localhost:61679/v1/enis | jq

# Check prefix delegation status
kubectl logs -n kube-system aws-node-xxxxx | grep -i prefix
```

其他选项的问题：

* **A. 对所有 pods 使用 host network mode**：Host network mode 会导致 pods 共享 node 的 network namespace，从而造成端口冲突并移除网络隔离。
* **C. 对所有 pods 使用 NodePort services**：NodePort 是一种 service 暴露机制，与 pod 网络性能优化无关。
* **D. 对所有 intra-cluster communication 使用 AWS Global Accelerator**：AWS Global Accelerator 用于 global traffic management，不适合 intra-cluster communication 优化。

</details>

## 简答题

### 7. 在 Amazon EKS 中实施 service mesh 时，最常用作 sidecar proxies 的开源 proxy 是什么？

<details>

<summary>显示答案</summary>

**答案：** Envoy

**详细解释：**

在 Amazon EKS 中实施 service mesh 时，最常用的 sidecar proxy 是 Envoy。Envoy 是一个基于 C++ 的高性能 proxy，在大多数主流 service mesh 实现（Istio、AWS App Mesh、Consul Connect 等）中用作 data plane proxy。

**Envoy 的主要特性：**

1. **高性能架构**：
   * 使用 C++ 编写，具备低延迟和高吞吐
   * Event-driven、asynchronous networking model
2. **丰富的流量管理功能**：
   * Load balancing（round robin、weighted、least request 等）
   * Circuit breaking 和 outlier detection
   * Retry 和 timeout policies
   * Traffic splitting 和 mirroring
3. **可观测性**：
   * 详细的 metrics 和 statistics
   * Distributed tracing integration（Zipkin、Jaeger 等）
   * Access logging
4. **安全功能**：
   * TLS/mTLS termination
   * Authentication 和 authorization
   * Rate limiting

**Service Mesh 中的 Envoy 部署：**

1.  **Sidecar Pattern**：

    ```yaml
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: example-app
    spec:
      template:
        spec:
          containers:
          - name: app
            image: app:latest
          - name: envoy-proxy
            image: envoyproxy/envoy:v1.20.0
            ports:
            - containerPort: 15001
            volumeMounts:
            - name: envoy-config
              mountPath: /etc/envoy
          volumes:
          - name: envoy-config
            configMap:
              name: envoy-config
    ```
2. **Automatic Injection**：
   * Istio: `sidecar.istio.io/inject: "true"` annotation
   * AWS App Mesh: `appmesh.k8s.aws/sidecarInjectorWebhook: enabled` label

**Envoy 配置示例：**

```yaml
static_resources:
  listeners:
  - address:
      socket_address:
        address: 0.0.0.0
        port_value: 15001
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: ingress_http
          route_config:
            name: local_route
            virtual_hosts:
            - name: backend
              domains: ["*"]
              routes:
              - match:
                  prefix: "/"
                route:
                  cluster: service_backend
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  clusters:
  - name: service_backend
    connect_timeout: 0.25s
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: service_backend
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: backend-service
                port_value: 80
```

**Service Mesh 中的 Envoy 集成：**

1. **Istio**：
   * 使用 Envoy 作为 sidecar proxy
   * istiod 动态管理 Envoy 配置
   * Pilot、Mixer、Citadel 等组件与 Envoy 集成
2. **AWS App Mesh**：
   * AWS App Mesh controller 注入 Envoy sidecar
   * 与 AWS Cloud Map 集成以进行 service discovery
   * Envoy Management Service (EMS) 管理 Envoy 配置
3. **Consul Connect**：
   * 使用 Envoy 作为 data plane proxy
   * Consul 提供 service discovery 和 configuration management

**Envoy 监控和调试：**

```bash
# Port forward Envoy admin interface
kubectl port-forward <pod-name> 19000:19000

# Check configuration and stats
curl localhost:19000/config_dump
curl localhost:19000/stats

# Check cluster status
curl localhost:19000/clusters
```

**性能优化注意事项：**

* Resource allocation：为 Envoy 分配足够的 CPU 和 memory
* Connection pooling：配置 upstream connection pooling 以提升性能
* Buffer size：设置适当的 buffer sizes 以优化 memory usage
* Filter chain：仅启用必要的 filters，以尽量减少 overhead

Envoy 是现代 service mesh 架构的核心组件，在让 microservice 通信变得安全、可靠且可观测方面发挥关键作用。

</details>

### 8. 在 Amazon EKS clusters 中负责内部 DNS resolution 的 Kubernetes add-on 名称是什么？

<details>

<summary>显示答案</summary>

**答案：** CoreDNS

**详细解释：**

在 Amazon EKS clusters 中负责内部 DNS resolution 的 Kubernetes add-on 是 CoreDNS。CoreDNS 是 Kubernetes clusters 内用于 service discovery 的 DNS server，负责处理 pods 和 services 的名称解析。

**CoreDNS 的主要特性：**

1. **Service Discovery**：
   * 解析格式为 `<service-name>.<namespace>.svc.cluster.local` 的 DNS names
   * 支持对 pod IP addresses 进行 reverse DNS lookups
2. **Plugin Architecture**：
   * 通过各种 plugins 扩展功能
   * Caching、metrics、logging、error handling 等
3. **配置灵活性**：
   * 通过 Corefile 进行 declarative configuration
   * 支持 dynamic reload

**EKS 中的 CoreDNS 部署：**

1. **Default Deployment Configuration**：
   * 创建 EKS cluster 时自动部署
   * 在 kube-system namespace 中运行
   * 通常部署 2 个或更多 replicas
2.  **验证**：

    ```bash
    # Check CoreDNS pods
    kubectl get pods -n kube-system -l k8s-app=kube-dns

    # Check CoreDNS version
    kubectl describe deployment coredns -n kube-system | grep Image
    ```

**CoreDNS 配置 (Corefile)：**

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

**关键 Plugin 说明：**

1. **errors**：记录 errors
2. **health**：提供 health check endpoint
3. **ready**：提供 readiness check endpoint
4. **kubernetes**：处理 Kubernetes service discovery
5. **prometheus**：暴露 Prometheus metrics
6. **forward**：将 external DNS queries 转发到 upstream DNS servers
7. **cache**：缓存 DNS responses
8. **loop**：检测并防止 DNS loops
9. **reload**：Corefile 发生变化时自动重新加载
10. **loadbalance**：在多个 A/AAAA records 之间进行 load balancing

**自定义配置示例：**

1.  **为 External Domain 使用特定 DNS Server**：

    ```
    example.com {
        forward . 10.0.0.1
    }
    ```
2.  **Stub Domain Configuration**：

    ```
    internal.corp {
        file /etc/coredns/internal.db
    }
    ```
3.  **Conditional Forwarding**：

    ```
    . {
        forward . 8.8.8.8 8.8.4.4 {
            policy sequential
        }
    }
    ```

**性能优化和扩展：**

1.  **Auto Scaling**：

    ```yaml
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    metadata:
      name: coredns
      namespace: kube-system
    spec:
      scaleTargetRef:
        apiVersion: apps/v1
        kind: Deployment
        name: coredns
      minReplicas: 2
      maxReplicas: 10
      metrics:
      - type: Resource
        resource:
          name: cpu
          target:
            type: Utilization
            averageUtilization: 60
    ```
2.  **Resource Allocation Optimization**：

    ```yaml
    resources:
      limits:
        memory: 170Mi
      requests:
        cpu: 100m
        memory: 70Mi
    ```
3.  **Cache Tuning**：

    ```
    cache {
        success 10000
        denial 1000
        prefetch 10 10% 2m
    }
    ```

**故障排查：**

1.  **DNS Resolution Test**：

    ```bash
    # Create test pod
    kubectl run dnsutils --image=gcr.io/kubernetes-e2e-test-images/dnsutils:1.3 -- sleep 3600

    # Test DNS lookup
    kubectl exec -it dnsutils -- nslookup kubernetes.default
    ```
2.  **Check CoreDNS Logs**：

    ```bash
    kubectl logs -n kube-system -l k8s-app=kube-dns
    ```
3.  **Check DNS Policy**：

    ```bash
    kubectl get pods <pod-name> -o jsonpath='{.spec.dnsPolicy}'
    ```

CoreDNS 是 EKS clusters 的关键组件，为 microservices 架构提供核心 service discovery 功能。通过适当的配置和监控来确保可靠的 DNS service 至关重要。

</details>

## 动手实践题

### 10. 说明如何在 Amazon EKS cluster 中实施 service mesh（例如 AWS App Mesh），以保护和监控 microservice 通信。请包括实施步骤、关键组件和监控方法。

<details>

<summary>显示答案</summary>

**答案：**

以下是在 Amazon EKS cluster 中实施 AWS App Mesh，以保护和监控 microservice 通信的方法：

### 1. AWS App Mesh 实施步骤

#### 1.1. 设置先决条件

```bash
# Set up required IAM permissions
eksctl create iamserviceaccount \
  --cluster=my-cluster \
  --namespace=appmesh-system \
  --name=appmesh-controller \
  --attach-policy-arn=arn:aws:iam::aws:policy/AWSCloudMapFullAccess,arn:aws:iam::aws:policy/AWSAppMeshFullAccess \
  --override-existing-serviceaccounts \
  --approve

# Add Helm repository
helm repo add eks https://aws.github.io/eks-charts
helm repo update
```

#### 1.2. 安装 App Mesh Controller

```bash
# Create App Mesh controller namespace
kubectl create ns appmesh-system

# Install App Mesh controller
helm install appmesh-controller eks/appmesh-controller \
  --namespace appmesh-system \
  --set region=${AWS_REGION} \
  --set serviceAccount.create=false \
  --set serviceAccount.name=appmesh-controller
```

#### 1.3. 创建 Mesh

```yaml
# mesh.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: Mesh
metadata:
  name: my-mesh
spec:
  namespaceSelector:
    matchLabels:
      mesh: my-mesh
```

```bash
kubectl apply -f mesh.yaml
```

#### 1.4. 设置 Application Namespace

```bash
# Create and label application namespace
kubectl create ns app-namespace
kubectl label namespace app-namespace mesh=my-mesh
kubectl label namespace app-namespace appmesh.k8s.aws/sidecarInjectorWebhook=enabled
```

#### 1.5. 定义 Virtual Nodes 和 Services

```yaml
# virtual-node.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualNode
metadata:
  name: service-a
  namespace: app-namespace
spec:
  podSelector:
    matchLabels:
      app: service-a
  listeners:
    - portMapping:
        port: 8080
        protocol: http
      healthCheck:
        protocol: http
        path: "/health"
        port: 8080
        healthyThreshold: 2
        unhealthyThreshold: 2
        timeoutMillis: 2000
        intervalMillis: 5000
  backends:
    - virtualService:
        virtualServiceRef:
          name: service-b
  serviceDiscovery:
    dns:
      hostname: service-a.app-namespace.svc.cluster.local
```

```yaml
# virtual-service.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualService
metadata:
  name: service-a
  namespace: app-namespace
spec:
  awsName: service-a.app-namespace.svc.cluster.local
  provider:
    virtualRouter:
      virtualRouterRef:
        name: service-a-router
```

```yaml
# virtual-router.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualRouter
metadata:
  name: service-a-router
  namespace: app-namespace
spec:
  listeners:
    - portMapping:
        port: 8080
        protocol: http
  routes:
    - name: service-a-route
      httpRoute:
        match:
          prefix: /
        action:
          weightedTargets:
            - virtualNodeRef:
                name: service-a
              weight: 1
```

#### 1.6. 部署 Application

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: service-a
  namespace: app-namespace
spec:
  replicas: 3
  selector:
    matchLabels:
      app: service-a
  template:
    metadata:
      labels:
        app: service-a
    spec:
      containers:
      - name: service-a
        image: service-a:latest
        ports:
        - containerPort: 8080
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
```

### 2. 使用 mTLS 配置保护通信

#### 2.1. 设置 AWS Certificate Manager Private CA

```bash
# Create private CA
aws acm-pca create-certificate-authority \
  --certificate-authority-configuration file://ca-config.json \
  --certificate-authority-type "ROOT" \
  --idempotency-token 1234567890 \
  --tags Key=Name,Value=AppMeshCA

# Save CA ARN
export CA_ARN=$(aws acm-pca list-certificate-authorities --query 'CertificateAuthorities[?Status==`ACTIVE`].Arn' --output text)
```

#### 2.2. 添加 TLS 配置

```yaml
# virtual-node-with-tls.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualNode
metadata:
  name: service-a
  namespace: app-namespace
spec:
  podSelector:
    matchLabels:
      app: service-a
  listeners:
    - portMapping:
        port: 8080
        protocol: http
      tls:
        mode: STRICT  # Enable mTLS
        certificate:
          acm:
            certificateArn: arn:aws:acm:region:account-id:certificate/certificate-id
  backends:
    - virtualService:
        virtualServiceRef:
          name: service-b
        clientPolicy:
          tls:
            enforce: true
            ports:
              - 8080
            validation:
              trust:
                acm:
                  certificateAuthorityArns:
                    - ${CA_ARN}
  serviceDiscovery:
    dns:
      hostname: service-a.app-namespace.svc.cluster.local
```

### 3. 设置 Monitoring 和 Observability

#### 3.1. AWS X-Ray 集成

```yaml
# mesh-with-xray.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: Mesh
metadata:
  name: my-mesh
spec:
  namespaceSelector:
    matchLabels:
      mesh: my-mesh
  egressFilter:
    type: ALLOW_ALL
  tracing:
    awsXRay:
      logLevel: INFO
```

```bash
# Deploy X-Ray daemon
kubectl apply -f https://github.com/aws/aws-app-mesh-controller-for-k8s/raw/master/config/samples/xray-daemon.yaml
```

#### 3.2. Amazon CloudWatch 集成

```yaml
# envoy-config.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: Mesh
metadata:
  name: my-mesh
spec:
  namespaceSelector:
    matchLabels:
      mesh: my-mesh
  egressFilter:
    type: ALLOW_ALL
  serviceDiscovery:
    ipPreference: IPv4_PREFERRED
  logging:
    accessLog:
      file:
        path: /dev/stdout
        format:
          json:
            - key: "source"
              value: "%DOWNSTREAM_REMOTE_ADDRESS%"
            - key: "destination"
              value: "%UPSTREAM_REMOTE_ADDRESS%"
            - key: "protocol"
              value: "%PROTOCOL%"
```

```bash
# Deploy CloudWatch agent
kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/cloudwatch-namespace.yaml

kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/cwagent/cwagent-serviceaccount.yaml

kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/cwagent/cwagent-configmap.yaml

kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/cwagent/cwagent-daemonset.yaml
```

#### 3.3. Prometheus 和 Grafana 设置

```bash
# Create Prometheus namespace
kubectl create namespace prometheus

# Install Prometheus
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/prometheus \
  --namespace prometheus \
  --set alertmanager.persistentVolume.storageClass="gp2" \
  --set server.persistentVolume.storageClass="gp2"

# Install Grafana
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
helm install grafana grafana/grafana \
  --namespace prometheus \
  --set persistence.storageClassName="gp2" \
  --set persistence.enabled=true \
  --set adminPassword='EKS!sAWSome' \
  --values grafana.yaml \
  --set service.type=LoadBalancer
```

```yaml
# grafana.yaml
datasources:
  datasources.yaml:
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      url: http://prometheus-server.prometheus.svc.cluster.local
      access: proxy
      isDefault: true
```

### 4. 配置 Traffic Management 和高级功能

#### 4.1. Canary Deployment 配置

```yaml
# virtual-router-canary.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualRouter
metadata:
  name: service-a-router
  namespace: app-namespace
spec:
  listeners:
    - portMapping:
        port: 8080
        protocol: http
  routes:
    - name: service-a-route
      httpRoute:
        match:
          prefix: /
        action:
          weightedTargets:
            - virtualNodeRef:
                name: service-a-v1
              weight: 90
            - virtualNodeRef:
                name: service-a-v2
              weight: 10
```

#### 4.2. Circuit Breaker 配置

```yaml
# virtual-node-circuit-breaker.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualNode
metadata:
  name: service-a
  namespace: app-namespace
spec:
  # ... existing configuration ...
  listeners:
    - portMapping:
        port: 8080
        protocol: http
      outlierDetection:
        baseEjectionDuration:
          unit: s
          value: 30
        interval:
          unit: s
          value: 10
        maxEjectionPercent: 50
        maxServerErrors: 5
```

#### 4.3. Retry Policy 配置

```yaml
# virtual-router-retry.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualRouter
metadata:
  name: service-a-router
  namespace: app-namespace
spec:
  # ... existing configuration ...
  routes:
    - name: service-a-route
      httpRoute:
        match:
          prefix: /
        action:
          weightedTargets:
            - virtualNodeRef:
                name: service-a
              weight: 1
        retryPolicy:
          maxRetries: 3
          perRetryTimeout:
            unit: ms
            value: 2000
          httpRetryEvents:
            - server-error
            - gateway-error
            - client-error
            - stream-error
```

### 5. Monitoring 和 Troubleshooting

#### 5.1. 检查 Envoy Proxy Logs

```bash
# Check Envoy sidecar logs for specific pod
kubectl logs <pod-name> -c envoy -n app-namespace

# Stream all Envoy logs
kubectl logs -f -l app=service-a -c envoy -n app-namespace
```

#### 5.2. 访问 Envoy Admin Interface

```bash
# Set up port forwarding
kubectl port-forward <pod-name> -n app-namespace 9901:9901

# Access in browser
# http://localhost:9901/
```

#### 5.3. 检查 X-Ray Traces

导航到 AWS Management Console 中的 X-Ray service，以查看 service maps 和 traces。

#### 5.4. 创建 CloudWatch Dashboard

```bash
# Prepare JSON file for CloudWatch dashboard creation
cat > appmesh-dashboard.json << EOF
{
  "widgets": [
    {
      "type": "metric",
      "x": 0,
      "y": 0,
      "width": 12,
      "height": 6,
      "properties": {
        "metrics": [
          [ "AWS/AppMesh", "RequestCount", "MeshName", "my-mesh", "VirtualNodeName", "service-a", { "stat": "Sum" } ]
        ],
        "period": 60,
        "region": "${AWS_REGION}",
        "title": "Request Count"
      }
    },
    {
      "type": "metric",
      "x": 12,
      "y": 0,
      "width": 12,
      "height": 6,
      "properties": {
        "metrics": [
          [ "AWS/AppMesh", "Latency", "MeshName", "my-mesh", "VirtualNodeName", "service-a", { "stat": "Average" } ]
        ],
        "period": 60,
        "region": "${AWS_REGION}",
        "title": "Latency"
      }
    }
  ]
}
EOF

# Create dashboard using AWS CLI
aws cloudwatch put-dashboard --dashboard-name AppMeshDashboard --dashboard-body file://appmesh-dashboard.json
```

### 6. Best Practices 和注意事项

#### 6.1. Resource Requirements

* 由于每个 pod 都会添加 Envoy sidecar，因此需要规划 node resources
* 通常为每个 Envoy proxy 分配 100-200m CPU 和 128-256Mi memory

#### 6.2. 渐进式实施策略

1. **Phased Approach**：
   * 从非业务关键 services 开始
   * 使用 traffic mirroring 评估影响
   * 成功验证后逐步扩大范围
2. **mTLS Implementation**：
   * 从 PERMISSIVE mode 开始
   * 验证所有 services 都兼容
   * 切换到 STRICT mode

#### 6.3. Performance Optimization

* 调整 Envoy resource limits
* 设置适当的 health check intervals
* 尽量减少不必要的 logging 和 tracing

#### 6.4. Security Hardening

* 使用 least privilege IAM policies
* 定期轮换 certificates
* 通过 network policies 实施 defense in depth

AWS App Mesh 为在 EKS clusters 中保护和监控 microservice 通信提供了强大的 service mesh 解决方案。适当的配置和监控可以显著提升 application 的可靠性、安全性和可观测性。

</details>

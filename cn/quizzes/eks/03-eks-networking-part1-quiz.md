# EKS 网络测验 - 第 1 部分

本测验用于测试你对 Amazon EKS 中基础网络概念、VPC CNI、网络策略和服务发现的理解。它重点关注 EKS 集群的网络架构和组件。

## 多项选择题

### 1. Amazon EKS 默认使用的 CNI (Container Network Interface) 插件是什么？

A. Calico B. Flannel C. Amazon VPC CNI D. Weave Net

<details>

<summary>显示答案</summary>

**答案：C. Amazon VPC CNI**

**解释：** Amazon EKS 默认使用 Amazon VPC CNI 插件。该插件为 Kubernetes pods 分配 VPC IP 地址，并使用 AWS VPC 网络的原生功能实现 pods 之间的通信。

**主要特性：**

1. **原生 VPC 网络**：每个 pod 都会获得 VPC 内的唯一 IP 地址。这允许 pods 与 VPC 内的其他服务直接通信。
2. **辅助 IP 地址分配**：辅助 IP 地址会分配给每个节点的 Elastic Network Interface (ENI)，并提供给 pods 使用。
3. **Security Group 集成**：AWS security groups 可以应用在 pod 级别，从而实现细粒度的网络安全控制。
4. **性能**：通过不使用 overlay networks 来提升网络性能。
5. **AWS Service 集成**：可与 AWS Load Balancer Controller 和 AWS App Mesh 等其他 AWS services 无缝集成。

**配置示例：**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: amazon-vpc-cni
  namespace: kube-system
data:
  enable-network-policy: "true"
  enable-pod-eni: "true"
  warm-ip-target: "5"
  minimum-ip-target: "10"
```

Amazon VPC CNI 是开源的，并在 GitHub 上进行管理。它可以根据需要替换为 Calico 或 Cilium 等其他 CNI plugins，但 Amazon VPC CNI 是 EKS 的默认选项，并由 AWS 官方支持。

</details>

### 2. 在 Amazon EKS 中，VPC CNI 如何为 pods 分配 IP 地址？

A. 为每个 pod 分配单独的 Elastic Network Interface (ENI) B. 将辅助 IP 地址分配给节点的 Elastic Network Interface (ENI)，并提供给 pods C. 使用 overlay networks 分配虚拟 IP 地址 D. 为每个 pod 分配单独的 VPC subnet

<details>

<summary>显示答案</summary>

**答案：B. 将辅助 IP 地址分配给节点的 Elastic Network Interface (ENI)，并提供给 pods**

**解释：** Amazon VPC CNI 的工作方式是将辅助 IP 地址分配给节点的 Elastic Network Interface (ENI)，并将这些 IP 地址提供给 pods。该方法也称为“IP-per-Pod”模型。

**工作原理：**

1. **ENI 分配**：每个 EC2 instance（节点）可以有一个或多个 ENIs。每个 ENI 可分配的 IP 地址数量由 instance type 决定。
2. **IP 地址池管理**：VPC CNI 的 `aws-node` DaemonSet 在每个节点上运行，并管理可用的 IP 地址池。
3. **IP 地址分配**：创建 pod 时，CNI 会从池中分配一个 IP 地址，并将其连接到 pod 的 network namespace。
4. **IP 地址回收**：pod 终止时，CNI 会回收该 IP 地址并将其返回到池中。

**示例配置：**

```bash
# Maximum pods per node calculation
Maximum pods = (Number of ENIs × (IP addresses per ENI - 1)) + 2

# For m5.large instance
# Number of ENIs: 3, IP addresses per ENI: 10
Maximum pods = (3 × (10 - 1)) + 2 = 29
```

**主要注意事项：**

1. **IP 地址限制**：每个节点可运行的最大 pods 数量会因 instance type 而受限。
2. **Warm IPs**：VPC CNI 可以通过 `WARM_IP_TARGET` 设置预分配一定数量的 IP 地址，以减少 pod 启动时间。
3. **Prefix Delegation**：较新版本的 VPC CNI 支持 prefix delegation 功能，该功能会为每个 ENI 分配 /28 CIDR blocks（16 个 IP），从而提高 IP 地址密度。
4. **Security Groups**：启用 `ENABLE_POD_ENI` 设置后，可以为特定 pods 配置单独的 security groups（Security Groups for Pods 功能）。

其他选项的问题：

* **A**：通常不会为每个 pod 分配单独的 ENI。由于每个 EC2 instance 的 ENI 数量有限，这种方式效率很低。
* **C**：VPC CNI 不使用 overlay networks。这是 Flannel 或 Weave Net 等其他 CNI plugins 的特征。
* **D**：在 AWS VPC 架构中，无法为每个 pod 分配单独的 VPC subnet。

</details>

### 3. 为什么 Amazon EKS 中的 pod-to-pod 通信会直接在 VPC 内发生，而不会出到外部？

A. 因为所有 pods 都位于同一个 subnet 中 B. 因为 pods 共享节点的 network namespace C. 因为 pods 被直接分配了 VPC IP 地址 D. 因为 pod-to-pod 通信总是通过 service mesh

<details>

<summary>显示答案</summary>

**答案：C. 因为 pods 被直接分配了 VPC IP 地址**

**解释：** Amazon EKS 中 pod-to-pod 通信会直接在 VPC 内发生而不会出到外部，主要原因是 Amazon VPC CNI 插件会直接为每个 pod 分配 VPC IP 地址。

**关键机制：**

1. **VPC IP 地址分配**：每个 pod 都会从 VPC subnet 获取唯一 IP 地址。该 IP 地址是连接到节点 ENI 的辅助 IP 地址。
2. **直接路由**：由于 pods 拥有 VPC IP 地址，它们可以与 VPC 中的其他资源（其他 pods、EC2 instances、RDS databases 等）直接通信。
3. **VPC 路由表**：Pod-to-pod 通信遵循 VPC 路由表，并直接在同一个 VPC 内路由，不会出到外部。

**优势：**

1. **网络性能**：不使用 overlay networks 或 NAT，从而降低延迟并提高吞吐量。
2. **安全性**：可以利用现有的 AWS 网络安全机制，如 VPC security groups 和 network ACLs。
3. **可见性**：可以通过 VPC Flow Logs 监控和分析 pod-to-pod 流量。
4. **AWS Service 集成**：由于 pods 拥有 VPC IP 地址，它们可以与 VPC endpoints 和 PrivateLink 等 AWS services 无缝集成。

**示例场景：**

当 Pod A (IP: 10.0.1.23) 与 Pod B (IP: 10.0.2.45) 通信时：

1. Pod A 将数据包直接发送到 Pod B 的 IP 地址 (10.0.2.45)。
2. 数据包会根据 VPC 路由表进行路由。
3. 数据包直接在 VPC 内到达 Pod B。
4. 在整个过程中，数据包不会离开 VPC。

其他选项的问题：

* **A**：Pods 可以分布在多个 subnets 中，不同 subnets 中的 pods 仍然可以在 VPC 内直接通信。
* **B**：Pods 不共享节点的 network namespace。每个 pod 都有自己的 network namespace。
* **D**：Pod-to-pod 通信并不总是通过 service mesh。Service mesh 是可选的附加层。

</details>

### 4. 在 Amazon EKS 中，用于控制 pods 入站和出站流量的最合适 Kubernetes 资源是什么？

A. Service B. Ingress C. NetworkPolicy D. SecurityContext

<details>

<summary>显示答案</summary>

**答案：C. NetworkPolicy**

**解释：** 在 Amazon EKS 中，用于控制 pods 入站和出站流量的最合适 Kubernetes 资源是 NetworkPolicy。NetworkPolicy 是 Kubernetes 的网络安全机制，允许对 pods 之间的通信进行细粒度控制。

**NetworkPolicy 的主要特性：**

1. **选择性应用**：可以使用 label selectors 将策略应用到特定 pods。
2. **入站和出站规则**：可以同时控制 ingress（入站）和 egress（出站）流量。
3. **多种 Selectors**：可以基于 namespaces、labels、IP CIDR blocks、ports 等过滤流量。
4. **默认拒绝策略**：未明确允许的流量默认会被拒绝。

**NetworkPolicy 示例：**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-allow
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          purpose: frontend
    - podSelector:
        matchLabels:
          role: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          purpose: database
    ports:
    - protocol: TCP
      port: 5432
```

**EKS 中的 NetworkPolicy 实现：**

要在 Amazon EKS 中使用 NetworkPolicy，需要支持 network policies 的 CNI plugin。默认的 Amazon VPC CNI 不直接支持 network policies，因此需要额外配置：

1.  **安装 Calico**：Calico 是在 EKS 中实现 NetworkPolicy 最常见的方式。

    ```bash
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml
    ```
2.  **在 Amazon VPC CNI 中启用 Network Policy**：较新版本的 Amazon VPC CNI 提供 network policy 支持。

    ```bash
    kubectl set env daemonset aws-node -n kube-system ENABLE_NETWORK_POLICY=true
    ```

其他选项的问题：

* **A. Service**：Service 为 pods 提供网络访问，但不具备流量控制或过滤能力。
* **B. Ingress**：Ingress 用于将 HTTP/HTTPS 流量路由到集群内的 services，但不定义通用网络策略。
* **D. SecurityContext**：SecurityContext 定义 pod 或 container 级别的安全设置，但与网络流量控制无关。

</details>

### 5. EKS 集群内用于服务发现的 DNS service 是什么？

A. Amazon Route 53 B. CoreDNS C. kube-dns D. AWS Cloud Map

<details>

<summary>显示答案</summary>

**答案：B. CoreDNS**

**解释：** Amazon EKS clusters 中默认用于服务发现的 DNS service 是 CoreDNS。CoreDNS 是一个灵活且可扩展的 DNS server，可在 Kubernetes clusters 内提供基于 DNS 的服务发现。

**CoreDNS 的主要特性：**

1. **Kubernetes 集成**：CoreDNS 与 Kubernetes API 集成，自动为 services 和 pods 创建 DNS records。
2. **Plugin 架构**：CoreDNS 可以通过各种 plugins 扩展功能。
3. **高可用性**：在 EKS 中，CoreDNS 通常以多个 replicas 部署，以确保高可用性。
4. **可配置性**：可以通过 Corefile 配置各种 DNS settings。

**EKS 中的 CoreDNS 部署：**

创建 EKS cluster 时，CoreDNS 会自动部署。CoreDNS 作为 `kube-system` namespace 中的 Deployment 运行：

```bash
kubectl get deployment coredns -n kube-system
```

**CoreDNS 配置示例：**

CoreDNS 配置存储在 ConfigMap 中：

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

**服务发现的工作方式：**

1. **Service 创建**：创建 Kubernetes Service 时，CoreDNS 会自动创建 DNS record。
2. **DNS 名称格式**：
   * Service: `<service-name>.<namespace>.svc.cluster.local`
   * Pod: `<pod-ip>.<namespace>.pod.cluster.local`
3. **DNS 查询**：当集群内的 pod 使用 service 名称执行 DNS 查询时，CoreDNS 会返回该 service 的 ClusterIP。

**示例：**

```bash
# If my-service service exists in the default namespace
nslookup my-service.default.svc.cluster.local

# Result
Name:   my-service.default.svc.cluster.local
Address: 10.100.43.150  # Service's ClusterIP
```

**CoreDNS 扩展和优化：**

在 EKS 中，CoreDNS 不会随 cluster 规模自动扩展，因此在大型 clusters 中，你可能需要手动扩展：

```bash
kubectl scale deployment coredns --replicas=4 -n kube-system
```

此外，可以通过调整 cache 设置来优化性能：

```yaml
cache {
    success 10000
    denial 1000
    prefetch 10 10m 20%
}
```

其他选项的问题：

* **A. Amazon Route 53**：Route 53 是 AWS 的 DNS service，但默认不用于 EKS clusters 内的服务发现。
* **C. kube-dns**：kube-dns 曾在早期 Kubernetes 版本中使用，但在 EKS 中已被 CoreDNS 取代。
* **D. AWS Cloud Map**：Cloud Map 是 AWS 的服务发现 service，但不是 EKS clusters 内默认的 DNS service。

</details>

## 简答题

### 6. 在 Amazon EKS cluster 中，限制每个节点最大 pods 数量的主要因素是什么，可以用哪些方法提高它？

<details>

<summary>显示答案</summary>

**答案：** 在 Amazon EKS cluster 中，限制每个节点最大 pods 数量的主要因素是 **每种 EC2 instance type 的 ENIs (Elastic Network Interfaces) 数量以及每个 ENI 可分配的 IP 地址数量**。提高该数量的主要方法是 **启用 Prefix Delegation 功能**。

**详细解释：**

1.  **每个节点最大 Pods 数量计算公式**：

    ```
    Maximum pods = (Number of ENIs × (IP addresses per ENI - 1)) + 2
    ```

    * 每个 ENI 的第一个 IP 地址会保留给节点自身使用。
    * 额外的 2 个用于 kube-proxy 和 aws-node pods。
2. **按 Instance Type 的限制示例**：
   * **t3.small**: (3 ENIs × (4 IPs - 1)) + 2 = 11 pods
   * **m5.large**: (3 ENIs × (10 IPs - 1)) + 2 = 29 pods
   * **c5.4xlarge**: (8 ENIs × (30 IPs - 1)) + 2 = 234 pods
3.  **通过 Prefix Delegation 扩展**：Prefix delegation 是一种为每个 ENI 分配 /28 CIDR blocks（16 个 IP）而不是单个 IP 地址的功能。

    **启用方法**：

    ```bash
    # Modify ConfigMap
    kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true

    # Optionally set prefix allocation mode
    kubectl set env daemonset aws-node -n kube-system WARM_PREFIX_TARGET=1
    ```

    **启用 Prefix Delegation 后的计算公式**：

    ```
    Maximum pods = (Number of ENIs × (Prefixes per ENI × IPs per prefix - 1)) + 2
    ```

    示例：启用 prefix delegation 的 m5.large

    * 未启用 prefix delegation：29 pods
    * 启用 prefix delegation：(3 ENIs × (1 prefix × 16 IPs - 1)) + 2 = 47 pods
4. **提高最大 Pod 数量的其他方法**：
   * **使用更大的 Instance Types**：更改为支持更多 ENIs 和 IP 地址的 instance types
   * **自定义 CNI 配置**：使用 `--max-pods` flag 调整 kubelet 配置（不推荐）
   * **使用替代 CNI Plugins**：切换到使用 overlay networks 的 CNI plugins，例如 Calico、Cilium
5. **注意事项**：
   * Prefix delegation 仅在基于 EC2 Nitro 的 instances 上受支持。
   * 启用 prefix delegation 后，无法使用 SecurityGroupsForPods 功能。
   * 随着每个节点的 pods 数量增加，可能会出现节点资源（CPU、memory）争用，因此选择合适的 instance size 很重要。
6.  **监控和优化**：

    ```bash
    # Check current IP address usage
    kubectl exec -n kube-system ds/aws-node -- curl -s http://localhost:61679/v1/enis | jq

    # Check prefix delegation status
    kubectl describe daemonset aws-node -n kube-system | grep PREFIX
    ```

虽然启用 prefix delegation 可以显著提高每个节点的最大 pod 数量，但必须根据你的 cluster 需求和 workload 特性选择合适的配置。

</details>

### 7. 在 Amazon EKS 中，允许为 pods 分配特定 AWS security groups 的功能叫什么，如何配置它？

<details>

<summary>显示答案</summary>

**答案：** 在 Amazon EKS 中，允许为 pods 分配特定 AWS security groups 的功能称为 **Security Groups for Pods** 或 **Pod ENI (Elastic Network Interface)**。该功能可以通过在 VPC CNI 中启用 **ENABLE\_POD\_ENI** 选项来配置。

**详细解释：**

1. **Security Groups for Pods 概览**：该功能会为特定 pods 创建单独的 ENI（也称为 trunk ENI），并将 security groups 附加到该 ENI，从而在 pod 级别实现细粒度的网络安全控制。
2. **前提条件**：
   * Amazon VPC CNI plugin version 1.7.7 或更高
   * Kubernetes version 1.17 或更高
   * 基于 EC2 Nitro 的 instances
   * Prefix delegation 功能必须禁用
3.  **配置步骤**：

    a. **在 VPC CNI 中启用 Pod ENI 功能**：

    ```bash
    kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true
    ```

    b. **创建 SecurityGroupPolicy Resource**：

    ```yaml
    apiVersion: vpcresources.k8s.aws/v1beta1
    kind: SecurityGroupPolicy
    metadata:
      name: allow-db-access
      namespace: app
    spec:
      podSelector:
        matchLabels:
          role: db-client
      securityGroups:
        groupIds:
          - sg-0123456789abcdef0
    ```

    c. **向 Service Account 授予 IAM Permissions**：VPC CNI service account 需要以下权限：

    * ec2:CreateNetworkInterface
    * ec2:DeleteNetworkInterface
    * ec2:DescribeNetworkInterfaces
    * ec2:DescribeSecurityGroups
    * ec2:ModifyNetworkInterfaceAttribute
    * ec2:CreateTags
4.  **Pod 配置示例**：

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: db-client
      namespace: app
      labels:
        role: db-client
    spec:
      containers:
      - name: app
        image: amazonlinux:2
        command: ['sleep', '3600']
    ```
5. **工作原理**：
   * 当创建的 pod 具有与 SecurityGroupPolicy 匹配的 labels 时，VPC CNI 会为该 pod 创建 branch ENI。
   * 指定的 security groups 会附加到该 branch ENI。
   * pod 的流量会通过该 branch ENI 路由，并应用附加的 security group 规则。
6.  **验证方法**：

    ```bash
    # Check pod's ENI information
    kubectl describe pod db-client -n app

    # Check SecurityGroupPolicy
    kubectl get securitygrouppolicy -n app

    # Check VPC CNI logs
    kubectl logs -n kube-system -l k8s-app=aws-node
    ```
7. **限制**：
   * 每个节点的 branch ENIs 数量存在限制（因 instance type 而异）。
   * 不能与 prefix delegation 功能一起使用。
   * pod 创建后无法更改 security groups。
   * pod 启动时间可能会略微增加。
8. **使用场景**：
   * 访问通过 security groups 控制访问的 AWS services（如 RDS、ElastiCache）的 pods
   * 需要对特定 pods 的入站/出站流量进行细粒度控制时
   * 需要根据合规要求进行网络隔离的 workloads

Security Groups for Pods 功能是增强 EKS 网络安全的强大工具，但应在考虑额外 ENI 使用带来的资源开销和相关限制后适当使用。

</details>

### 8. 在 Amazon EKS 中使用 Service type LoadBalancer 时，AWS Load Balancer Controller 默认会创建哪种 load balancer，如何更改它？

<details>

<summary>显示答案</summary>

**答案：** 在 Amazon EKS 中使用 Service type LoadBalancer 时，AWS Load Balancer Controller 默认会创建 **Classic Load Balancer (CLB)**。要将其更改为 **Network Load Balancer (NLB)**，需要向 service 添加特定的 **annotation**。

**详细解释：**

1. **默认行为**：创建 `LoadBalancer` type Kubernetes Service 时，AWS cloud controller manager 默认会预置 Classic Load Balancer。
2.  **如何更改为 Network Load Balancer**：向 Service 添加以下 annotation：

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-type: nlb
    ```
3.  **完整 Service 示例（使用 NLB）**：

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: my-service
      annotations:
        service.beta.kubernetes.io/aws-load-balancer-type: nlb
    spec:
      type: LoadBalancer
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: my-app
    ```
4.  **Internal Load Balancer 配置**：默认情况下，创建的 load balancers 是 internet-facing。要配置为 internal load balancer：

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-internal: "true"
    ```
5.  **其他配置选项**：

    a. **Target Type 设置（IP Mode）**：

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    ```

    b. **指定 Security Groups**：

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-security-groups: sg-0123456789abcdef0
    ```

    c. **指定 Subnets**：

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-subnets: subnet-0123456789abcdef0,subnet-0123456789abcdef1
    ```

    d. **禁用 Cross-Zone Load Balancing**：

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "false"
    ```

    e. **启用 Access Logs**：

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-access-log-enabled: "true"
    service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-name: "my-elb-logs"
    service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-prefix: "my-app"
    ```

    f. **SSL Certificate 配置（HTTPS）**：

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: arn:aws:acm:region:account-id:certificate/certificate-id
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
    ```
6.  **使用 AWS Load Balancer Controller**：在较新的 EKS clusters 中，可以使用 AWS Load Balancer Controller 来利用更多功能：

    a. **安装**：

    ```bash
    helm repo add eks https://aws.github.io/eks-charts
    helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
      -n kube-system \
      --set clusterName=my-cluster \
      --set serviceAccount.create=false \
      --set serviceAccount.name=aws-load-balancer-controller
    ```

    b. **通过 Ingress 使用 Application Load Balancer (ALB)**：

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: my-ingress
      annotations:
        kubernetes.io/ingress.class: alb
        alb.ingress.kubernetes.io/scheme: internet-facing
    spec:
      rules:
      - http:
          paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-service
                port:
                  number: 80
    ```
7.  **Load Balancer 类型比较**：

    | Characteristic          | Classic Load Balancer | Network Load Balancer | Application Load Balancer |
    | ----------------------- | --------------------- | --------------------- | ------------------------- |
    | Protocol                | TCP, SSL, HTTP, HTTPS | TCP, UDP, TLS         | HTTP, HTTPS               |
    | Layer                   | 4 & 7                 | 4                     | 7                         |
    | Performance             | Good                  | Very Good             | Good                      |
    | Latency                 | Medium                | Very Low              | Low                       |
    | Static IP               | No                    | Yes                   | No                        |
    | Path-based Routing      | No                    | No                    | Yes                       |
    | WebSockets              | Limited               | Yes                   | Yes                       |
    | Container-based Targets | No                    | Yes (IP mode)         | Yes (IP mode)             |
8. **最佳实践**：
   * 对大多数 HTTP/HTTPS 流量使用 Ingress with ALB
   * 对 TCP/UDP 流量或需要极高吞吐量时使用 NLB
   * 除非存在 legacy applications 或特殊需求，否则使用 NLB 或 ALB，而不是 CLB
   * 在 production environments 中始终启用 cross-zone load balancing

使用 AWS Load Balancer Controller 可以通过 Kubernetes Services 和 Ingress resources 更有效地管理 AWS load balancers，并可通过各种 annotations 进行细粒度配置。

</details>

## 实操题

### 9. 编写一个 NetworkPolicy，使其在 Amazon EKS cluster 中只允许特定 namespace 内的 pods 之间通信，并阻止与其他 namespaces 中 pods 的通信。

<details>

<summary>显示答案</summary>

**答案：** 以下是一个 NetworkPolicy，它只允许特定 namespace 内的 pods 之间通信，并阻止与其他 namespaces 中 pods 的通信：

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: restrict-to-same-namespace
  namespace: app-namespace  # Namespace name to apply
spec:
  podSelector: {}  # Apply to all pods in the namespace
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: app-namespace  # Same namespace
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: app-namespace  # Same namespace
  # Allow DNS lookups (to CoreDNS in kube-system)
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

**详细解释：**

1. **NetworkPolicy 组件说明**：
   * **metadata.namespace**：指定该 policy 将应用到的 namespace。
   * **spec.podSelector: {}**：空的 pod selector 会将该 policy 应用于 namespace 中的所有 pods。
   * **policyTypes**：同时控制 Ingress（入站）和 Egress（出站）流量。
   * **ingress.from.namespaceSelector**：只允许来自同一 namespace 的流量。
   * **egress.to.namespaceSelector**：只允许发往同一 namespace 的流量。
   * **Allow DNS Lookups**：允许到 kube-system namespace 中 CoreDNS 的 DNS 流量。
2.  **实施步骤**：

    a. **创建 Namespace**：

    ```bash
    kubectl create namespace app-namespace
    ```

    b. **为 Namespace 添加 Label**（Kubernetes 1.21+ 中会自动添加）：

    ```bash
    kubectl label namespace app-namespace kubernetes.io/metadata.name=app-namespace
    ```

    c. **应用 NetworkPolicy**：

    ```bash
    kubectl apply -f network-policy.yaml
    ```

    d. **验证 Policy**：

    ```bash
    kubectl describe networkpolicy restrict-to-same-namespace -n app-namespace
    ```
3.  **测试方法**：

    a. **在同一 Namespace 中部署测试 Pod**：

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: test-pod-1
      namespace: app-namespace
    spec:
      containers:
      - name: busybox
        image: busybox
        command: ['sleep', '3600']
    ```

    b. **在不同 Namespace 中部署测试 Pod**：

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: test-pod-2
      namespace: default
    spec:
      containers:
      - name: busybox
        image: busybox
        command: ['sleep', '3600']
    ```

    c. **连接测试**：

    ```bash
    # Test communication within same namespace (should succeed)
    kubectl exec -n app-namespace test-pod-1 -- ping -c 2 $(kubectl get pod test-pod-3 -n app-namespace -o jsonpath='{.status.podIP}')

    # Test communication to other namespace (should fail)
    kubectl exec -n app-namespace test-pod-1 -- ping -c 2 $(kubectl get pod test-pod-2 -n default -o jsonpath='{.status.podIP}')
    ```
4.  **备注和注意事项**：

    a. **验证 NetworkPolicy 支持**：要在 Amazon EKS 中使用 NetworkPolicy，需要支持 network policies 的 CNI plugin：

    ```bash
    # Install Calico
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml

    # Or enable network policy in Amazon VPC CNI
    kubectl set env daemonset aws-node -n kube-system ENABLE_NETWORK_POLICY=true
    ```

    b. **默认拒绝策略**：应用 NetworkPolicy 后，所有未明确允许的流量默认都会被拒绝。

    c. **允许 DNS 访问**：必须允许到 kube-system namespace 中 CoreDNS 的流量，以便 pods 能够执行 DNS 查询。

    d. **System Service 访问**：可能需要根据需要允许访问 Kubernetes API server、monitoring services 等 system services。
5.  **扩展和改进**：

    a. **仅允许特定 Pods 之间通信**：

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: allow-specific-pods
      namespace: app-namespace
    spec:
      podSelector:
        matchLabels:
          app: web
      policyTypes:
      - Ingress
      ingress:
      - from:
        - podSelector:
            matchLabels:
              app: api
    ```

    b. **只允许特定 Ports**：

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: allow-specific-ports
      namespace: app-namespace
    spec:
      podSelector: {}
      policyTypes:
      - Ingress
      ingress:
      - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: app-namespace
        ports:
        - protocol: TCP
          port: 8080
    ```

    c. **允许 External Service 访问**：

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: allow-external-service
      namespace: app-namespace
    spec:
      podSelector:
        matchLabels:
          app: web
      policyTypes:
      - Egress
      egress:
      - to:
        - ipBlock:
            cidr: 10.0.0.0/16  # VPC CIDR
        - ipBlock:
            cidr: 0.0.0.0/0
            except:
            - 10.0.0.0/8
            - 172.16.0.0/12
            - 192.168.0.0/16
    ```

使用 NetworkPolicy 可以在 EKS clusters 中实现细粒度的网络安全控制，这在 multi-tenant environments 或有合规要求的 workloads 中尤其有用。

</details>

## 高级题

### 10. 说明在 Amazon EKS cluster 中使用 VPC CNI 时解决 IP 地址耗尽问题的各种策略，并比较每种方法的优缺点。

<details>

<summary>显示答案</summary>

**答案：** 以下是在 Amazon EKS cluster 中使用 VPC CNI 时解决 IP 地址耗尽问题的各种策略，以及每种方法的优缺点：

### 1. 启用 Prefix Delegation

**描述**：一种为每个 ENI 分配 /28 CIDR blocks（16 个 IP）而不是单个 IP 地址的功能。

**实施方法**：

```bash
kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true
```

**优点**：

* 显著增加每个节点可用的 IP 地址（最多 5 倍）
* 与现有 VPC CNI 功能兼容
* 提高 IP 地址分配速度

**缺点**：

* 仅在基于 EC2 Nitro 的 instances 上受支持
* 不能与 Security Groups for Pods 功能一起使用
* 可能与某些 AWS services 存在兼容性问题

### 2. 启用 Custom Networking Mode

**描述**：从单独的 subnets 分配 pod IP 地址，而不是从节点所在 subnet 分配的功能。

**实施方法**：

```bash
kubectl set env daemonset aws-node -n kube-system AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true
kubectl set env daemonset aws-node -n kube-system ENI_CONFIG_LABEL_DEF=failure-domain.beta.kubernetes.io/zone
```

为每个 availability zone 创建 ENIConfig：

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  securityGroups:
    - sg-0123456789abcdef0
  subnet: subnet-0123456789abcdef0
```

**优点**：

* 防止节点 subnets 的 IP 地址耗尽
* 可以为 pod networking 配置专用 subnet
* 可以使用更大的 CIDR blocks

**缺点**：

* 设置和管理复杂
* 需要额外的 subnets
* 节点替换时需要重新配置 ENIConfig

### 3. 添加 Secondary CIDR Blocks

**描述**：向 VPC 添加 secondary CIDR blocks，并将它们分配给新的 subnets，以扩展 IP 地址空间。

**实施方法**：

1. 通过 AWS console 或 CLI 向 VPC 添加 secondary CIDR block
2. 在 secondary CIDR block 中创建新的 subnets
3. 与 custom networking mode 一起使用

**优点**：

* 大幅扩展现有 VPC 的 IP 地址空间
* 可以在不影响现有基础设施的情况下实施
* 可以使用更大的 CIDR blocks

**缺点**：

* VPC peering、Transit Gateway 等网络配置复杂性增加
* 需要更新 routing tables
* 某些 AWS services 可能不完全支持 secondary CIDRs

### 4. 使用替代 CNI Plugins

**描述**：使用 Calico 或 Cilium 等替代 CNI plugins，而不是 Amazon VPC CNI。

**实施方法**：

```bash
# Calico installation example
kubectl apply -f https://docs.projectcalico.org/manifests/calico-vxlan.yaml

# Disable Amazon VPC CNI
kubectl patch daemonset aws-node -n kube-system -p '{"spec": {"template": {"spec": {"nodeSelector": {"non-existing": "true"}}}}}'
```

**优点**：

* 通过 overlay networks 解决 IP 地址限制
* 更丰富的 network policy 功能
* 与 cloud provider 无关的 networking

**缺点**：

* 缺少与 AWS 原生功能（security groups 等）的集成
* 可能存在性能开销
* 增加管理复杂性
* 不在 AWS support 范围内

### 5. 使用更大的 Subnet CIDRs

**描述**：创建 clusters 时使用更大的 CIDR blocks 的 subnets。

**实施方法**：创建新 clusters 时，使用更大的 CIDR blocks 的 subnets（例如 /16 或 /17）

**优点**：

* 实施简单
* 无需额外配置
* 所有现有 VPC CNI 功能均可使用

**缺点**：

* 难以应用到现有 clusters
* 可能造成 IP 地址空间使用效率低下
* 需要更改 VPC 设计

### 6. 优化 Warm IP 和 Minimum IP 设置

**描述**：通过优化 VPC CNI 的 IP 地址分配行为，提高 IP 地址使用效率。

**实施方法**：

```bash
# Set warm IP target
kubectl set env daemonset aws-node -n kube-system WARM_IP_TARGET=5

# Set minimum IP target
kubectl set env daemonset aws-node -n kube-system MINIMUM_IP_TARGET=10

# Set maximum ENI
kubectl set env daemonset aws-node -n kube-system MAX_ENI=5
```

**优点**：

* 只需简单调整现有设置即可实施
* 无需额外基础设施变更
* 提高 IP 地址分配效率

**缺点**：

* 可能无法完全解决 IP 地址不足问题
* 可能造成 pod 启动延迟
* 效果受 node type 限制

### 7. Hybrid Approach

**描述**：组合使用多种策略。例如，将 prefix delegation 与 custom networking 结合使用，或将部分 workloads 迁移到 Fargate。

**实施方法**：根据 workload 特性选择性应用各种策略

**优点**：

* 针对 workload 特性的优化解决方案
* 提高资源效率
* 可逐步实施

**缺点**：

* 配置和管理复杂性增加
* 需要理解各种 networking models
* 增加故障排查难度

### 8. 使用 Fargate

**描述**：使用 Fargate 代替基于节点的 workloads，将 IP 地址管理委托给 AWS。

**实施方法**：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  labels:
    fargate: "true"

---
apiVersion: eks.amazonaws.com/v1alpha1
kind: FargateProfile
metadata:
  name: my-fargate-profile
  namespace: default
spec:
  selectors:
  - namespace: my-app
```

**优点**：

* 消除 IP 地址管理开销
* 无需管理节点
* Serverless 可扩展性

**缺点**：

* 可能增加成本
* 某些 Kubernetes 功能受限（DaemonSets、privileged containers 等）
* 不适用于所有 workloads

### 推荐方法和最佳实践

1. **评估当前情况**：
   * 分析当前 IP 地址使用情况和预期增长率
   * 理解 workload 特性和需求
   * 审查现有网络配置
2. **短期解决方案**：
   * 启用 prefix delegation（最简单且最有效的方法）
   * 优化 warm IP 和 minimum IP 设置
   * 清理不必要的 pods
3. **中长期解决方案**：
   * 配置 custom networking
   * 添加 secondary CIDR blocks
   * 实施 hybrid approach
4. **监控和告警**：
   * 监控 IP 地址使用情况
   * 设置基于阈值的告警
   * 定期进行容量规划审查
5. **自动化**：
   * 自动化 IP 地址使用情况监控和报告
   * 当 cluster 扩展时自动调整网络配置
   * 建立文档和运维流程

随着 EKS clusters 增长，IP 地址耗尽是常见问题，应根据 cluster 规模和 workload 特性选择或组合适当策略。在大多数情况下，prefix delegation 是最简单且最有效的解决方案，但从长期来看，可能需要更全面的网络设计。

</details>

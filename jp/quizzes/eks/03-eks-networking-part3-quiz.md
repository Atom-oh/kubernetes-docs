# EKS Networking Quiz - Part 3

このクイズでは、service mesh、VPC endpoints、multi-cluster networking、network security など、Amazon EKS における高度な networking 概念についての理解を確認します。

## Multiple Choice Questions

### 1. What is the main architectural change that occurs when implementing a service mesh (e.g., AWS App Mesh, Istio) in Amazon EKS?

A. すべての pod-to-pod 通信が VPC の外部へ routing される B. service-to-service 通信を仲介するため、各 pod に sidecar proxy が追加される C. Kubernetes Service objects が使われなくなる D. すべての network traffic が AWS Transit Gateway を経由して routing される

<details>

<summary>回答を表示</summary>

**回答: B. service-to-service 通信を仲介するため、各 pod に sidecar proxy が追加される**

**説明:** service mesh を実装する際の最も重要なアーキテクチャ上の変更は、各 pod に sidecar proxy（通常は Envoy）が追加されることです。この sidecar proxy は、pod のすべての inbound および outbound traffic を intercept して処理し、service-to-service 通信を仲介します。

**主な機能:**

1. **Sidecar Pattern**: proxy container が各 application container と並んで deployment されます。この proxy がすべての network communication を処理します。
2. **Traffic Flow Changes**:
   * Traditional: Client → Service → Target Pod
   * Service Mesh: Client → Client Sidecar → Service → Target Sidecar → Target Pod
3. **Data Plane and Control Plane**:
   * Data Plane: sidecar proxies の集合
   * Control Plane: proxy configuration を管理し、policies を適用する中央 component
4. **No Application Code Changes**: service mesh の主な利点の 1 つは、application code を変更せずに高度な networking features を追加できることです。

**Service Mesh 実装例 (AWS App Mesh):**

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

**Service Mesh が提供する機能:**

* Traffic management（routing、load balancing、circuit breaking）
* Security（mTLS、authentication、authorization）
* Observability（metrics、logs、distributed tracing）
* Policy enforcement

他の選択肢の問題点:

* **A. すべての pod-to-pod 通信が VPC の外部へ routing される**: Service mesh は通常 cluster 内で動作し、traffic を VPC の外部へ routing しません。
* **C. Kubernetes Service objects が使われなくなる**: Service mesh は Kubernetes Service objects を置き換えるのではなく補完します。
* **D. すべての network traffic が AWS Transit Gateway を経由して routing される**: Service mesh は AWS Transit Gateway とは無関係であり、cluster 内の service-to-service 通信を管理します。

</details>

### 2. What is the main benefit of using VPC endpoints to privately access AWS services in Amazon EKS?

A. すべての AWS services に unlimited bandwidth を提供する B. internet gateway なしで AWS services への private access を可能にする C. AWS service usage costs を 50% 削減する D. すべての AWS services への automatic authentication を提供する

<details>

<summary>回答を表示</summary>

**回答: B. internet gateway なしで AWS services への private access を可能にする**

**説明:** Amazon EKS で VPC endpoints を使用する主な利点は、internet gateway なしで AWS services へ private に access できることです。これにより security が強化され、data transfer costs が削減されます。

**VPC Endpoint Types:**

1. **Interface Endpoints (AWS PrivateLink)**:
   * ほとんどの AWS services への private connectivity を提供します
   * 各 subnet に endpoint network interfaces (ENIs) を作成します
   * Examples: ECR, CloudWatch, SNS, SQS, etc.
2. **Gateway Endpoints**:
   * S3 および DynamoDB への private connectivity を提供します
   * route tables に routes を追加します
   * 追加コストはありません

**EKS 向け VPC Endpoint Configuration Example:**

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

**EKS に VPC Endpoints が必要となる主な AWS Services:**

* Amazon ECR（container images の pull）
* Amazon S3（configuration files、backups など）
* AWS KMS（encryption keys）
* Amazon CloudWatch（logging and monitoring）
* AWS STS（IAM roles の assume）

**VPC Endpoints を使用する利点:**

1. **Enhanced Security**: Traffic が public internet を通過しません
2. **Reduced Network Costs**: AWS services への data transfer costs が減少します
3. **Reduced Latency**: AWS network 内で直接 routing されます
4. **Compliance**: data sovereignty や regulatory requirements を満たします

**Private Subnets における EKS Node Configuration:**

```bash
# Create node group in private subnets with eksctl
eksctl create nodegroup \
  --cluster my-cluster \
  --name private-ng \
  --node-private-networking \
  --vpc-private-subnets subnet-0123456789abcdef0,subnet-0123456789abcdef1
```

他の選択肢の問題点:

* **A. すべての AWS services に unlimited bandwidth を提供する**: VPC endpoints は unlimited bandwidth を提供しません。service や region によって bandwidth limits が存在する場合があります。
* **C. AWS service usage costs を 50% 削減する**: VPC endpoints は data transfer costs を削減できますが、AWS service usage costs を 50% 削減するものではありません。
* **D. すべての AWS services への automatic authentication を提供する**: VPC endpoints は authentication を自動化しません。適切な IAM permissions が引き続き必要です。

</details>

### 3. What is the most effective method for implementing multi-cluster networking in Amazon EKS?

A. inter-cluster communication のために各 cluster で public load balancers を使用する B. AWS Transit Gateway を使用して複数の VPCs を接続し、inter-cluster routing を構成する C. network complexity を減らすためにすべての clusters を単一 VPC に deploy する D. inter-cluster communication のために各 cluster で NAT gateways を使用する

<details>

<summary>回答を表示</summary>

**回答: B. AWS Transit Gateway を使用して複数の VPCs を接続し、inter-cluster routing を構成する**

**説明:** Amazon EKS で multi-cluster networking を実装する最も効果的な方法は、AWS Transit Gateway を使用して複数の VPCs を接続し、inter-cluster routing を構成することです。この approach は scalability、security、management の容易さを提供します。

**AWS Transit Gateway を使用した Multi-Cluster Networking:**

1. **Architecture Overview**:
   * 各 EKS cluster は別々の VPC に deploy されます
   * Transit Gateway がすべての VPCs を接続します
   * Inter-cluster communication は Transit Gateway を通じて routing されます
2.  **Configuration Steps**:

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
3. **CIDR Planning**:
   * 各 cluster/VPC に重複しない CIDR blocks を割り当てます
   * Example: Cluster1: 10.0.0.0/16, Cluster2: 10.1.0.0/16, Cluster3: 10.2.0.0/16

**Multi-Cluster Service Discovery Options:**

1.  **AWS Cloud Map**:

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
2.  **Custom CoreDNS Configuration**:

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

**Multi-Cluster Networking Security Considerations:**

1. **Inter-VPC Traffic Control**:
   * Transit Gateway security groups と routing tables を使用して traffic を制限します
   * 必要な ports と protocols のみを許可します
2.  **Network Policies**:

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

**Multi-Cluster Service Mesh Options:**

1. **Istio Multi-Cluster**:
   * 単一の control plane で複数の clusters を管理します
   * Cross-cluster service discovery and load balancing
2. **AWS App Mesh**:
   * 複数の clusters にまたがる mesh を作成します
   * AWS Cloud Map を通じた service discovery

**Cost Optimization Considerations:**

* Transit Gateway の hourly charges と data processing charges を考慮します
* cross-cluster data transfer を最小化します
* 可能な場合は同じ availability zone 内で通信します

他の選択肢の問題点:

* **A. inter-cluster communication のために各 cluster で public load balancers を使用する**: この方法は security risks を高め、internet data transfer costs を発生させ、latency を増加させます。
* **C. network complexity を減らすためにすべての clusters を単一 VPC に deploy する**: 複数の clusters を単一 VPC に deploy すると、IP address space limitations、security boundaries の欠如、scalability issues につながる可能性があります。
* **D. inter-cluster communication のために各 cluster で NAT gateways を使用する**: NAT gateways は outbound internet traffic 用であり、inter-cluster communication には適していません。

</details>

### 5. What is the most effective method for optimizing pod networking performance in Amazon EKS?

A. すべての pods に host network mode を使用する B. Amazon VPC CNI の prefix delegation feature を有効にする C. すべての pods に NodePort services を使用する D. すべての intra-cluster communication に AWS Global Accelerator を使用する

<details>

<summary>回答を表示</summary>

**回答: B. Amazon VPC CNI の prefix delegation feature を有効にする**

**説明:** Amazon EKS で pod networking performance を最適化する最も効果的な方法は、Amazon VPC CNI の prefix delegation feature を有効にすることです。この feature により、各 node に割り当てられる secondary IP addresses の数が大幅に増え、ENI (Elastic Network Interface) の作成頻度が低下し、networking performance と scalability が向上します。

**Prefix Delegation の仕組み:**

1. **Default VPC CNI vs Prefix Delegation**:
   * Default VPC CNI: 各 ENI に個別の secondary IP addresses を割り当てます
   * Prefix Delegation: 各 ENI に /28 CIDR blocks（16 IPs）を割り当てます
2.  **Enabling Method**:

    ```bash
    # Enable prefix delegation
    kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true

    # Verify prefix delegation
    kubectl describe daemonset aws-node -n kube-system | grep ENABLE_PREFIX_DELEGATION
    ```
3.  **Additional Configuration Options**:

    ```bash
    # Set prefix allocation size (default: /28)
    kubectl set env daemonset aws-node -n kube-system WARM_PREFIX_TARGET=1

    # Threshold for requesting new prefix when available IPs are low
    kubectl set env daemonset aws-node -n kube-system WARM_IP_TARGET=5
    ```

**Prefix Delegation の利点:**

1. **Improved Scalability**:
   * node あたりの最大 pods 数が増加します（通常 110 から 250+ へ）
   * ENI creation calls が少なくなることで API throttling が減少します
2. **Faster Pod Startup Time**:
   * 新しい pods に IP addresses を割り当てるために必要な API calls が減少します
   * large-scale pod deployments の performance が向上します
3. **IP Address Efficiency**:
   * 同じ数の ENIs でより多くの pods を support します
   * IP address exhaustion issues を緩和します

**Maximum Pods Per Instance Type Comparison:**

| Instance Type | Default VPC CNI | Prefix Delegation Enabled |
| ------------- | --------------- | ------------------------- |
| t3.medium     | 17              | 110                       |
| m5.large      | 29              | 110                       |
| c5.xlarge     | 58              | 250                       |
| r5.2xlarge    | 58              | 250                       |

**Configuration Example (ConfigMap):**

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

**Considerations and Limitations:**

1. **Subnet Size**:
   * Prefix delegation には十分に大きな subnets が必要です
   * 最小 /24 CIDR block が推奨されます
2. **Security Group Rules**:
   * prefix delegation により security group rules を簡素化できます
   * 個別 IPs の代わりに CIDR blocks を参照できます
3. **Compatibility**:
   * 一部の legacy EC2 instance types は prefix delegation を support していません
   * Nitro-based instances が推奨されます
4. **IP Address Management**:
   * Prefix delegation は IP addresses をより効率的に使用しますが、適切な CIDR planning は引き続き必要です

**Monitoring and Troubleshooting:**

```bash
# Check IP address allocation per node
kubectl exec -n kube-system aws-node-xxxxx -- curl -s http://localhost:61679/v1/enis | jq

# Check prefix delegation status
kubectl logs -n kube-system aws-node-xxxxx | grep -i prefix
```

他の選択肢の問題点:

* **A. すべての pods に host network mode を使用する**: Host network mode では pods が node の network namespace を共有するため、port conflicts が発生し、network isolation が失われます。
* **C. すべての pods に NodePort services を使用する**: NodePort は service exposure mechanism であり、pod networking performance optimization とは無関係です。
* **D. すべての intra-cluster communication に AWS Global Accelerator を使用する**: AWS Global Accelerator は global traffic management 用であり、intra-cluster communication optimization には適していません。

</details>

## Short Answer Questions

### 7. What is the most commonly used open-source proxy for sidecar proxies when implementing a service mesh in Amazon EKS?

<details>

<summary>回答を表示</summary>

**回答:** Envoy

**詳細な説明:**

Amazon EKS で service mesh を実装する際に最も一般的に使用される sidecar proxy は Envoy です。Envoy は高 performance な C++ ベースの proxy で、主要な service mesh implementations（Istio、AWS App Mesh、Consul Connect など）のほとんどで data plane proxy として使用されます。

**Envoy の主な機能:**

1. **High-Performance Architecture**:
   * 低 latency と高 throughput のために C++ で記述されています
   * event-driven、asynchronous networking model
2. **Rich Traffic Management Features**:
   * Load balancing（round robin、weighted、least request など）
   * Circuit breaking and outlier detection
   * Retry and timeout policies
   * Traffic splitting and mirroring
3. **Observability**:
   * 詳細な metrics and statistics
   * Distributed tracing integration（Zipkin、Jaeger など）
   * Access logging
4. **Security Features**:
   * TLS/mTLS termination
   * Authentication and authorization
   * Rate limiting

**Service Mesh における Envoy Deployment:**

1.  **Sidecar Pattern**:

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
2. **Automatic Injection**:
   * Istio: `sidecar.istio.io/inject: "true"` annotation
   * AWS App Mesh: `appmesh.k8s.aws/sidecarInjectorWebhook: enabled` label

**Envoy Configuration Example:**

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

**Service Mesh 別の Envoy Integration:**

1. **Istio**:
   * Envoy を sidecar proxy として使用します
   * istiod が Envoy configuration を動的に管理します
   * Pilot、Mixer、Citadel などの components が Envoy と統合されます
2. **AWS App Mesh**:
   * AWS App Mesh controller が Envoy sidecar を inject します
   * service discovery のために AWS Cloud Map と統合します
   * Envoy Management Service (EMS) が Envoy configuration を管理します
3. **Consul Connect**:
   * Envoy を data plane proxy として使用します
   * Consul が service discovery と configuration management を提供します

**Envoy Monitoring and Debugging:**

```bash
# Port forward Envoy admin interface
kubectl port-forward <pod-name> 19000:19000

# Check configuration and stats
curl localhost:19000/config_dump
curl localhost:19000/stats

# Check cluster status
curl localhost:19000/clusters
```

**Performance Optimization Considerations:**

* Resource allocation: Envoy に十分な CPU と memory を割り当てます
* Connection pooling: performance 向上のため upstream connection pooling を構成します
* Buffer size: memory usage optimization のため適切な buffer sizes を設定します
* Filter chain: overhead を最小化するため必要な filters のみを有効にします

Envoy は modern service mesh architecture の中核 component であり、microservice communication を secure、reliable、observable にするうえで重要な役割を果たします。

</details>

### 8. What is the name of the Kubernetes add-on responsible for internal DNS resolution in Amazon EKS clusters?

<details>

<summary>回答を表示</summary>

**回答:** CoreDNS

**詳細な説明:**

Amazon EKS clusters における internal DNS resolution を担当する Kubernetes add-on は CoreDNS です。CoreDNS は Kubernetes clusters 内の service discovery のための DNS server として機能し、pods と services の name resolution を処理します。

**CoreDNS の主な機能:**

1. **Service Discovery**:
   * `<service-name>.<namespace>.svc.cluster.local` 形式の DNS names を解決します
   * pod IP addresses の reverse DNS lookups を support します
2. **Plugin Architecture**:
   * さまざまな plugins を通じて functionality を拡張します
   * Caching、metrics、logging、error handling など
3. **Configuration Flexibility**:
   * Corefile による declarative configuration
   * dynamic reload を support します

**EKS における CoreDNS Deployment:**

1. **Default Deployment Configuration**:
   * EKS cluster 作成時に自動的に deploy されます
   * kube-system namespace で実行されます
   * 通常 2 つ以上の replicas で deploy されます
2.  **Verification**:

    ```bash
    # Check CoreDNS pods
    kubectl get pods -n kube-system -l k8s-app=kube-dns

    # Check CoreDNS version
    kubectl describe deployment coredns -n kube-system | grep Image
    ```

**CoreDNS Configuration (Corefile):**

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

**主な Plugin Descriptions:**

1. **errors**: errors を logs に記録します
2. **health**: health check endpoint を提供します
3. **ready**: readiness check endpoint を提供します
4. **kubernetes**: Kubernetes service discovery を処理します
5. **prometheus**: Prometheus metrics を公開します
6. **forward**: external DNS queries を upstream DNS servers に forward します
7. **cache**: DNS responses を cache します
8. **loop**: DNS loops を検出して防止します
9. **reload**: Corefile changes に応じて自動的に reload します
10. **loadbalance**: 複数の A/AAAA records 間で load balancing します

**Custom Configuration Examples:**

1.  **Use Specific DNS Server for External Domain**:

    ```
    example.com {
        forward . 10.0.0.1
    }
    ```
2.  **Stub Domain Configuration**:

    ```
    internal.corp {
        file /etc/coredns/internal.db
    }
    ```
3.  **Conditional Forwarding**:

    ```
    . {
        forward . 8.8.8.8 8.8.4.4 {
            policy sequential
        }
    }
    ```

**Performance Optimization and Scaling:**

1.  **Auto Scaling**:

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
2.  **Resource Allocation Optimization**:

    ```yaml
    resources:
      limits:
        memory: 170Mi
      requests:
        cpu: 100m
        memory: 70Mi
    ```
3.  **Cache Tuning**:

    ```
    cache {
        success 10000
        denial 1000
        prefetch 10 10% 2m
    }
    ```

**Troubleshooting:**

1.  **DNS Resolution Test**:

    ```bash
    # Create test pod
    kubectl run dnsutils --image=gcr.io/kubernetes-e2e-test-images/dnsutils:1.3 -- sleep 3600

    # Test DNS lookup
    kubectl exec -it dnsutils -- nslookup kubernetes.default
    ```
2.  **Check CoreDNS Logs**:

    ```bash
    kubectl logs -n kube-system -l k8s-app=kube-dns
    ```
3.  **Check DNS Policy**:

    ```bash
    kubectl get pods <pod-name> -o jsonpath='{.spec.dnsPolicy}'
    ```

CoreDNS は EKS clusters の重要な component であり、microservices architecture に core service discovery functionality を提供します。適切な configuration と monitoring によって reliable な DNS service を確保することが不可欠です。

</details>

## Hands-on Questions

### 10. Explain how to implement a service mesh (e.g., AWS App Mesh) in an Amazon EKS cluster to secure and monitor microservice communication. Include implementation steps, key components, and monitoring methods.

<details>

<summary>回答を表示</summary>

**回答:**

Amazon EKS cluster で microservice communication を secure にし、monitor するために AWS App Mesh を実装する方法は次のとおりです。

### 1. AWS App Mesh Implementation Steps

#### 1.1. Set Up Prerequisites

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

#### 1.2. Install App Mesh Controller

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

#### 1.3. Create Mesh

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

#### 1.4. Set Up Application Namespace

```bash
# Create and label application namespace
kubectl create ns app-namespace
kubectl label namespace app-namespace mesh=my-mesh
kubectl label namespace app-namespace appmesh.k8s.aws/sidecarInjectorWebhook=enabled
```

#### 1.5. Define Virtual Nodes and Services

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

#### 1.6. Deploy Application

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

### 2. Secure Communication with mTLS Configuration

#### 2.1. Set Up AWS Certificate Manager Private CA

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

#### 2.2. Add TLS Configuration

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

### 3. Set Up Monitoring and Observability

#### 3.1. AWS X-Ray Integration

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

#### 3.2. Amazon CloudWatch Integration

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

#### 3.3. Prometheus and Grafana Setup

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

### 4. Configure Traffic Management and Advanced Features

#### 4.1. Canary Deployment Configuration

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

#### 4.2. Circuit Breaker Configuration

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

#### 4.3. Retry Policy Configuration

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

### 5. Monitoring and Troubleshooting

#### 5.1. Check Envoy Proxy Logs

```bash
# Check Envoy sidecar logs for specific pod
kubectl logs <pod-name> -c envoy -n app-namespace

# Stream all Envoy logs
kubectl logs -f -l app=service-a -c envoy -n app-namespace
```

#### 5.2. Access Envoy Admin Interface

```bash
# Set up port forwarding
kubectl port-forward <pod-name> -n app-namespace 9901:9901

# Access in browser
# http://localhost:9901/
```

#### 5.3. Check X-Ray Traces

service maps と traces を表示するには、AWS Management Console の X-Ray service に移動します。

#### 5.4. Create CloudWatch Dashboard

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

### 6. Best Practices and Considerations

#### 6.1. Resource Requirements

* Envoy sidecar が各 pod に追加されるため、node resources を計画します
* 通常、各 Envoy proxy に 100-200m CPU と 128-256Mi memory を割り当てます

#### 6.2. Gradual Implementation Strategy

1. **Phased Approach**:
   * non-business-critical services から開始します
   * traffic mirroring で impact を評価します
   * successful validation の後に段階的に拡大します
2. **mTLS Implementation**:
   * PERMISSIVE mode から開始します
   * すべての services が compatible であることを確認します
   * STRICT mode に切り替えます

#### 6.3. Performance Optimization

* Envoy resource limits を調整します
* 適切な health check intervals を設定します
* 不要な logging and tracing を最小化します

#### 6.4. Security Hardening

* least privilege IAM policies を使用します
* 定期的な certificate rotation
* network policies による defense in depth を実装します

AWS App Mesh は、EKS clusters における microservice communication の secure 化と monitoring のための強力な service mesh solution を提供します。適切な configuration と monitoring によって、application reliability、security、observability を大幅に向上できます。

</details>

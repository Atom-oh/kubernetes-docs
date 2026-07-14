# EKS Networking クイズ - Part 1

このクイズでは、Amazon EKS、VPC CNI、Network Policy、Service Discovery における基本的な Networking の概念についての理解を確認します。EKS cluster の Networking アーキテクチャとコンポーネントに焦点を当てています。

## 選択式問題

### 1. Amazon EKS で使用されるデフォルトの CNI (Container Network Interface) plugin は何ですか？

A. Calico B. Flannel C. Amazon VPC CNI D. Weave Net

<details>

<summary>回答を表示</summary>

**回答: C. Amazon VPC CNI**

**解説:** Amazon EKS はデフォルトで Amazon VPC CNI plugin を使用します。この plugin は Kubernetes pod に VPC IP address を割り当て、AWS VPC networking のネイティブ機能を使用して pod 間の通信を可能にします。

**主な機能:**

1. **Native VPC Networking**: 各 pod は VPC 内で一意の IP address を受け取ります。これにより、pod は VPC 内の他の service と直接通信できます。
2. **Secondary IP Address Assignment**: Secondary IP address が各 node の Elastic Network Interface (ENI) に割り当てられ、pod に提供されます。
3. **Security Group Integration**: AWS security group を pod level で適用でき、きめ細かな network security control が可能になります。
4. **Performance**: Overlay network を使用しないことで network performance が向上します。
5. **AWS Service Integration**: AWS Load Balancer Controller や AWS App Mesh などの他の AWS service とシームレスに統合します。

**設定例:**

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

Amazon VPC CNI は open source で、GitHub で管理されています。必要に応じて Calico や Cilium などの他の CNI plugin に置き換えることもできますが、Amazon VPC CNI は EKS のデフォルトオプションであり、AWS によって公式にサポートされています。

</details>

### 2. VPC CNI は Amazon EKS でどのように IP address を pod に割り当てますか？

A. 各 pod に個別の Elastic Network Interface (ENI) を割り当てる B. node の Elastic Network Interface (ENI) に secondary IP address を割り当て、それらを pod に提供する C. overlay network を使用して virtual IP address を割り当てる D. 各 pod に個別の VPC subnet を割り当てる

<details>

<summary>回答を表示</summary>

**回答: B. node の Elastic Network Interface (ENI) に secondary IP address を割り当て、それらを pod に提供する**

**解説:** Amazon VPC CNI は、node の Elastic Network Interface (ENI) に secondary IP address を割り当て、それらの IP address を pod に提供することで動作します。この方式は「IP-per-Pod」モデルとも呼ばれます。

**仕組み:**

1. **ENI Allocation**: 各 EC2 instance (node) は 1 つ以上の ENI を持つことができます。ENI ごとに割り当て可能な IP address の数は instance type によって決まります。
2. **IP Address Pool Management**: VPC CNI の `aws-node` DaemonSet が各 node で実行され、利用可能な IP address pool を管理します。
3. **IP Address Assignment**: pod が作成されると、CNI は pool から IP address を割り当て、それを pod の network namespace に接続します。
4. **IP Address Reclamation**: pod が終了すると、CNI は IP address を回収し、pool に戻します。

**設定例:**

```bash
# Maximum pods per node calculation
Maximum pods = (Number of ENIs × (IP addresses per ENI - 1)) + 2

# For m5.large instance
# Number of ENIs: 3, IP addresses per ENI: 10
Maximum pods = (3 × (10 - 1)) + 2 = 29
```

**主な考慮事項:**

1. **IP Address Limit**: node ごとに実行できる pod の最大数は、instance type に応じて制限されます。
2. **Warm IPs**: VPC CNI は `WARM_IP_TARGET` 設定を通じて一定数の IP address を事前に割り当て、pod の起動時間を短縮できます。
3. **Prefix Delegation**: VPC CNI の新しい version は prefix delegation 機能をサポートしており、各 ENI に /28 CIDR block (16 IPs) を割り当てて IP address density を高めます。
4. **Security Groups**: `ENABLE_POD_ENI` 設定を有効にすると、特定の pod に対して個別の security group を設定できます (Security Groups for Pods 機能)。

他の選択肢の問題点:

* **A**: 一般的に、各 pod に個別の ENI は割り当てられません。これは EC2 instance ごとの ENI limit により非効率です。
* **C**: VPC CNI は overlay network を使用しません。これは Flannel や Weave Net など他の CNI plugin の特徴です。
* **D**: 各 pod に個別の VPC subnet を割り当てることは、AWS VPC アーキテクチャではできません。

</details>

### 3. Amazon EKS における pod-to-pod communication が VPC の外に出ず、VPC 内で直接行われるのはなぜですか？

A. すべての pod が同じ subnet に配置されているため B. pod が node の network namespace を共有しているため C. pod に VPC IP address が直接割り当てられているため D. pod-to-pod communication は常に service mesh を経由するため

<details>

<summary>回答を表示</summary>

**回答: C. pod に VPC IP address が直接割り当てられているため**

**解説:** Amazon EKS における pod-to-pod communication が VPC の外に出ず、VPC 内で直接行われる主な理由は、Amazon VPC CNI plugin が各 pod に VPC IP address を直接割り当てるためです。

**主な仕組み:**

1. **VPC IP Address Assignment**: 各 pod は VPC subnet から一意の IP address を受け取ります。この IP address は node の ENI に接続された secondary IP address です。
2. **Direct Routing**: pod は VPC IP address を持つため、VPC 内の他の resource (他の pod、EC2 instance、RDS database など) と直接通信できます。
3. **VPC Routing Tables**: pod-to-pod communication は VPC routing table に従い、外に出ることなく同じ VPC 内で直接 route されます。

**利点:**

1. **Network Performance**: overlay network や NAT を使用しないことで、latency が低減され throughput が向上します。
2. **Security**: VPC security group や network ACL など、既存の AWS network security mechanism を活用できます。
3. **Visibility**: VPC Flow Logs を通じて pod-to-pod traffic を監視および分析できます。
4. **AWS Service Integration**: pod は VPC IP address を持つため、VPC endpoint や PrivateLink などの AWS service とシームレスに統合します。

**例のシナリオ:**

Pod A (IP: 10.0.1.23) が Pod B (IP: 10.0.2.45) と通信する場合:

1. Pod A は Pod B の IP address (10.0.2.45) に直接 packet を送信します。
2. packet は VPC routing table に従って route されます。
3. packet は VPC 内で直接 Pod B に到達します。
4. このプロセス全体を通じて、packet は VPC の外に出ません。

他の選択肢の問題点:

* **A**: pod は複数の subnet に分散できます。また、異なる subnet の pod でも VPC 内で直接通信できます。
* **B**: pod は node の network namespace を共有しません。各 pod は独自の network namespace を持ちます。
* **D**: pod-to-pod communication は常に service mesh を経由するわけではありません。Service mesh は任意の追加 layer です。

</details>

### 4. Amazon EKS で pod への inbound および outbound traffic を制御するために最も適切な Kubernetes resource は何ですか？

A. Service B. Ingress C. NetworkPolicy D. SecurityContext

<details>

<summary>回答を表示</summary>

**回答: C. NetworkPolicy**

**解説:** Amazon EKS で pod への inbound および outbound traffic を制御するために最も適切な Kubernetes resource は NetworkPolicy です。NetworkPolicy は Kubernetes の network security mechanism であり、pod 間の通信をきめ細かく制御できます。

**NetworkPolicy の主な機能:**

1. **Selective Application**: label selector を使用して特定の pod に policy を適用できます。
2. **Inbound and Outbound Rules**: ingress (inbound) と egress (outbound) traffic の両方を制御できます。
3. **Various Selectors**: namespace、label、IP CIDR block、port などに基づいて traffic を filtering できます。
4. **Default Deny Policy**: 明示的に許可されていない traffic はデフォルトで拒否されます。

**NetworkPolicy の例:**

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

**EKS における NetworkPolicy の実装:**

Amazon EKS で NetworkPolicy を使用するには、network policy をサポートする CNI plugin が必要です。デフォルトの Amazon VPC CNI は network policy を直接サポートしないため、追加設定が必要です:

1.  **Calico のインストール**: Calico は EKS で NetworkPolicy を実装する最も一般的な方法です。

    ```bash
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml
    ```
2.  **Amazon VPC CNI で Network Policy を有効化**: Amazon VPC CNI の新しい version は network policy support を提供します。

    ```bash
    kubectl set env daemonset aws-node -n kube-system ENABLE_NETWORK_POLICY=true
    ```

他の選択肢の問題点:

* **A. Service**: Service は pod への network access を提供しますが、traffic control や filtering の機能はありません。
* **B. Ingress**: Ingress は HTTP/HTTPS traffic を cluster 内の service に route するために使用されますが、一般的な network policy は定義しません。
* **D. SecurityContext**: SecurityContext は pod または container level の security setting を定義しますが、network traffic control には関係しません。

</details>

### 5. EKS cluster 内の service discovery に使用される DNS service は何ですか？

A. Amazon Route 53 B. CoreDNS C. kube-dns D. AWS Cloud Map

<details>

<summary>回答を表示</summary>

**回答: B. CoreDNS**

**解説:** Amazon EKS cluster 内の service discovery にデフォルトで使用される DNS service は CoreDNS です。CoreDNS は、Kubernetes cluster 内で DNS-based service discovery を提供する柔軟で拡張可能な DNS server です。

**CoreDNS の主な機能:**

1. **Kubernetes Integration**: CoreDNS は Kubernetes API と統合し、service と pod の DNS record を自動的に作成します。
2. **Plugin Architecture**: CoreDNS はさまざまな plugin を通じて機能を拡張できます。
3. **High Availability**: EKS では、CoreDNS は通常、high availability を確保するために複数の replica で deploy されます。
4. **Configurability**: Corefile を通じてさまざまな DNS setting を設定できます。

**EKS における CoreDNS Deployment:**

EKS cluster を作成すると、CoreDNS は自動的に deploy されます。CoreDNS は `kube-system` namespace 内の Deployment として実行されます:

```bash
kubectl get deployment coredns -n kube-system
```

**CoreDNS 設定例:**

CoreDNS の設定は ConfigMap に保存されます:

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

**Service Discovery の仕組み:**

1. **Service Creation**: Kubernetes Service が作成されると、CoreDNS は DNS record を自動的に作成します。
2. **DNS Name Format**:
   * Service: `<service-name>.<namespace>.svc.cluster.local`
   * Pod: `<pod-ip>.<namespace>.pod.cluster.local`
3. **DNS Lookup**: cluster 内の pod が service name で DNS lookup を行うと、CoreDNS はその service の ClusterIP を返します。

**例:**

```bash
# If my-service service exists in the default namespace
nslookup my-service.default.svc.cluster.local

# Result
Name:   my-service.default.svc.cluster.local
Address: 10.100.43.150  # Service's ClusterIP
```

**CoreDNS のスケーリングと最適化:**

EKS では、CoreDNS は cluster size に応じて自動的に scale しないため、大規模 cluster では手動で scale する必要がある場合があります:

```bash
kubectl scale deployment coredns --replicas=4 -n kube-system
```

また、cache setting を調整することで performance を最適化できます:

```yaml
cache {
    success 10000
    denial 1000
    prefetch 10 10m 20%
}
```

他の選択肢の問題点:

* **A. Amazon Route 53**: Route 53 は AWS の DNS service ですが、EKS cluster 内の service discovery にはデフォルトでは使用されません。
* **C. kube-dns**: kube-dns は以前の Kubernetes version で使用されていましたが、EKS では CoreDNS に置き換えられています。
* **D. AWS Cloud Map**: Cloud Map は AWS の service discovery service ですが、EKS cluster 内のデフォルト DNS service としては使用されません。

</details>

## 短答問題

### 6. Amazon EKS cluster において node ごとの pod 最大数を制限する主な要因は何で、それを増やすにはどのような方法がありますか？

<details>

<summary>回答を表示</summary>

**回答:** Amazon EKS cluster において node ごとの pod 最大数を制限する主な要因は、**EC2 instance type ごとの ENI (Elastic Network Interface) 数と ENI ごとに割り当て可能な IP address 数**です。これを増やす主な方法は、**Prefix Delegation 機能を有効にすること**です。

**詳細な解説:**

1.  **Maximum Pods Per Node の計算式**:

    ```
    Maximum pods = (Number of ENIs × (IP addresses per ENI - 1)) + 2
    ```

    * 各 ENI の最初の IP address は node 自身のために予約されます。
    * 追加の 2 つは kube-proxy と aws-node pod のためです。
2. **Instance Type ごとの制限例**:
   * **t3.small**: (3 ENIs × (4 IPs - 1)) + 2 = 11 pods
   * **m5.large**: (3 ENIs × (10 IPs - 1)) + 2 = 29 pods
   * **c5.4xlarge**: (8 ENIs × (30 IPs - 1)) + 2 = 234 pods
3.  **Prefix Delegation による拡張**: Prefix delegation は、各 ENI に個別の IP address ではなく /28 CIDR block (16 IPs) を割り当てる機能です。

    **有効化方法**:

    ```bash
    # Modify ConfigMap
    kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true

    # Optionally set prefix allocation mode
    kubectl set env daemonset aws-node -n kube-system WARM_PREFIX_TARGET=1
    ```

    **Prefix Delegation 有効化後の計算式**:

    ```
    Maximum pods = (Number of ENIs × (Prefixes per ENI × IPs per prefix - 1)) + 2
    ```

    例: prefix delegation を有効にした m5.large

    * prefix delegation なし: 29 pods
    * prefix delegation 有効: (3 ENIs × (1 prefix × 16 IPs - 1)) + 2 = 47 pods
4. **Maximum Pod Count を増やすその他の方法**:
   * **より大きい Instance Type を使用**: より多くの ENI と IP address をサポートする instance type に変更します
   * **Custom CNI Configuration**: `--max-pods` flag を使用して kubelet configuration を調整します (非推奨)
   * **Alternative CNI Plugins を使用**: Calico、Cilium など overlay network を使用する CNI plugin に切り替えます
5. **考慮事項**:
   * Prefix delegation は EC2 Nitro-based instance でのみサポートされます。
   * Prefix delegation を有効にすると、SecurityGroupsForPods 機能は使用できません。
   * node ごとの pod 数が増えると、node resource (CPU、memory) の競合が発生する可能性があるため、適切な instance size の選択が重要です。
6.  **Monitoring and Optimization**:

    ```bash
    # Check current IP address usage
    kubectl exec -n kube-system ds/aws-node -- curl -s http://localhost:61679/v1/enis | jq

    # Check prefix delegation status
    kubectl describe daemonset aws-node -n kube-system | grep PREFIX
    ```

Prefix delegation を有効化すると node ごとの最大 pod 数を大幅に増やせますが、cluster の要件と workload の特性に基づいて適切な設定を選択することが重要です。

</details>

### 7. Amazon EKS で特定の AWS security group を pod に割り当てられる機能の名前は何で、どのように設定しますか？

<details>

<summary>回答を表示</summary>

**回答:** Amazon EKS で特定の AWS security group を pod に割り当てられる機能の名前は **Security Groups for Pods** または **Pod ENI (Elastic Network Interface)** です。この機能は、VPC CNI で **ENABLE\_POD\_ENI** option を有効にすることで設定できます。

**詳細な解説:**

1. **Security Groups for Pods の概要**: この機能は、特定の pod 用に個別の ENI (trunk ENI とも呼ばれます) を作成し、この ENI に security group を attach することで、pod level のきめ細かな network security control を可能にします。
2. **前提条件**:
   * Amazon VPC CNI plugin version 1.7.7 以上
   * Kubernetes version 1.17 以上
   * EC2 Nitro-based instance
   * Prefix delegation 機能が無効であること
3.  **設定手順**:

    a. **VPC CNI で Pod ENI 機能を有効化**:

    ```bash
    kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true
    ```

    b. **SecurityGroupPolicy Resource を作成**:

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

    c. **Service Account に IAM Permission を付与**: VPC CNI service account には以下の permission が必要です:

    * ec2:CreateNetworkInterface
    * ec2:DeleteNetworkInterface
    * ec2:DescribeNetworkInterfaces
    * ec2:DescribeSecurityGroups
    * ec2:ModifyNetworkInterfaceAttribute
    * ec2:CreateTags
4.  **Pod 設定例**:

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
5. **仕組み**:
   * SecurityGroupPolicy に一致する label を持つ pod が作成されると、VPC CNI はその pod 用の branch ENI を作成します。
   * 指定された security group がこの branch ENI に attach されます。
   * pod の traffic はこの branch ENI を通じて route され、attach された security group rule が適用されます。
6.  **検証方法**:

    ```bash
    # Check pod's ENI information
    kubectl describe pod db-client -n app

    # Check SecurityGroupPolicy
    kubectl get securitygrouppolicy -n app

    # Check VPC CNI logs
    kubectl logs -n kube-system -l k8s-app=aws-node
    ```
7. **制限事項**:
   * node ごとの branch ENI 数には制限があります (instance type によって異なります)。
   * prefix delegation 機能と併用できません。
   * pod 作成後に security group を変更することはできません。
   * pod の起動時間がわずかに増加する可能性があります。
8. **ユースケース**:
   * RDS、ElastiCache など、security group で access を制御する AWS service に access する pod
   * 特定の pod の inbound/outbound traffic をきめ細かく制御する必要がある場合
   * 規制要件に従った network isolation が必要な workload

Security Groups for Pods 機能は EKS networking security を強化する強力な tool ですが、追加の ENI 使用による resource overhead と制限を考慮して適切に使用する必要があります。

</details>

### 8. Amazon EKS で Service type LoadBalancer を使用する場合、AWS Load Balancer Controller はデフォルトでどの type の load balancer を作成し、どのように変更しますか？

<details>

<summary>回答を表示</summary>

**回答:** Amazon EKS で Service type LoadBalancer を使用する場合、AWS Load Balancer Controller はデフォルトで **Classic Load Balancer (CLB)** を作成します。これを **Network Load Balancer (NLB)** に変更するには、Service に特定の **annotation** を追加する必要があります。

**詳細な解説:**

1. **デフォルト動作**: `LoadBalancer` type の Kubernetes Service を作成すると、AWS cloud controller manager はデフォルトで Classic Load Balancer を provision します。
2.  **Network Load Balancer に変更する方法**: Service に以下の annotation を追加します:

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-type: nlb
    ```
3.  **完全な Service 例 (NLB を使用)**:

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
4.  **Internal Load Balancer 設定**: デフォルトでは、作成される load balancer は internet-facing です。internal load balancer として設定するには:

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-internal: "true"
    ```
5.  **追加の設定オプション**:

    a. **Target Type 設定 (IP Mode)**:

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    ```

    b. **Security Groups を指定**:

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-security-groups: sg-0123456789abcdef0
    ```

    c. **Subnets を指定**:

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-subnets: subnet-0123456789abcdef0,subnet-0123456789abcdef1
    ```

    d. **Cross-Zone Load Balancing を無効化**:

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "false"
    ```

    e. **Access Logs を有効化**:

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-access-log-enabled: "true"
    service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-name: "my-elb-logs"
    service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-prefix: "my-app"
    ```

    f. **SSL Certificate 設定 (HTTPS)**:

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: arn:aws:acm:region:account-id:certificate/certificate-id
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
    ```
6.  **AWS Load Balancer Controller の使用**: 新しい EKS cluster では、AWS Load Balancer Controller を使用してより多くの機能を活用できます:

    a. **インストール**:

    ```bash
    helm repo add eks https://aws.github.io/eks-charts
    helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
      -n kube-system \
      --set clusterName=my-cluster \
      --set serviceAccount.create=false \
      --set serviceAccount.name=aws-load-balancer-controller
    ```

    b. **Ingress で Application Load Balancer (ALB) を使用**:

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
7.  **Load Balancer Type Comparison**:

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
8. **Best Practices**:
   * ほとんどの HTTP/HTTPS traffic には ALB と Ingress を使用します
   * TCP/UDP traffic または非常に高い throughput が必要な場合は NLB を使用します
   * legacy application や特別な要件がない限り、CLB ではなく NLB または ALB を使用します
   * production environment では常に cross-zone load balancing を有効にします

AWS Load Balancer Controller を使用すると、Kubernetes Service と Ingress resource を通じて AWS load balancer をより効果的に管理でき、さまざまな annotation によってきめ細かな設定が可能になります。

</details>

## ハンズオン問題

### 9. Amazon EKS cluster で、特定の namespace 内の pod 間の通信のみを許可し、他の namespace の pod との通信をブロックする NetworkPolicy を作成してください。

<details>

<summary>回答を表示</summary>

**回答:** 以下は、特定の namespace 内の pod 間の通信のみを許可し、他の namespace の pod との通信をブロックする NetworkPolicy です:

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

**詳細な解説:**

1. **NetworkPolicy コンポーネントの解説**:
   * **metadata.namespace**: この policy が適用される namespace を指定します。
   * **spec.podSelector: {}**: 空の pod selector は、namespace 内のすべての pod に policy を適用します。
   * **policyTypes**: Ingress (inbound) と Egress (outbound) traffic の両方を制御します。
   * **ingress.from.namespaceSelector**: 同じ namespace からの traffic のみを許可します。
   * **egress.to.namespaceSelector**: 同じ namespace への traffic のみを許可します。
   * **Allow DNS Lookups**: kube-system namespace 内の CoreDNS への DNS traffic を許可します。
2.  **実装手順**:

    a. **Namespace を作成**:

    ```bash
    kubectl create namespace app-namespace
    ```

    b. **Namespace に Label を追加** (Kubernetes 1.21+ では自動的に追加されます):

    ```bash
    kubectl label namespace app-namespace kubernetes.io/metadata.name=app-namespace
    ```

    c. **NetworkPolicy を適用**:

    ```bash
    kubectl apply -f network-policy.yaml
    ```

    d. **Policy を検証**:

    ```bash
    kubectl describe networkpolicy restrict-to-same-namespace -n app-namespace
    ```
3.  **テスト方法**:

    a. **同じ Namespace に Test Pod を Deploy**:

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

    b. **異なる Namespace に Test Pod を Deploy**:

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

    c. **接続テスト**:

    ```bash
    # Test communication within same namespace (should succeed)
    kubectl exec -n app-namespace test-pod-1 -- ping -c 2 $(kubectl get pod test-pod-3 -n app-namespace -o jsonpath='{.status.podIP}')

    # Test communication to other namespace (should fail)
    kubectl exec -n app-namespace test-pod-1 -- ping -c 2 $(kubectl get pod test-pod-2 -n default -o jsonpath='{.status.podIP}')
    ```
4.  **注意事項と考慮事項**:

    a. **NetworkPolicy Support を確認**: Amazon EKS で NetworkPolicy を使用するには、network policy をサポートする CNI plugin が必要です:

    ```bash
    # Install Calico
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml

    # Or enable network policy in Amazon VPC CNI
    kubectl set env daemonset aws-node -n kube-system ENABLE_NETWORK_POLICY=true
    ```

    b. **Default Deny Policy**: NetworkPolicy が適用されると、明示的に許可されていないすべての traffic はデフォルトで拒否されます。

    c. **DNS Access を許可**: pod が DNS lookup を実行できるように、kube-system namespace 内の CoreDNS への traffic を許可する必要があります。

    d. **System Service Access**: Kubernetes API server、monitoring service などの system service への access を必要に応じて許可する必要がある場合があります。
5.  **拡張と改善**:

    a. **特定の Pod 間の通信のみを許可**:

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

    b. **特定の Port のみを許可**:

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

    c. **External Service Access を許可**:

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

NetworkPolicy を使用すると、EKS cluster 内で fine-grained network security control を実装できます。これは特に multi-tenant environment や規制要件のある workload で有用です。

</details>

## 高度な問題

### 10. Amazon EKS cluster で VPC CNI による IP address exhaustion 問題を解決するためのさまざまな戦略を説明し、それぞれの approach の利点と欠点を比較してください。

<details>

<summary>回答を表示</summary>

**回答:** 以下は、Amazon EKS cluster で VPC CNI による IP address exhaustion 問題を解決するためのさまざまな戦略と、それぞれの approach の利点および欠点です:

### 1. Prefix Delegation を有効化

**説明**: 各 ENI に個別の IP address ではなく /28 CIDR block (16 IPs) を割り当てる機能です。

**実装方法**:

```bash
kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true
```

**利点**:

* node ごとの利用可能な IP address を大幅に増やします (最大 5 倍)
* 既存の VPC CNI 機能と互換性があります
* IP address allocation speed が向上します

**欠点**:

* EC2 Nitro-based instance でのみサポートされます
* Security Groups for Pods 機能と併用できません
* 一部の AWS service で互換性の問題が発生する可能性があります

### 2. Custom Networking Mode を有効化

**説明**: node が配置されている subnet ではなく、別の subnet から pod IP address を割り当てる機能です。

**実装方法**:

```bash
kubectl set env daemonset aws-node -n kube-system AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true
kubectl set env daemonset aws-node -n kube-system ENI_CONFIG_LABEL_DEF=failure-domain.beta.kubernetes.io/zone
```

availability zone ごとに ENIConfig を作成します:

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

**利点**:

* node subnet の IP address exhaustion を防ぎます
* pod networking 用の専用 subnet 設定が可能です
* より大きな CIDR block を使用できます

**欠点**:

* setup と management が複雑です
* 追加の subnet が必要です
* node が置き換えられると ENIConfig の再設定が必要です

### 3. Secondary CIDR Blocks を追加

**説明**: VPC に secondary CIDR block を追加し、それらを新しい subnet に割り当てて IP address space を拡張します。

**実装方法**:

1. AWS console または CLI を通じて VPC に secondary CIDR block を追加
2. secondary CIDR block に新しい subnet を作成
3. custom networking mode と併用

**利点**:

* 既存 VPC の IP address space を大幅に拡張します
* 既存 infrastructure に影響を与えずに実装できます
* より大きな CIDR block を使用できます

**欠点**:

* VPC peering、Transit Gateway などで networking configuration complexity が増加します
* routing table の update が必要です
* 一部の AWS service は secondary CIDR を完全にはサポートしない場合があります

### 4. Alternative CNI Plugins を使用

**説明**: Amazon VPC CNI の代わりに Calico や Cilium などの alternative CNI plugin を使用します。

**実装方法**:

```bash
# Calico installation example
kubectl apply -f https://docs.projectcalico.org/manifests/calico-vxlan.yaml

# Disable Amazon VPC CNI
kubectl patch daemonset aws-node -n kube-system -p '{"spec": {"template": {"spec": {"nodeSelector": {"non-existing": "true"}}}}}'
```

**利点**:

* overlay network により IP address limitation を解決します
* より豊富な network policy 機能があります
* cloud provider に依存しない networking が可能です

**欠点**:

* AWS native feature (security group など) との統合が不足します
* performance overhead が発生する可能性があります
* management complexity が増加します
* AWS support scope の外になります

### 5. より大きい Subnet CIDRs を使用

**説明**: cluster 作成時に、より大きな CIDR block を持つ subnet を使用します。

**実装方法**: 新しい cluster を作成する際に、より大きな CIDR block (例: /16 または /17) を持つ subnet を使用します

**利点**:

* 実装が簡単です
* 追加設定は不要です
* 既存のすべての VPC CNI 機能が利用可能です

**欠点**:

* 既存 cluster への適用が困難です
* IP address space の非効率な使用につながる可能性があります
* VPC design の変更が必要です

### 6. Warm IP と Minimum IP の設定を最適化

**説明**: VPC CNI の IP address allocation behavior を最適化して、IP address usage efficiency を向上させます。

**実装方法**:

```bash
# Set warm IP target
kubectl set env daemonset aws-node -n kube-system WARM_IP_TARGET=5

# Set minimum IP target
kubectl set env daemonset aws-node -n kube-system MINIMUM_IP_TARGET=10

# Set maximum ENI
kubectl set env daemonset aws-node -n kube-system MAX_ENI=5
```

**利点**:

* 既存設定の簡単な調整で実装できます
* 追加の infrastructure 変更は不要です
* IP address allocation efficiency が向上します

**欠点**:

* IP address 不足問題を完全には解決できない場合があります
* pod startup delay が発生する可能性があります
* node type によって効果が限定的です

### 7. Hybrid Approach

**説明**: 複数の戦略を組み合わせて使用します。たとえば、prefix delegation と custom networking を併用したり、一部の workload を Fargate に移行したりします。

**実装方法**: workload の特性に応じて、さまざまな戦略を選択的に適用します

**利点**:

* workload の特性に最適化された解決策です
* resource efficiency が向上します
* 段階的な実装が可能です

**欠点**:

* configuration と management complexity が増加します
* さまざまな networking model を理解する必要があります
* troubleshooting difficulty が増加します

### 8. Fargate を使用

**説明**: node-based workload の代わりに Fargate を使用し、IP address management を AWS に委任します。

**実装方法**:

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

**利点**:

* IP address management overhead をなくせます
* node management が不要です
* serverless scalability が得られます

**欠点**:

* cost increase が発生する可能性があります
* 一部の Kubernetes 機能に制限があります (DaemonSets、privileged containers など)
* すべての workload に適しているわけではありません

### 推奨される Approach と Best Practices

1. **現状を評価**:
   * 現在の IP address usage と予想 growth rate を分析します
   * workload の特性と要件を理解します
   * 既存の network configuration を確認します
2. **短期的な解決策**:
   * prefix delegation を有効化します (最も簡単で効果的な方法)
   * warm IP と minimum IP 設定を最適化します
   * 不要な pod を cleanup します
3. **中長期的な解決策**:
   * custom networking を設定します
   * secondary CIDR block を追加します
   * hybrid approach を実装します
4. **Monitoring and Alerting**:
   * IP address usage を監視します
   * threshold-based alert を設定します
   * 定期的な capacity planning review を行います
5. **Automation**:
   * IP address usage の monitoring と reporting を自動化します
   * cluster が scale するときに network configuration を自動調整します
   * documentation と operational procedure を整備します

IP address exhaustion は EKS cluster の成長に伴ってよく発生する問題であり、cluster の規模と workload の特性に基づいて適切な戦略を選択または組み合わせる必要があります。Prefix delegation はほとんどの場合で最も簡単かつ効果的な解決策ですが、長期的にはより包括的な network design が必要になる場合があります。

</details>

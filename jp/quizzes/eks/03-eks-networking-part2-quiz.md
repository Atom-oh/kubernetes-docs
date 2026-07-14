# EKS Networking Quiz - Part 2

このクイズでは、Amazon EKS、AWS Load Balancer Controller、Ingress resources、service mesh、network security における高度な networking concepts の理解を確認します。

## Multiple Choice Questions

### 1. AWS Load Balancer Controller は、Kubernetes Ingress resources に対してデフォルトでどの種類の AWS load balancer をプロビジョニングしますか？

A. Classic Load Balancer (CLB) B. Network Load Balancer (NLB) C. Application Load Balancer (ALB) D. Gateway Load Balancer (GWLB)

<details>

<summary>回答を表示</summary>

**回答: C. Application Load Balancer (ALB)**

**解説:** AWS Load Balancer Controller は、Kubernetes Ingress resources に対してデフォルトで Application Load Balancer (ALB) をプロビジョニングします。ALB は HTTP/HTTPS traffic を処理する Layer 7 load balancer であり、path-based routing、host-based routing、TLS termination などの機能を提供して Ingress resources の要件を満たします。

**主な機能:**

1. **Path-Based Routing**: ALB は URL path に基づいて traffic を異なる services に route できるため、Ingress で path-based routing rules を実装するのに適しています。
2. **Host-Based Routing**: 複数の domains を単一の ALB で処理でき、複数の host rules を持つ Ingress をサポートします。
3. **TLS Termination**: ALB は SSL/TLS certificates を管理し、HTTPS traffic を terminate できます。
4. **WebSockets Support**: ALB は WebSockets protocol をサポートしており、real-time applications に適しています。
5. **Authentication Integration**: Amazon Cognito または OIDC と統合して、application-level authentication を提供できます。

**設定例:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
spec:
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
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
```

**主な Annotations:**

* `kubernetes.io/ingress.class: alb`: ALB Ingress Controller を使用することを指定します
* `alb.ingress.kubernetes.io/scheme: internet-facing`: internet-facing ALB を作成します
* `alb.ingress.kubernetes.io/target-type: ip`: targets として pod IPs を使用します（instance ではなく）
* `alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'`: listener ports を設定します
* `alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account-id:certificate/certificate-id`: SSL certificate を指定します

他の選択肢の問題点:

* **A. Classic Load Balancer (CLB)**: AWS Load Balancer Controller は Ingress resources に CLB を使用しません。CLB は legacy load balancer と見なされています。
* **B. Network Load Balancer (NLB)**: NLB は主に Service type LoadBalancer に使用され、Ingress resources ではデフォルトで使用されません。
* **D. Gateway Load Balancer (GWLB)**: GWLB は network virtual appliances 用であり、Kubernetes Ingress resources では使用されません。

</details>

### 2. AWS Load Balancer Controller を使用して internal Application Load Balancer を作成するには、Amazon EKS の Ingress resource にどの annotation を追加する必要がありますか？

A. `service.beta.kubernetes.io/aws-load-balancer-internal: "true"` B. `alb.ingress.kubernetes.io/scheme: internal` C. `kubernetes.io/ingress.class: internal-alb` D. `aws-load-balancer-type: internal`

<details>

<summary>回答を表示</summary>

**回答: B. `alb.ingress.kubernetes.io/scheme: internal`**

**解説:** Amazon EKS で AWS Load Balancer Controller を使用して internal Application Load Balancer を作成するには、`alb.ingress.kubernetes.io/scheme: internal` annotation を Ingress resource に追加する必要があります。この annotation は、ALB を VPC 内からのみアクセス可能に設定します。

**Internal ALB 設定例:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: internal-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internal
spec:
  rules:
  - host: internal.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: internal-service
            port:
              number: 80
```

**主な考慮事項:**

1.  **Subnet Selection**: Internal ALBs は private subnets に作成されます。Subnets は明示的に指定できます:

    ```yaml
    alb.ingress.kubernetes.io/subnets: subnet-0123456789abcdef0,subnet-0123456789abcdef1
    ```
2.  **Security Groups**: 特定の Security Groups を internal ALBs に適用できます:

    ```yaml
    alb.ingress.kubernetes.io/security-groups: sg-0123456789abcdef0
    ```
3.  **Inbound CIDR Restriction**: 特定の CIDR blocks からのみアクセスを許可できます:

    ```yaml
    alb.ingress.kubernetes.io/inbound-cidrs: 10.0.0.0/16,192.168.0.0/16
    ```
4.  **Internal DNS**: Internal ALB は VPC 内の Route 53 private hosted zones と統合できます:

    ```yaml
    alb.ingress.kubernetes.io/load-balancer-attributes: routing.http.drop_invalid_header_fields.enabled=true,access_logs.s3.enabled=true
    ```

**Internal ALB のユースケース:**

* Microservices 間の internal communication
* Backend API services
* Administrative interfaces
* Development and test environments
* Regulatory requirements のある workloads

**AWS Load Balancer Controller Installation の確認:**

```bash
kubectl get deployment -n kube-system aws-load-balancer-controller
```

他の選択肢の問題点:

* **A. `service.beta.kubernetes.io/aws-load-balancer-internal: "true"`**: この annotation は Service type LoadBalancer に使用され、Ingress resources には適用されません。
* **C. `kubernetes.io/ingress.class: internal-alb`**: 正しい ingress.class は 'alb' です。'internal-alb' は有効な値ではありません。
* **D. `aws-load-balancer-type: internal`**: この annotation は存在しません。

</details>

### 3. Amazon EKS で AWS Load Balancer Controller が pod IPs を直接 targets として使用するよう設定するには、どの annotation を使用しますか？

A. `alb.ingress.kubernetes.io/target-type: pod` B. `alb.ingress.kubernetes.io/target-type: ip` C. `service.beta.kubernetes.io/aws-load-balancer-target-type: ip` D. `aws-load-balancer-target-node-labels: ip-mode=true`

<details>

<summary>回答を表示</summary>

**回答: B. `alb.ingress.kubernetes.io/target-type: ip`**

**解説:** Amazon EKS で AWS Load Balancer Controller が pod IPs を直接 targets として使用するよう設定するには、`alb.ingress.kubernetes.io/target-type: ip` annotation を使用する必要があります。この設定により、load balancer は node IPs ではなく pod IPs へ直接 traffic を route できます。

**Target Type Options:**

1. **instance**: （デフォルト）node IP と NodePort を使用して traffic を route します。
2. **ip**: pod IP と container port を使用して pods に直接 traffic を route します。

**IP Mode 設定例:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/target-type: ip
spec:
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example-service
            port:
              number: 80
```

**IP Mode の利点:**

1. **Node Failure Resilience**: node が故障しても、traffic は他の nodes 上の pods へ引き続き route されます。
2. **Direct Routing**: NodePort を経由する追加 hop なしで、traffic が pods に直接配信されます。
3. **Fargate Compatibility**: AWS Fargate で実行される pods には必須です。
4. **Security Group Integration**: Security Groups を pod level で適用できます。

**IP Mode Requirements:**

1. **VPC CNI**: Amazon VPC CNI plugin が必要です。
2. **Subnet Configuration**: pods が実行される subnets は、load balancer subnets に routing 可能である必要があります。
3. **Security Group Rules**: Load balancer の Security Group は pod IPs への traffic を許可する必要があります。

**IP Mode vs Instance Mode Comparison:**

| Characteristic  | IP Mode            | Instance Mode                       |
| --------------- | ------------------ | ----------------------------------- |
| Target          | Pod IP             | Node IP                             |
| Port            | Container port     | NodePort                            |
| Traffic Path    | LB -> Pod          | LB -> Node -> Pod                   |
| On Node Failure | No impact          | Pods on that node inaccessible      |
| Performance     | Better performance | Slight overhead from additional hop |
| Fargate Support | Supported          | Not supported                       |

**追加の設定オプション:**

```yaml
# Target group attributes setting
alb.ingress.kubernetes.io/target-group-attributes: deregistration_delay.timeout_seconds=30,stickiness.enabled=true

# Health check settings
alb.ingress.kubernetes.io/healthcheck-path: /health
alb.ingress.kubernetes.io/healthcheck-interval-seconds: '15'
alb.ingress.kubernetes.io/healthcheck-timeout-seconds: '5'
alb.ingress.kubernetes.io/success-codes: '200'
alb.ingress.kubernetes.io/healthy-threshold-count: '2'
alb.ingress.kubernetes.io/unhealthy-threshold-count: '2'
```

他の選択肢の問題点:

* **A. `alb.ingress.kubernetes.io/target-type: pod`**: 正しい値は 'pod' ではなく 'ip' です。
* **C. `service.beta.kubernetes.io/aws-load-balancer-target-type: ip`**: この annotation は Service type LoadBalancer に使用され、Ingress resources には適用されません。
* **D. `aws-load-balancer-target-node-labels: ip-mode=true`**: この annotation は存在しません。

</details>

### 4. Amazon EKS で VPC endpoint service を作成するために、Kubernetes Service と AWS PrivateLink を統合するにはどの annotation を使用しますか？

A. `service.beta.kubernetes.io/aws-load-balancer-type: nlb` B. `service.beta.kubernetes.io/aws-load-balancer-private-link: "true"` C. `service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip` D. `service.beta.kubernetes.io/aws-vpc-endpoint-service: "true"`

<details>

<summary>回答を表示</summary>

**回答: C. `service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip`**

**解説:** Amazon EKS で VPC endpoint service を作成するために Kubernetes Service と AWS PrivateLink を統合するには、`service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip` annotation を使用する必要があります。この annotation は IP mode の Network Load Balancer (NLB) を作成し、これは AWS PrivateLink との統合の前提条件です。

**VPC Endpoint Service 設定手順:**

1. **NLB-IP Mode で Kubernetes Service を作成:**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: privatelink-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip
    service.beta.kubernetes.io/aws-load-balancer-internal: "true"
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8080
  selector:
    app: my-app
```

2. **AWS CLI を使用して VPC Endpoint Service を作成:**

```bash
# Get NLB ARN
NLB_ARN=$(aws elbv2 describe-load-balancers --names $(kubectl get svc privatelink-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' | cut -d- -f1) --query 'LoadBalancers[0].LoadBalancerArn' --output text)

# Create VPC endpoint service
aws ec2 create-vpc-endpoint-service-configuration \
  --network-load-balancer-arns $NLB_ARN \
  --acceptance-required \
  --private-dns-name service.example.com
```

3. **VPC Endpoint Service Allow List を設定:**

```bash
aws ec2 modify-vpc-endpoint-service-permissions \
  --service-id vpce-svc-0123456789abcdef0 \
  --add-allowed-principals arn:aws:iam::111122223333:root
```

**主な考慮事項:**

1. **Internal NLB Requirement**: PrivateLink には internal NLB が必要なため、`service.beta.kubernetes.io/aws-load-balancer-internal: "true"` annotation も必要です。
2. **Importance of IP Mode**: NLB-IP mode は pod IPs を targets として直接使用することで、node failures への resilience を提供します。
3. **Service Name Resolution**: Private DNS names を設定して、VPC 内での service name resolution を簡素化できます。
4. **Access Control**: `acceptance-required` flag を使用して、endpoint connection requests を手動で承認できます。
5. **Network ACLs and Security Groups**: 適切な network ACL と Security Group rules が設定されていることを確認してください。

**PrivateLink Integration のメリット:**

* **Enhanced Security**: Traffic は public internet を経由せず AWS network 内に留まります。
* **Compliance**: Data sovereignty と compliance requirements を満たします。
* **Simplified Networking**: VPC peering、Transit Gateway、VPN connections なしで services にアクセスできます。
* **Scalability**: Services は数千の VPCs からアクセスできます。

**Client-Side Configuration:**

```bash
# Create VPC endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-0123456789abcdef0 \
  --service-name com.amazonaws.vpce.us-east-1.vpce-svc-0123456789abcdef0 \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-0123456789abcdef0 subnet-0123456789abcdef1 \
  --security-group-ids sg-0123456789abcdef0
```

他の選択肢の問題点:

* **A. `service.beta.kubernetes.io/aws-load-balancer-type: nlb`**: この annotation は instance mode NLB を作成し、PrivateLink integration に最適化されていません。
* **B. `service.beta.kubernetes.io/aws-load-balancer-private-link: "true"`**: この annotation は存在しません。
* **D. `service.beta.kubernetes.io/aws-vpc-endpoint-service: "true"`**: この annotation は存在しません。

</details>

### 5. Amazon EKS で Kubernetes NetworkPolicy resources を実装するために、Amazon VPC CNI と併用できる追加 component は何ですか？

A. AWS Network Firewall B. Calico C. AWS Security Groups for Pods D. VPC Flow Logs

<details>

<summary>回答を表示</summary>

**回答: B. Calico**

**解説:** Calico は、Amazon EKS で Kubernetes NetworkPolicy resources を実装するために Amazon VPC CNI と併用できる追加 component です。Calico は Kubernetes NetworkPolicy API をサポートする open-source networking and network security solution であり、Amazon VPC CNI と連携して EKS clusters で fine-grained network policies を適用します。

**Calico Installation and Configuration:**

1. **Calico のインストール:**

```bash
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml
```

2. **Installation の確認:**

```bash
kubectl get pods -n calico-system
```

3. **Basic NetworkPolicy Example:**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

**Calico の主な機能:**

1. **Kubernetes NetworkPolicy Support**: 標準の Kubernetes NetworkPolicy API を完全に実装します。
2. **Extended Policy Features**: Calico の GlobalNetworkPolicy や NetworkSet などの custom resources を通じて、Kubernetes NetworkPolicy を超える advanced network policies を提供します。
3. **Fine-Grained Control**: protocols、ports、CIDR blocks、service accounts などに基づいて traffic を filter できます。
4. **Logging and Monitoring**: Network policy violations を log および monitor できます。
5. **Host Endpoint Protection**: Kubernetes nodes 自体に network policies を適用できます。

**Calico Advanced Policy Example:**

```yaml
# GlobalNetworkPolicy example (cluster-wide policy)
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: allow-cluster-internal-traffic
spec:
  selector: all()
  types:
  - Ingress
  - Egress
  ingress:
  - action: Allow
    source:
      selector: all()
  egress:
  - action: Allow
    destination:
      selector: all()

# Restrict access to specific IP ranges
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: external-services
spec:
  nets:
  - 203.0.113.0/24
  - 198.51.100.0/24
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-external-services
  namespace: app
spec:
  podSelector:
    matchLabels:
      role: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
  - to:
    - ipBlock:
        cidr: 203.0.113.0/24
    - ipBlock:
        cidr: 198.51.100.0/24
```

**Amazon VPC CNI と Calico の統合:**

1. **Network Mode**: Amazon VPC CNI と併用する場合、Calico は overlay mode ではなく policy-only mode で動作します。
2. **Performance**: Amazon VPC CNI の native VPC networking performance を維持しながら、Calico の network policy features を活用します。
3. **Compatibility**: Calico はすべての Amazon VPC CNI features（prefix delegation、custom networking など）と互換性があります。
4. **Upgrades**: Calico と Amazon VPC CNI は独立して upgrade できます。

**Best Practices:**

* default deny policy から開始し、必要な communications のみを明示的に許可します。
* inter-namespace communication の明確な policies を定義します。
* policies を適用する前に logging mode でテストします。
* cluster essential components への communication は常に許可します。
* policies を定期的に review および update します。

他の選択肢の問題点:

* **A. AWS Network Firewall**: AWS Network Firewall は VPC-level firewall service であり、Kubernetes NetworkPolicy との直接統合はありません。
* **C. AWS Security Groups for Pods**: Security Groups for Pods は AWS Security Groups を pods に適用する機能ですが、Kubernetes NetworkPolicy API は実装しません。
* **D. VPC Flow Logs**: VPC Flow Logs は network traffic を monitoring するための tool であり、network policies は適用しません。

</details>

## Short Answer Questions

### 6. Amazon EKS で AWS Load Balancer Controller を使用して Application Load Balancer を作成する際に、特定の Security Groups を割り当てるにはどの annotation を使用しますか？

<details>

<summary>回答を表示</summary>

**回答:** `alb.ingress.kubernetes.io/security-groups: sg-xxxx,sg-yyyy`

**詳細な解説:**

AWS Load Balancer Controller を使用して Application Load Balancer (ALB) を作成する場合、`alb.ingress.kubernetes.io/security-groups` annotation を使用して特定の Security Groups を割り当てることができます。この annotation は、ALB に attach する Security Group IDs をカンマ区切りで指定します。

**実装方法:**

1.  **Security Group IDs を指定:**

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: example-ingress
      annotations:
        kubernetes.io/ingress.class: alb
        alb.ingress.kubernetes.io/security-groups: sg-0123456789abcdef0,sg-0123456789abcdef1
    spec:
      rules:
      - http:
          paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: example-service
                port:
                  number: 80
    ```
2.  **Security Group Names を指定（代替方法）:**

    ```yaml
    alb.ingress.kubernetes.io/security-groups: my-security-group-name
    ```
3.  **Security Groups を自動作成:**

    ```yaml
    alb.ingress.kubernetes.io/manage-backend-security-group-rules: "true"
    ```

**主な考慮事項:**

1. **Security Group Rules:**
   * Inbound rules: client traffic（通常 HTTP/80、HTTPS/443）を許可する必要があります。
   * Outbound rules: target groups（pods または nodes）への traffic を許可する必要があります。
2. **Default Behavior:** annotation が指定されていない場合、AWS Load Balancer Controller は Security Group を自動作成し、必要な rules を設定します。
3. **Permission Requirements:** AWS Load Balancer Controller の IAM role には、次の permissions が必要です:
   * ec2:CreateSecurityGroup
   * ec2:DeleteSecurityGroup
   * ec2:DescribeSecurityGroups
   * ec2:AuthorizeSecurityGroupIngress
   * ec2:RevokeSecurityGroupIngress
4.  **Security Group Management:**

    ```yaml
    # Set controller to manage security group rules
    alb.ingress.kubernetes.io/manage-backend-security-group-rules: "true"
    ```
5.  **Tagging:** 作成された Security Groups に tags を追加できます:

    ```yaml
    alb.ingress.kubernetes.io/tags: Environment=prod,Team=devops
    ```

**Best Practices:**

1. **Principle of Least Privilege:** 必要な traffic のみを許可する制限的な Security Group rules を使用します。
2. **Security Group Reuse:** 管理を簡素化するために、複数の Ingress resources で同じ Security Groups を再利用します。
3. **Documentation:** 追跡のため、使用している Security Groups とその rules を文書化します。
4. **Regular Review:** 不要な access を削除するため、Security Group rules を定期的に review します。
5. **Monitoring:** 拒否された connections を monitor して、Security Group rules の有効性を評価します。

**関連 Annotations:**

*   **Inbound CIDR Restriction:**

    ```yaml
    alb.ingress.kubernetes.io/inbound-cidrs: 10.0.0.0/16,192.168.0.0/16
    ```
*   **Security Group Tags:**

    ```yaml
    alb.ingress.kubernetes.io/load-balancer-attributes: load_balancing.cross_zone.enabled=true
    ```
*   **SSL Policy:**

    ```yaml
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS-1-2-2017-01
    ```

AWS Load Balancer Controller を使用すると、Kubernetes Ingress resources を通じて ALB Security Groups を fine-grained に制御でき、cluster の network security posture を強化するのに役立ちます。

</details>

### 7. Amazon EKS で Kubernetes Service resource を Network Load Balancer として公開する際に、client IP addresses を保持するにはどの annotation を使用しますか？

<details>

<summary>回答を表示</summary>

**回答:** `service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true`

**詳細な解説:**

Amazon EKS で Kubernetes Service resource を Network Load Balancer (NLB) として公開する場合、client IP addresses を保持するには `service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true` annotation を使用する必要があります。この設定により、NLB は元の client IP addresses を維持します。

**実装方法:**

1.  **Basic NLB Service Configuration:**

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: example-service
      annotations:
        service.beta.kubernetes.io/aws-load-balancer-type: nlb
        service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true
    spec:
      type: LoadBalancer
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: example
    ```
2.  **IP Mode NLB で使用:**

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: example-service
      annotations:
        service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip
        service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true
    spec:
      type: LoadBalancer
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: example
    ```

**Client IP Preservation の重要性:**

1. **Security and Access Control:**
   * client IP-based access control を実装する
   * 疑わしい IP addresses を block する
   * IP-based rate limiting を適用する
2. **Logging and Auditing:**
   * request sources を追跡する
   * security events を調査する
   * compliance requirements を満たす
3. **Geolocation-Based Features:**
   * region-specific content を提供する
   * geographic analysis を実行する

**仕組み:**

1. **Instance Mode (aws-load-balancer-type: nlb):**
   * TCP traffic では、client IP は自動的に保持されます。
   * UDP traffic では、preserve\_client\_ip.enabled=true 設定が必要です。
2. **IP Mode (aws-load-balancer-type: nlb-ip):**
   * TCP と UDP traffic の両方で preserve\_client\_ip.enabled=true 設定が必要です。

**制限事項と考慮事項:**

1. **Proxy Protocol:** Client IP preservation は proxy protocol を使用せず、direct packet routing によって行われます。
2. **Target Group Types:**
   * Instance mode: node IP と NodePort を使用します。
   * IP mode: pod IP と port を直接使用します。
3. **Performance Impact:** Client IP preservation により、わずかな performance overhead が発生する場合があります。
4. **Compatibility:** 一部の legacy applications は client IP preservation と互換性がない場合があります。

**Applications で Client IP にアクセスする方法:**

1.  **HTTP Applications:**

    ```python
    # Python Flask example
    from flask import Flask, request

    app = Flask(__name__)

    @app.route('/')
    def index():
        client_ip = request.remote_addr
        return f"Your IP address is: {client_ip}"
    ```
2.  **TCP/UDP Applications:**

    ```go
    // Go example
    package main

    import (
        "fmt"
        "net"
    )

    func handleConnection(conn net.Conn) {
        addr := conn.RemoteAddr().String()
        fmt.Printf("Client connected from: %s\n", addr)
        // ...
    }
    ```

**関連 Annotations:**

*   **Internal NLB Configuration:**

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-internal: "true"
    ```
*   **Cross-Zone Load Balancing:**

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: load_balancing.cross_zone.enabled=true
    ```
*   **TCP Connection Keep-Alive:**

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true,deregistration_delay.timeout_seconds=30
    ```

Client IP preservation は security、logging、access control などさまざまな目的で重要であり、適切な annotation を使用して EKS clusters で簡単に設定できます。

</details>

### 8. Amazon EKS で AWS WAF (Web Application Firewall) を Kubernetes Ingress resource に attach するにはどの annotation を使用しますか？

<details>

<summary>回答を表示</summary>

**回答:** `alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:region:account-id:global/webacl/name/id`

**詳細な解説:**

Amazon EKS で AWS WAF (Web Application Firewall) を Kubernetes Ingress resource に attach するには、`alb.ingress.kubernetes.io/wafv2-acl-arn` annotation を使用する必要があります。この annotation は、AWS Load Balancer Controller によって作成された Application Load Balancer (ALB) に AWS WAF WebACL を attach します。

**実装方法:**

1.  **AWS WAF WebACL を作成:** まず、AWS Management Console、AWS CLI、または AWS CloudFormation を使用して WAF WebACL を作成します。

    ```bash
    # AWS CLI example
    aws wafv2 create-web-acl \
      --name "eks-ingress-protection" \
      --scope "REGIONAL" \
      --default-action Allow={} \
      --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=eks-ingress-protection \
      --region us-west-2
    ```
2.  **Ingress Resource に WAF WebACL ARN を指定:**

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: example-ingress
      annotations:
        kubernetes.io/ingress.class: alb
        alb.ingress.kubernetes.io/scheme: internet-facing
        alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:us-west-2:111122223333:regional/webacl/eks-ingress-protection/a1b2c3d4-5678-90ab-cdef
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

**AWS WAF の主な保護機能:**

1. **Common Web Vulnerability Defense:**
   * SQL injection attacks
   * Cross-site scripting (XSS)
   * Path traversal attacks
   * Command injection
2. **Bot Traffic Control:**
   * malicious bots を block する
   * scraping を防止する
   * credential stuffing attacks を防止する
3. **Rate Limiting:**
   * DDoS attack mitigation
   * brute force attacks を防止する
4. **Geographic Restrictions:**
   * 特定の countries または regions からの access を制限する
5. **IP Reputation Filtering:**
   * 既知の malicious IP addresses を block する

**AWS WAF Rule Group Examples:**

1. **AWS Managed Rules:**
   * AWS Core rule set (CRS)
   * SQL database rules
   * Linux operating system rules
   * PHP application rules
2.  **Custom Rules:**

    ```json
    {
      "Name": "block-specific-uri-paths",
      "Priority": 1,
      "Action": { "Block": {} },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "block-specific-uri-paths"
      },
      "Statement": {
        "ByteMatchStatement": {
          "SearchString": "/admin",
          "FieldToMatch": { "UriPath": {} },
          "TextTransformations": [
            { "Priority": 0, "Type": "NONE" }
          ],
          "PositionalConstraint": "STARTS_WITH"
        }
      }
    }
    ```

**Monitoring and Logging:**

1.  **CloudWatch Logs を有効化:**

    ```yaml
    alb.ingress.kubernetes.io/load-balancer-attributes: access_logs.s3.enabled=true,access_logs.s3.bucket=my-alb-logs,access_logs.s3.prefix=ingress-logs
    ```
2.  **WAF Logging を設定:**

    ```bash
    aws wafv2 put-logging-configuration \
      --logging-configuration ResourceArn=arn:aws:wafv2:us-west-2:111122223333:regional/webacl/eks-ingress-protection/a1b2c3d4-5678-90ab-cdef,LogDestinationConfigs=arn:aws:firehose:us-west-2:111122223333:deliverystream/aws-waf-logs \
      --region us-west-2
    ```

**Permission Requirements:**

AWS Load Balancer Controller の IAM role には、次の permissions が必要です:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "wafv2:AssociateWebACL",
        "wafv2:DisassociateWebACL",
        "wafv2:GetWebACL",
        "wafv2:GetWebACLForResource"
      ],
      "Resource": "*"
    }
  ]
}
```

**Best Practices:**

1. **Defense in Depth:** network security、authentication、authorization など他の security controls と併用して WAF を使用します。
2. **Regular Rule Updates:** 新しい threats に対応するため、WAF rules を定期的に review および update します。
3. **Logging and Monitoring:** WAF logs を分析して attack patterns を特定し、rules を改善します。
4. **Testing:** production に適用する前に、test environments で WAF rules を検証します。
5. **Count Mode:** 新しい rules を初めて deploy する場合は、false positives を monitor するために block ではなく count mode に設定します。

AWS WAF と EKS Ingress の統合は application security を強化する強力な方法であり、適切な annotation を使用して簡単に設定できます。

</details>

## Hands-on Questions

### 9. Amazon EKS cluster で AWS Load Balancer Controller を使用して Application Load Balancer を作成し、特定の paths に基づいて traffic を異なる services に route する Ingress resource を作成してください。

<details>

<summary>回答を表示</summary>

**回答:** 以下は、AWS Load Balancer Controller を使用して Application Load Balancer を作成し、特定の paths に基づいて traffic を異なる services に route する Ingress resource です:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: multi-path-ingress
  namespace: default
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account-id:certificate/certificate-id
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    alb.ingress.kubernetes.io/healthcheck-path: /health
    alb.ingress.kubernetes.io/success-codes: '200'
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: '15'
    alb.ingress.kubernetes.io/healthcheck-timeout-seconds: '5'
spec:
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
      - path: /admin
        pathType: Prefix
        backend:
          service:
            name: admin-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
```

**詳細な解説:**

1. **Ingress Resource Component Explanation**:
   * **metadata.annotations**: AWS Load Balancer Controller の configuration options を指定します。
     * `kubernetes.io/ingress.class: alb`: AWS Load Balancer Controller の使用を指定します。
     * `alb.ingress.kubernetes.io/scheme: internet-facing`: internet-accessible ALB を作成します。
     * `alb.ingress.kubernetes.io/target-type: ip`: targets として pod IPs を使用します。
     * `alb.ingress.kubernetes.io/listen-ports`: HTTP(80) と HTTPS(443) ports の両方で listen します。
     * `alb.ingress.kubernetes.io/certificate-arn`: HTTPS 用の ACM certificate を指定します。
     * `alb.ingress.kubernetes.io/ssl-redirect`: HTTP traffic を HTTPS に redirect します。
     * `alb.ingress.kubernetes.io/healthcheck-*`: health check settings を設定します。
   * **spec.rules**: host と path-based routing rules を定義します。
     * `/api` path は `api-service` に route されます。
     * `/admin` path は `admin-service` に route されます。
     * `/` (root) path は `frontend-service` に route されます。
2.  **実装手順**:

    a. **必要な Services を作成**:

    ```yaml
    # api-service.yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: api-service
    spec:
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: api
    ---
    # admin-service.yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: admin-service
    spec:
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: admin
    ---
    # frontend-service.yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: frontend-service
    spec:
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: frontend
    ```

    b. **Services 用の Deployments を作成**:

    ```yaml
    # api-deployment.yaml
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: api-deployment
    spec:
      replicas: 2
      selector:
        matchLabels:
          app: api
      template:
        metadata:
          labels:
            app: api
        spec:
          containers:
          - name: api
            image: nginx
            ports:
            - containerPort: 8080
            readinessProbe:
              httpGet:
                path: /health
                port: 8080
    ```

    （admin と frontend deployments にも同様の configurations が必要です）

    c. **AWS Load Balancer Controller Installation を確認**:

    ```bash
    kubectl get deployment -n kube-system aws-load-balancer-controller
    ```

    d. **Ingress Resource を適用**:

    ```bash
    kubectl apply -f multi-path-ingress.yaml
    ```

    e. **Ingress Status を確認**:

    ```bash
    kubectl get ingress multi-path-ingress
    ```
3.  **テスト方法**:

    a. **DNS Setup**: Ingress によって作成された ALB の DNS name を取得します:

    ```bash
    kubectl get ingress multi-path-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
    ```

    この DNS name を `example.com` の CNAME record として設定します。

    b. **Path-Based Routing をテスト**:

    ```bash
    # Test API service
    curl https://example.com/api

    # Test admin service
    curl https://example.com/admin

    # Test frontend service
    curl https://example.com/
    ```
4.  **注意事項と考慮事項**:

    a. **SSL Certificate**: HTTPS を使用するには有効な SSL certificate が必要です。AWS Certificate Manager (ACM) で certificate を作成し、annotation に ARN を指定します。

    b. **IAM Permissions**: AWS Load Balancer Controller には、ALB と related resources を作成および管理するための適切な IAM permissions が必要です。

    c. **Health Checks**: 各 service は health check endpoint (`/health`) を提供する必要があります。

    d. **Target Group Settings**: `target-type: ip` を使用すると、pod IPs が targets として直接使用されます。これにより node failures への resilience が得られ、Fargate pods をサポートします。

    e. **Security Groups**: 必要に応じて、特定の Security Groups を ALB に適用できます:

    ```yaml
    alb.ingress.kubernetes.io/security-groups: sg-0123456789abcdef0
    ```
5.  **追加の設定オプション**:

    a. **Session Stickiness を有効化**:

    ```yaml
    alb.ingress.kubernetes.io/target-group-attributes: stickiness.enabled=true,stickiness.lb_cookie.duration_seconds=86400
    ```

    b. **Access Logs を有効化**:

    ```yaml
    alb.ingress.kubernetes.io/load-balancer-attributes: access_logs.s3.enabled=true,access_logs.s3.bucket=my-alb-logs,access_logs.s3.prefix=ingress-logs
    ```

    c. **IP-Based Restrictions**:

    ```yaml
    alb.ingress.kubernetes.io/inbound-cidrs: 192.168.0.0/16,10.0.0.0/8
    ```

    d. **Weighted Routing**:

    ```yaml
    alb.ingress.kubernetes.io/actions.weighted-routing: >
      {"Type":"forward","ForwardConfig":{"TargetGroups":[{"ServiceName":"service-v1","ServicePort":"80","Weight":80},{"ServiceName":"service-v2","ServicePort":"80","Weight":20}]}}
    ```

AWS Load Balancer Controller と Ingress resources を使用すると、EKS clusters で complex routing rules を実装し、さまざまな ALB features を活用して application availability、scalability、security を向上させることができます。

</details>

## Advanced Questions

### 10. Amazon EKS cluster に service mesh（例: Istio、AWS App Mesh）を実装する際の主な考慮事項と networking architecture の変更点を説明してください。また、service mesh が EKS の default networking model とどのように統合されるかも説明してください。

<details>

<summary>回答を表示</summary>

**回答:** 以下では、Amazon EKS cluster に service mesh（例: Istio、AWS App Mesh）を実装する際の主な考慮事項と networking architecture の変更点、および service mesh が EKS の default networking model とどのように統合されるかを説明します:

### 1. Service Mesh Overview and Key Components

**Service Mesh とは？** Service mesh は、microservices 間の communication を管理する infrastructure layer であり、service discovery、traffic management、security、observability などの機能を提供します。

**主な Components:**

1. **Data Plane**:
   * Sidecar proxies（通常 Envoy）が各 pod に注入されます。
   * すべての inbound および outbound traffic を intercept して処理します。
2. **Control Plane**:
   * policies と configuration を管理します。
   * data plane proxies を設定します。
   * service discovery と routing information を提供します。

### 2. EKS Networking Architecture Changes

**Default EKS Networking Model:**

* Amazon VPC CNI を使用して VPC IP addresses を pods に割り当てます。
* Pods は VPC 内で直接通信します。
* Kubernetes Service resources は service discovery と load balancing を提供します。

**Service Mesh 導入後の変更点:**

1.  **Traffic Flow Change**:

    ```
    Default EKS: Client -> Service -> Target Pod
    Service Mesh: Client -> Client Sidecar -> Service -> Target Sidecar -> Target Pod
    ```
2. **Network Topology**:
   * Sidecar containers が各 pod に追加されます。
   * Applications と sidecars は pod 内の local network を通じて通信します。
   * Sidecar-to-sidecar communication は引き続き VPC CNI を使用します。
3. **Port Allocation**:
   * Sidecar proxies は追加の ports（management、metrics、health checks など）を使用します。
   * Port redirection は pod 内で行われます。

### 3. Major Service Mesh Options Comparison

#### Istio

**Architecture Integration:**

```yaml
# Istio sidecar injection example
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
        sidecar.istio.io/inject: "true"  # Automatic sidecar injection
    spec:
      containers:
      - name: example
        image: example:latest
        ports:
        - containerPort: 8080
```

**Networking Features:**

* Advanced traffic management（weighted routing、canary deployments）
* Circuit breakers と fault injection
* mTLS による service-to-service encryption
* Fine-grained access control

**EKS Integration Considerations:**

* 高い resource requirements（特に control plane）
* Fargate との compatibility は限定的
* setup と management が複雑

#### AWS App Mesh

**Architecture Integration:**

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

**Networking Features:**

* AWS services との seamless integration
* Cross-account と hybrid mesh support
* AWS X-Ray との統合
* 比較的 simple setup

**EKS Integration Considerations:**

* AWS services との優れた統合
* Fargate と互換性あり
* 一部の advanced features は制限される場合があります

### 4. Networking Considerations

#### Performance Impact

1. **Latency**:
   * Sidecar proxies を通る追加 hops により、latency がわずかに増加します（通常 <10ms）
   *   Optimization techniques:

       ```yaml
       # Istio example: Proxy resource optimization
       apiVersion: v1
       kind: ConfigMap
       metadata:
         name: istio-sidecar-injector
         namespace: istio-system
       data:
         values: |-
           pilot:
             resources:
               requests:
                 cpu: 500m
                 memory: 2048Mi
       ```
2. **Resource Usage**:
   * pod ごとに追加の CPU と memory overhead（通常 10-15%）
   * node density が低下する可能性があります

#### Network Policy Integration

1. **Kubernetes NetworkPolicy との関係**:
   * Service mesh は L7 policies を提供し、NetworkPolicy は L3/L4 policies を提供します。
   * defense in depth を実装するために、両方の policy types を併用できます。
2.  **Policy Example**:

    ```yaml
    # Istio authentication policy
    apiVersion: security.istio.io/v1beta1
    kind: PeerAuthentication
    metadata:
      name: default
      namespace: istio-system
    spec:
      mtls:
        mode: STRICT
    ---
    # Kubernetes NetworkPolicy
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: allow-same-namespace
    spec:
      podSelector: {}
      ingress:
      - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: default
    ```

### 5. Service Mesh Implementation Steps

#### 1. Verify Prerequisites

* cluster version compatibility を確認する
* resource requirements を評価する
* networking model を review する

#### 2. Install Control Plane

**Istio Example:**

```bash
istioctl install --set profile=default
```

**App Mesh Example:**

```bash
helm repo add eks https://aws.github.io/eks-charts
helm install appmesh-controller eks/appmesh-controller \
  --namespace appmesh-system \
  --create-namespace
```

#### 3. Configure Sidecar Injection

**Automatic Injection:**

```yaml
# Add label to namespace
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  labels:
    istio-injection: enabled  # Istio
    appmesh.k8s.aws/sidecarInjectorWebhook: enabled  # App Mesh
```

#### 4. Define Service Mesh Resources

**Istio Virtual Service and Destination Rule:**

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 90
    - destination:
        host: reviews
        subset: v2
      weight: 10
---
apiVersion: networking.istio.io/v1alpha3
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

**App Mesh Virtual Service and Virtual Router:**

```yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualService
metadata:
  name: reviews
  namespace: my-app
spec:
  awsName: reviews.my-app.svc.cluster.local
  provider:
    virtualRouter:
      virtualRouterRef:
        name: reviews-router
---
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualRouter
metadata:
  name: reviews-router
  namespace: my-app
spec:
  listeners:
    - portMapping:
        port: 9080
        protocol: http
  routes:
    - name: reviews-route
      httpRoute:
        match:
          prefix: /
        action:
          weightedTargets:
            - virtualNodeRef:
                name: reviews-v1
              weight: 90
            - virtualNodeRef:
                name: reviews-v2
              weight: 10
```

### 6. Monitoring and Observability

#### Metrics Collection

**Prometheus Integration:**

```yaml
# Istio Prometheus configuration
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  addonComponents:
    prometheus:
      enabled: true
```

#### Distributed Tracing

**X-Ray Integration (App Mesh):**

```yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: Mesh
metadata:
  name: my-mesh
spec:
  serviceDiscovery:
    ipPreference: IPv4_PREFERRED
  egressFilter:
    type: ALLOW_ALL
  tracing:
    awsXRay:
      logLevel: INFO
```

### 7. Service Mesh Adoption Best Practices

1. **Gradual Adoption**:
   * non-business-critical workloads から開始する
   * 段階的に拡大する
2. **Resource Planning**:
   * node size と count の増加を検討する
   * control plane 用に dedicated node groups を使用する
3. **Networking Optimization**:
   * 不要な sidecar injection を防ぐ
   * 適切な timeouts と retry policies を設定する
4. **Security Enhancement**:
   * mTLS を段階的に採用する
   * principle of least privilege を適用する
5. **Monitoring Strategy**:
   * service mesh 採用前後の performance を比較する
   * key metrics dashboards を設定する

### 8. EKS-Specific Considerations

1. **Fargate Compatibility**:
   * Istio: limited support（一部の features は利用不可）
   * App Mesh: full support
2. **AWS Load Balancer Controller Integration**:
   *   Ingress gateway と ALB integration:

       ```yaml
       apiVersion: networking.k8s.io/v1
       kind: Ingress
       metadata:
         annotations:
           kubernetes.io/ingress.class: alb
           alb.ingress.kubernetes.io/scheme: internet-facing
           alb.ingress.kubernetes.io/target-type: ip
       ```
3. **IAM Roles and Permissions**:
   * App Mesh controller に必要な IAM permissions:
     * appmesh:\*
     * servicediscovery:\*
     * cloudmap:\*
4. **VPC CNI Settings**:
   * service mesh による追加の ENI と IP address requirements を考慮する
   *   prefix delegation を有効化することを推奨:

       ```bash
       kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true
       ```

### 9. Service Mesh Selection Guide

| Factor                | Istio                   | AWS App Mesh             |
| --------------------- | ----------------------- | ------------------------ |
| Feature Set           | Very comprehensive      | Focused on core features |
| AWS Integration       | Third-party integration | Native integration       |
| Complexity            | High                    | Medium                   |
| Resource Requirements | High                    | Medium                   |
| Fargate Support       | Limited                 | Full support             |
| Community             | Very active             | Growing                  |
| Hybrid/Multi-cloud    | Strong support          | AWS-centric              |

Service mesh は EKS clusters の networking architecture に大きな変更をもたらしますが、microservices architecture の複雑さを管理するための強力な tools を提供します。Default EKS networking model との統合は sidecar pattern を通じて行われ、既存の application code を変更せずに advanced networking features を追加できます。Service mesh を採用する際は、performance impact、operational complexity、resource requirements を慎重に考慮し、段階的な approach が推奨されます。

</details>

### 11. Kubernetes Gateway API で L7 load balancing (ALB) に使用される routing resource は何ですか？

A. IngressRoute B. HTTPRoute C. VirtualService D. ServiceRoute

<details>

<summary>回答を表示</summary>

**回答: B. HTTPRoute**

**解説:** Kubernetes Gateway API では、HTTPRoute resource が L7 load balancing に使用されます。HTTPRoute は services へ HTTP/HTTPS traffic を route する rules を定義し、AWS Load Balancer Controller と併用すると ALB を通じて traffic を分散します。

**Gateway API Resource Hierarchy:**

1. **GatewayClass**: load balancer type（例: `amazon-alb`、`amazon-nlb`）を定義します
2. **Gateway**: 実際の load balancer instance（listener ports、TLS settings など）
3. **HTTPRoute**: L7 routing rules（host、path、header-based routing）
4. **TCPRoute**: L4 routing rules（TCP traffic）

**主な HTTPRoute Features:**

* Path and host-based routing
* Native weight-based traffic splitting
* Header and query parameter matching
* 複数の backend services への routing

他の選択肢の問題点:

* **A. IngressRoute**: これは標準の Gateway API resource ではありません。
* **C. VirtualService**: これは Istio service mesh の resource です。
* **D. ServiceRoute**: この resource は存在しません。

</details>

### 12. AWS Load Balancer Controller で Gateway API を有効化するために必要な feature gate flag は何ですか？

A. `--enable-gateway-api` B. `--feature-gates=EnableGatewayAPI=true` C. `--gateway-api-enabled=true` D. `--enable-feature=gateway-api`

<details>

<summary>回答を表示</summary>

**回答: B. `--feature-gates=EnableGatewayAPI=true`**

**解説:** AWS Load Balancer Controller で Gateway API を有効化するには、controller を deploy する際に `--feature-gates=EnableGatewayAPI=true` flag を追加する必要があります。この feature gate により、controller は Gateway API resources（GatewayClass、Gateway、HTTPRoute、TCPRoute など）を watch および process できるようになります。

**Gateway API Activation の完全な前提条件:**

1. AWS Load Balancer Controller v2.13.0 以降を install する
2. `--feature-gates=EnableGatewayAPI=true` flag を追加する
3. Gateway API Standard CRDs を install する
4. Experimental CRDs（TCPRoute などを使用する場合）を install する
5. AWS LBC-specific CRDs を install する

他の選択肢の問題点:

* **A, C, D**: これらの flags は AWS Load Balancer Controller で使用される形式ではなく、誤りです。

</details>

### 13. Gateway API で NLB を通じて L4-level TCP traffic を route するために使用される resource は何ですか？

A. HTTPRoute B. TLSRoute C. TCPRoute D. GRPCRoute

<details>

<summary>回答を表示</summary>

**回答: C. TCPRoute**

**解説:** Gateway API では、TCPRoute resource が L4-level TCP traffic を route するために使用されます。AWS Load Balancer Controller と併用すると、TCPRoute は NLB (Network Load Balancer) を通じて TCP traffic を backend services に forward します。

**TCPRoute Configuration Example:**

```yaml
apiVersion: gateway.networking.k8s.io/v1alpha2
kind: TCPRoute
metadata:
  name: db-route
spec:
  parentRefs:
  - name: my-nlb-gateway
    sectionName: tcp
  rules:
  - backendRefs:
    - name: postgres-service
      port: 5432
```

**Gateway API Routing Resource Usage:**

| Resource  | Protocol   | AWS LB Type |
| --------- | ---------- | ----------- |
| HTTPRoute | HTTP/HTTPS | ALB         |
| TCPRoute  | TCP        | NLB         |
| TLSRoute  | TLS        | NLB         |
| GRPCRoute | gRPC       | ALB         |

他の選択肢の問題点:

* **A. HTTPRoute**: ALB で HTTP/HTTPS L7 traffic に使用されます。
* **B. TLSRoute**: TLS traffic routing 用ですが、TCP-level routing には TCPRoute が適切です。
* **D. GRPCRoute**: gRPC protocol 専用の routing resource です。

</details>

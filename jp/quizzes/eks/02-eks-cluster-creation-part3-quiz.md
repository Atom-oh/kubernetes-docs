# EKS Cluster 作成クイズ - Part 3

このクイズでは、Amazon EKS cluster 作成に関連する高度な Networking、Storage 設定、および Multi-tenancy についての理解を確認します。Cluster Networking、Storage オプション、Multi-tenant 環境設定などのトピックを扱います。

## 基本概念の問題

1. Amazon EKS cluster で pod あたりの IP アドレス数を制限する主な要因は何ですか？
   * A) VPC CIDR block size
   * B) Node instance type
   * C) Cluster's Kubernetes version
   * D) Number of available IP addresses in the subnet

<details>

<summary>解答を表示</summary>

**解答: B) Node instance type**

**説明:** Amazon EKS cluster で pod あたりの IP アドレス数を制限する主な要因は、node の instance type です。Amazon VPC CNI plugin は、各 node の Elastic Network Interfaces (ENIs) と Secondary IP addresses を使用して pod に IP アドレスを割り当てます。各 EC2 instance type は、ENI の最大数と ENI あたりの最大 IP アドレス数が異なり、これによって node 上で実行できる pod の最大数が決まります。

**Instance Type 別の最大 Pod 数の計算:**

pod の最大数は、次の式を使用して計算されます。

```
(Number of ENIs × IP addresses per ENI - 1) + 2
```

ここで:

* 1 を引くのは、primary ENI の primary IP address が node 自体で使用されるためです。
* 2 を足すのは、kube-proxy と aws-node pods が host networking を使用するためです。

**Maximum Pod Count for Common Instance Types:**

| Instance Type | Max ENIs | IPs per ENI | Max Pods |
| ------------- | -------- | ----------- | -------- |
| t3.small      | 3        | 4           | 11       |
| t3.medium     | 3        | 6           | 17       |
| m5.large      | 3        | 10          | 29       |
| m5.xlarge     | 4        | 15          | 58       |
| m5.2xlarge    | 4        | 15          | 58       |
| m5.4xlarge    | 8        | 30          | 234      |
| c5.large      | 3        | 10          | 29       |
| c5.xlarge     | 4        | 15          | 58       |
| r5.large      | 3        | 10          | 29       |
| r5.xlarge     | 4        | 15          | 58       |

**最大 Pod 数の確認方法:**

```bash
# Check maximum pod count for a node
kubectl get nodes -o jsonpath='{.items[*].status.capacity.pods}'

# Or use the max-pods script
curl -s https://raw.githubusercontent.com/awslabs/amazon-eks-ami/master/scripts/max-pods-calculator.sh | bash -s -- --instance-type m5.large
```

**最大 Pod 数を制限する要因:**

1. **Instance Type**:
   * 各 instance type は、ENI の最大数と ENI あたりの IP アドレス数が異なります。
   * より大きな instance type は、一般により多くの ENI と IP アドレスをサポートします。
2. **CNI Configuration**:
   * デフォルトの VPC CNI configuration は、各 pod に full ENI を割り当てるのではなく、Secondary IP addresses を使用します。
   * この動作は custom networking を使用して変更できます。
3.  **Prefix Delegation**:

    * VPC CNI 1.9.0 以降は prefix delegation をサポートしており、各 ENI に /28 CIDR block (16 IPs) を割り当てます。
    * これにより、node あたりの pod の最大数を大幅に増やすことができます。

    ```bash
    kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true
    ```
4.  **Custom max-pods Value**:

    * kubelet の `--max-pods` flag を使用して、node あたりの pod の最大数を制限できます。
    * これは、instance type がサポートする値より低い値に設定できます。

    ```bash
    eksctl create nodegroup \
      --cluster my-cluster \
      --name my-nodegroup \
      --node-type m5.large \
      --nodes 3 \
      --kubelet-extra-args "--max-pods=110"
    ```

**他の選択肢の問題点:**

* **VPC CIDR block size**: VPC CIDR block size は VPC 内で使用可能な IP アドレスの総数を制限しますが、個々の node あたりの pod の最大数を直接制限するものではありません。
* **Cluster's Kubernetes version**: Kubernetes version はサポートされる機能に影響しますが、node あたりの pod の最大数を直接制限するものではありません。
* **Number of available IP addresses in the subnet**: subnet 内で使用可能な IP アドレス数は、その subnet にデプロイできる pod の総数に影響しますが、個々の node あたりの pod の最大数を直接制限するものではありません。

node の instance type は、サポートする ENI 数と ENI あたりの IP アドレス数を通じて、node 上で実行できる pod の最大数を決定する主な要因です。したがって、workload 要件を満たす適切な instance type を選択することが重要です。

</details>

2\. Amazon EKS cluster における pod-to-pod communication のデフォルト network policy は何ですか？ - A) すべての pod-to-pod communication を許可する - B) 同じ namespace 内の pods 間の communication のみを許可する - C) 明示的に許可された pod-to-pod communication のみを許可する - D) すべての pod-to-pod communication をブロックする

<details>

<summary>解答を表示</summary>

**解答: A) すべての pod-to-pod communication を許可する**

**説明:** Amazon EKS cluster における pod-to-pod communication のデフォルト network policy は、すべての pod-to-pod communication を許可することです。デフォルトでは、EKS は network policies を実装しておらず、すべての pods は cluster 内の他のすべての pods と自由に通信できます。これは Kubernetes のデフォルト動作であり、pod-to-pod communication を制限するには network policies を明示的に設定する必要があります。

**EKS におけるデフォルト Networking 動作:**

1. **Default Allow Policy**:
   * デフォルトでは、すべての pods が cluster 内の他のすべての pods と通信できます。
   * namespaces 間の communication も制限なしで許可されます。
   * これは Kubernetes の "flat network" model に従います。
2. **Amazon VPC CNI**:
   * EKS のデフォルト CNI plugin は Amazon VPC CNI です。
   * この plugin は VPC IP addresses を pods に割り当て、VPC 内で直接 routable にします。
   * デフォルトでは network policies を実装しません。

**Network Policies を実装する方法:**

EKS で pod-to-pod communication を制限するには、次の network policy solutions のいずれかを実装する必要があります。

1.  **Calico**:

    ```bash
    # Install Calico
    kubectl create namespace tigera-operator
    helm repo add projectcalico https://docs.projectcalico.org/charts
    helm install calico projectcalico/tigera-operator --namespace tigera-operator
    ```
2.  **Cilium**:

    ```bash
    # Install Cilium
    helm repo add cilium https://helm.cilium.io/
    helm install cilium cilium/cilium --namespace kube-system
    ```
3. **AWS Network Firewall** (VPC level):
   * AWS Network Firewall を使用して VPC level で traffic をフィルタリングできます。
   * これは細かな pod-level control ではなく、subnet-level control を提供します。

**Network Policy の例:**

1.  **Default Deny Policy**:

    ```yaml
    # Block all ingress traffic
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: default-deny-ingress
      namespace: default
    spec:
      podSelector: {}
      policyTypes:
      - Ingress
    ```
2.  **特定の Pods 間の Communication を許可**:

    ```yaml
    # Allow communication only from frontend to backend
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: allow-frontend-to-backend
      namespace: default
    spec:
      podSelector:
        matchLabels:
          app: backend
      ingress:
      - from:
        - podSelector:
            matchLabels:
              app: frontend
        ports:
        - protocol: TCP
          port: 8080
    ```
3.  **Cross-Namespace Communication の制限**:

    ```yaml
    # Allow access only from prod namespace
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: allow-from-prod-namespace
      namespace: default
    spec:
      podSelector:
        matchLabels:
          app: database
      ingress:
      - from:
        - namespaceSelector:
            matchLabels:
              name: prod
        ports:
        - protocol: TCP
          port: 5432
    ```

**Network Policy のベストプラクティス:**

1. **Default Deny Policy を適用**:
   * 明示的に許可されていないすべての traffic をブロックするため、すべての namespaces に default deny policy を適用します。
   * 必要な communication のみを明示的に許可します。
2. **Least Privilege Principle を適用**:
   * pods が必要とする最小限の network access のみを許可します。
   * 特定の ports と protocols のみを許可します。
3. **Namespace Isolation**:
   * namespaces を使用して workloads を論理的に分離します。
   * namespaces 間の communication を明示的に制御します。
4. **Label-Based Policies**:
   * pod labels を使用して細かな network policies を定義します。
   * 一貫した labeling scheme を維持します。

**他の選択肢の問題点:**

* **Allow communication only between pods in the same namespace**: デフォルトでは、EKS は cross-namespace communication を含むすべての pod-to-pod communication を許可します。
* **Allow only explicitly permitted pod-to-pod communication**: これは network policies を実装した後の動作ですが、デフォルト動作ではありません。
* **Block all pod-to-pod communication**: デフォルトでは、EKS は pod-to-pod communication をブロックしません。

EKS のデフォルト network policy は、すべての pod-to-pod communication を許可することです。これは開発およびテスト環境では便利な場合がありますが、本番環境では security を強化するために適切な network policies を実装することが重要です。

</details>

3. Amazon EKS cluster 内の pods が VPC 外部の internet にアクセスするには何が必要ですか？
   * A) Attach an internet gateway to the subnet where the pod is located
   * B) Attach a NAT gateway or NAT instance to the subnet where the pod is located
   * C) Assign a public IP address to the pod
   * D) Associate an Elastic IP address with the pod

<details>

<summary>解答を表示</summary>

**解答: B) Attach a NAT gateway or NAT instance to the subnet where the pod is located**

**説明:** Amazon EKS cluster 内の pods が VPC 外部の internet にアクセスするには、pod が配置されている subnet に NAT gateway または NAT instance が関連付けられている必要があります。これは private subnets 内の pods が internet にアクセスできるようにする標準的な方法です。

**EKS Networking Architecture:**

1. **Private Subnets 内の Pods**:
   * EKS worker nodes は通常、security のため private subnets に配置されます。
   * private subnets 内の pods は internet に直接アクセスできません。
   * NAT gateway または NAT instance を通じて internet にアクセスする必要があります。
2. **Public Subnets 内の Pods**:
   * worker nodes が public subnets にある場合でも、pods はデフォルトで public IP addresses を受け取りません。
   * pods は node の network interface を介した NAT を通じて internet にアクセスします。

**NAT Gateway Configuration:**

```bash
# Create NAT gateway
aws ec2 create-nat-gateway \
  --subnet-id subnet-public1 \
  --allocation-id eipalloc-12345

# Update private subnet routing table
aws ec2 create-route \
  --route-table-id rtb-private \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id nat-12345
```

**VPC Configuration Example Using CloudFormation:**

```yaml
Resources:
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsSupport: true
      EnableDnsHostnames: true
      Tags:
        - Key: Name
          Value: EKS-VPC

  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs ""]
      CidrBlock: 10.0.0.0/24
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: Public-Subnet-1

  PrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs ""]
      CidrBlock: 10.0.2.0/24
      Tags:
        - Key: Name
          Value: Private-Subnet-1

  InternetGateway:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - Key: Name
          Value: EKS-IGW

  VPCGatewayAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  NatGatewayEIP:
    Type: AWS::EC2::EIP
    DependsOn: VPCGatewayAttachment
    Properties:
      Domain: vpc

  NatGateway:
    Type: AWS::EC2::NatGateway
    Properties:
      AllocationId: !GetAtt NatGatewayEIP.AllocationId
      SubnetId: !Ref PublicSubnet1
      Tags:
        - Key: Name
          Value: EKS-NAT-GW

  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: Public-RT

  PublicRoute:
    Type: AWS::EC2::Route
    DependsOn: VPCGatewayAttachment
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  PrivateRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: Private-RT

  PrivateRoute:
    Type: AWS::EC2::Route
    Properties:
      RouteTableId: !Ref PrivateRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      NatGatewayId: !Ref NatGateway
```

**VPC Configuration Using eksctl:**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
vpc:
  cidr: 192.168.0.0/16
  nat:
    gateway: Single  # NAT gateway configuration
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
```

**他の選択肢の問題点:**

* **Attach an internet gateway to the subnet where the pod is located**: internet gateway は public subnets に attached され、private subnets 内の resources が internet にアクセスするには NAT gateway が必要です。さらに、internet gateway だけでは pods が internet にアクセスできません。
* **Assign a public IP address to the pod**: Amazon VPC CNI plugin は pods への public IP addresses の割り当てをサポートしていません。pods は常に private IP addresses を受け取ります。
* **Associate an Elastic IP address with the pod**: Elastic IP address を pod に直接関連付けることはできません。Elastic IP addresses は EC2 instances または network interfaces にのみ関連付けられます。

NAT gateway または NAT instance は、private subnets 内の pods が internet にアクセスできるようにする標準的な方法です。pod の private IP address を NAT gateway の public IP address に変換し、internet communication を可能にします。本番環境では、高可用性のため各 availability zone に NAT gateway をデプロイすることを推奨します。

</details>

4. Amazon EKS cluster で SecurityGroupPolicy を使用して security groups を pods に適用するための要件ではないものはどれですか？
   * A) Amazon VPC CNI plugin version 1.7.7 or later
   * B) ENIConfig resource configuration
   * C) Setting hostNetwork: true on the pod
   * D) Specifying a service account for pods to apply security groups

<details>

<summary>解答を表示</summary>

**解答: C) Setting hostNetwork: true on the pod**

**説明:** "Setting hostNetwork: true on the pod" は、Amazon EKS cluster で SecurityGroupPolicy を使用して security groups を pods に適用するための要件ではありません。実際には、hostNetwork: true の pods には security groups を適用できません。security groups を pods に適用するには、pods が独自の network namespace を使用する必要があります。

**Pod Security Group Feature Requirements:**

1.  **Amazon VPC CNI Plugin Version 1.7.7 or Later**:

    * pod security group feature は Amazon VPC CNI plugin version 1.7.7 以降でサポートされています。
    * 最新 version の使用が推奨されます。

    ```bash
    # Check CNI version
    kubectl describe daemonset aws-node -n kube-system | grep Image

    # Update CNI
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.10.0/config/master/aws-k8s-cni.yaml
    ```
2.  **Pod Security Group Feature を有効化**:

    ```bash
    # Enable pod security group feature
    kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true

    # Or use eksctl
    eksctl utils update-cluster-config \
      --name my-cluster \
      --region us-west-2 \
      --enable-pod-security-groups
    ```
3.  **Security Groups を適用する Pods の Service Account を指定**:

    * SecurityGroupPolicy では、pod selector または service account selector を使用して security groups を適用する pods を指定する必要があります。

    ```yaml
    apiVersion: vpcresources.k8s.aws/v1beta1
    kind: SecurityGroupPolicy
    metadata:
      name: my-security-group-policy
      namespace: default
    spec:
      podSelector:
        matchLabels:
          app: my-app
      securityGroups:
        groupIds:
          - sg-12345
    ```

**Pod Security Group Configuration Examples:**

1.  **Create SecurityGroupPolicy**:

    ```yaml
    apiVersion: vpcresources.k8s.aws/v1beta1
    kind: SecurityGroupPolicy
    metadata:
      name: db-client-policy
      namespace: default
    spec:
      serviceAccountSelector:
        matchLabels:
          role: db-client
      securityGroups:
        groupIds:
          - sg-db-client
    ```
2.  **Create Service Account**:

    ```yaml
    apiVersion: v1
    kind: ServiceAccount
    metadata:
      name: db-client
      namespace: default
      labels:
        role: db-client
    ```
3.  **Deploy Pod**:

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: db-client-pod
    spec:
      serviceAccountName: db-client
      containers:
      - name: db-client
        image: mysql:5.7
        command: ['sleep', '3600']
    ```

**hostNetwork: true の問題点:**

`hostNetwork: true` の Pods は node の network namespace を使用するため、個別の security groups を pod に適用できません。このような pods は node の security groups を継承します。

```yaml
# Security groups cannot be applied to this pod
apiVersion: v1
kind: Pod
metadata:
  name: host-network-pod
spec:
  hostNetwork: true  # Uses the node's network namespace
  containers:
  - name: nginx
    image: nginx
```

**ENIConfig Resource Configuration:**

ENIConfig resources は custom networking を設定する際に必要ですが、pod security groups feature のみを使用する場合の必須要件ではありません。ただし、pod security groups と custom networking を併用する場合は、ENIConfig resources を設定する必要があります。

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  subnet: subnet-12345
  securityGroups:
  - sg-12345
```

**Pod Security Group の制限:**

1. **Resource Limitations**:
   * 各 node には pod security groups 用の追加 ENI が必要です。
   * サポートされる ENI の最大数は instance type によって制限されます。
2. **Compatibility Limitations**:
   * hostNetwork: true の pods には適用できません。
   * hostPort を使用する pods には適用できません。
   * 一部の CNI plugins と互換性がない場合があります。
3. **Performance Impact**:
   * pod ごとに追加 ENI が必要なため、pod startup time が長くなる場合があります。
   * node あたりの pod の最大数が制限される場合があります。

pod security groups feature は、pod level で granular network security を提供する強力な機能です。ただし、この機能は hostNetwork: true の pods には適用できないため、pod security groups を使用するには pods が独自の network namespace を使用する必要があります。

</details>

4\. Amazon EKS cluster で SecurityGroupPolicy を使用して security groups を pods に適用するための要件ではないものは何ですか？ - A) Amazon VPC CNI plugin version 1.7.7 以上 - B) ENIConfig resource configuration - C) pod に hostNetwork: true を設定する - D) security groups が適用される pods の service account を指定する

<details>

<summary>解答を表示</summary>

**解答: C) pod に hostNetwork: true を設定する**

**説明:** Amazon EKS cluster で SecurityGroupPolicy を使用して security groups を pods に適用するための要件ではない選択肢は、"pod に hostNetwork: true を設定する" です。実際には、hostNetwork: true の pods には security groups を適用できません。security groups を pods に適用するには、pods が独自の network namespace を使用する必要があります。

**Pod Security Groups Feature Requirements:**

1.  **Amazon VPC CNI plugin version 1.7.7 or higher**:

    * pod security groups feature は Amazon VPC CNI plugin version 1.7.7 以降でサポートされています。
    * 最新 version の使用が推奨されます。

    ```bash
    # Check CNI version
    kubectl describe daemonset aws-node -n kube-system | grep Image

    # Update CNI
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.10.0/config/master/aws-k8s-cni.yaml
    ```
2.  **pod security groups feature を有効化**:

    ```bash
    # Enable pod security groups feature
    kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true

    # Or use eksctl
    eksctl utils update-cluster-config \
      --name my-cluster \
      --region us-west-2 \
      --enable-pod-security-groups
    ```
3.  **security groups が適用される pods の service account を指定**:

    * SecurityGroupPolicy では、pod selector または service account selector を使用して security groups が適用される pods を指定する必要があります。

    ```yaml
    apiVersion: vpcresources.k8s.aws/v1beta1
    kind: SecurityGroupPolicy
    metadata:
      name: my-security-group-policy
      namespace: default
    spec:
      podSelector:
        matchLabels:
          app: my-app
      securityGroups:
        groupIds:
          - sg-12345
    ```

**Pod Security Group Configuration Examples:**

1.  **Create SecurityGroupPolicy**:

    ```yaml
    apiVersion: vpcresources.k8s.aws/v1beta1
    kind: SecurityGroupPolicy
    metadata:
      name: db-client-policy
      namespace: default
    spec:
      serviceAccountSelector:
        matchLabels:
          role: db-client
      securityGroups:
        groupIds:
          - sg-db-client
    ```
2.  **Create Service Account**:

    ```yaml
    apiVersion: v1
    kind: ServiceAccount
    metadata:
      name: db-client
      namespace: default
      labels:
        role: db-client
    ```
3.  **Deploy Pod**:

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: db-client-pod
    spec:
      serviceAccountName: db-client
      containers:
      - name: db-client
        image: mysql:5.7
        command: ['sleep', '3600']
    ```

**hostNetwork: true の問題点:**

`hostNetwork: true` の Pods は node の network namespace を使用するため、個別の security groups を pod に適用できません。このような pods は node の security groups を継承します。

```yaml
# Security groups cannot be applied to this pod
apiVersion: v1
kind: Pod
metadata:
  name: host-network-pod
spec:
  hostNetwork: true  # Uses the node's network namespace
  containers:
  - name: nginx
    image: nginx
```

**ENIConfig Resource Configuration:**

ENIConfig resources は custom networking を設定する際に必要ですが、pod security groups feature のみを使用する場合の必須要件ではありません。ただし、pod security groups と custom networking を併用する場合は、ENIConfig resources を設定する必要があります。

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  subnet: subnet-12345
  securityGroups:
  - sg-12345
```

**Pod Security Group Limitations:**

1. **Resource Limitations**:
   * 各 node には pod security groups 用の追加 ENI が必要です。
   * サポートされる ENI の最大数は instance type によって制限されます。
2. **Compatibility Limitations**:
   * hostNetwork: true の pods には適用できません。
   * hostPort を使用する pods には適用できません。
   * 一部の CNI plugins と互換性がない場合があります。
3. **Performance Impact**:
   * pod ごとに追加 ENI が必要なため、pod startup time が長くなる場合があります。
   * node あたりの pod の最大数が制限される場合があります。

pod security groups feature は、pod level で granular network security を提供する強力な機能です。ただし、この機能は hostNetwork: true の pods には適用できないため、pod security groups を使用するには pods が独自の network namespace を使用する必要があります。

</details>

5. Amazon EKS cluster における Prefix Delegation feature の主な利点は何ですか？
   * A) Improved communication speed between pods
   * B) Increased maximum number of pods per node
   * C) Ability to assign public IP addresses to pods
   * D) Enhanced pod network isolation

<details>

<summary>解答を表示</summary>

**解答: B) Increased maximum number of pods per node**

**説明:** Amazon EKS cluster における Prefix Delegation feature の主な利点は、node あたりの pod の最大数を増やすことです。この feature は、各 Elastic Network Interface (ENI) に個別の IP アドレスではなく /28 CIDR blocks (16 IP addresses) を割り当て、node がサポートできる pod の最大数を大幅に増やします。

**Prefix Delegation の仕組み:**

1. **Default VPC CNI Behavior**:
   * デフォルトでは、VPC CNI は各 pod に対して ENI から Secondary IP addresses を割り当てます。
   * 各 EC2 instance type には、ENI の最大数と ENI あたりの IP アドレス数に制限があります。
   * これにより node あたりの pod の最大数が制限されます。
2. **Prefix Delegation Behavior**:
   * prefix delegation が有効な場合、個別の IP アドレスではなく /28 CIDR blocks (16 IPs) が各 ENI に割り当てられます。
   * これにより、各 ENI がサポートできる IP アドレス数が大幅に増えます。
   * その結果、node あたりの pod の最大数が増加します。

**Prefix Delegation の有効化:**

```bash
# Enable prefix delegation
kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true

# Check prefix delegation status
kubectl describe daemonset aws-node -n kube-system | grep ENABLE_PREFIX_DELEGATION
```

**Prefix Delegation の利点:**

1. **Node あたりの最大 Pods 数の増加**:
   * prefix delegation を使用すると、node あたりの pod の最大数が大幅に増加します。
   * たとえば、m5.large instance の場合:
     * Default configuration: maximum 29 pods
     * With prefix delegation enabled: over 110 pods maximum
2. **IP Address Efficiency**:
   * 大規模 clusters で IP アドレス使用を最適化します。
   * VPC CIDR ranges が限られている環境で有用です。
3. **Node Resource Utilization の向上**:
   * より多くの pods を実行することで node resource utilization が向上します。
   * cluster cost optimization に役立ちます。

**Prefix Delegation の制限:**

1. **EC2 Instance Support**:
   * Nitro-based instances のみが prefix delegation をサポートします。
   * 古い世代の instances では使用できません。
2. **VPC CNI Version Requirements**:
   * VPC CNI version 1.9.0 以上が必要です。
   * この feature は以前の versions では使用できません。
3. **Subnet Size Requirements**:
   * 十分な IP address space を持つ subnets が必要です。
   * 小さな subnets では IP addresses がすぐに枯渇する可能性があります。
4. **Migration Considerations**:
   * 既存の clusters で有効にした場合、新しい pods のみが prefix delegation を使用します。
   * すべての pods に適用するには、既存の pods を再起動する必要があります。

**Prefix Delegation Configuration Example:**

```yaml
# eksctl configuration file
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
managedNodeGroups:
  - name: ng-1
    instanceType: m5.large
    minSize: 2
    maxSize: 5
    disableIMDSv1: true
iam:
  withOIDC: true
addons:
  - name: vpc-cni
    version: latest
    configurationValues: |
      {
        "env": {
          "ENABLE_PREFIX_DELEGATION": "true"
        }
      }
```

**他の選択肢の問題点:**

* **Improved communication speed between pods**: Prefix delegation は pod-to-pod communication speed に直接影響しません。Pod communication performance は主に network infrastructure と CNI implementation によって決まります。
* **Ability to assign public IP addresses to pods**: Prefix delegation は pods に public IP addresses を割り当てる機能を提供しません。VPC CNI は常に private IP addresses を pods に割り当てます。
* **Enhanced pod network isolation**: Prefix delegation は pod network isolation とは関係ありません。Network isolation は network policies または security groups を通じて実装されます。

Prefix delegation は、node あたりの pod の最大数を増やし、cluster density と efficiency を向上させる強力な feature です。大規模 clusters や高密度 workloads を実行する環境で特に有用です。

</details>

6. Amazon EKS cluster で CoreDNS をカスタマイズする正しい方法は何ですか？
   * A) Modify CoreDNS settings in the AWS Management Console
   * B) Modify the CoreDNS ConfigMap
   * C) Specify CoreDNS configuration during EKS cluster creation
   * D) Update CoreDNS add-on parameters using the AWS CLI

<details>

<summary>解答を表示</summary>

**解答: B) Modify the CoreDNS ConfigMap**

**説明:** Amazon EKS cluster で CoreDNS をカスタマイズする正しい方法は、CoreDNS ConfigMap を変更することです。CoreDNS は Kubernetes の cluster DNS server であり、ConfigMap を通じて設定されます。EKS では、`coredns` ConfigMap を変更することで CoreDNS の動作をカスタマイズできます。

**CoreDNS ConfigMap を変更する方法:**

1.  **現在の ConfigMap を確認**:

    ```bash
    kubectl get configmap coredns -n kube-system -o yaml
    ```
2.  **ConfigMap を編集**:

    ```bash
    kubectl edit configmap coredns -n kube-system
    ```
3.  **または Patch を適用**:

    ```bash
    kubectl patch configmap coredns -n kube-system --type=merge -p '{"data":{"Corefile":".:53 {\n    errors\n    health {\n        lameduck 5s\n    }\n    ready\n    kubernetes cluster.local in-addr.arpa ip6.arpa {\n        pods insecure\n        fallthrough in-addr.arpa ip6.arpa\n        ttl 30\n    }\n    prometheus :9153\n    forward . /etc/resolv.conf\n    cache 30\n    loop\n    reload\n    loadbalance\n    # Add custom settings\n    hosts {\n        10.0.0.1 example.com\n        fallthrough\n    }\n}"}}'
    ```

**一般的な CoreDNS カスタマイズケース:**

1.  **Custom DNS Records の追加**:

    ```
    hosts {
        10.0.0.1 example.com
        10.0.0.2 api.example.com
        fallthrough
    }
    ```
2.  **特定 Domains 向け Forwarding の設定**:

    ```
    forward example.org 10.0.0.1:53
    ```
3.  **DNS Caching の調整**:

    ```
    cache {
        success 10000
        denial 5000
        prefetch 10 10 10%
    }
    ```
4.  **Logging の設定**:

    ```
    log {
        class error
    }
    ```
5.  **Autopath の無効化**:

    ```
    kubernetes cluster.local in-addr.arpa ip6.arpa {
        pods insecure
        fallthrough in-addr.arpa ip6.arpa
        ttl 30
        autopath off
    }
    ```

**CoreDNS 変更後の適用:**

ConfigMap を変更した後、変更を適用するために CoreDNS pods を再起動する必要があります。

```bash
# Check CoreDNS pods
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Restart CoreDNS pods
kubectl rollout restart deployment coredns -n kube-system

# Verify changes are applied
kubectl logs -n kube-system -l k8s-app=kube-dns
```

**CoreDNS Performance Optimization:**

1.  **Auto-scaling の設定**:

    ```yaml
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    metadata:
      name: coredns-autoscaler
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
2.  **Resource Requests and Limits の調整**:

    ```bash
    kubectl patch deployment coredns -n kube-system --type=json -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources", "value": {"requests": {"cpu": "100m", "memory": "70Mi"}, "limits": {"cpu": "200m", "memory": "170Mi"}}}]'
    ```

**他の選択肢の問題点:**

* **Modify CoreDNS settings in the AWS Management Console**: AWS Management Console は CoreDNS settings を直接変更する interface を提供していません。
* **Specify CoreDNS configuration during EKS cluster creation**: 詳細な CoreDNS configuration は EKS cluster 作成時に指定できません。cluster 作成後に ConfigMap を変更する必要があります。
* **Update CoreDNS add-on parameters using the AWS CLI**: AWS CLI を使用して CoreDNS add-on version を更新することはできますが、詳細な configuration は変更できません。Configuration changes は ConfigMap を通じて行う必要があります。

```bash
# Update CoreDNS add-on version (not configuration change)
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name coredns \
  --addon-version v1.8.7-eksbuild.2 \
  --resolve-conflicts PRESERVE
```

CoreDNS ConfigMap の変更は、EKS cluster で DNS settings をカスタマイズする標準的な方法です。これにより、custom DNS records の追加、特定 domains 向け forwarding の設定、caching behavior の調整など、さまざまなカスタマイズが可能になります。

</details>

7\. Amazon EKS cluster で multi-tenancy を実装する最も効果的な方法は何ですか？ - A) tenant ごとに別々の EKS clusters を作成する - B) tenant ごとに別々の namespaces を使用し、RBAC、network policies、resource quotas を適用する - C) tenant ごとに別々の node groups を作成し、node selectors を使用する - D) tenant ごとに別々の VPCs を使用する

<details>

<summary>解答を表示</summary>

**解答: B) tenant ごとに別々の namespaces を使用し、RBAC、network policies、resource quotas を適用する**

**説明:** Amazon EKS cluster で multi-tenancy を実装する最も効果的な方法は、tenant ごとに別々の namespaces を使用し、RBAC (Role-Based Access Control)、network policies、resource quotas を適用することです。この approach は、resource sharing を可能にしながら、単一 cluster 内で複数 tenants を効率的に分離します。

**Namespace-Based Multi-Tenancy の実装:**

1.  **各 Tenant 用の Namespaces を作成**:

    ```bash
    # Create namespaces for each tenant
    kubectl create namespace tenant-a
    kubectl create namespace tenant-b
    ```
2.  **RBAC を設定**:

    ```yaml
    # Create tenant role
    apiVersion: rbac.authorization.k8s.io/v1
    kind: Role
    metadata:
      name: tenant-full-access
      namespace: tenant-a
    rules:
    - apiGroups: ["", "apps", "batch"]
      resources: ["*"]
      verbs: ["*"]
    ---
    # Bind role to tenant users
    apiVersion: rbac.authorization.k8s.io/v1
    kind: RoleBinding
    metadata:
      name: tenant-a-access
      namespace: tenant-a
    subjects:
    - kind: Group
      name: tenant-a-users
      apiGroup: rbac.authorization.k8s.io
    roleRef:
      kind: Role
      name: tenant-full-access
      apiGroup: rbac.authorization.k8s.io
    ```
3.  **Network Policies を適用**:

    ```yaml
    # Restrict communication between tenants
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    ```

metadata: name: deny-cross-tenant-traffic namespace: tenant-a spec: podSelector: {} policyTypes: - Ingress - Egress ingress: - from: - namespaceSelector: matchLabels: name: tenant-a egress: - to: - namespaceSelector: matchLabels: name: tenant-a - to: - namespaceSelector: matchLabels: name: kube-system

````

4. **Resource Quota Configuration**:
 ```yaml
 # Tenant Resource Quota
 apiVersion: v1
 kind: ResourceQuota
 metadata:
   name: tenant-quota
   namespace: tenant-a
 spec:
   hard:
     requests.cpu: "10"
     requests.memory: 20Gi
     limits.cpu: "20"
     limits.memory: 40Gi
     pods: "50"
     services: "20"
     persistentvolumeclaims: "30"
     secrets: "100"
     configmaps: "100"
````

5.  **LimitRange Configuration**:

    ```yaml
    # Default resource limit settings
    apiVersion: v1
    kind: LimitRange
    metadata:
      name: tenant-limits
      namespace: tenant-a
    spec:
      limits:
      - default:
          cpu: 500m
          memory: 512Mi
        defaultRequest:
          cpu: 100m
          memory: 256Mi
        type: Container
    ```

**Namespace-Based Multi-Tenancy の利点:**

1. **Resource Efficiency**:
   * 複数 tenants が単一 cluster を共有するため、resource utilization が向上します。
   * control plane costs が削減されます。
2. **Ease of Management**:
   * 単一 cluster を管理することで operational overhead が減少します。
   * 集中型の monitoring と logging が可能です。
3. **Flexibility**:
   * tenants の追加と削除が簡単です。
   * tenant-specific policies を簡単に適用できます。
4. **Cost Efficiency**:
   * cluster overhead が複数 tenants 間で共有されます。
   * resource utilization の向上により cost savings につながります。

**Namespace-Based Multi-Tenancy の欠点:**

1. **Limited Isolation Level**:
   * Namespaces は完全な physical isolation ではなく、logical isolation のみを提供します。
   * kernel-level vulnerabilities にさらされる可能性があります。
2. **Resource Contention**:
   * tenants 間で resource contention が発生する可能性があります。
   * Noisy Neighbor problems が発生する場合があります。
3. **Security Risks**:
   * cluster-level privilege escalation のリスクがあります。
   * container escape vulnerabilities にさらされる可能性があります。

**その他の Multi-Tenancy Approaches:**

1. **Cluster-Based Multi-Tenancy (Separate EKS Cluster per Tenant)**:
   * 最も強力な isolation を提供します
   * management overhead が増加します
   * costs が増加します
   * 大規模 enterprise environments や規制の厳しい industries に適しています
2. **Node-Based Multi-Tenancy (Separate Node Group per Tenant)**:
   * 中程度の isolation level を提供します
   * tenant ごとの node-level customization が可能です
   * resource utilization が低下します
   * security requirements が高いが cost も考慮する必要がある場合に適しています
3. **Hybrid Approach**:
   * 重要な tenants には dedicated clusters を提供します
   * 重要度の低い tenants は shared cluster 内の namespace で分離します
   * flexibility と cost efficiency のバランスを取ります

**他の選択肢の問題点:**

* **Creating a Separate EKS Cluster per Tenant**: 最も強力な isolation を提供しますが、management overhead と costs が大幅に増加します。tenants が多い場合、scalability issues が発生する可能性があります。
* **Creating Separate Node Groups per Tenant and Using Node Selectors**: node-level isolation を提供しますが、resource utilization が低下し、management が複雑になる可能性があります。また、node groups だけでは完全な isolation は提供されません。
* **Using Separate VPCs per Tenant**: EKS clusters は単一 VPC 内に作成されるため、tenant ごとに別々の VPCs を使用するには tenant ごとに別々の clusters を作成する必要があります。これにより management overhead と costs が大幅に増加します。

Namespace-based multi-tenancy は、ほとんどの use cases において isolation、ease of management、cost efficiency の最適なバランスを提供します。ただし、security requirements が非常に高い場合は cluster-based multi-tenancy を検討する必要があります。

</details>

8. Amazon EKS cluster の node group で instance type を選択する際に考慮すべき要因ではないものはどれですか？
   * A) CPU and memory requirements of the workload
   * B) Cost optimization
   * C) Kubernetes version of the cluster
   * D) Required pod density

<details>

<summary>解答を表示</summary>

**解答: C) Kubernetes version of the cluster**

**説明:** Amazon EKS cluster の node group で instance type を選択する際に考慮すべきではない要因は、"Kubernetes version of the cluster" です。Kubernetes version はサポートされる機能に影響しますが、node group の instance type 選択には直接影響しません。Instance type は主に workload requirements、cost、pod density、およびその他の要因によって決まります。

**Node Group Instance Types 選択時に考慮すべき実際の要因:**

1. **CPU and Memory Requirements of the Workload**:
   * workload の resource requirements に一致する instance types を選択します
   * CPU-intensive workloads: c5、c6g などの Compute-optimized instances
   * Memory-intensive workloads: r5、r6g などの Memory-optimized instances
   * Balanced workloads: m5、m6g などの General-purpose instances
   * GPU workloads: p3、g4dn などの Accelerated computing instances
2. **Cost Optimization**:
   * On-Demand vs Spot instances
   * Reserved Instances または Savings Plans
   * ARM-based Graviton instances (例: m6g、c6g) による cost savings
   * 適切なサイズの instances の選択 (overprovisioning の回避)
3. **Required Pod Density**:
   * サポートされる pod の最大数は instance type によって異なります
   * instance type ごとの ENI 数と ENI あたりの IP アドレス数を考慮します
   * high-density workloads の場合、より多くの ENI と IP アドレスをサポートする instance types を選択します
4. **Networking Requirements**:
   * Network bandwidth requirements
   * Enhanced networking support (ENA、EFA など)
   * Network performance は instance type によって異なります
5. **Storage Requirements**:
   * local instance storage が必要かどうか (例: i3、d3 instances)
   * EBS optimization support
   * Storage throughput と IOPS requirements
6. **Availability Requirements**:
   * instance types の Regional availability
   * Spot instances 使用時の interruption possibility
   * Availability Zone ごとの instance type availability

**Instance Type Selection Examples:**

1.  **Web Application Servers**:

    ```yaml
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig
    metadata:
      name: my-cluster
      region: us-west-2
    managedNodeGroups:
      - name: web-servers
        instanceType: m5.large
        minSize: 2
        maxSize: 10
        labels:
          role: web
    ```
2.  **Database Workloads**:

    ```yaml
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig
    metadata:
      name: my-cluster
      region: us-west-2
    managedNodeGroups:
      - name: database-nodes
        instanceType: r5.xlarge
        minSize: 3
        maxSize: 5
        labels:
          role: database
    ```
3.  **Batch Processing Workloads**:

    ```yaml
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig
    metadata:
      name: my-cluster
      region: us-west-2
    managedNodeGroups:
      - name: batch-processors
        instanceType: c5.2xlarge
        minSize: 0
        maxSize: 20
        labels:
          role: batch
    ```
4.  **Cost-Optimized Workloads**:

    ```yaml
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig
    metadata:
      name: my-cluster
      region: us-west-2
    managedNodeGroups:
      - name: spot-workers
        instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5ad.large"]
        minSize: 2
        maxSize: 10
        spot: true
        labels:
          lifecycle: spot
    ```

**Kubernetes Version と Instance Types の関係:**

Kubernetes version は cluster に次のような影響を与えますが、instance type selection には直接影響しません。

1. **Supported Features**:
   * 新しい Kubernetes versions は新しい features を提供します。
   * 一部の features は特定の versions でのみ利用できます。
2. **API Compatibility**:
   * 新しい versions では一部の APIs が変更または削除される場合があります。
   * application が特定の APIs に依存している場合、version selection は重要です。
3. **Security Patches**:
   * 最新 versions には最新の security patches が含まれます。
   * 古い versions は security vulnerabilities にさらされる可能性があります。
4. **Support Period**:
   * 各 Kubernetes version は限られた期間サポートされます。
   * EKS は各 version を約 14 か月間サポートします。

Instance type selection は主に workload resource requirements、cost optimization、pod density、およびその他の要因によって決まり、Kubernetes version とは直接関係ありません。したがって、"Kubernetes version of the cluster" は node group の instance type を選択する際の主要な考慮要因ではありません。

</details>

9\. Amazon EKS cluster で node group updates 中の pod disruption を最小限に抑える最も効果的な方法は何ですか？ - A) rolling update strategy を使用する - B) PodDisruptionBudget を設定する - C) node group update 前にすべての pods を手動で移行する - D) blue/green deployment strategy を使用する

<details>

<summary>解答を表示</summary>

**解答: B) PodDisruptionBudget を設定する**

**説明:** Amazon EKS cluster で node group updates 中の pod disruption を最小限に抑える最も効果的な方法は、PodDisruptionBudget (PDB) を設定することです。PDB は voluntary disruptions 中に同時に中断できる pods の数を制限し、application availability を確保します。node group updates は voluntary disruptions とみなされるため、PDB を通じて updates 中の application availability を維持できます。

**PodDisruptionBudget の仕組み:**

1. **PDB Definition**:
   * `minAvailable`: 常に利用可能でなければならない pods の最小数または割合を指定します
   * `maxUnavailable`: 同時に unavailable になり得る pods の最大数または割合を指定します
   * これら 2 つの options のうち 1 つだけを指定する必要があります
2. **PDB Application**:
   * Kubernetes は node draining 中に PDB を尊重します
   * PDB に違反する場合、draining process は一時停止します
   * 新しい pods が他の nodes で実行開始されると draining が続行されます

**PodDisruptionBudget Examples:**

```yaml
# Ensure at least 2 pods are always available
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: default
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```

```yaml
# Limit only up to 50% of pods to be unavailable simultaneously
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: default
spec:
  maxUnavailable: 50%
  selector:
    matchLabels:
      app: my-app
```

**EKS Node Group Update Process:**

1. **Update Start**:
   * 新しい nodes を作成します
   * 新しい nodes が cluster に参加します
2. **Node Draining**:
   * 既存 nodes に cordoning を適用します (新しい pod scheduling を防止)
   * 既存 nodes から pods を drain します (pods を移行)
   * PDB を尊重しながら pods を移行します
3. **Node Termination**:
   * すべての pods が移行された後、nodes を terminate します
   * 次の node に対して process を繰り返します

**PDB Configuration Best Practices:**

1. **適切な Replica Count を設定**:
   * PDB が効果的に機能するには十分な replicas が必要です
   * 少なくとも 3 replicas が推奨されます
2. **適切な PDB Values を選択**:
   * application characteristics に適した values を選択します
   * 制限が厳しすぎる values は updates を遅延させる可能性があります
   * 緩すぎる values は availability に影響する可能性があります
3. **すべての Critical Workloads に PDB を適用**:
   * Stateful applications
   * User-facing services
   * System components
4. **PDB をテスト**:
   * updates 前に PDB behavior をテストします
   * draining simulation で availability を検証します

**Node Group Update Configuration:**

```bash
# Modify managed node group update configuration
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --update-config '{"maxUnavailable": 1}'

# Or using eksctl
eksctl update nodegroup \
  --cluster my-cluster \
  --name my-nodegroup \
  --max-unavailable 1
```

**他の選択肢の問題点:**

* **Using a Rolling Update Strategy**: EKS managed node groups はすでにデフォルトで rolling update strategy を使用します。しかし、rolling updates だけでは pod disruption を制御できず、効果を出すには PDB と併用する必要があります。
* **Manually Migrating All Pods Before Node Group Update**: これは時間がかかり、error-prone な manual process です。また、大規模 clusters には実用的ではありません。
* **Using a Blue/Green Deployment Strategy**: Blue/green deployment は、新しい node group を作成し、workloads を移行してから既存の node group を削除します。これは効果的な strategy ですが、resource duplication による costs の増加と implementation の複雑さという欠点があります。また、PDB と併用するのが最適です。

PodDisruptionBudget は、node group updates 中の pod disruption を制御する Kubernetes-native な方法であり、application availability を確保しながら node groups を安全に更新できます。したがって、node group updates 中の pod disruption を最小限に抑える最も効果的な方法は PodDisruptionBudget を設定することです。

</details>

10. Amazon EKS cluster で node groups の Auto Scaling behavior を制御するために使用されないものはどれですか？
    * A) Cluster Autoscaler
    * B) Karpenter
    * C) Horizontal Pod Autoscaler
    * D) Vertical Pod Autoscaler

<details>

<summary>解答を表示</summary>

**解答: D) Vertical Pod Autoscaler**

**説明:** Amazon EKS cluster で node groups の Auto Scaling behavior を制御するために使用されないものは Vertical Pod Autoscaler (VPA) です。VPA は pods の CPU と memory requests を自動調整するために使用されますが、node groups の size を調整するためには使用されません。Node group Auto Scaling は主に Cluster Autoscaler、Karpenter、および Horizontal Pod Autoscaler (HPA) によって間接的に制御されます。

**Node Group Auto Scaling Tools:**

1.  **Cluster Autoscaler**:

    * node groups の size を自動調整する Kubernetes component
    * pods を schedule できない場合に nodes を追加します
    * nodes が十分に利用されていない場合に nodes を削除します
    * AWS Auto Scaling Groups と統合されます

    ```yaml
    # Cluster Autoscaler Deployment
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: cluster-autoscaler
      namespace: kube-system
    spec:
      replicas: 1
      selector:
        matchLabels:
          app: cluster-autoscaler
      template:
        metadata:
          labels:
            app: cluster-autoscaler
        spec:
          serviceAccountName: cluster-autoscaler
          containers:
          - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.23.0
            name: cluster-autoscaler
            command:
            - ./cluster-autoscaler
            - --v=4
            - --stderrthreshold=info
            - --cloud-provider=aws
            - --skip-nodes-with-local-storage=false
            - --expander=least-waste
            - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/my-cluster
    ```
2.  **Karpenter**:

    * AWS の open-source node provisioning project
    * workload requirements に最適な instance types を選択します
    * 高速な node provisioning (数秒単位)
    * Cost optimization と unified lifecycle management

    ```yaml
    # Karpenter Provisioner
    apiVersion: karpenter.sh/v1alpha5
    kind: NodePool
    metadata:
      name: default
    spec:
      template:
        spec:
          requirements:
            - key: karpenter.sh/capacity-type
              operator: In
              values: ["spot", "on-demand"]
          nodeClassRef:
            name: default-class
      limits:
        cpu: 1000
          memory: 1000Gi
      provider:
        subnetSelector:
          karpenter.sh/discovery: "true"
        securityGroupSelector:
          karpenter.sh/discovery: "true"
      ttlSecondsAfterEmpty: 30
    ```
3.  **Horizontal Pod Autoscaler (HPA)**:

    * pod replicas の数を自動調整します
    * CPU、memory、または custom metrics に基づきます
    * node group Auto Scaling を間接的に trigger できます
    * Cluster Autoscaler または Karpenter と連携します

    ```yaml
    # Horizontal Pod Autoscaler
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    metadata:
      name: my-app-hpa
    spec:
      scaleTargetRef:
        apiVersion: apps/v1
        kind: Deployment
        name: my-app
      minReplicas: 2
      maxReplicas: 10
      metrics:
      - type: Resource
        resource:
          name: cpu
          target:
            type: Utilization
            averageUtilization: 70
    ```

**Vertical Pod Autoscaler (VPA):**

VPA は pods の CPU と memory requests を自動調整するために使用されますが、node groups の size を直接調整しません。

```yaml
# Vertical Pod Autoscaler
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 50Mi
      maxAllowed:
        cpu: 1
        memory: 500Mi
      controlledResources: ["cpu", "memory"]
```

VPA は次の features を提供します。

* pod resource requests の自動調整
* resource usage に基づく recommendations
* pod restarts を通じた resource request updates

ただし、VPA は node groups の size を直接調整せず、pod level の resource allocation にのみ影響します。

**Node Group Auto Scaling Strategies:**

1. **Reactive Scaling**:
   * Cluster Autoscaler を使用します
   * pods を schedule できない場合に nodes を追加します
   * resource utilization が低い場合に nodes を削除します
   * predictable workloads に適しています
2. **Predictive Scaling**:
   * AWS Auto Scaling predictive scaling を使用します
   * historical patterns に基づいて将来の demand を予測します
   * demand が増加する前に capacity を確保します
   * periodic patterns を持つ workloads に適しています
3. **Event-driven Scaling**:
   * KEDA (Kubernetes Event-driven Autoscaling) を使用します
   * external events または metrics に基づいて scaling します
   * queue length、event count などに基づいて scaling します
   * batch processing、event processing workloads に適しています

**他の選択肢の説明:**

* **Cluster Autoscaler**: pod scheduling requirements に基づいて nodes を追加または削除し、node group Auto Scaling を直接制御する Kubernetes component です。
* **Karpenter**: workload requirements に合致する最適な instances を迅速に provision する AWS open-source node provisioning project です。Cluster Autoscaler の代替として使用できます。
* **Horizontal Pod Autoscaler**: pod replicas の数を自動調整し、より多くの pods が作成されたときに Cluster Autoscaler または Karpenter が node group size を調整するよう間接的に trigger できます。

Vertical Pod Autoscaler は pod resource requests を調整するために使用されますが、node group size を直接調整しません。したがって、node group Auto Scaling behavior を制御するために使用されないものは Vertical Pod Autoscaler です。

</details>

## ハンズオン演習

### 演習 1: EKS Cluster における Network Policies の実装

**シナリオ:** あなたは会社の security engineer で、EKS cluster 内の microservices 間の network traffic を制限する必要があります。具体的には、frontend service のみが backend API にアクセスでき、database は backend API からのみアクセス可能である必要があります。

**要件:**

1. Calico network policy engine をインストールする
2. default deny policy を実装する
3. frontend から backend への traffic を許可する
4. backend から database への traffic を許可する
5. policies をテストする

**解答:**

<details>

<summary>解答例を表示</summary>

**1. Install Calico Network Policy Engine**

```bash
# Install Tigera Operator
kubectl create namespace tigera-operator
helm repo add projectcalico https://docs.projectcalico.org/charts
helm install calico projectcalico/tigera-operator --namespace tigera-operator

# Verify installation
kubectl get pods -n calico-system
```

**2. Create Namespace and Sample Applications**

```bash
# Create namespace
kubectl create namespace microservices

# Deploy frontend
cat > frontend.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: microservices
  labels:
    app: frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: microservices
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 80
EOF

kubectl apply -f frontend.yaml

# Deploy backend
cat > backend.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: microservices
  labels:
    app: backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: httpd
        image: httpd:alpine
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: microservices
spec:
  selector:
    app: backend
  ports:
  - port: 80
    targetPort: 80
EOF

kubectl apply -f backend.yaml

# Deploy database
cat > database.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: database
  namespace: microservices
  labels:
    app: database
spec:
  replicas: 1
  selector:
    matchLabels:
      app: database
  template:
    metadata:
      labels:
        app: database
    spec:
      containers:
      - name: postgres
        image: postgres:13-alpine
        env:
        - name: POSTGRES_PASSWORD
          value: "password"
        ports:
        - containerPort: 5432
---
apiVersion: v1
kind: Service
metadata:
  name: database
  namespace: microservices
spec:
  selector:
    app: database
  ports:
  - port: 5432
    targetPort: 5432
EOF

kubectl apply -f database.yaml

# Verify deployment
kubectl get pods -n microservices
kubectl get services -n microservices
```

**3. Implement Default Deny Policy**

```bash
# Create default deny policy
cat > default-deny.yaml << EOF
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: microservices
spec:
  selector: all()
  types:
  - Ingress
  - Egress
EOF

kubectl apply -f default-deny.yaml
```

**4. Allow Traffic from Frontend to Backend**

```bash
# Policy to allow traffic from frontend to backend
cat > frontend-to-backend.yaml << EOF
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: frontend-to-backend
  namespace: microservices
spec:
  selector: app == 'backend'
  types:
  - Ingress
  ingress:
  - action: Allow
    source:
      selector: app == 'frontend'
    destination:
      ports:
      - 80
EOF

kubectl apply -f frontend-to-backend.yaml

# Allow frontend egress to external DNS and API
cat > frontend-egress.yaml << EOF
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: frontend-egress
  namespace: microservices
spec:
  selector: app == 'frontend'
  types:
  - Egress
  egress:
  - action: Allow
    destination:
      selector: app == 'backend'
      ports:
      - 80
  # Allow DNS access
  - action: Allow
    destination:
      selector: k8s-app == 'kube-dns'
      ports:
      - 53
EOF

kubectl apply -f frontend-egress.yaml
```

**5. Allow Traffic from Backend to Database**

```bash
# Policy to allow traffic from backend to database
cat > backend-to-database.yaml << EOF
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: backend-to-database
  namespace: microservices
spec:
  selector: app == 'database'
  types:
  - Ingress
  ingress:
  - action: Allow
    source:
      selector: app == 'backend'
    destination:
      ports:
      - 5432
EOF

kubectl apply -f backend-to-database.yaml

# Allow backend egress to external DNS and database
cat > backend-egress.yaml << EOF
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: backend-egress
  namespace: microservices
spec:
  selector: app == 'backend'
  types:
  - Egress
  egress:
  - action: Allow
    destination:
      selector: app == 'database'
      ports:
      - 5432
  # Allow DNS access
  - action: Allow
    destination:
      selector: k8s-app == 'kube-dns'
      ports:
      - 53
EOF

kubectl apply -f backend-egress.yaml
```

**6. Test Policies**

```bash
# Get frontend pod name
FRONTEND_POD=$(kubectl get pods -n microservices -l app=frontend -o jsonpath='{.items[0].metadata.name}')

# Get backend pod name
BACKEND_POD=$(kubectl get pods -n microservices -l app=backend -o jsonpath='{.items[0].metadata.name}')

# Get database pod name
DATABASE_POD=$(kubectl get pods -n microservices -l app=database -o jsonpath='{.items[0].metadata.name}')

# Test connection from frontend to backend (should succeed)
kubectl exec -it $FRONTEND_POD -n microservices -- wget -O- --timeout=2 http://backend

# Test connection from frontend to database (should fail)
kubectl exec -it $FRONTEND_POD -n microservices -- nc -zv database 5432

# Test connection from backend to database (should succeed)
kubectl exec -it $BACKEND_POD -n microservices -- nc -zv database 5432

# Test connection from backend to external site (should fail)
kubectl exec -it $BACKEND_POD -n microservices -- wget -O- --timeout=2 https://www.example.com
```

**7. Network Policy Visualization (Optional)**

```bash
# Install Calico network policy visualization tool
kubectl apply -f https://raw.githubusercontent.com/tigera/ccol/master/manifests/tigera-policies-viewer/tigera-policies-viewer.yaml

# Set up port forwarding
kubectl port-forward -n tigera-policies-viewer svc/tigera-policies-viewer 8080:8080

# Access http://localhost:8080 in browser to visualize policies
```

この演習を通じて、EKS cluster 内の microservices 間の network traffic を制限するために Calico を使用する方法を学びました。default deny policies を実装し、必要な traffic のみを明示的に許可することで、principle of least privilege を適用しました。これらの network policies は、cluster 内の services 間の communication を制限し、潜在的な attack surface を減らすことで security の向上に役立ちます。

</details>

\### 演習 2: EKS Cluster における IRSA と S3 Access の設定

**シナリオ:** あなたは会社の DevOps engineer で、EKS cluster で実行されている applications が S3 bucket に安全にアクセスする必要があります。security best practices に従い、node IAM role を共有する代わりに、IRSA (IAM Roles for Service Accounts) を使用して特定の pods に必要な permissions のみを付与したいと考えています。

**要件:**

1. OIDC provider を EKS cluster に関連付ける
2. S3 access permissions を持つ IAM role を作成する
3. Kubernetes service account を作成し、IAM role を関連付ける
4. service account を使用する pod をデプロイする
5. S3 access をテストする

**解答:**

<details>

<summary>解答例を表示</summary>

**1. Associate OIDC Provider with the EKS Cluster**

```bash
# Set cluster name
CLUSTER_NAME=my-cluster
REGION=us-west-2

# Get OIDC provider URL
OIDC_PROVIDER=$(aws eks describe-cluster --name $CLUSTER_NAME --region $REGION --query "cluster.identity.oidc.issuer" --output text | sed -e "s/^https:\/\///")

# Check if OIDC provider already exists
aws iam list-open-id-connect-providers | grep $OIDC_PROVIDER

# Create OIDC provider if it doesn't exist
if [ $? -ne 0 ]; then
  echo "Creating OIDC provider..."
  eksctl utils associate-iam-oidc-provider --cluster $CLUSTER_NAME --region $REGION --approve
else
  echo "OIDC provider already exists."
fi
```

**2. Create IAM Role with S3 Access Permissions**

```bash
# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Set namespace and service account name
NAMESPACE=default
SERVICE_ACCOUNT_NAME=s3-access-sa

# Create trust policy
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_PROVIDER}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${OIDC_PROVIDER}:sub": "system:serviceaccount:${NAMESPACE}:${SERVICE_ACCOUNT_NAME}"
        }
      }
    }
  ]
}
EOF

# Create IAM role
ROLE_NAME=eks-s3-access-role
aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document file://trust-policy.json

# Attach S3 read-only policy
aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# Get role ARN
ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query Role.Arn --output text)
echo "Role ARN: $ROLE_ARN"
```

**3. Create Kubernetes Service Account and Associate IAM Role**

```bash
# Create service account
cat > service-account.yaml << EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ${SERVICE_ACCOUNT_NAME}
  namespace: ${NAMESPACE}
  annotations:
    eks.amazonaws.com/role-arn: ${ROLE_ARN}
EOF

kubectl apply -f service-account.yaml

# Verify service account
kubectl get serviceaccount $SERVICE_ACCOUNT_NAME -o yaml
```

**4. Deploy Pod Using the Service Account**

```bash
# Deploy test pod
cat > s3-test-pod.yaml << EOF
apiVersion: v1
kind: Pod
metadata:
  name: s3-test-pod
  namespace: ${NAMESPACE}
spec:
  serviceAccountName: ${SERVICE_ACCOUNT_NAME}
  containers:
  - name: aws-cli
    image: amazon/aws-cli:latest
    command:
    - sleep
    - "3600"
  restartPolicy: Never
EOF

kubectl apply -f s3-test-pod.yaml

# Check pod status
kubectl get pod s3-test-pod
kubectl describe pod s3-test-pod
```

**5. Test S3 Access**

```bash
# Test listing S3 buckets
kubectl exec -it s3-test-pod -- aws s3 ls

# Test listing objects in a specific S3 bucket (change bucket name as needed)
kubectl exec -it s3-test-pod -- aws s3 ls s3://my-bucket/

# Verify AWS credentials
kubectl exec -it s3-test-pod -- aws sts get-caller-identity

# Check environment variables
kubectl exec -it s3-test-pod -- env | grep AWS
```

**6. Deploy a Regular Pod for Comparison**

```bash
# Deploy a pod using a regular service account
cat > regular-pod.yaml << EOF
apiVersion: v1
kind: Pod
metadata:
  name: regular-pod
  namespace: ${NAMESPACE}
spec:
  containers:
  - name: aws-cli
    image: amazon/aws-cli:latest
    command:
    - sleep
    - "3600"
  restartPolicy: Never
EOF

kubectl apply -f regular-pod.yaml

# Test S3 access from regular pod (should fail if node IAM role doesn't have S3 access permissions)
kubectl exec -it regular-pod -- aws s3 ls
```

**7. Cleanup**

```bash
# Delete pods
kubectl delete pod s3-test-pod regular-pod

# Delete service account
kubectl delete serviceaccount $SERVICE_ACCOUNT_NAME

# Clean up IAM role (optional)
aws iam detach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
aws iam delete-role --role-name $ROLE_NAME
```

**IRSA の仕組み:**

1. **OIDC Provider Connection**:
   * EKS cluster は OIDC provider として設定されます。
   * これにより、Kubernetes service account tokens が AWS IAM における trusted authentication mechanism になります。
2. **IAM Role Trust Policy**:
   * IAM role の trust policy は、どの Kubernetes service accounts が role を assume できるかを制限します。
   * Conditions を使用して、特定の namespaces 内の特定 service accounts に制限します。
3. **Service Account Annotation**:
   * `eks.amazonaws.com/role-arn` annotation は、service account が assume すべき IAM role を指定します。
   * この annotation は EKS Pod Identity Webhook によって処理されます。
4. **Environment Variable Injection**:
   * EKS Pod Identity Webhook は、次の environment variables を pods に自動的に inject します:
     * `AWS_ROLE_ARN`
     * `AWS_WEB_IDENTITY_TOKEN_FILE`
     * `AWS_REGION`
   * AWS SDKs はこれらの environment variables を使用して credentials を取得します。
5. **Principle of Least Privilege**:
   * application に必要な最小限の permissions のみを付与します。
   * この例では、S3 read-only access permissions のみを付与しました。

この lab を通じて、EKS cluster で実行される特定の pods のみに AWS services への細かな permissions を付与するために IRSA を設定する方法を学びました。この approach は node IAM roles を共有するより安全であり、principle of least privilege に従います。

</details>

## 高度なトピック

次の問題は、Amazon EKS cluster 作成に関連する高度なトピックについてのものです。この section では、EKS cluster 作成の advanced concepts と best practices に関する理解を確認します。

1. Amazon EKS cluster で Prefix Delegation を有効にしたときに発生する変更ではないものはどれですか？
   * A) Each ENI is assigned a /28 CIDR block (16 IPs)
   * B) Increased maximum pods per node
   * C) Reduced pod startup time
   * D) Improved IP address usage efficiency

<details>

<summary>解答を表示</summary>

**解答: C) Reduced pod startup time**

**説明:** Amazon EKS cluster で Prefix Delegation を有効にしたときに発生しない変更は、"Reduced pod startup time" です。実際には、prefix delegation を有効にしても pod startup time は短縮されず、わずかに増加する可能性さえあります。prefix delegation の主な利点は、node あたりの pod の最大数の増加と IP address usage efficiency の向上です。

**Prefix Delegation 有効化時に発生する実際の変更:**

1. **各 ENI に /28 CIDR block (16 IPs) が割り当てられる**:
   * デフォルトでは、VPC CNI は各 pod に対して ENI から Secondary IP addresses を割り当てます。
   * prefix delegation が有効になると、各 ENI には個別の IP アドレスではなく /28 CIDR blocks (16 IPs) が割り当てられます。
   * これにより、各 ENI がサポートできる IP アドレス数が大幅に増加します。
2. **node あたりの最大 pods 数の増加**:
   * prefix delegation を使用すると、node あたりの最大 pods 数が大幅に増加します。
   * たとえば、m5.large instance の場合:
     * Default configuration: maximum 29 pods
     * With prefix delegation enabled: maximum 110+ pods
3. **IP address usage efficiency の向上**:
   * 大規模 clusters で IP アドレス使用を最適化します。
   * VPC CIDR ranges が限られている環境で有用です。
   * 同じ IP address space 内でより多くの pods を実行できます。

**Prefix Delegation が Pod Startup Time に与える影響:**

Prefix delegation は pod startup time を短縮しません。次の理由により、わずかに増加する可能性があります。

1. **追加の setup overhead**:
   * CIDR block allocation と management に追加 overhead が発生する可能性があります。
   * routing table updates に時間が必要な場合があります。
2. **IP address allocation complexity**:
   * CIDR block allocation と management は、個別 IP address allocation より複雑になる場合があります。
   * これにより pod startup 中にわずかな遅延が発生する可能性があります。
3. **Initial setup time**:
   * 新しい ENIs に CIDR blocks を割り当てる initial setup time が長くなる場合があります。
   * ただし、一度 setup されると、その ENI 上で複数 pods を迅速に開始できます。

**Prefix Delegation を有効にする方法:**

```bash
# Enable prefix delegation
kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true

# Check prefix delegation status
kubectl describe daemonset aws-node -n kube-system | grep ENABLE_PREFIX_DELEGATION
```

**Prefix Delegation の制限:**

1. **EC2 Instance Support**:
   * Nitro-based instances のみが prefix delegation をサポートします。
   * 旧世代の instances では使用できません。
2. **VPC CNI Version Requirements**:
   * VPC CNI version 1.9.0 以上が必要です。
   * この feature は以前の versions では利用できません。
3. **Subnet Size Requirements**:
   * 十分な IP address space を持つ subnets が必要です。
   * 小さな subnets では IP addresses がすぐに枯渇する可能性があります。
4. **Transition Considerations**:
   * 既存の clusters で有効にした場合、新しい pods のみが prefix delegation を使用します。
   * すべての pods に適用するには、既存の pods を再起動する必要があります。

Prefix delegation は、node あたりの最大 pods 数を増やし、IP address usage efficiency を向上させる強力な feature ですが、pod startup time は短縮しません。したがって、"Reduced pod startup time" は prefix delegation を有効にしたときに発生する変更ではありません。

</details>

2\. Amazon EKS cluster node group で instance types を混在させる主な利点ではないものはどれですか？ - A) Cost optimization - B) Improved availability - C) workload characteristics に適した instance types の選択 - D) cluster management の簡素化

<details>

<summary>解答を表示</summary>

**解答: D) cluster management の簡素化**

**説明:** Amazon EKS cluster node group で instance types を混在させる主な利点ではない選択肢は、"cluster management の簡素化" です。実際には、さまざまな instance types を混在させると cluster management はより複雑になる可能性があります。instance types を混在させる主な利点は、cost optimization、improved availability、workload characteristics に適した instance types の選択です。

**Instance Types を混在させる実際の利点:**

1. **Cost optimization**:
   * spot instances と on-demand instances を混在させる
   * さまざまな instance families 間の価格差を活用する
   * workload requirements に対して最適な price-to-performance ratio を選択する
   *   Example:

       ```yaml
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: mixed-spot-instances
           instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5ad.large", "m5n.large"]
           spot: true
           minSize: 2
           maxSize: 10
       ```
2. **Improved availability**:
   * 特定の instance types の capacity が不足している場合に代替 instance types を使用する
   * spot instances が interrupted された場合に他の types で代替できる
   * 複数 instance families への diversification による risk distribution
   *   Example:

       ```yaml
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: mixed-instance-types
           instanceTypes: ["c5.large", "c5a.large", "c5d.large", "c5n.large"]
           minSize: 3
           maxSize: 10
           spotAllocationStrategy: capacity-optimized
       ```
3. **workload characteristics に適した instance types の選択**:
   * さまざまな workload requirements に対応する instance types を提供する
   * compute-intensive workloads には C series
   * memory-intensive workloads には R series
   * balanced workloads には M series
   * GPU workloads には G または P series
   *   Example:

       ```yaml
       # Compute optimized node group
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: compute-optimized
           instanceTypes: ["c5.2xlarge"]
           minSize: 2
           maxSize: 10
           labels:
             workload-type: compute
           taints:
             - key: workload-type
               value: compute
               effect: NoSchedule

         # Memory optimized node group
         - name: memory-optimized
           instanceTypes: ["r5.2xlarge"]
           minSize: 2
           maxSize: 10
           labels:
             workload-type: memory
           taints:
             - key: workload-type
               value: memory
               effect: NoSchedule
       ```

**Instance Types を混在させるデメリット:**

1. **cluster management complexity の増加**:
   * さまざまな instance types の monitoring と management が必要です
   * performance characteristics が異なるため troubleshooting complexity が増加します
   * さまざまな instance types に対して resource requests と limits を調整する必要があります
2. **workload predictability の低下**:
   * performance characteristics が instance type によって異なる可能性があります
   * 特に spot instances を使用する場合、workload performance variations が発生する可能性があります
3. **Resource allocation complexity**:
   * さまざまな instance types に対して pod resource requests と limits を設定するのが難しくなります
   * node selectors と taints を使用した複雑な scheduling rules が必要です
4. **Testing and validation burden**:
   * さまざまな instance types 上で applications をテストする必要があります
   * performance と compatibility issues を発見する可能性が高まります

**Instance Types を混在させる Strategies:**

1.  **workload ごとに node groups を分離**:

    ```yaml
    # Node group for web servers
    - name: web-servers
      instanceTypes: ["c5.large", "c5a.large"]
      labels:
        role: web

    # Node group for databases
    - name: databases
      instanceTypes: ["r5.xlarge", "r5a.xlarge"]
      labels:
        role: database
    ```
2.  **Cost optimization strategy**:

    ```yaml
    # Base on-demand node group
    - name: on-demand-base
      instanceTypes: ["m5.large"]
      minSize: 2
      maxSize: 5
      spot: false

    # Spot node group for scaling
    - name: spot-scaling
      instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5n.large"]
      minSize: 0
      maxSize: 20
      spot: true
    ```
3.  **Availability optimization strategy**:

    ```yaml
    # Diversification across multiple instance families
    - name: high-availability
      instanceTypes: ["m5.large", "m5a.large", "c5.large", "c5a.large", "r5.large", "r5a.large"]
      minSize: 3
      maxSize: 10
      spotAllocationStrategy: capacity-optimized
    ```

Instance types を混在させると、cost optimization、improved availability、workload characteristics に適した instance types の選択といった利点がありますが、cluster management は簡素化されず、実際にはより複雑になる可能性があります。したがって、"Simplified cluster management" は instance types を混在させる主な利点ではありません。

</details>

3. Amazon EKS cluster で最も安全な node group update strategy は何ですか？
   * A) In-place update
   * B) Blue/Green deployment
   * C) Canary deployment
   * D) Rolling update

<details>

<summary>解答を表示</summary>

**解答: B) Blue/Green deployment**

**説明:** Amazon EKS cluster で最も安全な node group update strategy は Blue/Green deployment です。Blue/Green deployment は新しい node group (green) を作成し、workloads を移行してから既存の node group (blue) を削除します。この approach は、update 中に問題が発生した場合に以前の環境へ直ちに rollback できるため、最も安全です。

**Node Group Update Strategies の比較:**

1. **Blue/Green Deployment**:
   * **How it works**: 新しい node group を作成 → workloads を移行 → 既存 node group を削除
   * **Advantages**:
     * 即時 rollback が可能
     * updates 中の workload disruption が最小限
     * update 前後の environments を比較可能
     * テスト後に切り替え可能
   * **Disadvantages**:
     * 一時的に 2 倍の resources が必要
     * Implementation complexity
     * cost の増加
   *   **Implementation example**:

       ```bash
       # 1. Create new node group
       eksctl create nodegroup \
         --cluster my-cluster \
         --name my-nodegroup-v2 \
         --node-type m5.large \
         --nodes 3 \
         --node-ami-family AmazonLinux2 \
         --node-labels "version=v2,color=green"

       # 2. Migrate workloads (update node selector)
       kubectl patch deployment my-app -p '{"spec":{"template":{"spec":{"nodeSelector":{"color":"green"}}}}}'

       # 3. Verify all workloads have moved to new nodes
       kubectl get pods -o wide

       # 4. Remove existing node group
       eksctl delete nodegroup --cluster my-cluster --name my-nodegroup-v1
       ```
2. **Rolling Update**:
   * **How it works**: nodes を 1 つずつ置き換える (cordon → drain → terminate → new node を追加)
   * **Advantages**:
     * 追加 resources が不要
     * EKS managed node groups の default strategy
     * simple implementation
   * **Disadvantages**:
     * rollback が困難
     * update 中の issues が cluster 全体に影響する可能性
     * update time が長くなる可能性
   *   **Implementation example**:

       ```bash
       # Update managed node group
       aws eks update-nodegroup-version \
         --cluster-name my-cluster \
         --nodegroup-name my-nodegroup

       # Modify update configuration
       aws eks update-nodegroup-config \
         --cluster-name my-cluster \
         --nodegroup-name my-nodegroup \
         --update-config '{"maxUnavailable": 1}'
       ```
3. **Canary Deployment**:
   * **How it works**: 小規模な新しい node group を作成 → 一部 workloads を移行 → 検証 → 完全移行
   * **Advantages**:
     * risk を最小化
     * 段階的な validation が可能
     * issues 発生時の impact scope を制限
   * **Disadvantages**:
     * Implementation complexity
     * 追加 resources が必要
     * complete migration まで時間がかかる
   *   **Implementation example**:

       ```bash
       # 1. Create small canary node group
       eksctl create nodegroup \
         --cluster my-cluster \
         --name canary-nodegroup \
         --node-type m5.large \
         --nodes 1 \
         --node-labels "deployment=canary"

       # 2. Migrate some workloads
       kubectl patch deployment my-app -p '{"spec":{"template":{"spec":{"nodeSelector":{"deployment":"canary"}}}}}'

       # 3. Proceed with complete migration after validation
       ```
4. **In-place Update**:
   * **How it works**: 既存 nodes 上で直接 updates を実行
   * **Advantages**:
     * 追加 resources が不要
     * simple changes に適している
   * **Disadvantages**:
     * high risk
     * rollback が困難
     * update に失敗した場合 node damage の可能性
     * EKS では推奨されません
   *   **Implementation example**:

       ```bash
       # SSH into node for direct update (not recommended)
       ssh ec2-user@node-ip
       sudo yum update -y
       ```

**Blue/Green Deployment が最も安全である理由:**

1. **Complete isolation**:
   * 新しい environment は既存 environment から完全に分離され、impact を最小化します
   * update 中に issues が発生しても既存 environment は影響を受けません
2. **Immediate rollback**:
   * issues 発生時に traffic を既存 environment に直ちに戻せます
   * downtime なしで rollback 可能です
3. **Validation opportunity**:
   * production traffic に切り替える前に新しい environment を十分にテストできます
   * actual environment と同一条件で validation できます
4. **Gradual transition**:
   * traffic を新しい environment に段階的に移行できます
   * issues 発生時の impact scope を制限します

**Blue/Green Deployment Best Practices:**

1. **Automation**:
   * deployment process を自動化して human error を最小化します
   * CI/CD pipeline と統合します
2. **Enhanced monitoring**:
   * 新しい environment の performance と error metrics を monitor します
   * 既存 environment と比較・分析します
3. **Gradual transition**:
   * traffic を新しい environment に段階的に移行します
   * issues 発生時は直ちに roll back します
4. **Resource optimization**:
   * transition 完了後、不要な resources を速やかに clean up します
   * Cost optimization

Blue/Green deployment には追加 resources と implementation complexity というデメリットがありますが、安全性の観点では最も優れた approach です。特に重要な本番環境や、updates 失敗時の business impact が大きい場合に推奨されます。

</details>

4\. Amazon EKS cluster で node groups の Auto Scaling を最適化する方法ではないものはどれですか？ - A) Cluster Autoscaler scan interval の調整 - B) pod priority and preemption の設定 - C) node group ごとの Auto Scaling groups への tagging - D) すべての nodes に同じ instance type を使用する

<details>

<summary>解答を表示</summary>

**解答: D) すべての nodes に同じ instance type を使用する**

**説明:** Amazon EKS cluster で node groups の Auto Scaling を最適化する方法ではない選択肢は、"すべての nodes に同じ instance type を使用する" です。実際には、さまざまな instance types を混在させる方が、cost optimization と availability の観点でより効果的な Auto Scaling strategy です。特に Spot Instances を使用する場合、複数の instance types を指定することで capacity availability を高め、interruption risk を低減することが推奨されます。

**Node Group Auto Scaling を最適化する実際の方法:**

1. **Cluster Autoscaler Scan Interval の調整**:
   * Cluster Autoscaler は cluster を定期的に scan して、scale up または scale down が必要かどうかを判断します。
   * scan interval を調整することで、response time と resource usage のバランスを取ることができます。
   *   Example:

       ```yaml
       # Cluster Autoscaler deployment configuration
       apiVersion: apps/v1
       kind: Deployment
       metadata:
         name: cluster-autoscaler
         namespace: kube-system
       spec:
         template:
           spec:
             containers:
             - name: cluster-autoscaler
               image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.23.0
               command:
               - ./cluster-autoscaler
               - --v=4
               - --stderrthreshold=info
               - --cloud-provider=aws
               - --scan-interval=30s  # Adjust scan interval (default: 10 seconds)
               - --max-node-provision-time=15m
               - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/my-cluster
       ```
2. **Pod Priority and Preemption の設定**:
   * pod priority と preemption (PriorityClass) を使用して、重要な workloads が先に schedule されるようにします。
   * resources が不足している場合、優先度の低い pods が preempt され、高優先度 pods のための空きが作られます。
   *   Example:

       ```yaml
       # Priority class definition
       apiVersion: scheduling.k8s.io/v1
       kind: PriorityClass
       metadata:
         name: high-priority
       value: 1000000
       globalDefault: false
       description: "High priority pods"
       ---
       # High priority pod
       apiVersion: v1
       kind: Pod
       metadata:
         name: high-priority-pod
       spec:
         priorityClassName: high-priority
         containers:
         - name: nginx
           image: nginx
       ```
3. **Node Group ごとの Auto Scaling Groups への Tagging**:
   * Auto Scaling groups に tag を付け、Cluster Autoscaler が特定の node groups を識別して管理できるようにします。
   * node group ごとに異なる Auto Scaling behaviors を設定できます。
   *   Example:

       ```bash
       # Tag Auto Scaling group
       aws autoscaling create-or-update-tags \
         --tags ResourceId=my-asg,ResourceType=auto-scaling-group,Key=k8s.io/cluster-autoscaler/enabled,Value=true,PropagateAtLaunch=true \
                ResourceId=my-asg,ResourceType=auto-scaling-group,Key=k8s.io/cluster-autoscaler/my-cluster,Value=owned,PropagateAtLaunch=true

       # Configure Auto Scaling settings per node group
       aws autoscaling update-auto-scaling-group \
         --auto-scaling-group-name my-asg \
         --min-size 2 \
         --max-size 10 \
         --desired-capacity 2
       ```

**さまざまな Instance Types を混在させる利点:**

1. **Cost Optimization**:
   * さまざまな instance types 間の価格差を活用します
   * Spot Instances 使用時の availability を向上させます
   *   Example:

       ```yaml
       # Node group using various instance types
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: mixed-instances
           instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5n.large"]
           minSize: 2
           maxSize: 10
           spot: true
       ```
2. **Improved Availability**:
   * 特定の instance types の capacity が不足している場合に代替 instance types を使用します
   * Spot Instances が interrupted された場合に他の types へ切り替えられます
   *   Example:

       ```yaml
       # Capacity-optimized Spot allocation strategy
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: spot-nodes
           instanceTypes: ["c5.large", "c5a.large", "c5d.large", "c5n.large"]
           minSize: 2
           maxSize: 10
           spot: true
           spotAllocationStrategy: capacity-optimized
       ```
3. **Workload Characteristics に基づく Instance Types の選択**:
   * さまざまな workload requirements に適した instance types を提供します
   * node selectors と taints を使用して workload placement を制御します
   *   Example:

       ```yaml
       # Node groups by workload characteristics
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: general-purpose
           instanceTypes: ["m5.large"]
           minSize: 2
           maxSize: 10

         - name: compute-intensive
           instanceTypes: ["c5.large"]
           minSize: 0
           maxSize: 10
           labels:
             workload-type: compute
       ```

**Auto Scaling Optimization の追加 Strategies:**

1. **Overprovisioning**:
   * sudden scaling requests に備えて一定量の spare resources を維持します
   *   Example:

       ```yaml
       # Overprovisioning pod
       apiVersion: apps/v1
       kind: Deployment
       metadata:
         name: overprovisioning
         namespace: kube-system
       spec:
         replicas: 1
         selector:
           matchLabels:
             app: overprovisioning
         template:
           metadata:
             labels:
               app: overprovisioning
           spec:
             priorityClassName: overprovisioning
             containers:
             - name: reserve-resources
               image: k8s.gcr.io/pause:3.2
               resources:
                 requests:
                   cpu: 1000m
                   memory: 1000Mi
       ```
2. **Scaling Policies の最適化**:
   * target tracking scaling policies を使用します
   * step scaling policies を使用します
   * predictive scaling を有効にします
   *   Example:

       ```bash
       # Configure target tracking scaling policy
       aws autoscaling put-scaling-policy \
         --auto-scaling-group-name my-asg \
         --policy-name cpu70-target-tracking-scaling-policy \
         --policy-type TargetTrackingScaling \
         --target-tracking-configuration '{"PredefinedMetricSpecification":{"PredefinedMetricType":"ASGAverageCPUUtilization"},"TargetValue":70.0,"DisableScaleIn":false}'
       ```
3. **Karpenter の使用**:
   * Cluster Autoscaler の代わりに Karpenter の使用を検討します
   * より高速な node provisioning と、より柔軟な instance type selection
   *   Example:

       ```yaml
       # Karpenter Provisioner
       apiVersion: karpenter.sh/v1alpha5
       kind: NodePool
       metadata:
         name: default
       spec:
         template:
           spec:
             requirements:
               - key: karpenter.sh/capacity-type
                 operator: In
                 values: ["spot", "on-demand"]
               - key: node.kubernetes.io/instance-type
                 operator: In
                 values: ["m5.large", "m5a.large", "m5d.large", "m5n.large"]
         limits:
           resources:
             cpu: 1000
             memory: 1000Gi
       ```

すべての nodes に同じ instance type を使用することは Auto Scaling optimization strategy ではありません。むしろ、cost optimization と availability の観点では、さまざまな instance types を混在させる方が効果的です。したがって、"Using the same instance type for all nodes" は node groups の Auto Scaling を最適化する方法ではありません。

</details>

5. Amazon EKS cluster で node groups を作成する際に考慮すべき security best practice ではないものはどれですか？
   * A) Requiring IMDSv2
   * B) Applying least privilege IAM policies
   * C) Assigning public IP addresses to all nodes
   * D) Restricting security group rules

<details>

<summary>解答を表示</summary>

**解答: C) Assigning public IP addresses to all nodes**

**説明:** Amazon EKS cluster で node groups を作成する際に考慮すべき security best practice ではない選択肢は、"Assigning public IP addresses to all nodes" です。security best practice は実際にはその逆で、nodes を private subnets に配置し、public IP addresses を割り当てないことです。これにより、nodes が internet から直接アクセス可能になることを防ぎ、attack surface を減らします。

**EKS Node Group 作成における実際の Security Best Practices:**

1. **Requiring IMDSv2**:
   * SSRF (Server-Side Request Forgery) attacks から保護するため、Instance Metadata Service version 2 (IMDSv2) を要求します
   * IMDSv2 は session-based requests を使用して security を強化します
   *   Example:

       ```yaml
       # eksctl configuration file
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: secure-nodes
           instanceType: m5.large
           minSize: 2
           maxSize: 5
           disableIMDSv1: true  # Disable IMDSv1
           metadataOptions:
             httpTokens: required  # Require IMDSv2
             httpPutResponseHopLimit: 1
       ```
2. **Applying Least Privilege IAM Policies**:
   * node IAM roles には必要最小限の permissions のみを付与します
   * default managed policies を超える追加 permissions が必要な場合は granular policies を作成します
   *   Example:

       ```yaml
       # Least privilege policy for node IAM role
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: secure-nodes
           instanceType: m5.large
           minSize: 2
           maxSize: 5
           iam:
             attachPolicyARNs:
               - arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy
               - arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
               - arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy
             withAddonPolicies:
               imageBuilder: false
               autoScaler: false
               externalDNS: false
               certManager: false
               appMesh: false
               ebs: true
               fsx: false
               efs: false
               albIngress: false
               xRay: false
               cloudWatch: true
       ```
3. **Restricting Security Group Rules**:
   * node security groups の inbound と outbound rules を制限します
   * 必要最小限の ports のみを開きます
   *   Example:

       ```bash
       # Create security group
       aws ec2 create-security-group \
         --group-name eks-node-sg \
         --description "Security group for EKS nodes" \
         --vpc-id vpc-12345

       # Add only rules necessary for cluster communication
       aws ec2 authorize-security-group-ingress \
         --group-id sg-12345 \
         --protocol tcp \
         --port 443 \
         --source-group sg-cluster

       aws ec2 authorize-security-group-ingress \
         --group-id sg-12345 \
         --protocol tcp \
         --port 10250 \
         --source-group sg-cluster
       ```

**Nodes に Public IP Addresses を割り当てない理由:**

1. **Reduced Attack Surface**:
   * public IP がないため、nodes は internet から直接アクセスできません
   * SSH access などの management tasks は bastion hosts または AWS Systems Manager を通じて実行します
2. **Improved Security Architecture**:
   * nodes を private subnets に配置します
   * NAT Gateway を通じた outbound communication のみを許可します
   * inbound traffic は load balancers を通じてのみ許可します
3. **Regulatory Compliance**:
   * 多くの security standards と regulations は direct internet exposure の最小化を要求します
   * PCI DSS、HIPAA、およびその他 regulations の compliance に役立ちます

**Nodes を Private Subnets に配置する例:**

```yaml
# eksctl configuration file
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
vpc:
  subnets:
    private:
      us-west-2a: { id: subnet-private-a }
      us-west-2b: { id: subnet-private-b }
    public:
      us-west-2a: { id: subnet-public-a }
      us-west-2b: { id: subnet-public-b }
managedNodeGroups:
  - name: secure-nodes
    instanceType: m5.large
    minSize: 2
    maxSize: 5
    privateNetworking: true  # Place nodes in private subnets
```

**追加の EKS Security Best Practices:**

1. **Encryption の有効化**:
   * EBS volume encryption
   * Secrets encryption
   *   Example:

       ```yaml
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       secretsEncryption:
         keyARN: arn:aws:kms:us-west-2:123456789012:key/key-id
       nodeGroups:
         - name: secure-nodes
           volumeEncrypted: true
           volumeKmsKeyID: arn:aws:kms:us-west-2:123456789012:key/key-id
       ```
2. **Container Security**:
   * privileged containers を無効化します
   * read-only root filesystem を使用します
   *   Example:

       ```yaml
       apiVersion: v1
       kind: Pod
       metadata:
         name: secure-pod
       spec:
         containers:
         - name: secure-container
           image: nginx
           securityContext:
             privileged: false
             readOnlyRootFilesystem: true
             allowPrivilegeEscalation: false
       ```
3. **Network Policies の実装**:
   * pod-to-pod communication を制限します
   * default deny policies を適用します
   *   Example:

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
4. **Logging and Monitoring**:
   * CloudWatch Logs を有効にします
   * GuardDuty EKS Protection を有効にします
   *   Example:

       ```bash
       # Enable CloudWatch Logs
       aws eks update-cluster-config \
         --name my-cluster \
         --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
       ```

すべての nodes に public IP addresses を割り当てることは security best practice ではありません。むしろ、security risk を増加させます。したがって、"Assigning public IP addresses to all nodes" は Amazon EKS cluster で node groups を作成する際に考慮すべき security best practice ではありません。

</details>

# EKS 入門クイズ

このクイズでは、Amazon Elastic Kubernetes Service (EKS) の基本概念と機能に関する理解を確認します。EKS architecture、components、管理方法、料金モデルなどのトピックを扱います。

## 多肢選択問題

1. Amazon EKS (Elastic Kubernetes Service) の主なメリットは何ですか？
   * A) 自分で Kubernetes control plane infrastructure を管理する必要がない
   * B) 他の managed Kubernetes services よりコストが低い
   * C) AWS services だけを使用できる
   * D) 単一の availability zone でのみ実行できる

<details>

<summary>答えを表示</summary>

**答え: A) 自分で Kubernetes control plane infrastructure を管理する必要がない**

**解説:** Amazon EKS (Elastic Kubernetes Service) の主なメリットは、自分で Kubernetes control plane infrastructure を管理する必要がないことです。AWS が Kubernetes control plane の可用性とスケーラビリティを管理するため、ユーザーは workloads の実行に集中できます。

EKS の主なメリット:

* **Managed Control Plane**: AWS が control plane nodes、etcd cluster、API server などを管理します。
* **High Availability**: control plane は複数の availability zones にまたがってデプロイされ、単一障害点を排除します。
* **Automatic Upgrades and Patches**: AWS が Kubernetes version upgrades と security patches を管理します。
* **Integration with AWS Services**: IAM、VPC、ELB、ECR など、さまざまな AWS services とシームレスに統合します。
* **Standard Kubernetes**: vendor lock-in を防ぐため、完全に互換性のある Kubernetes を提供します。

他の選択肢の問題点:

* EKS は他の managed Kubernetes services より必ずしも安いわけではありません。実際には control plane に時間単位の料金がかかります。
* EKS は AWS services だけでなく、任意の Kubernetes-compatible applications と services を実行できます。
* EKS clusters は high availability のため、デフォルトで複数の availability zones にまたがってデプロイされます。

</details>

2. Amazon EKS cluster control plane はどこにデプロイされますか？
   * A) ユーザーの VPC 内
   * B) AWS-managed account の複数の availability zones にまたがってデプロイされる
   * C) ユーザーが選択した単一の availability zone
   * D) ユーザーの EC2 instances 上で実行される

<details>

<summary>答えを表示</summary>

**答え: B) AWS-managed account の複数の availability zones にまたがってデプロイされる**

**解説:** Amazon EKS cluster control plane は、AWS-managed account の複数の availability zones にまたがってデプロイされます。これは managed service としての EKS の中核的な側面の 1 つです。

EKS control plane deployment の主な特徴:

* **AWS-Managed Infrastructure**: control plane は AWS が所有および管理する account で実行されます。
* **Multi-AZ Deployment**: high availability のため、少なくとも 3 つの availability zones にまたがってデプロイされます。
* **Auto Recovery**: AWS が control plane components の健全性を監視し、障害が発生した components を自動的に置き換えます。
* **Endpoint Accessibility**: control plane endpoints は、publicly accessible または VPC 内からのみアクセス可能に構成できます。
* **Auto Scaling**: control plane capacity は cluster load に基づいて自動的に調整されます。

他の選択肢の問題点:

* control plane はユーザーの VPC 内にはデプロイされません。代わりに、ENI (Elastic Network Interface) を通じてユーザーの VPC と AWS-managed VPC の間に接続が確立されます。
* control plane は high availability を確保するため、単一ではなく複数の availability zones にまたがってデプロイされます。
* control plane はユーザーの EC2 instances 上ではなく、AWS-managed infrastructure 上で実行されます。

</details>

3. Amazon EKS で worker nodes を管理する有効な方法ではないものはどれですか？
   * A) Self-managed node groups
   * B) Managed node groups
   * C) Fargate profiles
   * D) EKS automatic node provisioning

<details>

<summary>答えを表示</summary>

**答え: D) EKS automatic node provisioning**

**解説:** 「EKS automatic node provisioning」は、Amazon EKS で正式に提供されている worker node 管理方法ではありません。この機能は存在しません。

Amazon EKS で worker nodes を管理する実際の方法は次のとおりです:

1. **Self-managed node groups**:
   * ユーザーが EC2 instances を直接作成して管理します。
   * Auto Scaling groups を通じて管理できます。
   * node configuration を完全に制御できます。
   * operational overhead が最も高くなります。
2. **Managed node groups**:
   * AWS が node provisioning と lifecycle を管理します。
   * node upgrades、patches、調整が自動化されます。
   * EC2 Auto Scaling groups に基づきます。
   * 標準の Amazon Linux または Bottlerocket AMI を使用します。
3. **Fargate profiles**:
   * 個々の EC2 instances を管理する必要をなくす serverless computing option です。
   * pod ごとに computing resources をプロビジョニングします。
   * infrastructure management overhead が最も低くなります。
   * 一定の制限があります (例: DaemonSet support がない、特定の resource restrictions)。

node auto-scaling について、EKS は Kubernetes Cluster Autoscaler や Karpenter のようなツールをサポートしていますが、「EKS automatic node provisioning」と呼ばれる公式機能はありません。

</details>

4. Amazon EKS clusters の pod networking でデフォルトで使用される CNI plugin は何ですか？
   * A) Flannel
   * B) Calico
   * C) AWS VPC CNI
   * D) Weave Net

<details>

<summary>答えを表示</summary>

**答え: C) AWS VPC CNI**

**解説:** Amazon EKS clusters の pod networking でデフォルトで使用される CNI (Container Network Interface) plugin は AWS VPC CNI です。この plugin は Amazon VPC networking と Kubernetes pods を直接統合します。

AWS VPC CNI の主な機能:

* **VPC-native IP address assignment**: Pods は VPC から直接 IP addresses を受け取り、VPC 内の他の resources と同じ network space に存在します。
* **Secondary IP address usage**: 各 node の Elastic Network Interface (ENI) に関連付けられた secondary IP addresses を pods に割り当てます。
* **Security group integration**: security groups を pod レベルで適用できます (SecurityGroupsForPods feature)。
* **VPC flow log visibility**: Pod traffic は VPC flow logs で可視化されます。
* **Leverage AWS networking features**: VPC peering、Transit Gateway、PrivateLink などの機能を pods から直接利用できます。

AWS VPC CNI は open-source project であり、GitHub で code を確認できます: https://github.com/aws/amazon-vpc-cni-k8s

他の CNI plugins (Flannel、Calico、Weave Net など) も EKS にインストールできますが、AWS VPC CNI がデフォルトで提供されます。

</details>

5. Amazon EKS で Kubernetes resources の authentication と authorization を管理する方法は何ですか？
   * A) Kubernetes service accounts のみを使用する
   * B) AWS IAM と Kubernetes RBAC の統合
   * C) EKS-specific permission management system
   * D) AWS Cognito による user authentication

<details>

<summary>答えを表示</summary>

**答え: B) AWS IAM と Kubernetes RBAC の統合**

**解説:** Amazon EKS は、AWS IAM (Identity and Access Management) と Kubernetes RBAC (Role-Based Access Control) の統合を通じて、Kubernetes resources の authentication と authorization を管理します。この統合アプローチは、AWS の強力な identity management capabilities と Kubernetes の細かな permission control を組み合わせます。

主な機能:

* **IAM Authentication**: AWS IAM credentials を使用して Kubernetes API server に認証します。
* **aws-auth ConfigMap**: IAM roles または users を Kubernetes users と groups にマッピングします。
* **RBAC Authorization**: Kubernetes RBAC system を使用して cluster 内の permissions を制御します。
* **IRSA (IAM Roles for Service Accounts)**: IAM roles を Kubernetes service accounts にリンクし、pods が AWS services に安全にアクセスできるようにします。

仕組み:

1. ユーザーは `aws eks get-token` command (AWS CLI または AWS SDK 経由) を使用して Kubernetes API server 用の authentication token を取得します。
2. この token は IAM credentials を使用して署名されます。
3. Kubernetes API server は AWS IAM authenticator を使用して token を検証します。
4. aws-auth ConfigMap の mappings に基づいて、ユーザーに Kubernetes users と groups が割り当てられます。
5. Kubernetes RBAC system は、それらの users または groups に付与された permissions に基づいて requests を許可または拒否します。

他の選択肢の問題点:

* Kubernetes service accounts のみを使用すると、AWS services との統合が制限されます。
* EKS には個別の専用 permission management system はなく、標準の Kubernetes RBAC と AWS IAM を統合します。
* AWS Cognito は EKS authentication には直接使用されませんが、OIDC provider として構成することはできます。

</details>

6. Amazon EKS cluster 内で pods が AWS services (例: S3、DynamoDB) にアクセスするための推奨方法は何ですか？
   * A) EC2 instance profiles を使用して nodes に IAM roles を付与する
   * B) AWS credentials を environment variables として pods に直接注入する
   * C) IAM roles を Kubernetes service accounts (IRSA) にリンクする
   * D) AWS credentials を Kubernetes Secrets として保存し、mount する

<details>

<summary>答えを表示</summary>

**答え: C) IAM roles を Kubernetes service accounts (IRSA) にリンクする**

**解説:** Amazon EKS cluster 内で pods が AWS services にアクセスするための推奨方法は、IAM roles を Kubernetes service accounts にリンクすることです。この機能は IRSA (IAM Roles for Service Accounts) と呼ばれ、pod レベルで細かな permissions を提供します。

IRSA の主なメリット:

* **Principle of least privilege**: 各 application に必要な最小限の permissions のみを付与できます。
* **Permission isolation**: 同じ node 上で実行される異なる pods に、異なる IAM permissions を持たせることができます。
* **Simplified credential management**: AWS credentials を直接管理する必要がありません。
* **Enhanced security**: credentials は code や configuration に hardcoded されません。

IRSA の設定方法:

1.  OpenID Connect (OIDC) provider を EKS cluster に関連付けます:

    ```bash
    eksctl utils associate-iam-oidc-provider --cluster=<cluster-name> --approve
    ```
2.  service account 用の IAM role を作成します:

    ```bash
    eksctl create iamserviceaccount \
      --name=<service-account-name> \
      --namespace=<namespace> \
      --cluster=<cluster-name> \
      --attach-policy-arn=arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
      --approve
    ```
3.  pod manifest で service account を参照します:

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: my-pod
    spec:
      serviceAccountName: <service-account-name>
      containers:
      - name: my-container
        image: my-image
    ```

他の選択肢の問題点:

* EC2 instance profiles を使用すると、同じ node 上のすべての pods に同じ permissions が付与され、principle of least privilege に反します。
* AWS credentials を environment variables として注入すると、credential exposure のリスクがあり、credential rotation が難しくなります。
* AWS credentials を Kubernetes Secrets として保存すると、credential management の負担が増え、credential rotation が複雑になります。

</details>

7. Amazon EKS clusters の logging feature について正しい記述はどれですか？
   * A) すべての logs がデフォルトで CloudWatch Logs に送信される
   * B) Control plane logs は任意で CloudWatch Logs に送信できる
   * C) worker node logs のみ CloudWatch Logs に送信できる
   * D) EKS は logging functionality を提供しない

<details>

<summary>答えを表示</summary>

**答え: B) Control plane logs は任意で CloudWatch Logs に送信できる**

**解説:** Amazon EKS clusters では、control plane logs を任意で CloudWatch Logs に送信できます。この機能はデフォルトでは無効で、ユーザーは必要な log types を選択して有効化できます。

EKS control plane logging の主な機能:

* **Optional activation**: cluster 作成時または既存 clusters で有効化できます。
* **Log type selection**: 次の中から必要な log types のみを選択できます:
  * API server (api)
  * Audit (audit)
  * Authenticator (authenticator)
  * Controller manager (controllerManager)
  * Scheduler (scheduler)
* **CloudWatch Logs integration**: 選択した logs は、保存、分析、monitoring のため AWS CloudWatch Logs に送信されます。
* **Cost consideration**: log storage には CloudWatch Logs pricing が適用されます。

logging を有効化する方法:

```bash
# Enable logging using AWS CLI
aws eks update-cluster-config \
    --region <region> \
    --name <cluster-name> \
    --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# Enable logging using eksctl
eksctl utils update-cluster-logging --enable-types api,audit,authenticator,controllerManager,scheduler --cluster <cluster-name> --region <region>
```

Worker node logging:

* Worker node logs は EKS control plane logging feature には含まれません。
* worker node logs を CloudWatch Logs に送信するには、CloudWatch agent をインストールするか、Fluentd/Fluent Bit のような logging solution を構成する必要があります。

他の選択肢の問題点:

* すべての logs がデフォルトで CloudWatch Logs に送信されるわけではありません。ユーザーが明示的に有効化する必要があります。
* CloudWatch Logs に送信できるのが worker node logs のみというわけではありません。control plane logs も送信できます。
* EKS は control plane logging functionality を提供しています。

</details>

8. Amazon EKS cluster の cost component ではないものはどれですか？
   * A) EKS control plane hourly fee
   * B) worker nodes の EC2 instance costs
   * C) Fargate pod execution costs
   * D) Kubernetes license fees

<details>

<summary>答えを表示</summary>

**答え: D) Kubernetes license fees**

**解説:** Kubernetes license fees は Amazon EKS clusters の cost component ではありません。Kubernetes は Cloud Native Computing Foundation (CNCF) によって管理される open-source software であり、Apache 2.0 license の下で無料で使用できます。したがって、EKS を使用する際に別途 Kubernetes license fees は発生しません。

Amazon EKS clusters の実際の cost components には次が含まれます:

1. **EKS control plane hourly fee**:
   * 各 EKS cluster に対して固定の hourly fee が課金されます (例: $0.10 per hour)。
   * このコストは cluster size や workload に関係なく一定です。
   * 複数 regions にまたがる場合は region ごとに料金が発生します。
2. **worker nodes の EC2 instance costs**:
   * self-managed または managed node groups で使用される EC2 instances に対してコストが発生します。
   * コストは instance type、size、quantity、runtime によって異なります。
   * Reserved Instances、Savings Plans、Spot Instances によってコストを最適化できます。
3. **Fargate pod execution costs**:
   * Fargate を使用する場合、pods に割り当てられた vCPU と memory resources に基づいて課金されます。
   * コストは pod runtime に基づいて秒単位で計算されます。
   * node management overhead はありませんが、一般的に EC2-based nodes より高くなります。
4. **追加の AWS resource costs**:
   * EBS volumes
   * Load balancers (NLB, ALB)
   * CloudWatch logs and metrics
   * NAT Gateway
   * Data transfer

Cost optimization strategies:

* 適切な instance types の選択
* auto-scaling の構成
* Spot Instances の使用
* Cluster automation と scheduled scaling
* resource requests と limits の最適化
* Cost monitoring と analysis

</details>

9. Amazon EKS cluster で load balancing を実装する正しい方法は何ですか？
   * A) built-in EKS load balancer を使用する
   * B) Kubernetes Service resources と AWS Load Balancer Controller を統合する
   * C) EC2 load balancers を手動で作成して構成する
   * D) EKS は load balancing をサポートしない

<details>

<summary>答えを表示</summary>

**答え: B) Kubernetes Service resources と AWS Load Balancer Controller を統合する**

**解説:** Amazon EKS cluster で load balancing を実装する正しい方法は、Kubernetes Service resources と AWS Load Balancer Controller を統合することです。このアプローチは Kubernetes の declarative resource management と AWS の load balancing capabilities を組み合わせます。

EKS で load balancing を実装する方法:

1.  **Default LoadBalancer type Service**:

    * Kubernetes で `LoadBalancer` type Service を作成すると、デフォルトで Classic Load Balancer (CLB) または Network Load Balancer (NLB) がプロビジョニングされます。

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: my-service
    spec:
      type: LoadBalancer
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: my-app
    ```
2.  **AWS Load Balancer Controller**:

    * Application Load Balancer (ALB) と Network Load Balancer (NLB) を管理するためのより高度な機能を利用するには、AWS Load Balancer Controller をインストールします。
    * ALB は Ingress resources を通じてプロビジョニングおよび構成できます。
    * さまざまな load balancer attributes を annotations によって構成できます。

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: my-ingress
      annotations:
        kubernetes.io/ingress.class: alb
        alb.ingress.kubernetes.io/scheme: internet-facing
        alb.ingress.kubernetes.io/target-type: ip
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
3.  **Service annotations**:

    * load balancer type と configuration を指定するために、services に annotations を追加できます。

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: my-service
      annotations:
        service.beta.kubernetes.io/aws-load-balancer-type: nlb
        service.beta.kubernetes.io/aws-load-balancer-internal: "true"
    spec:
      type: LoadBalancer
      # ...
    ```

他の選択肢の問題点:

* EKS には独立した「built-in EKS load balancer」component はありません。load balancing は Kubernetes Service resources と AWS load balancers の統合を通じて提供されます。
* EC2 load balancers を手動で作成して構成することは可能ですが、Kubernetes の declarative approach に合わず、管理が複雑になります。
* EKS は load balancing を完全にサポートしています。

</details>

10. Amazon EKS cluster で storage を管理する有効な方法ではないものはどれですか？
    * A) EBS CSI driver を使用して EBS volumes をプロビジョニングする
    * B) EFS CSI driver を使用して EFS file systems を mount する
    * C) EKS built-in storage manager による automatic volume provisioning
    * D) FSx for Lustre CSI driver を使用して high-performance file systems に接続する

<details>

<summary>答えを表示</summary>

**答え: C) EKS built-in storage manager による automatic volume provisioning**

**解説:** 「EKS built-in storage manager」は存在しない機能です。Amazon EKS には automatic volume provisioning のための built-in storage manager はなく、storage は CSI (Container Storage Interface) drivers を通じて管理されます。

Amazon EKS clusters で storage を管理する実際の方法には次が含まれます:

1.  **EBS CSI driver**:

    * Amazon EBS (Elastic Block Store) volumes を Kubernetes pods に接続できます。
    * block storage を必要とする applications (databases など) に適しています。
    * dynamic provisioning、snapshots、volume resizing をサポートします。
    * 単一の availability zone 内でのみアクセス可能です (ReadWriteOnce access mode)。

    ```yaml
    # StorageClass example
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer
    parameters:
      type: gp3
      encrypted: "true"
    ```
2.  **EFS CSI driver**:

    * Amazon EFS (Elastic File System) を Kubernetes pods に mount できます。
    * 複数の pods から同時にアクセスする必要がある shared file systems に適しています。
    * 複数の availability zones にまたがってアクセス可能です (ReadWriteMany access mode)。
    * web servers、CMS、CI/CD pipelines などに適しています。

    ```yaml
    # StorageClass example
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: efs-sc
    provisioner: efs.csi.aws.com
    parameters:
      provisioningMode: efs-ap
      fileSystemId: fs-0123456789abcdef0
      directoryPerms: "700"
    ```
3.  **FSx for Lustre CSI driver**:

    * Amazon FSx for Lustre を Kubernetes pods に接続できます。
    * high-performance computing、machine learning、big data analytics などの high-performance workloads に適しています。
    * high throughput と low latency を提供します。

    ```yaml
    # StorageClass example
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: fsx-sc
    provisioner: fsx.csi.aws.com
    parameters:
      subnetId: subnet-0123456789abcdef0
      securityGroupIds: sg-0123456789abcdef0
      deploymentType: PERSISTENT_1
      automaticBackupRetentionDays: "1"
      dailyAutomaticBackupStartTime: "00:00"
      perUnitStorageThroughput: "200"
      storageCapacity: "1200"
    ```
4. **Other storage options**:
   * CSI drivers または S3 mounters を通じた Amazon S3 (Simple Storage Service)
   * Amazon FSx for Windows File Server
   * Amazon FSx for NetApp ONTAP
   * Third-party storage solutions (Portworx, Rook など)

Storage management best practices:

* workload requirements に適した storage types を選択する
* dynamic provisioning のために StorageClass を構成する
* backup と recovery strategies を確立する
* storage performance を監視する
* cost optimization のために適切な storage classes と sizes を選択する

</details>

## ハンズオン演習

### 演習 1: EKS Cluster の作成と構成

**シナリオ:** あなたは会社の DevOps engineer であり、development team のために Amazon EKS cluster をセットアップする必要があります。この cluster は development environment 用で、必要な機能をすべて提供しながら cost-effective である必要があります。

**要件:**

1. cost-effective な EKS cluster を作成する
2. 適切な node groups を構成する
3. basic monitoring を設定する
4. cluster への kubectl access を構成する

**解決策:**

<details>

<summary>解決策を表示</summary>

**1. eksctl を使用して EKS Cluster を作成する**

```bash
# Install eksctl (if not already installed)
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
eksctl version

# Create cluster
cat << EOF > eks-cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: dev-cluster
  region: us-west-2
  version: "1.28"

managedNodeGroups:
  - name: ng-1
    instanceType: t3.medium
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    iam:
      withAddonPolicies:
        imageBuilder: true
        autoScaler: true
        externalDNS: true
        certManager: true
        appMesh: false
        ebs: true
        fsx: false
        efs: false
        albIngress: true
        xRay: false
        cloudWatch: true

cloudWatch:
  clusterLogging:
    enableTypes: ["api", "audit", "authenticator", "controllerManager", "scheduler"]
EOF

eksctl create cluster -f eks-cluster.yaml
```

**2. kubectl を構成して検証する**

```bash
# Update kubectl configuration
aws eks update-kubeconfig --name dev-cluster --region us-west-2

# Verify cluster connection
kubectl get nodes
kubectl cluster-info
```

**3. Basic Monitoring Components を検証する**

```bash
# Check basic system pods
kubectl get pods -n kube-system

# Install metrics server (if not provided by default)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Verify metrics server operation
kubectl get deployment metrics-server -n kube-system
kubectl top nodes
```

**4. AWS Load Balancer Controller をインストールする**

```bash
# Create IAM policy
curl -o iam-policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json
aws iam create-policy \
    --policy-name AWSLoadBalancerControllerIAMPolicy \
    --policy-document file://iam-policy.json

# Set up IRSA
eksctl create iamserviceaccount \
  --cluster=dev-cluster \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn=arn:aws:iam::<AWS_ACCOUNT_ID>:policy/AWSLoadBalancerControllerIAMPolicy \
  --override-existing-serviceaccounts \
  --approve

# Install controller with Helm
helm repo add eks https://aws.github.io/eks-charts
helm repo update
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=dev-cluster \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

**5. Cluster Status を確認する**

```bash
# Check node status
kubectl get nodes -o wide

# Check system pod status
kubectl get pods -n kube-system

# Check cluster events
kubectl get events --sort-by='.lastTimestamp'

# Check cluster info
kubectl cluster-info
```

**6. Test Application をデプロイする**

```bash
# Deploy simple nginx
kubectl create deployment nginx --image=nginx
kubectl expose deployment nginx --port=80 --type=LoadBalancer

# Verify deployment
kubectl get deployment nginx
kubectl get service nginx
```

この演習を通じて、cost-effective な EKS cluster を作成し、basic monitoring を設定し、load balancer controller を構成して applications を外部に公開する方法を学びました。t3.medium instance type は development environments に適した cost-effective な選択肢であり、auto-scaling settings によって必要に応じて nodes をスケールできます。

</details>

### 演習 2: EKS Cluster への Applications のデプロイと Services の公開

**シナリオ:** あなたの team は microservices architecture に基づく web application を開発しました。この application を EKS cluster にデプロイし、外部からアクセスできるように構成する必要があります。

**要件:**

1. frontend と backend services をデプロイする
2. inter-service communication を構成する
3. ingress controller を通じて external access を構成する
4. basic scaling を設定する

**解決策:**

<details>

<summary>解決策を表示</summary>

**1. Namespace を作成する**

```bash
kubectl create namespace web-app
kubectl config set-context --current --namespace=web-app
```

**2. Backend Service をデプロイする**

```yaml
# backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: web-app
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
      - name: backend
        image: nginx:alpine  # Replace with actual backend image
        ports:
        - containerPort: 8080
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
---
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: web-app
spec:
  selector:
    app: backend
  ports:
  - port: 80
    targetPort: 8080
```

```bash
kubectl apply -f backend-deployment.yaml
```

**3. Frontend Service をデプロイする**

```yaml
# frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: web-app
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
      - name: frontend
        image: nginx:alpine  # Replace with actual frontend image
        ports:
        - containerPort: 80
        env:
        - name: BACKEND_URL
          value: "http://backend-service"
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
---
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  namespace: web-app
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 80
```

```bash
kubectl apply -f frontend-deployment.yaml
```

**4. Ingress Resource を作成する (AWS ALB Ingress Controller を使用)**

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-app-ingress
  namespace: web-app
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /
spec:
  rules:
  - http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend-service
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

```bash
kubectl apply -f ingress.yaml
```

**5. Horizontal Pod Autoscaling (HPA) を構成する**

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: frontend-hpa
  namespace: web-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: web-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
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

```bash
kubectl apply -f hpa.yaml
```

**6. Deployment Status を確認する**

```bash
# Check deployment status
kubectl get deployments -n web-app

# Check service status
kubectl get services -n web-app

# Check ingress status
kubectl get ingress -n web-app

# Check HPA status
kubectl get hpa -n web-app

# Get ALB address
kubectl get ingress web-app-ingress -n web-app -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

**7. Load Test を実行し、Scaling を検証する**

```bash
# Get ALB address
ALB_ADDRESS=$(kubectl get ingress web-app-ingress -n web-app -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Load test (requires separate tool)
# Example: Using Apache Bench
ab -n 10000 -c 100 http://$ALB_ADDRESS/

# Verify scaling
kubectl get hpa -n web-app -w
```

この演習を通じて、microservices architecture application を EKS cluster にデプロイし、AWS ALB Ingress Controller を使用して外部に公開し、HPA を通じて auto-scaling を構成する方法を学びました。Resource requests と limits は efficient resource usage を確保するために適切に設定され、path-based routing は ingress rules を通じて実装されました。

</details>

## 高度なトピック

以下は高度な Amazon EKS topics に関する問題です。このセクションでは、高度な EKS features と integrations に関する理解を確認します。

1. Amazon EKS で Fargate profile を構成する際の正しい説明はどれですか？
   * A) Fargate profiles は、特定の namespaces と labels に基づいて pods を Fargate で実行することを指定する
   * B) Fargate profiles はすべての pods を Fargate で自動的に実行する
   * C) Fargate profiles は pod execution を特定の EC2 instance types に制限する
   * D) Fargate profiles は cluster 全体の resource quotas を設定する

<details>

<summary>答えを表示</summary>

**答え: A) Fargate profiles は、特定の namespaces と labels に基づいて pods を Fargate で実行することを指定する**

**解説:** Amazon EKS Fargate profile は、特定の namespaces と labels に基づいて、どの pods を Fargate で実行するかを指定する configuration です。これにより、serverless container execution environments と EC2-based nodes の両方を使用する hybrid architecture を構成できます。

Fargate profiles の主な機能:

* **Selective execution**: すべての pods ではなく、profile で定義された条件に一致する pods のみが Fargate で実行されます。
* **Namespace and label selectors**: Pods は特定の namespace と label の組み合わせに基づいて選択されます。
* **Subnet specification**: pods が実行される private subnets を指定できます。
* **IAM role**: Fargate pods 用の IAM execution role を指定します。

Fargate profile 作成例:

```bash
eksctl create fargateprofile \
  --cluster my-cluster \
  --name my-fargate-profile \
  --namespace my-namespace \
  --labels app=my-app
```

YAML-based Fargate profile definition:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
fargateProfiles:
  - name: my-fargate-profile
    selectors:
      - namespace: my-namespace
        labels:
          app: my-app
      - namespace: another-namespace
```

Fargate を使用する際の考慮事項:

* DaemonSets は Fargate でサポートされません。
* Privileged containers は実行できません。
* HostNetwork と HostPort はサポートされません。
* GPU workloads はサポートされません。
* pod ごとのコストが発生するため、cost planning が必要です。
* storage は ephemeral storage に制限されます (EFS を通じて persistent volumes は可能)。

他の選択肢の問題点:

* Fargate profiles はすべての pods を Fargate で自動的に実行するわけではありません。selectors に一致する pods のみが Fargate で実行されます。
* Fargate profiles は EC2 instance types とは関係ありません。Fargate は serverless container execution environment です。
* Fargate profiles は cluster-wide resource quotas を設定しません。Resource quotas は Kubernetes ResourceQuota を通じて管理されます。

</details>

2. Amazon EKS で cluster upgrade を実行する際の正しい順序はどれですか？
   * A) Worker node upgrade -> Control plane upgrade -> Add-on upgrade
   * B) Control plane upgrade -> Worker node upgrade -> Add-on upgrade
   * C) Add-on upgrade -> Control plane upgrade -> Worker node upgrade
   * D) すべての components を同時に upgrade する

<details>

<summary>答えを表示</summary>

**答え: B) Control plane upgrade -> Worker node upgrade -> Add-on upgrade**

**解説:** Amazon EKS cluster upgrade の正しい順序は、まず control plane を upgrade し、次に worker nodes、最後に add-ons を upgrade することです。この順序は Kubernetes の version compatibility model に従い、upgrade process 中の潜在的な問題を最小限に抑えます。

**1. Control Plane Upgrade**

* control plane は cluster の頭脳として機能し、最初に upgrade する必要があります。
* Kubernetes は、control plane が nodes より最大 2 minor versions 先行できるように設計されています。
* Control plane upgrades は AWS Management Console、AWS CLI、または eksctl を通じて実行できます。

```bash
# Control plane upgrade using AWS CLI
aws eks update-cluster-version --name my-cluster --kubernetes-version 1.28

# Control plane upgrade using eksctl
eksctl upgrade cluster --name=my-cluster --version=1.28 --approve
```

**2. Worker Node Upgrade**

* control plane upgrade が完了したら、worker nodes を upgrade します。
* managed node groups の場合、upgrades は AWS Management Console、AWS CLI、または eksctl を通じて実行できます。
* self-managed nodes の場合、nodes を新しい AMIs に置き換える必要があります。

```bash
# Managed node group upgrade
aws eks update-nodegroup-version --cluster-name my-cluster --nodegroup-name my-nodegroup

# Managed node group upgrade using eksctl
eksctl upgrade nodegroup --cluster=my-cluster --name=my-nodegroup
```

**3. Add-on Upgrade**

* 最後に、cluster add-ons (kube-proxy、CoreDNS、Amazon VPC CNI など) を upgrade します。
* Add-ons は特定の Kubernetes versions と互換性があるように設計されているため、control plane と node upgrades の後に upgrade する必要があります。

```bash
# Add-on upgrade using AWS CLI
aws eks update-addon --cluster-name my-cluster --addon-name vpc-cni --addon-version v1.12.0-eksbuild.1

# Add-on upgrade using eksctl
eksctl update addon --name vpc-cni --version v1.12.0-eksbuild.1 --cluster my-cluster
```

**Upgrade Best Practices:**

* upgrade 前に cluster status を確認し、backup を取得する
* まず test environment で upgrade をテストする
* blue/green deployment strategy を検討する
* upgrade 中の workload disruption を最小限にするため PodDisruptionBudget を構成する
* 一度に 1 minor version ずつ upgrade する
* upgrade 後に workloads と system components を検証する

他の選択肢の問題点:

* control plane の前に worker nodes を upgrade すると、version compatibility issues が発生する可能性があります。
* add-ons を先に upgrade すると、新しい add-on versions が古い Kubernetes version と互換性を持たない可能性があります。
* すべての components を同時に upgrade するのはリスクが高く、問題が発生した場合に原因の特定が困難です。

</details>

3. Amazon EKS の VPC CNI plugin の key feature ではないものはどれですか？
   * A) pods に VPC IP addresses を割り当てる
   * B) pod レベルで security groups を適用する
   * C) pods 間の network traffic を暗号化する
   * D) prefix delegation によって IP addresses を拡張する

<details>

<summary>答えを表示</summary>

**答え: C) pods 間の network traffic を暗号化する**

**解説:** Amazon VPC CNI (Container Network Interface) plugin は、pods 間の network traffic を自動的には暗号化しません。Pod-to-pod traffic encryption は VPC CNI の基本機能ではなく、service meshes (例: AWS App Mesh、Istio) や network policy solutions (例: Calico、Cilium) などの追加ツールが必要です。

Amazon VPC CNI plugin の実際の key features には次が含まれます:

1. **pods への VPC IP addresses の割り当て**:
   * 各 pod は VPC 内で一意の IP address を受け取ります。
   * これにより、pods は VPC 内の他の resources と直接通信できます。
   * Pod IPs は VPC 内で routable であり、複雑な overlay networks は不要です。
2. **pod レベルでの security groups の適用**:
   * SecurityGroupsForPods feature によって、AWS security groups を個々の pods に適用できます。
   * これにより、pod レベルで細かな network security policies を実装できます。
   *   Example configuration:

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
             - sg-0123456789abcdef0
       ```
3. **prefix delegation による IP addresses の拡張**:
   * デフォルトでは、各 node が pods に割り当てられる IP addresses の数は限られています (instance type によって異なります)。
   * prefix delegation feature を使用すると、各 node に /28 CIDR blocks (16 IPs) を割り当てることができ、利用可能な IP addresses を増やせます。
   * これにより、高密度 deployment scenarios での IP address shortage problems を解決できます。
4. **Custom networking**:
   * Pods を特定の subnets に配置できます。
   * Pod networking は複数の network interfaces を使用して構成できます。
5. **Host networking integration**:
   * Pods は host network stack を直接使用できます。
   * network performance が重要な workloads に役立ちます。

VPC CNI configuration examples:

```bash
# Enable prefix delegation
kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true

# Enable security group pods feature
kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true

# Enable custom networking
kubectl set env daemonset aws-node -n kube-system AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true
```

pods 間の network traffic encryption を実装するには、次の代替案を検討してください:

* TLS を使用した AWS App Mesh
* Istio service mesh の実装
* Cilium の transparent encryption feature の使用
* application レベルでの TLS/mTLS の実装

</details>

4. Amazon EKS で cluster authentication のために IAM role-based access control (RBAC) を構成する正しい方法は何ですか？
   * A) Kubernetes RBAC roles を IAM users に直接割り当てる
   * B) aws-auth ConfigMap で IAM role と Kubernetes group mappings を構成する
   * C) IAM policies を EKS cluster に直接 attach する
   * D) IAM roles を Kubernetes service accounts にリンクする

<details>

<summary>答えを表示</summary>

**答え: B) aws-auth ConfigMap で IAM role と Kubernetes group mappings を構成する**

**解説:** Amazon EKS で cluster authentication のために IAM role-based access control (RBAC) を構成する正しい方法は、`aws-auth` ConfigMap を使用して IAM roles と Kubernetes groups の mappings を構成することです。この方法により、AWS IAM credentials と Kubernetes RBAC system を統合できます。

**aws-auth ConfigMap の仕組み:**

1. EKS は AWS IAM Authenticator を使用して API requests を認証します。
2. `aws-auth` ConfigMap は IAM entities (users または roles) を Kubernetes users と groups にマッピングします。
3. Kubernetes RBAC system はこれらの users と groups に permissions を付与します。

**aws-auth ConfigMap configuration example:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: arn:aws:iam::123456789012:role/EksAdminRole
      username: eks-admin
      groups:
        - system:masters
    - rolearn: arn:aws:iam::123456789012:role/DevTeamRole
      username: dev-team
      groups:
        - dev-group
  mapUsers: |
    - userarn: arn:aws:iam::123456789012:user/admin-user
      username: admin
      groups:
        - system:masters
    - userarn: arn:aws:iam::123456789012:user/read-only-user
      username: read-only
      groups:
        - read-only-group
```

**Kubernetes RBAC role and binding configuration:**

```yaml
# Create developer role
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: dev
  name: developer
rules:
- apiGroups: ["", "apps", "batch"]
  resources: ["pods", "deployments", "jobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]

---
# Bind role to developer group
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-binding
  namespace: dev
subjects:
- kind: Group
  name: dev-group
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer
  apiGroup: rbac.authorization.k8s.io
```

**eksctl を使用した IAM と RBAC の構成:**

```bash
# Add IAM role mapping
eksctl create iamidentitymapping \
  --cluster my-cluster \
  --arn arn:aws:iam::123456789012:role/EksAdminRole \
  --username eks-admin \
  --group system:masters

# Add IAM user mapping
eksctl create iamidentitymapping \
  --cluster my-cluster \
  --arn arn:aws:iam::123456789012:user/admin-user \
  --username admin \
  --group system:masters
```

**Best practices:**

* principle of least privilege を適用する
* 個別の IAM users より IAM roles を優先する
* namespace ごとに permissions を分離する
* access permissions を定期的に review する
* cluster administrator permissions (system:masters) は慎重に付与する

他の選択肢の問題点:

* Kubernetes RBAC roles を IAM users に直接割り当てることはできません。IAM と Kubernetes は別々の systems であるため、aws-auth ConfigMap を通じた mapping が必要です。
* IAM policies を EKS cluster に直接 attach することは、cluster 内の RBAC permissions とは関係ありません。IAM policies は cluster 自体への API call permissions を制御します。
* IAM roles を Kubernetes service accounts にリンクすること (IRSA) は、pods が AWS services にアクセスするためのものであり、cluster authentication と authorization とは異なる目的です。

</details>

5. Amazon EKS の Kubernetes version support policy の正しい説明はどれですか？
   * A) すべての Kubernetes versions が無期限にサポートされる
   * B) 各 Kubernetes version は release 後 12 か月間サポートされる
   * C) latest version と previous 3 versions のみがサポートされる
   * D) 各 Kubernetes version は release 後 14 か月間サポートされる

<details>

<summary>答えを表示</summary>

**答え: D) 各 Kubernetes version は release 後 14 か月間サポートされる**

**解説:** Amazon EKS の Kubernetes version support policy によると、各 Kubernetes version は EKS での release 後 14 か月間サポートされます。この期間の後、その version はサポート対象外となり、cluster をサポートされている version に upgrade する必要があります。

**EKS version support policy の主な特徴:**

1. **14-month support period**:
   * 各 Kubernetes version は EKS で release された日から 14 か月間サポートされます。
   * Support end dates は AWS によって事前に発表されます。
2. **Standard support schedule**:
   * Kubernetes community は約 4 か月ごとに新しい version を release します。
   * EKS は通常、community release 後 2〜3 か月以内に新しい Kubernetes versions をサポートします。
   * これにより、通常は 3〜4 個の Kubernetes versions が EKS で同時にサポートされます。
3. **No automatic upgrades**:
   * support が終了しても AWS は clusters を自動的には upgrade しません。
   * Cluster administrators が明示的に upgrades を実行する必要があります。
4. **Impact after support ends**:
   * サポート対象外の versions で実行されている clusters は動作を続けますが、AWS は security patches や bug fixes を提供しなくなります。
   * サポート対象外の versions では新しい clusters を作成できません。
   * AWS support は利用できません。

**Version upgrade best practices:**

* 定期的な upgrade schedules を確立する
* support end dates を監視する
* まず test environments で upgrades をテストする
* upgrade 前に cluster を backup する
* 一度に 1 minor version ずつ upgrade する
* blue/green deployment strategy を検討する

**version support status の確認:**

```bash
# Check available EKS versions
aws eks describe-addon-versions | grep kubernetesVersion

# Check specific cluster version
aws eks describe-cluster --name my-cluster --query "cluster.version"
```

他の選択肢の問題点:

* すべての Kubernetes versions が無期限にサポートされるわけではありません。各 version は定められた期間のみサポートされます。
* 各 version は 12 か月ではなく 14 か月間サポートされます。
* 「latest version と previous 3 versions のみがサポートされる」という固定ルールはありません。サポートされる versions の数は Kubernetes community release schedule と EKS support policy に基づいて変わります。

</details>

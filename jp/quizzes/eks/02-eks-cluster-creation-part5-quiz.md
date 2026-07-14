# EKS Cluster 作成クイズ - Part 5

このクイズでは、Amazon EKS cluster の高度な設定、最適化、運用上のベストプラクティスについての理解を確認します。cost optimization、高可用性設計、security 強化、運用自動化に焦点を当てています。

## 選択問題

### 1. Amazon EKS cluster でコストを最適化する最も効果的な方法は何ですか？

A. すべての worker node を On-Demand instances として実行する B. Spot instances と On-Demand instances を組み合わせて使用する C. すべての worker node を Reserved instances として実行する D. すべての worker node を Fargate で実行する

<details>

<summary>回答と解説</summary>

**回答: B. Spot instances と On-Demand instances を組み合わせて使用する**

**解説:** EKS cluster でコストを最適化する最も効果的な方法は、Spot instances と On-Demand instances を組み合わせて使用することです。

* **Spot instances**: On-Demand pricing より最大 90% 安価ですが、AWS が capacity を回収すると中断される可能性があります。fault-tolerant な stateless workloads に適しています。
* **On-Demand instances**: 価格は高いものの安定しており、重要な stateful workloads や中断に敏感な applications に適しています。

この組み合わせアプローチにより、次のことができます。

1. 重要な workloads を On-Demand instances で実行する
2. fault-tolerant な workloads を Spot instances で実行する
3. node affinity、tolerations、taints を使用して workload 配置を制御する

追加の cost optimization 戦略には、Karpenter または Cluster Autoscaler を使用した auto-scaling、適切な instance size の選択、Graviton (ARM) instances の使用、Reserved Instances または Savings Plans の活用が含まれます。

</details>

### 2. EKS cluster で複数の Availability Zones (AZs) に node をデプロイする主な理由は何ですか？

A. network latency を削減する B. data throughput を増加させる C. high availability と fault tolerance を向上させる D. AWS regions 間で data replication を有効にする

<details>

<summary>回答と解説</summary>

**回答: C. high availability と fault tolerance を向上させる**

**解説:** EKS cluster で複数の Availability Zones (AZs) に node をデプロイする主な理由は、high availability と fault tolerance を向上させることです。

1. **AZ Failure Response**: 1 つの AZ に障害が発生しても、他の AZ の nodes は稼働を継続し、application availability を維持します。
2. **Infrastructure Redundancy**: 複数の AZ に workloads を分散することで、物理 infrastructure 障害に対する保護層を追加できます。
3. **Automatic Recovery**: Kubernetes は、障害が発生した nodes から正常な nodes へ Pod を自動的に再スケジュールし、service disruption を最小化します。
4. **Rolling Update Stability**: workloads が複数の AZ に分散されているため、更新中も availability が維持されます。

EKS はデフォルトで control plane を複数の AZ にデプロイしますが、cluster 全体の high availability を確保するために、worker nodes も複数の AZ にデプロイすることがベストプラクティスです。node groups を作成するときに、複数の subnets (それぞれ異なる AZ に配置) を指定できます。

</details>

### 3. EKS cluster の Pod networking におけるデフォルトの CNI plugin は何ですか？

A. Calico B. Flannel C. Amazon VPC CNI D. Weave Net

<details>

<summary>回答と解説</summary>

**回答: C. Amazon VPC CNI**

**解説:** Amazon EKS clusters における Pod networking のデフォルト CNI (Container Network Interface) plugin は Amazon VPC CNI です。この plugin の主な特徴は次のとおりです。

1. **Native VPC Networking**: 各 Pod は VPC 内で一意の IP address を受け取り、AWS VPC networking を直接利用します。
2. **Security Group Integration**: AWS security groups を Pod level で適用でき、きめ細かな network security control が可能になります。
3. **IP Address Management**: 各 node には VPC subnets から secondary IP addresses が割り当てられ、Pod に提供されます。
4. **Performance**: overlay networks を使用しないため、network performance が向上します。
5. **AWS Service Integration**: AWS Load Balancer Controller、AWS App Mesh などの他の AWS services とシームレスに統合されます。

Amazon VPC CNI は open source であり、GitHub 上で管理されています。必要に応じて Calico や Cilium などの他の CNI plugins に置き換えることもできますが、Amazon VPC CNI は EKS のデフォルト option であり、AWS によって公式にサポートされています。

</details>

### 4. EKS cluster で IAM roles を Kubernetes service accounts に関連付ける機能の名前は何ですか？

A. IAM for Service Accounts (IRSA) B. Pod Identity Webhook C. Kubernetes IAM Authenticator D. EKS Identity Manager

<details>

<summary>回答と解説</summary>

**回答: A. IAM for Service Accounts (IRSA)**

**解説:** EKS cluster で IAM roles を Kubernetes service accounts に関連付ける機能は、IAM for Service Accounts (IRSA) です。この機能の主な特徴は次のとおりです。

1. **Fine-grained Permission Control**: node level で広範な permissions を付与することを避け、Pod level で AWS resources への access を制御できます。
2. **OIDC-based Authentication**: EKS は OpenID Connect (OIDC) provider を使用して、Kubernetes service accounts と IAM roles の間に trust relationships を確立します。
3. **Enhanced Security**: application ごとに必要最小限の permissions のみを付与することで、least privilege の原則を実装できます。
4. **Implementation Method**:
   * EKS cluster 用の OIDC provider を作成する
   * service account を信頼する IAM role を作成する
   * 特定の annotation を持つ Kubernetes service account を作成する
   * その service account を使用して Pod をデプロイする

IRSA を使用すると、AWS SDK を使用する applications は、node の IAM role に依存する代わりに、自分自身の IAM role を使用して AWS services に安全に access できます。

</details>

### 5. EKS cluster で node group Auto Scaling を管理する Kubernetes-native tool は何ですか？

A. Horizontal Pod Autoscaler B. Vertical Pod Autoscaler C. Cluster Autoscaler D. Node Autoscaler

<details>

<summary>回答と解説</summary>

**回答: C. Cluster Autoscaler**

**解説:** EKS cluster で node group Auto Scaling を管理する Kubernetes-native tool は Cluster Autoscaler です。この tool の主な特徴は次のとおりです。

1. **Automatic Scaling**: resource 不足により Pod をスケジュールできない場合に node を自動的に追加し、使用率が低い場合に node を削除します。
2. **AWS Auto Scaling Group Integration**: EKS の AWS Auto Scaling Groups と統合して動作します。
3. **How It Works**:
   * Scale Out: resource constraints により Pod が Pending 状態の場合に node を追加します
   * Scale In: utilization が低く、Pod を他の nodes に移動できる場合に node を削除します
4. **Configuration Options**:
   * scale up/down thresholds を設定する
   * node group discovery method を指定する
   * scale down delay を設定する
   * Pod Disruption Budgets (PDB) を尊重する

Horizontal Pod Autoscaler (HPA) は Pod 数を自動的に調整し、Vertical Pod Autoscaler (VPA) は Pod resource requests を自動的に調整しますが、node 数を調整する役割は Cluster Autoscaler が担います。

AWS は新しい node provisioning tool として Karpenter も提供しており、より高速で柔軟な node provisioning 機能を提供します。

</details>

## 短答問題

### 6. EKS cluster で Kubernetes control plane logs を有効化し、CloudWatch Logs に送信するにはどのような設定が必要ですか？

<details>

<summary>回答と解説</summary>

Kubernetes control plane logs を EKS cluster から CloudWatch Logs に送信するには、cluster 作成時または既存の cluster で特定の log types を有効にする必要があります。

**必要な設定:**

1. **Log Types を有効化**: 次の log types のうち 1 つ以上を有効にします。
   * `api`: Kubernetes API server logs
   * `audit`: Kubernetes audit logs
   * `authenticator`: AWS IAM authenticator logs
   * `controllerManager`: Controller manager logs
   * `scheduler`: Scheduler logs
2. **AWS Management Console から有効化**:
   * EKS console で cluster を選択する
   * "Logging" tab を選択する
   * 必要な log types を有効にする
3. **AWS CLI から有効化**:

```bash
aws eks update-cluster-config \
    --region region-code \
    --name cluster-name \
    --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

4. **eksctl から有効化**:

```bash
eksctl utils update-cluster-logging \
    --region=region-code \
    --cluster=cluster-name \
    --enable-types=api,audit,authenticator,controllerManager,scheduler
```

有効化された logs は、CloudWatch Logs log group `/aws/eks/cluster-name/cluster` に自動的に送信されます。各 log type は個別の log stream として保存されます。

**注意事項:**

* logs を有効にすると追加コストが発生します (CloudWatch Logs pricing が適用されます)。
* 特に audit logs は大量の data を生成する可能性があるため、cost management に注意してください。
* cost を管理するために log retention periods を設定してください。

</details>

### 7. EKS cluster で worker nodes から kubelet logs を CloudWatch Logs に送信するにはどうすればよいですか？

<details>

<summary>回答と解説</summary>

EKS cluster で worker nodes から kubelet logs を CloudWatch Logs に送信するには、CloudWatch agent をインストールして設定する必要があります。control plane logs とは異なり、worker node logs は CloudWatch に自動的には送信されません。

**Implementation Steps:**

1. **CloudWatch Agent をインストール**: CloudWatch agent を Kubernetes の DaemonSet としてデプロイします。
2. **Fluentd または Fluent Bit を設定**: kubelet logs を CloudWatch Logs に送信するように log collector を設定します。
3.  **推奨方法: Amazon EKS Add-on を使用**:

    ```bash
    # Create namespace for CloudWatch log collection
    kubectl create namespace amazon-cloudwatch

    # Create service account for AWS observability access
    eksctl create iamserviceaccount \
        --name cloudwatch-agent \
        --namespace amazon-cloudwatch \
        --cluster my-cluster \
        --attach-policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy \
        --approve \
        --override-existing-serviceaccounts

    # Create service account for Fluent Bit
    eksctl create iamserviceaccount \
        --name fluent-bit \
        --namespace amazon-cloudwatch \
        --cluster my-cluster \
        --attach-policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy \
        --approve \
        --override-existing-serviceaccounts

    # Install CloudWatch agent and Fluent Bit
    kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluent-bit-quickstart.yaml
    ```
4.  **Configuration をカスタマイズ**: 特定の log paths と formats を収集するように ConfigMap を変更します。

    ```yaml
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: fluent-bit-config
      namespace: amazon-cloudwatch
    data:
      fluent-bit.conf: |
        [INPUT]
            Name tail
            Path /var/log/kubelet.log
            Tag kubelet
        [OUTPUT]
            Name cloudwatch
            Match kubelet
            region region-name
            log_group_name /aws/eks/my-cluster/nodes
            log_stream_prefix kubelet-
            auto_create_group true
    ```
5. **Logs を確認**: CloudWatch Logs console で log group `/aws/eks/my-cluster/nodes` を確認します。

**主な Log Collection Targets:**

* `/var/log/kubelet.log`: kubelet logs
* `/var/log/kube-proxy.log`: kube-proxy logs
* `/var/log/aws-routed-eni/ipamd.log`: VPC CNI logs
* `/var/log/containers/*.log`: container logs

**Alternative Methods:**

* AWS Distro for OpenTelemetry (ADOT) を使用する
* Amazon OpenSearch と Fluent Bit の組み合わせを使用する
* custom logging solution (例: ELK stack) を構築する

**Best Practices:**

* log retention period settings で cost を管理する
* 必要な logs のみを選択的に収集する
* log filtering により重要な情報のみを収集する
* log groups に tag を付けて cost を追跡する

</details>

### 8. Pod Security Policy (PSP) が EKS clusters で使われなくなった理由は何ですか？また、代替手段は何ですか？

<details>

<summary>回答と解説</summary>

Pod Security Policy (PSP) は Kubernetes version 1.21 以降 deprecated となり、Kubernetes 1.25 で完全に削除されました。そのため、EKS は PSP をサポートしなくなりました。

**Deprecation の理由:**

1. **Complexity**: PSP は設定と理解が困難でした。
2. **Debugging Difficulty**: PSP violations が発生したときに明確な error messages を提供せず、troubleshooting が困難でした。
3. **Limited Flexibility**: 特定の scenarios では fine-grained control が困難でした。
4. **Lack of Consistency**: 他の Kubernetes security mechanisms との統合がスムーズではありませんでした。

**代替手段:**

1. **Pod Security Standards (PSS) / Pod Security Admission (PSA)**:
   * Kubernetes 1.22 以降に導入された公式の代替手段
   * Privileged、Baseline、Restricted の 3 つの security levels を提供
   * namespace labels を通じて適用
   *   Example:

       ```yaml
       apiVersion: v1
       kind: Namespace
       metadata:
         name: my-namespace
         labels:
           pod-security.kubernetes.io/enforce: restricted
           pod-security.kubernetes.io/audit: restricted
           pod-security.kubernetes.io/warn: restricted
       ```
2. **Kyverno**:
   * YAML-based policy definitions を持つ policy engine
   * PSP より柔軟で強力な機能を提供
   * validation、mutation、generation、cleanup policies をサポート
   *   Example:

       ```yaml
       apiVersion: kyverno.io/v1
       kind: ClusterPolicy
       metadata:
         name: restrict-privileged
       spec:
         validationFailureAction: enforce
         rules:
         - name: privileged-containers
           match:
             resources:
               kinds:
               - Pod
           validate:
             message: "Privileged containers are not allowed"
             pattern:
               spec:
                 containers:
                   - name: "*"
                     securityContext:
                       privileged: false
       ```
3. **OPA Gatekeeper**:
   * Open Policy Agent に基づく policy controller
   * Rego language を使用した policy definitions
   * ConstraintTemplate と Constraint concepts を使用
   *   Example:

       ```yaml
       apiVersion: templates.gatekeeper.sh/v1beta1
       kind: ConstraintTemplate
       metadata:
         name: k8spsprivilegedcontainer
       spec:
         crd:
           spec:
             names:
               kind: K8sPSPPrivilegedContainer
         targets:
           - target: admission.k8s.gatekeeper.sh
             rego: |
               package k8spsprivilegedcontainer
               violation[{"msg": msg}] {
                 c := input.review.object.spec.containers[_]
                 c.securityContext.privileged
                 msg := "Privileged containers are not allowed"
               }
       ```
4. **AWS Built-in Security Features**:
   * Amazon GuardDuty for EKS Protection
   * AWS Security Hub の EKS security standards
   * Amazon Inspector for EKS

**Migration Strategy:**

1. 現在の PSP policies を分析して文書化する
2. 置き換え solution (PSA、Kyverno、OPA Gatekeeper など) を選択する
3. 影響を評価するため、新しい policies を audit mode でデプロイする
4. policies を段階的に適用する (enforce mode へ移行)
5. monitoring と logging settings で policy violations を追跡する

EKS 1.25 以上へ upgrade する前に、PSP から代替 solution へ移行することが重要です。

</details>

## ハンズオン問題

### 9. EKS cluster で cost optimization のために Spot instances と On-Demand instances を組み合わせて使用する node group configuration を作成してください。次の要件を満たす必要があります。

* 重要な workloads 用の On-Demand node group (2-5 nodes)
* general workloads 用の Spot node group (2-10 nodes)
* 適切な node labels と taints
* workload placement のための node affinity と tolerations の例

<details>

<summary>回答と解説</summary>

EKS cluster で cost optimization のために Spot instances と On-Demand instances を組み合わせて使用する node group configuration は次のとおりです。

#### 1. On-Demand Node Group Configuration (for Critical Workloads)

**eksctl を使用した Configuration:**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
nodeGroups:
  - name: critical-workloads
    instanceType: m5.xlarge
    desiredCapacity: 2
    minSize: 2
    maxSize: 5
    capacityType: ON_DEMAND
    labels:
      workload-type: critical
      node-lifecycle: on-demand
    tags:
      k8s.io/cluster-autoscaler/enabled: "true"
      k8s.io/cluster-autoscaler/my-cluster: "owned"
    iam:
      withAddonPolicies:
        autoScaler: true
    ssh:
      allow: false
```

**AWS CLI を使用した Configuration:**

```bash
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name critical-workloads \
  --scaling-config minSize=2,maxSize=5,desiredSize=2 \
  --instance-types m5.xlarge \
  --capacity-type ON_DEMAND \
  --subnets subnet-0a1b2c3d4e5f6g7h8 subnet-0a1b2c3d4e5f6g7h9 \
  --node-role arn:aws:iam::123456789012:role/EKS-NodeInstanceRole \
  --labels workload-type=critical,node-lifecycle=on-demand \
  --tags "k8s.io/cluster-autoscaler/enabled=true,k8s.io/cluster-autoscaler/my-cluster=owned"
```

#### 2. Spot Node Group Configuration (for General Workloads)

**eksctl を使用した Configuration:**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
nodeGroups:
  - name: general-workloads
    instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5ad.large"]
    desiredCapacity: 3
    minSize: 2
    maxSize: 10
    capacityType: SPOT
    labels:
      workload-type: general
      node-lifecycle: spot
    taints:
      - key: spot
        value: "true"
        effect: PreferNoSchedule
    tags:
      k8s.io/cluster-autoscaler/enabled: "true"
      k8s.io/cluster-autoscaler/my-cluster: "owned"
    iam:
      withAddonPolicies:
        autoScaler: true
    ssh:
      allow: false
```

**AWS CLI を使用した Configuration:**

```bash
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name general-workloads \
  --scaling-config minSize=2,maxSize=10,desiredSize=3 \
  --instance-types m5.large m5a.large m5d.large m5ad.large \
  --capacity-type SPOT \
  --subnets subnet-0a1b2c3d4e5f6g7h8 subnet-0a1b2c3d4e5f6g7h9 \
  --node-role arn:aws:iam::123456789012:role/EKS-NodeInstanceRole \
  --labels workload-type=general,node-lifecycle=spot \
  --taints "spot=true:PreferNoSchedule" \
  --tags "k8s.io/cluster-autoscaler/enabled=true,k8s.io/cluster-autoscaler/my-cluster=owned"
```

#### 3. Node Affinity and Tolerations Example for Workload Placement

**Critical Workload Deployment Example (On-Demand nodes を優先):**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: critical-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: critical-app
  template:
    metadata:
      labels:
        app: critical-app
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: workload-type
                operator: In
                values:
                - critical
              - key: node-lifecycle
                operator: In
                values:
                - on-demand
      containers:
      - name: critical-app
        image: my-critical-app:latest
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
```

**General Workload Deployment Example (Spot nodes を許可):**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: general-app
spec:
  replicas: 5
  selector:
    matchLabels:
      app: general-app
  template:
    metadata:
      labels:
        app: general-app
    spec:
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 1
            preference:
              matchExpressions:
              - key: node-lifecycle
                operator: In
                values:
                - spot
      tolerations:
      - key: "spot"
        operator: "Equal"
        value: "true"
        effect: "PreferNoSchedule"
      containers:
      - name: general-app
        image: my-general-app:latest
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

#### 4. 追加の Optimization Settings

**Cluster Autoscaler Deployment:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
  labels:
    app: cluster-autoscaler
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
        - --balance-similar-node-groups
        - --skip-nodes-with-system-pods=false
```

**AWS Node Termination Handler (Spot instance interruption handling):**

```bash
helm repo add eks https://aws.github.io/eks-charts
helm install aws-node-termination-handler \
  --namespace kube-system \
  --set enableSpotInterruptionDraining=true \
  --set enableRebalanceMonitoring=true \
  --set enableRebalanceDraining=true \
  eks/aws-node-termination-handler
```

#### 5. Best Practices と考慮事項

1. **Use Various Instance Types**: Spot node groups で複数の instance types を使用すると、中断リスクを分散できます。
2.  **Set Pod Disruption Budgets (PDB)**: 重要な applications に PDBs を設定し、同時に disruption される Pod 数を制限します。

    ```yaml
    apiVersion: policy/v1
    kind: PodDisruptionBudget
    metadata:
      name: critical-app-pdb
    spec:
      minAvailable: 2
      selector:
        matchLabels:
          app: critical-app
    ```
3. **Set Appropriate Resource Requests and Limits**: node resources を効率的に利用するため、適切な container resource requests と limits を設定します。
4.  **Utilize Horizontal Pod Autoscaler**: workload demand に基づいて Pod 数を自動的に調整します。

    ```yaml
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    metadata:
      name: general-app-hpa
    spec:
      scaleTargetRef:
        apiVersion: apps/v1
        kind: Deployment
        name: general-app
      minReplicas: 3
      maxReplicas: 10
      metrics:
      - type: Resource
        resource:
          name: cpu
          target:
            type: Utilization
            averageUtilization: 70
    ```
5. **Cost Monitoring and Optimization**: AWS Cost Explorer や Kubecost などの tools を使用して cluster costs を monitor し、最適化します。

</details>

## 応用問題

### 10. EKS cluster で multi-tenancy を実装する戦略を説明し、各 approach の advantages と disadvantages を比較してください。

<details>

<summary>回答と解説</summary>

EKS cluster で multi-tenancy を実装するとは、複数の teams、applications、または customers が同じ Kubernetes infrastructure を共有しながら、適切な isolation と resource management を確保することを意味します。以下は、EKS で multi-tenancy を実装する主な戦略と、各 approach の advantages と disadvantages です。

### 1. Cluster-Level Separation (Hard Multi-tenancy)

**Description**: tenant ごとに個別の EKS clusters を provision します。

**Implementation Method**:

```bash
# Create cluster for Tenant A
eksctl create cluster --name tenant-a-cluster --region us-west-2

# Create cluster for Tenant B
eksctl create cluster --name tenant-b-cluster --region us-west-2
```

**Advantages**:

* 完全な isolation (security、networking、resources) を確保できる
* tenant ごとに cluster versions と configurations をカスタマイズできる
* 1 つの tenant の問題が他に影響しない
* 厳格な regulatory requirements がある environments に適している

**Disadvantages**:

* operational overhead が大きい (複数 clusters の管理)
* resource utilization が低下する (cluster ごとに control plane と system components が重複)
* costs が増加する (cluster ごとの control plane cost)
* centralized management と policy enforcement が難しい

### 2. Namespace-Level Separation (Soft Multi-tenancy)

**Description**: 単一の EKS cluster 内で Kubernetes namespaces を使用して tenants を分離します。

**Implementation Method**:

```yaml
# Create namespace for Tenant A
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-a
  labels:
    tenant: a

# Create namespace for Tenant B
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-b
  labels:
    tenant: b
```

**Advantages**:

* 単一 cluster によって management が簡素化される
* resource utilization が向上する
* cost efficiency が高い (shared control plane)
* centralized management と policy enforcement が容易になる

**Disadvantages**:

* 完全な isolation の確保が難しい
* cluster-level resources の共有により security risks がある
* 1 つの tenant による過剰な resource usage が他に影響する可能性がある
* cluster upgrades がすべての tenants に影響する

### 3. Namespace-Level Separation + Additional Security Controls

**Description**: namespace separation に追加の security と resource control mechanisms を適用します。

**Implementation Method**:

1. **Network Policies**:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-cross-tenant-traffic
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          tenant: a
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          tenant: a
```

2. **Resource Quotas**:

```yaml
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
```

3. **RBAC Permission Control**:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-admin
  namespace: tenant-a
subjects:
- kind: Group
  name: tenant-a-admins
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: tenant-admin-role
  apiGroup: rbac.authorization.k8s.io
```

**Advantages**:

* namespace separation の advantages を維持できる
* security と resource isolation が強化される
* tenant ごとの access control と resource allocation が可能
* cost efficiency を維持できる

**Disadvantages**:

* configuration と management complexity が増加する
* cluster-level resources の完全な isolation は依然として不足する
* policy setup と maintenance に追加の effort が必要

### 4. Virtual Clusters

**Description**: 単一の物理 EKS cluster 内に仮想 Kubernetes control planes を作成し、各 tenant に独自の "cluster" を提供します。

**Implementation Method**:

```bash
# Install vcluster
helm repo add vcluster https://charts.loft.sh
helm repo update

# Create virtual cluster for Tenant A
helm install vcluster-tenant-a vcluster/vcluster \
  --namespace tenant-a \
  --create-namespace \
  --set sync.nodes.enabled=true

# Create virtual cluster for Tenant B
helm install vcluster-tenant-b vcluster/vcluster \
  --namespace tenant-b \
  --create-namespace \
  --set sync.nodes.enabled=true
```

**Advantages**:

* cluster-level と namespace-level separation の advantages を組み合わせられる
* tenant ごとに専用の Kubernetes API server と control plane を提供できる
* resource utilization と cost efficiency が向上する
* tenant ごとに cluster versions と configurations をカスタマイズできる

**Disadvantages**:

* 追加の overhead と complexity が発生する
* virtual cluster technology の maturity と support が限定的
* 一部の Kubernetes features の support が限定的
* debugging と troubleshooting が複雑になる

### 5. AWS Service Integration を活用した Multi-tenancy

**Description**: AWS IAM、AWS Organizations、AWS Resource Access Manager などの AWS services を使用して、EKS cluster multi-tenancy を強化します。

**Implementation Method**:

1. **IAM Roles for Service Accounts (IRSA)**:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: tenant-a-sa
  namespace: tenant-a
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/tenant-a-role
```

2. **AWS Organizations and SCP (Service Control Policies)**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyAccessToOtherTenantsResources",
      "Effect": "Deny",
      "Action": ["s3:*"],
      "Resource": ["arn:aws:s3:::tenant-b-*"]
    }
  ]
}
```

**Advantages**:

* AWS services に対する fine-grained access control が可能
* organizational structure と policies を活用して governance を強化できる
* AWS service level で追加の isolation layer を提供できる
* 既存の AWS security model と統合できる

**Disadvantages**:

* AWS services への dependency が増加する
* configuration と management complexity が増加する
* AWS-specific solution のため portability が限定的
* 追加の AWS service costs が発生する可能性がある

### Multi-tenancy Implementation の Best Practices

1. **Requirements を分析**:
   * tenants 間で必要な isolation level を評価する
   * regulatory と compliance requirements を考慮する
   * operational overhead と cost constraints を考慮する
2. **Hybrid Approach を検討**:
   * critical tenants には dedicated clusters を提供する
   * 重要度の低い tenants は namespace-level separation でグループ化する
3. **Automation and IaC (Infrastructure as Code)**:
   * Terraform、AWS CDK、または eksctl を使用して cluster と namespace provisioning を自動化する
   * GitOps workflows を通じて configurations を管理する
4. **Monitoring and Cost Allocation**:
   * tenant ごとの resource usage を monitor する
   * cost allocation tags を使用して tenant ごとの costs を追跡する
   * Kubecost または AWS Cost Explorer を使用して costs を分析する
5. **Security Enhancement**:
   * 定期的な security audits と vulnerability scanning
   * least privilege の原則を適用する
   * network policies と service mesh を活用する

### Conclusion

EKS で multi-tenancy を実装するための最適な戦略は、organization の specific requirements、security needs、operational capabilities、cost constraints によって異なります。多くの organizations は、単一の approach ではなく、複数の strategies を組み合わせた hybrid approach を採用しています。たとえば、critical または regulated workloads には dedicated clusters を使用し、development and test environments には namespace-level separation を適用します。

multi-tenancy strategy を選択するときは、security、isolation、resource utilization、operational overhead、cost などの factors のバランスを取る必要があります。また、選択した strategy が、時間とともに変化する organization の requirements に適応できるかを評価することも重要です。

</details>

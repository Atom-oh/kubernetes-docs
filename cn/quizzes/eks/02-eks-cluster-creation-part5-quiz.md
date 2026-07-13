# EKS Cluster 创建测验 - 第 5 部分

本测验用于测试你对 Amazon EKS 集群高级配置、优化和运维最佳实践的理解。内容重点包括成本优化、高可用设计、安全增强和运维自动化。

## 选择题

### 1. 在 Amazon EKS 集群中优化成本最有效的方法是什么？

A. 将所有工作节点作为 On-Demand instances 运行 B. 混合使用 Spot instances 和 On-Demand instances C. 将所有工作节点作为 Reserved instances 运行 D. 将所有工作节点运行在 Fargate 上

<details>

<summary>答案和解释</summary>

**答案：B. 混合使用 Spot instances 和 On-Demand instances**

**解释：** 在 EKS 集群中优化成本最有效的方法是混合使用 Spot instances 和 On-Demand instances：

* **Spot instances**：比 On-Demand 定价最多便宜 90%，但当 AWS 回收容量时可能会被中断。适用于可容错的无状态工作负载。
* **On-Demand instances**：价格更高但稳定，适用于关键的有状态工作负载或对中断敏感的应用程序。

通过这种混合方式：

1. 在 On-Demand instances 上运行关键工作负载
2. 在 Spot instances 上运行可容错工作负载
3. 使用 node affinity、tolerations 和 taints 控制工作负载放置

其他成本优化策略包括使用 Karpenter 或 Cluster Autoscaler 进行 auto-scaling、选择合适的实例大小、使用 Graviton (ARM) instances，以及使用 Reserved Instances 或 Savings Plans。

</details>

### 2. 在 EKS 集群中跨多个 Availability Zones (AZs) 部署节点的主要原因是什么？

A. 降低网络延迟 B. 增加数据吞吐量 C. 提高高可用性和容错能力 D. 支持跨 AWS 区域的数据复制

<details>

<summary>答案和解释</summary>

**答案：C. 提高高可用性和容错能力**

**解释：** 在 EKS 集群中跨多个 Availability Zones (AZs) 部署节点的主要原因是提高高可用性和容错能力：

1. **AZ 故障响应**：如果一个 AZ 发生故障，其他 AZ 中的节点会继续运行，从而维持应用程序可用性。
2. **基础设施冗余**：将工作负载分布到多个 AZ，可增加一层针对物理基础设施故障的保护。
3. **自动恢复**：Kubernetes 会自动将 pods 从故障节点重新调度到健康节点，从而最大限度减少服务中断。
4. **Rolling Update 稳定性**：由于工作负载分布在多个 AZ 中，更新期间仍可保持可用性。

EKS 默认将 control plane 跨多个 AZ 部署，但跨多个 AZ 部署工作节点也是确保整体集群高可用性的最佳实践。创建 node groups 时可以指定多个 subnets（每个 subnet 位于不同 AZ 中）。

</details>

### 3. EKS 集群中用于 pod 网络的默认 CNI plugin 是什么？

A. Calico B. Flannel C. Amazon VPC CNI D. Weave Net

<details>

<summary>答案和解释</summary>

**答案：C. Amazon VPC CNI**

**解释：** Amazon EKS 集群中用于 pod 网络的默认 CNI (Container Network Interface) plugin 是 Amazon VPC CNI。该 plugin 的主要特点是：

1. **原生 VPC 网络**：每个 pod 都会获得 VPC 内的唯一 IP 地址，直接使用 AWS VPC 网络。
2. **Security Group 集成**：AWS security groups 可以应用到 pod 级别，从而实现细粒度的网络安全控制。
3. **IP 地址管理**：每个节点都会从 VPC subnets 分配 secondary IP addresses，以提供给 pods 使用。
4. **性能**：由于不使用 overlay networks，因此网络性能得到提升。
5. **AWS Service 集成**：可与 AWS Load Balancer Controller、AWS App Mesh 等其他 AWS services 无缝集成。

Amazon VPC CNI 是开源项目，并在 GitHub 上管理。它可以根据需要替换为 Calico 或 Cilium 等其他 CNI plugins，但 Amazon VPC CNI 是 EKS 的默认选项，并由 AWS 官方支持。

</details>

### 4. 在 EKS 集群中，将 IAM roles 与 Kubernetes service accounts 关联的功能叫什么？

A. IAM for Service Accounts (IRSA) B. Pod Identity Webhook C. Kubernetes IAM Authenticator D. EKS Identity Manager

<details>

<summary>答案和解释</summary>

**答案：A. IAM for Service Accounts (IRSA)**

**解释：** 在 EKS 集群中，将 IAM roles 与 Kubernetes service accounts 关联的功能是 IAM for Service Accounts (IRSA)。该功能的主要特点是：

1. **细粒度权限控制**：在 pod 级别控制对 AWS resources 的访问，避免在节点级别授予过宽的权限。
2. **基于 OIDC 的身份验证**：EKS 使用 OpenID Connect (OIDC) provider，在 Kubernetes service accounts 和 IAM roles 之间建立信任关系。
3. **增强安全性**：通过为每个应用程序仅授予所需的最低权限，支持实现最小权限原则。
4. **实现方法**：
   * 为 EKS cluster 创建 OIDC provider
   * 创建信任该 service account 的 IAM role
   * 创建带有特定 annotation 的 Kubernetes service account
   * 使用该 service account 部署 pod

通过 IRSA，使用 AWS SDK 的应用程序可以使用自己的 IAM role 安全访问 AWS services，而不是依赖节点的 IAM role。

</details>

### 5. 在 EKS 集群中，管理 node group Auto Scaling 的 Kubernetes-native 工具是什么？

A. Horizontal Pod Autoscaler B. Vertical Pod Autoscaler C. Cluster Autoscaler D. Node Autoscaler

<details>

<summary>答案和解释</summary>

**答案：C. Cluster Autoscaler**

**解释：** 在 EKS 集群中，管理 node group Auto Scaling 的 Kubernetes-native 工具是 Cluster Autoscaler。该工具的主要特点是：

1. **自动扩缩容**：当 pods 因资源不足而无法调度时自动添加节点，并在节点利用率较低时移除节点。
2. **AWS Auto Scaling Group 集成**：在 EKS 中与 AWS Auto Scaling Groups 集成工作。
3. **工作方式**：
   * Scale Out：当 pods 因资源约束处于 Pending 状态时添加节点
   * Scale In：当利用率较低且 pods 可以移动到其他节点时移除节点
4. **配置选项**：
   * 设置 scale up/down 阈值
   * 指定 node group discovery 方法
   * 设置 scale down delay
   * 遵守 Pod Disruption Budgets (PDB)

Horizontal Pod Autoscaler (HPA) 会自动调整 pod 数量，Vertical Pod Autoscaler (VPA) 会自动调整 pod resource requests，而调整节点数量是 Cluster Autoscaler 的职责。

请注意，AWS 还提供 Karpenter 作为新的 node provisioning 工具，它提供更快且更灵活的节点供应能力。

</details>

## 简答题

### 6. 在 EKS 集群中，需要什么配置才能启用 Kubernetes control plane logs 并将它们发送到 CloudWatch Logs？

<details>

<summary>答案和解释</summary>

要在 EKS 集群中将 Kubernetes control plane logs 发送到 CloudWatch Logs，你需要在创建集群期间或在现有集群上启用特定日志类型。

**所需配置：**

1. **启用日志类型**：启用以下一种或多种日志类型：
   * `api`: Kubernetes API server logs
   * `audit`: Kubernetes audit logs
   * `authenticator`: AWS IAM authenticator logs
   * `controllerManager`: Controller manager logs
   * `scheduler`: Scheduler logs
2. **通过 AWS Management Console 启用**：
   * 在 EKS console 中选择集群
   * 选择 "Logging" tab
   * 启用所需的日志类型
3. **通过 AWS CLI 启用**：

```bash
aws eks update-cluster-config \
    --region region-code \
    --name cluster-name \
    --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

4. **通过 eksctl 启用**：

```bash
eksctl utils update-cluster-logging \
    --region=region-code \
    --cluster=cluster-name \
    --enable-types=api,audit,authenticator,controllerManager,scheduler
```

启用的日志会自动发送到 CloudWatch Logs log group `/aws/eks/cluster-name/cluster`。每种日志类型都会存储为单独的 log stream。

**注意事项：**

* 启用日志会产生额外费用（适用 CloudWatch Logs 定价）。
* 特别是 audit logs 可能会生成大量数据，因此需要注意成本管理。
* 设置日志保留周期以管理成本。

</details>

### 7. 如何将 worker nodes 上的 kubelet logs 发送到 EKS 集群中的 CloudWatch Logs？

<details>

<summary>答案和解释</summary>

要在 EKS 集群中将 worker nodes 上的 kubelet logs 发送到 CloudWatch Logs，你需要安装并配置 CloudWatch agent。与 control plane logs 不同，worker node logs 不会自动发送到 CloudWatch。

**实现步骤：**

1. **安装 CloudWatch Agent**：在 Kubernetes 中将 CloudWatch agent 部署为 DaemonSet。
2. **配置 Fluentd 或 Fluent Bit**：配置日志收集器，将 kubelet logs 发送到 CloudWatch Logs。
3.  **推荐方法：使用 Amazon EKS Add-on**：

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
4.  **自定义配置**：修改 ConfigMap 以收集特定的日志路径和格式。

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
5. **验证日志**：在 CloudWatch Logs console 中检查 log group `/aws/eks/my-cluster/nodes`。

**关键日志收集目标：**

* `/var/log/kubelet.log`: kubelet logs
* `/var/log/kube-proxy.log`: kube-proxy logs
* `/var/log/aws-routed-eni/ipamd.log`: VPC CNI logs
* `/var/log/containers/*.log`: container logs

**替代方法：**

* 使用 AWS Distro for OpenTelemetry (ADOT)
* 使用 Amazon OpenSearch 与 Fluent Bit 组合
* 构建自定义 logging solution（例如 ELK stack）

**最佳实践：**

* 通过日志保留周期设置管理成本
* 选择性地仅收集必要日志
* 通过日志过滤仅收集重要信息
* 通过为 log groups 添加 tags 来跟踪成本

</details>

### 8. 为什么 Pod Security Policy (PSP) 不再用于 EKS 集群，替代方案有哪些？

<details>

<summary>答案和解释</summary>

Pod Security Policy (PSP) 自 Kubernetes version 1.21 起已被弃用，并在 Kubernetes 1.25 中被完全移除。因此，EKS 不再支持 PSP。

**弃用原因：**

1. **复杂性**：PSP 难以配置和理解。
2. **调试困难**：当发生 PSP 违规时，没有提供清晰的错误消息，导致故障排查困难。
3. **灵活性有限**：在某些场景中难以实现细粒度控制。
4. **一致性不足**：与其他 Kubernetes 安全机制的集成不够顺畅。

**替代方案：**

1. **Pod Security Standards (PSS) / Pod Security Admission (PSA)**：
   * 自 Kubernetes 1.22 起引入的官方替代方案
   * 提供三个安全级别：Privileged、Baseline、Restricted
   * 通过 namespace labels 应用
   *   示例：

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
2. **Kyverno**：
   * 使用基于 YAML 的 policy definitions 的 policy engine
   * 提供比 PSP 更灵活、更强大的功能
   * 支持 validation、mutation、generation、cleanup policies
   *   示例：

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
3. **OPA Gatekeeper**：
   * 基于 Open Policy Agent 的 policy controller
   * 使用 Rego language 编写 policy definitions
   * 使用 ConstraintTemplate 和 Constraint 概念
   *   示例：

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
4. **AWS 内置安全功能**：
   * Amazon GuardDuty for EKS Protection
   * AWS Security Hub's EKS security standards
   * Amazon Inspector for EKS

**迁移策略：**

1. 分析并记录当前 PSP policies
2. 选择替代解决方案（PSA、Kyverno、OPA Gatekeeper 等）
3. 以 audit mode 部署新 policies 以评估影响
4. 逐步应用 policies（过渡到 enforce mode）
5. 通过 monitoring 和 logging 设置跟踪 policy violations

在升级到 EKS 1.25 或更高版本之前，从 PSP 迁移到替代解决方案非常重要。

</details>

## 实操题

### 9. 编写一个 node group 配置，在 EKS 集群中混合使用 Spot instances 和 On-Demand instances 以优化成本。它应满足以下要求：

* 用于关键工作负载的 On-Demand node group（2-5 个节点）
* 用于通用工作负载的 Spot node group（2-10 个节点）
* 适当的 node labels 和 taints
* 用于工作负载放置的 node affinity 和 tolerations 示例

<details>

<summary>答案和解释</summary>

在 EKS 集群中使用 Spot instances 和 On-Demand instances 混合进行成本优化的 node group 配置如下：

#### 1. On-Demand Node Group 配置（用于关键工作负载）

**使用 eksctl 的配置：**

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

**使用 AWS CLI 的配置：**

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

#### 2. Spot Node Group 配置（用于通用工作负载）

**使用 eksctl 的配置：**

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

**使用 AWS CLI 的配置：**

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

#### 3. 用于工作负载放置的 Node Affinity 和 Tolerations 示例

**关键工作负载 Deployment 示例（优先使用 On-Demand 节点）：**

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

**通用工作负载 Deployment 示例（允许 Spot 节点）：**

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

#### 4. 其他优化设置

**Cluster Autoscaler Deployment：**

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

**AWS Node Termination Handler（Spot instance 中断处理）：**

```bash
helm repo add eks https://aws.github.io/eks-charts
helm install aws-node-termination-handler \
  --namespace kube-system \
  --set enableSpotInterruptionDraining=true \
  --set enableRebalanceMonitoring=true \
  --set enableRebalanceDraining=true \
  eks/aws-node-termination-handler
```

#### 5. 最佳实践和注意事项

1. **使用多种实例类型**：在 Spot node groups 中使用多种实例类型可分散中断风险。
2.  **设置 Pod Disruption Budgets (PDB)**：为关键应用程序设置 PDB，以限制同时被中断的 pods 数量。

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
3. **设置适当的 Resource Requests 和 Limits**：设置适当的 container resource requests 和 limits，以高效利用节点资源。
4.  **使用 Horizontal Pod Autoscaler**：根据工作负载需求自动调整 pod 数量。

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
5. **成本监控和优化**：使用 AWS Cost Explorer 和 Kubecost 等工具监控并优化集群成本。

</details>

## 高级题

### 10. 说明在 EKS 集群中实现 multi-tenancy 的策略，并比较每种方法的优点和缺点。

<details>

<summary>答案和解释</summary>

在 EKS 集群中实现 multi-tenancy 意味着在多个团队、应用程序或客户共享同一 Kubernetes 基础设施时，确保适当的隔离和资源管理。以下是在 EKS 中实现 multi-tenancy 的主要策略，以及每种方法的优点和缺点。

### 1. Cluster-Level Separation（Hard Multi-tenancy）

**描述**：为每个 tenant 供应独立的 EKS clusters。

**实现方法**：

```bash
# Create cluster for Tenant A
eksctl create cluster --name tenant-a-cluster --region us-west-2

# Create cluster for Tenant B
eksctl create cluster --name tenant-b-cluster --region us-west-2
```

**优点**：

* 确保完全隔离（安全、网络、资源）
* 可为每个 tenant 自定义 cluster versions 和配置
* 一个 tenant 的问题不会影响其他 tenant
* 适用于具有严格监管要求的环境

**缺点**：

* 运维开销高（管理多个 clusters）
* 资源利用率降低（每个 cluster 都有重复的 control plane 和系统组件）
* 成本增加（每个 cluster 都有 control plane 成本）
* 集中式管理和 policy enforcement 困难

### 2. Namespace-Level Separation（Soft Multi-tenancy）

**描述**：在单个 EKS cluster 中使用 Kubernetes namespaces 分隔 tenants。

**实现方法**：

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

**优点**：

* 使用单个 cluster 简化管理
* 提高资源利用率
* 成本效率更高（共享 control plane）
* 更容易进行集中式管理和 policy enforcement

**缺点**：

* 难以确保完全隔离
* 由于共享 cluster-level resources，存在安全风险
* 一个 tenant 过度使用资源可能影响其他 tenant
* Cluster upgrades 会影响所有 tenants

### 3. Namespace-Level Separation + Additional Security Controls

**描述**：在 namespace separation 基础上应用额外的安全和资源控制机制。

**实现方法**：

1. **Network Policies**：

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

2. **Resource Quotas**：

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

3. **RBAC Permission Control**：

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

**优点**：

* 保留 namespace separation 的优点
* 增强安全性和资源隔离
* 按 tenant 进行访问控制和资源分配
* 保持成本效率

**缺点**：

* 配置和管理复杂性增加
* 仍然缺乏对 cluster-level resources 的完全隔离
* policy 设置和维护需要额外工作

### 4. Virtual Clusters

**描述**：在单个物理 EKS cluster 内创建虚拟 Kubernetes control planes，为每个 tenant 提供自己的 "cluster"。

**实现方法**：

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

**优点**：

* 结合 cluster-level 和 namespace-level separation 的优点
* 为每个 tenant 提供专用的 Kubernetes API server 和 control plane
* 提高资源利用率和成本效率
* 可为每个 tenant 自定义 cluster versions 和配置

**缺点**：

* 额外开销和复杂性
* virtual cluster 技术的成熟度和支持有限
* 对某些 Kubernetes features 的支持有限
* 调试和故障排查复杂

### 5. 利用 AWS Service Integration 的 Multi-tenancy

**描述**：使用 AWS IAM、AWS Organizations、AWS Resource Access Manager 等 AWS services 增强 EKS cluster multi-tenancy。

**实现方法**：

1. **IAM Roles for Service Accounts (IRSA)**：

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: tenant-a-sa
  namespace: tenant-a
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/tenant-a-role
```

2. **AWS Organizations and SCP (Service Control Policies)**：

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

**优点**：

* 对 AWS services 进行细粒度访问控制
* 利用组织结构和 policies 增强治理
* 在 AWS service 级别提供额外隔离层
* 与现有 AWS 安全模型集成

**缺点**：

* 对 AWS services 的依赖增加
* 配置和管理复杂性增加
* 作为 AWS-specific solution，可移植性有限
* 可能产生额外的 AWS service 成本

### Multi-tenancy 实施最佳实践

1. **分析需求**：
   * 评估 tenants 之间所需的隔离级别
   * 考虑监管和合规要求
   * 考虑运维开销和成本约束
2. **考虑混合方法**：
   * 为关键 tenants 提供专用 clusters
   * 使用 namespace-level separation 对不太关键的 tenants 分组
3. **Automation and IaC (Infrastructure as Code)**：
   * 使用 Terraform、AWS CDK 或 eksctl 自动化 cluster 和 namespace provisioning
   * 通过 GitOps workflows 管理配置
4. **Monitoring and Cost Allocation**：
   * 监控每个 tenant 的资源使用情况
   * 使用 cost allocation tags 跟踪每个 tenant 的成本
   * 使用 Kubecost 或 AWS Cost Explorer 分析成本
5. **Security Enhancement**：
   * 定期进行安全审计和漏洞扫描
   * 应用最小权限原则
   * 使用 network policies 和 service mesh

### 结论

在 EKS 中实现 multi-tenancy 的最佳策略取决于组织的具体需求、安全要求、运维能力和成本约束。许多组织会采用结合多种策略的混合方法，而不是单一方法。例如，对关键或受监管的工作负载使用专用 clusters，同时对开发和测试环境应用 namespace-level separation。

选择 multi-tenancy 策略时，应在安全性、隔离、资源利用率、运维开销和成本等因素之间取得平衡。评估所选策略能否随时间适应组织不断变化的需求也同样重要。

</details>

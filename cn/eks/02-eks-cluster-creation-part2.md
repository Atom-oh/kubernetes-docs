# 第 2 部分：使用 eksctl 创建 Cluster

## 使用 eksctl 创建 Cluster

eksctl 是创建和管理 EKS Cluster（集群）的最简单方式。eksctl 使用 CloudFormation 创建 EKS Cluster 及相关资源。

下图展示了使用 eksctl 创建 EKS Cluster 的过程：

![eksctl Cluster 创建流程](../.gitbook/assets/eksctl_cluster_creation_process.png)

### 基本 Cluster 创建

要创建最基本形式的 EKS Cluster，请运行以下命令：

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

此命令会使用以下默认设置创建一个 Cluster：

* 2 个 m5.large node（节点）
* 新的 VPC 和 subnet（子网）
* 默认 Amazon Linux 2 AMI
* 最新 Kubernetes 版本

### 使用配置文件创建 Cluster

对于更复杂的配置，你可以使用 YAML 文件定义 Cluster：

```yaml
# cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-eks-cluster
  region: us-west-2
  version: "1.26"

vpc:
  id: vpc-12345678
  subnets:
    private:
      us-west-2a:
        id: subnet-12345678
      us-west-2b:
        id: subnet-87654321
    public:
      us-west-2a:
        id: subnet-23456789
      us-west-2b:
        id: subnet-98765432

managedNodeGroups:
  - name: ng-1
    instanceType: m5.large
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    privateNetworking: true
    volumeSize: 80
    volumeType: gp3
    iam:
      withAddonPolicies:
        imageBuilder: true
        autoScaler: true
        externalDNS: true
        certManager: true
        appMesh: true
        ebs: true
        fsx: true
        efs: true
        albIngress: true
        xRay: true
        cloudWatch: true

  - name: ng-2
    instanceType: c5.xlarge
    desiredCapacity: 2
    privateNetworking: true
    spot: true

fargate:
  profiles:
    - name: fp-default
      selectors:
        - namespace: default
          labels:
            env: fargate
    - name: fp-kube-system
      selectors:
        - namespace: kube-system
          labels:
            k8s-app: kube-dns

cloudWatch:
  clusterLogging:
    enableTypes: ["api", "audit", "authenticator", "controllerManager", "scheduler"]
```

要使用此配置文件创建 Cluster，请运行以下命令：

```bash
eksctl create cluster -f cluster.yaml
```

### 创建 Managed Node Group

下图展示了 EKS Cluster 的 Managed Node Group 架构：

![EKS Managed Node Group 架构](../.gitbook/assets/eks_managed_node_group_detailed.png)

要向现有 Cluster 添加 Managed Node Group，请运行以下命令：

```bash
eksctl create nodegroup \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-nodegroup \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --ssh-access \
  --ssh-public-key my-key
```

或者你可以使用配置文件：

```yaml
# nodegroup.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2

managedNodeGroups:
  - name: my-nodegroup
    instanceType: m5.large
    desiredCapacity: 3
    minSize: 1
    maxSize: 5
    volumeSize: 80
    volumeType: gp3
    ssh:
      allow: true
      publicKeyName: my-key
```

```bash
eksctl create nodegroup -f nodegroup.yaml
```

### 创建 Fargate Profile

下图展示了 EKS Fargate Profile 架构：

![EKS Fargate Profile 架构](../.gitbook/assets/eks_fargate_profile_architecture.png)

要创建 Fargate Profile，请运行以下命令：

```bash
eksctl create fargateprofile \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-fargate-profile \
  --namespace default \
  --labels env=fargate
```

或者你可以使用配置文件：

```yaml
# fargate.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2

fargate:
  profiles:
    - name: my-fargate-profile
      selectors:
        - namespace: default
          labels:
            env: fargate
```

```bash
eksctl create fargateprofile -f fargate.yaml
```

### 更新 Cluster

你可以使用 eksctl 更新现有 Cluster：

```bash
# Upgrade cluster version
eksctl upgrade cluster --name=my-cluster --version=1.27

# Upgrade node group
eksctl upgrade nodegroup --cluster=my-cluster --name=my-nodegroup
```

### 删除 Cluster

你可以使用 eksctl 删除 Cluster：

```bash
eksctl delete cluster --name=my-cluster --region=us-west-2
```

## EKS Cluster 生命周期管理

下图展示了 EKS Cluster 的整体生命周期管理过程：

![EKS Cluster 生命周期管理](../.gitbook/assets/eks_cluster_lifecycle_management.png)

## 测验

要测试你在本章中学到的内容，请尝试 [EKS Cluster 创建 - 第 2 部分测验](../quizzes/eks/02-eks-cluster-creation-part2-quiz.md)。

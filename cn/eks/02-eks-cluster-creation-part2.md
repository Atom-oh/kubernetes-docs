# 第 2 部分：使用 eksctl 创建集群

## 使用 eksctl 创建集群

eksctl 是创建和管理 EKS 集群最简单的方式。eksctl 使用 CloudFormation 创建 EKS 集群及相关资源。

下图展示了使用 eksctl 创建 EKS 集群的过程：

![eksctl 集群创建过程图，CloudFormation 堆栈依次构建 VPC、IAM、控制平面和节点组。](../.gitbook/assets/en-eks-02-eks-cluster-creation-part2-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part2-0.html)

### 基础集群创建

要创建最基本形式的 EKS 集群，请运行以下命令：

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

此命令会使用以下默认设置创建集群：

* 2 个 m5.large 节点
* 新的 VPC 和子网
* 默认 Amazon Linux 2 AMI
* 最新 Kubernetes 版本

### 使用配置文件创建集群

对于更复杂的配置，可以使用 YAML 文件定义集群：

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

要使用此配置文件创建集群，请运行以下命令：

```bash
eksctl create cluster -f cluster.yaml
```

### 创建托管节点组

下图展示了 EKS 集群的托管节点组架构：

![架构图：控制平面管理一个节点组，该节点组的 Auto Scaling 组启动运行 Pod 的 EC2 实例。](../.gitbook/assets/en-eks-02-eks-cluster-creation-part2-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part2-1.html)

要向现有集群添加托管节点组，请运行以下命令：

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

或者，您可以使用配置文件：

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

### 创建 Fargate 配置文件

下图展示了 EKS Fargate 配置文件架构：

![架构图：与 Fargate 配置文件的命名空间和标签选择器匹配的 Pod 被放置在专用 microVM 上。](../.gitbook/assets/en-eks-02-eks-cluster-creation-part2-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part2-2.html)

要创建 Fargate 配置文件，请运行以下命令：

```bash
eksctl create fargateprofile \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-fargate-profile \
  --namespace default \
  --labels env=fargate
```

或者，您可以使用配置文件：

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

### 更新集群

您可以使用 eksctl 更新现有集群：

```bash
# Upgrade cluster version
eksctl upgrade cluster --name=my-cluster --version=1.27

# Upgrade node group
eksctl upgrade nodegroup --cluster=my-cluster --name=my-nodegroup
```

### 删除集群

您可以使用 eksctl 删除集群：

```bash
eksctl delete cluster --name=my-cluster --region=us-west-2
```

## EKS 集群生命周期管理

下图展示了 EKS 集群的整体生命周期管理过程：

![EKS 集群生命周期图，从创建和配置，经版本更新，直至删除。](../.gitbook/assets/en-eks-02-eks-cluster-creation-part2-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part2-3.html)

## 测验

要测试您在本章所学的内容，请尝试 [EKS 集群创建 - 第 2 部分测验](../quizzes/eks/02-eks-cluster-creation-part2-quiz.md)。

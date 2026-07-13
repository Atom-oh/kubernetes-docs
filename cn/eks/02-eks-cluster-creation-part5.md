# 第 5 部分：Cluster 访问、验证、升级和删除

## 配置 Cluster 访问

创建 EKS cluster 后，需要进行配置才能访问该 cluster。在本节中，我们将学习如何配置 cluster 访问。

### Cluster 访问配置流程

![EKS Cluster 访问配置流程](../.gitbook/assets/eks_cluster_access_configuration.png)

### kubeconfig 配置

你需要配置 kubeconfig 文件来访问 EKS cluster。可以使用 AWS CLI 配置 kubeconfig：

```bash
aws eks update-kubeconfig \
  --name my-cluster \
  --region us-west-2
```

此命令会更新 `~/.kube/config` 文件，以启用对 EKS cluster 的访问。

### 配置 IAM User 和 Role 访问

默认情况下，只有创建 EKS cluster 的 IAM 实体（user 或 role）可以访问该 cluster。有两种方法可以向其他 IAM users 或 roles 授予 cluster 访问权限：传统的 aws-auth ConfigMap 方法和新的 EKS Access Entry 方法。

![EKS IAM 访问方法比较](../.gitbook/assets/eks_iam_access_methods.png)

#### 方法 1：EKS Access Entry（推荐）

EKS Access Entry 是一种替代 aws-auth ConfigMap 的新方法，提供了更稳定且更易于管理的方式。

1. 为 cluster 启用 Access Entry：

```bash
aws eks update-cluster-config \
  --name my-cluster \
  --region us-west-2 \
  --access-config authenticationMode=API_AND_CONFIG_MAP
```

2. 为 IAM role 创建 Access Entry：

```bash
aws eks create-access-entry \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:role/MyRole \
  --username my-role \
  --kubernetes-groups system:masters
```

3. 为 IAM user 创建 Access Entry：

```bash
aws eks create-access-entry \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:user/my-user \
  --username my-user \
  --kubernetes-groups system:masters
```

4. 列出 Access Entries：

```bash
aws eks list-access-entries --cluster-name my-cluster
```

5. 描述 Access Entry 详细信息：

```bash
aws eks describe-access-entry \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:user/my-user
```

#### 方法 2：aws-auth ConfigMap（传统）

aws-auth ConfigMap 是传统方法，并且仍然受支持，但建议为新的 clusters 使用 Access Entry。

1. 获取当前的 `aws-auth` ConfigMap：

```bash
kubectl get configmap aws-auth -n kube-system -o yaml > aws-auth.yaml
```

2. 编辑 `aws-auth.yaml` 文件以添加 users 或 roles：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: arn:aws:iam::123456789012:role/EKSNodeRole
      username: system:node:{{EC2PrivateDNSName}}
      groups:
        - system:bootstrappers
        - system:nodes
    # Additional role
    - rolearn: arn:aws:iam::123456789012:role/MyRole
      username: my-role
      groups:
        - system:masters
  mapUsers: |
    # IAM user
    - userarn: arn:aws:iam::123456789012:user/my-user
      username: my-user
      groups:
        - system:masters
```

3. 应用更新后的 ConfigMap：

```bash
kubectl apply -f aws-auth.yaml
```

> **注意**：EKS Access Entry 于 2023 年推出，建议新的 clusters 使用 Access Entry。现有 clusters 可以迁移到同时支持两种方法的混合模式。

### RBAC 配置

你可以使用 Kubernetes Role-Based Access Control (RBAC) 控制对 cluster 内资源的访问。

1. 创建 namespace：

```bash
kubectl create namespace dev
```

2. 创建 role：

```yaml
# role.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: dev
  name: developer
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps", "secrets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "daemonsets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
```

```bash
kubectl apply -f role.yaml
```

3. 创建 role binding：

```yaml
# rolebinding.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer-binding
  namespace: dev
subjects:
- kind: User
  name: my-user
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer
  apiGroup: rbac.authorization.k8s.io
```

```bash
kubectl apply -f rolebinding.yaml
```

## Cluster 验证

创建 EKS cluster 后，你需要验证该 cluster 是否正常工作。在本节中，我们将学习如何验证 cluster。

### Cluster 验证流程

![EKS Cluster 验证流程](../.gitbook/assets/eks_cluster_validation_process.png)

### 验证 Nodes

验证 cluster 中的 nodes：

```bash
kubectl get nodes
```

验证所有 nodes 都处于 `Ready` 状态。

### 验证 System Pods

验证 kube-system namespace 中的 pods：

```bash
kubectl get pods -n kube-system
```

验证所有 system pods 都处于 `Running` 状态。

### 部署测试应用程序

部署一个简单的测试应用程序，以验证 cluster 是否正常工作：

```yaml
# nginx.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: nginx
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 80
  selector:
    app: nginx
```

```bash
kubectl apply -f nginx.yaml
```

验证 deployment 和 service 状态：

```bash
kubectl get deployments
kubectl get pods
kubectl get services
```

验证你可以使用 LoadBalancer service 的外部 IP 访问该应用程序：

```bash
curl http://<EXTERNAL-IP>
```

### 验证 Cluster Logs

在 CloudWatch Logs 中验证 cluster logs：

```bash
aws logs describe-log-groups \
  --log-group-name-prefix /aws/eks/my-cluster
```

## Cluster 升级

为了让 EKS cluster 保持最新，需要定期升级。在本节中，我们将学习如何升级 cluster。

### Cluster 升级流程

![EKS Cluster 升级流程](../.gitbook/assets/eks_cluster_upgrade_process.png)

### Control Plane 升级

要升级 EKS control plane，请按照以下步骤操作：

1. 检查可用的 Kubernetes versions：

```bash
aws eks describe-addon-versions \
  --kubernetes-version 1.27 \
  --query "addons[].addonVersions[].compatibilities[].clusterVersion"
```

2. 升级 cluster：

```bash
aws eks update-cluster-version \
  --name my-cluster \
  --kubernetes-version 1.27
```

3. 检查升级状态：

```bash
aws eks describe-update \
  --name my-cluster \
  --update-id <UPDATE-ID>
```

### Node 升级

升级 control plane 后，nodes 也必须升级：

#### Managed Node Group 升级

```bash
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup
```

#### Self-Managed Node 升级

对于 self-managed nodes，你需要创建新的 node group、迁移 workloads，然后删除旧的 node group。

### Add-on 升级

要升级 EKS add-ons，请按照以下步骤操作：

1. 检查可用的 add-on versions：

```bash
aws eks describe-addon-versions \
  --addon-name vpc-cni \
  --kubernetes-version 1.27
```

2. 升级 add-on：

```bash
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version <VERSION>
```

## Cluster 删除

当不再需要 EKS cluster 时，你可以删除它以节省成本。在本节中，我们将学习如何删除 cluster。

### Cluster 删除流程

![EKS Cluster 删除流程](../.gitbook/assets/eks_cluster_deletion_process.png)

### Resource 清理

删除 cluster 之前，必须清理 cluster 中创建的所有 resources：

1. 删除 LoadBalancer services：

```bash
kubectl get services --all-namespaces -o json | jq -r '.items[] | select(.spec.type == "LoadBalancer") | .metadata.name + " " + .metadata.namespace' | while read name namespace; do
  kubectl delete service $name -n $namespace
done
```

2. 删除 PersistentVolumeClaims：

```bash
kubectl delete pvc --all --all-namespaces
```

### 使用 eksctl 删除 Cluster

如果你使用 eksctl 创建了 cluster，可以使用以下命令删除它：

```bash
eksctl delete cluster --name my-cluster --region us-west-2
```

### 使用 AWS CLI 删除 Cluster

要使用 AWS CLI 删除 cluster，请按照以下步骤操作：

1. 删除 node group：

```bash
aws eks delete-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup
```

2. 删除 Fargate profile：

```bash
aws eks delete-fargate-profile \
  --cluster-name my-cluster \
  --fargate-profile-name my-fargate-profile
```

3. 删除 cluster：

```bash
aws eks delete-cluster \
  --name my-cluster
```

### 清理相关 Resources

删除 EKS cluster 后，以下相关 resources 可能仍会保留：

1. VPC 和相关 resources：

```bash
aws ec2 delete-vpc --vpc-id vpc-xxxxxxxxxxxxxxxxx
```

2. IAM roles 和 policies：

```bash
aws iam detach-role-policy \
  --role-name EKSClusterRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy

aws iam delete-role --role-name EKSClusterRole

aws iam detach-role-policy \
  --role-name EKSNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy

aws iam detach-role-policy \
  --role-name EKSNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy

aws iam detach-role-policy \
  --role-name EKSNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

aws iam delete-role --role-name EKSNodeRole
```

3. CloudWatch log groups：

```bash
aws logs delete-log-group \
  --log-group-name /aws/eks/my-cluster/cluster
```

## Quiz

要测试你在本章中学到的内容，请尝试 [EKS Cluster Creation - Part 5 Quiz](../quizzes/eks/02-eks-cluster-creation-part5-quiz.md)。

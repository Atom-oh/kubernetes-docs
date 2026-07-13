# EKS Cluster 创建实验指南

> **难度**: 中级
> **预计时间**: 60 分钟
> **最后更新**: February 11, 2026

## 学习目标
- 使用 eksctl 创建 EKS cluster
- 使用 kubectl 访问 cluster 并检查其状态
- 部署一个示例应用
- 安全删除 cluster

## 前提条件
- [ ] AWS account 和 AWS CLI 已配置（使用 `aws sts get-caller-identity` 验证）
- [ ] 已安装 eksctl（使用 `eksctl version` 验证）
- [ ] 已安装 kubectl
- [ ] 已完成 [EKS Cluster 创建](../../eks/02-eks-cluster-creation-part1.md) 学习内容

> **费用警告**: 运行 EKS cluster 会产生 AWS 费用。完成实验后请务必删除 cluster。

---

## 练习 1：eksctl 配置验证

### 步骤

**步骤 1.1：检查工具版本**
```bash
aws --version
eksctl version
kubectl version --client
```

**步骤 1.2：验证 AWS credentials**
```bash
aws sts get-caller-identity
```

预期输出：
```json
{
    "UserId": "AIDACKCEVSQ6C2EXAMPLE",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-user"
}
```

**步骤 1.3：设置默认 region**
```bash
export AWS_DEFAULT_REGION=ap-northeast-2
echo "Region: $AWS_DEFAULT_REGION"
```

<details>
<summary>需要提示吗？</summary>

- 使用 `aws configure list` 检查当前配置
- eksctl 在内部使用 CloudFormation
- IAM user 需要 EKS、EC2、CloudFormation 和 IAM 权限
</details>

---

## 练习 2：EKS Cluster 创建

### 步骤

**步骤 2.1：编写 cluster 配置文件**
```bash
cat > /tmp/eks-cluster.yaml << 'EOF'
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: lab-cluster
  region: ap-northeast-2
  version: "1.31"
managedNodeGroups:
  - name: workers
    instanceType: t3.medium
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    volumeSize: 20
EOF
```

**步骤 2.2：创建 cluster**
```bash
eksctl create cluster -f /tmp/eks-cluster.yaml
```

> Cluster 创建需要 15-20 分钟。

**步骤 2.3：验证 kubeconfig**
```bash
kubectl config current-context
kubectl cluster-info
```

### 验证
```bash
kubectl get nodes
# Should display 2 Ready nodes
```

---

## 练习 3：Cluster 探索

### 步骤

**步骤 3.1：检查 node 信息**
```bash
kubectl get nodes -o wide
kubectl describe node $(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')
```

**步骤 3.2：检查系统组件**
```bash
kubectl get pods -n kube-system
kubectl get svc -n kube-system
```

**步骤 3.3：检查资源使用情况**
```bash
kubectl top nodes 2>/dev/null || echo "Metrics Server is not installed"
```

---

## 练习 4：示例 App 部署

### 步骤

**步骤 4.1：部署 Nginx**
```bash
kubectl create deployment nginx --image=nginx:1.25 --replicas=2
kubectl expose deployment nginx --port=80 --type=LoadBalancer
kubectl wait --for=condition=available deployment/nginx --timeout=120s
```

**步骤 4.2：验证访问**
```bash
# Check LoadBalancer External IP (ELB creation takes a few minutes)
kubectl get svc nginx -w
# Press Ctrl+C once EXTERNAL-IP is assigned

# Test access
ELB_URL=$(kubectl get svc nginx -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "ELB URL: $ELB_URL"
curl -s "$ELB_URL" | head -5
```

**步骤 4.3：Scaling 测试**
```bash
kubectl scale deployment nginx --replicas=4
kubectl get pods -l app=nginx -o wide
```

<details>
<summary>需要提示吗？</summary>

- ELB URL 通过 DNS 传播可能需要几分钟
- 使用 `kubectl get svc -w` 实时监控 EXTERNAL-IP 分配
- 也可以在 AWS Console 的 EC2 > Load Balancers 下进行验证
</details>

### 验证
```bash
kubectl get deployment nginx -o jsonpath='{.status.readyReplicas}'
# Output: 4
```

---

## 清理

> **重要**: 请务必删除 cluster，以防止持续产生费用。

```bash
# 1. Clean up application (so LoadBalancer deletes the ELB)
kubectl delete svc nginx
kubectl delete deployment nginx

# 2. Wait for ELB deletion (about 1 minute)
sleep 60

# 3. Delete cluster
eksctl delete cluster -f /tmp/eks-cluster.yaml --wait

# 4. Clean up configuration file
rm -f /tmp/eks-cluster.yaml
```

## 故障排除

<details>
<summary>Cluster 创建失败</summary>

- 检查 IAM 权限（需要 AdministratorAccess 或 EKS 相关 policies）
- 检查 VPC/subnet 限制（每个 region 的默认 VPC 数量限制）
- 使用 `eksctl utils describe-stacks --region=ap-northeast-2 --cluster=lab-cluster` 获取详细信息
</details>

<details>
<summary>kubectl 无法连接到 cluster</summary>

手动更新 kubeconfig：
```bash
aws eks update-kubeconfig --name lab-cluster --region ap-northeast-2
```
</details>

## 后续步骤
- [EKS Cluster 创建测验](../../quizzes/eks/02-eks-cluster-creation-part1-quiz.md)
- 高级主题：[EKS Networking](../../eks/03-eks-networking-part1.md)

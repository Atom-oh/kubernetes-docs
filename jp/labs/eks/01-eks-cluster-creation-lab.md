# EKS Cluster Creation ラボガイド

> **難易度**: 中級
> **所要時間**: 60 分
> **最終更新**: February 11, 2026

## 学習目標
- eksctl を使用して EKS cluster を作成する
- kubectl で cluster にアクセスし、ステータスを確認する
- サンプルアプリケーションをデプロイする
- cluster を安全に削除する

## 前提条件
- [ ] AWS account と AWS CLI が設定済み（`aws sts get-caller-identity` で確認）
- [ ] eksctl がインストール済み（`eksctl version` で確認）
- [ ] kubectl がインストール済み
- [ ] [EKS Cluster Creation](../../eks/02-eks-cluster-creation-part1.md) の学習を完了済み

> **コストに関する警告**: EKS cluster を運用すると AWS 利用料金が発生します。ラボ完了後は必ず cluster を削除してください。

---

## 演習 1: eksctl Configuration の確認

### 手順

**Step 1.1: tool のバージョンを確認する**
```bash
aws --version
eksctl version
kubectl version --client
```

**Step 1.2: AWS credentials を確認する**
```bash
aws sts get-caller-identity
```

期待される出力:
```json
{
    "UserId": "AIDACKCEVSQ6C2EXAMPLE",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-user"
}
```

**Step 1.3: default region を設定する**
```bash
export AWS_DEFAULT_REGION=ap-northeast-2
echo "Region: $AWS_DEFAULT_REGION"
```

<details>
<summary>ヒントが必要ですか？</summary>

- 現在の configuration を確認するには `aws configure list` を使用します
- eksctl は内部的に CloudFormation を使用します
- IAM user には EKS、EC2、CloudFormation、IAM permissions が必要です
</details>

---

## 演習 2: EKS Cluster Creation

### 手順

**Step 2.1: cluster configuration file を作成する**
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

**Step 2.2: cluster を作成する**
```bash
eksctl create cluster -f /tmp/eks-cluster.yaml
```

> Cluster の作成には 15〜20 分かかります。

**Step 2.3: kubeconfig を確認する**
```bash
kubectl config current-context
kubectl cluster-info
```

### 検証
```bash
kubectl get nodes
# Should display 2 Ready nodes
```

---

## 演習 3: Cluster Exploration

### 手順

**Step 3.1: node 情報を確認する**
```bash
kubectl get nodes -o wide
kubectl describe node $(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')
```

**Step 3.2: system components を確認する**
```bash
kubectl get pods -n kube-system
kubectl get svc -n kube-system
```

**Step 3.3: resource usage を確認する**
```bash
kubectl top nodes 2>/dev/null || echo "Metrics Server is not installed"
```

---

## 演習 4: Sample App Deployment

### 手順

**Step 4.1: Nginx をデプロイする**
```bash
kubectl create deployment nginx --image=nginx:1.25 --replicas=2
kubectl expose deployment nginx --port=80 --type=LoadBalancer
kubectl wait --for=condition=available deployment/nginx --timeout=120s
```

**Step 4.2: access を確認する**
```bash
# Check LoadBalancer External IP (ELB creation takes a few minutes)
kubectl get svc nginx -w
# Press Ctrl+C once EXTERNAL-IP is assigned

# Test access
ELB_URL=$(kubectl get svc nginx -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "ELB URL: $ELB_URL"
curl -s "$ELB_URL" | head -5
```

**Step 4.3: Scaling test**
```bash
kubectl scale deployment nginx --replicas=4
kubectl get pods -l app=nginx -o wide
```

<details>
<summary>ヒントが必要ですか？</summary>

- ELB URL が DNS に伝播するまで数分かかる場合があります
- EXTERNAL-IP の割り当てをリアルタイムで監視するには `kubectl get svc -w` を使用します
- AWS Console の EC2 > Load Balancers でも確認できます
</details>

### 検証
```bash
kubectl get deployment nginx -o jsonpath='{.status.readyReplicas}'
# Output: 4
```

---

## クリーンアップ

> **重要**: 継続的なコストを防ぐため、必ず cluster を削除してください。

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

## トラブルシューティング

<details>
<summary>Cluster の作成に失敗する</summary>

- IAM permissions を確認します（AdministratorAccess または EKS 関連 policies が必要）
- VPC/subnet limits を確認します（region ごとの default VPC count limits）
- `eksctl utils describe-stacks --region=ap-northeast-2 --cluster=lab-cluster` で詳細を取得します
</details>

<details>
<summary>kubectl が cluster に接続できない</summary>

kubeconfig を手動で更新します:
```bash
aws eks update-kubeconfig --name lab-cluster --region ap-northeast-2
```
</details>

## 次のステップ
- [EKS Cluster Creation Quiz](../../quizzes/eks/02-eks-cluster-creation-part1-quiz.md)
- Advanced topics: [EKS Networking](../../eks/03-eks-networking-part1.md)

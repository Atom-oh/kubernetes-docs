# Pods and Workloads ラボガイド

> **難易度**: 初級
> **所要時間**: 50 分
> **最終更新**: February 11, 2026

## 学習目標
- YAML を使用して Pod を作成および管理する
- Deployment をデプロイおよびスケールする
- Rolling Update と Rollback を実行する

## 前提条件
- [ ] kubectl がインストール済みで、cluster へのアクセス権があること（minikube または kind）
- [ ] [Pods and Workloads](../../core/02-pods-and-workloads.md) の学習を完了済み

---

## 演習 1: Pod の作成と管理

### 手順

**Step 1.1: Pod YAML を作成する**
```bash
cat > /tmp/nginx-pod.yaml << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: nginx-lab
  labels:
    app: nginx
    env: lab
spec:
  containers:
  - name: nginx
    image: nginx:1.25
    ports:
    - containerPort: 80
    resources:
      requests:
        memory: "64Mi"
        cpu: "100m"
      limits:
        memory: "128Mi"
        cpu: "200m"
EOF

kubectl apply -f /tmp/nginx-pod.yaml
```

**Step 1.2: Pod のステータスを確認する**
```bash
kubectl get pod nginx-lab -o wide
kubectl describe pod nginx-lab
kubectl logs nginx-lab
```

**Step 1.3: Pod の内部にアクセスする**
```bash
kubectl exec -it nginx-lab -- bash
# Run inside:
curl localhost
exit
```

### 検証
```bash
kubectl get pod nginx-lab -o jsonpath='{.status.phase}'
# Output: Running
```

---

## 演習 2: Deployment

### 手順

**Step 2.1: Deployment を作成する**
```bash
cat > /tmp/nginx-deployment.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deploy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx-deploy
  template:
    metadata:
      labels:
        app: nginx-deploy
    spec:
      containers:
      - name: nginx
        image: nginx:1.24
        ports:
        - containerPort: 80
EOF

kubectl apply -f /tmp/nginx-deployment.yaml
```

**Step 2.2: deployment のステータスを確認する**
```bash
kubectl get deployment nginx-deploy
kubectl get replicaset
kubectl get pods -l app=nginx-deploy
```

**Step 2.3: Scaling**
```bash
kubectl scale deployment nginx-deploy --replicas=5
kubectl get pods -l app=nginx-deploy -w
# Press Ctrl+C to stop watching
```

<details>
<summary>ヒントが必要ですか？</summary>

- `kubectl get pods -w` は変更をリアルタイムで監視します
- ReplicaSet は Deployment によって自動的に管理されます
- label ベースのフィルタリングには `-l` オプションを使用します
</details>

### 検証
```bash
READY=$(kubectl get deployment nginx-deploy -o jsonpath='{.status.readyReplicas}')
echo "Ready replicas: $READY"
```

---

## 演習 3: Rolling Update

### 手順

**Step 3.1: image を更新する**
```bash
kubectl set image deployment/nginx-deploy nginx=nginx:1.25 --record
kubectl rollout status deployment/nginx-deploy
```

**Step 3.2: 更新履歴を確認する**
```bash
kubectl rollout history deployment/nginx-deploy
kubectl get replicaset -o wide
```

### 検証
```bash
kubectl get deployment nginx-deploy -o jsonpath='{.spec.template.spec.containers[0].image}'
# Output: nginx:1.25
```

---

## 演習 4: Rollback

### 手順

**Step 4.1: 無効な image で更新する（意図的なエラー）**
```bash
kubectl set image deployment/nginx-deploy nginx=nginx:invalid-tag --record
kubectl rollout status deployment/nginx-deploy --timeout=30s
```

**Step 4.2: エラーを確認して Rollback する**
```bash
kubectl get pods -l app=nginx-deploy
kubectl rollback deployment/nginx-deploy 2>/dev/null || kubectl rollout undo deployment/nginx-deploy
kubectl rollout status deployment/nginx-deploy
```

### 検証
```bash
IMAGE=$(kubectl get deployment nginx-deploy -o jsonpath='{.spec.template.spec.containers[0].image}')
echo "Current image: $IMAGE"
[ "$IMAGE" = "nginx:1.25" ] && echo "Rollback successful!" || echo "Please verify the image"
```

---

## クリーンアップ
```bash
kubectl delete pod nginx-lab
kubectl delete deployment nginx-deploy
rm -f /tmp/nginx-pod.yaml /tmp/nginx-deployment.yaml
```

## 次のステップ
- [Pods and Workloads クイズ](../../quizzes/core/02-pods-and-workloads-quiz.md)
- [Services and Networking ラボ](./03-services-networking-lab.md)

# Pods 和 Workloads 实验指南

> **难度**: 初级
> **预计时间**: 50 分钟
> **最后更新**: February 11, 2026

## 学习目标
- 使用 YAML 创建和管理 Pods
- 部署和扩缩 Deployments
- 执行滚动更新和回滚

## 前提条件
- [ ] 已安装 kubectl 并具有集群访问权限（minikube 或 kind）
- [ ] 已完成 [Pods 和 Workloads](../../core/02-pods-and-workloads.md) 学习

---

## 练习 1：Pod 创建与管理

### 步骤

**步骤 1.1：编写 Pod YAML**
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

**步骤 1.2：检查 Pod 状态**
```bash
kubectl get pod nginx-lab -o wide
kubectl describe pod nginx-lab
kubectl logs nginx-lab
```

**步骤 1.3：访问 Pod 内部**
```bash
kubectl exec -it nginx-lab -- bash
# Run inside:
curl localhost
exit
```

### 验证
```bash
kubectl get pod nginx-lab -o jsonpath='{.status.phase}'
# Output: Running
```

---

## 练习 2：Deployment

### 步骤

**步骤 2.1：创建 Deployment**
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

**步骤 2.2：检查 Deployment 状态**
```bash
kubectl get deployment nginx-deploy
kubectl get replicaset
kubectl get pods -l app=nginx-deploy
```

**步骤 2.3：扩缩容**
```bash
kubectl scale deployment nginx-deploy --replicas=5
kubectl get pods -l app=nginx-deploy -w
# Press Ctrl+C to stop watching
```

<details>
<summary>需要提示吗？</summary>

- `kubectl get pods -w` 会实时监控变化
- ReplicaSet 由 Deployment 自动管理
- 使用 `-l` 选项按标签过滤
</details>

### 验证
```bash
READY=$(kubectl get deployment nginx-deploy -o jsonpath='{.status.readyReplicas}')
echo "Ready replicas: $READY"
```

---

## 练习 3：滚动更新

### 步骤

**步骤 3.1：更新镜像**
```bash
kubectl set image deployment/nginx-deploy nginx=nginx:1.25 --record
kubectl rollout status deployment/nginx-deploy
```

**步骤 3.2：检查更新历史**
```bash
kubectl rollout history deployment/nginx-deploy
kubectl get replicaset -o wide
```

### 验证
```bash
kubectl get deployment nginx-deploy -o jsonpath='{.spec.template.spec.containers[0].image}'
# Output: nginx:1.25
```

---

## 练习 4：回滚

### 步骤

**步骤 4.1：使用无效镜像更新（有意错误）**
```bash
kubectl set image deployment/nginx-deploy nginx=nginx:invalid-tag --record
kubectl rollout status deployment/nginx-deploy --timeout=30s
```

**步骤 4.2：检查错误并回滚**
```bash
kubectl get pods -l app=nginx-deploy
kubectl rollback deployment/nginx-deploy 2>/dev/null || kubectl rollout undo deployment/nginx-deploy
kubectl rollout status deployment/nginx-deploy
```

### 验证
```bash
IMAGE=$(kubectl get deployment nginx-deploy -o jsonpath='{.spec.template.spec.containers[0].image}')
echo "Current image: $IMAGE"
[ "$IMAGE" = "nginx:1.25" ] && echo "Rollback successful!" || echo "Please verify the image"
```

---

## 清理
```bash
kubectl delete pod nginx-lab
kubectl delete deployment nginx-deploy
rm -f /tmp/nginx-pod.yaml /tmp/nginx-deployment.yaml
```

## 后续步骤
- [Pods 和 Workloads 测验](../../quizzes/core/02-pods-and-workloads-quiz.md)
- [Services 和 Networking 实验](./03-services-networking-lab.md)

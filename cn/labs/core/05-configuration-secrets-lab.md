# ConfigMap 和 Secret 实验指南

> **难度**: 初级
> **预计时间**: 35 分钟
> **最后更新**: February 11, 2026

## 学习目标
- 创建 ConfigMaps 并在 Pods 中使用它们
- 创建 Secrets 并安全地注入它们
- 比较环境变量和 Volume 挂载方法

## 前置条件
- [ ] kubectl、Kubernetes cluster
- [ ] 已完成 [Configuration](../../core/05-configuration-secrets.md) 学习

---

## 练习 1：ConfigMap 创建和使用

### 步骤

**步骤 1.1：创建 ConfigMap**
```bash
# Create from literal values
kubectl create configmap app-config \
  --from-literal=APP_ENV=production \
  --from-literal=LOG_LEVEL=info \
  --from-literal=MAX_CONNECTIONS=100

kubectl get configmap app-config -o yaml
```

**步骤 1.2：从文件创建 ConfigMap**
```bash
cat > /tmp/app.properties << 'EOF'
database.host=mysql.default.svc.cluster.local
database.port=3306
database.name=myapp
EOF

kubectl create configmap app-properties --from-file=/tmp/app.properties
kubectl describe configmap app-properties
```

**步骤 1.3：将 ConfigMap 作为环境变量注入**
```bash
cat > /tmp/configmap-env-pod.yaml << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: config-env-demo
spec:
  containers:
  - name: app
    image: busybox
    command: ["sh", "-c", "echo APP_ENV=$APP_ENV LOG_LEVEL=$LOG_LEVEL; sleep 3600"]
    envFrom:
    - configMapRef:
        name: app-config
EOF

kubectl apply -f /tmp/configmap-env-pod.yaml
kubectl wait --for=condition=ready pod/config-env-demo --timeout=30s
kubectl logs config-env-demo
```

预期输出：
```
APP_ENV=production LOG_LEVEL=info
```

**步骤 1.4：将 ConfigMap 作为 Volume 挂载**
```bash
cat > /tmp/configmap-vol-pod.yaml << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: config-vol-demo
spec:
  containers:
  - name: app
    image: busybox
    command: ["sh", "-c", "cat /config/app.properties; sleep 3600"]
    volumeMounts:
    - name: config-volume
      mountPath: /config
  volumes:
  - name: config-volume
    configMap:
      name: app-properties
EOF

kubectl apply -f /tmp/configmap-vol-pod.yaml
kubectl wait --for=condition=ready pod/config-vol-demo --timeout=30s
kubectl logs config-vol-demo
```

<details>
<summary>需要提示吗？</summary>

- `envFrom` 将 ConfigMap 中的所有键作为环境变量注入
- 作为 Volume 挂载时，每个键都会成为一个文件名
- 通过 Volume 挂载的 ConfigMaps 会自动更新（环境变量需要重启 Pod）
</details>

---

## 练习 2：Secret 管理

### 步骤

**步骤 2.1：创建 Secret**
```bash
kubectl create secret generic db-secret \
  --from-literal=DB_USER=admin \
  --from-literal=DB_PASSWORD=s3cr3tP@ss

kubectl get secret db-secret -o yaml
```

**步骤 2.2：将 Secret 注入 Pod**
```bash
cat > /tmp/secret-pod.yaml << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: secret-demo
spec:
  containers:
  - name: app
    image: busybox
    command: ["sh", "-c", "echo User=$DB_USER; echo PassLength=${#DB_PASSWORD}; sleep 3600"]
    env:
    - name: DB_USER
      valueFrom:
        secretKeyRef:
          name: db-secret
          key: DB_USER
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: db-secret
          key: DB_PASSWORD
EOF

kubectl apply -f /tmp/secret-pod.yaml
kubectl wait --for=condition=ready pod/secret-demo --timeout=30s
kubectl logs secret-demo
```

预期输出：
```
User=admin
PassLength=10
```

**步骤 2.3：解码 Secret**
```bash
# Check base64 encoded value
kubectl get secret db-secret -o jsonpath='{.data.DB_PASSWORD}' | base64 -d
echo ""
```

<details>
<summary>需要提示吗？</summary>

- Secret 值以 base64 编码形式存储（这不是加密！）
- 在生产环境中，使用 Sealed Secrets、External Secrets、AWS Secrets Manager 等
- 在 `kubectl get secret -o yaml` 中，`.data` 字段中的值是 base64 编码的
</details>

---

## 练习 3：环境变量与 Volume 挂载比较

### 步骤

**步骤 3.1：检查每种方法的特征**
```bash
echo "=== Environment Variable Method ==="
kubectl exec config-env-demo -- env | grep -E "APP_ENV|LOG_LEVEL|MAX_CONNECTIONS"

echo ""
echo "=== Volume Mount Method ==="
kubectl exec config-vol-demo -- ls /config/
kubectl exec config-vol-demo -- cat /config/app.properties
```

---

## 清理
```bash
kubectl delete pod config-env-demo config-vol-demo secret-demo
kubectl delete configmap app-config app-properties
kubectl delete secret db-secret
rm -f /tmp/app.properties /tmp/configmap-env-pod.yaml /tmp/configmap-vol-pod.yaml /tmp/secret-pod.yaml
```

## 后续步骤
- [Configuration Quiz](../../quizzes/core/05-configuration-secrets-quiz.md)
- [EKS Cluster Creation Lab](../eks/01-eks-cluster-creation-lab.md)

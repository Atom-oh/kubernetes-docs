# ConfigMap と Secret ラボガイド

> **難易度**: 初級
> **所要時間**: 35 分
> **最終更新**: February 11, 2026

## 学習目標
- ConfigMap を作成し、Pod で使用する
- Secret を作成し、安全に注入する
- 環境変数と volume mount の方法を比較する

## 前提条件
- [ ] kubectl、Kubernetes cluster
- [ ] [Configuration](../../core/05-configuration-secrets.md) の学習を完了済み

---

## 演習 1: ConfigMap の作成と使用

### 手順

**ステップ 1.1: ConfigMap を作成する**
```bash
# Create from literal values
kubectl create configmap app-config \
  --from-literal=APP_ENV=production \
  --from-literal=LOG_LEVEL=info \
  --from-literal=MAX_CONNECTIONS=100

kubectl get configmap app-config -o yaml
```

**ステップ 1.2: ファイルから ConfigMap を作成する**
```bash
cat > /tmp/app.properties << 'EOF'
database.host=mysql.default.svc.cluster.local
database.port=3306
database.name=myapp
EOF

kubectl create configmap app-properties --from-file=/tmp/app.properties
kubectl describe configmap app-properties
```

**ステップ 1.3: ConfigMap を環境変数として注入する**
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

想定される出力:
```
APP_ENV=production LOG_LEVEL=info
```

**ステップ 1.4: ConfigMap を volume として mount する**
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
<summary>ヒントが必要ですか？</summary>

- `envFrom` は ConfigMap のすべての key を環境変数として注入します
- volume として mount すると、各 key はファイル名になります
- volume-mounted ConfigMap は自動的に更新されます（環境変数には Pod の再起動が必要です）
</details>

---

## 演習 2: Secret 管理

### 手順

**ステップ 2.1: Secret を作成する**
```bash
kubectl create secret generic db-secret \
  --from-literal=DB_USER=admin \
  --from-literal=DB_PASSWORD=s3cr3tP@ss

kubectl get secret db-secret -o yaml
```

**ステップ 2.2: Secret を Pod に注入する**
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

想定される出力:
```
User=admin
PassLength=10
```

**ステップ 2.3: Secret をデコードする**
```bash
# Check base64 encoded value
kubectl get secret db-secret -o jsonpath='{.data.DB_PASSWORD}' | base64 -d
echo ""
```

<details>
<summary>ヒントが必要ですか？</summary>

- Secret の値は base64 encoded で保存されます（これは暗号化ではありません！）
- production では、Sealed Secrets、External Secrets、AWS Secrets Manager などを使用してください
- `kubectl get secret -o yaml` では、`.data` field の値は base64 encoded です
</details>

---

## 演習 3: 環境変数と Volume Mount の比較

### 手順

**ステップ 3.1: 各方法の特性を確認する**
```bash
echo "=== Environment Variable Method ==="
kubectl exec config-env-demo -- env | grep -E "APP_ENV|LOG_LEVEL|MAX_CONNECTIONS"

echo ""
echo "=== Volume Mount Method ==="
kubectl exec config-vol-demo -- ls /config/
kubectl exec config-vol-demo -- cat /config/app.properties
```

---

## クリーンアップ
```bash
kubectl delete pod config-env-demo config-vol-demo secret-demo
kubectl delete configmap app-config app-properties
kubectl delete secret db-secret
rm -f /tmp/app.properties /tmp/configmap-env-pod.yaml /tmp/configmap-vol-pod.yaml /tmp/secret-pod.yaml
```

## 次のステップ
- [Configuration Quiz](../../quizzes/core/05-configuration-secrets-quiz.md)
- [EKS Cluster Creation Lab](../eks/01-eks-cluster-creation-lab.md)

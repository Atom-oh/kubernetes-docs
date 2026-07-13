# Services and Networking ラボガイド

> **難易度**: 中級
> **所要時間**: 45 分
> **最終更新**: February 11, 2026

## 学習目標
- ClusterIP および NodePort Service を作成する
- Service 経由で Pod にアクセスする練習をする
- DNS ベースの Service Discovery を検証する

## 前提条件
- [ ] kubectl、Kubernetes cluster（minikube/kind）
- [ ] [Services and Networking](../../core/03-services-networking.md) の学習を完了済み

---

## 演習 1: ClusterIP Service

### 手順

**Step 1.1: backend Deployment を作成する**
```bash
kubectl create deployment web --image=nginx:1.25 --replicas=3
kubectl wait --for=condition=available deployment/web --timeout=60s
```

**Step 1.2: ClusterIP Service を作成する**
```bash
cat > /tmp/clusterip-svc.yaml << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: web-clusterip
spec:
  type: ClusterIP
  selector:
    app: web
  ports:
  - port: 80
    targetPort: 80
EOF

kubectl apply -f /tmp/clusterip-svc.yaml
kubectl get svc web-clusterip
```

**Step 1.3: cluster 内部からのアクセスをテストする**
```bash
# Access the Service from a temporary Pod
kubectl run curl-test --image=curlimages/curl --rm -it --restart=Never -- \
  curl -s http://web-clusterip.default.svc.cluster.local
```

<details>
<summary>ヒントが必要ですか？</summary>

- ClusterIP は cluster 内部からのみアクセスできます
- Service DNS 形式: `<service-name>.<namespace>.svc.cluster.local`
- 同じ namespace 内では、`<service-name>` だけでアクセスできます
</details>

### 検証
```bash
kubectl get endpoints web-clusterip
# Should display 3 Pod IPs
```

---

## 演習 2: NodePort Service

### 手順

**Step 2.1: NodePort Service を作成する**
```bash
cat > /tmp/nodeport-svc.yaml << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: web-nodeport
spec:
  type: NodePort
  selector:
    app: web
  ports:
  - port: 80
    targetPort: 80
    nodePort: 30080
EOF

kubectl apply -f /tmp/nodeport-svc.yaml
kubectl get svc web-nodeport
```

**Step 2.2: 外部からアクセスする**
```bash
# For minikube
minikube service web-nodeport --url 2>/dev/null || echo "NodePort: 30080"

# Get node IP
kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}'
```

### 検証
```bash
kubectl get svc web-nodeport -o jsonpath='{.spec.type}'
# Output: NodePort
```

---

## 演習 3: DNS Service Discovery

### 手順

**Step 3.1: DNS lookup テスト**
```bash
kubectl run dns-test --image=busybox:1.36 --rm -it --restart=Never -- nslookup web-clusterip
```

期待される出力:
```
Server:    10.96.0.10
Address:   10.96.0.10:53
Name:      web-clusterip.default.svc.cluster.local
Address:   10.96.x.x
```

**Step 3.2: 別の namespace からアクセスする**
```bash
kubectl create namespace test-ns
kubectl run cross-ns-test -n test-ns --image=curlimages/curl --rm -it --restart=Never -- \
  curl -s http://web-clusterip.default.svc.cluster.local
kubectl delete namespace test-ns
```

<details>
<summary>ヒントが必要ですか？</summary>

- 別の namespace からアクセスする場合は、FQDN を使用する必要があります
- CoreDNS が cluster DNS を管理します
- DNS Pod は `kubectl get pods -n kube-system -l k8s-app=kube-dns` で確認します
</details>

---

## クリーンアップ
```bash
kubectl delete deployment web
kubectl delete svc web-clusterip web-nodeport
rm -f /tmp/clusterip-svc.yaml /tmp/nodeport-svc.yaml
```

## 次のステップ
- [Services and Networking クイズ](../../quizzes/core/03-services-networking-quiz.md)
- [Storage ラボ](./04-storage-lab.md)

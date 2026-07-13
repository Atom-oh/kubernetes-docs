# Services 和 Networking 实验指南

> **难度**: 中级
> **预计时间**: 45 分钟
> **最后更新**: February 11, 2026

## 学习目标
- 创建 ClusterIP 和 NodePort Services
- 练习通过 Services 访问 Pods
- 验证基于 DNS 的 service discovery

## 前提条件
- [ ] kubectl, Kubernetes cluster (minikube/kind)
- [ ] 已完成 [Services and Networking](../../core/03-services-networking.md) 学习

---

## 练习 1: ClusterIP Service

### 步骤

**步骤 1.1: 创建后端 Deployment**
```bash
kubectl create deployment web --image=nginx:1.25 --replicas=3
kubectl wait --for=condition=available deployment/web --timeout=60s
```

**步骤 1.2: 创建 ClusterIP Service**
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

**步骤 1.3: 从 cluster 内部测试访问**
```bash
# Access the Service from a temporary Pod
kubectl run curl-test --image=curlimages/curl --rm -it --restart=Never -- \
  curl -s http://web-clusterip.default.svc.cluster.local
```

<details>
<summary>需要提示吗？</summary>

- ClusterIP 只能从 cluster 内部访问
- Service DNS 格式：`<service-name>.<namespace>.svc.cluster.local`
- 在同一 namespace 内，可以只使用 `<service-name>` 访问
</details>

### 验证
```bash
kubectl get endpoints web-clusterip
# Should display 3 Pod IPs
```

---

## 练习 2: NodePort Service

### 步骤

**步骤 2.1: 创建 NodePort Service**
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

**步骤 2.2: 从外部访问**
```bash
# For minikube
minikube service web-nodeport --url 2>/dev/null || echo "NodePort: 30080"

# Get node IP
kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}'
```

### 验证
```bash
kubectl get svc web-nodeport -o jsonpath='{.spec.type}'
# Output: NodePort
```

---

## 练习 3: DNS Service Discovery

### 步骤

**步骤 3.1: DNS 查找测试**
```bash
kubectl run dns-test --image=busybox:1.36 --rm -it --restart=Never -- nslookup web-clusterip
```

预期输出：
```
Server:    10.96.0.10
Address:   10.96.0.10:53
Name:      web-clusterip.default.svc.cluster.local
Address:   10.96.x.x
```

**步骤 3.2: 从不同 namespace 访问**
```bash
kubectl create namespace test-ns
kubectl run cross-ns-test -n test-ns --image=curlimages/curl --rm -it --restart=Never -- \
  curl -s http://web-clusterip.default.svc.cluster.local
kubectl delete namespace test-ns
```

<details>
<summary>需要提示吗？</summary>

- 从不同 namespace 访问时，必须使用 FQDN
- CoreDNS 管理 cluster DNS
- 使用 `kubectl get pods -n kube-system -l k8s-app=kube-dns` 检查 DNS Pods
</details>

---

## 清理
```bash
kubectl delete deployment web
kubectl delete svc web-clusterip web-nodeport
rm -f /tmp/clusterip-svc.yaml /tmp/nodeport-svc.yaml
```

## 后续步骤
- [Services and Networking Quiz](../../quizzes/core/03-services-networking-quiz.md)
- [Storage Lab](./04-storage-lab.md)

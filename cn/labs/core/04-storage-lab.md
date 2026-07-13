# Storage Lab 指南

> **难度**: 中级
> **预计时间**: 40 分钟
> **最后更新**: February 11, 2026

## 学习目标
- 创建 PersistentVolume (PV) 和 PersistentVolumeClaim (PVC)
- 在 Pod 中挂载并使用 Volume（卷）
- 比较 emptyDir 和 hostPath Volume 类型

## 前提条件
- [ ] kubectl、Kubernetes cluster
- [ ] 已完成 [Storage](../../core/04-storage.md) 学习

---

## 练习 1：emptyDir Volume

### 步骤

**步骤 1.1：创建使用 emptyDir 的 Pod**
```bash
cat > /tmp/emptydir-pod.yaml << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: emptydir-demo
spec:
  containers:
  - name: writer
    image: busybox
    command: ["sh", "-c", "while true; do echo $(date) >> /data/log.txt; sleep 5; done"]
    volumeMounts:
    - name: shared-data
      mountPath: /data
  - name: reader
    image: busybox
    command: ["sh", "-c", "tail -f /data/log.txt"]
    volumeMounts:
    - name: shared-data
      mountPath: /data
  volumes:
  - name: shared-data
    emptyDir: {}
EOF

kubectl apply -f /tmp/emptydir-pod.yaml
kubectl wait --for=condition=ready pod/emptydir-demo --timeout=30s
```

**步骤 1.2：验证容器之间的数据共享**
```bash
# Check reader container logs
kubectl logs emptydir-demo -c reader --tail=5

# Check file in writer container
kubectl exec emptydir-demo -c writer -- cat /data/log.txt
```

<details>
<summary>需要提示吗？</summary>

- `emptyDir` 在 Pod 被分配到 node 时创建，并在 Pod 被删除时删除
- 用于在同一个 Pod 中的容器之间共享数据
- 经常用于 K8s sidecar 模式
</details>

### 验证
```bash
kubectl exec emptydir-demo -c writer -- wc -l /data/log.txt
```

---

## 练习 2：PV/PVC 创建

### 步骤

**步骤 2.1：创建 PersistentVolume**
```bash
cat > /tmp/pv.yaml << 'EOF'
apiVersion: v1
kind: PersistentVolume
metadata:
  name: lab-pv
spec:
  capacity:
    storage: 1Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  hostPath:
    path: /tmp/k8s-lab-pv
EOF

kubectl apply -f /tmp/pv.yaml
kubectl get pv lab-pv
```

**步骤 2.2：创建 PersistentVolumeClaim**
```bash
cat > /tmp/pvc.yaml << 'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: lab-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 500Mi
EOF

kubectl apply -f /tmp/pvc.yaml
kubectl get pvc lab-pvc
kubectl get pv lab-pv
```

预期输出：
```
NAME      STATUS   VOLUME   CAPACITY   ACCESS MODES
lab-pvc   Bound    lab-pv   1Gi        RWO
```

**步骤 2.3：创建使用 PVC 的 Pod**
```bash
cat > /tmp/pvc-pod.yaml << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: pvc-demo
spec:
  containers:
  - name: app
    image: nginx:1.25
    volumeMounts:
    - name: persistent-storage
      mountPath: /usr/share/nginx/html
  volumes:
  - name: persistent-storage
    persistentVolumeClaim:
      claimName: lab-pvc
EOF

kubectl apply -f /tmp/pvc-pod.yaml
kubectl wait --for=condition=ready pod/pvc-demo --timeout=30s
```

**步骤 2.4：测试数据持久性**
```bash
# Write data
kubectl exec pvc-demo -- sh -c 'echo "Persistent Data" > /usr/share/nginx/html/index.html'

# Delete and recreate Pod
kubectl delete pod pvc-demo
kubectl apply -f /tmp/pvc-pod.yaml
kubectl wait --for=condition=ready pod/pvc-demo --timeout=30s

# Verify data
kubectl exec pvc-demo -- cat /usr/share/nginx/html/index.html
```

<details>
<summary>需要提示吗？</summary>

- PV 是 cluster 级资源，PVC 是 namespace 级资源
- `Bound` 状态表示 PVC 已绑定到 PV
- `persistentVolumeReclaimPolicy: Retain` 即使在 PVC 删除后也会保留数据
</details>

### 验证
```bash
kubectl exec pvc-demo -- cat /usr/share/nginx/html/index.html
# Output: Persistent Data (persists even after Pod recreation)
```

---

## 练习 3：Volume 类型比较

### 步骤

**步骤 3.1：比较 Volume 信息**
```bash
echo "=== emptyDir Pod ==="
kubectl get pod emptydir-demo -o jsonpath='{.spec.volumes[*].name}: {.spec.volumes[*].emptyDir}'
echo ""
echo "=== PVC Pod ==="
kubectl get pod pvc-demo -o jsonpath='{.spec.volumes[*].name}: {.spec.volumes[*].persistentVolumeClaim.claimName}'
echo ""
echo "=== PV Details ==="
kubectl get pv lab-pv -o custom-columns='NAME:.metadata.name,CAPACITY:.spec.capacity.storage,ACCESS:.spec.accessModes[0],STATUS:.status.phase'
```

---

## 清理
```bash
kubectl delete pod emptydir-demo pvc-demo
kubectl delete pvc lab-pvc
kubectl delete pv lab-pv
rm -f /tmp/emptydir-pod.yaml /tmp/pv.yaml /tmp/pvc.yaml /tmp/pvc-pod.yaml
```

## 下一步
- [Storage 测验](../../quizzes/core/04-storage-quiz.md)
- [ConfigMap 和 Secret Lab](./05-configuration-secrets-lab.md)

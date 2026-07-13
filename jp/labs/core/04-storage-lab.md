# Storage ラボガイド

> **難易度**: 中級
> **所要時間**: 40分
> **最終更新**: February 11, 2026

## 学習目標
- PersistentVolume (PV) と PersistentVolumeClaim (PVC) を作成する
- Pod で volume を mount して使用する
- emptyDir と hostPath の volume タイプを比較する

## 前提条件
- [ ] kubectl、Kubernetes cluster
- [ ] [Storage](../../core/04-storage.md) の学習を完了していること

---

## 演習 1: emptyDir Volume

### 手順

**ステップ 1.1: emptyDir を使用する Pod を作成する**
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

**ステップ 1.2: container 間のデータ共有を確認する**
```bash
# Check reader container logs
kubectl logs emptydir-demo -c reader --tail=5

# Check file in writer container
kubectl exec emptydir-demo -c writer -- cat /data/log.txt
```

<details>
<summary>ヒントが必要ですか？</summary>

- `emptyDir` は Pod が node に割り当てられたときに作成され、Pod が削除されると削除されます
- 同じ Pod 内の container 間でデータを共有するために使用されます
- K8s の sidecar pattern でよく使用されます
</details>

### 検証
```bash
kubectl exec emptydir-demo -c writer -- wc -l /data/log.txt
```

---

## 演習 2: PV/PVC の作成

### 手順

**ステップ 2.1: PersistentVolume を作成する**
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

**ステップ 2.2: PersistentVolumeClaim を作成する**
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

期待される出力:
```
NAME      STATUS   VOLUME   CAPACITY   ACCESS MODES
lab-pvc   Bound    lab-pv   1Gi        RWO
```

**ステップ 2.3: PVC を使用する Pod を作成する**
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

**ステップ 2.4: データの永続性をテストする**
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
<summary>ヒントが必要ですか？</summary>

- PV は cluster-level resource、PVC は namespace-level resource です
- `Bound` status は PVC が PV に bound されていることを意味します
- `persistentVolumeReclaimPolicy: Retain` は、PVC の削除後もデータを保持します
</details>

### 検証
```bash
kubectl exec pvc-demo -- cat /usr/share/nginx/html/index.html
# Output: Persistent Data (persists even after Pod recreation)
```

---

## 演習 3: Volume タイプの比較

### 手順

**ステップ 3.1: volume 情報を比較する**
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

## クリーンアップ
```bash
kubectl delete pod emptydir-demo pvc-demo
kubectl delete pvc lab-pvc
kubectl delete pv lab-pv
rm -f /tmp/emptydir-pod.yaml /tmp/pv.yaml /tmp/pvc.yaml /tmp/pvc-pod.yaml
```

## 次のステップ
- [Storage Quiz](../../quizzes/core/04-storage-quiz.md)
- [ConfigMap and Secret Lab](./05-configuration-secrets-lab.md)

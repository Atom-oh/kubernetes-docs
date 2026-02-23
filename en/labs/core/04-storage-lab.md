# Storage Lab Guide

> **Difficulty**: Intermediate
> **Estimated Time**: 40 minutes
> **Last Updated**: February 11, 2026

## Learning Objectives
- Create PersistentVolume (PV) and PersistentVolumeClaim (PVC)
- Mount and use volumes in Pods
- Compare emptyDir and hostPath volume types

## Prerequisites
- [ ] kubectl, Kubernetes cluster
- [ ] Completed [Storage](../../core/04-storage.md) learning

---

## Exercise 1: emptyDir Volume

### Steps

**Step 1.1: Create a Pod using emptyDir**
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

**Step 1.2: Verify data sharing between containers**
```bash
# Check reader container logs
kubectl logs emptydir-demo -c reader --tail=5

# Check file in writer container
kubectl exec emptydir-demo -c writer -- cat /data/log.txt
```

<details>
<summary>Need a hint?</summary>

- `emptyDir` is created when a Pod is assigned to a node and deleted when the Pod is deleted
- Used for sharing data between containers in the same Pod
- Frequently used in K8s sidecar patterns
</details>

### Verification
```bash
kubectl exec emptydir-demo -c writer -- wc -l /data/log.txt
```

---

## Exercise 2: PV/PVC Creation

### Steps

**Step 2.1: Create PersistentVolume**
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

**Step 2.2: Create PersistentVolumeClaim**
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

Expected output:
```
NAME      STATUS   VOLUME   CAPACITY   ACCESS MODES
lab-pvc   Bound    lab-pv   1Gi        RWO
```

**Step 2.3: Create a Pod using PVC**
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

**Step 2.4: Test data persistence**
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
<summary>Need a hint?</summary>

- PV is a cluster-level resource, PVC is a namespace-level resource
- `Bound` status means PVC is bound to a PV
- `persistentVolumeReclaimPolicy: Retain` preserves data even after PVC deletion
</details>

### Verification
```bash
kubectl exec pvc-demo -- cat /usr/share/nginx/html/index.html
# Output: Persistent Data (persists even after Pod recreation)
```

---

## Exercise 3: Volume Type Comparison

### Steps

**Step 3.1: Compare volume information**
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

## Cleanup
```bash
kubectl delete pod emptydir-demo pvc-demo
kubectl delete pvc lab-pvc
kubectl delete pv lab-pv
rm -f /tmp/emptydir-pod.yaml /tmp/pv.yaml /tmp/pvc.yaml /tmp/pvc-pod.yaml
```

## Next Steps
- [Storage Quiz](../../quizzes/core/04-storage-quiz.md)
- [ConfigMap and Secret Lab](./05-configuration-secrets-lab.md)

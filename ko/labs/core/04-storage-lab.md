# 스토리지 실습 가이드

> **난이도**: 중급
> **예상 소요 시간**: 40분
> **마지막 업데이트**: 2026년 2월 11일

## 학습 목표
- PersistentVolume(PV)과 PersistentVolumeClaim(PVC)을 생성합니다
- Pod에서 볼륨을 마운트하여 사용합니다
- emptyDir과 hostPath 볼륨 타입을 비교합니다

## 사전 요구 사항
- [ ] kubectl, Kubernetes 클러스터
- [ ] [스토리지](../../core/04-storage.md) 학습 완료

---

## 실습 1: emptyDir 볼륨

### 단계

**Step 1.1: emptyDir을 사용하는 Pod 생성**
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

**Step 1.2: 컨테이너 간 데이터 공유 확인**
```bash
# reader 컨테이너의 로그 확인
kubectl logs emptydir-demo -c reader --tail=5

# writer 컨테이너에서 파일 확인
kubectl exec emptydir-demo -c writer -- cat /data/log.txt
```

<details>
<summary>힌트가 필요하신가요?</summary>

- `emptyDir`은 Pod가 노드에 할당될 때 생성되고, Pod가 삭제되면 함께 삭제됩니다
- 같은 Pod 내 컨테이너 간 데이터 공유에 사용됩니다
- K8s의 사이드카 패턴에서 자주 활용됩니다
</details>

### 검증
```bash
kubectl exec emptydir-demo -c writer -- wc -l /data/log.txt
```

---

## 실습 2: PV/PVC 생성

### 단계

**Step 2.1: PersistentVolume 생성**
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

**Step 2.2: PersistentVolumeClaim 생성**
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

예상 결과:
```
NAME      STATUS   VOLUME   CAPACITY   ACCESS MODES
lab-pvc   Bound    lab-pv   1Gi        RWO
```

**Step 2.3: PVC를 사용하는 Pod 생성**
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

**Step 2.4: 데이터 영속성 테스트**
```bash
# 데이터 쓰기
kubectl exec pvc-demo -- sh -c 'echo "Persistent Data" > /usr/share/nginx/html/index.html'

# Pod 삭제 후 재생성
kubectl delete pod pvc-demo
kubectl apply -f /tmp/pvc-pod.yaml
kubectl wait --for=condition=ready pod/pvc-demo --timeout=30s

# 데이터 확인
kubectl exec pvc-demo -- cat /usr/share/nginx/html/index.html
```

<details>
<summary>힌트가 필요하신가요?</summary>

- PV는 클러스터 수준 리소스, PVC는 네임스페이스 수준 리소스입니다
- `Bound` 상태는 PVC가 PV에 바인딩되었음을 의미합니다
- `persistentVolumeReclaimPolicy: Retain`은 PVC 삭제 후에도 데이터를 보존합니다
</details>

### 검증
```bash
kubectl exec pvc-demo -- cat /usr/share/nginx/html/index.html
# 출력: Persistent Data (Pod 재생성 후에도 유지)
```

---

## 실습 3: 볼륨 타입 비교

### 단계

**Step 3.1: 볼륨 정보 비교**
```bash
echo "=== emptyDir Pod ==="
kubectl get pod emptydir-demo -o jsonpath='{.spec.volumes[*].name}: {.spec.volumes[*].emptyDir}'
echo ""
echo "=== PVC Pod ==="
kubectl get pod pvc-demo -o jsonpath='{.spec.volumes[*].name}: {.spec.volumes[*].persistentVolumeClaim.claimName}'
echo ""
echo "=== PV 상세 ==="
kubectl get pv lab-pv -o custom-columns='NAME:.metadata.name,CAPACITY:.spec.capacity.storage,ACCESS:.spec.accessModes[0],STATUS:.status.phase'
```

---

## 정리
```bash
kubectl delete pod emptydir-demo pvc-demo
kubectl delete pvc lab-pvc
kubectl delete pv lab-pv
rm -f /tmp/emptydir-pod.yaml /tmp/pv.yaml /tmp/pvc.yaml /tmp/pvc-pod.yaml
```

## 다음 단계
- [스토리지 퀴즈](../../quizzes/core/04-storage-quiz.md)
- [ConfigMap과 Secret 실습](./05-configuration-secrets-lab.md)

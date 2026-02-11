# 파드와 워크로드 실습 가이드

> **난이도**: 초급
> **예상 소요 시간**: 50분
> **마지막 업데이트**: 2025년 2월

## 학습 목표
- Pod를 YAML로 생성하고 관리합니다
- Deployment를 배포하고 스케일링합니다
- 롤링 업데이트와 롤백을 수행합니다

## 사전 요구 사항
- [ ] kubectl 설치 및 클러스터 접근 (minikube 또는 kind)
- [ ] [파드와 워크로드](../../core/02-pods-and-workloads.md) 학습 완료

---

## 실습 1: Pod 생성과 관리

### 단계

**Step 1.1: Pod YAML 작성**
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

**Step 1.2: Pod 상태 확인**
```bash
kubectl get pod nginx-lab -o wide
kubectl describe pod nginx-lab
kubectl logs nginx-lab
```

**Step 1.3: Pod 내부 접속**
```bash
kubectl exec -it nginx-lab -- bash
# 내부에서 실행:
curl localhost
exit
```

### 검증
```bash
kubectl get pod nginx-lab -o jsonpath='{.status.phase}'
# 출력: Running
```

---

## 실습 2: Deployment 배포

### 단계

**Step 2.1: Deployment 생성**
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

**Step 2.2: 배포 상태 확인**
```bash
kubectl get deployment nginx-deploy
kubectl get replicaset
kubectl get pods -l app=nginx-deploy
```

**Step 2.3: 스케일링**
```bash
kubectl scale deployment nginx-deploy --replicas=5
kubectl get pods -l app=nginx-deploy -w
# Ctrl+C로 watch 종료
```

<details>
<summary>힌트가 필요하신가요?</summary>

- `kubectl get pods -w`는 실시간 변경을 모니터링합니다
- ReplicaSet은 Deployment가 자동으로 관리합니다
- `-l` 옵션으로 라벨 기반 필터링이 가능합니다
</details>

### 검증
```bash
READY=$(kubectl get deployment nginx-deploy -o jsonpath='{.status.readyReplicas}')
echo "Ready replicas: $READY"
```

---

## 실습 3: 롤링 업데이트

### 단계

**Step 3.1: 이미지 업데이트**
```bash
kubectl set image deployment/nginx-deploy nginx=nginx:1.25 --record
kubectl rollout status deployment/nginx-deploy
```

**Step 3.2: 업데이트 이력 확인**
```bash
kubectl rollout history deployment/nginx-deploy
kubectl get replicaset -o wide
```

### 검증
```bash
kubectl get deployment nginx-deploy -o jsonpath='{.spec.template.spec.containers[0].image}'
# 출력: nginx:1.25
```

---

## 실습 4: 롤백

### 단계

**Step 4.1: 잘못된 이미지로 업데이트 (의도적 오류)**
```bash
kubectl set image deployment/nginx-deploy nginx=nginx:invalid-tag --record
kubectl rollout status deployment/nginx-deploy --timeout=30s
```

**Step 4.2: 오류 확인 및 롤백**
```bash
kubectl get pods -l app=nginx-deploy
kubectl rollback deployment/nginx-deploy 2>/dev/null || kubectl rollout undo deployment/nginx-deploy
kubectl rollout status deployment/nginx-deploy
```

### 검증
```bash
IMAGE=$(kubectl get deployment nginx-deploy -o jsonpath='{.spec.template.spec.containers[0].image}')
echo "현재 이미지: $IMAGE"
[ "$IMAGE" = "nginx:1.25" ] && echo "롤백 성공!" || echo "이미지를 확인하세요"
```

---

## 정리
```bash
kubectl delete pod nginx-lab
kubectl delete deployment nginx-deploy
rm -f /tmp/nginx-pod.yaml /tmp/nginx-deployment.yaml
```

## 다음 단계
- [파드와 워크로드 퀴즈](../../quizzes/core/02-pods-and-workloads-quiz.md)
- [서비스와 네트워킹 실습](./03-services-networking-lab.md)

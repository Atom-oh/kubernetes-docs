# ConfigMap과 Secret 실습 가이드

> **난이도**: 초급
> **예상 소요 시간**: 35분
> **마지막 업데이트**: 2026년 2월 11일

## 학습 목표
- ConfigMap을 생성하고 Pod에서 활용합니다
- Secret을 생성하고 안전하게 주입합니다
- 환경변수와 볼륨 마운트 방식을 비교합니다

## 사전 요구 사항
- [ ] kubectl, Kubernetes 클러스터
- [ ] [구성](../../core/05-configuration-secrets.md) 학습 완료

---

## 실습 1: ConfigMap 생성과 활용

### 단계

**Step 1.1: ConfigMap 생성**
```bash
# 리터럴 값으로 생성
kubectl create configmap app-config \
  --from-literal=APP_ENV=production \
  --from-literal=LOG_LEVEL=info \
  --from-literal=MAX_CONNECTIONS=100

kubectl get configmap app-config -o yaml
```

**Step 1.2: 파일에서 ConfigMap 생성**
```bash
cat > /tmp/app.properties << 'EOF'
database.host=mysql.default.svc.cluster.local
database.port=3306
database.name=myapp
EOF

kubectl create configmap app-properties --from-file=/tmp/app.properties
kubectl describe configmap app-properties
```

**Step 1.3: 환경변수로 ConfigMap 주입**
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

예상 결과:
```
APP_ENV=production LOG_LEVEL=info
```

**Step 1.4: 볼륨으로 ConfigMap 마운트**
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
<summary>힌트가 필요하신가요?</summary>

- `envFrom`은 ConfigMap의 모든 키를 환경변수로 주입합니다
- 볼륨 마운트 시 각 키가 파일명이 됩니다
- 볼륨 마운트된 ConfigMap은 업데이트 시 자동 반영됩니다 (환경변수는 Pod 재시작 필요)
</details>

---

## 실습 2: Secret 관리

### 단계

**Step 2.1: Secret 생성**
```bash
kubectl create secret generic db-secret \
  --from-literal=DB_USER=admin \
  --from-literal=DB_PASSWORD=s3cr3tP@ss

kubectl get secret db-secret -o yaml
```

**Step 2.2: Secret을 Pod에 주입**
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

예상 결과:
```
User=admin
PassLength=10
```

**Step 2.3: Secret 디코딩**
```bash
# Base64 인코딩된 값 확인
kubectl get secret db-secret -o jsonpath='{.data.DB_PASSWORD}' | base64 -d
echo ""
```

<details>
<summary>힌트가 필요하신가요?</summary>

- Secret의 값은 base64로 인코딩되어 저장됩니다 (암호화가 아닙니다!)
- 프로덕션에서는 Sealed Secrets, External Secrets, AWS Secrets Manager 등을 사용합니다
- `kubectl get secret -o yaml`에서 `.data` 필드의 값은 base64 인코딩입니다
</details>

---

## 실습 3: 환경변수 vs 볼륨 마운트 비교

### 단계

**Step 3.1: 방식별 특성 확인**
```bash
echo "=== 환경변수 방식 ==="
kubectl exec config-env-demo -- env | grep -E "APP_ENV|LOG_LEVEL|MAX_CONNECTIONS"

echo ""
echo "=== 볼륨 마운트 방식 ==="
kubectl exec config-vol-demo -- ls /config/
kubectl exec config-vol-demo -- cat /config/app.properties
```

---

## 정리
```bash
kubectl delete pod config-env-demo config-vol-demo secret-demo
kubectl delete configmap app-config app-properties
kubectl delete secret db-secret
rm -f /tmp/app.properties /tmp/configmap-env-pod.yaml /tmp/configmap-vol-pod.yaml /tmp/secret-pod.yaml
```

## 다음 단계
- [구성 퀴즈](../../quizzes/core/05-configuration-secrets-quiz.md)
- [EKS 클러스터 생성 실습](../eks/01-eks-cluster-creation-lab.md)

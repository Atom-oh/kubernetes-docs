# 파드와 워크로드 실습 가이드

> **난이도**: 초급
> **예상 소요 시간**: 50분
> **마지막 업데이트**: 2026년 9월 11일

## 학습 목표
- Pod를 YAML로 생성하고 관리합니다
- Deployment를 배포하고 스케일링합니다
- 롤링 업데이트와 롤백을 수행합니다

## 사전 요구 사항
- [ ] kubectl 설치 및 클러스터 접근 (minikube 또는 kind)
- [ ] [파드와 워크로드](../../core/02-pods-and-workloads.md) 학습 완료

실습 네임스페이스 생성·예제 이미지 pull 권한이 있는 기존의 폐기 가능한 kind/minikube 클러스터를 사용합니다. 설정 실행 전에 context를 확인하세요. 같은 Bash 세션을 유지하며 함수가 context·namespace를 고정합니다. 사용자가 실행하면 실제로 변경되며 이번 감사에서는 클러스터 작업을 수행하지 않았습니다.

```bash
WORKLOADS_LAB_DIR=$(mktemp -d /tmp/k8s-docs-workloads.XXXXXX)
: "${WORKLOADS_LAB_DIR:?mktemp failed}"
WORKLOADS_LAB_CONTEXT=$(kubectl config current-context)
: "${WORKLOADS_LAB_CONTEXT:?No current context selected}"
printf 'Selected context: %s\n' "$WORKLOADS_LAB_CONTEXT"
WORKLOADS_LAB_CANDIDATE=$(basename "$WORKLOADS_LAB_DIR" | tr '[:upper:].' '[:lower:]-')
unset WORKLOADS_LAB_NAMESPACE WORKLOADS_LAB_GOOD_REVISION
if WORKLOADS_LAB_UID=$(kubectl --context "$WORKLOADS_LAB_CONTEXT" create namespace "$WORKLOADS_LAB_CANDIDATE" -o jsonpath='{.metadata.uid}'); then
  WORKLOADS_LAB_NAMESPACE=$WORKLOADS_LAB_CANDIDATE
else
  printf 'Namespace creation failed; do not continue with workload commands\n' >&2
fi
workload_kubectl() {
  kubectl --context "${WORKLOADS_LAB_CONTEXT:?}" \
    --namespace "${WORKLOADS_LAB_NAMESPACE:?Create the lab namespace first}" "$@"
}
```

---

## 실습 1: Pod 생성과 관리

### 단계

**Step 1.1: Pod YAML 작성**
```bash
cat > "${WORKLOADS_LAB_DIR:?}/nginx-pod.yaml" << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: nginx-lab
  labels:
    app: nginx
    env: lab
spec:
  automountServiceAccountToken: false
  containers:
  - name: nginx
    image: nginx:1.30.4
    ports:
    - name: http
      containerPort: 80
    resources:
      requests:
        memory: 64Mi
        cpu: 100m
      limits:
        memory: 128Mi
        cpu: 200m
    readinessProbe:
      httpGet:
        path: /
        port: http
      periodSeconds: 3
EOF
workload_kubectl apply -f "$WORKLOADS_LAB_DIR/nginx-pod.yaml"
```

**Step 1.2: Pod 상태 확인**
Running phase만으로 준비 상태를 뜻하지 않습니다. 로그·exec 전에 HTTP readiness probe를 기다리고, 시간 초과를 성공으로 처리하지 말고 원인을 확인하세요.

```bash
workload_kubectl wait --for=condition=Ready pod/nginx-lab --timeout=120s
workload_kubectl get pod nginx-lab -o wide
workload_kubectl describe pod nginx-lab
workload_kubectl logs nginx-lab
```

**Step 1.3: Pod 내부 접속**
```bash
workload_kubectl exec -it nginx-lab -- sh
# Inside the container:
nginx -v
ls /usr/share/nginx/html/
exit
```

### 검증
```bash
workload_kubectl wait --for=condition=Ready pod/nginx-lab --timeout=120s
workload_kubectl get pod nginx-lab -o wide
```

---

## 실습 2: Deployment 배포

### 단계

**Step 2.1: Deployment 생성**
Deployment는 maxUnavailable0·maxSurge1로 의도적인 잘못된 이미지 롤아웃 중 기존 ready 복제본을 유지하도록 설정합니다. surge·종료 중 Pod와 별도 Pod를 위한 여유 용량이 필요합니다. 다른 장애에서의 가용성을 보장하는 것은 아닙니다.

```bash
cat > "${WORKLOADS_LAB_DIR:?}/nginx-deployment.yaml" << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deploy
spec:
  replicas: 3
  revisionHistoryLimit: 5
  progressDeadlineSeconds: 120
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  selector:
    matchLabels:
      app: nginx-deploy
  template:
    metadata:
      labels:
        app: nginx-deploy
    spec:
      automountServiceAccountToken: false
      containers:
      - name: nginx
        image: nginx:1.30.4
        ports:
        - name: http
          containerPort: 80
        resources:
          requests:
            memory: 64Mi
            cpu: 100m
          limits:
            memory: 128Mi
            cpu: 200m
        readinessProbe:
          httpGet:
            path: /
            port: http
          periodSeconds: 3
EOF
workload_kubectl apply -f "$WORKLOADS_LAB_DIR/nginx-deployment.yaml"
```

**Step 2.2: 배포 상태 확인**
```bash
workload_kubectl rollout status deployment/nginx-deploy --timeout=120s
workload_kubectl get deployment nginx-deploy
workload_kubectl get replicasets,pods -l app=nginx-deploy
```

**Step 2.3: 스케일링**
```bash
workload_kubectl scale deployment nginx-deploy --replicas=5
workload_kubectl rollout status deployment/nginx-deploy --timeout=120s
workload_kubectl get pods -l app=nginx-deploy
```

<details>
<summary>힌트가 필요하신가요?</summary>

- `kubectl get pods -w`는 실시간 변경을 모니터링합니다
- ReplicaSet은 Deployment가 자동으로 관리합니다
- `-l` 옵션으로 라벨 기반 필터링이 가능합니다
</details>

### 검증
```bash
READY=$(workload_kubectl get deployment nginx-deploy -o jsonpath='{.status.readyReplicas}')
printf 'Ready replicas: %s\n' "$READY"
[ "$READY" = "5" ]
```

---

## 실습 3: 롤링 업데이트

### 단계

**Step 3.1: 이미지 업데이트**
지원이 끝난 NGINX 버전을 쓰지 않고 같은 유지보수 릴리스의 기반 이미지 변형을 변경합니다. deprecated --record 대신 `kubernetes.io/change-cause`로 의도를 기록합니다. 롤백을 위해 완료된 revision을 저장하세요.

```bash
workload_kubectl annotate deployment/nginx-deploy \
  kubernetes.io/change-cause="NGINX 1.30.4 Debian to Alpine variant" --overwrite
unset WORKLOADS_LAB_GOOD_REVISION
if workload_kubectl set image deployment/nginx-deploy nginx=nginx:1.30.4-alpine &&
   workload_kubectl rollout status deployment/nginx-deploy --timeout=120s; then
  WORKLOADS_LAB_GOOD_REVISION=$(workload_kubectl get deployment nginx-deploy \
    -o jsonpath='{.metadata.annotations.deployment\.kubernetes\.io/revision}')
  : "${WORKLOADS_LAB_GOOD_REVISION:?No completed revision recorded}"
else
  printf 'Healthy rollout not confirmed; stop before the failure/rollback exercise\n' >&2
fi
```

**Step 3.2: 업데이트 이력 확인**
```bash
workload_kubectl rollout history deployment/nginx-deploy
workload_kubectl get replicasets -l app=nginx-deploy -o wide
```

### 검증
```bash
workload_kubectl get deployment nginx-deploy -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
# Expected configured image: nginx:1.30.4-alpine
```

---

## 실습 4: 롤백

### 단계

**Step 4.1: 잘못된 이미지로 업데이트 (의도적 오류)**
예약된 .invalid 레지스트리는 격리된 실습의 의도적인 오류입니다. rollout timeout은 스케줄링·quota·API 문제로도 발생하므로 Pod 이벤트·상태를 확인합니다. 롤백은 보존된 Pod 템플릿을 복원하며 외부 데이터·ConfigMap/Secret 내용·DB 마이그레이션을 되돌리지 않습니다.

```bash
workload_kubectl annotate deployment/nginx-deploy \
  kubernetes.io/change-cause="Intentional lab image-pull failure" --overwrite
workload_kubectl set image deployment/nginx-deploy nginx=registry.invalid/training/nginx:unavailable
if workload_kubectl rollout status deployment/nginx-deploy --timeout=30s; then
  printf 'Unexpected completion; inspect which image is running\n'
else
  printf 'Rollout did not complete; inspect Pod status/events to identify the cause\n'
fi
```

**Step 4.2: 오류 확인 및 롤백**
```bash
workload_kubectl get pods -l app=nginx-deploy
workload_kubectl describe deployment nginx-deploy
workload_kubectl get events --sort-by=.metadata.creationTimestamp
workload_kubectl rollout undo deployment/nginx-deploy \
  --to-revision="${WORKLOADS_LAB_GOOD_REVISION:?Complete Step 3.1 first}"
workload_kubectl rollout status deployment/nginx-deploy --timeout=120s
```

### 검증
```bash
IMAGE=$(workload_kubectl get deployment nginx-deploy -o jsonpath='{.spec.template.spec.containers[0].image}')
printf 'Current image: %s\n' "$IMAGE"
[ "$IMAGE" = "nginx:1.30.4-alpine" ]
workload_kubectl rollout status deployment/nginx-deploy --timeout=120s
```

---

## 정리
```bash
# Delete the isolated lab namespace only if its recorded identity still matches.
if [[ -n ${WORKLOADS_LAB_NAMESPACE:-} && -n ${WORKLOADS_LAB_UID:-} ]]; then
  current_uid=$(kubectl --context "${WORKLOADS_LAB_CONTEXT:?}" get namespace "$WORKLOADS_LAB_NAMESPACE" -o jsonpath='{.metadata.uid}') || current_uid=""
  if [ "$current_uid" = "$WORKLOADS_LAB_UID" ]; then
    kubectl --context "$WORKLOADS_LAB_CONTEXT" delete namespace "$WORKLOADS_LAB_NAMESPACE" --timeout=120s
  else
    printf 'Namespace missing or identity changed; automatic deletion skipped\n'
  fi
fi
if [[ -n ${WORKLOADS_LAB_DIR:-} ]]; then
  rm -f -- "$WORKLOADS_LAB_DIR/nginx-pod.yaml" "$WORKLOADS_LAB_DIR/nginx-deployment.yaml"
  rmdir -- "$WORKLOADS_LAB_DIR"
fi
unset -f workload_kubectl
```


## 참고 자료와 검증 범위

* [Deployments, rollout and rollback](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
* [kubectl rollout undo](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_rollout/kubectl_rollout_undo/)
* [Readiness and liveness probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

매니페스트·명령을 로컬 검사합니다. 이번 감사에서 클러스터 배포·이미지 pull·스케일링·롤백·네임스페이스 삭제를 실행하지 않았습니다.

## 다음 단계
- [파드와 워크로드 퀴즈](../../quizzes/core/02-pods-and-workloads-quiz.md)
- [서비스와 네트워킹 실습](./03-services-networking-lab.md)

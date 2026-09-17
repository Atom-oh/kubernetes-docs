# 스케줄러 스코어링 전략 실습: LeastAllocated vs. MostAllocated

> **난이도**: 중급
> **예상 소요 시간**: 30분
> **마지막 업데이트**: 2026년 9월 17일

## 학습 목표
- 이 실습만을 위한 폐기 가능한 멀티 노드 `kind` 클러스터를 만듭니다
- `nodeName`으로 고정한 포드를 이용해 노드별 CPU 사용률을 불균등하게 만듭니다
- 그 상태에서 기본 스케줄러의 `LeastAllocated` 배치 동작을 관찰합니다
- `NodeResourcesFit`의 `MostAllocated` 스코어링 전략으로 설정한 두 번째 스케줄러를 배포하고 배치 결과를 비교합니다
- Karpenter/Cluster Autoscaler와 함께 실행되는 배치 워크로드에 `MostAllocated` 빈패킹이 왜 유리한지 설명합니다

## 사전 요구 사항
- [ ] `kubectl`, `docker`(또는 kind가 지원하는 다른 컨테이너 런타임)
- [ ] `kind` v0.20 이상 (없으면 이 실습에서 로컬에 설치합니다)
- [ ] [스케줄링, 선점 및 축출](../../core/08-scheduling-preemption-eviction.md) 학습 완료, 특히 [NodeResourcesFit 스코어링 전략: LeastAllocated vs. MostAllocated](../../core/08-scheduling-preemption-eviction.md#noderesourcesfit-스코어링-전략-leastallocated-vs-mostallocated) 절

이 실습은 기존 클러스터를 재사용하지 않고 전용 멀티 노드 `kind` 클러스터를 새로 만듭니다. 워커 노드별 CPU 할당량을 독립적으로 관찰하려면 최소 3개의 워커 노드가 필요하기 때문입니다. 실습이 끝나면 클러스터를 완전히 삭제합니다. 같은 셸에서 순서대로 실행하고, 앞선 명령이 실패하면 중단합니다.

```bash
SCHED_LAB_DIR=$(mktemp -d /tmp/k8s-docs-sched.XXXXXX)
: "${SCHED_LAB_DIR:?mktemp failed}"
cd "$SCHED_LAB_DIR"

if ! command -v kind >/dev/null 2>&1; then
  KIND_ARCH=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')
  curl -Lo ./kind "https://kind.sigs.k8s.io/dl/v0.33.0/kind-linux-${KIND_ARCH}"
  chmod +x ./kind
  SCHED_LAB_KIND=./kind
else
  SCHED_LAB_KIND=kind
fi
"$SCHED_LAB_KIND" version
```

---

## 실습 1: 테스트 클러스터 생성과 불균등한 초기 상태 만들기

### 단계

**Step 1.1: 워커 노드 3개짜리 kind 클러스터 생성**
```bash
cat > "$SCHED_LAB_DIR/kind-config.yaml" << 'EOF'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: scheduler-strategy-lab
nodes:
- role: control-plane
- role: worker
- role: worker
- role: worker
EOF

export KUBECONFIG="$SCHED_LAB_DIR/kubeconfig"
"$SCHED_LAB_KIND" create cluster --config "$SCHED_LAB_DIR/kind-config.yaml"
kubectl wait --for=condition=Ready nodes --all --timeout=120s
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"  cpu="}{.status.allocatable.cpu}{"\n"}{end}'
```
kind 노드는 호스트를 공유하는 컨테이너이므로 네 노드 모두 같은 할당 가능 CPU(예: `cpu=16`)를 보고합니다. 실제 값은 실습 환경의 호스트 사양에 따라 다릅니다.

**Step 1.2: 워커 노드 이름 기록**
```bash
mapfile -t SCHED_LAB_WORKERS < <(kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | grep -v control-plane)
printf 'Workers: %s\n' "${SCHED_LAB_WORKERS[*]}"
kubectl create namespace sched-lab
```

**Step 1.3: 필러(filler) 포드로 CPU 사용률을 불균등하게 만들기**

`spec.nodeName`(스케줄러를 거치지 않고 노드를 직접 지정)을 사용해 세 워커 노드의 시작 사용률을 각각 75%, 약 37%, 0%로 만듭니다.

```bash
{
  for i in $(seq 1 12); do
cat << EOF
apiVersion: v1
kind: Pod
metadata:
  name: filler-busy-${i}
  namespace: sched-lab
  labels: { role: filler }
spec:
  nodeName: ${SCHED_LAB_WORKERS[0]}
  containers:
  - name: filler
    image: registry.k8s.io/pause:3.10
    resources:
      requests: { cpu: "1000m", memory: "64Mi" }
      limits: { cpu: "1000m", memory: "64Mi" }
---
EOF
  done
  for i in $(seq 1 6); do
cat << EOF
apiVersion: v1
kind: Pod
metadata:
  name: filler-medium-${i}
  namespace: sched-lab
  labels: { role: filler }
spec:
  nodeName: ${SCHED_LAB_WORKERS[1]}
  containers:
  - name: filler
    image: registry.k8s.io/pause:3.10
    resources:
      requests: { cpu: "1000m", memory: "64Mi" }
      limits: { cpu: "1000m", memory: "64Mi" }
---
EOF
  done
} > "$SCHED_LAB_DIR/filler-pods.yaml"

kubectl apply -f "$SCHED_LAB_DIR/filler-pods.yaml"
kubectl -n sched-lab wait --for=condition=Ready pod -l role=filler --timeout=120s
kubectl describe nodes "${SCHED_LAB_WORKERS[@]}" | grep -E "^Name:|cpu\s+[0-9]"
```

### 예상 결과
대략 다음과 같이 나타나야 합니다:
- `${SCHED_LAB_WORKERS[0]}` (이하 **A**): 요청량 12000m, 약 75%
- `${SCHED_LAB_WORKERS[1]}` (이하 **B**): 요청량 6000m, 약 37%
- `${SCHED_LAB_WORKERS[2]}` (이하 **C**): 요청량 약 0m, 0%

정확한 퍼센트는 호스트가 kind에 보고하는 CPU 코어 수에 따라 달라지지만, A > B > C 순서는 그대로 재현되어야 합니다.

---

## 실습 2: 기본 스케줄러(`LeastAllocated`) 관찰

### 단계

**Step 2.1: 기본 스케줄러로 새 포드 6개 배치**
```bash
for i in $(seq 1 6); do
cat << EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: batch-default-${i}
  namespace: sched-lab
  labels: { role: batch-default }
spec:
  containers:
  - name: batch
    image: registry.k8s.io/pause:3.10
    resources:
      requests: { cpu: "1000m", memory: "64Mi" }
      limits: { cpu: "1000m", memory: "64Mi" }
EOF
done
kubectl -n sched-lab wait --for=condition=Ready pod -l role=batch-default --timeout=60s
```

**Step 2.2: 배치 위치 확인**
```bash
kubectl -n sched-lab get pods -l role=batch-default -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName
kubectl describe nodes "${SCHED_LAB_WORKERS[@]}" | grep -E "^Name:|cpu\s+[0-9]"
```

### 예상 결과
6개 포드 전부가 가장 비어 있던 **C** 노드에 배치되어, C의 사용률이 B와 비슷한 수준까지 올라갑니다. 이것이 `LeastAllocated`의 동작입니다: 기본 스케줄러는 새 포드마다 여유 용량이 가장 많은 노드를 계속 선택하므로, 소수 노드에 몰리기보다 노드 간 사용률이 서로 비슷해지는 방향으로 수렴합니다. 이 단계 이후에는 세 워커 노드 모두 어느 정도 부하를 갖게 되어, 그중 어느 노드도 스케일 다운의 깔끔한 후보가 되지 못합니다.

---

## 실습 3: `MostAllocated` 두 번째 스케줄러 배포와 비교

### 단계

**Step 3.1: 초기화 — 실습 2의 포드만 제거하고 필러는 그대로 유지**
```bash
kubectl -n sched-lab delete pod -l role=batch-default --wait=true
```

**Step 3.2: `MostAllocated`로 설정한 두 번째 kube-scheduler 배포**
```bash
cat > "$SCHED_LAB_DIR/most-allocated-scheduler.yaml" << 'EOF'
apiVersion: v1
kind: ServiceAccount
metadata:
  name: most-allocated-scheduler
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: most-allocated-scheduler-as-kube-scheduler
roleRef: { apiGroup: rbac.authorization.k8s.io, kind: ClusterRole, name: system:kube-scheduler }
subjects:
- kind: ServiceAccount
  name: most-allocated-scheduler
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: most-allocated-scheduler-as-volume-scheduler
roleRef: { apiGroup: rbac.authorization.k8s.io, kind: ClusterRole, name: system:volume-scheduler }
subjects:
- kind: ServiceAccount
  name: most-allocated-scheduler
  namespace: kube-system
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: most-allocated-scheduler-config
  namespace: kube-system
data:
  config.yaml: |
    apiVersion: kubescheduler.config.k8s.io/v1
    kind: KubeSchedulerConfiguration
    leaderElection:
      leaderElect: false
    profiles:
    - schedulerName: most-allocated-scheduler
      pluginConfig:
      - name: NodeResourcesFit
        args:
          scoringStrategy:
            type: MostAllocated
            resources:
            - { name: cpu, weight: 1 }
            - { name: memory, weight: 1 }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: most-allocated-scheduler
  namespace: kube-system
spec:
  replicas: 1
  selector: { matchLabels: { app: most-allocated-scheduler } }
  template:
    metadata: { labels: { app: most-allocated-scheduler } }
    spec:
      serviceAccountName: most-allocated-scheduler
      containers:
      - name: kube-scheduler
        image: registry.k8s.io/kube-scheduler:v1.37.0
        command: ["kube-scheduler", "--config=/etc/kubernetes/scheduler-config/config.yaml", "-v=2"]
        volumeMounts:
        - { name: config, mountPath: /etc/kubernetes/scheduler-config }
      volumes:
      - name: config
        configMap: { name: most-allocated-scheduler-config }
EOF

kubectl apply -f "$SCHED_LAB_DIR/most-allocated-scheduler.yaml"
kubectl -n kube-system rollout status deployment/most-allocated-scheduler --timeout=120s
```
`image: registry.k8s.io/kube-scheduler:v1.37.0`은 실습 클러스터의 실제 마이너 버전에 맞춰야 합니다(`kubectl version`으로 확인). 스케줄러 바이너리가 API 서버와 마이너 버전이 1 이상 차이 나면 시작에 실패하거나 예측할 수 없게 동작할 수 있습니다.

**Step 3.3: 동일한 포드 6개를 이번에는 `schedulerName`으로 배치**
```bash
for i in $(seq 1 6); do
cat << EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: batch-mostalloc-${i}
  namespace: sched-lab
  labels: { role: batch-mostalloc }
spec:
  schedulerName: most-allocated-scheduler
  containers:
  - name: batch
    image: registry.k8s.io/pause:3.10
    resources:
      requests: { cpu: "1000m", memory: "64Mi" }
      limits: { cpu: "1000m", memory: "64Mi" }
EOF
done
kubectl -n sched-lab wait --for=condition=Ready pod -l role=batch-mostalloc --timeout=60s
```

**Step 3.4: 배치 위치 확인 및 비교**
```bash
kubectl -n sched-lab get pods -l role=batch-mostalloc -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName
kubectl describe nodes "${SCHED_LAB_WORKERS[@]}" | grep -E "^Name:|cpu\s+[0-9]"
```

### 예상 결과와 참조 테스트 결과

이 실습 원고를 작성하면서 노드당 할당 가능 CPU 16코어인 워커 3개짜리 kind 클러스터(`kubectl version` 결과 `v1.37.0`)에서 위 절차를 실제로 한 번 실행했습니다:

| 스케줄러 / 전략 | 새 포드 6개가 배치된 곳 | 최종 CPU 사용률 (A / B / C) |
|---|---|---|
| 기본값 (`LeastAllocated`) | C 노드에 6개 전부 배치 | 75% / 37% / 37% — 세 노드 모두 사용 중 |
| `MostAllocated` | A 노드에 3개, B 노드에 3개 | 93% / 56% / 0% — C 노드는 완전히 그대로 유지 |

절대 사용률은 실습 환경의 호스트 CPU 코어 수에 따라 달라지지만, **패턴**은 그대로 재현되어야 합니다: `LeastAllocated`는 유휴 노드를 이웃 노드 수준까지 채우고, `MostAllocated`는 이미 바쁜 노드에 계속 쌓아 올리며 유휴 노드는 건드리지 않습니다. 이렇게 남은 유휴 노드가 바로 Cluster Autoscaler나 Karpenter의 통합(consolidation) 로직이 종료 대상으로 삼는 노드입니다. 그래서 오토스케일러와 함께 실행되는 배치/단명 Job 워크로드에는 `MostAllocated`가, 모든 노드에 여유 공간을 두고자 하는 장시간 실행·지연 민감형 서비스에는 여전히 `LeastAllocated`가 더 안전한 기본값입니다.

---

## 정리
```bash
unset KUBECONFIG
"$SCHED_LAB_KIND" delete cluster --name scheduler-strategy-lab --kubeconfig "$SCHED_LAB_DIR/kubeconfig"
rm -rf -- "$SCHED_LAB_DIR"
unset SCHED_LAB_DIR SCHED_LAB_KIND SCHED_LAB_WORKERS
```

## 참고 자료와 검증 범위

- [Scheduler Configuration — Kubernetes documentation](https://kubernetes.io/docs/reference/scheduling/config/)
- [NodeResourcesFit scoring strategies](https://kubernetes.io/docs/reference/config-api/kube-scheduler-config.v1/)
- [Configure Multiple Schedulers](https://kubernetes.io/docs/tasks/extend-kubernetes/configure-multiple-schedulers/)

이 실습은 클러스터 생성, 필러 포드 배치, 두 스케줄러 패스, 정리까지 전 과정을 격리된 폐기 가능한 `kind` 클러스터에서 실제로 실행했습니다. 공유 클러스터나 클라우드 리소스는 전혀 사용하지 않았습니다. 위 참조 결과 표는 가상의 예측이 아니라 그 실행에서 실제로 관찰된 출력을 기록한 것입니다.

## 다음 단계
- [스케줄링, 선점 및 축출 퀴즈](../../quizzes/core/08-scheduling-preemption-eviction-quiz.md)
- [커스텀 스케줄러 만들기](../../scheduling/01-custom-scheduler-part1.md)

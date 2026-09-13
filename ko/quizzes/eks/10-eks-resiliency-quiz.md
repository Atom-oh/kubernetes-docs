# Amazon EKS 고가용성 및 복원력 퀴즈

> **예제 API 기준**: Kubernetes 1.36; 공식 근거·예제 전제는 [본문](../../eks/10-eks-resiliency.md)과 동일합니다.
> **마지막 업데이트**: 2026년 9월 12일

설정·수치는 예시이며 감사에서 cloud 자원·chaos·workload·benchmark를 실행하지 않았습니다. 소유 test 범위에서 placeholder를 교체한 뒤 배포합니다.

이 퀴즈는 Amazon EKS 클러스터의 고가용성(HA), 복원력, Multi-AZ 배포, Cell-Based Architecture, Chaos Engineering, PodDisruptionBudget, Topology Spread Constraints에 대한 이해를 테스트합니다.

## 퀴즈 개요
- Multi-AZ 아키텍처 및 구성
- Cell-Based Architecture 패턴
- Chaos Engineering 원칙 및 도구
- PodDisruptionBudget (PDB) 구성
- Topology Spread Constraints
- 장애 복구 및 재해 복구

## 객관식 문제

### 1. EKS workload를 Multi-AZ로 배치하는 주요 복원력 이점은 무엇인가요?

A. 자동 비용 절감
B. 용량·data·routing 준비 시 한 AZ 장애 후 서비스 지속을 지원
C. 지연시간 증가 자체
D. 운영 복잡성 제거

<details>
<summary>정답 보기</summary>

**정답: B. 용량·data·routing 준비 시 한 AZ 장애 후 서비스 지속을 지원**

Multi-AZ는 장애 영역 설계를 개선하지만 자동 workload·data failover나 99.99% 가용성을 보장하지 않습니다. Region 전체 장애도 해결하지 않습니다. 동일 용량 node 6개를 3 AZ에 균등 배치하면 하나의 AZ 손실 후 4개가 남는 예시이며 실제 Pod·용량을 확인해야 합니다. 아래는 실행하지 않은 provisioning 입력입니다. 1.36은 장의 기준이며 생성 전 현재 region의 EKS·AMI 지원을 확인합니다.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: owned-ha-example
  region: us-west-2
  version: '1.36'
managedNodeGroups:
- name: ng-multi-az
  instanceType: m5.large
  desiredCapacity: 6
  availabilityZones:
  - us-west-2a
  - us-west-2b
  - us-west-2c
```

</details>

### 2. PodDisruptionBudget은 무엇을 제한하나요?

A. Pod CPU 사용량
B. Workload 가용성을 고려하는 지원 자발적 eviction
C. 모든 Pod 간 traffic
D. 모든 Pod 종료 원인

<details>
<summary>정답 보기</summary>

**정답: B. Workload 가용성을 고려하는 지원 자발적 eviction**

PDB는 협력하는 drain·유지보수·autoscaler가 사용하는 Eviction API를 제한합니다. 직접 Pod 삭제, Deployment rollout·scale-down, 비자발적 장애를 보호하지는 않습니다. minAvailable·maxUnavailable 중 하나를 선택하고 대상 controller workload label을 일치시킵니다. 아래 percentage PDB와 함께 중복 적용하는 것이 아닌 대안입니다.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
  namespace: resilience-demo
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web-app
```

</details>

### 3. whenUnsatisfiable: DoNotSchedule은 어떤 동작인가요?

A. 제약과 무관하게 어디든 배치
B. Spread 제약을 만족하는 eligible node가 없으면 새 Pod를 미배치 상태로 유지
C. 모든 scheduling 제약 무시
D. 기존 Pod를 삭제해 균형 복원

<details>
<summary>정답 보기</summary>

**정답: B. Spread 제약을 만족하는 eligible node가 없으면 새 Pod를 미배치 상태로 유지**

API server가 Pod 객체 생성을 거부한다는 뜻이 아닌 scheduling filter입니다. ScheduleAnyway도 이 spread rule만 선호도로 바꾸며 resource·affinity·taint·storage 조건은 남습니다. 완전한 Deployment 예시의 placeholder image·앱 health path는 적용 전에 교체합니다. minDomains=2는 eligible zone 두 개가 남을 때 N-1 계산을 허용하지만 초기 3 AZ 점유·용량 생성을 강제하지 않습니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: resilience-demo
spec:
  replicas: 6
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: app
        image: registry.example.com/team/web-app:replace-with-reviewed-digest
        ports:
        - name: http
          containerPort: 8080
        startupProbe:
          httpGet:
            path: /healthz
            port: http
          failureThreshold: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        lifecycle:
          preStop:
            sleep:
              seconds: 5
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-app
```

</details>

### 4. Cell 기반 아키텍처의 목표가 아닌 것은 무엇인가요?

A. 독립 배포·확장
B. Cell 장애를 전체 시스템으로 전파
C. 자체 완결된 기능 단위
D. 다른 cell과의 제한한 결합

<details>
<summary>정답 보기</summary>

**정답: B. Cell 장애를 전체 시스템으로 전파**

격리는 구현·검증할 설계 속성이며 Namespace label만으로 생기는 보장이 아닙니다. Routing·admission limit·용량·data 의존성을 분리하고 공유 node·control plane·DNS·router를 고려합니다. 아래 namespace는 그룹만 표현하며 quota·NetworkPolicy도 물리적 장애 영역을 만들지 않습니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cell-a
  labels:
    cell: a
```
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cell-b
  labels:
    cell: b
```

</details>

### 5. 카오스 엔지니어링의 steady-state hypothesis는 무엇인가요?

A. 서비스를 정지 상태로 유지
B. 장애 전·중·후 허용 동작에 대한 측정 가능한 가설
C. 실험 중단 명령만
D. 가능한 최대 부하

<details>
<summary>정답 보기</summary>

**정답: B. 장애 전·중·후 허용 동작에 대한 측정 가능한 가설**

실험 전에 사용자 관점 metric·기간·missing-data 처리·abort threshold를 정의합니다. 기존 p99<200ms·오류<0.1%·처리량>1000req/s·Ready Pod>99%는 관측값이 아닌 예시 기준입니다. Ready Pod 비율은 요청 가용성이 아닙니다. 검토한 Litmus CRD에는 ChaosExperiment.spec.definition.steadyState가 없습니다. 아래 JSON은 Kubernetes resource가 아닌 검토 계획입니다.

```json
{
  "scenario": "one bounded test fault",
  "hypothesis": {
    "p99_latency_seconds": "<0.2",
    "error_percentage": "<0.1",
    "request_rate_per_second": ">1000",
    "ready_pod_percentage": ">99"
  },
  "required_observations": [
    "baseline",
    "during fault",
    "recovery",
    "missing data"
  ],
  "abort": "Set an independent measured threshold and recovery owner before execution"
}
```

</details>

### 6. Kubernetes 1.36 기준에서 같은 zone 선호도를 표현하는 Service 필드는 무엇인가요?

A. spec.trafficDistribution: PreferSameZone
B. spec.zoneRouting: enabled
C. spec.localOnly: true
D. spec.crossZone: disabled

<details>
<summary>정답 보기</summary>

**정답: A. spec.trafficDistribution: PreferSameZone**

PreferSameZone·PreferSameNode는 1.35부터 GA입니다. 엄격한 격리·비용 절감 보장이 아닌 선호입니다. PreferClose는 이전 alias이고 topology-mode=Auto annotation은 별도 hint 휴리스틱을 사용합니다. topology-aware-hints는 legacy 안내입니다. Proxy 구현·EndpointSlice·Local traffic policy 우선순위를 확인합니다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-app
  namespace: resilience-demo
spec:
  selector:
    app: web-app
  ports:
  - name: http
    port: 80
    targetPort: http
  trafficDistribution: PreferSameZone
```

</details>

### 7. 정상 replica 8개·진행 중 disruption 없음·maxUnavailable: 25%일 때 명목상 eviction 허용 수는?

A. 1
B. 2
C. 3
D. 4

<details>
<summary>정답 보기</summary>

**정답: B. 2**

ceil(8×0.25)=2입니다. 두 PDB percentage 형식 모두 내림이 아닌 올림입니다. Replica 3개의 maxUnavailable 25%는 ceil(0.75)=1, minAvailable 75%는 ceil(2.25)=3개 정상 Pod를 요구합니다. 비정상·진행 중 disruption이 budget을 소비하며 모든 장애에서 항상 6개가 실행된다는 보장이 아닙니다.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb-percentage
  namespace: resilience-demo
spec:
  selector:
    matchLabels:
      app: web-app
  maxUnavailable: 25%
```

</details>

### 8. 검토한 Litmus operator·catalog에 대한 설명 중 틀린 것은?

A. pod-delete는 catalog fault
B. node-drain은 instance termination과 다름
C. pod-network-loss는 catalog fault
D. cluster-delete는 전체 EKS cluster를 지우는 표준 fault

<details>
<summary>정답 보기</summary>

**정답: D. cluster-delete는 전체 EKS cluster를 지우는 표준 fault**

검토한 catalog에는 정확한 Pod·node fault명이 있으며 주장한 cluster-delete는 없습니다. network-loss·ec2-terminate 같은 일반 표현을 유효 ID로 추정하지 않습니다. 현재 AWS catalog에는 aws-az-chaos·ebs-loss-by-id/by-tag·ec2-stop-by-id/by-tag가 있습니다. 실제 fault 정의·RBAC·runner image를 확인합니다. Operator만 설치해도 모든 실험이 생기지는 않으며 3.31.0 operator에는 ChaosHub·ChaosSchedule이 없습니다.


</details>

### 9. Regional EKS control-plane 가용성은 누가 관리하나요?

A. 사용자가 API server를 수동 배치
B. AWS가 regional control plane을 3 AZ에 걸쳐 관리
C. 항상 단일 AZ control plane
D. 사용자가 managed EKS etcd failover를 구현

<details>
<summary>정답 보기</summary>

**정답: B. AWS가 regional control plane을 3 AZ에 걸쳐 관리**

Regional EKS의 managed control plane은 3 AZ에 분산되며 고객 subnet의 최소 2 AZ 요구와 다릅니다. Standard endpoint 월 SLA는 99.95%, Provisioned는 99.99%이며 service-credit 조건·측정 간격이 다릅니다. 앱 가용성 보장이나 고객 workload·PV backup은 아니며 workload·data-plane 배치·data 복구·SLO 측정은 고객 책임입니다.


</details>

### 10. DoNotSchedule에서 새 Pod 배치 시 maxSkew가 제한하는 것은?

A. 전체 Pod 최대 수
B. 후보 domain count와 global minimum의 차이
C. 최소 node 수
D. Node당 최대 Pod 수

<details>
<summary>정답 보기</summary>

**정답: B. 후보 domain count와 global minimum의 차이**

Eligible domain·minDomains가 global minimum을 결정하며 eligible 수가 minDomains보다 적으면 minimum은 0입니다. 두 zone의 2/2 상태라도 minDomains=3·maxSkew=1이면 replacement가 막힐 수 있습니다. 2/2/2는 정상 예시이지 영구 불변식이 아닙니다. 3/2/1은 skew 2 예시이며 4/1/1의 많은 쪽에 추가 배치는 실패할 수 있습니다. 기존 Pod를 자동 재배치·삭제하지 않습니다.


</details>

## 단답형 문제

### 1. Kubernetes 1.36 Service에서 같은 zone 선호도를 표현하는 필드는?

<details>
<summary>정답 보기</summary>

spec.trafficDistribution: PreferSameZone입니다. 선호도이므로 실제 routing·cost를 측정합니다. Legacy topology-aware-hints annotation은 현재 답이 아닙니다. Local traffic policy와 실제 Service 구현을 확인합니다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-app
  namespace: resilience-demo
spec:
  selector:
    app: web-app
  ports:
  - name: http
    port: 80
    targetPort: http
  trafficDistribution: PreferSameZone
```

</details>

### 2. PDB를 고려한 자발적 eviction을 사용할 수 있는 동작 세 가지와 우회 경로를 구분하세요.

<details>
<summary>정답 보기</summary>

예: Eviction을 사용하는 kubectl drain, Eviction 기반 drain을 수행하는 upgrade, PDB와 협력하는 node autoscaler scale-down입니다. 구현·force 옵션을 확인합니다. Deployment·StatefulSet rollout, 직접 kubectl delete pod, 일부 cloud desired-capacity 변경은 같은 PDB admission을 사용하지 않습니다. Cordon만으로 기존 Pod가 퇴거되지 않습니다. PDB가 hardware 장애·kernel panic·OOM을 막지는 못합니다.


</details>

### 3. 유용한 chaos 실험을 위한 네 가지 제어를 설명하세요.

<details>
<summary>정답 보기</summary>

측정 가능한 정상 상태 가설, 실제적인 제한된 fault, 대표 환경과 필요 시 명시적 production 권한, 독립 관찰·중단 threshold·복구 책임자를 통한 영향 범위 제한입니다. 자동화·사후 분석은 반복성을 돕지만 production 실험이 필수라거나 data가 자동 복원된다는 뜻은 아닙니다.


</details>

### 4. 이 workload 예시가 세 AZ를 사용하는 이유와 EKS node-group 최소 요구 여부는?

<details>
<summary>정답 보기</summary>

동일 용량 세 zone에 workload·의존성까지 분산하면 한 zone 손실 후 기존 용량 2/3가 남는 설계입니다. 모든 node-group API의 최소 요구는 아닙니다. EKS cluster subnet은 최소 두 AZ, regional managed control plane은 세 AZ이며 고객 node-group AZ가 managed etcd 배치를 정하지 않습니다. Region·instance type·storage·workload 조건에 맞는 zone을 선택합니다.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: owned-ha-example
  region: us-west-2
  version: '1.36'
managedNodeGroups:
- name: ng-multi-az
  instanceType: m5.large
  desiredCapacity: 6
  availabilityZones:
  - us-west-2a
  - us-west-2b
  - us-west-2c
```

</details>

### 5. Routing layer는 traffic을 cell에 어떻게 할당해야 하나요?

<details>
<summary>정답 보기</summary>

신뢰하는 tenant identity와 안정적 hash·명시적 mapping·지역 할당을 사용합니다. Router는 authorization·용량·data 위치를 검증해야 하며 임의 client x-cell-id를 tenant 권한으로 믿지 않습니다. 아래 mesh는 등록된 destination Service·정책을 전제합니다. 알 수 없거나 신뢰하지 않는 cell ID는 거부·기본 처리 정책이 필요합니다. Namespace·ConfigMap만으로 격리·failover를 구현하지는 못합니다.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: cell-routing-example
  namespace: resilience-demo
spec:
  hosts:
  - cell-router.resilience-demo.svc.cluster.local
  http:
  - match:
    - headers:
        x-cell-id:
          exact: cell-a
    route:
    - destination:
        host: app.cell-a.svc.cluster.local
  - match:
    - headers:
        x-cell-id:
          exact: cell-b
    route:
    - destination:
        host: app.cell-b.svc.cluster.local
```

</details>

## 실습 문제

### 1. app=api-server의 PDB를 고려한 eviction 이후 가용 replica 세 개를 요구하는 api-server-pdb를 작성하세요.

<details>
<summary>정답 보기</summary>

고객 앱 label이며 AWS가 관리하는 Kubernetes API server를 설정하는 것이 아닙니다. Namespace·일치하는 controller workload가 존재해야 합니다. Ready 5개·진행 중 disruption 없음이면 허용 2개라는 예시이며 replica 3개면 정상 eviction 여유가 없습니다. 기존 출력이 실측이라고 가정하지 말고 실제 status를 확인합니다.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-server-pdb
  namespace: resilience-demo
spec:
  minAvailable: 3
  selector:
    matchLabels:
      app: api-server
```
```bash
# Prerequisite: the owned test namespace and matching application already exist.
: "${KUBE_CONTEXT:?Set the owned test context}"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pods -l app=api-server
# MUTATION: apply only this reviewed PDB file.
kubectl --context "$KUBE_CONTEXT" -n resilience-demo apply -f api-server-pdb.yaml
kubectl --context "$KUBE_CONTEXT" -n resilience-demo describe pdb api-server-pdb
```

</details>

### 2. Replica 여섯 개와 zone spread rule의 web-frontend를 작성하고 AZ 손실 시 trade-off를 설명하세요.

<details>
<summary>정답 보기</summary>

완전한 예시는 N-1 상황에 maxSkew=1·minDomains=2를 사용합니다. 초기 3-zone 배치·잔여 용량은 별도 검증하며 자동 재배치·zonal PVC 이동을 하지 않습니다. 앱 placeholder image·health path를 바꾸고 resource를 조정합니다. 통제한 적용 후 모든 Pod에 node·zone label이 있다고 가정하지 말고 아래 Python 보고를 사용합니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
  namespace: resilience-demo
spec:
  replicas: 6
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: app
        image: registry.example.com/team/web-app:replace-with-reviewed-digest
        ports:
        - name: http
          containerPort: 8080
        startupProbe:
          httpGet:
            path: /healthz
            port: http
          failureThreshold: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        lifecycle:
          preStop:
            sleep:
              seconds: 5
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-frontend
```
```bash
# MUTATION: replace the image/health contract and review this exact file first.
: "${KUBE_CONTEXT:?Set the owned test context}"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo apply -f web-frontend.yaml
kubectl --context "$KUBE_CONTEXT" -n resilience-demo rollout status deployment/web-frontend --timeout=5m
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pods -l app=web-frontend -o json > frontend-pods.json
kubectl --context "$KUBE_CONTEXT" get nodes -o json > frontend-nodes.json
```
```python
import collections, json
from pathlib import Path
pods = json.loads(Path("frontend-pods.json").read_text())["items"]
nodes = json.loads(Path("frontend-nodes.json").read_text())["items"]
zones = {n["metadata"]["name"]: n["metadata"].get("labels", {}).get("topology.kubernetes.io/zone", "<unlabeled>") for n in nodes}
counts, ready = collections.Counter(), collections.Counter()
for pod in pods:
    if pod["metadata"].get("deletionTimestamp"):
        continue
    node = pod.get("spec", {}).get("nodeName")
    zone = zones.get(node, "<unknown-node>") if node else "<unscheduled>"
    counts[zone] += 1
    if any(c.get("type") == "Ready" and c.get("status") == "True" for c in pod.get("status", {}).get("conditions", [])):
        ready[zone] += 1
print(json.dumps({"activePodsByZone": dict(counts), "readyPodsByZone": dict(ready)}, indent=2))
```

</details>

### 3. 검토한 test Pod 한 개로 제한한 30초 Litmus Pod 삭제 실험을 중지 상태로 준비하세요.

<details>
<summary>정답 보기</summary>

전체 production selector가 아닌 resilience-demo의 소유 payment-service test workload를 사용합니다. UID·owner 확인 후 TARGET_PODS를 현재 정확한 이름으로 바꿉니다. Operator·pod-delete ChaosExperiment·검증한 runner/helper image·제한한 RBAC가 준비되어야 합니다. Duration·interval은 반복 삭제 시도를 만들 수 있으므로 30초 동안 정확히 한 번 삭제한다는 증명이 아닙니다. 한 번의 선택한 삭제 action이 필요하면 본문의 FIS COUNT(1)과 별도 IAM·RBAC 전제를 사용합니다. 여기서는 fault를 실행하지 않습니다.

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: payment-pod-delete-review
  namespace: resilience-demo
spec:
  engineState: stop
  appinfo:
    appns: resilience-demo
    applabel: app=payment-service,experiment-approved=true
    appkind: deployment
  chaosServiceAccount: pod-delete-sa
  experiments:
  - name: pod-delete
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: '30'
        - name: CHAOS_INTERVAL
          value: '10'
        - name: FORCE
          value: 'false'
        - name: TARGET_PODS
          value: REPLACE_WITH_ONE_REVIEWED_POD_NAME
        - name: PODS_AFFECTED_PERC
          value: '100'
```
```bash
# Read-only: resolve an exact current Pod name/UID before filling TARGET_PODS.
: "${KUBE_CONTEXT:?Set the owned test context}"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pods \
  -l 'app=payment-service,experiment-approved=true' -o wide
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get chaosexperiment pod-delete
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get serviceaccount pod-delete-sa
# MUTATION: this reviewed file must still have engineState: stop.
kubectl --context "$KUBE_CONTEXT" -n resilience-demo apply -f payment-pod-delete-review.yaml
```
```bash
# Read-only observation; no experiment is started by these commands.
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get chaosengine payment-pod-delete-review -o yaml
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get chaosresult
```

</details>

## 심화 문제

### 1. 99.99% 가용성 SLO를 목표로 하는 금융 서비스 workload를 설계하고 검증할 항목을 설명하세요.

<details>
<summary>정답 보기</summary>

99.99%는 다음 resource만으로 보장되는 수치가 아닌 workload SLO입니다. 365일의 시간 기반 산술 budget은 연 52.56분이며 기존 “약 52분”은 근삿값입니다. EKS SLA는 별도의 월 service-credit 약정이고 요청 기반 가용성은 분모도 다릅니다. 핵심 사용자 흐름·부분 장애·측정 기간·RTO/RPO·alert를 정의합니다.

Primary·secondary region의 data·identity·DNS·routing·관측·용량을 독립적으로 사용할 수 있게 준비합니다. 복제 지연·write 승격·충돌·복구 책임자를 검증하며 Multi-AZ·Active-Active만으로 무손실이 보장되지 않습니다. 아래 기존 규모 수치는 실측 용량·실행 배포가 아닌 설계 예시입니다.

#### Multi-AZ node input and cell resources

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: finance-primary-example
  region: us-west-2
  version: '1.36'
managedNodeGroups:
- name: ng-critical
  instanceType: m5.xlarge
  desiredCapacity: 9
  availabilityZones:
  - us-west-2a
  - us-west-2b
  - us-west-2c
  labels:
    criticality: high
```
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: finance-cell
  labels:
    cell: finance
```
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: cell-quota
  namespace: finance-cell
spec:
  hard:
    requests.cpu: '100'
    requests.memory: 200Gi
    limits.cpu: '200'
    limits.memory: 400Gi
```
Quota가 node를 예약하거나 공유 의존성을 격리하지는 않습니다. 본문의 router·network-policy·data 경계를 추가 검토합니다. 아래 strict hostname anti-affinity의 replica 9개에는 criticality=high인 eligible node 9개가 필요하며 30개 확장에도 그에 맞는 용량이 필요합니다. Strict 조건은 의도적으로 Pending을 만들 수 있습니다. Placeholder image·health contract·region/version/instance 가용성을 먼저 확인합니다.

#### Placement and eviction budget

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-api
  namespace: finance-cell
spec:
  replicas: 9
  selector:
    matchLabels:
      app: payment-api
  template:
    metadata:
      labels:
        app: payment-api
        tier: critical
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: app
        image: registry.example.com/team/web-app:replace-with-reviewed-digest
        ports:
        - name: http
          containerPort: 8080
        startupProbe:
          httpGet:
            path: /healthz
            port: http
          failureThreshold: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        lifecycle:
          preStop:
            sleep:
              seconds: 5
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: payment-api
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: payment-api
      nodeSelector:
        criticality: high
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: payment-api
            topologyKey: kubernetes.io/hostname
```
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: critical-service-pdb
  namespace: finance-cell
spec:
  minAvailable: 80%
  selector:
    matchLabels:
      app: payment-api
```
정상 replica 9개의 minAvailable 80%는 올림해 8개이며 다른 차감 전 명목상 정상 eviction 여유는 1개입니다. 모든 rollout·cloud scale-down·AZ 장애를 제한하지 않습니다. minDomains=2는 설명한 N-1 계산을 지원하며 자동 evacuation·data migration이 아닙니다.

#### HPA with an actual target and metric contract

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: critical-service-hpa
  namespace: finance-cell
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: payment-api
  minReplicas: 9
  maxReplicas: 30
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
```
CPU resource metric에는 정상 Metrics Server와 관련 container CPU request가 필요합니다. Replica 증가가 memory leak·DB 포화·zonal volume 제약을 해결하지는 않습니다. Replica field·GitOps·HPA 소유권을 일치시킵니다.

정기 game day는 소유 scheduler·승인한 workflow로 검토한 개별 실험을 호출하고 정확한 target·ID·abort 신호·다음 실험 전 복구를 기록합니다. 기존 2024 ChaosSchedule은 기간이 만료되었고 Litmus 3.31.0 CRD에도 없으므로 날짜만 바꿔 해결할 수 없습니다. 99.99% 주장은 주간 schedule이 아니라 실제 SLI·훈련 근거가 필요합니다.

</details>

### 2. 10배 Black Friday traffic 시나리오의 사전 확장과 제한된 장애 복구를 설계하세요.

<details>
<summary>정답 보기</summary>

10배는 실측 결과가 아닌 test 목표입니다. Request mix·CPU/memory·warm-up·연결·queue·DB·외부 service quota를 모델링하고 목표 traffic 중 한 AZ 손실까지 계산합니다. NodePool limit는 **사전 생성·예약 용량이 아닌 provisioning 상한**입니다. 기존 EC2NodeClass·AMI/IAM·subnet/IP·instance type이 설계를 지원해야 합니다. 자발적 disruption budget 0도 interruption·repair·모든 강제 종료를 막지 않습니다.

#### Capacity settings to validate

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: blackfriday-example
spec:
  template:
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: reviewed-test-class
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - m5.2xlarge
        - m5.4xlarge
        - c5.2xlarge
        - c5.4xlarge
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - us-west-2a
        - us-west-2b
        - us-west-2c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
  limits:
    cpu: 2000
    memory: 4000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
    budgets:
    - nodes: '0'
```
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: product-catalog-hpa
  namespace: resilience-demo
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: product-catalog
  minReplicas: 50
  maxReplicas: 500
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
  behavior:
    scaleDown:
      selectPolicy: Disabled
```
기존 평시 10→minimum 50/max 500은 예시이며 replica floor 5배가 처리량 10배를 증명하지 않습니다. HPA는 CPU request·정상 metric이 있는 기존 product-catalog Deployment를 전제합니다. ScaleDown 비활성화는 HPA scale-in을 막고 scale-up은 허용하며 전체 HPA 정지가 아닙니다. 행사 전 Ready Pod·건강한 endpoint·실제 확보한 node/headroom을 확인하고 이후 검토한 평시 policy로 복원합니다.

행사 전 대표 test load에서 본문의 검토한 개별 실험을 수행합니다. 제한된 Pod fault, 통제한 zonal shift·network 시나리오, 의존성 지연을 구분합니다. Node-drain을 AZ 전체 장애라 하지 않고 TARGET_PODS에 label selector를 넣거나 미검토 fault를 하나의 active production engine에 합치지 않습니다. 실패·no-data·실제 복원을 포함해 기록합니다.

#### Scenario response plan

| 상황 | 근거 | 검토할 대응 |
| --- | --- | --- |
| AZ 장애 | Endpoint·고객 health·node·data 가용성 | 지원 ARC·수동 shift와 검증한 잔여 용량; topology spread만으로 Pod를 evacuation하지 않음 |
| DB 지연 | Query·connection·복제 metric | Retry·동시성 제한, 필요 시 writer 승격 runbook; 임의 read replica로 전환하지 않음 |
| OOM·memory 증가 | Limit·working set·restart·앱 근거 | Resource·앱 원인 수정; CPU HPA가 자동 OOM 복구는 아님 |
| Traffic 급증 | Request mix·backlog·포화·고객 오류 | Admission·rate limit·검증한 확장; public·개인화 의미가 안전한 data만 cache |

#### Circuit breaker and metrics

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: product-catalog-circuit-breaker
  namespace: resilience-demo
spec:
  host: product-catalog.resilience-demo.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 3s
      http:
        http1MaxPendingRequests: 1000
        http2MaxRequests: 2000
        maxRequestsPerConnection: 10
        maxRetries: 3
    outlierDetection:
      consecutive5xxErrors: 5
      consecutiveGatewayErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 30
      splitExternalLocalOriginErrors: true
```
Proxy pool 제한·outlier detection이 backend 용량을 예약하지는 않습니다. 본문의 timeout·idempotency 원칙으로 조정합니다. 아래 query는 명시한 counter·classic histogram·job/namespace/status label을 제공하는 **앱 instrumentation**과 kube-state-metrics가 필요하며 EKS가 자동 제공하지 않습니다. 관련 status series를 초기화하고 scrape 범위를 확인합니다. 분모 0·sample 없음은 가용성 100%가 아닌 근거 없음입니다. Pod 지표는 완료·삭제 중 Pod를 제외하지만 앱 SLI가 아닙니다.

Request rate

```promql
sum(rate(http_requests_total{job="product-catalog",namespace="resilience-demo"}[5m]))
```

5xx percentage

```promql
100 * sum(rate(http_requests_total{job="product-catalog",namespace="resilience-demo",status=~"5.."}[5m]))
/ sum(rate(http_requests_total{job="product-catalog",namespace="resilience-demo"}[5m]))
and on() (sum(rate(http_requests_total{job="product-catalog",namespace="resilience-demo"}[5m])) > 0)
```

Classic-histogram p99 seconds

```promql
histogram_quantile(0.99,
  sum by (le) (rate(http_request_duration_seconds_bucket{job="product-catalog",namespace="resilience-demo"}[5m]))
)
```

Active test-namespace Ready Pod percentage, not request availability

```promql
100 *
sum(
  kube_pod_status_ready{namespace="resilience-demo",condition="true"}
  and on (namespace,pod)
  (kube_pod_status_phase{namespace="resilience-demo",phase=~"Pending|Running|Unknown"} == 1)
  unless on (namespace,pod) kube_pod_deletion_timestamp{namespace="resilience-demo"}
)
/
count(
  (kube_pod_status_phase{namespace="resilience-demo",phase=~"Pending|Running|Unknown"} == 1)
  unless on (namespace,pod) kube_pod_deletion_timestamp{namespace="resilience-demo"}
)
```

#### Workload rollback and separately reviewed controls

```bash
# MUTATION: workload revision rollback only, after data/schema and GitOps review.
set -euo pipefail
: "${KUBE_CONTEXT:?Set the verified owned context}"
: "${REVIEWED_REVISION:?Set an inspected compatible Deployment revision}"
[[ "$REVIEWED_REVISION" =~ ^[1-9][0-9]*$ ]]
kubectl --context "$KUBE_CONTEXT" -n resilience-demo rollout history deployment/product-catalog
kubectl --context "$KUBE_CONTEXT" -n resilience-demo rollout undo deployment/product-catalog \
  --to-revision="$REVIEWED_REVISION"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo rollout status deployment/product-catalog --timeout=5m
```
Rollback 전 GitOps·HPA 소유권을 조정합니다. Rollout undo는 DB·PVC rollback이나 EKS control-plane downgrade가 아닙니다. minReplicas를 100으로 올려도 HPA는 정지하지 않습니다. 필요하면 HPA behavior와 기록한 복원 계획을 사용합니다. Feature flag는 실제 인증된 관리 API/SDK·검토한 대상 flag를 사용하며 범용 무인증 disable URL을 가정하지 않습니다.

CloudFront는 기존 전체 configuration과 ETag를 비공개 파일로 먼저 가져옵니다.

```bash
# Read-only preparation; output can include sensitive origin configuration.
set -euo pipefail
umask 077
: "${CF_DIST_ID:?Set the exact owned CloudFront distribution ID}"
test ! -e cloudfront-current-private.json
aws cloudfront get-distribution-config --id "$CF_DIST_ID" > cloudfront-current-private.json
```
Cache policy·cookie·authorization·개인화 content를 검토합니다. 변경에는 유효한 전체 DistributionConfig와 일치하는 IfMatch ETag가 필요하며 update-distribution에 --default-cache-behavior shortcut은 없습니다. 전체 설정을 별도로 준비·검토하고 배포 완료·복원 계획을 확인합니다. 거래·사용자별 응답에 일괄 24시간 TTL을 적용하지 않습니다.

기존 D-14 기본 test, D-7 game day, D-3 최종 검증·사전 확장, D-Day 관찰 일정은 계획 예시로 보존하며 여기서 runtime 결과는 검증하지 않았습니다.

[CloudFront update API](https://docs.aws.amazon.com/cli/latest/reference/cloudfront/update-distribution.html) · [HPA behavior](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/) · [kube-state-metrics Pod metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md)

</details>

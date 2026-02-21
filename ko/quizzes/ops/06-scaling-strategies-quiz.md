# 스케일링 전략 퀴즈

> **관련 문서**: [스케일링 전략](../../ops/06-scaling-strategies.md)

## 객관식 문제

### 1. HPA(Horizontal Pod Autoscaler)에서 Custom Metrics를 사용하려면 어떤 컴포넌트가 필요한가요?

- A) Vertical Pod Autoscaler
- B) Prometheus Adapter 또는 KEDA
- C) Cluster Autoscaler만
- D) Ingress Controller

<details>
<summary>정답 보기</summary>

**정답: B) Prometheus Adapter 또는 KEDA**

**설명:**
HPA가 CPU/메모리 외의 Custom Metrics를 사용하려면 custom.metrics.k8s.io API를 제공하는 어댑터가 필요합니다. Prometheus Adapter는 Prometheus 메트릭을 Kubernetes Metrics API로 변환하고, KEDA는 더 다양한 외부 소스(SQS, Kafka, Redis 등)를 지원합니다.

</details>

### 2. KEDA ScaledObject에서 pollingInterval의 역할은 무엇인가요?

- A) Pod 삭제 대기 시간
- B) 외부 메트릭 소스를 확인하는 주기
- C) HPA 동기화 주기
- D) 스케일 다운 안정화 시간

<details>
<summary>정답 보기</summary>

**정답: B) 외부 메트릭 소스를 확인하는 주기**

**설명:**
pollingInterval은 KEDA가 외부 메트릭 소스(SQS 큐 길이, Kafka 컨슈머 랙 등)를 확인하는 주기를 초 단위로 지정합니다. 기본값은 30초이며, 더 빠른 반응이 필요하면 값을 줄일 수 있지만 외부 API 호출 비용이 증가할 수 있습니다.

</details>

### 3. VPA(Vertical Pod Autoscaler)의 updateMode: "Off" 설정의 의미는 무엇인가요?

- A) VPA 완전 비활성화
- B) 권장 값만 계산하고 실제 적용은 하지 않음
- C) 즉시 Pod 재시작하여 적용
- D) 새 Pod에만 적용

<details>
<summary>정답 보기</summary>

**정답: B) 권장 값만 계산하고 실제 적용은 하지 않음**

**설명:**
updateMode: "Off"는 VPA가 리소스 사용 패턴을 분석하여 권장 requests/limits 값을 계산하지만, 실제로 Pod에 적용하지는 않습니다. 이 모드는 현재 설정이 적절한지 확인하거나, 권장 값을 수동으로 검토한 후 적용할 때 유용합니다.

</details>

### 4. KEDA의 cooldownPeriod 설정의 역할은 무엇인가요?

- A) 스케일 업 대기 시간
- B) 마지막 트리거 활성화 후 0으로 스케일 다운까지의 대기 시간
- C) 메트릭 수집 간격
- D) Pod 시작 대기 시간

<details>
<summary>정답 보기</summary>

**정답: B) 마지막 트리거 활성화 후 0으로 스케일 다운까지의 대기 시간**

**설명:**
cooldownPeriod는 모든 트리거가 비활성화된 후 KEDA가 워크로드를 0으로 스케일 다운하기까지 대기하는 시간(초)입니다. 이를 통해 일시적인 트래픽 감소로 인한 불필요한 스케일 다운을 방지하고, 다시 트래픽이 증가할 때 빠르게 대응할 수 있습니다.

</details>

### 5. HPA와 VPA를 함께 사용할 때 주의해야 할 점은 무엇인가요?

- A) 동일한 메트릭에 대해 둘 다 설정하면 충돌 가능
- B) VPA가 항상 우선
- C) HPA가 항상 우선
- D) 함께 사용 불가

<details>
<summary>정답 보기</summary>

**정답: A) 동일한 메트릭에 대해 둘 다 설정하면 충돌 가능**

**설명:**
HPA와 VPA를 CPU/메모리에 대해 동시에 설정하면 서로 충돌할 수 있습니다. VPA가 requests를 변경하면 HPA의 스케일링 결정에 영향을 주고, 이로 인해 예상치 못한 동작이 발생할 수 있습니다. 일반적으로 HPA는 RPS 같은 Custom Metrics에, VPA는 리소스 권장에 사용하는 것이 좋습니다.

</details>

### 6. Kubernetes 1.27+에서 지원되는 In-Place Pod Vertical Scaling의 장점은 무엇인가요?

- A) 더 많은 메트릭 지원
- B) Pod 재시작 없이 리소스 변경 가능
- C) 자동 롤백 지원
- D) 멀티 클러스터 지원

<details>
<summary>정답 보기</summary>

**정답: B) Pod 재시작 없이 리소스 변경 가능**

**설명:**
In-Place Pod Vertical Scaling(KEP-1287)은 Pod를 재시작하지 않고도 CPU/메모리 requests와 limits를 변경할 수 있게 합니다. 기존 VPA는 리소스 변경 시 Pod를 재생성해야 했지만, 이 기능을 사용하면 서비스 중단 없이 리소스를 조정할 수 있습니다.

</details>

### 7. KEDA에서 minReplicaCount: 0 설정의 의미는 무엇인가요?

- A) 최소 1개 Pod 유지
- B) 이벤트가 없으면 Pod를 0개로 스케일 다운 (scale-to-zero)
- C) 스케일링 비활성화
- D) 무제한 스케일링

<details>
<summary>정답 보기</summary>

**정답: B) 이벤트가 없으면 Pod를 0개로 스케일 다운 (scale-to-zero)**

**설명:**
KEDA의 핵심 기능 중 하나는 scale-to-zero입니다. minReplicaCount: 0으로 설정하면 트리거 조건이 충족되지 않을 때(예: SQS 큐가 비어있을 때) Pod를 0개로 줄여 리소스를 절약합니다. 이벤트가 발생하면 KEDA가 빠르게 Pod를 생성합니다.

</details>

### 8. HPA의 behavior.scaleDown.stabilizationWindowSeconds 설정의 역할은 무엇인가요?

- A) 스케일 업 속도 제한
- B) 지정된 시간 동안 가장 높은 권장 값을 사용하여 급격한 스케일 다운 방지
- C) Pod 시작 대기 시간
- D) 메트릭 수집 간격

<details>
<summary>정답 보기</summary>

**정답: B) 지정된 시간 동안 가장 높은 권장 값을 사용하여 급격한 스케일 다운 방지**

**설명:**
stabilizationWindowSeconds는 HPA가 스케일 다운 결정 시 지정된 시간 동안의 권장 값 중 가장 높은 값을 사용하도록 합니다. 이를 통해 트래픽 급감 후 빠른 회복 시 Pod 부족 상황을 방지하고, 안정적인 스케일링을 유지합니다.

</details>

### 9. Pod Deletion Cost 어노테이션의 용도는 무엇인가요?

- A) Pod 생성 비용 계산
- B) 스케일 다운 시 어떤 Pod를 먼저 삭제할지 우선순위 지정
- C) 클라우드 비용 추적
- D) 리소스 할당량 설정

<details>
<summary>정답 보기</summary>

**정답: B) 스케일 다운 시 어떤 Pod를 먼저 삭제할지 우선순위 지정**

**설명:**
`controller.kubernetes.io/pod-deletion-cost` 어노테이션은 스케일 다운 시 Pod 삭제 우선순위를 지정합니다. 값이 낮은 Pod가 먼저 삭제됩니다. 예를 들어, 중요한 작업을 처리 중인 Pod에 높은 값을 설정하여 먼저 삭제되지 않도록 보호할 수 있습니다.

</details>

### 10. KEDA의 ScaledJob과 ScaledObject의 차이점은 무엇인가요?

- A) 동일한 기능
- B) ScaledJob은 Job 워크로드용, ScaledObject는 Deployment/StatefulSet용
- C) ScaledJob만 scale-to-zero 지원
- D) ScaledObject만 Custom Metrics 지원

<details>
<summary>정답 보기</summary>

**정답: B) ScaledJob은 Job 워크로드용, ScaledObject는 Deployment/StatefulSet용**

**설명:**
ScaledObject는 Deployment, StatefulSet 같은 장기 실행 워크로드의 스케일링에 사용됩니다. ScaledJob은 Kubernetes Job을 이벤트에 따라 동적으로 생성하는 데 사용됩니다. 예를 들어, SQS 메시지마다 Job을 생성하여 배치 처리를 수행할 수 있습니다.

</details>

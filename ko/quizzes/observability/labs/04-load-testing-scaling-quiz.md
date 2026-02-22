# Observability 실습 Part 4: 부하 테스트 및 스케일링 퀴즈

> **마지막 업데이트**: 2025년 2월

이 퀴즈는 Observability 실습 Part 4의 부하 테스트 및 자동 스케일링에 대한 이해도를 테스트합니다.

---

1. k6 부하 테스트에서 VU(Virtual User)의 개념으로 올바른 것은?
   - A) 실제 사용자 수를 의미한다
   - B) 동시에 스크립트를 실행하는 가상 사용자로, 각 VU는 독립적인 JavaScript 런타임에서 실행된다
   - C) CPU 코어 수를 의미한다
   - D) 초당 요청 수(RPS)와 동일하다
<details>
<summary>정답 보기</summary>

**정답: B) 동시에 스크립트를 실행하는 가상 사용자로, 각 VU는 독립적인 JavaScript 런타임에서 실행된다**

**설명:**
k6의 VU(Virtual User)는 테스트 스크립트를 병렬로 실행하는 가상 사용자입니다. 각 VU는 독립적인 JavaScript 런타임과 상태를 가지며, 스크립트의 default function을 반복 실행합니다. VU 수와 duration/iterations를 조합하여 부하 패턴을 정의합니다. RPS는 VU 수, 스크립트 실행 시간, 응답 시간에 따라 결정됩니다.

</details>

---

2. k6와 Locust 부하 테스트 도구의 주요 차이점으로 올바른 것은?
   - A) k6는 Python으로, Locust는 JavaScript로 스크립트를 작성한다
   - B) k6는 JavaScript/TypeScript로 스크립트를 작성하고 Go 기반이며, Locust는 Python으로 스크립트를 작성하고 Python 기반이다
   - C) Locust만 분산 테스트를 지원한다
   - D) k6는 웹 UI를 제공하지 않는다
<details>
<summary>정답 보기</summary>

**정답: B) k6는 JavaScript/TypeScript로 스크립트를 작성하고 Go 기반이며, Locust는 Python으로 스크립트를 작성하고 Python 기반이다**

**설명:**
k6는 Go로 작성되어 높은 성능을 제공하고, JavaScript/TypeScript로 테스트 스크립트를 작성합니다. Locust는 Python 기반으로 Python 코드로 테스트를 정의합니다. 두 도구 모두 분산 테스트를 지원하며, k6는 CLI 중심이고 Locust는 웹 UI를 기본 제공합니다. k6는 특히 CI/CD 파이프라인 통합과 클라우드 실행에 강점이 있습니다.

</details>

---

3. KEDA의 SQS 스케일러가 Pod를 스케일링하는 메커니즘으로 올바른 것은?
   - A) SQS API를 직접 호출하여 메시지를 처리한다
   - B) SQS 대기열 메트릭을 주기적으로 폴링하고, 설정된 임계값에 따라 Deployment의 replica 수를 조정한다
   - C) Pod 내부에서 SQS 클라이언트를 실행한다
   - D) AWS Lambda를 트리거한다
<details>
<summary>정답 보기</summary>

**정답: B) SQS 대기열 메트릭을 주기적으로 폴링하고, 설정된 임계값에 따라 Deployment의 replica 수를 조정한다**

**설명:**
KEDA의 SQS 스케일러는 AWS API를 통해 SQS 대기열의 메트릭(ApproximateNumberOfMessages 등)을 주기적으로 조회합니다. ScaledObject에 정의된 queueLength(Pod당 처리할 메시지 수)와 현재 대기열 깊이를 비교하여 필요한 Pod 수를 계산하고, HPA를 통해 Deployment replica를 자동 조정합니다.

</details>

---

4. KEDA의 Prometheus 스케일러에서 사용하는 메트릭 쿼리 방식은?
   - A) Prometheus에 직접 접속할 수 없다
   - B) PromQL 쿼리를 실행하여 반환된 값을 스케일링 메트릭으로 사용한다
   - C) Prometheus Alertmanager의 알림을 트리거로 사용한다
   - D) Prometheus Push Gateway에만 연결한다
<details>
<summary>정답 보기</summary>

**정답: B) PromQL 쿼리를 실행하여 반환된 값을 스케일링 메트릭으로 사용한다**

**설명:**
KEDA Prometheus 스케일러는 지정된 Prometheus 서버에 PromQL 쿼리를 실행하고, 반환된 스칼라 값을 스케일링 결정에 사용합니다. 예를 들어 `sum(rate(http_requests_total[1m]))`의 결과가 임계값을 초과하면 Pod를 스케일 아웃합니다. 이를 통해 애플리케이션 특정 메트릭(요청률, 대기열 깊이 등)에 기반한 세밀한 스케일링이 가능합니다.

</details>

---

5. Karpenter가 Pending Pod를 감지하고 노드를 프로비저닝하는 과정으로 올바른 것은?
   - A) HPA가 Karpenter에게 직접 노드 생성을 요청한다
   - B) Karpenter 컨트롤러가 Pending Pod를 감지하고, NodePool 제약 조건에 맞는 최적의 인스턴스 타입을 선택하여 EC2 인스턴스를 프로비저닝한다
   - C) AWS Auto Scaling Group이 노드를 생성한다
   - D) 사용자가 수동으로 노드를 추가해야 한다
<details>
<summary>정답 보기</summary>

**정답: B) Karpenter 컨트롤러가 Pending Pod를 감지하고, NodePool 제약 조건에 맞는 최적의 인스턴스 타입을 선택하여 EC2 인스턴스를 프로비저닝한다**

**설명:**
Karpenter는 Kubernetes 스케줄러가 노드 부족으로 스케줄링하지 못한 Pending Pod를 모니터링합니다. Pending Pod의 리소스 요청, nodeSelector, tolerations 등을 분석하고, NodePool에 정의된 인스턴스 타입, 가용 영역 등의 제약 조건 내에서 비용 효율적인 인스턴스를 선택하여 빠르게 프로비저닝합니다. Cluster Autoscaler와 달리 ASG에 의존하지 않아 더 빠르고 유연합니다.

</details>

---

6. Karpenter의 Consolidation 정책에서 empty node 제거와 비용 최적화의 동작 방식은?
   - A) 사용자가 수동으로 빈 노드를 삭제해야 한다
   - B) Pod가 없는 노드나 다른 노드로 Pod를 이동시켜 비용을 절감할 수 있는 노드를 자동으로 종료한다
   - C) 모든 노드를 주기적으로 재시작한다
   - D) Consolidation은 노드 추가만 담당한다
<details>
<summary>정답 보기</summary>

**정답: B) Pod가 없는 노드나 다른 노드로 Pod를 이동시켜 비용을 절감할 수 있는 노드를 자동으로 종료한다**

**설명:**
Karpenter Consolidation은 두 가지 방식으로 비용을 최적화합니다. Empty node 제거는 Pod가 없는 노드를 감지하여 종료합니다. Replace 방식은 여러 노드의 Pod를 더 적은 수의 노드로 통합(bin-packing)하거나, 더 저렴한 인스턴스 타입으로 교체할 수 있는지 평가하고 실행합니다. 이를 통해 부하 감소 후 불필요한 노드를 자동으로 제거하여 비용을 절감합니다.

</details>

---

7. 부하 테스트 중 Grafana에서 관찰해야 할 핵심 RED 메트릭의 구성 요소는?
   - A) RAM, Encryption, Disk
   - B) Rate(요청률), Errors(에러율), Duration(지연 시간)
   - C) Read, Execute, Delete
   - D) Replicas, Events, Deployments
<details>
<summary>정답 보기</summary>

**정답: B) Rate(요청률), Errors(에러율), Duration(지연 시간)**

**설명:**
RED 메트릭은 마이크로서비스 모니터링의 핵심 지표입니다. Rate는 초당 요청 수로 서비스 부하를 나타냅니다. Errors는 실패한 요청의 비율로 서비스 건강 상태를 나타냅니다. Duration은 요청 처리 시간(보통 p50, p95, p99 백분위수)으로 사용자 경험을 나타냅니다. 부하 테스트 중 이 세 가지 메트릭의 변화를 모니터링하여 시스템의 한계점과 성능 특성을 파악합니다.

</details>

---

8. `kube_deployment_status_replicas` 메트릭으로 Pod 수 변화를 추적하는 방법은?
   - A) 이 메트릭은 Pod 수와 관련이 없다
   - B) Deployment별 현재 replica 수를 시계열로 조회하여 스케일링 이벤트를 시각화한다
   - C) 이 메트릭은 CPU 사용량을 나타낸다
   - D) kube-state-metrics 없이 사용할 수 있다
<details>
<summary>정답 보기</summary>

**정답: B) Deployment별 현재 replica 수를 시계열로 조회하여 스케일링 이벤트를 시각화한다**

**설명:**
`kube_deployment_status_replicas`는 kube-state-metrics가 노출하는 메트릭으로, Deployment의 현재 replica 수를 나타냅니다. 이 메트릭을 시계열 그래프로 시각화하면 HPA나 KEDA에 의한 스케일링 이벤트를 확인할 수 있습니다. `kube_deployment_spec_replicas`(원하는 replica 수)와 비교하면 스케일링 지연도 파악할 수 있습니다.

</details>

---

9. KEDA에서 스케일 다운 시 stabilizationWindowSeconds의 역할은?
   - A) Pod 시작 시간을 지연시킨다
   - B) 스케일 다운 결정 전 지정된 시간 동안 메트릭이 안정적으로 낮은지 확인하여 급격한 스케일 다운을 방지한다
   - C) 네트워크 지연을 설정한다
   - D) 로그 보존 기간을 설정한다
<details>
<summary>정답 보기</summary>

**정답: B) 스케일 다운 결정 전 지정된 시간 동안 메트릭이 안정적으로 낮은지 확인하여 급격한 스케일 다운을 방지한다**

**설명:**
stabilizationWindowSeconds는 스케일 다운 안정화 기간입니다. 부하가 갑자기 줄어들었다가 다시 증가하는 경우, 즉시 스케일 다운하면 다시 스케일 업해야 하는 비효율이 발생합니다. 이 설정은 지정된 시간(예: 300초) 동안 스케일 다운 조건이 유지되는지 확인한 후에만 replica를 줄입니다. 이를 통해 부하 변동에 대한 과민 반응을 방지합니다.

</details>

---

10. SQS Queue Depth와 Pod 스케일링 간의 상관관계로 올바른 것은?
    - A) Queue Depth가 증가하면 Pod 수가 감소한다
    - B) Queue Depth가 증가하면 처리량을 높이기 위해 Pod 수가 증가하고, Queue Depth가 감소하면 Pod 수가 점진적으로 감소한다
    - C) Queue Depth는 Pod 스케일링과 관련이 없다
    - D) Pod 수가 고정되어 있으면 Queue Depth도 고정된다
<details>
<summary>정답 보기</summary>

**정답: B) Queue Depth가 증가하면 처리량을 높이기 위해 Pod 수가 증가하고, Queue Depth가 감소하면 Pod 수가 점진적으로 감소한다**

**설명:**
이벤트 기반 아키텍처에서 SQS Queue Depth는 처리 대기 중인 작업량을 나타냅니다. KEDA는 Queue Depth를 모니터링하여 메시지가 쌓이면 더 많은 worker Pod를 생성하여 처리 속도를 높입니다. 대기열이 비워지면 stabilizationWindow 후에 Pod를 점진적으로 줄여 비용을 절감합니다. queueLength 파라미터로 Pod당 목표 메시지 수를 설정하여 스케일링 민감도를 조정합니다.

</details>

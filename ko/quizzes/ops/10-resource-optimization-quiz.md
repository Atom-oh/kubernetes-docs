# 리소스 최적화 퀴즈

> **관련 문서**: [리소스 최적화](../../ops/10-resource-optimization.md)

## 객관식 문제

### 1. Kubernetes QoS 클래스 중 Guaranteed 클래스의 조건은 무엇인가요?

- A) requests만 설정
- B) limits만 설정
- C) requests와 limits가 동일하게 설정
- D) 아무 설정도 하지 않음

<details>
<summary>정답 보기</summary>

**정답: C) requests와 limits가 동일하게 설정**

**설명:**
Guaranteed QoS는 CPU와 메모리 모두 requests와 limits가 동일하게 설정된 경우 부여됩니다. 이 클래스의 Pod는 노드 리소스 부족 시 가장 나중에 eviction 대상이 되어 가장 안정적으로 실행됩니다. 중요한 워크로드에 권장됩니다.

</details>

### 2. JVM 애플리케이션에서 컨테이너 메모리에 맞게 힙 크기를 자동 조정하는 옵션은 무엇인가요?

- A) -Xmx 고정값 설정
- B) -XX:MaxRAMPercentage
- C) -XX:+UseSerialGC
- D) -Xms 고정값 설정

<details>
<summary>정답 보기</summary>

**정답: B) -XX:MaxRAMPercentage**

**설명:**
-XX:MaxRAMPercentage는 JVM이 컨테이너 메모리 limit의 지정된 비율만큼 힙을 할당하도록 합니다. 예: `-XX:MaxRAMPercentage=75.0`은 메모리 limit의 75%를 최대 힙으로 설정합니다. 이를 통해 컨테이너 크기가 변경되어도 자동으로 적절한 힙 크기가 설정됩니다.

</details>

### 3. CPU Throttling이 발생하는 주된 원인은 무엇인가요?

- A) 메모리 부족
- B) CPU requests 초과 사용
- C) CPU limits 도달로 인한 CFS 스케줄러 제한
- D) 디스크 I/O 병목

<details>
<summary>정답 보기</summary>

**정답: C) CPU limits 도달로 인한 CFS 스케줄러 제한**

**설명:**
CPU Throttling은 컨테이너가 설정된 CPU limit에 도달했을 때 Linux CFS(Completely Fair Scheduler)가 CPU 시간을 제한하여 발생합니다. Throttling이 발생하면 애플리케이션 지연이 증가합니다. limit 증가 또는 limit 제거를 고려할 수 있습니다.

</details>

### 4. Go 애플리케이션에서 컨테이너 CPU limit에 맞게 GOMAXPROCS를 자동 설정하는 방법은 무엇인가요?

- A) 환경변수 수동 설정
- B) go.uber.org/automaxprocs 라이브러리 사용
- C) runtime.GOMAXPROCS() 직접 호출
- D) Kubernetes annotation 사용

<details>
<summary>정답 보기</summary>

**정답: B) go.uber.org/automaxprocs 라이브러리 사용**

**설명:**
automaxprocs 라이브러리는 import만 하면 자동으로 컨테이너의 CPU limit을 감지하여 GOMAXPROCS를 설정합니다. `import _ "go.uber.org/automaxprocs"`를 추가하면 됩니다. 이를 통해 CPU limit이 1.5인 경우 GOMAXPROCS가 2로 설정되어 적절한 동시성을 유지합니다.

</details>

### 5. BestEffort QoS 클래스의 Pod는 언제 가장 먼저 eviction 대상이 되나요?

- A) CPU 사용량이 높을 때
- B) 노드의 메모리가 부족할 때
- C) 디스크가 부족할 때
- D) 네트워크 문제 발생 시

<details>
<summary>정답 보기</summary>

**정답: B) 노드의 메모리가 부족할 때**

**설명:**
BestEffort QoS(requests/limits 미설정)의 Pod는 노드에 메모리 압박이 발생하면 가장 먼저 eviction 대상이 됩니다. Guaranteed > Burstable > BestEffort 순서로 보호됩니다. 중요한 워크로드는 최소한 requests를 설정해야 합니다.

</details>

### 6. GOMEMLIMIT 환경변수의 역할은 무엇인가요?

- A) 최대 고루틴 수 제한
- B) Go 런타임의 메모리 사용량 제한 힌트 제공
- C) GC 비활성화
- D) 스택 크기 제한

<details>
<summary>정답 보기</summary>

**정답: B) Go 런타임의 메모리 사용량 제한 힌트 제공**

**설명:**
GOMEMLIMIT(Go 1.19+)은 Go 런타임에 메모리 사용량 목표를 알려줍니다. GC는 이 limit을 초과하지 않도록 더 적극적으로 수집합니다. 컨테이너 메모리 limit의 80-90% 정도로 설정하면 OOM을 방지하면서 메모리를 효율적으로 사용할 수 있습니다.

</details>

### 7. 컨테이너 리소스 설정에서 requests와 limits의 차이점은 무엇인가요?

- A) requests는 최대값, limits는 최소값
- B) requests는 스케줄링 기준, limits는 런타임 제한
- C) 둘은 동일한 역할
- D) requests만 강제 적용됨

<details>
<summary>정답 보기</summary>

**정답: B) requests는 스케줄링 기준, limits는 런타임 제한**

**설명:**
requests는 Pod가 스케줄링될 때 노드에 필요한 최소 리소스를 나타냅니다. limits는 Pod가 사용할 수 있는 최대 리소스입니다. 스케줄러는 requests 기준으로 노드를 선택하고, kubelet은 limits를 초과하지 않도록 제한합니다.

</details>

### 8. LimitRange 리소스의 주요 용도는 무엇인가요?

- A) 클러스터 전체 리소스 제한
- B) 네임스페이스 내 Pod/Container의 기본 리소스 설정 및 제한
- C) 노드 리소스 관리
- D) 네트워크 대역폭 제한

<details>
<summary>정답 보기</summary>

**정답: B) 네임스페이스 내 Pod/Container의 기본 리소스 설정 및 제한**

**설명:**
LimitRange는 네임스페이스 레벨에서 Pod/Container의 기본 requests/limits, 최소/최대 값, request-to-limit 비율 등을 설정합니다. 리소스 설정이 없는 Pod에 기본값을 적용하거나, 너무 큰 리소스 요청을 방지할 수 있습니다.

</details>

### 9. ResourceQuota와 LimitRange의 차이점은 무엇인가요?

- A) 동일한 기능
- B) ResourceQuota는 네임스페이스 총량 제한, LimitRange는 개별 Pod/Container 제한
- C) ResourceQuota만 CPU 제한 가능
- D) LimitRange만 메모리 제한 가능

<details>
<summary>정답 보기</summary>

**정답: B) ResourceQuota는 네임스페이스 총량 제한, LimitRange는 개별 Pod/Container 제한**

**설명:**
ResourceQuota는 네임스페이스 내 전체 리소스 사용량(총 CPU, 메모리, Pod 수 등)을 제한합니다. LimitRange는 개별 Pod나 Container의 리소스 범위와 기본값을 설정합니다. 둘을 함께 사용하여 효과적인 리소스 거버넌스를 구현합니다.

</details>

### 10. 컨테이너에서 CPU limit을 설정하지 않는 전략의 장단점은 무엇인가요?

- A) 장점: 스로틀링 방지, 단점: 노이지 네이버 문제 가능성
- B) 장점: 메모리 절약, 단점: 성능 저하
- C) 장점: 자동 스케일링, 단점: 비용 증가
- D) 장점: 보안 강화, 단점: 복잡성 증가

<details>
<summary>정답 보기</summary>

**정답: A) 장점: 스로틀링 방지, 단점: 노이지 네이버 문제 가능성**

**설명:**
CPU limit을 설정하지 않으면 버스트 트래픽 시 스로틀링 없이 CPU를 사용할 수 있습니다. 하지만 다른 Pod에 영향을 줄 수 있는 "노이지 네이버" 문제가 발생할 수 있습니다. requests는 반드시 설정하고, 워크로드 특성에 따라 limit 설정 여부를 결정합니다.

</details>

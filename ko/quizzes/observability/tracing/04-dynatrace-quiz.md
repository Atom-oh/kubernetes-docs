# Dynatrace 퀴즈

Dynatrace에 대한 이해도를 테스트하는 퀴즈입니다.

---

1. Dynatrace의 핵심 기술인 OneAgent의 특징이 아닌 것은?
   - A) 단일 에이전트로 전체 스택 모니터링
   - B) 자동 코드 계측
   - C) 수동 구성 필요
   - D) 프로세스 자동 탐지

<details>
<summary>정답 보기</summary>

**정답: C) 수동 구성 필요**

**설명:**
OneAgent는 자동 탐지와 자동 계측이 핵심 특징입니다. 설치 후 별도의 수동 구성 없이 호스트의 프로세스, 서비스, 애플리케이션을 자동으로 탐지하고 모니터링합니다. 이는 Dynatrace의 "Zero-configuration" 철학을 반영합니다.

</details>

---

2. EKS에서 Dynatrace를 배포할 때 권장되는 방식은?
   - A) kubectl apply로 직접 배포
   - B) Dynatrace Operator 사용
   - C) Helm으로 OneAgent만 배포
   - D) Lambda 함수로 배포

<details>
<summary>정답 보기</summary>

**정답: B) Dynatrace Operator 사용**

**설명:**
Dynatrace Operator는 Kubernetes 환경에서 Dynatrace 컴포넌트(OneAgent, ActiveGate 등)의 라이프사이클을 자동으로 관리합니다. DynaKube CR을 통해 선언적으로 구성하며, 자동 업데이트, 롤링 배포, 상태 모니터링 등을 제공합니다.

</details>

---

3. Davis AI 엔진의 주요 기능이 아닌 것은?
   - A) 자동 기준선(baseline) 학습
   - B) 이상 탐지
   - C) 코드 자동 수정
   - D) 근본 원인 분석

<details>
<summary>정답 보기</summary>

**정답: C) 코드 자동 수정**

**설명:**
Davis AI는 자동으로 기준선을 학습하고, 이상을 탐지하며, 문제의 근본 원인을 분석합니다. 하지만 코드를 자동으로 수정하지는 않습니다. Davis는 문제를 진단하고 해결 방향을 제안하지만, 실제 코드 수정은 개발자가 수행해야 합니다.

</details>

---

4. Dynatrace의 배포 모드 중 Cloud Native Full Stack과 Classic Full Stack의 차이점은?
   - A) Cloud Native는 Windows만 지원
   - B) Cloud Native는 코드 모듈 주입 방식 사용
   - C) Classic은 클라우드 환경에서 사용 불가
   - D) 두 모드는 동일한 기능 제공

<details>
<summary>정답 보기</summary>

**정답: B) Cloud Native는 코드 모듈 주입 방식 사용**

**설명:**
Cloud Native Full Stack은 CSI Driver를 통해 코드 모듈을 Pod에 주입하는 경량화된 방식입니다. Classic Full Stack은 DaemonSet으로 전체 OneAgent를 각 노드에 배포합니다. Cloud Native는 리소스 사용량이 적고 Pod 수준의 세밀한 제어가 가능하지만, 호스트 수준 모니터링에는 제한이 있습니다.

</details>

---

5. Dynatrace에서 PurePath 기술이 제공하는 기능은?
   - A) 로그 압축
   - B) 코드 수준 분산 추적
   - C) 네트워크 패킷 캡처
   - D) 데이터베이스 백업

<details>
<summary>정답 보기</summary>

**정답: B) 코드 수준 분산 추적**

**설명:**
PurePath는 Dynatrace의 독자적인 분산 추적 기술로, 요청이 시스템을 통과하는 전체 경로를 코드 수준까지 추적합니다. 단순히 서비스 간 호출뿐만 아니라 각 서비스 내부의 메서드 호출, 데이터베이스 쿼리, 외부 API 호출까지 상세하게 기록합니다.

</details>

---

6. Dynatrace Host Unit 계산 공식으로 올바른 것은?
   - A) vCPU + Memory(GB)
   - B) max(Memory(GB) / 16, vCPU / 1.5)
   - C) vCPU * Memory(GB) / 100
   - D) (vCPU + Memory(GB)) / 2

<details>
<summary>정답 보기</summary>

**정답: B) max(Memory(GB) / 16, vCPU / 1.5)**

**설명:**
Dynatrace Host Unit은 메모리와 CPU 중 더 큰 값을 기준으로 계산됩니다. 16GB 메모리 또는 1.5 vCPU가 1 Host Unit에 해당합니다. 예를 들어 8 vCPU, 32GB RAM 호스트는 max(2, 5.33) = 5.33 Host Units입니다.

</details>

---

7. Dynatrace ActiveGate의 역할이 아닌 것은?
   - A) 데이터 라우팅
   - B) Kubernetes API 모니터링
   - C) 데이터 장기 저장
   - D) 네트워크 영역 분리

<details>
<summary>정답 보기</summary>

**정답: C) 데이터 장기 저장**

**설명:**
ActiveGate는 OneAgent와 Dynatrace SaaS 간의 데이터 라우팅, Kubernetes API 모니터링, 폐쇄망 환경에서의 프록시 역할을 수행합니다. 데이터 장기 저장은 Dynatrace의 Grail 데이터 레이크하우스에서 담당하며, ActiveGate는 데이터를 저장하지 않고 전달만 합니다.

</details>

---

8. Dynatrace에서 namespaceSelector를 사용하는 목적은?
   - A) 네임스페이스 생성
   - B) 특정 네임스페이스만 모니터링
   - C) 네임스페이스 간 통신 차단
   - D) 리소스 할당량 설정

<details>
<summary>정답 보기</summary>

**정답: B) 특정 네임스페이스만 모니터링**

**설명:**
DynaKube CR의 namespaceSelector를 사용하면 특정 레이블이 있는 네임스페이스만 모니터링 대상으로 지정할 수 있습니다. 이를 통해 프로덕션 환경만 모니터링하거나, 특정 팀의 네임스페이스만 선택적으로 모니터링하여 비용을 최적화할 수 있습니다.

</details>

---

9. Dynatrace와 OpenTelemetry를 연동할 때 사용하는 프로토콜은?
   - A) gRPC만 지원
   - B) HTTP만 지원
   - C) OTLP (gRPC 및 HTTP)
   - D) Proprietary 프로토콜만 지원

<details>
<summary>정답 보기</summary>

**정답: C) OTLP (gRPC 및 HTTP)**

**설명:**
Dynatrace는 OpenTelemetry Protocol(OTLP)을 네이티브로 지원합니다. OTEL Collector에서 otlphttp exporter를 사용하여 Dynatrace API 엔드포인트로 traces, metrics, logs를 전송할 수 있습니다. gRPC와 HTTP 모두 지원됩니다.

</details>

---

10. Dynatrace의 Smartscape가 제공하는 기능은?
    - A) 스마트 알림 필터링
    - B) 실시간 토폴로지 매핑
    - C) 자동 스케일링
    - D) 코드 리뷰

<details>
<summary>정답 보기</summary>

**정답: B) 실시간 토폴로지 매핑**

**설명:**
Smartscape는 Dynatrace의 실시간 토폴로지 매핑 기술입니다. 인프라(호스트, 컨테이너), 프로세스, 서비스, 애플리케이션 간의 관계를 자동으로 탐지하고 시각화합니다. 이를 통해 시스템의 의존성을 이해하고 문제 영향 범위를 파악할 수 있습니다.

</details>

---

# Knative 퀴즈

> **마지막 업데이트**: 2026년 9월 11일

1. Knative Serving에서 Scale-to-Zero가 동작하는 원리는?
   - A) Pod를 삭제하고 새 요청 시 Deployment를 다시 생성
   - B) Activator가 허용된 요청을 버퍼링하고 오토스케일링 경로가 준비된 복제본을 활성화
   - C) Node를 종료하고 새 요청 시 Karpenter가 Node를 프로비저닝
   - D) 컨테이너를 일시 중지(pause)하고 요청 시 재개

<details>
<summary>정답 보기</summary>

**정답: B) Activator가 허용된 요청을 버퍼링하고 오토스케일링 경로가 준비된 복제본을 활성화**

**설명:**
복제본이0개면 Activator 경로를 사용해 용량·타임아웃 범위 안에서 요청을 버퍼링하고 준비된 용량이 생기기를 기다립니다. 실패·버퍼 고갈·클라이언트/요청 타임아웃은 여전히 오류를 만들 수 있습니다. min-scale을 양수로 두면 일반적인 유휴 제로 축소를 피하지만 새 Revision·재시작·추가 복제본 초기화까지 제거하지는 않습니다.

</details>

---

2. Knative Serving의 KPA와 HPA 통합 방식은 어떻게 다른가요?
   - A) KPA는 CPU만 기반이고, HPA는 메모리만 기반
   - B) KPA는 동시 요청 수(concurrency) 기반이며 Scale-to-Zero를 지원하고, HPA는 CPU/메모리 기반
   - C) KPA는 노드 스케일링이고, HPA는 Pod 스케일링
   - D) KPA는 수동 스케일링이고, HPA는 자동 스케일링

<details>
<summary>정답 보기</summary>

**정답: B) KPA는 동시 요청 수(concurrency) 기반이며 Scale-to-Zero를 지원하고, HPA는 CPU/메모리 기반**

**설명:**
Knative KPA는 동시성/RPS와 Activator 기반 제로 경로를 지원합니다. 선택적 Knative HPA 확장은 CPU·메모리·지원되는 사용자 정의 Pod 메트릭을 사용하며 해당 제로 경로를 구현하지 않습니다. Kubernetes HPA 전체에 대한 단정은 아닙니다. 업스트림 Kubernetes1.37은 object/external 메트릭의 제로 축소를 beta로 지원합니다.1.23 HPA 구현에서 CPU 목표는 CPU 요청량 대비 사용률%, 메모리는MiB, 사용자 정의 메트릭은 Pod별 평균값입니다.

</details>

---

3. Knative Eventing의 Broker/Trigger 패턴에서 Trigger의 역할은?
   - A) 이벤트를 생성하는 소스
   - B) Broker에서 이벤트를 필터링하여 특정 서비스로 라우팅
   - C) 이벤트를 영구 저장하는 스토리지
   - D) 이벤트를 외부 시스템으로 전송하는 게이트웨이

<details>
<summary>정답 보기</summary>

**정답: B) Broker에서 이벤트를 필터링하여 특정 서비스로 라우팅**

**설명:**
Trigger는 Broker의 필터와 구독 대상을 정의하며 컨트롤러·Broker 데이터플레인이 전달합니다. 여러 Trigger가 일치하면 같은 이벤트 사본을 전달할 수 있고 재시도·저장 동작은 구현·정책에 따라 다릅니다. Trigger는 영구 이벤트 저장소나 범용 소비자 오토스케일러가 아닙니다.

</details>

---

4. Knative Service에서 `containerConcurrency: 1`로 설정하면 어떻게 동작하는가?
   - A) 컨테이너 당 최대 1개의 Pod만 생성
   - B) Queue Proxy가 Pod당 동시 요청1개까지만 전달하고 제한된 대기·비동기 확장을 사용
   - C) 1초에 하나의 요청만 허용
   - D) 하나의 리비전만 유지

<details>
<summary>정답 보기</summary>

**정답: B) Queue Proxy가 Pod당 동시 요청1개까지만 전달하고 제한된 대기·비동기 확장을 사용**

**설명:**
Queue Proxy가 각 Pod의 수신 컨테이너에 동시에 전달하는 요청 수를 제한합니다. 추가 요청은 제한된 큐에서 기다리거나 가용 용량으로 전달되거나 실패할 수 있습니다. 확장은 비동기이며 설정 한도·노드 용량에 제한됩니다. 초당1회, 모든 복제본을 합쳐1회, 추가 요청마다 새 Pod를 보장하는 설정이 아닙니다.

</details>

---

5. KEDA와 Knative를 함께 사용하는 적절한 시나리오는?
   - A) 두 도구는 호환되지 않으므로 하나만 사용
   - B) Knative Serving으로 HTTP 워크로드를 처리하고, KEDA로 큐/스트림 기반 비동기 워크로드를 스케일링
   - C) KEDA와 KPA가 같은 Knative 생성 Deployment를 독립적으로 스케일링
   - D) 모든 Knative Service가 KEDA를 자동 설치하고 기본 오토스케일러로 사용

<details>
<summary>정답 보기</summary>

**정답: B) Knative Serving으로 HTTP 워크로드를 처리하고, KEDA로 큐/스트림 기반 비동기 워크로드를 스케일링**

**설명:**
적합한 HTTP 서비스에는 Knative Serving을, 독립적으로 관리하는 백그라운드 워커에는 KEDA를 사용할 수 있습니다. 큐 보존·승인·활성화 메트릭·워커 멱등성을 구성하세요. KEDA와 KPA가 같은 생성된 Deployment를 각각 제어하게 하지 마세요. SinkBinding은 이벤트 생산자를 설정하며0개인 임의의 HTTP 소비자를 깨우지 않습니다.

</details>

---

6. Knative에서 트래픽 분할(Traffic Splitting)을 사용하여 카나리 배포를 하는 방법은?
   - A) Deployment의 replicas를 조정
   - B) Knative Service의 spec.traffic에서 Revision별 트래픽 비율을 지정
   - C) Istio VirtualService를 수동으로 생성
   - D) HPA의 minReplicas를 조정

<details>
<summary>정답 보기</summary>

**정답: B) Knative Service의 spec.traffic에서 Revision별 트래픽 비율을 지정**

**설명:**
spec.traffic에는 revisionName 또는 latestRevision: true와 비율을 지정합니다. @latest는 kn CLI 축약이며 revisionName이나 최신을 의미하는 API 태그가 아닙니다. 대상 Revision이 존재하고 준비되어 있어야 합니다. 경로 조정은 전역에서 즉시 원자적으로 전환되지 않으며 기존 요청은 이전 Revision에서 계속 처리될 수 있습니다.

</details>

---

7. Knative의 Dead Letter Sink의 목적은?
   - A) 삭제된 Knative Service를 보관
   - B) 구독자 전달 실패 시 설정된 대체 목적지로 전달을 시도
   - C) 만료된 Revision을 정리
   - D) 디버그 로그를 저장

<details>
<summary>정답 보기</summary>

**정답: B) 구독자 전달 실패 시 설정된 대체 목적지로 전달을 시도**

**설명:**
DLS는 전달 정책으로 구독자에게 보내지 못했을 때 사용하는 설정된 대체 목적지입니다. DLS도 실패할 수 있으며 보존·영속 저장 성공은 전송 구현과 처리기에 달려 있습니다. 의도한 저장·처리가 성공한 뒤에만 승인하고 필요한 경우 CloudEvent의 source와id 조합으로 중복을 제거하세요.

</details>

---

8. 명시적인 기본 용량 정책을 유지하며 콜드 스타트 지연을 줄일 수 있는 조합은?
   - A) 컨테이너 이미지 크기를 무한히 줄이기
   - B) `minScale` 어노테이션으로 최소 인스턴스를 유지하고, 경량 이미지와 빠른 시작 프레임워크 사용
   - C) Scale-to-Zero를 완전히 비활성화
   - D) Node를 항상 최대 수로 유지

<details>
<summary>정답 보기</summary>

**정답: B) `minScale` 어노테이션으로 최소 인스턴스를 유지하고, 경량 이미지와 빠른 시작 프레임워크 사용**

**설명:**
양수 autoscaling.knative.dev/min-scale은 일반적인 유휴 기간에 기본 용량을 유지하고 initial-scale은 Revision 최초 생성 시 적용됩니다. 이미지·노드 가용성·캐시·시작·준비 상태가 지연에 영향을 줍니다. 새 Revision·재시작·기본 용량을 넘는 확장에는 콜드 스타트가 남으므로 제거를 보장하지 말고 대표 트래픽으로 측정하세요.

</details>

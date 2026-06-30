# Knative 퀴즈

1. Knative Serving에서 Scale-to-Zero가 동작하는 원리는?
   - A) Pod를 삭제하고 새 요청 시 Deployment를 다시 생성
   - B) Activator가 트래픽을 버퍼링하고, Autoscaler가 Replica를 0에서 1로 스케일업
   - C) Node를 종료하고 새 요청 시 Karpenter가 Node를 프로비저닝
   - D) 컨테이너를 일시 중지(pause)하고 요청 시 재개

<details>
<summary>정답 보기</summary>

**정답: B) Activator가 트래픽을 버퍼링하고, Autoscaler가 Replica를 0에서 1로 스케일업**

**설명:**
Replica가 0일 때 들어오는 요청은 Activator가 버퍼링합니다. Activator가 Autoscaler에 스케일업을 요청하고, Pod가 준비되면 버퍼링된 요청을 전달합니다. 이 과정이 "콜드 스타트"이며, `minScale`로 최소 인스턴스를 유지하여 콜드 스타트를 방지할 수 있습니다.

</details>

---

2. Knative의 KPA(Knative Pod Autoscaler)와 HPA의 핵심 차이점은?
   - A) KPA는 CPU만 기반이고, HPA는 메모리만 기반
   - B) KPA는 동시 요청 수(concurrency) 기반이며 Scale-to-Zero를 지원하고, HPA는 CPU/메모리 기반
   - C) KPA는 노드 스케일링이고, HPA는 Pod 스케일링
   - D) KPA는 수동 스케일링이고, HPA는 자동 스케일링

<details>
<summary>정답 보기</summary>

**정답: B) KPA는 동시 요청 수(concurrency) 기반이며 Scale-to-Zero를 지원하고, HPA는 CPU/메모리 기반**

**설명:**
KPA는 Queue Proxy가 측정하는 동시 요청 수나 RPS를 기반으로 스케일링하며, Scale-to-Zero를 네이티브로 지원합니다. HPA는 CPU/메모리 메트릭 기반으로 스케일링하지만 최소 1개의 Replica를 유지해야 합니다.

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
Trigger는 Broker에 등록되어 CloudEvents의 속성(type, source 등)을 기반으로 이벤트를 필터링합니다. 조건에 맞는 이벤트만 지정된 Subscriber(Knative Service, Kubernetes Service 등)로 전달합니다. 하나의 Broker에 여러 Trigger를 등록하여 이벤트를 다양한 서비스로 라우팅할 수 있습니다.

</details>

---

4. Knative Service에서 `containerConcurrency: 1`로 설정하면 어떻게 동작하는가?
   - A) 컨테이너 당 최대 1개의 Pod만 생성
   - B) 각 컨테이너가 한 번에 하나의 요청만 처리하고, 추가 요청은 새 Pod로 라우팅
   - C) 1초에 하나의 요청만 허용
   - D) 하나의 리비전만 유지

<details>
<summary>정답 보기</summary>

**정답: B) 각 컨테이너가 한 번에 하나의 요청만 처리하고, 추가 요청은 새 Pod로 라우팅**

**설명:**
`containerConcurrency: 1`은 각 Pod의 Queue Proxy가 동시에 하나의 요청만 컨테이너로 전달하도록 제한합니다. 추가 요청이 들어오면 Autoscaler가 새 Pod를 생성합니다. 이는 CPU 집약적 작업이나 스레드 안전하지 않은 애플리케이션에 유용합니다.

</details>

---

5. KEDA와 Knative를 함께 사용하는 적절한 시나리오는?
   - A) 두 도구는 호환되지 않으므로 하나만 사용
   - B) Knative Serving으로 HTTP 워크로드를 처리하고, KEDA로 큐/스트림 기반 비동기 워크로드를 스케일링
   - C) KEDA로 Scale-to-Zero를 구현하고, Knative로 이벤트를 라우팅
   - D) Knative가 KEDA를 내부적으로 사용

<details>
<summary>정답 보기</summary>

**정답: B) Knative Serving으로 HTTP 워크로드를 처리하고, KEDA로 큐/스트림 기반 비동기 워크로드를 스케일링**

**설명:**
Knative Serving은 HTTP 요청 기반 서버리스 워크로드에 최적화되어 있으며, Scale-to-Zero와 동시성 기반 스케일링을 제공합니다. KEDA는 SQS, Kafka, Redis 등의 큐 메트릭 기반 스케일링에 강점이 있습니다. 두 도구를 함께 사용하면 동기/비동기 워크로드를 각각 최적의 방식으로 스케일링할 수 있습니다.

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
Knative Service의 `spec.traffic` 필드에서 각 Revision에 대한 트래픽 비율(percent)을 지정할 수 있습니다. 예를 들어 기존 Revision에 90%, 새 Revision에 10%를 할당하여 카나리 배포를 구현합니다. `@latest` 태그로 최신 Revision을 참조하거나, 특정 Revision 이름을 직접 지정할 수 있습니다.

</details>

---

7. Knative의 Dead Letter Sink의 목적은?
   - A) 삭제된 Knative Service를 보관
   - B) 이벤트 전달에 실패한 경우 이벤트를 별도의 목적지로 전송하여 손실 방지
   - C) 만료된 Revision을 정리
   - D) 디버그 로그를 저장

<details>
<summary>정답 보기</summary>

**정답: B) 이벤트 전달에 실패한 경우 이벤트를 별도의 목적지로 전송하여 손실 방지**

**설명:**
Dead Letter Sink는 이벤트 전달이 재시도 후에도 실패하면 해당 이벤트를 지정된 목적지(다른 Knative Service, Kubernetes Service 등)로 전송합니다. 이를 통해 이벤트 손실을 방지하고, 실패한 이벤트를 분석하거나 재처리할 수 있습니다.

</details>

---

8. Knative Serving의 콜드 스타트를 최소화하기 위한 가장 효과적인 방법은?
   - A) 컨테이너 이미지 크기를 무한히 줄이기
   - B) `minScale` 어노테이션으로 최소 인스턴스를 유지하고, 경량 이미지와 빠른 시작 프레임워크 사용
   - C) Scale-to-Zero를 완전히 비활성화
   - D) Node를 항상 최대 수로 유지

<details>
<summary>정답 보기</summary>

**정답: B) `minScale` 어노테이션으로 최소 인스턴스를 유지하고, 경량 이미지와 빠른 시작 프레임워크 사용**

**설명:**
`autoscaling.knative.dev/min-scale`로 최소 인스턴스를 1 이상으로 설정하면 콜드 스타트를 방지합니다. 추가로 경량 베이스 이미지(distroless, alpine), GraalVM Native Image 같은 빠른 시작 프레임워크, `initialScale` 설정 등을 조합하면 콜드 스타트 시간을 최소화할 수 있습니다.

</details>

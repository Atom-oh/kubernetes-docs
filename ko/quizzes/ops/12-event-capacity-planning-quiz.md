# 이벤트 용량 계획 플레이북 퀴즈

1. KEDA에서 복수 트리거(Cron + Prometheus + SQS)를 동시에 설정했을 때, 최종 replica 수는 어떻게 결정되나요?
   - A) 모든 트리거의 평균값
   - B) 가장 낮은 값 (MIN)
   - C) 가장 높은 값 (MAX)
   - D) 첫 번째 트리거의 값

<details>
<summary>정답 보기</summary>

**정답: C) 가장 높은 값 (MAX)**

**설명:**
KEDA는 복수 트리거가 설정된 경우 각 트리거가 요구하는 replica 수 중 가장 높은 값을 선택합니다. 이를 통해 "Cron으로 바닥을 잡고, 메트릭으로 천장을 결정"하는 패턴이 가능합니다. 예를 들어, Cron이 100을 요구하고 Prometheus가 150을 요구하면 150이 적용됩니다.

</details>

---

2. Pause Pod 패턴에서 실제 워크로드가 배치될 때 Pause Pod가 축출되는 원리는 무엇인가요?
   - A) Pod의 리소스 요청이 작아서 자동 교체
   - B) PriorityClass의 value가 낮아서 Preemption 발생
   - C) DaemonSet이라서 자동으로 재배치
   - D) TTL이 만료되어 자동 삭제

<details>
<summary>정답 보기</summary>

**정답: B) PriorityClass의 value가 낮아서 Preemption 발생**

**설명:**
Pause Pod에는 value: -10의 낮은 PriorityClass가 할당됩니다. 실제 워크로드(기본 priority 0 이상)가 스케줄링될 Node 공간이 부족할 때, Kubernetes Scheduler는 낮은 priority의 Pod를 축출(preemption)하여 공간을 확보합니다. 이를 통해 Node가 미리 프로비저닝된 상태에서 즉시 실제 워크로드를 배치할 수 있습니다.

</details>

---

3. 플래시 세일 이벤트에서 KEDA Cron 트리거의 시작 시간을 이벤트 시작 30분 전으로 설정하는 이유는?
   - A) KEDA의 폴링 간격이 30분이라서
   - B) Cron 트리거는 정확한 시간에 동작하지 않아서
   - C) Node 프로비저닝과 Pod 스케줄링에 시간이 필요하므로
   - D) AWS API 호출 제한을 피하기 위해

<details>
<summary>정답 보기</summary>

**정답: C) Node 프로비저닝과 Pod 스케줄링에 시간이 필요하므로**

**설명:**
KEDA가 Pod를 스케일 업하면 Karpenter가 새 Node를 프로비저닝하는 데 60-90초, Pod 스케줄링과 컨테이너 시작에 추가 시간이 소요됩니다. 이벤트 시작 30분 전에 미리 스케일링을 시작하면 모든 Pod가 Ready 상태가 되어 첫 트래픽 급증을 안정적으로 처리할 수 있습니다.

</details>

---

4. EC2 Capacity Reservation의 `instance_match_criteria`를 `targeted`로 설정하는 이유는?
   - A) 비용을 절감하기 위해
   - B) 특정 Karpenter NodePool만 해당 예약을 사용하도록 제한하기 위해
   - C) Spot 인스턴스와 함께 사용하기 위해
   - D) Multi-AZ 배포를 위해

<details>
<summary>정답 보기</summary>

**정답: B) 특정 Karpenter NodePool만 해당 예약을 사용하도록 제한하기 위해**

**설명:**
`targeted` 설정은 명시적으로 해당 Capacity Reservation을 참조하는 인스턴스만 예약을 사용할 수 있도록 합니다. 이를 통해 이벤트 전용 Karpenter NodePool(capacityReservationSelectorTerms로 매칭)만 예약된 용량을 사용하고, 일반 워크로드가 예약을 소진하는 것을 방지합니다.

</details>

---

5. Karpenter NodePool의 `weight` 필드 값이 높으면 어떤 효과가 있나요?
   - A) Node 프로비저닝 속도가 빨라진다
   - B) 해당 NodePool이 다른 NodePool보다 우선 사용된다
   - C) 더 많은 Node를 프로비저닝할 수 있다
   - D) 비용이 더 낮은 인스턴스를 선택한다

<details>
<summary>정답 보기</summary>

**정답: B) 해당 NodePool이 다른 NodePool보다 우선 사용된다**

**설명:**
Karpenter에서 여러 NodePool이 Pending Pod의 요구사항을 충족할 수 있는 경우, weight 값이 높은 NodePool이 우선 선택됩니다. 이벤트 NodePool에 weight: 100을 설정하면 기본 NodePool(weight: 10 등)보다 우선 사용되어 이벤트 전용 Node 구성(인스턴스 타입, capacity type 등)이 적용됩니다.

</details>

---

6. 이벤트 후 스케일 다운 시 HPA의 `scaleDown.policies`에서 `type: Percent, value: 10, periodSeconds: 120`의 의미는?
   - A) 120초 안에 전체의 10%까지 축소
   - B) 120초마다 현재 Pod 수의 10%씩 축소
   - C) 10초마다 120개씩 축소
   - D) 최소 10개를 유지하며 120초 후 전체 축소

<details>
<summary>정답 보기</summary>

**정답: B) 120초마다 현재 Pod 수의 10%씩 축소**

**설명:**
HPA의 scaleDown behavior에서 `type: Percent, value: 10, periodSeconds: 120`은 120초(2분)마다 현재 replica 수의 최대 10%까지 축소할 수 있다는 의미입니다. 200개 Pod가 있다면 2분마다 최대 20개씩 줄어들어, 급격한 축소로 인한 서비스 불안정을 방지합니다.

</details>

---

7. 용량 계획 워크시트에서 안전 마진(Safety Margin)으로 30%를 추가하는 주된 이유는?
   - A) AWS 인스턴스 가격 변동 대비
   - B) 예측과 실제 트래픽의 차이, Pod 시작 시간, 비균등 부하 분산 등을 고려
   - C) Kubernetes 시스템 Pod가 사용하는 리소스 때문
   - D) 네트워크 대역폭 제한 때문

<details>
<summary>정답 보기</summary>

**정답: B) 예측과 실제 트래픽의 차이, Pod 시작 시간, 비균등 부하 분산 등을 고려**

**설명:**
안전 마진 30%는 여러 불확실성을 흡수합니다: (1) 트래픽 예측이 정확하지 않을 수 있음, (2) Pod가 동시에 준비되지 않음, (3) 부하가 Pod 간 균등하게 분산되지 않음, (4) 일부 Node/Pod 장애 가능성. 이전 이벤트의 포스트모템 데이터를 기반으로 마진율을 조정할 수 있습니다.

</details>

---

8. 이미지 사전 캐싱(Image Pre-Caching) DaemonSet에서 initContainers를 사용하는 이유는?
   - A) 이미지를 실행한 후 종료하여 리소스를 절약하기 위해
   - B) 이미지를 Node에 다운로드(pull)하고 종료하여 캐시만 남기기 위해
   - C) 이미지 버전을 검증하기 위해
   - D) Container Registry에 인증하기 위해

<details>
<summary>정답 보기</summary>

**정답: B) 이미지를 Node에 다운로드(pull)하고 종료하여 캐시만 남기기 위해**

**설명:**
DaemonSet의 initContainers는 모든 Node에서 실행되어 컨테이너 이미지를 pull합니다. `echo cached`만 실행하고 종료하지만, 이미지는 Node의 로컬 캐시에 남습니다. 이후 실제 워크로드 Pod가 스케줄링될 때 이미지 pull 시간(수십 초~수 분)을 절약하여 Pod 시작 시간을 단축합니다.

</details>

---

9. D-30 타임라인에서 부하 테스트를 목표 RPM의 120%로 실행하는 이유는?
   - A) AWS에서 높은 트래픽을 사전 승인받기 위해
   - B) 목표 트래픽 이상에서도 시스템이 안정적인지 확인하고 병목을 미리 발견하기 위해
   - C) KEDA 트리거의 threshold를 정확히 산출하기 위해
   - D) 비용 계산의 정확도를 높이기 위해

<details>
<summary>정답 보기</summary>

**정답: B) 목표 트래픽 이상에서도 시스템이 안정적인지 확인하고 병목을 미리 발견하기 위해**

**설명:**
이벤트 시 실제 트래픽이 예상을 초과할 수 있으므로, 120% 부하 테스트를 통해: (1) 예상 이상의 트래픽에서도 시스템 안정성 확인, (2) DB 커넥션, 네트워크 대역폭, API 게이트웨이 등의 병목 사전 발견, (3) 스케일링 동작(KEDA→HPA→Karpenter 체인)의 실제 검증이 가능합니다.

</details>

---

10. Spot 인스턴스를 이벤트에 사용할 때 On-Demand를 권장하는 상황으로 가장 적절한 것은?
    - A) 이벤트 지속 시간이 4시간 이상일 때
    - B) Spot 절감율이 60% 이상일 때
    - C) 매출에 직접 영향을 미치고 중단이 허용되지 않는 핵심 서비스일 때
    - D) 워크로드에 재시도(retry) 로직이 구현되어 있을 때

<details>
<summary>정답 보기</summary>

**정답: C) 매출에 직접 영향을 미치고 중단이 허용되지 않는 핵심 서비스일 때**

**설명:**
Spot 인스턴스는 AWS에 의해 2분 경고 후 회수될 수 있습니다. 플래시 세일의 주문 처리 서비스처럼 매출에 직접 영향을 주는 핵심 서비스는 On-Demand를 사용하여 가용성을 보장해야 합니다. 반면, 이메일 발송이나 로그 처리 같은 보조 서비스는 재시도 로직이 있다면 Spot으로 비용을 절감할 수 있습니다.

</details>

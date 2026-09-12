# 이벤트 용량 계획 퀴즈

> **관련 문서**: [이벤트 용량 계획](../../ops/12-event-capacity-planning.md)

## 1. KEDA의 여러 metric이 있는 경우 최종 목표에 대한 올바른 설명은?

- A) 모든 값을 더한다
- B) HPA가 metric별 권고의 최댓값과 behavior/min/max 제약을 적용한다
- C) Cron이면 Ready Pod 수를 보장한다
- D) metrics가 항상 최대 상한을 정한다

<details>
<summary>정답 보기</summary>

**정답: B**

Cron은 기간 중 수요 바닥이고 maxReplicaCount 등이 상한입니다. 실제 준비는 별도 검증합니다.

</details>

## 2. 5필드 Cron으로 특정 날짜의 행사를 설정할 때 주의할 점은?

- A) 연도가 자동 포함된다
- B) 한 번 실행하면 자동 삭제된다
- C) 연도 필드가 없어 다음 해에도 반복될 수 있고 timezone/DST 검증이 필요하다
- D) 항상 UTC로만 실행된다

<details>
<summary>정답 보기</summary>

**정답: C**

예제의 연간 반복과 시작/종료 경계를 시험했습니다. 행사 후 이벤트 설정을 정리해야 합니다.

</details>

## 3. 정적 Karpenter NodePool의 올바른 조건은?

- A) weight만 올리면 정적 용량이 생긴다
- B) replicas를 사용하며 weight 없이 limits.nodes를 설정한다
- C) 언제든 replicas를 삭제해 dynamic으로 전환한다
- D) scale 동작이 모든 NodePool budget에 막힌다

<details>
<summary>정답 보기</summary>

**정답: B**

정적/동적 모드를 구별합니다. 정적 scale은 NodePool disruption budget을 우회하지만 PDB를 고려합니다.

</details>

## 4. Placeholder Deployment 목표 수를 인계 후에도 유지하면?

- A) 항상 추가 비용 없이 유지된다
- B) 선점된 placeholder를 재생성하여 추가 노드를 만들 수 있다
- C) Karpenter가 자동으로 desired를 0으로 만든다
- D) 실제 앱이 항상 즉시 Ready가 된다

<details>
<summary>정답 보기</summary>

**정답: B**

유지/만료 조건, placeholder 수 제거와 실제 앱 준비를 함께 검증합니다.

</details>

## 5. 30% 추가 용량이 한 AZ 장애 대응을 보장하나요?

- A) 항상 보장한다
- B) 인스턴스가 On-Demand이면 보장한다
- C) 배치와 잔존 처리량을 계산해야 하며 보장하지 않는다
- D) PDB만 있으면 보장한다

<details>
<summary>정답 보기</summary>

**정답: C**

15/11 노드 예제는 큰 AZ 손실 시 기준 피크를 충족하지 못합니다. 계산 입력 자체도 측정으로 검증해야 합니다.

</details>

## 6. targeted Capacity Reservation의 의미는?

- A) 특정 NodePool만 사용할 수 있는 보안 ACL
- B) 명시적으로 참조하고 조건이 맞는 인스턴스가 사용
- C) 모든 기존 인스턴스에 자동 적용
- D) On-Demand 할인 상품

<details>
<summary>정답 보기</summary>

**정답: B**

IAM/공유·AZ·타입·platform·tenancy와 실제 예약 사용 상태를 확인합니다. RI와도 다릅니다.

</details>

## 7. 즉시 예약을 D-30에 만들고 미래 end_date만 지정하면?

- A) 행사 시작까지 무료 대기
- B) end_date가 미래 시작을 의미
- C) 미사용 활성 구간도 과금될 수 있다
- D) 사용 중 인스턴스와 예약을 항상 두 번 과금

<details>
<summary>정답 보기</summary>

**정답: C**

활성 구간을 비용 모델에 포함합니다. 예약을 소비하는 인스턴스를 이중으로 더하지 않습니다.

</details>

## 8. CloudWatch scaler의 metricStat과 minMetricValue를 올바르게 설명한 것은?

- A) metricStatType이 올바른 필드다
- B) minMetricValue는 항상 활성화 threshold다
- C) metricStat은 통계 선택, minMetricValue는 NoData fallback이며 ignoreNullValues=false가 우선한다
- D) Sum은 모든 rate gauge에 적합하다

<details>
<summary>정답 보기</summary>

**정답: C**

요청 delta/count와 rate/cumulative counter를 구별하고 period·collection window·게시 지연을 확인합니다.

</details>

## 9. 메트릭 지연 때 KEDA 관리 Deployment에 대한 올바른 대응은?

- A) Deployment만 scale하면 항상 유지된다
- B) HPA 이름은 항상 Deployment와 같다
- C) 승인된 상한 안에서 ScaledObject floor와 GitOps 소유권을 검토한다
- D) 상한 없이 새 NodePool을 만든다

<details>
<summary>정답 보기</summary>

**정답: C**

직접 HPA/Deployment 변경은 reconcile로 덮어쓸 수 있습니다. 원래 값을 기록하고 복원합니다.

</details>

## 10. 행사 종료와 이미지 준비에 대한 올바른 설명은?

- A) 모든 이미지에서 sh echo가 동작하고 캐시는 영구적이다
- B) 30분 후 NodePool을 삭제하면 항상 안전하다
- C) 앱 준비·cache 제약을 확인하고 baseline trigger와 실제 노드/예약 종료를 검증한다
- D) ScaledObject 삭제는 항상 원래 replica를 복원한다

<details>
<summary>정답 보기</summary>

**정답: C**

기동/GC/아키텍처/권한은 이미지별로 다릅니다. 소유 controller와 삭제 수명주기를 고려해 정리합니다.

</details>

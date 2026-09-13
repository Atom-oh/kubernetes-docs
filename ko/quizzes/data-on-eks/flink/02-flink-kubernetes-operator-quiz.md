# Flink Kubernetes Operator 퀴즈

Operator 1.15.0 / Flink 2.2.1 기준으로 설치·상태 복구·autoscaler를 확인합니다.

1. Deployment와 SessionJob은 어떻게 다른가요?

<details>
<summary>정답 보기</summary>

**정답:** Deployment는 Application/Session cluster, SessionJob은 기존 managed Session cluster의 job을 정의합니다.

**설명:** 개별 SessionJob을 관리해도 기반 cluster의 자원·장애는 공유합니다.

</details>

2. Kubernetes 1.21+라는 과거 최소값만 확인하면 현재 EKS에 적합한가요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. 현재 EKS 지원 버전, client skew와 Operator·webhook·CRD 호환성을 확인합니다.

**설명:** Namespace label 기능의 도입 시점은 현재 전체 지원 표나 모든 기능 검증을 대신하지 않습니다.

</details>

3. Blue/green CR이 있으면 두 job의 Kafka/S3 쓰기를 자동으로 무중복 전환하나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Consumer group·transactional ID·sink 출력과 state 호환성을 별도로 설계합니다.

**설명:** 두 child deployment의 전환 관리와 end-to-end 데이터 보장은 다른 문제이며 전환 중 추가 자원도 필요합니다.

</details>

4. Savepoint upgrade는 항상 가장 안전하고 느린 stop-the-world 방식인가요?

<details>
<summary>정답 보기</summary>

**정답:** 그렇게 일반화할 수 없습니다. 소요 시간·복원 가능성·fallback은 실제 job과 state 변경에 달려 있습니다.

**설명:** Snapshot 생성 성공만으로 serializer·UID·connector 호환성까지 검증되지는 않습니다.

</details>

5. Unhealthy job의 last-state 복구는 어떤 조건이 필요한가요?

<details>
<summary>정답 보기</summary>

**정답:** 접근 가능한 HA metadata/checkpoint와 호환되는 state, 자격 증명·저장소가 필요합니다.

**설명:** 새 savepoint를 요구하지 않을 수 있지만 metadata 손실이나 오래된 checkpoint가 자동 해결되지는 않습니다.

</details>

6. SessionJob YAML에 last-state만 넣으면 stateful upgrade 준비가 끝나나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Session cluster와 job의 effective config에 필요한 checkpointing·저장소·복구 조건이 있어야 합니다.

**설명:** 실제 validator와 restore 경로를 확인하며 mode 문자열만으로 안전성을 판정하지 않습니다.

</details>

7. Flink autoscaler의 주된 scaling 대상은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:** Job graph vertex별 parallelism입니다.

**설명:** HPA의 replica 조정과 다르며, 실제 Pod/node 수는 slot 배치와 자원 관리 계층에 달려 있습니다.

</details>

8. 하위 vertex의 목표율은 단순한 현재 upstream 출력율의 합인가요?

<details>
<summary>정답 보기</summary>

**정답:** 상위 목표율에 edge output ratio를 곱해 합산하며 backlog 처리 목표도 전파합니다.

**설명:** Filter·join 등 출력 비율과 필요한 미래 처리 용량을 고려해야 합니다.

</details>

9. Autoscaler는 CPU·memory 지표를 전혀 보지 않나요?

<details>
<summary>정답 보기</summary>

**정답:** 주 parallelism 모델은 처리율·busy time을 쓰지만 memory/GC pressure, quota와 선택적 memory tuning도 존재합니다.

**설명:** Memory tuning은 기본 false이며 CPU 기반 HPA와 동일하지 않습니다.

</details>

10. Flink에서 parallelism은 반드시 max parallelism의 약수여야 하나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Autoscaler가 균등한 key-group/partition 배치를 위해 정렬을 선호하는 것과 Flink의 허용 범위는 다릅니다.

**설명:** Alignment 모드·keyed 입력·source partition 수를 확인합니다. 기존 state의 max parallelism을 바꾸는 것은 호환성 검토가 필요합니다.

</details>

11. 모든 autoscaler rescale은 last-state 전체 upgrade인가요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. 가능한 경우 resource-requirements API를 사용하는 in-place scaling을 시도하고 조건에 따라 재배포합니다.

**설명:** In-place도 task 재시작·state 복구 비용을 없앤다는 보장은 아닙니다.

</details>

12. 예제에서 최신 Flink 2.3.0 대신 2.2.1을 기준으로 삼은 이유는 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:** Operator·커넥터 공개 지원 표와 함께 확인할 연동 조합을 고정하기 위해서입니다.

**설명:** CRD enum이 새로운 version 값을 받아들이는 것만으로 해당 조합의 runtime 호환성을 증명하지 않습니다.

</details>

13. Chart가 로깅 config를 제공하면 reporter JAR와 수집 서버도 설치된 것인가요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Chart 설정 파일, runtime image의 실제 JAR, reporter 활성화와 수집 backend를 구분해야 합니다.

**설명:** 1.15 chart에는 Log4j/Logback 설정이 있지만 YAML 설정만으로 모든 metrics pipeline이 생기지는 않습니다.

</details>

14. watchNamespaces를 지정하면 무엇을 추가 확인해야 하나요?

<details>
<summary>정답 보기</summary>

**정답:** 대상 namespace 존재 여부, 생성되는 job SA/Role/RoleBinding과 다른 기존 권한입니다.

**설명:** 빈 목록은 전체 감시입니다. Watch 범위만으로 tenant 간 완전한 격리가 성립하지 않습니다.

</details>

15. 10분 metrics window가 모든 workload의 최적값인가요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Window·stabilization·scale-down interval과 실제 SLO를 함께 조정합니다.

**설명:** 너무 짧으면 노이즈, 너무 길면 반응 지연이 커질 수 있습니다. 관찰 결과와 부하 시험으로 결정합니다.

</details>

16. 기본 webhook 설치 전 cert-manager가 필요한가요?

<details>
<summary>정답 보기</summary>

**정답:** 네. 검토한 chart는 Certificate와 Issuer를 생성하며 내부 cert 생성 Job은 없습니다.

**설명:** CRD 존재뿐 아니라 cert-manager controller/webhook/cainjector와 Certificate Ready도 확인합니다.

</details>

17. 기본 Flink image로 시작할 때 가상의 order-events JAR를 지정해도 되나요?

<details>
<summary>정답 보기</summary>

**정답:** 해당 JAR를 image에 넣지 않았다면 실행되지 않습니다. 본문은 실제 포함된 StateMachineExample으로 경로를 확인합니다.

**설명:** Stateless demo 성공과 durable checkpoint/HA 복구 검증은 별도입니다.

</details>

18. 추천 parallelism만 관찰하고 실제 scaling을 막는 설정은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:** job.autoscaler.enabled=true와 job.autoscaler.scaling.enabled=false입니다.

**설명:** 현재 utilization.target/min/max key를 쓰고 추천 결과·state 복구·quota를 검증한 뒤 실제 scaling을 켭니다.

</details>

19. 초기 FlinkDeployment 준비 상태는 어떤 condition으로 기다리나요?

<details>
<summary>정답 보기</summary>

**정답:** Running입니다. Available이 아닙니다.

**설명:** Running은 관찰된 job/JM 상태를 뜻합니다. 기존 CR update 후에는 stale condition과 실제 spec 반영을 구분해야 합니다.

</details>

20. Backlog 6,000건의 catch-up.duration을 600초에서 60초로 줄이면 추가 목표 처리율은 어떻게 바뀌나요?

<details>
<summary>정답 보기</summary>

**정답:** 10건/초에서 100건/초로 늘어납니다.

**설명:** 목표 해소 시간이 짧으면 더 많은 용량이 필요합니다. Backlog를 무시해 주는 grace period가 아니며 0은 backlog 기반 scaling을 끕니다.

</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/flink/02-flink-kubernetes-operator.md)

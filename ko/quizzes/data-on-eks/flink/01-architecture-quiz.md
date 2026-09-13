# Kubernetes에서의 Flink 아키텍처 퀴즈

Flink 2.2.1 / Operator 1.15.0 기준의 실행 역할과 자원 경계를 확인합니다.

1. 모든 제출 경로에서 JobManager가 최초 job graph를 만들고 client는 아무 계산도 하지 않나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Application main()은 JM에서 실행되지만 일반적인 2.2 Session CLI 제출은 client에서 graph를 구성합니다.

**설명:** JM은 실행·slot·checkpoint·복구를 조정하고 TM은 task를 실행합니다. 사용자 main()도 JM 자원을 사용할 수 있습니다.

</details>

2. TaskManager에 4 slots가 있으면 최대 4개의 operator subtask만 실행할 수 있나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Chaining과 slot sharing으로 여러 operator가 slot을 공유할 수 있습니다.

**설명:** Fixed slot은 주로 managed memory 할당 단위이며 CPU core나 독립적인 CPU isolation 단위가 아닙니다.

</details>

3. Application Mode는 항상 job 하나당 cluster 하나이며 공유 EKS 자원까지 완전히 격리하나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. 한 application/main()에 여러 job이 있을 수 있고, node·network·storage·quota는 공유될 수 있습니다.

**설명:** Application별 lifecycle/JVM 분리는 도움이 되지만 무조건적인 격리를 보장하지 않습니다. 2.2의 multi-execute Application HA 제한도 확인합니다.

</details>

4. Session Mode의 기존 cluster에 제출하면 job이 항상 즉시 실행되나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Cluster 시작 오버헤드는 줄일 수 있지만 slot·CPU·상태 복구·공유 부하를 기다릴 수 있습니다.

**설명:** Session job들은 JM/TM 자원을 공유하며 한 TM 장애가 그 TM을 사용하던 여러 job에 영향을 줄 수 있습니다.

</details>

5. 이 장에서 Per-Job을 현재 지원되는 세 번째 Native Kubernetes 모드로 세어도 되나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. 현재 다루는 cluster 수명 선택은 Application과 Session이며 Per-Job은 과거 모델입니다.

**설명:** Application/Session과 자원 관리 주체인 Native/Standalone은 서로 다른 분류입니다.

</details>

6. Native 모드의 TaskManager Pod와 그 Pod를 수용할 EKS node는 누가 관리하나요?

<details>
<summary>정답 보기</summary>

**정답:** Flink Kubernetes ResourceManager가 API로 TM Pod를 요청하고, Karpenter/Cluster Autoscaler 등은 별도로 node capacity를 관리합니다.

**설명:** TM 해제는 idle timeout·resource profile·수요에 따릅니다. Job 종료 즉시 모든 Pod/node가 사라지는 보장은 없습니다.

</details>

7. Standalone-on-Kubernetes의 TaskManager 수는 사람이 YAML을 고쳐야만 바꿀 수 있나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Operator 등 외부 controller가 Kubernetes 자원을 조정할 수 있습니다.

**설명:** Flink runtime이 Native 방식으로 직접 TM Pod를 요청하지 않는다는 뜻입니다. HA 등 추가 기능의 API 권한은 별도로 검토합니다.

</details>

8. Operator 1.15.0의 두 cluster CR은 무엇이며 Native만 지원하나요?

<details>
<summary>정답 보기</summary>

**정답:** FlinkDeployment와 FlinkSessionJob이며 Native와 Standalone을 모두 지원합니다.

**설명:** Deployment는 Application/Session cluster, SessionJob은 기존 managed Session cluster의 job을 정의합니다. 버전 enum에 있는 값만으로 통합 호환성을 판정하지 않습니다.

</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/flink/01-architecture.md)

# 운영·HA·관리형 Flink 퀴즈

실제 수집 경로, 메모리·복구 경계와 서비스 지원 범위를 확인합니다.

1. 검토한 Kubernetes HA의 leader election은 어떤 자원을 사용하나요?

<details>
<summary>정답 보기</summary>

**정답:** Fabric8 ConfigMapLock을 사용하며 Kubernetes control plane의 가용성에 의존합니다.

**설명:** 별도의 leader-election 서버를 추가하는 것이 아니며, 항상 Lease 자원이라고 일반화하지 않습니다. ZooKeeper HA도 별도 지원 방식입니다.

</details>

2. HA ConfigMap, HA storageDir, checkpoint directory는 같은 데이터를 저장하나요?

<details>
<summary>정답 보기</summary>

**정답:** ConfigMap은 leader 정보/참조, HA storageDir은 JM 복구 metadata·job graph, checkpoint directory는 checkpoint state를 보존합니다.

**설명:** HA 경로 하나를 설정했다고 모든 state 파일과 복구 권한이 준비되는 것은 아닙니다.

</details>

3. HA용 ConfigMap Role만 있으면 Native Flink 배포의 모든 권한이 충족되나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Native ResourceManager는 Pod/Service 관리 등 별도 권한도 필요합니다.

**설명:** 기능별 caller 권한을 확인합니다. 실패가 항상 silent한 것도 아니므로 API 오류·로그·재시작을 조사합니다.

</details>

4. Flink autoscaler가 조정하는 것과 node autoscaler가 조정하는 것은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:** 주로 vertex parallelism과 node capacity입니다.

**설명:** Pressure·quota·state 복구·Pod 배치 조건으로 서로 영향을 주며, 무조건 Flink가 먼저라는 순서는 없습니다.

</details>

5. Pending Pod를 보면 Karpenter가 반드시 새 node를 만들나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Unschedulable인지 image pull/PVC/admission 등 다른 원인인지 구분해야 합니다.

**설명:** NodePool constraints·resource requests·instance 가용성·quota에 맞지 않으면 capacity를 만들 수 없을 수 있습니다.

</details>

6. Consolidation delay를 Flink stabilization보다 길게 두면 중단이 방지되나요?

<details>
<summary>정답 보기</summary>

**정답:** 보장되지 않습니다. Node failure·Spot·drift 등도 독립적으로 발생할 수 있습니다.

**설명:** 실제 provisioning·restore·backlog catch-up과 disruption/PDB 정책을 함께 시험합니다.

</details>

7. 현재 관리형 Flink 2.3 문서에 있다는 이유로 upstream 기능을 모두 쓸 수 있나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Java 17/Python 3.12 조합과 서비스별 미지원 기능을 확인해야 합니다.

**설명:** Java 21·ForSt·Native S3·custom telemetry·Studio 등의 제한이 있습니다. AWS의 기반 HA와 사용자의 application/state 책임을 구분합니다.

</details>

8. Managed KPU와 EKS Spot 비용은 어떻게 비교해야 하나요?

<details>
<summary>정답 보기</summary>

**정답:** 같은 throughput·latency·복구 목표에서 전체 비용과 운영 부담을 비교합니다.

**설명:** KPU에는 orchestration 추가 과금과 관련 storage/network 비용이 있고, Spot은 interruption/recovery 비용도 고려합니다.

</details>

9. RocksDB managed memory와 network buffer는 같은 pool인가요?

<details>
<summary>정답 보기</summary>

**정답:** 서로 다른 예산 영역입니다.

**설명:** 검증한 4GiB 기본 구성에서 managed fraction을 0.4에서 0.5로 늘려도 network는 같았고 task heap이 줄었습니다. 실제 RSS와 구성 예산은 다릅니다.

</details>

10. PodMonitor가 있어도 target이 없을 때 무엇을 확인하나요?

<details>
<summary>정답 보기</summary>

**정답:** Prometheus의 monitor/namespace selector, 실제 Pod label, named port, target namespace와 discovery 권한을 확인합니다.

**설명:** 이 chart의 Operator Pod에는 기본 instance 라벨이 없었습니다. Deployment metadata를 Pod label로 가정하지 않습니다.

</details>

11. block-cache-usage는 비율이고 Flink Counter는 항상 Prometheus Counter인가요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Cache usage는 bytes이며, 검토한 reporter는 Flink Counter를 Gauge로 내보냅니다.

**설명:** Cache capacity·hit/miss와 함께 해석합니다. Histogram도 Summary로 매핑되므로 exported TYPE과 label을 확인합니다.

</details>

12. Operator-managed CR에 kubernetes.cluster-id를 직접 넣어야 하나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Operator 1.15 validator가 금지하며 CR name/namespace에서 관리합니다.

**설명:** 저수준 CLI 가이드의 cluster ID 설정을 그대로 복사하지 않습니다. kubernetes.namespace와 high-availability.cluster-id도 구분합니다.

</details>

13. JM replica 2개와 checklist 완료만으로 즉시·무중단 복구를 보장하나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Election·node/AZ 배치·storage·state restore·replay 시간과 실제 결과를 검증해야 합니다.

**설명:** 기본값을 유지하는 것도 유효한 선택이며, 설정 존재보다 측정한 SLO/복구 결과와 운영 책임이 중요합니다.

</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/flink/04-operations-ha.md) | [Flink](../../../data-on-eks/flink/README.md)

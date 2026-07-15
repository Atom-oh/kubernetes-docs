# Part 4: 운영, 고가용성, 그리고 매니지드 Flink 퀴즈

이 퀴즈는 Zookeeper 없이 동작하는 Kubernetes 네이티브 HA의 원리, ConfigMap이 HA를 위해 저장하는 정보, Flink 오토스케일러와 Karpenter의 2단계 관계, 그리고 Amazon Managed Service for Apache Flink와 EKS 셀프 매니지드 Flink 중 언제 무엇을 선택해야 하는지에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Flink의 Kubernetes 네이티브 고가용성(FLIP-144)에서 Zookeeper를 대체하는 것은 무엇인가요?
   - A) Flink와 함께 배포되는 별도의 etcd 클러스터
   - B) Kubernetes 리더 선출(leader-election) API와 ConfigMap
   - C) 전용 Raft 합의 사이드카
   - D) AWS Systems Manager Parameter Store

<details>
<summary>정답 보기</summary>

**정답: B) Kubernetes 리더 선출(leader-election) API와 ConfigMap**

**설명:**
Flink 1.12부터 제공되는 Kubernetes 네이티브 HA는 다른 Kubernetes 컨트롤러들이 사용하는 것과 동일한 리더 선출 프리미티브로 어떤 JobManager 레플리카가 활성 상태인지 결정하고, 리더 주소와 HA 메타데이터를 ConfigMap에 저장합니다. 외부 Zookeeper 앙상블을 배포·업그레이드·백업할 필요가 없습니다.
</details>

2. Flink의 Kubernetes 네이티브 HA에서 사용하는 ConfigMap이 실제로 저장하는 것은 무엇인가요?
   - A) 잡의 전체 체크포인트 데이터
   - B) 활성 리더의 주소와 HA 메타데이터(JobGraph 저장소, 체크포인트 포인터)
   - C) TaskManager의 RocksDB 상태 사본
   - D) Flink Kubernetes Operator의 Helm values 값

<details>
<summary>정답 보기</summary>

**정답: B) 활성 리더의 주소와 HA 메타데이터(JobGraph 저장소, 체크포인트 포인터)**

**설명:**
ConfigMap은 다른 컴포넌트가 찾을 수 있도록 현재 활성 상태인 JobManager의 주소를 저장하고, 장애 복구 후 새 리더가 잡을 복구하는 데 필요한 HA 메타데이터(JobGraph 저장소와 체크포인트에 대한 포인터)도 함께 저장합니다. 실제 JobGraph와 체크포인트 데이터는 ConfigMap 자체가 아니라 `high-availability.storageDir`이 가리키는 내구성 있는 스토리지(예: S3)에 저장됩니다.
</details>

3. Kubernetes 네이티브 HA가 동작하려면 JobManager의 `ServiceAccount`에 어떤 RBAC 권한이 필요한가요?
   - A) 클러스터 전체에 대한 관리자 권한
   - B) `Pod` 오브젝트에 대한 읽기 전용 권한
   - C) 자신의 네임스페이스 안 `ConfigMap` 오브젝트에 대한 `get`/`list`/`watch`/`create`/`update`/`patch`/`delete` 권한
   - D) `PersistentVolumeClaim` 오브젝트에 대한 쓰기 권한

<details>
<summary>정답 보기</summary>

**정답: C) 자신의 네임스페이스 안 `ConfigMap` 오브젝트에 대한 `get`/`list`/`watch`/`create`/`update`/`patch`/`delete` 권한**

**설명:**
JobManager는 리더 선출과 HA 메타데이터 읽기/쓰기를 위해 Kubernetes API를 직접 호출하므로, 그 `ServiceAccount`에는 딱 이 정도 수준의 네임스페이스 범위 `Role`(`configmaps`에 대한 위 권한들)만 있으면 됩니다 — 클러스터 전체 관리자 권한처럼 더 넓은 권한은 필요 없습니다. 이 Role이 `RoleBinding`으로 바인딩되어 있지 않으면 HA 구성은 조용히 실패합니다. Pod는 정상적으로 뜨지만 리더 선출과 장애 복구가 실제로는 동작하지 않습니다.
</details>

4. Flink 오토스케일러와 Karpenter의 2단계 오토스케일링 관계에서, Flink 오토스케일러가 직접 제어하는 것은 무엇인가요?
   - A) EC2 인스턴스 유형과 노드 프로비저닝을 직접 제어
   - B) 백프레셔, Busy Time 같은 잡 내부 메트릭을 기반으로 한 버텍스별 병렬도
   - C) Karpenter의 `NodePool` 통합(consolidation) 설정
   - D) Kubernetes 스케줄러의 빈 패킹(bin-packing) 알고리즘

<details>
<summary>정답 보기</summary>

**정답: B) 백프레셔, Busy Time 같은 잡 내부 메트릭을 기반으로 한 버텍스별 병렬도**

**설명:**
Flink Kubernetes Operator에 내장된 오토스케일러는 버텍스별 메트릭(백프레셔, Busy Time, 랙)을 관찰해 각 연산자에 필요한 병렬도를 조정합니다 — 이는 하위 노드에 대한 정보가 없는, 잡 내부의 판단입니다. Karpenter는 그 결과로 생기는 TaskManager Pod 수에 반응하는, 별도의 노드 단위 루프입니다.
</details>

5. 이 2단계 스택에서 Karpenter가 새 EC2 노드를 프로비저닝하는 이유는 무엇인가요?
   - A) Flink의 체크포인트 메트릭을 독립적으로 모니터링하기 때문
   - B) 오토스케일러가 병렬도를 늘린 뒤 스케줄링되지 못하는 TaskManager Pod가 생기는 것에 반응하기 때문
   - C) Flink REST API를 직접 조회해 병렬도 설정을 가져오기 때문
   - D) Pod 상태와 무관하게 고정된 일정에 따라 노드를 프로비저닝하기 때문

<details>
<summary>정답 보기</summary>

**정답: B) 오토스케일러가 병렬도를 늘린 뒤 스케줄링되지 못하는 TaskManager Pod가 생기는 것에 반응하기 때문**

**설명:**
Karpenter는 TaskManager Pod가 왜 존재하는지는 전혀 모르고, Pending 상태로 스케줄링되지 못한 Pod에 용량이 필요하다는 사실에만 반응합니다. Flink 오토스케일러가 병렬도를 올려 더 많은 TaskManager Pod가 요청되면 일부가 기존 노드에 스케줄링되지 못할 수 있고, Karpenter는 그 신호에 반응해 새 EC2 용량을 프로비저닝합니다. 잡 단위 판단이 항상 먼저 일어나고, 노드 단위 판단은 그 결과에만 반응합니다.
</details>

6. Flink 오토스케일러가 병렬도를 Karpenter의 `NodePool`이 맞는 노드를 프로비저닝할 수 있는 속도보다 빠르게 늘리면 어떤 문제가 생길 수 있나요?
   - A) 잡이 메모리 부족(OOM) 오류로 크래시된다
   - B) 새 TaskManager Pod가 예상보다 오래 `Pending` 상태로 머물며 스케일 업 자체가 지연된다
   - C) Flink가 자동으로 힙 상태 백엔드로 전환된다
   - D) Kubernetes API 서버가 이후 Pod 생성 요청을 거부한다

<details>
<summary>정답 보기</summary>

**정답: B) 새 TaskManager Pod가 예상보다 오래 `Pending` 상태로 머물며 스케일 업 자체가 지연된다**

**설명:**
오토스케일러의 병렬도 증가 속도가 Karpenter가 맞는 EC2 용량을 프로비저닝하는 속도보다 빠르면, 새 TaskManager Pod가 예상보다 오래 `Pending` 상태로 머물게 되어 오토스케일러가 유발한 스케일 업 자체가 지연됩니다. 이는 Spark 성능 튜닝 문서에서 Karpenter와 Dynamic Resource Allocation(DRA)에 대해 설명하는 것과 같은 종류의 불일치입니다.
</details>

7. Amazon Managed Service for Apache Flink에서 JobManager 고가용성은 누가 관리하나요?
   - A) 고객이 직접 구성한 RBAC Role을 통해 고객이 관리
   - B) AWS가 여러 가용 영역(AZ)에 걸쳐 자동으로 관리
   - C) 고객이 프로비저닝한 Zookeeper 앙상블
   - D) 매니지드 서비스 내부에서 실행되는 Flink Kubernetes Operator

<details>
<summary>정답 보기</summary>

**정답: B) AWS가 여러 가용 영역(AZ)에 걸쳐 자동으로 관리**

**설명:**
Amazon Managed Service for Apache Flink는 완전관리형 서버리스 서비스로, 클러스터·호스트·Kubernetes 오브젝트를 전혀 프로비저닝할 필요가 없으며, EKS 셀프 매니지드 환경에서는 RBAC Role과 `flinkConfiguration`을 직접 구성해야 했던 JobManager HA도 AWS가 여러 AZ에 걸쳐 자동으로 처리합니다.
</details>

8. Amazon Managed Service for Apache Flink 대신 EKS에서 Flink를 직접 운영하는 구체적인 이유로 옳은 것은 무엇인가요?
   - A) RBAC Role을 절대 구성하고 싶지 않기 때문
   - B) 규모상 EC2 Spot Instance를 통한 비용 통제가 중요하고, AWS가 Flink-on-EKS를 Spot으로 최적화하는 가이드를 공개했기 때문
   - C) Amazon Managed Service for Apache Flink는 어떤 Flink 2.x 버전도 지원하지 않기 때문
   - D) 셀프 매니지드 Flink는 모니터링 구성이 전혀 필요 없기 때문

<details>
<summary>정답 보기</summary>

**정답: B) 규모상 EC2 Spot Instance를 통한 비용 통제가 중요하고, AWS가 Flink-on-EKS를 Spot으로 최적화하는 가이드를 공개했기 때문**

**설명:**
Amazon Managed Service for Apache Flink는 KPU 기준의 사용량 기반 과금 모델을 사용하며, Spot과 같은 비용 레버를 제공하지 않습니다. 세밀한 오토스케일러 튜닝이 필요하거나, Spot Instance로 비용을 통제하고 싶거나, 이미 다른 워크로드(예: Strimzi 기반 Kafka-on-EKS)를 동일한 GitOps/관측 파이프라인으로 운영 중인 조직은 EKS에서 Flink를 직접 운영하는 것이 유리합니다. 참고로 2026년 3월부터 매니지드 서비스도 Flink 2.2를 지원하므로 C는 옳지 않습니다.
</details>

## 단답형 문제

9. Flink의 Kubernetes 네이티브 HA가 Zookeeper 기반 HA처럼 별도의 쿼럼 앙상블을 필요로 하지 않는 이유를 한 문장으로 설명하세요.

<details>
<summary>정답 보기</summary>

**정답: Kubernetes 자체의 리더 선출 API가 이미 리더 선출 프리미티브를 제공하므로, Flink가 그 목적을 위해 별도의 Zookeeper 쿼럼을 실행하고 크기를 관리할 필요가 없습니다.**

**설명:**
Kubernetes 네이티브 HA에서도 여전히 직접 결정해야 하는 것은 `FlinkDeployment`가 실행하는 JobManager 레플리카 수입니다 — 2개 이상을 실행하면 장애 복구 시 즉시 넘겨받을 웜 스탠바이가 준비되지만, 그것을 대체했던 Zookeeper 기반 방식과 달리 별도로 크기를 관리해야 할 합의 앙상블 자체는 없습니다.
</details>

10. `high-availability.storageDir`이 가리켜야 하는 대상은 무엇이며 그 이유는 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답: 새 리더가 될 수 있는 어떤 Pod에서도 접근 가능한, 내구성 있는 공유 스토리지(예: S3)를 가리켜야 합니다. 실제 JobGraph와 체크포인트 포인터가 저장되는 곳이 바로 여기이며, ConfigMap은 이 위치와 리더 주소에 대한 포인터만 담고 있기 때문입니다.**

**설명:**
`storageDir`이 내구성 있는 공유 스토리지가 아니라면, 장애 복구 후 새로 선출된 리더가 잡을 복구하는 데 필요한 JobGraph와 체크포인트 데이터에 접근할 수 없어 HA 구성의 목적 자체가 무너집니다.
</details>

11. 2단계 오토스케일링 스택에서 Flink 오토스케일러와 Karpenter가 각각 반응하는 두 가지 서로 다른 신호를 설명하세요.

<details>
<summary>정답 보기</summary>

**정답: Flink 오토스케일러는 버텍스별 잡 메트릭(백프레셔, Busy Time, 랙)에 반응하여 연산자의 병렬도를 결정합니다. Karpenter는 그 결과로 생기는 TaskManager Pod의 스케줄링 상태(Pending/스케줄 불가 상태, 또는 비어버린 노드)에 반응하여 EC2 용량을 결정합니다.**

**설명:**
이 둘은 서로에 대해 직접적인 정보가 없는 독립적인 두 제어 루프입니다 — Flink 오토스케일러는 노드에 대해 알지 못하고, Karpenter는 잡 내부 메트릭에 대해 알지 못합니다 — 하지만 오토스케일러의 병렬도 판단이 Karpenter가 반응할 Pod 수를 바꾸기 때문에 서로 맞물려 있습니다.
</details>

## 실습 문제

12. `s3://my-flink-bucket/ha/`에 HA 메타데이터를 저장하고 클러스터 ID를 `my-flink-cluster`로 설정하여, `FlinkDeployment`에서 Kubernetes 네이티브 HA를 활성화하는 `flinkConfiguration` 스니펫을 작성하세요.

<details>
<summary>정답 보기</summary>

**정답:**
```yaml
high-availability.type: kubernetes
high-availability.storageDir: s3://my-flink-bucket/ha/
kubernetes.cluster-id: my-flink-cluster
```

**설명:**
`high-availability.type: kubernetes`는 (레거시 Zookeeper 기반 방식이 아닌) Kubernetes 네이티브 HA를 선택합니다. `high-availability.storageDir`은 JobGraph와 체크포인트 데이터를 저장할 내구성 있는 공유 위치를 지정합니다. `kubernetes.cluster-id`는 HA ConfigMap을 이 클러스터 전용으로 스코프하여, 같은 네임스페이스에 여러 Flink 클러스터가 있어도 충돌하지 않도록 합니다.
</details>

13. `flink` 네임스페이스의 Flink `ServiceAccount`에 Kubernetes 네이티브 HA에 필요한 `ConfigMap` 권한을 부여하는 RBAC `Role`(rules 부분만)을 작성하세요.

<details>
<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: flink-ha-role
  namespace: flink
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
```

**설명:**
JobManager는 리더 선출과 HA 메타데이터 관리를 위해 자신의 네임스페이스 안에서 ConfigMap을 생성·조회·수정·삭제할 수 있어야 합니다. HA가 실제로 동작하려면 이 `Role`을 `RoleBinding`으로 JobManager의 `ServiceAccount`에 바인딩해야 하며, 그렇지 않으면 HA 구성이 조용히 실패합니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/flink/04-operations-ha.md) | [이전 퀴즈: 상태 백엔드와 체크포인트](./03-state-checkpointing-streaming-quiz.md)

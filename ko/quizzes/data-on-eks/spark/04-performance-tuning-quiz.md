# Part 4: 성능 및 비용 튜닝 퀴즈

이 퀴즈는 Spark on EKS의 노드 타입 선택, 셔플 스필에 EBS보다 NVMe 인스턴스 스토어가 유리한 이유, On-Demand 드라이버/Spot Executor 분리, Spot 중단 시 Graceful Decommission의 역할, Karpenter와 Spark Dynamic Resource Allocation의 관계에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Spark on EKS에 대한 AWS의 모범 사례 가이드가 셔플이 많은 잡에 권장하는 인스턴스 패밀리는 무엇인가요?
   - A) T 계열 버스터블 인스턴스
   - B) C 계열 컴퓨팅 최적화 인스턴스
   - C) NVMe 인스턴스 스토어를 갖춘 R 계열 인스턴스 (R5d, R5ad, R5dn)
   - D) X 계열 고메모리 인스턴스

<details>
<summary>정답 보기</summary>

**정답: C) NVMe 인스턴스 스토어를 갖춘 R 계열 인스턴스 (R5d, R5ad, R5dn)**

**설명:**
셔플 스테이지는 대체로 CPU가 아니라 메모리와 디스크 I/O에 의해 좌우되므로, AWS는 vCPU당 메모리 비율이 넉넉하고 빠른 로컬 NVMe 디스크를 갖춘 R 계열 인스턴스를 셔플이 많은 Spark 워크로드에 특별히 권장합니다. T 계열과 C 계열은 이 프로파일에 맞게 사이즈되어 있지 않고, X 계열은 이 가이드에서 언급되지 않습니다.
</details>

2. 이 문서가 Graviton(arm64) 인스턴스 타입을 곧바로 추천하지 않고 "별도로 검증해야 할 대상"으로 다루는 이유는 무엇인가요?
   - A) Graviton 인스턴스는 컨테이너를 실행할 수 없기 때문
   - B) 이 섹션이 근거로 삼은 AWS 가이드가 Spark 셔플 워크로드에 대해 Graviton을 별도로 다루지 않기 때문
   - C) Graviton 인스턴스는 인스턴스 스토어를 지원하지 않기 때문
   - D) Spark는 arm64 아키텍처에서 전혀 실행될 수 없기 때문

<details>
<summary>정답 보기</summary>

**정답: B) 이 섹션이 근거로 삼은 AWS 가이드가 Spark 셔플 워크로드에 대해 Graviton을 별도로 다루지 않기 때문**

**설명:**
원 자료는 R5d/R5ad/R5dn을 권장하지만, 이 워크로드에 대해 R6gd/R7gd 같은 Graviton 대응 인스턴스는 다루지 않습니다. 문서화되지 않은 동등성을 단정하기보다, 네이티브/JNI 의존성의 arm64 빌드 여부를 포함해 독립적으로 벤치마크해 볼 것을 권장합니다.
</details>

3. EKS 워커 노드의 기본 루트 EBS 볼륨이 `spark.local.dir`에 부적합한 이유는 무엇인가요?
   - A) EBS 볼륨은 Spark가 마운트할 수 없기 때문
   - B) 루트 볼륨은 보통 20GB 안팎으로 잡혀 있어, 셔플이 많은 워크로드의 스크래치 공간으로는 턱없이 작기 때문
   - C) EBS 볼륨은 읽기 전용이기 때문
   - D) `spark.local.dir`은 특정 EBS 볼륨 타입을 요구하기 때문

<details>
<summary>정답 보기</summary>

**정답: B) 루트 볼륨은 보통 20GB 안팎으로 잡혀 있어, 셔플이 많은 워크로드의 스크래치 공간으로는 턱없이 작기 때문**

**설명:**
루트 EBS 볼륨은 OS와 컨테이너 이미지를 위해 잡힌 크기이지, 셔플이 많은 잡이 만들어내는 수백 GB~TB 단위의 스크래치 데이터를 위한 크기가 아닙니다. 실제 셔플 부하가 걸리면 금방 가득 차서 "No space left on device" 오류로 잡이 실패합니다.
</details>

4. NVMe 인스턴스 스토어가 셔플 스필 저장 용도로 EBS보다 나은 이유는 무엇인가요?
   - A) EBS보다 기본 크기가 더 크기 때문
   - B) 물리 호스트에 직접 붙어 있어 네트워크로 연결되는 EBS보다 처리량과 IOPS가 높기 때문
   - C) 가용 영역 간 데이터를 자동으로 복제하기 때문
   - D) 대용량으로 프로비저닝할 때 EBS보다 저렴하기 때문

<details>
<summary>정답 보기</summary>

**정답: B) 물리 호스트에 직접 붙어 있어 네트워크로 연결되는 EBS보다 처리량과 IOPS가 높기 때문**

**설명:**
인스턴스 스토어는 호스트에 물리적으로 직접 붙은 임시 로컬 디스크라서, 네트워크로 연결되는 EBS보다 훨씬 높은 처리량/IOPS를 제공합니다. 대신 인스턴스가 정지되거나 종료되면 데이터가 사라지므로, 셔플 스필처럼 일시적인 스크래치 데이터에만 적합합니다.
</details>

5. Spark 드라이버 파드는 On-Demand에, Executor 파드는 Spot에 두어야 하는 이유는 무엇인가요?
   - A) 드라이버는 Spot 인스턴스가 제공할 수 없는 CPU를 필요로 하기 때문
   - B) 드라이버는 잡의 코디네이션 상태를 쥐고 있어 잃으면 잡 전체가 실패하지만, Executor를 잃으면 그 Executor가 처리 중이던 태스크만 손실되기 때문
   - C) On-Demand 인스턴스는 파드 하나짜리 워크로드에서 항상 Spot보다 저렴하기 때문
   - D) Spot 인스턴스는 JVM 기반 워크로드를 실행할 수 없기 때문

<details>
<summary>정답 보기</summary>

**정답: B) 드라이버는 잡의 코디네이션 상태를 쥐고 있어 잃으면 잡 전체가 실패하지만, Executor를 잃으면 그 Executor가 처리 중이던 태스크만 손실되기 때문**

**설명:**
드라이버는 잡 전체의 단일 장애점(DAG 스케줄러, 태스크 북키핑)입니다. Executor는 언제든 대체 가능한 컴퓨트로, 하나를 잃어도 처리 중이던 태스크와 아직 마이그레이션하지 못한 셔플 데이터 정도만 손실되므로 Spot의 중단 위험을 감수할 만합니다. 드라이버는 그렇지 않습니다.
</details>

6. 드라이버/Executor 분리를 강제하는 Taint/Toleration 패턴에서, Executor 파드가 On-Demand `NodePool`에 스케줄되지 못하게 막는 요소는 무엇인가요?
   - A) Executor에는 On-Demand 노드에 대한 명시적 안티어피니티 규칙이 있다
   - B) On-Demand `NodePool`에 Taint가 걸려 있고, 그에 맞는 Toleration은 드라이버 파드에만 있다
   - C) Executor는 물리적으로 On-Demand 인스턴스에서 실행될 수 없다
   - D) Karpenter가 Executor 파드의 On-Demand 용량 사용을 자동으로 차단한다

<details>
<summary>정답 보기</summary>

**정답: B) On-Demand `NodePool`에 Taint가 걸려 있고, 그에 맞는 Toleration은 드라이버 파드에만 있다**

**설명:**
On-Demand `NodePool`에는 `NoSchedule` Taint(예: `spark-role=driver`)가 걸려 있습니다. 드라이버 Pod 템플릿(`spark.kubernetes.driver.podTemplateFile`)을 통해 이 Taint에 맞는 Toleration을 가진 것은 드라이버 Pod뿐이므로, 그런 Toleration이 없는 Executor는 그 노드에 절대 스케줄될 수 없습니다. Executor는 별도로 노드 셀렉터를 통해 Spot 풀로 보내집니다.
</details>

7. Spot 인스턴스 중단 시 Graceful Decommission(`spark.decommission.enabled`, `spark.storage.decommission.enabled`)이 Spark에게 허용하는 것은 무엇인가요?
   - A) 중단을 취소하고 인스턴스를 계속 실행시킨다
   - B) 중단 통보 시간 동안 셔플 블록과 캐시된 RDD 파티션을 정상 상태의 다른 Executor로 마이그레이션한다
   - C) 잡 전체를 마지막 체크포인트부터 자동으로 재시작한다
   - D) Spot 인스턴스를 자동으로 On-Demand로 전환한다

<details>
<summary>정답 보기</summary>

**정답: B) 중단 통보 시간 동안 셔플 블록과 캐시된 RDD 파티션을 정상 상태의 다른 Executor로 마이그레이션한다**

**설명:**
AWS는 Spot 인스턴스를 회수하기 전에 대략 2분의 중단 통보 시간을 줍니다. Decommission이 활성화되어 있으면 Spark는 이 시간 동안 곧 사라질 Executor의 셔플 블록과 캐시된 RDD 파티션을 다른 정상 Executor로 옮깁니다. 여유 공간을 가진 피어 Executor가 없으면, 설정된 durable/원격 셔플 스토리지로 폴백하거나 해당 태스크를 재계산합니다.
</details>

8. Karpenter와 Spark의 Dynamic Resource Allocation(DRA)의 관계를 가장 잘 설명한 것은 무엇인가요?
   - A) 서로 다른 컴포넌트에서 실행될 뿐, 사실상 동일한 제어 루프다
   - B) DRA는 대기 중인 태스크에 반응해 Executor 파드를 요청/해제하고, Karpenter는 Pending/빈 파드에 반응해 노드를 프로비저닝/회수한다 — 서로 영향을 주는 두 개의 독립적인 루프다
   - C) Karpenter가 Spark가 요청할 Executor 수를 직접 제어한다
   - D) DRA는 Karpenter를 거치지 않고 EC2 노드를 직접 프로비저닝한다

<details>
<summary>정답 보기</summary>

**정답: B) DRA는 대기 중인 태스크에 반응해 Executor 파드를 요청/해제하고, Karpenter는 Pending/빈 파드에 반응해 노드를 프로비저닝/회수한다 — 서로 영향을 주는 두 개의 독립적인 루프다**

**설명:**
DRA는 밑단의 노드 상태를 전혀 모릅니다 — Spark 자신의 태스크 백로그만 보고 Executor 파드를 몇 개 요청할지 결정합니다. Karpenter는 Spark의 태스크 백로그를 전혀 모릅니다 — DRA가 이미 만들어 놓은 파드(또는 비어버린 노드)만 봅니다. 두 루프는 서로 영향을 주지만 각각 별도로 튜닝해야 합니다.
</details>

9. Karpenter의 `consolidateAfter`를 DRA의 `spark.dynamicAllocation.executorIdleTimeout`보다 훨씬 짧게 설정하면 어떤 문제가 발생할 수 있나요?
   - A) Karpenter가 신규 노드를 전혀 프로비저닝하지 않게 된다
   - B) DRA가 아직 해제하지 않은 Executor가 남아 있는 노드를 Karpenter가 통합하려다 Decommission 경로와 충돌할 수 있다
   - C) DRA가 신규 Executor 요청을 완전히 멈춘다
   - D) 드라이버 파드가 축출된다

<details>
<summary>정답 보기</summary>

**정답: B) DRA가 아직 해제하지 않은 Executor가 남아 있는 노드를 Karpenter가 통합하려다 Decommission 경로와 충돌할 수 있다**

**설명:**
DRA가 아직 유휴 Executor를 해제하기로 결정하지 않은 상태에서 Karpenter가 그 노드를 회수하려 하면 두 루프가 충돌합니다. Karpenter의 통합 지연 시간을 DRA의 Executor 유휴 타임아웃보다 다소 길게 잡으면, DRA가 노드를 먼저 비워둔 뒤에 Karpenter가 회수를 시도하게 됩니다.
</details>

10. 이 문서가 드라이버 파드는 크고 안정적으로, Executor 파드는 작게 여러 개로 사이징하라고 하면서도 고정된 수치 기본값을 제시하지 않는 이유는 무엇인가요?
    - A) Kubernetes가 드라이버·Executor 리소스 요청 사이에 고정된 비율을 강제하기 때문
    - B) 적절한 크기는 잡마다 다른 요인(추적하는 상태, 태스크당 작업셋, 셔플 버퍼)에 좌우되고 원 자료에도 범용 수치가 없어, 부하 테스트로 찾아가야 하기 때문
    - C) Spark가 런타임에 최적 크기를 자동으로 계산하기 때문
    - D) 드라이버와 Executor 파드는 항상 동일한 리소스를 요청해야 하기 때문

<details>
<summary>정답 보기</summary>

**정답: B) 적절한 크기는 잡마다 다른 요인(추적하는 상태, 태스크당 작업셋, 셔플 버퍼)에 좌우되고 원 자료에도 범용 수치가 없어, 부하 테스트로 찾아가야 하기 때문**

**설명:**
드라이버가 필요로 하는 메모리는 얼마나 많은 상태(파티션 수, 브로드캐스트 변수, 어큐뮬레이터)를 추적하느냐에 달려 있고, Executor가 필요로 하는 메모리는 태스크당 작업셋 크기와 셔플 설정에 달려 있습니다. 원 자료에 근거가 없는 고정 기본값을 단정하기보다, 실제 잡과 데이터셋으로 부하 테스트를 해서 값을 찾아가는 방식을 제시합니다.
</details>

## 단답형 문제

11. Graceful Decommission을 함께 활성화하는 두 가지 Spark 설정 프로퍼티의 이름을 쓰세요.

<details>
<summary>정답 보기</summary>

**정답: `spark.decommission.enabled=true`와 `spark.storage.decommission.enabled=true`**

**설명:**
두 설정을 함께 켜야 합니다. `spark.decommission.enabled`는 Decommission 메커니즘 자체를 활성화하고, `spark.storage.decommission.enabled`는 종료 그레이스 기간 동안 스토리지(셔플 블록, 캐시된 RDD 파티션)를 다른 Executor로 마이그레이션하는 기능을 구체적으로 활성화합니다.
</details>

12. Graceful Decommission이 활성화되어 있지만 Spot 중단 시 마이그레이션할 셔플 데이터를 받아줄 여유 공간이 있는 피어 Executor가 없다면 어떻게 되나요?

<details>
<summary>정답 보기</summary>

**정답: 설정되어 있다면 durable/원격 셔플 스토리지로 폴백하고, 그렇지 않다면 해당 데이터에 의존하던 태스크가 재계산됩니다.**

**설명:**
Decommission의 마이그레이션 경로는 유입되는 블록을 받아줄 여유 공간을 가진 정상 피어 Executor가 있어야 성립합니다. 그런 Executor가 없으면, 설정된 외부 셔플 스토리지로 폴백하거나(설정이 없다면) 영향받은 태스크를 재계산합니다 — 성능은 저하되지만 잡 전체가 실패하지는 않습니다.
</details>

## 실습 문제

13. 드라이버 Pod가 key `spark-role`, value `driver`인 `NoSchedule` Taint를 Toleration으로 감내하고, `karpenter.sh/capacity-type=on-demand` 레이블이 붙은 노드를 타겟팅하도록 하는 드라이버 Pod 템플릿과 `spark-submit` 설정 프로퍼티를 작성하세요.

<details>
<summary>정답 보기</summary>

**정답:**
```yaml
# driver-pod-template.yaml
apiVersion: v1
kind: Pod
spec:
  tolerations:
    - key: spark-role
      operator: Equal
      value: driver
      effect: NoSchedule
```
```properties
spark.kubernetes.driver.podTemplateFile=driver-pod-template.yaml
spark.kubernetes.driver.node.selector.karpenter.sh/capacity-type=on-demand
```

**설명:**
Spark에는 `spark.kubernetes.*.tolerations.*` 설정 항목이 존재하지 않습니다 — Toleration은 Pod spec 필드이지 평범한 conf 키가 아니므로, Pod 템플릿(`spark.kubernetes.driver.podTemplateFile`)을 통해서, 또는 Spark Operator를 쓴다면 `SparkApplication` CRD의 `spec.driver.tolerations`를 통해 설정해야 합니다. `spark.kubernetes.driver.node.selector.<레이블>`은 노드 셀렉터를 추가해, 드라이버가 On-Demand 노드에 단지 허용되는 것을 넘어 실제로 그쪽을 향하도록 만듭니다.
</details>

14. `spark.local.dir`을 마운트된 NVMe 경로로 지정하는 Spark 설정 프로퍼티를 작성하고, 이것이 동작하려면 Executor 파드 스펙에 왜 `hostPath` 볼륨이 필요한지 한 문장으로 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**
```properties
spark.local.dir=/data/spark-local
```

**설명:**
Spark 쪽 설정은 `spark.local.dir` 하나면 되지만, 이 경로가 실제로 노드의 NVMe 디스크로 뒷받침되려면 파드 스펙에서 호스트의 인스턴스 스토어 마운트 지점(예: `/mnt/k8s-disks/nvme1n1`)을 `/data/spark-local`에 매핑하는 `hostPath` 볼륨이 있어야 합니다. 이 볼륨 마운트가 없으면 `spark.local.dir`은 그냥 루트 EBS 볼륨 위의 일반 컨테이너 파일시스템 공간을 가리키게 됩니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/spark/04-performance-tuning.md)

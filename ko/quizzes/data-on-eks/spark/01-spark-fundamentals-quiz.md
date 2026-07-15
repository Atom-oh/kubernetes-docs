# Spark on Kubernetes 기초 퀴즈

이 퀴즈는 클러스터 모드 제출 방식, 드라이버가 스스로 스케줄러 역할을 하는 이유, Kubernetes에서의 Dynamic Resource Allocation, executor의 정상 종료(graceful decommission)에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Kubernetes에서 `spark-submit`이 지원하는 배포 모드는 무엇인가요?
   - A) 클라이언트 모드만
   - B) 클러스터 모드만
   - C) 클라이언트 모드와 클러스터 모드를 Kubernetes가 자동으로 선택
   - D) 둘 다 지원하지 않으며, 별도의 제출 도구가 필요함

<details>

<summary>정답 보기</summary>

**정답: B) 클러스터 모드만**

**설명:**
Kubernetes에서 `--deploy-mode cluster`로 `spark-submit`을 실행하면, 드라이버는 제출 명령을 실행한 머신이 아니라 클러스터 내부의 Pod에서 실행됩니다. 클라이언트 모드도 Kubernetes에서 존재하지만, 주로 드라이버가 클러스터 외부에서 실행되어야 하는 spark-shell이나 노트북 같은 대화형 도구에 사용됩니다.
</details>

2. `spark-submit`이 드라이버 Pod를 생성한 이후, executor Pod는 누가 생성하나요?
   - A) YARN의 ResourceManager와 유사한 별도의 Spark 클러스터 매니저 데몬
   - B) Spark 쪽의 별도 요청 없이 Kubernetes 스케줄러가 자동으로 생성
   - C) 드라이버 Pod 스스로가 Kubernetes API를 호출해서 생성
   - D) `spark-submit` 클라이언트 프로세스가 종료되기 전에 생성

<details>

<summary>정답 보기</summary>

**정답: C) 드라이버 Pod 스스로가 Kubernetes API를 호출해서 생성**

**설명:**
드라이버 Pod가 실행되면 스스로 스케줄러 역할을 수행합니다. `spark.executor.instances` 또는 Dynamic Resource Allocation을 기준으로, 드라이버가 직접 Kubernetes API 서버에 요청을 보내 필요한 executor Pod를 생성합니다. 이는 상시 실행 중인 ResourceManager와 노드별 NodeManager가 컨테이너를 협상해 배분하는 YARN과의 핵심적인 아키텍처 차이입니다.
</details>

3. Spark를 Kubernetes 위에서 운영할 때 YARN과 비교해 얻게 되는 운영상의 단순화는 무엇인가요?
   - A) 드라이버 프로세스 자체가 필요 없어진다
   - B) ResourceManager/NodeManager 같은 별도의 상시 실행 Spark 클러스터 매니저 데몬을 설치하고 유지 관리할 필요가 없어진다
   - C) executor가 드라이버에 상태를 보고할 필요가 없어진다
   - D) 작업당 메모리 사용량이 항상 줄어드는 것이 보장된다

<details>

<summary>정답 보기</summary>

**정답: B) ResourceManager/NodeManager 같은 별도의 상시 실행 Spark 클러스터 매니저 데몬을 설치하고 유지 관리할 필요가 없어진다**

**설명:**
YARN에서는 작업 제출 시 상시 실행 중인 ResourceManager가 노드별 NodeManager 데몬으로부터 컨테이너를 협상해야 합니다. Kubernetes에서는 다른 모든 워크로드를 위해 이미 운영 중인 동일한 Kubernetes 컨트롤 플레인이 Spark의 드라이버·executor Pod를 직접 스케줄링하므로, Spark 전용의 별도 클러스터 매니저 프로세스가 필요 없습니다. 그 대신 스케줄링/할당 책임이 드라이버 Pod 자신에게 넘어간다는 트레이드오프가 있습니다.
</details>

4. Kubernetes에서 Dynamic Resource Allocation이 안전하게 동작하려면 `spark.dynamicAllocation.enabled=true`뿐 아니라 `spark.dynamicAllocation.shuffleTracking.enabled=true`도 함께 필요한 이유는 무엇인가요?
   - A) Kubernetes에는 External Shuffle Service(ESS) 데몬이 없기 때문에, 아직 필요한 셔플 블록을 들고 있는 executor를 스케일 다운이 제거하지 못하도록 셔플 트래킹이 막아준다
   - B) 이 설정이 없으면 `spark.dynamicAllocation.enabled` 자체가 아무 효과도 내지 않기 때문이다
   - C) 각 executor의 메모리 사용량을 줄여주기 때문이다
   - D) 클라이언트 모드에서만 필요한 설정이기 때문이다

<details>

<summary>정답 보기</summary>

**정답: A) Kubernetes에는 External Shuffle Service(ESS) 데몬이 없기 때문에, 아직 필요한 셔플 블록을 들고 있는 executor를 스케일 다운이 제거하지 못하도록 셔플 트래킹이 막아준다**

**설명:**
YARN에서는 NodeManager가 호스팅하는 External Shuffle Service가 셔플 데이터를 만든 executor가 제거된 뒤에도 해당 블록을 계속 서빙할 수 있습니다. Kubernetes에는 이에 대응하는 내장 데몬이 없습니다. 셔플 트래킹(Spark 3.3.0부터 안정화)은 다른 작업이 아직 필요로 하는 셔플 블록을 어떤 executor가 들고 있는지를 Spark의 스케일 다운 로직이 알 수 있게 해줘서, 그 블록이 더 이상 필요 없어지거나 작업이 끝날 때까지 해당 executor를 제거하지 않도록 합니다.
</details>

5. Spark의 정상 종료(graceful decommission) 기능(`spark.decommission.enabled` + `spark.storage.decommission.enabled`)은 무엇을 보호하기 위한 기능인가요?
   - A) executor Pod 생성 과정에서 Kubernetes API 서버가 병목이 되는 것을 막는다
   - B) Pod가 종료되기 전에 캐시된 RDD 블록과 셔플 블록을 다른 executor로 이전시켜, 데이터가 그대로 사라지는 것을 막는다
   - C) 드라이버 Pod가 크래시되면 자동으로 재시작시킨다
   - D) 클러스터 전체의 `terminationGracePeriodSeconds` 값을 자동으로 늘려준다

<details>

<summary>정답 보기</summary>

**정답: B) Pod가 종료되기 전에 캐시된 RDD 블록과 셔플 블록을 다른 executor로 이전시켜, 데이터가 그대로 사라지는 것을 막는다**

**설명:**
노드 스케일 다운, Spot 인스턴스 중단, 롤링 업그레이드 등으로 Pod에 종료 신호가 전달되면, Kubernetes는 강제 종료 전에 유예 시간(`terminationGracePeriodSeconds`, 기본값 30초)을 부여합니다. 정상 종료 기능이 켜져 있으면 Spark는 이 시간 동안 캐시된 RDD 블록과 셔플 블록을 다른 정상 executor로 이전시켜 데이터를 그대로 잃어버리지 않도록 하며, 이를 통해 작업 전체 실패로 이어질 상황을 제한적이고 복구 가능한 이벤트로 바꿔줍니다.
</details>

6. Pod의 `terminationGracePeriodSeconds` 기본값은 몇 초이며, 이 시간이 정상 종료 기능이 블록을 이전할 수 있는 시간을 제한하나요?
   - A) 10초
   - B) 30초
   - C) 60초
   - D) 5분

<details>

<summary>정답 보기</summary>

**정답: B) 30초**

**설명:**
Kubernetes의 `terminationGracePeriodSeconds` 기본값은 30초입니다. 이 시간 동안 Spark의 정상 종료 기능이 캐시된 RDD 블록과 셔플 블록을 다른 executor로 이전할 수 있으며, 이 시간이 지나면 Pod는 강제로 종료됩니다. 이전 시간이 더 필요한 작업이라면 executor Pod 템플릿에서 이 값을 늘려 정상 종료가 작동할 시간을 더 확보할 수 있습니다.
</details>

7. Dynamic Resource Allocation이 확장(scale-up)될 때, 드라이버가 Kubernetes API에 한 번에 보내는 executor Pod 생성 요청 수를 제어하는 설정은 무엇인가요?
   - A) `spark.dynamicAllocation.maxExecutors`
   - B) `spark.executor.instances`
   - C) `spark.kubernetes.allocation.batch.size`
   - D) `spark.dynamicAllocation.shuffleTracking.enabled`

<details>

<summary>정답 보기</summary>

**정답: C) `spark.kubernetes.allocation.batch.size`**

**설명:**
`spark.kubernetes.allocation.batch.size`는 드라이버가 Kubernetes API에 executor Pod 생성 요청을 얼마나 공격적으로 보낼지를 제어합니다. 이 값을 너무 높게 설정하면 Pod 생성 요청이 한꺼번에 몰려 API와 노드 그룹의 오토스케일링에 부담을 줄 수 있습니다. `minExecutors`/`maxExecutors`는 전체 하한/상한을 정할 뿐, 요청을 배치로 묶어 보내는 방식은 제어하지 않습니다.
</details>

## 단답형 문제

8. Kubernetes 클러스터 모드에서, YARN의 상시 실행 ResourceManager가 하던 역할을 드라이버 Pod가 어떻게 대신하나요?

<details>

<summary>정답 보기</summary>

**정답: 드라이버 Pod가 스스로 스케줄러 역할을 수행합니다.**

**설명:**
YARN의 ResourceManager처럼 컨테이너를 협상해 배분하는 별도의 상시 실행 클러스터 매니저 프로세스 없이, Spark 드라이버 Pod가 직접 Kubernetes API에 요청을 보내 필요한 executor Pod를 생성하고, 어떤 executor가 살아 있는지 추적하며, executor가 실패하면 대체 Pod를 요청합니다. 이는 운영해야 할 인프라 계층을 하나 줄여주지만, 드라이버 Pod의 API 접근 권한이 작업 전체의 성패를 좌우하는 요소가 됩니다.
</details>

9. 셔플 트래킹이 켜져 있지 않으면 Kubernetes에서 Dynamic Resource Allocation이 유휴 상태처럼 보이는 executor를 안전하게 제거할 수 없는 이유는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: 그 executor가 다른, 아직 끝나지 않은 작업이 읽어야 할 셔플 블록을 여전히 들고 있을 수 있는데, Kubernetes에는 executor가 사라진 뒤에도 그 블록을 계속 서빙해 줄 External Shuffle Service가 없기 때문입니다.**

**설명:**
YARN에서는 NodeManager가 호스팅하는 External Shuffle Service가 executor의 생명주기와 무관하게 셔플 블록을 계속 서빙할 수 있어, 유휴 executor를 제거해도 안전합니다. Kubernetes에는 이런 데몬이 없기 때문에, DRA가 다른 작업이 의존하는 셔플 블록을 들고 있는 executor를 제거하면 그 블록은 사라지고 의존하던 작업은 실패해 재계산이 강제됩니다. `spark.dynamicAllocation.shuffleTracking.enabled=true`는 필요한 셔플 데이터를 들고 있는 executor를 Spark가 추적하게 함으로써, 회수 가능한 상태가 될 때까지 제거를 미루도록 하여 이 문제를 해결합니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/spark/01-spark-fundamentals.md)

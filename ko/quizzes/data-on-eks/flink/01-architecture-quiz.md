# Kubernetes에서의 Flink 아키텍처 퀴즈

이 퀴즈는 JobManager/TaskManager 클러스터 모델, Flink의 세 가지 배포 모드, 네이티브 Kubernetes 배포와 Standalone-on-Kubernetes의 차이에 대한 이해도를 테스트합니다.

## 객관식 문제

1. 잡 그래프를 구성하고, 체크포인트를 조율하며, TaskManager에 작업을 스케줄링하는 역할을 담당하는 컴포넌트는 무엇인가요?
   - A) TaskManager
   - B) JobManager
   - C) Kubernetes ResourceManager(kube-scheduler)
   - D) Task Slot

<details>

<summary>정답 보기</summary>

**정답: B) JobManager**

**설명:**
JobManager는 Flink 클러스터의 컨트롤 플레인입니다. 제출된 애플리케이션으로부터 잡 그래프를 구성하고, 분산 체크포인트를 조율하며, 가용한 TaskManager의 태스크 슬롯에 오퍼레이터 서브태스크를 스케줄링하고, REST API와 웹 UI를 제공합니다. 반면 TaskManager는 스케줄링된 서브태스크를 실제로 실행하는 워커 프로세스입니다.

</details>

2. Flink의 "태스크 슬롯(task slot)"은 무엇을 의미하나요?
   - A) TaskManager 간 셔플 트래픽을 위해 예약된 전용 네트워크 포트
   - B) 한 번에 정확히 하나의 오퍼레이터 서브태스크를 위해 예약된, TaskManager 자원의 고정된 단위
   - C) 영구 디스크에 있는 체크포인트 저장 위치
   - D) JobManager만을 위해 예약된 Kubernetes 노드

<details>

<summary>정답 보기</summary>

**정답: B) 한 번에 정확히 하나의 오퍼레이터 서브태스크를 위해 예약된, TaskManager 자원의 고정된 단위**

**설명:**
각 TaskManager는 하나 이상의 태스크 슬롯을 제공하며, 각 슬롯은 오퍼레이터 서브태스크의 병렬 인스턴스 하나를 실행하기 위해 예약된 TaskManager 자원(주로 메모리)의 고정된 몫입니다. 슬롯이 4개인 TaskManager는 최대 4개의 서브태스크를 동시에 실행할 수 있습니다.

</details>

3. 프로덕션 환경에서 Kubernetes 위의 Flink 워크로드에 Application Mode가 기본값으로 권장되는 이유는 무엇인가요?
   - A) 모든 경우에 Session Mode보다 메모리를 적게 사용하기 때문에
   - B) 잡마다 전용 클러스터를 부여하여 다른 잡으로부터 완전한 자원 격리와 펜싱을 제공하기 때문에
   - C) 체크포인팅을 지원하는 유일한 모드이기 때문에
   - D) JobManager 자체가 필요 없어지기 때문에

<details>

<summary>정답 보기</summary>

**정답: B) 잡마다 전용 클러스터를 부여하여 다른 잡으로부터 완전한 자원 격리와 펜싱을 제공하기 때문에**

**설명:**
Application Mode에서는 잡마다 전용 클러스터가 생성되고, 잡의 `main()`이 JobManager 내부에서 직접 실행됩니다. 이는 각 잡이 자신만의 JobManager와 TaskManager Pod를 갖는다는 의미이며, 문제를 일으키거나 자원을 과다하게 사용하는 잡이 다른 잡의 클러스터를 굶기거나 불안정하게 만들 수 없습니다. 여러 Flink 워크로드를 함께 운영하는 공유 EKS 클러스터에서는 이 특성이 특히 중요합니다.

</details>

4. Session Mode와 Application Mode의 핵심적인 운영상 차이는 무엇인가요?
   - A) Session Mode는 Kubernetes에서 전혀 실행될 수 없다
   - B) Session Mode는 하나의 공유된 장수명 클러스터에서 여러 잡을 실행하며, 격리 수준을 낮추는 대신 잡당 시작 지연시간을 줄인다
   - C) Session Mode는 Application Mode와 달리 별도의 ZooKeeper 앙상블이 필요하다
   - D) Session Mode는 배치 잡만 지원하며 스트리밍 잡은 지원하지 않는다

<details>

<summary>정답 보기</summary>

**정답: B) Session Mode는 하나의 공유된 장수명 클러스터에서 여러 잡을 실행하며, 격리 수준을 낮추는 대신 잡당 시작 지연시간을 줄인다**

**설명:**
Session Mode는 이미 존재하며 계속 실행 중인 클러스터에 잡을 독립적으로 제출하므로, 새 잡은 클러스터 시작 오버헤드를 피할 수 있습니다. 그 대신 여러 잡이 같은 JobManager를 공유하고 동일한 TaskManager 풀을 두고 경쟁하게 되어, 하나의 시끄러운 잡이 세션 클러스터 전체에 영향을 줄 수 있습니다 — Application Mode의 잡 단위 격리와는 대조적입니다.

</details>

5. Kubernetes 위의 Flink에서 Per-Job Mode가 어디에서도 권장되지 않는 이유는 무엇인가요?
   - A) Flink 2.0에서 Session Mode로 통합되었기 때문에
   - B) 네이티브 Kubernetes 배포에서 지원되지 않아 EKS에서는 사실상 사용할 수 없기 때문에
   - C) 잡마다 최소 10개의 TaskManager가 필요하기 때문에
   - D) 레거시 ZooKeeper 기반 JobManager에서만 동작하기 때문에

<details>

<summary>정답 보기</summary>

**정답: B) 네이티브 Kubernetes 배포에서 지원되지 않아 EKS에서는 사실상 사용할 수 없기 때문에**

**설명:**
Per-Job Mode는 클라이언트가 로컬에서 `main()`을 실행해 미리 만들어진 잡 그래프를 전용 클러스터에 제출하는 레거시 모드입니다. 네이티브 Kubernetes 배포는 이 모드를 처음부터 구현하지 않았기 때문에, Kubernetes/EKS에서는 선택할 수 있는 옵션 자체가 아닙니다. Application Mode는 레거시 클라이언트 측 제출 방식 없이도 동일한 잡 단위 격리 목표를 달성합니다.

</details>

6. 네이티브 Kubernetes 배포에서 TaskManager Pod를 동적으로 요청하고 반환하는 역할을 담당하는 컴포넌트는 무엇인가요?
   - A) Flink의 개입 없이 동작하는 Kubernetes Cluster Autoscaler 단독
   - B) 모든 노드에서 실행되는 DaemonSet
   - C) JobManager 내부에서 실행되는 Kubernetes ResourceManager 통합
   - D) 5분마다 잡 병렬도를 확인하는 cron job

<details>

<summary>정답 보기</summary>

**정답: C) JobManager 내부에서 실행되는 Kubernetes ResourceManager 통합**

**설명:**
네이티브 Kubernetes 배포에서는 JobManager 내부의 Kubernetes ResourceManager가 Kubernetes API 서버와 직접 통신하여, 더 많은 태스크 슬롯이 필요할 때 새로운 TaskManager Pod를 요청하고, 잡의 병렬도가 줄거나 잡이 종료되면 해당 Pod를 반환합니다. 이것이 네이티브 모드를 Standalone-on-Kubernetes와 달리 탄력적으로 만드는 핵심입니다.

</details>

7. 네이티브 Kubernetes 배포와 Standalone-on-Kubernetes의 근본적인 차이는 무엇인가요?
   - A) Standalone-on-Kubernetes는 체크포인팅을 지원하지 않는다
   - B) 네이티브 배포는 Flink 자체의 ResourceManager를 통해 TaskManager Pod를 동적으로 요청/반환하는 반면, Standalone-on-Kubernetes는 일반 Deployment/YAML 매니페스트로 정의된 고정된 개수의 Pod를 실행한다
   - C) 네이티브 배포는 Session Mode에서만 동작한다
   - D) Standalone-on-Kubernetes는 배치 워크로드에만 사용된다

<details>

<summary>정답 보기</summary>

**정답: B) 네이티브 배포는 Flink 자체의 ResourceManager를 통해 TaskManager Pod를 동적으로 요청/반환하는 반면, Standalone-on-Kubernetes는 일반 Deployment/YAML 매니페스트로 정의된 고정된 개수의 Pod를 실행한다**

**설명:**
네이티브 Kubernetes 배포는 Flink가 Kubernetes를 직접 인식하고 제어할 수 있게 해주어, JobManager가 TaskManager Pod 개수를 탄력적으로 조절할 수 있습니다. Standalone-on-Kubernetes는 이러한 통합이 나오기 전부터 존재한 방식으로, JobManager와 TaskManager를 고정된 개수의 일반 컨테이너로 그냥 실행하며 동적인 자원 요청이 없어, TaskManager 개수를 바꾸려면 YAML을 직접 수정해야 합니다.

</details>

8. Part 2에서 다룰 Flink Kubernetes Operator는 무엇을 기반으로 구축되나요?
   - A) 고정된 Pod 개수가 필요한 Standalone-on-Kubernetes
   - B) Per-Job Mode의 클라이언트 측 제출 모델
   - C) 네이티브 Kubernetes 배포 위에 `FlinkDeployment`, `FlinkSessionJob` 같은 CRD 계층을 추가해 선언적 라이프사이클 관리를 제공
   - D) JobManager를 완전히 우회하는 독립적인 스케줄러

<details>

<summary>정답 보기</summary>

**정답: C) 네이티브 Kubernetes 배포 위에 `FlinkDeployment`, `FlinkSessionJob` 같은 CRD 계층을 추가해 선언적 라이프사이클 관리를 제공**

**설명:**
Flink Kubernetes Operator는 네이티브 Kubernetes 배포의 동적 자원 할당 위에 구축됩니다. Kubernetes 네이티브 커스텀 리소스(`FlinkDeployment`는 Application/Session 클러스터용, `FlinkSessionJob`은 세션 클러스터에 제출되는 잡용)를 추가하여, 수동으로 `flink run` 명령을 실행하는 대신 클러스터 라이프사이클, 업그레이드, 세이브포인트 기반 재배포를 선언적으로 관리할 수 있게 합니다.

</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/flink/01-architecture.md)

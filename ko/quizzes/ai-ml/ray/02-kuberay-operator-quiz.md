# KubeRay 오퍼레이터 퀴즈

이 퀴즈는 KubeRay가 무엇인지, 세 가지 핵심 CRD, Karpenter와 함께 동작하는 2단계 오토스케일링 모델, 그리고 GPU 스케줄링 처리 방식에 대한 이해를 확인합니다.

## 객관식 문제

1. KubeRay는 무엇입니까?
   - A) Ray 클러스터를 실행하기 위한 AWS 관리형 서비스
   - B) Ray 클러스터를 Kubernetes 네이티브 커스텀 리소스로 관리하며, head/워커 노드 형태를 Pod, Service, 관련 오브젝트로 변환해 주는 Kubernetes 오퍼레이터
   - C) kubectl을 대체하는 Ray 전용 CLI
   - D) 클러스터 관리 기능이 전혀 없는, Ray 클러스터를 위한 모니터링 대시보드

<details>

<summary>정답 보기</summary>

**정답: B) Ray 클러스터를 Kubernetes 네이티브 커스텀 리소스로 관리하며, head/워커 노드 형태를 Pod, Service, 관련 오브젝트로 변환해 주는 Kubernetes 오퍼레이터**

**설명:**
KubeRay는 "Kubernetes 위의 Ray"를 Pod 스펙을 손으로 작성하는 대신 선언적으로 만들어 주는 요소입니다. 선언된 RayCluster/RayJob/RayService 스펙을 Kubernetes가 필요로 하는 실제 Pod, Service, 기타 오브젝트로 재조정합니다.
</details>

2. head Pod 하나와 하나 이상의 워커 그룹으로 구성된 순수한 Ray 클러스터를 나타내는 CRD는 무엇입니까?
   - A) RayJob
   - B) RayService
   - C) RayCluster
   - D) RayNodePool

<details>

<summary>정답 보기</summary>

**정답: C) RayCluster**

**설명:**
RayCluster는 가장 기본이 되는 CRD로, head Pod 하나와 하나 이상의 워커 그룹(예: CPU 워커 그룹과 별도의 GPU 워커 그룹처럼 동질적인 워커 Pod의 집합)으로 구성되며, 오퍼레이터가 원하는 스펙에 맞춰 재조정합니다.
</details>

3. RayJob이 일회성 또는 스케줄링된 배치 워크로드에 적합한 이유는 무엇입니까?
   - A) 이미 존재하는, 계속 실행 중인 RayCluster에서만 동작할 수 있기 때문
   - B) RayCluster를 생성하고, 제출된 작업을 실행하고, 작업이 끝나면 클러스터를 정리할 수 있어 실행 사이에 클러스터가 유휴 상태로 남지 않기 때문
   - C) Ray 오토스케일러를 완전히 비활성화하기 때문
   - D) 먼저 별도의 RayService가 실행되고 있어야 하기 때문

<details>

<summary>정답 보기</summary>

**정답: B) RayCluster를 생성하고, 제출된 작업을 실행하고, 작업이 끝나면 클러스터를 정리할 수 있어 실행 사이에 클러스터가 유휴 상태로 남지 않기 때문**

**설명:**
RayJob은 배치 작업을 제출하며, 선택적으로 클러스터 생성·작업 실행·정리까지 이어지는 전체 생명주기를 관리할 수 있습니다. 이로써 실행 사이에 유휴 클러스터에 비용을 지불하는 상황을 피할 수 있습니다.
</details>

4. RayService가 RayCluster와 다른 점은 무엇입니까?
   - A) RayService는 어떤 Ray Serve 애플리케이션도 실행할 수 없다
   - B) RayService는 RayCluster와 그 위에 배포된 Ray Serve 애플리케이션을 함께 관리하며, 무중단 롤링 업그레이드를 지원한다
   - C) RayService는 워커 그룹 없이 단일 Pod로만 동작한다
   - D) RayService는 RayCluster로 대체되어 더 이상 쓰이지 않는다

<details>

<summary>정답 보기</summary>

**정답: B) RayService는 RayCluster와 그 위에 배포된 Ray Serve 애플리케이션을 함께 관리하며, 무중단 롤링 업그레이드를 지원한다**

**설명:**
RayService는 프로덕션 모델 서빙을 목표로 하며, RayCluster와 그 위에 배포된 Ray Serve 애플리케이션을 함께 관리합니다. 또한 무중단을 목표로 하는 롤링 업그레이드도 지원합니다 — 이 업그레이드 경로의 성숙도는 실제로 의존하기 전에 현재 KubeRay 릴리스 노트에서 확인하세요.
</details>

5. EKS 위의 Ray에 적용되는 2단계 오토스케일링 패턴에서, Ray 오토스케일러는 무엇을 결정하고 Karpenter는 무엇을 결정합니까?
   - A) Ray 오토스케일러는 EC2 노드 타입을 결정하고, Karpenter는 Ray 태스크 배치를 결정한다
   - B) Ray 오토스케일러는 (RayCluster 워커 그룹의 replica 수를 조정해) 몇 개의 Ray 워커 Pod가 필요한지 결정하고, Karpenter는 그 결과로 생긴 Pending Pod를 위해 몇 개의 EC2 노드를 프로비저닝할지 결정한다
   - C) 두 제어 루프는 내결함성을 위해 중복으로 동일한 것을 결정한다
   - D) Karpenter가 Pod 개수를 결정하고, Ray 오토스케일러가 노드 개수를 결정한다

<details>

<summary>정답 보기</summary>

**정답: B) Ray 오토스케일러는 (RayCluster 워커 그룹의 replica 수를 조정해) 몇 개의 Ray 워커 Pod가 필요한지 결정하고, Karpenter는 그 결과로 생긴 Pending Pod를 위해 몇 개의 EC2 노드를 프로비저닝할지 결정한다**

**설명:**
하나의 제어 루프(KubeRay를 통해 조율되는 Ray 오토스케일러)는 Pod 개수를 담당하고, 다른 하나(Karpenter, 또는 Kubernetes Cluster Autoscaler)는 노드 개수를 담당합니다. 이 둘은 오직 평범한 Pending Pod 스케줄링 상태를 통해서만 간접적으로 소통합니다 — 이 문서 사이트가 Flink와 Katib에 대해 설명하는 것과 동일한 2단계 패턴입니다.
</details>

6. Ray 오토스케일러의 `idleTimeoutSeconds` 설정은 무엇을 제어하며, 기본값은 얼마입니까?
   - A) KubeRay 오퍼레이터가 CRD를 설치하기 전 대기하는 시간; 기본값 60초
   - B) 워커 Pod가 태스크·액터·참조된 오브젝트 없이 유휴 상태로 머물러야 오토스케일러가 스케일 다운하는 대기 시간; 기본값 60초
   - C) Karpenter가 새 EC2 노드를 프로비저닝하기 전 대기하는 시간; 기본값 60초
   - D) 완료된 RayJob의 head Pod에 대한 TTL; 기본값 60초

<details>

<summary>정답 보기</summary>

**정답: B) 워커 Pod가 태스크·액터·참조된 오브젝트 없이 유휴 상태로 머물러야 오토스케일러가 스케일 다운하는 대기 시간; 기본값 60초**

**설명:**
`idleTimeoutSeconds`의 기본값은 60초이며, Ray 오토스케일러가 유휴 워커 Pod를 스케일 다운하기 전에 기다리는 시간입니다.
</details>

7. KubeRay는 워커 그룹의 Ray 프로세스가 인식하는 GPU 개수를 어떻게 결정합니까?
   - A) RayCluster 스펙의 최상위 메타데이터에 있는 별도의 `numGPUs` 필드를 읽는다
   - B) 워커 그룹의 Pod 스펙에 설정된 GPU 리소스 limit(예: `nvidia.com/gpu`)을 읽어 Ray 스케줄러와 오토스케일러에 알리고, Ray 프로세스의 `--num-gpus` 플래그를 그에 맞춰 자동으로 설정한다
   - C) Pod가 시작된 후 별도의 `kubectl ray gpu-config` 명령으로 수동 설정해야 한다
   - D) Pod 스펙과 무관하게 KubeRay는 항상 워커 Pod당 정확히 GPU 1개를 가정한다

<details>

<summary>정답 보기</summary>

**정답: B) 워커 그룹의 Pod 스펙에 설정된 GPU 리소스 limit(예: `nvidia.com/gpu`)을 읽어 Ray 스케줄러와 오토스케일러에 알리고, Ray 프로세스의 `--num-gpus` 플래그를 그에 맞춰 자동으로 설정한다**

**설명:**
GPU 워커 그룹의 Pod 스펙은 단 하나의 소스 오브 트루스입니다. KubeRay는 컨테이너의 GPU 리소스 limit을 Ray 스케줄러와 오토스케일러 모두에게 알리고, Ray 프로세스의 `--num-gpus`를 그에 맞춰 설정하므로 GPU 개수를 별도로 맞춰 관리할 곳이 없습니다.
</details>

8. 이 문서에 따르면 KubeRay 오퍼레이터를 설치하는 표준적인 방법은 무엇입니까?
   - A) 임의의 GitHub gist에서 내려받은 원시 매니페스트를 수동으로 적용
   - B) `helm repo add kuberay https://ray-project.github.io/kuberay-helm/`로 추가하는 공식 Helm 차트
   - C) 한 줄짜리 `kubectl create clusterrole kuberay` 명령
   - D) 지원되는 설치 방법은 없으며 KubeRay는 소스에서 직접 빌드해야 한다

<details>

<summary>정답 보기</summary>

**정답: B) `helm repo add kuberay https://ray-project.github.io/kuberay-helm/`로 추가하는 공식 Helm 차트**

**설명:**
`ray-project/kuberay-helm` 저장소는 KubeRay 오퍼레이터와 그 컨트롤러, 그리고 RayCluster/RayJob/RayService CRD를 설치하는 공식 Helm 차트를 호스팅합니다.
</details>

## 서술형 문제

9. KubeRay가 제공하는 세 가지 핵심 CRD의 이름을 말하고, 각각 무엇을 위해 쓰이는지 간단히 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
- RayCluster: head Pod 하나와 하나 이상의 워커 그룹으로 구성된 순수한 Ray 클러스터로, 선언된 스펙에 맞춰 재조정된다.
- RayJob: Ray 클러스터에 배치 작업을 제출하며, 선택적으로 일회성/스케줄링 워크로드를 위해 생성-실행-정리로 이어지는 클러스터 전체 생명주기를 관리한다.
- RayService: 프로덕션 모델 서빙을 위해 RayCluster와 그 위의 Ray Serve 애플리케이션을 함께 관리하며, 무중단 롤링 업그레이드를 지원한다.

**설명:**
각 CRD는 동일한 재조정 모델을 기반으로 하면서도 순수 클러스터 관리, 배치 작업 실행, 프로덕션 서빙이라는 서로 다른 사용 패턴을 겨냅니다.
</details>

10. EKS 위의 Ray 오토스케일링이 하나가 아니라 두 개의 별도 제어 루프를 필요로 하는 이유를 설명하고, 각 루프가 무엇을 담당하는지 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
Ray 오토스케일러는 Ray 수준의 상태(대기 중인 태스크와 액터)는 이해하지만 EC2 용량에 대해서는 전혀 모릅니다. Karpenter는 Kubernetes 수준의 Pending Pod와 EC2 프로비저닝은 이해하지만 Ray 태스크나 액터에 대해서는 전혀 모릅니다. Ray 오토스케일러는 몇 개의 Ray 워커 Pod가 필요한지 결정하고 RayCluster 워커 그룹의 replica 수를 통해 요청하며, Karpenter는 그 결과로 생긴 Pending Pod에 별도로 반응해 이를 실행할 EC2 노드를 프로비저닝합니다.

**설명:**
서로 다른 정보를 기반으로 동작하기 때문에 어느 한 루프도 다른 루프를 대신할 수 없습니다. Pod 개수는 한 루프가, 노드 개수는 다른 루프가 맡고 오직 평범한 Kubernetes 스케줄링 상태로만 소통하는 이 2단계 구조는, 이 문서 사이트가 Flink와 Katib의 오토스케일링을 설명할 때 쓰는 것과 동일한 패턴입니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/ray/02-kuberay-operator.md) | [다음 퀴즈: Ray Train and Tune](./03-ray-train-tune-quiz.md)

# Ray Serve 퀴즈

이 퀴즈는 Ray Serve의 deployment 모델, Ray Serve LLM, Serve 수준의 autoscaling, GPU 추론, 그리고 RayService가 EKS에서 프로덕션 Serve application을 관리하는 방식에 대한 이해를 확인합니다.

## 객관식 문제

1. Ray Serve의 라우팅 계층 아래에서 deployment는 실제로 무엇으로 구현됩니까?
   - A) Ray의 핵심 프리미티브와 아무 관련 없는 독립 컨테이너
   - B) Ray Serve가 HTTP/gRPC 요청을 라우팅하는 대상인 Ray actor, 또는 actor replica 그룹
   - C) 고정된 스케줄로 실행되는 Kubernetes CronJob
   - D) 들어오는 요청마다 다시 실행되는 단일 Ray task

<details>

<summary>정답 보기</summary>

**정답: B) Ray Serve가 HTTP/gRPC 요청을 라우팅하는 대상인 Ray actor, 또는 actor replica 그룹**

**설명:**
Ray Serve는 Ray의 actor 프리미티브 위에 직접 만들어졌습니다. deployment는 actor 하나 또는 actor replica 그룹이며, Ray Serve는 들어오는 HTTP/gRPC 요청을 그 replica들로 라우팅합니다. 이 때문에 replica 메모리에 한 번 로드된 모델은 다시 로드하지 않고도 여러 요청에 응답할 수 있습니다.
</details>

2. Ray Serve에서 "application"이란 무엇입니까?
   - A) 스케일이 불가능한 단일 deployment
   - B) 전처리 deployment가 모델 추론 deployment로 결과를 넘기는 것처럼, 하나 이상의 deployment가 조합되어 만들어지는 서빙 파이프라인
   - C) 한 번 실행되고 스스로 종료되는 RayJob
   - D) RayCluster가 실행되는 Kubernetes 네임스페이스

<details>

<summary>정답 보기</summary>

**정답: B) 전처리 deployment가 모델 추론 deployment로 결과를 넘기는 것처럼, 하나 이상의 deployment가 조합되어 만들어지는 서빙 파이프라인**

**설명:**
Ray Serve는 전처리 단계가 그 출력을 모델 추론 단계로 넘기는 것처럼, 여러 deployment를 application이라 부르는 하나의 서빙 파이프라인으로 조합할 수 있게 해줍니다. 파이프라인의 각 deployment는 여전히 독립적으로 스케일, 버전 관리, 리소스 배정이 가능합니다.
</details>

3. `ray.serve.llm`은 무엇이며, 지원 추론 엔진으로 어떤 엔진을 문서화하고 있습니까?
   - A) LLM과 관련이 없는 범용 배치 처리 모듈이며, 어떤 엔진이든 지원한다
   - B) Ray Serve의 일반적인 deployment 모델 위에 세워진, LLM 서빙을 위한 전용 빌딩 블록으로, 지원 추론 엔진으로 vLLM을 문서화하고 있다
   - C) actor를 사용하지 않는, Ray Serve를 대체하는 모듈
   - D) LLM 서빙이 아니라 학습만을 위한 모듈

<details>

<summary>정답 보기</summary>

**정답: B) Ray Serve의 일반적인 deployment 모델 위에 세워진, LLM 서빙을 위한 전용 빌딩 블록으로, 지원 추론 엔진으로 vLLM을 문서화하고 있다**

**설명:**
`ray.serve.llm`은 Ray Serve의 일반적인 deployment 모델 위에 계층화된, LLM 서빙 패턴에 특화된 더 높은 수준의 구성 요소를 제공합니다. 지원 추론 엔진으로 vLLM을 문서화하고 있으며, vLLM 자체의 OpenAI 호환 서버와 최대한 맞춰서 설계된 OpenAI 호환 API를 제공합니다.
</details>

4. Ray Serve 자체의 autoscaler는 무엇을 결정하며, 그 결정을 위해 무엇을 비교합니까?
   - A) 결제 데이터를 기준으로 Karpenter가 프로비저닝할 EC2 노드 수
   - B) replica당 진행 중인 요청 수(대기 중 + 처리 중)를 목표값과 비교해, 특정 deployment에 필요한 actor replica 수
   - C) 대기 중인 task 배치를 기준으로 RayCluster에 필요한 worker Pod 수
   - D) RayCluster를 배포할 AWS 리전

<details>

<summary>정답 보기</summary>

**정답: B) replica당 진행 중인 요청 수(대기 중 + 처리 중)를 목표값과 비교해, 특정 deployment에 필요한 actor replica 수**

**설명:**
Ray Serve의 autoscaler는 클러스터 수준 autoscaling과는 별개의 계층입니다. replica당 진행 중인 요청 수를 목표값과 비교해, 설정된 최소·최대 범위 안에서 해당 deployment의 replica 수를 늘리거나 줄입니다.
</details>

5. EKS에서 실행되는 Ray Serve application의 3단계 autoscaling 구조에서, Karpenter 바로 위에 있는 계층은 무엇입니까?
   - A) AWS Load Balancer Controller
   - B) 대기 중인 actor 배치를 기준으로 worker Pod 수를 결정하는 Ray/KubeRay autoscaler
   - C) CPU 사용률을 감시하는 별도의 Kubernetes Horizontal Pod Autoscaler
   - D) 요청을 보내는 클라이언트 애플리케이션 자체

<details>

<summary>정답 보기</summary>

**정답: B) 대기 중인 actor 배치를 기준으로 worker Pod 수를 결정하는 Ray/KubeRay autoscaler**

**설명:**
3단계 구조는 다음과 같습니다. Ray Serve의 autoscaler가 replica 수를 결정하고, Ray/KubeRay autoscaler가 (Serve autoscaler가 요청한 replica를 포함한) 대기 중인 actor 배치를 기준으로 worker Pod 수를 결정하며, Karpenter가 그 Pod들을 실행할 노드 수를 결정합니다.
</details>

6. GPU 기반 Ray Serve deployment는 GPU를 어떻게 요청합니까?
   - A) Ray Serve만을 위한 별도의 GPU 예약 API를 통해
   - B) Ray Train과 Ray Tune worker가 사용하는 것과 동일한, actor 단위의 일반적인 Ray 리소스 요청 메커니즘을 통해
   - C) worker 노드에 직접 SSH로 접속해 환경 변수를 설정해서
   - D) Ray Serve deployment는 GPU를 요청할 수 없다

<details>

<summary>정답 보기</summary>

**정답: B) Ray Train과 Ray Tune worker가 사용하는 것과 동일한, actor 단위의 일반적인 Ray 리소스 요청 메커니즘을 통해**

**설명:**
GPU가 필요한 모델 추론 deployment는 Ray Train과 Ray Tune이 사용하는 것과 같은 actor 단위 리소스 요청 메커니즘으로 GPU를 요청하며, worker group의 Pod spec이 Ray 스케줄러에 GPU 용량을 알리는 근거입니다.
</details>

7. Ray Serve의 autoscaler가 새 GPU replica를 요청했는데 기존 GPU worker Pod에 여유가 없을 때 어떤 일이 일어납니까?
   - A) 요청이 조용히 무시되고 새 replica는 결코 생성되지 않는다
   - B) 그 replica 요청은 대기 중인 Pod가 되고, Karpenter가 새 GPU 기반 EC2 노드를 프로비저닝해야 비로소 그 replica가 트래픽을 서빙할 수 있게 된다
   - C) Ray Serve가 자동으로 해당 모델을 CPU에서 실행하도록 전환한다
   - D) Ray autoscaler가 Karpenter를 완전히 건너뛰고 스스로 EC2 인스턴스를 생성한다

<details>

<summary>정답 보기</summary>

**정답: B) 그 replica 요청은 대기 중인 Pod가 되고, Karpenter가 새 GPU 기반 EC2 노드를 프로비저닝해야 비로소 그 replica가 트래픽을 서빙할 수 있게 된다**

**설명:**
Ray Serve의 autoscaling과 Karpenter의 노드 프로비저닝 소요 시간은 다른 GPU 워크로드와 동일하게 상호작용합니다. 대기 중인 Pod가 Karpenter로 하여금 맞는 노드를 프로비저닝하게 하며, GPU replica를 적극적으로 스케일하는 서빙 애플리케이션이라면 이 소요 시간을 감안해야 합니다.
</details>

8. RayService CRD는 프로덕션에서 무엇을 관리하며, 구체적으로 어떤 기능을 지원합니까?
   - A) 하위 RayCluster와는 아무 관계 없이 Serve application만 관리한다
   - B) 하위 RayCluster와 그 위에 배포된 Serve application을 함께 관리하며, 무중단 rolling upgrade를 지원한다
   - C) 서빙 기능 없이, 한 번 실행되고 종료되는 배치 작업만 관리한다
   - D) 업그레이드할 수 없는 정적이고 변경 불가능한 Ray 클러스터 스냅샷이다

<details>

<summary>정답 보기</summary>

**정답: B) 하위 RayCluster와 그 위에 배포된 Serve application을 함께 관리하며, 무중단 rolling upgrade를 지원한다**

**설명:**
RayService는 RayCluster와 그 위의 Serve application을 하나의 단위로 함께 관리하며, 진행 중인 요청을 끊지 않고 새 애플리케이션 버전이나 RayCluster spec을 롤아웃하는 무중단 rolling upgrade 기능을 지원하는 리소스입니다 — 이 업그레이드 경로의 성숙도는 실제로 의존하기 전에 현재 KubeRay 릴리스 노트에서 확인하세요.
</details>

## 서술형 문제

9. Ray Serve의 autoscaler와 Ray/KubeRay autoscaler가 "바로 아래 계층만 본다"고 설명되는 이유를 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
Ray Serve의 autoscaler는 요청 부하를 기준으로 특정 deployment에 필요한 actor replica 수만 결정하며, 새 replica가 기존 worker Pod에 배치되는지 새 Pod가 필요한지는 전혀 알지 못합니다. 한 단계 아래의 Ray/KubeRay autoscaler는 (Serve autoscaler가 요청한 replica를 포함한) 대기 중인 actor 배치에만 반응해 worker Pod 수를 결정하며, 요청 수준의 지표는 전혀 알지 못합니다. 다시 한 단계 아래의 Karpenter는 대기 중인 Pod에만 반응해 노드 수를 결정합니다.

**설명:**
각 제어 루프는 그 위 계층보다 더 좁은 질문에만 답하며, 계층들은 직접 조율하지 않고 각 계층이 만들어내는 상태(replica 요청 → 대기 중인 Pod → 대기 중인 노드)를 통해서만 간접적으로 소통합니다.
</details>

10. 한 팀이 2단계 Ray Serve application(전처리 다음 GPU 기반 모델 추론)을 EKS 프로덕션에 배포하려 합니다. 이 문서에서 설명한 deployment 구조, autoscaling, 생명주기 관리가 이 애플리케이션에서 어떻게 맞물리는지 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
이 application은 전처리 deployment와 모델 추론 deployment 두 개로 구성되며, 각각은 actor replica로 구현되고 전처리 deployment의 출력이 추론 deployment로 넘어갑니다. 각 deployment는 자신의 요청 부하를 기준으로 Ray Serve의 autoscaler를 통해 독립적으로 replica 수를 autoscaling합니다. 추론 deployment의 actor replica는 Ray의 일반적인 actor 단위 리소스 메커니즘으로 GPU를 요청하며, Ray Serve의 autoscaler가 기존 worker Pod가 감당할 수 없는 만큼 GPU replica를 더 필요로 하면 Ray/KubeRay autoscaler가 worker Pod를 더 요청하고 Karpenter가 그에 맞는 GPU 기반 EC2 노드를 프로비저닝합니다. 프로덕션에서는 `RayService` 오브젝트가 애플리케이션 전체의 RayCluster와 Serve 롤아웃을 함께 관리하며, 애플리케이션이나 클러스터 spec이 바뀔 때 무중단 업그레이드까지 포함합니다.

**설명:**
이 답은 문서의 모든 개념 — actor 기반 deployment/application 모델, Serve 자체의 autoscaling 계층, Ray/KubeRay와 Karpenter로 이어지는 3단계 autoscaling 구조, GPU 리소스 요청, 그리고 이 모든 것의 프로덕션 생명주기를 관리하는 RayService — 를 하나로 엮습니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/ray/04-ray-serve.md)

# Ray 아키텍처 퀴즈

이 퀴즈는 Ray의 핵심 primitive(task, actor, object store), Ray 클러스터 아키텍처(head node, worker node), 그리고 Ray의 상위 레벨 라이브러리들이 이 기반 위에 어떻게 구축되는지에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Ray는 근본적으로 무엇인가요?
   - A) 분산 모델 학습만을 위해 만들어진 도메인 특화 프레임워크
   - B) 소수의 범용 primitive를 중심으로 만들어진, Python 워크로드를 확장하기 위한 오픈소스 분산 컴퓨팅 프레임워크
   - C) 기본 kube-scheduler를 대체하는 Kubernetes 네이티브 스케줄러
   - D) 프로그래밍 API가 없는 매니지드 모델 서빙 제품

<details>

<summary>정답 보기</summary>

**정답: B) 소수의 범용 primitive를 중심으로 만들어진, Python 워크로드를 확장하기 위한 오픈소스 분산 컴퓨팅 프레임워크**

**설명:**
Ray는 하나의 워크로드만을 위해 만들어지지 않았습니다. task, actor, object store라는 범용 primitive를 제공하며, 이는 임시 병렬 작업부터 분산 학습, 하이퍼파라미터 튜닝, 모델 서빙까지 다양한 사용 사례를 지원합니다.
</details>

2. Ray의 task란 무엇인가요?
   - A) 클래스에 `@ray.remote`를 적용해 만드는, 상태를 가진(stateful) 오래 살아 있는 원격 객체
   - B) 함수에 `@ray.remote`를 적용해 만드는, Ray가 원격에서 실행하는 상태 없는(stateless) 함수
   - C) head node에서 클러스터 메타데이터를 관리하는 프로세스
   - D) 분산 object store의 한 샤드

<details>

<summary>정답 보기</summary>

**정답: B) 함수에 `@ray.remote`를 적용해 만드는, Ray가 원격에서 실행하는 상태 없는(stateless) 함수**

**설명:**
Task는 상태 없는 원격 함수입니다. 호출하면 즉시 future를 반환하고, 실제 실행은 여유가 있는 워커에 Ray가 스케줄링합니다. Task는 호출 사이에 상태를 유지하지 않으므로, Ray는 여유가 있는 어떤 워커에서든 그 호출을 실행할 수 있습니다.
</details>

3. Actor는 task와 어떤 점에서 다른가요?
   - A) Actor는 상태가 없고, task가 호출 사이에 상태를 유지한다
   - B) Actor는 클래스로부터 만들어지는, 오래 살아 있고 상태를 가지는 원격 인스턴스이며, 그 상태가 메서드 호출 사이에 계속 유지된다
   - C) Actor는 head node에서만 실행할 수 있다
   - D) Actor는 `@ray.remote` 데코레이터로 만들 수 없다

<details>

<summary>정답 보기</summary>

**정답: B) Actor는 클래스로부터 만들어지는, 오래 살아 있고 상태를 가지는 원격 인스턴스이며, 그 상태가 메서드 호출 사이에 계속 유지된다**

**설명:**
클래스에 `@ray.remote`를 적용하면 actor가 됩니다. Ray는 그 결과 생성된 인스턴스를 오래 살아 있는 원격 프로세스로 유지하므로, 불러온 모델 가중치나 카운터처럼 인스턴스에 저장된 상태가 메서드 호출 사이에 계속 유지됩니다. 이는 상태가 없는 task와 다른 점입니다.
</details>

4. Ray의 분산 object store가 주로 해결하는 문제는 무엇인가요?
   - A) Ray 클러스터에서 head node가 필요 없게 만든다
   - B) 큰 객체를 필요로 하는 모든 프로세스에 다시 직렬화해서 복사하는 대신, 공유 메모리에서 읽을 수 있게 하여 불필요한 복사를 없앤다
   - C) 클러스터의 autoscaler 설정을 저장한다
   - D) task를 특정 worker node에 스케줄링한다

<details>

<summary>정답 보기</summary>

**정답: B) 큰 객체를 필요로 하는 모든 프로세스에 다시 직렬화해서 복사하는 대신, 공유 메모리에서 읽을 수 있게 하여 불필요한 복사를 없앤다**

**설명:**
Object store는 task와 actor 사이에 전달되는 객체를 담는 분산 공유 메모리 저장소입니다. 데이터셋이나 모델 가중치처럼 큰 객체의 경우, 이 방식은 필요한 모든 프로세스에 객체를 중복 저장하는 직렬화·복사 비용을 없애줍니다.
</details>

5. Worker node가 하는 일 외에, Ray 클러스터의 head node에서 추가로 실행되는 것은 무엇인가요?
   - A) 분산 object store뿐이다
   - B) Global Control Store(GCS), (그곳에서 실행하는 경우의) driver 프로세스, autoscaler
   - C) 사용자가 제출한 task와 actor뿐이다
   - D) 별도의 Kubernetes control plane

<details>

<summary>정답 보기</summary>

**정답: B) Global Control Store(GCS), (그곳에서 실행하는 경우의) driver 프로세스, autoscaler**

**설명:**
Head node는 worker node처럼 리소스 풀에 CPU/GPU/메모리를 제공하는 것 외에도, GCS(클러스터 메타데이터), 최상위 스크립트나 세션이 그곳에서 실행되는 경우의 driver 프로세스, autoscaler를 실행합니다.
</details>

6. Ray는 클러스터 전체에 걸쳐 task와 actor를 어떻게 스케줄링하나요?
   - A) 각 노드의 리소스를 개별적으로 보고, 사용자가 task마다 특정 노드를 직접 골라야 한다
   - B) 클러스터 전체가 합쳐진 리소스 풀을 기준으로 스케줄링하므로, task는 여유 리소스가 충분한 어떤 노드에든 배치될 수 있다
   - C) head node에서만 실행하고, worker node는 오직 저장용으로만 사용한다
   - D) 사용 가능한 CPU, GPU, 메모리와 무관하게 무작위로 배치한다

<details>

<summary>정답 보기</summary>

**정답: B) 클러스터 전체가 합쳐진 리소스 풀을 기준으로 스케줄링하므로, task는 여유 리소스가 충분한 어떤 노드에든 배치될 수 있다**

**설명:**
Ray는 개별 노드가 아니라 클러스터 전체의 리소스 풀을 기준으로 작업을 스케줄링합니다. 특정 양의 CPU를 요청하는 task는 클러스터 안에서 그만큼의 여유 CPU가 있는 어떤 노드에든 실행될 수 있습니다.
</details>

7. Ray Train, Ray Tune, Ray Serve가 아키텍처적으로 공유하는 특징은 무엇인가요?
   - A) 각각 Ray의 core와 무관한, 자기만의 별도 스케줄링·장애 복구 시스템을 구현한다
   - B) 모두 동일한 task, actor, object store라는 Ray core primitive 위에 구축되어 있다
   - C) Ray 클러스터 밖에서만 실행할 수 있다
   - D) head node가 필요 없게 만든다

<details>

<summary>정답 보기</summary>

**정답: B) 모두 동일한 task, actor, object store라는 Ray core primitive 위에 구축되어 있다**

**설명:**
학습, 튜닝, 서빙을 위한 Ray의 상위 레벨 라이브러리들은 워크로드마다 스케줄링과 데이터 이동을 따로 재구현하지 않고 동일한 primitive를 재사용합니다. 이렇게 기반을 공유한다는 점이, 서로 무관한 개별 도구들을 한데 묶어 놓은 것과 Ray를 구분하는 핵심적인 아키텍처 차이입니다.
</details>

8. Ray를 Kubernetes 위에서 실행할 때, Ray 자체의 클러스터 개념만으로는 부족하고 그 이상의 무언가가 필요한 이유는 무엇인가요?
   - A) Ray가 컨테이너 안에서 실행될 수 없기 때문에
   - B) Ray의 head/worker 클러스터 구조가 Kubernetes 자체의 스케줄링과는 다른 레이어이기 때문에, 이 구조를 Pod, Deployment 같은 Kubernetes 객체로 변환해줄 무언가가 필요하기 때문에
   - C) Kubernetes가 오토스케일링을 지원하지 않기 때문에
   - D) Ray task가 Kubernetes 노드의 CPU 리소스를 사용할 수 없기 때문에

<details>

<summary>정답 보기</summary>

**정답: B) Ray의 head/worker 클러스터 구조가 Kubernetes 자체의 스케줄링과는 다른 레이어이기 때문에, 이 구조를 Pod, Deployment 같은 Kubernetes 객체로 변환해줄 무언가가 필요하기 때문에**

**설명:**
Ray 자체의 클러스터 개념(head node, worker node, autoscaler)은 Kubernetes의 스케줄링 모델에 자동으로 대응되지 않습니다. Ray 클러스터의 구조를 Kubernetes 스케줄러가 이해하는 Pod, Deployment로 변환해줄 무언가가 필요하며, 이 변환을 제공하는 것이 바로 KubeRay입니다.
</details>

## 단답형 문제

9. 동료가 어떤 로직을 Ray task로 구현할지 actor로 구현할지 고민하고 있습니다. 매번 다시 불러오는 대신, 들어오는 여러 요청에 걸쳐 머신러닝 모델을 메모리에 계속 로드된 상태로 유지해야 합니다. 어떤 primitive를 사용해야 하며, 그 이유는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: Actor를 사용해야 합니다. Actor는 오래 살아 있고 상태를 가지는 원격 인스턴스이므로, 로드된 모델을 actor의 상태에 보관해 두고 여러 메서드 호출에 걸쳐 재사용할 수 있습니다. Task였다면 매 호출마다 다시 로드해야 했을 것입니다.**

**설명:**
Task는 상태가 없고 한 번의 호출로 끝나므로, 호출 사이에 로드된 모델을 유지할 곳이 없습니다. Actor의 인스턴스는 원격 프로세스로 계속 살아 있으므로, 로드된 모델 가중치 같은 상태가 actor 핸들을 통한 여러 호출에 걸쳐 계속 유지됩니다.
</details>

10. Ray가 스케줄링, 장애 복구, 데이터 이동을 상위 레벨 라이브러리(Train, Tune, Serve)마다 따로 구현하지 않고 core primitive에서 한 번만 구현하는 이유는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: Ray Train, Ray Tune, Ray Serve가 모두 동일한 task, actor, object store 위에 구축되어 있기 때문에, 각 라이브러리는 자기 워크로드를 위해 스케줄링과 데이터 이동을 따로 재구현하는 대신 이 공유된 구현을 재사용할 수 있습니다.**

**설명:**
이렇게 기반을 공유한다는 점이, 워크로드마다 각자의 실행 모델을 가진 개별 도구들을 한데 묶어 놓은 생태계와 Ray를 구분하는 핵심적인 아키텍처 차이입니다. 분산 학습 run과 하이퍼파라미터 스윕은 내부적으로 보면 모두, Ray actor나 task로 실행되는 워커들이 동일한 object store를 통해 데이터를 주고받는 방식입니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/ray/01-architecture.md) | [다음 퀴즈: KubeRay Operator](./02-kuberay-operator-quiz.md)

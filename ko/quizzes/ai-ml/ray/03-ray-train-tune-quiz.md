# Ray Train과 Ray Tune 퀴즈

이 퀴즈는 Ray Train(Trainer, ScalingConfig, 체크포인팅), Ray Tune, 그리고 분산 하이퍼파라미터 튜닝을 위해 이 둘이 어떻게 결합되는지에 대한 이해를 테스트합니다.

## 객관식 문제

1. Ray Train이 분산 학습 스크립트에 대해 주로 해결하는 문제는 무엇인가요?
   - A) PyTorch 등의 학습 프레임워크를 완전히 새로운 학습 API로 대체한다
   - B) 워커 프로세스 실행, 워커 간 통신 그룹 구성, 체크포인트 조율이라는 보일러플레이트를 대신 처리해준다
   - C) 학습이 시작되기 전에 학습 데이터에 자동으로 레이블을 붙여준다
   - D) GPU 없이도 학습을 전부 CPU로 실행할 수 있게 해준다

<details>

<summary>정답 보기</summary>

**정답: B) 워커 프로세스 실행, 워커 간 통신 그룹 구성, 체크포인트 조율이라는 보일러플레이트를 대신 처리해준다**

**설명:**
Ray Train은 Ray의 task와 actor 원시 개념 위에 만들어졌으며, 할당된 리소스마다 워커를 하나씩 실행하고, 워커 간 통신 그룹(예: PyTorch DDP 프로세스 그룹)을 구성하고, 체크포인팅을 조율하는 분산 학습 보일러플레이트를 대신 처리합니다. 그 결과 익숙한 프레임워크 API로 작성된 학습 스크립트는 작성자가 이런 조율을 직접 손으로 구현하지 않고도 확장될 수 있습니다.
</details>

2. Ray Train V2에 대한 설명으로 가장 적절한 것은 무엇인가요?
   - A) 이전 Ray Train 릴리스와 전혀 관련 없는 완전히 별개의 제품이다
   - B) 기존의 `ray.train.torch.TorchTrainer` import 경로 뒤에서 다시 작성된 구현으로, 이전 세대의 여러 Trainer 클래스가 내부적으로 동작하던 방식을 통합하고 단순화했다
   - C) CPU 기반 학습만 지원하는 Ray Train 버전이다
   - D) Ray가 더 이상 문서화하지 않는 폐기된 API이다

<details>

<summary>정답 보기</summary>

**정답: B) 기존의 `ray.train.torch.TorchTrainer` import 경로 뒤에서 다시 작성된 구현으로, 이전 세대의 여러 Trainer 클래스가 내부적으로 동작하던 방식을 통합하고 단순화했다**

**설명:**
Ray Train의 API는 시간이 지나면서 계속 발전해왔지만, 사용자가 쓰는 import 경로(PyTorch 기준 `ray.train.torch.TorchTrainer`)는 바뀌지 않았습니다 — 바뀐 것은 그 경로 뒤의 구현입니다. 이 재작성이 정확히 언제 기본값이 되었는지는 현재의 Ray 공식 문서를 확인하는 것이 가장 좋습니다.
</details>

3. Ray Train의 `ScalingConfig`가 하는 역할은 무엇인가요?
   - A) 워커를 몇 개 실행할지, 각 워커에 어떤 리소스(예: GPU)가 필요한지를 지정한다
   - B) 학습에 사용할 신경망 아키텍처를 정의한다
   - C) optimizer의 학습률(learning rate) 스케줄을 설정한다
   - D) Ray 클러스터가 실행될 클라우드 리전을 설정한다

<details>

<summary>정답 보기</summary>

**정답: A) 워커를 몇 개 실행할지, 각 워커에 어떤 리소스(예: GPU)가 필요한지를 지정한다**

**설명:**
`ScalingConfig`는 Trainer에게 워커를 몇 개 실행할지와 각 워커에 GPU가 필요한지를 알려줍니다. Trainer는 이 설정을 바탕으로 다른 일반적인 Ray task나 actor와 동일한 방식으로 기반 Ray 클러스터에 해당 리소스를 요청합니다.
</details>

4. 워커 장애 이후 학습을 복구할 수 있게 하는 것 외에, Ray Train의 체크포인팅이 수행하는 또 다른 역할은 무엇인가요?
   - A) 학습 데이터셋을 압축해 저장 공간을 절약한다
   - B) 학습된 모델을 워크플로우의 다음 단계, 예를 들어 하이퍼파라미터 튜닝 관련 의사결정이나 모델 등록으로 넘겨준다
   - C) 모델을 프로덕션 서빙 엔드포인트에 자동으로 배포한다
   - D) ScalingConfig가 필요 없게 만든다

<details>

<summary>정답 보기</summary>

**정답: B) 학습된 모델을 워크플로우의 다음 단계, 예를 들어 하이퍼파라미터 튜닝 관련 의사결정이나 모델 등록으로 넘겨준다**

**설명:**
보고된 체크포인트는 학습을 이어갈 수 있을 만큼의 상태(보통 모델 weight와 optimizer 상태)를 담고 있지만, 동시에 다음에 이어질 작업, 예를 들어 튜닝 관련 의사결정이나 결과를 모델 버전으로 등록하는 일로 넘어가는 지점 역할도 합니다. 이는 이 문서 사이트의 다른 부분에서 다루는 모델 레지스트리 패턴과 개념적으로 유사합니다.
</details>

5. Ray Tune은 무엇을 하나요?
   - A) 클러스터 전역에서 많은 학습 trial을 병렬로 실행하고, pluggable한 탐색 알고리즘으로 다음에 시도할 하이퍼파라미터 조합을 결정한다
   - B) 한 번에 하나의 하이퍼파라미터만 순차적으로 튜닝한다
   - C) 모든 분산 학습 워크로드에 대해 Ray Train을 완전히 대체한다
   - D) Ray의 핵심 원시 개념과 무관한 Kubernetes CRD 기반 컨트롤러이다

<details>

<summary>정답 보기</summary>

**정답: A) 클러스터 전역에서 많은 학습 trial을 병렬로 실행하고, pluggable한 탐색 알고리즘으로 다음에 시도할 하이퍼파라미터 조합을 결정한다**

**설명:**
Ray Tune은 Ray 위에 만들어진 하이퍼파라미터 튜닝 라이브러리입니다. 각 trial은 하나의 하이퍼파라미터 조합으로 학습을 수행하고 결과를 다시 보고하며, Tune의 탐색 알고리즘은 이를 바탕으로 다음 시도를 결정합니다. 이는 Kubeflow 생태계의 Katib가 제공하는 것과 개념적으로 유사하지만, 별도의 Kubernetes CRD 기반 시스템이 아니라 Ray에 네이티브하다는 점이 다릅니다.
</details>

6. 그 자체로 분산 학습이 필요한 모델에 대해, Ray Tune과 Ray Train은 흔히 어떻게 결합되나요?
   - A) Tune과 Train은 함께 쓸 수 없으며, 팀은 둘 중 하나만 선택해야 한다
   - B) Tune이 탐색 대상인 trainable로 Ray Train의 `Trainer`를 그대로 감싸서, 각 trial이 독립적인 분산 Ray Train 실행이 된다
   - C) Ray Train이 먼저 끝까지 실행되고, 그 후에야 Ray Tune이 별도의 클러스터에서 시작된다
   - D) Tune이 Trainer의 ScalingConfig를 자신만의 리소스 모델로 대체한다

<details>

<summary>정답 보기</summary>

**정답: B) Tune이 탐색 대상인 trainable로 Ray Train의 `Trainer`를 그대로 감싸서, 각 trial이 독립적인 분산 Ray Train 실행이 된다**

**설명:**
흔히 쓰이는 패턴은 Tune에 Ray Train의 `Trainer`를 trainable로 넘기는 것입니다. 이 경우 각 하이퍼파라미터 trial은 그 자체로 독립적인 분산 Ray Train 실행이 되며, 여러 GPU나 여러 노드에 걸칠 수 있습니다. 이는 trial 하나만으로도 합리적인 시간 안에 끝내기 위해 분산 학습이 필요한 경우에 유용합니다.
</details>

7. EKS에서 KubeRay 기반 오토스케일러가 Ray Train이나 Ray Tune 작업의 실제 리소스 수요에 반응할 수 있는 이유는 무엇인가요?
   - A) Ray Train과 Ray Tune이 다른 모든 Ray 워크로드와 동일하게, Ray의 일반적인 task/actor 리소스 요청 메커니즘을 통해 CPU와 GPU를 요청하기 때문이다
   - B) Ray Train과 Ray Tune이 Ray의 스케줄러를 건너뛰고 Kubernetes API 서버와 직접 통신하기 때문이다
   - C) 어떤 작업이든 실행되기 전에 클러스터가 항상 고정된 크기로 프로비저닝되어야 하기 때문이다
   - D) Karpenter가 학습 프로세스 내부의 GPU 사용률을 직접 모니터링하기 때문이다

<details>

<summary>정답 보기</summary>

**정답: A) Ray Train과 Ray Tune이 다른 모든 Ray 워크로드와 동일하게, Ray의 일반적인 task/actor 리소스 요청 메커니즘을 통해 CPU와 GPU를 요청하기 때문이다**

**설명:**
두 라이브러리 모두 학습이나 튜닝만을 위한 별도의 경로 없이, Ray의 일반적인 task/actor 리소스 요청 메커니즘을 통해 리소스를 요청합니다. 이 덕분에 Part 2에서 다룬 오토스케일러가 실제 수요에 반응할 수 있습니다. Tune sweep이 더 많은 동시 trial을 실행하면 더 많은 워커 노드를 요청하고, trial이 끝나면 다시 축소합니다. 클러스터를 미리 고정된 크기로 프로비저닝할 필요가 없습니다.
</details>

8. EKS에서 Ray Train 실행을 구성하는 분산 워커들의 코스케줄링 요구사항에서 발생할 수 있는 실무적인 문제는 무엇인가요?
   - A) 없다 — Ray Train 워커들은 동시에 시작될 필요가 전혀 없다
   - B) 오토스케일러가 합리적인 시간 안에 요청된 모든 워커를 프로비저닝하지 못하면, 학습 작업이 마지막 남은 GPU 워커들이 뜰 때까지 멈춰서 대기할 수 있다
   - C) 코스케줄링은 Ray Tune에서만 문제가 되고, Ray Train에는 전혀 해당하지 않는다
   - D) 체크포인팅이 코스케줄링 지연을 자동으로 해결해준다

<details>

<summary>정답 보기</summary>

**정답: B) 오토스케일러가 합리적인 시간 안에 요청된 모든 워커를 프로비저닝하지 못하면, 학습 작업이 마지막 남은 GPU 워커들이 뜰 때까지 멈춰서 대기할 수 있다**

**설명:**
하나의 Ray Train 실행을 구성하는 워커들은 보통 코스케줄링, 즉 모두가 떠서 각자의 GPU를 확보한 상태여야 통신 그룹을 세울 수 있습니다. 이는 이 문서 사이트의 다른 부분에서 다룬 gang-scheduling 요구사항과 유사합니다. GPU 노드 풀 프로비저닝 리드 타임은 CPU 노드보다 더 길고 예측하기 어려운 경우가 많기 때문에, 학습 작업의 실제 시작 시점은 요청된 모든 워커가 얼마나 빠르게 코스케줄링될 수 있는지에 달려 있습니다.
</details>

## 서술형 문제

9. Ray Train의 `Trainer`와 `ScalingConfig`가 각각 무엇을 하는지, 그리고 분산 학습 작업을 실행하기 위해 이 둘이 어떻게 함께 동작하는지 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
Trainer(예: `TorchTrainer`)는 사용자가 작성한 학습 함수를 감쌉니다. 이 함수에는 모델을 구성하고, 배치를 순회하고, loss를 계산하고, optimizer를 한 단계 진행하는 일반적인 모델 학습 로직이 들어 있습니다. Trainer는 이 함수를 워커마다 한 번씩, 기반 프레임워크의 데이터 병렬 학습이 요구하는 분산 프로세스 그룹(예: PyTorch DDP 프로세스 그룹) 안에서 실행하는 역할을 맡습니다. 따라서 학습 함수 자체는 이 조율을 직접 손으로 구성할 필요가 없습니다.

`ScalingConfig`는 Trainer에게 워커를 몇 개 실행할지, 그리고 각 워커에 GPU가 필요한지 같은 리소스 요구사항을 알려줍니다. Trainer는 이 `ScalingConfig`를 바탕으로 Ray의 일반적인 task/actor 리소스 요청 메커니즘을 통해 기반 Ray 클러스터에 해당 리소스를 요청합니다. 즉 Trainer는 학습 로직과 조율을 담당하고, `ScalingConfig`는 Trainer가 그 로직을 확장할 리소스의 규모를 담당합니다.
</details>

10. Ray Tune과 Ray Train을 결합하는 것이 왜 유용한지, 그리고 이 결합에서 발생하는 리소스 요청이 EKS의 클러스터 오토스케일링과 어떻게 상호작용하는지 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
일부 모델은 학습 비용이 매우 커서, 하이퍼파라미터 trial 하나만으로도 합리적인 시간 안에 끝내려면 분산(멀티 GPU 또는 멀티 노드) 학습이 필요합니다. 두 라이브러리를 결합하지 않으면, 팀은 분산 학습 작업을 대상으로 하이퍼파라미터를 순차적으로 튜닝하거나, 탐색 단계에서는 분산 학습을 포기해야 하는 상황에 놓입니다. Ray Tune이 Ray Train의 `Trainer`를 trainable로 감쌀 수 있기 때문에, 각 trial은 독립적인 분산 Ray Train 실행이 되고, Tune은 다음에 시도할 하이퍼파라미터 조합을 결정하면서 이런 실행을 여러 개 동시에 진행할 수 있습니다.

모든 trial의 모든 워커가 여전히 Ray의 일반적인 task/actor 리소스 요청 메커니즘을 통해 CPU와 GPU를 요청하기 때문에, EKS의 KubeRay 기반 오토스케일러는 미리 선언된 고정된 형태가 아니라 현재 활성화된 모든 trial의 실시간 총 리소스 수요를 파악할 수 있습니다. Tune sweep이 더 많은 동시 trial을 실행하면 더 많은 워커 노드를 프로비저닝하고, trial이 끝나면 다시 축소할 수 있으므로, 가능한 가장 큰 sweep을 기준으로 클러스터를 미리 크게 잡아둘 필요가 없습니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/ray/03-ray-train-tune.md) | [다음 퀴즈: Ray Serve](./04-ray-serve-quiz.md)

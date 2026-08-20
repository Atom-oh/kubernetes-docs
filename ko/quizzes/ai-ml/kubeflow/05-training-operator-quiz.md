# Kubeflow Trainer와 분산 학습 퀴즈

이 퀴즈는 레거시 Training Operator의 프레임워크별 CRD, Kubeflow Trainer v2의 통합 `TrainJob`/런타임 모델로의 전환, Kubernetes에서의 분산 학습 메커니즘에 대한 이해를 확인합니다.

## 객관식 문제

1. 2021년에 통합된 기존(v1) Training Operator의 근본적인 아키텍처 방식은 무엇이었습니까?
   - A) 모든 프레임워크가 공유하는 단일 CRD를 두고 런타임에 프레임워크를 감지
   - B) ML 프레임워크마다 별도의 CRD(예: `PyTorchJob`, `TFJob`, `MPIJob`)를 두고, 각각 그 프레임워크의 분산 학습 규약을 구현하는 자체 컨트롤러를 가짐
   - C) CRD가 전혀 없고 학습 인자를 이미지에 박아 넣은 `kubectl run` 컨테이너로 작업을 직접 제출
   - D) `framework` 필드를 가진 단일 `TrainingJob` CRD와 하나의 공유 컨트롤러

<details>
<summary>정답 보기</summary>

**정답: B) ML 프레임워크마다 별도의 CRD(예: `PyTorchJob`, `TFJob`, `MPIJob`)를 두고, 각각 그 프레임워크의 분산 학습 규약을 구현하는 자체 컨트롤러를 가짐**

**설명:**
v1 Training Operator는 `PyTorchJob`, `TFJob`, `MPIJob` 등 프레임워크당 하나의 CRD를 제공했고, 각 CRD는 해당 프레임워크만의 분산 학습 규약(PyTorch의 랭크/환경 변수 모델 vs. TensorFlow의 `TF_CONFIG`)을 이해하는 자체 컨트롤러가 뒷받침했습니다.

</details>

2. `PyTorchJob` 컨트롤러가 워커들이 `torch.distributed` 프로세스 그룹을 구성할 수 있도록 주입한 환경 변수는 무엇입니까?
   - A) `TF_CONFIG`만
   - B) `MASTER_ADDR`, `RANK`, `WORLD_SIZE`
   - C) `KUBEFLOW_HOST`와 `KUBEFLOW_PORT`
   - D) `POD_IP`와 `POD_NAMESPACE`

<details>
<summary>정답 보기</summary>

**정답: B) `MASTER_ADDR`, `RANK`, `WORLD_SIZE`**

**설명:**
`PyTorchJob` 컨트롤러는 각 워커 Pod에 `MASTER_ADDR`, `RANK`, `WORLD_SIZE`를 주입해 PyTorch의 `torch.distributed` 메커니즘이 프로세스 그룹을 구성하고 조율할 수 있게 했습니다.

</details>

3. v1 Training Operator와 비교했을 때 Kubeflow Trainer v2가 도입한 핵심 아키텍처 변화는 무엇입니까?
   - A) 기존 CRD 위에 프레임워크별 CRD를 더 추가한다
   - B) 프레임워크별 CRD를 통합 `TrainJob` API와 재사용 가능한 `TrainingRuntime`/`ClusterTrainingRuntime` 템플릿으로 대체한다
   - C) 컨트롤러를 완전히 제거하고 어드미션 웹훅에만 의존한다
   - D) `TrainJob`과 `ClusterTrainingRuntime`을 다시 하나의 프레임워크별 CRD로 합친다

<details>
<summary>정답 보기</summary>

**정답: B) 프레임워크별 CRD를 통합 `TrainJob` API와 재사용 가능한 `TrainingRuntime`/`ClusterTrainingRuntime` 템플릿으로 대체한다**

**설명:**
프레임워크마다 CRD와 컨트롤러를 두는 대신, Trainer v2는 `TrainJob`(무엇을 실행할지)과 `TrainingRuntime`/`ClusterTrainingRuntime`(어떻게 실행할지 — 재사용 가능한 프레임워크별 실행 템플릿)을 도입해 작업 제출과 분산 실행 메커니즘을 분리합니다.

</details>

4. `TrainJob` / `ClusterTrainingRuntime` 구조에서, 일반적으로 플랫폼 팀이 소유하고 여러 학습 실행에 걸쳐 재사용되는 객체는 무엇입니까?
   - A) `TrainJob`
   - B) `ClusterTrainingRuntime`
   - C) 두 객체 모두 실행마다 새로 생성된다
   - D) 둘 다 아니고 대신 `PyTorchJob`이 생성된다

<details>
<summary>정답 보기</summary>

**정답: B) `ClusterTrainingRuntime`**

**설명:**
`ClusterTrainingRuntime`(또는 네임스페이스 범위의 `TrainingRuntime`)은 플랫폼 팀이 한 번 정의해두는 재사용 가능한 템플릿으로, 컨테이너 이미지와 분산 실행 메커니즘을 담습니다. 개별 `TrainJob`은 이름으로 이를 참조하고 실행별 스크립트, 인자, 워커 수만 채워 넣습니다.

</details>

5. Kubeflow Trainer v2.2가 정식으로 지원을 추가한 두 가지 학습 런타임은 무엇입니까?
   - A) TensorFlow와 MXNet
   - B) JAX와 XGBoost
   - C) Scikit-learn과 ONNX
   - D) Spark MLlib과 H2O

<details>
<summary>정답 보기</summary>

**정답: B) JAX와 XGBoost**

**설명:**
Kubeflow Trainer의 [릴리스 노트](https://github.com/kubeflow/trainer/releases)에 따르면, 2026년 3월경 출시된 v2.2는 기존 PyTorch 지원에 더해 JAX와 XGBoost 학습 런타임을 정식으로 추가했고, 관측성 강화와 HPC 스타일 워크로드를 위한 Flux Framework 연동도 함께 추가했습니다.

</details>

6. Kubeflow Community Distribution 26.03 릴리스 기준으로, v1에서 Trainer v2로의 마이그레이션 현황을 가장 정확하게 설명한 것은 무엇입니까?
   - A) 마이그레이션은 완전히 끝났고 모든 배포판에서 레거시 Training Operator가 제거되었다
   - B) 26.03 배포판에는 레거시 Training Operator(1.9.2)가 Trainer v2와 함께 여전히 포함되어 있으며, 기존 작업을 `TrainJob`으로 옮기는 것은 많은 팀에서 현재진행형 전환이다
   - C) Kubeflow Trainer v2는 폐기되었고 v1 CRD로 되돌아갔다
   - D) `TrainJob`과 `PyTorchJob`은 단순히 동일한 CRD의 다른 이름일 뿐이다

<details>
<summary>정답 보기</summary>

**정답: B) 26.03 배포판에는 레거시 Training Operator(1.9.2)가 Trainer v2와 함께 여전히 포함되어 있으며, 기존 작업을 `TrainJob`으로 옮기는 것은 많은 팀에서 현재진행형 전환이다**

**설명:**
Kubeflow Community Distribution 26.03은 Trainer v2와 함께 레거시 Training Operator 1.9.2를 여전히 배포하며, 이는 두 시스템이 공존하고 있고 많은 팀이 아직 `TrainJob`으로의 완전한 전환을 마치지 못했음을 보여줍니다.

</details>

7. 분산 학습 작업이 일반적으로 갱 스케줄링(gang scheduling)을 필요로 하는 이유는 무엇입니까?
   - A) Kubernetes는 기본적으로 네임스페이스 내 모든 Pod를 갱 스케줄링하도록 요구한다
   - B) 학습을 시작하기 전에 일반적으로 모든 워커가 함께 스케줄되어 실행 중이어야 하며, 일부만 스케줄되면 GPU 자원이 낭비되고 데드락이 발생할 수 있다
   - C) 갱 스케줄링은 스테이트리스 웹 워크로드에만 필요하다
   - D) 클라우드 제공업체가 부과하는 과금 요건이다

<details>
<summary>정답 보기</summary>

**정답: B) 학습을 시작하기 전에 일반적으로 모든 워커가 함께 스케줄되어 실행 중이어야 하며, 일부만 스케줄되면 GPU 자원이 낭비되고 데드락이 발생할 수 있다**

**설명:**
필요한 워커 중 일부만 스케줄된 분산 학습 작업은 나머지를 무한정 기다리며 확보된 GPU 자원을 낭비하고 데드락에 빠질 수 있습니다. 갱 스케줄링 메커니즘은 작업의 Pod들을 all-or-nothing 단위로 묶어 이를 방지합니다.

</details>

## 단답형 문제

8. Kubernetes에서 다중 워커 분산 학습 작업을 조율할 때 헤드리스 Service는 어떤 역할을 합니까?

<details>
<summary>정답 보기</summary>

**정답:** 재스케줄링 시 바뀔 수 있는 Pod IP에 의존하지 않고, 각 워커 Pod에 안정적이고 조회 가능한 DNS 이름을 부여해 다른 워커들이 그것을 찾을 수 있게 합니다.

**설명:**
분산 학습 워커들은 서로를 안정적으로 찾아야 합니다. 워커 Pod 앞에 둔 헤드리스 Service는 개별 Pod의 재스케줄링에도 유지되는 DNS 기반 탐색을 제공합니다.

</details>

9. 이 문서의 Katib 참고 내용에서, `TrainJob`은 Katib Trial 안에서 어떤 역할을 합니까?

<details>
<summary>정답 보기</summary>

**정답:** Katib은 보통 각 Trial의 실제 학습 작업으로 `TrainJob`을 템플릿화하여, 해당 Trial에서 선택된 하이퍼파라미터 값을 스크립트 인자로 주입하고, 보고된 메트릭을 읽어 탐색 방향을 결정합니다.

**설명:**
Katib 자체는 분산 실행 메커니즘을 알 필요가 없습니다 — 플랫폼 팀이 이미 정의해둔 런타임을 대상으로 Trial마다 `TrainJob`을 찍어내며, 하이퍼파라미터 탐색 로직과 학습 실행 메커니즘을 분리해 둡니다.

</details>

10. 기존 v1 CRD 매니페스트(예: `PyTorchJob`)를 Kubeflow Trainer v2로 옮기는 필드 단위의 권위 있는 참고 자료는 이 문서 대신 어디에서 찾아야 합니까?

<details>
<summary>정답 보기</summary>

**정답:** kubeflow.org의 "Migrating to Kubeflow Trainer v2" 가이드입니다.

**설명:**
이 문서는 개념적 전환과 메커니즘을 개괄적으로 다루지만 모든 마이그레이션 단계를 의도적으로 다시 나열하지 않습니다. 구체적인 필드 단위 매핑에 대한 공식적이고 권위 있는 출처는 kubeflow.org의 마이그레이션 가이드입니다.

</details>

---

[학습 자료로 돌아가기](../../../ai-ml/kubeflow/05-training-operator.md)

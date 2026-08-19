# Part 6: KServe — Kubernetes 위에서의 모델 서빙 퀴즈

이 퀴즈는 KServe와 Kubeflow의 관계, `InferenceService`의 구성 요소, Serverless와 Raw Deployment 사이의 트레이드오프, 오토스케일링 방식, 캐너리 롤아웃, 그리고 EKS에서의 GPU 추론에 대한 이해도를 테스트합니다.

## 객관식 문제

1. KServe와 Kubeflow의 역사적 관계는 무엇인가요?
   - A) KServe는 처음부터 Kubeflow와 아무런 관계가 없는 완전히 독립적인 프로젝트였다
   - B) KServe는 Kubeflow 내부의 KFServing으로 시작했다가 이후 독립적인 최상위 프로젝트로 분리되었다
   - C) Kubeflow는 KServe의 하위 컴포넌트이다
   - D) KServe는 Katib의 리브랜딩이다

<details>
<summary>정답 보기</summary>

**정답: B) KServe는 Kubeflow 내부의 KFServing으로 시작했다가 이후 독립적인 최상위 프로젝트로 분리되었다**

**설명:**
KServe는 학습된 모델을 추론 엔드포인트로 전환하는 역할을 맡은 Kubeflow 내부 컴포넌트인 KFServing으로 시작했습니다. 이후 Kubeflow 없이도 임의의 Kubernetes 클러스터에 설치할 수 있는 독립적인 프로젝트가 되었으며, Kubeflow는 여전히 이를 기본 모델 서빙 계층으로 함께 제공하고 있습니다.
</details>

2. Kubeflow 대시보드에 표시되는 KServe 웹 앱 버전이 KServe 컨트롤러/CRD 버전과 항상 같다고 가정할 수 없는 이유는 무엇인가요?
   - A) Kubeflow 대시보드는 KServe 버전 정보를 전혀 표시하지 않기 때문
   - B) KServe는 Kubeflow Community Distribution의 캘린더 버저닝 릴리스 트레인과 독립적인 자체 릴리스 주기를 가지고 있어, 플랫폼 팀이 웹 앱과 무관하게 컨트롤러를 업그레이드할 수 있기 때문
   - C) KServe는 더 이상 유지보수되지 않는 폐기된 프로젝트이기 때문
   - D) Kubeflow 웹 앱과 KServe 컨트롤러는 항상 동일한 바이너리이기 때문

<details>
<summary>정답 보기</summary>

**정답: B) KServe는 Kubeflow Community Distribution의 캘린더 버저닝 릴리스 트레인과 독립적인 자체 릴리스 주기를 가지고 있어, 플랫폼 팀이 웹 앱과 무관하게 컨트롤러를 업그레이드할 수 있기 때문**

**설명:**
Kubeflow Community Distribution 26.03은 KServe 웹 앱을 v0.16.1로 포함하지만, 이 숫자는 대시보드 통합 부분을 가리킬 뿐 클러스터에서 실행 중인 KServe 컨트롤러/CRD 버전을 반드시 의미하지는 않습니다. 컨트롤러는 자체 일정에 따라 독립적으로 업그레이드될 수 있기 때문입니다.
</details>

3. `InferenceService`의 구성 요소 중 필수이며, 나머지는 선택 사항인 것은 무엇인가요?
   - A) Explainer
   - B) Transformer
   - C) Predictor
   - D) 세 가지 모두 필수이다

<details>
<summary>정답 보기</summary>

**정답: C) Predictor**

**설명:**
Predictor는 모델 서버 그 자체이며 `InferenceService`에서 유일하게 필수인 컴포넌트입니다. Transformer(전/후처리)와 explainer(모델 설명)는 모두 선택적 부가 기능으로, 해당 사용 사례에 필요할 때만 추가합니다.
</details>

4. KServe Serverless 배포 모드의 핵심 기능과 그 대가는 각각 무엇인가요?
   - A) 일반 Deployment와 HPA를 사용하며 트레이드오프가 전혀 없다
   - B) 유휴 상태일 때 Knative를 통해 Pod를 0개까지 줄일 수 있으며, 그 대가로 스케일 업 시 콜드 스타트 지연이 발생한다
   - C) Kubernetes 클러스터가 전혀 필요하지 않다
   - D) predictor가 필요 없어진다

<details>
<summary>정답 보기</summary>

**정답: B) 유휴 상태일 때 Knative를 통해 Pod를 0개까지 줄일 수 있으며, 그 대가로 스케일 업 시 콜드 스타트 지연이 발생한다**

**설명:**
Serverless 모드는 Pod 라이프사이클을 Knative Serving에 위임하며, 트래픽이 없을 때 predictor(그리고 transformer/explainer) Pod를 0개까지 줄여 유휴 GPU 비용을 절약할 수 있습니다. 그 대가는 콜드 스타트 지연입니다 — 0에서 스케일 업된 이후 첫 요청에 응답하기까지 새 Pod 스케줄링, 컨테이너 시작, 모델 아티팩트 로드에 시간이 소요됩니다.
</details>

5. Raw Deployment 모드와 Serverless 모드의 핵심 차이는 무엇인가요?
   - A) Raw Deployment 모드는 Knative 의존성이 없고 scale-to-zero도 없는, 일반 Deployment/Service(그리고 선택적 HPA)를 관리한다
   - B) Raw Deployment 모드는 Knative Serving을 필요로 하며 transformer를 자동으로 추가한다
   - C) Raw Deployment 모드는 SKLearn 모델에서만 사용할 수 있다
   - D) Raw Deployment 모드는 항상 Serverless 모드보다 더 많은 레플리카를 실행한다

<details>
<summary>정답 보기</summary>

**정답: A) Raw Deployment 모드는 Knative 의존성이 없고 scale-to-zero도 없는, 일반 Deployment/Service(그리고 선택적 HPA)를 관리한다**

**설명:**
Raw Deployment 모드는 운영상 더 단순하며(Knative를 설치·업그레이드할 필요가 없음) 콜드 스타트를 완전히 피할 수 있지만, Deployment에 설정된 최소 레플리카 수 이하로는 절대 스케일 다운되지 않습니다. 따라서 트래픽 여부와 관계없이 최소한 그 개수만큼의 predictor Pod(그리고 그 GPU까지)가 항상 실행 상태로 유지됩니다.
</details>

6. 두 배포 모드 사이에 오토스케일링 방식은 어떻게 다른가요?
   - A) 두 모드 모두 정확히 동일한 HPA 기반 CPU 스케일링을 사용한다
   - B) Serverless 모드는 Knative의 동시성/RPS 기반 신호로 스케일링하고, Raw Deployment 모드는 CPU/메모리나 커스텀 메트릭을 사용하는 표준 HPA로 스케일링한다
   - C) Serverless 모드는 전혀 스케일링하지 않는다
   - D) Raw Deployment 모드가 Knative 동시성 기반으로 스케일링하고, Serverless 모드가 HPA를 사용한다

<details>
<summary>정답 보기</summary>

**정답: B) Serverless 모드는 Knative의 동시성/RPS 기반 신호로 스케일링하고, Raw Deployment 모드는 CPU/메모리나 커스텀 메트릭을 사용하는 표준 HPA로 스케일링한다**

**설명:**
Serverless 모드의 Knative 오토스케일러는 동시성이나 초당 요청 수 같은 요청 단위 신호에 반응하며, 이는 리소스 사용률 기반 신호보다 트래픽이 튀는 추론 워크로드에 더 빠르게 반응하는 경향이 있습니다. 반면 Raw Deployment 모드는 클러스터의 다른 일반 Deployment와 동일한, 표준 Kubernetes HorizontalPodAutoscaler에 의존합니다.
</details>

7. KServe의 내장 캐너리 롤아웃 메커니즘은 이 문서의 다른 곳에서 다루는 Istio/Argo Rollouts 트래픽 분산 패턴과 어떤 관계인가요?
   - A) 이름만 다를 뿐 정확히 동일한 메커니즘이다
   - B) KServe의 캐너리 롤아웃은 KServe 컨트롤 플레인에 내장된, 서비스 메시나 점진적 배포 컨트롤러의 트래픽 분산과는 구분되는 모델 서빙 전용 메커니즘이다
   - C) KServe에는 캐너리 롤아웃 기능이 없으며 반드시 Argo Rollouts를 사용해야 한다
   - D) Istio 트래픽 분산이 있으면 InferenceService 자체가 필요 없어진다

<details>
<summary>정답 보기</summary>

**정답: B) KServe의 캐너리 롤아웃은 KServe 컨트롤 플레인에 내장된, 서비스 메시나 점진적 배포 컨트롤러의 트래픽 분산과는 구분되는 모델 서빙 전용 메커니즘이다**

**설명:**
KServe는 자체적으로 stable 리비전과 canary 리비전 사이에 트래픽을 분산시키고, 신뢰가 쌓일수록 점진적으로 트래픽을 옮길 수 있습니다. 이는 `InferenceService` 리비전 단위에서 구체적으로 동작하며, 플랫폼의 다른 워크로드에 사용되는 Istio나 Argo Rollouts 기반 트래픽 분산 패턴과는 다른 도구입니다 — 기존 방식을 대체해야 한다는 뜻이 아니라, 모델 서빙에 특화된 별개의 경로입니다.
</details>

8. `InferenceService`의 predictor가 EKS에서 GPU를 요청할 때 Karpenter는 어떤 역할을 하나요?
   - A) Karpenter가 KServe predictor의 추론 프로토콜을 구성한다
   - B) 기존 노드로 충족할 수 없는 GPU 요청이 있으면 Karpenter가 그에 맞는 GPU 기반 EC2 인스턴스를 프로비저닝하고, 더 이상 필요 없어지면 그 용량을 통합·회수할 수 있다
   - C) Karpenter는 GPU device plugin을 대체한다
   - D) Karpenter는 Raw Deployment 모드에서만 동작하며 Serverless 모드에서는 동작하지 않는다

<details>
<summary>정답 보기</summary>

**정답: B) 기존 노드로 충족할 수 없는 GPU 요청이 있으면 Karpenter가 그에 맞는 GPU 기반 EC2 인스턴스를 프로비저닝하고, 더 이상 필요 없어지면 그 용량을 통합·회수할 수 있다**

**설명:**
EKS에서의 GPU 추론은 GPU device plugin이 노출하는 리소스에 대한 표준 Kubernetes 리소스 요청 모델을 따릅니다. Karpenter의 GPU 노드 풀은 스케줄링되지 못하는 GPU 요청에 반응해 맞는 용량을 프로비저닝하고, predictor가(특히 Serverless 모드에서 0으로 스케일 다운되는 경우) 더 이상 그 용량을 필요로 하지 않게 되면 통합 동작을 통해 회수할 수 있습니다 — 이는 EKS의 다른 곳에서도 쓰이는 2단계 오토스케일링 패턴입니다.
</details>

## 단답형 문제

9. 트래픽이 간헐적이고 튀는 모델에는 Serverless 모드가 좋은 선택이지만, 매 요청마다 일관되게 낮은 지연이 필요한 모델에는 좋지 않은 이유를 한두 문장으로 설명하세요.

<details>
<summary>정답 보기</summary>

**정답: Serverless 모드의 scale-to-zero는 유휴 기간 동안 GPU 비용을 절약할 수 있어, 대부분의 시간 동안 모델이 유휴 상태인 간헐적/버스트성 트래픽에 적합합니다. 하지만 0에서 다시 스케일 업할 때 콜드 스타트 지연(Pod 스케줄링, 컨테이너 시작, 모델 로드)이 발생하므로, 매 요청마다 일관되게 낮은 지연이 필요한 워크로드에는 받아들일 수 없는 방식입니다.**

**설명:**
이 트레이드오프는 본질적으로 비용(유휴 시 GPU 절감)과 지연 예측 가능성(콜드 스타트 없음) 사이의 문제입니다. Raw Deployment 모드는 최소 레플리카 수를 항상 웜 상태로 유지함으로써 이 트레이드오프를 반대로 뒤집으며, 대가로 유휴 상태에서도 그 용량에 대한 비용을 지불합니다.
</details>

10. KServe에서 predictor의 빌트인 프레임워크 지원과 커스텀 컨테이너 predictor는 어떻게 다른가요?

<details>
<summary>정답 보기</summary>

**정답: (SKLearn, XGBoost, TorchServe를 통한 PyTorch, NVIDIA Triton 등의) 빌트인 predictor 서버를 사용하면 predictor 스펙이 모델 아티팩트 위치만 지정해도 서빙 코드를 작성하지 않고 동작하는 서버를 얻을 수 있습니다. 이런 빌트인 프레임워크 범위를 벗어나는 경우에는 커스텀 컨테이너 predictor를 사용해야 하며, 이 컨테이너는 KServe의 추론 프로토콜을 직접 구현해야 합니다.**

**설명:**
이 구분은 서빙 측 구현 작업이 얼마나 필요한지를 결정합니다. 빌트인 서버는 흔히 쓰이는 프레임워크를 기본으로 지원하지만, 그 외의 경우에는 KServe 프로토콜을 이해하는 컨테이너를 직접 작성해야 합니다.
</details>

11. KServe 자체의 스케일링 결정과 그에 대한 Karpenter의 대응 사이의 2단계 오토스케일링 관계를 설명하세요.

<details>
<summary>정답 보기</summary>

**정답: KServe는(Serverless 모드에서는 Knative를 통해, Raw Deployment 모드에서는 HPA를 통해) 요청 단위 신호나 리소스 사용률 신호를 바탕으로 얼마나 많은 predictor Pod가 필요한지를 결정합니다 — 노드에 대한 정보가 없는 Pod 단위의 판단입니다. Karpenter는 그 결과로 생기는 Pod 스케줄링 상태(스케줄링되지 못한 GPU 요청, 또는 비어버린 GPU 노드)에 별도로 반응하여 얼마나 많은 EC2 GPU 용량을 프로비저닝하거나 회수할지를 결정합니다 — Pod가 왜 존재하는지는 모르는 노드 단위의 판단입니다.**

**설명:**
이 둘은 Pod 수/스케줄링 상태를 통해서만 연결되는 독립적인 두 제어 루프입니다 — 이 문서의 다른 곳에서 EKS의 다른 오토스케일 워크로드에 대해 설명하는 것과 동일한, 잡/Pod 단위 판단이 먼저 일어나고 노드 단위 판단이 그 결과에 반응하는 2단계 오토스케일링 패턴입니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/kubeflow/06-kserve.md)

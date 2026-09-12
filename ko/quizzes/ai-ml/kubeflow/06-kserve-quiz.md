# KServe 퀴즈

기준: KServe 0.18.0 / Community Distribution 26.03.1.

## 객관식 문제

1. KServe와 Kubeflow의 관계는 무엇인가요?

   - A) KFServing에서 발전했고 의존성을 갖추면 독립 실행 가능
   - B) Katib의 새로운 이름
   - C) 항상 전체 Kubeflow 배포판 필요
   - D) Kubernetes를 대체

<details>
<summary>정답 보기</summary>

**정답: A) KFServing에서 발전했고 의존성을 갖추면 독립 실행 가능**

전체 Kubeflow와 Models Web Application이 모든 KServe 설치의 필수 조건은 아닙니다.
</details>

2. 이 장의 검토 버전은 무엇인가요?

   - A) 웹앱 0.16.1만
   - B) Community 26.03.1의 KServe·웹앱 0.18.0; 확인한 최신 KServe는 0.20.0
   - C) 모든 컴포넌트 버전은 반드시 달라야 함
   - D) 웹앱 표시가 모든 설치 CRD를 결정

<details>
<summary>정답 보기</summary>

**정답: B) Community 26.03.1의 KServe·웹앱 0.18.0; 확인한 최신 KServe는 0.20.0**

컨트롤러, CRD, 웹앱은 별도 산출물이며 실제 호환성과 리비전을 기록해야 합니다.
</details>

3. InferenceService의 필수 컴포넌트는 무엇인가요?

   - A) Explainer
   - B) Transformer
   - C) Predictor
   - D) 세 가지 모두

<details>
<summary>정답 보기</summary>

**정답: C) Predictor**

Transformer와 explainer는 선택 사항이며 runtime·프로토콜 호환성과 실제 설명 요청 경로를 확인해야 합니다.
</details>

4. Knative를 선택하면 모든 유휴 predictor가 자동으로 0이 되나요?

   - A) 추가 설정 없이 항상 0
   - B) 아니며 KServe 기본 minReplicas는 1이고 minReplicas 0 등의 autoscaler·정책 조건이 필요
   - C) 항상 0이며 EC2 과금도 즉시 중지
   - D) Knative 설치 불필요

<details>
<summary>정답 보기</summary>

**정답: B) 아니며 KServe 기본 minReplicas는 1이고 minReplicas 0 등의 autoscaler·정책 조건이 필요**

0에서 다시 시작하면 용량, 이미지, 모델 로드 지연이 있습니다. Pod가 0이라고 노드가 종료되는 것은 아닙니다.
</details>

5. Standard 모드에 대한 올바른 설명은 무엇인가요?

   - A) 항상 웜 상태의 정상 replica 보장
   - B) Deployment·Service를 사용하며 기본 HPA는 최소 1, 구성된 KEDA 경로는 0 지원 가능
   - C) 항상 Knative 필요
   - D) autoscaling 선택지 없음

<details>
<summary>정답 보기</summary>

**정답: B) Deployment·Service를 사용하며 기본 HPA는 최소 1, 구성된 KEDA 경로는 0 지원 가능**

KEDA 설치, 유효한 메트릭·trigger, activation 경로가 필요합니다. 두 모드 모두 재시작·롤아웃·확장 때 시작 지연이 있습니다.
</details>

6. 0.18.0의 새 배포 모드 이름은 무엇인가요?

   - A) Serverless와 RawDeployment만 유효
   - B) Knative와 Standard; 이전 이름은 deprecated 별칭
   - C) HPA와 GPU
   - D) Predictor와 Transformer

<details>
<summary>정답 보기</summary>

**정답: B) Knative와 Standard; 이전 이름은 deprecated 별칭**

실제 annotation과 config를 확인해야 합니다. 코드 fallback은 Standard지만 확인한 OCI 리소스 차트 기본값은 Knative입니다.
</details>

7. 검토한 canaryTrafficPercent는 어떻게 동작하나요?

   - A) KServe 컨트롤러가 모든 요청 직접 중계
   - B) KServe가 Knative revision traffic을 설정하고 networking 계층이 요청 분배
   - C) 모든 Standard Deployment가 같은 revision 분할 자동 수행
   - D) Argo Rollouts 필수

<details>
<summary>정답 보기</summary>

**정답: B) KServe가 Knative revision traffic을 설정하고 networking 계층이 요청 분배**

Standard rolling update는 같은 revision 비율 라우팅이 아닙니다. 승격·롤백과 아티팩트 보존을 별도로 검증해야 합니다.
</details>

8. nvidia.com/gpu 요청만으로 GPU 추론이 보장되나요?

   - A) 모든 모델에 보장
   - B) 아니며 드라이버, 이미지·backend, 모델·device 설정도 맞아야 함
   - C) 모든 드라이버 자동 설치
   - D) 노드 용량 불필요

<details>
<summary>정답 보기</summary>

**정답: B) 아니며 드라이버, 이미지·backend, 모델·device 설정도 맞아야 함**

자원 할당과 실제 모델 실행은 다릅니다. Karpenter도 정책·할당량·가용 용량 조건에서 적합한 용량을 공급합니다.
</details>

## 단답형 문제

9. 상시 웜 상태와 scale-to-zero가 두 모드를 절대적으로 나누는 기준이 아닌 이유는 무엇인가요?

<details>
<summary>정답 보기</summary>

Knative도 최소 replica 설정으로 웜 Pod를 유지할 수 있고 Standard도 적합한 외부 신호를 사용하는 KEDA 경로가 있습니다. 어느 모드도 가용성·지연을 자동 보장하지 않으므로 readiness, 로드, 용량, 복구를 검증해야 합니다.
</details>

10. 아티팩트 URI만으로 충분하지 않은 이유와 TorchServe의 취급을 설명하세요.

<details>
<summary>정답 보기</summary>

runtime, 모델 형식·파일 구조, 라이브러리 버전, 자격 증명, 포트, 프로토콜이 맞아야 합니다. TorchServe는 적극적 유지보수와 예정된 보안 수정이 없다고 공지하므로 오래된 runtime 목록에 있다는 사실을 유지보수되는 기본 선택의 근거로 삼으면 안 됩니다.
</details>

11. Pod autoscaling과 EC2 scaling의 관계는 무엇인가요?

<details>
<summary>정답 보기</summary>

Knative/HPA/KEDA 등 선택한 scaler가 Pod 수를 결정하고 Kubernetes 스케줄링과 Karpenter 용량 정책이 노드 공급·회수에 영향을 줍니다. 모델 Pod가 0이어도 다른 워크로드나 중단 정책 때문에 EC2 노드와 비용이 남을 수 있습니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/kubeflow/06-kserve.md)

# SageMaker AI로 Qwen PII 파인튜닝하기

> 문서 검토: 2026-09-12. AWS provisioning 결과는 2026-09-01의 과거 실험 기록입니다.

이 가이드북은 Qwen/Qwen3-30B-A3B-Instruct-2507의 QLoRA 실험을 위한 설계와
component-tested 예제 패키지를 설명합니다. 관리형 SageMaker Training Job과
임시 EKS GPU Job이 같은 소스·합성 데이터·평가 코드를 사용하도록 구성되어 있습니다.
**두 GPU 경로의 end-to-end 학습 성공을 검증한 가이드가 아닙니다.**

현재 고정한 PyTorch 2.8 DLC는 2026-08-06에 패치 지원이 종료되어 **자원 생성·GPU 실행을 차단**합니다. 지원되는 이미지·의존성 조합으로 갱신해야 하며, [실행 장](03-sagemaker-mlflow-execution.md)에서 로컬 검증과 재개 조건을 설명합니다.

모델은 `TYPE<TAB>ORIGINAL` 후보를 출력하고 Python 코드가 검증·치환·복원을 담당합니다.
결정론적 치환이나 round-trip 성공이 모든 PII 탐지, 완전한 마스킹 또는 익명성을
보장하지는 않습니다. 놓친 엔터티와 잘못 분류한 값은 별도로 평가합니다.

## 5부 학습 경로

| Part | 주제 |
| --- | --- |
| [1](01-platform-architecture.md) | 플랫폼 책임과 목표 아키텍처 |
| [2](02-pii-data-tokenization.md) | 합성 데이터·토큰 치환·평가 한계 |
| [3](03-sagemaker-mlflow-execution.md) | SageMaker/EKS 실행 계약과 MLflow |
| [4](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md) | Unified Studio domain/project/membership |
| [5](04-validation-results.md) | 실행한 것과 측정하지 않은 것 |

## 검증 기록

| 구분 | 범위 |
| --- | --- |
| 2026-09-12 로컬 재검사 | 초기 30개 검사 이후 토큰화·평가·실행·정리 회귀 검사 추가; GPU와 AWS API 실행 없음 |
| 2026-09-01 AWS 기록 | 쿼터·MLflow App과 project provisioning 실패 경로 |
| 그 기록에서 미실행 | SageMaker Training Job / EKS GPU Job |
| 당시 정리 결과 | App/S3/IAM 실험 자원 정리, Unified Studio project 1개 잔존 |

현재 AWS 계정을 조회하지 않았으므로 잔존 project가 지금도 존재한다고 주장하지 않습니다.
다시 실행하기 전 최신 ownership·inventory를 확인합니다. 측정하지 않은 fine-tuned F1,
GPU peak memory·학습 시간·비용을 결과값으로 제시하지 않습니다.

## 실험 정책과 한계

- Seed 42의 합성 데이터만 사용하고 split/hash를 기록합니다.
- 일반 로그와 MLflow에는 원문·추출값·token mapping·raw completion을 보내지 않도록 설계합니다.
  Autolog/tracing과 artifact 내용도 실제 실행에서 검증해야 합니다.
- Private inventory에는 정리에 필요한 resource ID/ARN을 보관할 수 있지만 공개 보고서는 요약합니다.
  Presigned URL은 접근 권한이 포함된 임시 URL로 취급합니다.
- Smoke/full 전환은 검토한 실행 결과에 근거하고, 정리는 이번 실행의 소유 자원에 한정합니다.
- Model ID/seed/direct dependency pin만으로 완전한 재현성이나 두 환경의 동등한 보안을 보장하지 않습니다.

예제 패키지: `examples/ai-ml/qwen-pii-finetuning/`.

## 참고 자료

- [Qwen model card](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)
- [QLoRA paper](https://arxiv.org/abs/2305.14314)
- [Experiment configuration](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/config/experiment.yaml)
- [Recorded provisioning result](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)

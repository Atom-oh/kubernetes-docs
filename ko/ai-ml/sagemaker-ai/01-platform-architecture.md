# Part 1: SageMaker Qwen PII 플랫폼 아키텍처

> 검토: 2026-09-12. 그림은 목표 설계이며 과거 AWS 기록에서 두 GPU 학습 경로는 미실행입니다.

현재 PyTorch 2.8 DLC의 패치 지원 종료로 GPU 실행이 차단됩니다. [실행 장](03-sagemaker-mlflow-execution.md)의 지원되는 런타임 갱신 조건을 먼저 확인합니다.

![Target design: managed and EKS execution, candidate extraction, deterministic processing, aggregate tracking and owned-resource cleanup.](../../.gitbook/assets/ko-ai-ml-sagemaker-ai-01-platform-architecture-0.png)

[Interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/ko-ai-ml-sagemaker-ai-01-platform-architecture-0.html)

## 1. 책임과 기록 경계

| 구성 요소 | 책임과 한계 |
| --- | --- |
| 합성 데이터 생성기 | Config 기준 1,600/200/400 split, 총 2,200문서; generator·seed·hash로 추적 |
| S3 / 데이터 전달 | Source/data/artifact 보관; IAM·encryption·보존·전송 경로를 별도로 관리 |
| Qwen + QLoRA | 엔터티 후보 추출을 위한 adapter 학습 설계; 최종 치환·탐지 완전성 보장은 별개 |
| Python 처리·평가 | 허용 유형/원문 포함 검사, 치환·복원과 집계; 모델이 놓친 엔터티를 자동 보완하지 않음 |
| MLflow | 설정·버전·집계 비교; 서버 접근 제어와 로그/artifact 내용 검증 필요 |
| Unified Studio | 이 실험이 선택한 project 거버넌스; QLoRA/EKS/Training Job의 필수 기술 의존성은 아님 |
| Inventory / teardown | Private resource 식별자·소유권·의존성 기록, export·정리·잔존 검증 |

원문이나 token mapping을 가진 산출물은 통제해야 합니다. Token 치환은 매핑이 있으면
복원 가능한 처리이며 암호화와 같지 않습니다. 로그 정책은 목표/계약이지 모든 library,
callback, exception이나 자동 추적을 실제로 검증했다는 뜻은 아닙니다.
Resource ID/ARN은 private inventory에서 필요할 수 있으며 공개 보고서와 구분합니다.

## 2. 같은 계약, 다른 실행 환경

| 항목 | SageMaker AI 경로 | EKS 경로 |
| --- | --- | --- |
| 실행 | 관리형 Training Job | 이 실험을 위해 준비한 GPU Job/cluster |
| 추적 | SageMaker MLflow App | ClusterIP MLflow |
| 데이터 | S3 input channel | ServiceAccount 범위의 AWS 권한으로 S3 SDK 다운로드 |
| 수명 | Job 종료와 외부 App/bucket 등의 정리를 구분 | 결과 export 후 소유한 임시 자원 정리 |

Training Job이나 namespace/Job이라는 단위만으로 강한 격리가 자동 완성되지는 않습니다.
실제 IAM/SA, network, storage, endpoint·MLflow 접근과 container 설정을 검증합니다.
EKS 경로는 ServiceAccount에 연결한 workload identity와 SDK credential chain을
사용합니다. Pod 환경 변수에 presigned URL을 넣지 않으며 입력 manifest의
SHA-256과 버킷 소유 계정도 확인합니다.

비교에는 config·split hash·학습/평가 코드·step 수뿐 아니라 model/tokenizer revision,
image digest, 실제 transitive dependency, CUDA/driver·hardware와 decoding 설정도 필요합니다.
Seed를 고정해도 모든 GPU 연산과 환경 결과가 동일해지는 것은 아닙니다.
현재 requirements.lock은 직접 package version pin이며 모든 transitive 환경의 완전한 lock은 아닙니다.

## 3. 모델과 제안된 QLoRA 설정

기준은 Qwen/Qwen3-30B-A3B-Instruct-2507입니다. 모델 카드는 **총 30.5B / 활성 3.3B
파라미터**의 MoE이며 non-thinking 전용이라고 설명합니다.
활성 파라미터 수를 저장해야 할 전체 가중치나 GPU 메모리 크기로 해석하지 않습니다.
이 모델을 현재 최신 모델 또는 특정 GPU에서 검증된 선택으로 제시하지 않습니다.

검토 시 모델 repository revision은 `0d7cf23991f47feeb3a57ecb4c9cee8ea4a17bfe`였습니다. 현재 loader/config는
model ID를 사용하며 이 revision을 명시적으로 고정하지 않습니다. 실행을 재현하려면
model/tokenizer revision과 artifact를 함께 고정해야 합니다.

| 설정 | Config의 제안 값 |
| --- | --- |
| Quantization / compute | 4-bit NF4, double quantization / bfloat16 |
| LoRA rank / alpha / dropout | 16 / 32 / 0.05 |
| Sequence length | 1,024 |
| Device batch / gradient accumulation | 1 / 8 |
| Smoke / full | 10 / 80 steps |
| Job runtime 설정 | 10,800초 |

이 값은 학습 성공·충분한 품질·GPU peak memory의 측정값이 아닙니다.
Job deadline은 전체 provisioning/tracking/storage 수명이나 비용 상한과도 다릅니다.
QLoRA는 base weight를 낮은 정밀도로 사용하고 adapter를 학습하는 접근이며,
실제 module coverage·optimizer·memory와 모델 호환성은 실행 시 확인해야 합니다.

## 4. Governance와 실행 준비

이 실험은 GPU 제출 전에 의도한 domain/profile·caller membership·MLflow 접근을
확인하도록 설계되어 있습니다. CreateProject의 membershipAssignments는 같은 요청에
owner를 전달할 수 있지만 전체 provisioning의 원자적 rollback을 보장하지 않습니다.
Project ACTIVE와 필요한 tool/environment readiness도 별도로 확인합니다.

과거 시도처럼 App 등 일부 자원이 project 실패 전에 생성될 수 있으므로, 생성 전
권한 검사와 생성 후 inventory·보상 정리를 함께 사용합니다.
정리는 이번 실행이 소유한 자원에 한정하며 현재 잔존 상태를 과거 기록만으로 판정하지 않습니다.
자세한 identity/삭제 경계는 [Unified Studio 장](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md)을 따릅니다.

## 검증 범위

Config·trainer source·공개 model card와 역사적 보고서를 대조했고, 초기 30개 로컬 검사 이후
토큰화·실행·정리 관련 회귀 검사를 추가했습니다. 모델 weights 다운로드, GPU 학습,
추론 품질 평가나 현재 AWS resource 재조회는 하지 않았습니다.

## 참고 자료

- [Qwen model card](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)
- [QLoRA paper](https://arxiv.org/abs/2305.14314)
- [Experiment configuration](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/config/experiment.yaml)
- [Recorded provisioning result](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)

[Next: PII data and tokenization](02-pii-data-tokenization.md)

[Quiz](../../quizzes/ai-ml/sagemaker-ai/01-platform-architecture-quiz.md)

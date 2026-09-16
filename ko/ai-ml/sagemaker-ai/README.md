# SageMaker AI로 Qwen PII 파인튜닝하기

> **마지막 업데이트**: 2026년 9월 16일

합성 데이터 CPU 실습과 QLoRA 학습 해설을 포함합니다. 2026-09-16에는 별도 런타임으로 실제 GPU 시험 학습을 완료했습니다. 2026-09-01 provisioning 기록은 과거 실험으로 구분합니다.

이 가이드는 문서에서 개인정보 후보를 찾는 모델을 어떻게 학습시키고 평가할지 설명합니다. 학습 데이터의 정답을 정의하고, 데이터 누수를 막으며 증강한 뒤, QLoRA 설정을 선택하고 누락·과잉 가림을 측정하는 순서로 진행합니다.

모델의 출력은 `TYPE<TAB>ORIGINAL` 후보입니다. 최종 문서는 Python 코드가 검증·치환하며, 모델이 원문 전체를 다시 작성하지 않습니다. 이 구조를 이해하면 모델의 탐지 오류와 처리 코드의 치환 오류를 따로 디버깅할 수 있습니다.

## 먼저 따라가는 실습 경로

| 순서 | 읽고 실행할 장 | 완료 후 설명할 수 있어야 하는 것 |
| --- | --- | --- |
| 1 | [합성 데이터와 증강 실습](06-data-augmentation-workshop.md) | Annotation 계약, family 분리, train-only 증강, 원문·label 감사 |
| 2 | [QLoRA 학습과 SageMaker 흐름](05-qlora-finetuning-workshop.md) | NF4·LoRA·loss mask, 실제 target module, batch/step, 튜닝 변수와 진단 |
| 3 | [PII 평가와 비식별화 파이프라인](07-pii-evaluation-release.md) | Recall/F1, 잔여 PII, 음성 문서의 과잉 가림, 최종 평가와 승인 |
| 4 | [SageMaker AI와 MLflow 실행 계약](03-sagemaker-mlflow-execution.md) | 소스·S3 channel·Training Job·artifact·정리의 연결 |

Python 3.12와 JSONL을 읽을 수 있으면 데이터·평가 실습부터 시작할 수 있습니다. 이 두 CPU 실습에는 AWS 계정이나 모델 weights가 필요하지 않습니다. QLoRA 장의 학습기 해설과 GPU 점검 절차는 실제 GPU 학습 성공 기록과 구분합니다.

새 증강 실습은 40개 합성 family를 먼저 분리하고 train만 증강하는 별도 데이터셋입니다. 기존 generator 1.0.0의 2,200개 레코드를 덮어쓰지 않습니다. 작은 실습 세트의 수치나 oracle 결과를 실제 업무 모델의 성능으로 제시하지 않습니다.

## SageMaker 실행 준비 상태

2026-09-16의 [실제 GPU 시험 기록](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/execution-smoke-20260916.json)은 PyTorch 2.11·AL2023·CUDA 13 환경에서 같은 Qwen 모델을 NF4로 불러와 attention projection 네 종류에 rank-16 LoRA를 적용한 별도 경로입니다. 4스텝 후 실제 어댑터 가중치 변경과 저장·재로딩 일치를 확인했습니다. 과금 시간 1,140초의 GPU 계산 비용 추정은 약 1.46달러이며 저장·로그·세금 등은 제외합니다.

단, 생성 검사는 합성 검증 문서 4개뿐입니다. 원본 모델은 entity F1 1.0000이지만 형식 준수는 2/4였고, 튜닝 모델은 F1 0.8125·형식 준수 4/4와 함께 불필요한 후보 6개를 추가했습니다. **실행 성공이 성능 개선을 뜻하지 않습니다.** 같은 날 600스텝 본 학습을 제출했으며, 이 기록에는 최종 테스트 결과가 아직 포함되지 않습니다. 본 학습은 validation loss로 checkpoint를 선택한 다음 별도 테스트 400개를 평가하도록 구성했습니다. [실행 설정과 결과 보관 방식](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/README.md#recorded-gpu-execution-september-16-2026)을 참고하세요.

현재 역사적 실행 패키지는 Qwen/Qwen3-30B-A3B-Instruct-2507을 관리형 SageMaker Training Job 또는 임시 EKS GPU Job으로 학습하도록 설계되어 있습니다. 두 GPU 경로의 end-to-end 성공은 기록되어 있지 않습니다.

이 과거 경로의 고정된 PyTorch 2.8 DLC는 2026-08-06 패치 지원 종료로 자원 생성·GPU 실행이 차단됩니다. [QLoRA 실습의 런타임 설명](05-qlora-finetuning-workshop.md)과 [실행 계약](03-sagemaker-mlflow-execution.md)을 따라 이미지·의존성·MLflow 조합을 함께 검증해야 합니다. 지원 확인 코드만 제거하는 절차는 제공하지 않습니다.

## 설계와 구현을 깊게 읽기

| 문서 | 역할 |
| --- | --- |
| [Part 1: 플랫폼 아키텍처](01-platform-architecture.md) | 모델·데이터·Python 처리·MLflow의 책임 |
| [Part 2: 데이터와 결정론적 토큰화](02-pii-data-tokenization.md) | 기존 9유형 데이터, 치환 구간, 지표의 정확한 계산 |
| [Part 3: 실행](03-sagemaker-mlflow-execution.md) | SageMaker/EKS 제출·저장·실패 복구·정리 |
| [Part 4: Unified Studio 거버넌스](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md) | Domain/project/membership |
| [Part 5: 실제 검증 기록](04-validation-results.md) | 실행한 작업, 미실행 작업, 역사적 잔존 상태 |

## 검증 기록을 읽는 방법

- 새 데이터·평가 명령은 합성 자료를 대상으로 CPU에서 검사합니다. 학습 F1·GPU peak memory·학습 시간의 측정은 별도입니다.
- 2026-09-12 검토는 토큰화·평가·실행·정리의 로컬 회귀 검사를 보강했습니다.
- 2026-09-01 AWS 기록은 quota·MLflow App·project provisioning 실패 경로이며, GPU 학습 제출 전에 중단됐습니다.
- 그 기록에서는 실험 App/S3/IAM을 정리했지만 Unified Studio project 하나가 남았습니다. 현재 잔존 여부는 새 inventory 조회로 확인해야 합니다.

원문·추출값·token mapping·raw completion은 일반 로그나 MLflow parameter/tag에 기록하지 않습니다. Autolog/tracing과 artifact 내용도 실행 환경에서 확인합니다. 복원 가능한 mapping, 학습 adapter, private resource inventory는 서로 다른 산출물이며 보관·접근 정책을 각각 정합니다.

예제 패키지: `examples/ai-ml/qwen-pii-finetuning/`. 정확한 CLI와 출력 예시는 각 실습 장에 있습니다.

## 참고 자료

- [Qwen model card](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)
- [QLoRA paper](https://arxiv.org/abs/2305.14314)
- [실험 설정](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/config/experiment.yaml)
- [과거 provisioning 결과](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)

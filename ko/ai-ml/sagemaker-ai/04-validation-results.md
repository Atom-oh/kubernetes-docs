# Part 5: SageMaker Qwen PII 실제 검증 결과

> **마지막 업데이트**: 2026년 9월 12일
> **AWS 검증일**: 2026년 9월 1일
> **당시 상태**: GPU 학습 시작 전 차단 · 잔존 자원 기록은 9월 2일 기준

## 결론

이 장은 저장소의 **2026년 9월 1~2일 실험 기록**을 설명합니다. 당시 로컬 검사와 AWS provisioning·부분 정리 결과를 보존한 문서이며, 현재 AWS 계정 상태를 새로 조회한 결과가 아닙니다. 9월 12일 코드 검토에서는 기존 30개 검사로 발견하지 못했던 토큰화·평가·실행 및 정리 오류를 추가로 확인했습니다.

그러나 세 번째 provisioning 시도에서 project membership이 누락됐고, 호출 역할은 생성된 프로젝트를 삭제할 수 없었습니다. 추가 자원 생성을 중단했기 때문에 **SageMaker Training Job과 EKS GPU Job은 모두 미실행**입니다.

## 확인된 사실

| 항목 | 결과 |
|---|---|
| 기준 모델 | `Qwen/Qwen3-30B-A3B-Instruct-2507` |
| 합성 레코드 | 2,200 |
| Train / Validation / Test | 1,600 / 200 / 400 |
| 한국어 / 영어 | 80% / 20% |
| 당시 Python 계약·회귀 테스트 | 30개 통과; GPU 실행이나 모든 오류의 부재를 증명하지 않음 |
| 추출 계약 | `TYPE<TAB>ORIGINAL` |
| 관찰된 SageMaker MLflow App 버전 | `3.10.1` |
| SageMaker training executed | `false` |
| EKS training executed | `false` |
| 2026년 9월 2일 잔존 project | 1개, `ACTIVE` |

## 실제 실행 흔적

아래 그림은 저장된 기록에 나타난 **로컬 검증, AWS preflight, 세 번의 provisioning 시도, 정리와 중단 지점**입니다. 흐름은 GPU 학습 전에 종료됩니다. GPU 미실행은 전체 실험 비용이 0원이라는 의미가 아닙니다.

![로컬 검증, 세 번의 SageMaker와 Unified Studio 프로비저닝 시도, 부분 정리, 프로젝트 1개 ACTIVE 상태와 GPU 학습 미실행으로 이어지는 실제 검증 워크플로.](../../.gitbook/assets/ko-ai-ml-sagemaker-ai-04-validation-results-0.png)

[🔍 인터랙티브 검증 워크플로 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-ai-ml-sagemaker-ai-04-validation-results-0.html)

> 한국어로 작성한 노드와 카드는 그대로 표시되지만, Archify Viewer의 고정 컨트롤은 지원 언어 정책에 따라 영어로 표시됩니다.

## 세 번의 Provisioning 시도

| 시도 | 실제 결과 | GPU 학습 | 정리 결과 |
|---|---|---|---|
| 1 | MLflow App이 `Created`에 도달했지만 초기 스크립트가 존재하지 않는 App `ACTIVE` 상태를 기다림 | 시작 안 함 | App·S3·IAM 회수, 잔존 0 |
| 2 | Unified Studio domain이 custom project resource tag를 거부 | 시작 안 함 | App·S3·IAM 회수, 잔존 0 |
| 3 | project는 생성됐지만 호출 role group profile의 project membership이 없음 | 시작 안 함 | App·S3·IAM 회수, project 1개 잔존 |

## 반영한 수정

당시에는 App 준비 상태, 프로젝트 태그 정책, owner membership과 재시도를 수정했다고 기록했습니다. 이 기록을 현재 자동화가 완전하다는 증거로 사용해서는 안 됩니다.

9월 12일 후속 검토에서는 같은 이름의 기존 자원을 삭제할 위험, 권한 오류를 자원 부재로 처리하는 문제, 설정 파일 경로 오류, EKS 어댑터 유실과 인터럽트 시 기록 누락을 확인했습니다. 수정된 실행·결과 보존 절차와 검증 범위는 [실행 장](03-sagemaker-mlflow-execution.md)을 따릅니다. 새 검사는 로컬·모의 API 검사이며 AWS 재실행 결과가 아닙니다.

`ListProjects`에서 보이지 않는 것만으로 삭제를 증명할 수 없습니다. 조회 권한·필터·페이지 범위를 확인하고, 직접 조회나 관리자 확인으로 실험 소유 자원의 상태를 판정합니다. 권한 오류·시간 초과는 **미확인**으로 남깁니다.

## 2026년 9월 2일 정리 상태

저장된 9월 2일 읽기 전용 재확인 기록:

| 자원 유형 | 상태 |
|---|---|
| SageMaker MLflow App | 잔존 없음 |
| 실험 S3 bucket | 잔존 없음 |
| 실험 IAM role | 잔존 없음 |
| EKS cluster / GPU instance | 생성하지 않음 |
| Unified Studio `qwen-pii-*` project | 1개 `ACTIVE` |

이 상태가 지금도 유지된다면 domain administrator와 기존 project owner가 권한과 소유권을 확인한 뒤 정리해야 합니다. 새 역할 이름으로 과거 membership이나 자원 소유권을 추정하지 않습니다.

## 측정하지 않은 항목

| 항목 | 결과를 게시하지 않는 이유 |
|---|---|
| fine-tuned entity F1 | adapter 학습과 tuned evaluation 미실행 |
| baseline 대비 개선폭 | 동일 GPU 환경의 baseline/tuned 결과가 없음 |
| 학습 시간 | SageMaker/EKS 학습 Job 미실행 |
| peak GPU memory | GPU process 미실행 |
| GPU 비용 | GPU Job이 시작되지 않아 두 경로를 비교할 측정값이 없음 |
| 전체 실험 비용 | MLflow App·S3 등 다른 자원의 청구까지 대조한 비용 보고서가 없음 |

설정 파일에 최대 runtime이나 step 수가 있다고 해서 실제 결과로 간주하지 않습니다.

## 재실행 게이트

다음 조건을 **순서대로 모두** 충족해야 합니다.

1. 과거 inventory와 실제 자원을 대조하고, **이 실험 소유 자원**의 잔존·미확인 상태를 해결합니다. 이름 prefix만 같은 타인의 자원을 삭제하지 않습니다.
2. 현재 계정·리전·쿼터·이미지·도메인 및 profile·owner membership을 읽기 전용으로 확인합니다.
3. 검토한 설정·소스·데이터 해시를 고정하고 업로드 결과를 확인합니다.
4. 실제 비용 발생을 전제로 SageMaker smoke run을 실행하고 결과 파일까지 보존합니다.
5. CloudWatch·MLflow의 원문 유출 여부를 검토합니다. 성공 상태나 허용 파일명만으로 자동 통과하지 않습니다.
6. 확인된 smoke 결과를 바탕으로 full Job 실행 여부를 결정합니다.

EKS 비교도 SageMaker smoke 결과와 데이터 해시를 먼저 고정한 뒤 별도 smoke/full 순서로 실행합니다.

## 증거 위치

- 구조화 결과: `examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json`
- 상세 검증 기록: `docs/superpowers/reports/2026-09-01-sagemaker-qwen-pii-validation.md`
- 실행 패키지: `examples/ai-ml/qwen-pii-finetuning/`

이전: [Part 4 — Unified Studio 거버넌스](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md)

처음으로: [SageMaker Qwen PII 가이드북](README.md)

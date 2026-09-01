# SageMaker Qwen PII 파인튜닝 검증 결과

> **검증일**: 2026년 9월 1일
> **리전**: `ap-northeast-2`
> **상태**: 학습 시작 전 차단됨

## 결론

합성 PII 데이터 생성, 결정론적 토큰화, 평가 지표 계산, SageMaker/EKS
런처와 정리 자동화까지 로컬 검증을 완료했다. AWS에서는 SageMaker MLflow
App과 Unified Studio 프로젝트 생성 경로를 실제로 검증했다.

그러나 Unified Studio 프로젝트를 생성할 때 현재 IAM 역할에 DataZone
프로젝트 membership이 할당되지 않아 `GetProject`와 `DeleteProject`가
거부됐다. 추가 리소스 생성을 중단했으므로 **파인튜닝 학습 Job은 실행되지
않았다.** 따라서 이 문서에는 fine-tuned 정확도, F1, 학습시간 또는 GPU 비용
수치를 기재하지 않는다.

## 로컬 검증 결과

| 항목 | 결과 |
|---|---:|
| 생성한 완전 합성 레코드 | 2,200개 |
| Train / Validation / Test | 1,600 / 200 / 400 |
| 한국어 / 영어 | 80% / 20% |
| Python 계약·회귀 테스트 | 30개 통과 |
| Qwen 학습 목표 | `TYPE<TAB>ORIGINAL` |
| 토큰 형식 | `[PERSON_1]`, `[PHONE_1]` |
| 기준 모델 | `Qwen/Qwen3-30B-A3B-Instruct-2507` |

데이터 해시는 다음과 같다.

| Split | SHA-256 |
|---|---|
| Train | `b98429fef0b103f24e8eaded069cbd2f6def5fbf8c083a5c7baf366c9fc1d21a` |
| Validation | `25ca38198d38e04be181e15b4e21a3c96d672f46f775ae1bc6c422ee4514f820` |
| Test | `6f6ef9a6b42297738b292d5149f2e6e323f7bcd6f2325b6bfbc04ae6d9d0ec21` |

모델은 마스킹된 문장을 직접 생성하지 않는다. PII 유형과 원문 문자열만
TSV로 추출하고, 별도 코드가 NFC 정규화, 원문 위치 정렬, 원본 우선 변형
매칭과 단일 정규식 치환을 적용한다.

## AWS 사전 점검

| 항목 | 실제 확인값 |
|---|---:|
| SageMaker `ml.g6e.4xlarge` Training Job 쿼터 | 1 |
| EC2 On-Demand G/VT 쿼터 | 768 vCPU |
| SageMaker PyTorch DLC | 확인 완료 |
| 기존 `qwen-pii-*` MLflow App/EKS 충돌 | 없음 |

Managed MLflow는 새 배포에 권장되는 SageMaker MLflow App API로 생성했다.
실제 App에서 MLflow `3.10.1`이 관측됐다.

## Provisioning 시도

| 시도 | 실제 결과 | GPU 학습 | 정리 결과 |
|---|---|---|---|
| 1 | App이 `Created`에 도달했지만 초기 스크립트가 존재하지 않는 `ACTIVE` 상태를 기다림 | 시작 안 함 | App·S3·IAM 회수, 잔존 0 |
| 2 | Unified Studio 도메인이 custom project resource tag를 거부 | 시작 안 함 | App·S3·IAM 회수, 잔존 0 |
| 3 | 프로젝트는 생성됐지만 현재 역할에 project membership이 없어 조회·삭제 거부 | 시작 안 함 | App·S3·IAM 회수, Unified Studio 프로젝트 1개 잔존 |

세 시도 모두 SageMaker Training Job과 EKS GPU 클러스터를 만들기 전에
중단됐다. 따라서 GPU 학습 비용은 발생하지 않았다.

## 반영한 수정

- MLflow App 준비 상태를 실제 API enum인 `Created`/`Updated`로 판정
- 삭제 상태 `Deleted`를 terminal 상태로 판정
- Unified Studio custom project tag가 금지된 도메인 지원
- 새 프로젝트 생성 시 현재 IAM role의 DataZone group profile을
  `PROJECT_OWNER`로 지정
- `GetProject` 대신 `ListProjects`로 삭제 대상 존재 여부 확인
- Service Quotas API에 adaptive retry 적용
- 오류나 인터럽트에서도 inventory 기반 teardown 실행

## 남은 자원과 조치

현재 남은 자원은 **Unified Studio 프로젝트 1개**다. App, S3 버킷과 IAM
실험 역할은 모두 삭제됐다. 잔존 프로젝트는 기존 Unified Studio 도메인
소유자가 포털에서 삭제하거나, 현재 역할의 DataZone group profile을
프로젝트 소유자로 추가한 후 삭제해야 한다.

이 프로젝트가 제거되기 전에는 preflight가 새 `qwen-pii-*` 실험을 차단한다.
학습 결과가 필요하면 프로젝트 삭제 후 SageMaker smoke test부터 다시
시작해야 한다.

구조화된 동일 결과는
`examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json`에
저장되어 있다.

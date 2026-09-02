# SageMaker AI로 Qwen PII 파인튜닝하기

> **마지막 업데이트**: 2026년 9월 2일

## 개요

이 가이드북은 `Qwen/Qwen3-30B-A3B-Instruct-2507`에 QLoRA를 적용해 문서에서 PII 엔터티를 추출하고, 결정론적 코드가 원문을 `[PERSON_1]`, `[EMAIL_1]` 같은 토큰으로 치환하는 과정을 다룹니다.

동일한 소스 코드와 합성 데이터셋을 두 실행 경로에서 사용합니다.

- **관리형 경로**: SageMaker AI Training Job + SageMaker MLflow App
- **Kubernetes 경로**: 임시 Amazon EKS GPU Job + MLflow on EKS

모델은 최종 마스킹 문서를 생성하지 않습니다. 모델의 책임은 한 줄에 하나씩 `TYPE<TAB>ORIGINAL`을 추출하는 데 한정되고, 검증·정렬·치환·복원은 테스트 가능한 Python 코드가 담당합니다.

## 5부 학습 경로

| Part | 주제 | 핵심 질문 |
|---|---|---|
| [Part 1](01-platform-architecture.md) | 플랫폼 아키텍처 | SageMaker AI, EKS, MLflow, Unified Studio의 책임을 어떻게 나누는가? |
| [Part 2](02-pii-data-tokenization.md) | PII 데이터와 토큰화 | 실제 PII 없이 학습 데이터를 만들고 누출을 어떻게 측정하는가? |
| [Part 3](03-sagemaker-mlflow-execution.md) | SageMaker AI와 MLflow 실행 | 동일한 학습 계약을 관리형·EKS 경로에서 어떻게 실행하는가? |
| [Part 4](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md) | Unified Studio 거버넌스 | domain, project profile, project, membership을 어떻게 운영하는가? |
| [Part 5](04-validation-results.md) | 실제 검증 결과 | 무엇을 실행했고, 어디서 중단했으며, 무엇을 측정하지 않았는가? |

## 현재 검증 상태

| 상태 | 확인된 범위 |
|---|---|
| **로컬 검증 완료** | 합성 데이터 생성, 토크나이저, 집계 메트릭, SageMaker/EKS 요청 계약 |
| **AWS에서 관찰** | 쿼터, SageMaker MLflow App, Unified Studio 프로젝트 생성 실패 경로 |
| **미실행** | SageMaker Training Job, EKS GPU Job |
| **차단 상태** | Unified Studio 프로젝트 1개 정리 대기 |

AWS 검증은 2026년 9월 1일 GPU 학습 시작 전에 중단됐습니다. 따라서 이 가이드북은 파인튜닝 후 F1, 학습 시간, GPU 메모리, GPU 비용을 결과값으로 제시하지 않습니다.

## 안전 원칙

1. 데이터는 seed `42`로 생성한 완전 합성 데이터만 사용합니다.
2. 원문, 추출값, 토큰 매핑, raw completion을 stdout, CloudWatch, MLflow parameter/tag에 기록하지 않습니다.
3. MLflow에는 설정, 버전, 데이터 해시, 집계 메트릭과 비민감 아티팩트만 남깁니다.
4. smoke run이 통과하기 전에는 full run을 시작하지 않습니다.
5. 실행 후 inventory 기반 teardown과 잔존 자원 확인을 완료합니다.

실행 가능한 예제 패키지는 `examples/ai-ml/qwen-pii-finetuning/`에 있습니다.

# SageMaker Unified Studio 거버넌스

> **마지막 업데이트**: 2026년 9월 2일

## 개요

Amazon SageMaker Unified Studio는 데이터와 AI 팀이 project 안에서 파일, 도구, 데이터 자산과 컴퓨팅 구성을 공유하도록 하는 관리형 작업 공간입니다. 이 섹션에서는 Unified Studio를 EKS에 배포하지 않습니다. 대신 Kafka, Spark, Airflow, Flink, ML 학습이 생산·소비하는 데이터와 실행 권한을 **어떤 domain과 project 경계에서 관리할지** 설명합니다.

Data on EKS와 함께 보는 이유는 다음과 같습니다.

- EKS 데이터 파이프라인이 생성한 데이터셋을 catalog asset으로 발견·공유할 수 있습니다.
- project profile과 blueprint를 통해 SQL, data engineering, ML experiment 도구의 준비 범위를 표준화할 수 있습니다.
- project membership으로 사용자와 자동화 role의 협업 권한을 분리할 수 있습니다.
- 관리형 SageMaker AI와 자체 운영 EKS 학습을 같은 데이터 거버넌스 원칙 아래 둘 수 있습니다.

## 이 가이드의 범위

| 주제 | 다루는 내용 |
|---|---|
| domain | 조직의 데이터·AI 거버넌스 경계 |
| project profile | project 생성 시 적용할 blueprint와 도구 템플릿 |
| project | 한 비즈니스 use case의 협업·자원 공유 경계 |
| catalog asset | 데이터 발견, 구독, 게시를 위한 메타데이터 |
| membership | project owner와 member의 권한 |
| lifecycle | 생성, ACTIVE 확인, 사용, 삭제, 잔존 확인 |

[Part 4: Domain, Project, Membership 거버넌스](01-domains-projects-governance.md)에서 Qwen PII 실험의 실제 실패 경로와 안전한 재실행 순서를 확인할 수 있습니다.

## 현재 검증 상태

2026년 9월 2일 읽기 전용 재확인에서 `qwen-pii-*` 프로젝트 **1개가 `ACTIVE`** 상태로 남아 있습니다. App, S3, IAM 실험 자원은 정리됐지만 project membership이 없는 현재 자동화 역할은 이 프로젝트를 삭제할 수 없습니다.

따라서 잔존 프로젝트를 domain owner가 삭제하거나 owner membership을 부여하기 전에는 새 실험을 시작하지 않습니다.

관련 가이드:

- [SageMaker Qwen PII 가이드북](../../ai-ml/sagemaker-ai/README.md)
- [Part 3: SageMaker AI와 MLflow 실행](../../ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md)
- [Part 5: 실제 검증 결과](../../ai-ml/sagemaker-ai/04-validation-results.md)

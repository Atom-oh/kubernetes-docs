# SageMaker Unified Studio 거버넌스

> 문서 검토: 2026-09-12. 실험 결과는 2026-09-01 기록과 9월 2일 문서의 과거 상태입니다.

Amazon SageMaker Unified Studio는 데이터·AI 팀의 협업, 도구와 catalog 자산을
관리하는 workspace입니다. EKS 데이터 파이프라인의 자산·사용자·실행 권한을
어느 domain/project에서 관리할지 설명합니다.
여기의 **Unified Studio/DataZone project**는 SageMaker AI의 MLOps Project나
SageMaker AI Studio domain과 같은 API 객체가 아닙니다.

## 이 섹션에서 확인할 것

| 주제 | 확인할 경계 |
| --- | --- |
| Domain 유형 | IAM-based와 IAM Identity Center-based의 로그인·관리 방식 |
| Project profile / blueprint | 생성 시 제공할 도구와 on-demand로 활성화할 도구 |
| Member / execution role | Portal·project 접근 identity와 실제 AWS resource 실행 identity |
| Membership / data access | Owner 등 관리 designation과 IAM·Lake Formation·catalog 데이터 권한 |
| Lifecycle | Project 존재·environment 준비·실제 도구 접근·소유 자원 정리 |

[Part 4: Domain, Project, Membership](01-domains-projects-governance.md)는 Qwen 실험의
실패 기록을 위 경계로 설명합니다. Unified Studio project는 이 가이드가 선택한
거버넌스 절차이며 모든 SageMaker Training Job/EKS 학습에 필수인 기술 의존성은 아닙니다.

## 실험 기록과 현재 상태를 구분

저장된 2026-09-01 validation JSON은 학습 시작 전 중단, App/S3/IAM 실험 자원 정리,
Unified Studio project 1개 잔존을 기록합니다. 9월 2일 문서에는 당시 ACTIVE
재확인이 기록되어 있습니다. **이번 문서 검토에서 AWS 계정을 다시 조회하지 않았으므로
현재도 1개가 남아 있다고 주장하지 않습니다.**

이 실험을 재개할 때는 권한 있는 주체가 최신 inventory·membership·정리 상태를
확인해야 합니다. 과거 오류를 해결하기 위해 무조건 새 권한을 부여하거나 공유 자원을
삭제하는 절차로 일반화하지 않습니다.

관련 가이드:

- [SageMaker Qwen PII 가이드북](../../ai-ml/sagemaker-ai/README.md)
- [Part 3: SageMaker AI와 MLflow](../../ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md)
- [Part 5: 실제 검증 결과](../../ai-ml/sagemaker-ai/04-validation-results.md)

## 참고 자료

- [IAM-based domains](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/iam-based-domains.html)
- [Project member and execution roles](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/projects-iam-based-domains.html)
- [User and group profiles](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/user-management.html)
- [CreateProject request and deployment status](https://docs.aws.amazon.com/boto3/latest/reference/services/datazone/client/create_project.html)
- [All capabilities profiles and on-demand provisioning](https://docs.aws.amazon.com/help-panel/sagemaker-unified-studio/latest/console/project-profiles-all-capabilities-hp.html)
- [Project deletion and external resources](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/userguide/delete-project.html)
- [Recorded Qwen provisioning validation](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)

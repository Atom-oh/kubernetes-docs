# Part 4: Domain, Project, Membership 거버넌스

> 문서 검토: 2026-09-12. Qwen provisioning 결과는 과거 실험 기록이며 현재 계정 상태를 재검증하지 않았습니다.

Qwen 실험 기록의 세 번째 시도는 project 생성 후 caller의 membership 문제로
조회·삭제가 거부되었다고 보고합니다. 학습은 시작되지 않았습니다.
이 사례를 모든 Unified Studio domain의 현재 상태나 모든 권한 실패의 유일한
원인으로 일반화하지 않습니다.

## 1. 객체와 identity를 구분

| 객체/역할 | 의미 |
| --- | --- |
| Unified domain / domain unit | 거버넌스 경계와 내부 조직 계층 |
| Project profile / blueprint | 도구·environment provision 구성과 허용된 account/region |
| Project | 협업·도구·자원 공유 경계 |
| User/group profile | SSO identity 또는 등록된 IAM role 등의 서비스 내부 표현 |
| Membership designation | PROJECT_OWNER, PROJECT_CONTRIBUTOR 등 project 관리 범위 |
| Project execution role | Project에서 AWS 데이터·compute에 접근하는 실행 identity |
| Catalog asset | 설명·schema·location 등 거버넌스 대상 메타데이터 |

IAM-based와 Identity Center-based domain의 설정·로그인 방식을 먼저 확인합니다.
Project member role과 execution role은 역할이 다르며 실제 ARN이 같을 수도 있습니다.
IAM-based project에서는 멤버들이 project execution role을 통한 데이터/compute
접근을 공유합니다. Owner designation만으로 사용자별 데이터 권한이 자동 분리되지 않습니다.
Identity-based 접근이나 Trusted Identity Propagation을 쓰면 해당 모델도 함께 검증합니다.

AWS user-management 문서는 domain에 추가된 IAM role의 group profile과, 그 role을
통해 로그인한 사용자의 session user profile을 구분합니다.
Membership은 role group profile로 관리할 수 있으며 rolePrincipalARN을 사용한
CreateGroupProfile은 **profile 등록**이지 IAM role 자체를 만드는 API가 아닙니다.
Project execution role의 자동 profile/membership 처리와 automation caller의 권한도
동일하다고 가정하지 않습니다.

## 2. Profile 이름은 도구 준비 상태가 아님

All capabilities는 blueprint 묶음의 template 이름입니다. Profile은 blueprint를
project 생성 때 provision하거나 나중에 on-demand로 활성화하도록 설정할 수 있습니다.
필요한 service·account·region·network와 profile 사용 권한을 확인합니다.

프로필 이름으로 처음 검색된 결과만 선택하지 말고 의도한 profile ID와 설정을
확인합니다. Qwen 실험에 필요한 범위가 작다면 필요한 capability만 제공하는 profile을
검토할 수 있지만, 조직의 승인된 구성과 실제 의존성을 먼저 확인합니다.
Unified Studio project가 없는 일반 SageMaker/EKS 학습 경로와도 구분합니다.

## 3. IAM, membership, 데이터 권한

IAM action 허용은 서비스 내부 project ownership을 대신하지 않습니다.
반대로 project owner라도 IAM·SCP·resource policy·데이터 접근 정책의 제한을
무시할 수 없습니다. 일반 member/contributor라는 이유만으로 삭제할 수 있는 것도
아닙니다. 삭제 경로에 필요한 project owner 또는 관리 권한을 확인합니다.

현재 CreateProject API는 membershipAssignments를 받습니다.
다음은 **요청 구조 예시**이며 domain/profile/group ID를 권한 있게 조회한 실제 값으로
바꿔야 합니다.

```json
{
  "domainIdentifier": "dzd-1111111111111111",
  "name": "docs-governance-example",
  "projectProfileId": "c1111111111111",
  "membershipAssignments": [
    {
      "member": {
        "groupIdentifier": "11111111-1111-1111-1111-111111111111"
      },
      "designation": "PROJECT_OWNER"
    }
  ]
}
```


member는 tagged union이므로 groupIdentifier와 userIdentifier 중 **하나만** 넣습니다.
같은 요청에 membership을 포함하면 별도 후속 요청이 실패하는 간극을 줄일 수 있지만,
전체 project/environment provision의 transaction 원자성·rollback을 보장한다는 뜻은 아닙니다.
CreateProject 응답과 실제 membership을 다시 확인합니다. Timeout 뒤 이름만 보고
새 project를 반복 생성하지 말고 기존 요청의 결과와 inventory를 먼저 확인합니다.

## 4. 생성·도구 준비 순서

1. 의도한 account/region/domain 유형과 profile ID를 확인합니다.
2. Caller login/profile, 필요한 owner/admin 및 execution-role 권한을 구분합니다.
3. 필요한 blueprint가 on-create인지 on-demand인지 확인하고 승인된 구성을 준비합니다.
4. CreateProject와 membership 결과를 저장·재조회합니다.
5. projectStatus와 environmentDeploymentDetails를 따로 확인합니다.
6. 필요한 environment/tool의 준비, 실제 read/write 권한을 확인한 뒤 다음 compute 단계를 진행합니다.

projectStatus=ACTIVE는 environment/tool이 전부 준비됐다는 뜻이 아닙니다.
overallDeploymentStatus에는 PENDING_DEPLOYMENT, IN_PROGRESS, SUCCESSFUL,
FAILED_VALIDATION, FAILED_DEPLOYMENT 등이 있습니다. On-demand로 의도적으로
아직 만들지 않은 도구까지 모두 실패로 취급하지 말고 **이번 작업에 필요한 것**을 확인합니다.

## 5. Tag 오류와 catalog 공개 범위

현재 API에는 resourceTags가 있습니다. 과거 실험의 tag 거부는 그 domain/요청의
실패 기록이며 “Unified Studio는 tag를 지원하지 않는다”는 뜻이 아닙니다.
실제 정책·값·원본 오류를 확인하고, 부분 실패 정리는 inventory에서 이번 실행이
생성했고 정리 권한이 있는 자원으로 한정합니다. Shared bucket/role을 prefix만 보고
일괄 삭제하는 근거로 사용하지 않습니다.

공개 문서에는 실험 횟수, 합성 데이터 schema·레코드 수, generator version/seed/hash,
소유·보존 원칙 같은 검토에 필요한 정보를 싣습니다. 실제 PII, credential,
presigned URL 또는 재식별용 mapping을 공개 산출물에 넣지 않습니다.

권한 통제된 **내부 catalog**에서는 데이터 발견/접근을 위해 storage location과
resource identifier가 필요할 수 있습니다. 공개 웹 문서의 식별자 비공개 원칙을
내부 catalog의 모든 location metadata 금지로 일반화하지 않습니다.
Metadata 공개, subscription 승인과 실제 데이터 권한 부여도 별도 단계입니다.

## 6. 삭제와 부재 검증

1. 보존할 데이터와 이번 실행의 소유 자원·의존성을 확인합니다.
2. 권한 있는 owner/admin context에서 해당 project의 작업을 중단하고 정리 범위를 확정합니다.
3. Project와 연결된 environment·managed 자원의 lifecycle에 맞춰 삭제합니다.
4. DELETING/DELETE_FAILED 등 상태와 오류를 확인하고 완료를 재검증합니다.
5. 관련 account/region에서 남는 외부 App·S3·IAM·compute 자원을 inventory와 대조합니다.

GetProject의 AccessDenied는 부재 증거가 아닙니다.
빈 ListProjects 결과도 visibility·filter·pagination이 제한되어 있으면 충분하지 않습니다.
의도한 domain/identity와 모든 page를 확인하고, 권한 있는 get/list 결과 및 외부 자원
inventory를 함께 사용합니다. Project 삭제가 외부 서비스 자원까지 모두 정리한다는
보장은 없으므로 데이터 보존과 소유권에 맞춰 별도 확인합니다.

## 7. Qwen 실험의 역사적 검증 범위

저장된 validation JSON의 날짜는 **2026-09-01**입니다.
기록에는 세 번 모두 trainingStarted=false, 세 번째 뒤 project 1개 잔존,
App/S3/IAM 실험 자원 정리가 담겨 있습니다. 9월 2일 문서는 당시 ACTIVE 재확인을
보고합니다. 이 장의 검토는 그 기록과 현재 공개 API 문서를 대조한 것이며,
현재 account에서 project가 존재·삭제되었는지 확인한 결과는 아닙니다.

재개 시에는 최신 inventory와 ownership을 다시 확인해야 합니다.
이 문서 수정 과정에서 project·membership·IAM·GPU 자원을 생성하거나 삭제하지 않았습니다.
요청 예시는 AWS CLI의 **로컬 output-skeleton 검증**으로 구조를 검사했고,
member에 두 identity 종류를 함께 넣은 변형은 ParameterValidation으로 거부됐습니다.
실제 API authorization이나 environment provision 성공으로 해석하지 않습니다.

## 참고 자료

- [IAM-based domains](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/iam-based-domains.html)
- [Project member and execution roles](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/projects-iam-based-domains.html)
- [User and group profiles](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/user-management.html)
- [CreateProject request and deployment status](https://docs.aws.amazon.com/boto3/latest/reference/services/datazone/client/create_project.html)
- [All capabilities profiles and on-demand provisioning](https://docs.aws.amazon.com/help-panel/sagemaker-unified-studio/latest/console/project-profiles-all-capabilities-hp.html)
- [Project deletion and external resources](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/userguide/delete-project.html)
- [Recorded Qwen provisioning validation](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)

[Previous: SageMaker AI / MLflow](../../ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md)

[Next: Validation results](../../ai-ml/sagemaker-ai/04-validation-results.md)

[Quiz](../../quizzes/data-on-eks/sagemaker-unified-studio/01-domains-projects-governance-quiz.md)

# Part 4: Domain, Project, Membership 거버넌스

> **마지막 업데이트**: 2026년 9월 2일

## 왜 이 장이 필요한가

Qwen PII 검증은 GPU나 모델 코드가 아니라 Unified Studio project membership에서 멈췄습니다. 세 번째 provisioning 시도에서 project는 생성됐지만 호출 역할의 group profile이 project member로 추가되지 않았고, 그 결과 조회·삭제가 거부됐습니다.

이 사례는 IAM 권한과 Unified Studio 내부 권한이 서로 다른 계층임을 보여줍니다.

## 객체 모델

| 객체 | 역할 | 운영 질문 |
|---|---|---|
| **SageMaker unified domain** | 사용자, project profile, catalog, 정책을 묶는 최상위 거버넌스 경계 | 어느 조직·계정·리전이 이 domain을 운영하는가? |
| **Domain unit** | domain 안의 조직 계층 | project와 정책을 어느 조직 단위에 배치하는가? |
| **Blueprint** | 도구·자원을 provision하는 구성 | 어떤 서비스와 리전에 자원을 만들 수 있는가? |
| **Project profile** | blueprint 모음으로 만든 project 템플릿 | 누가 이 profile로 project를 만들 수 있는가? |
| **Project** | 한 use case의 협업·파일·도구·자원 공유 경계 | owner와 member는 누구이며 삭제 책임자는 누구인가? |
| **Catalog asset** | 데이터의 설명, schema, 위치, 구독 가능한 메타데이터 | 원본 데이터 대신 어떤 메타데이터를 게시하는가? |
| **User/group profile** | SSO 사용자·그룹 또는 IAM role을 나타내는 내부 profile | 자동화 role의 group profile이 membership에 포함됐는가? |
| **Membership** | project와 profile 사이의 owner/member association | 생성·조회·멤버 관리·삭제를 누가 할 수 있는가? |

AWS 문서의 project 정의처럼, project는 collaboration boundary입니다. 강한 보안 격리가 필요하면 project만 믿지 말고 별도 AWS 계정과 데이터·네트워크 경계를 함께 사용합니다.

## Project profile과 All capabilities

Project profile은 project를 만드는 상위 템플릿이며 blueprint의 묶음입니다. `All capabilities` template은 Tooling blueprint를 바탕으로 시작하고, 관리자가 필요에 따라 다음 capability를 구성합니다.

- `MLExperiments`
- `Workflows`
- `LakehouseCatalog`
- `EmrOnEc2`
- `RedshiftServerless`
- `LakeHouseDatabase`
- `EmrServerless`
- `AmazonBedrockGenerativeAI`

이름이 `All capabilities`라고 해서 모든 blueprint가 즉시 준비됐다고 가정하지 않습니다. profile이 enabled인지, 필요한 blueprint가 대상 리전에 enabled인지, project 생성 권한을 누가 가졌는지 확인해야 합니다.

Qwen 예제는 enabled `All capabilities` profile을 찾지만, 학습 자체에는 모든 capability가 필요하지 않습니다. 조직 표준에 맞춘 custom profile로 Tooling과 ML experiment 범위만 제공하는 편이 더 적절할 수 있습니다.

## IAM 권한과 DataZone authorization

두 권한 계층을 분리해 생각합니다.

| 계층 | 허용하는 것 | 충분하지 않은 것 |
|---|---|---|
| IAM | `CreateProject`, `ListProjects`, `DeleteProject` 같은 API 호출 시도 | 특정 project의 owner/member association |
| Unified Studio/DataZone authorization | domain owner, project owner, project member의 context별 작업 | AWS API에 접근할 IAM permission |

IAM role이 domain에 추가되면 Unified Studio는 group profile을 만듭니다. project membership과 access policy는 이 group profile을 통해 관리됩니다.

프로젝트 생성 시 실행 role의 group profile을 owner로 함께 지정하는 형태는 다음과 같습니다.

```json
[
  {
    "member": {
      "groupIdentifier": "<execution-role-group-profile>"
    },
    "designation": "PROJECT_OWNER"
  }
]
```

project owner는 project member를 추가·제거하고 asset 게시 같은 project-level 작업을 관리할 수 있습니다.

## 안전한 생성 순서

1. `ListDomains`와 조직 설정으로 대상 domain을 확인합니다.
2. enabled project profile과 필요한 blueprint/region readiness를 확인합니다.
3. 호출 IAM role에 대응하는 group profile을 찾습니다.
4. project 생성 요청에 owner membership을 원자적으로 포함합니다.
5. project가 `ACTIVE`가 될 때까지 상태를 확인합니다.
6. owner context에서 project 조회와 member 관리를 검증합니다.
7. 그 뒤에만 MLflow App과 GPU 실행 경로를 승인합니다.

membership을 생성 후 별도 단계로 추가하면, 중간 실패 시 “프로젝트는 있으나 자동화 역할은 접근할 수 없는” 상태가 생길 수 있습니다.

## Tag 정책과 project 생성

두 번째 provisioning 시도에서는 domain이 custom project resource tag를 거부했습니다. 일반 AWS resource에 사용한 실험 tag를 Unified Studio project 생성에도 무조건 전달하면 안 됩니다.

- domain/project profile 정책이 허용하는 tag만 사용합니다.
- lifecycle 추적은 로컬 inventory와 안전한 resource name prefix로 보완합니다.
- tag 거부 시 project 생성 요청만 수정하고, 이미 만든 App·S3·IAM은 teardown합니다.

## Catalog asset 설계

PII 학습 데이터는 실제 고객 PII가 아니라 합성 데이터라도 최소 공개 원칙을 따릅니다.

게시하기 적합한 메타데이터:

- split별 레코드 수와 언어 비율
- schema와 9개 entity type
- generator version, seed, SHA-256
- 소유 팀, 보존 기간, 승인된 사용 목적

게시하지 않는 값:

- source text 전체
- entity original 값
- raw model completion
- token mapping
- presigned URL이나 내부 storage 식별자

## 삭제와 잔존 확인

안전한 삭제는 “delete API가 성공했다”에서 끝나지 않습니다.

1. 새 GPU 실행을 막습니다.
2. project의 owner membership을 확인합니다.
3. project에 연결된 environment와 resource를 정리합니다.
4. project 삭제를 요청합니다.
5. `ListProjects`에서 대상이 사라질 때까지 재확인합니다.
6. App, S3, IAM, EKS, EC2와 tag inventory를 별도로 검사합니다.
7. 잔존 개수가 0일 때만 inventory를 닫습니다.

`GetProject`가 authorization 오류를 반환하더라도 project가 없다고 간주하면 안 됩니다. 존재 확인과 teardown 검증에는 권한이 허용되는 list API를 사용하고, list 결과의 정확한 ID는 문서에 게시하지 않습니다.

## 2026년 9월 2일 상태

읽기 전용 재확인 결과:

| 항목 | 상태 |
|---|---|
| `qwen-pii-*` Unified Studio project | 1개 |
| project status | `ACTIVE` |
| SageMaker MLflow App | 잔존 없음 |
| 실험 S3/IAM 자원 | 잔존 없음 |
| 필요한 조치 | domain owner 삭제 또는 실행 role에 owner membership 부여 후 삭제 |

이 project가 제거되기 전에는 preflight가 새 실행을 차단해야 합니다.

이전: [Part 3 — SageMaker AI와 MLflow 실행](../../ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md)

다음: [Part 5 — 실제 검증 결과](../../ai-ml/sagemaker-ai/04-validation-results.md)

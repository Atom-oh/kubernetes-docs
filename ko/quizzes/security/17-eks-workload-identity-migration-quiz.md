# EKS 워크로드 IAM 이전 퀴즈

1. 노드의 S3 읽기 정책을 회수한 뒤 레거시 Pod의 `GetCallerIdentity`는 성공하고 `GetObject`는 거부됩니다. 어떤 일이 일어난 것인가요?

   <details>
   <summary>정답 보기</summary>

   IMDSv2에서 받은 자격 증명으로 노드 역할의 신원을 확인했습니다. 해당 역할에서 객체 읽기 권한을 제거했으므로 S3는 요청을 거절합니다.

   </details>

2. IRSA와 Pod Identity는 각각 어느 경로로 임시 자격 증명을 얻나요?

   <details>
   <summary>정답 보기</summary>

   IRSA의 SDK는 projected ServiceAccount 토큰을 STS `AssumeRoleWithWebIdentity`로 교환합니다. Pod Identity의 SDK는 노드 에이전트에 토큰을 보내고, 에이전트는 EKS Auth를 통해 역할 자격 증명을 받아 반환합니다.

   </details>

3. 이전 카나리에서 어떤 증거를 확인한 뒤 노드 정책을 회수하나요?

   <details>
   <summary>정답 보기</summary>

   새 Pod가 기대한 워크로드 역할로 동작하며 필요한 AWS API 호출을 성공하는지 확인합니다. 배치 및 컨트롤러를 포함한 다른 의존성, 임시 자격 증명 갱신, 롤백용 정책도 확인합니다.

   </details>

[실전 글과 데모](../../security/17-eks-workload-identity-migration.md)

# Crossplane 퀴즈

[Crossplane](../../platform-engineering/07-crossplane.md)

원문의 8개 주제를 Crossplane 2.4 기준으로 검토했습니다.

## 1. Composition은 무엇을 해결하나요?

<details>
<summary>정답 보기</summary>

Function pipeline으로 XR의 입력을 여러 자원의 원하는 상태로 변환합니다. 여러 AWS 작업이 원자적 transaction으로 실행되거나 모두 준비됐다는 보장은 아닙니다.

</details>

## 2. v2 XR와 기존 Claim의 관계는 무엇인가요?

<details>
<summary>정답 보기</summary>

XRD v2는 기본 Namespaced이며 개발자가 XR을 직접 만들 수 있습니다. 기존 v1 LegacyCluster XRD는 cluster XR과 namespaced Claim의 호환 경로를 유지합니다. 모든 XR/MR이 cluster 범위라는 설명은 현재 API에 맞지 않습니다.

</details>

## 3. IRSA나 Pod Identity만 선택하면 최소 권한 구성이 끝나나요?

<details>
<summary>정답 보기</summary>

아닙니다. 실제 ServiceAccount·OIDC audience/subject 또는 association과 role policy를 구성해야 합니다. Provider별 runtime 소유권, ProviderConfig 작성·참조 권한과 AssumeRole 경계도 제한합니다.

</details>

## 4. Terraform과 Crossplane의 주요 차이는 무엇인가요?

<details>
<summary>정답 보기</summary>

둘 다 선언적 상태를 다루지만 Terraform은 plan/apply workflow, Crossplane은 지속적 controller reconciliation을 중심으로 합니다. Terraform 실행도 자동화할 수 있고 Crossplane 조정도 provider·정책·quota·오류의 영향을 받습니다.

</details>

## 5. ACK와 Crossplane은 어떻게 공존하나요?

<details>
<summary>정답 보기</summary>

각 도구가 관리할 외부 리소스의 소유권을 분리합니다. ACK도 namespace CR과 참조를 제공하며 kro로 조합할 수 있습니다. 같은 AWS 리소스를 여러 controller가 경쟁 수정하도록 구성하지 않습니다.

</details>

## 6. v2 Connection Secret은 어떻게 제공하나요?

<details>
<summary>정답 보기</summary>

MR의 writeConnectionSecretToRef는 유지되지만 XR core native publication은 제거됐습니다. Secret을 compose하거나 지원 Function의 집계를 사용합니다. 본문 P&T 예제는 endpoint와 username만 합성하며 password는 사전 준비한 별도 Secret을 사용합니다.

</details>

## 7. Backstage와 GitOps의 올바른 흐름은 무엇인가요?

<details>
<summary>정답 보기</summary>

준비된 skeleton/action으로 XR YAML 생성 → 검토한 PR merge → ArgoCD 적용 → Crossplane/Provider 조정 → 실제 readiness 확인 순서입니다. PR 생성, catalog 등록, AWS 생성 완료는 서로 다른 상태입니다.

</details>

## 8. drift 수정과 삭제 보존은 무엇으로 제어하나요?

<details>
<summary>정답 보기</summary>

Provider의 지원 필드와 managementPolicies, poll 설정 등을 확인합니다. 이 v2 namespace MR에서는 Delete를 제외해 외부 자원을 보존하며 legacy deletionPolicy: Orphan과 구분합니다. 보존해도 backup·credential·비용·후속 소유권 책임은 남습니다.

</details>

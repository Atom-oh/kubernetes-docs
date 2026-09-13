# Backstage IDP 퀴즈

[Backstage](../../platform-engineering/06-backstage-idp.md)

원문의 8개 주제를 Backstage 1.54.7 검토 내용에 맞춰 정리했습니다.

## 1. 마이크로서비스를 나타내는 catalog kind는 무엇인가요?

<details>
<summary>정답 보기</summary>

Component이며 spec.type으로 service 등을 구분합니다. Catalog의 Resource는 인프라를 기술하는 엔티티이지 AWS 리소스를 생성하는 controller가 아닙니다.

</details>

## 2. Software Template이 실제로 생성하는 것은 무엇인가요?

<details>
<summary>정답 보기</summary>

등록한 action과 제공한 skeleton이 구현한 파일·외부 작업만 실행합니다. 본문의 작은 예제는 catalog/TechDocs 세 파일을 생성하며 runtime 앱이나 DB를 배포하지 않습니다. Golden Path도 승인·권한·필수 정책을 대신하지 않습니다.

</details>

## 3. Kubernetes workload와 catalog 엔티티를 어떻게 연결하나요?

<details>
<summary>정답 보기</summary>

backstage.io/kubernetes-id 또는 지원 label-selector annotation을 실제 workload label과 맞춥니다. namespace/cluster 선택과 credential·RBAC도 필요합니다. 이 metadata matching은 사용자별 접근 제어가 아닙니다.

</details>

## 4. EKS에서 PostgreSQL과 Secret을 어떻게 준비하나요?

<details>
<summary>정답 보기</summary>

RDS 같은 외부 PostgreSQL을 선택하면 chart의 내장 PostgreSQL을 끄고 TLS·네트워크·schema·migration 권한과 backup을 구성합니다. Secret은 승인된 파일 mount로 제공하고 app-config의 $file 경로를 맞춥니다. 관리형 DB 선택만으로 HA·복구 검증이 끝나지는 않습니다.

</details>

## 5. TechDocs는 무엇으로 빌드하고 어떻게 제공하나요?

<details>
<summary>정답 보기</summary>

MkDocs와 techdocs-core로 빌드합니다. external 모드에서는 CI publisher가 S3 등에 게시하고 Backstage backend가 읽어 UI에 제공합니다. reader와 publisher 권한, entity key·root path를 맞추며 S3 공개 접근이 필요하지 않습니다.

</details>

## 6. 단계적으로 도입할 때 무엇부터 갖추나요?

<details>
<summary>정답 보기</summary>

정확한 소유권과 source를 갖춘 Software Catalog를 작은 범위부터 운영하고 templates/TechDocs를 확장할 수 있습니다. 인증·권한·신뢰 경계는 나중으로 미루지 않고 시작 단계부터 준비합니다.

</details>

## 7. GitHub와 ArgoCD 작업이 자동 연결되려면 무엇이 필요한가요?

<details>
<summary>정답 보기</summary>

각 backend action module, credential·권한과 실제 input/output schema가 필요합니다. Roadie 1.8.1의 argocd:create-resources는 배포 대상 namespace를 받으며 revision 입력은 없습니다. PR 생성 뒤 아직 main에 없는 catalog 파일을 바로 등록하지 말고 merge 후 처리합니다.

</details>

## 8. 팀 소유권에 따라 삭제를 제한하려면 어떻게 하나요?

<details>
<summary>정답 보기</summary>

실제 PermissionPolicy module을 등록하고 catalog delete에 IS_ENTITY_OWNER 조건을 반환한 뒤 catalog backend가 이를 평가하게 합니다. 본문 정책은 명시한 작업 외에는 DENY합니다. catalog 소유권, GitHub 쓰기와 ArgoCD 배포 권한은 별개이며 Group/User source도 보호해야 합니다.

</details>

# Platform Engineering 개요 퀴즈

[관련 문서](../../platform-engineering/00-platform-engineering-overview.md)

## 1. 플랫폼 엔지니어링의 핵심 목표는 무엇인가요?

<details>
<summary>정답 및 설명</summary>

개발자 요구를 이해하고 승인된 셀프서비스 API·CLI·포털·템플릿과 운영 지원을 내부 제품으로 제공하는 것입니다. 운영팀을 없애거나 모든 application 책임을 대신하는 것이 아닙니다.
</details>

## 2. Start·Advance·Excel과 도구 매핑은 어떻게 해석하나요?

<details>
<summary>정답 및 설명</summary>

AWS platform engineering 상세 가이드의 개선 과제 구분입니다. IaC와 셀프서비스 자동화는 Advance에서 설명하지만 문서의 Kubernetes 도구 매핑은 학습 예시이며 공식 인증 점수나 모든 조직의 필수 순서는 아닙니다.
</details>

## 3. Platform Engineering, DevOps와 SRE는 어떤 관계인가요?

<details>
<summary>정답 및 설명</summary>

서로 보완하는 접근입니다. 플랫폼 팀은 개발자 경험과 반복 가능한 제품을, DevOps는 협업 문화·delivery를, SRE는 신뢰성·운영 engineering을 강조합니다. 팀 형태나 계층 관계가 모든 조직에서 고정되지는 않습니다.
</details>

## 4. IDP의 계층과 Backstage 포털의 범위는 무엇인가요?

<details>
<summary>정답 및 설명</summary>

본문의 interface·orchestration·resource·infrastructure는 참조 모델입니다. Backstage 같은 포털은 interface의 일부이며 실제 provisioning, 정책, runtime, 문서·지원까지 모두 대신하지 않습니다.
</details>

## 5. Golden Path에서 벗어나면 필수 보안 정책도 생략할 수 있나요?

<details>
<summary>정답 및 설명</summary>

아닙니다. Golden Path는 지원되는 권장 경로이지만 예외도 조직의 승인과 필수 보안·데이터 정책을 따라야 합니다. 모든 경우에 최적이라는 보장도 없습니다.
</details>

## 6. WebApplication 하나를 만들면 KRO가 항상 Deployment·RDS·IAM을 생성하나요?

<details>
<summary>정답 및 설명</summary>

아닙니다. WebApplication은 예시 사용자 API이며 대응 RGD/CRD가 먼저 있어야 합니다. RGD가 선언한 Kubernetes 리소스를 kro가 관리하고, ACK service controller가 권한을 갖고 AWS API를 호출합니다. 생성 조합과 readiness·삭제 정책은 정의에 따라 다릅니다.
</details>

## 7. 현재 DORA 지표와 활용 방식은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

change lead time, deployment frequency, failed deployment recovery time, change fail rate, deployment rework rate입니다. 서비스·팀의 delivery와 안정성을 개선하는 데 사용하며 일반 MTTR이나 개인 순위로 대체하지 않습니다. Excel 이전에도 측정할 수 있습니다.
</details>

## 8. Guardrail이 있으면 보안과 규정 준수가 자동 보장되나요?

<details>
<summary>정답 및 설명</summary>

아닙니다. 정책을 실제로 적용하고 우회·예외·권한·변경을 검증하며 감사와 복구를 운영해야 합니다. guardrail은 application의 데이터 처리 책임이나 법적 요구 검토를 대신하지 않습니다.
</details>

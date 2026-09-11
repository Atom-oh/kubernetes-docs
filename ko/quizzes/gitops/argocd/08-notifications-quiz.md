# ArgoCD 알림 퀴즈

이 퀴즈는 ArgoCD 알림 시스템과 알림에 대한 이해도를 테스트합니다.

1. ArgoCD에서 알림을 처리하는 컴포넌트는 무엇인가요?
   - A) Application Controller
   - B) Notifications Controller (argocd-notifications)
   - C) API Server
   - D) Repo Server

<details>
<summary>정답 보기</summary>

**정답: B) Notifications Controller (argocd-notifications)**

**설명:**
ArgoCD Notifications Controller는 ArgoCD Applications를 모니터링하고 구성된 트리거와 템플릿을 기반으로 알림을 보냅니다. 핵심 ArgoCD에 병합된 별도의 컴포넌트입니다.

</details>

2. ArgoCD에서 알림 구성은 어디에 저장되나요?
   - A) 전용 CRD에
   - B) argocd-notifications-cm ConfigMap에
   - C) Application spec에
   - D) 환경 변수에

<details>
<summary>정답 보기</summary>

**정답: B) argocd-notifications-cm ConfigMap에**

**설명:**
알림 서비스, 템플릿 및 트리거는 `argocd-notifications-cm` ConfigMap에 구성됩니다. 웹훅 URL과 같은 민감한 데이터는 `argocd-notifications-secret`에 저장됩니다.

</details>

3. ArgoCD 알림에서 "트리거"란 무엇인가요?
   - A) 수동 알림 전송 버튼
   - B) 알림을 보낼 시기를 결정하는 조건
   - C) 웹훅 엔드포인트
   - D) 알림 템플릿

<details>
<summary>정답 보기</summary>

**정답: B) 알림을 보낼 시기를 결정하는 조건**

**설명:**
트리거는 알림을 보내야 할 시기를 결정하는 조건(동기화 상태 변경, 헬스 변경 또는 동기화 실패와 같은)을 정의합니다. 알림 내용을 포맷하는 템플릿을 참조합니다.

</details>

4. 특정 Application의 metadata에서 알림 구독을 직접 지정하는 방법은 무엇인가요?
   - A) Application의 replica 수 변경
   - B) Application에 알림 구독 어노테이션 추가
   - C) NotificationSubscription CRD 생성
   - D) ArgoCD UI에서 구성

<details>
<summary>정답 보기</summary>

**정답: B) Application에 알림 구독 어노테이션 추가**

**설명:**
Applications는 `notifications.argoproj.io/subscribe.on-sync-succeeded.slack: my-channel`과 같은 어노테이션을 통해 알림을 구독합니다. 트리거, 서비스 및 수신자를 지정합니다. 중앙 ConfigMap의 `subscriptions` 또는 AppProject 어노테이션으로도 구독할 수 있습니다. 여러 수신자는 세미콜론으로 구분합니다.

</details>

5. ArgoCD가 기본으로 지원하는 알림 서비스는 무엇인가요?
   - A) Slack만
   - B) 이메일만
   - C) Slack, Teams, 이메일, 웹훅 등 여러 개
   - D) 없음, 모두 커스텀 플러그인 필요

<details>
<summary>정답 보기</summary>

**정답: C) Slack, Teams, 이메일, 웹훅 등 여러 개**

**설명:**
Argo CD는 Slack, Teams Workflows, GitHub, 이메일, 일반 Webhook, SQS 등 여러 서비스 형식을 지원합니다. 서비스 자격 증명과 트리거·템플릿·구독을 구성해야 해당 수신자로 전송됩니다. 템플릿에 여러 서비스가 있어도 자동으로 모두에게 보내지 않습니다. 기존 Opsgenie 통합은 공지된 제품 종료 일정에 맞춰 이전해야 합니다.

</details>

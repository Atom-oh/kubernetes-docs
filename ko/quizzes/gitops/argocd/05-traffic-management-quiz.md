# ArgoCD 트래픽 관리 퀴즈

이 퀴즈는 ArgoCD와 Argo Rollouts를 사용한 점진적 배포 및 트래픽 관리에 대한 이해도를 테스트합니다.

1. Argo Rollouts란 무엇인가요?
   - A) ArgoCD를 위한 로깅 솔루션
   - B) 점진적 배포 전략을 위한 Kubernetes 컨트롤러
   - C) Git 브랜치 관리 도구
   - D) 트래픽 모니터링 대시보드

<details>
<summary>정답 보기</summary>

**정답: B) 점진적 배포 전략을 위한 Kubernetes 컨트롤러**

**설명:**
Argo Rollouts는 카나리 배포, 블루-그린 배포, 자동화된 분석을 통한 점진적 배포와 같은 고급 배포 기능을 제공하는 Kubernetes 컨트롤러입니다.

</details>

2. 명시한 트래픽 비중 단계와 분석 게이트를 통해 새 버전을 검증하는 배포 전략은 무엇인가요?
   - A) Recreate
   - B) Rolling Update
   - C) Canary
   - D) Blue-Green

<details>
<summary>정답 보기</summary>

**정답: C) Canary**

**설명:**
카나리 배포는 이전 버전에서 새 버전으로 트래픽을 점진적으로(예: 10%, 25%, 50%, 100%) 이동시켜 각 단계에서 테스트와 검증을 할 수 있게 합니다.

</details>

3. Argo Rollouts를 사용한 Blue-Green 배포에서 프로모션 중에 무슨 일이 일어나나요?
   - A) Blue 환경이 삭제됨
   - B) active Service의 selector를 새 ReplicaSet으로 변경
   - C) 두 버전이 영원히 동시 실행
   - D) 새 환경이 생성됨

<details>
<summary>정답 보기</summary>

**정답: B) active Service의 selector를 새 ReplicaSet으로 변경**

**설명:**
Blue-Green 배포에서 프로모션은 활성 서비스 선택기를 업데이트하여 현재 안정 버전에서 미리보기 버전으로 트래픽을 전환합니다. 이전 ReplicaSet의 축소는 분석과 scale-down 지연 설정에 따라 진행되며 데이터플레인 전파가 즉시 완료된다고 보장하지 않습니다.

</details>

4. Argo Rollouts에서 AnalysisTemplate이란 무엇인가요?
   - A) 새 애플리케이션 생성을 위한 템플릿
   - B) 자동화된 카나리 분석을 위한 메트릭과 성공 기준 정의
   - C) 로깅 구성
   - D) 리소스 쿼터 템플릿

<details>
<summary>정답 보기</summary>

**정답: B) 자동화된 카나리 분석을 위한 메트릭과 성공 기준 정의**

**설명:**
AnalysisTemplates는 쿼리할 메트릭(Prometheus, Datadog 등에서)과 성공/실패 기준을 정의합니다. 롤아웃 중에 AnalysisRuns가 이 템플릿을 실행하여 배포를 계속할지 자동으로 결정합니다.

</details>

5. Argo Rollouts의 네이티브 트래픽 관리 provider는 무엇인가요?
   - A) Traefik만
   - B) NGINX Ingress만
   - C) NGINX, ALB, Istio, Traefik 등 여러 개
   - D) 없음, 수동 구성 필요

<details>
<summary>정답 보기</summary>

**정답: C) NGINX, ALB, Istio, Traefik 등 여러 개**

**설명:**
Argo Rollouts는 AWS ALB, Istio, Traefik, APISIX 등의 네이티브 통합을 제공합니다. ingress-nginx/SMI API가 남아 있어도 해당 프로젝트의 유지보수가 보장되는 것은 아닙니다. Linkerd를 위한 별도 네이티브 필드는 없습니다.

</details>

6. 트래픽 라우터와 기본 maxTrafficWeight=100을 사용하는 Canary 전략에서 `setWeight` 단계는 무엇을 하나요?
   - A) 파드의 CPU 가중치 설정
   - B) 카나리 버전으로 라우팅할 트래픽 비율 설정
   - C) 배포의 중요도 설정
   - D) 롤백 임계값 설정

<details>
<summary>정답 보기</summary>

**정답: B) 카나리 버전으로 라우팅할 트래픽 비율 설정**

**설명:**
카나리 전략의 `setWeight` 단계는 카나리(새) 버전으로 라우팅해야 할 트래픽 비율을 구성합니다. 예를 들어, `setWeight: 20`은 상대 가중치20/100을 요청합니다. 실제 요청 비율은 표본·연결·쿠키 등에 따라 달라질 수 있고, 라우터가 없으면 Pod 비율의 근사치입니다.

</details>

7. Rollout에 연결된 분석의 AnalysisRun이 Failed 상태가 되면 어떻게 되나요?
   - A) 배포가 상관없이 계속됨
   - B) 알림이 전송되지만 다른 일은 없음
   - C) 롤아웃을 중단하고 stable 트래픽으로 복귀
   - D) 클러스터가 종료됨

<details>
<summary>정답 보기</summary>

**정답: C) 롤아웃을 중단하고 stable 트래픽으로 복귀**

**설명:**
AnalysisRun이 실패하면(메트릭이 실패 임계값 초과) Argo Rollouts는 롤아웃을 중단하고 stable로 트래픽을 되돌립니다. Git 커밋이나 데이터베이스는 되돌리지 않으며, 개별 실패 측정과 전체 AnalysisRun 실패는 failureLimit에 의해 구분됩니다. Inconclusive는 조사할 수 있도록 일시 중지합니다.

</details>

8. 수동 검증을 위해 특정 단계에서 Rollout을 일시 중지하려면 어떻게 해야 하나요?
   - A) 기간 없이 `pause` 단계 사용
   - B) `stop` 단계 사용
   - C) duration: forever와 함께 `wait` 단계 사용
   - D) 불가능함

<details>
<summary>정답 보기</summary>

**정답: A) 기간 없이 `pause` 단계 사용**

**설명:**
기간 없이 `pause` 단계를 추가하면 계속하려면 수동 프로모션(CLI 또는 UI를 통해)이 필요한 무기한 일시 중지가 생성됩니다. 이는 배포 프로세스의 수동 검증 게이트에 유용합니다.

</details>

9. Kong Ingress Controller로 카나리 트래픽을 분할하려면 어떻게 해야 하나요?
   - A) `trafficRouting.kong` 필드를 직접 사용한다
   - B) Gateway API 플러그인(`trafficRouting.plugins`)을 통해 HTTPRoute를 조작한다
   - C) Kong은 Argo Rollouts와 연동할 수 없다
   - D) Istio VirtualService로 우회한다

<details>
<summary>정답 보기</summary>

**정답: B) Gateway API 플러그인(`trafficRouting.plugins`)을 통해 HTTPRoute를 조작한다**

**설명:**
Kong은 Argo Rollouts에 네이티브로 통합되어 있지 않습니다. `trafficRouting.kong`이라는 필드는 존재하지 않으며, argoproj-labs의 Gateway API 플러그인을 통해 표준 HTTPRoute 리소스를 조작하는 방식이 이 문서의 연동 경로입니다. Kong 외에도 Traefik, kgateway 등 Gateway API를 구현하는 다른 컨트롤러 역시 동일한 플러그인을 사용합니다.

</details>

10. Argo Rollouts Gateway API 플러그인이 카나리 weight 전환마다 실제로 갱신하는 대상은 무엇인가요?
    - A) Service의 `selector` 라벨
    - B) Ingress의 `canary-weight` 애노테이션
    - C) HTTPRoute의 `backendRefs[].weight`
    - D) DestinationRule의 subset 라벨

<details>
<summary>정답 보기</summary>

**정답: C) HTTPRoute의 `backendRefs[].weight`**

**설명:**
Gateway API 플러그인은 표준 Gateway API 리소스인 HTTPRoute의 `backendRefs[].weight` 값을 setWeight 단계마다 직접 갱신합니다. 이 방식은 Gateway API를 구현하는 어떤 컨트롤러(Kong, Traefik, kgateway 등)에도 적용할 수 있지만, 실제 CRD·구현체의 Route 기능 지원과 수렴 상태를 검증해야 합니다.

</details>

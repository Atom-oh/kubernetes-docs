# 09. 엣지 보안: WAF와 DDoS 방어 퀴즈

> **마지막 업데이트**: 2026년 11월 19일

[워크북](../../../networking/expert/09-edge-security-waf-ddos.md)으로 돌아갑니다.
문항마다 답 하나를 고르고 워크북의 어떤 규칙이 답을 뒷받침하는지 설명합니다.
설계 추론 문제이며 실제 웹 ACL을 배포했다는 주장이 아닙니다.

1. 봇넷이 CloudFront 배포로 SYN 플러드를 보냅니다. 오리진은 VPC 오리진 뒤의 internal ALB입니다. ALB가 SYN 플러드를 받지 않는 이유는?
   - A) 엣지의 Shield TCP SYN 프록시가 연결이 서비스에 닿기 전에 핸드셰이크를 검증하고(상태 없는 SYN 쿠키), CloudFront는 오리진과 자체 지속 연결을 유지하기 때문입니다.
   - B) WAF 웹 ACL의 속도 기반 규칙이 SYN 패킷을 Block하기 때문입니다.
   - C) ALB 보안 그룹이 너무 빨리 들어오는 SYN 패킷을 버리기 때문입니다.

<details>
<summary>정답 보기</summary>

**정답: A) 엣지의 Shield TCP SYN 프록시가 연결이 서비스에 닿기 전에 핸드셰이크를 검증하고(상태 없는 SYN 쿠키), CloudFront는 오리진과 자체 지속 연결을 유지하기 때문입니다.**

**설명:** SYN 플러드는 리스너의 반열림 연결 백로그를 바닥냅니다. 여기서 리스너는 CloudFront이고, Shield의 SYN 프록시는 핸드셰이크를 끝낸 연결만 통과시킵니다. 뷰어의 새 연결은 새 오리진 연결이 아닙니다. AWS WAF는 TCP 세그먼트가 아니라 HTTP 요청을 검사하며, 보안 그룹은 속도를 제한하지 않습니다.

</details>

2. UDP 반사 공격은 공격자에게 무엇을 요구하며, 어떤 네트워크 관행이 그것을 없애는가?
   - A) 반사 서버와 TCP 핸드셰이크를 끝내는 것. 모든 구간의 TLS가 없앱니다.
   - B) 피해자 주소를 출발지로 위조하는 능력. 출발지 주소 검증(BCP 38)이 없앱니다.
   - C) 올바른 HTTP 요청. WAF 속도 기반 규칙이 없앱니다.

<details>
<summary>정답 보기</summary>

**정답: B) 피해자 주소를 출발지로 위조하는 능력. 출발지 주소 검증(BCP 38)이 없앱니다.**

**설명:** 공격자는 피해자 주소를 출발지로 넣은 작은 UDP 요청(DNS, NTP, SSDP, CLDAP, Memcached 등)을 보내고, 반사 서버는 훨씬 큰 응답을 피해자에게 보냅니다. AWS 백서는 DNS의 증폭률을 28~54배로 듭니다. 출발지 주소를 검증하는 네트워크는 위조 능력을 없앱니다.

</details>

3. 요청이 작업이 CAPTCHA인 규칙과 일치하고, 유효하며 만료되지 않은 CAPTCHA 토큰을 가지고 있습니다. AWS WAF는 어떻게 하는가?
   - A) 요청을 Block하고 새 퍼즐을 보냅니다.
   - B) 즉시 Allow하고 평가를 멈춥니다.
   - C) Count처럼 처리하고 남은 규칙으로 평가를 계속합니다.

<details>
<summary>정답 보기</summary>

**정답: C) Count처럼 처리하고 남은 규칙으로 평가를 계속합니다.**

**설명:** CAPTCHA와 Challenge는 유효하고 만료되지 않은 토큰이 있으면 평가를 끝내지 않고, 토큰이 없거나 잘못되었거나 만료되었으면 평가를 끝내고 Block합니다(퍼즐이나 조용한 챌린지와 함께). Allow와 Block은 항상 평가를 끝내고 Count는 끝내지 않습니다. Block된 요청은 기본적으로 `403 (Forbidden)`을 받습니다.

</details>

4. 다음 속도 기반 규칙 구성 중 유효하지 **않은** 것은?
   - A) 평가 기간 300초, 한도 100, 작업 Block
   - B) 평가 기간 600초, 한도 10, 작업 Count
   - C) 평가 기간 300초, 한도 100, 작업 Allow

<details>
<summary>정답 보기</summary>

**정답: C) 평가 기간 300초, 한도 100, 작업 Allow**

**설명:** 속도 기반 규칙은 Allow를 뺀 모든 규칙 작업을 쓸 수 있습니다. 평가 기간은 60, 120, 300, 600초(기본 300초)이고 한도의 최솟값은 10이므로 A와 B는 모두 유효합니다.

</details>

5. HTTP 플러드 중에 엔지니어가 이미 트래픽을 Block하고 있는 속도 기반 규칙의 한도를 낮춥니다. 변경 직후 팀이 예상해야 할 것은?
   - A) 기존 카운트를 유지한 채 새 한도가 즉시 적용됩니다.
   - B) 변경으로 규칙의 카운트가 초기화되고 속도 제한이 최대 1분 멈출 수 있습니다.
   - C) 다음 평가 기간 전체가 지날 때까지 규칙이 동작하지 않습니다.

<details>
<summary>정답 보기</summary>

**정답: B) 변경으로 규칙의 카운트가 초기화되고 속도 제한이 최대 1분 멈출 수 있습니다.**

**설명:** 한도, 평가 기간, 집계, 전달 IP 구성, 범위를 바꾸면 카운트가 초기화됩니다. 속도 제한은 근사적이기도 해서, 속도를 넘은 뒤 몇 분까지 지나서야 제한이 시작될 수 있고 속도가 떨어진 뒤에도 잠시 이어질 수 있습니다. 속도 한도 변경은 사고 중이 아니라 사고 전에 계획합니다.

</details>

6. `AWSManagedRulesCommonRuleSet`의 각 규칙이 무엇을 Block할지 적용 전에 보고 싶습니다. 어떤 설정이 그것을 보여 주는가?
   - A) 규칙 그룹의 반환 작업을 Count로 재정의합니다.
   - B) 웹 ACL 기본 작업을 Count로 설정합니다.
   - C) `RuleActionOverrides`로 각 규칙의 작업을 Count로 재정의합니다.

<details>
<summary>정답 보기</summary>

**정답: C) `RuleActionOverrides`로 각 규칙의 작업을 Count로 재정의합니다.**

**설명:** 규칙별 재정의를 쓰면 일치한 요청을 그 규칙의 작업이 Count인 것처럼 처리하고, 그룹은 다른 규칙을 계속 평가합니다. 규칙 그룹 반환 작업을 Count로 재정의해도 그룹의 평가 방식은 바뀌지 않아서 첫 종료 일치에서 멈추므로, 그 요청에 대해 그룹의 뒤쪽 규칙은 실행되지 않습니다. 기본 작업은 Allow 또는 Block뿐입니다.

</details>

7. 우선순위 50의 규칙 `block-bad-ua`는 `awswaf:managed:aws:core-rule-set:NoUserAgent_Header`에 대한 레이블 일치 문입니다. 핵심 규칙 세트는 우선순위 100에 있고 해당 규칙은 Count로 재정의되어 있습니다. `block-bad-ua`가 절대 일치하지 않는 이유는?
   - A) 관리형 규칙 그룹은 레이블을 붙이지 않습니다.
   - B) 레이블은 그것을 붙인 규칙보다 나중에 평가되는 규칙에서만 쓸 수 있는데, 우선순위 50은 100보다 먼저 실행됩니다.
   - C) Count 규칙의 레이블은 버려집니다.

<details>
<summary>정답 보기</summary>

**정답: B) 레이블은 그것을 붙인 규칙보다 나중에 평가되는 규칙에서만 쓸 수 있는데, 우선순위 50은 100보다 먼저 실행됩니다.**

**설명:** AWS WAF는 숫자 우선순위가 가장 낮은 규칙부터 평가하고, 레이블은 그 평가가 끝날 때까지 요청에 남아 뒤의 규칙이 레이블 일치 문으로 읽습니다. 모든 AWS Managed Rules 규칙 그룹은 레이블을 붙이며, 규칙을 Count로 두어 레이블만 붙이게 하는 것이 핵심 패턴입니다. 레이블 일치 규칙을 그룹 아래로 옮깁니다.

</details>

8. CloudFront 배포를 보호할 웹 ACL을 CLI로 만듭니다. 옳은 설명은?
   - A) `--scope=CLOUDFRONT --region=us-east-1`을 씁니다. 이 전역 웹 ACL은 ALB에 함께 연결할 수 없습니다.
   - B) 오리진 ALB 리전에서 `--scope=REGIONAL`을 쓰고, 같은 웹 ACL을 ALB에도 연결합니다.
   - C) CloudFront는 전역이므로 아무 리전에서나 `--scope=CLOUDFRONT`를 씁니다.

<details>
<summary>정답 보기</summary>

**정답: A) `--scope=CLOUDFRONT --region=us-east-1`을 씁니다. 이 전역 웹 ACL은 ALB에 함께 연결할 수 없습니다.**

**설명:** CloudFront용 웹 ACL은 리전이 미국 동부(버지니아 북부)로 고정된 전역 웹 ACL이며, API와 SDK는 `us-east-1` 엔드포인트를 씁니다. CloudFront 배포에 연결한 웹 ACL은 다른 자원 유형에 연결할 수 없으므로, 두 번째 검사를 원하면 ALB에는 자체 `REGIONAL` 웹 ACL이 필요합니다.

</details>

9. 웹 ACL이 `AWSManagedRulesCommonRuleSet`(700 WCU), `AWSManagedRulesSQLiRuleSet`(200 WCU), `AWSManagedRulesKnownBadInputsRuleSet`(200 WCU), 그리고 용량 500 WCU로 만들었고 지금은 120 WCU어치 규칙만 담은 사용자 규칙 그룹을 씁니다. 결과는?
   - A) 1,220 WCU이며 기본 요금 안입니다.
   - B) 1,600 WCU입니다. 최대가 5,000이라 허용되지만 기본 요금에 포함된 1,500 WCU를 넘으므로 추가 요금이 붙습니다.
   - C) 웹 ACL은 1,500 WCU를 넘을 수 없으므로 거부됩니다.

<details>
<summary>정답 보기</summary>

**정답: B) 1,600 WCU입니다. 최대가 5,000이라 허용되지만 기본 요금에 포함된 1,500 WCU를 넘으므로 추가 요금이 붙습니다.**

**설명:** 웹 ACL에서 규칙 그룹을 쓰는 비용은 현재 내용이 아니라 만들 때 정한 변경할 수 없는 용량이므로 사용자 그룹은 500으로 셉니다. 700 + 200 + 200 + 500 = 1,600입니다. 기본 요금에는 1,500 WCU가 포함되고, 그 이상은 최대 5,000 WCU까지 단계별 추가 요금이 붙습니다.

</details>

10. 한 팀이 Shield Advanced를 구독했고, 공격 중에 Shield Response Team이 먼저 연락해 주기를 원합니다. 무엇이 갖춰져야 하는가?
   - A) 더 필요한 것은 없습니다. 구독에 포함됩니다.
   - B) 모든 ALB에 리전 웹 ACL이 필요합니다.
   - C) SRT 이용을 위한 Business Support 또는 Enterprise Support 플랜, 그리고 보호 대상 자원에 Route 53 상태 확인을 쓰는 상태 기반 탐지가 필요합니다.

<details>
<summary>정답 보기</summary>

**정답: C) SRT 이용을 위한 Business Support 또는 Enterprise Support 플랜, 그리고 보호 대상 자원에 Route 53 상태 확인을 쓰는 상태 기반 탐지가 필요합니다.**

**설명:** SRT를 쓰려면 이 지원 플랜 중 하나가 필요합니다. 선제 대응은 상태 기반 탐지(Route 53 상태 확인 사용)를 켠 자원에서만 쓸 수 있습니다. Shield Advanced는 명시적으로 추가한 자원만 보호하며, 자동이고 추가 비용이 없는 계층은 Shield Standard입니다.

</details>

11. 한 팀이 보안 그룹에서 CloudFront origin-facing 관리형 prefix list를 허용하는 공개 ALB를 오리진으로 제안합니다. 이 과정이 이것을 internal ALB로 가는 VPC 오리진보다 약하다고 보는 이유는?
   - A) prefix list는 공격자가 만든 것을 포함해 어느 CloudFront 배포든 허용하지만, internal ALB에는 인터넷 경로가 아예 없기 때문입니다.
   - B) prefix list에 CloudFront의 IPv4 주소가 들어 있지 않기 때문입니다.
   - C) 공개 ALB는 TLS를 쓸 수 없기 때문입니다.

<details>
<summary>정답 보기</summary>

**정답: A) prefix list는 공격자가 만든 것을 포함해 어느 CloudFront 배포든 허용하지만, internal ALB에는 인터넷 경로가 아예 없기 때문입니다.**

**설명:** 엣지 제어는 자신의 배포를 거치는 요청에만 적용됩니다. 다른 배포에서 온 요청은 자신의 웹 ACL과 속도 기반 규칙을 건너뜁니다. 비밀 헤더를 더해도 비밀이 지켜지는 동안에만 도움이 됩니다. internal ALB로 하는 은닉은 라우팅의 성질이라서 나중에 보안 그룹이 느슨해져도 인터넷에서 오리진에 닿지 않습니다.

</details>

12. count 모드 시험 중에 관리형 규칙 그룹 안의 규칙이 일치했을 것임을 믿을 만하게 보여 주는 증거는?
   - A) WAF 로그의 `nonTerminatingMatchingRules` 필드와 레이블, 그리고 레이블 지표
   - B) 웹 ACL 화면의 샘플 요청 표
   - C) CloudFront 표준 로그의 상태 코드

<details>
<summary>정답 보기</summary>

**정답: A) WAF 로그의 `nonTerminatingMatchingRules` 필드와 레이블, 그리고 레이블 지표**

**설명:** WAF 로그는 Count 일치를 `nonTerminatingMatchingRules`에, 요청마다 붙은 레이블을 함께 남깁니다. 규칙 그룹 안 Count 규칙의 샘플은 웹 ACL 화면에 보이지 않고, 규칙 그룹 안의 Count 작업 규칙은 웹 ACL 차원 지표를 내지 않습니다. Count 일치는 상태 코드를 바꾸지 않습니다.

</details>

13. 기준 설계에서 Pod의 NetworkPolicy는 클라이언트 주소가 아니라 ALB 서브넷을 담은 `ipBlock`에서 오는 인그레스를 허용합니다. 이유는?
   - A) ALB는 프록시이므로 Pod IP 대상은 ALB 노드의 프라이빗 주소를 보고, 클라이언트 주소는 `X-Forwarded-For`로 오기 때문입니다.
   - B) NetworkPolicy는 IPv4 CIDR 블록을 표현할 수 없기 때문입니다.
   - C) CloudFront가 HTTP/3에서만 클라이언트 주소를 VPC 오리진 ENI로 바꾸기 때문입니다.

<details>
<summary>정답 보기</summary>

**정답: A) ALB는 프록시이므로 Pod IP 대상은 ALB 노드의 프라이빗 주소를 보고, 클라이언트 주소는 `X-Forwarded-For`로 오기 때문입니다.**

**설명:** ELB 안내서에 따르면 서버 액세스 로그에는 로드 밸런서의 주소만 남습니다. Kubernetes 문서는 재작성이 NetworkPolicy 처리 전후 중 언제 일어나는지가 플러그인, 클라우드 제공자, Service 구현에 따라 다르다고 경고하므로, 사용하는 CNI에서 실제 출발지를 확인합니다.

</details>

14. 워크북 과제에서 `rate-login`(기간 300초, 한도 100, IP 집계, 작업 Count)은 `198.51.100.20`이 한 시간 동안 조용하다가 5분 안에 `POST /login` 요청 640건을 단발 버스트로 보내는 것을 봅니다. 규칙은 그 주소의 요청을 대략 몇 건 Count하며, 실제 값이 정확하지 않은 이유는?
   - A) 640건. Count는 범위 축소 문과 일치하는 모든 요청을 세기 때문입니다.
   - B) 한도를 넘은 요청인 약 540건. AWS WAF가 속도를 추정하고 초과를 늦게 탐지하므로 근사값입니다.
   - C) 100건. 한도가 카운트를 제한하기 때문입니다.

<details>
<summary>정답 보기</summary>

**정답: B) 한도를 넘은 요청인 약 540건. AWS WAF가 속도를 추정하고 초과를 늦게 탐지하므로 근사값입니다.**

**설명:** 속도 기반 규칙은 한도를 넘은 인스턴스의 이후 일치 요청에 작업을 적용합니다. 640 - 100 = 540입니다. 이는 단발 버스트일 때이며, 그 주소가 한도를 넘는 상태를 계속 유지하면 추정 속도가 한도 아래로 떨어질 때까지 규칙이 작업을 계속 적용하므로 이후 요청 거의 전부가 Count됩니다. AWS WAF는 최근 요청에 가중치를 두어 설정값과 정확히 같지 않고 그 근처에서 제한합니다. 이 시험은 오탐(여럿이 함께 쓰는 사무실 NAT)을 드러내며, 계획은 범위 축소 문 안의 `NotStatement`에 IP 세트를 넣어 이를 없앱니다.

</details>

완료 기준: 모든 답을 워크북의 규칙으로 설명하고, 규칙 계획에는 **측정값이 아닌 풀이 시나리오**라고 표시합니다.

# 09. 엣지 보안: WAF와 DDoS 방어

> **마지막 업데이트**: 2026년 11월 19일
> **실습 경계**: 책상 연습만 합니다. count 모드 규칙 계획을 문서로 작성할 뿐이며, 이 워크북은 웹 ACL, 배포, Shield 구독, 로드 밸런서, Kubernetes 객체를 만들지 않고 어떤 시스템에도 공격이나 부하 트래픽을 보내지 않습니다.
> **검증 상태**: AWS WAF, AWS Shield, Amazon CloudFront 개발자 안내서, AWS WAF API 참조, AWS DDoS 복원력 백서, RFC 4987, OWASP Top 10 2021 페이지를 확인했습니다. 규칙을 배포하거나 트래픽을 측정하지 **않았습니다**. 과제의 숫자는 관측값이 아니라 풀이용 시나리오입니다.

이 워크북의 목표는 공격이 노리는 계층을 말하고, 경로의 **어디에서** 어떤 제어가 그 공격을 멈추는지 짚고, count 모드에서 시작해 예상 일치 수와 롤백 조건까지 갖춘 AWS WAF 규칙 계획을 세우며, 인터넷에서 오리진에 직접 닿을 수 있으면 왜 모든 엣지 제어가 공격자에게 선택 사항이 되는지 설명하는 것입니다.

이 장은 [워크북 08](./08-cdn-edge-delivery.md#edge-origin-path)의 엣지에서 오리진까지의 경로(CloudFront → VPC 오리진 → internal ALB)를 바탕으로 하며 그 내용을 다시 가르치지 않습니다. 서버 자체의 호스트 방화벽은 [beginner 06](../beginner/06-firewalls-host-security.md)에 있습니다. WAF 배치, 규칙 순서의 함정, 요청 본문 검사 한도, 전달된 클라이언트 IP, 로그 필드 전체 목록은 [WAF·엣지·API 보안](../../security/14-waf-edge-api-security.md)에 있으므로 이 워크북은 해당 절을 링크합니다. Pod 수준 규칙은 [네트워크 정책](../../security/04-network-policies.md)에, Ingress 쪽은 [AWS Load Balancer Controller](../03-aws-lb-controller.md)에 있습니다. 컨트롤러 문서의 예시는 `alb.ingress.kubernetes.io/scheme: internet-facing`을 쓰지만, **이 과정의 엣지 설계에서 ALB는 internal**(`alb.ingress.kubernetes.io/scheme: internal`)이며 CloudFront VPC 오리진 뒤에 있으므로 그 값 하나를 바꿔서 읽습니다. BGP 기반 Anycast는 [워크북 02](./02-routing-policy-convergence.md)에, TCP 핸드셰이크는 [네트워크 기초 Part 2](../../basics/06-network-fundamentals-part2.md)에 있습니다.

**준비 조건:** 텍스트 편집기와 AWS 문서만 있으면 됩니다. AWS 계정은 필요 없습니다. 이 설계를 직접 구축하면 AWS WAF 요금(웹 ACL당, 규칙당, 요청 100만 건당, 그리고 Bot Control, 계정 탈취 방지, Anti-DDoS 규칙 그룹(Shield Advanced가 포함하는 경우 제외), CAPTCHA와 Challenge, 1,500 WCU 초과 용량, 로깅의 추가 요금), CloudFront와 로드 밸런서 요금, 구독한다면 AWS Shield Advanced 요금(요금 페이지 기준 월 3,000달러부터, 1년 약정)이 발생하며 그 **비용과 정리 책임은 학습자 본인**에게 있습니다. 서면으로 승인된 테스트 계획 없이는 자신의 자원을 대상으로도 공격 트래픽으로 시험하지 않습니다.

## 1. 질문을 정하고 읽기

시험 범위는 읽을 범위를 정하는 데만 씁니다. 숫자와 동작은 첫 열의 공식 문서로 확인합니다.

| 읽을 자료 | 대응하는 시험 범위 | 자신의 말로 답할 질문 |
|---|---|---|
| [AWS Shield Standard overview](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-standard-summary.html), [Shield mitigation logic for CloudFront and Route 53](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-event-mitigation-logic-continuous-inspection.html) | ANS-C01 Domain 4 Network Security, Compliance, and Governance, Task 4.1(AWS WAF와 AWS Shield로 인바운드 트래픽 흐름 보호) | CloudFront 배포를 노린 SYN 플러드가 왜 오리진에서는 SYN 플러드가 되지 않는가? |
| [Using rule actions](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-action.html), [Rate-based rule settings](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based-high-level-settings.html), [Web request labeling](https://docs.aws.amazon.com/waf/latest/developerguide/waf-labels.html) | Domain 4, Task 4.1(위협 모델, 완화 전략) | 어떤 작업이 요청 평가를 끝내고, 어떤 작업이 뒤의 규칙도 요청을 보게 하는가? |
| [AWS Shield Advanced capabilities](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-advanced-summary-capabilities.html), [Anti-DDoS managed rule group](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-anti-ddos.html) | Domain 4, Task 4.1 | Shield Advanced는 Standard에 무엇을 더하며, 먼저 무엇이 필요한가? |
| [Testing and tuning protections](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing.html), [Logging web ACL traffic](https://docs.aws.amazon.com/waf/latest/developerguide/logging.html), [Viewing sampled requests](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing-view-sample.html) | Domain 4, Task 4.2(모니터링과 로깅으로 보안 검증·감사) | count 모드 규칙이 일치했을 것임을 보여 주는 로그 필드는 무엇인가? |
| [OWASP Top 10 2021](https://owasp.org/Top10/2021/) | Domain 4, Task 4.1(흔한 보안 위협) | 열 개 범주 중 엣지 WAF가 줄일 수 있는 것과 애플리케이션만 고칠 수 있는 것은 무엇인가? |

읽은 뒤 클라이언트에서 Pod까지의 경로를 그리고, 2절의 각 공격이 멈추는 곳을 표시합니다. 어떤 공격이 멈추는 곳을 가리키지 못하는 설계 검토는 그 공격을 다루지 않은 것입니다.

## 2. 위협 계층: 공격이 소진시키는 자원

공격이 무엇을 바닥내려 하는지(링크 대역폭, 연결 상태, TLS용 CPU, 애플리케이션 작업)를 물으면 위치를 정하기 쉽습니다.

| 계층 | 공격 | 동작 | 소진시키는 것 |
|---|---|---|---|
| L3 | **UDP 반사(reflection)** | 공격자가 피해자 주소를 출발지로 위조한 작은 UDP 요청을 제3자 서버(DNS, NTP, SSDP, CLDAP, Memcached, CharGen, QOTD)에 보내고, 그 서버들이 훨씬 큰 응답을 피해자에게 보냄. AWS 백서는 DNS의 증폭률을 28~54배로 듦 | 링크와 네트워크 용량 |
| L4 | **SYN 플러드** | 3-way 핸드셰이크([Part 2](../../basics/06-network-fundamentals-part2.md))를 끝내지 않는 SYN을 대량으로 보냄 | 리스너의 반열림(half-open) 연결 백로그([RFC 4987](https://www.rfc-editor.org/rfc/rfc4987.html) 2.2절). 링크를 채울 필요가 없음 |
| L6 | **TLS 악용** | 핸드셰이크처럼 보이는 읽을 수 없는 데이터, 끝없는 재협상, 빠른 세션 열고 닫기 | TLS를 종료하는 쪽의 CPU |
| L7 | **HTTP 플러드** | 정상 사용자처럼 보이는 요청, 때로는 사람의 탐색을 흉내 냄 | 애플리케이션 용량. 적은 양으로도 충분할 수 있음 |
| L7 | **캐시 무력화(cache-busting)** | 쿼리 문자열을 바꿔 CDN이 모든 요청을 전달하게 만드는 HTTP 플러드([워크북 08](./08-cdn-edge-delivery.md) 5절) | 캐시 뒤 오리진 용량 |
| L7 | **익스플로잇 시도** | 알려진 취약점 유형을 노리는 페이로드(4절) | 용량이 아니라 기밀성과 무결성 |
| L7 | **봇, 스크레이퍼, 크리덴셜 스터핑** | 자동화된 콘텐츠 탈취, 유출된 사용자 이름·비밀번호 쌍으로 로그인 시도 | 비즈니스 로직과 계정. 백서는 이들이 엄밀히는 DDoS가 아니지만 DDoS처럼 보인다고 설명 |

두 가지 결론이 나옵니다. 첫째, 반사 공격은 출발지 주소를 위조할 수 있어야 하며, 출발지 주소 검증([BCP 38](https://www.rfc-editor.org/info/bcp38))을 적용하는 네트워크는 그 능력을 없앱니다. 둘째, L7 공격은 형식이 올바른 트래픽이므로 패킷 유효성만 보는 제어로는 막을 수 없고 요청을 읽는 제어가 필요합니다.

## 3. 공격별로 멈추는 곳

| 공격 | 멈추는 곳 | 방식 | 책임 |
|---|---|---|---|
| UDP 반사 | CloudFront 엣지 | Shield 완화는 웹 애플리케이션에 유효한 트래픽만 통과시키고, CloudFront는 형식이 올바른 연결만 받음 | AWS(자동) |
| SYN 플러드 | CloudFront 엣지 | Shield TCP SYN 프록시가 연결이 서비스에 닿기 전에 핸드셰이크를 검증(상태 없는 SYN 쿠키) | AWS(자동) |
| TLS 악용 | CloudFront 엣지 | TLS가 엣지에서 끝나므로 오리진은 형식이 올바른 요청만 봄([워크북 08](./08-cdn-edge-delivery.md) 7절) | AWS(자동) |
| HTTP 플러드, 캐시 무력화 | 엣지의 WAF 웹 ACL | 속도 기반 규칙, Anti-DDoS 관리형 규칙 그룹, Challenge | 사용자 |
| 익스플로잇 시도 | WAF 웹 ACL, 그다음 애플리케이션 | 첫 필터로 관리형 규칙 그룹, 애플리케이션의 입력 검증과 인가 | 사용자 |
| 크리덴셜 스터핑 | WAF(계정 탈취 방지), 그다음 애플리케이션 | 유출 자격 증명 확인과 로그인량 제한, 애플리케이션의 MFA와 잠금 정책 | 사용자 |
| 오리진을 직접 노린 모든 것 | 오리진에 공개 경로가 없지 않다면 **어디에서도 멈추지 않음** | 오리진 은닉(8절) | 사용자 |

**SYN 쿠키**는 리스너가 SYN-RECEIVED 상태의 연결에 대해 아무 상태도 저장하지 않게 합니다. 서버는 필요한 정보를 SYN-ACK의 시퀀스 번호에 담고, 올바른 ACK가 돌아오면 그 값으로 상태를 다시 만듭니다([RFC 4987](https://www.rfc-editor.org/rfc/rfc4987.html) 3.6절). AWS 백서는 엣지 서비스의 상태 없는 SYN 플러드 완화가 들어오는 연결을 SYN 쿠키로 검증한 뒤에 넘긴다고 설명하고, 최신 운영체제는 기본적으로 SYN 쿠키를 켠다고 적습니다. CloudFront는 오리진과 지속 연결도 유지하므로 뷰어의 새 연결이 새 오리진 연결이 되지 않습니다. AWS WAF와 보안 그룹은 이를 대신하지 못합니다. AWS WAF는 HTTP 요청을 검사하므로 연결이 생긴 뒤에야 동작하고, 보안 그룹은 출발지, 프로토콜, 포트로 허용 여부만 정할 뿐 속도를 제한하지 않습니다.

**흡수**에는 플러드보다 큰 용량이 필요합니다. CloudFront용 Shield 완화 페이지는 CloudFront가 DNS 트래픽 유도와 Anycast 라우팅을 함께 써서 공격을 출발지 가까이에서 완화하고 장애를 격리한다고 설명합니다. 이는 워크북 08과 맞습니다. DNS는 각 뷰어를 POP으로 보내고, 공격 트래픽은 오리진 하나가 아니라 여러 POP에 떨어집니다. Shield 완화는 엣지 서비스에 통합되어 있으며, 백서는 이로써 완화 시간이 분 단위에서 1초 미만으로 줄어든다고 적습니다.

**거부된 트래픽의 비용:** 백서에 따르면 CloudFront나 AWS WAF가 거부한 요청에는 HTTP 요청 요금과 데이터 전송(아웃) 요금이 부과되지 않습니다. WAF가 Block한 요청은 오리진 용량이 아니라 WAF 요청 검사 비용만 씁니다.

**실무 포인트:** 엣지는 양을 막지만 누가 무엇을 할 수 있는지는 정하지 않습니다. AWS WAF는 익스플로잇과 남용 표면을 줄일 뿐이고, [인가는 애플리케이션에 남습니다](../../security/14-waf-edge-api-security.md)(그 장의 1절). 비즈니스 작업을 WAF만 검사하는 설계는 단일 장애점을 가집니다.

## 4. OWASP Top 10 2021과 엣지 WAF가 할 수 있는 일

[OWASP Top 10 2021](https://owasp.org/Top10/2021/)에는 A01부터 A10까지 열 개의 웹 애플리케이션 위험 범주가 있습니다. OWASP는 이후 2025년판을 냈지만 이 워크북은 2021년 목록을 씁니다. AWS는 핵심 규칙 세트(core rule set)를 OWASP Top 10 같은 OWASP 문서에 설명된 "위험이 높고 흔히 발생하는 취약점 중 일부"에 대한 보호라고 설명합니다. 관리형 규칙은 알려진 요청 패턴을 거르는 필터이지 범주 하나를 다 막는 장치가 아닙니다.

| 2021 범주 | 엣지 WAF의 기여(AWS 관리형 규칙 그룹 예) | 애플리케이션이나 플랫폼만 할 수 있는 일 |
|---|---|---|
| A01 Broken Access Control | 거의 없음. 요청은 정상으로 보임 | 모든 요청에서 객체 수준 인가 |
| A02 Cryptographic Failures | WAF에서는 없음 | 모든 구간의 TLS([워크북 08](./08-cdn-edge-delivery.md) 7절), 키와 데이터 처리 |
| A03 Injection | SQL 인젝션 규칙(`AWSManagedRulesSQLiRuleSet`, 200 WCU), 핵심 규칙 세트의 크로스 사이트 스크립팅 규칙 | 매개변수화 쿼리, 출력 인코딩 |
| A04 Insecure Design | 없음 | 위협 모델링, 비즈니스 한도 |
| A05 Security Misconfiguration | 간접적 | 구성 검토. 공개적으로 닿는 오리진은 엣지 설계의 잘못된 구성(8절) |
| A06 Vulnerable and Outdated Components | 알려진 잘못된 입력(`AWSManagedRulesKnownBadInputsRuleSet`, 200 WCU). 예: Log4j, Java 역직렬화 패턴 | 패치. WAF 규칙은 시간을 벌 뿐 |
| A07 Identification and Authentication Failures | 계정 탈취 방지(`AWSManagedRulesATPRuleSet`, 50 WCU, 유료) | MFA, 잠금, 세션 처리 |
| A08 Software and Data Integrity Failures | 없음 | 서명된 아티팩트, 공급망 통제 |
| A09 Security Logging and Monitoring Failures | WAF 로그와 지표가 입력 중 하나(9절) | 계층 간 상관 분석과 경보 |
| A10 Server-Side Request Forgery (SSRF) | EC2 메타데이터 유출 시도를 찾는 핵심 규칙 세트 규칙(`EC2MetaDataSSRF_*`) | 이그레스 제어와 애플리케이션의 URL 검증 |

핵심 규칙 세트(`AWSManagedRulesCommonRuleSet`)는 700 WCU입니다. 크기 제한도 적용해서, 예를 들어 `SizeRestrictions_BODY`는 8 KB를 넘는 요청 본문을 Block하며 업로드 경로에서 흔한 오탐(false positive) 원인이 됩니다(10절).

## 5. AWS WAF 모델

**웹 ACL.** AWS WAF 콘솔은 이제 웹 ACL을 **protection pack**(web ACL)이라고 부르지만, 이 워크북은 "웹 ACL"이라고 씁니다. 웹 ACL에는 규칙과 규칙 그룹, 그리고 어떤 규칙도 평가를 끝내지 않은 요청에 적용할 **기본 작업(default action)**(Allow 또는 Block)이 있습니다. 자원 하나에는 웹 ACL을 하나만 연결할 수 있고, 웹 ACL 하나는 여러 자원을 보호할 수 있습니다.

**범위.** CloudFront용 웹 ACL은 **전역**이며 리전이 미국 동부(버지니아 북부)로 고정됩니다. CLI에서는 `--scope=CLOUDFRONT --region=us-east-1`을 넘기고, API와 SDK에서는 `us-east-1` 엔드포인트를 씁니다. CloudFront 배포에 연결한 웹 ACL은 다른 자원 유형에 연결할 수 없으므로, ALB 같은 리전 자원에는 그 리전의 `REGIONAL` 웹 ACL이 따로 필요합니다.

**규칙, 규칙 그룹, 순서.** 규칙은 문(statement)과 작업으로 이뤄집니다. 규칙 그룹은 재사용할 수 있는 규칙 묶음이며, 직접 만든 것이나 **관리형 규칙 그룹**(AWS Managed Rules, AWS Marketplace 판매자)이 있습니다. AWS WAF는 숫자 우선순위가 가장 낮은 규칙부터 평가해, 어떤 규칙이 평가를 끝내거나 규칙이 다 떨어질 때까지 진행합니다. 규칙 그룹 안에서는 그 그룹의 우선순위를 씁니다. 순서의 함정(앞쪽의 넓은 Allow, 그룹 전체 예외)은 [security/14의 3절](../../security/14-waf-edge-api-security.md)에 있습니다.

**작업:**

| 작업 | 평가를 끝내는가 | 동작 |
|---|---|---|
| Allow | 예 | 보호 대상 자원으로 요청을 전달. 직접 만든 규칙은 사용자 지정 요청 헤더를 넣을 수 있음 |
| Block | 예 | 보호 대상 자원이 기본적으로 `403 (Forbidden)`으로 응답. 직접 만든 규칙은 사용자 지정 응답을 정할 수 있음 |
| Count | 아니요 | 일치를 세고 다음 규칙으로 진행. 레이블과 사용자 지정 요청 헤더를 붙일 수 있음 |
| CAPTCHA | 토큰에 따라 다름 | 유효하고 만료되지 않은 토큰이면 Count처럼 동작. 토큰이 없거나 잘못되었거나 만료되었으면 Block하고, 클라이언트가 표시할 수 있으면 CAPTCHA 퍼즐을 보냄 |
| Challenge | 토큰에 따라 다름 | 같은 토큰 논리이며, 퍼즐 대신 조용한 브라우저 챌린지를 보냄 |

CAPTCHA와 Challenge는 브라우저가 보안 컨텍스트에서 HTTPS 엔드포인트에 접근할 때만 동작하며 둘 다 추가 요금이 있습니다. 브라우저가 아닌 API 클라이언트는 응답할 수 없으므로 기계용 API는 따로 시험합니다. AWS WAF는 앱의 요청에 토큰을 붙이는 애플리케이션 통합 SDK도 제공합니다. AWS는 **Monetize** 작업(HTTP `402 Payment Required`, CloudFront 웹 ACL 전용, 평가 종료, 속도 기반 규칙에서는 사용 불가)도 추가했지만 이 워크북의 범위 밖입니다.

**속도 기반 규칙(rate-based rule).** 속도 기반 규칙은 **집계 인스턴스**(예: 출발지 IP 하나)마다 60, 120, 300, 600초 중 하나인 **평가 기간(evaluation window)**(기본 300초) 동안 요청을 세고, **한도(limit)**(최솟값 10)를 넘은 인스턴스의 이후 일치 요청에 작업을 적용합니다. 작업은 Allow만 아니면 됩니다. **범위 축소 문**(scope-down statement)은 세고 조치할 요청을 좁히며, 예를 들어 `/login`에 대한 `POST`만 대상으로 합니다. 설계할 때 염두에 둘 동작:

- AWS WAF는 최근 요청에 가중치를 더 주는 알고리즘으로 속도를 추정하므로, 설정값과 정확히 같지 않고 그 근처에서 제한합니다.
- 안내서는 속도를 평가 기간과 관계없이 자주 확인한다고 하고, API 참조는 약 10초마다라고 합니다. 제한이 시작되기 전 몇 분까지 요청이 너무 빨리 들어올 수 있고, 속도가 떨어진 뒤에도 보통 30초 미만 동안 제한이 이어질 수 있습니다.
- 한도, 기간, 집계, 전달 IP 구성, 범위를 바꾸면 **카운트가 초기화**되고 속도 제한이 최대 1분 멈출 수 있습니다.
- 속도 기반 문은 다른 문(예: `NotStatement`) 안에 넣을 수 없지만, 그 범위 축소 문 안에는 `NotStatement`를 넣을 수 있습니다.
- IP만으로 집계하면 `GetRateBasedStatementManagedKeys`가 지금 제한 중인 주소를 보여 줍니다.

CloudFront → ALB → Ingress에서 어떤 클라이언트 주소로 집계할지는 [security/14의 5절](../../security/14-waf-edge-api-security.md)에 있습니다.

**레이블(label).** 레이블은 일치한 규칙이 요청에 붙이는 메타데이터로, 그 웹 ACL 평가가 끝날 때까지 남고 뒤의 규칙이 **레이블 일치 문**(label match statement)으로 읽습니다. 직접 만든 레이블은 `awswaf:<계정 ID>:<rulegroup 또는 webacl>:<이름>:<네임스페이스>:...:<레이블 이름>` 형식이고, 관리형 규칙 그룹 레이블은 `awswaf:managed:<공급자>:<규칙 그룹 이름>:...` 형식입니다. 예: `awswaf:managed:aws:core-rule-set:NoUserAgent_Header`. 모든 AWS Managed Rules 규칙 그룹은 레이블을 붙입니다. 핵심 패턴은 규칙을 Count로 두어 레이블만 붙이게 하고, 뒤에 레이블 조합으로 판정하는 규칙을 두는 것입니다. 레이블은 CloudWatch 레이블 지표도 만듭니다.

**관리형 규칙 재정의(override).** 서로 다른 스위치가 두 개 있습니다.

| 재정의 | 일어나는 일 | 시험에 쓰는가 |
|---|---|---|
| **규칙 작업 재정의**(`RuleActionOverrides`, 그룹 안의 규칙별) | 일치한 요청을 그 규칙의 작업이 재정의 값(예: Count)인 것과 똑같이 처리하고, 그룹은 다른 규칙을 계속 평가 | 예. 규칙 그룹을 시험하는 문서상 방법 |
| **규칙 그룹 반환 작업을 Count로 재정의** | 그룹은 평소처럼 평가하다 첫 종료 일치에서 멈추고, 웹 ACL로 돌려주는 결과만 Count가 됨 | 아니요. 안내서는 그룹 평가 방식을 바꾸지 않는다고 하므로, 그 요청에 대해 그룹의 뒤쪽 규칙은 실행되지 않음 |

`RuleActionOverrides`는 2022년 10월에 예전 `ExcludedRules` 설정을 대체했습니다.

**용량(WCU).** 웹 ACL 용량 단위(WCU)는 규칙 실행에 필요한 자원을 재는 단위이며 트래픽 검사 방식은 바꾸지 않습니다. 단순한 문은 정규식 패턴 세트나 JSON 본문 검사 같은 문보다 적게 듭니다. 규칙 그룹은 만들 때 정하는 **변경할 수 없는 용량**(최대 5,000 WCU)을 가지며, 웹 ACL에서 그룹을 쓰는 비용은 현재 내용이 아니라 그 용량입니다. 웹 ACL은 최대 5,000 WCU를 쓸 수 있고 기본 요금에 1,500이 포함되며, 그 이상은 단계별 추가 요금이 붙습니다. `CheckCapacity` API로 배포 전에 규칙 목록의 용량을 확인할 수 있습니다.

**전파.** 변경이 모든 위치에 닿는 데 몇 초에서 몇 분이 걸리므로, 잠시 동안 한 위치는 새 작업을, 다른 위치는 이전 작업을 적용할 수 있습니다.

## 6. AWS Shield Standard와 Shield Advanced

| | Shield Standard | Shield Advanced |
|---|---|---|
| 비용과 활성화 | 모든 AWS 고객에게 추가 요금 없이 자동 적용 | 구독. 요금 페이지는 월 3,000달러부터, 자동 갱신되는 1년 약정으로 안내. 명시적으로 추가한 자원(또는 AWS Firewall Manager Shield Advanced 정책으로 보호하는 자원)만 보호 |
| 범위 | 가장 흔하고 자주 일어나는 네트워크·전송 계층 공격. CloudFront 배포, Route 53 호스팅 영역, Global Accelerator 표준 가속기는 알려진 모든 네트워크·전송 계층 공격에 대한 보호를 받음 | CloudFront, Route 53 호스팅 영역, Global Accelerator 표준 가속기, 탄력적 IP 주소(와 그 뒤의 EC2 인스턴스, NLB), ALB, Classic Load Balancer |
| 애플리케이션 계층(L7) | 자체적으로는 없음. L7은 WAF의 일 | AWS WAF 웹 ACL을 사용. 보호 대상 자원의 표준 WAF 요금은 1,500 WCU와 기본 본문 크기까지 포함. Bot Control, CAPTCHA, 1,500 WCU 초과 용량, 더 큰 본문 검사는 포함되지 않음. 구독에는 Anti-DDoS 규칙 그룹이 추가 비용 없이 포함되며, 결제자(payer)당 월 500억 요청까지 AWS WAF 요청 요금을 포함하고 그 이후는 100만 건당 0.15달러 |
| 자동 L7 완화 | 없음 | 다음 문단 참조 |
| 대응 팀 | 없음 | 공격 중 지원과 사용자 지정 완화를 맡는 **Shield Response Team(SRT)**. Business Support 또는 Enterprise Support 플랜이 필요(DDoS 복원력 백서는 Business Support+ 또는 Enterprise Support로 표기) |
| 탐지 | 자동 | Route 53 상태 확인을 쓰는 상태 기반 탐지. **선제 대응(proactive engagement)**(SRT가 먼저 연락)에 필요 |
| 비용 보호 | 없음 | 공격으로 생긴 일부 확장 요금에 대한 Shield Advanced 서비스 크레딧 |
| 가시성 | 서비스 지표 외에는 없음 | 콘솔, API, CloudWatch 지표의 이벤트 정보, 보호 그룹 |

**2026년의 자동 L7 완화.** 2026년 3월 26일부터 **Anti-DDoS 관리형 규칙 그룹**(`AWSManagedRulesAntiDDoSRuleSet`, 50 WCU, AWS WAF만 쓰면 추가 요금, Shield Advanced 구독에는 추가 비용 없이 포함)이 HTTP 요청 플러드에 대한 AWS의 기본 해법이며, Shield Advanced의 Layer 7 자동 완화를 대체합니다(기존 고객은 계속 쓸 수 있음). 이 규칙 그룹은 트래픽을 자원의 기준선과 비교하고, 이벤트 중에는 모든 요청에 레이블(`awswaf:managed:aws:anti-ddos:event-detected`)을, 의심 출발지에는 신뢰도별 레이블(`low-`, `medium-`, `high-suspicion-ddos-request`)을 붙이며, 약한 완화로 조용한 Challenge를 보내고(`GET` 요청만 challengeable 레이블을 받음) 강한 완화로 Block합니다. 이전 Shield Advanced 기능은 150 WCU 규칙 그룹을 추가하고, 기준선을 익히는 데 24시간에서 30일이 걸리며, Count 또는 Block으로 동작하고, CDN 뒤의 ALB에서는 CDN이 원래 클라이언트 속성을 전달하지 않을 수 있어 효과가 줄어듭니다. AWS는 대신 CloudFront 배포에서 켜라고 권장합니다.

## 7. 기준 경로의 심층 방어

![엣지 보안 애니메이션. ① 봇넷이 CloudFront 엣지로 L3/L4 플러드(UDP 반사와 SYN 플러드)를 보내지만 Shield가 엣지에서 흡수하고 오리진에는 아무것도 닿지 않는다. ② 봇이 /login에 정상 형식의 HTTPS 요청을 대량으로 보낸다. L3/L4 검사는 통과하지만 WAF 웹 ACL의 속도 기반 규칙(예시 이름 rate-login)이 Block하고 클라이언트는 403 Forbidden을 받는다. ③ 정상 GET은 Shield를 지나고, 평가를 끝내는 WAF 규칙이 없으므로 웹 ACL 기본 작업 Allow로 전달된다. ④ CloudFront가 VPC 오리진으로 연결한다. 프라이빗 서브넷의 서비스 관리형 ENI(10.0.11.25)가 internal ALB(10.0.12.40)로 연결을 열고, ALB 보안 그룹은 CloudFront-VPCOrigins-Service-SG 또는 origin-facing prefix list만 허용한다. ⑤ Ingress(scheme: internal)로 만든 ALB가 Pod IP(10.0.13.31)로 전달하고, Pod의 NetworkPolicy는 ALB 서브넷만 허용하며 Pod는 200을 돌려준다. 인터넷용 로드 밸런서도, 공개 CIDR을 허용하는 인바운드 규칙도 없다.](../../.gitbook/assets/ko-networking-expert-09-edge-security-waf-ddos-anim-0.svg)

| 계층 | 제어 | 허용하는 것 | 동작했다는 증거 |
|---|---|---|---|
| 엣지 네트워크 | Shield Standard, CloudFront(DNS 유도, Anycast, SYN 프록시, 엣지 TLS) | 형식이 올바른 HTTP(S) 연결 | 네트워크 계층 이벤트 중에도 오리진 부하가 그대로. 구독했다면 Shield Advanced 이벤트 정보 |
| 엣지 애플리케이션 | 전역 웹 ACL(`CLOUDFRONT` 범위, us-east-1) | 어떤 규칙도 끝내지 않은 요청, 그다음 기본 작업 | WAF 로그의 `terminatingRuleId`, `action`, 레이블 |
| 오리진 경로 | internal ALB로 가는 VPC 오리진([워크북 08](./08-cdn-edge-delivery.md#edge-origin-path)) | CloudFront만. ALB에는 프라이빗 주소만 있음 | 시험할 인터넷 경로 자체가 없음 |
| ALB 보안 그룹 | `CloudFront-VPCOrigins-Service-SG`(자신의 배포) 또는 관리형 prefix list `com.amazonaws.global.cloudfront.origin-facing`(모든 배포)에서 오는 인바운드만 | CloudFront의 VPC 오리진 ENI | 보안 그룹 규칙. ALB 액세스 로그에는 VPC 오리진 서브넷 주소만 보일 것으로 예상 |
| Ingress | `alb.ingress.kubernetes.io/scheme: internal`과 `target-type: ip`를 쓰는 AWS Load Balancer Controller([AWS Load Balancer Controller](../03-aws-lb-controller.md)) | 정의한 리스너 규칙 | Ingress 이벤트, 대상 상태 |
| Pod | ALB 서브넷을 담은 `ipBlock`에서 오는 NetworkPolicy 인그레스([네트워크 정책](../../security/04-network-policies.md#kubernetes-networkpolicy-spec)) | ALB 노드에서 오는 연결 | 켜져 있다면 CNI 정책 로그의 거부 기록 |
| 호스트 | 호스트 방화벽([beginner 06](../beginner/06-firewalls-host-security.md)) | 노드가 제공해야 하는 포트 | 방화벽 카운터 |
| 애플리케이션 | 인증과 인가 | 사용자에게 허용된 작업 | 애플리케이션 감사 로그 |

**Pod가 보는 출발지 주소.** ALB는 프록시입니다. ELB 안내서에 따르면 서버 액세스 로그에는 로드 밸런서의 IP 주소만 남고, 클라이언트 주소는 `X-Forwarded-For`로 오며 이 값은 제대로 보호된 시스템이 붙였을 때만 믿을 수 있습니다. 그래서 Pod IP 대상은 ALB 노드의 프라이빗 주소를 보며, 위 NetworkPolicy가 ALB 서브넷을 지정하는 이유입니다. Kubernetes 문서는 주소 재작성이 NetworkPolicy 처리 전후 중 언제 일어나는지가 네트워크 플러그인, 클라우드 제공자, Service 구현에 따라 다르다고 경고하므로, 규칙에 기대기 전에 사용하는 CNI에서 실제 출발지를 확인합니다. NetworkPolicy는 이를 적용하는 플러그인이 없으면 효과가 없다는 점도 기억합니다.

**웹 ACL 하나 또는 둘.** CloudFront 웹 ACL은 ALB에 함께 연결할 수 없습니다. ALB에 리전 웹 ACL을 더하면 로그와 비용이 따로 있는 별개의 두 번째 검사가 됩니다. 그럴 가치가 있는 경우는 [security/14의 2절](../../security/14-waf-edge-api-security.md)에서 다룹니다.

## 8. 오리진 은닉: 닿는 오리진이 엣지를 우회하는 이유

위 표의 엣지 행에 있는 모든 제어는 **배포를 거치는 요청에만** 적용됩니다. 공격자가 인터넷에서 오리진이 응답하는 주소나 DNS 이름을 알아내면 그곳으로 요청을 보내 Shield의 엣지 흡수, 전역 웹 ACL, 속도 기반 규칙, CloudFront의 TLS 종료를 한꺼번에 건너뜁니다. 그러면 오리진은 자기 용량만으로 SYN 플러드와 HTTP 플러드를 맞고, WAF 로그에는 아무것도 남지 않습니다.

**은닉**(cloaking)은 오리진에 인터넷 경로가 아예 없다는 뜻입니다. 기준 설계에서 이는 필터가 아니라 라우팅의 성질입니다. internal ALB에는 프라이빗 주소만 있으므로 나중에 보안 그룹이 느슨해져도 인터넷에서 닿지 않습니다([워크북 08](./08-cdn-edge-delivery.md#edge-origin-path)). [security/14의 옵션 A](../../security/14-waf-edge-api-security.md)가 설명하는 더 약한 설계, 즉 CloudFront prefix list를 허용하고 비밀 헤더를 확인하는 공개 ALB와 비교해 보면, prefix list는 공격자가 만든 것을 포함해 **어느** CloudFront 배포든 허용하고, 헤더는 노출되면 효력을 잃는 공유 비밀입니다. 이 과정은 그 설계를 쓰지 않습니다.

**검토용 우회 경로 목록:** 예전 공개 오리진을 아직 가리키는 DNS 레코드, 같은 클러스터의 다른 로드 밸런서나 `LoadBalancer` 유형 Service, NodePort, 관리 엔드포인트, 같은 애플리케이션을 제공하는 테스트 환경. 한 경로에 붙은 비공개 오리진 표시가 다른 경로가 없다는 증명은 아닙니다.

## 9. 로깅과 지표: 신호별로 증명하는 것

| 신호 | 위치 | 알려 주는 것 | 한계 |
|---|---|---|---|
| WAF 로그 | 이름이 `aws-waf-logs-`로 시작하는 CloudWatch Logs 로그 그룹, S3 버킷, Amazon Data Firehose 스트림 | 요청별 `terminatingRuleId`와 `action`, `nonTerminatingMatchingRules`의 Count 일치, `ruleGroupId`, `labels` | 별도 요금. 남길 요청을 필터링하고 필드를 가릴 수 있음(`xxx`로 표시) |
| CloudWatch 지표 | AWS WAF 지표 | 작업별로 묶인 일치(Count 규칙의 일치는 Count 지표로 보임), 모든 레이블의 레이블 지표 | 규칙 그룹 안 Count 작업 규칙은 웹 ACL 차원 지표를 내지 않고 Rule, RuleGroup, Region 차원만 냄 |
| 샘플 요청 | 웹 ACL 콘솔 탭 또는 `GetSampledRequests` | 지난 3시간 동안 규칙과 일치한 요청 최대 100개와 기본 작업이 적용된 요청 100개, 규칙·작업·URI 포함 | 샘플링을 켜야 함. 규칙 그룹 안 Count 규칙의 샘플은 웹 ACL 화면에 보이지 않음. 로깅의 필드 가리기는 샘플링에 적용되지 않음 |
| 트래픽 개요 대시보드 | WAF 콘솔 | CloudWatch 지표의 거의 실시간 요약 | 요약일 뿐 요청 증거가 아님 |
| Shield Advanced 이벤트 | Shield 콘솔, API, CloudWatch | 보호 대상 자원에서 탐지된 이벤트와 완화 | 구독 시에만 |
| CloudFront 로그 | [워크북 08의 10절](./08-cdn-edge-delivery.md) | 엣지의 요청별 상태 코드와 결과 유형 | 일치한 규칙은 WAF 로그에 있으므로 둘을 함께 봄 |

WAF 로그 필드 전체 목록은 [security/14의 6절](../../security/14-waf-edge-api-security.md)에 있습니다. Count 규칙에는 **로그와 레이블 지표**가 믿을 만한 증거입니다. 샘플 요청과 웹 ACL 지표에서는 관리형 규칙 그룹 안의 Count 일치가 보이지 않을 수 있기 때문입니다.

## 10. 과제: 롤백 조건이 있는 count 모드 규칙 계획

책상 연습입니다. 나중에 승인된 계정에서 누군가 실행할 수 있는 계획을 쓰되 배포하지 않습니다. 결과에는 **측정값이 아닌 풀이 시나리오**라고 표시합니다.

**시나리오.** 한 쇼핑몰이 7절의 기준 경로로 `/assets/*`, `/login`(`POST`, 브라우저 폼), `/api/*`(브라우저가 아닌 모바일 앱), `/api/upload`(최대 5 MB 이미지)를 제공합니다. 7일 동안의 CloudFront 로그로 얻은 기준선은 다음과 같습니다.

| 경로 | 양 | 5분 구간의 IP별 최대 | 참고 |
|---|---|---|---|
| `POST /login` | 하루 120만 건, 성공률 96% | p99는 18건, 주소 하나(`198.51.100.20`)는 최대 640건 | `198.51.100.20`은 여러 직원이 함께 쓰는 협력사 사무실 NAT |
| `/api/upload` | 하루 4만 건 | p99는 6건 | 모든 요청 본문이 8 KB보다 큼 |
| `/api/*`(그 밖) | 하루 900만 건 | p99는 120건 | 모바일 앱, Challenge와 CAPTCHA를 실행할 수 없음 |

웹 ACL 기본 작업은 Allow입니다.

**계획(행마다 채우거나 확인):**

| 우선순위 | 규칙 | 시험 작업 | 시험 중 예상 일치 | Block 전 결정 |
|---|---|---|---|---|
| 10 | 모든 규칙을 `RuleActionOverrides`로 Count 재정의한 `AWSManagedRulesCommonRuleSet` | Count(규칙별) | 하루 4만 건의 `/api/upload` 요청 거의 전부에서 `SizeRestrictions_BODY`(8 KB 초과 본문). 실제 사용자에게 다른 규칙은 거의 0 | 범위 축소 문으로 `/api/upload`를 그룹에서 빼거나, `SizeRestrictions_BODY`를 Count로 두고 다른 경로용 레이블 일치 규칙을 추가 |
| 20 | 규칙을 Count로 재정의한 `AWSManagedRulesSQLiRuleSet` | Count(규칙별) | 실제 사용자에게는 거의 0 | 승격 전에 알려진 클라이언트의 일치를 모두 조사 |
| 30 | `rate-login`: 속도 기반, IP 집계, 기간 300초, 한도 100, 범위 축소는 `POST`이면서 `/login`으로 시작하는 경로 | Count | 일반 사용자는 일치하지 않음(p99 18은 100보다 훨씬 작음). `198.51.100.20`은 100을 넘을 때마다 일치함. 조용한 구간 뒤 5분짜리 단발 버스트 640건이면 한도를 넘은 약 540건이 Count되고, 100을 넘는 상태가 더 오래 이어지면 추정 속도가 한도 아래로 떨어질 때까지 규칙이 계속 작업을 적용하므로 이후 요청 거의 전부가 Count됨 | 오탐: 범위 축소 문 안에 `NOT`(`198.51.100.20`을 담은 IP 세트)을 넣거나, 그 주소에 따로 높은 한도를 둠 |

30행의 조각은 다음과 같습니다. 오탐 결정을 내린 **뒤의** 규칙으로, `PartnerNat` 제외가 들어 있습니다. 표에서 설명한 시험 중에는 이 `NotStatement`가 없습니다. 완전한 웹 ACL이나 배포 명령이 아니라 **웹 ACL 안의 규칙 하나**이며, `PartnerNat`은 새로 만들 IP 세트입니다.

```json
{
  "Name": "rate-login",
  "Priority": 30,
  "Statement": {
    "RateBasedStatement": {
      "Limit": 100,
      "EvaluationWindowSec": 300,
      "AggregateKeyType": "IP",
      "ScopeDownStatement": {
        "AndStatement": {
          "Statements": [
            { "ByteMatchStatement": { "SearchString": "POST", "FieldToMatch": { "Method": {} },
                "TextTransformations": [{ "Priority": 0, "Type": "NONE" }], "PositionalConstraint": "EXACTLY" } },
            { "ByteMatchStatement": { "SearchString": "/login", "FieldToMatch": { "UriPath": {} },
                "TextTransformations": [{ "Priority": 0, "Type": "NONE" }], "PositionalConstraint": "STARTS_WITH" } },
            { "NotStatement": { "Statement": { "IPSetReferenceStatement": {
                "ARN": "arn:aws:wafv2:us-east-1:111122223333:global/ipset/PartnerNat/<id>" } } } }
          ]
        }
      }
    }
  },
  "Action": { "Count": {} },
  "VisibilityConfig": { "SampledRequestsEnabled": true, "CloudWatchMetricsEnabled": true, "MetricName": "rate-login" }
}
```

**과제:**

1. 계획을 완성합니다. 행마다 읽을 증거(로그 필드, 지표, 레이블), 시험 기간, 결정권자를 적습니다.
2. 10행이 규칙 그룹 반환 작업 재정의가 아니라 규칙별 `RuleActionOverrides`를 쓰는 이유를 설명합니다(5절).
3. `PartnerNat` 제외가 있을 때와 없을 때, 단발 버스트와 지속되는 최대치 각각에 대해 `rate-login`의 예상 Count 일치 수를 계산하고, 실제 값이 다를 이유(근사 카운트, 탐지 지연, 속도가 떨어진 뒤 잠시 이어지는 제한)를 적습니다.
4. Block으로 승격하는 규칙마다 **롤백 조건**을 씁니다. 측정 가능한 임곗값, 시간 창, 담당자, 정확한 조치가 들어가야 합니다. 예: "`rate-login`을 Block으로 바꾼 뒤 `/login` 성공률이 기준선 96%보다 2%p 넘게 낮은 상태가 10분 연속 이어지거나 합성 로그인 점검 요청이 하나라도 Block되면, 당직 엔지니어가 `rate-login`을 Count로 되돌리고 변경을 기록한다." 롤백 자체도 몇 초에서 몇 분에 걸쳐 전파되며, 속도 기반 규칙은 카운트가 초기화된다는 점을 적습니다.
5. 모바일 `/api/*` 트래픽에 Challenge나 CAPTCHA 대신 무엇을 적용할지와 그 이유를 정합니다.
6. Anti-DDoS 관리형 규칙 그룹을 계획에 넣을지, 넣는다면 30행과 비교해 어느 위치에 둘지 정합니다.

**검토 기준:**

- 모든 예상 수치가 기준선 표에서 나오고 계산 과정이 보입니다.
- Block 승격마다 관리형 규칙 그룹 안의 Count 일치를 볼 수 있는 증거 출처(샘플 요청만이 아니라 로그나 레이블)가 있습니다.
- 계획은 규칙을 한 번에 하나씩 바꾸고, 결과를 판단하기 전에 전파 시간을 둡니다.
- 계획의 어떤 부분도 오리진을 노출하거나, 인터넷용 로드 밸런서를 추가하거나, 공개 CIDR을 허용하지 않습니다.

## 11. 장애와 복구를 관찰하는 방법

이 표는 **어떤 증거가 각 판정을 확정하는지** 정하는 연습입니다. 나중에 승인된 환경에서 시나리오를 재현하게 되면 바로 이 증거를 모읍니다.

| 장애 | 예상 동작 | 증거 | 그 증거만으로는 확인되지 않는 것 |
|---|---|---|---|
| 관리형 규칙이 정상 업로드를 Block | 승격 직후 `/api/upload`에서 `403` | WAF 로그의 `terminatingRuleId` = 그 그룹, 규칙 `SizeRestrictions_BODY`. CloudFront `403` 비율 상승 | 그룹의 다른 규칙이 안전하다는 것 |
| 공격 중에 속도 한도를 바꿈 | 제한이 최대 1분 멈춤 | 변경 기록. Count 또는 Block 지표가 떨어졌다가 돌아옴 | 새 한도가 적절하다는 것 |
| Block에서 Count로 롤백 | 일부 위치는 잠시 계속 Block | Block 지표가 몇 초에서 몇 분에 걸쳐 감소 | 특정 순간에 모든 위치가 새 설정을 쓴다는 것 |
| 노출된 오리진으로 직접 요청 | WAF 지표는 평탄한데 오리진 과부하 | 오리진 액세스 로그에 CloudFront ENI가 아닌 출발지 | 공격자가 찾은 경로가 무엇인지(8절의 목록으로 조사) |
| 배포에 대한 L3/L4 플러드 | 오리진 영향 없음 | 오리진 지표 평탄. 구독했다면 Shield Advanced 이벤트 | 애플리케이션 계층이 안전하다는 것 |
| Anti-DDoS 이벤트 | 정상이든 아니든 모든 요청이 `event-detected`를 받음 | 레이블 지표 | 레이블이 붙은 요청이 악성이라는 것(의심 레이블만 그렇게 말함) |
| 모바일 API에 Challenge 적용 | 앱 요청 실패 | WAF 로그에서 앱 트래픽의 종료 규칙이 Challenge 규칙. 앱 오류율 상승 | 그 클라이언트가 봇이라는 것 |

**복구도 변경입니다.** 롤백은 사고를 일으킨 변경과 같은 전파 특성을 가진 웹 ACL 업데이트입니다. 롤백 명령과 담당자는 사고 중이 아니라 Block 변경 전에 계획에 적어 둡니다.

## 12. 산출물과 완료 기준

| 산출물 | 완료 조건 |
|---|---|
| 위협 지도 | 2절의 모든 공격을 멈추는 제어와 책임자와 함께 경로 위에 배치함 |
| Shield 결정 | Standard만 쓸지, Advanced를 쓴다면 사용할 기능과 그 전제 조건(지원 플랜, 상태 확인), 비용 |
| 규칙 계획 | 우선순위, 시험 작업, 계산 과정이 있는 예상 일치 수, 오탐 결정, 규칙별 롤백 조건 |
| 오리진 경로 검토 | 기준 경로의 은닉 확인, 우회 경로 목록 점검, 인터넷용 로드 밸런서와 공개 CIDR 인그레스 없음 |
| 증거 계획 | 규칙마다 일치를 증명하는 로그 필드나 지표와 그 알려진 사각지대 |

각 공격이 노리는 계층과 멈추는 곳, AWS WAF가 규칙과 작업을 평가하는 방식, count 모드 시험에 규칙별 재정의를 쓰는 이유, Shield Advanced가 Standard에 더하는 것, 오리진에 공개 경로가 없어야 하는 이유를 근거 문서와 함께 설명할 수 있으면 완료입니다. WAF 배치는 [WAF·엣지·API 보안](../../security/14-waf-edge-api-security.md)에서 검토하고, 오리진 경로는 [워크북 08](./08-cdn-edge-delivery.md#edge-origin-path)에서 다시 본 뒤 [퀴즈](../../quizzes/networking/expert/09-edge-security-waf-ddos-quiz.md)를 풉니다.

## 참고 자료

AWS WAF 개발자 안내서

- [Using rule actions in AWS WAF](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-action.html) (Allow, Block과 기본 `403`, Count, CAPTCHA, Challenge, Monetize)
- [Setting rule priority](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-processing-order.html)
- [Rate-based rule high-level settings](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based-high-level-settings.html), [Rate-based rule caveats](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based-caveats.html)
- [Web request labeling](https://docs.aws.amazon.com/waf/latest/developerguide/waf-labels.html), [Label syntax and naming requirements](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-label-requirements.html)
- [Overriding rule group actions](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-rule-group-override-options.html)
- [Web ACL capacity units (WCUs)](https://docs.aws.amazon.com/waf/latest/developerguide/aws-waf-capacity-units.html)
- [Associating or disassociating protection with an AWS resource](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-associating-aws-resource.html) (미국 동부(버지니아 북부)의 전역 웹 ACL, 자원당 웹 ACL 하나)
- [Baseline rule groups](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-baseline.html) (핵심 규칙 세트, 알려진 잘못된 입력), [Use-case specific rule groups](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-use-case.html) (SQL 데이터베이스), [Account takeover prevention rule group](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-atp.html), [Anti-DDoS rule group](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-anti-ddos.html)
- [Testing and tuning your AWS WAF protections](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing.html), [Monitoring and tuning](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing-activities.html) (count 모드, 오탐 완화, 전파)
- [Logging web ACL traffic](https://docs.aws.amazon.com/waf/latest/developerguide/logging.html), [Logging destinations](https://docs.aws.amazon.com/waf/latest/developerguide/logging-destinations.html), [Configuring logging](https://docs.aws.amazon.com/waf/latest/developerguide/logging-management-configure.html) (`aws-waf-logs-` 접두사, 가리기, 필터)
- [Viewing a sample of web requests](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing-view-sample.html)

AWS Shield (같은 안내서)

- [AWS Shield](https://docs.aws.amazon.com/waf/latest/developerguide/shield-chapter.html), [Shield Standard overview](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-standard-summary.html)
- [Shield mitigation logic for CloudFront and Route 53](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-event-mitigation-logic-continuous-inspection.html) (유효한 웹 트래픽만 통과, TCP SYN 프록시, 엣지 TLS, DNS와 Anycast)
- [Shield Advanced overview](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-advanced-summary.html), [capabilities and options](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-advanced-summary-capabilities.html), [protected resources](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-advanced-summary-protected-resources.html)
- [Automating application layer DDoS mitigation with Shield Advanced](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-automatic-app-layer-response.html) (2026년 3월 26일부터 Anti-DDoS 규칙 그룹이 기본, 150 WCU, 기준선 24시간~30일, CDN 뒤의 ALB)
- [AWS Shield pricing](https://aws.amazon.com/shield/pricing/)

그 밖의 AWS 자료

- [AWS WAF API Reference: CreateWebACL](https://docs.aws.amazon.com/waf/latest/APIReference/API_CreateWebACL.html) (`CLOUDFRONT` 범위와 `us-east-1`, 기본 작업), [RateBasedStatement](https://docs.aws.amazon.com/waf/latest/APIReference/API_RateBasedStatement.html) (한도 범위, 기간, 약 10초마다 속도 확인, 중첩 제한)
- [AWS Best Practices for DDoS Resiliency: infrastructure layer attacks](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/infrastructure-layer-attacks.html), [UDP reflection attacks](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/udp-reflection-attacks.html), [SYN flood attacks](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/syn-flood-attacks.html), [application layer attacks](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/application-layer-attacks.html), [mitigation techniques](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/mitigation-techniques.html), [web application delivery at the edge (BP1)](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/web-application-delivery-at-the-edge-bp1.html)
- [Amazon CloudFront 개발자 안내서: Use AWS WAF protections](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/distribution-web-awswaf.html), [Restrict access with VPC origins](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html)
- [Elastic Load Balancing: HTTP headers and Application Load Balancers](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/x-forwarded-headers.html) (서버 로그의 로드 밸런서 주소, `X-Forwarded-For`)

표준과 그 밖의 1차 자료

- [RFC 4987: TCP SYN Flooding Attacks and Common Mitigations](https://www.rfc-editor.org/rfc/rfc4987.html) (2.2절, 3.6절)
- [BCP 38](https://www.rfc-editor.org/info/bcp38) (출발지 주소 검증)
- [OWASP Top 10 2021](https://owasp.org/Top10/2021/)
- [Kubernetes: Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/) (`ipBlock`, 출발지 재작성, 플러그인 요건)
- [RFC 1918](https://www.rfc-editor.org/rfc/rfc1918.html), [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.html) (예시 주소)

시험 범위 (목차를 정하는 데만 사용)

- [AWS Certified Advanced Networking - Specialty (ANS-C01): Domain 4](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01-domain4.html)

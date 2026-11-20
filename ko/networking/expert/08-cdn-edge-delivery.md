# 08. CDN과 엣지 전송 설계

> **마지막 업데이트**: 2026년 11월 19일
> **실습 경계**: 읽기 전용 관찰만 수행합니다. 과제는 CloudFront가 전송하는 공개 정적 파일에 `curl` 요청을 몇 번 보낼 뿐이며, 이 워크북은 배포(distribution), 오리진, VPC, 로드 밸런서를 만들지 않습니다.
> **검증 상태**: Amazon CloudFront 개발자 안내서, AWS 지식 센터 문서, RFC 9111/5861을 확인했습니다. 집필 중 CloudFront가 전송하는 공개 파일 하나의 응답 헤더를 관찰했으며 **Hit 응답만 보았고 Miss는 포착하지 못했습니다**. 배포를 **구성하거나 측정하지 않았습니다**.

이 워크북의 목표는 요청이 **어디에서 응답되는지**(엣지 POP, 리전 엣지 캐시, Origin Shield, 오리진)를 예측하고, 응답 헤더로 그 이유를 설명하며, 오리진이 CloudFront를 통해서만 닿도록 엣지에서 오리진까지의 경로를 그리는 것입니다.

기초는 링크로 대신합니다. DNS 캐시와 TTL 동작은 [네트워크 기초 Part 3](../../basics/06-network-fundamentals-part3.md)에, HTTP/1.1 메시지 구조는 [Part 3의 요청과 응답 읽기](../../basics/06-network-fundamentals-part3.md#http11-message-structure)에, TLS 핸드셰이크와 SNI, 종료 지점은 [Part 2](../../basics/06-network-fundamentals-part2.md)에, CloudFront·ALB·ACM의 역할은 [Part 4](../../basics/06-network-fundamentals-part4.md)에 있습니다. Part 3는 DNS 캐시를 다루지만 HTTP 캐시는 다루지 않으므로, 이 장에 필요한 HTTP 캐시 용어는 6절에서 정의합니다. BGP 기반 Anycast는 [워크북 02](02-routing-policy-convergence.md)를, 오리진 뒤의 사설 연결은 [워크북 07](07-wan-hybrid-connectivity.md)을 바탕으로 합니다.

**준비 조건:** `curl`이 있는 셸과 인터넷 연결만 있으면 됩니다. AWS 계정은 필요 없습니다. 참조 설계를 직접 구축하면 CloudFront 요청·데이터 전송, 무료 한도를 넘는 무효화 경로, Origin Shield 요청, 로드 밸런서 시간, 인스턴스 시간 요금이 발생하며 그 **비용과 정리 책임은 학습자 본인**에게 있습니다. 승인된 기존 실습 계정 밖에서 자원을 만들지 않습니다.

## 1. 질문을 정하고 읽기

시험 범위는 읽을 범위를 정하는 데만 씁니다. 숫자와 동작은 첫 열의 공식 문서로 확인합니다.

| 읽을 자료 | 대응하는 시험 범위 | 자신의 말로 답할 질문 |
|---|---|---|
| [How CloudFront delivers content](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/HowCloudFrontWorks.html), [Origin Shield](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/origin-shield.html) | ANS-C01 Domain 1 Network Design, Task 1.1(엣지 네트워크 서비스) | 어떤 요청이 리전 엣지 캐시를 건너뛰고, 어떤 요청이 Origin Shield를 건너뛰는가? |
| [Understand the cache key](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html), [Control origin requests with a policy](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/controlling-origin-requests.html) | ANS-C01 Domain 1, Domain 2 Network Implementation | 오리진은 받아야 하지만 캐시 키에는 **넣으면 안 되는** 값은 무엇인가? |
| [Manage how long content stays in the cache](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Expiration.html), [RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html), [RFC 5861](https://www.rfc-editor.org/rfc/rfc5861.html) | ANS-C01 Domain 2, 프로토콜 원리 | 오리진의 `s-maxage`와 캐시 정책의 최대 TTL이 다르면 무엇이 이기는가? |
| [Restrict access with VPC origins](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html), [Restrict access to an Amazon S3 origin](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html) | ANS-C01 Domain 4 Network Security, Compliance, and Governance | 무엇이 오리진을 CloudFront 경로 밖에서 닿지 않게 만드는가? |
| [View CloudFront metrics](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/viewing-cloudfront-metrics.html), [Standard log fields](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/standard-logs-reference.html) | ANS-C01 Domain 3 Network Management and Operation | POP 적중과 Origin Shield 적중을 구분하는 필드는 무엇인가? |

읽은 뒤 뷰어, POP, 리전 엣지 캐시, (쓴다면) Origin Shield, 오리진을 그리고, **캐시 계층**과 **연결 구간**을 다른 선으로 구분합니다. 구간마다 TCP 또는 QUIC 연결과 TLS 세션이 따로 있으므로 "끝까지 HTTPS"는 구간 하나가 아니라 모든 구간에 대한 주장입니다.

## 2. CDN을 쓰는 이유

CDN은 세 가지를 바꾸며, 설계 문서는 그중 무엇을 사려는지 밝혀야 합니다.

| 목표 | 동작 | 설계에 적을 한계 |
|---|---|---|
| **지연(RTT) 단축** | 뷰어의 TCP/QUIC·TLS 핸드셰이크가 먼 오리진이 아니라 가까운 POP에서 끝나고, 캐시 적중이면 오리진 왕복이 아예 없음 | 캐시 미스는 여전히 POP에서 오리진까지의 경로를 지남. Part 2에서 본 TLS 1.3 전체 핸드셰이크 약 1 RTT가 짧은 뷰어-POP RTT로 바뀔 뿐임 |
| **오리진 부하 감소** | 적중은 오리진에 닿지 않고, 리전 엣지 캐시·Origin Shield·요청 병합이 남은 미스를 줄임 | 적중률은 CDN이 아니라 고른 캐시 키와 TTL이 정함(5절, 6절) |
| **흡수** | 트래픽이 오리진 하나가 아니라 넓게 분산된 엣지에 도착 | CDN을 우회해 오리진에 닿을 수 없을 때만 오리진이 보호됨(9절). 볼륨형·L7 공격 방어는 다음 워크북(엣지 보안)의 주제 |

CloudFront는 요청을 가장 잘 처리할 수 있는 엣지 로케이션, 보통 지연이 가장 낮은 곳으로 보내고, 오리진 쪽 트래픽은 AWS 네트워크로 운반합니다.

## 3. 요청 유도: DNS 방식과 Anycast

뷰어가 **어느 POP**과 통신할지 누군가 정해야 합니다. 흔한 방식은 두 가지입니다.

| 방식 | POP 선택 방법 | 장애 조치와 세밀도 | 쓰이는 곳 |
|---|---|---|---|
| **DNS 방식** | CDN의 권한 DNS가 뷰어의 리졸버에 적절한 POP 주소를 답함 | 리졸버가 다시 질의할 때 바뀌며 이미 캐시된 답의 영향을 받음(Part 3: 지금 TTL을 줄여도 이미 캐시된 답은 짧아지지 않음). 리졸버가 클라이언트 서브넷 정보를 전달하지 않으면([RFC 7871](https://www.rfc-editor.org/rfc/rfc7871.html)) 권한 서버는 뷰어가 아니라 **리졸버** 주소를 봄 | CloudFront 기본 동작: "DNS가 요청을 가장 잘 처리할 수 있는 CloudFront POP(엣지 로케이션)으로 보낸다" |
| **Anycast** | 여러 사이트가 **같은** prefix를 BGP로 광고하고, 일반 라우팅이 패킷을 위상상 가장 가까운 광고 지점으로 보냄([RFC 4786](https://www.rfc-editor.org/rfc/rfc4786.html)) | 장애 조치는 BGP 철회와 수렴을 따름(워크북 02). RFC 4786은 라우팅 변화가 세션의 나머지를 다른 노드로 보낼 수 있으므로 노드 선택이 트랜잭션보다 충분히 오래 안정적이어야 한다고 경고함 | CloudFront **Anycast static IPs**: 허용 목록 등록이나 apex 도메인 A 레코드용으로 신청하는 전용 고정 IPv4(또는 IPv4와 IPv6) 목록. SNI와 함께 동작 |

**실무 포인트:** DNS 방식에서는 먼 리졸버를 쓰는 뷰어가 자신과 먼 POP에 도착할 수 있습니다. Anycast에서 "가장 가까움"은 지연이 아니라 BGP 홉 수나 선호도 기준입니다. 어느 방식도 연속된 두 요청이 같은 POP, 같은 서버에 닿는다고 보장하지 않으며, 이 점이 11절 과제에서 중요합니다.

## 4. 캐시 계층: POP, 리전 엣지 캐시, Origin Shield, 오리진

**GET 하나가 처리되는 순서:**

1. DNS가 뷰어를 POP으로 보냅니다. 객체가 그 POP에 캐시되어 있고 유효하면 POP이 바로 돌려줍니다.
2. POP에서 미스이면 POP은 **보통** 가장 가까운 **리전 엣지 캐시**에 묻습니다. 리전 엣지 캐시는 개별 POP보다 캐시가 커서, POP에 남을 만큼 인기가 없어진 객체도 더 오래 남습니다.
3. 리전에서도 미스이면 CloudFront가 (켜져 있으면 Origin Shield를 거쳐) 오리진에 요청합니다. 응답은 리전 엣지 캐시를 거쳐 POP으로 돌아오고 **두 곳 모두** 사본을 저장합니다. CloudFront는 첫 바이트가 도착하는 즉시 뷰어로 전달을 시작합니다.

![CDN 캐시 MISS 다음 HIT 애니메이션. ① 클라이언트 A가 배포 이름을 조회하면 DNS가 지연이 가장 낮은 엣지 POP을 답하고, A가 GET /img/logo.png를 보낸다. ② 엣지 POP에는 그 캐시 키의 객체가 없어 MISS이고, 리전 엣지 캐시에 물었지만 그곳도 MISS다. ③ CloudFront VPC 오리진을 거쳐 닿는 internal ALB인 오리진이 200과 Cache-Control: max-age=3600을 돌려준다. ④ 돌아오는 길에 리전 엣지 캐시와 POP이 각각 사본을 저장하고, 클라이언트 A는 x-cache: Miss from cloudfront를 받는다. ⑤ 클라이언트 B가 같은 POP에 같은 객체를 요청하면 HIT이며, POP이 캐시에서 Age: 42와 x-cache: Hit from cloudfront로 응답하고 오리진에는 요청이 가지 않는다.](../../.gitbook/assets/ko-networking-expert-08-cdn-edge-delivery-anim-0.svg)

**리전 엣지 캐시를 건너뛰는 요청**(개발자 안내서):

- 프록시 HTTP 메서드 `PUT`, `POST`, `PATCH`, `OPTIONS`, `DELETE`는 POP에서 오리진으로 바로 갑니다.
- 요청 시점에 동적 요청으로 판단된 요청은 오리진으로 바로 갑니다.
- 오리진이 S3 버킷이고 요청에 최적인 리전 엣지 캐시가 버킷과 같은 리전에 있으면 POP이 버킷으로 바로 갑니다.

리전 엣지 캐시는 POP과 기능이 같아서, 무효화는 두 곳 모두에서 객체를 지웁니다.

**Origin Shield**는 리전 엣지 캐시와 오리진 사이에 넣는 선택형 계층입니다. 모든 CloudFront 캐시 계층에서 오리진으로 가는 요청이 이곳을 지나므로 객체 하나를 오리진 요청 한 번만으로 가져올 수 있고, 오리진과 같은 리전에서 생긴 요청은 이 계층을 건너뜁니다. Origin Shield 리전은 오리진까지 지연이 가장 낮은 곳으로 고르며, CloudFront 리전 엣지 캐시가 있는 리전에서만 제공됩니다. 요금은 Origin Shield가 **추가 계층**으로 동작한 요청 수에 매깁니다. 동적 요청(`PUT`, `POST`, `PATCH`, `DELETE`, 그리고 TTL이 3600초 미만이거나 캐시가 꺼진 `GET`/`HEAD`)은 항상 해당되고, 캐시 가능한 요청은 Origin Shield와 다른 리전의 리전 엣지 캐시에서 올 때만 해당됩니다. AWS는 오리진으로 프록시되는 동적 콘텐츠, 캐시 가능성이 낮은 콘텐츠, 드물게 요청되는 콘텐츠를 맞지 않는 경우로 듭니다.

**요청 병합(request collapsing):** 첫 미스가 오리진 응답을 기다리는 동안 같은 캐시 키의 요청이 더 오면 CloudFront는 그 요청들을 잠시 멈췄다가 첫 응답으로 모두 답합니다. 캐시 키가 같은 요청만 병합됩니다. 로그에는 첫 요청이 `Miss`, 병합된 요청이 `Hit`로 남습니다.

## 5. 캐시 키 설계와 적중률

**캐시 키**는 캐시 안 객체의 고유 식별자입니다. 요청이 이전 요청과 같은 캐시 키를 만들고 그 객체가 캐시에 있으며 유효하면 적중입니다. RFC 9111은 최소 키를 요청 메서드와 대상 URI로 정의하고, `Vary`가 요청 헤더를 키에 더합니다.

**CloudFront 기본값:** 배포의 도메인 이름과 URL 경로입니다. 쿼리 문자열, 헤더, 쿠키는 기본적으로 키에 **들어가지 않습니다**. 개발자 안내서는 `/content/stories/example-story.html`에 대해 쿼리 문자열, `User-Agent`, `Referer`, `session_id` 쿠키가 모두 다른 두 요청을 예로 들며, 두 번째 요청도 적중이라고 설명합니다. `OPTIONS` 응답은 `GET`, `HEAD` 응답과 따로 캐시됩니다.

**정책 두 개, 역할 두 개:**

| 정책 | 제어 대상 | 규칙 |
|---|---|---|
| **캐시 정책(cache policy)** | 캐시 키에 넣을 값과 최소·기본·최대 TTL | 응답을 바꾸는 값만 넣음 |
| **오리진 요청 정책(origin request policy)** | 미스 때 오리진이 받을 값, 단 캐시 키에는 **넣지 않음** | 캐시 키에 넣은 값은 자동으로 오리진에 전달됨. 오리진에는 필요하지만 캐시를 쪼개면 안 되는 값(분석, 텔레메트리)에 이 정책을 씀 |

오리진 요청에는 항상 URL 경로, (있다면) 본문, 그리고 `Host`, `User-Agent`, `X-Amz-Cf-Id`처럼 CloudFront가 자동으로 넣는 헤더가 포함됩니다.

**키를 쪼개는 값과 대안:**

| 후보 | 문제 | 대안 |
|---|---|---|
| `Accept-Language` | `en-US,en`, `en,en-US`, `en-US, en`, `en-US`가 모두 영어인데 서로 다른 객체가 됨 | 언어를 URL에 넣음(`/en-US/...`) |
| `User-Agent` | 변형이 수천 개 | 키에서 뺌 |
| 세션 쿠키 | 사용자마다 달라서 사용자별 사본이 생김 | 키에서 빼거나 응답을 캐시 불가로 표시 |
| 오리진이 쓰지 않는 쿼리 문자열 | 중복 객체 | 빼거나 이름을 지정한 파라미터만 넣음 |

**적중률**(cache hit ratio)은 뷰어 요청 중 적중의 비율입니다. 키에 꼭 필요한 값만 넣고, 신선도가 허락하는 곳에서 TTL을 늘리고, 뷰어가 여러 지역에 퍼져 있으면 Origin Shield를 써서 높입니다.

## 6. TTL, Cache-Control, 무효화

**이 장에서 쓰는 HTTP 캐시 용어**(RFC 9111): 저장된 응답은 신선도 수명(freshness lifetime)이 지나기 전까지 **신선**(fresh)하고, 지나면 **오래된**(stale) 응답입니다. 공유 캐시(CDN)는 `s-maxage`, `max-age`, `Expires`에서 `Date`를 뺀 값 순으로 처음 있는 것을 수명으로 씁니다. 오래된 응답을 다시 쓰려면 보통 오리진과 **검증(validation)**해야 하며, 조건부 요청이 `304 Not Modified`를 받을 수 있습니다. `Age` 헤더는 응답이 오리진에서 생성되거나 검증된 뒤 지난 초를 보낸 쪽이 추정한 값이며, 이 헤더가 있다는 것은 이번 요청에 대해 오리진이 응답을 만들지 않았다는 뜻입니다. 응답은 신선도 수명이 현재 나이(age)보다 큰 동안 신선하므로, 남은 시간은 수명에서 `Age`를 뺀 값입니다. `no-cache`는 검증에 성공하기 전에는 저장된 응답을 다시 쓰지 말라는 뜻이고, `no-store`는 저장하지 말라는 뜻입니다.

**CloudFront가 오리진 헤더와 캐시 정책 TTL을 합치는 방식:**

| 오리진이 보내는 값 | 최소 TTL = 0 | 최소 TTL > 0 |
|---|---|---|
| `Cache-Control: max-age` | `max-age`와 최대 TTL 중 작은 값만큼 캐시 | 범위 고정: 최소 TTL보다 작으면 최소 TTL, 최대 TTL보다 크면 최대 TTL |
| `max-age`**와** `s-maxage` | CloudFront는 `s-maxage`(최대 TTL이 상한), 브라우저는 `max-age` | `s-maxage`를 최소·최대 TTL 범위로 고정 |
| `max-age` 없음 | 기본 TTL | 최소 TTL과 기본 TTL 중 큰 값 |
| `Expires` | 그 시각과 최대 TTL 중 먼저 오는 쪽까지 | 최소·최대 TTL 범위로 고정 |
| `no-cache`, `no-store`, `private` 중 하나 이상 | CloudFront와 브라우저 모두 헤더를 따름 | 그래도 CloudFront는 **최소 TTL**만큼 캐시 |

그 밖의 규칙:

- `max-age`와 `Expires`가 함께 있으면 CloudFront는 `max-age`만 씁니다.
- 뷰어가 GET에 넣은 `Cache-Control`이나 `Pragma`로는 CloudFront를 오리진으로 되돌려 보낼 수 없습니다. CloudFront는 그 헤더를 무시합니다.
- 캐시 정책 없이(레거시 설정) 쓰면 기본 TTL은 24시간입니다.
- **함정:** 최소 TTL이 0보다 크면 오리진이 `no-cache`를 보내도 최소 TTL만큼 캐시되며, 나중에 오리진에 닿을 수 없게 되면 CloudFront가 예전에 받은 객체를 내줄 수 있습니다. 이를 막으려면 `Cache-Control: stale-if-error=0`을 붙입니다.

**의도적으로 오래된 사본 쓰기:** CloudFront는 [RFC 5861](https://www.rfc-editor.org/rfc/rfc5861.html) 확장을 지원합니다.

- `max-age=3600, stale-while-revalidate=600`: 한 시간이 지나면 CloudFront가 백그라운드에서 새 사본을 가져오는 동안 최대 10분 동안 오래된 사본을 내줍니다.
- `max-age=3600, stale-if-error=86400`: 한 시간이 지난 뒤 오리진에 닿을 수 없거나 5xx 오류가 나면 최대 24시간 동안 오래된 사본을 계속 내줍니다.
- 두 경우 모두 오래된 사본은 지시어 값과 **최대 TTL** 중 작은 값까지만 쓰입니다.

**무효화와 버전이 붙은 파일 이름:**

| | 무효화(invalidation) | 버전 이름(`app.3f9c.js`) |
|---|---|---|
| 효과 | POP과 리전 엣지 캐시에서 객체를 지우고 다음 요청은 오리진으로 감 | 새 URL은 새 캐시 키이며 이전 것과 함께 존재 |
| 브라우저·회사 프록시 캐시 | 영향 없음. 사용자는 그 캐시에서 만료될 때까지 예전 사본을 볼 수 있음 | 페이지가 새 이름을 참조하므로 모든 캐시가 새로 받음 |
| 비용 | 계정당 매월 무효화 경로 1,000개까지 무료, 그 뒤 경로당 과금. `*` 와일드카드 경로는 지우는 파일 수와 관계없이 경로 하나로 셈 | 무효화 요금 없음. 새 버전을 엣지로 전송하는 비용은 냄 |
| 속도 할당량 | 초당 경로·태그 150개, 초당 와일드카드 무효화 1개(개발자 안내서 할당량 페이지) | 없음 |
| 롤백 | 다시 무효화 | 페이지가 이전 이름을 가리키게 되돌림 |

AWS는 자주 바꾸는 파일에 버전 이름을 권장합니다. CloudFront FAQ와 지식 센터 문서 하나는 아직 예전의 "동시에 진행 중" 한도(배포당 개별 파일 3,000개, 와일드카드 경로 15개)를 적고 있습니다. 현재 기준은 개발자 안내서의 할당량 페이지이므로 설계하는 날 그 페이지를 확인합니다.

## 7. 엣지와 오리진 구간의 TLS

뷰어 구간과 오리진 구간은 서로 다른 TLS 세션입니다(Part 2: 종료 지점이 다음 홉을 자동으로 암호화하지 않음).

**뷰어 → CloudFront:**

- 뷰어 프로토콜 정책은 HTTP와 HTTPS 허용, HTTP를 HTTPS로 리디렉션, HTTPS만 허용 중 하나입니다.
- CloudFront 배포에 쓰는 ACM 인증서는 **미국 동부(버지니아 북부)** 리전에서 요청하거나 가져와야 하며, CloudFront가 이를 각 로케이션에 배포합니다.
- HTTP/2는 TLS 1.2 이상과 SNI를, HTTP/3는 TLS 1.3과 SNI를 지원하는 뷰어가 필요합니다.

**CloudFront → 오리진:**

- 오리진 프로토콜 정책은 HTTP만, HTTPS만, 뷰어 프로토콜과 동일(match viewer) 중 하나입니다. match viewer는 뷰어 정책이 HTTPS 리디렉션이나 HTTPS만 허용일 때만 고릅니다.
- 오리진 인증서는 배포에 적은 오리진 도메인 이름, 또는 `Host` 헤더를 전달한다면 그 이름과 일치해야 하며, CloudFront는 그 이름을 SNI로도 보냅니다. 이름이 맞지 않거나, 신뢰하는 CA가 발급하지 않았거나, 체인이 잘못되었거나, 만료된 인증서이면 CloudFront는 연결을 끊고 뷰어에게 `502`를 돌려줍니다.
- ALB 오리진의 인증서는 us-east-1의 뷰어 인증서와 별개로 **ALB가 있는 리전**에 둡니다.
- **VPC 오리진**에서는 CloudFront가 공개 DNS 조회가 아니라 ARN으로 internal ALB에 닿습니다. 설정한 호스트 이름은 SNI와 인증서 일치 확인에만 쓰이므로 internal ALB를 가리키는 공개 DNS 레코드가 필요 없습니다(AWS Networking 블로그, 2026년).

**실무 포인트:** 구간마다 프로토콜, 인증서와 그 리전, 최소 TLS 버전, 인증서 갱신 책임자를 적습니다. 설계 검토에서 "HTTPS"는 두 줄이 모두 채워졌다는 뜻입니다.

## 8. 동적 가속, HTTP/2, HTTP/3

모든 응답을 캐시할 수는 없지만, CDN은 캐시되지 않는 트래픽에도 도움이 됩니다.

- **짧은 뷰어 핸드셰이크:** TCP/QUIC와 TLS 핸드셰이크가 가까운 POP과 이뤄집니다.
- **오리진 지속 연결:** 응답을 받은 뒤 CloudFront는 다음 요청이 새 TCP·TLS 핸드셰이크를 생략하도록 오리진 연결을 몇 초 동안 유지합니다(사용자 지정 오리진과 VPC 오리진은 keep-alive 시간 제한을 설정할 수 있음).
- **AWS 네트워크:** 엣지와 AWS 리전 안 오리진 사이의 트래픽은 AWS 네트워크에 머뭅니다.
- **동적 요청은 리전 엣지 캐시를 건너뜀**(4절): 캐시 조회 단계가 하나 더 붙지 않습니다.

**구간별 프로토콜 버전:**

| 구간 | 버전 | 참고 |
|---|---|---|
| 뷰어 ↔ CloudFront | HTTP/1.0과 1.1은 기본으로 켜짐, HTTP/2와 HTTP/3는 켤 수 있음 | HTTP/3는 UDP 위의 QUIC로 동작하며, CloudFront는 연결 마이그레이션을 지원해 뷰어가 네트워크를 바꿔도 연결이 유지됨 |
| CloudFront → 사용자 지정 오리진 | HTTP/1.1 | 뷰어 쪽 HTTP/2 다중화가 오리진까지 이어지지 않으므로 오리진 연결 용량을 따로 계획함 |

HTTP/2와 HTTP/3는 HTTP 의미를 유지하고 프레이밍만 바꾸므로(Part 3), 캐시 키와 TTL은 어느 버전에서나 똑같이 동작합니다.

## 9. CloudFront 대응과 엣지에서 오리진까지의 경로

| 개념 | CloudFront 기능 | 설계 메모 |
|---|---|---|
| 캐시 키와 TTL | 캐시 정책 | 키에는 최소한의 값, TTL은 동작(behavior)별 |
| 캐시를 쪼개지 않고 전달 | 오리진 요청 정책 | 오리진에는 필요하지만 캐시가 구분하면 안 되는 값 |
| 경로별 동작 | 캐시 동작(경로 패턴) | 예: `/assets/*`는 버전 이름과 긴 TTL, `/api/*`는 캐시 끔 |
| 비공개 S3 오리진 | 오리진 액세스 제어(OAC) | 레거시 OAI 대신 권장 |
| 비공개 ALB·NLB·EC2 오리진 | VPC 오리진 | 아래의 기준 설계 |

**S3용 OAC:** CloudFront가 오리진 요청에 서명하고 버킷 정책은 그 배포만 허용합니다. AWS가 OAI 대신 OAC를 권장하는 이유는 모든 리전의 S3 버킷(2022년 12월 이후 출시된 옵트인 리전 포함), SSE-KMS, 동적 요청(`PUT`, `DELETE`)을 지원하기 때문입니다. OAC를 쓰려면 S3 객체 소유권(Object Ownership)이 **버킷 소유자 적용**(Bucket owner enforced)이어야 하며, 새 버킷의 기본값입니다. S3 **웹 사이트 엔드포인트**는 사용자 지정 오리진이므로 OAC를 쓸 수 없습니다.

<a id="edge-origin-path"></a>

### 엣지에서 오리진까지: VPC 오리진과 internal ALB

**기준 설계:** CloudFront → **VPC 오리진** → 프라이빗 서브넷의 **internal** ALB → 대상 그룹입니다. 오리진에는 공인 주소가 없고, 들어오는 길은 CloudFront뿐입니다. CloudFront 뒤에 인터넷용(internet-facing) 로드 밸런서를 두지 않으며, 오리진에 공개 CIDR을 허용하는 인바운드 규칙을 절대 넣지 않습니다.

![엣지에서 오리진까지의 경로 애니메이션. ① 뷰어가 HTTPS로 캐시할 수 있는 GET /menu.json을 보낸다. TLS는 엣지 POP에서 끝나고, 요청은 POP과 리전 엣지 캐시에서 모두 MISS다. ② CloudFront가 VPC 오리진으로 오리진에 연결한다. 프라이빗 서브넷의 서비스 관리형 ENI(예: 10.0.11.25)가 internal ALB(10.0.12.40)로 연결을 연다. ③ ALB 보안 그룹은 CloudFront-VPCOrigins-Service-SG(또는 CloudFront origin-facing 관리형 prefix list)에서 온 트래픽만 허용한다. ④ ALB 리스너가 대상 그룹으로 전달하고, 대상은 ALB 보안 그룹에서 온 트래픽만 받는다. ⑤ 인터넷 클라이언트가 ALB에 직접 접속하려 하지만 VPC 경계에서 실패한다. internal ALB는 프라이빗 주소만 가지므로 인터넷에서 그곳으로 가는 경로가 없다. VPC에는 인터넷 게이트웨이가 연결되어 있지만 이 경로의 라우팅에는 쓰이지 않는다.](../../.gitbook/assets/ko-networking-expert-08-cdn-edge-delivery-anim-1.svg)

**VPC 오리진 요건**(개발자 안내서):

- **오리진 종류:** 프라이빗 서브넷의 ALB, NLB, EC2 인스턴스이며, 완전히 배포되어 Active 상태여야 합니다. Gateway Load Balancer와 TLS 리스너가 있는 NLB는 오리진이 될 수 없고, NLB에는 보안 그룹이 연결되어 있어야 합니다.
- **VPC:** VPC에 **인터넷 게이트웨이가 연결**되어 있어야 합니다. 이는 VPC가 인터넷 트래픽을 받을 수 있음을 나타낼 뿐 오리진으로 가는 **라우팅에는 쓰이지 않으며**, 라우트 테이블을 바꿀 필요도 없습니다.
- **서브넷:** CloudFront가 프라이빗 서브넷에 서비스 관리형 ENI를 만들므로 비어 있는 IPv4 주소가 하나 이상(이중 스택이면 IPv6 주소도 하나 이상) 있어야 합니다.
- **보안 그룹:** 오리진에 보안 그룹이 있어야 합니다. 인바운드 허용 원본은 둘 중 하나입니다. 미리 넣을 수 있는 **CloudFront 관리형 prefix list**(`com.amazonaws.global.cloudfront.origin-facing`, 이중 스택이면 IPv6 목록도), 또는 VPC 오리진을 만든 뒤 생기며 자신의 배포만 허용해 더 제한적인 서비스 관리형 보안 그룹(**`CloudFront-VPCOrigins-Service-SG`**)입니다. 이 그룹은 수정하지 않으며, 같은 이름 접두사로 보안 그룹을 만들지 않습니다.
- **지원하지 않는 것:** gRPC, Lambda@Edge의 origin request·origin response 트리거. CloudFront에서 오리진으로 가는 트래픽에는 인바운드 NACL 규칙이 평가되지 않지만, 돌아가는 경로에서는 **아웃바운드** NACL 규칙이 평가되므로 CloudFront origin-facing 범위로 가는 임시 TCP 포트 1024–65535를 허용해야 합니다.
- **할당량:** 계정당 VPC 오리진 25개(조정 가능), VPC 오리진 하나에 배포 50개.

**internal ALB를 CloudFront 밖에서 닿을 수 없는 이유:** internal 로드 밸런서의 노드는 프라이빗 IP 주소만 가집니다. DNS 이름은 공개적으로 조회되지만 그 프라이빗 주소로 풀리므로 VPC에 접근할 수 있는 클라이언트만 닿습니다. 이는 필터가 아니라 라우팅의 성질이라서, 나중에 보안 그룹 규칙이 느슨해져도 유지됩니다. ALB를 Kubernetes Ingress로 만든다면 [AWS Load Balancer Controller](../03-aws-lb-controller.md)에서 `alb.ingress.kubernetes.io/scheme: internal`로 지정합니다.

**prefix list와 서비스 보안 그룹의 차이:** 관리형 prefix list는 모든 CloudFront origin-facing 서버를 담으므로 **어느 배포든** 허용하고, VPC 오리진 서비스 그룹은 자신의 배포만 허용합니다. prefix list를 인바운드 규칙에 쓰면 보안 그룹 규칙 할당량에서 규칙 55개의 가중치로 셉니다. 헤더로 보호하는 공개 ALB 오리진 방식과 WAF 배치는 [WAF·엣지·API 보안](../../security/14-waf-edge-api-security.md)을 참고하고, 다음 워크북(엣지 보안)은 이 경로 위에 공격 쪽 관점을 더합니다.

## 10. 관측: 신호별로 증명하는 것

| 신호 | 위치 | 알려 주는 것 |
|---|---|---|
| `x-cache` 응답 헤더 | 뷰어 응답 | `Hit from cloudfront`, `RefreshHit from cloudfront`(만료된 사본을 오리진과 재검증), `Miss from cloudfront` |
| `Age` | 뷰어 응답 | 사본이 오리진에서 생성되거나 검증된 뒤 지난 초. 적중이면 `Date`에 `Age`를 더한 값이 대략 현재 시각 |
| `x-amz-cf-pop` | 뷰어 응답 | 응답한 POP. 두 번째 Miss에서 결론을 내리기 전에 요청 사이에 비교함 |
| `Via` | 뷰어 응답 | 메시지를 처리한 중개자([RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)). 같은 POP에 보낸 두 요청에서 서버 식별자가 다를 수 있음 |
| `x-edge-result-type` | 표준 로그 | `Hit`, `RefreshHit`, `Miss`, `LimitExceeded`, `CapacityExceeded`, `Error`, `Redirect`. WebSocket과 gRPC는 항상 `Miss` |
| `x-edge-detailed-result-type` | 표준 로그 | Origin Shield가 응답하면 `OriginShieldHit`(Origin Shield 역할을 하는 리전 엣지 캐시로 라우팅된 요청은 `Hit`로 기록) |
| `time-to-first-byte` | 표준 로그 | 요청을 받은 뒤 첫 바이트를 쓰기까지의 초, 서버에서 측정 |
| 캐시 적중률, 오리진 지연 | CloudWatch 추가 지표(유료, 배포당 최대 8개, us-east-1에 게시) | 적중률은 캐시 가능한 요청만 셈(`POST`, `PUT`, 오류 제외). 오리진 지연은 오리진에서 응답한 요청의 첫 바이트 지연 |

**두 번째 요청이 여전히 Miss일 수 있는 이유**(AWS 지식 센터): 엣지 로케이션은 자신이 받은 요청의 객체만 캐시하므로 다른 POP에 도착한 요청은 미스입니다. 드물게 요청되는 객체는 만료 전에 밀려날 수 있습니다. 캐시 키에 넣은 헤더, 쿠키, 쿼리 문자열이 요청을 쪼갭니다. 오리진의 `Cache-Control`이나 `Expires`가 수명을 줄일 수 있습니다.

## 11. 과제: 응답 헤더로 미스와 적중 읽기

읽기 전용 관찰입니다. 결과에는 **제3자 배포 관찰**이라고 표시합니다. 그 배포의 캐시 정책은 볼 수 없으므로 모든 결론은 헤더에서 추론한 것입니다.

**대상 고르기:** 응답에 `x-cache: ... from cloudfront`와 `x-amz-cf-pop`이 있는 공개 정적 파일(이미지, CSS, JavaScript) 아무것이나 고릅니다. 특정 사이트가 어떻게 동작한다고 가정하지 말고 먼저 헤더를 확인합니다. 승인된 자신의 배포가 있다면 알려진 정책과 비교할 수 있으므로 그것을 씁니다.

```bash
URL='https://<cloudfront-served-host>/<path-to-static-asset>'
curl -sI "$URL" | grep -iE '^(HTTP|date|age|cache-control|x-cache|via|x-amz-cf-pop)'
sleep 5
curl -sI "$URL" | grep -iE '^(HTTP|date|age|cache-control|x-cache|via|x-amz-cf-pop)'
```

`curl -I`는 `HEAD`를 보냅니다. 개발자 안내서에 따르면 `GET`, `HEAD`와 따로 캐시되는 것은 `OPTIONS` 응답뿐이므로, 헤더는 `GET`이 쓰는 것과 같은 캐시 객체를 보여 줍니다. 본문을 버리는 실제 `GET`으로 반복하려면 `curl -s -o /dev/null -D - "$URL"`을 씁니다.

**예시 출력**(형태만 보여 주며 특정 사이트에서 캡처한 값이 아님, 실제 값은 다름):

```text
HTTP/2 200
date: Thu, 19 Nov 2026 09:00:00 GMT
cache-control: max-age=86400
x-cache: Miss from cloudfront
via: 1.1 <edge-server-id-1>.cloudfront.net (CloudFront)
x-amz-cf-pop: <POP-code>

HTTP/2 200
date: Thu, 19 Nov 2026 09:00:00 GMT
cache-control: max-age=86400
x-cache: Hit from cloudfront
via: 1.1 <edge-server-id-2>.cloudfront.net (CloudFront)
x-amz-cf-pop: <POP-code>
age: 5
```

**해석 규칙:**

| 관찰 | 결론 | 다음 확인 |
|---|---|---|
| Miss 다음 Hit, `x-amz-cf-pop` 같음 | 첫 요청이 이 POP의 캐시(또는 POP이 읽은 리전 캐시)를 채웠고, 두 번째는 오리진 없이 응답됨 | `age`가 요청 간격과 비슷하고 `date`는 그대로 |
| **첫** 요청부터 Hit | 다른 뷰어가 이미 캐시를 채움 | `date` + `age` ≈ 현재. `age`가 `max-age`에 가까우면 곧 만료 |
| Miss 다음 Miss | 다른 POP, 밀려남, 무언가 다른 값이 들어간 캐시 키, 캐시 불가 응답 중 하나 | `x-amz-cf-pop` 비교, `cache-control`에서 `no-store`, `private`, `max-age=0` 확인 |
| `RefreshHit` | 사본이 만료되어 오리진과 재검증됨 | `age`가 0 근처부터 다시 시작할 것으로 예상 |
| POP은 같은데 `via` 서버 식별자가 바뀜 | 같은 POP의 다른 서버가 응답했고 캐시 객체는 여전히 찾음 | 고칠 것 없음 |

**과제:**

1. 두 요청을 보내고 각각의 `x-amz-cf-pop`, `x-cache`, `age`, `date`, `cache-control`을 기록합니다.
2. `date` + `age`를 계산해 자신의 시계와 비교하고 차이를 설명합니다.
3. `cache-control`에서 공유 캐시가 사본을 신선하다고 볼 수 있는 시간과, CDN이 쓸 값(`s-maxage` 또는 `max-age`)을 적습니다. 배포의 최소·최대 TTL이 무엇을 바꿀 수 있는지 6절의 표를 인용해 적습니다.
4. 첫 요청부터 Hit였다면 이유를 설명합니다. 캐시 무력화용 쿼리 문자열이 Miss를 확실히 만들지는 않습니다. 캐시 정책이 쿼리 문자열을 키에서 빼면(CloudFront 기본값) `?x=1`도 같은 객체에 적중합니다. 시도한다면 다른 사람의 사이트에는 그런 요청을 한 번만 보내고, 결과를 캐시 키로 설명합니다.
5. **설계 과제(desk check):** `/assets/*`(버전 이름), `/index.html`, `/api/*`가 있는 사이트의 캐시 동작 표를 씁니다. 캐시 키 구성, TTL, 오리진 요청 정책, 무효화 계획, 그리고 Origin Shield가 요청당 비용만큼 가치가 있는지를 적습니다. 이어서 9절을 따라 오리진 경로를 그리고 보안 그룹 규칙을 적습니다.

**검토 기준:**

- 모든 결론이 헤더 하나와 4–6절 또는 10절의 규칙 하나를 인용합니다.
- POP 코드를 비교하기 전에 두 번째 Miss를 "캐시가 고장 났다"고 보고하지 않습니다.
- 설계 과제에 인터넷용 로드 밸런서가 없고, 어떤 인바운드 규칙에도 공개 CIDR이 없으며, `/api/*`는 아무것도 캐시하지 않거나 응답을 바꾸는 모든 값을 캐시 키에 넣었습니다.

## 12. 장애와 복구를 관찰하는 방법

이 표는 **어떤 증거가 각 판정을 확정하는지** 정하는 연습입니다. 나중에 승인된 기존 환경에서 시나리오를 재현하게 되면 이 증거를 모읍니다.

| 장애 | 예상 동작 | 증거 | 그 증거만으로는 확인되지 않는 것 |
|---|---|---|---|
| 오리진 다운, 객체는 아직 신선 | 적중은 계속되고 미스는 실패 | `age`가 커지는 `x-cache: Hit`, 로그의 미스 `Error` | 모든 객체가 캐시되어 있다는 것 |
| 오리진 다운, 객체는 오래됨, `stale-if-error` 설정 | 지시어 값과 최대 TTL 중 작은 값까지 오래된 사본 제공 | `max-age`를 넘긴 `age`, 로그의 오리진 오류 | 장애가 얼마나 이어졌는지 |
| 오리진 다운, 최소 TTL > 0이고 `no-cache` | 예전에 받은 사본이 나갈 수 있음(6절 함정) | 오류를 예상한 곳에서 나온 응답 | 그 콘텐츠에 이 동작이 허용되는지 |
| 캐시 키가 커짐(헤더나 쿠키 추가) | 적중률이 떨어지고 오리진 지연과 부하가 오름 | CloudWatch 캐시 적중률, 오리진 요청 수 | 어떤 값이 키를 쪼갰는지(정책 비교) |
| 오리진 인증서 불일치·만료 | 미스에서 뷰어에게 `502` | 뷰어 `502`, 오리진 TLS 오류 | 적중이 영향을 받았는지(받지 않음) |
| 보안 그룹 변경으로 CloudFront 원본이 빠짐 | 미스는 연결 실패, 적중은 계속 | 미스의 `502`/`504`, 보안 그룹 규칙 변경 이력 | internal ALB가 인터넷에서 닿게 되었다는 것(공인 주소가 없으므로 닿지 않음) |
| 잘못된 배포를 무효화로 수정 | 엣지는 다시 가져오지만 브라우저·프록시는 예전 사본을 가질 수 있음 | 무효화 상태, `x-cache: Miss` 다음 `Hit` | 사용자 브라우저가 갱신되었다는 것(버전 이름만 보장) |

**복구는 부하 사건입니다.** 무효화나 오리진 장애 뒤에는 여러 POP이 한꺼번에 미스를 냅니다. 리전 엣지 캐시, Origin Shield, 요청 병합이 오리진 요청 수를 줄이지만, 캐시를 다시 채우는 동안의 오리진 용량을 계획합니다. 관찰된 오류 0은 그 샘플링이 오류를 포착하지 못했다는 뜻일 뿐입니다.

## 13. 산출물과 완료 기준

| 산출물 | 완료 조건 |
|---|---|
| 경로 그림 | 뷰어, POP, 리전 엣지 캐시, (쓴다면) Origin Shield, 오리진을 그리고 캐시 계층과 연결 구간을 구분했으며, 리전 엣지 캐시를 건너뛰는 요청을 표시함 |
| 헤더 관찰 | 두 요청의 POP, `x-cache`, `age`, `date`, `cache-control`을 기록하고 결론마다 규칙을 연결함 |
| 캐시 동작 표 | 경로별 캐시 키, TTL, 오리진 요청 정책, 무효화 또는 버전 계획과 Origin Shield 결정의 근거 |
| 오리진 경로와 규칙 | internal ALB로 가는 VPC 오리진, 보안 그룹 규칙의 원본(서비스 그룹 또는 prefix list), 구간별 TLS 표 |
| 장애 표 | 행마다 예상 동작, 증거, 그 증거의 한계 |

요청이 POP으로 유도되는 방식, 어느 계층이 왜 응답하는지, 캐시 키와 TTL 규칙이 적중률을 정하는 방식, 무효화와 버전 이름의 차이, 오리진이 CloudFront를 통해서만 닿는 이유를 근거 문서와 함께 설명할 수 있으면 완료입니다. 같은 경로의 공격 쪽은 다음 워크북(엣지 보안)에서 이어 가고, WAF 배치는 [WAF·엣지·API 보안](../../security/14-waf-edge-api-security.md)에서 검토한 뒤 [퀴즈](../../quizzes/networking/expert/08-cdn-edge-delivery-quiz.md)를 풉니다.

## 참고 자료

Amazon CloudFront 개발자 안내서

- [What is Amazon CloudFront?](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html) (최저 지연 라우팅, AWS 네트워크)
- [How CloudFront delivers content](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/HowCloudFrontWorks.html) (DNS의 POP 유도, 리전 엣지 캐시, 이를 건너뛰는 요청)
- [Use Amazon CloudFront Origin Shield](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/origin-shield.html) (우회, 리전, 과금 기준, `OriginShieldHit`)
- [Understand the cache key](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html), [Control origin requests with a policy](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/controlling-origin-requests.html)
- [Manage how long content stays in the cache (expiration)](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Expiration.html) (TTL 표, `stale-while-revalidate`, `stale-if-error`, 최소 TTL 경고)
- [Invalidate files to remove content](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html), [Pay for file invalidation](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/PayingForInvalidation.html)
- [Quotas](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cloudfront-limits.html) (무효화 속도, VPC 오리진, 오리진 액세스 제어)
- [Request and response behavior for custom origins](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/RequestAndResponseBehaviorCustomOrigin.html) (오리진 HTTP/1.1, 지속 연결, 요청 병합, `Via`, 오리진 프로토콜)
- [Distribution settings reference](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/DownloadDistValuesGeneral.html) (지원 HTTP 버전, HTTP/2·HTTP/3 요건)
- [Require HTTPS between CloudFront and your custom origin](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-https-cloudfront-to-custom-origin.html) (오리진 프로토콜 정책, 오리진 인증서 이름)
- [Restrict access to an Amazon S3 origin](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html) (OAC)
- [Restrict access with VPC origins](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html) (요건, 보안 그룹, 제약)
- [Locations and IP address ranges of CloudFront edge servers](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/LocationsOfEdgeServers.html) (관리형 prefix list)
- [Request Anycast static IPs](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/request-static-ips.html)
- [View CloudFront and edge function metrics](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/viewing-cloudfront-metrics.html) (캐시 적중률, 오리진 지연), [Standard log file fields](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/standard-logs-reference.html)
- [Restrict access to Application Load Balancers](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/restrict-access-to-load-balancer.html) (ALB 인증서 리전과 us-east-1 뷰어 인증서)

그 밖의 AWS 자료

- [How Elastic Load Balancing works](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/how-elastic-load-balancing-works.html) (internal 로드 밸런서 스킴)
- [AWS 지식 센터: X-Cache: Miss from CloudFront](https://repost.aws/knowledge-center/cloudfront-x-cachemiss-error), [사용자 지정 객체 캐싱과 오리진 헤더](https://repost.aws/knowledge-center/cloudfront-custom-object-caching) (`x-cache` 값, `x-amz-cf-pop`)
- [AWS 지식 센터: 미국 동부(버지니아 북부) 인증서 연결](https://repost.aws/knowledge-center/migrate-ssl-cert-us-east)
- [Amazon CloudFront FAQs](https://aws.amazon.com/cloudfront/faqs/) (예전 동시 무효화 한도), [Amazon CloudFront pricing](https://aws.amazon.com/cloudfront/pricing/)
- [AWS Networking 블로그: CloudFront VPC Origins 위의 비공개 AI 에이전트](https://aws.amazon.com/blogs/networking-and-content-delivery/private-ai-agent-with-websocket-streaming-over-cloudfront-vpc-origins-and-the-next-generation-of-opensearch-serverless-for-knowledge-retrieval/) (ARN 기반 VPC 오리진 라우팅, 오리진 인증서)
- [AWS Networking 블로그: CloudFront 관리형 prefix list](https://aws.amazon.com/blogs/networking-and-content-delivery/limit-access-to-your-origins-using-the-aws-managed-prefix-list-for-amazon-cloudfront/) (규칙 가중치 55)

표준

- [RFC 9111: HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111.html) (캐시 키, 신선도, `Age`, `no-cache`, `s-maxage`)
- [RFC 5861: HTTP Cache-Control Extensions for Stale Content](https://www.rfc-editor.org/rfc/rfc5861.html)
- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) (`Via`)
- [RFC 4786: Operation of Anycast Services](https://www.rfc-editor.org/rfc/rfc4786.html), [RFC 7871: Client Subnet in DNS Queries](https://www.rfc-editor.org/rfc/rfc7871.html)
- [RFC 1918](https://www.rfc-editor.org/rfc/rfc1918.html) (예시 주소)

시험 범위 (목차를 정하는 데만 사용)

- [AWS Certified Advanced Networking - Specialty (ANS-C01) 시험 안내](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01.html)

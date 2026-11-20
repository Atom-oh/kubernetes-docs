# 08. CDN과 엣지 전송 설계 퀴즈

> **마지막 업데이트**: 2026년 11월 19일

[워크북](../../../networking/expert/08-cdn-edge-delivery.md)으로 돌아갑니다.
문항마다 답 하나를 고르고 워크북의 어떤 규칙이 답을 뒷받침하는지 설명합니다.
설계 추론 문제이며 실제 배포를 구성했다는 주장이 아닙니다.

1. POP에서 미스가 났습니다. 다음 중 POP이 리전 엣지 캐시에 묻지 않고 **오리진으로 바로** 보내는 요청은?
   - A) 한 번도 요청된 적 없는 이미지에 대한 `GET`
   - B) API 경로로 가는 `POST`
   - C) TTL이 만료된, 캐시된 스타일시트에 대한 `HEAD`

<details>
<summary>정답 보기</summary>

**정답: B) API 경로로 가는 `POST`**

**설명:** 프록시 HTTP 메서드(`PUT`, `POST`, `PATCH`, `OPTIONS`, `DELETE`)는 리전 엣지 캐시를 거치지 않고 POP에서 오리진으로 바로 갑니다. 동적 요청과, 최적 리전 엣지 캐시와 같은 리전에 있는 S3 오리진도 건너뜁니다. 처음 요청되는 `GET`은 리전 엣지 캐시가 존재하는 이유 그 자체입니다.

</details>

2. 배포가 기본 캐시 키를 씁니다. 두 뷰어가 쿼리 문자열, `User-Agent`, `session_id` 쿠키가 서로 다른 채로 `/content/stories/example-story.html`을 요청합니다. 두 번째 요청은?
   - A) 적중입니다. 기본 키에는 배포 도메인 이름과 URL 경로만 들어가기 때문입니다.
   - B) 미스입니다. 쿼리 문자열이 다르기 때문입니다.
   - C) 미스입니다. 쿠키는 항상 캐시 키에 들어가기 때문입니다.

<details>
<summary>정답 보기</summary>

**정답: A) 적중입니다. 기본 키에는 배포 도메인 이름과 URL 경로만 들어가기 때문입니다.**

**설명:** 쿼리 문자열, 헤더, 쿠키는 기본 캐시 키에 없습니다. 캐시 정책은 응답을 바꾸는 값만 키에 더하고, 오리진 요청 정책은 캐시를 쪼개지 않고 값을 오리진에 전달합니다.

</details>

3. 오리진이 `Cache-Control: max-age=600, s-maxage=86400`을 보냅니다. 캐시 정책은 최소 TTL 0, 최대 TTL 3600입니다. CloudFront와 브라우저는 각각 얼마나 캐시하나요?
   - A) CloudFront 600초, 브라우저 86,400초
   - B) CloudFront 86,400초, 브라우저 600초
   - C) CloudFront 3,600초, 브라우저 600초

<details>
<summary>정답 보기</summary>

**정답: C) CloudFront 3,600초, 브라우저 600초**

**설명:** 두 지시어가 모두 있고 최소 TTL이 0이면 CloudFront는 `s-maxage`와 최대 TTL 중 작은 값만큼 캐시하고, 브라우저는 `max-age`를 씁니다. RFC 9111은 공유 캐시에서 `s-maxage`를 우선하지만, 배포의 최대 TTL이 여전히 상한입니다.

</details>

4. 캐시 정책의 최소 TTL이 300초이고, 오리진은 계정 페이지에 `Cache-Control: no-cache`를 보냅니다. CloudFront의 동작과, 오리진에 닿지 않을 때 예전 사본이 나가는 것을 막는 방법은?
   - A) CloudFront는 `no-cache` 응답을 절대 캐시하지 않으므로 바꿀 것이 없습니다.
   - B) `no-cache`가 있어도 최소 TTL만큼 캐시하며, 오리진에 닿지 않으면 예전 사본을 내줄 수 있습니다. `Cache-Control: stale-if-error=0`을 붙이면 막을 수 있습니다.
   - C) 기본 TTL인 24시간 동안 캐시합니다.

<details>
<summary>정답 보기</summary>

**정답: B) `no-cache`가 있어도 최소 TTL만큼 캐시하며, 오리진에 닿지 않으면 예전 사본을 내줄 수 있습니다. `Cache-Control: stale-if-error=0`을 붙이면 막을 수 있습니다.**

**설명:** 개발자 안내서는 최소 TTL이 0보다 크면 `no-cache`, `no-store`, `private`보다 최소 TTL이 우선한다고 경고합니다. 다시 쓰면 안 되는 콘텐츠는 그 동작의 최소 TTL을 0으로 두거나, 적어도 `stale-if-error=0`을 붙입니다.

</details>

5. 오리진이 `Cache-Control: max-age=3600, stale-while-revalidate=600`을 보냅니다. 객체가 캐시된 지 65분 뒤의 요청은 어떻게 되나요?
   - A) CloudFront가 오래된 사본을 바로 내주고 백그라운드에서 오리진으로부터 새 사본을 가져옵니다.
   - B) CloudFront가 오리진의 새 사본이 올 때까지 뷰어를 기다리게 합니다.
   - C) 객체가 오래되었으므로 CloudFront가 `504`를 돌려줍니다.

<details>
<summary>정답 보기</summary>

**정답: A) CloudFront가 오래된 사본을 바로 내주고 백그라운드에서 오리진으로부터 새 사본을 가져옵니다.**

**설명:** 한 시간의 수명이 지나면 `stale-while-revalidate=600`에 따라 CloudFront는 비동기로 재검증하는 동안 최대 10분 동안 오래된 사본을 내줍니다(RFC 5861). 오래된 사본은 지시어 값과 최대 TTL 중 작은 값까지만 쓰입니다.

</details>

6. 잘못된 배포 뒤 `/app.js`를 무효화했지만, 회사 프록시 뒤의 일부 사용자는 여전히 예전 파일을 받습니다. 다음에는 무엇으로 막나요?
   - A) `/app.js` 대신 `/*`를 무효화합니다.
   - B) 최소 TTL을 0으로 낮춥니다.
   - C) 버전 이름(예: `app.3f9c.js`)을 쓰고 그 파일을 참조하는 페이지를 갱신합니다.

<details>
<summary>정답 보기</summary>

**정답: C) 버전 이름(예: `app.3f9c.js`)을 쓰고 그 파일을 참조하는 페이지를 갱신합니다.**

**설명:** 무효화는 POP과 리전 엣지 캐시에서만 객체를 지우며, 브라우저와 회사 프록시 캐시는 그곳에서 만료될 때까지 예전 사본을 유지합니다. 새 이름은 모든 캐시에게 새 캐시 키입니다. 버전 이름은 무효화 요금도 없어 더 저렴하며, `/*` 경로도 무효화 경로 하나로 과금됩니다.

</details>

7. 같은 파일에 `curl -sI`를 두 번 보냈더니 둘 다 `x-cache: Miss from cloudfront`이고 `x-amz-cf-pop`이 서로 다릅니다. 가장 그럴듯한 설명은?
   - A) 두 요청이 서로 다른 POP에 도착했고, 엣지 로케이션은 자신이 받은 객체만 캐시합니다.
   - B) 배포의 캐시가 고장 났습니다.
   - C) `HEAD` 요청은 절대 캐시되지 않습니다.

<details>
<summary>정답 보기</summary>

**정답: A) 두 요청이 서로 다른 POP에 도착했고, 엣지 로케이션은 자신이 받은 객체만 캐시합니다.**

**설명:** DNS 방식이든 Anycast든 연속된 요청이 같은 POP에 닿는다고 보장하지 않습니다. 결론을 내리기 전에 `x-amz-cf-pop`을 비교하며, 지식 센터가 드는 다른 원인은 밀려남, 캐시 키 구성, 오리진의 `Cache-Control`입니다.

</details>

8. 응답에 `x-cache: Hit from cloudfront`, `date: Thu, 19 Nov 2026 09:00:00 GMT`, `age: 7200`이 있습니다. 무엇을 알 수 있나요?
   - A) 오리진이 이 응답을 두 시간 전에 만들었고 엣지가 저장된 사본을 내주었습니다. `date`에 `age`를 더하면 대략 현재 시각인 11:00 GMT입니다.
   - B) 이번 요청에서 오리진에 연결했고 응답에 7,200 ms가 걸렸습니다.
   - C) 객체가 7,200초 뒤에 만료됩니다.

<details>
<summary>정답 보기</summary>

**정답: A) 오리진이 이 응답을 두 시간 전에 만들었고 엣지가 저장된 사본을 내주었습니다. `date`에 `age`를 더하면 대략 현재 시각인 11:00 GMT입니다.**

**설명:** RFC 9111은 `Age`를 응답이 오리진에서 생성되거나 검증된 뒤 지난 초로 정의하며, 이 헤더가 있으면 이번 요청에 대해 오리진이 응답을 만들지 않았다는 뜻입니다. 남은 신선도는 `Age` 자체가 아니라 (TTL 설정 범위 안의 `s-maxage` 또는 `max-age`로 정한) 수명에서 `Age`를 뺀 값입니다.

</details>

9. internal ALB가 CloudFront VPC 오리진입니다. 개발자 안내서가 제시하는 인바운드 보안 그룹 원본 중 **가장 제한적인** 것은?
   - A) CloudFront 관리형 prefix list `com.amazonaws.global.cloudfront.origin-facing`
   - B) 서비스 관리형 보안 그룹 `CloudFront-VPCOrigins-Service-SG`
   - C) VPC CIDR

<details>
<summary>정답 보기</summary>

**정답: B) 서비스 관리형 보안 그룹 `CloudFront-VPCOrigins-Service-SG`**

**설명:** 관리형 prefix list는 모든 CloudFront origin-facing 서버를 담으므로 어느 배포든 허용하고, VPC 오리진 서비스 그룹은 자신의 배포로만 제한하며 VPC 오리진을 만든 뒤에야 생깁니다. 이 그룹은 수정하지 않고 같은 이름 접두사로 그룹을 만들지 않습니다. VPC CIDR은 CloudFront 원본이 아닙니다.

</details>

10. 인터넷 클라이언트가 internal ALB의 DNS 이름을 조회한 뒤 접속하려 합니다. 보안 그룹 규칙이 평가되기도 전에 실패하는 이유는?
   - A) internal 로드 밸런서의 DNS 이름은 VPC 밖에서 조회되지 않습니다.
   - B) internal 로드 밸런서의 노드는 프라이빗 IP 주소만 가지므로 인터넷에서 그곳으로 가는 경로가 없습니다. 이름은 공개적으로 조회되지만 그 프라이빗 주소로 풀립니다.
   - C) CloudFront가 그 클라이언트를 차단합니다.

<details>
<summary>정답 보기</summary>

**정답: B) internal 로드 밸런서의 노드는 프라이빗 IP 주소만 가지므로 인터넷에서 그곳으로 가는 경로가 없습니다. 이름은 공개적으로 조회되지만 그 프라이빗 주소로 풀립니다.**

**설명:** ELB 안내서는 internal 로드 밸런서의 DNS 이름이 노드의 프라이빗 IP로 공개 조회되므로 VPC에 접근할 수 있는 클라이언트만 닿는다고 설명합니다. 라우팅의 성질이므로 나중에 보안 그룹 규칙이 느슨해져도 유지됩니다. 이 클라이언트의 경로에는 CloudFront가 아예 없습니다.

</details>

11. 검토자가 VPC 오리진 뒤의 VPC에 인터넷 게이트웨이가 연결되어 있다고 문제를 제기합니다. 올바른 설명은?
   - A) 인터넷 게이트웨이는 필수입니다. VPC가 인터넷 트래픽을 받을 수 있음을 나타낼 뿐 오리진으로 가는 라우팅에는 쓰이지 않으며, 라우트 테이블을 바꿀 필요도 없습니다.
   - B) 인터넷 게이트웨이가 있으므로 오리진 서브넷이 퍼블릭이 되어야 합니다.
   - C) VPC 오리진이 동작하려면 인터넷 게이트웨이를 제거해야 합니다.

<details>
<summary>정답 보기</summary>

**정답: A) 인터넷 게이트웨이는 필수입니다. VPC가 인터넷 트래픽을 받을 수 있음을 나타낼 뿐 오리진으로 가는 라우팅에는 쓰이지 않으며, 라우트 테이블을 바꿀 필요도 없습니다.**

**설명:** CloudFront는 프라이빗 서브넷의 서비스 관리형 ENI를 통해 오리진에 닿습니다. 오리진은 공인 주소 없이 프라이빗 서브넷에 남고, 인터넷 게이트웨이는 VPC 수준의 전제 조건일 뿐입니다.

</details>

12. Origin Shield를 켰습니다. 표준 로그에서 POP이나 리전 캐시가 아니라 Origin Shield가 응답했음을 보여 주는 필드와 값은?
   - A) `x-edge-result-type` = `RefreshHit`
   - B) `x-edge-detailed-result-type` = `OriginShieldHit`
   - C) `x-edge-result-type` = `Miss`

<details>
<summary>정답 보기</summary>

**정답: B) `x-edge-detailed-result-type` = `OriginShieldHit`**

**설명:** `x-edge-detailed-result-type`은 Origin Shield 적중 같은 경우를 빼면 `x-edge-result-type`과 같은 값을 담습니다. Origin Shield 역할을 하는 리전 엣지 캐시로 라우팅된 요청은 `OriginShieldHit`가 아니라 `Hit`로 기록됩니다.

</details>

완료 기준: 모든 답을 워크북의 규칙으로 설명하고, 헤더 관찰 기록을 첨부하거나 **설계 검토**로 표시합니다.

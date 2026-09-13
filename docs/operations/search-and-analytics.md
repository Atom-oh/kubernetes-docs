# 검색 노출과 방문자 집계 운영

운영 방식 갱신일: 2026-09-12. 아래 검색 노출 점검 결과는 2026-09-10 기준입니다.
공개 사이트는 `https://www.atomai.click/kubernetes-docs/`,
GA4 측정 ID는 `G-GWVLEW5JLL`입니다. 방문자 수는 **atom - GA4 속성 `396631876`의
관리자 보고서에서 확인**합니다. 사이트 내 통계 표시와 GA4 Data API 조회는 사용하지 않으므로
별도 Google Cloud 프로젝트·서비스 계정 연결이 필요하지 않습니다.
이 문서는 저장소 운영자를 위한 안내이며
VitePress 공개 페이지에는 포함되지 않습니다.

## 확인한 설정

| 항목 | 확인 결과 |
|---|---|
| 크롤링 | 원점 `/robots.txt`가 HTTP 200과 `User-agent: * / Allow: /`를 반환 |
| 사이트맵 | `/kubernetes-docs/sitemap.xml`이 HTTP 200을 반환. 점검 당시 공개 버전에는 1,162개 URL이 있음 |
| 원점 사이트맵 | `/sitemap.xml`의 11개 URL 중 가이드북 홈은 있으나 가이드북 하위 사이트맵을 등록한 sitemap index는 아님 |
| 본문 | HTML에 본문과 내부 링크가 렌더링돼 있어 JavaScript 실행 없이도 읽을 수 있음 |
| 페이지 정보 | 문서별 title/description, canonical, ko/en/x-default 대체 언어, Open Graph, TechArticle/BreadcrumbList 제공 |
| 페이지 이동 | canonical·대체 언어·공유 정보·구조화 데이터·Markdown 원문 링크가 현재 문서에 맞춰 갱신되도록 보완 |
| 중복·내부 자료 | 독립 다이어그램 뷰어는 noindex. 내부 `assets/` 관리용 Markdown은 페이지와 사이트맵에서 제외 |
| LLM 수집 | `llms.txt`, 문서별 Markdown, 변경 해시를 가진 manifest, 로컬 MCP 검색·조회 제공 |
| 방문 집계 | 공개 사이트에서 GA4 태그 로드와 초기 `page_view` 요청 생성을 확인. 검사 요청은 전송 전에 차단했으므로 GA 서버 수신 확인과는 구분 |

사이트맵에 들어간 URL 수는 **검색엔진에 색인된 페이지 수가 아닙니다**.
올바른 기술 설정만으로 검색 순위·색인·방문량이 보장되지는 않습니다.
실제 색인/검색 노출은 Search Console, 실제 방문 수치는 GA4 권한으로 확인합니다.
소스 코드의 측정 ID만으로 비공개 방문자 통계를 조회할 수는 없습니다.

## Search Console에서 검색 노출 확인

1. [Google Search Console](https://search.google.com/search-console)에 접속해
   `atomai.click` 도메인 속성 또는
   `https://www.atomai.click/kubernetes-docs/` URL 접두어 속성을 선택합니다.
   속성이 없다면 Google이 안내하는 소유권 확인을 먼저 진행합니다.
2. **사이트맵**에 아래 주소를 제출합니다. 기존에 제출했는지는 계정에서 확인해야 합니다.

   ```text
   https://www.atomai.click/kubernetes-docs/sitemap.xml
   ```

3. **페이지 색인 생성**에서 색인됨/제외됨과 사유를 확인합니다. canonical 선택,
   중복, 크롤링됐지만 색인되지 않음, 404를 따로 봅니다. 이전 내부 관리 페이지가
   404로 바뀌는 것은 의도한 제거이며, 실제 본문 404와 구분합니다.
4. **URL 검사**로 한국어·영어 대표 문서 하나씩 확인합니다. Google이 선택한
   canonical이 해당 언어의 공개 문서 URL인지, 렌더링된 본문을 읽을 수 있는지 봅니다.
5. **실적 → 검색 결과**에서 페이지 URL에 `/kubernetes-docs/`가 포함되는 필터를
   적용하고 클릭수·노출수·CTR·평균 게재순위를 확인합니다.
6. 원점 사이트를 관리할 수 있다면 원점 `/robots.txt`에 다음 줄을 추가하는 것도
   발견 경로를 보강합니다. 이 저장소의 `public/robots.txt`는 하위 경로에 배포되므로
   원점 robots 정책을 바꾸는 방법이 아닙니다.

   ```text
   Sitemap: https://www.atomai.click/kubernetes-docs/sitemap.xml
   ```

대규모 URL을 수동으로 하나씩 색인 요청하기보다 사이트맵 제출, 실제 갱신일,
내용이 있는 문서 간 링크를 유지합니다. 이 작업은 원점 저장소나 Search Console
계정 설정을 자동으로 변경하지 않습니다.

## GA4에서 방문자 수 확인

1. [Google Analytics](https://analytics.google.com/)에 로그인합니다.
2. **atom - GA4 (`396631876`)** 속성을 선택하고 **관리 → 데이터 스트림 → 웹 스트림**에서
   측정 ID `G-GWVLEW5JLL`을 확인합니다. `G-...` 측정 ID와 숫자 속성 ID는 서로 다릅니다.
3. **보고서 → 실시간**에서 최근 5분/30분의 활성 사용자와 유입을 확인합니다.
   표준 보고서와 신규 이벤트 목록에는 처리 지연이 있을 수 있습니다.
4. 기간별 가이드북 통계는 **탐색 → 자유 형식**에서 다음과 같이 구성합니다.

   | 설정 | 값 |
   |---|---|
   | 측정기준 | 호스트 이름, 페이지 경로 + 쿼리 문자열, 이벤트 이름, 날짜 |
   | 필터 | 호스트 이름 = `www.atomai.click`; 페이지 경로가 `/kubernetes-docs/`로 시작 |
   | 방문자 | 총 사용자, 활성 사용자 |
   | 방문 횟수 | 세션 |
   | 기본 조회수 | 조회수 (`page_view` 기반) |
   | 문서 조회 | 이벤트 이름 = `docs_page_view`로 필터한 이벤트 수 |

같은 GA4 속성에서 다른 사이트도 측정할 수 있으므로 가이드북 경로 필터를
적용합니다. 조회수나 이벤트 수를 고유 방문자 수로 해석하지 않습니다.

### 문서 전용 이벤트

기본 GA4 `page_view` 및 자동 히스토리 추적 설정은 유지합니다.
VitePress는 최초 표시와 문서 이동 후 `docs_page_view`를 별도로 보냅니다.
이벤트에는 새 문서의 `page_location`, `page_path`, `page_title`과 직전 문서의
`page_referrer`가 들어갑니다. 같은 문서의 목차 앵커 이동이나 중복 렌더링은
문서 조회에 추가하지 않습니다.

`docs_page_view`를 `page_view`로 이름 변경하거나, 동일한 문서 이동을 보내는
GTM 태그를 추가하면 조회가 중복될 수 있습니다. 문서 전용 집계는 이벤트 이름을
그대로 사용합니다. 일반 페이지뷰와 문서 이벤트를 합산해서 조회수를 만들지 않습니다.
GA4의 사용자 식별·광고 차단·동의 상태에 따라 관측 가능한 방문 범위는 달라집니다.

배포 후 직접 가이드북을 열어 문서 A → B → 목차 앵커 이동을 해 보고,
GA4 실시간 또는 DebugView에서 문서 이벤트가 A/B에 각각 한 번만 보이는지 확인합니다.
브라우저 요청 생성 검사와 비공개 GA4 보고서의 수신 확인은 별도 단계입니다.

## 운영 루틴

- 배포 후: 사이트맵과 대표 한영 문서 HTTP 응답, 메타데이터, GA4 수신을 확인합니다.
- 매주: Search Console의 노출은 높지만 CTR이 낮은 문서와 색인 제외 사유를 확인합니다.
- 매월: GA4의 가이드북 경로별 방문자·문서 조회·유입 경로를 같은 기간 기준으로 비교합니다.

## 공식 참고 문서

- [Google 검색엔진 최적화 기본 가이드](https://developers.google.com/search/docs/fundamentals/seo-starter-guide)
- [사이트맵 만들기 및 제출](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)
- [Search Console 실적 보고서](https://support.google.com/webmasters/answer/7576553)
- [GA4 실시간 보고서](https://support.google.com/analytics/answer/9271392)
- [SPA 측정](https://developers.google.com/analytics/devguides/collection/ga4/single-page-applications)

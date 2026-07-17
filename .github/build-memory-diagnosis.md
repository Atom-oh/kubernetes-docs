# VitePress 빌드 메모리 폭증 진단 (2026-07-16)

## 요약 (TL;DR)

- **범인은 검색도 mermaid도 아니라 페이지 볼륨 자체다.** VitePress(Vite/Rollup)가 2,472개 페이지 모듈 전체를 한 프로세스 메모리에 보유하며, 실측 스케일링은 **피크 RSS ≈ 2.7GB + 페이지당 ~10MB (거의 선형)**. 2,472페이지 외삽값 ~27GB는 실제 26Gi 파드 OOM 이력과 일치한다.
- "비선형 폭증"으로 보인 것은 알고리즘적 비선형이 아니라 **(언어 수 × 페이지 수)의 곱셈 성장 + heap cap 근처 V8 GC 스래싱**이다. 언어가 2→5개가 되며 페이지가 배로 늘었고, cap 근처에서는 GC가 메모리를 거의 회수하지 못해 벽시계 시간과 요구 메모리가 함께 튄다.
- **처방: 로케일별 분리 빌드 + dist 병합.** 5개 언어를 순차 빌드하면 **피크 7.9GB**(단일 빌드 대비 –70%+)로 전 사이트가 빌드되며, 본 브랜치에서 end-to-end로 실증 완료(자산 충돌 0, hashmap/sitemap 병합 검증). 언어가 더 늘어도 피크는 "가장 큰 단일 로케일" 기준으로 고정된다.
- 검색(MiniSearch)은 부차 요인(537페이지 기준 +1.1GB, 선형 증가 — 전체 기준 ~+5GB). 분리 빌드 후에도 아끼고 싶으면 Pagefind 전환이 유효하나 필수는 아니다.
- Rspress/Docusaurus 이주는 **현 시점 불필요.**

## 측정 환경·방법

- 컨테이너: 16GB RAM / 4 vCPU / Node v22.22.2 / vitepress 1.6.4 (프로덕션 러너는 52Gi 파드, `--max-old-space-size=43008`)
- 방법: `NODE_OPTIONS=--max-old-space-size=12288`, 각 런 전 `.vitepress/dist`·`.vitepress/cache` 삭제, `/usr/bin/time -v`의 Maximum resident set size 기록. 환경 한계(16GB)에 근접한 런은 시스템 OOM 보호를 위해 RSS ~14GB에서 SIGTERM으로 중단하고 그 시점의 VmHWM을 기록.
- 토글: `.vitepress/config.ts`의 `VP_DISABLE_SEARCH` / `VP_DISABLE_MERMAID` / `VP_LOCALES` (이 브랜치에서 추가, 기본값은 기존 동작과 동일)

## 측정 결과

페이지 수: ko 537 / en 538 / cn 465 / jp 466 / es 466 = **2,472** (마크다운 원문 169MB, 페이지 평균 ~68KB, mermaid 펜스 4,147개/977파일)

| # | 구성 | 페이지 | 피크 RSS | 경과 | 결과 |
|---|------|--------|----------|------|------|
| A | 현재 설정 그대로 (5개 언어) | 2,472 | **14.1GB에서 중단** (상승 중) | 14m09s | 미완료 — 12GB heap cap 초과, 변환 단계에서 폭증 |
| B | A − mermaid 플러그인 | 2,472 | **14.2GB에서 중단** (상승 중) | 11m43s | 미완료 — A와 동일 궤적 |
| C | B − 로컬 검색 | 2,472 | **14.1GB에서 중단** (상승 중) | 9m48s | 미완료 — A/B와 동일 궤적 |
| D1 | ko만, 현재 설정 | 537 | **8.0GB** | 3m56s | ✅ 완주 |
| D1b | ko만, 검색 OFF | 537 | **6.9GB** | 2m26s | ✅ 완주 |
| D2 | ko+en, 현재 설정 | 1,075 | **13.2GB** | 10m18s | ✅ 완주 |

분리 빌드 실증 (현재 설정 그대로, 언어 메뉴 5개 유지):

| 로케일 | 페이지 | 피크 RSS | 경과 |
|--------|--------|----------|------|
| ko | 537 | 7.9GB | 3m50s |
| en | 538 | 6.9GB | 3m46s |
| cn | 465 | 7.4GB | 3m19s |
| jp | 466 | 6.8GB | 3m28s |
| es | 466 | 6.9GB | 3m22s |
| **합계 (순차)** | 2,472 | **피크 7.9GB** | ~18m |

병합 검증: 동명이내용 자산 충돌 **0건**(Vite 콘텐츠 해시), hashmap.json 합집합 2,468 페이지, sitemap.xml 합집합 2,472 URL, en 딥페이지 참조 자산 누락 0건.

## 판정 근거

1. **mermaid는 무죄.** A(14.1GB)와 B(14.2GB)가 오차 범위 내 동일. `vitepress-plugin-mermaid`는 애초에 **클라이언트 사이드 렌더링**이라 빌드 타임에는 코드펜스를 컴포넌트 자리로 치환만 하고, 4,147개 다이어그램의 렌더링 비용은 방문자 브라우저에서 발생한다. (사용자 질의의 "SSR→CSR 전환"은 이미 현재 상태.)
2. **검색은 부차 요인.** C(검색 OFF)도 A와 동일 지점에서 폭증. 완주 빌드로 분리하면 검색 기여분은 537페이지에 +1.1GB(D1−D1b), 페이지당 ~2MB 선형 → 전체 2,472페이지 기준 약 +5GB. 주범은 아니고, 분리 빌드 후에는 로케일당 ~1GB 수준이라 감내 가능.
3. **주범은 페이지 볼륨 × VitePress 파이프라인.** 세 완주점(537→8.0, 1,075→13.2)과 프로덕션 이력(2,291페이지 시절 26Gi OOM)이 한 직선 위에 있다: **RSS ≈ 2.7GB + 10MB/페이지**. Rollup이 client+server 두 번들의 전체 모듈 그래프(shiki 이중 테마 하이라이팅으로 팽창한 페이지 모듈 포함)를 빌드 내내 메모리에 들고 있는 구조적 특성이며, 설정 토글로는 제거 불가.
4. **10GB→64GB "비선형" 체감의 정체**: 페이지 수 자체가 언어 백필로 배 이상 늘었고(곱셈 성장), heap cap 근처에서는 V8이 mark-compact를 반복하며 시간이 폭증해 "더 큰 파드 + 더 큰 cap"으로 대응하게 되는 악순환이 있었다. 43008MB cap을 주면 V8은 full GC를 미루고 cap까지 채우는 경향이 있어 관측 사용량도 cap을 따라 커진다.

## 권고

### 1순위 — 로케일별 분리 빌드 (이 브랜치에서 실증 완료)

`deploy.yml`의 빌드 스텝을 아래로 교체하면 **피크 메모리 ~8GB**로 떨어져 52Gi 파드가 필요 없어진다 (16Gi면 충분, `--max-old-space-size` 튜닝 불필요 수준):

```yaml
      - run: npm ci
      - run: |
          for l in ko en cn jp es; do
            rm -rf .vitepress/dist .vitepress/cache
            VP_LOCALES=$l npm run docs:build
            mv .vitepress/dist dist-$l
          done
          python3 scripts/merge-locale-dists.py .vitepress/dist dist-ko dist-en dist-cn dist-jp dist-es
```

- 언어 스위처는 부분 빌드에서도 5개 언어 전부 렌더링됨(이 브랜치의 config 수정으로 보장, 실측 확인).
- 병합은 `scripts/merge-locale-dists.py`가 처리: 로케일 트리 + 콘텐츠 해시 자산 복사, `hashmap.json`(SPA 네비게이션 청크맵)·`sitemap.xml` 합집합.
- 로컬 검색은 원래 로케일별 인덱스라 분리 빌드와 정합 — 각 언어 페이지는 자기 언어 인덱스만 로드한다.
- **확장성**: 언어가 늘어도 피크는 불변(빌드 시간만 +~4분/언어, 필요시 matrix 병렬화 가능). 단일 로케일이 ~1,300페이지가 되어야 피크 16GB에 닿는다(현재 최대 538).
- 트레이드오프: 총 빌드 시간 ~18분(순차) vs 현재 대형 파드에서의 단일 빌드. GC 스래싱이 없어 로케일당 시간은 안정적이며, spot 대형 인스턴스(r6g.2xlarge) 대신 소형 러너로 충분해 비용도 준다.

### 2순위 (선택) — 검색을 Pagefind로 전환

분리 빌드만으로 문제는 해소되지만, 검색을 빌드 파이프라인에서 완전히 떼내고 싶다면: `themeConfig.search` 제거 후 병합된 dist에 `npx pagefind --site .vitepress/dist` 1회 실행(빌드 후 정적 HTML 스캔이라 Node heap 무부담, 언어별 인덱스 자동 분리). UI는 `vitepress-plugin-pagefind` 또는 커스텀 컴포넌트. 부수 효과: 페이지별 검색 인덱스 청크(수십 MB)가 클라이언트 번들에서 빠진다.

### 이주(Rspress/Docusaurus)는 보류

- 분리 빌드로 피크가 8GB로 떨어지고 언어 증가에도 불변이므로 이주의 메모리 근거가 소멸.
- 이주 비용이 큼: mermaid/로컬검색/사이드바 자동생성(`summary.ts`)/GitBook 리라이트/테마 커스텀을 전부 재구축해야 하고 URL 구조 변동 위험(GitHub Pages SEO)이 있다.
- 재검토 트리거: **단일 로케일**이 ~1,200페이지를 넘거나, 순차 빌드 총 시간이 CI 한계를 넘을 때.

### mermaid 3안 비교 (참고 — 측정상 무죄이므로 빌드 메모리 목적으로는 불필요)

| 방안 | 빌드 메모리 | 비고 (4,147개 다이어그램 × 5개 언어, GitHub Pages 기준) |
|------|------------|------|
| 1. SSR→CSR 전환 | 효과 없음 | **이미 CSR** — vitepress-plugin-mermaid는 브라우저에서 렌더링. 전환할 SSR이 없음 |
| 2. mmdc 사전 SVG 생성 | 효과 없음 (빌드 메모리 기준) | 방문자 초기 렌더 성능은 개선(번들에서 mermaid ~1.5MB gzip 제거, FOUC 제거). 단 러너에 puppeteer/Chromium 필요, 4,147개 렌더 시간, 언어별 라벨 차이로 캐시 키 관리 필요 — 페이지 성능 과제로 별도 검토 권장 |
| 3. 로케일 분리 빌드 | **–70%+ (실측)** | 본 리포트의 1순위 권고. mermaid와 무관하게 실제 원인을 해소 |

참고: 이미지 라이트박스는 현 브랜치 코드에 존재하지 않음(테마는 DefaultTheme + custom.css, medium-zoom 등 미설치). 도입하더라도 클라이언트 사이드라 빌드 메모리와 무관.

## 재현 방법

```bash
npm ci
# 전체(현재 설정): 16GB 박스에서는 ~14GB에서 중단됨
NODE_OPTIONS=--max-old-space-size=12288 /usr/bin/time -v npx vitepress build
# 변인 제거
VP_DISABLE_MERMAID=1 /usr/bin/time -v npx vitepress build
VP_DISABLE_MERMAID=1 VP_DISABLE_SEARCH=1 /usr/bin/time -v npx vitepress build
# 로케일 스케일링
VP_LOCALES=ko /usr/bin/time -v npx vitepress build
VP_LOCALES=ko,en /usr/bin/time -v npx vitepress build
```

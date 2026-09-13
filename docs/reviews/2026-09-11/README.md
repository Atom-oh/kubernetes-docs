# 문서 전수 검토 기록

검토 기준일은 2026-09-13입니다. 한·영 원문 1,260개의 내용 검토 근거와 현재 main의 파일 해시를 대조했습니다. 최종 번역·배포 검증은 아래 기록과 해당 PR의 최신 상태를 함께 확인합니다.

| 범위 | 확인 결과 |
|---|---|
| 기본 한·영 문서 1,194개 | 문서별 완독 기록이 있으며, 현재 main과 일치하거나 검토한 후속 변경으로 연결됩니다. |
| 추가 문서 66개 | 독립 리뷰 커밋과 현재 파일 해시가 모두 일치합니다. |
| 전체 언어 2,795개 | 원문 외 번역본은 링크·이미지·Markdown 구조를 기계적으로 검사했습니다. 모든 번역 문장을 새로 의미 검토했다는 뜻은 아닙니다. |
| 기록된 위치 링크 검사 | 66,588건에서 대상 누락이 없었습니다. 해당 검사 커밋은 JSON 보고서에 고정되어 있습니다. |
| 기록된 로컬 이미지 검사 | 2,619개 이미지, 2,711개 참조를 확인했습니다. Raster는 전체 디코딩하고 SVG는 XML을 검사했습니다. |
| 실제 사이트 AI 원문 | 680개 Markdown의 해시와 바이트 크기가 공개 manifest와 모두 일치했습니다. |
| 실제 문서 화면 | 1920px 화면에서 본문 952px, 768px에서 704px, 375px에서 327px를 확인했습니다. 검사한 페이지에 가로 넘침이나 깨진 이미지는 없었습니다. |
| 검색·MCP | 도메인 루트 robots.txt에 문서 sitemap을 추가했습니다. 로컬 stdio MCP의 검색·인용·페이지 분할·허용 경로 검사도 통과했습니다. |

## 검증 근거

- [전체 검증 결과와 파일별 검토 연결](full-audit-verification.json)
- [추가 교육 문서의 독립 리뷰 근거](new-curricula-review-provenance.json)
- [기초 관측성·Hybrid Nodes·Gatekeeper 배포 검증](production-observability-foundation-hybrid-gatekeeper.json)
- [Grafana 배포 검증](production-grafana-validation.json)
- [로그·알림 개요 배포 검증](production-logging-alerting-overview-validation.json)
- [보안·관측성 배포 검증](production-security-observability-validation.json)
- [OnCall 배포 검증](production-oncall-validation.json)
- [CloudWatch·Dynatrace 배포 검증](production-cloudwatch-dynatrace-validation.json)

세부 내용 수정과 실행 범위는 각 주제의 `*-validation.json` 및 `batches/` 기록에 있습니다. 원문 내용 수정, 번역 동기화, 링크·앵커 보완, 실제 배포 확인을 구분해 기록합니다.

## 검증 범위의 한계

실제 AWS 계정·Kubernetes 클러스터·SaaS tenant에 예제 전체를 배포한 것은 아닙니다. 로컬에서 실행한 도구·스키마·프로토콜 검사와 실제 외부 실행을 구분했습니다. 접근을 거부하거나 네트워크가 차단된 외부 문서는 그 응답만으로 삭제된 문서라고 판정하지 않았습니다.

검색봇이 접근할 수 있고 sitemap·원문이 일관되게 제공되는지는 검증했지만, 모든 페이지가 이미 검색엔진 또는 모든 AI에 색인되었다고 보장하지는 않습니다. MCP는 체크아웃을 읽는 stdio 방식이며, 최신 내용을 사용하려면 체크아웃을 갱신하고 서버를 재시작해야 합니다.

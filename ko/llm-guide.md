# LLM과 함께 읽기 — llms.txt

> **마지막 업데이트**: 2026년 9월 2일

이 가이드북 전체는 [llms.txt 표준](https://llmstxt.org/)으로 제공됩니다. URL 하나만 넘기면 ChatGPT, Claude, 사내 RAG 파이프라인 등 어떤 LLM 도구에서든 이 가이드북을 지식 소스로 쓸 수 있습니다.

## 엔드포인트

| URL | 내용 | 용도 |
|-----|------|------|
| [llms.txt](https://www.atomai.click/kubernetes-docs/llms.txt) | 본문 문서 전체의 제목·URL 색인 (퀴즈·랩은 `## Optional`의 목록 페이지 링크로) | LLM이 필요한 페이지만 골라 읽게 할 때 |
| [llms-full-ko.txt](https://www.atomai.click/kubernetes-docs/llms-full-ko.txt) | 한국어 전체 본문 (마크다운) | 컨텍스트에 통째로 넣거나 RAG 인덱싱 |
| [llms-full-en.txt](https://www.atomai.click/kubernetes-docs/llms-full-en.txt) | 영어 전체 본문 (마크다운) | 영어 기반 도구/파이프라인 |

세 파일 모두 사이트가 배포될 때마다 자동으로 다시 생성되므로 항상 최신 콘텐츠와 일치합니다. 퀴즈는 `llms.txt`의 `## Optional` 절에 퀴즈 목록 페이지 링크(언어별 하나)로만 등장하고, 개별 퀴즈 페이지(정답 포함)는 색인과 full 파일 어디에도 들어가지 않습니다 — LLM 컨텍스트에 정답지를 섞지 않기 위해서입니다. 랩 가이드는 색인에서는 마찬가지로 목록 페이지 링크(언어별 하나)로만 나타나지만, full 파일에는 본문과 함께 포함됩니다.

## 활용 예시

**대화형 AI에게 특정 주제 질문하기** — 색인을 주고 필요한 페이지만 읽게 합니다:

```text
https://www.atomai.click/kubernetes-docs/llms.txt 를 읽고,
Istio ambient 모드의 mTLS 레이턴시 실측 결과가 있는 문서를 찾아
sidecar와 비교해서 요약해줘.
```

**Claude Code / 코딩 에이전트에서** — 작업 컨텍스트로 주입:

```text
이 클러스터의 스토리지 클래스를 정리하려고 해.
근거 자료: https://www.atomai.click/kubernetes-docs/ko/storage/01-ebs-gp2-gp3-benchmark
gp2 PVC를 gp3로 마이그레이션하는 계획을 세워줘.
```

**RAG 파이프라인 인덱싱** — full 파일 하나만 내려받아 청킹:

```bash
curl -sL https://www.atomai.click/kubernetes-docs/llms-full-ko.txt -o guidebook-ko.txt
# 각 문서는 "Source: <URL>" 구분자로 나뉘어 있어 문서 단위 청킹이 쉽습니다
```

## 형식 안내

- `llms.txt` — `# 제목` / `> 요약` / `## Docs (한국어)` / `## Docs (English)` / `## Optional` 섹션으로 구성된 llms.txt 표준 색인입니다. 각 항목은 그룹명과 제목을 붙인 링크 목록이라, 링크만 봐도 분류를 알 수 있습니다.
- `llms-full-*.txt` — 문서마다 아래 구분자 블록이 앞에 붙습니다:

```text
----------------------------------------
Source: https://www.atomai.click/kubernetes-docs/ko/core/01-cluster-architecture
----------------------------------------
```

- 크기 주의: full 파일은 수 MiB 규모입니다. 한 번의 프롬프트 컨텍스트에 다 넣기보다, 색인(llms.txt)으로 필요한 페이지를 고르게 하는 편이 대부분의 도구에서 더 잘 동작합니다.

## 다이어그램은 사람에게 — 내보내기 링크

full 파일은 문서의 마크다운을 그대로 담기 때문에, 각 다이어그램의 설명(alt 텍스트)과 인터랙티브 뷰어 URL(`https://www.atomai.click/kubernetes-docs/archmaps/<이름>.html`)도 텍스트로 들어 있습니다. LLM은 그 설명으로 다이어그램의 내용을 파악하고, 사람은 그 URL을 열어 뷰어의 **Export** 메뉴에서 PNG/JPEG/WebP, 라이트·다크 겸용 SVG, 트레이스 애니메이션 6초 WebM, 1200×630 Share Card를 바로 받을 수 있습니다. 메뉴 항목별 용도와 LinkedIn 포스팅 레시피는 [가이드북 로드맵](roadmap.md)의 "다이어그램 공유하기 — LinkedIn·발표용 내보내기" 섹션에 정리해 두었습니다. 내보낸 파일은 커뮤니케이션 자산일 뿐, 아키텍처 검증 증거는 아닙니다.

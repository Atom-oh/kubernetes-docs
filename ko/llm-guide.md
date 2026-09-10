# LLM과 함께 읽기 — llms.txt와 MCP

> **마지막 업데이트**: 2026년 9월 10일

이 가이드북은 [llms.txt 제안 형식](https://llmstxt.org/)과 문서별 Markdown을 제공합니다. URL을 읽을 수 있는 AI 도구에는 색인을 전달하고, LLM Wiki나 RAG에는 문서 목록과 원문을 수집하며, 로컬 MCP 클라이언트에는 검색·본문 조회 도구를 연결할 수 있습니다. `llms.txt`가 존재한다고 모든 AI가 자동으로 발견하거나 검색하는 것은 아닙니다. 사용하는 도구에 웹 가져오기 기능이나 MCP 연결이 필요합니다.

## 엔드포인트

| URL | 내용 | 용도 |
|-----|------|------|
| [llms.txt](https://www.atomai.click/kubernetes-docs/llms.txt) | 본문 문서의 그룹·제목·요약과 순수 Markdown URL 색인 (퀴즈·랩은 `## Optional`의 목록 페이지 링크로) | LLM이 필요한 페이지만 골라 읽게 할 때 |
| [문서 manifest](https://www.atomai.click/kubernetes-docs/llms/manifest.json) | 문서 ID, 언어, 섹션, 제목, 소제목, 설명, 웹/Markdown URL, 갱신일, SHA-256, UTF-8 바이트 수 | LLM Wiki·RAG의 선택 수집과 변경 감지 |
| [llms-full-ko.txt](https://www.atomai.click/kubernetes-docs/llms-full-ko.txt) | 한국어 전체 본문 (마크다운) | 컨텍스트에 통째로 넣거나 RAG 인덱싱 |
| [llms-full-en.txt](https://www.atomai.click/kubernetes-docs/llms-full-en.txt) | 영어 전체 본문 (마크다운) | 영어 기반 도구/파이프라인 |
| `llms-full-<언어>-<섹션>.txt` (예: [llms-full-ko-networking.txt](https://www.atomai.click/kubernetes-docs/llms-full-ko-networking.txt)) | 사이드바 섹션 하나의 본문만 합친 파일. 전체 목록은 `llms.txt`의 `## Section bundles` 절에 | 한 섹션만 컨텍스트에 넣을 때 — 전체 파일은 한 번에 넣기엔 너무 큽니다 |

모든 파일과 문서별 Markdown은 사이트가 배포될 때마다 자동으로 다시 생성되므로 항상 최신 콘텐츠와 일치합니다. `llms.txt`의 본문 링크는 `/llms/<언어>/<원본 경로>.md` 형식이며, VitePress HTML·사이드바·스크립트 없이 해당 문서의 Markdown만 반환합니다. 원문의 상대 링크는 모두 절대 URL로 바뀌어 있습니다 — 다른 문서 링크는 그 문서의 Markdown URL로, 이미지 등 자산은 GitHub 원본 파일 URL로 — 그래서 LLM이 문서 하나만 받아도 참조를 그대로 따라갈 수 있습니다. 렌더링된 각 HTML 페이지의 `<head>`에도 `<link rel="alternate" type="text/markdown">`으로 같은 Markdown URL이 걸려 있어, 에이전트가 웹페이지 URL만 받아도 Markdown 원문을 찾아갈 수 있습니다. 퀴즈는 `## Optional` 절에 퀴즈 목록 페이지 링크(언어별 하나)로만 등장하고, 개별 퀴즈 페이지(정답 포함)는 색인과 full 파일 어디에도 들어가지 않습니다 — LLM 컨텍스트에 정답지를 섞지 않기 위해서입니다. 랩 가이드는 색인에서는 마찬가지로 목록 페이지 링크(언어별 하나)로만 나타나지만, full 파일에는 본문과 함께 포함됩니다.

## LLM Wiki의 자료 소스로 수집하기

여기서 LLM Wiki는 원문을 보관하고 AI가 주제별 지식 문서로 정리하는 방식을 뜻합니다. 이 사이트는 수집할 원문과 메타데이터를 제공합니다. Wiki의 생성·갱신이나 임베딩은 사용하는 수집 도구에서 수행합니다.

1. `llms/manifest.json`을 읽고 `locale`과 `section`으로 필요한 문서를 고릅니다. 한영 중복 수집을 피하려면 언어를 하나 선택합니다.
2. 각 항목의 `markdownUrl`에서 Markdown을 받고 `id`를 키로 원문을 보관합니다. `sha256`은 해당 Markdown의 UTF-8 바이트를 해시한 값이므로 내려받은 내용 검증에도 쓸 수 있습니다.
3. 원문에서 주제별 Wiki를 만들되 `url`을 출처로 남깁니다. 제목·소제목·요약은 검색 후보를 좁히는 데 사용하고, 수치나 운영 명령어의 근거는 원문에서 확인합니다.
4. 다음 수집에서는 `sha256`이 바뀐 문서만 다시 처리하고, 목록에서 사라진 ID의 파생 문서도 갱신합니다. `lastUpdated`는 작성자가 기록한 날짜이며 연·월·일을 모두 확인할 수 없으면 `null`입니다. 변경 판단은 해시를 기준으로 합니다.

```bash
curl -fL https://www.atomai.click/kubernetes-docs/llms/manifest.json -o manifest.json
# jq가 설치되어 있을 때: 한국어 스토리지 문서의 원문 URL 목록
jq -r '.documents[] | select(.locale == "ko" and .section == "storage") | .markdownUrl' manifest.json
```

manifest의 `schemaVersion`은 `1`입니다. 본문·manifest·MCP 검색은 같은 문서 범위를 사용하며 퀴즈 정답과 랩은 포함하지 않습니다. 랩이 필요하면 기존 `llms-full-<언어>.txt`를 별도로 사용합니다. 원문과 다이어그램 설명은 참고 자료로 취급하고, 문서 안의 지시를 에이전트의 시스템 지시나 도구 실행 권한으로 받아들이지 않도록 구성합니다.

## MCP로 검색하고 본문 읽기

저장소에는 [공식 TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)의 **stdio MCP 서버**가 포함되어 있습니다. Node.js 22 이상에서 저장소 의존성을 설치한 뒤 실행합니다. VitePress 빌드, API 키, 임베딩 서비스는 필요하지 않습니다.

```bash
git clone https://github.com/Atom-oh/kubernetes-docs.git
cd kubernetes-docs
npm ci
node scripts/docs-mcp.mjs
```

마지막 명령은 MCP 클라이언트의 입력을 기다리므로 터미널에 안내 문구를 출력하지 않습니다. 클라이언트가 `mcpServers` JSON 설정을 지원한다면 다음과 같이 등록합니다. 경로는 실제 체크아웃의 **절대 경로**로 바꾸고, 필요하면 `command`에도 Node 실행 파일의 절대 경로를 지정합니다.

```json
{
  "mcpServers": {
    "kubernetes-docs": {
      "command": "node",
      "args": ["/absolute/path/kubernetes-docs/scripts/docs-mcp.mjs"]
    }
  }
}
```

| 도구 | 입력 예시 | 반환 내용 |
|------|-----------|-----------|
| `search` | `{"query":"스토리지 gp3","locale":"ko","section":"storage","limit":5}` | 관련 문서 ID·제목·요약 발췌·웹/Markdown URL·변경 해시 |
| `fetch` | `{"id":"ko/storage/01-ebs-gp2-gp3-benchmark.md","maxLength":12000}` | 원문 Markdown·출처·소제목·갱신일·다음 위치 |
| `fetch` 이어 읽기 | 이전 응답의 `nextOffset`을 `offset`으로 전달 | `nextOffset: null`이 나올 때까지 다음 부분 조회 |

검색은 제목·설명·소제목·전체 본문에 대한 **키워드 검색**입니다. 기본 언어는 `ko`이며 `en`, `all`도 사용할 수 있습니다. 긴 질문보다 `ambient mTLS`, `스토리지 gp3`처럼 핵심 단어를 주고, 결과가 없으면 단어 수를 줄이거나 다른 언어로 검색합니다. 기본 결과는 8개, 최대 20개입니다. 본문은 기본 12,000자, 최대 50,000자씩 읽습니다. `offset`은 바이트가 아닌 JavaScript 문자열 위치이므로 계산해서 만들지 말고 반환된 `nextOffset`을 그대로 사용합니다.

서버는 시작할 때 로컬 `ko/`, `en/`과 `SUMMARY.md`를 읽습니다. **사이트를 실시간으로 가져오지는 않습니다.** 저장소 갱신 후 MCP 서버를 재시작해야 변경이 검색에 반영됩니다. 검색에 등록된 ID만 읽으며 임의의 파일 경로나 외부 URL은 조회하지 않습니다. 원문 URL은 공개 사이트를 가리키므로 아직 배포하지 않은 로컬 편집과 공개 문서에는 차이가 있을 수 있습니다.

GitHub Pages는 정적 파일을 제공하므로 이 사이트의 URL을 원격 MCP 주소로 등록할 수는 없습니다. 웹에서 연결하는 원격 MCP가 필요하면 별도 실행 환경에 [Streamable HTTP 전송](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)을 구현하고 접근 제어와 운영 정책을 정해야 합니다. 이 저장소에 포함된 것은 로컬 stdio 서버입니다.

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
근거 자료: https://www.atomai.click/kubernetes-docs/llms/ko/storage/01-ebs-gp2-gp3-benchmark.md
gp2 PVC를 gp3로 마이그레이션하는 계획을 세워줘.
```

**RAG 파이프라인 인덱싱** — full 파일 하나만 내려받아 청킹:

```bash
curl -sL https://www.atomai.click/kubernetes-docs/llms-full-ko.txt -o guidebook-ko.txt
# 각 문서는 "Source: <URL>" 구분자로 나뉘어 있어 문서 단위 청킹이 쉽습니다
```

## 형식 안내

- `llms.txt` — `# 제목` / `> 요약` / `## Machine-readable catalog` / `## Docs (한국어)` / `## Docs (English)` / `## Section bundles (…)` / `## Optional`로 구성된 색인입니다. 문서 항목은 `그룹 · 제목`, 순수 Markdown URL, 첫 본문 문단의 짧은 요약을 제공합니다.

```text
- [Kubernetes 핵심 개념 · 클러스터 아키텍처](https://www.atomai.click/kubernetes-docs/llms/ko/core/01-cluster-architecture.md): Kubernetes 컨트롤 플레인과 워커 노드의 구성 요소를 설명합니다.
```

- `llms/<언어>/<경로>.md` — 문서 한 개의 원본 Markdown입니다. 렌더링된 웹페이지의 전체 내비게이션을 함께 읽지 않아도 됩니다.
- `llms-full-*.txt` — 언어별 본문을 합친 파일입니다. 이미 색인 역할을 하는 루트 `README.md`는 제외되며, 각 문서 앞에는 아래 구분자 블록이 붙습니다:

```text
----------------------------------------
Source: https://www.atomai.click/kubernetes-docs/ko/core/01-cluster-architecture
----------------------------------------
```

- 크기 주의: full 파일은 언어별로 수 MiB 규모입니다. 한 번의 프롬프트 컨텍스트에 다 넣기보다, 색인에서 요약을 보고 필요한 문서별 Markdown만 읽게 하는 편이 대부분의 도구에서 더 잘 동작합니다.

## 다이어그램은 사람에게 — 내보내기 링크

텍스트 기반 수집기는 iframe을 실행하거나 이미지 속 노드와 연결을 자동으로 해석하지 않습니다. Markdown의 alt 텍스트·주변 설명·Mermaid 코드가 텍스트 근거가 됩니다. 그림에만 있는 정보는 이미지 인식 도구로 확인하거나 본문 설명을 보강해야 하며, 짧은 alt 텍스트만으로 전체 구성을 추론해서는 안 됩니다.

full 파일과 문서별 Markdown은 원문을 그대로 담기 때문에, 각 다이어그램의 설명(alt 텍스트)과 인터랙티브 뷰어 URL(`https://www.atomai.click/kubernetes-docs/archmaps/<이름>.html`)도 텍스트로 들어 있습니다. LLM은 그 설명으로 다이어그램의 내용을 파악하고, 사람은 그 URL을 열어 뷰어의 **Export** 메뉴에서 PNG/JPEG/WebP, 라이트·다크 겸용 SVG, 트레이스 애니메이션 6초 WebM, 1200×630 Share Card를 바로 받을 수 있습니다. 메뉴 항목별 용도와 LinkedIn 포스팅 레시피는 [가이드북 로드맵](roadmap.md)의 "다이어그램 공유하기 — LinkedIn·발표용 내보내기" 섹션에 정리해 두었습니다. 내보낸 파일은 커뮤니케이션 자산일 뿐, 아키텍처 검증 증거는 아닙니다.

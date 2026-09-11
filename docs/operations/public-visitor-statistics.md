# 문서 사이트 방문 통계 연결

상단 **방문 통계 / Statistics** 메뉴에서 최근 30일의 방문자 수, 문서 조회수,
일별 추이를 볼 수 있습니다. 각 문서 하단에도 같은 기간의 요약을 표시합니다.
PC와 모바일, 한국어와 영어를 지원합니다.

## 집계 기준

- GA4 `totalUsers`: 기간 전체의 고유 사용자 수. 일별 사용자 수를 더하지 않습니다.
- GA4 `eventCount`: `docs_page_view` 이벤트만 집계. 기본 `page_view`와 합산하지 않습니다.
- 두 보고서 모두 `hostName = www.atomai.click`, `pagePath`가
  `/kubernetes-docs/`로 시작하는 조건과 이벤트 이름 필터를 적용합니다.
- 기간은 GA4 속성 시간대의 **어제까지 30일**입니다. 날짜별 보고서와 기간 전체
  보고서를 한 번의 `batchRunReports` 요청으로 읽습니다.
- `docs_page_view` 수집은 2026-09-10부터 시작했습니다. 이전 방문량을 복원하지 않습니다.
- 공개 JSON에는 날짜·사용자 수·조회수·시간대·갱신 시각·집계 제한 여부만 들어갑니다.
  IP, 사용자 ID, 이메일, 유입 URL, 쿼리 문자열, 액세스 토큰은 요청·공개 대상이 아닙니다.
- GA4 데이터 처리, 광고 차단과 동의 상태에 따라 실제 이용과 차이가 있습니다.
  임계값·표본 추출·집계 제한이 보고되면 화면에 알리고, 누락값은 0 대신 `—`로 표시합니다.

## 연결에 필요한 값

저장소의 **Settings → Secrets and variables → Actions → Variables**에 설정합니다.
아래 값은 식별자이며, 서비스 계정 JSON 키를 만들거나 저장할 필요가 없습니다.

| GitHub repository variable | 값 |
|---|---|
| `GA4_PROPERTY_ID` | GA4 관리 → 속성 세부정보의 숫자 속성 ID. `G-GWVLEW5JLL` 측정 ID와 다름 |
| `GA4_SERVICE_ACCOUNT` | 해당 GA4 속성에 **뷰어**로 추가한 Google 서비스 계정 이메일 |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL/providers/PROVIDER` |

GA4 권한과 Google Cloud IAM 권한은 별개입니다. Google Cloud 프로젝트의 Viewer
역할만 부여해서는 GA4 보고서를 읽을 수 없습니다.

### Google Cloud를 처음 사용하는 경우

1. Google Cloud 콘솔에 로그인하고 상단 프로젝트 선택 메뉴에서 **새 프로젝트**를
   만듭니다. 프로젝트 이름은 자유롭게 정하고, 생성된 **프로젝트 ID**를 확인합니다.
2. 해당 프로젝트를 선택한 상태에서 **Cloud Shell 활성화**를 누릅니다.
   아래 `DOCS_PROJECT_ID`에 확인한 값을 넣어 초기 설정을 실행합니다.
   속성 ID `396631876`은 이 저장소의 GitHub 변수에 등록되어 있습니다.
3. 만들어진 서비스 계정 이메일을 GA4 속성의 **뷰어**로 추가하고,
   나머지 GitHub 변수 두 개를 등록한 뒤 배포 워크플로를 실행합니다.

프로젝트 생성·Cloud Shell 로그인·GA4 액세스 관리는 계정 소유자가 수행해야 합니다.
Google 계정 비밀번호나 서비스 계정 JSON 키를 채팅으로 전달하지 않습니다.

### Google Cloud 설정 예시

다음은 프로젝트 관리자가 한 번 수행하는 초기 설정입니다. 이 저장소 작업이
Google Cloud나 GA4 계정 설정까지 자동으로 변경하지는 않습니다.
이미 같은 리소스가 있다면 새로 만들기보다 기존 설정을 확인해서 사용합니다.

```bash
# 실제 Google Cloud 프로젝트 ID와 GA4 숫자 속성 ID로 바꿉니다.
DOCS_PROJECT_ID="YOUR_PROJECT_ID"
DOCS_GA4_PROPERTY_ID="396631876"
DOCS_PROJECT_NUMBER="$(gcloud projects describe "$DOCS_PROJECT_ID" --format='value(projectNumber)')"
DOCS_STATS_SA="docs-statistics@${DOCS_PROJECT_ID}.iam.gserviceaccount.com"
DOCS_POOL="docs-statistics"
DOCS_PROVIDER="github"

gcloud services enable \
  analyticsdata.googleapis.com iam.googleapis.com \
  iamcredentials.googleapis.com sts.googleapis.com \
  --project="$DOCS_PROJECT_ID"

gcloud iam service-accounts create docs-statistics \
  --project="$DOCS_PROJECT_ID" --display-name="Public documentation aggregates"

gcloud iam workload-identity-pools create "$DOCS_POOL" \
  --project="$DOCS_PROJECT_ID" --location=global \
  --display-name="Documentation statistics"

# Numeric repository/owner IDs prevent a renamed or reused repository name
# from inheriting trust. Only this deployment workflow on main is accepted.
gcloud iam workload-identity-pools providers create-oidc "$DOCS_PROVIDER" \
  --project="$DOCS_PROJECT_ID" --location=global \
  --workload-identity-pool="$DOCS_POOL" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository_id=assertion.repository_id,attribute.repository_owner_id=assertion.repository_owner_id" \
  --attribute-condition="assertion.repository_id == '1020175043' && assertion.repository_owner_id == '52226147' && assertion.ref == 'refs/heads/main' && assertion.workflow_ref == 'Atom-oh/kubernetes-docs/.github/workflows/deploy.yml@refs/heads/main'"

gcloud iam service-accounts add-iam-policy-binding "$DOCS_STATS_SA" \
  --project="$DOCS_PROJECT_ID" \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/${DOCS_PROJECT_NUMBER}/locations/global/workloadIdentityPools/${DOCS_POOL}/attribute.repository_id/1020175043"
```

GA4에서 측정 ID `G-GWVLEW5JLL`에 해당하는 속성을 선택하고,
**관리 → 속성 액세스 관리**에서 `$DOCS_STATS_SA`에 해당하는 이메일을
**뷰어**로 추가합니다. 실제 방문 통계가 다른 속성에 있다면 숫자 속성 ID를 먼저
바로잡습니다. 서비스 계정에는 이 집계를 위해 Google Cloud 프로젝트 전체의
편집자·소유자 권한을 부여하지 않습니다.

그다음 GitHub 저장소의 **Settings → Secrets and variables → Actions → Variables**에서
서비스 계정 이메일과 Workload Identity Provider 전체 이름을 등록합니다.
Cloud Shell에서는 다음 명령으로 복사할 값을 확인할 수 있습니다.

```bash
printf 'GA4_SERVICE_ACCOUNT=%s\n' "$DOCS_STATS_SA"
printf 'GCP_WORKLOAD_IDENTITY_PROVIDER=projects/%s/locations/global/workloadIdentityPools/%s/providers/%s\n' \
  "$DOCS_PROJECT_NUMBER" "$DOCS_POOL" "$DOCS_PROVIDER"
```

`gh` CLI가 설치되어 있고 GitHub 저장소 관리 권한으로 인증한 환경에서는
아래 명령으로도 등록할 수 있습니다. Cloud Shell의 Google 로그인만으로
GitHub에 인증되는 것은 아닙니다.

```bash
gh variable set GA4_PROPERTY_ID --repo Atom-oh/kubernetes-docs \
  --body "$DOCS_GA4_PROPERTY_ID"
gh variable set GA4_SERVICE_ACCOUNT --repo Atom-oh/kubernetes-docs \
  --body "$DOCS_STATS_SA"
gh variable set GCP_WORKLOAD_IDENTITY_PROVIDER --repo Atom-oh/kubernetes-docs \
  --body "projects/${DOCS_PROJECT_NUMBER}/locations/global/workloadIdentityPools/${DOCS_POOL}/providers/${DOCS_PROVIDER}"
```

## 갱신과 실패 동작

`deploy.yml`은 main 배포와 매일 UTC 03:37에 집계를 갱신합니다. 예약 실행은
GitHub 상황에 따라 늦어질 수 있고, 위 변수들이 없으면 예약 빌드는 건너뜁니다.
공개 저장소의 예약 워크플로가 비활동으로 비활성화되면 Actions에서 다시 활성화합니다.

배포 작업은 OIDC로 5분짜리 `analytics.readonly` 액세스 토큰을 발급받고,
`scripts/fetch-public-statistics.mjs`만 해당 토큰을 전달받습니다. 인증 파일을
생성하지 않으며 토큰을 Vite 환경 변수나 HTML에 넣지 않습니다.

- 성공: `public/site-statistics.json`을 새로운 집계로 교체하고 사이트를 배포합니다.
- GA4 연결/갱신 실패: 현재 공개 사이트의 유효한 집계를 가져와 **원래 갱신 시각 그대로**
  재사용합니다. 72시간 이상 지나면 화면에 갱신 지연을 표시합니다.
- 기존 집계도 없음: 숫자 없이 “통계를 연결하고 있습니다”를 표시합니다.
- 브라우저에서 JSON 로드 실패: 오류와 재시도 버튼을 표시합니다.

설정 후 Actions의 **Deploy VitePress site to Pages → Run workflow → main**으로
실행합니다. `Refresh public visitor statistics` 로그가 `Public statistics: ga4`인지,
배포된 JSON이 `status: ready`인지, 통계 화면에 실제 기간과 갱신 시각이 보이는지 확인합니다.
`previous`는 이번 갱신에 실패해 이전 집계를 유지한 상태이며, `unavailable`은 아직
공개할 유효한 집계가 없는 상태입니다. 집계할 이벤트가 없는 정상 응답은 조회수 0과 안내문으로 표시합니다.
권한·임계값으로 제공되지 않는 값은 0으로 만들지 않습니다.

연결 전에는 UI·집계 변환·실패 처리만 검증할 수 있습니다. 실제 GA4 수신 및 보고서
조회 성공은 위 계정 권한을 연결한 뒤 별도로 확인해야 합니다.

## 공식 근거

- [GA4 Data API 시작하기](https://developers.google.com/analytics/devguides/reporting/data/v1/quickstart)
- [지원 측정기준과 측정항목](https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema)
- [batchRunReports](https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/properties/batchRunReports)
- [보고서 메타데이터와 임계값](https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/ResponseMetaData)
- [Google GitHub Actions 인증](https://github.com/google-github-actions/auth)
- [배포 파이프라인의 Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)

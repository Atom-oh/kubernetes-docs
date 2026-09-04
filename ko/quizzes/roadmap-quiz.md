# 가이드북 로드맵 퀴즈

1. 도메인 지도에서 Storage와 Database 도메인은 어느 계층에 속하나요?
   - A) 기초
   - B) 연결
   - C) 상태
   - D) 횡단
<details>
<summary>정답 보기</summary>

**정답: C) 상태**

**설명:**
도메인 지도 표에서 Storage(EBS gp2 vs gp3 fio 실측 벤치마크)와 Database(Operator 지형과 ClickHouse 1억 행 실측)는 모두 "상태" 계층입니다. 기초 계층은 Linux & Container, 연결 계층은 Networking과 Service Mesh, 횡단 계층은 Security & Policy·GitOps·Platform Engineering·Container Registry·Observability·Operations Guide입니다.

</details>

2. 로드맵의 학습 흐름 지도가 제시하는 계층 순서로 옳은 것은?
   - A) 오케스트레이션 → 기초 → 연결 → 상태 → 데이터·AI → 횡단 관심사
   - B) 기초 → 오케스트레이션 → 연결 → 상태 → 데이터·AI → 횡단 관심사
   - C) 기초 → 연결 → 오케스트레이션 → 데이터·AI → 상태 → 횡단 관심사
   - D) 횡단 관심사 → 기초 → 오케스트레이션 → 연결 → 상태 → 데이터·AI
<details>
<summary>정답 보기</summary>

**정답: B) 기초 → 오케스트레이션 → 연결 → 상태 → 데이터·AI → 횡단 관심사**

**설명:**
학습 흐름 지도는 15개 도메인이 "기초(Linux/Container) → 오케스트레이션(Kubernetes/EKS) → 연결(Networking/Service Mesh) → 상태(Storage/Database) → 데이터·AI(Data Pipeline/AI-ML) → 횡단 관심사(Security/GitOps/Platform/Container Registry/Observability/Operations)"로 이어진다고 설명합니다. Linux 커널에서 시작해 클라우드 네이티브 스택 전체를 하나의 서사로 다루는 구성입니다.

</details>

3. 다음 중 로드맵의 "실측 벤치마크 시리즈"에 **포함되지 않는** 도메인은 무엇인가요?
   - A) Service Mesh (Istio sidecar vs ambient)
   - B) Storage (EBS gp2 vs gp3)
   - C) Database (ClickHouse on EKS)
   - D) GitOps (ArgoCD·Flux)
<details>
<summary>정답 보기</summary>

**정답: D) GitOps (ArgoCD·Flux)**

**설명:**
실측 벤치마크 시리즈는 "스펙 시트가 아니라 실제 AWS 리소스에서 직접 측정한 숫자를 담은 문서들"로, Istio sidecar vs ambient 실측(mTLS 데이터플레인별 P50/P99 레이턴시와 rollout 중 503 비율), EBS gp2 vs gp3 실측 벤치마크(IOPS 10배 차이와 gp2 버스트 크레딧 절벽), ClickHouse on EKS 실측 벤치마크(1억 행 ingest 처리량·압축률·쿼리 레이턴시), Kafka on EKS 실측 벤치마크(RF3 ingest 상한 ≈130–135 MiB/s 등) 네 편입니다. GitOps는 횡단 도메인이지만 이 시리즈에 실측 문서가 없습니다.

</details>

4. 추천 학습 경로 ③ "데이터·AI 플랫폼"의 읽기 순서로 옳은 것은?
   - A) AI/ML → Data Pipeline → Database → Storage
   - B) Storage → Database → Data Pipeline(Kafka → Spark → Airflow → Flink) → AI/ML(vLLM → Ray → Kubeflow)
   - C) Data Pipeline → Storage → AI/ML → Database
   - D) Database → Storage → AI/ML → Data Pipeline
<details>
<summary>정답 보기</summary>

**정답: B) Storage → Database → Data Pipeline(Kafka → Spark → Airflow → Flink) → AI/ML(vLLM → Ray → Kubeflow)**

**설명:**
경로 ③은 "Storage → Database → Data Pipeline(Kafka → Spark → Airflow → Flink) → AI/ML(vLLM → Ray → Kubeflow)" 순서이며, GPU/스케줄링이 필요하면 Kubernetes 핵심 개념의 Custom Scheduler 파트를 함께 보라고 안내합니다. 상태 계층에서 시작해 데이터·AI 계층으로 올라가는 흐름입니다.

</details>

5. 추천 학습 경로 ① "인프라 입문"에서 이해도를 점검하는 방법으로 로드맵이 제시하는 것은?
   - A) 각 문서의 퀴즈로 점검하고, 실습 랩(labs)을 병행한다
   - B) 실측 벤치마크 시리즈를 먼저 모두 읽는다
   - C) 다이어그램 Share Card를 내보내 본다
   - D) llms.txt URL 하나를 LLM에 넣고 요약을 받는다
<details>
<summary>정답 보기</summary>

**정답: A) 각 문서의 퀴즈로 점검하고, 실습 랩(labs)을 병행한다**

**설명:**
경로 ①은 "Linux 기초 → 컨테이너 기술 → Kubernetes 소개 → 핵심 개념(파드/서비스/스토리지/구성) → EKS 클러스터 생성 → 네트워크 기초" 순서로 읽으면서 "각 문서의 퀴즈로 이해를 점검하고, 실습 랩을 병행하세요"라고 안내합니다. 실습 랩은 `labs/README.md`에서 시작합니다. 실측 벤치마크 시리즈는 경로 ② 플랫폼/SRE의 판단 근거로 소개됩니다.

</details>

6. LinkedIn에 "움직이는" 다이어그램 포스트를 올리려 할 때, 로드맵의 30초 레시피가 안내하는 절차로 옳은 것은?
   - A) 화면 녹화 프로그램으로 뷰어를 캡처한 뒤 GIF로 변환한다
   - B) 뷰어 툴바의 Live/Still 토글이 Live인지 확인하고, Export(`E`) → WebM으로 트레이스 애니메이션 6초를 내려받는다
   - C) Export → SVG를 내려받아 LinkedIn에 영상으로 업로드한다
   - D) Route Probe(`R`)로 경로를 추적한 뒤 Copy diagram으로 클립보드에 복사한다
<details>
<summary>정답 보기</summary>

**정답: B) 뷰어 툴바의 Live/Still 토글이 Live인지 확인하고, Export(`E`) → WebM으로 트레이스 애니메이션 6초를 내려받는다**

**설명:**
모든 인터랙티브 다이어그램은 `https://www.atomai.click/kubernetes-docs/archmaps/<이름>.html`에서 열리고, 툴바의 **Export** 버튼(단축키 `E`)이 공유용 파일을 바로 만들어 주므로 "별도 캡처 도구 없이 다이어그램 페이지 하나로 끝납니다". 레시피는 ① 다이어그램 열기 → ② **Live/Still** 토글이 Live인지 확인(화살표를 따라 흐르는 모션이 영상에 담기는 내용) → ③ **Export → WebM**(움직이는 포스트) 또는 **Export → Share Card**(1200×630 정적 미리보기) → ④ 원문 문서 URL과 함께 포스트, 순서입니다. WebM은 "Recording 6 seconds of motion…" 표시 후 내려오며, 트레이스 애니메이션이 있는 다이어그램과 브라우저의 MediaRecorder 지원이 필요합니다. SVG는 라이트·다크 겸용 벡터로 발표 자료용입니다.

</details>

7. Export 메뉴의 **Route Share Card**에 대한 설명으로 옳은 것은?
   - A) 어떤 다이어그램에서든 항상 표시되며, 가까운 도형 사이의 경로를 자동으로 추측해 그린다
   - B) Route Probe(`R`)로 두 노드 사이 경로를 추적한 뒤에만 나타나며, 작성자가 명시한 방향성 관계만 따라 계산된 경로를 담는다
   - C) 노드의 upstream/downstream 도달성을 보여 주는 카드로, 장애 반경(blast radius) 분석 결과다
   - D) 클립보드 복사만 지원하고 다운로드는 지원하지 않는다
<details>
<summary>정답 보기</summary>

**정답: B) Route Probe(`R`)로 두 노드 사이 경로를 추적한 뒤에만 나타나며, 작성자가 명시한 방향성 관계만 따라 계산된 경로를 담는다**

**설명:**
Export 메뉴 표에서 Route Share Card는 1200×630 PNG(다운로드 전용)이며 "Route Probe(`R`)로 두 노드 사이 경로를 추적한 뒤에만 나타남"이라고 되어 있습니다. "내보내기의 한계" 섹션은 "Route Share Card는 작성자가 명시한 방향성 관계만 따라 계산된 경로입니다. 도형이 가까이 있다는 이유로 경로를 추측하지 않고, 경로가 바뀌었거나 도달 불가능하면 내보내기를 거부합니다"라고 덧붙입니다. upstream/downstream 도달성은 별도의 Reach Share Card가 담당하며, 그것도 영향 범위·장애 반경·장애 전파·런타임 인과관계로 해석하지 말라고 명시합니다.

</details>

8. 로드맵이 "내보내기의 한계 — 정직하게 말하기"에서 Share Card 등 내보낸 파일에 대해 밝히는 입장은 무엇인가요?
   - A) 내보낸 파일은 커뮤니케이션 자산이며, 아키텍처가 검증됐다는 증거가 아니고 Share Card에도 "검증됨" 표시는 붙지 않는다
   - B) Share Card에는 자동으로 "검증됨" 배지가 붙어 검증 증거로 쓸 수 있다
   - C) 내보낸 파일이 게시된 원본 HTML을 대체하는 정식 산출물이다
   - D) Reach Share Card는 런타임 장애 전파를 실측한 결과이므로 장애 분석 보고서에 그대로 쓸 수 있다
<details>
<summary>정답 보기</summary>

**정답: A) 내보낸 파일은 커뮤니케이션 자산이며, 아키텍처가 검증됐다는 증거가 아니고 Share Card에도 "검증됨" 표시는 붙지 않는다**

**설명:**
해당 섹션의 첫 항목은 "내보낸 파일은 커뮤니케이션 자산입니다. 아키텍처가 검증됐다는 증거가 아니며, 게시된 원본 HTML과 작성자의 검증 과정을 대신하지 않습니다. Share Card에도 '검증됨' 같은 표시는 붙지 않습니다"라고 말합니다. Reach Share Card가 보여 주는 것도 *authored reachability*일 뿐이므로 영향 범위, 장애 반경, 장애 전파, 런타임 인과관계로 해석해 소개하지 말라고 명시합니다.

</details>

# Dynatrace 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

---

1. OneAgent에 대한 설명 중 잘못된 것은?
   - A) 지원되는 프로세스를 탐지할 수 있다.
   - B) 지원되는 기술을 계측할 수 있다.
   - C) 설치하면 권한·범위·연결에 관한 모든 전제 조건이 사라진다.
   - D) 배포 모드와 기술 지원에 따라 수집 범위가 달라진다.

<details>
<summary>정답 보기</summary>

**정답: C) 설치하면 권한·범위·연결에 관한 모든 전제 조건이 사라진다.**

자동 탐지가 설치 권한·지원 runtime·egress·토큰·주입 범위·데이터 보호 결정을 대신하지 않습니다. 모든 메서드나 요청의 수집을 보장하지도 않습니다.

</details>

---

2. Kubernetes에서 DynaKube 리소스와 Dynatrace 워크로드를 관리하는 컴포넌트는?
   - A) kubectl binary 단독.
   - B) Dynatrace Operator.
   - C) OneAgent 프로세스만.
   - D) 자동 생성되는 Lambda 함수.

<details>
<summary>정답 보기</summary>

**정답: B) Dynatrace Operator.**

Helm 또는 manifest로 Operator를 설치하므로 서로 경쟁하는 모니터링 모드가 아닙니다. 검토 기준 Operator/chart는 1.10.2이며 배포 CRD는 v1beta5·v1beta6을 제공하고 storage는 v1beta6입니다. 기존 v1beta2는 현재 제공 API가 아닙니다. 컴포넌트 버전과 업데이트 동작은 별도 검토가 필요합니다.

</details>

---

3. 문제 탐지와 근본 원인 분석을 켜는 것만으로 성립하지 않는 결과는?
   - A) 기준선·이상 분석.
   - B) 토폴로지를 활용한 조사.
   - C) 검토하지 않은 운영 코드 변경이 자동 승인됨.
   - D) 수집한 근거를 활용한 영향 분석.

<details>
<summary>정답 보기</summary>

**정답: C) 검토하지 않은 운영 코드 변경이 자동 승인됨.**

이전 자료의 Davis 명칭과 현재 Dynatrace Intelligence를 구분합니다. Preview를 포함해 승인된 agentic action/workflow를 구성할 수 있으므로 'AI는 절대 조치할 수 없다'도 과도한 표현입니다. 탐지 자체가 복구 권한이나 진단의 정확성을 보장하지는 않습니다.

</details>

---

4. cloudNativeFullStack은 무엇을 결합하나요?
   - A) Windows 모니터링만.
   - B) Host monitoring과 webhook 기반 앱 code-module 주입.
   - C) Host 컴포넌트가 없는 application-only 모니터링.
   - D) 모든 workload의 더 낮은 overhead 보장.

<details>
<summary>정답 보기</summary>

**정답: B) Host monitoring과 webhook 기반 앱 code-module 주입.**

배포된 Operator는 cloudNativeFullStack을 hostMonitoring과 applicationMonitoring의 결합으로 설명하며 CSI 구조를 사용합니다. 단순한 앱 sidecar가 아닙니다. classicFullStack도 검토한 release에 남아 있으므로 제거됐다고 설명하지 않습니다. 모드·OS·CSI 권한에 따라 적합성이 달라집니다.

</details>

---

5. PurePath와 관련된 기능은?
   - A) 로그 압축.
   - B) 지원되는 코드 수준 컨텍스트를 포함한 분산 추적.
   - C) 범용 패킷 캡처 장비.
   - D) 데이터베이스 백업.

<details>
<summary>정답 보기</summary>

**정답: B) 지원되는 코드 수준 컨텍스트를 포함한 분산 추적.**

Trace·코드 가시성은 지원 기술·계측·capture/sampling 설정·수집 데이터에 좌우됩니다. '전체 경로'라는 표현이 모든 요청·메서드·비동기 관계의 보존을 입증하지는 않습니다.

</details>

---

6. 현재 DPS의 host-based Full-Stack Monitoring 사용량 단위는?
   - A) vCPU와 RAM의 합.
   - B) 해당 rate card에 따른 모니터링 memory-GiB-hour.
   - C) max(RAM/16, vCPU/1.5) Host Unit.
   - D) Kubernetes namespace마다 고정 한 단위.

<details>
<summary>정답 보기</summary>

**정답: B) 해당 rate card에 따른 모니터링 memory-GiB-hour.**

공식 지침은 15분 청구 구간, 0.25 GiB 단위 RAM 올림과 host 최소 4 GiB를 설명합니다. Container-based application-only에는 다른 메모리·최솟값 규칙이 있습니다. 기존 CPU/RAM 최댓값 공식은 현재 DPS 계산이 아닙니다. 사용량 계산과 청구액은 다르며 commitment·rate card·포함량·별도 과금 기능을 확인해야 합니다.

</details>

---

7. ActiveGate의 역할이 아닌 것은?
   - A) 텔레메트리 라우팅.
   - B) 구성한 Kubernetes API 모니터링.
   - C) 장기 분석용 data lakehouse 역할.
   - D) 환경으로 연결되는 승인된 통신 경로 제공.

<details>
<summary>정답 보기</summary>

**정답: C) 장기 분석용 data lakehouse 역할.**

라우팅·모니터링·로컬 버퍼와 장기 backend 저장소는 다릅니다. 일부 containerized ActiveGate 수신 구성에는 PVC가 필요합니다. SaaS 경로에는 연결이 필요하며 proxy가 완전히 단절된 망을 SaaS에 연결해 주는 것은 아닙니다.

</details>

---

8. oneAgent.cloudNativeFullStack.namespaceSelector는 무엇을 선택하나요?
   - A) 생성할 namespace.
   - B) 구성한 webhook 주입 대상 namespace.
   - C) 네트워크 격리 경계.
   - D) Host·Kubernetes API 모니터링의 전체 범위.

<details>
<summary>정답 보기</summary>

**정답: B) 구성한 webhook 주입 대상 namespace.**

Selector와 Pod 주입 annotation은 webhook 주입을 제어하며 OneAgent host monitoring이나 ActiveGate Kubernetes API monitoring을 제한하지 않습니다. Metadata enrichment·OTLP exporter 자동 구성에도 별도 selector가 있습니다. Label·DynaKube 변경 권한을 통제해야 하며 selector는 RBAC나 비용 상한이 아닙니다.

</details>

---

9. 공식 Dynatrace SaaS/ActiveGate native OTLP API가 받는 전송 형식은?
   - A) gRPC만.
   - B) HTTP와 binary Protocol Buffers.
   - C) gRPC와 HTTP/JSON을 구분 없이.
   - D) OTLP가 아닌 독자 형식만.

<details>
<summary>정답 보기</summary>

**정답: B) HTTP와 binary Protocol Buffers.**

Native endpoint는 HTTP/protobuf를 지원하며 gRPC·protobuf JSON은 받지 않습니다. Collector에서 gRPC를 받아 HTTP로 변환할 수 있습니다. /api/v2/otlp base와 신호별 suffix, TLS, 선택한 endpoint의 토큰 종류·scope를 맞춰야 하며 .apps 브라우저 URL로 대체하지 않습니다.

</details>

---

10. Smartscape가 제공하는 기능은?
   - A) 모든 알림을 끄는 switch.
   - B) 관측 데이터 기반 토폴로지·의존성 매핑.
   - C) 확장을 위한 자동 권한 부여.
   - D) 소스 코드 리뷰.

<details>
<summary>정답 보기</summary>

**정답: B) 관측 데이터 기반 토폴로지·의존성 매핑.**

의존성 그래프는 영향 분석과 조사를 돕습니다. 수집 기술·텔레메트리에 따라 범위가 달라지므로 관계가 보이지 않거나 데이터가 없다는 사실을 의존성이 없다는 증거로 해석하지 않습니다.

</details>

---

[본문으로 돌아가기](../../../observability/tracing/04-dynatrace.md)

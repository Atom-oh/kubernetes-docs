# 로그 수집기 비교 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

1. 수집기 자원 요구량은 어떻게 비교해야 하는가?

   - A) 구현 언어만으로 고정 메모리 순위를 정한다
   - B) 같은 레코드·처리·목적지·실패 설정으로 측정한다
   - C) 모든 Go 수집기를 동일하게 취급한다
   - D) 공개된 초당 이벤트 숫자 하나만 사용한다

<details>
<summary>정답 보기</summary>

**정답: B) 같은 레코드·처리·목적지·실패 설정으로 측정한다**

Buffer·metadata cache·batch·retry·동시성이 자원에 영향을 줍니다. 언어나 압축 형식만으로 처리량을 보장할 수 없습니다.

</details>

---

2. Fluent Bit에서 Pod·namespace metadata를 추가하는 filter는?

   - A) modify
   - B) parser
   - C) kubernetes
   - D) record_modifier만

<details>
<summary>정답 보기</summary>

**정답: C) kubernetes**

kubernetes filter는 올바른 tag와 metadata 조회 권한이 필요합니다. Use_Kubelet을 켜면 kubelet 연결·권한도 별도로 확인합니다.

</details>

---

3. 현재 Promtail에 대한 올바른 접근은?

   - A) 2026년 3월 2일 EOL이므로 이전한다
   - B) 모든 신규 Loki 배포에 선택한다
   - C) 기존 설치는 계속 업데이트된다고 가정한다
   - D) lambda-promtail도 자동으로 같은 종료 대상이다

<details>
<summary>정답 보기</summary>

**정답: A) 2026년 3월 2일 EOL이므로 이전한다**

공식 공지는 Alloy 또는 지원되는 다른 client로의 이전을 안내하며 별도 lambda-promtail은 해당 공지에서 제외합니다.

</details>

---

4. Grafana Alloy가 사용하는 설정 문법은?

   - A) 변환 없이 모든 Kubernetes YAML 사용
   - B) 이전 명칭이 River인 Alloy 설정 문법
   - C) 모든 Terraform provider를 포함한 Terraform HCL
   - D) INI만

<details>
<summary>정답 보기</summary>

**정답: B) 이전 명칭이 River인 Alloy 설정 문법**

HCL과 비슷하지만 Alloy component graph가 Terraform 파일과 호환되는 것은 아닙니다. 선택한 Alloy binary로 검증합니다.

</details>

---

5. 일반적인 Collector pipeline 순서는?

   - A) Exporters → Receivers → Processors
   - B) Processors → Exporters → Receivers
   - C) Receivers → Processors → Exporters
   - D) 모든 component를 임의 순서로 실행

<details>
<summary>정답 보기</summary>

**정답: C) Receivers → Processors → Exporters**

Connector는 pipeline을 연결할 수 있습니다. 현재 Loki 경로는 OTLP HTTP를 사용하며 Contrib0.160.0에는 제거된 loki exporter가 없습니다.

</details>

---

6. 예제 Lua 변환이 수행하는 것은?

   - A) 임의 텍스트의 모든 비밀 제거
   - B) 원본 node log file 삭제
   - C) Exactly-once 전달
   - D) 지정한 structured key 가림과 raw 복사본 제거

<details>
<summary>정답 보기</summary>

**정답: D) 지정한 structured key 가림과 raw 복사본 제거**

일반 PII 탐지기나 fail-closed 경계가 아닙니다. 일반 텍스트와 message 문자열에는 민감정보가 남을 수 있습니다.

</details>

---

7. 기존 Promtail과 Alloy의 drop stage 이름을 올바르게 구분한 것은?

   - A) Promtail YAML key도 모두 stage.drop
   - B) Promtail YAML은 drop, Alloy는 stage.drop
   - C) Promtail filter.exclude, Alloy ignore
   - D) 둘 다 record를 버릴 수 없음

<details>
<summary>정답 보기</summary>

**정답: B) Promtail YAML은 drop, Alloy는 stage.drop**

Parser·template·labels·output도 순서와 필드 보존에 영향을 줍니다. Stage 목록을 하나의 범용 처리 chain으로 적용하지 않습니다.

</details>

---

8. 두 AWS 목적지의 native Fluent Bit output 이름은?

   - A) cloudwatch_logs와 opensearch
   - B) cloudwatch와 elastic만
   - C) stage.cloudwatch와 stage.opensearch
   - D) Loki tenant_id가 두 AWS 목적지를 생성

<details>
<summary>정답 보기</summary>

**정답: A) cloudwatch_logs와 opensearch**

Plugin 지원이 IAM 권한을 부여하지는 않습니다. 실제 ServiceAccount identity·Region·endpoint·TLS·사전 생성 리소스의 소유권을 맞춥니다.

</details>

---

9. memory_limiter는 메모리 압박에서 어떻게 동작하는가?

   - A) 프로세스가 절대 OOM 나지 않음을 보장
   - B) Node 메모리를 추가 생성
   - C) Retryable error로 데이터를 거절하고 garbage collection을 요청할 수 있음
   - D) 모든 source record를 자동 영속화

<details>
<summary>정답 보기</summary>

**정답: C) Retryable error로 데이터를 거절하고 garbage collection을 요청할 수 있음**

Receiver retry·한도·queue가 중요합니다. Filelog의 유한한 retry 시간이 끝나면 실패한 batch를 버릴 수 있습니다.

</details>

---

10. Promtail→Alloy 변환 성공 후 필요한 작업은?

   - A) 전달·메트릭이 완전히 같다고 즉시 선언
   - B) 모든 진단 경고 무시
   - C) 같은 로그에서 두 agent를 무기한 동시 실행
   - D) 파싱·state·소유권·인증·self-metric·실제 backend record 검증

<details>
<summary>정답 보기</summary>

**정답: D) 파싱·state·소유권·인증·self-metric·실제 backend record 검증**

Converter가 전역 rate limit을 pipeline별 제한으로 바꿀 수 있으며 host mount나 Kubernetes 권한을 검증하지는 않습니다. File/API 수집 소유권을 정해 중복을 피합니다.

</details>

---

[본문으로 돌아가기](../../../observability/logging/05-collectors.md)

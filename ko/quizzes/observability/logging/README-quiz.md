# 로깅 개요 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

1. 구조화된 JSON log에 대한 올바른 설명은?

   - A) Parsing이 필요 없음
   - B) 항상 byte가 더 적음
   - C) 명시적 field가 분석을 돕지만 decoding·framing·mapping은 여전히 필요
   - D) 모든 민감 데이터를 자동 제거

<details>
<summary>정답 보기</summary>

**정답: C**

검증한 schema와 보통 한 줄당 encoded event 하나를 사용합니다. JSON이 더 클 수 있으며 raw/parsed copy 모두 데이터 처리 정책이 필요합니다.

</details>

2. TRACE부터 FATAL까지의 숫자는 언제나 0부터 5인가요?

   - A) 아니요. Framework마다 다르고 OpenTelemetry는 1–24 범위와 미지정 0을 사용
   - B) 모든 언어에서 예
   - C) Kubernetes에서만 예
   - D) FATAL은 항상 0

<details>
<summary>정답 보기</summary>

**정답: A**

임의 숫자가 아니라 의미를 mapping합니다. Level만으로 복구 가능성을 정하지 않으며 모두 WARN으로 올리면 증거가 사라질 수 있습니다.

</details>

3. 일반적인 Linux container log 기본 배치는?

   - A) /var/log/containers가 실제 file, /var/log/pods가 symlink
   - B) /var/log/pods가 실제 file, /var/log/containers가 호환 symlink
   - C) 모든 runtime이 /var/lib/docker만 사용
   - D) kubectl logs가 무제한 archive 제공

<details>
<summary>정답 보기</summary>

**정답: B**

기존 설명은 뒤바뀌어 있었습니다. podLogsDir/OS/runtime별 차이가 있으며 rotation과 --previous는 중앙 과거 archive가 아닙니다.

</details>

4. 공정한 backend 비용 비교에 필요한 것은?

   - A) S3 GB 단가만
   - B) 항상 Loki가 최저가
   - C) 자체 운영 query는 무료로 가정
   - D) 같은 workload에서 수집·보존/index·compute·query·request·network·복구·운영 비교

<details>
<summary>정답 보기</summary>

**정답: D**

기존 2025/100-GB 예시는 단위를 섞고 재현 가능한 구성이 없었습니다. 측정 production 결과가 아니므로 날짜만 바꾸어도 고쳐지지 않습니다.

</details>

5. Log에 trace context를 연결하는 올바른 방법은?

   - A) Record마다 무관한 ID 생성
   - B) 실제 active context를 사용하고 예시 표현은 trace/span 32/16 hex이며 모두 0이면 안 됨
   - C) 모든 startup record에 trace ID 필수
   - D) Session token을 span ID로 사용

<details>
<summary>정답 보기</summary>

**정답: B**

Trace가 없는 event도 유효합니다. JSON field는 destination 모델로 mapping해야 하며 ID만으로 trace 생성이나 correlation이 보장되지는 않습니다.

</details>

6. 예시 pipeline에서 더 적절한 처리 선택은?

   - A) HealthCheck가 있으면 모두 삭제
   - B) Application JSON을 tenant identity로 신뢰
   - C) App field와 신뢰 metadata를 분리하고 redaction/filter·offset·buffer·retry 검증
   - D) Buffer가 모든 유실/중복을 방지한다고 가정

<details>
<summary>정답 보기</summary>

**정답: C**

Fluent Bit 예시는 classic-format filter fragment입니다. Keep_Log의 raw copy도 redaction 대상이며 실패 health check는 중요한 증거일 수 있습니다.

</details>

7. 규정 관련 retention은 어떻게 선택하나요?

   - A) Record 유형·관할·계약·legal hold·승인 정책에 따라
   - B) 모든 금융 log는 7년
   - C) 모든 의료 log는 6년
   - D) Backend 이름만으로 규정 준수 증명

<details>
<summary>정답 보기</summary>

**정답: A**

업종 이름만으로 법 규칙이 완성되지 않습니다. Replica/object version/backup/export를 보존·삭제·접근 계획에 포함하고 복원을 시험합니다.

</details>

8. Sidecar와 DaemonSet에 대한 올바른 설명은?

   - A) 둘 다 tenant 격리 보장
   - B) emptyDir가 Pod 삭제를 견딤
   - C) DaemonSet만 있으면 모든 node log 전달이 증명
   - D) Sidecar는 file-only app에 유용하지만 배치·shared storage·lifecycle·security 검증 필요

<details>
<summary>정답 보기</summary>

**정답: D**

emptyDir는 같은 Pod의 container 재시작은 견디지만 Pod 삭제는 아닙니다. DaemonSet은 대상 node에 배치되며 rollout/복수 경로로 중복 수집될 수 있습니다.

</details>

9. 저장소/client에 대한 올바른 설명은?

   - A) OpenSearch는 모든 배포에서 S3를 snapshot에만 사용
   - B) 배포/index/query 설계가 중요하며 UltraWarm은 S3/cache를 쓰고 Promtail은 EOL 이후 migration 필요
   - C) 모든 CloudWatch log class 기능이 같음
   - D) Dataset 없이 압축 순위가 유효

<details>
<summary>정답 보기</summary>

**정답: B**

실제 배포 모델과 query 요구를 비교합니다. Promtail EOL은 2026-03-02이며 lambda-promtail은 별도입니다. Backend 선택만으로 비용/규정 준수를 보장하지 않습니다.

</details>

10. EKS control-plane audit logging을 활성화하면 무엇을 알 수 있나요?

   - A) 모든 request/body가 무손실 기록
   - B) Worker DaemonSet이 managed API-server host를 읽음
   - C) Policy와 best-effort CloudWatch 전달 경로를 따르는 audit record를 실제 확인해야 함
   - D) Application stdout 수집이 자동 완성

<details>
<summary>정답 보기</summary>

**정답: C**

비동기 update 상태·stream·retention/접근을 확인합니다. Fargate는 managed router를 사용하며 Container Insights performance log와 application stdout/stderr는 다릅니다.

</details>

---

[학습 자료로 돌아가기](../../../observability/logging/README.md)

# Observability Lab 02 퀴즈

<span id="observability-실습-part-2-observability-스택-퀴즈"></span>

> **마지막 업데이트**: 2026년 9월 13일

1. cross-cluster 수집 endpoint는?
   - A) 다른 cluster의 svc DNS만
   - B) 실제 route/DNS/TLS가 준비된 private endpoint
   - C) TLS 검증 항상 끄기
   - D) kubeconfig 파일을 URL로

<details>
<summary>정답 보기</summary>

**정답: B) 실제 route/DNS/TLS가 준비된 private endpoint**

NLB는 TCP를 전달하고 서버에서 clientcert를 검증합니다.

</details>

---

2. CRI 로그 처리 순서는?
   - A) Docker JSON parser만
   - B) container/CRI parser 다음 JSON parser
   - C) 원본 prefix를 body 필드로 가정
   - D) traceID를 모두 stream label로

<details>
<summary>정답 보기</summary>

**정답: B) container/CRI parser 다음 JSON parser**

앱 body의 service/level/trace_id가 보존되는지 검증합니다.

</details>

---

3. mTLS Prometheus의 health probe는?
   - A) 인증서 없는 기본 HTTPS probe가 항상 성공
   - B) clientcert 설정을 사용하는 promtool exec probe
   - C) probe를 모두 삭제
   - D) readiness를 항상 true

<details>
<summary>정답 보기</summary>

**정답: B) clientcert 설정을 사용하는 promtool exec probe**

실제 Operator merge와 Prometheus TLS ready/healthy를 검증했습니다.

</details>

---

4. Tempo 3 설정에서 주의할 변화는?
   - A) Tempo 2 ingester 값만 그대로
   - B) live-store/backend scheduler/worker와 현재 차트 값을 사용
   - C) Loki 설정을 복사
   - D) 차트 버전과 앱 버전은 항상 같다

<details>
<summary>정답 보기</summary>

**정답: B) live-store/backend scheduler/worker와 현재 차트 값을 사용**

차트 render와 실제 binary config/startup을 구분해 확인합니다.

</details>

---

5. 단일 Loki/Tempo baseline의 의미는?
   - A) production HA 자동 완성
   - B) 실습용 durable instance이며 HA·용량 보장은 아니다
   - C) 스토리지 비용 없음
   - D) 백업도 자동 보장

<details>
<summary>정답 보기</summary>

**정답: B) 실습용 durable instance이며 HA·용량 보장은 아니다**

보존 기간·PVC·정리 및 장애 영향을 확인합니다.

</details>

---

6. AIOps용 CloudWatch JSON은?
   - A) 쿼리 문자열만
   - B) service/level/trace_id가 유지된 구조화 로그
   - C) 모든 비밀번호 원문
   - D) trace만 있으면 로그도 자동으로 생김

<details>
<summary>정답 보기</summary>

**정답: B) service/level/trace_id가 유지된 구조화 로그**

raw_log 설정과 실제 PutLogEvents 메시지를 로컬로 검증했습니다.

</details>

---

7. Grafana correlation의 필요조건은?
   - A) UI 옵션만 켜기
   - B) UID·필드명·실제 수집 데이터·보존 기간 일치
   - C) 데이터 소스 이름만 같게
   - D) trace_id를 항상 대문자로

<details>
<summary>정답 보기</summary>

**정답: B) UID·필드명·실제 수집 데이터·보존 기간 일치**

prometheus/loki/tempo UID와 escaped derived field 표현식을 맞춥니다.

</details>

---

8. service Prometheus remote-write에서 exemplar는?
   - A) 항상 자동 보존
   - B) sendExemplars와 수신/저장/데이터 소스 연결을 함께 확인
   - C) 기본 정보만 있으면 trace도 생김
   - D) 모든 요청을 무조건 저장

<details>
<summary>정답 보기</summary>

**정답: B) sendExemplars와 수신/저장/데이터 소스 연결을 함께 확인**

전송 옵션뿐 아니라 대표 요청의 trace 존재도 검증합니다.

</details>

---

9. node 로그를 읽는 DaemonSet 권한은?
   - A) hostPID와 모든 capability 항상 허용
   - B) 정해진 read-only host mount·제한 RBAC·명시한 root 예외만 허용
   - C) 전체 clusteradmin
   - D) host log 경로는 권한과 무관

<details>
<summary>정답 보기</summary>

**정답: B) 정해진 read-only host mount·제한 RBAC·명시한 root 예외만 허용**

namespace admission과 실제 file 권한을 함께 검증합니다.

</details>

---

10. 선택 backend와 durable queue의 설명은?
   - A) 모든 backend가 이미 배포됨
   - B) 별도 검증 대상이며 baseline은 file offset/queue 영속성을 보장하지 않는다
   - C) 재시작 시 유실/중복 불가능
   - D) 24시간 보존은 30일 SLO 증거

<details>
<summary>정답 보기</summary>

**정답: B) 별도 검증 대상이며 baseline은 file offset/queue 영속성을 보장하지 않는다**

실제 설정과 검증 범위만 성공으로 기록합니다.

</details>

---

[본문으로 돌아가기](../../../labs/observability/02-observability-stack-lab.md)

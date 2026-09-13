# Observability Lab 02 퀴즈

<span id="observability-실습-part-2-observability-스택-퀴즈"></span>

> **마지막 업데이트**: 2026년 9월 13일

1. cross-cluster 수집 endpoint는?
   - A) 다른cluster의svcDNS만
   - B) 실제 route/DNS/TLS가 준비된 private endpoint
   - C) TLS검증항상끄기
   - D) kubeconfig파일을URL로

<details>
<summary>정답 보기</summary>

**정답: B) 실제 route/DNS/TLS가 준비된 private endpoint**

NLB는TCP를전달하고서버에서clientcert를검증합니다.

</details>

---

2. CRI 로그 처리 순서는?
   - A) DockerJSONparser만
   - B) container/CRI parser 다음 JSON parser
   - C) 원본prefix를body필드로가정
   - D) traceID를모두streamlabel로

<details>
<summary>정답 보기</summary>

**정답: B) container/CRI parser 다음 JSON parser**

앱body의service/level/trace_id가보존되는지검증합니다.

</details>

---

3. mTLS Prometheus의 health probe는?
   - A) 인증서없는기본HTTPSprobe가항상성공
   - B) clientcert설정을사용하는promtool exec probe
   - C) probe를모두삭제
   - D) readiness를항상true

<details>
<summary>정답 보기</summary>

**정답: B) clientcert설정을사용하는promtool exec probe**

실제Operatormerge와PrometheusTLSready/healthy를검증했습니다.

</details>

---

4. Tempo3 설정에서 주의할 변화는?
   - A) Tempo2ingester값만그대로
   - B) live-store/backend scheduler/worker와현재차트값을사용
   - C) Loki설정을복사
   - D) 차트버전과앱버전은항상같다

<details>
<summary>정답 보기</summary>

**정답: B) live-store/backend scheduler/worker와현재차트값을사용**

차트render와실제binaryconfig/startup을구분해확인합니다.

</details>

---

5. 단일 Loki/Tempo baseline의 의미는?
   - A) productionHA자동완성
   - B) 실습용 durable instance이며HA·용량보장은아니다
   - C) 스토리지비용없음
   - D) 백업도자동보장

<details>
<summary>정답 보기</summary>

**정답: B) 실습용 durable instance이며HA·용량보장은아니다**

보존기간·PVC·정리및장애영향을확인합니다.

</details>

---

6. AIOps용 CloudWatch JSON은?
   - A) 쿼리문자열만
   - B) service/level/trace_id가유지된구조화로그
   - C) 모든비밀번호원문
   - D) trace만있으면로그도자동생김

<details>
<summary>정답 보기</summary>

**정답: B) service/level/trace_id가유지된구조화로그**

raw_log설정과실제PutLogEvents메시지를로컬로검증했습니다.

</details>

---

7. Grafana correlation의 필요조건은?
   - A) UI옵션만켜기
   - B) UID·필드명·실제수집데이터·보존기간일치
   - C) 데이터소스이름만같게
   - D) trace_id를항상대문자로

<details>
<summary>정답 보기</summary>

**정답: B) UID·필드명·실제수집데이터·보존기간일치**

prometheus/loki/tempo UID와escapedderivedfield표현식을맞춥니다.

</details>

---

8. service Prometheus remote-write에서 exemplar는?
   - A) 항상자동보존
   - B) sendExemplars와수신/저장/데이터소스연결을함께확인
   - C) 기본정보만있으면trace도생김
   - D) 모든요청을무조건저장

<details>
<summary>정답 보기</summary>

**정답: B) sendExemplars와수신/저장/데이터소스연결을함께확인**

전송옵션뿐아니라대표요청의trace존재도검증합니다.

</details>

---

9. node 로그를 읽는 DaemonSet 권한은?
   - A) hostPID와모든capability항상허용
   - B) 정해진read-onlyhostmount·제한RBAC·명시한root예외만허용
   - C) 전체clusteradmin
   - D) hostlog경로는권한과무관

<details>
<summary>정답 보기</summary>

**정답: B) 정해진read-onlyhostmount·제한RBAC·명시한root예외만허용**

namespaceadmission과실제file권한을함께검증합니다.

</details>

---

10. 선택 backend와 durable queue의 설명은?
   - A) 모든backend가이미배포됨
   - B) 별도검증대상이며baseline은fileoffset/queue영속성을보장하지않는다
   - C) 재시작시유실/중복불가능
   - D) 24시간보존은30일SLO증거

<details>
<summary>정답 보기</summary>

**정답: B) 별도검증대상이며baseline은fileoffset/queue영속성을보장하지않는다**

실제설정과검증범위만성공으로기록합니다.

</details>

---

[본문으로 돌아가기](../../../labs/observability/02-observability-stack-lab.md)

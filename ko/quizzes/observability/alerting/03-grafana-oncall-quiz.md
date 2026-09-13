# Grafana OnCall 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

보관된 OnCall OSS의 기존 설치·이전 검토를 위한 퀴즈입니다.

Grafana OnCall에 대한 이해도를 테스트하는 퀴즈입니다.

**Cloud Connection도 2026-03-24에 종료되었습니다.** OSS 사용자의 Grafana IRM 모바일 앱 push와 Cloud Connection에 의존하는 SMS·음성 알림은 더 이상 동작하지 않습니다. 별도로 구성한 Twilio 또는 다른 알림 서비스는 별도 경로이며 모든 자체 호스팅 전화/SMS 방식이 종료됐다는 뜻은 아닙니다.

---

1. Grafana OnCall의 주요 기능이 아닌 것은?
   - A) 온콜 스케줄 관리
   - B) 에스컬레이션 체인 설정
   - C) 메트릭 수집 및 저장
   - D) ChatOps 통합 (Slack, Teams)

<details>
<summary>정답 보기</summary>

**정답: C) 메트릭 수집 및 저장**

**설명:**
OnCall은 알림·일정·라우팅·담당자 동작을 관리하며 메트릭 데이터베이스가 아닙니다. OSS는2026-03-24에 보관 처리되었고 기존 설치의 채널/API 사용 가능 여부는 유지보수되는 Cloud IRM과 별도로 확인합니다.

</details>

---

2. Grafana OnCall의 에스컬레이션 정책에서 `wait` 타입의 역할은?
   - A) 알림 전송 전 데이터 수집 대기
   - B) 다음 에스컬레이션 단계로 넘어가기 전 대기
   - C) 사용자 응답 대기 후 자동 해결
   - D) 알림 그룹화를 위한 대기

<details>
<summary>정답 보기</summary>

**정답: B) 다음 에스컬레이션 단계로 넘어가기 전 대기**

**설명:**
wait는 다음 에스컬레이션 단계로 진행하기 전 대기하며 사건을 확인하거나 해결하지 않습니다. 읽은 public serializer는 초 단위로1분~24시간 대기를 허용하고 중단·재호출은 chain과 alert-group 상태에 따릅니다.

</details>

---

3. Grafana OnCall에서 온콜 스케줄의 "오버라이드(Override)"란?
   - A) 스케줄을 완전히 삭제하고 새로 만드는 것
   - B) 특정 기간 동안 기존 스케줄의 담당자를 임시로 변경하는 것
   - C) 스케줄의 시간대를 변경하는 것
   - D) 로테이션 주기를 수정하는 것

<details>
<summary>정답 보기</summary>

**정답: B) 특정 기간 동안 기존 스케줄의 담당자를 임시로 변경하는 것**

**설명:**
override는 정한 기간의 담당 범위를 바꿉니다. 읽은 API에서는 on_call_shifts의 type이며 시간대와 대상 schedule 연결이 필요합니다. 기존 shift ID·우선순위·공백·최종 담당자를 확인하고 예전 중첩 overrides endpoint를 가정하지 않습니다.

</details>

---

4. Grafana OnCall과 Alertmanager를 통합할 때 사용하는 방식은?
   - A) Alertmanager가 OnCall의 메트릭을 직접 수집
   - B) Alertmanager의 webhook_configs를 통해 OnCall로 알림 전송
   - C) OnCall이 Alertmanager의 API를 주기적으로 폴링
   - D) 두 시스템이 데이터베이스를 공유

<details>
<summary>정답 보기</summary>

**정답: B) Alertmanager의 webhook_configs를 통해 OnCall로 알림 전송**

**설명:**
실제 integration 유형이 생성한 URL을 webhook_configs로 사용하고 적합하면 보호된 url_file에 둡니다. 참조 receiver를 모두 정의하고 current matchers를 사용합니다. Public API raw token 인증과 webhook URL은 별개이며 send_resolved가 OnCall에서 소스 규칙을 바꾸는 기능은 아닙니다.

</details>

---

5. Grafana OnCall의 알림 그룹화(Alert Grouping)의 주요 목적은?
   - A) 알림을 시간순으로 정렬
   - B) 관련된 여러 알림을 하나의 그룹으로 묶어 알림 피로 감소
   - C) 알림을 심각도별로 분류
   - D) 중복 알림을 자동으로 삭제

<details>
<summary>정답 보기</summary>

**정답: B) 관련된 여러 알림을 하나의 그룹으로 묶어 알림 피로 감소**

**설명:**
그룹화는 중복 대응을 줄일 수 있지만 사건 범위에 맞는 키가 필요합니다. 라벨이 부족하면 다른 사건을 합치고 무제한 ID는 그룹을 분산합니다. Alertmanager 타이머와 OnCall grouping/resolve template은 다르며 exactly-once 전달도 보장하지 않습니다.

</details>

---

6. Grafana OnCall의 에스컬레이션 정책에서 `notify_on_call_from_schedule`의 `important` 플래그가 true일 때의 동작은?
   - A) 알림을 최우선 순위로 표시
   - B) 사용자가 설정한 중요 알림 규칙 세트를 선택
   - C) 에스컬레이션 체인을 건너뛰고 즉시 상위자에게 알림
   - D) 알림을 영구 저장

<details>
<summary>정답 보기</summary>

**정답: B) 사용자가 설정한 중요 알림 규칙 세트를 선택**

**설명:**
Important는 사용자의 중요 알림 규칙 세트를 선택합니다. 설정한 순서·대기·채널·사용 가능 여부가 적용되며 모든 채널 자동 전송이 아닙니다. 기본 규칙도 항상 Slack만 사용하는 것은 아닙니다.

</details>

---

7. 기존 OnCall 설치에서 Slack 동작을 올바르게 사용하는 방법은?
   - A) 모든 설치가 /oncall ack를 지원한다고 가정
   - B) slash command를 Bash로 실행
   - C) 설치한 app의 명령·권한·동작 버튼 확인
   - D) 확인이 소스 모니터를 해결한다고 가정

<details>
<summary>정답 보기</summary>

**정답: C) 설치한 app의 명령·권한·동작 버튼 확인**

**설명:**
설치한 Slack app의 실제 root command/help와 권한 있는 버튼을 확인합니다. 읽은 source는 설정 가능한 root command와 /grafana 예시를 사용하며 기존 /oncall 명령 목록을 입증하지 않습니다. Acknowledge·Resolve·Silence는 다르고 배포 실행 기능이 자동으로 포함되지 않습니다.

</details>

---

8. 온콜 도구 도입·이전을 판단하는 적절한 기준은?
   - A) 과거 통합 수만 비교
   - B) OSS에는 운영비가 없다고 가정
   - C) 유지보수·필요 기능·실제 비용·이전/복구 검토
   - D) 보관된 OnCall OSS를 기본 설치

<details>
<summary>정답 보기</summary>

**정답: C) 유지보수·필요 기능·실제 비용·이전/복구 검토**

**설명:**
현재 유지보수·수명주기, 필요한 기능, 운영비·계약을 기준으로 비교합니다. 과거 통합 수·사용자당 가격만으로는 부족합니다. OnCall OSS는 보관 상태이며 Opsgenie는2027-04-05 서비스·지원 종료가 예정되어 있습니다. 유지보수되는 목적지와 이전·복구를 검증합니다.

</details>

---

9. 기존 OnCall 배포의 가용성을 위해 검증해야 하는 것은?
   - A) API 복제본3개면 가용성 보장
   - B) 종속성·상태·전달·장애·복구 동작
   - C) 클러스터 수만 확인
   - D) DB 읽기 복제본만 추가

<details>
<summary>정답 보기</summary>

**정답: B) 종속성·상태·전달·장애·복구 동작**

**설명:**
복제본 수만으로 모든 장애 지점이 사라지지 않습니다. 기존 설치는 종속성·broker/cache/DB·scheduler·키·TLS·전달·복구를 검증해야 합니다. 보관된 OSS를 신규 운영 기본값으로 삼지 않으며 이번 검토에서 HA 배포를 실행하지 않았습니다.

</details>

---

10. Grafana OnCall에서 라우트(Route)를 설정하는 주요 목적은?
    - A) 네트워크 트래픽 분산
    - B) 알림 조건에 따라 다른 에스컬레이션 체인 적용
    - C) 데이터베이스 쿼리 최적화
    - D) 사용자 인증 경로 설정

<details>
<summary>정답 보기</summary>

**정답: B) 알림 조건에 따라 다른 에스컬레이션 체인 적용**

**설명:**
라우트는 실제 integration payload·매칭 방식·순서·fallback으로 에스컬레이션/통보를 선택합니다. 읽은 serializer는 중첩 slack.channel_id/enabled를 사용합니다. 누락·충돌 필드를 시험하고 임의 메시지 정규식을 보편적 제공자 계약으로 취급하지 않습니다.

</details>

---

## 추가 학습 자료

- [Grafana OnCall Documentation](https://grafana.com/docs/oncall/latest/)
- [Grafana OnCall GitHub](https://github.com/grafana-cold-storage/oncall)
- [Grafana OnCall Helm Chart](https://github.com/grafana-cold-storage/oncall/tree/af0fbd40558c9a63bcf438589894c440fc434a54/helm/oncall)
- [Grafana IRM (Incident Response Management)](https://grafana.com/products/cloud/irm/)

- [가이드](../../../observability/alerting/03-grafana-oncall.md)

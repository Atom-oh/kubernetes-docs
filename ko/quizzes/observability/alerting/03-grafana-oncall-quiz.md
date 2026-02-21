# Grafana OnCall 퀴즈

Grafana OnCall에 대한 이해도를 테스트하는 퀴즈입니다.

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
Grafana OnCall은 온콜 관리 및 인시던트 대응 도구로, 다음 기능을 제공합니다:
- 온콜 스케줄 관리 (로테이션, 오버라이드)
- 에스컬레이션 체인 설정
- 알림 그룹화 및 라우팅
- ChatOps 통합 (Slack, MS Teams, Telegram)
- 모바일 앱 알림

메트릭 수집 및 저장은 Prometheus, Grafana Mimir 등 다른 도구의 역할입니다. OnCall은 이러한 도구에서 발생한 알림을 받아서 처리합니다.

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
에스컬레이션 체인에서 `wait` 타입은 현재 단계와 다음 단계 사이에 대기 시간을 설정합니다. 예를 들어:
1. Step 1: 현재 온콜 담당자에게 알림
2. Step 2: wait 900초 (15분)
3. Step 3: 응답이 없으면 2차 담당자에게 알림

이를 통해 1차 담당자가 응답할 시간을 주고, 응답이 없을 경우에만 에스컬레이션이 진행됩니다.

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
오버라이드는 정기적인 온콜 스케줄에서 특정 기간 동안 담당자를 임시로 변경하는 기능입니다. 주요 사용 사례:
- 휴가로 인한 담당자 대체
- 긴급 상황으로 인한 임시 변경
- 교육/미팅으로 인한 일시적 교체

오버라이드는 기존 스케줄을 유지하면서 특정 기간만 다른 담당자로 지정합니다.

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
Alertmanager와 Grafana OnCall 통합은 webhook을 통해 이루어집니다:
```yaml
receivers:
  - name: 'grafana-oncall'
    webhook_configs:
      - url: 'https://oncall.example.com/api/v1/webhook/<integration-id>/'
        send_resolved: true
```

Alertmanager가 알림을 발생시키면 설정된 webhook URL로 HTTP POST 요청을 보내고, OnCall이 이를 수신하여 처리합니다.

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
알림 그룹화는 동일한 문제로 인해 발생하는 여러 알림을 하나의 그룹으로 묶어 관리합니다. 예를 들어, 노드 장애로 인해 여러 파드에서 알림이 발생하면 이를 하나의 그룹으로 묶어 담당자가 수십 개의 개별 알림 대신 하나의 그룹화된 알림만 받게 됩니다. 그룹화 키(예: alertname + namespace)를 정의하여 어떤 알림을 함께 그룹화할지 결정합니다.

</details>

---

6. Grafana OnCall의 에스컬레이션 정책에서 `notify_on_call_from_schedule`의 `important` 플래그가 true일 때의 동작은?
   - A) 알림을 최우선 순위로 표시
   - B) 모든 설정된 채널(전화, SMS, 푸시 등)로 알림 전송
   - C) 에스컬레이션 체인을 건너뛰고 즉시 상위자에게 알림
   - D) 알림을 영구 저장

<details>
<summary>정답 보기</summary>

**정답: B) 모든 설정된 채널(전화, SMS, 푸시 등)로 알림 전송**

**설명:**
`important` 플래그의 의미:
- `important: true`: 사용자가 설정한 모든 알림 채널(전화, SMS, 모바일 푸시, Slack 등)로 알림 전송
- `important: false`: 기본 채널(예: Slack)로만 알림 전송

이를 통해 심각도에 따라 알림 강도를 조절할 수 있습니다. Critical 알림은 important=true로 설정하여 전화/SMS까지 전송하고, Warning은 important=false로 Slack만 사용하는 식으로 구성합니다.

</details>

---

7. Grafana OnCall에서 Slack 통합 시 사용할 수 있는 명령어가 아닌 것은?
   - A) /oncall ack (알림 확인)
   - B) /oncall resolve (알림 해결)
   - C) /oncall deploy (배포 실행)
   - D) /oncall silence 2h (2시간 무음)

<details>
<summary>정답 보기</summary>

**정답: C) /oncall deploy (배포 실행)**

**설명:**
Grafana OnCall의 Slack 명령어:
- `/oncall` - 현재 온콜 담당자 확인
- `/oncall schedule` - 스케줄 보기
- `/oncall ack` - 알림 확인(Acknowledge)
- `/oncall resolve` - 알림 해결
- `/oncall silence 2h` - 2시간 무음
- `/oncall unsilence` - 무음 해제
- `/oncall escalate` - 알림 에스컬레이션

배포 실행은 OnCall의 기능이 아닙니다. OnCall은 알림 관리 및 온콜 관리에 집중합니다.

</details>

---

8. Grafana OnCall과 PagerDuty/OpsGenie를 비교했을 때 OnCall의 장점이 아닌 것은?
   - A) 오픈소스로 자체 호스팅 가능
   - B) Grafana 스택과 네이티브 통합
   - C) 700개 이상의 통합 지원
   - D) 무료 사용 가능 (OSS 버전)

<details>
<summary>정답 보기</summary>

**정답: C) 700개 이상의 통합 지원**

**설명:**
700개 이상의 통합은 PagerDuty의 장점입니다. 비교:
- **Grafana OnCall**: 30+ 통합, 오픈소스, 자체 호스팅 가능, Grafana 네이티브 통합, 무료(OSS)
- **PagerDuty**: 700+ 통합, SaaS 전용, 고급 분석/보고, AIOps 기능
- **OpsGenie**: 200+ 통합, SaaS 전용, Atlassian 생태계 통합

OnCall은 Grafana 스택을 사용하는 환경에서 비용 효율적인 선택이지만, 다양한 외부 시스템 통합이 필요한 경우 PagerDuty가 더 적합할 수 있습니다.

</details>

---

9. Grafana OnCall의 프로덕션 배포에서 고가용성을 위해 권장되는 구성은?
   - A) 단일 인스턴스로 충분하다
   - B) API 서버와 Celery 워커의 복제본 수를 늘리고 외부 PostgreSQL/Redis 사용
   - C) 여러 클러스터에 분산 배포
   - D) 읽기 전용 복제본만 추가

<details>
<summary>정답 보기</summary>

**정답: B) API 서버와 Celery 워커의 복제본 수를 늘리고 외부 PostgreSQL/Redis 사용**

**설명:**
Grafana OnCall 프로덕션 HA 구성:
- **API 서버**: 3+ 복제본, Pod Anti-Affinity 설정
- **Celery 워커**: 3+ 복제본, Pod Anti-Affinity 설정
- **PostgreSQL**: 외부 관리형 DB (AWS RDS 등) 사용
- **Redis**: 외부 관리형 Redis (AWS ElastiCache 등) 사용

이렇게 구성하면 단일 장애 지점이 제거되고, 각 컴포넌트의 장애에도 서비스가 계속 동작합니다.

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
라우트는 들어오는 알림의 속성(라벨, 심각도, 팀 등)에 따라 적절한 에스컬레이션 체인으로 연결합니다:
- `severity=critical` → Critical 에스컬레이션 체인 (전화/SMS 포함)
- `team=infra` → 인프라 팀 에스컬레이션 체인
- `namespace=production` → 프로덕션 온콜 스케줄

라우팅 규칙은 정규식으로 정의하며, 알림 페이로드의 내용을 기반으로 매칭합니다. 이를 통해 알림 유형별로 적절한 담당자와 에스컬레이션 정책을 적용할 수 있습니다.

</details>

---

## 추가 학습 자료

- [Grafana OnCall Documentation](https://grafana.com/docs/oncall/latest/)
- [Grafana OnCall GitHub](https://github.com/grafana/oncall)
- [Grafana OnCall Helm Chart](https://github.com/grafana/helm-charts/tree/main/charts/oncall)
- [Grafana IRM (Incident Response Management)](https://grafana.com/products/cloud/irm/)

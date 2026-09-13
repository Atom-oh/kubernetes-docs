# Prometheus Alertmanager 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

---

1. Prometheus 알림 규칙에 양수 `for` 기간이 있을 때 Firing 전에 거치는 상태는?
   - A) Active
   - B) Pending
   - C) Warning
   - D) Waiting

<details>
<summary>정답 보기</summary>

**정답: B) Pending**

Pending은 Alertmanager의 평가 단계가 아니라 Prometheus 규칙 평가 상태입니다. 설정한 기간 동안 연속 평가에서 조건이 유지되어야 합니다. `for`가 없거나 0이면 첫 일치 평가에서 발화할 수 있습니다. 통지 그룹화에는 별도 지연이 있으며 `keep_firing_for`는 식이 더 이상 일치하지 않아도 Firing을 유지할 수 있습니다.

</details>

---

2. 그룹화 타이머에 대한 올바른 설명은?
   - A) `group_wait`는 새 그룹의 첫 통지까지 기다리는 시간이다.
   - B) `group_interval`은 변경 없는 알림의 반복 주기만 뜻한다.
   - C) `repeat_interval`은 새 알림의 최초 대기 시간이다.
   - D) 세 타이머는 모두 같다.

<details>
<summary>정답 보기</summary>

**정답: A) `group_wait`는 새 그룹의 첫 통지까지 기다리는 시간이다.**

`group_interval`은 변경·해결된 알림을 포함한 후속 그룹 검사 간격입니다. `repeat_interval`은 변경 없는 발화 알림의 반복 통지를 제어하며 그룹 간격마다 확인하므로 그 배수로 설정합니다. 통지 로그 보존 기간 때문에 더 일찍 반복될 수도 있습니다. Prometheus 규칙의 `for`와는 별개입니다.

</details>

---

3. Inhibition은 무엇을 하나요?
   - A) 일정 기간 모든 알림을 무시한다.
   - B) 일치하는 source가 활성 상태일 때 해당 target 통지를 억제한다.
   - C) 알림 심각도를 자동으로 바꾼다.
   - D) Prometheus에서 중복 알림을 삭제한다.

<details>
<summary>정답 보기</summary>

**정답: B) 일치하는 source가 활성 상태일 때 해당 target 통지를 억제한다.**

Inhibition은 기저 알림 조건이 아니라 통지 대상을 바꿉니다. Source/target matcher와 equal 레이블이 실제 의존 관계를 나타내야 합니다. 누락된 equal 레이블은 빈 값처럼 비교되므로 `cluster`·`node` 등 상관관계 레이블의 비어 있지 않음을 요구해야 무관한 알림 억제를 막을 수 있습니다. 규칙 배열 순서는 우선순위 체계가 아닙니다.

</details>

---

4. 아래 규칙의 `for`는 무엇을 의미하나요?

   ```yaml
   - alert: HighCPU
     expr: 100 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100 > 80
     for: 5m
     labels:
       severity: warning
   ```
   - A) CPU가 80%를 넘으면 즉시 통지한다.
   - B) 연속 평가에서 조건이 5분 유지된 후 Firing으로 전환한다.
   - C) CPU를 5분에 한 번만 평가한다.
   - D) 실제 CPU 증가 후 정확히 5분에 전달을 보장한다.

<details>
<summary>정답 보기</summary>

**정답: B) 연속 평가에서 조건이 5분 유지된 후 Firing으로 전환한다.**

Node exporter CPU counter 수집과 적절한 평가 간격을 가정합니다. `for`는 수집·평가 간격이나 통지 마감 시각을 정하지 않습니다. 레이블 집합이 바뀌면 다른 알림이며, 조건이 해제되면 Pending이 초기화됩니다. 별도의 발화 유지 설정도 확인해야 합니다. CrashLoop 예제는 먼저 5분 관측 window를 사용하고 `for: 10m`을 적용해 재시도 빈 구간을 연결하고 일회성 waiting을 제외합니다. 해제에는 lookback에 따른 지연이 있습니다.

</details>

---

5. `send_resolved: true`는 무엇을 활성화하나요?
   - A) 해당 통합의 해결 상태 통지.
   - B) 자동 복구 지침 생성.
   - C) 알림 조건을 정상으로 변경.
   - D) 수신자에게 클러스터 복구 권한 부여.

<details>
<summary>정답 보기</summary>

**정답: A) 해당 통합의 해결 상태 통지.**

선택한 통합의 resolved 통지를 제어하며 기본값은 수신자마다 다릅니다. Resolved는 알림 수명주기 상태이며 서비스 복구의 독립적인 증거는 아닙니다. 식 변경, 데이터 누락, 클라이언트 갱신·만료 동작도 상태에 영향을 줄 수 있습니다.

</details>

---

6. Alertmanager 클러스터 상태 동기화에 사용하는 프로토콜은?
   - A) Raft
   - B) Paxos
   - C) Gossip
   - D) gRPC

<details>
<summary>정답 보기</summary>

**정답: C) Gossip**

Gossip은 Silence와 통지 로그 상태를 최종적 일관성으로 공유합니다. 같은 알림을 모든 복제본에 보내야 하며 gossip이 이를 대신하지 않습니다. 중복 제거는 최선 노력 방식이고 네트워크 분할 시 중복이 생길 수 있습니다. Exactly-once 전달이나 모든 통지 손실 방지를 보장하지 않습니다.

</details>

---

7. 아래에서 `severity=critical, team=infra`이면 어떤 route가 선택되나요?

   ```yaml
   route:
     receiver: default
     routes:
       - matchers: ['severity="critical"']
         receiver: critical-receiver
       - matchers: ['team="infra"']
         receiver: infra-team
   ```
   - A) default
   - B) critical-receiver
   - C) infra-team
   - D) 두 하위 route 모두

<details>
<summary>정답 보기</summary>

**정답: B) critical-receiver**

기본 `continue: false`에서는 첫 일치 형제 route가 이후 형제 탐색을 중단합니다. 후속 형제를 보려면 해당 route에 `continue: true`를 설정합니다. 이는 레이블 라우팅만 보는 예제입니다. 비활성·mute route도 탐색을 중단할 수 있어 시간 조건은 별도 검증해야 합니다. 한 receiver 안의 여러 통합에는 `continue`가 필요하지 않습니다. Provider의 수신처 규칙도 적용됩니다. Slack incoming-webhook URL은 채널에 연결되므로 일반·critical 채널에는 channel 덮어쓰기 대신 서로 다른 webhook 파일·Secret 키가 필요합니다.

</details>

---

8. 네임스페이스가 소유한 AlertmanagerConfig로 무엇을 할 수 있나요?
   - A) 모든 네임스페이스 제약을 자동 우회한다.
   - B) Alertmanager 인스턴스가 선택하는 구조화된 route·receiver를 관리한다.
   - C) PromQL recording·alert 규칙을 정의한다.
   - D) Gossip peer 설정을 대체한다.

<details>
<summary>정답 보기</summary>

**정답: B) Alertmanager 인스턴스가 선택하는 구조화된 route·receiver를 관리한다.**

Operator가 객체 레이블과 네임스페이스를 선택해야 하며 참조 Secret도 필요한 네임스페이스에 있어야 합니다. Matcher strategy가 네임스페이스 적용을 제어합니다. 검토한 Operator 0.93.1 chart는 `v1alpha1`을 제공하므로 불필요한 API 업그레이드를 가정하지 않습니다. 전역 설정 사용은 별도 옵션이며 네임스페이스 레이블 매칭이 알림 전송자 인증은 아닙니다.

</details>

---

9. Silence의 적절한 목적이 아닌 것은?
   - A) 계획한 유지보수.
   - B) 기간을 제한한 조사.
   - C) 알림 규칙의 영구 비활성화.
   - D) 검토한 배포 시간대.

<details>
<summary>정답 보기</summary>

**정답: C) 알림 규칙의 영구 비활성화.**

Silence에는 유한한 종료 시각이 필요하며 통지에 영향을 줍니다. 만료는 억제 종료를 뜻하고 저장된 이력의 즉시 삭제는 아닙니다. 영구 규칙·라우팅 변경은 별도로 검토합니다. 소유자·이유·승인 범위를 기록하고 만료 알림은 명시적으로 구성한 워크플로가 필요합니다.

</details>

---

10. Go 템플릿 문법으로 유효하지 않은 식은?
   - A) `{{ .CommonLabels.alertname }}`
   - B) `{{ if eq .Status "firing" }}위험{{ end }}`
   - C) `{{ range .Alerts }}{{ .Labels.severity }}{{ end }}`
   - D) `{{ .Annotations.description | length > 100 ? substring(0, 100) : .Annotations.description }}`

<details>
<summary>정답 보기</summary>

**정답: D) `{{ .Annotations.description | length > 100 ? substring(0, 100) : .Annotations.description }}`**

Go 템플릿은 이 삼항식을 지원하지 않습니다. Alertmanager 최상위 Data에는 CommonLabels/CommonAnnotations가 있고 Labels/Annotations/StartsAt은 `range .Alerts` 안의 개별 Alert에 속합니다. 아래는 설명을 최대 100 rune으로 포맷하여 바이트 slice가 한글을 자르는 문제를 피합니다. 출력 포맷이며 민감 정보 제거 기능은 아닙니다.

```text
{{ range .Alerts }}
{{ printf "%.100s" .Annotations.description }}
{{ end }}
```

</details>

---

## 추가 학습 자료

- [Alertmanager 0.34 configuration](https://github.com/prometheus/alertmanager/blob/v0.34.0/docs/configuration.md)
- [Notification template reference](https://github.com/prometheus/alertmanager/blob/v0.34.0/docs/notifications.md)
- [Prometheus Operator alerting](https://prometheus-operator.dev/docs/developer/alerting/)

[본문으로 돌아가기](../../../observability/alerting/01-alertmanager.md)

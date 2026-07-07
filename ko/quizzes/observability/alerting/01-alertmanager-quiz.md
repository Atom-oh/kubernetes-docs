# Prometheus Alertmanager 퀴즈

Prometheus Alertmanager에 대한 이해도를 테스트하는 퀴즈입니다.

---

1. Alertmanager에서 알림이 발생(Firing)하기 전에 거치는 중간 상태는 무엇인가요?
   - A) Active
   - B) Pending
   - C) Warning
   - D) Waiting

<details>
<summary>정답 보기</summary>

**정답: B) Pending**

**설명:**
Prometheus 알림은 세 가지 상태를 가집니다: Inactive, Pending, Firing. 알림 규칙의 조건(expr)이 충족되면 먼저 Pending 상태로 전환되고, `for` 절에 지정된 기간 동안 조건이 지속되면 Firing 상태로 전환되어 Alertmanager로 전송됩니다. 이 메커니즘은 일시적인 스파이크로 인한 불필요한 알림을 방지합니다.

</details>

---

2. Alertmanager의 라우팅 설정에서 `group_wait`, `group_interval`, `repeat_interval`의 역할로 올바른 것은?
   - A) group_wait: 알림 그룹의 첫 번째 알림 전송 전 대기 시간
   - B) group_interval: 동일 알림의 반복 전송 간격
   - C) repeat_interval: 새로운 알림이 그룹에 추가될 때 대기 시간
   - D) 모두 같은 기능을 한다

<details>
<summary>정답 보기</summary>

**정답: A) group_wait: 알림 그룹의 첫 번째 알림 전송 전 대기 시간**

**설명:**
- `group_wait`: 새 알림 그룹이 생성된 후 첫 번째 알림을 보내기 전 대기하는 시간. 이 기간 동안 동일 그룹에 속하는 다른 알림들을 모아서 함께 전송합니다.
- `group_interval`: 같은 그룹에 새로운 알림이 추가되었을 때, 다음 알림 전송까지 대기하는 시간.
- `repeat_interval`: 이미 전송된 알림이 아직 해결되지 않았을 때, 동일한 알림을 다시 전송하는 간격.

</details>

---

3. Alertmanager의 Inhibition 기능에 대한 설명으로 올바른 것은?
   - A) 특정 시간 동안 모든 알림을 무시하는 기능
   - B) 특정 알림이 발생하면 관련된 다른 알림을 억제하는 기능
   - C) 알림의 심각도를 자동으로 낮추는 기능
   - D) 중복 알림을 병합하는 기능

<details>
<summary>정답 보기</summary>

**정답: B) 특정 알림이 발생하면 관련된 다른 알림을 억제하는 기능**

**설명:**
Inhibition(억제)은 특정 조건의 알림(source)이 발생했을 때 관련된 다른 알림(target)을 억제하는 기능입니다. 예를 들어, 노드가 다운되면 해당 노드의 모든 파드 관련 알림을 억제하여 알림 폭풍을 방지할 수 있습니다. Silencing은 특정 시간 동안 알림을 무시하는 별도의 기능입니다.

</details>

---

4. PrometheusRule CRD에서 다음 알림 규칙의 의미로 올바른 것은?
   ```yaml
   - alert: HighCPU
     expr: node_cpu_usage > 80
     for: 5m
     labels:
       severity: warning
   ```
   - A) CPU 사용량이 80%를 초과하면 즉시 알림 발생
   - B) CPU 사용량이 80%를 초과한 상태가 5분간 지속되면 알림 발생
   - C) 5분마다 CPU 사용량을 체크하여 80% 초과 시 알림 발생
   - D) CPU 사용량 80% 초과 알림을 5분 후에 전송

<details>
<summary>정답 보기</summary>

**정답: B) CPU 사용량이 80%를 초과한 상태가 5분간 지속되면 알림 발생**

**설명:**
`for: 5m` 설정은 알림 조건(expr)이 5분 동안 연속으로 충족되어야 Firing 상태로 전환된다는 의미입니다. 조건이 처음 충족되면 Pending 상태가 되고, 5분 동안 계속 충족되면 Firing으로 전환되어 Alertmanager로 전송됩니다. 이는 일시적인 스파이크로 인한 불필요한 알림을 방지합니다.

</details>

---

5. Alertmanager의 수신자(Receiver) 설정에서 `send_resolved: true`의 의미는?
   - A) 해결된 알림도 수신자에게 전송
   - B) 해결 방법을 알림 메시지에 포함
   - C) 알림을 해결 상태로 자동 변경
   - D) 수신자가 알림을 해결할 수 있는 권한 부여

<details>
<summary>정답 보기</summary>

**정답: A) 해결된 알림도 수신자에게 전송**

**설명:**
`send_resolved: true` 설정은 알림이 해결되었을 때(조건이 더 이상 충족되지 않을 때) 해결 알림(resolved notification)을 수신자에게 전송합니다. 이를 통해 담당자는 문제가 해결되었음을 알 수 있습니다. 기본값은 수신자 유형에 따라 다르며, 일반적으로 활성화하는 것이 권장됩니다.

</details>

---

6. Alertmanager 고가용성 구성에서 클러스터 멤버 간 상태를 동기화하는 데 사용되는 프로토콜은?
   - A) Raft
   - B) Paxos
   - C) Gossip
   - D) gRPC

<details>
<summary>정답 보기</summary>

**정답: C) Gossip**

**설명:**
Alertmanager 클러스터는 Gossip 프로토콜을 사용하여 멤버 간 상태를 동기화합니다. 이를 통해 Silence 정보와 알림 전송 기록(nflog)이 모든 인스턴스 간에 공유되어, 알림이 중복 전송되지 않도록 합니다. 클러스터 구성 시 `--cluster.peer` 플래그로 다른 멤버를 지정합니다.

</details>

---

7. 다음 Alertmanager 라우팅 설정에서 `severity=critical`이고 `team=infra`인 알림은 어느 수신자로 전송되나요?
   ```yaml
   route:
     receiver: 'default'
     routes:
       - match:
           severity: critical
         receiver: 'critical-receiver'
       - match:
           team: infra
         receiver: 'infra-team'
   ```
   - A) default
   - B) critical-receiver
   - C) infra-team
   - D) critical-receiver와 infra-team 모두

<details>
<summary>정답 보기</summary>

**정답: B) critical-receiver**

**설명:**
Alertmanager의 라우팅은 트리 구조로 동작하며, 기본적으로 첫 번째로 매칭되는 라우트에서 처리가 종료됩니다. 이 경우 `severity=critical` 조건이 먼저 매칭되므로 `critical-receiver`로 전송됩니다. 여러 라우트로 전송하려면 `continue: true` 설정이 필요합니다.

</details>

---

8. AlertmanagerConfig CRD의 주요 목적은?
   - A) Alertmanager의 전역 설정을 정의
   - B) 네임스페이스별로 알림 설정을 분리
   - C) Prometheus 알림 규칙을 정의
   - D) Alertmanager 클러스터 구성

<details>
<summary>정답 보기</summary>

**정답: B) 네임스페이스별로 알림 설정을 분리**

**설명:**
AlertmanagerConfig CRD는 Prometheus Operator에서 제공하는 리소스로, 네임스페이스별로 Alertmanager 설정(수신자, 라우트, 억제 규칙 등)을 분리하여 관리할 수 있게 합니다. 이를 통해 각 팀이 자신의 네임스페이스에서 알림 설정을 독립적으로 관리할 수 있습니다.

</details>

---

9. Alertmanager에서 Silence를 생성하는 주된 사용 사례로 적절하지 않은 것은?
   - A) 계획된 유지보수 작업 중 알림 억제
   - B) 알려진 이슈로 인한 반복 알림 방지
   - C) 영구적으로 특정 알림 비활성화
   - D) 배포 중 일시적 알림 억제

<details>
<summary>정답 보기</summary>

**정답: C) 영구적으로 특정 알림 비활성화**

**설명:**
Silence는 일시적으로 알림을 억제하는 기능으로, 반드시 종료 시간을 지정해야 합니다. 영구적으로 알림을 비활성화하려면 알림 규칙 자체를 수정하거나 삭제해야 합니다. Silence의 주요 사용 사례는 유지보수, 배포, 알려진 이슈 조사 중 등 일시적인 상황입니다.

</details>

---

10. 다음 중 Alertmanager 템플릿에서 사용할 수 있는 Go 템플릿 문법으로 올바르지 않은 것은?
    - A) <code v-pre>{{ .Labels.alertname }}</code>
    - B) <code v-pre>{{ if eq .Status "firing" }}위험{{ end }}</code>
    - C) <code v-pre>{{ range .Alerts }}{{ .Labels.severity }}{{ end }}</code>
    - D) <code v-pre>{{ .Annotations.description | length > 100 ? substring(0, 100) : .Annotations.description }}</code>

<details>
<summary>정답 보기</summary>

**정답: D) <code v-pre>{{ .Annotations.description | length > 100 ? substring(0, 100) : .Annotations.description }}</code>**

**설명:**
Go 템플릿은 삼항 연산자(`? :`)를 지원하지 않습니다. 대신 <code v-pre>{{ if }}</code>문을 사용해야 합니다. 올바른 문법은 다음과 같습니다:
```
{{ if gt (len .Annotations.description) 100 }}
  {{ slice .Annotations.description 0 100 }}...
{{ else }}
  {{ .Annotations.description }}
{{ end }}
```
Go 템플릿은 파이프(`|`), 조건문(`if`/`else`), 반복문(`range`), 내장 함수 등을 지원합니다.

</details>

---

## 추가 학습 자료

- [Prometheus Alerting Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [Alertmanager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)
- [Prometheus Operator - AlertmanagerConfig](https://prometheus-operator.dev/docs/user-guides/alerting/)

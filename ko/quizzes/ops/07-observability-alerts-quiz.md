# Observability 알림 설정 퀴즈

> **관련 문서**: [Observability 알림 설정](../../ops/07-observability-alerts.md)

## 객관식 문제

### 1. CPU Throttling을 탐지하기 위한 PromQL 메트릭은 무엇인가요?

- A) container_cpu_usage_seconds_total
- B) container_cpu_cfs_throttled_periods_total / container_cpu_cfs_periods_total
- C) node_cpu_seconds_total
- D) kube_pod_container_resource_limits

<details>
<summary>정답 보기</summary>

**정답: B) container_cpu_cfs_throttled_periods_total / container_cpu_cfs_periods_total**

**설명:**
CPU Throttling 비율은 `container_cpu_cfs_throttled_periods_total`(스로틀된 기간)을 `container_cpu_cfs_periods_total`(전체 기간)로 나누어 계산합니다. 이 비율이 높으면(예: 25% 이상) 컨테이너가 CPU limit에 의해 제한받고 있음을 의미하며, limit 증가를 고려해야 합니다.

</details>

### 2. Alertmanager의 group_wait 설정의 역할은 무엇인가요?

- A) 알림 재전송 간격
- B) 동일 그룹의 알림을 모아서 보내기 전 대기 시간
- C) 알림 만료 시간
- D) 알림 우선순위 설정

<details>
<summary>정답 보기</summary>

**정답: B) 동일 그룹의 알림을 모아서 보내기 전 대기 시간**

**설명:**
group_wait는 새로운 알림 그룹이 생성된 후 첫 번째 알림을 보내기 전에 대기하는 시간입니다. 이 기간 동안 동일 그룹의 다른 알림들이 도착하면 함께 묶어서 전송합니다. 이를 통해 알림 폭풍을 방지하고 관련 알림을 한 번에 확인할 수 있습니다.

</details>

### 3. 네트워크 패킷 드롭을 모니터링하기 위한 주요 메트릭은 무엇인가요?

- A) node_network_transmit_bytes_total
- B) node_network_receive_drop_total, node_network_transmit_drop_total
- C) container_network_receive_bytes_total
- D) kube_pod_status_phase

<details>
<summary>정답 보기</summary>

**정답: B) node_network_receive_drop_total, node_network_transmit_drop_total**

**설명:**
네트워크 패킷 드롭은 `node_network_receive_drop_total`(수신 드롭)과 `node_network_transmit_drop_total`(송신 드롭) 메트릭으로 모니터링합니다. 이 값이 증가하면 네트워크 버퍼 오버플로우, 대역폭 초과, 또는 네트워크 인터페이스 문제가 있을 수 있습니다.

</details>

### 4. PrometheusRule에서 'for' 필드의 역할은 무엇인가요?

- A) 알림 지속 시간
- B) 조건이 지정된 시간 동안 지속될 때만 알림 발생 (떨림 방지)
- C) 메트릭 수집 간격
- D) 알림 만료 시간

<details>
<summary>정답 보기</summary>

**정답: B) 조건이 지정된 시간 동안 지속될 때만 알림 발생 (떨림 방지)**

**설명:**
'for' 필드는 알림 조건이 지정된 시간 동안 연속으로 참일 때만 알림을 firing 상태로 전환합니다. 예를 들어 `for: 5m`이면 조건이 5분 동안 지속되어야 알림이 발생합니다. 이를 통해 일시적인 스파이크로 인한 불필요한 알림을 방지합니다.

</details>

### 5. 디스크 사용량 알림에서 predict_linear 함수를 사용하는 이유는 무엇인가요?

- A) 현재 사용량만 확인
- B) 현재 추세를 기반으로 미래 디스크 부족 시점을 예측
- C) 디스크 속도 측정
- D) 디스크 오류 감지

<details>
<summary>정답 보기</summary>

**정답: B) 현재 추세를 기반으로 미래 디스크 부족 시점을 예측**

**설명:**
predict_linear 함수는 지정된 기간의 메트릭 추세를 기반으로 미래 값을 예측합니다. 디스크 모니터링에서 `predict_linear(node_filesystem_avail_bytes[6h], 24*3600) < 0`은 현재 추세로 24시간 내 디스크가 부족할 것으로 예측되면 알림을 보냅니다. 이를 통해 사전에 조치할 수 있습니다.

</details>

### 6. Alertmanager의 inhibit_rules 기능의 용도는 무엇인가요?

- A) 알림 우선순위 설정
- B) 특정 알림이 활성화되면 관련된 다른 알림을 억제
- C) 알림 그룹화
- D) 알림 라우팅

<details>
<summary>정답 보기</summary>

**정답: B) 특정 알림이 활성화되면 관련된 다른 알림을 억제**

**설명:**
inhibit_rules는 상위 레벨 알림이 발생했을 때 하위 레벨 알림을 억제합니다. 예를 들어, 노드가 다운되면(NodeDown) 해당 노드의 Pod 관련 알림(PodNotReady)을 억제하여 알림 폭풍을 방지하고 근본 원인에 집중할 수 있게 합니다.

</details>

### 7. severity 레이블 값으로 일반적으로 사용되는 레벨이 아닌 것은 무엇인가요?

- A) critical
- B) warning
- C) info
- D) debug

<details>
<summary>정답 보기</summary>

**정답: D) debug**

**설명:**
알림의 severity 레벨로는 일반적으로 critical(즉각 대응 필요), warning(주의 필요), info(정보성)를 사용합니다. debug는 로그 레벨에서 사용되지만 알림 심각도로는 적합하지 않습니다. 각 레벨에 따라 다른 알림 채널(PagerDuty, Slack 등)로 라우팅할 수 있습니다.

</details>

### 8. Network Bandwidth 초과를 감지하기 위한 접근 방식은 무엇인가요?

- A) 패킷 수 카운트
- B) rate() 함수로 초당 바이트 전송량 계산 후 임계값 비교
- C) 연결 수 카운트
- D) DNS 쿼리 모니터링

<details>
<summary>정답 보기</summary>

**정답: B) rate() 함수로 초당 바이트 전송량 계산 후 임계값 비교**

**설명:**
네트워크 대역폭 사용량은 `rate(node_network_transmit_bytes_total[5m])`로 초당 바이트 전송량을 계산합니다. 이 값을 인스턴스 타입별 네트워크 대역폭 제한(예: c5.xlarge는 최대 10Gbps)과 비교하여 임계값 초과 시 알림을 발생시킵니다.

</details>

### 9. Prometheus 알림 규칙에서 annotations의 역할은 무엇인가요?

- A) 알림 조건 정의
- B) 알림의 설명, runbook URL 등 추가 정보 제공
- C) 알림 라우팅 결정
- D) 메트릭 필터링

<details>
<summary>정답 보기</summary>

**정답: B) 알림의 설명, runbook URL 등 추가 정보 제공**

**설명:**
annotations는 알림에 추가 정보를 제공합니다. summary(요약), description(상세 설명), runbook_url(대응 문서 링크) 등을 포함합니다. labels는 라우팅에 사용되고, annotations는 알림 메시지에 표시되어 운영자가 상황을 빠르게 파악하고 대응할 수 있게 합니다.

</details>

### 10. OOMKilled 이벤트를 모니터링하기 위한 메트릭은 무엇인가요?

- A) container_memory_usage_bytes
- B) kube_pod_container_status_last_terminated_reason
- C) node_memory_MemFree_bytes
- D) container_memory_cache

<details>
<summary>정답 보기</summary>

**정답: B) kube_pod_container_status_last_terminated_reason**

**설명:**
`kube_pod_container_status_last_terminated_reason` 메트릭은 컨테이너의 마지막 종료 이유를 나타냅니다. 이 메트릭에서 reason="OOMKilled"인 경우를 필터링하면 메모리 부족으로 종료된 컨테이너를 찾을 수 있습니다. OOMKilled가 발생하면 메모리 limit 증가나 메모리 누수 조사가 필요합니다.

</details>

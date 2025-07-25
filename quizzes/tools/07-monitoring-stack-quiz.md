# 모니터링 스택 퀴즈

이 퀴즈는 Kubernetes 모니터링 스택 (VictoriaMetrics, Prometheus, Grafana)에 대한 이해도를 테스트합니다.

## 문제 1: 모니터링 스택 구성 요소

<details>
<summary>Kubernetes 모니터링 스택의 주요 구성 요소와 역할은?</summary>

**답변:**
- **Prometheus**: 메트릭 수집 및 저장
- **VictoriaMetrics**: 고성능 시계열 데이터베이스
- **Grafana**: 메트릭 시각화 및 대시보드
- **Alertmanager**: 알림 관리 및 라우팅
- **Node Exporter**: 노드 레벨 메트릭 수집
- **kube-state-metrics**: Kubernetes 객체 상태 메트릭
- **cAdvisor**: 컨테이너 메트릭 수집
</details>

## 문제 2: Prometheus vs VictoriaMetrics

<details>
<summary>VictoriaMetrics가 Prometheus보다 나은 점은?</summary>

**답변:**
**VictoriaMetrics 장점:**
- **성능**: 더 빠른 쿼리 처리 및 데이터 압축
- **확장성**: 수평적 확장 지원 (클러스터 모드)
- **메모리 효율성**: 더 적은 메모리 사용량
- **스토리지 효율성**: 더 나은 데이터 압축
- **호환성**: PromQL 완전 호환
- **장기 저장**: 효율적인 장기 데이터 보관
- **다운샘플링**: 자동 데이터 다운샘플링
</details>

## 문제 3: 메트릭 수집 구성

<details>
<summary>Prometheus에서 Kubernetes 메트릭을 수집하는 구성 예시는?</summary>

**답변:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    
    scrape_configs:
    - job_name: 'kubernetes-apiservers'
      kubernetes_sd_configs:
      - role: endpoints
      scheme: https
      tls_config:
        ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
      bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
      relabel_configs:
      - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
        action: keep
        regex: default;kubernetes;https
    
    - job_name: 'kubernetes-nodes'
      kubernetes_sd_configs:
      - role: node
      relabel_configs:
      - action: labelmap
        regex: __meta_kubernetes_node_label_(.+)
    
    - job_name: 'kubernetes-pods'
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
```
</details>

## 문제 4: Grafana 대시보드

<details>
<summary>Kubernetes 클러스터 모니터링을 위한 주요 Grafana 대시보드는?</summary>

**답변:**
- **Kubernetes Cluster Monitoring (315)**: 전체 클러스터 개요
- **Kubernetes Pod Monitoring (747)**: 포드 레벨 메트릭
- **Node Exporter Full (1860)**: 노드 시스템 메트릭
- **Kubernetes Deployment Statefulset Daemonset (8588)**: 워크로드 메트릭
- **Kubernetes Networking (12114)**: 네트워크 메트릭
- **Kubernetes Persistent Volumes (13646)**: 스토리지 메트릭

**커스텀 대시보드 생성:**
```json
{
  "dashboard": {
    "title": "Custom Kubernetes Dashboard",
    "panels": [
      {
        "title": "CPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(container_cpu_usage_seconds_total[5m])",
            "legendFormat": "{{pod}}"
          }
        ]
      }
    ]
  }
}
```
</details>

## 문제 5: 알림 구성

<details>
<summary>Alertmanager를 사용한 알림 구성 예시는?</summary>

**답변:**
```yaml
# Prometheus 알림 규칙
groups:
- name: kubernetes-alerts
  rules:
  - alert: PodCrashLooping
    expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Pod {{ $labels.pod }} is crash looping"
      description: "Pod {{ $labels.pod }} in namespace {{ $labels.namespace }} is restarting frequently"

  - alert: NodeNotReady
    expr: kube_node_status_condition{condition="Ready",status="true"} == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Node {{ $labels.node }} is not ready"

---
# Alertmanager 구성
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@company.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
- name: 'web.hook'
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/...'
    channel: '#alerts'
    title: 'Kubernetes Alert'
    text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
```
</details>

## 문제 6: 성능 최적화

<details>
<summary>대규모 Kubernetes 클러스터에서 모니터링 스택을 최적화하는 방법은?</summary>

**답변:**
1. **메트릭 수집 최적화**:
   ```yaml
   # 불필요한 메트릭 제외
   metric_relabel_configs:
   - source_labels: [__name__]
     regex: 'go_.*|process_.*'
     action: drop
   ```

2. **샘플링 간격 조정**:
   ```yaml
   scrape_interval: 30s  # 기본 15s에서 증가
   ```

3. **VictoriaMetrics 클러스터 모드**:
   ```yaml
   # vmselect, vminsert, vmstorage 분리 배포
   ```

4. **데이터 보존 정책**:
   ```yaml
   # 단기: 고해상도 (1일)
   # 중기: 중간 해상도 (1주일)
   # 장기: 저해상도 (1년)
   ```

5. **리소스 할당**:
   ```yaml
   resources:
     requests:
       memory: "2Gi"
       cpu: "1000m"
     limits:
       memory: "4Gi"
       cpu: "2000m"
   ```

6. **스토리지 최적화**:
   - SSD 사용
   - 적절한 볼륨 크기
   - 백업 및 복구 전략
</details>

---

**점수 계산:**
- 5-6개 정답: 우수 (모니터링 스택 전문가 수준)
- 3-4개 정답: 양호 (추가 학습 권장)
- 1-2개 정답: 보통 (기본 개념 복습 필요)
- 0개 정답: 미흡 (전체 내용 재학습 필요)

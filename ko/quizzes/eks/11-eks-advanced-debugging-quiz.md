# Amazon EKS 고급 디버깅 퀴즈

이 퀴즈는 Amazon EKS의 고급 디버깅 기법, 인시던트 대응, 컨트롤 플레인 디버깅, 노드 문제 해결, kubectl debug, PromQL 쿼리, 관측성(Observability)에 대한 이해를 테스트합니다.

## 퀴즈 개요
- 인시던트 대응 프로세스
- EKS 컨트롤 플레인 디버깅
- 노드 및 kubelet 문제 해결
- kubectl debug 명령어 활용
- PromQL 쿼리 및 메트릭 분석
- 분산 추적 및 로그 분석

## 객관식 문제

### 1. EKS에서 API 서버 감사 로그(Audit Log)를 확인하려면 어디서 조회해야 하나요?

A. /var/log/kubernetes/ 디렉토리
B. Amazon CloudWatch Logs
C. etcd 데이터베이스
D. kubectl logs 명령어

<details>
<summary>정답 보기</summary>

**정답: B. Amazon CloudWatch Logs**

**설명:**
EKS 컨트롤 플레인 로그는 AWS에서 관리되며, CloudWatch Logs로 전송됩니다. 감사 로그는 `/aws/eks/<cluster-name>/cluster` 로그 그룹에서 확인할 수 있습니다.

**로그 유형:**
- `api`: API 서버 로그
- `audit`: 감사 로그
- `authenticator`: 인증 로그
- `controllerManager`: 컨트롤러 매니저 로그
- `scheduler`: 스케줄러 로그

```bash
# 컨트롤 플레인 로그 활성화
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# CloudWatch Logs Insights 쿼리
fields @timestamp, @message
| filter @logStream like /kube-apiserver-audit/
| filter @message like "403"
| sort @timestamp desc
| limit 100
```

</details>

### 2. kubectl debug 명령어로 실행 중인 Pod에 디버깅 컨테이너를 추가할 때 사용하는 플래그는?

A. --attach
B. --copy-to
C. --ephemeral
D. --sidecar

<details>
<summary>정답 보기</summary>

**정답: B. --copy-to**

**설명:**
`--copy-to` 플래그를 사용하면 기존 Pod의 복사본을 생성하고 디버깅 컨테이너나 수정된 설정을 추가할 수 있습니다. `--share-processes` 플래그와 함께 사용하면 프로세스 네임스페이스를 공유할 수 있습니다.

```bash
# 기존 Pod 복사본에 디버그 컨테이너 추가
kubectl debug myapp-pod --copy-to=myapp-debug --container=debugger --image=busybox -- sh

# 프로세스 네임스페이스 공유
kubectl debug myapp-pod --copy-to=myapp-debug --share-processes --container=debugger --image=busybox

# Ephemeral 컨테이너로 직접 디버깅 (Pod 복사 없이)
kubectl debug -it myapp-pod --image=busybox --target=myapp-container
```

**주요 옵션:**
- `--copy-to`: Pod 복사본 생성
- `--share-processes`: 프로세스 네임스페이스 공유
- `--target`: 타겟 컨테이너 지정 (ephemeral container용)

</details>

### 3. 노드가 NotReady 상태일 때 가장 먼저 확인해야 할 것은?

A. Pod 로그
B. kubelet 상태 및 로그
C. etcd 상태
D. CoreDNS 로그

<details>
<summary>정답 보기</summary>

**정답: B. kubelet 상태 및 로그**

**설명:**
노드가 NotReady 상태가 되는 가장 일반적인 원인은 kubelet 문제입니다. kubelet이 API 서버와 통신하지 못하면 노드 상태가 NotReady로 변경됩니다.

```bash
# 노드 상태 확인
kubectl describe node <node-name>

# 노드에 SSH 접속 후 kubelet 상태 확인
systemctl status kubelet

# kubelet 로그 확인
journalctl -u kubelet -f

# kubelet 재시작
sudo systemctl restart kubelet
```

**NotReady 원인 체크리스트:**
1. kubelet 프로세스 상태
2. 네트워크 연결 (API 서버 접근성)
3. 디스크 공간 부족
4. 메모리 부족 (OOM)
5. 컨테이너 런타임 상태

</details>

### 4. PromQL에서 최근 5분간 CPU 사용률이 80%를 초과한 Pod를 찾는 쿼리는?

A. `cpu_usage > 80`
B. `rate(container_cpu_usage_seconds_total[5m]) > 0.8`
C. `sum(rate(container_cpu_usage_seconds_total[5m])) by (pod) / sum(kube_pod_container_resource_limits{resource="cpu"}) by (pod) > 0.8`
D. `container_cpu_percent > 80`

<details>
<summary>정답 보기</summary>

**정답: C. `sum(rate(container_cpu_usage_seconds_total[5m])) by (pod) / sum(kube_pod_container_resource_limits{resource="cpu"}) by (pod) > 0.8`**

**설명:**
CPU 사용률은 실제 사용량을 limit으로 나눈 비율입니다. `rate()` 함수로 초당 CPU 사용량을 계산하고, limit으로 나누어 백분율을 구합니다.

```promql
# CPU 사용률 (limit 대비)
sum(rate(container_cpu_usage_seconds_total{container!=""}[5m])) by (pod, namespace)
/
sum(kube_pod_container_resource_limits{resource="cpu"}) by (pod, namespace)
* 100 > 80

# 메모리 사용률
sum(container_memory_working_set_bytes{container!=""}) by (pod, namespace)
/
sum(kube_pod_container_resource_limits{resource="memory"}) by (pod, namespace)
* 100 > 80

# 특정 네임스페이스의 CPU 사용량 Top 10
topk(10, sum(rate(container_cpu_usage_seconds_total{namespace="production"}[5m])) by (pod))
```

</details>

### 5. EKS에서 노드 간 네트워크 문제를 디버깅할 때 사용하는 도구로 적합하지 않은 것은?

A. tcpdump
B. wireshark
C. kubectl exec으로 ping/curl 테스트
D. etcdctl

<details>
<summary>정답 보기</summary>

**정답: D. etcdctl**

**설명:**
etcdctl은 etcd 데이터베이스를 관리하는 도구로, 네트워크 디버깅과는 관련이 없습니다. EKS에서는 etcd가 AWS에 의해 관리되므로 직접 접근할 수도 없습니다.

**네트워크 디버깅 도구:**
```bash
# tcpdump로 패킷 캡처
kubectl debug node/<node-name> -it --image=nicolaka/netshoot -- tcpdump -i eth0

# 노드 간 연결 테스트
kubectl debug node/<node-name> -it --image=nicolaka/netshoot -- ping <other-node-ip>

# Pod 내에서 네트워크 테스트
kubectl exec -it <pod-name> -- curl -v http://service-name

# DNS 테스트
kubectl exec -it <pod-name> -- nslookup kubernetes.default.svc.cluster.local
```

</details>

### 6. 인시던트 대응에서 MTTD(Mean Time To Detect)를 줄이기 위한 가장 효과적인 방법은?

A. 수동 모니터링 강화
B. 알림 임계값을 매우 낮게 설정
C. 적절한 알림 규칙과 자동화된 모니터링 시스템 구축
D. 로그 보관 기간 연장

<details>
<summary>정답 보기</summary>

**정답: C. 적절한 알림 규칙과 자동화된 모니터링 시스템 구축**

**설명:**
MTTD를 줄이려면 적절한 임계값의 알림 규칙과 자동화된 모니터링이 필요합니다. 너무 민감한 알림은 알림 피로(Alert Fatigue)를 유발합니다.

```yaml
# Prometheus AlertRule 예시
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: eks-alerts
spec:
  groups:
  - name: eks.rules
    rules:
    - alert: HighErrorRate
      expr: |
        sum(rate(http_requests_total{status=~"5.."}[5m]))
        / sum(rate(http_requests_total[5m])) > 0.05
      for: 2m
      labels:
        severity: critical
      annotations:
        summary: "High error rate detected"

    - alert: PodCrashLooping
      expr: |
        rate(kube_pod_container_status_restarts_total[15m]) > 0
      for: 5m
      labels:
        severity: warning
```

**MTTD 최적화 전략:**
- SLO 기반 알림 설정
- Multi-window burn rate 알림
- 알림 우선순위 분류
- On-call 로테이션 및 에스컬레이션

</details>

### 7. kubectl debug로 노드에 직접 디버깅 Pod를 생성하는 명령어는?

A. `kubectl debug node/<node-name> -it --image=busybox`
B. `kubectl exec node/<node-name> -- sh`
C. `kubectl attach node/<node-name>`
D. `kubectl run debug --node=<node-name>`

<details>
<summary>정답 보기</summary>

**정답: A. `kubectl debug node/<node-name> -it --image=busybox`**

**설명:**
Kubernetes 1.20+에서 `kubectl debug node/` 명령어를 사용하면 노드에 privileged Pod를 생성하여 호스트 파일시스템과 네트워크에 접근할 수 있습니다.

```bash
# 노드 디버깅
kubectl debug node/ip-10-0-1-100.ap-northeast-2.compute.internal -it --image=busybox

# 호스트 파일시스템 접근 (/host에 마운트됨)
# Pod 내에서:
chroot /host

# 더 많은 도구가 포함된 이미지 사용
kubectl debug node/<node-name> -it --image=nicolaka/netshoot

# 노드의 kubelet 로그 확인 (Pod 내에서)
journalctl -u kubelet --no-pager | tail -100
```

**주의사항:**
- 노드 디버깅 Pod는 privileged 모드로 실행됨
- 호스트 네임스페이스에 접근 가능
- 프로덕션 환경에서는 RBAC으로 접근 제한 필요

</details>

### 8. 분산 추적(Distributed Tracing)에서 Span의 의미는?

A. 전체 요청의 처리 시간
B. 단일 작업 단위의 시간 측정
C. 서비스 간 네트워크 지연
D. 로그 메시지의 타임스탬프

<details>
<summary>정답 보기</summary>

**정답: B. 단일 작업 단위의 시간 측정**

**설명:**
Span은 분산 시스템에서 하나의 작업 단위를 나타내며, 시작 시간, 종료 시간, 메타데이터를 포함합니다. 여러 Span이 모여 하나의 Trace를 구성합니다.

**분산 추적 개념:**
- **Trace**: 전체 요청 흐름을 나타내는 Span들의 집합
- **Span**: 단일 작업 단위 (예: HTTP 요청, DB 쿼리)
- **Parent-Child 관계**: Span 간의 호출 관계
- **Baggage**: Span 간 전파되는 컨텍스트 정보

```yaml
# OpenTelemetry Collector 설정
apiVersion: opentelemetry.io/v1alpha1
kind: OpenTelemetryCollector
metadata:
  name: otel-collector
spec:
  config: |
    receivers:
      otlp:
        protocols:
          grpc:
          http:
    processors:
      batch:
    exporters:
      jaeger:
        endpoint: jaeger-collector:14250
    service:
      pipelines:
        traces:
          receivers: [otlp]
          processors: [batch]
          exporters: [jaeger]
```

</details>

### 9. EKS에서 CoreDNS 문제를 디버깅할 때 가장 유용한 명령어는?

A. `kubectl logs -n kube-system -l k8s-app=kube-dns`
B. `kubectl describe service kubernetes`
C. `aws eks describe-cluster`
D. `kubectl get endpoints`

<details>
<summary>정답 보기</summary>

**정답: A. `kubectl logs -n kube-system -l k8s-app=kube-dns`**

**설명:**
CoreDNS Pod의 로그를 확인하면 DNS 쿼리 처리 상태, 오류, 타임아웃 등을 파악할 수 있습니다.

```bash
# CoreDNS 로그 확인
kubectl logs -n kube-system -l k8s-app=kube-dns -f

# CoreDNS Pod 상태 확인
kubectl get pods -n kube-system -l k8s-app=kube-dns

# CoreDNS ConfigMap 확인
kubectl get configmap coredns -n kube-system -o yaml

# DNS 테스트 Pod 생성
kubectl run dns-test --image=busybox:1.28 --rm -it --restart=Never -- nslookup kubernetes.default

# DNS 쿼리 디버깅
kubectl exec -it <pod-name> -- nslookup -debug kubernetes.default.svc.cluster.local
```

**CoreDNS 일반적인 문제:**
- Pod 리소스 부족 (CPU/Memory)
- ConfigMap 설정 오류
- 업스트림 DNS 연결 문제
- 클러스터 IP 서비스 연결 문제

</details>

### 10. kubectl을 사용하여 Pod의 리소스 사용량을 실시간으로 확인하는 명령어는?

A. `kubectl describe pod`
B. `kubectl top pods`
C. `kubectl get pods -o wide`
D. `kubectl logs`

<details>
<summary>정답 보기</summary>

**정답: B. `kubectl top pods`**

**설명:**
`kubectl top` 명령어는 Metrics Server가 수집한 리소스 사용량 데이터를 표시합니다. CPU와 메모리 사용량을 실시간으로 확인할 수 있습니다.

```bash
# 모든 네임스페이스의 Pod 리소스 사용량
kubectl top pods -A

# 특정 네임스페이스의 Pod
kubectl top pods -n production

# 컨테이너별 리소스 사용량
kubectl top pods --containers

# 노드 리소스 사용량
kubectl top nodes

# CPU 기준 정렬
kubectl top pods --sort-by=cpu

# 메모리 기준 정렬
kubectl top pods --sort-by=memory
```

**사전 요구사항:**
- Metrics Server 설치 필요
- `kubectl top`은 실시간 스냅샷만 제공 (히스토리 없음)
- 장기 모니터링은 Prometheus + Grafana 사용

</details>

## 단답형 문제

### 1. EKS 컨트롤 플레인 로그를 CloudWatch Logs에서 확인할 때 사용하는 로그 그룹 이름 패턴은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:** `/aws/eks/<cluster-name>/cluster`

**설명:**
EKS 컨트롤 플레인 로그는 자동으로 이 로그 그룹으로 전송됩니다.

```bash
# CloudWatch Logs Insights 쿼리 예시
# 로그 그룹: /aws/eks/my-cluster/cluster

# API 서버 에러 로그 검색
fields @timestamp, @message
| filter @logStream like /kube-apiserver/
| filter @message like /error|Error|ERROR/
| sort @timestamp desc
| limit 50

# 감사 로그에서 특정 사용자 활동 검색
fields @timestamp, @message
| filter @logStream like /kube-apiserver-audit/
| filter @message like /"user":.*"admin"/
| sort @timestamp desc
```

</details>

### 2. Kubernetes에서 Ephemeral Container를 활성화하는 데 필요한 feature gate 이름은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:** `EphemeralContainers` (Kubernetes 1.25+에서는 기본 활성화)

**설명:**
Kubernetes 1.23부터 beta, 1.25부터 GA(Generally Available)로 기본 활성화되어 있습니다. EKS 1.25 이상에서는 별도 설정 없이 사용 가능합니다.

```bash
# Ephemeral Container 추가
kubectl debug -it <pod-name> --image=busybox --target=<container-name>

# Ephemeral Container 확인
kubectl get pod <pod-name> -o jsonpath='{.spec.ephemeralContainers}'

# Pod에 추가된 Ephemeral Container 목록
kubectl describe pod <pod-name> | grep -A 10 "Ephemeral Containers"
```

</details>

### 3. PromQL에서 rate() 함수와 irate() 함수의 차이점은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:**
- `rate()`: 지정된 시간 범위 전체의 평균 변화율 계산 (smooth)
- `irate()`: 가장 최근 두 데이터 포인트만 사용하여 순간 변화율 계산 (volatile)

**사용 예시:**
```promql
# rate() - 5분간 평균 요청률 (알림, 대시보드에 적합)
rate(http_requests_total[5m])

# irate() - 순간 요청률 (급격한 변화 감지에 적합)
irate(http_requests_total[5m])

# CPU 사용률 - rate() 권장
rate(container_cpu_usage_seconds_total[5m])

# 스파이크 감지 - irate() 권장
irate(http_requests_total[1m]) > 1000
```

**선택 가이드:**
- 알림 규칙: `rate()` 사용 (노이즈 감소)
- 디버깅/급격한 변화 감지: `irate()` 사용
- 장기 트렌드 분석: `rate()` 사용

</details>

### 4. kubectl debug로 노드에 접속했을 때 호스트 파일시스템이 마운트되는 경로는 어디인가요?

<details>
<summary>정답 보기</summary>

**정답:** `/host`

**설명:**
`kubectl debug node/` 명령어로 생성된 Pod에서 호스트의 루트 파일시스템은 `/host`에 마운트됩니다.

```bash
# 노드 디버깅 Pod 생성
kubectl debug node/<node-name> -it --image=busybox

# Pod 내에서 호스트 파일시스템 접근
ls /host
cat /host/etc/kubernetes/kubelet/kubelet-config.json

# 호스트 환경으로 chroot
chroot /host

# chroot 후 호스트 명령어 실행
systemctl status kubelet
journalctl -u kubelet -n 100
```

</details>

### 5. 인시던트 대응에서 MTTR(Mean Time To Resolve)을 구성하는 두 가지 주요 요소는 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:**
1. **MTTD (Mean Time To Detect)**: 문제 발생부터 감지까지의 시간
2. **MTTI (Mean Time To Investigate/Identify)**: 문제 감지부터 원인 파악 및 해결까지의 시간

또는:
- MTTD + MTTI + MTTFix (실제 수정 시간)

**MTTR 개선 전략:**
```
MTTR = MTTD + MTTI + MTTFix

MTTD 개선:
- 효과적인 모니터링 및 알림
- SLO 기반 알림 설정

MTTI 개선:
- 런북(Runbook) 작성
- 자동화된 진단 도구

MTTFix 개선:
- 자동 복구 메커니즘
- 롤백 자동화
- GitOps 기반 배포
```

</details>

## 실습 문제

### 1. 다음 요구사항을 충족하는 PromQL 쿼리를 작성하세요.
- production 네임스페이스에서 최근 5분간 재시작된 컨테이너를 찾는 쿼리
- 재시작 횟수가 2회 이상인 것만 필터링

<details>
<summary>정답 보기</summary>

```promql
# 최근 5분간 재시작 횟수가 2회 이상인 컨테이너
increase(kube_pod_container_status_restarts_total{namespace="production"}[5m]) >= 2
```

**변형 쿼리:**
```promql
# 재시작 횟수와 함께 Pod 이름 표시
sum by (pod, container) (
  increase(kube_pod_container_status_restarts_total{namespace="production"}[5m])
) >= 2

# 전체 재시작 횟수 (누적)
kube_pod_container_status_restarts_total{namespace="production"} > 5

# 최근 1시간 동안 가장 많이 재시작된 Pod Top 10
topk(10,
  increase(kube_pod_container_status_restarts_total{namespace="production"}[1h])
)
```

**Grafana 대시보드용:**
```promql
# 시계열 그래프
rate(kube_pod_container_status_restarts_total{namespace="production"}[5m])

# 테이블 (현재 상태)
kube_pod_container_status_restarts_total{namespace="production"}
```

</details>

### 2. CrashLoopBackOff 상태의 Pod를 디버깅하는 단계별 명령어를 작성하세요.

<details>
<summary>정답 보기</summary>

```bash
# 1. Pod 상태 확인
kubectl get pods -n <namespace> | grep CrashLoopBackOff

# 2. Pod 상세 정보 확인 (이벤트 포함)
kubectl describe pod <pod-name> -n <namespace>

# 3. 이전 컨테이너 로그 확인 (크래시 전 로그)
kubectl logs <pod-name> -n <namespace> --previous

# 4. 현재 컨테이너 로그 확인
kubectl logs <pod-name> -n <namespace>

# 5. 컨테이너 시작 명령어 오버라이드하여 디버깅
kubectl debug <pod-name> -n <namespace> --copy-to=debug-pod \
  --container=<container-name> -- sleep infinity

# 6. 디버그 Pod에 접속
kubectl exec -it debug-pod -n <namespace> -- sh

# 7. 환경 변수 확인
kubectl exec -it debug-pod -n <namespace> -- env

# 8. 파일시스템 및 설정 확인
kubectl exec -it debug-pod -n <namespace> -- ls -la /app
kubectl exec -it debug-pod -n <namespace> -- cat /app/config.yaml

# 9. 디버그 완료 후 정리
kubectl delete pod debug-pod -n <namespace>
```

**일반적인 CrashLoopBackOff 원인:**
- 잘못된 설정 파일
- 누락된 환경 변수 또는 시크릿
- 리소스 부족 (OOM Kill)
- 헬스 체크 실패
- 의존성 서비스 연결 실패

</details>

### 3. CloudWatch Logs Insights를 사용하여 EKS 감사 로그에서 최근 1시간 동안 발생한 권한 거부(403) 이벤트를 조회하는 쿼리를 작성하세요.

<details>
<summary>정답 보기</summary>

```sql
# CloudWatch Logs Insights 쿼리
# 로그 그룹: /aws/eks/<cluster-name>/cluster

# 기본 403 에러 검색
fields @timestamp, @message
| filter @logStream like /kube-apiserver-audit/
| filter @message like /"responseStatus":\s*\{\s*"code":\s*403/
| sort @timestamp desc
| limit 100

# 상세 정보 파싱
fields @timestamp, @message
| filter @logStream like /kube-apiserver-audit/
| parse @message '"user":{"username":"*"}' as username
| parse @message '"verb":"*"' as verb
| parse @message '"resource":"*"' as resource
| parse @message '"responseStatus":{"code":*}' as statusCode
| filter statusCode = 403
| display @timestamp, username, verb, resource
| sort @timestamp desc
| limit 100

# 사용자별 403 에러 집계
fields @timestamp, @message
| filter @logStream like /kube-apiserver-audit/
| parse @message '"user":{"username":"*"}' as username
| parse @message '"responseStatus":{"code":*}' as statusCode
| filter statusCode = 403
| stats count(*) as errorCount by username
| sort errorCount desc
```

**AWS CLI를 통한 실행:**
```bash
aws logs start-query \
  --log-group-name "/aws/eks/my-cluster/cluster" \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @logStream like /kube-apiserver-audit/ | filter @message like /"code":403/ | sort @timestamp desc | limit 50'
```

</details>

## 심화 문제

### 1. 마이크로서비스 아키텍처에서 특정 API의 응답 시간이 간헐적으로 느려지는 문제가 발생했습니다. 분산 추적, 메트릭, 로그를 활용한 종합적인 디버깅 전략을 수립하세요.

<details>
<summary>정답 보기</summary>

**종합 디버깅 전략: 간헐적 지연 문제 분석**

**1단계: 문제 범위 파악 (Metrics)**

```promql
# P99 응답 시간 확인
histogram_quantile(0.99,
  sum(rate(http_request_duration_seconds_bucket{service="api-gateway"}[5m])) by (le, endpoint)
)

# 응답 시간 분포 확인 (히트맵용)
sum(rate(http_request_duration_seconds_bucket{service="api-gateway"}[1m])) by (le)

# 느린 요청 비율
sum(rate(http_request_duration_seconds_count{service="api-gateway"}[5m]))
-
sum(rate(http_request_duration_seconds_bucket{service="api-gateway",le="0.5"}[5m]))
```

**2단계: 분산 추적으로 병목 지점 식별**

```yaml
# Jaeger 쿼리 전략
# 1. 느린 트레이스 검색 (>2초)
service=api-gateway minDuration=2s

# 2. 에러가 포함된 트레이스
service=api-gateway tags={"error":"true"}

# 3. 특정 엔드포인트의 트레이스
service=api-gateway operation="GET /api/products"
```

**3단계: 로그 상관관계 분석**

```bash
# Trace ID로 관련 로그 검색
kubectl logs -l app=api-gateway | grep "trace_id=abc123"

# CloudWatch Logs Insights
fields @timestamp, @message
| filter @message like /trace_id=abc123/
| sort @timestamp asc
```

**4단계: 인프라 수준 분석**

```promql
# Pod CPU Throttling 확인
rate(container_cpu_cfs_throttled_seconds_total[5m])

# 네트워크 지연
rate(container_network_receive_bytes_total[5m])

# GC 영향 분석 (Java)
rate(jvm_gc_pause_seconds_sum[5m])
```

**5단계: 종합 대시보드**

```yaml
# Grafana 대시보드 구성
panels:
  - title: "Request Latency (P50, P95, P99)"
    query: histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

  - title: "Request Rate by Status"
    query: sum(rate(http_requests_total[5m])) by (status_code)

  - title: "Slow Requests Heatmap"
    query: sum(increase(http_request_duration_seconds_bucket[1m])) by (le)

  - title: "Downstream Service Latency"
    query: histogram_quantile(0.99, sum(rate(downstream_request_duration_seconds_bucket[5m])) by (le, service))

  - title: "Pod Resource Usage"
    queries:
      - container_cpu_usage_seconds_total
      - container_memory_working_set_bytes
```

**6단계: 자동화된 이상 탐지**

```yaml
# Prometheus AlertRule
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: latency-anomaly-detection
spec:
  groups:
  - name: latency.rules
    rules:
    - alert: LatencyAnomaly
      expr: |
        (
          histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service))
          -
          histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[1h])) by (le, service))
        )
        /
        histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[1h])) by (le, service))
        > 0.5
      for: 5m
      annotations:
        summary: "Latency increased by 50% compared to 1h average"
```

**결과 분석 체크리스트:**
- [ ] 특정 엔드포인트에서만 발생하는가?
- [ ] 특정 시간대에 집중되는가?
- [ ] 특정 다운스트림 서비스가 원인인가?
- [ ] 리소스 제한(CPU throttling)이 영향을 주는가?
- [ ] GC나 JVM 관련 문제인가?
- [ ] 네트워크 레벨 문제인가?

</details>

### 2. EKS 클러스터에서 노드가 간헐적으로 NotReady 상태가 되는 문제가 발생했습니다. 체계적인 근본 원인 분석(RCA) 프로세스와 재발 방지 대책을 수립하세요.

<details>
<summary>정답 보기</summary>

**근본 원인 분석 (RCA) 프로세스**

**Phase 1: 데이터 수집**

```bash
# 1. 노드 이벤트 히스토리 확인
kubectl get events --field-selector involvedObject.kind=Node --sort-by='.lastTimestamp'

# 2. 노드 상태 상세 확인
kubectl describe node <node-name> | grep -A 20 "Conditions:"

# 3. CloudWatch에서 노드 메트릭 확인
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name StatusCheckFailed \
  --dimensions Name=InstanceId,Value=<instance-id> \
  --start-time $(date -d '24 hours ago' -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Sum
```

**Phase 2: 시스템 로그 분석**

```bash
# 노드에 디버깅 Pod 배포
kubectl debug node/<node-name> -it --image=amazonlinux:2 -- bash

# chroot로 호스트 환경 접근
chroot /host

# 시스템 로그 확인
journalctl -u kubelet --since "24 hours ago" | grep -i "error\|fail\|timeout"
dmesg | tail -100

# 메모리/CPU 상태 확인
free -h
vmstat 1 5
cat /proc/pressure/memory
cat /proc/pressure/cpu
```

**Phase 3: 네트워크 분석**

```bash
# API 서버 연결 확인
curl -k https://kubernetes.default.svc.cluster.local/healthz

# VPC CNI 상태 확인
kubectl logs -n kube-system -l k8s-app=aws-node --tail=100

# ENI 및 IP 할당 상태
aws ec2 describe-network-interfaces \
  --filters Name=attachment.instance-id,Values=<instance-id>
```

**Phase 4: 리소스 압박 분석**

```promql
# 노드 메모리 압박
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 90

# 노드 디스크 압박
(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100 > 85

# 노드 PID 압박
node_processes_threads / node_processes_max_threads * 100 > 80
```

**Phase 5: 근본 원인 분류**

| 카테고리 | 가능한 원인 | 확인 방법 |
|---------|------------|----------|
| 리소스 | OOM Kill | `dmesg \| grep -i oom` |
| 리소스 | 디스크 풀 | `df -h` |
| 네트워크 | CNI 문제 | aws-node 로그 |
| 네트워크 | API 서버 연결 | curl healthz |
| 시스템 | kubelet 크래시 | `journalctl -u kubelet` |
| 인프라 | EC2 인스턴스 문제 | CloudWatch 메트릭 |

**Phase 6: 재발 방지 대책**

```yaml
# 1. 노드 문제 감지기 배포
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-problem-detector
  namespace: kube-system
spec:
  selector:
    matchLabels:
      app: node-problem-detector
  template:
    spec:
      containers:
      - name: node-problem-detector
        image: registry.k8s.io/node-problem-detector/node-problem-detector:v0.8.13
        securityContext:
          privileged: true
        volumeMounts:
        - name: log
          mountPath: /var/log
          readOnly: true
        - name: kmsg
          mountPath: /dev/kmsg
          readOnly: true
      volumes:
      - name: log
        hostPath:
          path: /var/log/
      - name: kmsg
        hostPath:
          path: /dev/kmsg
```

```yaml
# 2. 리소스 기반 알림
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: node-health-rules
spec:
  groups:
  - name: node.health
    rules:
    - alert: NodeMemoryPressure
      expr: |
        (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) > 0.85
      for: 5m
      labels:
        severity: warning

    - alert: NodeDiskPressure
      expr: |
        (1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes) > 0.85
      for: 5m
      labels:
        severity: warning

    - alert: NodeNotReady
      expr: |
        kube_node_status_condition{condition="Ready",status="true"} == 0
      for: 2m
      labels:
        severity: critical
```

```bash
# 3. 노드 자동 복구 설정 (Karpenter)
# Karpenter는 NotReady 노드를 자동으로 교체

# 4. kubelet 설정 최적화
# /etc/kubernetes/kubelet/kubelet-config.json
{
  "evictionHard": {
    "memory.available": "500Mi",
    "nodefs.available": "10%",
    "imagefs.available": "15%"
  },
  "evictionSoft": {
    "memory.available": "1Gi",
    "nodefs.available": "15%"
  },
  "evictionSoftGracePeriod": {
    "memory.available": "1m",
    "nodefs.available": "1m"
  }
}
```

**RCA 보고서 템플릿:**
```markdown
## 인시던트 요약
- 발생 시간: 2024-01-15 14:30 KST
- 영향 범위: 노드 3대, Pod 45개 영향
- 해결 시간: 2024-01-15 15:15 KST (MTTR: 45분)

## 타임라인
- 14:30 - 알림 발생: NodeNotReady
- 14:35 - 초기 분석 시작
- 14:50 - 근본 원인 식별: 메모리 압박으로 인한 kubelet OOM
- 15:00 - 노드 드레인 및 재시작
- 15:15 - 정상화 확인

## 근본 원인
메모리 누수가 있는 애플리케이션으로 인해 노드 메모리 고갈

## 재발 방지 대책
1. [완료] 문제 애플리케이션 메모리 limit 설정
2. [진행중] 노드 메모리 압박 알림 임계값 조정 (90% -> 80%)
3. [계획] Node Problem Detector 배포
```

</details>

# Part 9: Calico 운영 가이드

> **검토 기준**: Calico 3.32.2 / Operator 1.42.6 / Calico의 Kubernetes 테스트 범위 1.34–1.36.
> **마지막 업데이트**: 2026년 9월 12일

## 개요

이 문서에서는 Calico의 설치, 모니터링, 문제 해결, 업그레이드 및 백업/복구에 대한 운영 가이드를 제공합니다. 프로덕션 환경에서 Calico를 안정적으로 운영하기 위한 모범 사례를 다룹니다.

## 설치 가이드

플랫폼에 맞는 구성과 하나의 설치 소유 경로를 사용하세요. 다음 예제는 **전체 Calico CNI를 사용하는 새 자체 관리 Linux 클러스터**의 Iptables/VXLAN 구성입니다. 중복되지 않는 Pod CIDR, 호환 노드 OS/커널, Kubernetes API 접근, 대상 노드 사이 underlay UDP 4789 연결을 준비해야 합니다. VPC CNI policy-only 구성이 아니며 EKS는 [Part 8](08-eks-integration.md)을 사용하세요. 다른 overlay/BGP 설계는 [네트워킹 모드](03-networking-modes.md)를 먼저 검토하세요.

### Tigera Operator 매니페스트

Calico 3.32에서는 operator 매니페스트와 별도로 Calico CRD가 필요합니다.

```bash
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/v1_crd_projectcalico_org.yaml
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/tigera-operator.yaml
kubectl wait --for=condition=Available deployment/tigera-operator \
  -n tigera-operator --timeout=300s
```

다음을 `installation.yaml`로 저장하고 예제 Pod CIDR을 준비한 클러스터에 맞게 변경하세요. Operator의 자동 감지를 사용하려면 MTU를 생략합니다. 실제 경로 측정을 임의 MTU 값으로 대체하지 마세요.

```yaml
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  variant: Calico
  cni:
    type: Calico
  calicoNetwork:
    bgp: Disabled
    linuxDataplane: Iptables
    ipPools:
    - cidr: 10.244.0.0/16
      blockSize: 26
      encapsulation: VXLAN
      natOutgoing: Enabled
      nodeSelector: all()
    nodeAddressAutodetectionV4:
      kubernetes: NodeInternalIP
  nodeUpdateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
---
apiVersion: operator.tigera.io/v1
kind: APIServer
metadata:
  name: default
spec: {}
---
apiVersion: operator.tigera.io/v1
kind: Goldmane
metadata:
  name: default
spec: {}
---
apiVersion: operator.tigera.io/v1
kind: Whisker
metadata:
  name: default
spec: {}
```

```bash
kubectl apply -f installation.yaml
```

이 VXLAN 예제는 BGP를 비활성화합니다. 선택한 구성에서 BGP를 활성화한 경우에만 BGP 진단이 의미가 있습니다. Calico API 서버와 Goldmane/Whisker는 OSS 컴포넌트입니다. 현재 OSS flow log 가이드는 관측성 기능을 tech preview로 표시하므로 운영 의존성을 결정하기 전에 이 상태를 평가하세요.

측정으로 지원되는 override가 필요하다고 판단하기 전까지 컴포넌트 자원과 Typha 규모는 operator가 관리하도록 두세요. 임의 메모리 제한, 지원되지 않는 `typhaDeployment.spec.replicas`/`minReadySeconds`, 레거시 `componentResources` 목록의 `KubeControllers` 항목은 프로덕션 구성이 아닙니다. 버전별 Installation API와 [아키텍처](02-architecture.md), [확장](07-advanced-topics.md)을 참고하세요.

### 대안: Helm

Helm 차트는 같은 operator를 설치합니다. 다음을 `calico-values.yaml`로 저장하고 매니페스트로 두 번째 operator를 설치하는 대신 이 경로를 사용하세요.

```yaml
installation:
  enabled: true
  variant: Calico
  cni:
    type: Calico
  calicoNetwork:
    bgp: Disabled
    linuxDataplane: Iptables
    ipPools:
    - cidr: 10.244.0.0/16
      blockSize: 26
      encapsulation: VXLAN
      natOutgoing: Enabled
      nodeSelector: all()
    nodeAddressAutodetectionV4:
      kubernetes: NodeInternalIP
  nodeUpdateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
apiServer:
  enabled: true
goldmane:
  enabled: true
whisker:
  enabled: true
manageCRDs: true
```

```bash
helm repo add projectcalico https://docs.tigera.io/calico/charts
helm repo update projectcalico
helm template calico projectcalico/tigera-operator \
  --namespace tigera-operator --version v3.32.2 \
  -f calico-values.yaml > calico-rendered.yaml

# 준비한 클러스터와 렌더링 결과를 검토한 후에만 적용합니다.
helm install calico projectcalico/tigera-operator \
  --namespace tigera-operator --create-namespace --version v3.32.2 \
  -f calico-values.yaml
```

최상위 `podAnnotations`는 operator Pod에 적용됩니다. Felix 메트릭을 활성화하거나 모든 컴포넌트의 Prometheus 수집을 설정하지 않습니다. 아래 모니터링 절에서 명시적으로 설정하세요. `manageCRDs: true`에서는 operator가 시작 후 CRD를 관리합니다. 새 필드에 필요한 업그레이드 순서는 뒤에서 설명합니다.

### 대안: 직접 매니페스트

직접 매니페스트로 관리하는 기존 설치에는 일치하는 릴리스/구성을 사용하고 사용자 변경을 보존하세요. 다운로드한 파일을 적용 전에 검토합니다.

```bash
curl -fL https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/calico.yaml \
  -o calico.yaml
```

Pod CIDR과 활성 네트워킹 모드 등 실제 설정을 수정하세요. 전역 `sed` 치환은 예제나 주석만 바꾸고 실제 IP pool을 설정하지 않을 수 있습니다. `kube-system`의 직접 매니페스트 리소스와 `calico-system`의 operator 설치를 혼합하지 마세요.

### 설치 검증

```bash
kubectl get tigerastatus
kubectl get installation default -o yaml
kubectl rollout status daemonset/calico-node -n calico-system --timeout=300s
kubectl get pods -n calico-system -o wide
kubectl get nodes -o wide
```

직접 매니페스트 설치라면 실제 네임스페이스와 리소스 이름을 확인하세요. 컴포넌트 Ready만으로 정책 적용이나 애플리케이션 접근이 검증되지는 않습니다. Controller가 관리하는 워크로드로 필요한 Service/DNS 경로와 허용·거부 애플리케이션 연결을 모두 테스트하세요. API 접근을 확인할 때는 실제 API 서버 HTTPS 엔드포인트와 적절한 인증을 사용합니다. `kubernetes.default`에 대한 HTTP 요청은 인증된 API 상태 검사가 아닙니다.

## calicoctl 명령어 레퍼런스

공식 릴리스에서 일치하는 **3.32.2** 바이너리를 설치하고 [설치 장](01-introduction.md)의 방식으로 체크섬을 확인하세요. Linux AMD64/ARM64, macOS AMD64/ARM64, Windows AMD64 자산이 있으므로 실제 호스트 아키텍처를 선택합니다. PowerShell 다운로드 명령을 Bash에서 실행하거나 호환성 경고를 확인하지 않고 업그레이드 후 이전 클라이언트를 사용하지 마세요.

Kubernetes 데이터스토어에 접근하는 일반적인 Unix shell 설정은 다음과 같습니다.

```bash
export DATASTORE_TYPE=kubernetes
export KUBECONFIG="$HOME/.kube/config"
calicoctl version
calicoctl get nodes -o wide
calicoctl get networkpolicy -A
calicoctl get globalnetworkpolicy
calicoctl get tier
calicoctl get networkset -A
calicoctl get globalnetworkset
calicoctl get workloadendpoint -A
calicoctl get hostendpoint
calicoctl get ippool -o yaml
calicoctl get bgpconfiguration default -o yaml
calicoctl get bgppeer -o wide
calicoctl get felixconfiguration default -o yaml
```

Kubeconfig는 의도한 클러스터와 필요한 RBAC 권한을 선택해야 합니다. Calico API 설정 파일은 `--config`로 명시할 수 있습니다. `~/.config` 아래 임의 경로가 자동 탐색된다고 가정하지 마세요. 직접 etcdv3 데이터스토어에 접근할 때는 해당 배포의 지원 설정과 인증서 검증을 사용합니다. 별도 배포 방식이며 EKS 관리 etcd에 접근할 수 있다는 뜻은 아닙니다.

### 로컬 노드 진단

`calicoctl node status`는 **로컬 노드의 BGP 상태**를 보여줍니다. Kubeconfig가 있다고 원격 클러스터 전체 readiness 검사로 바뀌지는 않습니다. 문서화된 접근 조건으로 대상 노드에서 실행하거나 아래와 같이 해당 노드의 BIRD 소켓을 조회하세요.

`calicoctl node diags`는 선택한 노드에서 진단 아카이브를 수집합니다. 지원되는 `--log-dir`은 **입력 로그 디렉터리**이며 3.32.2에는 `--output-dir`이 없습니다. 구현은 root 권한을 요구하며 privileged 진단 컨테이너 실행과 Felix 상태 덤프 signal을 수행할 수 있습니다. 수동적 상태 프로브가 아닌 의도적인 근거 수집으로 취급하세요. 아카이브를 보호하고 명령이 출력하는 실제 경로를 사용합니다.

### Calico IPAM

주소를 **Calico IPAM**이 할당하는 경우에만 다음을 사용합니다. VPC CNI, host-local 등 다른 IPAM은 실제 할당자를 조사해야 합니다.

```bash
calicoctl ipam show
calicoctl ipam show --show-blocks
calicoctl ipam show --show-borrowed
calicoctl ipam show --show-configuration
calicoctl ipam show --ip=10.244.0.15
calicoctl ipam check --show-problem-ips -o ipam-report.json
```

`--show-blocks`는 블록 사용률을 보여줍니다. 블록과 노드의 연결은 BlockAffinity로 확인하며 Kubernetes Node PodCIDR과 동일하지 않습니다. `--ip`는 읽기 전용 할당 조회입니다. 보고서는 조사 후보를 제시하지만 Pod가 없다는 사실만으로 주소를 안전하게 해제할 수 있다고 판단해서는 안 됩니다.

검토한 CLI에는 `ipam release --block` 또는 `--handle`이 없습니다. 보고서 기반 해제에는 할당 sequence 검사가 있지만 [고급 IPAM](07-advanced-topics.md)의 정리 절차도 필요합니다. `ipam split NUMBER --cidr=...`는 실제 명령이지만 할당 블록이 아닌 **IP pool**을 분할하며 datastore lock과 2의 거듭제곱 분할 개수가 필요합니다. 멈춘 Pod의 일반적인 해결책이 아닌 계획된 마이그레이션 작업입니다.

### 리소스 변경과 내보내기

`get`, `create`, `apply`, `replace`, `patch`, `delete`는 지원 리소스 타입에 적용됩니다. 타입/네임스페이스를 명확히 하고 전체 정책을 검토하며 patch에서 다른 필드를 보존하세요. 예를 들어 로깅 변경은 기존 FelixConfiguration 또는 GitOps 소유 설정에 반영하며 새 필드만 있는 오브젝트로 교체하지 않습니다.

`calicoctl get all`은 모든 리소스의 백업이 아닙니다. 필요한 타입을 나열하고 Kubernetes 정책과 operator 리소스도 별도로 포함해야 합니다. `calicoctl get ... --export`는 존재하지만 검토한 CLI는 리소스 이름이 없으면 이 플래그를 무시합니다. 목록 내보내기를 완전하고 이식 가능한 재해 복구 백업으로 바꾸지는 않습니다. 아래 백업 절을 참고하세요.

## Prometheus 메트릭

**설치한 버전의 `/metrics` 출력**에서 이름, 타입, 레이블을 확인하세요. 데이터플레인별 series가 모든 구성에 존재한다고 보장할 수 없으며 누락은 0이 아닙니다. 아래 이름은 Calico 3.32.2 소스와 공식 메트릭 참조를 대조했습니다.

### 컴포넌트 메트릭 활성화

Felix 메트릭은 기본 비활성화이며 기본 포트는 **9091**입니다. Typha도 기본 비활성화이며 바이너리의 기본 메트릭 포트는 **9091**입니다. 이 operator 예제는 **9093**을 명시적으로 선택합니다. kube-controllers 메트릭은 기본적으로 **9094**에서 활성화됩니다.

기존 operator 설치에서는 설정 소유 경로에서 다음을 merge합니다.

```bash
kubectl patch felixconfiguration default --type=merge \
  -p '{"spec":{"prometheusMetricsEnabled":true,"prometheusMetricsPort":9091}}'
kubectl patch installation default --type=merge \
  -p '{"spec":{"typhaMetricsPort":9093}}'
kubectl get service calico-typha-metrics -n calico-system
kubectl get service calico-kube-controllers-metrics -n calico-system
```

`typhaMetricsPort`를 설정하면 operator가 Typha 메트릭 Service를 생성합니다. 충돌하는 Service로 교체하지 마세요. 직접 매니페스트 설치에는 자체 Typha 환경변수와 Service 설정이 필요합니다. 메트릭 접근을 제한해야 하며 host-network 엔드포인트에는 워크로드 NetworkPolicy 외의 호스트/네트워크 제어가 필요할 수 있습니다.

### 메트릭 이름과 의미

| 메트릭 | 타입 / 의미 |
| --- | --- |
| `felix_active_local_endpoints` | Gauge, 로컬 워크로드 **및 호스트** 엔드포인트 수, 0도 정상일 수 있어 readiness 검사가 아님 |
| `felix_active_local_policies` | Gauge, 해당 노드에서 활성인 정책 수, 합산하면 클러스터 고유 정책 수가 아닌 노드별 정책 인스턴스 수 |
| `felix_cluster_num_hosts`, `felix_cluster_num_policies` | 각 Felix가 관측한 클러스터 범위 Gauge, 노드별 같은 값을 합산하지 않음 |
| `felix_int_dataplane_failures` | Counter, 재시도할 데이터플레인 업데이트 실패, 검토한 이름에는 `_total` 접미사 없음 |
| `felix_int_dataplane_apply_time_seconds` | 증분 업데이트 시간의 **Summary**, histogram bucket 대신 quantile·`_sum`·`_count` 제공 |
| `felix_iptables_restore_calls`, `felix_iptables_restore_errors` | iptables 데이터플레인의 iptables-restore 호출/오류 Counter |
| `felix_log_errors`, `felix_logs_dropped` | 프로세스 로그 출력 오류/출력 막힘으로 버린 로그, ERROR 레벨 항목이나 거부 패킷 개수가 아님 |
| `typha_connections_active` | Gauge, handshake 중인 연결을 포함한 열린 연결 |
| `typha_connections_streaming{syncer="..."}` | Gauge, handshake를 마치고 streaming 중인 클라이언트 |
| `typha_connections_accepted` | Counter, 수락한 연결 수 |
| `typha_connections_dropped` | **재분배를 위해** 끊은 연결 Counter, 일반적인 네트워크 실패 개수가 아님 |
| `typha_cache_size{syncer="..."}` | Gauge, 캐시의 key/value 항목 수 |
| `typha_updates_total{syncer="..."}` | 데이터스토어 syncer로부터 **받은** 업데이트 Counter |
| `ipam_allocations_in_use{ippool="...",node="..."}` | kube-controllers Gauge, 워크로드/인터페이스에 할당된 Calico IPAM 주소 |
| `ipam_ippool_size{ippool="..."}` | kube-controllers Gauge, pool CIDR 전체 주소 수 |
| `ipam_allocations_gc_candidates` | 조사 중인 잠재적 누수, 주소 해제 허가가 아님 |

BIRD 제어 소켓은 Prometheus exporter가 아닙니다. `bird_protocol_up`, `calico_bgp_peer_status` 같은 이름은 레이블과 의미를 검증한 별도 exporter/collector가 필요하며 이 설치가 해당 series를 제공하지 않습니다. 아래 BGP 진단 또는 [CalicoNodeStatus 방식](04-bgp-deep-dive.md)을 사용하고 실제 출력 확인 후에만 exporter 알람을 추가하세요.

### ServiceMonitor 연결

Prometheus Operator CRD와 `monitoring` 네임스페이스가 이미 있다고 가정합니다. ServiceMonitor 레이블을 Prometheus의 `serviceMonitorSelector`에 맞추고 `serviceMonitorNamespaceSelector`가 해당 네임스페이스를 포함하는지 확인하세요. PrometheusRule 레이블도 `ruleSelector`와 일치해야 합니다. 스키마가 유효해도 선택되지 않은 리소스에서는 수집/규칙이 생성되지 않습니다.

아래 **별도 Service**는 operator 소유 Service를 변경하지 않고 모두 `http-metrics`라는 포트 이름을 제공합니다. 이미 해당 엔드포인트를 수집한다면 중복 scrape를 추가하지 말고 기존 설정을 사용하세요. ServiceMonitor의 `jobLabel`이 아래 쿼리에서 사용하는 `calico-felix`, `calico-typha`, `calico-kube-controllers` job을 만듭니다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: calico-audit-felix-metrics
  namespace: calico-system
  labels:
    audit.calico/component: calico-felix
spec:
  clusterIP: None
  selector:
    k8s-app: calico-node
  ports:
  - name: http-metrics
    port: 9091
    targetPort: 9091
    protocol: TCP
---
apiVersion: v1
kind: Service
metadata:
  name: calico-audit-typha-metrics
  namespace: calico-system
  labels:
    audit.calico/component: calico-typha
spec:
  clusterIP: None
  selector:
    k8s-app: calico-typha
  ports:
  - name: http-metrics
    port: 9093
    targetPort: 9093
    protocol: TCP
---
apiVersion: v1
kind: Service
metadata:
  name: calico-audit-kube-controllers-metrics
  namespace: calico-system
  labels:
    audit.calico/component: calico-kube-controllers
spec:
  clusterIP: None
  selector:
    k8s-app: calico-kube-controllers
  ports:
  - name: http-metrics
    port: 9094
    targetPort: 9094
    protocol: TCP
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: calico-components
  namespace: monitoring
  labels:
    app.kubernetes.io/part-of: calico-monitoring
spec:
  jobLabel: audit.calico/component
  selector:
    matchExpressions:
    - key: audit.calico/component
      operator: Exists
  namespaceSelector:
    matchNames:
    - calico-system
  endpoints:
  - port: http-metrics
    interval: 30s
    scrapeTimeout: 10s
    path: /metrics
```

엔드포인트 탐색/RBAC, 네트워크 접근, Prometheus Targets 화면을 확인하세요. ServiceMonitor의 `endpoints.port`는 컨테이너 포트 번호가 아닌 **Service 포트 이름**을 선택합니다. 부하 분산되는 Service 주소 하나를 수집하며 모든 노드를 수집한다고 가정하지 말고 개별 탐색 target을 확인하세요.

## Grafana 대시보드

설정한 Prometheus datasource와 현재 time-series/stat 패널을 사용합니다. 다음은 완성된 import용 대시보드가 아닌 패널 쿼리입니다. 하나의 클러스터 메트릭을 선택해야 하며 여러 클러스터를 모은 datasource는 selector와 집계에 cluster 레이블을 유지해야 합니다.

| 패널 | PromQL |
| --- | --- |
| 노드별 엔드포인트 | `felix_active_local_endpoints{job="calico-felix"}` |
| 노드별 활성 정책 | `felix_active_local_policies{job="calico-felix"}` |
| 관측한 클러스터 정책 수 | `max(felix_cluster_num_policies{job="calico-felix"})` |
| 초당 데이터플레인 재시도 | `rate(felix_int_dataplane_failures{job="calico-felix"}[5m])` |
| Typha streaming 연결 | `typha_connections_streaming{job="calico-typha"}` |
| 로컬 summary p99 | `felix_int_dataplane_apply_time_seconds{job="calico-felix",quantile="0.99"}` |

프로세스별 Summary quantile은 클러스터 전체 p99가 아니며 `histogram_quantile`로 합칠 수 없습니다. 업데이트가 발생하는 구간의 평균 증분 적용 시간은 다음과 같습니다.

```promql
rate(felix_int_dataplane_apply_time_seconds_sum{job="calico-felix"}[5m])
/ rate(felix_int_dataplane_apply_time_seconds_count{job="calico-felix"}[5m])
```

관측값이 없으면 평균은 정의되지 않으며(`0/0`) 지연 0의 근거가 아닙니다. 이 Summary에 존재하지 않는 `_bucket` series를 만들거나 검증되지 않은 `felix_iptables_restore_time_seconds` 쿼리를 유지하지 마세요. 실제 제공하는 작업 Counter와 데이터플레인 시간 메트릭을 사용합니다.

Calico IPAM 주소 사용률은 다음과 같이 볼 수 있습니다.

```promql
sum by (ippool) (
  max by (ippool, node) (ipam_allocations_in_use{job="calico-kube-controllers",ippool!="no_ippool"})
)
/ max by (ippool) (ipam_ippool_size{job="calico-kube-controllers",ippool!="no_ippool"})
```

pool/node별 `max`로 컨트롤러의 같은 관측값 중복을 피한 뒤 노드별 할당량을 합산합니다. **주소 사용률**이며 블록 소비율이나 특정 노드의 실제 할당 가능 용량을 보장하지 않습니다. Pool selector, strict affinity, 블록 상한, 예약/tunnel 주소 등도 확인해야 합니다. VPC CNI 할당량을 설명하는 메트릭이 아니며 비어 있거나 누락된 series, 용량 0은 별도 조사 대상입니다.

## Alert 규칙

예제는 위 job, 하나의 선택한 클러스터, DaemonSet 메트릭을 위한 kube-state-metrics를 전제로 합니다. 실제 실행해야 하는 컴포넌트에만 target 누락 규칙을 활성화하세요. 기존 모니터링을 재사용하면 selector를 조정하고 임계값·지속시간은 워크로드에 맞게 설정합니다.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: calico-alerts
  namespace: monitoring
  labels:
    app.kubernetes.io/part-of: calico-monitoring
spec:
  groups:
  - name: calico.rules
    rules:
    - alert: CalicoDaemonSetUnavailable
      expr: kube_daemonset_status_number_unavailable{namespace="calico-system",daemonset="calico-node"}
        > 0
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: Calico DaemonSet has unavailable Pods
        description: Inspect the affected node, rollout and kube-state-metrics data.
    - alert: CalicoMetricsScrapeFailed
      expr: up{job=~"calico-(felix|typha|kube-controllers)"} == 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Calico scrape failed for {{ $labels.job }} on {{ $labels.instance
          }}
    - alert: CalicoMetricsTargetsMissing
      expr: |-
        absent(up{job="calico-felix"})
        or absent(up{job="calico-typha"})
        or absent(up{job="calico-kube-controllers"})
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: No discovered metrics targets for {{ $labels.job }}
    - alert: CalicoDataplaneRetries
      expr: rate(felix_int_dataplane_failures{job="calico-felix"}[5m]) > 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Dataplane updates are being retried on {{ $labels.instance }}
    - alert: CalicoDataplaneMeanSlow
      expr: |-
        (rate(felix_int_dataplane_apply_time_seconds_sum{job="calico-felix"}[5m])
        / rate(felix_int_dataplane_apply_time_seconds_count{job="calico-felix"}[5m])) > 0.5
        and (rate(felix_int_dataplane_apply_time_seconds_count{job="calico-felix"}[5m]) > 0)
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Mean dataplane update time exceeds 0.5s on {{ $labels.instance }}
    - alert: CalicoIPAMHighAddressUsage
      expr: |-
        (sum by (ippool) (
          max by (ippool, node) (ipam_allocations_in_use{job="calico-kube-controllers",ippool!="no_ippool"})
        )
        / max by (ippool) (ipam_ippool_size{job="calico-kube-controllers",ippool!="no_ippool"})) > 0.8
        and on (ippool)
        (max by (ippool) (ipam_ippool_size{job="calico-kube-controllers",ippool!="no_ippool"}) > 0)
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: High address utilization in Calico IP pool {{ $labels.ippool }}
        description: Address utilization is {{ $value | humanizePercentage }}; inspect
          per-node eligibility and block constraints.
```

`up == 0`은 탐색된 target의 scrape 실패를 감지하지만 target 자체가 사라지면 감지하지 못합니다. `absent` 규칙은 예상 컴포넌트의 **모든** target이 사라진 경우를 감지합니다. 정상 노드 사이에서 한 노드만 누락된 상황은 기대 노드/DaemonSet 목록과 비교해야 합니다. 메트릭이나 규칙이 로드되지 않았다면 알람이 보이지 않는다고 정상이라고 판단할 수 없습니다.

Typha 연결 감소나 재분배 Counter 증가는 확장 중 정상적으로 발생할 수 있습니다. 지속되는 streaming/client 지연과 컴포넌트 가용성을 함께 보고 장애를 판단하세요. 로컬 엔드포인트 수 0도 Felix unready를 뜻하지 않습니다. 실제 readiness/rollout 상태와 별도 합성 허용·거부 테스트를 사용하세요.

## 로그 분석과 트러블슈팅

### 영향받은 워크로드와 노드부터 확인

Pending Pod는 CNI 호출 전에 스케줄링에서 막혔을 수 있습니다. 먼저 이벤트와 `spec.nodeName`을 확인하세요. CNI/IP 할당 오류라면 실제 할당자를 식별하고 해당 노드의 kubelet/CNI 로그를 조사합니다. 모든 Pod IPAM 오류가 Felix 프로세스 로그에 있는 것은 아닙니다.

```bash
CALICO_NAMESPACE=calico-system
WORKLOAD_NAMESPACE=calico-demo
WORKLOAD_POD=replace-with-actual-pod

kubectl describe pod "$WORKLOAD_POD" -n "$WORKLOAD_NAMESPACE"
CALICO_NODE=$(kubectl get pod "$WORKLOAD_POD" -n "$WORKLOAD_NAMESPACE" \
  -o jsonpath='{.spec.nodeName}')
test -n "$CALICO_NODE" || { echo "Pod is not scheduled to a node" >&2; exit 1; }
kubectl get pods -n "$CALICO_NAMESPACE" -l k8s-app=calico-node \
  --field-selector "spec.nodeName=$CALICO_NODE" -o wide

# Rollout 중에도 이 노드의 실제 에이전트 Pod를 선택합니다.
CALICO_POD=replace-with-actual-calico-node-pod
kubectl logs -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node \
  --since=15m --tail=200 --timestamps
```

시간 범위와 tail 제한을 명시하세요. Selector를 사용하면 `kubectl logs`의 기본 tail이 짧을 수 있으므로 시간 범위를 지정했다고 그 구간의 모든 로그를 받았다고 가정하면 안 됩니다. 컨테이너가 재시작했다면 가능한 경우 이전 로그도 확인합니다. 조회 오류를 “오류 없음”으로 바꾸지 말고 보존하세요.

Felix 프로세스 로그는 규칙 설정과 컴포넌트 동작을 설명합니다. `logSeverityScreen`을 Debug로 바꿔도 패킷별 정책 결정 로그가 생성되지는 않습니다. 임시 변경 전에 기존 필드 값과 설정 소유자를 기록하고, 이전 값이 Info였다고 가정하지 말고 정확한 값 또는 필드 부재를 복원하세요. 파일/syslog 출력도 설정 경로와 런타임에 따라 달라집니다.

### 주소 할당과 연결

| 증상 | 상태 변경 전에 확인할 사항 |
| --- | --- |
| 스케줄링된 노드 없음 | Scheduler 이벤트, 용량, affinity, taint 확인, 아직 IPAM 진단 단계가 아님 |
| CNI 할당 실패 | 실제 할당자 로그, pool/주소 용량, selector 적격성, 블록/affinity 제한, API 접근 |
| Pod IP는 연결되지만 Service 실패 | Endpoints/EndpointSlices, Service 포트, kube-proxy 또는 BPF Service 처리, DNS, 정책 |
| 작은 패킷만 성공 | Underlay/overlay MTU, fragmentation/PMTUD, 반환 경로 |
| 정책이 의도대로 차단하지 않음 | 실제 엔드포인트 identity/레이블, 방향, namespace selector, tier/order, 앞선 allow, host-network/추가 인터페이스 제약, 기존 연결 |

```bash
kubectl exec -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node -- ip route show
kubectl exec -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node -- ip -d link show
calicoctl get networkpolicy -n "$WORKLOAD_NAMESPACE" -o yaml
calicoctl get globalnetworkpolicy -o yaml
calicoctl get tier -o yaml
calicoctl get workloadendpoint -n "$WORKLOAD_NAMESPACE" -o yaml
kubectl get pod "$WORKLOAD_POD" -n "$WORKLOAD_NAMESPACE" --show-labels
```

클러스터의 첫 번째 `calico-node` Pod를 골라 문제가 있는 워크로드의 노드라고 가정하지 마세요. ICMP 성공/실패만으로 TCP나 HTTP 정책이 검증되지는 않습니다. 도구가 확인된 승인 진단 워크로드와 애플리케이션의 실제 프로토콜/포트를 사용하세요.

Calico IPAM에서는 위의 읽기 전용 명령과 [IPAM 정리 절차](07-advanced-topics.md)를 사용합니다. Pool CIDR과 blockSize는 변경할 수 없습니다. 겹치지 않는 적격 pool 추가는 계획된 용량 변경이며 기존 CIDR의 직접 확장이 아닙니다. 원인을 확인하기 전에 주소를 해제하거나 에이전트를 재시작하지 마세요.

Operator 설치의 MTU와 주소 자동 감지는 `Installation.spec.calicoNetwork`에 설정하며 문서화된 경우 터널별 Felix 필드를 사용합니다. `FelixConfiguration.spec.mtu`와 `ipAutoDetectionMethod`는 검토한 API가 아닙니다. [MTU/네트워킹 안내](03-networking-modes.md)를 따르며 다른 설정을 보존하고 신규/기존 Pod를 각각 검증하세요.

### BGP 진단

BGP를 사용하는 구성에서만 BGP를 검사합니다. 선택한 `calico-node` Pod에서 실제 BIRD 소켓을 사용하세요.

```bash
kubectl exec -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node -- \
  birdcl -s /var/run/calico/bird.ctl show protocols all
kubectl exec -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node -- \
  birdcl -s /var/run/calico/bird.ctl show route
calicoctl get bgpconfiguration -o yaml
calicoctl get bgppeer -o yaml
calicoctl get bgpfilter -o yaml
```

IPv6 데몬이 있다면 해당 `bird6.ctl`을 사용합니다. 로컬/피어 ASN, 선택한 출발지 주소, 양방향 TCP 179, 인증/TTL, 라우트 필터, 기대하는 광고 경로를 확인하세요. TCP 연결 성공만으로 세션 Established나 필요한 prefix 수용이 검증되지는 않습니다. 파일이 있다고 가정하기 전에 패키지의 로그 설정을 확인하세요. 릴리스 컨테이너의 BIRD run/log 스크립트가 출력 위치를 결정합니다. [BGP 심화](04-bgp-deep-dive.md)를 참고하세요.

## 헬스체크 자동화

다음 **operator 설치 상태 검사**는 Bash, jq, 호환 kubectl이 있는 관리 환경에서 실행합니다. 읽기 전용 API/로그 요청으로 DaemonSet의 관측 generation과 복제본 가용성을 확인하고 요청이 실패하면 실패를 반환합니다. BGP 소켓, 패킷 전달, 모든 정책의 정확성을 검사하는 스크립트는 아닙니다.

```bash
#!/usr/bin/env bash
# calico-status-check.sh: operator 컴포넌트 상태와 제한된 로그 수집.
set -euo pipefail
CALICO_NAMESPACE=${CALICO_NAMESPACE:-calico-system}

if ! calico_ds_json=$(kubectl get daemonset calico-node -n "$CALICO_NAMESPACE" \
  --request-timeout=20s -o json); then
  echo "Unable to read calico-node DaemonSet status" >&2
  exit 2
fi
if ! jq -e '
  .status.desiredNumberScheduled as $desired
  | ($desired > 0)
    and (.status.observedGeneration >= .metadata.generation)
    and (.status.updatedNumberScheduled == $desired)
    and (.status.numberReady == $desired)
    and (.status.numberAvailable == $desired)
    and ((.status.numberUnavailable // 0) == 0)
' <<<"$calico_ds_json" >/dev/null; then
  echo "Calico DaemonSet is not fully observed, updated and available" >&2
  exit 1
fi

if ! calico_status_json=$(kubectl get tigerastatus --request-timeout=20s -o json); then
  echo "Unable to read operator component status" >&2
  exit 2
fi
if ! jq -e '
  (.items | length) > 0 and all(.items[];
    any(.status.conditions[]?; .type == "Available" and .status == "True")
    and any(.status.conditions[]?; .type == "Progressing" and .status == "False")
    and any(.status.conditions[]?; .type == "Degraded" and .status == "False")
  )
' <<<"$calico_status_json" >/dev/null; then
  echo "Operator components are unavailable, progressing, degraded or missing conditions" >&2
  exit 1
fi

if ! calico_logs=$(kubectl logs -n "$CALICO_NAMESPACE" -l k8s-app=calico-node \
  -c calico-node --since=15m --tail=200 --timestamps --prefix \
  --request-timeout=20s); then
  echo "Unable to retrieve selected Calico logs; do not report no errors" >&2
  exit 2
fi
printf '%s\n' "$calico_logs"
echo "Component status checks passed; review these bounded logs and test application policy separately."
```

비어 있거나 스케줄링되지 않은 DaemonSet, 오래된 상태, 누락된 컴포넌트 condition은 성공이 아닙니다. 로그는 선택한 시간/tail 범위로 제한되며 해석이 필요합니다. Counter나 ERROR 단어 하나가 실제 장애와 같은 의미는 아닙니다.

CronJob으로 예약하려면 먼저 필요한 도구와 스크립트를 승인 이미지에 패키징하고 검증하세요. DaemonSet, Pod/Pod 로그, TigeraStatus 읽기 권한을 가진 전용 ServiceAccount를 사용하며 권한이 큰 `calico-node` identity를 재사용하지 마세요. 동시 실행, deadline, 실패 보고도 설정합니다. `calico/ctl` 이미지는 범용 Bash/kubectl 진단 환경이 아니며 일반 Job은 의도적으로 추가 접근을 제공하지 않으면 다른 노드의 BIRD 소켓을 조사할 수 없습니다. 이 로컬 스크립트가 작동하는 클러스터 내부 CronJob까지 제공한다는 뜻은 아닙니다.

## 버전 업그레이드와 복구

### 전환 준비

```bash
calicoctl version
kubectl version --output=yaml
kubectl get deployment tigera-operator -n tigera-operator \
  -o jsonpath='{.spec.template.spec.containers[*].image}'
kubectl get tigerastatus
kubectl get daemonset calico-node -n calico-system -o wide
helm get values calico -n tigera-operator -o yaml
```

Helm 명령은 Helm 관리 설치에만 적용됩니다. 실제 이미지, CRD, 데이터스토어, 노드 OS/커널, 데이터플레인, Kubernetes 호환성을 확인하세요. 소유 매니페스트/values, 정책, 검증된 복구 계획을 보존합니다. `kubectl version --short`는 현재 명령 옵션이 아닙니다.

실제 출발 버전과 설치 방식에 맞는 [3.32 업그레이드 절차](https://docs.tigera.io/calico/latest/operations/upgrading/kubernetes-upgrade)를 따릅니다. 해당 릴리스를 거칠 때 OwnerReference/UID 마이그레이션 주의사항을 검토하세요. 목표 버전을 고정하고 calicoctl도 맞춥니다.

Helm에서는 새 operator보다 먼저 소유 경로로 일치하는 Calico CRD를 적용하거나, `manageCRDs: true`로 operator의 CRD 설치를 기다린 뒤 새 필드를 사용합니다. Operator 변경만을 이유로 `--force-conflicts`로 필드 소유권을 덮어쓰지 마세요. 검토한 변경 후 operator, calico-node, 설정한 다른 컴포넌트를 관찰하고 rollout 중·이후 허용/거부 경로를 테스트합니다.

Operator는 자신이 관리하는 DaemonSet을 조정합니다. Affinity patch로 “canary” 노드에서 에이전트를 제거한다고 안전한 canary가 배포되는 것은 아니며 해당 노드가 정책 없이 남을 수 있습니다. 대표성 있는 격리 환경에서 버전/설정을 검증하고 지원되는 rollout 제어를 사용하세요. 경쟁하는 두 번째 노드 DaemonSet을 임의로 만들지 마세요.

### 복구 한계

`helm rollback`, 이전 operator 적용, 설정 export 적용은 CRD/데이터 마이그레이션이나 패킷 처리 상태를 자동으로 되돌리지 않습니다. 출발/목표 릴리스의 지원 다운그레이드 경로와 저장 데이터를 확인한 후 복구를 선택하세요. Installation 리소스가 남아 있다고 데이터 손실이 없다는 뜻은 아닙니다.

EKS 컨트롤 플레인 복구는 [Part 8](08-eks-integration.md)의 현재 자격과 7일 롤백 한계를 따릅니다. Calico/애드온과 애플리케이션 호환성은 별도 책임입니다.

## 백업 및 재해 복구

### 설정 목록과 상태 복구 구분

| 자료 | 목적과 한계 |
| --- | --- |
| Git 관리 매니페스트/Helm values, 버전 기록 | 원하는 설정과 소유권, 일치하는 CRD 정의와 이미지 보존 |
| Calico 정책, tier, set, pool, BGP/filter, controller 설정 | 실제 사용한 namespaced/staged/global 리소스를 포함한 설정 목록 |
| Kubernetes NetworkPolicy, namespace/ServiceAccount 레이블, 관련 RBAC | Calico 리소스만 export하면 빠지는 정책 identity/의존성 |
| Host/node/endpoint와 IPAM 상태 | 런타임/토폴로지에 의존하므로 이전 노드 주소와 할당을 다른 클러스터에 그대로 적용하지 않음 |
| 데이터스토어 백업과 애플리케이션 데이터 | 일관된 복구 수단과 별도로 보호할 자격증명/데이터, YAML 목록은 원자적 데이터스토어 snapshot이 아님 |

`kubectl export` 명령은 없습니다. `calicoctl get TYPE -o yaml`은 리소스 export이며 `--export`에는 앞서 설명한 이름 지정 제한이 있습니다. 자체 관리 Kubernetes/etcd는 일치하는 버전과 복구 테스트를 포함한 [Kubernetes etcd 백업/복구 절차](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/)를 따르세요. 관리형 서비스는 해당 서비스의 지원 복구 방식을 사용하며 이 절차로 EKS etcd에 접근할 수는 없습니다.

### 보호된 설정 목록 예제

다음은 Calico IPAM을 사용하는 3.32 operator 설치에서 **명시한 일부 리소스**를 내보내는 스크립트입니다. Bash, calicoctl, kubectl, sha256sum이 필요합니다. 대상 디렉터리는 없어야 하며 부분 실패에는 `STATE=incomplete`가 남습니다. Secret, 외부 IAM/네트워크 장비, 모든 operator 사용자 정의 리소스, 전체 IPAM 할당 상태를 수집하지 않습니다. 실제 기능에 맞게 목록을 확장하고 자격증명은 별도 안전한 백업으로 보호하세요.

```bash
#!/usr/bin/env bash
# calico-config-inventory.sh: 보호된 설정 목록, 데이터스토어 snapshot이 아님.
set -euo pipefail
umask 077
CALICO_EXPORT_DIR=${1:?Usage: calico-config-inventory.sh NEW_EXPORT_DIRECTORY}
mkdir -m 700 -- "$CALICO_EXPORT_DIR"
printf '%s\n' incomplete > "$CALICO_EXPORT_DIR/STATE"

for calico_kind in node ippool ipreservation bgpconfiguration bgppeer bgpfilter \
  globalnetworkpolicy stagedglobalnetworkpolicy globalnetworkset \
  felixconfiguration kubecontrollersconfiguration ipamconfiguration \
  tier hostendpoint profile; do
  calicoctl get "$calico_kind" -o yaml > "$CALICO_EXPORT_DIR/$calico_kind.yaml"
done
for calico_kind in networkpolicy stagednetworkpolicy stagedkubernetesnetworkpolicy \
  networkset workloadendpoint; do
  calicoctl get "$calico_kind" -A -o yaml > "$CALICO_EXPORT_DIR/$calico_kind.yaml"
done
kubectl get installation default -o yaml > "$CALICO_EXPORT_DIR/installation.yaml"
kubectl get networkpolicies.networking.k8s.io -A -o yaml \
  > "$CALICO_EXPORT_DIR/kubernetes-networkpolicies.yaml"
kubectl get namespaces -o yaml > "$CALICO_EXPORT_DIR/namespaces.yaml"
kubectl get serviceaccounts -A -o yaml > "$CALICO_EXPORT_DIR/serviceaccounts.yaml"
(
  cd -- "$CALICO_EXPORT_DIR"
  sha256sum ./*.yaml > SHA256SUMS
)
printf '%s\n' complete > "$CALICO_EXPORT_DIR/STATE"
echo "Configuration inventory completed: $CALICO_EXPORT_DIR"
```

`complete`는 명시한 조회와 체크섬 작성이 완료되었다는 뜻이며 트랜잭션 일관성이나 재해 복구 테스트 완료를 의미하지 않습니다. Export를 민감한 인프라 자료로 취급하세요. 체크섬을 확인하고 장애 영역 밖에 보관하며 실제 데이터스토어/버전으로 복구를 연습합니다.

### 복구 계획

1. 선택한 방식으로 호환 컨트롤 플레인/데이터스토어와 필요한 CRD/operator를 복구합니다. 새 클러스터 이전과 같은 클러스터 복구의 identity/IPAM 요건은 다릅니다.
2. Namespace/ServiceAccount identity, 레이블, RBAC를 검토하고 tier/set을 의존 정책보다 먼저 복구하는 등 소유 선언적 설정의 의존 순서를 따릅니다.
3. 클러스터별 metadata, 생성형/controller 소유 오브젝트, 이전 노드 주소/할당을 검토합니다. 원본 dump를 이식 가능한 desired-state 매니페스트로 그대로 적용하지 마세요.
4. 정상 변경을 재개하기 전에 IP 할당 중복, 경로, 암호화, Service/DNS, 허용·거부 트래픽을 검증합니다.

`calicoctl datastore migrate export/import`는 datastore lock과 rollback 경계가 있는 실제 **etcd→Kubernetes 마이그레이션** 기능입니다. 기존 Kubernetes 데이터스토어의 일반 백업 단축 명령이 아닙니다. Lock은 새 Pod에 영향을 주며 문서화된 마이그레이션은 Kubernetes 데이터스토어 unlock 후 되돌릴 수 없습니다. [마이그레이션 절차](https://docs.tigera.io/calico/latest/operations/datastore-migration)를 참고하세요.

## 운영 모범 사례

### 정책과 접근

선택한 테스트 네임스페이스에서 DNS, API, identity, 모니터링, 애플리케이션 의존성을 준비한 후 default-deny를 검증하세요. 빈 전역 `all()` 정책이나 존재하지 않는 API-server/노드 레이블 selector는 필수 트래픽을 끊을 수 있습니다. Pod와 host endpoint의 정책 경로도 다릅니다. [Part 5](05-network-policy.md)의 제한된 예제, tier 의미, host endpoint 제어를 사용하세요. 독립적으로 사용할 수 있는 복구 경로를 유지하고 범위를 넓히기 전에 거부 사례를 테스트합니다.

### Flow 관측성

현재 OSS operator/Helm 설치는 Goldmane와 Whisker를 사용할 수 있습니다. [OSS flow log 가이드](https://docs.tigera.io/calico/latest/observability/view-flow-logs)는 이 기능을 tech preview로 표시하며 패킷/연결 하나당 한 레코드가 아닌 집계 flow를 설명합니다. 이전 파일/DNS logger 필드와 존재하지 않는 `FlowLogsFileReporter` 이름은 유효한 OSS 설정이 아닙니다.

```bash
kubectl get goldmane,whisker
kubectl port-forward -n calico-system service/whisker 8081:8081
```

Port-forward는 기본적으로 로컬에 바인딩합니다. Whisker/Goldmane에는 민감한 워크로드/네트워크 자료가 있으므로 외부 노출 전 인증과 접근 제어를 설정하세요. 이 컴포넌트가 없던 버전에서 업그레이드했다면 해당 사용자 정의 리소스를 의도적으로 활성화해야 합니다. 프로세스 debug 로그, 정책 Log action, 집계 flow log, Prometheus 메트릭은 서로 다른 질문에 답합니다.

### 성능과 자원

엔드포인트/정책 변경량, 데이터플레인 설정 시간, 대기열, 메모리, 실제 애플리케이션 트래픽을 측정하세요. Resync/refresh 주기는 Kubernetes API polling 주기가 아니며 늘린다고 보편적인 API 부하 최적화가 되지는 않습니다. 이전 `...Secs` 철자 대신 실제 duration 필드 `iptablesPostWriteCheckInterval`을 사용합니다. 설치 소유자의 지원 resource override와 operator 규모 조절을 보존하세요.

BPF, DSR, 추측한 인터페이스 패턴을 일반적인 튜닝 프리셋으로 활성화하지 마세요. [Part 6](06-ebpf-dataplane.md)에서 커널/플랫폼, Service 처리, kube-proxy 충돌, 복구를 다룹니다. Conntrack map을 키우면 메모리를 사용하며 모든 병목이 사라지는 것은 아닙니다. 데이터플레인이나 자원 변경이 필요하면 관련 워크로드·실패 테스트를 다시 수행하세요.

이 문서의 검사는 오프라인 스키마, 쿼리, 스크립트 fixture 검증입니다. 프로덕션 용량, 성공적인 클러스터 업그레이드나 재해 복구를 입증하지 않습니다.

## 참고 자료

- [Calico 요구사항](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements)
- [Calico Installation API](https://docs.tigera.io/calico/latest/reference/installation/api)
- [컴포넌트 메트릭 모니터링](https://docs.tigera.io/calico/latest/operations/monitor/monitor-component-metrics)
- [Felix 메트릭](https://docs.tigera.io/calico/latest/reference/felix/prometheus)
- [Typha 메트릭](https://docs.tigera.io/calico/latest/reference/typha/prometheus)
- [kube-controllers 메트릭](https://docs.tigera.io/calico/latest/reference/kube-controllers/prometheus)
- [Calico 트러블슈팅](https://docs.tigera.io/calico/latest/operations/troubleshoot/troubleshooting)
- [Calico 업그레이드](https://docs.tigera.io/calico/latest/operations/upgrading/kubernetes-upgrade)
- [Prometheus Operator API](https://prometheus-operator.dev/docs/api-reference/api/)

## 다음 단계와 퀴즈

[용어집](glossary.md), [고급 주제](07-advanced-topics.md), [EKS 통합](08-eks-integration.md)을 복습하고 [운영 퀴즈](../../quizzes/networking/calico/09-operations-quiz.md)를 풀어보세요.

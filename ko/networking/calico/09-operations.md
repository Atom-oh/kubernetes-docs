# Part 9: Calico 운영 가이드

> **지원 버전**: Calico v3.29+ / Kubernetes 1.28+
> **마지막 업데이트**: 2025년 2월 22일

## 개요

이 문서에서는 Calico의 설치, 모니터링, 문제 해결, 업그레이드 및 백업/복구에 대한 운영 가이드를 제공합니다. 프로덕션 환경에서 Calico를 안정적으로 운영하기 위한 모범 사례를 다룹니다.

## 설치 가이드

### 방법 1: Tigera Operator (권장)

Tigera Operator는 Calico의 라이프사이클을 관리하는 권장 설치 방법입니다.

```bash
# 1. Tigera Operator 설치
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.29.0/manifests/tigera-operator.yaml

# Operator 준비 대기
kubectl wait --for=condition=available --timeout=300s deployment/tigera-operator -n tigera-operator
```

```yaml
# 2. Installation CR 적용
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  # 네트워크 설정
  calicoNetwork:
    bgp: Enabled

    # IP Pool 설정
    ipPools:
      - cidr: 10.244.0.0/16
        encapsulation: VXLANCrossSubnet
        natOutgoing: Enabled
        nodeSelector: all()
        blockSize: 26

    # Node IP 자동 감지
    nodeAddressAutodetectionV4:
      kubernetes: NodeInternalIP

    # MTU 설정 (선택)
    # mtu: 1400

  # 컴포넌트 리소스
  componentResources:
    - componentName: Node
      resourceRequirements:
        requests:
          cpu: 200m
          memory: 256Mi
        limits:
          cpu: 1000m
          memory: 512Mi

    - componentName: Typha
      resourceRequirements:
        requests:
          cpu: 100m
          memory: 128Mi
        limits:
          cpu: 500m
          memory: 256Mi

    - componentName: KubeControllers
      resourceRequirements:
        requests:
          cpu: 100m
          memory: 128Mi
        limits:
          cpu: 500m
          memory: 256Mi

  # Typha 배포 설정
  typhaDeployment:
    spec:
      minReadySeconds: 10
      template:
        spec:
          tolerations:
            - key: CriticalAddonsOnly
              operator: Exists

  # 노드 업데이트 전략
  nodeUpdateStrategy:
    rollingUpdate:
      maxUnavailable: 1
    type: RollingUpdate
```

```bash
# 3. Installation 적용
kubectl apply -f installation.yaml

# 4. 설치 상태 확인
kubectl get installation default -o yaml
kubectl get tigerastatus
```

### 방법 2: Manifest 설치

```bash
# 전체 Calico 설치 (Operator 없이)
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.29.0/manifests/calico.yaml

# 또는 커스텀 CIDR
curl https://raw.githubusercontent.com/projectcalico/calico/v3.29.0/manifests/calico.yaml | \
  sed 's|192.168.0.0/16|10.244.0.0/16|g' | \
  kubectl apply -f -
```

### 방법 3: Helm 설치

```bash
# Helm repo 추가
helm repo add projectcalico https://docs.tigera.io/calico/charts
helm repo update

# values.yaml 생성
cat > values.yaml <<EOF
installation:
  calicoNetwork:
    bgp: Enabled
    ipPools:
      - cidr: 10.244.0.0/16
        encapsulation: VXLANCrossSubnet
        natOutgoing: Enabled
    nodeAddressAutodetectionV4:
      kubernetes: NodeInternalIP

typhaDeployment:
  replicas: 3

componentResources:
  - componentName: Node
    resourceRequirements:
      requests:
        cpu: 200m
        memory: 256Mi
      limits:
        cpu: 1000m
        memory: 512Mi
EOF

# 설치
helm install calico projectcalico/tigera-operator \
  --namespace tigera-operator \
  --create-namespace \
  --version v3.29.0 \
  -f values.yaml
```

### 설치 검증

```bash
# 1. 컴포넌트 상태 확인
kubectl get pods -n calico-system -o wide
kubectl get pods -n calico-apiserver -o wide

# 2. DaemonSet 상태
kubectl get ds -n calico-system calico-node

# 3. Installation 상태
kubectl get installation default -o yaml | grep -A 20 status:

# 4. TigeraStatus 확인
kubectl get tigerastatus

# 5. calicoctl로 노드 상태 확인
calicoctl node status

# 6. BGP 피어 상태
calicoctl get bgppeer
calicoctl get node -o wide

# 7. IP Pool 확인
calicoctl get ippool -o yaml

# 8. 네트워크 연결 테스트
kubectl run test-pod --image=busybox --rm -it --restart=Never -- wget -qO- http://kubernetes.default.svc.cluster.local/healthz
```

## calicoctl 명령어 레퍼런스

### 설치

```bash
# Linux AMD64
curl -L https://github.com/projectcalico/calico/releases/download/v3.29.0/calicoctl-linux-amd64 -o calicoctl
chmod +x calicoctl
sudo mv calicoctl /usr/local/bin/

# Linux ARM64
curl -L https://github.com/projectcalico/calico/releases/download/v3.29.0/calicoctl-linux-arm64 -o calicoctl
chmod +x calicoctl
sudo mv calicoctl /usr/local/bin/

# macOS
curl -L https://github.com/projectcalico/calico/releases/download/v3.29.0/calicoctl-darwin-amd64 -o calicoctl
chmod +x calicoctl
sudo mv calicoctl /usr/local/bin/

# 데이터스토어 설정
export DATASTORE_TYPE=kubernetes
export KUBECONFIG=~/.kube/config

# 또는 calicoctl.cfg 파일 사용
cat > ~/.config/calicoctl/calicoctl.cfg <<EOF
apiVersion: projectcalico.org/v3
kind: CalicoAPIConfig
metadata:
spec:
  datastoreType: "kubernetes"
  kubeconfig: "/home/user/.kube/config"
EOF
```

### 노드 명령어

```bash
# 노드 상태 확인
calicoctl node status

# 샘플 출력:
# Calico process is running.
#
# IPv4 BGP status
# +--------------+-------------------+-------+----------+-------------+
# | PEER ADDRESS |     PEER TYPE     | STATE |  SINCE   |    INFO     |
# +--------------+-------------------+-------+----------+-------------+
# | 10.0.1.2     | node-to-node mesh | up    | 12:00:00 | Established |
# | 10.0.1.3     | node-to-node mesh | up    | 12:00:00 | Established |
# +--------------+-------------------+-------+----------+-------------+

# 노드 진단 정보 수집
calicoctl node diags
# 출력 파일: /tmp/calico-diags-<timestamp>.tar.gz

# 노드 목록
calicoctl get node -o wide
calicoctl get node <node-name> -o yaml
```

### IPAM 명령어

```bash
# IPAM 전체 상태
calicoctl ipam show

# 샘플 출력:
# +----------+-----------------+-----------+------------+-----------+
# | GROUPING |      CIDR       | IPS TOTAL | IPS IN USE | IPS FREE  |
# +----------+-----------------+-----------+------------+-----------+
# | IP Pool  | 10.244.0.0/16   | 65536     | 1250       | 64286     |
# +----------+-----------------+-----------+------------+-----------+

# 블록별 상세 정보
calicoctl ipam show --show-blocks

# 샘플 출력:
# +----------+-------------------+-----------+------------+-----------+
# | GROUPING |       CIDR        | IPS TOTAL | IPS IN USE | IPS FREE  |
# +----------+-------------------+-----------+------------+-----------+
# | Block    | 10.244.0.0/26     | 64        | 45         | 19        |
# | Block    | 10.244.0.64/26    | 64        | 32         | 32        |
# | Block    | 10.244.1.0/26     | 64        | 28         | 36        |
# +----------+-------------------+-----------+------------+-----------+

# 특정 IP 정보 조회
calicoctl ipam show --ip=10.244.0.15

# 샘플 출력:
# IP 10.244.0.15 is in use
# Attributes:
#   pod: my-pod
#   namespace: default
#   node: node-1

# 사용하지 않는 IP 해제
calicoctl ipam release --ip=10.244.0.15

# 빈 블록 해제
calicoctl ipam release --block=10.244.5.0/26

# IP Pool 설정 확인
calicoctl ipam show --show-configuration
```

### Policy 명령어

```bash
# NetworkPolicy 목록
calicoctl get networkpolicy -A
calicoctl get networkpolicy -n production

# GlobalNetworkPolicy 목록
calicoctl get globalnetworkpolicy

# 특정 정책 상세
calicoctl get networkpolicy <policy-name> -n <namespace> -o yaml
calicoctl get globalnetworkpolicy <policy-name> -o yaml

# NetworkSet 목록
calicoctl get networkset -A
calicoctl get globalnetworkset

# Tier 목록
calicoctl get tier

# 정책 생성/업데이트
calicoctl apply -f policy.yaml
calicoctl create -f policy.yaml
calicoctl replace -f policy.yaml

# 정책 삭제
calicoctl delete networkpolicy <name> -n <namespace>
calicoctl delete globalnetworkpolicy <name>
```

### 리소스 명령어

```bash
# 리소스 조회
calicoctl get <resource-type> [name] [-n namespace] [-o yaml|json|wide]

# 지원 리소스 타입:
# - node
# - ippool
# - bgppeer
# - bgpconfiguration
# - felixconfiguration
# - networkpolicy
# - globalnetworkpolicy
# - networkset
# - globalnetworkset
# - hostendpoint
# - workloadendpoint
# - profile

# 리소스 생성
calicoctl create -f resource.yaml

# 리소스 업데이트 (존재하면 업데이트, 없으면 생성)
calicoctl apply -f resource.yaml

# 리소스 교체
calicoctl replace -f resource.yaml

# 리소스 삭제
calicoctl delete -f resource.yaml
calicoctl delete <resource-type> <name> [-n namespace]

# 출력 포맷
calicoctl get node -o yaml     # YAML 형식
calicoctl get node -o json     # JSON 형식
calicoctl get node -o wide     # 확장 테이블
calicoctl get node -o custom-columns=NAME:.metadata.name,BGP:.spec.bgp.ipv4Address
```

## Prometheus 메트릭

### Felix 메트릭

```yaml
# ServiceMonitor 설정
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: calico-felix
  namespace: monitoring
  labels:
    app: calico
spec:
  selector:
    matchLabels:
      k8s-app: calico-node
  namespaceSelector:
    matchNames:
      - calico-system
  endpoints:
    - port: http-metrics
      path: /metrics
      interval: 30s
```

**주요 Felix 메트릭:**

| 메트릭 | 설명 | 타입 |
|--------|------|------|
| `felix_active_local_endpoints` | 활성 로컬 엔드포인트 수 | Gauge |
| `felix_active_local_policies` | 적용된 정책 수 | Gauge |
| `felix_iptables_save_time_seconds` | iptables 저장 시간 | Histogram |
| `felix_iptables_restore_time_seconds` | iptables 복원 시간 | Histogram |
| `felix_int_dataplane_failures_total` | 데이터플레인 실패 횟수 | Counter |
| `felix_route_table_list_seconds` | 라우트 테이블 조회 시간 | Histogram |
| `felix_calc_graph_update_time_seconds` | 그래프 업데이트 시간 | Histogram |
| `felix_resync_state` | 재동기화 상태 | Gauge |

### BIRD 메트릭

```bash
# BGP 세션 상태 확인
kubectl exec -n calico-system <calico-node-pod> -c calico-node -- \
  birdcl show protocols

# BGP 경로 확인
kubectl exec -n calico-system <calico-node-pod> -c calico-node -- \
  birdcl show route
```

### Typha 메트릭

| 메트릭 | 설명 | 타입 |
|--------|------|------|
| `typha_connections_accepted` | 수락된 연결 수 | Counter |
| `typha_connections_dropped` | 드롭된 연결 수 | Counter |
| `typha_connections_active` | 활성 연결 수 | Gauge |
| `typha_updates_total` | 전송된 업데이트 수 | Counter |
| `typha_breadcrumb_block_seconds` | 브레드크럼 블록 시간 | Histogram |

```yaml
# Typha ServiceMonitor
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: calico-typha
  namespace: monitoring
spec:
  selector:
    matchLabels:
      k8s-app: calico-typha
  namespaceSelector:
    matchNames:
      - calico-system
  endpoints:
    - port: http-metrics
      path: /metrics
      interval: 30s
```

## Grafana 대시보드

### 주요 패널 구성

```json
{
  "title": "Calico Overview Dashboard",
  "panels": [
    {
      "title": "Active Endpoints",
      "type": "stat",
      "targets": [
        {
          "expr": "sum(felix_active_local_endpoints)"
        }
      ]
    },
    {
      "title": "Active Policies",
      "type": "stat",
      "targets": [
        {
          "expr": "sum(felix_active_local_policies)"
        }
      ]
    },
    {
      "title": "Dataplane Failures",
      "type": "graph",
      "targets": [
        {
          "expr": "rate(felix_int_dataplane_failures_total[5m])"
        }
      ]
    },
    {
      "title": "iptables Restore Time",
      "type": "graph",
      "targets": [
        {
          "expr": "histogram_quantile(0.99, rate(felix_iptables_restore_time_seconds_bucket[5m]))"
        }
      ]
    },
    {
      "title": "BGP Peer Status",
      "type": "table",
      "targets": [
        {
          "expr": "calico_bgp_peer_status"
        }
      ]
    },
    {
      "title": "Typha Connections",
      "type": "graph",
      "targets": [
        {
          "expr": "typha_connections_active"
        }
      ]
    }
  ]
}
```

## Alert 규칙

### PrometheusRule 설정

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: calico-alerts
  namespace: monitoring
spec:
  groups:
    - name: calico.rules
      rules:
        # calico-node 실행 상태
        - alert: CalicoNodeNotReady
          expr: |
            kube_daemonset_status_number_unavailable{daemonset="calico-node"} > 0
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "Calico node not ready"
            description: "{{ $value }} calico-node pods are not ready"

        # BGP 피어 다운
        - alert: CalicoBGPPeerDown
          expr: |
            calico_bgp_peer_status == 0
          for: 2m
          labels:
            severity: warning
          annotations:
            summary: "BGP peer down"
            description: "BGP peer {{ $labels.peer }} is down"

        # Felix 데이터플레인 실패
        - alert: CalicoFelixDataplaneFailure
          expr: |
            rate(felix_int_dataplane_failures_total[5m]) > 0
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "Felix dataplane failures"
            description: "Felix is experiencing dataplane failures on {{ $labels.instance }}"

        # iptables 복원 시간 지연
        - alert: CalicoIptablesRestoreSlow
          expr: |
            histogram_quantile(0.99, rate(felix_iptables_restore_time_seconds_bucket[5m])) > 0.5
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "iptables restore slow"
            description: "iptables restore taking > 500ms on {{ $labels.instance }}"

        # Typha 연결 드롭
        - alert: CalicoTyphaConnectionsDropped
          expr: |
            rate(typha_connections_dropped[5m]) > 0
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "Typha connections dropped"
            description: "Typha is dropping connections on {{ $labels.instance }}"

        # IP Pool 고갈 경고
        - alert: CalicoIPPoolNearExhaustion
          expr: |
            (calico_ipam_blocks_used / calico_ipam_blocks_total) > 0.8
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "IP Pool near exhaustion"
            description: "IP Pool {{ $labels.pool }} is {{ $value | humanizePercentage }} used"
```

## 로그 분석

### Felix 로그

```bash
# Felix 로그 위치
# 컨테이너: /var/log/calico/felix.log
# 또는 stdout으로 출력

# 실시간 로그 확인
kubectl logs -n calico-system -l k8s-app=calico-node -c calico-node -f

# 특정 로그 레벨 필터링
kubectl logs -n calico-system -l k8s-app=calico-node -c calico-node | grep -E "(ERROR|WARNING)"

# 일반적인 메시지 패턴
# INFO: 정상 동작
# WARNING: 주의 필요 (재시도 가능)
# ERROR: 오류 발생 (개입 필요)
```

**일반적인 Felix 로그 메시지:**

| 메시지 패턴 | 의미 | 조치 |
|------------|------|------|
| `Resync starting` | 재동기화 시작 | 정상 |
| `Resync complete` | 재동기화 완료 | 정상 |
| `Failed to connect to Typha` | Typha 연결 실패 | Typha 상태 확인 |
| `Failed to update iptables` | iptables 업데이트 실패 | 커널/권한 확인 |
| `Endpoint deleted` | 엔드포인트 삭제됨 | 정상 (Pod 삭제 시) |

### BIRD 로그

```bash
# BIRD 로그 확인
kubectl exec -n calico-system <calico-node-pod> -c calico-node -- \
  cat /var/log/calico/bird/current

# 또는
kubectl exec -n calico-system <calico-node-pod> -c calico-node -- \
  cat /var/log/calico/bird6/current

# BGP 세션 문제 확인
kubectl exec -n calico-system <calico-node-pod> -c calico-node -- \
  grep -i "error\|failed\|refused" /var/log/calico/bird/current
```

### 로그 레벨 설정

```yaml
# FelixConfiguration에서 로그 레벨 조정
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  # 화면 출력 로그 레벨
  logSeverityScreen: Info  # Debug, Info, Warning, Error, Fatal

  # 파일 출력 로그 레벨
  logSeverityFile: Warning
  logFilePath: /var/log/calico/felix.log

  # Syslog 로그 레벨
  logSeveritySys: Warning
```

## 트러블슈팅 상세

### 1. Pod가 IP를 받지 못하는 경우

```bash
# 증상: Pod가 Pending 상태, IP 미할당

# 진단 Step 1: calico-node 로그 확인
kubectl logs -n calico-system -l k8s-app=calico-node -c calico-node | grep -i "ipam\|allocat"

# 진단 Step 2: IPAM 블록 상태 확인
calicoctl ipam show
calicoctl ipam show --show-blocks

# 진단 Step 3: IP Pool 설정 확인
calicoctl get ippool -o yaml

# 일반적인 원인 및 해결:

# 원인 1: IP Pool CIDR 소진
# 해결: 새 IP Pool 추가 또는 CIDR 확장
calicoctl apply -f - <<EOF
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: additional-pool
spec:
  cidr: 10.245.0.0/16
  vxlanMode: CrossSubnet
  natOutgoing: true
EOF

# 원인 2: 노드 레이블 불일치
# 해결: nodeSelector 확인 및 수정
calicoctl get ippool default-ipv4-ippool -o yaml | grep nodeSelector

# 원인 3: calico-node가 실행되지 않음
# 해결: DaemonSet 상태 확인
kubectl get ds -n calico-system calico-node
kubectl describe ds -n calico-system calico-node
```

### 2. Pod 간 통신 실패

```bash
# 증상: Pod 간 ping/curl 실패

# 진단 Step 1: 라우팅 테이블 확인
kubectl exec -n calico-system <calico-node-pod> -c calico-node -- ip route

# 진단 Step 2: BIRD 상태 확인
kubectl exec -n calico-system <calico-node-pod> -c calico-node -- \
  birdcl show protocols

# 진단 Step 3: Felix 로그에서 연결 관련 오류
kubectl logs -n calico-system -l k8s-app=calico-node -c calico-node | grep -i "route\|connect"

# 진단 Step 4: MTU 확인
kubectl exec -n calico-system <calico-node-pod> -c calico-node -- \
  ip link show | grep mtu

# 일반적인 원인 및 해결:

# 원인 1: MTU 불일치
# 해결: FelixConfiguration에서 MTU 조정
calicoctl patch felixconfiguration default -p '{"spec":{"mtu":1400}}'

# 원인 2: BGP 피어링 실패
# 해결: BGP 상태 확인 및 네트워크 연결 점검
calicoctl node status

# 원인 3: VXLAN/IPIP 터널 문제
# 해결: 캡슐화 인터페이스 확인
kubectl exec -n calico-system <calico-node-pod> -c calico-node -- \
  ip -d link show vxlan.calico
```

### 3. Network Policy가 작동하지 않음

```bash
# 증상: Policy 적용 후에도 트래픽이 차단/허용되지 않음

# 진단 Step 1: Policy 목록 확인
calicoctl get networkpolicy -A
calicoctl get globalnetworkpolicy

# 진단 Step 2: 특정 Pod의 적용된 정책 확인
kubectl get pod <pod-name> -n <namespace> -o yaml | grep -A 20 "cni.projectcalico.org"

# 진단 Step 3: WorkloadEndpoint 확인
calicoctl get workloadendpoint -n <namespace> -o yaml | grep -A 30 <pod-name>

# 진단 Step 4: iptables 규칙 확인 (노드에서)
kubectl exec -n calico-system <calico-node-pod> -c calico-node -- \
  iptables -L -n -v | grep cali

# 일반적인 원인 및 해결:

# 원인 1: 잘못된 selector
# 해결: Pod 레이블과 Policy selector 일치 확인
kubectl get pod <pod-name> -n <namespace> --show-labels

# 원인 2: Policy 순서 문제
# 해결: order 필드 확인 및 조정
calicoctl get globalnetworkpolicy -o yaml | grep order

# 원인 3: Tier 설정 누락
# 해결: Tier 존재 여부 확인
calicoctl get tier

# 원인 4: 정책 타입 누락 (Ingress/Egress)
# 해결: types 필드 확인
calicoctl get networkpolicy <name> -n <namespace> -o yaml | grep types
```

### 4. BGP 피어링 실패

```bash
# 증상: BGP 피어 상태가 "down" 또는 "idle"

# 진단 Step 1: 노드 BGP 상태
calicoctl node status

# 진단 Step 2: BGP 설정 확인
calicoctl get bgpconfig default -o yaml
calicoctl get bgppeer -o yaml

# 진단 Step 3: BIRD 로그 확인
kubectl exec -n calico-system <calico-node-pod> -c calico-node -- \
  cat /var/log/calico/bird/current | grep -i "error\|connect"

# 진단 Step 4: 네트워크 연결 확인
kubectl exec -n calico-system <calico-node-pod> -c calico-node -- \
  nc -zv <peer-ip> 179

# 일반적인 원인 및 해결:

# 원인 1: AS 번호 불일치
# 해결: BGPConfiguration과 피어의 AS 번호 확인
calicoctl get bgpconfig default -o yaml | grep asNumber

# 원인 2: 방화벽에서 BGP 포트 차단
# 해결: TCP 179 포트 개방

# 원인 3: 노드 IP 감지 실패
# 해결: IP 자동 감지 방법 지정
calicoctl patch felixconfiguration default -p '{"spec":{"ipAutoDetectionMethod":"kubernetes-internal-ip"}}'
```

## 헬스체크 자동화

### 헬스체크 스크립트

```bash
#!/bin/bash
# calico-health-check.sh

set -e

echo "=== Calico Health Check ==="
echo "Date: $(date)"
echo ""

# 1. calico-node DaemonSet 상태
echo "1. calico-node DaemonSet Status:"
kubectl get ds -n calico-system calico-node -o wide
echo ""

# 2. Pod 상태
echo "2. Calico Pods Status:"
kubectl get pods -n calico-system -o wide
echo ""

# 3. BGP 상태
echo "3. BGP Status:"
for node in $(kubectl get nodes -o name | cut -d'/' -f2); do
  echo "Node: $node"
  pod=$(kubectl get pods -n calico-system -l k8s-app=calico-node --field-selector spec.nodeName=$node -o name | head -1)
  if [ -n "$pod" ]; then
    kubectl exec -n calico-system $pod -c calico-node -- calicoctl node status 2>/dev/null || echo "  BGP check failed"
  fi
done
echo ""

# 4. IPAM 상태
echo "4. IPAM Status:"
calicoctl ipam show
echo ""

# 5. Installation 상태
echo "5. Installation Status:"
kubectl get installation default -o jsonpath='{.status.conditions}' | jq .
echo ""

# 6. 최근 에러 로그
echo "6. Recent Errors (last 100 lines):"
kubectl logs -n calico-system -l k8s-app=calico-node -c calico-node --tail=100 | grep -i "error\|warning" | tail -20 || echo "No recent errors"

echo ""
echo "=== Health Check Complete ==="
```

### Kubernetes Job으로 실행

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: calico-health-check
  namespace: calico-system
spec:
  schedule: "*/30 * * * *"  # 30분마다
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: calico-node
          containers:
            - name: health-check
              image: calico/ctl:v3.29.0
              command:
                - /bin/sh
                - -c
                - |
                  echo "=== Calico Health Check ==="
                  calicoctl node status
                  calicoctl ipam show
                  calicoctl get node -o wide
          restartPolicy: Never
```

## 버전 업그레이드

### Rolling Upgrade (Operator 사용)

```bash
# 1. 현재 버전 확인
kubectl get deployment -n tigera-operator tigera-operator -o jsonpath='{.spec.template.spec.containers[0].image}'

# 2. 새 Operator 적용
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.29.0/manifests/tigera-operator.yaml

# 3. 업그레이드 진행 모니터링
kubectl rollout status deployment/tigera-operator -n tigera-operator
kubectl get pods -n calico-system -w

# 4. 검증
calicoctl node status
kubectl get tigerastatus
```

### Canary 업그레이드

```bash
# 일부 노드에서만 먼저 테스트

# 1. 테스트 노드 레이블 지정
kubectl label node test-node-1 calico-upgrade=canary

# 2. 테스트 노드의 calico-node 수동 업그레이드
kubectl patch ds -n calico-system calico-node -p '{
  "spec": {
    "template": {
      "spec": {
        "affinity": {
          "nodeAffinity": {
            "requiredDuringSchedulingIgnoredDuringExecution": {
              "nodeSelectorTerms": [
                {
                  "matchExpressions": [
                    {
                      "key": "calico-upgrade",
                      "operator": "NotIn",
                      "values": ["canary"]
                    }
                  ]
                }
              ]
            }
          }
        }
      }
    }
  }
}'

# 3. Canary 노드에 새 버전 배포
# (별도 DaemonSet으로 또는 수동 Pod 배포)

# 4. 테스트 완료 후 전체 롤아웃
kubectl rollout undo ds/calico-node -n calico-system  # 원복
# 전체 업그레이드 진행
```

### 롤백 절차

```bash
# Operator 롤백
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/tigera-operator.yaml

# 롤백 확인
kubectl rollout status deployment/tigera-operator -n tigera-operator
kubectl get pods -n calico-system

# Installation CR은 유지됨 (데이터 손실 없음)
```

## 백업 및 재해 복구

### 백업 대상

| 항목 | 백업 방법 | 빈도 |
|------|----------|------|
| Calico 리소스 | calicoctl export | 일간 |
| Installation CR | kubectl export | 변경 시 |
| IPPool 설정 | calicoctl export | 변경 시 |
| Network Policy | kubectl export | 변경 시 |
| BGP 설정 | calicoctl export | 변경 시 |

### 백업 스크립트

```bash
#!/bin/bash
# calico-backup.sh

BACKUP_DIR="/backup/calico/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

echo "Backing up Calico resources to $BACKUP_DIR"

# 1. Installation CR
kubectl get installation default -o yaml > $BACKUP_DIR/installation.yaml

# 2. IP Pools
calicoctl get ippool -o yaml > $BACKUP_DIR/ippools.yaml

# 3. BGP Configuration
calicoctl get bgpconfiguration -o yaml > $BACKUP_DIR/bgpconfig.yaml
calicoctl get bgppeer -o yaml > $BACKUP_DIR/bgppeers.yaml

# 4. Network Policies
calicoctl get networkpolicy -A -o yaml > $BACKUP_DIR/networkpolicies.yaml
calicoctl get globalnetworkpolicy -o yaml > $BACKUP_DIR/globalnetworkpolicies.yaml

# 5. NetworkSets
calicoctl get networkset -A -o yaml > $BACKUP_DIR/networksets.yaml
calicoctl get globalnetworkset -o yaml > $BACKUP_DIR/globalnetworksets.yaml

# 6. Felix Configuration
calicoctl get felixconfiguration -o yaml > $BACKUP_DIR/felixconfig.yaml

# 7. Tier
calicoctl get tier -o yaml > $BACKUP_DIR/tiers.yaml

# 8. Node 설정 (BGP 관련)
calicoctl get node -o yaml > $BACKUP_DIR/nodes.yaml

echo "Backup completed: $BACKUP_DIR"
ls -la $BACKUP_DIR
```

### 복구 절차

```bash
#!/bin/bash
# calico-restore.sh

BACKUP_DIR=$1

if [ -z "$BACKUP_DIR" ]; then
  echo "Usage: $0 <backup-dir>"
  exit 1
fi

echo "Restoring Calico resources from $BACKUP_DIR"

# 1. Installation CR (Operator가 이미 설치된 경우)
kubectl apply -f $BACKUP_DIR/installation.yaml

# 2. IP Pools
calicoctl apply -f $BACKUP_DIR/ippools.yaml

# 3. BGP Configuration
calicoctl apply -f $BACKUP_DIR/bgpconfig.yaml
calicoctl apply -f $BACKUP_DIR/bgppeers.yaml

# 4. Tier (Policy 전에 복구)
calicoctl apply -f $BACKUP_DIR/tiers.yaml

# 5. NetworkSets
calicoctl apply -f $BACKUP_DIR/networksets.yaml
calicoctl apply -f $BACKUP_DIR/globalnetworksets.yaml

# 6. Network Policies
calicoctl apply -f $BACKUP_DIR/globalnetworkpolicies.yaml
calicoctl apply -f $BACKUP_DIR/networkpolicies.yaml

# 7. Felix Configuration
calicoctl apply -f $BACKUP_DIR/felixconfig.yaml

echo "Restore completed"
calicoctl node status
```

## 모범 사례

### 1. 보안 강화

```yaml
# 기본 거부 정책 적용
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default-deny
spec:
  selector: all()
  types:
    - Ingress
    - Egress
---
# 필수 통신만 허용
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: allow-essential
spec:
  selector: all()
  order: 100
  egress:
    # DNS
    - action: Allow
      protocol: UDP
      destination:
        ports: [53]
    # Kubernetes API
    - action: Allow
      protocol: TCP
      destination:
        selector: "has(kubernetes.io/api-server)"
        ports: [443, 6443]
  ingress:
    # Kubelet health checks
    - action: Allow
      source:
        selector: "has(node-role.kubernetes.io/control-plane)"
```

### 2. 관측성 설정

```yaml
# Flow Logs 활성화
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  # Flow Logs 설정
  flowLogsFlushInterval: "15s"
  flowLogsFileEnabled: true
  flowLogsFileDirectory: "/var/log/calico/flowlogs"
  flowLogsFileMaxFiles: 5
  flowLogsFileMaxFileSizeMb: 100

  # Prometheus 메트릭
  prometheusMetricsEnabled: true
  prometheusMetricsPort: 9091

  # 헬스체크
  healthEnabled: true
  healthPort: 9099
```

### 3. 성능 최적화

```yaml
# 프로덕션 환경 최적화
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  # iptables 최적화
  iptablesRefreshInterval: "180s"  # 기본 90s
  routeRefreshInterval: "180s"

  # 로깅 최적화
  logSeverityScreen: Warning  # 프로덕션에서는 Warning 이상

  # 데이터플레인
  bpfEnabled: true  # eBPF 모드 (권장)
  bpfExternalServiceMode: "DSR"
```

### 4. 리소스 관리

```yaml
# 적절한 리소스 할당
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  componentResources:
    - componentName: Node
      resourceRequirements:
        requests:
          cpu: 200m
          memory: 256Mi
        limits:
          cpu: 1000m
          memory: 512Mi
```

---

## 다음 단계

- [용어집](glossary.md)에서 Calico 용어를 확인합니다
- [Part 7: 고급 주제](07-advanced-topics.md)로 돌아가 고급 기능을 복습합니다
- [Part 8: EKS 통합](08-eks-integration.md)에서 EKS 환경 운영을 확인합니다

## 참고 자료

- [Calico 운영 가이드](https://docs.tigera.io/calico/latest/operations/)
- [calicoctl 레퍼런스](https://docs.tigera.io/calico/latest/reference/calicoctl/)
- [Calico 트러블슈팅](https://docs.tigera.io/calico/latest/operations/troubleshoot/)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [운영 가이드 퀴즈](../../quizzes/networking/calico/09-operations-quiz.md)를 풀어보세요.

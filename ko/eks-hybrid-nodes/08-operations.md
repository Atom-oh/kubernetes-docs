# 운영 및 유지보수

< [이전: 노드 라이프사이클 관리](./07-node-lifecycle.md) | [목차](./README.md) | [다음: 베어메탈 서버 OS 설치](./09-bare-metal-os-setup.md) >

> **검증 기준**: nodeadm 1.0.20; Cilium 1.18.3 CRD; Prometheus Operator 0.93.1; kube-prometheus-stack 90.0.0; Harbor 2.15.2. 검토에 사용한 기준이며 모든 제품의 지원 버전 조합을 뜻하지 않습니다.
> **마지막 업데이트**: 2026년 9월 13일

이 문서에서는 EKS Hybrid Nodes 환경의 운영 및 유지보수 절차를 다룹니다.

## Harbor 취약점 스캔 자동화

관리자 비밀번호를 가진 CronJob이 latest 태그만 순회하는 대신 Harbor 내장 scan-all 스케줄러를 사용합니다. 시스템 관리자 UI에서 **Administration → Interrogation Services → Vulnerability → Schedule to scan all**을 엽니다. Hourly/Daily/Weekly/Custom을 지원하며 문서화된 UI의 Daily는 자정입니다. 오전 02:00 작업 창이 필요하면 배포한 버전에 맞는 Custom 문법·시간대·다음 실행 시각을 확인합니다.

Harbor 2.15.2에는 GET/POST/PUT `/api/v2.0/system/scanAll/schedule` API가 있습니다. UI 또는 신뢰할 CA 검증·보호된 자격 증명·필요한 시스템 권한을 갖춘 승인한 API 연동을 사용합니다. 프로젝트 robot 권한이 전체 스캔 설정 권한을 뜻하지 않습니다. 관리자 비밀번호를 Pod 환경 변수·명령 인자에 넣거나 TLS 검증을 끄지 않습니다.

스캐너 상태, 취약점 DB 최신성, 실제 완료와 실패를 기록합니다. 요청 제출이나 빈 API 응답은 취약점 평가 성공이 아닙니다. 지원하지 않는 artifact도 별도로 처리해야 하며 전체 스캔은 리소스를 소비합니다. 일부 artifact를 자동화할 때도 필요한 모든 페이지·digest를 열거하고 repository 경로를 올바르게 인코딩하며 모든 응답을 확인합니다. latest만 순회하는 루프는 전체 레지스트리를 검사하지 않습니다.

[Harbor 가이드](../container-registry/03-harbor.md)와 [공식 스케줄 절차](https://github.com/goharbor/website/blob/main/docs/administration/vulnerability-scanning/schedule-scans.md)를 참고합니다.

## 데이터베이스 백업 절차

복구 목표와 인벤토리를 정한 뒤 데이터를 복사합니다. Harbor 복구에는 호환되는 DB 메타데이터, registry blob/object storage, 구성과 보호된 시크릿·암호화 키가 필요합니다. PostgreSQL dump만으로 전체 백업이 되지 않습니다. 최신 Harbor에는 Notary v1이 없으므로 notarysigner/notaryserver DB가 있다고 가정하지 않습니다.

[공식 Harbor Velero 절차](https://github.com/goharbor/website/blob/main/docs/administration/backup-restore/_index.md)는 repository read-only 모드와 지정한 Kubernetes 리소스/PV를 사용합니다. 결과는 **application-consistent가 아닌 crash-consistent**이며 Redis를 제외합니다. 동기화되지 않은 메타데이터·세션이 유실되거나 작업 정리가 필요할 수 있습니다. 내부 DB를 대상으로 하며 외부 관리형 DB는 포함하지 않습니다. 지원하는 snapshot/file-backup/data-movement 플러그인을 선택하고 복구 위치에서 모든 볼륨·object 데이터에 접근할 수 있는지 확인합니다. snapshot 참조만으로 별도 위치에 복원 가능한 복사본이 되지는 않습니다.

다음은 확인한 내부 PostgreSQL Pod의 **DB 구성 요소 dump 예시**입니다. pg_dump/pg_restore와 로컬 인증이 이미 구성되어 있어야 합니다. 외부 DB는 해당 시스템의 인증된 백업·복원 절차를 사용합니다. 자격 증명을 명령 인자에 전달하지 않습니다. 오류에서 중단하고 부분 파일을 비공개로 보관하며 완료된 dump로 처리하지 않습니다.

```bash
set -euo pipefail
umask 077
: "${KUBE_CONTEXT:?Set the approved cluster context}"
: "${HARBOR_NAMESPACE:?Set the Harbor namespace}"
: "${HARBOR_DB_POD:?Set the verified internal PostgreSQL Pod}"
: "${HARBOR_DB_USER:?Set the approved backup database user}"
: "${HARBOR_DB_NAME:?Set the actual Harbor database name}"
: "${PRIVATE_BACKUP_ROOT:?Set an existing protected durable directory}"
BACKUP_DIR=$(mktemp -d "$PRIVATE_BACKUP_ROOT/harbor-db.XXXXXX")
kubectl --context "$KUBE_CONTEXT" -n "$HARBOR_NAMESPACE" exec "$HARBOR_DB_POD" -- \
  pg_dump --format=custom --username "$HARBOR_DB_USER" --dbname "$HARBOR_DB_NAME" \
  > "$BACKUP_DIR/registry.dump.partial"
test -s "$BACKUP_DIR/registry.dump.partial"
kubectl --context "$KUBE_CONTEXT" -n "$HARBOR_NAMESPACE" exec -i "$HARBOR_DB_POD" -- \
  pg_restore --list < "$BACKUP_DIR/registry.dump.partial" > "$BACKUP_DIR/archive-toc.private.txt"
mv "$BACKUP_DIR/registry.dump.partial" "$BACKUP_DIR/registry.dump"
printf 'Database archive created: %s; full Harbor recovery requires separate evidence.\n' "$BACKUP_DIR"
```

archive 목록을 읽었다고 복원이 입증되지는 않습니다. 호환되는 PostgreSQL/Harbor 버전으로 복원을 시험하고 artifact pull, 메타데이터, 권한과 연동을 검증합니다. 전체 백업 인벤토리를 보호·체크섬 검증하고 read-only 모드, 작업과 upload/GC 활동을 조정합니다. 실패한 작업의 상태를 확인하지 않은 채 read-only를 자동 해제하지 않습니다.

Redis BGSAVE는 비동기 작업이므로 바로 dump.rdb를 복사하면 이전 세대 파일일 수 있습니다. 별도 설계에서 Redis persistence를 포함한다면 담당자와 완료·상태·세대를 검증합니다. Redis를 제외하는 공식 튜토리얼과 해당 맞춤 설계를 무심코 섞지 않습니다. 이 장에서는 백업·복원을 실행하지 않았습니다.

## Prometheus 메트릭 수집

호스트, kubelet/container, GPU 지표를 구분합니다. `node_cpu_seconds_total`과 `node_memory_*`는 kubelet endpoint가 아니라 Node Exporter가 제공합니다. 검토한 Node Exporter/DCGM 구성에서 실제 host mount, 권한, 노드 배치와 지표 가용성을 확인합니다. Container Insights는 EC2 IMDS를 통해 Hybrid 호스트 수준 지표를 제공하지 않습니다.

아래 discovery 예시는 `monitoring` namespace의 `kube-prom` 릴리스에 대해 kube-prometheus-stack 90.0.0의 Node Exporter Service label·port를 사용합니다. DCGM 부분은 `gpu-operator` namespace에 `app: nvidia-dcgm-exporter` label과 이름이 `metrics`인 container port를 가진 Pod가 있다는 전제이므로 설치한 exporter와 맞춥니다. Monitor 리소스가 exporter를 설치하지는 않습니다. Prometheus 리소스의 monitor·namespace selector를 확인하고 기존 monitor와 중복 수집하지 않습니다.

`attachMetadata.node`는 Node discovery 메타데이터를 제공하지만 이를 지표 label로 자동 복사하지 않습니다. ServiceMonitor는 Prometheus >=2.37, PodMonitor는 >=2.35와 Prometheus ServiceAccount의 Node `list`/`watch` 권한이 필요합니다. relabeling은 실제 `eks.amazonaws.com/compute-type=hybrid` 노드를 선택하고 `node`·`compute_type` target label을 만듭니다. SSM Node 이름의 접두사로 Hybrid 배치를 추측하지 않습니다.

이 예시는 kubelet HTTPS가 아니라 보호된 exporter HTTP endpoint를 사용합니다. 수집기의 접근을 제한합니다. 신뢰하지 않는 경계를 지나면 exporter TLS·인증 또는 검토한 proxy와 CA·authorization 설정을 적용하며 `insecureSkipVerify`를 사용하지 않습니다. kubelet 수집은 별도의 인증·CA 검증 구성을 유지합니다.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: hybrid-node-exporter
  namespace: monitoring
  labels:
    release: kube-prom
spec:
  attachMetadata:
    node: true
  selector:
    matchLabels:
      app.kubernetes.io/name: prometheus-node-exporter
      app.kubernetes.io/instance: kube-prom
  namespaceSelector:
    matchNames: [monitoring]
  endpoints:
  - port: http-metrics
    interval: 30s
    relabelings:
    - sourceLabels: [__meta_kubernetes_node_label_eks_amazonaws_com_compute_type]
      regex: hybrid
      action: keep
    - sourceLabels: [__meta_kubernetes_pod_node_name]
      targetLabel: node
    - targetLabel: compute_type
      replacement: hybrid
---
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: hybrid-gpu-metrics
  namespace: monitoring
  labels:
    release: kube-prom
spec:
  attachMetadata:
    node: true
  selector:
    matchLabels:
      app: nvidia-dcgm-exporter
  namespaceSelector:
    matchNames: [gpu-operator]
  podMetricsEndpoints:
  - port: metrics
    interval: 30s
    relabelings:
    - sourceLabels: [__meta_kubernetes_node_label_eks_amazonaws_com_compute_type]
      regex: hybrid
      action: keep
    - sourceLabels: [__meta_kubernetes_pod_node_name]
      targetLabel: node
    - targetLabel: compute_type
      replacement: hybrid
```

### Grafana 대시보드 쿼리 예시

위 target label과 호환되는 exporter 지표가 있어야 합니다. 단위, GPU/MIG 식별자, 미지원·오류 sentinel, scrape 누락과 중복 series를 확인합니다. GPU framebuffer 사용률은 free가 아니라 전체 용량(`used + free`)으로 나누며, 용량이 0인 series는 제외합니다. 아래 식은 로컬에서 검증할 수 있는 쿼리이며 이 환경의 실측값이 아닙니다.

```promql
# Host CPU utilization percent
100 * (1 - avg by (node) (rate(node_cpu_seconds_total{mode="idle",compute_type="hybrid"}[5m])))

# Host memory utilization percent
100 * (1 - node_memory_MemAvailable_bytes{compute_type="hybrid"} / node_memory_MemTotal_bytes{compute_type="hybrid"})

# GPU utilization: this metric is already a percentage
DCGM_FI_DEV_GPU_UTIL{compute_type="hybrid"}

# GPU framebuffer usage: used / (used + free), excluding zero capacity
(100 * DCGM_FI_DEV_FB_USED{compute_type="hybrid"} /
 (DCGM_FI_DEV_FB_USED{compute_type="hybrid"} + DCGM_FI_DEV_FB_FREE{compute_type="hybrid"}))
and
((DCGM_FI_DEV_FB_USED{compute_type="hybrid"} + DCGM_FI_DEV_FB_FREE{compute_type="hybrid"}) > 0)
```

## Direct Connect 성능 검증

시험 계획과 AWS 서비스 보장을 구분합니다. 기존 예제의 RTT <5ms, 변동 <2ms, 손실 <0.01%, 처리량 >1Gbps는 예시 목표이며 실측 결과나 모든 Direct Connect 연결의 보장이 아닙니다. 실제 위치, 회선, endpoint, workload와 계약 용량에 맞춰 목표를 정하고 측정 경로가 VPN 등 다른 경로가 아닌 Direct Connect인지 확인합니다.

`ping`은 ICMP RTT와 Linux iputils의 RTT mdev를 보고합니다. 이 분산 지표는 단방향 지연 변동이나 iperf3 UDP jitter와 같지 않습니다. ICMP 필터링·우선순위는 실제 애플리케이션 트래픽과 다를 수 있습니다. 1,000개 패킷의 손실 비율 단위는 0.1%이며, 손실 0개를 관측했다고 장기 손실률 <0.01%가 입증되지는 않습니다.

승인된 private test server에서 iperf3가 준비되어 있어야 합니다. 시험 시간과 전송률 상한을 조정하고 결과를 보호합니다. EKS API endpoint에 iperf3를 실행하지 않습니다. 다음 예시는 Bash, Python3, iputils ping, GNU timeout과 해당 옵션을 지원하는 iperf3가 필요합니다. 오류가 나면 중단하며 도구 누락, 잘못된 JSON, iperf3 오류는 성능 시험 통과가 아닙니다.

```bash
set -euo pipefail
umask 077
: "${PROBE_HOST:?Set the approved private test host}"
: "${TEST_BITRATE:?Set an approved traffic cap, for example 10M}"
: "${PRIVATE_RESULTS_ROOT:?Set an existing protected results directory}"
if [[ ! "$TEST_BITRATE" =~ ^[1-9][0-9]*[KMGT]?$ ]]; then
  printf 'TEST_BITRATE must be a positive integer with an optional K/M/G/T suffix.\n' >&2
  exit 2
fi
RUN_DIR=$(mktemp -d "$PRIVATE_RESULTS_ROOT/dx-check.XXXXXX")
date -u +%FT%TZ > "$RUN_DIR/started-at.txt"
LC_ALL=C ping -n -c 100 -W 2 "$PROBE_HOST" > "$RUN_DIR/ping.txt"
timeout 45s iperf3 --client "$PROBE_HOST" --connect-timeout 3000 \
  --time 10 --bitrate "$TEST_BITRATE" --json > "$RUN_DIR/iperf-tcp.json"
python3 - "$RUN_DIR/iperf-tcp.json" <<'PY'
import json, math, sys
with open(sys.argv[1]) as stream:
    result = json.load(stream)
if result.get("error") or not isinstance(result.get("end"), dict):
    raise SystemExit("iperf3 result is incomplete or reports an error")
received = result["end"].get("sum_received", {})
for field in ("bits_per_second", "bytes", "seconds"):
    value = received.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise SystemExit("Missing or invalid TCP receiver statistics")
if received["seconds"] <= 0:
    raise SystemExit("Invalid TCP test duration")
print("Saved a completed iperf3 result; compare receiver statistics with the approved test plan.")
PY
printf 'Private observations: %s; this does not establish an AWS latency/throughput guarantee.\n' "$RUN_DIR"
```

전송률을 제한한 TCP 시험으로 회선 최대 용량을 입증하지는 못합니다. 수신 측 처리량, 재전송, 방향, 기간과 혼잡을 확인합니다. 별도로 승인한 UDP 시험에는 `--udp`와 명시적인 bitrate를 사용하고 해당 버전 JSON의 수신 측 loss/jitter를 보존·해석합니다. 실패·생략한 시험은 그대로 기록합니다. 이 감사에서는 네트워크 부하 시험을 실행하지 않았습니다.

## 인증서 갱신 관리

Harbor TLS 서버 인증서, CA 체인, kubelet serving 인증서, EKS 컨트롤 플레인 CA, IAM Roles Anywhere 호스트 인증서 중 무엇을 점검하는지 먼저 구분합니다. CA 인증서가 유효해도 서버 leaf의 유효성을 입증하지 못하며, Node Ready heartbeat는 인증서 만료 정보가 아닙니다. EKS 컨트롤 플레인 인증서는 AWS가 관리하므로 kubeadm 갱신 명령을 EKS 복구 절차로 사용하지 않습니다.

다음 로컬 만료 검사는 파일 누락·읽기 실패·잘못된 인증서 또는 예시 경고 기간 30일 이내의 만료를 실패로 처리합니다. 체인·호스트 이름·폐기 여부나 실제 서비스가 제시하는 인증서를 확인하는 검사는 아닙니다. 실제 endpoint에는 아래 TLS 검사를 사용하고, 호스트 인증서 갱신은 [자격 증명 라이프사이클 절차](./07-node-lifecycle.md)를 따릅니다.

```bash
set -euo pipefail
: "${CERT_PATH:?Set the actual certificate file to inspect}"
test -r "$CERT_PATH"
openssl x509 -in "$CERT_PATH" -checkend 2592000 -noout
```

실제 발급자·담당자, 설정한 인증서 경로, 만료일과 경고 전달을 추적합니다. kubelet serving/client 자격 증명 경로는 설정에 따라 다릅니다. serverTLSBootstrap만 활성화해도 serving CSR이 승인되거나 IAM Roles Anywhere 인증서가 갱신되는 것은 아닙니다.

## Ingress 구성

### ALB Ingress (ip target mode)

자체 관리형 AWS Load Balancer Controller는 `alb.ingress.kubernetes.io/target-type: ip`로 도달 가능한 Hybrid Pod IP를 등록할 수 있습니다. 라우트, 반환 경로, security group/firewall과 EKS remote Pod network 구성이 맞아야 합니다.

AWS 혼합 모드 webhook 예제는 controller를 cloud node에 배치합니다. 이는 해당 설계의 권장 배치이며 Hybrid Node에서 webhook을 실행하는 것이 언제나 불가능하다는 뜻은 아닙니다. Add-on 지침은 control plane에서 설정한 remote Pod CIDR로 접근할 수 있을 때 Hybrid 배치를 허용합니다. label이 없는 노드까지 선택하는 `compute-type NotIn [hybrid]` 대신 관리자가 확인한 배치 label을 사용합니다. 아래 예시 label은 적격 cloud node에만 부여해야 합니다.

```yaml
# Fragment under the controller Deployment's spec.template.spec:
nodeSelector:
  infrastructure.example.com/location: aws
```

### Cilium Ingress Controller

이 절의 Cilium Ingress와 Gateway API 예제는 L7 proxy를 활성화한 Cilium 구성을 전제로 합니다. [EKS Hybrid Nodes Gateway](./10-hybrid-nodes-gateway.md)를 위해 구성한 동일 Cilium 설치에는 함께 적용할 수 없습니다. Gateway의 [AWS 필수 VTEP 설정](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-gateway-cni.html)은 `vtep.enabled=true`, `l7Proxy=false`입니다. 기능을 활성화하기 전에 네트워크 설계를 선택합니다. 이 제약은 Cilium의 L7 proxy 기능에 해당하며, HTTP 애플리케이션이 Gateway의 라우팅 경로를 이용하지 못한다는 뜻은 아닙니다.

Cilium 1.18.3 upstream Ingress에는 NodePort 지원 또는 kube-proxy replacement, L7 proxy와 노출할 load-balancer 경로가 필요합니다. 다음 조각을 적용한다고 혼합 클러스터의 cloud node CNI를 바꿔도 되는 것은 아닙니다. 검토한 Hybrid Cilium 구성을 보존하고 추가 기능의 AWS 지원 범위를 확인합니다. dedicated/shared 전환은 주소 변경과 기존 연결 중단을 일으킬 수 있습니다.

```yaml
# Merge into the reviewed Cilium release values, not a full installation:
nodePort:
  enabled: true
l7Proxy: true
ingressController:
  enabled: true
  loadbalancerMode: dedicated
```

### Cilium Gateway API

선택한 controller 버전이 지원하는 Gateway API CRD·리소스 버전을 설치하고 NodePort/kube-proxy replacement와 L7 전제 조건, GatewayClass/Gateway/Route condition을 확인합니다. Helm flag 하나가 CRD 설치나 외부 도달성을 보장하지 않습니다.

```yaml
# Required Gateway API CRDs and controller prerequisites must already be met:
gatewayAPI:
  enabled: true
```

### LoadBalancer IPAM (Cilium)

다음 pool은 1.18.3 CRD로 확인한 `cilium.io/v2` API를 사용하고 명시한 label이 있는 Service만 선택합니다. 예시 CIDR은 네트워크 인벤토리에서 예약한 비중복 주소 범위로 바꿉니다. IP 할당이 라우터 광고나 실제 통신 성공을 보장하지는 않습니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumLoadBalancerIPPool
metadata:
  name: on-prem-pool
spec:
  blocks:
  - cidr: "10.80.100.0/24"
  serviceSelector:
    matchLabels:
      exposure: onprem-bgp
```

## 로드 밸런싱

### NLB (ip target mode)

자체 관리형 AWS Load Balancer Controller에는 소유권을 지정한 `LoadBalancer` Service의 `spec.loadBalancerClass: service.k8s.aws/nlb`와 `service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip`, 또는 해당 controller의 문서화된 `aws-load-balancer-type: external` 방식을 사용합니다. target-type annotation만으로 controller가 선택되지는 않습니다. AWS에서 Hybrid Pod target과 반환 경로에 접근할 수 있어야 하며 internal/public 노출, subnet과 접근 통제를 명시적으로 정합니다.

이 예시는 EKS Auto Mode 소유권 구성이 아닙니다. 기존 Service의 class/controller를 바꿀 때는 리소스 교체와 트래픽 영향을 검토해야 합니다.

### Cilium LB + BGP

설치한 `cilium.io/v2` schema를 사용합니다. Service 주소 종류의 위치는 `advertisements[].service.addresses`입니다. 아래 예시는 `exposure: onprem-bgp` label이 있는 Service의 LoadBalancer IP만 광고하며, 사실상 모든 Service를 선택하는 `NotIn` 조건을 사용하지 않습니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumBGPAdvertisement
metadata:
  name: hybrid-service-advertisement
  labels:
    advertise: hybrid-services
spec:
  advertisements:
  - advertisementType: Service
    service:
      addresses: [LoadBalancerIP]
    selector:
      matchLabels:
        exposure: onprem-bgp
```

CiliumBGPClusterConfig의 node·peer 선택과 CiliumBGPPeerConfig의 family를 구성합니다. Peer의 advertisement selector는 `advertise: hybrid-services`와 일치해야 하며 Service selector도 실제 Service label과 맞아야 합니다. 검토한 BGP control plane을 활성화하고 router session, 수락된 라우트, next hop, 반환 경로와 traffic policy를 확인합니다. IPPool/Advertisement만으로는 완성된 구성이 아닙니다. 변경 전에 [네트워크 기초](./02-network-configuration.md)와 설치 버전의 BGP 문서를 참고합니다.

## 애드온 상세 설정

### CloudWatch Observability Agent

지원되는 Pod Identity 구성을 사용하고 실제 workload IAM association·권한을 확인합니다. 현재 AWS 절차는 이름과 달리 Pod Identity 환경에서도 Hybrid 호환 변수 `RUN_WITH_IRSA`를 요구합니다. 기존 `AmazonCloudWatchAgent` 리소스의 **spec.env 목록**에 추가하고 `K8S_NODE_NAME` 등 기존 항목을 보존합니다. 임의의 최상위 `env`를 EKS add-on configurationValues에 넣는 형태가 아닙니다.

```yaml
# Add this item to the existing AmazonCloudWatchAgent.spec.env list:
- name: RUN_WITH_IRSA
  value: "True"
```

편집 전에 `amazon-cloudwatch` namespace의 `amazoncloudwatchagents/cloudwatch-agent`를 확인하고 add-on/operator가 이 구성을 어떻게 조정하는지 검토합니다. 이후 agent rollout과 실제 수집을 확인합니다. Hybrid의 cluster/workload/Pod/container 지표는 지원하지만 EC2 IMDS 의존성이 없어 node-level Container Insights 지표는 제공하지 않습니다. Operator가 Hybrid Node에 있으면 control plane webhook 접근 조건도 충족해야 합니다.

### EKS Pod Identity Agent

| 호스트 OS | 문서화된 최소 조건 | Hybrid DaemonSet / credential 경로 |
| --- | --- | --- |
| Ubuntu, RHEL, AL2023 | Add-on 1.3.3-eksbuild.1 | `hybrid`; `/eks-hybrid/.aws/credentials` |
| Bottlerocket (지원되는 VMware variant) | Add-on 1.3.7-eksbuild.2 및 OS 1.39.0 | `hybrid-bottlerocket`; `/var/eks-hybrid/.aws/credentials` |

이는 기능 최소 버전이며 오래된 버전 설치 권장이 아닙니다. 현재 호환되는 add-on 버전과 configuration schema를 확인합니다. Ubuntu/RHEL/AL2023에서는 각 호스트의 기존 전체 NodeConfig에 다음 조각을 병합합니다.

```yaml
# Merge this fragment into each host's complete, protected NodeConfig:
spec:
  hybrid:
    enableCredentialsFile: true
```

AWS 절차는 이미 가입한 노드를 포함하여 대상 호스트마다 계획된 `nodeadm init -c file:///path/to/nodeconfig.yaml` 조정을 요구합니다. 운영 노드를 일괄 재초기화하지 말고 identity·구성을 보존하면서 수명주기 절차에 따라 한 호스트씩 검증합니다. Bottlerocket은 이 nodeadm 조각이 아니라 문서화된 OS 설정 경로를 사용합니다. 임시 credential 파일은 민감하므로 출력하지 않습니다.

Bottlerocket이 아닌 Hybrid DaemonSet을 위한 add-on 설정에는 다음이 포함됩니다.

```json
{
  "daemonsets": {
    "hybrid": {
      "create": true
    }
  }
}
```

Bottlerocket은 선택한 버전의 `hybrid-bottlerocket` 설정을 사용합니다. 기존 설정을 조회·병합하고 add-on이 없을 때만 생성합니다. 이미 설치되어 있으면 무조건 create 또는 OVERWRITE하지 말고 충돌 처리를 검토해 업데이트합니다. Agent와 credential 파일이 애플리케이션별 Pod Identity association을 생성해 주는 것은 아닙니다. Namespace, ServiceAccount, IAM role trust·권한, SDK credential 해석과 실제 인가 성공을 확인합니다.

## 혼합 모드 웹훅 운영

AWS가 지원하는 혼합 모드 패턴은 cloud node의 VPC CNI와 Hybrid Node의 Cilium/Calico를 구분합니다. 이 패턴의 webhook은 cloud 배치를 권장합니다. Hybrid에 배치한 webhook에는 routable remote Pod CIDR와 control-plane 접근이 필요하므로 모든 webhook이 특정 위치에서만 또는 어디서나 동작한다고 가정하지 않습니다.

### CoreDNS 배치

AWS는 이 혼합 모드 설계에서 cloud node와 Hybrid Node에 각각 CoreDNS replica 1개 이상을 권장합니다. Desired replica 2개 이상, 적격 용량, selector, toleration과 실제 endpoint를 확인합니다. `maxSkew: 1`만으로 두 도메인이 생기거나 각각 Pod 1개가 보장되지 않으며 cloud node에는 `eks.amazonaws.com/compute-type` label이 없을 수 있습니다.

`minDomains`를 지원하는 클러스터라면 아래 Pod spec 조각처럼 관리자가 명시한 두 도메인을 사용할 수 있습니다. 의도한 DNS 노드만 표시하고 모든 적격 노드에 확인한 `location` 값 `aws` 또는 `onprem`을 부여합니다. 기존 affinity/toleration과 CoreDNS Pod label을 확인하고 add-on이 지원하는 구성 경로로 조정합니다.

```yaml
# Fragment under CoreDNS Deployment.spec.template.spec.
# Label eligible nodes with exactly aws or onprem in this administrative domain.
nodeSelector:
  infrastructure.example.com/dns-eligible: "true"
topologySpreadConstraints:
- maxSkew: 1
  minDomains: 2
  topologyKey: infrastructure.example.com/location
  whenUnsatisfiable: DoNotSchedule
  labelSelector:
    matchLabels:
      k8s-app: kube-dns
```

적격 도메인 2개와 replica 2개 이상일 때 엄격한 분산이 양쪽 배치를 제한합니다. 한 도메인에 용량이 없으면 새 replica가 Pending일 수 있으므로 이는 가용성 절충이며 failover 보장이 아닙니다. DNS Service/EndpointSlice와 로컬·원격 해석을 실제로 시험합니다. Auto Mode를 포함하면 node-local DNS system service와 non-Auto node에 필요한 Deployment를 구분합니다.

<span id="애드온별-nodeaffinity-설정-가이드"></span>

### 애드온별 배치 가이드

| 애드온 | 이 설계의 배치 | 확인할 사항 |
| --- | --- | --- |
| AWS Load Balancer Controller | AWS 혼합 모드 예제의 cloud node | Webhook 접근, positive label, routable Hybrid IP target |
| CloudWatch agent/operator | 지원하는 노드의 agent; operator webhook은 cloud 권장 | IAM·agent 상태; Hybrid node-level 지표 제외 |
| cert-manager | Webhook cloud 권장; routable Hybrid 배치 가능 | Control-plane 접근과 remote Pod network |
| Metrics Server | Cloud 또는 도달 가능한 Hybrid Pod endpoint | Control-plane→Pod, Metrics-Server→kubelet 경로 |
| CoreDNS | Cloud와 Hybrid replica 확인 | 적격 도메인·용량·실제 DNS 통신 |
| Cilium/Calico | AWS가 지원하는 혼합 CNI 설계의 Hybrid Node | Cloud node의 VPC CNI 유지 |

## 일반적인 문제 해결

### ImagePullBackOff 진단

Pod 이벤트와 참조하는 Secret 이름·유형을 확인하되 레지스트리 자격 증명을 디코딩해 출력하지 않습니다. Secret은 Pod와 같은 namespace에 있어야 합니다. 레지스트리 호스트 이름, 필요한 repository 권한과 만료 여부를 자격 증명 담당자와 확인합니다. 메타데이터만으로 실제 인증 성공을 입증할 수는 없습니다.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the approved cluster context}"
: "${NAMESPACE:?Set the workload namespace}" "${POD:?Set the affected Pod}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" describe pod "$POD"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD" \
  -o jsonpath='{.spec.imagePullSecrets[*].name}{"\n"}'
: "${PULL_SECRET:?Set a referenced imagePullSecret in that namespace}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get secret "$PULL_SECRET" \
  -o jsonpath='{.type}{"\n"}'
```

실제로 문제가 발생한 호스트·네트워크 경로에서 신뢰할 CA와 호스트 이름 검증을 켜고 TLS를 확인합니다. curl -k를 사용하거나 인증하지 않은 registry 401 응답을 TLS 실패로 해석하지 않습니다. 이 예시는 Bash·OpenSSL·GNU timeout을 사용합니다.

```bash
set -euo pipefail
: "${HARBOR_HOST:?Set the registry DNS name, without scheme or port}"
: "${HARBOR_CA_FILE:?Set the approved CA bundle file}"
timeout 10s openssl s_client -connect "$HARBOR_HOST:443" \
  -servername "$HARBOR_HOST" -verify_hostname "$HARBOR_HOST" \
  -verify_return_error -CAfile "$HARBOR_CA_FILE" </dev/null
```

Pod 안에서 DNS·네트워크를 시험하려면 digest로 고정한 승인된 진단 이미지, 전용 namespace와 해당 Hybrid Node 배치를 사용합니다. 무작위로 만든 최신 태그 debug Pod가 클라우드 노드에 배치되면 다른 경로를 검사하게 됩니다. Pod 생성·삭제는 별도로 검토하고 해당 범위의 관측 결과를 보관합니다.

### DNS 해석 문제

실제 CoreDNS Deployment/Pod, Service·EndpointSlice, 클라우드·온프레미스 배치, DNS 설정과 네트워크 도달성을 확인합니다. 문제가 발생한 워크로드 환경에서 레지스트리 이름과 kubernetes.default.svc.cluster.local을 시험합니다. API·DNS·로그 조회 실패는 확인 불가이며 점검 성공이 아닙니다.

전체 CoreDNS Pod 재시작을 기본 진단 절차로 사용하지 않습니다. 실패한 계층을 찾고, 재시작이 필요하면 이중화·복구 확인과 함께 진행합니다. Auto Mode를 포함한 혼합 클러스터는 node-local DNS 경로가 있을 수 있으므로 해당 Pod가 실제 사용하는 resolver를 확인합니다.

### 노드 연결 문제

인벤토리의 실제 Node 이름과 매핑한 호스트를 사용합니다. SSM 기반 Node 이름이 hybrid-로 시작하거나 호스트 이름으로 해석된다고 가정하지 않습니다.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the approved cluster context}" "${NODE:?Set the actual registered Node name}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE" -o wide
kubectl --context "$KUBE_CONTEXT" describe node "$NODE"
```

```bash
# Run on the mapped host, not a hostname guessed from the Node name.
sudo systemctl status kubelet containerd --no-pager
sudo journalctl -u kubelet -u containerd --since '10 minutes ago' \
  --no-pager -n 200
```

자격 증명 공급자와 OS별 에이전트 unit을 확인합니다. Ubuntu에서는 snap 기반 SSM 설치도 고려합니다. 네트워크·인증 진단에는 확인한 `nodeadm debug -c file:///etc/eks/nodeconfig.yaml` 절차를 root 권한으로 사용하고 결과를 비공개로 보관합니다. AWS와 클러스터에 접속하는 진단이며 발급된 자격 증명을 로그에 남기거나 TLS 검증을 끄지 않습니다.

검토한 1.0.20 CLI에는 `nodeadm reset` 하위 명령이 없습니다. NotReady만으로 호스트를 무조건 등록 해제·재초기화하지 않습니다. 원인을 확인한 뒤 마운트·데이터를 보존하고 Node/SSM 식별자를 기록하며 [복구와 식별자 조정 절차](./07-node-lifecycle.md)를 따릅니다.

## 검증 범위와 참고 자료

로컬에서 고정한 리소스 schema, 합성 표본을 사용한 PromQL 식 4개와 백업·네트워크 명령 대체 도구 사례 11개를 검증했습니다. AWS/Kubernetes 변경, 실제 백업·복원, 네트워크 부하 시험, BGP session, exporter 수집이나 운영 rollout은 실행하지 않았습니다. 배포 전에 최신 AWS 지원 문서에서 EKS/OS/CNI/add-on 조합을 확인합니다.

- [AWS Hybrid add-ons](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)
- [AWS Hybrid webhooks](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-webhooks.html)
- [AWS Hybrid upgrades](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-upgrade.html)
- [Prometheus Operator API](https://prometheus-operator.dev/docs/api-reference/api/)
- [Cilium 1.18.3 Ingress prerequisites](https://github.com/cilium/cilium/blob/v1.18.3/Documentation/network/servicemesh/ingress.rst)
- [Cilium 1.18.3 LoadBalancer IPPool CRD](https://github.com/cilium/cilium/blob/v1.18.3/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumloadbalancerippools.yaml)
- [iperf3 invocation](https://software.es.net/iperf/invoking.html)
- [Kubernetes taint tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)


---

< [이전: 노드 라이프사이클 관리](./07-node-lifecycle.md) | [목차](./README.md) | [다음: 베어메탈 서버 OS 설치](./09-bare-metal-os-setup.md) >

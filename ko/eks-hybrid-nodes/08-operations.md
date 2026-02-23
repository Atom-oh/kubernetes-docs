# 운영 및 유지보수

< [이전: 노드 라이프사이클 관리](./07-node-lifecycle.md) | [목차](./README.md) | [다음: 베어메탈 서버 OS 설치](./09-bare-metal-os-setup.md) >

> **지원 버전**: EKS 1.31+, nodeadm 0.1+
> **마지막 업데이트**: 2026년 2월 23일

이 문서에서는 EKS Hybrid Nodes 환경의 운영 및 유지보수 절차를 다룹니다.

## Harbor 취약점 스캔 자동화

```yaml
# harbor-scan-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: harbor-vulnerability-scan
  namespace: harbor
spec:
  schedule: "0 2 * * *"  # 매일 오전 2시
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: scanner
            image: curlimages/curl:latest
            command:
            - /bin/sh
            - -c
            - |
              # 모든 프로젝트의 이미지 스캔 트리거
              for project in $(curl -sk -u admin:$HARBOR_PASSWORD \
                "https://harbor.internal.company.io/api/v2.0/projects" | \
                jq -r '.[].name'); do

                for repo in $(curl -sk -u admin:$HARBOR_PASSWORD \
                  "https://harbor.internal.company.io/api/v2.0/projects/$project/repositories" | \
                  jq -r '.[].name'); do

                  # 최신 태그 스캔
                  curl -sk -X POST -u admin:$HARBOR_PASSWORD \
                    "https://harbor.internal.company.io/api/v2.0/projects/$project/repositories/${repo#*/}/artifacts/latest/scan"
                done
              done
            env:
            - name: HARBOR_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: harbor-admin-secret
                  key: password
          restartPolicy: OnFailure
```

## 데이터베이스 백업 절차

```bash
#!/bin/bash
# harbor-backup.sh - Harbor 데이터베이스 백업 스크립트

BACKUP_DIR="/backup/harbor/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# PostgreSQL 백업
kubectl exec -n harbor harbor-database-0 -- \
  pg_dump -U postgres registry > $BACKUP_DIR/registry.sql

kubectl exec -n harbor harbor-database-0 -- \
  pg_dump -U postgres notarysigner > $BACKUP_DIR/notarysigner.sql

kubectl exec -n harbor harbor-database-0 -- \
  pg_dump -U postgres notaryserver > $BACKUP_DIR/notaryserver.sql

# Redis 백업
kubectl exec -n harbor harbor-redis-0 -- \
  redis-cli BGSAVE

kubectl cp harbor/harbor-redis-0:/data/dump.rdb $BACKUP_DIR/redis-dump.rdb

# 레지스트리 데이터 백업 (선택사항 - 대용량)
# kubectl exec -n harbor harbor-registry-xxx -- \
#   tar czf - /storage > $BACKUP_DIR/registry-storage.tar.gz

echo "백업 완료: $BACKUP_DIR"
ls -la $BACKUP_DIR
```

## Prometheus 메트릭 수집

```yaml
# hybrid-node-servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: hybrid-nodes
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: kubelet
  namespaceSelector:
    matchNames:
    - kube-system
  endpoints:
  - port: https-metrics
    scheme: https
    tlsConfig:
      insecureSkipVerify: true
    bearerTokenFile: /var/run/secrets/kubernetes.io/serviceaccount/token
    relabelings:
    - sourceLabels: [__meta_kubernetes_node_label_topology_kubernetes_io_zone]
      regex: on-premises
      action: keep
---
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: gpu-metrics
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: nvidia-dcgm-exporter
  namespaceSelector:
    matchNames:
    - gpu-operator
  podMetricsEndpoints:
  - port: metrics
    interval: 15s
```

### Grafana 대시보드 쿼리 예시

```promql
# Hybrid Node CPU 사용률
100 - (avg by (node) (rate(node_cpu_seconds_total{mode="idle", node=~"hybrid-.*"}[5m])) * 100)

# Hybrid Node 메모리 사용률
(1 - (node_memory_MemAvailable_bytes{node=~"hybrid-.*"} / node_memory_MemTotal_bytes{node=~"hybrid-.*"})) * 100

# GPU 사용률 (DCGM)
DCGM_FI_DEV_GPU_UTIL{kubernetes_node=~"hybrid-gpu-.*"}

# GPU 메모리 사용률
DCGM_FI_DEV_FB_USED{kubernetes_node=~"hybrid-gpu-.*"} / DCGM_FI_DEV_FB_FREE{kubernetes_node=~"hybrid-gpu-.*"} * 100
```

## Direct Connect 성능 검증

```bash
#!/bin/bash
# network-validation.sh - Direct Connect 네트워크 성능 검증

echo "=== Direct Connect 성능 검증 ==="

# 타겟 설정
EKS_API_ENDPOINT="XXXXXXXX.gr7.ap-northeast-2.eks.amazonaws.com"
AWS_VPC_HOST="10.0.1.100"

# 지연시간 테스트
echo ""
echo "1. 지연시간 테스트 (목표: <5ms)"
LATENCY=$(ping -c 100 $AWS_VPC_HOST | tail -1 | awk '{print $4}' | cut -d'/' -f2)
echo "   평균 지연시간: ${LATENCY}ms"
if (( $(echo "$LATENCY < 5" | bc -l) )); then
    echo "   [PASS] 지연시간 목표 충족"
else
    echo "   [WARN] 지연시간이 목표(5ms)를 초과합니다"
fi

# 지터 테스트
echo ""
echo "2. 지터 테스트 (목표: <2ms)"
JITTER=$(ping -c 100 $AWS_VPC_HOST | tail -1 | awk '{print $4}' | cut -d'/' -f4)
echo "   지터: ${JITTER}ms"
if (( $(echo "$JITTER < 2" | bc -l) )); then
    echo "   [PASS] 지터 목표 충족"
else
    echo "   [WARN] 지터가 목표(2ms)를 초과합니다"
fi

# 패킷 손실 테스트
echo ""
echo "3. 패킷 손실 테스트 (목표: <0.01%)"
PACKET_LOSS=$(ping -c 1000 $AWS_VPC_HOST | grep "packet loss" | awk '{print $6}' | tr -d '%')
echo "   패킷 손실률: ${PACKET_LOSS}%"
if (( $(echo "$PACKET_LOSS < 0.01" | bc -l) )); then
    echo "   [PASS] 패킷 손실 목표 충족"
else
    echo "   [WARN] 패킷 손실이 목표(0.01%)를 초과합니다"
fi

# 대역폭 테스트 (iperf3 필요)
echo ""
echo "4. 대역폭 테스트 (목표: >1Gbps)"
if command -v iperf3 &> /dev/null; then
    BANDWIDTH=$(iperf3 -c $AWS_VPC_HOST -t 10 -f g | grep "sender" | awk '{print $7}')
    echo "   대역폭: ${BANDWIDTH} Gbps"
else
    echo "   [SKIP] iperf3가 설치되지 않았습니다"
fi

echo ""
echo "=== 검증 완료 ==="
```

## 인증서 갱신 관리

```bash
#!/bin/bash
# cert-renewal.sh - 인증서 만료 확인 및 갱신 알림

# Harbor 인증서 만료일 확인
echo "=== 인증서 만료 확인 ==="

HARBOR_CERT="/etc/ssl/certs/harbor-ca.crt"
DAYS_WARNING=30

if [ -f "$HARBOR_CERT" ]; then
    EXPIRY_DATE=$(openssl x509 -enddate -noout -in $HARBOR_CERT | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
    NOW_EPOCH=$(date +%s)
    DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))

    echo "Harbor CA 인증서"
    echo "  만료일: $EXPIRY_DATE"
    echo "  남은 일수: $DAYS_LEFT일"

    if [ $DAYS_LEFT -lt $DAYS_WARNING ]; then
        echo "  [WARN] 인증서 갱신이 필요합니다!"
        # 알림 전송 (Slack, Email 등)
    else
        echo "  [OK] 인증서 유효"
    fi
fi

# Kubernetes 인증서 확인
echo ""
echo "Kubernetes 클러스터 인증서"
kubectl get nodes -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].lastHeartbeatTime}'
```

## Ingress 구성

### ALB Ingress (ip target mode)

AWS Load Balancer Controller는 하이브리드 노드에서 `target-type: ip` 모드로 지원됩니다:

- 라우팅 가능한 파드 CIDR 필요 (BGP 또는 정적 라우트)
- 컨트롤러는 클라우드 노드에서만 실행해야 함 (웹훅 요구사항)

```yaml
# ALB Ingress에서 클라우드 노드 nodeAffinity 설정
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: eks.amazonaws.com/compute-type
          operator: NotIn
          values:
          - hybrid
```

### Cilium Ingress Controller

```yaml
# Cilium Ingress 활성화 (Helm values)
ingressController:
  enabled: true
  loadbalancerMode: dedicated  # 또는 shared
```

### Cilium Gateway API

```yaml
# Gateway API 활성화 (Helm values)
gatewayAPI:
  enabled: true
```

### LoadBalancer IPAM (Cilium)

온프레미스 환경에서 LoadBalancer 타입 서비스에 IP를 할당하려면:

```yaml
# CiliumLoadBalancerIPPool
apiVersion: cilium.io/v2alpha1
kind: CiliumLoadBalancerIPPool
metadata:
  name: on-prem-pool
spec:
  blocks:
  - cidr: "10.80.100.0/24"
```

## 로드 밸런싱

### NLB (ip target mode)

NLB는 ip target 타입으로 하이브리드 노드를 지원합니다:

- 타겟은 파드 IP로 등록됨 (라우팅 가능한 파드 CIDR 필요)
- Service annotation: `service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip`

### Cilium LB + BGP

Cilium은 온프레미스 서비스를 위한 LoadBalancer로 작동할 수 있습니다:

- BGP 광고와 결합하면 외부 IP가 네트워크에서 접근 가능
- `CiliumBGPAdvertisement`에서 `advertisementType: Service` + `addresses: [ExternalIP, LoadBalancerIP]` 설정

```yaml
# CiliumBGPAdvertisement 예시
apiVersion: cilium.io/v2alpha1
kind: CiliumBGPAdvertisement
metadata:
  name: service-advertisement
spec:
  advertisements:
  - advertisementType: Service
    selector:
      matchExpressions:
      - key: somekey
        operator: NotIn
        values: ['never-match-this']
    addresses: [ExternalIP, LoadBalancerIP]
```

## 애드온 상세 설정

### CloudWatch Observability Agent

CloudWatch 에이전트에서 IRSA 대신 Pod Identity 사용:

```yaml
# CloudWatch agent configurationValues
configurationValues: |
  {
    "agent": {
      "config": {
        "logs": { "metrics_collected": { "kubernetes": {} } }
      }
    },
    "env": [
      { "name": "RUN_WITH_IRSA", "value": "true" }
    ]
  }
```

### EKS Pod Identity Agent

```yaml
# NodeConfig에서 enableCredentialsFile 설정
spec:
  hybrid:
    enableCredentialsFile: true
```

```bash
# 애드온 설치 시 hybrid DaemonSet 활성화
aws eks create-addon \
  --cluster-name my-hybrid-cluster \
  --addon-name eks-pod-identity-agent \
  --configuration-values '{"daemonsets":{"hybrid":{"create": true}}}'
```

## 혼합 모드 웹훅 운영

하이브리드 노드와 클라우드 노드가 혼합된 환경에서 웹훅 기반 애드온의 배치 전략입니다.

### CoreDNS 배치

`topologySpreadConstraints`를 사용하여 클라우드와 온프레미스 양쪽에 배치:

```yaml
topologySpreadConstraints:
- maxSkew: 1
  topologyKey: eks.amazonaws.com/compute-type
  whenUnsatisfiable: DoNotSchedule
  labelSelector:
    matchLabels:
      k8s-app: kube-dns
```

### 애드온별 nodeAffinity 설정 가이드

| 애드온 | 권장 배치 | 이유 |
|--------|----------|------|
| AWS Load Balancer Controller | 클라우드 노드 전용 | 웹훅 필요, VPC 통합 |
| CloudWatch Agent | DaemonSet 전체, 웹훅은 클라우드 | 메트릭 수집은 전체 노드, 웹훅은 클라우드 |
| cert-manager | 클라우드 노드 전용 | 웹훅 필요 |
| Metrics Server | 클라우드 노드 권장 | 라우팅 가능한 파드 CIDR 필요 |
| CoreDNS | 양쪽 분산 | DNS 복원력 |
| Cilium | 하이브리드 노드 전용 | 온프레미스 CNI |

## 일반적인 문제 해결

### ImagePullBackOff 진단

```bash
# 문제 파드 확인
kubectl get pods --all-namespaces | grep ImagePullBackOff

# 상세 정보 확인
kubectl describe pod <pod-name> -n <namespace>

# 일반적인 원인 및 해결책:
# 1. Harbor 인증 실패
kubectl get secret harbor-registry-secret -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d | jq

# 2. 인증서 문제 확인
openssl s_client -connect harbor.internal.company.io:443 -CAfile /etc/ssl/certs/harbor-ca.crt

# 3. DNS 해석 문제
kubectl run dns-debug --rm -it --image=busybox --restart=Never -- nslookup harbor.internal.company.io

# 4. 네트워크 연결 문제
kubectl run net-debug --rm -it --image=nicolaka/netshoot --restart=Never -- curl -v https://harbor.internal.company.io/v2/
```

### DNS 해석 문제

```bash
# CoreDNS 로그 확인
kubectl logs -n kube-system -l k8s-app=kube-dns -f

# DNS 쿼리 테스트
kubectl run dnsutils --rm -it --image=gcr.io/kubernetes-e2e-test-images/dnsutils:1.3 --restart=Never -- bash
# Pod 내에서:
nslookup harbor.internal.company.io
nslookup kubernetes.default.svc.cluster.local
dig +short harbor.internal.company.io

# CoreDNS 재시작
kubectl rollout restart deployment coredns -n kube-system
```

### 노드 연결 문제

```bash
# 노드 상태 확인
kubectl get nodes
kubectl describe node hybrid-node-001

# kubelet 로그 확인 (노드에서 실행)
sudo journalctl -u kubelet -f --since "10 minutes ago"

# API 서버 연결 테스트 (노드에서 실행)
curl -k https://<EKS-API-ENDPOINT>:443/healthz

# SSM Agent 상태 확인 (노드에서 실행)
sudo systemctl status amazon-ssm-agent

# 노드 재등록
sudo nodeadm reset
sudo nodeadm init -c file://nodeconfig.yaml
```

---

< [이전: 노드 라이프사이클 관리](./07-node-lifecycle.md) | [목차](./README.md) | [다음: 베어메탈 서버 OS 설치](./09-bare-metal-os-setup.md) >

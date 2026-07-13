# 運用とメンテナンス

< [前へ: Node Lifecycle Management](./07-node-lifecycle.md) | [目次](./README.md) | [次へ: Bare Metal OS Setup](./09-bare-metal-os-setup.md) >

> **サポート対象バージョン**: EKS 1.31+, Prometheus Operator
> **最終更新**: February 23, 2026

このドキュメントでは、EKS Hybrid Nodes 環境の日常的な運用とメンテナンスタスクについて説明します。これには、monitoring、backup 手順、および troubleshooting が含まれます。

## Harbor 脆弱性スキャン自動化

```yaml
# harbor-scan-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: harbor-vulnerability-scan
  namespace: harbor
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
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
              # Trigger scan for all project images
              for project in $(curl -sk -u admin:$HARBOR_PASSWORD \
                "https://harbor.internal.company.io/api/v2.0/projects" | \
                jq -r '.[].name'); do

                for repo in $(curl -sk -u admin:$HARBOR_PASSWORD \
                  "https://harbor.internal.company.io/api/v2.0/projects/$project/repositories" | \
                  jq -r '.[].name'); do

                  # Scan latest tag
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

## Database Backup 手順

```bash
#!/bin/bash
# harbor-backup.sh - Harbor Database Backup Script

BACKUP_DIR="/backup/harbor/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# PostgreSQL backup
kubectl exec -n harbor harbor-database-0 -- \
  pg_dump -U postgres registry > $BACKUP_DIR/registry.sql

kubectl exec -n harbor harbor-database-0 -- \
  pg_dump -U postgres notarysigner > $BACKUP_DIR/notarysigner.sql

kubectl exec -n harbor harbor-database-0 -- \
  pg_dump -U postgres notaryserver > $BACKUP_DIR/notaryserver.sql

# Redis backup
kubectl exec -n harbor harbor-redis-0 -- \
  redis-cli BGSAVE

kubectl cp harbor/harbor-redis-0:/data/dump.rdb $BACKUP_DIR/redis-dump.rdb

# Registry data backup (optional - large)
# kubectl exec -n harbor harbor-registry-xxx -- \
#   tar czf - /storage > $BACKUP_DIR/registry-storage.tar.gz

echo "Backup complete: $BACKUP_DIR"
ls -la $BACKUP_DIR
```

## Prometheus Metrics 収集

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

### Grafana Dashboard Query 例

```promql
# Hybrid Node CPU Usage
100 - (avg by (node) (rate(node_cpu_seconds_total{mode="idle", node=~"hybrid-.*"}[5m])) * 100)

# Hybrid Node Memory Usage
(1 - (node_memory_MemAvailable_bytes{node=~"hybrid-.*"} / node_memory_MemTotal_bytes{node=~"hybrid-.*"})) * 100

# GPU Usage (DCGM)
DCGM_FI_DEV_GPU_UTIL{kubernetes_node=~"hybrid-gpu-.*"}

# GPU Memory Usage
DCGM_FI_DEV_FB_USED{kubernetes_node=~"hybrid-gpu-.*"} / DCGM_FI_DEV_FB_FREE{kubernetes_node=~"hybrid-gpu-.*"} * 100
```

## Direct Connect パフォーマンス検証

```bash
#!/bin/bash
# network-validation.sh - Direct Connect Network Performance Validation

echo "=== Direct Connect Performance Validation ==="

# Target configuration
EKS_API_ENDPOINT="XXXXXXXX.gr7.ap-northeast-2.eks.amazonaws.com"
AWS_VPC_HOST="10.0.1.100"

# Latency test
echo ""
echo "1. Latency Test (Target: <5ms)"
LATENCY=$(ping -c 100 $AWS_VPC_HOST | tail -1 | awk '{print $4}' | cut -d'/' -f2)
echo "   Average Latency: ${LATENCY}ms"
if (( $(echo "$LATENCY < 5" | bc -l) )); then
    echo "   [PASS] Latency target met"
else
    echo "   [WARN] Latency exceeds target (5ms)"
fi

# Jitter test
echo ""
echo "2. Jitter Test (Target: <2ms)"
JITTER=$(ping -c 100 $AWS_VPC_HOST | tail -1 | awk '{print $4}' | cut -d'/' -f4)
echo "   Jitter: ${JITTER}ms"
if (( $(echo "$JITTER < 2" | bc -l) )); then
    echo "   [PASS] Jitter target met"
else
    echo "   [WARN] Jitter exceeds target (2ms)"
fi

# Packet loss test
echo ""
echo "3. Packet Loss Test (Target: <0.01%)"
PACKET_LOSS=$(ping -c 1000 $AWS_VPC_HOST | grep "packet loss" | awk '{print $6}' | tr -d '%')
echo "   Packet Loss Rate: ${PACKET_LOSS}%"
if (( $(echo "$PACKET_LOSS < 0.01" | bc -l) )); then
    echo "   [PASS] Packet loss target met"
else
    echo "   [WARN] Packet loss exceeds target (0.01%)"
fi

# Bandwidth test (requires iperf3)
echo ""
echo "4. Bandwidth Test (Target: >1Gbps)"
if command -v iperf3 &> /dev/null; then
    BANDWIDTH=$(iperf3 -c $AWS_VPC_HOST -t 10 -f g | grep "sender" | awk '{print $7}')
    echo "   Bandwidth: ${BANDWIDTH} Gbps"
else
    echo "   [SKIP] iperf3 not installed"
fi

echo ""
echo "=== Validation Complete ==="
```

## Certificate 更新管理

```bash
#!/bin/bash
# cert-renewal.sh - Certificate Expiration Check and Renewal Alert

# Check Harbor certificate expiration
echo "=== Certificate Expiration Check ==="

HARBOR_CERT="/etc/ssl/certs/harbor-ca.crt"
DAYS_WARNING=30

if [ -f "$HARBOR_CERT" ]; then
    EXPIRY_DATE=$(openssl x509 -enddate -noout -in $HARBOR_CERT | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
    NOW_EPOCH=$(date +%s)
    DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))

    echo "Harbor CA Certificate"
    echo "  Expiry Date: $EXPIRY_DATE"
    echo "  Days Remaining: $DAYS_LEFT days"

    if [ $DAYS_LEFT -lt $DAYS_WARNING ]; then
        echo "  [WARN] Certificate renewal required!"
        # Send alert (Slack, Email, etc.)
    else
        echo "  [OK] Certificate valid"
    fi
fi

# Check Kubernetes certificate
echo ""
echo "Kubernetes Cluster Certificate"
kubectl get nodes -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].lastHeartbeatTime}'
```

## Ingress 設定

### ALB Ingress (ip target mode)

AWS Load Balancer Controller は、`target-type: ip` mode で hybrid nodes をサポートします:

- routable pod CIDRs (BGP または static routes) が必要です
- Controller は cloud nodes 上でのみ実行する必要があります (webhook 要件)

```yaml
# Cloud node nodeAffinity for ALB Ingress
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
# Enable Cilium Ingress (Helm values)
ingressController:
  enabled: true
  loadbalancerMode: dedicated  # or shared
```

### Cilium Gateway API

```yaml
# Enable Gateway API (Helm values)
gatewayAPI:
  enabled: true
```

### LoadBalancer IPAM (Cilium)

On-premises environments で LoadBalancer type services に IP を割り当てるには:

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

## Load Balancing

### NLB (ip target mode)

NLB は ip target type で hybrid nodes をサポートします:

- Targets は pod IP によって登録されます (routable pod CIDRs が必要)
- Service annotation: `service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip`

### Cilium LB + BGP

Cilium は on-premises services の LoadBalancer として機能できます:

- BGP advertisement と組み合わせることで、external IPs は network から到達可能になります
- `advertisementType: Service` + `addresses: [ExternalIP, LoadBalancerIP]` を指定して `CiliumBGPAdvertisement` を設定します

```yaml
# CiliumBGPAdvertisement example
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

## Add-on 詳細設定

### CloudWatch Observability Agent

CloudWatch agent では、IRSA の代わりに Pod Identity を使用します:

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
# enableCredentialsFile in NodeConfig
spec:
  hybrid:
    enableCredentialsFile: true
```

```bash
# Enable hybrid DaemonSet when installing add-on
aws eks create-addon \
  --cluster-name my-hybrid-cluster \
  --addon-name eks-pod-identity-agent \
  --configuration-values '{"daemonsets":{"hybrid":{"create": true}}}'
```

## Mixed-Mode Webhook 運用

hybrid nodes と cloud nodes の両方がある環境における webhook-based add-ons の配置戦略です。

### CoreDNS 配置

`topologySpreadConstraints` を使用して cloud と on-premises に分散します:

```yaml
topologySpreadConstraints:
- maxSkew: 1
  topologyKey: eks.amazonaws.com/compute-type
  whenUnsatisfiable: DoNotSchedule
  labelSelector:
    matchLabels:
      k8s-app: kube-dns
```

### Add-on ごとの nodeAffinity 設定ガイド

| Add-on | 推奨配置 | 理由 |
|--------|----------------------|--------|
| AWS Load Balancer Controller | Cloud nodes のみ | Webhook が必要、VPC integration |
| CloudWatch Agent | すべての nodes 上に DaemonSet、cloud 上に webhook | すべての nodes で Metrics collection、cloud で webhook |
| cert-manager | Cloud nodes のみ | Webhook が必要 |
| Metrics Server | Cloud nodes を推奨 | routable pod CIDR が必要 |
| CoreDNS | 両方に分散 | DNS resilience |
| Cilium | Hybrid nodes のみ | On-premises CNI |

## 一般的な Troubleshooting

### ImagePullBackOff 診断

```bash
# Check problem pods
kubectl get pods --all-namespaces | grep ImagePullBackOff

# Check details
kubectl describe pod <pod-name> -n <namespace>

# Common causes and solutions:
# 1. Harbor authentication failure
kubectl get secret harbor-registry-secret -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d | jq

# 2. Certificate issue check
openssl s_client -connect harbor.internal.company.io:443 -CAfile /etc/ssl/certs/harbor-ca.crt

# 3. DNS resolution issue
kubectl run dns-debug --rm -it --image=busybox --restart=Never -- nslookup harbor.internal.company.io

# 4. Network connectivity issue
kubectl run net-debug --rm -it --image=nicolaka/netshoot --restart=Never -- curl -v https://harbor.internal.company.io/v2/
```

### DNS 解決の問題

```bash
# Check CoreDNS logs
kubectl logs -n kube-system -l k8s-app=kube-dns -f

# DNS query test
kubectl run dnsutils --rm -it --image=gcr.io/kubernetes-e2e-test-images/dnsutils:1.3 --restart=Never -- bash
# Inside Pod:
nslookup harbor.internal.company.io
nslookup kubernetes.default.svc.cluster.local
dig +short harbor.internal.company.io

# Restart CoreDNS
kubectl rollout restart deployment coredns -n kube-system
```

### Node 接続の問題

```bash
# Check node status
kubectl get nodes
kubectl describe node hybrid-node-001

# Check kubelet logs (run on node)
sudo journalctl -u kubelet -f --since "10 minutes ago"

# API server connection test (run on node)
curl -k https://<EKS-API-ENDPOINT>:443/healthz

# Check SSM Agent status (run on node)
sudo systemctl status amazon-ssm-agent

# Re-register node
sudo nodeadm reset
sudo nodeadm init -c file://nodeconfig.yaml
```

---

< [前へ: Node Lifecycle Management](./07-node-lifecycle.md) | [目次](./README.md) | [次へ: Bare Metal OS Setup](./09-bare-metal-os-setup.md) >

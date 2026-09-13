# EKS Hybrid Nodes 네트워크 구성 퀴즈

> **관련 문서**: [네트워크 구성](../../eks-hybrid-nodes/02-network-configuration.md)
> **마지막 업데이트**: 2026년 9월 12일

## 객관식 문제

### 1. 필요한 양방향 hybrid network 경로를 제공하는 접근은 무엇인가요?

- A) Public internet만
- B) 실제 route·firewall을 검토한 Direct Connect/VPN 설계
- C) SSH tunnel만
- D) HTTP proxy만

<details>
<summary>정답 보기</summary>

**정답: B) 실제 route·firewall을 검토한 Direct Connect/VPN 설계**

**설명:**
Node→AWS뿐 아니라 control plane→kubelet·해당 Pod endpoint 접근도 필요합니다. Public Kubernetes API를 써도 private 역방향 요구는 없어지지 않습니다. Direct Connect가 모든 통신 암호화·latency를 보장하지도 않습니다. VPN resource `available`만 보지 말고 실제 tunnel 상태를 확인하세요. 본문에서 계정/context와 private WORK_DIR를 설정한 뒤 아래 읽기 전용 진단을 사용합니다.
```bash
: "${VPN_ID:?Select the reviewed VPN connection}"
: "${TUNNEL_IP:?Select its actual AWS tunnel outside IP}"
check_account
# Select telemetry only: do not dump customer gateway configuration or pre-shared keys.
aws ec2 describe-vpn-connections --region "$AWS_REGION" --vpn-connection-ids "$VPN_ID" \
  --query 'VpnConnections[].{id:VpnConnectionId,state:State,telemetry:VgwTelemetry}' \
  --output json > "$WORK_DIR/vpn-state.json"
jq -e --arg ip "$TUNNEL_IP" 'length==1 and any(.[0].telemetry[]?; .OutsideIpAddress==$ip)' \
  "$WORK_DIR/vpn-state.json" >/dev/null
export VPN_ID TUNNEL_IP
python3 - <<'PY'
import ipaddress, json, os
from datetime import datetime, timedelta, timezone
from pathlib import Path
ipaddress.ip_address(os.environ["TUNNEL_IP"])
now = datetime.now(timezone.utc)
end = now.replace(minute=now.minute - now.minute % 5, second=0, microsecond=0)
body = {"Namespace": "AWS/VPN", "MetricName": "TunnelState",
        "Dimensions": [{"Name": "VpnId", "Value": os.environ["VPN_ID"]},
                       {"Name": "TunnelIpAddress", "Value": os.environ["TUNNEL_IP"]}],
        "StartTime": (end - timedelta(minutes=15)).isoformat(), "EndTime": end.isoformat(),
        "Period": 300, "Statistics": ["Minimum", "Maximum"]}
(Path(os.environ["WORK_DIR"]) / "vpn-metric-request.json").write_text(json.dumps(body, indent=2) + "\n")
PY
aws cloudwatch get-metric-statistics --region "$AWS_REGION" \
  --cli-input-json "file://$WORK_DIR/vpn-metric-request.json" --output json \
  > "$WORK_DIR/vpn-metric-result.json"
jq '{label:.Label,datapoints:(.Datapoints|sort_by(.Timestamp))}' "$WORK_DIR/vpn-metric-result.json"
```


</details>

### 2. Node의 Kubernetes API 연결 port는 무엇인가요?

- A) TCP22
- B) TCP443
- C) 기본 TCP8080
- D) TCP3306

<details>
<summary>정답 보기</summary>

**정답: B) TCP443**

**설명:**
역방향 control-plane→kubelet은 secure TCP10250이며 webhook/aggregated API는 실제 설정 port를 사용합니다. 인증 없는 10255를 현대적인 요구로 열지 마세요. Cluster CA·hostname을 검증합니다. HTTP401/403은 TLS 도달과 미충족 권한일 수 있으며 app health 성공은 아닙니다.
```bash
set -euo pipefail
endpoint=$(jq -er '.cluster.endpoint' "$WORK_DIR/cluster.json")
case "$endpoint" in https://*) ;; *) printf 'HTTPS endpoint required.\n' >&2; exit 1;; esac
jq -er '.cluster.certificateAuthority.data' "$WORK_DIR/cluster.json" |
  base64 --decode > "$WORK_DIR/cluster-ca.pem"
openssl x509 -in "$WORK_DIR/cluster-ca.pem" -noout >/dev/null
curl --silent --show-error --connect-timeout 5 --max-time 15 \
  --cacert "$WORK_DIR/cluster-ca.pem" --output "$WORK_DIR/api-response.txt" \
  --write-out '{"httpCode":%{http_code},"remoteIP":"%{remote_ip}","dnsTotalSeconds":%{time_namelookup},"connectTotalSeconds":%{time_connect},"tlsTotalSeconds":%{time_appconnect},"totalSeconds":%{time_total}}\n' \
  "$endpoint/readyz" > "$WORK_DIR/api-timing.json"
cat "$WORK_DIR/api-timing.json"
```


</details>

### 3. 인터넷 없는 설계에서 private ECR image pull 부분에 관련된 서비스는 무엇인가요?

- A) ecr.api·ecr.dkr와 적절한 private S3 layer 경로
- B) Lambda·DynamoDB·SNS만
- C) EC2 metadata만
- D) EKS 관리 endpoint만

<details>
<summary>정답 보기</summary>

**정답: A) ecr.api·ecr.dkr와 적절한 private S3 layer 경로**

**설명:**
Credential provider·EKS 관리·Kubernetes API·workload service는 별도 요구가 있습니다. Private ECR endpoint가 public ECR/CloudFront를 private으로 만들지는 않습니다. S3 interface는 private DNS를 지원하고 inbound-Resolver-only에는 VPC 내부용 S3 gateway가 필요합니다. EKS 관리 interface는 Kubernetes API endpoint가 아니며 DNS alias로 다른 TLS hostname 문제를 고칠 수도 없습니다.

</details>

### 4. Hybrid Pod 주소 계획의 요구가 아닌 것은 무엇인가요?

- A) Remote node/VPC/Service 대역과 비중첩
- B) 실제 node/Pod 수요에 맞는 크기
- C) 모든 Pod pool은 반드시 /8
- D) Cluster 간 분리·return routing

<details>
<summary>정답 보기</summary>

**정답: C) 모든 Pod pool은 반드시 /8**

**설명:**
IPv4 RFC1918/CGNAT와 문서화된 remote-CIDR 한도를 사용합니다. Cluster-pool Cilium은 kubelet에 cluster 전체 Pod CIDR을 넣는 대신 Cilium에서 pool을 설정합니다. 다음 새 pool 예제를 기존 할당 pool 변경 지시로 사용하지 마세요. 실제 CiliumNode 할당을 읽으며 block 순서·사용 가능한 Pod 용량은 보장되지 않습니다.
```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.85.0.0/16
    clusterPoolIPv4MaskSize: 25
```


</details>

### 5. Cluster DNS 주소는 어떻게 결정해야 하나요?

- A) 항상 8.8.8.8
- B) 실제 kube-dns Service 또는 의도적으로 구성한 local-DNS 설계 확인
- C) 항상 10.100.0.10
- D) EC2 metadata 주소 사용

<details>
<summary>정답 보기</summary>

**정답: B) 실제 kube-dns Service 또는 의도적으로 구성한 local-DNS 설계 확인**

**설명:**
`10.100.0.10`은 특정 Service CIDR의 예시입니다. 실제 Service IP·EndpointSlice·node resolver를 확인하세요. DNS 배치만으로 local routing이 보장되지 않으며 Service Traffic Distribution·지원 dataplane 설정이 필요합니다. Soft spread도 CoreDNS 2+2 배치를 입증하지 않습니다.
```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n kube-system \
  get service kube-dns -o json |
  jq '{name:.metadata.name,uid:.metadata.uid,clusterIP:.spec.clusterIP,
       clusterIPs:.spec.clusterIPs,ports:.spec.ports,trafficDistribution:.spec.trafficDistribution}'
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n kube-system \
  get endpointslices -l kubernetes.io/service-name=kube-dns -o json |
  jq '[.items[]|{name:.metadata.name,addressType,ports,
       endpoints:[.endpoints[]?|{addresses,nodeName,zone,conditions,hints}]}]'
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n kube-system \
  get pods -l k8s-app=kube-dns -o json |
  jq '[.items[]|{name:.metadata.name,node:.spec.nodeName,phase:.status.phase,
       ready:([.status.conditions[]?|select(.type=="Ready")|.status]|first // "NotReported")}]'
```


</details>

### 6. AWS hybrid network latency 안내를 어떻게 해석해야 하나요?

- A) 500ms가 보장 한도
- B) RTT 약 200ms 이하가 일반 안내이며 workload로 검증
- C) 100ms가 엄격한 보편적 요구
- D) Direct Connect는 항상 10ms 미만 보장

<details>
<summary>정답 보기</summary>

**정답: B) RTT 약 200ms 이하가 일반 안내이며 workload로 검증**

**설명:**
AWS의 100Mbps도 일반 안내이며 workload와 무관한 합격 임계값이 아닙니다. 이전 <50/50–100/100–200/>200ms 등급·Direct Connect <10ms는 미검증 예시입니다. Curl DNS/connect/TLS 시간은 누적 단계이지 순수 RTT가 아니고 ICMP 무응답은 API 실패 증거가 아닙니다. 실제 앱·API·image·telemetry 동작을 측정하세요.

</details>

## 참고 자료

- [Hybrid networking](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
- [EKS PrivateLink](https://docs.aws.amazon.com/eks/latest/userguide/vpc-interface-endpoints.html)
- [S3 private DNS](https://docs.aws.amazon.com/AmazonS3/latest/userguide/privatelink-interface-endpoints.html)
- [VPN metrics](https://docs.aws.amazon.com/vpn/latest/s2svpn/monitoring-cloudwatch-vpn.html)

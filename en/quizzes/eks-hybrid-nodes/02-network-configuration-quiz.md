# EKS Hybrid Nodes Network Configuration Quiz

> **Related Document**: [Network Configuration](../../eks-hybrid-nodes/02-network-configuration.md)
> **Last Updated**: September 12, 2026

## Multiple Choice Questions

### 1. Which approach supplies the required bidirectional hybrid network path?

- A) Public internet access alone
- B) A reviewed Direct Connect/VPN design with actual routes and firewall access
- C) Only an SSH tunnel
- D) Only an HTTP proxy

<details>
<summary>Show Answer</summary>

**Answer: B) A reviewed Direct Connect/VPN design with actual routes and firewall access**

**Explanation:**
The control plane must reach the kubelet and applicable Pod endpoints as well as nodes reaching AWS. A public Kubernetes API endpoint does not remove that private reverse-path requirement. Direct Connect does not inherently encrypt every connection or guarantee latency. Confirm the VPN's actual tunnel state, not only resource state `available`. The related guide establishes the account/context and private WORK_DIR for these read-only diagnostics.
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

### 2. Which port is used for the node's Kubernetes API connection?

- A) TCP22
- B) TCP443
- C) TCP8080 by default
- D) TCP3306

<details>
<summary>Show Answer</summary>

**Answer: B) TCP443**

**Explanation:**
The reverse control-plane→kubelet connection uses secure TCP10250. Webhooks/aggregated APIs use their configured ports. Do not open unauthenticated 10255 as a modern requirement. Verify the cluster CA and hostname; HTTP401/403 can indicate reachable TLS but missing authorization, not application health.
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

### 3. For the private ECR image-pull portion of a no-internet design, which services are relevant?

- A) ecr.api, ecr.dkr and an appropriate private S3 layer-access path
- B) Only Lambda, DynamoDB and SNS
- C) Only EC2 metadata
- D) Only an EKS management endpoint

<details>
<summary>Show Answer</summary>

**Answer: A) ecr.api, ecr.dkr and an appropriate private S3 layer-access path**

**Explanation:**
Credential providers, EKS management, Kubernetes API and workload services have separate requirements. Private ECR endpoints do not make public ECR/CloudFront private. S3 interface endpoints support private DNS; inbound-Resolver-only mode needs the S3 gateway endpoint for in-VPC traffic. An EKS management interface endpoint is not the Kubernetes API endpoint, and a DNS alias cannot repair an unrelated TLS hostname.

</details>

### 4. Which is not a requirement for a hybrid Pod address plan?

- A) No overlap with remote node/VPC/Service ranges
- B) Sizing for actual node/Pod demand
- C) Every Pod pool must be a /8
- D) Correct cross-cluster separation and return routing

<details>
<summary>Show Answer</summary>

**Answer: C) Every Pod pool must be a /8**

**Explanation:**
IPv4 RFC1918 or CGNAT ranges are supported, with the documented remote-CIDR limits. A cluster-pool Cilium deployment configures its pool in Cilium, not by assigning one cluster-wide Pod CIDR through kubelet settings. This new-pool example is not an instruction to mutate an existing allocated pool. Read actual CiliumNode assignments; block order and usable Pod capacity are not guaranteed.
```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.85.0.0/16
    clusterPoolIPv4MaskSize: 25
```


</details>

### 5. How should the cluster DNS address be determined?

- A) Always use 8.8.8.8
- B) Inspect the real kube-dns Service or the deliberately configured local-DNS design
- C) Always assume 10.100.0.10
- D) Use the EC2 metadata address

<details>
<summary>Show Answer</summary>

**Answer: B) Inspect the real kube-dns Service or the deliberately configured local-DNS design**

**Explanation:**
`10.100.0.10` is an example for a particular Service CIDR. Check actual Service IPs, EndpointSlices and node resolver configuration. DNS placement alone does not guarantee local routing; Service Traffic Distribution and the supported dataplane must be configured. A soft spread preference does not prove a 2+2 CoreDNS layout.
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

### 6. How should AWS's hybrid network latency guidance be interpreted?

- A) 500ms is a guaranteed limit
- B) About 200ms RTT or less is general guidance, to validate against the workload
- C) 100ms is a strict universal requirement
- D) Direct Connect always guarantees under 10ms

<details>
<summary>Show Answer</summary>

**Answer: B) About 200ms RTT or less is general guidance, to validate against the workload**

**Explanation:**
AWS also gives 100Mbps as general guidance, not a workload-independent acceptance threshold. The previous <50/50–100/100–200/>200ms grading and <10ms Direct Connect claim were unverified heuristics. Curl's DNS/connect/TLS timings are cumulative phases, not pure RTT; unanswered ICMP is not proof of API failure. Measure actual application, API, image and telemetry behavior.

</details>

## References

- [Hybrid networking](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
- [EKS PrivateLink](https://docs.aws.amazon.com/eks/latest/userguide/vpc-interface-endpoints.html)
- [S3 private DNS](https://docs.aws.amazon.com/AmazonS3/latest/userguide/privatelink-interface-endpoints.html)
- [VPN metrics](https://docs.aws.amazon.com/vpn/latest/s2svpn/monitoring-cloudwatch-vpn.html)

# EKS Hybrid Nodes のネットワーク設定クイズ

> **関連ドキュメント**: [ネットワーク設定](../../eks-hybrid-nodes/02-network-configuration.md)
> **最終更新**: 2026年9月12日

## 選択式問題

### 1. ハイブリッドネットワークに必要な双方向接続を実現する方法はどれですか？

- A) パブリックインターネット接続だけを使う
- B) 実際の経路とファイアウォールのアクセス許可を確認した Direct Connect/VPN 設計を使う
- C) SSH トンネルだけを使う
- D) HTTP プロキシだけを使う

<details>
<summary>回答を表示</summary>

**回答: B) 実際の経路とファイアウォールのアクセス許可を確認した Direct Connect/VPN 設計を使う**

**解説:**
コントロールプレーンから kubelet と該当する Pod endpoint に到達でき、ノードから AWS にも到達できる必要があります。Kubernetes API のパブリック endpoint を使っても、プライベートな戻り経路の要件はなくなりません。Direct Connect はすべての接続を自動的に暗号化するものでも、遅延を保証するものでもありません。VPN はリソースの状態が `available` かどうかだけで判断せず、実際のトンネル状態を確認してください。関連ガイドでは、読み取り専用の診断を行うアカウント/context とプライベートな WORK_DIR を設定します。
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

### 2. ノードが Kubernetes API に接続するときに使うポートはどれですか？

- A) TCP 22
- B) TCP 443
- C) デフォルトで TCP 8080
- D) TCP 3306

<details>
<summary>回答を表示</summary>

**回答: B) TCP 443**

**解説:**
コントロールプレーンから kubelet への逆方向接続には、セキュアな TCP 10250 を使います。Webhook と集約 API は、それぞれ設定されたポートを使います。認証されていない TCP 10255 を、現在の要件として開放しないでください。クラスター CA とホスト名を検証します。HTTP 401/403 は TLS で到達できていても認可が不足していることを示す場合があり、アプリケーションの正常性を示すものではありません。
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

### 3. インターネットに接続しない構成で、プライベート ECR からイメージを取得するには、どのサービスが関係しますか？

- A) ecr.api、ecr.dkr、および S3 レイヤー取得用の適切なプライベート経路
- B) Lambda、DynamoDB、SNS だけ
- C) EC2 メタデータだけ
- D) EKS 管理 endpoint だけ

<details>
<summary>回答を表示</summary>

**回答: A) ecr.api、ecr.dkr、および S3 レイヤー取得用の適切なプライベート経路**

**解説:**
認証情報プロバイダー、EKS 管理、Kubernetes API、ワークロードサービスには、それぞれ別の要件があります。ECR のプライベート endpoint を用意しても、パブリック ECR や CloudFront へのアクセスがプライベートになるわけではありません。S3 の interface endpoint はプライベート DNS に対応します。inbound Resolver のみを使う構成では、VPC 内の通信に S3 gateway endpoint が必要です。EKS 管理用の interface endpoint は Kubernetes API endpoint ではありません。また、無関係な TLS ホスト名の問題は DNS alias では解決できません。

</details>

### 4. ハイブリッド Pod のアドレス設計で要件ではないものはどれですか？

- A) リモートのノード/VPC/Service のアドレス範囲と重複しない
- B) 実際のノード数と Pod 数に応じたサイズにする
- C) すべての Pod pool を /8 にする
- D) クラスター間で分離し、戻り経路を確保する

<details>
<summary>回答を表示</summary>

**回答: C) すべての Pod pool を /8 にする**

**解説:**
IPv4 の RFC1918 または CGNAT アドレス範囲を使用できます。リモート CIDR には文書に記載された上限が適用されます。cluster-pool を使う Cilium 環境では pool を Cilium で設定し、kubelet 設定でクラスター全体の Pod CIDR を割り当てることはしません。ここに示すのは新しい pool の例であり、すでに割り当て済みの pool を変更する指示ではありません。実際の CiliumNode の割り当てを確認してください。block の順序や利用可能な Pod 数は保証されません。
```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.85.0.0/16
    clusterPoolIPv4MaskSize: 25
```


</details>

### 5. クラスターの DNS アドレスはどのように決めるべきですか？

- A) 常に 8.8.8.8 を使う
- B) 実際の kube-dns Service、または意図して設定した local-DNS 構成を確認する
- C) 常に 10.100.0.10 とする
- D) EC2 メタデータアドレスを使う

<details>
<summary>回答を表示</summary>

**回答: B) 実際の kube-dns Service、または意図して設定した local-DNS 構成を確認する**

**解説:**
`10.100.0.10` は特定の Service CIDR における例です。実際の Service IP、EndpointSlice、ノードの resolver 設定を確認してください。DNS の配置だけではローカル経路は保証されません。Service Traffic Distribution と、対応する dataplane の設定が必要です。優先度の低い分散設定だけでは、CoreDNS が 2+2 の構成で配置されている証拠にはなりません。
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

### 6. AWS が示すハイブリッドネットワークの遅延ガイダンスは、どのように解釈すべきですか？

- A) 500 ms が保証された上限である
- B) RTT 約 200 ms 以下は一般的な目安であり、ワークロードに照らして検証する
- C) 100 ms がすべての環境に適用される厳格な要件である
- D) Direct Connect なら常に 10 ms 未満が保証される

<details>
<summary>回答を表示</summary>

**回答: B) RTT 約 200 ms 以下は一般的な目安であり、ワークロードに照らして検証する**

**解説:**
AWS は 100 Mbps も一般的な目安として示していますが、あらゆるワークロードに共通する合否基準ではありません。従来の「<50/50–100/100–200/>200 ms」という段階評価や、Direct Connect は 10 ms 未満という主張は、検証されていない経験則でした。curl の DNS/connect/TLS の時間は累積した各段階の所要時間であり、純粋な RTT ではありません。ICMP に応答がないことも、API の障害を証明するものではありません。アプリケーション、API、イメージ取得、テレメトリで実際の挙動を測定してください。

</details>

## 参考資料

- [ハイブリッドネットワーク](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
- [EKS PrivateLink](https://docs.aws.amazon.com/eks/latest/userguide/vpc-interface-endpoints.html)
- [S3 プライベート DNS](https://docs.aws.amazon.com/AmazonS3/latest/userguide/privatelink-interface-endpoints.html)
- [VPN メトリクス](https://docs.aws.amazon.com/vpn/latest/s2svpn/monitoring-cloudwatch-vpn.html)

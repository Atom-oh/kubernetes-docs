# Pod ネットワークベンチマーク: 同一ノード、同一 AZ、クロス AZ、DNS ndots

> **記録したテスト環境**: Kubernetes 1.36（Amazon EKS）、Amazon VPC CNI v1.21.1、kube-proxy iptables モード
> **測定日**: 2026年9月2日 · **コンテンツレビュー**: 2026年9月12日

このページは、ソウルの `fsi-demo-cluster` で2026年9月2日に実施したベンチマーク報告を記録しています。Pod 間 RTT、HTTP/gRPC レイテンシ、iperf3 スループット、DNS クエリ数を扱います。この測定では、AZ をまたぐとレイテンシが上がり、2つのノード間経路では同程度のスループットが得られました。ただし、これは AZ に依存しない帯域幅を保証するものではありません。測定 1～2 のアプリケーショントラフィックは Pod IP を直接使い、測定 3 はその料金をモデル化しています。測定 4 では既存の `kube-dns` ClusterIP を使いました。報告された DNS の10クエリの名前解決は、このリゾルバー、search list、応答順序に依存しており、すべての EKS Pod に当てはまるものではありません。過去のバージョンと測定値を保持しており、このレビューでは EKS ベンチマークを再実行していません。また、請求明細も確認していません。

![ap-northeast-2a のノード A 上のクライアント Pod が、同一ノード上のサーバー Pod、同じ AZ のノード B 上のサーバー Pod、ap-northeast-2b のノード C 上のサーバー Pod に到達する構成。RTT は 0.040 / 0.339 / 0.544 ms、単一フローは 29.97 / 4.96 / 4.96 Gbps。](../.gitbook/assets/en-networking-06-pod-network-benchmark-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-06-pod-network-benchmark-0.html)

この図は、テスト時のトポロジーを表します。+0.21 ms は今回の測定間の差、$4.47 は後述する十進 GB による過去の料金モデルです。どちらも請求額として検証されたものでも、AZ ごとに常に発生する料金でもありません。

## 要約: 測定した内容

1. **報告された RTT**: 同一ノード **0.040 ms** → 同一 AZ **0.339 ms** → クロス AZ **0.544 ms**（ping、200 probe の平均）。観測された差は2つのノード間経路で +0.21 ms、同一ノードとの比較で +0.50 ms です。
2. **HTTP p50 / p99**（fortio、100 qps、4 connection、keepalive、60 s）: 0.259 / 0.350 ms → 0.461 / 0.667 ms → 0.704 / 0.812 ms。アプリケーションから見ても同じ段階差が見られます。
3. **報告された帯域幅**: TCP 1 flow では2つのノード間経路で **4.96 Gbps**、8 flow では **9.94 Gbps** に達し、m5.xlarge の 10 Gbps burst peak に近い値でした。これは cluster placement group 外で一般的な single-flow 5 Gbps 制限と整合します。別のインスタンス機能や経路では上限が異なる場合があります。
4. **同一ノードの Pod 間通信**: 1 flow で **29.97 Gbps**（client process CPU 99.8 %。CPU 圧力と整合する値）、8 flow で **48.15 Gbps**。この VPC CNI 構成では、通信は Pod の veth pair とホストネットワークスタックを通り、物理 NIC は使いません。
5. **料金モデル**: 180 s のクロス AZ 実行で **223.4 十進 GB** を送信しました。元の payload ベースのモデルでは、両端それぞれ $0.01/GB として **$4.47** です。請求書ではありません。180 s の範囲では 1.25 Gbps baseline への低下は観測されませんでした。
6. **報告された DNS**: `ndots:5` の glibc Pod が `sts.ap-northeast-2.amazonaws.com` を解決した際に **10 query**（8件は NXDOMAIN）を送信し、warm 測定の中央値は **3.78 ms** でした。末尾に dot を付けると 2 query / 0.80 ms、`ndots:1` では 2 / 0.54 ms でした。これらの時間は測定サンプルであり、保証値ではありません。
7. **新規接続**: keepalive を無効にすると p50 は 0.259 → 0.664、0.461 → 1.079、0.704 → **1.517 ms** に変化しました。TCP 接続確立が増加に寄与していますが、handshake、socket、アプリケーションのコストは個別に分離していません。

## テスト環境

| 項目 | 値 |
|---|---|
| クラスター | Amazon EKS `fsi-demo-cluster`、ap-northeast-2（ソウル）、control plane `v1.36.2-eks-bca9cf6`、使用した AZ は2つ（2a、2b） |
| ノード | このテスト用に Karpenter `system` NodePool が新規起動した **3 × m5.xlarge**: 2a の client node、2a の server node、2b の server node。4 vCPU、Intel Xeon Platinum 8175M @ 2.50GHz |
| ノード OS | Amazon Linux 2023.12.20260817、kernel `6.18.41-94.142.amzn2023.x86_64`、containerd 2.2.5、kubelet v1.36.3-eks-cb19647 |
| CNI | Amazon VPC CNI `v1.21.1-eksbuild.8`（+ network-policy-agent v1.3.4）。`ENABLE_PREFIX_DELEGATION=false`、`ENABLE_POD_ENI=false`、`AWS_VPC_K8S_CNI_EXTERNALSNAT=false`、`NETWORK_POLICY_ENFORCING_MODE=standard`、`WARM_ENI_TARGET=1`、`WARM_IP_TARGET=3` |
| kube-proxy | `v1.35.3-eksbuild.5`、`mode: "iptables"` |
| CoreDNS | `v1.14.2-eksbuild.4`、2 replica（AZ ごとに1つ、`10.0.2.106` / 2a、`10.0.3.14` / 2b）。Service `kube-dns` の ClusterIP は `172.20.0.10`。Corefile は `kubernetes cluster.local … { pods insecure }`、`forward . /etc/resolv.conf`、`cache 30`、`loadbalance`。**NodeLocal DNSCache はなし**、`autopath` plugin もなし |
| Pod の resolv.conf（デフォルト） | `search bench-net.svc.cluster.local svc.cluster.local cluster.local ap-northeast-2.compute.internal` / `nameserver 172.20.0.10` / `options ndots:5` |
| Pod NIC | eth0 MTU **9001**（jumbo frame）、TCP congestion control `cubic`、iperf3 `tcp_mss_default: 8949` |
| EC2 ネットワーク仕様 | m5.xlarge「Up to 10 Gigabit」: baseline **1.25 Gbps**、peak **10 Gbps**、4 vCPU（比較: m5.large は baseline 0.75 Gbps、peak 10 Gbps、2 vCPU）。`aws ec2 describe-instance-types` で確認。ENA が必要 |
| 料金 | usage type `APN2-DataTransfer-Regional-Bytes`、「Regional Data Transfer - in/out/between AZs or when using public IP or Elastic IP addresses」、**$0.01/GB**（`aws pricing get-products --region us-east-1`、2026年9月に照会） |
| ツール | `nicolaka/netshoot:v0.14`（iperf **3.19**、fortio **1.69.5**、iputils ping 20250605、tcpdump 4.99.5）。DNS client は `python:3.12-slim`（Debian 13、**glibc 2.41**、Python 3.12.14） |
| テスト時間 | 2026-09-02 07:58–08:40 UTC（最初の Pod は 07:58:22Z、DNS Pod は 08:16:24Z） |

AWS は burst 帯域幅を best effort と説明しています。network I/O credit が残っていても、利用可能な burst とその継続時間は変わります。新規インスタンスは最大 credit で開始しますが、peak の利用可能性と burst 時間は一定ではありません。この180 s の実行で言えるのは、その観測時間内に baseline への低下がなかったことだけです。記録された m5.xlarge の baseline 1.25 Gbps / peak 10 Gbps は公式の [M5 network specifications](https://docs.aws.amazon.com/ec2/latest/instancetypes/gp.html) にも記載されています。現在の credit 動作については [EC2 bandwidth guide](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-network-bandwidth.html) を参照してください。

実行時の fixture 配置:

| Pod | IP | ノード | Zone | 役割 / requests |
|---|---|---|---|---|
| `cli` | 10.0.2.109 | ip-10-0-2-128（nodeclaim `system-76r87`） | ap-northeast-2a | client; 2500m / 1Gi |
| `srv-same` | 10.0.2.72 | ip-10-0-2-128（`cli` と同じ node。必須 podAffinity） | ap-northeast-2a | server; 200m / 256Mi |
| `srv-a` | 10.0.2.37 | ip-10-0-2-20（nodeclaim `system-ksrbg`、`cli` への podAntiAffinity） | ap-northeast-2a | server; 2800m / 1Gi |
| `srv-b` | 10.0.3.65 | ip-10-0-3-32（nodeclaim `system-svdvk`） | ap-northeast-2b | server; 2500m / 1Gi |
| `dns-default` | 10.0.2.5 | ip-10-0-2-20（`srv-a` への podAffinity） | ap-northeast-2a | glibc resolver、デフォルト `ndots:5` |
| `dns-ndots1` | 10.0.2.143 | ip-10-0-2-20 | ap-northeast-2a | glibc resolver、`dnsConfig.options ndots=1` |

server Pod は `sh -c "iperf3 -s -p 5201 & exec fortio server -http-port 8080 -grpc-port 8079 -tcp-port 8078"` を実行しました。すべての bench Pod に `karpenter.sh/do-not-disrupt: "true"` が設定されています。`srv-a` は最初 m5.large / 1500m で要求しましたが、Karpenter は `no instance type has enough resources` と報告しました。DaemonSet overhead が m5.large の 1930m allocatable のうち821mを使うため、m5.xlarge / 2800m に変更しました。

### Fixture のマニフェスト

以下は記録された fixture です。過去の selector、requests、image、command、annotation をそのまま保持しています。アプリケーション Service object は含まれていません。この selector だけでは新規または単独の node への配置は保証されません。新しいテストでは、承認済みの NodePool、利用可能な AZ、リソース予算に合わせてコピーを調整してから実施してください。この fixture を共有の `system` pool にそのままデプロイしないでください。mutable な image tag と netshoot の build-time tool download は、元の binary を保証しないため、image digest と tool version を記録してください。以下の改訂手順は、この履歴 artifact とは別の手順です。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: bench-net
  labels:
    bench: net
---
# client: fresh m5.xlarge in ap-northeast-2a
apiVersion: v1
kind: Pod
metadata:
  name: cli
  namespace: bench-net
  labels: { app: cli, role: client }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  nodeSelector:
    topology.kubernetes.io/zone: ap-northeast-2a
    node.kubernetes.io/instance-type: m5.xlarge
    karpenter.sh/nodepool: system
  terminationGracePeriodSeconds: 5
  containers:
    - name: netshoot
      image: nicolaka/netshoot:v0.14
      command: ["sleep", "infinity"]
      resources:
        requests: { cpu: "2500m", memory: "1Gi" }
---
# same-node: co-located with cli through required podAffinity
apiVersion: v1
kind: Pod
metadata:
  name: srv-same
  namespace: bench-net
  labels: { app: srv-same, role: server, zone: a }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  affinity:
    podAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector: { matchLabels: { app: cli } }
          topologyKey: kubernetes.io/hostname
  terminationGracePeriodSeconds: 5
  containers:
    - name: netshoot
      image: nicolaka/netshoot:v0.14
      command: ["sh", "-c", "iperf3 -s -p 5201 & exec fortio server -http-port 8080 -grpc-port 8079 -tcp-port 8078"]
      ports: [{ containerPort: 8080 }, { containerPort: 5201 }]
      resources:
        requests: { cpu: "200m", memory: "256Mi" }
---
# same-AZ: same AZ as cli, different node (podAntiAffinity). m5.large did not fit because of DaemonSet overhead, hence m5.xlarge
apiVersion: v1
kind: Pod
metadata:
  name: srv-a
  namespace: bench-net
  labels: { app: srv-a, role: server, zone: a }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  nodeSelector:
    topology.kubernetes.io/zone: ap-northeast-2a
    node.kubernetes.io/instance-type: m5.xlarge
    karpenter.sh/nodepool: system
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector: { matchLabels: { app: cli } }
          topologyKey: kubernetes.io/hostname
  terminationGracePeriodSeconds: 5
  containers:
    - name: netshoot
      image: nicolaka/netshoot:v0.14
      command: ["sh", "-c", "iperf3 -s -p 5201 & exec fortio server -http-port 8080 -grpc-port 8079 -tcp-port 8078"]
      ports: [{ containerPort: 8080 }, { containerPort: 5201 }]
      resources:
        requests: { cpu: "2800m", memory: "1Gi" }
---
# cross-AZ: fresh m5.xlarge in ap-northeast-2b
apiVersion: v1
kind: Pod
metadata:
  name: srv-b
  namespace: bench-net
  labels: { app: srv-b, role: server, zone: b }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  nodeSelector:
    topology.kubernetes.io/zone: ap-northeast-2b
    node.kubernetes.io/instance-type: m5.xlarge
    karpenter.sh/nodepool: system
  terminationGracePeriodSeconds: 5
  containers:
    - name: netshoot
      image: nicolaka/netshoot:v0.14
      command: ["sh", "-c", "iperf3 -s -p 5201 & exec fortio server -http-port 8080 -grpc-port 8079 -tcp-port 8078"]
      ports: [{ containerPort: 8080 }, { containerPort: 5201 }]
      resources:
        requests: { cpu: "2500m", memory: "1Gi" }
```

2つの DNS Pod は `srv-a` と同じ node に配置されたと報告されています。`app` image は Debian 13 / glibc 2.41 と報告されました。musl やほかの resolver は測定していません。`sniffer` は Pod の network namespace を共有するため、クラスターが packet capture を許可すれば、該当するアプリケーション DNS packet を capture できます。下の例から2つの DNS object を作るには、2つ目を複製し、name と `app` label を `dns-ndots1` に変更して、その2つ目の object だけで `dnsConfig` のコメントを解除します。image は同一に保ち、新しい測定では記録した digest を固定してください。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: dns-default          # the second Pod is name: dns-ndots1 plus the dnsConfig block below
  namespace: bench-net
  labels: { app: dns-default, role: dns }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  affinity:
    podAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector: { matchLabels: { app: srv-a } }
          topologyKey: kubernetes.io/hostname
  # present only in dns-ndots1:
  # dnsConfig:
  #   options:
  #     - name: ndots
  #       value: "1"
  terminationGracePeriodSeconds: 5
  containers:
    - name: app
      image: python:3.12-slim
      command: ["sleep", "infinity"]
      resources: { requests: { cpu: "50m", memory: "64Mi" } }
    - name: sniffer
      image: nicolaka/netshoot:v0.14
      command: ["sleep", "infinity"]
      resources: { requests: { cpu: "50m", memory: "64Mi" } }
```

## 測定 1. RTT と HTTP レイテンシ: 同一ノード → 同一 AZ → クロス AZ

ICMP probe（`ping -c 200 -i 0.05 -q`）で idle 経路を測定しました。これには endpoint の kernel 処理と scheduling も含まれます。同じ経路を HTTP/1.1 と gRPC でも測定しました。新規接続を使った `curl` 1回の connect / total time も参考値として記載します。

| 経路 | RTT min / **avg** / max / mdev (ms) | loss | curl、cold request 1回: connect / total |
|---|---|---|---|
| 同一ノード → 10.0.2.72 | 0.021 / **0.040** / 0.089 / 0.007 | 0/200 | 0.194 ms / 0.497 ms |
| 同一 AZ → 10.0.2.37 | 0.300 / **0.339** / 0.450 / 0.017 | 0/200 | 0.497 ms / 2.333 ms |
| クロス AZ → 10.0.3.65 | 0.504 / **0.544** / 0.625 / 0.015 | 0/200 | 0.694 ms / 4.038 ms |

観測された差: 同一 AZ − 同一ノード = +0.30 ms、クロス AZ − 同一 AZ = **+0.21 ms**、クロス AZ − 同一ノード = +0.50 ms。このサンプルでは報告された mdev は最大でも 0.017 ms です。curl の `time_total` は process 起動時間を測るものではなく、転送操作を測定します。単一観測では分布を評価できません。[curl の時間計測項目](https://curl.se/docs/manpage.html) を参照してください。

### HTTP/1.1: 100 qps、4 connection、keepalive、60 s（6,000 request）、ms

| 経路 | avg | **p50** | p90 | p99 | p99.9 | max | min |
|---|---|---|---|---|---|---|---|
| 同一ノード | 0.260 | **0.259** | 0.299 | 0.350 | 1.267 | 2.080 | 0.111 |
| 同一 AZ | 0.468 | **0.461** | 0.560 | 0.667 | 0.783 | 2.823 | 0.336 |
| クロス AZ | 0.706 | **0.704** | 0.782 | 0.812 | 1.150 | 4.581 | 0.551 |

### gRPC ping: 100 qps、4 connection、30 s（3,000 request）、ms

| 経路 | avg | **p50** | p90 | p99 | p99.9 | max | min |
|---|---|---|---|---|---|---|---|
| 同一ノード | 0.410 | **0.397** | 0.449 | 0.869 | 1.187 | 1.314 | 0.241 |
| 同一 AZ | 0.601 | **0.592** | 0.687 | 0.889 | 1.052 | 1.105 | 0.448 |
| クロス AZ | 0.878 | **0.865** | 0.967 | 1.209 | 2.582 | 2.826 | 0.692 |

報告では、HTTP echo body は約75 byte、request payload は空、すべての実行で error は0件です。各 protocol の結果 counter は分けて確認してください。HTTP status 200、gRPC Ping の結果、gRPC health-check の `SERVING` は別の応答です。`-grpc -ping` を指定すると、デフォルトの health-check workload ではなく Ping を実行します。

**読み方。** HTTP p50 は ping mean より約0.22 / 0.12 / 0.16 ms高い値ですが、異なる protocol の異なる統計量を引いても user-space overhead は分離できません。観測した HTTP p50 の段差は +0.202 ms と +0.243 ms であり、ノードごと、または AZ ごとの固定コストではありません。gRPC p50 はこれらの実装で HTTP p50 より0.138 / 0.131 / 0.161 ms高くなっていますが、HTTP/2、serialization、scheduling、client / server code の各寄与は特定できません。tail にも差が出ています。HTTP p99 は 0.350 → 0.667 → 0.812 ms、gRPC p99.9 は 1.187 → 1.052 → **2.582 ms** でした。これらは各セルで1回実行した分布の報告値です。

> **mesh benchmark との比較。** [Istio sidecar vs ambient report](../service-mesh/istio/comparison/03-sidecar-vs-ambient.md) は、sidecar 全体のシナリオで p50 に **+1.29 ms**（2.11 − 0.82 ms）の差を記録しています。単一 proxy の分離測定ではありません。Graviton hardware、200 qps、16 connection、Fortio 1.69.4 を使っており、この M5 / 100 qps / 4 connection の測定とは異なります。数値を普遍的な「mesh hop」と「AZ hop」のコストとして足し合わせたり、順位付けしたりすることはできません。

### 新規接続のコスト: keepalive=false、100 qps、4 connection、30 s（3,000 request）、ms

すべての request で新しい TCP connection を開く（fortio `-keepalive=false`）と、レイテンシはどうなるでしょうか。

| 経路 | avg | **p50** | p90 | p99 | p99.9 | max | min | keepalive p50 との差 |
|---|---|---|---|---|---|---|---|---|
| 同一ノード | 0.672 | **0.664** | 0.782 | 0.957 | 1.253 | 1.306 | 0.364 | **+0.405 ms** |
| 同一 AZ | 1.066 | **1.079** | 1.185 | 1.369 | 1.582 | 1.795 | 0.769 | **+0.618 ms** |
| クロス AZ | 1.530 | **1.517** | 1.678 | 1.796 | 1.981 | 2.009 | 1.300 | **+0.813 ms** |

観測された増加は **+0.405 / +0.618 / +0.813 ms** でした。新しい TCP connection では確立処理が加わりますが、「RTT 1回 + 0.3 ms」で分解できるとはこの測定から言えません。実際の workload で connection reuse を測ることは有用な最適化ですが、AZ 間通信が正しく動作するための前提条件ではありません。connection churn は、connection の close 方法によって active-closing 側の TIME_WAIT state を増やす可能性もありますが、ここでは測定していません。

### 固定 connection pool の最大 qps: レイテンシがスループットを決める（closed loop、16 connection、20 s）

`-qps 0`（無制限、closed loop）では、16 connection が維持できる最大 request rate によって、レイテンシ差がスループット差になります。

| 経路 | request 数 | **達成 qps** | avg ms | p50 | p90 | p99 | p99.9 | max |
|---|---|---|---|---|---|---|---|---|
| 同一ノード | 899,827 | **44,991** | 0.355 | 0.249 | 0.733 | 1.695 | 3.389 | 13.593 |
| 同一 AZ | 770,156 | **38,507** | 0.415 | 0.396 | 0.537 | 0.728 | 1.147 | 4.502 |
| クロス AZ | 512,060 | **25,602** | 0.624 | 0.597 | 0.770 | 0.949 | 1.293 | 4.725 |

処理中の request が約16件で、client の考慮時間がほぼない安定した closed loop では、Little の法則により throughput ≈ concurrency / mean latency となります。16 / 0.000355 = 45,070（報告値 44,991）、16 / 0.000415 = 38,554（38,507）、16 / 0.000624 = 25,641（25,602）です。この測定ではクロス AZ の報告 rate は同一 AZ より **33.5 % 低い**値でした。この関係からレイテンシの原因だけを特定したり、普遍的な AZ penalty を予測したりはできません。同一ノードの tail が悪化した理由として共有 CPU contention は考えられますが、ここでの profiling では確認していません。

## 測定 2. スループット: single-flow の 5 Gbps 上限とインスタンスの 10 Gbps 上限

iperf3 3.19、TCP、1回20 s、`-J`、client は `cli`。CPU 列は iperf3 自身の process 別数値で、100 % は1 vCPU を意味します。

| 経路 | flow 数 (-P) | 送信 Gbps | 受信 Gbps | retransmit | 送信 byte 数 | client CPU | server CPU | 送信側 TCP mean RTT (stream 1) | max snd_cwnd |
|---|---|---|---|---|---|---|---|---|---|
| 同一ノード (cli→srv-same) | 1 | **29.97** | 29.97 | 13 | 74,921,541,632 | **99.8 %** | 80.9 % | 34 µs | 1,861,392 B |
| 同一ノード | 8 | **48.15** | 48.08 | 14,567 | 120,375,083,008 | 179.0 % | 186.9 % | 201 µs / 767 µs（stream 1、2） | 5,888,442 B |
| 同一 AZ (cli→srv-a、2a→2a) | 1 | **4.96** | 4.96 | 4 | 12,411,731,968 | 19.5 % | 15.4 % | **5,641 µs** | 4,349,214 B |
| 同一 AZ | 8 | **9.94** | 9.93 | 5,874 | 24,846,139,392 | 36.3 % | 159.3 % | 2,720 µs / 1,626 µs | 1,163,370 B |
| クロス AZ (cli→srv-b、2a→2b) | 1 | **4.96** | 4.96 | 2 | 12,411,994,112 | 20.0 % | 22.5 % | **5,420 µs** | 4,304,469 B |
| クロス AZ | 8 | **9.94** | 9.93 | 5,979 | 24,845,090,816 | 36.7 % | 138.2 % | 3,671 µs / 3,237 µs | 1,226,013 B |

ここから読み取れる点は4つあります。

1. **同一ノードの通信は物理 NIC を通りません。** single-flow は 29.97 Gbps、client process CPU は 99.8 % でした。8 flow は 48.15 Gbps に達しました。ホスト routing、両 Pod の veth 経路、kernel 処理、CPU scheduling の影響は受けます。CPU 圧力を示す材料を含むネットワークベンチマークであり、純粋な memory-copy speed の測定ではありません。
2. **ノード間の single-flow はどちらも 4.96 Gbps でした。** cluster placement group 外の通常の 5 Gbps 上限と整合します。AWS は cluster placement group 内の flow で最大10 Gbps、同一 AZ の条件を満たす ENA Express 経路で最大25 Gbps も記載しています。iperf3 process CPU が低いだけで、ホスト / network 処理による制約をすべて否定できるわけではありません。
3. **8 flow ではどちらも 9.94 Gbps でした。** この観測時間内に両経路で似た throughput となったことを示します。single-flow でも retransmit があり（ノード間で4 / 2）、8 flow では増加しました（5,874 / 5,979）。retransmit 数だけでは ENA shaping や loss の発生箇所を特定できません。ENA allowance counter は収集していません。
4. **負荷時の TCP RTT は idle ICMP RTT より高い値でした。** single-flow の送信側で約 **5.6 / 5.4 ms**、congestion window は約4.3 MB と報告されました。これに対し idle ping mean は 0.34 / 0.54 ms です。queueing は原因候補ですが、protocol、sampling、負荷条件が異なります。queue の位置や multiplex されたすべての RPC に保証された5 msが加わることを測定したわけではありません。

報告された MSS 8949 は MTU 9001 byte と IPv4/TCP overhead に整合します。実効 MSS は header と経路 MTU にも依存します。次節の byte sent 列はアプリケーション転送量であり、課金対象量として独立検証したものではありません。

> この一般的な EC2 経路では、parallel flow により、1 flow の場合よりインスタンスが利用できる burst 帯域幅を多く使えました。parallelism を増やすと CPU 負荷、congestion、コストも変わります。Kafka fetcher や転送 concurrency を変更する前に、実際のインスタンス / 経路の上限を確認してください。この測定は「接続ごとに必ず 5 Gbps で頭打ちになる」ことも、「1 AZ なら帯域幅が常に2倍になる」ことも裏付けません。

### 3分間の持続実行と burst credit

報告対象の m5.xlarge の baseline は 1.25 Gbps、best-effort の peak は最大10 Gbps です。過去の4-flow クロス AZ テストは180 s、10 s 間隔で実行されました（`iperf3 -c 10.0.3.65 -p 5201 -t 180 -P 4 -i 10 -J`）。この IP は記録された fixture に属します。新たなテストでは現在の Pod IP を取得してください。

| 項目 | 値 |
|---|---|
| 10 s ごとの Gbps（18 interval） | 9.94、9.93 ×12、9.92、9.93 ×4（**min 9.92、max 9.94**） |
| 送信合計 | 180.0 s で 223,376,179,200 B = **223.4 GB**（9.93 Gbps） |
| retransmit | 44,842（約249/s、10 s ごとに2,273～2,669） |
| CPU | client 30.7 %（system 30.1 %）、server 54.2 %（system 52.2 %） |

**180 s の間に 1.25 Gbps への低下は観測されませんでした。** これは credit が無制限にあることや、peak 帯域幅を持続的に保証する証拠ではありません。AWS は burst を変動する best-effort と説明し、credit が尽きると baseline へ向けて throttle される場合があります。長時間の backup や rebalance は、この短い測定から外挿せず、適用される baseline と実測 workload 要件を使って計画してください。

## 測定 3. クロス AZ data transfer cost のモデル

ここでは報告書の計算を見積もりとして保持しています。ベンチマークから得られたのは payload byte 数と公開 price であり、Cost and Usage Report (CUR) や請求書ではありません。

同一 Region 内で AZ 間を EC2 private IP で直接転送する場合、[EC2 の料金ページ](https://aws.amazon.com/ec2/pricing/on-demand/) には両端それぞれ $0.01/GB と記載されています。報告された公開 Pricing API item は `APN2-DataTransfer-Regional-Bytes`、**$0.0100000000 USD/GB** です。`get-products` が返すのは catalog price で、アカウント固有の実際の請求 rate ではありません。一方向の payload 転送では、同程度の逆方向転送がなくても、送信側の “out” と受信側の “in” の双方に課金される場合があります。ほかの AWS service 経路では課金ルールが異なることがあります。

| シナリオ | 過去の十進 GB モデルによる payload 量 | 推定コスト（model GB × $0.01 × 2） |
|---|---|---|
| 180 s の実行（測定 payload、推定コスト） | 223.4 GB | 223.4 × $0.01 ≈ **各端 $2.23、合計 $4.47** |
| 測定 2 のクロス AZ iperf3 転送（12.41 + 24.85 + 223.38 GB） | 260.6 GB | 約各端 $2.61、**合計約 $5.21**（ほかの通信は除外） |
| 30日間平均1 Gbpsで AZ 間を転送（**仮定**） | 0.125 GB/s × 86,400 s × 30日 = 324,000 GB ≈ **324 TB** | 324,000 × $0.02 ≈ **月 $6,480** |
| 3 AZ に RF3 StatefulSet を配置し leader ingest 100 MiB/s（**仮定**、replication 通信のみ） | 別 AZ の follower が2つ → 2 × 100 MiB/s = 209,715,200 B/s × 2,592,000 s ≈ 543,600 GB ≈ **月 544 TB** | 543,600 × $0.02 ≈ **月 $10,870** |

4行すべてで、**1 GB = 10⁹ payload byte** の十進換算をモデル上の仮定として使っています。EC2 の課金量もこの換算になるとは、この監査で確認していません。正確な raw total は持続実行で 223,376,179,200 B、3回のクロス AZ iperf3 実行の合計で 260,633,264,128 B です。実際の計量単位、rate、両端の課金、protocol overhead / retransmit、適用される credit や discount を [CUR のデータ転送記録](https://docs.aws.amazon.com/cur/latest/userguide/cur-data-transfers-charges.html) と照合してください。下2行はさらに30日間の連続通信を仮定し、replication 量には producer / consumer 通信を含みません。**$4.47 と $5.21 は見積もりであり、実際に支払った金額として確認されたものではありません。**

**運用担当者が行うこと。**

- **対応する場合は近い endpoint を優先する。** 現行 Kubernetes 文書では `Service.spec.trafficDistribution: PreferSameZone` を使います。deprecated alias は `PreferClose` です。これは fallback を伴う preference であり、zone を厳密に固定する設定ではありません。API server、kube-proxy の version、feature 対応状況を確認してください。この記録では control plane が1.36、kube-proxy が1.35 でした。この preference もアプリケーションの Service 経路も測定しておらず、直接の Pod-IP 通信には影響しません。
- **近接性と耐障害性のバランスを取る。** zone-aware read や client は不要な転送を減らせる場合がありますが、RF3 replica をすべて1つの AZ に置くと、AZ 障害への保護が失われます。必要な replica / failover 設計を保ち、[ゾーン別クラスター運用](../ops/15-zonal-operations-guide.md) を参照してください。
- **課金される両端を計測する。** backup、rebalance、replay について送信元 / 宛先 AZ と計量 volume を追跡してください。関連する “in” と “out” の usage record は別アカウントに計上される場合もあります。payload byte だけで最終請求を推定しないでください。

## 測定 4. DNS: ndots:5 による query amplification

![glibc の ndots:5 lookup では、4つの search suffix に対して A と AAAA の組を順に送り（NXDOMAIN が8応答、合計10 query）、絶対名で成功します。末尾 dot を付けると2 query で終了します。](../.gitbook/assets/en-networking-06-pod-network-benchmark-1.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-06-pod-network-benchmark-1.html)

この図は、記録された glibc の search 順序を示します。4.37 ms は報告された A 応答で終了しており、`getaddrinfo` 呼び出し全体の時間ではありません。upstream への矢印は説明用で、Pod capture ではその通信区間を観測していません。「cache 30」は TTL の上限であり、30秒間 cache hit する保証ではありません。

記録された Pod は4つの search domain と `ndots:5` を使っていました。この構成が、すべての EKS、DNS policy、OS、node 設定で共通というわけではありません。この glibc `AF_UNSPEC` lookup では候補名ごとに A と AAAA が要求され、4つの search 候補は NXDOMAIN を返した後、絶対名 STS が成功しました。A/AAAA の並列性と query 数は resolver option、address family、早期成功、retry、TCP fallback によって変わります。過去の capture は `tcpdump -i eth0 -nn udp port 53` を使っており、UDP DNS のみを観測します。報告は process の最初の lookup 1回と、その後の計時された20 repeat を区別しています。process 起動後の最初の呼び出しだけでは、CoreDNS や upstream cache が cold だったとは証明できません。[Kubernetes Pod の DNS 設定](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/) を参照してください。

### 1回の名前解決で送信した query と warm latency（20 repeat）、ms

| Pod / ndots | 名前（dot 数） | 送信 query | NXDOMAIN 応答 | warm min | **median** | p90 | max |
|---|---|---|---|---|---|---|---|
| default / 5 | `kubernetes.default` (1) | 4 | 2 | 0.87 | **1.71** | 1.97 | 2.61 |
| default / 5 | `kubernetes.default.svc.cluster.local` (4) | **10** | 8 | 1.53 | **3.63** | 4.45 | 6.41 |
| default / 5 | `kubernetes.default.svc.cluster.local.`（末尾 dot） | 2 | 0 | 0.33 | **0.46** | 1.09 | 1.58 |
| default / 5 | `sts.ap-northeast-2.amazonaws.com` (3) | **10** | 8 | 3.08 | **3.78** | 4.66 | 4.84 |
| default / 5 | `sts.ap-northeast-2.amazonaws.com.`（末尾 dot） | 2 | 0 | 0.42 | **0.80** | 1.25 | 2.17 |
| default / 5 | `www.amazon.com` (2) | **10** | 8 | 2.51 | **3.46** | 3.74 | 5.86 |
| ndots1 / 1 | `kubernetes.default` (1) | **6** | 4 | 1.16 | **2.04** | 2.80 | 4.54 |
| ndots1 / 1 | `kubernetes.default.svc.cluster.local` (4) | 2 | 0 | 0.35 | **0.97** | 1.08 | 1.35 |
| ndots1 / 1 | `kubernetes.default.svc.cluster.local.` | 2 | 0 | 0.34 | **0.40** | 0.97 | 1.17 |
| ndots1 / 1 | `sts.ap-northeast-2.amazonaws.com` (3) | 2 | 0 | 0.45 | **0.54** | 1.22 | 1.42 |
| ndots1 / 1 | `sts.ap-northeast-2.amazonaws.com.` | 2 | 0 | 0.47 | **0.75** | 1.20 | 1.30 |
| ndots1 / 1 | `www.amazon.com` (2) | 2 | 0 | 0.63 | **0.90** | 1.27 | 2.74 |

報告された process 最初の呼び出し時間は、default / `sts` 6.22 ms、default / `sts.` 2.87 ms、default / `www.amazon.com` 9.58 ms、default / `kubernetes.default.svc.cluster.local` 7.40 ms、ndots1 / `kubernetes.default` 10.52 ms、ndots1 / `sts` 2.84 ms でした。resolver 初期化を含むため、下の wire timeline とは別の値です。

**読み方。** このサンプルでは、外部名と末尾 dot なしの cluster FQDN は **10 query / 8 NXDOMAIN** でした。末尾 dot ありの STS median は 3.78 → 0.80 ms、cluster FQDN は 3.63 → 0.46 ms に下がりました。`kubernetes.default` は2番目の search 候補で成功したため、必要な query は4つだけです。search expansion が常にリスト全体を消費するわけではありません。[CoreDNS cache](https://coredns.io/plugins/cache/) は否定応答を cache できますが、`cache 30` が設定するのは最大 TTL です。実際の TTL と minimum の影響を受け、各 replica の cache は別々です。Kubernetes plugin の default TTL は、変更しなければ5秒です。cache hit でも query 自体は順に行われますが、この capture から、すべての warm lookup が upstream 通信を避けたとは言えません。

### 名前解決の経路: `sts.ap-northeast-2.amazonaws.com` の cold lookup 1回（ndots:5、tcpdump、最初の packet からの ms）

| t (ms) | 172.20.0.10 に送った候補名（A + AAAA を並列送信） | 応答 |
|---|---|---|
| 0.00 | `sts.ap-northeast-2.amazonaws.com.bench-net.svc.cluster.local.` | NXDOMAIN（権威応答、CoreDNS kubernetes plugin）0.92 / 1.14 |
| 1.21 | `sts.ap-northeast-2.amazonaws.com.svc.cluster.local.` | NXDOMAIN 2.01 / 2.26 |
| 2.32 | `sts.ap-northeast-2.amazonaws.com.cluster.local.` | NXDOMAIN 3.15 / 3.41 |
| 3.47 | `sts.ap-northeast-2.amazonaws.com.ap-northeast-2.compute.internal.` | NXDOMAIN（VPC resolver に転送、非権威応答）3.68 / 3.93 |
| 3.99 | `sts.ap-northeast-2.amazonaws.com.` | **A 10.0.3.84、A 10.0.2.129** 4.37（AAAA: data なし）|

表は10 query と8 NXDOMAIN を記録しています。**4.37 ms** は最初の query から報告された A 応答までの時間です。AAAA の完了時間は記録されていないため、process 起動後の最初の呼び出し 6.22 ms 全体を示すものではありません。候補ごとの RTT は一律0.8～1.1 msではありません。4番目の A/AAAA は0.21 / 0.46 ms、最後の A は0.38 msでした。kube-proxy iptables は新しい conntrack flow に対して endpoint を選び、各 packet ごとには選びません。A/AAAA request が同じ flow を共有することもあります。2つの endpoint が均等に選ばれる場合は新規 flow の半分というのが例示的な期待値ですが、**クロス AZ DNS query の割合を測定したものではありません。** Service VIP `172.20.0.10` を写した Pod capture だけでは、選ばれた backend の AZ は分かりません。元の報告は2つの STS private address を interface endpoint ENI に割り当てており、cluster FQDN の候補転送は2.2 ms / wire 全体は5.6 ms、末尾 dot ありでは0.4～0.5 ms と記録しています。これらは別の観測値です。

### `ndots:1` の効果と副作用

- **このサンプルの外部名**: 10 → **2 query**、median は約3.5～3.8 → **0.5～0.9 ms**。この改善は名前と resolver の動作に依存します。
- **短い名前は失敗する試行が増える場合があります。** 今回の `kubernetes.default` は dot が1つあり `ndots:1` を満たすため、glibc は先に `kubernetes.default.` を試しました。CoreDNS はこれを転送し、報告された1.6 ms後に NXDOMAIN を受け取ってから、namespace suffix を試し、最終的に `svc.cluster.local` で `172.20.0.1` に解決しました。結果は6 query、4 NXDOMAIN、median 2.04 ms で、default 設定の1.71 msより長くなりました。この動作では内部名のような名前が upstream に漏れる場合があります。`ndots` を変更する前に、各アプリケーションの service 名をテストしてください。完全な Service 名を使うと曖昧さを減らせます。
- **末尾 dot は resolver name を絶対名にします。** この resolver では search expansion を避けられますが、retry、address family、cache の条件が変わっても wire query が常に2回になる、またはレイテンシが一定になる保証はありません。

### amplification の計算（導出）

**同じ応答パターン**で、アプリケーション DNS cache がなく、毎秒1,000回 lookup するなら、10 query の形式で毎秒10,000 query、2 query の形式で毎秒2,000 query です。最初の10,000件では8,000件（80 %）が NXDOMAIN になります。これは query 数のモデルであり、CoreDNS CPU やクロス AZ query の割合を測ったものではありません。観測した median 差は STS で 3.78 − 0.80 = 2.98 ms、cluster FQDN で 3.63 − 0.46 = 3.17 ms です。固定のリクエスト当たり penalty ではありません。

**実際のアプリケーションでテストする選択肢:**

- client が対応している場合は絶対 DNS 名を使います。HTTPS や AWS SDK endpoint URL に末尾 dot を機械的に付けないでください。Host 処理、SNI、証明書検証、request signing が正しく動作する必要があります。
- 短縮名の動作とアプリケーション DNS cache を考慮しながら、`dnsConfig: {options: [{name: ndots, value: "1"}]}` を評価します。
- 適切な環境では [NodeLocal DNSCache](https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/) を評価します。cache hit は node 内にとどまり、miss は引き続き upstream に向かいます。現行の [EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html) では node-local CoreDNS が system service として稼働します。Auto Mode のみのクラスターでは CoreDNS Deployment は不要ですが、混在クラスターの非 Auto node では引き続き必要です。
- [CoreDNS autopath](https://coredns.io/plugins/autopath/) は server 側で search completion を行えますが、Kubernetes 統合には `pods verified`、送信元 Pod IP の可視性、関連する Pod watch / RBAC / memory が必要です。記録された `pods insecure` 設定は要件を満たしません。この最適化はテストしていません。

## 再現方法: 改訂手順

承認済みの隔離 lab と、このテスト専用の未使用 namespace を使用してください。最初の fixture を調整して `bench-net.yaml`、2つの DNS object を `bench-dns.yaml` として保存し、namespace 名を一致させます。適用前に NodePool の容量、AZ、scheduling、packet-capture 権限を確認してください。テストのために本番 admission や security control を弱めないでください。実行時間を限定した command でも node を飽和させ、課金を発生させる場合があります。

すべての command は `cli` 内の interactive shell に入らず、**operator の Bash shell** から実行します。この監査では syntax と一部のローカル tool の動作を確認しましたが、fixture を deploy したり EKS で network load を実行したりしていません。

**1. 調整した fixture を deploy し、配置を検証する。**

```bash
set -euo pipefail
BENCH_NS=bench-net
kubectl apply -f bench-net.yaml
kubectl -n "$BENCH_NS" wait --for=condition=Ready \
  pod/cli pod/srv-same pod/srv-a pod/srv-b --timeout=300s
kubectl -n "$BENCH_NS" get pods -o wide
kubectl get nodes -L topology.kubernetes.io/zone,node.kubernetes.io/instance-type,karpenter.sh/nodepool

SAME_IP=$(kubectl -n "$BENCH_NS" get pod srv-same -o jsonpath='{.status.podIP}')
AZ_IP=$(kubectl -n "$BENCH_NS" get pod srv-a -o jsonpath='{.status.podIP}')
CROSS_IP=$(kubectl -n "$BENCH_NS" get pod srv-b -o jsonpath='{.status.podIP}')
: "${SAME_IP:?missing srv-same IP}" "${AZ_IP:?missing srv-a IP}" "${CROSS_IP:?missing srv-b IP}"
for bench_pod in srv-same srv-a srv-b; do
  kubectl -n "$BENCH_NS" logs "$bench_pod" --tail=30
  kubectl -n "$BENCH_NS" exec "$bench_pod" -- ss -lnt
done
for bench_ip in "$SAME_IP" "$AZ_IP" "$CROSS_IP"; do
  kubectl -n "$BENCH_NS" exec cli -- \
    curl --fail --silent --show-error --max-time 5 "http://$bench_ip:8080/" >/dev/null
done
```

次に進む前に、`cli` と `srv-same` が同じ node、`srv-a` が同一 AZ の別 node、`srv-b` が別 AZ にあることを検証してください。server の 5201/8080/8079 listener と起動エラーを確認します。過去の fixture に readiness probe がないため、Pod が Ready でも process が listening 中とは限りません。node ID、IP、image ID、実際の `iperf3 --version` / `fortio version` を記録してください。Pod が再作成された場合は停止して IP を更新します。

**2. RTT と参考用 HTTP request 1回。**

```bash
for bench_ip in "$SAME_IP" "$AZ_IP" "$CROSS_IP"; do
  kubectl -n "$BENCH_NS" exec cli -- ping -c 200 -i 0.05 -q "$bench_ip"
done
kubectl -n "$BENCH_NS" exec cli -- curl --fail --silent --show-error --max-time 5 \
  -o /dev/null -w 'connect=%{time_connect} total=%{time_total}\n' "http://$CROSS_IP:8080/"
```

**3. 転送量を制限し、operator のローカルファイルに出力する。**

```bash
for bench_ip in "$SAME_IP" "$AZ_IP" "$CROSS_IP"; do
  kubectl -n "$BENCH_NS" exec cli -- iperf3 -c "$bench_ip" -p 5201 -t 20 -P 1 -J > "t1-$bench_ip-P1.json"
  kubectl -n "$BENCH_NS" exec cli -- iperf3 -c "$bench_ip" -p 5201 -t 20 -P 8 -J > "t1-$bench_ip-P8.json"
done
kubectl -n "$BENCH_NS" exec cli -- \
  iperf3 -c "$CROSS_IP" -p 5201 -t 180 -P 4 -i 10 -J > t1-cross-sustained180-P4.json
```

終了 status に加えて JSON error も確認してください。`end.sum_sent.bits_per_second`、`end.sum_sent.retransmits`、`end.cpu_utilization_percent.host_total` / `remote_total`、`end.streams[].sender.mean_rtt` / `max_snd_cwnd` を読み取ります。iperf3 3.19 の process CPU は経過 wall time に対する1 CPU の時間を100 %としており、複数 thread では100 %を超える場合があります。TCP RTT field の単位は microsecond です。

**4. request latency。検証済みの各 server address で繰り返す。**

```bash
for bench_ip in "$SAME_IP" "$AZ_IP" "$CROSS_IP"; do
  kubectl -n "$BENCH_NS" exec cli -- fortio load -quiet -r 0.00001 -json - \
    -qps 100 -c 4 -t 60s "http://$bench_ip:8080/" > "http-$bench_ip.json"
  kubectl -n "$BENCH_NS" exec cli -- fortio load -quiet -r 0.00001 -json - \
    -qps 100 -c 4 -t 30s -keepalive=false "http://$bench_ip:8080/" > "new-connection-$bench_ip.json"
  kubectl -n "$BENCH_NS" exec cli -- fortio load -quiet -r 0.00001 -json - \
    -qps 0 -c 16 -t 20s "http://$bench_ip:8080/" > "closed-loop-$bench_ip.json"
  kubectl -n "$BENCH_NS" exec cli -- fortio load -quiet -r 0.00001 -json - \
    -grpc -ping -qps 100 -c 4 -t 30s "$bench_ip:8079" > "grpc-$bench_ip.json"
done
```

Fortio 1.69.5 では `-r` は histogram の最小 bucket resolution（秒）です。デフォルト `0.001` は1 ms、大きめの精度を指定する `0.00001` は10 µsで、より広い bucket もあり得ます。percentile は bucket の範囲内で補間され、観測された min / max も端点として扱います。そのため、値の入った bucket が1つだけでも **p50 = 0.5 ms とは限りません。** この報告では最初の粗い resolution の percentile を捨て、10 µs resolution で再実行しました。補間された percentile をすべて偽物と呼ばず、その経緯を保持してください。表中には1 msを超える tail 値と新規接続の median もあります。平均値とともに histogram 全体と error counter を保存してください。

**5. DNS: 1回の lookup の capture と計時 repeat を分ける。**

```bash
kubectl apply -f bench-dns.yaml
kubectl -n "$BENCH_NS" wait --for=condition=Ready pod/dns-default pod/dns-ndots1 --timeout=300s
for bench_pod in dns-default dns-ndots1; do
  kubectl -n "$BENCH_NS" exec "$bench_pod" -c app -- cat /etc/resolv.conf
  kubectl -n "$BENCH_NS" exec "$bench_pod" -c app -- ldd --version
done
```

terminal 1 では、単一 lookup の前に capture を開始します。この filter は通常の UDP と port 53 の TCP DNS を含みますが、暗号化 DNS や CoreDNS の upstream 経路は対象外です。単一 lookup が終わったら、warm repeat を始める前に Ctrl-C で capture を止めます。

```bash
kubectl -n bench-net exec -it dns-default -c sniffer -- \
  tcpdump -l -i eth0 -nn '(udp or tcp) and port 53'
```

terminal 2 でこのローカル helper を作り、**`kubectl exec -i`** で転送します。最初の mode は resolver call を正確に1回実行します。warm mode は、同じ process 内で計時しない warm-up を1回、その後に20回呼び出します。改訂手順では capture の範囲を明確にしています。

```bash
cat > dns-probe.py <<'PY'
import json
import socket
import statistics
import sys
import time

name, mode = sys.argv[1:3]
if mode not in ("first", "warm"):
    raise SystemExit("mode must be first or warm")

def one():
    started = time.perf_counter()
    socket.getaddrinfo(name, 80, socket.AF_UNSPEC, socket.SOCK_STREAM)
    return (time.perf_counter() - started) * 1000

first = one()
if mode == "first":
    print(json.dumps({"name": name, "first_process_ms": first}))
else:
    samples = [one() for _ in range(20)]
    ordered = sorted(samples)
    print(json.dumps({
        "name": name, "warmup_ms": first, "samples_ms": samples,
        "min_ms": ordered[0], "median_ms": statistics.median(ordered),
        "p90_ms": ordered[17], "max_ms": ordered[-1],
    }))
PY
BENCH_NS=bench-net
DNS_POD=dns-default
DNS_NAME=sts.ap-northeast-2.amazonaws.com
kubectl -n "$BENCH_NS" exec -i "$DNS_POD" -c app -- \
  python3 - "$DNS_NAME" first < dns-probe.py
```

capture を停止した後:

```bash
kubectl -n "$BENCH_NS" exec -i "$DNS_POD" -c app -- \
  python3 - "$DNS_NAME" warm < dns-probe.py
```

表の名前で繰り返し、`DNS_POD=dns-ndots1` に切り替え、capture の対象 Pod も変更してください。query / response pair は最初の1回だけの capture 範囲で数え、21 lookup を1回として数えないでください。同じ digest、resolver version、設定を使っても時間や cache 状態は異なる場合があります。元の image digest と完全な packet / JSON artifact はこのページに含まれていないため、完全に同じ結果を再現できる保証はありません。

**6. このテスト専用のリソースだけを削除する。** `bench-net` をこの実行専用に作成した場合は、結果を保存してから `kubectl delete namespace bench-net` を実行します。残りの node とコストを別途確認してください。Karpenter の consolidation はその policy、budget、ほかの workload に依存するため、namespace を削除しても node がすぐに削除されるとは限りません。`do-not-disrupt` はあらゆる強制的な中断手段に対する保護ではありません。

## 注意事項

- **node は新規でしたが、完全に単独ではありません。** このテスト用に Karpenter が3台の m5.xlarge node を起動した直後、consolidation によってほかの namespace の小さな Pod がいくつか移動しました（`cli` node に1個、`srv-b` node に3個。benchmark traffic と無関係な小規模の内部 service と controller）。実行中は idle または low-traffic で、load は最大180 s の burst です。`cli` node の CPU request は 3901m / 3920m（99 %）でしたが、実使用率を示す値ではありません。
- **各測定 cell は1回のみ（n = 1、1日）。** variance 推定のための独立した反復はありません。sample 数が限られるため、順位、比率、原因の説明にも限界があり、どれも SLA ではありません。
- **アプリケーションの ClusterIP と traffic distribution は測定していません。** benchmark namespace での Service 作成は `failed calling webhook "mservice.elbv2.k8s.aws": … no endpoints available for service "aws-load-balancer-webhook-service"` により失敗したと報告されています。`failurePolicy: Fail` の webhook は、一致する request を拒否します。その対象範囲は rule、namespace / object selector、match condition によって決まります。この過去の事象は、現在のクラスターで Service を作成できないという意味ではありません。benchmark のために webhook を迂回しておらず、DNS は既存の `kube-dns` Service を使いました。[トラブルシューティング手引き](../ops/16-troubleshooting-playbook.md) を参照してください。
- **ENA allowance counter は収集していません。** `ethtool -S` は適切な access を使い、host の実際の ENA interface に対して実行する必要があります。Pod の `eth0` は通常 veth であり、`hostNetwork` だけでは正しい device や権限があると証明できません。関連 counter は `bw_in_allowance_exceeded`、`bw_out_allowance_exceeded`、`pps_allowance_exceeded`、`conntrack_allowance_exceeded`、`linklocal_allowance_exceeded` です。retransmit はこれらの測定の代替になりません。
- **burst credit が尽きなかったのではなく、180 s 内に低下が観測されなかっただけです。** 「Up to」instance では、より長い転送が baseline（1.25 Gbps）へ throttle されることがあります。180 s を超えるテストはしていません。
- **DNS cache 状態は制御していません。** process 最初の lookup と repeat は異なりますが、`cache 30` で30秒間 hit するとは限りません。replica の選択と upstream の状態は両方の時間に影響し、報告された比較は観測結果です。
- **同一ノードの CPU 圧力は原因候補です。** client process CPU 99.8 % は 29.97 Gbps という結果の解釈と整合しますが、あらゆる bottleneck を証明するものでも、29.97 / 48.15 Gbps をほかの instance に適用できると示すものでもありません。
- **別の CNI mode や policy enforcement は比較していません。** prefix delegation と Security Groups for Pods は off で、この namespace に NetworkPolicy はありませんでした。これらの bare Pod は、対応 controller が管理する workload に対する VPC CNI NetworkPolicy enforcement の検証にはなりません。

## 関連資料

- [Amazon VPC CNI](./01-vpc-cni.md): この測定で使った data plane（VPC IP を直接受け取る Pod、prefix delegation、ENI/IP の warming）
- [ゾーン別クラスター運用](../ops/15-zonal-operations-guide.md): 測定 3 の請求を減らし得る zone-aligned placement と AZ failover 設計
- [トラブルシューティング手引き](../ops/16-troubleshooting-playbook.md): webhook failure の診断。この事象は過去のものです
- [サイドカーと Ambient モードの選択ガイド](../service-mesh/istio/comparison/03-sidecar-vs-ambient.md): 別 hardware / workload の実験。+1.29 ms はシナリオ全体の差です
- [EBS gp2 と gp3 の実測ベンチマーク](../storage/01-ebs-gp2-gp3-benchmark.md): 同じ cluster の storage 経路を測定
- [EKS 上の Kafka 実測ベンチマーク](../data-on-eks/kafka/09-kafka-benchmark.md): replication traffic、flow limit、availability tradeoff
- [ガイドブックのロードマップ: 実測ベンチマーク編](../roadmap.md)
- [クイズ: Pod ネットワークベンチマーク](../quizzes/networking/06-pod-network-benchmark-quiz.md)

### レビューで使用した主な参考資料

- [Fortio 1.69.5 histogram implementation](https://github.com/fortio/fortio/blob/v1.69.5/stats/stats.go) · [CLI flags](https://github.com/fortio/fortio/blob/v1.69.5/cli/fortio_main.go)
- [glibc 2.41 search ordering](https://github.com/bminor/glibc/blob/glibc-2.41/resolv/res_query.c) · [A/AAAA transport](https://github.com/bminor/glibc/blob/glibc-2.41/resolv/res_send.c)
- [CoreDNS Kubernetes / autopath requirements](https://coredns.io/plugins/kubernetes/)
- [Kubernetes Service traffic distribution](https://kubernetes.io/docs/concepts/services-networking/service/) · [virtual IP handling](https://kubernetes.io/docs/reference/networking/virtual-ips/)
- [EC2 ENA network metrics](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/monitoring-network-performance-ena.html)
- [Karpenter disruption and cleanup conditions](https://karpenter.sh/docs/concepts/disruption/)

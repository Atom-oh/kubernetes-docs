# Cilium ネットワーキング検証演習

この章では、期待される結果を含む8つの演習を順に行います。基準バージョンは Cilium 1.20.3、CLI 0.20.1、サポート対象の Kubernetes バージョン（1.33～1.36）で、レビュー日は2026年10月16日です。「1.30以降」のすべてのバージョンに互換性があると主張するものではありません。

## 前提条件

[ネットワーキングガイド](../../../networking/cilium/03-networking.md)と[インストールプロファイル](../../../networking/cilium/README.md)に従って準備した、破棄可能なクラスターを使用してください。スケジュール可能な Linux ノードを2台用意します。ノードのアーキテクチャに合ったツールを使い、同じくアーキテクチャに対応するイメージを取得してください。kubectl は文書化されたバージョンスキューの範囲内に保ちます。これらの演習では、既存 CNI の移行や、プロバイダー管理のネットワーク設定変更は行いません。

手動のポリシーラボでは、新しい namespace、Pod、Deployment、Service、namespace スコープの CiliumNetworkPolicy を作成する権限が必要です。既存のクラスター全体に適用されるポリシーや admission 制約も確認してください。namespace を分けても、それらの制約が無効になるわけではありません。変数が保持されるよう、シェルのブロックは同じシェルで実行してください。

## 1. インストールと基本テスト

インストールガイドで検証済みの CLI ダウンロード手順と、選択した Cilium プロファイルを使ってください。同じリリースに Helm と CLI の両方からインストールしないでください。また、検証していない `latest` の AMD64 アーカイブを使用しないでください。

```bash
set -euo pipefail
kubectl config current-context
kubectl version -o yaml
cilium version
cilium status --wait
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
```

任意で、破棄可能なクラスター上で保守されている connectivity suite を実行できます。suite はワークロードとポリシーを作成し、外部の宛先に接続することがあります。実行対象のテストと前提条件を確認してください。

```bash
cilium connectivity test --test-namespace cilium-net-smoke \
  --namespace-labels docs-audit-lab=cilium-networking-03
```

CLI 0.20.1 は連番サフィックスを追加します。既定の単一 suite では `cilium-net-smoke-1` が使われます。失敗やスキップされたケースを確認してください。コマンドが完了しても、未テストのクラウド環境や機能の組み合わせまで動作が確認されたことにはなりません。

<details>
<summary>期待される結果と自己確認</summary>

インストールしたバージョンが文書化された互換性表に合い、agent が Ready になり、選択した connectivity ケースが成功します。DaemonSet が Ready でもノード間ルーティングを証明しない理由と、「kubectl 1.31以降」だけでは新しい API server に対する十分な条件にならない理由を説明してください。

</details>

## 2. Network Policy のテスト

### 隔離されたテスト namespace とワークロードを作成する

```bash
kubectl create namespace cilium-net-lab
kubectl label namespace cilium-net-lab docs-audit-lab=cilium-networking-03
```

namespace の作成時にすでに存在すると報告されたら、そこで停止し、ファイルやコマンド全体で一貫して使う新しい名前を選んでください。他者の namespace を付け替えたり、再利用したりしないでください。

次のイメージ digest は公式 CLI 0.20.1 のテスト既定値です。その Deployment のソースでは、curl 用イメージに `/usr/bin/pause` を、TCP 8080 と `/` の readiness を使う JSON mock server に使用しています。これらはテスト用イメージであり、本番アプリケーション向けの推奨ではありません。backend の anti-affinity により、frontend とは別のノードに配置されます。

**`lab-app.yaml`**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend
  namespace: cilium-net-lab
  labels:
    app: frontend
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: v1
kind: Pod
metadata:
  name: outsider
  namespace: cilium-net-lab
  labels:
    app: outsider
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: cilium-net-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      automountServiceAccountToken: false
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: frontend
            topologyKey: kubernetes.io/hostname
      containers:
      - name: http
        image: quay.io/cilium/json-mock:v1.4.1@sha256:6a66df90808a39c02e7a9d58af7bf0e54d8f8b7d4bc528f48c891969a7049195
        ports:
        - containerPort: 8080
          name: http
        readinessProbe:
          httpGet:
            path: /
            port: http
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: cilium-net-lab
spec:
  selector:
    app: backend
  ports:
  - name: http
    port: 8080
    targetPort: http
    protocol: TCP
```

```bash
kubectl apply -f lab-app.yaml
kubectl -n cilium-net-lab wait --for=condition=Ready pod/frontend pod/outsider --timeout=120s
kubectl -n cilium-net-lab rollout status deployment/backend --timeout=120s
kubectl -n cilium-net-lab get pods -o wide
kubectl -n cilium-net-lab get endpointslices -l kubernetes.io/service-name=backend
BACKEND_IP=$(kubectl -n cilium-net-lab get service backend -o jsonpath='{.spec.clusterIP}')
test -n "$BACKEND_IP"
```

backend が Pending になる場合、anti-affinity を満たせるノードが不足している可能性があります。これをネットワークポリシーの失敗と解釈しないでください。新しいポリシーを適用する前に、**両方の**クライアントから正常な backend に到達できることを確認してください。この ingress テストでは Service IP を使い、DNS の失敗を切り分けます。

```bash
kubectl -n cilium-net-lab exec frontend -- \
  curl --fail --silent --show-error --connect-timeout 3 --max-time 5 "http://$BACKEND_IP:8080/"
kubectl -n cilium-net-lab exec outsider -- \
  curl --fail --silent --show-error --connect-timeout 3 --max-time 5 "http://$BACKEND_IP:8080/"
```

### ポリシーを適用して確認する

**`allow-frontend.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: cilium-net-lab
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-net-lab
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
```

```bash
kubectl apply -f allow-frontend.yaml
kubectl -n cilium-net-lab get ciliumnetworkpolicy allow-frontend-to-backend -o yaml
kubectl -n cilium-net-lab exec frontend -- \
  curl --fail --silent --show-error --connect-timeout 3 --max-time 5 "http://$BACKEND_IP:8080/"
```

対象 endpoint でポリシーが実際に反映されるのを待ち、許可されるリクエストが引き続き成功することを再確認してください。以前の接続で許可されたことだけでは、新しいポリシーが反映済みとは言えません。各コマンドは新しい curl プロセスを開始します。

```bash
if kubectl -n cilium-net-lab exec outsider -- \
  curl --fail --silent --show-error --connect-timeout 3 --max-time 5 "http://$BACKEND_IP:8080/"; then
  echo "Unexpected allowed request: inspect combined policy and realization" >&2
  exit 1
else
  denied_rc=$?
  printf 'Outsider request failed with exit %s; correlate the flow before declaring a policy pass.\n' "$denied_rc"
fi
```

終了コードが **0以外というだけで、拒否テストの成功とは判断できません**。exec/RBAC、curl の不足、ルーティング、backend、その他の失敗でも非ゼロになります。curl のタイムアウトは多くの場合 exit code 28 ですが、正常だった baseline と引き続き動作する frontend を基準に、送信元・宛先・ポートとポリシーによる拒否フローを照合してください。namespace スコープのこのルールが、他のポリシーによる許可まで防ぐわけではありません。

<details>
<summary>期待される結果と自己確認</summary>

ポリシー適用前は両方のクライアントが backend に到達します。反映後は frontend が引き続き成功し、裏付けとなるポリシーの証拠とともに outsider が拒否されます。EndpointSlice の欠落、DNS エラー、任意の非ゼロ終了だけでは分離を証明できない理由を説明してください。この L3/L4 ポリシーは HTTP を解析しません。

</details>

## 3. Hubble の可視性をテストする

プロファイルで有効になっている Hubble Relay/UI と、対応する Hubble CLI を使ってください。次の port-forward は別のターミナルで維持し、観測コマンドはもう一方のターミナルで実行します。

```bash
cilium hubble port-forward
```

```bash
hubble status
hubble observe --namespace cilium-net-lab --last 50
hubble observe --from-pod cilium-net-lab/outsider --verdict DROPPED --last 20
cilium hubble ui
```

観測中に新しいリクエストを発生させてください。イベントの欠落、集約、filter によって見える内容が変わります。HTTP flow の表示には対応する L7 proxy／visibility の構成が必要で、上の L4 ルールでは追加されません。設定済みの L7 拒否は、packet の DROPPED event ではなく HTTP 403 を返すことがあります。

<details>
<summary>期待される結果と自己確認</summary>

Relay に接続でき、flow に意図した endpoint が示され、拒否テストの証拠がそのリクエストと一致します。この L4 のみのラボで HTTP 記録がないことは、Hubble の障害を示すものではない理由を説明してください。

</details>

## 4. パフォーマンステスト

一致する client/server ワークロードを作成する[ガイドの保守対象 `cilium connectivity perf` の例](../../../networking/cilium/03-networking.md)を実行してください。同一ノードとノード間の結果を分け、ノード配置、バージョン、経路の MTU、ポリシー／暗号化設定を記録します。

以前のテストでは、無関係な `netperf-*` Pod 名と iperf3 イメージ、TCP のみの Service が混在していました。別途用意した iperf3 環境で UDP をテストするには、設定したポートで **TCP 制御通信と UDP データ通信の両方**が必要です。`-b 1G` を指定しただけでは、1 Gbit/s が実際に送信されることを証明できません。

<details>
<summary>期待される結果と自己確認</summary>

選択したテスト用ワークロードがすべて Ready になり、結果にシナリオが明記されます。TCP request/response、接続確立、stream throughput、UDP の提示レート／損失の違いを説明してください。ベンチマーク結果は記録した構成に適用されるもので、すべての Cilium mode やクラウド環境を代表するものではありません。

</details>

## 5. 任意の高度な機能を確認する

各機能は、個別に準備して文書化したプロファイルで構成してください。**確認のたびにクラスター CNI をアンインストールしないでください。** Helm flag だけでは、不足する key、route、API 到達性、BGP peer は補われません。

| 機能 | 準備すること | 観測すること |
|---|---|---|
| kube-proxy replacement | `kubeProxyReplacement: true`、到達可能な `k8sServiceHost`/`k8sServicePort`、対応 datapath、移行計画 | 実際の agent 状態と Service 通信。`strict` は現行の値ではありません |
| IPsec/WireGuard | 適切な暗号化 mode、key 管理、port/MTU、対応する通信範囲 | agent の暗号化状態と実際のノード間経路 |
| BGP Control Plane | `bgpControlPlane.enabled: true`、バージョンに対応した BGP resource、到達可能な設定済み peer | session と広告 route。ローカルの転送テーブルが設定されるとは限りません |

対象ノード上の agent を選択してください。

```bash
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
export CILIUM_POD=cilium-REPLACE-WITH-AGENT-ON-TARGET-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg encrypt status
cilium bgp peers
kubectl get ciliumbgpclusterconfigs,ciliumbgppeerconfigs,ciliumbgpadvertisements
```

任意機能のコマンドは、その機能を構成した場合にのみ解釈してください。基本プロファイルで機能が無効／未構成なのは想定どおりです。単独の `cilium bgp peers` コマンドはクラスターのノード状態を報告します。古い agent 内の BGP コマンドは非推奨です。BGP には該当する `cilium.io/v2` 設定 resource が必要です。削除された `bgp.enabled` と `bgp.announce.loadbalancerIP` の設定では session は確立されません。

<details>
<summary>期待される結果と自己確認</summary>

観測した状態が選択したプロファイルに一致し、関連する通信／route の証拠で結果を裏付けられます。「BGP established」だけでは内部 Pod routing を証明できない理由、または暗号化状態だけではすべての通信経路が暗号化されたと証明できない理由を説明してください。

</details>

## 6. 互換性を確認する

```bash
kubectl version -o yaml
cilium version
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.nodeInfo.kernelVersion}{"\n"}{end}'
kubectl -n kube-system get configmap cilium-config -o yaml
kubectl -n kube-system get daemonset cilium -o yaml
```

文書化された kernel backport も含め、バージョンと機能を互換性表と照合してください。host の設定ファイルを読む前に、実際の CNI 設定と volume mount を確認します。`/etc/cni/net.d/05-cilium.conf` は、すべてのコンテナに共通するパスやファイル名ではありません。chaining やカスタム構成では異なります。ファイルが存在するだけでは、実行時の互換性を証明できません。

<details>
<summary>期待される結果と自己確認</summary>

バージョンと kernel の要件がプラットフォームに合い、Pod が意図した CNI から address を取得し、通信テストが成功します。CNI のインストール、IPAM による割り当て、end-to-end forwarding の違いを説明してください。

</details>

## 7. トラブルシューティング

```bash
cilium status --verbose
kubectl -n kube-system logs "$CILIUM_POD" -c cilium-agent --tail=100
kubectl -n kube-system logs deployment/cilium-operator --tail=100
kubectl -n kube-system logs deployment/hubble-relay --tail=100
```

frontend endpoint を調べる前に、frontend が動作するノードの agent を選択してください。

```bash
kubectl -n cilium-net-lab get pod frontend -o wide
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg endpoint get pod-name:cilium-net-lab:frontend
```

ingress が拒否された場合は、backend 側の agent/endpoint も調べてください。期待するポリシー、反映状態、route/backend の正常性、観測した flow を比較します。削除済みの `policy trace` コマンドを使ったり、引用符で囲んでいない `<pod-name>` shell placeholder を人間向けの表から解析したりしないでください。

必要なら `cilium sysdump` で診断情報を収集し、共有前に archive 内の log/resource 情報を確認します。`cilium clustermesh status` は Cluster Mesh を構成した場合にのみ使用します。Relay の状態は接続を設定した後に `hubble status` で確認します。

<details>
<summary>期待される結果と自己確認</summary>

DaemonSet Pod が偶然選ばれるのではなく、正しいノードと endpoint の証拠を確認できています。backend が未準備、route が失敗、ポリシーが拒否、観測自体が欠落した状態を、どの証拠で区別できるか説明してください。

</details>

## 8. クリーンアップ

この実行で作成した namespace を確認し、先に結果を保存してください。

```bash
kubectl get namespaces -l docs-audit-lab=cilium-networking-03
LAB_OWNER=$(kubectl get namespace cilium-net-lab -o jsonpath='{.metadata.labels.docs-audit-lab}')
test "$LAB_OWNER" = cilium-networking-03
kubectl delete namespace cilium-net-lab
```

CLI suite を実行した場合、生成された `cilium-net-smoke-1` / `cilium-net-perf-1` namespace を削除する前に、所有者がこの実行であることを個別に確認してください。無関係な namespace を一括削除したり、アプリケーションの後片付けとして Cilium をアンインストールしたりしないでください。ローカルの port-forward は Ctrl-C で停止します。

<details>
<summary>期待される結果と自己確認</summary>

この実行が作成したテストリソースだけが削除され、インストール済み CNI と他のワークロードは稼働したままです。機能を比較するための手順として CNI を繰り返しアンインストールするのが不適切である理由を説明してください。

</details>

## 検証の限界と参考資料

公開されている YAML/Helm 値、shell 構文、CLI/API 契約は、これらのワークロードをデプロイせずに確認しました。ホスト再起動後に、ライブクラスター、イメージ実行、Helm render、スループット測定は行っていません。admission、イメージのアーキテクチャ／pull policy、capacity、実際の datapath、期待される結果は、準備済みの環境で確認する必要があります。

- [CLI 0.20.1 のイメージ既定値](https://github.com/cilium/cilium-cli/blob/v0.20.1/vendor/github.com/cilium/cilium/cilium-cli/defaults/defaults.go)、[テスト用 Deployment](https://github.com/cilium/cilium-cli/blob/v0.20.1/vendor/github.com/cilium/cilium/cilium-cli/connectivity/check/deployment.go)、[connectivity/perf の flag](https://github.com/cilium/cilium-cli/blob/v0.20.1/vendor/github.com/cilium/cilium/cilium-cli/cli/connectivity.go)
- [Cilium 1.20.3 のポリシー API](https://github.com/cilium/cilium/blob/v1.20.3/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnetworkpolicies.yaml)、[L7 の動作](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/layer7.rst)、[BGP 設定](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/bgp-control-plane/bgp-control-plane-configuration.rst)、[BGP CLI](https://github.com/cilium/cilium-cli/blob/v0.20.1/vendor/github.com/cilium/cilium/cilium-cli/cli/bgp.go)、[agent コマンド](https://github.com/cilium/cilium/tree/v1.20.3/Documentation/cmdref)
- [Kubernetes バージョンスキュー](https://kubernetes.io/releases/version-skew-policy/)、[iperf3 の実行方法](https://software.es.net/iperf/invoking.html)、[ネットワーキングガイド](../../../networking/cilium/03-networking.md)

# パート13: バージョン、インストール/アップグレード、Cluster Meshクイズ

> **Cilium 1.20.2 · 2026-10-15**

1. アップグレードとロールバックの両方について、upstreamがテストしているアップグレード経路はどれですか？
   - A) 現行マイナーバージョンの最新パッチへ更新してから、連続するマイナーバージョン間だけを移行する（例: 1.19と1.20の間を往復する）
   - B) 最新パッチがインストールされていれば、NからN+2へのマイナーバージョン移行はどれでもよい
   - C) 事前チェックのchartが通れば、どのマイナーバージョンから最新マイナーへも移行できる
   - D) 最初にagentだけを更新し、operatorは後でマイナーバージョンを更新する

   <details>
   <summary>回答を表示</summary>

   **回答: A) 現行マイナーバージョンの最新パッチへ更新してから、連続するマイナーバージョン間だけを移行する（例: 1.19と1.20の間を往復する）**

   マイナーバージョンを飛ばす経路はテストされておらず、すべてのコンポーネントを同じバージョンで実行する必要があります。最初に最新パッチへ更新すると、修正をすべて含むバージョンへロールバックできます。

   </details>

2. 新しいマイナーバージョンに移行するとき、`helm upgrade --reuse-values`を実行してはいけないのはなぜですか？
   - A) Cilium CRDが削除されるため
   - B) `upgradeCompatibility`が新しいバージョンへリセットされるため
   - C) OCI chartが従来のリポジトリchartに置き換えられるため
   - D) 古いリリースの値を再利用して新しいchartのデフォルトを無視するため、壊れたマニフェストが生成されることがある

   <details>
   <summary>回答を表示</summary>

   **回答: D) 古いリリースの値を再利用して新しいchartのデフォルトを無視するため、壊れたマニフェストが生成されることがある**

   `helm get values`で値を保存し、名前変更または削除されたキーを確認してから、`-f`で指定してください。chartのバージョンが変わらない場合、たとえば同じバージョンのCluster Mesh用の値を適用する場合に限り、`--reuse-values`を使えます。

   </details>

3. `maxConnectedClusters`のデフォルト値はいくつですか。また、511に設定するとどのような代償がありますか？
   - A) 255。KVStoreMeshを無効にする必要がある
   - B) 255。クラスター内IDの最大数が65535から32767に減る
   - C) 127。クラスター名の長さ制限が半分になる
   - D) 511。IDの範囲は変わらないが、オーバーレイモードしか使えない

   <details>
   <summary>回答を表示</summary>

   **回答: B) 255。クラスター内IDの最大数が65535から32767に減る**

   クラスターIDは数値IDのビットを使います。全クラスターで同じ値にし、インストール時にのみ設定してください。稼働中のクラスターで変更すると、接続が中断したりポリシーが誤って適用されたりする可能性があります。

   </details>

4. 1.20と1.21のプレリリースでは、`clustermesh.apiserver.tls.authMode`のデフォルトは何ですか？
   - A) 1.20では`legacy`、1.21では`migration`
   - B) 1.20では`cluster`、1.21では`cluster-strict`
   - C) 1.20では`migration`、1.21では`cluster`（新しい`cluster-strict`オプションもある）
   - D) どちらも`migration`

   <details>
   <summary>回答を表示</summary>

   **回答: C) 1.20では`migration`、1.21では`cluster`（新しい`cluster-strict`オプションもある）**

   `cluster`モードでは各クラスターが`remote-<cluster-name>`として認証され、共通CAが必要です。ユーザー提供の証明書と`tls.auto.enabled=false`を使っている場合は、CNを新しい値にしてリモート証明書を再発行するか、`authMode`を`migration`に戻してください。

   </details>

5. Cilium 1.19以降のCluster Meshで、clusterラベルを指定しないポリシーセレクターは、どのエンドポイントに一致しますか？
   - A) 接続済みのすべてのクラスターのエンドポイント
   - B) 何にも一致せず、ポリシーが拒否される
   - C) リモートクラスターのグローバルNamespace内にあるエンドポイントだけ
   - D) ローカルクラスターのエンドポイントだけ

   <details>
   <summary>回答を表示</summary>

   **回答: D) ローカルクラスターのエンドポイントだけ**

   1.19では`policy-default-local-cluster`（Helmの`clustermesh.policyDefaultLocalCluster`）がデフォルトでtrueです。リモートクラスターを選択するには`io.cilium.k8s.policy.cluster`ラベルを指定し、すべてのクラスターを対象にするには`Exists`式を使います。1.18までのデフォルトは全クラスターでした。

   </details>

6. agentがローカルキャッシュからリモートクラスターの状態を読み取れるようにするclustermesh-apiserverのコンテナはどれですか？
   - A) `kvstoremesh`。リモート状態をローカルetcdへ取り込む
   - B) `apiserver`。リモートクラスターをミラーする
   - C) `etcd`。リモートetcdインスタンスから直接取得する
   - D) cilium-agent。リモートetcdごとに1つの接続を保持する

   <details>
   <summary>回答を表示</summary>

   **回答: A) `kvstoremesh`。リモート状態をローカルetcdへ取り込む**

   `apiserver`コンテナは、ローカルクラスターの状態だけをローカルetcdへ同期します。KVStoreMeshは1.16以降デフォルトで有効であり、1.21プレリリースでは無条件に有効です。

   </details>

7. Cilium 1.20で必要なGateway API CRDのバージョンと、TLSRouteに関する注意点は何ですか？
   - A) v1.6.1。Helm chartがCRDをインストールし、TLSRouteを自動的に置き換える
   - B) v1.4。TLSRouteはまったくサポートされない
   - C) v1.6.1。standard-channelのTLSRoute v1.6をインストールすると既存の`v1alpha2`オブジェクトが読み取り不能になるため、すでに使っている場合はexperimental v1.6.1 TLSRouteを使う
   - D) v1.3.0。TLSRouteには`bpf.tproxy`フラグが必要

   <details>
   <summary>回答を表示</summary>

   **回答: C) v1.6.1。standard-channelのTLSRoute v1.6をインストールすると既存の`v1alpha2`オブジェクトが読み取り不能になるため、すでに使っている場合はexperimental v1.6.1 TLSRouteを使う**

   chartはGateway API CRDをインストールしません。チャネルを切り替える前にTLSRouteオブジェクトをバックアップし、`kubectl apply --server-side`でCRDを適用してください。

   </details>

8. EKS Auto ModeでCiliumをCNIとして使用できますか？
   - A) `cni.chainingMode=aws-cni`を使えば可能
   - B) 不可。AWSによると、Auto Modeでは代替CNIやネットワークポリシープラグインはサポートされない
   - C) オーバーレイモードに限り可能
   - D) `aws-node`に一致しないnode selectorを設定すれば可能

   <details>
   <summary>回答を表示</summary>

   **回答: B) 不可。AWSによると、Auto Modeでは代替CNIやネットワークポリシープラグインはサポートされない**

   マネージドまたはセルフマネージドのノードグループを使ってください。`aws-node`のpatchとENIモードは標準のノードグループに適用されるもので、Auto Modeには適用されません。

   </details>

9. `cilium_drift_checker_config_delta > 0`は何を意味しますか？
   - A) agentがKubernetes APIサーバーに接続できない
   - B) CiliumNodeConfigの検証に失敗した
   - C) `cilium-config` ConfigMapに稼働中のagentが適用していないキーがあり、agentの再起動が必要
   - D) operatorとagentで異なるイメージバージョンが使われている

   <details>
   <summary>回答を表示</summary>

   **回答: C) `cilium-config` ConfigMapに稼働中のagentが適用していないキーがあり、agentの再起動が必要**

   drift checkerは、監視対象のConfigMapとagent起動時の設定を比較します。`cilium config set --restart=false`は、保留中の変更を作成し、その変更がメトリクスに表示される方法の1つです。

   </details>

10. KVStoreからCRDへDouble Write移行するとき、`identity-allocation-mode`の値をどの順に設定しますか？
    - A) `crd`、次に`doublewrite-readcrd`、その後`kvstore`
    - B) `doublewrite-readcrd`、次に`doublewrite-readkvstore`、その後`crd`
    - C) `kvstore`、次に`crd`。`doublewrite-readkvstore`はロールバック状態としてだけ使う
    - D) `kvstore`、次に`doublewrite-readkvstore`、次に`doublewrite-readcrd`、最後に`crd`

    <details>
    <summary>回答を表示</summary>

    **回答: D) `kvstore`、次に`doublewrite-readkvstore`、次に`doublewrite-readcrd`、最後に`crd`**

    2つのDouble Write段階では、最初にoperatorを、次にagentを再デプロイします。最後の`crd`段階では、最初にagentを再デプロイし、その後operatorを再デプロイしてください。この機能はbetaです。1.21プレリリースでは、一度だけ実行する`migrate-identity`ツールは非推奨です。

    </details>

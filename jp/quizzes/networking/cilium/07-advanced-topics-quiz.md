# Cilium 上級クイズ

> **レビュー対象の基準バージョン**: Cilium 1.20.3、Cilium CLI 0.20.1、Hubble CLI 1.20.2
> **最終レビュー日**: 2026年10月16日

[ガイドに戻る](../../../networking/cilium/07-advanced-topics.md)

## eBPF テクノロジー

1. **このコースで扱う Linux eBPF データプレーンプログラムは、どこで実行されますか？**

   - A) ブラウザー内のみ
   - B) Linux カーネルのサポート対象フック
   - C) Envoy 内のみ
   - D) Kubernetes API サーバー

   <details>
   <summary>回答を表示</summary>

   **回答: B) Linux カーネルのサポート対象フック**

   Cilium は eBPF プログラムをカーネルフックにアタッチします。ユーザー空間のコンポーネントがそれらをロードして管理します。

   </details>

2. **カーネルが eBPF プログラムを受け入れる前に、どの仕組みが検査しますか？**

   - A) 暗号化
   - B) コンテナのスケジューリング
   - C) verifier
   - D) DNS

   <details>
   <summary>回答を表示</summary>

   **回答: C) verifier**

   verifier は、メモリアクセスの安全性や、プログラムの実行が有界であることなどを検査します。ただし、実装上の脆弱性やあらゆるカーネル障害が起きないことを絶対に保証するものではありません。

   </details>

3. **Cilium のソフトウェア eBPF データプレーンに一般的な必須要件ではないものはどれですか？**

   - A) サポート対象のカーネル機能
   - B) 適切な権限
   - C) 互換性のあるネットワーク設定
   - D) 専用ハードウェアオフロード

   <details>
   <summary>回答を表示</summary>

   **回答: D) 専用ハードウェアオフロード**

   ハードウェアオフロードは必須ではありません。性能は、実際の通信経路、ワークロード、カーネル、ハードウェアによって異なります。

   </details>

## ネットワークモデル

4. **このコースで説明する Cilium のネイティブ／トンネル方式に含まれないものはどれですか？**

   - A) VXLAN
   - B) Geneve
   - C) ネイティブルーティング
   - D) MPLS データプレーンモード

   <details>
   <summary>回答を表示</summary>

   **回答: D) MPLS データプレーンモード**

   これは Cilium の設定方式についての説明であり、外部アンダーレイで MPLS を使うことまで禁止するものではありません。

   </details>

5. **Cilium の kube-proxy 置き換えを実現するものは何ですか？**

   - A) iptables チェーンのみ
   - B) IPVS ルールのみ
   - C) eBPF による Service 処理と、任意で使える XDP アクセラレーション
   - D) 必須の外部ハードウェアスイッチ

   <details>
   <summary>回答を表示</summary>

   **回答: C) eBPF による Service 処理と、任意で使える XDP アクセラレーション**

   ソケットとパケット経路の eBPF が Service 処理を実装します。XDP は条件を満たす外部転送経路を高速化するもので、すべての Service に必要なわけではありません。

   </details>

6. **Kubernetes を認識したフローレコードを公開する Cilium の可観測性コンポーネントはどれですか？**

   - A) Helm
   - B) Hubble
   - C) kube-scheduler
   - D) etcdctl

   <details>
   <summary>回答を表示</summary>

   **回答: B) Hubble**

   Hubble が公開するフロー情報は限定された観測結果であり、すべてのパケットを損失なく記録したものではありません。ほかのパケット解析ツールには、それぞれ異なる役割があります。

   </details>

## IPAM と Network Policy

7. **VPC アドレスの割り当てに EC2 ENI を使う Cilium IPAM モードはどれですか？**

   - A) cluster-pool
   - B) kubernetes host scope
   - C) ENI
   - D) 汎用の CRD ベース

   <details>
   <summary>回答を表示</summary>

   **回答: C) ENI**

   ENI モードは AWS ネットワークインターフェイスとアドレス割り当てを使います。ただし、EKS のすべてのコンピュート方式が代替 CNI をサポートするわけではありません。プラットフォームの前提条件を確認してください。

   </details>

8. **toFQDNs は何を使って送信接続を許可しますか？**

   - A) 検証済み JWT
   - B) 固定された Service ポートのみ
   - C) DNS 名との照合によって学習した宛先 IP
   - D) TLS の自動復号

   <details>
   <summary>回答を表示</summary>

   **回答: C) DNS 名との照合によって学習した宛先 IP**

   DNS クエリの許可／proxy による観測と、その後の IP 接続は別の処理です。このルールは、リモートアプリケーションを認証するものではありません。

   </details>

9. **CiliumClusterwideNetworkPolicy でノードのホストポリシーに使うセレクターはどれですか？**

   - A) すべてのノードを対象にする endpointSelector
   - B) nodeSelector
   - C) トップレベルの serviceSelector
   - D) トップレベルの namespaceSelector

   <details>
   <summary>回答を表示</summary>

   **回答: B) nodeSelector**

   nodeSelector はクラスター全体に適用するホストポリシーのフィールドです。Kubernetes のすべてのセレクター形式が、CiliumNetworkPolicy のトップレベルフィールドとして互換的に使えるわけではありません。

   </details>

## L2～L7 ネットワーキング

10. **Cilium の HTTP ポリシーでリクエスト照合に使うフィールドではないものはどれですか？**

   - A) Path
   - B) Method
   - C) Headers
   - D) レスポンスレイテンシー

   <details>
   <summary>回答を表示</summary>

   **回答: D) レスポンスレイテンシー**

   HTTP が可視な場合、HTTP ルールはサポート対象のリクエストフィールドを検査します。レイテンシーを測定しても、レイテンシーに基づく許可ルール用のフィールドが追加されるわけではありません。

   </details>

11. **identity ベースのネットワークポリシーだけでは提供されないものは何ですか？**

   - A) endpoint の選択
   - B) ネットワークアクセスの制限
   - C) 方向別のルール
   - D) エンドユーザーのトークン認証

   <details>
   <summary>回答を表示</summary>

   **回答: D) エンドユーザーのトークン認証**

   ユーザー認証には、適切なアプリケーションまたはゲートウェイのロジックが必要です。SPIRE の相互認証と、ベータ版 ztunnel のワークロード mTLS は、それぞれ制限のある別設定の機能です。

   </details>

12. **適切な経路で設定した場合、Cilium の Envoy 統合が提供できる機能はどれですか？**

   - A) HTTP ロードバランシング
   - B) HTTP の可視性
   - C) HTTP ポリシーの適用
   - D) 上記すべて

   <details>
   <summary>回答を表示</summary>

   **回答: D) 上記すべて**

   これらの機能は、選択した proxy 経路と設定によって異なります。関係のないネットワーク機能を有効にしても、すべての L7 機能が有効になるわけではありません。

   </details>

## セキュリティと可視性

13. **Hubble UI の機能はどれですか？**

   - A) Slack インシデントの自動作成
   - B) サービス依存関係マップとフローの探索
   - C) ソースコードのデプロイ管理
   - D) JWT 署名キーのローテーション

   <details>
   <summary>回答を表示</summary>

   **回答: B) サービス依存関係マップとフローの探索**

   通知や自動応答には別の統合が必要です。UI は観測されたネットワークフローを可視化します。

   </details>

14. **Cilium で利用できるノード間トランスポート暗号化モードはどれですか？**

   - A) IPsec と WireGuard
   - B) HTTP と DNS
   - C) Relay と Prometheus
   - D) TCP と UDP

   <details>
   <summary>回答を表示</summary>

   **回答: A) IPsec と WireGuard**

   暗号化の適用範囲と前提条件を確認してください。ノードトンネルでは同一ノード内の通信は暗号化されず、ワークロード mTLS は別の機能です。

   </details>

15. **HTTP の Method と Path を照合するポリシー層はどれですか？**

   - A) L2 アドレス照合のみ
   - B) L7 ポリシー
   - C) L3 CIDR 照合のみ
   - D) トランスポート暗号化

   <details>
   <summary>回答を表示</summary>

   **回答: B) L7 ポリシー**

   現行の Cilium HTTP ポリシーでは、これらのフィールドを検査できます。Kafka の topic ルールは削除されています。また、header の照合はトークン認証ではありません。

   </details>

## 上級トピックとユースケース

16. **ClusterMesh の機能ではないものはどれですか？**

   - A) クラスター間の Service ディスカバリー
   - B) リモート endpoint identity をポリシーで使用する
   - C) クラスター間の Service ロードバランシング
   - D) 共有永続ストレージ

   <details>
   <summary>回答を表示</summary>

   **回答: D) 共有永続ストレージ**

   ClusterMesh はネットワークのメタデータと接続性を扱います。共有ストレージを提供したり、すべてのポリシーリソースを自動的に複製したりするものではありません。

   </details>

17. **Bandwidth Manager について正しい説明はどれですか？**

   - A) 帯域幅をグラフ化するだけ
   - B) 設定した Pod ごとの帯域幅制限を適用する
   - C) 各 Pod に物理リンクの帯域を予約することを保証する
   - D) 機械学習で将来のトラフィックを予測する

   <details>
   <summary>回答を表示</summary>

   **回答: B) 設定した Pod ごとの帯域幅制限を適用する**

   egress では EDT、ingress では eBPF の token bucket を使います。制限は Pod ごとに適用され、egress での L7 処理や kind 環境には文書化された制約があります。帯域が予約されるわけではありません。

   </details>

18. **Cilium Host Firewall の適用対象は何ですか？**

   - A) コンテナ間の HTTP のみ
   - B) ストレージ暗号化のみ
   - C) ホストのネットワークトラフィック
   - D) 外部 SaaS の認可

   <details>
   <summary>回答を表示</summary>

   **回答: C) ホストのネットワークトラフィック**

   Host Firewall はノード／ホスト向けのネットワークポリシーであり、汎用的な実行時システムコール制御機能ではありません。

   </details>

19. **Egress Gateway は、条件に一致した送信トラフィックに何を行いますか？**

   - A) 選択した予測可能なゲートウェイ IP に SNAT する
   - B) 常に元の Pod の送信元 IP を保持する
   - C) すべての外部接続を自動的に暗号化する
   - D) 前提条件なしで、すべてのクラウドにパブリック IP を作成する

   <details>
   <summary>回答を表示</summary>

   **回答: A) 選択した予測可能なゲートウェイ IP に SNAT する**

   ゲートウェイの IP、インターフェイス、ルーティングを事前に用意する必要があります。新しい Pod はポリシー適用前に通信できる場合があります。また、ClusterMesh と CiliumEndpointSlice には非互換性の制約があります。

   </details>

20. **Cilium BGP Control Plane が行う操作はどれですか？**

   - A) 学習したすべてのルートをローカル Linux データプレーンにインストールする
   - B) 選択した Pod または Service のプレフィックスを peer にアドバタイズする
   - C) すべての Service の DNS レコードを作成する
   - D) 外部ルーターのインターフェイスを割り当てる

   <details>
   <summary>回答を表示</summary>

   **回答: B) 選択した Pod または Service のプレフィックスを peer にアドバタイズする**

   BGP アドバタイズは、ローカルのデータプレーンルーティング、アドレス割り当て、DNS とは別の処理です。外部ルーターと実際の順方向／戻り経路を確認してください。

   </details>

## パフォーマンスとトラブルシューティング

21. **ネイティブの NIC ドライバーフックで、サポート対象の外部 Service 転送を処理できる仕組みはどれですか？**

   - A) Grafana ダッシュボード
   - B) XDP アクセラレーション
   - C) DNS 検索サフィックス
   - D) サイズの大きいアプリケーションログファイル

   <details>
   <summary>回答を表示</summary>

   **回答: B) XDP アクセラレーション**

   XDP には、サポート対象の NIC／ドライバーと通信経路が必要です。任意のワークロードで一定のレイテンシーやスループット改善が得られるとは限りません。

   </details>

22. **ワークロードを実際に作成し、接続シナリオをテストするスタンドアロン Cilium CLI コマンドはどれですか？**

   - A) `cilium status`
   - B) `cilium connectivity test`
   - C) `hubble status`
   - D) `kubectl get nodes`

   <details>
   <summary>回答を表示</summary>

   **回答: B) `cilium connectivity test`**

   これはリソースとトラフィックを作成する能動的なテストであり、読み取り専用の状態確認ではありません。隔離されたテスト範囲で実行し、クリーンアップを確認してください。

   </details>

23. **対象の Cilium agent 内で、1つの endpoint の詳細を調べるコマンドはどれですか？**

   - A) `cilium endpoint list`
   - B) `cilium policy get`
   - C) `cilium-dbg endpoint get ENDPOINT_ID`
   - D) `cilium status --all-endpoints`

   <details>
   <summary>回答を表示</summary>

   **回答: C) `cilium-dbg endpoint get ENDPOINT_ID`**

   endpoint ID は、その agent の一覧からノードローカルの ID を取得してください。別の agent の ID が同じワークロードを指すとは限りません。

   </details>

24. **map manager が認識しているオープン BPF map を一覧表示する、agent ローカルのコマンドはどれですか？**

   - A) `cilium-dbg map list`
   - B) `cilium bpf maps`
   - C) `cilium status --maps`
   - D) `cilium bpf map list`

   <details>
   <summary>回答を表示</summary>

   **回答: A) `cilium-dbg map list`**

   これは map manager が把握している、開かれた BPF map の一覧であり、カーネル内のすべての BPF map の一覧ではありません。以前の回答にあった cilium bpf maps は有効なコマンドではありません。

   </details>

25. **Cilium BPF プログラムが出力するローカルイベントを表示するコマンドはどれですか？**

   - A) `cilium tcpdump`
   - B) `cilium capture`
   - C) `cilium-dbg monitor`
   - D) `cilium packet-capture`

   <details>
   <summary>回答を表示</summary>

   **回答: C) `cilium-dbg monitor`**

   このコマンドはサポート対象のイベント／trace 種別を表示します。集約、抑制、バッファーによって可視性が変わるため、すべてのパケットを必ず捕捉するものではありません。

   </details>

# 運用クイズ

> **関連ドキュメント**: [運用](../../../networking/calico/09-operations.md)
> **最終更新**: 2026年9月12日

## クイズ

1. Calico のインストール管理について、正しい説明はどれですか？
   - A) 冗長化のため、インストール用 manifest と Helm operator を併用する
   - B) プラットフォームに合った operator/Helm または直接 manifest を管理する主体を 1 つ選ぶ
   - C) すべてのインストールで BPF を有効にする必要がある
   - D) operator の新しい manifest には、すべての Calico CRD が自動的に含まれる

<details>
<summary>回答を表示</summary>

**回答: B) プラットフォームに合った operator/Helm または直接 manifest を管理する主体を 1 つ選ぶ**

Helm chart は Tigera Operator をインストールします。管理主体は 1 つにし、バージョンを固定し、対応する CRD を管理したうえで、実際のネットワークプロファイルを選択してください。この例は、自己管理 Linux 上の完全な Calico CNI を対象とします。EKS VPC CNI のポリシー専用構成とは異なります。

</details>

2. `calicoctl node status` が調べるのは何ですか？
   - A) kubeconfig context 内のすべてのノード
   - B) 必要なノードアクセスを用いた、ローカルノードの BGP 状態
   - C) すべてのアプリケーションの HTTP readiness
   - D) すべての IPAM 割り当て漏れ

<details>
<summary>回答を表示</summary>

**回答: B) 必要なノードアクセスを用いた、ローカルノードの BGP 状態**

これはローカルノードの BGP 診断であり、クラスター全体の readiness probe ではありません。BGP を使わないプロファイルでは、BGP の成功結果は必要ありません。影響を受けたノードを選び、必要に応じて実際の BIRD socket を調べてください。

</details>

3. `calicoctl ipam show --show-blocks` で何を確認できますか？
   - A) Calico IPAM の block 使用状況。ノードとの紐付けは別途調べる
   - B) 空の block を自動的に安全に解放する
   - C) すべての VPC CNI ENI 割り当て
   - D) トランザクション整合性のある datastore backup

<details>
<summary>回答を表示</summary>

**回答: A) Calico IPAM の block 使用状況。ノードとの紐付けは別途調べる**

このコマンドは IP block と pool の使用状況を報告します。block とノードの対応関係は BlockAffinity で確認してください。対象は Calico IPAM です。VPC CNI や host-local を使う場合は、実際のアドレス割り当て機構を調べます。

</details>

4. 確認対象のリリースにおける `felix_int_dataplane_apply_time_seconds` の型は何ですか？
   - A) 拒否したパケット数を示す Counter
   - B) 必須の _bucket series を持つ Histogram
   - C) quantile、_sum、_count を持つ Summary
   - D) 割り当て済み IP block 数を示す Gauge

<details>
<summary>回答を表示</summary>

**回答: C) quantile、_sum、_count を持つ Summary**

これは dataplane 適用時間の増分を観測する Summary です。ローカルの quantile はクラスター全体の p99 ではありません。観測値がある場合は sum/count の rate から平均を算出し、存在しない histogram bucket を仮定してはいけません。

</details>

5. Typha の metrics port について、正しい説明はどれですか？
   - A) バイナリのデフォルトは 9091。ガイドでは Operator の Typha metrics を 9093 に明示設定する
   - B) すべての Typha インストールで 9093 が自動的に使われる
   - C) Typha は常に kube-controllers の port 9094 を共有する
   - D) Service を作成するだけで metrics が有効になる

<details>
<summary>回答を表示</summary>

**回答: A) バイナリのデフォルトは 9091。ガイドでは Operator の Typha metrics を 9093 に明示設定する**

Typha metrics はデフォルトでは無効です。Operator の typhaMetricsPort で metrics の公開と Service を有効化・設定します。ServiceMonitor は対応する Service port を選び、Prometheus にも選択される必要があります。

</details>

6. Pod に IP アドレスが割り当てられないとき、何を確認すべきですか？
   - A) 直ちにアドレスを解放して、すべての Calico agent を再起動する
   - B) スケジューリングと event、選択されたノード、実際の CNI/IPAM 割り当て元
   - C) DNS レコードだけ
   - D) すべての BGP session の ASN が同じかどうか

<details>
<summary>回答を表示</summary>

**回答: B) スケジューリングと event、選択されたノード、実際の CNI/IPAM 割り当て元**

Pending の Pod は、まだスケジュールされていない可能性があります。割り当てに失敗した場合は、kubelet/CNI と IPAM の証拠、対象となる pool、容量と affinity の制約を調べてください。すべての Pod IP 割り当てエラーの原因が Felix process log にあるわけではありません。

</details>

7. BGP のトラブルシューティングでは何を確認すべきですか？
   - A) ping が成功することだけ
   - B) 影響を受けたノードの session 状態、送信元/peer address と ASN、TCP 179、認証/TTL、filter
   - C) session が開くまで ASN を無作為に変更する
   - D) 対象ノードに関係なく、クラスター内で最初の Calico Pod を調べる

<details>
<summary>回答を表示</summary>

**回答: B) 影響を受けたノードの session 状態、送信元/peer address と ASN、TCP 179、認証/TTL、filter**

TCP 接続が確立しても、BGP が Established 状態であることや prefix が受理されていることの証明にはなりません。想定される route と、正しい IPv4/IPv6 の BIRD socket を確認してください。選択したネットワークプロファイルで BGP が有効な場合にのみ、これらの確認を行います。

</details>

8. ポリシーがあるように見えるのに通信が拒否されない場合、正しい調査方法はどれですか？
   - A) kube-proxy や Service 変換は調査に影響しない
   - B) Pod annotation に有効なポリシー判定がすべて表示される
   - C) Felix Debug log はパケットごとの拒否を自動的に記録する
   - D) endpoint identity、selector、方向、tier/order、既存 flow、実際の Service/dataplane 経路を確認する

<details>
<summary>回答を表示</summary>

**回答: D) endpoint identity、selector、方向、tier/order、既存 flow、実際の Service/dataplane 経路を確認する**

Calico はポリシーを適用しますが、Service 変換、endpoint の選択、送信元アドレスの変更によって評価対象の通信が変わることがあります。特定のコンポーネントは無関係だと決めつけず、経路全体を調べ、許可されるケースと拒否されるケースを両方テストしてください。

</details>

9. Calico のアップグレードに必要な対応はどれですか？
   - A) 管理対象 DaemonSet を変更し、すべての canary agent を削除する
   - B) インストール方法とバージョンに対応する CRD、operator、保存データの移行手順に従う
   - C) 必ず開始前に Installation.spec.version を設定する
   - D) Helm rollback ですべての CRD とデータの変更が戻ると想定する

<details>
<summary>回答を表示</summary>

**回答: B) インストール方法とバージョンに対応する CRD、operator、保存データの移行手順に従う**

互換性のある移行元/移行先バージョンを使い、現在のインストール管理主体を更新します。新しいフィールドが必要になる前に CRD も管理してください。ロールアウトと復旧をテストします。古い operator や未加工の YAML export が、確実なダウングレード手段になるとは限りません。

</details>

10. default-deny ポリシーはどのように導入すべきですか？
    - A) 対象 namespace を選び、必要な依存先を明示的に許可してから適用範囲を広げる
    - B) すべての endpoint に適用する空の GlobalNetworkPolicy を直ちに適用する
    - C) 作り上げた Pod label から API server の endpoint を推測する
    - D) endpoint 数が 0 なら拒否が機能している証拠とみなす

<details>
<summary>回答を表示</summary>

**回答: A) 対象 namespace を選び、必要な依存先を明示的に許可してから適用範囲を広げる**

DNS、API、identity、監視、アプリケーションの各経路を明示的に確認します。拒否と許可の両方をテストし、復旧手段を確保して、ワークロード endpoint と host endpoint のポリシーを考慮してください。

</details>

11. 現在の OSS flow observability について、正しい説明はどれですか？
    - A) FlowLogsFileReporter は必須の OSS API field である
    - B) すべての flow log は常に 1 パケットにつき 1 record である
    - C) Operator/Helm で Goldmane と Whisker を導入でき、現行の flow-log ガイドではこの機能は tech preview とされている
    - D) flow log と Felix process log は同じものである

<details>
<summary>回答を表示</summary>

**回答: C) Operator/Helm で Goldmane と Whisker を導入でき、現行の flow-log ガイドではこの機能は tech preview とされている**

Goldmane は集約した flow data を Whisker に提供します。文書に記載された導入前提を満たせば OSS でも利用できます。古い file/DNS logger field は代替手段になりません。機微な flow data を保護し、tech preview である点を考慮してください。

</details>

12. calicoctl が Kubernetes datastore にアクセスするには、どの設定を使えますか？
    - A) CNI_PATH だけを設定する
    - B) DATASTORE_TYPE=kubernetes と適切な kubeconfig access を使うか、サポート対象の設定ファイルを明示する
    - C) 任意の ~/.config path が常に自動検出される
    - D) Calico 用 kubeconfig から EKS 管理の etcd にアクセスできる

<details>
<summary>回答を表示</summary>

**回答: B) DATASTORE_TYPE=kubernetes と適切な kubeconfig access を使うか、サポート対象の設定ファイルを明示する**

ガイドには一般的な環境変数の設定例があります。サポートされる別の方法として、--config file を明示することもできます。対象クラスターと RBAC を選んでください。etcdv3 への直接アクセスは別のデプロイ構成です。

</details>

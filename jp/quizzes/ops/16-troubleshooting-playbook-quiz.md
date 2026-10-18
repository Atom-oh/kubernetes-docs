# トラブルシューティング手順書クイズ

> **関連ドキュメント**: [Kubernetes／EKS トラブルシューティング手順書](../../ops/16-troubleshooting-playbook.md)

## 選択問題

### 1. `FailedScheduling` に CPU 不足が 1 件、メモリ不足が 1 件、affinity 不一致が 6 件、taint の不一致が 8 件と表示されています。正しい解釈はどれですか？

- A) 理由ごとの件数は重複する場合があるため、個々のノードの状態を比較する
- B) CPU とメモリの両方が不足しているノードは、同じ 1 台でなければならない
- C) 15 台すべてで CPU が不足している
- D) scheduler はノードを評価していない

<details>
<summary>解答を表示</summary>

**解答: A) 理由ごとの件数は重複する場合があるため、個々のノードの状態を比較する**

scheduler はノードごとに複数の理由を集約することがあります。件数だけでは、ノードを互いに重複しない集合に分けたり、特定のノードを特定したりできません。スケジューリング失敗と、イメージ取得／CNI 初期化の待機を区別するには、`nodeName` と `PodScheduled` を確認してください。

</details>

### 2. 通常の EC2 ワーカーで ECR イメージの pull が 401 Unauthorized で失敗します。最初に確認すべきことは何ですか？

- A) Docker Hub の rate limit
- B) kubelet のイメージ認証情報経路と、ノードロールの ECR 権限
- C) コンテナの liveness probe のパス
- D) アプリケーションの S3 バケット名

<details>
<summary>解答を表示</summary>

**解答: B) kubelet のイメージ認証情報経路と、ノードロールの ECR 権限**

アプリケーションの IRSA と、イメージ pull に使う ID を混同しないでください。Fargate では Pod 実行ロールを使います。`crictl pull` は kubelet の credential provider や `imagePullSecrets` を自動的に再利用しないため、同等の認証テストにはなりません。

</details>

### 3. コンテナの終了理由が `OOMKilled`、終了コードが 137 です。次に行うべきことは何ですか？

- A) 長時間動作していたことからメモリリークだと判断する
- B) コンテナの limit、ノードの pressure、メモリ時系列、カーネルイベントを調べる
- C) すぐに limit を必ず 2 倍にする
- D) 正常な SIGTERM 終了として無視する

<details>
<summary>解答を表示</summary>

**解答: B) コンテナの limit、ノードの pressure、メモリ時系列、カーネルイベントを調べる**

137 は一般に SIGKILL (128+9) を表し、`OOMKilled` は OOM の根拠を追加します。ただし、これだけでメモリリークや、コンテナの limit だけが原因だったと断定することはできません。終了理由が異なる 137 は別途調査が必要です。アプリケーションによっては SIGTERM の処理でも 143 以外の終了コードになることがあります。

</details>

### 4. EndpointSlice の ENDPOINTS 欄に IP アドレスが表示されます。何が分かりますか？

- A) すべての Pod が Ready である
- B) Service へのリクエストは必ず成功する
- C) アドレスが存在する。`ready`、`serving`、`terminating` は個別に確認する
- D) すべての NetworkPolicy が通信を許可している

<details>
<summary>解答を表示</summary>

**解答: C) アドレスが存在する。`ready`、`serving`、`terminating` は個別に確認する**

未 Ready の Pod でも `ready=false` として表示される場合があります。コンテナの READY 数も Pod の Ready condition とは異なります。アドレスがない場合は selector、namespace、管理状態を確認してください。selector のない Service では、EndpointSlice を手動管理する必要がある場合があります。

</details>

### 5. `DiskPressure=True` に対応する自動 taint はどれですか？

- A) node.kubernetes.io/unreachable
- B) node.kubernetes.io/not-ready
- C) node.kubernetes.io/disk-pressure
- D) node.kubernetes.io/memory-pressure

<details>
<summary>解答を表示</summary>

**解答: C) node.kubernetes.io/disk-pressure**

pressure により新規スケジューリングが妨げられても、ノードが Ready のままの場合があります。空き容量だけでなく inode 数とファイルシステム構成も確認してください。Ready=Unknown は unreachable、Ready=False は not-ready に関係します。

</details>

### 6. PVC が `WaitForFirstConsumer` の StorageClass を使っていて、まだ利用する Pod がありません。正しい解釈はどれですか？

- A) 必ず CSI の IAM エラーである
- B) `gp3` という名前の StorageClass は誤りである
- C) 正常な場合がある。利用者のスケジューリング制約に合わせて bind／provisioning が待機する
- D) すぐに PV を削除する

<details>
<summary>解答を表示</summary>

**解答: C) 正常な場合がある。利用者のスケジューリング制約に合わせて bind／provisioning が待機する**

動作を決めるのは StorageClass の名前ではなく `volumeBindingMode` です。API の既定値は `Immediate` なので、実際の値を確認してください。利用する Pod も Pending なら、`FailedScheduling` と topology 制約を確認します。PVC の削除は既定の診断手順ではありません。

</details>

### 7. Pod 作成後に ServiceAccount に IRSA アノテーションを追加しましたが、既存 Pod に注入されたフィールドがありません。次に何をしますか？

- A) クラスターを再作成する
- B) `serviceAccountName` と webhook 設定を確認し、影響を考慮したうえで Pod を再作成する
- C) ノードロールに AdministratorAccess を付与する
- D) ServiceAccount に関係なく既存環境が変わるまで待つ

<details>
<summary>解答を表示</summary>

**解答: B) `serviceAccountName` と webhook 設定を確認し、影響を考慮したうえで Pod を再作成する**

注入は Pod の作成時に行われ、既存 Pod は自動変更されません。再作成後に注入された内容と実際の呼び出し元を確認してください。別の SDK credential provider が優先される場合があります。また IMDS へのアクセスが遮断されている場合、ノードロールへの fallback は利用できません。

</details>

### 8. Karpenter が nodepool で利用可能なすべてのインスタンスタイプが limit を超えると報告しました。これは何を意味しますか？

- A) 現在の使用量が limit と等しい場合に限って発生する
- B) 候補インスタンスを追加すると NodePool の残り headroom を超える
- C) リージョンに EC2 インスタンスタイプが存在しない
- D) Pod に toleration がないに違いない

<details>
<summary>解答を表示</summary>

**解答: B) 候補インスタンスを追加すると NodePool の残り headroom を超える**

たとえば現在の CPU 使用量が 7、limit が 8、最小候補が 2 CPU なら、limit 到達前でもこのエラーが発生します。他のリソース limit、DaemonSet の overhead、要件も確認してください。`Nominated` イベントは、ノードや Pod の Ready を証明しません。

</details>

### 9. Secondary-IP モードで `WARM_IP_TARGET=3`、`MINIMUM_IP_TARGET=6`、使用中 IP が 1 つです。正しい解釈はどれですか？

- A) IP の合計は 4 個でなければならない
- B) 両方の target を満たすには、合計 6 個、予備 5 個が必要になる場合がある
- C) `MINIMUM_IP_TARGET` は予備 IP を少なくとも 6 個確保するという意味である
- D) Pod 数超過はサブネット枯渇を証明する

<details>
<summary>解答を表示</summary>

**解答: B) 両方の target を満たすには、合計 6 個、予備 5 個が必要になる場合がある**

warm target は予備アドレス数を示し、minimum は使用中と予備を合わせた合計数の下限です。実際の数には IPAM の調整、ENI 上限、prefix 割り当ての粒度が影響します。正の IP target は `WARM_ENI_TARGET` より優先されます。Prefix モードには対応インスタンスと連続した /28 ブロックが必要です。max-pods の上限と実際の IP 枯渇は分けて診断してください。

</details>

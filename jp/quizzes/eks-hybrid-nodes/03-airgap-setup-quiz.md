# EKS Hybrid Nodes 制限付きインターネット環境のセットアップクイズ

> **関連ドキュメント**: [制限付きインターネット環境のセットアップ](../../eks-hybrid-nodes/03-airgap-setup.md)
> **最終更新日**: 2026年9月12日

### 1. EKS Hybrid Nodes の接続性について正しい説明はどれですか?

A. イメージを物理的に転送すれば AWS への接続は不要になる

B. ノードには引き続き EKS コントロールプレーンと認証情報サービスへの接続が必要である

C. プライベート S3 バケットが EKS コントロールプレーンをホストする

D. VPN 接続は物理的な隔離と同じである

<details>
<summary>答えを表示</summary>

**答え: B. ノードには引き続き EKS コントロールプレーンと認証情報サービスへの接続が必要である**

パブリックインターネットへのアクセスを制限しながら、AWS へのプライベート接続を使うことはできます。一方、物理的に切断されたネットワークでは、Hybrid Nodes に必要な稼働中のコントロールプレーンや認証情報サービスへの経路を提供できません。

</details>

### 2. `hybrid-assets.eks.amazonaws.com` から S3 への PHZ alias だけでは不十分なのはなぜですか?

A. S3 はプライベート DNS に対応していない

B. DNS より先に ECR をインストールする必要がある

C. DNS は元の TLS hostname、オブジェクトのルーティング、認可を提供しない

D. すべての HTTPS request は自動的に IAM role を使う

<details>
<summary>答えを表示</summary>

**答え: C. DNS は元の TLS hostname、オブジェクトのルーティング、認可を提供しない**

S3 interface endpoint は private DNS に対応しています。ただし、alias を設定しても TLS SNI、HTTP Host header、オブジェクトの path、認証方式は書き換わりません。承認済みのイメージ準備手順、または実際の URL を指定したカスタム manifest を使ってください。証明書検証を無効にしてはいけません。

</details>

### 3. nodeadm v1.0.20 の private installation mode は何をしますか?

A. すべての OS 依存パッケージをローカル manifest からインストールする

B. OS package のインストールは省略するが、認証情報と EKS の artifact は引き続きインストールする

C. すべての AWS API 呼び出しを任意にする

D. すべての S3 artifact download に自動署名する

<details>
<summary>答えを表示</summary>

**答え: B. OS package のインストールは省略するが、認証情報と EKS の artifact は引き続きインストールする**

リリース済みのソースでは、`--private-mode` とともに `--manifest-override` を指定する必要があります。実行環境と OS の依存関係は別途準備してください。SSM の installer と署名の取得元も別に組み立てられます。また、manifest に `file://` を指定しても、artifact まで `file://` で取得できるとは限りません。

</details>

### 4. checksum がない、または一致しない場合、artifact 準備スクリプトはどうするべきですか?

A. 警告を出し、残りのファイルを公開する

B. 1 つ以上のファイルが検証に通れば処理を受け入れる

C. ダウンロードしたファイルから新しい期待 checksum を生成する

D. 処理を停止し、検証に失敗した候補を調査用に保持する

<details>
<summary>答えを表示</summary>

**答え: D. 処理を停止し、検証に失敗した候補を調査用に保持する**

必要な各ファイルは、信頼できるレビュー済み checksum 記録と一致しなければなりません。期待値を新たに生成すると、その検査の意味がなくなります。hash が一致しても、公開元を独立して認証したことにはなりません。

</details>

### 5. IAM Roles Anywhere の更新サービスを使う範囲はどれですか?

A. SSM を含むすべてのインストールで使われる

B. `enableCredentialsFile` を有効にした場合に使われ、通常の credential-process 利用は別の経路である

C. このサービスは存在しないため、常に削除するべきである

D. 証明書の更新が不要になる

<details>
<summary>答えを表示</summary>

**答え: B. `enableCredentialsFile` を有効にした場合に使われ、通常の credential-process 利用は別の経路である**

`aws_signing_helper_update.service` は credentials-file mode で実際に使われます。適切な service と、それを呼び出すプロセスの環境を設定してください。nodeadm による proxy の検出や `--with-proxy` の動作も含めて確認が必要です。証明書のライフサイクル管理と AWS への接続も引き続き必要です。

</details>

### 6. Hybrid Nodes の配布用 inventory に含めるイメージはどれですか?

A. すべてのノードで固定の VPC CNI イメージ一覧

B. CNI イメージである kubelet だけ

C. 実際にサポートされている CNI、DNS、datapath、sandbox、ワークロード用イメージ。init container と各 platform のイメージも含む

D. Kubernetes の patch version の末尾に `-eksbuild.1` を付けて作った任意の tag

<details>
<summary>答えを表示</summary>

**答え: C. 実際にサポートされている CNI、DNS、datapath、sandbox、ワークロード用イメージ。init container と各 platform のイメージも含む**

VPC CNI は Hybrid Nodes の CNI ではありません。実際にデプロイされている manifest と承認済み digest を使ってください。Private ECR から pull する場合は、S3 の layer 取得経路とワークロードの image-pull 認証情報も必要です。repository の一覧だけでは十分ではありません。

</details>

### 7. bootstrap 前に nodeadm の設定を検証する正しい方法はどれですか?

A. `nodeadm init --dry-run`

B. `nodeadm config check --config-source file:///etc/eks/nodeconfig.yaml`

C. `curl -k` を実行し、準備完了と報告する

D. 設定ファイルがない場合は処理を飛ばして成功を返す

<details>
<summary>答えを表示</summary>

**答え: B. `nodeadm config check --config-source file:///etc/eks/nodeconfig.yaml`**

内容を設定済みで、アクセスを保護したファイルを使ってください。`config check` が検証するのは設定内容です。プライベートネットワークで動作できることや、ノード登録までを証明するものではありません。確認した `init` command には `--dry-run` flag はありません。

</details>

### 8. 既存の kube-proxy DaemonSet をできるだけ保つ proxy 変更はどれですか?

A. JSON Patch で `/containers/0/env` を新しい配列に置き換える

B. proxy に不要なので `NODE_NAME` を削除する

C. container/env の name に基づくレビュー済み strategic merge を使い、既存の引数と `NODE_NAME` を維持する

D. 常に `.eks.amazonaws.com` を proxy 対象外にする

<details>
<summary>答えを表示</summary>

**答え: C. container/env の name に基づくレビュー済み strategic merge を使い、既存の引数と `NODE_NAME` を維持する**

既存の env member を対象とする JSON Patch の add は、配列全体を置き換えることがあります。patch の対象を kube-proxy に限定し、ほかの値も保持してください。`.eks.amazonaws.com` を広く除外すると、パブリックな `hybrid-assets` download host も除外対象になります。

</details>

### 9. 転送した OCI image archive を使う前に必要な確認はどれですか?

A. tar の import が成功したことだけを確認する

B. 承認済み hash、digest/platform の内容、転送先の参照、および実際の runtime pull 動作を検証する

C. 証明書エラーを避けるため、転送元 registry の TLS を無効にする

D. image の builder と同じ architecture だけで十分だと仮定する

<details>
<summary>答えを表示</summary>

**答え: B. 承認済み hash、digest/platform の内容、転送先の参照、および実際の runtime pull 動作を検証する**

Skopeo の `--all` は platform 一覧を保持し、`--preserve-digests` は digest を維持できない場合に失敗します。import 時の名前、containerd の `k8s.io` namespace、`imagePullPolicy`、garbage collection も、実際の Pod が起動できるかどうかに影響します。

</details>

### 10. プライベート artifact repository の適切な更新方法はどれですか?

A. production の `latest` key を毎週自動的に上書きする

B. `head-object` の AccessDenied をオブジェクトがないものとして扱う

C. provenance、互換性、代表的なノードでの検証後に、新しい immutable candidate を承認する

D. すべての環境で帯域幅を 50～80% 削減できると約束する

<details>
<summary>答えを表示</summary>

**答え: C. provenance、互換性、代表的なノードでの検証後に、新しい immutable candidate を承認する**

所有者を明示した bucket を使い、publisher と reader の権限を分け、未知のエラーが発生したら停止してください。条件付きの object write でも、アップロード全体が atomic になるわけではありません。以前に示された帯域幅削減率は、検証されていない過去の例示であり、測定結果や保証値ではありません。

</details>

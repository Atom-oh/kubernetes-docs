# EKS ワークロード IAM 移行クイズ

> **最終更新日**: 2026年11月21日

[ワークブックとライブデモを読む](../../security/17-eks-workload-identity-migration.md)

### 1. アプリの S3 権限をノードの IAM ロールに付与する場合の主な問題は何ですか？

- A) S3 リクエストが遅くなる
- B) そのノード上で IMDS にアクセスできるすべての Pod が同じ権限を使う
- C) ノードがクラスターに参加できなくなる
- D) S3 バケットがパブリックになる

<details>
<summary>回答を表示</summary>

**回答: B) そのノード上で IMDS にアクセスできるすべての Pod が同じ権限を使う**

**解説:** ノードロールはインスタンスプロファイルを通じてノード全体に付与されます。ホップ制限が 2 以上の場合、通常の Pod は IMDSv2 経由でノードロールの認証情報を取得できます。CloudTrail に記録されるのはノードインスタンスのセッションだけなので、ワークロードを見分けるのは困難です。

</details>

### 2. AWS SDK のデフォルト認証情報チェーンでは、IRSA と Pod Identity のプロバイダーは IMDS に対してどの位置にありますか？

- A) IMDS が最初
- B) IRSA（ウェブ ID）と Pod Identity（コンテナプロバイダー）はどちらも IMDS より前
- C) 順序はランダム
- D) Pod Identity だけが IMDS より前

<details>
<summary>回答を表示</summary>

**回答: B) IRSA（ウェブ ID）と Pod Identity（コンテナプロバイダー）はどちらも IMDS より前**

**解説:** 環境変数のキー、ウェブ ID トークン、コンテナ認証情報プロバイダーは IMDS より先に評価されます。EKS が変数を注入した新しい Pod は、コードを変更せずに新しいロールを使用します。何も注入されていない Pod は、IMDS からノードロールの認証情報を取得します。

</details>

### 3. IRSA では、STS が投影されたトークンを信頼できるのはなぜですか？

- A) トークンに IAM アクセスキーが含まれている
- B) クラスターの発行者が IAM OIDC プロバイダーとして登録されており、ロールの信頼ポリシーが `aud` と `sub` を検証する
- C) Pod Identity Agent がトークンに署名する
- D) ノードロールが Pod の代わりに STS を呼び出す

<details>
<summary>回答を表示</summary>

**回答: B) クラスターの発行者が IAM OIDC プロバイダーとして登録されており、ロールの信頼ポリシーが `aud` と `sub` を検証する**

**解説:** STS の `AssumeRoleWithWebIdentity` は、OIDC プロバイダーを通じて登録された発行者のキーでトークンの署名を検証し、信頼条件を確認します。`aud` は `sts.amazonaws.com`、`sub` は `system:serviceaccount:<namespace>:<serviceaccount>` です。

</details>

### 4. Pod Identity を使う場合、ノードロールに残す必要がある権限はどれですか？

- A) アプリの S3 読み取り権限
- B) `sts:AssumeRoleWithWebIdentity`
- C) エージェントが EKS Auth を呼び出すための `eks-auth:AssumeRoleForPodIdentity`（`AmazonEKSWorkerNodePolicy` の一部）
- D) 何も必要ない

<details>
<summary>回答を表示</summary>

**回答: C) エージェントが EKS Auth を呼び出すための `eks-auth:AssumeRoleForPodIdentity`（`AmazonEKSWorkerNodePolicy` の一部）**

**解説:** Pod Identity Agent は、このノードロール権限を使って EKS Auth を呼び出します。アプリの業務上必要な権限は、関連付けで指定した Pod Identity ロールに付与します。

</details>

### 5. デモの `diff` では、どのクレームによって IRSA トークンと Pod Identity トークンを区別できましたか？

- A) `iss`
- B) `aud`
- C) `exp`
- D) 同一だった

<details>
<summary>回答を表示</summary>

**回答: B) `aud`**

**解説:** どちらも同じクラスター発行者が署名した ServiceAccount トークンです。IRSA トークンの audience は `sts.amazonaws.com`、Pod Identity トークンの audience は `pods.eks.amazonaws.com` です。`sub` は ServiceAccount ごとに異なります。

</details>

### 6. 信頼ポリシーを変更せずに、新しい 10 個のクラスターで 1 つの IAM ロールを使える方法はどれですか？

- A) IRSA
- B) EKS Pod Identity
- C) どちらも変更不要
- D) どちらもクラスターごとの編集が必要

<details>
<summary>回答を表示</summary>

**回答: B) EKS Pod Identity**

**解説:** Pod Identity ロールが信頼するのは `pods.eks.amazonaws.com` のみです。クラスターのスコープは関連付けとセッションタグで設定します。IRSA ではクラスターごとに OIDC プロバイダーと信頼ステートメントが必要で、デフォルトの 2,048 文字の信頼ポリシーには通常、約 4 つの関連付けしか収まりません。

</details>

### 7. Fargate 上で実行される Pod にワークロードロールが必要です。どの方法を使いますか？

- A) EKS Pod Identity
- B) IRSA
- C) ノードロール
- D) どちらも使えない

<details>
<summary>回答を表示</summary>

**回答: B) IRSA**

**解説:** EKS Pod Identity がサポートするのは、EKS の Linux EC2 ノードと EKS Hybrid Nodes（エージェントのハイブリッド DaemonSet およびノード認証情報ファイルを使用）です。Fargate、Windows EC2 ノード、Outposts、EKS Anywhere では IRSA を使います。

</details>

### 8. 関連付けを作成してすぐにロールアウトしたところ、新しい Pod がまだノードロールを使っています。最も考えられる原因は何ですか？

- A) バケットポリシーによって拒否された
- B) 関連付けがまだ Pod のアドミッション処理に反映されておらず、何も注入されなかった
- C) Pod Identity Agent が IMDS をブロックした
- D) IRSA アノテーションも必要

<details>
<summary>回答を表示</summary>

**回答: B) 関連付けがまだ Pod のアドミッション処理に反映されておらず、何も注入されなかった**

**解説:** 関連付けの反映には時間がかかり、数秒かかる場合があります。デモの最初のリハーサルでは、作成直後にロールアウトした結果、何も注入されませんでした。2 回目のリハーサルでは、注入が反映されるまでに 5 秒かかりました。ロールアウトの前に `kubectl create --dry-run=server` を使って Pod テンプレートを確認してください。

</details>

### 9. すでに IRSA アノテーションが付いた ServiceAccount に Pod Identity の関連付けを追加し、新しい Pod を作成しました。この Pod はどの認証情報を使いますか？

- A) Pod Identity: webhook は Pod Identity の変数だけを注入する
- B) IRSA: ウェブ ID プロバイダーがチェーンの先にある
- C) リクエストごとに交互に使う
- D) 競合によって Pod の起動に失敗する

<details>
<summary>回答を表示</summary>

**回答: A) Pod Identity: webhook は Pod Identity の変数だけを注入する**

**解説:** 関連付けがある場合、EKS webhook は新しい Pod に `AWS_CONTAINER_CREDENTIALS_FULL_URI` と `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE` だけを注入し、IRSA の変数は注入しません。これはデモクラスターでの dry-run で確認されました。認証情報チェーンの順序 (B) が関係するのは、両方の変数セットが存在する場合だけです。関連付けの作成前に作成された Pod は、再作成されるまで IRSA を使い続けます。

</details>

### 10. ノードロールの S3 ポリシーを削除した直後、レガシー Pod の読み取りが拒否されました。移行が完了したと判断できますか？

- A) はい、拒否が 1 回あれば確定
- B) いいえ、IAM の変更は最終的に反映されるため、結果が数分間混在することがあります。引き続き監視してください
- C) はい、ノードが再起動した時点で完了
- D) いいえ、ノードロールを削除する必要がある

<details>
<summary>回答を表示</summary>

**回答: B) いいえ、IAM の変更は最終的に反映されるため、結果が数分間混在することがあります。引き続き監視してください**

**解説:** デモでは、レガシー Pod のアクセスは 13 秒後に拒否されましたが、その約 4.5 分後に許可された読み取りがさらに 2 回発生しました。スケジュール実行も含めて数分間監視し、ロールバック用にポリシーの正確なコピーを保管してください。

</details>

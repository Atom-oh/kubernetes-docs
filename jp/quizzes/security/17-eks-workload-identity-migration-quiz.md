# EKS ワークロード IAM 移行クイズ

> **最終更新日**: 2026年11月21日

[ワークブックとライブデモを読む](../../security/17-eks-workload-identity-migration.md)

### 1. アプリの S3 権限をノードの IAM ロールに付与することの主な問題は何ですか？

- A) S3 リクエストが遅くなる
- B) そのノード上で IMDS にアクセスできるすべての Pod が同じ権限を使う
- C) ノードがクラスターに参加できなくなる
- D) S3 バケットが公開状態になる

<details>
<summary>回答を表示</summary>

**回答: B) そのノード上で IMDS にアクセスできるすべての Pod が同じ権限を使う**

**解説:** ノードロールはインスタンスプロファイルを通じてノード全体に付与されます。ホップ制限が 2 以上の場合、通常の Pod は IMDSv2 経由でノードロールの認証情報を取得できます。CloudTrail に記録されるのはノードインスタンスのセッションのみなので、ワークロードを区別するのは困難です。

</details>

### 2. AWS SDK のデフォルト認証情報チェーンでは、IRSA と Pod Identity のプロバイダーは IMDS に対してどの位置にありますか？

- A) IMDS が最初
- B) IRSA（ウェブ ID）と Pod Identity（コンテナプロバイダー）はどちらも IMDS より前
- C) 順序はランダム
- D) Pod Identity だけが IMDS より前

<details>
<summary>回答を表示</summary>

**回答: B) IRSA（ウェブ ID）と Pod Identity（コンテナプロバイダー）はどちらも IMDS より前**

**解説:** 環境変数のキー、ウェブ ID トークン、コンテナ認証情報プロバイダーは IMDS より優先されます。EKS が変数を注入した新しい Pod は、コードを変更せずに新しいロールを使用します。何も注入されていない Pod はフォールバックして、IMDS からノードロールを取得します。

</details>

### 3. IRSA では、STS が投影されたトークンを信頼できるのはなぜですか？

- A) トークンに IAM アクセスキーが含まれている
- B) クラスターの発行者が IAM OIDC プロバイダーとして登録され、ロールの信頼ポリシーが `aud` と `sub` を確認する
- C) Pod Identity Agent がトークンに署名する
- D) ノードロールが Pod に代わって STS を呼び出す

<details>
<summary>回答を表示</summary>

**回答: B) クラスターの発行者が IAM OIDC プロバイダーとして登録され、ロールの信頼ポリシーが `aud` と `sub` を確認する**

**解説:** STS の `AssumeRoleWithWebIdentity` は、OIDC プロバイダーを通じて登録された発行者の鍵でトークンの署名を検証し、信頼条件を確認します。`aud` は `sts.amazonaws.com`、`sub` は `system:serviceaccount:<namespace>:<serviceaccount>` です。

</details>

### 4. Pod Identity では、どの権限をノードロールに残す必要がありますか？

- A) アプリの S3 読み取り権限
- B) `sts:AssumeRoleWithWebIdentity`
- C) エージェントが EKS Auth を呼び出すための `eks-auth:AssumeRoleForPodIdentity`（`AmazonEKSWorkerNodePolicy` の一部）
- D) 権限は一切不要

<details>
<summary>回答を表示</summary>

**回答: C) エージェントが EKS Auth を呼び出すための `eks-auth:AssumeRoleForPodIdentity`（`AmazonEKSWorkerNodePolicy` の一部）**

**解説:** Pod Identity Agent は、このノードロール権限を使って EKS Auth を呼び出します。アプリの業務権限は、関連付けで指定された Pod Identity ロールに付与します。

</details>

### 5. デモの `diff` では、IRSA トークンと Pod Identity トークンを区別するクレームはどれでしたか？

- A) `iss`
- B) `aud`
- C) `exp`
- D) どちらも同一だった

<details>
<summary>回答を表示</summary>

**回答: B) `aud`**

**解説:** どちらも同じクラスター発行者が署名した ServiceAccount トークンです。IRSA トークンのオーディエンスは `sts.amazonaws.com`、Pod Identity トークンのオーディエンスは `pods.eks.amazonaws.com` です。`sub` は ServiceAccount ごとに異なります。

</details>

### 6. 信頼ポリシーを変更せずに、1 つの IAM ロールを新しい 10 個のクラスターで使える方法はどれですか？

- A) IRSA
- B) EKS Pod Identity
- C) どちらも変更不要
- D) どちらもクラスターごとに変更が必要

<details>
<summary>回答を表示</summary>

**回答: B) EKS Pod Identity**

**解説:** Pod Identity ロールは `pods.eks.amazonaws.com` だけを信頼し、関連付けとセッションタグでクラスターのスコープを設定します。IRSA ではクラスターごとに OIDC プロバイダーと信頼ステートメントが必要で、デフォルトの 2,048 文字の信頼ポリシーには通常、約 4 つのバインディングしか収まりません。

</details>

### 7. Fargate で実行されている Pod にワークロード用ロールが必要です。どの方法を使いますか？

- A) EKS Pod Identity
- B) IRSA
- C) ノードロール
- D) どちらも使えない

<details>
<summary>回答を表示</summary>

**回答: B) IRSA**

**解説:** EKS Pod Identity がサポートするのは、EKS の Linux EC2 ノードのみです。Fargate、Windows EC2 ノード、Outposts、EKS Anywhere では IRSA を使います。

</details>

### 8. 関連付けを作成してすぐにロールアウトしたところ、新しい Pod がまだノードロールを使っています。最も可能性の高い原因は何ですか？

- A) バケットポリシーによって拒否された
- B) 関連付けがまだ Pod のアドミッションに反映されておらず、何も注入されなかった
- C) Pod Identity Agent が IMDS をブロックした
- D) IRSA アノテーションも必要

<details>
<summary>回答を表示</summary>

**回答: B) 関連付けがまだ Pod のアドミッションに反映されておらず、何も注入されなかった**

**解説:** 関連付けの整合性は最終的に確保されるもので、反映には数秒かかることがあります。デモの最初のリハーサルでは、作成直後にロールアウトしたため何も注入されませんでした。2 回目は、注入が現れるまで 5 秒かかりました。ロールアウトする前に、`kubectl create --dry-run=server` で Pod テンプレートを確認してください。

</details>

### 9. IRSA アノテーションがすでに設定されている ServiceAccount に Pod Identity の関連付けを追加し、新しい Pod を作成しました。この新しい Pod はどの認証情報を使いますか？

- A) Pod Identity: webhook が Pod Identity の変数だけを注入する
- B) IRSA: ウェブ ID プロバイダーがチェーンで先にある
- C) リクエストごとに交互に使う
- D) 競合により Pod の起動に失敗する

<details>
<summary>回答を表示</summary>

**回答: A) Pod Identity: webhook が Pod Identity の変数だけを注入する**

**解説:** 関連付けがある場合、EKS webhook が新しい Pod に注入するのは `AWS_CONTAINER_CREDENTIALS_FULL_URI` と `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE` だけで、IRSA の変数は注入しません。これはデモクラスターでのドライランでも確認されました。チェーンの順序（B）が関係するのは両方の変数セットが存在する場合だけです。関連付けの作成前に作られた Pod は、再作成されるまで IRSA を使い続けます。

</details>

### 10. ノードロールの S3 ポリシーを削除した直後、レガシー Pod の読み取りが拒否されました。移行完了と判断できますか？

- A) はい、1 回拒否されれば確定
- B) いいえ、IAM の変更は最終的に整合され、結果が数分間混在する可能性があるので、引き続き監視する
- C) はい、ノードが再起動すればよい
- D) いいえ、ノードロールを削除する必要がある

<details>
<summary>回答を表示</summary>

**回答: B) いいえ、IAM の変更は最終的に整合され、結果が数分間混在する可能性があるので、引き続き監視する**

**解説:** デモでは、レガシー Pod のリクエストは 13 秒後に拒否されましたが、その約 4.5 分後に許可された読み取りがさらに 2 回ありました。スケジュール実行も含めて数分間監視し、ロールバックに備えてポリシーの正確なコピーを保管してください。

</details>

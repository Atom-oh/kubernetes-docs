# IRSA と OIDC プロバイダーのクイズ

> **最終更新日**: 2026年11月21日

このクイズでは、[IRSA と OIDC プロバイダー](../../eks/05-eks-security-irsa-oidc.md)についての理解度を確認します。

## クイズの概要
- クラスターの OIDC 発行者と IAM OIDC プロバイダー
- IRSA トークンの交換
- ロールの信頼条件
- Discovery/JWKS と鍵のローテーション

## 多肢選択式の問題

### 1. EKS クラスターは OIDC 発行者と公開署名鍵を公開しています。ワークロードがロールを引き受けるには、IRSA にほかに何が必要ですか？

- A) それ以上は何も必要ない。発行者のエンドポイントだけでロールの引き受けが許可される
- B) Kubernetes ユーザーのログイン用に関連付けられた外部 OIDC アイデンティティプロバイダー
- C) IAM OIDC プロバイダー、適切な信頼関係を持つロール、互換性のある SDK
- D) ワークロードが必要とする S3 アクセス許可をノードの IAM ロールに追加する

<details>
<summary>回答を表示</summary>

**回答: C) IAM OIDC プロバイダー、適切な信頼関係を持つロール、互換性のある SDK**

**解説:**

EKS が公開するクラスターの OIDC 発行者エンドポイントだけでは、IAM OIDC プロバイダーは作成されず、ロールの引き受けも許可されません。IRSA には、ロールを所有するアカウント内の適切な IAM OIDC プロバイダー、正しい発行者／サブジェクト／オーディエンス条件でそのプロバイダーを信頼するロール、そして互換性のある SDK が必要です。Kubernetes ユーザーのログイン用の外部 OIDC プロバイダーは、IRSA とは別のものです。

</details>

### 2. IRSA では、投影された Web アイデンティティトークンを一時的な AWS 認証情報に交換するために、SDK はどの API を呼び出しますか？

- A) EKS Auth AssumeRoleForPodIdentity
- B) STS AssumeRoleWithWebIdentity
- C) IMDSv2 インスタンスプロファイルの認証情報
- D) STS GetSessionToken

<details>
<summary>回答を表示</summary>

**回答: B) STS AssumeRoleWithWebIdentity**

**解説:**

IRSA webhook は、対象となる Pod に投影トークンとロール設定を追加し、SDK は AssumeRoleWithWebIdentity を使ってトークンを STS と交換します。STS は発行者、署名、トークン、ロールの信頼関係を検証し、一時的な認証情報を返します。AssumeRoleForPodIdentity は、Pod Identity エージェントが呼び出す EKS Auth API です。Kubernetes は投影トークンをローテーションし、SDK はそれとは異なる有効期間に従って AWS 認証情報を更新します。

</details>

### 3. IRSA の信頼関係を限定する例では、どの条件によってロールの引き受けを `security-demo/irsa-reader` ServiceAccount に限定していますか？

- A) `aws:RequestTag/kubernetes-service-account` セッションタグ条件
- B) `Principal.Service` を `pods.eks.amazonaws.com` に設定する
- C) IAM ロールの名前を ServiceAccount と完全に同じにする
- D) `<issuer>:sub` と `<issuer>:aud` に対する StringEquals 条件

<details>
<summary>回答を表示</summary>

**回答: D) `<issuer>:sub` と `<issuer>:aud` に対する StringEquals 条件**

**解説:**

IRSA ロールは IAM OIDC プロバイダーを `Federated` プリンシパルとして使用し、`sts:AssumeRoleWithWebIdentity` を許可します。完全な発行者ホスト名／パスをプレフィックスとする StringEquals 条件によって、ServiceAccount とオーディエンスを指定します。`:sub` は `system:serviceaccount:security-demo:irsa-reader`、`:aud` は `sts.amazonaws.com` です。`aws:RequestTag/...` 条件と `pods.eks.amazonaws.com` は Pod Identity の信頼関係で使われます。ロールは、明示的に許可した複数の ServiceAccount または発行者を信頼できます。IRSA では、ServiceAccount ごとにロールを 1 つだけ使用する必要はありません。

</details>

### 4. クラスターの OIDC discovery ドキュメントと JWKS を取得してトークンを検証するバリデーターを構築する場合、正しい説明はどれですか？

- A) Cache-Control に従って鍵をキャッシュし、鍵のローテーションと未知の `kid` 値に対応する
- B) JWKS を一度だけ取得し、バリデーターにハードコードして永久に再利用する
- C) JWKS の取得に成功したら、トークンの署名も検証済みとみなす
- D) discovery ドキュメントの発行者とクラスターの発行者の比較を省略する

<details>
<summary>回答を表示</summary>

**回答: A) Cache-Control に従って鍵をキャッシュし、鍵のローテーションと未知の `kid` 値に対応する**

**解説:**

ページに掲載されている診断スクリプトは、公開されている discovery/JWKS を取得し、discovery の発行者と HTTPS スキームを確認します。ワークロードトークンの署名も IAM アクセス許可も検証しません。自動バリデーターでは、Cache-Control に従って鍵をキャッシュし、レビュー済みの JWT ライブラリーを使って、署名鍵のローテーションと未知の `kid` 値に対応する必要があります。EKS は OIDC 署名鍵を 7 日ごとにローテーションします。

</details>

### 5. インターネットへのエグレスがないバリデーターは、どのようにしてクラスターの OIDC discovery ドキュメントと JWKS にアクセスできますか？

- A) EKS 管理 API のインターフェイスエンドポイントを作成する。これを使って OIDC にもアクセスできる
- B) 必要に応じて、セキュリティグループで一時的に 0.0.0.0/0 へのエグレスを許可する
- C) discovery と JWKS へのアクセスに `oidc-eks` PrivateLink インターフェイスエンドポイントを使う
- D) IRSA では JWKS が不要なので、ネットワーク経路を一切用意しない

<details>
<summary>回答を表示</summary>

**回答: C) discovery と JWKS へのアクセスに `oidc-eks` PrivateLink インターフェイスエンドポイントを使う**

**解説:**

現在の EKS では、インターネットへのエグレスがないバリデーター向けに、クラスターの OIDC discovery/JWKS 用 PrivateLink インターフェイスエンドポイント `com.amazonaws.region-code.oidc-eks` がサポートされています。このエンドポイントのリージョン／DNS の要件を確認してください。EKS 管理 API エンドポイントは別のサービスです。

</details>

# EKS Pod Identity クイズ

> **最終更新日**: 2026年11月21日

このクイズでは、[EKS Pod Identity](../../eks/05-eks-security-pod-identity.md) の理解度を確認します。

## クイズの概要
- アソシエーションの役割
- エージェントと認証情報のフロー
- ロールの信頼関係とセッションタグ
- クロスアカウントとキャッシュ
- IRSA との共存と IRSA からの移行

## 多肢選択式問題

### 1. EKS Pod Identity アソシエーションについて、正しい説明はどれですか？

- A) 作成すると、名前空間に ServiceAccount が自動的に作成される
- B) IAM ロールに加えて Kubernetes RBAC 権限も付与される
- C) ServiceAccount オブジェクト自体のアノテーションとして、Kubernetes に保存される
- D) EKS API で、クラスター、名前空間、ServiceAccount を IAM ロールに対応付ける

<details>
<summary>回答を表示</summary>

**回答: D) EKS API で、クラスター、名前空間、ServiceAccount を IAM ロールに対応付ける**

**解説:**

アソシエーションは、クラスター、名前空間、ServiceAccount を IAM ロールに対応付けるもので、EKS API に保存されます。ServiceAccount の作成、Kubernetes RBAC 権限の付与、IAM ロールやエージェントの作成は行いません。このページの例では、別の所有者の設定を上書きしないよう、作成前に `list-pod-identity-associations` で既存のアソシエーションを確認しています。

</details>

### 2. 新たに作成されたアソシエーション済み Pod 内の AWS SDK は、どのように Pod Identity 認証情報を取得しますか？

- A) SDK がノードエージェントを呼び出し、エージェントが EKS Auth から認証情報を取得する
- B) エージェントが Pod からのすべての AWS リクエストを透過的に横取りし、署名する
- C) SDK がウェブ ID トークンを使って STS AssumeRoleWithWebIdentity を呼び出す
- D) SDK が IMDSv2 から受け取ったノード IAM ロールの認証情報を使う

<details>
<summary>回答を表示</summary>

**回答: A) SDK がノードエージェントを呼び出し、エージェントが EKS Auth から認証情報を取得する**

**解説:**

アソシエーション済みの新しい Pod には、オーディエンスが `pods.eks.amazonaws.com` のトークン、トークンファイルを示す環境変数、コンテナ認証情報 URI が EKS によって注入されます。SDK はエージェントのエンドポイント（一般的には `169.254.170.23/v1/credentials`）を呼び出します。エージェントは EKS Auth の AssumeRoleForPodIdentity を呼び出し、取得した認証情報を SDK に返します。これはリクエストを横取りする仕組みではなく、アプリケーションは引き続き、自身の認証情報を使って AWS サービスを直接呼び出します。

</details>

### 3. Pod Identity のロール信頼ポリシーの例について、正しい説明はどれですか？

- A) 信頼ポリシーの `Federated` プリンシパルとして、クラスターの IAM OIDC プロバイダーを指定する
- B) Pod Identity では `sts:AssumeRoleWithWebIdentity` のみを許可すれば十分である
- C) タグで範囲を限定したうえで、`pods.eks.amazonaws.com` に AssumeRole/TagSession を許可する
- D) 条件なしで `pods.eks.amazonaws.com` を信頼するのが最小権限である

<details>
<summary>回答を表示</summary>

**回答: C) タグで範囲を限定したうえで、`pods.eks.amazonaws.com` に AssumeRole/TagSession を許可する**

**解説:**

この信頼ポリシーの例では、サービスプリンシパル `pods.eks.amazonaws.com` に対し、`aws:RequestTag/eks-cluster-arn`、`kubernetes-namespace`、`kubernetes-service-account` の条件を付けて、`sts:AssumeRole` と `sts:TagSession` を許可しています。これらの条件はデフォルトのセッションタグに依存するため、タグを無効にする場合は条件を見直す必要があります。アソシエーションを作成する呼び出し元には、対象のロールに対する `iam:PassRole` も必要です。

</details>

### 4. Pod Identity で別のアカウントのリソースにアクセスする場合、正しい説明はどれですか？

- A) アソシエーションのロールとして、別アカウントの任意のロールを直接アタッチする
- B) アソシエーションのロールはクラスターのアカウントに置き、対象ロールにロールチェーンする
- C) Pod Identity はクロスアカウントに対応していないため、対象のワークロードは必ず IRSA に切り替える
- D) 対象ロールを使う場合、アソシエーションを変更すると認証情報キャッシュが直ちにリセットされる

<details>
<summary>回答を表示</summary>

**回答: B) アソシエーションのロールはクラスターのアカウントに置き、対象ロールにロールチェーンする**

**解説:**

アソシエーションのロールは、EKS クラスターのアカウントに置く必要があります。オプションの対象 IAM ロールは別のアカウントに置くことができ、同一アカウント内のロールからその対象ロールへ、信頼設定と AssumeRole 権限を構成したうえで Pod Identity がロールチェーンします。現在のガイドでは、対象ロールを使わない場合の認証情報キャッシュの有効期間は 6 時間、使う場合は 59 分とされています。また、アソシエーションを変更してもキャッシュはリセットされません。Pod を再作成すれば、新しい設定をより早く取得できます。

</details>

### 5. 1 つの ServiceAccount に IRSA アノテーションと Pod Identity アソシエーションの両方がある場合、EKS はどのように認証情報を注入しますか？

- A) 新しい Pod には Pod Identity の環境変数のみが付与され、実行中の Pod には IRSA の環境変数が残る
- B) 新しい Pod には両方の環境変数が付与され、SDK はどちらかをランダムに選ぶ
- C) アソシエーションを作成すると、実行中の Pod の環境変数が直ちに書き換えられる
- D) 常に IRSA アノテーションが優先されるため、新しい Pod はアソシエーションを無視する

<details>
<summary>回答を表示</summary>

**回答: A) 新しい Pod には Pod Identity の環境変数のみが付与され、実行中の Pod には IRSA の環境変数が残る**

**解説:**

[IRSA と Pod Identity への EKS ノード IAM 権限の移行](../../security/17-eks-workload-identity-migration.md#irsa-and-pod-identity-compared)で確認されているように、両方の設定がある場合、EKS webhook は新しい Pod に `AWS_CONTAINER_CREDENTIALS_FULL_URI` と `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE` のみを注入します。実行中の Pod には、再作成するまで IRSA の環境変数が残るため、計画的にロールアウトして切り替え、使用しないアノテーションを削除してください。同じロールが表示される `get-caller-identity` の結果では、2 つの仕組みを区別できません。そのため、注入された環境変数名を確認してください。

</details>

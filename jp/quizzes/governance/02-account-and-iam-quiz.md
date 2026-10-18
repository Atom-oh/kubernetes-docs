# Account 構成と IAM 境界クイズ

> このクイズでは、[Account 構成と IAM 境界](../../governance/02-account-and-iam.md)の理解度を確認します。

---

1. Identity Center のグループ数上限100の適用範囲はどれですか？
   - A) Organization 内のすべてのグループ
   - B) 1つの Account 内のすべてのグループ
   - C) 1つの Account 内の1つの permission set、または1つのアプリケーションに割り当てられたグループ
   - D) 同時にサインインしているユーザー数

<details>
<summary>回答を表示</summary>

**回答: C) 1つの Account 内の1つの permission set、または1つのアプリケーションに割り当てられたグループ**

**解説:**
この上限は permission set と Account の組み合わせごとに適用され、複数の permission set にまたがる Account 全体の合計ではありません。また、ABAC を一律に必須とするものでもありません。

</details>

---

2. Shared VPC を使用している Account を分離する計画で重要なのは何ですか？
   - A) すべてのリソースが直ちに削除される
   - B) 共有解除後の同一 Organization 要件と作成/置換の制限を考慮して、移行を計画する
   - C) RAM サブネットは外部 Organization との共有を維持する
   - D) EKS が VPC を自動的に移動する

<details>
<summary>回答を表示</summary>

**回答: B) 共有解除後の同一 Organization 要件と作成/置換の制限を考慮して、移行を計画する**

**解説:**
共有解除後も既存リソースは継続して利用できる場合がありますが、新しいリソースの作成や、マネージドサービスのスケーリング/置換に影響する可能性があります。分離する前に、単独で運用できる経路を準備してください。

</details>

---

3. Shared Cluster から、別の Account が所有する AWS リソースにアクセスするにはどうすればよいですか？
   - A) 常に IAM user のキーを発行する
   - B) 必要に応じて、ターゲットロールのチェーン、サポート対象のリソースポリシー、または IRSA を選択する
   - C) すべてのワークロードに対して、必ず2つのロールを作成する
   - D) aws-auth を編集して AWS 権限を付与する

<details>
<summary>回答を表示</summary>

**回答: B) 必要に応じて、ターゲットロールのチェーン、サポート対象のリソースポリシー、または IRSA を選択する**

**解説:**
プライマリ Pod Identity role が同一 Account に必要という要件は、すべてのリクエストにターゲットロールを要求するものではありません。クラスターを所有する Account と、データベースのみを所有する Account を区別してください。

</details>

---

4. Access Policies と Kubernetes RBAC を組み合わせるとどうなりますか？
   - A) 後から適用された方だけが有効になる
   - B) Allow が組み合わさり、どちらも相手を制限しない
   - C) 両者を組み合わせることはできない
   - D) RBAC が常に優先される

<details>
<summary>回答を表示</summary>

**回答: B) Allow が組み合わさり、どちらも相手を制限しない**

**解説:**
意図した権限付与と重複を確認してください。自動化は役立ちますが、API の前提条件ではありません。

</details>

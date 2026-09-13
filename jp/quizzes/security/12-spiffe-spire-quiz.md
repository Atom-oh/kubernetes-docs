# SPIFFE/SPIRE クイズ

> **最終更新**: September 13, 2026

## 問題

<span id="_1-what-is-the-correct-format-for-a-spiffe-id"></span>

### 1. 有効な SPIFFE ID はどれですか？

- A) `https://example.org/app`
- B) `spiffe://example.org/app`
- C) `spiffe://example.org:8443/app`
- D) `spiffe://example.org/app?role=admin`

<details>
<summary>答えを表示</summary>

**回答: B) spiffe://example.org/app**

spiffe スキーム、trust domain（信頼ドメイン）、および任意のパスを使用します。ポート、クエリ、フラグメントは許可されません。パス構造はサイト側で定義するものであり、/ns/.../sa/... に限定されません。

</details>

<span id="_2-what-is-the-key-difference-between-x-509-svid-and-jwt-svid"></span>

### 2. X.509/JWT-SVID の検証について正しく説明しているのはどれですか？

- A) X.509 の CN のみを確認する
- B) JWT の署名が有効であれば audience は不要になる
- C) X.509 の URI SAN/証明書チェーンと、JWT の署名/sub/audience/有効期限を検証する
- D) JWT の audience チェックによってすべてのリプレイを防止できる

<details>
<summary>答えを表示</summary>

**回答: C) X.509 の URI SAN/証明書チェーンと、JWT の署名/sub/audience/有効期限を検証する**

証明書の CN は SPIFFE identity ではありません。JWT bearer token は audience が一致していてもリプレイされる可能性があります。有効期間はポリシーに依存し、本章で扱う X.509/JWT の範囲は Incubating の WIT-SVID 仕様とは別ものです。

</details>

<span id="_3-what-is-the-primary-role-of-the-spire-server"></span>

### 3. SPIRE Server の役割は何ですか？

- A) すべてのアプリケーション接続を自動的に暗号化する
- B) agent の attestation、登録、SVID の署名を管理する
- C) すべてのサービスリクエストを自動的に認可する
- D) CSI を通じてすべての Pod に秘密鍵ファイルを配布する

<details>
<summary>答えを表示</summary>

**回答: B) agent の attestation、登録、SVID の署名を管理する**

CA/JWT 署名、DataStore、KeyManager の責務を区別してください。AWS PCA を upstream にすると SPIRE の中間 CA に署名されますが、ローカルでの leaf 署名や鍵管理がなくなるわけではありません。

</details>

<span id="_4-what-is-the-primary-role-of-the-spire-agent"></span>

### 4. Workload API を呼び出しているアプリケーションを識別するのは誰ですか？

- A) ローカルの SPIRE agent の workload attestor
- B) DNS リゾルバー
- C) ファイル名を確認する CSI
- D) アプリケーションが自己申告した SPIFFE ID のみ

<details>
<summary>答えを表示</summary>

**回答: A) ローカルの SPIRE agent の workload attestor**

agent は呼び出し元の PID/cgroups/Pod メタデータを調べ、認可済みのエントリ/キャッシュと照合します。agent Pod 内から取得した場合は、実際のアプリケーションのコンテキストではなくその呼び出し元が attest されます。

</details>

<span id="_5-which-node-attestation-method-is-recommended-for-amazon-eks"></span>

### 5. server は k8s_psat token をどのように検証しますか？

- A) IRSA ロールの S3 権限を確認する
- B) Kubernetes の TokenReview に加えて、設定された audience/SA の許可リストで検証する
- C) token を base64 デコードするだけ
- D) 有効期限のない join token に変換する

<details>
<summary>答えを表示</summary>

**回答: B) Kubernetes の TokenReview に加えて、設定された audience/SA の許可リストで検証する**

server/agent の論理クラスター名、token の audience、SA 許可リスト、TokenReview の権限を一致させてください。aws_iid は異なる信頼の前提を持つ代替手段であり、常に優れているわけでも EKS で禁止されているわけでもありません。

</details>

<span id="_6-what-selector-types-does-k8s-workload-attestation-support"></span>

### 6. k8s:container-image:nginx:* はどのように解釈すべきですか？

- A) すべての nginx タグに対する自動的な glob マッチング
- B) selector の値であり、ワイルドカードマッチングを前提にしてはならない
- C) イメージ署名が検証されていることの証明
- D) namespace の RBAC を自動的に強制すること

<details>
<summary>答えを表示</summary>

**回答: B) selector の値であり、ワイルドカードマッチングを前提にしてはならない**

Kubernetes が実際に報告する image/ImageID の値と一致させてください。タグだけではサプライチェーンの信頼は確立できません。Pod/SA/label の作成・変更権限も identity の適格性に影響します。

</details>

<span id="_7-what-is-the-purpose-of-the-spiffe-csi-driver"></span>

### 7. SPIFFE CSI 0.2.13 は Pod に何をマウントしますか？

- A) 自動生成された svid.pem/svid.key ファイル
- B) Workload API の Unix socket を含むディレクトリ
- C) SPIRE の CA 秘密鍵
- D) 共有された PostgreSQL のデータ

<details>
<summary>答えを表示</summary>

**回答: B) Workload API の Unix socket を含むディレクトリ**

CSI は API socket へのアクセスを提供します。ファイルベースのアプリケーションには別途アダプターとリロード処理が必要です。API を利用するのは依然としてアプリケーションまたは proxy であり、統合が常に自動で行われるわけではありません。

</details>

<span id="_8-what-does-spiffe-federation-enable"></span>

### 8. https_spiffe の federation をブートストラップするには何が必要ですか？

- A) エンドポイント URL のみ
- B) 初期の信頼済み bundle と正しいエンドポイントの SPIFFE ID
- C) 双方の CA 秘密鍵を交換すること
- D) すべてのリモート workload を自動的に認可すること

<details>
<summary>答えを表示</summary>

**回答: B) 初期の信頼済み bundle と正しいエンドポイントの SPIFFE ID**

信頼の方向ごとに設定してください。bundle の更新、接続性、TLS 検証、workload の認可はそれぞれ別の責務です。https_web はエンドポイントの Web PKI 検証パスを使用します。

</details>

<span id="_9-how-does-spiffe-spire-compare-to-iam-roles-for-service-accounts-irsa"></span>

### 9. IRSA と SPIFFE/SPIRE を正しく比較しているのはどれですか？

- A) IRSA の更新には必ず Pod の再起動が必要である
- B) SPIFFE を使えば AWS IAM ポリシーは不要になる
- C) IRSA は AWS の認証情報の経路であり、SPIFFE は workload identity で、いずれも検証が必要である
- D) Pod の annotation だけで IRSA と CSI による証明書ファイルの配布が完結する

<details>
<summary>答えを表示</summary>

**回答: C) IRSA は AWS の認証情報の経路であり、SPIFFE は workload identity で、いずれも検証が必要である**

IRSA はサポートされている SDK/projected token の挙動によって更新され、クロスアカウント構成にも対応します。ServiceAccount の annotation、aud/sub の信頼関係、AWS の権限を検証してください。SPIFFE の mTLS でも、認証情報の利用とピアの認可が必要です。

</details>

<span id="_10-what-are-best-practices-for-naming-trust-domains-in-spiffe"></span>

### 10. trust domain と CA ローテーションについて正しいのはどれですか？

- A) trust domain は解決可能な DNS 名でなければならない
- B) bundle set は CA 秘密鍵を自動的にローテーションする
- C) 安定した名前を選び、bundle の変更と CA 鍵のローテーションを区別する
- D) 数値や IPv4 形式のドメインはパーサーによって常に拒否される

<details>
<summary>答えを表示</summary>

**回答: C) 安定した名前を選び、bundle の変更と CA 鍵のローテーションを区別する**

DNS 風の命名はガイダンスであり、構文規則のすべてではありません。bundle は公開された信頼情報であり、鍵のローテーションは別のライフサイクルです。authority の重複期間と利用側の更新を確認してください。

</details>

## スコア計算

- 9〜10: しっかり理解できています
- 7〜8: 信頼、認可、配布の経路を再確認しましょう
- 6 以下: ガイドと検証済みの例を復習しましょう

## 関連ドキュメント

- [SPIFFE/SPIRE](../../security/12-spiffe-spire.md)

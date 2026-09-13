# Observability ラボ 01 クイズ

<span id="observability-lab-part-1-infrastructure-setup-quiz"></span>

> **最終更新**: September 13, 2026

1. 確認した EKS バージョンのサポート状況はどのように活用すべきですか？
   - A) 1.31 は必然的にすでにサポート対象外である。
   - B) 確認済みの 1.36 標準サポートを基準としつつ、現在の Region とサポート状況を再確認する。
   - C) マイナーバージョンは永久にサポートされる。
   - D) kubectl のバージョンスキューは決して問題にならない。

<details>
<summary>回答を表示</summary>

**回答: B) 確認済みの 1.36 標準サポートを基準としつつ、現在の Region とサポート状況を再確認する。**

延長サポートとサポート終了を区別し、クライアントとサーバーの互換性を検証してください。

</details>

---

2. VPC を再利用する際に何を確認する必要がありますか？
   - A) VPC ID の文字列のみ。
   - B) Subnet の AZ、アドレス容量、ルート、DNS / SG、そして重複しない service CIDR。
   - C) 両方の service CIDR を同一にする。
   - D) NAT やエンドポイントは決して必要ない。

<details>
<summary>回答を表示</summary>

**回答: B) Subnet の AZ、アドレス容量、ルート、DNS / SG、そして重複しない service CIDR。**

ジェネレーターはネットワークリソースを作成しないため、実際の接続性に関する前提条件は依然として残ります。

</details>

---

3. パブリック API クライアントの CIDR はどのように設定すべきですか？
   - A) 常に 0.0.0.0/0。
   - B) 実際の送信元に一致する、承認された狭い範囲。
   - C) 本番環境でドキュメント用の任意の IP を使用する。
   - D) CIDR だけで認証を置き換えられる。

<details>
<summary>回答を表示</summary>

**回答: B) 実際の送信元に一致する、承認された狭い範囲。**

プライベート / パブリックエンドポイント、送信元アドレス、認証をあわせて検証してください。

</details>

---

4. IRSA の信頼関係で不可欠な制約は何ですか？
   - A) すべての ServiceAccount を許可する。
   - B) 正しい OIDC プロバイダーと、正確な audience / namespace / ServiceAccount の subject。
   - C) すべての権限を node role に付与する。
   - D) Pod 内にアクセスキーをハードコードする。

<details>
<summary>回答を表示</summary>

**回答: B) 正しい OIDC プロバイダーと、正確な audience / namespace / ServiceAccount の subject。**

プロバイダー ARN と issuer のホスト / パスは、同一のプロバイダーを指し示している必要があります。

</details>

---

5. Aurora のアクセス境界はどうあるべきですか？
   - A) インターネットに公開されたパブリックな writer。
   - B) プライベート Subnet と、実際のサービスクライアント SG からの PostgreSQL 5432 アクセス。
   - C) SG 名が似ていれば十分である。
   - D) マルチ AZ の writer が自動的に現れる。

<details>
<summary>回答を表示</summary>

**回答: B) プライベート Subnet と、実際のサービスクライアント SG からの PostgreSQL 5432 アクセス。**

単一の writer はラボ上の選択であり、HA の保証ではありません。

</details>

---

6. アプリケーションはどの DB アカウントを使用すべきですか？
   - A) すべての Pod でマスターアカウント。
   - B) ラボ用テーブルへの DML 権限を持つ、独立したランタイムアカウント。
   - C) パスワードなしのパブリック接続。
   - D) 実行ごとに既存のパスワードを上書きする。

<details>
<summary>回答を表示</summary>

**回答: B) ラボ用テーブルへの DML 権限を持つ、独立したランタイムアカウント。**

Bootstrap はロールを上書きしません。失敗した場合は候補となる認証情報を検証してください。

</details>

---

7. 特殊文字を含むパスワードはどのように渡すべきですか？
   - A) DSN に直接連結する。
   - B) 生の JSON 値を URL.create の password 引数として渡す。
   - C) 繰り返し URL エンコードする。
   - D) コピーできるようログに出力する。

<details>
<summary>回答を表示</summary>

**回答: B) 生の JSON 値を URL.create の password 引数として渡す。**

あわせて TLS の verify-full と実際の CA パスも検証してください。

</details>

---

8. クラスター作成が失敗した後には何をすべきですか？
   - A) 新しい名前を作り続ける。
   - B) 同じ名前で作成された部分的なリソース、状態、所有関係を調査する。
   - C) 失敗後は課金されないと想定する。
   - D) すべての VPC を削除する。

<details>
<summary>回答を表示</summary>

**回答: B) 同じ名前で作成された部分的なリソース、状態、所有関係を調査する。**

CLI の失敗は、リソースが作成されなかったことの証明にはなりません。

</details>

---

9. gp3 StorageClass の確認には何が含まれますか？
   - A) 名前が一致していれば常に動作する。
   - B) EBS CSI、権限、実際の class、そしてボリュームのクリーンアップを確認する。
   - C) 常に共有 class を上書きする。
   - D) PVC の削除とスナップショットの削除は同一である。

<details>
<summary>回答を表示</summary>

**回答: B) EBS CSI、権限、実際の class、そしてボリュームのクリーンアップを確認する。**

共有オブジェクトの変更と、リソース削除の責任範囲を区別してください。

</details>

---

10. ラボのコストはどのように見積もるべきですか？
   - A) 常に 1 時間あたり 2.5 USD。
   - B) 実際の Region、使用量、保持期間、NAT / LB / ストレージ / スナップショットを含める。
   - C) AMG の月額ユーザー料金を、ワークスペースの時間単位料金として扱う。
   - D) NodePool の上限は絶対的な予算である。

<details>
<summary>回答を表示</summary>

**回答: B) 実際の Region、使用量、保持期間、NAT / LB / ストレージ / スナップショットを含める。**

固定の合計額や、計測していない削減効果を主張しないでください。

</details>

---

[ガイドに戻る](../../../labs/observability/01-infrastructure-setup-lab.md)

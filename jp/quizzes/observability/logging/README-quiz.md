# Logging 概要クイズ

Logging の基本概念に関する理解度を確認しましょう。

---

1. Structured Logging の主な利点ではないものはどれですか？

   - A) 検索およびフィルタリングの効率向上
   - B) ログファイルサイズの削減
   - C) 一貫したログ形式
   - D) 自動分析ツールとの互換性

<details>
<summary>回答を表示</summary>

**回答: B) ログファイルサイズの削減**

**解説:**
Structured Logging（特に JSON 形式）は、非構造化テキストログよりも実際にはファイルサイズが大きくなる場合があります。これは、フィールド名と区切り文字が追加されるためです。Structured Logging の真の利点は、検索効率、一貫性、自動化ツールとの互換性です。

</details>

---

2. 本番環境で推奨されるログレベルはどれですか？

   - A) DEBUG
   - B) TRACE
   - C) INFO or WARN
   - D) FATAL

<details>
<summary>回答を表示</summary>

**回答: C) INFO or WARN**

**解説:**
本番環境では INFO または WARN レベルが推奨されます。DEBUG や TRACE は詳細すぎてログ量が過剰になり、FATAL のみを使用すると重要な運用情報を見逃す可能性があります。

</details>

---

3. Kubernetes で最も推奨されるログ収集パターンはどれですか？

   - A) File-based logging + Sidecar
   - B) stdout/stderr + DaemonSet agent
   - C) リモート Logging サーバーへの直接送信
   - D) 手動収集を伴うローカルファイル保存

<details>
<summary>回答を表示</summary>

**回答: B) stdout/stderr + DaemonSet agent**

**解説:**
Kubernetes では、コンテナが stdout/stderr にログを出力し、DaemonSet としてデプロイされた agent がノード上の `/var/log/containers/` からログを収集するのが標準的なアプローチです。このアプローチには、kubectl logs command との互換性、自動ローテーション、別途 Volume が不要であることなどの利点があります。

</details>

---

4. ログストレージの選定で「コスト最適化」が最優先の場合、推奨されるソリューションはどれですか？

   - A) Amazon OpenSearch Service
   - B) CloudWatch Logs
   - C) Grafana Loki + S3
   - D) EC2 上の Elasticsearch

<details>
<summary>回答を表示</summary>

**回答: C) Grafana Loki + S3**

**解説:**
Loki はログの内容ではなくラベルのみをインデックス化することで、ストレージコストを大幅に削減します。バックエンドとして S3 を使用すると、GB あたり $0.023 という低いストレージコストを実現できます。

</details>

---

5. 分散トレーシングのために JSON ログ形式に含める必要があるフィールドはどれですか？

   - A) user_id, session_id
   - B) trace_id, span_id
   - C) request_id, response_time
   - D) level, message

<details>
<summary>回答を表示</summary>

**回答: B) trace_id, span_id**

**解説:**
分散トレーシングでは、trace_id（リクエスト全体の追跡）と span_id（個々の操作の識別）が必要です。これらのフィールドにより、複数の Service にまたがるリクエストのフローを追跡できます。

</details>

---

6. ログ収集パイプラインにおける「Processing Layer」の役割ではないものはどれですか？

   - A) ログの解析と正規化
   - B) Kubernetes メタデータの追加
   - C) ログの保存とインデックス化
   - D) フィルタリングとサンプリング

<details>
<summary>回答を表示</summary>

**回答: C) ログの保存とインデックス化**

**解説:**
ログの保存とインデックス化は「Storage Layer」の役割です。Processing Layer は、解析、メタデータの追加、フィルタリング、バッファリングなどを処理します。

</details>

---

7. 金融規制への準拠のために推奨されるログ保持期間はどれですか？

   - A) 30 日
   - B) 1 年
   - C) 7 年
   - D) 90 日

<details>
<summary>回答を表示</summary>

**回答: C) 7 年**

**解説:**
金融規制への準拠（例: SOX、PCI-DSS 関連）では、通常 7 年間のログ保持が推奨されます。医療分野（HIPAA）では 6 年間が求められ、一般的な運用ログでは通常約 1 年間が必要です。

</details>

---

8. Sidecar パターンを使用してログを収集すべきなのは、どのような場合ですか？

   - A) すべての標準 Kubernetes ワークロード
   - B) レガシーアプリケーションがログをファイルにしか出力しない場合
   - C) CPU リソースに制約のある環境
   - D) 単一コンテナの Pod のみ

<details>
<summary>回答を表示</summary>

**回答: B) レガシーアプリケーションがログをファイルにしか出力しない場合**

**解説:**
Sidecar パターンは、レガシーアプリケーション（stdout/stderr ではなくファイルへの Logging）、マルチテナント環境でのログ分離、特別なログ形式の処理が必要な場合に使用されます。リソースのオーバーヘッドがあるため、標準ワークロードでは DaemonSet アプローチの方が効率的です。

</details>

---

9. クエリパフォーマンスと全文検索の両方で「優れている」ログストレージソリューションはどれですか？

   - A) Grafana Loki
   - B) CloudWatch Logs
   - C) Amazon OpenSearch Service
   - D) ClickHouse

<details>
<summary>回答を表示</summary>

**回答: C) Amazon OpenSearch Service**

**解説:**
OpenSearch（Elasticsearch fork）は、強力な Lucene ベースの全文検索機能と複雑な集計クエリの両方をサポートします。Loki の全文検索は限定的であり、CloudWatch と ClickHouse の全文検索機能は中程度です。

</details>

---

10. EKS control plane Logging でセキュリティ監査のために有効にする必要があるログタイプはどれですか？

    - A) scheduler
    - B) controllerManager
    - C) audit
    - D) api

<details>
<summary>回答を表示</summary>

**回答: C) audit**

**解説:**
Audit logs は Kubernetes API server へのすべてのリクエストを記録します。誰が、何を、いつ行ったかを追跡できるため、セキュリティ監査と規制準拠に不可欠です。API logs も重要ですが、セキュリティ監査の目的では audit が最も重要です。

</details>

---

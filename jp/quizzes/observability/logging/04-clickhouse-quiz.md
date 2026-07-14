# ログ分析のための ClickHouse クイズ

ClickHouse を使用したログ分析についての理解を確認しましょう。

---

1. ClickHouse がログ分析で高いパフォーマンスを示す主な理由は何ですか？

   - A) 行指向ストレージ
   - B) カラム指向ストレージ
   - C) ドキュメント指向ストレージ
   - D) キー・バリューストレージ

<details>
<summary>答えを表示</summary>

**答え: B) カラム指向ストレージ**

**解説:**
ClickHouse は分析クエリ（特定のカラムのみをスキャン）向けに最適化されたカラム指向データベースです。同じデータ型は連続して保存されるため、高い圧縮率とベクトル化クエリ実行が可能になります。

</details>

---

2. ClickHouse クラスターでデータレプリケーションと分散クエリの調整に使用されるコンポーネントはどれですか？

   - A) Kafka
   - B) Redis
   - C) ZooKeeper/ClickHouse Keeper
   - D) etcd

<details>
<summary>答えを表示</summary>

**答え: C) ZooKeeper/ClickHouse Keeper**

**解説:**
ClickHouse クラスターは ZooKeeper または ClickHouse Keeper を使用して、レプリカ間のデータ同期、分散 DDL の実行、リーダー選出を調整します。ClickHouse Keeper は ZooKeeper に代わる ClickHouse 専用の選択肢です。

</details>

---

3. レプリケーションをサポートし、ログストレージに最も適した ClickHouse テーブルエンジンはどれですか？

   - A) MergeTree
   - B) ReplicatedMergeTree
   - C) Log
   - D) Memory

<details>
<summary>答えを表示</summary>

**答え: B) ReplicatedMergeTree**

**解説:**
ReplicatedMergeTree は、すべての MergeTree 機能（ソート、パーティショニング、TTL など）にレプリケーション機能を追加します。高可用性が必要な本番ログストレージに推奨されます。

</details>

---

4. ClickHouse で低カーディナリティの文字列カラム（例: level、namespace）に使用すべき最適化タイプはどれですか？

   - A) String
   - B) FixedString
   - C) LowCardinality(String)
   - D) Enum

<details>
<summary>答えを表示</summary>

**答え: C) LowCardinality(String)**

**解説:**
LowCardinality(String) は、一意の値が少ない（約 10,000 以下）文字列カラムに使用されます。内部で辞書エンコーディングを使用して、ストレージ容量とクエリパフォーマンスを最適化します。

</details>

---

5. ClickHouse のログテーブルを設計する際、`ORDER BY` 句でカラムの順序を指定する原則は何ですか？

   - A) アルファベット順
   - B) カラムサイズ順（小さいものから）
   - C) 頻繁にフィルタリングされるカラムを先に配置する
   - D) 作成時刻順

<details>
<summary>答えを表示</summary>

**答え: C) 頻繁にフィルタリングされるカラムを先に配置する**

**解説:**
ClickHouse の ORDER BY はデータのソートとインデックス作成に影響します。WHERE 句で頻繁に使用されるカラムを先頭に配置すると、クエリ時にスキャンするデータ量が少なくなります。例: `ORDER BY (namespace, service, timestamp)`

</details>

---

6. ClickHouse で大規模なデータセットを高速に分析するためのサンプリング手法の構文はどれですか？

   - A) `LIMIT RANDOM 10%`
   - B) `SAMPLE 0.1`
   - C) `WHERE rand() < 0.1`
   - D) `TABLESAMPLE (10 PERCENT)`

<details>
<summary>答えを表示</summary>

**答え: B) `SAMPLE 0.1`**

**解説:**
ClickHouse の `SAMPLE` 句は、データの一部のみをスキャンして高速な近似分析を行います。`SAMPLE 0.1` はデータの 10% のみを読み取ります。適切な係数を結果に乗算することで、推定合計を得られます。

</details>

---

7. ログ収集のために、ログソースと ClickHouse の間に Kafka を配置する主な理由は何ですか？

   - A) データ暗号化
   - B) バッファリングとピークトラフィックへの対応
   - C) データ圧縮
   - D) クエリ最適化

<details>
<summary>答えを表示</summary>

**答え: B) バッファリングとピークトラフィックへの対応**

**解説:**
Kafka は、ピークトラフィック時にログをバッファリングするメッセージキューとして機能し、ClickHouse が一貫したレートでデータを消費できるようにします。また、ClickHouse の障害時にデータ損失を防ぎます。

</details>

---

8. ClickHouse SQL で JSON フィールド値を抽出するために使用される関数はどれですか？

   - A) JSON_EXTRACT()
   - B) JSONExtractString(), JSONExtractFloat()
   - C) parseJSON()
   - D) getJSON()

<details>
<summary>答えを表示</summary>

**答え: B) JSONExtractString(), JSONExtractFloat()**

**解説:**
ClickHouse は、`JSONExtractString(json, 'field')` や `JSONExtractFloat(json, 'field')` などの関数を使用して JSON フィールドを抽出します。型ごとに異なる関数が使用されます。

</details>

---

9. ClickHouse テーブルで古いデータを自動的に削除する機能はどれですか？

   - A) AUTO_DELETE
   - B) RETENTION_POLICY
   - C) TTL (Time To Live)
   - D) EXPIRE_AFTER

<details>
<summary>答えを表示</summary>

**答え: C) TTL (Time To Live)**

**解説:**
ClickHouse の TTL 機能は、一定期間後にデータを自動的に削除するか、別のストレージ（例: S3）へ移動します。例: `TTL date + INTERVAL 90 DAY DELETE`

</details>

---

10. ClickHouse を Grafana と統合する際に使用されるデータソースプラグインはどれですか？

    - A) grafana-mysql-datasource
    - B) grafana-clickhouse-datasource
    - C) grafana-sql-datasource
    - D) grafana-olap-datasource

<details>
<summary>答えを表示</summary>

**答え: B) grafana-clickhouse-datasource**

**解説:**
ClickHouse を Grafana と統合するには、`grafana-clickhouse-datasource` プラグインをインストールします。このプラグインにより、SQL クエリを使用して ClickHouse データを可視化し、ダッシュボードを構築できます。

</details>

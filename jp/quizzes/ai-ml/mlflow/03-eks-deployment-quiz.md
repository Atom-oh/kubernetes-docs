# MLflow EKS デプロイメントクイズ

## 選択式問題

1. EKS セルフホスティングにおける主なトレードオフは何ですか？
   - A) マネージドサービスより常に低コストである
   - B) サーバー、ストア、アクセス制御を運用しながら Kubernetes パターンを再利用する
   - C) マネージドサービスでは実験を追跡できない
   - D) S3 とデータベースが自動的に作成される

<details>
<summary>回答を表示</summary>

**回答: B**

運用作業、機能、サポート対象バージョン、測定された負荷を比較してください。
</details>

2. SQLite の同時実行性について正しい記述はどれですか？
   - A) 2 人目のユーザーが常に即座に破損させる
   - B) 複数のプロセスと直列化された書き込みは可能だが、writer、locking、shared-file の制限がある
   - C) リレーショナルではない
   - D) Pod ローカルの個別ファイルが自動的に 1 つの共有 DB を形成する

<details>
<summary>回答を表示</summary>

**回答: B**

SQLite の機能とマルチ Pod ストレージトポロジーを区別してください。
</details>

3. レビュー対象のコミュニティ Chart 1.11.7 のメタデータにおけるデフォルトは何ですか？
   - A) 必須の RDS PostgreSQL
   - B) S3 オブジェクト
   - C) backendStore.defaultSqlitePath は :memory: である
   - D) 自動的にプロビジョニングされる永続 PVC

<details>
<summary>回答を表示</summary>

**回答: C**

この Chart のオーバーライドは、upstream CLI の新しい SQLite ファイルのデフォルトとは異なります。
</details>

4. 外部の tracking PostgreSQL データベースは、他のすべての状態を自動的に共有しますか？
   - A) はい、すべての auth DB と cache を共有する
   - B) はい、すべての worker memory を共有する
   - C) はい、すべての session secret を共有する
   - D) いいえ。個別の auth DB、secret、queue、cache を確認する

<details>
<summary>回答を表示</summary>

**回答: D**

レプリカを増やす前に、有効化された機能の共有状態を確認してください。
</details>

5. Chart、image、source のバージョンはどのように扱うべきですか？
   - A) 常に 1 つの番号を共有する
   - B) source tag によって OCI package の存在が保証される
   - C) それぞれを検証し、実際の package をダウンロードして render する
   - D) latest tag があれば image digest を確認する必要はない

<details>
<summary>回答を表示</summary>

**回答: C**

レビュー対象の upstream Chart source と appVersion も異なっていました。
</details>

6. ServiceAccount の S3 への IAM アクセスは、PostgreSQL ログインを自動的に許可しますか？
   - A) 常に許可する
   - B) いいえ。DB networking、TLS、users/credentials、または IAM DB auth を個別に設定する
   - C) bucket 名が一致する場合のみ許可する
   - D) DB password を image に入れる

<details>
<summary>回答を表示</summary>

**回答: B**

これらは別個の authorization 層と authentication 層です。
</details>

7. EKS Pod Identity に必要なものは何ですか？
   - A) すべての Fargate および Windows Pod に対する無条件のサポート
   - B) ServiceAccount 名のみ
   - C) Linux EC2 worker、Agent、association、サポート対象の SDK、および関連するセットアップ
   - D) 静的な root access key

<details>
<summary>回答を表示</summary>

**回答: C**

IRSA と Pod Identity のサポートおよび設定は個別に確認してください。
</details>

8. SecretKeyRef と allowed_hosts だけでセキュリティは完了しますか？
   - A) environment exposure を排除し、すべての user authorization を実装する
   - B) いいえ。secret delivery と application authentication/authorization を個別に確認する
   - C) データベースを自動的にバックアップする
   - D) すべての CORS origin を許可する必要がある

<details>
<summary>回答を表示</summary>

**回答: B**

runtime secret injection と host-validation の境界を理解してください。
</details>

## 短答式問題

9. /health が 200 を返すことは、RDS と S3 が正常であることを証明しますか？

<details>
<summary>回答を表示</summary>

いいえ。検証済みの実装では、HTTP プロセスの応答性に対して OK、200 を返します。継続的なデータベース、S3、authorization、および実際の workload path を個別に確認してください。
</details>

10. 頻繁な logging と Aurora Serverless v2 を評価する際に重要なことは何ですか？

<details>
<summary>回答を表示</summary>

レプリカや worker 全体で batching、transaction、metric history、trace payload、pool を測定してください。Aurora には capacity、connection、I/O、transaction の制限があります。無制限の burst absorption や最低コストは保証されません。
</details>

---

[学習教材に戻る](../../../ai-ml/mlflow/03-eks-deployment.md)

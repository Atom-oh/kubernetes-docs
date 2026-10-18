# Helm デプロイとエグゼキューター選択クイズ

Chart 1.22.0 / Airflow 3.3.1 / KEDA 2.20。

## 1. このガイドではどの chart とリポジトリエイリアスを使いますか？

<details>
<summary>回答を表示</summary>

Apache Airflow プロジェクトの公式 chart です。リポジトリを apache-airflow として登録すると、コマンドでは apache-airflow/airflow を使います。独立したコミュニティ chart の値を混在させないでください。

</details>

## 2. Chart 1.22.0 の実際の Airflow/エグゼキューターのデフォルト値は何ですか？

<details>
<summary>回答を表示</summary>

Airflow 3.2.2 と CeleryExecutor です。このガイドでは 3.3.1/KubernetesExecutor のプロファイルを使うため、明示的に上書きしています。

</details>

## 3. Chart.yaml ではドキュメントに記載されているすべての最小バージョンが適用されますか？

<details>
<summary>回答を表示</summary>

そうとは限りません。Helm 3.19.0 以降と、互換性のある Kubernetes/Airflow を使用してください。Chart 1.16 の README では Kubernetes 1.29 以降が指定されていました。レビュー対象の 1.22 のテンプレートも 1.29 でレンダリングされましたが、これはサポートの証明にはなりません。

</details>

## 4. エグゼキューターだけで Redis とワーカーのリソース種別が決まりますか？

<details>
<summary>回答を表示</summary>

エグゼキューターは影響しますが、Redis/外部ブローカーの設定やワーカーの永続化も関係します。ワーカーには Deployment と StatefulSet を使えます。Celery では外部ブローカーも使用できます。

</details>

## 5. PostgreSQL を無効にすれば外部データベースが構成されますか？

<details>
<summary>回答を表示</summary>

いいえ。データベース、マイグレーション権限、URI/TLS、metadataSecretName などの接続参照を準備してください。この Secret を設定すると、metadataConnection は正しい接続元にはなりません。

</details>

## 6. アップグレード時に Fernet/API/JWT キーを再生成すべきですか？

<details>
<summary>回答を表示</summary>

通常のアップグレードでは保持してください。Fernet キーを失うと暗号化データにアクセスできなくなる可能性があり、JWT の変更は実行中のタスク認証に影響する場合があります。バックアップとローテーションは慎重に扱ってください。

</details>

## 7. この例ではデフォルトの admin/admin をどのように避けていますか？

<details>
<summary>回答を表示</summary>

createUserJob を無効にし、選択した FAB 認証マネージャー向けに対話型の airflow users create を使います。パスワードは 2 回入力します。ほかの認証マネージャー/SSO では、それぞれの手順が必要です。

</details>

## 8. KubernetesExecutor の起動には常に 1〜2 分かかりますか？

<details>
<summary>回答を表示</summary>

いいえ。イメージキャッシュ/取得、Kubernetes API/スケジューラー、ノードの利用可能性/プロビジョニング、クォータ、ランタイムの初期化を測定してください。Celery でもゼロからのスケール後にはコールドスタートがあります。

</details>

## 9. KubernetesExecutor で任意の GPU/CLI ワーカーイメージを使えますか？

<details>
<summary>回答を表示</summary>

ワーカーには互換性のある Airflow タスクランタイムと DAG/provider の依存関係が必要です。これは KubernetesPodOperator がワークロードイメージを使って子 Pod を起動する場合とは異なります。

</details>

## 10. ワーカー Pod がなくなれば、Airflow のアイドル時の総コストはゼロになりますか？

<details>
<summary>回答を表示</summary>

コントロールプレーン、データベース、ブローカー、ノード、ストレージ、ログのコストは残る場合があります。Pod ごとの実行やゼロへのスケーリングでも、総コストがゼロになったり、セキュリティが完全に分離されたりするわけではありません。

</details>

## 11. chart の KEDA のタイミングに関するデフォルト値と例の値は何ですか？

<details>
<summary>回答を表示</summary>

デフォルトは pollingInterval=5s、cooldownPeriod=30s です。例では 10s/300s を明示的に選択しています。ゼロへのスケーリングの cooldown と、ゼロより上での HPA スケーリング/安定化を区別してください。

</details>

## 12. SQL 内の worker_concurrency には何を設定すべきですか？

<details>
<summary>回答を表示</summary>

データベースの worker_concurrency という列名ではなく、chart がレンダリングした数値 (この例では 4) です。対象ワーカーのキュー/エグゼキューターについて、該当する実行中/待機中のタスク数を数えて割り、切り上げます。

</details>

## 13. k8s エイリアスで混合エグゼキューターのスケーリングエラーが起きることがあるのはなぜですか？

<details>
<summary>回答を表示</summary>

TaskInstance には task.executor が保存されます。chart が文字列どおりの KubernetesExecutor だけを除外している場合、k8s として保存されたタスクが Celery の件数に含まれることがあります。実際に保存される値と一致するフィルターを使ってください。

</details>

## 14. クエリ結果が 25 で、maxReplicaCount=20 の場合はどうなりますか？

<details>
<summary>回答を表示</summary>

最大値によってワーカー数が制限されるため、すべての需要がすぐに満たされるわけではありません。バックログ、並行数、ワーカーリソース、データベース/ブローカーの負荷、ノード容量を合わせて調べてください。

</details>

## 15. Airflow Pod の TLS 設定があれば、KEDA のデータベースアクセスにも十分ですか？

<details>
<summary>回答を表示</summary>

いいえ。KEDA は独立したデータベースクライアントであり、DNS、ネットワーキング、権限、互換性のある URI、CA が必要です。URI の sslrootcert パスは scaler から読み取れる必要があります。chart が自動的にコピーすることはありません。

</details>

## 16. KEDA は Deployment にしか使えませんか？

<details>
<summary>回答を表示</summary>

いいえ。Celery の永続化設定に応じて、この chart は Deployment または StatefulSet を対象にします。KubernetesExecutor のタスク Pod は同じレプリカプールのパターンではありませんが、それによってほかの KEDA の用途が禁止されるわけではありません。

</details>

## 17. Helm --wait が成功すれば、検証も完了しますか？

<details>
<summary>回答を表示</summary>

マイグレーションの成功、長時間稼働するコンポーネントの Ready、DAG の配布、ワーカーの実行、Execution API、結果、ログを確認してください。KEDA のプロファイルでは、ワークロードに応じたスケーリング、アイドル状態への復帰、復旧もテストします。

</details>

## 18. Helm uninstall を実行すると PostgreSQL のデータはすぐにすべて削除されますか？

<details>
<summary>回答を表示</summary>

Pod の削除と PVC/PV のデータライフサイクルは異なります。PVC の保持、StorageClass の reclaim policy、外部データベースの削除/バックアップは別々に確認してください。共有 namespace、Secret、データベースを無差別に削除しないでください。

</details>

[ガイド](../../../data-on-eks/airflow/02-helm-deployment.md)

[前のクイズ](./01-architecture-quiz.md)

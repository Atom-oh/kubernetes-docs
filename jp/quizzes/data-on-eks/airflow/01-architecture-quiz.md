# Airflow アーキテクチャクイズ

Airflow 3.3.1 / Helm chart 1.22.0 · 2026年9月。

## 1. Airflow 2 の DAG 解析について正しい説明はどれですか？

- A) すべてのファイルをスケジューラと同じループ内だけで解析していた
- B) DAG は Redis からだけ読み込まれていた
- C) ファイル処理用サブプロセスと、オプションの独立した DAG 処理機能が既にあった
- D) 解析せずにタスクが実行されていた

<details>
<summary>回答を表示</summary>

**C**

スケジューラはファイルごとのサブプロセスを使う manager を起動するか、独立した処理を使用できました。シリアライズされた DAG によるスケジューリングと、複数スケジューラによる HA も Airflow 3 より前からありました。

</details>

## 2. Airflow 3 の DAG プロセッサは何をしますか？

- A) すべての Operator を実行する
- B) UI ユーザーの JWT のみを発行する
- C) Celery ブローカーを置き換える
- D) bundle の DAG を解析/シリアライズし、関連するメタデータを更新する

<details>
<summary>回答を表示</summary>

**D**

Airflow 3 では必須の独立したロールです。ワーカーにも実行コード/依存関係が必要であり、DAG コードをプロセッサにだけ置いても不十分です。

</details>

## 3. DAG プロセッサを分離すると何が可能になりますか？

- A) 解析とスケジューリングのデプロイや調整を、より独立して行える
- B) スケジューリングのレイテンシがすべてなくなる
- C) データベースのボトルネックがすべてなくなる
- D) レプリカを増やせば HA が保証される

<details>
<summary>回答を表示</summary>

**A**

最新 DAG の解析遅延、共有リソース/データベースの負荷、過剰な並行処理がスケジューリングに影響する場合は残ります。分離しても運用上の検証に代わるものではありません。

</details>

## 4. 通常の supervisor 管理下で動く Python Task SDK 実行では、誰が API を呼び出しますか？

- A) ユーザーのタスクコードがメタデータ SQL を直接実行する
- B) ワーカー側の supervisor がタスク JWT を使って Execution API を呼び出す
- C) すべての状態アクセスを Redis が担う
- D) Kubernetes が XCom を保存する

<details>
<summary>回答を表示</summary>

**B**

タスクランナーと supervisor はソケットを介して通信します。ワーカーから API へのアドレス指定/認証/ネットワーキングが重要です。Celery の結果バックエンドなど、エグゼキューターの内部構成は別途調べてください。

</details>

## 5. triggerer について正しい説明はどれですか？

- A) すべての完全な Operator を実行する
- B) すべての最小デプロイで必須である
- C) 遅延実行されたタスクのトリガーを実行し、その後タスクはワーカーで再開する
- D) 非同期タスクはすべてワーカースロットを解放する

<details>
<summary>回答を表示</summary>

**C**

遅延実行を使わないデプロイでは省略できます。遅延実行されたタスクはワーカースロットと通常はプールスロットを解放しますが、プールの動作は構成できます。

</details>

## 6. メタデータデータベースと Celery ブローカーについて正しい説明はどれですか？

- A) すべてのデプロイで PostgreSQL と Redis が必須である
- B) SQLite が本番環境で標準的に推奨される
- C) MariaDB と MySQL のサポートは同じである
- D) PostgreSQL/MySQL がサポートされ、Celery には Redis 以外のブローカーもある

<details>
<summary>回答を表示</summary>

**D**

このシリーズでは PostgreSQL を例にしています。SQLite は開発/テスト用で、MariaDB はサポートされていません。また、KubernetesExecutor は本質的に Celery ブローカーを必要としません。

</details>

## 7. Airflow 3.0 でサポート対象外になった固定のハイブリッドクラスはどれですか？

- A) LocalKubernetesExecutor と CeleryKubernetesExecutor
- B) LocalExecutor と CeleryExecutor
- C) KubernetesExecutor とすべてのブローカー
- D) DAG プロセッサと triggerer

<details>
<summary>回答を表示</summary>

**A**

固定の 2 種類のハイブリッドクラスは、並行エグゼキューター構成とは異なります。互換性のあるエグゼキューターを明示的に構成し、タスクごとに選択してください。

</details>

## 8. 並行エグゼキューターと DAG のデフォルト値は、どのように動作しますか？

- A) 3.3 で初めて導入され、未インストールのエグゼキューターも動作する
- B) 2.10.0 からサポートされ、DAG の default_args で executor を指定し、タスクごとに上書きできる
- C) 常に 1 つしか使用できない
- D) どの選択肢も Redis のキュー名だけを使う

<details>
<summary>回答を表示</summary>

**B**

最初に構成されたエグゼキューターがデフォルトになります。タスクでは、構成済みの名前/エイリアスを選択できます。また、DAG の default_args でタスクのデフォルト値を指定できます。

</details>

## 9. DAG bundle と git-sync はどのような関係ですか？

- A) Airflow 3 で git-sync は削除された
- B) S3 のバージョニングを有効にすると、すべての S3DagBundle がバージョン管理される
- C) git-sync は引き続きサポートされ、バージョン管理の可否は bundle による
- D) ワーカーに DAG コードは不要である

<details>
<summary>回答を表示</summary>

**C**

GitDagBundle はバージョニングをサポートしますが、レビュー対象の Local/S3/GCS bundle はサポートしません。配布方法と、再試行時に使われるコードのバージョンを確認してください。

</details>

[ガイド](../../../data-on-eks/airflow/01-architecture.md)

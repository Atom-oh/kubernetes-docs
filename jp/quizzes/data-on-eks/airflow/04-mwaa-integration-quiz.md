# MWAA 統合クイズ

プロビジョニング済み MWAA 3.3.1/Python 3.12 の管理境界と EKS 接続性を確認します。

1. 顧客の EKS クラスター内にある kubectl から、MWAA スケジューラを調査できますか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。顧客の VPC 内のプライベートサブネットに接続された AWS マネージド Fargate インフラストラクチャを使用します。

**解説:** これは MWAA が VPC と無関係という意味ではありません。DAG、IAM、ネットワーキング、容量の選択、アップグレードは引き続きユーザーが管理します。

</details>

2. MWAA から EKS に Pod を送信する際に確認すべき 3 つの境界は何ですか？

<details>
<summary>回答を表示</summary>

**回答:** ネットワーク到達性、IAM ベースの EKS 認証、Kubernetes RBAC です。

**解説:** kubeconfig と in_cluster=False だけでは、エンドポイントへの接続性や namespace の権限は得られません。

</details>

3. EKS API 認証モードでは、aws-auth マッピングを追加すればアクセス権が付与されますか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。このモードではアクセスエントリを使います。

**解説:** API_AND_CONFIG_MAP モードでもアクセスエントリを使えます。実際の RoleBinding にグループを一致させ、ほかの権限付与も確認してください。

</details>

4. MWAA では Linux ランタイムやシステム依存関係のインストールが禁止されていますか？

<details>
<summary>回答を表示</summary>

**回答:** スタートアップスクリプトを使えば、サポートされるランタイムをインストールできます。

**解説:** 公式の例には sudo が含まれています。起動時間、ネットワーキング、バージョン制約を検証してください。マネージドのベースイメージを自由に置き換えることとは異なります。

</details>

5. Git → CI → S3 → MWAA の流れがあれば、マージ直後の実行が保証されますか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。ファイルの同期と DAG の解析が完了する必要があります。

**解説:** 記載されている S3 の基本構成だけでは、Airflow bundle の各機能が利用できないとは断定できません。選択したリリースで別の構成がサポートされるか確認してください。

</details>

6. 2026-09-12 に確認したサポート表で、最新の Airflow リリースと MWAA の利用開始日はいつですか？

<details>
<summary>回答を表示</summary>

**回答:** Airflow 3.3.1。2026-09-01 から利用可能で、Python 3.12 に対応しています。

**解説:** 上流の 3.3.1 は 2026-08-12 にリリースされたため、3 か月の固定遅延という説明は誤りです。既存環境のバージョンは別途確認してください。

</details>

7. MWAA は PyPI だけを使うパイプラインや重要度の低いパイプラインにしか適していませんか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。外部の EKS ワークロードイメージを実行できます。運用、機能、復旧に関する要件に基づいて判断してください。

**解説:** KPO 子リソースのイメージは MWAA 自身のランタイムとは異なります。また、プロビジョニング済み MWAA と YAML ベースの MWAA Serverless を区別してください。

</details>

8. セルフホスト型は 30〜60% 安くなるという固定値を、コスト比較に使うべきですか？

<details>
<summary>回答を表示</summary>

**回答:** 根拠と同等の条件がなければ使うべきではありません。

**解説:** 同じスループット/レイテンシの目標を比較し、ワーカー数の範囲、EKS、データベース、ストレージ、NAT、ログ、エンジニアリング工数を含めてください。

</details>

9. この章の Airflow 3.3.1/Python 3.12 環境では、Kubernetes provider をどのように固定しますか？

<details>
<summary>回答を表示</summary>

**回答:** Airflow/Python に対応する制約と apache-airflow-providers-cncf-kubernetes==10.21.0 を使います。

**解説:** まずベースイメージを確認してください。S3 にアップロードした後、環境の requirements オブジェクトのバージョンとインストールログを確認します。

</details>

10. ローカルで生成した kubeconfig を MWAA に渡す前に、何を確認すべきですか？

<details>
<summary>回答を表示</summary>

**回答:** クラスター、コンテキスト、CA、exec.command、IAM 認証情報の選択を確認し、ローカルの AWS_PROFILE 参照を削除します。

**解説:** 静的トークンや長期キーを埋め込まないでください。aws get-token の実行と、MWAA から対象エンドポイントへのアクセスを検証してください。

</details>

11. Kubernetes グループを data-processing namespace 内だけで Role に結び付けるには何を使いますか？

<details>
<summary>回答を表示</summary>

**回答:** その namespace 内に RoleBinding を作成します。

**解説:** ClusterRoleBinding では namespace の境界を表現できません。ほかの権限付与は追加で適用されます。Pod の作成には、サービスアカウントの選択に関する考慮事項もあります。

</details>

12. MWAA_EKS_OK が表示されず、子 Pod が ImagePullBackOff になった場合、最初に MWAA ロールの S3 権限を拡張すべきですか？

<details>
<summary>回答を表示</summary>

**回答:** いいえ。EKS ノード/Fargate のイメージ取得 ID、レジストリ接続性、イメージの有無を調べてください。

**解説:** 子 Pod が MWAA の実行ロールを自動的に継承するわけではありません。ワークロードの実際のデータ権限は別途構成してください。

</details>

---

[学習教材に戻る](../../../data-on-eks/airflow/04-mwaa-integration.md)

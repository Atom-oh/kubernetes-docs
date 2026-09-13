# Dynatrace クイズ

> **最終更新**: September 13, 2026

---

1. OneAgent に関する記述で誤っているものはどれですか？
   - A) サポートされるプロセスを検出できる。
   - B) サポートされるテクノロジーをインストルメントできる。
   - C) インストールにより、すべての権限、スコープ、接続性に関する前提条件が不要になる。
   - D) カバレッジはデプロイモードとテクノロジーのサポート状況に依存する。

<details>
<summary>回答を表示</summary>

**回答: C) インストールにより、すべての権限、スコープ、接続性に関する前提条件が不要になる。**

自動検出によって、インストール権限、サポート対象ランタイムの要件、egress、トークン設定、インジェクションの選択、データプライバシーに関する判断が不要になるわけではありません。また、すべてのメソッドまたはリクエストがキャプチャされることも保証しません。

</details>

---

2. Kubernetes で DynaKube リソースと Dynatrace ワークロードを管理するコンポーネントはどれですか？
   - A) スタンドアロンの kubectl バイナリ。
   - B) Dynatrace Operator。
   - C) OneAgent プロセスのみ。
   - D) 自動作成される Lambda 関数。

<details>
<summary>回答を表示</summary>

**回答: B) Dynatrace Operator。**

Helm または manifest によって Operator をインストールしますが、これらは競合する監視モードではありません。確認した Operator/chart は 1.10.2 です。リリースされた CRD は v1beta5 と v1beta6 を提供し、ストレージには v1beta6 を使用します。古い v1beta2 の例は現在提供されている API ではありません。コンポーネントのバージョンと更新時の動作は引き続き確認が必要です。

</details>

---

3. 問題検出と根本原因分析を有効にすることで、暗黙的に得られるわけではない結果はどれですか？
   - A) ベースラインと異常の分析。
   - B) トポロジーを考慮した調査。
   - C) 未レビューの本番コード変更が自動的に承認される。
   - D) 収集したエビデンスを使用した影響分析。

<details>
<summary>回答を表示</summary>

**回答: C) 未レビューの本番コード変更が自動的に承認される。**

Davis という用語は古い資料に残っていますが、現在のドキュメントでは Dynatrace Intelligence を使用しています。Preview 機能を含め、承認済みのエージェント型アクションやワークフローを設定できます。そのため、「AI は決してアクションを実行できない」という表現も広すぎます。検出だけでは修復の権限は付与されず、診断が正しいことも証明されません。

</details>

---

4. cloudNativeFullStack は何を組み合わせますか？
   - A) Windows の監視のみ。
   - B) ホスト監視と webhook ベースのアプリケーションコードモジュールインジェクション。
   - C) ホストコンポーネントを持たないアプリケーションのみの監視。
   - D) すべてのワークロードでオーバーヘッドが低くなるという保証。

<details>
<summary>回答を表示</summary>

**回答: B) ホスト監視と webhook ベースのアプリケーションコードモジュールインジェクション。**

リリースされた Operator では、cloudNativeFullStack は hostMonitoring と applicationMonitoring を組み合わせ、CSI インフラストラクチャを使用するものとして説明されています。これは単なるアプリケーション sidecar ではありません。確認したリリースには classicFullStack が引き続き存在するため、削除されたと表現してはいけません。適合性はモード、OS、CSI の権限によって決まります。

</details>

---

5. PurePath に関連する機能はどれですか？
   - A) ログ圧縮。
   - B) サポート対象のコードレベルコンテキストを含む分散トレーシング。
   - C) 汎用的なパケットキャプチャアプライアンス。
   - D) データベースバックアップ。

<details>
<summary>回答を表示</summary>

**回答: B) サポート対象のコードレベルコンテキストを含む分散トレーシング。**

トレースとコードの可視性は、サポート対象のテクノロジー、インストルメンテーション、キャプチャ/サンプリング設定、利用可能なテレメトリに依存します。「完全なパス」は、すべてのリクエスト、メソッド、または非同期関係が保持されていることの証明ではありません。

</details>

---

6. 現在の DPS のホストベース Full-Stack Monitoring では、どの測定単位を使用しますか？
   - A) vCPU と RAM。
   - B) 適用される rate card に基づく、監視対象メモリの GiB 時間。
   - C) max(RAM/16, vCPU/1.5) Host Units。
   - D) Kubernetes namespace ごとに一律 1 ユニット。

<details>
<summary>回答を表示</summary>

**回答: B) 適用される rate card に基づく、監視対象メモリの GiB 時間。**

ベンダーは、15 分間の課金間隔、RAM の 0.25 GiB 単位での切り上げ、およびホストあたり最低 4 GiB を文書化しています。コンテナベースのアプリケーションのみの監視には、異なるメモリ/最小値ルールがあります。古い CPU/RAM の最大値計算式は、現在の DPS 計算ではありません。使用量の算術計算は請求書ではありません。コミットメント、rate card、allowance、個別に課金される機能が重要です。

</details>

---

7. ActiveGate の役割ではないものはどれですか？
   - A) テレメトリをルーティングする。
   - B) 設定された Kubernetes API 監視。
   - C) 長期分析用データ lakehouse として機能する。
   - D) 環境への承認済み接続パスを提供する。

<details>
<summary>回答を表示</summary>

**回答: C) 長期分析用データ lakehouse として機能する。**

ルーティング/監視とローカルバッファリングは、長期的なバックエンドストレージとは異なります。一部のコンテナ化された ActiveGate インジェスト設定では PVC が必要です。SaaS への経路には引き続き接続性が必要です。プロキシがあっても、完全に切断されたネットワークが SaaS に到達できるようになるわけではありません。

</details>

---

8. oneAgent.cloudNativeFullStack.namespaceSelector は何を選択しますか？
   - A) 作成する namespace。
   - B) 設定済み webhook インジェクションの対象となる namespace。
   - C) ネットワーク分離の境界。
   - D) ホストおよび Kubernetes API 監視の完全なスコープ。

<details>
<summary>回答を表示</summary>

**回答: B) 設定済み webhook インジェクションの対象となる namespace。**

selector と Pod インジェクションアノテーションは webhook インジェクションを制御します。これらは OneAgent のホスト監視や ActiveGate の Kubernetes API 監視を制限しません。メタデータのエンリッチメントと OTLP exporter の自動設定には、それぞれ独自の selector があります。ラベルと DynaKube 更新権限を保護してください。selector は RBAC でも課金上限でもありません。

</details>

---

9. 文書化されているネイティブ Dynatrace SaaS/ActiveGate OTLP API が受け入れるトランスポートはどれですか？
   - A) gRPC のみ。
   - B) バイナリ Protocol Buffers を使用する HTTP。
   - C) gRPC と HTTP/JSON のいずれも同等に使用可能。
   - D) 独自の非 OTLP 形式のみ。

<details>
<summary>回答を表示</summary>

**回答: B) バイナリ Protocol Buffers を使用する HTTP。**

ネイティブ endpoint は HTTP/protobuf をサポートしますが、gRPC や protobuf JSON はサポートしません。Collector は gRPC を受け入れ、HTTP で Dynatrace にエクスポートできます。正しい /api/v2/otlp base と signal suffix、TLS、および選択した endpoint に必要なトークンタイプ/scopes を使用してください。.apps のブラウザ URL を代用してはいけません。

</details>

---

10. Smartscape は何を提供しますか？
   - A) 汎用的なアラート無効化スイッチ。
   - B) 観測データに基づくトポロジーと依存関係のマッピング。
   - C) スケーリングの自動承認。
   - D) ソースコードレビュー。

<details>
<summary>回答を表示</summary>

**回答: B) 観測データに基づくトポロジーと依存関係のマッピング。**

依存関係グラフは、影響分析と調査を支援します。そのカバレッジは監視対象のテクノロジーとテレメトリに依存します。関係性の欠落やデータギャップを、依存関係が存在しないことの証明として扱ってはいけません。

</details>

---

[ガイドに戻る](../../../observability/tracing/04-dynatrace.md)

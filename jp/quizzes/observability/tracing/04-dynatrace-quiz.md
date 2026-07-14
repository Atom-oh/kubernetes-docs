# Dynatrace クイズ

Dynatrace についての理解度を確認しましょう。

---

1. Dynatrace のコア技術である OneAgent の特性ではないものはどれですか？
   - A) 単一エージェントによるフルスタック監視
   - B) 自動コードインストルメンテーション
   - C) 手動設定が必要
   - D) 自動プロセス検出

<details>
<summary>回答を表示</summary>

**回答: C) 手動設定が必要**

**解説:**
OneAgent の主な特性は、自動検出と自動インストルメンテーションです。インストール後、追加の手動設定なしで、ホスト上のプロセス、Service、アプリケーションを自動的に検出して監視します。これは Dynatrace の「ゼロコンフィギュレーション」という理念を反映しています。

</details>

---

2. EKS で Dynatrace をデプロイする推奨方法は何ですか？
   - A) kubectl apply を使用して直接デプロイする
   - B) Dynatrace Operator を使用する
   - C) Helm で OneAgent のみをデプロイする
   - D) Lambda 関数でデプロイする

<details>
<summary>回答を表示</summary>

**回答: B) Dynatrace Operator を使用する**

**解説:**
Dynatrace Operator は、Kubernetes 環境内の Dynatrace コンポーネント（OneAgent、ActiveGate など）のライフサイクルを自動的に管理します。DynaKube CR を通じて宣言的に設定でき、自動更新、ローリングデプロイメント、ステータス監視を提供します。

</details>

---

3. Davis AI エンジンの主な機能ではないものはどれですか？
   - A) 自動ベースライン学習
   - B) 異常検出
   - C) 自動コード修正
   - D) 根本原因分析

<details>
<summary>回答を表示</summary>

**回答: C) 自動コード修正**

**解説:**
Davis AI はベースラインを自動的に学習し、異常を検出して問題の根本原因を分析します。ただし、コードを自動的に修正することはありません。Davis は問題を診断して解決の方向性を提案しますが、実際のコード修正は開発者が行う必要があります。

</details>

---

4. Dynatrace における Cloud Native Full Stack と Classic Full Stack のデプロイモードの違いは何ですか？
   - A) Cloud Native は Windows のみをサポートする
   - B) Cloud Native はコードモジュールのインジェクションを使用する
   - C) Classic はクラウド環境では使用できない
   - D) 両モードは同一の機能を提供する

<details>
<summary>回答を表示</summary>

**回答: B) Cloud Native はコードモジュールのインジェクションを使用する**

**解説:**
Cloud Native Full Stack は、CSI Driver を通じて Pod にコードモジュールをインジェクトする軽量なアプローチです。Classic Full Stack は、DaemonSet として各ノードに完全な OneAgent をデプロイします。Cloud Native はリソース使用量が少なく、Pod レベルで細かな制御が可能ですが、ホストレベルの監視には制限があります。

</details>

---

5. Dynatrace の PurePath テクノロジーはどのような機能を提供しますか？
   - A) ログ圧縮
   - B) コードレベルの分散トレーシング
   - C) ネットワークパケットキャプチャ
   - D) データベースバックアップ

<details>
<summary>回答を表示</summary>

**回答: B) コードレベルの分散トレーシング**

**解説:**
PurePath は Dynatrace 独自の分散トレーシング技術で、システムを通過するリクエストの完全な経路をコードレベルまで追跡します。Service 間の呼び出しだけでなく、各 Service 内のメソッド呼び出し、データベースクエリ、外部 API 呼び出しも詳細に記録します。

</details>

---

6. Dynatrace Host Units の計算式として正しいものはどれですか？
   - A) vCPU + Memory(GB)
   - B) max(Memory(GB) / 16, vCPU / 1.5)
   - C) vCPU * Memory(GB) / 100
   - D) (vCPU + Memory(GB)) / 2

<details>
<summary>回答を表示</summary>

**回答: B) max(Memory(GB) / 16, vCPU / 1.5)**

**解説:**
Dynatrace Host Units は、メモリと CPU のうち大きい方に基づいて計算されます。メモリ 16GB または 1.5 vCPU が 1 Host Unit に相当します。たとえば、8 vCPU と 32GB RAM を持つホストは max(2, 5.33) = 5.33 Host Units です。

</details>

---

7. Dynatrace ActiveGate の役割ではないものはどれですか？
   - A) データルーティング
   - B) Kubernetes API 監視
   - C) 長期データ保存
   - D) ネットワークゾーン分離

<details>
<summary>回答を表示</summary>

**回答: C) 長期データ保存**

**解説:**
ActiveGate は、OneAgent と Dynatrace SaaS 間のデータルーティング、Kubernetes API 監視、およびエアギャップ環境におけるプロキシの役割を担います。長期データ保存は Dynatrace の Grail データレイクハウスが処理します。ActiveGate はデータを保存せず、転送のみを行います。

</details>

---

8. Dynatrace で namespaceSelector を使用する目的は何ですか？
   - A) namespace を作成する
   - B) 特定の namespace のみを監視する
   - C) namespace 間の通信をブロックする
   - D) リソースクォータを設定する

<details>
<summary>回答を表示</summary>

**回答: B) 特定の namespace のみを監視する**

**解説:**
DynaKube CR で namespaceSelector を使用すると、特定のラベルを持つ namespace のみを監視対象として指定できます。これにより、本番環境のみを監視したり、特定チームの namespace を選択的に監視したりして、コストを最適化できます。

</details>

---

9. Dynatrace を OpenTelemetry と統合する際に使用されるプロトコルは何ですか？
   - A) gRPC のみをサポートする
   - B) HTTP のみをサポートする
   - C) OTLP (gRPC and HTTP)
   - D) 独自プロトコルのみをサポートする

<details>
<summary>回答を表示</summary>

**回答: C) OTLP (gRPC and HTTP)**

**解説:**
Dynatrace は OpenTelemetry Protocol (OTLP) をネイティブにサポートしています。OTEL Collector の otlphttp exporter を使用すると、トレース、メトリクス、ログを Dynatrace API エンドポイントへ送信できます。gRPC と HTTP の両方がサポートされています。

</details>

---

10. Dynatrace の Smartscape はどのような機能を提供しますか？
    - A) スマートアラートフィルタリング
    - B) リアルタイムトポロジーマッピング
    - C) オートスケーリング
    - D) コードレビュー

<details>
<summary>回答を表示</summary>

**回答: B) リアルタイムトポロジーマッピング**

**解説:**
Smartscape は Dynatrace のリアルタイムトポロジーマッピング技術です。インフラストラクチャ（ホスト、コンテナ）、プロセス、Service、アプリケーション間の関係を自動的に検出して可視化します。これにより、システムの依存関係を理解し、問題の影響範囲を特定できます。

</details>

---

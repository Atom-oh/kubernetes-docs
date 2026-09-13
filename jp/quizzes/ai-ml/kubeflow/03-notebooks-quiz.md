# Kubeflow Notebooks クイズ

ベースライン: Notebooks 1.11.0 / Community Distribution 26.03.1。

## 選択問題

1. Notebook controller は何を reconcile しますか？

   - A) ユーザーのノートPC上のブラウザープロセス
   - B) Notebook CR から生成される StatefulSet、Service、および設定済みのルーティングリソース
   - C) ユーザーごとの EC2 インスタンス
   - D) HTML ダッシュボードのみ

<details>
<summary>回答を表示</summary>

**回答: B) Notebook CR から生成される StatefulSet、Service、および設定済みのルーティングリソース**

StatefulSet controller が Pod を作成し、Kubernetes がそれらをスケジュールします。ダッシュボードは UI のエントリポイントです。
</details>

2. ここでの正確なバージョンベースラインは何ですか？

   - A) すべてのコンポーネントが Workspaces GA である
   - B) Notebooks v1.11.0。26.03.1 では Workspaces は beta とされ、そのイメージは v2.0.0-alpha.3 である
   - C) Notebook と Workspace は同一の API である
   - D) この章では v1 のサポート終了日が確定している

<details>
<summary>回答を表示</summary>

**回答: B) Notebooks v1.11.0。26.03.1 では Workspaces は beta とされ、そのイメージは v2.0.0-alpha.3 である**

リリース説明とイメージタグは異なります。GA や v1 の廃止日を推測するのではなく、実際の API および移行サポートを確認してください。
</details>

3. Profile はすべての notebook を他のすべてのユーザーから自動的に分離しますか？

   - A) はい。AWS とストレージも含みます
   - B) いいえ。Profile は共有でき、ネットワーク、ストレージ、IAM、およびアプリケーション認可は別途考慮する必要があります
   - C) はい。namespace がネットワークパケットをブロックするためです
   - D) はい。RBAC が無関係なすべての権限付与を無効にするためです

<details>
<summary>回答を表示</summary>

**回答: B) いいえ。Profile は共有でき、ネットワーク、ストレージ、IAM、およびアプリケーション認可は別途考慮する必要があります**

完全な UI は Profile namespace を選択します。Notebook CRD 自体は、すべての namespace で Profile オブジェクトを必要としません。
</details>

4. notebook Pod が置き換えられた場合、何が保持されますか？

   - A) すべてのプロセスメモリ
   - B) コンテナ内のどこかにインストールされたすべてのパッケージ
   - C) 保持された永続ボリューム上のデータ。コンテナレイヤーのパッケージとカーネルメモリは保持されない
   - D) 接続されているすべての EC2 インスタンス

<details>
<summary>回答を表示</summary>

**回答: C) 保持された永続ボリューム上のデータ。コンテナレイヤーのパッケージとカーネルメモリは保持されない**

マウント場所、PVC/volume のライフサイクル、およびバックアップを確認してください。ReadWriteOnce は単一ノードアクセスモードであり、単一 Pod を保証するものではありません。
</details>

5. 確認された idle-culling のデフォルト値は何ですか？

   - A) 有効で、アイドルしきい値は 1 分
   - B) 無効。アイドルしきい値は 1440 分、チェック間隔は 1 分
   - C) すべての RStudio および shell プロセスで有効
   - D) GPU notebook でのみ無効

<details>
<summary>回答を表示</summary>

**回答: B) 無効。アイドルしきい値は 1440 分、チェック間隔は 1 分**

culler は Jupyter kernel のアクティビティを使用します。失敗した、または空の API 結果では古いアクティビティが変わらず、停止につながる可能性があります。実際のイメージとアクセスパスをテストしてください。
</details>

6. v1.11.0 では、停止した Notebook はどのように表現されますか？

   - A) spec.replicas: 0
   - B) kubeflow-resource-stopped の存在。controller が StatefulSet replicas をゼロに設定する
   - C) annotation の値 false は実行中を意味する
   - D) その PVC を削除する

<details>
<summary>回答を表示</summary>

**回答: B) kubeflow-resource-stopped の存在。controller が StatefulSet replicas をゼロに設定する**

NotebookSpec には replicas フィールドがありません。annotation を削除して再開します。false という文字列であっても、存在していると見なされます。
</details>

7. カスタムイメージの digest は何を保証しますか？

   - A) すべてのユーザーが同一の完全なランタイム環境を持つこと
   - B) 参照されるイメージコンテンツ。マウントされたデータとランタイムの変更は依然として異なる可能性がある
   - C) すべての GPU driver との自動的な互換性
   - D) UI のイメージ制限を API 経由で回避できないこと

<details>
<summary>回答を表示</summary>

**回答: B) 参照されるイメージコンテンツ。マウントされたデータとランタイムの変更は依然として異なる可能性がある**

テスト済みの server-prefix/port/UID の動作、依存関係、およびアーキテクチャを使用してください。mutable tag だけではイメージバイトを固定できません。
</details>

## 短答問題

8. idle 状態の GPU notebook を停止しても、即時のコスト削減が保証されないのはなぜですか？

<details>
<summary>回答を表示</summary>

Pod requests は解放される可能性がありますが、他の workload、PDB、NodePool の制限/中断ポリシー、およびキャパシティ管理がノード終了に影響します。ノードが実行中のままであれば、EC2 の料金は継続する可能性があります。
</details>

9. notebook において、RBAC、Istio authorization、および NetworkPolicy はどのように異なりますか？

<details>
<summary>回答を表示</summary>

RBAC は Kubernetes API アクションを管理します。Istio authorization は、設定された proxy とポリシーで処理されるリクエストを制御します。NetworkPolicy は、CNI により適用される場合に許可される Pod ネットワークトラフィックを管理します。これらのいずれも単独では、ストレージ/IAM/アプリケーションの分離を保証しません。
</details>

---

[学習教材に戻る](../../../ai-ml/kubeflow/03-notebooks.md)

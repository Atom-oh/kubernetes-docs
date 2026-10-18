# EKS 上の AI インフラストラクチャクイズ

現行 API と運用上の境界に関する 15 問です。

## 1. JARK とは何であり、それだけで必要な構成がそろいますか？

<details>
<summary>回答と解説</summary>

JupyterHub/Argo Workflows/Ray/Karpenter を組み合わせる統合パターンです。ID、ジョブ投入、実行、Pod の配置、ノードの供給、ストレージ、認可を明示的に接続してください。
</details>

## 2. Cognito を使用する JupyterHub では何を設定する必要がありますか？

<details>
<summary>回答と解説</summary>

callback/token/userInfo の URL、scope、安定した username claim、許可ポリシーを設定します。client secret は事前に用意したファイルから読み取ります。MFA/federation はプロバイダー側で別途設定します。認証に成功しても、あらゆるアクセスが許可されるわけではありません。
</details>

## 3. Ray head と Karpenter の役割は何ですか？

<details>
<summary>回答と解説</summary>

GCS は Global Control Service で、スケジューリングは raylet と連携します。CPU リソースを申告している head は、処理を実行する場合があります。Karpenter は worker Pod の需要と Kubernetes のスケジューリング状態に基づいてノードをプロビジョニングします。
</details>

## 4. DRA と device plugin はどのように比較すべきですか？

<details>
<summary>回答と解説</summary>

DRA は DeviceClass/ResourceSlice/ResourceClaim を通じて、構造化された要求、属性、割り当てを提供します。デバイスプラグインも MIG/time-slicing に対応しており、常に排他的な割り当てに限られるわけではありません。利用できる機能はドライバー、ハードウェア、機能ゲートに依存します。
</details>

## 5. MIG profile と isolation について重要な点は何ですか？

<details>
<summary>回答と解説</summary>

3g.20gb は 1 つのプロファイルを表し、20 GB のデバイス 3 基を意味するものではありません。MIG はハードウェアを分割しますが、ホスト、ドライバー、認可による分離の代わりにはなりません。MPS/time-slicing もセキュリティ境界ではありません。
</details>

## 6. 単一の GPU Operator バージョンですべての DRA サポートを確立できますか？

<details>
<summary>回答と解説</summary>

いいえ。Kubernetes API、ドライバー/ハードウェア/CDI、および個別の機能ゲートを確認してください。Operator 26.7 の GPUCluster は ClusterPolicy と併用できません。standalone 0.5 には、デバイスプラグインとの競合を防ぐ opt-in のガードがあります。
</details>

## 7. Langfuse を統合する際には何を確認すべきですか？

<details>
<summary>回答と解説</summary>

現行 SDK/backend の依存関係、DB/ClickHouse/オブジェクトストレージ、ファイルから読み込む認証情報、トレース、機微データの保持期間を確認してください。古い 2.x の Deployment や trace() の呼び出しは、現行 4.x の API ではありません。
</details>

## 8. EFS、FSx、Mountpoint はどのように選択すべきですか？

<details>
<summary>回答と解説</summary>

I/O、認可、名前空間/PVC のスコープ、容量、ファイルシステムの動作を比較してください。EFS のリクエスト値はクォータではありません。Mountpoint CSI 2.8 は既存のバケットに静的 PV を使用し、POSIX に完全準拠しているわけではありません。
</details>

## 9. EFA の帯域幅と interface 数はどのように解釈すべきですか？

<details>
<summary>回答と解説</summary>

インスタンス全体の集約帯域幅とインターフェイスごとの値を区別し、すでに集約された数値を重ねて乗算しないでください。同一 AZ への配置、インターフェイス、ドライバー/libfabric/NCCL、セキュリティグループ、Pod のリソースを確認してください。RAID0 を構成しても EFA は有効になりません。
</details>

## 10. GPU memory と XID の metric はどのように解釈すべきですか？

<details>
<summary>回答と解説</summary>

FB_USED/FREE は MiB 単位のゲージです。使用率が高くても、必ずしも OOM とは限りません。XID_ERRORS は最後のコードを示すゲージであり、increase() を適用するカウンターではありません。実際のエラー、キャッシュ、割り当ての失敗、デバイス固有の上限を調べてください。
</details>

## 11. Karpenter の consolidation は GPU 使用率の metric を直接使用しますか？

<details>
<summary>回答と解説</summary>

DCGM の使用率 20% といったしきい値ではなく、ワークロードのリクエスト、スケジューリングの可否、価格、中断に関する制約に基づいて動作します。上限や予算はコストや障害に対する絶対的な保証ではありません。終了と復旧の動作を検証してください。
</details>

## 12. ResourceSlice は誰が publish し、何を表しますか？

<details>
<summary>回答と解説</summary>

ドライバーが、型付きの属性/容量を持つ実際のデバイス在庫を公開します。任意の ResourceSlice を作成しても GPU が作られるわけではありません。CEL と matchAttribute は実際に公開されたスキーマに合わせる必要があります。
</details>

## 13. Milvus のために GPU をリクエストすれば RAG は完成しますか？

<details>
<summary>回答と解説</summary>

いいえ。サポートされるイメージ/インデックス、埋め込みの次元数/リビジョン、検索距離の尺度/パラメーター、テナントのフィルタリング、更新/削除のライフサイクルを整合させてください。検索結果への認可を検証し、根拠が得られない場合の扱いも考慮してください。
</details>

## 14. pending 状態の GPU Pod と node の障害はどのように調査すべきですか？

<details>
<summary>回答と解説</summary>

GPU を要求して pending になっている Pod の数だけでは、原因を診断できません。イベント、PVC、アフィニティ、taint、クォータ、claim、イメージを確認し、チェックポイントからの再開をテストしてください。GPU を要求するコンテナが複数あっても、Pod ごとに 1 件として数えます。
</details>

## 15. MCP は標準的な Kubernetes 自動検出 gateway を提供しますか？

<details>
<summary>回答と解説</summary>

いいえ。MCP はツールの一覧取得や呼び出しなどの操作を定義します。実在する server/gateway のリリース、通信方式、認可設計を選んでください。存在しないイメージ/ラベル/設定や URL の環境変数だけでは、自動検出や実行は実装されません。
</details>

[ガイドに戻る](../../ai-ml/06-ai-infrastructure.md)

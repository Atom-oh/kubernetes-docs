# EKS 上の AI Infrastructure クイズ

現在の API と運用上の境界に関する15問です。

## 1. JARK とは何であり、自動的に完成するものですか？

<details>
<summary>回答と解説</summary>

JupyterHub/Argo Workflows/Ray/Karpenter の統合パターンです。identity、submission、実行、Pod の配置、node の供給、storage、authorization を明示的に接続してください。
</details>

## 2. Cognito を使用する JupyterHub では何を設定する必要がありますか？

<details>
<summary>回答と解説</summary>

callback/token/userInfo の URL、scope、安定した username claim、そして allow policy です。client secret は事前に用意したファイルから読み取ります。MFA/federation は provider 側で個別に設定します。認証が成功したことは、あらゆるアクセスが許可されることを意味しません。
</details>

## 3. Ray head と Karpenter の役割は何ですか？

<details>
<summary>回答と解説</summary>

GCS は Global Control Service であり、scheduling は raylet と連携します。CPU を広告している head は work を実行する場合があります。Karpenter は worker Pod の需要と Kubernetes の scheduling 状態に基づいて node を provision します。
</details>

## 4. DRA と device plugin はどのように比較すべきですか？

<details>
<summary>回答と解説</summary>

DRA は DeviceClass/ResourceSlice/ResourceClaim を通じて構造化されたリクエスト、attribute、割り当てを提供します。device plugin も MIG/time-slicing をサポートしており、常に排他的な利用のみに限られるわけではありません。機能は driver、hardware、gate に依存します。
</details>

## 5. MIG profile と isolation について重要な点は何ですか？

<details>
<summary>回答と解説</summary>

3g.20gb は1つの profile を表しており、3 個の 20GB デバイスではありません。MIG は hardware を分割しますが、host/driver/authorization の isolation を置き換えるものではありません。MPS/time-slicing は security boundary ではありません。
</details>

## 6. 単一の GPU Operator バージョンですべての DRA サポートを確立できますか？

<details>
<summary>回答と解説</summary>

いいえ。Kubernetes API、driver/hardware/CDI、および個々の gate を確認してください。Operator26.7 の GPUCluster は ClusterPolicy と相互排他であり、standalone0.5 には device plugin との衝突に対する opt-in のガードがあります。
</details>

## 7. Langfuse を統合する際には何を確認すべきですか？

<details>
<summary>回答と解説</summary>

現在の SDK/backend の依存関係、DB/ClickHouse/object storage、ファイルによる credential、tracing、機微データの保持期間を検証してください。古い2.x の Deployment や trace() の呼び出しは、現在の4.x API ではありません。
</details>

## 8. EFS、FSx、Mountpoint はどのように選択すべきですか？

<details>
<summary>回答と解説</summary>

I/O、authorization、namespace/PVC のスコープ、容量、filesystem のセマンティクスを比較してください。EFS のリクエストは quota ではありません。Mountpoint CSI2.8 は既存の bucket に対して static PV を使用し、完全な POSIX 準拠ではありません。
</details>

## 9. EFA の帯域幅と interface 数はどのように解釈すべきですか？

<details>
<summary>回答と解説</summary>

インスタンス全体の集約帯域幅と interface あたりの値を区別してください。すでに集約された数値を乗算しないでください。同一 AZ への配置、interface、driver/libfabric/NCCL、security group、Pod の resource を検証してください。RAID0 は EFA を有効にしません。
</details>

## 10. GPU memory と XID の metric はどのように解釈すべきですか？

<details>
<summary>回答と解説</summary>

FB_USED/FREE は MiB 単位の gauge であり、比率が高いことが必ずしも OOM を意味するわけではありません。XID_ERRORS は最後の code を示す gauge であり、increase() 用の counter ではありません。実際のエラー、cache、割り当ての失敗、デバイス固有の上限を調査してください。
</details>

## 11. Karpenter の consolidation は GPU 使用率の metric を直接使用しますか？

<details>
<summary>回答と解説</summary>

DCGM20% のしきい値ではなく、workload のリクエスト、scheduling の実行可能性、価格、disruption の制約を使用します。limit/budget は絶対的なコストや障害の保証ではありません。終了と復旧を検証してください。
</details>

## 12. ResourceSlice は誰が publish し、何を表しますか？

<details>
<summary>回答と解説</summary>

driver が型付き attribute/capacity を伴う実際のデバイス在庫を publish します。任意の slice を作成しても GPU は作成されません。CEL と matchAttribute は、実際に publish された schema に従う必要があります。
</details>

## 13. Milvus のために GPU をリクエストすれば RAG は完成しますか？

<details>
<summary>回答と解説</summary>

いいえ。サポートされる image/index、embedding の次元数/revision、metric/parameter、tenant のフィルタリング、更新/削除のライフサイクルを一致させてください。結果の authorization を検証し、根拠が存在しない場合の扱いも考慮してください。
</details>

## 14. pending 状態の GPU Pod と node の障害はどのように調査すべきですか？

<details>
<summary>回答と解説</summary>

GPU をリクエストして pending になっている Pod を数えるだけでは原因を診断できません。event、PVC、affinity、taint、quota、claim、image を確認し、checkpoint/resume をテストしてください。リクエストする container が複数あっても Pod 単位で1回として数えられます。
</details>

## 15. MCP は標準的な Kubernetes 自動検出 gateway を提供しますか？

<details>
<summary>回答と解説</summary>

いいえ。MCP は tool の一覧取得/呼び出しなどの操作を定義します。実際の server/gateway のリリース、transport、authorization の設計を選択してください。存在しない image/label/config や URL の環境変数だけでは、discovery/実行は実装されません。
</details>

[ガイドに戻る](../../ai-ml/06-ai-infrastructure.md)

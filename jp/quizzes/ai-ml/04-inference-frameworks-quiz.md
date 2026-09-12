# Inference Frameworks クイズ

現在の API と実行境界に関する15問。

## 1. NIM は何を提供し、何を検証する必要がありますか？

<details>
<summary>回答と解説</summary>

モデル/デバイス指向のコンテナとプロファイルです。NIM が常に TensorRT-LLM であるとは限りません。コンテナ/モデルのリビジョン、サポート対象デバイス、サポート契約、認証、キャッシュ、メトリクスを検証してください。
</details>

## 2. Dynamo の分離型サービングとは何ですか？

<details>
<summary>回答と解説</summary>

互換性のある KV 転送で接続された、個別の prefill ワーカーと decode ワーカーです。モデル、KV 形式、バックエンド、デバイス、ネットワークの整合性が必要です。速度またはコストの改善はワークロードに依存します。
</details>

## 3. AIBrix0.7.0 で LoRA アダプターはどのように宣言しますか？

<details>
<summary>回答と解説</summary>

baseModel、podSelector、artifactURL を含む ModelAdapter を使用します。replicas を省略すると一致するすべての Pod、1 の場合は 1 つの Pod になります。その他の値はサポートされていません。アダプター名によってテナントが認証されるわけではありません。
</details>

## 4. Kubernetes 上で Ray Serve を動作させるコントローラーとスケーリングレイヤーはどれですか？

<details>
<summary>回答と解説</summary>

KubeRay が Ray リソースを調整し、Ray autoscaling がワーカーを、Serve autoscaling がサービングレプリカを調整します。RayCluster を通常の Deployment HPA ターゲットとして扱わないでください。
</details>

## 5. Inf2 のコストとハードウェアはどのように評価すべきですか？

<details>
<summary>回答と解説</summary>

同一のモデル、SLO、成功スループット、日付付き価格を測定します。各チップには2コア/32GiB HBM があります。inf2.24xlarge には6チップ/12コア/192GiB HBM、48xlarge には12/24/384GiB があります。ホスト RAM は別です。
</details>

## 6. TTFT、ITL、エンドツーエンドレイテンシーはどのように異なりますか？

<details>
<summary>回答と解説</summary>

TTFT は最初のトークンまでの時間を、ITL は後続トークン間の間隔を測定します。一様間隔の近似は、TTFT+(出力トークン数-1)×ITL に別途オーバーヘッドを加えたものです。ワークロード固有の SLO と実際の単位を使用してください。
</details>

## 7. Dynamo の KV 対応ルーティングは何を考慮しますか？

<details>
<summary>回答と解説</summary>

キャッシュの局所性とワーカーの負荷です。固定の0.7/0.3 の式または decode 専用キャッシュという前提は普遍的ではありません。実際のバックエンドとルーティングポリシーを確認してください。
</details>

## 8. Neuron device plugin をインストールする前に何を確認すべきですか？

<details>
<summary>回答と解説</summary>

固定された公式 chart をレンダリングし、ドライバー、RBAC/hostPaths、有効化されたコンポーネント、実際の DaemonSet を確認します。neuron はデバイス全体を割り当て、neuroncore はコアを割り当てます。
</details>

## 9. AIBrix autoscaler の設定形式はどのようなものですか？

<details>
<summary>回答と解説</summary>

PodAutoscaler は scaleTargetRef、metricsSources、HPA/KPA/APA 戦略を使用します。コントローラーと実際のメトリクスソースが必要です。ConfigMap または GPU リクエストだけではワークロードはスケールしません。
</details>

## 10. NGC/プロファイルの役割と認証情報の境界とは何ですか？

<details>
<summary>回答と解説</summary>

サポート対象のモデル、イメージ、プロファイルを特定します。NIM_MODEL_PROFILE には実際のプロファイル ID/名前を使用する必要があります。イメージプル用の認証情報と実行時ダウンロード用の認証情報を区別してください。Secret の環境変数による提供は、ファイルのみのポリシーを満たしません。
</details>

## 11. 複数バックエンドのサポートは任意の組み合わせを意味しますか？

<details>
<summary>回答と解説</summary>

いいえ。選択した vLLM/SGLang/TensorRT-LLM、デバイス、コネクター、モデル、KV 形式を検証してください。モデル名が一致するだけでは、prefill/decode の相互運用性は確立されません。
</details>

## 12. モデルキャッシュはどのように選択すべきですか？

<details>
<summary>回答と解説</summary>

サイズ、リビジョン、再起動/ダウンロードの同時実行性、認可、コストを用いて local/EBS/EFS/FSx を比較します。1 つの RWO EBS PVC をノード間で共有しないでください。特定の制約下では、モデルをイメージに埋め込むことが適切な場合があります。
</details>

## 13. GenAI-Perf コマンドと結果で重要なことは何ですか？

<details>
<summary>回答と解説</summary>

バージョン0.0.16 では profile と synthetic-input-tokens-mean/output-tokens-mean を使用します。analyze は追加のスイープロードを実行できます。生の結果、失敗、ウォームアップ、トークナイザーを保持してください。GPU 使用率には設定済みの収集が必要です。
</details>

## 14. StatefulSet だけで分散 vLLM を実装できますか？

<details>
<summary>回答と解説</summary>

いいえ。安定した名前は役立つことがありますが、ランク、rendezvous、TP/PP、モデル、通信には明示的な設定が必要です。順序付き Ready 状態によるデッドロックを確認してください。ほかのコントローラーが適切な場合もあります。
</details>

## 15. NEURON_RT_VISIBLE_CORES は Kubernetes の割り当てとどのように関係しますか？

<details>
<summary>回答と解説</summary>

これはランタイムコアを選択するものであり、未割り当てのデバイスを作成するものではありません。inf2.xlarge には 1 つのデバイスしかないため、neuron:2 はスケジュールできません。Inf2 向けの SDK2.32 NxD と、新しい Trn2/3 beta パスを区別してください。
</details>

[ガイドに戻る](../../ai-ml/04-inference-frameworks.md)

# Ray Serve クイズ

このクイズでは、Ray Serve の Deployment モデル、Ray Serve LLM、Serve レベルの autoscaling、GPU inference、および RayService が EKS 上の本番 Serve application をどのように管理するかについての理解度を確認します。

## 多肢選択問題

1. Ray Serve の routing layer の基盤となる Ray Serve Deployment は、何として実装されていますか？
   - A) Ray のコアプリミティブとは無関係なスタンドアロン container
   - B) Ray actor、または Ray Serve が HTTP/gRPC リクエストをルーティングする actor replica のグループ
   - C) 固定スケジュールで実行される Kubernetes CronJob
   - D) 到着するリクエストごとに再実行される単一の Ray task

<details>

<summary>回答を表示</summary>

**回答: B) Ray actor、または Ray Serve が HTTP/gRPC リクエストをルーティングする actor replica のグループ**

**解説:**
Ray Serve は Ray の actor プリミティブに直接構築されています。Deployment は 1 つの actor または actor replica のグループであり、Ray Serve は受信した HTTP/gRPC リクエストをそれらの replica にルーティングします。そのため、replica のメモリに一度ロードされた model は、再ロードせずに多数のリクエストに応答できます。
</details>

2. Ray Serve の用語で「application」とは何ですか？
   - A) scale する機能がない単一の Deployment
   - B) 前処理 Deployment が model-inference Deployment に入力を渡す場合のように、serving pipeline を形成する 1 つ以上の組み合わせた Deployment
   - C) 一度実行されて自身を削除する RayJob
   - D) RayCluster が実行される Kubernetes namespace

<details>

<summary>回答を表示</summary>

**回答: B) 前処理 Deployment が model-inference Deployment に入力を渡す場合のように、serving pipeline を形成する 1 つ以上の組み合わせた Deployment**

**解説:**
Ray Serve では、複数の Deployment を組み合わせて、application と呼ばれる 1 つの serving pipeline を構成できます。たとえば、前処理ステップがその出力を model-inference ステップに渡します。その pipeline 内の各 Deployment は、引き続き独立して scale、version 管理、resource 割り当てを行えます。
</details>

3. `ray.serve.llm` とは何ですか？また、サポート対象の inference engine としてどれを文書化していますか？
   - A) LLM とは無関係の汎用 batch-processing module。任意の engine をサポートする
   - B) Ray Serve の一般的な Deployment モデル上に構築された、LLM serving 用の専用 building block 群。サポート対象の inference engine として vLLM を文書化している
   - C) actor を使用しない Ray Serve の代替
   - D) LLM の serving ではなく training 専用の module

<details>

<summary>回答を表示</summary>

**回答: B) Ray Serve の一般的な Deployment モデル上に構築された、LLM serving 用の専用 building block 群。サポート対象の inference engine として vLLM を文書化している**

**解説:**
`ray.serve.llm` は、Ray Serve の一般的な Deployment モデルの上に配置された、LLM serving パターン向けの高レベルな構成要素を提供します。サポート対象の inference engine として vLLM を文書化しており、vLLM 自身の OpenAI-compatible server と密接に整合するよう設計された OpenAI-compatible API を提供します。
</details>

4. Ray Serve 独自の autoscaler は何を決定し、その決定のために何を比較しますか？
   - A) 請求データに基づいて Karpenter が provision すべき EC2 node の数
   - B) 継続中の replica あたりのリクエスト数（queue 内と in-flight の合計）を target value と比較して、特定の Deployment に必要な actor replica 数
   - C) pending task の配置に基づいて RayCluster に必要な worker Pod 数
   - D) RayCluster をデプロイする AWS region

<details>

<summary>回答を表示</summary>

**回答: B) 継続中の replica あたりのリクエスト数（queue 内と in-flight の合計）を target value と比較して、特定の Deployment に必要な actor replica 数**

**解説:**
Ray Serve の autoscaler は、cluster レベルの autoscaling とは別の layer です。replica あたりの継続中のリクエスト数を target と比較し、設定された minimum と maximum の範囲内で、その Deployment の replica 数を scale up または scale down します。
</details>

5. EKS 上の Ray Serve application における 3 層の autoscaling 構成で、Karpenter の直接上に位置する layer はどれですか？
   - A) AWS Load Balancer Controller
   - B) pending actor の配置に基づいて worker Pod 数を決定する Ray/KubeRay autoscaler
   - C) CPU 使用率を監視する個別の Kubernetes Horizontal Pod Autoscaler
   - D) リクエストを行う client application

<details>

<summary>回答を表示</summary>

**回答: B) pending actor の配置に基づいて worker Pod 数を決定する Ray/KubeRay autoscaler**

**解説:**
3 層は次のとおりです。Ray Serve の autoscaler が replica 数を決定し、Ray/KubeRay autoscaler が pending actor の配置（Serve の autoscaler が要求した replica を含む）に基づいて worker Pod 数を決定し、Karpenter がそれらの Pod を実行する node 数を決定します。
</details>

6. GPU を使用する Ray Serve Deployment は、どのように GPU を要求しますか？
   - A) Ray Serve 専用の個別の GPU reservation API を使用する
   - B) Ray Train および Ray Tune worker と同じ、Ray の通常の actor 単位の resource request mechanism を使用する
   - C) worker node に手動で SSH 接続し、environment variable を設定する
   - D) Ray Serve Deployment は GPU をまったく要求できない

<details>

<summary>回答を表示</summary>

**回答: B) Ray Train および Ray Tune worker と同じ、Ray の通常の actor 単位の resource request mechanism を使用する**

**解説:**
GPU を必要とする model-inference Deployment は、Ray Train と Ray Tune が使用するのと同じ actor レベルの resource request mechanism を通じて GPU を要求します。また、Ray scheduler に GPU capacity を通知するのは worker group の Pod spec です。
</details>

7. Ray Serve の autoscaler が新しい GPU replica を要求したものの、既存の GPU worker Pod に配置可能な空きがない場合、何が起こりますか？
   - A) リクエストは暗黙的に破棄され、新しい replica は作成されない
   - B) replica のリクエストは pending Pod になり、その replica が traffic の serving を開始する前に、Karpenter が新しい GPU 搭載 EC2 node を provision する必要がある
   - C) Ray Serve は自動的に CPU 上で model を実行するようフォールバックする
   - D) Ray autoscaler は Karpenter を完全に迂回し、自ら EC2 instance を作成する

<details>

<summary>回答を表示</summary>

**回答: B) replica のリクエストは pending Pod になり、その replica が traffic の serving を開始する前に、Karpenter が新しい GPU 搭載 EC2 node を provision する必要がある**

**解説:**
Ray Serve の autoscaling と Karpenter の node-provisioning に要する時間は、他の GPU workload と同じように相互作用します。pending Pod が Karpenter に一致する node を provision させるため、GPU replica を積極的に scale する serving application では、その所要時間を考慮する必要があります。
</details>

8. RayService CRD は本番環境で何を管理し、具体的にどのような機能をサポートしますか？
   - A) 基盤となる RayCluster とは無関係に、Serve application のみを管理する
   - B) 基盤となる RayCluster とその上にデプロイされた Serve application をまとめて管理し、zero-downtime rolling upgrade をサポートする
   - C) 一度実行されて削除される batch job のみを管理し、serving 機能はない
   - D) upgrade できない Ray cluster の静的で変更不可能な snapshot

<details>

<summary>回答を表示</summary>

**回答: B) 基盤となる RayCluster とその上にデプロイされた Serve application をまとめて管理し、zero-downtime rolling upgrade をサポートする**

**解説:**
RayService は RayCluster とその Serve application を 1 つの unit として管理し、in-flight リクエストを失わずに新しい application version または RayCluster spec を rollout するための zero-downtime rolling upgrade をサポートする resource です。本番環境でその upgrade path に依存する前に、現在の KubeRay release note でその成熟度を確認してください。
</details>

## 短答問題

9. Ray Serve の autoscaler と Ray/KubeRay autoscaler が、それぞれ「直接下の layer しか見ない」別個の layer と説明される理由を説明してください。

<details>

<summary>回答を表示</summary>

**回答:**
Ray Serve の autoscaler は、リクエスト負荷に基づいて、特定の Deployment に必要な actor replica 数だけを決定します。新しい replica が既存の worker Pod に配置されるのか、新しい worker Pod が必要なのかについては可視性がありません。1 つ下の layer にある Ray/KubeRay autoscaler は、worker Pod 数を決定するために pending actor の配置（Serve の autoscaler が要求した replica を含む）にのみ反応し、リクエストレベルの metric は認識しません。さらに 1 つ下の layer にある Karpenter は、node 数を決定するために pending Pod にのみ反応します。

**解説:**
各 control loop は、その上の layer よりも狭い問いに答えます。layer 間は直接連携するのではなく、各 layer が生成する通常の state（replica のリクエストが pending Pod になり、pending Pod が pending node になる）を介して間接的にのみ通信します。
</details>

10. あるチームが、2 ステップの Ray Serve application（前処理、次に GPU を使用する model inference）を EKS の本番環境にデプロイしています。この document で説明した Deployment topology、autoscaling、lifecycle management が、その application にどのように組み合わさるかを説明してください。

<details>

<summary>回答を表示</summary>

**回答:**
application は、前処理 Deployment と model-inference Deployment の 2 つの Deployment で構成され、それぞれ actor replica として実装されます。前処理 Deployment の出力は inference Deployment に渡されます。各 Deployment は、自身のリクエスト負荷に基づき、Ray Serve の autoscaler を通じて独立して自身の replica 数を autoscale します。inference Deployment の actor replica は、Ray の通常の actor 単位の resource mechanism を通じて GPU を要求します。Ray Serve の autoscaler が既存の worker Pod で配置できる数を超える GPU replica を必要とする場合、Ray/KubeRay autoscaler がより多くの worker Pod を要求し、Karpenter が一致する GPU 搭載 EC2 node を provision します。本番環境では、`RayService` object が application 全体の RayCluster と Serve rollout をまとめて管理し、application または cluster spec の変更時の zero-downtime upgrade も含めて対応します。

**解説:**
これは document 内のすべての概念を結び付けています。すなわち、actor ベースの Deployment/application モデル、Serve 独自の autoscaling layer、Ray/KubeRay と Karpenter による 3 層の autoscaling 分割、GPU resource request、およびこれらすべての本番 lifecycle manager である RayService です。
</details>

---

[学習教材に戻る](../../../ai-ml/ray/04-ray-serve.md)

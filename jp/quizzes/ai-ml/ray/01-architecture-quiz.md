# Ray アーキテクチャクイズ

このクイズでは、Ray のコアプリミティブ（tasks、actors、object store）、Ray cluster アーキテクチャ（head node、worker nodes）、および Ray の高レベルライブラリが同じ基盤の上にどのように構築されているかについての理解を確認します。

## 多肢選択問題

1. Ray とは、根本的には何ですか？
   - A) 分散 model training 専用に構築されたドメイン固有のフレームワーク
   - B) 少数の汎用プリミティブを中心に構築され、Python workload をスケールさせるためのオープンソース分散コンピューティングフレームワーク
   - C) デフォルトの kube-scheduler を置き換える Kubernetes ネイティブのスケジューラ
   - D) プログラミング API を持たないマネージド model-serving 製品

<details>

<summary>回答を表示</summary>

**回答: B) 少数の汎用プリミティブを中心に構築され、Python workload をスケールさせるためのオープンソース分散コンピューティングフレームワーク**

**解説:**
Ray は、単一の workload タイプ向けに構築されたものではありません。ad hoc な並列 tasks から distributed training、hyperparameter tuning、model serving までのユースケースをサポートする、tasks、actors、object store という汎用プリミティブを提供します。
</details>

2. Ray task とは何ですか？
   - A) `@ray.remote` を class に適用して作成される、stateful で長期間存続する remote object
   - B) `@ray.remote` を function に適用して作成される、Ray がリモートで実行する stateless function
   - C) head node 上で cluster metadata を管理する process
   - D) 分散 object store の shard

<details>

<summary>回答を表示</summary>

**回答: B) `@ray.remote` を function に適用して作成される、Ray がリモートで実行する stateless function**

**解説:**
task は stateless な remote function です。呼び出すと直ちに future が返され、Ray は利用可能な capacity を持つ worker で実際の実行をスケジュールします。tasks は呼び出し間で state を保持しないため、Ray は capacity を持つ任意の worker で任意の呼び出しを実行できます。
</details>

3. actor と task の違いは何ですか？
   - A) actor は stateless であり、task は呼び出し間で state を保持する
   - B) actor は class から作成される長期間存続する stateful な remote instance であり、その state は method calls をまたいで保持される
   - C) actor は head node 上でのみ実行できる
   - D) actor は `@ray.remote` decorator で作成できない

<details>

<summary>回答を表示</summary>

**回答: B) actor は class から作成される長期間存続する stateful な remote instance であり、その state は method calls をまたいで保持される**

**解説:**
`@ray.remote` を class に適用すると、それは actor になります。Ray は作成された instance を長期間存続する remote process として保持するため、読み込み済みの model weights や counter など、そこに格納された state は stateless task とは異なり method calls をまたいで保持されます。
</details>

4. Ray の distributed object store が主に解決する問題は何ですか？
   - A) Ray cluster で head node が不要になる
   - B) 必要とするすべての process に large objects を再シリアライズするのではなく shared memory から読み取れるようにすることで、不必要なコピーを回避する
   - C) cluster の autoscaler configuration を保存する
   - D) tasks を特定の worker nodes にスケジュールする

<details>

<summary>回答を表示</summary>

**回答: B) 必要とするすべての process に large objects を再シリアライズするのではなく shared memory から読み取れるようにすることで、不必要なコピーを回避する**

**解説:**
object store は、tasks と actors の間で渡される objects のための distributed shared-memory store です。datasets や model weights などの large objects では、これにより必要とするすべての process に object を複製する際の serialization と copy のコストを回避できます。
</details>

5. Ray cluster の head node では、worker nodes で実行されるものに加えて何が実行されますか？
   - A) distributed object store のみ
   - B) Global Control Store (GCS)、driver process（そこで実行される場合）、および autoscaler
   - C) ユーザーが送信した tasks と actors のみ
   - D) 個別の Kubernetes control plane

<details>

<summary>回答を表示</summary>

**回答: B) Global Control Store (GCS)、driver process（そこで実行される場合）、および autoscaler**

**解説:**
head node では、GCS（cluster metadata）、トップレベルの script または session がそこで実行される場合の driver process、autoscaler が実行されます。さらに worker nodes と同様に、resource pool に CPU/GPU/memory を提供します。
</details>

6. Ray は cluster 全体で tasks と actors をどのようにスケジュールしますか？
   - A) 各 node の resources を個別に対象とし、ユーザーが各 task に特定の node を選択する必要がある
   - B) cluster の統合 resource pool を対象とするため、task は十分な free resources を持つ任意の node に配置できる
   - C) head node 上でのみ実行し、worker nodes は storage 専用で使用する
   - D) 利用可能な CPU、GPU、memory を考慮せず、ランダムに実行する

<details>

<summary>回答を表示</summary>

**回答: B) cluster の統合 resource pool を対象とするため、task は十分な free resources を持つ任意の node に配置できる**

**解説:**
Ray は node ごとではなく、cluster 全体の resource pool を対象に work をスケジュールします。指定量の CPU を要求する task は、cluster 内でその capacity が空いている任意の node で実行できます。
</details>

7. Ray Train、Ray Tune、Ray Serve にアーキテクチャ上共通していることは何ですか？
   - A) それぞれが Ray の core から独立した独自の scheduling および fault-tolerance system を実装している
   - B) いずれも Ray の core primitives と同じ underlying tasks、actors、object store の上に構築されている
   - C) Ray cluster の外部でしか実行できない
   - D) head node が不要になる

<details>

<summary>回答を表示</summary>

**回答: B) いずれも Ray の core primitives と同じ underlying tasks、actors、object store の上に構築されている**

**解説:**
Ray の training、tuning、serving 向けの高レベルライブラリは、workload ごとに scheduling と data movement を個別に再実装するのではなく、同じ primitives を再利用します。この共有基盤は、無関係な point tools をまとめたものとは異なる Ray の主要なアーキテクチャ上の特性です。
</details>

8. Kubernetes 上で Ray を実行する際に、Ray 独自の cluster concept 以外のものが必要なのはなぜですか？
   - A) Ray は containers 内で実行できないため
   - B) Ray の head/worker cluster shape は Kubernetes 独自の scheduling とは異なる layer であり、その shape を Pods や Deployments などの Kubernetes objects に変換するものが必要なため
   - C) Kubernetes が autoscaling をサポートしていないため
   - D) Ray tasks が Kubernetes nodes の CPU resources を利用できないため

<details>

<summary>回答を表示</summary>

**回答: B) Ray の head/worker cluster shape は Kubernetes 独自の scheduling とは異なる layer であり、その shape を Pods や Deployments などの Kubernetes objects に変換するものが必要なため**

**解説:**
Ray 独自の cluster の概念（head node、worker nodes、autoscaler）は、Kubernetes の scheduling model に自動的には対応しません。Ray cluster の shape を Kubernetes scheduler が理解する Pods と Deployments に変換するものが必要です。この変換を提供するのが KubeRay です。
</details>

## 短答式問題

9. チームメイトが、あるロジックを Ray task として実装すべきか、Ray actor として実装すべきかを検討しています。毎回読み込み直すのではなく、多数の incoming requests にわたって machine learning model を memory に読み込んだままにする必要があります。どの primitive を使用すべきですか？また、その理由は何ですか？

<details>

<summary>回答を表示</summary>

**回答: actor を使用します。actor は長期間存続する stateful な remote instance であるためです。読み込み済みの model を actor の state に保持し、多数の method calls にわたって再利用できます。stateless task の場合のように、呼び出しごとに再読み込みする必要はありません。**

**解説:**
tasks は stateless で単一の呼び出しを完了するため、呼び出し間で読み込み済みの model を常駐させておく場所がありません。actor の instance は remote process として存続するため、actor handle を通じた呼び出し間でも、読み込み済みの model weights などの state が保持されます。
</details>

10. Ray は、なぜ scheduling、fault tolerance、data movement を高レベルライブラリ（Train、Tune、Serve）ごとではなく、core primitives に一度だけ実装するのですか？

<details>

<summary>回答を表示</summary>

**回答: Ray Train、Ray Tune、Ray Serve はいずれも同じ tasks、actors、object store の上に構築されているため、各ライブラリは独自の workload 向けに scheduling と data movement を個別に再実装するのではなく、その共有実装を再利用します。**

**解説:**
この共有基盤は、それぞれ独自の execution model を持ちながら一緒にまとめられた、個別の point tools の ecosystem とは異なる Ray の主要なアーキテクチャ上の特性です。distributed training run と hyperparameter sweep はどちらも、その内部では Ray actors または tasks として動作する workers が、同じ object store を介して data を交換しています。
</details>

---

[学習資料に戻る](../../../ai-ml/ray/01-architecture.md) | [次のクイズ: KubeRay Operator](./02-kuberay-operator-quiz.md)

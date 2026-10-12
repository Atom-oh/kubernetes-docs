# EKS Hybrid Nodes GPU 統合クイズ

> **関連ドキュメント**: [GPU 統合](../../eks-hybrid-nodes/05-gpu-integration.md)
> **最終更新**: October 12, 2026

### 1. MIG を正しく説明している記述はどれですか？

A. 複数の物理 GPU を 1 つに統合する

B. サポート対象のハードウェアに裏付けられた compute/memory インスタンスを作成するが、host/driver とアプリケーション SLO に関する考慮事項は残る

C. すべてのテナントおよびすべての障害に対する完全な分離を保証する

D. ソフトウェアによる time-slicing と同一である

<details>
<summary>回答を表示</summary>

**回答: B. サポート対象のハードウェアに裏付けられた compute/memory インスタンスを作成するが、host/driver とアプリケーション SLO に関する考慮事項は残る**

**解説:** MIG は GPU ハードウェア層で memory/fault と resource の分離を提供します。サポート対象の profile/limit は GPU SKU と driver に依存します。これは完全な shared-host security やアプリケーション latency の保証を確立するものではありません。

</details>

### 2. 一般的な A10040GB の表に含まれる profile はどれですか？

A. 4g.40gb

B. 4g.20gb

C. 4g.80gb

D. 1g は物理 GPU 全体を 1 つ意味する

<details>
<summary>回答を表示</summary>

**回答: B. 4g.20gb**

**解説:** A10040GB の例には1g.5gb、2g.10gb、3g.20gb、4g.20gb、7g.40gb が含まれます。4g.40gb は A10080GB セットに属します。g コンポーネントは profile の compute slice 数を表します。名目上の memory ラベルは、正確に利用可能な memory を保証するものではありません。

</details>

### 3. time-slicing replicas:4 は何を提供しますか？

A. 4 つの物理 GPU と 4 つのプライベート memory 領域

B. 構成された GPU ごとに 4 つの論理 access slot を提供し、その memory/fault domain を共有する

C. 各 Pod に compute の 4 分の 1 を保証する

D. GPU memory を自動的に拡張する

<details>
<summary>回答を表示</summary>

**回答: B. 構成された GPU ごとに 4 つの論理 access slot を提供し、その memory/fault domain を共有する**

**解説:** contention と workload の動作は latency/throughput を変化させる可能性があります。より多くの replica をリクエストしても、比例した compute は保証されません。renameByDefault:true は nvidia.com/gpu.shared を広告します。使用されない ConfigMap を作成するのではなく、構成を実際の plugin に接続してください。

</details>

### 4. 現在の DRA は GPU allocation に何を追加しますか？

A. vendor driver なしでの GPU サポート

B. static CPU と memory の request のみ

C. DeviceClasses と ResourceClaims による構造化された device selection/allocation

D. すべての GPU アプリケーションに対する自動的な production validation

<details>
<summary>回答を表示</summary>

**回答: C. DeviceClasses と ResourceClaims による構造化された device selection/allocation**

**解説:** vendor driver、ResourceSlices、互換性のある kubelet/runtime、有効化された API は依然として必要です。現在の v1 claim は requests[].exactly を使用し、Pod resourceClaims は resourceClaimTemplateName を直接参照します。

</details>

### 5. 現在の ResourceClaim はどのように評価すべきですか？

A. 汎用的な status.phase:Bound enum を待つ

B. Claim の作成だけで GPU が使用可能であることを証明する

C. allocation.devices.results、reservation、Pod event、および driver preparation を確認する

D. 古い resourceHandles field のみを確認する

<details>
<summary>回答を表示</summary>

**回答: C. allocation.devices.results、reservation、Pod event、および driver preparation を確認する**

**解説:** 現在の ResourceClaims には、汎用的に保存される Pending→Allocated→Bound の phase sequence はありません。allocation/reservation は、device injection やアプリケーション実行が成功することを証明しません。

</details>

### 6. GPU Operator26.7 の ownership に関する正しい記述はどれですか？

A. GPUCluster と ClusterPolicy は常に同時に実行する必要がある

B. device-plugin management には ClusterPolicy を選択するか、managed DRA には新しい GPUCluster workflow を選択する。両者は共存できない

C. driver.enabled:false を設定すると、不足している host driver がインストールされる

D. controller nodeSelector はすべての operand を自動的に制限する

<details>
<summary>回答を表示</summary>

**回答: B. device-plugin management には ClusterPolicy を選択するか、managed DRA には新しい GPUCluster workflow を選択する。両者は共存できない**

**解説:** GPUCluster は gpu-cluster という名前の cluster-scoped singleton です。managed DRA workflow は ClusterPolicy/standalone DRA からの in-place migration ではありません。適切な driver/CDI/discovery component を準備し、operand label は別途確認してください。

</details>

### 7. H100SXM/H200SXM の比較は何を確立していますか？

A. すべての H100 variant は同一の memory を持つ

B. NVIDIA は H100SXM について80GB/3.35TB/s、H200SXM について141GB/4.8TB/s を示しているが、アプリケーションの結果には依然として測定が必要である

C. H200 は MIG をサポートしない

D. H200 は常にすべてのアプリケーションの throughput を 2 倍にする

<details>
<summary>回答を表示</summary>

**回答: B. NVIDIA は H100SXM について80GB/3.35TB/s、H200SXM について141GB/4.8TB/s を示しているが、アプリケーションの結果には依然として測定が必要である**

**解説:** これらは vendor SKU specification であり、audit benchmark ではありません。H100NVL/PCIe variant は異なります。model size、precision、batching、software、interconnect、contention も実際の performance に影響します。

</details>

### 8. 正しい EKS GPU deployment boundary はどれですか？

A. すべての Auto Mode node に追加の NVIDIA device plugin をインストールする

B. DRA はあらゆる種類の EKS node でサポートされていない

C. 範囲を限定した Hybrid allocation cohort を使用する。現在の EKS Auto Mode は NVIDIA DRA driver をサポートせず、device plugin はすでに管理している

D. 各物理 GPU を可能な限り多くの manager を通じて公開する

<details>
<summary>回答を表示</summary>

**回答: C. 範囲を限定した Hybrid allocation cohort を使用する。現在の EKS Auto Mode は NVIDIA DRA driver をサポートせず、device plugin はすでに管理している**

**解説:** AWS は、新しいサポート対象の EKS 1.34+ static-capacity deployment に DRA を推奨しています。文書化された driver prerequisite を使用し、重複する device ownership を防止してください。Kubernetes API maturity は、個々の vendor feature gate とは別のものです。

</details>

### 9. container が 1 つの DRA GPU をリクエストします。CUDA_VISIBLE_DEVICES はどのように設定すべきですか？

A. 常に0,1,2,3 を設定する

B. host で検出されたすべての物理 index を設定する

C. この variable を使用して GPU をさらに 3 つリクエストする

D. device manager/runtime に割り当てられた device を公開させ、無関係な物理 index で上書きしない

<details>
<summary>回答を表示</summary>

**回答: D. device manager/runtime に割り当てられた device を公開させ、無関係な物理 index で上書きしない**

**解説:** process から見える CUDA index は、物理 GPU index と異なる場合があります。手動による上書きは device を非表示にしたり誤って識別したりする可能性があり、追加の GPU を付与することはありません。1 つの claim を参照する複数の container は、依然としてその 1 つの allocation を共有します。

</details>

### 10. suspended smoke Job と local schema check は何を証明しますか？

A. GPU driver と model が正常に実行された

B. すべての GPU workload が latency SLO を満たす

C. レビューされた manifest/configuration は範囲を限定した local check を通過する。実際の GPU validation には owner の承認と実行が必要である

D. cleanup verification は不要である

<details>
<summary>回答を表示</summary>

**回答: C. レビューされた manifest/configuration は範囲を限定した local check を通過する。実際の GPU validation には owner の承認と実行が必要である**

**解説:** 意図的に使用不能な image を承認済み digest に置き換え、1 つの Job の suspend を解除する前に runtime/placement/security を検証してください。結果を記録し、cleanup 中に claim unprepare/release を検証してください。nvidia-smi の可視性だけでは CUDA/LLM benchmark にはなりません。

</details>

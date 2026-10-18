# AI/ML ワークロードクイズ

リソース割り当て、学習と推論、ストレージ、ネットワーク、セキュリティ、可観測性、コスト、それぞれの適用範囲を確認しましょう。

## クイズ問題

### 1. NVIDIA device plugin が公開する GPU を、Pod はどのように要求すべきですか？

- A. nvidia.com/gpu:0.5 を requests にだけ指定する
- B. 整数値の nvidia.com/gpu を limits に指定し、requests も指定する場合は同じ値にする
- C. nvidia.com/gpu の node annotation だけを追加する
- D. RuntimeClass を nvidia-mps という名前にすれば、自動的に GPU 共有が有効になる

<details>
<summary>回答を表示</summary>

**回答: B. 整数値の nvidia.com/gpu を limits に指定し、requests も指定する場合は同じ値にする**

limits だけを指定した場合、同じ値の requests が暗黙に設定されます。割り当て可能な GPU 容量は node label ではありません。GPU Feature Discovery のラベル、MIG、MPS、time-slicing には、それぞれ別途設定が必要です。共有スロットを使っても、GPU メモリの一部が保証されるわけではありません。

[割り当てと共有](../../ai-ml/01-ai-ml-workloads.md#nvidia-gpu-operator-and-device-allocation)
</details>

### 2. TensorFlow の分散ロールを理解する、インストール済みのレガシー Kubeflow リソースはどれですか？

- A. Deployment はすべての TF_CONFIG 値を自動的に作成する
- B. Job はトレーニングの成功と、すべての worker の同時配置を保証する
- C. TFJob はフレームワーク固有のロールと設定を提供する
- D. TFJob は Kubernetes に組み込まれているため、インストールは不要である

<details>
<summary>回答を表示</summary>

**回答: C. TFJob はフレームワーク固有のロールと設定を提供する**

TFJob の CRD と controller をインストールし、restart policy、フレームワーク戦略、checkpoint、ストレージ、ネットワークを設定します。障害からの復旧や gang scheduling が常に保証されるわけではありません。実際に学習を行うコードを用意すれば、通常の Job でもトレーニングできます。

[Trainer とレガシー API](../../ai-ml/kubeflow/05-training-operator.md)
</details>

### 3. 既存の FSx for Lustre ファイルシステムを CSI 経由で接続するには、どの方法を使うべきですか？

- A. Lustre CR と、既存のファイルシステム ID を含む StorageClass を組み合わせる
- B. volumeHandle/dnsname/mountname を指定した静的 PV と、バインド済み PVC を使う
- C. SCRATCH_2 なら、永続バックアップやスループットに関するすべてのオプションを利用できる
- D. マウントされていない /data に対する FIO で FSx の性能を測定できる

<details>
<summary>回答を表示</summary>

**回答: B. volumeHandle/dnsname/mountname を指定した静的 PV と、バインド済み PVC を使う**

静的な接続と、ファイルシステムを動的に作成する方法は異なります。容量、IOPS/スループット、レイテンシー、アクセスパターン、権限、AZ とネットワーク、バックアップを比較してください。実際にマウントしたボリューム上に専用のテスト領域を用意して、ベンチマークを実施します。

[静的および動的ストレージ](../../ai-ml/01-ai-ml-workloads.md#storage-and-caching)
</details>

### 4. AI/ML ワークロードのリソース割り当てでは、何を指針にすべきですか？

- A. すべてのトレーニング Job に GPU が必要である
- B. 実測した CPU/メモリ/GPU 使用量、モデルの大きさ、I/O、レイテンシー、スループット
- C. 常に最大量のリソースを要求する
- D. requests を省略するのが常に最も効率的である

<details>
<summary>回答を表示</summary>

**回答: B. 実測した CPU/メモリ/GPU 使用量、モデルの大きさ、I/O、レイテンシー、スループット**

CPU やほかのアクセラレーターが適切な場合もあります。OMP/MKL のスレッド設定が影響するのは補助ライブラリであり、GPU の共有方法ではありません。CUDA allocator の設定も、Kubernetes による GPU の割り当てや分離とは異なります。VPA の効果は、そのモード、再起動時の動作、ワークロードとの互換性によって変わります。

[リソース配置](../../ai-ml/01-ai-ml-workloads.md#placement-and-topology)
</details>

### 5. KServe などの推論基盤を選ぶ際に確認すべきことは何ですか？

- A. どの model URI もすぐに利用できる
- B. ランタイムイメージ、モデル形式、プロトコル、ストレージ、デプロイ方式が要件に合っている
- C. 通常の Deployment では推論サーバーを実行できない
- D. どの方式でも canary と scale-to-zero の動作は同じである

<details>
<summary>回答を表示</summary>

**回答: B. ランタイムイメージ、モデル形式、プロトコル、ストレージ、デプロイ方式が要件に合っている**

通常の Deployment でも推論サーバーを実行できます。KServe の Knative/Standard モードと、バージョンごとに異なる Seldon API では動作が異なります。説明可能性、前処理、重み付けルーティング、バッチ推論が、常にデフォルトで有効になっているとは限りません。TorchServe は、新規利用向けに保守される標準の選択肢ではありません。

[KServe のモードとランタイム](../../ai-ml/kubeflow/06-kserve.md)
</details>

### 6. GPU 使用率やリクエスト負荷に基づいて HPA をスケーリングするには、何が必要ですか？

- A. 割り当て済みの nvidia.com/gpu が、自動的に utilization の Resource metric になる
- B. 正しいラベル、単位、集約方法を設定した exporter と custom/external metrics adapter
- C. モデルの精度が低いときに replica 数を増やす
- D. 加算式のスケーリングを行うため、同じ Deployment に複数の HPA を設定する

<details>
<summary>回答を表示</summary>

**回答: B. 正しいラベル、単位、集約方法を設定した exporter と custom/external metrics adapter**

標準の metrics-server が Resource metrics として公開するのは CPU とメモリです。GPU やリクエストのメトリクスには、別途収集機構と adapter が必要です。Pod のメトリクスは namespace と Pod のラベルに対応付ける必要があります。全体平均では、その対応関係が失われる場合があります。スケーリングを管理する主体は 1 つにし、レイテンシーパーセンタイルよりも負荷やキュー長の方が比例的な指標として適切かを検証してください。

[HPA の例](../../ai-ml/01-ai-ml-workloads.md#hpa-and-metrics)
</details>

### 7. 分散トレーニングのネットワークについて、正しい説明はどれですか？

- A. zone annotation だけで配置を制御できる
- B. GPU の hostPath マウントで EFA/GPUDirect を設定できる
- C. node label による配置、ハードウェア、ドライバー/plugin、通信ライブラリ、ネットワークポリシーをまとめて検証する
- D. NCCL は常に MPI 経由でデータを転送する

<details>
<summary>回答を表示</summary>

**回答: C. node label による配置、ハードウェア、ドライバー/plugin、通信ライブラリ、ネットワークポリシーをまとめて検証する**

EFA 上で NCCL を使うには AWS OFI NCCL と libfabric が必要です。MPI はプロセスを起動できます。Multus/SR-IOV、MTU、RDMA の設定は環境によって異なります。一般的な NIC の例を、そのまま使える EKS 設定として扱わないでください。NetworkPolicy が必要な通信をブロックすると、可用性や性能に影響する場合があります。

[分散トレーニングの境界](../../ai-ml/01-ai-ml-workloads.md#kubeflow-and-distributed-training)
</details>

### 8. モデルとデータの保護について、正しい説明はどれですか？

- A. Secret の base64 は暗号化である
- B. Kubernetes RBAC により S3/KMS の権限が付与される
- C. API RBAC、ワークロード IAM、暗号化と鍵管理、ファイル認証情報、ネットワークをそれぞれ設定する
- D. 大きなモデルは Secrets に保存し、復号鍵はデフォルトで環境変数に保存する

<details>
<summary>回答を表示</summary>

**回答: C. API RBAC、ワークロード IAM、暗号化と鍵管理、ファイル認証情報、ネットワークをそれぞれ設定する**

Secrets にはサイズ上限があり、base64 は暗号化ではなくエンコードです。大きなモデルには、認可と整合性の検証を行えるオブジェクトストレージを使います。Secret volume をマウントする Pod の service account に、常に Secret の get 権限が必要なわけではありません。API による読み取りと kubelet による volume の配信は別の処理です。PodSecurityPolicy は削除済みのため、現在の admission/PSS 制御を使ってください。

[データとモデルへのアクセス](../../ai-ml/01-ai-ml-workloads.md#data-and-model-access)
</details>

### 9. ML サービスの可観測性では、何を区別すべきですか？

- A. GPU 使用率がモデルの精度を決める
- B. ServiceMonitor は Pod のラベルを直接選択する
- C. サービスのエラー/レイテンシー/スループット、リソース使用量、正解ラベルに基づくモデル品質は、それぞれ別の指標である
- D. すべてのコンテナログは Docker JSON 形式である

<details>
<summary>回答を表示</summary>

**回答: C. サービスのエラー/レイテンシー/スループット、リソース使用量、正解ラベルに基づくモデル品質は、それぞれ別の指標である**

ServiceMonitor は Service のラベルと名前付きポートを選択します。レイテンシーに失敗したリクエストを含めるか定義し、1 つのリクエストを成功とエラーの両方に数えないようにします。品質の評価にはラベルや正解データが必要です。CRI のログ形式とアプリケーションの JSON、Grafana の datasource/panel schema、ラベル別のアラート集約、トラフィックがゼロの場合の動作を検証してください。

[メトリクスとログ](../../ai-ml/01-ai-ml-workloads.md#prometheus-and-grafana)
</details>

### 10. コスト最適化はどのように検証すべきですか？

- A. すべてのワークロードに Spot を使う
- B. 新しい世代の instance は常に最安である
- C. 必要な性能、総コスト、中断からの復旧と checkpoint、実際に Pod/node が解放されるかを測定する
- D. 夜間には On-Demand の料金が自動的に下がる

<details>
<summary>回答を表示</summary>

**回答: C. 必要な性能、総コスト、中断からの復旧と checkpoint、実際に Pod/node が解放されるかを測定する**

Pod 数が減っても、EC2 instance が終了するとは限りません。可用性、クォータ、AMI/ドライバー、NodePool の上限を確認してください。トレーニング用 taint には一致する toleration が必要です。CPU/GPU の混在グループは EKS Hybrid Nodes ではありません。使用されない Autoscaler ConfigMap を作成しても、controller の起動フラグは変わりません。

[Spot とノードのプロビジョニング](../../ai-ml/01-ai-ml-workloads.md#spot-and-node-provisioning)
</details>

---

[学習教材に戻る](../../ai-ml/01-ai-ml-workloads.md)

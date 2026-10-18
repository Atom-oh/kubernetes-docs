# EKS Hybrid Nodes ワークロード配置クイズ

> **関連ドキュメント**: [ワークロード配置](../../eks-hybrid-nodes/06-workload-placement.md)
> **最終更新日**: 2026年9月13日

### 1. Podの配置先や配置可否を直接決める仕組みではないものはどれですか？

A. nodeSelector

B. Node affinity

C. Taints and tolerations

D. PodDisruptionBudget

<details>
<summary>解答を表示</summary>

**解答: D. PodDisruptionBudget**

**解説:** PDBは、サポート対象の自発的な退避要求を制約するもので、Nodeを選択しません。また、あらゆる削除経路で可用性を保証するものでもありません。Node選択、affinity、taintにはそれぞれ異なるスケジューリング上の役割があります。

</details>

### 2. `dedicated=gpu:NoSchedule`で何が保証されますか？

A. GPUを要求するコンテナだけが、そのNodeで実行できる

B. 新しいPodには適用可能なtolerationが必要だが、それだけではGPU使用も配置の強制も保証されない

C. 既存のPodが直ちに退避される

D. NodeがGPUリソースを自動的に広告する

<details>
<summary>解答を表示</summary>

**解答: B. 新しいPodには適用可能なtolerationが必要だが、それだけではGPU使用も配置の強制も保証されない**

**解説:** CPUだけを使うPodも、このtaintを許容できます。GPUリソース要求とadmission policyは別の仕組みです。`NoSchedule`は新しいPodのスケジューリングに影響し、`NoExecute`には異なる退避動作があります。

</details>

### 3. バースト可能なワークロードでpreferred node affinityが行うことは何ですか？

A. 実行中のクラウドPodをオンプレミスへ自動移行する

B. オンプレミスとクラウドのレプリカ比率を固定する

C. 他の制約と利用可能な容量の範囲で、適格なNodeの中から配置先の選好を示す

D. 8個目のPod以降、AWSの容量を無制限にする

<details>
<summary>解答を表示</summary>

**解答: C. 他の制約と利用可能な容量の範囲で、適格なNodeの中から配置先の選好を示す**

**解説:** preferred affinityは、容量不足の検出機能でも、厳密な配置順序でも、移行controllerでもありません。Node数はPodの収容容量を表しません。Karpenterとレプリカautoscalerは別々の制御ループであり、quota、提供中のインスタンスタイプ、IP、ワークロードの依存関係が拡張を妨げることがあります。

</details>

### 4. `DoNotSchedule`の場合、topologyの`maxSkew`はどのように解釈しますか？

A. クラスター全体のPod総数に対する上限

B. 設定されていれば`minDomains`の動作も考慮した、適格なdomain間の全体最小値との差

C. `ScheduleAnyway`で必ず均等に分散させる条件

D. AWSアカウント数

<details>
<summary>解答を表示</summary>

**解答: B. 設定されていれば`minDomains`の動作も考慮した、適格なdomain間の全体最小値との差**

**解説:** 適格なdomainは、Podの制約とtopology policyによって決まります。`ScheduleAnyway`はソフトなスコアを使うため、`maxSkew`を超える場合があります。domainが欠けていたり、ハード制約を満たせなかったりすると、PodがPendingのままになることがあります。

</details>

### 5. ローカルの永続データを使う場合、どの方法が適切ですか？

A. Node labelを設定し、データもそこに存在するとみなす

B. 管理されたlocal PV/PVCのtopologyとbindingを使い、クラウドへの配置に備えてデータアクセスまたは複製を別途計画する

C. `/mnt/data`を`hostPath`でmountし、移植可能なストレージとして扱う

D. volumeを確認せず、任意のクラウドNodeへPodを移動する

<details>
<summary>解答を表示</summary>

**解答: B. 管理されたlocal PV/PVCのtopologyとbindingを使い、クラウドへの配置に備えてデータアクセスまたは複製を別途計画する**

**解説:** labelを付けてもデータは作成・複製されません。local PVのNode affinityと`WaitForFirstConsumer`によって配置を調整できますが、binding済みのlocal volumeがEC2へのfallback先から自動的に利用できるわけではありません。

</details>

### 6. 必須のhostname anti-affinityによって、何を実現できますか？

A. アプリケーションの可用性を完全に保証する

B. 容量が十分な場合、該当するレプリカを適格なKubernetes Node間で分散する

C. 独立した物理電源間での分離を保証する

D. 他のcontrollerなしでレプリカを自動修復する

<details>
<summary>解答を表示</summary>

**解答: B. 容量が十分な場合、該当するレプリカを適格なKubernetes Node間で分散する**

**解説:** これは相関障害の要因を一つ減らします。残るレプリカのreadiness、依存関係、十分な処理容量は別途必要です。また、別々のKubernetes Nodeが同じ物理hostや障害domainを共有していることもあります。

</details>

### 7. `deletion-cost`が1000のオンプレミスPodが、cost 0のクラウドPodより先に削除されることはありますか？

A. ありません。1000ならevictionされません

B. ありません。ReplicaSetの最初の比較基準がcostだからです

C. あります。確認対象のcontrollerでは、assignment、phase、readinessがdeletion costより先に評価されます

D. cost annotationがない場合に限ります

<details>
<summary>解答を表示</summary>

**解答: C. あります。確認対象のcontrollerでは、assignment、phase、readinessがdeletion costより先に評価されます**

**解説:** 未割り当て、Pending/Unknown、NotReadyなどの条件が優先される場合があります。deletion costは同じReplicaSetのPod間で使われるベストエフォートの優先度であり、すべてのcontroller、rollout、eviction、障害からPodを保護するものではありません。

</details>

### 8. 古いCREATE専用の場所判定mutating webhookが不完全なのはなぜですか？

A. Pod作成ではadmission webhookを利用できない

B. クラウドにはlabelがない

C. 通常のCREATE要求ではNodeへのbinding前であり、最終的な配置先のlocationがまだ分からないことが多い

D. deletion costはスケジューリング後にしか変更できない

<details>
<summary>解答を表示</summary>

**解答: C. 通常のCREATE要求ではNodeへのbinding前であり、最終的な配置先のlocationがまだ分からないことが多い**

**解説:** binding後の処理なら`spec.nodeName`を確認できます。本番用webhookには、有効なbackend、Service、TLS、適切に限定したpolicyも必要です。不完全なfail-closed webhookはPod作成を妨げる可能性があります。

</details>

### 9. Karpenter 1.14.1は`pod-deletion-cost`を読み取りますか？

A. いいえ。読み取る可能性があるのはReplicaSetだけです

B. はい。他の入力とともに正規化されたeviction-costのヒューリスティックに使いますが、disruptionを禁止するものではありません

C. はい。1000なら1000倍の保護が保証されます

D. はい。PDBとあらゆるdisruption budgetの代わりになります

<details>
<summary>解答を表示</summary>

**解答: B. はい。他の入力とともに正規化されたeviction-costのヒューリスティックに使いますが、disruptionを禁止するものではありません**

**解説:** 対象のKarpenter sourceでは、このannotationがPodのeviction costに含まれます。候補評価、Nodeの状態、priority、lifecycle上の制約も関係します。cost annotationによって空のNodeが直ちに削除されると保証されるわけでもありません。

</details>

### 10. 単一Podへのannotation patchが、古いクラスター全体のCronJobより安全なのはなぜですか？

A. すべてのAPI errorを無視する

B. labelがない場合にクラウド配置を推測する

C. 対象のReplicaSet owner、Node分類、Pod UID、resourceVersionを確認してから、範囲を絞ったpatchをレビューする

D. 最初の競合の後、同時更新のテストを削除する

<details>
<summary>解答を表示</summary>

**解答: C. 対象のReplicaSet owner、Node分類、Pod UID、resourceVersionを確認してから、範囲を絞ったpatchをレビューする**

**解説:** この例では、状態が不明または未スケジュールの場合に処理を拒否し、レビュー可能なpatchを作成します。UID、resourceVersion、Nodeのtestによって古い状態を拒否でき、無関係なannotationは維持されます。すべてのnamespaceを走査・変更するものではありません。

</details>

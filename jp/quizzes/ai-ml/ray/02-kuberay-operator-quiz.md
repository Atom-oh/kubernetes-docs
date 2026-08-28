# KubeRay Operator クイズ

このクイズでは、KubeRay とは何か、その 3 つの主要な CRD、Karpenter と共有する 2 層の autoscaling モデル、および GPU scheduling の処理方法についての理解を確認します。

## 選択式問題

1. KubeRay とは何ですか？
   - A) Ray cluster を実行するためのマネージド AWS service
   - B) Ray cluster をネイティブ Kubernetes custom resource として管理し、head/worker-node 構成を Pods、Services、および関連する object に変換する Kubernetes operator
   - C) Ray 専用の kubectl 置き換えツール
   - D) cluster management 機能を持たない Ray cluster 向け monitoring dashboard

<details>

<summary>回答を表示</summary>

**回答: B) Ray cluster をネイティブ Kubernetes custom resource として管理し、head/worker-node 構成を Pods、Services、および関連する object に変換する Kubernetes operator**

**解説:**
KubeRay は、Pod spec を手作業で記述するのではなく、「Kubernetes 上の Ray」を宣言的に実現するものです。宣言された RayCluster/RayJob/RayService spec を、Kubernetes が必要とする実際の Pods、Services、およびその他の object に reconcile します。
</details>

2. 1 つの head Pod と 1 つ以上の worker group で構成される生の Ray cluster を表す CRD はどれですか？
   - A) RayJob
   - B) RayService
   - C) RayCluster
   - D) RayNodePool

<details>

<summary>回答を表示</summary>

**回答: C) RayCluster**

**解説:**
RayCluster は基本となる CRD です。1 つの head Pod と 1 つ以上の worker group で構成され、各 worker group は同種の worker Pods のセットです（たとえば、CPU worker group と別個の GPU worker group）。operator が reconcile して、目的の spec に一致させます。
</details>

3. RayJob が単発またはスケジュールされた batch workload に適している理由は何ですか？
   - A) 事前に存在し、永続的に実行されている RayCluster でしか実行できないため
   - B) RayCluster を作成し、送信された job を実行し、job 完了時に cluster を削除できるため、実行の合間に cluster が idle 状態にならないため
   - C) Ray autoscaler を完全に無効にするため
   - D) 先に別の RayService が実行されている必要があるため

<details>

<summary>回答を表示</summary>

**回答: B) RayCluster を作成し、送信された job を実行し、job 完了時に cluster を削除できるため、実行の合間に cluster が idle 状態にならないため**

**解説:**
RayJob は batch job を送信し、必要に応じて基盤となる cluster の完全な lifecycle、すなわち作成、job 実行、削除を管理できます。これにより、実行の合間に idle 状態の cluster に料金を支払うことを避けられます。
</details>

4. RayService と RayCluster の違いは何ですか？
   - A) RayService は Ray Serve application を一切実行できない
   - B) RayService は RayCluster とその上で動作する Ray Serve application を管理し、downtime なしの rolling upgrade をサポートする
   - C) RayService は worker group のない単一の Pod でのみ実行される
   - D) RayService は RayCluster の代わりに非推奨となっている

<details>

<summary>回答を表示</summary>

**回答: B) RayService は RayCluster とその上で動作する Ray Serve application を管理し、downtime なしの rolling upgrade をサポートする**

**解説:**
RayService は本番の model serving を対象とします。RayCluster とその上にデプロイされた Ray Serve application の両方を管理し、zero downtime を目指した rolling upgrade をサポートします。本番環境でこの upgrade path に依存する前に、現在の KubeRay release notes でその成熟度を確認してください。
</details>

5. Ray on EKS で説明されている 2 層の autoscaling パターンでは、Ray autoscaler と Karpenter はそれぞれ何を決定しますか？
   - A) Ray autoscaler が EC2 node type を決定し、Karpenter が Ray task の配置を決定する
   - B) Ray autoscaler が必要な Ray worker Pods の数を決定し（RayCluster worker group replica count を調整することで）、Karpenter がその結果 pending 状態になった Pods のために provisioning する EC2 nodes の数を決定する
   - C) fault tolerance のため、両方の control loop が同じことを冗長に決定する
   - D) Karpenter が Pod count を決定し、Ray autoscaler が node count を決定する

<details>

<summary>回答を表示</summary>

**回答: B) Ray autoscaler が必要な Ray worker Pods の数を決定し（RayCluster worker group replica count を調整することで）、Karpenter がその結果 pending 状態になった Pods のために provisioning する EC2 nodes の数を決定する**

**解説:**
一方の control loop（KubeRay を通じて連携する Ray autoscaler）は Pod count を担当し、別の control loop（Karpenter または Kubernetes Cluster Autoscaler）は node count を担当します。両者は通常の pending-Pod scheduling state を介して間接的にのみ通信します。これは、この documentation site が Flink と Katib について説明しているものと同じ 2 層パターンです。
</details>

6. Ray autoscaler の `idleTimeoutSeconds` 設定は何を制御し、その default value は何ですか？
   - A) KubeRay operator が CRD を install するまでの待機時間。default は 60 秒
   - B) task、actor、または参照中の object がない worker Pod が idle 状態であり続けてから、autoscaler が scale down するまでの時間。default は 60 秒
   - C) Karpenter が新しい EC2 node を provisioning するまでの待機時間。default は 60 秒
   - D) 完了した RayJob の head Pod の TTL。default は 60 秒

<details>

<summary>回答を表示</summary>

**回答: B) task、actor、または参照中の object がない worker Pod が idle 状態であり続けてから、autoscaler が scale down するまでの時間。default は 60 秒**

**解説:**
`idleTimeoutSeconds` の default は 60 秒であり、idle 状態の worker Pod を scale down する前に Ray autoscaler が適用する待機時間です。
</details>

7. KubeRay は、worker group の Ray process に認識させる GPU の数をどのように決定しますか？
   - A) RayCluster spec の top-level metadata にある別個の `numGPUs` field を読み取る
   - B) worker group の Pod spec に設定された GPU resource limit（例: `nvidia.com/gpu`）を読み取り、Ray scheduler と autoscaler に通知し、Ray process の `--num-gpus` flag を一致するよう自動設定する
   - C) Pods の開始後に別個の `kubectl ray gpu-config` command を使って GPU count を手動設定する必要がある
   - D) KubeRay は Pod spec にかかわらず、worker Pod ごとに必ず GPU が 1 つであると仮定する

<details>

<summary>回答を表示</summary>

**回答: B) worker group の Pod spec に設定された GPU resource limit（例: `nvidia.com/gpu`）を読み取り、Ray scheduler と autoscaler に通知し、Ray process の `--num-gpus` flag を一致するよう自動設定する**

**解説:**
GPU worker group の Pod spec は唯一の source of truth です。KubeRay は container の GPU resource limit を Ray scheduler と autoscaler の両方に通知し、Ray process の `--num-gpus` を一致するよう設定します。そのため、GPU count を手作業で同期させる場所を別途持つ必要はありません。
</details>

8. このドキュメントによると、KubeRay operator を install する標準的な方法は何ですか？
   - A) 無作為な GitHub gist からダウンロードした raw manifest を手動で適用する
   - B) `helm repo add kuberay https://ray-project.github.io/kuberay-helm/` を通じて追加する公式 Helm chart
   - C) 1 行の `kubectl create clusterrole kuberay` command
   - D) サポートされている install 方法はなく、KubeRay を source から build する必要がある

<details>

<summary>回答を表示</summary>

**回答: B) `helm repo add kuberay https://ray-project.github.io/kuberay-helm/` を通じて追加する公式 Helm chart**

**解説:**
`ray-project/kuberay-helm` repository には、KubeRay operator、その controller、および RayCluster/RayJob/RayService CRDs を install するための公式 Helm chart があります。
</details>

## 短答式問題

9. KubeRay が公開する 3 つの主要な CRD を挙げ、それぞれの用途を簡潔に説明してください。

<details>

<summary>回答を表示</summary>

**回答:**
- RayCluster: 1 つの head Pod と 1 つ以上の worker group で構成され、宣言された spec に一致するよう reconcile される生の Ray cluster。
- RayJob: Ray cluster に batch job を送信し、必要に応じて単発またはスケジュールされた workload 向けに、その cluster の作成・実行・削除という完全な lifecycle を管理する。
- RayService: 本番の model serving 向けに RayCluster とその上で動作する Ray Serve application を管理し、zero-downtime rolling upgrade をサポートする。

**解説:**
各 CRD は、同じ基盤となる reconciliation model 上に構築されながら、生の cluster management、batch job 実行、本番 serving という異なる usage pattern を対象とします。
</details>

10. Ray-on-EKS autoscaling で 1 つではなく 2 つの別個の control loop が必要な理由と、各 loop の責任を説明してください。

<details>

<summary>回答を表示</summary>

**回答:**
Ray autoscaler は Ray-level state（pending task と actor）を理解しますが、EC2 capacity については何も認識しません。Karpenter は Kubernetes-level の pending Pods と EC2 provisioning を理解しますが、Ray task や actor については何も認識しません。Ray autoscaler は必要な Ray worker Pods の数を決定し、RayCluster worker group replica count を通じてそれらを要求します。Karpenter は結果として pending 状態になった Pods に個別に反応し、それらを実行するための一致する EC2 nodes を provisioning します。

**解説:**
各 loop は他方が持たない情報に基づいて動作するため、一方が他方の代わりになることはできません。Pod count 用の loop と node count 用の loop があり、通常の Kubernetes scheduling state を介してのみ通信するこの 2 層の分割は、この documentation site が Flink と Katib の autoscaling を説明するために使用しているものと同じパターンです。
</details>

---

[学習教材に戻る](../../../ai-ml/ray/02-kuberay-operator.md) | [次のクイズ: Ray Train and Tune](./03-ray-train-tune-quiz.md)

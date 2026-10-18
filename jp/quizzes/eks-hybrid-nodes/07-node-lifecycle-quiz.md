# Node Lifecycle Management クイズ

> このクイズでは、[Node Lifecycle Management](../../eks-hybrid-nodes/07-node-lifecycle.md) ドキュメントの理解度を確認します。

---

1. NodeConfig の kubelet 設定で `systemReserved` と `kubeReserved` を設定する主な目的は何ですか？
   - A) Pod のリソース要求を自動的に調整するため
   - B) Node Allocatable の計算時に、システムプロセスと Kubernetes コンポーネント用のリソースを予約するため
   - C) Node で利用可能な総リソースを増やすため
   - D) Pod のスケジューリング優先度を決定するため

<details>
<summary>回答を表示</summary>

**回答: B) Node Allocatable の計算時に、システムプロセスと Kubernetes コンポーネント用のリソースを予約するため**

**説明:**
`systemReserved` は OS とシステムデーモン（sshd、udev など）用、`kubeReserved` は kubelet と containerd 用のリソースを予約します。この予約によって Node の割り当て可能容量が減ります。ホストプロセス用 cgroup 予約を強制するには追加設定が必要であり、これらのフィールドだけで安定性が保証されるわけではありません。

</details>

---

2. kubelet の `evictionHard` と `evictionSoft` の違いは何ですか？
   - A) `evictionHard` はソフトリミットで、`evictionSoft` はハードリミットである
   - B) `evictionHard` にはソフトなしきい値の観測猶予がなく、`evictionSoft` ではしきい値が一定時間継続する必要がある
   - C) `evictionHard` は Pod のみを退避し、`evictionSoft` は Node をシャットダウンする
   - D) 両方の設定は名前が異なるだけで同じように動作する

<details>
<summary>回答を表示</summary>

**回答: B) `evictionHard` にはソフトなしきい値の観測猶予がなく、`evictionSoft` ではしきい値が一定時間継続する必要がある**

**説明:**
必要に応じて kubelet はまず Node レベルのリソース回収を試み、その後 Pod を退避します。ハードしきい値にはソフトなしきい値の観測期間がなく、Pod の終了猶予も与えずに退避します。ソフトしきい値は `evictionSoftGracePeriod` の期間継続する必要があります。`evictionMaxPodGracePeriod` は Pod の終了猶予を別途制限します。これらの設定も、ハード退避や OOM を防ぐものではありません。

</details>

---

3. Kubernetes の version skew policy によると、1.31 の API server を使う過去の例で実行できる最も古い kubelet バージョンは何ですか？（現在の EKS バージョンの提供状況は考慮しません）
   - A) 1.27
   - B) 1.28
   - C) 1.29
   - D) 1.30

<details>
<summary>回答を表示</summary>

**回答: B) 1.28**

**説明:**
Kubernetes の version skew policy によると、kubelet は API server より最大 3 つ前のマイナーバージョンまで古くできます。API server が 1.31 の場合、kubelet は 1.31、1.30、1.29、1.28 と互換性があります。バージョン 1.27 は n-4 であり、サポートされません。

</details>

---

4. canary upgrade 戦略の中核となる原則は何ですか？
   - A) すべての Node を同時にアップグレードする
   - B) まず 1 つの Node をアップグレードして検証し、その後残りを進める
   - C) Node を削除して新しい Node を作成する
   - D) ダウンタイムなしで in-place upgrade を実行する

<details>
<summary>回答を表示</summary>

**回答: B) まず 1 つの Node をアップグレードして検証し、その後残りを進める**

**説明:**
canary upgrade では、最初に単一の「canary」Node をアップグレードし、結果を検証します。問題が見つからなければ、残りの Node に対して rolling upgrade を進め、リスクを最小化します。

</details>

---

5. hybrid node を初期化するとき、nodeadm はどのラベルを自動的に割り当てますか？
   - A) `node-role.kubernetes.io/hybrid=true`
   - B) `topology.kubernetes.io/zone=on-premises`
   - C) `eks.amazonaws.com/compute-type=hybrid`
   - D) `kubernetes.io/os=hybrid`

<details>
<summary>回答を表示</summary>

**回答: C) `eks.amazonaws.com/compute-type=hybrid`**

**説明:**
nodeadm は hybrid node の初期化中に `eks.amazonaws.com/compute-type=hybrid` ラベルを自動的に割り当てます。このラベルを `--node-labels` に手動で追加する必要はなく、Cilium affinity、workload 配置などに使用されます。

</details>

---

6. SSM activation の有効期限が切れたものの、Node はすでに登録済みです。正しい対応は何ですか？
   - A) 既存の activation の有効期限を延長する
   - B) 既存の登録は維持し、新規登録が必要な場合に限って新しい activation を使う
   - C) IAM Roles Anywhere に切り替える
   - D) 自動更新のために kubelet を再起動する

<details>
<summary>回答を表示</summary>

**回答: B) 既存の登録は維持し、新規登録が必要な場合に限って新しい activation を使う**

**説明:**
Activation の有効期限切れによってブロックされるのは新規登録です。すでに登録された Node は明示的に登録解除されるまで管理対象のままです。activation の期限切れだけを理由に、正常な Node をアンインストールして再登録しないでください。エージェントの認証情報、ロール権限、接続性はそれぞれ別の要件です。

</details>

---

7. Node がすでに control plane と同じマイナーバージョンにある場合、次のマイナーバージョンへ移行する順序は何ですか？
   - A) まず Node をアップグレードし、その後 control plane をアップグレードする
   - B) control plane と Node を同時にアップグレードする
   - C) まず control plane (EKS) をアップグレードし、その後 Node をアップグレードする
   - D) 順序は重要ではない

<details>
<summary>回答を表示</summary>

**回答: C) まず control plane (EKS) をアップグレードし、その後 Node をアップグレードする**

**説明:**
Kubernetes の version skew policy では、kubelet を API server より新しいバージョンにはできません。この次のマイナーバージョンへの移行では、Node より先に control plane をアップグレードしてください。遅れている Node を現在の control plane のバージョンまで先に引き上げても、バージョン skew の範囲には抵触しません。

</details>

---

8. `shutdownGracePeriod: 60s` と `shutdownGracePeriodCriticalPods: 20s` が設定されている場合、通常の Pod はどれだけの終了猶予時間を受け取りますか？
   - A) 20 秒
   - B) 40 秒
   - C) 60 秒
   - D) 80 秒

<details>
<summary>回答を表示</summary>

**回答: B) 40 秒**

**説明:**
`shutdownGracePeriodCriticalPods` は `shutdownGracePeriod` に含まれます。合計 60 秒から critical Pod 用に確保された 20 秒を差し引くと、通常の Pod グループには 40 秒が割り当てられます。最後の 20 秒は critical Pod 用です。これは設定された時間枠の説明であり、強制終了時に各 Pod の猶予時間が保証されるわけではありません。個々の `terminationGracePeriodSeconds` も適用されます。

</details>

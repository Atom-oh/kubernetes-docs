# Node Lifecycle Management クイズ

> このクイズでは、[Node Lifecycle Management](../../eks-hybrid-nodes/07-node-lifecycle.md) ドキュメントの理解度を確認します。

---

1. NodeConfig の kubelet 設定で `systemReserved` と `kubeReserved` を設定する主な目的は何ですか？
   - A) Pod のリソース要求を自動的に調整するため
   - B) Node の安定性を確保するために、システムプロセスと Kubernetes コンポーネント用のリソースを予約するため
   - C) Node で利用可能な総リソースを増やすため
   - D) Pod のスケジューリング優先度を決定するため

<details>
<summary>回答を表示</summary>

**回答: B) Node の安定性を確保するために、システムプロセスと Kubernetes コンポーネント用のリソースを予約するため**

**説明:**
`systemReserved` は OS とシステムデーモン（sshd、udev など）用のリソースを予約し、`kubeReserved` は kubelet と containerd 用のリソースを予約します。これにより、Pod が Node のすべてのリソースを消費することを防ぎ、Node の安定性を維持します。

</details>

---

2. kubelet の `evictionHard` と `evictionSoft` の違いは何ですか？
   - A) `evictionHard` はソフトリミットで、`evictionSoft` はハードリミットである
   - B) `evictionHard` は即時退避をトリガーし、`evictionSoft` は猶予期間後に退避する
   - C) `evictionHard` は Pod のみを退避し、`evictionSoft` は Node をシャットダウンする
   - D) 両方の設定は名前が異なるだけで同じように動作する

<details>
<summary>回答を表示</summary>

**回答: B) `evictionHard` は即時退避をトリガーし、`evictionSoft` は猶予期間後に退避する**

**説明:**
`evictionHard` のしきい値に達すると、kubelet はただちに Pod を退避します。`evictionSoft` は、しきい値が `evictionSoftGracePeriod` で指定された期間継続した場合にのみ退避し、Pod の突然の終了を防ぎます。

</details>

---

3. Kubernetes の version skew policy によると、EKS control plane がバージョン 1.31 の場合に実行できる最も古い kubelet バージョンは何ですか？
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

6. SSM Hybrid Activation の有効期限が切れた場合の正しい対応は何ですか？
   - A) 既存の activation の有効期限を延長する
   - B) 新しい SSM Hybrid Activation を作成し、nodeconfig.yaml を更新する
   - C) IAM Roles Anywhere に切り替える
   - D) 自動更新のために kubelet を再起動する

<details>
<summary>回答を表示</summary>

**回答: B) 新しい SSM Hybrid Activation を作成し、nodeconfig.yaml を更新する**

**説明:**
SSM Hybrid Activation は、有効期限が切れた後に有効期限を延長することはできません。新しい activation を作成し、nodeconfig.yaml の `activationCode` と `activationId` を更新し、必要に応じて Node を再登録する必要があります。

</details>

---

7. Kubernetes コンポーネントをアップグレードする正しい順序は何ですか？
   - A) まず Node をアップグレードし、その後 control plane をアップグレードする
   - B) control plane と Node を同時にアップグレードする
   - C) まず control plane (EKS) をアップグレードし、その後 Node をアップグレードする
   - D) 順序は重要ではない

<details>
<summary>回答を表示</summary>

**回答: C) まず control plane (EKS) をアップグレードし、その後 Node をアップグレードする**

**説明:**
Kubernetes の version skew policy によると、kubelet は API server より新しくすることはできません。常に最初に control plane をアップグレードし、その後 Node をアップグレードする必要があります。control plane より先に Node をアップグレードすると、互換性の問題が発生します。

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
`shutdownGracePeriodCriticalPods` は `shutdownGracePeriod` に含まれます。合計 60 秒の猶予期間から critical Pod 用に予約された 20 秒を差し引くと、通常の Pod 終了用に 40 秒が残ります。critical Pod（priority class system-cluster-critical または system-node-critical を持つ Pod）は最後の 20 秒間に終了されます。

</details>

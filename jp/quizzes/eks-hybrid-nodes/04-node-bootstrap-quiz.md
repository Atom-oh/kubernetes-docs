# EKS Hybrid Nodes nodeadmブートストラップクイズ

> **関連ドキュメント**: [Node bootstrap](../../eks-hybrid-nodes/04-node-bootstrap.md)
> **最終更新日**: 2026年9月12日

### 1. Hybrid nodeadmの役割は何ですか？

A. EKS control planeを作成する

B. `aws/eks-hybrid`実装を使ってHybrid Nodeのcomponentをインストールし、初期化する

C. アプリケーションPodをスケジュールする

D. CNI controllerを置き換える

<details>
<summary>解答を表示</summary>

**解答: B. `aws/eks-hybrid`実装を使ってHybrid Nodeのcomponentをインストールし、初期化する**

**解説:** EC2用の`amazon-eks-ami` nodeadmではなく、Hybrid用installerを使います。initの前に依存関係をインストールし、OS/runtimeに合う配布元を選び、承認済みbinaryであることを確認してください。現在のSSM新規インストールとupgradeにはnodeadm 1.0.19以降が必要です。

</details>

### 2. 通常のHybrid NodeConfigで使うcluster入力はどれですか？

A. cluster名とRegion、およびサポート対象のcredential provider

B. VPC IDとsubnet IDのみ

C. 手書きのname、endpoint、CAという3つの必須field

D. IAM userのaccess keyとpassword

<details>
<summary>解答を表示</summary>

**解答: A. cluster名とRegion、およびサポート対象のcredential provider**

**解説:** ドキュメントにあるHybrid configは`spec.cluster.name`と`spec.cluster.region`に加えて、`spec.hybrid.ssm`または`spec.hybrid.iamRolesAnywhere`を使います。準備済みのHybrid roleがcluster discovery権限を提供します。通常のHybrid初期化でraw PEMのCAを手作業でコピーする必要がある、という説明は正しくありません。

</details>

### 3. nodeadmでサポートされるcredential providerの組み合わせはどれですか？

A. IAM user keyとLDAP

B. static Kubernetes tokenとローカルpassword

C. SSM hybrid activationとIAM Roles Anywhere

D. EC2 instance profileとkubeconfig password

<details>
<summary>解答を表示</summary>

**解答: C. SSM hybrid activationとIAM Roles Anywhere**

**解説:** `ssm`または`iam-ra`のどちらか一方を選びます。SSM設定では`spec.hybrid.ssm`の下に`activationCode`と`activationId`を置きます。IAM Roles Anywhereでは`spec.hybrid.iamRolesAnywhere`を使います。どちらも、準備済みのHybrid roleとcluster accessが必要です。

</details>

### 4. kubeletの設定fieldではないものはどれですか？

A. `maxPods`

B. `clusterDNS`

C. `clusterDomain`

D. `podScheduler`

<details>
<summary>解答を表示</summary>

**解答: D. `podScheduler`**

**解説:** `podScheduler`はkubelet設定fieldではありません。schedulerはcontrol planeで動作します。以前の選択肢にあった`clusterCIDR`もkubelet設定fieldとして不適切だったため、旧問題は曖昧でした。NodeConfigのkubelet設定はCNI IPAMの計画に代わるものではありません。

</details>

### 5. init-command-completedのautomation recordで確認できることは何ですか？

A. Nodeが恒久的にReadyである

B. その時点でinit commandが完了し、ローカルcheckが通ったこと。cluster readinessは別途確認が必要

C. すべてのimage pullとcredential更新がテスト済みである

D. identityを含めてhostを安全にcloneできる

<details>
<summary>解答を表示</summary>

**解答: B. その時点でinit commandが完了し、ローカルcheckが通ったこと。cluster readinessは別途確認が必要**

**解説:** automation recordをhost/config/binaryに紐付け、処理が中断された場合はstarted状態を保持し、状態不明のまま自動再実行しないでください。`network-online.target`や`RemainAfterExit`は、AWSへの接続性やNode readinessの証明にはなりません。

</details>

### 6. Kubernetes API serverのCAは何のために使われますか？

A. TLS handshakeごとにkubelet client certificateを自動発行する

B. registry login credentialとして使う

C. server certificateへの信頼を検証する。client certificateの承認・発行は別の処理

D. Hybrid IAM roleを置き換える

<details>
<summary>解答を表示</summary>

**解答: C. server certificateへの信頼を検証する。client certificateの承認・発行は別の処理**

**解説:** serverのhostnameとCA chainを検証してください。信頼性の確認に`curl -k`を使ってはいけません。cluster CA、private registry CA、IAM Roles Anywhereのhost identityは、それぞれ異なる信頼用途です。

</details>

### 7. join失敗または初期化が一部だけ完了した場合、適切な対応はどれですか？

A. `nodeadm status`を実行してから、すぐに`uninstall --force`する

B. 範囲を限定してprivateなkubelet logとnodeadm debugを確認し、identity/networkを検証してから記録済み状態を調整する

C. 共有cluster内のCilium CRDをすべて削除する

D. Node objectを削除すればSSMも登録解除されるとみなす

<details>
<summary>解答を表示</summary>

**解答: B. 範囲を限定してprivateなkubelet logとnodeadm debugを確認し、identity/networkを検証してから記録済み状態を調整する**

**解説:** 確認したCLIには`nodeadm status`ではなく`nodeadm debug`があります。debugはAWS/cluster serviceへ接続するため、出力を非公開に保ってください。Node objectを削除してもkubeletは停止せず、SSMも登録解除されません。uninstallは管理された削除操作であり、一般的な認証修復手段ではありません。

</details>

### 8. Bottlerocket Pod Identityについて正しい説明はどれですか？

A. Ubuntuと同様にNodeConfigとnodeadmを使う

B. `settings.hybrid.ssm`だけで、ドキュメントにあるbootstrap要件をすべて満たす

C. Bottlerocket 1.39.0以降ではprovider bootstrapのcredential-file対応と`hybrid-bottlerocket` agent DaemonSetを使う

D. Base64形式のuser dataはprivate keyを暗号化する

<details>
<summary>解答を表示</summary>

**解答: C. Bottlerocket 1.39.0以降ではprovider bootstrapのcredential-file対応と`hybrid-bottlerocket` agent DaemonSetを使う**

**解説:** Bottlerocketには別個のsettings/bootstrap-container入力があります。互換性のあるagentの最低versionは`v1.3.7-eksbuild.2`で、一時credentialのpathは`/var/eks-hybrid/.aws/credentials`です。現行の互換add-onを選び、user dataを保護してください。encodingは暗号化ではありません。

</details>

### 9. Cilium lifecycleの適切な操作はどれですか？

A. 既存のcluster-pool CIDRをその場で変更する

B. Hybrid Nodeに対象を絞ったpreflightを行い、upgrade前にDaemonSetのcoverageとvalidation Deploymentのreadinessを確認する

C. 古いHelm値をすべて見直さず再利用する

D. Node一台を直すため、`cilium`を含む名前のCRDをすべてuninstallする

<details>
<summary>解答を表示</summary>

**解答: B. Hybrid Nodeに対象を絞ったpreflightを行い、upgrade前にDaemonSetのcoverageとvalidation Deploymentのreadinessを確認する**

**解説:** preflightには別個のNode selectorがあります。既存のpool elementとmask sizeは変更しないでください。拡張する場合は、レビュー済みの新しいpool entryを追加し、それに対応するEKS/routingの変更を行います。CNI/CRDの削除は、所有者が管理する影響の大きい作業です。

</details>

### 10. 確認対象のreleaseで`nodeadm uninstall --force`は何を意味しますか？

A. `/var/lib/kubelet`を含め、mount中のpathをすべて必ず削除する

B. 一般的な確認省略機能であり、drainの代わりになる

C. 追加のdefault pathを削除するが、v1.0.9以降で保護される`/var/lib/kubelet`の動作は変わらない

D. 新しいreplacement Nodeの状態を自動確認する

<details>
<summary>解答を表示</summary>

**解答: C. 追加のdefault pathを削除するが、v1.0.9以降で保護される`/var/lib/kubelet`の動作は変わらない**

**解説:** mount中のkubelet pathを無条件に削除しないでください。workloadを退避し、dataとprovider/CNIのcleanupを確認して、復旧用の証跡を保持します。承認済みの再インストールでは、uninstall後にinitだけを実行するのではなく、install → config check → initの順で行います。

</details>

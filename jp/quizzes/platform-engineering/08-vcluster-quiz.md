# vClusterクイズ

[vCluster](../../platform-engineering/08-vcluster.md)

元の8トピックをvCluster 0.37.0に照らしてレビューしました。

## 1. Shared Nodes vClusterは何を分離し、何を共有しますか？

<details>
<summary>解答を表示</summary>

仮想API、RBAC、controller、storeを分離し、workload node、kernel、CNI、CSIを共有できます。完全なhardware/network/performance分離は保証しません。

</details>

## 2. Syncerは何をしますか？

<details>
<summary>解答を表示</summary>

設定した仮想resource/参照をhost resourceへ変換し、観測状態を戻します。defaultと命名はmode/版次第で、全resourceが常に双方向同期するわけではありません。

</details>

## 3. PRプレビューに何が必要ですか？

<details>
<summary>解答を表示</summary>

検証済みprofile、host容量、信頼CI identity/event、明示namespace/context、cleanupです。30秒未満の作成や高速テストは保証されません。未信頼forkコードへhost認証情報を渡さないでください。

</details>

## 4. Pauseと自動Sleepをどう理解すべきですか？

<details>
<summary>解答を表示</summary>

現pauseはworkloadを除去しresumeで再作成し、PVC/Service保持は別です。メモリ保存suspendやbackupではありません。自動wake、利用権、実節約を別々に検証します。

</details>

## 5. Shared NodesでStorageClassとPVCはどう動きますか？

<details>
<summary>解答を表示</summary>

対応fromHost StorageClass設定とhost CSIを使い、PVCをhostへ同期します。binding mode、topology、回収/保持を確認します。0.37はsnapshot同期対応で、削除されたdeploy.volumeSnapshotControllerとは別です。

</details>

## 6. BackstageとGitOpsプロビジョニングを何でつなぎますか？

<details>
<summary>解答を表示</summary>

準備したaction/skeleton、レビュー済みPR、実ArgoCD project/destination/repository権限、values sourceです。debug:logは承認/デプロイ待機をしません。kubeconfigは承認済み認証情報経路で渡します。

</details>

## 7. NetworkPolicy追加で全hostアクセスを遮断できますか？

<details>
<summary>解答を表示</summary>

いいえ。Allowは加算的で別denyでは減らせません。Syncerはhost APIアクセスが必要です。profileはworkload公開Egressを無効にしますがcontrol-plane port許可を残すため、実CNI/経路検証が必要です。

</details>

## 8. デプロイモードをどう選びますか？

<details>
<summary>解答を表示</summary>

API自律性、node/kernel/CNI/CSI、account/admin境界、性能、lifecycle要件を評価します。未実測の速度、費用、規制適合性を約束せず、Shared Nodes、Dedicated/Private Nodes、Standalone、独立clusterを比較します。

</details>

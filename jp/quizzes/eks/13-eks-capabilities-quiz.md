# Amazon EKS Capabilities クイズ

> **最終更新日**: 2026年10月23日

測定結果とドキュメントにのみ記載された内容を区別するには、[ソース章](../../eks/13-eks-capabilities.md)を参照してください。

1. EKS Capabilities の Argo CD、kro、ACK コントローラーはどこで実行されますか？

   - A) 各ワーカーノード上の DaemonSet として
   - B) `kube-system` 名前空間内の Deployment として
   - C) AWS が所有するインフラストラクチャ上で実行され、ワーカーノード上には Pod がない
   - D) VPC 内に自動作成される Fargate プロファイル上

<details>
<summary>回答を表示</summary>

**回答: C) AWS が所有するインフラストラクチャ上で実行され、ワーカーノード上には Pod がない**

3つすべての機能で、ワーカーノード上に作成された Pod はゼロでした。コントローラーは機能ロールと EKS アクセスエントリを介して API サーバーを呼び出すため、プライベート専用の API エンドポイントでも動作します。同じ理由から、`kubectl logs` ではログを取得できません。Vended Logs を使用してください。

</details>

---

2. マネージド Argo CD の作成直後に、Application をローカルクラスターへ同期するには何が必要ですか？

   - A) 何も必要ない。ローカルクラスターは自動的に登録される
   - B) EKS ARN を使ったクラスター Secret と、機能ロールのアクセスエントリに付与されたデプロイ権限
   - C) `argocd cluster add` の実行
   - D) 常に `system:masters` が必要

<details>
<summary>回答を表示</summary>

**回答: B) EKS ARN を使ったクラスター Secret と、機能ロールのアクセスエントリに付与されたデプロイ権限**

自動作成されたアクセスエントリだけでは、`podtemplates is forbidden` エラーが発生しました。Argo CD はキャッシュを構築するためにすべてのリソースタイプを列挙するので、`AmazonEKSEditPolicy` だけでは不十分でした。`AmazonEKSAdminViewPolicy` を追加すると同期できるようになりました。cluster-admin は不要でした。

</details>

---

3. マネージド Argo CD で、コミットから Synced になるまでの数分間の遅延をなくすにはどうすればよいですか？

   - A) `argocd-cm` の `timeout.reconciliation` を30秒に下げる
   - B) 毎回機能を作り直す
   - C) 機能のサーバー URL にある `/api/webhook` に GitHub webhook を登録する
   - D) ノードを追加する

<details>
<summary>回答を表示</summary>

**回答: C) 機能のサーバー URL にある `/api/webhook` に GitHub webhook を登録する**

デフォルトのポーリングでは342～697秒を計測しました。また、マネージド機能ではポーリング間隔を設定するキーは変更できません。Webhook を使うと、同期にかかる時間は7.0～7.3秒でした。サーバー URL は AWS にホストされているため、別途パブリックエンドポイントを用意する必要はありません。

</details>

---

4. マネージド kro に RGD を適用した後、`ControllerReady=False` と「cache sync timeout」が表示されました。最も可能性の高い原因は何ですか？

   - A) AWS 側のコントローラー障害
   - B) `AmazonEKSKROPolicy` に、RGD が生成する API とその子リソースへの権限が不足している
   - C) RGD の CEL 構文エラー
   - D) ノードのメモリ不足

<details>
<summary>回答を表示</summary>

**回答: B) `AmazonEKSKROPolicy` に、RGD が生成する API とその子リソースへの権限が不足している**

デフォルトのポリシーが対象とするのは `kro.run` グループと CRD のみです。メッセージに「forbidden」と表示されないため、コントローラーの障害と誤解しやすい点に注意してください。アクセスエントリに Kubernetes グループを追加し、RGD ごとに ClusterRole をバインドして、RGD より先に適用してください。こうすることで待ち時間を回避できました（計測値は228秒で、おそらくコントローラーの再試行間隔です）。

</details>

---

5. テストで、kro インスタンスの子リソースと同じ名前の ACK Table CR がすでに存在していた場合、何が起きましたか？

   - A) kro がインスタンスの作成を拒否した
   - B) kro が既存の CR を引き継いで `spec.tableName` を変更し、元のテーブルは管理対象外のままになった
   - C) マネージド kro でのみ発生し、OSS では再現しない
   - D) ACK が2つの CR を自動的にマージした

<details>
<summary>回答を表示</summary>

**回答: B) kro が既存の CR を引き継いで `spec.tableName` を変更し、元のテーブルは管理対象外のままになった**

kro はサーバーサイド適用で CR を上書きし、`kro.run/owned=true` のラベルを付けました。インスタンスを削除すると、引き継がれた CR も削除されました。OSS 0.9.4 でも同じ動作をしたため、これは上流の挙動です。RGD ごとに異なる名前サフィックスを使い、名前空間を分離して対処してください。

</details>

---

6. マネージド ACK で、チームごとに異なる IAM 権限を付与するにはどうすればよいですか？

   - A) 各サービスコントローラーの ServiceAccount に IRSA を割り当てる
   - B) 機能ロールには AssumeRole 権限のみを付与し、`IAMRoleSelector` で名前空間をチームのロールに対応付ける
   - C) CARM を有効にし、名前空間のアノテーションでアカウントを設定する
   - D) マネージド機能ではチームごとの分離はできない

<details>
<summary>回答を表示</summary>

**回答: B) 機能ロールには AssumeRole 権限のみを付与し、`IAMRoleSelector` で名前空間をチームのロールに対応付ける**

SQS のみを許可するロールを持つ team-b の Bucket は、`AccessDenied` で失敗し、エラーメッセージには使用されたロールが示されました。OSS コントローラーで同じ設定を使う場合は、`featureGates.IAMRoleSelector=true` と `enableCARM=false` の両方が必要です。CARM を有効にしたままにすると CrashLoopBackOff が発生します。

</details>

---

7. ACK の外部で（CLI を使って）変更された SQS 属性について、テストでは何がわかりましたか？

   - A) マネージド ACK は必ず1分以内に変更を元に戻す
   - B) マネージド版も OSS 版も25分以内に定期的に変更を元に戻すことはなかった。マネージド版で変更が元に戻ったのは、コントローラーの再起動と思われるタイミングのみだった
   - C) OSS 版はリアルタイムイベントによって直ちに変更を元に戻す
   - D) マネージド版の再同期間隔は `disabledServices` で設定する

<details>
<summary>回答を表示</summary>

**回答: B) マネージド版も OSS 版も25分以内に定期的に変更を元に戻すことはなかった。マネージド版で変更が元に戻ったのは、コントローラーの再起動と思われるタイミングのみだった**

ACK は AWS 側の変更をリアルタイムでは監視しません。OSS 版のデフォルトの再同期間隔は10時間で、調整可能です。マネージド版の間隔は公開されておらず、固定されています。迅速な復旧が重要な場合は、SCP または IAM 条件を使って帯域外の変更をブロックしてください。

</details>

---

8. マネージド機能のコントローラーバージョンについて、正しい説明はどれですか？

   - A) `create-capability --version` でバージョンを固定できる
   - B) クラスターのバージョンをロールバックすると、機能のバージョンもロールバックされる
   - C) AWS がバージョンを選択して更新する。クラスターのアップグレードとは独立して変更される場合があり、`describe-capability` の `version` で確認できる
   - D) クラスターの Kubernetes バージョンをアップグレードした場合にのみ変更される

<details>
<summary>回答を表示</summary>

**回答: C) AWS がバージョンを選択して更新する。クラスターのアップグレードとは独立して変更される場合があり、`describe-capability` の `version` で確認できる**

作成 API と更新 API にバージョン引数はなく、1日違いで作成した Argo CD 機能では、それぞれ `3.4.6-eks-2` と `3.4.7-eks-1` が報告されました。バージョン変更を記録し、検証用クラスターを用意して、RETAIN ベースの一時的なセルフマネージドへのフォールバックに備えてください。バージョンの固定が必須要件であれば、セルフマネージドを選択してください。

</details>

---

9. プライベート専用のスポーククラスターで、ハブの Argo CD 機能が `CreateNamespace=true` を指定してアプリをデプロイするには、何が必要でしたか？

   - A) Transit Gateway とインバウンドのセキュリティグループルール
   - B) Edit、AdminView、`AmazonEKSArgoCDClusterPolicy` が付与された、ハブ機能ロール用のアクセスエントリ
   - C) スポーククラスター独自の Argo CD 機能
   - D) パブリック API エンドポイント

<details>
<summary>回答を表示</summary>

**回答: B) Edit、AdminView、`AmazonEKSArgoCDClusterPolicy` が付与された、ハブ機能ロール用のアクセスエントリ**

ネットワーク設定なしで接続と認証には成功しましたが、Edit と AdminView だけでは `namespaces is forbidden` エラーが発生しました。ハブではこのポリシーが自動的に付与されますが、リモートクラスターには手動でアタッチする必要があります。自動再試行が尽きた後、手動での同期が必要でした。

</details>

---

10. どのような場合に、マネージド機能よりセルフマネージドが適していますか？

   - A) 複数のプライベート EKS クラスターにデプロイするハブを構築する場合
   - B) 組織のサインインがすでに Identity Center に集約されている場合
   - C) Argo CD Notifications、CMP、または ACK FieldExport に依存し、さらに EKS 以外のクラスターにもデプロイする場合
   - D) 複数の AWS サービスを管理しているが、サービスごとにコントローラーを実行する負担が大きい場合

<details>
<summary>回答を表示</summary>

**回答: C) Argo CD Notifications、CMP、または ACK FieldExport に依存し、さらに EKS 以外のクラスターにもデプロイする場合**

マネージド機能には Notifications、CMP、`argocd admin`、Lua 標準ライブラリ、FieldExport がなく、クラスター Secret で受け入れられるのは EKS ARN のみです。その他の選択肢は、マネージド機能が適しているケースです。

</details>

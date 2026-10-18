# EKS Auto Mode 移行ガイドクイズ

> **関連ドキュメント**: [移行ガイド](../../eks-auto-mode/09-migration-guide.md)
> **最終更新**: 2026年9月12日

## 選択式問題

### 1. 移行用のキャパシティを有効化または削除する前に、何を行うべきですか？

- A) 古いノードグループを削除する
- B) ワークロード、依存関係、所有者、復旧要件を棚卸しする
- C) すべての Pod を drain する
- D) インスタンス名が一致すれば互換性があると判断する

<details>
<summary>回答を表示</summary>

**回答: B) ワークロード、依存関係、所有者、復旧要件を棚卸しする**

**解説:**
アカウント、クラスター、既存ノードグループの ID を特定し、配置、データ、IAM、ネットワーク、コントローラー、コスト、アプリケーションの正常性を調べてください。スケール変更や削除の前に各 wave を検証します。最後の検証段階が最初の正常性確認になるわけではありません。以下の読み取り専用診断で使うプライベートな WORK_DIR と KUBE_CONTEXT は、関連ガイドで設定します。
```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s \
  get deployments,statefulsets,daemonsets,jobs,cronjobs -A -o json |
jq '[.items[] | (.spec.template // .spec.jobTemplate.spec.template) as $t |
 {kind,namespace:.metadata.namespace,name:.metadata.name,uid:.metadata.uid,
  nodeSelector:$t.spec.nodeSelector,affinity:$t.spec.affinity,tolerations:$t.spec.tolerations,
  serviceAccountName:$t.spec.serviceAccountName,hostNetwork:$t.spec.hostNetwork,
  pvcNames:[$t.spec.volumes[]?.persistentVolumeClaim.claimName // empty]}]' \
  > "$WORK_DIR/workload-placement.json"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pods -A -o json |
jq '[.items[] | {namespace:.metadata.namespace,name:.metadata.name,node:.spec.nodeName,
  phase:.status.phase,deletionTimestamp:.metadata.deletionTimestamp,
  ready:([.status.conditions[]?|select(.type=="Ready")|.status]|first // "NotReported"),
  owners:[.metadata.ownerReferences[]?|{kind,name,controller}]}]' \
  > "$WORK_DIR/pod-state.json"
```


</details>

### 2. 既存の managed node と Auto Mode を、予測可能な形で共存させるにはどうしますか？

- A) 共存できない
- B) 各ワークロードに明示的な配置とコントローラーの所有者を設定する
- C) 別のクラスターだけを使う
- D) AWS リソースタグを一致させるだけでよい

<details>
<summary>回答を表示</summary>

**回答: B) 各ワークロードに明示的な配置とコントローラーの所有者を設定する**

**解説:**
既存ノードグループ専用の selector と、Auto pool／compute type を正確に指定する selector で、2 つのノード群を区別します。汎用的な Karpenter label は、セルフマネージドの Karpenter も対象にします。依存関係を移行し終えるまで、混在環境で必要な DNS／agent と、既存の storage／load balancer controller を維持してください。ここに示すのは Pod spec の断片です。ガイドには完全な canary Deployment が含まれています。

既存 managed group:
```yaml
# Pod template spec fragment
nodeSelector:
  eks.amazonaws.com/nodegroup: REPLACE_WITH_OLD_NODEGROUP
tolerations: []
```

Auto canary:
```yaml
# Pod template spec fragment
nodeSelector:
  karpenter.sh/nodepool: migration-pool
  eks.amazonaws.com/compute-type: auto
tolerations:
- key: migration
  operator: Equal
  value: auto-mode
  effect: NoSchedule
```


</details>

### 3. 移行リスクを抑えるには、どの順序が適切ですか？

- A) 重要な本番ワークロードから始める
- B) 影響の小さい代表的なワークロードから始め、より重要な依存先へ段階的に進む
- C) すべてを一度に移行する
- D) 順序を決めずに移行する

<details>
<summary>回答を表示</summary>

**回答: B) 影響の小さい代表的なワークロードから始め、より重要な依存先へ段階的に進む**

**解説:**
実際の依存関係に沿うなら、開発／ステージング、重要度の低い本番環境、重要な本番環境の順が適切です。配置を管理する controller／GitOps を更新してから、アプリケーションの動作、ストレージ、IAM、DNS、トラフィックを検証してください。優先度の低い配置設定や、根拠のない `node-type=auto-mode` label だけでは移行を証明できません。正常性が失敗または不明なら停止します。一定時間待つだけでは検証になりません。

</details>

### 4. 復旧手段を保つロールバック手順はどれですか？

- A) まずクラスターを削除して再作成する
- B) 互換性のある既存キャパシティと配置を復元して正常性を確認し、その後、該当する Auto リソースを退役させる
- C) 先に Auto NodePool を削除する
- D) Auto Mode を無効にするだけ

<details>
<summary>回答を表示</summary>

**回答: B) 互換性のある既存キャパシティと配置を復元して正常性を確認し、その後、該当する Auto リソースを退役させる**

**解説:**
既存キャパシティが Ready になるまで Auto pool を維持してください。意図した配置を確認して復元し、競合する Auto selector を残したり、無関係な affinity を消したりしないでください。Pod だけでなくデータとトラフィックも検証します。その後に、移行作業が所有するキャパシティだけを退役させます。NodePool の削除によって node が連鎖削除されることがあり、scaling JSON では削除済みの node group を再作成できません。これはワークロード移行のロールバックであり、Kubernetes バージョンのロールバックではありません。

</details>

### 5. 古い managed node group の desired size を減らす前に必要なことは何ですか？

- A) 直ちに 0 にする
- B) 移行済みワークロードを検証し、古いアプリケーション用キャパシティを cordon／退避し、その所有者と調整する
- C) 常にサイズを半分にする
- D) 5 分待つだけ

<details>
<summary>回答を表示</summary>

**回答: B) 移行済みワークロードを検証し、古いアプリケーション用キャパシティを cordon／退避し、その所有者と調整する**

**解説:**
MNG の scaling configuration の変更は ASG の縮退処理を使い、PDB を尊重しません。ガイドに示された確認処理では、旧ノードの cordon 状態と、DaemonSet 以外の稼働中 Pod を調べ、クエリが失敗した場合は停止します。システム依存関係とエクスポート済みジョブ結果を確認し、controller が旧ノードに Pod を再配置しないようにしてください。desired size を半分にして一定時間待っても、安全性の確認にはなりません。元の IaC／スケーリングの所有者が管理を続けます。

</details>

### 6. 移行中のコストはどのように監視すべきですか？

- A) すべての旧リソースを削除するまで無視する
- B) 現在のノード数を請求額そのものとみなす
- C) 可用性と性能に加え、並行稼働するノード群／ロードバランサーのコストを追跡する
- D) Auto Mode が旧リソースの料金をすべて自動的に削除すると想定する

<details>
<summary>回答を表示</summary>

**回答: C) 可用性と性能に加え、並行稼働するノード群／ロードバランサーのコストを追跡する**

**解説:**
共存期間中は、両方のノード群とトラフィック経路に料金が発生することがあります。実際の請求情報と、設定済みの運用データ収集元を確認してください。以下の以前のしきい値は検証されていない計画例であり、Auto Mode の既定メトリクスや通常範囲ではありません。

| 指標 | 以前の基準例 | 以前のアラート例 |
|--------|------------------|--------------------|
| Pending Pod | 0～5 | 5 分間 > 10 |
| プロビジョニング時間 | <90 秒 | >120 秒 |
| 可用性 | >99.9% | <99.5% |
| API レイテンシー | <200 ms | >500 ms |

Pending は unschedulable と同義ではありません。Running はアプリケーションの readiness ではなく、collector のデータがないことも障害がゼロであることを意味しません。

</details>

### 7. ワークロードの検証後、ロールバックの選択肢を維持するために後回しにできる作業はどれですか？

- A) アプリケーションの動作確認
- B) 想定どおりに配置されたかの確認
- C) 古い node-group 定義の削除
- D) データと controller の正常性確認

<details>
<summary>回答を表示</summary>

**回答: C) 古い node-group 定義の削除**

**解説:**
リソースやコストが残ることを考慮したうえで、明確に定めた安定化期間の間は古い定義／構成を保持してください。以前の「1～2 週間」という期間は一例であり、共通要件ではありません。すべての Pod が Running になることを求めるのではなく、実際の readiness と Job の成功を確認します。データ／トラフィック／ワークロードの検証後に、元の IaC 管理者を通じて削除してください。

</details>

### 8. 既存のセルフマネージド Karpenter controller について、正しい対応はどれですか？

- A) Auto Mode を有効にする前に必ず削除する
- B) 共存中は互換性のある Karpenter を維持し、旧リソースの finalization を終えてからアンインストールする
- C) 共有 Karpenter CRD をすべて削除する
- D) Karpenter label が付いた node をすべて削除対象にする

<details>
<summary>回答を表示</summary>

**回答: B) 共存中は互換性のある Karpenter を維持し、旧リソースの finalization を終えてからアンインストールする**

**解説:**
AWS は直接の共存移行手順を説明しています。Karpenter v1.1 は移行に必要な最低バージョンですが、現在の Kubernetes との互換性要件に代わるものではありません。別々の NodeClass 参照と taint 付き Auto pool を使ってください。共有 NodePool／NodeClaim CRD を変更または削除しないでください。既存 controller が finalization を完了できる状態で、旧構成が所有する NodePool／NodeClaim を退役させ、インスタンスと依存リソースの削除を確認してから、その controller の release／IAM／queue リソースだけを削除します。

</details>

## 参考資料

- [Managed node group のスケーリングと PDB](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html)
- [Auto Mode 移行リファレンス](https://docs.aws.amazon.com/eks/latest/userguide/migrate-auto.html)
- [Karpenter の共存移行](https://docs.aws.amazon.com/eks/latest/userguide/auto-migrate-karpenter.html)

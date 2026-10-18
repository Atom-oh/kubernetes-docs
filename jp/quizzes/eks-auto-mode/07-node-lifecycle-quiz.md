# EKS Auto Mode Node Lifecycle クイズ

> **関連ドキュメント**: [Node Lifecycle](../../eks-auto-mode/07-node-lifecycle.md)
> **最終更新**: 2026年9月12日

## 選択問題

### 1. 新しく作成される NodeClaim の経過時間ベースの有効期限を指定する NodePool field はどれですか？

- A) `nodeLifetime`
- B) `maxAge`
- C) `expireAfter`
- D) `rotationPeriod`

<details>
<summary>回答を表示</summary>

**回答: C) `expireAfter`**

**解説:**
この field は `spec.template.spec` の下にあります。Auto Mode では既定値 336h が文書化されており、NodePool で省略すると NodeClaim の termination grace は 24h になります。managed instance の最大 lifetime は 21 日であり、最低 uptime の保証ではありません。template を更新しても既存の claim は上書きされません。以前の開発環境 336h、staging 168h、production 72～168h、セキュリティ重視環境 24～48h という値は、未検証の policy 例であり、準拠に必要な interval ではありません。

```yaml
# Fragment of NodePool spec.template.spec
expireAfter: 168h
terminationGracePeriod: 24h
```

</details>

### 2. Auto Mode の NodeClaim が期限切れになると、何が起こりますか？

- A) 常に即座に消失する
- B) 事前に Ready な replacement が用意される保証なしに、termination/draining が始まる
- C) 通知だけが送信される
- D) 同じ instance が再起動される

<details>
<summary>回答を表示</summary>

**回答: B) 事前に Ready な replacement が用意される保証なしに、termination/draining が始まる**

**解説:**
Expiration は強制的な trigger であり、NodePool disruption budget による rate limit の対象ではありません。controller は通常の新規 scheduling を止め、drain/cleanup を試みます。PDB と Pod annotation は eviction に影響することがありますが、termination grace と AWS の lifetime 上限が保護期間を制限します。そのため、`nodes: 10%` の budget を設定しても、expiration が制御された 10% ずつの rolling update になるわけではありません。replacement capacity と application readiness は、それぞれ別の証拠で確認する必要があります。

</details>

### 3. EKS Auto Mode の OS 選択について正しい説明はどれですか？

- A) `amiFamily` で AL2023 を選択する
- B) Bottlerocket の variant は AWS が管理し、NodeClass は AMI family selector ではない
- C) `amiSelectorTerms` で custom AMI を選ぶ
- D) GPU node は customer-managed AL2023 を使う必要がある

<details>
<summary>回答を表示</summary>

**回答: B) Bottlerocket の variant は AWS が管理し、NodeClass は AMI family selector ではない**

**解説:**
Auto Mode は、そのような custom AMI interface や SSH/SSM access を公開していません。管理対象 image は accelerated workload にも対応します。以前のクイズにある AL2023 の 20～40 秒と Bottlerocket の 15～25 秒、また元資料にある 40～60 秒と 20～30 秒/20～40 秒という比較には、検証済みの測定根拠がありません。いずれも、起動が常に一方で速いことを示すものではありません。一般的な OS 比較は、Auto Mode の管理 interface とは別の話です。

</details>

### 4. Auto Mode の管理対象 image が更新され、既存 NodeClaim が drifted になった場合、何が起こり得ますか？

- A) すべての instance が直ちにその場で patch される
- B) 条件を満たす claim が、適用対象の graceful-disruption control の範囲で置き換えられる
- C) Node tag を任意に変更するまで何も起きない
- D) すべての node を同時に削除する必要がある

<details>
<summary>回答を表示</summary>

**回答: B) 条件を満たす claim が、適用対象の graceful-disruption control の範囲で置き換えられる**

**解説:**
`Drifted` condition、理由、現在の policy を確認してください。10% budget は切り上げられ、ほかに有効な limit と組み合わされます。1 台ずつの置き換えを意味しません。scheduling/PDB の制約と grace の意味も考慮してください。NodePool の変更すべてが drift を起こすわけではありません。互換性を保った requirement の拡張や、weight/limit/disruption の動作変更は、desired-state drift とは異なります。Auto Mode に `amiFamily` field はありません。

</details>

### 5. Expiration policy を短くすると、どのような trade-off が生じる可能性がありますか？

- A) コスト削減が保証される
- B) 再スケジューリングや warm-up/recovery 作業が増え、可用性に影響する可能性がある
- C) CVE が増えることが保証される
- D) 安定性が保証される

<details>
<summary>回答を表示</summary>

**回答: B) 再スケジューリングや warm-up/recovery 作業が増え、可用性に影響する可能性がある**

**解説:**
頻繁な置き換えにより、管理対象 image の rollout がより頻繁になる場合がありますが、必要な patch が提供されている証拠にも、すべての workload の脆弱性が修正される証拠にもなりません。capacity、image pull、checkpoint、recovery のコストが増える可能性もあります。EC2 Spot instance の interruption 発生確率自体が高くなるわけではありません。application recovery と node grace は別々に評価してください。NodePool budget では expiration を rate limit できません。

```yaml
# Fragment of NodePool spec.template.spec
expireAfter: 168h
terminationGracePeriod: 24h
```

</details>

### 6. Consolidation と expiration の条件が重なる場合、どう理解すべきですか？

- A) 常に consolidation が優先される
- B) expiration は必ず drift、その後 consolidation を待つ
- C) graceful な方法と強制 expiration は別の control path であり、全体に適用される一律の順序はない
- D) すべての処理を管理者が手動で選ぶ

<details>
<summary>回答を表示</summary>

**回答: C) graceful な方法と強制 expiration は別の control path であり、全体に適用される一律の順序はない**

**解説:**
graceful controller は consolidation より先に drift を評価します。expiration は独立した強制 path です。`drift > expiration > consolidation` のような全体順序や、最初に条件を満たしたものが常に勝つという保証は文書化されていません。作成から 5 日経過した node は 7 日の expiration より先に consolidation されることがあります。8 日経過した expired claim は、十分に利用されていても termination を開始する場合があります。

</details>

### 7. 緊急の node patch remediation を始める際、適切な手順はどれですか？

- A) すべての pool で `expireAfter` を 0 に設定する
- B) drift annotation を独自に作る
- C) 管理対象の修正を確認し、影響を受ける claim を特定して、health check を伴う単一 resource の手順を使う
- D) pool を一括削除し、順次置き換えと呼ぶ

<details>
<summary>回答を表示</summary>

**回答: C) 管理対象の修正を確認し、影響を受ける claim を特定して、health check を伴う単一 resource の手順を使う**

**解説:**
管理対象 image/fix が利用可能であることを確認し、レビュー済みの context で、単一 NodeClaim の UID、node との対応、PDB、永続状態、余剰または調達可能な capacity を調べます。適切であれば管理対象の drift を使います。手動置き換えは別途レビューし、次の node に進む前に health と image の根拠を再確認してください。見た目だけの `SecurityPatch` tag は patch trigger の保証ではありません。label の付いた node をすべて削除しても rolling update にはなりません。`--delete-emptydir-data` によって local data が失われる場合があります。

関連ガイドで `KUBE_CONTEXT` を設定します。以下の command は証拠の収集だけを行います。

```bash
: "${NODECLAIM_NAME:?Select one NodeClaim for review}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaim "$NODECLAIM_NAME" -o json |
  jq '{name:.metadata.name,uid:.metadata.uid,node:.status.nodeName,
       pool:.metadata.labels["karpenter.sh/nodepool"],imageID:.status.imageID,
       expireAfter:.spec.expireAfter,terminationGracePeriod:.spec.terminationGracePeriod,
       conditions:[.status.conditions[]?|{type,status,reason}]}'
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pdb -A -o json |
  jq '[.items[]|{namespace:.metadata.namespace,name:.metadata.name,
       observedGeneration:.status.observedGeneration,generation:.metadata.generation,
       currentHealthy:.status.currentHealthy,desiredHealthy:.status.desiredHealthy,
       disruptionsAllowed:.status.disruptionsAllowed}]'
```

</details>

### 8. Upstream の `expireAfter: Never` は Auto Mode node を無期限に保持できますか？

- A) 保守や interruption も含めて保持できる
- B) できない。Auto Mode の managed instance には 21 日の最大 lifetime が引き続き適用される
- C) Pod に PDB があれば保持できる
- D) すべての stateful workload で保持できる

<details>
<summary>回答を表示</summary>

**回答: B) できない。Auto Mode の managed instance には 21 日の最大 lifetime が引き続き適用される**

**解説:**
upstream の syntax は、Auto Mode の service lifetime を上書きする許可ではありません。`Never` を使って Auto Mode の database や長時間 job を単一 instance 上で永久に実行する方法として推奨しないでください。また、実際に試さずに特定の admission response が保証されると推測しないでください。checkpoint、外部の永続 storage、recovery を計画します。drift、interruption、その他の lifecycle action がこれより前に起こる可能性もあります。

</details>

## 参考資料

- [Auto Mode NodePool の既定値](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Auto Mode の最大 lifetime](https://docs.aws.amazon.com/eks/latest/userguide/auto-security.html)
- [Disruption と drift](https://karpenter.sh/v1.14/concepts/disruption/)

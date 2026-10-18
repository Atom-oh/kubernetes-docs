# Crossplane クイズ

[Crossplane](../../platform-engineering/07-crossplane.md)

元の8つのトピックは、Crossplane 2.4を基準にレビューされています。

## 1. Composition は何を提供しますか？

<details>
<summary>回答を表示</summary>

Function pipeline は XR の入力を目的のリソースに対応付けます。複数の AWS 操作を原子的に実行する機能や、リソースの準備完了を保証する機能ではありません。

</details>

## 2. v2 XR は従来の Claim とどのように異なりますか？

<details>
<summary>回答を表示</summary>

XRD v2 のデフォルトは Namespaced で、利用者は XR を直接作成できます。従来の v1 LegacyCluster XRD では、cluster-scoped XR と namespace-scoped Claim が引き続き使われます。現在の XR や MR がすべて cluster-scoped というわけではありません。

</details>

## 3. IRSA または Pod Identity を選ぶだけで、最小権限が実現しますか？

<details>
<summary>回答を表示</summary>

いいえ。ServiceAccount、OIDC の audience/subject または association、role policy を設定してください。また、実行時の所有権、ProviderConfig へのアクセス、AssumeRole の境界も制約する必要があります。

</details>

## 4. Terraform と Crossplane の主な違いは何ですか？

<details>
<summary>回答を表示</summary>

どちらも宣言的な状態を扱います。Terraform は plan/apply のワークフローを中心とし、Crossplane は継続的な調整を中心とします。Terraform も自動化できます。また、Crossplane も Provider の対応状況、ポリシー、クォータ、エラーの影響を受けます。

</details>

## 5. ACK と Crossplane はどのように併用できますか？

<details>
<summary>回答を表示</summary>

外部リソースの所有権を分けてください。ACK は namespace-scoped な CR と参照も提供し、kro と組み合わせることもできます。同じ AWS リソースを複数の controller に変更させないでください。

</details>

## 6. v2 では接続情報の Secret をどのように提供しますか？

<details>
<summary>回答を表示</summary>

MR の writeConnectionSecretToRef は引き続き使えますが、XR から core-native に公開する機能は削除されています。Secret を Composition で構成するか、サポートされている Function による集約を使ってください。この例では endpoint/username のみを集約し、password は別途準備した Secret を使います。

</details>

## 7. Backstage/GitOps のワークフローはどのようなものですか？

<details>
<summary>回答を表示</summary>

準備済みの skeleton/action を使って XR YAML を生成し、レビュー済みの PR をマージした後、ArgoCD と Crossplane/Provider で調整し、実際の準備完了状態を確認します。PR の作成、catalog への登録、AWS リソースのプロビジョニング完了は、それぞれ異なる状態です。

</details>

## 8. Drift の修正とリソース保持は何によって制御されますか？

<details>
<summary>回答を表示</summary>

Provider が対応するフィールド、managementPolicies、polling を確認してください。v2 の namespace-scoped MR は Delete を含めないことで外部リソースを保持します。これは従来の deletionPolicy: Orphan とは異なります。リソースを保持する場合も、バックアップ、認証情報、コスト、所有権に関する責任は残ります。

</details>

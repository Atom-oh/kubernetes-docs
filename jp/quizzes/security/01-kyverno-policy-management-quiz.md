# Kyverno Policy 管理クイズ

> **最終更新**: September 13, 2026

これらの問題では、レビュー済みの Kyverno 1.19.1 CEL policy を使用します。例はローカルの fixture であり、クラスターや破壊的なクリーンアップは実行されていません。

## クイズ問題

### 1. Kyverno とは何ですか？

- A) admission と、個別に設定される background/lifecycle controller を備えた Kubernetes policy engine。
- B) 脆弱性スキャナーのみ。
- C) API server 認証の代替。
- D) service mesh の dataplane。

<details>
<summary>答えを表示</summary>

**回答: A) admission と、個別に設定される background/lifecycle controller を備えた Kubernetes policy engine。**

Kyverno policy は、設定されたスコープの範囲内で検証 (validate)、変更 (mutate)、生成 (generate)、image の検証、削除を行います。現行の v1 policy は YAML/JSON 内で CEL を使用します。従来の ClusterPolicy パターンと JMESPath は別の言語です。Kubernetes ネイティブなパッケージングであっても、policy の式を学ぶ必要がなくなるわけではありません。

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: require-team
spec:
  validationActions:
  - Audit
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: object.metadata.?labels.team.orValue('') != ''
    message: A nonempty team label is required.
```

</details>

<span id="_2-which-of-the-following-is-not-a-policy-type-supported-by-kyverno"></span>

### 2. policy の動作の違いを正しく説明しているのはどれですか？

- A) すべての policy は admission 時のみ実行され、他のオブジェクトを変更することはない。
- B) Audit は生成と削除を読み取り専用にする。
- C) すべての GET/list リクエストは admission webhook によってインターセプトされる。
- D) 検証、変更、生成、スケジュールされた削除は、それぞれ異なる controller、設定、権限を持つ。

<details>
<summary>答えを表示</summary>

**回答: D) 検証、変更、生成、スケジュールされた削除は、それぞれ異なる controller、設定、権限を持つ。**

Kubernetes の認証 (例: OIDC や ServiceAccount token) と認可 (RBAC) は admission policy とは別のものであり、Authenticate は Kyverno の policy action ではありません。DeletingPolicy は schedule と条件を使用します。cleanup.ttl を持つ ClusterPolicy rule はその API ではありません。無関係な検証 policy が Audit であっても、変更/生成/削除はリソースを変更しえます。明示的な lab セレクター、必要な RBAC、復旧計画を用意してください。次の任意の削除定義は schema を理解するために示すものであり、適用されておらず、24 時間の経過時間しきい値を実装するものでもありません。

```yaml
apiVersion: policies.kyverno.io/v1
kind: DeletingPolicy
metadata:
  name: cleanup-lab-completed-pods
spec:
  schedule: 0 1 * * *
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      resources:
      - pods
      scope: Namespaced
    namespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: policy-lab
  conditions:
  - name: explicitly-approved-completed
    expression: object.metadata.?labels['training.example.com/disposable'].orValue('') == 'true' && object.?status.phase.orValue('')
      in ['Succeeded', 'Failed']
```

</details>

### 3. 現行の ValidatingPolicy において、validationActions: [Audit] と [Deny] はどう異なりますか？

- A) どちらも一致した違反を常に拒否する。
- B) Audit は一致した違反をレポート目的で許可し、Deny は一致する admission 時にそれらを拒否する。
- C) Audit は既存の違反オブジェクトを削除する。
- D) Deny はリソースを自動的に書き換える。

<details>
<summary>答えを表示</summary>

**回答: B) Audit は一致した違反をレポート目的で許可し、Deny は一致する admission 時にそれらを拒否する。**

webhook の failurePolicy は評価/転送の失敗を扱うもので、これとは別です。ローカル CLI の fail 結果は policy 違反を記録するものであり、Audit policy が実際のリクエストを拒否した証拠ではありません。従来の API では Enforce/Audit の failure action はフィールド名が異なるため、意図的に移行してください。

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: require-container-limits
spec:
  validationActions:
  - Audit
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: variables.containers.all(c, has(c.resources) && has(c.resources.limits) && ['cpu', 'memory'].all(k, k in c.resources.limits
      && string(c.resources.limits[k]) != ''))
    message: Normal and init containers need nonempty CPU and memory limits.
  variables:
  - name: containers
    expression: object.spec.containers + object.spec.?initContainers.orValue([])
```

</details>

<span id="_4-what-field-is-used-in-kyverno-to-select-which-resources-a-policy-applies-to"></span>

### 4. CEL ベースの ValidatingPolicy では、リソースのスコープはどのように選択されますか？

- A) トップレベルの target 文字列だけで十分。
- B) matchConstraints と任意の matchConditions を使用し、kind、operation、namespace、リクエストデータの利用可否を確認する。
- C) すべての policy は自動的にあらゆる Kubernetes リソースに一致する。
- D) metadata.name を唯一のセレクターとして使用する。

<details>
<summary>答えを表示</summary>

**回答: B) matchConstraints と任意の matchConditions を使用し、kind、operation、namespace、リクエストデータの利用可否を確認する。**

従来の ClusterPolicy は rule の match/exclude 構造を使用しますが、これは現行の CEL のフィールド構成ではありません。リソースおよびユーザーの条件は、OR/AND の省略記法だと想定せず、式として理解する必要があります。admission から得られるユーザー/ロール情報は、background スキャンでは常に利用できるとは限りません。namespace のラベルセレクターも、そのラベルを変更できる者によって制御されます。

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: require-team
spec:
  validationActions:
  - Audit
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: object.metadata.?labels.team.orValue('') != ''
    message: A nonempty team label is required.
```

</details>

<span id="_5-which-policy-type-in-kyverno-automatically-modifies-resources-on-policy-violation"></span>

### 5. このリソースのデフォルト設定を行う mutation が既存の値に対して安全なのはなぜですか？

- A) すべての container を同一の limits で上書きするから。
- B) CREATE 時に、まったく未設定の通常 container の resources のみを補完し、既存の完全な設定や部分的な設定を保持するから。
- C) 最初の container の値を他のすべての container にコピーするから。
- D) Kyverno の式の中で Helm の if/hasKey 文を使用しているから。

<details>
<summary>答えを表示</summary>

**回答: B) CREATE 時に、まったく未設定の通常 container の resources のみを補完し、既存の完全な設定や部分的な設定を保持するから。**

実際の CLI 出力を、完全に設定された入力オブジェクトおよび部分的に設定された入力オブジェクトと比較したところ、変更されていませんでした。部分的なフィールドは個別のレビューが必要です。既存の小さい limit を超える request を作成しないでください。ApplyConfiguration と JSONPatch はセマンティクスが異なり、JSONPatch は既存の親パスを必要とします。また、独立した policy の実行順序は保証されません。

```yaml
apiVersion: policies.kyverno.io/v1
kind: MutatingPolicy
metadata:
  name: default-unset-resources
spec:
  evaluation:
    mutateExisting:
      enabled: false
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  mutations:
  - patchType: ApplyConfiguration
    applyConfiguration:
      expression: |-
        Object{spec: Object.spec{containers: object.spec.containers.map(c,
          (!has(c.resources) || ((!has(c.resources.requests) || c.resources.requests.size() == 0) &&
            (!has(c.resources.limits) || c.resources.limits.size() == 0)))
          ? Object.spec.containers{name: c.name, resources: Object.spec.containers.resources{
              requests: {"cpu": "250m", "memory": "256Mi"},
              limits: {"cpu": "500m", "memory": "512Mi"}
            }}
          : Object.spec.containers{name: c.name}
        )}}
```

</details>

### 6. GeneratingPolicy が有用なのはどのような場合ですか？

- A) 一致した trigger から、必要な権限を持って明示的に選択された downstream リソースを作成する場合。
- B) 削除されたすべてのリソースを自動的にバックアップする場合。
- C) 作成時に namespace の分離をアトミックに保証する場合。
- D) background controller の RBAC を回避する場合。

<details>
<summary>答えを表示</summary>

**回答: A) 一致した trigger から、必要な権限を持って明示的に選択された downstream リソースを作成する場合。**

この Deployment の例では opt-in と 2 つ以上の desired replicas が必要であり、spec.selector 全体をコピーします。生成は非同期になりえます。同期、data ソースと clone ソースの違い、generate-existing、orphaning の設定は更新/削除の挙動に影響します。承認されたソース/ターゲットの境界なしに、registry Secret をすべての新しい namespace に clone しないでください。

```yaml
apiVersion: policies.kyverno.io/v1
kind: GeneratingPolicy
metadata:
  name: generate-lab-pdb
spec:
  evaluation:
    synchronize:
      enabled: false
    generateExisting:
      enabled: false
    orphanDownstreamOnPolicyDelete:
      enabled: true
  matchConstraints:
    resourceRules:
    - apiGroups:
      - apps
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - deployments
  matchConditions:
  - name: approved-deployment
    expression: object.metadata.namespace == 'policy-lab' && object.metadata.?labels['training.example.com/managed'].orValue('')
      == 'true' && object.spec.?replicas.orValue(1) >= 2
  generate:
  - expression: |-
      generator.Apply(object.metadata.namespace, [{
        "apiVersion": dyn("policy/v1"), "kind": dyn("PodDisruptionBudget"),
        "metadata": dyn({"name": object.metadata.name + "-pdb", "namespace": object.metadata.namespace}),
        "spec": dyn({"minAvailable": 1, "selector": object.spec.selector})
      }])
```

</details>

<span id="_7-what-policy-type-is-used-in-kyverno-to-verify-container-image-signatures"></span>

### 7. container image の署名と attestation を検証する現行の Kyverno の type はどれですか？

- A) ResourceQuota。
- B) ImageValidatingPolicy。
- C) ServiceMonitor。
- D) LimitRange。

<details>
<summary>答えを表示</summary>

**回答: B) ImageValidatingPolicy。**

従来の ClusterPolicy の verifyImages rule は、新しい manifest の kind とは異なります。image セキュリティガイドで説明されている、サポート対象の Cosign または Notary/Notation の信頼パス、正確な署名者/発行者/鍵のルール、registry アクセスを設定してください。任意の GPG や Docker Content Trust の資材はそのままの代替にはなりません。検証は脆弱性スキャンではなく、自動的に registry の許可リストになるものでもありません。digest の mutation を設定すると image の参照が変わりえます。この章では registry/署名の操作は実行していません。

[Image セキュリティガイド](../../security/07-image-security.md)

</details>

<span id="_8-what-does-the-background-false-setting-mean-in-a-kyverno-policy"></span>

### 8. background の検証スキャンを無効にすると、どういう意味になりますか？

- A) その検証設定では既存リソースが定期的にスキャンされなくなるが、一致する admission の更新は引き続きチェックされる。
- B) すべての既存リソースが admission から恒久的に除外される。
- C) この設定はすべての Kyverno controller を停止する。
- D) 既存の policy 違反が削除される。

<details>
<summary>答えを表示</summary>

**回答: A) その検証設定では既存リソースが定期的にスキャンされなくなるが、一致する admission の更新は引き続きチェックされる。**

現行の type では spec.evaluation.background.enabled を使用します。従来の ClusterPolicy では background を使用していました。どちらも mutate-existing、生成、cleanup に対するグローバルなスイッチではありません。background のレポート自体は、すでに保存されているリソースを修復したり、拒否したり、削除したりはしません。admission の operation と match 条件が引き続き更新を制御します。

</details>

### 9. PolicyReport の表現として正しいのはどれですか？

- A) resource フィールドと、results とは無関係な summary カウントを持つ status フィールド。
- B) resources/result のエントリと、それらのエントリと整合する summary カウントを持つ PolicyReport。
- C) すべてのレポートは文字列の timestamp.created を使用しなければならない。
- D) ClusterPolicyReport は、すべての namespace レポートを任意に集約したものを意味する。

<details>
<summary>答えを表示</summary>

**回答: B) resources/result のエントリと、それらのエントリと整合する summary カウントを持つ PolicyReport。**

デフォルトの chart プロファイルは Policy WG のレポートを使用します。PolicyReport は namespace スコープであり、ClusterPolicyReport はクラスタースコープのリソースを対象とします。これは合成した schema の例であり、実際に収集した証跡ではありません。指定する timestamp は整数の秒/ナノ秒を使用します。他のレポートバックエンドは個別に検証する必要があります。

```yaml
apiVersion: wgpolicyk8s.io/v1alpha2
kind: PolicyReport
metadata:
  name: example-report
  namespace: policy-lab
summary:
  pass: 1
  fail: 1
  warn: 0
  error: 0
  skip: 0
results:
- policy: require-team
  source: kyverno
  resources:
  - apiVersion: v1
    kind: Pod
    name: good
    namespace: policy-lab
  result: pass
- policy: require-team
  source: kyverno
  resources:
  - apiVersion: v1
    kind: Pod
    name: missing-label
    namespace: policy-lab
  result: fail
  message: A nonempty team label is required.
```

</details>

<span id="_10-what-command-line-tool-can-be-used-to-test-policies-in-kyverno"></span>

### 10. これらの Kyverno policy はローカルでどのようにテストすべきですか？

- A) kyverno apply --cluster を実行してすべての policy をインストールする。
- B) test manifest ディレクトリを指定して kyverno test を使用する、またはローカルのリソースファイルを指定して kyverno apply を使用する。
- C) 存在しない汎用の kyverno validate コマンドを実行する。
- D) Helm のレンダリングが成功すれば policy の挙動と RBAC が証明される。

<details>
<summary>答えを表示</summary>

**回答: B) test manifest ディレクトリを指定して kyverno test を使用する、またはローカルのリソースファイルを指定して kyverno apply を使用する。**

ガイドでは、成功する入力と失敗が期待される入力を含む policy-lab-tests を提供しています。kyverno test --require-tests は、空のテストフォルダーを受け入れてしまうのを防ぎます。kyverno apply はリソースを評価します。--cluster は評価のために選択したクラスターを読み取るものであり、インストールではありません。--output は変更/生成されたオブジェクトの出力先パスを取ります。サポートされているヘルパー向けに create サブコマンドが存在しますが、create disallow-latest-tag のようなテンプレートコマンドを勝手に作り出さないでください。

```bash
kyverno test ./policy-lab-tests --require-tests --warnings-as-errors
kyverno apply ./policy-lab-tests/require-team.yaml \
  --resource ./policy-lab-tests/pod-missing.yaml \
  --continue-on-error=false --warn-no-pass --warn-exit-code 2
```

</details>

[ガイドに戻る](../../security/01-kyverno-policy-management.md)

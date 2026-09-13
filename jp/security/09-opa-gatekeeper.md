# OPA Gatekeeper

> **検証ベースライン**: Gatekeeper/Gator 3.23.1 · Helm chart 3.23.1

> **最終更新**: September 13, 2026

## 概要

Gatekeeper は、Kubernetes admission と定期監査の際にポリシーを評価します。ConstraintTemplate はロジックとパラメータスキーマを定義し、Constraint はスコープ、値、enforcementAction を定義します。[完全な例](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/gatekeeper)では、専用の `policy-lab` namespace とローカルテストを使用します。すべてのテストフィクスチャを本番クラスタに適用しないでください。

![Gatekeeper admission と定期監査。Template がロジックを定義し、Constraint がスコープを選択します。](../.gitbook/assets/en-security-09-opa-gatekeeper-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-security-09-opa-gatekeeper-0.html)

<span id="gatekeeper-vs-kyverno-comparison"></span>

## Gatekeeper と Kyverno の選択

要件、テスト、運用モデルに基づいて、Gatekeeper の Rego/Constraint モデルと Kyverno の Kubernetes 指向ポリシーモデルを選択してください。Gatekeeper は任意で CEL ベースの Kubernetes ネイティブ検証もサポートします。サポートされない固定的なリソース使用量ランキングや、別のエンジンが複雑なロジックを表現できないという主張は避けてください。OPA の CNCF 卒業は、Gatekeeper が別個に卒業したプロジェクトであることを示すものではありません。

<span id="installation-with-helm"></span>

<span id="installation-with-manifests"></span>

<span id="verify-installation"></span>

## Gatekeeper のインストール

例ディレクトリの固定された chart とサポートされている値を使用してください。`auditInterval` と `logLevel` は chart のトップレベルフィールドです。任意の `audit.replicas` や `audit.logLevel` の値が有効になると想定しないでください。このプロファイルでは、3 つの webhook レプリカと 1 つの audit Deployment がレンダリングされます。EKS control plane から webhook へのネットワークパス、証明書、配置、利用可能なリソースを検証してください。

```bash
helm repo add gatekeeper https://open-policy-agent.github.io/gatekeeper/charts
helm repo update gatekeeper
helm upgrade --install gatekeeper gatekeeper/gatekeeper --version 3.23.1 \
  --namespace gatekeeper-system --create-namespace --values values.yaml --wait
kubectl -n gatekeeper-system rollout status deployment/gatekeeper-controller-manager
kubectl -n gatekeeper-system rollout status deployment/gatekeeper-audit
```

段階的なロールアウトでは、`values.yaml` は webhook の `failurePolicy: Ignore` を明示的に維持します。そのため、Constraint が `deny` を指定していても、webhook 呼び出しの失敗によってリクエストが許可される可能性があります。`Fail` は API の可用性、復旧、除外する namespace と合わせて評価してください。webhook のスコープは、個々の Constraint のスコープより広くなることがあります。

### Template と Constraint の順序

Template は対応する Constraint CRD を生成します。Constraint を適用する前に、Established CRD を待機し、template Pod のステータスを確認してください。すべての例の Constraint は `dryrun` で開始します。対象環境向けにイメージプレフィックス、パラメータ、namespace を確認してください。

```bash
kubectl create namespace policy-lab --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f templates/
kubectl wait --for=condition=Established --timeout=90s \
  crd/docsrequiredlabels.constraints.gatekeeper.sh \
  crd/docsnoprivileged.constraints.gatekeeper.sh \
  crd/docsapprovedimages.constraints.gatekeeper.sh \
  crd/k8scontainerlimits.constraints.gatekeeper.sh \
  crd/docsuniqueingress.constraints.gatekeeper.sh
kubectl apply -f constraints/
```

<span id="rego-language-basics"></span>

<span id="rego-syntax-overview"></span>

<span id="rego-data-types"></span>

<span id="rego-operators-and-built-in-functions"></span>

## Rego と入力コントラクト

Gatekeeper ポリシーでは、汎用的な OPA AdmissionReview の例にある `input.request` ではなく `input.review` を使用します。`input.parameters` は Constraint の値を提供し、`data.inventory` は同期された Kubernetes オブジェクトを提供します。既存の `targets[].rego` は、デフォルトでサポートされる Rego v0 を使用します。Rego v1 は `code[].source.version: v1` により明示的に選択されます。古い v0 Template が自動的に無効になることはありません。

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: docsrequiredlabels
spec:
  crd:
    spec:
      names:
        kind: DocsRequiredLabels
      validation:
        openAPIV3Schema:
          type: object
          properties:
            labels:
              type: array
              minItems: 1
              items:
                type: string
                minLength: 1
          required:
          - labels
  targets:
  - target: admission.k8s.gatekeeper.sh
    code:
    - engine: Rego
      source:
        version: v1
        rego: "package docsrequiredlabels\nvalid_label(key) if {\n  value := input.review.object.metadata.labels[key]\n\
          \  is_string(value)\n  value != \"\"\n}\nviolation contains {\"msg\": sprintf(\"\
          required nonempty label: %v\", [key])} if {\n  some key in input.parameters.labels\n\
          \  not valid_label(key)\n}\n"
```

`violation contains ... if` は v1 の部分集合ルールです。複数の定義がその集合に寄与しますが、これは競合する完全ドキュメントルールが常に OR として結合されることを意味するものではありません。ルール本文内の条件はすべて満たされる必要があります。再帰的なユーザー定義ルールと、`walk` のような JSON トラバーサル組み込み関数を区別してください。

```rego
package examples
items := [x | some x in input.items; x > 10]
keys := object.keys(object.get(input, "labels", {}))
missing := {"app", "team"} - keys
```

`obj[_]` はオブジェクト値を選択します。ラベルキーが必要な場合は、`object.keys` を使用するか、キーを明示的にバインドしてください。集合差 `-`、積集合 `&`、和集合 `|` は有用なポリシー操作です。

<span id="writing-constraint-templates"></span>

<span id="basic-structure"></span>

<span id="preventing-privileged-containers"></span>

<span id="enforcing-resource-limits"></span>

<span id="restricting-image-registries"></span>

<span id="defining-constraints"></span>

<span id="basic-constraint-writing"></span>

<span id="using-namespace-selectors"></span>

<span id="resource-limits-constraint"></span>

<span id="image-registry-constraint"></span>

## ポリシーとスコープ

| Template | チェック | スコープと制限 |
|---|---|---|
| DocsRequiredLabels | 必須の空でないラベル | Pod メタデータ。Deployment メタデータは Pod template ラベルと異なります |
| DocsNoPrivileged | privileged=true を拒否 | 通常、init、ephemeral コンテナ。完全な PSS スイートではありません |
| DocsApprovedImages | 承認済み registry/path プレフィックス | 3 種類すべてのコンテナ。スキーマには末尾の `/` 境界が必要です |
| K8sContainerLimits | CPU/memory limit の存在と最大値 | 固定された upstream ポリシー。ephemeral コンテナはリソースフィールドを設定できないため、通常/init コンテナが対象です |
| DocsUniqueIngress | 同期された inventory 内の厳密な host 競合 | 同一オブジェクトの更新を除外。ワイルドカードやアトミックな同時作成の保証はありません |

### イメージ境界と例外

`registry.example.com/team/` は `registry.example.com/team-evil/` および `registry.example.com.evil/` と異なります。プレフィックス一致には区切り境界と完全修飾イメージ名のコントラクトが必要です。この例では、`skip-privileged-check=true` のようなワークロード制御のバイパスラベルは提供しません。namespace の例外には、ラベル変更に対する制御された RBAC、認可、有効期限、監査記録が必要です。

### リソース量

Gi/Mi/Ki 専用のパーサーは、`9G` やプレーンバイトに対して undefined を返し、違反を見逃す可能性があります。この例では、サポートされない文字列を違反として報告する upstream の `K8sContainerLimits` ポリシーを固定しています。Kubernetes が許可するすべての量表現を受け入れるわけではないため、その形式制限を文書化してください。ネイティブテストでは、millicore、10 進数/2 進数 memory、プレーンバイト、数値入力、明示的に引用した指数文字列を区別します。YAML パーサーが `8e9` のような文字列フィクスチャを数値に変換しないように、引用符で囲んでください。

### PSS と Controller リソース

少数の privileged/runAsNonRoot チェックを完全な Baseline/Restricted の適用と表現しないでください。バージョン化された PSS は、host namespace、seccomp、capability、OS の違い、Pod レベルの継承、ephemeral コンテナも対象とします。[Pod Security Standards ガイド](./03-pod-security-standards.md)を使用してください。これらの例は Pod admission をチェックします。Controller の Pod template をより早く評価するには、別の template または ExpansionTemplate テストを構成してください。

<span id="advanced-policy-patterns"></span>

<span id="external-data-reference"></span>

<span id="cross-namespace-policies"></span>

<span id="complex-condition-policies"></span>

## 同期データと参照ポリシー

`sync.yaml` は `networking.k8s.io/v1` Ingress オブジェクトを inventory に同期します。これは、外部 HTTP provider や任意の OPA bundle に接続することとは異なります。必要なオブジェクトのみを同期し、RBAC、memory、機密データを確認してください。

```yaml
apiVersion: config.gatekeeper.sh/v1alpha1
kind: Config
metadata:
  name: config
  namespace: gatekeeper-system
spec:
  sync:
    syncOnly:
    - group: networking.k8s.io
      version: v1
      kind: Ingress
```

同じ namespace 内の異なる名前、または異なる namespace 内の同じ名前でも競合する可能性があります。namespace と名前の両方が異なることを要求すると、そのようなケースを見逃します。この例では、自己更新として同じ namespace/名前のみを除外します。inventory は結果整合性を持つため、同時作成に対する一意性をアトミックに保証することはできません。

<span id="mutation-features"></span>

<span id="using-assignmetadata"></span>

<span id="using-assign"></span>

<span id="conditional-mutation"></span>

<span id="using-modifyset"></span>

## Mutation

AssignMetadata はサポートされているメタデータの label/annotation を追加します。これは汎用的な上書きメカニズムではありません。Assign はフィールドを設定します。toleration リスト全体を割り当てると既存のエントリが破棄される可能性があるため、この例では ModifySet merge を使用します。この toleration は専用の lab taint を許可しますが、Spot ノードを選択するものではありません。

```yaml
apiVersion: mutations.gatekeeper.sh/v1
kind: ModifySet
metadata:
  name: docs-dedicated-toleration
spec:
  applyTo:
  - groups:
    - ''
    versions:
    - v1
    kinds:
    - Pod
  match:
    scope: Namespaced
    namespaces:
    - policy-lab
  location: spec.tolerations
  parameters:
    operation: merge
    values:
      fromList:
      - key: dedicated
        operator: Equal
        value: policy-lab
        effect: NoSchedule
```

mutation/defaulting を validation から分離してください。CREATE/UPDATE のスコープ、繰り返し適用、他の mutator との収束、既存オブジェクトへの影響を確認してください。mutator を作成しても、既存のすべてのオブジェクトが自動的に書き換えられるわけではありません。

<span id="audit-configuration"></span>

<span id="checking-constraint-violations"></span>

<span id="prometheus-metrics"></span>

<span id="grafana-dashboard"></span>

## 監査とモニタリング

監査頻度は chart の `auditInterval` で設定します。Config の `validation.traces` は、監査をスケジュールするためではなく、選択した admission 評価をデバッグするためのものです。admission 入力と Rego print には機密オブジェクトデータが含まれる可能性があります。必要なスコープでのみ有効にしてください。`constraintViolationsLimit` はステータス詳細リストの上限を設定します。これは totalViolations と異なる場合があります。

```bash
kubectl get constraints
kubectl describe docsrequiredlabels required-labels
kubectl get constrainttemplatepodstatuses -n gatekeeper-system
kubectl get constraintpodstatuses -n gatekeeper-system
```

chart の webhook Service は、metrics ではなく HTTPS webhook トラフィックのみを公開します。`podmonitor.yaml` は、audit と webhook の両方の Deployment にある実際の名前付き metrics:8888 container port を選択します。最初に Prometheus Operator CRD をインストールし、PodMonitor の label/namespace selector を整合させてください。

| Metric | 解釈 |
|---|---|
| gatekeeper_validation_request_count | 実際の admission_status ラベルを持つ validation リクエスト |
| gatekeeper_validation_request_duration_seconds | Validation レイテンシヒストグラム |
| gatekeeper_violations | enforcement_action 別の監査済み違反。デフォルトの constraint_name ラベルを仮定しないでください |
| gatekeeper_audit_last_run_end_time | 最後に完了した監査のタイムスタンプ |
| gatekeeper_constraint_templates | Template ステータス数 |

```promql
sum by (enforcement_action) (gatekeeper_violations)
histogram_quantile(0.99, sum by (le) (rate(gatekeeper_validation_request_duration_seconds_bucket[5m])))
```

<span id="testing-and-ci-cd-integration"></span>

<span id="gator-cli-testing"></span>

<span id="test-suite-definition"></span>

<span id="test-fixtures"></span>

<span id="github-actions-integration"></span>

## Gator テストと CI

公式の 3.23.1 リリースアセットをインストールし、公開されている checksum を検証してください。ARM64 バイナリは GitVersion に +dirty を報告します。監査では、このテキストがローカル変更を意味すると想定するのではなく、公開アーカイブの hash を検証しました。バージョンが固定された証拠を、固定されていない @latest CLI 実行で置き換えないでください。

```bash
gator version
gator verify tests/suite.yaml --verbose
gator test -f templates/docsnoprivileged.yaml \
  -f constraints/no-privileged.yaml \
  -f tests/fixtures/tenant-skip-label-no-bypass.yaml --output=json
```

`verify` は Suite 内の期待される違反をチェックし、`test -f` は Template/Constraint に対して manifest を評価します。Suite がないディレクトリは verify が無視することがあるため、終了ステータスだけを信頼せず、5 件のテストと 33 件のケースすべてが実行されたことを確認してください。フィクスチャイメージはポリシー入力であり、pull 可能なワークロードではありません。CI は認証情報なしでローカル Suite を実行します。cluster dry-run は、認可されたアクセスを持つ別の信頼できる環境に属します。

<span id="best-practices"></span>

<span id="policy-organization"></span>

<span id="gradual-policy-rollout"></span>

<span id="policy-exception-management"></span>

<span id="troubleshooting"></span>

<span id="common-issues"></span>

<span id="debugging-tips"></span>

## ロールアウトとトラブルシューティング

同じ値が設定された Constraint を dryrun→warn→deny と移行し、監査/admission の結果と例外を確認してください。ロールアウトのメカニズムとして、パラメータのない Constraint を 3 つ作成しないでください。Dryrun/warn は Gator テストの終了ステータスがゼロでも違反を返すことがあります。deny 違反は 1 を返します。webhook の可用性障害は、ポリシー違反とは別に監視してください。

```bash
kubectl get validatingwebhookconfiguration gatekeeper-validating-webhook-configuration -o yaml
kubectl -n gatekeeper-system logs deployment/gatekeeper-controller-manager --tail=100
kubectl -n gatekeeper-system logs deployment/gatekeeper-audit --tail=100
```

ポリシー入力、match スコープ、CRD/template エラー、webhook 証明書/ネットワーク、監査タイムスタンプ、inventory の鮮度を確認してください。webhook の適用を変更したり、namespace の例外を広げたりする前に原因を診断してください。

<span id="summary"></span>

<span id="related-documentation"></span>

## 検証スコープと関連資料

Gator3.23.1 は 33 件のポリシーケースと 3 つの適用モードを実行しました。チェック対象は、固定された Helm render、8 個の Gatekeeper CRD オブジェクト、audit/webhook PodMonitor バインディングです。Kubernetes admission、EKS ネットワーク、ライブの audit-cache 同期、API failover は実行していません。ネイティブ mutation 検証はレビュー報告書に別途記録されています。

- [Gatekeeper クイズ](../quizzes/security/09-opa-gatekeeper-quiz.md)
- [Kyverno](./01-kyverno-policy-management.md)
- [Pod Security Standards](./03-pod-security-standards.md)
- [EKS セキュリティプラクティス](./06-eks-security-best-practices.md)

## 参考資料

- [Gatekeeper v3.23.1](https://github.com/open-policy-agent/gatekeeper/tree/v3.23.1)
- [ConstraintTemplate と Rego バージョン](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/constrainttemplates.md)
- [Gator](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/gator.md)
- [Mutation](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/mutation.md)
- [Audit](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/audit.md)
- [Metrics](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/metrics.md)
- [固定された resource-limits ポリシー](https://github.com/open-policy-agent/gatekeeper-library/blob/bd333d4704647b1000cef5a92017257ee46fe2c8/library/general/containerlimits/template.yaml)

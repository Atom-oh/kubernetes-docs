# Kyvernoによるポリシー管理

> **検証ベースライン**: Kyverno/CLI 1.19.1、Helm chart 3.9.1。現在のリリースガイドでは Kubernetes 1.33～1.35 がテスト対象として掲載されています。chart のより広範なインストール制約は互換性の保証ではありません。
> **最終更新**: September 13, 2026

Kyverno は Kubernetes policy を評価し、明示的に設定された mutation、generation、deletion を実行します。これらの例は、実際の CLI とリリース済みの schema/chart を使用してローカルで確認しました。live cluster へのインストール、admission、network isolation、cleanup、AWS integration は実行していません。

元の `ClusterPolicy` の例は、`policies.kyverno.io/v1` CEL policy に更新されています。公式の 1.19 migration guide では、ClusterPolicy/Policy、CleanupPolicy、従来の `kyverno.io` PolicyException は非推奨とされ、1.20 での削除が予定されています。これらは 1.19 ですでに存在しないわけではありません。単に apiVersion string を置き換えるのではなく、アップグレード前に migrate と test を実施してください。

## Lab環境のセットアップ

### 必要なツール

target API server でサポートされる version skew の kubectl、OCI 対応のサポート対象 Helm release、およびこれらのローカルテスト用に検証済みの Kyverno 1.19.1 CLI を使用します。CLI と一致する OS/architecture の archive を取得し、公開済み checksum/signature を検証してください。1.10.0 の archive を再利用したり、未検証の download を root installation に pipe したりしないでください。

まずローカルファイルから始めます。以下の policy は一括適用するセットではなく、独立した例です。Pod の例は `policy-lab` を対象とし、generation にはさらに明示的な label が必要です。これらの policy、namespace label、Role、PolicyException を変更できるユーザーを制限してください。これらの selector 自体は RBAC security boundary ではありません。

### Kyvernoのインストール

専用の `kyverno` namespace を準備します。共有 cluster を変更する前に、選択した EKS/Kubernetes version、API-server-to-webhook connectivity、DNS、admission failure/timeout の動作、CRD upgrade procedure を確認してください。Kubernetes ServiceAccounts/RBAC が controller を認可します。Kyverno のインストール自体には AWS administrator role は必要ありません。

## Kyvernoの概要

### Kyvernoアーキテクチャと仕組み

| コンポーネント | 責任 | 
|---|---|
| Admission controller | 一致する admission request と policy validation/mutation/image check。すべての GET/list request ではありません |
| Background controller | Generate と明示的に有効化された mutate-existing 作業 |
| Reports controller | Policy result の集計/reporting |
| Cleanup controller | Scheduled deletion policy と許可された cleanup 操作 |

validating policy は、既存の非準拠 resource を削除または修復しません。Background reporting、mutate-existing、generate-existing、scheduled deletion は、それぞれ異なる権限を必要とする別個の mechanism です。Generation は asynchronous になり得ます。namespace の作成と生成された NetworkPolicy の enforcement は atomic operation ではありません。

### KyvernoとOPA Gatekeeperの比較

Kyverno の現行 policy では YAML/JSON manifest 内で CEL を使用します。従来の policy では pattern と JMESPath も使用します。Kubernetes-native packaging により policy expression の学習が不要になるわけではありません。Gatekeeper は ConstraintTemplates/Constraints と、その version でサポートされる policy engine を使用し、admission/audit/mutation 機能はそれぞれ別です。必要な feature、expression language、policy test、controller availability、測定済みの workload impact を比較してください。以前の「easy/complex」と「good/very good performance」という評価は、benchmark ではなく根拠のない比較でした。

## Kyvernoのインストール

### Helmを使用したインストール

これを `kyverno-values.yaml` として保存します。これは single-replica の **lab** profile です。ServiceMonitor CRD と、実際の namespace/label を選択する Prometheus installation がすでに存在している必要があります。例の `release: kube-prom` label をその installation の selector に置き換えるか、準備が整うまで ServiceMonitor を無効にしてください。

```yaml
admissionController:
  replicas: 1
  serviceMonitor:
    enabled: true
    additionalLabels:
      release: kube-prom
backgroundController:
  replicas: 1
  serviceMonitor:
    enabled: true
    additionalLabels:
      release: kube-prom
cleanupController:
  replicas: 1
  serviceMonitor:
    enabled: true
    additionalLabels:
      release: kube-prom
reportsController:
  replicas: 1
  serviceMonitor:
    enabled: true
    additionalLabels:
      release: kube-prom
```

```bash
# Use an approved context; this changes real cluster resources.
: "${KUBE_CONTEXT:?Set the reviewed cluster context}"
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update kyverno
helm template kyverno kyverno/kyverno --version 3.9.1 \
  --namespace kyverno --values kyverno-values.yaml > kyverno-rendered.yaml
# Inspect the render, CRD migration and webhook reachability before installation.
helm upgrade --install kyverno kyverno/kyverno --version 3.9.1 \
  --namespace kyverno --create-namespace --kube-context "$KUBE_CONTEXT" \
  --values kyverno-values.yaml
```

render には 4 つの controller Deployment と 4 つの metrics ServiceMonitor が含まれます。replica を増やすには topology、disruption、resource sizing、webhook availability の計画が必要です。controller あたり 1 replica は HA design ではありません。chart version label を application version と解釈するのではなく、現行 chart の default と実際に render された image tag を確認してください。

### YAML Manifestを使用したインストール

GitOps が YAML を管理する場合は、固定した chart を render し、その CRD、RBAC、certificate、hook を管理対象のセットとして review してください。render の raw `kubectl apply` は Helm の hook/upgrade semantics を実行しません。新しい release の上に古い 1.10.0 install.yaml を適用したり、同じ controller を複数の owner で管理したりしないでください。

## Policyタイプ

### 1. Validation Policy

この独立した例を `require-limits.yaml` として保存します。これは **normal container と init container** の空でない CPU/memory limit をチェックします。ephemeral container は resource request/limit を宣言できません。以下の security check で別途カバーします。これは選択された per-container policy であり、すべての Kubernetes workload がこの resource strategy を使用すべきだという主張ではありません。

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

`validationActions: [Audit]` は、一致する admission request を許可しながら violation を記録します。`[Deny]` は staging/impact review 後にそれらを拒否します。`Warn` は client warning を提供できます。Webhook の `failurePolicy` は evaluation/transport failure を制御する別の設定です。offline CLI failure result は、Audit policy が live request を拒否したことを示すものではありません。

### 2. Mutation Policy

`add-default-label.yaml` として保存します。明示的に空の値を含む既存の `environment` label は保持されます。これは Kyverno 内で Helm Go-template の `if`/`hasKey` syntax ではなく、CEL ApplyConfiguration を使用します。

```yaml
apiVersion: policies.kyverno.io/v1
kind: MutatingPolicy
metadata:
  name: add-default-label
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
      - UPDATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  mutations:
  - patchType: ApplyConfiguration
    applyConfiguration:
      expression: |-
        has(object.metadata.labels) && 'environment' in object.metadata.labels
        ? Object{}
        : Object{metadata: Object.metadata{labels: {"environment": object.metadata.namespace}}}
```

この例では mutate-existing を無効にしています。admission mutation は一致する CREATE/UPDATE request には引き続き影響する可能性があります。JSONPatch の代替では、child key を追加する前に存在しない labels map を作成し、JSON Pointer path の `/` を `~1` として escape する必要があります。独立した policy 間で mutation order は保証されません。

### 3. Generation Policy

`generate-networkpolicy.yaml` として保存します。`training.example.com/managed: "true"` を持つ `policy-lab` という名前の Namespace のみがこの例を trigger します。Namespace object の場合は、`metadata.namespace` や従来の namespace exclusion list ではなく、その **name/label** に一致させます。

```yaml
apiVersion: policies.kyverno.io/v1
kind: GeneratingPolicy
metadata:
  name: generate-lab-networkpolicy
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
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - namespaces
  matchConditions:
  - name: approved-lab-namespace
    expression: object.metadata.name == 'policy-lab' && object.metadata.?labels['training.example.com/managed'].orValue('')
      == 'true'
  generate:
  - expression: |-
      generator.Apply(object.metadata.name, [{
        "apiVersion": dyn("networking.k8s.io/v1"),
        "kind": dyn("NetworkPolicy"),
        "metadata": dyn({"name": "lab-default-deny", "namespace": object.metadata.name}),
        "spec": dyn({"podSelector": {}, "policyTypes": ["Ingress", "Egress"]})
      }])
```

workload がこの namespace に依存する前に、必要な DNS/API/application allow rule を準備してください。Kubernetes NetworkPolicy isolation には enforcement を行う CNI が必要です。他の allow policy は additive であり、host-network behavior を考慮する必要があります。ローカルで生成された manifest は、traffic が block された証拠ではありません。

ここでは synchronization と generate-existing を無効にしています。この policy をインストールしても、すでに存在する Namespace は自動的に backfill されません。後続の一致する trigger を使用するか、その設定を変更する前に generate-existing の有効化を明示的に review してください。synchronization を有効にすると、downstream lifecycle は data と clone source、trigger change、`orphanDownstreamOnPolicyDelete` に依存します。これは汎用的な backup/rollback mechanism ではありません。Secret の共有には、新しい namespace ごとに copy するのではなく、明示的な source/target allowlist と RBAC/credential-lifecycle review が必要です。

### 4. Scheduled Deletion

`DeletingPolicy` は `spec.schedule` と CEL condition を使用します。これは validation とは別で、validationActions Audit switch はありません。cleanup controller には明示的な deletion permission が必要です。狭い namespace/object label と明確な age/status retention requirement を優先し、選択された candidate を確認してから、schedule を有効にする前に recovery を test してください。任意の quiz 例は、マークされた完了済み Pod を選択します。これは「24 時間より古い」ことを意味するものではなく、ここでは scheduled deletion は実行していません。

## EKSにおけるKyvernoユースケース

### EKSとKyvernoの統合アーキテクチャ

EKS API server は、設定された Kubernetes network/RBAC path を使用して一致する admission webhook を呼び出します。CloudWatch export は、独自の IAM と retention を持つ別途設定された collector/integration です。Kyverno をインストールしても、すべての PolicyReport が自動的に CloudWatch に送信されるわけではありません。secret を含む可能性のある raw admission payload を出力しないでください。

### 1. Security Hardening

#### Privileged Containerの防止

存在しない `privileged` は false として扱われます。この check は normal、init、ephemeral container を対象とします。宣言された `pods/ephemeralcontainers` matching については、target environment で live admission/subresource test が引き続き必要です。

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: disallow-privileged
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
      - pods/ephemeralcontainers
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: variables.containers.all(c, !c.?securityContext.privileged.orValue(false))
    message: Privileged normal, init and ephemeral containers are not allowed.
  variables:
  - name: containers
    expression: object.spec.containers + object.spec.?initContainers.orValue([]) + object.spec.?ephemeralContainers.orValue([])
```

#### Root User実行の防止

この policy は、各 container の override または Pod-level default を使用し、有効な runAsNonRoot を必須とし、明示的な有効 UID 0 を拒否します。これは宣言を validation します。runtime では kubelet/image behavior も引き続き重要です。

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: require-non-root
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
      - pods/ephemeralcontainers
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: variables.containers.all(c, c.?securityContext.runAsNonRoot.orValue(object.spec.?securityContext.runAsNonRoot.orValue(false))
      && c.?securityContext.runAsUser.orValue(object.spec.?securityContext.runAsUser.orValue(-1)) != 0)
    message: Use effective runAsNonRoot=true and do not select UID 0.
  variables:
  - name: containers
    expression: object.spec.containers + object.spec.?initContainers.orValue([]) + object.spec.?ephemeralContainers.orValue([])
```

### 2. Cost Optimization

#### Resource Limitの設定

`default-resources.yaml` として保存します。この CREATE-only の例は、通常の update 中に実行中の Pod resource を変更することを避け、normal container に **request も limit もない** 場合にのみ default を提供します。workload sizing を上書きしたり、既存の小さな limit より大きい request を生成したりする代わりに、完全または部分的な既存 resource setting を保持します。部分的な setting は別途 review してください。これは欠落するすべての field を補完するものでも、init/ephemeral resource を default 化するものでもありません。

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

#### 特定Instance Typeの強制

元の instance name は説明用の allowlist であり、現在の推奨ではありません。明示的な nodeSelector は必須の scheduling constraint です。この admission-only CREATE policy は指定された nodeName を拒否します。scheduled Pod は正当に nodeName を取得するため、background scanning は無効です。node label、scheduler/binding permission、利用可能な capacity への信頼は別の問題です。宣言の check では、Pod の bind または Node の変更を許可された principal に対する placement を保証できません。

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: approved-node-selector
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
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: object.spec.?nodeName.orValue('') == '' && object.spec.?nodeSelector['node.kubernetes.io/instance-type'].orValue('')
      in ['m5.large', 'c5.large', 'r5.large']
    message: Use an approved instance-type nodeSelector and do not bypass the scheduler with nodeName.
  evaluation:
    background:
      enabled: false
```

### 3. Compliance

#### PodDisruptionBudgetの自動生成

この opt-in Deployment の例では、少なくとも 2 つの desired replica が必要であり、存在しない可能性のある top-level app label ではなく、matchExpressions を含む **完全な spec.selector** を copy します。これは 2 replica が Ready であることを証明するものではありません。この static lab budget には、特に synchronization を無効にしている場合、scaling または selector change 後に別途 ownership/review の判断が必要です。PDB は eligible な voluntary eviction を制約しますが、すべての rollout や involuntary failure を制約するものではありません。

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

background controller には、生成される resource を作成する実際の permission が必要です。render された `kyverno` release について、この追加の namespace Role/Binding は狭い PDB grant を例示しています。chart にはすでに他の controller permission が含まれています。これを controller の全有効 RBAC policy と呼ばないでください。ServiceAccount name を render に合わせ、target cluster で authorization を検証してください。

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: kyverno-lab-pdb-writer
  namespace: policy-lab
rules:
- apiGroups:
  - policy
  resources:
  - poddisruptionbudgets
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
  - delete
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: kyverno-lab-pdb-writer
  namespace: policy-lab
subjects:
- kind: ServiceAccount
  name: kyverno-background-controller
  namespace: kyverno
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: kyverno-lab-pdb-writer
```

#### Namespace ResourceQuotaの自動生成

同じ明示的な Namespace opt-in が適用されます。Quota value は lab policy であり、AWS budget や cost cap ではありません。有効にする前に workload request、init container、limit、既存 quota を考慮してください。

```yaml
apiVersion: policies.kyverno.io/v1
kind: GeneratingPolicy
metadata:
  name: generate-lab-quota
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
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - namespaces
  matchConditions:
  - name: approved-lab-namespace
    expression: object.metadata.name == 'policy-lab' && object.metadata.?labels['training.example.com/managed'].orValue('')
      == 'true'
  generate:
  - expression: |-
      generator.Apply(object.metadata.name, [{
        "apiVersion": dyn("v1"), "kind": dyn("ResourceQuota"),
        "metadata": dyn({"name": "lab-resource-quota", "namespace": object.metadata.name}),
        "spec": dyn({"hard": {"requests.cpu": "10", "requests.memory": "10Gi",
          "limits.cpu": "20", "limits.memory": "20Gi", "pods": "50"}})
      }])
```

## Policy TestingとValidation

### Policy適用ワークフロー

policy ownership と scope を review し、positive/negative/skip case をローカルで test して、生成/変更された object を確認した後、live admission と controller permission を stage してください。Audit は validation action であり、mutation、generation、deletion を無害にするものではありません。Pod-controller autogeneration と native ValidatingAdmissionPolicy/MutatingAdmissionPolicy generation は、互換性の制限がある別個の opt-in です。すべての controller template が対象になると想定するのではなく、生成された policy status を確認してください。

### Policy Simulation

`policy-lab-tests/` を作成し、以下の 4 ファイルをそこに保存します。この test は意図的に `missing-label` の violation を期待します。test suite が pass しても、すべての input が準拠しているのではなく、expectation が一致したことを意味します。

`require-team.yaml`:

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

`pod.yaml`（ローカル fixture。image は pull されません）:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: good
  namespace: policy-lab
  labels:
    team: platform
spec:
  containers:
  - name: app
    image: registry.example.com/app:fixture
```

`pod-missing.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: missing-label
  namespace: policy-lab
spec:
  containers:
  - name: app
    image: registry.example.com/app:fixture
```

`kyverno-test.yaml`:

```yaml
apiVersion: cli.kyverno.io/v1alpha1
kind: Test
metadata:
  name: team-label-local-test
policies:
- require-team.yaml
resources:
- pod.yaml
- pod-missing.yaml
results:
- policy: require-team
  kind: Pod
  resources:
  - good
  result: pass
- policy: require-team
  kind: Pod
  resources:
  - missing-label
  result: fail
```

```bash
kyverno version
kyverno test ./policy-lab-tests --require-tests --warnings-as-errors
# Offline evaluation; this does not install a policy or modify cluster resources:
kyverno apply ./policy-lab-tests/require-team.yaml \
  --resource ./policy-lab-tests/pod-missing.yaml \
  --continue-on-error=false --warn-no-pass --warn-exit-code 2
# For mutation/generation, --output takes a file/directory path, not a format name:
kyverno apply add-default-label.yaml --resource ./policy-lab-tests/pod.yaml --output ./mutated/
```

### Policy Validation

`kyverno test` は test manifest を含む directory を受け取ります。`kyverno apply` は、指定された resource に対して policy を評価します。`--cluster` は evaluation のために選択された cluster から resource を読み取ります。これは policy installation command ではありません。review 済みの policy をインストールするには kubectl/GitOps を使用し、cluster を変更します。固定した CLI help を参照してください。汎用的な `kyverno validate` または `kyverno create disallow-latest-tag` のワークフローは test 済み interface ではありません。`create` はサポート対象の Kyverno helper resource に対しては存在します。

## Policy MonitoringとReporting

### Policy Report

default profile は Policy WG の `PolicyReport`/`ClusterPolicyReport` API を使用します。PolicyReport は namespaced です。ClusterPolicyReport は、単にすべての namespace をまとめたものではなく、cluster-scoped resource を対象とします。reporting configuration とサポートされる rule type が重要です。Background scan は validation result を report します。既存 object を遡って deny、mutate、delete するものではありません。background scanning が無効でも、既存 object は update 時に一致する admission check の対象であり続けます。

これは cluster から収集した report ではなく、**synthetic schema example** です。result には `resource`/`status` ではなく `resources` と `result` を使用します。timestamp を指定する場合は integer seconds/nanos を使用します。summary count は entry と一致する必要があります。

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

実際の report は `kubectl get policyreports -n policy-lab` と `kubectl get clusterpolicyreports` で query します。Reports Server/OpenReports は別個の任意 installation/configuration です。backend を想定する前に、実際にインストールされた API を確認してください。

### Prometheus Metrics

上記の test 済み values から、chart が作成する metrics Service と controller ごとの ServiceMonitor を使用します。これらの Service port name は 8000 の `metrics-port` であり、`app: kyverno` ではなく component/instance/part-of selector を使用します。render はこれらを `kyverno` に配置し、`namespaceSelector.matchNames: [kyverno]` を設定します。Prometheus はそれらの monitor と namespace を選択する必要があります。resource の存在は scraping や CloudWatch export の証明ではありません。

## ベストプラクティス

### 1. 段階的ロールアウト

新しい validation を Audit で stage し、実際の report と exception を review してから、適切な箇所で Deny を選択してください。webhook failure policy、timeout、replica availability、emergency recovery を確認します。generation、mutation-existing、destructive deletion の review は分けてください。

### 2. Exception Handling

狭い matchConstraints/matchConditions は無制限の exemption と同等ではありません。namespace scope、name、kind、admission/user information availability を review してください。user/role information に依存する classic rule は、background scan で評価可能であると想定できません。CEL PolicyException は `policies.kyverno.io/v1`、明示的な policyRefs/matchConditions、および必要に応じて expiresAt を使用します。これを作成できるユーザーを制限し、installation/configuration support を検証してください。exception は authorization-sensitive object であり、すべての application team に付与すべき admission bypass ではありません。

### 3. Policy Organization

test と owner を伴う versioned validation、mutation、generation、deletion policy を維持してください。従来の ClusterPolicy pattern/JMESPath は CEL と異なります。output comparison を行いながら rule 単位で migrate してください。image signature verification は現行 API では `ImageValidatingPolicy` です。attestor/registry/trust prerequisite については、[image security guide](./07-image-security.md) を参照してください。signature verification は vulnerability scanning や包括的な registry allowlist ではありません。

## 結論

ローカル validation では、実際の Kyverno 1.19.1 policy evaluation と output preservation、リリース済み API schema、chart rendering を対象にしました。live webhook ordering/autogeneration、controller RBAC、networking、image trust、destructive lifecycle action は実行していません。これらは deployment acceptance check として残ります。

- [Kyvernoのリリースとテスト済みKubernetes version](https://kyverno.io/docs/installation/releases/)
- [インストールとcontrollerの責任](https://kyverno.io/docs/installation/installation/)
- [CELへの移行](https://kyverno.io/docs/guides/migration-to-cel/)
- [ValidatingPolicy](https://kyverno.io/docs/policy-types/validating-policy/)
- [MutatingPolicy](https://kyverno.io/docs/policy-types/mutating-policy/)
- [GeneratingPolicy](https://kyverno.io/docs/policy-types/generating-policy/)
- [DeletingPolicy](https://kyverno.io/docs/policy-types/deleting-policy/)
- [Kyverno CLI](https://kyverno.io/docs/kyverno-cli/reference/kyverno/)

## クイズ

[Kyverno Policy Management Quiz](../quizzes/security/01-kyverno-policy-management-quiz.md) を試してください。

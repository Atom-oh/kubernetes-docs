# Helm パッケージマネージャー

> **最終更新**: September 12, 2026
> **ローカル検証**: Helm 3.21.3 / Helm 4.3.0

Helm は chart をレンダリングし、Kubernetes リソースと release 履歴を管理します。Chart version、appVersion、image tag/digest、release revision はそれぞれ異なる値です。Helm 4 は既存の apiVersion:v2 chart を受け入れますが、CLI/apply/wait の動作は対象バージョンで確認する必要があります。

## 基本概念と権限

Helm 3 では Tiller が削除され、client は自身の Kubernetes credentials/RBAC を使用します。Chart-repository/OCI-registry との通信は Kubernetes API へのアクセスとは別です。Tiller を削除しても、安全でない chart や広範な権限が無害になるわけではありません。

release storage はデフォルトで release namespace 内の Secrets です。ConfigMap/SQL backend などの代替手段も設定できます。保存される release data には manifests/values が含まれ、機密情報が露出するおそれがあります。Base64 は暗号化ではありません。release Secrets へのアクセスを制限してください。

## 完全なローカル Chart の例

`examples/platform/helm/reviewed-app` には、以下の 8 ファイルが含まれています。Helm 3/4 での lint/render 出力、packaging、value overrides、無効な replicaCount の拒否をテストしました。Kubernetes のインストールや container の実行は行っていません。操作前に image digests、namespaces、hardware、policies を確認してください。

### Chart.yaml

```yaml
apiVersion: v2
name: reviewed-app
description: Offline Helm teaching chart
type: application
version: 0.1.0
appVersion: "1.30.4"
```

### values.yaml

```yaml
replicaCount: 1
image:
  repository: nginxinc/nginx-unprivileged
  tag: "1.30.4-alpine"
service:
  port: 8080
resources:
  requests:
    cpu: 100m
    memory: 64Mi
  limits:
    cpu: 500m
    memory: 128Mi
env:
  LOG_LEVEL: info
```

### values.schema.json

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": [
    "replicaCount",
    "image",
    "service"
  ],
  "properties": {
    "replicaCount": {
      "type": "integer",
      "minimum": 0,
      "maximum": 5
    },
    "image": {
      "type": "object",
      "required": [
        "repository",
        "tag"
      ],
      "properties": {
        "repository": {
          "type": "string",
          "minLength": 1
        },
        "tag": {
          "type": "string",
          "minLength": 1
        }
      }
    },
    "service": {
      "type": "object",
      "required": [
        "port"
      ],
      "properties": {
        "port": {
          "type": "integer",
          "minimum": 1,
          "maximum": 65535
        }
      }
    },
    "env": {
      "type": "object",
      "additionalProperties": {
        "type": "string"
      }
    }
  }
}
```

### templates/_helpers.tpl

```text
{{- define "reviewed-app.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- define "reviewed-app.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name | quote }}
app.kubernetes.io/instance: {{ .Release.Name | quote }}
{{- end -}}
```

### templates/deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "reviewed-app.fullname" . }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "reviewed-app.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "reviewed-app.selectorLabels" . | nindent 8 }}
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: web
        image: {{ printf "%s:%s" .Values.image.repository .Values.image.tag | quote }}
        ports:
        - name: http
          containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: [ALL]
        resources:
          {{- toYaml .Values.resources | nindent 10 }}
        env:
          {{- range $key, $value := .Values.env }}
        - name: {{ $key | quote }}
          value: {{ $value | quote }}
          {{- end }}
        readinessProbe:
          httpGet:
            path: /
            port: http
        volumeMounts:
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 64Mi
```

### templates/service.yaml

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "reviewed-app.fullname" . }}
spec:
  type: ClusterIP
  selector:
    {{- include "reviewed-app.selectorLabels" . | nindent 4 }}
  ports:
  - name: http
    port: {{ .Values.service.port }}
    targetPort: http
```

### templates/NOTES.txt

```text
Inspect the rendered resources and prepare namespace/image compatibility before installation.
Release: {{ .Release.Name }}
Namespace: {{ .Release.Namespace }}
```

### .helmignore

```text
*.private
```

すべての helper が定義され、Service は名前付き container port を対象とし、securityContext は manifest 内にあり、resources/env は values から templates へ接続されています。未使用の values entry は影響しません。この基本 chart は database、Ingress、autoscaler を作成しません。

### ローカルチェック

repository root から実行し、`helm version --short` で選択された binary を確認してください。

```bash
helm lint examples/platform/helm/reviewed-app
helm template demo examples/platform/helm/reviewed-app --namespace example
helm template demo examples/platform/helm/reviewed-app   --set replicaCount=3 --set-string env.MAX_CONNECTIONS=100
helm package examples/platform/helm/reviewed-app --destination ./chart-packages
```

lint/template の成功は、admission、CEL、RBAC、image execution、Service connectivity、readiness を検証しません。test hooks は実際に cluster で実行する必要があります。`helm template --api-versions` は offline capabilities を提供しますが、CRDs をインストールしません。

## コマンドと Helm 3/4 の違い

| 目的 | 例と制限事項 |
| --- | --- |
| Repositories | `helm repo add/update/list/remove`, `helm search repo`; OCI registries には別の login/pull フローがあります |
| Install | `helm install demo ./chart -n example --create-namespace`; namespace/release の存在を確認します |
| Install または upgrade | `helm upgrade --install`; hooks、random values、external state は必ずしも冪等ではありません |
| Inspect | `helm list -n example`, status/history/get values/get manifest; 機密性の高い出力を保護します |
| Computed values | `helm get values demo -n example --all` には chart defaults が含まれます |
| Rollback | `helm rollback demo REVISION -n example`; revision は image tag ではありません |
| Uninstall | `helm uninstall demo -n example`; PVC/CRD/hook/external-resource lifecycle を確認します |

古い stable repository はアーカイブであり、現在の default ではありません。外部 chart/image の可用性、licensing、support、security を確認し、chart versions を pin してください。古い Bitnami PostgreSQL12/Redis17 dependencies は、もはやこの例の defaults ではありません。

### Dry Run と Waiting

Helm 4.3 は `--dry-run=client` と `--dry-run=server` を区別します。この環境では、4.3 の client mode は cluster なしで成功しました。3.21.3 の install client dry-run は cluster access を試行して失敗しました。offline rendering には、検証済みの `helm template` パスを使用してください。server mode には cluster access/permissions が必要であり、すべての webhook/external side effects を証明するものではありません。

Helm 4.3 では、省略した --wait はデフォルトで hookOnly となり、--wait を指定すると watcher がデフォルトになります。legacy も利用できます。`--rollback-on-failure` は失敗した upgrades を以前に成功した release へ rollback します。その名前は Helm 3 の --atomic とは異なります。`--force-replace` と `--force-conflicts` はそれぞれ replacement と server-side-apply conflicts を制御します。対象バージョンの help を確認してください。

Rollback は、DB migrations、external API effects、削除済み data を元に戻す transaction ではありません。timeout、Pod readiness、Job completion、application SLOs を区別してください。

## Templates と Values

Chart、Release、Values、Capabilities は context objects です。range/with は dot context を変更するため、root が必要な場合は `$` を使用してください。Capabilities は提供された discovery information を反映するものであり、普遍的な互換性を示すものではありません。

include は named-template の出力を string として返し、nindent に pipe できます。nindent は newline も挿入します。subchart collisions を避けるため helper names に prefix を付け、upgrades をまたぐ不必要な selector changes を避けてください。

default/coalesce は false、zero、empty strings、collections を空として扱います。明示的な false/zero を保持する場合は、存在/type を別途確認してください。default は、parent map が存在しない nested lookup のすべてを保護するわけではありません。

values.yaml は data です。埋め込まれた <code v-pre>{{ .Values... }}</code> が自動的に再評価されることはありません。Chart authors は必要に応じて明示的に tpl を使用できますが、input trust と template privileges を確認する必要があります。以前の subchart storageClass と Blue/Green selector strings は自動的に接続されませんでした。

繰り返し指定する files/overrides では、最も右側の values が優先されます。map merging と list replacement を理解してください。1 つの YAML document 内で keys を重複させるのではなく、dev/staging/prod を別々の files として保存してください。数値のように見える strings には --set-string を使用し、structures にはバージョンでサポートされる --set-json を使用してください。

--reuse-values、--reset-values、--reset-then-reuse-values は、以前の release values と新しい defaults を異なる方法で組み合わせます。暗黙的な動作に依存せず、computed values と rendered diffs を確認してください。

## Dependency Management

Chart.yaml は dependency names、versions、repositories、optional aliases/conditions を宣言します。この fragment は、**準備済みのローカル helper subchart** を前提としています。

```yaml
dependencies:
- name: helper
  alias: cache
  version: 0.1.0
  repository: file://../dependency-child
  condition: cache.enabled
```

alias を使用する場合は、values を cache の下に置き、対応する condition を使用します。condition path が存在しない場合の動作をテストしてください。Global values は subchart がそれらを使用する場合にのみ重要です。import-values には一致する child/parent export structure が必要です。

dependency update は Chart.yaml constraints を解決し、Chart.lock を書き込みます。build は locked versions を使用します。lock がない場合は、update と同様に解決できます。lock だけでは、tamper resistance、pinned runtime images、完全な reproducibility は確立されません。chart digests/signatures、supply paths、image revisions を管理してください。ローカル file-dependency update/build と alias on/off は Helm 3/4 で実施しました。

## Hooks、CRDs、Tests

pre/post install、upgrade、rollback、delete、test hooks は lifecycle stages で実行されます。weight が低いものから先に実行されます。ties については kind/name ordering を確認してください。pre-install migration は、chart の通常の database resource が存在する前に実行される場合があります。

Hook Jobs/Pods には、実際の executables、images、Services/Secrets、permissions、timeouts、repeat-safe behavior が必要です。before-hook-creation/hook-succeeded/hook-failed と Job TTLs による cleanup を計画してください。uninstall はすべての hook resources を削除するとは限りません。post-install readiness は --wait と併せて解釈してください。

crds/ 配下の CRDs は通常の templates と異なります。CRD schemas の自動 upgrade/deletion や rollback を想定しないでください。明示的な migration と custom-resource retention plans を使用してください。CRD を削除すると custom-resource data が削除される場合があります。

helm test は宣言された hooks を実行します。単純な HTTP connectivity では databases、security、load、recovery を検証できません。Blue/Green/canary には実際の Deployments、Services/mesh routes、controllers、metric/rollback conditions が必要です。Values だけでは progressive delivery を実装しません。

## GitOps と Security

Argo CD は一般に Helm を template renderer として使用し、Helm release lifecycle の管理とは異なります。Flux helm-controller は HelmRelease を reconcile します。source/chart revisions、valuesFrom namespace/precedence、hook mapping、pruning、ownership を確認し、競合する controllers を避けてください。

secrets を chart defaults、--set arguments、debug output に配置しないでください。--hide-secret は dry-run 中の Kubernetes Secret output を対象とし、すべての values/logs を一般的に redaction するものではありません。app environment variables を介して提供される既存の Secret references も、file-credential policies に違反します。承認済みの Secret volumes と file reread/rotation paths を使用してください。

ESO v1 などの current APIs とその controllers は別途準備してください。Sealed Secrets/helm-secrets には controller/plugin、key/KMS access、decryption workflow が必要であり、Helm core features ではありません。decrypted values が release records や logs に入るかを確認してください。

ServiceAccounts/Roles だけでは workload permissions は付与されません。必要に応じて RoleBindings と serviceAccountName を接続し、Secret volume のためだけにすべての Secret への get/list/watch を付与しないでください。この demo web chart は Kubernetes API credentials を必要とせず、token automount を無効にしています。

## Troubleshooting の順序

| 症状 | 調査と修正 |
| --- | --- |
| 再利用した release name | namespace/state/history を確認し、意図した upgrade または新しい name を選択します |
| Existing-resource collision | owner annotations/labels/controllers を確認し、レビュー済みの adoption/migration を使用するか rename します |
| Failed release | causes/events/history を確認し、検証済みの revision/configuration で retry します |
| Missing helper | definitions、names、scope、root context を確認します |
| Schema failure | 最終的にマージされた values、types、required fields、ranges を確認します |

Deletion/force flags は万能な修正ではありません。mutation を選択する前に、diffs、immutable fields、data retention、他の controllers を確認してください。

## 検証と参照

全 764 ガイド行、locale ごとの 462 quiz 行、58 の一意な blocks をレビューしました。チェックでは、完全な chart の Helm 3/4 lint/template/package、overrides/negative schemas、local dependencies/aliases を対象としました。4.3 client dry-run は成功しました。3.21.3 install dry-run の cluster-access failure は記録されています。実際の Kubernetes installation、upgrade、rollback、hooks、app HTTP behavior は検証していません。

- [Helm install](https://helm.sh/docs/helm/helm_install/)
- [Helm upgrade](https://helm.sh/docs/helm/helm_upgrade/)
- [Charts と values](https://helm.sh/docs/topics/charts/)
- [Chart hooks](https://helm.sh/docs/topics/charts_hooks/)
- [Dependency build](https://helm.sh/docs/helm/helm_dependency_build/)
- [Helm 4.3.0 release](https://github.com/helm/helm/releases/tag/v4.3.0)

[Helm クイズ](../quizzes/platform-engineering/01-helm-quiz.md)

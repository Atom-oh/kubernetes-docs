# Helm パッケージマネージャー

> **最終更新日**: 2026年9月12日
> **ローカル検証**: Helm 3.21.3 / Helm 4.3.0

Helm は chart をレンダリングし、Kubernetes リソースと release 履歴を管理します。chart version、appVersion、image tag／digest、release revision はそれぞれ別の値です。Helm 4 は apiVersion:v2 の既存 chart を受け付けますが、CLI、apply、wait の動作は使用するバージョンごとに確認してください。

## 基本概念と権限

Helm 3 では Tiller が削除され、クライアントは自身の Kubernetes credentials／RBAC を使います。chart repository／OCI registry との通信は Kubernetes API へのアクセスとは別です。Tiller を削除しても、安全でない chart や広すぎる権限が無害になるわけではありません。

release の保存先は、既定では release の namespace 内にある Secret です。ConfigMap や SQL backend などに変更することもできます。保存される release data には manifest や values が含まれ、機密情報が露出するおそれがあります。Base64 は暗号化ではありません。release Secret へのアクセスを制限してください。

## ローカル chart の全体例

`examples/platform/helm/reviewed-app` には、次の 8 ファイルがあります。Helm 3／4 での lint／render 出力、package 作成、values の上書き、無効な replicaCount の拒否をテストしました。Kubernetes へのインストールやコンテナの実行は行っていません。実際に操作する前に、image digest、namespace、ハードウェア、policy を確認してください。

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
  tag: "1.30.6-alpine"
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

helper はすべて定義済みで、Service は名前付き container port を参照し、manifest には securityContext があります。resources と env は values から template に渡されます。使われない values entry に効果はありません。この基本 chart は database、Ingress、autoscaler を作成しません。

### ローカルチェック

repository root から実行し、`helm version --short` で使う binary を確認してください。

```bash
helm lint examples/platform/helm/reviewed-app
helm template demo examples/platform/helm/reviewed-app --namespace example
helm template demo examples/platform/helm/reviewed-app   --set replicaCount=3 --set-string env.MAX_CONNECTIONS=100
helm package examples/platform/helm/reviewed-app --destination ./chart-packages
```

lint／template の成功だけでは、admission、CEL、RBAC、image の実行、Service 接続、readiness は検証できません。test hook は実際の cluster で実行する必要があります。`helm template --api-versions` はオフラインで利用可能な API 情報を渡しますが、CRD をインストールするものではありません。

## Helm 3／4 のコマンドと違い

| 用途 | 例と制約 |
| --- | --- |
| Repository | `helm repo add/update/list/remove`、`helm search repo`。OCI registry には別の login／pull 手順があります |
| Install | `helm install demo ./chart -n example --create-namespace`。namespace と release の存在を確認してください |
| Install または upgrade | `helm upgrade --install`。hook、ランダムな値、外部状態は必ずしも冪等ではありません |
| 状態確認 | `helm list -n example`、status／history／get values／get manifest。機密情報を含む出力を保護してください |
| 計算後の values | `helm get values demo -n example --all` には chart の既定値も含まれます |
| Rollback | `helm rollback demo REVISION -n example`。revision は image tag ではありません |
| Uninstall | `helm uninstall demo -n example`。PVC／CRD／hook／外部リソースのライフサイクルを確認してください |

古い stable repository はアーカイブであり、現在の既定値ではありません。外部 chart／image の提供状況、ライセンス、サポート、セキュリティを確認し、chart version を固定してください。以前の Bitnami PostgreSQL 12／Redis 17 の依存関係は、この例の現行既定値ではありません。

### Dry run と wait

Helm 4.3 では `--dry-run=client` と `--dry-run=server` が区別されます。この環境では 4.3 の client mode は cluster なしで成功しましたが、3.21.3 の install client dry-run は cluster への接続を試みて失敗しました。オフラインでのレンダリングには、検証済みの `helm template` を使ってください。server mode には cluster へのアクセスと権限が必要で、すべての webhook や外部副作用を検証できるわけではありません。

Helm 4.3 では、`--wait` を省略すると既定で hookOnly となり、指定すると watcher が既定になります。legacy mode も選択できます。`--rollback-on-failure` は失敗した upgrade を以前に成功した release に戻しますが、名前も Helm 3 の `--atomic` とは異なります。`--force-replace` と `--force-conflicts` は、それぞれ置き換えと server-side apply の競合を制御します。正確な挙動は対象バージョンの help で確認してください。

Rollback は DB migration、外部 API の副作用、削除済みデータを元に戻す transaction ではありません。timeout、Pod readiness、Job completion、application SLO を区別してください。

## Template と values

Chart、Release、Values、Capabilities は context object です。range／with は dot context を変えるため、root context が必要な場合は `$` を使ってください。Capabilities が反映するのは渡された discovery 情報であり、あらゆる環境との互換性を示すものではありません。

include は名前付き template の出力を string として返し、nindent に渡せます。nindent は改行も挿入します。subchart 間の衝突を避けるため helper 名に prefix を付け、upgrade をまたぐ不要な selector 変更は避けてください。

default／coalesce は false、zero、空文字列、collection を空として扱います。明示的な false／zero を維持するには、存在と型を別に確認してください。default は、親 map がない場合のすべての nested lookup を保護するわけではありません。

values.yaml は data です。埋め込まれた <code v-pre>{{ .Values... }}</code> が自動的に再評価されることはありません。chart author は必要な箇所で明示的に tpl を使えますが、入力の信頼性と template の権限を確認してください。以前の subchart storageClass と Blue／Green selector の文字列は、自動的には接続されませんでした。

複数の values file や override を指定すると、右側にある値が優先されます。map の merge と list の置換を理解してください。1 つの YAML document で key を重複させず、dev／staging／prod は別ファイルに分けてください。数値に見える文字列には `--set-string` を使い、構造化データには対象バージョンが対応している `--set-json` を使ってください。

`--reuse-values`、`--reset-values`、`--reset-then-reuse-values` は、以前の release values と新しい既定値をそれぞれ異なる方法で組み合わせます。暗黙の動作に頼らず、計算後の values とレンダリング結果の差分を確認してください。

## 依存関係の管理

Chart.yaml では dependency 名、version、repository、任意の alias／condition を宣言します。この設定例は、**準備済みのローカル helper subchart** を前提としています。

```yaml
dependencies:
- name: helper
  alias: cache
  version: 0.1.0
  repository: file://../dependency-child
  condition: cache.enabled
```

alias を使う場合は values を `cache` の下に置き、対応する condition を指定してください。condition path がない場合の動作をテストします。global values は subchart が参照する場合にだけ影響します。import-values を使うには、child と parent の export 構造が対応している必要があります。

`dependency update` は Chart.yaml の制約を解決し、Chart.lock を書き出します。`build` は lock に記録された version を使います。lock がない場合は update と同様に解決できます。lock だけでは改ざん防止、実行時 image の固定、完全な再現性は保証されません。chart digest／signature、供給元の経路、image revision を管理してください。ローカルの file dependency に対する update／build と、alias の有効／無効は Helm 3／4 で実行済みです。

## Hook、CRD、テスト

pre／post install、upgrade、rollback、delete、test の hook は、それぞれのライフサイクル段階で実行されます。weight が小さいものから先に実行されます。同じ weight の場合は kind／name の順序を確認してください。pre-install migration は chart の通常の database resource が作られる前に実行されることがあります。

Hook の Job／Pod には、実際に動く executable、image、Service／Secret、権限、timeout、繰り返し実行に耐える動作が必要です。before-hook-creation／hook-succeeded／hook-failed と Job TTL を使った cleanup を計画してください。uninstall しても、すべての hook resource が削除されるとは限りません。post-install readiness は `--wait` と併せて解釈してください。

`crds/` 内の CRD は通常の template とは扱いが異なります。CRD schema の自動 upgrade／削除や rollback を前提にしないでください。明示的な migration と custom resource の保持計画を用意してください。CRD を削除すると custom resource のデータも失われる場合があります。

`helm test` は宣言された hook を実行します。単純な HTTP 接続テストでは、database、セキュリティ、負荷、復旧は検証できません。Blue／Green／canary には、実際の Deployment、Service／mesh route、controller、metric／rollback 条件が必要です。values だけでは段階的なリリースは実装されません。

## GitOps とセキュリティ

Argo CD は一般に Helm を template renderer として使い、Helm release のライフサイクル管理とは区別されます。Flux helm-controller は HelmRelease を継続的に調整します。source／chart revision、valuesFrom の namespace／優先順位、hook mapping、pruning、ownership を確認し、管理が競合する controller を避けてください。

secret を chart の既定値、`--set` 引数、debug 出力に含めないでください。`--hide-secret` が隠すのは dry-run 中の Kubernetes Secret 出力であり、すべての values／log を一般的にマスクする機能ではありません。既存 Secret を app の環境変数経由で渡す方法も、ファイル credential の方針に違反します。承認済みの Secret volume と、ファイルの再読み込み／rotation 経路を使ってください。

ESO v1 などの現行 API と controller は別途準備してください。Sealed Secrets／helm-secrets には controller／plugin、key／KMS へのアクセス、復号手順が必要で、Helm core の機能ではありません。復号後の values が release record や log に残るか確認してください。

ServiceAccount／Role だけでは workload に権限は付与されません。必要な場合は RoleBinding と serviceAccountName を接続してください。Secret volume を使うだけの目的で、すべての Secret に対する get／list／watch を与えないでください。この demo web chart は Kubernetes API credential を必要とせず、token automount を無効にしています。

## トラブルシューティングの順序

| 症状 | 調査と修正 |
| --- | --- |
| release 名を再利用した | namespace／state／history を確認し、意図した upgrade を行うか、新しい name を選びます |
| 既存リソースとの衝突 | owner annotation／label／controller を確認し、レビュー済みの adoption／migration を行うか、name を変更します |
| release の失敗 | 原因、event、history を確認し、検証済みの revision／configuration で再試行します |
| helper が見つからない | 定義、名前、scope、root context を確認します |
| schema 検証の失敗 | 最終的に merge された values、型、必須 field、範囲を確認します |

削除や force の flag は万能な修正ではありません。変更を選ぶ前に、diff、変更不可の field、データ保持、他の controller を確認してください。

## 検証と参照

ガイド全 764 行、各 locale の quiz 462 行、58 個の一意な block をレビューしました。検証対象は、chart 全体に対する Helm 3／4 の lint／template／package、override／不正 schema、ローカル依存関係／alias です。4.3 の client dry-run は成功しました。3.21.3 の install dry-run が cluster access で失敗したことも記録しています。実際の Kubernetes install、upgrade、rollback、hook、アプリケーションの HTTP 動作は検証していません。

- [Helm の install](https://helm.sh/docs/helm/helm_install/)
- [Helm の upgrade](https://helm.sh/docs/helm/helm_upgrade/)
- [Chart と values](https://helm.sh/docs/topics/charts/)
- [Chart hook](https://helm.sh/docs/topics/charts_hooks/)
- [Dependency build](https://helm.sh/docs/helm/helm_dependency_build/)
- [Helm 4.3.0 のリリース](https://github.com/helm/helm/releases/tag/v4.3.0)

[Helm クイズ](../quizzes/platform-engineering/01-helm-quiz.md)

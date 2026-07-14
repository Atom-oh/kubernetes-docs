# Helm Package Manager クイズ

> **関連ドキュメント**: [Helm Package Manager](../../platform-engineering/01-helm.md)

## 多肢選択問題

### 1. Helm v3 で Tiller が削除された主な理由は何ですか？

- A) パフォーマンスを向上させるため
- B) セキュリティを強化し、アーキテクチャを簡素化するため
- C) chart サイズを削減するため
- D) Kubernetes バージョン互換性のため

<details>
<summary>答えを表示</summary>

**答え: B) セキュリティを強化し、アーキテクチャを簡素化するため**

**解説:**
Helm v2 の Tiller は cluster 内で昇格された権限を持って実行され、セキュリティリスクを生じさせていました。Helm v3 では Tiller が削除され、client が Kubernetes API と直接通信するようになったため、セキュリティが強化され、アーキテクチャが簡素化されました。

</details>

### 2. Helm Chart における values.yaml ファイルの主な目的は何ですか？

- A) chart metadata を保存すること
- B) template で使用されるデフォルト設定値を定義すること
- C) Kubernetes manifest を直接保存すること
- D) chart dependencies を定義すること

<details>
<summary>答えを表示</summary>

**答え: B) template で使用されるデフォルト設定値を定義すること**

**解説:**
values.yaml ファイルは、chart template で使用されるデフォルト設定値を定義します。ユーザーは --set flag または -f flag を使用してこれらの値を上書きし、異なる環境向けに deployment をカスタマイズできます。

</details>

### 3. `helm upgrade --install` コマンドの挙動は何ですか？

- A) 常に新しい release をインストールする
- B) 常に既存の release を upgrade する
- C) release が存在しない場合はインストールし、存在する場合は upgrade する
- D) release を削除して再インストールする

<details>
<summary>答えを表示</summary>

**答え: C) release が存在しない場合はインストールし、存在する場合は upgrade する**

**解説:**
`helm upgrade --install` は冪等な挙動を提供します。指定された release が存在しない場合は新しい release をインストールし、存在する場合は upgrade します。これは CI/CD pipeline で特に有用です。

</details>

### 4. Helm template 内の <code v-pre>{{ .Release.Name }}</code> は何を参照しますか？

- A) Chart 名
- B) Kubernetes cluster 名
- C) インストールされた release の名前
- D) Namespace 名

<details>
<summary>答えを表示</summary>

**答え: C) インストールされた release の名前**

**解説:**
`.Release.Name` は、`helm install` コマンドで指定された release 名を参照する Helm built-in object です。たとえば `helm install my-app chart/` では、`.Release.Name` は "my-app" になります。

</details>

### 5. Chart.yaml の `dependencies` field における `condition` attribute の目的は何ですか？

- A) dependency chart のバージョンを指定すること
- B) dependency chart を有効化/無効化する values path を指定すること
- C) dependency chart repository URL を指定すること
- D) dependency chart の優先度を指定すること

<details>
<summary>答えを表示</summary>

**答え: B) dependency chart を有効化/無効化する values path を指定すること**

**解説:**
`condition` attribute は、dependency chart を有効にするかどうかを決定する values.yaml 内の path を指定します。たとえば `condition: postgresql.enabled` は、`postgresql.enabled` の値が true の場合にのみ PostgreSQL subchart が含まれることを意味します。

</details>

### 6. `pre-upgrade` Helm Hook はいつ実行されますか？

- A) release deletion の前
- B) upgrade request の後、resource が更新される前
- C) すべての resource が作成された後
- D) rollback completion の後

<details>
<summary>答えを表示</summary>

**答え: B) upgrade request の後、resource が更新される前**

**解説:**
`pre-upgrade` Hook は、upgrade request を受信した後、実際の resource 更新が開始される前に実行されます。database migration や backup operation によく使用されます。

</details>

### 7. `helm template` コマンドの主な用途は何ですか？

- A) chart を cluster にデプロイすること
- B) 検証のために chart template をローカルでレンダリングすること
- C) chart dependencies を更新すること
- D) release を rollback すること

<details>
<summary>答えを表示</summary>

**答え: B) 検証のために chart template をローカルでレンダリングすること**

**解説:**
`helm template` は chart template をローカルでレンダリングし、生成される Kubernetes manifest を事前に確認できるようにします。これにより、cluster に接続せずに template を検証できます。

</details>

### 8. Helm における `_helpers.tpl` ファイルの目的は何ですか？

- A) chart metadata を保存すること
- B) 再利用可能な template helper function を定義すること
- C) デフォルト値を保存すること
- D) post-installation message を表示すること

<details>
<summary>答えを表示</summary>

**答え: B) 再利用可能な template helper function を定義すること**

**解説:**
`_helpers.tpl` ファイルは、複数の template で共通して使用される helper function (named template) を定義します。chart 名、label、selector などの反復的な logic をカプセル化します。

</details>

### 9. `helm get values my-release --all` コマンドは何を出力しますか？

- A) ユーザーが指定した値のみ
- B) デフォルトを含むすべての値
- C) release manifest
- D) release history

<details>
<summary>答えを表示</summary>

**答え: B) デフォルトを含むすべての値**

**解説:**
`--all` flag を使用すると、ユーザーが上書きした値と values.yaml にある chart のデフォルト値の両方を含む、すべての計算済み値が出力されます。

</details>

### 10. Helm chart で `toYaml` と `nindent` function が一緒によく使用される理由は何ですか？

- A) YAML を JSON に変換するため
- B) 複雑な値を適切な indentation で YAML に挿入するため
- C) 値を Base64 encode するため
- D) 文字列を引用符で囲むため

<details>
<summary>答えを表示</summary>

**答え: B) 複雑な値を適切な indentation で YAML に挿入するため**

**解説:**
`toYaml` は Go object を YAML 文字列に変換し、`nindent` は指定された数の space による indentation を適用します。この組み合わせは、resources や annotations のような複雑な構造を template に正しく挿入するために不可欠です。

</details>

## 短答問題

### 1. Helm v3 で release 情報を保存するために使用される Kubernetes resource type は何ですか？

<details>
<summary>答えを表示</summary>

**答え: Secret**

**解説:**
Helm v3 は、release 情報を release がデプロイされている namespace 内の Secrets として保存します。Secret 名の形式は `sh.helm.release.v1.<release-name>.v<version>` です。

</details>

### 2. `helm dependency update` コマンドによって生成される lock file の名前は何ですか？

<details>
<summary>答えを表示</summary>

**答え: Chart.lock**

**解説:**
`helm dependency update` は Chart.yaml 内の dependencies を解析し、正確なバージョンを含む Chart.lock ファイルを生成します。このファイルにより、再現可能な build が保証されます。

</details>

### 3. Helm template で値が空の場合にデフォルト値を提供する function は何ですか？

<details>
<summary>答えを表示</summary>

**答え: default**

**解説:**
`default` function は、値が空または未定義の場合にデフォルト値を提供します。使用例: <code v-pre>{{ .Values.image.tag | default .Chart.AppVersion }}</code>

</details>

### 4. Helm Hooks の実行順序を制御する annotation は何ですか？

<details>
<summary>答えを表示</summary>

**答え: helm.sh/hook-weight**

**解説:**
`helm.sh/hook-weight` annotation は、同じ Hook type 内での実行順序を決定します。小さい数値ほど先に実行され、負の値も許可されています。

</details>

### 5. Helm chart の NOTES.txt ファイルはいつユーザーに表示されますか？

<details>
<summary>答えを表示</summary>

**答え: helm install または helm upgrade が正常に完了した後**

**解説:**
NOTES.txt は、インストールまたは upgrade が成功した後にユーザーに表示されます。通常、application access 手順と initial setup guidance が含まれます。

</details>

## ハンズオン問題

### 1. 次の要件を満たす Helm コマンドを書いてください:

- bitnami/nginx chart を "web-server" release としてインストールする
- "frontend" namespace にデプロイする (存在しない場合は作成する)
- replicaCount を 3 に設定する

<details>
<summary>答えを表示</summary>

```bash
helm install web-server bitnami/nginx \
  -n frontend --create-namespace \
  --set replicaCount=3
```

**解説:**
- `helm install web-server bitnami/nginx`: nginx chart を "web-server" release としてインストールする
- `-n frontend`: frontend namespace を指定する
- `--create-namespace`: namespace が存在しない場合に作成する
- `--set`: 値を inline で上書きする

</details>

### 2. 次の Helm template snippet の出力を予測してください:

```yaml
# values.yaml
env:
  LOG_LEVEL: debug
  MAX_CONNECTIONS: "100"

# template
env:
{{- range $key, $value := .Values.env }}
  - name: {{ $key }}
    value: {{ $value | quote }}
{{- end }}
```

<details>
<summary>答えを表示</summary>

```yaml
env:
  - name: LOG_LEVEL
    value: "debug"
  - name: MAX_CONNECTIONS
    value: "100"
```

**解説:**
- `range` function は `.Values.env` map を反復処理します
- `$key` は map key、`$value` は map value です
- `quote` function は値を引用符で囲みます
- map はアルファベット順にソートされます

</details>

### 3. 次の要件を満たす `_helpers.tpl` template を書いてください:

- Name: mychart.labels
- app.kubernetes.io/name: chart name
- app.kubernetes.io/instance: release name
- app.kubernetes.io/version: app version

<details>
<summary>答えを表示</summary>

```yaml
{{- define "mychart.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
```

**解説:**
- `define` は再利用可能な named template を作成します
- `.Chart.Name` は chart 名を参照します
- `.Release.Name` は release 名を参照します
- `.Chart.AppVersion` は app version を参照します (quote により string type が保証されます)

</details>

## 高度な問題

### 1. Helm chart を使用して Blue-Green deployment と Canary deployment を実装する方法を説明してください。

<details>
<summary>答えを表示</summary>

**Blue-Green Deployment:**
```yaml
# values.yaml
deployment:
  activeColor: blue

blue:
  enabled: true
  image:
    tag: "v1.0.0"

green:
  enabled: true
  image:
    tag: "v2.0.0"

service:
  selector:
    color: "{{ .Values.deployment.activeColor }}"
```

**実装戦略:**
1. Blue と Green 用に 2 つの Deployment template を作成する
2. activeColor value を使用して Service selector を切り替える
3. deployment 中に green.image.tag を新しいバージョンに設定する
4. 検証後、deployment.activeColor を green に変更する
5. 問題が発生した場合はすぐに blue に rollback する

**Canary Deployment (with Istio):**
```yaml
# VirtualService for traffic distribution
http:
  - route:
      - destination:
          host: myapp
          subset: stable
        weight: 90
      - destination:
          host: myapp
          subset: canary
        weight: 10
```

**実装戦略:**
1. Stable と Canary 用に 2 つの Deployments を作成する
2. Istio VirtualService を使用して traffic ratio を制御する
3. Canary ratio を段階的に増やす (10% -> 25% -> 50% -> 100%)
4. metric monitoring に基づく自動 rollback を実装する

</details>

### 2. Helm chart のセキュリティのベストプラクティスを説明し、secret management strategy を設計してください。

<details>
<summary>答えを表示</summary>

**セキュリティのベストプラクティス:**

1. **Value Validation (values.schema.json)**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["image"],
  "properties": {
    "image": {
      "type": "object",
      "required": ["repository"],
      "properties": {
        "repository": {
          "type": "string",
          "pattern": "^[a-z0-9.-/]+$"
        }
      }
    }
  }
}
```

2. **RBAC Least Privilege Principle**
```yaml
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list"]  # Grant only necessary permissions
```

3. **Pod Security Standards の適用**
```yaml
securityContext:
  runAsNonRoot: true
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]
```

**Secret Management Strategy:**

1. **External Secrets Manager 連携 (AWS Secrets Manager)**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: {{ include "mychart.fullname" . }}
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: {{ include "mychart.fullname" . }}-secrets
  data:
    - secretKey: database-password
      remoteRef:
        key: myapp/database
        property: password
```

2. **Sealed Secrets の使用**
```bash
# Encrypt secret
kubeseal --format=yaml < secret.yaml > sealed-secret.yaml
```

3. **Helm Secrets Plugin**
```bash
# Use encrypted values file
helm secrets install myapp ./mychart -f secrets.yaml
```

</details>

# Helm パッケージマネージャークイズ

> **関連ガイド**: [Helm](../../platform-engineering/01-helm.md)

この20問のトピックは、Helm 3.21.3 / 4.3.0 の復習に沿っています。

## 選択問題

### 1. Tiller を削除したことで何が変わりましたか？

- A) Chart のサイズだけが変わる。
- B) クライアントは自身の Kubernetes 認証情報と RBAC を使用する。
- C) すべての Chart が安全になる。
- D) Kubernetes API が不要になる。

<details>
<summary>回答を表示</summary>

**回答: B**

Helm 3 は Tiller を削除し、権限の経路を簡素化しました。安全でない manifest と広範なクライアント権限は、引き続きレビューが必要です。

</details>

### 2. values.yaml は何のためにありますか？

- A) Chart メタデータ
- B) template によって使用されるデフォルト設定データ
- C) Release 履歴
- D) 自動的に実行される template

<details>
<summary>回答を表示</summary>

**回答: B**

template によって使用される values だけが効果を持ちます。ファイルと --set バリアントでそれらを上書きできます。埋め込まれた template 文字列は自動的には評価されません。

</details>

### 3. helm upgrade --install は何をしますか？

- A) 常に新しい Release を作成する。
- B) 常に削除して再作成する。
- C) 存在しない Release を install するか、既存の Release を upgrade する。
- D) 外部操作の冪等性を保証する。

<details>
<summary>回答を表示</summary>

**回答: C**

これは installation または upgrade を選択します。Hook、ランダム値、外部データベースの変更は冪等であるとは限りません。

</details>

### 4. Release.Name とは何ですか？

- A) Chart 名
- B) Cluster 名
- C) 選択した Release 名
- D) Image tag

<details>
<summary>回答を表示</summary>

**回答: C**

`helm install demo ./chart` では、名前は demo です。これは Chart 名、appVersion、および Release revision とは異なります。

</details>

### 5. dependency condition は何を指定しますか？

- A) Image tag
- B) dependency を有効にするか制御する values path
- C) Registry password
- D) Pod priority

<details>
<summary>回答を表示</summary>

**回答: B**

alias cache では、cache.enabled のような実際の Boolean path を使用します。path がない場合の動作をテストし、subchart に渡される values とは区別してください。

</details>

### 6. pre-upgrade Hook はいつ実行されますか？

- A) 削除後
- B) rendering の後、通常の resource が upgrade される前
- C) 常に新しい Pod が Ready になった後
- D) rollback 後のみ

<details>
<summary>回答を表示</summary>

**回答: B**

データベース migration では、データベースの可用性、retry、failure、および以前の app との互換性を考慮する必要があります。rollback はデータベースの変更を自動的に元に戻しません。

</details>

### 7. 通常の helm template の目的は何ですか？

- A) Cluster に install する。
- B) manifest をローカルで render する。
- C) 実際の webhook を検証する。
- D) 自動的に roll back する。

<details>
<summary>回答を表示</summary>

**回答: B**

デフォルトのローカル rendering は、admission、RBAC、Image 実行、または接続性を証明しません。server に接続するオプションとは区別してください。

</details>

### 8. _helpers.tpl は何のためにありますか？

- A) metadata を保存する。
- B) 再利用可能な名前付き template を定義する。
- C) デフォルト values を保存する。
- D) Release 履歴を保存する。

<details>
<summary>回答を表示</summary>

**回答: B**

名前付き template には define を使用し、それらを使用するには include を使用します。衝突を避けるために名前に prefix を付け、意図した context を渡してください。

</details>

### 9. helm get values demo --all は何を出力しますか？

- A) ユーザーによる override のみ
- B) Chart defaults を含む計算済み values
- C) manifest のみ
- D) 履歴のみ

<details>
<summary>回答を表示</summary>

**回答: B**

正しい namespace と Release を選択してください。values には機密情報が含まれる可能性があるため、出力を保護してください。

</details>

### 10. toYaml と nindent を組み合わせるのはなぜですか？

- A) 自動 encryption
- B) 構造化された values を YAML に serialize し、改行と indentation を追加する。
- C) JSON のみを生成する。
- D) 常に数値を文字列に変換する。

<details>
<summary>回答を表示</summary>

**回答: B**

indent とは異なり、nindent は改行も先頭に追加します。挿入箇所で必要な indentation に合わせてください。

</details>

## 短答問題

### 1. デフォルトの Release storage resource は何ですか？

<details>
<summary>回答を表示</summary>

Release namespace 内の Secret で、名前は `sh.helm.release.v1.<release>.v<revision>` です。ConfigMap や SQL などの他の backend も設定できます。Base64 は encryption ではありません。

</details>

### 2. dependency update はどの lock file を作成し、その制限は何ですか？

<details>
<summary>回答を表示</summary>

Chart.lock。dependency build は lock された version を使用しますが、lock 単体では artifact integrity、固定された Image、または完全な再現性を保証しません。

</details>

### 3. default を使用する際、どの空の values が重要ですか？

<details>
<summary>回答を表示</summary>

false、zero、空文字列、および collection は空として扱われます。明示的な false/zero を保持する必要がある場合は、存在と type を確認してください。default はすべての nested lookup を保護するわけではありません。

</details>

### 4. Hook の順序を制御する annotation はどれですか？

<details>
<summary>回答を表示</summary>

`helm.sh/hook-weight`。phase 内では、negative weight を含め、より小さい weight が先に実行されます。kind/name による同順位時の順序、Job completion、および timeout も考慮してください。

</details>

### 5. NOTES.txt はいつ、なぜ使用されますか？

<details>
<summary>回答を表示</summary>

成功した install/upgrade の後に表示され、`helm get notes` から利用できる手順を template 化します。手順を正確に保ち、Secret を避けてください。Notes は application readiness を証明しません。

</details>

## ハンズオン

### 1. 例を frontend に web-server として 3 replicas で install してください。

<details>
<summary>回答を表示</summary>

```bash
helm install web-server examples/platform/helm/reviewed-app \
  --namespace frontend --create-namespace \
  --set replicaCount=3
```

承認済みの Cluster context と権限で、repository root から実行します。この監査では lint/template/package を実行しており、installation は実行していません。

</details>

### 2. LOG_LEVEL=debug と MAX_CONNECTIONS="100" は env としてどのように render されるべきですか？

<details>
<summary>回答を表示</summary>

```yaml
env:
  - name: LOG_LEVEL
    value: "debug"
  - name: MAX_CONNECTIONS
    value: "100"
```

map を range で反復し、両方が文字列のままになるよう各 value を quote します。Go template は、基本的な順序付き key を持つ map を key 順に走査します。これは list の順序とは異なります。

</details>

### 3. Chart、Release、および appVersion label のための helper を書いてください。

<details>
<summary>回答を表示</summary>

```text
{{- define "mychart.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name | quote }}
app.kubernetes.io/instance: {{ .Release.Name | quote }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
```

意図した root context を渡し、call site で indent してください。appVersion は metadata であり、Image tag を自動的に選択しません。

</details>

## 応用

### 1. Helm による Blue/Green と canary delivery には何が必要ですか？

<details>
<summary>回答を表示</summary>

Blue/Green には、label を持つ 2 つの Deployment と、検証後に active color を選択する実際の Service template が必要です。values.yaml 内の template 文字列は自動的には評価されません。Canary には、実際の route/subset または rollout controller、weight、observation metrics、および abort condition が必要です。values だけでは自動分析や rollback は作成されません。データベース互換性と in-flight request を考慮してください。

</details>

### 2. Chart security と Secret management を設計してください。

<details>
<summary>回答を表示</summary>

サポートされている values.schema.json で必須 values と type を検証し、レビュー済みの Chart/Image revision を固定します。必要な ServiceAccount と RoleBinding を最小限の API 権限で接続します。Secret volume があるからといって、app にすべての Secret へのアクセスを付与する理由にはなりません。Secret value を default、CLI argument、および debug log に含めないでください。承認済みの file mount、rotation、および再読み込みを計画してください。ESO v1、Sealed Secrets、および helm-secrets には、それらの controller/plugin と provider/key 権限が必要です。復号された values が Release record に入るかを確認してください。non-root UID、drop した capability、read-only root、および必要な writable volume を組み合わせ、実際の Image compatibility を検証してください。

</details>

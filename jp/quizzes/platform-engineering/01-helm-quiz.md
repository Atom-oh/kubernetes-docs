# Helm パッケージマネージャーのクイズ

> **関連ガイド**: [Helm](../../platform-engineering/01-helm.md)

この20問は、Helm 3.21.3 / 4.3.0 のレビューに基づいています。

## 選択式問題

### 1. Tiller を削除したことで、何が変わりましたか？

- A) Chart のサイズだけが変わる。
- B) クライアントが自身の Kubernetes 認証情報と RBAC を使う。
- C) すべての Chart が安全になる。
- D) Kubernetes API が不要になる。

<details>
<summary>回答を表示</summary>

**回答: B**

Helm 3 では Tiller が削除され、権限を適用する経路が簡素化されました。ただし、安全でないマニフェストや広すぎるクライアント権限は、引き続き確認が必要です。

</details>

### 2. values.yaml は何のために使いますか？

- A) Chart のメタデータ
- B) テンプレートが参照するデフォルト設定値
- C) Release の履歴
- D) 自動実行されるテンプレート

<details>
<summary>回答を表示</summary>

**回答: B**

テンプレートから参照される値だけが反映されます。値はファイルや `--set` の指定で上書きできます。値に埋め込んだテンプレート文字列は、自動では評価されません。

</details>

### 3. helm upgrade --install は何をしますか？

- A) 常に新しい Release を作成する。
- B) 常に削除して作り直す。
- C) Release がなければインストールし、あればアップグレードする。
- D) 外部操作の冪等性を保証する。

<details>
<summary>回答を表示</summary>

**回答: C**

Release をインストールするか、既存の Release をアップグレードするかを選びます。Hook、ランダム値、外部データベースへの変更は、冪等とは限りません。

</details>

### 4. Release.Name が表すものは何ですか？

- A) Chart 名
- B) Cluster 名
- C) 選択した Release 名
- D) Image tag

<details>
<summary>回答を表示</summary>

**回答: C**

`helm install demo ./chart` の場合、Release 名は `demo` です。Chart 名、appVersion、Release revision とは異なります。

</details>

### 5. dependency の condition は何を指定しますか？

- A) Image tag
- B) dependency を有効にするかを制御する values path
- C) Registry password
- D) Pod priority

<details>
<summary>回答を表示</summary>

**回答: B**

`cache` という alias を付けた dependency では、`cache.enabled` のような実在する Boolean path を使います。path がない場合の動作をテストし、subchart に渡す values とは区別してください。

</details>

### 6. pre-upgrade Hook はいつ実行されますか？

- A) 削除後
- B) レンダリング後、通常のリソースをアップグレードする前
- C) 常に新しい Pod が Ready になった後
- D) rollback の後だけ

<details>
<summary>回答を表示</summary>

**回答: B**

データベースのマイグレーションでは、データベースの可用性、再試行、失敗時の動作、以前のアプリとの互換性を考慮する必要があります。rollback しても、データベースの変更は自動で元に戻りません。

</details>

### 7. 通常の helm template の目的は何ですか？

- A) Cluster にインストールする。
- B) マニフェストをローカルでレンダリングする。
- C) 実際の webhook を検証する。
- D) 自動で rollback する。

<details>
<summary>回答を表示</summary>

**回答: B**

デフォルトのローカルレンダリングだけでは、admission、RBAC、イメージの実行、接続性は確認できません。サーバーに接続するオプションとは区別してください。

</details>

### 8. _helpers.tpl は何のために使いますか？

- A) メタデータを保存する。
- B) 再利用可能な名前付きテンプレートを定義する。
- C) デフォルト値を保存する。
- D) Release の履歴を保存する。

<details>
<summary>回答を表示</summary>

**回答: B**

名前付きテンプレートの定義には `define` を、呼び出しには `include` を使います。名前には prefix を付けて衝突を避け、意図した context を渡してください。

</details>

### 9. helm get values demo --all は何を出力しますか？

- A) ユーザーが上書きした値だけ
- B) Chart のデフォルト値を含む計算済み values
- C) マニフェストだけ
- D) 履歴だけ

<details>
<summary>回答を表示</summary>

**回答: B**

正しい namespace と Release を指定してください。values に機密情報が含まれる場合があるため、出力を適切に保護してください。

</details>

### 10. toYaml と nindent を組み合わせるのはなぜですか？

- A) 自動で暗号化するため
- B) 構造化データを YAML に変換し、改行とインデントを加えるため
- C) JSON だけを生成するため
- D) 数値を必ず文字列に変換するため

<details>
<summary>回答を表示</summary>

**回答: B**

`indent` と違い、`nindent` は先頭に改行も追加します。挿入する位置で必要なインデントに合わせてください。

</details>

## 短答問題

### 1. Release 情報を保存するデフォルトのリソースは何ですか？

<details>
<summary>回答を表示</summary>

Release の namespace 内にある Secret で、名前は `sh.helm.release.v1.<release>.v<revision>` です。ConfigMap や SQL など、別のバックエンドも設定できます。Base64 は暗号化ではありません。

</details>

### 2. dependency update が作成する lock file は何ですか？また、その限界は何ですか？

<details>
<summary>回答を表示</summary>

`Chart.lock` です。dependency build はロックされたバージョンを使いますが、この lock file だけでは、成果物の完全性、固定されたイメージ、完全な再現性は保証されません。

</details>

### 3. default を使うとき、どの値が「空」として扱われますか？

<details>
<summary>回答を表示</summary>

`false`、ゼロ、空文字列、空のコレクションです。明示的な `false` やゼロを保持する必要がある場合は、値の有無と型を確認してください。`default` は、すべてのネストした lookup を保護するわけではありません。

</details>

### 4. Hook の実行順を制御する annotation はどれですか？

<details>
<summary>回答を表示</summary>

`helm.sh/hook-weight` です。同じ phase では、負の値も含め、weight が小さいものから先に実行されます。同じ weight の場合の kind/name 順、Job の完了、timeout も考慮してください。

</details>

### 5. NOTES.txt はいつ、何のために使いますか？

<details>
<summary>回答を表示</summary>

インストールやアップグレードが成功した後に表示する手順をテンプレート化します。`helm get notes` でも確認できます。手順を正確に保ち、Secret を含めないでください。Notes はアプリケーションの readiness を証明しません。

</details>

## ハンズオン

### 1. 例を web-server という名前で frontend にインストールし、レプリカを 3 つにしてください。

<details>
<summary>回答を表示</summary>

```bash
helm install web-server examples/platform/helm/reviewed-app \
  --namespace frontend --create-namespace \
  --set replicaCount=3
```

承認された Cluster context と権限を使い、repository のルートから実行してください。この監査では lint、template、package を確認しましたが、インストールは実行していません。

</details>

### 2. LOG_LEVEL=debug と MAX_CONNECTIONS="100" は、env としてどうレンダリングすべきですか？

<details>
<summary>回答を表示</summary>

```yaml
env:
  - name: LOG_LEVEL
    value: "debug"
  - name: MAX_CONNECTIONS
    value: "100"
```

map を `range` で走査し、どちらも文字列として保持されるよう各値を quote します。Go template では、基本型のキーを持つ map はキー順に反復処理されます。これは list の順序とは異なります。

</details>

### 3. Chart、Release、appVersion の label を定義する helper を書いてください。

<details>
<summary>回答を表示</summary>

```text
{{- define "mychart.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name | quote }}
app.kubernetes.io/instance: {{ .Release.Name | quote }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
```

意図した root context を渡し、呼び出し箇所でインデントしてください。appVersion はメタデータであり、Image tag を自動で選択するものではありません。

</details>

## 応用問題

### 1. Helm で Blue/Green と canary 配信を行うには、何が必要ですか？

<details>
<summary>回答を表示</summary>

Blue/Green には、label を設定した 2 つの Deployment と、検証後に有効な色を選択する実際の Service template が必要です。values.yaml 内のテンプレート文字列は自動では評価されません。Canary には、実際の route/subset または rollout controller、weight、観測メトリクス、abort 条件が必要です。values だけでは自動分析も rollback も構成されません。データベースとの互換性と処理中のリクエストも考慮してください。

</details>

### 2. Chart のセキュリティと Secret 管理を設計してください。

<details>
<summary>回答を表示</summary>

対応する `values.schema.json` で必須 values と型を検証し、レビュー済みの Chart と Image の revision を固定します。必要な ServiceAccount と RoleBinding を、最小限の API 権限で構成してください。Secret volume を使うからといって、アプリにすべての Secret へのアクセスを許可してよいわけではありません。Secret の値をデフォルト値、CLI 引数、debug log に含めないでください。承認済みのファイルマウント、ローテーション、再読み込みの手順を計画します。ESO v1、Sealed Secrets、helm-secrets には、それぞれの controller/plugin と、provider/key への権限が必要です。復号した値が Release の記録に残るかも確認してください。non-root UID、capability の削除、root filesystem の読み取り専用化、必要な書き込み可能ボリュームを組み合わせ、実際の Image との互換性を検証してください。

</details>

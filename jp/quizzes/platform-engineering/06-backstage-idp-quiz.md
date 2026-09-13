# Backstage IDP クイズ

[Backstage](../../platform-engineering/06-backstage-idp.md)

元の 8 つのトピックは Backstage 1.54.7 のレビュー内容に更新されています。

## 1. microservice を表す catalog kind はどれですか？

<details>
<summary>回答を表示</summary>

Component であり、spec.type には service などを指定します。catalog の Resource は infrastructure を記述するもので、AWS resource を provision する controller ではありません。

</details>

## 2. Software Template は実際には何を作成しますか？

<details>
<summary>回答を表示</summary>

登録された action と提供された skeleton によって実装されたファイルと外部操作のみです。ガイドの小さな例では 3 つの catalog/TechDocs ファイルが作成されるだけで、application runtime や database は作成されません。golden path は認可や必須ポリシーを置き換えるものではありません。

</details>

## 3. Kubernetes workload はどのように catalog entity と対応付けられますか？

<details>
<summary>回答を表示</summary>

backstage.io/kubernetes-id またはサポートされている label-selector annotation を、実際の workload の label と一致させます。Namespace/cluster の選択、認証情報、RBAC も必要です。メタデータの一致はユーザーごとの認可ではありません。

</details>

## 4. EKS 上で PostgreSQL と secret はどのように準備すべきですか？

<details>
<summary>回答を表示</summary>

RDS のような外部 PostgreSQL を選択する場合は、同梱の database を無効化し、TLS、ネットワーク、スキーマ、マイグレーション、バックアップを設定します。承認された secret ファイルのマウントを使用し、$file のパスを一致させます。マネージド database だけでは HA/リカバリの検証は完了しません。

</details>

## 5. TechDocs はどのようにビルドされ配信されますか？

<details>
<summary>回答を表示</summary>

MkDocs と techdocs-core を使用します。外部 builder を使う場合は、CI が S3 などのストレージに publish し、Backstage backend がそれを読み取って UI に表示します。entity のキーとルートパスを揃え、publisher と reader の権限を分離します。バケットへのパブリックアクセスは不要です。

</details>

## 6. 段階的な導入の過程で何を確立すべきですか？

<details>
<summary>回答を表示</summary>

小さく正確な catalog と信頼できる ownership/ソースから始め、その後 template と TechDocs を拡張します。認証、認可、信頼境界は最初から確立しておきます。

</details>

## 7. GitHub への publish と ArgoCD の action をつなぐものは何ですか？

<details>
<summary>回答を表示</summary>

action モジュールを登録し、認証情報、権限、実際の入出力スキーマを設定します。Roadie 1.8.1 の argocd:create-resources はデプロイ先の namespace を受け取り、revision の入力はありません。マージされていない PR を作成した直後に main branch の catalog ファイルを登録してはいけません。

</details>

## 8. catalog の削除を ownership によって制限するにはどうすればよいですか？

<details>
<summary>回答を表示</summary>

実際の PermissionPolicy モジュールを登録し、catalog の削除に対して IS_ENTITY_OWNER 条件を返して、catalog backend にそれを評価させます。この例では明示的な許可がない action は拒否されます。catalog の ownership、GitHub への書き込み、ArgoCD のデプロイ権限はそれぞれ別個のものです。Group/User のソースも保護しましょう。

</details>

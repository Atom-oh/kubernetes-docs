# Platform Engineering の概要クイズ

[関連ガイド](../../platform-engineering/00-platform-engineering-overview.md)

## 1. Platform Engineering の中核となる目標は何ですか？

<details>
<summary>回答と解説</summary>

開発者のニーズを理解し、承認済みのセルフサービス API、CLI、ポータル、テンプレート、運用サポートを内部プロダクトとして提供することです。これは運用チームをなくすことや、すべてのアプリケーションの責任を負うことを意味するものではありません。
</details>

## 2. Start、Advance、Excel とツールの対応関係はどのように解釈すべきですか？

<details>
<summary>回答と解説</summary>

これらは AWS の Platform Engineering ガイダンスにおける改善タスクを整理したものです。Advance では IaC/セルフサービス自動化を扱います。このガイドの Kubernetes の対応付けは学習用の例であり、公式認定のスコアや普遍的な順序ではありません。
</details>

## 3. Platform Engineering、DevOps、SRE はどのような関係にありますか？

<details>
<summary>回答と解説</summary>

これらは補完関係にあります。プラットフォームは開発者体験と再利用可能なプロダクトを重視し、DevOps はコラボレーションとデリバリーを、SRE は信頼性と運用エンジニアリングを重視します。チーム構成と階層は普遍的なものではありません。
</details>

## 4. IDP のレイヤーと Backstage ポータルの対象範囲は何ですか？

<details>
<summary>回答と解説</summary>

インターフェース、オーケストレーション、リソース、インフラストラクチャがリファレンスモデルを構成します。Backstage スタイルのポータルはインターフェースの一部であり、プロビジョニング、ポリシー、ランタイム、ドキュメント、サポートの代替ではありません。
</details>

## 5. Golden Path から逸脱すると、必須のセキュリティポリシーを回避できますか？

<details>
<summary>回答と解説</summary>

いいえ。これはサポート対象の推奨パスですが、例外についても組織の承認と必須のセキュリティ/データポリシーに従います。すべてのケースで最適であることが保証されているわけではありません。
</details>

## 6. 1 つの WebApplication により、kro が常に Deployment、RDS、IAM を作成しますか？

<details>
<summary>回答と解説</summary>

いいえ。WebApplication は RGD/CRD を必要とするカスタム API の例です。kro は宣言された Kubernetes リソースを管理し、認可された ACK サービスコントローラーが AWS API を呼び出します。リソースの組み合わせ、準備完了状態、削除ポリシーは定義によって異なります。
</details>

## 7. 現在の DORA メトリクスとは何ですか？また、どのように使用すべきですか？

<details>
<summary>回答と解説</summary>

変更のリードタイム、デプロイ頻度、失敗したデプロイからの復旧時間、変更失敗率、デプロイのやり直し率です。一般的な MTTR や個人ランキングの代わりとしてではなく、サービス/チームのデリバリーと安定性を改善するために使用します。測定は Excel の前から開始できます。
</details>

## 8. ガードレールはセキュリティとコンプライアンスを自動的に保証しますか？

<details>
<summary>回答と解説</summary>

いいえ。監査と復旧を伴い、ポリシー、バイパス/例外処理、権限、変更を適用および検証します。ガードレールは、アプリケーションのデータ処理に関する責任や法的要件の評価に代わるものではありません。
</details>

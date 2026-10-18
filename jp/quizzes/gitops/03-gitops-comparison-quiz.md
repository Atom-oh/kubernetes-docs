# GitOps ツール比較クイズ

このクイズでは、GitOps ツールと、それらをどのように選択するかについての理解を確認します。

1. 標準で組み込みの Web UI を提供する GitOps ツールはどれですか？
   - A) FluxCD
   - B) ArgoCD
   - C) 両方
   - D) どちらでもない

<details>
<summary>回答を表示</summary>

**回答: B) ArgoCD**

**解説:**
ArgoCD には、アプリケーションを管理するための機能豊富な組み込み Web UI が含まれています。FluxCD は CLI ファーストであり、組み込み UI は含まれていませんが、Weave GitOps などのサードパーティ UI を追加できます。

</details>

2. OCI ベースのデプロイソースの現在のサポートについて、正しい説明はどれですか？
   - A) ArgoCD だけが OCI をサポートする
   - B) FluxCD だけが OCI をサポートする
   - C) 両方ともサポートするが、ソース、レイヤー、検証の設定が異なる
   - D) どちらも OCI をサポートしない

<details>
<summary>回答を表示</summary>

**回答: C) 両方ともサポートするが、ソース、レイヤー、検証の設定が異なる**

**解説:**
FluxCD は `OCIRepository` source type を通じて OCI artifact を第一級の機能としてサポートしています。現在の Argo CD も、一般的な OCI Application source をサポートしています。バージョン、media type、認証、検証要件を比較してください。

</details>

3. 組み込みの image automation（新しい image に対する Git の自動更新）を提供するツールはどれですか？
   - A) ArgoCD (ネイティブ)
   - B) FluxCD (ネイティブ)
   - C) 両方ともネイティブサポートを持つ
   - D) どちらもネイティブサポートを持たない

<details>
<summary>回答を表示</summary>

**回答: B) FluxCD (ネイティブ)**

**解説:**
FluxCD には Image Reflector と Image Automation controller がありますが、これらはオプションであり、デフォルトの bootstrap で常にインストールされるわけではありません。Argo CD で同様の機能を使うには、別プロジェクトの Argo Image Updater が必要です。

</details>

4. どのユースケースで ArgoCD がより適した選択肢になりますか？
   - A) UI 要件がない CLI 主導のワークフロー
   - B) 視覚的なデプロイ管理と SSO 統合を必要とするチーム
   - C) 最小限のリソース使用量が求められる場合
   - D) OCI artifact ベースのデプロイ

<details>
<summary>回答を表示</summary>

**回答: B) 視覚的なデプロイ管理と SSO 統合を必要とするチーム**

**解説:**
ArgoCD は、チームが Web UI による視覚的なフィードバック、包括的な RBAC、およびエンタープライズ ID プロバイダーとの SSO 統合を必要とする環境で優れています。

</details>

5. ArgoCD と FluxCD は同じ cluster で併用できますか？
   - A) いいえ、両者は相互排他的です
   - B) はい、互いを補完できます
   - C) 開発環境でのみ可能です
   - D) 特別な設定がある場合のみ可能です

<details>
<summary>回答を表示</summary>

**回答: B) はい、互いを補完できます**

**解説:**
ArgoCD と FluxCD は、管理するリソースを分ければ併用できます。同じオブジェクトを両方に reconcile または prune させないでください。一般的なパターンは、インフラストラクチャ管理と image automation に FluxCD を使い、UI を備えたアプリケーションのデプロイに ArgoCD を使う方法です。

</details>

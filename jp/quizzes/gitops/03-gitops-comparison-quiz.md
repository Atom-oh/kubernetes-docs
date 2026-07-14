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

2. デプロイソースとして OCI artifacts をネイティブでより適切にサポートしているツールはどれですか？
   - A) ArgoCD
   - B) FluxCD
   - C) 両方とも同等にサポートしている
   - D) どちらも OCI をサポートしていない

<details>
<summary>回答を表示</summary>

**回答: B) FluxCD**

**解説:**
FluxCD は OCIRepository ソースタイプを通じて OCI artifacts をファーストクラスでサポートしており、OCI 準拠のレジストリから保存およびデプロイできます。ArgoCD の OCI サポートは Helm charts に限定されています。

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
FluxCD には Image Reflector および Image Automation controllers による組み込みの Image Automation があります。ArgoCD では、同様の機能のために別プロジェクトである Argo Image Updater が必要です。

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
ArgoCD と FluxCD は併用できます。一般的なパターンは、インフラストラクチャ管理と image automation には FluxCD を使用し、UI を備えたアプリケーションのデプロイには ArgoCD を使用することです。

</details>

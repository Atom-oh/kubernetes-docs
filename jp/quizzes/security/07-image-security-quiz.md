<span id="quiz-questions"></span>

# コンテナイメージセキュリティクイズ
> **最終更新**: 2026年9月13日

<span id="_1-what-is-the-correct-command-to-scan-a-container-image-with-trivy"></span>

### 1. 指定したイメージ参照をTrivyでスキャンするコマンドはどれですか？

- A. trivy scan "$IMAGE_REF"
- B. trivy image "$IMAGE_REF"
- C. trivy container "$IMAGE_REF"
- D. trivy check "$IMAGE_REF"

<details>
<summary>解答を表示</summary>

**正解: B. trivy image "$IMAGE_REF"**

trivy imageがイメージスキャン用のコマンドです。IMAGE_REFには実際のダイジェスト参照を設定します。構文が正しくても、レジストリへのアクセス、データベースの最新性、パッケージの検出範囲は保証されません。

</details>

<span id="_2-which-tool-is-used-for-image-signing-and-verification"></span>

### 2. イメージダイジェストと承認署名者の関係を検証するツールはどれですか？

- A. TrivyのCVEデータベース
- B. Cosign/Sigstore
- C. Clairのパッケージスキャナー
- D. Docker imagePullPolicy

<details>
<summary>解答を表示</summary>

**正解: B. Cosign/Sigstore**

Cosignは、鍵またはOIDC identity/issuer、digest、必須の透明性証跡を検証します。署名があっても、既知の脆弱性がないとは限りません。

</details>

<span id="_3-what-does-the-shift-left-security-approach-mean"></span>

### 3. シフトレフトセキュリティとは何ですか？

- A. 本番まで確認を先送りする
- B. 開発、PR、ビルドの早い段階で確認する
- C. ソースアクセスをセキュリティチームに限定する
- D. 本番での再スキャンをなくす

<details>
<summary>解答を表示</summary>

**正解: B. 開発、PR、ビルドの早い段階で確認する**

早期に確認することで、フィードバックまでの時間を短縮できます。新たなCVEや実行時の挙動を検出するには、リリース後もレジストリの再スキャンとランタイム検出が必要です。

</details>

<span id="_4-what-is-the-main-characteristic-of-distroless-images"></span>

### 4. 標準distroless runtimeイメージの特性は何ですか？

- A. 全Linuxツールを含む
- B. 最小限のアプリruntime構成要素
- C. シェルとdebuggerを必ず含む
- D. package managerが必須

<details>
<summary>解答を表示</summary>

**正解: B. 最小限のアプリruntime構成要素**

標準のランタイムイメージではシェルやパッケージマネージャーを省きますが、デバッグ版は構成が異なります。アプリケーションのバイナリやライブラリには脆弱性が残る場合があります。

</details>

<span id="_5-what-are-the-two-types-of-amazon-ecr-image-scanning"></span>

### 5. 現在のECR BasicとEnhancedはどう異なりますか？

- A. BasicはAWSネイティブOSスキャン、EnhancedはInspectorでOS/言語packageをスキャン
- B. Basicは常にClair、EnhancedはOSだけ
- C. 両方がpushを自動拒否
- D. Enhancedは全イメージを永久スキャン

<details>
<summary>解答を表示</summary>

**正解: A. BasicはAWSネイティブOSスキャン、EnhancedはInspectorでOS/言語packageをスキャン**

Basicは手動スキャンとpush時スキャン、Enhancedはpush時スキャンと継続スキャンに対応します。findingsとenhancedFindings、およびECRとInspectorのイベントを区別してください。

</details>

<span id="_6-what-is-sbom-software-bill-of-materials"></span>

### 6. SBOMは何を提供しますか？

- A. 脆弱性がない認証
- B. ツールが検出したソフトウェア構成要素一覧
- C. 承認署名者の自動証明
- D. デプロイ認可

<details>
<summary>解答を表示</summary>

**正解: B. ツールが検出したソフトウェア構成要素一覧**

SBOMにはソフトウェア構成要素とその関係が記録されますが、検出範囲が不完全な場合があります。digestに結び付いた署名付きattestationと、その検証policyは別々に評価してください。

</details>

<span id="_7-what-policy-type-verifies-image-signatures-in-kyverno"></span>

### 7. 旧Kyverno ClusterPolicyでイメージ署名を確認するルールはどれですか？

- A. validateのみ
- B. mutateのみ
- C. verifyImages
- D. generateのみ

<details>
<summary>解答を表示</summary>

**正解: C. verifyImages**

旧形式のverifyImagesと、新しいImageValidatingPolicyを区別してください。Kyverno 1.19.1の例では、CEL policyに加えて、通常のコンテナ、initコンテナ、ephemeralコンテナを対象とするregistry/digest制限を適用します。

</details>

<span id="_8-why-should-you-use-digests-instead-of-image-tags"></span>

### 8. タグでなくダイジェストを固定する理由は何ですか？

- A. 常に短いから
- B. 特定のイメージ内容を識別するから
- C. 自動で署名検証するから
- D. CVEを除去するから

<details>
<summary>解答を表示</summary>

**正解: B. 特定のイメージ内容を識別するから**

タグは別のイメージを指すよう変更できますが、digestは特定の内容を識別します。digestの固定は成果物を再現可能に選択するのに役立ちますが、署名者の信頼性、脆弱性の確認、可用性の検証に代わるものではありません。

</details>

<span id="_9-what-does-trivy-not-scan"></span>

### 9. Trivyの静的確認と別の領域はどれですか？

- A. OS package識別
- B. 言語依存スキャン
- C. 稼働中syscall/process動作検出
- D. ソース内secret検出

<details>
<summary>解答を表示</summary>

**正解: C. 稼働中syscall/process動作検出**

パッケージ、設定ミス、シークレットのスキャンと、ランタイムの挙動検出は別の機能です。Falcoなどのランタイム向けツールは別途設計してください。

</details>

<span id="_10-which-is-not-a-container-image-registry-security-best-practice"></span>

### 10. 不適切なregistryアクセス運用はどれですか？

- A. privateイメージの承認済みpull ID
- B. publicイメージのdigest/署名検証
- C. 任意の匿名push/削除を許可
- D. registry、admission、scan gate権限を分離

<details>
<summary>解答を表示</summary>

**正解: C. 任意の匿名push/削除を許可**

意図的に公開しているイメージへの匿名readは、それ自体が脆弱性ではありません。機密性、書き込み/削除権限、来歴、レート制限をそれぞれ管理してください。

</details>

<span id="_11-what-is-the-recommended-action-when-image-scanning-fails-in-ci-cd-pipeline"></span>

### 11. 合意したCIスキャン判定を通過しない場合、どうすべきですか？

- A. 常に無視
- B. 公開/署名前に停止して原因を調べる
- C. 別イメージを再ビルドし未スキャンでpush
- D. 終了コード0を強制

<details>
<summary>解答を表示</summary>

**正解: B. 公開/署名前に停止して原因を調べる**

policy違反とscanner、データベース、権限に関するエラーを区別し、スキャン結果を保持してください。スキャン後に別の成果物を再ビルドしてデプロイしてはいけません。例外を認める場合は、理由、責任者、期限を明記してください。

</details>

<span id="_12-what-is-not-an-advantage-of-alpine-base-images"></span>

### 12. Alpineについて誤った想定はどれですか？

- A. musl libcを使う
- B. apk package managerを使う
- C. glibc依存アプリと常に完全互換
- D. 選択releaseのサポート寿命確認が必要

<details>
<summary>解答を表示</summary>

**正解: C. glibc依存アプリと常に完全互換**

Alpineはmuslを使うため、glibcに依存するバイナリで互換性の問題が起こる場合があります。イメージサイズだけで脆弱性の数やビルド速度が決まるわけではありません。

</details>

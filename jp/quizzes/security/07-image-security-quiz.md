<span id="quiz-questions"></span>

# コンテナイメージセキュリティクイズ
> **最終更新**: September 13, 2026

<span id="_1-what-is-the-correct-command-to-scan-a-container-image-with-trivy"></span>

### 1. 指定イメージ参照をTrivyでスキャンするコマンドはどれですか？

- A. trivy scan "$IMAGE_REF"
- B. trivy image "$IMAGE_REF"
- C. trivy container "$IMAGE_REF"
- D. trivy check "$IMAGE_REF"

<details>
<summary>解答を表示</summary>

**正解: B. trivy image "$IMAGE_REF"**

trivy imageがイメージスキャンコマンドです。IMAGE_REFに実ダイジェスト参照を設定します。有効構文だけではregistryアクセス、DB鮮度、package検出範囲は成立しません。

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

Cosignは鍵またはOIDC identity/issuer、digest、必要な透明性証拠を検証します。署名は既知脆弱性がないことを保証しません。

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

早期確認はフィードバックを短縮します。新CVEと実行時動作にはrelease後もregistry再スキャンとruntime検出が必要です。

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

標準runtimeはshell/package managerを省き、debug版は異なります。アプリbinary/libraryには脆弱性が残り得ます。

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

Basicは手動/scan-on-push、Enhancedはscan-on-push/continuousに対応します。findingsとenhancedFindings、ECRとInspectorイベントを区別します。

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

SBOMは構成要素と関係を記録しますが、範囲が不完全な場合があります。digestへ結び付ける署名付きattestationと検証policyを別評価します。

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

旧verifyImagesと新ImageValidatingPolicyを区別します。Kyverno 1.19.1例はCEL policyと、通常/init/ephemeralを対象とするregistry/digest制限を併用します。

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

タグは移動し得ますがdigestは内容を識別します。再現可能な成果物選択を支えますが、署名者信頼、脆弱性確認、可用性検証の代わりではありません。

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

package、設定誤り、secretスキャンとruntime動作検出は異なります。Falcoなどruntimeツールを別設計します。

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

意図的publicイメージの匿名readは本質的に脆弱性ではありません。機密性、書込/削除権限、来歴、レート制限を別々に制御します。

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

policy違反とscanner/DB/権限エラーを区別し、結果を保持します。scan後に再ビルドした別成果物をデプロイしないでください。例外には理由、所有者、期限が必要です。

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

Alpineはmuslなのでglibc依存binaryで互換問題が起こり得ます。イメージサイズだけでは脆弱性数もビルド速度も保証されません。

</details>

# Container Image Security クイズ

このクイズでは、image scanning、image signing、supply chain security、base image の選択に関する理解を確認します。

## クイズ問題

### 1. Trivy で container image をスキャンする正しいコマンドはどれですか？

A. trivy scan nginx:latest
B. trivy image nginx:latest
C. trivy container nginx:latest
D. trivy check nginx:latest

<details>
<summary>答えを表示</summary>

**答え: B. trivy image nginx:latest**

**解説:**
Trivy の image scanning コマンド:
```bash
trivy image nginx:latest
trivy image --severity HIGH,CRITICAL nginx:latest
trivy image --format json nginx:latest
```

`trivy image` は container image の脆弱性をスキャンします。

</details>

### 2. image signing と verification に使用されるツールはどれですか？

A. Trivy
B. Cosign/Sigstore
C. Clair
D. Anchore

<details>
<summary>答えを表示</summary>

**答え: B. Cosign/Sigstore**

**解説:**
Cosign は Sigstore project の一部であり、container image signing と verification のためのツールです:
```bash
# Sign image
cosign sign --key cosign.key myregistry/myimage:tag

# Verify signature
cosign verify --key cosign.pub myregistry/myimage:tag
```

Trivy、Clair、Anchore は vulnerability scanner です。

</details>

### 3. 「Shift-Left」security approach とは何を意味しますか？

A. security を operations phase まで延期する
B. security を development の早期段階に移動する
C. Security team のみが責任を持つ
D. automation を削除する

<details>
<summary>答えを表示</summary>

**答え: B. security を development の早期段階に移動する**

**解説:**
Shift-Left security は、security check を development cycle の可能な限り早い段階に移動します:
- IDE 段階での scanning
- CI/CD pipeline での build gate
- PR review 中の security check

問題が早く見つかるほど、修正コストは低くなります。

</details>

### 4. Distroless image の主な特徴は何ですか？

A. すべての Linux utilities を含む
B. application の実行に必要な最小限の component のみを含む
C. debugging tools を含む
D. package manager を含む

<details>
<summary>答えを表示</summary>

**答え: B. application の実行に必要な最小限の component のみを含む**

**解説:**
Distroless image には次の特徴があります:
- shell（bash、sh など）がない
- package manager がない
- 不要な utilities がない
- 最小限の attack surface
- application runtime のみ

security と image size の面でメリットがあります。

</details>

### 5. Amazon ECR image scanning の 2 つのタイプは何ですか？

A. Basic scanning、Enhanced scanning
B. Automatic scanning、Manual scanning
C. Quick scanning、Deep scanning
D. Free scanning、Paid scanning

<details>
<summary>答えを表示</summary>

**答え: A. Basic scanning、Enhanced scanning**

**解説:**
Amazon ECR scanning のタイプ:
- **Basic scanning**: Clair ベース、OS package vulnerability scan
- **Enhanced scanning**: Amazon Inspector ベース、OS + programming language packages、continuous scanning

Enhanced scanning には追加コストがかかりますが、より包括的です。

</details>

### 6. SBOM（Software Bill of Materials）とは何ですか？

A. software license のリスト
B. software component のリスト
C. security vulnerability のリスト
D. build command のリスト

<details>
<summary>答えを表示</summary>

**答え: B. software component のリスト**

**解説:**
SBOM は、software に含まれるすべての component（libraries、dependencies、versions など）のリストです。supply chain security と vulnerability management に不可欠です:
```bash
# Generate SBOM with Trivy
trivy image --format spdx-json -o sbom.json nginx:latest
```

</details>

### 7. Kyverno で image signature を検証する policy type はどれですか？

A. validate
B. mutate
C. verifyImages
D. generate

<details>
<summary>答えを表示</summary>

**答え: C. verifyImages**

**解説:**
Kyverno の `verifyImages` rule は container image signature を検証します:
```yaml
spec:
  rules:
  - name: verify-signature
    verifyImages:
    - imageReferences:
      - "myregistry/*"
      attestors:
      - entries:
        - keys:
            publicKeys: |-
              -----BEGIN PUBLIC KEY-----
              ...
              -----END PUBLIC KEY-----
```

</details>

### 8. image tag の代わりに digest を使用すべきなのはなぜですか？

A. 名前が短くなる
B. immutability が保証される
C. pull が速くなる
D. storage space を節約できる

<details>
<summary>答えを表示</summary>

**答え: B. immutability が保証される**

**解説:**
Tag（例: `nginx:latest`）は、別の image を指すように変更できます。Digest（例: `nginx@sha256:abc123...`）は特定の image content の hash であり、immutable です:
```yaml
image: nginx@sha256:abc123def456...
```

これにより reproducibility と security が確保されます。

</details>

### 9. Trivy がスキャンしないものはどれですか？

A. OS package vulnerabilities
B. Language-specific dependencies
C. Runtime behavior
D. Secret detection

<details>
<summary>答えを表示</summary>

**答え: C. Runtime behavior**

**解説:**
Trivy は次をスキャンする static analysis tool です:
- OS package vulnerabilities
- Language-specific dependencies（npm、pip、go など）
- IaC misconfigurations
- Hardcoded secrets
- Licenses

runtime behavior analysis は Falco のような runtime security tool の領域です。

</details>

### 10. container image registry security の best practice ではないものはどれですか？

A. private registry を使用する
B. image scanning を有効化する
C. anonymous pulling を許可する
D. vulnerable image push をブロックする

<details>
<summary>答えを表示</summary>

**答え: C. anonymous pulling を許可する**

**解説:**
Registry security の best practice:
- private registry を使用する
- IAM ベースの authentication
- image scanning を有効化する
- vulnerable image push/pull をブロックする
- Image signature verification
- immutable tags または digests を使用する

anonymous pulling は security risk であり、production environment では無効化すべきです。

</details>

### 11. CI/CD pipeline で image scanning が失敗した場合に推奨される action は何ですか？

A. warning のみをログに記録する
B. build を停止する
C. 自動修正する
D. 無視して続行する

<details>
<summary>答えを表示</summary>

**答え: B. build を停止する**

**解説:**
CI/CD pipeline では、Critical/High vulnerabilities が見つかった場合に build を停止すべきです:
```bash
trivy image --exit-code 1 --severity HIGH,CRITICAL myimage:tag
```

`--exit-code 1` は vulnerabilities が見つかった場合に non-zero exit code を返し、pipeline を失敗させます。

</details>

### 12. Alpine base image の利点ではないものはどれですか？

A. サイズが小さい
B. vulnerabilities が少ない
C. glibc compatibility
D. build が速い

<details>
<summary>答えを表示</summary>

**答え: C. glibc compatibility**

**解説:**
Alpine Linux の特徴:
- サイズが小さい（~5MB）
- 最小限の packages
- musl libc を使用する（glibc ではない）

Alpine は glibc ではなく musl libc を使用するため、glibc に依存する一部の application では compatibility issues が発生する可能性があります。

</details>

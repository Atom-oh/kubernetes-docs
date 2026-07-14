# CI Pipelines クイズ

> **関連ドキュメント**: [CI Pipelines](../../ops/03-ci-pipelines.md)

## 選択問題

### 1. ECR lifecycle policies の主な目的は何ですか？

- A) container image を自動的にビルドすること
- B) image の保持を管理し、ストレージコストを削減すること
- C) image の脆弱性をスキャンすること
- D) 複数のリージョン間で image をレプリケートすること

<details>
<summary>回答を表示</summary>

**回答: B) image の保持を管理し、ストレージコストを削減すること**

**解説:**
ECR lifecycle policies は、経過日数や数などのルールに基づいて古い images を自動的に期限切れにして削除します。これにより、重要な images（production tags など）を無期限に保持しつつ、ストレージの無制限な増加を防ぎ、コストを削減できます。

</details>

### 2. GitLab Runner を EKS 上で実行する場合、分離のために推奨される executor type はどれですか？

- A) Shell executor
- B) Docker executor
- C) Kubernetes executor
- D) SSH executor

<details>
<summary>回答を表示</summary>

**回答: C) Kubernetes executor**

**解説:**
Kubernetes executor は各 CI job を個別の Pod で実行し、jobs 間に強力な分離を提供します。jobs の完了後にリソースを自動的にクリーンアップし、node selectors や tolerations などの Kubernetes 機能を活用できます。

</details>

### 3. GitHub Actions Runner Controller (ARC) とは何ですか？

- A) GitHub-hosted runner service
- B) self-hosted GitHub runners のための Kubernetes operator
- C) GitHub API client library
- D) container registry controller

<details>
<summary>回答を表示</summary>

**回答: B) self-hosted GitHub runners のための Kubernetes operator**

**解説:**
ARC は、workflow の需要に基づいて self-hosted GitHub Actions runners を自動的にスケールする Kubernetes operator です。jobs がキューに入ると runner pods を作成し、完了後にクリーンアップします。

</details>

### 4. multi-platform container builds (linux/amd64, linux/arm64) の利点は何ですか？

- A) image sizes が小さくなる
- B) build times が速くなる
- C) 異なる CPU architectures (x86 and Graviton) のサポート
- D) security scanning が向上する

<details>
<summary>回答を表示</summary>

**回答: C) 異なる CPU architectures (x86 and Graviton) のサポート**

**解説:**
multi-platform builds は、x86 (amd64) と ARM (arm64/Graviton) processors の両方で動作する images を作成します。これにより、Graviton instances を使用したコスト最適化が可能になり、多様な deployment environments をサポートできます。

</details>

### 5. BuildKit cache は container build performance をどのように向上させますか？

- A) すべての build steps をスキップすることによって
- B) layer artifacts をキャッシュし、変更されていない layers を再利用することによって
- C) images をより小さく圧縮することによって
- D) すべての operations を並列化することによって

<details>
<summary>回答を表示</summary>

**回答: B) layer artifacts をキャッシュし、変更されていない layers を再利用することによって**

**解説:**
BuildKit は build artifacts と layer outputs をインテリジェントにキャッシュします。source files が変更されていない場合、再ビルドする代わりに cached layers を再利用します。Cache は registries、S3、または local storage に保存して、builds 間で共有できます。

</details>

### 6. Kaniko は主に何に使用されますか？

- A) Container orchestration
- B) Docker daemon なしで container images をビルドすること
- C) Container runtime security
- D) Image vulnerability scanning

<details>
<summary>回答を表示</summary>

**回答: B) Docker daemon なしで container images をビルドすること**

**解説:**
Kaniko は Docker daemon や privileged mode を必要とせずに、Dockerfiles から container images をビルドします。これにより、Docker-in-Docker の実行がセキュリティ上の懸念を生む、または利用できない CI/CD environments に最適です。

</details>

### 7. GitLab CI において、`services` keyword の目的は何ですか？

- A) deployment targets を定義すること
- B) テスト用に補助 containers（databases など）を起動すること
- C) GitLab Pages を設定すること
- D) monitoring をセットアップすること

<details>
<summary>回答を表示</summary>

**回答: B) テスト用に補助 containers（databases など）を起動すること**

**解説:**
`services` keyword は、main job container と並行して実行される containers を定義します。これらは、tests がやり取りする必要のある databases (PostgreSQL, MySQL) や caches (Redis) などの test dependencies によく使用されます。

</details>

### 8. CI/CD で container build cache を保存するための推奨アプローチは何ですか？

- A) local disk のみ
- B) --cache-to と --cache-from flags を使用した registry-based cache
- C) CI/CD では cache を使用しない
- D) cache を git repository に保存する

<details>
<summary>回答を表示</summary>

**回答: B) --cache-to と --cache-from flags を使用した registry-based cache**

**解説:**
registry-based caching は build cache layers を container registry に保存し、異なる CI runners 間でアクセスできるようにします。BuildKit の `--cache-to` と `--cache-from` flags により、このパターンを使って一貫した build acceleration を実現できます。

</details>

### 9. GitHub ARC を設定する際、`minRunners` setting は何を制御しますか？

- A) 最大 concurrent jobs
- B) 維持される idle runners の最小数
- C) Runner memory allocation
- D) Job timeout duration

<details>
<summary>回答を表示</summary>

**回答: B) 維持される idle runners の最小数**

**解説:**
`minRunners` は、warm runners の baseline が常に利用可能であることを保証し、job startup latency を低減します。これを 0 より大きく設定すると、時間に敏感な workflows の cold-start delays を防げますが、idle resource costs は増加します。

</details>

### 10. CI/CD runners に long-lived credentials の代わりに IAM roles を使用することの security benefit は何ですか？

- A) 認証が速くなる
- B) credential の自動ローテーションと exposure risk の低減
- C) 設定がより簡単になる
- D) Cross-account access

<details>
<summary>回答を表示</summary>

**回答: B) credential の自動ローテーションと exposure risk の低減**

**解説:**
IAM roles は自動的にローテーションされる temporary credentials を提供し、long-lived access keys が漏えいまたは侵害されるリスクを排除します。Pod Identity または IRSA と組み合わせることで、runners は secrets を保存せずに scoped permissions を取得できます。

</details>

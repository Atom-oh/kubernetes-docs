# Amazon EKS セキュリティクイズ

> **最終更新日**: 2026年11月21日

このクイズでは、Amazon EKS のセキュリティ機能、ベストプラクティス、設定に関する理解度を確認します。

## クイズの概要
- ネットワークセキュリティ
- コンテナセキュリティ
- データセキュリティ
- コンプライアンスと監査
- セキュリティのベストプラクティス

クラスターアクセス認証、IRSA/OIDC、Pod Identity に関する問題は、各詳細ページのクイズにあります：[EKS クラスターアクセス認証クイズ](./05-eks-security-cluster-access-quiz.md)、[IRSA と OIDC プロバイダーのクイズ](./05-eks-security-irsa-oidc-quiz.md)、[EKS Pod Identity クイズ](./05-eks-security-pod-identity-quiz.md)。

## 選択式問題

### 1. ポリシー適用に対応する EKS ネットワークで、ラベルに基づく Pod トラフィックルールを表現する Kubernetes の仕組みはどれですか？

- A) インスタンスのセキュリティグループのみ
- B) ポリシーを適用するネットワーク実装と NetworkPolicy リソース
- C) VPC エンドポイントポリシーのみ
- D) ホストファイアウォールコマンドのみ

<details>
<summary>回答を表示</summary>

**回答: B) ポリシーを適用するネットワーク実装と NetworkPolicy リソース**

**解説:**

NetworkPolicy は Kubernetes のラベルと Namespace を使って Pod と許可するトラフィックを選択します。ポリシーを適用するネットワーク実装が必要です。Pod 用のサポート対象セキュリティグループを含むセキュリティグループも、有用な AWS の制御機能であり、インスタンス全体に限られるわけではありません。VPC エンドポイントポリシーは、サポートされている AWS サービスへのアクセスを制御するもので、任意のラベルベースの Pod トラフィックを制御するものではありません。

**ポリシーの完全な例:** これらのマニフェストは、アプリケーションのインストールや CNI の置き換えを目的とせず、分離されたデモ用 Namespace を記述しています。サポート対象のポリシー適用 CNI と、一般的な CoreDNS Deployment/Pod ラベルを使用する標準的な Linux EC2 ノードを想定しています。Auto Mode やノードローカル DNS を使う場合は、実際に使用するリゾルバ経路に対するルールが必要です。CoreDNS の ingress を制限する場合は、その管理者もこれらのクエリを許可する必要があります。

Namespace の管理者が保存して適用してください。デフォルト拒否で双方向の通信を隔離し、frontend → API と API → database について、クライアント側の egress と宛先側の ingress を明示的に許可します。DNS では UDP と TCP の両方が必要です。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-network-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
---
apiVersion: v1
kind: Namespace
metadata:
  name: security-monitoring-demo
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: security-network-demo
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: security-network-demo
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-to-api
  namespace: security-network-demo
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-ingress
  namespace: security-network-demo
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-to-database
  namespace: security-network-demo
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-ingress
  namespace: security-network-demo
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 5432
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: monitor-api
  namespace: security-network-demo
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: security-monitoring-demo
      podSelector:
        matchLabels:
          app: prometheus
    ports:
    - protocol: TCP
      port: 9090
```

監視側のピアでは、1つのピア内で namespaceSelector **と** podSelector を使用しているため、security-monitoring-demo 内で条件に一致する Prometheus Pod のみが選択されます。クライアントが egress 分離されている場合は、その Pod からの送信接続も許可する必要があります。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: prometheus-to-demo-api
  namespace: security-monitoring-demo
spec:
  podSelector:
    matchLabels:
      app: prometheus
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: security-network-demo
      podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 9090
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

| フロー | これらのポリシーで意図する結果 |
|---|---|
| frontend → api TCP 8080 | 許可 |
| api → database TCP 5432 | 許可 |
| frontend → database TCP 5432 | 拒否 |
| 無関係な Pod → api TCP 8080 | 拒否 |
| 選択された Prometheus → api TCP 9090 | 許可 |
| monitoring Namespace 内の別の Pod → api TCP 9090 | 拒否 |
| ワークロード → 条件に一致する CoreDNS Pod UDP/TCP 53 | 許可。ただしリゾルバ側の制御に従う |
| 任意の外部宛先 | 明示的な egress ルールを追加しない限り拒否 |

ポリシーは加算的に適用され、順序には依存しません。別の広範な許可ルールがあれば、結果として許可範囲が広がる可能性があります。デフォルト拒否は、それを上書きしません。対象の CNI 上で、インストール済みポリシー一式、DNS 名前解決、新たに許可・拒否する接続をテストしてください。確立済み接続、hostNetwork/ノードのトラフィック、NAT の動作には実装固有の制限があります。単純な NetworkPolicy は、IMDS やホストファイアウォールに対する汎用的な境界ではありません。

外部サービスについては、実際の宛先アドレスとポートを限定するか、選択した実装がサポートする DNS 対応の制御を使用してください。ポート 443 のすべての宛先や、10.0.0.0/8 全体を許可しても、サービスの許可リストにはなりません。既存の EKS ネットワークでポリシーを有効にする安全な方法として、任意の代替 Calico/Cilium マニフェストや不完全な kube-proxy 置換フラグを使わないでください。

対応する原文の18件の合成セレクター/ポートケースをローカルで確認しました。パケット/CNI テストは実行していません。参考資料：[Kubernetes NetworkPolicy の動作](https://kubernetes.io/docs/concepts/services-networking/network-policies/)。

</details>

### 2. EKS でコンテナイメージのセキュリティを確保するために、相補的な制御を組み合わせる方法はどれですか？

- A) 手作業によるイメージ検査のみに頼る
- B) 公式イメージはすべて脆弱性がないと見なす
- C) スキャン、署名/検証、Admission 制御を組み合わせる
- D) コンテナ内のウイルス対策のみに頼る

<details>
<summary>回答を表示</summary>

**回答: C) スキャン、署名/検証、Admission 制御を組み合わせる**

**解説:**

スキャナーが特定するのは、ルールと脆弱性データベースで対象となる問題です。すべてのバックドアや将来の脆弱性が存在しないことを証明するものではありません。署名が証明するのは、設定された信頼ポリシーに基づく完全性と ID の関係であり、署名済みソフトウェアが安全であることではありません。Admission 制御は、選択したデプロイポリシーを適用します。保守されている最小限のベースイメージを使用し、パッチ適用のために再ビルドし、例外を追跡して、適切な ECR 基本/拡張スキャンモードなどを選択してください。

**AWS Signer と Notation:** コンテナ署名プラットフォームは `Notation-OCI-SHA384-ECDSA` です。Notation AWS Signer プラグインを使用して、すでにプッシュ済みのイメージにダイジェストで署名します。`Aws::ECR::Image` プラットフォームや `start-signing-job --source-image` は、サポートされているワークフローではありません。確認した AWS CLI は、そのオプションを拒否します。

現在の ECR マネージド署名も、レジストリ署名ルールを使うサポート対象のプッシュトリガー方式です。これを選ぶ場合は、適切なプロファイル/権限を設定し、実際の署名ステータスを確認してからプロモーションしてください。イメージがプッシュされたというだけで、非同期署名が完了したと見なさないでください。

**信頼設定:** 検証済みの Notation/Signer プラグインのインストール、該当パーティションの AWS Signer ルート信頼ストア、レビュー済みの厳格な信頼ポリシーを準備してください。この商用リージョンの例では、信頼対象を1つのリポジトリと承認済みプロファイルに限定しています。アカウント/リージョン/リポジトリ/プロファイルをすべて一貫して置き換えてください。証明書が AWS ルートにつながるというだけで、任意の署名者を信頼してはいけません。

```json
{
  "version": "1.0",
  "trustPolicies": [
    {
      "name": "reviewed-eks-repository",
      "registryScopes": [
        "123456789012.dkr.ecr.us-west-2.amazonaws.com/team/app"
      ],
      "signatureVerification": {
        "level": "strict"
      },
      "trustStores": [
        "signingAuthority:aws-signer-ts"
      ],
      "trustedIdentities": [
        "arn:aws:signer:us-west-2:123456789012:/signing-profiles/eks_images"
      ]
    }
  ]
}
```

このポリシーを `notation policy import notation-trust-policy.json` で、ビルド環境が所有する Notation 設定にインポートしてください。置き換える前に既存のポリシーを確認してください。レビューされていないスクリプトで、開発者の共有信頼設定を上書きしてはいけません。ビルドロールには、リポジトリを限定した ECR のプル/プッシュ操作、ECR 認証、および必要な SignPayload/GetRevocationStatus 権限が必要です。署名プロファイルの作成は別のプロビジョニング作業です。既存の承認済みプロファイルを使うだけであれば、ビルドに PutSigningProfile は必要ありません。

**CodeBuild の例:** これは buildspec であり、CodePipeline の定義ではありません。Bash、Python、Docker/デーモンアクセス、AWS CLI、Trivy、Notation、AWS Signer プラグインがあらかじめインストールされ、バージョン固定された、所有者が管理する Linux ビルドイメージが必要です。プロジェクトに必要なランタイム特権、ネットワークアクセス、スキャナーのデータベース、IAM ロール、信頼ストア/ポリシー、既存の ECR リポジトリは別途設定してください。Dockerfile とソースは、そのビルドロールが信頼する入力です。この例では解決済みの Git コミットと、商用 AWS アカウント/リージョンを1つ使用します。クロスアカウント署名の設計は実装していません。

```yaml
version: 0.2
env:
  shell: bash
phases:
  build:
    commands:
      - |
        set -euo pipefail
        umask 077
        # Reserve this generated artifact name; remove stale output before any build step.
        rm -f -- verified-image.json
        : "${AWS_REGION:?Set the commercial AWS Region}"
        : "${AWS_ACCOUNT_ID:?Set the expected ECR/signing account ID}"
        : "${ECR_REPOSITORY:?Set the complete repository name, including any path}"
        : "${SIGNING_PROFILE_ARN:?Set the approved AWS Signer profile ARN}"
        : "${CODEBUILD_RESOLVED_SOURCE_VERSION:?This example requires a resolved Git commit}"
        python3 - <<'PY'
        import os, re
        checks = {
            "AWS_ACCOUNT_ID": r"[0-9]{12}",
            "AWS_REGION": r"[a-z0-9-]+",
            "ECR_REPOSITORY": r"[a-z0-9]+(?:[._/-][a-z0-9]+)*",
            "CODEBUILD_RESOLVED_SOURCE_VERSION": r"(?:[0-9a-f]{40}|[0-9a-f]{64})",
        }
        for name, pattern in checks.items():
            if not re.fullmatch(pattern, os.environ[name]):
                raise SystemExit("Invalid example input: " + name)
        prefix = f"arn:aws:signer:{os.environ['AWS_REGION']}:{os.environ['AWS_ACCOUNT_ID']}:/signing-profiles/"
        profile = os.environ["SIGNING_PROFILE_ARN"]
        if not profile.startswith(prefix) or not re.fullmatch(r"[A-Za-z0-9_/]+", profile[len(prefix):]):
            raise SystemExit("Use an approved signing profile in this example's account/Region")
        PY
        REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        IMAGE_URI="${REGISTRY}/${ECR_REPOSITORY}:${CODEBUILD_RESOLVED_SOURCE_VERSION}"
        ACTUAL_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
        if [[ "$ACTUAL_ACCOUNT" != "$AWS_ACCOUNT_ID" ]]; then
          printf '%s\n' 'Unexpected build-role account' >&2
          exit 1
        fi
        aws ecr get-login-password --region "$AWS_REGION" |
          docker login --username AWS --password-stdin "$REGISTRY"
        docker build --tag "$IMAGE_URI" .
        trivy image --image-src docker --scanners vuln --severity HIGH,CRITICAL \
          --exit-code 1 --no-progress "$IMAGE_URI"
        docker push "$IMAGE_URI"
        DIGESTS_JSON=$(docker image inspect --format '{{json .RepoDigests}}' "$IMAGE_URI")
        IMAGE_REFERENCE=$(python3 - "$REGISTRY/$ECR_REPOSITORY" "$DIGESTS_JSON" <<'PY'
        import json, re, sys
        digests = json.loads(sys.argv[2])
        if not isinstance(digests, list):
            raise SystemExit("Expected Docker RepoDigests array")
        pattern = re.escape(sys.argv[1]) + r"@sha256:[0-9a-f]{64}"
        matching = {d for d in digests if isinstance(d, str) and re.fullmatch(pattern, d)}
        if len(matching) != 1:
            raise SystemExit("Expected exactly one pushed digest for this repository")
        print(matching.pop())
        PY
        )
        notation sign --plugin com.amazonaws.signer.notation.plugin \
          --id "$SIGNING_PROFILE_ARN" "$IMAGE_REFERENCE"
        notation verify "$IMAGE_REFERENCE"
        python3 - "$IMAGE_REFERENCE" "$CODEBUILD_RESOLVED_SOURCE_VERSION" <<'PY'
        import json, sys
        with open("verified-image.json", "x") as stream:
            json.dump({"image": sys.argv[1], "sourceCommit": sys.argv[2]}, stream)
            stream.write("\n")
        PY
artifacts:
  files:
    - verified-image.json
```

レビュー済みのプロジェクト設定を通じて、`AWS_ACCOUNT_ID`、`AWS_REGION`、`ECR_REPOSITORY`（例: `team/app`）、`SIGNING_PROFILE_ARN` を設定してください。このコマンドはレジストリのホスト名に対して認証し、階層化されたリポジトリパスを保持し、プッシュ前にローカルでビルドしたイメージをスキャンします。また、任意の最初のエントリーや変更可能なタグではなく、プッシュ済みの一致する RepoDigest を選択します。ここでの Trivy は HIGH/CRITICAL の脆弱性検出をゲートします。シークレット、設定、来歴については、明示的に設計した他のチェックを追加してください。

すべてのプロモーション手順は、`set -euo pipefail` を設定した1つの Bash ビルドブロック内にあります。ログイン/ビルド/スキャン/プッシュ/署名/検証に失敗すると、新たなアーティファクトが書き込まれる前に停止します。ビルドが失敗していても CodeBuild の post_build は実行されることがあるため、保護されていない別個の post_build プッシュ/署名ステップは安全ではありません。以前の出力が再利用されないよう、予約したアーティファクトパスを最初に消去します。下流のデプロイでもビルドの成功を必須とし、アーティファクトを検証してください。JSON ファイルだけでは、認可にも署名済みアテステーションにもなりません。

`verified-image.json` には、EKS デプロイ/GitOps の利用者向けに正確なダイジェスト参照が含まれます。これは ECS の `imagedefinitions.json` ではなく、それ自体で何かをデプロイするものでもありません。署名/検証が成功するには、実際のレジストリアクセス、信頼、失効チェック、AWS Signer の可用性も引き続き必要です。

**Admission:** 本番環境の署名検証機能は、選択した Notation/Signer の署名と信頼ポリシーを理解できる必要があります。AWS は Gatekeeper と Ratify の組み合わせ、および Kyverno と AWS Signer/Notation の統合を文書化しています。汎用ポリシーエンジンのインストール、ConstraintTemplate を伴わない Gatekeeper の制約、別の署名方式用の公開鍵フィールドでは、その統合を実現できません。適用を強制する前に、信頼済み/未信頼のプロファイル、署名なしのイメージ、ダイジェストの不一致、失効/期限切れの署名、検証機能の停止、Admission 失敗時のポリシーを検証してください。

以下の独立した Kyverno 1.19.1 ルールは、security-demo 内の**イメージ参照の構文とリポジトリ**だけを制限します。通常のコンテナ、init コンテナ、ephemeral コンテナを確認します。署名を検証するとは主張していません。

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: demo-approved-image-reference
spec:
  validationActions:
  - Deny
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      resources:
      - pods
      - pods/ephemeralcontainers
      operations:
      - CREATE
      - UPDATE
      scope: Namespaced
  matchConditions:
  - name: demo-namespace
    expression: has(object.metadata.namespace) && object.metadata.namespace == 'security-demo'
  validations:
  - expression: object.spec.containers.all(c, c.image.matches('^123456789012[.]dkr[.]ecr[.]us-west-2[.]amazonaws[.]com/team/app@sha256:[0-9a-f]{64}$'))
      && (!has(object.spec.initContainers) || object.spec.initContainers.all(c, c.image.matches('^123456789012[.]dkr[.]ecr[.]us-west-2[.]amazonaws[.]com/team/app@sha256:[0-9a-f]{64}$')))
      && (!has(object.spec.ephemeralContainers) || object.spec.ephemeralContainers.all(c, c.image.matches('^123456789012[.]dkr[.]ecr[.]us-west-2[.]amazonaws[.]com/team/app@sha256:[0-9a-f]{64}$')))
    message: Use a sha256 digest from the approved team/app repository in security-demo.
```

検証内容: モックのパイプライン失敗/順序/アーティファクトケース20件と、Kyverno CLI による実際の文字列ポリシーケース9件。buildspec/Bash/Python/JSON と、リリース済みポリシー CRD を確認しました。イメージのビルド/スキャン/プッシュ、実際の AWS 署名の生成/検証、Admission webhook のデプロイは行っていません。これは、環境に関する前提を明示したレビュー済みの学習用ワークフローであり、本番運用に向けてテスト済みのワークフローではありません。

参考資料：[Signer の署名](https://docs.aws.amazon.com/signer/latest/developerguide/image-signing-steps.html)、[Signer の検証](https://docs.aws.amazon.com/signer/latest/developerguide/image-verification.html)、[ECR マネージド署名](https://docs.aws.amazon.com/AmazonECR/latest/userguide/managed-signing.html)、[EKS Admission 検証](https://docs.aws.amazon.com/eks/latest/userguide/image-verification.html)、[CodeBuild buildspec](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html)、[Trivy イメージフラグ](https://trivy.dev/docs/latest/references/configuration/cli/trivy_image/)。

</details>

### 3. EKS で一貫性のある最新の Pod セキュリティベースラインを適用する方法はどれですか？

- A) 特権モードのみを無効にする
- B) PSA を通じてバージョン指定の PSS プロファイルを使い、必要に応じてレビュー済みの Admission ポリシーを適用する
- C) root 以外の UID のみを設定する
- D) root ファイルシステムを読み取り専用にするだけ

<details>
<summary>回答を表示</summary>

**回答: B) PSA を通じてバージョン指定の PSS プロファイルを使い、必要に応じてレビュー済みの Admission ポリシーを適用する**

**解説:**

Pod Security Standards は Privileged、Baseline、Restricted の各プロファイルを定義します。Pod Security Admission は Namespace で選択したプロファイルを適用します。PSA は Kubernetes 1.25 から安定版です。PodSecurityPolicy は 1.21 で非推奨となり、**1.25 で削除されました**。現在のクラスターには、削除済みの API をデプロイできません。古い例で制約名に「PSP」が使われていても、Kyverno/Gatekeeper ポリシーは別個のリソースです。

レビュー済みの v1.36 プロファイルを使う、分離された Linux の例を示します。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
---
apiVersion: v1
kind: Pod
metadata:
  name: security-context-demo
  namespace: security-demo
spec:
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: busybox:1.38.0
    command:
    - sh
    - -c
    args:
    - id && sleep 3600
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    resources:
      requests:
        cpu: 10m
        memory: 16Mi
      limits:
        cpu: 100m
        memory: 64Mi
```

Namespace の enforce は Pod の Admission に適用されます。audit/warn はコントローラーテンプレートの違反を報告できますが、Deployment/Job の適用が成功しても、その Pod が enforce を通過することの証明にはなりません。ラベルを変更しても、既存の Pod が遡って排除されることはありません。実際のクラスターに合ったポリシーバージョンを選び、適用を強制する前に既存のワークロードを確認してください。

runAsNonRoot/runAsUser と seccomp は、allowPrivilegeEscalation や capabilities とは別の設定です。fsGroup は Pod レベルのボリューム所有権設定であり、コンテナの capability ではありません。読み取り専用の root はアプリケーションとの互換性に配慮したハードニングとして有用ですが、PSS Restricted で普遍的に必須ではなく、マウント済み PVC を読み取り専用にするものでもありません。実際のアプリケーションには、互換性のある UID/GID と、書き込み可能な一時/キャッシュ/ソケットのパスが必要です。root を前提とする一般的な nginx イメージは、これらのフィールドを追加するだけでは動作しません。

**追加のスコープ付き Admission ルール:** この Kyverno 1.19.1 ValidatingPolicy は、security-demo 内の通常のコンテナ、init コンテナ、ephemeral コンテナをすべて確認します。privileged が未指定の場合は false として受け入れ、true の場合は拒否します。廃止されたインストールマニフェストではなく、現行の v1 ポリシー API を使用します。

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: demo-disallow-privileged
spec:
  validationActions:
  - Deny
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      resources:
      - pods
      - pods/ephemeralcontainers
      operations:
      - CREATE
      - UPDATE
      scope: Namespaced
  matchConditions:
  - name: demo-namespace
    expression: has(object.metadata.namespace) && object.metadata.namespace == 'security-demo'
  validations:
  - expression: object.spec.containers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged)
      || c.securityContext.privileged == false) && (!has(object.spec.initContainers)
      || object.spec.initContainers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged)
      || c.securityContext.privileged == false)) && (!has(object.spec.ephemeralContainers)
      || object.spec.ephemeralContainers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged)
      || c.securityContext.privileged == false))
    message: Privileged containers, including init and ephemeral containers, are not
      allowed in security-demo.
```

このルール1つで PSS プロファイル全体やイメージ検証を置き換えることはできません。特権を必要とする CSI/監視エージェントや、意図的な例外は、プラットフォーム所有者の管理下に置いてください。デモ用ポリシーを kube-system に一律適用しないでください。Gatekeeper で実現する場合は、実際の ConstraintTemplate、対応する制約、検証済みの動作が必要です。

マニフェスト/スキーマと、Kyverno CLI の実際の6つのケースでは、未指定/false、privileged を有効にした通常/init/ephemeral コンテナ、別の Namespace を対象にしています。ephemeral コンテナのテストには、Pod 作成ではなく合成した UPDATE オブジェクトを使っています。ライブの Admission webhook や Pod のデプロイは実行していません。

参考資料：[Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/)、[Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)。

</details>

### 4. EKS ワークロードに関する相補的なセキュリティ証跡を得る方法はどれですか？

- A) 時折行う手動レビューだけを使う
- B) AWS Config のチェックだけを使う
- C) GuardDuty だけを使う
- D) セキュリティ態勢の検出結果、監査ログ、実行時のカバレッジ、検証済みの対応経路を組み合わせる

<details>
<summary>回答を表示</summary>

**回答: D) セキュリティ態勢の検出結果、監査ログ、実行時のカバレッジ、検証済みの対応経路を組み合わせる**

**解説:**

| 証跡/制御 | 提供するものと、証明できないこと |
|---|---|
| Security Hub CSPM / AWS Config | サポート対象の設定制御と検出結果。Kubernetes 全体や規制への適合を証明するものではない |
| GuardDuty EKS Protection | 独立したストリームを通じた Kubernetes 監査ベースの脅威分析 |
| GuardDuty Runtime Monitoring | サポート対象ノードでのエージェントベースの実行時イベント。有効化されているだけではカバレッジを証明できない |
| CloudTrail | AWS API のアクティビティ。Kubernetes 監査ログやアプリケーションのデータアクセスログの代替にはならない |
| Kubernetes 監査ログ | 監査ポリシー/レベルに応じて選択されたリクエスト。ワークロードのすべてのアクション/本文を記録するわけではない |
| CloudWatch / インシデント通知経路 | ログ分析と運用担当者への配信。配信、保持、対応を検証する必要がある |

Security Hub CSPM の FSBP 標準は CIS Kubernetes Benchmark ではありません。サポート対象の CIS AWS Foundations 制御も、CIS Kubernetes の監査全体を網羅するものではありません。適用するベンチマーク/バージョン、手動チェック、マネージドサービスの例外、ワークロードの実際の義務に必要な証跡を記録してください。

検出器、CSPM 標準、Config レコーダー、CloudTrail については、既存の組織/リージョンの管理方針に従ってください。別のリージョン検出器を作成したり、集中管理された設定を上書きしたり、バケットポリシー、暗号化、イベントセレクター、保持期間を準備せずにトレイルを開始したりしないでください。CloudTrail のデータイベントは、デフォルトの管理イベントのカバレッジとは別です。このレビューでは、アカウントレベルの監視リソースをプロビジョニングしていません。

**EKS 固有のチェック:** ソースの章に記載されているとおり、意図したコントロールプレーンログの種類、有効化の完了、ログの到着を確認してください。`eks-cluster-logging-enabled`（全種類、定期実行）と `eks-cluster-log-enabled`（任意の選択された種類、設定変更時）は、どちらも有効な Config ルールです。自動で最新バージョンのカタログが適用されると想定せず、`oldestVersionSupported` パラメーターを維持してください。明示的な encryptionConfig 制御の検出結果があっても、EKS 1.28 以降の API データにデフォルトのエンベロープ暗号化がないことを意味するわけではありません。

GuardDuty の監査分析に、別途 CloudWatch への監査ログエクスポートは不要です。Runtime Monitoring には、サポート対象のセキュリティエージェント/データエンドポイントと、実際のカバレッジが必要です。現在の EKS サポート対象には EC2 と Auto Mode が含まれますが、Fargate や Hybrid Nodes は含まれません。現行の RUNTIME_MONITORING 機能を使用し、レガシーの EKS_RUNTIME_MONITORING からの移行を確認してください。EKS_AUDIT_LOGS を Runtime Monitoring と取り違えないでください。

**CSPM イベントルーティングの例:** これを `security-event-pattern.json` として保存してください。アクティブな HIGH/CRITICAL ASFF 検出結果のうち、ワークフローステータスが NEW/NOTIFIED のものを選択します。異なる OCSF イベントスキーマを持つ `Findings Imported V2` には、意図的に一致しません。

```json
{
  "source": [
    "aws.securityhub"
  ],
  "detail-type": [
    "Security Hub Findings - Imported"
  ],
  "detail": {
    "findings": {
      "Severity": {
        "Label": [
          "HIGH",
          "CRITICAL"
        ]
      },
      "Workflow": {
        "Status": [
          "NEW",
          "NOTIFIED"
        ]
      },
      "RecordState": [
        "ACTIVE"
      ]
    }
  }
}
```

この合成イベントはパターンの確認専用であり、実際の検出結果でも、完全な ASFF インポートペイロードでもありません。`synthetic-security-event.json` として保存してください。

```json
{
  "version": "0",
  "id": "00000000-0000-0000-0000-000000000001",
  "account": "123456789012",
  "region": "us-west-2",
  "time": "2026-09-11T00:00:00Z",
  "source": "aws.securityhub",
  "detail-type": "Security Hub Findings - Imported",
  "resources": [],
  "detail": {
    "findings": [
      {
        "Id": "synthetic-example-not-a-real-finding",
        "Severity": {
          "Label": "HIGH"
        },
        "Workflow": {
          "Status": "NEW"
        },
        "RecordState": "ACTIVE"
      }
    ]
  }
}
```

認可された AWS テストでは、`aws events test-event-pattern --event-pattern file://security-event-pattern.json --event file://synthetic-security-event.json --region us-west-2` が一致するはずです。LOW の重大度、RESOLVED/SUPPRESSED のワークフロー、ARCHIVED 状態、フィールド欠落、V2 イベントタイプについてもテストしてください。これらはこのパターンに一致しないはずです。このレビューでは JSON/ソーススキーマを確認しましたが、EventBridge サービスのマッチャーやライブイベントの配信は確認していません。

ターゲット設定では、現行の EventBridge ガイドがサポートする、所有する SNS トピックへの publish 権限を持つ**既存のレビュー済み EventBridge 実行ロール**を使用できます。所有する ARN に置き換えたうえで、`security-event-targets.json` として保存してください。

```json
[
  {
    "Id": "SecurityAlerts",
    "Arn": "arn:aws:sns:us-west-2:123456789012:eks-security-alerts",
    "RoleArn": "arn:aws:iam::123456789012:role/EventBridgeSecurityAlerts"
  }
]
```

このロールには、適切な EventBridge の信頼設定と、最小権限の sns:Publish 権限が必要です。該当するトピック/キーのポリシーや、明示的な拒否も確認してください。別の方法として、実行ロールを指定しないターゲットでは、サポートされているリソースベースの権限経路が必要です。ターゲット JSON だけでは権限は付与されず、ルール、トピック、ロール、サブスクリプションも作成されません。

`aws events put-targets --rule eks-security-alerts --targets file://security-event-targets.json --region us-west-2` を使う前に、既存のルール/ターゲットの所有者を確認してください。コマンドの終了ステータスだけでなく、FailedEntryCount と FailedEntries も確認します。SNS サブスクリプション、暗号化権限、再試行/デッドレターの動作、制御されたエンドツーエンドの配信テストを確認してください。この監査中に通知は送信していません。

**監査調査:** 実際の EKS ロググループで使う以下の Logs Insights の例は、Kubernetes 監査レコードの JSON フィールド検出を前提としています。RBAC の変更リクエストに焦点を当てています。responseStatus.code を調べ、成功したリクエストと拒否されたリクエストを区別してください。

```text
fields @timestamp, verb, user.username, objectRef.resource, objectRef.namespace, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter verb in ["create", "update", "patch", "delete", "deletecollection"]
| filter objectRef.resource in ["roles", "rolebindings", "clusterroles", "clusterrolebindings"]
| sort @timestamp desc
| limit 100
```

クエリを信頼する前に、サンプルレコードのフィールドとストリーム名を確認してください。関連する証跡を保持し、担当者/重大度/エスカレーションを定め、対応プロセスをテストします。検出結果のダッシュボードやサービスが有効であるだけでは、是正が完了したことやコンプライアンス上の義務を満たしたことの証拠にはなりません。

参考資料：[CSPM 標準](https://docs.aws.amazon.com/securityhub/latest/userguide/standards-view-manage.html)、[ASFF イベント](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-cwe-event-formats.html)、[V2 イベント](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-v2-cwe-event-formats.html)、[EventBridge ターゲットの権限](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html)、[EKS 監査ログ](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)。

</details>

### 5. AWS アクセスを一元的に管理し、ライフサイクルも管理する必要があるアプリケーション認証情報には、どの方法が適していますか？

- A) アクセス、ローテーション、再読み込みの計画なしに値を保存する
- B) 環境変数を暗号化の仕組みとして扱う
- C) 適切な AWS シークレット/パラメーターバックエンドと、スコープを限定した ID、および明示的な受け渡し/ライフサイクル設計を使用する
- D) 本番環境の認証情報をイメージにハードコードする

<details>
<summary>回答を表示</summary>

**回答: C) 適切な AWS シークレット/パラメーターバックエンドと、スコープを限定した ID、および明示的な受け渡し/ライフサイクル設計を使用する**

**解説:**

Secrets Manager と Parameter Store は AWS アクセス制御と監査を一元化できますが、外部バックエンドを使うだけで自動的に安全になるわけではありません。ワークロード ID、最小権限、受け渡し、再読み込みの制御が必要です。Secrets Manager は、対応する認証情報に対して設定済みのローテーションをサポートします。Parameter Store には、同じ組み込みの認証情報ローテーションワークフローはありません。SecureString パラメーターの KMS 暗号化とバージョニングは、対象データベース/サービス内の認証情報を変更することとは別です。

EKS 1.28 以降では、Kubernetes API のすべてのデータがデフォルトの KMS v2 エンベロープ暗号化です。Secret マニフェスト内の Base64 は依然として単なるエンコードであり、API/Pod へのアクセスによって値が漏えいするおそれがあります。環境変数は値を渡す手段であって、暗号化ではありません。Secret が変更されても、既存プロセスの環境変数は更新されません。

**所有者と受け渡し方法を意図的に選択する:** ESO は Kubernetes Secret を書き込みます。ASCP と Secrets Store CSI Driver はファイルをマウントし、必要に応じて Kubernetes Secret と同期できます。同じターゲット Secret を両方のコントローラーに管理させないでください。ファイルのみを使う CSI 設計でも、ワークロード/ノードのアクセス制御が必要です。任意の同期を有効にすると、Kubernetes API に値のコピーが追加されます。

**ASCP の例:** これは、既存環境にロールアウトするものではなく、レビュー済み EKS 1.36 の例に対する、新規の所有者管理の Linux EC2 インストールです。まず既存のリリース/CSIDriver の所有者、ノードとの互換性、特権を持つプラットフォームエージェントの Admission、ネットワークアクセス、スケジューリングを確認してください。Fargate では CSI のノード DaemonSet を実行できません。Hybrid/Auto Mode での使用には、現行のプロバイダー/ノード要件があります。以下のローカルレンダリングでそれらを検証できるわけではありません。

別途管理する CSI 1.6.1 ドライバーには、`secrets-csi-values.yaml` で次の設定を使用してください。両方の AWS トークンオーディエンス、任意の Secret 同期、ローテーションを明示的に設定しています。

```yaml
tokenRequests:
- audience: sts.amazonaws.com
- audience: pods.eks.amazonaws.com
syncSecret:
  enabled: true
enableSecretRotation: true
rotationPollInterval: 2m
```

ASCP Chart 3.1.3 には通常、依存関係としてドライバーが含まれ、トークンオーディエンスも設定されます。この例ではドライバーを別途インストールするため、二重にドライバーがインストールされないよう、以下を `ascp-values.yaml` として保存してください。

```yaml
secrets-store-csi-driver:
  install: false
```



```bash
helm repo add secrets-store-csi-driver https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
helm repo add aws-secrets-manager https://aws.github.io/secrets-store-csi-driver-provider-aws
helm repo update secrets-store-csi-driver aws-secrets-manager
helm install csi-secrets-store secrets-store-csi-driver/secrets-store-csi-driver \
  --version 1.6.1 --namespace kube-system -f secrets-csi-values.yaml --wait --timeout 5m
helm install secrets-provider-aws aws-secrets-manager/secrets-store-csi-driver-provider-aws \
  --version 3.1.3 --namespace kube-system -f ascp-values.yaml --wait --timeout 5m
```

既存のインストールでは、その管理者のバージョン/CRD アップグレード手順が必要です。これらの新規インストール用コマンドや、不完全な `helm upgrade` を、無関係な値に対して実行しないでください。Chart のバージョン固定とレンダリングの成功だけでは、ノードプラグインとの互換性、接続、シークレットアクセスは証明できません。

所有する Secrets Manager JSON シークレットを username/password フィールド付きで準備します。さらに、その特定のシークレットにスコープを限定した `ASCPSecretReader` ロールと、必要に応じて適切なカスタマーキーの復号権限を準備してください。この IRSA 信頼設定では、正確な ServiceAccount サブジェクトを指定します。OIDC issuer/provider とアカウントを一貫してすべて置き換えてください。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/EXAMPLEOIDCID"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLEOIDCID:aud": "sts.amazonaws.com",
          "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLEOIDCID:sub": "system:serviceaccount:security-secrets-demo:ascp-reader"
        }
      }
    }
  ]
}
```

以下の Namespace、ServiceAccount、SecretProviderClass、Pod は、ファイル受け渡しの例を構成しています。実際のクラスターに適した PSS バージョンを選択してください。JMESPath でフィールドを別名に抽出し、`secretObjects.data.objectName` ではマウント済みの別名を指定します。secretObjects.data 内での `property` フィールドはサポートされていません。権限 0444 では、この非 root のデモプロセスがファイルを読み取れます。実際のアプリケーションでは、誰がマウント/Pod 作成できるかを制限し、互換性のある UID/GID/ファイル権限を選択してください。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-secrets-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ascp-reader
  namespace: security-secrets-demo
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ASCPSecretReader
automountServiceAccountToken: false
---
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: db-secrets-files
  namespace: security-secrets-demo
spec:
  provider: aws
  parameters:
    region: us-west-2
    usePodIdentity: 'false'
    objects: |
      - objectName: arn:aws:secretsmanager:us-west-2:123456789012:secret:training/db-credentials-ABC123
        objectType: secretsmanager
        objectAlias: credentials
        filePermission: '0444'
        jmesPath:
        - path: username
          objectAlias: db_username
        - path: password
          objectAlias: db_password
  secretObjects:
  - secretName: csi-db-credentials
    type: Opaque
    data:
    - objectName: db_username
      key: username
    - objectName: db_password
      key: password
---
apiVersion: v1
kind: Pod
metadata:
  name: secret-file-check
  namespace: security-secrets-demo
spec:
  serviceAccountName: ascp-reader
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: check
    image: busybox:1.37
    command:
    - sh
    - -c
    - test -s /mnt/secrets/db_username && test -s /mnt/secrets/db_password && sleep 3600
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    volumeMounts:
    - name: secrets
      mountPath: /mnt/secrets
      readOnly: true
  volumes:
  - name: secrets
    csi:
      driver: secrets-store.csi.k8s.io
      readOnly: true
      volumeAttributes:
        secretProviderClass: db-secrets-files
```

この Pod は、内容を出力せずにファイルの存在を確認します。`automountServiceAccountToken: false` は、Kubernetes API トークンの自動マウントを無効にしますが、CSI ドライバーによる明示的なトークンリクエストは無効にしません。この IRSA の例の代わりに Pod Identity を使用する場合は、ワークロードの ServiceAccount に対してサポート対象のエージェント/関連付けを使用し、`usePodIdentity: "true"` を設定してください。IRSA のアノテーションによってその関連付けが行われるとは限りません。

任意の csi-db-credentials Secret は、Pod がボリュームをマウントした後にのみ同期されます。そのライフサイクルは利用する Pod に従い、すべての利用者が削除されると削除される場合があります。SecretProviderClass を作成しただけでは、単独で Secret が生成されることはありません。値を出力せずに、SecretProviderClassPodStatus とコントローラー/ノードのイベントを確認してください。

Parameter Store では、SecureString に対する適切な KMS アクセスと、所有するパラメーターに対するプロバイダー必須の SSM 読み取り権限を付与したうえで、objects の値に代わりに次のエントリーを指定できます。これは objects の一部であり、SecretProviderClass 全体ではありません。

```yaml
- objectName: /training/app/config
  objectType: ssmparameter
  objectAlias: app_config
  filePermission: "0444"
```

**ESO の代替方法:** ソースの章で準備した EKSSecretReader IRSA ロール/信頼設定を、正確な eso-reader ServiceAccount に対して使用します。ESO 2.10.0 と v1 CRD がその管理者のもとでインストール済みであれば、以下は別のターゲットである eso-db-credentials に書き込みます。バックエンドの ARN、Namespace、ロール、JSON のプロパティは、実際に準備したシークレットを参照している必要があります。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-secrets-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: eso-reader
  namespace: security-secrets-demo
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/EKSSecretReader
automountServiceAccountToken: false
---
apiVersion: external-secrets.io/v1
kind: SecretStore
metadata:
  name: aws-secretsmanager
  namespace: security-secrets-demo
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-west-2
      auth:
        jwt:
          serviceAccountRef:
            name: eso-reader
---
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: db-credentials
  namespace: security-secrets-demo
spec:
  refreshPolicy: Periodic
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: SecretStore
  target:
    name: eso-db-credentials
    creationPolicy: Owner
    deletionPolicy: Retain
  data:
    - secretKey: username
      remoteRef:
        key: arn:aws:secretsmanager:us-west-2:123456789012:secret:training/db-credentials-ABC123
        property: username
    - secretKey: password
      remoteRef:
        key: arn:aws:secretsmanager:us-west-2:123456789012:secret:training/db-credentials-ABC123
        property: password
```

ここで Owner は、ターゲット Secret を ExternalSecret に関連付けます。所有者を削除すると、ガベージコレクションが実行される場合があります。Retain が対象とするのはバックエンドの消失であり、所有者削除の影響を受けないという意味ではありません。ESO の serviceAccountRef JWT 方式は IRSA です。コントローラーの Pod Identity は別の設計です。コントローラー ServiceAccount を関連付け、ストアの auth ブロックを省略します。ESO は serviceAccountRef を使って、別の Pod Identity 関連付け済みアカウントになりすますことはできません。

**ローテーションと再読み込み:** CSI 1.6 以降では、ローテーションに kubelet の RequiresRepublish 呼び出しを使用します。requiresRepublish だけではローテーションは有効になりません。ドライバーの enableSecretRotation フラグも必要です。ここでの2分という rotationPollInterval は、キャッシュ期間の最小値であり、エンドツーエンドの更新が2分以内に必ず行われるという保証ではありません。実際のタイミングは kubelet の再公開に依存します。ESO の更新間隔は、別個の調整スケジュールです。アプリケーションは、更新されたファイルを再度開く/監視するか、制御されたロールアウトを実行する必要があります。subPath マウントと既存の環境変数は自動更新されません。

Secrets Manager の rotate-secret は、デフォルトで即時にローテーションします。`--no-rotate-immediately` を指定した場合でも、Lambda ローテーション関数をテストし、AWSPENDING を作成/削除することがあります。また、以前に設定した頻度/日数ベースのスケジュールが実行される可能性もあります。無害なスケジュールのみの確認や、読み取り専用の確認ではありません。ローテーションを実行する前に、対象の認証情報の変更、有効期間の重複、アプリケーションの再読み込み、ロールバックを確認してください。

**シークレット値を含まない Terraform の例:** Terraform の sensitive は、選択した出力の表示を抑えるだけです。通常の secret_string/random_password の値は、引き続き state に保存される可能性があります。以下では、既存の承認済み KMS キーを使って、シークレットのメタデータのみを管理します。既存のシークレットを管理する場合は、この設定で管理する前に、所有者を通じて調整/インポートしてください。

```hcl
terraform {
  required_version = ">= 1.5.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.69.1"
    }
  }
}

variable "aws_region" {
  type    = string
  default = "us-west-2"
}

variable "kms_key_arn" {
  type        = string
  description = "Existing approved Secrets Manager encryption key ARN in this Region"
}

provider "aws" {
  region = var.aws_region
}

resource "aws_secretsmanager_secret" "credentials" {
  name                    = "training/db-credentials"
  kms_key_id              = var.kms_key_arn
  recovery_window_in_days = 30
  lifecycle {
    prevent_destroy = true
  }
}

output "secret_arn" {
  value = aws_secretsmanager_secret.credentials.arn
}
```

この設定ではシークレットのバージョン/値は作成されず、ローテーションも有効になりません。ハードコードされた Terraform 文字列や平文のコマンドライン引数ではなく、承認済みのシークレット入力手順を通じて初期値を設定してください。メタデータのみが対象の想定でも、state と plan を保護してください。prevent_destroy は Terraform 設定上のガードであり、サービス側で変更不能な保護ではありません。リソース設定を削除したり、Terraform の外で操作したりすれば、保護の前提は変わります。

検証では、ネイティブ Kubernetes およびリリース済みの SecretProviderClass/ESO CRD、公開済みの Chart チェックサム、CSI/ASCP オブジェクトの22件のレンダリング、合成データを使った実際の JMESPath 投影を確認しました。生成された null の creationTimestamp フィールドは、Swagger スキーマの確認時にのみ除外しました。Terraform fmt は成功しましたが、init/plan/apply は実行していません。AWS シークレットの取得、マウント、同期、ローテーションは行っておらず、アプリケーションの再読み込みもテストしていません。

参考資料：[ASCP 設定](https://github.com/aws/secrets-store-csi-driver-provider-aws)、[CSI 1.6.1](https://github.com/kubernetes-sigs/secrets-store-csi-driver/releases/tag/v1.6.1)、[CSI Secret 同期](https://secrets-store-csi-driver.sigs.k8s.io/topics/sync-as-kubernetes-secret)、[CSI ローテーション](https://secrets-store-csi-driver.sigs.k8s.io/topics/secret-auto-rotation)、[ESO AWS 認証](https://github.com/external-secrets/external-secrets/blob/v2.10.0/docs/provider/aws-access.md)、[EKS エンベロープ暗号化](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html)、[Secrets Manager のローテーション](https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/rotate-secret.html)。

</details>

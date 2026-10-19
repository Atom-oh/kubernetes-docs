# Amazon EKS セキュリティクイズ

> **最終更新日**: 2026年9月11日

このクイズでは、Amazon EKS のセキュリティ機能、ベストプラクティス、設定への理解を確認します。

## クイズの概要
- EKS の認証と認可
- ネットワークセキュリティ
- コンテナセキュリティ
- データセキュリティ
- コンプライアンスと監査
- セキュリティのベストプラクティス

## 選択問題

### 1. IAM ユーザーまたはロールについて、ID 認証と Kubernetes 認可を正しく組み合わせる EKS の設定はどれですか？

- A) IAM の管理権限だけを使う
- B) ID の認証経路を設定せずに RBAC ルールを作成する
- C) IAM のクラスターアクセスと、適切な RBAC および／または EKS アクセスポリシーを設定する
- D) API エンドポイントのネットワーク制限だけを使う

<details>
<summary>回答を表示</summary>

**回答: C) IAM のクラスターアクセスと、適切な RBAC および／または EKS アクセスポリシーを設定する**

**解説:**

IAM は設定された EKS アクセス経路を通じて、対象の人間または自動化用 ID を認証します。Kubernetes RBAC と EKS アクセスポリシーは Kubernetes 操作を認可し、それぞれの許可は加算されます。ネットワーク制限は別の防御層であり、認可の代わりにはなりません。Pod から Kubernetes への認証では通常 ServiceAccount トークンを使います。IRSA／Pod Identity はワークロードに AWS 認証情報を提供する仕組みです。

EKS クラスターのサービスロールと人間の開発者ロールは用途が異なります。開発者に AmazonEKSClusterPolicy を付与しても Kubernetes アクセスは許可されません。また、DescribeCluster／ListClusters 権限や kubeconfig ファイルだけでは、ワークロードに対する権限は得られません。

**権限を限定した実装:** 認可済みのプラットフォーム運用者が、既存の承認済み開発者 IAM ロール用に、以下の Namespace と RBAC を準備します。クラスターで EKS access entry が利用可能になっている必要があります。既存の管理者／ノードのマッピングを保持し、認証モードの移行を確認してください。サンプル ConfigMap で aws-auth を上書きしないでください。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
```



```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set its Region}"
: "${DEVELOPER_ROLE_ARN:?Set a prepared IAM role ARN, not an STS session ARN}"
MODE=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.accessConfig.authenticationMode --output text)
case "$MODE" in
  API|API_AND_CONFIG_MAP) ;;
  *) echo "Access entries are not enabled; review the migration first"; exit 1 ;;
esac
aws eks list-access-entries --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --output json > security-access-entries.json
python3 - "$DEVELOPER_ROLE_ARN" <<'PY'
import json, sys
with open("security-access-entries.json") as stream:
    existing = json.load(stream)["accessEntries"]
if sys.argv[1] in existing:
    raise SystemExit("Entry already exists; inspect its groups/policies instead of overwriting")
PY
aws eks create-access-entry --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --principal-arn "$DEVELOPER_ROLE_ARN" --type STANDARD \
  --kubernetes-groups security-demo-developers
```



```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: developer
  namespace: security-demo
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - apps
  resources:
  - deployments
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
- apiGroups:
  - batch
  resources:
  - jobs
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer
  namespace: security-demo
subjects:
- kind: Group
  name: security-demo-developers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer
  apiGroup: rbac.authorization.k8s.io
```

Access entry のグループ名は RoleBinding の subject と一致させます。このロールが許可する操作は security-demo Namespace 内に限られますが、既存の別の許可によって権限が広がる場合があります。Deployment／Job の作成によって、その Namespace 内の Secret、PVC、ServiceAccount を間接的に利用できるため、Secret の直接読み取りルールがないことはテナント分離の保証にはなりません。Admission とリソース所有権の制御を使い、テナントを分離してワークロード ID／リソースの利用を制限してください。

別途レビューした閲覧者には、Namespace スコープの AmazonEKSViewPolicy association を使う方法もあります。追加前に既存のアクセスポリシーを確認してください。この association は、より広い RBAC 権限や他のアクセスポリシーによる許可を取り消しません。`eks:namespaces` はアクセスポリシー association のリクエストを絞るもので、通常の kubectl リクエストをフィルタリングするものではありません。

**実際のログインを検証する:** 呼び出し元には、クラスターを検索して承認済みロールを引き受ける権限が必要です。次の例は既定のコンテキストを置き換えず、一時的な kubeconfig を作成します。

```bash
set -euo pipefail
umask 077
: "${CLUSTER_NAME:?Set the reviewed cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${DEVELOPER_ROLE_ARN:?Set the intended IAM role ARN}"
review_dir=$(mktemp -d "${TMPDIR:-/tmp}/eks-login-check.XXXXXXXX")
trap 'rm -rf -- "$review_dir"' EXIT
aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --role-arn "$DEVELOPER_ROLE_ARN" --kubeconfig "$review_dir/config"
kubectl --kubeconfig "$review_dir/config" auth can-i list pods -n security-demo
kubectl --kubeconfig "$review_dir/config" auth can-i create jobs -n security-demo
kubectl --kubeconfig "$review_dir/config" auth can-i list pods -n another-team
```

結果を想定した許可と照合し、Namespace をまたぐ予期しない権限があれば調査してください。`--as` はユーザー偽装による RBAC をテストするものであり、IAM アクセスポリシー経路が機能することは検証しません。このクイズでは IAM の実ログインや Kubernetes 認可テストを実行していません。ローカルで確認したのはスキーマ／シェルのチェックと、モックを使った access entry のフローです。

参考資料: [EKS access entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)、[EKS access policies](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)、[Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)。

</details>

### 2. ネットワークポリシーの適用に対応する EKS ネットワークで、Pod のトラフィックルールをラベルベースで表す Kubernetes の仕組みはどれですか？

- A) インスタンスのセキュリティグループだけを使う
- B) ネットワークポリシーを強制するネットワーク実装と NetworkPolicy リソースを使う
- C) VPC エンドポイントポリシーだけを使う
- D) ホストのファイアウォールコマンドだけを使う

<details>
<summary>回答を表示</summary>

**回答: B) ネットワークポリシーを強制するネットワーク実装と NetworkPolicy リソースを使う**

**解説:**

NetworkPolicy は Kubernetes のラベルと Namespace を使って Pod と許可するトラフィックを選択します。ポリシーを実施するネットワーク実装が必要です。Pod 用のセキュリティグループなど、セキュリティグループも有用な AWS の制御手段であり、インスタンス全体に限られるわけではありません。VPC エンドポイントポリシーは、対応する AWS サービスへのアクセスを制御するもので、任意のラベルベースの Pod トラフィックを制御するものではありません。

**ポリシー全体の例:** 次のマニフェストは、アプリケーションをインストールしたり CNI を置き換えたりするものではなく、隔離されたデモ用 Namespace を定義します。対応するネットワーク実装を備えた標準 Linux EC2 ノードと、一般的な CoreDNS Deployment／Pod のラベルを前提にしています。Auto Mode やノードローカル DNS では、実際に使われる名前解決経路に合わせたルールが必要です。CoreDNS の ingress を制限する場合は、CoreDNS の管理者もこれらの問い合わせを許可する必要があります。

Namespace の所有者が内容を保存して適用してください。既定の拒否で ingress と egress の両方を隔離し、frontend → API と API → database の通信について、送信側の egress と宛先側の ingress を明示的に許可します。DNS には UDP と TCP の両方が必要です。

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

monitoring peer では、1つの peer 内で namespaceSelector と podSelector の両方を使います。そのため security-monitoring-demo 内のうち、ラベルが一致する Prometheus Pod だけが選択されます。そのクライアントも egress で隔離されている場合は、送信接続の許可も必要です。

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

| 通信 | このポリシーで意図する結果 |
|---|---|
| frontend → api TCP 8080 | 許可 |
| api → database TCP 5432 | 許可 |
| frontend → database TCP 5432 | 拒否 |
| 無関係な Pod → api TCP 8080 | 拒否 |
| 選択された Prometheus → api TCP 9090 | 許可 |
| monitoring Namespace 内の別の Pod → api TCP 9090 | 拒否 |
| ワークロード → 一致する CoreDNS Pod UDP／TCP 53 | 許可（名前解決側の制御が適用されます） |
| 任意の外部宛先 | egress ルールを明示的に追加しない限り拒否 |

ポリシーは順序付けされず、許可が加算されます。別の広い許可ルールがあると結果が緩和されることがあり、default deny はそれを上書きしません。対象 CNI にインストールされたポリシー全体、DNS 解決、許可／拒否される新規接続をテストしてください。確立済み接続、hostNetwork／ノードのトラフィック、NAT の挙動には実装ごとの制約があります。単純な NetworkPolicy は、あらゆる IMDS やホストファイアウォールへのアクセスを防ぐ境界ではありません。

外部サービスへの通信は、実際の宛先アドレス／ポートに範囲を限定するか、選択した実装がサポートする DNS 対応制御を使ってください。ポート 443 の全宛先や 10.0.0.0/8 全体を許可しても、サービスの許可リストにはなりません。既存の EKS ネットワーク上でネットワークポリシーを有効にするために、任意の Calico／Cilium マニフェストを置き換えたり、kube-proxy 置換フラグの一部だけを設定したりするのは安全な方法ではありません。

元のページにある合成 selector／port の18ケースをローカルで確認しました。パケット転送や CNI の実テストは行っていません。参考資料: [Kubernetes NetworkPolicy の動作](https://kubernetes.io/docs/concepts/services-networking/network-policies/)。

</details>

### 3. EKS でコンテナイメージのセキュリティを強化するため、相互補完する制御を組み合わせる方法はどれですか？

- A) 手作業によるイメージ検査だけに依存する
- B) 公式イメージには脆弱性がないとみなす
- C) スキャン、署名／検証、Admission 制御を組み合わせる
- D) コンテナ内のウイルス対策だけに依存する

<details>
<summary>回答を表示</summary>

**回答: C) スキャン、署名／検証、Admission 制御を組み合わせる**

**解説:**

スキャナーが特定するのは、ルールと脆弱性データベースが対象とする問題です。すべてのバックドアや将来の脆弱性が存在しないことを証明するものではありません。署名が証明するのは、設定された信頼ポリシーに基づく完全性と署名者 ID との関係であり、署名されたソフトウェアの安全性ではありません。Admission 制御は、選択したデプロイポリシーを強制します。保守されている最小構成のベースイメージを使い、パッチのために再ビルドし、例外を追跡し、ECR basic／enhanced など適切なスキャン方式を選んでください。

**AWS Signer と Notation:** コンテナ署名プラットフォームは `Notation-OCI-SHA384-ECDSA` です。AWS Signer 用 Notation プラグインを使い、すでに push 済みのイメージを digest で指定して署名します。`Aws::ECR::Image` プラットフォームや `start-signing-job --source-image` はサポートされる手順ではありません。レビュー対象の AWS CLI はこのオプションを拒否します。

ECR マネージド署名も、レジストリの署名ルールを使う push 起点の方法としてサポートされています。選択する場合は、正しいプロファイルと権限を設定し、昇格前に実際の署名ステータスが完了するまで待ってください。イメージが push されたことだけで、非同期署名が完了したとはみなせません。

**信頼設定:** 検証済みの Notation／Signer プラグイン、該当する AWS パーティションの AWS Signer ルート信頼ストア、レビュー済みの厳格な信頼ポリシーを準備します。この商用リージョンの例は、信頼対象を1つのリポジトリと承認済みプロファイルに限定します。アカウント／リージョン／リポジトリ／プロファイルをすべて一貫して置き換えてください。証明書が AWS ルートに連なるという理由だけで、任意の署名者を信頼してはいけません。

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

そのポリシーを `notation policy import notation-trust-policy.json` でビルド環境が所有する Notation 設定にインポートします。既存ポリシーを確認してから置き換えてください。レビューしていないスクリプトから、開発者が共有する信頼設定を上書きしてはいけません。ビルドロールには、リポジトリを範囲指定した ECR pull／push 操作、ECR 認証、および必要な SignPayload／GetRevocationStatus 権限が必要です。署名プロファイルの作成は別のプロビジョニング作業です。既存の承認済みプロファイルを使うだけなら、ビルドに PutSigningProfile は必要ありません。

**CodeBuild の例:** これは CodePipeline 定義ではなく buildspec です。Bash、Python、Docker／デーモンアクセス、AWS CLI、Trivy、Notation、AWS Signer プラグインがすでにインストールされ、バージョン固定された所有済み Linux ビルドイメージが必要です。プロジェクトの実行権限、ネットワークアクセス、スキャナーデータベース、IAM ロール、信頼ストア／ポリシー、既存の ECR リポジトリは別途設定してください。Dockerfile とソースは、ビルドロールが信頼できる入力でなければなりません。この例は解決済みの Git commit と単一の商用 AWS アカウント／リージョンを使い、クロスアカウント署名には対応していません。

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

`AWS_ACCOUNT_ID`、`AWS_REGION`、`ECR_REPOSITORY`（例: `team/app`）、`SIGNING_PROFILE_ARN` はレビュー済みのプロジェクト設定から指定します。コマンドはレジストリのホスト名で認証し、ネストしたリポジトリパスを維持します。ローカルでビルドしたイメージを push 前にスキャンし、任意の最初のエントリや可変タグではなく、push された一致する RepoDigest を選びます。ここでの Trivy は HIGH／CRITICAL の脆弱性検出をゲートします。シークレット、設定、来歴については、要件を明確に設計した別のチェックを追加してください。

すべての昇格手順は `set -euo pipefail` を指定した1つの Bash ブロック内にあります。ログイン／ビルド／スキャン／push／署名／検証のいずれかが失敗すると、新しい成果物を書き出す前に停止します。CodeBuild の post_build はビルド失敗後にも実行されることがあるため、保護されていない push／署名を別の post_build 手順に置くのは安全ではありません。以前の出力を再利用しないよう、予約済み成果物パスを先に消去します。後続のデプロイでもビルド成功を必須とし、成果物を検証する必要があります。JSON ファイルだけでは認可済みであることや、署名済み attestation を証明できません。

`verified-image.json` には、EKS のデプロイ／GitOps 利用者が使う正確な digest 参照が含まれます。これは ECS の `imagedefinitions.json` ではなく、デプロイ自体も行いません。署名／検証の成功は、実際のレジストリアクセス、信頼設定、失効確認、AWS Signer の可用性にも依存します。

**Admission:** 本番環境の署名検証器は、選択した Notation／Signer 署名と信頼ポリシーを理解している必要があります。AWS は Ratify を使う Gatekeeper、および AWS Signer／Notation 統合を使う Kyverno を案内しています。汎用のポリシーエンジンをインストールするだけ、ConstraintTemplate のない Gatekeeper constraint を置くだけ、異なる署名方式の公開鍵フィールドを使うだけでは、その統合が成立したことになりません。強制適用の前に、信頼／非信頼プロファイル、未署名イメージ、digest の不一致、失効／期限切れ署名、検証器の停止、Admission の失敗ポリシーを検証してください。

次の Kyverno 1.19.1 ルールが制限するのは security-demo 内の**イメージ参照形式とリポジトリ**だけです。通常のコンテナ、init コンテナ、ephemeral コンテナを確認します。意図的に署名を検証するとは主張していません。

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

検証では、パイプラインの失敗／順序／成果物に関する20件のモックケースと、Kyverno CLI による実際の文字列ポリシーケース9件を確認しました。buildspec／Bash／Python／JSON と公開済みポリシー CRD をチェックしました。イメージのビルド／スキャン／push、実際の AWS 署名の作成／検証、Admission webhook のデプロイは行っていません。これは前提を明記した学習用ワークフローであり、本番準備状況を検証したワークフローではありません。

参考資料: [Signer による署名](https://docs.aws.amazon.com/signer/latest/developerguide/image-signing-steps.html)、[Signer による検証](https://docs.aws.amazon.com/signer/latest/developerguide/image-verification.html)、[ECR マネージド署名](https://docs.aws.amazon.com/AmazonECR/latest/userguide/managed-signing.html)、[EKS Admission 検証](https://docs.aws.amazon.com/eks/latest/userguide/image-verification.html)、[CodeBuild buildspec](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html)、[Trivy image オプション](https://trivy.dev/docs/latest/references/configuration/cli/trivy_image/)。

</details>

### 4. EKS で一貫性のある最新の Pod セキュリティ基準を適用する方法はどれですか？

- A) privileged mode だけを無効にする
- B) PSA を使ってバージョン固定の PSS プロファイルを適用し、必要に応じてレビュー済み Admission ポリシーを使う
- C) non-root UID だけを設定する
- D) root filesystem を read-only にするだけ

<details>
<summary>回答を表示</summary>

**回答: B) PSA を使ってバージョン固定の PSS プロファイルを適用し、必要に応じてレビュー済み Admission ポリシーを使う**

**解説:**

Pod Security Standards は Privileged、Baseline、Restricted のプロファイルを定義します。Pod Security Admission は Namespace ごとに選択されたプロファイルを強制します。PSA は Kubernetes 1.25 から安定版です。PodSecurityPolicy は 1.21 で非推奨になり、**1.25 で削除**されました。現在のクラスターには削除済み API をデプロイできません。古い例で constraint 名に「PSP」が残っていても、Kyverno／Gatekeeper のポリシーは別のリソースです。

レビュー済みの v1.36 プロファイルを使った、隔離された Linux のデモは次のとおりです。

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

Namespace の enforce は Pod の Admission 時に適用されます。audit／warn はコントローラーテンプレートの違反を報告できますが、Deployment／Job の apply 成功は、その Pod が enforce を通過することを保証しません。ラベルを変更しても、既存の Pod は遡及的に退避されません。実際のクラスターに合うポリシーバージョンを選び、強制前に既存ワークロードを確認してください。

runAsNonRoot／runAsUser と seccomp は、allowPrivilegeEscalation や capabilities とは別の設定です。fsGroup は Pod レベルのボリューム所有権設定であり、コンテナ capability ではありません。read-only root はアプリケーションに適合する場合に有用な強化策ですが、PSS Restricted の普遍的な必須要件ではなく、マウントした PVC を read-only にするものでもありません。実際のアプリケーションでは適合する UID／GID と、書き込み可能な一時／キャッシュ／ソケット用パスが必要です。root 前提の汎用 nginx イメージは、これらのフィールドを追加するだけでは正常に動作しません。

**追加のスコープ付き Admission ルール:** 次の Kyverno 1.19.1 ValidatingPolicy は security-demo 内の通常コンテナ、init コンテナ、ephemeral コンテナをすべて確認します。privileged が欠落している場合は false として許可し、true なら拒否します。廃止されたインストールマニフェストではなく、現行の v1 ポリシー API を使います。

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

このルール1つで PSS プロファイル全体やイメージ検証を置き換えることはできません。privileged な CSI／監視エージェントや意図的な例外はプラットフォーム所有者の管理下に置き、デモポリシーを kube-system に一律適用しないでください。Gatekeeper を代替として使うなら、ConstraintTemplate、対応する constraint、検証済みの動作が必要です。

マニフェスト／スキーマと Kyverno CLI の実ケース6件で、省略／false、通常／init／ephemeral コンテナでの privileged、別 Namespace を確認しました。ephemeral コンテナのテストでは Pod の作成ではなく、合成した UPDATE オブジェクトを使っています。実際の Admission webhook や Pod のデプロイは行っていません。

参考資料: [Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/)、[Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)。

</details>

### 5. EKS ワークロードについて相互補完するセキュリティ上の証拠を得る方法はどれですか？

- A) 時折手作業でレビューするだけ
- B) AWS Config のチェックだけを使う
- C) GuardDuty だけを使う
- D) セキュリティ態勢の検出結果、監査ログ、ランタイムのカバレッジ、検証済みの対応経路を組み合わせる

<details>
<summary>回答を表示</summary>

**回答: D) セキュリティ態勢の検出結果、監査ログ、ランタイムのカバレッジ、検証済みの対応経路を組み合わせる**

**解説:**

| 証拠／制御 | 得られる情報と、それだけでは証明できないこと |
|---|---|
| Security Hub CSPM／AWS Config | 対応する設定コントロールと検出結果。Kubernetes 全体の監査や規制準拠を完全に保証するものではない |
| GuardDuty EKS Protection | 独立したストリームを使った Kubernetes 監査ログベースの脅威分析 |
| GuardDuty Runtime Monitoring | 対応ノード上のエージェントによるランタイムイベント。有効化済みというだけではカバレッジを証明しない |
| CloudTrail | AWS API アクティビティ。Kubernetes 監査ログやアプリケーションのデータアクセスログの代わりにはならない |
| Kubernetes 監査ログ | 監査ポリシー／レベルで選択されたリクエスト。すべてのワークロード操作／本文を含むわけではない |
| CloudWatch／インシデント経路 | ログ分析と運用担当者への通知。配信、保持、対応を検証する必要がある |

Security Hub CSPM の FSBP 標準は CIS Kubernetes Benchmark ではありません。対応する CIS AWS Foundations の制御も、CIS Kubernetes の完全な監査ではありません。該当するベンチマーク／バージョン、手動チェック、マネージドサービスの例外、実際のワークロード要件に必要な証拠を記録してください。

検出器、CSPM 標準、Config recorder、CloudTrail は、既存の組織／リージョンの所有権に従ってください。リージョンの検出器を重複作成したり、集中管理された設定を上書きしたり、準備済みのバケットポリシー、暗号化、イベントセレクター、保持期間なしに trail を開始したりしないでください。CloudTrail data event は既定の管理イベント範囲とは別です。このレビューではアカウントレベルの監視リソースを作成していません。

**EKS 固有の確認:** 元の章に示すとおり、意図したコントロールプレーンログの種類、有効化処理の完了、ログ到着を確認します。`eks-cluster-logging-enabled`（全種類、定期評価）と `eks-cluster-log-enabled`（選択した種類は任意、設定変更時評価）はどちらも有効な Config ルールです。`oldestVersionSupported` パラメーターを維持し、自動的に最新バージョンのカタログが選ばれるとは考えないでください。明示的な encryptionConfig コントロールの検出結果は、EKS 1.28 以降の API データに既定の envelope encryption がないことを意味しません。

GuardDuty の監査分析に、別途エクスポートした CloudWatch 監査ログは必要ありません。Runtime Monitoring では、対応するセキュリティエージェント／データエンドポイントと実際のカバレッジが必要です。現行の EKS 対応対象には EC2 と Auto Mode が含まれ、Fargate と Hybrid Nodes は含まれません。現行の RUNTIME_MONITORING 機能を使い、旧 EKS_RUNTIME_MONITORING からの移行を確認してください。EKS_AUDIT_LOGS を Runtime Monitoring と取り違えないでください。

**CSPM イベントルーティングの例:** 次を `security-event-pattern.json` として保存します。ASFF のうち、アクティブかつ HIGH／CRITICAL で、ワークフローステータスが NEW／NOTIFIED の検出結果を選択します。異なる OCSF イベントスキーマの「`Findings Imported V2`」には意図的に一致しません。

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

この合成イベントはパターン確認専用であり、実際の検出結果でも完全な ASFF インポートペイロードでもありません。`synthetic-security-event.json` として保存します。

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

承認済み AWS テストでは、`aws events test-event-pattern --event-pattern file://security-event-pattern.json --event file://synthetic-security-event.json --region us-west-2` が一致するはずです。LOW severity、RESOLVED／SUPPRESSED workflow、ARCHIVED 状態、フィールド欠落、V2 event type もテストしてください。これらはパターンに一致しないはずです。このレビューでは JSON／ソーススキーマを確認しましたが、EventBridge サービスによるマッチングや実際のイベント配信は確認していません。

現在の EventBridge ガイドにあるとおり、既存のレビュー済み EventBridge 実行ロールに、所有する SNS topic への publish 権限を付与して宛先設定に利用できます。所有済み ARN に置き換えて `security-event-targets.json` として保存します。

```json
[
  {
    "Id": "SecurityAlerts",
    "Arn": "arn:aws:sns:us-west-2:123456789012:eks-security-alerts",
    "RoleArn": "arn:aws:iam::123456789012:role/EventBridgeSecurityAlerts"
  }
]
```

ロールには正しい EventBridge trust と、最小権限の sns:Publish が必要です。適用される topic／key ポリシーと明示的な拒否も確認してください。実行ロールなしのターゲットを使う場合は、サポートされるリソースベースの権限経路を設定します。ターゲット JSON だけで権限が付与されたり、ルール、topic、ロール、subscription が作成されたりすることはありません。

`aws events put-targets --rule eks-security-alerts --targets file://security-event-targets.json --region us-west-2` を実行する前に、既存ルール／ターゲットの所有者を確認してください。コマンドの終了ステータスだけでなく、FailedEntryCount と FailedEntries を確認します。SNS subscription、暗号化権限、再試行／デッドレター動作を確認し、制御した end-to-end 配信テストを行ってください。この監査では通知を送信していません。

**監査ログの調査:** 実際の EKS ロググループで次の Logs Insights 例を使います。Kubernetes 監査レコードの JSON フィールド検出を前提に RBAC の変更リクエストに絞っています。responseStatus.code を見て、成功したリクエストと拒否されたリクエストを区別してください。

```text
fields @timestamp, verb, user.username, objectRef.resource, objectRef.namespace, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter verb in ["create", "update", "patch", "delete", "deletecollection"]
| filter objectRef.resource in ["roles", "rolebindings", "clusterroles", "clusterrolebindings"]
| sort @timestamp desc
| limit 100
```

クエリに依存する前に、サンプルレコードのフィールドとストリーム名を確認してください。関連する証拠を保持し、所有者／重要度／エスカレーションを定義して対応手順をテストします。ダッシュボードに検出結果があることやサービスが有効であることは、修復完了やコンプライアンス要件の達成を証明しません。

参考資料: [CSPM 標準](https://docs.aws.amazon.com/securityhub/latest/userguide/standards-view-manage.html)、[ASFF イベント](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-cwe-event-formats.html)、[V2 イベント](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-v2-cwe-event-formats.html)、[EventBridge ターゲット権限](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html)、[EKS 監査ログ](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)。

</details>

### 6. 集中的に管理する AWS アクセスとライフサイクル管理が必要なアプリケーション認証情報には、どの方法が適していますか？

- A) アクセス、ローテーション、再読み込みの計画なしに値を保存する
- B) 環境変数を暗号化の仕組みとみなす
- C) 適切な AWS シークレット／パラメータバックエンドを、スコープを限定した ID と明確な配信／ライフサイクル設計と組み合わせる
- D) 本番認証情報をイメージにハードコードする

<details>
<summary>回答を表示</summary>

**回答: C) 適切な AWS シークレット／パラメータバックエンドを、スコープを限定した ID と明確な配信／ライフサイクル設計と組み合わせる**

**解説:**

Secrets Manager と Parameter Store は AWS アクセス制御と監査を集約できますが、外部バックエンドを使うだけで安全になるわけではありません。ワークロード ID、最小権限、値の配信、再読み込みの制御も必要です。Secrets Manager は対応する認証情報について設定可能なローテーションをサポートします。Parameter Store には同じ組み込み認証情報ローテーションのワークフローはありません。SecureString パラメータの KMS 暗号化とバージョニングは、接続先のデータベース／サービス上の認証情報を変更することとは異なります。

EKS 1.28 以降では、Kubernetes API データはすでに既定の KMS v2 envelope encryption で暗号化されています。Secret マニフェスト内の base64 は暗号化ではなくエンコードにすぎず、API／Pod へのアクセスで値が露出する可能性があります。環境変数は値を渡す方法であり暗号化ではありません。Secret が変わっても、稼働中プロセスの環境変数は更新されません。

**所有者と配信方法を明確に選択する:** ESO は Kubernetes Secret を作成します。Secrets Store CSI Driver と ASCP はファイルをマウントし、オプションで Kubernetes Secret に同期できます。同じ Secret を両方のコントローラーに管理させないでください。ファイルのみを使う CSI 設計でもワークロード／ノードのアクセス制御が必要です。同期を有効にすると、Kubernetes API 上にも値のコピーが作られます。

**ASCP の例:** これはレビュー済み EKS 1.36 用の、新規に所有された Linux EC2 環境へのインストールです。状態が不明な既存クラスターへのロールアウトではありません。最初に既存のリリース／CSIDriver の所有権、ノード互換性、privileged なプラットフォームエージェントの Admission、ネットワークアクセス、スケジューリングを確認してください。Fargate では CSI ノード DaemonSet を実行できません。Hybrid／Auto Mode での利用には現在のプロバイダー／ノード要件があります。次のローカルレンダリングではそれらを検証していません。

個別に管理する CSI 1.6.1 driver では、次の `secrets-csi-values.yaml` 設定を使います。AWS token audience の両方、オプションの Secret 同期、ローテーションを明示的に構成します。

```yaml
tokenRequests:
- audience: sts.amazonaws.com
- audience: pods.eks.amazonaws.com
syncSecret:
  enabled: true
enableSecretRotation: true
rotationPollInterval: 2m
```

ASCP chart 3.1.3 は通常、driver を依存関係として含み、token audience を設定します。この例では driver を別途インストールするため、driver の二重導入を避けるよう、以下を `ascp-values.yaml` として保存します。

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

既存環境では所有者が定めたバージョン／CRD 更新手順を使ってください。新規インストール用のコマンドや、無関係な値を含む設定への部分的な `helm upgrade` を実行してはいけません。chart のバージョン固定とレンダリング成功だけでは、ノードプラグインとの互換性、接続性、シークレットアクセスは確認できません。

username／password フィールドを持つ、所有済みの Secrets Manager JSON シークレットと、そのシークレットだけに範囲を限定した `ASCPSecretReader` ロールを準備します。必要に応じてカスタマー管理キーの復号権限も付与してください。この IRSA trust は ServiceAccount の正確な subject を使います。OIDC issuer／provider とアカウントの値をすべて一貫して置き換えてください。

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

以下の Namespace、ServiceAccount、SecretProviderClass、Pod は、ファイル配信の例を構成します。実際のクラスターに適した PSS バージョンを選択してください。JMESPath はフィールドを alias に抽出し、`secretObjects.data.objectName` はマウントした alias を指定します。secretObjects.data 内の `property` フィールドはサポートされません。権限 0444 により、この非 root デモプロセスからファイルを読み取れます。実際のアプリケーションでは、Pod の作成／マウント権限を制限し、互換性のある UID／GID／ファイル権限を選択してください。

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

Pod はファイルの値を表示せず、ファイルが存在することだけを確認します。`automountServiceAccountToken: false` は Kubernetes API 用の自動トークンマウントを無効にしますが、CSI driver が明示的に要求するトークンは無効にしません。この IRSA 例の代わりに Pod Identity を使う場合は、ワークロード ServiceAccount に対応する agent／association を設定し、`usePodIdentity: "true"` を指定してください。IRSA annotation がその association を設定すると考えてはいけません。

オプションの csi-db-credentials Secret は、Pod がボリュームをマウントした後にのみ同期されます。そのライフサイクルは利用中の Pod に従い、すべての利用者を削除すると Secret も削除される場合があります。SecretProviderClass を作るだけでは Secret は生成されません。値を出力せずに SecretProviderClassPodStatus とコントローラー／ノードのイベントを確認してください。

Parameter Store では、所有するパラメータへの SSM 読み取り権限と SecureString に適切な KMS アクセス権限をプロバイダーに設定したうえで、objects の値に代わりに次の項目を含められます。これは objects の断片であり、完全な SecretProviderClass ではありません。

```yaml
- objectName: /training/app/config
  objectType: ssmparameter
  objectAlias: app_config
  filePermission: "0444"
```

**ESO を使う場合:** 元の章で準備した EKSSecretReader IRSA ロール／trust を、正確な eso-reader ServiceAccount に使います。ESO 2.10.0 と v1 CRD が所有者の手順でインストール済みの場合、次の設定は別の eso-db-credentials Secret を作成します。バックエンド ARN、Namespace、ロール、JSON のプロパティは実際に準備したシークレットを参照する必要があります。

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

Owner は対象 Secret を ExternalSecret に関連付けます。所有者を削除するとガベージコレクションが起きる場合があります。Retain が扱うのはバックエンドの消失であり、所有者の削除から保護するものではありません。ESO の serviceAccountRef JWT 方式は IRSA です。コントローラーの Pod Identity は別設計です。コントローラー ServiceAccount を関連付けて store の auth ブロックを省略します。ESO は serviceAccountRef で別の Pod Identity 関連付け済みアカウントになりすますことはできません。

**ローテーションと再読み込み:** CSI 1.6 以降のローテーションでは kubelet の RequiresRepublish 呼び出しを使います。requiresRepublish だけではローテーションは有効にならず、driver の enableSecretRotation フラグも必要です。ここでの2分間の rotationPollInterval は最低キャッシュ期間であり、エンドツーエンドの更新が必ず2分で完了する保証ではありません。実際のタイミングは kubelet の再公開に依存します。ESO の refresh interval は別の調整スケジュールです。アプリケーションは更新ファイルを再オープン／監視するか、制御されたロールアウトを実行する必要があります。subPath マウントと既存の環境変数は自動更新されません。

Secrets Manager の rotate-secret は既定で即時ローテーションを行います。--no-rotate-immediately を指定しても Lambda ローテーション関数をテストし、AWSPENDING を作成／削除することがあります。また、既存の頻度／日付ベースのスケジュールが実行される場合があります。これは無害なスケジュール確認や読み取り専用チェックではありません。実行前に対象認証情報の変更、有効期間の重複、アプリケーションの再読み込み、ロールバックを確認してください。

**シークレット値を含めない Terraform の例:** Terraform の sensitive は選択された表示出力を抑制するだけです。通常の secret_string／random_password の値は state に保存されることがあります。以下は既存の承認済み KMS キーを使い、シークレットのメタデータだけを管理します。既存のシークレットをこの設定で管理する場合は、先に所有者と調整して import／照合してください。

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

これはシークレットのバージョン／値を作成せず、ローテーションも有効にしません。初期値はハードコードした Terraform 文字列や平文のコマンド引数ではなく、承認済みのシークレット入力手順で登録してください。メタデータしか扱わない想定でも state と plan を保護します。prevent_destroy は Terraform の設定上のガードであり、サービス上で不可逆な保護ではありません。リソース設定を削除したり Terraform の外で操作したりすると、保護の前提が変わります。

検証では、Kubernetes のネイティブスキーマと公開済み SecretProviderClass／ESO CRD、公開済み chart の checksum、レンダリングした CSI／ASCP オブジェクト22件、合成データを使った実際の JMESPath 投影を確認しました。Swagger スキーマのチェックでは、生成された null の creationTimestamp フィールドだけを除外しました。Terraform fmt は通過しましたが、init／plan／apply は実行していません。AWS シークレットの取得、マウント、同期、ローテーション、アプリケーションの再読み込みは行っていません。

参考資料: [ASCP の設定](https://github.com/aws/secrets-store-csi-driver-provider-aws)、[CSI 1.6.1](https://github.com/kubernetes-sigs/secrets-store-csi-driver/releases/tag/v1.6.1)、[CSI Secret 同期](https://secrets-store-csi-driver.sigs.k8s.io/topics/sync-as-kubernetes-secret)、[CSI ローテーション](https://secrets-store-csi-driver.sigs.k8s.io/topics/secret-auto-rotation)、[ESO AWS 認証](https://github.com/external-secrets/external-secrets/blob/v2.10.0/docs/provider/aws-access.md)、[EKS envelope encryption](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html)、[Secrets Manager ローテーション](https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/rotate-secret.html)。

</details>

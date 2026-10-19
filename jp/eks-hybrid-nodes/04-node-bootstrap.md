# ノードのブートストラップ

< [前へ: 制限付きインターネット環境の構成](./03-airgap-setup.md) | [目次](./README.md) | [次へ: GPU 統合](./05-gpu-integration.md) >

> **サポート対象バージョン**: EKS Hybrid Nodes。nodeadm v1.0.20 のソースを確認済みです。対象クラスターに対応する、サポート対象の OS、Kubernetes、CNI の組み合わせを選んでください。
> **最終更新**: 2026年9月12日

この章では、準備済みのオンプレミスホストを EKS に接続します。ソフトウェアのインストール、AWS アイデンティティ、初期化、ワークロードの稼働確認を分けて説明します。例を実行するには、対象クラスターとホストの特定、および記載した変更に対する運用担当者の承認が必要です。ローカルでの検証は、本番ネットワーク、OS イメージ、PKI、ワークロードがテスト済みであることを意味しません。

## ブートストラップの流れ

1. [前提条件](./01-prerequisites.md) と [ネットワーク構成](./02-network-configuration.md) に従い、サポート対象の OS/ランタイム、一意なホスト ID、時刻同期、ルート、DNS、ファイアウォールルールを準備します。
2. **Hybrid Nodes 用 IAM ロール**、SSM または IAM Roles Anywhere のプロバイダー、および `HYBRID_LINUX` タイプのクラスターアクセスエントリを用意します。一般的な SSM 管理ロールだけでは不十分です。
3. Hybrid nodeadm のリリースを確認してから、ホスト上または管理された OS イメージのビルド工程で依存関係をインストールします。
4. 認証情報プロバイダーを 1 つだけ指定した、ノードごとの保護された NodeConfig を配布します。必要に応じてプロキシとレジストリの信頼設定を行います。
5. 対象ホストで `nodeadm config check` を実行し、続けて `nodeadm init` を実行します。
6. サポート対象の Hybrid CNI と必要なアドオンを構成します。Node が登録されても `NotReady` のままの場合があります。
7. Node の ID、Ready 条件、CNI/DNS、認証情報の更新、制限付きワークロードを確認してから、サービスに受け入れます。

## nodeadm と依存関係のインストール

Hybrid nodeadm は EC2 用の `amazon-eks-ami` インストーラーではなく、**`aws/eks-hybrid`** から入手します。新規の SSM インストール/アップグレードには **nodeadm 1.0.19 以降**が必要です。それ以前のバージョンには古い SSM 署名キーが含まれます。このレビューではリリース済みの **v1.0.20 ソース**を確認しました。

承認済みリリースを HTTPS 検証付きでダウンロードし、root として実行する前に、独立して承認された記録とダイジェストを照合してください。変更可能な `latest` ダウンロードで `/usr/local/bin/nodeadm` を無条件に置き換えないでください。[制限付きインターネット環境の章](./03-airgap-setup.md) では、イメージ準備と、確認したリリースの private-manifest 用フラグを説明しています。この環境では公式アーティファクトホストの TLS ホスト名検証に失敗したため、今回の監査では nodeadm バイナリを取得も実行もしていません。

```bash
# Target host/image builder: installs software. Choose exactly one provider.
set -euo pipefail
: "${KUBERNETES_VERSION:?Approved cluster-compatible version}"
: "${CREDENTIAL_PROVIDER:?ssm or iam-ra}" "${REGION:?}"
: "${CONTAINERD_SOURCE:?distro, docker or none for this OS}"
case "$CREDENTIAL_PROVIDER" in ssm|iam-ra) ;; *) exit 1 ;; esac
case "$CONTAINERD_SOURCE" in distro|docker|none) ;; *) exit 1 ;; esac
sudo nodeadm install "$KUBERNETES_VERSION" \
  --credential-provider "$CREDENTIAL_PROVIDER" \
  --containerd-source "$CONTAINERD_SOURCE" --region "$REGION" --timeout 20m
```

新しい Node には、コントロールプレーンと同じマイナーバージョンを優先してください。サポートされる kubelet のバージョン差は互換性の許容範囲であり、サポート対象外の古い EKS バージョンを選ぶ理由にはなりません。kubelet は API server より新しいバージョンにしてはいけません。上流のバージョン差ポリシーだけでなく、EKS と CNI のサポート状況も確認してください。

RHEL では `distro` はサポートされません。文書化された Docker パッケージソースを使うか、互換性のあるランタイムが事前インストールされた状態で `none` を指定してください。AL2023 では `docker` はサポートされません。`none` は containerd のインストールを省略します。Private モードも OS パッケージのインストールを省略するため、不足しているランタイム依存関係を補うものではありません。

| コンポーネント | 文書化されたインストール先 |
|---|---|
| kubelet | `/usr/bin/kubelet` |
| kubectl | `/usr/local/bin/kubectl` |
| ECR 認証情報プロバイダー | `/etc/eks/image-credential-provider/ecr-credential-provider` |
| AWS IAM authenticator / 署名ヘルパー | `/usr/local/bin/aws-iam-authenticator` / `/usr/local/bin/aws_signing_helper` |
| SSM セットアップ CLI | `/opt/ssm/ssm-setup-cli` |
| SSM Agent | Ubuntu snap: `/snap/amazon-ssm-agent/current/amazon-ssm-agent`; AL2023/RHEL: `/usr/bin/amazon-ssm-agent` |
| containerd | Ubuntu/AL2023: `/usr/bin/containerd`; RHEL の文書: `/bin/containerd` |
| nodeadm の追跡データ | `/opt/nodeadm/tracker` |

`nodeadm install` は署名済みセットアップ CLI を通じて SSM agent をインストール、構成します。**SSM への登録は `init` 中に行われます**。これは、手作業で `dpkg` を実行してから互換性のない別の nodeadm インストーラーを使う手順ではありません。

## NodeConfig と認証情報

### SSM

準備済み Hybrid ロールに対するクラスター名/Region と有効な activation code/ID を指定します。

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-hybrid-cluster
    region: ap-northeast-2
  hybrid:
    ssm:
      activationCode: REPLACE_WITH_ACTIVATION_CODE
      activationId: REPLACE_WITH_ACTIVATION_ID
  kubelet:
    config:
      maxPods: 110
      shutdownGracePeriod: 30s
      shutdownGracePeriodCriticalPods: 10s
    flags:
      - --node-labels=workload.example.com/location=onprem
```

保護対象の設定ファイルは入力テンプレートであり、秘密情報を含む状態でコミットしてはいけません。root 所有、モード `0600` とし、値をログやシェル履歴に出さずに渡してください。クラスターの検出では Hybrid ロールの EKS 権限を使って API endpoint と CA を取得します。base64 で符号化された CA フィールドに生の PEM ブロックを入れても、API が要求する表現の代わりにはなりません。

`maxPods` とシャットダウン時間は計画用の例であり、容量を保証しません。CNI の割り当て、予約済み IP、リソース、ワークロードの終了要件を確認してください。任意の `NoSchedule` taint を設定する場合は、対象ワークロード/CNI に対応する toleration が必要です。必要な agent やアプリケーションのスケジュールを妨げる既定 taint を安易に追加しないでください。

認証情報の所有者を通じてのみ activation を作成し、準備済み Hybrid ロール、正しい Region、明示的な有効期限、上限付きの登録数を指定してください。応答は activation code を表示するのではなく、アクセスを制限したファイルに保存します。

```bash
# AWS write: owner-approved activation for one new host.
set -euo pipefail
umask 077
: "${REGION:?}" "${HYBRID_ROLE_NAME:?Prepared Hybrid Nodes IAM role name}"
: "${ACTIVATION_EXPIRY:?Future UTC timestamp within SSM service limits}"
test ! -e activation.json
aws ssm create-activation --region "$REGION" \
  --iam-role "$HYBRID_ROLE_NAME" --registration-limit 1 \
  --expiration-date "$ACTIVATION_EXPIRY" \
  --default-instance-name eks-hybrid-node > activation.json
```

リクエストが失敗したか結果不明の場合、無条件に再作成してはいけません。認証情報の所有者と状態を照合してください。SSM は生成された `mi-*` 管理インスタンス ID を Node 名として使います。通常の再起動では SSM 登録を再利用し、一時認証情報を更新します。再登録には、登録可能数が残っている有効な activation が必要です。有効期限と登録数の両方を確認してください。

### IAM Roles Anywhere

[前提条件](./01-prerequisites.md) で準備した trust anchor、有効な profile、Hybrid ロール、ノードごとの証明書/秘密鍵を使います。この章を実行するたびに trust anchor/profile を新たに作成しないでください。

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-hybrid-cluster
    region: ap-northeast-2
  hybrid:
    iamRolesAnywhere:
      nodeName: hybrid-node-001
      trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:111122223333:trust-anchor/REPLACE_ID
      profileArn: arn:aws:rolesanywhere:ap-northeast-2:111122223333:profile/REPLACE_ID
      roleArn: arn:aws:iam::111122223333:role/EKSHybridNodeRole
      certificatePath: /etc/iam/pki/server.pem
      privateKeyPath: /etc/iam/pki/server.key
```

パスは例であり、1 つの証明書を複数のマシンで使い回す指示ではありません。`nodeName` をロールの trust policy が参照する証明書属性に結び付けてください。一般的な CN 条件を使う場合は両者を一致させる必要があります。Node 名は Kubernetes の命名規則を満たし、64 文字以下でなければなりません。profile では **`acceptRoleSessionName: true`** を有効にしてください。

ロールの最大値を 12 時間に設定しただけで、session duration が延びるわけではありません。実際に要求する/profile の期間は、ロールの `MaxSessionDuration` 以下である必要があります。同じ値は許可されます。セキュリティと可用性の要件に応じて期間を選び、認証情報が更新されることを確認してください。静的な IAM ユーザーアクセスキーは、Hybrid nodeadm がサポートする 3 つ目の認証情報プロバイダーではありません。

## プライベートレジストリの信頼設定

社内レジストリを使う場合は、その管理者を通じて CA のフィンガープリントと証明書のホスト名を確認してください。適切な場合はレジストリ単位の信頼設定を優先します。提示された証明書を無条件にシステム全体へインストールしたり、ホスト名検証を無効にしたりしないでください。

承認済みレジストリ向け `hosts.toml` の例です。

```toml
# /etc/containerd/certs.d/registry.internal.example.com/hosts.toml
server = "https://registry.internal.example.com"

[host."https://registry.internal.example.com"]
  capabilities = ["pull", "resolve"]
  ca = "/etc/containerd/certs.d/registry.internal.example.com/ca.crt"
```

対応する、レビュー済みの CA ファイルを各 Node に配置してください。containerd 1.x ではレジストリの `config_path` は `plugins."io.containerd.grpc.v1.cri".registry` の下に置きます。containerd 2.x/config version 3 では `plugins."io.containerd.cri.v1.images".registry` の下です。nodeadm が生成した `/etc/containerd/config.toml` を確認し、実際に導入したランタイムの節を使ってください。非推奨のインライン `configs/auth` と `config_path` の手順を混在させたり、レジストリのパスワードを NodeConfig に入れたりしないでください。

組織でシステム全体の CA 信頼が必要な場合、Ubuntu では `/usr/local/share/ca-certificates/` と `update-ca-certificates` を使います。RHEL/AL2023 では `/etc/pki/ca-trust/source/anchors/` と `update-ca-trust extract` を使います。RHEL の例で Ubuntu のパスを参照しないでください。通常の ECR 証明書は公開 CA で信頼されますが、OS に正常な CA bundle が必要です。レジストリの信頼設定と認証は別の仕組みです。

## 初期化と検証

```bash
# Identified target host; init changes local configuration and joins EKS.
set -euo pipefail
sudo nodeadm config check --config-source file:///etc/eks/nodeconfig.yaml
sudo nodeadm init --config-source file:///etc/eks/nodeconfig.yaml
```

Private-manifest を使ったインストールでは、[制限付きインターネット環境の構成](./03-airgap-setup.md) に従い、`init` に承認済みの `--manifest-override` と `--private-mode` を渡してください。プロキシ設定が nodeadm と daemon の実プロセスに届くようにします。`config check` はローカルの設定検査であり、接続全体の試験ではありません。

**クラスター管理者の**端末から、使用する kubeconfig context と、想定した Node 名（SSM の `mi-*`、または承認済みの IAM Roles Anywhere 名）を確認してください。

```bash
set -euo pipefail
umask 077
: "${KUBECONFIG:?}" "${CONTEXT:?}" "${EXPECTED_NODE_NAME:?}"
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  get node "$EXPECTED_NODE_NAME" -o json > node-registration.json
jq -e '.metadata.labels["eks.amazonaws.com/compute-type"] == "hybrid"
  and (.metadata.uid | type == "string" and length > 0)' node-registration.json
expected_uid=$(jq -er '.metadata.uid' node-registration.json)
# After CNI and required add-ons are ready:
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" wait \
  --for=condition=Ready "node/$EXPECTED_NODE_NAME" --timeout=5m
observed_uid=$(kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  get node "$EXPECTED_NODE_NAME" -o jsonpath='{.metadata.uid}')
test "$observed_uid" = "$expected_uid"
```

Node UID を記録し、provider/addresses を対象として特定した物理/仮想ホストと照合してください。Ready 条件だけでは不十分です。DNS、イメージ取得、接続性、認証情報の更新、必要なワークロードも確認してください。以前の `v1.31.0` 出力は説明用の過去の出力であり、今回新たに登録して測定した結果ではありません。

## 事前インストール済みホストの systemd 自動化

管理されたビルド/インストール工程で `nodeadm install` を使ってソフトウェアを準備してください。以下の自動化は**初期化だけ**を実行し、マシン ID、承認済み nodeadm バイナリ、NodeConfig、任意の private manifest にひも付けた記録を保存します。状態の変更や一部だけ初期化された状態を検知した場合、黙って登録を繰り返さず停止します。登録状態、マシン ID、鍵、この状態ディレクトリを他の Node に複製しないでください。

root 所有の `/etc/eks/bootstrap.env` の例（モード `0600`）:

```text
NODECONFIG_PATH=/etc/eks/nodeconfig.yaml
APPROVED_NODEADM_SHA256=REPLACE_WITH_APPROVED_64_HEX_DIGEST
# Only for the reviewed private-manifest path:
# LOCAL_MANIFEST=/etc/eks/manifest.json
```

root 所有の次のスクリプトを `/usr/local/bin/eks-hybrid-bootstrap.sh` に保存します。親ディレクトリとファイルはホスト管理者が保護してください。これは悪意ある root から保護する仕組みではありません。

```bash
#!/usr/bin/env bash
# Initialize one preinstalled, uniquely identified host. Run as root.
set -euo pipefail
umask 077
[[ "$EUID" -eq 0 ]]
: "${NODECONFIG_PATH:?Absolute per-node config path}"
: "${APPROVED_NODEADM_SHA256:?Hash from the approved binary record}"
[[ "$NODECONFIG_PATH" = /* ]]
[[ "$APPROVED_NODEADM_SHA256" =~ ^[0-9a-f]{64}$ ]]
NODEADM=/usr/local/bin/nodeadm
STATE=/var/lib/eks-hybrid-bootstrap

private_file() {
  local path=$1 owner mode
  [[ -f "$path" && ! -L "$path" ]]
  owner=$(stat -c '%u' "$path")
  mode=$(stat -c '%a' "$path")
  [[ "$owner" == 0 && "$mode" == 600 ]]
}

private_file "$NODECONFIG_PATH"
test -s /etc/machine-id
test -s /opt/nodeadm/tracker
test -x "$NODEADM"
actual=$(sha256sum "$NODEADM")
[[ "${actual%% *}" == "$APPROVED_NODEADM_SHA256" ]]
if [[ -e /var/lib/eks/.nodeadm-installed || -e /var/lib/eks/.nodeadm-initialized ]]; then
  echo 'Legacy markers found: review existing installation and migrate state manually.' >&2
  exit 1
fi
[[ ! -L "$STATE" ]]
mkdir -p -m 700 "$STATE"
[[ "$(stat -c '%u:%a' "$STATE")" == 0:700 ]]
exec 9>"$STATE/lock"
flock -n 9

args=(--config-source "file://$NODECONFIG_PATH")
fingerprint_inputs=(/etc/machine-id "$NODEADM" "$NODECONFIG_PATH")
if [[ -n "${LOCAL_MANIFEST:-}" ]]; then
  [[ "$LOCAL_MANIFEST" = /* ]]
  private_file "$LOCAL_MANIFEST"
  fingerprint_inputs+=("$LOCAL_MANIFEST")
  args+=(--manifest-override "file://$LOCAL_MANIFEST" --private-mode)
fi
fingerprint=$(sha256sum "${fingerprint_inputs[@]}" | sha256sum)
fingerprint=${fingerprint%% *}
if [[ -e "$STATE/state" ]]; then
  private_file "$STATE/state"
  if [[ "$(cat "$STATE/state")" == "$fingerprint init-command-completed" ]]; then
    echo 'Matching initialization record; verify current Node readiness separately.'
    exit 0
  fi
  echo 'Changed identity/config or incomplete initialization: manual recovery required.' >&2
  exit 1
fi

"$NODEADM" config check --config-source "file://$NODECONFIG_PATH"
printf '%s started\n' "$fingerprint" > "$STATE/state.new"
mv "$STATE/state.new" "$STATE/state"
# Failure/interruption retains started state and prevents an automatic retry.
"$NODEADM" init "${args[@]}"
systemctl is-active --quiet containerd
systemctl is-active --quiet kubelet
printf '%s init-command-completed\n' "$fingerprint" > "$STATE/state.new"
mv "$STATE/state.new" "$STATE/state"
echo 'Init command completed; cluster registration/CNI/readiness still require verification.'
```

この状態記録は、init コマンドが完了し、その時点で 2 つのローカルサービスが active だったことを示します。**Kubernetes Node が Ready であることを意味しません**。失敗時には `started` の記録が残るため、運用担当者が状態を照合する前に、実際のホスト/SSM/クラスターの状態を調べてください。サービスのタイムアウトやコマンドの中断だけでは、登録が行われなかったとは判断できません。

```ini
# /etc/systemd/system/eks-hybrid-bootstrap.service
[Unit]
Description=Initialize one prepared EKS Hybrid Node
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
EnvironmentFile=/etc/eks/bootstrap.env
ExecStart=/usr/local/bin/eks-hybrid-bootstrap.sh
TimeoutStartSec=10min
RemainAfterExit=true
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

ホスト構成の管理者を通じてインストール/有効化してください。`network-online.target` はネットワーク管理サービスの待機機能に基づき起動順序を定めますが、DNS、VPN、EKS、認証情報サービスへの到達性を保証しません。`RemainAfterExit` が記録するのはサービス状態であり、Node の健全性ではありません。`EnvironmentFile` は systemd が解析するファイルであり、スクリプトが shell の `source` で実行するものではありません。

marker だけを使う既存インストールからの移行には、明示的な手順が必要です。`.nodeadm-installed` / `.nodeadm-initialized` を削除して再起動するだけではリセットになりません。認証情報ファイルの有効化など承認済みの構成変更は、文書化されたメンテナンス/init 手順に従い、自動化の記録もその後に照合してください。

通常の再起動では、構成済みの kubelet/認証情報サービスが再開します。Kubernetes Node オブジェクトを削除しても、SSM の登録解除や kubelet の停止にはなりません。稼働中で認可された kubelet は Node を再作成できます。`delete node` をホスト廃止の手段として使わず、障害のあったすべてのホストが必ず再参加すると想定しないでください。

## Cilium CNI

AWS は現在、Hybrid Nodes 向けに保守する **Cilium 1.17.x と 1.18.x** のビルドをサポートしています。公開例には `oci://public.ecr.aws/eks/cilium/cilium` の `1.17.9-0` と `1.18.3-0` があります。任意の新しい上流 chart を選ぶ推奨ではありません。

現在の AWS CNI ページでは、カーネル要件のため **Ubuntu 20.04 と RHEL 8 は Cilium v1.18.3 の対象外**と明記されています。カーネルを変更しただけで AWS のサポート対象になると主張しないでください。文書化された対応表の範囲内で OS/CNI を選択します。

Calico の例は `aws-samples/eks-hybrid-examples` に移動されました。これは Calico プロジェクトの非推奨を意味せず、既存のあらゆる Calico 配置が今後も動作する保証でもありません。現行の AWS CNI サポートページには、AWS が保守する Cilium ビルドとサポート対象の機能が記載されています。

### インストール値

この IPv4 cluster-pool の例は、Node/VPC/Service ネットワークと重ならない、レビュー済みのリモート Pod ネットワーク `10.85.0.0/16` を前提とします。初回インストールの**前に**、クラスターで承認済みの値に置き換えてください。

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
            - key: eks.amazonaws.com/compute-type
              operator: In
              values: [hybrid]
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4MaskSize: 25
    clusterPoolIPv4PodCIDRList: [10.85.0.0/16]
loadBalancer:
  serviceTopology: true
operator:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
          - matchExpressions:
              - key: eks.amazonaws.com/compute-type
                operator: In
                values: [hybrid]
  unmanagedPodWatcher:
    restart: false
envoy:
  enabled: false
kubeProxyReplacement: "false"
preflight:
  nodeSelector:
    eks.amazonaws.com/compute-type: hybrid
```

事前チェック用 selector は agent affinity とは別です。`/25` には 128 アドレスがありますが、Cilium cluster-pool はそのうち 2 つを予約するため、Pod に 128 個のアドレスを使用できる保証にはなりません。kubelet の `maxPods`、hostNetwork Pod、その他の制約も合わせて調整してください。

既存の pool entry や `clusterPoolIPv4MaskSize` を変更しないでください。Cilium が文書化する拡張方法は、新しい pool entry の**追加**です。事前に EKS remote networks、ルーティング/BGP、アドレス重複、容量をまとめて確認します。「リスト全体を拡張できない」という説明は強すぎます。

```bash
# Cluster write; requires approved context, values and supported chart.
set -euo pipefail
: "${KUBECONFIG:?}" "${CONTEXT:?}" "${CILIUM_VERSION:?Approved AWS chart version}"
helm install cilium oci://public.ecr.aws/eks/cilium/cilium \
  --version "$CILIUM_VERSION" --namespace kube-system \
  --kubeconfig "$KUBECONFIG" --kube-context "$CONTEXT" \
  --values cilium-values.yaml --wait --timeout 10m
```

すべての対象 Hybrid Node 上の Cilium agent と operator、Node の Ready 状態、ノード間通信を確認してください。affinity によりこのインストールは Hybrid Node に限定され、クラウド Node のネットワークは既存の controller が引き続き管理します。kube-proxy を置き換える設計には、独自の API 到達性と移行計画が必要です。同じ Node 上で kube-proxy と競合する設定を残さないでください。

### アップグレードと削除の境界

Cilium をアップグレードする前に、現在の値/manifest と明示的な Helm revision を保存し、バージョン固有のアップグレードノートを確認し、承認済みの値で候補 chart を render してください。Hybrid Node に対象を絞った**別個の事前検証リリース**を `preflight.enabled=true`、`agent=false`、`operator.enabled=false` で実行します。DaemonSet の全対象 Node への展開と validation Deployment の Ready の**両方**を待ちます。事前検証リリースを作っただけでは検査結果になりません。

検査に合格したら、その事前検証リリースだけを削除します。レビュー済みの保存値と適切な `upgradeCompatibility` 設定でアップグレードします。マイナーバージョンを越えて古い設定を `--reuse-values` で無条件に引き継がないでください。ロールバックには、明示的に確認した revision と CNI 状態/CRD 互換性の確認が必要です。データプレーンが必ず復旧する保証ではありません。

CNI の削除は、サービスに影響する廃止/移行作業です。ワークロードを退避し、どの Node、ポリシー、CR がまだ Cilium に依存しているか確認してください。共有クラスターで `kubectl get crds | grep cilium | xargs kubectl delete` を実行してはいけません。Helm uninstall だけでホストのルート、インターフェイス、BPF 状態がすべて削除されるとは限りません。対象 Node を退避させた上で、バージョン固有の CNI cleanup 手順に従い、パスを削除する前にマウント中の領域と保持データを確認してください。

## Bottlerocket は異なるブートストラップ契約を使用

AWS は、サポート対象の x86_64 Kubernetes variant と前提条件を備えた VMware Bottlerocket variant を **1.37.0 以降**でサポートしています。これは nodeadm を**実行しません**。AWS ガイドでは Kubernetes/AWS 設定に加え、**`eks-hybrid-setup` bootstrap container** を構成します。以前の `[settings.hybrid.ssm]` と `[settings.hybrid.iam-roles-anywhere]` の例は、文書化された設定仕様ではありません。

選択したプロバイダーの設定一式は、[Bottlerocket での Hybrid Node 接続](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-bottlerocket.html) を参照してください。一般的な項目は次のとおりです。

```toml
# Common fragment only: combine with the provider-specific settings from AWS.
[settings.kubernetes]
cluster-name = "my-hybrid-cluster"
api-server = "https://REPLACE_WITH_CLUSTER_ENDPOINT"
cluster-certificate = "REPLACE_WITH_BASE64_CLUSTER_CA"
hostname-override = "hybrid-node-001"
provider-id = "eks-hybrid:///ap-northeast-2/my-hybrid-cluster/hybrid-node-001"
authentication-mode = "aws"
cloud-provider = ""
server-tls-bootstrap = true

[settings.network]
hostname = "hybrid-node-001"

[settings.aws]
region = "ap-northeast-2"

[settings.kubernetes.node-labels]
"eks.amazonaws.com/compute-type" = "hybrid"

[settings.bootstrap-containers.eks-hybrid-setup]
mode = "always"
user-data = "REPLACE_WITH_BASE64_PROVIDER_BOOTSTRAP_INPUT"
```

この断片だけでは起動可能な設定になりません。SSM provider は `eks-hybrid-ssm-setup` に activation/Region の入力を渡し、登録後の Node 名は `mi-*` に変わります。IAM Roles Anywhere provider は `eks-hybrid-iam-ra-setup` に証明書/鍵の入力と AWS credential-process の設定を渡し、role-session-name を証明書ポリシーに結び付けます。文書化された ECR provider とプロバイダー固有の Node label/設定も含めてください。

Base64 は符号化であり、暗号化ではありません。provider bootstrap data に activation secret や秘密鍵が含まれる場合があります。VM の設定、guestinfo、管理権限、診断情報の出力を保護し、公開リポジトリやログに入れないでください。admin-container 経由の SSH は任意ですが、別途認可が必要です。登録済み VM をクリーンなテンプレートとして複製しないでください。

承認済みの**電源 OFF 状態の新規プロビジョニング済み VM**を、初回起動の前に構成してください。AWS ガイドでは base64 で符号化した `settings.toml` と `guestinfo.userdata.encoding=base64` を使います。通常の base64 を `gzip+base64` と表記しないでください。プロビジョニング前に、実際の govc/VMware バージョン、datastore、ネットワーク、テンプレート所有者、秘密情報の配布方法を確認してください。この監査では VMware のデプロイを実行していません。

## アドオン配置と Pod Identity

API server のトラフィックが、実際の webhook/aggregated API listener に到達するようにしてください。Hybrid Pod CIDR に到達できない場合、**webhook server/operator** を到達可能なクラウド Node に配置するか、サポートされる範囲で適切な hostNetwork 設計を検証します。CloudWatch/ADOT agent やアプリケーションのすべての Pod をクラウド側で動かす必要があるという意味ではありません。

クラウド Node に配置する場合は、レビュー済みの明示的な Node label/affinity を使い、容量と taint を確認してください。`NotIn [hybrid]` は label のない Node にも一致するため、承認済み EC2 の配置を証明しません。

クラウド/Hybrid 混在クラスターでは、AWS は CoreDNS replica を両側に少なくとも 1 つずつ置くことを推奨しています。replica を 4 つにし、soft spread を使っても、各側にちょうど 2 つずつ配置される保証はありません。[ネットワーク構成](./02-network-configuration.md) にある配置と Service Traffic Distribution の手順を適用し、結果を確認してください。

| Node OS | Pod Identity の準備 |
|---|---|
| Ubuntu/RHEL/AL2023 | `spec.hybrid.enableCredentialsFile: true` としてから、文書化された `nodeadm init` を実行。agent 設定で `daemonsets.hybrid.create` を有効にする |
| Bottlerocket | OS **1.39.0 以降**。provider bootstrap command に `--enable-credentials-file=true` を指定し、`daemonsets.hybrid-bottlerocket.create` を有効にする |

互換性の最低バージョンは Bottlerocket 以外の agent が **v1.3.3-eksbuild.1**、Bottlerocket が **v1.3.7-eksbuild.2** です。これは現行のインストール先を示すものではありません。クラスターに対応する現在のアドオンバージョンと設定 schema を選んでください。マウントされる一時認証情報のパスは異なり、`/eks-hybrid/.aws/credentials` と Bottlerocket の `/var/eks-hybrid/.aws/credentials` です。

Private 環境では `eks-auth` service への経路、Node role の `eks-auth:AssumeRoleForPodIdentity` 権限、各ワークロード用の Pod Identity association/trust/permission が必要です。agent をインストールしただけでは不十分です。必要な DaemonSet 設定はアドオン所有者を通じてマージしてください。既存アドオンを無条件の `create-addon` で上書きしないでください。

## アップグレード、復旧、削除

古い Node を退避する前に、置換容量を追加し、**完全に初期化して検証**してください。新しいホストにバイナリをインストールしただけではクラスター容量は増えません。DNS の可用性を維持してください。「回復性」を理由に、既存の CoreDNS 4 replica を確認せず 2 つに減らさないでください。

特定した古い Node について context、Node UID、ホスト対応、ワークロード/データの所有者を確認します。cordon し、timeout を指定して drain し、PDB/eviction のエラーがあれば停止してください。`--delete-emptydir-data` はローカルの emptyDir データ消失を明示的に許可する指定であり、既定の安全オプションではありません。管理外 Pod、ローカル永続データ、DaemonSet は個別に扱う必要があります。drain の停止を成功扱いにするため、`--force` を使ったり eviction を無効にしたりしないでください。

インプレース更新では、退避させたホストで文書化された `nodeadm upgrade` を実行します。その後、Node identity、ソフトウェアバージョン、Ready/CNI/DNS、ワークロード動作を検証してから uncordon してください。これは中断を伴います。「予備容量がない」ことは安全性の根拠にはなりません。

廃止時は自動 bootstrap/rejoin 経路を止め、文書化された nodeadm の削除とプロバイダー登録解除を完了してから、該当 Node object を削除し、残る CNI リソースを所有者と照合します。復旧に必要な証跡は非公開の場所に保持してください。

`nodeadm uninstall` は `kubectl drain` や `kubectl delete node` と同じではありません。通常、ワークロード Pod が残っていると処理を拒否します。すべての CNI/アドオン資産を削除するわけでもありません。**v1.0.9 以降、文書化された force/skip uninstall 経路でも、ホストのファイルシステムを露出するマウント済みパスがあるため `/var/lib/kubelet` は削除しません**。`--force` は既定の CNI/Kubernetes パスをさらに削除しますが、確認を省略してすべてを消す汎用フラグではありません。手動削除の前にマウントとデータを調査してください。

削除後に承認された再インストールを行う場合は、有効な認証情報で **install → config check → init** を実行し、自動化記録を照合してください。認証エラー、既存 profile、一部だけ完了した init を、稼働中 Node の uninstall を正当化する理由にしてはいけません。

## トラブルシューティング

| 観測された状態 | 状態を変更する前に調査する内容 |
|---|---|
| 古い nodeadm で SSM installer の署名エラー | 承認済み nodeadm が 1.0.19 以降か確認。署名検証を回避しない |
| package manager/ダウンロード失敗 | 実際の repository 到達性、proxy、CA trust、package lock、サポート OS/runtime、エラー内容。`dnf update` は診断ではなくシステムアップグレード |
| timeout | 失敗した工程と到達性を特定。timeout を延ばすだけでは解決しない |
| Node IP が remote networks の範囲外 | 実際に設定された Node IP と EKS remote-node CIDR |
| API に到達できない / Unauthorized | DNS/route/443 と戻り経路、想定する Hybrid role、trust/認証情報の有効性、`HYBRID_LINUX` access entry |
| NotReady | CNI/agent log と選択した datapath port、runtime、disk/resource 状態。すべてのケースで CNI 不足とは限らない |
| image pull または x509 error | 正確な image/auth 経路、ECR API/DKR/S3、private-registry CA と hostname。TLS 検証は有効のままにする |
| activation / token の期限切れ | activation の有効期限/残数/Region と、稼働中 agent の認証情報更新、時刻同期、AWS 到達性を切り分ける。再起動で必ず直るわけではない |
| Hybrid profile が既存 / init が一部完了 | 現在の nodeadm/provider 状態と対象クラスターを調べ、証跡を保持する。自動で uninstall しない |

```bash
# Private diagnostic output on the identified node; no nonexistent nodeadm status.
sudo systemctl status kubelet containerd --no-pager
sudo journalctl -u kubelet --since '-15 min' --lines 200 --no-pager
sudo nodeadm debug --config-source file:///etc/eks/nodeconfig.yaml
```

`nodeadm debug` は AWS/クラスターへの読み取りと認証情報の検査を行います。出力を非公開にし、共有前に秘密情報を伏せてください。`sudo aws sts get-caller-identity` は別の root/admin 認証情報チェーンを使う場合があり、kubelet が使う認証情報を証明するものではありません。TLS 検証に `curl -k` を使わないでください。サーバーの CA 信頼と kubelet client certificate の承認/発行は別の仕組みです。

## 主な参考資料

- [Hybrid nodeadm のコマンド、ファイル配置、削除時の動作](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [Hybrid の認証情報](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
- [IAM Roles Anywhere CreateSession の期間](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/authentication-create-session.html)
- [SSM CreateActivation](https://docs.aws.amazon.com/systems-manager/latest/APIReference/API_CreateActivation.html)
- [AWS Hybrid CNI のサポートとライフサイクル](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Cilium cluster-pool の拡張](https://github.com/cilium/cilium/blob/v1.18.3/Documentation/network/concepts/ipam/cluster-pool.rst)
- [Bottlerocket Hybrid のブートストラップ](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-bottlerocket.html)
- [Hybrid アドオンと Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)
- [containerd registry host の構成](https://github.com/containerd/containerd/blob/v2.2.0/docs/hosts.md)
- [systemd network-online の意味](https://systemd.io/NETWORK_ONLINE/)
- [Kubernetes のバージョン差](https://kubernetes.io/releases/version-skew-policy/)

< [前へ: 制限付きインターネット環境の構成](./03-airgap-setup.md) | [目次](./README.md) | [次へ: GPU 統合](./05-gpu-integration.md) >

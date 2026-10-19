# 前提条件

> **サポート対象バージョン**: EKS 1.36 / hybrid nodeadm 1.0.20 を対象にレビュー。OS ごとの要件は以下を参照。
> **最終更新日**: 2026年9月13日

Hybrid Node を参加させる前に、ホスト、ネットワーク、認証情報、クラスターアクセスを準備してください。ローカルでのスキーマ・暗号・入力値チェックでは、実ネットワーク、GPU ランタイム、本番クラスターを検証できません。このレビューでは、クラウド、ホストネットワーク、GPU ドライバー、イメージビルドへの変更は行っていません。

![Hybrid Node の前提条件と、VPC／オンプレミス間の双方向ルーティング。リモート CIDR を宣言しても、すべてのルートやファイアウォールルールが作成されるわけではありません。](../.gitbook/assets/en-eks-hybrid-nodes-prereq-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-prereq-0.html)

## オペレーティングシステムとランタイム

| AWS が Hybrid Nodes 連携を検証した OS | バージョン／適用範囲 |
|---------------------------------|------------------|
| Ubuntu | 20.04、22.04、24.04。ディストリビューションのセキュリティメンテナンス状況を別途確認 |
| RHEL | 8、9。カーネル／CNI と Red Hat サブスクリプション／サポートを確認 |
| AL2023 | オンプレミスの**仮想化環境**。一般的なベアメタルには適用されず、EC2 外で AWS が OS サポートを提供することも意味しない |
| Bottlerocket | VMware バリアント v1.37.0 以降、Kubernetes 1.28 以降で利用可能。**x86_64 のみ**。ブートストラップ手順は別 |

これらの下限を満たしても、古い Kubernetes リリースが現在も EKS のサポート対象になるわけではありません。サポート期間中の EKS バージョンを選び、対応する OS／ランタイム／CNI の組み合わせを使用してください。AWS がサポートするのは Ubuntu／RHEL の Hybrid Nodes 連携であり、OS ベンダー自身によるメンテナンスではありません。

新規 SSM インストールまたはアップグレードには **nodeadm 1.0.19 以降**が必要です。それ以前のバイナリには古い SSM 署名キーが含まれています。今回レビューしたリリースは **v1.0.20** です。EC2 EKS AMI 用の同名ツールではなく、Hybrid Node 用 nodeadm を使用してください。

ARM 上の EKS kube-proxy 1.31 以降には ARMv8.2+crypto が必要です。Pi 5 より前の Raspberry Pi／Cortex-A72 ハードウェアは要件を満たしません。Pi 5 の CPU だけでは、スタック全体の互換性を確認したことになりません。古い kube-proxy 1.30 の回避策は、EKS の延長サポートが終了した 2026年7月までのものでした。

containerd は必須ですが、Docker Engine は必須ではありません。「containerd 1.6 以降」や Docker のバージョン確認だけでは、現在の CRI 互換性を証明できません。

| OS／選択肢 | nodeadm の containerd ソース |
|-------------|--------------------------|
| Ubuntu／AL2023 | `distro` がサポート対象のデフォルト |
| RHEL | `docker`、または互換ランタイムを事前導入して `none`。`distro` は無効 |
| AL2023 | `docker` はサポート対象外 |
| ランタイムを手動で導入 | `none` はインストールを省略するだけで、ランタイムを提供しない |

Ubuntu 24.04 で過去に発生した Pod 終了／AppArmor の問題の修正には、containerd 1.7.19 以降、または適切な AppArmor 更新が必要でした。これは古いバージョンのインストールを勧めるものではありません。選択した CNI のカーネル要件を確認してください。「カーネル 5.4 以降」であることも、カーネルを無条件に置き換えることも十分ではありません。

### サイジングとホストの確認

AWS はホストに **1 vCPU、メモリ 1 GiB 以上**を推奨しています。実際に必要な容量は、ワークロードと運用設定によって異なります。

コンテナランタイム、CNI、管理エージェント、ワークロードを合わせた CPU とメモリ使用量を見積もってください。OS、コンテナイメージ、ログに必要なディスク容量を確保し、運用上の余裕も設けてください。

```bash
# Run these read-only checks on the intended hybrid host.
cat /etc/os-release
uname -m
uname -r
free -h
df -h /
swapon --show
ip -j link show
# When already installed, inspect the actual CRI runtime:
containerd --version
```

バイナリのバージョンだけでは、kubelet がそのランタイムソケットを使用していることは分かりません。ホストの管理者と連携し、swap、cgroups、フォワーディング、CNI モジュール、ファイアウォールを確認してください。swapoff、fstab、sysctl、MTU を一律に変更する方法は、すべてのサポート対象ホストに適用できるわけではありません。

### インストール、検証、初期化の順に行う

準備済みの Ubuntu／AL2023 ホストでは、次の順序で依存関係をインストールしてから参加させます。RHEL では前述のランタイムソースが必要です。Bottlerocket は異なる手順を使用します。

```bash
set -euo pipefail
# Installation/bootstrap sequence for prepared Ubuntu/AL2023 hosts.
# RHEL requires --containerd-source docker, or none with a preinstalled compatible runtime.
# These commands mutate the host; review OS/runtime/network/identity first.
sudo nodeadm install 1.36 --credential-provider ssm --containerd-source distro \
  --region ap-northeast-2 --timeout 20m
sudo nodeadm config check -c file:///etc/eks/nodeConfig.yaml
sudo nodeadm init -c file:///etc/eks/nodeConfig.yaml
```

ノード設定には、対象クラスターとプロバイダーの入力値をあらかじめ記載してください。認証情報を含む設定ファイルはモード 0600 で保護し、アクティベーションコードをゴールデンイメージやログに含めないでください。以下のコマンドはホストを変更します。失敗を隠すために検証手順を省略しないでください。`nodeadm upgrade` は影響の大きい操作なので、実行前にワークロードを退避させてください。

## Packer によるイメージ準備

AWS の例は Ubuntu 22.04／24.04 と RHEL 8／9 を対象とし、vSphere の OVA および QEMU の qcow2／raw 形式を扱います。レビューした **v1.0.20 のテンプレートは、EKS 1.36 用の完成済みイメージパイプラインではありません**。

- `K8S_VERSION` の検証で許可されるのは、引き続き 1.26～1.31 のみです。レビュー済みの現行フォークを保守し、サンプルに合わせてバージョンを下げないでください。
- `NODEADM_ARCH` が受け取る値は **`amd` または `arm`** で、その後ろに `64` が追加されます。以前の `amd64` を指定すると `amd6464` になります。
- Packer の `CREDENTIAL_PROVIDER=iam` は、nodeadm の **`iam-ra`** に対応します。
- 実際のファイルは `hybrid-nodes-template.pkr.hcl` です。`general-build.qemu.al2023` というソースは存在しません。
- 変更され得る `releases/latest` のダウンロード、vSphere の `insecure_connection=true`、ビルダーのデフォルトパスワード、グローバル変数の要件を確認してください。RHEL のプロビジョナーは x86 用リポジトリを固定指定しています。バイナリのアーキテクチャだけを変更しても ARM 用ビルドにはなりません。

| 入力グループ | 確認事項 |
|-------------|--------|
| ツール | Packer ≥1.11、vSphere plugin ≥1.4 または QEMU 1.x。検証済みの組み合わせを固定 |
| 共通 | `ISO_URL`、検証済みの `ISO_CHECKSUM`、`PKR_SSH_PASSWORD`、`K8S_VERSION`、`NODEADM_ARCH`、`CREDENTIAL_PROVIDER` |
| RHEL | `RH_USERNAME`、`RH_PASSWORD`、`RHEL_VERSION`。最終イメージ／ログにシークレットを含めない |
| vSphere | サーバー、ユーザー、パスワード、データセンター、クラスター、データストア、ネットワーク、**VSPHERE_OUTPUT_FOLDER** |
| QEMU | **PACKER_OUTPUT_FORMAT**（`qcow2`／`raw`）、CPU／仮想化互換性 |

ソースには課金対象となる AWS AMI ビルダーも含まれます。これは Hybrid Node としてクラウドマシンを起動する許可を意味しません。保守されたテンプレートと生成イメージを検証してください。ここでは Packer／VM ビルドを実施していません。

## GPU 互換性

GPU の種類、CPU アーキテクチャ、OS／カーネル、サポート対象 NVIDIA ドライバー、コンテナツールキット／ランタイム、CUDA／フレームワークイメージ、メモリを組み合わせて確認してください。過去に挙げられたドライバー 525／535／545／550 と CUDA 11.8／12.x の値は、歴史的な最小値と推奨値が混在しており、現在の Hybrid Nodes 全体に一律適用される要件ではありません。

H100 80GB、H200 141GB、A100 40／80GB、L40S 48GB は構成例であり、認定済みモデルの完全な一覧ではありません。4GB はすべてのモデルに適用できる有意な最小値ではありません。適切にパッケージされた GPU コンテナを実行するだけなら、ホストに CUDA コンパイラーは不要です。ドライバーとコンパイラーのバージョンは別のものです。

```bash
# On a host where the driver is already installed:
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
# Optional: nvcc reports the locally installed compiler, if present.
if command -v nvcc >/dev/null 2>&1; then nvcc --version; fi
```

選択した構成に対応する、最新の NVIDIA 互換性／プラットフォーム手順を確認してください。ドライバー／カーネルの変更は、ワークロードを退避させたテストホストで事前に実施してください。古いドライバーブランチのインストールや、稼働中ワーカー上の containerd 再起動は、無害な前提条件チェックではありません。

## ネットワーク、CIDR、MTU

Hybrid Nodes には、コントロールプレーンから kubelet および Hybrid Node 上の Webhook へのアクセスも含め、信頼性の高い**プライベートな双方向接続**が必要です。API のパブリックアクセスを有効にしても変わるのは node から API への経路であり、必要なプライベートの逆方向経路ではありません。

AWS は一般的な接続目安として、**帯域幅 100 Mbps、RTT 200 ms 以下**を推奨しています。帯域幅、遅延、パケット損失の目標値はワークロードに合わせて設定し、実際の接続経路で測定してください。トンネルのカプセル化によるオーバーヘッドと経路上の機器が対応するサイズを考慮して MTU を設定してください。

リモート node／Pod の CIDR には IPv4 RFC1918 または CGNAT を使用します。相互に、また VPC／Service のネットワークと重複させないでください。各リモート種別の CIDR は最大 15 個までを、それぞれ**単一の** remote-node-network／remote-pod-network wrapper に含められます。クラスター間の Pod ルーティングにも、意図した分離が必要です。

レビュー済みの `network-plan.json` を保存します。

```json
{
  "vpcCidrs": [
    "10.0.0.0/16"
  ],
  "serviceCidrs": [
    "10.100.0.0/16"
  ],
  "remoteNodeCidrs": [
    "10.80.0.0/16"
  ],
  "remotePodCidrs": [
    "10.85.0.0/16"
  ]
}
```
```bash
: "${NETWORK_PLAN_JSON:?Set the reviewed local network plan JSON}"
export NETWORK_PLAN_JSON
python3 - <<'PY'
import ipaddress, itertools, json, os
from pathlib import Path
plan = json.loads(Path(os.environ["NETWORK_PLAN_JSON"]).read_text())
allowed = [ipaddress.ip_network(c) for c in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10")]
groups = {}
for key in ("vpcCidrs", "serviceCidrs", "remoteNodeCidrs", "remotePodCidrs"):
    values = plan[key]
    if not isinstance(values, list) or not values:
        raise SystemExit(f"{key} must be a nonempty list for this example")
    groups[key] = [ipaddress.ip_network(v, strict=True) for v in values]
    if any(n.version != 4 for n in groups[key]):
        raise SystemExit("This Hybrid Nodes plan requires IPv4")
for key in ("remoteNodeCidrs", "remotePodCidrs"):
    if len(groups[key]) > 15 or any(not any(n.subnet_of(a) for a in allowed) for n in groups[key]):
        raise SystemExit("Remote CIDRs must use RFC1918/CGNAT ranges, at most 15 per kind")
flat = [(key, n) for key, networks in groups.items() for n in networks]
for (ka, a), (kb, other) in itertools.combinations(flat, 2):
    if a.overlaps(other):
        raise SystemExit(f"Overlapping CIDRs: {ka} {a}, {kb} {other}")
print("CIDR syntax/range/non-overlap checks passed; routing and reachability remain unverified")
PY
```

この検査で確認できるのは構文、範囲、重複であり、到達性ではありません。実際の TGW／VGW を経由する VPC 戻りルートと、オンプレミス側の戻りルート／ノード単位の Pod ルートを設定してください。

| 通信フロー | 確認事項 |
|------|--------|
| リモート node／Pod → API TCP 443 | 対象 CIDR に対するクラスター SG の追加インバウンドルール |
| コントロールプレーン ENI → node TCP 10250 | 制限付きクラスター送信ルール、プライベートルート、オンプレミスホスト／ファイアウォールの受信ルール |
| コントロールプレーン → Webhook | 実際の Pod IP、ポート、ルート、ファイアウォール |
| ホスト／Pod → 認証情報／イメージ／DNS／時刻 | プロバイダーのエンドポイント、レジストリ、DNS、時刻同期 |

TCP 10250 は、API サーバー SG への kubelet 受信ルールではありません。EKS だけではすべてのカスタムリモートルールは作成されません。eksctl が自動化できるのは、自身が所有する VPC 側リソースです。ルール上限を固定の 60 とみなさず、実際のクォータを確認してください。

AWS はパブリックのみ、またはプライベートのみを推奨しています。両方を有効にすると、VPC 外の node はパブリックアドレスを解決し、経路／アクセスルールの差異によっては参加に失敗する**可能性があります**。API が必ず拒否するという意味ではありません。プライベートのみの場合も、プライベート DNS と管理者からの到達性が必要です。

## プロバイダー固有の認証情報

想定した管理者 ID を使って AWS の入力値を準備してください。アクティベーション情報はアクセス制限されたディレクトリに保管します。

```bash
set -euo pipefail
: "${EXPECTED_ACCOUNT_ID:?Set the intended account}"
: "${AWS_REGION:?Set the intended Region}"
: "${CLUSTER_NAME:?Set the intended cluster}"
check_account() {
  local actual
  actual=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text) || return
  test "$actual" = "$EXPECTED_ACCOUNT_ID" || { printf 'Account mismatch.\n' >&2; return 1; }
}
check_account
umask 077
export WORK_DIR
WORK_DIR=$(mktemp -d "$PWD/hybrid-preflight.XXXXXXXX")
export EXPECTED_ACCOUNT_ID AWS_REGION CLUSTER_NAME
printf 'Private preparation directory: %s\n' "$WORK_DIR"
```

SSM と Roles Anywhere のどちらも AWS への接続が必要です。ローカル CA や長時間キャッシュされる認証情報があっても、オフラインのコントロールプレーンにはなりません。

### SSM ロールとアクティベーション

ロールには `eks:DescribeCluster`、ECR pull、SSM core／cleanup の権限が必要です。**AmazonEKSWorkerNodeMinimalPolicy だけでは DescribeCluster 権限は付与されません。** Pod Identity の `eks-auth:AssumeRoleForPodIdentity` 権限は別途必要です。

アカウント、Region、クラスターの例示値は一貫して置き換えてください。以下の一覧取得操作はインスタンス単位にリソースを絞れないため、ワイルドカードの範囲を対象 Region に制限しています。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ssm.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "123456789012"
        },
        "ArnLike": {
          "aws:SourceArn": "arn:aws:ssm:ap-northeast-2:123456789012:*"
        }
      }
    }
  ]
}
```
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "eks:DescribeCluster",
      "Resource": "arn:aws:eks:ap-northeast-2:123456789012:cluster/my-hybrid-cluster"
    },
    {
      "Effect": "Allow",
      "Action": "ssm:DescribeInstanceInformation",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-2"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": "ssm:DeregisterManagedInstance",
      "Resource": "arn:aws:ssm:ap-northeast-2:123456789012:managed-instance/*",
      "Condition": {
        "StringEquals": {
          "ssm:resourceTag/EKSClusterARN": "arn:aws:eks:ap-northeast-2:123456789012:cluster/my-hybrid-cluster"
        }
      }
    }
  ]
}
```

レビュー済みの `AmazonEC2ContainerRegistryPullOnly` および `AmazonSSMManagedInstanceCore`、または同等の権限を付与してください。アクティベーションの `EKSClusterARN` タグは、登録解除ポリシーの条件に一致させてください。

登録数の上限を意図的に設定し、登録の有効期限を 24 時間にしてください。

```bash
: "${HYBRID_ROLE_NAME:?Use the reviewed SSM-trusting role name}"
: "${REGISTRATION_LIMIT:?Set a deliberate node registration limit}"
export HYBRID_ROLE_NAME REGISTRATION_LIMIT
python3 - <<'PY'
import json, os, re
from datetime import datetime, timedelta, timezone
from pathlib import Path
account, region, cluster = (os.environ[k] for k in ("EXPECTED_ACCOUNT_ID", "AWS_REGION", "CLUSTER_NAME"))
if not re.fullmatch(r"\d{12}", account) or not re.fullmatch(r"[a-z]{2}(?:-[a-z]+)+-\d", region):
    raise SystemExit("Invalid account/Region")
if region.startswith(("cn-", "us-gov-")):
    raise SystemExit("Hybrid Nodes is not available in this Region family")
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", cluster):
    raise SystemExit("Invalid cluster name")
role = os.environ["HYBRID_ROLE_NAME"]
if not re.fullmatch(r"[\w+=,.@-]{1,64}", role, re.ASCII):
    raise SystemExit("Use the actual IAM role name, not a role ARN")
limit = int(os.environ["REGISTRATION_LIMIT"])
if not 1 <= limit <= 1000:
    raise SystemExit("RegistrationLimit must be 1..1000 per activation; review service quotas separately")
body = {"DefaultInstanceName": "eks-hybrid-node", "IamRole": role, "RegistrationLimit": limit,
        "Description": "Reviewed EKS hybrid activation",
        "Tags": [{"Key": "EKSClusterARN", "Value": f"arn:aws:eks:{region}:{account}:cluster/{cluster}"}],
        "ExpirationDate": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()}
(Path(os.environ["WORK_DIR"]) / "activation-request.json").write_text(json.dumps(body, indent=2) + "\n")
PY
```
```bash
set -euo pipefail
# Run only after the role/trust/tag policy and registration scope are prepared.
check_account
aws ssm create-activation --region "$AWS_REGION" \
  --cli-input-json "file://$WORK_DIR/activation-request.json" --output json \
  > "$WORK_DIR/activation-response.json"
chmod 600 "$WORK_DIR/activation-response.json"
# The response contains the secret ActivationCode. Do not print or commit it.
```

ActivationCode は一度だけ返されます。ActivationId とともに安全に配布してください。アクティベーションが期限切れ／削除になっても、既存の管理対象インスタンスが登録解除されるわけではありません。[CreateActivation の RegistrationLimit](https://docs.aws.amazon.com/systems-manager/latest/APIReference/API_CreateActivation.html) は、引き続きアクティベーション 1 件につき 1～1,000 です。フリーティアの対象となるフリート全体の上限ではありません。最新料金は[認証プロバイダーの比較](README.md#credential-providers)を参照してください。

SSM のノード名は `mi-...` 形式で、認証情報の有効期間は固定の 1 時間です。ネットワーク障害後は、再試行のバックオフによって再接続が遅れる場合があります。認証情報をログに出力しないでください。

### Roles Anywhere の信頼設定と有効期間

プロバイダーに適したロール、信頼アンカー、プロファイルを使用してください。セッション名を証明書 ID／nodeName に紐付けます。従来の PrincipalTag／RequestTag の比較では、この紐付けができていませんでした。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "rolesanywhere.amazonaws.com"
      },
      "Action": [
        "sts:TagSession",
        "sts:SetSourceIdentity"
      ],
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/11111111-2222-3333-4444-555555555555"
        }
      }
    },
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "rolesanywhere.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/11111111-2222-3333-4444-555555555555"
        },
        "StringEquals": {
          "sts:RoleSessionName": "${aws:PrincipalTag/x509Subject/CN}"
        }
      }
    }
  ]
}
```
```json
{
  "name": "hybrid-node-profile",
  "roleArns": [
    "arn:aws:iam::123456789012:role/EKSHybridNodeRole"
  ],
  "enabled": true,
  "acceptRoleSessionName": true,
  "durationSeconds": 3600
}
```

アンカー ARN を置き換え、範囲を限定した DescribeCluster／ECR 権限を付与し、**acceptRoleSessionName=true** を設定してください。

```text
effectiveDuration = min(profileDuration, requestedDuration)
                    or profileDuration when the request omits duration
effectiveDuration <= role.MaxSessionDuration
```

CreateSession で要求する有効期間とプロファイルの設定値は 900～43,200 秒です。CreateSession では**同じ値も許可**されます。プロファイルを 3,600 秒、override なし、ロールの最大値を 3,600 秒にしても有効です。従来の「より大きくなければならない」という説明は正確ではありません。証明書の有効性／失効状況と AWS への接続も必要です。

### ノードごとの鍵と証明書

対象となる新規ノード上にアクセス制限されたディレクトリを作成します。一意の鍵／CSR を生成します。この例では小文字の単純な DNS ラベルを受け付けます。CSR は承認済みの発行元に送り、ノードに CA 署名鍵を置かないでください。

```bash
set -euo pipefail
umask 077
: "${WORK_DIR:?Set a private preparation directory on this node}"
: "${NODE_NAME:?Use a unique certificate CN / node name}"
export NODE_NAME
python3 - <<'PY'
import os, re
name = os.environ["NODE_NAME"]
if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,61}[a-z0-9]", name):
    raise SystemExit("This example requires a lowercase DNS label of 2..63 characters")
PY
test ! -e "$WORK_DIR/node.key"
test ! -e "$WORK_DIR/node.csr"
openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out "$WORK_DIR/node.key"
chmod 600 "$WORK_DIR/node.key"
openssl req -new -key "$WORK_DIR/node.key" -out "$WORK_DIR/node.csr" -subj "/CN=$NODE_NAME"
# Send the CSR to the approved PKI issuer; do not copy its CA private key to nodes.
```

発行された証明書チェーン、承認済み CA、有効期間／失効状況、鍵との一致、CN を確認してください。時刻を同期させます。新しいノードに限り、次の操作を行います。

```bash
set -euo pipefail
: "${ISSUED_NODE_CERT:?Set the verified certificate/chain issued for this node}"
: "${WORK_DIR:?Set the private directory containing the node key}"
# New-node installation only; do not overwrite an existing identity.
sudo test ! -e /etc/iam/pki/server.key
sudo test ! -e /etc/iam/pki/server.pem
sudo install -d -m 0700 /etc/iam/pki
sudo install -m 0644 "$ISSUED_NODE_CERT" /etc/iam/pki/server.pem
sudo install -m 0600 "$WORK_DIR/node.key" /etc/iam/pki/server.key
```

これらは EKS Kubernetes API の CA ファイルではありません。ノード ID をイメージ間で複製したり、既存の鍵を通知なく上書きしたりしないでください。

## CloudFormation の準備

固定した v1.0.20 のテンプレートは、リソース作成の出発点です。SSM 用テンプレートはロールを作成しますが、**アクティベーションは作成しません**。複数クラスターで使う前に、広範な DescribeCluster の範囲と固定の export 名を確認してください。

IRA の `CertAttributeTrustPolicy` 値は、文字列 **`${aws:PrincipalTag/x509Subject/CN}`** です。「CN」ではありません。この Python `cryptography` ヘルパーは PEM を正しくシリアル化し、基本的な CA 形式と現在の有効性を確認しますが、発行者の正当性や失効は確認しません。

```bash
: "${CA_PEM_FILE:?Set the approved CA certificate file, not a private key}"
: "${ROLE_NAME:?Set the new role name selected by the IaC owner}"
export CA_PEM_FILE ROLE_NAME
python3 - <<'PY'
import json, os, re
from pathlib import Path
from cryptography import x509
from datetime import datetime, timezone
raw = Path(os.environ["CA_PEM_FILE"]).read_bytes()
if b"PRIVATE KEY" in raw or raw.count(b"-----BEGIN CERTIFICATE-----") != 1:
    raise SystemExit("Provide one reviewed CA certificate")
cert = x509.load_pem_x509_certificate(raw)
if not cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
    raise SystemExit("Certificate is not a CA")
now = datetime.now(timezone.utc)
if not cert.not_valid_before.replace(tzinfo=timezone.utc) <= now <= cert.not_valid_after.replace(tzinfo=timezone.utc):
    raise SystemExit("CA certificate is not currently valid")
role = os.environ["ROLE_NAME"]
if not re.fullmatch(r"[\w+=,.@-]{1,64}", role, re.ASCII):
    raise SystemExit("Invalid IAM role name")
body = [
    {"ParameterKey": "RoleName", "ParameterValue": role},
    {"ParameterKey": "CertAttributeTrustPolicy", "ParameterValue": "${aws:PrincipalTag/x509Subject/CN}"},
    {"ParameterKey": "CABundleCert", "ParameterValue": raw.decode("ascii")}
]
(Path(os.environ["WORK_DIR"]) / "cfn-iamra-parameters.json").write_text(json.dumps(body, indent=2) + "\n")
PY
```

パラメーターのキー／AllowedValues を固定したテンプレートと比較し、IaC の担当者とともにポリシー範囲および namespace の export を確認してから、変更セットをレビューしてください。不正な PEM の略記や、変更され得る main ブランチのテンプレートをデプロイしないでください。

## クラスターアクセスと作成計画

node IAM ロールには、**HYBRID_LINUX access entry** を優先してください。

```json
{
  "clusterName": "my-hybrid-cluster",
  "principalArn": "arn:aws:iam::123456789012:role/EKSHybridNodeRole",
  "type": "HYBRID_LINUX"
}
```

マッピングには `system:node:{{SessionName}}` とノードのブートストラップ用グループを使用します。認証モードが API／API_AND_CONFIG_MAP のどちらかと、その管理者を確認してください。既存マッピングを消去する 1 ロールだけの `aws-auth` ConfigMap に置き換えないでください。従来のマッピングを変更する場合は、管理された移行を行ってください。

以下の ID は、レビュー済みの既存リソースにすべて置き換えてください。プライベートのみのエンドポイント、IPv4、バージョン 1.36 を明示しています。bootstrap creator への管理者権限付与は管理されたラボ向けです。本番環境での運用者アクセスは、意図的に選択してください。

eksctl 0.229.0 では、文書化された **SSM／IRA** プロバイダー値を使用してください。roleARN を渡す場合は、プロバイダーのリソースを別途準備します。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-hybrid-cluster
  region: ap-northeast-2
  version: '1.36'
iam:
  serviceRoleARN: arn:aws:iam::123456789012:role/EKSClusterRole
accessConfig:
  authenticationMode: API_AND_CONFIG_MAP
  bootstrapClusterCreatorAdminPermissions: true
kubernetesNetworkConfig:
  ipFamily: IPv4
  serviceIPv4CIDR: 10.100.0.0/16
vpc:
  id: vpc-0123456789abcdef0
  subnets:
    private:
      ap-northeast-2a:
        id: subnet-0123456789abcdef0
      ap-northeast-2c:
        id: subnet-0123456789abcdef1
  controlPlaneSecurityGroupIDs:
  - sg-0123456789abcdef0
  clusterEndpoints:
    privateAccess: true
    publicAccess: false
remoteNetworkConfig:
  iam:
    provider: SSM
    roleARN: arn:aws:iam::123456789012:role/EKSHybridNodeRole
  vpcGatewayID: tgw-0123456789abcdef0
  remoteNodeNetworks:
  - cidrs:
    - 10.80.0.0/16
  remotePodNetworks:
  - cidrs:
    - 10.85.0.0/16
```

eksctl でプロビジョニングする場合は `--without-nodegroup` と明示的な private kubeconfig パスを使用してください。スキーマが有効でも、IAM、ルート、ゲートウェイへの到達性は証明されません。eksctl の旧来の「起動時のみ」の説明は古くなっています。現在の EKS では、適切な API の手順を使って既存クラスターにハイブリッドのリモートネットワークを設定できます。

同等の EKS CreateCluster リクエスト:

```json
{
  "name": "my-hybrid-cluster",
  "version": "1.36",
  "roleArn": "arn:aws:iam::123456789012:role/EKSClusterRole",
  "resourcesVpcConfig": {
    "subnetIds": [
      "subnet-0123456789abcdef0",
      "subnet-0123456789abcdef1"
    ],
    "securityGroupIds": [
      "sg-0123456789abcdef0"
    ],
    "endpointPrivateAccess": true,
    "endpointPublicAccess": false
  },
  "kubernetesNetworkConfig": {
    "ipFamily": "ipv4",
    "serviceIpv4Cidr": "10.100.0.0/16"
  },
  "accessConfig": {
    "authenticationMode": "API_AND_CONFIG_MAP",
    "bootstrapClusterCreatorAdminPermissions": true
  },
  "remoteNetworkConfig": {
    "remoteNodeNetworks": [
      {
        "cidrs": [
          "10.80.0.0/16"
        ]
      }
    ],
    "remotePodNetworks": [
      {
        "cidrs": [
          "10.85.0.0/16"
        ]
      }
    ]
  }
}
```

インフラ管理者はどちらか一方に決め、両方の手順を実行しないでください。ホストを参加させる前に、実クラスター／エンドポイント ID、運用者権限、ノードアクセスを検証してください。例示の AWS ID は、実在性を確認していません。

## アドオン

以下は文書化された Hybrid Nodes 互換性の下限であり、すべての Kubernetes バージョンにおける**インストール対象バージョンではありません**。

| アドオン | Hybrid Nodes 互換性の下限 |
|--------|-----------------------------|
| kube-proxy／CoreDNS | 1.25.14-eksbuild.2／1.9.3-eksbuild.7 |
| ADOT／CloudWatch Observability | 0.102.1-eksbuild.2／2.2.1-eksbuild.1 |
| Pod Identity Agent | 通常は 1.3.3-eksbuild.1。Bottlerocket では **1.3.7-eksbuild.2** が必要で、**Bottlerocket OS 1.39.0 以降**も必要 |
| Node monitoring／snapshot controller | 1.2.0-eksbuild.1／8.1.0-eksbuild.2 |
| Private CA Connector／FSx CSI／Secrets Store provider | 1.6.0-eksbuild.1／1.7.0-eksbuild.1／2.1.1-eksbuild.1 |
| Metrics Server／cert-manager | 0.7.2-eksbuild.1／1.17.2-eksbuild.1 |
| Node Exporter／kube-state-metrics／External DNS | 1.9.1-eksbuild.2／2.15.0-eksbuild.4／0.19.0-eksbuild.1 |

```bash
check_account
: "${ADDON_NAME:?Select one add-on to review}"
aws eks describe-addon-versions --region "$AWS_REGION" --addon-name "$ADDON_NAME" \
  --kubernetes-version 1.36 --output json > "$WORK_DIR/addon-catalog.json"
jq '[.addons[].addonVersions[] |
     {addonVersion,architecture,computeTypes,compatibilities}]' "$WORK_DIR/addon-catalog.json"
```

選択したバージョンの Hybrid Nodes／OS／カーネル設定を確認してください。VPC CNI は Hybrid Node を管理しません。互換性のある CNI と、クラウド専用エージェントの配置を設定してください。カタログに掲載されているだけでは、インストール済みまたは正常稼働中であることは分かりません。

## 参考資料

- [Hybrid Nodes の前提条件](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-prereqs.html)
- [オペレーティングシステムと nodeadm の最小バージョン](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
- [nodeadm リファレンス](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [Hybrid Nodes のネットワーク](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
- [認証情報と Hybrid Nodes IAM ロール](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
- [接続断中のホスト認証情報](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-host-creds.html)
- [IAM Roles Anywhere CreateSession](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/authentication-create-session.html)
- [Hybrid Nodes 対応アドオン](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)
- [eksctl の Hybrid Nodes 設定](https://docs.aws.amazon.com/eks/latest/eksctl/hybrid-nodes.html)
- [リリース済み nodeadm v1.0.20](https://github.com/aws/eks-hybrid/releases/tag/v1.0.20)
- [固定した Packer ソース](https://github.com/aws/eks-hybrid/tree/v1.0.20/example/packer)
- [固定した SSM CloudFormation テンプレート](https://github.com/aws/eks-hybrid/blob/v1.0.20/example/hybrid-ssm-cfn.yaml)
- [固定した Roles Anywhere CloudFormation テンプレート](https://github.com/aws/eks-hybrid/blob/v1.0.20/example/hybrid-ira-cfn.yaml)
- [NVIDIA CUDA 互換性](https://docs.nvidia.com/deploy/cuda-compatibility/)
- [NVIDIA Container Toolkit のインストール](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)

< [目次](./README.md) | [次へ: ネットワーク設定](02-network-configuration.md) >

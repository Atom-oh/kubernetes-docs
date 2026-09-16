# 制限されたインターネット環境でのセットアップ（S3、private endpoint、プロキシ）

< [前へ: Network Configuration](./02-network-configuration.md) | [目次](./README.md) | [次へ: Node Bootstrap](./04-node-bootstrap.md) >

> **サポート対象バージョン**: EKS Hybrid Nodes。nodeadm v1.0.20 のソースを確認済みです。クラスターに対応する Kubernetes、OS、runtime、add-on のコホートを選択してください。
> **最終更新**: September 16, 2026

この章では、パブリックインターネットへのアクセスが制限されている Hybrid Nodes を準備します。**Hybrid Nodes には、AWS でホストされる EKS control plane と、認証情報に使用する AWS サービスへの接続が引き続き必要です。** ソフトウェアを物理的に転送しても、Hybrid Nodes が切断された Kubernetes distribution になるわけではありません。

ここでの例は準備およびレビューの手順であり、テスト済みの本番デプロイではありません。監査ではソースコード、設定、ローカルの失敗ケースを検証しましたが、OS image の構築、artifact の公開、node の登録、実際の private network の検証は行っていません。TLS hostname verification が失敗したため、監査環境ではパブリック artifact manifest を取得できませんでした。certificate check はバイパスしておらず、この失敗した取得から現在の artifact patch や digest を推定していません。

**セキュリティチーム向け補足資料:** [Hybrid Nodes network-separation review](11-network-separation-security.md) では、新しい control-plane-to-on-premises 接続、endpoint の種類、権限とデータの境界、レビューの証跡について説明します。private connectivity だけではコンプライアンスを満たしません。

## 接続性と分離の境界

| パターン | 提供するもの | Hybrid Nodes での考慮事項 |
|---|---|---|
| 物理的に切断されたネットワーク | AWS へのライブ接続なし | 必要な EKS control-plane および credential-service への接続を提供できない |
| 制御された egress proxy | 承認済みの外部 HTTPS 宛先およびログ | installer、package manager、host daemon、該当する Pod を個別に設定する |
| private endpoint を伴う VPN/Direct Connect | クラスターおよびサポートされる AWS API への private path | 双方向ルート、DNS、security group、authorization が必要。endpoint はすべてのパブリック download host をカバーしない |
| offline software transfer | レビュー済み artifact をインポートする制御された方法 | private AWS connectivity と併用すると有用だが、その接続を置き換えるものではない |

ネットワーク制限は露出を減らせますが、規制コンプライアンスの保証、データ流出の排除、すべての supply-chain attack の防止を保証するものではありません。certificate trust、承認済み publisher、signature、patching、operator access、application data flow は別個の control です。private connectivity にも、AWS サービスおよびオンプレミスネットワークへの依存関係が残ります。

![物理的分離、proxy egress、private AWS connectivity の比較。接続されているパターンだけが EKS Hybrid Nodes を運用できます。](../.gitbook/assets/en-eks-hybrid-nodes-03-airgap-setup-0.png)

[🔍 対話型ダイアグラムを表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-03-airgap-setup-0.html)

> **ダイアグラムの明確化:** 物理的に分離された選択肢は比較用であり、サポートされる Hybrid Nodes の運用モードではありません。

## アーキテクチャと artifact の責任範囲

![制御された準備ホストがレビュー済みソフトウェアを private storage にステージングし、node は検証済み download URL と private AWS connectivity を使用します。](../.gitbook/assets/en-eks-hybrid-nodes-03-airgap-setup-1.png)

[🔍 対話型ダイアグラムを表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-03-airgap-setup-1.html)

> **ダイアグラムの訂正:** `hybrid-assets.eks.amazonaws.com → PHZ → S3` のショートカットは、機能する透過的な mirror ではありません。以下の installation path を使用してください。DNS の変更だけでは、元の hostname の TLS certificate、S3 object routing、request authorization は提供されません。

| Artifact | 準備と配信 |
|---|---|
| Hybrid `nodeadm` | `aws/eks-hybrid` の release を承認し、root として実行する前に provenance と checksum を検証します。これは EC2 の `amazon-eks-ami` nodeadm とは異なります |
| kubelet、kubectl、CNI plugin、ECR credential provider、IAM authenticator | 承認済み artifact manifest から、正確に 1 つの release/build/OS/architecture を選択します |
| IAM Roles Anywhere signing helper | 独自の release を選択して検証します。任意に最初の array entry を選択しないでください |
| SSM installer/agent | 個別の Regional download、signature、registration path です。custom EKS artifact manifest によって完全にはリダイレクトされません |
| containerd、runc、iptables、OS dependency | transitive dependency と署名済み repository metadata を含む、承認済み OS/runtime package cohort |
| CNI、CoreDNS、kube-proxy、sandbox、workload image | 実際の manifest、init container、image digest、platform を棚卸しします。image tag は binary manifest からは提供されません |

Amazon VPC CNI（`aws-node` / `vpc-cni-init`）は Hybrid Nodes 用の CNI ではありません。[Network Configuration](./02-network-configuration.md) にあるサポート対象の Hybrid CNI 手順を使用してください。選択した CNI datapath が使用する場合にのみ kube-proxy を含めます。CNI plugin binary bundle はデプロイ済み CNI controller ではありません。

## installation path を選択する

### Path A: preinstalled OS image

制御された builder で、承認済み Hybrid nodeadm をインストールし、クラスターで選択した Kubernetes version と credential provider を使用して `nodeadm install` を実行します。AWS はこの image-build の利用を文書化しています。インストール済み artifact と nodeadm tracker を image 内に保持します。

```bash
# Controlled image builder only; installs software on this host.
set -euo pipefail
: "${KUBERNETES_VERSION:?Approved cluster-compatible version}"
: "${REGION:?}" "${CREDENTIAL_PROVIDER:?ssm or iam-ra}"
case "$CREDENTIAL_PROVIDER" in ssm|iam-ra) ;; *) exit 1 ;; esac
sudo nodeadm install "$KUBERNETES_VERSION" \
  --credential-provider "$CREDENTIAL_PROVIDER" --region "$REGION"
```

デフォルトの runtime source は OS distro ですが、この source は RHEL ではサポートされません。RHEL では、文書化された Docker package source を選択するか、互換性のある runtime を事前インストールして `--containerd-source none` を使用してください。Docker source は AL2023 ではサポートされません。`none` は containerd を自動的にインストールしません。

builder を initialize/register してその identity を複製することは**しないでください**。各 node の SSM activation または IAM Roles Anywhere certificate/private key は、承認済みの node ごとのプロセスで配信してください。activation code、private key、SSM registration state、kubelet certificate、operator credential を再利用可能な image に bake しないでください。Bottlerocket には独自の preparation/bootstrap workflow があり、この nodeadm 手順は使用しません。

新しい SSM installation/upgrade には nodeadm **1.0.19 以降**が必要です。これは古い release に古い SSM signing key が含まれているためです。この章で確認したのは **v1.0.20** であり、無制限な `latest` binary ではありません。

### Path B: custom artifact manifest

公開された **v1.0.20 source** は、user-guide の flag table にすべてが記載されていない場合でも、以下の flag をサポートします。

| Command/setting | 確認した release での実際の動作 |
|---|---|
| `install --manifest-override file:///path/manifest.json` | ローカル manifest を読み取ります。YAML decoder が JSON を受け付けます |
| `install --manifest-override https://mirror.example.com/manifest.json` | 通常の HTTP client で manifest を download します |
| `install --private-mode` | `--manifest-override` が必要です。OS package installation をスキップしますが、credential および EKS artifact は引き続きインストールします |
| `init --manifest-override ... --private-mode` | manifest argument が必要であり、そこから Region metadata を取得します。AWS authentication または EKS connectivity の要件は削除しません |
| 個々の artifact `uri` / `checksum_uri` | S3 SigV4 signing なしで HTTP(S) 経由で取得されます。`file://` **manifest** は `file://` **artifact** URL のサポートを意味しません |
| `gzip_uri` | 存在する場合は `uri` より優先されます。checksum verification は decompression 後に行われます |

これらの flag を使用する前に、正確にデプロイされる binary の `install --help` と `init --help` を確認してください。private mode は完全な offline package installer ではありません。systemd unit を含む containerd、runc、iptables、CA certificate、および必要なすべての OS dependency を事前インストールしてください。

`--credential-provider ssm` では、v1.0.20 は引き続き Regional `ssm-setup-cli` と signature URL を個別に構築します。manifest の `ssm_releases` field はこの installation path をリダイレクトしません。これらの S3 object と後続の agent installation/registration dependency へのアクセスを計画するか、検証済みの preinstalled-image workflow を使用してください。

### manifest をレビューして 1 つの cohort を選択する

upstream manifest には、`supported_eks_releases`、`iam_roles_anywhere_releases`、`region_config` があります。Kubernetes record には `major_minor_version`、`latest_patch_version`、`patch_releases[].version`、**`patch_version`**、**`release_date`**、artifact ごとの URL が含まれます。複数の build が 1 つの patch version を共有する場合があります。以前の `1.33.3` の例は過去の schema illustration であり、現在承認されている patch の証拠ではありません。

download した upstream manifest、その取得日/hash、承認記録を保持してください。選択前に HTTPS origin を検証してください。次のローカル selector には、正確な Kubernetes patch、build date、signing-helper release、architecture が必要です。曖昧な選択、artifact の欠落、重複する YAML key、未知の Region を拒否します。ECR account を推測せず、実際の Region metadata を保持します。

準備ホストで `select-mirror.py` として保存してください。Python 3 と PyYAML が必要です。

```python
#!/usr/bin/env python3
"""Build a local review plan, not an installer. Requires PyYAML."""
import copy
import datetime
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

import yaml


class UniqueLoader(yaml.SafeLoader):
    pass


def mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError("duplicate YAML key")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping
)


def https_url(value):
    if not isinstance(value, str) or any(c.isspace() for c in value):
        raise ValueError("URL must be a nonempty HTTPS URL")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment):
        raise ValueError("HTTPS URL must not contain credentials, query or fragment")
    return value


def select(manifest, version, build_date, iam_version, arch, region, mirror):
    if not re.fullmatch(r"1\.\d+\.\d+", version):
        raise ValueError("an exact approved Kubernetes patch is required")
    datetime.date.fromisoformat(build_date)
    if arch not in ("amd64", "arm64"):
        raise ValueError("unsupported architecture")
    mirror = https_url(mirror).rstrip("/")
    region_info = manifest["region_config"][region]  # No account fallback.
    if (region_info.get("partition") != "aws"
            or region_info.get("dns_suffix") != "amazonaws.com"
            or not region_info.get("cred_providers", {}).get("iam-ra")
            or not re.fullmatch(r"\d{12}", str(region_info.get("ecr_account_id", "")))):
        raise ValueError("review a supported commercial Region with IAM Roles Anywhere")
    minor, patch = version.rsplit(".", 1)
    releases = [
        release
        for family in manifest["supported_eks_releases"]
        if family["major_minor_version"] == minor
        for release in family["patch_releases"]
        if release["version"] == version and release["patch_version"] == patch
        and release["release_date"] == build_date
    ]
    iam = [
        release for release in manifest["iam_roles_anywhere_releases"]
        if release["version"] == iam_version
    ]
    if len(releases) != 1 or len(iam) != 1:
        raise ValueError("release selection must be unique")
    eks_release, iam_release = copy.deepcopy(releases[0]), copy.deepcopy(iam[0])
    plan = []
    for release, names in [
        (eks_release, ["kubelet", "kubectl", "cni-plugins",
                       "ecr-credential-provider", "aws-iam-authenticator"]),
        (iam_release, ["aws_signing_helper"]),
    ]:
        chosen = []
        for name in names:
            matches = [a for a in release["artifacts"]
                       if a["name"] == name and a["arch"] == arch and a["os"] == "linux"]
            if len(matches) != 1:
                raise ValueError("missing or duplicate artifact: " + name)
            artifact = matches[0]
            item_id = "a%02d" % len(plan)
            plan.append({"id": item_id, "name": name,
                         "uri": https_url(artifact["uri"]),
                         "checksum_uri": https_url(artifact["checksum_uri"])})
            # Use the original, uncompressed URI; its checksum is not a gzip-file hash.
            artifact.pop("gzip_uri", None)
            artifact["uri"] = mirror + "/" + item_id + "/data"
            artifact["checksum_uri"] = mirror + "/" + item_id + "/data.sha256"
            chosen.append(artifact)
        release["artifacts"] = chosen
    selected = {
        "supported_eks_releases": [{
            "major_minor_version": minor, "latest_patch_version": patch,
            "patch_releases": [eks_release],
        }],
        "iam_roles_anywhere_releases": [iam_release],
        "region_config": {region: copy.deepcopy(region_info)},
    }
    return selected, {"artifacts": plan}


def main():
    if len(sys.argv) != 9:
        raise ValueError(
            "usage: select-mirror.py UPSTREAM VERSION BUILD_DATE IAM_VERSION "
            "ARCH REGION HTTPS_MIRROR_PREFIX NEW_OUTPUT_DIR"
        )
    source, version, date, iam, arch, region, mirror, output = sys.argv[1:]
    manifest = yaml.load(Path(source).read_text(), Loader=UniqueLoader)
    selected, plan = select(manifest, version, date, iam, arch, region, mirror)
    out = Path(output)
    out.mkdir(mode=0o700, parents=False, exist_ok=False)
    (out / "upstream.yaml").write_bytes(Path(source).read_bytes())
    (out / "manifest.json").write_text(json.dumps(selected, indent=2) + "\n")
    (out / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")


if __name__ == "__main__":
    main()
```

output directory は新規でなければなりません。HTTPS mirror prefix は、公開に使用する同じ immutable object prefix にマッピングする必要があります。この script は plan を構築するだけで、mirror への download も authentication も行いません。

```bash
set -euo pipefail
: "${APPROVED_PATCH:?}" "${APPROVED_BUILD_DATE:?}" "${APPROVED_IAM_VERSION:?}"
: "${ARCH:?amd64 or arm64}" "${REGION:?}"
: "${MIRROR_PREFIX:?HTTPS URL for this reviewed candidate}"
: "${NEW_PLAN_DIR:?A new local directory}"
python3 select-mirror.py upstream.yaml "$APPROVED_PATCH" "$APPROVED_BUILD_DATE" \
  "$APPROVED_IAM_VERSION" "$ARCH" "$REGION" "$MIRROR_PREFIX" "$NEW_PLAN_DIR"
```

すべての source host と選択された 6 つの artifact を download 前にレビューしてください。これは **IAM Roles Anywhere artifact の例**であり、SSM installer mirror ではありません。nodeadm 自体、OS package、image、signing key、certificate は含まれません。

`download-plan.sh` として保存してください。

```bash
#!/usr/bin/env bash
# Download into a new plan directory. No AWS writes or host installation.
set -euo pipefail
umask 077
cd -- "${1:?Use the directory produced by select-mirror.py}"
test ! -e checksums.sha256
test ! -e queue.tsv
jq -er '.artifacts[] | [.id, .uri, .checksum_uri] | @tsv' plan.json > queue.tsv
test "$(wc -l < queue.tsv)" -eq 6
while IFS=$'\t' read -r item_id uri checksum_uri; do
  [[ "$item_id" =~ ^a[0-9]{2}$ ]]
  mkdir -- "$item_id"  # Refuse a partial run or existing directory.
  curl --fail --show-error --silent --location \
    --proto '=https' --proto-redir '=https' --connect-timeout 10 \
    --max-time 300 --max-filesize 268435456 \
    "$uri" -o "$item_id/data"
  curl --fail --show-error --silent --location \
    --proto '=https' --proto-redir '=https' --connect-timeout 10 \
    --max-time 30 --max-filesize 4096 \
    "$checksum_uri" -o "$item_id/upstream.sha256"
  expected=$(python3 - "$item_id/upstream.sha256" <<'CHECKSUM_PY'
import pathlib, re, sys
text = pathlib.Path(sys.argv[1]).read_text().strip()
match = re.fullmatch(r"([0-9a-fA-F]{64})(?:[ \t]+[^\r\n]+)?", text)
if not match:
    raise SystemExit("missing, malformed or multi-record upstream checksum")
print(match.group(1).lower())
CHECKSUM_PY
)
  actual=$(sha256sum "$item_id/data")
  [[ "${actual%% *}" == "$expected" ]]
  # nodeadm v1.0.20 requires GNU format: digest, space, filename.
  printf '%s  data\n' "$expected" > "$item_id/data.sha256"
done < queue.tsv
sha256sum manifest.json plan.json upstream.yaml a*/data a*/data.sha256 \
  > checksums.sha256
sha256sum --strict --check checksums.sha256
printf '%s\n' 'Six artifacts verified locally; publishing and node installation remain separate.'
```

size limit は artifact あたり意図的に 256 MiB としています。承認済み artifact がこれを超える場合はレビューしてください。download、malformed checksum、hash mismatch が発生すると script は停止します。partial directory は調査用に保持されます。原因を解決した後、新しい candidate を開始してください。共有の `/tmp` directory を削除したり、欠落した checksum をスキップしたりしないでください。

これらの hash は、選択した byte を取得済み checksum に結び付けます。これらは独立した signature でも、侵害された publisher が信頼できることの証明でもありません。レビュー済み manifest/checksum record を保護し、利用可能な場合は publisher verification を使用してください。

## Private S3 の公開と authorization

Block Public Access、承認済み encryption、versioning/retention、分離された publisher/reader permission を備えた、**事前作成済みで所有する** bucket を使用してください。以下の例では bucket を作成せず、その policy を置き換えることもありません。AccessDenied、expired credential、timeout は失敗であり、bucket/object が存在しない証拠ではありません。

既存 bucket 向けの reader-policy statement の例は次のとおりです。

```json
{
  "Sid": "ReadApprovedHybridArtifacts",
  "Effect": "Allow",
  "Principal": {"AWS": "arn:aws:iam::111122223333:role/HybridArtifactReader"},
  "Action": "s3:GetObject",
  "Resource": "arn:aws:s3:::example-hybrid-artifacts/hybrid-candidates/*",
  "Condition": {"StringEquals": {"aws:SourceVpce": "vpce-0123456789abcdef0"}}
}
```

account、role、bucket、prefix、endpoint をレビュー済みの値に置き換えてください。この statement は 1 つの path を許可するものであり、他の既存 grant を取り消すものではありません。1 つの endpoint 外からのすべての request に対する bucket-wide の `Deny s3:*` は、接続された publisher と管理上の recovery も block する可能性があります。そのような boundary を適用する前に、これらの path を明示的に設計してください。

named-principal policy には signed request が必要です。**nodeadm の通常の HTTPS downloader は、node に IAM role があるからといって IAM-authenticated S3 client にはなりません。** 検証すべき実行可能な design は次の 2 つです。

1. authenticated preparation agent/CLI を使用して承認済み file を取得し、適切な network access control と独自 hostname 用の certificate を持つ組織管理下の HTTPS artifact service で提供する。
2. runtime binary mirror dependency のない preinstalled-image path を使用する。

private S3 object URL が `403` を返す問題は、DNS override では修復されません。bearer presigned URL や credential を manifest、process argument、公開 log に入れないでください。組織が private network に限定した非secret binary の unauthenticated read を選択する場合、それは別途明示的にレビューする policy であり、上記の named-principal policy ではありません。

`publish-plan.sh` として保存してください。bucket owner が candidate と permission を承認した後にのみ実行してください。この script は **S3 object を書き込みます**。

```bash
#!/usr/bin/env bash
# Owner-approved publication only; creates billable S3 objects, never a bucket.
set -euo pipefail
umask 077
cd -- "${1:?Use a verified plan directory}"
: "${REGION:?}" "${BUCKET:?}" "${EXPECTED_ACCOUNT_ID:?}" "${PREFIX:?}"
[[ "$EXPECTED_ACCOUNT_ID" =~ ^[0-9]{12}$ ]]
[[ "$PREFIX" =~ ^hybrid-candidates/[A-Za-z0-9-]+$ ]]
sha256sum --strict --check checksums.sha256
aws s3api head-bucket --region "$REGION" --bucket "$BUCKET" \
  --expected-bucket-owner "$EXPECTED_ACCOUNT_ID"
# Manifest is last. Any failed write stops; retain the partial prefix for review.
for file in a{00..05}/data a{00..05}/data.sha256 checksums.sha256 \
            upstream.yaml plan.json manifest.json; do
  test -f "$file"
  aws s3api put-object --region "$REGION" --bucket "$BUCKET" \
    --expected-bucket-owner "$EXPECTED_ACCOUNT_ID" \
    --key "$PREFIX/$file" --body "$file" --if-none-match '*' \
    --server-side-encryption AES256 --checksum-algorithm SHA256 \
    --output json > "${file//\//_}.upload.json"
done
printf '%s\n' 'Candidate uploaded. Verify readback, mirror URL mapping and hashes before promotion.'
```

SSE-KMS が必要な bucket では、AES256 の例ではなく承認済み key と KMS permission を使用してください。conditional write は既存 key の overwrite を防止しますが、multi-object upload を atomic にはしません。manifest は最後に upload され、失敗した candidate は readback と実際の HTTPS mirror mapping が検証されるまで unpublished のままです。返却される object VersionId/checksum と retention を記録してください。S3 ETag は汎用的な SHA-256 digest ではありません。

## DNS と private endpoint の要件

`hybrid-assets.eks.amazonaws.com` は AWS CloudFront download host です。その名前の PHZ を作成して S3 に alias しても、以下は維持されません。

- TLS certificate/SNI hostname。
- HTTP Host header と S3 bucket/object key mapping。
- 特に uploader がすべての name を flatten した場合の、元の path。
- request authorization。

TLS check を無効化してこれを修正しないでください。承認済み origin へ制御された proxy 経由で到達可能にするか、preinstalled image を使用するか、実際の mirror URL を伴うサポート対象の manifest override を使用してください。

S3 **Interface** endpoint は、VPN/Direct Connect 経由でオンプレミス client にサービスを提供できます。S3 private DNS はサポートされています。**private DNS only for inbound Resolver** option では、VPC 側で維持される S3 gateway endpoint が必要です。あるいは、VPC とオンプレミスの request の両方を interface endpoint 経由で route します。gateway endpoint 単体にはオンプレミスから直接アクセスできません。

Region 内の最初の S3 endpoint ではなく、レビュー済みの VPC と endpoint ID で endpoint を選択してください。[Network Configuration](./02-network-configuration.md) の DNS/routing procedure を使用してください。EKS management API endpoint は Kubernetes API endpoint ではありません。private ECR endpoint は public ECR や CloudFront への一般的なアクセスを提供しません。

## 準備済み node のインストールと初期化

custom IAM Roles Anywhere path では、runtime、OS dependency、承認済み nodeadm、mirror service がすでに準備されている必要があります。この command は target node に software をインストールします。

```bash
set -euo pipefail
: "${APPROVED_PATCH:?}" "${REGION:?}" "${LOCAL_MANIFEST:?Absolute local path}"
[[ "$LOCAL_MANIFEST" = /* ]]
test -s "$LOCAL_MANIFEST"
sudo nodeadm install "$APPROVED_PATCH" --region "$REGION" \
  --credential-provider iam-ra --containerd-source none \
  --manifest-override "file://$LOCAL_MANIFEST" --private-mode
```

[Prerequisites](./01-prerequisites.md) と [Node Bootstrap](./04-node-bootstrap.md) を使用して node ごとの config を準備してください。たとえば、SSM config の**形式**は次のとおりです。

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-hybrid-cluster
    region: ap-northeast-2
  hybrid:
    ssm:
      activationCode: REPLACE_WITH_NODE_ACTIVATION_CODE
      activationId: REPLACE_WITH_NODE_ACTIVATION_ID
```

node にインストールされている provider と正確に一致するものを使用してください。この SSM 形式は、上記の IAM Roles Anywhere command 用の config ではありません。入力済み file を保護し（root-owned、mode `0600`）、絶対に commit せず、shell history に secret を入れないでください。手書きの API endpoint/CA field を指定しても、文書化された cluster discovery と authentication path の必要性はなくなりません。

```bash
# Local config validation; this is not a join or an end-to-end network test.
sudo nodeadm config check --config-source file:///etc/eks/nodeconfig.yaml
```

network、identity、CNI の prerequisite に合格した後、owner は `nodeadm init` を実行できます。private-manifest path では、承認済み manifest を再度渡してください。

```bash
# Mutates the target node and registers it with EKS.
sudo nodeadm init --config-source file:///etc/eks/nodeconfig.yaml \
  --manifest-override file:///etc/eks/manifest.json --private-mode
```

確認した version には `nodeadm init --dry-run` はありません。不完全な preparation pass を成立させるために initialization validation をスキップしないでください。

## Container image の配信

private ECR pull には、ECR API および DKR path、S3 layer-download path、DNS、適切な image-pull permission が必要です。`describe-repositories` call が成功しても、image layer を download できることは証明されません。pull-through cache を事前に投入してテストしてください。ECR endpoint documentation では、最初の未キャッシュ pull に追加のインターネット要件があることを説明しています。

デプロイ済み add-on manifest にある実際の registry account/Region/image reference を使用してください。Kubernetes patch に `-eksbuild.1` を付加して image tag を構築したり、無関係な cluster から古い pause/CoreDNS version をコピーしたりしないでください。

nodeadm は ECR helper を `/etc/eks/image-credential-provider/ecr-credential-provider` にインストールし、その config を `/etc/eks/image-credential-provider/config.json` に初期化します。別の directory の下に使用されない file を書き込むのではなく、生成された kubelet configuration を確認してください。`ctr images pull` は別の client であり、kubelet の exec credential provider を自動的には使用しません。

### Offline image transfer

承認済み digest と必要な platform を選択してください。multi-platform archive では、source/destination format が対応している場所で index と digest を保持してください。

```bash
# Preparation host: downloads images; requires reviewed registry authentication.
set -euo pipefail
: "${SOURCE_DIGEST_REF:?registry/repository@sha256:approved-digest}"
: "${NEW_IMAGE_DIR:?New directory}"
[[ "$SOURCE_DIGEST_REF" =~ @sha256:[0-9a-f]{64}$ ]]
mkdir -m 700 -- "$NEW_IMAGE_DIR"
skopeo copy --all --preserve-digests "docker://$SOURCE_DIGEST_REF" \
  "oci-archive:$NEW_IMAGE_DIR/image.tar:approved"
(cd "$NEW_IMAGE_DIR" && sha256sum image.tar > image.tar.sha256)
```

archive と、独立して保護された approval/hash record を転送してください。import または push の前に、その directory で `sha256sum --strict --check image.tar.sha256` を実行し、失敗した場合は停止してください。internal registry destination の場合は次のとおりです。

```bash
# Internal staging host: writes an image to the reviewed destination registry.
set -euo pipefail
: "${DEST_DIGEST_REF:?approved-registry/repository@sha256:approved-digest}"
[[ "$DEST_DIGEST_REF" =~ @sha256:[0-9a-f]{64}$ ]]
sha256sum --strict --check image.tar.sha256
skopeo copy --all --preserve-digests oci-archive:image.tar:approved \
  "docker://$DEST_DIGEST_REF"
```

registry TLS verification を無効化しないでください。compression/manifest format を変更すると digest を保持できない場合があります。変更されていないと黙って主張するのではなく、停止して結果の identity をレビューしてください。

containerd を直接 preload する方法もありますが、デプロイされる runtime に対してテストする必要があります。Kubernetes は `k8s.io` namespace を使用し、import された reference は Pod/sandbox reference と一致する必要があり、必要なすべての platform blob が存在しなければなりません。archive の `approved` annotation が、Pod が要求する registry name になるわけではありません。image garbage collection と `imagePullPolicy` も後続の pull を発生させることがあります。tar import の成功だけでは offline Pod が起動することの証明にはなりません。

## 署名済みローカル package repository

OS release、architecture、transitive dependency、metadata をレビュー済み cohort として mirror してください。vendor signature を保持するか、別途信頼される key を使用して組織管理の repository に署名してください。

**すでに準備・署名済みの**ローカル flat repository 向け Ubuntu client configuration の例は次のとおりです。

```text
deb [signed-by=/etc/apt/keyrings/hybrid-mirror.gpg] file:///srv/apt-repo ./
```

repository には `Packages.gz` だけでなく、有効な `Release` と `InRelease` または `Release.gpg` が必要です。独立した信頼済み path を通じて key fingerprint を配布し検証してください。repository authentication を抑制するために `trusted=yes` を使用しないでください。

DNF/YUM repository configuration の例は次のとおりです。

```ini
[hybrid-local]
name=Reviewed hybrid packages
baseurl=file:///srv/yum-repo
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-hybrid-mirror
```

これには有効な package signature と署名済み repository metadata が必要です。metadata と package signing key は異なる場合があります。承認済み key set を設定してください。verification が失敗したときに `gpgcheck=0` を設定しないでください。package installation と service restart は、任意の live-node verification script ではなく、image build または drain 済みの maintenance operation で実施するものです。

## Proxy configuration

まず client ごとの destination map を作成してください。loopback、実際の private API/registry name、proxy を bypass すべき node/Pod/Service range を含めてください。CIDR と suffix matching は client によって異なります。**`.eks.amazonaws.com`** を無条件に `NO_PROXY` に入れないでください。これは public `hybrid-assets.eks.amazonaws.com` download host にも一致します。

レビュー済みの nonsecret proxy configuration 用の shell example は次のとおりです。

```bash
export HTTP_PROXY=http://proxy.internal.example.com:3128
export HTTPS_PROXY=http://proxy.internal.example.com:3128
export NO_PROXY=localhost,127.0.0.1,::1,.svc,.cluster.local,registry.internal.example.com
export http_proxy="$HTTP_PROXY" https_proxy="$HTTPS_PROXY" no_proxy="$NO_PROXY"
```

実際の private API hostname/IP および他の bypass destination を追加してください。これは完全な site configuration ではありません。login shell の environment は既存の systemd service を設定しません。`/etc/environment` を source したり、繰り返し追記したりしないでください。

`containerd.service` と `kubelet.service` では、`/etc/systemd/system/UNIT.service.d/http-proxy.conf` の下に owner-managed drop-in を使用してください。

```ini
[Service]
Environment="HTTP_PROXY=http://proxy.internal.example.com:3128"
Environment="HTTPS_PROXY=http://proxy.internal.example.com:3128"
Environment="NO_PROXY=localhost,127.0.0.1,::1,.svc,.cluster.local,registry.internal.example.com"
```

既存の drop-in をレビューし、影響を受ける unit は承認済みの build/maintenance phase でのみ restart してください。containerd TOML の `[proxy.http]` section は HTTP proxy configuration ではありません。

| Component | 設定と条件 |
|---|---|
| nodeadm process | `sudo` 経由で渡すのはレビュー済み proxy environment のみとし、`sudo -E` で operator environment 全体を渡さない |
| containerd / kubelet | 個別の systemd environment。生成される kubelet config と host environment は異なる layer |
| documented snap install を使用する Ubuntu 上の SSM | `snap.amazon-ssm-agent.amazon-ssm-agent.service.d/http-proxy.conf` |
| AL2023/RHEL 上の SSM | `amazon-ssm-agent.service.d/http-proxy.conf`。実際にインストールされた unit を確認する |
| IAM Roles Anywhere credential process | nodeadm は `--with-proxy` の生成時に proxy variable を検出します。起動元 daemon にも正しい environment を渡す必要があります |
| `spec.hybrid.enableCredentialsFile: true` を使用する IAM Roles Anywhere | この mode には `aws_signing_helper_update.service` が**存在します**。initialization 前にその drop-in を設定してください。すべての IAM Roles Anywhere installation に service が存在すると仮定しないでください |
| apt | `Acquire::http::Proxy` と `Acquire::https::Proxy` を含む owner-managed `/etc/apt/apt.conf.d/` file |
| snap | snap を実際に使用する場合は `snap set system proxy.http=... proxy.https=...` |
| dnf / yum | 既存 configuration の `proxy` setting をレビューして更新します。他の setting を置き換えたり、重複を追記したりしないでください |
| kube-proxy / その他の Pod | その traffic に proxy が必要な場合にのみ Pod environment を設定する |

文書化された proxy topology では、kube-proxy は cluster creation 後かつ hybrid node の join 前に設定してください。既存の `NODE_NAME` environment とすべての command argument を保持してください。次は standalone DaemonSet ではなく、**strategic merge patch fragment** です。

```yaml
spec:
  template:
    spec:
      containers:
        - name: kube-proxy
          env:
            - name: HTTP_PROXY
              value: http://proxy.internal.example.com:3128
            - name: HTTPS_PROXY
              value: http://proxy.internal.example.com:3128
            - name: NO_PROXY
              value: localhost,127.0.0.1,::1,.svc,.cluster.local
```

bypass destination をレビュー/拡張し、add-on の owner を通じて適用してください。built-in DaemonSet strategic merge は container/env name を使用します。JSON Patch の `add /containers/0/env` は既存 environment 全体を置き換える可能性があり、container index を前提とします。選択した CNI が kube-proxy を置き換える場合、この例のためだけに kube-proxy をデプロイしないでください。

## 検証と制御された更新

| Check | 必要な証拠 | 不十分なもの |
|---|---|---|
| Artifact integrity | 選択されたすべての file、checksum、承認済み manifest、cohort が一致すること | 欠落した file のスキップ、または検証済み file が 0 件であることを受容すること |
| DNS/TLS | 意図した route 上での正しい destination と hostname/CA validation | `10.*` address、任意の `172.*` address、または `curl -k` |
| S3 | 正確な bucket/key/version、expected owner、hash に対する実際の authorized readback | prefix の listing、または API error を不在として扱うこと |
| ECR | workload の credential path による、実際に必要な digest/platform と layer pull | `describe-repositories` または standalone の unauthenticated `ctr` call |
| nodeadm config | 保護され入力済みの file で `nodeadm config check` が成功すること | config の欠落を成功として数えること、または存在しない `init --dry-run` |
| Node operation | credential refresh、Kubernetes API trust/authentication、CNI/DNS、範囲を限定した workload test | 成功したローカル parser check または 1 回の `/healthz` response |

AWS read が認可されている場合は、文書化された connectivity/identity diagnostics に `nodeadm debug --config-source file:///etc/eks/nodeconfig.yaml` を使用してください。これは service に接続し、sensitive diagnostic context を出力する場合があります。出力を非公開に保ち、共有前に機密データを除去してください。不明または失敗した check を「本番運用可能」に変えないでください。

update automation は**candidate を検出**した後、promotion 前に source verification、compatibility review、OS/image scanning、local validation、representative node canary、approval を要求する必要があります。新しい immutable version/build prefix の下で公開し、以前に承認された cohort を保持して、rollback limit を記録してください。本番の `latest` key を密かに overwrite する cron job を実行しないでください。`nodeadm upgrade` は disruptive であり、workload evacuation が必要です。

以前の quiz にある過去の bandwidth estimate、layer caching **50–80%**、compression **30–50%**、platform filtering **50%** には、帰属可能な measurement がありません。予測される節約量ではなく、未検証の過去の illustration としてのみ保持してください。layer reuse、platform set、compression format の実際の byte 数を測定してください。digest が変わらないと主張しながら、承認済み content を recompress しないでください。

## 主な参照先

- [AWS Hybrid nodeadm reference](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [Prepare Hybrid operating systems](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
- [Hybrid proxy configuration](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-proxy.html)
- [nodeadm v1.0.20 install flags](https://github.com/aws/eks-hybrid/blob/v1.0.20/cmd/nodeadm/install/install.go) and [init flags](https://github.com/aws/eks-hybrid/blob/v1.0.20/cmd/nodeadm/init/init.go)
- [Artifact selection/download implementation](https://github.com/aws/eks-hybrid/blob/v1.0.20/internal/aws/source.go) and [SSM source](https://github.com/aws/eks-hybrid/blob/v1.0.20/internal/ssm/source.go)
- [S3 interface endpoints/private DNS](https://docs.aws.amazon.com/AmazonS3/latest/userguide/privatelink-interface-endpoints.html)
- [ECR VPC endpoints](https://docs.aws.amazon.com/AmazonECR/latest/userguide/vpc-endpoints.html)
- [Skopeo copy](https://github.com/containers/skopeo/blob/main/docs/skopeo-copy.1.md)
- [APT repository authentication](https://manpages.ubuntu.com/manpages/noble/man8/apt-secure.8.html)
- [DNF repository signature settings](https://github.com/rpm-software-management/dnf/blob/master/doc/conf_ref.rst)
- [S3 PutObject conditions, encryption and checksums](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObject.html)
- [Kubernetes image names, digests and pull policies](https://kubernetes.io/docs/concepts/containers/images/)

< [前へ: Network Configuration](./02-network-configuration.md) | [目次](./README.md) | [次へ: Node Bootstrap](./04-node-bootstrap.md) >

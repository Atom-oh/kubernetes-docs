# Bare Metal ServerのOSインストールと移行ガイド

< [前へ: 運用と保守](./08-operations.md) | [目次](./README.md) | [次へ: Hybrid Nodes Gateway](./10-hybrid-nodes-gateway.md) >

> **検証基準**: AWS Hybrid OS/nodeadmのドキュメントと公開価格を2026年9月13日に確認しました。nodeadm 1.0.20をCLIの確認対象としています。現在サポートされているEKS／OS／CNIの組み合わせを選択してください。
> **最終更新**: 2026年9月13日

このガイドでは、破壊を伴うOSインストール、イメージ準備、クラスターへの参加、読み取り専用の受け入れ確認を分けて説明します。例にはplaceholderが含まれ、ホスト固有のインストール計画が必要です。このレビューではOSインストール、Packer build、VM作成、AWS／クラスター操作を実行していません。

## 概要

### Bare Metalを選択する理由

hypervisorを取り除くと、ライセンス費用と実行レイヤーを避けられる場合がありますが、総コストの削減やアプリケーション性能の向上が保証されるわけではありません。置き換えを決める前に、仮想化機能、可用性、backup、storage、networking、support契約、移行工数を棚卸ししてください。VMのアプリケーションが自動的にcontainerへ変換されるわけではなく、pilotクラスターを開始しても既存のライセンス義務はなくなりません。

### OSインフラストラクチャのサポートマトリクス

| OS | Bare metal | オンプレミス仮想化 | 設定とサポートの範囲 |
| --- | --- | --- | --- |
| Ubuntu 20.04/22.04/24.04 | 対応するHybrid OS familyとして掲載 | OS/kernel/CNI要件に従うサポート対象host infrastructure | nodeadm/YAML。Ubuntuのサポート期間とsupportを別途確認 |
| RHEL 8/9 | 対応するHybrid OS familyとして掲載 | OS/kernel/CNI要件に従うサポート対象host infrastructure | nodeadm/YAML。Red Hat subscription／OS supportは別途必要 |
| AL2023 | **サポートされる導入方式ではありません** | オンプレミスの仮想化guest | nodeadm/YAML。AWS Support PlanはEC2外のAL2023 OSを対象外 |
| Bottlerocket VMware variant >=1.37.0 | **Hybrid bare metalでは非対応** | VMware vSphere、**x86_64** | Bottlerocket settings/bootstrap。VMware VMはgovcで管理 |

AWSがHybrid連携をサポートするOSは掲載されているUbuntu/RHEL familyであり、OS vendorのsupport義務とは別です。具体的なversion、architecture、CNI/kernel要件を確認してください。EC2外のAL2023はVM guestの選択肢であり、一般的なraw imageのbare-metal推奨ではありません。BottlerocketのVMware Kubernetes variantは1.28から存在しますが、これはvariantの履歴であり、古いEKS versionの使用を推奨するものではありません。SSMによるインストール／upgradeにはnodeadm 1.0.19以降が必要です。それ以前のversionは古いSSM署名keyを使用します。

## コスト比較分析

### ライセンス／subscriptionコストの比較

#### VMware vSphere

実際の製品bundle、ライセンス対象core数、最低料金、契約期間、supportを明記した最新の見積もりを取得してください。以前の「1 socketあたり年間$4,500～$8,500」という数字は、ここでは出典を確認できていないため、現在のvSphere見積もりとして扱えません。

#### OpenShift

実際のRed Hat entitlement、物理／仮想coreまたはsocketの計量方法、support tierを同じ条件で比較してください。以前の「1 nodeあたり年間$2,500～$5,000」という概算と「premium support込み」という説明は未検証です。現在の価格やentitlementの保証に使わないでください。

#### EKS Hybrid Nodes

[公式価格ページ](https://aws.amazon.com/eks/pricing/)では、**報告されたnode vCPU-hour**に対して月次の限界料金tierが適用されます。最初の576,000時間は$0.020、次の576,000時間は$0.014、次の4,608,000時間は$0.010、次の5,760,000時間は$0.008、11,520,000時間を超える分は$0.006です。常に一律$0.01という料金ではありません。

tierの集計範囲は、1つのaccount／Region内、またはAWS Organizationsの一括請求を利用する同一Region内のaccountです。hyperthreaded bare-metal coreは1つにつき2 vCPUとして報告される場合があります。nodeが参加した時点で課金が始まり、削除されると停止します。workloadがidleでもnode料金はなくなりません。32 vCPUを超えるマシンについて、AWSはaccount teamへの問い合わせを求めています。クラスター、provisioned control plane／capability、network、logging、storage、OS、その他のsupport料金は別です。

### 規模別の年間コスト比較（32 vCPU Server）

以下は請求書や測定結果ではなく、条件を固定した**モデル**です。nodeごとに報告vCPU 32、毎月730時間、Region／集計範囲は1つ、他のHybrid利用なし、同じ条件の月を12回と仮定します。最後の列には、standard supportで基本tierのクラスター1つを$0.10/時間で加算しています。他service、割引／税、hardware、電力、OS entitlement、作業人員、移行費用は含みません。実際の請求には月の日数やtierの再計算も影響します。

| node数 | 月間vCPU-hour | 月間node料金 | 年間換算node料金 | 年間換算node料金 + standard supportの基本クラスター1つ |
| --- | --- | --- | --- | --- |
| 10 | 233,600 | $4,672.00 | $56,064.00 | $56,940.00 |
| 50 | 1,168,000 | $19,744.00 | $236,928.00 | $237,804.00 |
| 100 | 2,336,000 | $31,424.00 | $377,088.00 | $377,964.00 |

<details>
<summary>過去の概算（未検証で、現在の価格ではありません）</summary>

元の表は追跡可能性のために残しています。vendor見積もりの出典を確認できませんでした。EKS列は、クラスター料金と限界tierを考慮しない旧式の「`32 × $0.01 × 8,760 = $2,803.20/node-year`」という仮定を使用しています。これらの数値は、現在有効な比較TCOの根拠ではありません。

| 規模 | VMware vSphere（以前の年間概算） | OpenShift（以前の年間概算） | EKS Hybrid（旧式の一律料金による概算） |
| --- | --- | --- | --- |
| 10 node | ~$45,000～85,000 | ~$25,000～50,000 | ~$28,032 |
| 50 node | ~$225,000～425,000 | ~$125,000～250,000 | ~$140,160 |
| 100 node | ~$450,000～850,000 | ~$250,000～500,000 | ~$280,320 |

</details>

### TCO（総所有コスト）の考慮事項

予備capacity、設備／電力、OS/security patch、PKI/SSM運用、storage/backup/restore、接続性、監視、要員、ライセンス義務、rollback用capacityを含めてください。availabilityとsupportの範囲を揃えて比較してください。未検証の古い表から削減率を主張しないでください。

## OS別のBare Metalインストール

### 前提条件

#### BIOS/UEFI設定

選択したinstaller、firmware、boot mode、NIC/storage driver、署名済みboot chainを確認してください。検証済みのbootloader/kernel/module chainが対応している場合はSecure Bootを維持してください。containerの一般的なLinux containerd/runc実行にVT-x/AMD-V hardware virtualizationは必要ありません。VM型sandbox、QEMU/KVM image builder、その他の仮想化workloadには別の要件があります。

#### ネットワークインフラストラクチャ

従来のPXEではDHCP/ProxyDHCPとTFTPを使うことが多い一方、UEFI HTTP/iPXE構成では別のboot transportを使う場合があります。`pxelinux.0`はどのUEFIでも使えるloaderではありません。firmwareに合ったbootloaderを選び、ISO/kernel/initrdの完全性を検証し、provisioning networkをworkloadから分離してください。host固有の設定を保護し、認証されていない共通HTTP/TFTP rootからactivation code、private key、passwordを配布しないでください。

#### AWS Packer template

[AWSのexample directory](https://github.com/aws/eks-hybrid/tree/main/example/packer)に現在あるファイルは`hybrid-nodes-template.pkr.hcl`です。以前の架空の`bare-metal-template.pkr.hcl`ではありません。入力`CREDENTIAL_PROVIDER`は`ssm`または`iam`を受け付け、HCLでは`iam`をnodeadmの`iam-ra`に対応づけます。QEMUの出力形式には`output_format` variableではなく`PACKER_OUTPUT_FORMAT`を使います。承認されたcommitのtemplateとprovisioner scriptを確認し、builderに必要な入力とpassword/user-dataの扱いもレビューしてください。

```bash
# From a reviewed checkout of aws/eks-hybrid/example/packer:
export NODEADM_ARCH=amd       # This template uses amd/arm, not amd64/arm64.
export CREDENTIAL_PROVIDER=ssm # The template accepts ssm/iam; maps iam to nodeadm iam-ra.
export PACKER_OUTPUT_FORMAT=raw
: "${K8S_VERSION:?Set a currently supported cluster-compatible major.minor}"
: "${ISO_URL:?Set the approved Ubuntu or RHEL installer ISO}"
: "${ISO_CHECKSUM:?Set the verified vendor ISO checksum}"
export K8S_VERSION ISO_URL ISO_CHECKSUM
# Also prepare the selected builder's required inputs using the reviewed template.
packer validate -syntax-only hybrid-nodes-template.pkr.hcl
# A separate build action, not a validation step:
# packer build -only=general-build.qemu.ubuntu24 hybrid-nodes-template.pkr.hcl
```

templateにはAMI/vSphere builderもあります。別途承認されたbuildを行う前に、目的のbuilderだけを選択してください。syntaxだけの検証はimageをbuild／testした証拠ではありません。古いKubernetes例、builderのdefault password、誰でも読めるcredential file、登録済みmachine／SSM identityを再利用するimageにコピーしないでください。

手動でprovisionしたhostには、承認済みのnodeadm release／architectureを、レビュー済みchecksumとともに用意します。これは**インストール手順**であり、health checkではありません。承認済みのrelease検証手順からchecksumを取得してください。推測したり、不一致を無視したりしないでください。

```bash
set -euo pipefail
: "${NODEADM_VERSION:?Set the approved release, at least 1.0.19 for SSM}"
: "${NODEADM_SHA256:?Set the approved SHA-256 for this release and architecture}"
: "${NODEADM_ARTIFACT:?Set the local file delivered through the approved artifact channel}"
case "$(uname -m)" in
  x86_64) NODEADM_ARCH=amd64 ;;
  aarch64|arm64) NODEADM_ARCH=arm64 ;;
  *) printf 'Unsupported architecture\n' >&2; exit 2 ;;
esac
[[ "$NODEADM_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || exit 2
[[ "$NODEADM_SHA256" =~ ^[[:xdigit:]]{64}$ ]] || exit 2
[[ "$(printf '%s\n' 1.0.19 "$NODEADM_VERSION" | sort -V | head -n 1)" == 1.0.19 ]] || exit 2
umask 077
STAGING_DIR=$(mktemp -d)
trap 'rm -f -- "$STAGING_DIR/nodeadm"; rmdir -- "$STAGING_DIR"' EXIT
cp -- "$NODEADM_ARTIFACT" "$STAGING_DIR/nodeadm"
printf '%s  %s\n' "$NODEADM_SHA256" "$STAGING_DIR/nodeadm" | sha256sum --check -
chmod 0700 "$STAGING_DIR/nodeadm"
# Check the verified staged binary before replacing the installed executable.
ACTUAL_VERSION=$("$STAGING_DIR/nodeadm" --version)
VERSION_RE="(^|[^0-9.])v?${NODEADM_VERSION//./\\.}([^0-9A-Za-z.+-]|$)"
[[ "$ACTUAL_VERSION" =~ $VERSION_RE ]] || { printf 'Artifact version mismatch\n' >&2; exit 2; }
printf '%s\n' "$ACTUAL_VERSION"
sudo install -m 0755 "$STAGING_DIR/nodeadm" /usr/local/bin/nodeadm
/usr/local/bin/nodeadm --version
```

### Ubuntu LTS（22.04/24.04）

Ubuntu ServerのSubiquity AutoinstallはYAMLを使い、cloud-initで設定を配信できます。以下のtemplateではstorage選択を意図的に対話式にしており、使用前に承認済みの正確なdisk serialとSSH keyが必要です。diskの選択／partition作成は既存データを破壊します。破棄可能なtarget上で先にbackup、disk一覧、installer配信、access/recovery、firmware互換性を確認してください。データdiskのあるhostではwildcard／空のdisk matchや「最大のdisk」を前提にしてはいけません。

#### Autoinstall設定例

```yaml
#cloud-config
autoinstall:
  version: 1
  interactive-sections: [storage]
  locale: en_US.UTF-8
  keyboard:
    layout: us
  storage:
    layout:
      name: lvm
      match:
        serial: REPLACE_WITH_APPROVED_DISK_SERIAL
  identity:
    hostname: replace-with-unique-hostname
    username: hybrid-admin
    password: "!"
  ssh:
    install-server: true
    allow-pw: false
    authorized-keys:
    - "ssh-ed25519 REPLACE_WITH_APPROVED_PUBLIC_KEY"
  packages: [curl, jq]
  shutdown: poweroff
```

このtemplateの`password: "!"`はpassword認証をlockします。実際に承認されたSSH accessとrecovery経路を確認してください。hostと選択したinstallerに合わせてnetwork/NIC/VLAN/bond設定を指定します。ローカルschema checkではdisk選択、boot、loginを検証できません。nodeadmは上記の別手順でstage／installします。installerが未検証の`latest` binaryを取得するわけではありません。

#### Ubuntu 24.04固有の注意事項

[Ubuntu bug 2065423](https://bugs.launchpad.net/ubuntu/+source/containerd-app/+bug/2065423)は、container終了時のAppArmorによるsignal拒否と、release済みpackage修正に関するものです。AWSのOSページには1.7.19以降の修正に関する説明が残っています。実際のdistribution package／backport、読み込まれたprofile、runtime、拒否ログを確認してください。停止中のPodすべてに当てはまる診断でも、古いcontainerd releaseを使い続ける推奨でもありません。

```bash
# Read-only investigation on the affected host:
containerd --version
dpkg-query -W 'containerd*' 'runc*' 'apparmor*'
sudo journalctl -k --since '30 minutes ago' --no-pager -n 200
if test -f /run/reboot-required.pkgs; then cat /run/reboot-required.pkgs; fi
```

文書化された該当package/profileの移行では、修正済みprofileを読み込むために再起動が必要です。lifecycle手順に沿ってdrain、reboot、workload確認を計画してください。AppArmorを編集するたびにrebootが必要と一般化しないでください。`aa-remove-unknown`は`/etc/apparmor.d`に存在しない読み込み済みprofileをすべて削除します。特定profileの編集機能ではなく、defaultの修復commandでもありません。

### RHEL 9

RHELではKickstartを使います。以下は**Bashではなく**インストールtemplateです。承認済みの単一インストールdisk識別子、password hash、完全なSSH public keyに置き換えてください。`ignoredisk --only-use`と`clearpart --drives`には同じ検証済みdiskを指定します。制限のない`clearpart --all`は使わないでください。repository/stage2/bootloader/networkの詳細を選択したRHEL installerに合わせ、使用前にksvalidatorで検証してください。

#### Kickstart設定例

```text
# Template: substitute and validate the approved target disk, key and password hash.
lang en_US.UTF-8
keyboard us
timezone UTC --utc
rootpw --lock
user --name=hybrid-admin --groups=wheel --iscrypted --password=REPLACE_WITH_CRYPT_HASH
sshkey --username=hybrid-admin "ssh-ed25519 REPLACE_WITH_APPROVED_PUBLIC_KEY"
network --bootproto=dhcp --device=link --activate
ignoredisk --only-use=REPLACE_WITH_APPROVED_INSTALL_DISK
clearpart --all --initlabel --drives=REPLACE_WITH_APPROVED_INSTALL_DISK
autopart --type=lvm
selinux --enforcing
services --enabled=sshd
%packages
@core
openssh-server
curl
jq
%end
poweroff
```

SELinuxはenforcingのままにして、個別のpolicy/context要件を調査してください。nodeadmにはcontainerd SELinux設定とPod security contextの説明があります。`container_t`を一律にpermissiveへ変更しないでください。OS packageとnodeadm/containerdのインストールは別の段階です。

#### RHELでのcontainerdインストールに関する注意事項

RHELでは`distro`はnodeadmの対応containerd sourceではありません。nodeadmに互換性のあるDocker配布packageをインストールさせる場合は`docker`を選択します。containerdを別途インストール／管理する場合は`none`を選択します。「RHELでは常にdockerが必要」という説明は範囲が広すぎます。

```bash
set -euo pipefail
: "${K8S_VERSION:?Set a currently supported cluster-compatible major.minor}"
sudo nodeadm install "$K8S_VERSION" --credential-provider ssm \
  --containerd-source docker
# If containerd is separately installed and maintained, choose --containerd-source none.
```

#### 大規模環境: Satellite/Foremanとの統合

Satellite/Foremanでは、レビュー済みKickstart template、repository、provisioning workflowを管理できます。hostごとのdisk、hardware identity、subscription、artifact完全性、障害復旧を確認してください。syntax上正しい共通templateだからといって、任意のfleetを消去してよいことにはなりません。

### Amazon Linux 2023

これは**仮想化guestの参考情報**であり、bare-metalインストールの選択肢ではありません。AWSはEC2外でAL2023を実行するためのKVM、VMware、Hyper-V VM imageを提供します。AWS Support PlanはEC2外でのAL2023 OS利用を対象にしません。EKS Hybrid連携のsupportとは区別してください。用途に適したimageとcloud-init transportを使います。最小限のVM identity断片は次のとおりです。

```yaml
#cloud-config
# VM identity fragment only; it does not install or join a Hybrid Node.
hostname: replace-with-unique-hostname
manage_etc_hosts: true
ssh_pwauth: false
```

この断片ではadminを作成せず、keyを埋め込まず、nodeも初期化しません。承認済みのaccessを準備し、別途レビューされたbootstrap手順を使ってください。AL2023では`--containerd-source docker`はサポートされません。対応するdistribution sourceを使うか、containerdを意図的に別管理してください。

### VMware上のBottlerocket（参考）

EKS Hybrid Nodesでは、x86_64上の対応するVMware variant >=1.37.0を使ってください。Bottlerocketのsettingsとbootstrap containerでOS/authenticationを設定します。govcはVMware VMの管理CLIであり、TOML settingsのparserではありません。version固有のsetting、private user-data、credential設定は[完全なbootstrapガイド](./04-node-bootstrap.md)を参照してください。

## Credential Providerの設定比較

### nodeadmベースの設定（Ubuntu/RHEL/AL2023）

以下はSSMとIAM Roles Anywhereという別々の選択肢です。各placeholderを承認済みのcluster/Region/identityに置き換え、NodeConfigのownerをrootにしてmode 0600で保護し、hostごとのprivate keyを秘密に保ってください。登録済みSSM stateや共有host keyをgolden imageへ入れないでください。

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    region: ap-northeast-2
  hybrid:
    ssm:
      activationCode: "REPLACE_WITH_PRIVATE_ACTIVATION_CODE"
      activationId: "REPLACE_WITH_PRIVATE_ACTIVATION_ID"
```

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    region: ap-northeast-2
  hybrid:
    iamRolesAnywhere:
      trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:111122223333:trust-anchor/REPLACE_WITH_ID
      profileArn: arn:aws:rolesanywhere:ap-northeast-2:111122223333:profile/REPLACE_WITH_ID
      roleArn: arn:aws:iam::111122223333:role/HybridNodeRole
      certificatePath: /etc/eks/pki/node.crt
      privateKeyPath: /etc/eks/pki/node.key
```

nodeadmは設定を検証し、構成済みAWS identityを使って必要なcluster metadataを取得します。参加させる前に、実際のAPI到達性、EKS access entry、trust／permission、certificate pathを確認してください。YAMLのparse成功だけでは認可の証明になりません。

### Bottlerocketベースの設定（VMware）

以前の`[settings.hybrid.ssm]`と`[settings.hybrid.iam-roles-anywhere]` blockは、Bottlerocketの有効なsettingではありません。対応するKubernetes settingと文書化されたHybrid bootstrap-container入力を[Node bootstrap](./04-node-bootstrap.md)で確認してください。base64 user-dataはencodingであり、暗号化ではありません。VMware guestinfoとprovisioning logを保護してください。

### Credential Provider選択ガイド

| 状況 | 選択時の考慮事項 |
| --- | --- |
| 管理されたPKIがない | SSM hybrid activationでcertificate管理を減らせます。identity／activationのライフサイクルは管理してください |
| 既存の管理PKIがある | IAM Roles AnywhereでhostごとのX.509 identityを利用できます。発行、trust、有効期限、revokeを管理してください |
| public internetがない | どちらも必要なAWS APIへ承認済みprivate／proxy経路から接続します。endpoint対応を確認してください |
| 完全に切断された環境／DDIL | EKS Hybrid Nodesは対応する運用方式ではありません。IAM Roles AnywhereもAWSのCreateSessionを呼び出します |
| 独自のnode identityが必要 | Providerの命名規則とライフサイクルを確認してください。Node名が名前解決可能なhost名とは限りません |

[private connectivity](./03-airgap-setup.md)を参照してください。「public internetがない」と「AWSへの接続がない」は異なる要件です。

## 大規模provisioningの自動化

### PXE bootインフラストラクチャの設定

```text
Approved host/firmware inventory
  → matching DHCP/HTTP/PXE boot configuration
  → verified signed loader and installer kernel/initrd
  → protected host-specific installation configuration
  → explicit approved disk / OS installation
  → unique host identity / separate Hybrid bootstrap
```

図示されたTFTP/PXELINUXの組み合わせはlegacy BIOSを想定しています。UEFI PXEでもTFTPを使えますが、UEFI対応loaderが必要です。実環境でサポートされるsecure transportを選択してください。ISO checksumの検証と署名へのtrustは、DHCP到達性とは別です。

### Ansible自動化playbook

以下のplaybookは、すでに準備したhostに対する**読み取り専用の事前確認**です。必要なcomponent/serviceがなければ停止します。`/usr/bin/kubelet`の存在を目的のversionがある証拠にはしません。binaryをinstallせず、secret templateも配布せず、nodeadm initを繰り返し実行しません。

```yaml
# Read-only preflight; does not provision, install, or initialize hosts.
- name: Inspect approved Hybrid hosts
  hosts: hybrid_nodes
  become: true
  gather_facts: false
  serial: 1
  any_errors_fatal: true
  tasks:
  - name: Read OS release
    ansible.builtin.command:
      argv: [cat, /etc/os-release]
    changed_when: false
  - name: Read architecture
    ansible.builtin.command:
      argv: [uname, -m]
    changed_when: false
  - name: Read installed nodeadm version
    ansible.builtin.command:
      argv: [/usr/local/bin/nodeadm, --version]
    changed_when: false
  - name: Check each required service
    ansible.builtin.command:
      argv: [systemctl, is-active, --quiet, "{{ item }}"]
    loop: [containerd, kubelet]
    changed_when: false
```

provisioningは承認済みの別工程に分けてください。host/disk一覧を検証 → 確認済みOS/artifactをstage → hostごとのprivate設定を渡す → [bootstrapのstate／identity手順](./04-node-bootstrap.md)を実行 → 実際のNode UID、version、新しいLease、workloadのhealthを確認します。既存hostには[ライフサイクル管理](./07-node-lifecycle.md)を使ってください。一度に1台を扱い、失敗時は停止して途中状態の証拠を保持してください。`creates: /usr/bin/kubelet`の背後に変更を隠さないでください。

## 移行戦略

### VMwareからBare Metal + EKS Hybrid Nodesへ

#### フェーズ1: 並行インフラストラクチャを構築する

workload、仮想machine、license、network/security機能、storage、依存関係を棚卸しします。並行して対応する移行先、private connectivity、rollback用capacityを準備します。移行期間中にBottlerocket on VMwareを残すことはできますが、それがbare-metal OSへ変わるわけではありません。

#### フェーズ2: workloadをcontainer化する

適切なworkloadを明示的にcontainer化してください。一部のVMはVMのまま残す必要があるかもしれません。書き込みを行うworkloadを移行する前に、stateの移行、CSIの動作、permission、backup、restoreを検証してください。AWS managed databaseはアーキテクチャ上の選択肢であり、自動変換ではありません。

#### フェーズ3: networkを移行する

NSX-Tのrouting、overlay、firewall、load balancing、policy機能を個別に棚卸しします。Cilium BGPはrouteを交換する機能であり、NSX-Tの全機能を同等に置き換えるものではありません。trafficを切り替える前にaddressing、return path、ingress/TLS、DNS、policy、確立済みconnectionを検証してください。

#### フェーズ4: VMwareを廃止する

workload/dataの受け入れ、合意済みrollback期間、backup復旧、ライセンス／保持方針を確認してから廃止してください。削除対象のインフラストラクチャを実際に確認します。license取消やdisk消去をpipelineの自動的な最終処理にしないでください。

### OpenShiftからEKS Hybrid Nodesへ

#### 概念の対応づけ

| OpenShift | 移行先候補 | 解決すべき移行上の差異 |
| --- | --- | --- |
| Route | Ingress / Gateway API controller | TLS終端／reencrypt／passthrough、weight、annotation、policyはcontrollerに依存します |
| SCC | PSS/Pod Security Admissionと必要なpolicy/defaulting | PSSはSCCのUID/SELinux/group戦略やmutationを再現しません |
| OLM | 対応するOLM、Helm、EKS add-on/operator配布 | OLMはKubernetes上で動作できますが、CRD変換、upgrade、dependencyは自動移行されません |
| MachineSet | host lifecycle/provisioning automation | nodeadm/Ansibleはreplacement／scaling意味論を持つMachine API controllerではありません |
| ImageStream | registryとimage昇格／trigger自動化 | ECRはimageを保存しますが、ImageStreamのimport/tag/change triggerは置き換えません |
| BuildConfig | レビュー済みの外部CI/CD | source、image、credential、build policyの挙動を再構成します |
| DeploymentConfig | Deploymentと必要なrollout自動化 | trigger、hook、strategy、rollbackの挙動を維持します |

#### workload移行チェックリスト

- すべてのRoute、policy/default、CRD/operator、image trigger、build、rollout hookを棚卸しします。
- 代表的なworkloadで移行先の挙動とServiceAccount/RBAC scopeをテストします。
- dataの整合性、snapshot/restore、DNS/TLS、network制御、observabilityを検証します。
- 移行元を廃止する前に、traffic切り替えとrollbackをリハーサルします。

#### 段階的な移行

依存関係を評価 → 重要度の低い代表workloadでpilot → 制御されたwaveで移行 → data／運用を受け入れて復旧証拠を保持 → 合意済みrollback期間後に廃止します。

## インストール後の検証

検証ではpackageを再installしたり、参加済みhostを初期化したりしません。次の読み取りは状態の観察だけです。processが動作していることや古いReady状態だけで、workloadを受け入れたとは判断できません。

```bash
# Read-only, on the host mapped to the intended Kubernetes Node:
set -euo pipefail
cat /etc/os-release
uname -m -r
/usr/local/bin/nodeadm --version
containerd --version
for service in containerd kubelet; do
  systemctl is-active --quiet "$service"
done
```

```bash
# From the approved administrative context; these are reads, not installation:
set -euo pipefail
: "${KUBE_CONTEXT:?Set the approved context}"
: "${NODE:?Set the actual registered Node name from inventory}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE" -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-node-lease get lease "$NODE" -o yaml
```

Nodeとhostの対応表を使い、新しいLeaseとversionを確認し、CNI/DNS/storageを検証してください。[bootstrap](./04-node-bootstrap.md)と[lifecycle](./07-node-lifecycle.md)ガイドに基づいて承認済みworkload checkを実行します。checkの失敗や不明な結果を合格扱いしないでください。

## トラブルシューティング

| 問題 | 確認事項と限定的な次の手順 |
| --- | --- |
| boot失敗 | firmware mode、署名済みloader、DHCP/HTTP/TFTP設計、NIC driver、承認済みimage checksum |
| Autoinstall/Kickstart失敗 | installer log/schema、対象disk、repository/stage2、host固有設定。破壊的なpartition操作を無計画に再試行しない |
| Ubuntuの終了処理問題 | 実際のAppArmor signal拒否の証拠、修正済みpackage/backport、計画済みの必要なreboot |
| RHEL containerd | 対応するdocker/none sourceを選択し、runtimeとSELinux policyを確認 |
| nodeadm/authentication | 現行nodeadm、保護された設定、AWS private connectivity、identity、trustを確認し、盲目的な再登録を避ける |

## 検証範囲と参考資料

ローカルの証拠には、schema/contract/command doubleのcheck 50件、artifact/host/API-read subprocess test 12件、pykickstart 3.78のRHEL9 parser、Decimalを使った価格assertion 10件が含まれます。canonical Autoinstall schemaではrootに追加keyを許可しており、選択したinstallerでの検証の代わりにはなりません。実OSインストール、disk消去、boot/login、Packer image build、Ansible SSH操作、nodeadm実行、VM作成、AWS/Kubernetes呼び出しは行っていません。一時的なtest targetと実行fileは合成したものです。

- [AWS Hybrid OS要件](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
- [AWS Hybrid nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [AWS EKS料金](https://aws.amazon.com/eks/pricing/)
- [AWS Packer example](https://github.com/aws/eks-hybrid/tree/main/example/packer)
- [Canonical Autoinstall reference](https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html)
- [RHEL 9 Kickstart reference](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/automatically_installing_rhel/kickstart-commands-and-options-reference_rhel-installer)
- [Ubuntu bug 2065423](https://bugs.launchpad.net/ubuntu/+source/containerd-app/+bug/2065423)
- [aa-remove-unknown manual](https://manpages.ubuntu.com/manpages/noble/man8/aa-remove-unknown.8.html)
- [EC2外でのAL2023](https://docs.aws.amazon.com/linux/al2023/ug/outside-ec2.html)
- [Operator Lifecycle Manager](https://olm.operatorframework.io/docs/)
- [OpenShift SCC API](https://docs.redhat.com/en/documentation/openshift_container_platform/4.20/html/security_apis/securitycontextconstraints-security-openshift-io-v1)


---

< [前へ: 運用と保守](./08-operations.md) | [目次](./README.md) | [次へ: Hybrid Nodes Gateway](./10-hybrid-nodes-gateway.md) >

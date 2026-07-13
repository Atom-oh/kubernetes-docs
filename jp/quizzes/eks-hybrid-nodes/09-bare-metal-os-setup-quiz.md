# Bare Metal Server OS インストールと移行クイズ

> **関連ドキュメント**: [Bare Metal Server OS Installation and Migration Guide](../../eks-hybrid-nodes/09-bare-metal-os-setup.md)

## 選択式問題

### 1. Bare Metal Server 上で EKS Hybrid Nodes を実行する主な利点は何ですか？

A. AWS EC2 インスタンスより高速なネットワーク速度
B. VMware ライセンスコストの削減と hypervisor オーバーヘッドの排除
C. Bottlerocket OS を使用できること
D. AWS Support Plans の適用

<details>
<summary>答えを表示</summary>

**回答: B) VMware ライセンスコストの削減と hypervisor オーバーヘッドの排除**

**解説:**
Bare Metal Server 上で EKS Hybrid Nodes を実行すると、VMware のライセンスコスト（Broadcom による買収後にサブスクリプションモデルへ移行）と OpenShift のサブスクリプション料金を削減できます。さらに、hypervisor レイヤーを排除することでパフォーマンスが最適化されます。

</details>

### 2. PXE boot infrastructure に必要な必須コンポーネントは何ですか？

A. DNS server と NFS server
B. DHCP server と TFTP server
C. FTP server と SMTP server
D. LDAP server と Kerberos server

<details>
<summary>答えを表示</summary>

**回答: B) DHCP server と TFTP server**

**解説:**
PXE boot infrastructure の中核コンポーネントは次のとおりです。
- DHCP Server: IP アドレス割り当てと PXE boot 情報（next-server、filename）を提供します
- TFTP Server: bootloader（pxelinux.0）、kernel（vmlinuz）、および initial RAM disk（initrd.img）を配信します
- HTTP Server（任意）: OS インストールイメージと設定ファイルをホストします

</details>

### 3. Ubuntu の自動インストール方法と RHEL の自動インストール方法の組み合わせとして正しいものはどれですか？

A. Ubuntu: Kickstart, RHEL: Autoinstall
B. Ubuntu: Autoinstall (cloud-init), RHEL: Kickstart
C. Ubuntu: Preseed, RHEL: Anaconda
D. Ubuntu: YAML, RHEL: JSON

<details>
<summary>答えを表示</summary>

**回答: B) Ubuntu: Autoinstall (cloud-init), RHEL: Kickstart**

**解説:**
- Ubuntu は PXE 自動インストールに Autoinstall（cloud-init ベース）を使用します。YAML 形式の設定ファイルを使用します。
- RHEL は PXE 自動インストールに Kickstart を使用します。設定は ks.cfg ファイルで行います。

</details>

### 4. OS infrastructure support matrix によると、Bottlerocket がサポートされる環境は何ですか？

A. Bare metal と VMware の両方をサポート
B. Bare metal のみ
C. VMware のみ
D. AWS EC2 のみ

<details>
<summary>答えを表示</summary>

**回答: C) VMware のみ**

**解説:**
Bottlerocket は EKS Hybrid Nodes では VMware 環境でのみサポートされています（v1.37.0 以降、x86_64 のみ）。Bare metal server では Ubuntu、RHEL、または Amazon Linux 2023 を使用する必要があります。Bottlerocket は nodeadm を使用せず、設定には settings.toml を使用します。

</details>

### 5. Bottlerocket は他の operating systems と異なり、どの設定ツールと形式を使用しますか？

A. nodeadm (YAML)
B. ansible (INI)
C. govc (TOML)
D. terraform (HCL)

<details>
<summary>答えを表示</summary>

**回答: C) govc (TOML)**

**解説:**
Bottlerocket は nodeadm を使用しません。代わりに、設定には settings.toml ファイルを使用します。govc のデプロイワークフローは、template の clone → user-data の注入 → 電源オンです。対照的に、Ubuntu、RHEL、Amazon Linux 2023 は nodeadm（YAML）を使用します。

</details>

### 6. PKI infrastructure がなく、インターネット接続がある環境で credential provider を選択する場合、どのオプションが推奨されますか？

A. IAM Roles Anywhere
B. SSM Hybrid Activations
C. Kubernetes Service Account
D. OIDC Provider

<details>
<summary>答えを表示</summary>

**回答: B) SSM Hybrid Activations**

**解説:**
Credential provider 選択ガイド:
- PKI infrastructure なし、インターネット利用可: SSM
- 既存の PKI infrastructure あり: IAM Roles Anywhere
- Air-gapped environment: IAM Roles Anywhere
- Custom node names が必要: IAM Roles Anywhere

SSM は、セットアップが簡単で証明書要件がないため、ほとんどの環境で推奨されます。

</details>

### 7. RHEL で nodeadm を使用して containerd をインストールする場合、どのオプションを使用する必要がありますか？

A. `--containerd-source distro`
B. `--containerd-source docker`
C. `--containerd-source eks`
D. `--containerd-version latest`

<details>
<summary>答えを表示</summary>

**回答: B) `--containerd-source docker`**

**解説:**
RHEL では、`--containerd-source docker` オプションを使用する必要があります。distribution のデフォルトソース（distro）は RHEL ではサポートされていません。

```bash
# Correct installation method
sudo nodeadm install 1.31 --credential-provider ssm --containerd-source docker
```

このオプションがないと、インストールは失敗します。

</details>

### 8. VMware から bare metal + EKS Hybrid Nodes へ移行する際のフェーズの正しい順序は何ですか？

A. VMware の廃止 → Workloads のコンテナ化 → Network transition → Parallel infrastructure の構築
B. Workloads のコンテナ化 → Parallel infrastructure の構築 → VMware の廃止 → Network transition
C. Parallel infrastructure の構築 → Workloads のコンテナ化 → Network transition → VMware の廃止
D. Network transition → Parallel infrastructure の構築 → Workloads のコンテナ化 → VMware の廃止

<details>
<summary>答えを表示</summary>

**回答: C) Parallel infrastructure の構築 → Workloads のコンテナ化 → Network transition → VMware の廃止**

**解説:**
VMware → Bare Metal + EKS Hybrid Nodes の移行フェーズ:
1. Phase 1: Parallel Infrastructure の構築（VMware と並行して EKS cluster と hybrid node infrastructure をデプロイ）
2. Phase 2: Workloads のコンテナ化（VM ベースの workloads を containers へ移行）
3. Phase 3: Network Transition（NSX-T から Cilium BGP へ移行）
4. Phase 4: VMware の廃止（すべての workloads が移行されたことを確認後）

</details>

### 9. OpenShift の Route 概念は EKS Hybrid Nodes では何に対応しますか？

A. Service
B. Ingress / Gateway API
C. NetworkPolicy
D. Endpoint

<details>
<summary>答えを表示</summary>

**回答: B) Ingress / Gateway API**

**解説:**
OpenShift から EKS Hybrid Nodes へ移行する際の概念マッピング:

| OpenShift | EKS Hybrid Nodes |
|-----------|-----------------|
| Route | Ingress / Gateway API |
| SCC | PSS (Pod Security Standards) |
| OLM | Helm / EKS Add-ons |
| MachineSet | nodeadm + Ansible |
| ImageStream | ECR |
| BuildConfig | External CI/CD |
| DeploymentConfig | Deployment |

</details>

### 10. Ubuntu 24.04 で containerd の問題により Pods が終了しない場合の解決策は何ですか？

A. SELinux を無効にして再起動する
B. containerd を v1.7.19 以降に更新する、または AppArmor profile を変更して再起動する
C. container runtime を Docker に切り替える
D. cgroup v1 にダウングレードする

<details>
<summary>答えを表示</summary>

**回答: B) containerd を v1.7.19 以降に更新する、または AppArmor profile を変更して再起動する**

**解説:**
Ubuntu 24.04 では containerd v1.7.19 以降が必要です。そうでない場合は AppArmor profile の変更が必要です（Ubuntu bug #2065423）。

```bash
# Check containerd version
containerd --version

# If version is below 1.7.19, modify AppArmor profile
sudo aa-remove-unknown

# Reboot required to apply changes
sudo reboot
```

再起動しないと、Pods が正しく終了しない場合があります。

</details>

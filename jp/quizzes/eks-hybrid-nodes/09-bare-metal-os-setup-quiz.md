# ベアメタルサーバーのOSインストールと移行に関するクイズ

> **最終更新日**: 2026年9月13日

> **関連ドキュメント**: [ガイド](../../eks-hybrid-nodes/09-bare-metal-os-setup.md)

## 選択式問題

<span id="_1-what-is-a-key-benefit-of-running-eks-hybrid-nodes-on-bare-metal-servers"></span>

### 1. Hybrid Nodes でベアメタルを評価する理由として考えられるものは何ですか？

- A) すべてのVMを自動的にコンテナへ変換できる
- B) ハイパーバイザー層をなくせる可能性があり、総コストとワークロード要件を踏まえて評価できる
- C) AWSとの接続なしで運用できる
- D) すべてのソフトウェアライセンスが自動的に解約される

<details>
<summary>解答を表示</summary>

**回答: B) ハイパーバイザー層をなくせる可能性があり、総コストとワークロード要件を踏まえて評価できる**

**解説:**

ハイパーバイザーをなくすとライセンス費用や実行時のオーバーヘッドが変わる可能性はありますが、総コストの低下や性能向上が保証されるわけではありません。コンテナ化、データ移行、可用性、サポート、契約上の義務については、それぞれ別途検討が必要です。ガイドに残されている未検証の過去の価格見積もりから、節約額を推測しないでください。

</details>

<span id="_2-what-are-the-essential-components-required-for-pxe-boot-infrastructure"></span>

### 2. 従来型のPXEブート設計で一般的に使われるコンポーネントは何ですか？

- A) DNSとNFSだけ
- B) DHCP/ProxyDHCPのブート情報とTFTPブートサーバー
- C) FTPとSMTP
- D) LDAPとKerberosだけ

<details>
<summary>解答を表示</summary>

**回答: B) DHCP/ProxyDHCPのブート情報とTFTPブートサーバー**

**解説:**

従来型のPXEでは、通常DHCPのブート情報とTFTPを使います。インストーラーのコンテンツはHTTPで配信できます。また、UEFI HTTPやiPXEを使う設計では別の配信経路を利用する場合があります。pxelinux.0があらゆるUEFI環境で使えるブートローダーというわけではありません。ファームウェアからローダーまでの構成を確認し、プロビジョニング環境を分離してください。共有の未認証サーバーに、外部に漏れてはならないアクティベーションコードや鍵を置かないでください。

</details>

<span id="_3-which-correctly-pairs-ubuntu-s-automated-installation-method-with-rhel-s-automated-installation-method"></span>

### 3. OSの自動インストール方式の組み合わせとして正しいものはどれですか？

- A) Ubuntu: Kickstart、RHEL: Autoinstall
- B) Ubuntu Server: Subiquity Autoinstall YAML、RHEL: Kickstart
- C) Ubuntu: govc、RHEL: TOML
- D) どちらも、未検証の最新版nodeadmをインストーラー内でダウンロードする必要がある

<details>
<summary>解答を表示</summary>

**回答: B) Ubuntu Server: Subiquity Autoinstall YAML、RHEL: Kickstart**

**解説:**

UbuntuのAutoinstall設定はcloud-initで配信できます。RHELではKickstartを使います。選択したインストーラーのバージョンと、ホスト固有のストレージおよびネットワーク設定を検証してください。YAMLパーサーやksvalidatorで検証しても、消去対象のディスクが安全か、インストール後のホストが認証できるかまでは保証されません。

</details>

<span id="_4-according-to-the-os-infrastructure-support-matrix-what-is-bottlerocket-s-supported-environment"></span>

### 4. 確認済みのAWSガイダンスで、EKS Hybrid Nodes向けにサポートされているBottlerocketのデプロイ先はどれですか？

- A) あらゆるベアメタル環境
- B) すべてのハイパーバイザーとアーキテクチャ
- C) x86_64上のサポート対象VMware環境、バージョン1.37.0以降
- D) EC2のみ

<details>
<summary>解答を表示</summary>

**回答: C) x86_64上のサポート対象VMware環境、バージョン1.37.0以降**

**解説:**

これはEKS Hybridのサポート範囲であり、Bottlerocketのすべての製品バリアントに関する説明ではありません。Hybrid Nodesをベアメタルで運用する場合は、サポート対象のUbuntuまたはRHELホストを検討してください。AL2023はオンプレミスの仮想化ゲストでも利用できますが、汎用的なベアメタル向けのサポート経路ではありません。Kubernetesバリアントの提供状況と現在のライフサイクル要件は、別途確認してください。

</details>

<span id="_5-what-configuration-tool-and-format-does-bottlerocket-use-differently-from-other-operating-systems"></span>

### 5. Bottlerocketの設定とgovcの役割を正しく区別している説明はどれですか？

- A) govcはBottlerocket用のTOMLパーサーである
- B) BottlerocketはUbuntuと同じnodeadm YAMLを使う
- C) Bottlerocketは設定やブートストラップ用の入力を使い、govcはVMwareのVMライフサイクルとユーザーデータの配信を管理する
- D) settings.hybrid.ssmは標準でサポートされる設定名前空間である

<details>
<summary>解答を表示</summary>

**回答: C) Bottlerocketは設定やブートストラップ用の入力を使い、govcはVMwareのVMライフサイクルとユーザーデータの配信を管理する**

**解説:**

ガイドに記載された、バージョンに対応するBottlerocketの設定およびブートストラップ手順を使ってください。以前のsettings.hybrid.*の例は無効でした。govcではVMを複製、設定、起動できますが、OS設定を解析するツールではありません。guestinfoとユーザーデータを保護してください。base64エンコードは認証情報を暗号化しません。

</details>

<span id="_6-when-selecting-a-credential-provider-for-an-environment-without-pki-infrastructure-and-with-internet-connectivity-which-option-is-recommended"></span>

### 6. Hybrid Nodesの認証情報プロバイダーと接続性について正しい説明はどれですか？

- A) IAM Roles AnywhereならAWSに接続できなくても無期限に運用できる
- B) どちらのプロバイダーにも必要なAWS APIへの接続が要るが、プライベート接続を使えばパブリックインターネットを経由せずに済む
- C) SSMには必ずパブリックインターネットへの直接接続が必要である
- D) KubernetesのServiceAccountがホストのHybrid認証情報プロバイダーの代わりになる

<details>
<summary>解答を表示</summary>

**回答: B) どちらのプロバイダーにも必要なAWS APIへの接続が要るが、プライベート接続を使えばパブリックインターネットを経由せずに済む**

**解説:**

管理されたPKIがない場合、SSMを使うと証明書管理の作業を減らせることがあります。IAM Roles AnywhereはX.509 IDを使いますが、一時認証情報を取得するためにAWSのCreateSession APIを呼び出します。どちらの方式でも、サポート対象のAPIまたはプライベートエンドポイントへの経路、IDのライフサイクル、EKSの認可が必要です。完全に接続されていない、またはDDILの環境は、EKS Hybridのサポート対象の運用モデルではありません。

</details>

<span id="_7-what-option-must-be-used-when-installing-containerd-with-nodeadm-on-rhel"></span>

### 7. RHELでnodeadmを使う場合、文書化されているcontainerdの取得元オプションはどれですか？

- A) distroのみがサポートされる
- B) docker、またはcontainerdを別途インストールして管理する場合はnone
- C) OSに関係なくeksを指定する
- D) 互換性を確認せずlatestを指定する

<details>
<summary>解答を表示</summary>

**回答: B) docker、またはcontainerdを別途インストールして管理する場合はnone**

**解説:**

RHELではnodeadmのdistro取得元はサポートされません。dockerを指定すると、Dockerが配布する互換性のあるcontainerdパッケージが選ばれます。noneを指定するとインストールは省略されるため、initの前に別途管理するランタイムを用意する必要があります。RHELのインストールでは必ずdockerを指定するという説明では、このサポート対象の選択肢が抜けています。AL2023では取得元に関する制約が異なります。

</details>

<span id="_8-what-is-the-correct-order-of-phases-when-migrating-from-vmware-to-bare-metal-eks-hybrid-nodes"></span>

### 8. 復旧手段を維持できる移行手順はどれですか？

- A) 最初に移行元を廃止する
- B) パイロットを行う前にライセンスを解約する
- C) 移行先を並行して準備し、ワークロードとネットワークを移行・テストし、データと運用を受け入れてから、ロールバック期間の終了後に移行元を廃止する
- D) VMのディスクをコンテナにコピーし、すぐに移行元を消去する

<details>
<summary>解答を表示</summary>

**回答: C) 移行先を並行して準備し、ワークロードとネットワークを移行・テストし、データと運用を受け入れてから、ロールバック期間の終了後に移行元を廃止する**

**解説:**

依存関係を洗い出し、バックアップと復元を計画し、ロールバック用の容量を確保してください。トラフィックを切り替える前に、データの整合性、TLS/DNS、アクセス制御、本番相当のワークロード動作をテストします。VMのコンテナ化だけでも、CSIドライバーのインストールだけでも、状態を持つデータは移行されません。移行元の廃止やライセンスの変更は、合意済みの受け入れ条件と保持方針に従って判断してください。

</details>

<span id="_9-what-does-openshift-s-route-concept-map-to-in-eks-hybrid-nodes"></span>

### 9. OpenShiftのRouteを移行するにはどうすればよいですか？

- A) ほかの変更をせず、Serviceに名前を変える
- B) Ingress/Gateway APIへのマッピングを設計し、選択したコントローラーのTLSとルーティング動作を検証する
- C) すべてのRouteをNetworkPolicyに置き換える
- D) RouteのフィールドをそのままGatewayにコピーする

<details>
<summary>解答を表示</summary>

**回答: B) Ingress/Gateway APIへのマッピングを設計し、選択したコントローラーのTLSとルーティング動作を検証する**

**解説:**

Ingress/Gateway APIは候補となるルーティングインターフェイスであり、自動的に同等の動作を実現するものではありません。該当する場合は、TLSの終端、再暗号化、パススルー、重み付け、アノテーションを引き継いでください。同じ注意は、SCCとPSS/PSA、OLMによる配布、ImageStreamのトリガー、DeploymentConfigのフックにも当てはまります。ECR、Helm、Deploymentに置き換えるだけでは、OpenShiftのすべての動作が自動的に再現されるわけではありません。

</details>

<span id="_10-what-is-the-solution-when-pods-won-t-terminate-on-ubuntu-24-04-due-to-containerd-issues"></span>

### 10. Ubuntu 24.04で確認されているAppArmorとコンテナ終了の問題に対し、適切な対応はどれですか？

- A) すべてのホストで、不明なAppArmorプロファイルをすべて削除する
- B) 実際に該当するパッケージまたはプロファイルの問題を確認し、サポート対象の修正を適用する。変更内容に再起動が必要なら計画的に実施する
- C) すべてのセキュリティ機能を無効にする
- D) Podが終了しない場合は、どのケースでもcontainerd 1.7.19をインストールすれば解決すると考える

<details>
<summary>解答を表示</summary>

**回答: B) 実際に該当するパッケージまたはプロファイルの問題を確認し、サポート対象の修正を適用する。変更内容に再起動が必要なら計画的に実施する**

**解説:**

Bug 2065423では修正がリリースされており、影響を受けるパッケージまたはプロファイルの変更後に再起動が必要なケースが説明されています。ベンダーのパッケージやバックポートの状況と、実際のシグナル拒否ログを確認してください。aa-remove-unknownは、/etc/apparmor.dに存在しないロード済みプロファイルを削除するコマンドであり、対象を指定してプロファイルを編集するものではありません。計画的なノードドレイン、再起動、ワークロード確認を行い、AppArmorへのあらゆる変更で常に再起動が必要だと決めつけないでください。

</details>

### 11. 確認済みのEKS Hybrid料金に一致するコストモデルはどれですか？

- A) すべてのサービスを含む、一律で1 vCPU時間あたり0.01ドルの料金
- B) 報告されたvCPU時間に適用される月ごとの段階料金に、クラスター料金などが別途加算される
- C) 実行中Podが要求したCPUだけに課金される
- D) ワークロードがアイドル状態ならノード料金は発生しない

<details>
<summary>解答を表示</summary>

**回答: B) 報告されたvCPU時間に適用される月ごとの段階料金に、クラスター料金などが別途加算される**

**解説:**

月間576,000 vCPU時間までは1 vCPU時間あたり0.020ドルで、その後は公開されている段階料金が適用されます。集計範囲は、アカウント内のリージョン単位、またはAWS Organizationsの一括請求対象範囲です。報告されたvCPU数、月の日数、クラスターのサポートティア、その他のサービス費用を含めてください。過去の「ノードあたり年間2,803.20ドル」という計算は、未検証で現在の総保有コストを表さない古い前提として残されています。

</details>

### 12. NSX-Tの機能を置き換える際、Cilium BGPを選ぶと何を意味しますか？

- A) NSX-Tのすべての機能が自動的に再現される
- B) BGPは経路交換を担い、オーバーレイ、ファイアウォール、ロードバランシング、ポリシーの要件は個別に対応付ける必要がある
- C) 戻り経路をテストする必要がなくなる
- D) 既存のセッションがすべてそのまま維持される

<details>
<summary>解答を表示</summary>

**回答: B) BGPは経路交換を担い、オーバーレイ、ファイアウォール、ロードバランシング、ポリシーの要件は個別に対応付ける必要がある**

**解説:**

BGPによる経路広告だけでNSXプラットフォーム全体の機能が提供されるわけではありません。経路、オーバーレイ、セキュリティ、ロードバランシングの動作を個別に洗い出し、移行先のアドレス、戻り経路、TLS/DNS、既存および新規の接続をテストしてください。サポート対象の混在CNI構成を選び、ロールバック手段を維持してください。すべてに適用できる一対一の置き換え方法があるわけではありません。

</details>

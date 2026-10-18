# ランディングゾーン、OU、組織制御

> **最終更新日**: 2026年9月13日

## 1. Control Tower ランディングゾーン4.0のベースライン依存関係

マルチアカウント環境を標準化する際、通常は AWS Control Tower が最初の選択肢になります。Control Tower は、マネージドなアカウント作成と組織ベースライン／制御を提供しますが、**ランディングゾーン4.0では複数のベースライン間に有効化順序の依存関係があります。** この依存関係を理解せず OU や IAM の設計を確定すると、作業のやり直しにつながります。

### 有効化の依存関係

```
CentralConfigBaseline
  └─▶ CentralSecurityRolesBaseline
        ├─▶ IdentityCenterBaseline
        ├─▶ BackupAdminBaseline
        └─▶ BackupCentralVaultBaseline
```

`IdentityCenterBaseline`（Identity Center 統合）を使うには、`CentralSecurityRolesBaseline` がすでに有効である必要があります。さらに、それには `CentralConfigBaseline`（AWS Config）が必要です。**無効化は逆の順番で行う必要があります**。SecurityRoles を無効化する前に、右側の IdentityCenter／BackupAdmin／BackupCentralVault をすべて無効にし、その後で初めて Config を無効にできます。

> **適用範囲**: この依存関係は、Control Tower 4.0 が管理する IdentityCenterBaseline に適用されます。IAM Identity Center 自体は AWS Config を必要としません。独立して管理する Identity Center と、Control Tower との統合を区別してください。

ランディングゾーンの Config 統合は、サービス統合アカウントに Config リソースをデプロイします。メンバーアカウントには OU レベルの AWSControlTowerBaseline または ConfigBaseline が必要ですが、1つの OU でこの2つを同時に使うことはできません。このマネージド経路には、ランディングゾーンの Config 統合が必要です。Config を独立してデプロイする場合は、所有権、競合処理、検出的制御のカバレッジを別途設計してください。

<span id="the-security-ou-is-no-longer-freely-designable"></span>

### Security OU の配置とベースラインの適用範囲

以前のランディングゾーンでは、Control Tower が管理する Security OU が作成されていました。**バージョン4.0では作成管理を行わず、サービス統合アカウントを含む共通の親 OU が Security OU として指定されます。** 次のベースライン適用範囲の制約を確認してください。

1. `AWSControlTowerBaseline` と Config Baseline はこの OU に適用できません（`Not Applicable` と表示されますが、これは通常の状態です）。`BackupBaseline` は適用できます。
2. サービス統合アカウント以外のアカウントをこの OU に配置しても、ベースラインリソースは付与されません。
3. Control Tower が Identity Center の Permission Set を自動作成するのは、Logging アカウントと SecurityRoles アカウントだけです。**Config アカウントと Backup アカウントの Permission Set は自分で作成する必要があります。**

サービス統合アカウントと同じ OU に一般アカウントを移動すると、自動登録とは関係なく、有効な制御に drift が生じる場合があります。この制約の対象はその OU です。一般的なセキュリティツールや移行待ちアカウント向けに、別のマネージド OU を検討してください。

> **設計案**: ベースラインの適用範囲を明確にするため、サービス統合アカウントと一般的なセキュリティ運用アカウントを分離します。AWS が特定の OU 名を必須としているわけではありません。

### CentralizedLogging を無効化した場合の動作変更

Control Tower 3.3以前では、CentralizedLogging 統合を無効にすると Organization の CloudTrail だけが停止し、デプロイ済みのリソースは保持されました。**4.0では無効化すると、Logging アカウント内の Config Recorder、Delivery Channel、CloudTrail 関連のスタックインスタンスが実際に削除されます。** その後、Control Tower はそのアカウントを管理しなくなります。

無効化の前に、影響を受けるスタック、記録の欠落、保持済み S3 ログをそれぞれ棚卸ししてください。統合を再度有効にするか、アカウントをマネージド OU に移動すれば管理を戻せますが、収集できなかった期間の復旧可能性は検証が必要です。この動作から、すべての過去ログが削除されるとは限りません。

### Control Tower と内部パイプラインの責任を分ける

どのサービス統合と OU ベースラインを有効にするかに応じて、まず次のどちらの方針を取るかを決める必要があります。

| 方針 | 構成 | トレードオフ |
|---|---|---|
| A. Control Tower による管理 | 依存関係の順に必要な統合を有効にし、OU ごとにベースラインを選択する | 記録範囲とコストをまとめて管理できる一方、運用が中央に集約される |
| B. 明示的な所有権の分割 | Identity Center／Config を独立して管理する範囲と、Control Tower の適用範囲を定義する | 内部でライフサイクル、競合、カバレッジを検証する必要がある |

## 2. 自動登録

ランディングゾーン3.1以降では、アカウントを登録済み OU に移動する前に、ランディングゾーンの設定／API から自動登録を有効にします。そうすると、その OU のベースラインと制御が自動的に適用されます。ただし、自動で処理されない項目もあります。

- **既存の構成競合を解決したり、失敗時の復旧を自動で行ったりするわけではありません。** Config、CloudTrail、SCP、IAM の競合は個別に事前確認する必要があります。
- 登録解除によって、マネージドベースラインのリソースが削除される場合があります。既存のログと根拠が保持されるか、別途確認してください。変更を制限しながらガバナンスを維持する方法は、廃止予定アカウントに対する運用上の選択肢です。すべての OU を登録状態に保つことが AWS の要件というわけではありません。
- 登録は結果整合性モデルに従うため、移動するアカウント数によって数分から数時間かかる場合があります。
- **自動登録では、Service Catalog のプロビジョニング済み製品は作成、変更、終了されません。** Account Factory で作成したアカウントの登録を解除すると、そのプロビジョニング済み製品は管理アカウント上で孤立します。

内部パイプラインが「アカウント移動 → 自動登録 → ワークロードのブートストラップ」を自動化する場合、トリガー条件は移動イベントそのものではなく、「**ベースラインの適用完了を確認済み**」とします。

## 3. 組織ポリシーの種類ごとのクォータ

Organizations がサポートするポリシーの種類は、役割もデフォルトのクォータも異なります。

| ポリシーの種類 | エンティティあたりの最大アタッチ数 | ドキュメントの最大サイズ | 組織全体の最大数 |
|---|---|---|---|
| SCP | 10 | 10,240文字 | 10,000 |
| RCP | 5（`RCPFullAWSAccess` を含む。利用できるのは4） | 5,120文字 | 2,000 |
| 宣言型ポリシー | 10 | 10,000文字 | 1,000 |
| タグポリシー | 10 | 10,000文字 | 1,000 |
| Backup ポリシー | 10 | 10,000文字 | 1,000 |
| Security Hub ポリシー | 10 | 10,000文字 | 1,000 |

重要なのは、**継承されたポリシーはエンティティあたりのアタッチ数上限を消費しない**ことです。この点が SCP の配置戦略に大きく影響します。

### SCP の配置戦略

| 戦略 | 構成 | クォータの観点からの評価 |
|---|---|---|
| Root に集約 | 組織共通の SCP を Root にアタッチし、OU で継承する | 新しいアカウントにも直ちに制御が適用されるが、OU ごとの例外を作りにくい |
| OU ごとに必要な SCP を直接アタッチ | 各 OU が必要とする SCP をすべて直接アタッチし、親 OU への依存を最小限にする | 継承を使わないため、単一 OU がアタッチ数上限10を使い切る場合がある。上限に達した場合はポリシーを統合する必要がある |
| **階層化されたバンドル** | Root には例外のない最小限の SCP だけを置き、残りはバージョン管理した OU ごとのポリシーバンドルと期限付き例外にする | 継承を積極的に使って OU ごとの直接アタッチ上限を節約でき、**クォータの観点から最もスケーラブルな選択肢** |

Git の改訂履歴、デプロイマニフェスト、CloudTrail の変更記録を通じて、ポリシードキュメントとアタッチ一覧をバージョン管理してください。Sid にバージョンを含めるかは任意です。継承された SCP／RCP、リソースポリシー、権限境界では評価範囲が異なります。1回のシミュレーションで実効認可全体が証明されるわけではありません。

追加で確認されている制約:

- **エンティティに SCP が1つでも有効な場合、最後に残った SCP は削除できません。** 「例外 OU には制御を一切置かない」という設計は成立しません。例外 OU にも最小限のベースライン SCP が必要です。
- OU は Root の下に**最大5階層**までネストでき、組織全体では最大**2,000 OU**を作成できます。フラットな構造や浅い機能別ハイブリッド構造は、この上限の影響を受けません。
- RCPFullAWSAccess は、エンティティあたり5つある RCP アタッチ枠のうち1つを消費します。直接アタッチに使える枠が4つでも、継承が妨げられるわけではありません。サポート対象サービス、サービスプリンシパルの例外、明示的 Deny を確認しながら、Root、OU、アカウントの各レベルに制御を配置してください。RCP は機密データ経路を保護できますが、IAM、KMS、リソースポリシーの代わりにはなりません。
- Organizations には**Security Hub ポリシーの種類**もあります。これは Security Hub 設定を組織ポリシーとして一元的にデプロイする方法です。SCP／RCP／宣言型ポリシー／タグポリシーと合わせて確認してください。

### ポリシーの種類ごとの役割（確認済みの事実）

| ポリシーの種類 | 役割 |
|---|---|
| SCP | プリンシパルが持てる最大権限を制限する（権限を付与しない） |
| RCP | メンバーアカウントのサポート対象リソースで利用できる最大権限を制限する（権限を付与しない） |
| 宣言型ポリシー | サポート対象サービスの組織共通ベースライン設定を維持する |
| タグポリシー | タグ標準への準拠を検査し、強制する |
| Control Tower の制御 | OU レベルで予防的／事前対応型／検出的な制御を行う |

覚えておくべき SCP 評価の原則が1つあります。許可リスト方式では、Root から対象アカウントまで**すべてのレベル**で明示的 Allow が必要です。また、どのレベルにある明示的 Deny も、下位レベルの Allow では上書きできません。

## 4. 許可リスト方式と拒否リスト方式

| 方針 | 適した対象 | 運用上の負荷 |
|---|---|---|
| 許可リスト中心 | Sandbox、使用可能なサービスを事前に制限する規制ゾーン | 新しいサービス／API を使う前に、明示的に許可する必要がある |
| **拒否リスト中心** | 一般的な Workload OU（デフォルト） | 新たなサービス／API のリスクを継続的に検出し、Deny カタログを維持する必要がある |

リージョンごとの describe-vpc-endpoint-services の結果とサービスのドキュメントを比較してください。API の一覧だけでは、エンドポイントポリシー、機能、プライベート DNS のサポート全体を確認できません。

## 5. OU の設計案

| 選択肢 | 構成 | メリット | デメリット |
|---|---|---|---|
| 深い階層構造 | Root の下に複数階層を作り、親の制御を子へ継承する | 分類と共有制御を階層で表現しやすい | 上位階層の Deny は広い範囲に影響する。実際の上限は5階層 |
| Root 直下のフラット構造 | 多くの OU を Root の直下に置き、制御を直接アタッチする | OU ごとの影響範囲を把握しやすい | 共有ポリシーの重複／欠落リスクがあり、継承を使わずにアタッチ上限10を消費する |
| **浅い機能別ハイブリッド** | 変更頻度の低い機能別 OU（`Security`、`Infrastructure`）と、ライフサイクル／手続き別 OU（`Workloads/Production`、`Workloads/Non-production`、`Sandbox`、`PolicyStaging`、`Transitional`、`Suspended`）を浅い階層で組み合わせる | 組織図の変更による影響を抑えながら、運用状態を表現できる | 機能分類、ライフサイクル、継承、ポリシーバンドルをまとめて検証する必要がある。前述の Security OU 4.0 の制約を踏まえ、サービス統合アカウントと一般の運用アカウントは別の場所に置くことを検討する |

`Transitional` は、移行チェックのためにアカウントを一時配置できます。`Suspended` は廃止前に変更を制限できます。ライフサイクルごとに、登録、根拠の保持、復旧アクセスを決めてください。インシデント調査の手順が異なる場合は、別の `Quarantine` を使います。

継続的な `Production-Exception` OU と、期限付きの例外ポリシーは区別してください。特定の API やポリシーを限られた期間だけ許可する場合は、標準の Production OU 内で、承認範囲を限定し期限を設定した例外として扱います。標準ベースラインと技術的に両立しない、根本的に異なる長期制御セットをアカウントに適用する場合に限り、独立 OU を作成してください。

## 次のステップ

ランディングゾーンと OU の構造が決まったら、次はアカウントの分割方法と、人／ワークロードに付与する IAM 経路を決めます → [アカウント構造と IAM の境界](./02-account-and-iam.md)

## 参考資料

- [Organizations のクォータ](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_reference_limits.html)
- [Control Tower ランディングゾーン4.0の主な変更点](https://docs.aws.amazon.com/controltower/latest/userguide/key-changes-lz-v4.html)
- [Control Tower の AWS Config 更新（4.0）](https://docs.aws.amazon.com/controltower/latest/userguide/config-updates-v4.html)
- [Control Tower のアカウント自動登録](https://docs.aws.amazon.com/controltower/latest/userguide/account-auto-enrollment.html)
- [ベースラインの種類](https://docs.aws.amazon.com/controltower/latest/userguide/types-of-baselines.html)
- [既存アカウントの登録](https://docs.aws.amazon.com/controltower/latest/userguide/enroll-account.html)
- [SCP の評価](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_evaluation.html)
- [RCP](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_rcps.html)
- [宣言型ポリシー](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_declarative_policies.html)
- [タグポリシー](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_tag-policies.html)
- [Control Tower 制御のリファレンス](https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html)
- [AWS マルチアカウント設計の原則](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/design-principles-for-your-multi-account-strategy.html)
- [AWS 推奨 OU とアカウント](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/recommended-ous-and-accounts.html)

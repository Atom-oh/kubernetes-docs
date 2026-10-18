# 実際のインシデントから学ぶ多層防御とインシデント対応

> **レビューの根拠**: AWS、Kubernetes、Palo Alto Networks、Fortinet の公式ドキュメント、CISA のアラート、NIST SP 800-61r3。公開日と調査日は異なります。
> **最終更新日**: 2026年10月15日

セキュリティ設計では、侵入、横展開、情報流出、復旧までを対象にする必要があります。本章では、境界の防御とインシデント対応を、既存の [EKS セキュリティ](./06-eks-security-best-practices.md)、[NetworkPolicy](./04-network-policies.md)、[ランタイムセキュリティ](./08-runtime-security.md)のガイドに結び付けます。以下の運用基準と手順は、このガイドで提案する設計であり、製品を導入しただけで実現が保証されるものではありません。

## 1. 確認済みのインシデントと設計上の教訓

| 事例と公開日／廃止日 | 一次資料で確認された影響範囲 | 設計への反映 |
|---|---|---|
| ingress-nginx CVE-2025-1974、2025-03-24 | Pod ネットワークから到達できる admission 検証 controller を介した攻撃。過去の修正版は 1.11.5 と 1.12.1 | 外部 WAF に加え、webhook の到達性と controller の Secret 権限を確認する |
| ingress-nginx の廃止、2026-03 | Kubernetes Steering／SRC は 2026-01-29 に、廃止後はセキュリティ更新を終了すると警告 | 保守が継続される実装へ移行する。過去の CVE 修正版を、2026 年の新たな推奨バージョンとして扱わない |
| PAN-OS CVE-2025-0108、2025-02-12 | 管理 Web 認証の回避と、他の攻撃と組み合わせようとする動きが観測された | 管理アクセスを公開アプリケーションの経路から分離する |
| PAN-OS CVE-2026-0322、2026-10-14 | 管理インターフェイスで認証後に root 権限を得る RCE。限定的な悪用を確認。PA-Series、VM-Series、Panorama が影響を受ける | 管理者の認証情報、セッション、管理経路への到達性を保護し、製品ファミリーごとの影響を区別する |
| FortiCloud SSO CVE-2026-24858、CISA KEV 追加日 2026-01-27 | FortiCloud SSO が有効な場合のアカウント間アクセスと、アカウント／VPN の変更。過去の SSO CVE を修正した機器にも及ぶ新たな経路 | 管理上の変更を監査する。SSO を導入しただけでは不十分 |
| FortiGate の永続アクセス、2025-04-10 | SSL-VPN に関連するシンボリックリンクにより、以前の脆弱性を修正した後もファイル読み取りアクセスが残る可能性 | パッチ適用と侵害の除去を別々の完了条件として追跡する |

根拠: [Kubernetes の CVE アラート][S01]、[廃止に関する声明][S02]、[PAN-OS 2025 年のアドバイザリ][S04]、[2026 年のアドバイザリ][S03]、[CISA KEV データ][S06]、[Fortinet の永続化に関する分析][S07]。Fortinet は 2026 年1月28日に SSO の分析を訂正しました。**この問題は、サードパーティ製 SAML IdP と FortiAuthenticator には影響しません。** 当初の「すべての SAML が対象」という広い説明を繰り返さないでください。[S05]

CISA は CVE-2026-0322 を 2026-10-14 に、CVE-2026-24858 を 2026-01-27 に KEV へ追加しました。優先順位を決める際は、KEV への掲載とベンダーによる影響範囲をあわせて確認してください。米国連邦機関向けの修正期限を、すべての組織に適用される法的義務として一般化しないでください。[S06]

脆弱性が公表されたことだけでは、すべてのインストール環境が侵害されたとは言えません。製品、バージョン系統、hotfix、利用中の機能、公開状況、侵害の証拠を確認してください。PAN-OS の 2026 年アドバイザリの対象外には Cloud NGFW と Prisma Access が含まれますが、この除外を他のすべての CVE に当てはめないでください。パッチ提供予定日は、実際にリリースされたことの確認とは異なります。[S03]

## 2. 制御の責任範囲と補完策

| 制御 | 主な対象範囲 | 補完する制御 |
|---|---|---|
| WAF | 関連付けられたリソースへの HTTP(S) リクエストと、設定した照合条件 | アプリケーションの認証／認可、入力検証、アップロード検査、オリジン制限 |
| NGFW／IPS | 通過するネットワークセッションと、設定済みのセキュリティプロファイル | TLS の可視性、管理経路の保護、パッチ適用、双方向のルーティング |
| GWLB／GWLBE | GENEVE 対応アプライアンスの挿入とフローの分配 | アプライアンスの検査ポリシー、セッション処理、処理能力、復旧 |
| Kubernetes NetworkPolicy | 対応 CNI が適用する Pod 間の接続制御 | hostNetwork／node／ローカル経路の確認とサービス認証 |
| mTLS／SPIFFE | ピアの ID と通信経路の保護 | サービス認可、リクエスト検証、アクセス記録 |
| イメージ／admission policy | デプロイするイメージとワークロードの設定 | 実行時検知、パッチ適用、シークレット管理 |

[WAF リソースの一覧][S09]と[GWLB のドキュメント][S24]で、それぞれの対象範囲を確認できます。NetworkPolicy の適用には、ポリシーを強制する CNI プラグインが必要です。NetworkPolicy API は TLS を提供せず、すべての接続を共通ゲートウェイ経由にするものでもありません。[S34]

**アプライアンスを設置した証拠と、リクエストが検査された証拠は別です。** 次の受け入れ基準で確認することを提案します。

1. **経路**: リクエストは実際に指定した WAF またはファイアウォールを通過したか。
2. **ポリシー**: どのルール、シグネチャ、復号ポリシー、例外が適用されたか。
3. **結果**: 許可／拒否の判断とアプリケーションの動作は期待どおりか。

## 3. まず通信経路を棚卸しする

この脅威モデルのテンプレートに、実際の主体、CIDR、リソース ID を記入してください。観測していない経路は未検証として記録します。

| 通信フロー | 調査する入口／出口の経路 | 制御と証拠 |
|---|---|---|
| 利用者 → Web／API | CloudFront、ALB、その他のロードバランサー／ドメイン／NodePort | Web ACL の関連付け、正当なリクエスト、影響のない遮断テスト、オリジンへの直接アクセス結果 |
| 運用者 → 管理面 | PAN-OS／FortiGate、Panorama／FortiManager、EKS API、GitOps | 信頼できる管理経路、認証、管理者／ポリシーの変更記録 |
| API server → webhook | control plane と admission Service | API server のアクセス、通常のワークロード制限、証明書、RBAC |
| Pod → 外部 | node SNAT、NAT Gateway、TGW、IPv4／IPv6、プロキシ | 許可／拒否した宛先、変換前後のアドレス、ファイアウォールのセッション |
| Pod → Pod／データベース | 同じ node、同じ VPC、別の VPC | CNI ポリシー、データベースの SG、サービス認可、双方向テスト |
| Pod → AWS service | PrivateLink、S3／DynamoDB gateway endpoint、public endpoint | IAM／リソース／endpoint policy と、観測した接続経路 |
| CI/CD → cluster | OIDC role、registry、GitOps controller | 署名／digest、最小権限、監査対象の変更 |

TGW による集中検査の対象は、**TGW 経由でルーティングされる通信**です。同じ node 上の Pod 間通信、VPC 内の経路、peering、独立した endpoint 経路まで含まれるとは限りません。ルーティングと CNI の両方を確認してください。[S29] [S30] [S34]

## 4. アーキテクチャの責任分担

公開アプリケーションには[WAF とオリジン保護](./14-waf-edge-api-security.md)を使います。送信通信と VPC 間の検査には[NGFW の設計](./15-ngfw-paloalto-fortinet.md)と[GWLB／GENEVE](./16-gwlb-geneve-inspection.md)を使います。VPC 内では、これらの制御を NetworkPolicy、セキュリティグループ、mTLS と組み合わせます。

責任分担の例:

| 担当 | 提案する責任 | 変更時の確認事項 |
|---|---|---|
| アプリケーションチーム | 認証、認可、スキーマ、アップロード | WAF の例外がある場合もアプリケーションを保護する |
| プラットフォームチーム | EKS、controller、CNI、admission、GitOps | webhook、Pod、AWS 権限の境界 |
| ネットワークチーム | TGW、VPC route、GWLBE、NAT、アプライアンスの処理能力 | リクエスト／応答経路、AZ 障害、迂回経路 |
| セキュリティチーム | 検査ポリシー、シグネチャ、調査、例外の期限 | 遮断の有効性、検知の証拠、復旧 |
| インシデント指揮者 | 封じ込め、証拠、復旧の判断 | 業務への影響、認証情報の交換、再テスト |

既定の経路を変更する権限と、検査例外を認める権限を分けてください。緊急迂回の範囲、理由、有効期限、復旧の担当者を記録します。これは組織上の提案であり、実際の AWS アカウントを調査して得た所見ではありません。

## 5. 検知の証拠

| 挙動 | 相関させる情報 | 情報源が1つだけの場合の限界 |
|---|---|---|
| 管理者のログイン後にアカウント／ポリシーを作成 | アプライアンスの認証／設定監査、中央管理システム、管理経路の記録 | アプライアンスが侵害されると、ローカル記録の信頼性が低下する場合がある |
| WAF の削除／例外、または検査の迂回 | AWS の変更、Web ACL の関連付け、route／SG の変更、アプリケーションアクセス | 遮断がゼロでも、制御が正常に機能している証明にはならない |
| controller の侵害後に Secret へアクセス | Kubernetes audit、controller RBAC、実行時の挙動 | Web access log では webhook を介するすべての攻撃を捉えられない |
| 情報流出の疑い | CNI の観測情報、ファイアウォールのセッション、変換前のアドレス、アプリケーション／AWS API の監査記録 | VPC Flow Logs にアプリケーションの payload や認可結果は含まれない |
| パッチ適用後の再侵入 | 管理者／VPN アカウント、設定差分、認証情報の利用状況 | バージョン番号だけでは永続アクセスの除去を証明できない |

Fortinet の資料では、管理者の作成と設定変更が記録されています。EKS の資料によると、Flow Logs はメタデータを記録するもので、Pod のアドレスが変わると通信元の特定が難しくなる場合があります。[S05] [S33]

GuardDuty の脅威検知、Inspector の脆弱性管理、Security Hub のエクスポージャー検出／相関、CSPM の設定確認は、それぞれ目的が異なります。利用中の各サービスの対象範囲を確認し、ネットワーク、アプライアンス、アプリケーションの記録を時刻とリソース ID で相関させてください。サービスの詳細は[EKS セキュリティの実践](./06-eks-security-best-practices.md)を参照してください。

## 6. 侵害が疑われる場合の対応

NIST SP 800-61r3 は、検知、対応、復旧を、より広いリスク管理と結び付けています。以下のアプライアンス／EKS の手順は、このガイドで提案する運用手順です。[S08]

1. **分類する**: 対象製品、バージョン系統、機能、公開状況、調査範囲を確認します。脆弱性のある資産と、侵害の証拠がある資産を区別します。
2. **証拠を保全する**: UTC 時刻、設定 revision、管理者／VPN アカウント、認証／system／threat log、クラウド上の変更を記録します。封じ込めを遅らせると被害が増える場合は、証拠を保全しながら封じ込めを進め、その判断も記録してください。
3. **封じ込める**: 影響を受けた管理経路とワークロードを制限しつつ、control plane、DNS、ログ収集、承認済みの復旧経路が依存するものを把握します。
4. **不正なアクセスを除去する**: 不正なアカウント、設定、ファイルシステムの変更についてベンダーの手順に従います。必要に応じて、検証済みイメージとクリーンな設定から再構築します。疑わしい設定をそのまま復元しないでください。
5. **シークレットを交換する**: 露出状況に応じて、管理者／VPN／LDAP／AD／API／クラウドの認証情報、証明書、セッションを確認します。ファイアウォールのパスワードを1つ変更するだけでは不十分です。
6. **復旧を実証する**: 管理アクセスが拒否されること、正当な業務機能、影響のない遮断テスト、外向き通信、AZ 障害、ログ収集を再テストします。
7. **改善する**: 原因、露出期間、例外、検知の遅延、変更権限を分析し、制御と playbook を更新します。

Fortinet は侵害の痕跡が確認された場合、システムと設定を侵害されたものとして扱い、設定を復元または監査し、関連する認証情報を交換するよう推奨しています。永続化に関する分析でも、設定の確認が必要です。[S05] [S07]

## 7. 導入の順序と完了基準

以下は状況に応じて調整する実行計画であり、ベンダー SLA やインシデント修正期限ではありません。

| 段階 | 作業 | 完了を示す証拠 |
|---|---|---|
| 最初に実施 | 公開された管理経路、廃止された ingress、悪用が確認された CVE、オリジン迂回を棚卸しする | 資産、公開範囲、影響するバージョン系統、担当者の記録と是正措置 |
| Stage 1 | WAF のログ／ルール、管理者変更の検知、webhook／Pod の境界を検証する | 許可／拒否の結果と、有効なポリシー ID |
| Stage 2 | 送信／VPC 間の検査、Palo Alto／Fortinet の PoC、双方向の GWLB 経路を検証する | リクエスト／応答の記録、NAT の位置、障害試験 |
| Stage 3 | 処理能力、アップグレード、復旧、例外のライフサイクルを確認する | SLO の測定結果、復旧訓練、レビュー済みの変更手順 |

遮断率だけを指標にしないでください。**検査経路のカバー率、オリジン迂回テスト、不正な管理者変更、欠落したログ、復旧時間、正当な通信のエラー**をあわせて追跡します。実測するまでは、性能や可用性の数値を断定しないでください。

## 続けて学ぶ

- [WAF、Edge、API のセキュリティ](./14-waf-edge-api-security.md)
- [Palo Alto と Fortinet の NGFW](./15-ngfw-paloalto-fortinet.md)
- [GWLB と GENEVE の検査](./16-gwlb-geneve-inspection.md)
- [章のクイズ](../quizzes/security/13-defense-in-depth-incident-response-quiz.md)

## 参考資料と調査根拠

一次資料は 2026-10-15 に確認しました。変更前に、対象製品／バージョン系統のアドバイザリと制約を再確認してください。

- [S01: Kubernetes: CVE-2025-1974][S01]
- [S02: Kubernetes: ingress-nginx の廃止に関する声明][S02]
- [S03: Palo Alto: CVE-2026-0322][S03]
- [S04: Palo Alto: CVE-2025-0108][S04]
- [S05: Fortinet: FortiOS における SSO 悪用の分析][S05]
- [S06: CISA: Known Exploited Vulnerabilities Catalog][S06]
- [S07: Fortinet: 脅威アクターの活動分析][S07]
- [S08: NIST SP 800-61r3][S08]
- [S09: AWS WAF: Web ACL の関連付け][S09]
- [S24: AWS: Gateway Load Balancer][S24]
- [S29: AWS: GWLB と TGW による集中検査][S29]
- [S30: AWS: NAT Gateway のシナリオ][S30]
- [S33: EKS: ネットワークセキュリティ][S33]
- [S34: Kubernetes: NetworkPolicy][S34]

[S01]: https://kubernetes.io/blog/2025/03/24/ingress-nginx-cve-2025-1974/
[S02]: https://kubernetes.io/blog/2026/01/29/ingress-nginx-statement/
[S03]: https://security.paloaltonetworks.com/CVE-2026-0322
[S04]: https://security.paloaltonetworks.com/CVE-2025-0108
[S05]: https://www.fortinet.com/blog/psirt-blogs/analysis-of-sso-abuse-on-fortios
[S06]: https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
[S07]: https://www.fortinet.com/blog/psirt-blogs/analysis-of-threat-actor-activity
[S08]: https://csrc.nist.gov/pubs/sp/800/61/r3/final
[S09]: https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-associating-aws-resource.html
[S24]: https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/gateway-load-balancers.html
[S29]: https://aws.amazon.com/blogs/networking-and-content-delivery/centralized-inspection-architecture-with-aws-gateway-load-balancer-and-aws-transit-gateway/
[S30]: https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-scenarios.html
[S33]: https://docs.aws.amazon.com/eks/latest/best-practices/network-security.html
[S34]: https://kubernetes.io/docs/concepts/services-networking/network-policies/

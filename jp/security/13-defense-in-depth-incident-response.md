# 実際のインシデントから学ぶ多層防御とインシデント対応

> **レビュー根拠**: AWS、Kubernetes、Palo Alto Networks、Fortinet の公式ドキュメント、CISA のアラート、NIST SP 800-61r3。公開日と調査日は異なります。
> **最終更新**: 2026年10月15日

セキュリティ設計では、侵入、横展開、持ち出し、復旧を扱う必要があります。この章では、境界の制御とインシデント対応を、既存の [EKS セキュリティ](./06-eks-security-best-practices.md)、[NetworkPolicy](./04-network-policies.md)、[ランタイムセキュリティ](./08-runtime-security.md)のガイドと関連付けます。以下の運用基準と順序は、このガイドに対する**設計提案**であり、製品を導入しただけで保証されるものではありません。

## 1. 検証済みのインシデントと設計上の教訓

| 事例と公開／終了日 | 一次資料で確認された範囲 | 設計への影響 |
|---|---|---|
| ingress-nginx CVE-2025-1974、2025-03-24 | Pod network から到達可能な validating admission controller を介した攻撃。過去の修正バージョンは1.11.5と1.12.1 | 外部 WAF 対策とあわせて webhook 到達性と controller の Secret 権限を確認する |
| ingress-nginx の終了、2026-03 | Kubernetes Steering／SRC は2026-01-29に、廃止後はセキュリティ更新が停止すると警告 | 保守される実装に移行する。過去の CVE 修正バージョンを、2026年時点の新たな推奨バージョンとして扱わない |
| PAN-OS CVE-2025-0108、2025-02-12 | 管理 web interface の認証 bypass と、組み合わせて悪用を試みた事例 | 管理アクセスを公開アプリケーションの経路から分離する |
| PAN-OS CVE-2026-0322、2026-10-14 | 認証済みの管理 interface で root 権限の RCE。限定的な悪用を確認。PA-Series、VM-Series、Panorama が影響を受ける | 管理者の認証情報、session、管理経路への到達性を保護し、製品ファミリーの違いを区別する |
| FortiCloud SSO CVE-2026-24858、CISA KEV 追加日 2026-01-27 | FortiCloud SSO 有効時のアカウント間アクセス、アカウント／VPN 変更、過去の SSO CVE を修正した機器にも影響する新たな経路 | 管理上の変更を監査する。SSO を導入しただけでは不十分 |
| FortiGate の永続アクセス、2025-04-10 | SSL-VPN 関連の symbolic link により、過去の脆弱性の修正後もファイル読み取りアクセスが残る可能性 | patch 適用と侵害除去を別々の完了条件として追跡する |

根拠: [Kubernetes CVE alert][S01]、[廃止に関する声明][S02]、[PAN-OS 2025 advisory][S04]、[2026 advisory][S03]、[CISA KEV data][S06]、[Fortinet の永続化に関する分析][S07]。Fortinet は2026年1月28日に SSO 分析を訂正しています。**この問題の影響を受けるのは third-party SAML IdP と FortiAuthenticator ではありません。** 当初の「すべての SAML」という広い説明を繰り返さないでください。[S05]

CISA は2026年10月14日に CVE-2026-0322、2026年1月27日に CVE-2026-24858 を KEV に追加しました。優先順位を決めるときは、KEV の掲載状況をベンダーの影響情報とあわせて確認してください。米国連邦機関向けの修正期限を、あらゆる組織に適用される法的義務として一般化しないでください。[S06]

脆弱性の公表だけでは、すべてのインストール環境が侵害されたとは言えません。製品、branch、hotfix、有効な機能、外部公開状況、証拠を確認してください。PAN-OS 2026 advisory の対象外には Cloud NGFW と Prisma Access が含まれますが、この除外をすべての CVE に当てはめないでください。patch の提供予定日は、リリース済みであることの確認とは異なります。[S03]

## 2. 制御の責任範囲と残る対策

| 制御 | 主な対象 | 補完する制御 |
|---|---|---|
| WAF | 関連付けられた resource への HTTP(S) request と、設定した match | アプリケーション認証／認可、入力検証、upload 検査、origin 制限 |
| NGFW／IPS | 通過する network session と設定済みの security profile | TLS の可視性、管理経路の保護、patch 適用、双方向 routing |
| GWLB／GWLBE | GENEVE 対応 appliance の挿入と flow 分配 | appliance の検査 policy、session 処理、capacity、復旧 |
| Kubernetes NetworkPolicy | 対応 CNI が適用する Pod 接続制御 | hostNetwork／node／ローカル経路の確認と service 認証 |
| mTLS／SPIFFE | peer identity と transport の保護 | service 認可、request 検証、access record |
| Image／admission policy | デプロイ対象 image と workload 設定 | runtime 検知、patch 適用、secret 管理 |

[WAF resource の一覧][S09]と[GWLB のドキュメント][S24]で、それぞれの適用範囲を確認できます。NetworkPolicy は対応する enforcement plugin が必要です。その API は TLS を提供せず、すべての接続に共通 gateway の通過を強制するものでもありません。[S34]

**Appliance が設置されている証拠と、request が検査された証拠は異なります。** 提案する受け入れ基準では、次を確認します。

1. **経路**: request は実際に指定した WAF または firewall を通過したか。
2. **Policy**: どの rule、signature、decryption policy、例外が適用されたか。
3. **結果**: allow／deny の判断とアプリケーションの動作は期待どおりか。

## 3. まず通信を棚卸しする

この threat model の template に実際の principal、CIDR、resource ID を記入し、観測していない経路は未検証として記録します。

| 通信 | 調べる入口／出口の経路 | 制御と証拠 |
|---|---|---|
| User → web／API | CloudFront、ALB、その他の load balancer／domain／NodePort | Web ACL の関連付け、正当な request、悪影響のない blocking canary、origin への直接アクセス結果 |
| Operator → management | PAN-OS／FortiGate、Panorama／FortiManager、EKS API、GitOps | 信頼された管理経路、認証、管理者／policy の変更記録 |
| API server → webhook | Control plane と admission Service | API server access、通常の workload 制限、証明書、RBAC |
| Pod → external | Node SNAT、NAT Gateway、TGW、IPv4／IPv6、proxy | 許可／拒否された宛先、変換前後の address、firewall session |
| Pod → Pod／database | 同じ node、同じ VPC、別 VPC | CNI policy、database SG、service 認可、双方向テスト |
| Pod → AWS service | PrivateLink、S3／DynamoDB gateway endpoint、public endpoint | IAM／resource／endpoint policy と観測した接続経路 |
| CI/CD → cluster | OIDC role、registry、GitOps controller | 署名／digest、最小権限、監査された変更 |

中央 TGW の検査範囲は、**TGW 経由で routing された通信**です。同一 node 内の Pod 通信、VPC 内部の route、peering、個別の endpoint 経路まで含むとは限りません。routing と CNI を組み合わせて確認してください。[S29] [S30] [S34]

## 4. アーキテクチャの責任分担

公開アプリケーションには[WAF と origin 保護](./14-waf-edge-api-security.md)を使います。送信通信と VPC 間の検査には[NGFW 設計](./15-ngfw-paloalto-fortinet.md)と[GWLB／GENEVE](./16-gwlb-geneve-inspection.md)を使います。VPC 内では、これらの制御を NetworkPolicy、security group、mTLS に結び付けます。

責任分担の例:

| 担当 | 提案する責任 | 変更時の確認 |
|---|---|---|
| アプリケーションチーム | 認証、認可、schema、upload | WAF 例外の背後でのアプリケーション保護 |
| Platform チーム | EKS、controller、CNI、admission、GitOps | Webhook、Pod、AWS permission の境界 |
| Network チーム | TGW、VPC route、GWLBE、NAT、appliance capacity | Request／response 経路、AZ 障害、bypass |
| Security チーム | 検査 policy、signature、調査、例外期限 | blocking の有効性、検知証拠、復旧 |
| Incident commander | 封じ込め、証拠、復旧判断 | 業務影響、認証情報の交換、再テスト |

既定経路を変更する権限と、検査例外を許可する権限を分けます。緊急 bypass の範囲、理由、期限、復旧担当者を記録してください。これは組織上の提案であり、実際の AWS account を調査した結果ではありません。

## 5. 検知の証拠

| 挙動 | 相関させる情報 | 1つの情報源だけでは分からないこと |
|---|---|---|
| 管理者の login 後に account／policy を作成 | Appliance の認証／設定監査、中央 manager、管理経路の記録 | Appliance が侵害されると、ローカル記録の信頼性が下がる場合がある |
| WAF の削除／例外、または検査 bypass | AWS の変更、Web ACL の関連付け、route／SG の変更、アプリケーション access | block がゼロでも正常に適用されているとは言えない |
| Controller の侵害後に Secret にアクセス | Kubernetes audit、controller RBAC、runtime の挙動 | Web access log ではすべての webhook 攻撃を把握できない |
| 持ち出しの疑い | CNI の観測情報、firewall session、変換前の address、アプリケーション／AWS API audit | VPC Flow Logs には application payload や認可結果が含まれない |
| patch 適用後の再侵入 | 管理者／VPN account、設定差分、認証情報の利用 | version 番号だけでは永続アクセスが除去されたと証明できない |

Fortinet は管理者の作成と設定変更を記録します。EKS の説明では、Flow Logs は metadata であり、Pod address の変更により通信元の特定が難しい場合があるとされています。[S05] [S33]

GuardDuty による脅威検知、Inspector による脆弱性管理、Security Hub による exposure／相関、CSPM の設定確認は、それぞれ目的が異なります。すでに利用している service の対象範囲を確認し、network、appliance、application の記録を時刻と resource identity で相関してください。各 service の詳細は[EKS セキュリティの実践](./06-eks-security-best-practices.md)を参照してください。

## 6. 侵害が疑われる場合の対応

NIST SP 800-61r3 は、検知、対応、復旧をより広い risk management と結び付けています。以下の appliance／EKS 手順は、このガイドの運用提案です。[S08]

1. **分類**: 対象製品、branch、機能、公開状況、調査範囲を確認します。脆弱性のある資産と、侵害の証拠がある資産を分けます。
2. **証拠の保全**: UTC 時刻、設定 revision、管理者／VPN account、認証／system／threat log、cloud の変更を記録します。封じ込めを遅らせることで被害が増える場合は保全と並行して封じ込め、判断を記録してください。
3. **封じ込め**: 影響を受けた管理経路と workload を制限しつつ、control plane、DNS、logging、承認済み復旧経路の依存関係を把握します。
4. **アクセスの除去**: 不正な account、設定、filesystem の変更についてベンダー手順に従います。必要に応じて検証済み image とクリーンな設定から再構築します。疑わしい設定をそのまま復元しないでください。
5. **Secret の交換**: 露出状況に応じて、管理者／VPN／LDAP／AD／API／cloud の認証情報、証明書、session を確認します。firewall の password を1つ変更するだけでは不十分です。
6. **復旧の実証**: 管理 access の拒否、正当な業務機能、悪影響のない blocking canary、egress、AZ 障害、log 収集を再テストします。
7. **改善**: 原因、露出期間、例外、検知の遅延、変更権限を分析し、制御と playbook を更新します。

Fortinet は侵害の痕跡が確認された場合、system／設定が侵害されたものとして扱い、設定を復元または監査し、関連する認証情報を交換するよう推奨しています。また、永続化の分析でも設定の確認が必要です。[S05] [S07]

## 7. 導入順序と完了基準

以下は調整可能な実行計画であり、ベンダー SLA やインシデント修正期限ではありません。

| 段階 | 作業 | 完了を示す証拠 |
|---|---|---|
| 最初に行うこと | 公開された管理経路、廃止された ingress、悪用が確認された CVE、origin bypass を棚卸し | 資産／公開範囲／影響 branch／担当者の記録と是正措置 |
| Stage 1 | WAF logging／rule、管理者変更の検知、webhook／Pod 境界を検証 | allow／deny の結果と有効な policy ID |
| Stage 2 | outbound／VPC 間検査、Palo Alto／Fortinet PoC、対称な GWLB 経路 | request／response capture、NAT の位置、障害試験 |
| Stage 3 | capacity、アップグレード、復旧、例外のライフサイクル | SLO の測定、復旧訓練、レビュー済み変更手順 |

blocking の割合だけを指標にしないでください。**検査経路の coverage、origin bypass のテスト、不正な管理者変更、欠損 log、復旧時間、正当な通信の error**をあわせて追跡します。実測するまでは性能や可用性の数値を断定しないでください。

## 続けて学ぶ

- [WAF、Edge、API セキュリティ](./14-waf-edge-api-security.md)
- [Palo Alto と Fortinet の NGFW](./15-ngfw-paloalto-fortinet.md)
- [GWLB と GENEVE の検査](./16-gwlb-geneve-inspection.md)
- [章のクイズ](../quizzes/security/13-defense-in-depth-incident-response-quiz.md)

## 参考資料と調査根拠

一次資料は2026年10月15日に確認しました。変更前に、選択した製品／branch の advisory と制約を再確認してください。

- [S01: Kubernetes: CVE-2025-1974][S01]
- [S02: Kubernetes: ingress-nginx 廃止に関する声明][S02]
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
- [S33: EKS: Network security][S33]
- [S34: Kubernetes: Network Policy][S34]

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

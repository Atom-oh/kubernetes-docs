# Istio

> **最終更新日**: 2026年10月26日

Amazon EKSでIstio Service Meshを活用するための実践ガイドです。

### 2026年10月のセキュリティ更新: 1.31.3、1.30.7、1.29.10

2026年10月22日、[ISTIO-SECURITY-2026-008](https://istio.io/latest/news/security/istio-security-2026-008/)（CVE-2026-111943）に対するセキュリティパッチリリースとして、**1.31.3**、**1.30.7**、**1.29.10**が公開されました。最後の1.29.10は、1.29が2026年10月15日にサポート終了を迎えた後の例外的なリリースです。2026年10月20日、eMudhraの中間CA証明書8つの秘密鍵が漏えいし、侵害されたことが公表されました。Envoy、Go、ztunnelはCertificate Transparencyを強制しないため、これらの鍵を持つ者は、Istioイメージに含まれる公開CAバンドルによって信頼される任意のドメインの証明書を発行できる可能性がありました。パッチでは、侵害された中間証明書をイメージのCAバンドルから削除し、1.30/1.31のistiod、`istioctl`、`pilot-agent`をGo 1.26.10でビルドします。このバージョンは、侵害された鍵を含む証明書チェーンを拒否します。また、ztunnelの`rustls-webpki`も更新します。システムCAバンドルを信頼する構成は影響を受ける可能性があります。たとえば、`caCertificates`を指定しない`tls.mode: SIMPLE`の`DestinationRule`や、`RequestAuthentication`の`jwksUri`フェッチが該当します。Istio自体のメッシュmTLS証明書は影響を受けません。同日、Istio 1.32.0-beta.0も公開されました。

### 2026年10月のレビュー: サポート対象リリース

Istio 1.31.0はGAであり、[リリース告知](https://istio.io/latest/news/releases/1.31.x/announcing-1.31/)は2026年8月31日に公開されました。現在のパッチバージョンは**1.31.3**で、10月22日に公開されました（上記の「2026年10月のセキュリティ更新」を参照）。10月15日に公開された1.31.2パッチには、[ISTIO-SECURITY-2026-007](https://istio.io/latest/news/security/istio-security-2026-007/)のセキュリティ修正が含まれています（[リリース告知](https://istio.io/latest/news/releases/1.31.x/announcing-1.31.2/)）。それより前のパッチである1.31.1は9月21日に公開されました。その[リリース告知](https://istio.io/latest/news/releases/1.31.x/announcing-1.31.1/)には、未解決の`BackendTLSPolicy` CA参照がプレーンテキストのバックエンド接続にフォールバックするのを防ぐ修正が記載されています。

このガイドの新規インストール用コマンドでは1.31.2を使用します。公開されているIstio 1.31のKubernetesサポート範囲は1.32～1.37です。EKSの標準サポート対象は現在1.34～1.37です。標準サポートの重複範囲は1.34～1.37です。EKSの延長サポート対象バージョン（1.31～1.33）のうち、1.32と1.33もIstio 1.31のサポート範囲内です。インストール前に、[Istioのサポートマトリクス](https://istio.io/latest/docs/releases/supported-releases/)と[EKSのバージョンライフサイクル](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)を再確認してください。

このレビュー時点では、Istio 1.30と1.29は引き続きサポート対象としてマトリクスに掲載されています。1.29のサポート終了日は、予定では2026年10月12日と記載されています。インストールまたはアップグレードの前に、ステータスを確認してください。これらのブランチを使用している既存のインストール環境では、Envoyの脆弱性、BackendTLSPolicyのフェイルオープン、EnvoyFilterによるコントロールプレーンのサービス拒否を対象とする[ISTIO-SECURITY-2026-006](https://istio.io/latest/news/security/istio-security-2026-006/)への対応として、少なくとも1.30.4または1.29.7が必要です。10月15日に公開された[ISTIO-SECURITY-2026-007](https://istio.io/latest/news/security/istio-security-2026-007/)は、1.31.0～1.31.1、1.30.0～1.30.5、1.29.0～1.29.8に影響します。既知のCVEがないバージョンとしてマトリクスに最初に掲載されているのは、1.31.2、1.30.6、1.29.9です。Istio 1.28はサポート対象外です。Istio 1.31のチャートでは`https://blob.istio.io/istio-release/charts`を使用します。以前のGoogleホストのリポジトリには、新しいリリースは追加されません。

### 2026年9月の更新: 1.31.1、1.30.5、1.29.8のパッチリリース

2026年9月21日、サポート対象の3つのブランチすべてに対するパッチリリースとして、[1.31.1](https://istio.io/latest/news/releases/1.31.x/announcing-1.31.1/)、1.30.5、1.29.8が公開されました。1.31.1には、セキュリティ修正[GHSA-qm8v-g4f9-qhjx](https://github.com/istio/istio/security/advisories/GHSA-qm8v-g4f9-qhjx)（CVSS 6.8、中程度）が含まれています。CA参照を解決できない場合、`BackendTLSPolicy`がサイドカープロキシ上でプレーンテキストにフェイルオープンします。その他の修正には、ambientモードのCNIノードエージェントで自動検出されたiptablesバックエンド（legacyとnft）がエージェントの再起動後に切り替わる問題、`AuthorizationPolicies`の数に応じてistiodのCPU使用率が増加する問題、リモートクラスターの認証情報をローテーションする際にambientマルチクラスター環境でメモリリークが発生する問題への対応が含まれます。新規インストール環境と既存の1.31環境は、1.31.1に更新してください。

## 目次

1. [本当にService Meshが必要ですか？](#do-you-really-need-a-service-mesh)
2. [インストールと初期設定](01-installation.md)
3. [基本概念](02-basic-concepts.md)
4. [アーキテクチャ](03-architecture.md)
5. [AWSとの統合](04-aws-integration.md)
6. [用語集](glossary.md)
7. [トラフィック管理](traffic-management/README.md)
8. [セキュリティ](security/README.md)
9. [可観測性](observability/README.md)
10. [レジリエンス](resilience/README.md)
11. [応用](advanced/README.md)
12. [トラブルシューティング](troubleshooting/common-errors.md)
13. [ベストプラクティス](best-practices.md)
14. [代替ソリューションの比較](comparison/README.md)

## Istioとは？

Istioは、マイクロサービスの接続、保護、制御、可観測性を実現するオープンソースのService Meshプラットフォームです。複雑なマイクロサービスアーキテクチャにおけるサービス間通信を管理し、トラフィック制御、セキュリティ、可観測性を提供します。

### Service Meshの概念

<div align="center"><img src="https://istio.io/latest/img/service-mesh.svg" alt="Istio Service Mesh" width="800"></div>

Service Meshは、マイクロサービス間の通信を管理するインフラストラクチャ層です。IstioはEnvoyサイドカーとambientモード（ノードレベルのztunnelと、必要に応じて使用するL7 waypoint）をサポートします。プロキシはメッシュに登録されたトラフィックを処理します。対象外のトラフィックやサポートされていないプロトコルは、その対象には含まれません。これにより、アプリケーションコードを変更せずに次の機能を利用できます。

* **トラフィックルーティング**: インテリジェントルーティング、負荷分散、カナリアリリース
* **セキュリティ**: 自動mTLS、認証、認可
* **可観測性**: メトリクス、ログ、分散トレーシング
* **レジリエンス**: サーキットブレーカー、リトライ、タイムアウト

### 実践的な使用例

<p align="center"><img src="https://istio.io/latest/docs/examples/bookinfo/noistio.svg" alt="Application without Istio"><br><em>Istioを使用しないアプリケーション</em></p>

<p align="center"><img src="https://istio.io/latest/docs/examples/bookinfo/withistio.svg" alt="Application with Istio"><br><em>Istioを使用するアプリケーション - Envoy Proxyを各サービスのサイドカーとしてデプロイ</em></p>

これらのBookinfoの図はサイドカーモードを示しています。自動インジェクションでは、オプトインした名前空間またはワークロード内で新しく作成されたPodにのみEnvoyが追加されます。ambientモードではサイドカーをインジェクションしません。

## 本当にService Meshが必要ですか？

以下に示すサービス数のしきい値とチェックリストのスコアは、検討のための目安であり、Istioの要件ではありません。小規模なメッシュでも、セキュリティ上のニーズがあれば導入する理由になります。判断用の図では、同じ説明用のしきい値を使用しています。

Service Meshは強力なツールですが、あらゆる状況に適しているわけではありません。導入前に慎重に検討する必要があります。

### 判断フロー

![Service Mesh導入の判断フロー。マイクロサービスアーキテクチャ、10以上のサービス、複雑なトラフィック／セキュリティ／可観測性のニーズ、運用リソースを順番に確認し、メッシュを推奨、不要、代替策、または慎重な検討のいずれかを判断する。](../../.gitbook/assets/en-service-mesh-istio-overview-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-0.html)

### Service Meshが必要な場合 ✅

#### 1. 複雑なマイクロサービス環境

![4つのサービスがメッシュなしでmTLS、リトライ、ロギングを個別に設定する構成と、Service Meshが同じ4つのサービス間の通信を自動的に処理、制御する構成の比較。](../../.gitbook/assets/en-service-mesh-istio-overview-1.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-1.html)

**推奨基準**:

* ✅ マイクロサービスが10個以上
* ✅ サービス間通信（East-Westトラフィック）が頻繁
* ✅ 複数のプログラミング言語を使用（ポリグロット）
* ✅ 複数のチームがそれぞれ独立してサービスを開発

#### 2. ゼロトラストのセキュリティ要件

**Service Meshが提供する機能**:

* サービス間の自動mTLS暗号化
* SPIFFEベースのID管理
* きめ細かな認証／認可ポリシー
* mTLSが強制されている場合のメッシュトラフィックの暗号化。自動mTLSだけではプレーンテキストのクライアントを拒否しません

**代替手段では実現が難しいこと**:

* 各サービスでのセキュリティロジックの重複実装
* 手動での証明書管理の複雑さ
* セキュリティポリシーの不統一

#### 3. 高度なトラフィック管理

```yaml
# Canary Deployment (Traffic Distribution)
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 90
    - destination:
        host: reviews
        subset: v2
      weight: 10  # Only 10% to new version
```

**必要となる場面**:

* カナリアリリース、A/Bテスト
* ヘッダー／パスベースのルーティング
* トラフィックミラーリング（シャドーテスト）
* フォルトインジェクション（カオスエンジニアリング）
* サーキットブレーカー、リトライ、タイムアウト

#### 4. 可観測性の統合

**Service Meshの利点**:

* アプリケーションコードを変更せずにメトリクスを自動収集
* プロキシがトレーススパンを生成。リクエストを関連付けるには、アプリケーションがトレースヘッダーを伝播する必要があります
* ログ形式を統一
* サービストポロジーを可視化（Kiali）

### Service Meshが不要な場合 ❌

#### 1. シンプルなアーキテクチャ

![ロードバランサー（Ingress Controller）を経由して単一のモノリシックアプリケーションとそのデータベースに到達するユーザーリクエスト。Service Meshを使わず、Ingress Controllerだけで十分なシンプルな構成。](../../.gitbook/assets/en-service-mesh-istio-overview-2.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-2.html)

**代わりに使用するもの**:

* 保守されているKubernetes Gateway APIまたはIngress Controller
* シンプルなロードバランサー
* アプリケーションレベルでの実装

#### 2. マイクロサービスが少ない（10個未満）

**運用負荷がメリットを上回る場合**:

* Service Meshの運用上の複雑さ > 得られるメリット
* 5～10個のサービスは手動で管理可能
* CNIが適用する場合、NetworkPolicyでL3/L4の分離が可能。ただし、mTLSやHTTP認可は提供しません

**代替案**:

```yaml
# L3/L4 ingress isolation; requires a NetworkPolicy-capable CNI
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
spec:
  podSelector:
    matchLabels:
      app: backend
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
```

#### 3. 運用リソースが不足している

**Service Meshの運用に必要なもの**:

* Istio/Envoyの専門知識
* コントロールプレーンの監視と管理
* アップグレードとパッチの管理
* トラブルシューティング能力（デバッグの複雑さが増す）

**チームに必要な準備**:

* Service Meshの専門家が少なくとも1～2人
* 継続的な学習と更新情報の追跡
* 十分なテスト環境

#### 4. パフォーマンスが極めて重要な場合

**Service Meshのオーバーヘッド**:

実際の利用状況を反映したトラフィック、プロキシ設定、テレメトリ設定で、レイテンシー、CPU、メモリを測定してください。[公式のパフォーマンスページ](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)にはIstio 1.24のベンチマークが記録されています。これらの過去の結果は、他のバージョンやワークロードでの性能を保証するものではありません。

**検討する代替案**:

* ambientモード（共有L4プロキシ。削減効果はトラフィックとwaypointのデプロイ方法によって異なります）
* CNIベースのソリューション（Cilium）
* アプリケーションレベルでの最適化

### 代替ソリューションの比較

| 機能                    | Service Mesh                                 | CNI (Cilium)    | Ingress Controller | アプリケーションレベル       |
| -------------------------- | -------------------------------------------- | --------------- | ------------------ | ------------------------ |
| **L7トラフィック管理**  | ✅ フルサポート                               | ⚠️ 限定的      | ⚠️ Ingressのみ    | ✅ 可能               |
| **mTLSの自動化**        | ✅ フルサポート                               | ⚠️ 相互認証と暗号化は別機能      | ❌ 非対応    | ❌ 手動実装  |
| **分散トレーシング**    | ⚠️ トレースコンテキストの伝播が必要                                  | ❌ 非対応 | ❌ 非対応    | ⚠️ 手動実装 |
| **L3/L4ポリシー**         | ✅ 対応                                  | ✅ フルサポート  | ❌ 非対応    | ❌ 非対応          |
| **運用の複雑さ** | 🔴 高                                      | 🟡 中       | 🟢 低             | 🟡 中                |
| **リソースオーバーヘッド**      | <p>🔴 高（サイドカー）<br>🟢 低（ambient）</p> | 🟢 低          | 🟢 低             | 🟢 なし                  |
| **適した規模**         | 要件による                                 | あらゆる規模      | 小規模        | 小規模              |

### CNIベースのソリューション（Cilium）

CiliumはeBPFを基盤として、**ネットワークレベル**で多くの機能を提供します。

![IstioのL7プロキシベースのService Meshと、CiliumのeBPFカーネルレベルのCNIの比較。複雑なL7ロジックにはService Mesh、ポリシーとパフォーマンスにはCilium、大規模企業では両方を使うシナリオを示す。](../../.gitbook/assets/en-service-mesh-istio-overview-3.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-3.html)

**Ciliumのほうが適している場合**:

* 主な目的がL3/L4ネットワークポリシーである
* 必要なポリシー／暗号化設定で測定したパフォーマンスが、ワークロードの要件を満たす
* サポートされる機能が要件を満たす既存のCiliumデプロイメントを再利用する
* 主なニーズがネットワークポリシーと可観測性である。Ciliumのアウトオブバンド相互認証では、ペイロードの機密性を確保するために別途WireGuard/IPsec暗号化が必要です

Cilium 1.20.1では、独立した[ztunnel透過暗号化ベータ版](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst)も提供されており、`encryption.type: ztunnel`で選択します。名前空間への登録を前提としたTCPワークロードのmTLSを提供します。両方のエンドポイントを登録する必要があります。ClusterMeshとホストネットワークを使用するPodは対象外です。また、公開されているガイドによると、HBONEポート15008を対象とする場合を除き、この経路では通常のL4ポリシーは機能しません。これは、独自のCAとブートストラップ要件を持つ、別個のデプロイ方式です。

この図ではCNIの役割に焦点を当てています。CiliumにはL7 Envoy機能もあります。コンポーネント数と運用コストは、選択するモードによって異なります。

**参考資料**: [Ciliumのドキュメント](../../networking/cilium/README.md)

### 判断チェックリスト

導入前に次の質問に答えてください。

**アーキテクチャ**:

* [ ] マイクロサービスが10個以上ありますか？
* [ ] サービス間通信は複雑ですか？
* [ ] 複数のプログラミング言語を使用していますか？

**セキュリティ**:

* [ ] ゼロトラストのセキュリティモデルが必要ですか？
* [ ] サービス間のmTLS暗号化は必須ですか？
* [ ] きめ細かなアクセス制御が必要ですか？

**トラフィック管理**:

* [ ] カナリアリリースやA/Bテストが必要ですか？
* [ ] 高度なルーティングルールが必要ですか？
* [ ] 多くのサービスでサーキットブレーカーやリトライが必要ですか？

**可観測性**:

* [ ] 分散トレーシングは必須ですか？
* [ ] メトリクスを統合して収集する必要がありますか？
* [ ] サービストポロジーを可視化する必要がありますか？

**運用**:

* [ ] Service Meshの専門家がいますか？
* [ ] 運用の複雑さに対応できますか？
* [ ] リソースのオーバーヘッドを許容できますか？

**結果**:

* ✅ チェックが10個以上: Service Meshを強く推奨
* 🟡 チェックが5～9個: 慎重な評価が必要。小規模から始める（ambientモードを推奨）
* ❌ チェックが4個以下: 代替ソリューション（CNI、Ingress、アプリケーションレベル）を検討

### 段階的な導入戦略

Service Meshが必要だと判断した場合は、段階的に導入してください。

![4段階のロールアウト。可観測性のみのメトリクス収集から始まり、mTLSによるセキュリティ、カナリアトラフィック管理へと進み、最後に高度な機能一式を導入する。各段階は検証を通過してから次に進む。](../../.gitbook/assets/en-service-mesh-istio-overview-4.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-4.html)

**推奨する順序**:

1. **パイロットプロジェクト**（1～2個の名前空間）
2. **まず可観測性を導入**（メトリクス、ログ、トレース）
3. **セキュリティを適用**（mTLS PERMISSIVE → STRICT）
4. **トラフィック管理**（VirtualService、DestinationRule）
5. **全社に展開**

### 主な機能

1.  **トラフィック管理**

    VirtualServiceでルートを選択し、DestinationRuleでサブセットと宛先トラフィックポリシーを定義します。

    * インテリジェントルーティングと負荷分散
    * A/Bテスト、カナリアリリース、Blue/Greenデプロイメント
    * サーキットブレーカー、リトライ、タイムアウトの制御
    * トラフィックミラーリングとフォルトインジェクション
2.  **セキュリティ**

    <div align="center"><img src="https://istio.io/latest/docs/concepts/security/arch-sec.svg" alt="Security Architecture" width="600"></div>

    * サービス間の自動mTLS暗号化
    * 強力な認証と認可
    * きめ細かなアクセス制御ポリシー
    * ネットワーク分離とセキュリティポリシー
3.  **可観測性**

    <div align="center"><img src="https://istio.io/latest/docs/tasks/observability/kiali/kiali-graph.png" alt="Kiali Service Graph" width="700"></div>

    * プロキシメトリクス、設定可能なアクセスログ、トレーシング
    * Prometheus、Grafana、Jaeger、Kialiとの統合
    * サービストポロジーの可視化
    * リアルタイムのトラフィック監視
4. **レジリエンス**
   * サーキットブレーカーパターン
   * レート制限
   * アウトライア検出
   * ゾーンを考慮したルーティング

### Istioのアーキテクチャ

<div align="center"><img src="https://istio.io/latest/docs/ops/deployment/architecture/arch.svg" alt="Istio Architecture" width="700"></div>

Istioはコントロールプレーンとデータプレーンで構成されます。

![Istioのコントロールプレーンとデータプレーン。istiodのPilotがルーティング設定をプッシュし、Citadelが各PodのEnvoyサイドカーに証明書を発行する。Envoyはアプリケーションリクエストをインターセプトし、mTLSで暗号化されたトラフィックをやり取りする。](../../.gitbook/assets/en-service-mesh-istio-overview-5.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-5.html)

**コントロールプレーン（istiod）**:

* サービスディスカバリーとプロキシ設定（旧称Pilot）
* 認証局とID管理（旧称Citadel）
* 設定の検証。Galleyは廃止された独立コンポーネントであり、現在の独立したサービスではありません

**データプレーン**:

* **サイドカーモード**: 登録されたPodごとにEnvoyを配置
* **ambientモード**: L4セキュリティ用のztunnelをノードごとに配置し、必要に応じてL7処理用のwaypointプロキシを配置

### Amazon EKSでIstioを使用する利点

1. **マイクロサービスを簡単に管理**
   * アプリケーションコードを変更せずにトラフィックを管理
   * 宣言的な設定でポリシーを一貫して適用
   * Kubernetes Native APIを使用
2. **セキュリティを強化**
   * サービス間の自動暗号化
   * EKS Pod IdentityまたはIRSAを介してAWS APIにアクセス。IstioのワークロードIDは引き続きサービスアカウントベースです
   * きめ細かな権限制御
3. **可観測性を向上**
   * Amazon CloudWatchとの統合
   * AWS X-Rayによる分散トレーシング
   * 詳細なメトリクスとログ
4. **AWSサービスと統合**
   * Application Load Balancer（ALB）との統合
   * AWS Certificate Manager（ACM）との統合
   * Amazon EBS CSI Driverとの互換性

### はじめに

[Gateway APIガイド](https://istio.io/latest/docs/tasks/traffic-management/ingress/gateway-api/)

Istioを初めて使用する場合は、次の順序でドキュメントを読んでください。

1. [**インストールと初期設定**](01-installation.md): EKSクラスターにIstioをインストール
2. [**基本概念**](02-basic-concepts.md): Istioの主要な概念を理解
3. [**トラフィック管理**](traffic-management/README.md): Gateway、VirtualService、DestinationRuleを学習
4. [**セキュリティ**](security/README.md): mTLS、認証、認可を設定
5. [**可観測性**](observability/README.md): メトリクス、ログ、トレースを収集
6. [**ベストプラクティス**](best-practices.md): 本番環境での推奨事項

### ハンズオンの例

これらのルーティング例を使用するには、対応するServicesとDestinationRuleのサブセット（`v1`/`v2`）が必要です。トラフィック管理の各章を参照してください。

各セクションには、実際に動作するYAMLの例が含まれています。すべての例はクリックしてコピーできる形式です。

```yaml
# Example VirtualService
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
```

### 参考資料

* [Istio公式ドキュメント](https://istio.io/latest/docs/)
* [Istio GitHub](https://github.com/istio/istio)
* [IstioのEKSプラットフォームガイダンス](https://istio.io/latest/docs/setup/platform-setup/amazon-eks/)
* [Istioコミュニティ](https://istio.io/latest/get-involved/)


* [トレーシングとアプリケーションでのヘッダー伝播](https://istio.io/latest/docs/tasks/observability/distributed-tracing/overview/)
* [Kubernetes NetworkPolicyの機能](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
* [Ciliumの相互認証](https://docs.cilium.io/en/stable/network/servicemesh/mutual-authentication/mutual-authentication/)

### クイズ

この章で学んだことを確認するために、次のクイズに挑戦してください。

* [トラフィック管理クイズ](../../quizzes/service-mesh/istio/traffic-management.md)
* [セキュリティクイズ](../../quizzes/service-mesh/istio/security.md)
* [可観測性クイズ](../../quizzes/service-mesh/istio/observability.md)
* [レジリエンスクイズ](../../quizzes/service-mesh/istio/resilience.md)
* [応用クイズ](../../quizzes/service-mesh/istio/advanced.md)

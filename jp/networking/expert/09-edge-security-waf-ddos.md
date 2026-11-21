# 09. エッジセキュリティ：WAF と DDoS 防御

> **最終更新日**: 2026年11月19日
> **ラボの範囲**: 机上演習のみです。紙の上でカウントモードのルール計画を作成します。このワークブックでは、Web ACL、ディストリビューション、Shield サブスクリプション、ロードバランサー、Kubernetes オブジェクトのいずれも作成せず、どのシステムにも攻撃トラフィックや負荷トラフィックを送信しません。
> **検証状況**: AWS WAF、AWS Shield、Amazon CloudFront の開発者ガイド、AWS WAF API リファレンス、DDoS 耐性に関する AWS ホワイトペーパー、RFC 4987、OWASP Top 10 2021 のページを確認しました。ルールは一切デプロイしておらず、トラフィックも測定していません。演習の数値はシナリオを解いた例であり、実測値ではありません。

このワークブックを終えると、攻撃が狙うレイヤーを挙げ、経路上の**どこで**、どの制御によって阻止されるかを説明し、測定可能な期待値とロールバックのトリガーを含む、カウントモードから始める AWS WAF のルール計画を作成できるようになります。また、インターネットから直接到達できるオリジンがあると、攻撃者にとってすべてのエッジ制御が任意のものになってしまう理由も説明できるようになります。

この章では、[ワークブック 08](./08-cdn-edge-delivery.md#edge-origin-path)（CloudFront → VPC origin → internal ALB）で扱ったエッジからオリジンまでの経路を前提とし、その説明を繰り返しません。サーバー自体のホストファイアウォールについては[初心者向け 06](../beginner/06-firewalls-host-security.md)を参照してください。WAF の配置、ルール順序の落とし穴、リクエスト本文の検査制限、転送されるクライアント IP、ログフィールドの全一覧については[「WAF、エッジ、API セキュリティ」](../../security/14-waf-edge-api-security.md)で説明しています。このワークブックでは内容を繰り返さず、該当セクションへのリンクを示します。Pod レベルのルールについては[ネットワークポリシー](../../security/04-network-policies.md)、Ingress 側については[AWS Load Balancer Controller](../03-aws-lb-controller.md)を参照してください。コントローラーのドキュメントにある例では `alb.ingress.kubernetes.io/scheme: internet-facing` を使っていますが、**このコースのエッジ設計では ALB は internal**（`alb.ingress.kubernetes.io/scheme: internal`）で、CloudFront VPC origin の背後に配置されます。したがって、これらの例はその値だけを変更して読んでください。BGP による Anycast ルーティングについては[ワークブック 02](./02-routing-policy-convergence.md)、TCP ハンドシェイクについては[ネットワーク基礎 パート 2](../../basics/06-network-fundamentals-part2.md)を参照してください。

**準備するもの:** テキストエディターと AWS ドキュメント。AWS アカウントは不要です。自分で設計を構築する場合、AWS WAF の料金（Web ACL ごと、ルールごと、100 万リクエストごとの料金に加え、Bot Control、アカウント乗っ取り防止、Anti-DDoS ルールグループ（Shield Advanced の対象となる場合を除く）、CAPTCHA、Challenge、1,500 WCU を超える容量、ロギングに対する追加料金）、CloudFront とロードバランサーの料金が発生します。また、サブスクリプションを契約する場合は、AWS Shield Advanced の料金もかかります（料金ページには、1年間の契約で月額 3,000 ドルからと記載されています）。**その費用とリソースのクリーンアップは、学習者自身の責任です。** 書面で承認されたテスト計画がない限り、自分のリソースに対するものも含め、攻撃トラフィックを使ったテストは絶対に行わないでください。

## 1. 答えを考えながら読む

試験範囲は、読む内容を選ぶためだけに使います。数値や動作は、最初の列に示した公式ページを参照してください。

| 読む資料 | 対応する試験範囲 | 自分の言葉で答える質問 |
|---|---|---|
| [AWS Shield Standard の概要](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-standard-summary.html)、[CloudFront と Route 53 における Shield の緩和ロジック](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-event-mitigation-logic-continuous-inspection.html) | ANS-C01 ドメイン 4「ネットワークセキュリティ、コンプライアンス、ガバナンス」、タスク 4.1（AWS WAF と AWS Shield によるインバウンドトラフィックフローの保護） | CloudFront ディストリビューションを狙った SYN フラッドが、オリジンへの SYN フラッドにならないのはなぜですか？ |
| [ルールアクションの使用](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-action.html)、[レートベースルールの設定](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based-high-level-settings.html)、[Web リクエストのラベリング](https://docs.aws.amazon.com/waf/latest/developerguide/waf-labels.html) | ドメイン 4、タスク 4.1（脅威モデル、緩和戦略） | リクエストの評価を終了するアクションと、後続のルールに評価を続けさせるアクションは、それぞれどれですか？ |
| [AWS Shield Advanced の機能](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-advanced-summary-capabilities.html)、[Anti-DDoS マネージドルールグループ](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-anti-ddos.html) | ドメイン 4、タスク 4.1 | Shield Standard にはなく Shield Advanced が提供するものは何ですか？また、その利用に先立って何が必要ですか？ |
| [保護のテストとチューニング](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing.html)、[Web ACL トラフィックのロギング](https://docs.aws.amazon.com/waf/latest/developerguide/logging.html)、[サンプリングされたリクエストの表示](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing-view-sample.html) | ドメイン 4、タスク 4.2（モニタリングとロギングによるセキュリティの検証と監査） | Count モードのルールに一致したはずであることを示すログフィールドはどれですか？ |
| [OWASP Top 10 2021](https://owasp.org/Top10/2021/) | ドメイン 4、タスク 4.1（一般的なセキュリティ脅威） | 10 個のカテゴリのうち、エッジ WAF でリスクを軽減できるものと、アプリケーションでしか修正できないものは、それぞれどれですか？ |

読了したら、クライアントから Pod までの経路を描き、セクション 2 の各攻撃がどこで止まるかをその経路上に示してください。攻撃を止める場所を指し示せない設計レビューでは、その攻撃への対策を網羅したとは言えません。

## 2. 脅威のレイヤー：各攻撃が枯渇させるもの

攻撃が使い果たそうとするリソース、つまりリンク帯域幅、接続状態、TLS 処理の CPU、アプリケーションの処理能力に注目すると、攻撃の位置づけを理解しやすくなります。

| レイヤー | 攻撃 | 仕組み | 枯渇させるもの |
|---|---|---|---|
| L3 | **UDP リフレクション** | 攻撃者は送信元として被害者のアドレスを偽装し、第三者のサーバー（DNS、NTP、SSDP、CLDAP、Memcached、CharGen、QOTD）に小さな UDP リクエストを送ります。サーバーはその被害者に、はるかに大きな応答を送ります。DNS について、AWS ホワイトペーパーでは増幅率を 28～54 倍としています | リンクとネットワークの容量 |
| L4 | **SYN フラッド** | 3 ウェイハンドシェイク（[パート 2](../../basics/06-network-fundamentals-part2.md)）を完了しない大量の SYN | リスナーの半開接続用バックログ（[RFC 4987](https://www.rfc-editor.org/rfc/rfc4987.html) §2.2）。リンクを埋め尽くす必要はありません |
| L6 | **TLS の悪用** | ハンドシェイクとして送られる解読不能なデータ、終わりのない再ネゴシエーション、またはセッションの急速な開始と終了 | TLS を終端する側の CPU |
| L7 | **HTTP フラッド** | 正当なユーザーのリクエストに見えるリクエスト。人間のブラウジングを模倣することもあります | アプリケーションの処理能力。少量でも十分な場合があります |
| L7 | **キャッシュバスティング** | クエリ文字列を変化させ、CDN に各リクエストを転送させる HTTP フラッド（[ワークブック 08](./08-cdn-edge-delivery.md)のセクション 5） | キャッシュの背後にあるオリジンの処理能力 |
| L7 | **エクスプロイトの試行** | 既知の脆弱性クラスを狙うペイロード（セクション 4） | 容量ではなく、機密性と完全性 |
| L7 | **ボット、スクレーパー、クレデンシャルスタッフィング** | コンテンツの自動窃取や、漏えいしたユーザー名とパスワードの組み合わせを使ったログイン試行 | ビジネスロジックとアカウント。ホワイトペーパーによると、これらは厳密には DDoS ではありませんが、DDoS のように見えます |

ここから 2 つのことが分かります。第一に、リフレクション攻撃には送信元アドレスを偽装する能力が必要であり、送信元アドレス検証を適用するネットワーク（[BCP 38](https://www.rfc-editor.org/info/bcp38)）によってそれを防げます。第二に、L7 攻撃は正しい形式のトラフィックなので、パケットの妥当性しか確認しないものでは阻止できません。リクエストを読み取る制御が必要です。

## 3. 各攻撃を阻止する場所

| 攻撃 | 阻止する場所 | 仕組み | 管理者 |
|---|---|---|---|
| UDP リフレクション | CloudFront エッジ | Shield の緩和策は、Web アプリケーションにとって妥当なトラフィックのみを通過させます。CloudFront は正しい形式の接続のみを受け入れます | AWS（自動） |
| SYN フラッド | CloudFront エッジ | Shield の TCP SYN プロキシが、接続がサービスに到達する前にハンドシェイクを検証します（ステートレスな SYN cookie） | AWS（自動） |
| TLS の悪用 | CloudFront エッジ | エッジで TLS を終端するため、オリジンが受け取るのは正しい形式のリクエストだけです（[ワークブック 08](./08-cdn-edge-delivery.md)のセクション 7） | AWS（自動） |
| HTTP フラッド、キャッシュバスティング | エッジの WAF Web ACL | レートベースルール、Anti-DDoS マネージドルールグループ、Challenge | あなた |
| エクスプロイトの試行 | WAF Web ACL、その後アプリケーション | 最初のフィルターとしてのマネージドルールグループ、アプリケーション内の入力検証と認可 | あなた |
| クレデンシャルスタッフィング | WAF（アカウント乗っ取り防止）、その後アプリケーション | 盗難された認証情報の検査とログイン回数の制限、アプリケーション内の MFA とロックアウトポリシー | あなた |
| オリジンを直接狙う攻撃全般 | オリジンにパブリックな経路がなければ、**どこにもない** | オリジンの隠蔽（セクション 8） | あなた |

**SYN cookie** を使うと、リスナーは SYN-RECEIVED 状態の接続について状態を保持せずに済みます。サーバーは必要な情報を SYN-ACK のシーケンス番号にエンコードし、有効な ACK が返ってきたときに状態を再構築します（[RFC 4987](https://www.rfc-editor.org/rfc/rfc4987.html) §3.6）。AWS ホワイトペーパーでは、エッジサービスのステートレスな SYN フラッド緩和策は、受信接続を SYN cookie で検証してから転送すると説明しており、最新のオペレーティングシステムでは SYN cookie がデフォルトで有効になっていると述べています。CloudFront はオリジンへの永続的な接続も保持するため、ビューアーの新しい接続が新しいオリジン接続になるわけではありません。AWS WAF もセキュリティグループも、これらの仕組みの代わりにはなりません。AWS WAF が検査するのは HTTP リクエストなので、接続が確立した後にのみ機能します。セキュリティグループは送信元、プロトコル、ポートに基づいて許可または拒否しますが、レートを制限しません。

**吸収**には、フラッドを上回る容量が必要です。CloudFront に対する Shield の緩和策の AWS ページには、CloudFront は DNS トラフィックの誘導と Anycast ルーティングを組み合わせて、攻撃の発生源に近い場所で攻撃を緩和し、障害を分離するとあります。これはワークブック 08 の説明とも一致しています。DNS が各ビューアーを POP に誘導し、攻撃トラフィックは単一のオリジンではなく多数の POP に到達します。Shield の緩和策はエッジサービスに統合されており、ホワイトペーパーによると、これにより緩和までの時間が数分から 1 秒未満に短縮されます。

**拒否されたトラフィックの費用:** ホワイトペーパーによると、CloudFront または AWS WAF が拒否したリクエストについては、HTTP リクエストやデータ転送アウトの料金は発生しません。WAF がブロックしたリクエストでは、WAF のリクエスト検査料金は発生しますが、オリジンの処理能力は消費しません。

**実務上のポイント:** エッジが止めるのはトラフィック量であり、誰が何をしてよいかを判断するわけではありません。AWS WAF はエクスプロイトや悪用の対象範囲を狭めますが、[認可はアプリケーションに残ります](../../security/14-waf-edge-api-security.md)（同章のセクション 1）。ビジネス上の操作に対する唯一のチェックが WAF である設計は、単一障害点を抱えています。

## 4. OWASP Top 10 2021 とエッジ WAF でできること

[OWASP Top 10 2021](https://owasp.org/Top10/2021/) には、A01 から A10 まで 10 個のWebアプリケーションリスクカテゴリがあります。OWASP はその後、2025 年版を公開していますが、このワークブックでは 2021 年版を使用します。AWS は、自社のコアルールセットについて、Top 10 などの OWASP の刊行物に記載された「高リスクで頻繁に発生する脆弱性の一部」に対する保護を提供すると説明しています。マネージドルールは、既知のリクエストパターンを検出するフィルターとして扱い、カテゴリ全体を網羅するものとは見なさないでください。

| 2021 年のカテゴリ | エッジ WAF ができること（AWS マネージドルールグループの例） | アプリケーションまたはプラットフォームでしかできないこと |
|---|---|---|
| A01 アクセス制御の不備 | 効果は限定的。リクエスト自体は正当なものに見えます | すべてのリクエストでオブジェクトレベルの認可を行う |
| A02 暗号化の失敗 | WAF では対応できない | すべての区間で TLS を使用する（[ワークブック 08](./08-cdn-edge-delivery.md)のセクション 7）、鍵とデータを適切に扱う |
| A03 インジェクション | SQL インジェクションルール（`AWSManagedRulesSQLiRuleSet`、200 WCU）、コアルールセットのクロスサイトスクリプティングルール | パラメーター化クエリ、出力エンコーディング |
| A04 安全でない設計 | なし | 脅威モデリング、ビジネス上の制限 |
| A05 セキュリティの設定ミス | 間接的な対応 | 設定レビュー。インターネットから到達できるオリジンは、エッジ設計の設定ミスです（セクション 8） |
| A06 脆弱で古くなったコンポーネント | 既知の悪意ある入力（`AWSManagedRulesKnownBadInputsRuleSet`、200 WCU）。たとえば Log4j や Java のデシリアライゼーションパターン | パッチの適用。WAF ルールが与えるのは時間的な猶予だけです |
| A07 識別と認証の失敗 | アカウント乗っ取り防止（`AWSManagedRulesATPRuleSet`、50 WCU、有料） | MFA、ロックアウト、セッション管理 |
| A08 ソフトウェアとデータの完全性の障害 | なし | 署名付き成果物、サプライチェーン制御 |
| A09 セキュリティのロギングとモニタリングの失敗 | WAF ログとメトリクスは入力情報の 1 つです（セクション 9） | レイヤーをまたいだ相関分析とアラート |
| A10 サーバーサイドリクエストフォージェリ（SSRF） | EC2 メタデータの持ち出しを試みるパターンを探すコアルールセットルール（`EC2MetaDataSSRF_*`） | アプリケーションの送信制御と URL 検証 |

コアルールセット（`AWSManagedRulesCommonRuleSet`）のコストは 700 WCU です。また、たとえば `SizeRestrictions_BODY` は 8 KB を超えるリクエスト本文をブロックします。これは、アップロードパスで誤検知がよく発生する原因です（セクション 10）。

## 5. AWS WAF のモデル

**Web ACL。** AWS WAF コンソールでは、現在 Web ACL を**保護パック**（Web ACL）と呼びますが、このワークブックでは「Web ACL」と表記します。Web ACL にはルールとルールグループ、およびどのルールも評価を終了させなかったリクエストに適用される**デフォルトアクション**（Allow または Block）が含まれます。各リソースに関連付けられる Web ACL は最大 1 つで、1 つの Web ACL で複数のリソースを保護できます。

**スコープ。** CloudFront 用の Web ACL は**グローバル**で、リージョンは US East（バージニア北部）に固定されています。CLI では `--scope=CLOUDFRONT --region=us-east-1` を指定し、API と SDK では `us-east-1` エンドポイントを使用します。CloudFront ディストリビューションに関連付けられた Web ACL は、別の種類のリソースには関連付けられません。ALB などのリージョナルリソースには、そのリソースが存在するリージョンに別の `REGIONAL` Web ACL が必要です。

**ルール、ルールグループ、評価順序。** ルールは、ステートメントとアクションで構成されます。ルールグループは、独自に作成したもの、または**マネージドルールグループ**（AWS Managed Rules、AWS Marketplace の販売者）である、再利用可能なルールの集合です。AWS WAF は、評価を終了するルールに達するかルールがなくなるまで、数値が最も小さい優先度から順にルールを評価します。ルールグループ内では、そのグループ独自の優先度が使われます。順序に関する落とし穴（早い段階に置かれた広範な Allow、グループ全体の除外）については、[security/14 のセクション 3](../../security/14-waf-edge-api-security.md)を参照してください。

**アクション:**

| アクション | 評価を終了するか | 動作 |
|---|---|---|
| Allow | はい | 保護対象リソースにリクエストを転送します。独自ルールでカスタムリクエストヘッダーを挿入することもできます |
| Block | はい | デフォルトでは保護対象リソースが `403 (Forbidden)` を返します。独自ルールでカスタムレスポンスを定義することもできます |
| Count | いいえ | 一致をカウントし、次のルールに進みます。ラベルやカスタムリクエストヘッダーを追加することもできます |
| CAPTCHA | トークンによって異なる | 有効で期限切れでないトークンの場合、Count と同じ動作をします。トークンがない、無効、または期限切れの場合、ブロックし、クライアントが表示可能であれば CAPTCHA パズルを送ります |
| Challenge | トークンによって異なる | 同じトークンの判定ロジックですが、パズルの代わりに、ブラウザーに対するサイレントなチャレンジを行います |

CAPTCHA と Challenge が実行されるのは、ブラウザーがセキュアコンテキストで HTTPS エンドポイントにアクセスするときだけで、どちらにも追加料金がかかります。ブラウザーではない API クライアントはこれらに応答できないため、マシン向け API は別にテストしてください。AWS WAF には、アプリからのリクエストにトークンを追加するアプリケーション統合 SDK もあります。AWS では **Monetize** アクションも追加されています（HTTP `402 Payment Required`、CloudFront Web ACL のみ、評価終了アクション、レートベースルールでは使用不可）。このワークブックでは対象外です。

**レートベースルール。** レートベースルールは、**評価ウィンドウ**（60、120、300、600 秒。デフォルトは 300 秒）内における各**集計インスタンス**（たとえば、各送信元 IP）のリクエストをカウントし、**上限**（最小 10）を超えたインスタンスからの、その後の一致するリクエストにアクションを適用します。アクションには Allow 以外のものを指定できます。**スコープダウンステートメント**を使うと、たとえば `/login` への `POST` のみのように、カウントとアクションの対象となるリクエストを絞り込めます。設計時には次の動作を考慮してください。

- AWS WAF は、最近のリクエストほど重みを大きくするアルゴリズムでレートを推定するため、設定値と完全に一致するのではなく、その値の近くで制限します。
- ガイドによると、レートはウィンドウとは独立して頻繁にチェックされます。API リファレンスでは、約 10 秒ごととされています。制限が始まるまでに数分間、リクエストが過剰な速度で到着することがあります。また、レートが下がった後も通常は 30 秒未満、制限が続く場合があります。
- 上限、ウィンドウ、集計方法、転送された IP の設定、スコープのいずれかを変更すると、カウントが**リセット**され、レート制限が最大 1 分間停止する場合があります。
- レートベースのステートメントは、別のステートメント（たとえば `NotStatement`）の内側にはネストできませんが、そのスコープダウンステートメントにはネストできます。
- IP のみを使って集計する場合、`GetRateBasedStatementManagedKeys` は現在制限中のアドレスを一覧表示します。

CloudFront → ALB → Ingress の経路で、どのクライアントアドレスを集計対象にするかについては、[security/14 のセクション 5](../../security/14-waf-edge-api-security.md)を参照してください。

**ラベル。** ラベルは、一致したルールがリクエストに追加するメタデータです。同じ Web ACL の評価が続く間は保持され、後続のルールは**ラベル一致ステートメント**を使って読み取ります。独自のラベルの形式は `awswaf:<account id>:<rulegroup or webacl>:<name>:<namespace>:...:<label name>`、マネージドルールグループのラベルの形式は `awswaf:managed:<vendor>:<rule group name>:...` です。たとえば、`awswaf:managed:aws:core-rule-set:NoUserAgent_Header` のようになります。すべての AWS Managed Rules ルールグループはラベルを追加します。主な使い方は、ルールを Count にしてラベルだけを付け、その後にラベルの組み合わせに基づいて判断するルールを追加することです。ラベルによって CloudWatch のラベルメトリクスも生成されます。

**マネージドルールのオーバーライド。** 異なるスイッチが 2 つあります。

| オーバーライド | 動作 | テストに使うか |
|---|---|---|
| **ルールアクションのオーバーライド**（`RuleActionOverrides`、グループ内のルールごとに設定） | 一致したリクエストは、たとえば Count のように、そのルールのアクションをオーバーライドした場合とまったく同じように処理されます。グループはほかのルールの評価を続けます | はい。ルールグループのテスト方法として、ドキュメントで説明されているのはこちらです |
| **ルールグループの返却アクションを Count にオーバーライド** | グループは通常どおり評価し、最初に一致した評価終了ルールで停止します。Web ACL に返される結果だけが Count になります | いいえ。ガイドによると、グループ内での評価方法は変わらないため、そのリクエストについてグループ内の後続ルールは実行されません |

`RuleActionOverrides` は 2022 年 10 月に、従来の `ExcludedRules` 設定に取って代わりました。

**容量（WCU）。** Web ACL の容量ユニットは、ルールの実行に必要なリソースを測るもので、トラフィックの検査方法は変わりません。単純なステートメントは、たとえば正規表現パターンセットや JSON 本文の検査よりコストが低くなります。ルールグループの容量は作成時に設定される**変更不可の値**（最大 5,000 WCU）であり、Web ACL でグループを使う際のコストは、その時点の内容ではなく、この容量になります。Web ACL では最大 5,000 WCU を使用できます。基本料金には 1,500 WCU が含まれ、それを超える容量には段階的な追加料金が発生します。デプロイ前にルールリストの容量を確認するには、`CheckCapacity` API を使います。

**伝播。** 変更がすべてのロケーションに反映されるまでには、数秒から数分かかります。そのため短時間、一部のロケーションには新しいアクションが適用され、ほかのロケーションには古いアクションが適用されたままになることがあります。

## 6. AWS Shield Standard と Shield Advanced

| | Shield Standard | Shield Advanced |
|---|---|---|
| 料金と有効化 | すべての AWS 顧客に追加料金なしで自動適用 | サブスクリプション制。料金ページには、契約が自動更新される1年間の契約で、月額 3,000 ドルからと記載されています。明示的に追加したリソース、または AWS Firewall Manager の Shield Advanced ポリシーを通じて追加したリソースのみを保護します |
| 保護範囲 | 最も一般的で頻繁に発生するネットワーク層およびトランスポート層の攻撃。CloudFront ディストリビューション、Route 53 ホストゾーン、Global Accelerator の標準アクセラレーターは、既知のすべてのネットワーク層およびトランスポート層の攻撃から保護されます | CloudFront、Route 53 ホストゾーン、Global Accelerator の標準アクセラレーター、Elastic IP アドレス（およびその背後にある EC2 インスタンスと NLB）、ALB、Classic Load Balancer |
| アプリケーション層（L7） | 単独では対応しません。L7 は WAF の役割です | AWS WAF Web ACL を使用します。保護対象リソースの標準的な WAF 料金は、最大 1,500 WCU とデフォルトの本文サイズまで対象になります。Bot Control、CAPTCHA、1,500 WCU を超える容量、大きな本文の検査は対象外です。サブスクリプションには Anti-DDoS ルールグループも追加料金なしで含まれ、支払者ごとに月間 500 億リクエストまで AWS WAF リクエスト料金が対象となります（その後は 100 万リクエストあたり 0.15 ドル） |
| L7 の自動緩和 | なし | 次の段落を参照 |
| 対応チーム | なし | 攻撃中の支援とカスタム緩和策を提供する **Shield Response Team（SRT）**。Business Support または Enterprise Support のプランが必要です（DDoS 耐性に関するホワイトペーパーでは Business Support+ または Enterprise Support と記載） |
| 検出 | 自動 | Route 53 ヘルスチェックを使うヘルスベースの検出。**プロアクティブエンゲージメント**（SRT から連絡を受けること）にはヘルスチェックが必要です |
| コスト保護 | なし | 攻撃によって発生したスケーリング料金の一部に対する Shield Advanced のサービスクレジット |
| 可視性 | サービスメトリクス以外にはなし | コンソール、API、CloudWatch メトリクスで確認できるイベントの詳細、保護グループ |

**2026 年の自動 L7 緩和。** 2026 年 3 月 26 日以降、**Anti-DDoS マネージドルールグループ**（`AWSManagedRulesAntiDDoSRuleSet`、50 WCU。通常の AWS WAF では追加料金が発生し、Shield Advanced のサブスクリプションでは追加料金なしで含まれます）が、HTTP リクエストフラッドに対する AWS のデフォルトのソリューションとなっています。既存顧客は引き続き利用できますが、Shield Advanced の従来のレイヤー 7 自動緩和機能に取って代わるものです。このルールグループはトラフィックをリソースのベースラインと比較し、イベント中のすべてのリクエストに `awswaf:managed:aws:anti-ddos:event-detected` というラベルを付け、疑わしい送信元には信頼度に応じて `low-`、`medium-`、`high-suspicion-ddos-request` というラベルを付けます。ソフトな緩和策としてサイレントな Challenge を送り（Challenge 対象としてラベル付けできるのは `GET` リクエストのみ）、ハードな緩和策としてブロックします。従来の Shield Advanced 機能は 150 WCU のルールグループを追加し、ベースラインの学習に 24 時間から 30 日かかります。また、Count または Block が可能です。CDN の背後にある ALB では CDN が元のクライアント属性を転送しない可能性があるため、効果が低くなります。AWS は代わりに CloudFront ディストリビューションで有効にすることを推奨しています。

## 7. 参照経路における多層防御

![エッジセキュリティのアニメーション。① ボットネットが CloudFront エッジに L3/L4 フラッド（UDP リフレクションと SYN フラッド）を送ります。Shield がそこで吸収し、オリジンには何も到達しません。② ボットが /login に正しい形式の HTTPS フラッドを送ります。L3/L4 の検査は通過しますが、WAF Web ACL のレートベースルール（名前の例: rate-login）がブロックし、クライアントは 403 Forbidden を受け取ります。③ 正当な GET は Shield を通過し、WAF ルールで評価が終了しないため、Web ACL のデフォルトアクション Allow によって転送されます。④ CloudFront は VPC origin を通じて接続します。プライベートサブネット内のサービス管理 ENI（10.0.11.25）が internal ALB（10.0.12.40）に接続し、ALB のセキュリティグループは CloudFront-VPCOrigins-Service-SG またはオリジン向けプレフィックスリストからのみ許可します。⑤ scheme internal の Ingress から作成された ALB は Pod IP（10.0.13.31）に転送します。Pod の NetworkPolicy は ALB サブネットからのみ許可し、Pod は 200 を返します。インターネット向けロードバランサーも、パブリック CIDR を許可するインバウンドルールもありません。](../../.gitbook/assets/en-networking-expert-09-edge-security-waf-ddos-anim-0.svg)

| レイヤー | 制御 | 許可するもの | 機能したことを示す証拠 |
|---|---|---|---|
| エッジネットワーク | Shield Standard、CloudFront（DNS による誘導、Anycast、SYN プロキシ、エッジでの TLS） | 正しい形式の HTTP(S) 接続 | ネットワーク層のイベント中にオリジンの負荷が変わらないこと。サブスクリプション契約時は Shield Advanced のイベントデータ |
| エッジアプリケーション | グローバル Web ACL（`CLOUDFRONT` スコープ、us-east-1） | どのルールでも評価が終了しなかったリクエスト。最終的にはデフォルトアクションが適用されます | WAF ログの `terminatingRuleId`、`action`、ラベル |
| オリジンへの経路 | VPC origin から internal ALB（[ワークブック 08](./08-cdn-edge-delivery.md#edge-origin-path)） | CloudFront のみ。ALB にはプライベートアドレスのみが割り当てられます | テスト対象となるインターネット経路が存在しないこと |
| ALB セキュリティグループ | `CloudFront-VPCOrigins-Service-SG`（自分のディストリビューション）またはマネージドプレフィックスリスト `com.amazonaws.global.cloudfront.origin-facing`（任意のディストリビューション）からのインバウンドのみ | CloudFront の VPC origin ENI | セキュリティグループのルール。ALB アクセスログには VPC origin サブネットのアドレスのみが表示される想定 |
| Ingress | `alb.ingress.kubernetes.io/scheme: internal` と `target-type: ip` を指定した AWS Load Balancer Controller（[AWS Load Balancer Controller](../03-aws-lb-controller.md)） | 定義したリスナールール | Ingress イベント、ターゲットのヘルス |
| Pod | ALB サブネットを指定した `ipBlock` からの NetworkPolicy ingress（[ネットワークポリシー](../../security/04-network-policies.md#kubernetes-networkpolicy-spec)） | ALB ノードからの接続 | 有効になっている場合、CNI のポリシーログに記録される拒否接続 |
| ホスト | ホストファイアウォール（[初心者向け 06](../beginner/06-firewalls-host-security.md)） | ノードがサービスを提供する必要のあるポート | ファイアウォールのカウンター |
| アプリケーション | 認証と認可 | ユーザーに許可された操作 | アプリケーションの監査ログ |

**Pod が認識する送信元アドレス。** ALB はプロキシです。ELB ガイドによると、サーバーアクセスログに記録されるのはロードバランサーの IP アドレスのみで、クライアントのアドレスは `X-Forwarded-For` に入ります。ただし、適切に保護されたシステムが追加した場合に限り、この値を信頼できます。したがって、Pod IP をターゲットとする場合、Pod が認識するのは ALB ノードのプライベートアドレスであり、そのため上記の NetworkPolicy では ALB サブネットを指定しています。Kubernetes のドキュメントでは、アドレスの書き換えが NetworkPolicy の処理の前に行われるか後に行われるかは、ネットワークプラグイン、クラウドプロバイダー、Service の実装によって異なると警告しています。そのため、このルールに依存する前に CNI 上で実際の送信元を確認してください。また、NetworkPolicy はそれを適用するプラグインがなければ何の効果もないことを忘れないでください。

**Web ACL は 1 つか 2 つか。** CloudFront Web ACL を ALB にも関連付けることはできません。ALB にリージョナル Web ACL を追加すると、独自のログと料金を持つ、2 つ目の独立した検査になります。それが有益な場合については、[security/14 のセクション 2](../../security/14-waf-edge-api-security.md)で説明しています。

## 8. オリジンの隠蔽：到達可能なオリジンがエッジを迂回させる理由

上の表のエッジに関する行にある制御は、すべて**ディストリビューションを通過するリクエストにのみ**適用されます。攻撃者が、インターネットからオリジンが応答するアドレスや DNS 名を知った場合、そこにリクエストを送り、Shield によるエッジでの吸収、グローバル Web ACL、レートベースルール、CloudFront による TLS 終端を一度に迂回します。その結果、オリジンは自らの処理能力だけで、生の SYN フラッドや HTTP フラッドに対処することになります。WAF ログには何も記録されません。

**隠蔽**とは、オリジンにインターネット経由の経路がまったくない状態を指します。参照設計では、これはフィルターではなくルーティング上の特性です。internal ALB にはプライベートアドレスしかないため、後からセキュリティグループを緩めても、インターネットから到達可能にはなりません（[ワークブック 08](./08-cdn-edge-delivery.md#edge-origin-path)）。これより弱い設計として、[security/14 のオプション A](../../security/14-waf-edge-api-security.md)で説明している、CloudFront プレフィックスリストからのアクセスを許可し、秘密のヘッダーを確認するパブリック ALB と比較してください。プレフィックスリストは、攻撃者が作成したものも含め、**任意の** CloudFront ディストリビューションを許可します。また、ヘッダーは共有秘密であり、漏えいした時点で役に立たなくなります。このコースではその設計を使用しません。

**レビュー時の迂回経路一覧:** 古い DNS レコードが以前のパブリックオリジンを指したままになっていないか、同じクラスター内の別のロードバランサーや `LoadBalancer` タイプの Service、NodePort、管理用エンドポイント、同じアプリケーションを提供するテスト環境がないかを確認してください。ある経路にプライベートオリジンのラベルが付いていても、ほかの経路が存在しない証明にはなりません。

## 9. ログとメトリクス：各シグナルが証明すること

| シグナル | 場所 | 分かること | 制限 |
|---|---|---|---|
| WAF ログ | 名前が `aws-waf-logs-` で始まる CloudWatch Logs ロググループ、S3 バケット、または Amazon Data Firehose ストリーム | リクエストごとの `terminatingRuleId` と `action`、`nonTerminatingMatchingRules` 内の Count 一致、`ruleGroupId`、`labels` | 別途料金がかかります。保持するリクエストをフィルタリングでき、フィールドを（`xxx` として表示される形に）秘匿できます |
| CloudWatch メトリクス | AWS WAF のメトリクス | アクション別に集計された一致（Count ルールの一致は Count メトリクスに表示）、すべてのラベルのラベルメトリクス | ルールグループ内の Count アクションルールは Web ACL ディメンションのメトリクスを発行せず、Rule、RuleGroup、Region ディメンションのみを発行します |
| サンプリングされたリクエスト | Web ACL コンソールのタブ、または `GetSampledRequests` | 過去 3 時間分の、ルールに一致した最大 100 リクエストとデフォルトアクションになった最大 100 リクエスト。ルール、アクション、URI も含まれます | サンプリングを有効にする必要があります。ルールグループ内の Count ルールのサンプルは Web ACL ビューに表示されません。ログの秘匿設定はサンプリングには適用されません |
| トラフィック概要ダッシュボード | WAF コンソール | CloudWatch メトリクスのほぼリアルタイムの概要 | 概要であり、リクエスト単位の証拠ではありません |
| Shield Advanced イベント | Shield コンソール、API、CloudWatch | 保護されたリソースで検出されたイベントと緩和策 | サブスクリプションが必要です |
| CloudFront ログ | [ワークブック 08 のセクション 10](./08-cdn-edge-delivery.md) | エッジにおけるリクエストごとのステータスコードと結果タイプ | 一致したルールは WAF ログに記録されるため、2 つを相関させます |

WAF ログフィールドの全一覧は、[security/14 のセクション 6](../../security/14-waf-edge-api-security.md)を参照してください。Count ルールの場合、**ログとラベルメトリクス**が信頼できる証拠です。サンプリングされたリクエストや Web ACL メトリクスでは、マネージドルールグループ内の Count 一致が表示されないことがあるためです。

## 10. 演習：ロールバックのトリガーを含むカウントモードのルール計画

机上演習です。承認済みのアカウントで後日実行できる計画を作成しますが、ここではデプロイしません。結果には**机上のシナリオであり、測定値ではない**と明記してください。

**シナリオ。** あるショップは、セクション 7 の参照経路を通じて `/assets/*`、`/login`（`POST`、ブラウザーフォーム）、`/api/*`（ブラウザーではなくモバイルアプリ）、`/api/upload`（最大 5 MB の画像）を提供しています。7 日間分の CloudFront ログから、次のベースラインが得られています。

| パス | トラフィック量 | 5 分間の最大値における IP ごとのピーク | 備考 |
|---|---|---|---|
| `POST /login` | 1 日あたり 120 万件、成功率 96% | リクエスト数の p99 は 18 件。あるアドレス `198.51.100.20` は 640 件に達する | `198.51.100.20` は多くの従業員が共有するパートナー企業のオフィス NAT |
| `/api/upload` | 1 日あたり 40,000 件 | p99 は 6 件 | すべてのリクエスト本文が 8 KB より大きい |
| `/api/*`（その他） | 1 日あたり 900 万件 | p99 は 120 件 | モバイルアプリのため、Challenge や CAPTCHA を実行できない |

Web ACL のデフォルトアクションは Allow です。

**計画（各行に記入するか、内容を確認してください）:**

| 優先度 | ルール | 試験アクション | 試験中に予想される一致 | Block にする前の判断 |
|---|---|---|---|---|
| 10 | `RuleActionOverrides` を使い、`AWSManagedRulesCommonRuleSet` のすべてのルールを Count にオーバーライドする | Count（ルールごと） | 1 日あたり 40,000 件ある `/api/upload` のほぼすべてのリクエストで `SizeRestrictions_BODY` が一致する（本文が 8 KB 超）。実際のユーザーについては、ほかのルールの一致はほぼゼロ | スコープダウンステートメントで `/api/upload` をグループから除外するか、`SizeRestrictions_BODY` を Count のままにし、ほかのパスに対するラベル一致ルールを追加する |
| 20 | `AWSManagedRulesSQLiRuleSet` のルールを Count にオーバーライドする | Count（ルールごと） | 実際のユーザーからの一致はほぼゼロ | Block にする前に、既知のクライアントからの一致をすべて調査する |
| 30 | `rate-login`：IP で集計するレートベースルール、ウィンドウ 300 秒、上限 100、スコープダウンは `POST` かつパスが `/login` で始まるリクエスト | Count | 通常のユーザーは一致しない（p99 の 18 件は上限 100 よりはるかに少ない）。`198.51.100.20` は 100 件を超えるたびに一致する。静穏期間後に 5 分間だけ 640 件のピークが発生した場合、カウントされるリクエストは約 540 件（上限を超えた分）。100 件を超える状態が続く場合は、推定レートが上限を下回るまでルールが適用され続けるため、その後のリクエストのほぼすべてがカウントされる | 誤検知: スコープダウンの中に `198.51.100.20` を含む IP セットを使った `NOT` を追加するか、そのアドレスに別の高い上限を設定する |

行 30 の断片を次に示します。これは、誤検知への対応を決めた**後**のルールを示すもので、`PartnerNat` 除外が追加されています。表に示した試験中は `NotStatement` はありません。これは**Web ACL 内の 1 つのルール**であり、Web ACL 全体でもデプロイコマンドでもありません。`PartnerNat` は作成する IP セットです。

```json
{
  "Name": "rate-login",
  "Priority": 30,
  "Statement": {
    "RateBasedStatement": {
      "Limit": 100,
      "EvaluationWindowSec": 300,
      "AggregateKeyType": "IP",
      "ScopeDownStatement": {
        "AndStatement": {
          "Statements": [
            { "ByteMatchStatement": { "SearchString": "POST", "FieldToMatch": { "Method": {} },
                "TextTransformations": [{ "Priority": 0, "Type": "NONE" }], "PositionalConstraint": "EXACTLY" } },
            { "ByteMatchStatement": { "SearchString": "/login", "FieldToMatch": { "UriPath": {} },
                "TextTransformations": [{ "Priority": 0, "Type": "NONE" }], "PositionalConstraint": "STARTS_WITH" } },
            { "NotStatement": { "Statement": { "IPSetReferenceStatement": {
                "ARN": "arn:aws:wafv2:us-east-1:111122223333:global/ipset/PartnerNat/<id>" } } } }
          ]
        }
      }
    }
  },
  "Action": { "Count": {} },
  "VisibilityConfig": { "SampledRequestsEnabled": true, "CloudWatchMetricsEnabled": true, "MetricName": "rate-login" }
}
```

**タスク:**

1. 計画を完成させてください。各行について、確認する証拠（ログフィールド、メトリクス、ラベル）、試験期間、判断する担当者を記入してください。
2. 行 10 でルールグループの返却アクションのオーバーライドではなく、ルールごとの `RuleActionOverrides` を使う理由を説明してください（セクション 5）。
3. `PartnerNat` の除外がある場合とない場合について、単発のピークと継続的なピークそれぞれの `rate-login` による Count 一致数の予想を計算し、実際の数値が異なる理由（近似的なカウント、検出の遅延、レートが下がった後も制限が短時間続くこと）を述べてください。
4. Block に変更する各ルールについて、**ロールバックのトリガー**を記述してください。測定可能なしきい値、時間枠、担当者、具体的なアクションを含める必要があります。例: 「`rate-login` を Block に変更した後、`/login` の成功率がベースラインの 96% より 2 パーセントポイントを超えて低い状態が 10 分間連続した場合、または合成ログインチェックのリクエストが 1 件でもブロックされた場合は、オンコールエンジニアが `rate-login` を Count に戻し、変更を記録する。」ロールバック自体も数秒から数分かけて伝播し、レートベースルールの場合はカウントがリセットされることに注意してください。
5. モバイルの `/api/*` トラフィックに Challenge や CAPTCHA の代わりに何を適用するか、その理由とともに決めてください。
6. Anti-DDoS マネージドルールグループを計画に含めるか、含める場合は行 30 に対してどの位置に置くかを決めてください。

**レビュー基準:**

- 予想される数値はすべてベースライン表から算出し、計算過程を示すこと。
- Block にする各ルールについて、マネージドルールグループ内の Count 一致を確認できる証拠（ログまたはラベル）があること。サンプリングされたリクエストだけに頼らないこと。
- 一度に変更するルールは 1 つとし、結果を判断する前に伝播を待つ時間を設けること。
- 計画によってオリジンを露出させたり、インターネット向けロードバランサーを追加したり、パブリック CIDR を許可したりしないこと。

## 11. 障害と復旧の観察

この表は、**各診断を裏づける証拠**を考える演習です。後日、承認済み環境でシナリオを再現する場合は、ここに記載した証拠を正確に収集してください。

| 障害 | 予想される動作 | 証拠 | その証拠では証明できないこと |
|---|---|---|---|
| マネージドルールが正当なアップロードをブロックする | Block への変更直後、`/api/upload` が `403` を返す | WAF ログの `terminatingRuleId` = グループ、ルール `SizeRestrictions_BODY`。CloudFront の `403` 発生率が上昇 | グループ内のほかのルールが安全であること |
| 攻撃中にレート制限を変更した | 最大 1 分間、制限が停止する | 変更記録。Count または Block のメトリクスが低下してから戻る | 新しい上限が適切であること |
| Block から Count にロールバックする | 一部のロケーションでは短時間ブロックが続く | Block メトリクスが数秒から数分かけて低下する | その時点ですべてのロケーションに新しい設定が反映済みであること |
| 公開されたオリジンへの直接リクエスト | WAF メトリクスが平坦なまま、オリジンが過負荷になる | オリジンアクセスログに CloudFront の ENI 以外を送信元とするアドレスが記録される | 攻撃者がどの経路を見つけたか（セクション 8 の一覧で確認） |
| ディストリビューションへの L3/L4 フラッド | オリジンには影響しない | オリジンのメトリクスは平坦。サブスクリプション契約時は Shield Advanced イベント | アプリケーション層が安全であること |
| Anti-DDoS イベント | 正当なリクエストかどうかにかかわらず、すべてのリクエストに `event-detected` が付く | ラベルメトリクス | ラベルが付いたリクエストが悪意のあるものだったこと（それを示すのは疑わしさのラベルのみ） |
| モバイル API に Challenge を適用した | アプリのリクエストが失敗する | WAF ログでアプリのトラフィックに対する Challenge ルールが評価を終了したルールと示される。アプリのエラー率が上がる | クライアントがボットであること |

**復旧も変更の 1 つです。** 各ロールバックは Web ACL の更新であり、インシデントの原因となった変更と同じ伝播の動作を伴います。Block への変更を行う前に、ロールバックコマンドと担当者を計画に記載してください。インシデントが起きてから記載してはいけません。

## 12. 成果物と完了基準

| 成果物 | 完了基準 |
|---|---|
| 脅威マップ | セクション 2 のすべての攻撃について、経路上の阻止制御と担当者を記載している |
| Shield の判断 | Standard のみ、または Advanced を使う場合は、利用する機能、その前提条件（サポートプラン、ヘルスチェック）、費用を記載している |
| ルール計画 | 優先度、試験アクション、計算過程を示した一致の予想、誤検知への対応、ルールごとのロールバックトリガーを記載している |
| オリジン経路のレビュー | 参照経路でオリジンが隠蔽されていることを確認し、迂回経路一覧をチェックし、インターネット向けロードバランサーもパブリック CIDR からの ingress もないことを確認している |
| 証拠計画 | 各ルールについて、一致を証明するログフィールドまたはメトリクスと、既知の死角を記載している |

攻撃が狙うレイヤーと阻止される場所、AWS WAF のルールとアクションの評価方法、カウントモードのテストでルールごとのオーバーライドを使う理由、Shield Advanced が Standard に加えて提供するもの、オリジンにパブリックな経路があってはならない理由を、情報源を示しながら説明できれば完了です。[「WAF、エッジ、API セキュリティ」](../../security/14-waf-edge-api-security.md)で WAF の配置を復習し、[ワークブック 08](./08-cdn-edge-delivery.md#edge-origin-path)でオリジン経路を見直してから、[クイズ](../../quizzes/networking/expert/09-edge-security-waf-ddos-quiz.md)に取り組んでください。

## 参考資料

AWS WAF 開発者ガイド

- [AWS WAF のルールアクションの使用](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-action.html)（Allow、Block とデフォルトの `403`、Count、CAPTCHA、Challenge、Monetize）
- [ルールの優先度の設定](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-processing-order.html)
- [レートベースルールの概要設定](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based-high-level-settings.html)、[レートベースルールに関する注意事項](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based-caveats.html)
- [Web リクエストのラベリング](https://docs.aws.amazon.com/waf/latest/developerguide/waf-labels.html)、[ラベルの構文と命名要件](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-label-requirements.html)
- [ルールグループのアクションのオーバーライド](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-rule-group-override-options.html)
- [Web ACL 容量ユニット（WCU）](https://docs.aws.amazon.com/waf/latest/developerguide/aws-waf-capacity-units.html)
- [AWS リソースへの保護の関連付けまたは関連付け解除](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-associating-aws-resource.html)（US East（バージニア北部）のグローバル Web ACL、リソースごとに Web ACL は 1 つ）
- [ベースラインルールグループ](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-baseline.html)（コアルールセット、既知の悪意ある入力）、[ユースケース固有のルールグループ](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-use-case.html)（SQL データベース）、[アカウント乗っ取り防止ルールグループ](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-atp.html)、[Anti-DDoS ルールグループ](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-anti-ddos.html)
- [AWS WAF 保護のテストとチューニング](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing.html)、[モニタリングとチューニング](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing-activities.html)（カウントモード、誤検知への対処、伝播）
- [Web ACL トラフィックのロギング](https://docs.aws.amazon.com/waf/latest/developerguide/logging.html)、[ログの送信先](https://docs.aws.amazon.com/waf/latest/developerguide/logging-destinations.html)、[ロギングの設定](https://docs.aws.amazon.com/waf/latest/developerguide/logging-management-configure.html)（`aws-waf-logs-` プレフィックス、秘匿、フィルター）
- [Web リクエストのサンプルの表示](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing-view-sample.html)

AWS Shield（同じガイド内）

- [AWS Shield](https://docs.aws.amazon.com/waf/latest/developerguide/shield-chapter.html)、[Shield Standard の概要](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-standard-summary.html)
- [CloudFront と Route 53 における Shield の緩和ロジック](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-event-mitigation-logic-continuous-inspection.html)（正当な Web トラフィックのみ、TCP SYN プロキシ、エッジでの TLS、DNS と Anycast）
- [Shield Advanced の概要](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-advanced-summary.html)、[機能とオプション](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-advanced-summary-capabilities.html)、[保護対象リソース](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-advanced-summary-protected-resources.html)
- [Shield Advanced によるアプリケーション層の DDoS 緩和の自動化](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-automatic-app-layer-response.html)（2026 年 3 月 26 日以降のデフォルトは Anti-DDoS ルールグループ、150 WCU、ベースラインの学習に 24 時間から 30 日、CDN の背後にある ALB）
- [AWS Shield の料金](https://aws.amazon.com/shield/pricing/)

その他の AWS 資料

- [AWS WAF API リファレンス: CreateWebACL](https://docs.aws.amazon.com/waf/latest/APIReference/API_CreateWebACL.html)（`CLOUDFRONT` スコープと `us-east-1`、デフォルトアクション）、[RateBasedStatement](https://docs.aws.amazon.com/waf/latest/APIReference/API_RateBasedStatement.html)（上限の範囲、ウィンドウ、約 10 秒ごとのレートチェック、ネスト）
- [DDoS 耐性に関する AWS のベストプラクティス: インフラストラクチャ層の攻撃](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/infrastructure-layer-attacks.html)、[UDP リフレクション攻撃](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/udp-reflection-attacks.html)、[SYN フラッド攻撃](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/syn-flood-attacks.html)、[アプリケーション層の攻撃](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/application-layer-attacks.html)、[緩和手法](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/mitigation-techniques.html)、[エッジでの Web アプリケーション配信（BP1）](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/web-application-delivery-at-the-edge-bp1.html)
- [Amazon CloudFront 開発者ガイド: AWS WAF 保護の使用](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/distribution-web-awswaf.html)、[VPC origins によるアクセス制限](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html)
- [Elastic Load Balancing: HTTP ヘッダーと Application Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/x-forwarded-headers.html)（サーバーログに記録されるロードバランサーのアドレス、`X-Forwarded-For`）

標準規格とその他の一次資料

- [RFC 4987: TCP SYN Flooding Attacks and Common Mitigations](https://www.rfc-editor.org/rfc/rfc4987.html)（§2.2、§3.6）
- [BCP 38](https://www.rfc-editor.org/info/bcp38)（送信元アドレスの検証）
- [OWASP Top 10 2021](https://owasp.org/Top10/2021/)
- [Kubernetes: ネットワークポリシー](https://kubernetes.io/docs/concepts/services-networking/network-policies/)（`ipBlock`、送信元の書き換え、プラグインの要件）
- [RFC 1918](https://www.rfc-editor.org/rfc/rfc1918.html)、[RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.html)（例示用アドレス）

試験範囲（トピックの選択にのみ使用）

- [AWS Certified Advanced Networking - Specialty（ANS-C01）: ドメイン 4](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01-domain4.html)

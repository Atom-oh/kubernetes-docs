# 08. CDNとエッジ配信の設計

> **最終更新日**: 2026年11月19日
> **ラボの範囲**: 読み取り専用の観察。この演習では、CloudFrontで配信される公開アセットに対して`curl`リクエストを数回送信します。このワークブックでは、ディストリビューション、オリジン、VPC、ロードバランサーは作成しません。
> **検証状況**: Amazon CloudFront Developer Guide、AWS Knowledge Centerのページ、およびRFC 9111/5861を確認しました。執筆中に、CloudFrontで配信される公開アセットのヘッダーを確認し、**Hitレスポンスのみを観測しました**（Missは確認できませんでした）。ディストリビューションの**設定や測定は行っていません**。

このワークブックを終えると、リクエストが**どこで応答されるか**（エッジPOP、リージョナルエッジキャッシュ、Origin Shield、またはオリジン）を予測し、レスポンスヘッダーからその場所で応答された理由を説明し、CloudFront経由でしかオリジンに到達できないエッジからオリジンへの経路を図示できるようになります。

この章では基礎知識があることを前提とします。DNSキャッシュとTTLの動作については[Network Fundamentals Part 3](../../basics/06-network-fundamentals-part3.md)で説明しています。同ページには[HTTP/1.1メッセージの構造](../../basics/06-network-fundamentals-part3.md#http11-message-structure)も含まれています。TLSハンドシェイク、SNI、終端ポイントについては[Part 2](../../basics/06-network-fundamentals-part2.md)、CloudFront、ALB、ACMの役割については[Part 4](../../basics/06-network-fundamentals-part4.md)で整理しています。Part 3ではDNSキャッシュを扱いますが、HTTPキャッシュは扱わないため、この章で必要なHTTPキャッシュ用語はセクション6で定義します。BGPを使ったAnycastルーティングは[workbook 02](02-routing-policy-convergence.md)を、オリジン背後のプライベート接続は[workbook 07](07-wan-hybrid-connectivity.md)を基礎としています。

**準備するもの:** `curl`とインターネット接続が利用できるシェル。AWSアカウントは不要です。自分でリファレンス設計を構築すると、CloudFrontのリクエストとデータ転送、無料枠を超える無効化パス、Origin Shieldリクエスト、ロードバランサーの稼働時間、インスタンスの稼働時間に対して料金が発生します。**これらの費用とリソースのクリーンアップは、学習者自身の責任です**。既存の承認済みラボアカウント以外でリソースを作成しないでください。

## 1. 問いに答えることを意識して読む

試験範囲は、何を読むかを決めるためだけに使います。数値や動作は、左端の列に記載した公式ドキュメントに基づいています。

| 読むもの | 対応する試験範囲 | 自分の言葉で答える問い |
|---|---|---|
| [CloudFrontによるコンテンツ配信](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/HowCloudFrontWorks.html)、[Origin Shield](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/origin-shield.html) | ANS-C01 ドメイン1 ネットワーク設計、タスク1.1（エッジネットワークサービス） | どのリクエストがリージョナルエッジキャッシュを通らず、どのリクエストがOrigin Shieldを通らないか。 |
| [キャッシュキーを理解する](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html)、[ポリシーを使ってオリジンリクエストを制御する](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/controlling-origin-requests.html) | ANS-C01 ドメイン1および2（ネットワーク実装） | オリジンに渡す必要がある一方で、キャッシュキーには**含めてはいけない**ものは何か。 |
| [コンテンツをキャッシュに保持する期間を管理する](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Expiration.html)、[RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html)、[RFC 5861](https://www.rfc-editor.org/rfc/rfc5861.html) | ANS-C01 ドメイン2、プロトコルの原則 | オリジンの`s-maxage`とキャッシュポリシーの最大TTLが食い違う場合、どちらが優先されるか。 |
| [VPC originsでアクセスを制限する](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html)、[Amazon S3オリジンへのアクセスを制限する](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html) | ANS-C01 ドメイン4 ネットワークセキュリティ、コンプライアンス、ガバナンス | CloudFront経由以外ではオリジンに到達できないようにするものは何か。 |
| [CloudFrontのメトリクスを表示する](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/viewing-cloudfront-metrics.html)、[標準ログのフィールド](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/standard-logs-reference.html) | ANS-C01 ドメイン3 ネットワーク管理と運用 | どのフィールドを見れば、POPでのHitとOrigin ShieldでのHitを区別できるか。 |

読み終えたら、ビューワー、POP、リージョナルエッジキャッシュ、Origin Shield（使用する場合）、オリジンを図に描き、**キャッシュ階層**と**接続レッグ**を異なる線種で表してください。各レッグにはそれぞれ独自のTCPまたはQUIC接続とTLSセッションがあるため、「エンドツーエンドでHTTPS」という主張は、1つの接続ではなく、すべてのレッグについて述べるものです。

## 2. CDNを使う理由

CDNが変えるのは3つの要素です。設計では、そのうちどれを目的に導入するのかを明示してください。

| 目的 | 仕組み | 設計で明記する制約 |
|---|---|---|
| **レイテンシ（RTT）の低減** | ビューワーのTCP/QUICおよびTLSハンドシェイクは、遠方のオリジンではなく近くのPOPで終端します。キャッシュHitなら、オリジンへの往復はまったく発生しません | Missでは、POPからオリジンへの経路で遅延が発生します。Part 2では、完全なTLS 1.3ハンドシェイクに約1 RTTかかることを確認しました。このRTTは、ビューワーからPOPまでの短いものになります |
| **オリジンの負荷軽減** | Hitはオリジンに到達しません。リージョナルエッジキャッシュ、Origin Shield、リクエストの集約によってMissを減らします | Hit率はCDNだけで決まるのではなく、選択したキャッシュキーとTTLに左右されます（セクション5、6） |
| **トラフィックの吸収** | 1つのオリジンではなく、大規模な分散エッジにトラフィックが到達します | オリジンにCDNを迂回して到達できない場合に限り、トラフィック吸収によってオリジンを保護できます（セクション9）。大量トラフィック攻撃やL7攻撃への対策は、次のワークブック[エッジセキュリティ](./09-edge-security-waf-ddos.md)で扱います |

CloudFrontは、通常はレイテンシが最も低いなど、各リクエストを最適に処理できるエッジロケーションへルーティングし、オリジントラフィックをAWSネットワーク経由で転送します。

## 3. リクエストの振り分け: DNSベースとAnycast

ビューワーが**どのPOP**と通信するかを決める仕組みが必要です。一般的な方法は2つあります。

| 方法 | POPの選び方 | フェイルオーバーと粒度 | どこで使われるか |
|---|---|---|---|
| **DNSベース** | CDNの権威DNSが、適切なPOPのアドレスをビューワーのリゾルバーに応答します | リゾルバーが再問い合わせすると変更が有効になりますが、キャッシュ済みの応答の影響を受けます（Part 3: TTLを今下げても、すでにキャッシュされている応答の有効期間は短くなりません）。リゾルバーがクライアントサブネット情報を渡さない限り、権威サーバーに見えるのはビューワーではなく**リゾルバーの**アドレスです（[RFC 7871](https://www.rfc-editor.org/rfc/rfc7871.html)） | CloudFrontのデフォルト:「DNSは、リクエストを最適に処理できるCloudFront POP（エッジロケーション）へルーティングする」 |
| **Anycast** | 複数のサイトがBGP経由で**同じ**プレフィックスを広告し、通常のルーティングによって、トポロジー上最も近い広告元へ各パケットが届けられます（[RFC 4786](https://www.rfc-editor.org/rfc/rfc4786.html)） | フェイルオーバーはBGPの広告取り下げと収束に従います（workbook 02）。RFC 4786は、ルーティング変更によってセッションの残りが別のノードに送られる可能性があるため、ノードの選択をトランザクションより長く安定させる必要があると警告しています | CloudFront **Anycast static IPs**: 許可リストへの登録や、Aレコードでapexドメインを指定するための専用静的IPv4（またはIPv4とIPv6）アドレスのオプトインリスト。SNIで動作します |

**実際の運用では:** DNSベースの振り分けでは、遠方のリゾルバーの背後にいるビューワーが、ビューワーから遠いPOPに振り分けられることがあります。Anycastでいう「近い」とは、BGPホップ数が最も少ないか、最も優先度の高い経路という意味であり、レイテンシが最も低いという意味ではありません。どちらの方法でも、連続した2つのリクエストが同じPOPや同じサーバーに届く保証はありません。これはセクション11の演習で重要になります。

## 4. キャッシュ階層: POP、リージョナルエッジキャッシュ、Origin Shield、オリジン

**GETの処理方法:**

1. DNSがビューワーをPOPへルーティングします。オブジェクトがそのPOPにキャッシュされていて有効なら、POPが応答します。
2. POPでMissすると、POPは**通常**、最寄りの**リージョナルエッジキャッシュ**に問い合わせます。リージョナルエッジキャッシュは個々のPOPより大きなキャッシュを持つため、人気が落ちてPOPに置かれなくなったオブジェクトも、ここではより長くキャッシュに保持されます。
3. リージョナルエッジキャッシュでMissすると、CloudFrontは（有効になっていればOrigin Shieldを経由して）リクエストをオリジンへ転送します。レスポンスはリージョナルエッジキャッシュ経由でPOPに戻り、**両方**にコピーが保存されます。CloudFrontは最初の1バイトが届くとすぐに転送を開始します。

![CDNキャッシュのMISSからHITへのアニメーション。① クライアントAがディストリビューション名を名前解決します。DNSはレイテンシが最も低いエッジPOPで応答し、AはGET /img/logo.pngを送信します。② エッジPOPにそのキャッシュキーのオブジェクトがないためMISSとなり、リージョナルエッジキャッシュに問い合わせますが、ここでもMissします。③ CloudFront VPC origin経由で到達する内部ALBであるオリジンが、Cache-Control: max-age=3600とともに200を返します。④ 戻りの経路で、リージョナルエッジキャッシュとPOPがそれぞれコピーを保存し、クライアントAはx-cache: Miss from cloudfrontを受け取ります。⑤ クライアントBが同じPOPに同じオブジェクトを要求するとHITになります。POPがキャッシュからAge: 42とx-cache: Hit from cloudfrontを返し、オリジンにはリクエストが届きません。](../../.gitbook/assets/en-networking-expert-08-cdn-edge-delivery-anim-0.svg)

**リージョナルエッジキャッシュを通らないリクエスト**（Developer Guide）:

- プロキシHTTPメソッド`PUT`、`POST`、`PATCH`、`OPTIONS`、`DELETE`は、POPからオリジンへ直接送られます。
- リクエスト時に動的と判断されたリクエストは、オリジンへ直接送られます。
- オリジンがS3バケットで、リクエストに最適なリージョナルエッジキャッシュがそのバケットと同じリージョンにある場合、POPはバケットに直接アクセスします。

リージョナルエッジキャッシュはPOPと同等の機能を備えています。無効化すると、両方からオブジェクトが削除されます。

**Origin Shield**は、リージョナルエッジキャッシュとオリジンの間に置く、追加のオプションレイヤーです。すべてのCloudFrontキャッシュレイヤーからオリジンへのリクエストがOrigin Shieldを経由するため、各オブジェクトの取得に必要なオリジンリクエストを1回まで減らせます。オリジンと同じリージョンから行われるリクエストはOrigin Shieldを迂回します。オリジンへのレイテンシが最も低いリージョンをOrigin Shieldに選択してください（CloudFrontにリージョナルエッジキャッシュがある場所でのみ利用できます）。Origin Shieldに送られるリクエストごとに、**追加レイヤーとして**料金が発生します。動的リクエスト（`PUT`、`POST`、`PATCH`、`DELETE`、およびTTLが3600秒未満またはキャッシュが無効になっている`GET`/`HEAD`）は常に課金対象になり、キャッシュ可能なリクエストは、別のリージョンにあるリージョナルエッジキャッシュから到着した場合にのみ課金対象になります。AWSは、プロキシ経由の動的コンテンツ、キャッシュ可能性の低いコンテンツ、リクエスト頻度の低いコンテンツには適さないとしています。

**リクエストの集約:** 最初のMissがオリジンの応答を待っている間に同じキャッシュキーへのリクエストが増えると、CloudFrontはそれらを保留し、最初のレスポンスですべてに応答します。集約されるのは、同じキャッシュキーを持つリクエストだけです。ログでは、最初のリクエストは`Miss`、集約されたリクエストは`Hit`として表示されます。

## 5. キャッシュキーの設計とHit率

**キャッシュキー**は、キャッシュ内のオブジェクトを一意に識別するものです。リクエストから以前のリクエストと同じキャッシュキーが生成され、対象のオブジェクトがキャッシュされていて有効であればHitになります。RFC 9111では、最小のキーはリクエストメソッドとターゲットURIと定義されており、`Vary`によってリクエストヘッダーが追加されます。

**CloudFrontのデフォルト:** ディストリビューションのドメイン名とURLパスです。クエリ文字列、ヘッダー、Cookieは、デフォルトではキーに**含まれません**。Developer Guideでは、`/content/stories/example-story.html`に対するクエリ文字列、`User-Agent`、`Referer`、`session_id` Cookieの異なる2つのリクエストを示していますが、2つ目もHitになります。`OPTIONS`へのレスポンスは、`GET`や`HEAD`とは別にキャッシュされます。

**2つのポリシー、それぞれ異なる役割:**

| ポリシー | 制御するもの | ルール |
|---|---|---|
| **キャッシュポリシー** | キャッシュキーに含めるもの、および最小/デフォルト/最大TTL | 値はレスポンスを変える場合にのみ含める |
| **オリジンリクエストポリシー** | キーには追加せずに、Miss時にオリジンが受け取るもの | キャッシュキーに含まれるものはすべて自動的に転送されます。オリジンが必要とする一方で、キャッシュを分割してはならない値（分析、テレメトリ）にはこのポリシーを使用します |

オリジンリクエストには常にURLパスとボディが含まれます。また、`Host`、`User-Agent`、`X-Amz-Cf-Id`など、CloudFrontが自動的に追加するヘッダーも含まれます。

**キーを分割する要素と、その代替策:**

| 候補 | 問題 | 代替策 |
|---|---|---|
| `Accept-Language` | `en-US,en`、`en,en-US`、`en-US, en`、`en-US`はすべて英語を意味しますが、別々のオブジェクトが作られます | 言語をURLに含める（`/en-US/...`） |
| `User-Agent` | バリエーションが数千通りあります | キーから除外する |
| セッションCookie | ユーザーごとに一意であるため、ユーザーごとに専用コピーが作られます | キーから除外するか、レスポンスをキャッシュ不可にする |
| オリジンが無視するクエリ文字列 | オブジェクトが重複します | 除外するか、名前を指定したパラメーターだけを含める |

**Hit率**は、ビューワーリクエストのうちHitとなる割合です。キーに含める値を必要最小限に絞る、鮮度が許す範囲でTTLを長くする、ビューワーが複数のリージョンに分散している場合はOrigin Shieldを使うことで、Hit率を高められます。

## 6. TTL、Cache-Control、無効化

**ここで使用するHTTPキャッシュ用語**（RFC 9111）: 保存されたレスポンスは、鮮度の有効期間が過ぎるまでは**fresh**（新鮮）で、その後は**stale**（古い）になります。共有キャッシュ（CDN）は、`s-maxage`、次に`max-age`、次に`Expires`から`Date`を差し引いた値のうち、最初に該当するものを使って有効期間を計算します。staleレスポンスを使うには、通常、オリジンでの**検証**（`304 Not Modified`を返すことがある条件付きリクエスト）が必要です。`Age`ヘッダーは、オリジンでレスポンスが生成または検証されてからの秒数を送信者が推定した値です。このヘッダーがあるということは、オリジンがこのリクエストに対してレスポンスを生成したわけではないことを示します。レスポンスは、鮮度の有効期間が現在のAgeを上回っている間はfreshです。したがって、残り時間は有効期間から`Age`を差し引いた値になります。`no-cache`は、検証が成功しない限り、保存済みレスポンスを再利用してはならないことを意味します。`no-store`は、保存してはならないことを意味します。

**CloudFrontがオリジンヘッダーとキャッシュポリシーのTTLを組み合わせる方法:**

| オリジンが送信する値 | 最小TTL = 0 | 最小TTL > 0 |
|---|---|---|
| `Cache-Control: max-age` | CloudFrontは`max-age`と最大TTLの小さい方の期間、キャッシュします | 下限と上限に合わせて調整されます。最小TTL未満なら最小TTL、最大TTLを超えるなら最大TTLになります |
| `max-age` **と**`s-maxage` | CloudFrontは`s-maxage`を使います（最大TTLが上限）。ブラウザーは`max-age`を使います | `s-maxage`を最小TTLと最大TTLの範囲内に調整します |
| `max-age`なし | デフォルトTTL | 最小TTLとデフォルトTTLの大きい方 |
| `Expires` | その日時または最大TTLのうち、先に到来する方まで | 最小TTLと最大TTLの範囲内に調整されます |
| `no-cache`、`no-store`、および/または`private` | CloudFrontとブラウザーはヘッダーに従います | CloudFrontは**最小TTL**の期間、キャッシュします |

その他のルール:

- `max-age`と`Expires`の両方がある場合、CloudFrontは`max-age`のみを使います。
- GETでビューワーが送信する`Cache-Control`や`Pragma`によって、CloudFrontにオリジンへの再アクセスを強制することはできません。CloudFrontはこれらを無視します。
- キャッシュポリシーを使わない場合（レガシー設定）、デフォルトTTLは24時間です。
- **注意点:** 最小TTLが0より大きい場合、オリジンが`no-cache`を送信しても、最小TTLの期間はキャッシュされます。その後オリジンに到達できなくなり、最小**または**最大TTLが0より大きい場合、CloudFrontは以前取得したオブジェクトを配信します。そのため、最小TTLだけを下げても、この動作は止まりません。代わりにエラーを返させるには、オリジンのレスポンスに`Cache-Control: stale-if-error=0`を追加します。

**意図的にstaleを配信する:** CloudFrontは[RFC 5861](https://www.rfc-editor.org/rfc/rfc5861.html)の拡張機能をサポートします。

- `max-age=3600, stale-while-revalidate=600`: 1時間経過した後、CloudFrontはバックグラウンドで新しいレスポンスを取得しながら、最大10分間staleコピーを配信します。
- `max-age=3600, stale-if-error=86400`: 1時間経過した後、オリジンに到達できないか、5xxエラーが返された場合、CloudFrontは最大24時間staleコピーを配信し続けます。
- どちらの場合も、staleコンテンツが配信されるのは、ディレクティブと**最大TTL**の小さい方までです。

**無効化とバージョン付きファイル名の比較:**

| | 無効化 | バージョン付きファイル名（`app.3f9c.js`） |
|---|---|---|
| 効果 | POPとリージョナルエッジキャッシュからオブジェクトを削除します。次のリクエストはオリジンに送られます | 新しいURLは新しいキャッシュキーになるため、古いバージョンと新しいバージョンが共存します |
| ブラウザーと企業プロキシのキャッシュ | 影響を受けません。ユーザー側では、期限切れになるまで古いコピーが使われる場合があります | ページが新しい名前を参照するため、すべてのキャッシュが新しいものを取得します |
| 料金 | アカウントごとに毎月最初の1,000無効化パスは無料で、その後はパスごとに課金されます。削除するファイル数にかかわらず、`*`ワイルドカードパスは1パスとして数えられます | 無効化料金はありませんが、新しいバージョンをエッジに転送する費用は発生します |
| レートクォータ | 1秒あたり150パスまたはタグ、1秒あたり1ワイルドカード無効化（Developer Guideのクォータページ） | なし |
| ロールバック | 再度無効化する | ページが古い名前を参照するように戻す |

AWSは、頻繁に更新するファイルにはバージョン付きファイル名を推奨しています。CloudFront FAQとKnowledge Centerの記事には、以前の「同時に進行中」の上限（ディストリビューションごとに個別ファイル3,000件、ワイルドカードパス15件）が現在も記載されています。最新の情報源はDeveloper Guideのクォータページなので、設計時に確認してください。

## 7. エッジでのTLSとオリジンへのTLS

ビューワー側のレッグとオリジン側のレッグは、別々のTLSセッションです（Part 2: ある地点で終端しても、次のホップが暗号化されるわけではありません）。

**ビューワーからCloudFront:**

- ビューワープロトコルポリシーでは、HTTPとHTTPSを許可する、HTTPをHTTPSにリダイレクトする、HTTPSのみを必須にする、のいずれかを指定できます。
- CloudFrontディストリビューション用のACM証明書は、**米国東部**（バージニア北部）でリクエストまたはインポートする必要があります。CloudFrontが証明書を各ロケーションに配布します。
- HTTP/2にはTLS 1.2以降とSNIをサポートするビューワーが必要です。HTTP/3にはTLS 1.3とSNIが必要です。

**CloudFrontからオリジン:**

- オリジンプロトコルポリシーは、HTTPのみ、HTTPSのみ、ビューワーに一致、のいずれかです。ビューワーポリシーがHTTPSへのリダイレクトまたはHTTPSのみの場合に限り、「ビューワーに一致」を選択してください。
- オリジン証明書は、ディストリビューションで指定したオリジンドメイン名と一致する必要があります。`Host`ヘッダーを転送する場合は、そのヘッダーと一致する必要があります。CloudFrontは、その名前をSNIとしても送信します。一致しない証明書、信頼できるCAが発行していない証明書、チェーンが壊れている証明書、または期限切れの証明書の場合、CloudFrontは接続を切断し、ビューワーに`502`を返します。
- ALBオリジンの場合、ALBの証明書は**ALBのリージョン**に置かれます。us-east-1のビューワー用証明書とは別です。
- **VPC origin**を使う場合、CloudFrontはパブリックDNSの名前解決ではなくARNを使って内部ALBに到達します。設定するホスト名はSNIと証明書の照合にのみ使われるため、内部ALBを指すパブリックDNSレコードは必要ありません（AWS Networking blog、2026年）。

**実際の運用では:** 各レッグについて、プロトコル、証明書とそのリージョン、最小TLSバージョン、証明書の更新担当者を記録してください。設計レビューで「HTTPS」と記載するなら、表の両方の行を埋める必要があります。

## 8. 動的コンテンツの高速化、HTTP/2、HTTP/3

すべてのコンテンツがキャッシュ可能とは限りませんが、CDNはキャッシュできないトラフィックにも役立ちます。

- **ビューワーとの短いハンドシェイク:** TCP/QUICとTLSのハンドシェイクは、近くのPOPとの間で実行されます。
- **オリジンとの永続的な接続:** レスポンスの後、CloudFrontは次のリクエストが新しいTCPおよびTLSハンドシェイクを省略できるよう、オリジン接続を数秒間開いたままにします（カスタムオリジンとVPC originsではKeep-Aliveタイムアウトを設定可能）。
- **AWSネットワーク:** エッジとAWSリージョン内のオリジン間のトラフィックは、AWSネットワーク内にとどまります。
- **動的リクエストはリージョナルエッジキャッシュを通らない**ため（セクション4）、余分なキャッシュ検索によって遅くなることはありません。

**レッグごとのプロトコルバージョン:**

| レッグ | バージョン | 備考 |
|---|---|---|
| ビューワー ↔ CloudFront | HTTP/1.0と1.1はデフォルトで有効。HTTP/2とHTTP/3は有効化可能 | HTTP/3はQUIC上のUDPで動作し、CloudFrontは接続の移行をサポートします。そのため、ビューワーは接続を失わずにネットワークを切り替えられます |
| CloudFront → カスタムオリジン | HTTP/1.1 | ビューワー側でのHTTP/2多重化はオリジンには引き継がれません。オリジンの接続容量を適切に計画してください |

HTTP/2とHTTP/3はHTTPのセマンティクスを維持しつつフレーミングを変更するため（Part 3）、キャッシュキーとTTLはどのバージョンでも同じように動作します。

## 9. CloudFrontの機能対応とエッジからオリジンへの経路

| 概念 | CloudFrontの機能 | 設計上の注意点 |
|---|---|---|
| キャッシュキーとTTL | キャッシュポリシー | キーに含める値を最小限にし、ビヘイビアごとにTTLを設定 |
| キャッシュを分割せずに転送 | オリジンリクエストポリシー | オリジンが必要とするが、キャッシュのバリエーションにしてはならない値 |
| パスごとのビヘイビア | キャッシュビヘイビア（パスパターン） | 例: `/assets/*`は長いTTLとバージョン付きファイル名、`/api/*`はキャッシュ無効 |
| プライベートS3オリジン | オリジンアクセスコントロール（OAC） | レガシーのOAIより推奨 |
| プライベートなALB、NLB、EC2オリジン | VPC origin | 以下のホームラボ用リファレンス設計 |

**S3用OAC:** CloudFrontがオリジンリクエストに署名し、バケットポリシーがそのディストリビューションだけを許可します。AWSはOAIよりOACを推奨しています。OACは、すべてのリージョン（2022年12月以降に提供開始されたオプトインリージョンを含む）のS3バケット、SSE-KMS、動的リクエスト（`PUT`、`DELETE`）をサポートするためです。OACを使う場合、S3 Object Ownershipは**Bucket owner enforced**（新しいバケットのデフォルト）にする必要があります。S3の**ウェブサイトエンドポイント**はカスタムオリジンであり、OACを使用できません。

<a id="edge-origin-path"></a>

### エッジからオリジンへの経路: VPC originから内部ALBへ

**リファレンス設計:** CloudFront → **VPC origin** → プライベートサブネット内の**内部**ALB → ターゲットグループ。オリジンにパブリックアドレスはなく、インバウンドを許可する送信元はCloudFrontのみです。CloudFrontの背後にインターネット向けロードバランサーを配置しないでください。また、オリジンへのパブリックCIDRからのアクセスを許可するインバウンドルールを決して追加しないでください。

![エッジからオリジンへの経路を示すアニメーション。① ビューワーが、キャッシュ可能なGET /menu.jsonをHTTPSで送信します。TLSはエッジPOPで終端され、POPとリージョナルエッジキャッシュの両方でリクエストがMissします。② CloudFrontはVPC origin経由でオリジンに接続します。プライベートサブネット内のサービス管理ENI（例: 10.0.11.25）が内部ALB（10.0.12.40）への接続を開始します。③ ALBのセキュリティグループは、CloudFront-VPCOrigins-Service-SG（またはCloudFrontのオリジン向けマネージドプレフィックスリスト）からのトラフィックのみを許可します。④ ALBリスナーはターゲットグループに転送し、ターゲットはALBのセキュリティグループからのトラフィックのみを許可します。⑤ インターネット上のクライアントがALBに直接接続しようとしても失敗します。内部ALBにはプライベートアドレスしかないため、インターネットからルーティングできず、接続の試みはVPCに到達しません。VPCにはインターネットゲートウェイがアタッチされていますが、この経路のルーティングには使われません。](../../.gitbook/assets/en-networking-expert-08-cdn-edge-delivery-anim-1.svg)

**VPC originの要件**（Developer Guide）:

- **オリジンの種類:** プライベートサブネットに完全にデプロイされ、Active状態にあるALB、NLB、またはEC2インスタンス。Gateway Load BalancerとTLSリスナーを備えたNLBはオリジンにできません。また、NLBにはセキュリティグループがアタッチされている必要があります。
- **VPC:** VPCには**インターネットゲートウェイがアタッチされている**必要があります。これはVPCがインターネットからトラフィックを受信できることを示しますが、オリジンへのルーティングには**使用されず**、ルートテーブルの変更も必要ありません。
- **サブネット:** CloudFrontはプライベートサブネット内にサービス管理ENIを作成します。ここには少なくとも1つの空きIPv4アドレス（デュアルスタックの場合はIPv6アドレスも1つ）が必要です。
- **セキュリティグループ:** オリジンにはセキュリティグループが必要です。事前に追加できる**CloudFrontマネージドプレフィックスリスト**（`com.amazonaws.global.cloudfront.origin-facing`。デュアルスタックの場合はIPv6リストも追加）か、VPC **originの作成後に使用できるサービス管理の`CloudFront-VPCOrigins-Service-SG`のいずれかからのインバウンドを許可します**。後者のほうが、自分のディストリビューションのみを許可するため、より制限的です。このセキュリティグループを編集したり、同じ名前のプレフィックスで独自のグループを作成したりしないでください。
- **サポート対象外:** gRPC、Lambda@Edgeのオリジンリクエストトリガーとオリジンレスポンストリガー。CloudFrontからオリジンへのトラフィックではインバウンドNACLルールは評価されませんが、戻りの経路では**アウトバウンド**NACLルールが評価されます。CloudFrontのオリジン向け範囲に対して、エフェメラルTCPポート1024～65535を許可する必要があります。
- **クォータ:** アカウントあたりVPC origins 25個（引き上げ可能）、VPC originあたりディストリビューション50個。

**内部ALBにCloudFrontを迂回して到達できない理由:** 内部ロードバランサーのノードにはプライベートIPアドレスしかありません。そのDNS名はパブリックに名前解決できますが、名前解決の結果はプライベートアドレスなので、VPCにアクセスできるクライアントしか到達できません。これはフィルターではなくルーティングの特性であり、後からセキュリティグループルールを緩和しても変わりません。ALBがKubernetes Ingressから作られる場合、[AWS Load Balancer Controller](../03-aws-lb-controller.md)が`alb.ingress.kubernetes.io/scheme: internal`を設定します。

**プレフィックスリストとサービスセキュリティグループ:** マネージドプレフィックスリストにはCloudFrontのすべてのオリジン向けサーバーが含まれるため、**どの**ディストリビューションからのトラフィックも許可します。VPC originサービスグループが許可するのは自分のディストリビューションのみです。インバウンドルールとして使う場合、プレフィックスリストはセキュリティグループルールのクォータに対して55ルール分として数えられます。[WAF, Edge and API Security](../../security/14-waf-edge-api-security.md)では、WAFの配置を説明し、この設計と、より脆弱なパブリックALBオリジン（プレフィックスリストとシークレットヘッダーを使用）を比較します。後者はホームラボ用リファレンス設計では使いません。次のワークブック[エッジセキュリティ](./09-edge-security-waf-ddos.md)では、この経路を基に攻撃側の視点を扱います。

## 10. 可観測性: 各シグナルから分かること

| シグナル | 場所 | 分かること |
|---|---|---|
| `x-cache`レスポンスヘッダー | ビューワーへのレスポンス | `Hit from cloudfront`、`RefreshHit from cloudfront`（期限切れコピーがオリジンで再検証された）、または`Miss from cloudfront` |
| `Age` | ビューワーへのレスポンス | コピーがオリジンで生成または検証されてからの秒数。Hitの場合、`Date`と`Age`を合わせると現在時刻にほぼ相当します |
| `x-amz-cf-pop` | ビューワーへのレスポンス | 応答したPOP。2回目のMissから何か結論を出す前に、リクエスト間で比較してください |
| `Via` | ビューワーへのレスポンス | メッセージを処理した中継者（[RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)）。同じPOPへの2つのリクエストでもサーバー識別子は異なる場合があります |
| `x-edge-result-type` | 標準ログ | `Hit`、`RefreshHit`、`Miss`、`LimitExceeded`、`CapacityExceeded`、`Error`、`Redirect`。WebSocketとgRPCは常に`Miss`です |
| `x-edge-detailed-result-type` | 標準ログ | 記載されたケースを除き、`x-edge-result-type`と同じ値です。Origin Shieldが配信した場合は`OriginShieldHit`（Origin Shieldとして機能するリージョナルエッジキャッシュにルーティングされたリクエストは`Hit`として記録されます） |
| `time-to-first-byte` | 標準ログ | リクエストを受信してから最初のバイトを書き込むまでの秒数。サーバー側で測定されます |
| キャッシュHit率、オリジンレイテンシ | CloudWatch追加メトリクス（有料。ディストリビューションあたり最大8個。us-east-1で発行） | Hit率はキャッシュ可能なリクエストのみを数えます（`POST`、`PUT`、エラーは対象外）。オリジンレイテンシは、オリジンから配信されたリクエストの最初のバイトまでのレイテンシです |

**2回目のリクエストもMissになる理由**（AWS Knowledge Center）: 各エッジロケーションがキャッシュするのは、実際に受け取ったものだけです。そのため、別のPOPに届いたリクエストはMissになります。リクエスト頻度の低いオブジェクトは、有効期限前にエビクトされることがあります。キャッシュキーに含まれるヘッダー、Cookie、クエリ文字列によってリクエストが分割される場合もあります。また、オリジンの`Cache-Control`や`Expires`によって有効期間が短くなることもあります。

## 11. 演習: レスポンスヘッダーからMissとHitを読み取る

これは読み取り専用の観察です。結果には「**第三者のディストリビューションを観察**」と明記してください。そのキャッシュポリシーを見ることはできないため、結論はすべてヘッダーからの推論になります。

**対象を選ぶ:** レスポンスに`x-cache: ... from cloudfront`と`x-amz-cf-pop`が含まれる、公開されている任意の静的アセット（画像、CSS、JavaScriptファイル）を選びます。特定のサイトの挙動を決めつけず、最初にヘッダーを確認してください。自分が所有する承認済みディストリビューションがあるなら、既知のポリシーと比較できるため、そちらを使ってください。

```bash
URL='https://<cloudfront-served-host>/<path-to-static-asset>'
curl -sI "$URL" | grep -iE '^(HTTP|date|age|cache-control|x-cache|via|x-amz-cf-pop)'
sleep 5
curl -sI "$URL" | grep -iE '^(HTTP|date|age|cache-control|x-cache|via|x-amz-cf-pop)'
```

`curl -I`は`HEAD`を送信します。Developer Guideによると、`GET`および`HEAD`とは別にキャッシュされるレスポンスは`OPTIONS`のみです。したがって、ここに表示されるヘッダーは、`GET`で使われるものと同じキャッシュオブジェクトを示しています。ボディを破棄して実際の`GET`を繰り返すには、`curl -s -o /dev/null -D - "$URL"`を使ってください。

**出力例**（形式のみを示したもので、特定のサイトから取得したものではありません。値は異なります）:

```text
HTTP/2 200
date: Thu, 19 Nov 2026 09:00:00 GMT
cache-control: max-age=86400
x-cache: Miss from cloudfront
via: 1.1 <edge-server-id-1>.cloudfront.net (CloudFront)
x-amz-cf-pop: <POP-code>

HTTP/2 200
date: Thu, 19 Nov 2026 09:00:00 GMT
cache-control: max-age=86400
x-cache: Hit from cloudfront
via: 1.1 <edge-server-id-2>.cloudfront.net (CloudFront)
x-amz-cf-pop: <POP-code>
age: 5
```

**解釈のルール:**

| 観測したもの | 結論 | 次に確認すること |
|---|---|---|
| 同じ`x-amz-cf-pop`でMissの後にHit | 最初のリクエストがこのPOPのキャッシュ（または、そのPOPが参照したリージョナルキャッシュ）を埋めました。2回目はオリジンを経由せずに配信されました | `age`はリクエスト間の時間差に近い値です。`date`は変わりません |
| **最初の**リクエストでHit | ほかのビューワーがすでにキャッシュを埋めていました | `date` + `age` ≈ 現在時刻です。`age`が`max-age`に近ければ、もうすぐ期限切れになります |
| Missの後もMiss | 異なるPOP、エビクション、異なる値を含むキャッシュキー、またはキャッシュ不可のレスポンスが考えられます | `x-amz-cf-pop`を比較し、`cache-control`に`no-store`、`private`、`max-age=0`が含まれるか確認します |
| `RefreshHit` | コピーは期限切れになっていて、オリジンで再検証されました | `age`はほぼ0から再び始まります |
| POPは同じだが`via`のサーバー識別子が変化 | 同じPOP内の別のサーバーが応答しました。キャッシュオブジェクトは見つかりました | 対応は不要です |

**タスク:**

1. 2つのリクエストを実行し、それぞれの`x-amz-cf-pop`、`x-cache`、`age`、`date`、`cache-control`を記録します。
2. `date` + `age`を計算して時計と比較し、差を説明します。
3. `cache-control`から、共有キャッシュがコピーを何秒間freshとして扱えるかを述べ、CDNが`s-maxage`と`max-age`のどちらを使うか説明します。ディストリビューションの最小TTLと最大TTLによって何が変わるかも、セクション6の表を引用して述べます。
4. 最初のリクエストですでにHitだった場合、その理由を説明します。キャッシュ回避用のクエリ文字列を付けても、確実にMissを強制できるわけではありません。キャッシュポリシーでクエリ文字列がキーから除外されている場合（CloudFrontのデフォルト）、`?x=1`を付けても同じオブジェクトがHitになります。試す場合は、他者のサイトに対してこのようなリクエストを最大1回だけ送り、キャッシュキーを使って結果を説明してください。
5. **設計課題（机上確認）:** `/assets/*`（バージョン付きファイル名）、`/index.html`、`/api/*`があるサイトについて、キャッシュキーに含める内容、TTL、オリジンリクエストポリシー、無効化計画、Origin Shieldにリクエストごとの料金を払う価値があるかどうかを記したキャッシュビヘイビアの表を作成します。次に、セクション9に沿ってオリジン経路を描き、セキュリティグループルールを列挙します。

**評価基準:**

- すべての結論が、セクション4～6または10のヘッダーとルールを根拠として示している。
- POPコードを比較する前に、2回目のMissを「キャッシュが壊れている」と報告していない。
- 設計課題にインターネット向けロードバランサーやインバウンドルールのパブリックCIDRが含まれていない。また、`/api/*`は何もキャッシュしないか、レスポンスを変える値をすべて含むキャッシュキーを使っている。

## 12. 障害と復旧の観察

この表を使って、各判定を確定するために**どんな証拠が必要か**を判断してください。承認済みの既存環境で後からシナリオを再現する場合は、その証拠を収集してください。

| 障害 | 予想される動作 | 証拠 | その証拠だけでは分からないこと |
|---|---|---|---|
| オリジン停止、オブジェクトはまだfresh | Hitは継続し、Missは失敗します | `age`が増加する`x-cache: Hit`、ログのMissに対する`Error`結果 | すべてのオブジェクトがキャッシュされているかどうか |
| オリジン停止、オブジェクトはstale、`stale-if-error`設定あり | ディレクティブと最大TTLの小さい方の期間、staleコピーが配信されます | `max-age`を超える`age`、ログのオリジンエラー | 停止がどれくらい続いたか |
| オリジン停止、最小または最大TTLが0より大きく、`stale-if-error=0`なしの`no-cache` | 以前に取得したコピーが配信される場合があります（セクション6の注意点） | エラーになるはずだと思っていたレスポンス | そのコンテンツについて、この動作が許容できるかどうか |
| キャッシュキーの拡大（ヘッダーやCookieの追加） | Hit率が低下し、オリジンレイテンシとオリジン負荷が増加します | CloudWatchのキャッシュHit率、オリジンリクエスト数 | どの値がキーを分割したか（ポリシーを比較してください） |
| オリジン証明書の不一致または期限切れ | Miss時にビューワーへ`502`が返されます | ビューワーの`502`、オリジンのTLSエラー | Hitが影響を受けたかどうか（影響を受けません） |
| セキュリティグループ変更でCloudFrontの送信元を除外 | Missは接続に失敗し、Hitは継続します | Miss時の`504`（CloudFrontからのトラフィックをブロックするオリジンのファイアウォールやセキュリティルールは504を返します）、SGルールの履歴 | 内部ALBがインターネットから到達可能になったかどうか（パブリックアドレスがないため、到達できません） |
| 不適切なデプロイを無効化で修正 | エッジは再取得しますが、ブラウザーやプロキシには古いコピーが残る場合があります | 無効化の状態、`x-cache: Miss`の後に`Hit` | ユーザーのブラウザーが更新されたかどうか（それを実現するのはバージョン付きファイル名のみ） |

**復旧は負荷イベントです。** 無効化後やオリジン停止後には、多くのPOPで同時にMissが発生します。リージョナルエッジキャッシュ、Origin Shield、リクエストの集約によってオリジンリクエスト数は減りますが、再充填に必要なオリジン容量を計画してください。エラーを観測しなかったとしても、それはサンプリングで検出できなかったことを意味するだけです。

## 13. 成果物と完了基準

| 成果物 | 完了条件 |
|---|---|
| 経路図 | ビューワー、POP、リージョナルエッジキャッシュ、Origin Shield（使用する場合）、オリジンを図示し、キャッシュ階層と接続レッグを区別して、リージョナルエッジキャッシュを通らないリクエストに印を付けている |
| ヘッダーの観察記録 | 2つのリクエストについて、POP、`x-cache`、`age`、`date`、`cache-control`を記録し、それぞれの結論をルールと結び付けている |
| キャッシュビヘイビアの表 | パスごとのキャッシュキー、TTL、オリジンリクエストポリシー、無効化またはバージョン管理の計画を記載し、Origin Shieldの採否を根拠とともに説明している |
| オリジン経路とルール | VPC originから内部ALBへの経路、セキュリティグループルールの送信元（サービスグループまたはプレフィックスリスト）、レッグごとのTLS表を記載している |
| 障害の表 | 各行に予想される動作、証拠、その証拠の限界を記載している |

リクエストがどのようにPOPへ振り分けられ、どの階層がなぜ応答するのか、キャッシュキーとTTLのルールがHit率をどう決めるのか、無効化とバージョン付きファイル名の違い、そしてCloudFront経由以外ではオリジンに到達できない理由を、情報源を示して説明できれば完了です。同じ経路の攻撃側については、次のワークブック[エッジセキュリティ](./09-edge-security-waf-ddos.md)に進み、[WAF, Edge and API Security](../../security/14-waf-edge-api-security.md)でWAFの配置を確認し、[クイズ](../../quizzes/networking/expert/08-cdn-edge-delivery-quiz.md)に取り組んでください。

## 参考資料

Amazon CloudFront Developer Guide

- [Amazon CloudFrontとは](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html)（低レイテンシのルーティング、AWSネットワーク）
- [CloudFrontによるコンテンツ配信](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/HowCloudFrontWorks.html)（POPへのDNSルーティング、リージョナルエッジキャッシュ、リージョナルエッジキャッシュを通らないリクエスト）
- [Amazon CloudFront Origin Shieldを使用する](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/origin-shield.html)（迂回、リージョン、料金の仕組み、`OriginShieldHit`）
- [キャッシュキーを理解する](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html)、[ポリシーを使ってオリジンリクエストを制御する](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/controlling-origin-requests.html)
- [コンテンツをキャッシュに保持する期間を管理する（有効期限）](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Expiration.html)（TTLの表、`stale-while-revalidate`、`stale-if-error`、最小TTLの警告）
- [コンテンツを削除するためにファイルを無効化する](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html)、[ファイル無効化の料金](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/PayingForInvalidation.html)
- [クォータ](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cloudfront-limits.html)（無効化レート、VPC origins、オリジンアクセスコントロール）
- [カスタムオリジンでのリクエストとレスポンスの動作](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/RequestAndResponseBehaviorCustomOrigin.html)（オリジンへのHTTP/1.1、永続的接続、リクエストの集約、`Via`、オリジンプロトコル）
- [ディストリビューション設定のリファレンス](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/DownloadDistValuesGeneral.html)（サポートされるHTTPバージョン、HTTP/2とHTTP/3の要件）
- [CloudFrontとカスタムオリジン間でHTTPSを必須にする](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-https-cloudfront-to-custom-origin.html)（オリジンプロトコルポリシー、オリジン証明書名）
- [Amazon S3オリジンへのアクセスを制限する](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)（OAC）
- [VPC originsでアクセスを制限する](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html)（要件、セキュリティグループ、制限）
- [CloudFrontエッジサーバーのロケーションとIPアドレス範囲](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/LocationsOfEdgeServers.html)（マネージドプレフィックスリスト）
- [Anycast静的IPをリクエストする](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/request-static-ips.html)
- [CloudFrontとエッジ関数のメトリクスを表示する](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/viewing-cloudfront-metrics.html)（キャッシュHit率、オリジンレイテンシ）、[標準ログファイルのフィールド](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/standard-logs-reference.html)
- [Application Load Balancerへのアクセスを制限する](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/restrict-access-to-load-balancer.html)（ALBの証明書リージョンとus-east-1のビューワー用証明書の違い）
- [HTTP 504ステータスコード（ゲートウェイタイムアウト）](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/http-504-gateway-timeout.html)（オリジンのファイアウォールがCloudFrontをブロックする場合）

その他のAWS資料

- [Elastic Load Balancingの仕組み](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/how-elastic-load-balancing-works.html)（内部ロードバランサーのスキーム）
- [AWS whitepaper: オリジンHTTPSの設定](https://docs.aws.amazon.com/whitepapers/latest/secure-content-delivery-amazon-cloudfront/origin-https-configuration.html)（オリジン証明書の条件、SNI、`502`）
- [AWS Knowledge Center: CloudFrontがサポートするプロトコル](https://repost.aws/knowledge-center/cloudfront-supported-protocols)（デフォルトで有効なHTTP/1.0と1.1、カスタムオリジンへのHTTP/1.1）
- [AWS Knowledge Center: X-Cache: Miss from CloudFront](https://repost.aws/knowledge-center/cloudfront-x-cachemiss-error)、[カスタムオブジェクトのキャッシュとオリジンヘッダー](https://repost.aws/knowledge-center/cloudfront-custom-object-caching)（`x-cache`の値、`x-amz-cf-pop`）
- [AWS Knowledge Center: 米国東部（バージニア北部）で証明書を関連付ける](https://repost.aws/knowledge-center/migrate-ssl-cert-us-east)
- [Amazon CloudFront FAQ](https://aws.amazon.com/cloudfront/faqs/)（以前の同時無効化上限）、[Amazon CloudFrontの料金](https://aws.amazon.com/cloudfront/pricing/)
- [AWS Networking blog: CloudFront VPC Originsを使ったプライベートAIエージェント](https://aws.amazon.com/blogs/networking-and-content-delivery/private-ai-agent-with-websocket-streaming-over-cloudfront-vpc-origins-and-the-next-generation-of-opensearch-serverless-for-knowledge-retrieval/)（ARNによるVPC originのルーティング、オリジン証明書）
- [AWS Networking blog: CloudFront用マネージドプレフィックスリスト](https://aws.amazon.com/blogs/networking-and-content-delivery/limit-access-to-your-origins-using-the-aws-managed-prefix-list-for-amazon-cloudfront/)（ルールウェイト55）

標準規格

- [RFC 9111: HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111.html)（キャッシュキー、鮮度、`Age`、`no-cache`、`s-maxage`）
- [RFC 5861: 古いコンテンツ向けHTTP Cache-Control拡張](https://www.rfc-editor.org/rfc/rfc5861.html)
- [RFC 9110: HTTPセマンティクス](https://www.rfc-editor.org/rfc/rfc9110.html)（`Via`）
- [RFC 4786: Anycastサービスの運用](https://www.rfc-editor.org/rfc/rfc4786.html)、[RFC 7871: DNSクエリのクライアントサブネット](https://www.rfc-editor.org/rfc/rfc7871.html)
- [RFC 1918](https://www.rfc-editor.org/rfc/rfc1918.html)（例示用アドレス）

試験範囲（トピック選定のみに使用）

- [AWS Certified Advanced Networking - Specialty（ANS-C01）試験ガイド](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01.html)

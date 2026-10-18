# ネットワークの基礎 パート 3 クイズ: アプリケーションプロトコル

> **最終更新日**: 2026 年 9 月 14 日

DNS から MQTT まで、アプリケーション層の 10 プロトコルに関する理解を確認します。

## 選択問題

1. HTTP/3 を有効にしても速度が向上しない場合、トランスポート層でどのような確認が役立ちますか？
   - A) サーバー証明書の有効期限
   - B) UDP 443 に到達できるか、および HTTP/3 が実際にネゴシエートされたか
   - C) DNS TTL の設定
   - D) HTTP/2 のヘッダー圧縮（HPACK）設定

<details>
<summary>解答を表示</summary>

**解答: B) UDP 443 に到達できるか、および HTTP/3 が実際にネゴシエートされたか**

**解説:**
HTTP/3 は一般に UDP 443 上で QUIC を使用します。その経路がブロックされると、クライアントは利用可能な場合に TCP ベースの HTTP/2 または HTTP/1.1 を使うことがあります。性能を比較する前に、ネゴシエートされたプロトコルを確認してください。損失、RTT、ワークロード、実装、CPU／オフロードの動作がすべて結果に影響します。この問題だけでは、実際のインシデント原因は特定できません。

</details>

2. 権威 DNS レコードを変更した後も、DNS フェイルオーバーが遅れることがある要因は何ですか？
   - A) DNS は TCP だけを使うため、ハンドシェイクのコストが大きい
   - B) 以前にキャッシュされた応答、アプリケーションのキャッシュ、既存の接続がレコード変更後も残ることがある
   - C) ルートネームサーバーが更新を承認しなければならない
   - D) A レコードは変更できない

<details>
<summary>解答を表示</summary>

**解答: B) 以前にキャッシュされた応答、アプリケーションのキャッシュ、既存の接続がレコード変更後も残ることがある**

**解説:**
TTL を新たに短くしても、古い TTL でキャッシュ済みの応答の有効期間は短縮されません。障害検出、レコード更新、アプリケーションキャッシュ、接続再利用も復旧時間に影響します。定められた障害条件では、resolver が古いデータを提供する場合があります（RFC 8767）。DNS、ロードバランサー、Anycast の各設計で、障害時と収束時の動作を測定する必要があります。

</details>

3. ブラウザーが承認されていないパブリック DoH resolver を選ぶと、どのようなポリシー上の問題が起こることがありますか？
   - A) DNS 応答が大きくなり、帯域幅が無駄になる
   - B) 組織の resolver ポリシーを迂回し、プライベート名を解決できなくなることがある
   - C) UDP ポート 53 が過負荷になる
   - D) DNSSEC と互換性がない

<details>
<summary>解答を表示</summary>

**解答: B) 組織の resolver ポリシーを迂回し、プライベート名を解決できなくなることがある**

**解説:**
DoH は HTTPS によってクライアントと resolver の間の通信を保護し、完全性も確保します。別のパブリック resolver を使うと組織の resolver 側の制御を迂回することがあります。一方で、管理された DoH 自体がポリシーとログ記録を提供する場合もあります。承認済み resolver を選び、endpoint ポリシーを設定し、split DNS をテストしてください。暗号化しても、resolver の endpoint やすべてのトラフィックメタデータが不可視になるわけではありません。

</details>

4. L4 ロードバランサーで gRPC トラフィックが少数のバックエンドに集中することがあるのはなぜですか？
    - A) Protocol Buffers のシリアライゼーションが非対称だから
    - B) 長時間維持される接続を多数の RPC が共有でき、L4 バランシングは接続ごとにバックエンドを選択するから
    - C) ロードバランサーで HTTP/2 ヘッダー圧縮が壊れるから
    - D) gRPC は UDP ベースなので、L4 バランシングは不可能だから

<details>
<summary>解答を表示</summary>

**解答: B) 長時間維持される接続を多数の RPC が共有でき、L4 バランシングは接続ごとにバックエンドを選択するから**

**解説:**
gRPC channel は HTTP/2 接続を 0 個以上使います。少数の長時間接続が多数の RPC を運ぶことがあり、L4 ロードバランサーは個々の RPC を再分散しません。適切なクライアント側ポリシーまたは gRPC を認識する L7 proxy によって、リクエスト分散を改善できる場合があります。確立した stream は同じバックエンドにとどまります。

</details>

5. WebSocket サービスの運用に関する問題と対処方法の組み合わせで、**誤っている**ものはどれですか？
    - A) ロードバランサーのアイドルタイムアウトによる切断 → ping/pong frame で keep alive する
    - B) デプロイ中の再接続集中 → jitter を加えた指数バックオフを使う
    - C) インスタンス間でアプリケーションイベントを配信する → Redis Pub/Sub などのメッセージングを使い、各 socket はローカルで保持する
    - D) Proxy が Upgrade header をブロックする → QoS 2 に上げる

<details>
<summary>解答を表示</summary>

**解答: D) Proxy が Upgrade header をブロックする → QoS 2 に上げる**

**解説:**
QoS レベルは MQTT のものであり、WebSocket ハンドシェイクを修正するものではありません。HTTP/1.1 は Upgrade を使い、HTTP/2 と HTTP/3 は対応している場合に Extended CONNECT を使います。heartbeat はアイドルタイムアウトの動作に合わせてください。バックオフと接続の drain により、再接続の急増を抑えられます。Pub/Sub はアプリケーションイベントを配信できますが、socket を移動したり、それだけでメッセージ配信を永続化したりするものではありません。

</details>

6. メールドメイン認証の 3 つの仕組み（SPF、DKIM、DMARC）とその役割を正しく対応付けているのはどれですか？
    - A) SPF: メッセージ署名 / DKIM: 許可する送信元 IP の公開 / DMARC: 暗号化の強制
    - B) SPF: envelope/HELO ID の送信元ホストを認可 / DKIM: ドメイン鍵で対象コンテンツに署名 / DMARC: 表示される From ドメインを SPF または DKIM の合格結果に整合させ、ポリシーを公開
    - C) SPF: 受信サーバーの認証 / DKIM: トランスポート暗号化 / DMARC: スパムフィルタリング
    - D) SPF: メールキュー管理 / DKIM: MX レコード検証 / DMARC: TLS の強制

<details>
<summary>解答を表示</summary>

**解答: B) SPF: envelope/HELO ID の送信元ホストを認可 / DKIM: ドメイン鍵で対象コンテンツに署名 / DMARC: 表示される From ドメインを SPF または DKIM の合格結果に整合させ、ポリシーを公開**

**解説:**
SPF は envelope/HELO ドメインを検査し、DKIM は署名ドメインに基づいて対象コンテンツを検証します。DMARC は、表示される From ドメインに整合する仕組みが少なくとも 1 つ合格することを要求します。両方の合格は必須ではありません。これらの仕組みはドメイン保護に役立ちますが、メール配信を保証したり、表示名や類似ドメインを使ったなりすましを防いだりするものではありません。

</details>

7. HTTP/1.1 リクエストが `POST /echo HTTP/1.1` で始まり、応答が `HTTP/1.1 200 OK` で始まります。正しい解釈はどれですか？
    - A) `POST` は header field で、`/echo` は応答の status である
    - B) `200` は本文の長さで、`OK` によってリクエストの成功が決まる
    - C) リクエスト行には method、target、version が含まれ、status line には version、status code、任意の reason phrase が含まれる
    - D) 最初の空行で本文も含めたメッセージ全体が終わる

<details>
<summary>解答を表示</summary>

**解答: C) リクエスト行には method、target、version が含まれ、status line には version、status code、任意の reason phrase が含まれる**

**解説:**
POST は target に対して送信したコンテンツを処理するよう要求し、200 は成功 status です。start line の後に header field の行が続き、空行で header section が終わります。メッセージ本文が続くのは、メッセージの規則が許す場合だけです。説明用の表示で LF を使っていても、HTTP/1.1 の wire 上の行末には CRLF が使われます。

</details>

8. HTTP/1.1 メッセージ本文の内容が、末尾改行、content coding、transfer coding のない ASCII 5 バイトの `hello` だけだとします。`Content-Length: 5` が数えるのは何ですか？
    - A) start line と header を含むメッセージ全体
    - B) 本文の 5 バイトだけ。`Content-Type` は別にその media type を示す
    - C) バイトエンコーディングに関係なく、Unicode 文字 5 つ
    - D) 本文を送信する TCP パケットの数

<details>
<summary>解答を表示</summary>

**解答: B) 本文の 5 バイトだけ。`Content-Type` は別にその media type を示す**

**解説:**
Content-Length が数えるのはバイト数であり、start line、header、区切りの空行は含みません。ASCII の `hello` は 5 バイトです。実際に LF を追加すると 6 バイトになります。ASCII 以外の UTF-8 文字は複数バイトになる場合があります。Content-Type は表現をどう解釈するかを受信側に伝えるもので、メッセージの終端位置は示しません。

</details>

9. 有効な HTTP/1.1 `200` 応答に `Transfer-Encoding: chunked` が設定され、TCP 接続が維持されています。本文はどのように区切られますか？
    - A) TCP パケットの境界で区切られる
    - B) Content-Type だけで区切られる
    - C) Transfer-Encoding と併せて送信する必須の Content-Length で区切られる
    - D) chunk framing に従って区切られ、サイズ 0 の chunk、任意の trailer、最後の空行で終わる

<details>
<summary>解答を表示</summary>

**解答: D) chunk framing に従って区切られ、サイズ 0 の chunk、任意の trailer、最後の空行で終わる**

**解説:**
chunk framing によって、接続を閉じずに本文の終わりを特定できます。送信側は Transfer-Encoding と一緒に Content-Length を送信してはいけません。TCP はバイトストリームです。1 つのメッセージが複数のパケットに分かれることも、1 つのパケットに複数メッセージのバイトが含まれることもあります。

</details>

10. GET に対する有効な HTTP/1.1 `200` 応答を HEAD にも返し、`Content-Length: 500` を含めます。header section の後に、クライアントは本文 500 バイトを読み取るべきですか？
    - A) いいえ。HEAD の応答にはメッセージ本文がなく、このフィールドは対応する GET 応答の長さを示す
    - B) はい。Content-Length は常に method より優先される
    - C) Content-Type が text/plain の場合に限り、はい
    - D) いいえ。すべての HEAD 応答で Content-Length が禁止されている

<details>
<summary>解答を表示</summary>

**解答: A) いいえ。HEAD の応答にはメッセージ本文がなく、このフィールドは対応する GET 応答の長さを示す**

**解説:**
一般的な長さの framing より、method／status の規則が優先されます。HEAD の応答に本文はなく、許可される長さフィールドはメタデータです。1xx、204、304 status の応答にも本文はなく、各フィールドに別々の制限が適用されます。

</details>

11. HTTP/2 でネゴシエートされた HTTPS リクエストについて、クライアントツールには読める header が表示されています。セッション秘密情報のない受動キャプチャでは何が見えるはずですか？
    - A) 同じ平文の `GET ... HTTP/1.1` リクエスト行
    - B) 本文だけが暗号化され、header は平文で見える
    - C) 保護されたアプリケーションデータ。HTTP/2 は binary frame を使い、ツールは復号したフィールドを表示している
    - D) すべての HTTP/2 stream を区切る HTTP/1.1 の chunk サイズ

<details>
<summary>解答を表示</summary>

**解答: C) 保護されたアプリケーションデータ。HTTP/2 は binary frame を使い、ツールは復号したフィールドを表示している**

**解説:**
HTTPS 接続では、TLS が HTTP/2 の header とコンテンツを保護します。HTTP/2 は TCP 上で HEADERS/DATA frame を使い、HTTP/3 は保護された QUIC stream 上で独自の frame を使います。どちらも HTTP の意味的な動作は維持しますが、HTTP/1.1 のテキスト形式の start line や chunked transfer coding は使いません。認可された endpoint または終端点で復号済みメッセージを観測してください。

</details>

---

[学習資料に戻る](../../basics/06-network-fundamentals-part3.md) | [次のクイズ: パート 4](./06-network-fundamentals-part4-quiz.md)

[HTTP メッセージの構造、framing、可視性](../../basics/06-network-fundamentals-part3.md#http11-message-structure)（主な参考資料を含む）を復習してください。

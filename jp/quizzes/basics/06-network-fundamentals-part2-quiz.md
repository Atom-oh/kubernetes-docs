# ネットワーク基礎 第2部クイズ: Transport と TLS

> **最終更新日**: September 11, 2026

TCP、UDP、QUIC、TLS の理解度を確認します。

## 選択式問題

1. QUIC は TCP における stream 間の Head-of-Line (HOL) delivery 依存を、どのように回避しますか？
   - A) packet loss のたびに接続全体を再確立する
   - B) 1つの接続内で、各 stream ごとに独立した byte 順序を維持する
   - C) 順序保証を完全に放棄する
   - D) kernel レベルで再送を処理する

<details>
<summary>回答を表示</summary>

**回答: B) 1つの接続内で、各 stream ごとに独立した byte 順序を維持する**

**解説:**
TCP では、欠落した segment より後の byte を配信できず、複数の HTTP/2 stream が遅延することがあります。QUIC では、別の stream の利用可能なデータを独立して配信できます。ただし、stream 自体は欠落した byte を待つことがあります。また、接続/経路の輻輳制御、packet recovery、アプリケーションの依存関係は共有されます。

</details>

2. TLS 1.3 について、正しくない説明はどれですか？
   - A) 通常の full handshake は約1 RTT で完了し、条件を満たす再開では任意の 0-RTT early data を送信できる
   - B) RSA key exchange と弱い cipher suite は削除された
   - C) TLS 1.3 だけで、ECH を使わずに SNI が暗号化される
   - D) Ephemeral (EC)DHE は forward secrecy を提供するが、PSK のみの交換と 0-RTT data には例外がある

<details>
<summary>回答を表示</summary>

**回答: C) TLS 1.3 だけで、ECH を使わずに SNI が暗号化される**

**解説:**
TLS 1.3 だけでは ClientHello の SNI は隠されません。ECH (RFC 9849) は、サポートされ設定されている場合に inner ClientHello を保護します。TLS 1.3 では PSK のみの key exchange も可能で、0-RTT data には forward secrecy がないため、forward secrecy が無条件で得られるとする説明は誤りです。また、early data を使っても handshake がすでに完了したことにはなりません。

</details>

3. BBR の輻輳制御のアプローチの特徴は何ですか？
   - A) packet loss を無視して、常に最大速度で送信する
   - B) ボトルネック帯域幅と伝搬 RTT をモデル化して送信を制御し、loss/ECN の動作はバージョンによって異なる
   - C) kernel ではなく user space で実行される
   - D) 再送を link layer に委ねる

<details>
<summary>回答を表示</summary>

**回答: B) ボトルネック帯域幅と伝搬 RTT をモデル化して送信を制御し、loss/ECN の動作はバージョンによって異なる**

**解説:**
BBR は、loss を基準にした輻輳 window だけに頼らず、帯域幅/RTT のモデルを使います。それでも loss recovery とバージョン固有の輻輳応答が必要です。性能は実装、競合するトラフィック、経路の状態に左右されるため、throughput の向上は保証されません。

</details>

4. TLS 1.3/QUIC の 0-RTT session resumption で request を送る際、どのルールに従う必要がありますか？
   - A) POST request だけを送る
   - B) 0-RTT data は replay される可能性があるため、アプリケーションが replay-safe と明示的に評価した操作だけを許可する
   - C) 0-RTT では certificate validation が省略されるため、内部ネットワークだけで使う
   - D) 0-RTT は UDP 上でしか動作しないため、TCP fallback をブロックする

<details>
<summary>回答を表示</summary>

**回答: B) 0-RTT data は replay される可能性があるため、アプリケーションが replay-safe と明示的に評価した操作だけを許可する**

**解説:**
Early-data のやり取りは replay され、アプリケーションによる処理が繰り返される場合があります。GET という method 名や idempotent であるという主張だけでは、replay safety の証明になりません。client/CDN/origin 全体で、承認済みの操作に early data を制限してください。HTTP server は 425 Too Early を返し、handshake 後に request を再試行させることができます。

</details>

---

[学習資料に戻る](../../basics/06-network-fundamentals-part2.md) | [次のクイズ: 第3部](./06-network-fundamentals-part3-quiz.md)

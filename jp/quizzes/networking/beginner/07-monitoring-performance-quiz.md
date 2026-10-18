# 監視とパフォーマンスのクイズ

[レッスン](../../../networking/beginner/07-monitoring-performance.md)

6つの質問に答え、それぞれの回答を自分の言葉で説明してください。

1. LISTEN socket に Recv-Q 3、Send-Q 128 と表示されています。これは何を意味しますか？

   - A) 受信した body byte が3個、送信した body byte が128個
   - B) accept を待つ接続が3個あり、accept backlog の最大値は128
   - C) 再送が3回、RTT が128ms
   - D) 接続が現在128個ある

<details>
<summary>回答を表示</summary>

**回答: B) accept を待つ接続が3個あり、accept backlog の最大値は128**

**解説:** LISTEN queue が数えるのは接続です。ESTABLISHED socket の stream byte とは単位が異なるため、最初に state を確認します。

</details>

2. IP address を使った curl request で time_namelookup が非常に小さい場合、何が結論できますか？

   - A) 組織の DNS は常に高速である
   - B) すべての DNS cache が空である
   - C) DNS performance の検証には適さない request である
   - D) Server の処理時間がゼロである

<details>
<summary>回答を表示</summary>

**回答: C) DNS performance の検証には適さない request である**

**解説:** IP literal では service name の lookup をテストできません。また、累積 timing field を独立した時間区間として足し合わせないでください。

</details>

3. curl は成功したのに tcpdump で何も取得できませんでした。最初に何を確認しますか？

   - A) 選択した NIC、filter、capture の時間範囲
   - B) すべての host routing table をリセットする
   - C) SSH password login を有効にする
   - D) TCP buffer の最大値を増やす

<details>
<summary>回答を表示</summary>

**回答: A) 選択した NIC、filter、capture の時間範囲**

**解説:** Capture の結果は、観測場所と条件に依存します。request と capture の時刻を合わせ、ラボで選択した NIC を確認してください。

</details>

4. 100 Mbit/s と 100 MB/s はどのように比較できますか？

   - A) 常に同じ
   - B) Mbit/s の値の方が8倍大きい
   - C) HTTP の場合だけ同じ
   - D) 100 MB/s は800 Mbit/s に相当する速度である

<details>
<summary>回答を表示</summary>

**回答: D) 100 MB/s は800 Mbit/s に相当する速度である**

**解説:** 1 byte は8 bit です。実際のアプリケーション throughput を比較する際は、protocol overhead、観測地点、実行条件も考慮します。

</details>

5. 1回の Send-Q snapshot が0より大きい場合、適切な次の手順はどれですか？

   - A) Network loss があったと断定する
   - B) すべての buffer sysctl を2倍にする
   - C) State、時間による変化、アプリケーションの進行状況、packet を関連付けて確認する
   - D) リモート firewall を無効にする

<details>
<summary>回答を表示</summary>

**回答: C) State、時間による変化、アプリケーションの進行状況、packet を関連付けて確認する**

**解説:** Send-Q には、未確認の byte と未送信の byte の両方が含まれる場合があります。1回の snapshot だけでは原因を特定できません。

</details>

6. Block I/O scheduler と network qdisc の違いを正しく説明しているのはどれですか？

   - A) それぞれ storage request と network transmit queue を処理する
   - B) どちらも DNS cache である
   - C) どちらも SSH key を検証する
   - D) どちらも同じ1つの sysctl を使う

<details>
<summary>回答を表示</summary>

**回答: A) それぞれ storage request と network transmit queue を処理する**

**解説:** まず bottleneck を特定してください。どちらも scheduling の概念を使いますが、同じリソースを制御するわけではなく、tuning の効果も同じではありません。

</details>

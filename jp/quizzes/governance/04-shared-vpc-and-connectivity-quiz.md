# Shared VPC と接続性のクイズ

> このクイズでは、[Shared VPC と接続性](../../governance/04-shared-vpc-and-connectivity.md)の理解度を確認します。

---

1. TGW の伝播は VPC route table とどのように関係しますか？
   - A) TGW prefix 100個が Shared VPC の固定上限である
   - B) TGW route は自動的に伝播されないため、所有者が TGW をターゲットとする VPC static route を追加する
   - C) すべてのテーブルで1つのクォータを共有する
   - D) CIDR のクォータが先に上限に達することはない

<details>
<summary>回答を表示</summary>

**回答: B) TGW route は自動的に伝播されないため、所有者が TGW をターゲットとする VPC static route を追加する**

**解説:**
TGW table の合計デフォルト上限は10,000 route、VPC の非伝播 route のデフォルト上限は500です。VGW の伝播 route 上限100と、TGW の合計数を混同しないでください。

</details>

---

2. Shared VPC の参加者が内容を参照できない、所有者側のリソースはどれですか？
   - A) Subnet
   - B) 自分が所有する security group
   - C) NAT Gateway
   - D) Route table

<details>
<summary>回答を表示</summary>

**回答: C) NAT Gateway**

**解説:**
参加者は所有者の NAT gateway の内容を参照できません。中央のインベントリ、ログ、委任された読み取り経路から、監査証跡を確認することはできます。

</details>

---

3. Shared VPC における LBC の subnet 検出は、どのように設計すべきですか？
   - A) すべてのバージョンで成功すると想定する
   - B) controller mode、権限、タグの可視性を検証し、明示的な subnet ID の指定も検討する
   - C) 常に所有者に Ingress を作成してもらう
   - D) NAT gateway だけを通じて検出する

<details>
<summary>回答を表示</summary>

**回答: B) controller mode、権限、タグの可視性を検証し、明示的な subnet ID の指定も検討する**

**解説:**
所有者のタグが自動的に共有されることはありません。subnet を明示的に指定すると予測しやすくなりますが、これはすべての検出モードが失敗することを示すものではありません。

</details>

---

4. 長時間存続する VPC Lattice 接続について正しい説明はどれですか？
   - A) Service と resource の両方の存続期間は10分である
   - B) Service の存続期間10分と resource の idle timeout 350秒を区別し、プロトコルと再接続の動作をテストする
   - C) HTTP listener はすべての WebSocket をネイティブにサポートする
   - D) 長時間のトラフィックを処理できる経路はない

<details>
<summary>回答を表示</summary>

**回答: B) Service の存続期間10分と resource の idle timeout 350秒を区別し、プロトコルと再接続の動作をテストする**

**解説:**
Resource に同じ存続期間の上限はありません。TLS listener または resource 経由のパスで WebSocket を処理できますが、プロトコルと認可の要件に従う必要があります。

</details>

---

5. Route 53 Profiles の DNS 優先順位ルールを正しく説明しているのはどれですか？
   - A) 常にローカル VPC のルールが Profile より優先される
   - B) 常に Profile のルールがローカル VPC より優先される
   - C) 名前が一致すればローカル VPC が優先されるが、Profile により具体的な名前が登録されている場合は Profile が優先される
   - D) 優先順位はランダムに決まる

<details>
<summary>回答を表示</summary>

**回答: C) 名前が一致すればローカル VPC が優先されるが、Profile により具体的な名前が登録されている場合は Profile が優先される**

**解説:**
たとえばローカル VPC に `example.com` のルールがあり、Profile により具体的な `test.example.com` のルールがある場合、Profile が適用されます。そのため、「中央 Profile は、ワークロードに委任された namespace より具体的な名前を所有しない」というルールを正式に定めることが推奨されます。

</details>

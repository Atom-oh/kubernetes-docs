# 意思決定フレームワークと PoC 設計クイズ

> このクイズでは、[意思決定フレームワークと PoC 設計](../../governance/06-decision-framework-and-poc.md)の理解度を確認します。

---

1. このドキュメントが、意思決定要因における「最大のギャップ」として挙げているのは何ですか？
   - A) Tag の命名規則
   - B) CUJ ごとの RTO/RPO 目標
   - C) EKS のバージョン番号
   - D) VPC CIDR のサイズ

<details>
<summary>回答を表示</summary>

**回答: B) CUJ ごとの RTO/RPO 目標**

**解説:**
CUJ ごとの RTO/RPO 目標が定義されていないと、A/B EKS Runtime の failover が十分に速いか、どのデータ所有モデルなら実際に復旧できるか、AZ 設定の違いが重要かを判断できません。この目標を最初に定義する必要があります。

</details>

---

2. ALB の weighted forwarding と fail-open はどのような関係ですか？
   - A) health check に失敗した group は常に別の group に failover する
   - B) group 間の自動 failover と、group 内での異常なターゲットへの routing は別の動作である
   - C) Weight によって RTO が保証される
   - D) ターゲットは Region 間で複製される

<details>
<summary>回答を表示</summary>

**回答: B) group 間の自動 failover と、group 内での異常なターゲットへの routing は別の動作である**

**解説:**
Weighted forwarding は、空または異常な group の weight を別の group に自動的に移しません。選択した group の DNS/routing の health threshold は別途評価してください。

</details>

---

3. なぜ「decision matrix dry-run」を他のすべての PoC より前に PoC-0 として実行するのですか？
   - A) 最も安価な選択肢だから
   - B) 独立した境界の判断や Hybrid 構成など、他のすべての選択肢では「decision matrix で再現できること」が妥当性の条件となるため、これを実施しないと PoC の結果を標準にできないから
   - C) AWS SA の承認が必要だから
   - D) 他の PoC と関係がないから

<details>
<summary>回答を表示</summary>

**回答: B) 独立した境界の判断や Hybrid 構成など、他のすべての選択肢では「decision matrix で再現できること」が妥当性の条件となるため、これを実施しないと PoC の結果を標準にできないから**

**解説:**
Decision matrix dry-run では、2人が代表的なワークロード10～15件に matrix を個別に適用します。ローカルの例示目標として、不一致率20%未満、例外率15%未満を使用します。そこで推定した Account/VPC/cluster の数を、残りの PoC の測定目標にします。

</details>

---

4. 未使用 Region の制御について、正しい説明はどれですか？
   - A) デフォルトで有効なすべての Region を無効にできる
   - B) SCP、検出、サポート対象 Region の opt-in 無効化、既存リソースのコスト確認を組み合わせる
   - C) GuardDuty だけですべての API をブロックできる
   - D) Region を無効にすると、すべてのリソースが削除される

<details>
<summary>回答を表示</summary>

**回答: B) SCP、検出、サポート対象 Region の opt-in 無効化、既存リソースのコスト確認を組み合わせる**

**解説:**
デフォルトで有効な Region は無効にできません。opt-in Region を無効にしても既存リソースは削除されず、料金が停止する保証もありません。そのため、クリーンアップとアクセス制御を合わせて計画してください。

</details>

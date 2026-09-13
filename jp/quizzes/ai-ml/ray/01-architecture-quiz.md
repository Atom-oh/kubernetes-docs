# Ray アーキテクチャクイズ

## 選択問題

1. リモート関数を送信するにはどうしますか？
   - A) 通常どおり f(...) を呼び出す
   - B) @ray.remote 関数で f.remote(...) を使用する
   - C) ray.get(f) だけを呼び出す
   - D) 呼び出しごとに Pod を作成する

<details>
<summary>回答を表示</summary>

**回答: B**

単一戻り値の例では ObjectRef が生成され、ray.get がその値を読み取ります。
</details>

2. すべての Ray タスクは独立しており、副作用がありませんか？
   - A) はい。Ray は依存関係を追跡しない
   - B) いいえ。ObjectRef の依存関係、副作用、リトライを考慮する
   - C) ObjectRef を返すのは actor だけである
   - D) すべての関数は必ず一度だけ実行される

<details>
<summary>回答を表示</summary>

**回答: B**

ステートレスな実行ユニットであっても、純粋性や厳密に一度だけの実行を保証するものではありません。
</details>

3. actor の状態に関する正確な記述はどれですか？
   - A) インスタンスメモリは呼び出し間で維持され、障害復旧は別途必要である
   - B) すべての状態は自動的に永続化される
   - C) actor は head 上でのみ実行される
   - D) 再起動を有効にすると以前のメモリが復元される

<details>
<summary>回答を表示</summary>

**回答: A**

max_restarts はコンストラクタを再実行しますが、checkpoint による復旧の代わりにはなりません。
</details>

4. 検証されたゼロコピーの範囲はどれですか？
   - A) すべての Python オブジェクトと GPU メモリ
   - B) すべての node で共有される 1 つの物理 RAM
   - C) 同じ node 上の読み取り専用 NumPy 共有メモリビュー
   - D) すべての場合でネットワーク転送コストがゼロ

<details>
<summary>回答を表示</summary>

**回答: C**

変更にはコピーが必要です。他のオブジェクト、GPU、または node 間転送に一般化しないでください。
</details>

5. GCS の名称と役割は何ですか？
   - A) Global Control Service。actor、node、placement group などのクラスター metadata
   - B) すべての weight のための GPU Copy Store
   - C) Global Control Store。すべての ObjectRef metadata の唯一の所有者
   - D) Kubernetes API server の代替

<details>
<summary>回答を表示</summary>

**回答: A**

Object ownership metadata は、元の ObjectRef を作成した process に属し、普遍的に GCS に属するわけではありません。
</details>

6. それぞれ 1 つの空き CPU がある 2 つの node で、2 CPU を必要とする 1 つのタスクを実行できますか？
   - A) 合計が 2 なので、常に実行できる
   - B) Ray が自動的にタスクを半分に分割する
   - C) いいえ。タスクは実行可能な 1 つの node に収まる必要がある
   - D) メモリが利用可能であれば CPU 要件は重要ではない

<details>
<summary>回答を表示</summary>

**回答: C**

クラスター全体での選択も、node レベルのリソース実行可能性に依存します。
</details>

7. num_cpus=1 は何を意味しますか？
   - A) OS がすべての thread を 1 つの core に固定する
   - B) OS の制限とは別の、論理的な Ray のスケジューリング／受け入れ要件
   - C) 専有の物理 core が保証される
   - D) GPU メモリ制限が自動的に設定される

<details>
<summary>回答を表示</summary>

**回答: B**

Container の制限と library の thread 設定は別のものです。
</details>

8. KubeRay は何をしますか？
   - A) アプリケーションに対して Train、Tune、Serve を自動的に選択する
   - B) Kubernetes 上で Ray CR と Pod lifecycle を調整する
   - C) kube-scheduler を置き換える
   - D) Ray タスクごとに新しい EC2 instance を作成する

<details>
<summary>回答を表示</summary>

**回答: B**

Ray の作業スケジューリング、Pod 配置、EC2 プロビジョニングは別のレイヤーです。
</details>

## 短答問題

9. リクエスト間で model を常駐させるために actor が適しているのはなぜですか？

<details>
<summary>回答を表示</summary>

明示的なリモート instance が状態を所有します。正しさのために、偶発的な task-worker のグローバル cache 再利用に依存しないでください。actor の障害には、引き続き checkpoint と復旧設計が必要です。
</details>

10. GCS 復旧を object および actor のアプリケーション復旧と分けるのはなぜですか？

<details>
<summary>回答を表示</summary>

永続的なクラスター metadata、object ownership／lineage／value の復旧、actor checkpoint はそれぞれ異なる問題を解決します。Redis または alpha RocksDB の設定だけでは、すべての value とアプリケーション状態を復元できません。
</details>

---

[学習教材に戻る](../../../ai-ml/ray/01-architecture.md)

# リソース最適化クイズ

> **関連ドキュメント**: [リソース最適化](../../ops/10-resource-optimization.md)

## 選択式問題

### 1. Kubernetes における resource requests と limits の違いは何ですか？

- A) Requests は CPU 専用で、limits は memory 専用である
- B) Requests はスケジューリングのために保証されるリソースで、limits は許可される最大値である
- C) Requests と limits は同じものである
- D) Limits は保証され、requests は任意である

<details>
<summary>回答を表示</summary>

**回答: B) Requests はスケジューリングのために保証されるリソースで、limits は許可される最大値である**

**解説:**
Requests は Kubernetes が container に保証するリソースであり、スケジューリングの判断に使用されます。Limits は container が使用できる最大リソースです。CPU limits を超えると throttling が発生し、memory limits を超えると OOM kill が発生する可能性があります。

</details>

### 2. node のリソース逼迫時に最も高い優先度を得る QoS class はどれですか？

- A) BestEffort
- B) Burstable
- C) Guaranteed
- D) すべての class の優先度は同じである

<details>
<summary>回答を表示</summary>

**回答: C) Guaranteed**

**解説:**
Guaranteed pods（CPU と memory の両方で requests=limits）は最も高い優先度を持ち、リソース逼迫時に最後に evict されます。BestEffort pods（requests/limits なし）が最初に evict され、その次に Burstable pods が続きます。

</details>

### 3. Kubernetes containers で CPU throttling が発生する原因は何ですか？

- A) memory が不足している
- B) container が CFS period 中に CPU limit を超えている
- C) ネットワーク輻輳
- D) ディスク I/O ボトルネック

<details>
<summary>回答を表示</summary>

**回答: B) container が CFS period 中に CPU limit を超えている**

**解説:**
Linux CFS (Completely Fair Scheduler) は 100ms の period ごとに CPU limits を強制します。container が period の早い段階で quota を使い切ると、次の period が始まるまで throttled（一時停止）されます。これは `cpu.cfs_throttled_us` で追跡されます。

</details>

### 4. containers に推奨される JVM MaxRAMPercentage 設定は何ですか？

- A) 100%
- B) 90%
- C) 75%
- D) 50%

<details>
<summary>回答を表示</summary>

**回答: C) 75%**

**解説:**
MaxRAMPercentage を 75% に設定すると、container memory の 25% を non-heap 用途（metaspace、thread stacks、native memory、OS overhead）に残せます。より高い値を使用すると、non-heap memory が予期せず増えた場合に OOM kill のリスクがあります。

</details>

### 5. VPA で "Initial" update mode は何をしますか？

- A) pods を継続的に更新する
- B) pods が最初に作成されるときにのみ resources を設定する
- C) 既存の pods をすべて削除する
- D) VPA を完全に無効化する

<details>
<summary>回答を表示</summary>

**回答: B) pods が最初に作成されるときにのみ resources を設定する**

**解説:**
"Initial" mode は VPA の推奨値を pod 作成時にのみ適用し、実行中の pods には適用しません。これは HPA と併用する場合に有用です。VPA が初期サイズを設定し、HPA が scaling を処理し、既存の pods は中断されないためです。

</details>

### 6. container CPU limits に基づいて設定すべき Go runtime 設定は何ですか？

- A) GOGC
- B) GOMAXPROCS
- C) GOPATH
- D) GOROOT

<details>
<summary>回答を表示</summary>

**回答: B) GOMAXPROCS**

**解説:**
GOMAXPROCS は Go code を実行する OS threads の数を制御します。デフォルトでは、Go は container limits ではなく host CPUs をすべて使用します。GOMAXPROCS を container CPU limits に合わせて設定する（automaxprocs library を使用する）ことで、過剰な context switching を防げます。

</details>

### 7. Go applications で GOMEMLIMIT は何に使用されますか？

- A) 最小 memory allocation を設定する
- B) garbage collector に soft memory limit のヒントを提供する
- C) goroutines の数を制限する
- D) swap memory を設定する

<details>
<summary>回答を表示</summary>

**回答: B) garbage collector に soft memory limit のヒントを提供する**

**解説:**
GOMEMLIMIT は Go garbage collector に目標 memory ceiling を伝えます。memory がこの limit に近づくと GC が早めに実行され、利用可能な memory を効率的に活用しながら OOM kill のリスクを低減します。

</details>

### 8. containers 内の Python Gunicorn workers について、推奨される worker 数の計算式は何ですか？

- A) 2 * CPU_CORES + 1
- B) host cores ではなく、container CPU limit に基づく
- C) 常に 1 worker を使用する
- D) 最大 throughput のために 100 workers を使用する

<details>
<summary>回答を表示</summary>

**回答: B) host cores ではなく、container CPU limit に基づく**

**解説:**
古典的な計算式 (2*cores+1) は host CPU count を使用するため、containers では過剰割り当てになります。worker 数は resource contention と OOM issues を避けるため、container CPU limits（例: CPU limit あたり 2〜4 workers）に基づく必要があります。

</details>

### 9. memory limit を超えた container には何が起きますか？

- A) CPU throttled される
- B) kernel によって OOM killed される
- C) 自動的に水平 scaling される
- D) memory が他の containers から借用される

<details>
<summary>回答を表示</summary>

**回答: B) kernel によって OOM killed される**

**解説:**
CPU（throttled される）とは異なり、memory limits は厳格に強制されます。container が memory limit を超えると、Linux OOM killer が container 内の processes を終了します。その後 Kubernetes は restart policy に基づいて container を再起動します。

</details>

### 10. VPA Recommender component の目的は何ですか？

- A) 新しい resources で pods を再起動する
- B) resource usage を分析して resource recommendations を生成する
- C) node scaling を管理する
- D) resource configurations を検証する

<details>
<summary>回答を表示</summary>

**回答: B) resource usage を分析して resource recommendations を生成する**

**解説:**
VPA Recommender は時間の経過に伴う containers の実際の resource usage を監視し、requests と limits の推奨値を生成します。CPU と memory の usage patterns、peaks、variance を考慮して、適切な値を提案します。

</details>

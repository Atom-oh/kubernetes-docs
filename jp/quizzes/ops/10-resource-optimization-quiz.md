# リソース最適化クイズ

> **関連ドキュメント**: [Resource optimization](../../ops/10-resource-optimization.md)

## 1. memory pressure 下の eviction を正しく説明しているのはどれですか？

- A) eviction の順序は QoS class だけで決まる
- B) request を超える使用量、Pod Priority、相対的な使用量が関係する
- C) Guaranteed Pod は決して eviction されない
- D) PDB は node pressure による eviction をすべて防ぐ

<details>
<summary>回答を表示</summary>

**回答: B**

QoS は判断材料になりますが、eviction の順序を絶対的に決めるものではありません。container limit 超過による OOM、memory pressure による eviction、DiskPressure を区別してください。

</details>

## 2. CPU throttled-period ratio は何を測定しますか？

- A) 失われた CPU 時間の正確な割合
- B) throttling が発生した quota period の割合
- C) CPU request の使用率
- D) 平均 memory 使用率

<details>
<summary>回答を表示</summary>

**回答: B**

複数の thread は quota を共有します。period の割合だけでは、失われた CPU 時間は分からず、limit を引き上げるのが適切な対処だとも判断できません。

</details>

## 3. JVM heap と container memory について、正しい説明はどれですか？

- A) 75% が常に最適である
- B) 比率を決める際は non-heap memory と RSS を測定する
- C) `MaxRAMPercentage` は実行中の Pod limit の変更に常に即時追従する
- D) kernel の SIGKILL が発生すると必ず heap dump が生成される

<details>
<summary>回答を表示</summary>

**回答: B**

Metaspace、thread stack、direct buffer、JNI にも memory が必要です。JVM ergonomics と cgroup limit、Java の OOME と SIGKILL を区別してください。

</details>

## 4. `JAVA_OPTS` を設定しても JVM option が適用されないことがあるのはなぜですか？

- A) JVM が security option として拒否する
- B) entrypoint が渡さない限り、JVM は自動的に読み込まない
- C) Kubernetes は環境変数をサポートしない
- D) Java 21 は container 内で動作しない

<details>
<summary>回答を表示</summary>

**回答: B**

`JAVA_TOOL_OPTIONS` を使うか、`java` に引数を明示的に渡し、実際の `VM.flags` 出力を確認してください。

</details>

## 5. VPA の `upperBound` について、正しい説明はどれですか？

- A) 常に container memory limit にコピーする
- B) request の推奨範囲の一部であり、container limit ではない
- C) HPA の最大 replica 数である
- D) OOM が発生しないことを保証する memory 量である

<details>
<summary>回答を表示</summary>

**回答: B**

`target`、`lowerBound`、`upperBound`、`uncappedTarget` を区別してください。Initial mode でも、新しい request が HPA の分母に影響することがあります。

</details>

## 6. Go 1.25 以降の `GOMAXPROCS` の既定値について、正しい説明はどれですか？

- A) 常に host CPU 数を使い、外部 library が必須である
- B) language version と互換性の既定動作に応じて、quota と CPU affinity を考慮する。明示的に設定すると自動更新は無効になる
- C) CPU request だけを使用する
- D) どの環境でも `500m` は常に 1 として扱われる

<details>
<summary>回答を表示</summary>

**回答: B**

この例は Go 1.27.2 と `go.mod` 1.25 以降でテストされています。quota の丸めと最小値の条件も考慮してください。

</details>

## 7. `GOMEMLIMIT` と Node の old-space limit に共通する制約は何ですか？

- A) process の RSS 全体を完全には制限しない
- B) native memory をすべて強制的に解放する
- C) container の OOM を防ぐことを保証する
- D) Pod request を自動的に変更する

<details>
<summary>回答を表示</summary>

**回答: A**

Go の値は runtime が管理する soft limit です。Node の option は V8 の old space を制御します。native allocation と複数 worker の memory は別途考慮してください。

</details>

## 8. Gunicorn と Tokio の worker 数をどう決めるべきですか？

- A) host CPU 数の固定倍率で十分である
- B) 実際の設定を確認し、quota、memory、workload の動作をテストする
- C) Rust には GC がないため、concurrency limit は不要である
- D) thread／process 数は memory に影響しない

<details>
<summary>回答を表示</summary>

**回答: B**

設定が実際に `WEB_CONCURRENCY` を読み取ることを確認してください。`worker_threads` を明示した Tokio の設定は環境変数を上書きします。blocking pool は別に扱います。

</details>

## 9. OOM reason と Pending phase の metric はどう解釈すべきですか？

- A) reason gauge に increase を適用すれば、正確な OOM 件数が得られる
- B) Pending の series をすべて数えれば、現在の Pending 数が得られる
- C) 0／1 の値と、reason gauge が最後の状態しか表さない制約を考慮する
- D) Pending は常に CPU 不足を意味する

<details>
<summary>回答を表示</summary>

**回答: C**

Pending で値が 0 の series も存在します。最近の restart と最後の OOM reason を組み合わせても、期間内の OOM をすべて再構成することはできません。

</details>

## 10. Auto Mode の bin-packing と placeholder Pod について、正しい説明はどれですか？

- A) 4 vCPU の instance には、アプリケーションの CPU request を常に合計 4 CPU 分配置できる
- B) placeholder は EC2 Capacity Reservation である
- C) allocatable、overhead、scheduler の制約を考慮する。placeholder は容量を保証しない
- D) `preemptionPolicy: Never` を設定すると、その Pod が preempt されなくなる

<details>
<summary>回答を表示</summary>

**回答: C**

`Never` はこの Pod がほかの Pod を preempt するのを防ぎます。NodePool は `karpenter.sh/v1` を使い、Auto Mode の NodeClass group は `eks.amazonaws.com` です。

</details>

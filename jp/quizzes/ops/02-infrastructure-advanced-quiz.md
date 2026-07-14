# インフラストラクチャ上級クイズ

> **関連ドキュメント**: [インフラストラクチャ上級](../../ops/02-infrastructure-advanced.md)

## 多肢選択問題

### 1. blue/green deployment における NLB weighted target groups の主な目的は何ですか？

- A) より少ない load balancer を使用してコストを削減するため
- B) cluster バージョン間の traffic distribution を制御するため
- C) SSL termination の性能を向上させるため
- D) health check の必要性をなくすため

<details>
<summary>答えを表示</summary>

**答え: B) cluster バージョン間の traffic distribution を制御するため**

**解説:**
NLB weighted target groups により、blue（現在）cluster と green（新規）cluster の間で traffic を段階的に移行できます。重み（例: 90:10、50:50、0:100）を調整することで、operator は制御された rollout を実行し、問題が検出された場合にすばやく rollback できます。

</details>

### 2. single-zone EKS cluster 戦略では、data nodes を 1 つの Availability Zone のみにデプロイすることがあるのはなぜですか？

- A) Cross-AZ data transfer costs を削減するため
- B) DNS 設定を簡素化するため
- C) 複数の subnet の使用を避けるため
- D) persistent volume の必要性をなくすため

<details>
<summary>答えを表示</summary>

**答え: A) Cross-AZ data transfer costs を削減するため**

**解説:**
AWS では Cross-AZ data transfer にコストが発生します。local storage を持つ data-intensive workload（database など）では、すべての replica を単一の AZ に保持することでこれらのコストをなくしつつ、durability には application-level replication に依存します。

</details>

### 3. Pod が異なる zone または node に分散されることを保証する Kubernetes 機能は何ですか？

- A) PodAffinity
- B) TopologySpreadConstraints
- C) ResourceQuota
- D) LimitRange

<details>
<summary>答えを表示</summary>

**答え: B) TopologySpreadConstraints**

**解説:**
TopologySpreadConstraints は、Pod が topology domain（zone、node、region）全体にどのように分散されるかを制御します。高可用性のために均等な分散を保証し、`maxSkew`、`topologyKey`、`whenUnsatisfiable` パラメータで設定できます。

</details>

### 4. Route53 weighted routing は NLB weighted target groups とどのように異なりますか？

- A) Route53 は DNS level で動作し、NLB は connection level で動作する
- B) Route53 は等しい重みのみをサポートする
- C) NLB は health check をサポートしない
- D) Route53 には VPC peering が必要である

<details>
<summary>答えを表示</summary>

**答え: A) Route53 は DNS level で動作し、NLB は connection level で動作する**

**解説:**
Route53 weighted routing は DNS 解決時に traffic を分散します。一方、NLB weighted target groups は connection level で分散します。DNS-based routing には TTL の考慮事項がありますが、NLB はより即時的な traffic shifting を提供します。

</details>

### 5. 3-AZ deployment における TopologySpreadConstraints の推奨 `maxSkew` 値は何ですか？

- A) 0
- B) 1
- C) 3
- D) 10

<details>
<summary>答えを表示</summary>

**答え: B) 1**

**解説:**
`maxSkew` を 1 にすると、topology domain 間の Pod 数の差が最大 1 になるように、Pod が均等に分散されます。これにより、node に resource constraints がある場合でも scheduling の柔軟性を保ちながら、良好なバランスを実現できます。

</details>

### 6. blue/green cluster architecture では、cluster 間で何を共有すべきですか？

- A) Worker nodes
- B) External DNS and load balancer
- C) etcd storage
- D) Kubernetes API server

<details>
<summary>答えを表示</summary>

**答え: B) External DNS and load balancer**

**解説:**
Blue/green cluster は、DNS record や load balancer などの外部 infrastructure を共有する別々の EKS cluster です。これにより、client-facing endpoint を変更せずに cluster 間で traffic を移行できます。

</details>

### 7. TopologySpreadConstraints で `whenUnsatisfiable: DoNotSchedule` が設定されている場合、何が起こりますか？

- A) Pod は constraint に関係なくどこにでも schedule される
- B) constraint を満たせない場合、Pod は pending のままになる
- C) Pod は自動的に削除される
- D) constraint は無視される

<details>
<summary>答えを表示</summary>

**答え: B) constraint を満たせない場合、Pod は pending のままになる**

**解説:**
`DoNotSchedule` は、spread constraint に違反する場合に Pod の scheduling を防ぎます。これにより topology requirements への厳密な準拠が保証されますが、cluster topology が constraint をサポートしない場合、Pod が pending になる可能性があります。

</details>

### 8. blue/green cluster 間の automated failover には、health check とともにどの AWS service を使用できますか？

- A) AWS Config
- B) Route53 health checks with failover routing
- C) AWS Inspector
- D) AWS Trusted Advisor

<details>
<summary>答えを表示</summary>

**答え: B) Route53 health checks with failover routing**

**解説:**
Route53 health checks は endpoint の可用性を継続的に監視し、failover routing policy を使用して healthy cluster に traffic を自動的に切り替えることができます。これにより、手動介入なしで automated disaster recovery が可能になります。

</details>

### 9. NLB cross-zone load balancing を使用する際の重要な考慮事項は何ですか？

- A) 常に無料である
- B) 追加の data transfer charges が発生する可能性がある
- C) VPC peering が必要である
- D) TCP protocol でのみ動作する

<details>
<summary>答えを表示</summary>

**答え: B) 追加の data transfer charges が発生する可能性がある**

**解説:**
cross-zone load balancing が有効な場合、NLB は有効化されたすべての AZ 内のすべての registered target に traffic を均等に分散します。その結果、Cross-AZ data transfer charges が発生する可能性があります。multi-AZ deployment を設計する際には、このコストを考慮してください。

</details>

### 10. zonal cluster deployment（a-zone blue、c-zone green）における主な利点は何ですか？

- A) networking complexity の低減
- B) failure isolation と独立した upgrade paths
- C) compute costs の削減
- D) 自動 data replication

<details>
<summary>答えを表示</summary>

**答え: B) failure isolation と独立した upgrade paths**

**解説:**
zonal cluster は failure domain isolation を提供します。つまり、1 つの zone での問題がもう一方の cluster に影響しません。これにより、独立した upgrade testing と段階的な rollout も可能になり、Kubernetes version upgrade 時のリスクを低減できます。

</details>

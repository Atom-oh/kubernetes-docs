# パート 10: IPAM 詳細クイズ

> **Cilium 1.20.2（stable、2026-09-16）· 2026-10-15**。 [1.21 pre-release] と記した項目は v1.21.0-pre.3 に基づきます。

1. **CNI ADD が `POST /ipam` で Pod IP を割り当てた後、endpoint が作成される前に CNI plugin がクラッシュしました。再起動しなくても Agent がその IP を解放するのはいつですか？**
   - A) 割り当て時に設定された 10 分間の有効期限タイマーが切れた後
   - B) Agent が再起動して endpoint を復元した場合のみ
   - C) REST 接続が切れた直後
   - D) `--excess-ip-release-delay` の既定値である 180 秒後

   <details>
   <summary>解答を表示</summary>

   **解答: A) 割り当て時に設定された 10 分間の有効期限タイマーが切れた後**

   **解説:**
   CNI plugin は有効期限フラグを設定して割り当てを要求するため、Agent は 10 分のタイマー（`defaults.IPAMExpiration`）を開始します。Endpoint が作成されるとタイマーは停止します。作成されなければ、タイマーが IP を解放します。180 秒の値は Operator における ENI の余剰 IP 解放に関するものです。

   </details>

2. **cluster-pool の Cilium 1.20.2 Helm 既定値（`10.0.0.0/8`、IPv4 マスクサイズ 24）では、この CIDR から PodCIDR を割り当てられるノード数と、各ノードブロックのアドレス数はいくつですか？**
   - A) 16,384 ノード、各 1,024 アドレス
   - B) 256 ノード、各 65,536 アドレス
   - C) 65,536 ノード、各 256 アドレス
   - D) 65,536 ノード、マスクの定義上、使用可能アドレスは各 254 個

   <details>
   <summary>解答を表示</summary>

   **解答: C) 65,536 ノード、各 256 アドレス**

   **解説:**
   pool CIDR 内のノード数は `2^(nodeMask - poolMask) = 2^(24 - 8) = 65,536` です。各ブロックには `2^(32 - 24) = 256` 個のアドレスがあります。ネットワーク／ブロードキャストのアドレス、ルーター、ヘルスチェック、Ingress 用のアドレスがブロックから除外されるため、Pod IP として使える数はそれより少なくなります。

   </details>

3. **Cilium 1.20.2 の allocator では、IPv6 cluster-pool の pool プレフィックス長と node mask の差を何が制限しますか？**
   - A) pool のサイズに関係なく各ノードに `/64` を割り当てるため、差は最低 64 ビット必要
   - B) allocator が非圧縮 bitmap を使うため、差は 16 ビット（`clusterSubnetMaxDiff`）以下でなければならない
   - C) bitmap が圧縮されるため、node mask が `/128` 以下であれば上限はない
   - D) IPv4 の既定値と同じ 8 ビットでなければならない

   <details>
   <summary>解答を表示</summary>

   **解答: B) allocator が非圧縮 bitmap を使うため、差は 16 ビット（`clusterSubnetMaxDiff`）以下でなければならない**

   **解説:**
   `pkg/ipam/cidrset` は、IPv6 の node mask が pool プレフィックスより 16 ビットを超えて長い場合、拒否します（`ErrCIDRSetSubNetTooBig`）。IPv4 では node mask が 32 以下であることだけが必要です。Helm の既定値 `fd00::/104` と `/120` は、ちょうど 16 ビットの上限です。

   </details>

4. **multi-pool IPAM では、新しい Pod に使う pool を Cilium はどの順で選択しますか？**
   - A) CiliumPodIPPool の selector、Pod annotation、namespace annotation の順。`require-pool-match` が設定されていなければ、最後に `default` pool を選ぶ
   - B) 常に `default` pool を使う。annotation と selector は masquerading と LB IPAM だけに影響する
   - C) namespace annotation、Pod annotation、`default` の順。CiliumPodIPPool selector は LB IPAM にだけ使う
   - D) Pod annotation（`ipv4-pool`/`ipv6-pool` が `ip-pool` より先）、namespace annotation、CiliumPodIPPool selector の順。`require-pool-match` が設定されていなければ、最後に `default` を選ぶ

   <details>
   <summary>解答を表示</summary>

   **解答: D) Pod annotation（`ipv4-pool`/`ipv6-pool` が `ip-pool` より先）、namespace annotation、CiliumPodIPPool selector の順。`require-pool-match` が設定されていなければ、最後に `default` を選ぶ**

   **解説:**
   Pod annotation が namespace annotation より優先され、それらは `podSelector`/`namespaceSelector` の一致より優先されます。一致するものがなければ、`ipam-default-ip-pool`（既定値は `default`）で指定された pool を使用します。ただし、Pod または namespace に `ipam.cilium.io/require-pool-match: "true"` が設定されている場合は割り当てがブロックされます。pool の選択は Pod 作成時に一度だけ行われます。

   </details>

5. **Pod に pool annotation がなく、同じアドレスファミリーに対する 2 つの異なる CiliumPodIPPool の selector に一致しました。どうなりますか？**
   - A) アドレスファミリーごとに一致する pool は 1 つだけでなければならないため、エラーとイベントが発生し、割り当てに失敗する
   - B) 名前をアルファベット順に並べて最初の pool が使われ、イベントが記録される
   - C) 一致した各 pool から 1 つずつアドレスが割り当てられ、両方の経路が設定される
   - D) tie-breaker として `default` pool を使い、selector は無視される

   <details>
   <summary>解答を表示</summary>

   **解答: A) アドレスファミリーごとに一致する pool は 1 つだけでなければならないため、エラーとイベントが発生し、割り当てに失敗する**

   **解説:**
   selector による選択では、アドレスファミリーごとに一致する pool が 1 つだけである必要があります。複数一致するとエラー（`multiple CiliumPodIPPools match pod ...`）が発生し、Pod は `ContainerCreating` のままになります。selector をより具体的にするか、Pod または namespace に明示的な annotation を設定して修正してください。

   </details>

6. **Cilium 1.20.2 における ENI prefix delegation について、正しい説明はどれですか？**
   - A) あらゆる EC2 インスタンスタイプで動作し、`/24` prefix を割り当てる。サブネットが満杯なら `/28` にフォールバックする
   - B) あらゆるインスタンスタイプで動作し、同じノードで `/32` と `/28` の割り当てを自由に混在させる。サブネットの状態に応じて Pod ごとに切り替える
   - C) `ipam.mode=multi-pool` と、委任する prefix を CIDR に指定した `CiliumPodIPPool` が必要
   - D) Nitro またはベアメタルのインスタンスに限り、`/28` prefix を割り当てる。セカンダリ `/32` IP をすでに持つノードではスキップし、サブネットに prefix が足りなければ `/32` にフォールバックする

   <details>
   <summary>解答を表示</summary>

   **解答: D) Nitro またはベアメタルのインスタンスに限り、`/28` prefix を割り当てる。セカンダリ `/32` IP をすでに持つノードではスキップし、サブネットに prefix が足りなければ `/32` にフォールバックする**

   **解説:**
   Operator は Nitro ハイパーバイザーまたはベアメタルかどうかを確認します。セカンダリ IP がすでにあるノードでは prefix モードをスキップし、混在モードにはしません。`InsufficientPrefixesInSubnet` が発生すると、そのノードでの prefix 割り当てを停止し、`AssignPrivateIpAddresses` を使用します。単位は `/28`（IPv4 で 16 アドレス、IPv6 では `/80`）です。ENI モードでは CiliumPodIPPool を使用しません。

   </details>

7. **Cilium 1.20 の ENI allocator は、EC2 インターフェイスの状態をどのように Agent に渡しますか？**
   - A) Operator が個々の IP を `spec.ipam.pool` に書き込み、Agent は 1.19 と同じく `status.ipam.used` に使用状況を報告する。ENI の状態は書き込まれない
   - B) Agent が独自の認証情報で直接 EC2 API を呼び出し、Operator は ENI の garbage collection だけを行う
   - C) Operator が ENI を `status.eni.enis` に書き込む。Agent はそれらを `/32` および `/28` CIDR に変換して `spec.ipam.pools.allocated`（pool `default`）に記録し、要求容量を `spec.ipam.pools.requested` に報告する
   - D) Operator が各 ENI を個別の CiliumPodIPPool として作成し、`ip-pool` annotation で選択する

   <details>
   <summary>解答を表示</summary>

   **解答: C) Operator が ENI を `status.eni.enis` に書き込む。Agent はそれらを `/32` および `/28` CIDR に変換して `spec.ipam.pools.allocated`（pool `default`）に記録し、要求容量を `spec.ipam.pools.requested` に報告する**

   **解説:**
   1.20 では ENI が multi-pool allocator に移行しました。EC2 API を呼び出すのは Operator だけです。Agent は ENI のインベントリから割り当て済み CIDR を導出し、必要容量を要求値として書き戻します。`spec.ipam.pool` / `status.ipam.used` モデルは、1.19 および 1.18 の CRD allocator で使われます。ENI モードでは CiliumPodIPPool も `ip-pool` annotation も使いません。

   </details>

8. **[1.21 pre-release] 現在 `--aws-use-primary-address` を Cilium Operator に直接渡しています。1.21 に移行する前に何をすべきですか？**
   - A) 何もする必要はない。この flag は非推奨になるだけで、1.21 でも Operator の flag として動作する
   - B) flag を削除し、`eni.nodeSpec.usePrimaryAddress=true` を設定する（Agent flag は `--eni-use-primary-address`）
   - C) 既定 pool の `CiliumPodIPPool` にある `spec.ipv4.pool[]` で設定する
   - D) 同じ名前の `--aws-use-primary-address` として Agent に移す

   <details>
   <summary>解答を表示</summary>

   **解答: B) flag を削除し、`eni.nodeSpec.usePrimaryAddress=true` を設定する（Agent flag は `--eni-use-primary-address`）**

   **解説:**
   per-node の `CiliumNode.spec.eni.use-primary-address` を唯一の信頼できる情報源にするため、1.21 では Operator flag が削除されます。Helm ユーザーには影響しません。chart はこれまでも Agent 側の値だけを配線していました。これは v1.21.0-pre.3 のプレリリース変更です。

   </details>

9. **[1.21 pre-release] `cilium.io/v2` の `CiliumPodIPPool` にある `spec.ipv4.pool[].reservedRanges` は何に使いますか？**
   - A) すべてのノードブロックからアドレスを除外し、LB IPAM pool が静的 Service IP として割り当てられるようにする
   - B) 既存ノードブロックを作り直さず、稼働中の pool の `maskSize` を変更できるようにする
   - C) すべてのノードブロックで router、health、ingress endpoint 用のアドレスを予約する
   - D) 古い CIDR を `cidrs` に残して既存のノードブロックを維持しつつ、新しいブロックをそこから割り当てないようにして、新しい CIDR へ段階的に移行する

   <details>
   <summary>解答を表示</summary>

   **解答: D) 古い CIDR を `cidrs` に残して既存のノードブロックを維持しつつ、新しいブロックをそこから割り当てないようにして、新しい CIDR へ段階的に移行する**

   **解説:**
   古い CIDR 全体を予約すると、Cilium は既存の割り当てを維持し、新しい PodCIDR ブロックはほかの CIDR からのみ割り当てます。すべてのノードグループの移行後、古い CIDR とその `pool` エントリーを削除します。各 `pool[].cidr` は `cidrs` のいずれかでなければならず、`maskSize` は不変です。

   </details>

10. **2 つの `CiliumLoadBalancerIPPool` リソースに重複するブロックが含まれています。LB IPAM はどう動作しますか？**
   - A) 後から追加された pool を Conflicting（`cilium.io/PoolConflict`）としてマークし、そこからは一切割り当てない
   - B) validating webhook によって、2 つ目の pool をアドミッション時に拒否する
   - C) 2 つを 1 つの pool にマージし、ブロックの和集合から割り当てる
   - D) Service 数に応じて重複範囲を 2 つの pool に均等配分する

   <details>
   <summary>解答を表示</summary>

   **解答: A) 後から追加された pool を Conflicting（`cilium.io/PoolConflict`）としてマークし、そこからは一切割り当てない**

   **解説:**
   LB IPAM は重複する pool をマージも拒否もしません。後から追加された pool に Conflicting のフラグが付き、`Conflicting` の表示列と `lbipam_conflicting_pools` メトリクスに示されます（実際の runtime prefix は `cilium_` または `cilium_operator_` のどちらか未検証です）。その pool からは割り当てられません。稼働中の pool を編集すると、既存 Service の IP が再割り当てされることもあるため、新しい pool の追加または `disabled: true` の設定を優先してください。

   </details>

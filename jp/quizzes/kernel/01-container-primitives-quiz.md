# コンテナを支えるカーネル機能のクイズ

このクイズでは、namespace、cgroup v2、netfilter、conntrackについて理解度を確認します。

## 多肢選択問題

1. 「カーネルにコンテナは存在しない」とはどういう意味で、そこから実務上どのような結論が導かれますか？
   - A) コンテナは仮想マシンの一種で、カーネルとは関係がない
   - B) コンテナはnamespace、cgroup、capabilityなどを組み合わせた慣習的な仕組みであるため、隔離は選択的であり、ランタイムが適用しない隔離には見落としが生じる
   - C) コンテナはユーザー空間のライブラリだけで実装されている
   - D) カーネル6.xで`struct container`が追加された

<details>

<summary>回答を表示</summary>

**回答: B) コンテナはnamespace、cgroup、capabilityなどを組み合わせた慣習的な仕組みであるため、隔離は選択的であり、ランタイムが適用しない隔離には見落としが生じる**

**解説:**
`struct container`も、コンテナを作成する単一のシステムコールもありません。ランタイムはnamespace（隔離）、cgroup（制限）、capability/seccomp/LSM（権限）、overlayfs（ファイルシステム）、netfilter（ネットワーク）をまとめて適用しながらプロセスを起動します。この組み合わせであることから2つの結論が導かれます。隔離はすべて適用されるかされないかの二択ではなく選択的です（Pod内でnetwork namespaceを共有しながらmountを分離する例があります）。また、カーネルは「コンテナを作成せよ」という命令を理解しないため、ランタイムがseccompプロファイルを適用しなければ、それなしでプロセスが実行されることになります。
</details>

2. Pod内の2つのコンテナが`localhost`経由で通信できるのに、同じポートをbindできないのはなぜですか？
   - A) Kubernetesがコンテナ間プロキシを自動で作成する
   - B) Podごとにnet namespaceを共有するため、同じIPアドレスとポート空間を使う
   - C) CNIがコンテナごとにloopbackを接続する
   - D) kube-proxyがPod内通信をルーティングする

<details>

<summary>回答を表示</summary>

**回答: B) Podごとにnet namespaceを共有するため、同じIPアドレスとポート空間を使う**

**解説:**
KubernetesはPodごとに1つのnet namespaceを作成し（pauseコンテナが保持します）、そのPod内のすべてのコンテナを入れます。そのため、同じIPアドレスとポート空間を共有し、`localhost`で通信できる一方、2つのコンテナが同時に8080へbindすることはできません。これがsidecarパターンの基礎です。また、netfilterルールはnet namespace単位で適用されるため、sidecarメッシュのinitコンテナはノード全体に影響を与えずPod内にiptablesルールを追加できます。
</details>

3. cgroup v2では`memory.current`が上限近くにあっても、まったく正常である場合があるのはなぜですか？
   - A) `memory.current`は推定値なので不正確である
   - B) `memory.current`には解放可能なpage cacheが含まれ、上限に達するとカーネルが領域を確保するためにpage cacheを破棄する
   - C) cgroup v2ではメモリ制限が適用されない
   - D) `memory.current`はノード全体のメモリを表示する

<details>

<summary>回答を表示</summary>

**回答: B) `memory.current`には解放可能なpage cacheが含まれ、上限に達するとカーネルが領域を確保するためにpage cacheを破棄する**

**解説:**
アプリケーションが実際に保持しているメモリ（anon/RSS）が上限を大きく下回っていても、大量のファイルを読むことでpage cacheが蓄積し、`memory.current`が上限に達することがあります。通常はpage cacheを解放可能なので、カーネルが破棄して空きを作り、OOMにはなりません。問題となるのは**reclaimがallocationに追いつけない場合**で、そのときOOM killerが動作します。そのため診断には`memory.stat`の`anon`、`memory.events`の`oom`、PSI（`memory.pressure`）を組み合わせる必要があります。
</details>

4. CPU使用率は20%と低いのにp99レイテンシーが急上昇しています。CPU制限が原因であることをどう確認しますか？
   - A) `top`で使用率を確認し直す
   - B) `cpu.stat`の`nr_throttled`と`nr_periods`の比率を確認する
   - C) `memory.pressure`を確認する
   - D) ノードの`/proc/loadavg`を確認する

<details>

<summary>回答を表示</summary>

**回答: B) `cpu.stat`の`nr_throttled`と`nr_periods`の比率を確認する**

**解説:**
CPU制限は帯域幅の制限です。`cpu.max`が`20000 100000`なら、「100msの期間につき最大20ms」という意味です。複数スレッドで短いバースト処理を行うアプリケーションは早い段階でクォータを使い切り、期間が終わるまで強制的に停止されます。平均使用率は20%に見えてもレイテンシーが急上昇します。`nr_throttled / nr_periods`の比率が高ければ、制限が原因であることを示します。根本原因は通常、アプリケーションが認識するCPU数とクォータの不一致です。そのため、まず`GOMAXPROCS`や`-XX:ActiveProcessorCount`を合わせてください。
</details>

5. 2026年時点のkube-proxyモードについて、正しい説明はどれですか？
   - A) nftablesがデフォルトで、iptablesは削除されている
   - B) nftablesは1.33でGA、IPVSは1.35で非推奨（デフォルト無効化は1.40、削除は1.43を予定）、デフォルトは引き続きiptables
   - C) IPVSがデフォルトで、nftablesはalpha
   - D) 3つのモードの性能特性は同じ

<details>

<summary>回答を表示</summary>

**回答: B) nftablesは1.33でGA、IPVSは1.35で非推奨（デフォルト無効化は1.40、削除は1.43を予定）、デフォルトは引き続きiptables**

**解説:**
nftablesモードはalphaの1.29からbetaの1.31を経て、**1.33でGA**になりました。O(1)検索と差分によるルール更新が可能です（workerにはカーネル5.13以降が必要で、AL2023は満たしています）。IPVSモードは**2025年12月の1.35で非推奨**となりました。upstreamでは1.40でデフォルト無効化、1.43で削除する予定です。将来の計画については[保守されているKEP-5495のスケジュール](https://github.com/kubernetes/enhancements/blob/master/keps/sig-network/5495-deprecate-ipvs-mode-in-kube-proxy/README.md)を確認してください。推奨される移行先はnftablesですが、**デフォルトは今もiptables**のため、明示的な切り替えが必要です。
</details>

6. conntrackの枯渇が疑われる場合、どう検証すべきですか？
   - A) `dmesg`ですぐ確認できる明白なカーネルパニック
   - B) conntrack数/最大値、挿入/ドロップカウンター、カーネルログを照合する。`insert_failed`だけでは枯渇の固有の証拠にならない
   - C) 既存の接続がすべて直ちに切断される
   - D) CPU使用率が100%になる

<details>

<summary>回答を表示</summary>

**回答: B) conntrack数/最大値、挿入/ドロップカウンター、カーネルログを照合する。`insert_failed`だけでは枯渇の固有の証拠にならない**

**解説:**
NATを使わないトラフィックにもconntrackが適用されることがあります。Headless ServiceのDNSではVIP DNATを避けられますが、conntrackを自動的に迂回するわけではありません。
</details>

7. EKSでconntrack値を調整するとき、何に注意すべきですか？
   - A) ノードbootstrapでsysctlを設定すれば十分である
   - B) EKSがデフォルトで提供する`kube-proxy-config` ConfigMapがコマンドライン引数より優先されるため、sysctlだけ引き上げてもkube-proxyによって元に戻される場合がある
   - C) conntrackは固定値で変更できない
   - D) Podの`securityContext.sysctls`でノード全体の値を変更できる

<details>

<summary>回答を表示</summary>

**回答: B) EKSがデフォルトで提供する`kube-proxy-config` ConfigMapがコマンドライン引数より優先されるため、sysctlだけ引き上げてもkube-proxyによって元に戻される場合がある**

**解説:**
kube-proxyもconntrack値を管理します。EKSはデフォルトでCLI引数より優先される`kube-proxy-config` ConfigMapを提供します。正しい方法は、ConfigMapの`conntrack.maxPerCore`/`conntrack.min`を調整し、kube-proxy DaemonSetを再起動することです。`maxPerCore`を使うとCPUコアごとの値となり、ノードサイズに比例して調整されます。Dは誤りです。`nf_conntrack_max`はノード全体に適用され、Pod仕様から変更できません。
</details>

8. overlayfsのcopy-upで起きる運用上の問題は何ですか？
   - A) イメージレイヤーが重複して保存され、レジストリのサイズが増える
   - B) lowerdirのファイルを変更するとファイル全体がupperdirへコピーされるため、大きなファイルへの小さな変更でも全体分のコピーコストが発生する
   - C) レイヤー数に応じてコンテナ起動時間が増える
   - D) レイヤー数に比例して読み取り性能が低下する

<details>

<summary>回答を表示</summary>

**回答: B) lowerdirのファイルを変更するとファイル全体がupperdirへコピーされるため、大きなファイルへの小さな変更でも全体分のコピーコストが発生する**

**解説:**
overlayfsは読み取り専用のlowerdir（イメージレイヤー）と書き込み可能なupperdir（変更内容）を統合します。lowerdir内のファイルを変更するには、先にupperdirへコピーする必要があり、**ファイル全体がコピーされます。** 1GBのファイルの1バイトだけを変更しても1GBがコピーされます。そのため、コンテナ内の書き込みが多いとノードのephemeral storageが消費され、**書き込みの多いデータはemptyDirやPVCなどのvolumeに置いてください。**
</details>

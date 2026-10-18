# Calico アーキテクチャクイズ

> **関連ドキュメント**: [Calico Architecture](../../../networking/calico/02-architecture.md)
> **最終更新日**: 2026年9月12日

## クイズ

1. Calico のアーキテクチャにおける Felix の主な役割は何ですか？
   - A) BGP ルートの配布
   - B) 各ノードでのポリシー適用とインターフェース管理
   - C) データストア接続の集約
   - D) 設定テンプレートの処理

<details>
<summary>回答を表示</summary>

**回答: B) 各ノードでのポリシー適用とインターフェース管理**

**解説:**
Felix は、エンドポイントのインターフェース設定、該当するルート、およびカーネルポリシーを調整します。Calico Linux ネットワーキングの全構成では、コンテナランタイムが CNI/IPAM チェーンを呼び出してアドレスを割り当て、Pod の veth インターフェースを作成します。Felix が CNI ADD で直接呼び出されることはなく、Pod IP の割り当ても担当しません。

</details>

2. BIRD は何の略で、Calico ではどのような役割を果たしますか？
   - A) Basic Internet Routing Daemon — DNS 解決を処理する
   - B) BIRD Internet Routing Daemon — BGP ルーティングを処理する
   - C) Binary Internet Relay Daemon — パケット転送を処理する
   - D) Bridge Internet Routing Device — VXLAN トンネリングを処理する

<details>
<summary>回答を表示</summary>

**回答: B) BIRD Internet Routing Daemon — BGP ルーティングを処理する**

**解説:**
BIRD は、そのバックエンドが有効な場合に BGP セッションとルート交換を管理します。ルートリフレクターとして動作し、カーネルプロトコルを通じてカーネルとルートを同期することもできます。BGP はカプセル化と併用できるため、BGP を有効にしただけでカプセル化されない転送が保証されるわけではありません。ワークロードのパケットが BIRD プロセスを通過することもありません。

</details>

3. Calico のアーキテクチャにおける confd の役割は何ですか？
   - A) コンテナ設定の管理
   - B) BIRD 設定ファイルの動的な生成
   - C) ネットワークポリシーの保存
   - D) トラフィックの負荷分散

<details>
<summary>回答を表示</summary>

**回答: B) BIRD 設定ファイルの動的な生成**

**解説:**
confd は関連するデータストアの状態を監視し、インストール済みの BIRD テンプレートから設定を生成します。生成結果を確認して、設定された reload コマンドを実行します。生成ファイルは永続的な設定元ではありません。生成済みの bird.cfg を編集するのではなく、BGP API リソースを変更してください。

</details>

4. Typha のデプロイに関する正しい説明はどれですか？
   - A) クラスター規模にかかわらず常に必要
   - B) Operator によるインストールでは 50 ノード未満でもデプロイされることがある。使用中のバージョンのスケーリングロジックと実際のワークロード要件に従う
   - C) eBPF モードを使用する場合に限り必要
   - D) マルチクラスター構成の場合に限り必要

<details>
<summary>回答を表示</summary>

**回答: B) Operator によるインストールでは 50 ノード未満でもデプロイされることがある。使用中のバージョンのスケーリングロジックと実際のワークロード要件に従う**

**解説:**
Typha は、データストアの更新が各 Felix に直接配信される際の負荷を軽減します。Typha が常に 50 ノードを超えた場合にのみ必須というわけではなく、Operator を使わないすべてのインストールで必要なわけでもありません。Operator 1.42.6 は、小規模クラスターでも Typha のレプリカ数を調整します。その際、カウント対象のノード数を使い、Linux ノードへの配置可能性も確認します。

</details>

5. Calico がサポートするデータストアの選択肢は何ですか？
   - A) MySQL と PostgreSQL
   - B) etcd と Kubernetes API
   - C) MongoDB と Redis
   - D) 専用 etcd のみ

<details>
<summary>回答を表示</summary>

**回答: B) etcd と Kubernetes API**

**解説:**
Calico には、機能やインストール方式に応じて、Kubernetes API と直接接続する etcdv3 データストアの経路があります。Kubernetes API を使う場合も Kubernetes 自体のストレージは使用しますが、Calico 専用の etcd クラスターは不要です。直接 etcd を使う場合は、TLS、認証情報、可用性、バックアップを別途設計する必要があります。ノード数だけを理由に切り替えるものではありません。

</details>

6. Operator 1.42.6 は、標準的な Open Source kube-controllers のデプロイでどのコントローラーを選択しますか？
   - A) Policy のみ
   - B) node と loadbalancer
   - C) Node と Policy のみ
   - D) WorkloadEndpoint のみ

<details>
<summary>回答を表示</summary>

**回答: B) node と loadbalancer**

**解説:**
固定された Operator のレンダラーは、通常の Open Source デプロイでは node と loadbalancer を起動します。Policy、namespace、serviceaccount、workloadendpoint の各コントローラーも、該当するデータストアや設定経路では利用できますが、常にすべて有効になるわけではありません。ServiceAccount profile に Kubernetes RBAC 権限を付与する機能はありません。

</details>

7. カウント対象のノードが 500 台の場合、Operator 1.42.6 のスケーリング関数が返す Typha の望ましいレプリカ数はいくつですか？
   - A) 50 ノードごとに 1 レプリカ
   - B) floor(500 / 200) + 2 による 4 レプリカ
   - C) 常に 5 レプリカ
   - D) 100 ノードごとに 1 レプリカ、最小 1

<details>
<summary>回答を表示</summary>

**回答: B) floor(500 / 200) + 2 による 4 レプリカ**

**解説:**
カウント対象が 4 ノードを超えると、このバージョンは max(3, floor(N / 200) + 2) を計算するため、500 ノードでは 4 になります。1～2 ノードでは 1、3～4 ノードでは 2 です。1,000 ノードの場合は 7 になります。オートスケーラーはスケジュール不可のノードと AKS 仮想ノードを除外し、利用可能な Linux ノードも確認します。この結果はスループットを保証するものではありません。

</details>

8. ローカルのワークロードルートとカーネルポリシーの状態を調整する Calico エージェントはどれですか？
   - A) BIRD
   - B) confd
   - C) Felix
   - D) Typha

<details>
<summary>回答を表示</summary>

**回答: C) Felix**

**解説:**
Felix はローカルのワークロードに関するルートとポリシーを調整します。ただし、ルートを扱うのが Felix だけという意味ではありません。CNI は初期インターフェースとルートを作成し、BIRD のカーネルプロトコルは BGP で学習したルートをインストールできます。confd は BIRD の設定を生成し、Typha はキャッシュした状態を配信します。

</details>

9. Typha が Felix インスタンスとの通信に使用するポートは何番ですか？
   - A) 443
   - B) 5473
   - C) 8080
   - D) 9090

<details>
<summary>回答を表示</summary>

**回答: B) 5473**

**解説:**
TCP 5473 は、Felix などのクライアント向けに Typha が使用するデフォルトの同期用リスナーポートです。メトリクス用やヘルスチェック用のポートとは別であり、アプリケーショントラフィックを中継するものではありません。Operator は TLS の信頼設定とクライアント ID も構成します。

</details>

10. eBPF モードを有効にする FelixConfiguration の設定はどれですか？
   - A) ebpfEnabled: true
   - B) bpfEnabled: true
   - C) dataplaneMode: ebpf
   - D) useEbpf: true

<details>
<summary>回答を表示</summary>

**回答: B) bpfEnabled: true**

**解説:**
bpfEnabled は、FelixConfiguration で有効な低レベルのフィールドです。Operator が管理するインストールでは、サポート対象の Installation linuxDataplane 設定を使用し、kube-proxy と API の到達性を調整してください。このブール値を変更するだけでは、検証済みの移行を完了したことにも、すべての eBPF 機能が利用可能であることにもなりません。

</details>

11. 大規模クラスターに Typha がデプロイされていない場合、Felix インスタンスには何が起こりますか？
   - A) Felix インスタンスの起動に失敗する
   - B) 各 Felix がデータストアに直接接続し、API サーバーに過剰な負荷がかかる可能性がある
   - C) ネットワークポリシーが適用されなくなる
   - D) BGP ピアリングに失敗する

<details>
<summary>回答を表示</summary>

**回答: B) 各 Felix がデータストアに直接接続し、API サーバーに過剰な負荷がかかる可能性がある**

**解説:**
ノード数や更新量が増えると、データストアへの直接 watch によって API の負荷が高まる可能性があります。これは容量上の懸念であり、Typha がないとポリシー適用や BGP が必ず停止するという意味ではありません。Typha がある場合でも、ほかのコンポーネントは Kubernetes API にアクセスします。

</details>

12. Felix のデフォルトのヘルスチェックポートは何番ですか？
   - A) 8080
   - B) 9091
   - C) 9099
   - D) 10250

<details>
<summary>回答を表示</summary>

**回答: C) 9099**

**解説:**
ヘルスチェックの提供が有効な場合、Felix のデフォルトのヘルスポートは 9099 で、バインド先はデフォルトで localhost です。Probe とネットワークの設定は実際のデプロイに合わせる必要があります。管理者の PC から localhost にリクエストしても、ノードを調べることにはなりません。通常のメトリクスポートは 9091 です。

</details>

---

[学習資料](../../../networking/calico/02-architecture.md) | [前のクイズ](01-introduction-quiz.md) | [次のクイズ](03-networking-modes-quiz.md)

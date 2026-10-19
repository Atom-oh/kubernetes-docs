# Kubernetes クラスターのアーキテクチャに関するクイズ

このクイズでは、Kubernetes クラスターのアーキテクチャ、主要コンポーネント、通信経路、高可用性構成について理解度を確認します。

## 選択問題

1. 次のうち、Kubernetes コントロールプレーンの中核コンポーネントではないものはどれですか。
   - A) kube-apiserver
   - B) etcd
   - C) kube-proxy
   - D) kube-scheduler
   
<details>

<summary>解答を表示</summary>

**解答: C) kube-proxy**

**解説:**
kube-proxy はノード上で動作するコンポーネントであり、コントロールプレーンの一部ではありません。コントロールプレーンの中核コンポーネントは kube-apiserver、etcd、kube-scheduler、kube-controller-manager、cloud-controller-manager です。kube-proxy は各ノードでネットワークルールを管理し、接続を転送します。
</details>

2. Kubernetes API の状態を保存する「正」となる情報源として機能するコンポーネントはどれですか。
   - A) kube-apiserver
   - B) etcd
   - C) kube-controller-manager
   - D) kubelet
   
<details>

<summary>解答を表示</summary>

**解答: B) etcd**

**解説:**
etcd は、一貫性と高可用性を備えたキー・バリュー型ストアで、Kubernetes API の状態を保存する「正」となる情報源です。クラスターの状態、構成、メタデータはすべて etcd に保存されます。他のコントロールプレーンコンポーネントは kube-apiserver を介して etcd の情報を読み書きします。
</details>

3. 次のうち、Kubernetes のノードコンポーネントではないものはどれですか。
   - A) kubelet
   - B) kube-proxy
   - C) コンテナランタイム
   - D) kube-controller-manager
   
<details>

<summary>解答を表示</summary>

**解答: D) kube-controller-manager**

**解説:**
kube-controller-manager はコントロールプレーンのコンポーネントであり、ノードコンポーネントではありません。ノードコンポーネントは kubelet、kube-proxy、コンテナランタイム（containerd、CRI-O など）です。kube-controller-manager はコントロールプレーン上で動作し、ノードコントローラーやレプリケーションコントローラーなど、さまざまなコントローラープロセスを実行します。
</details>

4. 新しく作成された Pod を実行するノードを選択する、Kubernetes のコントロールプレーンコンポーネントはどれですか。
   - A) kube-apiserver
   - B) kube-scheduler
   - C) kubelet
   - D) kube-controller-manager
   
<details>

<summary>解答を表示</summary>

**解答: B) kube-scheduler**

**解説:**
kube-scheduler は、新しく作成された Pod を実行するノードを選択するコントロールプレーンコンポーネントです。スケジューリングでは、まず Pod を実行できるノードを絞り込み（フィルタリング）、次に適切なノードを評価してスコアを付け、最後に最適なノードへ Pod を割り当てます。kube-scheduler は、リソース要件、ハードウェア・ソフトウェア・ポリシー上の制約、アフィニティ／アンチアフィニティ、データの局所性、ワークロード間の干渉を考慮します。
</details>

5. クラウドプロバイダーの API と連携するコントロールプレーンコンポーネントはどれですか。
   - A) kube-apiserver
   - B) etcd
   - C) cloud-controller-manager
   - D) kubelet
   
<details>

<summary>解答を表示</summary>

**解答: C) cloud-controller-manager**

**解説:**
cloud-controller-manager は、クラウド固有の制御ロジックを持ち、クラウドプロバイダーの API と連携するコントロールプレーンコンポーネントです。これにより、Kubernetes のコア部分とクラウドプロバイダー API の依存関係を分離できます。cloud-controller-manager は、ノード、ルート、サービスなどに関するクラウド固有のコントローラーを実行します。ストレージのプロビジョニング、アタッチ、マウントは、CSI コントローラーとノードプラグインが処理します。
</details>

6. 各ノードで動作し、Pod 内のコンテナ実行を管理するエージェントは何ですか。
   - A) kube-proxy
   - B) kubelet
   - C) containerd
   - D) kube-scheduler
   
<details>

<summary>解答を表示</summary>

**解答: B) kubelet**

**解説:**
kubelet は各ノードで動作し、Pod 内のコンテナ実行を管理するエージェントです。さまざまな方法で PodSpec を受け取り、その仕様に従ってコンテナが正常に動作するようにします。主な役割は、PodSpec に基づくコンテナの実行、コンテナ状態の監視と報告、コンテナのライフサイクルとボリュームマウントの管理、ノード状態の報告、コンテナのヘルスチェックです。
</details>

7. Kubernetes のどのノードコンポーネントが Service IP 向けのネットワークルールを管理し、接続を転送しますか。
   - A) kubelet
   - B) kube-proxy
   - C) CNI plugin
   - D) containerd
   
<details>

<summary>解答を表示</summary>

**解答: B) kube-proxy**

**解説:**
kube-proxy は各ノードで動作し、Kubernetes の Service を実現するネットワークプロキシです。ノード上のネットワークルールを管理し、接続を転送します。Service IP とポートに対するルールの管理、接続転送、ロードバランシング、サービスディスカバリーを担います。Linux では iptables と nftables、Windows では kernelspace などの動作モードをサポートします。IPVS は v1.35 以降非推奨で、userspace モードは削除されています。
</details>

8. Kubernetes でコンテナを実行するための標準インターフェイスは何ですか。
   - A) CRI (Container Runtime Interface)
   - B) CNI (Container Network Interface)
   - C) CSI (Container Storage Interface)
   - D) CPI (Container Platform Interface)
   
<details>

<summary>解答を表示</summary>

**解答: A) CRI (Container Runtime Interface)**

**解説:**
CRI（Container Runtime Interface）は、Kubernetes でコンテナを実行するための標準インターフェイスです。CRI により、Kubernetes は containerd や CRI-O など複数のコンテナランタイムを利用できます。CRI は kubelet とコンテナランタイム間の通信 API を定義し、コンテナの作成、起動、停止、削除などの操作を可能にします。CNI（Container Network Interface）はネットワーク用、CSI（Container Storage Interface）はストレージ用のインターフェイスです。
</details>

9. Kubernetes クラスターの Pod ネットワークを実現するために使われるインターフェイスは何ですか。
   - A) CRI (Container Runtime Interface)
   - B) CNI (Container Network Interface)
   - C) CSI (Container Storage Interface)
   - D) API (Application Programming Interface)
   
<details>

<summary>解答を表示</summary>

**解答: B) CNI (Container Network Interface)**

**解説:**
CNI（Container Network Interface）は、Kubernetes の Pod ネットワークを実現する標準インターフェイスです。CNI プラグインはネットワークインターフェイスを Pod に接続し、IP アドレスを割り当てます。Calico、Cilium、Flannel など複数の CNI プラグインがあり、機能や性能特性はそれぞれ異なります。Kubernetes は CNI を通じてさまざまなネットワーク実装を利用できます。
</details>

10. Kubernetes クラスターとストレージシステムの間に標準インターフェイスを提供するものは何ですか。
    - A) CRI (Container Runtime Interface)
    - B) CNI (Container Network Interface)
    - C) CSI (Container Storage Interface)
    - D) CPI (Cloud Provider Interface)
    
<details>

<summary>解答を表示</summary>

**解答: C) CSI (Container Storage Interface)**

**解説:**
CSI（Container Storage Interface）は、Kubernetes とストレージシステムの間に標準インターフェイスを提供します。ストレージプロバイダーは、Kubernetes のコードを変更せずに独自のストレージドライバーを開発できます。CSI はボリュームの作成、削除、マウント、アンマウントなどの操作に使う標準 API を定義します。AWS EBS CSI Driver、Azure Disk CSI Driver、GCP PD CSI Driver などの CSI ドライバーがあります。
</details>

## 短答問題

11. Kubernetes コントロールプレーンで複数のコントローラープロセスを実行するコンポーネントは何ですか。

<details>

<summary>解答を表示</summary>

**解答: kube-controller-manager**

**解説:**
kube-controller-manager は複数のコントローラープロセスを実行するコントロールプレーンコンポーネントです。各コントローラーはクラスターの特定の機能を管理します。主なコントローラーには、ノード、レプリケーション、エンドポイント、サービスアカウントとトークン、Job、CronJob、DaemonSet、StatefulSet、PV、Namespace の各コントローラーとガベージコレクターがあります。
</details>

12. etcd のデータの一貫性を保つために使われる合意アルゴリズムは何ですか。

<details>

<summary>解答を表示</summary>

**解答: Raft**

**解説:**
etcd は、分散システム上のデータに強い一貫性を持たせるため、Raft 合意アルゴリズムを使います。Raft はリーダー選出、ログ複製、安全性の仕組みによって合意を実現します。etcd クラスターは通常 3 台または 5 台のノードで構成され、過半数（クォーラム）のノードが正常であれば動作を継続できます。
</details>

13. Linux で kube-proxy のモードを明示的に指定しない場合、デフォルトで使用されるモードは何ですか。

<details>

<summary>解答を表示</summary>

**解答: iptables**

**解説:**
kube-proxy のデフォルトモードは iptables です。このモードでは Linux の iptables を使って NAT を行い、Service IP 宛てのトラフィックを Pod に転送します。nftables も Linux のモードの一つで、v1.33 以降 stable です。移行前にカーネルと CNI の互換性を確認してください。IPVS は v1.35 以降非推奨で、v1.40 でデフォルト無効化、v1.43 で削除が予定されています。userspace モードは削除済みです。Windows では kernelspace モードを使います。
</details>

14. Kubernetes クラスターから API server と通信するための設定ファイルは何ですか。

<details>

<summary>解答を表示</summary>

**解答: kubeconfig**

**解説:**
kubeconfig は Kubernetes API server と通信するための設定ファイルです。クラスター情報、認証情報（証明書やトークンなど）、およびクラスターとユーザーの組み合わせである context を含みます。kubectl はデフォルトで $HOME/.kube/config を使います。--kubeconfig フラグまたは KUBECONFIG 環境変数を指定すれば、別のファイルを使えます。
</details>

15. Kubernetes で高可用性クラスターを構成する場合、一般に推奨されるコントロールプレーンノードの最小数はいくつですか。

<details>

<summary>解答を表示</summary>

**解答: 3**

**解説:**
高可用性クラスターでは、コントロールプレーンノードを最低 3 台にする構成が一般に推奨されます。etcd クラスターは過半数（クォーラム）で動作するため、3 台なら 1 台が故障しても（残る 2 台が過半数）動作を続けられます。5 台なら 2 台が故障しても（残る 3 台が過半数）動作できます。通常は奇数台で構成します。
</details>

## 実践問題

16. etcd データベースのバックアップを作成するコマンドを書いてください。バックアップ先は `/backup/etcd-snapshot-$(date +%Y%m%d).db`、etcd endpoint は `https://127.0.0.1:2379`、証明書ファイルは `/etc/kubernetes/pki/etcd/` にあります。

<details>

<summary>解答を表示</summary>

**解答:**
```bash
ETCDCTL_API=3 etcdctl snapshot save /backup/etcd-snapshot-$(date +%Y%m%d).db \
--endpoints=https://127.0.0.1:2379 \
--cacert=/etc/kubernetes/pki/etcd/ca.crt \
--cert=/etc/kubernetes/pki/etcd/server.crt \
--key=/etc/kubernetes/pki/etcd/server.key
```

**解説:**
このコマンドは ETCDCTL_API 環境変数を 3 に設定して etcdctl v3 API を使い、snapshot save コマンドで etcd データベースのスナップショットを作成します。--endpoints は etcd サーバーの endpoint を指定し、--cacert、--cert、--key は TLS 認証に必要な証明書ファイルを指定します。バックアップファイルは、現在の日付を含む名前で /backup ディレクトリに保存されます。
</details>

17. 次の要件を満たす kube-scheduler 設定ファイル（YAML）を書いてください。
    - スケジューラー名: custom-scheduler
    - リーダー選出を有効にする
    - スコアリングプラグイン: NodeResourcesBalancedAllocation の weight を 2 にする
    - フィルタリングプラグイン: NodeUnschedulable を有効のままにし、cordon 済みのノードを引き続き除外する

<details>

<summary>解答を表示</summary>

**解答:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
leaderElection:
  leaderElect: true

profiles:
  - schedulerName: custom-scheduler
    plugins:
      score:
        enabled:
          - name: NodeResourcesBalancedAllocation
            weight: 2
        disabled: []
```

**解説:**
この YAML は KubeSchedulerConfiguration オブジェクトを定義します。leaderElection.leaderElect: true によってリーダー選出を有効にし、profiles セクションで custom-scheduler というスケジューラープロファイルを定義します。plugins セクションでは、score プラグイン NodeResourcesBalancedAllocation の weight を 2 にします。NodeUnschedulable フィルターはデフォルトで有効のままです。これを無効にすると cordon 済みノードにも Pod がスケジュールされます。
</details>

18. 次の要件を満たす、高可用性 etcd クラスター用の起動コマンドを書いてください。
    - ノード名: etcd-1
    - クラスター名: etcd-cluster
    - クライアント URL: https://192.168.1.10:2379
    - peer URL: https://192.168.1.10:2380
    - 初期クラスター: etcd-1=https://192.168.1.10:2380,etcd-2=https://192.168.1.11:2380,etcd-3=https://192.168.1.12:2380
    - データディレクトリ: /var/lib/etcd
    - 証明書ファイルの場所: /etc/kubernetes/pki/etcd/

<details>

<summary>解答を表示</summary>

**解答:**
```bash
etcd \
--name=etcd-1 \
--initial-advertise-peer-urls=https://192.168.1.10:2380 \
--listen-peer-urls=https://192.168.1.10:2380 \
--listen-client-urls=https://192.168.1.10:2379,https://127.0.0.1:2379 \
--advertise-client-urls=https://192.168.1.10:2379 \
--initial-cluster-token=etcd-cluster \
--initial-cluster=etcd-1=https://192.168.1.10:2380,etcd-2=https://192.168.1.11:2380,etcd-3=https://192.168.1.12:2380 \
--initial-cluster-state=new \
--data-dir=/var/lib/etcd \
--cert-file=/etc/kubernetes/pki/etcd/server.crt \
--key-file=/etc/kubernetes/pki/etcd/server.key \
--trusted-ca-file=/etc/kubernetes/pki/etcd/ca.crt \
--client-cert-auth=true \
--peer-cert-file=/etc/kubernetes/pki/etcd/peer.crt \
--peer-key-file=/etc/kubernetes/pki/etcd/peer.key \
--peer-trusted-ca-file=/etc/kubernetes/pki/etcd/ca.crt \
--peer-client-cert-auth=true
```

**解説:**
このコマンドは etcd-1 という名前の etcd ノードを起動します。--initial-advertise-peer-urls と --listen-peer-urls は peer 通信用の URL を、--listen-client-urls と --advertise-client-urls はクライアント通信用の URL を指定します。--initial-cluster-token はクラスター固有の識別子を指定し、--initial-cluster はクラスター内の全ノードを列挙します。--initial-cluster-state=new は新しいクラスターを作成することを示します。--data-dir は etcd データの保存先を指定します。証明書関連のフラグは TLS 通信に使う証明書ファイルを指定します。
</details>

## 応用問題

19. Kubernetes クラスターの高可用性アーキテクチャを設計し、コントロールプレーンコンポーネントと etcd の配置方式、ロードバランサーの構成、障害発生時の対応を説明してください。

<details>

<summary>解答を表示</summary>

**解答:**

**高可用性 Kubernetes クラスターのアーキテクチャ設計**

1. **コントロールプレーンコンポーネントの配置**:
  - 3 台以上のコントロールプレーンノードを複数のアベイラビリティーゾーンに分散する
  - 各ノードに kube-apiserver、kube-scheduler、kube-controller-manager を配置する
  - kube-scheduler と kube-controller-manager はリーダー選出モードで動かす（一度にアクティブになるインスタンスは 1 つ）
  - kube-apiserver は水平スケール可能で、すべてのインスタンスが同時に稼働する

2. **etcd の配置方式**:
  - スタックトポロジー: etcd をコントロールプレーンノードと同じノード群に配置する
  - 外部トポロジー: etcd を別のノードに配置し、分離性と拡張性を高める
  - 3 台以上の etcd ノードを複数のアベイラビリティーゾーンに分散する（障害許容度とレイテンシーに応じて 3 台または 5 台を選ぶ）
  - etcd クラスターは Raft 合意アルゴリズムでデータの一貫性を保つ

3. **ロードバランサーの構成**:
  - kube-apiserver の前段にロードバランサーを配置する
  - エンドツーエンドの TLS とクライアント証明書認証を維持するため、L4 の TCP パススルーを使う
  - ヘルスチェックで異常な kube-apiserver インスタンスを検出し、トラフィックの送信先から除外する
  - クラウド環境では、クラウドプロバイダーのマネージドロードバランサー（AWS ELB、GCP Cloud Load Balancer など）を使う
  - オンプレミス環境では、HAProxy、NGINX、keepalived などを使う

4. **障害シナリオと対応**:
  - **コントロールプレーンノードが 1 台故障した場合**:
  - kube-apiserver: ロードバランサーが正常なノードへトラフィックを振り分ける
  - kube-scheduler / kube-controller-manager: リーダー選出により別ノードのインスタンスがアクティブになる
  - etcd: 過半数が正常ならクラスターは動作を続ける（3 台中 2 台、5 台中 3 台）

  - **アベイラビリティーゾーンが停止した場合**:
  - ノードを複数のアベイラビリティーゾーンに分散し、単一ゾーンの停止に備える
  - ワーカーノードも複数のアベイラビリティーゾーンに分散する

  - **ネットワーク分断が発生した場合**:
  - etcd は過半数で動作し、ネットワーク分断によるスプリットブレインを防ぐ
  - 少数側は書き込みを確定できず、線形化可能な読み取りにも応答できない。明示的に要求された serializable read では、古いローカルデータが返る場合がある

  - **etcd のデータが破損または消失した場合**:
  - etcd を定期的にバックアップする
  - バックアップからの復旧手順を文書化し、テストする

5. **その他の考慮事項**:
  - **証明書管理**: 証明書の有効期限を監視し、自動更新する
  - **監査ログ**: 重要な操作の監査ログを有効にし、外部に保存する
  - **監視とアラート**: コントロールプレーンコンポーネントの状態を監視し、アラートを設定する
  - **自動復旧**: systemd サービスの自動再起動など、復旧の仕組みを実装する

この高可用性構成により、ノード 1 台、アベイラビリティーゾーン 1 つ、または一部のコンポーネントに障害が発生しても、Kubernetes クラスターの動作を継続できます。
</details>

20. Kubernetes クラスターのネットワーク構成、Pod 間通信、Service ネットワーク、外部通信の仕組み、CNI プラグインの役割を説明してください。また、NetworkPolicy を使って Pod 間通信を制限する方法も説明してください。

<details>

<summary>解答を表示</summary>

**解答:**

**Kubernetes のネットワークアーキテクチャ**

1. **Kubernetes ネットワークモデル**:
  - すべての Pod に一意の IP アドレスを割り当てる
  - Pod 同士は NAT なしで通信できる
  - ノードと Pod は NAT なしで通信できる
  - 同じ Pod 内のコンテナは localhost を通じて通信する

2. **Pod 間通信**:
  - **同じノード上の Pod 間**: CNI プラグインに応じて、ローカルデータプレーン（ブリッジ、ルーティング、eBPF など）を介して通信する
  - **異なるノード上の Pod 間**: オーバーレイネットワークまたはルーティングテーブルを介して通信する
  - CNI プラグインが Pod の IP アドレス割り当てとルーティングを処理する

3. **Service ネットワーク**:
  - **ClusterIP**: クラスター内からのみ到達できる仮想 IP アドレス
  - **kube-proxy**: Service IP 宛てのトラフィックを Pod に転送する
  - iptables モード: Linux の iptables ルールで NAT を実装する
  - nftables モード: Linux の nftables データプレーンを構成する。IPVS は非推奨
  - **CoreDNS**: Service 名を ClusterIP に名前解決する DNS サービス
  - **サービスディスカバリー**: 環境変数または DNS で Service を検出する

4. **外部との通信**:
  - **Ingress**: HTTP/HTTPS トラフィックを Service にルーティングする
  - **NodePort**: ノード上の特定ポートを通じて Service を公開する
  - **LoadBalancer**: クラウドプロバイダーのロードバランサーを通じて Service を公開する
  - **ExternalName**: 外部サービスを指す CNAME レコードを作成する

5. **CNI（Container Network Interface）プラグインの役割**:
  - ネットワークインターフェイスを Pod に接続する
  - IP アドレスを割り当て、管理する
  - ルーティングテーブルを構成する
  - NetworkPolicy を実装する
  - 主な CNI プラグイン:
  - **Calico**: BGP ベースのネットワーク、NetworkPolicy 対応、高い性能
  - **Cilium**: eBPF ベースのネットワークとセキュリティ、L3〜L7 のセキュリティポリシー、高い性能
  - **Flannel**: シンプルなオーバーレイネットワークと容易な構成
  - **Weave Net**: 複数ホスト間のコンテナネットワークと暗号化に対応

6. **NetworkPolicy による Pod 間通信の制限**:
  - NetworkPolicy リソースで Pod 間通信を制御する
  - ポリシーがない場合、デフォルトではすべての Pod が相互に通信できる
  - NetworkPolicy の主なフィールド:
  - **podSelector**: ポリシーの適用対象となる Pod を選択する
  - **policyTypes**: Ingress（受信）、Egress（送信）、または両方を指定する
  - **ingress**: 受信トラフィックのルール
  - **egress**: 送信トラフィックのルール

  - **デフォルト拒否ポリシーの例**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

  - **特定の Pod 間のみ通信を許可するポリシーの例**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Ingress
  ingress:
    - from:
      - podSelector:
          matchLabels:
            app: frontend
      ports:
        - protocol: TCP
          port: 8080
```

  - **Namespace 間の通信を制御する例**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-monitoring
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Ingress
  ingress:
    - from:
      - namespaceSelector:
          matchLabels:
            purpose: monitoring
      ports:
        - protocol: TCP
          port: 9090
```

7. **NetworkPolicy の実装に関する注意点**:
  - NetworkPolicy は CNI プラグインによって実装される
  - すべての CNI プラグインが NetworkPolicy に対応しているわけではない
  - ポリシーを適用する前にテスト環境で検証する
  - デフォルト拒否ポリシーから始め、必要な通信だけを許可する

Kubernetes のネットワークアーキテクチャはコンテナ間の柔軟で拡張性の高い通信を可能にし、NetworkPolicy によってきめ細かなセキュリティ制御を提供します。
</details>

---

[学習資料に戻る](../../core/01-cluster-architecture.md) | [次のクイズ: Pod とワークロード](../core/02-pods-and-workloads-quiz.md)

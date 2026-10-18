# クラスター管理クイズ

このクイズでは、セルフマネージド Kubernetes と EKS の運用、バックアップ、メンテナンス、監視、復旧を扱います。元の 15 問を維持しています。ホストレベルの etcd 手順は、マネージド EKS コントロールプレーンには適用されません。

## 短答問題

1. Kubernetes クラスターにおける etcd データベースのバックアップと復元の手順を説明してください。

<details>
<summary>答えを表示</summary>

**答え:**

**etcd のバックアップ手順:**

1. **etcdctl がインストールされていることを確認する:**
   ```bash
   etcdctl version
   ```

2. **バックアップコマンドを実行する:**
   ```bash
   ETCDCTL_API=3 etcdctl snapshot save snapshot.db \
     --endpoints=https://127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt \
     --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key
   ```

3. **バックアップファイルを検証する:**
   ```bash
   etcdutl snapshot status snapshot.db --write-out=table
   ```

4. **バックアップファイルを安全な場所に保管する:**
   - クラスター外のストレージ
   - クラウドストレージ（S3、GCS など）
   - 別の物理的な場所

**etcd の復元手順:**

1. スナップショットを検証し、元のデータ、PKI、暗号化プロバイダーの鍵と設定を保護します。etcd スナップショットには、永続ボリュームのファイルやホスト設定のすべては含まれません。
2. ディストリビューションの手順に従って、すべての API server と対象の etcd プロセスを停止します。kubeadm では systemd unit ではなく static Pod を使うのが一般的です。kubelet を停止しただけでは、これらのコンテナは停止しません。
3. 互換性のある etcdutl を使い、新しいディレクトリへオフラインで復元します。次の単一メンバー例は HA クラスターの復旧コマンドではありません。

```bash
etcdutl snapshot restore snapshot.db \
  --data-dir=/var/lib/etcd-restore \
  --name=etcd-1 \
  --initial-cluster=etcd-1=https://127.0.0.1:2380 \
  --initial-cluster-token=restored-cluster \
  --initial-advertise-peer-urls=https://127.0.0.1:2380 \
  --bump-revision=1000000000 --mark-compacted
```

4. HA 構成では、同じスナップショットを各メンバーの名前と peer URL を使い、全メンバーを含む同一の membership list で復元します。revision bump はスナップショット後の書き込み数を上回る値に設定し、watch cache を無効化します。
5. 正しい所有者と証明書を設定して、etcd manifest/service が復元したデータを参照するようにします。API server/controller を再起動する前に etcd の quorum と健全性を確認し、その後ノードとワークロードも検証します。
6. [公式の復旧手順](https://etcd.io/docs/v3.6/op-guide/recovery/)に従います。EKS の利用者は、マネージド etcd にアクセスせず、サポート対象のバックアップツールを使ってアプリケーションリソースとデータを復元します。

**ベストプラクティス:**
- 定期的なバックアップスケジュール（例: 毎日）を設定する
- バックアップ前に etcd クラスターの状態を確認する
- バックアップファイルの完全性を検証する
- 復元手順を定期的にテストする
- バックアップファイル名にタイムスタンプを含める
- 複数のバックアップバージョンを保持する
- バックアップと復元の手順を文書化する
</details>

2. Kubernetes クラスターのノードメンテナンス手順を説明し、`cordon`、`drain`、`uncordon` コマンドの違いを説明してください。

<details>
<summary>答えを表示</summary>

**答え:**

**ノードメンテナンス手順:**

1. **ノードの状態を確認する:**
   ```bash
   kubectl get nodes
   kubectl describe node <node_name>
   ```

2. **ノードを cordon する:**
   ```bash
   kubectl cordon <node_name>
   ```

3. **ノードを drain する:**
   ```bash
   kubectl drain <node_name> --ignore-daemonsets
   ```

4. **メンテナンス作業を実施する:**
   - ソフトウェアの更新
   - カーネルのアップグレード
   - ハードウェアの交換
   - 設定の変更

5. **作業完了後にノードを uncordon する:**
   ```bash
   kubectl uncordon <node_name>
   ```

6. **ノードの状態を確認する:**
   ```bash
   kubectl get nodes
   ```

**コマンドの違い:**

1. **`kubectl cordon <node_name>`:**
   - ノードをスケジュール不可としてマークします。
   - 新しい Pod はそのノードにスケジュールされません。
   - すでに実行中の Pod は実行を継続します。
   - ノードの状態に `SchedulingDisabled` が表示されます。

2. **`kubectl drain <node_name>`:**
   - ノードをスケジュール不可としてマークします（cordon も実行します）。
   - 実行中の Pod をノードから安全に退避させます。
   - ワークロードコントローラーが置き換えの Pod を作成する場合があります。再スケジュールは、空き容量と配置制約によって決まります。
   - `--ignore-daemonsets` を指定しないと、DaemonSet の Pod がある場合は drain が拒否されます。このフラグを指定しても、それらの Pod はノード上に残ります。
   - emptyDir ボリュームを使う Pod のデータは失われる可能性があるため、`--delete-emptydir-data` フラグが必要となる場合は特別な取り扱いを検討してください。
   - PodDisruptionBudget を尊重します。

3. **`kubectl uncordon <node_name>`:**
   - ノードを再びスケジュール可能としてマークします。
   - 新しい Pod をノードにスケジュールできます。
   - 以前に退避された Pod は自動的には戻りません。

**メンテナンス時の考慮事項:**
- クラスターに十分な余剰容量があることを確認する
- 重要なワークロードに PodDisruptionBudget を設定する
- 一度に 1 つのノードだけをメンテナンスする
- メンテナンス期間中はオートスケーリング設定を調整する
- メンテナンスの前後にワークロードの状態を確認する
- ローリングアップデート戦略を使う
</details>

3. Kubernetes クラスターのリソース使用量を監視、管理する方法を説明してください。使用するツールや手法も挙げてください。

<details>
<summary>答えを表示</summary>

**答え:**

**Kubernetes のリソース監視・管理方法:**

**1. 基本的な監視ツール:**

- **Metrics Server:**
  - 基本的な CPU とメモリの使用量メトリクスを提供します
  - `kubectl top` コマンドで使用できます
  - Kubernetes 1.34 以降でのインストール例です（要件と既存のインストール状況を先に確認してください）。
    ```bash
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.9.0/components.yaml
    ```
  - 使用例:
    ```bash
    kubectl top nodes
    kubectl top pods --all-namespaces
    ```

- **Headlamp（Kubernetes Dashboard はアーカイブ済み）:**
  - クラスターの状態とリソース使用量を視覚的に表示します
  - Pod、ノード、namespace などを管理するインターフェースを提供します

**2. 高度な監視スタック:**

- **Prometheus + Grafana:**
  - Prometheus: メトリクスの収集と保存
  - Grafana: メトリクスの可視化とダッシュボード
  - kube-prometheus-stack または Prometheus Operator を使ってインストールできます
  - カスタムのアラートルールとダッシュボードに対応します

- **ELK/EFK Stack:**
  - Elasticsearch: ログの保存と検索
  - Logstash/Fluentd: ログの収集と処理
  - Kibana: ログの可視化と分析

**3. リソース管理の手法:**

- **リソースの request と limit を設定する:**
  ```yaml
  resources:
    requests:
      memory: "64Mi"
      cpu: "250m"
    limits:
      memory: "128Mi"
      cpu: "500m"
  ```

- **namespace 単位のリソースクォータ（ResourceQuota）:**
  ```yaml
  apiVersion: v1
  kind: ResourceQuota
  metadata:
    name: compute-quota
    namespace: dev
  spec:
    hard:
      pods: "10"
      requests.cpu: "4"
      requests.memory: 8Gi
      limits.cpu: "8"
      limits.memory: 16Gi
  ```

- **既定のリソース制限（LimitRange）:**
  ```yaml
  apiVersion: v1
  kind: LimitRange
  metadata:
    name: default-limits
    namespace: dev
  spec:
    limits:
    - default:
        cpu: 500m
        memory: 512Mi
      defaultRequest:
        cpu: 200m
        memory: 256Mi
      type: Container
  ```

- **Horizontal Pod Autoscaler (HPA):**
  ```yaml
  apiVersion: autoscaling/v2
  kind: HorizontalPodAutoscaler
  metadata:
    name: web-app
  spec:
    scaleTargetRef:
      apiVersion: apps/v1
      kind: Deployment
      name: web-app
    minReplicas: 2
    maxReplicas: 10
    metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 80
  ```

- **Vertical Pod Autoscaler (VPA):**
  - Pod の CPU とメモリの request を自動調整します
  - リソース使用パターンに基づく推奨値を提示します

- **Cluster Autoscaler:**
  - ワークロードの要件に基づいてクラスターのノード数を自動調整します
  - リソースが不足したときにノードを追加し、使用率が低いときにノードを削除します

**4. 監視のベストプラクティス:**

- すべての Pod にリソースの request と limit を設定する
- 重要なメトリクスに対するアラートを設定する
- 過去の使用量分析に基づいてリソースを計画する
- 定期的にリソースを監査する
- コスト最適化のためにリソース使用量の傾向を分析する
- 開発、ステージング、本番環境に適切なリソースクォータを設定する
- ノード単位と Pod 単位の両方のメトリクスを監視する
</details>

4. Kubernetes クラスターのアップグレードで発生する主なリスクと、その軽減策を説明してください。

<details>
<summary>答えを表示</summary>

**答え:**

**Kubernetes クラスターのアップグレードに伴うリスクと軽減策:**

**1. 主なリスク:**

- **API の互換性の問題:**
  - 新しいバージョンで API が変更または削除されることがあります
  - 一部の Custom Resource Definition (CRD) や API バージョンがサポート対象外になることがあります

- **ワークロードの中断:**
  - コントロールプレーンコンポーネントの再起動中に、API server が一時的に利用できなくなることがあります
  - ノードのアップグレード中に Pod が再配置され、サービスが中断することがあります

- **機能の変更:**
  - デフォルトの動作が変わり、既存のワークロードに影響することがあります
  - セキュリティポリシーの変更により、権限上の問題が発生することがあります

- **パフォーマンスの問題:**
  - 新しいバージョンで必要なリソースが増えることがあります
  - アップグレード直後の安定化期間に、パフォーマンスが低下する可能性があります

- **ロールバックの複雑さ:**
  - 簡単にはロールバックできないアップグレードがあります
  - データ形式の変更により、ロールバックが制限されることがあります

**2. 軽減策:**

- **十分な計画と準備:**
  - **変更履歴を確認する:** 新しいバージョンの変更点、削除された機能、既知の問題を確認する
  - **アップグレード経路を確認する:** 現在のバージョンから対象バージョンへ直接アップグレードできることを確認する
  - **リソース要件を確認する:** 新しいバージョンの最低要件を確認する

- **テスト環境で事前に検証する:**
  - 本番環境に近いテストクラスターでアップグレードを実施する
  - 重要なワークロードとカスタムリソースをすべてテストする
  - 自動テストスイートを実行する

- **API の互換性を確認する:**
  - 現在提供されている API バージョンの一覧を確認する（クライアントが実際に使っている API の一覧とは異なります）:
    ```bash
    kubectl api-resources -o wide
    ```
  - `/metrics` へのアクセスが許可されている場合は、廃止予定 API のリクエスト状況を調べます。マニフェストとリクエストログも確認します:
    ```bash
    kubectl get --raw /metrics | grep '^apiserver_requested_deprecated_apis'
    ```
  - 必要に応じてマニフェストを更新する

- **バックアップと復旧計画:**
  - etcd データベースをバックアップする:
    ```bash
    ETCDCTL_API=3 etcdctl snapshot save snapshot.db \
      --endpoints=https://127.0.0.1:2379 \
      --cacert=/etc/kubernetes/pki/etcd/ca.crt \
      --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
      --key=/etc/kubernetes/pki/etcd/healthcheck-client.key
    ```
  - ワークロードオブジェクトの一部をエクスポートする（完全なバックアップではありません。出力を安全に保管してください）:
    ```bash
    umask 077
    kubectl get all --all-namespaces -o yaml > workload-subset.yaml
    ```
  - 復旧手順を文書化し、テストする

- **段階的にアップグレードする:**
  - **コントロールプレーンコンポーネントを先にアップグレードする:**
    - HA 構成では、コントロールプレーンノードを一度に 1 台ずつアップグレードする
  - **ワーカーノードをローリングアップグレードする:**
    - ノードグループを小さな単位に分けてアップグレードする
    - 各グループのアップグレード後に安定性を確認する

- **ワークロードを保護する:**
  - **PodDisruptionBudget を設定する:**
    ```yaml
    apiVersion: policy/v1
    kind: PodDisruptionBudget
    metadata:
      name: app-pdb
    spec:
      minAvailable: 2  # or maxUnavailable: 1
      selector:
        matchLabels:
          app: my-app
    ```
  - **ノードを drain するときは注意する:**
    ```bash
    kubectl drain <node_name> --ignore-daemonsets
    ```

- **監視を強化する:**
  - アップグレードの前・実施中・完了後にクラスターの状態を監視する
  - 主要なメトリクスとログを確認する
  - アラートのしきい値を一時的に調整する

- **ロールバック計画を立てる:**
  - ロールバックを開始する条件を定める
  - ロールバック手順を文書化する
  - ロールバックに必要なすべてのコンポーネントとイメージを保持する

- **連絡計画を立てる:**
  - アップグレードの予定と想定される影響を関係者全員に知らせる
  - アップグレード中に状況を共有する
  - 問題発生時のエスカレーション経路を定める

**3. バージョン固有の考慮事項:**

- **マイナーバージョンのアップグレード（例: 1.24 → 1.25）:**
  - 削除される API と機能変更に特に注意する
  - マイナーバージョンを一度に 1 つずつ上げる

- **パッチバージョンのアップグレード（例: 1.24.0 → 1.24.1）:**
  - 一般にリスクは低めですが、テストは必要です
  - セキュリティパッチは、より迅速な適用を検討します
</details>

5. Kubernetes クラスターでよく発生するネットワークの問題と、その診断方法および解決方法を説明してください。

<details>
<summary>答えを表示</summary>

**答え:**

**Kubernetes のネットワーク問題の診断と解決:**

**1. Pod 間の通信問題:**

- **症状:**
  - Pod が他の Pod と通信できない
  - Service 名で接続できない
  - ネットワークタイムアウトが発生する

- **診断方法:**
  - NetworkPolicy を確認する:
    ```bash
    kubectl get networkpolicy --all-namespaces
    ```
  - 接続テスト用の Pod を作成する:
    ```bash
    kubectl run -it --rm debug --image=busybox -- sh
    # Inside the pod
    ping <target_pod_IP>
    wget -O- <service_name>:<port>
    ```
  - CNI プラグインの Pod の状態を確認する:
    ```bash
    kubectl get pods -n kube-system | grep -E 'calico|flannel|weave|cilium'
    ```

- **解決方法:**
  - CNI プラグインを再インストールまたは更新する
  - NetworkPolicy を変更または削除する
  - ノードのネットワークインターフェースを確認する
  - ファイアウォールルールを確認する

**2. サービスディスカバリーと DNS の問題:**

- **症状:**
  - Service 名で接続できない
  - DNS 名前解決に失敗する
  - 接続が断続的に失敗する

- **診断方法:**
  - CoreDNS の Pod の状態を確認する:
    ```bash
    kubectl get pods -n kube-system -l k8s-app=kube-dns
    kubectl logs -n kube-system -l k8s-app=kube-dns
    ```
  - DNS 名前解決をテストする:
    ```bash
    kubectl run -it --rm debug --image=busybox -- sh
    # Inside the pod
    nslookup kubernetes.default.svc.cluster.local
    nslookup <service_name>.<namespace>.svc.cluster.local
    cat /etc/resolv.conf
    ```
  - Service のエンドポイントを確認する:
    ```bash
    kubectl get endpoints <service_name>
    ```

- **解決方法:**
  - CoreDNS の Pod を再起動する:
    ```bash
    kubectl rollout restart deployment coredns -n kube-system
    ```
  - DNS 設定を確認し、必要に応じて変更する:
    ```bash
    kubectl edit configmap coredns -n kube-system
    ```
  - kubelet の DNS 設定を確認する

**3. Service と Ingress の問題:**

- **症状:**
  - 外部から Service にアクセスできない
  - Ingress ルールが機能しない
  - ロードバランサーが作成されない

- **診断方法:**
  - Service の状態を確認する:
    ```bash
    kubectl describe service <service_name>
    ```
  - Ingress の状態を確認する:
    ```bash
    kubectl describe ingress <ingress_name>
    ```
  - Ingress コントローラーの Pod ログを確認する:
    ```bash
    kubectl logs -n <ingress_namespace> <ingress_controller_pod>
    ```
  - エンドポイントを確認する:
    ```bash
    kubectl get endpoints <service_name>
    ```

- **解決方法:**
  - Service の selector が Pod の label と一致していることを確認する
  - Ingress コントローラーを再インストールまたは更新する
  - Service の type と port の設定を確認する
  - クラウドプロバイダーのロードバランサー設定を確認する

**4. ノードのネットワーク問題:**

- **症状:**
  - ノードがクラスターから切断されている
  - ノード間通信に失敗する
  - kubelet への接続エラーが発生する

- **診断方法:**
  - ノードの状態を確認する:
    ```bash
    kubectl describe node <node_name>
    ```
  - ノードのネットワークインターフェースを確認する:
    ```bash
    # Directly on the node
    ip addr
    ip route
    ```
  - ファイアウォールルールを確認する:
    ```bash
    # Directly on the node
    iptables -L
    ```
  - kubelet のログを確認する:
    ```bash
    journalctl -u kubelet
    ```

- **解決方法:**
  - ノードのネットワークインターフェースを再設定する
  - ファイアウォールルールを変更する
  - kubelet を再起動する
  - 必要に応じてノードを再起動する

**5. NetworkPolicy の問題:**

- **症状:**
  - 想定外に接続が遮断される
  - 特定の namespace 間で通信できない
  - 一部の Pod にしかアクセスできない

- **診断方法:**
  - NetworkPolicy を確認する:
    ```bash
    kubectl get networkpolicy -A
    kubectl describe networkpolicy <policy_name> -n <namespace>
    ```
  - Pod の label を確認する:
    ```bash
    kubectl get pods --show-labels
    ```
  - ネットワークプラグインが NetworkPolicy に対応していることを確認する

- **解決方法:**
  - NetworkPolicy を変更または削除する
  - Pod の label を変更する
  - NetworkPolicy のデバッグツールを使用する

**6. 一般的なネットワークデバッグツール:**

- **ネットワークデバッグ用 Pod:**
  ```yaml
  apiVersion: v1
  kind: Pod
  metadata:
    name: network-debug
  spec:
    containers:
    - name: debug
      image: nicolaka/netshoot
      command: ["sleep", "3600"]
  ```

- **便利なコマンド:**
  ```bash
  # Inside the pod
  ping <IP>
  traceroute <IP>
  dig <service_name>.<namespace>.svc.cluster.local
  curl -v <URL>
  tcpdump -i any
  netstat -tuln
  ```

- **CNI プラグイン固有のデバッグツール:**
  - Calico: `calicoctl`
  - Cilium: `cilium`
  - Weave: `weave`

**7. ベストプラクティス:**

- ネットワークトポロジーを文書化する
- 接続テストを定期的に実施する
- NetworkPolicy を変更する前に影響を分析する
- クラスターネットワークの CIDR 範囲を計画する
- ネットワーク監視ツールを導入する
</details>
## ハンズオン問題

1. 次の要件を満たす ResourceQuota マニフェストを作成してください:
   - Namespace: `development`
   - Pod の上限: 20
   - CPU request の合計上限: 4 cores
   - メモリ request の合計上限: 8Gi
   - PVC の上限: 10
   - ストレージ request の合計上限: 100Gi

<details>
<summary>答えを表示</summary>

**答え:**

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: dev-quota
  namespace: development
spec:
  hard:
    pods: "20"
    requests.cpu: "4"
    requests.memory: 8Gi
    persistentvolumeclaims: "10"
    requests.storage: 100Gi
```

この ResourceQuota は `development` namespace に次の上限を設定します:
- Pod は最大 20 個
- CPU request の合計は 4 cores
- メモリ request の合計は 8Gi
- PersistentVolumeClaim は最大 10 個
- ストレージ request の合計は 100Gi

ResourceQuota を適用します:
```bash
kubectl apply -f resource-quota.yaml
```

現在の quota 使用量を確認します:
```bash
kubectl describe quota dev-quota -n development
```

注: ResourceQuota を適用する前に namespace が存在している必要があります。まだ作成されていない場合は、先に作成します:
```bash
kubectl create namespace development
```
</details>

2. SSH alias を使って各ノードに接続できるセルフマネージド Linux クラスターで、kubelet を確認し、明示的な修復モードを備えたスクリプトを作成してください。

<details>
<summary>答えを表示</summary>

**答え:**

```bash
#!/usr/bin/env bash
# check_kubelet.sh: self-managed Linux nodes with configured SSH aliases only.
set -euo pipefail
repair=${REPAIR_KUBELET:-0}
status=0
nodes=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')
for node in $nodes; do
  printf '%s: ' "$node"
  if state=$(ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" \
      'sudo -n systemctl is-active kubelet'); then
    printf 'kubelet %s\n' "$state"
    continue
  else
    rc=$?
  fi
  if [ "$rc" -ne 3 ]; then
    printf 'SSH/sudo/service query failed (exit %s); no repair attempted\n' "$rc" >&2
    status=1
    continue
  fi
  printf 'kubelet %s\n' "$state"
  if [ "$repair" != 1 ]; then
    printf 'Inspect logs and approve a repair before rerunning with REPAIR_KUBELET=1\n'
    status=1
    continue
  fi
  if ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" \
      'sudo -n systemctl start kubelet && sudo -n systemctl is-active --quiet kubelet' \
      && kubectl wait --for=condition=Ready "node/$node" --timeout=120s; then
    printf '%s: kubelet active and node Ready\n' "$node"
  else
    status=1
    ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" \
      'sudo -n journalctl -u kubelet --no-pager -n 50' || true
  fi
done
exit "$status"
```

このスクリプトは次の処理を行います:
1. `kubectl get nodes` でクラスター内の全ノードを取得します。
2. 各ノードについて:
   - サービスの状態を調べ、修復を要求した場合は修復後にノードが Ready になることを確認します。
   - SSH でノードに接続し、kubelet サービスの状態を確認します。
   - サービスが停止していることを確認できた場合に、`REPAIR_KUBELET=1` が指定されていれば kubelet を起動します。
   - 起動後にサービスの状態を再確認します。
   - 起動に失敗した場合はログを確認します。
   - SSH、sudo、状態照会の失敗と、kubelet の停止を区別し、修復後にノードの Ready 状態を確認します。

**使い方:**
```bash
chmod +x check_kubelet.sh
./check_kubelet.sh
# After diagnosing the inactive service and approving repair:
REPAIR_KUBELET=1 ./check_kubelet.sh
```

**注意:**
- このスクリプトの実行には、すべてのノードへの SSH 接続が必要です。
- 本番環境では SSH 公開鍵認証を推奨します。
- クラウド環境ではノードへの直接 SSH 接続が制限される場合があるため、クラウドプロバイダーのノード管理ツールが必要になることがあります。
</details>

3. クラスターの etcd データベースをバックアップし、ファイルを安全な場所に保存する cron job を設定してください。

<details>
<summary>答えを表示</summary>

**答え:**

**1. バックアップスクリプトを作成する:**

```bash
#!/usr/bin/env bash
# backup_etcd.sh: self-managed etcd; external storage must already be mounted.
set -euo pipefail
umask 077
BACKUP_DIR=${BACKUP_DIR:-/opt/etcd-backup}
REMOTE_ROOT=${REMOTE_ROOT:-/mnt/remote-storage}
REMOTE_DIR="$REMOTE_ROOT/etcd-backups"
METRICS_DIR=${METRICS_DIR:-/var/lib/node_exporter/textfile_collector}
RETENTION_DAYS=${RETENTION_DAYS:-7}
ETCD_ENDPOINT=${ETCD_ENDPOINT:-https://127.0.0.1:2379}
ETCD_CACERT=${ETCD_CACERT:-/etc/kubernetes/pki/etcd/ca.crt}
ETCD_CERT=${ETCD_CERT:-/etc/kubernetes/pki/etcd/healthcheck-client.crt}
ETCD_KEY=${ETCD_KEY:-/etc/kubernetes/pki/etcd/healthcheck-client.key}

publish_status() {
  rc=$?
  trap - EXIT
  if [ -d "$METRICS_DIR" ]; then
    tmp=$(mktemp "$METRICS_DIR/.etcd-backup.XXXXXX")
    success=0
    [ "$rc" -eq 0 ] && success=1
    printf 'etcd_backup_success %s\netcd_backup_last_attempt_timestamp_seconds %s\n' \
      "$success" "$(date +%s)" > "$tmp"
    chmod 0644 "$tmp"
    mv "$tmp" "$METRICS_DIR/etcd_backup_status.prom"
  fi
  exit "$rc"
}
trap publish_status EXIT
case "$RETENTION_DAYS" in ''|*[!0-9]*) echo 'Invalid retention' >&2; exit 1;; esac
mountpoint -q "$REMOTE_ROOT" || { echo 'Remote storage is not mounted' >&2; exit 1; }
mkdir -p "$BACKUP_DIR" "$REMOTE_DIR"
exec 9>"$BACKUP_DIR/.backup.lock"
flock -n 9 || { echo 'Another backup is running' >&2; exit 1; }
name="etcd-snapshot-$(date -u +%Y%m%d-%H%M%S).db"
ETCDCTL_API=3 etcdctl snapshot save "$BACKUP_DIR/$name" \
  --endpoints="$ETCD_ENDPOINT" --cacert="$ETCD_CACERT" \
  --cert="$ETCD_CERT" --key="$ETCD_KEY"
etcdutl snapshot status "$BACKUP_DIR/$name" --write-out=table
gzip "$BACKUP_DIR/$name"
cp "$BACKUP_DIR/$name.gz" "$REMOTE_DIR/.$name.gz.partial"
cmp "$BACKUP_DIR/$name.gz" "$REMOTE_DIR/.$name.gz.partial"
mv "$REMOTE_DIR/.$name.gz.partial" "$REMOTE_DIR/$name.gz"
# Retention runs only after snapshot validation and verified external copy.
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'etcd-snapshot-*.db.gz' \
  -mtime "+$RETENTION_DAYS" -delete
find "$REMOTE_DIR" -maxdepth 1 -type f -name 'etcd-snapshot-*.db.gz' \
  -mtime "+$RETENTION_DAYS" -delete
printf 'Verified backup copied to %s\n' "$REMOTE_DIR/$name.gz"
```

**2. スクリプトに実行権限を付与する:**

```bash
chmod +x /opt/etcd-backup/backup_etcd.sh
```

**3. cron job を設定する:**

```bash
# Edit root user's crontab
sudo crontab -e
```

次の設定を追加します:

```
# Run etcd backup daily at 2 AM
0 2 * * * /opt/etcd-backup/backup_etcd.sh >> /var/log/etcd-backup.log 2>&1
```

**4. バックアップログのローテーションを設定する:**

`/etc/logrotate.d/etcd-backup` ファイルを作成します:

```
/var/log/etcd-backup.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0600 root root
}
```

**5. バックアップをテストする:**

```bash
sudo /opt/etcd-backup/backup_etcd.sh
```

**6. バックアップを監視する（任意）:**

スクリプトの EXIT trap は、`METRICS_DIR` が存在する場合に、数値の `etcd_backup_success` と `etcd_backup_last_attempt_timestamp_seconds` メトリクスを出力します。node-exporter の textfile collector がこのディレクトリを読み取るよう設定し、書き込み権限を付与して、失敗または更新の途絶に対するアラートを設定してください。echo や copy コマンドの後に `$?` を確認する処理を追加してはいけません。外部ストレージは事前にマウントしておく必要があり、スナップショットの検証やコピーに失敗した場合、古いバックアップの削除処理は実行されません。

**注意:**
- バックアップファイルはクラスター外の安全な場所に保管してください。
- クラウド環境では、S3 や GCS などのオブジェクトストレージを利用できます。
- バックアップから復元できることを確認するため、定期的に復元テストを実施してください。
- HA etcd クラスターでは、バックアップは 1 つの etcd インスタンスで取得すれば十分です。
</details>
4. disruption budget を守り、ヘルスチェックに失敗したら停止する、対象を明示したセルフマネージド Linux ワーカーノードのメンテナンス手順を作成してください。

<details>
<summary>答えを表示</summary>

**答え:**

**ワーカーノードのローリングアップデート手順:**

```bash
#!/usr/bin/env bash
# node_rolling_update.sh: explicitly selected self-managed Linux workers only.
set -euo pipefail
: "${MAINTENANCE_COMMAND:?Set a reviewed node-maintenance command that does not reboot itself}"
: "${WORKLOAD_HEALTHCHECK:?Set a command that verifies critical workload health}"
[ "$#" -gt 0 ] || { echo 'Pass the worker node names as arguments' >&2; exit 1; }
trap 'echo "Stopped on error; inspect the node before manually uncordoning it" >&2' ERR
for node in "$@"; do
  kubectl get node "$node" -o json | jq -e '
    (.metadata.labels["kubernetes.io/os"] == "linux") and
    (.metadata.labels | has("node-role.kubernetes.io/control-plane") | not) and
    (.metadata.labels | has("node-role.kubernetes.io/master") | not)' >/dev/null
  ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" 'sudo -n true'
done
kubectl get poddisruptionbudgets -A
bash -c "$WORKLOAD_HEALTHCHECK"
for node in "$@"; do
  kubectl wait --for=condition=Ready "node/$node" --timeout=120s
  boot_before=$(kubectl get node "$node" -o jsonpath='{.status.nodeInfo.bootID}')
  kubectl cordon "$node"
  kubectl drain "$node" --ignore-daemonsets --timeout=10m
  ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" "$MAINTENANCE_COMMAND"
  reboot_required=$(ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" \
    'if [ -f /var/run/reboot-required ]; then echo yes; else echo no; fi')
  if [ "$reboot_required" = yes ]; then
    ssh -o BatchMode=yes -o ConnectTimeout=5 "$node" 'sudo -n reboot' || true
    deadline=$((SECONDS + 600))
    while :; do
      boot_after=$(kubectl get node "$node" -o jsonpath='{.status.nodeInfo.bootID}')
      [ -n "$boot_after" ] && [ "$boot_after" != "$boot_before" ] && break
      [ "$SECONDS" -lt "$deadline" ] || { echo 'New boot ID not reported' >&2; exit 1; }
      sleep 5
    done
  fi
  # Require a fresh kubelet lease renewal, not a stale pre-maintenance Ready flag.
  lease_before=$(kubectl -n kube-node-lease get lease "$node" -o jsonpath='{.spec.renewTime}')
  deadline=$((SECONDS + 120))
  while :; do
    lease_after=$(kubectl -n kube-node-lease get lease "$node" -o jsonpath='{.spec.renewTime}')
    [ -n "$lease_after" ] && [ "$lease_after" != "$lease_before" ] && break
    [ "$SECONDS" -lt "$deadline" ] || { echo 'No fresh kubelet lease' >&2; exit 1; }
    sleep 5
  done
  kubectl wait --for=condition=Ready "node/$node" --timeout=5m
  bash -c "$WORKLOAD_HEALTHCHECK"
  kubectl uncordon "$node"
  bash -c "$WORKLOAD_HEALTHCHECK"
done
```

この例では `kubectl`、`jq`、対象ノード用の SSH alias、パスワードなしで実行できる承認済みの `sudo`、レビュー済みのメンテナンスコマンドが必要です。Debian/Ubuntu の再起動要求マーカーを確認するため、他の OS ではこの部分を環境に合わせてください。`WORKLOAD_HEALTHCHECK` には重要なアプリケーションの健全性を実際に検証するコマンドを設定し、レビュー済みの worker node だけを引数に渡します。例:

```bash
MAINTENANCE_COMMAND='sudo -n /usr/local/sbin/approved-node-maintenance' \
WORKLOAD_HEALTHCHECK='kubectl -n app rollout status deployment/frontend --timeout=5m' \
./node_rolling_update.sh worker-1 worker-2
```

コマンドとアプリケーション名は、実際の環境とメンテナンス計画に合わせてください。この手順は force drain を使わず、emptyDir のデータ損失も許可しません。drain またはメンテナンスに失敗した場合は停止し、再起動後の boot ID の変化と新しい kubelet lease を待ちます。失敗したノードは cordon 状態のまま残します。PDB とヘルスチェックは計画された中断を抑えますが、無関係な障害時の可用性まで保証するものではありません。EKS managed node group と Auto Mode node にはプロバイダー管理の更新を使用し、コントロールプレーンノードには別途 kubeadm の手順を使ってください。

**ローリングアップデート前の準備:**

1. **PodDisruptionBudget を設定する:**
   可用性を維持できるよう、重要なワークロードに PDB を設定します。

   ```yaml
   apiVersion: policy/v1
   kind: PodDisruptionBudget
   metadata:
     name: app-pdb
     namespace: default
   spec:
     minAvailable: 2  # or maxUnavailable: 1
     selector:
       matchLabels:
         app: my-app
   ```

2. **十分なリソースを確保する:**
   1 台のノードを対象から外しても、残りのノードで全ワークロードを処理できることを確認します。

3. **バックアップを取得する:**
   アップデートの前に etcd データベースをバックアップします。

**ローリングアップデートのベストプラクティス:**

1. **段階的に進める:**
   - 一度に 1 台のノードだけを更新する
   - 各ノードの更新後にクラスターの状態を確認する

2. **自動化と冪等性:**
   - スクリプトで作業を自動化する
   - 失敗時にも安全に再試行できるよう設計する

3. **監視を強化する:**
   - 更新中にクラスターのメトリクスを監視する
   - アプリケーションの状態とパフォーマンスを監視する

4. **ロールバック計画を立てる:**
   - 問題に備えてロールバック手順を準備する
   - 以前の状態に戻す方法を用意する

5. **連絡する:**
   - 更新予定と想定される影響を関係者に知らせる
   - 作業の進捗を定期的に報告する

**注意:**
- クラウド環境では、マネージド Kubernetes サービス（EKS、GKE、AKS など）が提供するノード更新機能を利用できます。
- 複数のノードグループがある場合は、グループごとに更新します。
- 重要なシステム Pod（CoreDNS、kube-proxy など）の状態を特に注意して監視します。
</details>

5. クラスター内でリソース使用量の多い Pod を特定し、その情報をまとめたレポートを生成するスクリプトを作成してください。

<details>
<summary>答えを表示</summary>

**答え:**

```python
#!/usr/bin/env python3
# resource_usage_report.py: read-only Kubernetes API/metrics reporting.
import datetime
from decimal import Decimal
import html
import json
import os
from pathlib import Path
import re
import subprocess

SCALE = {"": Decimal(1), "n": Decimal("1e-9"), "u": Decimal("1e-6"),
         "m": Decimal("1e-3"), "k": Decimal(1000), "K": Decimal(1000)}
SCALE.update({s: Decimal(1000) ** n for n, s in enumerate("MGTPE", 2)})
SCALE.update({s + "i": Decimal(1024) ** n for n, s in enumerate("KMGTPE", 1)})

def quantity(value):
    text = str(value)
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([a-zA-Z]*)", text)
    if not match or match[2] not in SCALE:
        raise ValueError("Unsupported Kubernetes quantity: " + text)
    return Decimal(match[1]) * SCALE[match[2]]

def kubectl_json(*args):
    return json.loads(subprocess.check_output(["kubectl", *args], text=True))

def make_rows(pods, metrics):
    index = {(p["metadata"]["namespace"], p["metadata"]["name"]): p for p in pods}
    rows = []
    for metric in metrics:
        key = metric["metadata"]["namespace"], metric["metadata"]["name"]
        if key not in index:
            continue  # API snapshots are not atomic; the Pod may have disappeared.
        spec = index[key]["spec"]
        active = spec.get("containers", []) + [c for c in spec.get("initContainers", [])
                                               if c.get("restartPolicy") == "Always"]
        usage = {r: sum((quantity(c["usage"][r]) for c in metric["containers"]), Decimal(0))
                 for r in ("cpu", "memory")}
        requests = {}
        for resource in ("cpu", "memory"):
            pod_request = spec.get("resources", {}).get("requests", {}).get(resource)
            values = [c.get("resources", {}).get("requests", {}).get(resource) for c in active]
            requests[resource] = (quantity(pod_request) if pod_request is not None else
                                  sum((quantity(v) for v in values), Decimal(0))
                                  if all(v is not None for v in values) else None)
        rows.append((key, usage, requests))
    return rows

def render_report(rows):
    lines = ["Kubernetes resource usage report", "Generated: " + datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "Requests: active application/native-sidecar containers or Pod-level requests.",
             "This is not scheduler effective-request accounting for completed init stages/overhead."]
    totals = {}
    for key, usage, _ in rows:
        total = totals.setdefault(key[0], {"cpu": Decimal(0), "memory": Decimal(0)})
        for resource in total:
            total[resource] += usage[resource]
    for resource in ("cpu", "memory"):
        lines.append("\nTop 10 Pods by " + resource)
        for key, usage, requests in sorted(rows, key=lambda row: row[1][resource], reverse=True)[:10]:
            request = requests[resource]
            ratio = f"{usage[resource] / request * 100:.1f}%" if request else "request missing/zero"
            lines.append(f"{key[0]}/{key[1]}: usage={usage[resource]}, request={request}, ratio={ratio}")
    lines.append("\nNamespace totals (CPU cores, memory GiB)")
    for namespace, total in sorted(totals.items()):
        lines.append(f"{namespace}: {total['cpu']:.3f}, {total['memory'] / (1024 ** 3):.3f}")
    lines.append("\nPods above 80% of known requests or with missing requests")
    for key, usage, requests in rows:
        if any(not requests[r] or usage[r] / requests[r] >= Decimal('0.8') for r in requests):
            lines.append(f"{key[0]}/{key[1]}: usage={usage}; requests={requests}")
    return "\n".join(lines)

def main():
    os.umask(0o077)
    group = kubectl_json("get", "--raw", "/apis/metrics.k8s.io")
    version = group["preferredVersion"]["version"]
    pod_metrics = kubectl_json("get", "--raw", f"/apis/metrics.k8s.io/{version}/pods")["items"]
    pods = kubectl_json("get", "pods", "-A", "-o", "json")["items"]
    rows = make_rows(pods, pod_metrics)
    report = render_report(rows)
    nodes = subprocess.check_output(["kubectl", "top", "nodes"], text=True)
    report += "\n\nNode resource usage\n" + nodes
    node_count = len(kubectl_json("get", "nodes", "-o", "json")["items"])
    namespace_count = len(kubectl_json("get", "namespaces", "-o", "json")["items"])
    context = subprocess.check_output(["kubectl", "config", "current-context"], text=True).strip()
    report += f"\nContext: {context}; nodes: {node_count}; namespaces: {namespace_count}\n"
    report += f"Inventory Pods: {len(pods)}; Pods with matched metrics: {len(rows)}\n"
    directory = Path(os.environ.get("REPORT_DIR", "/tmp/k8s-reports"))
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    stem = "resource-usage-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    text_path = directory / (stem + ".txt")
    text_path.write_text(report, encoding="utf-8")
    (directory / (stem + ".html")).write_text(
        '<!doctype html><meta charset="utf-8"><title>Kubernetes resource report</title><pre>'
        + html.escape(report) + '</pre>', encoding="utf-8")
    print(text_path)

if __name__ == "__main__":
    main()
```

**スクリプトの使い方:**
```bash
python3 resource_usage_report.py
```

**スクリプトの機能:**
1. クラスター情報を収集する
2. ノードのリソース使用量を収集する
3. CPU とメモリの使用量が多い Pod を特定する
4. namespace ごとのリソース使用量を計算する
5. request に対して使用量の多い Pod を特定する
6. リソース request が設定されていない Pod を特定する
7. テキスト形式と HTML 形式のレポートを生成する

**注意:**
- Python 3 と、Pod API および metrics API を読み取れる権限を持つ `kubectl` が必要です。スクリプトは提供中の metrics API バージョンを検出し、namespace ごとに複数コンテナの使用量を集計し、リソース量の単位を処理して、HTML 出力をエスケープします。
- クラスターに Metrics Server がインストールされている必要があります。
- 大規模クラスターでは、スクリプトの実行に時間がかかることがあります。
- 定期的なレポート生成には cron job として設定できます。
- レポートはメールで送信したり、監視システムと連携したりできます。
</details>
## 高度なトピック

1. 実在する etcd 設定または運用方法を含む組み合わせを 2 つ選んでください。
   - A) `--max-request-bytes`、`--quota-backend-bytes`、定期的な compaction
   - B) `--max-concurrent-requests`、`--max-connections`、ディスク RAID の構成
   - C) `--auto-compaction-retention`、`--snapshot-count`、SSD ストレージ
   - D) `--max-txn-ops`、`--max-result-buffer`、メモリの増設

<details>
<summary>答えを表示</summary>

**答え: A と C**

**解説:**
etcd は Kubernetes クラスターの中核となるデータストアであり、その性能はクラスター全体に影響します。性能を高める設定と運用方法には、次のものがあります。

1. **`--auto-compaction-retention`**: etcd は変更履歴を保持する append-only store です。この設定は、キーの古いバージョンを自動 compact する保持期間を指定します。デフォルトは 0（無効）ですが、本番環境では通常 1 hour（1h）または 24 hours（24h）に設定します。これにより、ディスク容量を節約し、性能を高められます。

2. **`--snapshot-count`**: etcd が snapshot を作成するまでに commit する transaction 数を指定します。これは内部の Raft snapshot を制御する設定で、持ち運び可能なバックアップ用 snapshot とは異なります。デフォルト値はバージョンによって異なり、v3.6 のリファレンスでは 10,000 です。調整する前に、使用中のバージョンを確認して実測してください。

3. **SSD ストレージ**: etcd はディスク I/O の影響を受けやすいため、SSD を使うと性能が大幅に向上します。大規模クラスターでは SSD の使用が欠かせません。

そのほかの重要な設定と運用方法:

- **専用ディスクを使う**: 他のアプリケーションとの I/O 競合を防ぐため、etcd データ用に専用ディスクを使用します。
- **十分なメモリを割り当てる**: etcd は性能向上のためにデータをメモリへ cache するので、十分な容量を確保します。
- **クラスター規模を適切にする**: 通常、etcd member を 3～5 台にすると、性能と可用性のバランスが取れます。
- **ネットワーク遅延と障害分離の両方を考慮する**: 全 member を 1 つの zone に置くと、その zone の障害で quorum を失います。
- **定期的にバックアップと compaction を行う**: データを保護し、ディスク容量を効率的に使います。

`--max-request-bytes`、`--quota-backend-bytes`、`--max-txn-ops` は実在する設定です。D の `--max-result-buffer` は有効な設定ではありません。リソース制限や内部 snapshot を、バックアップ戦略と混同しないでください。
</details>

2. Kubernetes クラスターでコントロールプレーンの高可用性（HA）を実現する効果的な方法は何ですか？
   - A) 1 台の master node 上で複数の API server instance を実行する
   - B) 複数の master node と load balancer を備えた etcd cluster を構成する
   - C) API server を PersistentVolume を使う StatefulSet としてデプロイする
   - D) master node 上で自動復旧する watchdog process を実装する

<details>
<summary>答えを表示</summary>

**答え: B) 複数の master node と load balancer を備えた etcd cluster を構成する**

**解説:**
Kubernetes コントロールプレーンの高可用性（HA）を実現する効果的な方法は、複数の master node と load balancer を備えた etcd cluster を構成することです。この構成は次の要素で成り立ちます。

1. **複数の master node**: 単一障害点をなくすため、通常は異なる availability zone に 3 台または 5 台を配置します。各 node は次のコントロールプレーンコンポーネントを実行します。
   - kube-apiserver: API request を処理する server
   - kube-controller-manager: controller process を実行する
   - kube-scheduler: Pod の配置先を決める

2. **etcd cluster**: etcd は Kubernetes クラスターのデータをすべて保存する分散 key-value store です。高可用性のため、通常は 3 台または 5 台の etcd instance を実行します。etcd は master node 上にも、専用 node 上にも配置できます。

3. **Load balancer**: client request を複数の kube-apiserver instance に分散するために必要です。通常は cloud provider の load balancer service、または HAProxy や Nginx などの software load balancer を使います。

この構成には次の利点があります。
- **耐障害性**: 1 台の master node が故障してもクラスターは動作を続けます。
- **高可用性**: 複数の availability zone に配置すれば、データセンターレベルの障害にも対応できます。
- **拡張性**: API server request を複数 instance に分散して処理できます。
- **データの一貫性**: etcd の Raft consensus algorithm がデータの一貫性を保ちます。

他の選択肢には次の問題があります。
- 1 台の master node 上で API server instance を複数実行しても、その node 自体が単一障害点として残ります。
- API server を StatefulSet としてデプロイする方法は一般的ではありません。コントロールプレーンコンポーネントは通常 Kubernetes の外部で管理します。
- watchdog process は役立つ場合がありますが、それだけでは高可用性を実現できません。
</details>

3. Kubernetes audit logging で、記録する event と詳細度を選択する仕組みは何ですか？
   - A) 完全な監査記録を残すため、すべての API request と response body を記録する
   - B) audit policy を使って、記録する event と詳細度を選択する
   - C) audit log を外部 SIEM system にリアルタイムで送信する
   - D) audit log へのアクセスを administrator のみに制限する

<details>
<summary>答えを表示</summary>

**答え: B) audit policy を使って、記録する event と詳細度を選択する**

**解説:**
audit policy は、記録する event とその詳細度を選択します。metadata を記録する包括的なルールを設定すれば、機密性の高い payload を除外しながら、広範な監査記録を残せます。保持期間、アクセス制御、ログの配信方法も重要です。

1. **性能への影響を抑える**: すべての API request を記録すると、API server に大きな負荷がかかり、性能が低下することがあります。必要な監査記録と測定した負荷に基づいて詳細度を選びます。すべての request を metadata レベルで記録する方法は、サポートされている基本設定です。

2. **ストレージを効率よく使う**: すべての event を詳細に記録するとログが急速に増え、ストレージコストと分析の負担が大きくなります。

3. **必要な情報を把握しやすくする**: 重要な event を記録すれば、security analyst が調査に必要な情報を見つけやすくなります。

4. **コンプライアンスに対応する**: 対象システムに適用される要件に合わせて、event の範囲、保持期間、アクセス制御を定めます。

Kubernetes audit policy では、次の audit level を指定できます。

- **None**: event を log に記録しません。
- **Metadata**: request metadata（user、timestamp、resource、action など）のみを log に記録し、request/response body は除外します。
- **Request**: metadata と request body を log に記録しますが、response body は除外します。
- **RequestResponse**: metadata、request body、response body を log に記録します。

効果的な audit policy の例:
```yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
- level: Metadata
  resources:
  - group: ""
    resources: ["secrets", "configmaps", "serviceaccounts/token"]
  - group: authentication.k8s.io
    resources: ["tokenreviews"]
- level: Metadata
```

他の選択肢には次の問題があります。
- すべての API request を詳細に記録すると、性能とストレージに問題が生じることがあります。
- 外部 SIEM system へのリアルタイム送信も重要ですが、まず記録する内容を決める必要があります。
- audit log へのアクセス制限は重要なセキュリティ対策ですが、何を記録するかを定める policy とは別のものです。
</details>

4. セルフマネージド環境で、専用の node problem detector と独自の修復ロジックを組み合わせる構成はどれですか？
   - A) node status を監視し、問題のある node を自動再起動する DaemonSet をデプロイする
   - B) cloud provider の managed node group と auto-repair 機能を利用する
   - C) Node Problem Detector と独自 controller で node status を監視し、復旧する
   - D) node status を定期確認し、問題のある node を再作成する cron job を実装する

<details>
<summary>答えを表示</summary>

**答え: C) Node Problem Detector と独自 controller で node status を監視し、復旧する**

**解説:**
Node Problem Detector と独自の修復処理を組み合わせる方法は、拡張性の高い設計の 1 つです。常に最善とは限りません。EKS を含む provider-managed repair が利用できる場合は、運用負荷を減らせます。

1. **問題を正確に検出する**: Node Problem Detector (NPD) は、次のようなさまざまな node problem を検出する専用ツールです。
   - Kernel error と crash
   - Hardware issue
   - File system issue
   - Network issue
   - Resource shortage issue

2. **柔軟に対応する**: 独自 controller を使うと、検出した問題に応じて異なる復旧方法を実装できます。
   - 軽微な問題: node を再起動する
   - 深刻な問題: node を置き換える
   - 特定の種類の問題: 該当サービスを再起動する

3. **Kubernetes と統合できる**: NPD は node status を NodeCondition として報告し、既存の Kubernetes の仕組みと連携します。

4. **実行環境に合わせる**: 検出と修復の方法は OS、runtime、provider に適合させる必要があります。node の障害で node 上の agent 自身が報告できない場合に備え、外部の signal や controller も必要です。

実装手順:

1. **Node Problem Detector をデプロイする**:
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/node-problem-detector/master/deployment/node-problem-detector.yaml
   ```

2. **独自 controller を実装する**:
   - Kubernetes event と node status の変化を監視する
   - 特定の NodeCondition に対応するロジックを実装する
   - 復旧処理（SSH 経由のコマンド実行、cloud API 経由の node 再作成など）を行う

3. **アラートとログを設定する**:
   - 復旧処理に対するアラートを設定する
   - 問題と復旧処理をログに記録する

他の選択肢には次の問題があります。

- **DaemonSet を使う方法**: node に深刻な問題があると DaemonSet 自体も影響を受ける可能性があり、あらゆる種類の問題を検出するのは困難です。

- **cloud provider の managed node group**: 特定の provider に依存するため、オンプレミス環境では使えません。また、検出できる問題の種類が限られる場合があります。

- **cron job を使う方法**: 反応が遅く、問題を検出する能力も限られます。また、クラスター外で実行する必要があります。

Node Problem Detector と独自 controller の組み合わせは、環境に応じた柔軟な node auto-repair の実装に役立ちます。
</details>

5. Kubernetes クラスターで RBAC (Role-Based Access Control) を適切に管理する方法はどれですか？
   - A) 管理を簡単にするため、すべての user に cluster-admin role を付与する
   - B) namespace ごとに詳細な role を定義し、最小権限の原則を適用する
   - C) 一貫性を保つため、すべての権限を 1 つの ClusterRole にまとめる
   - D) 認証には常に service account ではなく user certificate を使う

<details>
<summary>答えを表示</summary>

**答え: B) namespace ごとに詳細な role を定義し、最小権限の原則を適用する**

**解説:**
Kubernetes クラスターで RBAC (Role-Based Access Control) を適切に管理するには、namespace ごとに必要な権限を定義し、最小権限の原則を適用します。この方法には次の利点があります。

1. **最小権限の原則**: user と service account には必要な最小限の権限だけを付与し、セキュリティリスクを抑えます。意図しない変更や悪意ある操作からクラスターを守れます。

2. **namespace による分離**: namespace ごとに role を定義すると、team や application 間を論理的に分離できます。これは通常の API 操作の範囲を制限しますが、ワークロードの admission 制御やネットワーク制御も必要です。

3. **詳細なアクセス制御**: resource type や action ごとに権限を細かく設定できます。たとえば、developer に Pod と Service の管理を許可しながら、Secret や namespace 自体を変更する権限を制限できます。

4. **監査しやすい**: 詳細な role を使うと、誰がどの操作を実行できるかが明確になり、監査やコンプライアンス対応が容易になります。

RBAC のベストプラクティスの例:

1. **namespace ごとに role を定義する**:
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     name: developer
     namespace: development
   rules:
   - apiGroups: [""]
     resources: ["pods", "services", "configmaps"]
     verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
   - apiGroups: ["apps"]
     resources: ["deployments", "replicasets"]
     verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
   ```

Pod や Deployment の作成権限は、その namespace 内の Secret や ServiceAccount の権限を間接的に利用できる可能性があります。Secret の直接読み取りを許可しないだけでは、ワークロードがどの資格情報を mount できるかまでは制限できません。適切な admission control も使ってください。

2. **RoleBinding を作成する**:
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: RoleBinding
   metadata:
     name: developer-binding
     namespace: development
   subjects:
   - kind: Group
     name: developers
     apiGroup: rbac.authorization.k8s.io
   roleRef:
     kind: Role
     name: developer
     apiGroup: rbac.authorization.k8s.io
   ```

3. **cluster-level role は必要な場合に限って使う**:
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: ClusterRole
   metadata:
     name: pod-reader
   rules:
   - apiGroups: [""]
     resources: ["pods"]
     verbs: ["get", "list", "watch"]
   ```

4. **service account に細かな権限を設定する**:
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     name: app-role
     namespace: production
   rules:
   - apiGroups: [""]
     resources: ["configmaps"]
     resourceNames: ["app-config"]  # Only access to specific ConfigMap
     verbs: ["get"]
   ```

他の選択肢には次の問題があります。

- **すべての user に cluster-admin role を付与する**: 重大なセキュリティリスクになります。すべての user がクラスター内の全 resource にアクセスでき、意図しない変更や悪意ある操作に弱くなります。

- **すべての権限を 1 つの ClusterRole にまとめる**: 過剰な権限を共有するリスクがあります。一方、範囲を絞った再利用可能な ClusterRole を作り、namespace 単位の RoleBinding で割り当てる方法は適切な場合があります。

- **常に user certificate を使う**: service account は application の認証に適しています。すべての場面で user certificate を使うと管理負担が増えるため、状況に応じて認証方式を選んでください。
</details>

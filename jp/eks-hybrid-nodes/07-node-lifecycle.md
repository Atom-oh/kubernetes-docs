# ノードのライフサイクル管理

< [前へ: ワークロード配置戦略](./06-workload-placement.md) | [目次](./README.md) | [次へ: 運用とメンテナンス](./08-operations.md) >

> **サポート対象**: AWS がサポートする Kubernetes バージョンの EKS Hybrid Nodes。nodeadm 1.0.20を参照（SSMでのインストール/アップグレードには1.0.19以降が必要）
> **最終更新**: 2026年9月13日

このドキュメントでは、EKS Hybrid Nodes の高度な nodeadm 設定、フリート全体へのインストール自動化、アップグレード戦略、認証情報のライフサイクル管理、ヘルス監視を説明します。

## 1. 高度な NodeConfig

### kubelet のチューニング

本番環境では、kubelet のリソース予約、eviction しきい値、イメージのガベージコレクション、シャットダウン動作を適切に調整する必要があります。

#### リソース予約（system-reserved / kube-reserved）

これらの設定は、Node Allocatable の計算時に予約分を差し引きます。すべてのホストプロセスに適用される一律のハード上限ではありません。既定の enforceNodeAllocatable が対象にするのは Pod です。system/kube の予約も強制するには、専用 cgroup とレビュー済みの cgroup 階層が正しく設定されている必要があります。値を決める前に、OS、kubelet、コンテナランタイム、CNI/ドライバーのオーバーヘッドを測定してください。

```yaml
kubelet:
  config:
    systemReserved:
      cpu: "500m"
      memory: "1Gi"
      ephemeral-storage: "10Gi"
    kubeReserved:
      cpu: "500m"
      memory: "1Gi"
      ephemeral-storage: "5Gi"
```

| パラメーター | 説明 | 初期計画の例。使用前に測定すること |
|---|---|---|
| `systemReserved.cpu` | OS とシステムデーモン用 CPU | 500m～1000m |
| `systemReserved.memory` | OS とシステムデーモン用メモリー | 1Gi～2Gi |
| `kubeReserved.cpu` | kubelet と containerd 用 CPU | 500m～1000m |
| `kubeReserved.memory` | kubelet と containerd 用メモリー | 1Gi～2Gi |

#### Eviction しきい値

kubelet はノード単位のリソース回収を試み、必要ならリソース圧迫時に Pod を eviction します。これは安定性の保証ではありません。また、ノード圧迫による eviction は、API の eviction 要求のように PodDisruptionBudget を尊重しません。

```yaml
kubelet:
  config:
    evictionHard:
      memory.available: 200Mi
      nodefs.available: 10%
      imagefs.available: 15%
      nodefs.inodesFree: 5%
      imagefs.inodesFree: 5%
    evictionSoft:
      memory.available: 500Mi
      nodefs.available: 15%
    evictionSoftGracePeriod:
      memory.available: 1m30s
      nodefs.available: 2m
    evictionMaxPodGracePeriod: 60
```

> **注意**: hard しきい値には設定可能な soft 観測期間がなく、即時終了に使われます。soft しきい値は evictionSoftGracePeriod の間継続した場合に適用され、Pod の終了猶予は別途 evictionMaxPodGracePeriod で上限を設定します。soft しきい値があっても、その後の hard eviction や OOM は防げません。evictionHard をカスタマイズするときは、inode しきい値を含む意図したしきい値マップ全体を指定してください。サポートされた既定値マージ動作を明示的に有効にしない限り、省略した既定値はゼロになります。

#### maxPods の計算

CPU、メモリー、デーモンのオーバーヘッド、Cilium のノードごとの IP pool を考慮して maxPods を決めます。Cilium の cluster-pool は CIDR あたり IPv4 アドレスを2つ予約します。そのため /25、/24、/26 で利用できるアドレスは、それぞれ126、254、62です。以下の値は計画用の例であり、検証済みのフリート推奨値でも ENI から算出した上限でもありません。既存の clusterPoolIPv4MaskSize を後から変更して割り当て済みブロックを拡張することはできません。

```yaml
kubelet:
  config:
    maxPods: 110  # /25 has 126 usable IPv4 addresses; leave capacity for overhead
```

| マスクサイズ | IPv4 アドレス総数 | maxPods の例 |
|---|---:|---:|
| /25 | 128 | 110 |
| /24 | 256 | 240 |
| /26 | 64 | 50 |

#### イメージのガベージコレクション

未使用イメージを自動的に削除し、ディスク容量を管理します。

```yaml
kubelet:
  config:
    imageGCHighThresholdPercent: 85
    imageGCLowThresholdPercent: 80
    imageMinimumGCAge: "2m"
```

#### シャットダウン猶予期間

サポート対象の Linux ホストで正常なノードシャットダウンを行うには、systemd inhibitor lock と kubelet の設定を使います。電源喪失や強制シャットダウン時の正常終了は保証できません。

```yaml
kubelet:
  config:
    shutdownGracePeriod: 60s
    shutdownGracePeriodCriticalPods: 20s
```

> **注意**: この2グループ構成では、合計60秒の猶予のうち20秒を重要 Pod に使い、残りの Pod には40秒の枠を割り当てます。各 Pod が常に40秒を得られるという約束ではありません。各 Pod の terminationGracePeriodSeconds と実際のシャットダウン状況も適用されます。

### containerd の高度な設定

#### プライベートレジストリミラーの設定

次の断片は containerd 1.x（config version 2）を使います。containerd 2.x では config version 3 と registry plugin path io.containerd.cri.v1.images.registry を使ってください。ランタイムを再起動する前に、インストール済みバージョンとマージ後の実効設定を確認します。レジストリの信頼設定とミラーのパス対応も検証し、TLS 検証を無効にしないでください。

信頼できるプライベートレジストリをミラーとして使います。下の server entry はフォールバックとして upstream endpoint を維持するため、air-gap 構成ではありません。ミラーに依存する前に、認証、proxy project path、CA の信頼を確認してください。

```yaml
containerd:
  config: |
    version = 2

    [plugins."io.containerd.grpc.v1.cri".registry]
      config_path = "/etc/containerd/certs.d"
```

`hosts.toml` ファイルを使ってレジストリごとにミラーを設定します。

```bash
# /etc/containerd/certs.d/docker.io/hosts.toml
sudo mkdir -p /etc/containerd/certs.d/docker.io
cat <<EOF | sudo tee /etc/containerd/certs.d/docker.io/hosts.toml
server = "https://registry-1.docker.io"

[host."https://harbor.internal.company.io/v2/dockerhub-proxy"]
  capabilities = ["pull", "resolve"]
  ca = "/usr/local/share/ca-certificates/registry-ca.crt"
  override_path = true
EOF
```

#### GPU ノード用 NVIDIA RuntimeClass

この containerd 1.x の断片は、専用 GPU ノードに NVIDIA runtime binary/toolkit と互換ドライバーがすでにインストール済みであることを前提とします。ここで設定するのは handler であり、GPU スタックをインストールするものではありません。必要な場合に実際の RuntimeClass/ワークロード設定で選択してください。containerd 2.x では config version 3 と io.containerd.cri.v1.runtime plugin path を使い、2つの形式を混在させないでください。device-plugin/DRA と toolkit の前提条件も確認してください。

```yaml
containerd:
  config: |
    version = 2

    [plugins."io.containerd.grpc.v1.cri".containerd]

    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia]
      privileged_without_host_devices = false
      runtime_type = "io.containerd.runc.v2"

    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia.options]
      BinaryName = "/usr/bin/nvidia-container-runtime"
      SystemdCgroup = true
```

### ラベルと taint の戦略

#### nodeadm が自動設定するラベル

nodeadm は Hybrid Node の初期化時に次のラベルを自動付与します。

```
eks.amazonaws.com/compute-type=hybrid
```

このラベルを `--node-labels` に手動で追加する必要はありません。

#### カスタムラベルの戦略

ワークロード配置を細かく制御できるよう、目的や環境に応じてラベルを追加します。

```yaml
kubelet:
  flags:
    # Purpose-based labels
    - --node-labels=node.kubernetes.io/instance-type=on-prem-gpu,workload-type=ml-training

    # Environment-based labels (production)
    # - --node-labels=environment=production,tier=compute

    # Datacenter location labels
    # - --node-labels=datacenter=dc-seoul-01,rack=rack-a3
```

#### Taint の戦略

| 戦略 | 説明 | 用途 |
|---|---|---|
| 自動 taint（NodeConfig） | 初回 Node 登録時に適用。既存 Node の taint は明示的に調整する | 全 Hybrid Node 共通の taint |
| 手動 taint（kubectl） | 運用時に動的に適用する | GPU ノードの分離、メンテナンスモード |

```yaml
# Automatic taints in NodeConfig
kubelet:
  flags:
    - --register-with-taints=eks.amazonaws.com/compute-type=hybrid:NoSchedule
```

```bash
# Manual taint addition during operations
kubectl taint nodes hybrid-gpu-001 gpu=true:NoSchedule
kubectl taint nodes hybrid-node-005 maintenance=true:NoSchedule
```

<a id="full-production-nodeconfig-example"></a>

### NodeConfig 全体のレビュー用テンプレート

これは未実行の設定テンプレートであり、本番対応の主張ではありません。前述の kubelet/containerd 断片は spec の下に入れます。クラスター名と Region は対象クラスターを示す必要があり、nodeadm は許可された検出経路からクラスターのメタデータを取得します。実際の有効化値は、承認済みの非公開 NodeConfig ファイルを通じてのみ渡してください。実ホストに合わせて containerd の構文とすべてのリソース値を選択します。

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: prod-hybrid-cluster
    region: ap-northeast-2
  hybrid:
    ssm:
      activationCode: <activation-code>
      activationId: <activation-id>
  kubelet:
    config:
      maxPods: 110
      shutdownGracePeriod: 60s
      shutdownGracePeriodCriticalPods: 20s
      systemReserved:
        cpu: 500m
        memory: 1Gi
        ephemeral-storage: 10Gi
      kubeReserved:
        cpu: 500m
        memory: 1Gi
        ephemeral-storage: 5Gi
      evictionHard:
        memory.available: 200Mi
        nodefs.available: 10%
        imagefs.available: 15%
        nodefs.inodesFree: 5%
        imagefs.inodesFree: 5%
      evictionSoft:
        memory.available: 500Mi
        nodefs.available: 15%
      evictionSoftGracePeriod:
        memory.available: 1m30s
        nodefs.available: 2m
      imageGCHighThresholdPercent: 85
      imageGCLowThresholdPercent: 80
      evictionMaxPodGracePeriod: 60
    flags:
    - --node-labels=node.kubernetes.io/instance-type=on-prem-gpu,workload-type=ml-training
    - --register-with-taints=eks.amazonaws.com/compute-type=hybrid:NoSchedule
  containerd:
    config: "version = 2\n[plugins.\"io.containerd.grpc.v1.cri\".registry]\n  config_path\
      \ = \"/etc/containerd/certs.d\"\n"
```

---

## 2. フリートインストールの自動化

### Ansible Playbook

管理された inventory と小さな wave を使って、[ブートストラップ手順](./04-node-bootstrap.md)を実行します。ホストのアーキテクチャごとに Hybrid Nodes の nodeadm artifact を固定して検証してください。すべてのホストに amd64 バイナリを配布したり、wave の実行中に未レビューの `latest` バイナリを再取得したりしないでください。SSM でインストール/アップグレードする場合、古いリリースに古い installer signing key が含まれるため、AWS は nodeadm **1.0.19以降**を要求します。この章では1.0.20を参照します。実行前に、承認済みの OS、Kubernetes、CNI、CSI、ランタイムの組み合わせを確認してください。

#### Inventory の設定

以下のアドレスはドキュメント用のプレースホルダーです。実際のホスト接続先は、Kubernetes Node 名と UID とは別に記録します。特に SSM 経由の Node 名は、SSH で名前解決できるホスト名とは限りません。

```ini
[hybrid_nodes:children]
gpu_nodes
cpu_nodes

[gpu_nodes]
gpu-host-a ansible_host=192.0.2.10 kubernetes_node_name=REPLACE_WITH_REGISTERED_NODE_NAME

[cpu_nodes]
cpu-host-a ansible_host=192.0.2.20 kubernetes_node_name=REPLACE_WITH_REGISTERED_NODE_NAME

[hybrid_nodes:vars]
ansible_user=REPLACE_WITH_APPROVED_OPERATOR
```

#### Automation Playbook

この playbook は**事前インストール済みホストの preflight**であり、完全な installer ではありません。先に承認済みの secret-file 手順で root 所有の非公開 NodeConfig を渡してください。有効化コード/秘密鍵を通常の inventory/group variable やログに出る template 出力に含めてはいけません。両方の digest placeholder は、選択したリリース用に独立検証した artifact へ置き換えます。install/init を実行したり、停止中の service を開始したうえで health check 済みと報告したりはしません。

```yaml
- name: Review preinstalled Hybrid Nodes before an approved bootstrap
  hosts: hybrid_nodes
  gather_facts: true
  become: true
  serial: 1
  any_errors_fatal: true
  vars:
    architecture_map:
      x86_64: amd64
      aarch64: arm64
    approved_nodeadm_sha256:
      amd64: REPLACE_WITH_REVIEWED_AMD64_SHA256
      arm64: REPLACE_WITH_REVIEWED_ARM64_SHA256
    nodeconfig_path: /etc/eks/nodeconfig.yaml
  tasks:
  - name: Require a reviewed architecture and binary digest
    ansible.builtin.assert:
      that:
      - ansible_facts.architecture in architecture_map
      - approved_nodeadm_sha256[architecture_map[ansible_facts.architecture]] is match('^[a-f0-9]{64}$')
  - name: Inspect the existing nodeadm artifact
    ansible.builtin.stat:
      path: /usr/local/bin/nodeadm
      checksum_algorithm: sha256
      get_checksum: true
    register: nodeadm_artifact
  - name: Match the approved artifact
    ansible.builtin.assert:
      that:
      - nodeadm_artifact.stat.exists
      - nodeadm_artifact.stat.executable
      - nodeadm_artifact.stat.checksum == approved_nodeadm_sha256[architecture_map[ansible_facts.architecture]]
  - name: Validate the privately delivered NodeConfig
    ansible.builtin.command:
      argv:
      - /usr/local/bin/nodeadm
      - config
      - check
      - -c
      - file://{{ nodeconfig_path }}
    changed_when: false
    no_log: true
```

kubelet のファイルがあるだけでは、インストール完了の証拠になりません。preflight 後は、ホストごとの作業記録と ID 確認を含む、ブートストラップ章の install/init 手順全体を実行してください。失敗時には wave を止め、init を盲目的に再実行せず、状態不明/部分完了として復旧します。`changed_when: false` が制御するのは Ansible の報告であり、実行するコマンドの動作ではありません。

#### GPU ノードと CPU ノードのロール別変数

| ホストグループ | ホストごとに明示してレビューする設定 |
|---|---|
| CPU | 選択した OS/アーキテクチャ、ランタイム形式、測定済み予約、ワークロードラベルと taint |
| GPU | CPU の前提条件に加え、実ドライバー/toolkit、選択した device-plugin または DRA、runtime handler/RuntimeClass、GPU 検証 |

各ホストにはテンプレートを明示的に選びます。`group_names[0]` は信頼できるロール判定方法ではありません。`nvidia.com/gpu.present=true` と宣言しても、ドライバーがインストールされたり allocatable GPU が成立したりするわけではありません。[GPU 統合](./05-gpu-integration.md)を参照してください。

### フリート検証スクリプト

クラスター内で**すべての Hybrid Node**を含む、個別に承認された expected-nodes.json を保存してください。検証対象と同じ API 応答から期待 Node 一覧を導出してはいけません。そうすると欠落 Node を見逃します。Node を置き換える場合は ID 記録が変わるため、意図的な照合作業が必要です。

```json
[
  {"name": "REPLACE_WITH_REGISTERED_NODE_NAME", "uid": "REPLACE_WITH_APPROVED_NODE_UID"}
]
```

次を check-fleet.sh として保存します。Bash、kubectl、jq が必要です。運用者のワークステーションでは `KUBE_CONTEXT` を設定し、クラスター内 observer は自身の ServiceAccount を使います。API 呼び出しが拒否/失敗した場合、対象グループが空の場合、UID が違う場合、condition が欠けている/Unknown の場合は、すべて nonzero で終了します。

```bash
#!/usr/bin/env bash
# Read-only Node inventory/condition snapshot; no workload or host mutations.
set -euo pipefail
EXPECTED_FILE="${1:?Usage: check-fleet.sh expected-nodes.json}"
umask 077
WORK_DIR=$(mktemp -d)
trap 'rm -rf -- "$WORK_DIR"' EXIT
KUBECTL=(kubectl --cache-dir "$WORK_DIR/kube-cache")
if [ -n "${KUBE_CONTEXT:-}" ]; then KUBECTL+=(--context "$KUBE_CONTEXT"); fi
"${KUBECTL[@]}" get nodes -l eks.amazonaws.com/compute-type=hybrid -o json > "$WORK_DIR/nodes.json"
jq -e --slurpfile expected "$EXPECTED_FILE" '
  def required($kind; $status):
    [.status.conditions[]? | select(.type == $kind)] as $c |
    ($c | length) == 1 and $c[0].status == $status;
  $expected[0] as $want |
  ($expected | length) == 1 and ($want | type) == "array" and
  ($want | length) > 0 and
  ($want | length) == ($want | map(.name) | unique | length) and
  all($want[]; (.name | type) == "string" and (.name | length) > 0 and
               (.uid | type) == "string" and (.uid | length) > 0) and
  (.items | type) == "array" and
  (.items | map(.metadata.name) | sort) == ($want | map(.name) | sort) and
  all(.items[];
    . as $node |
    any($want[]; .name == $node.metadata.name and .uid == $node.metadata.uid) and
    .metadata.deletionTimestamp == null and
    .metadata.labels["eks.amazonaws.com/compute-type"] == "hybrid" and
    required("Ready"; "True") and
    required("MemoryPressure"; "False") and
    required("DiskPressure"; "False") and
    required("PIDPressure"; "False"))
' "$WORK_DIR/nodes.json" > /dev/null
printf 'Expected Node identities and conditions match this snapshot.\n'
# CNI readiness, DNS, network paths, storage, applications and freshness need
# separate checks; Node Ready is not an end-to-end health guarantee.
```

これは Node の一覧と condition のスナップショットです。`Ready=True` でも現在の CNI、DNS、ストレージ、アプリケーションの正常性は証明されません。選択した CNI の実際の DaemonSet/Pod、対象サイト間の接続、DNS 解決、ストレージ操作、ワークロード endpoint を個別に確認してください。部分文字列一致で `NotReady` を Ready と数えてはいけません。

## 3. Node のアップグレード戦略

### バージョン skew ポリシー

以下の1.31表はバージョン skew の計算例であり、現在その過去の Node バージョンをデプロイする推奨ではありません。現行の AWS 資料から EKS 対応の対象バージョンと互換 OS、CNI、CSI、ランタイムを選択してください。

Kubernetes は kubelet と API server の間に厳格なバージョン互換ポリシーを定めています。

| kubelet バージョン | API Server バージョン | 互換性 |
|---|---|---|
| 1.31 | 1.31 | 可（同じバージョン） |
| 1.30 | 1.31 | 可（n-1） |
| 1.29 | 1.31 | 可（n-2） |
| 1.28 | 1.31 | 可（n-3） |
| 1.27 | 1.31 | 不可（n-4、非対応） |
| 1.32 | 1.31 | 不可（kubelet が API server より新しいため非対応） |

> **アップグレード順序**: 遅れている Node を現行 control plane のマイナーバージョンに合わせてから、Node を次のマイナーバージョンへ移す前に control plane をアップグレードします。kubelet を API server より新しくしてはいけません。サポートされる skew は、古い Node を無期限に維持する推奨ではありません。

### アップグレード前チェックリスト

各 wave の前に、対象の major.minor と完全な artifact バージョン/チェックサムを承認し、control-plane skew と OS/CNI/CSI/ランタイムの互換性、退避するワークロードを受け入れる十分な空き容量を確認します。Pod の request/配置、PDB の許容 disruption、local PV/emptyDir の所有者、バックアップ/復旧、可観測性を確認してください。`kubectl top` は任意の実測値であり、すべての Pod が再配置可能だという証拠ではありません。

Node 名/UID、実ホスト接続先、credential provider、元の `.spec.unschedulable` 状態を inventory に記録します。`nodeadm upgrade` は Node 名を維持し、credential provider を変更できません。通常、指定 minor 用の最新 artifact を選ぶため、minor を固定するだけでは不変の artifact 計画になりません。再現性が必要な場合は、承認済み manifest/非公開 artifact の手順を使います。

### Rolling Upgrade

**明示的に選んだ Node を一度に1台だけ**処理し、最初の失敗で停止します。以下は未実行の運用手順例であり、可用性を検証済みのフリートコントローラーではありません。最初と最後のブロックは承認済みのクラスター管理ワークステーションから、同じ shell 内で実行するか、記録済みディレクトリ/入力を復元して実行します。運用者には Node、Lease、Pod/PDB の参照と cordon/drain 権限が必要です。

非公開の作業記録のパスを保存してください。以下のコマンドは選択した Node を cordon/drain します。PDB による停止や local emptyDir がある場合は、ワークロード/データの扱いを明示的に決めます。失敗した drain を通すためだけに force、eviction 無効化、emptydir-data 削除を追加してはいけません。

```bash
set -euo pipefail
umask 077
: "${KUBE_CONTEXT:?Set the approved host cluster context}"
: "${NODE:?Set the actual Kubernetes Node name}"
: "${EXPECTED_UID:?Set the approved Node UID}"
UPGRADE_RECORD_DIR=$(mktemp -d "$PWD/hybrid-upgrade.XXXXXX")
kubectl --context "$KUBE_CONTEXT" get node "$NODE" -o json \
  > "$UPGRADE_RECORD_DIR/node-before.private.json"
jq -e --arg uid "$EXPECTED_UID" '
  .metadata.uid == $uid and
  .metadata.labels["eks.amazonaws.com/compute-type"] == "hybrid" and
  .metadata.deletionTimestamp == null
' "$UPGRADE_RECORD_DIR/node-before.private.json" > /dev/null
kubectl --context "$KUBE_CONTEXT" -n kube-node-lease get lease "$NODE" -o json \
  > "$UPGRADE_RECORD_DIR/lease-before.private.json"
jq -e --arg uid "$EXPECTED_UID" '
  any(.metadata.ownerReferences[]?; .kind == "Node" and .uid == $uid) and
  (.spec.renewTime | type) == "string"
' "$UPGRADE_RECORD_DIR/lease-before.private.json" > /dev/null
printf 'Private upgrade record: %s\n' "$UPGRADE_RECORD_DIR"
kubectl --context "$KUBE_CONTEXT" cordon "$NODE"
kubectl --context "$KUBE_CONTEXT" drain "$NODE" --ignore-daemonsets --timeout=10m
```

drain 成功後に限り、**対応付け済みの物理/仮想ホスト**へ接続し、記録した ID とレビュー済み nodeadm バイナリを確認してから、そのホスト上で影響を伴う upgrade を実行します。NodeConfig では既存の credential provider を維持します。node/pod/init 検証を通常作業として省略しないでください。

```bash
set -euo pipefail
: "${TARGET_MINOR:?Set the approved EKS-supported major.minor target}"
sudo /usr/local/bin/nodeadm upgrade "$TARGET_MINOR" \
  -c file:///etc/eks/nodeconfig.yaml --timeout 20m
```

upgrade コマンドのエラーや接続喪失は、Kubernetes に古い Ready condition が表示されていても、状態不明/失敗の作業です。Node を cordon したまま調査してください。ホスト上の処理成功が確認できた後、ワークステーションから状態を観測します。artifact 計画にある完全な kubelet バージョンを、build suffix も含めて使用します。

```bash
set -euo pipefail
umask 077
: "${KUBE_CONTEXT:?Set the approved host cluster context}"
: "${NODE:?Set the recorded Node name}"
: "${EXPECTED_UID:?Set the recorded Node UID}"
: "${EXPECTED_KUBELET_VERSION:?Set the full version from the approved artifact plan}"
: "${UPGRADE_RECORD_DIR:?Use the private record directory from the pre-upgrade step}"
jq -e --arg uid "$EXPECTED_UID" --arg node "$NODE" \
  '.metadata.uid == $uid and .metadata.name == $node' \
  "$UPGRADE_RECORD_DIR/node-before.private.json" > /dev/null
POSTCHECK_DIR=$(mktemp -d "$UPGRADE_RECORD_DIR/check.XXXXXX")
kubectl --context "$KUBE_CONTEXT" get node "$NODE" -o json \
  > "$POSTCHECK_DIR/node-after.private.json"
jq -e --arg uid "$EXPECTED_UID" --arg version "$EXPECTED_KUBELET_VERSION" '
  [.status.conditions[]? | select(.type == "Ready")] as $ready |
  .metadata.uid == $uid and
  .metadata.labels["eks.amazonaws.com/compute-type"] == "hybrid" and
  .metadata.deletionTimestamp == null and
  .status.nodeInfo.kubeletVersion == $version and
  ($ready | length) == 1 and $ready[0].status == "True"
' "$POSTCHECK_DIR/node-after.private.json" > /dev/null
kubectl --context "$KUBE_CONTEXT" -n kube-node-lease get lease "$NODE" -o json \
  > "$POSTCHECK_DIR/lease-after.private.json"
jq -e --arg uid "$EXPECTED_UID" \
  --slurpfile before "$UPGRADE_RECORD_DIR/lease-before.private.json" '
  def epoch: sub("\\.[0-9]+Z$"; "Z") | fromdateiso8601;
  any(.metadata.ownerReferences[]?; .kind == "Node" and .uid == $uid) and
  (.spec.renewTime | epoch) > ($before[0].spec.renewTime | epoch)
' "$POSTCHECK_DIR/lease-after.private.json" > /dev/null
printf 'Node identity, target kubelet version, Ready and a newer Lease observed.\n'
# Workload/CNI/DNS/storage checks and the prior scheduling intent remain separate.
# This check never uncordons the node.
```

保存したスナップショットより後の Lease renewal に加えて、対象バージョンと Node ID の一致が必要です。それでもアプリケーションの受け入れ試験にはなりません。CNI、DNS、volume、driver/runtime、ワークロードの復旧を確認してください。その後、メンテナンス前に schedulable だった Node だけを明示的に uncordon します。EXIT trap で自動 uncordon したり、すでに意図的に cordon されていた Node のスケジューリングを戻したりしてはいけません。証跡を保存し、次の承認済み Node に進みます。

### Canary Upgrade

最初に選ぶ canary は OS/アーキテクチャ、ランタイム、credential provider、ワークロードが代表的になるようにし、API が返した最初の Node を選んではいけません。同じ1台ずつの手順を使い、合意した期間、アプリケーションのエラー/レイテンシー、ストレージ/ネットワークの正常性、実バージョンを観測します。固定 sleep や Node Ready だけでは合格になりません。確認後に限って小さな wave へ広げ、切替の受け入れが完了するまで旧ホストを維持します。

<a id="rollback-procedure"></a>

### 復旧とロールバックの境界

予備容量がある場合、AWS はホスト交換と管理された切替を推奨しています。アプリケーション、ストレージ、ネットワーク、対象バージョンの確認が完了するまで旧ホストを利用可能に保ちます。インプレース `nodeadm upgrade` は影響を伴い、汎用のトランザクション型 downgrade 手段ではありません。

失敗時は該当 Node を cordon したまま残りの wave を停止し、診断情報を保持してインストール済み artifact/認証情報を調べます。現行 control plane と互換性のある承認済みイメージ/バージョンで復旧します。古い `Ready=True` condition が残っているというだけで uncordon せず、想定 Node ID、実際の kubelet バージョン、ワークロード readiness を確認します。

汎用ロールバック手順として `/var/lib/kubelet` や `/etc/kubernetes` を再帰削除しないでください。Pod の volume/subpath mount がホストやアプリケーションのデータを露出することがあります。nodeadm 1.0.9以降では、強制 uninstall でも `/var/lib/kubelet` を意図的に保持します。例外的な削除には mount とデータ保持の明示的なレビューが必要です。uninstall は drain も Kubernetes Node object の削除も行わず、CNI も完全には削除しません。SSM の場合は managed instance の登録も解除します。再構築には、盲目的な uninstall/install の繰り返しではなく、install/bootstrap 全体と ID の照合が必要です。

---

## 4. 認証情報のライフサイクル

<a id="ssm-hybrid-activation-renewal"></a>

### SSM Hybrid Activation の有効期限

Activation の有効期限が制限するのは**新しい登録**です。すでに登録済みの Node は明示的に登録解除するまで Systems Manager の管理対象のままです。元の activation が期限切れになっただけで、正常な Node を uninstall/re-register しないでください。登録、agent のローテーション認証情報、IAM 権限、接続性はそれぞれ別のライフサイクルです。

ホスト追加の登録や、承認済み復旧で再登録が必要な場合に限り新しい activation を作ります。SSM 用に設定した実際の Hybrid Nodes IAM role を使い、汎用 Run Command role で代用しないでください。AWS リソース作成コマンドの前に role の trust/permissions、account、Region、新規登録する正確な Node 数を確認します。Activation code はパスワード同様の秘密情報です。応答は非公開ファイルに保存し、承認済み NodeConfig secret-file 手順で渡してください。

```bash
set -euo pipefail
umask 077
: "${HYBRID_NODE_ROLE_NAME:?Set the reviewed Hybrid Nodes IAM role name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${NEW_NODE_COUNT:?Set the approved registration count}"
set -C  # Refuse to overwrite an existing private response file.
aws ssm create-activation   --iam-role "$HYBRID_NODE_ROLE_NAME"   --registration-limit "$NEW_NODE_COUNT"   --region "$AWS_REGION"   --output json > activation.private.json
```

AWS CLI の失敗時は、応答ファイルが信頼できない/部分的に書かれた可能性があります。再試行前に非公開のまま確認し、処理を止めてください。Activation code を表示したり、このファイルを commit したりしないでください。API の既定登録期間が適切でない場合は、承認済みの有効期限を明示します。最長は30日です。count は登録数の上限であり、activation が漏えいした際に利用可能ホストを認可する境界ではありません。

`nodeadm uninstall` は SSM 管理下ホストの登録を解除し、インストール済みコンポーネントを削除します。後続の `init` だけでは `install` を置き換えられません。意図的な復旧では、まず drain/データ保持と ID 変更をレビューし、完全な[ブートストラップ手順](./04-node-bootstrap.md)を使います。既存 Node 名/UID と SSM managed-instance ID を inventory と照合し、古い成功記録を黙って再利用しないでください。

### IAM Roles Anywhere 証明書の更新

期限前に既存 PKI を通じて Node の**ホスト認証証明書**を更新します。これは kubelet client/server 証明書や EKS control-plane CA とは別です。証明書 subject、設定された nodeName、role-session condition、profile、role、trust anchor の互換性を維持してください。CN の変更は無害なファイル更新ではありません。

#### 証明書の有効期限監視

想定パスではなく、設定済みの certificatePath を対象にこの検査を実行します。証明書の欠落、読み込み不能、無効、または30日以内の期限切れ見込みはいずれも失敗として扱います。30日の警告は運用しきい値の例です。

```bash
#!/usr/bin/env bash
set -euo pipefail
CERT_PATH="${1:?Usage: check-cert-expiry.sh certificate.pem}"
test -r "$CERT_PATH" || { echo 'Certificate missing or unreadable' >&2; exit 1; }
openssl x509 -in "$CERT_PATH" -checkend 2592000 -noout
# This is an expiration check only, not chain/key/CN/trust/IAM validation.
```

<a id="automatic-renewal-script"></a>

#### 証明書更新の手順

組織が承認した CA client と認証付き enrollment policy を使ってください。汎用の認証不要な `/sign` endpoint はありません。既存鍵を再利用する場合は保護を維持し、鍵をローテーションする場合は承認済み手順に従います。意図した ID で CSR を提出し、発行された証明書候補は稼働中証明書と別に保存します。

次の**ローカル検査だけ**が確認するのは、残存有効期間、別途承認された root に対する chain 検証、公開鍵との対応です。必要な場合は `INTERMEDIATE_CHAIN` で中間証明書を渡します。すべての PKI/IAM policy、失効、nodeName/CN、実際の認証条件を確認するわけではありません。

```bash
set -euo pipefail
umask 077
: "${CANDIDATE_CERT:?Path to the issued candidate leaf certificate}"
: "${PRIVATE_KEY:?Path to its existing protected private key}"
: "${APPROVED_CA_PEM:?Path to the separately approved trust roots}"
CERT_CHECK_DIR=$(mktemp -d)
trap 'rm -rf -- "$CERT_CHECK_DIR"' EXIT
openssl x509 -in "$CANDIDATE_CERT" -checkend 2592000 -noout
VERIFY=(openssl verify -CAfile "$APPROVED_CA_PEM")
if [ -n "${INTERMEDIATE_CHAIN:-}" ]; then VERIFY+=(-untrusted "$INTERMEDIATE_CHAIN"); fi
"${VERIFY[@]}" "$CANDIDATE_CERT"
openssl x509 -in "$CANDIDATE_CERT" -pubkey -noout > "$CERT_CHECK_DIR/cert.pub"
openssl pkey -in "$PRIVATE_KEY" -pubout > "$CERT_CHECK_DIR/key.pub"
cmp "$CERT_CHECK_DIR/cert.pub" "$CERT_CHECK_DIR/key.pub"
```

リリース前に subject/SAN、用途、CA policy、失効状態、正確な nodeName/role condition をレビューします。現行証明書を非公開でバックアップし、承認済み certificate manager に、所有者/permission を維持して同一 filesystem 上で検証済み証明書を atomic に置換させます。鍵と証明書を両方ローテーションする場合、利用側から不一致の組み合わせが見えないよう調整してください。

nodeadm が設定した credential-helper 方式（credential process または credential-file updater）を確認し、承認済みの非公開診断経路で次の credential refresh を検証します。kubelet を再起動しても X.509 証明書は更新されず、helper が受け入れた証明にもなりません。発行元、候補拒否、atomic replacement、refresh、rollback をその環境でテストした後にのみ自動更新を計画します。この章のために本番更新は実行していません。

#### Trust Anchor の更新

同じ信頼済み CA で leaf certificate を更新しても、通常は trust anchor の置換は不要です。CA の切替は依存する全ホスト/profile/role に影響します。PKI/IAM の担当者と移行期間を計画し、source type と依存 Node を調べ、trust 変更前に復旧経路を維持してください。

**CERTIFICATE_BUNDLE** source では JSON file input を使い、PEM の改行を維持します。ここでの sourceData union には x509CertificateData だけを指定します。AWS_ACM_PCA anchor は acmPcaArn を使い、別途レビューが必要です。この例は非公開 request file を作成した後 AWS を更新します。通常の証明書期限監視として実行してはいけません。

```bash
set -euo pipefail
umask 077
: "${APPROVED_CA_PEM:?Path to the reviewed CA certificate bundle}"
: "${TRUST_ANCHOR_ID:?Set the reviewed existing trust anchor ID}"
: "${AWS_REGION:?Set the trust anchor Region}"
set -C
jq -n --rawfile bundle "$APPROVED_CA_PEM" \
  '{sourceType:"CERTIFICATE_BUNDLE", sourceData:{x509CertificateData:$bundle}}' \
  > trust-anchor-source.private.json
# AWS mutation: run only after the CA rollover and dependent-node review.
aws rolesanywhere update-trust-anchor --trust-anchor-id "$TRUST_ANCHOR_ID" \
  --region "$AWS_REGION" --source file://trust-anchor-source.private.json \
  --output json > trust-anchor-update.private.json
```

更新後に意図した anchor を読み戻して検証し、切替完了前に canary で新しい credential 発行をテストしてください。API エラーは状態不明/失敗であり、旧 trust が有効だという証拠ではありません。発行済み credential を記録したり、anchor を1つ置き換えればすべての旧証明書のアクセスが保たれると考えたりしないでください。

## 5. ヘルス監視の自動化

### 自動ヘルスチェック CronJob

この observer はセクション2の Node スナップショット検査を実行します。ホスト上で nodeadm を実行したり、AWS credential を検証したりはしません。Bash、kubectl、jq を含み、クラスターと互換性があり UID 10001 で実行できる、レビュー済みイメージを使います。placeholder image はデプロイ前に置き換えてください。ここではイメージやクラスター実行を検証していません。監視用 namespace は事前に存在する必要があります。

保存済み `check-fleet.sh` と承認済み `expected-nodes.json` から ConfigMap manifest を作ります。その後、以下の ServiceAccount/RBAC/CronJob とまとめてレビューし、適用してください。ClusterRole は全 Node を list できます。label selector はクエリの絞り込みであり、認可境界ではありません。この ServiceAccount を使う Pod や ConfigMap を変更できる namespace owner を確認してください。

```bash
: "${KUBE_CONTEXT:?Set the approved cluster context}"
kubectl --context "$KUBE_CONTEXT" -n monitoring create configmap hybrid-node-check \
  --from-file=check-fleet.sh --from-file=expected-nodes.json \
  --dry-run=client -o yaml > hybrid-node-check.yaml
# Review this manifest and the observer/RBAC manifest before applying either.
```
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: hybrid-node-observer
  namespace: monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: hybrid-node-observer
rules:
- apiGroups:
  - ''
  resources:
  - nodes
  verbs:
  - get
  - list
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: hybrid-node-observer
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: hybrid-node-observer
subjects:
- kind: ServiceAccount
  name: hybrid-node-observer
  namespace: monitoring
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: hybrid-node-observer
  namespace: monitoring
spec:
  schedule: '*/30 * * * *'
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 120
  successfulJobsHistoryLimit: 1
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      backoffLimit: 0
      activeDeadlineSeconds: 120
      ttlSecondsAfterFinished: 1800
      template:
        spec:
          serviceAccountName: hybrid-node-observer
          restartPolicy: Never
          securityContext:
            runAsNonRoot: true
            runAsUser: 10001
            runAsGroup: 10001
            fsGroup: 10001
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: observer
            image: example.invalid/hybrid-observer:replace-with-reviewed-build
            command:
            - /bin/bash
            - /config/check-fleet.sh
            - /config/expected-nodes.json
            env:
            - name: TMPDIR
              value: /work
            securityContext:
              allowPrivilegeEscalation: false
              readOnlyRootFilesystem: true
              capabilities:
                drop:
                - ALL
            resources:
              requests:
                cpu: 100m
                memory: 64Mi
              limits:
                cpu: 500m
                memory: 128Mi
            volumeMounts:
            - name: config
              mountPath: /config
              readOnly: true
            - name: work
              mountPath: /work
          volumes:
          - name: config
            configMap:
              name: hybrid-node-check
              defaultMode: 292
          - name: work
            emptyDir:
              sizeLimit: 64Mi
```

Job の失敗**だけでなく、実行漏れ/最近の成功がない場合**にも alert を出します。30分間隔の poll は即時障害検知を提供しません。保護された monitoring system の連携経由で通知してください。Slack webhook bearer URL を Pod 環境変数に埋め込んだり、通知失敗をヘルスチェック成功として扱ったりしないでください。

### kubelet/containerd の状態監視（Node レベル）

次の root 所有スクリプトは、service 状態と root filesystem を観測し、service を再起動しません。別 mount の kubelet/containerd/image filesystem は追加確認が必要です。root disk の使用率だけでは不十分です。コマンドが利用できない場合や測定値が不正な場合に、正常と報告してはいけません。

```bash
#!/usr/bin/env bash
# Observe local services/filesystem; do not restart anything automatically.
set -euo pipefail
failed=0
for service in kubelet containerd; do
  if ! systemctl is-active --quiet "$service"; then
    printf '%s is not active\n' "$service" >&2
    failed=1
  fi
done
usage=$(df --output=pcent / | tail -n 1 | tr -d ' %')
case "$usage" in ''|*[!0-9]*) echo 'Unknown filesystem usage' >&2; exit 1;; esac
if [ "$usage" -ge 90 ]; then
  printf 'Root filesystem usage: %s%%\n' "$usage" >&2
  failed=1
fi
exit "$failed"
```

レビュー済みのホスト管理手順でこのスクリプトを `/usr/local/bin/node-health-check.sh` としてインストールします。実行可能にし、信頼できないユーザーから書き込みできないようにしてください。timer/unit は設定例です。journal と failed unit の監視は別途接続する必要があります。`PrivateTmp` は認証情報を安全にログ出力できるという意味ではありません。

```ini
[Unit]
Description=Periodic Hybrid Node local observation

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
```
```ini
[Unit]
Description=Observe Hybrid Node local services and root filesystem

[Service]
Type=oneshot
User=root
ExecStart=/usr/local/bin/node-health-check.sh
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
```

特定のネットワーク/credential 問題では、運用者が root 権限で `nodeadm debug -c file:///etc/eks/nodeconfig.yaml` を個別に実行できます。AWS とクラスターへ接続し、診断情報を露出する可能性があるため、出力は非公開で保持してください。各 timer tick で黙って実行したり、エラーを破棄したり、インシデント固有の判断なしに kubelet/containerd を自動再起動したりしてはいけません。

## 検証と参考資料

ローカル検証では、設定例の parse、Node/API 失敗時の mock、合成証明書チェックを確認します。フリートへのインストール、ホスト upgrade、credential の切替、Kubernetes admission、CNI/DNS/ストレージ試験、本番 SLO を証明するものではありません。

- [AWS Hybrid Nodes nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [AWS Hybrid Nodes のアップグレード](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-upgrade.html)
- [SSM 登録と activation の有効期間](https://docs.aws.amazon.com/systems-manager/latest/userguide/hybrid-activation-managed-nodes.html)
- [IAM Roles Anywhere credential の設定](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
- [UpdateTrustAnchor の入力](https://docs.aws.amazon.com/botocore/latest/reference/services/rolesanywhere/client/update_trust_anchor.html)
- [Kubernetes バージョン skew](https://kubernetes.io/releases/version-skew-policy/)
- [Node 圧迫による eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [Node Allocatable](https://kubernetes.io/docs/tasks/administer-cluster/reserve-compute-resources/)
- [正常な Node shutdown](https://kubernetes.io/docs/concepts/cluster-administration/node-shutdown/)
- [containerd の設定](https://github.com/containerd/containerd/blob/main/docs/cri/config.md)
- [Cilium 1.20.1 cluster-pool allocator](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/cluster-pool.rst)

---

< [前へ: ワークロード配置戦略](./06-workload-placement.md) | [目次](./README.md) | [次へ: 運用とメンテナンス](./08-operations.md) >

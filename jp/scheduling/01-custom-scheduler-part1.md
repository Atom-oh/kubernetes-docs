# カスタムスケジューラー

> **例の基準**: Kubernetes 1.35.8、Go 1.27.2
> **最終更新日**: 2026年10月16日

Kubernetesスケジューラーは、Podをどのノードに配置するかを決める重要なコンポーネントです。既定のスケジューラーはほとんどの場面で適切に動作しますが、特定の要件に対応するためにカスタムスケジューラーを実装することもできます。この章では、EKSでカスタムスケジューラーを実装する方法を説明します。

## ラボ環境のセットアップ

このドキュメントの例を試すには、次のツールと環境が必要です。

### 必要なツール

* クラスターのAPIサーバーに対して、マイナーバージョン差が1以内のkubectl
* 再現可能な例を実行するためのGo 1.27.2とPython 3
* Linuxワーカーノードを持つ、破棄可能なKubernetes 1.35クラスター。EKSを使う場合は、まず[AWSのバージョンカレンダー](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)を確認してください。

ここで使うフレームワークのインターフェースと設定は、Kubernetes **1.35.8**に対して確認しています。これは例示用の基準であり、KubernetesやEKSの最新リリースを示すものではありません。スケジューラーをクラスターのマイナーバージョンに合わせ、アップグレード時にプラグイン、フィーチャーゲート、RBACを再検証してください。Kubernetesモジュールはstaging依存関係を使っているため、`go get k8s.io/kubernetes`だけでは`v0.0.0`のstaging要件を解決できません。

### 開発環境のセットアップ

```bash
mkdir -p custom-scheduler
cd custom-scheduler

# Generate a standalone module from the pinned upstream staging-module list.
python3 - <<'PY'
from pathlib import Path
import re
from urllib.request import urlopen

version = "v1.35.8"
staging_version = "v0.35.8"
url = f"https://raw.githubusercontent.com/kubernetes/kubernetes/{version}/go.mod"
with urlopen(url, timeout=30) as response:
    upstream = response.read().decode()
modules = re.findall(r"^\s*(k8s\.io/[\w-]+) => \./staging/src/\1\s*$", upstream, re.M)
if not modules:
    raise RuntimeError("No staging modules found; review upstream go.mod")
text = f"module example.com/custom-scheduler\n\ngo 1.27.2\n\nrequire k8s.io/kubernetes {version}\n\nreplace (\n"
text += "".join(f"\t{m} => {m} {staging_version}\n" for m in modules)
Path("go.mod").write_text(text + ")\n")
PY
```

## スケジューリングの概要

### Kubernetesのスケジューリングプロセス

Kubernetesのスケジューリングプロセスは、次の段階で構成されます。

### スケジューリング段階の詳細

1. **フィルタリング段階**
   * Podを実行できるノードを特定します。
   * 各フィルタープラグインが、そのノードでPodを実行できるか判定します。
   * いずれかのフィルターで不適合になると、そのノードは候補から除外されます。
2. **スコアリング段階**
   * フィルターを通過したノードにスコアを付けます。
   * 各スコアリングプラグインは、必要に応じて正規化した後、0～100のスコアを返します。
   * 重みを適用して最終スコアを計算します。
3. **バインド段階**
   * 最も高いスコアのノードにPodを割り当てます。
   * Podとノードのバインド情報をKubernetes API経由で更新します。

## カスタムスケジューラーが必要な場合

次のような要件がある場合は、カスタムスケジューラーを検討してください。

1. **特殊なハードウェア要件**: GPU、FPGA、特殊なネットワークデバイスなど
2. **複雑なワークロード配置ルール**: 特定のワークロードを特定のノードグループに配置する
3. **コスト最適化**: Spotインスタンスとオンデマンドインスタンスの間で配置を最適化する
4. **ローカリティ要件**: データのローカリティを考慮してワークロードを配置する
5. **複数スケジューラーの利用**: ワークロードの種類に応じて複数のスケジューラーを使う

### 実環境でのユースケース

| 業界 | ユースケース | カスタムスケジューラーを使う利点 |
|---|---|---|
| 金融 | 高頻度取引システム | ネットワークトポロジーを考慮して配置し、レイテンシーを最小化する |
| 医療 | 医用画像処理 | GPUを考慮した配置とデータローカリティの優先 |
| 通信 | 5Gネットワーク機能 | ラベル付けされたネットワークデバイスに配置を制約する |
| 小売 | 季節的なトラフィックへの対応 | Spotインスタンスを費用対効果よく利用する |
| メディア | 動画トランスコーディング | ワークロード特性に応じてCPU／GPUノードを選択する |

1. **フィルタリング**: Podを実行できるノードを特定します。リソース要件、ノードセレクター、ノードアフィニティ、taintとtolerationなどを確認します。
2. **スコアリング**: フィルターを通過したノードにスコアを付けます。ノードのリソース使用状況、Pod間アフィニティ、ノードアフィニティなどを考慮します。
3. **バインド**: 最も高いスコアのノードにPodを割り当てます。

コードを書く前に、デバイスプラグイン、必須／優先アフィニティ、taintとtoleration、トポロジー分散制約で要件を表現できないか確認してください。通常のGPUリクエストにカスタムスケジューラーは必要ありません。

### 既定のスケジューラーの制約

既定のスケジューラーでは、次のような要件を満たせないことがあります。

1. **特殊なハードウェア要件**: GPUやFPGAなどに高度なスケジューリングロジックが必要になる場合があります。
2. **複雑なアフィニティルール**: 基本的なアフィニティルールでは表現しにくい配置制約がある場合があります。
3. **カスタムメトリクス**: 既定のスケジューラーが考慮しないメトリクスを基準に配置する必要がある場合があります。
4. **ドメイン固有の知識**: 特定のアプリケーション領域に特化したスケジューリングロジックが必要になる場合があります。

## カスタムスケジューラーの実装方法

カスタムスケジューラーの実装方法は、大きく分けて3つあります。

1. **複数スケジューラー方式**: 既定のスケジューラーと並行してカスタムスケジューラーを実行します。
2. **Scheduler Extender方式**: 既定のスケジューラーを拡張し、追加のフィルタリング関数や優先度関数を提供します。
3. **Scheduler Frameworkプラグイン**: Kubernetes 1.15で導入されたScheduler Frameworkを使ってプラグインを開発します。

### 複数スケジューラー方式

複数スケジューラー方式では、カスタムスケジューラーを既定のスケジューラーと並行して実行します。Podの作成時に`schedulerName`フィールドを指定して、使用するスケジューラーを選択できます。

#### カスタムスケジューラーの実装

upstreamのスケジューラーコマンドを、2つ目のスケジューラーのベースとして使います。これにより、`NodeResourcesFit`、`TaintToleration`、`NodeAffinity`、`VolumeBinding`などの既定プラグインが維持されます。最初にReady状態になったノードを選んでバインドAPIを呼び出すだけの実装では、これらのチェックを回避してしまいます。

これを`main.go`として保存します。この段階では独自の配置ポリシーは追加しません。後述のスコアリング用ヘルパーとクイズで、拡張できる箇所を確認します。

```go
package main

import (
    "os"

    "k8s.io/component-base/cli"
    "k8s.io/kubernetes/cmd/kube-scheduler/app"
)

func main() {
    os.Exit(cli.Run(app.NewSchedulerCommand()))
}
```

#### カスタムスケジューラーのデプロイ

以下の`Dockerfile`を保存し、ローカルでビルドコマンドを実行したうえで、承認済みのレジストリ手順でイメージを公開します。マニフェストの`registry.example.com/...`は作成したイメージに置き換え、可能であればダイジェストを指定してください。バイナリーとイメージのアーキテクチャはワーカーノードに合わせる必要があります。

```dockerfile
FROM gcr.io/distroless/static-debian12:nonroot
COPY custom-scheduler /custom-scheduler
ENTRYPOINT ["/custom-scheduler"]
```

```bash
go mod tidy
CGO_ENABLED=0 go build -buildvcs=false -trimpath -o custom-scheduler .
# Build for the same architecture as the scheduler's worker nodes.
docker build -t custom-scheduler:v1.35.8-1 .
```

これはラボ用のデプロイ例であり、本番環境で検証済みの高可用性構成ではありません。`custom-scheduler`が利用可能になる前に起動できるよう、スケジューラーPod自体は`default-scheduler`を使います。2つのレプリカは`scheduler-lab`名前空間の**1つの**Leaseを共有します。別のスケジューラーグループには別のLeaseが必要です。優先アンチアフィニティは配置を分散しやすくしますが、ホストやAZが分かれる保証はありません。

管理者は、参照先のブートストラップRBACロールが存在することを確認してください。`system:kube-scheduler`と`system:volume-scheduler`は、バインドやプリエンプションを含む強力なクラスター全体のスケジューリング権限を付与します。`schedulerName`はセキュリティ境界ではありません。別のRoleでKubernetesのブートストラップロールを変更せずにLeaseへのアクセス権を追加します。HTTPSエンドポイントは非公開にしてください。リソース量と障害時の動作は、対象クラスターでテストする必要があります。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: scheduler-lab
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: custom-scheduler
  namespace: scheduler-lab
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: scheduler-lab-scheduling
subjects:
- kind: ServiceAccount
  name: custom-scheduler
  namespace: scheduler-lab
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:kube-scheduler
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: scheduler-lab-volumes
subjects:
- kind: ServiceAccount
  name: custom-scheduler
  namespace: scheduler-lab
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:volume-scheduler
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: scheduler-lab-authentication
  namespace: kube-system
subjects:
- kind: ServiceAccount
  name: custom-scheduler
  namespace: scheduler-lab
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: extension-apiserver-authentication-reader
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: custom-scheduler-leader-election
  namespace: scheduler-lab
rules:
- apiGroups: ["coordination.k8s.io"]
  resources: ["leases"]
  verbs: ["create"]
- apiGroups: ["coordination.k8s.io"]
  resources: ["leases"]
  resourceNames: ["custom-scheduler"]
  verbs: ["get", "update", "patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: custom-scheduler-leader-election
  namespace: scheduler-lab
subjects:
- kind: ServiceAccount
  name: custom-scheduler
  namespace: scheduler-lab
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: custom-scheduler-leader-election
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: custom-scheduler-config
  namespace: scheduler-lab
data:
  config.yaml: |
    apiVersion: kubescheduler.config.k8s.io/v1
    kind: KubeSchedulerConfiguration
    leaderElection:
      leaderElect: true
      resourceLock: leases
      resourceName: custom-scheduler
      resourceNamespace: scheduler-lab
      leaseDuration: 15s
      renewDeadline: 10s
      retryPeriod: 2s
    profiles:
    - schedulerName: custom-scheduler
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: custom-scheduler
  namespace: scheduler-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: custom-scheduler
  template:
    metadata:
      labels:
        app: custom-scheduler
    spec:
      serviceAccountName: custom-scheduler
      securityContext:
        runAsUser: 65532
        runAsGroup: 65532
        fsGroup: 65532
      nodeSelector:
        kubernetes.io/os: linux
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              topologyKey: kubernetes.io/hostname
              labelSelector:
                matchLabels:
                  app: custom-scheduler
      containers:
      - name: custom-scheduler
        image: registry.example.com/training/custom-scheduler:v1.35.8-1
        args:
        - --config=/etc/scheduler/config.yaml
        - --cert-dir=/tmp
        ports:
        - name: https
          containerPort: 10259
        livenessProbe:
          httpGet:
            path: /healthz
            port: https
            scheme: HTTPS
          initialDelaySeconds: 15
        securityContext:
          runAsNonRoot: true
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: ["ALL"]
          seccompProfile:
            type: RuntimeDefault
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            memory: 512Mi
        volumeMounts:
        - name: config
          mountPath: /etc/scheduler
          readOnly: true
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: config
        configMap:
          name: custom-scheduler-config
      - name: tmp
        emptyDir: {}
```

#### カスタムスケジューラーの使用

Podの作成時に`schedulerName`フィールドを指定して、カスタムスケジューラーを選択します。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx
spec:
  schedulerName: custom-scheduler
  containers:
  - name: nginx
    image: nginx:1.30.6
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        memory: 128Mi
```

## EKSでのカスタムスケジューラー実装

Amazon EKSでカスタムスケジューラーを実装する場合は、次の点を考慮してください。

1. **Kubernetesの認証と認可**: クラスター内で動作するスケジューラーは、ServiceAccountトークンとKubernetes RBACを使います。EC2やCloudWatchなどAWS APIを呼び出す場合に限りIAM権限も必要です。そのワークロードIDには必要最小限のAWS権限だけを付与してください。
2. **マネージドコントロールプレーン**: ワーカーノード上で独自のセカンダリスケジューラーを実行します。マネージド既定スケジューラーのプロセス、フラグ、プラグインレジストリーにアクセスできると考えないでください。
3. **コンピューティングの境界**: この例はEC2ワーカーノードを対象とします。[EKS FargateではスケジューリングとアドミッションのコントローラーをAWSが管理します](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)。Fargateノードを選択したり、`custom-scheduler`を指定したりしても、Fargateのキャパシティはプロビジョニングされません。
4. **トポロジーとインスタンスのラベル**: まず既存のノードラベル、リソースリクエスト、アフィニティ、トポロジー分散制約を使います。カスタムスケジューラーがキャパシティを作り出したり、レイテンシーを保証したりするわけではありません。

### EKSカスタムスケジューラーのアーキテクチャ

各スケジューラーはKubernetes APIを監視し、対象Pod用の**独自のキャッシュとキュー**を保持します。APIサーバーはPodの状態を保存して公開しますが、共有のスケジューリングキューを所有するわけではありません。EC2／CloudWatch連携は任意です。メトリクス取得が遅い場合や失敗する場合に備え、タイムアウトに上限を設け、明示的なフォールバックポリシーを用意してください。

### EKS固有のスケジューリング上の考慮事項

以下の関数は、`preferences`パッケージに別ファイルとして保存する**説明用のソフトスコアリングヘルパー**です。上のバイナリーに自動登録されるわけではありません。既定のフィルターを通過した後で、テスト済みのScheduler Frameworkの`Score`プラグインから呼び出してください。スコアが**0でもノードは候補のまま**です。必須のルールはフィルターまたは必須アフィニティで実装してください。スコアは0～100の範囲にします。

#### 1. インスタンスタイプを考慮したスケジューリング

以下のc5／m5／r5の重みは、ラベルに基づく優先度設定の例です。実測パフォーマンスの順位でも、これらの世代の購入を推奨するものでもありません。実際のワークロードに適したインスタンスタイプをベンチマークし、優先度を明示的に設定してください。

```go
package preferences

import (
	"strings"

	v1 "k8s.io/api/core/v1"
)

// Illustrative weights, not measured performance or current purchase advice.
func ScoreInstanceType(node *v1.Node) int64 {
	switch {
	case strings.HasPrefix(node.Labels["node.kubernetes.io/instance-type"], "c5."):
		return 100
	case strings.HasPrefix(node.Labels["node.kubernetes.io/instance-type"], "m5."):
		return 50
	case strings.HasPrefix(node.Labels["node.kubernetes.io/instance-type"], "r5."):
		return 30
	default:
		return 10
	}
}
```

#### 2. アベイラビリティゾーン分散を考慮したスケジューリング

組み込みの`PodTopologySpread`プラグインと`topologySpreadConstraints`を優先してください。独自スコアリングが必要なら、スケジューラーキャッシュから一貫したスケジューリングサイクルのスナップショットを作り、対象ワークロードと候補となるすべてのゾーンに範囲を限定します。Podが0個のゾーンも含めてください。必要に応じて割り当て済み／仮定済みPodも数えます。RunningのPodだけを数えると予約を見落とします。候補ノードごとにAPIのlist／getを実行したり、APIエラーを根拠のない件数に置き換えたりしないでください。

```go
package preferences

import (
	"fmt"

	v1 "k8s.io/api/core/v1"
)

// counts is a consistent snapshot for one workload, including empty eligible zones.
// Build it once per scheduling cycle, not by making API calls for every node.
func ScoreAZ(node *v1.Node, counts map[string]int) (int64, error) {
	zone := node.Labels["topology.kubernetes.io/zone"]
	count, ok := counts[zone]
	if zone == "" || !ok {
		return 0, fmt.Errorf("missing eligible-zone snapshot for node %q", node.Name)
	}
	maxCount := 0
	for _, n := range counts {
		if n < 0 {
			return 0, fmt.Errorf("negative pod count")
		}
		if n > maxCount {
			maxCount = n
		}
	}
	if maxCount == 0 {
		return 100, nil
	}
	return int64(100 * (maxCount - count) / maxCount), nil
}
```

#### 3. Spotインスタンスを考慮したスケジューリング

[EKSマネージドノードグループ](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html)では、`eks.amazonaws.com/capacityType`に`SPOT`／`ON_DEMAND`を使います。[Karpenter](https://karpenter.sh/docs/concepts/nodepools/)では、`karpenter.sh/capacity-type`に`spot`／`on-demand`／`reserved`を使います。`node.kubernetes.io/lifecycle`は標準の代替ラベルではありません。このヘルパーはPodに明示された優先度を適用し、不明なラベルは中立として扱います。キャパシティタイプが必須なら必須アフィニティを使用してください。スコアからSpot価格や中断許容度を推測することはできません。

```go
package preferences

import v1 "k8s.io/api/core/v1"

func ScoreCapacityType(node *v1.Node, pod *v1.Pod) int64 {
	preferred := pod.Labels["lifecycle-preference"]
	if preferred != "spot" && preferred != "on-demand" {
		return 50
	}
	actual := node.Labels["karpenter.sh/capacity-type"]
	if actual == "" {
		switch node.Labels["eks.amazonaws.com/capacityType"] {
		case "SPOT":
			actual = "spot"
		case "ON_DEMAND":
			actual = "on-demand"
		}
	}
	if actual != "spot" && actual != "on-demand" && actual != "reserved" {
		return 50
	}
	if actual == preferred {
		return 100
	}
	return 0
}
```

#### 4. GPUワークロードのスケジューリング

デバイスプラグインがGPUリソースを広告し、アドミッション処理後のPodがそのリソースをリクエストする必要があります。拡張リソースでは、リクエストがないリミットは同じ値のリクエストとして補われます。リクエストが0ならGPU需要にはなりません。`NodeResourcesFit`は、有効なリクエストを、既存／仮定済みリクエストを差し引いた割り当て可能リソースと照合します。`Capacity`だけでは空きGPU数は分かりません。

このヘルパーは、GPU対応ノードをGPU以外のワークロードが占有しにくくするだけです。バージョンに対応したリソースヘルパーを使い、initコンテナー、sidecar、オーバーヘッドを含めて計算します。また、APIのデフォルト値が適用済みのPodを前提とします。GPUを配置可能と判定するものではなく、すべてのDRAリソースモデルに対応するものでも、既定のリソースフィルターを置き換えるものでもありません。

```go
package preferences

import (
	v1 "k8s.io/api/core/v1"
	resourcehelper "k8s.io/component-helpers/resource"
)

// pod must be API-defaulted; limits-only extended resources acquire requests.
// NodeResourcesFit still decides whether the effective request fits.
func ScoreGPU(node *v1.Node, pod *v1.Pod) int64 {
	requests := resourcehelper.PodRequests(pod, resourcehelper.PodResourcesOptions{})
	gpuRequest := requests[v1.ResourceName("nvidia.com/gpu")]
	if gpuRequest.Sign() > 0 {
		return 50
	}
	gpuAllocatable := node.Status.Allocatable[v1.ResourceName("nvidia.com/gpu")]
	if gpuAllocatable.Sign() > 0 {
		return 0
	}
	return 100
}
```

## まとめ

この章では、Kubernetesのスケジューリングプロセスの概要と、複数スケジューラー方式でカスタムスケジューラーを実装する方法を説明しました。また、EKSクラスターでカスタムスケジューラーを実装する際の考慮事項も確認しました。

次の章では、Scheduler Extender方式とScheduler Frameworkプラグインを使ったカスタムスケジューラーの実装について説明します。

## 検証と参考資料

Goコマンド、プラグイン、設定は、固定した依存関係のバージョンに対してローカルで確認しました。この監査では、クラスターへのデプロイ、イメージの公開、AWS APIの呼び出し、配置ベンチマーク、高可用性フェイルオーバーのテストは実施していません。

* [複数のスケジューラーを設定する](https://kubernetes.io/docs/tasks/extend-kubernetes/configure-multiple-schedulers/): アーキテクチャとRBACのパターン。古いイメージ／ビルド例はバージョンの根拠にしないでください。
* [スケジューラーの設定](https://kubernetes.io/docs/reference/scheduling/config/)
* [スケジューリングフレームワーク](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
* [Kubernetes 1.35.8のFrameworkインターフェース](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/framework/interface.go)
* [Kubernetes 1.35.8の既定プラグイン](https://github.com/kubernetes/kubernetes/blob/v1.35.8/pkg/scheduler/apis/config/v1/default_plugins.go)

## クイズ

この章の内容を確認するには、[トピッククイズ](../quizzes/scheduling/02-custom-scheduler-part1-quiz.md)に挑戦してください。

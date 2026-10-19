# Managed Node Group から Auto Mode への移行

> **サポート対象バージョン**: EKS Auto Mode GA。例は EKS 1.36 向けにレビュー済み
> **最終更新日**: 2026年9月12日

旧環境のキャパシティを削除する前に、アプリケーション、ストレージ、コントローラーの所有関係を確認してください。以下は段階的な操作例であり、スキーマと CLI フィクスチャをローカルで確認していますが、本番環境でのゼロダウンタイム手順として検証されたものではありません。この監査では、クラウドやクラスターへの変更操作は行っていません。

![既存の7段階の移行概要。旧キャパシティを縮小または削除する前に、各ワークロードの移行段階を検証します。最後の検証レーンはクリーンアップ後の監査であり、最初に行うヘルスチェックではありません。](../.gitbook/assets/en-eks-auto-mode-09-migration-guide-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-auto-mode-09-migration-guide-0.html)

図の最後にある検証ステップは、それ以前のヘルスチェックやロールバック計画なしに、ドレイン、スケールゼロ、削除を行ってよいという意味ではありません。

## 1. 運用対象を棚卸しして特定する

現在サポートされている EKS とアドオンの組み合わせを使用してください。以前の最小バージョン 1.29 は過去の機能要件であり、現在のサポート対象バージョンを示すものではありません。互換性のある VPC CNI、kube-proxy、EBS CSI、スナップショットコントローラー、Pod Identity Agent（導入済みの場合）を確認します。実際の Kubernetes バージョンについて、公式の移行最小要件と互換性一覧の両方を参照してください。

コントローラーの所有関係、ワークロードの配置、システムエージェント、ボリュームとアベイラビリティーゾーン、ロードバランサークラス、IAM、復旧手順、コストを記録します。次のガードは、アカウント、クラスター ARN と作成時刻、API エンドポイント、ノードグループ ARN と作成時刻を確認します。これらは特定時点での識別子チェックであり、並行して動くコントローラーを止める原子的なロックではありません。意図的にプロキシを介しているエンドポイントには、レビュー済みの代替手段を用意してください。不一致を黙って無視してはいけません。

```bash
set -euo pipefail
: "${EXPECTED_ACCOUNT_ID:?Set the intended account}"
: "${AWS_REGION:?Set the cluster region}"
: "${CLUSTER_NAME:?Set the cluster name}"
: "${OLD_NODEGROUP:?Set the reviewed managed node group}"
: "${KUBECONFIG:?Set the reviewed kubeconfig}"
export KUBECONFIG
export KUBE_CONTEXT="${KUBE_CONTEXT:-$CLUSTER_NAME}"
check_account() {
  local actual
  actual=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text) || return
  test "$actual" = "$EXPECTED_ACCOUNT_ID" || { printf 'Account mismatch.\n' >&2; return 1; }
}
check_account
umask 077
export WORK_DIR
WORK_DIR=$(mktemp -d "$PWD/auto-migration.XXXXXXXX")
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" --output json \
  > "$WORK_DIR/cluster-before.json"
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$OLD_NODEGROUP" \
  --region "$AWS_REGION" --output json > "$WORK_DIR/nodegroup-before.json"
guard_context() {
  check_account || return
  local endpoint
  aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" --output json \
    > "$WORK_DIR/cluster-current.json" || return
  endpoint=$(kubectl --context "$KUBE_CONTEXT" config view --minify \
    -o jsonpath='{.clusters[0].cluster.server}') || return
  jq -e --arg endpoint "$endpoint" --slurpfile before "$WORK_DIR/cluster-before.json" '
    .cluster.arn == $before[0].cluster.arn and
    .cluster.createdAt == $before[0].cluster.createdAt and
    .cluster.endpoint == $endpoint and .cluster.status == "ACTIVE"
  ' "$WORK_DIR/cluster-current.json" >/dev/null
}
guard_nodegroup() {
  guard_context || return
  aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$OLD_NODEGROUP" \
    --region "$AWS_REGION" --output json > "$WORK_DIR/nodegroup-current.json" || return
  jq -e --slurpfile before "$WORK_DIR/nodegroup-before.json" '
    .nodegroup.nodegroupArn == $before[0].nodegroup.nodegroupArn and
    .nodegroup.createdAt == $before[0].nodegroup.createdAt and .nodegroup.status == "ACTIVE"
  ' "$WORK_DIR/nodegroup-current.json" >/dev/null
}
guard_nodegroup
printf 'Private migration evidence: %s\n' "$WORK_DIR"
```

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s \
  get deployments,statefulsets,daemonsets,jobs,cronjobs -A -o json |
jq '[.items[] | (.spec.template // .spec.jobTemplate.spec.template) as $t |
 {kind,namespace:.metadata.namespace,name:.metadata.name,uid:.metadata.uid,
  nodeSelector:$t.spec.nodeSelector,affinity:$t.spec.affinity,tolerations:$t.spec.tolerations,
  serviceAccountName:$t.spec.serviceAccountName,hostNetwork:$t.spec.hostNetwork,
  pvcNames:[$t.spec.volumes[]?.persistentVolumeClaim.claimName // empty]}]' \
  > "$WORK_DIR/workload-placement.json"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pods -A -o json |
jq '[.items[] | {namespace:.metadata.namespace,name:.metadata.name,node:.spec.nodeName,
  phase:.status.phase,deletionTimestamp:.metadata.deletionTimestamp,
  ready:([.status.conditions[]?|select(.type=="Ready")|.status]|first // "NotReported"),
  owners:[.metadata.ownerReferences[]?|{kind,name,controller}]}]' \
  > "$WORK_DIR/pod-state.json"
```

これらのファイルには運用メタデータが含まれるため、復旧に備えて保持してください。クエリが失敗した場合は、失敗として扱います。`kubectl top` には正常に動作する Metrics API が必要です。また、現在の CPU スナップショットはワークロードの履歴の代わりにはなりません。

| 既存の設定 | 移行時の考慮事項 |
|------------------------|-------------------------|
| カスタム AMI、ブートストラップ、ユーザーデータ | Auto Mode では任意の AL2023 AMI、カスタム AMI、userData ではなく、管理された Bottlerocket を使用します |
| ノード IAM 権限 | ノードロール、インスタンスプロファイル、アクセスエントリを準備します。ワークロードの権限は、ノードロールや IMDS へのフォールバックではなく、レビュー済みの IRSA または Pod Identity に移行します |
| クラスター IAM ロール | 既存ロールに Auto Mode 用の権限と信頼設定を追加します。CLI で有効化しても、必要なロールがすべて自動作成されるわけではありません |
| セレクター、アフィニティ、テイント | Deployment、StatefulSet、DaemonSet、Job、CronJob を含めて確認し、競合する配置条件を意図的に解消します |
| 代替 CNI、ネットワーク設定 | 有効化前に文書化された互換性を確認します。非対応のネットワーク設定は NodeClass では修復されません |
| スケーリング、IaC の所有関係 | Cluster Autoscaler、GitOps、元の IaC 管理者と調整し、移行による変更が元に戻されないようにします |

### データ、ロードバランサー、混在ノードの DNS

ドライバーとコントローラーのインターフェイスは異なります。

| リソース | セルフマネージド | Auto Mode |
|----------|--------------|-----------|
| EBS StorageClass のプロビジョナー | `ebs.csi.aws.com` | `ebs.csi.eks.amazonaws.com` |
| NLB Service の loadBalancerClass | `service.k8s.aws/nlb` | `eks.amazonaws.com/nlb` |
| ALB IngressClass の controller | `ingress.k8s.aws/alb` | `eks.amazonaws.com/alb` |
| TargetGroupBinding の apiVersion | `elbv2.k8s.aws/v1beta1` | `eks.amazonaws.com/v1` |
| コンピュートクラス | `karpenter.k8s.aws/v1 EC2NodeClass` | `eks.amazonaws.com/v1 NodeClass` |

既存の PVC は StorageClass 名を書き換えてもドライバーが切り替わりません。また、既存のロードバランサーが管理対象コントローラーに自動で引き継がれることもありません。EBS では、検証済みのバックアップ／スナップショット復元計画、または AWS の現行ドキュメントにある **ワークロード停止、Retain、静的 PV/PVC の再作成** 手順を使用してください。後者は EBS ボリュームを再利用しますが、Kubernetes のバインディングオブジェクトを作り直す方法であり、ドライバーをその場で切り替えるものではありません。バックアップからの復元、ボリューム、AZ、KMS の所有関係、回収ポリシー、finalizer、バインディング、アプリケーションの整合性を確認してください。ここでは破壊的なボリューム移行スクリプトを提供しません。

セルフマネージドの AWS Load Balancer Controller がリソースを所有している間は、そのコントローラーを稼働させてください。旧ロードバランサーを廃止する前に、新しい管理対象ロードバランサーを作成してテストし、レビュー済みの Blue/Green DNS 計画でトラフィックを切り替えます。クラスの変更可否、アノテーション、TargetGroupBinding の所有関係は個別に確認してください。API グループを書き換えても、安全に引き継げるわけではありません。

Auto Mode ノードではノードローカル DNS を使用します。**Auto Mode 以外のノードが CoreDNS を必要とする間は、CoreDNS Deployment を残してください。** 残っているノード種別に必要な CNI、プロキシ、ストレージ、ID エージェントも維持し、配置先を限定します。Auto Mode のコンポーネントが管理されるからといって、混在クラスターの依存関係を早期に削除してよいわけではありません。

## 2. 制限のないデフォルトプールを作らずに Auto Mode を有効にする

まず[開始方法](./01-getting-started.md)の IAM とアクセス準備を完了してください。既存のクラスター IAM ロールには、文書化された Compute、**BlockStoragePolicyV2**、LoadBalancing、Networking、Cluster ポリシーと、必要な `sts:TagSession` 信頼設定が必要です。この例では、API または API_AND_CONFIG_MAP 認証と、EC2 アクセスエントリを設定したカスタムノードロール／プロファイルを前提にしています。

この段階的な手順では、**組み込みプールを作りません**。そのため、次のステップで独自の NodeClass を作成します。`default` が存在すると想定しないでください。制限のない汎用プールを有効にすると、意図した切り替えより前に既存の保留中ワークロードがスケジュールされる可能性があります。この例は、Auto Mode がすでに動作しているクラスターのプール一覧を置き換えず、処理を拒否します。

完了を待つ際は、個別の更新 ID を使ってください。クラスターが `ACTIVE` であるだけでは、この設定更新の成功を証明できません。

```bash
wait_eks_update() {
  local id="$1" group="${2:-}" attempt status
  local extra=()
  test -n "$group" && extra=(--nodegroup-name "$group")
  for ((attempt=0; attempt<120; attempt++)); do
    aws eks describe-update --name "$CLUSTER_NAME" --region "$AWS_REGION" \
      --update-id "$id" "${extra[@]}" --output json > "$WORK_DIR/update-current.json" || return
    status=$(jq -er '.update.status' "$WORK_DIR/update-current.json") || return
    case "$status" in
      Successful) return 0 ;;
      Failed|Cancelled)
        jq '{id:.update.id,status:.update.status,errorCodes:[.update.errors[]?.errorCode]}' \
          "$WORK_DIR/update-current.json" >&2
        return 1 ;;
      InProgress) sleep 10 ;;
      *) printf 'Unknown update state; inspect saved evidence.\n' >&2; return 1 ;;
    esac
  done
  printf 'Update still unconfirmed; stop and retain its ID.\n' >&2
  return 1
}
```

```bash
guard_context
jq -e '.cluster.computeConfig.enabled != true and
       (.cluster.accessConfig.authenticationMode == "API" or
        .cluster.accessConfig.authenticationMode == "API_AND_CONFIG_MAP")' \
  "$WORK_DIR/cluster-current.json" >/dev/null
jq -n --arg name "$CLUSTER_NAME" '{
  name:$name,
  computeConfig:{enabled:true,nodePools:[]},
  storageConfig:{blockStorage:{enabled:true}},
  kubernetesNetworkConfig:{elasticLoadBalancing:{enabled:true}}
}' > "$WORK_DIR/enable-request.json"
aws eks update-cluster-config --region "$AWS_REGION" \
  --cli-input-json "file://$WORK_DIR/enable-request.json" --output json \
  > "$WORK_DIR/enable-response.json"
update_id=$(jq -er '.update.id' "$WORK_DIR/enable-response.json")
wait_eks_update "$update_id"
guard_context
jq -e '.cluster.computeConfig.enabled == true and
       .cluster.computeConfig.nodePools == [] and
       .cluster.storageConfig.blockStorage.enabled == true and
       .cluster.kubernetesNetworkConfig.elasticLoadBalancing.enabled == true' \
  "$WORK_DIR/cluster-current.json" >/dev/null
```

コンピュート、ブロックストレージ、管理対象ロードバランシングは、まとめて有効化または無効化する必要があります。リクエストの形式検証が成功しても、IAM やサービス側で受け付けられるとは限りません。エラーで停止し、更新の証跡を保持してください。応答が不明瞭な場合に、確認せず再実行してはいけません。認証モードの変更には、別途移行とロールバックの制約があります。

## 3. 選択的なプールを作成し、両方の環境でテストする

NodeClass のプロファイル、サブネット、セキュリティグループのプレースホルダーは、レビュー済みの既存リソースに置き換えてください。プロファイルのロールには適切なノードアクセスエントリが必要です。これらのマニフェストは IAM、VPC、アプリケーション認証情報を作成しません。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: migration-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
---
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: migration-nodeclass
spec:
  instanceProfile: eks-migration-node-profile
  subnetSelectorTerms:
  - tags:
      Name: private-subnet
  securityGroupSelectorTerms:
  - tags:
      Name: worker-restricted
  advancedNetworking:
    associatePublicIPAddress: false
  ephemeralStorage:
    size: 100Gi
    iops: 3000
    throughput: 125
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: migration-pool
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: migration-nodeclass
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: migration
        value: auto-mode
        effect: NoSchedule
    metadata:
      labels:
        migration: auto-mode
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 2m
    budgets:
    - nodes: '1'
  limits:
    cpu: '32'
    memory: 128Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: legacy-canary
  namespace: migration-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: legacy-canary
  template:
    metadata:
      labels:
        app: legacy-canary
    spec:
      containers:
      - name: web
        image: nginxinc/nginx-unprivileged:1.30.6@sha256:455cebcadcac0b597cdeaab077d93fb8ad59a98f7ed001dcf8f8693154b5d3d3
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        ports:
        - containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        readinessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 5
      terminationGracePeriodSeconds: 60
      automountServiceAccountToken: false
      nodeSelector:
        eks.amazonaws.com/nodegroup: REPLACE_WITH_OLD_NODEGROUP
      tolerations: []
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 128Mi
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auto-canary
  namespace: migration-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: auto-canary
  template:
    metadata:
      labels:
        app: auto-canary
    spec:
      containers:
      - name: web
        image: nginxinc/nginx-unprivileged:1.30.6@sha256:455cebcadcac0b597cdeaab077d93fb8ad59a98f7ed001dcf8f8693154b5d3d3
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        ports:
        - containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        readinessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 5
      terminationGracePeriodSeconds: 60
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: migration-pool
        eks.amazonaws.com/compute-type: auto
      tolerations:
      - key: migration
        operator: Equal
        value: auto-mode
        effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 128Mi
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
```

レガシー側のカナリアを使う前に、`REPLACE_WITH_OLD_NODEGROUP` を置き換えてください。完全な nginx の例では、運用の章でレビュー済みの非 root イメージとセキュリティコンテキストを使用します。ここで確認するのは基本的な配置と Ready 状態であり、アプリケーションの状態、ID、トラフィック経路ではありません。

Auto Mode のカナリアは、対象プールと `eks.amazonaws.com/compute-type=auto` の両方を指定します。`karpenter.sh/nodepool` の存在だけでは、セルフマネージド Karpenter ノードにも一致します。テイント許容設定は配置を許可するだけで、それ単独ではプールを選択しません。

| MNG の設定 | Auto Mode での対応 |
|-------------|-------------------|
| インスタンスタイプ、キャパシティタイプ | 正確なインスタンス要件または意図的に広げたカテゴリと、キャパシティタイプ要件 |
| ラベル、テイント | `spec.template.metadata.labels` / `spec.template.spec.taints` |
| 最小、希望、最大ノード数 | CPU／メモリの `spec.limits` と同等ではありません。希望台数を固定する必要がある場合は、静的プールの意味を別途検討してください |
| サブネット、セキュリティグループ | カスタム NodeClass のセレクターとレビュー済みのルール |
| AMI、ブートストラップ | Auto Mode では任意の AMI ファミリーや userData に対応するマッピングはありません |

## 4. 段階ごとに移行し、失敗時は停止する

まずリスクの低い代表的なワークロードから始め、依存関係の検証後にステージング／重要度の低い本番環境、最後に重要なワークロードへ進みます。ライブ Pod だけでなく、**所有元のコントローラーまたは GitOps の期待状態**を変更してください。

配置ポリシー全体を確認します。Auto のセレクターを追加しても、古いノードグループのセレクターを残すと、条件の積み合わせでスケジュール不能になる場合があります。無関係な Pod アフィニティ、セキュリティ上の配置条件、許容設定を `affinity: null` で消してはいけません。StatefulSet、実行中の Job、ローカルボリュームを使うワークロードには、それぞれデータを考慮した手順が必要です。

Deployment のレプリカ数がゼロでない場合、次のコマンドでロールアウトと観測されたレプリカの Ready 状態を確認できます。

```bash
: "${WORKLOAD_NAMESPACE:?Select the namespace}"
: "${DEPLOYMENT_NAME:?Select one migrated Deployment}"
kubectl --context "$KUBE_CONTEXT" -n "$WORKLOAD_NAMESPACE" rollout status \
  "deployment/$DEPLOYMENT_NAME" --timeout=10m
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$WORKLOAD_NAMESPACE" \
  get deployment "$DEPLOYMENT_NAME" -o json |
jq -e '(.spec.replicas // 1) as $desired |
  $desired > 0 and .status.observedGeneration >= .metadata.generation and
  .status.updatedReplicas == $desired and .status.readyReplicas == $desired and
  .status.availableReplicas == $desired' >/dev/null
```

実際のリクエスト、DNS、ロードバランサーのターゲット、ボリュームの読み書き、ID、ログ／メトリクス、アプリケーションの SLO も確認してください。Deployment のローリング更新設定と PDB による Eviction API の保護は別の制御です。`rollout status` の成功や Pod の `Running` 状態だけでは、エンドツーエンドの可用性を証明できません。完了済みの Job は `Succeeded` で正常な場合があります。

### オプション: ノードを1台ずつドレインする

置き換え先のキャパシティ、ワークロードの配置、PDB、データ耐久性を確認した後に限り、古い管理対象ノードを1台選び、記録済みの UID を指定してください。

```bash
: "${NODE_NAME:?Select exactly one old managed node}"
: "${EXPECTED_NODE_UID:?Set its previously reviewed UID}"
guard_nodegroup
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get node "$NODE_NAME" -o json \
  > "$WORK_DIR/node-before-drain.json"
jq -e --arg uid "$EXPECTED_NODE_UID" --arg group "$OLD_NODEGROUP" '
  .metadata.uid == $uid and .metadata.labels["eks.amazonaws.com/nodegroup"] == $group and
  .metadata.labels["eks.amazonaws.com/compute-type"] != "auto" and
  .metadata.deletionTimestamp == null and
  any(.status.conditions[]?; .type=="Ready" and .status=="True")
' "$WORK_DIR/node-before-drain.json" >/dev/null
kubectl --context "$KUBE_CONTEXT" drain "$NODE_NAME" --ignore-daemonsets --timeout=10m
printf 'Drain returned successfully. Validate application health before selecting another node.\n'
```

一括で cordon／drain するループ、固定時間の sleep を使ったヘルス判定、失敗後も続行する処理はありません。デフォルトの drain は、未管理 Pod や local emptyDir データを、意図的に対処しない限り拒否します。失敗を消すために `--force`、`--disable-eviction`、`--delete-emptydir-data` を追加してはいけません。ドレインが失敗または中断するとノードが cordon のまま残る場合があります。状態を確認し、復旧計画が求める場合に限ってスケジューリングを戻してください。次のノードを選ぶ前に、影響を受けたアプリケーションを検証します。

## 5. 古いワークロードがなくなってからスケールダウンする

**MNG の希望台数を変更しても PDB は尊重されません。** EKS は ASG のスケールダウンを行います。これは、通常の管理対象ノードグループのバージョン更新時の drain とは異なります。希望台数を半分にして5分待つ方法は、安全な安定化手順ではありません。

元のスケーリング／IaC 管理者と調整し、古いノードへの新たなアプリケーション配置を防いでください。API の例は、観測された古いノードがすべて cordon 済みで、アクティブな非 DaemonSet Pod がないことを確認したうえで、最小台数と希望台数をゼロにします。cordon を無視するコントローラーやノードを置き換えるコントローラーとの競合までは防げません。移行用の配置制御は引き続き有効にしてください。残る DaemonSet とシステム依存関係を確認し、必要な完了済み Job の成果物は先にエクスポートします。

```bash
guard_nodegroup
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l "eks.amazonaws.com/nodegroup=$OLD_NODEGROUP" -o json > "$WORK_DIR/old-nodes.json"
jq -e 'all(.items[]; .spec.unschedulable == true)' "$WORK_DIR/old-nodes.json" >/dev/null
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pods -A -o json \
  | jq '{items:[.items[]|{metadata:{name:.metadata.name,namespace:.metadata.namespace,
         ownerReferences:.metadata.ownerReferences},spec:{nodeName:.spec.nodeName},
         status:{phase:.status.phase}}]}' > "$WORK_DIR/pods-before-scale.json"
jq --slurpfile nodes "$WORK_DIR/old-nodes.json" '
  ($nodes[0].items|map(.metadata.name)) as $names |
  [.items[] | select(.spec.nodeName as $n | $names|index($n)) |
   select(.status.phase!="Succeeded" and .status.phase!="Failed") |
   select(any(.metadata.ownerReferences[]?; .kind=="DaemonSet" and .controller==true)|not) |
   {namespace:.metadata.namespace,name:.metadata.name,phase:.status.phase}]
' "$WORK_DIR/pods-before-scale.json" > "$WORK_DIR/old-active-workloads.json"
jq -e 'length == 0' "$WORK_DIR/old-active-workloads.json" >/dev/null

guard_nodegroup
aws eks update-nodegroup-config --cluster-name "$CLUSTER_NAME" --nodegroup-name "$OLD_NODEGROUP" \
  --region "$AWS_REGION" --scaling-config minSize=0,desiredSize=0 --output json \
  > "$WORK_DIR/scale-zero-response.json"
update_id=$(jq -er '.update.id' "$WORK_DIR/scale-zero-response.json")
wait_eks_update "$update_id" "$OLD_NODEGROUP"
```

実際の旧ノードとインスタンスが消えたことを待ち、アプリケーションの健全性を再確認してください。合意したロールバック期間中は、ノードグループ定義と記録済みのスケーリング設定を保持します。希望キャパシティをゼロにしても、直ちに復旧可能なキャパシティが保証されるわけではありません。

## 6. 元の所有者を通じて旧インフラを廃止する

ワークロード、データ、トラフィックの検証が成功し、意図した安定化期間を経た後に、旧グループを**元の所有者**（Terraform、CloudFormation、eksctl、その他の管理手順）を通じて削除します。IaC が所有するグループを EKS API から直接削除すると、ドリフト、スタック、IAM ロールなどのリソースが残ることがあります。

次の例は、レビュー済みの**直接 API で管理している**グループに限って使用します。希望台数がゼロであることを必須とし、ノードとワークロードの状態を再確認し、CloudFormation の所有を示すタグが見つかった場合は処理を拒否します。このチェックですべての外部 IaC 所有者を発見できるとは限りません。実行前に所有関係を確認してください。

```bash
guard_nodegroup
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l "eks.amazonaws.com/nodegroup=$OLD_NODEGROUP" -o json > "$WORK_DIR/old-nodes.json"
jq -e 'all(.items[]; .spec.unschedulable == true)' "$WORK_DIR/old-nodes.json" >/dev/null
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pods -A -o json \
  | jq '{items:[.items[]|{metadata:{name:.metadata.name,namespace:.metadata.namespace,
         ownerReferences:.metadata.ownerReferences},spec:{nodeName:.spec.nodeName},
         status:{phase:.status.phase}}]}' > "$WORK_DIR/pods-before-scale.json"
jq --slurpfile nodes "$WORK_DIR/old-nodes.json" '
  ($nodes[0].items|map(.metadata.name)) as $names |
  [.items[] | select(.spec.nodeName as $n | $names|index($n)) |
   select(.status.phase!="Succeeded" and .status.phase!="Failed") |
   select(any(.metadata.ownerReferences[]?; .kind=="DaemonSet" and .controller==true)|not) |
   {namespace:.metadata.namespace,name:.metadata.name,phase:.status.phase}]
' "$WORK_DIR/pods-before-scale.json" > "$WORK_DIR/old-active-workloads.json"
jq -e 'length == 0' "$WORK_DIR/old-active-workloads.json" >/dev/null

: "${NODEGROUP_MANAGEMENT:?Use the original IaC owner, or explicitly set direct-api for an API-managed group}"
test "$NODEGROUP_MANAGEMENT" = direct-api
guard_nodegroup
jq -e '.nodegroup.scalingConfig.desiredSize == 0 and
  ((.nodegroup.tags // {} | keys | map(select(startswith("aws:cloudformation:"))) | length) == 0)' \
  "$WORK_DIR/nodegroup-current.json" >/dev/null
aws eks delete-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$OLD_NODEGROUP" \
  --region "$AWS_REGION" --output json > "$WORK_DIR/delete-nodegroup-response.json"
aws eks wait nodegroup-deleted --cluster-name "$CLUSTER_NAME" --nodegroup-name "$OLD_NODEGROUP" \
  --region "$AWS_REGION"
```

削除待機処理が成功する必要があります。AccessDenied、認証情報の期限切れ、その他のクエリ失敗は、対象が存在しないことを意味しません。別途所有されている IAM、ネットワーク、ストレージのリソースと請求を監査してください。ノードグループ API オブジェクトを削除しても、関連コストがすべて終了した証明にはなりません。以前の1～2週間という安定化期間の例は計画上の選択肢であり、普遍的な要件ではありません。

## 7. 最終検証と最適化

移行の各段階の検証記録を保持し、クリーンアップ後に最終監査を実施します。想定したコントローラーと Pod の Ready 状態、配置、PVC の健全性、DNS、アプリケーショントラフィック、IAM、ログ／メトリクス、コスト配賦を確認してください。共存中は両方のコンピュート群と、場合によっては両方のロードバランサーに料金が発生するため、その間のコストも追跡します。

以前示されていた Pending 0～5／5分を超えて10より大、起動時間90秒未満／120秒超、可用性99.9%超／99.5%未満、API 応答200ms未満／500ms超という値は、未検証の参考しきい値です。Auto Mode の既定メトリクスだと思い込まず、実際のメトリクス提供元、アプリケーション目標、測定済みのベースラインを使用してください。

## セルフマネージド Karpenter との共存

AWS は直接的な共存移行をサポートしています。前提条件の **v1.1** は移行機能の最低バージョンです。現在の Kubernetes 互換性一覧も満たしてください（たとえば Kubernetes 1.36 には Karpenter 1.13 以上が必要です）。既存のコントローラーを稼働させたまま、別のテイント付き Auto Mode プールを作り、選択したワークロード群を移行します。

移行中に共有の `nodepools.karpenter.sh` や `nodeclaims.karpenter.sh` CRD を変更または削除しないでください。汎用の Karpenter ラベルではなく、クラス参照と対象プールを使って所有関係を記録します。古いワークロードがなくなった後、コントローラーが finalization を完了できる間に、旧環境が所有する NodePool／NodeClaim だけを廃止します。インスタンスと依存リソースのクリーンアップを確認してから、セルフマネージドのリリースと、それが所有する IAM／キューのリソースだけをアンインストールしてください。先にアンインストールしたり、リソースのクリーンアップの代わりに namespace を削除したりしないでください。

## Auto Mode のキャパシティを除去する前に、ロールバックで旧キャパシティと配置を戻す

これは**ワークロード／インフラの移行ロールバック**であり、Kubernetes コントロールプレーンのバージョンロールバックではありません。

1. Auto プールはそのままにして、まず互換性のある旧キャパシティを復元または用意します。旧グループを削除済みの場合、保存したスケーリング JSON だけでは再作成できません。
2. 記録したスケーリング値を現在のワークロード需要に照らして確認します。同一の識別情報を持つ既存グループには、次の設定で以前の値を復元できます。

```bash
guard_nodegroup
jq --arg name "$CLUSTER_NAME" --arg group "$OLD_NODEGROUP" '{
  clusterName:$name,nodegroupName:$group,scalingConfig:.nodegroup.scalingConfig
}' "$WORK_DIR/nodegroup-before.json" > "$WORK_DIR/restore-capacity-request.json"
aws eks update-nodegroup-config --region "$AWS_REGION" \
  --cli-input-json "file://$WORK_DIR/restore-capacity-request.json" --output json \
  > "$WORK_DIR/restore-capacity-response.json"
update_id=$(jq -er '.update.id' "$WORK_DIR/restore-capacity-response.json")
wait_eks_update "$update_id" "$OLD_NODEGROUP"
```

3. 十分な数の旧ノードが Ready になり、ネットワーク、DNS、ID、ストレージのエージェントが動作するまで待ちます。更新成功のステータスだけでは、Pod のキャパシティが準備できた証拠になりません。まだ存在する旧ノードの cordon を解除する前に、ノード UID を確認してください。
4. レビュー済みのコントローラー配置、トラフィック、データの計画を戻します。無関係なアフィニティを保ったまま、競合する Auto セレクターを明示的に除去します。旧環境で実際のワークロードの Ready 状態とアプリケーション動作を検証します。
5. その後に限り、移行で作成した Auto プール／リソースを、所有者を通じて廃止します。NodePool の削除はノードのカスケード削除につながる場合があります。ロールバックの最初の操作として削除したり、Karpenter ラベルだけで全ノードを選択したりしないでください。

Auto Mode を無効にするかどうかは任意であり、別の操作です。まず Auto Mode が所有するコンピュート、ストレージ、ロードバランサーの依存関係をすべて解消してください。この変更が適切であれば、3つのフラグを1つのリクエストに含めます。次のコードはレビュー用のリクエストファイルを準備するだけです。

```bash
jq -n --arg name "$CLUSTER_NAME" '{
  name:$name,
  computeConfig:{enabled:false},
  storageConfig:{blockStorage:{enabled:false}},
  kubernetesNetworkConfig:{elasticLoadBalancing:{enabled:false}}
}' > "$WORK_DIR/disable-request.json"
```

必要に応じて、コンテキスト確認と更新 ID の追跡を含むレビュー済み手順で送信します。Auto Mode を無効にしても、アプリケーションのセレクター、データ、トラフィックは復元されず、認証モードの変更も元に戻りません。

## 参考資料

- [既存クラスターで Auto Mode を有効にする](https://docs.aws.amazon.com/eks/latest/userguide/auto-enable-existing.html)
- [移行リファレンス: EBS とロードバランサー](https://docs.aws.amazon.com/eks/latest/userguide/migrate-auto.html)
- [管理対象ノードグループの移行](https://docs.aws.amazon.com/eks/latest/userguide/auto-migrate-mng.html)
- [セルフマネージド Karpenter の移行](https://docs.aws.amazon.com/eks/latest/userguide/auto-migrate-karpenter.html)
- [管理対象ノードグループのスケーリングと PDB の動作](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html)
- [Auto Mode のネットワークと混在ノードの DNS](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [NodeClass の ID とアクセスエントリ](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [Karpenter と Kubernetes の互換性](https://karpenter.sh/docs/upgrading/compatibility/)
- [Kubernetes ノードを安全にドレインする](https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/)
- [Kubernetes Pod disruption](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)

< [前へ: ワークロードの最適化](./08-workload-optimization.md) | [目次](./README.md) | [EKS トピックに戻る](../README.md) >

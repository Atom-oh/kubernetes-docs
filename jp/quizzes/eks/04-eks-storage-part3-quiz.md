# EKS ストレージ Part 3 クイズ

> **最終更新日**: 2026年9月11日

この章で設定した collector とストレージの例を使って、監視、診断、コスト、セキュリティを確認します。以下の例はローカルで確認したものであり、AWS 操作、本番環境での復旧、稼働中のダッシュボードを検証した結果を示すものではありません。デプロイ前にプレースホルダーを置き換え、リソースの所有者を確認してください。

## 選択式問題

### 1. VolumeReadOps から読み取り IOPS を計算する方法はどれですか？

- A. Average をそのまま IOPS として使う
- B. Sum を期間の秒数で割る
- C. バイト数に Pod 数を掛ける
- D. VolumeQueueLength を完了済み IOPS として使う

<details>
<summary>解答を表示</summary>

**正解: B**

Sum を期間の秒数で割ります。VolumeReadBytes/VolumeWriteBytes も同様に正規化して bytes/s を求めます。VolumeTotalReadTime/VolumeTotalWriteTime は累積された操作時間（秒）です。対応する操作の Sum で割ると平均秒/操作になり、操作数がゼロの場合は別途処理が必要です。生のカウンターをすべてレートやレイテンシーとして扱わないでください。

現在の Nitro メトリクスには、文書化された単位や制約を持つ VolumeAvgIOPS、VolumeAvgThroughput、平均レイテンシーのメトリクスもあります。BurstBalance は gp2/st1/sc1 に適用され、gp3 には適用されません。EFS の byte/metered-byte メトリクスと FSx の OSS/OST ごとのメトリクスでは、ディメンションや統計量が異なります。対応している環境では kubelet_volume_stats_* からファイルシステム使用量を取得できる場合がありますが、container_fs_usage_bytes はあらゆる PVC に共通する測定値ではありません。

</details>

### 2. Pending の PVC や consumer について、最初に確認することはどれですか？

- A. PVC をすぐに削除する
- B. すべてのノードに EC2 の完全なアクセス権を与える
- C. イベント、binding mode、スケジューリング制約を調べる
- D. 未バインドの PVC が AZ をすでに固定していると考える

<details>
<summary>解答を表示</summary>

**正解: C**

実際の namespace、claim、consumer のイベント、StorageClass、トポロジーを調べます。WaitForFirstConsumer は、スケジューリングまで新しい PVC を Pending のままにすることがあります。これは必ずしも driver の障害ではありません。バインド後は、EBS PV の node affinity/AZ とアタッチ上限が重要です。バインドに必要なスケジューラーを迂回する spec.nodeName の使用は避けてください。

```bash
set -euo pipefail
: "${NAMESPACE:?Set the workload namespace}"
: "${PVC_NAME:?Set the claim name}"
: "${POD_NAME:?Set its intended consumer Pod}"
kubectl -n "$NAMESPACE" get pvc "$PVC_NAME" -o yaml
kubectl -n "$NAMESPACE" describe pvc "$PVC_NAME"
kubectl -n "$NAMESPACE" describe pod "$POD_NAME"
kubectl get storageclass
kubectl get nodes -L topology.kubernetes.io/zone
```



```bash
set -euo pipefail
: "${CSI_CONTROLLER_POD:?Select the actual controller Pod}"
: "${CSI_CONTAINER:?Select the relevant driver/sidecar container}"
kubectl -n kube-system get pod "$CSI_CONTROLLER_POD" \
  -o jsonpath='{.spec.containers[*].name}'
kubectl -n kube-system logs "$CSI_CONTROLLER_POD" -c "$CSI_CONTAINER" --since=15m --tail=200
```

CSI driver の実際の Pod Identity/IRSA ロールと KMS grant を確認してください。EC2 ノードの instance profile だけを見ても十分ではありません。複数コンテナを持つ controller では、対象の driver/sidecar を選んでログを確認します。ContainerCreating の原因は、アタッチ、マウント、クライアントソフトウェア、イメージ取得、アプリケーション権限の場合もあります。症状をリセットするためにデータを削除しないでください。

</details>

### 3. データベースのストレージを調整する方法として適切なのはどれですか？

- A. 測定し、ボリューム、ファイルシステム、インスタンスの制約に合わせる
- B. 常に multiAttach:true を有効にする
- C. どの hostPath も高速な NVMe だとみなす
- D. 対象を特定せずルートディスクの scheduler を変更する

<details>
<summary>解答を表示</summary>

**正解: A**

I/O パターン、キュー、レイテンシー、インスタンス上限を測定してから、ストレージと性能の設定を選んでください。この 10,000 IOPS io2 クラスは説明用の割り当て例であり、データベースの SLO を満たす証拠ではありません。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: io2
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
  iops: '10000'
```

Multi-Attach は、汎用の読み取り専用性能スイッチではありません。レビュー済みの EBS CSI 経路では、Part 2 に記載されたとおり、io2、RWX、raw Block とアプリケーション側の協調制御を使います。/mnt/instance-store という名前の hostPath だけでは、物理的な instance store であることは確認できません。準備済みのノードローカルストレージ設計を使い、そのデータは一時的なものとして扱ってください。EC2 instance-store CSI は実際にサポートされている統合機能ですが、独自の前提条件があります。

対象が nvme0n1 だと決めつけて noop を設定しないでください。それがルートディスクや別のディスクである可能性があり、最新の blk-mq ではデバイス名も異なります。個別に変更を検討する前にデバイスとサポート対象の scheduler を特定してください。ファイルシステムの選択やマウントオプションにもワークロードの根拠が必要です。XFS も ext4 も性能結果を保証しません。

</details>

### 4. デフォルトの gp3 StorageClass を作成すると、既存の gp2 ボリュームも移行されますか？

- A. はい、アタッチ済みの全ボリュームが直ちに変更される
- B. はい、StorageClass の名前を変更した後に限られる
- C. はい、デフォルトの StorageClass が既存データを暗号化して移行する
- D. いいえ。既存ボリュームには別途、サポートされた手順が必要

<details>
<summary>解答を表示</summary>

**正解: D**

移行されません。StorageClass は適用対象のプロビジョニングを制御するもので、すでにバインド済みの PV/backend を書き換えるものではありません。デフォルト StorageClass の変更は、無関係な新規 claim に影響することがあります。所有者が明確なサポート対象の変更またはデータ移行を選び、復旧ポイントを保持してアプリケーションデータを検証してください。容量拡張と容量縮小は別の操作です。一般に PVC/EBS のサイズをインプレースで縮小することはできません。

割り当て容量、プロビジョニング済み IOPS/throughput、保持期間、リクエスト、転送コストを比較してください。コンピューティングの割引で別料金のストレージ費用が自動的に下がるわけではありません。VolumeSnapshotClass はスケジュール機能ではありません。以下の例は、意図的に一時利用する snapshot の削除動作だけを定義します。

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: temporary-ebs-snapshots
driver: ebs.csi.aws.com
deletionPolicy: Delete
```

コスト最適化のために、この一時用 StorageClass で章の保持用クラスを一括置換しないでください。バックアップの所有者が保持期間をスケジュールし、管理する必要があります。Velero には独自の CSI snapshot ライフサイクルがあります。

</details>

### 5. ストレージのセキュリティ制御を正しく分けて説明しているのはどれですか？

- A. PVC 名だけで暗号化が保証される
- B. 各制御には、それぞれ正しい適用範囲と実際のリソース対応付けが必要
- C. Role により、すべてのクラスタースコープ PV 権限を付与できる
- D. PSS が IAM と KMS の代わりになる

<details>
<summary>解答を表示</summary>

**正解: B**

IAM/KMS、ネットワークアクセス、Kubernetes API 認可、admission、ファイルシステムの identity は、それぞれ異なる操作を保護します。リージョン指定の EC2 action 一覧だけで、CSI に必要な最小権限ポリシー全体を満たすとは限りません。実際の driver ロールのポリシーと必要な key grant を確認してください。存在しない kmsKeyId を指定しても KMS key は作成されません。

namespace 単位の Role で PVC へのアクセス権は付与できますが、クラスタースコープの PV への権限は付与できません。この Role を通じて PVC オブジェクトを読めない Pod 作成者であっても、namespace 内の PVC をマウントできる場合があります。ワークロードの作成権限と tenant の境界も保護してください。この章の namespace reader は、オブジェクトを調査する例です。

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: storage-auditor
  namespace: storage-demo
automountServiceAccountToken: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pvc-reader
  namespace: storage-demo
rules:
- apiGroups:
  - ''
  resources:
  - persistentvolumeclaims
  verbs:
  - get
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pvc-reader
  namespace: storage-demo
subjects:
- kind: ServiceAccount
  name: storage-auditor
  namespace: storage-demo
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: pvc-reader
```

EFS の SG は、実在する mount target/client に適用されます。架空の securityGroupSelector 断片に適用されるわけではありません。実際の TCP 2049 経路を使ってください。Lustre/EFA のルールは異なります。Pod Security Standards は、クラウド暗号化や IAM 権限を構成するものではありません。

</details>

### 6. 監視統合について正しい説明はどれですか？

- A. Grafana ConfigMap が PVC メトリクスを自動収集する
- B. Prometheus はデータを常に無期限に保持する
- C. collector、service discovery、認可、ストレージを構成する必要がある
- D. CloudWatch はカスタムメトリクスを受け取れない

<details>
<summary>解答を表示</summary>

**正解: C**

CloudWatch は AWS ネイティブのサービスメトリクスを扱い、Prometheus は構成した Kubernetes/application の target から収集し、Grafana は構成済みのデータソースを可視化します。collector、service discovery、IAM/auth、保持期間、label、alert routing は別途構成が必要です。ダッシュボード ConfigMap だけでは、存在しないメトリクスは生成されません。

CloudWatch は構成済みの agent/integration 経由でカスタム/Kubernetes メトリクスを取り込めます。また、Prometheus が自動的に長期間保持するわけではありません。ワークロードに合った保持期間とストレージ/remote-write 構成を使ってください。自動管理は、無条件の変更ではなく、観測と範囲を限定した提案から始めます。

</details>

### 7. どの観測結果だけでボリュームの削除を承認できますか？

- A. PV が Available である
- B. 現在一覧に表示される Pod が PVC を参照していない
- C. lastUsed annotation の日時が古い
- D. どれも単独では承認できない

<details>
<summary>解答を表示</summary>

**正解: D**

保持データ、scale-to-zero controller、今後実行される Job、バックアップ義務、外部の所有者を考慮する必要があります。lastUsed は、信頼できる標準 PVC 使用フィールドではありません。削除前に namespace/UID を保全し、backend の identity を確認してください。

</details>

### 8. kubectl top pods で PVC のディスク使用量を測定できますか？

- A. いいえ。主に CPU/メモリを報告する
- B. はい。メモリ使用量とディスク使用量は同じ
- C. はい。EBS の空き block をすべて一覧表示する
- D. StorageClass の名前が gp3 の場合に限り測定できる

<details>
<summary>解答を表示</summary>

**正解: A**

正しい mount path/driver の、サポートされたファイルシステム統計を使い、実際の PVC を特定してください。コンテナ内の df が別の mount や共有 EFS ファイルシステムを示すことがあります。EFS PVC の request はディレクトリ単位の quota ではありません。

</details>

### 9. EFS IA/Archive のライフサイクルはどこで構成しますか？

- A. access point 用 StorageClass に任意の performanceMode parameter を指定する
- B. 意図した遷移を保ちながらファイルシステムの lifecycle configuration で設定する
- C. PVC request を減らす
- D. Pod の label を IA に変更する

<details>
<summary>解答を表示</summary>

**正解: B**

EFS CSI の access-point parameter ですべてのファイルシステム throughput や lifecycle property を構成できるわけではありません。既存ポリシーを読んでから配列を更新してください。空の配列は lifecycle 管理を無効にします。需要が予測しにくい場合、Elastic が推奨される開始点です。Archive には、利用可能性と遷移順序に関する固有の要件があります。

</details>

### 10. aws s3 cp --sse AES256 が選択するのは何ですか？

- A. TLS protocol version
- B. NetworkPolicy の暗号化
- C. 保存時の SSE-S3 暗号化
- D. EFS mount の暗号化

<details>
<summary>解答を表示</summary>

**正解: C**

HTTPS/TLS は転送中の通信を保護しますが、--sse で TLS が有効になるわけではありません。適切な endpoint と証明書検証を使用してください。FSx scratch data はサービス管理キーで暗号化され、選択可能な顧客キーを使えるのは persistent filesystem です。

</details>

## 短答問題

### 11. レート計算と容量予測をどのように検証しますか？

<details>
<summary>解答を表示</summary>

**解答: 単位、期間、欠損データ、代表的なシナリオを確認する**

300 秒の期間に読み取り操作が 30,000 回完了した場合、読み取り IOPS は 100 です。累積された読み取り時間が 1,500 秒で、操作数が 30,000 回なら、1,500 / 30,000 = 0.05 秒/操作、つまり 50 ミリ秒です。操作が重なると、累積時間が実時間を超えることがあります。期間を揃え、ゼロ件/サンプルなしは個別に処理してください。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the volume Region}"
: "${EBS_VOLUME_ID:?Set the verified owned EBS volume ID}"
read -r START_TIME END_TIME < <(python3 - <<'PY'
import datetime, time
end = int(time.time()) // 300 * 300
fmt = lambda value: datetime.datetime.fromtimestamp(value, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
print(fmt(end - 3600), fmt(end))
PY
)
aws cloudwatch get-metric-statistics --region "$AWS_REGION" \
  --namespace AWS/EBS --metric-name VolumeReadOps \
  --dimensions "Name=VolumeId,Value=$EBS_VOLUME_ID" \
  --start-time "$START_TIME" --end-time "$END_TIME" \
  --period 300 --statistics Sum --output json > ebs-read-ops.json
python3 - ebs-read-ops.json <<'PY'
import json, sys
with open(sys.argv[1]) as stream:
    points = json.load(stream)["Datapoints"]
for point in sorted(points, key=lambda p: p["Timestamp"]):
    print(point["Timestamp"], "read IOPS:", point["Sum"] / 300)
if not points:
    print("No datapoints: check dimensions, attachment/activity, Region and publication delay")
PY
```

これらは算術上の例であり、測定したワークロードの結果ではありません。カウンターではなく gauge に predict_linear を使います。重複する scrape series を除き、無効な容量値も除外してください。直近の傾向は、将来の容量枯渇を保証するものではありません。ソースのルールは、合成データを使って、高い使用率の継続、重複 target、容量ゼロ、series 欠損、使用量増加をテストしました。

</details>

### 12. CSI identity、Multi-Attach、ノードローカルストレージの違いは何ですか？

<details>
<summary>解答を表示</summary>

**解答: それぞれ認可、アタッチ、配置の問題を解決します**

CSI controller の identity は backend のライフサイクル API を認可するものであり、各アプリケーションの identity ではありません。EBS Multi-Attach は、サービス/driver/AZ の制約下で raw device を共有してアタッチします。アプリケーション側の書き込み調整と fencing が必要です。任意の multiAttach StorageClass field は、サポートされたスイッチではありません。

ノードローカルの instance store は物理的にノードのライフサイクルに結びついており、適切なデバイスのプロビジョニング/スケジューリングが必要です。hostPath の文字列だけでは、実際の backing device や耐久性を確認できません。性能例を動かすために権限を広げたり、対象不明のディスクを format したりせず、この章のレビュー済み CSI 経路を使ってください。

</details>

### 13. admission と EKS audit logging で何を証明できますか？

<details>
<summary>解答を表示</summary>

**解答: 構成されたリクエスト範囲と記録済みイベントに限られます**

この章の Kyverno policies.kyverno.io/v1 ValidatingPolicy は、対象となる EBS StorageClass の暗号化 parameter の宣言を確認します。既存の AWS volume、static PV の内容、すべての迂回経路を検査するものではありません。管理者権限を制限し、admission に加えて実際の backend 暗号化を検証してください。

EKS では control plane の audit policy を AWS が管理します。クラスター所有者がサポートされた audit log type を有効にし、配信された記録を確認してください。貼り付けた audit.k8s.io policy 断片は、EKS API から管理済み policy を置き換える方法ではありません。Kubernetes audit event と CloudTrail backend API event は補完関係にありますが、保持期間、アクセス、対象範囲は別々です。audit logging だけでデータ損失を防ぐことはできません。

</details>

## 実践問題

### 14. レビュー可能な監視/ダッシュボード構成を作成してください。

<details>
<summary>解答を表示</summary>

**解答: 依存する各要素を明示的に構成する**

この章でレビューした monitoring stack と collector を使ってください。ConfigMap だけで agent がインストールされると考えないでください。従来の CloudWatch agent のインストールでは、実際の namespace/workload と identity を確認します。選択した integration に合わせて名前を変更し、対応状況を確認してください。

```bash
set -euo pipefail
kubectl -n amazon-cloudwatch get daemonsets,pods
kubectl -n amazon-cloudwatch get serviceaccount cloudwatch-agent -o yaml
```

[クラスター監視の例](../../eks/02-eks-cluster-creation-part3.md)では、所有する agent/add-on の前提条件を説明しています。StatsD receiver だけでは EBS/PVC メトリクスは生成されません。ダッシュボードの不足を埋める目的で static AWS key を追加したり、agent を重複して有効にしたりしないでください。

EBS CSI では、既存の管理者を通じてサポートされた metrics configuration を有効化してください。この章で生成した monitor、**または**既存の Service がある場合は以下の単独 monitor を使い、scrape の重複を避けてください。Prometheus は monitor の namespace/label を選択し、指定された Service port に到達できる必要があります。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: csi-metrics-reviewed
  namespace: monitoring
  labels:
    release: prometheus
spec:
  namespaceSelector:
    matchNames:
    - kube-system
  selector:
    matchLabels:
      app: ebs-csi-controller
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
```

この章の recording/alert rule を監視管理者経由でインストールし、target の Up 状態、期待した series、alert の配信を確認してください。EBS driver endpoint が報告するのは CSI operation のメトリクスであり、すべての sidecar メトリクスや生のファイルシステム使用量ではありません。

この ConfigMap は、その import/provisioning 経路をサポートするデプロイメント向けの **Classic dashboard model** です。現在の Grafana には V1 Resource と既定の V2 Resource model もあります。この raw Classic object を、resource envelope を期待する別の API に送らないでください。Prometheus data-source UID を置き換え、参照する recording rule が存在すること、Grafana sidecar の label/namespace 設定が一致することを確認してください。採用前に対象の Grafana version で export/import を検証します。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: storage-dashboard-reviewed
  namespace: monitoring
  labels:
    grafana_dashboard: '1'
data:
  storage-dashboard.json: |
    {
      "id": null,
      "uid": "eks-storage-reviewed",
      "title": "EKS Storage: PVC Filesystem Usage",
      "tags": [
        "storage"
      ],
      "timezone": "browser",
      "schemaVersion": 42,
      "version": 1,
      "refresh": "30s",
      "time": {
        "from": "now-6h",
        "to": "now"
      },
      "panels": [
        {
          "id": 1,
          "type": "timeseries",
          "title": "PVC filesystem utilization",
          "gridPos": {
            "x": 0,
            "y": 0,
            "w": 24,
            "h": 8
          },
          "datasource": {
            "type": "prometheus",
            "uid": "REPLACE_WITH_PROMETHEUS_DATASOURCE_UID"
          },
          "targets": [
            {
              "refId": "A",
              "expr": "(pvc:storage_used_bytes:max / pvc:storage_capacity_bytes:max) and (pvc:storage_capacity_bytes:max > 0)",
              "legendFormat": "{{cluster}} {{namespace}}/{{persistentvolumeclaim}}"
            }
          ],
          "fieldConfig": {
            "defaults": {
              "unit": "percentunit",
              "min": 0,
              "max": 1
            },
            "overrides": []
          }
        }
      ]
    }
```

EBS IOPS/EFS throughput の追加のネイティブパネルでは、レビュー済み IAM access を使って CloudWatch data source を構成し、ソースに基づく metric dimension と期間正規化済みの計算を使ってください。構成済み exporter が実際にその名前と意味の series を公開していない限り、aws_ebs_* Prometheus series を作り出さないでください。ここにある JSON と式はローカルで確認しただけで、認証済み Grafana への import や稼働中の AWS query は行っていません。

</details>

### 15. 安全でない削除推定をせずにストレージ一覧を作成してください。

<details>
<summary>解答を表示</summary>

**解答: 根拠を報告し、削除可能とは推定しない**

古い placeholder CronJob を読み取り専用のレポートに置き換えます。次の script は namespace と UID を保持し、直接参照する Pod を一覧表示し、削除を承認しません。lastUsed から古さを推定せず、Bound を未使用と同義に扱わず、全 namespace の query から namespace を取り除きません。

```python
"""Report direct Pod/PVC references; never infer deletion eligibility."""
import json,sys
def inventory(namespace,claims,pods):
    refs={}
    for pod in pods['items']:
        meta=pod['metadata']
        if meta['namespace']!=namespace:raise ValueError('Pod list contains another namespace')
        seen=set()
        for volume in pod.get('spec',{}).get('volumes',[]):
            claim=volume.get('persistentVolumeClaim',{}).get('claimName')
            if claim and claim not in seen:
                seen.add(claim)
                refs.setdefault(claim,[]).append({'pod':meta['name'],'podUID':meta['uid'],'phase':pod.get('status',{}).get('phase','Unknown')})
    rows=[]
    for pvc in claims['items']:
        meta,spec=pvc['metadata'],pvc.get('spec',{})
        if meta['namespace']!=namespace:raise ValueError('PVC list contains another namespace')
        rows.append({'namespace':namespace,'name':meta['name'],'uid':meta['uid'],
          'phase':pvc.get('status',{}).get('phase','Unknown'),'volumeName':spec.get('volumeName'),
          'storageClassName':spec.get('storageClassName'),'requestedStorage':spec.get('resources',{}).get('requests',{}).get('storage'),
          'directPodReferences':refs.get(meta['name'],[]),'ownerReferences':meta.get('ownerReferences',[]),
          'deletionAuthorized':False,'nextAction':'Review owner, controller templates, retention, backups and actual backend before any change'})
    return {'reviewOnly':True,'namespace':namespace,'rows':sorted(rows,key=lambda x:x['name']),
      'limitations':['The two API reads are not an atomic snapshot.','No Pod reference does not mean unused: scale-to-zero controllers, future Jobs, retained data and indirect/ephemeral references need separate review.','lastUsed is not a standard trustworthy Kubernetes PVC field. This report never authorizes snapshot creation or deletion.']}
if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('Usage: storage-inventory.py namespace pvcs.json pods.json')
    with open(sys.argv[2]) as f:claims=json.load(f)
    with open(sys.argv[3]) as f:pods=json.load(f)
    print(json.dumps(inventory(sys.argv[1],claims,pods),indent=2))
```



```bash
set -euo pipefail
: "${STORAGE_NAMESPACE:?Set the namespace being reviewed}"
kubectl -n "$STORAGE_NAMESPACE" get pvc -o json > inventory-pvcs.json
kubectl -n "$STORAGE_NAMESPACE" get pods -o json > inventory-pods.json
python3 storage-inventory.py "$STORAGE_NAMESPACE" inventory-pvcs.json inventory-pods.json
```

query を実行する identity に必要なのは、この namespace の読み取り権限だけです。この Role は適用範囲の例です。必要であればレビュー済みの operator/automation identity に bind します。snapshot の作成、resize、削除権限は付与しません。

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: storage-inventory-reader
  namespace: storage-demo
rules:
- apiGroups:
  - ''
  resources:
  - pods
  - persistentvolumeclaims
  verbs:
  - get
  - list
```

scale-to-zero controller template、Job/CronJob、保持中の claim、間接/一時的な参照、バックアップ方針、実際の backend ID を別々に確認してください。現在 Pod から参照されていないだけで削除を決めてはいけません。このレポートを後で定期実行する場合は、script/client を含む実在するレビュー済み image、上限のある実行、範囲を限定した credential、明確なレポート出力先を使用してください。storage-tools:latest や省略記号入りのコマンドは実装ではありません。

まず観測を自動化し、その後、範囲を限定した変更提案と独立して検証された復旧を行います。EBS/PVC の拡張は任意の縮小ではありません。リソースを密かに破棄する script を使わず、デプロイメントに合った監査証拠、ライフサイクル所有者、明示的な承認/運用制御を維持してください。

</details>

## 解答を振り返る

問題は全15問で、選択式が10問あります。誤答は復習が必要な分野を見つけるために使ってください。クイズの得点だけで本番環境を扱う専門性が証明されるわけではありません。実践問題では、構文だけでなく前提条件、リソースの適用範囲、検証証拠も評価してください。

## 参考資料

- [参照章](../../eks/04-eks-storage-part3.md)
- [EBS メトリクス](https://docs.aws.amazon.com/ebs/latest/userguide/using_cloudwatch_ebs.html)
- [FSx メトリクス](https://docs.aws.amazon.com/fsx/latest/LustreGuide/fs-metrics.html)
- [EFS lifecycle API](https://docs.aws.amazon.com/efs/latest/APIReference/API_PutLifecycleConfiguration.html)
- [EKS audit](https://docs.aws.amazon.com/eks/latest/best-practices/auditing-and-logging.html)
- [Grafana dashboard model](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/view-dashboard-json-model/)

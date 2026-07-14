# EKS ストレージ Part 3 クイズ

このクイズでは、Amazon EKS におけるストレージのモニタリング、トラブルシューティング、コスト最適化、セキュリティに関する理解を確認します。

## 問題 1: ストレージモニタリングメトリクス

<details>
<summary>EKS でストレージ性能を監視するための主要なメトリクスは何ですか？</summary>

**解答:**
**EBS メトリクス:**
- VolumeReadOps/VolumeWriteOps: IOPS 使用量
- VolumeReadBytes/VolumeWriteBytes: スループット
- VolumeTotalReadTime/VolumeTotalWriteTime: レイテンシー
- VolumeQueueLength: 保留中の I/O リクエスト数
- BurstBalance: バーストクレジット残高

**EFS メトリクス:**
- DataReadIOBytes/DataWriteIOBytes: データ転送量
- MetadataIOBytes: メタデータ操作量
- ClientConnections: クライアント接続数
- PercentIOLimit: I/O 制限の使用率

**Kubernetes メトリクス:**
- kubelet_volume_stats_used_bytes: Volume 使用量
- kubelet_volume_stats_capacity_bytes: Volume 容量
- container_fs_usage_bytes: Container ファイルシステム使用量
</details>

## 問題 2: ストレージ問題の診断

<details>
<summary>EKS の Pod が "Pending" 状態のままで PVC をマウントできない場合、何を確認すべきですか？</summary>

**解答:**
1. **PVC ステータスの確認**:
   ```bash
   kubectl get pvc
   kubectl describe pvc <pvc-name>
   ```

2. **Storage Class の確認**:
   ```bash
   kubectl get storageclass
   kubectl describe storageclass <storage-class-name>
   ```

3. **CSI Driver ステータスの確認**:
   ```bash
   kubectl get pods -n kube-system -l app=ebs-csi-controller
   kubectl logs -n kube-system -l app=ebs-csi-controller
   ```

4. **Node 権限の確認**:
   - EC2 instance profile に必要な IAM 権限があることを確認
   - EBS CSI driver service account の権限を確認

5. **Availability Zone の互換性**:
   - Pod と EBS volume が同じ AZ にあることを確認

6. **リソース制限**:
   - EBS volume の制限（instance あたりの最大 volume 数）
   - volume サイズ制限を確認
</details>

## 問題 3: 性能最適化

<details>
<summary>EKS でデータベースワークロード向けのストレージ性能をどのように最適化できますか？</summary>

**解答:**
1. **適切な Volume Type の選択**:
   ```yaml
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: fast-ssd
   provisioner: ebs.csi.aws.com
   parameters:
     type: io2
     iops: "10000"
     encrypted: "true"
   volumeBindingMode: WaitForFirstConsumer
   ```

2. **Multi-Attach Volumes の使用**（読み取り専用ワークロード向け）:
   ```yaml
   parameters:
     type: io2
     multiAttach: "true"
   ```

3. **Instance Store の活用**:
   ```yaml
   # Instance store for temporary data
   volumeMounts:
   - name: instance-store
     mountPath: /tmp
   volumes:
   - name: instance-store
     hostPath:
       path: /mnt/instance-store
   ```

4. **適切な Filesystem の選択**:
   - XFS: 大きなファイルと高い同時実行性
   - ext4: 汎用
   - 適切なマウントオプションを設定

5. **I/O Scheduler の最適化**:
   ```bash
   # noop or deadline scheduler for SSD
   echo noop > /sys/block/nvme0n1/queue/scheduler
   ```
</details>

## 問題 4: コスト最適化戦略

<details>
<summary>EKS のストレージコストを最適化するために、どのような戦略を使用できますか？</summary>

**解答:**
1. **適切な Volume Type の選択**:
   - gp3: ほとんどのワークロードで費用対効果が高い
   - gp2 から gp3 へ移行
   - 必要な場合にのみ provisioned IOPS を使用

2. **Volume サイズの最適化**:
   ```bash
   # Monitor usage
   kubectl top pods --containers
   df -h # Inside pod
   ```

3. **ライフサイクル管理**:
   ```yaml
   # Snapshot automation
   apiVersion: snapshot.storage.k8s.io/v1
   kind: VolumeSnapshotClass
   metadata:
     name: csi-aws-vsc
   driver: ebs.csi.aws.com
   deletionPolicy: Delete
   ```

4. **EFS Storage Classes の活用**:
   ```yaml
   # Infrequent Access storage class
   parameters:
     performanceMode: generalPurpose
     throughputMode: provisioned
     provisionedThroughputInMibps: "100"
   ```

5. **未使用 Volume のクリーンアップ**:
   ```bash
   # Check unused PVs
   kubectl get pv | grep Available

   # Clean up old snapshots
   aws ec2 describe-snapshots --owner-ids self \
     --query 'Snapshots[?StartTime<=`2023-01-01`]'
   ```
</details>

## 問題 5: セキュリティのベストプラクティス

<details>
<summary>EKS のストレージセキュリティをどのように強化できますか？</summary>

**解答:**
1. **暗号化の有効化**:
   ```yaml
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: encrypted-gp3
   provisioner: ebs.csi.aws.com
   parameters:
     type: gp3
     encrypted: "true"
     kmsKeyId: "arn:aws:kms:region:account:key/key-id"
   ```

2. **IAM 権限の最小化**:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "ec2:CreateVolume",
           "ec2:AttachVolume",
           "ec2:DetachVolume",
           "ec2:DeleteVolume",
           "ec2:DescribeVolumes",
           "ec2:CreateSnapshot",
           "ec2:DeleteSnapshot",
           "ec2:DescribeSnapshots"
         ],
         "Resource": "*",
         "Condition": {
           "StringEquals": {
             "aws:RequestedRegion": "us-west-2"
           }
         }
       }
     ]
   }
   ```

3. **ネットワークセキュリティ**:
   ```yaml
   # EFS mount target security group
   securityGroupSelector:
     matchLabels:
       Name: "efs-mount-target-sg"
   ```

4. **アクセス制御**:
   ```yaml
   # RBAC configuration
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     name: storage-admin
   rules:
   - apiGroups: [""]
     resources: ["persistentvolumes", "persistentvolumeclaims"]
     verbs: ["get", "list", "create", "delete"]
   ```

5. **監査ログ**:
   ```yaml
   # Storage-related audit policy
   - level: Metadata
     resources:
     - group: ""
       resources: ["persistentvolumes", "persistentvolumeclaims"]
   ```
</details>

### 6. Amazon EKS におけるストレージモニタリングと管理に最も効果的なツールの組み合わせは何ですか？

A. CloudWatch と AWS Console のみを使用する
B. CloudWatch、Prometheus、Grafana、自動管理ツール
C. 手動検査とログ分析
D. サードパーティ製モニタリングツールのみを使用する

<details>
<summary>解答を表示</summary>

**解答: B. CloudWatch、Prometheus、Grafana、自動管理ツール**

**解説:**
Amazon EKS におけるストレージモニタリングと管理に最も効果的なツールの組み合わせは、CloudWatch、Prometheus、Grafana、自動管理ツールを併用することです。この統合アプローチにより、AWS ネイティブのメトリクスと詳細な Kubernetes レベルのメトリクスの両方を収集し、それらを可視化し、自動管理を通じて運用効率を向上させます。

**統合モニタリングおよび管理アーキテクチャ:**

1. **CloudWatch**:
   - AWS インフラストラクチャレベルのメトリクスを収集
   - EBS、EFS、FSx ストレージ性能メトリクス
   - アラームとイベント管理

2. **Prometheus**:
   - 詳細な Kubernetes レベルのメトリクスを収集
   - カスタムストレージメトリクスを収集
   - 長期データ保持とクエリ

3. **Grafana**:
   - 統合ダッシュボードと可視化
   - CloudWatch と Prometheus データソースの統合
   - カスタムアラートとレポート

4. **Automated Management Tools**:
   - ストレージプロビジョニングの自動化
   - 容量計画とスケーリング
   - 問題の検出と解決
</details>

---

**スコア計算:**
- 5-6 問正解: 優秀（EKS ストレージエキスパートレベル）
- 3-4 問正解: 良好（追加学習を推奨）
- 1-2 問正解: 可（基本概念の復習が必要）
- 0 問正解: 改善が必要（全内容の再学習が必要）

**実装例:**

1. **CloudWatch Container Insights のセットアップ**:
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: cwagent-config
     namespace: amazon-cloudwatch
   data:
     cwagentconfig.json: |
       {
         "logs": {
           "metrics_collected": {
             "kubernetes": {
               "cluster_name": "my-cluster",
               "metrics_collection_interval": 60
             }
           },
           "force_flush_interval": 5
         },
         "metrics": {
           "namespace": "EKS/Storage",
           "metrics_collected": {
             "statsd": {
               "service_address": ":8125"
             }
           }
         }
       }
   ```

2. **Prometheus と Storage Exporter のセットアップ**:
   ```yaml
   apiVersion: monitoring.coreos.com/v1
   kind: ServiceMonitor
   metadata:
     name: storage-monitor
     namespace: monitoring
   spec:
     selector:
       matchLabels:
         app: storage-exporter
     endpoints:
     - port: metrics
       interval: 30s
       path: /metrics
   ```

3. **Grafana Dashboard の設定**:
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: storage-dashboard
     namespace: monitoring
   data:
     storage-dashboard.json: |
       {
         "title": "EKS Storage Dashboard",
         "panels": [
           {
             "title": "EBS Volume IOPS",
             "datasource": "Prometheus",
             "targets": [
               {
                 "expr": "aws_ebs_volume_read_ops + aws_ebs_volume_write_ops",
                 "legendFormat": "{{volume_id}}"
               }
             ]
           },
           {
             "title": "EFS Throughput",
             "datasource": "CloudWatch",
             "targets": [
               {
                 "namespace": "AWS/EFS",
                 "metricName": "TotalIOBytes",
                 "dimensions": {
                   "FileSystemId": "*"
                 },
                 "statistic": "Sum"
               }
             ]
           }
         ]
       }
   ```

4. **自動ストレージ管理 CronJob**:
   ```yaml
   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: storage-manager
   spec:
     schedule: "0 1 * * *"
     jobTemplate:
       spec:
         template:
           spec:
             containers:
             - name: storage-manager
               image: storage-tools:latest
               command:
               - /bin/bash
               - -c
               - |
                 # Identify unused PVCs
                 UNUSED_PVCS=$(kubectl get pvc -A -o json | jq -r '.items[] | select(.status.phase == "Bound") | select(.metadata.annotations.lastUsed < "'$(date -d "30 days ago" +%Y-%m-%d)'") | .metadata.name')

                 # Create snapshots
                 for PVC in $UNUSED_PVCS; do
                   kubectl create snapshot ...
                 done

                 # Analyze volume usage and generate reports
                 ...
             restartPolicy: OnFailure
   ```

**主要なモニタリングメトリクス:**

1. **EBS Volume メトリクス**:
   - VolumeReadOps/VolumeWriteOps
   - VolumeReadBytes/VolumeWriteBytes
   - VolumeQueueLength
   - BurstBalance（gp2 volumes）

2. **EFS メトリクス**:
   - TotalIOBytes
   - DataReadIOBytes/DataWriteIOBytes
   - MetadataIOBytes
   - ClientConnections
   - StorageBytes（Standard/IA）

3. **FSx for Lustre メトリクス**:
   - DataReadBytes/DataWriteBytes
   - DataReadOperations/DataWriteOperations
   - FreeDataStorageCapacity
   - LogicalDiskUsage

4. **Kubernetes Storage メトリクス**:
   - PVC 使用量と容量
   - Volume マウントステータス
   - Storage class 使用量

**高度なモニタリングおよび管理機能:**

1. **予測分析**:
   - 容量予測と計画
   - 性能トレンド分析
   - コスト予測

2. **異常検知**:
   - 異常な I/O パターンを検出
   - 性能低下の早期警告
   - 容量不足の予測

3. **自動最適化**:
   - 使用パターンに基づく Volume type 推奨
   - 自動スケールアップおよびスケールダウン
   - コスト最適化の推奨

4. **統合レポート**:
   - ストレージ使用量と性能レポート
   - コスト配分と分析
   - コンプライアンスおよび監査レポート

**実装のベストプラクティス:**

1. **マルチレベルモニタリング**:
   - インフラストラクチャレベル（CloudWatch）
   - Kubernetes レベル（Prometheus）
   - アプリケーションレベル（custom metrics）

2. **アラート戦略**:
   - 重要度に基づいてアラートを設定
   - アラートのグループ化と重複排除
   - エスカレーションパスを定義

3. **データ保持ポリシー**:
   - 高解像度データ: 短期保持
   - 集約データ: 長期保持
   - コストと有用性のバランス

4. **段階的な自動化導入**:
   - まずモニタリングとアラートを実装
   - レポートと分析機能を追加
   - 自動管理を段階的に導入

その他の選択肢の問題点:
- **A. CloudWatch と AWS Console のみを使用する**: AWS ネイティブのメトリクスは提供しますが、詳細な Kubernetes レベルのメトリクスが不足し、自動化機能が限られています。
- **C. 手動検査とログ分析**: スケーラビリティが不足し、リアルタイムモニタリングが困難になり、プロアクティブな問題検出を妨げます。
- **D. サードパーティ製モニタリングツールのみを使用する**: AWS ネイティブのメトリクスとの統合が限られる可能性があり、追加コストが発生する場合があります。

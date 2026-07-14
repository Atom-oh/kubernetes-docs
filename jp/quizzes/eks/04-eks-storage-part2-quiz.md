# EKS Storage クイズ - Part 2

このクイズでは、Amazon EKS における高度な storage 概念についての理解を確認します。storage 最適化、backup と recovery 戦略、さまざまな workload 向けの storage solution が含まれます。

## 選択問題

### 1. Amazon EKS で StatefulSet を使用する場合、PersistentVolumeClaims を作成する最も効果的な方法は何ですか？

A. 各 pod に対して PVC を手動で作成する B. volumeClaimTemplates を使用する C. ConfigMap を使用して PVC を定義する D. dynamic provisioning を無効化する

<details>

<summary>回答を表示</summary>

**回答: B. volumeClaimTemplates を使用する**

**解説:** Amazon EKS で StatefulSet を使用する際に PersistentVolumeClaims (PVCs) を作成する最も効果的な方法は、`volumeClaimTemplates` を使用することです。この方法では、StatefulSet 内の各 pod に対して一意の PVC が自動的に作成され、それらは pod の lifecycle とは独立して管理されます。

**volumeClaimTemplates の主な機能:**

1.  **PVC の自動作成**: StatefulSet 内の各 pod に対して一意の PVC が自動的に作成されます。

    ```yaml
    volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: [ "ReadWriteOnce" ]
        storageClassName: ebs-sc
        resources:
          requests:
            storage: 10Gi
    ```
2. **安定した Storage**: pod が再起動または再スケジュールされても、同じ PVC が再利用されます。
3. **命名規則**: PVC 名は `<volumeClaimTemplate-name>-<statefulset-name>-<ordinal>` の形式で作成されます。例: `data-mysql-0`, `data-mysql-1`, `data-mysql-2`
4. **順次 Deployment**: StatefulSet は pod を順番に作成および削除するため、storage 操作も順番に処理されます。

**StatefulSet の例:**

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  selector:
    matchLabels:
      app: mysql
  serviceName: mysql
  replicas: 3
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:5.7
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-secret
              key: password
        ports:
        - containerPort: 3306
          name: mysql
        volumeMounts:
        - name: data
          mountPath: /var/lib/mysql
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: ebs-sc
      resources:
        requests:
          storage: 10Gi
```

**volumeClaimTemplates の利点:**

1. **自動化**: PVC を手動で作成および管理する必要がありません。
2. **スケーラビリティ**: StatefulSet の replicas を調整すると、PVC が自動的に作成されます。
3. **データ永続性**: pod が削除されても PVC とデータは保持されます。
4. **順序保証**: Pod と PVC の作成および削除の順序が保証されます。

**注意点:**

1.  **PVC 削除ポリシー**: StatefulSet が削除されても PVC は自動的には削除されません。これはデータ損失を防ぐための設計です。

    ```bash
    # Check PVCs after StatefulSet deletion
    kubectl get pvc -l app=mysql

    # Manually delete PVCs if needed
    kubectl delete pvc data-mysql-0 data-mysql-1 data-mysql-2
    ```
2. **Storage Class の選択**: workload 要件を満たす適切な storage class を選択します。
   * EBS: Single node access (RWO)
   * EFS: Multi-node access (RWX)
3.  **Volume Binding Mode**: pod がスケジュールされる availability zone に volume が作成されるよう、`WaitForFirstConsumer` を使用します。

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer
    ```

他の選択肢の問題点:

* **A. 各 pod に対して PVC を手動で作成する**: 手動作成は error-prone で、スケーラビリティに欠け、StatefulSet の自動化の利点を活用できません。
* **C. ConfigMap を使用して PVC を定義する**: ConfigMap は configuration data を保存するために使用されるもので、PVC を直接作成するためには使用できません。
* **D. dynamic provisioning を無効化する**: dynamic provisioning を無効化すると、PVC を手動で作成する必要があるため管理オーバーヘッドが増加します。

</details>

### 2. Amazon EKS で EBS volume performance を最適化する最も効果的な方法は何ですか？

A. すべての EBS volume に provisioned IOPS (io1) type を使用する B. workload 要件に基づいて適切な EBS volume type を選択する C. すべての EBS volume に最大サイズをプロビジョニングする D. すべての pod を同じ availability zone に配置する

<details>

<summary>回答を表示</summary>

**回答: B. workload 要件に基づいて適切な EBS volume type を選択する**

**解説:** Amazon EKS で EBS volume performance を最適化する最も効果的な方法は、workload 要件に基づいて適切な EBS volume type を選択することです。各 EBS volume type は異なる performance 特性とコスト構造を持つため、workload の特性に合った volume type を選ぶことが重要です。

**主な EBS Volume Type と特性:**

1.  **gp3 (General Purpose SSD)**:

    * Baseline Performance: 3,000 IOPS, 125MB/s throughput
    * Maximum Performance: 16,000 IOPS, 1,000MB/s throughput
    * Use Cases: Boot volumes, development and test environments, small to medium databases

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-gp3
    provisioner: ebs.csi.aws.com
    parameters:
      type: gp3
      iops: "8000"
      throughput: "500"
    ```
2.  **io1/io2 (Provisioned IOPS SSD)**:

    * Maximum Performance: 64,000 IOPS, 1,000MB/s throughput
    * Use Cases: I/O-intensive databases, latency-sensitive workloads

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-io2
    provisioner: ebs.csi.aws.com
    parameters:
      type: io2
      iops: "25000"
    ```
3.  **st1 (Throughput Optimized HDD)**:

    * Maximum Performance: 500 IOPS, 500MB/s throughput
    * Use Cases: Big data, data warehouses, log processing

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-st1
    provisioner: ebs.csi.aws.com
    parameters:
      type: st1
    ```
4.  **sc1 (Cold HDD)**:

    * Maximum Performance: 250 IOPS, 250MB/s throughput
    * Use Cases: Infrequently accessed data, archives

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc1
    provisioner: ebs.csi.aws.com
    parameters:
      type: sc1
    ```

**workload 別の最適な Volume Type 選択:**

1.  **Database Workloads**:

    * 高い performance が必要: io2 または高 performance の gp3
    * 中程度の performance が必要: gp3

    ```yaml
    # StorageClass for high-performance database
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: database-storage
    provisioner: ebs.csi.aws.com
    parameters:
      type: io2
      iops: "25000"
    volumeBindingMode: WaitForFirstConsumer
    ```
2.  **Log and Streaming Workloads**:

    * 高い throughput が必要: st1 または高 throughput の gp3

    ```yaml
    # StorageClass for log processing
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: log-storage
    provisioner: ebs.csi.aws.com
    parameters:
      type: st1
    volumeBindingMode: WaitForFirstConsumer
    ```
3.  **Web and Application Servers**:

    * 中程度の performance が必要: gp3

    ```yaml
    # StorageClass for web servers
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: web-storage
    provisioner: ebs.csi.aws.com
    parameters:
      type: gp3
      iops: "3000"
      throughput: "125"
    volumeBindingMode: WaitForFirstConsumer
    ```

**追加の Performance 最適化戦略:**

1. **Volume サイズ最適化**: 一部の volume type (例: gp2) はサイズに基づいて performance がスケールします。
2. **Instance Type の考慮**: EBS volume 用の専用帯域幅を確保するために、EBS-optimized instances を使用します。
3.  **RAID 構成**: performance 向上のため、複数の EBS volume を RAID 0 で構成します

    ```yaml
    # RAID configuration within pod
    apiVersion: v1
    kind: Pod
    metadata:
      name: raid-pod
    spec:
      containers:
      - name: raid-container
        image: ubuntu:latest
        command: ["/bin/bash", "-c"]
        args:
        - |
          apt-get update && apt-get install -y mdadm
          mdadm --create --verbose /dev/md0 --level=0 --raid-devices=2 /dev/xvdf /dev/xvdg
          mkfs.ext4 /dev/md0
          mount /dev/md0 /data
          # Run application
        volumeMounts:
        - name: vol1
          mountPath: /dev/xvdf
        - name: vol2
          mountPath: /dev/xvdg
        - name: raid-mount
          mountPath: /data
      volumes:
      - name: vol1
        persistentVolumeClaim:
          claimName: ebs-claim-1
      - name: vol2
        persistentVolumeClaim:
          claimName: ebs-claim-2
      - name: raid-mount
        emptyDir: {}
    ```
4. **File System 最適化**: workload に適した file system を選択し、最適化します
   * XFS: 大きなファイルと parallel I/O に適しています
   * ext4: 汎用用途に適しています
5. **Monitoring と調整**: CloudWatch metrics を監視し、必要に応じて volume type または configuration を調整します

他の選択肢の問題点:

* **A. すべての EBS volume に provisioned IOPS (io1) type を使用する**: すべての workload に provisioned IOPS を使用するのは cost-effective ではなく、一部の workload には他の volume type の方が適している場合があります。
* **C. すべての EBS volume に最大サイズをプロビジョニングする**: 必要以上に大きな volume をプロビジョニングすると、不要なコストが発生します。
* **D. すべての pod を同じ availability zone に配置する**: これは high availability を損ない、単一の availability zone 障害によって application 全体が影響を受ける可能性があります。

</details>

### 4. Amazon EKS で FSx for Lustre を使用する主な利点は何ですか？

A. コスト効率 B. シンプルな setup C. 高 performance な parallel file system D. Native EKS integration

<details>

<summary>回答を表示</summary>

**回答: C. 高 performance な parallel file system**

**解説:** Amazon EKS で FSx for Lustre を使用する主な利点は、高 performance な parallel file system を提供することです。FSx for Lustre は、high-performance computing (HPC)、machine learning、big data analytics などの compute-intensive workloads 向けに設計された fully managed file system であり、数百 GB/s の throughput、数百万 IOPS、sub-millisecond latency を提供します。

**FSx for Lustre の主な Performance 特性:**

1. **高 Throughput**:
   * 最大 1,000GB/s throughput
   * storage 1TiB あたり最大 200MB/s throughput (SSD-based)
   * 大規模 datasets の処理に適しています
2. **低 Latency**:
   * sub-millisecond latency
   * latency-sensitive applications に適しています
3. **Parallel Access**:
   * 数千の compute instances からの同時 access
   * parallel processing による performance 向上
4. **Scalability**:
   * 数百 GB/s throughput までスケール
   * petabyte-scale datasets をサポート

**FSx for Lustre と EKS の Integration:**

1.  **CSI Driver**:

    ```bash
    # Install FSx for Lustre CSI driver
    helm repo add aws-fsx-csi-driver https://kubernetes-sigs.github.io/aws-fsx-csi-driver/
    helm repo update
    helm upgrade -i aws-fsx-csi-driver aws-fsx-csi-driver/aws-fsx-csi-driver \
      --namespace kube-system \
      --set controller.serviceAccount.create=true \
      --set controller.serviceAccount.name=fsx-csi-controller-sa
    ```
2.  **StorageClass Configuration**:

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: fsx-lustre
    provisioner: fsx.csi.aws.com
    parameters:
      subnetId: subnet-0123456789abcdef0
      securityGroupIds: sg-0123456789abcdef0
      deploymentType: SCRATCH_2
      perUnitStorageThroughput: "200"
      dataCompressionType: "LZ4"
    mountOptions:
      - flock
    ```
3.  **PersistentVolumeClaim Creation**:

    ```yaml
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: fsx-claim
    spec:
      accessModes:
        - ReadWriteMany
      storageClassName: fsx-lustre
      resources:
        requests:
          storage: 1200Gi  # Minimum 1.2TiB
    ```

**FSx for Lustre に適した workloads:**

1. **Machine Learning and Deep Learning**:
   * 大規模 dataset training
   * Distributed training jobs
   * Model serving
2. **High-Performance Computing (HPC)**:
   * Scientific simulations
   * Weather forecasting
   * Genomics
3. **Big Data Analytics**:
   * 大規模 data processing
   * Real-time analytics
   * ETL jobs
4. **Media Processing**:
   * Video rendering
   * Image processing
   * Content creation

**S3 Integration:**

FSx for Lustre は Amazon S3 と seamless に統合されており、S3 data を high-performance file system に簡単に import して処理できます。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-s3
provisioner: fsx.csi.aws.com
parameters:
  subnetId: subnet-0123456789abcdef0
  securityGroupIds: sg-0123456789abcdef0
  deploymentType: SCRATCH_2
  perUnitStorageThroughput: "200"
  s3ImportPath: s3://my-bucket/prefix
  s3ExportPath: s3://my-bucket/export
```

**Deployment Type Options:**

1. **SCRATCH\_1**:
   * 一時 storage と短期 processing
   * Cost-effective
   * Data replication なし
2. **SCRATCH\_2**:
   * 一時 storage と短期 processing
   * server failure 時の data replication
   * SCRATCH\_1 より高い availability
3. **PERSISTENT**:
   * 長期 storage と workloads
   * Data replication と automatic recovery
   * 高い durability

**Performance 最適化のヒント:**

1. **適切な Throughput 選択**:
   * SSD storage: 50, 100, 200 MB/s/TiB
   * HDD storage: 12, 40 MB/s/TiB
2. **Data Compression の有効化**:
   * LZ4 compression による storage efficiency の向上
   * network bandwidth 使用量の削減
3. **File System サイズ最適化**:
   * より大きな file system は、より多くの servers と高い aggregate performance を提供します
4.  **Mount Option 最適化**:

    ```
    mount -t lustre -o noatime,flock file_system_dns_name@tcp:/mountname /mnt/fsx
    ```

他の選択肢の問題点:

* **A. コスト効率**: FSx for Lustre は高 performance を提供しますが、一般的に EBS や EFS より高価です。
* **B. シンプルな setup**: FSx for Lustre は高度な configuration options を必要とし、EBS や EFS より setup が複雑です。
* **D. Native EKS integration**: FSx for Lustre は EKS と native に統合されていません。CSI driver を別途インストールする必要があります。

</details>

## 短答問題

### 6. Amazon EKS で EBS volume performance を向上させるために使用できる RAID 構成は何ですか？

<details>

<summary>回答を表示</summary>

**回答:** RAID 0 (Striping)

**詳細な解説:**

Amazon EKS で EBS volume performance を向上させるために使用できる RAID 構成は RAID 0 (striping) です。RAID 0 は data を複数の EBS volume に分散して I/O performance を向上させます。

**RAID 0 の仕組み:**

RAID 0 は、data を複数の disk に分散して保存し、各 disk が全体の I/O workload の一部を処理することで、全体的な performance を向上させます。たとえば、2 つの EBS volume で RAID 0 を構成すると、理論上 throughput と IOPS を 2 倍にできます。

**RAID 0 の主な機能:**

1. **Performance 向上**: I/O 操作は複数の volume で parallel に処理され、throughput と IOPS が向上します。
2. **Capacity 集約**: すべての volume の capacity が集約され、1 つの大きな volume として使用されます。
3. **Fault Tolerance なし**: 1 つの volume が故障すると、RAID array 全体のすべての data が失われます。

**EKS で RAID 0 を構成する方法:**

1.  **複数の PVC を作成:**

    ```yaml
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: ebs-claim-1
    spec:
      accessModes:
        - ReadWriteOnce
      storageClassName: ebs-sc
      resources:
        requests:
          storage: 100Gi
    ---
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: ebs-claim-2
    spec:
      accessModes:
        - ReadWriteOnce
      storageClassName: ebs-sc
      resources:
        requests:
          storage: 100Gi
    ```
2.  **Pod 内で RAID 0 を構成:**

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: raid0-pod
    spec:
      containers:
      - name: raid-container
        image: ubuntu:latest
        command: ["/bin/bash", "-c"]
        args:
        - |
          apt-get update && apt-get install -y mdadm
          mdadm --create --verbose /dev/md0 --level=0 --raid-devices=2 /dev/xvdf /dev/xvdg
          mkfs.ext4 /dev/md0
          mount /dev/md0 /data
          # Run application
          while true; do sleep 30; done
        volumeMounts:
        - name: vol1
          mountPath: /dev/xvdf
        - name: vol2
          mountPath: /dev/xvdg
        - name: raid-mount
          mountPath: /data
        securityContext:
          privileged: true  # Permissions required for RAID configuration
      volumes:
      - name: vol1
        persistentVolumeClaim:
          claimName: ebs-claim-1
      - name: vol2
        persistentVolumeClaim:
          claimName: ebs-claim-2
      - name: raid-mount
        emptyDir: {}
    ```

**RAID 0 Performance 最適化のヒント:**

1. **Volume 数**: 通常 2〜4 個の volume が最適な performance を提供します。volume が多すぎると管理オーバーヘッドが増加する可能性があります。
2. **Volume サイズ**: performance を均等に分散するため、すべての volume を同じサイズで構成します。
3. **Stripe Size**: workload に基づいて適切な stripe size を選択します。
   * Small random I/O: 小さい stripe size (例: 4KB)
   * Large sequential I/O: 大きい stripe size (例: 64KB または 128KB)
4. **Instance Type**: EBS volume 用の専用帯域幅を確保するため、EBS-optimized instances を使用します。

**RAID 0 のユースケース:**

1. **High-Performance Databases**: 高い IOPS と throughput を必要とする database workloads
2. **Big Data Processing**: 大規模 data processing と analytics workloads
3. **Media Processing**: video encoding/decoding、rendering などの I/O-intensive tasks

**注意点:**

1. **Data Durability**: RAID 0 には fault tolerance がないため、重要な data には適切な backup strategy が必要です。
2. **Volume Failure**: 1 つの volume が故障すると、すべての data が失われる可能性があるため、snapshots による定期 backup が重要です。
3. **Complexity**: RAID 構成は管理の complexity を増加させるため、本当に必要な場合にのみ使用してください。
4. **Cost**: 複数の EBS volume を使用すると storage cost が増加します。

**代替案の検討:**

1. **High-Performance Single Volume**: シンプルさを優先する場合は io2 または高 performance の gp3 volume を使用します
2. **Instance Store**: 一時 data には instance store volume を検討します
3. **FSx for Lustre**: 非常に高い performance が必要な場合は parallel file system を検討します

RAID 0 は EBS volume performance を向上させる効果的な方法ですが、data durability と管理 complexity を考慮して慎重に使用する必要があります。

</details>

### 7. Amazon EKS で EFS file system performance を最適化するため、read と write buffer size を設定するのに使用できる mount options は何ですか？

<details>

<summary>回答を表示</summary>

**回答:** rsize and wsize

**詳細な解説:**

Amazon EKS で EFS file system performance を最適化するために read と write buffer size を設定するために使用できる mount options は、`rsize` (read buffer size) と `wsize` (write buffer size) です。これらの options は、NFS clients が EFS file system と通信する際に使用される data chunks のサイズを決定します。

**rsize と wsize の役割:**

1. **rsize (Read Buffer Size)**:
   * NFS client が server から読み取る際に使用される最大 bytes 数
   * 値を大きくすると、より少ない network requests でより多くの data を読み取れます
   * Default は通常 1MB (1048576 bytes)
2. **wsize (Write Buffer Size)**:
   * NFS client が server に書き込む際に使用される最大 bytes 数
   * 値を大きくすると、より少ない network requests でより多くの data を書き込めます
   * Default は通常 1MB (1048576 bytes)

**EKS での rsize と wsize の設定:**

1.  **StorageClass での設定:**

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: efs-sc-optimized
    provisioner: efs.csi.aws.com
    parameters:
      provisioningMode: efs-ap
      fileSystemId: fs-0123456789abcdef0
      directoryPerms: "700"
    mountOptions:
      - rsize=1048576
      - wsize=1048576
    ```
2.  **PersistentVolume での設定:**

    ```yaml
    apiVersion: v1
    kind: PersistentVolume
    metadata:
      name: efs-pv
    spec:
      capacity:
        storage: 5Gi
      volumeMode: Filesystem
      accessModes:
        - ReadWriteMany
      persistentVolumeReclaimPolicy: Retain
      storageClassName: efs-sc
      mountOptions:
        - rsize=1048576
        - wsize=1048576
      csi:
        driver: efs.csi.aws.com
        volumeHandle: fs-0123456789abcdef0
    ```

**最適値の選択:**

1. **一般的な推奨値**:
   * rsize=1048576 (1MB)
   * wsize=1048576 (1MB)
2. **Workload 固有の最適化**:
   * Large sequential read/write: より大きな値 (例: 1MB)
   * Small random read/write: より小さな値 (例: 32KB または 64KB)
3. **Network Conditions の考慮**:
   * Stable network: より大きな値
   * Unstable network: より小さな値 (packet loss 時の retransmission overhead を削減)

**追加の Performance 最適化 Mount Options:**

1.  **timeo**: Server response wait time (in 1/10 second units)

    ```
    timeo=600  # 60 seconds
    ```
2.  **retrans**: Number of retries before timeout

    ```
    retrans=2
    ```
3.  **noresvport**: Use new TCP port on connection recovery

    ```
    noresvport
    ```
4.  **noatime**: Disable file access time updates

    ```
    noatime
    ```

**完全な最適化済み Mount Options の例:**

```yaml
mountOptions:
  - rsize=1048576
  - wsize=1048576
  - timeo=600
  - retrans=2
  - noresvport
  - noatime
```

**Performance Monitoring と Tuning:**

1.  **Performance 測定**:

    ```bash
    # Read performance test
    dd if=/efs/testfile of=/dev/null bs=1M count=1000

    # Write performance test
    dd if=/dev/zero of=/efs/testfile bs=1M count=1000
    ```
2. **CloudWatch Metrics Monitoring**:
   * TotalIOBytes
   * DataReadIOBytes
   * DataWriteIOBytes
   * MetadataIOBytes
3. **段階的な Tuning**:
   * さまざまな rsize/wsize 値でテストします
   * workload patterns に基づいて最適値を選択します

rsize と wsize options を適切に設定すると、特に大きな file transfers や高 throughput 要件を伴う workload で、EFS file system performance を大幅に向上できます。

</details>

### 9. Amazon EKS で EBS volumes を使用する場合の data durability に関する AWS の SLA (Service Level Agreement) は何ですか？

<details>

<summary>回答を表示</summary>

**回答:** 99.999% (5 9's)

**詳細な解説:**

Amazon EKS で EBS volumes を使用する場合の data durability に関する AWS の SLA (Service Level Agreement) は 99.999% (5 9's) です。これは Amazon EBS の年間 data loss 確率が 0.001% 未満であることを意味します。

**EBS Durability の主な機能:**

1. **Design Durability**: Amazon EBS volumes は 99.999% durability を提供するよう設計されています。
2. **Availability Zone Replication**: EBS volume data は単一の availability zone 内の複数 servers に自動的に複製されます。
3. **Annual Failure Rate (AFR)**: 年間 failure rate の目標範囲は 0.1% - 0.2% です。

**EBS Volume Type の Durability:**

すべての EBS volume type (gp2, gp3, io1, io2, st1, sc1) は同じ 99.999% durability design を持ちます。ただし、io2 volume は追加の durability guarantees を提供します:

* **io2 Block Express**: 99.999% durability に加えて 99.999% availability SLA

**Data Protection 強化方法:**

1.  **EBS Snapshots**:

    * 定期 snapshots による data backup
    * Snapshots は S3 に 99.999999999% (11 9's) durability で保存されます

    ```yaml
    apiVersion: snapshot.storage.k8s.io/v1
    kind: VolumeSnapshotClass
    metadata:
      name: ebs-snapshot-class
    driver: ebs.csi.aws.com
    deletionPolicy: Retain
    ```
2.  **Cross-Region Snapshot Copy**:

    * disaster recovery のため snapshots を別 region にコピーします

    ```bash
    aws ec2 copy-snapshot \
      --source-region us-west-2 \
      --source-snapshot-id snap-0123456789abcdef0 \
      --destination-region us-east-1 \
      --description "Cross-region backup"
    ```
3.  **Automated Backup Policies**:

    * Amazon Data Lifecycle Manager または Kubernetes CronJob を使用した automated backups

    ```yaml
    apiVersion: batch/v1
    kind: CronJob
    metadata:
      name: ebs-snapshot-job
    spec:
      schedule: "0 0 * * *"  # Daily at midnight
      jobTemplate:
        spec:
          template:
            spec:
              containers:
              - name: snapshot-creator
                image: amazon/aws-cli:latest
                command:
                - /bin/sh
                - -c
                - |
                  # Get volume ID from PVC
                  VOLUME_ID=$(kubectl get pvc my-pvc -o jsonpath='{.spec.volumeName}' | xargs kubectl get pv -o jsonpath='{.spec.csi.volumeHandle}')
                  # Create snapshot
                  aws ec2 create-snapshot --volume-id $VOLUME_ID --description "Daily backup"
              restartPolicy: OnFailure
    ```

**EBS Volume Failure シナリオと Recovery:**

1. **Volume Corruption**:
   * Symptoms: I/O errors, performance degradation
   * Recovery: 最新 snapshot から新しい volume を作成
2. **Availability Zone Failure**:
   * Symptoms: Volume inaccessible
   * Recovery: 別の availability zone で snapshot から volume を復元
3. **Accidental Data Deletion**:
   * Recovery: snapshot から特定の point-in-time に復元

**EBS Durability Best Practices:**

1. **Regular Snapshots**:
   * 重要な data には毎日またはより頻繁に snapshots を作成します
   * snapshot retention policies を実装します
2. **Snapshot Testing**:
   * snapshots からの restore を定期的にテストします
   * recovery processes を文書化し、訓練します
3. **Multi-Region Strategy**:
   * critical data では snapshots を別 region にコピーします
   * disaster recovery plans を確立します
4. **Monitoring and Alerting**:
   * EBS volume health を監視します
   * CloudWatch alarms を設定します

**EBS vs Other AWS Storage Services Durability Comparison:**

| Service        | Durability             | Availability                   |
| -------------- | ---------------------- | ------------------------------ |
| Amazon EBS     | 99.999%                | 99.95-99.999% (varies by type) |
| Amazon EFS     | 99.999999999% (11 9's) | 99.99%                         |
| Amazon S3      | 99.999999999% (11 9's) | 99.99%                         |
| FSx for Lustre | 99.999%                | 99.95%                         |

Amazon EBS の 99.999% durability はほとんどの workload に十分な data protection を提供しますが、critical data については、定期 snapshots と multi-region backup strategies による追加の protection layers を実装することが推奨されます。

</details>

## ハンズオン問題

### 10. Amazon EKS cluster 内の database workloads 向けに高 performance な storage solution を設計してください。次の要件を満たす storage classes、persistent volume claims、StatefulSet を作成してください:

* 高い IOPS を必要とする PostgreSQL database
* Automatic backup と recovery functionality
* Volume expansion capability

<details>

<summary>回答を表示</summary>

**回答:**

Amazon EKS cluster 内の database workloads 向けに高 performance な storage solution を設計する方法は次のとおりです:

### 1. High-Performance StorageClass Definition

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: postgres-io2
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: io2
  iops: "25000"  # High IOPS provision
  encrypted: "true"
  kmsKeyId: "arn:aws:kms:region:account-id:key/key-id"  # Optional: Encryption with KMS key
allowVolumeExpansion: true  # Allow volume expansion
reclaimPolicy: Retain  # Retain PV on PVC deletion
```

### 2. PostgreSQL StatefulSet Definition

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: database
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      securityContext:
        fsGroup: 999  # PostgreSQL group ID
      containers:
      - name: postgres
        image: postgres:14
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        ports:
        - containerPort: 5432
          name: postgres
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          initialDelaySeconds: 5
          periodSeconds: 10
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          initialDelaySeconds: 30
          periodSeconds: 15
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: postgres-io2
      resources:
        requests:
          storage: 100Gi
```

### 3. PostgreSQL Service Definition

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: database
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  clusterIP: None  # Headless service
```

### 4. VolumeSnapshotClass and CronJob for Automated Backups

```yaml
# VolumeSnapshotClass Definition
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: postgres-snapshot-class
driver: ebs.csi.aws.com
deletionPolicy: Retain
parameters:
  # Enable snapshot encryption
  encrypted: "true"
  # Add snapshot tags
  tagSpecification_0_resourceType: "snapshot"
  tagSpecification_0_tags_Purpose: "PostgreSQL Backup"
  tagSpecification_0_tags_Environment: "Production"

# CronJob for automated backups
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: database
spec:
  schedule: "0 1 * * *"  # Daily at 1 AM
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: postgres-backup-sa  # Service account with appropriate permissions
          containers:
          - name: snapshot-creator
            image: bitnami/kubectl:latest
            command:
            - /bin/bash
            - -c
            - |
              # Create snapshot name based on current date
              SNAPSHOT_NAME="postgres-snapshot-$(date +%Y%m%d-%H%M%S)"

              # Create snapshot
              cat <<EOF | kubectl apply -f -
              apiVersion: snapshot.storage.k8s.io/v1
              kind: VolumeSnapshot
              metadata:
                name: $SNAPSHOT_NAME
                namespace: database
              spec:
                volumeSnapshotClassName: postgres-snapshot-class
                source:
                  persistentVolumeClaimName: data-postgres-0
              EOF

              # Delete snapshots older than 30 days
              kubectl get volumesnapshot -n database -o json | \
                jq -r '.items[] | select(.metadata.name | startswith("postgres-snapshot-")) |
                select(.metadata.creationTimestamp | fromnow | contains("days") and (split(" ")[0] | tonumber) > 30) |
                .metadata.name' | \
                xargs -r kubectl delete volumesnapshot -n database
          restartPolicy: OnFailure
```

### 5. Volume Expansion Automation Script

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-volume-monitor
  namespace: database
spec:
  schedule: "0 */6 * * *"  # Run every 6 hours
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: postgres-volume-monitor-sa
          containers:
          - name: volume-monitor
            image: bitnami/kubectl:latest
            command:
            - /bin/bash
            - -c
            - |
              # Get PostgreSQL pod name
              POD_NAME=$(kubectl get pods -n database -l app=postgres -o jsonpath='{.items[0].metadata.name}')

              # Check volume usage
              USAGE_PERCENT=$(kubectl exec -n database $POD_NAME -- df -h /var/lib/postgresql/data | tail -1 | awk '{print $5}' | sed 's/%//')

              # Expand volume if usage is 80% or higher
              if [ $USAGE_PERCENT -ge 80 ]; then
                # Get current PVC size
                CURRENT_SIZE=$(kubectl get pvc data-postgres-0 -n database -o jsonpath='{.spec.resources.requests.storage}')

                # Increase by 50% from current size
                NEW_SIZE=$(echo $CURRENT_SIZE | sed 's/Gi//' | awk '{print int($1 * 1.5)}')

                # Expand PVC
                kubectl patch pvc data-postgres-0 -n database -p "{\"spec\":{\"resources\":{\"requests\":{\"storage\":\"${NEW_SIZE}Gi\"}}}}"

                # Log message
                echo "$(date): Volume expanded from ${CURRENT_SIZE} to ${NEW_SIZE}Gi due to high usage (${USAGE_PERCENT}%)"
              fi
          restartPolicy: OnFailure
```

### 6. Job Template for Recovery Procedures

```yaml
# Job template for recovering from snapshot
apiVersion: batch/v1
kind: Job
metadata:
  name: postgres-restore
  namespace: database
spec:
  template:
    spec:
      serviceAccountName: postgres-restore-sa
      containers:
      - name: restore-manager
        image: bitnami/kubectl:latest
        command:
        - /bin/bash
        - -c
        - |
          # 1. Scale down StatefulSet
          kubectl scale statefulset postgres -n database --replicas=0

          # 2. Delete existing PVC (caution: data will be lost)
          kubectl delete pvc data-postgres-0 -n database

          # 3. Create PVC from snapshot
          cat <<EOF | kubectl apply -f -
          apiVersion: v1
          kind: PersistentVolumeClaim
          metadata:
            name: data-postgres-0
            namespace: database
          spec:
            accessModes:
              - ReadWriteOnce
            storageClassName: postgres-io2
            resources:
              requests:
                storage: 100Gi
            dataSource:
              name: ${SNAPSHOT_NAME}  # Snapshot name to restore
              kind: VolumeSnapshot
              apiGroup: snapshot.storage.k8s.io
          EOF

          # 4. Scale up StatefulSet
          kubectl scale statefulset postgres -n database --replicas=1

          # 5. Check recovery status
          sleep 60
          kubectl get pods -n database -l app=postgres
      restartPolicy: OnFailure
```

### 7. Monitoring and Alerting Setup

```yaml
# ServiceMonitor for PostgreSQL metrics collection (assuming Prometheus)
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: postgres-monitor
  namespace: database
spec:
  selector:
    matchLabels:
      app: postgres
  endpoints:
  - port: postgres
    interval: 15s
  namespaceSelector:
    matchNames:
    - database
```

### Design Explanation

#### 1. High-Performance Storage Selection

* **io2 Volume Type**: 高い IOPS を必要とする database workloads に最適化された EBS volume type
* **25,000 IOPS**: high-performance database operations に十分な IOPS provision
* **Encryption**: data-at-rest security のため EBS volume encryption を有効化

#### 2. StatefulSet を使用する利点

* **Stable Network ID**: 各 pod に predictable DNS names を提供します
* **Sequential Deployment**: database pods の安全な updates を保証します
* **Volume Management**: volumeClaimTemplates による自動 PVC 作成と管理

#### 3. Automated Backup Strategy

* **Regular Snapshots**: 毎日の automated snapshot creation
* **Retention Policy**: 30 日を超えた snapshots の automatic deletion
* **Tagging**: manageability 向上のため snapshots に tags を追加

#### 4. Volume Expansion Automation

* **Usage Monitoring**: 定期的な volume usage checks
* **Automatic Expansion**: usage が 80% 以上に達したら volume size を自動的に増加
* **allowVolumeExpansion**: StorageClass で volume expansion を有効化

#### 5. Recovery Procedures

* **Snapshot-Based Restore**: snapshot から新しい PVC を作成
* **Phased Approach**: StatefulSet を scale down し、PVC を置換して scale up
* **Status Check**: recovery 後に database status を確認

#### 6. Performance and Stability Considerations

* **Resource Requests and Limits**: 適切な CPU と memory allocation
* **Health Checks**: readinessProbe と livenessProbe による database status の監視
* **fsGroup**: 適切な file system permissions を設定

#### 7. Security Considerations

* **Encrypted Volumes**: data at rest を保護
* **Encrypted Snapshots**: backup data を保護
* **Secrets**: database credentials の安全な管理

この設計は、高い IOPS を必要とする PostgreSQL databases 向けに、automatic backup と recovery functionality、および volume expansion capability を含む高 performance な storage solution を提供します。さらに、monitoring と alerting setup により、storage 関連の問題を proactive に検出して対応できます。

</details>

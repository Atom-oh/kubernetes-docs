# EKS 存储测验 - 第 2 部分

本测验测试你对 Amazon EKS 中高级存储概念的理解，包括存储优化、备份与恢复策略，以及适用于各种工作负载的存储解决方案。

## 多项选择题

### 1. 在 Amazon EKS 中使用 StatefulSet 时，创建 PersistentVolumeClaims 的最有效方法是什么？

A. 为每个 pod 手动创建 PVC B. 使用 volumeClaimTemplates C. 使用 ConfigMap 定义 PVC D. 禁用动态预置

<details>

<summary>显示答案</summary>

**答案：B. 使用 volumeClaimTemplates**

**解释：** 在 Amazon EKS 中使用 StatefulSet 时，创建 PersistentVolumeClaims (PVCs) 的最有效方法是使用 `volumeClaimTemplates`。此方法会为 StatefulSet 中的每个 pod 自动创建唯一的 PVC，并且这些 PVC 独立于 pod 生命周期进行管理。

**volumeClaimTemplates 的主要特性：**

1.  **自动创建 PVC**：会为 StatefulSet 中的每个 pod 自动创建唯一的 PVC。

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
2. **稳定存储**：即使 pod 重启或重新调度，也会复用同一个 PVC。
3. **命名约定**：PVC 名称会按 `<volumeClaimTemplate-name>-<statefulset-name>-<ordinal>` 格式创建。示例：`data-mysql-0`、`data-mysql-1`、`data-mysql-2`
4. **顺序部署**：StatefulSet 会按顺序创建和删除 pods，因此存储操作也会按顺序处理。

**StatefulSet 示例：**

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

**volumeClaimTemplates 的优势：**

1. **自动化**：无需手动创建和管理 PVC。
2. **可扩展性**：调整 StatefulSet 副本数时会自动创建 PVC。
3. **数据持久性**：即使 pods 被删除，PVC 和数据也会保留。
4. **顺序保证**：保证 Pod 和 PVC 的创建与删除顺序。

**注意事项：**

1.  **PVC 删除策略**：删除 StatefulSet 时不会自动删除 PVC。这是为了防止数据丢失而设计的。

    ```bash
    # Check PVCs after StatefulSet deletion
    kubectl get pvc -l app=mysql

    # Manually delete PVCs if needed
    kubectl delete pvc data-mysql-0 data-mysql-1 data-mysql-2
    ```
2. **Storage Class 选择**：选择合适的 storage class 以满足工作负载需求。
   * EBS：单节点访问 (RWO)
   * EFS：多节点访问 (RWX)
3.  **Volume Binding Mode**：使用 `WaitForFirstConsumer` 确保 volumes 在 pod 被调度到的可用区中创建。

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer
    ```

其他选项的问题：

* **A. 为每个 pod 手动创建 PVC**：手动创建容易出错，缺乏可扩展性，并且无法利用 StatefulSet 自动化的优势。
* **C. 使用 ConfigMap 定义 PVC**：ConfigMap 用于存储配置数据，不能直接用于创建 PVC。
* **D. 禁用动态预置**：禁用动态预置会增加管理开销，因为必须手动创建 PVC。

</details>

### 2. 在 Amazon EKS 中优化 EBS volume 性能的最有效方法是什么？

A. 对所有 EBS volumes 使用 provisioned IOPS (io1) 类型 B. 根据工作负载需求选择合适的 EBS volume 类型 C. 为所有 EBS volumes 预置最大容量 D. 将所有 pods 放在同一个可用区

<details>

<summary>显示答案</summary>

**答案：B. 根据工作负载需求选择合适的 EBS volume 类型**

**解释：** 在 Amazon EKS 中优化 EBS volume 性能的最有效方法是根据工作负载需求选择合适的 EBS volume 类型。每种 EBS volume 类型都有不同的性能特征和成本结构，因此选择与工作负载特征匹配的 volume 类型非常重要。

**主要 EBS Volume 类型及特征：**

1.  **gp3 (General Purpose SSD)**：

    * 基准性能：3,000 IOPS，125MB/s 吞吐量
    * 最高性能：16,000 IOPS，1,000MB/s 吞吐量
    * 使用场景：启动 volumes、开发和测试环境、中小型数据库

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
2.  **io1/io2 (Provisioned IOPS SSD)**：

    * 最高性能：64,000 IOPS，1,000MB/s 吞吐量
    * 使用场景：I/O 密集型数据库、对延迟敏感的工作负载

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
3.  **st1 (Throughput Optimized HDD)**：

    * 最高性能：500 IOPS，500MB/s 吞吐量
    * 使用场景：大数据、数据仓库、日志处理

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-st1
    provisioner: ebs.csi.aws.com
    parameters:
      type: st1
    ```
4.  **sc1 (Cold HDD)**：

    * 最高性能：250 IOPS，250MB/s 吞吐量
    * 使用场景：不常访问的数据、归档

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc1
    provisioner: ebs.csi.aws.com
    parameters:
      type: sc1
    ```

**按工作负载选择最佳 Volume 类型：**

1.  **数据库工作负载**：

    * 需要高性能：io2 或高性能 gp3
    * 需要中等性能：gp3

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
2.  **日志和流式工作负载**：

    * 需要高吞吐量：st1 或高吞吐量 gp3

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
3.  **Web 和应用服务器**：

    * 需要中等性能：gp3

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

**其他性能优化策略：**

1. **Volume 大小优化**：某些 volume 类型（例如 gp2）会根据大小扩展性能。
2. **实例类型考虑**：使用 EBS-optimized instances 为 EBS volumes 获取专用带宽。
3.  **RAID 配置**：将多个 EBS volumes 配置为 RAID 0 以提升性能

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
4. **文件系统优化**：选择并优化适合工作负载的文件系统
   * XFS：适合大文件和并行 I/O
   * ext4：适合通用场景
5. **监控与调整**：监控 CloudWatch 指标，并根据需要调整 volume 类型或配置

其他选项的问题：

* **A. 对所有 EBS volumes 使用 provisioned IOPS (io1) 类型**：对所有工作负载使用 provisioned IOPS 不具备成本效益，并且某些工作负载可能更适合其他 volume 类型。
* **C. 为所有 EBS volumes 预置最大容量**：预置超过实际需要的 volumes 会产生不必要的成本。
* **D. 将所有 pods 放在同一个可用区**：这会损害高可用性，单个可用区故障可能会影响整个应用程序。

</details>

### 4. 在 Amazon EKS 中使用 FSx for Lustre 的主要优势是什么？

A. 成本效率 B. 设置简单 C. 高性能并行文件系统 D. 原生 EKS 集成

<details>

<summary>显示答案</summary>

**答案：C. 高性能并行文件系统**

**解释：** 在 Amazon EKS 中使用 FSx for Lustre 的主要优势是它提供高性能并行文件系统。FSx for Lustre 是一种完全托管的文件系统，专为高性能计算 (HPC)、机器学习和大数据分析等计算密集型工作负载而设计，可提供数百 GB/s 的吞吐量、数百万 IOPS 和亚毫秒级延迟。

**FSx for Lustre 的主要性能特征：**

1. **高吞吐量**：
   * 最高 1,000GB/s 吞吐量
   * 每 1TiB 存储最高 200MB/s 吞吐量（基于 SSD）
   * 适合处理大型数据集
2. **低延迟**：
   * 亚毫秒级延迟
   * 适合对延迟敏感的应用程序
3. **并行访问**：
   * 可从数千个 compute instances 同时访问
   * 通过并行处理提升性能
4. **可扩展性**：
   * 可扩展到数百 GB/s 吞吐量
   * 支持 PB 级数据集

**FSx for Lustre 与 EKS 集成：**

1.  **CSI Driver**：

    ```bash
    # Install FSx for Lustre CSI driver
    helm repo add aws-fsx-csi-driver https://kubernetes-sigs.github.io/aws-fsx-csi-driver/
    helm repo update
    helm upgrade -i aws-fsx-csi-driver aws-fsx-csi-driver/aws-fsx-csi-driver \
      --namespace kube-system \
      --set controller.serviceAccount.create=true \
      --set controller.serviceAccount.name=fsx-csi-controller-sa
    ```
2.  **StorageClass 配置**：

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
3.  **创建 PersistentVolumeClaim**：

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

**适合 FSx for Lustre 的工作负载：**

1. **机器学习和深度学习**：
   * 大型数据集训练
   * 分布式训练作业
   * 模型服务
2. **High-Performance Computing (HPC)**：
   * 科学模拟
   * 天气预报
   * 基因组学
3. **大数据分析**：
   * 大规模数据处理
   * 实时分析
   * ETL 作业
4. **媒体处理**：
   * 视频渲染
   * 图像处理
   * 内容创建

**S3 集成：**

FSx for Lustre 可与 Amazon S3 无缝集成，使你能够轻松使用高性能文件系统导入和处理 S3 数据。

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

**部署类型选项：**

1. **SCRATCH\_1**：
   * 临时存储和短期处理
   * 具备成本效益
   * 无数据复制
2. **SCRATCH\_2**：
   * 临时存储和短期处理
   * 服务器故障时进行数据复制
   * 可用性优于 SCRATCH\_1
3. **PERSISTENT**：
   * 长期存储和工作负载
   * 数据复制和自动恢复
   * 高持久性

**性能优化提示：**

1. **选择合适的吞吐量**：
   * SSD 存储：50、100、200 MB/s/TiB
   * HDD 存储：12、40 MB/s/TiB
2. **启用数据压缩**：
   * 通过 LZ4 压缩提升存储效率
   * 减少网络带宽使用
3. **文件系统大小优化**：
   * 更大的文件系统可提供更多服务器和更高的聚合性能
4.  **Mount Option 优化**：

    ```
    mount -t lustre -o noatime,flock file_system_dns_name@tcp:/mountname /mnt/fsx
    ```

其他选项的问题：

* **A. 成本效率**：FSx for Lustre 提供高性能，但通常比 EBS 或 EFS 更昂贵。
* **B. 设置简单**：FSx for Lustre 需要高级配置选项，设置也比 EBS 或 EFS 更复杂。
* **D. 原生 EKS 集成**：FSx for Lustre 并非与 EKS 原生集成；必须单独安装 CSI driver。

</details>

## 简答题

### 6. 在 Amazon EKS 中可以使用哪种 RAID 配置来提升 EBS volume 性能？

<details>

<summary>显示答案</summary>

**答案：** RAID 0 (Striping)

**详细解释：**

在 Amazon EKS 中可用于提升 EBS volume 性能的 RAID 配置是 RAID 0 (striping)。RAID 0 将数据分布到多个 EBS volumes 上，以提升 I/O 性能。

**RAID 0 的工作方式：**

RAID 0 通过将数据分布到多个磁盘来存储数据，每个磁盘处理总 I/O 工作负载的一部分，从而提升整体性能。例如，使用 2 个 EBS volumes 配置 RAID 0 理论上可以使吞吐量和 IOPS 翻倍。

**RAID 0 的主要特性：**

1. **性能提升**：I/O 操作在多个 volumes 上并行处理，从而提高吞吐量和 IOPS。
2. **容量聚合**：所有 volumes 的容量会聚合并作为一个大型 volume 使用。
3. **无容错能力**：如果一个 volume 发生故障，整个 RAID 阵列中的所有数据都会丢失。

**如何在 EKS 中配置 RAID 0：**

1.  **创建多个 PVC：**

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
2.  **在 Pod 中配置 RAID 0：**

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

**RAID 0 性能优化提示：**

1. **Volumes 数量**：通常 2-4 个 volumes 可提供最佳性能。过多 volumes 可能会增加管理开销。
2. **Volume 大小**：将所有 volumes 配置为相同大小，以均匀分布性能。
3. **Stripe Size**：根据工作负载选择合适的 stripe size。
   * 小型随机 I/O：较小的 stripe size（例如 4KB）
   * 大型顺序 I/O：较大的 stripe size（例如 64KB 或 128KB）
4. **实例类型**：使用 EBS-optimized instances 为 EBS volumes 获取专用带宽。

**RAID 0 使用场景：**

1. **高性能数据库**：需要高 IOPS 和吞吐量的数据库工作负载
2. **大数据处理**：大规模数据处理和分析工作负载
3. **媒体处理**：视频编码/解码、渲染等 I/O 密集型任务

**注意事项：**

1. **数据持久性**：RAID 0 没有容错能力，因此重要数据需要适当的备份策略。
2. **Volume 故障**：如果一个 volume 故障，所有数据都可能丢失，因此通过 snapshots 定期备份非常重要。
3. **复杂性**：RAID 配置会增加管理复杂性，因此只应在确实需要时使用。
4. **成本**：使用多个 EBS volumes 会增加存储成本。

**替代方案考虑：**

1. **高性能单 Volume**：使用 io2 或高性能 gp3 volumes 以保持简单性
2. **Instance Store**：对于临时数据，考虑 instance store volumes
3. **FSx for Lustre**：当需要非常高性能时，考虑并行文件系统

RAID 0 是提升 EBS volume 性能的有效方式，但应在考虑数据持久性和管理复杂性的前提下谨慎使用。

</details>

### 7. 在 Amazon EKS 中，可以使用哪些 mount options 设置读取和写入缓冲区大小，以优化 EFS 文件系统性能？

<details>

<summary>显示答案</summary>

**答案：** rsize and wsize

**详细解释：**

在 Amazon EKS 中，可用于设置读取和写入缓冲区大小以优化 EFS 文件系统性能的 mount options 是 `rsize`（读取缓冲区大小）和 `wsize`（写入缓冲区大小）。这些选项决定 NFS clients 与 EFS 文件系统通信时使用的数据块大小。

**rsize 和 wsize 的作用：**

1. **rsize（读取缓冲区大小）**：
   * NFS client 从服务器读取时使用的最大字节数
   * 较大的值允许通过更少的网络请求读取更多数据
   * 默认值通常为 1MB（1048576 字节）
2. **wsize（写入缓冲区大小）**：
   * NFS client 向服务器写入时使用的最大字节数
   * 较大的值允许通过更少的网络请求写入更多数据
   * 默认值通常为 1MB（1048576 字节）

**在 EKS 中设置 rsize 和 wsize：**

1.  **在 StorageClass 中设置：**

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
2.  **在 PersistentVolume 中设置：**

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

**选择最佳值：**

1. **通用推荐值**：
   * rsize=1048576 (1MB)
   * wsize=1048576 (1MB)
2. **按工作负载优化**：
   * 大型顺序读/写：较大的值（例如 1MB）
   * 小型随机读/写：较小的值（例如 32KB 或 64KB）
3. **网络状况考虑**：
   * 稳定网络：较大的值
   * 不稳定网络：较小的值（减少丢包时的重传开销）

**其他性能优化 Mount Options：**

1.  **timeo**：服务器响应等待时间（以 1/10 秒为单位）

    ```
    timeo=600  # 60 seconds
    ```
2.  **retrans**：超时前的重试次数

    ```
    retrans=2
    ```
3.  **noresvport**：连接恢复时使用新的 TCP port

    ```
    noresvport
    ```
4.  **noatime**：禁用文件访问时间更新

    ```
    noatime
    ```

**完整的优化 Mount Options 示例：**

```yaml
mountOptions:
  - rsize=1048576
  - wsize=1048576
  - timeo=600
  - retrans=2
  - noresvport
  - noatime
```

**性能监控和调优：**

1.  **性能测量**：

    ```bash
    # Read performance test
    dd if=/efs/testfile of=/dev/null bs=1M count=1000

    # Write performance test
    dd if=/dev/zero of=/efs/testfile bs=1M count=1000
    ```
2. **CloudWatch 指标监控**：
   * TotalIOBytes
   * DataReadIOBytes
   * DataWriteIOBytes
   * MetadataIOBytes
3. **渐进式调优**：
   * 使用不同的 rsize/wsize 值进行测试
   * 根据工作负载模式选择最佳值

正确设置 rsize 和 wsize 选项可以显著提升 EFS 文件系统性能，尤其适用于涉及大文件传输或高吞吐需求的工作负载。

</details>

### 9. 在 Amazon EKS 中使用 EBS volumes 时，AWS 针对数据持久性的 SLA (Service Level Agreement) 是什么？

<details>

<summary>显示答案</summary>

**答案：** 99.999%（5 个 9）

**详细解释：**

在 Amazon EKS 中使用 EBS volumes 时，AWS 针对数据持久性的 SLA (Service Level Agreement) 是 99.999%（5 个 9）。这意味着 Amazon EBS 年度数据丢失概率低于 0.001%。

**EBS 持久性的主要特性：**

1. **设计持久性**：Amazon EBS volumes 设计为提供 99.999% 的持久性。
2. **可用区复制**：EBS volume 数据会在单个可用区内的多台服务器之间自动复制。
3. **Annual Failure Rate (AFR)**：目标年度故障率范围为 0.1% - 0.2%。

**EBS Volume 类型持久性：**

所有 EBS volume 类型（gp2、gp3、io1、io2、st1、sc1）都具有相同的 99.999% 持久性设计。不过，io2 volumes 提供额外的持久性保证：

* **io2 Block Express**：除 99.999% 持久性外，还提供 99.999% 可用性 SLA

**数据保护增强方法：**

1.  **EBS Snapshots**：

    * 通过定期 snapshots 进行数据备份
    * Snapshots 存储在 S3 中，具有 99.999999999%（11 个 9）的持久性

    ```yaml
    apiVersion: snapshot.storage.k8s.io/v1
    kind: VolumeSnapshotClass
    metadata:
      name: ebs-snapshot-class
    driver: ebs.csi.aws.com
    deletionPolicy: Retain
    ```
2.  **跨区域 Snapshot 复制**：

    * 将 snapshots 复制到不同区域用于灾难恢复

    ```bash
    aws ec2 copy-snapshot \
      --source-region us-west-2 \
      --source-snapshot-id snap-0123456789abcdef0 \
      --destination-region us-east-1 \
      --description "Cross-region backup"
    ```
3.  **自动化备份策略**：

    * 使用 Amazon Data Lifecycle Manager 或 Kubernetes CronJob 进行自动备份

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

**EBS Volume 故障场景和恢复：**

1. **Volume 损坏**：
   * 症状：I/O 错误、性能下降
   * 恢复：从最新 snapshot 创建新 volume
2. **可用区故障**：
   * 症状：Volume 无法访问
   * 恢复：在不同可用区中从 snapshot 恢复 volume
3. **意外数据删除**：
   * 恢复：从 snapshot 恢复到特定时间点

**EBS 持久性最佳实践：**

1. **定期 Snapshots**：
   * 为重要数据创建每日或更高频率的 snapshots
   * 实施 snapshot 保留策略
2. **Snapshot 测试**：
   * 定期测试从 snapshots 恢复
   * 记录并演练恢复流程
3. **多区域策略**：
   * 将关键数据的 snapshots 复制到不同区域
   * 建立灾难恢复计划
4. **监控与告警**：
   * 监控 EBS volume 健康状况
   * 设置 CloudWatch alarms

**EBS 与其他 AWS 存储服务持久性比较：**

| 服务           | 持久性                 | 可用性                         |
| -------------- | ---------------------- | ------------------------------ |
| Amazon EBS     | 99.999%                | 99.95-99.999%（因类型而异）    |
| Amazon EFS     | 99.999999999%（11 个 9） | 99.99%                         |
| Amazon S3      | 99.999999999%（11 个 9） | 99.99%                         |
| FSx for Lustre | 99.999%                | 99.95%                         |

Amazon EBS 的 99.999% 持久性为大多数工作负载提供了足够的数据保护，但对于关键数据，建议通过定期 snapshots 和多区域备份策略实施额外保护层。

</details>

## 实践题

### 10. 为 Amazon EKS cluster 中的数据库工作负载设计一个高性能存储解决方案。创建满足以下要求的 storage classes、persistent volume claims 和 StatefulSet：

* PostgreSQL 数据库需要高 IOPS
* 自动备份和恢复功能
* Volume 扩展能力

<details>

<summary>显示答案</summary>

**答案：**

以下是在 Amazon EKS cluster 中为数据库工作负载设计高性能存储解决方案的方法：

### 1. 高性能 StorageClass 定义

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

### 2. PostgreSQL StatefulSet 定义

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

### 3. PostgreSQL Service 定义

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

### 4. 用于自动备份的 VolumeSnapshotClass 和 CronJob

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

### 5. Volume 扩展自动化脚本

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

### 6. 用于恢复流程的 Job 模板

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

### 7. 监控和告警设置

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

### 设计说明

#### 1. 高性能存储选择

* **io2 Volume Type**：针对需要高 IOPS 的数据库工作负载优化的 EBS volume 类型
* **25,000 IOPS**：为高性能数据库操作预置足够的 IOPS
* **Encryption**：启用 EBS volume 加密以保护静态数据

#### 2. 使用 StatefulSet 的优势

* **稳定网络 ID**：为每个 pod 提供可预测的 DNS 名称
* **顺序部署**：确保数据库 pods 的安全更新
* **Volume 管理**：通过 volumeClaimTemplates 自动创建和管理 PVC

#### 3. 自动化备份策略

* **定期 Snapshots**：每天自动创建 snapshots
* **保留策略**：自动删除超过 30 天的 snapshots
* **标签**：为 snapshots 添加标签以提升可管理性

#### 4. Volume 扩展自动化

* **使用率监控**：定期检查 volume 使用情况
* **自动扩展**：当使用率达到 80% 或更高时自动增加 volume 大小
* **allowVolumeExpansion**：在 StorageClass 中启用 volume 扩展

#### 5. 恢复流程

* **基于 Snapshot 的恢复**：从 snapshot 创建新的 PVC
* **分阶段方法**：缩减 StatefulSet、副本替换 PVC、再扩展副本
* **状态检查**：恢复后验证数据库状态

#### 6. 性能和稳定性考虑

* **Resource Requests and Limits**：适当分配 CPU 和内存
* **Health Checks**：通过 readinessProbe 和 livenessProbe 监控数据库状态
* **fsGroup**：设置适当的文件系统权限

#### 7. 安全考虑

* **加密 Volumes**：保护静态数据
* **加密 Snapshots**：保护备份数据
* **Secrets**：安全管理数据库凭证

此设计为需要高 IOPS 的 PostgreSQL 数据库提供高性能存储解决方案，包括自动备份与恢复功能以及 volume 扩展能力。此外，监控和告警设置可主动检测并响应与存储相关的问题。

</details>

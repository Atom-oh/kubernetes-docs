# EKS 存储测验 - 第 2 部分

> **最后更新**：2026 年 9 月 11 日

本测验涵盖存储选择、StatefulSet 声明、S3/Mountpoint、克隆、备份和恢复。示例会复用本章中已准备好的驱动程序、类和专用命名空间。本次审查未执行云资源预置、数据库恢复或性能基准测试。使用示例前，请检查资源所有权并替换占位符。

## 选择题

### 1. StatefulSet 应如何为每个序号分配独立的 PVC？

- A. 在 ConfigMap 中手动为每个声明命名
- B. 使用 volumeClaimTemplates
- C. 让所有副本使用相同的数据库目录
- D. 禁用 CSI 驱动程序

<details>
<summary>显示答案</summary>

**答案：B**

`volumeClaimTemplates` 会为每个 StatefulSet 序号创建独立的声明，命名格式为 `<template>-<statefulset>-<ordinal>`。Pod 重启后通常会复用其声明，但具体情况取决于存储拓扑和声明生命周期。StatefulSet 不会在副本之间复制数据库数据。

`OrderedReady` 是默认的 Pod 管理策略；`Parallel` 会改变扩缩容行为。无法普遍保证每个 PVC 的创建/删除都会遵循 Pod 顺序。可通过 `persistentVolumeClaimRetentionPolicy` 配置 PVC 保留策略；默认值为 Retain，而 Delete 可在缩容/删除时移除声明。PV reclaimPolicy 是单独的后端生命周期选择。

以下三个副本仅演示各自独立的持久化标记文件。它们**不是复制式数据库**。无头 Service 提供身份；这个休眠的文件演示不会在其示例 Service 端口上实现 HTTP 服务器。复用本章的 `ebs-gp3` 类：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: stateful-files
  namespace: storage-demo
spec:
  clusterIP: None
  selector:
    app: stateful-files
  ports:
  - name: unused-demo
    port: 8080
    targetPort: 8080
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: stateful-files
  namespace: storage-demo
spec:
  serviceName: stateful-files
  replicas: 3
  podManagementPolicy: OrderedReady
  selector:
    matchLabels:
      app: stateful-files
  persistentVolumeClaimRetentionPolicy:
    whenDeleted: Retain
    whenScaled: Retain
  template:
    metadata:
      labels:
        app: stateful-files
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: file-owner
        image: busybox:1.38.0
        command:
        - sh
        - -c
        args:
        - |
          set -eu
          if [ ! -e /data/owner ]; then (set -C; printf "%s\n" "$POD_NAME" > /data/owner); fi
          cat /data/owner
          sleep 3600
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        resources:
          requests:
            cpu: 10m
            memory: 16Mi
          limits:
            cpu: 100m
            memory: 64Mi
        volumeMounts:
        - name: data
          mountPath: /data
        env:
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
  volumeClaimTemplates:
  - metadata:
      name: data
      labels:
        storage-demo: stateful-files
    spec:
      accessModes:
      - ReadWriteOnce
      storageClassName: ebs-gp3
      resources:
        requests:
          storage: 10Gi
```



```bash
kubectl -n storage-demo get pvc -l storage-demo=stateful-files -o wide
```

声明模板上的标签使检查时使用的选择器具有实际意义。不要把删除保留的声明作为常规 Pod 清理操作。WFFC 会根据调度约束选择合适的卷可用区；它不会让 EBS 数据在所有可用区都可用。RWO 是节点级访问约束，并不保证只能由一个 Pod 访问；如果需要单 Pod 访问，请使用受支持的 RWOP。

</details>

### 2. EBS 性能选择应依据什么？

- A. 始终选择 io1
- B. 根据测得的工作负载需求和卷/实例限制
- C. 始终预置最大容量
- D. 将所有应用放在一个可用区

<details>
<summary>显示答案</summary>

**答案：B**

测量延迟、IOPS、I/O 大小、队列深度和吞吐量，然后根据卷和实例的 EBS 限制进行匹配。即使每个卷预置的性能很充足，实例也可能成为多个卷的瓶颈。文件系统、初始化、缓存和应用行为同样重要。

| 类型 | 当前公布的上限，具体取决于条件 | 典型考量 |
|---|---|---|
| gp3 | 区域：80,000 IOPS /2,000 MiB/s；Outposts 更低 | 基线为 3,000 IOPS /125 MiB/s，可单独付费设置性能 |
| io1 |64,000 IOPS /1,000 MiB/s | 预置 IOPS，受实例/大小限制 |
| io2 Block Express |256,000 IOPS /4,000 MiB/s | 取决于受支持的 Nitro/大小/IOPS 及工作负载需求 |
| st1 |500MiB/s | 面向吞吐量的 HDD，具有顺序访问/突发行为 |
| sc1 |250MiB/s | 用于不频繁顺序访问的 HDD |

此前的 gp3 示例设置为 16,000 IOPS/1,000 MiB/s，仍然有效；但它们并非当前通用最大值。gp2 的基线/突发性能受容量影响，而 gp3 的性能可在满足其比率限制的前提下单独预置。没有哪种卷类型能自动适用于所有数据库、日志或 Web 服务器。RAID0 是另一种权衡方式，下文会讨论，并非 CSI 的默认优化方案。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: gp3
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
```

</details>

### 3. FSx for Lustre 的主要架构优势是什么？

- A. 保证成本最低
- B. 不需要驱动程序或网络前置条件
- C. 为适用的工作负载提供并行文件系统
- D. 保证每个 PVC 都达到 1,000 GB/s

<details>
<summary>显示答案</summary>

**答案：C**

FSx for Lustre 为受支持的 HPC、ML、分析和媒体工作负载提供托管式并行文件系统。应一并选择部署类型、客户端/内核、容量、预置吞吐量和网络。营销材料中的聚合最大值并不代表任意小型 PVC 的性能。

SCRATCH_1/SCRATCH_2 面向可重新生成的临时数据；仅仅使用 PV 并不会让 SCRATCH_2 获得持久化服务器复制能力。PERSISTENT_1/PERSISTENT_2 支持的存储和吞吐量选项各不相同。例如，PERSISTENT_2 SSD 提供 125/250/500/1,000 MB/s/TiB；不要把通用的 200MB/s/TiB 或 1,000 GB/s 声明套用到每个文件系统。本次审查未验证此前的聚合性能声明。

按照本章所述准备托管式附加组件或由你负责管理的兼容驱动程序。以下示例保留了受支持的 `s3ImportPath` 参数；导入/导出需要兼容的部署、权限以及存储库策略/任务。仅创建 CSI 资源不会自动实现 S3 双向同步：

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre-import-demo
provisioner: fsx.csi.aws.com
reclaimPolicy: Retain
parameters:
  subnetId: subnet-0123456789abcdef0
  securityGroupIds: sg-0123456789abcdef0
  deploymentType: SCRATCH_2
  dataCompressionType: NONE
  s3ImportPath: s3://replace-with-owned-data-bucket/training/
```

PVC 请求决定动态文件系统容量；StorageClass 没有通用的 storageCapacity 字段。必须针对数据和并发情况测量压缩和条带化。更高的并行度、更多条带或 LZ4 并不总能提升性能。应使用托管式 EKS 附加组件目录选择兼容方案；“没有原生 EKS 集成”并不是拒绝 FSx 的准确理由。

</details>

### 4. 哪种 Mountpoint CSI 预置模式是正确的？

- A. 动态 s3-sc 会创建存储桶
- B. 将静态 PV/PVC 绑定到现有存储桶
- C. PVC 容量字段会设置 S3 配额
- D. 文件系统 PVC 会自动创建 EFS 文件系统

<details>
<summary>显示答案</summary>

**答案：B**

使用 `s3.csi.aws.com`、现有存储桶、在两个对象上都设置空的 storageClassName、显式填写 claimRef/volumeName，并使用唯一的 volumeHandle。将 CLI 选项放入 PV 的 mountOptions。Kubernetes 容量元数据并不是 S3 容量限制。

</details>

### 5. 使用 authenticationSource: pod 时，会使用哪个身份？

- A. 始终使用控制器 IAM 角色
- B. PV 中嵌入的静态密钥
- C. 应用 ServiceAccount 所支持的 Pod Identity 或 IRSA
- D. 创建 PVC 的用户在工作站上的凭证

<details>
<summary>显示答案</summary>

**答案：C**

CSI 2.8 支持 Pod 级别的 Pod Identity 和 IRSA；该卷不会使用驱动程序凭证。必须配置角色、关联/信任关系、必要时的代理，以及存储桶/KMS 权限。仅有 ServiceAccount 注解并不等同于 IAM 角色。

</details>

### 6. CSI v2 会把配置的 emptyDir 缓存放在哪里？

- A. Mountpoint Pod 中
- B. 任意具有相同路径的应用 Pod emptyDir 中
- C. 按定义存放在 S3 存储桶中
- D. 自动存放在 GPU 实例的 NVMe 上

<details>
<summary>显示答案</summary>

**答案：A**

使用 `cache: emptyDir`、`cacheEmptyDirSizeLimit` 等 cache volumeAttributes。Memory 表示 tmpfs RAM。Mountpoint 元数据 TTL 的单位是秒，独立的 max-cache-size 单位是 MiB，读写分块大小的单位是字节。特定版本的标志必须与其内嵌的 Mountpoint 二进制文件相匹配。

</details>

### 7. 为什么缓存挂载可能不会立即显示外部 S3 的更改？

- A. S3 的列表操作始终采用最终一致性
- B. 配置的缓存 TTL 可能会保留旧条目/负缓存条目
- C. 所有 S3 写入都需要重启 CSI
- D. PV 容量太小

<details>
<summary>显示答案</summary>

**答案：B**

S3 的读取/列表操作具有强一致性。可选的 Mountpoint 缓存会改变客户端所观察到的内容，直到 TTL 到期。不要把缓存行为误认为是 S3 的一致性模型。如果可重复性很重要，请使用不可变数据集前缀或适当的缓存设置。

</details>

### 8. 哪组条件适用于原生 EBS PVC 克隆？

- A. 任意命名空间和任意可用区
- B. 始终继承源存储类
- C. 无需协调即可保证克隆与应用一致
- D. 受支持的驱动程序、相同的命名空间/源可用区、兼容模式和足够大的目标卷

<details>
<summary>显示答案</summary>

**答案：D**

EBS CSI 1.66 使用真正的原生卷复制路径。常规 PVC dataSource 要求源和目标位于同一命名空间；EBS 副本仍位于源卷所在的可用区。明确设置存储类，并请求至少与源卷相同的容量。卷可用之后，后台初始化可能仍未完成；为满足一致性要求，应暂停应用写入。

</details>

### 9. 哪个示例符合 EBS CSI 1.66 动态 Multi-Attach？

- A. gp3 + RWO + multiAttachEnabled:true
- B. io2 + RWOP + 独立 ext4 写入者
- C. io2 + RWX + Raw Block，并协调应用 I/O
- D. 任意 EBS 类型跨多个可用区

<details>
<summary>显示答案</summary>

**答案：C**

驱动程序会将 io2 多写入者块设备能力映射到 Multi-Attach；不存在通用的 SC multiAttachEnabled 开关。符合条件的 Nitro 实例必须位于卷所在的可用区。共享设备本身不会自动提供写入协调或隔离机制。与笼统声称“无法调整大小”不同，io2 在满足服务/驱动程序条件时支持修改容量/IOPS。

</details>

### 10. 拥有 CSI 快照的 Velero 备份过期后会发生什么？

- A. Velero 可以将内容的 deletionPolicy 设为 Delete，即使类设置的是 Retain 也能删除快照
- B. Retain 始终会永久保留快照
- C. 只会删除 PVC
- D. 快照会自动变成可移植的 S3 对象

<details>
<summary>显示答案</summary>

**答案：A**

Velero 1.18 管理其 CSI 快照生命周期。应谨慎配置备份 TTL；如有需要，请使用单独的保留/归档流程。其集成的 CSI 支持仍需要启用 EnableCSI；备份元数据、原生 CSI 快照和复制的卷数据是不同的内容。

</details>

## 简答题

### 11. RAID0 提供什么能力，EKS 设计必须考虑哪些事项？

<details>
<summary>显示答案</summary>

**答案：条带化，不提供冗余**

RAID0 会将数据块分布到多个卷上，并汇总可用容量。任何一个成员卷发生故障，都可能导致整个阵列无法使用；它不是备份或高可用性解决方案。只有当应用、文件系统、CPU 和实例 EBS 限制都允许时，两个相同的卷才有可能在理论上提供约为单个卷两倍的性能。这只是理论上限，并非经过测量的 2×结果。

以文件系统模式挂载到 `/volume1` 的 PVC 是一个目录，不是供 mdadm 使用的原始磁盘。真正的块设备设计需要 `volumeMode: Block`、`volumeDevices`、准确的卷标识、经授权的存储组件，以及明确的空设备初始化与现有阵列组装流程。绝不能在每次应用重启时都格式化磁盘。要规划同一节点/可用区内的挂载、重新调度、权限、扩容以及多卷一致性备份/恢复。

因此，先前特权 Pod 中无条件执行 mdadm/mkfs 的流程并不适合作为复制粘贴的操作指南。旧示例中的 2–4 个卷以及 4/64/128KiB 条带大小都是尚未验证测量结果的调优候选值，并非通用最优值。在接受这类额外复杂性之前，应先评估合适的单个 gp3/io2 卷、可再现的实例存储临时数据或 FSx。

</details>

### 12. EFS 的 rsize 和 wsize 控制什么？

<details>
<summary>显示答案</summary>

**答案：NFS 读写 RPC 负载的最大大小**

它们不是 TCP 套接字缓冲区大小。AWS 建议读写都设置为 1,048,576 字节（1MiB），并通过受支持的 NFS/EFS 挂载路径使用 `hard,timeo=600,retrans=2,noresvport`。timeo 的单位是十分之一秒，因此 600 表示 60 秒。在 hard 挂载中，retrans=2 并不表示尝试两次后就放弃操作。没有工作负载证据时，不要因随机 I/O 或丢包而擅自采用更小的值。应在 StorageClass/PV 上配置这些选项，而不是在 Pod 卷上配置；EFS 不支持 nconnect。

复用本章中由你负责管理的 EFS 文件系统和访问点配置：

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-tuned
provisioner: efs.csi.aws.com
reclaimPolicy: Retain
mountOptions:
- tls
- rsize=1048576
- wsize=1048576
- hard
- timeo=600
- retrans=2
- noresvport
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: '750'
  uid: '1000'
  gid: '1000'
  basePath: /storage-demo
  ensureUniqueDirectory: 'true'
```

如需进行经授权的写入测试，请使用已经验证过的临时目录和唯一文件，而不是可能覆盖数据的固定路径 `/efs/testfile`。以下 GNU dd 示例会写入 64 MiB，并且只清理它创建的文件/目录。读取可能命中客户端缓存，因此仅凭这些耗时数据无法确定 EFS 的冷读取吞吐量：

```bash
set -euo pipefail
: "${EFS_TEST_DIR:?Set an approved disposable directory on the verified EFS mount}"
test -d "$EFS_TEST_DIR" && test -w "$EFS_TEST_DIR"
EFS_TEST_PATH=$(mktemp -d "$EFS_TEST_DIR/efs-test.XXXXXX")
cleanup() { rm -f -- "$EFS_TEST_PATH/payload"; rmdir -- "$EFS_TEST_PATH"; }
trap cleanup EXIT
time dd if=/dev/zero of="$EFS_TEST_PATH/payload" bs=1M count=64 conv=fsync
time dd if="$EFS_TEST_PATH/payload" of=/dev/null bs=1M
```

本次审查未进行 EFS 性能测试。应使用适当的 CloudWatch 统计数据/周期，将客户端/应用延迟和并发情况与 EFS 的 TotalIOBytes、DataReadIOBytes、DataWriteIOBytes 和 MetadataIOBytes 关联起来。字节计数器除以测量时间间隔后，才能得到吞吐速率。

</details>

### 13. EBS 可用性 SLA 与持久性设计有何不同？

<details>
<summary>显示答案</summary>

**答案：它们描述的是不同的属性和条件**

EBS SLA 是有关可用性/服务抵扣的协议，并非适用于所有情况的 99.999% 数据持久性 SLA。其区域级承诺对跨多个可用区的合格并发部署采用 99.99% 的阈值；单卷承诺采用 99.9%。应阅读协议中的定义、例外情况和抵扣条件，不要把任一数字视为无条件保证。

| 公布的设计特性 | 卷类型 |
|---|---|
|99.8–99.9% 持久性；0.1–0.2% AFR | gp3/gp2/io1 和 HDD 类型 |
|99.999% 持久性；0.001% AFR | io2 Block Express |

此协议中没有单独的 io2“五个九可用性 SLA”。AFR/设计持久性并不等于特定应用丢失全部数据的概率；数据损坏、删除、备份和恢复架构都很重要。EBS 复制发生在单个可用区内，并不会自动实现跨可用区数据库复制。

在需要时使用与应用一致的备份，保留独立恢复点，测试恢复，并监控卷/应用健康状况。要从可用区故障中恢复，请将可访问的快照恢复到获准的可用区；要恢复已删除的记录，请使用合适的恢复点或数据库时间点恢复机制。单独的块设备快照无法提供任意时间点的恢复能力。

跨区域复制快照是独立操作，需要源/目标/KMS 权限和完成状态检查。以下命令仅用于说明快照创建方式，并非已执行的恢复测试。请先确认源快照的所有权和允许的目标区域，记录返回的 SnapshotId，并等待复制完成/检查复制状态，然后再依赖该副本：

```bash
set -euo pipefail
: "${SOURCE_REGION:?Set the source snapshot Region}"
: "${DESTINATION_REGION:?Set the recovery Region}"
: "${SOURCE_SNAPSHOT_ID:?Select an owned completed snapshot}"
: "${DESTINATION_KMS_KEY_ARN:?Set a usable customer managed key in the recovery Region}"
STATE=$(aws ec2 describe-snapshots --region "$SOURCE_REGION" \
  --snapshot-ids "$SOURCE_SNAPSHOT_ID" --query 'Snapshots[0].State' --output text)
test "$STATE" = completed || { echo "Snapshot is not completed"; exit 1; }
aws ec2 copy-snapshot --region "$DESTINATION_REGION" --source-region "$SOURCE_REGION" \
  --source-snapshot-id "$SOURCE_SNAPSHOT_ID" --encrypted --kms-key-id "$DESTINATION_KMS_KEY_ARN" \
  --description "Reviewed storage recovery copy" --output json
```

AWS CLI 镜像不会自动包含 kubectl，也不会自动授予 Kubernetes/IAM 权限。应使用 Velero、Data Lifecycle Manager 或 AWS Backup 等受支持的备份管理工具，并配置适当的作用范围，而不是使用未配置的 CronJob。应分别比较各存储服务实际的存储类/部署 SLA 和持久性设计；列出适用于所有服务的统一百分比表会造成误导。

</details>

## 实践题

### 14. 设计一个有明确限制的数据库存储和恢复工作流。

<details>
<summary>显示答案</summary>

**答案：经过审查的蓝图，而非自动恢复保证**

针对具有高 I/O 需求、定期备份、经验证的恢复能力和受控扩容的 PostgreSQL 工作负载进行设计。以下内容是**培训蓝图**，不是经过测试的生产部署。复用专用的 `database` 命名空间、已准备好的 Secret `postgres-secret/password`、兼容的 EBS/快照驱动程序，以及由你负责管理的 Velero 安装。未经资源所有者同意，不要将其应用到现有资源上。

#### 存储和数据库

保留原先的 25,000 IOPS 分配，作为 io2 设置示例；其是否足够需要通过测量和实例限制来确认。加密使用配置的/默认的 EBS 密钥。如果选择客户自主管理的密钥，请准备真实的 ARN/密钥策略/驱动程序授权，而不要使用虚构的 kmsKeyId。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: postgres-io2
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: io2
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
  iops: '25000'
```



```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: database
spec:
  clusterIP: None
  selector:
    app: postgres
  ports:
  - name: postgres
    port: 5432
    targetPort: postgres
---
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
  persistentVolumeClaimRetentionPolicy:
    whenDeleted: Retain
    whenScaled: Retain
  template:
    metadata:
      labels:
        app: postgres
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 999
        runAsGroup: 999
        fsGroup: 999
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: postgres
        image: postgres:14.24
        env:
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        - name: POSTGRES_PASSWORD_FILE
          value: /run/postgres-secret/password
        ports:
        - name: postgres
          containerPort: 5432
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          periodSeconds: 5
        resources:
          requests:
            cpu: '2'
            memory: 4Gi
          limits:
            cpu: '4'
            memory: 8Gi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
        - name: socket
          mountPath: /var/run/postgresql
        - name: tmp
          mountPath: /tmp
        - name: password
          mountPath: /run/postgres-secret
          readOnly: true
      volumes:
      - name: socket
        emptyDir: {}
      - name: tmp
        emptyDir: {}
      - name: password
        secret:
          secretName: postgres-secret
          defaultMode: 288
          items:
          - key: password
            path: password
  volumeClaimTemplates:
  - metadata:
      name: data
      labels:
        app: postgres
        storage-review: database-demo
    spec:
      accessModes:
      - ReadWriteOnce
      storageClassName: postgres-io2
      resources:
        requests:
          storage: 100Gi
```

此配置遵循第 1 部分中已验证的 PostgreSQL 14.24 镜像约定：UID/GID 999、挂载的密码文件、可写的 socket/tmp 卷，以及 PGDATA 子目录。14 主版本将于 2026 年 11 月 12 日结束支持；保留该教学版本并不意味着它适合新的生产部署。请选择合适且仍受支持的主版本，并制定迁移计划。单副本 StatefulSet 不具备高可用性；pg_isready 是连接就绪检查，不是数据完整性或恢复测试。

#### 备份和保留

使用本章的快照控制器前置条件和 `ebs-snapshot-class`。手动创建恢复点之前，请暂停数据库写入，或使用受支持的数据库备份协议。实际的 StatefulSet 声明名为 **data-postgres-0**：

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: postgres-review-snapshot
  namespace: database
  labels:
    storage-review: database-demo
spec:
  volumeSnapshotClassName: ebs-snapshot-class
  source:
    persistentVolumeClaimName: data-postgres-0
```

在将快照视为可恢复之前，应等待 readyToUse，并检查 restoreSize/content/driver。快照加密遵循源卷/密钥配置；VolumeSnapshotClass 中不受支持的 encrypted/tagSpecification 密钥不会配置快照加密。当前驱动程序支持特定的快照标签参数；使用前必须对照该驱动程序的版本进行检查，不要直接照搬卷类参数。

以下命令会生成一个 TTL 为 30 天的 Velero 每日计划。通过备份管理工具应用前，应检查 CSI 类选择以及数据库一致性钩子/协议。即使原始类设置为 Retain，Velero TTL 也可能删除其 CSI 快照。应针对备份失败/缺失设置告警，并定期测试恢复；仅有计划并不能证明数据可恢复：

```bash
velero schedule create database-daily --schedule="0 1 * * *" \
  --include-namespaces=database --ttl=720h0m0s -o yaml > database-backup-schedule-review.yaml
```

#### 有界扩容规划

不要根据过时指标，每六小时盲目扩容 50%。以下仅供审查的规划器要求 PVC 处于 Bound 状态、对应的类支持扩容、没有待处理的调整，并且新鲜指标必须标识相同的 PVC UID，且包含有效的文件系统字节数。它支持常见的十进制/二进制 Kubernetes 数量格式，并会拒绝不支持的输入。当使用率达到 80% 时，它会建议扩容至至少为当前请求容量 1.5 倍的大小，并设置示例上限 500 Gi，同时提供 UID/resourceVersion/当前容量前置条件。它不会修改 Kubernetes 资源。

从准确的对象中获取最新的 `pvc.json` 和 `storageclass.json`。`trusted-metrics.json` 必须包含 namespace、pvcName、pvcUID、带时区的 observedAt、usedBytes 和 capacityBytes；这些数据应来自实际挂载的文件系统。调用方提供的 UID 本身并不能证明指标来源可信。在任何操作员/控制器应用经审查的补丁之前，请验证采集器/挂载映射、配额、成本和驱动程序限制。

```python
"""Generate a review-only plan from captured PVC, StorageClass and trusted metrics."""
import datetime,decimal,json,math,re,sys
D=decimal.Decimal
def quantity(s):
    match=re.fullmatch(r'([+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))([EPTGMK]i|[EPTGMk]|m|[eE][+-]?[0-9]+)?',s)
    if not match:raise ValueError('Unsupported/nonpositive quantity: '+s)
    value,suffix=D(match[1]),match[2] or ''
    if suffix.endswith('i'):value*=D(1024)**('KMGTPE'.index(suffix[0])+1)
    elif suffix in ['k','M','G','T','P','E']:value*=D(1000)**('kMGTPE'.index(suffix)+1)
    elif suffix=='m':value/=1000
    elif suffix:value*=D(10)**int(suffix[1:])
    if value<=0:raise ValueError('Capacity must be positive')
    return value
def plan(pvc,sc,metrics,now):
    meta,spec,status=pvc['metadata'],pvc['spec'],pvc['status']
    if (meta['namespace'],meta['name'])!=('database','data-postgres-0'):
        raise ValueError('Unexpected PVC')
    if status.get('phase')!='Bound' or not spec.get('volumeName'):
        raise ValueError('PVC is not Bound')
    if sc['metadata']['name']!=spec['storageClassName'] or sc.get('allowVolumeExpansion') is not True:
        raise ValueError('StorageClass mismatch or expansion disabled')
    if any(c.get('status')=='True' and c.get('type') in ['Resizing','FileSystemResizePending'] for c in status.get('conditions',[])):
        raise ValueError('Resize is pending')
    if status.get('allocatedResourceStatuses',{}).get('storage'):
        raise ValueError('Storage allocation is pending')
    requested=quantity(spec['resources']['requests']['storage'])
    if requested!=quantity(status['capacity']['storage']):
        raise ValueError('Request and capacity differ; inspect before another resize')
    if (metrics['namespace'],metrics['pvcName'],metrics['pvcUID'])!=(meta['namespace'],meta['name'],meta['uid']):
        raise ValueError('Metrics identify a different PVC')
    seen=datetime.datetime.fromisoformat(metrics['observedAt'].replace('Z','+00:00'))
    if seen.tzinfo is None or not 0<=(now-seen).total_seconds()<=300:
        raise ValueError('Metrics are stale or future-dated')
    used,capacity=D(str(metrics['usedBytes'])),D(str(metrics['capacityBytes']))
    if not used.is_finite() or not capacity.is_finite() or not 0<=used<=capacity<=requested or capacity<=0:
        raise ValueError('Invalid filesystem metrics')
    if used/capacity<D('0.8'):return {'reviewOnly':True,'action':'none','reason':'Below 80%'}
    target=math.ceil(max(requested*D('1.5'),used/D('0.7'))/D(1024**3))
    if target>500:return {'reviewOnly':True,'action':'manual-review','reason':'Illustrative 500Gi cap exceeded'}
    return {'reviewOnly':True,'action':'propose-resize','target':str(target)+'Gi','patch':[
      {'op':'test','path':'/metadata/uid','value':meta['uid']},
      {'op':'test','path':'/metadata/resourceVersion','value':meta['resourceVersion']},
      {'op':'test','path':'/spec/resources/requests/storage','value':spec['resources']['requests']['storage']},
      {'op':'replace','path':'/spec/resources/requests/storage','value':str(target)+'Gi'}]}
if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('Usage: resize-plan.py pvc.json storageclass.json trusted-metrics.json')
    inputs=[]
    for name in sys.argv[1:]:
        with open(name) as f:inputs.append(json.load(f))
    print(json.dumps(plan(*inputs,datetime.datetime.now(datetime.timezone.utc)),indent=2))
```

如果资源发生变化，请重新生成计划；不要移除未满足的前置条件，也不要在补丁应用失败后记录成功。批准扩容后，应检查 PVC 条件和实际文件系统容量。应通过受支持的资源管理流程，使 StatefulSet 模板中未来声明的容量与之保持一致；不要通过编辑 PV 容量来伪造扩容完成。

#### 恢复候选卷

绝不要让会重试的 Job 把缩容并删除在线声明作为恢复的第一步。请使用独立的候选卷，其容量至少要达到 restoreSize；以下 100 Gi 示例假定该恢复点不大于此容量。如果原始声明已经扩容，请相应调整候选卷：

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-restore-candidate
  namespace: database
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: postgres-io2
  resources:
    requests:
      storage: 100Gi
  dataSource:
    name: postgres-review-snapshot
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
```

调度一个隔离的、兼容 PostgreSQL 的使用者，并配置所需凭证/版本；等待绑定/恢复，并在受控切换前验证应用查询和数据。保留原始数据并制定回退方案。为已有恢复数据库设置新的 POSTGRES_PASSWORD 环境变量，并不会重置数据库凭证。

#### 监控

PostgreSQL 5432 使用的是数据库协议，而不是 Prometheus HTTP。应准备经过审查的 postgres-exporter 工作负载，将其标签设为 `app: postgres-exporter`，并提供命名为 `metrics` 的 9187 端口以及作用范围适当的数据库凭证。此 Service 和 ServiceMonitor 会选择该 exporter，但不会安装它。确保 Prometheus 会选择此 ServiceMonitor/命名空间，并且 NetworkPolicy/TLS/身份验证设置与部署相匹配：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres-exporter
  namespace: database
  labels:
    monitoring: postgres-exporter
spec:
  selector:
    app: postgres-exporter
  ports:
  - name: metrics
    port: 9187
    targetPort: metrics
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: postgres-exporter
  namespace: database
spec:
  selector:
    matchLabels:
      monitoring: postgres-exporter
  namespaceSelector:
    matchNames:
    - database
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
```

针对备份时效性/失败、文件系统剩余空间、PVC 扩容错误以及实测 I/O 延迟/队列限制设置告警。在声称已达到生产就绪状态之前，此蓝图还需要针对工作负载进行高可用性、恢复、凭证轮换和负载测试。

</details>

### 15. 如何调查新克隆卷运行缓慢以及 S3 数据集显示旧内容的问题？

<details>
<summary>显示答案</summary>

**答案：分别排查初始化、缓存和应用一致性**

对于 EBS 克隆，请验证实际驱动程序版本、源可用区/容量、复制状态、初始化进度以及预置性能/实例性能。新的原生副本即使已可用，也可能仍在后台初始化。不要向其写入零数据、把它当作空卷，也不要假设仅针对快照的初始化加速器可以用于它。

对于 Mountpoint，请检查已安装的 CSI/二进制文件版本、PV 选项、Pod 身份、存储桶/前缀和缓存 TTL，包括负缓存条目。S3 的强一致性不会绕过已配置的客户端缓存。请确认应用操作是否受该存储桶类型支持；通用型存储桶和目录存储桶对追加/重命名的处理假设可能不同。

使用本章中隔离的克隆标记和版本化 S3 数据集来验证假设。保留历史基准值作为未经验证的背景信息；如果之后获准测试，请记录实际环境和新测量结果。读取测试或创建快照都不能证明数据库与应用一致。

</details>

## 参考资料

- [与章节和源文件一致的示例](../../eks/04-eks-storage-part2.md)
- [StatefulSet PVC 保留策略](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [EBS 卷类型](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volume-types.html)
- [EBS SLA](https://aws.amazon.com/ebs/sla/)
- [EBS 原生复制](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-copying-volume.html)
- [EFS 挂载设置](https://docs.aws.amazon.com/efs/latest/ug/mounting-fs-nfs-mount-settings.html)
- [Mountpoint CSI 配置](https://github.com/awslabs/mountpoint-s3-csi-driver/blob/v2.8.0/docs/CONFIGURATION.md)
- [Velero CSI 生命周期](https://velero.io/docs/v1.18/csi/)
- [Prometheus Operator API](https://prometheus-operator.dev/docs/api-reference/api/)
- [PostgreSQL 版本策略](https://www.postgresql.org/support/versioning/)

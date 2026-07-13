# Storage 测验

本测验测试你对 Kubernetes 存储概念、卷类型、PersistentVolume、StorageClass 等内容的理解。

## 选择题

1. Kubernetes 中哪个存储资源即使在 Pod 重启后也能保留数据？
   - A) ConfigMap
   - B) Secret
   - C) PersistentVolume
   - D) emptyDir
   
<details>

<summary>显示答案</summary>

**答案: C) PersistentVolume**

**解析:**
PersistentVolume (PV) 是由集群管理员预置或使用 StorageClass 动态预置的集群存储。即使 Pod 被重启或删除，PV 也会保留数据。ConfigMap 和 Secret 分别用于存储配置数据和敏感信息，而 emptyDir 是只在 Pod 运行期间存在的临时目录。
</details>

2. Kubernetes 中用于请求 PersistentVolume 的资源是什么？
   - A) VolumeRequest
   - B) PersistentVolumeClaim
   - C) StorageRequest
   - D) VolumeBinding
   
<details>

<summary>显示答案</summary>

**答案: B) PersistentVolumeClaim**

**解析:**
PersistentVolumeClaim (PVC) 是用户请求 PersistentVolume 的方式。PVC 表示具有特定大小和访问模式的存储请求。Kubernetes 会找到满足 PVC 要求的 PV，并将二者绑定在一起。
</details>

3. Kubernetes 中用于动态卷预置的资源是哪一个？
   - A) VolumeProvisioner
   - B) StorageClass
   - C) DynamicVolume
   - D) AutoProvisioner
   
<details>

<summary>显示答案</summary>

**答案: B) StorageClass**

**解析:**
StorageClass 为管理员提供了一种描述其所提供存储“类别”的方式。不同类别可以映射到服务级别、备份策略，或由集群管理员确定的任意策略。使用 StorageClass 时，可以在创建 PVC 时动态预置 PV。
</details>

4. Kubernetes 中哪种策略会在 Pod 被删除时自动删除 PersistentVolumeClaim？
   - A) Delete
   - B) Retain
   - C) Recycle
   - D) 不提供此功能
   
<details>

<summary>显示答案</summary>

**答案: D) 不提供此功能**

**解析:**
Kubernetes 不提供在 Pod 被删除时自动删除 PVC 的内置功能。PVC 独立于 Pod 存在，即使 Pod 被删除也会保留。这是一项用于防止数据丢失的设计选择。对于 StatefulSet，你可以使用 `persistentVolumeClaimRetentionPolicy` 配置 PVC 删除策略。
</details>

5. 以下哪一项不是 PersistentVolume 访问模式？
   - A) ReadWriteOnce
   - B) ReadOnlyMany
   - C) ReadWriteMany
   - D) WriteOnlyMany
   
<details>

<summary>显示答案</summary>

**答案: D) WriteOnlyMany**

**解析:**
Kubernetes 中 PersistentVolume 的访问模式包括 ReadWriteOnce (RWO)、ReadOnlyMany (ROX) 和 ReadWriteMany (RWX)。WriteOnlyMany 并不存在于访问模式中。ReadWriteOnce 允许单个节点以读写方式挂载，ReadOnlyMany 允许多个节点以只读方式挂载，而 ReadWriteMany 允许多个节点以读写方式挂载。
</details>

6. 哪种 PersistentVolume Reclaim Policy 会在不删除卷的情况下释放资源？
   - A) Delete
   - B) Retain
   - C) Recycle
   - D) Release
   
<details>

<summary>显示答案</summary>

**答案: B) Retain**

**解析:**
Retain 策略会在 PVC 被删除后保留 PV 及其数据。该卷会被视为“Released”，但不能用于其他 claim。管理员必须手动清理数据，并使该卷可供重复使用。Delete 策略会在 PVC 被删除时删除 PV 和外部基础设施（例如 AWS EBS、GCE PD）。Recycle 策略已弃用，应改用动态预置。
</details>

7. Kubernetes 中哪种卷类型提供临时存储？
   - A) hostPath
   - B) emptyDir
   - C) nfs
   - D) awsElasticBlockStore
   
<details>

<summary>显示答案</summary>

**答案: B) emptyDir**

**解析:**
emptyDir 卷会在 Pod 被分配到节点时首次创建，并且只要该 Pod 在该节点上运行，它就会一直存在。顾名思义，该卷最初是空的。Pod 中的所有容器都可以读取和写入 emptyDir 卷中的相同文件，不过该卷可以在每个容器中挂载到相同或不同的路径。当 Pod 因任何原因从节点移除时，emptyDir 中的数据会被永久删除。
</details>

8. AWS EKS 默认使用哪个存储 provisioner？
   - A) kubernetes.io/aws-ebs
   - B) kubernetes.io/gce-pd
   - C) kubernetes.io/azure-disk
   - D) kubernetes.io/nfs
   
<details>

<summary>显示答案</summary>

**答案: A) kubernetes.io/aws-ebs**

**解析:**
AWS EKS 默认使用 AWS EBS (Elastic Block Store) 来提供持久存储。provisioner 名称是 'kubernetes.io/aws-ebs'。当创建 PVC 时，此 provisioner 会自动创建和管理 EBS 卷。AWS EKS 支持多种 EBS 卷类型，包括 gp2、gp3、io1、sc1 和 st1。
</details>

9. StatefulSet 中用于卷 claim 模板的正确字段名是什么？
   - A) volumeClaimTemplate
   - B) persistentVolumeClaimTemplate
   - C) volumeClaimTemplates
   - D) persistentVolumeClaimTemplates
   
<details>

<summary>显示答案</summary>

**答案: C) volumeClaimTemplates**

**解析:**
StatefulSet 使用 `volumeClaimTemplates` 字段为每个 Pod 自动创建 PVC。该模板用于为 StatefulSet 的每个副本创建 PVC。创建的 PVC 名称遵循 `<volume-claim-template-name>-<pod-name>` 格式。
</details>

10. CSI (Container Storage Interface) 在 Kubernetes 中的主要目的是什么？
    - A) 标准化容器之间的通信
    - B) 允许在 Kubernetes 代码之外开发存储驱动程序
    - C) 标准化对容器镜像注册表的访问
    - D) 自动执行云提供商之间的存储迁移
    
<details>

<summary>显示答案</summary>

**答案: B) 允许在 Kubernetes 代码之外开发存储驱动程序**

**解析:**
CSI (Container Storage Interface) 定义了容器编排系统（例如 Kubernetes）与存储提供商之间的标准接口。CSI 的主要目的是允许在 Kubernetes 代码库之外开发、部署和管理存储驱动程序。这使存储提供商能够独立于 Kubernetes 发布周期来开发和维护自己的插件。
</details>

## 高级问题

1. 说明如何使用 CSI (Container Storage Interface) driver 在 Kubernetes 中集成新的存储类型及其优势。

<details>

<summary>显示答案</summary>

**答案:**

**CSI Driver 集成方法:**

1. **部署 CSI Driver**: CSI driver 通常由以下组件组成：
  - **Node Plugin DaemonSet**: 在每个节点上运行，并执行卷挂载/卸载操作
  - **Controller Plugin Deployment/StatefulSet**: 执行卷创建/删除/snapshot 操作
  - **RBAC Resources**: 设置所需权限

2. **创建 StorageClass**: 定义一个使用 CSI driver 的 StorageClass：
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: csi-storage
provisioner: example.csi.k8s.io  # CSI driver name
parameters:
  # Driver-specific parameters
  type: ssd
  fsType: ext4
```

3. **设置 CSI Volume Snapshot 支持**（可选）：
```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: csi-snapshot-class
driver: example.csi.k8s.io
deletionPolicy: Delete
```

4. **测试 CSI Driver**: 通过创建 PVC 并将其挂载到 Pod 来验证功能

**使用 CSI 的优势:**

1. **独立开发周期**: 存储提供商可以独立于 Kubernetes 发布周期来开发和部署 driver。

2. **标准化接口**: CSI 在容器编排系统和存储提供商之间提供标准接口。

3. **高级存储功能**: 以标准化方式支持 volume snapshot、克隆和调整大小等高级功能。

4. **增强安全性**: CSI driver 以有限权限运行，并且只需授予必要权限。

5. **多样化存储选项**: 轻松集成云提供商、开源和商业存储解决方案。

6. **插件架构**: 可以根据需要添加或移除 CSI driver。

**真实世界实现示例 (AWS EBS CSI Driver):**

```bash
# Install AWS EBS CSI Driver (using Helm)
helm repo add aws-ebs-csi-driver https://kubernetes-sigs.github.io/aws-ebs-csi-driver
helm install aws-ebs-csi-driver aws-ebs-csi-driver/aws-ebs-csi-driver \
  --namespace kube-system \
  --set enableVolumeScheduling=true \
  --set enableVolumeResizing=true \
  --set enableVolumeSnapshot=true

# Create StorageClass
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-sc
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  encrypted: "true"
EOF
```

CSI 是 Kubernetes 存储生态系统的核心组成部分，可支持集成各种存储解决方案并利用高级存储功能。
</details>

2. 使用 StatefulSet 和 PersistentVolume 设计一个高可用数据库集群，并说明数据持久化和备份策略。

<details>

<summary>显示答案</summary>

**答案:**

**高可用数据库集群设计:**

1. **架构概览**:
  - 数据库集群配置为包含 3 个或更多副本的 StatefulSet
  - 每个 Pod 分配一个唯一的 PersistentVolume
  - 通过 headless service 提供稳定的网络标识符
  - 通过 leader election 机制实现主从配置

2. **StorageClass 设置**:
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-storage
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
  iopsPerGB: "3000"
  encrypted: "true"
reclaimPolicy: Retain
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
```

3. **创建 Headless Service**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: db-cluster
spec:
  clusterIP: None
  selector:
    app: database
    ports:
      - port: 3306
    name: db
```

4. **使用 ConfigMap 管理配置**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: db-config
data:
  my.cnf: |
    [mysqld]
    server-id = ${HOSTNAME##*-}
    log_bin = /var/lib/mysql/mysql-bin.log
    binlog_format = ROW
    sync_binlog = 1
    innodb_flush_log_at_trx_commit = 1
```

5. **StatefulSet 定义**:
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: db-cluster
spec:
  serviceName: db-cluster
  replicas: 3
  selector:
    matchLabels:
      app: database
  template:
    metadata:
      labels:
        app: database
    spec:
      initContainers:
        - name: init-config
          image: busybox
          command: ['sh', '-c', 'cp /config-map/my.cnf /etc/mysql/conf.d/']
          volumeMounts:
            - name: config-map
              mountPath: /config-map
            - name: config-dir
              mountPath: /etc/mysql/conf.d/
      containers:
        - name: mysql
          image: mysql:8.0
          env:
            - name: MYSQL_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: password
          ports:
            - containerPort: 3306
              name: db
          volumeMounts:
            - name: data
              mountPath: /var/lib/mysql
            - name: config-dir
              mountPath: /etc/mysql/conf.d/
          readinessProbe:
            exec:
              command: ["mysql", "-u", "root", "-p${MYSQL_ROOT_PASSWORD}", "-e", "SELECT 1"]
            initialDelaySeconds: 30
            periodSeconds: 10
      volumes:
        - name: config-map
          configMap:
            name: db-config
        - name: config-dir
          emptyDir: {}
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: [ "ReadWriteOnce" ]
        storageClassName: "fast-storage"
        resources:
          requests:
            storage: 50Gi
```

**数据持久化和备份策略:**

1. **确保数据持久化**:
  - 使用 `reclaimPolicy: Retain` 保护 PV，避免意外删除
  - 在数据库引擎中启用持久性设置（例如 MySQL 的 `sync_binlog=1`、`innodb_flush_log_at_trx_commit=1`）
  - 通过复制确保数据冗余

2. **备份策略**:
  - **定期创建 VolumeSnapshot**:
```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: db-snapshot-{{date}}
spec:
  volumeSnapshotClassName: csi-snapshot-class
  source:
    persistentVolumeClaimName: data-db-cluster-0
```

  - **数据库逻辑备份**:
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: db-backup
spec:
  schedule: "0 2 * * *"  # Runs daily at 02:00
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: mysql:8.0
              command:
                - /bin/sh
                - -c
                - |
                  mysqldump -h db-cluster-0.db-cluster -u root -p"${MYSQL_ROOT_PASSWORD}" --all-databases > /backup/full-backup-$(date +%Y%m%d).sql
                  aws s3 cp /backup/full-backup-$(date +%Y%m%d).sql s3://my-backup-bucket/
              env:
                - name: MYSQL_ROOT_PASSWORD
                  valueFrom:
                    secretKeyRef:
                      name: mysql-secret
                      key: password
              volumeMounts:
                - name: backup-volume
                  mountPath: /backup
          volumes:
            - name: backup-volume
              emptyDir: {}
          restartPolicy: OnFailure
```

  - **备份验证和恢复测试**: 定期从备份执行恢复测试，以验证备份有效性

3. **灾难恢复策略**:
  - 将 Pod 分布到多个可用区
  - 跨区域复制备份
  - 实现自动化恢复流程

4. **监控和告警**:
  - 为备份作业成功/失败设置告警
  - 监控存储使用量
  - 监控复制延迟

此设计将 StatefulSet 的稳定网络标识符与 PersistentVolume 的数据持久化结合起来，以提供高可用数据库集群。多层备份策略可在各种故障场景中防止数据丢失。
</details>

## 总结

通过本测验，你测试了自己对 Kubernetes 存储概念的理解。我们涵盖了 PersistentVolume、PersistentVolumeClaim、StorageClass、卷类型、访问模式和 reclaim policy 等概念。我们还探讨了 AWS EKS 中的存储配置、CSI driver 和 volume snapshot 等高级主题。理解并运用这些概念，可以让你在 Kubernetes 中构建可靠且可扩展的存储解决方案。

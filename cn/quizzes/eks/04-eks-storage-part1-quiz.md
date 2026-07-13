# EKS 存储测验 - 第 1 部分

本测验测试你对 Amazon EKS 中存储概念的理解，包括持久卷、存储类和动态预置。

## 多项选择题

### 1. Amazon EKS 默认原生支持哪种存储驱动？

A. Amazon EFS CSI Driver B. Amazon EBS CSI Driver C. Amazon FSx for Lustre CSI Driver D. Amazon S3 CSI Driver

<details>

<summary>显示答案</summary>

**答案：B. Amazon EBS CSI Driver**

**解释：** Amazon EKS 默认原生支持的存储驱动是 Amazon EBS CSI (Container Storage Interface) Driver。该驱动允许将 Amazon Elastic Block Store (EBS) 卷用作 Amazon EKS 集群中的持久存储。

**主要特性：**

1.  **作为 EKS Add-on 提供**：Amazon EBS CSI driver 作为 EKS add-on 提供，便于安装和管理。

    ```bash
    aws eks create-addon \
      --cluster-name my-cluster \
      --addon-name aws-ebs-csi-driver \
      --service-account-role-arn arn:aws:iam::111122223333:role/AmazonEKS_EBS_CSI_DriverRole
    ```
2.  **支持动态预置**：通过 StorageClass 支持 EBS 卷的动态预置。

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer
    parameters:
      type: gp3
      encrypted: "true"
    ```
3.  **支持卷快照**：支持卷快照和恢复功能。

    ```yaml
    apiVersion: snapshot.storage.k8s.io/v1
    kind: VolumeSnapshot
    metadata:
      name: ebs-volume-snapshot
    spec:
      volumeSnapshotClassName: ebs-snapshot-class
      source:
        persistentVolumeClaimName: ebs-claim
    ```
4. **多种 EBS 卷类型**：支持多种 EBS 卷类型，包括 gp2、gp3、io1、io2、sc1、st1。

**所需 IAM 权限：**

EBS CSI driver 需要以下 IAM 权限才能运行：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateSnapshot",
        "ec2:AttachVolume",
        "ec2:DetachVolume",
        "ec2:ModifyVolume",
        "ec2:DescribeAvailabilityZones",
        "ec2:DescribeInstances",
        "ec2:DescribeSnapshots",
        "ec2:DescribeTags",
        "ec2:DescribeVolumes",
        "ec2:DescribeVolumesModifications"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateTags"
      ],
      "Resource": [
        "arn:aws:ec2:*:*:volume/*",
        "arn:aws:ec2:*:*:snapshot/*"
      ],
      "Condition": {
        "StringEquals": {
          "ec2:CreateAction": [
            "CreateVolume",
            "CreateSnapshot"
          ]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteTags"
      ],
      "Resource": [
        "arn:aws:ec2:*:*:volume/*",
        "arn:aws:ec2:*:*:snapshot/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateVolume"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "aws:RequestTag/ebs.csi.aws.com/cluster": "true"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateVolume"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "aws:RequestTag/CSIVolumeName": "*"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteVolume"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "ec2:ResourceTag/ebs.csi.aws.com/cluster": "true"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteVolume"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "ec2:ResourceTag/CSIVolumeName": "*"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteVolume"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "ec2:ResourceTag/kubernetes.io/created-for/pvc/name": "*"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteSnapshot"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "ec2:ResourceTag/CSIVolumeSnapshotName": "*"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteSnapshot"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "ec2:ResourceTag/ebs.csi.aws.com/cluster": "true"
        }
      }
    }
  ]
}
```

**限制：**

1. **可用区限制**：EBS 卷受限于单个可用区，因此 pods 必须在与该卷相同的可用区中运行。
2. **单节点挂载**：EBS 卷一次只能挂载到一个节点（ReadWriteOnce 访问模式）。
3. **Fargate 限制**：Amazon EKS Fargate 目前不支持 EBS CSI driver。

其他选项的问题：

* **A. Amazon EFS CSI Driver**：EFS CSI driver 在 EKS 中受支持，但默认不会安装。必须单独安装。
* **C. Amazon FSx for Lustre CSI Driver**：FSx for Lustre CSI driver 在 EKS 中受支持，但默认不会安装。必须单独安装。
* **D. Amazon S3 CSI Driver**：目前没有官方的 Amazon S3 CSI driver。S3 通常通过 S3 API 访问，而不是通过 CSI 直接挂载。

</details>

### 2. 当 Amazon EKS 中多个 pods 需要同时读/写访问时，最合适的存储解决方案是什么？

A. Amazon EBS B. Amazon EFS C. Amazon S3 D. Amazon FSx for Lustre

<details>

<summary>显示答案</summary>

**答案：B. Amazon EFS**

**解释：** 当 Amazon EKS 中多个 pods 需要同时读/写访问时，最合适的存储解决方案是 Amazon EFS (Elastic File System)。EFS 是一项托管的 NFS (Network File System) 服务，支持 ReadWriteMany (RWX) 访问模式，允许多个 pods 同时读取和写入同一个卷。

**主要特性：**

1. **多可用区访问**：EFS 可以跨多个可用区访问，允许运行在不同节点和可用区中的 pods 访问相同的数据。
2.  **支持 ReadWriteMany**：EFS 支持 ReadWriteMany (RWX) 访问模式，使多个 pods 能够同时读取和写入同一个卷。

    ```yaml
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: efs-claim
    spec:
      accessModes:
        - ReadWriteMany
      storageClassName: efs-sc
      resources:
        requests:
          storage: 5Gi
    ```
3. **可扩展性**：EFS 会自动扩展，消除了容量规划的需要。
4. **持久性和可用性**：提供 99.999999999%（11 个 9）的持久性和 99.99% 的可用性。

**EFS CSI Driver 安装：**

```bash
# Install using Helm
helm repo add aws-efs-csi-driver https://kubernetes-sigs.github.io/aws-efs-csi-driver/
helm repo update
helm upgrade -i aws-efs-csi-driver aws-efs-csi-driver/aws-efs-csi-driver \
  --namespace kube-system \
  --set controller.serviceAccount.create=true \
  --set controller.serviceAccount.name=efs-csi-controller-sa
```

**EFS 文件系统创建：**

```bash
# Create EFS file system
aws efs create-file-system \
  --creation-token eks-efs \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --tags Key=Name,Value=EKS-EFS

# Create mount target
aws efs create-mount-target \
  --file-system-id fs-0123456789abcdef0 \
  --subnet-id subnet-0123456789abcdef0 \
  --security-groups sg-0123456789abcdef0
```

**StorageClass 和 PVC 配置：**

```yaml
# Create StorageClass
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: "700"

# Create PVC
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-claim
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: efs-sc
  resources:
    requests:
      storage: 5Gi
```

**使用场景：**

1. **共享文件系统**：当多个 pods 需要访问相同文件时
2. **Web Server 内容**：当多个 web server pods 需要提供相同的静态内容时
3. **日志聚合**：当多个 pods 写入同一个日志目录时
4. **CI/CD Pipelines**：当构建产物需要共享时

**性能注意事项：**

1. **性能模式**：
   * General Purpose：适用于大多数工作负载
   * Max I/O：适用于需要高吞吐量的工作负载
2. **吞吐量模式**：
   * Bursting：默认模式，基于文件系统大小提供突增积分
   * Provisioned：在需要一致吞吐量时预置特定吞吐量
3. **延迟**：EFS 的延迟可能高于块存储，因此可能不适合对延迟敏感的应用程序。

**安全注意事项：**

1.  **加密**：EFS 支持传输中和静态加密。

    ```bash
    aws efs create-file-system \
      --creation-token eks-efs \
      --encrypted \
      --kms-key-id 1234abcd-12ab-34cd-56ef-1234567890ab
    ```
2. **访问控制**：可以通过 IAM policies、network ACLs 和 security groups 控制访问。
3. **Access Points**：EFS access points 可用于限制对特定目录的访问。

其他选项的问题：

* **A. Amazon EBS**：EBS 仅支持 ReadWriteOnce (RWO) 访问模式，因此一次只能挂载到一个节点。
* **C. Amazon S3**：S3 是对象存储，不是文件系统，因此不能通过标准文件系统接口直接挂载。
* **D. Amazon FSx for Lustre**：FSx for Lustre 适用于高性能工作负载，但与 EFS 相比，设置更复杂且成本更高。

</details>

### 4. 在 Amazon EKS 中使用 EBS 卷时有什么限制？

A. EBS 卷可以让多个 pods 同时进行读/写访问 B. EBS 卷可以跨多个可用区访问 C. EBS 卷一次只能让一个 pod 进行读/写访问 D. EBS 卷可以与 Fargate pods 一起使用

<details>

<summary>显示答案</summary>

**答案：C. EBS 卷一次只能让一个 pod 进行读/写访问**

**解释：** Amazon EBS (Elastic Block Store) 卷一次只能让一个 pod 进行读/写访问。这是 EBS 的基本限制，因为 EBS 卷仅支持 ReadWriteOnce (RWO) 访问模式。

**主要限制：**

1. **单节点挂载**：EBS 卷一次只能挂载到一个 EC2 instance。因此，跨多个节点的 pods 无法访问同一个 EBS 卷。
2.  **可用区限制**：EBS 卷受限于其创建所在的可用区。运行在不同可用区节点上的 pods 无法访问该卷。

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer  # Delay volume creation until pod is scheduled
    ```
3. **Fargate 不兼容**：Amazon EKS Fargate 目前不支持 EBS 卷。Fargate pods 无法挂载 EBS 卷。
4.  **访问模式限制**：EBS 仅支持以下访问模式：

    * ReadWriteOnce (RWO)：由单个节点进行读写挂载

    ```yaml
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: ebs-claim
    spec:
      accessModes:
        - ReadWriteOnce  # The only access mode supported by EBS
      storageClassName: ebs-sc
      resources:
        requests:
          storage: 10Gi
    ```

**解决这些限制的替代方案：**

1.  **使用 StatefulSet**：通过为每个 pod 提供专用 EBS 卷来运行有状态应用程序

    ```yaml
    apiVersion: apps/v1
    kind: StatefulSet
    metadata:
      name: web
    spec:
      serviceName: "nginx"
      replicas: 3
      selector:
        matchLabels:
          app: nginx
      template:
        metadata:
          labels:
            app: nginx
        spec:
          containers:
          - name: nginx
            image: nginx
            volumeMounts:
            - name: www
              mountPath: /usr/share/nginx/html
      volumeClaimTemplates:
      - metadata:
          name: www
        spec:
          accessModes: [ "ReadWriteOnce" ]
          storageClassName: ebs-sc
          resources:
            requests:
              storage: 10Gi
    ```
2. **使用 Amazon EFS**：当多个 pods 需要访问同一个卷时，使用支持 ReadWriteMany (RWX) 访问模式的 EFS
3. **卷复制**：将数据复制到多个 EBS 卷，以允许多个 pods 访问
4. **拓扑感知调度**：使用 `volumeBindingMode: WaitForFirstConsumer` 在 pod 被调度的可用区中创建卷

**可用区注意事项：**

1.  **使用 Node Selector**：将 pods 调度到特定可用区中的节点

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: az-pod
    spec:
      nodeSelector:
        topology.kubernetes.io/zone: us-west-2a
      containers:
      - name: app
        image: nginx
    ```
2.  **卷快照和恢复**：当数据需要移动到不同可用区时，使用卷快照

    ```yaml
    apiVersion: snapshot.storage.k8s.io/v1
    kind: VolumeSnapshot
    metadata:
      name: ebs-snapshot
    spec:
      volumeSnapshotClassName: ebs-snapshot-class
      source:
        persistentVolumeClaimName: ebs-claim
    ```

**最佳实践：**

1. **适当的存储选择**：根据工作负载要求选择适当的存储类型
   * 单 pod 访问：EBS
   * 多 pod 访问：EFS
   * 高性能工作负载：FSx for Lustre
2. **可用区感知部署**：确保 pods 和卷位于同一个可用区
3. **卷备份**：通过定期快照保护数据

其他选项的问题：

* **A. EBS 卷可以让多个 pods 同时进行读/写访问**：这是不正确的。EBS 卷仅支持 ReadWriteOnce (RWO) 访问模式。
* **B. EBS 卷可以跨多个可用区访问**：这是不正确的。EBS 卷受限于其创建所在的可用区。
* **D. EBS 卷可以与 Fargate pods 一起使用**：这是不正确的。Amazon EKS Fargate 目前不支持 EBS 卷。

</details>

## 简答题

### 6. 在 Amazon EKS 中为 EBS 卷进行动态预置时，PersistentVolumeClaim 中必须指定哪种访问模式？

<details>

<summary>显示答案</summary>

**答案：** ReadWriteOnce (RWO)

**详细解释：**

在 Amazon EKS 中为 EBS 卷进行动态预置时，PersistentVolumeClaim (PVC) 中必须指定的访问模式是 ReadWriteOnce (RWO)。这是由 EBS 卷的基本特性决定的：它一次只能让一个节点进行读/写访问。

**访问模式说明：**

1. **ReadWriteOnce (RWO)**：该卷可以由单个节点以读写模式挂载。
2. **ReadOnlyMany (ROX)**：该卷可以由多个节点以只读模式挂载。
3. **ReadWriteMany (RWX)**：该卷可以由多个节点以读写模式挂载。

**为什么 EBS 仅支持 RWO：**

Amazon EBS 是一种块存储服务，设计为一次仅附加到一个 EC2 instance。这不是硬件限制，而是 EBS 服务的设计特性。因此，EBS 卷仅支持 ReadWriteOnce 访问模式。

**PVC 示例：**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-claim
spec:
  accessModes:
    - ReadWriteOnce  # The only access mode supported by EBS
  storageClassName: ebs-sc
  resources:
    requests:
      storage: 10Gi
```

**需要其他访问模式时的替代方案：**

1. **需要 ReadOnlyMany (ROX) 时：**
   * 创建 EBS snapshot，并创建多个只读 EBS 卷
   * 为每个节点提供单独的只读卷
2.  **需要 ReadWriteMany (RWX) 时：**

    * 使用 Amazon EFS（基于 NFS 的文件系统）

    ```yaml
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: efs-claim
    spec:
      accessModes:
        - ReadWriteMany
      storageClassName: efs-sc
      resources:
        requests:
          storage: 5Gi
    ```

**使用 EBS 卷时的注意事项：**

1. **Pod 调度**：使用 EBS 卷的 Pods 只能运行在该卷所附加到的节点上。
2. **可用区限制**：EBS 卷受限于其创建所在的可用区。因此，pods 只能运行在该可用区中的节点上。
3.  **卷绑定模式**：建议使用 `WaitForFirstConsumer` 在 pod 调度后创建卷。

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer
    ```
4. **与 StatefulSet 一起使用**：StatefulSet 为每个 pod 提供唯一的 PVC，因此适合与 EBS 卷一起使用。

**访问模式选择指南：**

| 存储类型       | ReadWriteOnce | ReadOnlyMany | ReadWriteMany |
| -------------- | ------------- | ------------ | ------------- |
| Amazon EBS     | ✓             | ✗            | ✗             |
| Amazon EFS     | ✓             | ✓            | ✓             |
| FSx for Lustre | ✓             | ✓            | ✓             |

使用 EBS 卷时，请始终指定 ReadWriteOnce 访问模式。如果需要多个节点同时访问，请考虑 EFS 或 FSx for Lustre 等替代方案。

</details>

### 7. 在 Amazon EKS 中，使用 EBS 卷的 pod 移动到不同节点时，数据会发生什么？

<details>

<summary>显示答案</summary>

**答案：** EBS 卷会从之前的节点分离，并附加到新节点。数据会被保留，但在卷重新附加过程中可能会有延迟。

**详细解释：**

当 Amazon EKS 中使用 EBS 卷的 pod 移动到不同节点时（例如由于节点故障、扩缩容、更新等），EBS 卷会从之前的节点分离，并附加到新节点。在此过程中，数据会被保留，但卷重新附加过程中可能会有延迟。

**卷重新附加过程：**

1. **Pod 终止**：pod 在原始节点上终止。
2. **卷分离**：EBS 卷从原始节点分离。
3. **卷附加**：EBS 卷附加到新节点。
4. **Pod 启动**：pod 在新节点上启动并挂载该卷。

**该过程的影响：**

1. **延迟时间**：卷分离和附加操作通常需要 10-30 秒，但在某些情况下可能需要更长时间。
2. **可用区限制**：EBS 卷受限于其创建所在的可用区，因此 pods 只能移动到同一可用区内的其他节点。
3. **数据持久性**：数据会被保留，在卷重新附加过程中不会丢失。

**处理此行为的策略：**

1.  **使用 PodDisruptionBudget**：通过限制可同时中断的 pods 数量来确保可用性

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
2.  **配置适当的 readinessProbe 和 livenessProbe**：在卷正确挂载且应用程序就绪之前延迟接收流量

    ```yaml
    readinessProbe:
      exec:
        command:
        - cat
        - /data/ready
      initialDelaySeconds: 5
      periodSeconds: 5
    ```
3. **使用 StatefulSet**：StatefulSet 提供顺序部署和扩缩容，以尽量减少卷重新附加的影响。
4.  **优化卷绑定模式**：使用 `WaitForFirstConsumer` 在 pod 被调度的可用区中创建卷

    ```yaml
    volumeBindingMode: WaitForFirstConsumer
    ```

**可用区注意事项：**

1. **多可用区部署**：跨多个可用区部署应用程序，以提高对单个 AZ 故障的韧性
2.  **拓扑分布**：使用 `topologySpreadConstraints` 将 pods 分布到多个可用区

    ```yaml
    topologySpreadConstraints:
    - maxSkew: 1
      topologyKey: topology.kubernetes.io/zone
      whenUnsatisfiable: DoNotSchedule
      labelSelector:
        matchLabels:
          app: my-app
    ```
3. **可用区感知 PDB**：为每个可用区配置单独的 PodDisruptionBudget

**最佳实践：**

1. **优化应用程序以快速重启**：设计应用程序，使其能够快速启动和初始化
2.  **设置适当的终止宽限期**：为应用程序优雅终止提供足够时间

    ```yaml
    terminationGracePeriodSeconds: 60
    ```
3. **关键数据备份策略**：通过定期快照或备份保护数据
4. **考虑无状态设计**：在可能的情况下，将应用程序设计为无状态，以尽量减少节点迁移的影响

当使用 EBS 卷的 pod 在节点之间移动时，数据会被保留，但卷重新附加过程中可能会出现延迟，因此在应用程序设计和配置中考虑这一点非常重要。

</details>

### 9. 在 Amazon EKS 中，用于创建 EBS 卷快照的 Kubernetes API 资源是什么？

<details>

<summary>显示答案</summary>

**答案：** VolumeSnapshot

**详细解释：**

在 Amazon EKS 中，用于创建 EBS 卷快照的 Kubernetes API 资源是 `VolumeSnapshot`。该资源是 Kubernetes Volume Snapshot API 的一部分，并与 CSI (Container Storage Interface) drivers 配合使用，以创建持久卷的时间点副本。

**使用 VolumeSnapshot 的前提条件：**

1. **安装 EBS CSI Driver**：集群中必须安装 AWS EBS CSI driver。
2.  **安装 Snapshot Controller**：集群中必须安装 Kubernetes snapshot controller。

    ```bash
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/client/config/crd/snapshot.storage.k8s.io_volumesnapshotclasses.yaml
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/client/config/crd/snapshot.storage.k8s.io_volumesnapshotcontents.yaml
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/client/config/crd/snapshot.storage.k8s.io_volumesnapshots.yaml
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/deploy/kubernetes/snapshot-controller/rbac-snapshot-controller.yaml
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/deploy/kubernetes/snapshot-controller/setup-snapshot-controller.yaml
    ```
3. **创建 VolumeSnapshotClass**：创建定义快照创建方式的 VolumeSnapshotClass。

**VolumeSnapshotClass 示例：**

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: ebs-snapshot-class
driver: ebs.csi.aws.com
deletionPolicy: Delete
```

**VolumeSnapshot 创建示例：**

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: ebs-volume-snapshot
spec:
  volumeSnapshotClassName: ebs-snapshot-class
  source:
    persistentVolumeClaimName: ebs-claim
```

**检查 Snapshot 状态：**

```bash
kubectl get volumesnapshot ebs-volume-snapshot
```

**从 Snapshot 创建新 PVC：**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-claim-from-snapshot
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: ebs-sc
  resources:
    requests:
      storage: 10Gi
  dataSource:
    name: ebs-volume-snapshot
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
```

**VolumeSnapshot 的主要优势：**

1. **数据保护**：创建关键数据的时间点备份
2. **灾难恢复**：在数据丢失或损坏时支持恢复
3. **环境复制**：为开发或测试环境复制生产数据
4. **数据迁移**：将数据从一个集群移动到另一个集群

**Snapshot 生命周期管理：**

1.  **自动创建 Snapshot**：使用 CronJob 自动定期创建 snapshot

    ```yaml
    apiVersion: batch/v1
    kind: CronJob
    metadata:
      name: volume-snapshot-job
    spec:
      schedule: "0 0 * * *"  # Daily at midnight
      jobTemplate:
        spec:
          template:
            spec:
              serviceAccountName: snapshot-creator
              containers:
              - name: snapshot-creator
                image: bitnami/kubectl:latest
                command:
                - /bin/sh
                - -c
                - |
                  cat <<EOF | kubectl apply -f -
                  apiVersion: snapshot.storage.k8s.io/v1
                  kind: VolumeSnapshot
                  metadata:
                    name: ebs-snapshot-$(date +%Y%m%d)
                  spec:
                    volumeSnapshotClassName: ebs-snapshot-class
                    source:
                      persistentVolumeClaimName: ebs-claim
                  EOF
              restartPolicy: OnFailure
    ```
2.  **Snapshot 保留策略**：自动删除旧 snapshots

    ```yaml
    apiVersion: batch/v1
    kind: CronJob
    metadata:
      name: snapshot-cleanup-job
    spec:
      schedule: "0 1 * * *"  # Daily at 1 AM
      jobTemplate:
        spec:
          template:
            spec:
              serviceAccountName: snapshot-manager
              containers:
              - name: snapshot-cleaner
                image: bitnami/kubectl:latest
                command:
                - /bin/sh
                - -c
                - |
                  # Delete snapshots older than 30 days
                  kubectl get volumesnapshot -o json | jq -r '.items[] | select(.metadata.creationTimestamp | fromnow | contains("days") and (split(" ")[0] | tonumber) > 30) | .metadata.name' | xargs -r kubectl delete volumesnapshot
              restartPolicy: OnFailure
    ```

**最佳实践：**

1. **定期 Snapshots**：为关键数据设置定期 snapshot 计划
2. **测试 Snapshots**：定期测试从 snapshots 恢复，以验证备份有效性
3. **标记**：为 snapshots 应用适当标签，便于管理和成本跟踪
4. **成本监控**：监控并优化成本，因为 EBS snapshots 会产生额外费用
5. **加密**：对敏感数据使用加密 snapshots

使用 VolumeSnapshot API 可以用 Kubernetes-native 的方式创建和管理 EBS 卷快照，从而有效实施数据保护和恢复策略。

</details>

## 动手实践题

### 10. 为 Amazon EKS 集群中具有多样化存储需求的应用程序设计一个存储解决方案。创建满足以下需求的 storage classes 和 persistent volume claims：

* 用于数据库的高性能块存储
* 需要在多个 pods 之间共享的配置文件
* 用于 AI/ML 工作负载的高性能并行文件系统

<details>

<summary>显示答案</summary>

**答案：**

以下是一个满足 Amazon EKS 集群中多样化存储需求的存储解决方案：

### 1. 用于数据库的高性能块存储 (Amazon EBS gp3)

#### StorageClass 定义：

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3-db
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  iops: "16000"  # Maximum IOPS
  throughput: "1000"  # Maximum throughput (MB/s)
  encrypted: "true"
allowVolumeExpansion: true
```

#### PersistentVolumeClaim 定义：

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: database-data
  namespace: database
spec:
  accessModes:
    - ReadWriteOnce  # EBS can only be mounted to a single node
  storageClassName: ebs-gp3-db
  resources:
    requests:
      storage: 100Gi
```

#### Database Pod 示例：

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: database
spec:
  serviceName: "postgres"
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:14
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: ebs-gp3-db
      resources:
        requests:
          storage: 100Gi
```

**解释：**

* **gp3 Volume Type**：提供最高 16,000 IOPS 和 1,000MB/s 吞吐量，适合数据库工作负载。
* **WaitForFirstConsumer**：将卷创建延迟到 pod 调度时，以防止可用区问题。
* **加密**：为 EBS 卷启用静态数据加密。
* **卷扩展**：允许将来随着数据库规模增长进行卷扩展。
* **StatefulSet**：为数据库提供稳定的网络 ID 和持久存储。

### 2. 跨多个 Pods 共享的配置文件 (Amazon EFS)

#### EFS CSI Driver 安装：

```bash
helm repo add aws-efs-csi-driver https://kubernetes-sigs.github.io/aws-efs-csi-driver/
helm repo update
helm upgrade -i aws-efs-csi-driver aws-efs-csi-driver/aws-efs-csi-driver \
  --namespace kube-system \
  --set controller.serviceAccount.create=true \
  --set controller.serviceAccount.name=efs-csi-controller-sa
```

#### StorageClass 定义：

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0  # Existing EFS file system ID
  directoryPerms: "700"
```

#### PersistentVolumeClaim 定义：

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: config-storage
  namespace: application
spec:
  accessModes:
    - ReadWriteMany  # Multiple pods can read/write simultaneously
  storageClassName: efs-sc
  resources:
    requests:
      storage: 5Gi  # This value is symbolic as EFS auto-scales
```

#### 使用配置文件的 Deployment 示例：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: application
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: web-app
        image: nginx:latest
        volumeMounts:
        - name: config-volume
          mountPath: /etc/config
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "1"
            memory: "1Gi"
      volumes:
      - name: config-volume
        persistentVolumeClaim:
          claimName: config-storage
```

**解释：**

* **ReadWriteMany Access Mode**：EFS 支持多个 pods 同时读取和写入同一个卷。
* **多可用区支持**：EFS 可以跨多个可用区访问，提供对节点故障的韧性。
* **自动扩展**：EFS 根据使用量自动扩展，消除容量规划需求。
* **Access Points**：EFS access points 可用于限制对特定目录的访问。

### 3. 用于 AI/ML 工作负载的高性能并行文件系统 (Amazon FSx for Lustre)

#### FSx CSI Driver 安装：

```bash
helm repo add aws-fsx-csi-driver https://kubernetes-sigs.github.io/aws-fsx-csi-driver/
helm repo update
helm upgrade -i aws-fsx-csi-driver aws-fsx-csi-driver/aws-fsx-csi-driver \
  --namespace kube-system \
  --set controller.serviceAccount.create=true \
  --set controller.serviceAccount.name=fsx-csi-controller-sa
```

#### StorageClass 定义：

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre
provisioner: fsx.csi.aws.com
parameters:
  subnetId: subnet-0123456789abcdef0  # Subnet for FSx file system
  securityGroupIds: sg-0123456789abcdef0  # Security group for FSx file system
  deploymentType: SCRATCH_2  # High-performance temporary storage
  perUnitStorageThroughput: "200"  # MB/s/TiB
  dataCompressionType: "LZ4"  # Enable data compression
  s3ImportPath: s3://ml-training-data-bucket/  # Optional: Import data from S3
mountOptions:
  - flock
```

#### PersistentVolumeClaim 定义：

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ml-training-data
  namespace: ml-workloads
spec:
  accessModes:
    - ReadWriteMany  # Multiple pods can read/write simultaneously
  storageClassName: fsx-lustre
  resources:
    requests:
      storage: 1200Gi  # FSx for Lustre starts at minimum 1.2TiB
```

#### ML Training Job 示例：

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: ml-training
  namespace: ml-workloads
spec:
  parallelism: 4  # Number of parallel jobs
  template:
    spec:
      containers:
      - name: training
        image: tensorflow/tensorflow:latest-gpu
        command:
          - "python"
          - "/training/train.py"
        volumeMounts:
        - name: training-data
          mountPath: "/training"
        resources:
          limits:
            nvidia.com/gpu: 4  # GPU resource request
          requests:
            cpu: "8"
            memory: "32Gi"
      volumes:
      - name: training-data
        persistentVolumeClaim:
          claimName: ml-training-data
      restartPolicy: Never
  backoffLimit: 2
```

**解释：**

* **高性能**：FSx for Lustre 提供数百 GB/s 的吞吐量和数百万 IOPS，适合 AI/ML 工作负载。
* **并行访问**：多个计算节点可以同时访问相同数据，非常适合分布式训练。
* **S3 集成**：训练数据可以存储在 S3 中，并导入 FSx for Lustre 进行处理。
* **数据压缩**：使用 LZ4 压缩以提高存储效率。
* **SCRATCH\_2 Deployment Type**：用于临时处理的高性能、经济高效选项。

### 其他注意事项和最佳实践

#### 1. 备份和灾难恢复：

```yaml
# EBS volume snapshot creation
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: ebs-snapshot-class
driver: ebs.csi.aws.com
deletionPolicy: Retain

---
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: database-snapshot
  namespace: database
spec:
  volumeSnapshotClassName: ebs-snapshot-class
  source:
    persistentVolumeClaimName: database-data
```

#### 2. 监控和告警：

* 设置 CloudWatch alarms 来监控存储使用量、延迟和吞吐量。
* 使用 Prometheus 和 Grafana 可视化存储指标。

#### 3. 成本优化：

* 删除未使用的卷之前，先删除或创建其 snapshots。
* 选择适当的存储类型和大小以优化成本。
* 对于 FSx for Lustre，如果不需要长期存储，请使用 SCRATCH deployment type。

#### 4. 安全：

* 为所有卷启用加密。
* 配置适当的 IAM permissions 和 security groups。
* 使用 PodSecurityPolicy 或 SecurityContext 限制卷访问。

此设计提供了一个全面的存储解决方案，满足多样化的工作负载需求：

* 用于数据库的高性能 EBS gp3 卷
* 支持多读/写访问、用于配置文件共享的 EFS
* 用于 AI/ML 工作负载的高性能并行文件系统 FSx for Lustre

每个存储解决方案都针对特定工作负载需求进行了优化，并在设计中考虑了可扩展性、性能和成本效率。

</details>

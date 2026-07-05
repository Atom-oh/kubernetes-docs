# EKS Storage Quiz - Part 1

This quiz tests your understanding of storage concepts in Amazon EKS, including persistent volumes, storage classes, and dynamic provisioning.

## Multiple Choice Questions

### 1. What storage driver is natively supported by Amazon EKS by default?

A. Amazon EFS CSI Driver B. Amazon EBS CSI Driver C. Amazon FSx for Lustre CSI Driver D. Amazon S3 CSI Driver

<details>

<summary>Show Answer</summary>

**Answer: B. Amazon EBS CSI Driver**

**Explanation:** The storage driver natively supported by Amazon EKS by default is the Amazon EBS CSI (Container Storage Interface) Driver. This driver allows Amazon Elastic Block Store (EBS) volumes to be used as persistent storage in Amazon EKS clusters.

**Key Features:**

1.  **Available as EKS Add-on**: The Amazon EBS CSI driver is provided as an EKS add-on for easy installation and management.

    ```bash
    aws eks create-addon \
      --cluster-name my-cluster \
      --addon-name aws-ebs-csi-driver \
      --service-account-role-arn arn:aws:iam::111122223333:role/AmazonEKS_EBS_CSI_DriverRole
    ```
2.  **Dynamic Provisioning Support**: Supports dynamic provisioning of EBS volumes through StorageClass.

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
3.  **Volume Snapshot Support**: Supports volume snapshot and restore functionality.

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
4. **Various EBS Volume Types**: Supports various EBS volume types including gp2, gp3, io1, io2, sc1, st1.

**Required IAM Permissions:**

The EBS CSI driver requires the following IAM permissions to operate:

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

**Limitations:**

1. **Availability Zone Restriction**: EBS volumes are restricted to a single availability zone, so pods must run in the same availability zone as the volume.
2. **Single Node Mount**: EBS volumes can only be mounted to one node at a time (ReadWriteOnce access mode).
3. **Fargate Limitation**: Amazon EKS Fargate does not currently support the EBS CSI driver.

Issues with other options:

* **A. Amazon EFS CSI Driver**: The EFS CSI driver is supported in EKS but is not installed by default. It must be installed separately.
* **C. Amazon FSx for Lustre CSI Driver**: The FSx for Lustre CSI driver is supported in EKS but is not installed by default. It must be installed separately.
* **D. Amazon S3 CSI Driver**: There is currently no official Amazon S3 CSI driver. S3 is typically accessed via the S3 API rather than directly mounted via CSI.

</details>

### 2. What is the most suitable storage solution when multiple pods in Amazon EKS need simultaneous read/write access?

A. Amazon EBS B. Amazon EFS C. Amazon S3 D. Amazon FSx for Lustre

<details>

<summary>Show Answer</summary>

**Answer: B. Amazon EFS**

**Explanation:** The most suitable storage solution when multiple pods in Amazon EKS need simultaneous read/write access is Amazon EFS (Elastic File System). EFS is a managed NFS (Network File System) service that supports ReadWriteMany (RWX) access mode, allowing multiple pods to simultaneously read and write to the same volume.

**Key Features:**

1. **Multi-Availability Zone Access**: EFS can be accessed across multiple availability zones, allowing pods running on different nodes and availability zones to access the same data.
2.  **ReadWriteMany Support**: EFS supports ReadWriteMany (RWX) access mode, enabling multiple pods to simultaneously read and write to the same volume.

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
3. **Scalability**: EFS automatically scales, eliminating the need for capacity planning.
4. **Durability and Availability**: Provides 99.999999999% (11 9's) durability and 99.99% availability.

**EFS CSI Driver Installation:**

```bash
# Install using Helm
helm repo add aws-efs-csi-driver https://kubernetes-sigs.github.io/aws-efs-csi-driver/
helm repo update
helm upgrade -i aws-efs-csi-driver aws-efs-csi-driver/aws-efs-csi-driver \
  --namespace kube-system \
  --set controller.serviceAccount.create=true \
  --set controller.serviceAccount.name=efs-csi-controller-sa
```

**EFS File System Creation:**

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

**StorageClass and PVC Configuration:**

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

**Use Cases:**

1. **Shared File System**: When multiple pods need to access the same files
2. **Web Server Content**: When multiple web server pods need to serve the same static content
3. **Log Aggregation**: When multiple pods write to the same log directory
4. **CI/CD Pipelines**: When build artifacts need to be shared

**Performance Considerations:**

1. **Performance Modes**:
   * General Purpose: Suitable for most workloads
   * Max I/O: Suitable for workloads requiring high throughput
2. **Throughput Modes**:
   * Bursting: Default mode, provides burst credits based on file system size
   * Provisioned: Provision specific throughput when consistent throughput is needed
3. **Latency**: EFS may have higher latency than block storage, so it may not be suitable for latency-sensitive applications.

**Security Considerations:**

1.  **Encryption**: EFS supports encryption in transit and at rest.

    ```bash
    aws efs create-file-system \
      --creation-token eks-efs \
      --encrypted \
      --kms-key-id 1234abcd-12ab-34cd-56ef-1234567890ab
    ```
2. **Access Control**: Access can be controlled through IAM policies, network ACLs, and security groups.
3. **Access Points**: EFS access points can be used to restrict access to specific directories.

Issues with other options:

* **A. Amazon EBS**: EBS only supports ReadWriteOnce (RWO) access mode, so it can only be mounted to one node at a time.
* **C. Amazon S3**: S3 is object storage, not a file system, so it cannot be directly mounted through standard file system interfaces.
* **D. Amazon FSx for Lustre**: FSx for Lustre is suitable for high-performance workloads, but it has more complex setup and higher costs compared to EFS.

</details>

### 4. What is a limitation when using EBS volumes in Amazon EKS?

A. EBS volumes can have simultaneous read/write access from multiple pods B. EBS volumes can be accessed across multiple availability zones C. EBS volumes can only have read/write access from one pod at a time D. EBS volumes can be used with Fargate pods

<details>

<summary>Show Answer</summary>

**Answer: C. EBS volumes can only have read/write access from one pod at a time**

**Explanation:** Amazon EBS (Elastic Block Store) volumes can only have read/write access from one pod at a time. This is a fundamental limitation of EBS, as EBS volumes only support ReadWriteOnce (RWO) access mode.

**Key Limitations:**

1. **Single Node Mount**: EBS volumes can only be mounted to one EC2 instance at a time. Therefore, pods across multiple nodes cannot access the same EBS volume.
2.  **Availability Zone Restriction**: EBS volumes are restricted to the availability zone where they were created. Pods running on nodes in different availability zones cannot access that volume.

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer  # Delay volume creation until pod is scheduled
    ```
3. **Fargate Incompatibility**: Amazon EKS Fargate does not currently support EBS volumes. Fargate pods cannot mount EBS volumes.
4.  **Access Mode Limitation**: EBS only supports the following access mode:

    * ReadWriteOnce (RWO): Read-write mount by a single node

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

**Alternatives to Address These Limitations:**

1.  **Use StatefulSet**: Run stateful applications by providing dedicated EBS volumes to each pod

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
2. **Use Amazon EFS**: Use EFS which supports ReadWriteMany (RWX) access mode when multiple pods need to access the same volume
3. **Volume Replication**: Replicate data to multiple EBS volumes to allow access from multiple pods
4. **Topology-Aware Scheduling**: Use `volumeBindingMode: WaitForFirstConsumer` to create volumes in the availability zone where the pod is scheduled

**Availability Zone Considerations:**

1.  **Use Node Selector**: Schedule pods to nodes in specific availability zones

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
2.  **Volume Snapshot and Restore**: Use volume snapshots when data needs to be moved to different availability zones

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

**Best Practices:**

1. **Appropriate Storage Selection**: Select appropriate storage type based on workload requirements
   * Single pod access: EBS
   * Multi-pod access: EFS
   * High-performance workloads: FSx for Lustre
2. **Availability Zone-Aware Deployment**: Ensure pods and volumes are in the same availability zone
3. **Volume Backup**: Protect data with regular snapshots

Issues with other options:

* **A. EBS volumes can have simultaneous read/write access from multiple pods**: This is incorrect. EBS volumes only support ReadWriteOnce (RWO) access mode.
* **B. EBS volumes can be accessed across multiple availability zones**: This is incorrect. EBS volumes are restricted to the availability zone where they were created.
* **D. EBS volumes can be used with Fargate pods**: This is incorrect. Amazon EKS Fargate does not currently support EBS volumes.

</details>

## Short Answer Questions

### 6. What access mode must be specified in a PersistentVolumeClaim for dynamic provisioning of EBS volumes in Amazon EKS?

<details>

<summary>Show Answer</summary>

**Answer:** ReadWriteOnce (RWO)

**Detailed Explanation:**

The access mode that must be specified in a PersistentVolumeClaim (PVC) for dynamic provisioning of EBS volumes in Amazon EKS is ReadWriteOnce (RWO). This is due to the fundamental characteristics of EBS volumes, which can only have read/write access from one node at a time.

**Access Mode Descriptions:**

1. **ReadWriteOnce (RWO)**: The volume can be mounted in read-write mode by a single node.
2. **ReadOnlyMany (ROX)**: The volume can be mounted in read-only mode by multiple nodes.
3. **ReadWriteMany (RWX)**: The volume can be mounted in read-write mode by multiple nodes.

**Why EBS Only Supports RWO:**

Amazon EBS is a block storage service designed to be attached to only one EC2 instance at a time. This is not a hardware limitation but a design characteristic of the EBS service. Therefore, EBS volumes only support ReadWriteOnce access mode.

**PVC Example:**

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

**Alternatives When Other Access Modes Are Needed:**

1. **When ReadOnlyMany (ROX) is needed:**
   * Create an EBS snapshot and create multiple read-only EBS volumes
   * Provide separate read-only volumes to each node
2.  **When ReadWriteMany (RWX) is needed:**

    * Use Amazon EFS (NFS-based file system)

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

**Considerations When Using EBS Volumes:**

1. **Pod Scheduling**: Pods using EBS volumes can only run on nodes where the volume is attached.
2. **Availability Zone Restriction**: EBS volumes are restricted to the availability zone where they were created. Therefore, pods can only run on nodes in that availability zone.
3.  **Volume Binding Mode**: It's recommended to use `WaitForFirstConsumer` to create volumes after the pod is scheduled.

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer
    ```
4. **Use with StatefulSet**: StatefulSet provides unique PVCs to each pod, making it suitable for use with EBS volumes.

**Access Mode Selection Guide:**

| Storage Type   | ReadWriteOnce | ReadOnlyMany | ReadWriteMany |
| -------------- | ------------- | ------------ | ------------- |
| Amazon EBS     | ✓             | ✗            | ✗             |
| Amazon EFS     | ✓             | ✓            | ✓             |
| FSx for Lustre | ✓             | ✓            | ✓             |

When using EBS volumes, always specify ReadWriteOnce access mode. If simultaneous access from multiple nodes is required, consider alternatives like EFS or FSx for Lustre.

</details>

### 7. What happens to the data when a pod using an EBS volume in Amazon EKS moves to a different node?

<details>

<summary>Show Answer</summary>

**Answer:** The EBS volume is detached from the previous node and attached to the new node. The data is preserved, but there may be delays during the volume reattachment process.

**Detailed Explanation:**

When a pod using an EBS volume in Amazon EKS moves to a different node (e.g., due to node failure, scaling, updates, etc.), the EBS volume is detached from the previous node and attached to the new node. During this process, data is preserved, but there may be delays during the volume reattachment process.

**Volume Reattachment Process:**

1. **Pod Termination**: The pod is terminated on the original node.
2. **Volume Detachment**: The EBS volume is detached from the original node.
3. **Volume Attachment**: The EBS volume is attached to the new node.
4. **Pod Startup**: The pod starts on the new node and the volume is mounted.

**Impact of This Process:**

1. **Delay Time**: Volume detachment and attachment operations typically take 10-30 seconds, but may take longer in some cases.
2. **Availability Zone Restriction**: EBS volumes are restricted to the availability zone where they were created, so pods can only move to other nodes within the same availability zone.
3. **Data Persistence**: Data is preserved and not lost during the volume reattachment process.

**Strategies to Handle This Behavior:**

1.  **Use PodDisruptionBudget**: Ensure availability by limiting the number of pods that can be disrupted simultaneously

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
2.  **Configure Appropriate readinessProbe and livenessProbe**: Delay traffic reception until the volume is properly mounted and the application is ready

    ```yaml
    readinessProbe:
      exec:
        command:
        - cat
        - /data/ready
      initialDelaySeconds: 5
      periodSeconds: 5
    ```
3. **Use StatefulSet**: StatefulSet provides sequential deployment and scaling to minimize the impact of volume reattachment.
4.  **Optimize Volume Binding Mode**: Use `WaitForFirstConsumer` to create volumes in the availability zone where the pod is scheduled

    ```yaml
    volumeBindingMode: WaitForFirstConsumer
    ```

**Availability Zone Considerations:**

1. **Multi-AZ Deployment**: Deploy applications across multiple availability zones for resilience against single AZ failures
2.  **Topology Spread**: Use `topologySpreadConstraints` to spread pods across multiple availability zones

    ```yaml
    topologySpreadConstraints:
    - maxSkew: 1
      topologyKey: topology.kubernetes.io/zone
      whenUnsatisfiable: DoNotSchedule
      labelSelector:
        matchLabels:
          app: my-app
    ```
3. **Availability Zone-Aware PDB**: Configure separate PodDisruptionBudgets for each availability zone

**Best Practices:**

1. **Optimize Applications for Fast Restart**: Design applications to start and initialize quickly
2.  **Set Appropriate Termination Grace Period**: Provide sufficient time for applications to terminate gracefully

    ```yaml
    terminationGracePeriodSeconds: 60
    ```
3. **Backup Strategy for Critical Data**: Protect data through regular snapshots or backups
4. **Consider Stateless Design**: When possible, design applications as stateless to minimize the impact of node moves

When a pod using an EBS volume moves between nodes, data is preserved, but delays may occur during the volume reattachment process, so application design and configuration that accounts for this is important.

</details>

### 9. What Kubernetes API resource is used to create EBS volume snapshots in Amazon EKS?

<details>

<summary>Show Answer</summary>

**Answer:** VolumeSnapshot

**Detailed Explanation:**

The Kubernetes API resource used to create EBS volume snapshots in Amazon EKS is `VolumeSnapshot`. This resource is part of the Kubernetes Volume Snapshot API and works with CSI (Container Storage Interface) drivers to create point-in-time copies of persistent volumes.

**Prerequisites for Using VolumeSnapshot:**

1. **EBS CSI Driver Installation**: The AWS EBS CSI driver must be installed in the cluster.
2.  **Snapshot Controller Installation**: The Kubernetes snapshot controller must be installed in the cluster.

    ```bash
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/client/config/crd/snapshot.storage.k8s.io_volumesnapshotclasses.yaml
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/client/config/crd/snapshot.storage.k8s.io_volumesnapshotcontents.yaml
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/client/config/crd/snapshot.storage.k8s.io_volumesnapshots.yaml
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/deploy/kubernetes/snapshot-controller/rbac-snapshot-controller.yaml
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/deploy/kubernetes/snapshot-controller/setup-snapshot-controller.yaml
    ```
3. **Create VolumeSnapshotClass**: Create a VolumeSnapshotClass that defines how snapshots are created.

**VolumeSnapshotClass Example:**

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: ebs-snapshot-class
driver: ebs.csi.aws.com
deletionPolicy: Delete
```

**VolumeSnapshot Creation Example:**

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

**Check Snapshot Status:**

```bash
kubectl get volumesnapshot ebs-volume-snapshot
```

**Create New PVC from Snapshot:**

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

**Key Benefits of VolumeSnapshot:**

1. **Data Protection**: Create point-in-time backups of critical data
2. **Disaster Recovery**: Support recovery in case of data loss or corruption
3. **Environment Replication**: Replicate production data for development or test environments
4. **Data Migration**: Move data from one cluster to another

**Snapshot Lifecycle Management:**

1.  **Automated Snapshot Creation**: Automate regular snapshot creation using CronJob

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
2.  **Snapshot Retention Policy**: Automatically delete old snapshots

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

**Best Practices:**

1. **Regular Snapshots**: Set up regular snapshot schedules for critical data
2. **Test Snapshots**: Regularly test restoring from snapshots to verify backup validity
3. **Tagging**: Apply appropriate tags to snapshots for easier management and cost tracking
4. **Cost Monitoring**: Monitor and optimize costs as EBS snapshots incur additional charges
5. **Encryption**: Use encrypted snapshots for sensitive data

Using the VolumeSnapshot API allows you to create and manage EBS volume snapshots in a Kubernetes-native way, enabling effective implementation of data protection and recovery strategies.

</details>

## Hands-on Questions

### 10. Design a storage solution for applications with diverse storage requirements in an Amazon EKS cluster. Create storage classes and persistent volume claims that meet the following requirements:

* High-performance block storage for databases
* Configuration files that need to be shared across multiple pods
* High-performance parallel file system for AI/ML workloads

<details>

<summary>Show Answer</summary>

**Answer:**

Here's a storage solution to meet diverse storage requirements in an Amazon EKS cluster:

### 1. High-Performance Block Storage for Databases (Amazon EBS gp3)

#### StorageClass Definition:

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

#### PersistentVolumeClaim Definition:

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

#### Database Pod Example:

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

**Explanation:**

* **gp3 Volume Type**: Provides up to 16,000 IOPS and 1,000MB/s throughput, suitable for database workloads.
* **WaitForFirstConsumer**: Delays volume creation until pod scheduling to prevent availability zone issues.
* **Encryption**: Enables EBS volume encryption for data-at-rest security.
* **Volume Expansion**: Allows volume expansion for future database size increases.
* **StatefulSet**: Provides stable network IDs and persistent storage for databases.

### 2. Configuration Files Shared Across Multiple Pods (Amazon EFS)

#### EFS CSI Driver Installation:

```bash
helm repo add aws-efs-csi-driver https://kubernetes-sigs.github.io/aws-efs-csi-driver/
helm repo update
helm upgrade -i aws-efs-csi-driver aws-efs-csi-driver/aws-efs-csi-driver \
  --namespace kube-system \
  --set controller.serviceAccount.create=true \
  --set controller.serviceAccount.name=efs-csi-controller-sa
```

#### StorageClass Definition:

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

#### PersistentVolumeClaim Definition:

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

#### Deployment Example Using Configuration Files:

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

**Explanation:**

* **ReadWriteMany Access Mode**: EFS supports multiple pods simultaneously reading and writing to the same volume.
* **Multi-Availability Zone Support**: EFS can be accessed across multiple availability zones, providing resilience against node failures.
* **Auto Scaling**: EFS automatically scales based on usage, eliminating capacity planning needs.
* **Access Points**: EFS access points can be used to restrict access to specific directories.

### 3. High-Performance Parallel File System for AI/ML Workloads (Amazon FSx for Lustre)

#### FSx CSI Driver Installation:

```bash
helm repo add aws-fsx-csi-driver https://kubernetes-sigs.github.io/aws-fsx-csi-driver/
helm repo update
helm upgrade -i aws-fsx-csi-driver aws-fsx-csi-driver/aws-fsx-csi-driver \
  --namespace kube-system \
  --set controller.serviceAccount.create=true \
  --set controller.serviceAccount.name=fsx-csi-controller-sa
```

#### StorageClass Definition:

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

#### PersistentVolumeClaim Definition:

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

#### ML Training Job Example:

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

**Explanation:**

* **High Performance**: FSx for Lustre provides hundreds of GB/s throughput and millions of IOPS, suitable for AI/ML workloads.
* **Parallel Access**: Multiple compute nodes can access the same data simultaneously, ideal for distributed training.
* **S3 Integration**: Training data can be stored in S3 and imported to FSx for Lustre for processing.
* **Data Compression**: Uses LZ4 compression for improved storage efficiency.
* **SCRATCH\_2 Deployment Type**: High-performance, cost-effective option for temporary processing.

### Additional Considerations and Best Practices

#### 1. Backup and Disaster Recovery:

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

#### 2. Monitoring and Alerting:

* Set up CloudWatch alarms to monitor storage usage, latency, and throughput.
* Use Prometheus and Grafana to visualize storage metrics.

#### 3. Cost Optimization:

* Delete or create snapshots of unused volumes before deleting.
* Select appropriate storage types and sizes to optimize costs.
* For FSx for Lustre, use SCRATCH deployment type if long-term storage is not needed.

#### 4. Security:

* Enable encryption for all volumes.
* Configure appropriate IAM permissions and security groups.
* Use PodSecurityPolicy or SecurityContext to restrict volume access.

This design provides a comprehensive storage solution that meets diverse workload requirements:

* High-performance EBS gp3 volumes for databases
* EFS supporting multi-read/write access for configuration file sharing
* High-performance parallel file system FSx for Lustre for AI/ML workloads

Each storage solution is optimized for specific workload requirements and designed with scalability, performance, and cost efficiency in mind.

</details>

# Amazon EKS 스토리지 - Part 1: 기본 개념, EBS, EFS

Amazon EKS에서 애플리케이션을 실행할 때 데이터를 저장하고 관리하기 위한 다양한 스토리지 옵션이 있습니다. 이 문서에서는 EKS 스토리지의 기본 개념과 Amazon EBS(Elastic Block Store) 및 Amazon EFS(Elastic File System)를 사용하는 방법에 대해 알아보겠습니다.

## 목차

1. [Kubernetes 스토리지 기본 개념](#kubernetes-스토리지-기본-개념)
2. [Amazon EKS 스토리지 옵션 개요](#amazon-eks-스토리지-옵션-개요)
3. [Amazon EBS를 사용한 스토리지](#amazon-ebs를-사용한-스토리지)
4. [Amazon EFS를 사용한 스토리지](#amazon-efs를-사용한-스토리지)
5. [스토리지 클래스 및 동적 프로비저닝](#스토리지-클래스-및-동적-프로비저닝)

## Kubernetes 스토리지 기본 개념

Kubernetes에서 스토리지를 관리하기 위한 핵심 개념들을 먼저 이해해 보겠습니다.

### 볼륨(Volume)

볼륨은 파드 내의 컨테이너에 마운트할 수 있는 디렉토리로, 컨테이너가 재시작되더라도 데이터가 유지됩니다. 볼륨의 수명은 파드의 수명과 동일하며, 파드가 삭제되면 볼륨도 함께 삭제됩니다.

### 영구 볼륨(PersistentVolume, PV)

영구 볼륨은 관리자가 프로비저닝하거나 스토리지 클래스를 통해 동적으로 프로비저닝된 클러스터의 스토리지 조각입니다. PV는 파드와 독립적인 수명 주기를 가지며, 파드가 삭제되어도 PV는 유지됩니다.

### 영구 볼륨 클레임(PersistentVolumeClaim, PVC)

영구 볼륨 클레임은 사용자의 스토리지 요청입니다. PVC는 특정 크기와 액세스 모드를 가진 스토리지를 요청하며, 이 요청은 적절한 PV에 바인딩됩니다.

### 스토리지 클래스(StorageClass)

스토리지 클래스는 관리자가 제공하는 스토리지의 "클래스"를 설명합니다. 스토리지 클래스를 사용하면 PVC가 생성될 때 동적으로 PV를 프로비저닝할 수 있습니다.

### 액세스 모드

Kubernetes는 다음과 같은 액세스 모드를 지원합니다:

- **ReadWriteOnce(RWO)**: 단일 노드에서 읽기/쓰기로 마운트 가능
- **ReadOnlyMany(ROX)**: 여러 노드에서 읽기 전용으로 마운트 가능
- **ReadWriteMany(RWX)**: 여러 노드에서 읽기/쓰기로 마운트 가능
- **ReadWriteOncePod(RWOP)**: 단일 파드에서만 읽기/쓰기로 마운트 가능 (Kubernetes 1.22+)

## Amazon EKS 스토리지 옵션 개요

Amazon EKS에서는 다양한 AWS 스토리지 서비스를 활용하여 컨테이너화된 애플리케이션에 스토리지를 제공할 수 있습니다.

### 주요 스토리지 옵션

1. **Amazon EBS(Elastic Block Store)**
   - 블록 스토리지로, 단일 노드에 마운트 가능(RWO)
   - 고성능, 내구성 있는 블록 스토리지
   - 데이터베이스, 상태 유지 애플리케이션에 적합

2. **Amazon EFS(Elastic File System)**
   - 완전 관리형 NFS 파일 시스템
   - 여러 노드에서 동시에 마운트 가능(RWX)
   - 공유 파일 시스템이 필요한 워크로드에 적합

3. **Amazon FSx for Lustre**
   - 고성능 파일 시스템
   - 기계 학습, HPC, 빅 데이터 분석에 적합
   - 여러 노드에서 동시에 마운트 가능(RWX)

4. **Amazon S3(Simple Storage Service)**
   - 객체 스토리지
   - 직접 볼륨으로 마운트할 수 없지만, S3 API를 통해 액세스 가능
   - 대용량 데이터 저장에 적합

### 스토리지 옵션 비교

| 스토리지 옵션 | 유형 | 액세스 모드 | 성능 | 사용 사례 |
|--------------|------|------------|------|----------|
| Amazon EBS | 블록 | RWO | 높음 | 데이터베이스, 상태 유지 애플리케이션 |
| Amazon EFS | 파일 | RWX | 중간 | 공유 파일, 웹 서버, CMS |
| FSx for Lustre | 파일 | RWX | 매우 높음 | HPC, ML 훈련, 빅 데이터 |
| Amazon S3 | 객체 | API 액세스 | 중간 | 백업, 아카이브, 정적 콘텐츠 |

## Amazon EBS를 사용한 스토리지

Amazon EBS는 EC2 인스턴스에 연결할 수 있는 블록 수준 스토리지 볼륨을 제공합니다. EKS에서는 EBS CSI(Container Storage Interface) 드라이버를 통해 EBS 볼륨을 Kubernetes 파드에 마운트할 수 있습니다.

### EBS CSI 드라이버 설치

EBS CSI 드라이버를 설치하기 위해 다음 단계를 따릅니다:

1. IAM 역할 생성:

```bash
eksctl create iamserviceaccount \
  --name ebs-csi-controller-sa \
  --namespace kube-system \
  --cluster my-cluster \
  --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy \
  --approve \
  --role-only \
  --role-name AmazonEKS_EBS_CSI_DriverRole
```

2. 애드온 설치:

```bash
eksctl create addon \
  --name aws-ebs-csi-driver \
  --cluster my-cluster \
  --service-account-role-arn arn:aws:iam::111122223333:role/AmazonEKS_EBS_CSI_DriverRole \
  --force
```

### EBS 스토리지 클래스 생성

EBS gp3 볼륨을 사용하는 스토리지 클래스를 생성합니다:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  encrypted: "true"
  fsType: ext4
  iops: "3000"
  throughput: "125"
allowVolumeExpansion: true
```

### PVC 생성 및 파드에 마운트

1. PVC 생성:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-claim
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 10Gi
```

2. 파드에 PVC 마운트:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-ebs
spec:
  containers:
  - name: app
    image: nginx
    volumeMounts:
    - mountPath: "/data"
      name: ebs-volume
  volumes:
  - name: ebs-volume
    persistentVolumeClaim:
      claimName: ebs-claim
```

### EBS 볼륨 스냅샷

EBS 볼륨의 스냅샷을 생성하여 데이터를 백업할 수 있습니다:

1. 볼륨 스냅샷 클래스 생성:

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: ebs-snapshot-class
driver: ebs.csi.aws.com
deletionPolicy: Delete
```

2. 볼륨 스냅샷 생성:

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

3. 스냅샷에서 PVC 복원:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-claim-restored
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 10Gi
  dataSource:
    name: ebs-volume-snapshot
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
```

### EBS 볼륨 유형 및 성능 특성

Amazon EBS는 다양한 볼륨 유형을 제공하며, 각각 다른 성능 특성과 비용을 가집니다:

| 볼륨 유형 | 설명 | IOPS | 처리량 | 사용 사례 |
|----------|------|------|-------|----------|
| gp3 | 범용 SSD | 3,000-16,000 | 125-1,000 MiB/s | 대부분의 워크로드 |
| gp2 | 범용 SSD | 100-16,000 | 최대 250 MiB/s | 중소 규모 워크로드 |
| io2 | 프로비저닝된 IOPS SSD | 최대 64,000 | 최대 1,000 MiB/s | 고성능 데이터베이스 |
| io1 | 프로비저닝된 IOPS SSD | 최대 64,000 | 최대 1,000 MiB/s | 고성능 데이터베이스 |
| st1 | 처리량 최적화 HDD | 최대 500 | 최대 500 MiB/s | 빅 데이터, 로그 처리 |
| sc1 | 콜드 HDD | 최대 250 | 최대 250 MiB/s | 자주 액세스하지 않는 데이터 |

EKS에서는 gp3 볼륨 유형을 권장합니다. gp3는 gp2보다 비용 효율적이며, 기본 성능이 더 높습니다.

## Amazon EFS를 사용한 스토리지

Amazon EFS는 여러 EC2 인스턴스에서 동시에 마운트할 수 있는 확장 가능한 파일 시스템을 제공합니다. EKS에서는 EFS CSI 드라이버를 통해 EFS 파일 시스템을 Kubernetes 파드에 마운트할 수 있습니다.

### EFS CSI 드라이버 설치

EFS CSI 드라이버를 설치하기 위해 다음 단계를 따릅니다:

1. IAM 역할 생성:

```bash
eksctl create iamserviceaccount \
  --name efs-csi-controller-sa \
  --namespace kube-system \
  --cluster my-cluster \
  --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEFSCSIDriverPolicy \
  --approve \
  --role-only \
  --role-name AmazonEKS_EFS_CSI_DriverRole
```

2. 애드온 설치:

```bash
eksctl create addon \
  --name aws-efs-csi-driver \
  --cluster my-cluster \
  --service-account-role-arn arn:aws:iam::111122223333:role/AmazonEKS_EFS_CSI_DriverRole \
  --force
```

### EFS 파일 시스템 생성

EFS 파일 시스템을 생성하고 EKS 클러스터의 VPC에 마운트 타겟을 설정합니다:

```bash
# EKS 클러스터의 VPC ID 가져오기
VPC_ID=$(aws eks describe-cluster \
  --name my-cluster \
  --query "cluster.resourcesVpcConfig.vpcId" \
  --output text)

# 보안 그룹 생성
SECURITY_GROUP_ID=$(aws ec2 create-security-group \
  --group-name EfsSecurityGroup \
  --description "Security group for EFS mount targets" \
  --vpc-id $VPC_ID \
  --output text)

# NFS 트래픽 허용
aws ec2 authorize-security-group-ingress \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 2049 \
  --cidr $VPC_CIDR

# EFS 파일 시스템 생성
FILE_SYSTEM_ID=$(aws efs create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --encrypted \
  --tags Key=Name,Value=MyEfsFileSystem \
  --query "FileSystemId" \
  --output text)

# 서브넷 ID 가져오기
SUBNET_IDS=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "Subnets[*].SubnetId" \
  --output text)

# 각 서브넷에 마운트 타겟 생성
for SUBNET_ID in $SUBNET_IDS; do
  aws efs create-mount-target \
    --file-system-id $FILE_SYSTEM_ID \
    --subnet-id $SUBNET_ID \
    --security-groups $SECURITY_GROUP_ID
done
```

### EFS 스토리지 클래스 생성

EFS를 사용하는 스토리지 클래스를 생성합니다:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: "700"
  gidRangeStart: "1000"
  gidRangeEnd: "2000"
  basePath: "/dynamic_provisioning"
```

### PVC 생성 및 파드에 마운트

1. PVC 생성:

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

2. 파드에 PVC 마운트:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-efs
spec:
  containers:
  - name: app
    image: nginx
    volumeMounts:
    - mountPath: "/data"
      name: efs-volume
  volumes:
  - name: efs-volume
    persistentVolumeClaim:
      claimName: efs-claim
```

### 정적 프로비저닝을 사용한 EFS 마운트

이미 생성된 EFS 파일 시스템을 정적으로 마운트할 수도 있습니다:

1. PV 생성:

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
  csi:
    driver: efs.csi.aws.com
    volumeHandle: fs-0123456789abcdef0
```

2. PVC 생성:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-claim-static
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: efs-sc
  resources:
    requests:
      storage: 5Gi
```

### EFS 성능 모드 및 처리량 모드

Amazon EFS는 다양한 성능 요구사항을 충족하기 위해 여러 성능 모드와 처리량 모드를 제공합니다:

#### 성능 모드

- **범용 모드(General Purpose)**: 대부분의 파일 시스템 워크로드에 권장되는 기본 모드입니다. 낮은 지연 시간과 높은 처리량을 제공합니다.
- **최대 I/O 모드(Max I/O)**: 높은 집계 처리량과 초당 작업 수를 제공하지만, 지연 시간이 약간 더 높습니다. 수천 개의 EC2 인스턴스가 동시에 파일 시스템에 액세스하는 빅 데이터 분석, 미디어 처리, 게놈 분석과 같은 워크로드에 적합합니다.

#### 처리량 모드

- **버스팅 모드(Bursting)**: 파일 시스템 크기에 따라 기본 처리량이 결정되며, 필요에 따라 버스트할 수 있습니다. 작은 파일 시스템의 경우 100MiB/s까지 버스트할 수 있습니다.
- **프로비저닝된 모드(Provisioned)**: 파일 시스템 크기와 관계없이 지정된 처리량 수준을 제공합니다. 1-3,072MiB/s 범위에서 처리량을 지정할 수 있습니다.
- **탄력적 모드(Elastic)**: 워크로드에 따라 자동으로 처리량을 확장 및 축소합니다. 예측할 수 없거나 변동이 심한 워크로드에 적합합니다.

### EFS 액세스 포인트

EFS 액세스 포인트는 애플리케이션별 진입점을 생성하여 공유 파일 시스템에 대한 액세스를 관리하는 데 도움이 됩니다:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-ap-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: "700"
  gidRangeStart: "1000"
  gidRangeEnd: "2000"
  basePath: "/dynamic_provisioning"
```

액세스 포인트를 사용하면 다음과 같은 이점이 있습니다:

- 애플리케이션별 루트 디렉토리 적용
- 사용자 및 그룹 ID 적용
- 파일 시스템 액세스 제한

## 스토리지 클래스 및 동적 프로비저닝

Kubernetes의 스토리지 클래스를 사용하면 스토리지 리소스를 동적으로 프로비저닝할 수 있습니다. EKS에서는 다양한 AWS 스토리지 서비스에 대한 스토리지 클래스를 구성할 수 있습니다.

### 기본 스토리지 클래스 설정

특정 스토리지 클래스를 기본값으로 설정하려면 `storageclass.kubernetes.io/is-default-class: "true"` 주석을 추가합니다:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  encrypted: "true"
```

### 볼륨 바인딩 모드

스토리지 클래스의 `volumeBindingMode` 필드는 PVC가 생성될 때 PV가 바인딩되는 방식을 결정합니다:

- **Immediate**: PVC가 생성되는 즉시 PV가 프로비저닝되고 바인딩됩니다.
- **WaitForFirstConsumer**: PVC를 사용하는 파드가 생성될 때까지 PV 프로비저닝 및 바인딩이 지연됩니다. 이 모드는 특히 EBS와 같은 영역 제한 스토리지를 사용할 때 권장됩니다.

### 재확보 정책

PV의 `persistentVolumeReclaimPolicy` 필드는 PVC가 삭제될 때 PV에 어떤 일이 발생하는지 결정합니다:

- **Delete**: PVC가 삭제되면 PV와 기본 스토리지 리소스가 자동으로 삭제됩니다.
- **Retain**: PVC가 삭제되어도 PV와 기본 스토리지 리소스는 유지됩니다. 관리자가 수동으로 정리해야 합니다.
- **Recycle**: 사용되지 않는 정책으로, 대신 동적 프로비저닝과 스토리지 클래스를 사용하는 것이 좋습니다.

### 볼륨 확장

스토리지 클래스에서 `allowVolumeExpansion: true`를 설정하면 PVC의 크기를 확장할 수 있습니다:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3-expandable
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
allowVolumeExpansion: true
```

PVC 크기 확장:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-claim
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: ebs-gp3-expandable
  resources:
    requests:
      storage: 20Gi  # 원래 10Gi에서 20Gi로 확장
```

## 결론

이 문서에서는 Amazon EKS에서 스토리지의 기본 개념과 Amazon EBS 및 Amazon EFS를 사용하는 방법에 대해 알아보았습니다. 각 스토리지 옵션은 서로 다른 특성과 사용 사례를 가지고 있으므로, 애플리케이션의 요구사항에 맞는 적절한 스토리지 솔루션을 선택하는 것이 중요합니다.

다음 파트에서는 Amazon FSx for Lustre, S3, 스냅샷, 볼륨 확장, 성능 최적화 등 더 고급 스토리지 주제에 대해 알아보겠습니다.

## 참고 자료

- [Kubernetes 스토리지 문서](https://kubernetes.io/docs/concepts/storage/)
- [Amazon EBS CSI 드라이버](https://github.com/kubernetes-sigs/aws-ebs-csi-driver)
- [Amazon EFS CSI 드라이버](https://github.com/kubernetes-sigs/aws-efs-csi-driver)
- [Amazon EKS 스토리지 모범 사례](https://aws.github.io/aws-eks-best-practices/storage/)

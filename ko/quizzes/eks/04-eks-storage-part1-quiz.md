# EKS 스토리지 퀴즈 - Part 1

이 퀴즈는 Amazon EKS의 스토리지 개념, 영구 볼륨, 스토리지 클래스 및 동적 프로비저닝에 대한 이해를 테스트합니다.

## 객관식 문제

### 1. Amazon EKS에서 기본적으로 지원하는 스토리지 드라이버는 무엇인가요?

A. Amazon EFS CSI 드라이버\
B. Amazon EBS CSI 드라이버\
C. Amazon FSx for Lustre CSI 드라이버\
D. Amazon S3 CSI 드라이버

<details>

<summary>정답 및 설명</summary>

**정답: B. Amazon EBS CSI 드라이버**

**설명:** Amazon EKS에서 기본적으로 지원하는 스토리지 드라이버는 Amazon EBS CSI(Container Storage Interface) 드라이버입니다. 이 드라이버는 Amazon EKS 클러스터에서 Amazon Elastic Block Store(EBS) 볼륨을 영구 스토리지로 사용할 수 있게 해줍니다.

**주요 특징:**

1.  **EKS 애드온으로 제공**: Amazon EBS CSI 드라이버는 EKS 애드온으로 제공되어 쉽게 설치하고 관리할 수 있습니다.

    ```bash
    aws eks create-addon \
      --cluster-name my-cluster \
      --addon-name aws-ebs-csi-driver \
      --service-account-role-arn arn:aws:iam::111122223333:role/AmazonEKS_EBS_CSI_DriverRole
    ```
2.  **동적 프로비저닝 지원**: StorageClass를 통해 EBS 볼륨의 동적 프로비저닝을 지원합니다.

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
3.  **볼륨 스냅샷 기능**: 볼륨 스냅샷 및 복원 기능을 지원합니다.

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
4. **다양한 EBS 볼륨 유형 지원**: gp2, gp3, io1, io2, sc1, st1 등 다양한 EBS 볼륨 유형을 지원합니다.

**필요한 IAM 권한:**

EBS CSI 드라이버가 작동하려면 다음과 같은 IAM 권한이 필요합니다:

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

**제한 사항:**

1. **가용성 영역 제한**: EBS 볼륨은 단일 가용성 영역에 제한되므로, 파드는 볼륨과 동일한 가용성 영역에서 실행되어야 합니다.
2. **단일 노드 마운트**: EBS 볼륨은 한 번에 하나의 노드에만 마운트할 수 있습니다(ReadWriteOnce 액세스 모드).
3. **Fargate 제한**: Amazon EKS Fargate는 현재 EBS CSI 드라이버를 지원하지 않습니다.

다른 옵션들의 문제점:

* **A. Amazon EFS CSI 드라이버**: EFS CSI 드라이버는 EKS에서 지원되지만 기본으로 설치되지는 않습니다. 별도로 설치해야 합니다.
* **C. Amazon FSx for Lustre CSI 드라이버**: FSx for Lustre CSI 드라이버는 EKS에서 지원되지만 기본으로 설치되지는 않습니다. 별도로 설치해야 합니다.
* **D. Amazon S3 CSI 드라이버**: 현재 공식적인 Amazon S3 CSI 드라이버는 존재하지 않습니다. S3는 일반적으로 CSI를 통해 직접 마운트되지 않고, S3 API를 통해 액세스합니다.

</details>

### 2. Amazon EKS에서 여러 파드가 동시에 읽기/쓰기 액세스를 필요로 할 때 가장 적합한 스토리지 솔루션은 무엇인가요?

A. Amazon EBS\
B. Amazon EFS\
C. Amazon S3\
D. Amazon FSx for Lustre

<details>

<summary>정답 및 설명</summary>

**정답: B. Amazon EFS**

**설명:** Amazon EKS에서 여러 파드가 동시에 읽기/쓰기 액세스를 필요로 할 때 가장 적합한 스토리지 솔루션은 Amazon EFS(Elastic File System)입니다. EFS는 ReadWriteMany(RWX) 액세스 모드를 지원하는 관리형 NFS(Network File System) 서비스로, 여러 파드가 동시에 동일한 볼륨에 읽고 쓸 수 있습니다.

**주요 특징:**

1. **다중 가용성 영역 액세스**: EFS는 여러 가용성 영역에 걸쳐 액세스할 수 있어, 다른 노드와 가용성 영역에서 실행되는 파드가 동일한 데이터에 액세스할 수 있습니다.
2.  **ReadWriteMany 지원**: EFS는 ReadWriteMany(RWX) 액세스 모드를 지원하여 여러 파드가 동시에 동일한 볼륨에 읽고 쓸 수 있습니다.

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
3. **확장성**: EFS는 자동으로 확장되므로 용량 계획이 필요하지 않습니다.
4. **내구성 및 가용성**: 99.999999999%(11 9's)의 내구성과 99.99%의 가용성을 제공합니다.

**EFS CSI 드라이버 설치:**

```bash
# Helm을 사용한 설치
helm repo add aws-efs-csi-driver https://kubernetes-sigs.github.io/aws-efs-csi-driver/
helm repo update
helm upgrade -i aws-efs-csi-driver aws-efs-csi-driver/aws-efs-csi-driver \
  --namespace kube-system \
  --set controller.serviceAccount.create=true \
  --set controller.serviceAccount.name=efs-csi-controller-sa
```

**EFS 파일 시스템 생성:**

```bash
# EFS 파일 시스템 생성
aws efs create-file-system \
  --creation-token eks-efs \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --tags Key=Name,Value=EKS-EFS

# 마운트 타겟 생성
aws efs create-mount-target \
  --file-system-id fs-0123456789abcdef0 \
  --subnet-id subnet-0123456789abcdef0 \
  --security-groups sg-0123456789abcdef0
```

**StorageClass 및 PVC 구성:**

```yaml
# StorageClass 생성
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: "700"

# PVC 생성
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

**사용 사례:**

1. **공유 파일 시스템**: 여러 파드가 동일한 파일에 액세스해야 하는 경우
2. **웹 서버 콘텐츠**: 여러 웹 서버 파드가 동일한 정적 콘텐츠를 제공해야 하는 경우
3. **로그 집계**: 여러 파드가 동일한 로그 디렉토리에 쓰는 경우
4. **CI/CD 파이프라인**: 빌드 아티팩트를 공유해야 하는 경우

**성능 고려 사항:**

1. **성능 모드**:
   * General Purpose: 대부분의 워크로드에 적합
   * Max I/O: 높은 처리량이 필요한 워크로드에 적합
2. **처리량 모드**:
   * Bursting: 기본 모드, 파일 시스템 크기에 따라 버스트 크레딧 제공
   * Provisioned: 일관된 처리량이 필요한 경우 특정 처리량 프로비저닝
3. **지연 시간**: EFS는 블록 스토리지보다 지연 시간이 높을 수 있으므로, 지연 시간에 민감한 애플리케이션에는 적합하지 않을 수 있습니다.

**보안 고려 사항:**

1.  **암호화**: EFS는 전송 중 암호화와 저장 데이터 암호화를 지원합니다.

    ```bash
    aws efs create-file-system \
      --creation-token eks-efs \
      --encrypted \
      --kms-key-id 1234abcd-12ab-34cd-56ef-1234567890ab
    ```
2. **액세스 제어**: IAM 정책, 네트워크 ACL, 보안 그룹을 통해 액세스를 제어할 수 있습니다.
3. **액세스 포인트**: EFS 액세스 포인트를 사용하여 특정 디렉토리에 대한 액세스를 제한할 수 있습니다.

다른 옵션들의 문제점:

* **A. Amazon EBS**: EBS는 ReadWriteOnce(RWO) 액세스 모드만 지원하므로, 한 번에 하나의 노드에서만 마운트할 수 있습니다.
* **C. Amazon S3**: S3는 파일 시스템이 아니라 객체 스토리지이므로, 표준 파일 시스템 인터페이스를 통해 직접 마운트할 수 없습니다.
* **D. Amazon FSx for Lustre**: FSx for Lustre는 고성능 워크로드에 적합하지만, EFS보다 설정이 복잡하고 비용이 더 높을 수 있습니다.

</details>

### 4. Amazon EKS에서 EBS 볼륨을 사용할 때의 제한 사항은 무엇인가요?

A. EBS 볼륨은 여러 파드에서 동시에 읽기/쓰기 액세스를 할 수 있습니다\
B. EBS 볼륨은 여러 가용성 영역에 걸쳐 액세스할 수 있습니다\
C. EBS 볼륨은 한 번에 하나의 파드에서만 읽기/쓰기 액세스를 할 수 있습니다\
D. EBS 볼륨은 Fargate 파드에서 사용할 수 있습니다

<details>

<summary>정답 및 설명</summary>

**정답: C. EBS 볼륨은 한 번에 하나의 파드에서만 읽기/쓰기 액세스를 할 수 있습니다**

**설명:** Amazon EBS(Elastic Block Store) 볼륨은 한 번에 하나의 파드에서만 읽기/쓰기 액세스를 할 수 있습니다. 이는 EBS의 기본적인 제한 사항으로, EBS 볼륨은 ReadWriteOnce(RWO) 액세스 모드만 지원합니다.

**주요 제한 사항:**

1. **단일 노드 마운트**: EBS 볼륨은 한 번에 하나의 EC2 인스턴스에만 마운트할 수 있습니다. 따라서 여러 노드에 걸쳐 있는 파드에서 동일한 EBS 볼륨에 액세스할 수 없습니다.
2.  **가용성 영역 제한**: EBS 볼륨은 생성된 가용성 영역에 제한됩니다. 다른 가용성 영역의 노드에서 실행되는 파드는 해당 볼륨에 액세스할 수 없습니다.

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer  # 파드가 스케줄링될 때까지 볼륨 생성 지연
    ```
3. **Fargate 호환성 부족**: Amazon EKS Fargate는 현재 EBS 볼륨을 지원하지 않습니다. Fargate 파드는 EBS 볼륨을 마운트할 수 없습니다.
4.  **액세스 모드 제한**: EBS는 다음 액세스 모드만 지원합니다:

    * ReadWriteOnce(RWO): 단일 노드에 의한 읽기-쓰기 마운트

    ```yaml
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: ebs-claim
    spec:
      accessModes:
        - ReadWriteOnce  # EBS에서 지원하는 유일한 액세스 모드
      storageClassName: ebs-sc
      resources:
        requests:
          storage: 10Gi
    ```

**이러한 제한 사항을 해결하기 위한 대안:**

1.  **StatefulSet 사용**: 각 파드에 전용 EBS 볼륨을 제공하여 상태 저장 애플리케이션 실행

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
2. **Amazon EFS 사용**: 여러 파드가 동일한 볼륨에 액세스해야 하는 경우 ReadWriteMany(RWX) 액세스 모드를 지원하는 EFS 사용
3. **볼륨 복제**: 데이터를 여러 EBS 볼륨에 복제하여 여러 파드에서 액세스 가능하게 함
4. **토폴로지 인식 스케줄링**: `volumeBindingMode: WaitForFirstConsumer`를 사용하여 파드가 스케줄링된 가용성 영역에 볼륨 생성

**가용성 영역 고려 사항:**

1.  **노드 선택기 사용**: 특정 가용성 영역의 노드에 파드 스케줄링

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
2.  **볼륨 스냅샷 및 복원**: 다른 가용성 영역으로 데이터 이동이 필요한 경우 볼륨 스냅샷 사용

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

**모범 사례:**

1. **적절한 스토리지 선택**: 워크로드 요구 사항에 따라 적절한 스토리지 유형 선택
   * 단일 파드 액세스: EBS
   * 다중 파드 액세스: EFS
   * 고성능 워크로드: FSx for Lustre
2. **가용성 영역 인식 배포**: 파드와 볼륨이 동일한 가용성 영역에 있도록 보장
3. **볼륨 백업**: 정기적인 스냅샷으로 데이터 보호

다른 옵션들의 문제점:

* **A. EBS 볼륨은 여러 파드에서 동시에 읽기/쓰기 액세스를 할 수 있습니다**: 이는 잘못된 설명입니다. EBS 볼륨은 ReadWriteOnce(RWO) 액세스 모드만 지원합니다.
* **B. EBS 볼륨은 여러 가용성 영역에 걸쳐 액세스할 수 있습니다**: 이는 잘못된 설명입니다. EBS 볼륨은 생성된 가용성 영역에 제한됩니다.
* **D. EBS 볼륨은 Fargate 파드에서 사용할 수 있습니다**: 이는 잘못된 설명입니다. Amazon EKS Fargate는 현재 EBS 볼륨을 지원하지 않습니다.

</details>

## 단답형 문제

### 6. Amazon EKS에서 EBS 볼륨의 동적 프로비저닝을 위해 PersistentVolumeClaim에서 지정해야 하는 액세스 모드는 무엇인가요?

<details>

<summary>정답 및 설명</summary>

**정답:** ReadWriteOnce (RWO)

**상세 설명:**

Amazon EKS에서 EBS 볼륨의 동적 프로비저닝을 위해 PersistentVolumeClaim(PVC)에서 지정해야 하는 액세스 모드는 ReadWriteOnce(RWO)입니다. 이는 EBS 볼륨의 기본적인 특성으로, 한 번에 하나의 노드에서만 읽기/쓰기 액세스가 가능하기 때문입니다.

**액세스 모드 설명:**

1. **ReadWriteOnce (RWO)**: 볼륨이 단일 노드에 의해 읽기-쓰기 모드로 마운트될 수 있습니다.
2. **ReadOnlyMany (ROX)**: 볼륨이 여러 노드에 의해 읽기 전용 모드로 마운트될 수 있습니다.
3. **ReadWriteMany (RWX)**: 볼륨이 여러 노드에 의해 읽기-쓰기 모드로 마운트될 수 있습니다.

**EBS는 RWO만 지원하는 이유:**

Amazon EBS는 블록 스토리지 서비스로, 한 번에 하나의 EC2 인스턴스에만 연결할 수 있도록 설계되었습니다. 이는 하드웨어 제한이 아니라 EBS 서비스의 설계 특성입니다. 따라서 EBS 볼륨은 ReadWriteOnce 액세스 모드만 지원합니다.

**PVC 예시:**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-claim
spec:
  accessModes:
    - ReadWriteOnce  # EBS에서 지원하는 유일한 액세스 모드
  storageClassName: ebs-sc
  resources:
    requests:
      storage: 10Gi
```

**다른 액세스 모드가 필요한 경우의 대안:**

1. **ReadOnlyMany (ROX)가 필요한 경우:**
   * EBS 스냅샷을 생성하고 여러 읽기 전용 EBS 볼륨 생성
   * 각 노드에 별도의 읽기 전용 볼륨 제공
2.  **ReadWriteMany (RWX)가 필요한 경우:**

    * Amazon EFS 사용 (NFS 기반 파일 시스템)

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

**EBS 볼륨 사용 시 고려 사항:**

1. **파드 스케줄링**: EBS 볼륨을 사용하는 파드는 볼륨이 연결된 노드에서만 실행될 수 있습니다.
2. **가용성 영역 제한**: EBS 볼륨은 생성된 가용성 영역에 제한됩니다. 따라서 파드는 해당 가용성 영역의 노드에서만 실행될 수 있습니다.
3.  **볼륨 바인딩 모드**: `WaitForFirstConsumer`를 사용하여 파드가 스케줄링된 후에 볼륨을 생성하는 것이 좋습니다.

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer
    ```
4. **StatefulSet과 함께 사용**: StatefulSet은 각 파드에 고유한 PVC를 제공하므로, EBS 볼륨과 함께 사용하기에 적합합니다.

**액세스 모드 선택 가이드:**

| 스토리지 유형        | ReadWriteOnce | ReadOnlyMany | ReadWriteMany |
| -------------- | ------------- | ------------ | ------------- |
| Amazon EBS     | ✓             | ✗            | ✗             |
| Amazon EFS     | ✓             | ✓            | ✓             |
| FSx for Lustre | ✓             | ✓            | ✓             |

EBS 볼륨을 사용할 때는 항상 ReadWriteOnce 액세스 모드를 지정해야 하며, 여러 노드에서 동시에 액세스해야 하는 경우에는 EFS나 FSx for Lustre와 같은 대안을 고려해야 합니다.

</details>

### 7. Amazon EKS에서 EBS 볼륨을 사용할 때 파드가 다른 노드로 이동하면 데이터에 어떤 일이 발생하나요?

<details>

<summary>정답 및 설명</summary>

**정답:** EBS 볼륨은 이전 노드에서 분리되고 새 노드에 연결됩니다. 데이터는 보존되지만 볼륨 재연결 과정에서 지연이 발생할 수 있습니다.

**상세 설명:**

Amazon EKS에서 EBS 볼륨을 사용하는 파드가 다른 노드로 이동할 때(예: 노드 장애, 스케일링, 업데이트 등으로 인해), EBS 볼륨은 이전 노드에서 분리되고 새 노드에 연결됩니다. 이 과정에서 데이터는 보존되지만, 볼륨 재연결 과정에서 지연이 발생할 수 있습니다.

**볼륨 재연결 프로세스:**

1. **파드 종료**: 원래 노드에서 파드가 종료됩니다.
2. **볼륨 분리**: EBS 볼륨이 원래 노드에서 분리됩니다.
3. **볼륨 연결**: EBS 볼륨이 새 노드에 연결됩니다.
4. **파드 시작**: 새 노드에서 파드가 시작되고 볼륨이 마운트됩니다.

**이 프로세스의 영향:**

1. **지연 시간**: 볼륨 분리 및 연결 작업은 일반적으로 10-30초가 소요되지만, 경우에 따라 더 오래 걸릴 수 있습니다.
2. **가용성 영역 제한**: EBS 볼륨은 생성된 가용성 영역에 제한되므로, 파드는 동일한 가용성 영역 내의 다른 노드로만 이동할 수 있습니다.
3. **데이터 지속성**: 볼륨 재연결 과정에서 데이터는 보존되며 손실되지 않습니다.

**이 동작을 처리하기 위한 전략:**

1.  **PodDisruptionBudget 사용**: 동시에 중단될 수 있는 파드 수를 제한하여 가용성 보장

    ```yaml
    apiVersion: policy/v1
    kind: PodDisruptionBudget
    metadata:
      name: app-pdb
    spec:
      minAvailable: 2  # 또는 maxUnavailable: 1
      selector:
        matchLabels:
          app: my-app
    ```
2.  **적절한 readinessProbe 및 livenessProbe 구성**: 볼륨이 제대로 마운트되고 애플리케이션이 준비될 때까지 트래픽 수신 지연

    ```yaml
    readinessProbe:
      exec:
        command:
        - cat
        - /data/ready
      initialDelaySeconds: 5
      periodSeconds: 5
    ```
3. **StatefulSet 사용**: StatefulSet은 순차적인 배포 및 스케일링을 제공하여 볼륨 재연결 과정의 영향을 최소화합니다.
4.  **볼륨 바인딩 모드 최적화**: `WaitForFirstConsumer`를 사용하여 파드가 스케줄링된 가용성 영역에 볼륨 생성

    ```yaml
    volumeBindingMode: WaitForFirstConsumer
    ```

**가용성 영역 고려 사항:**

1. **다중 AZ 배포**: 여러 가용성 영역에 걸쳐 애플리케이션을 배포하여 단일 AZ 장애에 대한 복원력 제공
2.  **토폴로지 분산**: `topologySpreadConstraints`를 사용하여 파드를 여러 가용성 영역에 분산

    ```yaml
    topologySpreadConstraints:
    - maxSkew: 1
      topologyKey: topology.kubernetes.io/zone
      whenUnsatisfiable: DoNotSchedule
      labelSelector:
        matchLabels:
          app: my-app
    ```
3. **가용성 영역 인식 PDB**: 각 가용성 영역에 대해 별도의 PodDisruptionBudget 구성

**모범 사례:**

1. **빠른 재시작을 위한 애플리케이션 최적화**: 애플리케이션이 빠르게 시작되고 초기화되도록 설계
2.  **적절한 종료 유예 기간 설정**: 애플리케이션이 정상적으로 종료될 수 있도록 충분한 시간 제공

    ```yaml
    terminationGracePeriodSeconds: 60
    ```
3. **중요한 데이터에 대한 백업 전략**: 정기적인 스냅샷 또는 백업을 통해 데이터 보호
4. **상태 비저장 설계 고려**: 가능한 경우 애플리케이션을 상태 비저장으로 설계하여 노드 이동의 영향 최소화

EBS 볼륨을 사용하는 파드가 노드 간에 이동할 때 데이터는 보존되지만, 볼륨 재연결 과정에서 지연이 발생할 수 있으므로 이를 고려한 애플리케이션 설계와 구성이 중요합니다.

</details>

### 9. Amazon EKS에서 EBS 볼륨 스냅샷을 생성하기 위해 사용하는 Kubernetes API 리소스는 무엇인가요?

<details>

<summary>정답 및 설명</summary>

**정답:** VolumeSnapshot

**상세 설명:**

Amazon EKS에서 EBS 볼륨 스냅샷을 생성하기 위해 사용하는 Kubernetes API 리소스는 `VolumeSnapshot`입니다. 이 리소스는 Kubernetes Volume Snapshot API의 일부로, CSI(Container Storage Interface) 드라이버와 함께 작동하여 영구 볼륨의 시점 복사본을 생성합니다.

**VolumeSnapshot 사용을 위한 사전 요구 사항:**

1. **EBS CSI 드라이버 설치**: AWS EBS CSI 드라이버가 클러스터에 설치되어 있어야 합니다.
2.  **스냅샷 컨트롤러 설치**: Kubernetes 스냅샷 컨트롤러가 클러스터에 설치되어 있어야 합니다.

    ```bash
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/client/config/crd/snapshot.storage.k8s.io_volumesnapshotclasses.yaml
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/client/config/crd/snapshot.storage.k8s.io_volumesnapshotcontents.yaml
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/client/config/crd/snapshot.storage.k8s.io_volumesnapshots.yaml
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/deploy/kubernetes/snapshot-controller/rbac-snapshot-controller.yaml
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/deploy/kubernetes/snapshot-controller/setup-snapshot-controller.yaml
    ```
3. **VolumeSnapshotClass 생성**: 스냅샷 생성 방법을 정의하는 VolumeSnapshotClass를 생성해야 합니다.

**VolumeSnapshotClass 예시:**

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: ebs-snapshot-class
driver: ebs.csi.aws.com
deletionPolicy: Delete
```

**VolumeSnapshot 생성 예시:**

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

**스냅샷 상태 확인:**

```bash
kubectl get volumesnapshot ebs-volume-snapshot
```

**스냅샷에서 새 PVC 생성:**

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

**VolumeSnapshot의 주요 이점:**

1. **데이터 보호**: 중요한 데이터의 시점 백업 생성
2. **재해 복구**: 데이터 손실 또는 손상 시 복구 지원
3. **환경 복제**: 개발 또는 테스트 환경을 위한 프로덕션 데이터 복제
4. **데이터 마이그레이션**: 한 클러스터에서 다른 클러스터로 데이터 이동

**스냅샷 수명 주기 관리:**

1.  **자동화된 스냅샷 생성**: CronJob을 사용하여 정기적인 스냅샷 생성 자동화

    ```yaml
    apiVersion: batch/v1
    kind: CronJob
    metadata:
      name: volume-snapshot-job
    spec:
      schedule: "0 0 * * *"  # 매일 자정
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
2.  **스냅샷 보존 정책**: 오래된 스냅샷 자동 삭제

    ```yaml
    apiVersion: batch/v1
    kind: CronJob
    metadata:
      name: snapshot-cleanup-job
    spec:
      schedule: "0 1 * * *"  # 매일 오전 1시
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
                  # 30일 이상 된 스냅샷 삭제
                  kubectl get volumesnapshot -o json | jq -r '.items[] | select(.metadata.creationTimestamp | fromnow | contains("days") and (split(" ")[0] | tonumber) > 30) | .metadata.name' | xargs -r kubectl delete volumesnapshot
              restartPolicy: OnFailure
    ```

**모범 사례:**

1. **정기적인 스냅샷**: 중요한 데이터에 대해 정기적인 스냅샷 일정 설정
2. **스냅샷 테스트**: 정기적으로 스냅샷에서 복원을 테스트하여 백업 유효성 확인
3. **태그 지정**: 스냅샷에 적절한 태그를 지정하여 관리 및 비용 추적 용이화
4. **비용 모니터링**: EBS 스냅샷은 추가 비용이 발생하므로 비용 모니터링 및 최적화
5. **암호화**: 민감한 데이터의 경우 암호화된 스냅샷 사용

VolumeSnapshot API를 사용하면 Kubernetes 네이티브 방식으로 EBS 볼륨의 스냅샷을 생성하고 관리할 수 있어, 데이터 보호 및 복구 전략을 효과적으로 구현할 수 있습니다.

</details>

## 실습 문제

### 10. Amazon EKS 클러스터에서 다양한 스토리지 요구 사항을 가진 애플리케이션을 위한 스토리지 솔루션을 설계하세요. 다음 요구 사항을 충족하는 스토리지 클래스와 영구 볼륨 클레임을 작성하세요:

* 데이터베이스용 고성능 블록 스토리지
* 여러 파드에서 공유해야 하는 구성 파일
* AI/ML 워크로드를 위한 고성능 병렬 파일 시스템

<details>

<summary>정답 및 설명</summary>

**정답:**

Amazon EKS 클러스터에서 다양한 스토리지 요구 사항을 충족하기 위한 스토리지 솔루션은 다음과 같습니다:

### 1. 데이터베이스용 고성능 블록 스토리지 (Amazon EBS gp3)

#### StorageClass 정의:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3-db
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  iops: "16000"  # 최대 IOPS
  throughput: "1000"  # 최대 처리량(MB/s)
  encrypted: "true"
allowVolumeExpansion: true
```

#### PersistentVolumeClaim 정의:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: database-data
  namespace: database
spec:
  accessModes:
    - ReadWriteOnce  # EBS는 단일 노드에만 마운트 가능
  storageClassName: ebs-gp3-db
  resources:
    requests:
      storage: 100Gi
```

#### 데이터베이스 파드 예시:

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

**설명:**

* **gp3 볼륨 유형**: 최대 16,000 IOPS와 1,000MB/s 처리량을 제공하여 데이터베이스 워크로드에 적합합니다.
* **WaitForFirstConsumer**: 파드가 스케줄링될 때까지 볼륨 생성을 지연시켜 가용성 영역 문제를 방지합니다.
* **암호화**: 저장 데이터 보안을 위해 EBS 볼륨 암호화를 활성화합니다.
* **볼륨 확장**: 향후 데이터베이스 크기 증가에 대비하여 볼륨 확장을 허용합니다.
* **StatefulSet**: 데이터베이스에 안정적인 네트워크 ID와 영구 스토리지를 제공합니다.

### 2. 여러 파드에서 공유해야 하는 구성 파일 (Amazon EFS)

#### EFS CSI 드라이버 설치:

```bash
helm repo add aws-efs-csi-driver https://kubernetes-sigs.github.io/aws-efs-csi-driver/
helm repo update
helm upgrade -i aws-efs-csi-driver aws-efs-csi-driver/aws-efs-csi-driver \
  --namespace kube-system \
  --set controller.serviceAccount.create=true \
  --set controller.serviceAccount.name=efs-csi-controller-sa
```

#### StorageClass 정의:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0  # 기존 EFS 파일 시스템 ID
  directoryPerms: "700"
```

#### PersistentVolumeClaim 정의:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: config-storage
  namespace: application
spec:
  accessModes:
    - ReadWriteMany  # 여러 파드에서 동시에 읽기/쓰기 가능
  storageClassName: efs-sc
  resources:
    requests:
      storage: 5Gi  # EFS는 자동으로 확장되므로 이 값은 상징적입니다
```

#### 구성 파일을 사용하는 Deployment 예시:

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

**설명:**

* **ReadWriteMany 액세스 모드**: EFS는 여러 파드가 동시에 동일한 볼륨에 읽고 쓸 수 있도록 지원합니다.
* **다중 가용성 영역 지원**: EFS는 여러 가용성 영역에 걸쳐 액세스할 수 있어, 노드 장애에 대한 복원력을 제공합니다.
* **자동 확장**: EFS는 사용량에 따라 자동으로 확장되므로 용량 계획이 필요하지 않습니다.
* **액세스 포인트**: EFS 액세스 포인트를 사용하여 특정 디렉토리에 대한 액세스를 제한할 수 있습니다.

### 3. AI/ML 워크로드를 위한 고성능 병렬 파일 시스템 (Amazon FSx for Lustre)

#### FSx CSI 드라이버 설치:

```bash
helm repo add aws-fsx-csi-driver https://kubernetes-sigs.github.io/aws-fsx-csi-driver/
helm repo update
helm upgrade -i aws-fsx-csi-driver aws-fsx-csi-driver/aws-fsx-csi-driver \
  --namespace kube-system \
  --set controller.serviceAccount.create=true \
  --set controller.serviceAccount.name=fsx-csi-controller-sa
```

#### StorageClass 정의:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre
provisioner: fsx.csi.aws.com
parameters:
  subnetId: subnet-0123456789abcdef0  # FSx 파일 시스템을 생성할 서브넷
  securityGroupIds: sg-0123456789abcdef0  # FSx 파일 시스템에 적용할 보안 그룹
  deploymentType: SCRATCH_2  # 고성능 임시 스토리지
  perUnitStorageThroughput: "200"  # MB/s/TiB
  dataCompressionType: "LZ4"  # 데이터 압축 활성화
  s3ImportPath: s3://ml-training-data-bucket/  # 선택적: S3에서 데이터 가져오기
mountOptions:
  - flock
```

#### PersistentVolumeClaim 정의:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ml-training-data
  namespace: ml-workloads
spec:
  accessModes:
    - ReadWriteMany  # 여러 파드에서 동시에 읽기/쓰기 가능
  storageClassName: fsx-lustre
  resources:
    requests:
      storage: 1200Gi  # FSx for Lustre는 최소 1.2TiB부터 시작
```

#### ML 훈련 작업 예시:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: ml-training
  namespace: ml-workloads
spec:
  parallelism: 4  # 병렬 처리 작업 수
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
            nvidia.com/gpu: 4  # GPU 리소스 요청
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

**설명:**

* **고성능**: FSx for Lustre는 수백 GB/s의 처리량과 수백만 IOPS를 제공하여 AI/ML 워크로드에 적합합니다.
* **병렬 액세스**: 여러 컴퓨팅 노드가 동시에 동일한 데이터에 액세스할 수 있어 분산 훈련에 이상적입니다.
* **S3 통합**: 훈련 데이터를 S3에 저장하고 FSx for Lustre로 가져와 처리할 수 있습니다.
* **데이터 압축**: LZ4 압축을 사용하여 스토리지 효율성을 높입니다.
* **SCRATCH\_2 배포 유형**: 임시 처리를 위한 고성능, 비용 효율적인 옵션입니다.

### 추가 고려 사항 및 모범 사례

#### 1. 백업 및 재해 복구:

```yaml
# EBS 볼륨 스냅샷 생성
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

#### 2. 모니터링 및 알림:

* CloudWatch 경보를 설정하여 스토리지 사용량, 지연 시간, 처리량을 모니터링합니다.
* Prometheus 및 Grafana를 사용하여 스토리지 메트릭을 시각화합니다.

#### 3. 비용 최적화:

* 사용하지 않는 볼륨은 삭제하거나 스냅샷을 생성한 후 삭제합니다.
* 적절한 스토리지 유형과 크기를 선택하여 비용을 최적화합니다.
* FSx for Lustre의 경우, 장기 스토리지가 필요하지 않은 경우 SCRATCH 배포 유형을 사용합니다.

#### 4. 보안:

* 모든 볼륨에 대해 암호화를 활성화합니다.
* 적절한 IAM 권한과 보안 그룹을 구성합니다.
* PodSecurityPolicy 또는 SecurityContext를 사용하여 볼륨 액세스를 제한합니다.

이 설계는 다양한 워크로드 요구 사항을 충족하는 종합적인 스토리지 솔루션을 제공합니다:

* 데이터베이스에는 고성능 EBS gp3 볼륨
* 구성 파일 공유에는 다중 읽기/쓰기 액세스를 지원하는 EFS
* AI/ML 워크로드에는 고성능 병렬 파일 시스템인 FSx for Lustre

각 스토리지 솔루션은 특정 워크로드 요구 사항에 맞게 최적화되어 있으며, 확장성, 성능 및 비용 효율성을 고려하여 설계되었습니다.

</details>

# EKS 스토리지 퀴즈 - Part 2

이 퀴즈는 Amazon EKS의 고급 스토리지 개념, 스토리지 최적화, 백업 및 복구 전략, 그리고 다양한 워크로드에 대한 스토리지 솔루션에 대한 이해를 테스트합니다.

## 객관식 문제

### 1. Amazon EKS에서 StatefulSet을 사용할 때 PersistentVolumeClaim을 생성하는 가장 효과적인 방법은 무엇인가요?

A. 각 파드마다 수동으로 PVC 생성\
B. volumeClaimTemplates 사용\
C. ConfigMap을 사용하여 PVC 정의\
D. 동적 프로비저닝 비활성화

<details>

<summary>정답 및 설명</summary>

**정답: B. volumeClaimTemplates 사용**

**설명:** Amazon EKS에서 StatefulSet을 사용할 때 PersistentVolumeClaim(PVC)을 생성하는 가장 효과적인 방법은 `volumeClaimTemplates`를 사용하는 것입니다. 이 방법을 통해 StatefulSet의 각 파드에 대해 고유한 PVC가 자동으로 생성되며, 파드의 생명주기와 독립적으로 관리됩니다.

**volumeClaimTemplates의 주요 특징:**

1.  **자동 PVC 생성**: StatefulSet의 각 파드에 대해 고유한 PVC가 자동으로 생성됩니다.

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
2. **안정적인 스토리지**: 파드가 재시작되거나 재스케줄링되어도 동일한 PVC가 재사용됩니다.
3. **명명 규칙**: PVC 이름은 `<volumeClaimTemplate-name>-<statefulset-name>-<ordinal>`의 형식으로 생성됩니다. 예: `data-mysql-0`, `data-mysql-1`, `data-mysql-2`
4. **순차적 배포**: StatefulSet은 파드를 순차적으로 생성하고 삭제하므로, 스토리지 작업도 순차적으로 처리됩니다.

**StatefulSet 예시:**

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

**volumeClaimTemplates의 이점:**

1. **자동화**: 수동으로 PVC를 생성하고 관리할 필요가 없습니다.
2. **확장성**: StatefulSet의 replicas를 조정하면 필요한 PVC가 자동으로 생성됩니다.
3. **데이터 지속성**: 파드가 삭제되어도 PVC와 데이터는 유지됩니다.
4. **순서 보장**: 파드와 PVC의 생성 및 삭제 순서가 보장됩니다.

**주의 사항:**

1.  **PVC 삭제 정책**: StatefulSet을 삭제해도 PVC는 자동으로 삭제되지 않습니다. 이는 데이터 손실을 방지하기 위한 설계입니다.

    ```bash
    # StatefulSet 삭제 후 PVC 확인
    kubectl get pvc -l app=mysql

    # 필요한 경우 수동으로 PVC 삭제
    kubectl delete pvc data-mysql-0 data-mysql-1 data-mysql-2
    ```
2. **스토리지 클래스 선택**: 적절한 스토리지 클래스를 선택하여 워크로드 요구 사항을 충족해야 합니다.
   * EBS: 단일 노드 액세스(RWO)
   * EFS: 다중 노드 액세스(RWX)
3.  **볼륨 바인딩 모드**: `WaitForFirstConsumer`를 사용하여 파드가 스케줄링된 가용성 영역에 볼륨이 생성되도록 하는 것이 좋습니다.

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer
    ```

다른 옵션들의 문제점:

* **A. 각 파드마다 수동으로 PVC 생성**: 수동 생성은 오류가 발생하기 쉽고, 확장성이 떨어지며, StatefulSet의 자동화 이점을 활용하지 못합니다.
* **C. ConfigMap을 사용하여 PVC 정의**: ConfigMap은 구성 데이터를 저장하는 데 사용되며, PVC를 생성하는 데 직접 사용할 수 없습니다.
* **D. 동적 프로비저닝 비활성화**: 동적 프로비저닝을 비활성화하면 PVC를 수동으로 생성해야 하므로 관리 오버헤드가 증가합니다.

</details>

### 2. Amazon EKS에서 EBS 볼륨의 성능을 최적화하기 위한 가장 효과적인 방법은 무엇인가요?

A. 모든 EBS 볼륨에 대해 프로비저닝된 IOPS (io1) 유형 사용\
B. 워크로드 요구 사항에 따라 적절한 EBS 볼륨 유형 선택\
C. 모든 EBS 볼륨에 대해 최대 크기 프로비저닝\
D. 모든 파드를 동일한 가용성 영역에 배치

<details>

<summary>정답 및 설명</summary>

**정답: B. 워크로드 요구 사항에 따라 적절한 EBS 볼륨 유형 선택**

**설명:** Amazon EKS에서 EBS 볼륨의 성능을 최적화하기 위한 가장 효과적인 방법은 워크로드 요구 사항에 따라 적절한 EBS 볼륨 유형을 선택하는 것입니다. 각 EBS 볼륨 유형은 서로 다른 성능 특성과 비용 구조를 가지고 있으므로, 워크로드의 특성에 맞는 볼륨 유형을 선택하는 것이 중요합니다.

**주요 EBS 볼륨 유형 및 특성:**

1.  **gp3 (범용 SSD)**:

    * 기본 성능: 3,000 IOPS, 125MB/s 처리량
    * 최대 성능: 16,000 IOPS, 1,000MB/s 처리량
    * 사용 사례: 부팅 볼륨, 개발 및 테스트 환경, 중소 규모 데이터베이스

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
2.  **io1/io2 (프로비저닝된 IOPS SSD)**:

    * 최대 성능: 64,000 IOPS, 1,000MB/s 처리량
    * 사용 사례: I/O 집약적 데이터베이스, 지연 시간에 민감한 워크로드

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
3.  **st1 (처리량 최적화 HDD)**:

    * 최대 성능: 500 IOPS, 500MB/s 처리량
    * 사용 사례: 빅 데이터, 데이터 웨어하우스, 로그 처리

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-st1
    provisioner: ebs.csi.aws.com
    parameters:
      type: st1
    ```
4.  **sc1 (콜드 HDD)**:

    * 최대 성능: 250 IOPS, 250MB/s 처리량
    * 사용 사례: 자주 액세스하지 않는 데이터, 아카이브

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc1
    provisioner: ebs.csi.aws.com
    parameters:
      type: sc1
    ```

**워크로드별 최적 볼륨 유형 선택:**

1.  **데이터베이스 워크로드**:

    * 고성능 필요: io2 또는 고성능 gp3
    * 중간 성능 필요: gp3

    ```yaml
    # 고성능 데이터베이스용 StorageClass
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
2.  **로그 및 스트리밍 워크로드**:

    * 높은 처리량 필요: st1 또는 처리량이 높은 gp3

    ```yaml
    # 로그 처리용 StorageClass
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: log-storage
    provisioner: ebs.csi.aws.com
    parameters:
      type: st1
    volumeBindingMode: WaitForFirstConsumer
    ```
3.  **웹 서버 및 애플리케이션 서버**:

    * 중간 성능 필요: gp3

    ```yaml
    # 웹 서버용 StorageClass
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

**추가 성능 최적화 전략:**

1. **볼륨 크기 최적화**: 일부 볼륨 유형(예: gp2)은 크기에 따라 성능이 확장됩니다.
2. **인스턴스 유형 고려**: EBS 최적화 인스턴스를 사용하여 EBS 볼륨에 대한 전용 대역폭 확보
3.  **RAID 구성**: 여러 EBS 볼륨을 RAID 0으로 구성하여 성능 향상

    ```yaml
    # 파드 내에서 RAID 구성
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
          # 애플리케이션 실행
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
4. **파일 시스템 최적화**: 워크로드에 적합한 파일 시스템 선택 및 최적화
   * XFS: 대용량 파일 및 병렬 I/O에 적합
   * ext4: 일반적인 용도에 적합
5. **모니터링 및 조정**: CloudWatch 메트릭을 모니터링하고 필요에 따라 볼륨 유형 또는 구성 조정

다른 옵션들의 문제점:

* **A. 모든 EBS 볼륨에 대해 프로비저닝된 IOPS (io1) 유형 사용**: 모든 워크로드에 프로비저닝된 IOPS를 사용하는 것은 비용 효율적이지 않으며, 일부 워크로드는 다른 볼륨 유형이 더 적합할 수 있습니다.
* **C. 모든 EBS 볼륨에 대해 최대 크기 프로비저닝**: 필요 이상의 크기로 볼륨을 프로비저닝하면 불필요한 비용이 발생합니다.
* **D. 모든 파드를 동일한 가용성 영역에 배치**: 이는 고가용성을 저해하며, 단일 가용성 영역 장애 시 전체 애플리케이션이 영향을 받을 수 있습니다.

</details>

### 4. Amazon EKS에서 FSx for Lustre를 사용하는 주요 이점은 무엇인가요?

A. 비용 효율성\
B. 단순한 설정\
C. 고성능 병렬 파일 시스템\
D. 기본 EKS 통합

<details>

<summary>정답 및 설명</summary>

**정답: C. 고성능 병렬 파일 시스템**

**설명:** Amazon EKS에서 FSx for Lustre를 사용하는 주요 이점은 고성능 병렬 파일 시스템을 제공한다는 것입니다. FSx for Lustre는 고성능 컴퓨팅(HPC), 기계 학습, 빅 데이터 분석과 같은 컴퓨팅 집약적 워크로드를 위해 설계된 완전 관리형 파일 시스템으로, 수백 GB/s의 처리량, 수백만 IOPS, 그리고 밀리초 미만의 지연 시간을 제공합니다.

**FSx for Lustre의 주요 성능 특성:**

1. **높은 처리량**:
   * 최대 1,000GB/s의 처리량 제공
   * 스토리지 용량 1TiB당 최대 200MB/s의 처리량 (SSD 기반)
   * 대규모 데이터 세트 처리에 적합
2. **낮은 지연 시간**:
   * 밀리초 미만의 지연 시간
   * 지연 시간에 민감한 애플리케이션에 적합
3. **병렬 액세스**:
   * 수천 개의 컴퓨팅 인스턴스에서 동시에 액세스 가능
   * 병렬 처리를 통한 성능 향상
4. **확장성**:
   * 수백 GB/s의 처리량으로 확장 가능
   * 페타바이트 규모의 데이터 세트 지원

**FSx for Lustre의 EKS 통합:**

1.  **CSI 드라이버**:

    ```bash
    # FSx for Lustre CSI 드라이버 설치
    helm repo add aws-fsx-csi-driver https://kubernetes-sigs.github.io/aws-fsx-csi-driver/
    helm repo update
    helm upgrade -i aws-fsx-csi-driver aws-fsx-csi-driver/aws-fsx-csi-driver \
      --namespace kube-system \
      --set controller.serviceAccount.create=true \
      --set controller.serviceAccount.name=fsx-csi-controller-sa
    ```
2.  **StorageClass 구성**:

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
3.  **PersistentVolumeClaim 생성**:

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
          storage: 1200Gi  # 최소 1.2TiB
    ```

**FSx for Lustre가 적합한 워크로드:**

1. **기계 학습 및 딥 러닝**:
   * 대규모 데이터 세트 훈련
   * 분산 훈련 작업
   * 모델 서빙
2. **고성능 컴퓨팅 (HPC)**:
   * 과학 시뮬레이션
   * 날씨 예측
   * 유전체학
3. **빅 데이터 분석**:
   * 대규모 데이터 처리
   * 실시간 분석
   * ETL 작업
4. **미디어 처리**:
   * 비디오 렌더링
   * 이미지 처리
   * 콘텐츠 생성

**S3와의 통합:**

FSx for Lustre는 Amazon S3와 원활하게 통합되어, S3 데이터를 고성능 파일 시스템으로 쉽게 가져오고 처리할 수 있습니다.

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

**배포 유형 옵션:**

1. **SCRATCH\_1**:
   * 임시 스토리지 및 단기 처리
   * 비용 효율적
   * 데이터 복제 없음
2. **SCRATCH\_2**:
   * 임시 스토리지 및 단기 처리
   * 서버 장애 시 데이터 복제
   * SCRATCH\_1보다 더 나은 가용성
3. **PERSISTENT**:
   * 장기 스토리지 및 워크로드
   * 데이터 복제 및 자동 복구
   * 높은 내구성

**성능 최적화 팁:**

1. **적절한 처리량 선택**:
   * SSD 스토리지: 50, 100, 200 MB/s/TiB
   * HDD 스토리지: 12, 40 MB/s/TiB
2. **데이터 압축 활성화**:
   * LZ4 압축을 통한 스토리지 효율성 향상
   * 네트워크 대역폭 사용량 감소
3. **파일 시스템 크기 최적화**:
   * 더 큰 파일 시스템은 더 많은 서버와 더 높은 집계 성능 제공
4.  **마운트 옵션 최적화**:

    ```
    mount -t lustre -o noatime,flock file_system_dns_name@tcp:/mountname /mnt/fsx
    ```

다른 옵션들의 문제점:

* **A. 비용 효율성**: FSx for Lustre는 고성능을 제공하지만, 일반적으로 EBS나 EFS보다 비용이 더 높습니다.
* **B. 단순한 설정**: FSx for Lustre는 고급 구성 옵션이 필요하며, EBS나 EFS보다 설정이 더 복잡합니다.
* **D. 기본 EKS 통합**: FSx for Lustre는 EKS와 기본적으로 통합되지 않으며, CSI 드라이버를 별도로 설치해야 합니다.

</details>

## 단답형 문제

### 6. Amazon EKS에서 EBS 볼륨의 성능을 향상시키기 위해 사용할 수 있는 RAID 구성은 무엇인가요?

<details>

<summary>정답 및 설명</summary>

**정답:** RAID 0 (스트라이핑)

**상세 설명:**

Amazon EKS에서 EBS 볼륨의 성능을 향상시키기 위해 사용할 수 있는 RAID 구성은 RAID 0(스트라이핑)입니다. RAID 0은 여러 EBS 볼륨에 데이터를 분산하여 I/O 성능을 향상시키는 구성입니다.

**RAID 0의 작동 방식:**

RAID 0은 데이터를 여러 디스크에 분산하여 저장하는 방식으로, 각 디스크가 전체 I/O 작업의 일부를 처리하므로 전체 성능이 향상됩니다. 예를 들어, 2개의 EBS 볼륨으로 RAID 0을 구성하면 이론적으로 처리량과 IOPS가 두 배로 증가할 수 있습니다.

**RAID 0의 주요 특징:**

1. **성능 향상**: 여러 볼륨에 걸쳐 I/O 작업을 병렬로 처리하여 처리량과 IOPS를 증가시킵니다.
2. **용량 합산**: 모든 볼륨의 용량이 합산되어 하나의 큰 볼륨처럼 사용됩니다.
3. **내결함성 없음**: 하나의 볼륨이 실패하면 전체 RAID 배열의 데이터가 손실됩니다.

**EKS에서 RAID 0 구성 방법:**

1.  **여러 PVC 생성:**

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
2.  **파드에서 RAID 0 구성:**

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
          # 애플리케이션 실행
          while true; do sleep 30; done
        volumeMounts:
        - name: vol1
          mountPath: /dev/xvdf
        - name: vol2
          mountPath: /dev/xvdg
        - name: raid-mount
          mountPath: /data
        securityContext:
          privileged: true  # RAID 구성에 필요한 권한
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

**RAID 0 성능 최적화 팁:**

1. **볼륨 수**: 일반적으로 2-4개의 볼륨이 최적의 성능을 제공합니다. 볼륨이 너무 많으면 관리 오버헤드가 증가할 수 있습니다.
2. **볼륨 크기**: 모든 볼륨을 동일한 크기로 구성하여 성능을 균등하게 분산합니다.
3. **스트라이프 크기**: 워크로드에 따라 적절한 스트라이프 크기를 선택합니다.
   * 작은 랜덤 I/O: 작은 스트라이프 크기 (예: 4KB)
   * 큰 순차 I/O: 큰 스트라이프 크기 (예: 64KB 또는 128KB)
4. **인스턴스 유형**: EBS 최적화 인스턴스를 사용하여 EBS 볼륨에 대한 전용 대역폭을 확보합니다.

**RAID 0의 사용 사례:**

1. **고성능 데이터베이스**: 높은 IOPS와 처리량이 필요한 데이터베이스 워크로드
2. **빅 데이터 처리**: 대용량 데이터 처리 및 분석 워크로드
3. **미디어 처리**: 비디오 인코딩/디코딩, 렌더링 등 I/O 집약적 작업

**주의 사항:**

1. **데이터 내구성**: RAID 0은 내결함성이 없으므로, 중요한 데이터에는 적절한 백업 전략이 필요합니다.
2. **볼륨 장애**: 하나의 볼륨이 실패하면 전체 데이터가 손실될 수 있으므로, 정기적인 스냅샷을 통한 백업이 중요합니다.
3. **복잡성**: RAID 구성은 관리 복잡성을 증가시키므로, 정말 필요한 경우에만 사용해야 합니다.
4. **비용**: 여러 EBS 볼륨을 사용하므로 스토리지 비용이 증가합니다.

**대안 고려:**

1. **고성능 단일 볼륨**: 단순성을 위해 io2 또는 고성능 gp3 볼륨 사용
2. **인스턴스 스토어**: 임시 데이터의 경우 인스턴스 스토어 볼륨 고려
3. **FSx for Lustre**: 매우 높은 성능이 필요한 경우 병렬 파일 시스템 고려

RAID 0은 EBS 볼륨의 성능을 향상시키는 효과적인 방법이지만, 데이터 내구성과 관리 복잡성을 고려하여 신중하게 사용해야 합니다.

</details>

### 7. Amazon EKS에서 EFS 파일 시스템의 성능을 최적화하기 위해 사용할 수 있는 마운트 옵션 중 읽기 및 쓰기 버퍼 크기를 설정하는 옵션은 무엇인가요?

<details>

<summary>정답 및 설명</summary>

**정답:** rsize와 wsize

**상세 설명:**

Amazon EKS에서 EFS 파일 시스템의 성능을 최적화하기 위해 사용할 수 있는 마운트 옵션 중 읽기 및 쓰기 버퍼 크기를 설정하는 옵션은 `rsize`(읽기 버퍼 크기)와 `wsize`(쓰기 버퍼 크기)입니다. 이러한 옵션은 NFS 클라이언트가 EFS 파일 시스템과 통신할 때 사용하는 데이터 청크의 크기를 결정합니다.

**rsize와 wsize의 역할:**

1. **rsize (읽기 버퍼 크기)**:
   * NFS 클라이언트가 서버에서 읽을 때 사용하는 최대 바이트 수
   * 더 큰 값은 더 적은 수의 네트워크 요청으로 더 많은 데이터를 읽을 수 있음
   * 기본값은 일반적으로 1MB(1048576바이트)
2. **wsize (쓰기 버퍼 크기)**:
   * NFS 클라이언트가 서버에 쓸 때 사용하는 최대 바이트 수
   * 더 큰 값은 더 적은 수의 네트워크 요청으로 더 많은 데이터를 쓸 수 있음
   * 기본값은 일반적으로 1MB(1048576바이트)

**EKS에서 rsize와 wsize 설정:**

1.  **StorageClass에서 설정:**

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
2.  **PersistentVolume에서 설정:**

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

**최적의 값 선택:**

1. **일반적인 권장 값**:
   * rsize=1048576 (1MB)
   * wsize=1048576 (1MB)
2. **워크로드별 최적화**:
   * 대용량 순차 읽기/쓰기: 더 큰 값 (예: 1MB)
   * 작은 랜덤 읽기/쓰기: 더 작은 값 (예: 32KB 또는 64KB)
3. **네트워크 조건 고려**:
   * 안정적인 네트워크: 더 큰 값
   * 불안정한 네트워크: 더 작은 값 (패킷 손실 시 재전송 오버헤드 감소)

**추가 성능 최적화 마운트 옵션:**

1.  **timeo**: 서버 응답 대기 시간(1/10초 단위)

    ```
    timeo=600  # 60초
    ```
2.  **retrans**: 타임아웃 전 재시도 횟수

    ```
    retrans=2
    ```
3.  **noresvport**: 연결 복구 시 새 TCP 포트 사용

    ```
    noresvport
    ```
4.  **noatime**: 파일 액세스 시간 업데이트 비활성화

    ```
    noatime
    ```

**전체 최적화 마운트 옵션 예시:**

```yaml
mountOptions:
  - rsize=1048576
  - wsize=1048576
  - timeo=600
  - retrans=2
  - noresvport
  - noatime
```

**성능 모니터링 및 튜닝:**

1.  **성능 측정**:

    ```bash
    # 읽기 성능 테스트
    dd if=/efs/testfile of=/dev/null bs=1M count=1000

    # 쓰기 성능 테스트
    dd if=/dev/zero of=/efs/testfile bs=1M count=1000
    ```
2. **CloudWatch 메트릭 모니터링**:
   * TotalIOBytes
   * DataReadIOBytes
   * DataWriteIOBytes
   * MetadataIOBytes
3. **점진적 튜닝**:
   * 다양한 rsize/wsize 값으로 테스트
   * 워크로드 패턴에 따라 최적의 값 선택

rsize와 wsize 옵션을 적절하게 설정하면 EFS 파일 시스템의 성능을 크게 향상시킬 수 있으며, 특히 대용량 파일 전송이나 높은 처리량이 필요한 워크로드에서 효과적입니다.

</details>

### 9. Amazon EKS에서 EBS 볼륨을 사용할 때 데이터 내구성을 보장하기 위한 AWS의 SLA(서비스 수준 계약)는 무엇인가요?

<details>

<summary>정답 및 설명</summary>

**정답:** 99.999% (5 9's)

**상세 설명:**

Amazon EKS에서 EBS 볼륨을 사용할 때 데이터 내구성을 보장하기 위한 AWS의 SLA(서비스 수준 계약)는 99.999%(5 9's)입니다. 이는 Amazon EBS가 연간 데이터 손실 가능성이 0.001% 미만임을 의미합니다.

**EBS 내구성의 주요 특징:**

1. **설계 내구성**: Amazon EBS 볼륨은 99.999%의 내구성을 제공하도록 설계되었습니다.
2. **가용성 영역 복제**: EBS 볼륨의 데이터는 단일 가용성 영역 내의 여러 서버에 자동으로 복제됩니다.
3. **연간 장애율(AFR)**: 0.1% - 0.2% 범위의 연간 장애율을 목표로 합니다.

**EBS 볼륨 유형별 내구성:**

모든 EBS 볼륨 유형(gp2, gp3, io1, io2, st1, sc1)은 동일한 99.999%의 내구성 설계를 가지고 있습니다. 그러나 io2 볼륨은 추가적인 내구성 보장을 제공합니다:

* **io2 Block Express**: 99.999% 내구성에 더해 99.999% 가용성 SLA 제공

**데이터 보호 강화 방법:**

1.  **EBS 스냅샷**:

    * 정기적인 스냅샷을 통한 데이터 백업
    * 스냅샷은 S3에 저장되어 99.999999999%(11 9's)의 내구성 제공

    ```yaml
    apiVersion: snapshot.storage.k8s.io/v1
    kind: VolumeSnapshotClass
    metadata:
      name: ebs-snapshot-class
    driver: ebs.csi.aws.com
    deletionPolicy: Retain
    ```
2.  **교차 리전 스냅샷 복사**:

    * 재해 복구를 위한 다른 리전으로 스냅샷 복사

    ```bash
    aws ec2 copy-snapshot \
      --source-region us-west-2 \
      --source-snapshot-id snap-0123456789abcdef0 \
      --destination-region us-east-1 \
      --description "Cross-region backup"
    ```
3.  **자동화된 백업 정책**:

    * Amazon Data Lifecycle Manager 또는 Kubernetes CronJob을 사용한 자동 백업

    ```yaml
    apiVersion: batch/v1
    kind: CronJob
    metadata:
      name: ebs-snapshot-job
    spec:
      schedule: "0 0 * * *"  # 매일 자정
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
                  # PVC에서 볼륨 ID 가져오기
                  VOLUME_ID=$(kubectl get pvc my-pvc -o jsonpath='{.spec.volumeName}' | xargs kubectl get pv -o jsonpath='{.spec.csi.volumeHandle}')
                  # 스냅샷 생성
                  aws ec2 create-snapshot --volume-id $VOLUME_ID --description "Daily backup"
              restartPolicy: OnFailure
    ```

**EBS 볼륨 장애 시나리오 및 복구:**

1. **볼륨 손상**:
   * 증상: I/O 오류, 성능 저하
   * 복구: 최신 스냅샷에서 새 볼륨 생성
2. **가용성 영역 장애**:
   * 증상: 볼륨 접근 불가
   * 복구: 다른 가용성 영역에 스냅샷에서 볼륨 복원
3. **우발적 데이터 삭제**:
   * 복구: 스냅샷에서 특정 시점으로 복원

**EBS 내구성 모범 사례:**

1. **정기적인 스냅샷**:
   * 중요한 데이터에 대해 일일 또는 더 자주 스냅샷 생성
   * 스냅샷 보존 정책 구현
2. **스냅샷 테스트**:
   * 정기적으로 스냅샷에서 복원 테스트
   * 복구 프로세스 문서화 및 연습
3. **다중 리전 전략**:
   * 중요한 데이터의 경우 다른 리전에 스냅샷 복사
   * 재해 복구 계획 수립
4. **모니터링 및 경고**:
   * EBS 볼륨 상태 모니터링
   * CloudWatch 경보 설정

**EBS vs 다른 AWS 스토리지 서비스의 내구성 비교:**

| 서비스            | 내구성                    | 가용성                    |
| -------------- | ---------------------- | ---------------------- |
| Amazon EBS     | 99.999%                | 99.95-99.999% (유형에 따라) |
| Amazon EFS     | 99.999999999% (11 9's) | 99.99%                 |
| Amazon S3      | 99.999999999% (11 9's) | 99.99%                 |
| FSx for Lustre | 99.999%                | 99.95%                 |

Amazon EBS의 99.999% 내구성은 대부분의 워크로드에 충분한 데이터 보호를 제공하지만, 중요한 데이터의 경우 정기적인 스냅샷과 다중 리전 백업 전략을 통해 추가적인 보호 계층을 구현하는 것이 좋습니다.

</details>

## 실습 문제

### 10. Amazon EKS 클러스터에서 데이터베이스 워크로드를 위한 고성능 스토리지 솔루션을 설계하세요. 다음 요구 사항을 충족하는 스토리지 클래스, 영구 볼륨 클레임 및 StatefulSet을 작성하세요:

* 높은 IOPS가 필요한 PostgreSQL 데이터베이스
* 자동 백업 및 복구 기능
* 볼륨 확장 가능성

<details>

<summary>정답 및 설명</summary>

**정답:**

Amazon EKS 클러스터에서 데이터베이스 워크로드를 위한 고성능 스토리지 솔루션을 다음과 같이 설계할 수 있습니다:

### 1. 고성능 StorageClass 정의

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: postgres-io2
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: io2
  iops: "25000"  # 높은 IOPS 제공
  encrypted: "true"
  kmsKeyId: "arn:aws:kms:region:account-id:key/key-id"  # 선택적: KMS 키로 암호화
allowVolumeExpansion: true  # 볼륨 확장 허용
reclaimPolicy: Retain  # PVC 삭제 시 PV 유지
```

### 2. PostgreSQL StatefulSet 정의

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
        fsGroup: 999  # PostgreSQL 그룹 ID
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

### 3. PostgreSQL 서비스 정의

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
  clusterIP: None  # Headless 서비스
```

### 4. 자동 백업을 위한 VolumeSnapshotClass 및 CronJob

```yaml
# VolumeSnapshotClass 정의
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: postgres-snapshot-class
driver: ebs.csi.aws.com
deletionPolicy: Retain
parameters:
  # 스냅샷 암호화 활성화
  encrypted: "true"
  # 스냅샷 태그 추가
  tagSpecification_0_resourceType: "snapshot"
  tagSpecification_0_tags_Purpose: "PostgreSQL Backup"
  tagSpecification_0_tags_Environment: "Production"

# 자동 백업을 위한 CronJob
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: database
spec:
  schedule: "0 1 * * *"  # 매일 오전 1시
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: postgres-backup-sa  # 적절한 권한을 가진 서비스 계정
          containers:
          - name: snapshot-creator
            image: bitnami/kubectl:latest
            command:
            - /bin/bash
            - -c
            - |
              # 현재 날짜 기반 스냅샷 이름 생성
              SNAPSHOT_NAME="postgres-snapshot-$(date +%Y%m%d-%H%M%S)"
              
              # 스냅샷 생성
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
              
              # 30일 이상 된 스냅샷 삭제
              kubectl get volumesnapshot -n database -o json | \
                jq -r '.items[] | select(.metadata.name | startswith("postgres-snapshot-")) | 
                select(.metadata.creationTimestamp | fromnow | contains("days") and (split(" ")[0] | tonumber) > 30) | 
                .metadata.name' | \
                xargs -r kubectl delete volumesnapshot -n database
          restartPolicy: OnFailure
```

### 5. 볼륨 확장 자동화 스크립트

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-volume-monitor
  namespace: database
spec:
  schedule: "0 */6 * * *"  # 6시간마다 실행
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
              # PostgreSQL 파드 이름 가져오기
              POD_NAME=$(kubectl get pods -n database -l app=postgres -o jsonpath='{.items[0].metadata.name}')
              
              # 볼륨 사용량 확인
              USAGE_PERCENT=$(kubectl exec -n database $POD_NAME -- df -h /var/lib/postgresql/data | tail -1 | awk '{print $5}' | sed 's/%//')
              
              # 사용량이 80% 이상이면 볼륨 확장
              if [ $USAGE_PERCENT -ge 80 ]; then
                # 현재 PVC 크기 가져오기
                CURRENT_SIZE=$(kubectl get pvc data-postgres-0 -n database -o jsonpath='{.spec.resources.requests.storage}')
                
                # 현재 크기에서 50% 증가
                NEW_SIZE=$(echo $CURRENT_SIZE | sed 's/Gi//' | awk '{print int($1 * 1.5)}')
                
                # PVC 확장
                kubectl patch pvc data-postgres-0 -n database -p "{\"spec\":{\"resources\":{\"requests\":{\"storage\":\"${NEW_SIZE}Gi\"}}}}"
                
                # 로그 메시지
                echo "$(date): Volume expanded from ${CURRENT_SIZE} to ${NEW_SIZE}Gi due to high usage (${USAGE_PERCENT}%)"
              fi
          restartPolicy: OnFailure
```

### 6. 복구 절차를 위한 Job 템플릿

```yaml
# 스냅샷에서 복구하기 위한 Job 템플릿
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
          # 1. StatefulSet 스케일 다운
          kubectl scale statefulset postgres -n database --replicas=0
          
          # 2. 기존 PVC 삭제 (데이터가 손실되므로 주의)
          kubectl delete pvc data-postgres-0 -n database
          
          # 3. 스냅샷에서 PVC 생성
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
              name: ${SNAPSHOT_NAME}  # 복원할 스냅샷 이름
              kind: VolumeSnapshot
              apiGroup: snapshot.storage.k8s.io
          EOF
          
          # 4. StatefulSet 스케일 업
          kubectl scale statefulset postgres -n database --replicas=1
          
          # 5. 복구 상태 확인
          sleep 60
          kubectl get pods -n database -l app=postgres
      restartPolicy: OnFailure
```

### 7. 모니터링 및 알림 설정

```yaml
# PostgreSQL 메트릭 수집을 위한 ServiceMonitor (Prometheus 가정)
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

### 설계 설명

#### 1. 고성능 스토리지 선택

* **io2 볼륨 유형**: 높은 IOPS가 필요한 데이터베이스 워크로드에 최적화된 EBS 볼륨 유형
* **25,000 IOPS**: 고성능 데이터베이스 작업을 위한 충분한 IOPS 제공
* **암호화**: 저장 데이터 보안을 위한 암호화 활성화

#### 2. StatefulSet 사용의 이점

* **안정적인 네트워크 ID**: 각 파드에 대해 예측 가능한 DNS 이름 제공
* **순차적 배포**: 데이터베이스 파드의 안전한 업데이트 보장
* **볼륨 관리**: volumeClaimTemplates를 통한 자동 PVC 생성 및 관리

#### 3. 자동 백업 전략

* **정기적인 스냅샷**: 매일 자동 스냅샷 생성
* **보존 정책**: 30일 이상 된 스냅샷 자동 삭제
* **태그 지정**: 스냅샷에 태그를 추가하여 관리 용이성 향상

#### 4. 볼륨 확장 자동화

* **사용량 모니터링**: 정기적으로 볼륨 사용량 확인
* **자동 확장**: 사용량이 80% 이상일 때 볼륨 크기 자동 증가
* **allowVolumeExpansion**: StorageClass에서 볼륨 확장 허용

#### 5. 복구 절차

* **스냅샷 기반 복원**: 스냅샷에서 새 PVC 생성
* **단계적 접근**: StatefulSet 스케일 다운, PVC 교체, 스케일 업
* **상태 확인**: 복구 후 데이터베이스 상태 확인

#### 6. 성능 및 안정성 고려 사항

* **리소스 요청 및 제한**: 적절한 CPU 및 메모리 할당
* **상태 확인**: readinessProbe 및 livenessProbe를 통한 데이터베이스 상태 모니터링
* **fsGroup**: 적절한 파일 시스템 권한 설정

#### 7. 보안 고려 사항

* **암호화된 볼륨**: 저장 데이터 보호
* **암호화된 스냅샷**: 백업 데이터 보호
* **Secrets**: 데이터베이스 자격 증명의 안전한 관리

이 설계는 높은 IOPS가 필요한 PostgreSQL 데이터베이스를 위한 고성능 스토리지 솔루션을 제공하며, 자동 백업 및 복구 기능과 볼륨 확장 가능성을 포함합니다. 또한 모니터링 및 알림 설정을 통해 스토리지 관련 문제를 사전에 감지하고 대응할 수 있습니다.

</details>

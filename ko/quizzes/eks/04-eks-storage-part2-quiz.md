# EKS 스토리지 퀴즈 - Part 2

> **마지막 업데이트**: 2026년 9월 11일

스토리지 선택·StatefulSet 클레임·S3/Mountpoint·복제·백업·복구를 점검하는 퀴즈입니다. 예제는 본문에서 준비한 드라이버·class와 전용 네임스페이스를 재사용합니다. 이번 검토에서 클라우드 프로비저닝·DB 복구·성능 벤치마크를 실행하지 않았습니다. 예제를 사용하기 전에 소유권을 확인하고 placeholder를 교체하세요.

## 객관식 문제

### 1. StatefulSet ordinal마다 별도 PVC를 할당하는 방법은 무엇인가요?

- A. ConfigMap에 각 클레임 이름 수동 정의
- B. volumeClaimTemplates 사용
- C. 모든 복제본에 같은 DB 디렉터리 제공
- D. CSI 드라이버 비활성화

<details>
<summary>정답 및 설명</summary>

**정답: B**

`volumeClaimTemplates`는 StatefulSet ordinal마다 `<template>-<statefulset>-<ordinal>` 이름의 클레임을 만듭니다. 재시작 Pod는 스토리지 topology·클레임 수명 조건에 따라 기존 클레임을 재사용합니다. StatefulSet이 복제본 사이에 DB 데이터를 복사하지는 않습니다.

기본 Pod 관리 정책은 `OrderedReady`이며 `Parallel`은 scaling 동작을 바꿉니다. 모든 PVC 생성·삭제 순서가 Pod 순서와 같다는 보장은 없습니다. `persistentVolumeClaimRetentionPolicy`로 PVC 보존을 설정할 수 있고 기본 Retain과 달리 Delete는 scale-down·삭제 시 클레임을 지울 수 있습니다. PV reclaimPolicy는 별도의 백엔드 수명 정책입니다.

다음 세 복제본은 독립적인 영구 marker 파일만 보여주며 **복제 DB가 아닙니다**. Headless Service는 신원을 제공하고 sleep 기반 파일 데모는 예시 Service port의 HTTP 서버를 구현하지 않습니다. 본문의 `ebs-gp3` class를 재사용합니다:

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
        image: busybox:1.37.0
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

Claim template의 레이블이 조회 selector와 일치합니다. 보존 클레임을 일반적인 Pod 정리처럼 삭제하지 마세요. WFFC는 스케줄 조건으로 적합한 볼륨 AZ를 선택하며 EBS 데이터를 모든 AZ에 제공하지 않습니다. RWO는 노드 단위 접근 제약이지 Pod 하나 보장이 아니며 필요하면 지원 RWOP를 사용합니다.

</details>

### 2. EBS 성능 선택의 기준은 무엇인가요?

- A. 항상 io1 선택
- B. 측정한 요구와 볼륨·인스턴스 한도
- C. 항상 최대 용량 프로비저닝
- D. 모든 애플리케이션을 한 AZ에 배치

<details>
<summary>정답 및 설명</summary>

**정답: B**

지연·IOPS·I/O 크기·queue depth·처리량을 측정한 뒤 볼륨과 인스턴스 EBS 한도를 맞춥니다. 개별 볼륨을 크게 프로비저닝해도 인스턴스가 여러 볼륨의 병목이 될 수 있습니다. 파일 시스템·초기화·캐시·애플리케이션 동작도 중요합니다.

| 유형 | 조건이 적용되는 현재 공개 상한 | 주요 고려 사항 |
|---|---|---|
| gp3 | Regional:80,000IOPS /2,000MiB/s; Outposts는 더 낮음 | 기본3,000IOPS /125MiB/s, 독립적인 유료 성능 설정 |
| io1 |64,000IOPS /1,000MiB/s | 인스턴스·크기 제약이 있는 provisioned IOPS |
| io2 Block Express |256,000IOPS /4,000MiB/s | 지원 Nitro·크기·IOPS와 워크로드 요구 |
| st1 |500MiB/s | 순차·버스트 특성을 가진 처리량 중심 HDD |
| sc1 |250MiB/s | 빈도가 낮은 순차 HDD 접근 |

이전 gp3의16,000IOPS/1,000MiB/s는 유효한 예시 설정이지만 현재의 보편적 최댓값은 아닙니다. gp2는 크기에 따라 기본·버스트 성능이 달라지고 gp3는 비율 제약 내에서 성능을 별도로 설정할 수 있습니다. 모든 DB·로그·웹 서버에 자동으로 최적인 유형은 없습니다. 아래 RAID0는 별도 절충안이지 기본 CSI 최적화가 아닙니다.

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

### 3. FSx for Lustre의 핵심 아키텍처 이점은 무엇인가요?

- A. 최저 비용 보장
- B. 드라이버·네트워크 전제 없음
- C. 적합한 워크로드용 병렬 파일 시스템
- D. 모든 PVC의1,000GB/s 보장

<details>
<summary>정답 및 설명</summary>

**정답: C**

FSx for Lustre는 지원 HPC·ML·분석·미디어 워크로드용 관리형 병렬 파일 시스템입니다. 배포 유형·클라이언트/kernel·용량·프로비저닝 처리량·네트워크를 함께 선택합니다. 제품 집계 최댓값이 임의의 작은 PVC 성능을 뜻하지는 않습니다.

SCRATCH_1/SCRATCH_2는 재생성 가능한 임시 데이터용이며 PV 사용만으로 SCRATCH_2에 persistent 서버 복제가 생기지 않습니다. PERSISTENT_1/PERSISTENT_2는 지원 스토리지·처리량 선택지가 다릅니다. 예를 들어 PERSISTENT_2 SSD는125/250/500/1000MB/s/TiB를 지원합니다. 일반적인200MB/s/TiB·1,000GB/s 주장을 모든 파일 시스템에 적용하지 마세요. 이전 집계 주장은 이번 검토에서 검증한 실측이 아닙니다.

본문처럼 관리형 add-on 또는 소유자가 관리하는 호환 드라이버를 준비합니다. 아래는 지원 `s3ImportPath`를 유지한 예제입니다. Import/export는 호환 배포·권한·repository 정책/작업이 필요하며 CSI 생성만으로 자동 S3 양방향 동기화가 되지는 않습니다:

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

동적 파일 시스템 크기는 PVC 요청으로 정하며 범용 StorageClass storageCapacity 필드는 없습니다. 데이터·동시성에 맞춰 압축·striping을 측정합니다. 병렬성·stripe 증가나 LZ4가 항상 빨라지는 것은 아닙니다. 관리형 EKS add-on catalog로 호환성을 선택하며 “EKS 통합이 없다”는 이유로 FSx를 제외하는 것은 부정확합니다.

</details>

### 4. 올바른 Mountpoint CSI 프로비저닝 모델은 무엇인가요?

- A. 동적 s3-sc가 버킷 생성
- B. 기존 버킷에 정적 PV/PVC 바인딩
- C. PVC capacity가 S3 quota 설정
- D. 파일 시스템 PVC가 자동으로 EFS 생성

<details>
<summary>정답 및 설명</summary>

**정답: B**

`s3.csi.aws.com`, 기존 버킷, 양쪽의 빈 storageClassName, 명시적인 claimRef/volumeName과 고유 volumeHandle을 사용합니다. CLI 옵션은 PV mountOptions에 둡니다. Kubernetes capacity 메타데이터는 S3 용량 한도가 아닙니다.

</details>

### 5. authenticationSource: pod는 어느 신원을 사용하나요?

- A. 항상 컨트롤러 IAM 역할
- B. PV에 내장한 정적 키
- C. 애플리케이션 ServiceAccount의 지원 Pod Identity 또는 IRSA
- D. PVC 생성자의 워크스테이션 자격 증명

<details>
<summary>정답 및 설명</summary>

**정답: C**

CSI2.8은 pod-level Pod Identity·IRSA를 지원하며 해당 볼륨의 driver 신원을 무시합니다. 역할·association/신뢰·필요한 agent·버킷/KMS 권한이 존재해야 합니다. ServiceAccount annotation만으로 IAM 역할이 되지는 않습니다.

</details>

### 6. CSI v2의 설정한 emptyDir 캐시는 어디에 있나요?

- A. Mountpoint Pod
- B. 같은 경로를 가진 임의 app Pod emptyDir
- C. 항상 S3 버킷 내부
- D. 자동으로 GPU 인스턴스 NVMe

<details>
<summary>정답 및 설명</summary>

**정답: A**

`cache: emptyDir`·`cacheEmptyDirSizeLimit` 같은 volumeAttributes를 사용합니다. Memory는 tmpfs RAM입니다. Mountpoint metadata TTL은 초, standalone max-cache-size는 MiB, read/write part size는 byte입니다. 버전별 flag는 내장 Mountpoint 바이너리와 맞아야 합니다.

</details>

### 7. 캐시 마운트에 외부 S3 변경이 즉시 보이지 않을 수 있는 이유는 무엇인가요?

- A. S3 목록이 항상 eventual consistency이기 때문
- B. 설정한 TTL 동안 이전/negative entry가 남을 수 있음
- C. 모든 S3 쓰기에 CSI 재시작 필요
- D. PV capacity가 너무 작음

<details>
<summary>정답 및 설명</summary>

**정답: B**

S3는 강한 읽기·목록 일관성을 제공합니다. 선택적인 Mountpoint 캐시는 TTL 만료 전 클라이언트 관측값에 영향을 줍니다. 캐시 동작을 S3 일관성 모델로 혼동하지 마세요. 재현성이 중요하면 불변 데이터셋 접두사나 적절한 캐시 설정을 사용합니다.

</details>

### 8. Native EBS PVC 복제에 맞는 조건은 무엇인가요?

- A. 임의 네임스페이스·AZ
- B. 항상 소스 class 자동 상속
- C. 조정 없이 애플리케이션 일관성 확보
- D. 지원 드라이버·같은 네임스페이스/소스 AZ·호환 모드·충분한 대상 크기

<details>
<summary>정답 및 설명</summary>

**정답: D**

EBS CSI1.66은 실제 native volume-copy 경로를 사용합니다. 일반 PVC dataSource는 같은 네임스페이스가 필요하며 EBS 복사본은 소스 AZ에 남습니다. Class를 명시하고 원본 이상 크기를 요청합니다. 사용 가능 상태가 백그라운드 초기화 완료보다 먼저 올 수 있고 필요한 일관성을 위해 애플리케이션을 quiesce합니다.

</details>

### 9. EBS CSI1.66 동적 Multi-Attach에 맞는 예제는 무엇인가요?

- A. gp3 + RWO + multiAttachEnabled:true
- B. io2 + RWOP + 독립 ext4 writer
- C. io2 + RWX + raw Block와 조정된 애플리케이션 I/O
- D. 여러 AZ에 걸친 모든 EBS 유형

<details>
<summary>정답 및 설명</summary>

**정답: C**

드라이버가 io2 multiwriter block capability를 Multi-Attach로 연결하며 범용 SC multiAttachEnabled 스위치는 없습니다. 적격 Nitro 인스턴스는 볼륨 AZ에 있어야 합니다. 공유 장치가 쓰기 조정·fencing을 자동 제공하지는 않습니다. “확장 불가”라는 일반화와 달리 io2는 서비스·드라이버 조건에 따른 크기·IOPS 변경을 지원합니다.

</details>

### 10. 소유 Velero 백업이 만료되면 CSI snapshot은 어떻게 되나요?

- A. Class가 Retain이어도 Velero가 content를 Delete로 바꾸어 삭제할 수 있음
- B. Retain이 항상 영구 보존
- C. PVC만 삭제
- D. 자동으로 이식 가능한 S3 객체가 됨

<details>
<summary>정답 및 설명</summary>

**정답: A**

Velero1.18은 자신의 CSI snapshot 수명을 관리합니다. 백업 TTL을 명시하고 필요하면 별도 보존·아카이브 절차를 사용합니다. 통합 CSI 지원에도 EnableCSI가 필요하며 백업 메타데이터·native CSI snapshot·복사된 볼륨 데이터는 서로 다릅니다.

</details>

## 단답형 문제

### 11. RAID0가 제공하는 기능과 EKS 설계에서 필요한 고려 사항은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

**정답: 중복성 없는 striping**

RAID0는 블록을 여러 볼륨에 분산하고 사용 가능 용량을 합칩니다. 구성원 하나의 장애로 전체 array를 사용할 수 없게 될 수 있으며 백업·HA 해법이 아닙니다. 같은 볼륨 두 개의 이론적 성능 합산이 약 두 배가 되려면 애플리케이션·파일 시스템·CPU·인스턴스 EBS 한도가 허용해야 합니다. 실측2배 결과가 아닌 이론적 상한입니다.

Filesystem 모드 PVC를 `/volume1`에 마운트한 것은 디렉터리이지 mdadm용 raw disk가 아닙니다. 실제 블록 설계에는 `volumeMode: Block`·`volumeDevices`, 정확한 볼륨 신원, 권한 있는 스토리지 구성 요소와 빈 장치 초기화/기존 array assembly를 구분한 절차가 필요합니다. 애플리케이션 재시작마다 포맷하면 안 됩니다. 같은 노드/AZ 연결·재스케줄·권한·확장·일관된 다중 볼륨 백업/복구를 계획하세요.

따라서 이전 특권 Pod의 무조건적인 mdadm/mkfs 순서는 복사·실행 예제로 적합하지 않습니다. 기존2–4개 볼륨·4/64/128KiB stripe 예시는 실측 검증이 없는 튜닝 후보이지 보편적 최적값이 아닙니다. 복잡성을 추가하기 전에 적절한 단일 gp3/io2, 재생성 가능한 instance store 임시 데이터 또는 FSx와 비교합니다.

</details>

### 12. EFS rsize와 wsize가 제어하는 것은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

**정답: NFS 읽기/쓰기 RPC의 최대 payload 크기**

TCP socket buffer 크기가 아닙니다. AWS는 둘 다1,048,576byte(1MiB)와 지원 NFS/EFS 마운트 경로의 `hard,timeo=600,retrans=2,noresvport`를 권장합니다. timeo 단위는0.1초이므로600은60초입니다. Hard mount의 retrans=2가 두 번 뒤 작업을 포기한다는 뜻은 아닙니다. 워크로드 근거 없이 random I/O·패킷 손실에 작은 값을 처방하지 않습니다. 옵션은 Pod volume이 아닌 StorageClass/PV에 두며 EFS는 nconnect를 지원하지 않습니다.

본문에서 소유자가 준비한 EFS 파일 시스템·access point 설정을 재사용합니다:

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

승인된 쓰기 테스트에서는 검증한 폐기 가능 디렉터리와 고유 파일을 사용합니다. 데이터를 덮어쓸 수 있는 고정 `/efs/testfile`은 사용하지 않습니다. 아래 GNU dd 예제는64MiB를 쓰고 자신의 파일·디렉터리만 정리합니다. 읽기가 클라이언트 캐시에 적중할 수 있으므로 이 시간만으로 cold EFS 처리량을 입증하지는 않습니다:

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

이번 검토에서는 EFS 성능 테스트를 실행하지 않았습니다. 적절한 CloudWatch 통계·기간으로 EFS TotalIOBytes·DataReadIOBytes·DataWriteIOBytes·MetadataIOBytes와 클라이언트/애플리케이션 지연·동시성을 함께 봅니다. Byte 합계는 측정 간격으로 나누기 전까지 처리량 속도가 아닙니다.

</details>

### 13. EBS 가용성 SLA와 내구성 설계는 어떻게 다른가요?

<details>
<summary>정답 및 설명</summary>

**정답: 서로 다른 특성과 조건을 설명합니다**

EBS SLA는 가용성·service credit 계약이며 보편적인99.999% 데이터 내구성 SLA가 아닙니다. Region-level 약정은 여러 AZ의 적격 동시 배포에99.99% 기준을 적용하고 단일 볼륨 약정은99.9% 기준을 사용합니다. 무조건적인 보장으로 취급하지 말고 계약의 정의·예외·credit 조건을 읽어야 합니다.

| 공개 설계 특성 | 볼륨 유형 |
|---|---|
|99.8–99.9% 내구성;0.1–0.2% AFR | gp3/gp2/io1·HDD 유형 |
|99.999% 내구성;0.001% AFR | io2 Block Express |

이 계약에는 별도 io2 “five-nines 가용성 SLA”가 없습니다. AFR·설계 내구성은 특정 애플리케이션이 모든 데이터를 잃을 확률과 같지 않으며 손상·삭제·백업·복구 설계도 중요합니다. EBS 복제는 한 AZ 내부이며 자동 교차 AZ DB 복제가 아닙니다.

필요한 애플리케이션 일관성 백업·독립 복구 지점·복원 테스트·볼륨/앱 상태 모니터링을 사용합니다. AZ 장애에는 접근 가능한 snapshot을 허용된 AZ로 복원하고 삭제된 레코드는 적절한 복구 지점이나 DB PITR로 복구합니다. 블록 snapshot만으로 모든 임의 시각을 복원할 수는 없습니다.

교차 리전 snapshot 복사는 소스·대상·KMS 권한과 완료 확인이 필요한 별도 작업입니다. 다음은 실행한 복구 테스트가 아닌 생성 명령 예제입니다. 먼저 소스 소유권·허용 대상을 확인하고 반환된 SnapshotId를 기록하여 완료를 확인한 뒤 의존하세요:

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

AWS CLI 이미지에 kubectl·Kubernetes/IAM 권한이 자동 포함되지는 않습니다. 미구성 CronJob 대신 적절한 범위의 Velero·Data Lifecycle Manager·AWS Backup 같은 지원 백업 소유자를 사용합니다. 서비스별 실제 스토리지 class·배포의 SLA와 내구성 설계를 각각 비교해야 하며 보편적인 서비스 간 백분율 표는 오해를 줍니다.

</details>

## 실습 문제

### 14. 제약을 명시한 데이터베이스 스토리지·복구 절차를 설계하세요.

<details>
<summary>정답 및 설명</summary>

**정답: 자동 복구 보장이 아닌 검토용 설계**

높은 I/O 요구의 PostgreSQL, 예약 백업·검증한 복구·통제된 확장을 설계합니다. 다음은 실증된 프로덕션 배포가 아닌 **학습용 설계**입니다. 전용 `database` 네임스페이스, 준비한 `postgres-secret/password` Secret, 호환 EBS/snapshot 드라이버와 소유자가 관리하는 Velero를 재사용합니다. 기존 리소스 소유자를 거치지 않고 덮어쓰지 마세요.

#### 스토리지와 데이터베이스

기존25,000IOPS 할당은 io2 예시로 보존하며 충분한지는 측정·인스턴스 한도로 판단합니다. 암호화는 설정된 기본 EBS 키를 사용합니다. Customer managed key를 선택하면 가짜 kmsKeyId 대신 실제 ARN·key policy·드라이버 grant를 준비하세요.

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

Part1에서 확인한 PostgreSQL14.24 이미지 계약인 UID/GID999·마운트한 암호 파일·쓰기 가능한 socket/tmp·PGDATA 하위 디렉터리를 사용합니다. Major14 지원은2026년11월12일 종료되므로 보존한 학습 버전은 신규 프로덕션의 기본 선택이 아닙니다. 적절한 지원 major와 이전 계획을 선택·테스트하세요. StatefulSet 복제본 하나는 HA가 아니며 pg_isready는 연결 준비 확인이지 데이터 무결성·복구 테스트가 아닙니다.

#### 백업과 보존

본문 snapshot-controller 전제와 `ebs-snapshot-class`를 사용합니다. 수동 복구 지점은 생성 전에 DB를 quiesce하거나 지원 DB 백업 프로토콜을 사용합니다. 실제 StatefulSet 클레임은 **data-postgres-0**입니다:

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

복구 가능하다고 판단하기 전에 readyToUse와 restoreSize·content·driver를 확인합니다. Snapshot 암호화는 소스·키 구성을 따르며 VolumeSnapshotClass의 미지원 encrypted/tagSpecification 키로 설정되지 않습니다. 현재 드라이버가 지원하는 별도 snapshot tag 파라미터는 볼륨 class에서 복사하지 말고 해당 릴리스로 확인해야 합니다.

다음은30일 TTL의 일일 Velero schedule을 출력합니다. CSI class 선택·DB 일관성 hook/프로토콜을 확인한 뒤 백업 소유자를 통해 적용합니다. 원래 class가 Retain이어도 Velero TTL이 CSI snapshot을 삭제할 수 있습니다. 실패·누락 백업을 경고하고 주기적으로 복구를 테스트하세요. Schedule만으로 복구 가능성이 입증되지는 않습니다:

```bash
velero schedule create database-daily --schedule="0 1 * * *" \
  --include-namespaces=database --ttl=720h0m0s -o yaml > database-backup-schedule-review.yaml
```

#### 상한이 있는 확장 계획

오래된 지표로6시간마다 무조건50%씩 늘리지 않습니다. 아래 읽기 전용 planner는 Bound 클레임·일치하는 확장 가능 class·진행 중 확장 없음·같은 PVC UID를 식별하는 신선한 지표·유효한 파일 시스템 byte 수치를 요구합니다. 일반적인 Kubernetes decimal/binary quantity를 지원하고 미지원 입력은 거부합니다.80% 사용 시 요청 용량의 최소1.5배를 제안하되 예시500Gi 상한과 UID/resourceVersion/현재 크기 전제 조건을 둡니다. Kubernetes patch를 수행하지 않습니다.

정확한 객체에서 최신 `pvc.json`·`storageclass.json`을 수집합니다. `trusted-metrics.json`은 실제 마운트 파일 시스템의 namespace·pvcName·pvcUID·timezone 포함 observedAt·usedBytes·capacityBytes를 포함해야 합니다. 호출자가 준 UID만으로 지표 출처가 입증되지는 않습니다. 운영자·컨트롤러가 검토한 patch를 적용하기 전에 수집기·마운트 매핑·quota·비용·드라이버 제약을 확인하세요.

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

리소스가 바뀌면 계획을 다시 만들고 실패한 전제 조건을 제거하거나 patch 실패 후 성공 로그를 남기지 않습니다. 승인된 확장 뒤 PVC 조건·실제 파일 시스템 용량을 확인합니다. 이후 생성할 클레임의 StatefulSet template 크기도 지원 소유권 절차로 맞추며 PV capacity를 수정해 완료처럼 보이게 하지 않습니다.

#### 복구 후보

재시도 Job의 첫 복구 단계로 운영 클레임 scale-down·삭제를 실행하지 않습니다. RestoreSize 이상의 별도 후보를 사용하며100Gi 예제는 복구 지점이 그보다 크지 않다는 가정입니다. 원본이 확장되었다면 후보 크기도 조정합니다:

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

필요한 자격 증명·버전의 격리된 호환 PostgreSQL 소비자를 스케줄하고 바인딩·복구 완료 및 애플리케이션 질의·데이터를 검증한 뒤 통제된 전환을 수행합니다. 원본 데이터와 되돌릴 계획을 유지하세요. 새 POSTGRES_PASSWORD 변수 설정으로 복원한 기존 DB의 암호가 재설정되지는 않습니다.

#### 모니터링

PostgreSQL5432는 Prometheus HTTP가 아닌 DB 프로토콜입니다. `app: postgres-exporter` 레이블·이름이 `metrics`인9187 port·적절한 DB 권한을 가진 검토한 postgres-exporter를 준비합니다. 다음 Service·ServiceMonitor는 exporter를 선택하며 설치하지는 않습니다. Prometheus가 해당 ServiceMonitor·네임스페이스를 선택하고 NetworkPolicy·TLS·인증 설정이 배포와 맞아야 합니다:

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

백업 최신성·실패, 파일 시스템 여유, PVC 확장 오류와 측정한 I/O 지연·queue 한도를 경고합니다. 프로덕션 준비를 주장하기 전에 워크로드별 HA·복구·자격 증명 교체·부하 테스트가 필요합니다.

</details>

### 15. 새 클론의 느린 I/O와 S3 데이터셋의 오래된 조회 결과를 어떻게 조사하나요?

<details>
<summary>정답 및 설명</summary>

**정답: 초기화·캐시·애플리케이션 일관성을 구분합니다**

EBS 클론은 실제 드라이버 버전·소스 AZ/크기·copy 상태·초기화 진행·프로비저닝 및 인스턴스 성능을 확인합니다. 새 native copy가 available이어도 백그라운드 초기화 중일 수 있습니다. 0을 쓰거나 빈 볼륨처럼 취급하거나 스냅샷 전용 초기화 가속이 적용된다고 가정하지 않습니다.

Mountpoint는 설치한 CSI/바이너리 버전·PV 옵션·Pod 신원·버킷/접두사·negative entry를 포함한 TTL을 확인합니다. S3 강한 일관성이 설정한 클라이언트 캐시를 우회하지는 않습니다. 해당 버킷 유형이 애플리케이션 연산을 지원하는지도 검증합니다. General purpose와 directory bucket은 append/rename 가정이 다릅니다.

본문의 격리된 클론 marker와 버전별 S3 데이터셋으로 가설을 점검합니다. 과거 벤치마크 수치는 미검증 맥락으로 보존하고 이후 승인된 테스트를 하면 실제 환경과 새 측정값을 기록합니다. 읽기 테스트·snapshot 생성만으로 DB 애플리케이션 일관성이 입증되지는 않습니다.

</details>

## 참고 자료

- [본문과 대응 예제](../../eks/04-eks-storage-part2.md)
- [StatefulSet PVC retention](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [EBS volume types](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volume-types.html)
- [EBS SLA](https://aws.amazon.com/ebs/sla/)
- [EBS native copy](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-copying-volume.html)
- [EFS mount settings](https://docs.aws.amazon.com/efs/latest/ug/mounting-fs-nfs-mount-settings.html)
- [Mountpoint CSI configuration](https://github.com/awslabs/mountpoint-s3-csi-driver/blob/v2.8.0/docs/CONFIGURATION.md)
- [Velero CSI lifecycle](https://velero.io/docs/v1.18/csi/)
- [Prometheus Operator API](https://prometheus-operator.dev/docs/api-reference/api/)
- [PostgreSQL version policy](https://www.postgresql.org/support/versioning/)

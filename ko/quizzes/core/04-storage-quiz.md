# 스토리지 퀴즈

이 퀴즈는 Kubernetes의 스토리지 개념, 볼륨 유형, 영구 볼륨, 스토리지 클래스 등에 대한 이해도를 테스트합니다.

## 객관식 문제

1. 일반 파드가 삭제·재생성되어도 독립된 수명 주기로 애플리케이션 데이터를 유지하는 스토리지 리소스는 무엇인가요?
   - A) ConfigMap
   - B) Secret
   - C) PersistentVolume
   - D) emptyDir
   
<details>

<summary>정답 보기</summary>

**정답: C) PersistentVolume**

**설명:**
PersistentVolume(PV)은 클러스터 관리자가 프로비저닝하거나 스토리지 클래스를 사용하여 동적으로 프로비저닝된 클러스터의 스토리지입니다. PV는 포드가 재시작되거나 삭제되어도 데이터가 유지됩니다. ConfigMap과 Secret은 구성 데이터와 민감한 정보를 저장하는 데 사용되며, emptyDir은 포드가 실행되는 동안에만 존재하는 임시 디렉토리입니다.
</details>

2. Kubernetes에서 PersistentVolume을 요청하기 위해 사용하는 리소스는 무엇인가요?
   - A) VolumeRequest
   - B) PersistentVolumeClaim
   - C) StorageRequest
   - D) VolumeBinding
   
<details>

<summary>정답 보기</summary>

**정답: B) PersistentVolumeClaim**

**설명:**
PersistentVolumeClaim(PVC)은 사용자가 PersistentVolume을 요청하는 방법입니다. PVC는 특정 크기와 접근 모드를 가진 스토리지 요청을 나타냅니다. Kubernetes는 PVC의 요구 사항을 충족하는 PV를 찾아 바인딩합니다.
</details>

3. 다음 중 Kubernetes에서 동적 볼륨 프로비저닝을 위해 사용되는 리소스는 무엇인가요?
   - A) VolumeProvisioner
   - B) StorageClass
   - C) DynamicVolume
   - D) AutoProvisioner
   
<details>

<summary>정답 보기</summary>

**정답: B) StorageClass**

**설명:**
StorageClass는 관리자가 제공하는 스토리지의 "클래스"를 설명하는 방법을 제공합니다. 다른 클래스는 서비스 수준, 백업 정책, 클러스터 관리자가 결정한 임의의 정책에 매핑될 수 있습니다. StorageClass를 사용하면 PVC가 생성될 때 동적으로 PV를 프로비저닝할 수 있습니다.
</details>

4. 일반 파드를 삭제하면 그 파드가 참조하는 별도 생성 PVC도 자동 삭제되나요?
   - A) Delete
   - B) Retain
   - C) Recycle
   - D) 아니요. 별도 생성 PVC는 유지됨
   
<details>

<summary>정답 보기</summary>

**정답: D) 아니요. 별도 생성 PVC는 유지됨**

**설명:**
별도 생성 PVC는 파드 소유가 아니므로 해당 파드가 삭제되어도 유지됩니다. 반면 generic ephemeral volume PVC는 파드 소유이므로 함께 가비지 수집됩니다. StatefulSet의 `persistentVolumeClaimRetentionPolicy`는 세트 삭제·축소 시 템플릿 PVC 삭제를 제어하며 이후 스토리지 정리는 PV 회수 정책을 따릅니다.
</details>

5. 다음 중 PersistentVolume의 접근 모드가 아닌 것은 무엇인가요?
   - A) ReadWriteOnce
   - B) ReadOnlyMany
   - C) ReadWriteMany
   - D) WriteOnlyMany
   
<details>

<summary>정답 보기</summary>

**정답: D) WriteOnlyMany**

**설명:**
Kubernetes에서 PersistentVolume의 접근 모드는 ReadWriteOnce(RWO), ReadOnlyMany(ROX), ReadWriteMany(RWX), ReadWriteOncePod(RWOP, CSI 전용)입니다. WriteOnlyMany는 존재하지 않는 접근 모드입니다. ReadWriteOnce는 단일 노드에 의한 읽기-쓰기 마운트를 허용하고, ReadOnlyMany는 여러 노드에 의한 읽기 전용 마운트를 허용하며, ReadWriteMany는 여러 노드에 의한 읽기-쓰기 마운트를 허용합니다.
</details>

6. PersistentVolume의 Reclaim Policy 중, 볼륨을 삭제하지 않고 리소스만 해제하는 정책은 무엇인가요?
   - A) Delete
   - B) Retain
   - C) Recycle
   - D) Release
   
<details>

<summary>정답 보기</summary>

**정답: B) Retain**

**설명:**
Retain 정책은 PVC가 삭제된 후에도 PV와 그 데이터를 유지합니다. 볼륨은 "Released" 상태로 간주되지만, 다른 클레임에서 사용할 수 없습니다. 관리자가 수동으로 데이터를 정리하고 볼륨을 재사용할 수 있도록 해야 합니다. Delete 정책은 PVC가 삭제될 때 PV와 외부 인프라(예: AWS EBS, GCE PD)를 삭제합니다. Recycle 정책은 더 이상 사용되지 않으며, 동적 프로비저닝을 대신 사용하는 것이 좋습니다.
</details>

7. 다음 중 Kubernetes에서 임시 스토리지를 제공하는 볼륨 유형은 무엇인가요?
   - A) hostPath
   - B) emptyDir
   - C) nfs
   - D) persistentVolumeClaim
   
<details>

<summary>정답 보기</summary>

**정답: B) emptyDir**

**설명:**
emptyDir 볼륨은 포드가 노드에 할당될 때 처음 생성되며, 해당 노드에서 포드가 실행되는 동안에만 존재합니다. 이름에서 알 수 있듯이 볼륨은 처음에 비어 있습니다. 포드 내의 모든 컨테이너는 emptyDir 볼륨의 동일한 파일을 읽고 쓸 수 있지만, 볼륨은 각 컨테이너에서 동일하거나 다른 경로에 마운트될 수 있습니다. 포드가 어떤 이유로든 노드에서 제거되면 emptyDir의 데이터는 영구적으로 삭제됩니다.
</details>

8. 표준 Amazon EBS CSI 드라이버의 프로비저너 이름은 무엇인가요? (EKS Auto Mode 제외)
   - A) ebs.csi.aws.com
   - B) kubernetes.io/gce-pd
   - C) kubernetes.io/azure-disk
   - D) kubernetes.io/nfs
   
<details>

<summary>정답 보기</summary>

**정답: A) ebs.csi.aws.com**

**설명:**
표준 EBS CSI 드라이버는 `ebs.csi.aws.com`을 사용하며 드라이버 설치와 IAM 권한 구성이 필요합니다. 클러스터에 적절한 기본 StorageClass가 자동으로 있다고 가정하면 안 됩니다. EKS Auto Mode는 `ebs.csi.eks.amazonaws.com`을 사용하며 새 예시에 레거시 인트리 프로비저너를 사용하지 않습니다.
</details>

9. 다음 중 StatefulSet에서 사용하는 볼륨 클레임 템플릿의 올바른 필드 이름은 무엇인가요?
   - A) volumeClaimTemplate
   - B) persistentVolumeClaimTemplate
   - C) volumeClaimTemplates
   - D) persistentVolumeClaimTemplates
   
<details>

<summary>정답 보기</summary>

**정답: C) volumeClaimTemplates**

**설명:**
StatefulSet에서는 `volumeClaimTemplates` 필드를 사용하여 각 포드에 대한 PVC를 자동으로 생성합니다. 이 템플릿은 StatefulSet의 각 복제본에 대해 PVC를 생성하는 데 사용됩니다. 생성된 PVC의 이름은 `<볼륨 클레임 템플릿 이름>-<포드 이름>`의 형식을 따릅니다.
</details>

10. Kubernetes에서 CSI(Container Storage Interface)의 주요 목적은 무엇인가요?
    - A) 컨테이너 간 통신을 표준화하기 위함
    - B) 스토리지 드라이버를 Kubernetes 코드 외부에서 개발할 수 있게 하기 위함
    - C) 컨테이너 이미지 저장소 접근을 표준화하기 위함
    - D) 클라우드 제공업체 간 스토리지 마이그레이션을 자동화하기 위함
    
<details>

<summary>정답 보기</summary>

**정답: B) 스토리지 드라이버를 Kubernetes 코드 외부에서 개발할 수 있게 하기 위함**

**설명:**
CSI(Container Storage Interface)는 컨테이너 오케스트레이션 시스템(예: Kubernetes)과 스토리지 공급자 간의 표준 인터페이스를 정의합니다. CSI의 주요 목적은 스토리지 드라이버를 Kubernetes 코드베이스 외부에서 개발, 배포 및 관리할 수 있도록 하는 것입니다. 이를 통해 스토리지 공급자는 Kubernetes 릴리스 주기에 종속되지 않고 자체 플러그인을 개발하고 유지 관리할 수 있습니다.
</details>

## 심화 문제

1. Kubernetes에서 CSI(Container Storage Interface) 드라이버를 사용하여 새로운 스토리지 유형을 통합하는 방법과 그 이점을 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**

**CSI 드라이버 통합 방법:**

1. **CSI 드라이버 배포**: CSI 드라이버는 일반적으로 다음 구성 요소로 구성됩니다:
  - **노드 플러그인 DaemonSet**: 각 노드에서 실행되며 볼륨 마운트/언마운트 작업 수행
  - **컨트롤러 플러그인 Deployment/StatefulSet**: 볼륨 생성/삭제/스냅샷 등의 작업 수행
  - **RBAC 리소스**: 필요한 권한 설정

2. **StorageClass 생성**: CSI 드라이버를 사용하는 StorageClass 정의:
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: csi-storage
provisioner: example.csi.k8s.io  # CSI 드라이버 이름
parameters:
  # 드라이버별 파라미터
  type: ssd
  fsType: ext4
```

3. **CSI 볼륨 스냅샷 지원 설정** (선택 사항):
```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: csi-snapshot-class
driver: example.csi.k8s.io
deletionPolicy: Delete
```

4. **CSI 드라이버 테스트**: PVC 생성 및 포드에 마운트하여 기능 검증

**CSI 사용의 이점:**

1. **독립적인 개발 주기**: 스토리지 공급자는 Kubernetes 릴리스 주기와 독립적으로 드라이버를 개발하고 배포할 수 있습니다.

2. **표준화된 인터페이스**: CSI는 컨테이너 오케스트레이션 시스템과 스토리지 공급자 간의 표준 인터페이스를 제공합니다.

3. **고급 스토리지 기능**: 볼륨 스냅샷, 복제, 크기 조정 등의 고급 기능을 표준화된 방식으로 지원합니다.

4. **보안 향상**: 컨트롤러 IAM/RBAC는 필요한 작업으로 제한하세요. CSI 노드 플러그인은 볼륨 마운트를 위해 특권 호스트 접근이 필요한 경우가 많으므로 별도로 검토해야 합니다.

5. **다양한 스토리지 옵션**: 클라우드 제공업체, 오픈 소스 및 상용 스토리지 솔루션을 쉽게 통합할 수 있습니다.

6. **플러그인 아키텍처**: 필요에 따라 CSI 드라이버를 추가하거나 제거할 수 있습니다.

**실제 구현 예시 (AWS EBS CSI 드라이버):**

```bash
# 공식 문서에 따라 IAM 역할과 EKS EBS CSI 애드온을 먼저 설치합니다.
# 스냅샷 기능에는 스냅샷 CRD와 스냅샷 컨트롤러도 필요합니다.

# StorageClass 생성
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

CSI는 Kubernetes 스토리지 에코시스템의 핵심 부분으로, 다양한 스토리지 솔루션을 통합하고 고급 스토리지 기능을 활용할 수 있게 해줍니다.
</details>

2. StatefulSet과 영구 스토리지를 사용하는 고가용성 DB 클러스터를 설계하세요. Kubernetes의 역할과 DB 복제를 구분하고 백업·복구 요구사항을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

1. 안정적인 파드 식별자, 헤드리스 Service, DB 멤버별 PVC를 사용하고 멤버를 노드·영역에 분산합니다. EBS 볼륨은 한 가용 영역에 남으므로 다른 영역의 복구에는 새 볼륨 복원이나 DB 복제가 필요합니다.
2. DB 오퍼레이터 또는 별도로 검증된 복제 시스템으로 고유 server ID, 초기 동기화, primary 선출, 이전 primary 차단, 복제 자격 증명, 클라이언트 라우팅을 구성합니다. StatefulSet 복제본 3개만으로 HA 데이터베이스가 되지는 않습니다.
3. `ebs.csi.aws.com`, `WaitForFirstConsumer`, 적절한 gp3 `iops`, 의도한 회수 정책으로 암호화 볼륨을 프로비저닝합니다. `Retain`은 클레임 삭제 후 스토리지를 보존하지만 백업이 아니며 모든 삭제 경로를 차단하지 않습니다.
4. ConfigMap은 `${HOSTNAME##*-}` 같은 셸 표현식을 치환하지 않습니다. 인스턴스별 구성은 init 컨테이너로 생성하고 SQL은 MySQL 시작 후 실행하세요. Exec 프로브도 셸 없이 `${VARIABLE}`을 치환하지 않습니다.
5. CSI 스냅샷에는 CRD·컨트롤러와 EBS용 `VolumeSnapshotClass`가 필요합니다. 일관된 복구 시점을 위해 쓰기를 중지하거나 DB 인식 백업을 사용하고 복원 크기·드라이버 호환성을 검증합니다.
6. 논리 백업에는 호환 DB 도구와 업로드 도구를 포함한 이미지를 사용합니다(기본 MySQL 이미지에는 AWS CLI가 없음). 전용 DB 백업 사용자와 제한된 AWS 권한을 사용하고 dump·업로드 실패 시 Job을 실패시킵니다. 성공한 백업은 파드 외부에 보존하고 복원 테스트를 수행하세요. Job 이력 보존은 백업 파일 보존이 아닙니다.
7. 복제 지연, 스토리지 사용량, 백업 경과 시간·실패, 복원 테스트를 모니터링합니다. RPO·RTO를 문서화하고 노드·영역 손실 시 장애 조치를 검증하세요.

[EBS CSI 설치 문서](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)와 본문의 스냅샷·보존 예시를 참고하세요.

</details>

## 결론

이 퀴즈를 통해 Kubernetes의 스토리지 개념에 대한 이해도를 테스트했습니다. 영구 볼륨, 영구 볼륨 클레임, 스토리지 클래스, 볼륨 유형, 접근 모드, 재확보 정책 등의 개념을 다루었습니다. 또한 AWS EKS에서의 스토리지 구성, CSI 드라이버, 볼륨 스냅샷 등의 고급 주제도 살펴보았습니다. 이러한 개념을 이해하고 활용하면 Kubernetes에서 안정적이고 확장 가능한 스토리지 솔루션을 구축할 수 있습니다.

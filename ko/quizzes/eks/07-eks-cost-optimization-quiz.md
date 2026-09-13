# Amazon EKS 비용 최적화 퀴즈

> **마지막 업데이트**: 2026년 9월 12일

예시는 독립적인 구성 대안이며 실제 실행한 배포나 실측 절감 결과가 아닙니다. 기존 리소스 소유 구성에 변경을 병합하고 같은 워크로드에 모든 예시를 차례로 덮어쓰지 않습니다. 자리표시자 이미지와 애플리케이션 소유 hook을 바꾸고 계정·context·리전·컨트롤러 호환성을 확인한 뒤 운영 전에 동작을 검증합니다.

이 퀴즈는 Amazon EKS 클러스터의 비용을 최적화하기 위한 전략, 도구 및 모범 사례에 대한 이해를 테스트합니다.

## 퀴즈 개요
- 컴퓨팅 리소스 최적화
- 스토리지 비용 최적화
- 네트워킹 비용 최적화
- 클러스터 관리 비용 최적화
- 비용 모니터링 및 분석
- 비용 최적화 도구 및 모범 사례

## 객관식 문제

### 1. Amazon EKS에서 컴퓨팅 비용을 최적화하기 위한 가장 효과적인 전략은 무엇인가요?

- A. 항상 가장 큰 인스턴스 유형 사용
- B. 모든 워크로드에 온디맨드 인스턴스만 사용
- C. 스팟 인스턴스, 적절한 인스턴스 크기 조정 및 자동 스케일링 결합
- D. 모든 워크로드를 단일 노드 그룹에 통합
<details>
<summary>정답 및 설명</summary>

**정답: C. 스팟 인스턴스, 적절한 인스턴스 크기 조정 및 자동 스케일링 결합**

**설명:**
Amazon EKS에서 컴퓨팅 비용을 최적화하기 위한 가장 효과적인 전략은 스팟 인스턴스, 적절한 인스턴스 크기 조정 및 자동 스케일링을 결합하는 것입니다. 중단 허용성과 가용 용량이 허용하는 워크로드에 Spot을 사용하고 SLO에 대조해 절감 결과를 검증합니다. 이 조합이나 광고된 최대 할인율이 비용 절감과 성능 유지를 보장하지는 않습니다.

**주요 컴퓨팅 최적화 전략:**

1. **스팟 인스턴스 활용**:
   - 온디맨드 대비 최대 90% 비용 절감
   - 내결함성 있는 워크로드에 적합
   - 중단 처리 메커니즘 구현

2. **적절한 인스턴스 크기 조정**:
   - 실제 리소스 사용량에 기반한 인스턴스 선택
   - 과도하게 프로비저닝된 리소스 제거
   - 리소스 요청 및 제한 최적화

3. **자동 스케일링 구현**:
   - Cluster Autoscaler 또는 Karpenter를 통한 노드 수준 스케일링
   - Horizontal Pod Autoscaler를 통한 파드 수준 스케일링
   - 수요에 따른 리소스 조정

NodePool/EC2NodeClass에는 설치된 호환 Karpenter 컨트롤러/CRD, 범위가 제한된 컨트롤러 IAM, 노드 역할, 검색 대상 리소스, 중단 처리 큐가 필요합니다. 현재 호환성 표에서 EKS 1.36은 Karpenter >=1.13이 필요합니다. `al2023@latest`는 변하는 선택자이므로 실제 AMI를 검토하고 통제된 변경에는 검증한 별칭/AMI를 고정합니다. 인스턴스 목록과 용량 limits는 예시이며 금액 상한이 아닙니다. 관리형 노드 그룹은 자체 중단 경로를 처리하며 Karpenter 노드에 두 번째 처리기를 중복 적용하지 않습니다.

HPA에는 resource metrics와 requests가 필요하고 CPU/메모리 목표 중 가장 큰 희망 복제본 수를 선택합니다. 아래 VPA는 분모를 변경하지 않고 권고만 제공하도록 **Off**입니다. `Auto`는 deprecated되어 `Recreate` 같은 명시적 모드로 대체하며, CPU/메모리 자동 변경은 HPA와 조율해야 합니다. preStop hook도 종료 유예 시간을 소비하며 Spot 기한이나 cleanup 성공을 보장하지 않습니다.

**구현 방법:**

1. **스팟 인스턴스를 사용한 노드 그룹 생성**:
   ```bash
   # eksctl을 사용한 스팟 인스턴스 노드 그룹 생성
   eksctl create nodegroup \
     --cluster my-cluster \
     --region us-west-2 \
     --managed \
     --name spot-ng \
     --node-type m5.large \
     --nodes-min 2 \
     --nodes-max 10 \
     --spot
   ```

2. **Karpenter 배포 및 구성**:
   ```yaml
   # Karpenter NodePool
   apiVersion: karpenter.sh/v1
   kind: NodePool
   metadata:
     name: default
   spec:
     template:
       spec:
         requirements:
           - key: "karpenter.sh/capacity-type"
             operator: In
             values: ["spot"]
           - key: "kubernetes.io/arch"
             operator: In
             values: ["amd64"]
           - key: "kubernetes.io/os"
             operator: In
             values: ["linux"]
           - key: "node.kubernetes.io/instance-type"
             operator: In
             values: ["m5.large", "m5a.large", "m5d.large", "m5ad.large", "m4.large"]
         nodeClassRef:
           group: karpenter.k8s.aws
           kind: EC2NodeClass
           name: default
     limits:
       cpu: 1000
       memory: 1000Gi
     disruption:
       consolidationPolicy: WhenEmpty
       consolidateAfter: 30s
   ---
   # Karpenter NodeClass
   apiVersion: karpenter.k8s.aws/v1
   kind: EC2NodeClass
   metadata:
     name: default
   spec:
     amiSelectorTerms:
       - alias: al2023@latest
     role: KarpenterNodeRole
     subnetSelectorTerms:
       - tags:
           karpenter.sh/discovery: my-cluster
     securityGroupSelectorTerms:
       - tags:
           karpenter.sh/discovery: my-cluster
     tags:
       karpenter.sh/discovery: my-cluster
   ```

3. **Horizontal Pod Autoscaler 구성**:
   ```yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: web-app
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: web-app
     minReplicas: 2
     maxReplicas: 10
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70
     - type: Resource
       resource:
         name: memory
         target:
           type: Utilization
           averageUtilization: 80
   ```

4. **Vertical Pod Autoscaler 구성**:
   ```yaml
   apiVersion: autoscaling.k8s.io/v1
   kind: VerticalPodAutoscaler
   metadata:
     name: web-app-vpa
   spec:
     targetRef:
       apiVersion: "apps/v1"
       kind: Deployment
       name: web-app
     updatePolicy:
       updateMode: "Off"
     resourcePolicy:
       containerPolicies:
       - containerName: '*'
         minAllowed:
           cpu: 50m
           memory: 100Mi
         maxAllowed:
           cpu: 1
           memory: 1Gi
         controlledResources: ["cpu", "memory"]
   ```

**워크로드 유형별 최적화 전략:**

1. **상태 비저장(Stateless) 애플리케이션**:
   - 스팟 인스턴스 우선 사용
   - 수평적 확장 구현
   - 다중 가용 영역 배포

2. **상태 저장(Stateful) 애플리케이션**:
   - 온디맨드 인스턴스와 스팟 인스턴스 혼합
   - 적절한 인스턴스 유형 선택
   - 스토리지 성능과 비용 균형

3. **배치 작업**:
   - 스팟 인스턴스 최대한 활용
   - 작업 재시도 메커니즘 구현
   - 작업 기한/가용 용량에 맞춰 예약하며 일반 온디맨드 시간대 할인을 가정하지 않음

**모범 사례:**

1. **리소스 요청 및 제한 최적화**:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
   spec:
     replicas: 3
     template:
       spec:
         containers:
         - name: web-app
           image: web-app:1.0
           resources:
             requests:
               cpu: 100m
               memory: 256Mi
             limits:
               cpu: 500m
               memory: 512Mi
       metadata:
         labels:
           app: web-app
     selector:
       matchLabels:
         app: web-app
   ```

2. **노드 선호도 및 파드 분배 최적화**:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
   spec:
     replicas: 3
     template:
       spec:
         affinity:
           nodeAffinity:
             preferredDuringSchedulingIgnoredDuringExecution:
             - weight: 1
               preference:
                 matchExpressions:
                 - key: node.kubernetes.io/instance-type
                   operator: In
                   values:
                   - m5.large
                   - m5a.large
           podAntiAffinity:
             preferredDuringSchedulingIgnoredDuringExecution:
             - weight: 100
               podAffinityTerm:
                 labelSelector:
                   matchExpressions:
                   - key: app
                     operator: In
                     values:
                     - web-app
                 topologyKey: kubernetes.io/hostname
         containers:
         - name: web-app
           image: registry.example.com/team/web-app:REVIEWED_TAG
       metadata:
         labels:
           app: web-app
     selector:
       matchLabels:
         app: web-app
   ```

3. **스팟 인스턴스 중단 처리**:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
   spec:
     replicas: 3
     template:
       spec:
         terminationGracePeriodSeconds: 60
         containers:
         - name: web-app
           image: web-app:1.0
           lifecycle:
             preStop:
               exec:
                 command:
                 - /bin/sh
                 - -c
                 - sleep 10; /app/cleanup.sh
       metadata:
         labels:
           app: web-app
     selector:
       matchLabels:
         app: web-app
   ```

**기존 구성에 적용하는 추가 예시:**

1. **비용 효율적인 노드 그룹 구성**:
   기존 클러스터에 노드 그룹을 추가하는 구성 fragment입니다. 소유자의 private subnet, 노드 IAM 정책, 기존 그룹/ASG 태그를 확인한 뒤 사용하며, 클러스터 전체를 새로 만드는 독립 예제로 취급하지 않습니다.
   ```yaml
   apiVersion: eksctl.io/v1alpha5
   kind: ClusterConfig
   metadata:
     name: my-cluster
     region: us-west-2
   managedNodeGroups:
   - name: system-ng
     instanceType: m5.large
     desiredCapacity: 2
     minSize: 2
     maxSize: 4
     labels:
       workload-type: system
     privateNetworking: true
   - name: app-spot-ng
     instanceTypes:
     - m5.large
     - m5a.large
     - m5d.large
     - m4.large
     spot: true
     desiredCapacity: 3
     minSize: 1
     maxSize: 10
     labels:
       workload-type: application
     privateNetworking: true
   ```

2. **Terraform을 사용한 비용 최적화 인프라 구성**:
   ```hcl
   # 스팟 인스턴스 노드 그룹
   resource "aws_eks_node_group" "spot" {
     cluster_name    = aws_eks_cluster.main.name
     node_group_name = "spot-ng"
     node_role_arn   = aws_iam_role.node_role.arn
     subnet_ids      = var.private_subnet_ids

     capacity_type  = "SPOT"
     instance_types = ["m5.large", "m5a.large", "m5d.large", "m4.large"]

     scaling_config {
       desired_size = 3
       min_size     = 1
       max_size     = 10
     }

     labels = {
       "workload-type" = "application"
     }

     tags = {
       Team        = "platform"
       Environment = "development"
     }
   }

   # Cluster Autoscaler IAM 정책
   resource "aws_iam_policy" "cluster_autoscaler" {
     name        = "EKSClusterAutoscalerPolicy"
     description = "Policy for Cluster Autoscaler"

     policy = jsonencode({
       Version = "2012-10-17",
       Statement = [
         {
           Effect = "Allow",
           Action = [
             "autoscaling:DescribeAutoScalingGroups",
             "autoscaling:DescribeAutoScalingInstances",
             "autoscaling:DescribeLaunchConfigurations",
             "autoscaling:DescribeTags",
             "autoscaling:DescribeScalingActivities",
             "ec2:DescribeImages",
             "ec2:DescribeInstanceTypes",
             "ec2:GetInstanceTypesFromInstanceRequirements",
             "eks:DescribeNodegroup",
             "ec2:DescribeLaunchTemplateVersions"
           ],
           Resource = "*"
         },
         {
           Effect = "Allow",
           Action = [
             "autoscaling:SetDesiredCapacity",
             "autoscaling:TerminateInstanceInAutoScalingGroup"
           ],
           Resource = "*",
           Condition = {
             StringEquals = {
               "aws:ResourceTag/k8s.io/cluster-autoscaler/enabled"                      = "true",
               "aws:ResourceTag/k8s.io/cluster-autoscaler/${aws_eks_cluster.main.name}" = "owned"
             }
           }
         }
       ]
     })
   }
   ```

추가 예시는 기존 Terraform 모듈의 fragment로 `aws_eks_cluster.main`, 노드 역할/정책, private subnet 변수와 provider가 이미 정의되었다고 가정하며 독립 실행 파일이 아닙니다. autoscaler와 `desired_size` 소유권도 조율합니다. 노드 그룹 태그는 실제 ASG 검색 태그를 대체하지 않으므로 ASG와 기존 태그 소유자를 조회해 확인합니다. 정책은 노드 역할이 아닌 전용 컨트롤러 identity에 연결합니다. 쓰기 동작 두 개는 enabled/cluster 태그 조건으로 제한하고 조회 권한과 분리합니다. 전체 IAM/검색 설정은 [공식 EKS 가이드](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)를 따릅니다. system/application 레이블만으로 격리되지는 않으며 bootstrap 컨트롤러가 실행되기 전에 유일한 온디맨드 노드를 taint하지 않습니다.

다른 옵션들의 문제점:
- **A. 항상 가장 큰 인스턴스 유형 사용**: 이는 과도한 프로비저닝으로 이어져 불필요한 비용이 발생하며, 워크로드 요구 사항에 맞지 않을 수 있습니다.
- **B. 모든 워크로드에 온디맨드 인스턴스만 사용**: 온디맨드 인스턴스는 스팟 인스턴스보다 비용이 더 높으며, 많은 워크로드가 스팟 인스턴스에서 효과적으로 실행될 수 있습니다.
- **D. 모든 워크로드를 단일 노드 그룹에 통합**: 다양한 워크로드 요구 사항을 충족하기 어렵고, 리소스 격리가 부족하며, 비용 할당 및 최적화가 어려워집니다.
</details>
### 2. Amazon EKS에서 스토리지 비용을 최적화하기 위한 가장 효과적인 접근 방식은 무엇인가요?

- A. 모든 워크로드에 대해 가장 저렴한 스토리지 유형 사용
- B. 모든 데이터를 S3로 마이그레이션
- C. 워크로드 요구 사항에 맞는 스토리지 유형 선택 및 수명 주기 관리 구현
- D. 모든 볼륨 크기를 최소화
<details>
<summary>정답 및 설명</summary>

**정답: C. 워크로드 요구 사항에 맞는 스토리지 유형 선택 및 수명 주기 관리 구현**

**설명:**
Amazon EKS에서 스토리지 비용을 최적화하기 위한 가장 효과적인 접근 방식은 워크로드 요구 사항에 맞는 스토리지 유형을 선택하고 수명 주기 관리를 구현하는 것입니다. 이 접근 방식은 성능 요구 사항을 충족하면서 비용을 최소화하고, 데이터의 가치와 액세스 패턴에 따라 적절한 스토리지 계층을 활용합니다.

**주요 스토리지 최적화 전략:**

1. **워크로드에 적합한 스토리지 유형 선택**:
   - 고성능 필요: io2, gp3 (EBS)
   - 공유 액세스 필요: EFS
   - 대용량 데이터 처리: FSx for Lustre
   - 아카이브 데이터: S3, S3 Glacier

2. **스토리지 수명 주기 관리**:
   - 자주 액세스하는 데이터: 고성능 스토리지
   - 가끔 액세스하는 데이터: 표준 스토리지
   - 거의 액세스하지 않는 데이터: 저비용 아카이브 스토리지

3. **효율적인 볼륨 관리**:
   - 적절한 볼륨 크기 설정
   - 사용하지 않는 볼륨 식별 및 제거
   - 스냅샷 수명 주기 관리

StorageClass 예시에는 설치된 CSI 드라이버와 올바른 IAM/KMS·토폴로지 설정이 필요합니다. `WaitForFirstConsumer`는 EBS 프로비저닝을 스케줄링과 맞추며 `Retain`으로 남은 볼륨은 소유자가 처리할 때까지 과금됩니다. 바인딩된 PVC의 클래스 변경이나 제자리 축소는 불가능합니다. 스냅샷/복원 또는 지원되는 볼륨 유형 변경은 소유자가 검토한 이전 절차와 복원 테스트가 필요합니다. Auto Mode의 EBS provisioner는 다르므로 표준 CSI 예시에 조용히 대입하지 않습니다.

`create-file-system`에는 `--lifecycle-policies` 옵션이 없습니다. 아래처럼 기존 파일 시스템의 전체 원하는 정책 배열을 보존하며 `put-lifecycle-configuration`을 사용합니다. S3 전환도 최소 기간/크기, 요청 비용, 버전 관리, 복구 지연을 검토하고 lifecycle 전체 교체 시 관련 없는 규칙을 보존해야 합니다.

**구현 방법:**

1. **EBS 볼륨 최적화**:
   ```yaml
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: ebs-gp3
   provisioner: ebs.csi.aws.com
   parameters:
     type: gp3
     iops: '3000'
     throughput: '125'
     encrypted: 'true'
   allowVolumeExpansion: true
   volumeBindingMode: WaitForFirstConsumer
   reclaimPolicy: Retain
   ```

2. **EFS 수명 주기 관리**:
   ```bash
   set -euo pipefail
   : "${AWS_REGION:?Set the reviewed Region}"
   : "${FILE_SYSTEM_ID:?Set the existing reviewed EFS filesystem ID}"
   aws efs describe-lifecycle-configuration --region "$AWS_REGION" \
     --file-system-id "$FILE_SYSTEM_ID" --query LifecyclePolicies --output json \
     > efs-lifecycle-policies.json
   # Edit the exported array; an IA entry is {"TransitionToIA":"AFTER_30_DAYS"}.
   # Preserve required Archive/return-to-primary entries before submitting the whole policy.
   aws efs put-lifecycle-configuration --region "$AWS_REGION" \
     --file-system-id "$FILE_SYSTEM_ID" \
     --lifecycle-policies file://efs-lifecycle-policies.json
   ```

3. **S3 수명 주기 정책**:
   ```json
   {
     "Rules": [
       {
         "ID": "Move to IA after 30 days, Glacier after 90 days",
         "Status": "Enabled",
         "Transitions": [
           {
             "Days": 30,
             "StorageClass": "STANDARD_IA"
           },
           {
             "Days": 90,
             "StorageClass": "GLACIER"
           }
         ],
         "Expiration": {
           "Days": 365
         },
         "Filter": {
           "Prefix": "eks-backups/"
         }
       }
     ]
   }
   ```

4. **EBS 스냅샷 수명 주기 관리**:
   ```yaml
   apiVersion: snapshot.storage.k8s.io/v1
   kind: VolumeSnapshotClass
   metadata:
     name: ebs-snapshot
   driver: ebs.csi.aws.com
   deletionPolicy: Delete
   ```

아래 스냅샷 일정은 소유자가 기존 `team-a/database-data` PVC, 표준 EBS CSI 드라이버, snapshot controller/CRD, `ebs-snapshot` 클래스를 확인할 때까지 suspend 상태입니다. 마운트한 template은 고정 이름 충돌을 피하도록 `generateName`을 사용합니다. Role은 이 namespace의 스냅샷 생성을 허용하며 source PVC 필드까지 제한하지는 않습니다. 애플리케이션 일관성/quiescing과 복원 검증은 별도 책임입니다. Job 성공은 API 생성 성공이며 snapshot 준비 완료가 아니므로 `readyToUse`와 오류를 별도로 감시합니다. Job 이력 제한은 VolumeSnapshot/EBS snapshot을 만료시키지 않습니다. 일정 활성화 전에 보존·복구 소유자를 정해야 하며 `deletionPolicy: Delete`이면 Kubernetes snapshot 삭제 시 원본 EBS snapshot도 삭제됩니다.

   ```yaml
   apiVersion: v1
   kind: ServiceAccount
   metadata:
     name: snapshot-creator
     namespace: team-a
   ---
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     name: snapshot-creator
     namespace: team-a
   rules:
   - apiGroups: ["snapshot.storage.k8s.io"]
     resources: ["volumesnapshots"]
     verbs: ["create"]
   ---
   apiVersion: rbac.authorization.k8s.io/v1
   kind: RoleBinding
   metadata:
     name: snapshot-creator
     namespace: team-a
   subjects:
   - kind: ServiceAccount
     name: snapshot-creator
     namespace: team-a
   roleRef:
     apiGroup: rbac.authorization.k8s.io
     kind: Role
     name: snapshot-creator
   ---
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: snapshot-templates
     namespace: team-a
   data:
     snapshot.yaml: |
       apiVersion: snapshot.storage.k8s.io/v1
       kind: VolumeSnapshot
       metadata:
         generateName: database-data-
         namespace: team-a
       spec:
         volumeSnapshotClassName: ebs-snapshot
         source:
           persistentVolumeClaimName: database-data
   ---
   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: volume-snapshot
     namespace: team-a
   spec:
     suspend: true
     schedule: "0 1 * * *"
     timeZone: Etc/UTC
     concurrencyPolicy: Forbid
     startingDeadlineSeconds: 1800
     successfulJobsHistoryLimit: 1
     failedJobsHistoryLimit: 2
     jobTemplate:
       spec:
         backoffLimit: 0
         activeDeadlineSeconds: 120
         template:
           spec:
             serviceAccountName: snapshot-creator
             restartPolicy: Never
             securityContext:
               runAsNonRoot: true
               runAsUser: 65532
               seccompProfile:
                 type: RuntimeDefault
             containers:
             - name: snapshot-creator
               image: registry.k8s.io/kubectl:v1.36.2
               command: ["kubectl"]
               args: ["create", "-f", "/snapshots/snapshot.yaml", "--namespace=team-a"]
               env:
               - name: HOME
                 value: /tmp
               securityContext:
                 allowPrivilegeEscalation: false
                 readOnlyRootFilesystem: true
                 capabilities:
                   drop: ["ALL"]
               resources:
                 requests:
                   cpu: 10m
                   memory: 32Mi
                 limits:
                   memory: 128Mi
               volumeMounts:
               - name: snapshots
                 mountPath: /snapshots
                 readOnly: true
               - name: tmp
                 mountPath: /tmp
             volumes:
             - name: snapshots
               configMap:
                 name: snapshot-templates
             - name: tmp
               emptyDir: {}
   ```

**워크로드 유형별 스토리지 최적화:**

1. **데이터베이스 워크로드**:
   - 성능 요구 사항: 높은 IOPS 및 처리량
   - 권장 스토리지: EBS io2 또는 gp3
   - 최적화 전략: 적절한 IOPS 및 처리량 설정, 정기적인 스냅샷

2. **웹 애플리케이션**:
   - 성능 요구 사항: 중간 IOPS, 공유 액세스
   - 권장 스토리지: EFS 또는 EBS gp3
   - 최적화 전략: 캐싱, 정적 콘텐츠 분리

3. **로그 및 분석 데이터**:
   - 성능 요구 사항: 높은 처리량, 대용량
   - 권장 스토리지: S3, EFS
   - 최적화 전략: 수명 주기 정책, 압축

4. **AI/ML 워크로드**:
   - 성능 요구 사항: 매우 높은 처리량
   - 권장 스토리지: FSx for Lustre, EBS gp3
   - 최적화 전략: 임시 데이터와 영구 데이터 분리

**모범 사례:**

1. **데이터 계층화 구현**:
   ```yaml
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: hot-data
     namespace: team-a
   spec:
     accessModes:
     - ReadWriteOnce
     storageClassName: ebs-gp3
     resources:
       requests:
         storage: 10Gi
   ---
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: warm-data
     namespace: team-a
   spec:
     accessModes:
     - ReadWriteMany
     storageClassName: efs-standard
     resources:
       requests:
         storage: 100Gi
   ```

2. **스토리지 사용량 모니터링 및 최적화**:
   ```bash
   set -euo pipefail
   : "${KUBE_CONTEXT:?Select the reviewed cluster context}"
   : "${KUBE_NAMESPACE:?Select the reviewed namespace}"
   kubectl --context "$KUBE_CONTEXT" --namespace "$KUBE_NAMESPACE" \
     get pvc --chunk-size=500 -o json > pvcs.json
   kubectl --context "$KUBE_CONTEXT" --namespace "$KUBE_NAMESPACE" \
     get pods --chunk-size=500 -o json > pods.json
   python3 unreferenced_pvcs.py
   ```

3. **데이터 압축 및 중복 제거**:
   - 로그 및 백업 데이터 압축
   - 중복 데이터 제거 기술 활용
   - 효율적인 데이터 형식 사용

4. **비용 할당 및 태깅**:
   ```yaml
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: database-data
     labels:
       app: database
       environment: production
       cost-center: cc-123
     namespace: team-a
   spec:
     accessModes:
     - ReadWriteOnce
     storageClassName: ebs-io2
     resources:
       requests:
         storage: 100Gi
   ```

**추가 구성과 읽기 전용 분석 예시:**

1. **스토리지 비용 최적화 아키텍처**:
   ```
   +-------------------+    +-------------------+    +-------------------+
   |                   |    |                   |    |                   |
   |  Hot Data         |    |  Warm Data        |    |  Cold Data        |
   |  (EBS gp3)        |    |  (EFS)            |    |  (S3)             |
   +-------------------+    +-------------------+    +-------------------+
           |                        |                        |
           v                        v                        v
   +-------------------+    +-------------------+    +-------------------+
   |                   |    |                   |    |                   |
   |  Active           |    |  Recent           |    |  Archive          |
   |  Applications     |    |  Applications     |    |  Data             |
   |                   |    |                   |    |                   |
   +-------------------+    +-------------------+    +-------------------+
                                     |
                                     v
                            +-------------------+
                            |                   |
                            |  Lifecycle        |
                            |  Management       |
                            |                   |
                            +-------------------+
   ```

2. **Terraform을 사용한 스토리지 최적화 인프라 구성**:
   ```hcl
   # EBS gp3 스토리지 클래스
   resource "kubernetes_storage_class_v1" "ebs_gp3" {
     metadata {
       name = "ebs-gp3"
     }
     storage_provisioner = "ebs.csi.aws.com"
     parameters = {
       type       = "gp3"
       iops       = "3000"
       throughput = "125"
       encrypted  = "true"
     }
     allow_volume_expansion = true
     volume_binding_mode    = "WaitForFirstConsumer"
     reclaim_policy         = "Retain"
   }

   # EFS 파일 시스템
   resource "aws_efs_file_system" "eks_efs" {
     creation_token = "eks-efs"
     encrypted      = true

     lifecycle_policy {
       transition_to_ia = "AFTER_30_DAYS"
     }

     tags = {
       Name = "eks-efs"
     }
   }

   # S3 버킷 및 수명 주기 정책
   resource "aws_s3_bucket" "eks_data" {
     bucket = "eks-data-${data.aws_caller_identity.current.account_id}"

     tags = {
       Name = "eks-data"
     }
   }

   resource "aws_s3_bucket_lifecycle_configuration" "eks_data_lifecycle" {
     bucket = aws_s3_bucket.eks_data.id

     rule {
       id     = "archive-rule"
       status = "Enabled"

       filter {
         prefix = "eks-backups/"
       }

       transition {
         days          = 30
         storage_class = "STANDARD_IA"
       }

       transition {
         days          = 90
         storage_class = "GLACIER"
       }

       expiration {
         days = 365
       }
     }
   }
   ```

3. **스토리지 비용 모니터링 및 최적화 스크립트**:
   ```python
   import json
   from pathlib import Path


   def unreferenced_claims(claims, pods):
       referenced = set()
       for pod in pods["items"]:
           namespace = pod["metadata"]["namespace"]
           for volume in pod.get("spec", {}).get("volumes") or []:
               claim = volume.get("persistentVolumeClaim")
               if claim:
                   referenced.add((namespace, claim["claimName"]))
       result = []
       for claim in claims["items"]:
           metadata = claim["metadata"]
           identity = (metadata["namespace"], metadata["name"])
           if claim.get("status", {}).get("phase") != "Bound" or identity in referenced:
               continue
           spec = claim.get("spec", {})
           result.append({
               "namespace": identity[0],
               "name": identity[1],
               "storageClass": spec.get("storageClassName"),
               "requested": ((spec.get("resources") or {}).get("requests") or {}).get("storage"),
               "meaning": "not referenced by the supplied current Pod snapshot; review required",
           })
       return result


   if __name__ == "__main__":
       claims = json.loads(Path("pvcs.json").read_text())
       pods = json.loads(Path("pods.json").read_text())
       print(json.dumps(unreferenced_claims(claims, pods), indent=2))
   ```

위 Python을 `unreferenced_pvcs.py`로 저장하고 앞의 읽기 전용 명령과 사용합니다. 현재 Pod snapshot에서 참조되지 않는 Bound PVC 후보만 출력합니다. `(namespace, name)`으로 비교하고 PVC가 아닌 볼륨의 `persistentVolumeClaim: null`도 처리합니다. 기본 Kubernetes에는 `pv_used` 어노테이션이 없으며 이를 미사용 판정으로 사용하지 않습니다. 서로 다른 시점의 목록, 축소된 StatefulSet, 대기 작업, 컨트롤러 template, 백업/복구 요구는 이 목록으로 확인되지 않습니다. 삭제를 자동화하지 마세요. EBS `available`도 미사용을 의미하지 않으며, [EKS06 비용 문항](06-eks-monitoring-logging-quiz.md)의 계정·태그 범위 조회를 사용합니다.

hot/warm/cold 도식은 접근 패턴별 선택 예시이며 EBS→EFS→S3 자동 이전 파이프라인이 아닙니다. `efs-standard`/`ebs-io2` 클래스는 별도로 준비해야 하고, EFS PVC의 `100Gi` 요청은 파일 시스템 사용량 quota나 선결제 용량을 설정하지 않습니다. PVC 레이블도 AWS 청구 태그로 자동 전달되지 않습니다. Terraform은 기존 provider·caller identity 등을 요구하는 구성 fragment로, 기존 StorageClass 소유권과 파일 시스템 mount target/접근 권한, 백업·보존 요구를 별도 구성해야 합니다.

다른 옵션들의 문제점:
- **A. 모든 워크로드에 대해 가장 저렴한 스토리지 유형 사용**: 가장 저렴한 스토리지는 성능 요구 사항을 충족하지 못할 수 있으며, 이로 인해 애플리케이션 성능 저하 및 비즈니스 영향이 발생할 수 있습니다.
- **B. 모든 데이터를 S3로 마이그레이션**: S3는 일부 데이터 유형에 적합하지만, 지연 시간에 민감한 워크로드나 블록 스토리지가 필요한 애플리케이션에는 적합하지 않습니다.
- **D. 모든 볼륨 크기를 최소화**: 볼륨 크기를 과도하게 최소화하면 공간 부족 문제가 발생할 수 있으며, 일부 볼륨 유형(예: gp2)은 크기에 따라 성능이 결정됩니다.
</details>
### 3. Amazon EKS에서 네트워킹 비용을 최적화하기 위한 가장 효과적인 전략은 무엇인가요?

- A. 모든 트래픽에 대해 가장 비싼 네트워크 대역폭 사용
- B. 모든 서비스를 단일 가용 영역에 배치
- C. 트래픽 패턴 최적화, 데이터 전송 비용 최소화 및 VPC 엔드포인트 활용
- D. 모든 네트워크 트래픽 차단
<details>
<summary>정답 및 설명</summary>

**정답: C. 트래픽 패턴 최적화, 데이터 전송 비용 최소화 및 VPC 엔드포인트 활용**

**설명:**
Amazon EKS에서 네트워킹 비용을 최적화하기 위한 가장 효과적인 전략은 트래픽 패턴을 최적화하고, 데이터 전송 비용을 최소화하며, VPC 엔드포인트를 활용하는 것입니다. 이 접근 방식은 네트워크 트래픽의 효율성을 높이고, AWS 네트워크 비용 모델을 고려하여 불필요한 비용을 줄입니다.

**주요 네트워킹 비용 최적화 전략:**

1. **트래픽 패턴 최적화**:
   - 가용 영역 간 트래픽 최소화
   - 리전 간 트래픽 최소화
   - 로컬리티 인식 라우팅 구현

2. **데이터 전송 비용 최소화**:
   - 압축 및 효율적인 데이터 형식 사용
   - 캐싱 전략 구현
   - 불필요한 데이터 전송 제거

3. **VPC 엔드포인트 활용**:
   - AWS 서비스에 대한 프라이빗 연결
   - 인터넷 게이트웨이 우회
   - 데이터 전송 비용 절감

Topology spread는 배치를 제어하며 Service 트래픽의 엔드포인트를 선택하지 않습니다. `spec.topologyKeys`는 제거되었습니다. 예시는 Kubernetes 1.35+에서 stable인 `trafficDistribution: PreferSameZone`을 사용하며 fallback이 가능하므로 AZ 간 트래픽 0을 보장하지 않습니다. 실제 proxy/CNI 동작과 가용성 제약을 검증합니다.

S3/DynamoDB gateway endpoint와 interface endpoint의 가격 모델은 다릅니다. ECR 이미지 pull에는 `ecr.api`, `ecr.dkr`, S3 연결과 private DNS, 대상 노드/Pod에서 endpoint로의 TCP 443 보안 그룹 규칙이 필요합니다. CLI는 interface endpoint 하나를 보여주며 아래 Terraform처럼 DKR 상대 endpoint도 준비합니다. endpoint policy와 실제 리전 트래픽/비용을 검토해야 하며 프라이빗 연결이 무료를 의미하지는 않습니다.

**구현 방법:**

1. **가용 영역 인식 파드 배치**:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
   spec:
     replicas: 6
     template:
       spec:
         topologySpreadConstraints:
         - maxSkew: 1
           topologyKey: topology.kubernetes.io/zone
           whenUnsatisfiable: DoNotSchedule
           labelSelector:
             matchLabels:
               app: web-app
         containers:
         - name: web-app
           image: registry.example.com/team/web-app:REVIEWED_TAG
       metadata:
         labels:
           app: web-app
     selector:
       matchLabels:
         app: web-app
   ```
   Private Pod in AZ-a
     -> S3/DynamoDB gateway endpoint route -> regional service
     -> private DNS -> interface endpoint ENI:443 -> ECR API/DKR
        (ECR layer downloads also require S3 access)
     -> zonal NAT in AZ-a public subnet -> internet gateway -> external API

   Locality-aware Service/mesh routing selects workload endpoints.
   It does not replace VPC routes, endpoint permissions, or NAT.
   ```yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: web-app
   spec:
     selector:
       app: web-app
     ports:
     - port: 80
       targetPort: 8080
     trafficDistribution: PreferSameZone
   ```
   Private Pod in AZ-a
     -> S3/DynamoDB gateway endpoint route -> regional service
     -> private DNS -> interface endpoint ENI:443 -> ECR API/DKR
        (ECR layer downloads also require S3 access)
     -> zonal NAT in AZ-a public subnet -> internet gateway -> external API

   Locality-aware Service/mesh routing selects workload endpoints.
   It does not replace VPC routes, endpoint permissions, or NAT.
   ```bash
   # S3 VPC 엔드포인트 생성
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-12345678 \
     --service-name com.amazonaws.us-west-2.s3 \
     --route-table-ids rtb-12345678

   # DynamoDB VPC 엔드포인트 생성
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-12345678 \
     --service-name com.amazonaws.us-west-2.dynamodb \
     --route-table-ids rtb-12345678

   # ECR API VPC 엔드포인트 생성
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-12345678 \
     --service-name com.amazonaws.us-west-2.ecr.api \
     --vpc-endpoint-type Interface \
     --subnet-ids subnet-12345678 subnet-87654321 \
     --security-group-ids sg-12345678 \
     --private-dns-enabled
   ```
   Private Pod in AZ-a
     -> S3/DynamoDB gateway endpoint route -> regional service
     -> private DNS -> interface endpoint ENI:443 -> ECR API/DKR
        (ECR layer downloads also require S3 access)
     -> zonal NAT in AZ-a public subnet -> internet gateway -> external API

   Locality-aware Service/mesh routing selects workload endpoints.
   It does not replace VPC routes, endpoint permissions, or NAT.
   ```yaml
   apiVersion: networking.istio.io/v1
   kind: DestinationRule
   metadata:
     name: web-app
   spec:
     host: web-app
     trafficPolicy:
       loadBalancer:
         simple: LEAST_REQUEST
         localityLbSetting:
           enabled: true
       outlierDetection:
         consecutive5xxErrors: 5
         interval: 5s
         baseEjectionTime: 30s
   ```
   Private Pod in AZ-a
     -> S3/DynamoDB gateway endpoint route -> regional service
     -> private DNS -> interface endpoint ENI:443 -> ECR API/DKR
        (ECR layer downloads also require S3 access)
     -> zonal NAT in AZ-a public subnet -> internet gateway -> external API

   Locality-aware Service/mesh routing selects workload endpoints.
   It does not replace VPC routes, endpoint permissions, or NAT.
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: database
   spec:
     replicas: 3
     template:
       spec:
         affinity:
           podAffinity:
             preferredDuringSchedulingIgnoredDuringExecution:
             - weight: 100
               podAffinityTerm:
                 labelSelector:
                   matchExpressions:
                   - key: app
                     operator: In
                     values:
                     - api-server
                 topologyKey: topology.kubernetes.io/zone
         containers:
         - name: database
           image: registry.example.com/team/database:REVIEWED_TAG
       metadata:
         labels:
           app: database
     selector:
       matchLabels:
         app: database
   ```
   Private Pod in AZ-a
     -> S3/DynamoDB gateway endpoint route -> regional service
     -> private DNS -> interface endpoint ENI:443 -> ECR API/DKR
        (ECR layer downloads also require S3 access)
     -> zonal NAT in AZ-a public subnet -> internet gateway -> external API

   Locality-aware Service/mesh routing selects workload endpoints.
   It does not replace VPC routes, endpoint permissions, or NAT.
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: api-network-policy
   spec:
     podSelector:
       matchLabels:
         app: api-server
     policyTypes:
     - Ingress
     - Egress
     ingress:
     - from:
       - podSelector:
           matchLabels:
             app: frontend
       ports:
       - protocol: TCP
         port: 8080
     egress:
     - to:
       - podSelector:
           matchLabels:
             app: database
       ports:
       - protocol: TCP
         port: 5432
     - to:
       - namespaceSelector:
           matchLabels:
             kubernetes.io/metadata.name: kube-system
         podSelector:
           matchLabels:
             k8s-app: kube-dns
       ports:
       - protocol: UDP
         port: 53
       - protocol: TCP
         port: 53
   ```
   Private Pod in AZ-a
     -> S3/DynamoDB gateway endpoint route -> regional service
     -> private DNS -> interface endpoint ENI:443 -> ECR API/DKR
        (ECR layer downloads also require S3 access)
     -> zonal NAT in AZ-a public subnet -> internet gateway -> external API

   Locality-aware Service/mesh routing selects workload endpoints.
   It does not replace VPC routes, endpoint permissions, or NAT.
   ```yaml
   apiVersion: networking.istio.io/v1
   kind: VirtualService
   metadata:
     name: api-service
   spec:
     hosts:
     - api-service
     http:
     - match:
       - headers:
           end-user:
             exact: premium-user
       route:
       - destination:
           host: api-service
           subset: premium
     - route:
       - destination:
           host: api-service
           subset: v1
         weight: 90
       - destination:
           host: api-service
           subset: v2
         weight: 10
   ---
   apiVersion: networking.istio.io/v1
   kind: DestinationRule
   metadata:
     name: api-service-subsets
   spec:
     host: api-service
     subsets:
     - name: v1
       labels:
         version: v1
     - name: v2
       labels:
         version: v2
     - name: premium
       labels:
         version: premium
   ```
   Private Pod in AZ-a
     -> S3/DynamoDB gateway endpoint route -> regional service
     -> private DNS -> interface endpoint ENI:443 -> ECR API/DKR
        (ECR layer downloads also require S3 access)
     -> zonal NAT in AZ-a public subnet -> internet gateway -> external API

   Locality-aware Service/mesh routing selects workload endpoints.
   It does not replace VPC routes, endpoint permissions, or NAT.
   ```yaml
   apiVersion: networking.istio.io/v1alpha3
   kind: EnvoyFilter
   metadata:
     name: compression-filter
     namespace: istio-system
   spec:
     workloadSelector:
       labels:
         istio: ingressgateway
     configPatches:
     - applyTo: HTTP_FILTER
       match:
         context: GATEWAY
         listener:
           filterChain:
             filter:
               name: envoy.filters.network.http_connection_manager
               subFilter:
                 name: envoy.filters.http.router
       patch:
         operation: INSERT_BEFORE
         value:
           name: envoy.filters.http.compressor
           typed_config:
             '@type': type.googleapis.com/envoy.extensions.filters.http.compressor.v3.Compressor
             response_direction_config:
               common_config:
                 min_content_length: 100
                 content_type:
                 - application/json
                 - text/html
             compressor_library:
               name: gzip
               typed_config:
                 '@type': type.googleapis.com/envoy.extensions.compression.gzip.compressor.v3.Gzip
                 memory_level: 3
                 window_bits: 10
                 compression_level: BEST_COMPRESSION
                 compression_strategy: DEFAULT_STRATEGY
   ```
   Private Pod in AZ-a
     -> S3/DynamoDB gateway endpoint route -> regional service
     -> private DNS -> interface endpoint ENI:443 -> ECR API/DKR
        (ECR layer downloads also require S3 access)
     -> zonal NAT in AZ-a public subnet -> internet gateway -> external API

   Locality-aware Service/mesh routing selects workload endpoints.
   It does not replace VPC routes, endpoint permissions, or NAT.
   ```
   +-------------------+    +-------------------+    +-------------------+
   |                   |    |                   |    |                   |
   |  VPC Endpoint     |    |  NAT Gateway      |    |  Internet         |
   |  (AWS Services)   |    |  (External APIs)  |    |  Gateway          |
   +-------------------+    +-------------------+    +-------------------+
           |                        |                        |
           v                        v                        v
   +---------------------------------------------------------------+
   |                                                               |
   |                  EKS Cluster VPC                              |
   |                                                               |
   +---------------------------------------------------------------+
           |                        |                        |
           v                        v                        v
   +-------------------+    +-------------------+    +-------------------+
   |                   |    |                   |    |                   |
   |  AZ-a             |    |  AZ-b             |    |  AZ-c             |
   |  Workloads        |    |  Workloads        |    |  Workloads        |
   |                   |    |                   |    |                   |
   +-------------------+    +-------------------+    +-------------------+
           |                        |                        |
           v                        v                        v
   +---------------------------------------------------------------+
   |                                                               |
   |                  Service Mesh                                 |
   |                  (Locality-aware routing)                     |
   |                                                               |
   +---------------------------------------------------------------+
   ```
   Private Pod in AZ-a
     -> S3/DynamoDB gateway endpoint route -> regional service
     -> private DNS -> interface endpoint ENI:443 -> ECR API/DKR
        (ECR layer downloads also require S3 access)
     -> zonal NAT in AZ-a public subnet -> internet gateway -> external API

   Locality-aware Service/mesh routing selects workload endpoints.
   It does not replace VPC routes, endpoint permissions, or NAT.
   ```hcl
   # VPC 엔드포인트 구성
   resource "aws_vpc_endpoint" "s3" {
     vpc_id            = aws_vpc.main.id
     service_name      = "com.amazonaws.${var.region}.s3"
     route_table_ids   = [aws_route_table.private.id]
     vpc_endpoint_type = "Gateway"

     tags = {
       Name = "s3-endpoint"
     }
   }

   resource "aws_vpc_endpoint" "dynamodb" {
     vpc_id            = aws_vpc.main.id
     service_name      = "com.amazonaws.${var.region}.dynamodb"
     route_table_ids   = [aws_route_table.private.id]
     vpc_endpoint_type = "Gateway"

     tags = {
       Name = "dynamodb-endpoint"
     }
   }

   # 인터페이스 VPC 엔드포인트
   resource "aws_vpc_endpoint" "ecr_api" {
     vpc_id              = aws_vpc.main.id
     service_name        = "com.amazonaws.${var.region}.ecr.api"
     vpc_endpoint_type   = "Interface"
     subnet_ids          = aws_subnet.private[*].id
     security_group_ids  = [aws_security_group.vpc_endpoints.id]
     private_dns_enabled = true

     tags = {
       Name = "ecr-api-endpoint"
     }
   }

   resource "aws_vpc_endpoint" "ecr_dkr" {
     vpc_id              = aws_vpc.main.id
     service_name        = "com.amazonaws.${var.region}.ecr.dkr"
     vpc_endpoint_type   = "Interface"
     subnet_ids          = aws_subnet.private[*].id
     security_group_ids  = [aws_security_group.vpc_endpoints.id]
     private_dns_enabled = true

     tags = {
       Name = "ecr-dkr-endpoint"
     }
   }
   ```
   Private Pod in AZ-a
     -> S3/DynamoDB gateway endpoint route -> regional service
     -> private DNS -> interface endpoint ENI:443 -> ECR API/DKR
        (ECR layer downloads also require S3 access)
     -> zonal NAT in AZ-a public subnet -> internet gateway -> external API

   Locality-aware Service/mesh routing selects workload endpoints.
   It does not replace VPC routes, endpoint permissions, or NAT.
   ```python
   import json
   import os
   import re
   from datetime import date
   from decimal import Decimal
   from pathlib import Path

   import boto3
   from botocore.config import Config


   def network_cost_rows(client, start, end, linked_account, usage_types):
       for value in [start, end]:
           if date.fromisoformat(value).isoformat() != value:
               raise ValueError("Use YYYY-MM-DD dates")
       if start >= end:
           raise ValueError("Start must precede exclusive End")
       if not re.fullmatch(r"[0-9]{12}", linked_account):
           raise ValueError("A reviewed linked account ID is required")
       if not isinstance(usage_types, list) or not usage_types or any(
           not isinstance(value, str) or not value.strip() for value in usage_types
       ):
           raise ValueError("Provide exact reviewed USAGE_TYPE values")
       request = {
           "TimePeriod": {"Start": start, "End": end},
           "Granularity": "DAILY",
           "Metrics": ["UnblendedCost"],
           "GroupBy": [
               {"Type": "DIMENSION", "Key": "SERVICE"},
               {"Type": "DIMENSION", "Key": "USAGE_TYPE"},
           ],
           "Filter": {
               "And": [
                   {"Dimensions": {"Key": "LINKED_ACCOUNT", "Values": [linked_account],
                                   "MatchOptions": ["EQUALS"]}},
                   {"Dimensions": {"Key": "USAGE_TYPE", "Values": usage_types,
                                   "MatchOptions": ["EQUALS"]}},
               ]
           },
       }
       rows = []
       seen_tokens = set()
       for _ in range(100):
           response = client.get_cost_and_usage(**request)
           for period in response["ResultsByTime"]:
               for group in period["Groups"]:
                   service, usage_type = group["Keys"]
                   metric = group["Metrics"]["UnblendedCost"]
                   amount = Decimal(metric["Amount"])
                   if not amount.is_finite() or not metric["Unit"]:
                       raise ValueError("Invalid monetary amount/unit")
                   rows.append({
                       "start": period["TimePeriod"]["Start"],
                       "endExclusive": period["TimePeriod"]["End"],
                       "service": service,
                       "usageType": usage_type,
                       "amount": str(amount),
                       "unit": metric["Unit"],
                       "estimated": period.get("Estimated"),
                   })
           token = response.get("NextPageToken")
           if not token:
               return rows
           if token in seen_tokens:
               raise RuntimeError("Repeated pagination token")
           seen_tokens.add(token)
           request["NextPageToken"] = token
       raise RuntimeError("Page limit exceeded; narrow the query")


   def main():
       expected_caller = os.environ["EXPECTED_CALLER_ACCOUNT"]
       if not re.fullmatch(r"[0-9]{12}", expected_caller):
           raise ValueError("Set the reviewed calling account")
       # Commercial AWS partition example; verify the billing endpoint/permissions.
       session = boto3.Session(region_name="us-east-1")
       config = Config(connect_timeout=5, read_timeout=30,
                       retries={"mode": "standard", "total_max_attempts": 4})
       identity = session.client("sts", config=config).get_caller_identity()
       if identity["Account"] != expected_caller:
           raise RuntimeError("Calling account mismatch")
       usage_types = json.loads(Path("reviewed-usage-types.json").read_text())
       rows = network_cost_rows(
           session.client("ce", config=config),
           os.environ["START_DATE"], os.environ["END_DATE"],
           os.environ["LINKED_ACCOUNT_ID"], usage_types,
       )
       print(json.dumps({"basis": "UnblendedCost", "rows": rows}, indent=2))


   if __name__ == "__main__":
       main()
   ```

추가 NetworkPolicy는 같은 namespace의 frontend→API→database와 표준 CoreDNS Deployment 경로를 예시로 허용합니다. 다른 필수 의존성은 별도 허용해야 하고 CNI의 NetworkPolicy 집행을 확인합니다. Auto Mode의 node-local DNS나 다른 DNS 경로에는 해당 환경의 허용 규칙이 필요합니다. namespace/pod selector를 실제 관리 레이블과 대조하세요.

VirtualService는 첫 일치 규칙을 사용하므로 premium match를 catch-all보다 먼저 두고 대응 DestinationRule subset을 정의했습니다. 실제 Pod에 version 레이블이 있어야 합니다. 클라이언트가 보낸 end-user 헤더는 인증된 자격을 증명하지 않으므로 권한 검증은 서버에서 수행합니다. EnvoyFilter는 실제 ingress gateway 레이블/namespace와 설치된 Istio·Envoy 버전을 확인한 후에만 사용합니다. gateway의 HTTP 응답 압축 예시이며, outbound sidecar에 필터를 넣는 것만으로 업로드 요청을 압축하는 것은 아닙니다. 기존 content_length/content_type 필드는 제거된 것이 아니라 deprecated입니다. 이 예시는 response_direction_config의 common_config를 사용하며 CPU·지연·보안 및 프로토콜별 영향을 테스트해야 합니다.

Terraform은 VPC·private subnet·endpoint SG·라우팅 테이블이 이미 정의된 모듈 fragment입니다. 기존 VPC 소유자가 NAT와 route association을 관리해야 하며 단일 zonal NAT를 모든 AZ에 공유하는 구성을 기본 고가용성/절감 해법으로 적용하지 않습니다. cross-AZ 전송과 장애 의존성을 비교하거나 별도의 regional NAT 모델을 평가합니다.

Python을 network_costs.py로 저장하고 EXPECTED_CALLER_ACCOUNT, LINKED_ACCOUNT_ID, START_DATE, END_DATE를 명시합니다. reviewed-usage-types.json은 Cost Explorer/GetDimensionValues에서 선택한 실제 USAGE_TYPE 문자열의 JSON 배열이어야 합니다. 이 코드는 상업 AWS 파티션의 us-east-1 청구 endpoint를 사용하며 읽기 권한과 호출 계정을 확인해야 합니다. API 쿼리 비용이 발생할 수 있습니다. GetCostAndUsage Dimensions는 CONTAINS를 지원하지 않으므로 정확한 값과 EQUALS를 사용합니다. NextPageToken을 끝까지 처리하고 금액은 Decimal, 단위와 estimated 상태는 원본대로 보존합니다. 빈 결과/실패를 전체 네트워크 비용 0으로 해석하지 않습니다. 특정 EKS 클러스터에 귀속하려면 계정 수준 결과에 검증된 태그/리소스 매핑이 추가로 필요합니다. 선택한 usage type만 포함하므로 전체 비용을 보장하지 않으며 서비스명/Regional/Region 같은 부분 문자열로 인터넷·AZ·리전 비용을 추정 분류하지 않습니다. 기간은 UTC이며 End는 미포함이고 조회 가능 이력과 최종 정산 상태를 확인합니다. 원래의 100/50/200 USD 임계값은 설명용 조사 기준일 뿐 범용 최적화 판정이 아닙니다.

다른 옵션들의 문제점:
- **A. 모든 트래픽에 대해 가장 비싼 네트워크 대역폭 사용**: 이는 불필요한 비용을 발생시키며, 모든 워크로드가 고대역폭을 필요로 하지는 않습니다.
- **B. 모든 서비스를 단일 가용 영역에 배치**: 중요 워크로드의 다중 AZ 가용성 요구를 충족하지 못할 수 있습니다. 비중요 환경의 단일 AZ 선택도 명시적인 장애 허용 결정이 필요합니다.
- **D. 모든 네트워크 트래픽 차단**: 이는 실용적이지 않으며, 애플리케이션 기능을 심각하게 제한합니다.
</details>
### 4. Amazon EKS 클러스터 관리 비용을 최적화하기 위한 가장 효과적인 접근 방식은 무엇인가요?

- A. 가능한 한 많은 클러스터 생성
- B. 모든 워크로드를 단일 클러스터에 통합
- C. 워크로드 요구 사항에 따라 클러스터 수를 최적화하고 관리 오버헤드 최소화
- D. 클러스터를 수동으로 관리
<details>
<summary>정답 및 설명</summary>

**정답: C. 워크로드 요구 사항에 따라 클러스터 수를 최적화하고 관리 오버헤드 최소화**

**설명:**
Amazon EKS 클러스터 관리 비용을 최적화하기 위한 가장 효과적인 접근 방식은 워크로드 요구 사항에 따라 클러스터 수를 최적화하고 관리 오버헤드를 최소화하는 것입니다. 이 접근 방식은 클러스터 관리 비용과 운영 복잡성 사이의 균형을 맞추면서 워크로드 격리 및 보안 요구 사항을 충족합니다.

**주요 클러스터 관리 비용 최적화 전략:**

1. **적절한 클러스터 수 유지**:
   - 비즈니스 요구 사항에 따른 클러스터 분리
   - 환경별 클러스터 분리 (개발, 스테이징, 프로덕션)
   - 보안 및 규정 준수 요구 사항 고려

2. **관리 오버헤드 최소화**:
   - 자동화된 클러스터 관리 도구 활용
   - 인프라스트럭처 코드(IaC) 구현
   - 중앙 집중식 모니터링 및 로깅

3. **클러스터 리소스 최적화**:
   - 적절한 컨트롤 플레인 구성
   - 효율적인 노드 그룹 관리
   - 공유 서비스 활용

짧은 eksctl 명령은 생성 예시이며 운영 네트워크/IAM 기본 구성이 아닙니다. AWS 카탈로그에서 EKS 버전을 선택하고 [생성 가이드](../../eks/02-eks-cluster-creation.md)에 따라 VPC와 API endpoint 노출을 검토하며 컨트롤러 권한은 전용 identity에 둡니다. 노드 그룹 크기 범위는 autoscaler를 설치하거나 지출 상한을 만들지 않습니다. 표준/확장 지원 요금, 선택적인 Provisioned Control Plane 용량, 공유 관리 구성 요소의 의존성도 비교에 포함합니다.

Terraform은 확인한 모듈 **21.25.0**을 사용하며 최소 AWS provider는 **6.59**, 예시 고정 버전은 6.64.0입니다. 환경 기본값을 추측하지 않도록 입력값을 필수로 두었습니다. 소유한 private 네트워크/API 연결 경로, 검토한 access entry, 호환·고정 애드온과 IAM 연결, 관리형 노드 그룹을 제공해야 합니다. 표준 EC2 노드에 맞는 CNI/DNS/proxy 경로가 필요하며 Auto Mode 예시는 아닙니다. autoscaler와 desired-size 소유권을 조율하고 격리 모델에 따라 state/provider identity를 분리합니다. plan/apply 실행이나 운영 준비 완료를 주장하지 않습니다.

**구현 방법:**

1. **EKS 클러스터 최적화 구성**:
   ```bash
   : "${EKS_VERSION:?Select a version offered by the AWS EKS support catalog}"
   # eksctl을 사용한 최적화된 클러스터 생성
   eksctl create cluster \
     --name optimized-cluster \
     --region us-west-2 \
     --version "$EKS_VERSION" \
     --nodegroup-name standard-workers \
     --node-type m5.large \
     --nodes-min 2 \
     --nodes-max 10 \
     --managed
   ```

2. **Terraform을 사용한 클러스터 관리 자동화**:
   ```hcl
   terraform {
     required_version = ">= 1.5.7"
     required_providers {
       aws = {
         source  = "hashicorp/aws"
         version = "= 6.64.0"
       }
     }
   }

   variable "region" { type = string }
   variable "account_id" { type = string }
   variable "cluster_name" { type = string }
   variable "environment" { type = string }
   variable "kubernetes_version" { type = string }
   variable "vpc_id" { type = string }
   variable "private_subnet_ids" { type = list(string) }
   variable "reviewed_addons" { type = any }
   variable "reviewed_access_entries" { type = any }
   variable "managed_groups" { type = any }

   provider "aws" {
     region              = var.region
     allowed_account_ids = [var.account_id]
   }

   module "eks" {
     source  = "terraform-aws-modules/eks/aws"
     version = "21.25.0"

     name                    = var.cluster_name
     kubernetes_version      = var.kubernetes_version
     endpoint_private_access = true
     endpoint_public_access  = false
     vpc_id                  = var.vpc_id
     subnet_ids              = var.private_subnet_ids

     addons                  = var.reviewed_addons
     access_entries          = var.reviewed_access_entries
     eks_managed_node_groups = var.managed_groups
     tags = {
       Environment = var.environment
       Terraform   = "true"
     }
   }
   ```

3. **GitOps를 사용한 클러스터 구성 관리**:
   ```yaml
   apiVersion: argoproj.io/v1alpha1
   kind: Application
   metadata:
     name: cluster-config
     namespace: argocd
   spec:
     project: cluster-config
     source:
       repoURL: https://github.com/myorg/cluster-config.git
       targetRevision: REPLACE_WITH_REVIEWED_COMMIT_SHA
       path: configs
     destination:
       server: https://kubernetes.default.svc
       namespace: default
     syncPolicy:
       automated:
         enabled: false
         prune: false
         selfHeal: false
   ```

4. **다중 테넌트 클러스터 구성**:
   ```yaml
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: team-a-quota
     namespace: team-a
   spec:
     hard:
       requests.cpu: '10'
       requests.memory: 20Gi
       limits.cpu: '20'
       limits.memory: 40Gi
       pods: '50'
       services: '20'
       persistentvolumeclaims: '30'
   ---
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: namespace-isolation
     namespace: team-a
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     - Egress
     ingress:
     - from:
       - podSelector: {}
       - namespaceSelector:
           matchLabels:
             kubernetes.io/metadata.name: shared-services
     egress:
     - to:
       - podSelector: {}
       - namespaceSelector:
           matchLabels:
             kubernetes.io/metadata.name: shared-services
     - to:
       - namespaceSelector:
           matchLabels:
             kubernetes.io/metadata.name: kube-system
         podSelector:
           matchLabels:
             k8s-app: kube-dns
       ports:
       - protocol: UDP
         port: 53
       - protocol: TCP
         port: 53
   ```

**클러스터 전략별 비용 영향:**

1. **단일 대형 클러스터**:
   - **장점**: 
     - 단일 컨트롤 플레인 비용
     - 리소스 공유 및 활용도 향상
     - 관리 오버헤드 감소
   - **단점**:
     - 테넌트 간 격리 부족
     - 장애 영향 범위 증가
     - 업그레이드 복잡성

2. **다중 소형 클러스터**:
   - **장점**:
     - 강력한 워크로드 격리
     - 독립적인 업그레이드 및 유지 관리
     - 장애 영향 범위 제한
   - **단점**:
     - 여러 컨트롤 플레인 비용
     - 리소스 중복 및 낮은 활용도
     - 관리 오버헤드 증가

3. **하이브리드 접근 방식**:
   - **장점**:
     - 비용과 격리 사이의 균형
     - 워크로드 특성에 따른 최적화
     - 유연한 리소스 할당
   - **단점**:
     - 복잡한 아키텍처 설계
     - 일관된 정책 적용의 어려움

**모범 사례:**

1. **클러스터 비용 분석 및 최적화**:
계정 전체 청구를 필터 없이 그룹화한 첫 행을 클러스터 총액으로 표시하지 말고 아래 context·계정·태그 범위 수집 예시를 사용합니다.

2. **클러스터 자동화 및 IaC 구현**:
   - 모든 클러스터 구성을 코드로 관리
   - 자동화된 배포 및 업데이트 파이프라인
   - 일관된 구성 및 정책 적용

3. **공유 서비스 모델 구현**:
   ```yaml
   apiVersion: v1
   kind: Namespace
   metadata:
     name: shared-services
     labels:
       name: shared-services
       access: global
   ---
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: allow-team-a
     namespace: shared-services
   spec:
     podSelector:
       matchLabels:
         app: shared-api
     policyTypes:
     - Ingress
     ingress:
     - from:
       - namespaceSelector:
           matchLabels:
             kubernetes.io/metadata.name: team-a
       ports:
       - protocol: TCP
         port: 8080
   ```

4. **클러스터 수명 주기 관리**:
   - 정기적인 클러스터 평가 및 최적화
   - 사용하지 않는 클러스터 식별 및 제거
   - 클러스터 통합 기회 모색

**추가 환경 구성과 읽기 전용 수집 예시:**

1. **비용 효율적인 다중 클러스터 아키텍처**:
   ```
   +-------------------+    +-------------------+    +-------------------+
   |                   |    |                   |    |                   |
   |  Production       |    |  Development      |    |  Staging          |
   |  Cluster          |    |  Cluster          |    |  Cluster          |
   |                   |    |                   |    |                   |
   +-------------------+    +-------------------+    +-------------------+
           |                        |                        |
           v                        v                        v
   +---------------------------------------------------------------+
   |                                                               |
   |                  Centralized Management                       |
   |                  (GitOps, Monitoring, Logging)                |
   |                                                               |
   +---------------------------------------------------------------+
           |                        |                        |
           v                        v                        v
   +-------------------+    +-------------------+    +-------------------+
   |                   |    |                   |    |                   |
   |  Team A           |    |  Team B           |    |  Team C           |
   |  Namespaces       |    |  Namespaces       |    |  Namespaces       |
   |                   |    |                   |    |                   |
   +-------------------+    +-------------------+    +-------------------+
   ```

2. **Terraform을 사용한 다중 클러스터 관리**:
   ```hcl
   # production.tfvars: merge with the production account/network/add-on/access inputs.
   cluster_name = "production"
   environment  = "production"
   managed_groups = {
     critical = {
       instance_types = ["m5.large"]
       capacity_type  = "ON_DEMAND"
       min_size       = 3
       max_size       = 10
       desired_size   = 3
     }
     general = {
       instance_types = ["m5.large", "m5a.large"]
       capacity_type  = "SPOT"
       min_size       = 3
       max_size       = 20
       desired_size   = 3
     }
   }
   ```

   ```hcl
   # development.tfvars: use a separate state/backend and the development identity.
   cluster_name = "development"
   environment  = "development"
   managed_groups = {
     default = {
       instance_types = ["m5.large", "m5a.large"]
       capacity_type  = "SPOT"
       min_size       = 1
       max_size       = 5
       desired_size   = 1
     }
   }
   ```

3. **클러스터 비용 모니터링 및 최적화 스크립트**:
   ```python
   import json
   import os
   import re
   import subprocess
   from datetime import date
   from pathlib import Path


   def read_json(command):
       completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)
       return json.loads(completed.stdout)


   def collect(context, expected_server, caller_account, linked_account, tag_key, tag_value, start, end,
               run=subprocess.run, query=read_json):
       if not all([context, expected_server, tag_key, tag_value]):
           raise ValueError("Explicit context, API server, and billing tag mapping are required")
       if not all(re.fullmatch(r"[0-9]{12}", account) for account in [caller_account, linked_account]):
           raise ValueError("Use reviewed 12-digit account IDs")
       if any(date.fromisoformat(value).isoformat() != value for value in [start, end]) or start >= end:
           raise ValueError("Use YYYY-MM-DD with Start before exclusive End")
       server = run(
           ["kubectl", "--context", context, "config", "view", "--minify",
            "--output", "jsonpath={.clusters[0].cluster.server}"],
           check=True, capture_output=True, text=True, timeout=30,
       ).stdout.strip()
       if server != expected_server:
           raise RuntimeError("Kubernetes context/API-server mismatch")
       identity = query(["aws", "sts", "get-caller-identity", "--region", "us-east-1",
                         "--output", "json", "--no-cli-pager"])
       if identity["Account"] != caller_account:
           raise RuntimeError("Calling AWS account mismatch")
       # Preserve actual metrics samples, timestamps, windows, and units.
       usage = query(["kubectl", "--context", context, "get", "--raw",
                      "/apis/metrics.k8s.io/v1beta1/nodes"])
       if usage.get("kind") != "NodeMetricsList" or not isinstance(usage.get("items"), list):
           raise ValueError("Unexpected node metrics response")
       expression = {"And": [
           {"Dimensions": {"Key": "LINKED_ACCOUNT", "Values": [linked_account], "MatchOptions": ["EQUALS"]}},
           {"Tags": {"Key": tag_key, "Values": [tag_value], "MatchOptions": ["EQUALS"]}},
       ]}
       base = [
           "aws", "ce", "get-cost-and-usage", "--region", "us-east-1",
           "--time-period", json.dumps({"Start": start, "End": end}),
           "--granularity", "MONTHLY", "--metrics", "UnblendedCost",
           "--group-by", "Type=DIMENSION,Key=SERVICE",
           "--filter", json.dumps(expression), "--output", "json", "--no-cli-pager",
       ]
       pages = []
       token = None
       seen = set()
       for _ in range(100):
           page = query(base + (["--next-page-token", token] if token else []))
           if not isinstance(page.get("ResultsByTime"), list):
               raise ValueError("Unexpected cost response")
           pages.append(page)
           token = page.get("NextPageToken")
           if not token:
               return {
                   "context": context, "apiServer": server, "nodeUsage": usage,
                   "billingScope": expression, "basis": "UnblendedCost", "costPages": pages,
               }
           if token in seen:
               raise RuntimeError("Repeated cost pagination token")
           seen.add(token)
       raise RuntimeError("Page limit exceeded; narrow the query")


   if __name__ == "__main__":
       result = collect(
           os.environ["KUBE_CONTEXT"], os.environ["EXPECTED_API_SERVER"],
           os.environ["EXPECTED_CALLER_ACCOUNT"], os.environ["LINKED_ACCOUNT_ID"],
           os.environ["BILLING_TAG_KEY"], os.environ["BILLING_TAG_VALUE"],
           os.environ["START_DATE"], os.environ["END_DATE"],
       )
       Path("cluster-cost-and-usage.json").write_text(json.dumps(result, indent=2) + "\n")
       print("Saved raw metrics and tag-scoped billing pages; no resizing recommendation was made.")
   ```

Argo CD Application에는 설치된 컨트롤러, 검토한 저장소/commit, 저장소·대상·리소스 종류를 제한하는 기존 `cluster-config` AppProject가 필요합니다. 자리표시자 SHA와 저장소를 바꾼 후 사용합니다. 초기 검토를 위해 자동 동기화/pruning을 끈 상태이며 소유자가 의도한 조정 동작만 활성화합니다. 공유 관리 자격 증명/컨트롤러는 별도 클러스터 사이에도 장애·보안 영향 범위를 넓힐 수 있습니다.

ResourceQuota는 admission과 객체 수를 제한하며 청구액이나 테넌트 인가를 제어하지 않습니다. NetworkPolicy는 여러 정책의 허용이 합쳐지고 CNI 집행이 필요합니다. namespace 예시는 `team-a` 내부, 지정한 공유 namespace와의 통신, 표준 CoreDNS Deployment로의 DNS를 허용합니다. node-local/Auto Mode DNS 및 다른 의존성은 명시적으로 조정합니다. shared API 예시는 `app: shared-api` Pod의 TCP 8080에 `team-a`만 허용합니다. 기존의 광범위한 allow-all 정책을 남기지 말고 함께 조정하세요. RBAC·admission·IAM·신뢰 경계는 별도 제어입니다.

환경별 tfvars는 위 검토한 모듈의 override이며 제공되지 않은 `./modules/eks-cluster` 호출이 아닙니다. 각 환경의 계정·네트워크·버전·애드온·접근 설정과 병합하고 별도 state/backend 및 identity를 사용합니다. 인스턴스 목록/수량은 예시이므로 중단 허용성과 현재 리전 선택지를 검토합니다.

수집 스크립트는 실행마다 **명시적인 context 하나**를 사용합니다. `KUBE_CONTEXT`, `EXPECTED_API_SERVER`, `EXPECTED_CALLER_ACCOUNT`, `LINKED_ACCOUNT_ID`, `BILLING_TAG_KEY`, `BILLING_TAG_VALUE`, `START_DATE`, `END_DATE`를 설정하고 클러스터마다 의도적으로 반복합니다. API server URL은 검토한 EKS 클러스터와 일치해야 합니다. 같은 context의 requests를 모든 클러스터의 사용률로 재표시하지 않고, 실제 Metrics API 표본의 timestamp/window/단위와 태그 범위 Cost Explorer 전체 페이지를 저장합니다. Metrics Server와 읽기 권한이 필요합니다. 노드 표본 누락은 사용량 0이 아니며 짧은 표본은 피크 수요 이력이 아닙니다.

상업 AWS 청구 endpoint와 미포함 종료일을 사용하며 조회 가능한 청구 기간을 선택합니다. 기존 2023년 날짜는 설정 예시였고 실측 결과가 아닙니다. 청구 데이터에 태그 매핑이 있어야 하며 태그 없는 비용/공유 비용은 누락될 수 있습니다. 금액 단위·비용 기준·estimated 상태를 원본대로 보존하고 첫 그룹에서 총액을 추정하거나 requests/capacity 임계값으로 축소를 권고하지 않습니다.

다른 옵션들의 문제점:
- **A. 가능한 한 많은 클러스터 생성**: 이는 각 클러스터에 대한 컨트롤 플레인 비용과 관리 오버헤드를 증가시키며, 리소스 활용도를 저하시킵니다.
- **B. 모든 워크로드를 단일 클러스터에 통합**: 이는 일부 환경에서 적합할 수 있지만, 보안 요구 사항, 워크로드 격리, 장애 영향 범위 등을 고려하지 않습니다.
- **D. 클러스터를 수동으로 관리**: 수동 관리는 오류 가능성을 높이고, 일관성을 저하시키며, 운영 오버헤드를 증가시킵니다.
</details>
### 5. Amazon EKS에서 비용 모니터링 및 할당을 위한 가장 효과적인 접근 방식은 무엇인가요?

- A. AWS 청구서만 검토
- B. 태그 지정 전략, 비용 할당 도구 및 지속적인 모니터링 구현
- C. 모든 리소스에 동일한 비용 할당
- D. 비용 모니터링 없이 리소스 사용
<details>
<summary>정답 및 설명</summary>

**정답: B. 태그 지정 전략, 비용 할당 도구 및 지속적인 모니터링 구현**

**설명:**
Amazon EKS에서 비용 모니터링 및 할당을 위한 가장 효과적인 접근 방식은 태그 지정 전략, 비용 할당 도구 및 지속적인 모니터링을 구현하는 것입니다. 이 접근 방식은 비용을 정확하게 추적하고, 팀이나 프로젝트별로 할당하며, 비용 최적화 기회를 식별하는 데 도움이 됩니다.

**주요 비용 모니터링 및 할당 전략:**

1. **포괄적인 태그 지정 전략**:
   - 비즈니스 단위, 팀, 프로젝트, 환경별 태그
   - 일관된 태그 지정 규칙 적용
   - 자동화된 태그 지정 구현

2. **비용 할당 도구 활용**:
   - AWS Cost Explorer 및 AWS Budgets
   - Kubecost 또는 CloudHealth와 같은 전문 도구
   - 사용자 정의 대시보드 및 보고서

3. **지속적인 모니터링 및 최적화**:
   - 정기적인 비용 검토 및 분석
   - 이상 탐지 및 알림
   - 최적화 권장 사항 구현

Kubernetes 레이블, AWS 리소스 태그, 활성화한 청구 태그는 서로 다릅니다. Namespace 레이블은 Pod나 AWS 리소스에 자동 전파되지 않으므로 워크로드 레이블은 Pod template에 넣습니다. 아래 Organizations 태그 정책은 EKS 클러스터를 포함한 지원 리소스의 지정 태그 키/값을 검증하며, 태그를 생성하거나 필수 태그 존재 검사를 설정하지 않습니다. 상속 정책과 별도 누락 태그 제어를 검토합니다. 청구 활성화/backfill은 별도 작업이며 최대 12개월 backfill도 과거에 실제 태그가 존재했어야 합니다.

아래 CUR 명령은 Cost Explorer 대시보드나 CUR 2.0이 아닌 **legacy CUR**를 만듭니다. AWS는 legacy CUR를 계속 지원합니다. 새 설계는 [FinOps 가이드](../../ops/13-finops-cost-platform.md)의 Data Exports/CUR 2.0을 평가합니다. legacy 예시에는 지정 리전의 기존 버킷, 검토한 CUR 전달 정책, 보고 권한이 필요하며 버킷·Glue 스키마·Athena 통합·대시보드를 생성하지 않습니다. 전달 서비스별 정책을 따르고 CUR 2.0의 `bcm-data-exports` 정책을 legacy 서비스에 대입하지 않습니다.

**구현 방법:**

1. **태그 지정 전략 구현**:
   ```yaml
   apiVersion: v1
   kind: Namespace
   metadata:
     name: team-a
     labels:
       team: team-a
       cost-center: cc-123
       environment: production
       project: project-x
   ---
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
     namespace: team-a
     labels:
       app: web-app
       team: team-a
       cost-center: cc-123
       environment: production
       project: project-x
   spec:
     selector:
       matchLabels:
         app: web-app
     template:
       metadata:
         labels:
           app: web-app
           team: team-a
           cost-center: cc-123
           environment: production
           project: project-x
       spec:
         containers:
         - name: web-app
           image: registry.example.com/team/web-app:REVIEWED_TAG
   ```

2. **AWS 태그 정책 구성**:
   ```json
   {
     "tags": {
       "team": {
         "tag_key": {
           "@@assign": "team"
         },
         "tag_value": {
           "@@assign": [
             "team-a",
             "team-b",
             "platform"
           ]
         },
         "enforced_for": {
           "@@assign": [
             "ec2:instance",
             "ec2:volume",
             "eks:cluster"
           ]
         }
       },
       "cost-center": {
         "tag_key": {
           "@@assign": "cost-center"
         },
         "enforced_for": {
           "@@assign": [
             "ec2:instance",
             "ec2:volume",
             "eks:cluster"
           ]
         }
       },
       "environment": {
         "tag_key": {
           "@@assign": "environment"
         },
         "tag_value": {
           "@@assign": [
             "production",
             "staging",
             "development"
           ]
         },
         "enforced_for": {
           "@@assign": [
             "ec2:instance",
             "ec2:volume",
             "eks:cluster"
           ]
         }
       }
     }
   }
   ```

3. **Kubecost 설치 및 구성**:
[본문](../../eks/07-eks-cost-optimization.md)의 검증한 Kubecost 3.2.4 설치 또는 [EKS06 6번 문항](06-eks-monitoring-logging-quiz.md)의 OpenCost 1.121.2/chart 2.5.31을 사용합니다. Kubecost 3.x는 ClickHouse/finops-agent 직접 수집을 사용하므로 2.x Prometheus values나 명령행 라이선스 토큰을 사용하지 않습니다. 소유 배포 하나를 재사용하고 마이그레이션·라이선스·스토리지 요구를 검토합니다.

4. **Legacy CUR 전달 설정**:
   ```bash
   # 비용 및 사용 보고서 생성
   aws cur put-report-definition \
     --report-definition '{
       "ReportName": "eks-cost-report",
       "TimeUnit": "HOURLY",
       "Format": "Parquet",
       "Compression": "Parquet",
       "AdditionalSchemaElements": ["RESOURCES"],
       "S3Bucket": "my-cost-reports",
       "S3Prefix": "eks-costs",
       "S3Region": "us-east-1",
       "AdditionalArtifacts": ["ATHENA"],
       "RefreshClosedReports": true,
       "ReportVersioning": "OVERWRITE_REPORT"
     }'
   ```

**비용 할당 및 모니터링 구성 요소:**

1. **태그 기반 비용 할당**:
   - 팀, 프로젝트, 환경별 비용 분석
   - 공유 리소스 비용 분배
   - 비용 책임 명확화

2. **네임스페이스 수준 비용 추적**:
   - Kubernetes 네임스페이스별 리소스 사용량
   - 네임스페이스별 비용 할당
   - 팀별 사용량 및 비용 추세

3. **워크로드 수준 비용 분석**:
   - 배포, 스테이트풀셋, 작업별 비용
   - 컨테이너 수준 리소스 사용량
   - 애플리케이션별 비용 최적화 기회

4. **비용 이상 탐지 및 알림**:
   - 예상치 못한 비용 증가 감지
   - 예산 초과 알림
   - 비용 추세 분석

**모범 사례:**

1. **일관된 태그 지정 정책 적용**:
   ```bash
   # AWS 리소스 태그 지정 자동화
   aws resourcegroupstaggingapi tag-resources --region us-west-2 \
     --resource-arn-list arn:aws:eks:us-west-2:123456789012:cluster/my-cluster \
     --tags team=platform,cost-center=cc-100,environment=production
   ```

2. **비용 할당을 위한 네임스페이스 설계**:
   ```yaml
   # 팀별 네임스페이스 구성
   apiVersion: v1
   kind: Namespace
   metadata:
     name: team-a-production
     labels:
       team: team-a
       environment: production
       cost-center: cc-123
   ---
   apiVersion: v1
   kind: Namespace
   metadata:
     name: team-a-development
     labels:
       team: team-a
       environment: development
       cost-center: cc-123
   ```

3. **리소스 요청 및 제한 최적화**:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
   spec:
     template:
       spec:
         containers:
         - name: web-app
           resources:
             requests:
               cpu: 100m
               memory: 256Mi
             limits:
               cpu: 500m
               memory: 512Mi
           image: registry.example.com/team/web-app:REVIEWED_TAG
       metadata:
         labels:
           app: web-app
     selector:
       matchLabels:
         app: web-app
   ```

4. **정기적인 비용 검토 및 최적화**:
   - 주간/월간 비용 검토 회의
   - 비용 추세 및 이상 분석
   - 최적화 조치 추적 및 영향 측정

**추가 구성과 데이터 검증 예시:**

1. **비용 모니터링 대시보드**:
리전별 TagResources 호출은 대상 리전을 확인하고 `FailedResourcesMap`을 검사합니다. CLI 종료 성공만으로 모든 요청 리소스의 태그 성공이 입증되지는 않으므로 청구 할당에 사용하기 전에 실제 태그를 확인합니다.

**할당 비용률 추정 대시보드**

이 예시는 한 클러스터 Prometheus의 순간 **CPU+메모리 할당 비용률 추정치(USD/hour)**이며 청구서나 namespace 전체 비용이 아닙니다. 입력은 OpenCost 할당/가격 메트릭(예시 `job="opencost"`)과 kube-state-metrics의 Pod 레이블(`job="kube-state-metrics"`)입니다. 실제 job 레이블과 CPU·메모리·가격 데이터 수집 범위를 확인합니다. 적절한 ServiceMonitor honor-label 설정으로 exporter의 워크로드 namespace 레이블을 유지하세요. 공유 백엔드에서는 모든 집계/join에 일치하는 cluster 식별자가 필요합니다.

첫 values fragment는 소유한 kube-prometheus-stack 릴리스에 병합합니다. team 레이블 값은 제한하고 Pod template에 실제로 넣어야 하며 namespace 레이블만으로 생성되지 않습니다. team 누락은 `unassigned`로 집계합니다. 동일 수집본은 중복 제거하지만 상충하는 가격/소유권 소스는 별도로 해결해야 합니다. GPU·스토리지·네트워크·컨트롤 플레인·유휴/공유 할당·할인·크레딧·세금은 이 두 구성 요소에 포함되지 않습니다. 누락은 비용 0이 아니며 시간당 비용률은 월별 금액이 아닙니다.

PrometheusRule의 namespace/release 레이블은 본문의 selector와 맞춰야 합니다. 대시보드 적용 전에 `REPLACE_WITH_PROMETHEUS_UID`를 검토한 단일 클러스터 데이터 소스로 바꾸세요. ConfigMap의 `grafana_dashboard: "1"`은 본문의 sidecar 레이블이며 실제 JSON도 아래에 제공합니다. rule 상태·데이터 범위·대시보드 쿼리를 검증해야 합니다. 실제 청구/Grafana 배포에 연결해 실행한 예시는 아닙니다.

```yaml
kube-state-metrics:
  metricLabelsAllowlist:
  - pods=[team]
```

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: eks-allocation-rate
  namespace: monitoring
  labels:
    release: monitoring
spec:
  groups:
  - name: eks-allocation-rate
    rules:
    - record: eks_review:pod_cpu_memory_cost_per_hour:sum
      expr: "sum by (namespace, pod) (\n  (\n    max by (namespace, pod, container,\
        \ node) (\n      container_cpu_allocation{job=\"opencost\"}\n    )\n    *\
        \ on (node) group_left\n    max by (node) (node_cpu_hourly_cost{job=\"opencost\"\
        })\n  )\n  +\n  (\n    max by (namespace, pod, container, node) (\n      container_memory_allocation_bytes{job=\"\
        opencost\"}\n    ) / 1073741824\n    * on (node) group_left\n    max by (node)\
        \ (node_ram_hourly_cost{job=\"opencost\"})\n  )\n)"
    - record: eks_review:team_cpu_memory_cost_per_hour:sum
      expr: "sum by (team) (\n  label_replace(\n    eks_review:pod_cpu_memory_cost_per_hour:sum\n\
        \    * on (namespace, pod) group_left (label_team)\n    max by (namespace,\
        \ pod, label_team) (kube_pod_labels{job=\"kube-state-metrics\",label_team!=\"\
        \"}),\n    \"team\", \"$1\", \"label_team\", \"(.+)\"\n  )\n  or\n  label_replace(\n\
        \    eks_review:pod_cpu_memory_cost_per_hour:sum\n    unless on (namespace,\
        \ pod) max by (namespace, pod, label_team) (kube_pod_labels{job=\"kube-state-metrics\"\
        ,label_team!=\"\"}),\n    \"team\", \"unassigned\", \"namespace\", \".*\"\n\
        \  )\n)"
```

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cost-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: '1'
data:
  cost-dashboard.json: "{\n  \"title\": \"Estimated CPU and memory allocation rate\"\
    ,\n  \"uid\": \"eks-allocation-rate\",\n  \"schemaVersion\": 39,\n  \"version\"\
    : 1,\n  \"refresh\": \"1m\",\n  \"time\": {\n    \"from\": \"now-6h\",\n    \"\
    to\": \"now\"\n  },\n  \"panels\": [\n    {\n      \"id\": 1,\n      \"title\"\
    : \"CPU + memory allocation by namespace (USD/hour)\",\n      \"type\": \"timeseries\"\
    ,\n      \"gridPos\": {\n        \"x\": 0,\n        \"y\": 0,\n        \"w\":\
    \ 12,\n        \"h\": 8\n      },\n      \"datasource\": {\n        \"type\":\
    \ \"prometheus\",\n        \"uid\": \"REPLACE_WITH_PROMETHEUS_UID\"\n      },\n\
    \      \"fieldConfig\": {\n        \"defaults\": {\n          \"unit\": \"currencyUSD\"\
    \n        },\n        \"overrides\": []\n      },\n      \"targets\": [\n    \
    \    {\n          \"refId\": \"A\",\n          \"expr\": \"sum by (namespace)\
    \ (eks_review:pod_cpu_memory_cost_per_hour:sum)\",\n          \"legendFormat\"\
    : \"{{namespace}}\"\n        }\n      ]\n    },\n    {\n      \"id\": 2,\n   \
    \   \"title\": \"CPU + memory allocation by team (USD/hour)\",\n      \"type\"\
    : \"timeseries\",\n      \"gridPos\": {\n        \"x\": 12,\n        \"y\": 0,\n\
    \        \"w\": 12,\n        \"h\": 8\n      },\n      \"datasource\": {\n   \
    \     \"type\": \"prometheus\",\n        \"uid\": \"REPLACE_WITH_PROMETHEUS_UID\"\
    \n      },\n      \"fieldConfig\": {\n        \"defaults\": {\n          \"unit\"\
    : \"currencyUSD\"\n        },\n        \"overrides\": []\n      },\n      \"targets\"\
    : [\n        {\n          \"refId\": \"A\",\n          \"expr\": \"eks_review:team_cpu_memory_cost_per_hour:sum\"\
    ,\n          \"legendFormat\": \"{{team}}\"\n        }\n      ]\n    }\n  ]\n}"
```



2. **AWS 예산 및 알림 설정**:
   ```bash
   # AWS 예산 생성
   aws budgets create-budget \
     --account-id 123456789012 \
     --budget '{
       "BudgetName": "EKS-Monthly",
       "BudgetLimit": {
         "Amount": "1000",
         "Unit": "USD"
       },
       "CostFilters": {
         "TagKeyValue": [
           "user:kubernetes.io/cluster/my-cluster$owned"
         ]
       },
       "TimeUnit": "MONTHLY",
       "BudgetType": "COST"
     }' \
     --notifications-with-subscribers '[
       {
         "Notification": {
           "NotificationType": "ACTUAL",
           "ComparisonOperator": "GREATER_THAN",
           "Threshold": 80,
           "ThresholdType": "PERCENTAGE"
         },
         "Subscribers": [
           {
             "SubscriptionType": "EMAIL",
             "Address": "team@example.com"
           }
         ]
       }
     ]'
   ```

3. **Terraform을 사용한 비용 모니터링 인프라 구성**:
   ```hcl
   # AWS 비용 및 사용 보고서
   resource "aws_cur_report_definition" "eks_cost" {
     report_name                = "eks-cost-report"
     time_unit                  = "HOURLY"
     format                     = "Parquet"
     compression                = "Parquet"
     additional_schema_elements = ["RESOURCES"]
     s3_bucket                  = aws_s3_bucket.cost_reports.id
     s3_prefix                  = "eks-costs"
     s3_region                  = "us-east-1"
     additional_artifacts       = ["ATHENA"]
     refresh_closed_reports     = true
     report_versioning          = "OVERWRITE_REPORT"
   }

   # Athena 쿼리 결과를 위한 S3 버킷
   resource "aws_s3_bucket" "athena_results" {
     bucket = "eks-cost-athena-results-${data.aws_caller_identity.current.account_id}-${var.region}"

     tags = {
       Name = "EKS Cost Athena Results"
     }
   }

   # Athena 워크그룹
   resource "aws_athena_workgroup" "eks_cost" {
     name = "eks-cost-analysis"

     configuration {
       result_configuration {
         output_location = "s3://${aws_s3_bucket.athena_results.bucket}/output/"
       }
     }
   }

   # Terraform supports aws_quicksight_dashboard.
   # Account edition, datasets/templates, and permissions still require an owned setup.
   ```

4. **비용 최적화 자동화 스크립트**:
Q4의 검증한 context·계정·태그 범위 수집 스크립트를 재사용하여 실제 Metrics API 표본과 청구 페이지를 확보합니다. requests/limits는 선언된 구성이지 실제 사용량이 아닙니다. 따라서 requests/limits 비율이 0.5보다 작다는 이유만으로 requests 축소를 권고하지 않습니다. 현재 replica 수로 계산한 요청량을 과거 기간 사용량과 직접 비교하지 말고 같은 워크로드·기간·단위·수집 범위를 맞춥니다. 팀/비용 센터별 표는 태그 없는 비용과 공유 비용 정책까지 대조해야 합니다. 운영용 보고·알림은 [FinOps 가이드](../../ops/13-finops-cost-platform.md)의 명시적인 수집/검증 절차를 참고하며 실패나 누락을 0으로 바꾸지 않습니다.

추가 예산의 1,000 USD/80%는 설정 예시입니다. 활성화한 실제 Budgets 태그 필터 형식과 범위를 확인하고 태그 없는/공유 요금을 별도로 다룹니다. Budgets는 처리된 청구 데이터에 의존하며 지출을 강제로 막지 않습니다. Terraform은 기존 CUR 버킷·caller identity·provider·region 입력을 요구하는 구성 fragment입니다. Athena 결과 버킷의 접근·보존·암호화와 Glue 테이블/쿼리 권한도 소유자가 구성해야 합니다. QuickSight 대시보드는 Terraform의 `aws_quicksight_dashboard`로 관리할 수 있으나 계정 에디션·데이터셋·템플릿·권한 설정을 대신하지 않습니다.

다른 옵션들의 문제점:
- **A. AWS 청구서만 검토**: AWS 청구서는 높은 수준의 비용 정보만 제공하며, 세부적인 비용 할당이나 최적화 기회를 식별하기 어렵습니다.
- **C. 모든 리소스에 동일한 비용 할당**: 이는 실제 리소스 사용량과 비용 발생을 정확하게 반영하지 않으며, 팀이나 프로젝트별 비용 책임을 명확히 하지 못합니다.
- **D. 비용 모니터링 없이 리소스 사용**: 비용 모니터링 없이는 비용 증가를 조기에 감지하거나 최적화 기회를 식별할 수 없으며, 예산 관리가 어렵습니다.
</details>
### 6. 확장 가능한 EKS 비용 최적화 워크플로우를 가장 잘 지원하는 접근은 무엇인가요?

- A. 결과 측정 없이 리소스를 수동 변경
- B. 워크로드 텔레메트리를 무시하고 청구 데이터만 고려
- C. 명확한 소유권 아래 비용 가시성·리소스 텔레메트리·적절한 자동 확장을 결합
- D. 같은 리소스에 조율되지 않은 최적화 도구를 중복 실행

<details>
<summary>정답 및 설명</summary>

**정답: C. 명확한 소유권 아래 비용 가시성·리소스 텔레메트리·적절한 자동 확장을 결합**

**설명:**
아래 도구는 상호 보완적인 역할의 예시이며 모두 설치해야 한다는 뜻이 아닙니다. 소유자가 명확한 비용/텔레메트리 경로와 워크로드에 적합한 확장을 선택합니다. EKS Auto Mode, 자체 Karpenter, Cluster Autoscaler가 이미 노드 용량을 관리할 수 있으므로 소유 범위를 분리하고 컨트롤러 충돌을 피합니다. 절감과 SLO 유지 여부는 측정해야 하며 비용 도구 설치만으로 청구 데이터가 HPA/Karpenter 정책에 자동 연결되지는 않습니다.

**주요 비용 최적화 도구 및 기능:**

1. **Kubecost**:
   - Kubernetes 리소스 비용 가시성
   - 네임스페이스, 배포, 서비스별 비용 할당
   - 비용 최적화 권장 사항
   - 비용 예측 및 예산 관리

2. **Karpenter**:
   - 지능적인 노드 프로비저닝 및 관리
   - 워크로드·가용 용량·가격 제약 내 인스턴스 선택
   - 실제 환경에서 검증해야 하는 프로비저닝/확장 동작
   - 스팟 인스턴스 활용 최적화

3. **AWS Cost Explorer**:
   - AWS 서비스 전반의 비용 분석
   - 태그 기반 비용 할당
   - 비용 추세 및 예측
   - 예약 인스턴스 및 절감형 플랜 권장 사항

4. **Kubernetes 자동 스케일링 도구**:
   - Horizontal Pod Autoscaler (HPA)
   - Vertical Pod Autoscaler (VPA)
   - Cluster Autoscaler
   - Cluster Proportional Autoscaler

**구현 방법:**

1. **Kubecost 설치 및 구성**:
Q5와 [본문](../../eks/07-eks-cost-optimization.md)의 검증한 설치/할당 데이터 전제 조건을 재사용합니다. Kubecost 3.2.4는 현재 `kubecost/kubecost` chart와 ClickHouse/직접 agent 구조를 사용하며 기능은 에디션/설정에 따릅니다. OpenCost는 별도 선택지입니다. 기존 소유 구성에 두 번째 수집기를 중복 배포하지 않습니다.

2. **Karpenter 설치 및 구성**:
다음을 `karpenter-values.yaml`로 저장하고 계정/역할/클러스터/endpoint/queue를 검토한 기존 값으로 바꾼 뒤 [Karpenter 가이드](../../autoscaling/02-karpenter.md)를 따릅니다. 확인한 예시는 1.14.1이며 호환성 표에서 EKS 1.36은 최소 1.13이 필요합니다. 적용되는 키는 `settings.*`이며 무시되는 `controller.clusterName/clusterEndpoint`가 아닙니다. IRSA trust는 `system:serviceaccount:karpenter:karpenter`와 audience에 맞춰야 하고 상충하는 IRSA/Pod Identity를 혼합하지 않습니다. 컨트롤러/노드 IAM, 노드 접근, 서브넷/보안 그룹, 중단 queue/이벤트 연결, 안정적인 bootstrap 용량을 먼저 준비합니다. 새 Helm 설치와 CRD 업그레이드는 소유권/수명 주기가 다르며 컨트롤러 업그레이드만으로 기존 CRD가 갱신되지 않습니다.

```yaml
serviceAccount:
  create: true
  name: karpenter
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/KarpenterControllerRole-my-cluster
settings:
  clusterName: my-cluster
  clusterEndpoint: https://REPLACE_WITH_REVIEWED_EKS_ENDPOINT
  interruptionQueue: my-cluster
```

```bash
: "${KUBE_CONTEXT:?Select the reviewed context matching the values file}"
KARPENTER_VERSION="1.14.1"
helm template karpenter oci://public.ecr.aws/karpenter/karpenter \
  --version "$KARPENTER_VERSION" --namespace karpenter \
  -f karpenter-values.yaml > karpenter-rendered.yaml
# Fresh installation only after the owned IAM, node access, queue, CRDs, and bootstrap capacity are ready.
helm install karpenter oci://public.ecr.aws/karpenter/karpenter \
  --kube-context "$KUBE_CONTEXT" \
  --version "$KARPENTER_VERSION" --namespace karpenter --create-namespace \
  -f karpenter-values.yaml --wait --timeout 5m
```

   ```yaml
   # Karpenter NodePool 및 NodeClass 구성
   apiVersion: karpenter.sh/v1
   kind: NodePool
   metadata:
     name: default
   spec:
     template:
       spec:
         requirements:
           - key: "karpenter.sh/capacity-type"
             operator: In
             values: ["spot", "on-demand"]
           - key: "kubernetes.io/arch"
             operator: In
             values: ["amd64"]
           - key: "kubernetes.io/os"
             operator: In
             values: ["linux"]
           - key: "node.kubernetes.io/instance-type"
             operator: In
             values: ["m5.large", "m5a.large", "m5d.large", "m4.large", "t3.large", "t3a.large"]
         nodeClassRef:
           group: karpenter.k8s.aws
           kind: EC2NodeClass
           name: default
     limits:
       cpu: 1000
       memory: 1000Gi
     disruption:
       consolidationPolicy: WhenEmpty
       consolidateAfter: 30s
   ---
   apiVersion: karpenter.k8s.aws/v1
   kind: EC2NodeClass
   metadata:
     name: default
   spec:
     amiSelectorTerms:
       - alias: al2023@latest
     role: KarpenterNodeRole
     subnetSelectorTerms:
       - tags:
           karpenter.sh/discovery: my-cluster
     securityGroupSelectorTerms:
       - tags:
           karpenter.sh/discovery: my-cluster
     tags:
       karpenter.sh/discovery: my-cluster
   ```

3. **Horizontal Pod Autoscaler 구성**:
   ```yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: web-app
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: web-app
     minReplicas: 2
     maxReplicas: 10
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70
     - type: Resource
       resource:
         name: memory
         target:
           type: Utilization
           averageUtilization: 80
   ```

4. **Vertical Pod Autoscaler 구성**:
   ```yaml
   apiVersion: autoscaling.k8s.io/v1
   kind: VerticalPodAutoscaler
   metadata:
     name: web-app-vpa
   spec:
     targetRef:
       apiVersion: "apps/v1"
       kind: Deployment
       name: web-app
     updatePolicy:
       updateMode: "Off"
     resourcePolicy:
       containerPolicies:
       - containerName: '*'
         minAllowed:
           cpu: 50m
           memory: 100Mi
         maxAllowed:
           cpu: 1
           memory: 1Gi
         controlledResources: ["cpu", "memory"]
   ```

**도구 통합 및 워크플로우:**

1. **비용 가시성 및 분석**:
   - Kubecost: 클러스터 내 리소스 비용 분석
   - AWS Cost Explorer: AWS 서비스 전반의 비용 분석
   - 통합 대시보드: 전체 비용 개요 및 추세

2. **자동화된 리소스 최적화**:
   - Karpenter: 최적의 노드 프로비저닝 및 관리
   - HPA/VPA: 워크로드 수준 리소스 최적화
   - 스팟 인스턴스 활용: 비용 효율적인 컴퓨팅 리소스

3. **비용 할당 및 책임**:
   - 태그 기반 비용 할당
   - 네임스페이스 및 레이블 기반 비용 분석
   - 팀 및 프로젝트별 비용 보고

4. **지속적인 최적화 및 개선**:
   - 비용 최적화 권장 사항 구현
   - 정기적인 비용 검토 및 분석
   - 비용 절감 목표 설정 및 추적

**모범 사례:**

1. **리소스 요청 및 제한 최적화**:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
   spec:
     template:
       spec:
         containers:
         - name: web-app
           resources:
             requests:
               cpu: 100m
               memory: 256Mi
             limits:
               cpu: 500m
               memory: 512Mi
           image: registry.example.com/team/web-app:REVIEWED_TAG
       metadata:
         labels:
           app: web-app
     selector:
       matchLabels:
         app: web-app
   ```

2. **비용 효율적인 노드 전략**:
   ```yaml
   # 비용 효율적인 노드 그룹 구성
   apiVersion: karpenter.sh/v1
   kind: NodePool
   metadata:
     name: spot-pool
   spec:
     template:
       spec:
         requirements:
           - key: "karpenter.sh/capacity-type"
             operator: In
             values: ["spot"]
           - key: "node.kubernetes.io/instance-type"
             operator: In
             values: ["m5.large", "m5a.large", "m5d.large", "m4.large", "t3.large", "t3a.large"]
         nodeClassRef:
           group: karpenter.k8s.aws
           kind: EC2NodeClass
           name: default
     limits:
       cpu: 1000
       memory: 1000Gi
   ```

3. **워크로드 우선순위 및 선점**:
   ```yaml
   apiVersion: scheduling.k8s.io/v1
   kind: PriorityClass
   metadata:
     name: high-priority
   value: 1000000
   globalDefault: false
   description: High priority pods
   ---
   apiVersion: scheduling.k8s.io/v1
   kind: PriorityClass
   metadata:
     name: low-priority
   value: 10000
   globalDefault: false
   description: Low priority pods
   ---
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: critical-app
   spec:
     template:
       spec:
         priorityClassName: high-priority
         containers:
         - name: critical-app
           image: registry.example.com/team/critical-app:REVIEWED_TAG
       metadata:
         labels:
           app: critical-app
     selector:
       matchLabels:
         app: critical-app
   ```

4. **비용 알림 및 예산 관리**:
   ```bash
   # AWS 예산 알림 설정
   aws budgets create-budget \
     --account-id 123456789012 \
     --budget '{
       "BudgetName": "EKS-Monthly",
       "BudgetLimit": {
         "Amount": "1000",
         "Unit": "USD"
       },
       "CostFilters": {
         "TagKeyValue": [
           "user:kubernetes.io/cluster/my-cluster$owned"
         ]
       },
       "TimeUnit": "MONTHLY",
       "BudgetType": "COST"
     }' \
     --notifications-with-subscribers '[
       {
         "Notification": {
           "NotificationType": "ACTUAL",
           "ComparisonOperator": "GREATER_THAN",
           "Threshold": 80,
           "ThresholdType": "PERCENTAGE"
         },
         "Subscribers": [
           {
             "SubscriptionType": "EMAIL",
             "Address": "team@example.com"
           }
         ]
       }
     ]'
   ```

**추가 구성과 읽기 전용 데이터 예시:**

1. **통합 비용 최적화 아키텍처**:
   ```
   +-------------------+    +-------------------+    +-------------------+
   |                   |    |                   |    |                   |
   |  Kubecost         |    |  AWS Cost         |    |  Custom           |
   |  (K8s 비용 분석)   |    |  Explorer         |    |  Dashboards       |
   |                   |    |                   |    |                   |
   +-------------------+    +-------------------+    +-------------------+
           |                        |                        |
           v                        v                        v
   +---------------------------------------------------------------+
   |                                                               |
   |                  비용 데이터 통합 및 분석                        |
   |                                                               |
   +---------------------------------------------------------------+
           |                        |                        |
           v                        v                        v
   +-------------------+    +-------------------+    +-------------------+
   |                   |    |                   |    |                   |
   |  Karpenter        |    |  HPA/VPA          |    |  Spot Instance    |
   |  (노드 최적화)      |    |  (파드 최적화)      |    |  Management      |
   |                   |    |                   |    |                   |
   +-------------------+    +-------------------+    +-------------------+
           |                        |                        |
           v                        v                        v
   +---------------------------------------------------------------+
   |                                                               |
   |                  EKS 클러스터                                  |
   |                                                               |
   +---------------------------------------------------------------+
   ```

2. **Terraform을 사용한 비용 최적화 인프라 구성**:
   ```hcl
   terraform {
     required_version = ">= 1.5"
     required_providers {
       aws = {
         source  = "hashicorp/aws"
         version = "= 6.64.0"
       }
       helm = {
         source  = "hashicorp/helm"
         version = "= 3.3.0"
       }
     }
   }

   variable "region" { type = string }
   variable "account_id" { type = string }
   variable "kubeconfig_path" { type = string }
   variable "kube_context" { type = string }
   variable "reviewed_kubecost_values_path" { type = string }
   variable "reviewed_karpenter_values_path" { type = string }
   variable "budget_name" { type = string }
   variable "budget_tag_filter" {
     type        = string
     description = "Actual activated Budgets TagKeyValue, for example user:cluster$production."
   }
   variable "notification_email" {
     type        = string
     description = "Approved recipient; applying this configures real notifications."
   }

   provider "aws" {
     region              = var.region
     allowed_account_ids = [var.account_id]
   }

   provider "helm" {
     kubernetes = {
       config_path    = var.kubeconfig_path
       config_context = var.kube_context
     }
   }

   resource "helm_release" "kubecost" {
     name             = "kubecost"
     repository       = "https://kubecost.github.io/kubecost/"
     chart            = "kubecost"
     version          = "3.2.4"
     namespace        = "kubecost"
     create_namespace = true
     values           = [file(var.reviewed_kubecost_values_path)]
     wait             = true
     timeout          = 300
   }

   resource "helm_release" "karpenter" {
     name             = "karpenter"
     repository       = "oci://public.ecr.aws/karpenter"
     chart            = "karpenter"
     version          = "1.14.1"
     namespace        = "karpenter"
     create_namespace = true
     values           = [file(var.reviewed_karpenter_values_path)]
     wait             = true
     timeout          = 300
   }

   resource "aws_budgets_budget" "eks" {
     account_id   = var.account_id
     name         = var.budget_name
     budget_type  = "COST"
     limit_amount = "1000"
     limit_unit   = "USD"
     time_unit    = "MONTHLY"

     cost_filter {
       name   = "TagKeyValue"
       values = [var.budget_tag_filter]
     }
     notification {
       comparison_operator        = "GREATER_THAN"
       threshold                  = 80
       threshold_type             = "PERCENTAGE"
       notification_type          = "ACTUAL"
       subscriber_email_addresses = [var.notification_email]
     }
   }
   ```

3. **비용 최적화 자동화 스크립트**:
```bash
: "${KUBE_CONTEXT:?Select the reviewed OpenCost cluster context}"
# Terminal 1: authorized local access to the OpenCost 1.121.2 service from EKS06.
kubectl --context "$KUBE_CONTEXT" -n opencost port-forward --address 127.0.0.1 svc/opencost 9003:9003
```

```bash
# Terminal 2: preserve the API response; this reads allocation estimates.
curl --fail --silent --show-error --max-time 30 --get \
  http://127.0.0.1:9003/allocation \
  --data-urlencode 'window=1d' \
  --data-urlencode 'aggregate=namespace,controllerKind,controller' \
  --data-urlencode 'accumulate=true' > allocation.json
```

```python
import json
from pathlib import Path

response = json.loads(Path("allocation.json").read_text())
if response.get("code") != 200 or not isinstance(response.get("data"), list):
    raise ValueError("Unexpected allocation API response; do not replace failure with zero")
if not all(isinstance(allocation_set, dict) for allocation_set in response["data"]):
    raise ValueError("Expected an array of allocation-set maps")
if not response["data"] or not any(response["data"]):
    raise SystemExit("No allocation data for the selected window; investigate coverage")
else:
    print("Allocation response shape accepted; review units, window, and coverage before analysis")
```

VPA 예시는 HPA가 CPU/메모리 utilization 분모를 사용하는 동안 Off로 둡니다. 자동 requests 변경은 해당 제어 루프와 조율한 후 활성화합니다. Cluster Proportional Autoscaler는 클러스터 크기 신호로 구성 요소 복제본을 조정하며 노드 프로비저너와 같은 역할이 아닙니다. Karpenter limits·인스턴스 선호·consolidation 지연은 금액 상한이나 종료 시각 보장이 아닙니다. `al2023@latest`를 불변으로 취급하지 말고 실제 AMI를 확인한 뒤 통제된 변경에는 검증한 버전/ID를 고정합니다.

PriorityClass는 스케줄링/선점 우선순위이며 비용 할당이나 가용성을 보장하지 않습니다. priority 지정 권한을 관리하고, 스케줄러 선점의 PDB 준수는 best effort임을 고려하여 disruption·복구를 검토합니다. 비용 관측/권고에서 컨트롤러 동작으로 이어지려면 명시적인 정책/변경 검토 경로가 필요하며 도식 자체가 통합을 구현하지는 않습니다.

Terraform 대안은 Helm provider 3.3.0의 values-file 설정과 AWS provider 6.64.0을 사용합니다. 명시적인 Kubernetes context와 호환 identity·스토리지·라이선스 Secret 참조를 포함한 검토한 values를 제공해야 하며 이런 전제 조건을 생성하지 않습니다. 원문 라이선스/클라우드 자격 증명을 values/state에 넣지 않습니다. 기존 릴리스는 다른 관리자로 중복 설치하지 말고 소유자와 조정합니다. 1,000 USD/80% 예산은 실제 청구 태그 필터를 사용하는 설명용 설정이며 강제 지출 상한이 아닙니다. 이 감사에서는 클러스터/Helm 프로비저닝이나 알림을 실행하지 않았습니다.

아래 API 예시는 추측한 Kubecost 3.x URL이 아닌 앞에서 구성한 OpenCost 1.121.2를 대상으로 합니다. `/allocation`은 `namespace,controllerKind,controller` 집계를 지원하며 `deployment`는 문서화된 일반 집계 키가 아닙니다. 응답 data는 namespace/Deployment를 직접 키로 갖는 객체가 아닌 allocation-set map의 배열입니다. HTTP/API 오류와 수집 범위를 확인하고 빈 결과를 비용 0이나 과다 프로비저닝 증거로 해석하지 않습니다. 할당량·사용량·requests·byte-hours/core-hours·현재 replica 수는 의미와 기간이 다릅니다. 버전별 스키마와 비교 가능한 워크로드 메트릭을 검토한 후 적정 크기를 판단하며 할당 추정치는 청구 및 유휴/공유 비용 정책과 대조해야 합니다.

나머지 선택지는 측정·워크로드 신호 또는 조정 주체를 놓칩니다. 같은 리소스를 여러 컨트롤러가 경쟁해서 변경하면 안정성과 비용 예측을 해칠 수 있습니다.
</details>

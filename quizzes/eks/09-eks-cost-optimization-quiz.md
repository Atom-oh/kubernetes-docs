# Amazon EKS 비용 최적화 퀴즈

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

A. 항상 가장 큰 인스턴스 유형 사용  
B. 모든 워크로드에 온디맨드 인스턴스만 사용  
C. 스팟 인스턴스, 적절한 인스턴스 크기 조정 및 자동 스케일링 결합  
D. 모든 워크로드를 단일 노드 그룹에 통합  

<details>
<summary>정답 및 설명</summary>

**정답: C. 스팟 인스턴스, 적절한 인스턴스 크기 조정 및 자동 스케일링 결합**

**설명:**
Amazon EKS에서 컴퓨팅 비용을 최적화하기 위한 가장 효과적인 전략은 스팟 인스턴스, 적절한 인스턴스 크기 조정 및 자동 스케일링을 결합하는 것입니다. 이 통합 접근 방식은 워크로드 특성에 맞게 비용 효율적인 컴퓨팅 리소스를 제공하면서 성능 요구 사항을 충족합니다.

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

**구현 방법:**

1. **스팟 인스턴스를 사용한 노드 그룹 생성**:
   ```bash
   # eksctl을 사용한 스팟 인스턴스 노드 그룹 생성
   eksctl create nodegroup \
     --cluster my-cluster \
     --name spot-ng \
     --node-type m5.large \
     --nodes-min 2 \
     --nodes-max 10 \
     --spot \
     --asg-access
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
           name: default
     limits:
       resources:
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
     amiFamily: AL2
     role: KarpenterNodeRole
     subnetSelector:
       karpenter.sh/discovery: my-cluster
     securityGroupSelector:
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
       updateMode: "Auto"
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
   - 비용 효율적인 시간대에 실행

**모범 사례:**

1. **리소스 요청 및 제한 최적화**:
   ```yaml
   # 리소스 요청 및 제한 예시
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
   ```

2. **노드 선호도 및 파드 분배 최적화**:
   ```yaml
   # 노드 선호도 및 파드 분배 예시
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
                 topologyKey: "kubernetes.io/hostname"
   ```

3. **스팟 인스턴스 중단 처리**:
   ```yaml
   # 스팟 인스턴스 중단 처리 예시
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
                 command: ["/bin/sh", "-c", "sleep 10; /app/cleanup.sh"]
   ```

**실제 구현 예시:**

1. **비용 효율적인 노드 그룹 구성**:
   ```yaml
   # eksctl 구성 파일
   apiVersion: eksctl.io/v1alpha5
   kind: ClusterConfig
   metadata:
     name: my-cluster
     region: us-west-2
   
   managedNodeGroups:
     # 시스템 워크로드용 온디맨드 노드 그룹
     - name: system-ng
       instanceType: m5.large
       desiredCapacity: 2
       minSize: 2
       maxSize: 4
       labels:
         workload-type: system
       taints:
         dedicated: system:NoSchedule
       iam:
         withAddonPolicies:
           autoScaler: true
   
     # 애플리케이션 워크로드용 스팟 노드 그룹
     - name: app-spot-ng
       instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m4.large"]
       spot: true
       desiredCapacity: 3
       minSize: 1
       maxSize: 10
       labels:
         workload-type: application
       iam:
         withAddonPolicies:
           autoScaler: true
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
       "k8s.io/cluster-autoscaler/enabled" = "true"
       "k8s.io/cluster-autoscaler/${aws_eks_cluster.main.name}" = "owned"
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
             "autoscaling:SetDesiredCapacity",
             "autoscaling:TerminateInstanceInAutoScalingGroup",
             "ec2:DescribeLaunchTemplateVersions"
           ],
           Resource = "*"
         }
       ]
     })
   }
   ```

다른 옵션들의 문제점:
- **A. 항상 가장 큰 인스턴스 유형 사용**: 이는 과도한 프로비저닝으로 이어져 불필요한 비용이 발생하며, 워크로드 요구 사항에 맞지 않을 수 있습니다.
- **B. 모든 워크로드에 온디맨드 인스턴스만 사용**: 온디맨드 인스턴스는 스팟 인스턴스보다 비용이 더 높으며, 많은 워크로드가 스팟 인스턴스에서 효과적으로 실행될 수 있습니다.
- **D. 모든 워크로드를 단일 노드 그룹에 통합**: 다양한 워크로드 요구 사항을 충족하기 어렵고, 리소스 격리가 부족하며, 비용 할당 및 최적화가 어려워집니다.
</details>
### 2. Amazon EKS에서 스토리지 비용을 최적화하기 위한 가장 효과적인 접근 방식은 무엇인가요?

A. 모든 워크로드에 대해 가장 저렴한 스토리지 유형 사용  
B. 모든 데이터를 S3로 마이그레이션  
C. 워크로드 요구 사항에 맞는 스토리지 유형 선택 및 수명 주기 관리 구현  
D. 모든 볼륨 크기를 최소화  

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

**구현 방법:**

1. **EBS 볼륨 최적화**:
   ```yaml
   # gp3 StorageClass 구성
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: ebs-gp3
   provisioner: ebs.csi.aws.com
   parameters:
     type: gp3
     iops: "3000"
     throughput: "125"
   allowVolumeExpansion: true
   ```

2. **EFS 수명 주기 관리**:
   ```bash
   # EFS 파일 시스템 생성 시 수명 주기 정책 설정
   aws efs create-file-system \
     --creation-token eks-efs \
     --performance-mode generalPurpose \
     --throughput-mode bursting \
     --lifecycle-policies '[{"TransitionToIA":"AFTER_30_DAYS"}]'
   ```

3. **S3 수명 주기 정책**:
   ```json
   {
     "Rules": [
       {
         "ID": "Move to IA after 30 days, Glacier after 90 days",
         "Status": "Enabled",
         "Prefix": "eks-backups/",
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
         }
       }
     ]
   }
   ```

4. **EBS 스냅샷 수명 주기 관리**:
   ```yaml
   # VolumeSnapshotClass 구성
   apiVersion: snapshot.storage.k8s.io/v1
   kind: VolumeSnapshotClass
   metadata:
     name: ebs-snapshot
     annotations:
       snapshot.storage.kubernetes.io/is-default-class: "true"
   driver: ebs.csi.aws.com
   deletionPolicy: Delete
   ```

   ```yaml
   # 정기적인 스냅샷 생성을 위한 CronJob
   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: volume-snapshot
   spec:
     schedule: "0 1 * * *"  # 매일 오전 1시
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
                 kubectl create -f /snapshots/snapshot.yaml
             restartPolicy: OnFailure
             volumes:
             - name: snapshots
               configMap:
                 name: snapshot-templates
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
   # 다중 스토리지 클래스 사용 예시
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: hot-data
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
   # 사용되지 않는 PVC 식별
   kubectl get pvc --all-namespaces -o json | jq -r '.items[] | select(.status.phase == "Bound") | select(.metadata.annotations.pv_used == "false") | .metadata.name'
   
   # 사용되지 않는 EBS 볼륨 식별
   aws ec2 describe-volumes \
     --filters Name=status,Values=available \
     --query 'Volumes[*].{ID:VolumeId,Size:Size,Type:VolumeType,State:State,CreateTime:CreateTime}'
   ```

3. **데이터 압축 및 중복 제거**:
   - 로그 및 백업 데이터 압축
   - 중복 데이터 제거 기술 활용
   - 효율적인 데이터 형식 사용

4. **비용 할당 및 태깅**:
   ```yaml
   # 스토리지 리소스에 비용 할당 태그 적용
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: database-data
     labels:
       app: database
       environment: production
       cost-center: cc-123
   spec:
     accessModes:
       - ReadWriteOnce
     storageClassName: ebs-io2
     resources:
       requests:
         storage: 100Gi
   ```

**실제 구현 예시:**

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
   resource "kubernetes_storage_class" "ebs_gp3" {
     metadata {
       name = "ebs-gp3"
     }
     storage_provisioner = "ebs.csi.aws.com"
     parameters = {
       type       = "gp3"
       iops       = "3000"
       throughput = "125"
     }
     allow_volume_expansion = true
   }
   
   # EFS 파일 시스템
   resource "aws_efs_file_system" "eks_efs" {
     creation_token = "eks-efs"
     
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
   import boto3
   import kubernetes
   from kubernetes import client, config
   
   # Kubernetes 클라이언트 설정
   config.load_kube_config()
   v1 = client.CoreV1Api()
   
   # AWS 클라이언트 설정
   ec2 = boto3.client('ec2')
   
   def find_unused_pvcs():
       """사용되지 않는 PVC 식별"""
       pvcs = v1.list_persistent_volume_claim_for_all_namespaces(watch=False)
       unused_pvcs = []
       
       for pvc in pvcs.items:
           # PVC가 바인딩되었지만 사용 중인 파드가 없는지 확인
           pod_list = v1.list_pod_for_all_namespaces(watch=False)
           is_used = False
           
           for pod in pod_list.items:
               for volume in pod.spec.volumes if pod.spec.volumes else []:
                   if hasattr(volume, 'persistent_volume_claim') and volume.persistent_volume_claim.claim_name == pvc.metadata.name:
                       is_used = True
                       break
           
           if not is_used and pvc.status.phase == "Bound":
               unused_pvcs.append({
                   'name': pvc.metadata.name,
                   'namespace': pvc.metadata.namespace,
                   'storage_class': pvc.spec.storage_class_name,
                   'size': pvc.spec.resources.requests.get('storage', 'Unknown')
               })
       
       return unused_pvcs
   
   def find_unused_ebs_volumes():
       """사용되지 않는 EBS 볼륨 식별"""
       volumes = ec2.describe_volumes(
           Filters=[
               {'Name': 'status', 'Values': ['available']},
               {'Name': 'tag:kubernetes.io/created-for/pvc/name', 'Values': ['*']}
           ]
       )
       
       return volumes['Volumes']
   
   # 메인 함수
   def main():
       unused_pvcs = find_unused_pvcs()
       unused_volumes = find_unused_ebs_volumes()
       
       print(f"Found {len(unused_pvcs)} unused PVCs")
       for pvc in unused_pvcs:
           print(f"  - {pvc['namespace']}/{pvc['name']} ({pvc['size']})")
       
       print(f"Found {len(unused_volumes)} unused EBS volumes")
       for volume in unused_volumes:
           print(f"  - {volume['VolumeId']} ({volume['Size']} GB, {volume['VolumeType']})")
   
   if __name__ == "__main__":
       main()
   ```

다른 옵션들의 문제점:
- **A. 모든 워크로드에 대해 가장 저렴한 스토리지 유형 사용**: 가장 저렴한 스토리지는 성능 요구 사항을 충족하지 못할 수 있으며, 이로 인해 애플리케이션 성능 저하 및 비즈니스 영향이 발생할 수 있습니다.
- **B. 모든 데이터를 S3로 마이그레이션**: S3는 일부 데이터 유형에 적합하지만, 지연 시간에 민감한 워크로드나 블록 스토리지가 필요한 애플리케이션에는 적합하지 않습니다.
- **D. 모든 볼륨 크기를 최소화**: 볼륨 크기를 과도하게 최소화하면 공간 부족 문제가 발생할 수 있으며, 일부 볼륨 유형(예: gp2)은 크기에 따라 성능이 결정됩니다.
</details>
### 3. Amazon EKS에서 네트워킹 비용을 최적화하기 위한 가장 효과적인 전략은 무엇인가요?

A. 모든 트래픽에 대해 가장 비싼 네트워크 대역폭 사용  
B. 모든 서비스를 단일 가용 영역에 배치  
C. 트래픽 패턴 최적화, 데이터 전송 비용 최소화 및 VPC 엔드포인트 활용  
D. 모든 네트워크 트래픽 차단  

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

**구현 방법:**

1. **가용 영역 인식 파드 배치**:
   ```yaml
   # 토폴로지 분산 제약 조건을 사용한 배포
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
   ```

2. **서비스 토폴로지 라우팅**:
   ```yaml
   # 토폴로지 인식 서비스 구성
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
     topologyKeys:
     - "kubernetes.io/hostname"
     - "topology.kubernetes.io/zone"
     - "*"
   ```

3. **VPC 엔드포인트 구성**:
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
     --security-group-ids sg-12345678
   ```

4. **Istio를 사용한 로컬리티 라우팅**:
   ```yaml
   # Istio 로컬리티 라우팅 구성
   apiVersion: networking.istio.io/v1alpha3
   kind: DestinationRule
   metadata:
     name: web-app
   spec:
     host: web-app
     trafficPolicy:
       loadBalancer:
         localityLbSetting:
           enabled: true
           failover:
           - from: us-west-2a
             to: us-west-2b
           - from: us-west-2b
             to: us-west-2c
           - from: us-west-2c
             to: us-west-2a
   ```

**네트워크 비용 구성 요소 및 최적화:**

1. **가용 영역 간 데이터 전송**:
   - 비용: GB당 요금 부과
   - 최적화: 동일 가용 영역 내 통신 우선, 필요한 경우에만 가용 영역 간 통신

2. **리전 간 데이터 전송**:
   - 비용: 더 높은 GB당 요금
   - 최적화: 리전 간 트래픽 최소화, 필요한 경우 데이터 복제

3. **인터넷 아웃바운드 트래픽**:
   - 비용: 가장 높은 GB당 요금
   - 최적화: CloudFront 사용, 압축, 캐싱

4. **NAT 게이트웨이 비용**:
   - 비용: 시간당 요금 + 데이터 처리 요금
   - 최적화: VPC 엔드포인트 사용, NAT 게이트웨이 공유

**모범 사례:**

1. **네트워크 토폴로지 최적화**:
   ```yaml
   # 노드 선호도를 사용한 파드 배치
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
   ```

2. **네트워크 정책을 통한 불필요한 트래픽 제한**:
   ```yaml
   # 네트워크 정책 예시
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
   ```

3. **서비스 메시를 통한 트래픽 최적화**:
   ```yaml
   # Istio 가상 서비스 구성
   apiVersion: networking.istio.io/v1alpha3
   kind: VirtualService
   metadata:
     name: api-service
   spec:
     hosts:
     - api-service
     http:
     - route:
       - destination:
           host: api-service
           subset: v1
         weight: 90
       - destination:
           host: api-service
           subset: v2
         weight: 10
     - match:
       - headers:
           end-user:
             exact: premium-user
       route:
       - destination:
           host: api-service
           subset: premium
   ```

4. **데이터 압축 및 효율적인 프로토콜 사용**:
   ```yaml
   # 데이터 압축을 위한 Envoy 필터
   apiVersion: networking.istio.io/v1alpha3
   kind: EnvoyFilter
   metadata:
     name: compression-filter
   spec:
     configPatches:
     - applyTo: HTTP_FILTER
       match:
         context: SIDECAR_OUTBOUND
         listener:
           filterChain:
             filter:
               name: envoy.http_connection_manager
       patch:
         operation: INSERT_BEFORE
         value:
           name: envoy.filters.http.compressor
           typed_config:
             "@type": type.googleapis.com/envoy.extensions.filters.http.compressor.v3.Compressor
             content_length: 100
             content_type:
             - application/json
             - text/html
             compressor_library:
               name: gzip
               typed_config:
                 "@type": type.googleapis.com/envoy.extensions.compression.gzip.compressor.v3.Gzip
                 memory_level: 3
                 window_bits: 10
                 compression_level: BEST_COMPRESSION
                 compression_strategy: DEFAULT_STRATEGY
   ```

**실제 구현 예시:**

1. **비용 효율적인 네트워크 아키텍처**:
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

2. **Terraform을 사용한 네트워크 최적화 인프라 구성**:
   ```hcl
   # VPC 엔드포인트 구성
   resource "aws_vpc_endpoint" "s3" {
     vpc_id       = aws_vpc.main.id
     service_name = "com.amazonaws.${var.region}.s3"
     route_table_ids = [aws_route_table.private.id]
     vpc_endpoint_type = "Gateway"
     
     tags = {
       Name = "s3-endpoint"
     }
   }
   
   resource "aws_vpc_endpoint" "dynamodb" {
     vpc_id       = aws_vpc.main.id
     service_name = "com.amazonaws.${var.region}.dynamodb"
     route_table_ids = [aws_route_table.private.id]
     vpc_endpoint_type = "Gateway"
     
     tags = {
       Name = "dynamodb-endpoint"
     }
   }
   
   # 인터페이스 VPC 엔드포인트
   resource "aws_vpc_endpoint" "ecr_api" {
     vpc_id            = aws_vpc.main.id
     service_name      = "com.amazonaws.${var.region}.ecr.api"
     vpc_endpoint_type = "Interface"
     subnet_ids        = aws_subnet.private[*].id
     security_group_ids = [aws_security_group.vpc_endpoints.id]
     private_dns_enabled = true
     
     tags = {
       Name = "ecr-api-endpoint"
     }
   }
   
   resource "aws_vpc_endpoint" "ecr_dkr" {
     vpc_id            = aws_vpc.main.id
     service_name      = "com.amazonaws.${var.region}.ecr.dkr"
     vpc_endpoint_type = "Interface"
     subnet_ids        = aws_subnet.private[*].id
     security_group_ids = [aws_security_group.vpc_endpoints.id]
     private_dns_enabled = true
     
     tags = {
       Name = "ecr-dkr-endpoint"
     }
   }
   
   # NAT 게이트웨이 최적화 (단일 NAT 게이트웨이 사용)
   resource "aws_nat_gateway" "main" {
     allocation_id = aws_eip.nat.id
     subnet_id     = aws_subnet.public[0].id
     
     tags = {
       Name = "main-nat-gateway"
     }
   }
   
   # 모든 프라이빗 서브넷이 단일 NAT 게이트웨이 사용
   resource "aws_route_table" "private" {
     vpc_id = aws_vpc.main.id
     
     route {
       cidr_block     = "0.0.0.0/0"
       nat_gateway_id = aws_nat_gateway.main.id
     }
     
     tags = {
       Name = "private-route-table"
     }
   }
   ```

3. **네트워크 비용 모니터링 및 최적화 스크립트**:
   ```python
   import boto3
   import datetime
   
   # AWS 클라이언트 설정
   ce = boto3.client('ce')  # Cost Explorer
   
   def get_network_costs(start_date, end_date):
       """네트워크 관련 비용 조회"""
       response = ce.get_cost_and_usage(
           TimePeriod={
               'Start': start_date,
               'End': end_date
           },
           Granularity='DAILY',
           Metrics=['UnblendedCost'],
           GroupBy=[
               {
                   'Type': 'DIMENSION',
                   'Key': 'SERVICE'
               },
               {
                   'Type': 'DIMENSION',
                   'Key': 'USAGE_TYPE'
               }
           ],
           Filter={
               'And': [
                   {
                       'Dimensions': {
                           'Key': 'SERVICE',
                           'Values': [
                               'Amazon Virtual Private Cloud',
                               'Amazon Elastic Compute Cloud',
                               'Amazon CloudFront'
                           ]
                       }
                   },
                   {
                       'Dimensions': {
                           'Key': 'USAGE_TYPE',
                           'Values': [
                               'DataTransfer-Out-Bytes',
                               'DataTransfer-Regional-Bytes',
                               'NatGateway-Bytes',
                               'VpcEndpoint-Hours'
                           ],
                           'MatchOptions': ['CONTAINS']
                       }
                   }
               ]
           }
       )
       
       return response['ResultsByTime']
   
   # 메인 함수
   def main():
       # 지난 30일 데이터 조회
       end_date = datetime.datetime.now().strftime('%Y-%m-%d')
       start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
       
       network_costs = get_network_costs(start_date, end_date)
       
       # 비용 분석 및 최적화 권장 사항
       analyze_costs(network_costs)
   
   def analyze_costs(network_costs):
       """네트워크 비용 분석 및 최적화 권장 사항 제공"""
       nat_gateway_costs = 0
       data_transfer_az_costs = 0
       data_transfer_region_costs = 0
       data_transfer_internet_costs = 0
       
       for day in network_costs:
           for group in day['Groups']:
               service = group['Keys'][0]
               usage_type = group['Keys'][1]
               cost = float(group['Metrics']['UnblendedCost']['Amount'])
               
               if 'NatGateway' in usage_type:
                   nat_gateway_costs += cost
               elif 'DataTransfer' in usage_type and 'Regional' in usage_type:
                   data_transfer_az_costs += cost
               elif 'DataTransfer' in usage_type and 'Region' in usage_type:
                   data_transfer_region_costs += cost
               elif 'DataTransfer-Out' in usage_type:
                   data_transfer_internet_costs += cost
       
       print(f"NAT Gateway costs: ${nat_gateway_costs:.2f}")
       print(f"AZ data transfer costs: ${data_transfer_az_costs:.2f}")
       print(f"Region data transfer costs: ${data_transfer_region_costs:.2f}")
       print(f"Internet data transfer costs: ${data_transfer_internet_costs:.2f}")
       
       # 최적화 권장 사항
       if nat_gateway_costs > 100:
           print("Consider using VPC endpoints to reduce NAT Gateway costs")
       
       if data_transfer_az_costs > 50:
           print("Consider optimizing pod placement to reduce cross-AZ traffic")
       
       if data_transfer_internet_costs > 200:
           print("Consider using CloudFront or implementing compression to reduce internet data transfer costs")
   
   if __name__ == "__main__":
       main()
   ```

다른 옵션들의 문제점:
- **A. 모든 트래픽에 대해 가장 비싼 네트워크 대역폭 사용**: 이는 불필요한 비용을 발생시키며, 모든 워크로드가 고대역폭을 필요로 하지는 않습니다.
- **B. 모든 서비스를 단일 가용 영역에 배치**: 이는 가용성과 내결함성을 크게 저하시키며, AWS의 고가용성 설계 원칙에 위배됩니다.
- **D. 모든 네트워크 트래픽 차단**: 이는 실용적이지 않으며, 애플리케이션 기능을 심각하게 제한합니다.
</details>
### 4. Amazon EKS 클러스터 관리 비용을 최적화하기 위한 가장 효과적인 접근 방식은 무엇인가요?

A. 가능한 한 많은 클러스터 생성  
B. 모든 워크로드를 단일 클러스터에 통합  
C. 워크로드 요구 사항에 따라 클러스터 수를 최적화하고 관리 오버헤드 최소화  
D. 클러스터를 수동으로 관리  

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

**구현 방법:**

1. **EKS 클러스터 최적화 구성**:
   ```bash
   # eksctl을 사용한 최적화된 클러스터 생성
   eksctl create cluster \
     --name optimized-cluster \
     --region us-west-2 \
     --version 1.28 \
     --nodegroup-name standard-workers \
     --node-type m5.large \
     --nodes-min 2 \
     --nodes-max 10 \
     --managed \
     --asg-access \
     --external-dns-access \
     --full-ecr-access \
     --appmesh-access \
     --alb-ingress-access
   ```

2. **Terraform을 사용한 클러스터 관리 자동화**:
   ```hcl
   module "eks" {
     source  = "terraform-aws-modules/eks/aws"
     version = "~> 19.0"
     
     cluster_name    = "optimized-cluster"
     cluster_version = "1.28"
     
     cluster_endpoint_public_access  = true
     cluster_endpoint_private_access = true
     
     cluster_addons = {
       coredns = {
         most_recent = true
       }
       kube-proxy = {
         most_recent = true
       }
       vpc-cni = {
         most_recent = true
       }
     }
     
     vpc_id     = module.vpc.vpc_id
     subnet_ids = module.vpc.private_subnets
     
     eks_managed_node_groups = {
       general = {
         min_size     = 1
         max_size     = 10
         desired_size = 2
         
         instance_types = ["m5.large"]
         capacity_type  = "ON_DEMAND"
       }
       
       spot = {
         min_size     = 1
         max_size     = 10
         desired_size = 2
         
         instance_types = ["m5.large", "m5a.large", "m5d.large", "m4.large"]
         capacity_type  = "SPOT"
       }
     }
     
     tags = {
       Environment = "production"
       Terraform   = "true"
     }
   }
   ```

3. **GitOps를 사용한 클러스터 구성 관리**:
   ```yaml
   # ArgoCD Application 예시
   apiVersion: argoproj.io/v1alpha1
   kind: Application
   metadata:
     name: cluster-config
     namespace: argocd
   spec:
     project: default
     source:
       repoURL: https://github.com/myorg/cluster-config.git
       targetRevision: HEAD
       path: configs
     destination:
       server: https://kubernetes.default.svc
       namespace: default
     syncPolicy:
       automated:
         prune: true
         selfHeal: true
       syncOptions:
       - CreateNamespace=true
   ```

4. **다중 테넌트 클러스터 구성**:
   ```yaml
   # 네임스페이스 리소스 할당량
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: team-a-quota
     namespace: team-a
   spec:
     hard:
       requests.cpu: "10"
       requests.memory: 20Gi
       limits.cpu: "20"
       limits.memory: 40Gi
       pods: "50"
       services: "20"
       persistentvolumeclaims: "30"
       
   # 네임스페이스 네트워크 정책
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
       - namespaceSelector:
           matchLabels:
             name: team-a
       - namespaceSelector:
           matchLabels:
             name: shared-services
     egress:
     - to:
       - namespaceSelector: {}
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
   ```bash
   # AWS Cost Explorer를 사용한 클러스터별 비용 분석
   aws ce get-cost-and-usage \
     --time-period Start=2023-01-01,End=2023-01-31 \
     --granularity MONTHLY \
     --metrics "BlendedCost" "UnblendedCost" "UsageQuantity" \
     --group-by Type=TAG,Key=kubernetes.io/cluster/cluster-name
   ```

2. **클러스터 자동화 및 IaC 구현**:
   - 모든 클러스터 구성을 코드로 관리
   - 자동화된 배포 및 업데이트 파이프라인
   - 일관된 구성 및 정책 적용

3. **공유 서비스 모델 구현**:
   ```yaml
   # 공유 서비스 네임스페이스 구성
   apiVersion: v1
   kind: Namespace
   metadata:
     name: shared-services
     labels:
       name: shared-services
       access: global
   
   # 공유 서비스에 대한 네트워크 정책
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: allow-from-all-namespaces
     namespace: shared-services
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     ingress:
     - from:
       - namespaceSelector: {}
   ```

4. **클러스터 수명 주기 관리**:
   - 정기적인 클러스터 평가 및 최적화
   - 사용하지 않는 클러스터 식별 및 제거
   - 클러스터 통합 기회 모색

**실제 구현 예시:**

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
   # 환경별 클러스터 모듈
   module "eks_prod" {
     source = "./modules/eks-cluster"
     
     cluster_name    = "production"
     cluster_version = "1.28"
     vpc_id          = module.vpc.vpc_id
     subnet_ids      = module.vpc.private_subnets
     
     node_groups = {
       critical = {
         instance_types = ["m5.large"]
         capacity_type  = "ON_DEMAND"
         min_size       = 3
         max_size       = 10
       },
       general = {
         instance_types = ["m5.large", "m5a.large"]
         capacity_type  = "SPOT"
         min_size       = 3
         max_size       = 20
       }
     }
     
     tags = {
       Environment = "production"
     }
   }
   
   module "eks_dev" {
     source = "./modules/eks-cluster"
     
     cluster_name    = "development"
     cluster_version = "1.28"
     vpc_id          = module.vpc.vpc_id
     subnet_ids      = module.vpc.private_subnets
     
     node_groups = {
       default = {
         instance_types = ["m5.large"]
         capacity_type  = "SPOT"
         min_size       = 1
         max_size       = 5
       }
     }
     
     tags = {
       Environment = "development"
     }
   }
   ```

3. **클러스터 비용 모니터링 및 최적화 스크립트**:
   ```python
   import boto3
   import kubernetes
   from kubernetes import client, config
   
   # Kubernetes 클라이언트 설정
   config.load_kube_config()
   v1 = client.CoreV1Api()
   
   # AWS 클라이언트 설정
   ce = boto3.client('ce')
   
   def get_cluster_costs(cluster_name, start_date, end_date):
       """클러스터별 비용 조회"""
       response = ce.get_cost_and_usage(
           TimePeriod={
               'Start': start_date,
               'End': end_date
           },
           Granularity='MONTHLY',
           Metrics=['UnblendedCost'],
           GroupBy=[
               {
                   'Type': 'TAG',
                   'Key': f'kubernetes.io/cluster/{cluster_name}'
               }
           ]
       )
       
       return response['ResultsByTime']
   
   def get_cluster_utilization(cluster_name):
       """클러스터 리소스 활용도 분석"""
       # 노드 리소스 사용량 조회
       nodes = v1.list_node().items
       total_cpu_capacity = 0
       total_memory_capacity = 0
       total_cpu_requests = 0
       total_memory_requests = 0
       
       for node in nodes:
           cpu_capacity = kubernetes.utils.parse_quantity(node.status.capacity['cpu'])
           memory_capacity = kubernetes.utils.parse_quantity(node.status.capacity['memory'])
           total_cpu_capacity += cpu_capacity
           total_memory_capacity += memory_capacity
       
       # 파드 리소스 요청 조회
       pods = v1.list_pod_for_all_namespaces().items
       for pod in pods:
           for container in pod.spec.containers:
               if container.resources.requests:
                   if 'cpu' in container.resources.requests:
                       total_cpu_requests += kubernetes.utils.parse_quantity(container.resources.requests['cpu'])
                   if 'memory' in container.resources.requests:
                       total_memory_requests += kubernetes.utils.parse_quantity(container.resources.requests['memory'])
       
       # 활용도 계산
       cpu_utilization = (total_cpu_requests / total_cpu_capacity) * 100 if total_cpu_capacity > 0 else 0
       memory_utilization = (total_memory_requests / total_memory_capacity) * 100 if total_memory_capacity > 0 else 0
       
       return {
           'cpu_utilization': cpu_utilization,
           'memory_utilization': memory_utilization
       }
   
   # 메인 함수
   def main():
       clusters = ['production', 'development', 'staging']
       start_date = '2023-01-01'
       end_date = '2023-01-31'
       
       for cluster in clusters:
           # 비용 분석
           costs = get_cluster_costs(cluster, start_date, end_date)
           
           # 활용도 분석
           utilization = get_cluster_utilization(cluster)
           
           # 최적화 권장 사항
           print(f"Cluster: {cluster}")
           print(f"Cost: ${costs[0]['Groups'][0]['Metrics']['UnblendedCost']['Amount']}")
           print(f"CPU Utilization: {utilization['cpu_utilization']:.2f}%")
           print(f"Memory Utilization: {utilization['memory_utilization']:.2f}%")
           
           if utilization['cpu_utilization'] < 30 or utilization['memory_utilization'] < 30:
               print("Recommendation: Consider downsizing cluster or consolidating workloads")
           
           print("---")
   
   if __name__ == "__main__":
       main()
   ```

다른 옵션들의 문제점:
- **A. 가능한 한 많은 클러스터 생성**: 이는 각 클러스터에 대한 컨트롤 플레인 비용과 관리 오버헤드를 증가시키며, 리소스 활용도를 저하시킵니다.
- **B. 모든 워크로드를 단일 클러스터에 통합**: 이는 일부 환경에서 적합할 수 있지만, 보안 요구 사항, 워크로드 격리, 장애 영향 범위 등을 고려하지 않습니다.
- **D. 클러스터를 수동으로 관리**: 수동 관리는 오류 가능성을 높이고, 일관성을 저하시키며, 운영 오버헤드를 증가시킵니다.
</details>
### 5. Amazon EKS에서 비용 모니터링 및 할당을 위한 가장 효과적인 접근 방식은 무엇인가요?

A. AWS 청구서만 검토  
B. 태그 지정 전략, 비용 할당 도구 및 지속적인 모니터링 구현  
C. 모든 리소스에 동일한 비용 할당  
D. 비용 모니터링 없이 리소스 사용  

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

**구현 방법:**

1. **태그 지정 전략 구현**:
   ```yaml
   # 네임스페이스 태그 지정
   apiVersion: v1
   kind: Namespace
   metadata:
     name: team-a
     labels:
       team: team-a
       cost-center: cc-123
       environment: production
       project: project-x
   
   # 배포에 태그 지정
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
   ```bash
   # Helm을 사용하여 Kubecost 설치
   helm repo add kubecost https://kubecost.github.io/cost-analyzer/
   helm install kubecost kubecost/cost-analyzer \
     --namespace kubecost \
     --create-namespace \
     --set kubecostToken="<YOUR_KUBECOST_TOKEN>" \
     --set prometheus.server.persistentVolume.size=100Gi \
     --set prometheus.nodeExporter.enabled=true \
     --set serviceMonitor.enabled=true
   ```

4. **AWS Cost Explorer 보고서 설정**:
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
   aws resourcegroupstaggingapi tag-resources \
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
   # 리소스 요청 및 제한 설정
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
   ```

4. **정기적인 비용 검토 및 최적화**:
   - 주간/월간 비용 검토 회의
   - 비용 추세 및 이상 분석
   - 최적화 조치 추적 및 영향 측정

**실제 구현 예시:**

1. **비용 모니터링 대시보드**:
   ```yaml
   # Grafana 대시보드 구성
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: cost-dashboard
     namespace: monitoring
   data:
     cost-dashboard.json: |
       {
         "title": "EKS Cost Dashboard",
         "panels": [
           {
             "title": "Cost by Namespace",
             "type": "bar",
             "datasource": "Prometheus",
             "targets": [
               {
                 "expr": "sum(kube_pod_container_resource_requests_cpu_cores * on(node) group_left() node_cpu_hourly_cost) by (namespace)",
                 "legendFormat": "{{namespace}}"
               }
             ]
           },
           {
             "title": "Cost by Team",
             "type": "pie",
             "datasource": "Prometheus",
             "targets": [
               {
                 "expr": "sum(kube_pod_container_resource_requests_cpu_cores * on(node) group_left() node_cpu_hourly_cost) by (label_team)",
                 "legendFormat": "{{label_team}}"
               }
             ]
           }
         ]
       }
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
     bucket = "eks-cost-athena-results"
     
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
   
   # QuickSight 대시보드 (Terraform에서 직접 지원하지 않음)
   # AWS CLI 또는 콘솔을 통해 구성
   ```

4. **비용 최적화 자동화 스크립트**:
   ```python
   import boto3
   import kubernetes
   from kubernetes import client, config
   import pandas as pd
   from datetime import datetime, timedelta
   
   # Kubernetes 클라이언트 설정
   config.load_kube_config()
   v1 = client.CoreV1Api()
   
   # AWS 클라이언트 설정
   ce = boto3.client('ce')
   
   def get_cost_by_tag(tag_key, start_date, end_date):
       """태그별 비용 조회"""
       response = ce.get_cost_and_usage(
           TimePeriod={
               'Start': start_date,
               'End': end_date
           },
           Granularity='MONTHLY',
           Metrics=['UnblendedCost'],
           GroupBy=[
               {
                   'Type': 'TAG',
                   'Key': tag_key
               }
           ]
       )
       
       return response['ResultsByTime']
   
   def get_namespace_resource_usage():
       """네임스페이스별 리소스 사용량 조회"""
       namespaces = v1.list_namespace().items
       namespace_usage = []
       
       for ns in namespaces:
           ns_name = ns.metadata.name
           pods = v1.list_namespaced_pod(ns_name).items
           
           cpu_requests = 0
           memory_requests = 0
           cpu_limits = 0
           memory_limits = 0
           
           for pod in pods:
               for container in pod.spec.containers:
                   if container.resources.requests:
                       if 'cpu' in container.resources.requests:
                           cpu_requests += kubernetes.utils.parse_quantity(container.resources.requests['cpu'])
                       if 'memory' in container.resources.requests:
                           memory_requests += kubernetes.utils.parse_quantity(container.resources.requests['memory'])
                   
                   if container.resources.limits:
                       if 'cpu' in container.resources.limits:
                           cpu_limits += kubernetes.utils.parse_quantity(container.resources.limits['cpu'])
                       if 'memory' in container.resources.limits:
                           memory_limits += kubernetes.utils.parse_quantity(container.resources.limits['memory'])
           
           namespace_usage.append({
               'namespace': ns_name,
               'cpu_requests': cpu_requests,
               'memory_requests': memory_requests,
               'cpu_limits': cpu_limits,
               'memory_limits': memory_limits,
               'team': ns.metadata.labels.get('team', 'unknown') if ns.metadata.labels else 'unknown',
               'cost_center': ns.metadata.labels.get('cost-center', 'unknown') if ns.metadata.labels else 'unknown'
           })
       
       return namespace_usage
   
   # 메인 함수
   def main():
       # 날짜 범위 설정
       end_date = datetime.now().strftime('%Y-%m-%d')
       start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
       
       # 태그별 비용 조회
       team_costs = get_cost_by_tag('team', start_date, end_date)
       env_costs = get_cost_by_tag('environment', start_date, end_date)
       
       # 네임스페이스별 리소스 사용량 조회
       namespace_usage = get_namespace_resource_usage()
       
       # 데이터 분석 및 보고서 생성
       df = pd.DataFrame(namespace_usage)
       team_summary = df.groupby('team').sum()
       cost_center_summary = df.groupby('cost_center').sum()
       
       print("Resource Usage by Team:")
       print(team_summary)
       print("\nResource Usage by Cost Center:")
       print(cost_center_summary)
       
       # 최적화 권장 사항
       print("\nOptimization Recommendations:")
       for ns in namespace_usage:
           cpu_ratio = ns['cpu_requests'] / ns['cpu_limits'] if ns['cpu_limits'] > 0 else 0
           memory_ratio = ns['memory_requests'] / ns['memory_limits'] if ns['memory_limits'] > 0 else 0
           
           if cpu_ratio < 0.5:
               print(f"Namespace {ns['namespace']} has low CPU request to limit ratio ({cpu_ratio:.2f}). Consider adjusting requests.")
           
           if memory_ratio < 0.5:
               print(f"Namespace {ns['namespace']} has low memory request to limit ratio ({memory_ratio:.2f}). Consider adjusting requests.")
   
   if __name__ == "__main__":
       main()
   ```

다른 옵션들의 문제점:
- **A. AWS 청구서만 검토**: AWS 청구서는 높은 수준의 비용 정보만 제공하며, 세부적인 비용 할당이나 최적화 기회를 식별하기 어렵습니다.
- **C. 모든 리소스에 동일한 비용 할당**: 이는 실제 리소스 사용량과 비용 발생을 정확하게 반영하지 않으며, 팀이나 프로젝트별 비용 책임을 명확히 하지 못합니다.
- **D. 비용 모니터링 없이 리소스 사용**: 비용 모니터링 없이는 비용 증가를 조기에 감지하거나 최적화 기회를 식별할 수 없으며, 예산 관리가 어렵습니다.
</details>
### 6. Amazon EKS에서 비용 최적화를 위한 가장 효과적인 도구 조합은 무엇인가요?

A. 수동 리소스 관리만 사용  
B. AWS Cost Explorer만 사용  
C. Kubecost, Karpenter, AWS Cost Explorer 및 Kubernetes 자동 스케일링 도구 통합  
D. 타사 비용 관리 도구만 사용  

<details>
<summary>정답 및 설명</summary>

**정답: C. Kubecost, Karpenter, AWS Cost Explorer 및 Kubernetes 자동 스케일링 도구 통합**

**설명:**
Amazon EKS에서 비용 최적화를 위한 가장 효과적인 도구 조합은 Kubecost, Karpenter, AWS Cost Explorer 및 Kubernetes 자동 스케일링 도구를 통합하는 것입니다. 이 통합 접근 방식은 클러스터 수준, 워크로드 수준 및 인프라 수준에서 비용을 최적화하고, 가시성을 제공하며, 자동화된 최적화를 가능하게 합니다.

**주요 비용 최적화 도구 및 기능:**

1. **Kubecost**:
   - Kubernetes 리소스 비용 가시성
   - 네임스페이스, 배포, 서비스별 비용 할당
   - 비용 최적화 권장 사항
   - 비용 예측 및 예산 관리

2. **Karpenter**:
   - 지능적인 노드 프로비저닝 및 관리
   - 워크로드 요구 사항에 맞는 최적의 인스턴스 선택
   - 빠른 스케일링 및 효율적인 리소스 활용
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
   ```bash
   # Helm을 사용하여 Kubecost 설치
   helm repo add kubecost https://kubecost.github.io/cost-analyzer/
   helm install kubecost kubecost/cost-analyzer \
     --namespace kubecost \
     --create-namespace \
     --set kubecostToken="<YOUR_KUBECOST_TOKEN>" \
     --set prometheus.server.persistentVolume.size=100Gi \
     --set prometheus.nodeExporter.enabled=true \
     --set serviceMonitor.enabled=true
   ```

2. **Karpenter 설치 및 구성**:
   ```bash
   # Karpenter 설치
   helm repo add karpenter https://charts.karpenter.sh
   helm upgrade --install karpenter karpenter/karpenter \
     --namespace karpenter \
     --create-namespace \
     --set serviceAccount.create=true \
     --set serviceAccount.name=karpenter \
     --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"="arn:aws:iam::123456789012:role/KarpenterControllerRole" \
     --set controller.clusterName=my-cluster \
     --set controller.clusterEndpoint=$(aws eks describe-cluster --name my-cluster --query "cluster.endpoint" --output text)
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
           name: default
     limits:
       resources:
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
     amiFamily: AL2
     role: KarpenterNodeRole
     subnetSelector:
       karpenter.sh/discovery: my-cluster
     securityGroupSelector:
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
       updateMode: "Auto"
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
   # VPA 권장 사항 기반 리소스 설정
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
           name: default
     limits:
       resources:
         cpu: 1000
         memory: 1000Gi
   ```

3. **워크로드 우선순위 및 선점**:
   ```yaml
   # 우선순위 클래스 정의
   apiVersion: scheduling.k8s.io/v1
   kind: PriorityClass
   metadata:
     name: high-priority
   value: 1000000
   globalDefault: false
   description: "High priority pods"
   ---
   apiVersion: scheduling.k8s.io/v1
   kind: PriorityClass
   metadata:
     name: low-priority
   value: 10000
   globalDefault: false
   description: "Low priority pods"
   
   # 우선순위 클래스 적용
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: critical-app
   spec:
     template:
       spec:
         priorityClassName: high-priority
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

**실제 구현 예시:**

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
   # Kubecost 설치
   resource "helm_release" "kubecost" {
     name       = "kubecost"
     repository = "https://kubecost.github.io/cost-analyzer/"
     chart      = "cost-analyzer"
     namespace  = "kubecost"
     create_namespace = true
     
     set {
       name  = "kubecostToken"
       value = var.kubecost_token
     }
     
     set {
       name  = "prometheus.server.persistentVolume.size"
       value = "100Gi"
     }
     
     set {
       name  = "prometheus.nodeExporter.enabled"
       value = "true"
     }
   }
   
   # Karpenter 설치
   resource "helm_release" "karpenter" {
     name       = "karpenter"
     repository = "https://charts.karpenter.sh"
     chart      = "karpenter"
     namespace  = "karpenter"
     create_namespace = true
     
     set {
       name  = "serviceAccount.create"
       value = "true"
     }
     
     set {
       name  = "serviceAccount.name"
       value = "karpenter"
     }
     
     set {
       name  = "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
       value = aws_iam_role.karpenter_controller.arn
     }
     
     set {
       name  = "controller.clusterName"
       value = var.cluster_name
     }
     
     set {
       name  = "controller.clusterEndpoint"
       value = data.aws_eks_cluster.cluster.endpoint
     }
   }
   
   # AWS 예산 설정
   resource "aws_budgets_budget" "eks" {
     name              = "eks-monthly-budget"
     budget_type       = "COST"
     limit_amount      = "1000"
     limit_unit        = "USD"
     time_unit         = "MONTHLY"
     time_period_start = "2023-01-01_00:00"
     
     cost_filter {
       name = "TagKeyValue"
       values = [
         "kubernetes.io/cluster/${var.cluster_name}$owned"
       ]
     }
     
     notification {
       comparison_operator        = "GREATER_THAN"
       threshold                  = 80
       threshold_type             = "PERCENTAGE"
       notification_type          = "ACTUAL"
       subscriber_email_addresses = ["team@example.com"]
     }
   }
   ```

3. **비용 최적화 자동화 스크립트**:
   ```python
   import boto3
   import kubernetes
   import requests
   import json
   from kubernetes import client, config
   
   # Kubernetes 클라이언트 설정
   config.load_kube_config()
   v1 = client.CoreV1Api()
   apps_v1 = client.AppsV1Api()
   
   # AWS 클라이언트 설정
   ec2 = boto3.client('ec2')
   ce = boto3.client('ce')
   
   def get_underutilized_nodes():
       """활용도가 낮은 노드 식별"""
       nodes = v1.list_node().items
       underutilized = []
       
       for node in nodes:
           # 노드 리소스 용량 및 할당 가능 리소스 조회
           capacity_cpu = kubernetes.utils.parse_quantity(node.status.capacity['cpu'])
           capacity_memory = kubernetes.utils.parse_quantity(node.status.capacity['memory'])
           allocatable_cpu = kubernetes.utils.parse_quantity(node.status.allocatable['cpu'])
           allocatable_memory = kubernetes.utils.parse_quantity(node.status.allocatable['memory'])
           
           # 노드에 스케줄된 파드 조회
           field_selector = f'spec.nodeName={node.metadata.name}'
           pods = v1.list_pod_for_all_namespaces(field_selector=field_selector).items
           
           # 파드 리소스 요청 합계 계산
           total_cpu_requests = 0
           total_memory_requests = 0
           
           for pod in pods:
               for container in pod.spec.containers:
                   if container.resources.requests:
                       if 'cpu' in container.resources.requests:
                           total_cpu_requests += kubernetes.utils.parse_quantity(container.resources.requests['cpu'])
                       if 'memory' in container.resources.requests:
                           total_memory_requests += kubernetes.utils.parse_quantity(container.resources.requests['memory'])
           
           # 활용도 계산
           cpu_utilization = (total_cpu_requests / capacity_cpu) * 100 if capacity_cpu > 0 else 0
           memory_utilization = (total_memory_requests / capacity_memory) * 100 if capacity_memory > 0 else 0
           
           # 활용도가 낮은 노드 식별
           if cpu_utilization < 30 and memory_utilization < 30:
               underutilized.append({
                   'name': node.metadata.name,
                   'cpu_utilization': cpu_utilization,
                   'memory_utilization': memory_utilization,
                   'instance_type': node.metadata.labels.get('node.kubernetes.io/instance-type', 'unknown')
               })
       
       return underutilized
   
   def get_overprovisioned_deployments():
       """과도하게 프로비저닝된 배포 식별"""
       deployments = apps_v1.list_deployment_for_all_namespaces().items
       overprovisioned = []
       
       for deployment in deployments:
           # Kubecost API에서 실제 리소스 사용량 조회 (예시)
           kubecost_url = "http://kubecost-cost-analyzer.kubecost:9090/model/allocation"
           params = {
               "window": "1d",
               "aggregate": "deployment",
               "namespace": deployment.metadata.namespace,
               "name": deployment.metadata.name
           }
           
           try:
               response = requests.get(kubecost_url, params=params)
               data = response.json()
               
               # 실제 사용량 데이터 추출 (Kubecost API에 따라 다를 수 있음)
               actual_cpu = data.get('data', {}).get(f"{deployment.metadata.namespace}/{deployment.metadata.name}", {}).get('cpuCores', 0)
               actual_memory = data.get('data', {}).get(f"{deployment.metadata.namespace}/{deployment.metadata.name}", {}).get('ramBytes', 0)
               
               # 요청된 리소스 계산
               requested_cpu = 0
               requested_memory = 0
               
               for container in deployment.spec.template.spec.containers:
                   if container.resources.requests:
                       if 'cpu' in container.resources.requests:
                           requested_cpu += kubernetes.utils.parse_quantity(container.resources.requests['cpu']) * deployment.spec.replicas
                       if 'memory' in container.resources.requests:
                           requested_memory += kubernetes.utils.parse_quantity(container.resources.requests['memory']) * deployment.spec.replicas
               
               # 과도하게 프로비저닝된 배포 식별
               if requested_cpu > 0 and actual_cpu > 0:
                   cpu_ratio = actual_cpu / requested_cpu
                   if cpu_ratio < 0.5:
                       overprovisioned.append({
                           'name': deployment.metadata.name,
                           'namespace': deployment.metadata.namespace,
                           'requested_cpu': requested_cpu,
                           'actual_cpu': actual_cpu,
                           'cpu_ratio': cpu_ratio,
                           'requested_memory': requested_memory,
                           'actual_memory': actual_memory,
                           'memory_ratio': actual_memory / requested_memory if requested_memory > 0 else 0
                       })
           except Exception as e:
               print(f"Error fetching data for {deployment.metadata.namespace}/{deployment.metadata.name}: {e}")
       
       return overprovisioned
   
   # 메인 함수
   def main():
       # 활용도가 낮은 노드 식별
       underutilized_nodes = get_underutilized_nodes()
       print(f"Found {len(underutilized_nodes)} underutilized nodes")
       for node in underutilized_nodes:
           print(f"  - {node['name']} ({node['instance_type']}): CPU {node['cpu_utilization']:.2f}%, Memory {node['memory_utilization']:.2f}%")
       
       # 과도하게 프로비저닝된 배포 식별
       overprovisioned_deployments = get_overprovisioned_deployments()
       print(f"Found {len(overprovisioned_deployments)} overprovisioned deployments")
       for deployment in overprovisioned_deployments:
           print(f"  - {deployment['namespace']}/{deployment['name']}: CPU ratio {deployment['cpu_ratio']:.2f}, Memory ratio {deployment['memory_ratio']:.2f}")
       
       # 최적화 권장 사항
       print("\nOptimization Recommendations:")
       
       # 노드 최적화 권장 사항
       if underutilized_nodes:
           print("Node Optimization:")
           print("  - Consider enabling Karpenter for more efficient node provisioning")
           print("  - Consolidate workloads to reduce the number of nodes")
       
       # 배포 최적화 권장 사항
       if overprovisioned_deployments:
           print("Deployment Optimization:")
           print("  - Enable Vertical Pod Autoscaler in recommendation mode")
           print("  - Adjust resource requests based on actual usage")
   
   if __name__ == "__main__":
       main()
   ```

다른 옵션들의 문제점:
- **A. 수동 리소스 관리만 사용**: 수동 관리는 확장성이 떨어지고, 오류 가능성이 높으며, 최적화 기회를 놓칠 수 있습니다.
- **B. AWS Cost Explorer만 사용**: AWS Cost Explorer는 AWS 서비스 수준의 비용 분석에 유용하지만, Kubernetes 리소스 수준의 세부적인 비용 분석이나 자동화된 최적화 기능을 제공하지 않습니다.
- **D. 타사 비용 관리 도구만 사용**: 타사 도구는 유용할 수 있지만, AWS 네이티브 서비스 및 Kubernetes 자동 스케일링 도구와의 통합이 제한적일 수 있으며, 추가 비용이 발생할 수 있습니다.
</details>

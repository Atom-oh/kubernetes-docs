# Karpenter

> **지원 버전**: Karpenter 1.6 ~ 1.14, Kubernetes 1.30+ (v1.14 기준)  
> **마지막 업데이트**: 2026년 9월 9일

## 목차
- [소개](#소개)
- [아키텍처](#아키텍처)
- [설치 및 구성](#설치-및-구성)
- [NodePool](#nodepool)
- [노드 클래스](#노드-클래스)
- [인터럽션 처리](#인터럽션-처리)
- [통합](#통합)
- [Amazon EKS와의 통합](#amazon-eks와의-통합)
- [모범 사례](#모범-사례)
- [문제 해결](#문제-해결)
- [결론](#결론)

## 소개

Karpenter는 Kubernetes 클러스터의 노드 프로비저닝을 자동화하는 오픈 소스 클러스터 오토스케일러입니다. Karpenter는 워크로드 요구 사항에 따라 적절한 컴퓨팅 리소스를 동적으로 프로비저닝하여 애플리케이션 가용성을 보장하고 클러스터 효율성을 최적화합니다.

### Karpenter의 주요 이점

1. **빠른 스케일링**: 워크로드 요구 사항에 따라 몇 초 내에 노드 프로비저닝
2. **비용 최적화**: 워크로드에 가장 적합한 인스턴스 유형 선택
3. **단순한 구성**: 선언적 API를 통한 간단한 구성
4. **워크로드 중심 설계**: 파드 요구 사항에 기반한 노드 프로비저닝
5. **클라우드 통합**: 클라우드 제공업체의 기능 활용
6. **효율적인 빈 패킹**: 리소스 활용도 최적화
7. **유연한 노드 관리**: 노드 수명 주기 관리 및 통합 인터럽션 처리

### 기존 오토스케일러와의 비교

| 기능 | Karpenter | Cluster Autoscaler | Cloud Provider 관리형 노드 그룹 |
|------|-----------|-------------------|---------------------------|
| 스케일링 속도 | 매우 빠름 (초 단위) | 중간 (분 단위) | 느림 (분 단위) |
| 인스턴스 유형 선택 | 동적 | 노드 그룹 기반 | 노드 그룹 기반 |
| 빈 패킹 효율성 | 높음 | 중간 | 낮음 |
| 구성 복잡성 | 낮음 | 중간 | 낮음 |
| 클라우드 통합 | 네이티브 | 제한적 | 네이티브 |
| 노드 그룹 관리 | 불필요 | 필요 | 필요 |
| 인터럽션 처리 | 통합 | 제한적 | 제한적 |

> **참고**: Karpenter 대신 전통적인 EKS Managed Node Group과 Cluster Autoscaler 조합을 유지하는 경우, 2026년 4월부터 EC2 Auto Scaling Warm Pool을 활용해 사전 초기화된 인스턴스를 대기시켜 콜드 스타트 없이 스케일 아웃할 수 있습니다. Stopped(비용 절감) 또는 Running(빠른 전환) 상태를 선택할 수 있고 Cluster Autoscaler와 자동으로 연동되지만, 이는 Karpenter가 아닌 Managed Node Group 전용 기능입니다.

## 아키텍처

Karpenter는 Kubernetes 컨트롤러로 작동하며, 스케줄링할 수 없는 파드를 감지하고 적절한 노드를 프로비저닝합니다.

![Karpenter 컨트롤러가 Kubernetes 클러스터 안에서 스케줄링되지 못한 파드를 감시하고 CRD CEL 규칙으로 검증된 NodePool·EC2NodeClass를 참조해, Kubernetes API와 클라우드 제공업체 Instance API를 호출하여 컴퓨트 인스턴스를 프로비저닝하는 구조를 보여준다.](../.gitbook/assets/ko-autoscaling-02-karpenter-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-autoscaling-02-karpenter-0.html)

### Karpenter 워크플로우

다음 다이어그램은 Karpenter가 EKS 클러스터에서 작동하는 방식을 보여줍니다:

![스케줄링되지 못한 파드가 Kubernetes API를 거쳐 Karpenter 컨트롤러에 전달되고, Karpenter가 AWS EC2 API로 인스턴스를 조회·요청해 새 노드가 등록된 뒤 파드가 최종 스케줄링되기까지의 시간 순서를 보여준다.](../.gitbook/assets/ko-autoscaling-02-karpenter-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-autoscaling-02-karpenter-1.html)

### 주요 구성 요소

1. **Karpenter 컨트롤러**: 스케줄링할 수 없는 파드를 감지하고 노드 프로비저닝을 관리
2. **CRD CEL 검증**: NodePool·EC2NodeClass를 CRD의 CEL 검증 규칙으로 유효성 검사 (어드미션·변환 웹훅은 Karpenter 1.1에서 제거)
3. **NodePool CRD**: 노드 프로비저닝 정책을 정의
4. **EC2NodeClass CRD**: 프로비저닝할 노드의 구성을 정의
5. **클라우드 제공업체 통합**: 클라우드 제공업체의 API와 통합하여 컴퓨팅 리소스 관리

### 작동 방식

1. Karpenter 컨트롤러가 스케줄링할 수 없는 파드를 감지
2. 파드 요구 사항(리소스, 노드 선택기, 허용 오차 등)을 분석
3. NodePool 및 EC2NodeClass 구성에 따라 적절한 노드 유형 결정
4. 클라우드 제공업체 API를 호출하여 노드 프로비저닝
5. 노드가 클러스터에 조인하면 파드 스케줄링
6. 노드가 더 이상 필요하지 않으면 통합 인터럽션 처리를 통해 노드 제거

## 설치 및 구성

### 사전 요구 사항

- Kubernetes 클러스터 (v1.30 이상 — Karpenter 호환성 매트릭스 참조, Kubernetes 1.36은 Karpenter 1.13+ 필요)
- kubectl 설정
- 클라우드 제공업체 자격 증명 및 권한
- Helm (선택 사항)

### AWS EKS에 설치

#### 1. IAM 역할 및 정책 설정

```bash
# eksctl을 사용한 IRSA 설정
eksctl create iamserviceaccount \
  --cluster=my-cluster \
  --name=karpenter \
  --namespace=karpenter \
  --attach-policy-arn=arn:aws:iam::aws:policy/AmazonEKSClusterPolicy \
  --attach-policy-arn=arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly \
  --approve

# 인스턴스 프로필 생성
aws iam create-instance-profile --instance-profile-name KarpenterNodeInstanceProfile

# 노드 역할 생성
aws iam create-role --role-name KarpenterNodeRole --assume-role-policy-document file://node-trust-policy.json

# 노드 역할에 정책 연결
aws iam attach-role-policy --role-name KarpenterNodeRole --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy
aws iam attach-role-policy --role-name KarpenterNodeRole --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy
aws iam attach-role-policy --role-name KarpenterNodeRole --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
aws iam attach-role-policy --role-name KarpenterNodeRole --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

# 인스턴스 프로필에 역할 추가
aws iam add-role-to-instance-profile --instance-profile-name KarpenterNodeInstanceProfile --role-name KarpenterNodeRole
```

#### 2. Helm을 사용한 설치

```bash
# Karpenter v1 차트는 Public ECR의 OCI 아티팩트로 배포됩니다 (`helm repo add` 불필요)
export KARPENTER_VERSION="1.14.1"   # 1.6 이상 아무 릴리스나 가능. 1.14.1은 이 문서가 다루는 최신 패치

# Karpenter 설치
helm upgrade --install karpenter oci://public.ecr.aws/karpenter/karpenter \
  --version "${KARPENTER_VERSION}" \
  --namespace karpenter \
  --create-namespace \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::${ACCOUNT_ID}:role/KarpenterControllerRole \
  --set settings.clusterName=${CLUSTER_NAME} \
  --set settings.clusterEndpoint=${CLUSTER_ENDPOINT} \
  --wait
# 노드 인스턴스 프로필은 더 이상 Helm 값이 아닙니다. 각 EC2NodeClass의 `role`(또는 `instanceProfile`)로 지정하세요
```

#### 3. 설치 확인

```bash
kubectl get pods -n karpenter
```

예상 출력:
```
NAME                         READY   STATUS    RESTARTS   AGE
karpenter-6f4f46d855-5lqx7   1/1     Running   0          1m
```

### 기본 NodePool 및 EC2NodeClass 구성

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
  limits:
    cpu: 1000
    memory: 1000Gi
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["m5.large", "m5.xlarge", "m5.2xlarge"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  role: KarpenterNodeRole
  amiSelectorTerms:
    - alias: al2023@latest
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: "true"
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: "true"
  tags:
    karpenter.sh/discovery: "true"
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
        deleteOnTermination: true
```

## NodePool

NodePool은 Karpenter가 노드를 프로비저닝하는 방법을 정의하는 Kubernetes 사용자 정의 리소스입니다. 이전의 Provisioner를 대체합니다.

### 기본 NodePool 구성

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    metadata:
      # 노드 레이블
      labels:
        environment: production
        app: web
    spec:
      # 노드 요구 사항
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["m5.large", "m5.xlarge", "m5.2xlarge"]

      # 노드 클래스 참조
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default

      # 테인트
      taints:
        - key: example.com/special-taint
          value: "true"
          effect: NoSchedule

      # 시작 테인트
      startupTaints:
        - key: node.kubernetes.io/not-ready
          effect: NoSchedule

      # 노드 만료 설정
      expireAfter: 720h  # 30일

  # 리소스 제한
  limits:
    cpu: 1000
    memory: 1000Gi

  # 중단(disruption) 설정
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### 요구 사항 구성

요구 사항은 Karpenter가 프로비저닝할 노드의 특성을 정의합니다:

```yaml
template:
  spec:
    requirements:
      # 용량 유형 (온디맨드 또는 스팟)
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["on-demand", "spot"]
      
      # 아키텍처
      - key: kubernetes.io/arch
        operator: In
        values: ["amd64", "arm64"]
      
      # 인스턴스 유형
      - key: node.kubernetes.io/instance-type
        operator: In
        values: ["m5.large", "m5.xlarge", "c5.large"]
      
      # 가용 영역
      - key: topology.kubernetes.io/zone
        operator: In
        values: ["us-west-2a", "us-west-2b", "us-west-2c"]
      
      # 운영 체제
      - key: kubernetes.io/os
        operator: In
        values: ["linux"]
```

### 제한 구성

제한은 Karpenter가 프로비저닝할 수 있는 리소스의 최대량을 정의합니다:

```yaml
limits:
  cpu: 1000
  memory: 1000Gi
  nvidia.com/gpu: 10
```

### Dynamic Resource Allocation(DRA) 지원 (v1.13)

Karpenter v1.13(2026년 6월 릴리스)부터 Kubernetes DRA(Dynamic Resource Allocation) 기반 디바이스 할당 추적을 지원합니다. GPU, 특수 가속기 등 클레임 기반으로 할당되는 리소스를 Karpenter가 인식해 프로비저닝 결정에 반영할 수 있어, `nvidia.com/gpu`와 같은 확장 리소스뿐 아니라 DRA `ResourceClaim`/`DeviceClass`를 사용하는 AI/HPC 워크로드에도 정확한 스케일링이 가능합니다. DRA 기반 추적을 사용하려면 Kubernetes 1.29 이상이 필요합니다.

### 노드 만료 구성

노드 만료 설정은 Karpenter가 노드를 제거하는 시기를 정의합니다:

```yaml
spec:
  template:
    spec:
      # 노드 생성 후 제거하기까지의 최대 시간
      expireAfter: 720h  # 30일 (만료를 끄려면 "Never")

  disruption:
    # 노드가 비어 있을 때 통합(제거)
    consolidationPolicy: WhenEmpty

    # 노드가 비어 있은 후 통합(제거)까지의 시간
    consolidateAfter: 30s
```

### NodeReadinessController를 통한 초기화 Taint 자동 무시 (v1.13)

Karpenter v1.13에 추가된 NodeReadinessController는 노드가 초기화되는 동안 붙는 준비성(readiness) 관련 Taint를 자동으로 무시해 불필요한 스케줄링 차단을 줄입니다. 기존에는 `startupTaints`로 수동 처리해야 했던 초기화 지연 문제가 완화되어, 신규 노드가 프로비저닝 후 Ready 상태에 도달하는 과정에서의 스케줄링 안정성과 프로비저닝 신뢰성이 향상됩니다.

### 2026년 7월 업데이트: v1.14 릴리스

2026년 7월 11일 릴리스된 Karpenter v1.14의 주요 기능:

- **CapacityBuffers API 지원**: 예비 용량(버퍼)을 선언적으로 확보해 급격한 스케일 아웃에 대비할 수 있습니다
- **프리뷰(preview) 인스턴스 타입 지원**: 아직 정식 출시 전인 EC2 인스턴스 타입도 프로비저닝 대상으로 선택 가능
- **Nitro Enclaves 지원**: 시작 템플릿에 `EnclaveOptions.Enabled`를 설정할 수 있어 기밀 컴퓨팅 워크로드에 활용 가능
- 버그 수정: 보조 ENI의 기본 IP 계산 반영, Zonal Shift 캐시 하이드레이션 보장, AWS SDK 클라이언트 타임아웃 설정 등

자세한 내용은 [v1.14.0 릴리스 노트](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.14.0)를 참고하세요.

이어서 2026년 7월 17일에는 유지 관리 중인 모든 마이너 라인(v1.3.8 ~ v1.11.3)에 대해 업스트림 `sigs.k8s.io/karpenter` 버전을 갱신하는 패치 릴리스가 일괄 공개되었습니다. 구버전 라인을 사용 중이라면 해당 라인의 최신 패치로 업데이트하는 것을 권장합니다 ([릴리스 목록](https://github.com/aws/karpenter-provider-aws/releases)).

또한 2026년 7월 22일에는 Karpenter(및 EKS Auto Mode) 노드 풀에서 Elastic Fabric Adapter(EFA) 네트워크 디바이스 구성과 EC2 배치 그룹(placement group)을 지원한다는 발표가 있었습니다. EFA 지원 인스턴스의 네트워크 인터페이스를 EFA 전용(VPC IP 주소를 소비하지 않음) 또는 표준 ENI로 설정할 수 있고, cluster/spread/partition 배치 전략을 노드 풀 구성에서 직접 지정할 수 있습니다 — 분산 학습·추론 워크로드에 유용합니다. [발표](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-eks-efa-placement-groups/)를 참고하세요.

### 2026년 8월 업데이트: v1.14.1 패치 릴리스

2026년 8월 21일 v1.14 라인의 첫 패치인 [v1.14.1](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.14.1)이 공개되었습니다. 업스트림 `sigs.k8s.io/karpenter` 버전 갱신과 v1.14.0 이후 수정 사항의 체리픽을 담은 유지 보수 릴리스입니다.

## 노드 클래스

노드 클래스는 Karpenter가 프로비저닝하는 노드의 구성을 정의합니다. AWS에서는 EC2NodeClass CRD를 사용합니다.

### AWS EC2NodeClass 구성

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  # 서브넷 선택
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: "true"

  # 보안 그룹 선택
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: "true"

  # 인스턴스 태그
  tags:
    karpenter.sh/discovery: "true"
    environment: production
  
  # 블록 디바이스 매핑
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
        deleteOnTermination: true
        encrypted: true
  
  # 세부 인스턴스 구성
  role: KarpenterNodeRole
  # AMI 선택: AL2 AMI는 EKS 1.33 이상에 더 이상 게시되지 않으므로 AL2023 alias를 사용
  amiSelectorTerms:
    - alias: al2023@latest
  userData: |
    #!/bin/bash
    echo "Hello from Karpenter node!"
  
  # 메타데이터 옵션
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 2
    httpTokens: required
```

### 서브넷 및 보안 그룹 선택

서브넷과 보안 그룹은 태그 기반 선택 조건(selector terms)을 사용하여 선택할 수 있습니다. 여러 term은 OR로, 하나의 term 안의 태그는 AND로 평가됩니다:

```yaml
# 서브넷 선택
subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: "true"
      Name: "private-*"

# 보안 그룹 선택
securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: "true"
      aws:eks:cluster-name: "my-cluster"
```

### AMI 구성

Karpenter는 `amiSelectorTerms`의 alias로 AMI 패밀리를 지정하며, 사용자 정의 AMI는 ID·이름·태그로 선택할 수 있습니다. AL2 AMI는 EKS 1.33 이상에 더 이상 게시되지 않으므로 AL2023을 사용하세요. EC2NodeClass 하나에는 `amiSelectorTerms`를 한 번만 선언하므로, 아래 예시는 각각 별개의 변형입니다:

```yaml
# Amazon Linux 2023
amiSelectorTerms:
  - alias: al2023@latest
---
# Bottlerocket
amiSelectorTerms:
  - alias: bottlerocket@latest
---
# 사용자 정의 AMI (ID 지정) — alias 항목이 없으면 amiFamily가 필수
amiFamily: Custom
amiSelectorTerms:
  - id: "ami-0123456789abcdef0"
# Ubuntu: v1 alias 없음 — amiFamily: Custom과 id/tags/name 항목을 사용
```

### 블록 디바이스 구성

노드의 스토리지 구성을 정의할 수 있습니다:

```yaml
blockDeviceMappings:
  # 루트 볼륨
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 100Gi
      volumeType: gp3
      iops: 3000
      throughput: 125
      deleteOnTermination: true
      encrypted: true
      kmsKeyID: "arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab"
  
  # 추가 볼륨
  - deviceName: /dev/xvdb
    ebs:
      volumeSize: 500Gi
      volumeType: gp3
      deleteOnTermination: true
```

### 사용자 데이터 구성

노드 시작 시 실행할 사용자 데이터 스크립트를 정의할 수 있습니다:

```yaml
userData: |
  #!/bin/bash
  echo "Hello from Karpenter node!"
  
  # 시스템 구성
  sysctl -w vm.max_map_count=262144
  
  # 패키지 설치
  yum update -y
  yum install -y amazon-cloudwatch-agent
  
  # CloudWatch 에이전트 시작
  systemctl enable amazon-cloudwatch-agent
  systemctl start amazon-cloudwatch-agent
```

### 노드 통합 프로세스

다음 다이어그램은 Karpenter의 노드 통합(consolidation) 프로세스를 보여줍니다. 이 기능은 클러스터 효율성을 최적화하고 비용을 절감하는 데 중요합니다:

![사용률이 낮은 기존 노드 세 개를 분석·평가한 뒤 하나의 새 노드로 파드를 마이그레이션하고, 비워진 기존 노드를 드레이닝·종료해 노드 수를 통합하는 과정을 보여준다.](../.gitbook/assets/ko-autoscaling-02-karpenter-2.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-autoscaling-02-karpenter-2.html)

## 인터럽션 처리

Karpenter는 노드 인터럽션을 자동으로 처리하여 워크로드 가용성을 보장합니다.

### 통합 인터럽션 처리

Karpenter는 다음과 같은 인터럽션 이벤트를 처리합니다:

1. **스팟 인스턴스 중단**: AWS 스팟 인스턴스 중단 알림 처리
2. **노드 만료**: TTL 기반 노드 교체
3. **스케일 다운**: 노드가 더 이상 필요하지 않을 때 제거
4. **노드 통합**: 더 효율적인 노드 구성으로 통합

### 인터럽션 처리 구성

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default

      # 노드 만료 설정
      expireAfter: 720h  # 30일

  # 통합(consolidation) 설정
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### 드레이닝 구성

Karpenter는 노드를 제거하기 전에 파드를 안전하게 드레이닝합니다. 컨트롤러 전역 동작은 Helm 값으로 설정하며(레거시 global-settings ConfigMap은 v0.33에서 제거됨), 동시에 드레이닝할 수 있는 노드 수는 NodePool별 disruption budget으로 설정합니다:

```yaml
# karpenter-values.yaml — `helm upgrade --install ... -f karpenter-values.yaml` 로 전달
settings:
  clusterName: my-cluster
  interruptionQueue: my-cluster   # 스팟 중단·리밸런스·헬스 이벤트를 수신하는 SQS 큐
  batchMaxDuration: 10s
  batchIdleDuration: 1s
  featureGates:
    spotToSpotConsolidation: false
controller:
  resources:
    requests:
      cpu: 1
      memory: 1Gi
    limits:
      cpu: 1
      memory: 1Gi
logLevel: info
```

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
      expireAfter: 720h
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
    budgets:
      - nodes: "30%"   # 이 NodePool 노드 중 동시에 최대 30%까지만 disruption 허용
```

### PDB(PodDisruptionBudget) 통합

Karpenter는 PDB를 존중하여 애플리케이션 가용성을 보장합니다:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```

## 통합

Karpenter는 다양한 Kubernetes 및 클라우드 서비스와 통합됩니다.

### Kubernetes 통합

#### 1. Pod Topology Spread Constraints

Karpenter는 Pod Topology Spread Constraints를 고려하여 노드를 프로비저닝합니다:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-server
spec:
  replicas: 10
  template:
    spec:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: web-server
```

#### 2. Pod Affinity/Anti-Affinity

Karpenter는 Pod Affinity 및 Anti-Affinity 규칙을 고려합니다:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-server
spec:
  replicas: 10
  template:
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchExpressions:
                  - key: app
                    operator: In
                    values:
                      - web-server
              topologyKey: "kubernetes.io/hostname"
```

#### 3. 테인트 및 허용 오차

Karpenter는 테인트 및 허용 오차를 고려하여 노드를 프로비저닝합니다:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu
spec:
  template:
    spec:
      requirements:
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["g4dn.xlarge", "g4dn.2xlarge"]
      taints:
        - key: nvidia.com/gpu
          value: "true"
          effect: NoSchedule
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gpu-app
spec:
  replicas: 3
  template:
    spec:
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
      nodeSelector:
        karpenter.sh/nodepool: gpu
```

### AWS 통합

#### 1. EC2 Spot 인스턴스

Karpenter는 EC2 Spot 인스턴스를 지원하여 비용을 최적화합니다:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: spot
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: spot
spec:
  role: KarpenterNodeRole
  amiSelectorTerms:
    - alias: al2023@latest
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: "true"
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: "true"
```

#### 2. EC2 인스턴스 프로필

Karpenter는 EC2 인스턴스 프로필을 사용하여 노드에 IAM 권한을 부여합니다:

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  instanceProfile: KarpenterNodeInstanceProfile
  # 또는 role: KarpenterNodeRole 을 지정하면 Karpenter가 인스턴스 프로필을 자동 생성합니다
  amiSelectorTerms:
    - alias: al2023@latest
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: "true"
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: "true"
```

#### 3. Launch Template 대체 (EC2NodeClass)

Karpenter v1에서는 사용자가 만든 EC2 시작 템플릿을 직접 참조하는 `launchTemplate` 필드가 제거되었습니다. 대신 Karpenter가 `EC2NodeClass`의 `amiSelectorTerms`, `blockDeviceMappings`, `userData`, `metadataOptions`, `tags` 등을 바탕으로 시작 템플릿을 자동 생성·관리합니다. 기존 시작 템플릿에 담겨 있던 설정은 해당 `EC2NodeClass` 필드로 옮겨 표현하세요:

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: node-config
spec:
  role: KarpenterNodeRole
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: "true"
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: "true"
  # AMI, 사용자 데이터, 블록 디바이스, IMDS 옵션이 시작 템플릿 내용을 대체
  amiSelectorTerms:
    - alias: al2023@latest
  userData: |
    #!/bin/bash
    echo "Hello from Karpenter node!"
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
        deleteOnTermination: true
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 2
    httpTokens: required
```
## Amazon EKS와의 통합

Karpenter는 Amazon EKS와 원활하게 통합되어 클러스터 오토스케일링을 제공합니다.

![Karpenter 컨트롤러가 IRSA를 통해 EC2 API 권한을 얻어 Auto Scaling Group과 관리형 노드 그룹을 거치지 않고 EC2 인스턴스를 직접 생성하며, 보안 그룹과 VPC 설정을 그대로 활용하는 구조를 보여준다.](../.gitbook/assets/ko-autoscaling-02-karpenter-3.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-autoscaling-02-karpenter-3.html)

### EKS 클러스터 준비

#### 1. 클러스터 태그 설정

Karpenter가 클러스터 리소스를 식별할 수 있도록 태그를 설정합니다:

```bash
# 클러스터 이름 설정
CLUSTER_NAME="my-cluster"

# VPC 태그 설정
aws ec2 create-tags \
  --resources $(aws eks describe-cluster \
    --name ${CLUSTER_NAME} \
    --query "cluster.resourcesVpcConfig.vpcId" \
    --output text) \
  --tags Key=karpenter.sh/discovery,Value=${CLUSTER_NAME}

# 서브넷 태그 설정
for SUBNET in $(aws eks describe-cluster \
  --name ${CLUSTER_NAME} \
  --query "cluster.resourcesVpcConfig.subnetIds[]" \
  --output text); do
  aws ec2 create-tags \
    --resources ${SUBNET} \
    --tags Key=karpenter.sh/discovery,Value=${CLUSTER_NAME}
done

# 보안 그룹 태그 설정
aws ec2 create-tags \
  --resources $(aws eks describe-cluster \
    --name ${CLUSTER_NAME} \
    --query "cluster.resourcesVpcConfig.clusterSecurityGroupId" \
    --output text) \
  --tags Key=karpenter.sh/discovery,Value=${CLUSTER_NAME}
```

#### 2. IAM 역할 설정

Karpenter 컨트롤러와 노드에 필요한 IAM 역할을 설정합니다:

```bash
# 컨트롤러 역할 생성
cat <<EOF > controller-trust-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_PROVIDER}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${OIDC_PROVIDER}:sub": "system:serviceaccount:karpenter:karpenter",
          "${OIDC_PROVIDER}:aud": "sts.amazonaws.com"
        }
      }
    }
  ]
}
EOF

aws iam create-role \
  --role-name KarpenterControllerRole-${CLUSTER_NAME} \
  --assume-role-policy-document file://controller-trust-policy.json

# 컨트롤러 정책 생성
cat <<EOF > controller-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateLaunchTemplate",
        "ec2:CreateFleet",
        "ec2:RunInstances",
        "ec2:CreateTags",
        "ec2:TerminateInstances",
        "ec2:DescribeLaunchTemplates",
        "ec2:DescribeInstances",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeSubnets",
        "ec2:DescribeInstanceTypes",
        "ec2:DescribeInstanceTypeOfferings",
        "ec2:DescribeAvailabilityZones",
        "ec2:DescribeSpotPriceHistory",
        "pricing:GetProducts",
        "ssm:GetParameter"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resources": "arn:aws:iam::${ACCOUNT_ID}:role/KarpenterNodeRole-${CLUSTER_NAME}",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": "ec2.amazonaws.com"
        }
      }
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name KarpenterControllerRole-${CLUSTER_NAME} \
  --policy-name KarpenterControllerPolicy-${CLUSTER_NAME} \
  --policy-document file://controller-policy.json
```

### EKS 클러스터에 Karpenter 설치

```bash
# Helm을 사용한 설치 (v1 OCI 차트)
export KARPENTER_VERSION="1.14.1"

helm upgrade --install karpenter oci://public.ecr.aws/karpenter/karpenter \
  --version "${KARPENTER_VERSION}" \
  --namespace karpenter \
  --create-namespace \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::${ACCOUNT_ID}:role/KarpenterControllerRole-${CLUSTER_NAME} \
  --set settings.clusterName=${CLUSTER_NAME} \
  --set settings.clusterEndpoint=$(aws eks describe-cluster --name ${CLUSTER_NAME} --query "cluster.endpoint" --output text) \
  --set settings.interruptionQueue=${CLUSTER_NAME} \
  --wait
# 노드 IAM: 각 EC2NodeClass의 `role:`에 KarpenterNodeRole-${CLUSTER_NAME}을 지정합니다 (아래 예시 참고)
```

### EKS 관리형 노드 그룹과 함께 사용

Karpenter는 EKS 관리형 노드 그룹과 함께 사용할 수 있습니다:

```yaml
# EKS 관리형 노드 그룹용 NodePool
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: managed-ng
spec:
  template:
    metadata:
      labels:
        managed-by: karpenter
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["m5.large", "m5.xlarge"]
      taints:
        - key: managed-by
          value: karpenter
          effect: NoSchedule
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: managed-ng
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: managed-ng
spec:
  role: KarpenterNodeRole-${CLUSTER_NAME}
  amiSelectorTerms:
    - alias: al2023@latest
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: "${CLUSTER_NAME}"
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: "${CLUSTER_NAME}"
  tags:
    karpenter.sh/discovery: "${CLUSTER_NAME}"
```

### EKS Fargate와 함께 사용

Karpenter는 EKS Fargate와 함께 사용하여 하이브리드 클러스터를 구성할 수 있습니다:

```bash
# Fargate 프로필 생성
aws eks create-fargate-profile \
  --cluster-name ${CLUSTER_NAME} \
  --fargate-profile-name fp-default \
  --pod-execution-role-arn arn:aws:iam::${ACCOUNT_ID}:role/AmazonEKSFargatePodExecutionRole \
  --selectors namespace=default,namespace=kube-system
```

```yaml
# Karpenter NodePool 구성
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ec2
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: ec2
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: ec2
spec:
  role: KarpenterNodeRole-${CLUSTER_NAME}
  amiSelectorTerms:
    - alias: al2023@latest
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: "${CLUSTER_NAME}"
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: "${CLUSTER_NAME}"
```

### AZ 장애 대응: Amazon ARC Zonal Shift 통합 (2026년 5월)

Karpenter는 Amazon ARC(Application Recovery Controller)의 Zonal Shift를 지원합니다. 특정 가용 영역(AZ)에 장애가 발생하면 Karpenter는 해당 AZ로의 신규 노드 프로비저닝을 자동으로 중단하고, 정상 AZ를 중심으로 스케줄링을 수행합니다. AWS가 AZ 상태를 자동으로 감지해 트래픽 전환과 복구까지 처리하는 Zonal Autoshift도 함께 지원됩니다.

장애가 감지되면 Karpenter의 voluntary disruption(consolidation, drift 처리 등)도 자동으로 중단되어, 장애 상황에서 불필요한 노드 교체로 클러스터가 더 불안정해지는 것을 방지합니다. 기존 EKS ARC 리소스를 그대로 활용하므로 별도의 커스텀 리소스를 만들 필요가 없으며, `ENABLE_ZONAL_SHIFT` 옵션으로 활성화합니다.

### EKS 비용 최적화

Karpenter를 사용하여 EKS 클러스터의 비용을 최적화할 수 있습니다:

![노드 그룹 기반으로 느리게 확장하는 Cluster Autoscaler와, 워크로드 기반으로 다양한 인스턴스 유형·노드 통합·스팟 활용까지 지원해 더 높은 비용 절감을 이끄는 Karpenter의 특징을 나란히 비교해 보여준다.](../.gitbook/assets/ko-autoscaling-02-karpenter-4.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-autoscaling-02-karpenter-4.html)

#### 1. 스팟 인스턴스 사용

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: spot
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: spot
spec:
  role: KarpenterNodeRole-${CLUSTER_NAME}
  amiSelectorTerms:
    - alias: al2023@latest
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: "${CLUSTER_NAME}"
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: "${CLUSTER_NAME}"
```

#### 2. 다양한 인스턴스 유형 사용

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: flexible
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: [
            "m5.large", "m5.xlarge", "m5.2xlarge",
            "m6g.large", "m6g.xlarge", "m6g.2xlarge",
            "c5.large", "c5.xlarge", "c5.2xlarge",
            "c6g.large", "c6g.xlarge", "c6g.2xlarge",
            "r5.large", "r5.xlarge", "r5.2xlarge",
            "r6g.large", "r6g.xlarge", "r6g.2xlarge"
          ]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: flexible
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

#### 3. 노드 통합 활성화

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
```

## 모범 사례

![Karpenter 운영 모범 사례를 성능 최적화, 비용 최적화, 가용성 향상, 보안 강화 네 가지 축으로 나누고 각 축에서 실천할 네 가지 설정 항목을 나란히 보여준다.](../.gitbook/assets/ko-autoscaling-02-karpenter-5.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-autoscaling-02-karpenter-5.html)

### 성능 최적화

1. **적절한 인스턴스 유형 선택**: 워크로드에 적합한 인스턴스 유형 선택
2. **다양한 인스턴스 유형 허용**: 가용성 및 비용 최적화를 위해 다양한 인스턴스 유형 허용
3. **적절한 TTL 설정**: 워크로드 패턴에 맞는 TTL 설정
4. **노드 통합 활성화**: 리소스 활용도 최적화를 위한 노드 통합 활성화

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: optimized
spec:
  # 다양한 인스턴스 유형 허용
  template:
    spec:
      requirements:
        - key: node.kubernetes.io/instance-type
          operator: In
          values: [
            "m5.large", "m5.xlarge", "m5.2xlarge",
            "c5.large", "c5.xlarge", "c5.2xlarge",
            "r5.large", "r5.xlarge", "r5.2xlarge"
          ]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: optimized

      # 적절한 TTL 설정
      expireAfter: 720h  # 30일

  # 노드 통합 활성화
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### 비용 최적화

1. **스팟 인스턴스 활용**: 비용 절감을 위한 스팟 인스턴스 사용
2. **적절한 인스턴스 크기 선택**: 워크로드에 적합한 인스턴스 크기 선택
3. **제로 스케일링 활용**: 활동이 없을 때 노드 수를 0으로 줄이기
4. **노드 만료 설정**: 정기적인 노드 교체를 통한 최신 인스턴스 유형 활용

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-optimized
spec:
  # 스팟 인스턴스 사용
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: cost-optimized

      # 노드 만료 설정
      expireAfter: 168h  # 7일

  # 제로 스케일링 (빈 노드 제거)
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### 가용성 향상

1. **다중 가용 영역 사용**: 여러 가용 영역에 걸쳐 노드 배포
2. **온디맨드 및 스팟 인스턴스 혼합**: 가용성과 비용 균형 유지
3. **적절한 PDB 설정**: 애플리케이션 가용성 보장
4. **인터럽션 처리 최적화**: 노드 인터럽션 시 워크로드 가용성 보장

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: high-availability
spec:
  # 다중 가용 영역 사용
  template:
    spec:
      requirements:
        - key: topology.kubernetes.io/zone
          operator: In
          values: ["us-west-2a", "us-west-2b", "us-west-2c"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: high-availability

      # 노드 만료 설정
      expireAfter: 720h  # 30일

  # 인터럽션 처리 최적화 및 노드 통합 설정
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 60s
```

## 문제 해결

### 일반적인 문제

#### 1. 노드 프로비저닝 실패

**증상**: 파드가 Pending 상태로 유지되고 노드가 프로비저닝되지 않음

**해결 방법**:
- Karpenter 로그 확인
- IAM 권한 확인
- NodePool 구성 확인

```bash
# Karpenter 로그 확인
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller

# NodePool 상태 확인
kubectl describe nodepool <name>

# 파드 이벤트 확인
kubectl describe pod <name>
```

#### 2. 노드 제거 문제

**증상**: 노드가 예상대로 제거되지 않음

**해결 방법**:
- TTL 설정 확인
- 노드 통합 설정 확인
- 파드 드레이닝 상태 확인

```bash
# 노드 상태 확인
kubectl describe node <name>

# 노드 레이블 확인
kubectl get node <name> --show-labels

# Karpenter 로그 확인
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller | grep "node termination"
```

#### 3. 인스턴스 유형 선택 문제

**증상**: 예상하지 않은 인스턴스 유형이 프로비저닝됨

**해결 방법**:
- NodePool 요구 사항 확인
- 파드 리소스 요청 확인
- 가용 영역 제약 조건 확인

```bash
# NodePool 요구 사항 확인
kubectl get nodepool <name> -o yaml

# 파드 리소스 요청 확인
kubectl describe pod <name>

# 노드 정보 확인
kubectl describe node <name>
```

### 디버깅 도구

```bash
# Karpenter 버전 확인
kubectl get deployment -n karpenter karpenter -o jsonpath="{.spec.template.spec.containers[0].image}"

# Karpenter 로그 확인
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller

# NodePool 목록 확인
kubectl get nodepools

# EC2NodeClass 목록 확인
kubectl get ec2nodeclasses

# 이벤트 확인
kubectl get events --sort-by='.lastTimestamp'

# 디버그 로그 활성화 (logLevel은 Helm 값이며, 레거시 global-settings ConfigMap은 더 이상 존재하지 않음)
helm upgrade karpenter oci://public.ecr.aws/karpenter/karpenter \
  --version "${KARPENTER_VERSION}" --namespace karpenter \
  --reuse-values --set logLevel=debug
```

## 결론

Karpenter는 Kubernetes 클러스터의 노드 프로비저닝을 자동화하는 강력한 오토스케일러입니다. 워크로드 요구 사항에 따라 적절한 컴퓨팅 리소스를 동적으로 프로비저닝하여 애플리케이션 가용성을 보장하고 클러스터 효율성을 최적화합니다.

이 문서에서는 Karpenter의 기본 개념, 설치 방법, NodePool 및 EC2NodeClass 구성, 인터럽션 처리, 다양한 통합, Amazon EKS와의 통합, 모범 사례 및 문제 해결에 대해 살펴보았습니다.

Karpenter를 사용하면 클러스터 관리를 간소화하고, 리소스 활용도를 최적화하며, 비용을 절감할 수 있습니다. 특히 Amazon EKS와 같은 클라우드 관리형 Kubernetes 환경에서 Karpenter의 이점을 최대한 활용할 수 있습니다.

### 다음 단계

- Karpenter를 사용한 비용 최적화 전략 구현
- 다양한 워크로드 유형에 맞는 NodePool 구성
- 하이브리드 클러스터 아키텍처 설계
- Karpenter와 다른 Kubernetes 도구와의 통합
- 고급 노드 수명 주기 관리 전략 개발

## 참고 자료

- [Karpenter 공식 문서](https://karpenter.sh/)
- [Karpenter GitHub 저장소](https://github.com/aws/karpenter)
- [Amazon EKS 워크숍 - Karpenter](https://www.eksworkshop.com/docs/autoscaling/compute/karpenter/)
- [AWS 블로그 - Karpenter](https://aws.amazon.com/blogs/containers/introducing-karpenter-an-open-source-high-performance-kubernetes-cluster-autoscaler/)
- [Karpenter 모범 사례](https://aws.github.io/aws-eks-best-practices/karpenter/)
- [Karpenter GitHub Releases](https://github.com/aws/karpenter-provider-aws/releases)
- [AWS What's New - Karpenter ARC Zonal Shift 지원](https://aws.amazon.com/about-aws/whats-new/2026/05/karpenter-arc-zonal-shift/)
- [AWS What's New - Amazon EKS Managed Node Group Warm Pool 지원](https://aws.amazon.com/about-aws/whats-new/2026/04/amazon-eks-managed-node-groups-ec2-warm-pools/)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [주제 퀴즈](../quizzes/autoscaling/06-karpenter-quiz.md)를 풀어보세요.

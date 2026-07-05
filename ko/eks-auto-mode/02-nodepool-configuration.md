# NodePool 구성 및 최적화

> **지원 버전**: EKS 1.29+, EKS Auto Mode GA
> **마지막 업데이트**: 2026년 7월 3일

< [이전: Auto Mode 시작하기](./01-getting-started.md) | [목차](./README.md) | [다음: 스케일링 동작](./03-scaling-behavior.md) >

---

이 문서에서는 EKS Auto Mode의 NodePool 리소스를 이해하고 워크로드 요구사항에 맞게 구성하는 방법을 설명합니다.

## 기본 NodePool 이해

EKS Auto Mode는 두 가지 기본 NodePool을 제공합니다:

### general-purpose NodePool

범용 워크로드를 위한 기본 NodePool입니다.

```yaml
# general-purpose NodePool (AWS 관리, 참고용)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: general-purpose
spec:
  template:
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c", "m", "r"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
```

### system NodePool

시스템 컴포넌트(CoreDNS, kube-proxy 등)를 위한 NodePool입니다.

```yaml
# system NodePool (AWS 관리, 참고용)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: system
spec:
  template:
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["medium", "large", "xlarge"]
      taints:
        - key: CriticalAddonsOnly
          value: "true"
          effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

## 커스텀 NodePool 생성

워크로드 요구사항에 맞는 커스텀 NodePool을 생성할 수 있습니다.

### 고성능 컴퓨팅 NodePool

```yaml
# compute-optimized-nodepool.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: compute-optimized
  labels:
    workload-type: compute-intensive
spec:
  template:
    metadata:
      labels:
        workload-type: compute-intensive
    spec:
      requirements:
        # CPU 최적화 인스턴스만 사용
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c"]
        # 최신 세대 인스턴스
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["6"]
        # 인스턴스 크기 제한
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["xlarge", "2xlarge", "4xlarge"]
        # x86_64만 사용
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        # On-Demand만 사용 (안정성 우선)
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  # 최대 노드 수 제한
  limits:
    cpu: 1000
    memory: 4000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
  # 노드 가중치 (높을수록 우선)
  weight: 10
```

### 메모리 최적화 NodePool

```yaml
# memory-optimized-nodepool.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: memory-optimized
  labels:
    workload-type: memory-intensive
spec:
  template:
    metadata:
      labels:
        workload-type: memory-intensive
    spec:
      requirements:
        # 메모리 최적화 인스턴스
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["r"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["2xlarge", "4xlarge", "8xlarge", "12xlarge"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: 500
    memory: 8000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
  weight: 5
```

## NodeClass 설정

NodeClass는 노드의 AWS 특정 설정을 정의합니다.

```yaml
# custom-nodeclass.yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: custom-nodeclass
spec:
  # AMI 패밀리 선택
  amiFamily: AL2023

  # 서브넷 선택
  subnetSelectorTerms:
    - tags:
        kubernetes.io/role/internal-elb: "1"
        Environment: production

  # 보안 그룹 선택
  securityGroupSelectorTerms:
    - tags:
        kubernetes.io/cluster/my-cluster: owned
        Type: worker-node

  # 인스턴스 프로파일
  instanceProfile: eks-node-instance-profile

  # 블록 디바이스 매핑
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
        iops: 3000
        throughput: 125
        encrypted: true
        deleteOnTermination: true

  # 사용자 데이터 (추가 부트스트랩 스크립트)
  userData: |
    #!/bin/bash
    echo "Custom bootstrap script"
    # 커널 파라미터 튜닝
    sysctl -w vm.max_map_count=262144

  # 메타데이터 옵션
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 2
    httpTokens: required  # IMDSv2 필수

  tags:
    Environment: production
    ManagedBy: eks-auto-mode
```

### 보안 및 네트워킹 확장 필드

NodeClass는 아래 필드로 디스크 암호화, 커스텀 CA 신뢰 체인, Pod 트래픽 분리를 추가로 제어할 수 있습니다.

```yaml
# secure-network-nodeclass.yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: secure-network-nodeclass
spec:
  amiFamily: AL2023

  # 고객 관리형 KMS 키로 ephemeral instance storage + root EBS volume 전체 암호화
  # (커스텀 AMI 없이 적용 가능)
  kmsKeyID: arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab

  # 엔터프라이즈 PKI/프록시 신뢰 체인을 위한 커스텀 CA 인증서 bundle
  certificateBundles:
    - name: corporate-ca
      content: |
        -----BEGIN CERTIFICATE-----
        MIIDXTCCAkWgAwIBAgIJAK...
        -----END CERTIFICATE-----

  # 인프라 트래픽과 애플리케이션 Pod 트래픽을 분리된 서브넷/보안 그룹(secondary ENI)으로 구성
  subnetSelectorTerms:
    - tags:
        kubernetes.io/role/internal-elb: "1"
  securityGroupSelectorTerms:
    - tags:
        kubernetes.io/cluster/my-cluster: owned
  podSubnetSelectorTerms:
    - tags:
        Purpose: pod-network
  podSecurityGroupSelectorTerms:
    - tags:
        Purpose: pod-network
```

| 필드 | 설명 |
|------|------|
| `kmsKeyID` | 고객 관리형 KMS 키 ARN. ephemeral instance storage와 root EBS volume을 암호화 |
| `certificateBundles` | 커스텀 CA 인증서 bundle 목록. 프록시/PKI 신뢰 체인이 필요한 엔터프라이즈 환경에서 사용 |
| `podSubnetSelectorTerms` | Pod 트래픽 전용 서브넷 지정 (secondary ENI로 분리) |
| `podSecurityGroupSelectorTerms` | Pod 트래픽 전용 보안 그룹 지정 (secondary ENI로 분리) |

`podSubnetSelectorTerms`/`podSecurityGroupSelectorTerms`를 설정하면 노드 자체의 인프라 트래픽(kubelet, 컨트롤 플레인 통신 등)과 Pod가 발생시키는 애플리케이션 트래픽이 서로 다른 서브넷·보안 그룹을 사용하도록 분리되어, 보안 그룹 규칙과 네트워크 ACL을 트래픽 유형별로 독립적으로 설계할 수 있습니다.

## NodePool 분리 전략

### 워크로드별 분리

```yaml
# 프론트엔드 워크로드용 NodePool
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: frontend
spec:
  template:
    metadata:
      labels:
        workload-tier: frontend
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
      taints:
        - key: workload-tier
          value: frontend
          effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  weight: 10
---
# 백엔드 워크로드용 NodePool
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: backend
spec:
  template:
    metadata:
      labels:
        workload-tier: backend
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "r"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      taints:
        - key: workload-tier
          value: backend
          effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  weight: 10
```

### 환경별 분리 (개발/스테이징/프로덕션)

```yaml
# 개발 환경 NodePool
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: dev-pool
spec:
  template:
    metadata:
      labels:
        environment: development
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["t", "m"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["medium", "large"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]  # 비용 절감
      taints:
        - key: environment
          value: development
          effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: 100
  weight: 1
```

---

< [이전: Auto Mode 시작하기](./01-getting-started.md) | [목차](./README.md) | [다음: 스케일링 동작](./03-scaling-behavior.md) >

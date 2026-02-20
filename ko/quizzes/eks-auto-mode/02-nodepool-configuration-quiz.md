# EKS Auto Mode NodePool 구성 퀴즈

> **관련 문서**: [NodePool 구성](../../eks-auto-mode/02-nodepool-configuration.md)

## 객관식 문제

### 1. EKS Auto Mode에서 기본 제공되는 NodePool은 무엇인가요?

- A) default, worker
- B) general-purpose, system
- C) compute, memory
- D) primary, secondary

<details>
<summary>정답 보기</summary>

**정답: B) general-purpose, system**

**설명:**
EKS Auto Mode는 두 가지 기본 NodePool을 제공합니다:
- **general-purpose**: 범용 워크로드를 위한 기본 NodePool로, 다양한 인스턴스 타입(c, m, r)과 Spot/On-Demand를 지원
- **system**: 시스템 컴포넌트(CoreDNS, kube-proxy 등)를 위한 NodePool로, On-Demand만 사용하고 CriticalAddonsOnly taint가 적용됨

```yaml
# Auto Mode 활성화 예시
autoModeConfig:
  enabled: true
  nodePools:
    - general-purpose
    - system
```

</details>

### 2. NodeClass에서 IMDSv2를 필수로 설정하는 방법은 무엇인가요?

- A) `httpTokens: optional`
- B) `httpTokens: required`
- C) `httpEndpoint: disabled`
- D) `httpPutResponseHopLimit: 0`

<details>
<summary>정답 보기</summary>

**정답: B) `httpTokens: required`**

**설명:**
NodeClass의 `metadataOptions`에서 `httpTokens: required`를 설정하면 IMDSv2만 허용되어 보안이 강화됩니다.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: secure-nodeclass
spec:
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 2
    httpTokens: required  # IMDSv2 필수
```

**보안 모범 사례:**
- `httpTokens: required`: IMDSv2 강제 사용
- `httpPutResponseHopLimit: 1`: Pod의 IMDS 직접 접근 차단

</details>

### 3. EKS Auto Mode에서 지원하는 AMI 패밀리는 무엇인가요?

- A) Amazon Linux 2, Ubuntu
- B) AL2023, Bottlerocket
- C) Windows Server, Amazon Linux 2
- D) Red Hat Enterprise Linux, Ubuntu

<details>
<summary>정답 보기</summary>

**정답: B) AL2023, Bottlerocket**

**설명:**
EKS Auto Mode는 AL2023(Amazon Linux 2023)과 Bottlerocket AMI 패밀리만 지원합니다. Windows 노드는 지원되지 않습니다.

**AMI 패밀리별 특징:**
- **AL2023**: 범용적인 용도, 풍부한 패키지 지원
- **Bottlerocket**: 컨테이너 전용 OS, 더 빠른 부팅 시간, 보안 강화

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: custom-nodeclass
spec:
  amiFamily: Bottlerocket  # 또는 AL2023
```

</details>

### 4. GPU 워크로드를 위한 NodePool에서 GPU 제조사를 지정하는 레이블 키는 무엇인가요?

- A) `karpenter.k8s.aws/gpu-vendor`
- B) `karpenter.k8s.aws/instance-gpu-manufacturer`
- C) `nvidia.com/gpu-family`
- D) `karpenter.sh/gpu-type`

<details>
<summary>정답 보기</summary>

**정답: B) `karpenter.k8s.aws/instance-gpu-manufacturer`**

**설명:**
GPU 인스턴스를 선택할 때 제조사를 지정할 수 있습니다.

```yaml
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["g", "p"]
        - key: karpenter.k8s.aws/instance-gpu-manufacturer
          operator: In
          values: ["nvidia"]
```

</details>

### 5. NodePool에서 특정 인스턴스 세대를 지정하는 올바른 방법은 무엇인가요?

- A) `node.kubernetes.io/instance-generation: "6"`
- B) `karpenter.k8s.aws/instance-generation` with `operator: In`
- C) `eks.amazonaws.com/generation: "6"`
- D) `instance-generation: 6`

<details>
<summary>정답 보기</summary>

**정답: B) `karpenter.k8s.aws/instance-generation` with `operator: In`**

**설명:**
Karpenter 레이블을 사용하여 인스턴스 세대를 지정합니다.

```yaml
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]  # 6세대 이상
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
```

</details>

### 6. NodeClass에서 프라이빗 서브넷만 사용하도록 설정하는 올바른 방법은 무엇인가요?

- A) `subnetType: private`
- B) `subnetSelectorTerms` with internal-elb tag
- C) `privateSubnetsOnly: true`
- D) `networkType: private`

<details>
<summary>정답 보기</summary>

**정답: B) `subnetSelectorTerms` with internal-elb tag**

**설명:**
`subnetSelectorTerms`를 사용하여 프라이빗 서브넷을 선택합니다.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: secure-nodeclass
spec:
  # 프라이빗 서브넷만 사용
  subnetSelectorTerms:
    - tags:
        kubernetes.io/role/internal-elb: "1"
```

퍼블릭 서브넷은 `kubernetes.io/role/elb: "1"` 태그를 사용합니다.

</details>

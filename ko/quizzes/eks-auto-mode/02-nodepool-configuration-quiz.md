# EKS Auto Mode NodePool 구성 퀴즈

> **관련 문서**: [NodePool 구성](../../eks-auto-mode/02-nodepool-configuration.md)

## 객관식 문제

### 1. EKS Auto Mode에서 선택적으로 활성화하는 기본 NodePool은 무엇인가요?

- A) default, worker
- B) general-purpose, system
- C) compute, memory
- D) primary, secondary

<details>
<summary>정답 보기</summary>

**정답: B) general-purpose, system**

**설명:**
활성화된 `general-purpose`와 `system`은 5세대 이상 C/M/R 계열 On-Demand를 사용합니다. General-purpose는 amd64이며 system은 amd64·arm64와 `CriticalAddonsOnly` taint를 사용합니다. Spot은 커스텀 풀로 구성하세요. Auto Mode의 로컬 DNS·서비스 네트워킹 기능은 system 풀에 배치해야 하는 일반 Pod가 아닙니다.

```yaml
# eksctl configuration fragment
autoModeConfig:
  enabled: true
  nodePools: [general-purpose, system]
```

기본 풀 이름을 제거하면 해당 NodePool과 관리 노드가 drain·종료됩니다. 둘 다 비활성화하면 `default`가 존재한다고 가정하지 말고 커스텀 NodeClass를 제공해야 합니다.

</details>

### 2. Auto Mode 노드의 IMDS는 어떻게 구성되나요?

- A) NodeClass에서 metadataOptions.httpTokens: optional을 설정한다
- B) AWS가 IMDSv2와 hop limit 1을 강제하며 NodeClass에서 바꿀 수 없다
- C) hop limit을 0으로 설정해야 IMDSv2가 동작한다
- D) AL2023을 선택하면 IMDS 인증을 끌 수 있다

<details>
<summary>정답 보기</summary>

**정답: B) AWS가 IMDSv2와 hop limit 1을 강제하며 NodeClass에서 바꿀 수 없다**

**설명:**
관리형 인스턴스 기본값은 IMDSv2와 hop limit 1이며 Auto Mode에서 변경할 수 없습니다. 이전 `metadataOptions` 예제는 다른 API의 설정이었습니다. Hop limit은 non-host-network Pod를 제한하지만 host-network 워크로드를 포함한 모든 Pod의 격리를 보장하지 않습니다. 노드 자격 증명에 의존하기보다 워크로드 ID와 명시적인 리전·설정을 사용하세요. [관리형 인스턴스 제한](https://docs.aws.amazon.com/eks/latest/userguide/automode-learn-instances.html)을 참고하세요.

</details>

### 3. Auto Mode 노드의 운영체제 이미지는 누가 선택하나요?

- A) 사용자가 amiFamily에서 Amazon Linux 2 또는 Ubuntu를 선택한다
- B) AWS가 적절한 관리형 Bottlerocket 변형을 선택한다
- C) 사용자가 임의의 Windows AMI를 제공한다
- D) NodePool weight가 Bottlerocket 대신 AL2023을 선택한다

<details>
<summary>정답 보기</summary>

**정답: B) AWS가 적절한 관리형 Bottlerocket 변형을 선택한다**

**설명:**
Auto Mode는 AWS 관리 Bottlerocket 변형을 사용합니다. AWS NodeClass에 `amiFamily: AL2023` 또는 `amiFamily: Bottlerocket` 선택지를 제공하지 않습니다. 스토리지, 네트워크, 인증서와 지원되는 커널 설정에는 문서화된 NodeClass 필드를 사용하세요. 임의 AMI 선택이나 셸 user data와는 다릅니다.

</details>

### 4. Auto Mode NodePool에서 GPU 제조사를 선택하는 label은 무엇인가요?

- A) karpenter.k8s.aws/gpu-vendor
- B) eks.amazonaws.com/instance-gpu-manufacturer
- C) nvidia.com/gpu-family
- D) karpenter.sh/gpu-type

<details>
<summary>정답 보기</summary>

**정답: B) eks.amazonaws.com/instance-gpu-manufacturer**

**설명:**
AWS Auto Mode label인 `eks.amazonaws.com/instance-gpu-manufacturer`를 사용합니다. NVIDIA GPU 하드웨어에는 다음과 같은 requirements를 지정할 수 있습니다.

```yaml
# Requirements fragment inside a complete NodePool
requirements:
  - key: eks.amazonaws.com/instance-category
    operator: In
    values: ["g", "p"]
  - key: eks.amazonaws.com/instance-gpu-manufacturer
    operator: In
    values: ["nvidia"]
```

하드웨어 선택만으로 컨테이너에 GPU가 할당되지는 않습니다. Pod도 `nvidia.com/gpu` 등의 적절한 확장 리소스를 요청하고 호환되는 이미지·런타임을 사용해야 합니다. 이번 감사에서 GPU 실행은 하지 않았습니다.

</details>

### 5. EC2 6세대 이상을 선택하는 조건은 무엇인가요?

- A) node.kubernetes.io/instance-generation: "6"
- B) eks.amazonaws.com/instance-generation에 Gt와 값 "5"를 사용한다
- C) eks.amazonaws.com/generation: "6"
- D) instance-generation: 6

<details>
<summary>정답 보기</summary>

**정답: B) eks.amazonaws.com/instance-generation에 Gt와 값 "5"를 사용한다**

**설명:**
`Gt`는 숫자의 엄격한 하한이므로 `Gt ["5"]`는 6세대 이상을 선택합니다. `In ["6"]`은 정확히 6세대만 선택하며 같은 조건이 아닙니다. 두 조건 모두 최신 세대 하나만 선택한다는 뜻은 아닙니다.

```yaml
# Requirements fragment inside a complete NodePool
requirements:
  - key: eks.amazonaws.com/instance-generation
    operator: Gt
    values: ["5"]
```

</details>

### 6. NodeClass에서 프라이빗 서브넷을 어떻게 선택하나요?

- A) subnetType: private을 설정한다
- B) 검토한 서브넷 ID·태그로 선택하고 라우팅과 IP 설정을 확인한다
- C) privateSubnetsOnly: true를 설정한다
- D) networkType: private을 설정한다

<details>
<summary>정답 보기</summary>

**정답: B) 검토한 서브넷 ID·태그로 선택하고 라우팅과 IP 설정을 확인한다**

**설명:**
`subnetSelectorTerms`는 ID나 태그로 선택합니다. `kubernetes.io/role/internal-elb` 같은 태그는 관례이며 프라이빗 라우팅 테이블의 증거가 아닙니다. 여러 term은 대안이며 한 term의 여러 태그는 함께 일치해야 합니다. VPC/AZ 선택, 라우팅과 공인 IP 동작을 검토하세요.

```yaml
# Selection fragment; a complete NodeClass also needs identity and security groups
subnetSelectorTerms:
  - tags:
      kubernetes.io/role/internal-elb: "1"
      Environment: production
advancedNetworking:
  associatePublicIPAddress: false
```

`associatePublicIPAddress: false`는 공인 IP 할당을 막지만 NAT 경로나 VPC 엔드포인트를 만들지는 않습니다. 완전한 NodeClass의 identity·보안 그룹 구성을 제공하고 readiness를 확인해야 합니다.

</details>

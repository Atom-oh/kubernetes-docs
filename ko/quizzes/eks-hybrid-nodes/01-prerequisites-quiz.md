# EKS Hybrid Nodes 사전 요구 사항 퀴즈

> **관련 문서**: [사전 요구 사항](../../eks-hybrid-nodes/01-prerequisites.md)
> **마지막 업데이트**: 2026년 9월 12일

## 객관식 문제

### 1. EKS Hybrid Nodes 인프라로 등록하는 지원 시나리오가 아닌 것은 무엇인가요?

- A) 호환 on-prem GPU 서버 사용
- B) 로컬 데이터 가까이에서 앱 처리
- C) 일반 EC2/cloud machine을 hybrid-node 인프라로 등록
- D) 복구를 검증한 연결형 edge workload

<details>
<summary>정답 보기</summary>

**정답: C) 일반 EC2/cloud machine을 hybrid-node 인프라로 등록**

**설명:**
Hybrid-node 인프라는 고객이 운영하는 on-prem/edge 물리·가상 host용이며 cloud 인프라는 지원하지 않습니다. EC2를 hybrid node로 등록하면 hybrid 요금도 발생합니다. Cloud node에는 일반 AWS compute type을 사용하세요. 안정적인 연결이 필요하며 placement label만으로 규정 준수·offline 운영이 입증되지는 않습니다.

</details>

### 2. 현재 AWS hybrid 통합 matrix에 맞는 OS 설명은 무엇인가요?

- A) Windows Server만 가능
- B) Ubuntu 20.04/22.04/24.04, RHEL 8/9, 가상화 AL2023, 지원 Bottlerocket VMware 변형
- C) 모든 macOS
- D) 모든 Linux image가 자동으로 AWS OS 지원을 받음

<details>
<summary>정답 보기</summary>

**정답: B) Ubuntu 20.04/22.04/24.04, RHEL 8/9, 가상화 AL2023, 지원 Bottlerocket VMware 변형**

**설명:**
Vendor security maintenance·아키텍처·선택 CNI/kernel을 검토합니다. Bottlerocket VMware v1.37.0+는 x86_64 전용이며 자체 bootstrap을 사용합니다. AL2023은 on-prem 가상화용이고 EC2 밖 AWS OS 지원 대상이 아닙니다. ARM의 EKS kube-proxy 1.31+에는 ARMv8.2+crypto가 필요하며 일반 kernel 5.4 기준·CPU 이름만으로 충분하지 않습니다.

</details>

### 3. GPU workload 호환성 평가에서 잘못된 주장은 무엇인가요?

- A) Driver와 CUDA/framework image 호환성이 중요
- B) Memory 요구는 workload에 따라 다름
- C) 지원 OS/kernel·container runtime이 중요
- D) GPU가 있으면 CPU 아키텍처를 무시해도 됨

<details>
<summary>정답 보기</summary>

**정답: D) GPU가 있으면 CPU 아키텍처를 무시해도 됨**

**설명:**
CPU 아키텍처·GPU variant·driver·OS/kernel·container toolkit/runtime·앱 image를 함께 검증합니다. Hybrid Nodes의 보편적인 GPU 최소 4GB나 고정 driver 525/550 요구는 없습니다. 올바른 container 실행만을 위해 host nvcc compiler가 필수는 아니며 nvidia-smi와 nvcc는 다른 구성 요소를 보여줍니다.

</details>

### 4. 기본 host 리소스 안내를 어떻게 해석해야 하나요?

- A) 1 core/512MB면 충분함을 보장
- B) AWS는 1 vCPU/1 GiB RAM 이상을 권장하며 엄격한 보편적 최소값은 없음
- C) 모든 workload에 정확히 4 core/8GB 필요
- D) 50GB disk가 readiness를 보장

<details>
<summary>정답 보기</summary>

**정답: B) AWS는 1 vCPU/1 GiB RAM 이상을 권장하며 엄격한 보편적 최소값은 없음**

**설명:**
OS·kubelet/runtime·CNI/agent·image/log·실제 workload를 따로 산정합니다. 이전 2-core/2GB 답과 20/50/100GB disk는 일치하지 않는 계획 예시였으며 검증된 workload 최소값이 아닙니다. AWS의 100Mbps/200ms도 일반 안내이지 보편적 합격 임계값이 아닙니다.

</details>

### 5. EKS Hybrid Node가 된다는 이유만으로 필수가 되지 않는 구성 요소는 무엇인가요?

- A) 호환 CRI runtime인 containerd 등
- B) kubelet
- C) Docker Engine
- D) 선택한 AWS credential/authentication helper

<details>
<summary>정답 보기</summary>

**정답: C) Docker Engine**

**설명:**
Docker의 containerd package source 사용이 Docker Engine 실행 요구는 아닙니다. 비 Bottlerocket host는 nodeadm install로 의존성 설치, config check로 입력 검증, init으로 구성·join합니다. SSM signing key 변경으로 설치/upgrade에는 nodeadm 1.0.19+가 필요하며 검토 릴리스는 1.0.20입니다. RHEL은 distro 대신 docker 또는 runtime 사전 설치 후 none을 사용합니다.

</details>

### 6. H100 Hybrid Nodes 배포의 올바른 접근은 무엇인가요?

- A) 모든 host에 450.x 설치
- B) 과거 525.x 예시가 영구적으로 충분하다고 판단
- C) Framework와 무관하게 정확히 535.x 요구
- D) 지원 GPU/OS/driver/CUDA/runtime 조합 선택 후 앱 검증

<details>
<summary>정답 보기</summary>

**정답: D) 지원 GPU/OS/driver/CUDA/runtime 조합 선택 후 앱 검증**

**설명:**
이전 표는 최소·권장 driver 버전을 혼합하고 답과도 충돌했습니다. 450/525/535/545/550은 현재의 보편적인 배포 계약이 아닙니다. 정확한 H100 variant·지원 driver branch·framework image·필요 기능을 확인하고 workload를 옮긴 test host에서 변경을 검증하세요. 이번 감사에서는 GPU 실행·model benchmark를 하지 않았습니다.

</details>

## 참고 자료

- [Hybrid prerequisites](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-prereqs.html)
- [Hybrid OS compatibility](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
- [nodeadm reference](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)

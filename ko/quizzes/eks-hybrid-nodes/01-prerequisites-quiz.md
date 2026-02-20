# EKS Hybrid Nodes 사전 요구사항 퀴즈

> **관련 문서**: [사전 요구사항](../../eks-hybrid-nodes/01-prerequisites.md)

## 객관식 문제

### 1. EKS Hybrid Nodes의 주요 사용 사례로 적합하지 않은 것은?

A. 온프레미스 데이터센터의 GPU 서버 활용
B. 규제 준수를 위한 데이터 로컬리티 요구사항
C. 순수 클라우드 네이티브 워크로드 실행
D. 레이턴시에 민감한 엣지 워크로드

<details>
<summary>정답 보기</summary>

**정답: C. 순수 클라우드 네이티브 워크로드 실행**

**설명:**
순수 클라우드 네이티브 워크로드는 일반 EKS 노드 그룹이나 Fargate에서 실행하는 것이 더 효율적입니다. Hybrid Nodes는 특별한 요구사항(온프레미스, 엣지, 규제 등)이 있을 때 사용합니다.

**EKS Hybrid Nodes 적합한 사용 사례:**
- 온프레미스 GPU/특수 하드웨어 활용
- 데이터 주권/규제 준수 요구사항
- 레이턴시에 민감한 엣지 컴퓨팅
- 클라우드 마이그레이션 과도기
- 기존 인프라 투자 보호

</details>

### 2. EKS Hybrid Nodes에서 지원되는 운영 체제로 올바른 것은?

A. Windows Server 2019만 지원
B. Ubuntu 20.04/22.04, Amazon Linux 2023, RHEL 8/9
C. macOS Ventura 이상
D. FreeBSD 13 이상

<details>
<summary>정답 보기</summary>

**정답: B. Ubuntu 20.04/22.04, Amazon Linux 2023, RHEL 8/9**

**설명:**
EKS Hybrid Nodes는 Linux 기반 운영 체제만 지원합니다. 지원되는 OS는 다음과 같습니다:
- Ubuntu 20.04 LTS, 22.04 LTS
- Amazon Linux 2023
- Red Hat Enterprise Linux (RHEL) 8, 9
- Bottlerocket (컨테이너 최적화 OS)

```bash
# OS 버전 확인
cat /etc/os-release

# 커널 버전 확인 (5.4 이상 권장)
uname -r
```

</details>

### 3. Hybrid Nodes에서 GPU 워크로드를 실행하기 위한 최소 요구사항으로 올바르지 않은 것은?

A. NVIDIA 드라이버 525 이상
B. CUDA Toolkit 11.8 이상
C. GPU 메모리 최소 4GB
D. x86_64 또는 arm64 아키텍처 필수

<details>
<summary>정답 보기</summary>

**정답: D. x86_64 또는 arm64 아키텍처 필수**

**설명:**
x86_64 또는 arm64 아키텍처는 CPU 아키텍처 요구사항이며, GPU 워크로드 실행을 위한 직접적인 요구사항은 아닙니다. GPU 워크로드의 주요 요구사항은:

- **NVIDIA 드라이버**: 525 이상 (CUDA 12 지원)
- **CUDA Toolkit**: 11.8 이상
- **GPU 메모리**: 워크로드에 따라 다르나 최소 4GB 이상 권장
- **containerd**: 1.6 이상 (GPU 컨테이너 지원)

```bash
# NVIDIA 드라이버 버전 확인
nvidia-smi --query-gpu=driver_version --format=csv,noheader

# CUDA 버전 확인
nvcc --version
```

</details>

### 4. EKS Hybrid Nodes의 하드웨어 최소 요구사항으로 올바른 것은?

A. CPU 1코어, 메모리 512MB
B. CPU 2코어, 메모리 2GB
C. CPU 4코어, 메모리 8GB
D. CPU 8코어, 메모리 16GB

<details>
<summary>정답 보기</summary>

**정답: B. CPU 2코어, 메모리 2GB**

**설명:**
EKS Hybrid Nodes의 최소 하드웨어 요구사항은 다음과 같습니다:

| 리소스 | 최소 요구사항 | 권장 사항 |
|--------|-------------|----------|
| CPU | 2코어 | 4코어 이상 |
| 메모리 | 2GB | 4GB 이상 |
| 디스크 | 20GB | 50GB 이상 (SSD 권장) |
| 네트워크 | 100Mbps | 1Gbps 이상 |

실제 운영 환경에서는 워크로드 요구사항에 따라 더 높은 사양이 필요할 수 있습니다.

</details>

### 5. EKS Hybrid Nodes 구성 시 필수 소프트웨어 구성 요소가 아닌 것은?

A. containerd 런타임
B. kubelet
C. Docker Engine
D. aws-iam-authenticator

<details>
<summary>정답 보기</summary>

**정답: C. Docker Engine**

**설명:**
EKS Hybrid Nodes는 containerd를 컨테이너 런타임으로 사용하며, Docker Engine은 필수가 아닙니다. 필수 구성 요소는:

- **containerd**: 컨테이너 런타임 (1.6 이상)
- **kubelet**: Kubernetes 노드 에이전트
- **aws-iam-authenticator**: AWS IAM 인증
- **CNI 플러그인**: 컨테이너 네트워킹

```bash
# nodeadm이 자동으로 설치하는 구성 요소
sudo nodeadm init --config-source file://nodeadm-config.yaml

# 설치된 구성 요소 확인
systemctl status containerd
systemctl status kubelet
```

</details>

### 6. H100 GPU를 Hybrid Nodes에서 사용할 때 필요한 최소 NVIDIA 드라이버 버전은?

A. 450.x
B. 470.x
C. 525.x
D. 535.x

<details>
<summary>정답 보기</summary>

**정답: D. 535.x**

**설명:**
NVIDIA H100 GPU는 Hopper 아키텍처로, 최신 드라이버가 필요합니다:

| GPU 모델 | 최소 드라이버 버전 | 권장 드라이버 버전 |
|---------|------------------|------------------|
| A100 | 450.x | 525.x 이상 |
| H100 | 525.x | 535.x 이상 |
| H200 | 535.x | 545.x 이상 |

```bash
# H100 드라이버 설치 확인
nvidia-smi

# 드라이버 업데이트
sudo apt-get update
sudo apt-get install nvidia-driver-535
```

H100의 주요 기능(MIG 확장, Transformer Engine 등)을 완전히 활용하려면 535.x 이상의 드라이버가 권장됩니다.

</details>


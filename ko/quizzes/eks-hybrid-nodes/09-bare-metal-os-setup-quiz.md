# 베어메탈 서버 OS 설치 퀴즈

> **관련 문서**: [베어메탈 서버 OS 설치 및 마이그레이션 가이드](../../eks-hybrid-nodes/09-bare-metal-os-setup.md)

## 객관식 문제

### 1. VMware에서 EKS Hybrid Nodes로 전환 시 기대할 수 있는 주요 이점이 아닌 것은?

A. VMware 라이선스 비용 절감
B. 하이퍼바이저 오버헤드 제거로 성능 최적화
C. 자동으로 모든 워크로드가 컨테이너화됨
D. 라이선스 관리 단순화

<details>
<summary>정답 보기</summary>

**정답: C. 자동으로 모든 워크로드가 컨테이너화됨**

**설명:**
VMware에서 EKS Hybrid Nodes로 전환하면 라이선스 비용 절감, 하이퍼바이저 오버헤드 제거, 라이선스 관리 단순화 등의 이점이 있습니다. 그러나 워크로드 컨테이너화는 자동으로 이루어지지 않습니다. VM 기반 워크로드를 컨테이너로 마이그레이션하는 작업은 별도의 마이그레이션 단계에서 수동으로 수행해야 합니다.

**마이그레이션 단계:**
- Phase 1: 병행 운영 인프라 구축
- Phase 2: **워크로드 컨테이너화** (수동 작업 필요)
- Phase 3: 네트워크 전환
- Phase 4: VMware 폐기

</details>

### 2. Bottlerocket OS가 지원되는 환경은?

A. 베어메탈 서버만
B. VMware 환경만
C. 베어메탈과 VMware 모두
D. AWS EC2만

<details>
<summary>정답 보기</summary>

**정답: B. VMware 환경만**

**설명:**
Bottlerocket은 EKS Hybrid Nodes에서 VMware 환경에서만 지원됩니다 (v1.37.0+, x86_64만). 베어메탈 서버에서는 Bottlerocket을 사용할 수 없으며, Ubuntu, RHEL, 또는 Amazon Linux 2023을 사용해야 합니다.

**OS 지원 매트릭스:**
| OS | 베어메탈 | VMware |
|----|---------|--------|
| Ubuntu 22.04/24.04 LTS | O | O |
| RHEL 8/9 | O | O |
| Amazon Linux 2023 | O | O |
| Bottlerocket v1.37.0+ | **X** | O |

</details>

### 3. Ubuntu에서 PXE 자동 설치를 위해 사용하는 설정 도구는?

A. Kickstart
B. Autoinstall (cloud-init 기반)
C. govc (TOML)
D. preseed

<details>
<summary>정답 보기</summary>

**정답: B. Autoinstall (cloud-init 기반)**

**설명:**
Ubuntu는 Autoinstall (cloud-init 기반)을 사용하여 PXE 자동 설치를 수행합니다. RHEL은 Kickstart를 사용하고, Bottlerocket은 govc와 TOML 설정 파일을 사용합니다.

```yaml
#cloud-config
autoinstall:
  version: 1
  locale: en_US.UTF-8
  keyboard:
    layout: us
  storage:
    layout:
      name: lvm
  # ...
```

</details>

### 4. RHEL에서 nodeadm install 명령 실행 시 반드시 사용해야 하는 옵션은?

A. `--selinux-permissive`
B. `--containerd-source docker`
C. `--skip-verification`
D. `--force`

<details>
<summary>정답 보기</summary>

**정답: B. `--containerd-source docker`**

**설명:**
RHEL에서는 반드시 `--containerd-source docker` 옵션을 사용해야 합니다. 배포판 기본 소스는 지원되지 않습니다.

```bash
# 올바른 설치 방법
sudo nodeadm install 1.31 --credential-provider ssm --containerd-source docker

# 잘못된 설치 방법 (실패함)
# sudo nodeadm install 1.31 --credential-provider ssm
```

</details>

### 5. Ubuntu 24.04에서 containerd 관련 문제가 발생할 때 필요한 조치는?

A. SELinux를 비활성화
B. containerd를 v1.7.19+로 업데이트하거나 AppArmor 변경 후 재부팅
C. firewalld를 중지
D. systemd를 재시작

<details>
<summary>정답 보기</summary>

**정답: B. containerd를 v1.7.19+로 업데이트하거나 AppArmor 변경 후 재부팅**

**설명:**
Ubuntu 24.04에서는 containerd v1.7.19 이상이 필요하거나 AppArmor 프로파일 변경이 필요합니다 (Ubuntu 버그 #2065423). 변경 후에는 반드시 재부팅해야 합니다. 재부팅하지 않으면 Pod가 정상적으로 종료되지 않을 수 있습니다.

```bash
# containerd 버전 확인
containerd --version

# 버전이 1.7.19 미만인 경우 AppArmor 프로파일 수정
sudo aa-remove-unknown

# 변경 적용을 위해 재부팅 필요
sudo reboot
```

</details>

### 6. 에어갭(air-gapped) 환경에서 권장되는 자격 증명 프로바이더는?

A. SSM Hybrid Activations
B. IAM Roles Anywhere
C. EC2 Instance Profile
D. AWS Access Keys

<details>
<summary>정답 보기</summary>

**정답: B. IAM Roles Anywhere**

**설명:**
에어갭 환경에서는 IAM Roles Anywhere를 사용해야 합니다. SSM Hybrid Activations는 SSM 엔드포인트에 접근이 필요하므로 에어갭 환경에서 사용할 수 없습니다. IAM Roles Anywhere는 로컬 CA와 X.509 인증서를 사용하므로 인터넷 연결 없이도 작동합니다.

| 조건 | 권장 프로바이더 |
|------|----------------|
| PKI 인프라 없음 | SSM |
| 기존 PKI 인프라 있음 | IAM Roles Anywhere |
| 에어갭(air-gapped) 환경 | **IAM Roles Anywhere** |
| 간단한 설정, 인터넷 연결 가능 | SSM |

</details>

### 7. VMware에서 EKS Hybrid Nodes로 마이그레이션할 때 NSX-T의 대체 솔루션은?

A. AWS Transit Gateway
B. Cilium BGP
C. Amazon VPC CNI
D. Calico Enterprise

<details>
<summary>정답 보기</summary>

**정답: B. Cilium BGP**

**설명:**
VMware에서 EKS Hybrid Nodes로 마이그레이션할 때 NSX-T 네트워크 기능은 Cilium BGP로 전환합니다. Phase 3(네트워크 전환)에서 NSX-T에서 Cilium BGP로 전환하고, 로드 밸런서 및 인그레스 설정을 이전합니다.

**마이그레이션 Phase 3:**
- NSX-T에서 Cilium BGP로 전환
- 로드 밸런서 및 인그레스 설정 이전
- DNS 레코드 업데이트

</details>

### 8. OpenShift의 Route는 EKS Hybrid Nodes에서 어떤 리소스로 대체됩니까?

A. Service
B. Ingress / Gateway API
C. NetworkPolicy
D. ConfigMap

<details>
<summary>정답 보기</summary>

**정답: B. Ingress / Gateway API**

**설명:**
OpenShift에서 EKS Hybrid Nodes로 마이그레이션할 때, OpenShift의 Route는 표준 Kubernetes Ingress 또는 Gateway API로 대체됩니다.

**OpenShift → EKS 개념 매핑:**
| OpenShift | EKS Hybrid Nodes |
|-----------|-----------------|
| **Route** | **Ingress / Gateway API** |
| SCC | PSS (Pod Security Standards) |
| OLM | Helm / EKS Add-ons |
| MachineSet | nodeadm + Ansible |
| ImageStream | ECR |
| BuildConfig | External CI/CD |
| DeploymentConfig | Deployment |

</details>

### 9. PXE 부트 인프라 구성에 필요하지 않은 서버는?

A. DHCP 서버
B. TFTP 서버
C. HTTP 서버
D. FTP 서버

<details>
<summary>정답 보기</summary>

**정답: D. FTP 서버**

**설명:**
PXE 부트 인프라 구성에는 DHCP 서버, TFTP 서버, HTTP 서버가 필요합니다. FTP 서버는 PXE 부트에 필요하지 않습니다.

**PXE 부트 인프라:**
- **DHCP 서버**: IP 주소 할당, next-server(TFTP 서버 주소), filename(pxelinux.0) 제공
- **TFTP 서버**: 부트로더(pxelinux.0), 커널(vmlinuz), 초기 RAM 디스크(initrd.img) 제공
- **HTTP 서버**: OS 설치 이미지, Autoinstall/Kickstart 설정 파일, nodeadm 바이너리 제공

</details>

### 10. 32 vCPU 서버 기준 EKS Hybrid Nodes의 연간 비용 계산에 사용되는 시간당 vCPU 요금은?

A. $0.001
B. $0.01
C. $0.10
D. $1.00

<details>
<summary>정답 보기</summary>

**정답: B. $0.01**

**설명:**
EKS Hybrid Nodes는 vCPU당 시간당 $0.01로 과금됩니다 (리전별 상이). 32 vCPU 서버의 연간 비용은 다음과 같이 계산됩니다:

```
32 vCPU × $0.01/시간 × 8,760시간(1년) = $2,803.20/노드/년
```

**규모별 연간 비용 비교 (32 vCPU 서버 기준):**
| 규모 | VMware vSphere (연간) | OpenShift (연간) | EKS Hybrid Nodes (연간) |
|------|----------------------|------------------|------------------------|
| 10 노드 | ~$45,000-85,000 | ~$25,000-50,000 | ~$28,032 |
| 50 노드 | ~$225,000-425,000 | ~$125,000-250,000 | ~$140,160 |
| 100 노드 | ~$450,000-850,000 | ~$250,000-500,000 | ~$280,320 |

</details>

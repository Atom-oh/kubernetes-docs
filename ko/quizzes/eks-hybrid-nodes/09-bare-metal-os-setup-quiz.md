<span id="베어메탈-서버-os-설치-퀴즈"></span>

# 베어메탈 서버 OS 설치 및 마이그레이션 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

> **관련 문서**: [가이드](../../eks-hybrid-nodes/09-bare-metal-os-setup.md)

## 객관식 문제

<span id="_1-vmware에서-eks-hybrid-nodes로-전환-시-기대할-수-있는-주요-이점이-아닌-것은"></span>

### 1. Hybrid Nodes에 베어메탈을 검토할 이유가 될 수 있는 것은?

- A) 모든 VM이 자동으로 컨테이너로 변환됨
- B) 하이퍼바이저 계층 제거 가능성을 총비용·workload 요구와 비교 평가
- C) AWS 연결 없이 운영 가능
- D) 모든 소프트웨어 계약 자동 취소

<details>
<summary>정답 보기</summary>

**정답: B) 하이퍼바이저 계층 제거 가능성을 총비용·workload 요구와 비교 평가**

**설명:**

하이퍼바이저 제거는 라이선스와 실행 overhead를 바꿀 수 있지만 총비용 절감·성능 향상을 보장하지 않습니다. 컨테이너화, 데이터 이전, 가용성, 지원과 계약 의무는 별도로 검토합니다. 본문에 보존한 미검증 과거 추정치에서 절감률을 도출하지 않습니다.

</details>

<span id="_9-pxe-부트-인프라-구성에-필요하지-않은-서버는"></span>

### 2. Legacy PXE boot 설계에서 일반적으로 사용하는 구성 요소는?

- A) DNS와 NFS만
- B) DHCP/ProxyDHCP boot 정보와 TFTP boot server
- C) FTP와 SMTP
- D) LDAP와 Kerberos만

<details>
<summary>정답 보기</summary>

**정답: B) DHCP/ProxyDHCP boot 정보와 TFTP boot server**

**설명:**

Legacy PXE는 보통 DHCP boot 정보와 TFTP를 사용합니다. Installer 콘텐츠를 HTTP로 전달할 수 있으며 UEFI HTTP/iPXE는 다른 경로를 사용할 수 있습니다. pxelinux.0은 모든 UEFI의 bootloader가 아닙니다. Firmware/loader 신뢰와 provisioning 분리를 확인하고 activation code·key를 공유 비인증 server에 공개하지 않습니다.

</details>

<span id="_3-ubuntu에서-pxe-자동-설치를-위해-사용하는-설정-도구는"></span>

### 3. OS 자동 설치 방식을 올바르게 연결한 것은?

- A) Ubuntu: Kickstart; RHEL: Autoinstall
- B) Ubuntu Server: Subiquity Autoinstall YAML; RHEL: Kickstart
- C) Ubuntu: govc; RHEL: TOML
- D) 둘 다 installer에서 검증하지 않은 최신 nodeadm 다운로드가 필수

<details>
<summary>정답 보기</summary>

**정답: B) Ubuntu Server: Subiquity Autoinstall YAML; RHEL: Kickstart**

**설명:**

Cloud-init으로 Ubuntu Autoinstall 구성을 전달할 수 있으며 RHEL은 Kickstart를 사용합니다. 선택한 installer 버전과 호스트별 storage/network를 검증합니다. YAML parser·ksvalidator 통과가 대상 disk 삭제의 안전성이나 설치 후 인증 성공을 입증하지는 않습니다.

</details>

<span id="_2-bottlerocket-os가-지원되는-환경은"></span>

### 4. 검토한 AWS 지침에서 EKS Hybrid Nodes에 지원되는 Bottlerocket 배치는?

- A) 모든 bare-metal variant
- B) 모든 hypervisor와 architecture
- C) x86_64의 지원되는 VMware variant >=1.37.0
- D) EC2만

<details>
<summary>정답 보기</summary>

**정답: C) x86_64의 지원되는 VMware variant >=1.37.0**

**설명:**

이는 EKS Hybrid 지원 범위이며 모든 Bottlerocket 제품 variant에 대한 설명이 아닙니다. Hybrid bare metal은 지원되는 Ubuntu/RHEL 호스트를 검토합니다. AL2023도 온프레미스 가상화 guest 선택지이며 일반 bare-metal 지원 경로가 아닙니다. Kubernetes variant 가용성과 현재 수명주기 조건을 따로 확인합니다.

</details>

### 5. Bottlerocket settings와 govc를 어떻게 구분해야 하나요?

- A) govc가 Bottlerocket TOML parser임
- B) Bottlerocket은 Ubuntu와 동일한 nodeadm YAML 사용
- C) Bottlerocket은 settings/bootstrap 입력을 사용하고 govc는 VMware VM 수명주기·user-data 전달을 관리
- D) settings.hybrid.ssm은 표준 지원 settings namespace

<details>
<summary>정답 보기</summary>

**정답: C) Bottlerocket은 settings/bootstrap 입력을 사용하고 govc는 VMware VM 수명주기·user-data 전달을 관리**

**설명:**

버전별 Bottlerocket settings/bootstrap 절차를 사용합니다. 이전 settings.hybrid.* 예제는 유효하지 않았습니다. govc는 VM 복제·구성·전원 제어를 할 수 있지만 OS settings parser가 아닙니다. Guestinfo·user-data를 보호하며 base64를 credential 암호화로 해석하지 않습니다.

</details>

<span id="_6-에어갭-air-gapped-환경에서-권장되는-자격-증명-프로바이더는"></span>

### 6. Hybrid credential provider와 연결성에 대한 올바른 설명은?

- A) IAM Roles Anywhere는 AWS 연결 없이 무기한 동작
- B) 두 방식 모두 필요한 AWS API에 접근해야 하며 private 연결로 public internet을 피할 수 있음
- C) SSM에는 항상 직접 public internet이 필요
- D) Kubernetes ServiceAccount가 호스트 Hybrid credential provider를 대체

<details>
<summary>정답 보기</summary>

**정답: B) 두 방식 모두 필요한 AWS API에 접근해야 하며 private 연결로 public internet을 피할 수 있음**

**설명:**

관리되는 PKI가 없다면 SSM으로 인증서 관리 부담을 줄일 수 있습니다. IAM Roles Anywhere는 X.509 identity를 쓰지만 임시 credential을 얻기 위해 AWS CreateSession을 호출합니다. 어느 쪽이든 지원되는 API/private endpoint 경로, identity 수명주기·EKS 인가가 필요합니다. 완전 단절/DDIL은 EKS Hybrid의 지원 운영 모델이 아닙니다.

</details>

<span id="_4-rhel에서-nodeadm-install-명령-실행-시-반드시-사용해야-하는-옵션은"></span>

### 7. RHEL에서 문서화된 nodeadm containerd-source 선택지는?

- A) distro만 지원
- B) docker 또는 containerd를 별도 설치·관리할 때 none
- C) OS와 무관하게 eks
- D) 호환성 검토 없이 latest

<details>
<summary>정답 보기</summary>

**정답: B) docker 또는 containerd를 별도 설치·관리할 때 none**

**설명:**

RHEL은 nodeadm의 distro source를 지원하지 않습니다. docker는 호환되는 Docker 배포 containerd 패키지를 설치하고 none은 설치를 생략하므로 init 전에 별도로 관리한 runtime이 필요합니다. 모든 RHEL 설치에 docker만 필수라고 하면 이 선택지를 누락합니다. AL2023의 source 조건은 다릅니다.

</details>

### 8. 복구 경로를 유지하는 이전 순서는?

- A) 원본부터 폐기
- B) Pilot 전에 라이선스 취소
- C) 병행 target 준비, workload·network 이전/검증, 데이터·운영 수락 후 rollback 기간을 거쳐 폐기
- D) VM disk를 컨테이너에 복사하고 즉시 원본 삭제

<details>
<summary>정답 보기</summary>

**정답: C) 병행 target 준비, workload·network 이전/검증, 데이터·운영 수락 후 rollback 기간을 거쳐 폐기**

**설명:**

의존성, backup/restore와 rollback 용량을 준비합니다. 트래픽 전환 전에 데이터 일관성, TLS/DNS, 접근 정책·실제 workload 동작을 검증합니다. VM 컨테이너화나 CSI driver 설치만으로 state가 이전되지 않습니다. 폐기·계약 변경은 합의한 수락·보존 판단을 따릅니다.

</details>

<span id="_8-openshift의-route는-eks-hybrid-nodes에서-어떤-리소스로-대체됩니까"></span>

### 9. OpenShift Route는 어떻게 이전해야 하나요?

- A) 다른 변경 없이 Service로 이름만 변경
- B) Ingress/Gateway API 매핑을 설계하고 선택한 controller의 TLS·routing 동작 검증
- C) 모든 Route를 NetworkPolicy로 교체
- D) 모든 필드를 Gateway에 그대로 복사

<details>
<summary>정답 보기</summary>

**정답: B) Ingress/Gateway API 매핑을 설계하고 선택한 controller의 TLS·routing 동작 검증**

**설명:**

Ingress/Gateway API는 routing 후보 인터페이스이며 자동 동등 변환이 아닙니다. 필요한 termination/reencrypt/passthrough, weight·annotation을 보존합니다. SCC와 PSS/PSA, OLM 공급, ImageStream trigger, DeploymentConfig hook도 마찬가지입니다. ECR/Helm/Deployment가 OpenShift 동작을 전부 자동 재현하지 않습니다.

</details>

<span id="_5-ubuntu-24-04에서-containerd-관련-문제가-발생할-때-필요한-조치는"></span>

### 10. 문서화된 Ubuntu 24.04 AppArmor/컨테이너 종료 문제에 적절한 대응은?

- A) 모든 호스트의 unknown AppArmor profile 제거
- B) 실제 package/profile 문제를 확인해 지원되는 수정을 적용하고 해당 전환에 필요한 경우 계획된 reboot 수행
- C) 모든 보안 기능 비활성화
- D) 모든 stuck Pod는 containerd 1.7.19를 정확히 설치하면 해결된다고 가정

<details>
<summary>정답 보기</summary>

**정답: B) 실제 package/profile 문제를 확인해 지원되는 수정을 적용하고 해당 전환에 필요한 경우 계획된 reboot 수행**

**설명:**

버그 2065423은 수정이 배포되었으며 해당 package/profile 전환의 재시작을 설명합니다. Vendor package/backport와 실제 signal-denial log를 확인합니다. aa-remove-unknown은 /etc/apparmor.d에 없는 로드된 profile을 제거하는 명령이지 특정 editor가 아닙니다. 통제된 drain/reboot/workload 검증을 사용하고 모든 AppArmor 변경을 일괄 reboot 규칙으로 만들지 않습니다.

</details>

<span id="_10-32-vcpu-서버-기준-eks-hybrid-nodes의-연간-비용-계산에-사용되는-시간당-vcpu-요금은"></span>

### 11. 검토한 EKS Hybrid 요금에 맞는 계산 모델은?

- A) 모든 서비스를 포함한 고정 $0.01/vCPU-hour
- B) 보고된 vCPU-hours의 월별 구간 요금과 별도 클러스터·기타 비용
- C) 실행 Pod가 요청한 CPU만 과금
- D) Workload가 idle이면 노드 요금 없음

<details>
<summary>정답 보기</summary>

**정답: B) 보고된 vCPU-hours의 월별 구간 요금과 별도 클러스터·기타 비용**

**설명:**

월 처음 576,000 vCPU-hours에는 $0.020/vCPU-hour를 적용하고 이후 공개된 구간별 요금을 적용합니다. 계정 또는 Organizations 통합 결제 범위의 동일 리전 사용량을 합산합니다. 보고된 vCPU, 월 길이, cluster 지원 tier와 기타 서비스를 포함합니다. 과거 $2,803.20/노드/년은 폐기한 미검증 가정으로 보존하며 현재 TCO가 아닙니다.

</details>

<span id="_7-vmware에서-eks-hybrid-nodes로-마이그레이션할-때-nsx-t의-대체-솔루션은"></span>

### 12. NSX-T 기능을 이전하며 Cilium BGP를 선택한다는 뜻은?

- A) 모든 NSX-T 기능 자동 재현
- B) BGP는 route 교환을 제공하며 overlay·firewall·load balancing·policy는 별도로 매핑
- C) 반환 경로 시험 불필요
- D) 모든 기존 연결이 그대로 유지

<details>
<summary>정답 보기</summary>

**정답: B) BGP는 route 교환을 제공하며 overlay·firewall·load balancing·policy는 별도로 매핑**

**설명:**

BGP advertisement가 NSX 플랫폼 전체를 제공하지는 않습니다. Route, overlay, security와 load-balancing 동작을 따로 조사하고 addressing, 반환 경로, TLS/DNS·기존/새 연결을 시험합니다. 지원되는 혼합 CNI 패턴과 rollback을 준비하며 일대일 전체 대체를 주장하지 않습니다.

</details>

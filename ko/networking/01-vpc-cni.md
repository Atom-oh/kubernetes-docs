# Amazon VPC CNI

> **검토 기준**: VPC CNI / Helm 차트 1.23.0, network policy agent 1.4.1.
> **최종 검토**: 2026년 9월 11일. 실제 클러스터 버전·리전에 호환되는 EKS add-on build를 선택합니다. 업스트림, Helm, EKS `eksbuild` 버전은 서로 다른 식별자입니다.

## 목차

- [VPC CNI 개요](#vpc-cni-개요)
- [네트워킹 모델](#네트워킹-모델)
- [설치 및 구성](#설치-및-구성)
- [IP 주소 관리](#ip-주소-관리)
- [Network Policy 지원](#network-policy-지원)
- [고급 기능](#고급-기능)
- [트러블슈팅](#트러블슈팅)
- [모범 사례](#모범-사례)

## VPC CNI 개요

Amazon VPC CNI는 표준 EKS EC2 노드에 VPC 기반 Pod 네트워킹을 제공합니다. 이 문서의 `aws-node` DaemonSet 명령도 해당 설치를 대상으로 합니다. Auto Mode는 노드 서비스로 관리형 네트워킹을 실행하고 Fargate·Windows는 관리 경로가 다릅니다. EC2/Linux 절차를 다른 컴퓨팅 모드에 적용하기 전에 [개요](README.md)를 확인합니다.

Pod는 overlay 캡슐화 없이 VPC에서 라우팅 가능한 주소를 사용합니다. 실제 연결·성능은 라우팅, 보안 그룹, 네트워크 정책, ENI/IP 한계, 애플리케이션에도 달려 있습니다. EKS는 생성 시 선택한 **IPv4 또는 IPv6 Pod/Service 주소**를 지원하며 dual-stack Pod·Service는 지원하지 않습니다. dual-stack VPC나 IPv6 Pod의 IPv4 egress 보조 인터페이스는 다른 개념입니다.

### 아키텍처

| 구성 요소 | 역할 |
|---|---|
| 컨테이너 런타임 / CNI 바이너리 | 런타임이 Pod sandbox의 CNI를 호출하고 AWS 플러그인이 주소 요청·네트워크 네임스페이스 설정 수행 |
| IPAMD | Linux EC2 노드의 주소 pool과 필요한 일반 ENI·IP 관리 |
| EKS 네트워크 정책 컨트롤러 / 노드 에이전트 | 관리형 컨트롤러가 정책 엔드포인트를 해석하고, 활성화된 `aws-eks-nodeagent`가 지원 정책을 eBPF로 강제 |
| VPC resource controller | 별도 전제에 따라 branch/trunk 인터페이스, Windows 주소 할당 등 관리 |

이전 그림은 kubelet이 CNI 바이너리를 직접 호출한다고 표시했습니다. 현재 Kubernetes의 CNI 관리는 컨테이너 런타임이 담당합니다.

### IP 할당 방식

| 특성 | 보조 IPv4 주소 | Prefix delegation |
|---|---|---|
| 할당 단위 | ENI의 개별 보조 주소 | IPv4는 16개 주소의 `/28`, IPv6는 `/80` prefix |
| 용량 | 인터페이스·주소 슬롯 및 kubelet 설정에 제한 | 슬롯당 주소를 늘리지만 지원 하드웨어·여유 prefix·kubelet/리소스 한계 적용 |
| 할당 절충 | 주소 단위로 세밀하게 할당 | 블록을 한 번에 할당하므로 warm target에 따라 미사용 주소 예약 |
| 선택 기준 | 호환성과 측정한 수요 | Nitro 지원, 서브넷 단편화, 워크로드 변경, 기능 조합 확인 |

Prefix delegation이 모든 대규모 클러스터의 필수 조건은 아니며 고갈된 서브넷에 새 주소 공간을 만들어 주지도 않습니다.

## 네트워킹 모델

### ENI 아키텍처

일반 secondary-IPv4 모드에서는 각 ENI에 primary 주소와 CNI가 사용할 추가 주소가 있습니다. Primary ENI는 노드의 primary 주소도 전달합니다. 추가 ENI에서 더 많은 보조 Pod 주소를 공급할 수 있습니다. Custom networking은 Pod 주소를 공급하는 인터페이스·서브넷을 바꾸고, prefix·branch-ENI 모드는 할당 규칙이 다릅니다.

```text
Linux EC2 노드 — 일반 secondary-IPv4 예제
├── Primary ENI: 노드 primary IP + Pod용 secondary IP
├── 추가 ENI: 해당 ENI의 primary IP + Pod용 secondary IP
└── 추가 ENI: 해당 ENI의 primary IP + Pod용 secondary IP
```

### 인스턴스 유형별 ENI/IP 제한

| 인스턴스 유형 | 최대 ENI 수 | ENI당 IPv4 슬롯 | 과거 secondary-IP bootstrap maxPods |
|---|---|---|---|
| t3.medium | 3 | 6 | 17 |
| t3.large | 3 | 12 | 35 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| c5.4xlarge | 8 | 30 | 234 |
| m5.8xlarge | 8 | 30 | 234 |

과거 공식은 **`ENI 수 × (ENI당 IPv4 슬롯 − 1) + 2`**입니다. `+2`는 해당 bootstrap 계산의 host-network 시스템 Pod 2개를 반영하므로 m5.large는 `3 × 9 + 2 = 29`입니다. 현재 모든 배포에 host-network Pod가 정확히 2개라는 뜻은 아닙니다.

이 값은 과거 bootstrap 값이며 현재 모든 환경의 Pod 밀도 권장값이 아닙니다. Prefix delegation, custom networking, branch 인터페이스, 다중 네트워크 카드, CPU·메모리, kubelet `maxPods`를 함께 고려합니다. EKS 관리형 노드 그룹은 vCPU 30개 미만에서 `maxPods` 110, 그 외에는 250을 상한으로 적용합니다. 실제 노드의 allocatable 용량을 확인합니다.

### Prefix Delegation

Linux IPv4 prefix 모드의 EKS 관리형 add-on 설정 조각입니다.

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```

아래 관리 절차로 의도한 add-on 설정과 합칩니다. Helm 관리 설치에서는 같은 `env` 매핑을 Helm values에 둡니다. 직접 `kubectl set env`로 바꾼 값은 관리 주체가 다시 조정할 수 있습니다.

IPv4 할당에는 단순히 양수 `AvailableIpAddressCount`가 아니라 적절한 연속 `/28` 블록이 필요합니다. 서브넷 예약·단편화와 Nitro 지원을 확인합니다. Prefix를 켜도 기존 kubelet Pod 상한이나 branch-ENI Pod 상한이 모두 자동으로 증가하지는 않습니다.

## 설치 및 구성

### 관리 주체와 호환성 확인

대상 클러스터의 AWS CLI 자격 증명과 Kubernetes context를 준비하고 읽기부터 시작합니다.

```bash
EKS_REGION=ap-northeast-2
CLUSTER_NAME=my-cluster
KUBERNETES_MINOR="$(aws eks describe-cluster --region "$EKS_REGION" \
  --name "$CLUSTER_NAME" --query cluster.version --output text)"
aws eks describe-addon-versions --region "$EKS_REGION" \
  --addon-name vpc-cni --kubernetes-version "$KUBERNETES_MINOR"
aws eks describe-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni
kubectl -n kube-system get daemonset aws-node -o yaml
```

EKS `describe-addon`의 `ResourceNotFoundException`만으로 CNI가 없다고 판단하지 않습니다. 자체 관리 설치일 수 있습니다. 기존 DaemonSet, ServiceAccount, Helm release, 설정, IAM을 확인하고 관리 주체를 **하나** 선택합니다. Auto Mode 네트워킹에는 이 설치 절차를 적용하지 않습니다.

### 기존 EKS 관리형 Add-on

기존 설정을 내보내고 선택한 호환 build의 스키마를 확인합니다.

```bash
umask 077
aws eks describe-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni > vpc-cni-before.json
jq -r '.addon.configurationValues // "{}"' vpc-cni-before.json > vpc-cni-config.json
: "${VPC_CNI_ADDON_VERSION:?Select a compatible EKS add-on build from the metadata}"
aws eks describe-addon-configuration --region "$EKS_REGION" \
  --addon-name vpc-cni --addon-version "$VPC_CNI_ADDON_VERSION"
```

필요한 중간 업그레이드 버전과 릴리스 변경을 검토합니다. `vpc-cni-config.json`에 의도한 기존 설정을 보존하면서 선택한 변경만 반영합니다. 일부 payload나 충돌 플래그가 모든 값을 자동 보존한다고 가정하지 않습니다. CNI IAM 권한과 설정한 IRSA/Pod Identity 역할을 확인하고 IPv6에 맞는 권한도 준비합니다.

이미 관리형인 add-on의 검토된 업데이트는 다음 형태로 실행할 수 있습니다.

```bash
set -eu
VPC_CNI_UPDATE_ID="$(aws eks update-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION" \
  --configuration-values file://vpc-cni-config.json --resolve-conflicts PRESERVE \
  --query update.id --output text)"
aws eks describe-update --region "$EKS_REGION" --name "$CLUSTER_NAME" \
  --addon-name vpc-cni --update-id "$VPC_CNI_UPDATE_ID"
```

`PRESERVE`는 명시적인 충돌 처리 선택이며 결과 환경 변수·이미지·동작을 확인해야 합니다. 기록한 update ID의 상태가 `Successful`이 될 때까지 조회합니다. `Failed`·`Cancelled`이면 오류를 확인하고 진행을 중단합니다. 성공한 뒤 결과 add-on·DaemonSet을 확인합니다.

```bash
aws eks describe-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni
kubectl -n kube-system rollout status daemonset/aws-node --timeout=10m
```

API 요청 수락이나 이전 DaemonSet의 준비 상태만으로 이번 업데이트·네트워크 검증이 끝났다고 판단하지 않습니다.

관리형 add-on이 없고 설치·소유 관계 준비를 마친 경우의 생성은 별도 작업입니다.

```bash
aws eks create-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION" \
  --configuration-values file://vpc-cni-config.json
```

개별 기능을 켤 때마다 `create-addon`을 반복하거나, 기존 사용자 설정에 마이그레이션 계획 없이 `OVERWRITE`를 강제하지 않습니다.

### Helm 관리 설치

Init·정책 에이전트 구성 요소도 함께 선택되도록 전체 차트를 고정합니다. 이미지 태그 두 개만 바꿔서는 차트의 나머지가 업데이트되지 않습니다.

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
helm show values eks/aws-vpc-cni --version 1.23.0 > chart-defaults.yaml
helm template aws-vpc-cni eks/aws-vpc-cni --namespace kube-system \
  --version 1.23.0 -f helm-values.yaml > rendered-cni.yaml
```

실제 IP family, CNI ServiceAccount/IAM, 선택한 기능에 맞게 `helm-values.yaml`을 준비합니다. 이 문서의 기본 Linux 예제는 IPv4입니다. 렌더링한 리소스를 검토한 뒤 적용합니다.

```bash
helm upgrade --install aws-vpc-cni eks/aws-vpc-cni --namespace kube-system \
  --version 1.23.0 -f helm-values.yaml --wait --timeout 10m
```

명령은 새 설치나 Helm 관리 설치를 전제로 합니다. 기존 EKS add-on·bootstrap 관리 객체는 소유 전환 계획이 필요합니다. EKS 파티션·레지스트리 접근과 이미지 pull 전제도 환경에 맞춰야 합니다.

### 주요 설정 값

| 설정 | 의미 | 기준·기본값 구분 |
|---|---|---|
| `WARM_IP_TARGET` | 새 일반 Pod 할당에 대비한 여유 주소 목표 | 기본 미설정, 최대 한계가 아님 |
| `MINIMUM_IP_TARGET` | 전체 할당 주소의 하한 | 기본 미설정, 사용 시 양수 warm-IP 목표와 조합 |
| `WARM_ENI_TARGET` | Warm ENI 용량 목표 | 릴리스 기본 1, IP target이 우선 |
| `WARM_PREFIX_TARGET` | 여유 IPv4 prefix 목표 | 릴리스 차트·매니페스트는 1, bare daemon 문서는 미설정 |
| `ENABLE_PREFIX_DELEGATION` | Prefix 할당 선택 | Linux 차트 기본 `"false"` |
| `AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG` | Custom networking 선택 | 기본 `"false"` |
| `ENI_CONFIG_LABEL_DEF` | ENIConfig를 선택하는 노드 레이블 키 | Daemon 기본 `k8s.amazonaws.com/eniConfig`, zone 예제는 재정의 |
| `ENABLE_POD_ENI` | EC2 Pod-ENI 연동 활성화 | 기본 `"false"`, 다른 SGPP 전제도 필요 |
| `POD_SECURITY_GROUP_ENFORCING_MODE` | SGPP 라우팅·SNAT·보안 그룹 동작 | 기본 `strict` |
| `NETWORK_POLICY_ENFORCING_MODE` | 새 Pod의 규칙을 설정하는 동안 네트워크 정책 동작 | 기본 `standard` |

두 enforcing-mode 설정은 다른 시스템을 제어합니다. EKS 설정 payload의 환경 변수 값은 문자열입니다.

### Custom Networking (ENIConfig)

의도한 VPC·AZ에 실제 Pod 서브넷·보안 그룹을 생성하고 ID를 참조합니다.

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: ap-northeast-2a
spec:
  subnet: subnet-0123456789abcdef0
  securityGroups:
  - sg-0123456789abcdef0
---
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: ap-northeast-2b
spec:
  subnet: subnet-0abcdef0123456789
  securityGroups:
  - sg-0123456789abcdef0
```

Custom networking을 켜고 노드의 실제 zone 레이블을 사용합니다.

```json
{
  "env": {
    "AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG": "true",
    "ENI_CONFIG_LABEL_DEF": "topology.kubernetes.io/zone"
  }
}
```

명시적인 ENIConfig 노드 어노테이션이 레이블보다 우선합니다. ENIConfig 객체만으로 custom networking이 활성화되지는 않습니다. 라우팅, DNS·보안 규칙, 주소 용량, 워크로드·노드 전환을 계획합니다. 새 CIDR·ENIConfig만 생성해도 현재 Pod가 다른 서브넷으로 이동하지는 않습니다.

## IP 주소 관리

### Warm Pool 튜닝

측정한 Pod 수요·변경 빈도, 주소 공간, EC2 API 한계로 정합니다. 다음은 클러스터 크기만으로 정한 권장값이 아닌 서로 다른 목표 예제입니다.

```json
{
  "env": {
    "WARM_IP_TARGET": "2",
    "MINIMUM_IP_TARGET": "4"
  }
}
```

```json
{
  "env": {
    "WARM_IP_TARGET": "5",
    "MINIMUM_IP_TARGET": "10"
  }
}
```

`MINIMUM_IP_TARGET`은 전체 할당 하한, `WARM_IP_TARGET`은 여유 주소 목표이며 ENI/prefix warm 전략보다 우선합니다. Prefix delegation에서는 실제로 prefix 단위 할당이 이루어집니다. Warm 용량은 할당 대기를 줄일 수 있지만 주소를 사용하고, 잦은 변경은 API 호출을 늘릴 수 있습니다.

### Secondary CIDR 추가

먼저 기존 연결, 연결된 네트워크와의 중복, VPC CIDR 제한, 서브넷·라우팅 전제를 검토합니다.

```bash
VPC_ID=vpc-0123456789abcdef0
aws ec2 describe-vpcs --region "$EKS_REGION" --vpc-ids "$VPC_ID" \
  --query 'Vpcs[0].CidrBlockAssociationSet'
```

다음 ID·주소 공간은 예제이며 검토한 VPC 계획의 일부로만 수행합니다.

```bash
aws ec2 associate-vpc-cidr-block --region "$EKS_REGION" \
  --vpc-id "$VPC_ID" --cidr-block 100.64.0.0/16
aws ec2 describe-vpcs --region "$EKS_REGION" --vpc-ids "$VPC_ID" \
  --query 'Vpcs[0].CidrBlockAssociationSet'
```

새 CIDR의 상태가 associating이 아니라 **associated**인지 확인한 뒤 그 범위에 서브넷을 생성합니다.

```bash
aws ec2 create-subnet --region "$EKS_REGION" --vpc-id "$VPC_ID" \
  --cidr-block 100.64.0.0/19 --availability-zone ap-northeast-2a
```

서브넷의 라우팅 테이블·보안 규칙·CNI 선택도 필요합니다. 기존 Pod는 계획한 전환 전까지 현재 네트워킹을 유지합니다. RFC 6598 `100.64.0.0/10`은 shared address space이지 전 세계에서 고유한 사설 용량이 아니므로 연결된 모든 환경과 중복을 확인합니다.

### IPv6 클러스터 구성

IP family는 생성 시 선택하고 이후 변경할 수 없습니다. 공식 `eksctl` 인터페이스는 `--ip-family` 플래그가 아닌 **설정 파일**입니다. 스키마 예제는 다음과 같습니다.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ipv6-example
  region: ap-northeast-2
  version: '1.35'
kubernetesNetworkConfig:
  ipFamily: IPv6
iam:
  withOIDC: true
addons:
- name: vpc-cni
- name: coredns
- name: kube-proxy
managedNodeGroups:
- name: linux-nitro
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  desiredCapacity: 2
  privateNetworking: true
```

예제 버전·리전을 바꾸고 지원되는 노드 이미지를 선택하며 생성 전 VPC endpoint·접근·IAM을 검토합니다. 여기서 생략한 add-on 버전은 EKS/eksctl의 지원 경로로 선택되므로, 통제된 배포에는 필요한 호환 build를 확인·고정합니다. `iam.withOIDC`와 관리형 add-on·node group은 공식 eksctl IPv6 전제를 반영합니다.

```bash
eksctl create cluster --config-file ipv6-cluster.yaml
```

이 감사에서 클러스터를 생성하지 않았습니다. 로컬 CLI help·schema 검사는 eksctl 0.229.0으로 했으며 네트워킹·IAM·리전별 build의 실제 배포 검증은 아닙니다.

IPv6에는 지원되는 Linux Nitro/Fargate 경로와 prefix 할당이 필요하고 Windows는 지원되지 않습니다. IPv6 Pod에 egress-only IPv4 보조 인터페이스가 있을 수 있습니다. 정책 에이전트 문서는 주 인터페이스의 IPv6 정책이 보조 인터페이스의 IPv4 트래픽을 보호하지 않는다고 명시합니다. 이 경로를 제거해야 한다면 `ENABLE_V4_EGRESS`, 의존성, Pod 롤아웃을 검토하고 IPv6 정책만으로 차단된다고 가정하지 않습니다.

## Network Policy 지원

### 네이티브 정책 강제

표준 네이티브 eBPF 정책은 VPC CNI 1.14에서 처음 도입되었습니다. 현재 EKS 문서의 표준·Admin 정책에는 더 새 전제가 있으며 검토한 1.23도 클러스터·플랫폼에 맞춰야 합니다.

```json
{
  "enableNetworkPolicy": "true"
}
```

`"enableNetworkPolicy": "true"`는 공식 문자열 설정입니다. 지원되는 EC2 Linux 노드에서 사용할 수 있고 Fargate·Windows에는 이 강제를 적용하지 않습니다. Auto Mode는 자체 관리형 구현을 사용합니다. EKS `ClusterNetworkPolicy` Admin/Baseline 제어와 Auto Mode DNS `ApplicationNetworkPolicy`는 표준 `NetworkPolicy`의 다른 이름이 아닌 확장입니다.

Standard 모드의 새 Pod는 규칙이 해석되는 동안 처음에 트래픽을 허용합니다. 더 엄격한 시작 동작을 의도적으로 선택할 수 있습니다.

```json
{
  "enableNetworkPolicy": "true",
  "env": {
    "NETWORK_POLICY_ENFORCING_MODE": "strict"
  }
}
```

Strict 모드에서는 시작 전 DNS 등 필수 트래픽 정책을 올바르게 준비해야 합니다. SGPP의 별도 `POD_SECURITY_GROUP_ENFORCING_MODE`를 설정하는 기능은 아닙니다.

### NetworkPolicy 예제

전제는 `app` 네임스페이스의 컨트롤러 관리 frontend/backend 워크로드와 TCP 8080을 수신하는 backend Pod입니다. 현재 AWS는 안정적인 강제에 `metadata.ownerReferences`가 중요하며 Service·컨테이너 포트 번호(이름 있는 포트는 이름도)가 일치해야 한다고 문서화합니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: app
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

출발 Pod 선택자는 같은 네임스페이스로 제한됩니다. 선택한 backend ingress를 격리하고 해당 frontend의 8080 접근을 허용하지만 backend egress를 거부하거나 애플리케이션 사용자를 인증하지는 않습니다. 다른 일치 정책과 Admin tier 동작도 고려합니다. 독립 진단 Pod 대신 Deployment/Job 관리 Pod로 허용·거부 흐름을 모두 확인합니다.

### 검증과 진단

```bash
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-eks-nodeagent --tail=200
kubectl get networkpolicy -A
kubectl get policyendpoints.networking.k8s.aws -A
```

이는 **노드 에이전트** 로그이며 정책 컨트롤러는 EKS 관리 제어 평면에서 실행됩니다. PolicyEndpoint는 생성된 상태이므로 임의로 편집·삭제하지 않습니다.

접근 권한이 있고 정책 CLI가 설치된 Linux 노드에서는 다음을 사용합니다.

```bash
sudo /opt/cni/bin/aws-eks-na-cli ebpf progs
sudo /opt/cni/bin/aws-eks-na-cli ebpf maps
```

도구는 `ebpf-sdk list-maps`가 아닌 `aws-eks-na-cli`입니다. 영향받은 노드를 확인하고 프로세스 로그, 설정한 정책 이벤트 로그, CloudWatch 전달을 구분합니다. 외부 로그 전달에는 해당 IAM·설정도 필요합니다.

## 고급 기능

### Pod별 보안 그룹

해당 보안 그룹이 DNS·API·애플리케이션·반환 경로에 맞는 규칙을 가지고 이미 존재해야 합니다.

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: my-security-group-policy
  namespace: app
spec:
  podSelector:
    matchLabels:
      app: database
  securityGroups:
    groupIds:
    - sg-0123456789abcdef0
    - sg-0abcdef0123456789
```

Standard SGPP 동작을 선택한 **EC2** 설정 예제입니다.

```json
{
  "env": {
    "ENABLE_POD_ENI": "true",
    "POD_SECURITY_GROUP_ENFORCING_MODE": "standard"
  }
}
```

완전한 SGPP 설치가 아닙니다. Trunking 지원 인스턴스, 클러스터 역할의 VPC resource-controller 권한, CNI 권한, 서브넷 용량, EKS 전제를 확인합니다. T 계열이 Nitro라고 해서 trunking을 지원하지는 않습니다. 새로 생성·재생성한 선택 Pod에 의도한 설정이 적용됩니다.

관리형 resource controller는 **추가 trunk ENI**를 붙이고 branch ENI를 연결합니다. Trunk는 노드의 primary `eth0` ENI가 아닙니다. 선택 Pod는 보안 그룹이 지정된 branch 인터페이스를 사용하며 prefix delegation이 branch Pod 상한을 늘리지 않습니다. Fargate 보안 그룹은 별도 관리 경로를 따릅니다.

| 모드·기능 | 확인할 영향 |
|---|---|
| SGPP `strict` | Branch 보안 그룹 동작과 Pod SNAT 비활성화, NodeLocal DNSCache 및 instance 대상 LoadBalancer/NodePort의 `externalTrafficPolicy: Local` 제약 |
| SGPP `standard` | 문서화된 정책·DNS 조합 지원. 기본 external-SNAT 동작에서는 VPC 밖 트래픽이 노드 primary 주소·보안 그룹 사용 |
| Custom networking + SGPP | Pod 보안 그룹이 ENIConfig 보안 그룹보다 우선 |
| IPv6 | EKS 문서의 버전·플랫폼 조건에 따라 지원(EC2 CNI 1.16+ 포함). 오래된 README 기능 표의 “No”가 상세 안내를 무효화하지 않음 |
| Windows / Auto Mode | 이 SGPP 방식은 미지원, Auto Mode는 별도 NodeClass 네트워킹 제어 사용 |

모드 변경은 새 Pod에 적용되므로 재생성과 트래픽 경로를 검증합니다. SNAT 뒤에도 모든 패킷에 같은 보안 그룹이 적용된다고 가정하지 않습니다.

### 다중 인터페이스와 Multus

VPC CNI 1.20+에는 다중 네트워크 카드를 지원하는 인스턴스용 native multi-NIC 기능이 있습니다. `ENABLE_MULTI_NIC`와 Pod NIC 설정은 Multus와 다르며 추가 인터페이스의 이점을 얻으려면 애플리케이션이 실제로 사용해야 합니다.

Multus는 meta-plugin입니다. AWS 지원 구성은 VPC CNI를 **주 delegate**로 사용하며 VPC CNI를 추가 인터페이스의 플러그인으로 쓰는 것은 지원하지 않습니다. 추가 인터페이스에는 호환 플러그인, 주소 할당, 수명 주기 관리가 필요합니다.

| 추가 인터페이스 전제 | 이유 |
|---|---|
| 식별한 전용 인터페이스 | 고정 `eth1`이 IPAMD 관리 인터페이스일 수 있음 |
| 추가 ENI의 `node.k8s.amazonaws.com/no_manage=true` | VPC CNI가 Multus 인터페이스를 관리하지 않도록 함 |
| AWS에 할당·라우팅된 주소와 올바른 서브넷·SG·경로 | 임의의 `192.168.1.0/24` 할당이 EC2 ENI에서 자동으로 유효해지지 않음 |
| 조정된 IPAM | 공유 `host-local` 범위는 여러 노드에서 중복 주소를 할당할 수 있음 |
| 인터페이스별 정책 시험 | 추가 인터페이스·IPv4 보조 경로가 모든 주 인터페이스 정책에 자동 포함되지는 않음 |

NetworkAttachmentDefinition의 `spec.config`는 지원 버전, 플러그인, 실제 parent 인터페이스, IPAM을 포함한 CNI JSON입니다. 이전 범용 `ipvlan`/`eth1`/`host-local` 매니페스트는 위 전제를 누락하여 구현 요구사항으로 대체했습니다. 이 문서는 실제 배포한 Multus/IPAM 솔루션이라고 주장하지 않습니다.

### Windows

Windows는 VPC resource-controller IPAM을 사용합니다. 클러스터 역할 권한, Windows 노드 역할의 인증·access entry(해당 시 `EC2_WINDOWS`), CoreDNS용 Linux/Fargate 용량을 준비합니다. Windows Fargate, Auto Mode, Hybrid Nodes, IPv6, custom networking, SGPP, 네이티브 VPC-CNI 네트워크 정책에는 문서화된 제약이 있습니다.

컨트롤러의 결과 ConfigMap에는 다음 Windows IPAM 항목이 필요합니다. 필요한 데이터를 나타내며 관리 주체가 소유한 ConfigMap 전체를 덮어쓰라는 명령은 아닙니다.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: amazon-vpc-cni
  namespace: kube-system
data:
  enable-windows-ipam: 'true'
```

**Helm 관리** 설치의 Windows prefix 목표는 Linux와 다른 키를 사용합니다.

```yaml
enableWindowsIpam: 'true'
enableWindowsPrefixDelegation: 'true'
warmWindowsPrefixTarget: 1
warmWindowsIPTarget: 0
minimumWindowsIPTarget: 0
```

해당 build 스키마, 필드 소유, 결과 ConfigMap을 확인합니다. Helm 값이 EKS add-on 설정 속성으로 그대로 수락된다고 가정하지 않습니다. Windows 차트 플래그는 `enable-windows-ipam`, `enable-windows-prefix-delegation`으로 변환되며 여기의 warm-target 필드도 Windows용입니다.

전제와 AMI·버전을 확인한 후 node-group 명령은 다음 형태로 사용할 수 있습니다.

```bash
eksctl create nodegroup --region "$EKS_REGION" --cluster "$CLUSTER_NAME" \
  --name windows-example --managed --node-type m5.large --nodes 2 \
  --node-ami-family WindowsServer2022FullContainer
```

Windows secondary-IP 모드는 일반적으로 ENI 1개와 그 주소 슬롯 상한을 사용하며 Linux의 다중 ENI 공식과 다릅니다. Prefix delegation과 실제 kubelet 상한도 별도로 계산합니다.

## 트러블슈팅

### IP 할당과 스케줄링

Pod 이벤트로 스케줄링 실패와 sandbox/CNI 주소 할당 실패를 구분합니다.

```bash
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-node --tail=300
kubectl get nodes -o json | jq '.items[] | {name: .metadata.name, allocatablePods: .status.allocatable.pods}'
SUBNET_ID=subnet-0123456789abcdef0
aws ec2 describe-subnets --region "$EKS_REGION" --subnet-ids "$SUBNET_ID" \
  --query 'Subnets[].{SubnetId:SubnetId,AvailableIPs:AvailableIpAddressCount}'
```

`allocatablePods`는 kubelet 스케줄링 용량이지 현재 IP 사용률이 아닙니다. 서브넷의 여유 주소 수만으로 연속 `/28` 존재를 알 수 없습니다. 대응을 정하기 전에 IPAMD 로그, 모드, warm target, ENI 한계, API 오류, 영향받은 노드를 확인합니다.

### ENI 수

```bash
INSTANCE_ID=i-0123456789abcdef0
aws ec2 describe-instances --region "$EKS_REGION" --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[].Instances[].{InstanceId:InstanceId,AttachedENIs:length(NetworkInterfaces)}'
aws ec2 describe-instance-types --region "$EKS_REGION" --instance-types m5.large \
  --query 'InstanceTypes[].NetworkInfo.{MaxENI:MaximumNetworkInterfaces,IPv4PerENI:Ipv4AddressesPerInterface}'
```

이전 쿼리는 인터페이스 자체가 아닌 중첩된 목록 수를 세었습니다. 수정 쿼리는 인스턴스별 개수를 반환합니다. 다중 카드, unmanaged/trunk 인터페이스, 인스턴스별 한계는 추가 해석이 필요합니다.

### Introspection과 메트릭

해당 노드의 실제 `aws-node` Pod를 선택하고 forwarding 세션을 유지합니다.

```bash
kubectl -n kube-system get pods -l k8s-app=aws-node -o wide
AWS_NODE_POD=aws-node-example
kubectl -n kube-system port-forward "pod/$AWS_NODE_POD" 61678:61678 61679:61679
```

다른 로컬 터미널에서 조회합니다.

```bash
curl --fail http://127.0.0.1:61679/v1/enis
curl --fail http://127.0.0.1:61678/metrics
```

IPAMD introspection 기본값은 loopback **61679**, Prometheus 메트릭은 **61678**입니다. `/v1/enis`는 메트릭 엔드포인트가 아닙니다. Kubernetes forwarding 경로의 로컬 curl을 사용하므로 CNI 이미지 안의 curl에 의존하지 않습니다.

### 변경 전 오류 분류

| 관측 | 조치 전 확인 |
|---|---|
| `InsufficientFreeAddressesInSubnet` | 실제 여유 주소, warm 할당, 선택 서브넷, 계획한 용량 확장 |
| `InsufficientCidrBlocks` | 연속 prefix·단편화·서브넷 예약 |
| ENI/SG 한계 오류 | 해당 quota, 인스턴스·인터페이스 유형, 사용 중 객체. 무관한 SG를 제거하지 않음 |
| ENI 생성 실패 | 상세 AWS 오류, CNI 자격 증명 역할, 권한·조건, quota, API 연결 |
| Pod IP 대기 | IPAMD 상태, 컨트롤러·API 지연, 스로틀링, sandbox 이벤트, 주소 준비 |

IPAMD 재시작, 인스턴스 확대, 노드 역할 권한 추가는 범용 해결책이 아닙니다. 근거를 먼저 수집하고 실제 실패 작업의 관리 주체에 검토한 변경을 적용합니다.

## 모범 사례

예상 Pod, warm pool, 증가량, 장애·교체 중복을 고려해 서브넷을 계획합니다. `/19`나 RFC 6598 범위는 설계 예제이지 필수 조건이 아닙니다. 새 CIDR 연결, 필요한 서브넷·경로, CNI·워크로드 전환을 함께 계획합니다.

Warm 전략을 하나 선택합니다. 여유 IP와 전체 IP 목표를 사용하는 IPv4 prefix 예제입니다.

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_IP_TARGET": "5",
    "MINIMUM_IP_TARGET": "10"
  }
}
```

IP target이 설정된 상태의 추가 `WARM_PREFIX_TARGET`을 독립적으로 유효한 목표라고 해석하지 않습니다. 클러스터 크기만으로 안전성을 추정하지 말고 할당 실패·실제 제약을 감시합니다.

### 메트릭과 알림

릴리스 IPAMD 코드는 `awscni_total_ip_addresses`, `awscni_assigned_ip_addresses`, counter `awscni_no_available_ip_addresses`를 제공합니다. Total/assigned gauge는 전체 VPC 서브넷이 아닌 **IPAMD 할당 pool**을 나타냅니다. 작은 warm target에서는 높은 assigned/total 비율이 정상일 수 있으며 cooldown, branch 인터페이스, IP family, kubelet 용량을 함께 봐야 합니다.

Prometheus Operator CRD와 선택자가 먼저 구성되어 있어야 합니다. Helm 관리 CNI에서는 다음 **IPv4 클러스터 예제**로 차트의 PodMonitor를 생성할 수 있습니다.

```yaml
podMonitor:
  create: true
  labels:
    release: prometheus
  interval: 30s
  relabelings:
  - sourceLabels:
    - __meta_kubernetes_pod_node_name
    targetLabel: node
  - targetLabel: cluster
    replacement: example-cluster
  - targetLabel: ip_family
    replacement: ipv4
  - targetLabel: job
    replacement: aws-vpc-cni
```

클러스터 레이블을 교체하고 `release` 선택자를 맞추며 IP family를 사실대로 지정합니다. 레이블이 실제 family를 탐지하지는 않습니다. 차트는 Agent의 이름 있는 `metrics` 포트와 활성화한 정책 에이전트의 `agentmetrics`를 수집합니다. EKS 관리형 add-on에는 두 번째 CNI Helm release를 설치하지 말고 독립된 scraper/PodMonitor를 구성합니다.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: vpc-cni-signals
  namespace: monitoring
  labels:
    release: prometheus
spec:
  groups:
  - name: vpc-cni
    rules:
    - record: vpc_cni:allocated_ipv4_pool_utilization:ratio
      expr: (awscni_assigned_ip_addresses{job="aws-vpc-cni",ip_family="ipv4"} / awscni_total_ip_addresses{job="aws-vpc-cni",ip_family="ipv4"})
        and (awscni_total_ip_addresses{job="aws-vpc-cni",ip_family="ipv4"} > 0)
    - alert: CniHighAllocatedIPv4PoolUtilization
      expr: vpc_cni:allocated_ipv4_pool_utilization:ratio > 0.9
      for: 5m
      labels:
        severity: info
      annotations:
        summary: Most currently allocated IPAMD IPv4 addresses are assigned
        description: This is allocated-pool utilization, not subnet exhaustion. Check
          warm targets, assignment failures and available subnet space.
    - alert: CniIPAssignmentFailures
      expr: increase(awscni_no_available_ip_addresses{job="aws-vpc-cni"}[5m]) > 0
      for: 1m
      labels:
        severity: warning
      annotations:
        summary: IPAMD could not assign an available IP address
    - alert: CniMetricsScrapeFailed
      expr: up{job="aws-vpc-cni"} == 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: A known CNI metrics endpoint cannot be scraped
```

Pool 비율은 IPv4와 관측된 양수 분모로 한정합니다. 서브넷 고갈 증거가 아닌 정보성 튜닝 신호입니다. 할당 실패 counter는 실제 실패를 나타냅니다. 수집 실패와 대상 삭제는 다르므로 예상 노드·구성 요소 목록도 비교합니다. 데이터 없음은 정상 0이 아닙니다. 실제 관측 환경에 맞게 임계값, 레이블, 알림 전달을 조정합니다.

## 참고 자료

- [VPC CNI 1.23.0 documentation](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/README.md)
- [VPC CNI Helm values](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/charts/aws-vpc-cni/values.yaml)
- [Chart version metadata](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/charts/aws-vpc-cni/Chart.yaml)
- [Released CNI manifest](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/config/master/aws-k8s-cni.yaml)
- [IPAMD implementation](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/pkg/ipamd/ipamd.go)
- [IPAMD introspection server](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/pkg/ipamd/introspect.go)
- [IPAM datastore](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/pkg/ipamd/datastore/data_store.go)
- [IPAMD metric definitions](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/utils/prometheusmetrics/prometheusmetrics.go)
- [Network policy agent 1.4.1](https://github.com/aws/aws-network-policy-agent/blob/v1.4.1/README.md)
- [AWS Helm chart index](https://aws.github.io/eks-charts/index.yaml)
- [EKS security groups for Pods](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
- [SGPP operating considerations](https://docs.aws.amazon.com/eks/latest/best-practices/sgpp.html)
- [EKS Multus support boundaries](https://docs.aws.amazon.com/eks/latest/userguide/pod-multus.html)
- [EKS Windows networking](https://docs.aws.amazon.com/eks/latest/userguide/windows-support.html)
- [EKS IPv6 support](https://docs.aws.amazon.com/eks/latest/userguide/cni-ipv6.html)
- [eksctl IPv6 configuration](https://docs.aws.amazon.com/eks/latest/eksctl/vpc-ip-family.html)
- [CNI IAM configuration](https://docs.aws.amazon.com/eks/latest/userguide/cni-iam-role.html)
- [EKS VPC CNI management](https://docs.aws.amazon.com/eks/latest/userguide/managing-vpc-cni.html)
- [EKS network policy conditions](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [Enable EKS network policy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [Prefix allocation and Pod-capacity limits](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)

## 퀴즈

[VPC CNI 퀴즈](../quizzes/networking/01-vpc-cni-quiz.md)로 이해를 확인합니다.

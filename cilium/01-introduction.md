# Cilium 소개 및 기본 개념

> **지원 버전**: Cilium 1.17  
> **마지막 업데이트**: 2025년 7월 21일

## 실습 환경 설정

이 문서의 예제를 따라하기 위해서는 다음과 같은 도구와 환경이 필요합니다:

### 필수 도구
- kubectl v1.33 이상
- Helm v3.12 이상
- 작동하는 Kubernetes 클러스터 (EKS, minikube, kind 등)
- Linux 커널 4.19 이상 (eBPF 기능 지원)

### Cilium 설치

```bash
# Cilium CLI 설치
curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz

# Cilium 설치
cilium install --version 1.17.0

# 설치 상태 확인
cilium status
```

## Cilium이란 무엇인가?

Cilium은 Linux 커널의 강력한 eBPF 기술을 활용하여 컨테이너화된 애플리케이션 간의 네트워크 연결, 보안, 관찰 가능성을 제공하는 오픈 소스 소프트웨어입니다. Kubernetes, Docker, Mesos와 같은 컨테이너 오케스트레이션 플랫폼에서 네트워킹, 보안, 관찰 가능성을 제공하기 위해 설계되었습니다.

### 주요 특징:

- **eBPF 기반**: 커널 내에서 프로그래밍 가능한 데이터 경로를 통해 고성능 네트워킹 및 보안 기능 제공
- **API 인식 네트워킹**: L3-L7 계층에서 API 인식 네트워크 보안 정책 지원
- **Kubernetes 통합**: Kubernetes CNI(Container Network Interface) 구현 제공
- **분산 로드 밸런싱**: 효율적인 서비스 간 통신을 위한 분산 로드 밸런싱
- **네트워크 가시성**: Hubble을 통한 네트워크 흐름 모니터링 및 문제 해결
- **멀티 클러스터 지원**: 클러스터 간 네트워킹 및 보안 정책 지원
- **Kubernetes 호환성**: Kubernetes 1.30 이상 버전과 완벽하게 호환

### Cilium 아키텍처

![cilium-architecture](../assets/cilium_arch.png)

## 컨테이너 네트워킹 기초

컨테이너 네트워킹은 컨테이너화된 애플리케이션이 서로 통신하고 외부 세계와 통신할 수 있도록 하는 메커니즘을 제공합니다.

### 컨테이너 네트워킹 모델:

1. **호스트 네트워크**: 컨테이너가 호스트의 네트워크 네임스페이스를 공유
2. **브리지 네트워크**: 컨테이너가 호스트 내 가상 브리지에 연결
3. **오버레이 네트워크**: 여러 호스트에 걸쳐 가상 네트워크 생성
4. **언더레이 네트워크**: 물리적 네트워크 인프라를 직접 활용

### 컨테이너 네트워킹 과제:

- **확장성**: 수천 개의 컨테이너 및 서비스 지원
- **성능**: 지연 시간 최소화 및 처리량 최대화
- **보안**: 마이크로서비스 간 통신 보호
- **관찰 가능성**: 네트워크 흐름 모니터링 및 문제 해결
- **이식성**: 다양한 환경에서 일관된 네트워킹 경험 제공

## CNI(Container Network Interface) 이해하기

> **핵심 개념**: CNI(Container Network Interface)는 컨테이너 런타임과 네트워크 플러그인 간의 표준 인터페이스를 정의하는 CNCF 프로젝트입니다.

### CNI의 주요 구성 요소:

- **플러그인 아키텍처**: 다양한 네트워킹 솔루션을 통합할 수 있는 모듈식 설계
- **네트워크 구성**: JSON 형식으로 네트워크 설정 정의
- **IPAM(IP Address Management)**: IP 주소 할당 및 관리
- **표준 API**: 컨테이너 추가/제거 시 네트워크 설정을 위한 표준 API

### 주요 CNI 플러그인 비교:

| 기능 | Cilium | Calico | Flannel | AWS VPC CNI |
|------|--------|--------|---------|-------------|
| **기반 기술** | eBPF | iptables/IPVS | VXLAN/host-gw | AWS ENI |
| **네트워크 정책** | L3-L7 | L3-L4 | 제한적 | AWS 보안 그룹 |
| **암호화** | IPsec/WireGuard | IPsec | 없음 | 없음 |
| **관찰 가능성** | Hubble | Flow Logs | 제한적 | VPC Flow Logs |
| **서비스 메시** | 내장 | Istio 필요 | Istio 필요 | Istio/AppMesh 필요 |
| **성능** | 매우 높음 | 높음 | 중간 | 높음 |
| **IPAM** | 클러스터 풀, CRD | IPAM 플러그인 | 호스트 서브넷 | AWS IPAM |
| **Kubernetes 호환성** | 1.30+ | 1.29+ | 1.28+ | 1.29+ |
- **Weave Net**: 멀티 호스트 컨테이너 네트워킹
- **AWS VPC CNI**: AWS VPC와 직접 통합

## Cilium의 차별화 포인트

Cilium은 다른 CNI 솔루션과 비교하여 여러 고유한 이점을 제공합니다.

### 기술적 차별화:

- **eBPF 활용**: 커널 내 프로그래밍 가능한 데이터 경로를 통해 고성능 및 유연성 제공
- **API 인식 네트워킹**: L7 계층까지 네트워크 정책 지원
- **XDP(eXpress Data Path)**: 패킷 처리 성능 최적화
- **Kube-proxy 대체**: 더 효율적인 서비스 로드 밸런싱
- **Hubble 통합**: 강력한 네트워크 관찰 가능성 도구
- **최신 Kubernetes 호환성**: Kubernetes 1.30 이상 버전과 완벽하게 호환

### 사용 사례별 이점:

- **마이크로서비스 아키텍처**: 세분화된 네트워크 정책 및 관찰 가능성
- **멀티 클러스터 배포**: 클러스터 간 원활한 네트워킹
- **보안 중심 환경**: 강력한 네트워크 보안 정책
- **고성능 요구 사항**: 최적화된 데이터 경로
- **서비스 메시 통합**: Istio와 같은 서비스 메시와의 통합

## 실습: Cilium 설치 및 기본 구성

```bash
# Kubernetes 클러스터에 Cilium CLI 설치
curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz

# Cilium 설치
cilium install --version 1.17.0

# 설치 상태 확인
cilium status

# 연결성 테스트
cilium connectivity test
```

### 기본 네트워크 정책 적용:

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "allow-frontend-backend"
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
```

[메인 페이지로 돌아가기](README.md)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [주제 퀴즈](../../quizzes/cilium/01-introduction-quiz.md)를 풀어보세요.

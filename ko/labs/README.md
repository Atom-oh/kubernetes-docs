# 실습 가이드

> **마지막 업데이트**: 2026년 2월 22일

이 섹션에서는 Kubernetes와 관련 기술을 직접 실습해볼 수 있는 가이드를 제공합니다. 각 실습은 단계별 지침과 검증 방법을 포함하고 있어, 이론으로 배운 내용을 실제 환경에서 확인할 수 있습니다.

## 실습 목록

| # | 실습 | 난이도 | 사전 요구 사항 |
|---|------|--------|---------------|
| 1 | [Linux 기초 실습](basics/01-linux-basics-lab.md) | 초급 | Linux 터미널 접근 |
| 2 | [Linux 실무 기술 실습](basics/02-linux-advanced-lab.md) | 초급 | Linux 기초 완료 |
| 3 | [컨테이너 기술 실습](basics/03-container-technology-lab.md) | 초급 | Docker 설치 |
| 4 | [파드와 워크로드 실습](core/02-pods-and-workloads-lab.md) | 초급 | kubectl, K8s 클러스터 |
| 5 | [서비스와 네트워킹 실습](core/03-services-networking-lab.md) | 중급 | kubectl, K8s 클러스터 |
| 6 | [스토리지 실습](core/04-storage-lab.md) | 중급 | kubectl, K8s 클러스터 |
| 7 | [ConfigMap과 Secret 실습](core/05-configuration-secrets-lab.md) | 초급 | kubectl, K8s 클러스터 |
| 8 | [EKS 클러스터 생성 실습](eks/01-eks-cluster-creation-lab.md) | 중급 | AWS CLI, eksctl |
| 9 | [Observability E2E: 시리즈 소개](observability/README.md) | 고급 | AWS 계정, Terraform, Helm |
| 10 | [Observability E2E: 인프라 구성](observability/01-infrastructure-setup-lab.md) | 중급 | Part 0 완료 |
| 11 | [Observability E2E: Observability 스택](observability/02-observability-stack-lab.md) | 고급 | Part 1 완료 |
| 12 | [Observability E2E: MSA 배포 및 카나리](observability/03-msa-deployment-lab.md) | 고급 | Part 2 완료 |
| 13 | [Observability E2E: 부하 테스트 및 스케일링](observability/04-load-testing-scaling-lab.md) | 중급 | Part 3 완료 |
| 14 | [Observability E2E: 알림 및 AIOps](observability/05-alerting-aiops-lab.md) | 고급 | Part 4 완료 |
| 15 | [Observability E2E: 분산 추적 분석](observability/06-distributed-tracing-lab.md) | 고급 | Part 5 완료 |

## 권장 학습 순서

1. **기초 실습** (1→2→3): Linux와 컨테이너 기술 익히기
2. **핵심 실습** (4→7→5→6): Kubernetes 핵심 리소스 다루기
3. **EKS 실습** (8): 실제 클라우드 환경에서 클러스터 운영
4. **Observability 실습** (9→10→11→12→13→14→15): End-to-End 관측성 스택 구축 및 운영

## 실습 환경 준비

### 로컬 환경 (기초/컨테이너 실습용)
- Linux 터미널 (WSL2, macOS Terminal, 또는 Linux)
- Docker Desktop 또는 Docker Engine

### Kubernetes 환경 (핵심 실습용)
```bash
# minikube 설치 및 시작
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
minikube start

# kubectl 설치
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install kubectl /usr/local/bin/kubectl
```

### AWS 환경 (EKS 실습용)
- AWS 계정 및 AWS CLI 설정
- eksctl 설치

## 실습 팁

- 각 실습의 **사전 요구 사항**을 먼저 확인하세요
- 명령어 실행 후 **예상 결과**와 비교하여 올바르게 동작하는지 확인하세요
- 막힐 때는 **힌트**를 활용하세요
- 실습이 끝나면 반드시 **정리** 섹션의 명령어를 실행하여 리소스를 삭제하세요

# Linux 커널 개요

> **지원 버전**: Linux 6.1 / 6.12 / 6.18 (Amazon Linux 2023), Kubernetes 1.33+ (Amazon EKS)
> **마지막 업데이트**: 2026년 9월 12일

## 이 섹션에서 다루는 것

- 컨테이너와 Kubernetes가 실제로 무엇에 올라타 있는가 — namespace, cgroup, netfilter, conntrack의 커널 기능들
- 패킷이 Pod에서 나가 NIC에 닿기까지 커널 안에서 지나는 경로와, 그 경로의 각 지점에서 무엇을 관측하고 조정할 수 있는가
- EKS 노드에서 커널 파라미터가 워크로드 성능·안정성에 미치는 영향과, 무엇을 건드려야 하고 무엇을 두어야 하는가

## 왜 이 섹션이 필요한가

Kubernetes 문서는 대부분 **선언적 API 위에서** 설명됩니다. Pod를 만들면 컨테이너가 뜨고, Service를 만들면 트래픽이 분산되고, resource limit을 걸면 컨테이너가 그만큼만 씁니다.

그런데 장애를 진단할 때 필요한 지식은 그 아래 계층에 있습니다.

| 현장에서 만나는 증상 | 커널 계층의 실체 |
|---|---|
| "Pod가 OOMKilled인데 컨테이너 메모리는 limit 아래였다" | cgroup v2의 `memory.current`에 page cache가 포함됨. RSS만 보면 안 됨 |
| "노드의 새 연결이 조용히 드롭된다" | 다른 packet drop 원인과 함께 conntrack count/max·insert/drop counter·kernel log 조사 |
| "CPU limit을 걸었더니 p99가 튄다" | CFS/EEVDF throttling. 사용률은 낮은데 주기마다 강제로 멈춤 |
| "같은 노드 Pod 간 통신이 유독 빠르다" | veth 쌍만 지나고 NIC를 거치지 않음 |
| "Service 규칙이 수천 개인데 지연이 늘었다" | iptables 모드 kube-proxy의 선형 룰 평가 |

이런 증상들은 **Kubernetes API 계층에서는 원인이 보이지 않습니다.** 이 섹션은 그 간극을 메우는 것이 목적입니다.

## 대상 독자와 전제

- EKS·Kubernetes 운영 경험이 있고, 리소스 제약과 네트워크 장애를 직접 진단해야 하는 인프라 담당자
- Linux 기본 명령과 프로세스 개념은 알고 있다고 전제합니다
- 커널 소스를 읽거나 모듈을 작성하는 것은 다루지 않습니다. **운영자가 관측하고 조정할 수 있는 범위**에 집중합니다

## 문서 구성

| # | 문서 | 다루는 질문 |
|---|------|------------|
| 1 | [컨테이너를 지탱하는 커널 기능](./01-container-primitives.md) | 컨테이너는 무엇으로 만들어지는가. cgroup v1과 v2의 차이가 왜 운영에 영향을 주는가 |
| 2 | [커널 네트워킹 스택](./02-network-stack.md) | 패킷이 socket에서 NIC까지 어떤 경로를 지나는가. 어디에 훅을 걸 수 있는가 |
| 3 | [EKS 노드 커널 튜닝](./03-eks-node-tuning.md) | 어떤 파라미터를 언제 건드려야 하는가. 기본값을 두는 게 정답인 경우는 언제인가 |

## 이 섹션을 읽는 순서

1번은 2번과 3번의 선행 개념입니다. cgroup과 namespace를 모르면 3번의 튜닝 항목이 왜 그 위치에 있는지 이해되지 않습니다.

네트워크 문제를 진단하러 오셨다면 **2번 → 3번의 네트워크 절**만 읽어도 됩니다. 리소스 제약(OOM, CPU throttling) 문제라면 **1번의 cgroup 절 → 3번의 메모리·CPU 절**이 경로입니다.

## 관련 문서

- [Linux 기초](../basics/01-linux-basics.md) / [Linux 운영 기술](../basics/02-linux-advanced.md) — 명령어와 기본 운영
- [컨테이너 기술](../basics/03-container-technology.md) — 컨테이너 런타임과 이미지 계층
- [eBPF 기초와 실무 활용](../basics/05-ebpf-fundamentals.md) — eBPF 프로그램 타입과 활용
- [네트워크 기초 4부작](../basics/06-network-fundamentals-part1.md) — 계층 모델부터 클라우드까지
- [Pod 네트워크 실측 벤치마크](../networking/06-pod-network-benchmark.md) — 이 섹션의 이론에 대응하는 실측값
- [리소스 최적화](../ops/10-resource-optimization.md) — request/limit 설계
- [VPC Lattice 커널 데이터패스](../service-mesh/vpc-lattice/07-kernel-datapath.md) — link-local 인터셉트의 커널 계층

## 정확성에 대한 안내

커널 기능은 버전에 따라 동작이 바뀌고, 특히 **튜너블의 위치와 이름이 커널 버전 간에 이동합니다**(sysctl → debugfs 등). 이 섹션은 AL2023이 제공하는 커널 계열(6.1 / 6.12 / 6.18)을 기준으로 쓰되, 버전 의존적인 항목은 어느 버전 기준인지 명시했습니다.

공식 문서로 확인되지 않은 항목은 단정하지 않고 `확인 필요` 블록으로 표시했습니다. **운영 클러스터에 파라미터를 적용하기 전에 해당 노드의 커널 버전에서 실제 값을 직접 확인**하시기 바랍니다.

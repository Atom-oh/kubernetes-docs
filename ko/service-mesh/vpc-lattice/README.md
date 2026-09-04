# VPC Lattice 딥다이브 개요

> **지원 버전**: Amazon VPC Lattice (GA), AWS Gateway API Controller v1.1+, Kubernetes 1.28+ (Amazon EKS)
> **마지막 업데이트**: 2026년 9월 3일

## 이 섹션에서 다루는 것

- sidecar 프록시 기반 서비스 메시(App Mesh, Istio)에서 **관리형 데이터플레인**(VPC Lattice)으로 모델이 바뀔 때 실제로 무엇이 달라지는가
- Lattice의 내부 동작 — link-local 주소로 트래픽을 가로채는 구조, SigV4 요청 서명 검증, 3중 auth policy 평가
- SPIFFE/SPIRE 기반 워크로드 신원을 IAM 신원으로 옮길 때의 구조적 차이와, 그것이 왜 심의 쟁점이 되는가

## 왜 이 섹션이 따로 필요한가

이 섹션은 **개념 이해**를 목적으로 합니다. Lattice 리소스를 만드는 방법이나 AWS Gateway API Controller 설치 절차는 [VPC Lattice](../../networking/02-vpc-lattice.md) 문서에 이미 있고, Istio와의 기능 대비는 [Istio vs VPC Lattice](../istio/comparison/02-istio-vs-lattice.md)에 있습니다. 여기서는 그 두 문서가 다루지 않는 것 — **"왜 그렇게 설계되었는가"와 "그 설계에서 무엇이 파생되는가"**를 다룹니다.

배경에는 시급성이 있습니다. **AWS App Mesh는 2026년 9월 30일 지원이 종료**되며, 그 이후에는 App Mesh 콘솔과 App Mesh 리소스에 접근할 수 없습니다. 신규 고객 온보딩은 2024년 9월 24일부터 이미 중단되었습니다. 즉 App Mesh를 운영 중인 조직에게 이 전환은 선택이 아니라 기한이 정해진 과제입니다.

그런데 App Mesh와 Lattice는 **같은 문제를 푸는 두 개의 구현이 아닙니다.** 데이터플레인이 있는 위치가 다르고(Pod 안 vs AWS 인프라), 신원을 증명하는 단위가 다르며(connection vs 요청), 신뢰 근원을 소유한 주체가 다릅니다(고객 CA vs AWS IAM/STS). 리소스 이름을 하나씩 갈아끼우는 식으로 접근하면 전환 후반에 기능 공백과 심의 반려를 만나게 됩니다. 이 섹션은 그 공백들을 **먼저** 드러내는 것이 목적입니다.

## 대상 독자와 전제

- AWS 아키텍트, 고객 인프라 담당자
- EKS와 Kubernetes는 이미 알고 있다고 전제합니다
- VPC Lattice와 서비스 메시 내부 동작은 처음 접한다고 전제합니다
- 코드와 매니페스트 예시는 최소한으로 유지합니다. 실습 가이드가 아닙니다

## 문서 구성

| # | 문서 | 다루는 질문 |
|---|------|------------|
| 1 | [App Mesh와 VPC Lattice 아키텍처 대비](./01-appmesh-vs-lattice.md) | 데이터플레인이 Pod에서 인프라로 옮겨가면 무엇이 남고 무엇이 사라지는가 |
| 2 | [레이턴시 영향 분석](./02-latency.md) | 악화 요인과 개선 요인이 동시에 있다. 우리 환경은 어느 쪽인가 |
| 3 | [IAM 인증 절차 상세](./03-auth-flow.md) | 요청 하나가 서명되고 검증되고 인가되기까지 4단계에서 무엇이 일어나는가 |
| 4 | [기반 개념 — link-local과 SNI](./04-networking-basics.md) | 사이드카 없이 어떻게 트래픽을 가로채는가. TLS를 종료하지 않으면 무엇을 잃는가 |
| 5 | [워크로드 신원 모델 전환 — SPIFFE에서 IAM으로](./05-spiffe-to-iam.md) | SPIRE가 하던 일을 IAM이 대신할 수 있는가. 무엇이 대체되지 않는가 |
| 6 | [제약사항과 의사결정 포인트](./06-constraints.md) | 설계를 확정하기 전에 반드시 답해야 하는 항목은 무엇인가 |

1번부터 순서대로 읽는 것을 권합니다. 4번(link-local, SNI)은 3번과 6번의 제약을 이해하는 데 필요한 선행 개념이라 뒤에 두었지만, 네트워크 기반 개념이 익숙하지 않다면 4번을 먼저 읽어도 됩니다.

## 정확성에 대한 안내

이 섹션의 사실 관계는 AWS 공식 문서, AWS Gateway API Controller 공식 문서, `aws-samples/migrating-from-aws-app-mesh-to-amazon-vpc-lattice` 레퍼런스 구현, SPIFFE/SPIRE 공식 문서를 근거로 작성했습니다.

공식 문서로 확인되지 않은 항목은 단정하지 않고 `확인 필요` 블록으로 표시했습니다. Lattice는 기능이 계속 추가되는 서비스이므로, 특히 **quotas와 요금은 리전·시점에 따라 달라집니다.** 설계 확정 전에 Service Quotas 콘솔과 [VPC Lattice 요금 페이지](https://aws.amazon.com/vpc/lattice/pricing/)에서 현재값을 직접 확인하시기 바랍니다.

## 관련 문서

- [VPC Lattice](../../networking/02-vpc-lattice.md) — Lattice 리소스 구성과 Gateway API Controller 설치 절차
- [Gateway API](../../networking/04-gateway-api.md) — Kubernetes Gateway API 표준
- [Istio vs VPC Lattice](../istio/comparison/02-istio-vs-lattice.md) — 기능·비용·운영 복잡도 비교
- [Istio Security — mTLS](../istio/security/01-mtls.md) — sidecar 기반 상호 인증의 동작
- [Pod 네트워크 실측 벤치마크](../../networking/06-pod-network-benchmark.md) — 같은 AZ와 Cross-AZ 레이턴시 실측 기준선

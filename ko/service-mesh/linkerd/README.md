# Linkerd

> **마지막 업데이트**: 2026년 9월 11일 · 공개 CLI 예제 검증: edge-26.9.1

Upstream 프로젝트는 edge 산출물을 배포하며 stable 배포판과 지원 수명 주기는 vendor가 제공합니다. Linkerd 2.20은 기능 milestone이지 내려받은 CLI의 보편적인 버전 문자열이 아닙니다. 정확한 배포판·릴리스를 고르고 Kubernetes·Gateway API 호환성을 확인하세요. 여기의 공개 예시는 2026년 9월 4일 게시된 edge-26.9.1입니다. Multicluster 원격 credential의 exec auth provider 수용 문제와 목적지 IP 충돌의 retry 가능 오류 처리를 수정했습니다. [릴리스](https://github.com/linkerd/linkerd2/releases/tag/edge-26.9.1)와 [배포 모델](https://linkerd.io/releases/)을 참고하세요.

아래는 과거 릴리스 맥락을 보존한 기록입니다. Edge-26.8.2의 테스트 Kubernetes 상한이 stable vendor 배포판의 지원 범위를 자동 확대하지는 않습니다.

### 2026년 8월 업데이트: edge-26.8.4

2026년 8월 25일 공개된 edge-26.8.4 릴리스에는 opaque 프로토콜 처리에서 nil ExternalWorkload를 방어하지 못하던 문제 수정, policy 컨트롤러가 TLSRoute API 버전을 클러스터와 협상(negotiate)하도록 하는 수정, Go 1.26.7 업데이트가 포함되었습니다. 자세한 내용은 [릴리스 노트](https://github.com/linkerd/linkerd2/releases/tag/edge-26.8.4)를 참고하세요.

### 2026년 8월 업데이트: edge-26.8.2 — Gateway API 1.5.1 지원

2026년 8월 14일 공개된 edge-26.8.2 릴리스는 Gateway API 1.5.1 지원(linkerd-kubert 0.27.0 경유)을 추가하고, 테스트된 최대 Kubernetes 버전을 1.36으로 올렸습니다. 그 외 destination 컨트롤러의 중복 Job informer 제거, lease watch 태스크가 죽으면 policy 컨트롤러가 함께 종료되도록 하는 안정성 수정이 포함되었습니다. 자세한 내용은 [릴리스 노트](https://github.com/linkerd/linkerd2/releases/tag/edge-26.8.2)를 참고하세요.

### 2026년 7월 업데이트: edge-26.7.1 — 미정의 서비스 포트 요청 차단

edge-26.7.1의 GitHub 릴리스 게시일은 2026년 7월 21일입니다. ServiceProfile이 있어도 목적지 Service에 선언하지 않은 포트의 요청을 거부하는 동작 변경이 포함되었습니다. 업그레이드 전에 실제 Service port 선언을 확인하세요. Gateway API 설치 검사도 추가되었습니다. [릴리스 노트](https://github.com/linkerd/linkerd2/releases/tag/edge-26.7.1)를 참고하세요.

## 개요

Linkerd는 Rust 데이터 플레인 프록시를 사용하는 CNCF 졸업 서비스 메시입니다. CNCF 기록상 첫 commit은 2016년, 졸업은 2021년입니다. “단순함”이나 “경량”을 보장으로 해석하기보다 실제 workload에 운영 모델, protocol 지원과 리소스 사용이 맞는지 평가하세요.

### 핵심 가치

| 기능 | 확인할 사항 |
|---|---|
| 기본 workload mTLS | 양쪽 peer의 mesh 등록과 proxy 우회 여부. Unmeshed plaintext에는 별도 인가 정책 필요 |
| Rust proxy | 예상 연결·트래픽의 memory/CPU request, limit과 실제 사용량 |
| HTTP/gRPC 라우팅 | 지원되는 Gateway API type, 부착과 protocol detection |
| 운영 | 인증서 수명 주기, HA, 업그레이드 호환과 확장 소유 |
| 성능 | 실제 지연·오류·부하 측정. 보편적인 10MB·1ms 미만 보장 없음 |

## Linkerd 아키텍처 개요

| 구성 요소 | 역할 |
|---|---|
| Destination·policy controller | Endpoint를 발견하고 라우팅·인가 정책을 proxy에 배포 |
| Identity | Identity 요청을 검증하고 구성한 신뢰 credential로 단기 workload 인증서 발급 |
| Proxy Injector | 대상인 새 Pod를 변형해 proxy 추가 |
| linkerd-proxy | 구성된 TCP 트래픽을 처리하고 해당 mesh 경로 인증·암호화 및 지원 L7 기능 제공 |
| 선택적 확장·backend | Viz metrics/dashboard, multicluster 통합, 별도로 구성한 trace 수집·저장 |

이 아키텍처만으로 고정 메모리나 지연 오버헤드가 정해지지 않습니다. 선택한 workload와 설정에서 측정해야 합니다.

## 서비스 메시 비교

| 항목 | Linkerd | Istio | Cilium |
|---|---|---|---|
| 데이터 플레인 | Rust sidecar | Envoy sidecar 또는 ztunnel·waypoint | eBPF networking과 지원 L7 기능의 Envoy |
| HTTP 라우팅 | Gateway API route. 이전 ServiceProfile 방식도 지원 | Istio API 또는 지원 Gateway API 부착 | Gateway API와 Cilium policy/controller 기능 |
| 보안 | 대상 mesh TCP peer 사이 자동 mTLS. 다른 출발지는 인가로 제어 | Auto mTLS, 수신 적용과 인가는 별도 제어 | Peer 인증과 payload 암호화를 별도로 평가 |
| 관측성 | Proxy metric과 구성한 Viz/기타 backend | 모드별 telemetry와 구성한 backend | Hubble 및 구성한 L7/metric backend |
| Multicluster | Mirroring/federation과 명시적 trust/network 구성 | 지원 토폴로지별 mesh 설정 | ClusterMesh와 플랫폼·네트워크 요구 |
| 선택 | 필요한 기능과 운영 검증 | 필요한 기능과 운영 검증 | 필요한 기능과 운영 검증 |

SMI TrafficSplit은 이전 방식이며 현재 Linkerd 라우팅의 전체 설명이 아닙니다. Gateway API로 HTTP/gRPC 요청 속성에 따라 라우팅할 수 있습니다. 재현 가능한 workload·버전별 측정 없이 고정 memory·p99·인력·복잡성 순위를 비교할 수 없습니다.

## Linkerd를 선택해야 할 때

기본 Kubernetes 통합, workload identity와 지원 HTTP/gRPC/TCP 동작이 앱 요구에 맞을 때 후보가 됩니다. 실제 부하에서 리소스 효율·지연을 측정하고 CA 회전, 접근 정책과 업그레이드를 계획하세요. 자동 전송 암호화만으로 완전한 zero-trust나 규정 준수가 되지는 않습니다.

필요한 라우팅·filter·확장 기능을 구체적으로 확인하세요. 비HTTP protocol도 TCP로 proxy할 수 있지만 HTTP routing·metric이 생기지는 않습니다. Server-first·idle 연결에는 opaque-port 또는 appProtocol 구성이 필요할 수 있으며 앱이 시작한 TLS는 HTTP 검사에 opaque합니다. Opaque 트래픽도 proxy를 통과하고 skip port는 우회합니다.

VM·물리 머신 통합은 ExternalWorkload 등록과 외부 identity/bootstrap을 포함한 [mesh expansion](https://linkerd.io/docs/tasks/adding-non-kubernetes-workloads/)으로 가능합니다. 범주 전체가 미지원인 것은 아닙니다. Network 연결, DNS, proxy 설치와 trust 설계가 Pod 주입 외에 필요하며 upstream tutorial의 간단한 bootstrap 구성이 운영 설계는 아닙니다.

## 문서 구성

| 문서 | 설명 |
|---|---|
| [설치 및 설정](01-installation.md) | 정확한 릴리스·호환성, CLI/Helm, trust credential, HA와 확장 |
| [아키텍처](02-architecture.md) | Controller, proxy와 인증서 계층 |
| [트래픽 관리](03-traffic-management.md) | Gateway API, 이전 ServiceProfile, retry/timeout과 traffic split |
| [보안](04-security.md) | mTLS 경계, 인가와 CA 회전 |
| [관찰성](05-observability.md) | Metrics, Viz, 외부 backend와 tracing |
| [다중 클러스터](06-multi-cluster.md) | Mirroring/federation, network 경로, trust와 credential |
| [모범 사례](07-best-practices.md) | 운영 검증, 성능과 문제 해결 |

## 빠른 시작

### 1. CLI와 전제 조건 선택

[설치 가이드](01-installation.md)에서 OS/architecture와 정확한 릴리스를 선택하세요. CLI 출력이 의도한 배포판과 맞는지 확인하고 버전 없는 installer가 예전 stable을 제공한다고 가정하지 않습니다. Gateway API CRD가 필요하며 설치 bundle은 사용하는 모든 controller와 호환되어야 합니다.

```bash
linkerd version --client
kubectl config current-context
kubectl get crd httproutes.gateway.networking.k8s.io   -o 'jsonpath={.metadata.annotations.gateway\.networking\.k8s\.io/bundle-version}'
linkerd check --pre
```

### 2. Render, 검토와 설치

선택한 CLI와 전제 조건을 갖춘 새 통제 실습에서 CLI는 매니페스트를 생성합니다:

```bash
set -euo pipefail
linkerd install --crds > linkerd-crds.yaml
# Review CRD ownership/version before applying.
kubectl apply -f linkerd-crds.yaml
linkerd install > linkerd-control-plane.yaml
# Review trust credentials and deployment settings before applying.
kubectl apply -f linkerd-control-plane.yaml
linkerd check
```

기본 CLI 구성은 유한한 유효기간의 trust credential을 생성하며 공유 trust multicluster 완성 구성이 아닙니다. 장기 설치는 문서화된 Helm·CA 수명 주기 절차를 따르세요. 이번 검토는 오프라인 render와 CLI 문법을 확인했으며 실제 설치는 하지 않았습니다.

### 3. 의도한 애플리케이션 추가

기존 namespace와 Deployment를 선택하고 두 my-app 이름을 실제 대상으로 바꿉니다:

```bash
kubectl annotate namespace my-app linkerd.io/inject=enabled
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
linkerd check --proxy -n my-app
```

기존 annotation이 충돌하면 자동으로 덮어쓰지 말고 검토하세요. 새 Pod에만 주입되며 rolling restart에는 workload readiness·capacity 조건이 필요합니다. 수동 주입은 검토한 앱 매니페스트에 적용할 수도 있습니다. 모든 live Deployment를 inject/apply로 왕복하는 방식을 일괄 수정으로 쓰지 않습니다.

### 4. 필요한 경우 Viz 추가

```bash
linkerd viz install > linkerd-viz.yaml
# Review the extension's backend, resources and retention.
kubectl apply -f linkerd-viz.yaml
linkerd viz check
linkerd viz dashboard
```

Viz는 선택적이며 자체 수명 주기 관리가 필요합니다. 기본 metric 구성이 모든 운영 보존·HA 요구를 충족하지는 않습니다.

## Linkerd 컴포넌트 상태 확인

```bash
# Core installation/control-plane checks.
linkerd check
# Data-plane proxy checks in the selected namespace.
linkerd check --proxy -n my-app
# Requires the configured Viz extension.
linkerd viz stat deploy -n my-app
linkerd viz tap deploy/my-app -n my-app
```

Tap은 지원되는 HTTP 요청 이벤트를 관찰하며 모든 TCP 경로, packet 또는 암호화 경계의 증거가 아닙니다.

## 핵심 개념

### 데이터 플레인 프록시

Rust linkerd-proxy는 등록된 workload 옆에서 구성된 TCP 경로를 처리합니다. Skip port, unmeshed endpoint와 플랫폼 제한을 별도로 확인하세요. HTTP 동작에는 보이거나 감지되는 HTTP가 필요합니다. 일정한 Pod당 사용량을 가정하지 말고 실제 리소스·지연을 측정합니다.

### 서비스 디스커버리

Destination·policy 구성 요소는 Service/endpoint 상태를 감시하고 라우팅 정보를 제공합니다. ServiceProfile과 Gateway API는 버전별 우선순위·지원 기능이 다른 설정 경로입니다. 필요한 모든 Service port를 선언하고 앞의 과거 동작 변경 기록을 확인하세요.

### 자동 mTLS

문서화된 workload 인증서 기본 유효기간은 24시간이며 자동 갱신됩니다. Identity는 Pod의 ServiceAccount에 연결되므로 Pod마다 고유한 identity가 아닙니다. Trust anchor와 issuer credential은 별도의 수명 주기를 가지며 기본 CLI 생성 credential은 1년 후 만료되어 회전 계획이 필요합니다.

Meshed TCP peer 사이에는 mTLS를 사용하지만 unmeshed peer·skip port 트래픽에는 그 자동 보장이 적용되지 않습니다. 기본 inbound policy는 unmeshed plaintext를 허용하므로 차단이 필요하면 인가 정책을 사용하세요. Multicluster에는 공유 trust와 명시적인 연결 경로가 필요합니다.

## 다음 단계

1. [설치 및 설정](01-installation.md)
2. [아키텍처](02-architecture.md)
3. [설치 퀴즈](../../quizzes/service-mesh/linkerd/installation.md), [아키텍처 퀴즈](../../quizzes/service-mesh/linkerd/architecture.md), [트래픽 퀴즈](../../quizzes/service-mesh/linkerd/traffic-management.md)
4. [보안 퀴즈](../../quizzes/service-mesh/linkerd/security.md), [관측성 퀴즈](../../quizzes/service-mesh/linkerd/observability.md), [멀티클러스터 퀴즈](../../quizzes/service-mesh/linkerd/multi-cluster.md)

## 참고 자료

- [Linkerd 문서](https://linkerd.io/docs/overview/)
- [릴리스 구분](https://linkerd.io/releases/)과 [설치](https://linkerd.io/docs/tasks/install/)
- [Gateway API](https://linkerd.io/docs/features/gateway-api/)와 [요청 라우팅](https://linkerd.io/docs/features/request-routing/)
- [자동 mTLS와 제약](https://linkerd.io/docs/features/automatic-mtls/) 및 [TCP/protocol 처리](https://linkerd.io/docs/features/protocol-detection/)
- [CNCF 프로젝트 기록](https://www.cncf.io/projects/linkerd/)
- [Linkerd GitHub](https://github.com/linkerd/linkerd2), [커뮤니티](https://slack.linkerd.io/), [Buoyant 블로그](https://buoyant.io/blog)

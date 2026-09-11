# 비교 가이드

> **마지막 검토**: 2026년 9월 11일
> **대상 독자**: 아키텍트, DevOps 엔지니어, 플랫폼 엔지니어

필요한 트래픽, identity, 플랫폼과 운영 조건을 비교한 뒤 mesh를 선택합니다. 조직 규모, 기능 별점이나 고정 overhead 비율만으로 적합성을 판단할 수 없습니다. 버전 지원과 release channel도 아키텍처 비교와 별도로 확인해야 합니다.

## 목차

### 1. [Service Mesh 솔루션 비교](01-service-mesh-comparison.md)

상세 비교는 Istio, Linkerd, Kong Mesh/Kuma와 Consul service mesh를 다룹니다. Networking과 mesh 기능을 함께 평가한다면 유지보수되는 [Cilium service-mesh 가이드](../../cilium-service-mesh/README.md)도 확인하세요.

Data/control plane, 지원하는 traffic policy, identity와 암호화, 관측성, Kubernetes/VM 지원, multicluster 토폴로지, lifecycle과 상용 배포 조건을 비교합니다. Resource 사용량은 동일한 정책·트래픽으로 측정하며 제품에 항상 높음/중간/낮음 등급을 붙이지 않습니다.

### 2. [Istio vs VPC Lattice](02-istio-vs-lattice.md)

Istio는 Kubernetes와 문서화된 VM 통합을 제공하는 배포형 mesh입니다. VPC Lattice는 지원되는 EC2, container, Lambda target 등을 포함하는 service/resource용 AWS 관리형 application networking입니다. 모든 앱이 serverless일 필요는 없습니다.

Protocol/routing, 각 TLS 경계의 identity, Region 연결, 운영 주체의 책임과 실제 과금 항목을 비교합니다. 관리형 network라도 앱, DNS, IAM, target health와 비용 관리는 남습니다.

### 3. [Sidecar vs Ambient](03-sidecar-vs-ambient.md)

이 가이드는 mTLS, NetworkPolicy, latency와 rollout 실패에 관한 EKS 실험 기록을 포함합니다. 각 결과의 실제 버전, workload, 측정 구간과 원시 503 결과를 결론과 함께 보존하세요. Retry 후 client가 본 결과는 별도 측정입니다. Retry가 실패를 가리거나 비멱등 작업을 중복 실행할 수 있습니다.

이 관측으로 실제 workload의 시험을 설계할 수 있지만 sidecar와 waypoint의 신뢰성에 보편적인 순위를 매기거나 core/semi-core/peripheral 배치를 강제할 수는 없습니다.

## 선택 기준

| 요구사항 | 평가할 후보 기능 | 필요한 근거 |
|---|---|---|
| 세밀한 L7 traffic·policy | Istio와 필요한 Linkerd/Kong/Consul/Cilium 기능 | 지원 API, protocol 동작, 생성된 설정과 upgrade 시험 |
| Kubernetes 중심 mesh | Linkerd 또는 범위를 조정한 Istio 배포 | 실제 운영 노력, identity lifecycle, 기능 충족과 동일 부하 측정 |
| 기존 Cilium networking | eBPF datapath와 proxy 기반 L7 기능 | Kernel/CNI 호환성, 활성화한 L7 기능, 별도 authentication/encryption 조건 |
| AWS service/resource 연결 | VPC Lattice | Regional network/endpoint 경로, target 지원, IAM/TLS와 service/resource owner의 책임 |
| VM·hybrid workload | Istio VM, Linkerd mesh expansion, Kong Universal 또는 Consul runtime | Workload identity, DNS, IP/API 접근과 runtime별 제약 |
| Multicluster·multicloud | 선택한 mesh의 지원 토폴로지와 외부 networking | Trust 경계, 설정 배포, 데이터 복구, latency와 전송 비용 |
| 상세한 관측성 | 선택한 mesh와 적절한 metrics/logging/tracing backend | 실제 telemetry label, 앱 context 전파, sampling, retention과 접근 제어 |

자동 제품 추천이 아닌 평가 후보입니다. Tracing backend와 dashboard도 별도 설정이 필요한 의존성이며, 필요한 context 전파/instrumentation 없이 mesh만으로 전체 앱 trace가 완성되지는 않습니다.

## 빠른 아키텍처 비교

| 솔루션 | Data plane | 플랫폼·운영 조건 |
|---|---|---|
| Istio | Envoy sidecar; ambient는 노드별 ztunnel과 선택적 Envoy waypoint | Kubernetes·문서화된 VM 통합; 모드별 기능/토폴로지 지원; 자체 운영 또는 vendor 배포 |
| Linkerd | Rust linkerd2-proxy | Kubernetes와 ExternalWorkload·호환 identity/network를 쓰는 non-Kubernetes mesh expansion; “VM 미지원”이 아님 |
| Kong Mesh | Envoy data-plane proxy | Kubernetes와 Universal VM/bare-metal mode; 자체 운영 또는 관리형 global control plane과 edition별 기능 |
| Consul service mesh | Consul discovery/control plane과 Envoy sidecar | Kubernetes, VM과 다른 runtime 통합; 선택한 edition/version·proxy 호환성 확인 |
| Cilium | eBPF network datapath와 L7용 Envoy 등의 proxy | 활성화한 component·플랫폼 지원 확인; L7 전체가 proxy 없이 동작하는 것은 아님 |

Cilium 1.20.1의 mutual authentication은 공식 문서상 **Beta**이며 out-of-band handshake를 사용합니다. 트래픽 암호화에는 별도 WireGuard/IPsec 설정이 필요합니다. 모든 앱 연결을 Istio 방식의 TLS session으로 자동 감싸는 기능과 같지 않습니다. 문서화된 Cluster Mesh·외부 mTLS 제약도 확인해야 합니다.

Linkerd의 project milestone version과 실제 설치 artifact는 별도 선택입니다. 공식 release 페이지는 Linkerd 2.20과 대응 edge release를 구분합니다. 오픈소스 project가 edge artifact를 배포하고 stable artifact는 vendor가 제공합니다. Release 권고, Kubernetes 호환성, update/support 조건과 subscription 비용을 확인하며 오래된 문서 링크로 artifact/channel을 추정하지 마세요.

### Istio와 VPC Lattice

| 항목 | Istio | VPC Lattice |
|---|---|---|
| 배포 | Control/data plane 직접 운영 또는 vendor 배포 선택 | AWS가 networking service 운영; 사용자는 service/resource, 접근과 target 구성 |
| 플랫폼 | 명시적인 network/trust 조건의 Kubernetes·VM 통합 | 지원 service target/resource configuration과 문서화된 client 경로의 AWS networking |
| Traffic/security 모델 | 모드별 mesh routing, workload identity와 policy | Listener/rule/target·service auth policy; resource configuration은 다른 제어 사용 |
| 운영 | Proxy/control-plane lifecycle, 용량, certificate, policy와 telemetry | IAM/sharing, DNS/endpoint, target health, controller, quota와 telemetry 관리 필요 |
| 비용 | Compute, LB, 전송, storage/telemetry와 선택적 support | 해당 provisioned/usage 과금과 주변 인프라·운영 비용 |
| Hybrid 통합 | Gateway/trust/identity의 명시적 설계 | Regional endpoint/network·TLS/authentication 경계 필요; 자동 cross-cloud mesh federation이 아님 |

기능 별점과 단일 vendor의 “enterprise support” 표시는 제외합니다. 가용성, license와 지원은 실제 배포·계약에 따르며 integration 이름이 설정의 검증을 뜻하지는 않습니다.

## 마이그레이션 지침

### Linkerd에서 Istio로

설정 변환 전에 traffic API, retry/timeout, authorization, identity, certificate와 telemetry를 파악합니다. Linkerd도 annotation 외에 CRD를 사용하므로 단순 annotation→Istio CRD 변환이 아닙니다. 검증된 공존 경로로 service/namespace 단위를 단계적으로 전환하고 동일 Pod에 겹치는 traffic capture나 mesh sidecar 두 개를 주입하지 않도록 합니다.

### Kubernetes에서 Mesh로

Workload identity, policy, resilience 또는 관측성 중 충족되지 않은 요구사항부터 확인합니다. Service 수만으로 mesh 도입 기준을 정하지 않습니다. 기존 Service, 유지보수되는 Ingress/Gateway API 구현, NetworkPolicy와 앱 instrumentation이 요구사항을 충족할 수도 있습니다. 제한된 workload에서 injection/ambient 등록, 시작·drain, 정책 강제와 rollback을 검증하세요.

### Istio와 VPC Lattice

Hybrid는 cluster 내부 Istio와 명시적으로 구성한 service 경로의 Lattice를 함께 사용할 수 있습니다. 모든 TLS 종료점과 caller identity를 정의해야 합니다. Lattice IAM 인증 요청에는 문서화된 서명/인가 경로가 필요하며 mesh mTLS만으로 SigV4 identity나 end-to-end SPIFFE 전파가 생기지 않습니다. 같은 route, target 또는 DNS resource를 controller 여러 개가 경쟁해서 관리하지 않게 합니다.

## FAQ

<details>
<summary>Service mesh는 항상 필요한가요?</summary>

아닙니다. Networking, identity, policy 또는 관측성 중 아직 충족하지 못한 요구사항을 확인하세요. 작은 service에도 강한 identity 제어가 필요할 수 있고 큰 시스템이 이미 다른 계층에서 필요한 제어를 구현했을 수도 있습니다. 실제 운영·resource 비용과 이점을 비교합니다.

</details>

<details>
<summary>Istio와 Linkerd 중 무엇을 선택해야 하나요?</summary>

정확한 routing/security/observability 기능, 플랫폼 지원과 운영 절차를 비교합니다. Linkerd가 “기본 기능”이나 Kubernetes workload만으로 제한되지는 않으며 Istio의 sidecar·ambient도 resource와 기능 조건이 다릅니다. 같은 대표 workload를 시험하고 release/support 옵션을 검토한 뒤 결정하세요.

</details>

<details>
<summary>VPC Lattice는 언제 후보가 되나요?</summary>

지원하는 service/resource 모델과 AWS networking/authentication 조건이 앱에 맞을 때입니다. Container, EC2와 Lambda 혼합이 관련될 수 있지만 “AWS 중심”이나 “serverless”만으로 충분하지는 않습니다. Region, client 경로, target type, protocol, identity와 비용 가정을 확인하세요.

</details>

<details>
<summary>Overhead는 얼마나 예상해야 하나요?</summary>

제품 전체에 보편적으로 적용되는 latency, CPU 비율, Pod당 메모리 값은 없습니다. 동일한 policy, TLS, traffic, concurrency, node/proxy/waypoint 수와 실패 동작으로 측정합니다. 재현 가능한 benchmark는 원래 version과 raw data를 보존하세요. 관리형 network도 처리 경로, 관측 작업과 과금이 있어 인프라 영향이 0은 아닙니다.

</details>

<details>
<summary>Mesh 여러 개가 공존할 수 있나요?</summary>

분리한 cluster/workload 집합이나 명시적인 migration/hybrid 경계에서 공존할 수 있습니다. 동일 Pod/network 경로의 interceptor 여러 개는 충돌할 수 있습니다. Namespace를 나누기만 하면 상호운용된다고 가정하지 말고 traffic ownership, trust/identity 변환, telemetry와 rollback을 정의하세요.

</details>

## 관련 자료

- [Istio 아키텍처](../03-architecture.md)
- [트래픽 관리](../traffic-management/README.md)
- [보안](../security/README.md)
- [관측성](../observability/README.md)
- [VPC Lattice](../../../networking/02-vpc-lattice.md)
- [Linkerd](../../linkerd/README.md)
- [Cilium service mesh](../../cilium-service-mesh/README.md)

## 공식 근거

- [Istio 문서](https://istio.io/latest/docs/)와 [VM 통합](https://istio.io/latest/docs/setup/install/virtual-machine/)
- [Linkerd 개요](https://linkerd.io/docs/overview/), [mesh expansion](https://linkerd.io/docs/tasks/adding-non-kubernetes-workloads/), [release channel](https://linkerd.io/releases/)
- [Kong Mesh](https://developer.konghq.com/mesh/)와 [아키텍처](https://developer.konghq.com/mesh/architecture/)
- [Consul service mesh](https://developer.hashicorp.com/consul/docs/connect)
- [Cilium 1.20.1 mesh 아키텍처 원문](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/network/servicemesh/index.rst)과 [mutual authentication 상태](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
- [VPC Lattice 구성요소와 운영 책임](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html)

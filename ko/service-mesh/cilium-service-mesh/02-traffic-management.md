# Cilium Service Mesh 트래픽 관리

> **검토 기준**: Cilium 1.20.1, Gateway API 1.6.1, 2026년 9월 11일. Kubernetes/EKS 테스트 범위와 플랫폼 요건은 [개요](./README.md)를 참고하세요.

## 개요

Cilium Service Mesh의 트래픽 관리는 eBPF 기반 L4 로드 밸런싱과 Envoy 기반 L7 라우팅을 결합하여 제공됩니다. 이 장에서는 CiliumEnvoyConfig, CiliumNetworkPolicy의 L7 규칙, Gateway API 통합 등을 통한 고급 트래픽 관리 기능을 설명합니다.

## 트래픽 관리 아키텍처

![클라이언트 요청이 L7 Envoy 계층의 HTTP 라우팅, L4 eBPF 계층의 로드 밸런싱, L3 eBPF 계층의 IP 라우팅을 차례로 거쳐 서버에 도달하는 경로와, 각 계층이 함께 제공하는 gRPC 라우팅·NAT·네트워크 정책 등의 트래픽 관리 기능을 보여준다.](../../.gitbook/assets/ko-service-mesh-cilium-service-mesh-02-traffic-management-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-cilium-service-mesh-02-traffic-management-0.html)

이 그림은 계층별 기능을 묶은 논리도이며 필수 패킷 처리 순서가 아닙니다. L3/L4만 필요한 트래픽은 Envoy를 거치지 않을 수 있고 실제 egress·ingress·Service 경로는 설정에 따라 달라집니다.

## CiliumEnvoyConfig

다음은 **서로 독립적인 설정 예시**이며 한꺼번에 설치하는 리소스 모음이 아닙니다. 여러 예시가 같은 프런트엔드 Service를 대상으로 하므로 Listener 충돌을 피하도록 하나의 설정 소유자를 선택하세요. 준비된 Cilium 설치에 `l7Proxy: true`, `envoyConfig.enabled: true`, 적절한 kube-proxy 대체·라우팅 설정과 CRD가 있어야 합니다.

이름으로 참조하는 프런트엔드·백엔드 Service는 `default`에 포트 **8080**, 올바른 selector와 준비된 HTTP 엔드포인트를 갖고 있어야 합니다. Kafka와 gRPC 절은 별도 네임스페이스·포트를 지정합니다. CEC 예시는 워크로드, Service나 인증서를 생성하지 않습니다.

`services`는 리다이렉트할 프런트엔드를 선택하고 백엔드를 동기화합니다. `backendServices`는 다른 Service의 프런트엔드를 리다이렉트하지 않고 백엔드만 동기화합니다. EDS Cluster 리소스는 여전히 필요합니다. 생략한 Listener 주소와 xDS 소스는 Cilium이 보완합니다. Kubernetes 수락만으로 충분하지 않으므로 Agent·Envoy 오류와 실제 요청을 확인하세요. 소유권과 검증 범위는 [아키텍처](./01-architecture.md)를 참고하세요.

### 기본 구조

CiliumEnvoyConfig는 특정 서비스에 대한 Envoy 설정을 정의합니다:

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: my-service-config
  namespace: default
spec:
  services:
  - name: my-service
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: backend-v1
    namespace: default
  - name: backend-v2
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: my-service-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: my-service-listener
          route_config:
            name: my-service-listener-routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                route:
                  weighted_clusters:
                    clusters:
                    - name: default/backend-v1
                      weight: 50
                    - name: default/backend-v2
                      weight: 50
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/backend-v1
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/backend-v2
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

이 완전한 예시는 명시된 두 백엔드로 요청을 분산합니다. Listener, HTTP 경로와 EDS Cluster는 별도 구성 요소이며, 백엔드 Service 목록만 작성해도 Cluster가 정의되는 것은 아닙니다.

### HTTP 라우팅

#### 경로 기반 라우팅

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: path-routing
  namespace: default
spec:
  services:
  - name: api-gateway
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: users-service
    namespace: default
  - name: orders-service
    namespace: default
  - name: products-service
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: api-gateway-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api-gateway
          codec_type: AUTO
          route_config:
            name: api_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  path_separated_prefix: /users
                route:
                  cluster: default/users-service
              - match:
                  path_separated_prefix: /orders
                route:
                  cluster: default/orders-service
              - match:
                  path_separated_prefix: /products
                route:
                  cluster: default/products-service
              - match:
                  prefix: /
                direct_response:
                  status: 404
                  body:
                    inline_string: Not Found
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/orders-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/products-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/users-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

Envoy는 이 경로들을 순서대로 평가합니다. `path_separated_prefix`는 `/users`와 `/users/123`에는 일치하지만 `/users-old`에는 일치하지 않습니다. 마지막 `/` 규칙이 기본 경로이며, 임의 문자열 prefix와 구분해야 합니다.

#### 헤더 기반 라우팅

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: header-routing
  namespace: default
spec:
  services:
  - name: api-service
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: api-v1
    namespace: default
  - name: api-v2
    namespace: default
  - name: api-beta
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: header-routing-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api-service
          route_config:
            name: header_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                  headers:
                  - name: X-API-Version
                    string_match:
                      exact: v2
                route:
                  cluster: default/api-v2
              - match:
                  prefix: /
                  headers:
                  - name: X-Beta-User
                    string_match:
                      exact: 'true'
                route:
                  cluster: default/api-beta
              - match:
                  prefix: /
                route:
                  cluster: default/api-v1
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-beta
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-v1
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-v2
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

먼저 일치한 규칙을 사용하므로 두 헤더를 모두 가진 요청은 v2를 선택합니다. 클라이언트가 보낸 버전·베타 헤더는 라우팅 힌트이며 해당 백엔드 접근 권한의 증거가 아닙니다.

#### 메서드 기반 라우팅

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: method-routing
  namespace: default
spec:
  services:
  - name: rest-api
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: read-service
    namespace: default
  - name: write-service
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: method-routing-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: rest-api
          route_config:
            name: method_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                  headers:
                  - name: :method
                    string_match:
                      safe_regex:
                        google_re2: {}
                        regex: ^(GET|HEAD)$
                route:
                  cluster: default/read-service
              - match:
                  prefix: /
                  headers:
                  - name: :method
                    string_match:
                      safe_regex:
                        google_re2: {}
                        regex: ^(POST|PUT|DELETE|PATCH)$
                route:
                  cluster: default/write-service
              - match:
                  prefix: /
                direct_response:
                  status: 405
                response_headers_to_add:
                - header:
                    key: allow
                    value: GET, HEAD, POST, PUT, DELETE, PATCH
                  append_action: OVERWRITE_IF_EXISTS_OR_ADD
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/read-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/write-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

GET/HEAD는 읽기 Service, POST/PUT/DELETE/PATCH는 쓰기 Service로 보냅니다. 다른 메서드는 405를 반환하므로 필요한 OPTIONS/CORS나 애플리케이션별 동작을 별도로 설계하세요. 쓰기를 전용 백엔드로 보내는 것만으로 인가·멱등성이 구현되지는 않습니다.

## L7 트래픽 정책

### CiliumNetworkPolicy L7 규칙

CiliumNetworkPolicy를 통해 L7 레벨의 세밀한 트래픽 제어가 가능합니다:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: l7-http-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:app: backend-api
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: default
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/api/users/.*$
        - method: ^GET$
          path: ^/api/products/.*$
        - method: ^POST$
          path: ^/api/orders$
        - method: ^GET$
          path: ^/api/admin/.*$
          headerMatches:
          - name: X-API-Version
            value: v1
```

규칙은 OR 관계이며 헤더 조건은 admin 경로 규칙에만 적용됩니다. `X-API-Version: v1`은 정확한 버전 조건이지 관리자 자격 증명이 아닙니다. 사용자 인증·인가는 애플리케이션에서 처리하세요. 명시한 네임스페이스의 ingress 트래픽을 선택하되 다른 적용 정책의 허용 규칙이 접근 범위를 넓힐 수 있습니다.

### 다양한 프로토콜 지원

#### Kafka: 네트워크 경계와 브로커 ACL

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: kafka-l4-policy
  namespace: kafka
spec:
  endpointSelector:
    matchLabels:
      k8s:app: kafka-broker
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: kafka-producer
        k8s:io.kubernetes.pod.namespace: kafka
    toPorts:
    - ports:
      - port: '9092'
        protocol: TCP
  - fromEndpoints:
    - matchLabels:
        k8s:app: kafka-consumer
        k8s:io.kubernetes.pod.namespace: kafka
    toPorts:
    - ports:
      - port: '9092'
        protocol: TCP
```

Cilium 1.20.1 L7 정책 API에는 HTTP와 DNS가 있고 기존 `rules.kafka` API는 없습니다. 해당 릴리스의 CRD는 이 Kafka 규칙 객체를 거부합니다. L7 규칙만 제거하면 토픽 권한 제어가 아니라 L4 허용만 남습니다. 대체 예시는 지정 클라이언트의 미리 구성된 브로커 TCP 9092 접근만 허용합니다. 토픽·컨슈머 그룹·작업 권한은 Kafka TLS/SASL과 브로커 ACL로 별도 구성하세요. 여기의 네트워크 정책은 produce와 fetch를 구분하지 못합니다.

#### DNS L7 정책

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: dns-l7-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:app: web-app
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
      rules:
        dns:
        - matchPattern: '*.example.com'
        - matchPattern: api.external-service.io
        - matchName: database.internal.svc.cluster.local
```

이 예시는 선택한 클러스터 resolver로 보내는 UDP·TCP **DNS 질의만** 허용합니다. 반환된 주소의 HTTPS·데이터베이스 연결을 허용하지 않으므로 필요한 목적지에 `toFQDNs`·엔드포인트와 포트 규칙을 따로 추가하세요. `*.example.com`에는 루트 `example.com`이나 임의 깊이의 하위 도메인이 포함되지 않습니다. Resolver 검색 목록에 따른 질의도 고려하고, NodeLocal DNS에는 별도로 검증한 목적지 규칙을 사용해야 합니다. 이름 제한만으로 데이터 유출·DoH·허용 도메인 악용을 방지한다고 보장할 수 없습니다.

#### gRPC L7 정책

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: grpc-l7-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:app: grpc-server
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: grpc-client
        k8s:io.kubernetes.pod.namespace: default
    toPorts:
    - ports:
      - port: '50051'
        protocol: TCP
      rules:
        http:
        - method: ^POST$
          path: ^/myapp\.UserService/GetUser$
        - method: ^POST$
          path: ^/myapp\.UserService/ListUsers$
        - method: ^POST$
          path: ^/myapp\.OrderService/.*$
```

이 HTTP/2 규칙은 gRPC의 `POST /package.Service/Method` 경로를 검사합니다. 패키지 이름의 점을 이스케이프하고 표현식의 경계를 고정했습니다. 지원되는 검사 가능한 HTTP/2 경로를 전제로 하며, 애플리케이션 암호화 트래픽에는 해당 TLS 설정이 필요합니다. Health/reflection 등 다른 메서드는 자동 허용되지 않고, HTTP 정책으로 protobuf 메시지 내부 필드를 인가할 수는 없습니다.

## 로드 밸런싱

### L4 로드 밸런싱 (eBPF)

eBPF 기반 L4 로드 밸런싱은 kube-proxy를 대체합니다:

```yaml
kubeProxyReplacement: true
k8sServiceHost: <reachable-api-server-host>
k8sServicePort: 6443
loadBalancer:
  algorithm: maglev
  mode: snat
nodePort:
  enableHealthCheck: true
```

API 엔드포인트는 bootstrap 중에도 접근할 수 있어야 하며 실제 포트를 사용하세요. EKS는 일반적으로 443입니다. 플랫폼별 IPAM·라우팅 설정도 유지해야 합니다. Chart 키는 `nodePort.enableHealthCheck`이며 기존 `loadBalancer.healthCheckNodePort`로는 설정되지 않았습니다. `loadBalancer.serviceTopology`는 topology-aware routing용이며 ClientIP 세션 어피니티가 아닙니다. DSR dispatch·라우팅 조합은 별도로 설계해야 하고, 문서화된 dispatch 선택지는 `opt`·`geneve`이며 `ipip`가 아닙니다. [아키텍처 설명](./01-architecture.md#kube-proxy-대체)을 참고하세요.

#### Maglev 해싱

Maglev는 해당 외부 트래픽의 흐름 키를 조회 테이블을 통해 백엔드에 매핑합니다. 백엔드 집합 변경 시 재할당을 줄이지만, 제거된 백엔드의 세션 유지나 `Service.spec.sessionAffinity: ClientIP`를 대체하지 않습니다.

Cilium 1.20.1 eBPF Maglev 테이블의 기본 크기는 **16,381**입니다. 지원 크기에는 **65,521**이 있으며, **65,537**은 아래의 별도 Envoy MAGLEV 예시 값으로 Cilium `maglev.tableSize` 지원값이 아닙니다. 노드 전체에서 설정이 일관되어야 합니다. 소켓 수준 east–west Service 변환에는 이 Maglev 경로가 적용되지 않습니다.

### L7 로드 밸런싱 (Envoy)

L7 로드 밸런싱은 Envoy를 통해 제공됩니다:

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: l7-load-balancing
  namespace: default
spec:
  services:
  - name: api-service
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: api-backend
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: l7-load-balancer
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: l7-load-balancer
          route_config:
            name: l7-load-balancer-routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                route:
                  cluster: default/api-backend
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-backend
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
    outlier_detection:
      consecutive_5xx: 5
      interval: 10s
      base_ejection_time: 30s
      max_ejection_percent: 50
    health_checks:
    - timeout: 5s
      interval: 10s
      unhealthy_threshold: 3
      healthy_threshold: 2
      http_health_check:
        path: /health
        expected_statuses:
        - start: 200
          end: 300
    circuit_breakers:
      thresholds:
      - priority: DEFAULT
        max_connections: 1000
        max_pending_requests: 1000
        max_requests: 1000
        max_retries: 3
```

능동 `/health` probe, 수동 outlier detection과 circuit breaker 용량 제한은 별개입니다. HTTP 상태 범위는 `[200, 300)`이므로 299도 포함합니다. 백엔드가 health 엔드포인트를 구현하고 정책이 probe 경로를 허용해야 합니다. Outlier ejection이 모든 요청의 실패 백엔드 회피를 보장하지는 않습니다. `circuit_breakers.thresholds`의 `max_retries`는 동시 재시도 리소스 제한이며 요청당 재시도 횟수가 아닙니다.

#### 로드 밸런싱 알고리즘 옵션

다음 Cluster 설정 조각 중 **하나만** 선택하세요. `lb_policy` 키를 반복한 하나의 YAML 매핑이 아니라 서로 다른 대안입니다. RING_HASH/MAGLEV에서 애플리케이션 키로 일관된 요청 분배를 하려면 적절한 경로 `hash_policy`도 필요합니다. 해시가 주어지지 않으면 임의 키로 선택할 수 있습니다. Envoy의 L7 MAGLEV 테이블과 Cilium eBPF Maglev 테이블은 별개입니다.

```yaml
lb_policy: ROUND_ROBIN
```

```yaml
lb_policy: LEAST_REQUEST
least_request_lb_config:
  choice_count: 2
```

```yaml
lb_policy: RANDOM
```

```yaml
lb_policy: RING_HASH
ring_hash_lb_config:
  hash_function: XX_HASH
  minimum_ring_size: 1024
  maximum_ring_size: 8388608
```

```yaml
lb_policy: MAGLEV
maglev_lb_config:
  table_size: 65537
```

## 트래픽 분할 (카나리 배포)

### 가중치 기반 트래픽 분할

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: canary-deployment
  namespace: default
spec:
  services:
  - name: frontend
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: frontend-stable
    namespace: default
  - name: frontend-canary
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: canary-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: frontend
          route_config:
            name: canary_routes
            virtual_hosts:
            - name: frontend
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                route:
                  weighted_clusters:
                    clusters:
                    - name: default/frontend-stable
                      weight: 90
                    - name: default/frontend-canary
                      weight: 10
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/frontend-canary
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/frontend-stable
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

90과 10은 상대적 선택 확률이며, 요청 10개마다 정확한 비율이나 사용자·세션 고정을 보장하지 않습니다. 현재 Envoy는 가중치 합계를 사용하므로 폐기된 `total_weight` 필드를 생략했습니다. 이는 트래픽 선택 설정일 뿐 자동 분석·승격·롤백 루프가 아닙니다.

### 헤더 기반 카나리

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: header-canary
  namespace: default
spec:
  services:
  - name: api
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: api-stable
    namespace: default
  - name: api-canary
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: header-canary-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api
          route_config:
            name: header_canary_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                  headers:
                  - name: X-Canary
                    string_match:
                      exact: 'true'
                route:
                  cluster: default/api-canary
              - match:
                  prefix: /
                route:
                  cluster: default/api-stable
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-canary
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-stable
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

정확히 `X-Canary: true`인 요청만 canary를 선택하며 다른 요청은 stable로 보냅니다. 인증된 경계가 제어하지 않는다면 이 헤더는 신뢰할 수 없습니다. Stable/canary의 애플리케이션 상태와 호환성도 롤아웃 계획에서 검토하세요.

## 재시도 및 타임아웃

### 재시도 설정

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: retry-config
  namespace: default
spec:
  services:
  - name: api-service
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: api-backend
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: retry-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api-service
          route_config:
            name: retry_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                  headers:
                  - name: :method
                    string_match:
                      exact: GET
                route:
                  cluster: default/api-backend
                  timeout: 7s
                  retry_policy:
                    retry_on: 5xx,reset,connect-failure
                    num_retries: 2
                    per_try_timeout: 2s
                    retry_back_off:
                      base_interval: 0.025s
                      max_interval: 0.25s
                    retriable_request_headers:
                    - name: :method
                      string_match:
                        exact: GET
              - match:
                  prefix: /
                route:
                  cluster: default/api-backend
                  timeout: 7s
                  retry_policy:
                    num_retries: 0
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
          early_header_mutation_extensions:
          - name: envoy.http.early_header_mutation.header_mutation
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.http.early_header_mutation.header_mutation.v3.HeaderMutation
              mutations:
              - remove: x-envoy-retry-on
              - remove: x-envoy-retry-grpc-on
              - remove: x-envoy-max-retries
              - remove: x-envoy-hedge-on-per-try-timeout
              - remove: x-envoy-retriable-header-names
              - remove: x-envoy-retriable-status-codes
              - remove: x-envoy-upstream-rq-timeout-ms
              - remove: x-envoy-upstream-rq-per-try-timeout-ms
              - remove: x-envoy-expected-rq-timeout-ms
              - remove: x-envoy-upstream-stream-duration-ms
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-backend
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

GET만 재시도하며 **최대 2회의 추가 시도**, 시도당 2초와 전체 경로 타임아웃 7초를 설정합니다. 시도당 타임아웃에는 첫 시도도 포함되며 재시도 사이의 대기 시간이 아닙니다. Backoff는 별도로 설정합니다. GET 이외의 기본 경로는 `num_retries: 0`을 명시합니다.

초기 헤더 변경 확장은 라우팅·타임아웃 계산 전에 Envoy 재시도·타임아웃 제어 헤더를 제거합니다. Cilium 1.20.1 프록시 이미지에는 이 확장이 포함되어 있지만 일반 HTTP `header_mutation`과 Lua 필터는 활성화되어 있지 않습니다. 기존 예시의 `previous_priorities` 재시도 우선순위 확장도 이 이미지에는 없습니다. 모든 upstream Envoy 확장을 사용할 수 있다고 가정하면 안 됩니다.

반복해도 안전한 GET을 구현한 HTTP 엔드포인트에 사용하세요. 애플리케이션·클라이언트나 다른 프록시는 독립적으로 재시도할 수 있습니다. 검토된 멱등성 메커니즘이 없다면 쓰기는 한 번만 시도하세요. `retriable_headers`는 **upstream 응답** 헤더이며 `retry_on: retriable-headers`와 함께 사용합니다. `retriable_request_headers`는 재시도할 요청을 제한하는 별도 필드입니다. `retriable-4xx`도 모든 4xx 응답 재시도를 뜻하지 않습니다.

### 타임아웃 설정

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: timeout-config
  namespace: default
spec:
  services:
  - name: slow-service
    namespace: default
    ports:
    - 8080
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: timeout-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: slow-service
          common_http_protocol_options:
            idle_timeout: 300s
            headers_with_underscores_action: REJECT_REQUEST
          stream_idle_timeout: 60s
          request_timeout: 0s
          route_config:
            name: timeout_routes
            virtual_hosts:
            - name: slow-service
              domains:
              - '*'
              routes:
              - match:
                  path_separated_prefix: /long-running
                route:
                  cluster: default/slow-service
                  timeout: 300s
                  idle_timeout: 300s
                  retry_policy:
                    num_retries: 0
              - match:
                  path_separated_prefix: /stream
                route:
                  cluster: default/slow-service
                  timeout: 0s
                  idle_timeout: 60s
                  retry_policy:
                    num_retries: 0
              - match:
                  prefix: /
                route:
                  cluster: default/slow-service
                  timeout: 60s
                  retry_policy:
                    num_retries: 0
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
          early_header_mutation_extensions:
          - name: envoy.http.early_header_mutation.header_mutation
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.http.early_header_mutation.header_mutation.v3.HeaderMutation
              mutations:
              - remove: x-envoy-retry-on
              - remove: x-envoy-retry-grpc-on
              - remove: x-envoy-max-retries
              - remove: x-envoy-hedge-on-per-try-timeout
              - remove: x-envoy-retriable-header-names
              - remove: x-envoy-retriable-status-codes
              - remove: x-envoy-upstream-rq-timeout-ms
              - remove: x-envoy-upstream-rq-per-try-timeout-ms
              - remove: x-envoy-expected-rq-timeout-ms
              - remove: x-envoy-upstream-stream-duration-ms
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/slow-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

구체적인 경로를 기본 경로보다 앞에 배치했습니다. `/long-running`에는 경로·스트림 idle 300초, `/stream`에는 전체 응답 타임아웃 비활성화와 idle 60초를 적용합니다. 다른 경로의 경로 타임아웃은 60초입니다. `/streaming`은 `/stream`에 일치하지 않습니다.

Upstream Cluster의 `connect_timeout`은 연결 수립 제한이고, `common_http_protocol_options.idle_timeout`은 downstream 연결의 유휴 제한입니다. HCM `request_timeout`은 백엔드 처리가 아니라 클라이언트 요청 수신 시간이며 스트리밍 요청을 위해 여기서는 비활성화합니다. 노출된 서비스에는 그에 맞는 edge·헤더·본문·연결 제한이 필요합니다. Stream idle 제한, 클라이언트 deadline, 인프라 제한과 연결 손실은 여전히 스트림을 종료할 수 있습니다. `timeout: 0s`는 무제한 연결을 보장하지 않습니다.

## Rate Limiting

### 로컬 Rate Limiting

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: local-ratelimit
  namespace: default
spec:
  services:
  - name: api-service
    namespace: default
    ports:
    - 8080
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: ratelimit-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api-service
          route_config:
            name: ratelimit_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                route:
                  cluster: default/api-service
          http_filters:
          - name: envoy.filters.http.local_ratelimit
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
              stat_prefix: http_local_rate_limiter
              token_bucket:
                max_tokens: 1000
                tokens_per_fill: 100
                fill_interval: 1s
              status:
                code: TooManyRequests
              filter_enabled:
                default_value:
                  numerator: 100
                  denominator: HUNDRED
              filter_enforced:
                default_value:
                  numerator: 100
                  denominator: HUNDRED
              enable_x_ratelimit_headers: DRAFT_VERSION_03
              local_rate_limit_per_downstream_connection: false
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

이 버킷은 **Envoy 프로세스별로** burst 1,000개와 초당 100개 토큰 보충을 제공하며 해당 프로세스 worker가 공유합니다. 클러스터 전체 쿼터가 아닙니다. 활성화·강제 적용 비율을 모두 명시했습니다. `enable_x_ratelimit_headers: DRAFT_VERSION_03`으로 필터의 실제 limit·remaining·reset 헤더를 사용하며, 임의의 dynamic-metadata 키로 정확한 잔여 토큰 수를 얻을 수 있다고 가정하지 않습니다.

### 경로별 Rate Limiting

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: per-route-ratelimit
  namespace: default
spec:
  services:
  - name: api-service
    namespace: default
    ports:
    - 8080
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: per-route-ratelimit-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api-service
          route_config:
            name: ratelimit_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  path_separated_prefix: /auth
                route:
                  cluster: default/api-service
                typed_per_filter_config:
                  envoy.filters.http.local_ratelimit:
                    '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
                    stat_prefix: auth_rate_limiter
                    token_bucket:
                      max_tokens: 10
                      tokens_per_fill: 5
                      fill_interval: 60s
                    filter_enabled:
                      default_value:
                        numerator: 100
                        denominator: HUNDRED
                    filter_enforced:
                      default_value:
                        numerator: 100
                        denominator: HUNDRED
                    local_rate_limit_per_downstream_connection: false
                    enable_x_ratelimit_headers: DRAFT_VERSION_03
              - match:
                  path_separated_prefix: /search
                route:
                  cluster: default/api-service
                typed_per_filter_config:
                  envoy.filters.http.local_ratelimit:
                    '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
                    stat_prefix: search_rate_limiter
                    token_bucket:
                      max_tokens: 100
                      tokens_per_fill: 50
                      fill_interval: 1s
                    filter_enabled:
                      default_value:
                        numerator: 100
                        denominator: HUNDRED
                    filter_enforced:
                      default_value:
                        numerator: 100
                        denominator: HUNDRED
                    local_rate_limit_per_downstream_connection: false
                    enable_x_ratelimit_headers: DRAFT_VERSION_03
              - match:
                  prefix: /
                route:
                  cluster: default/api-service
                typed_per_filter_config:
                  envoy.filters.http.local_ratelimit:
                    '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
                    stat_prefix: default_rate_limiter
                    token_bucket:
                      max_tokens: 1000
                      tokens_per_fill: 100
                      fill_interval: 1s
                    filter_enabled:
                      default_value:
                        numerator: 100
                        denominator: HUNDRED
                    filter_enforced:
                      default_value:
                        numerator: 100
                        denominator: HUNDRED
                    local_rate_limit_per_downstream_connection: false
                    enable_x_ratelimit_headers: DRAFT_VERSION_03
          http_filters:
          - name: envoy.filters.http.local_ratelimit
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
              stat_prefix: http_local_rate_limiter
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

경로마다 활성화·강제 적용 비율까지 포함한 완전한 로컬 rate-limit 오버라이드를 제공합니다. Auth는 burst 10개와 60초당 5개 보충, search는 burst 100개와 초당 50개 보충, 기본 경로는 burst 1,000개와 초당 100개 보충입니다. 사용자별 제한이 아니라 프로세스별 버킷입니다. Enabled/enforced 비율이 없으면 실질적인 제한이 기본적으로 적용되지 않습니다.

## URL 재작성 및 헤더 조작

### URL 재작성

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: url-rewrite
  namespace: default
spec:
  services:
  - name: api-gateway
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: users-service
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: rewrite-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api-gateway
          route_config:
            name: rewrite_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  path_separated_prefix: /api/v1/users
                route:
                  cluster: default/users-service
                  prefix_rewrite: /users
              - match:
                  safe_regex:
                    google_re2: {}
                    regex: ^/v([0-9]+)/(.*)$
                route:
                  cluster: default/users-service
                  regex_rewrite:
                    pattern:
                      google_re2: {}
                      regex: ^/v([0-9]+)/([^?]*)(\?.*)?$
                    substitution: /api/v\1/\2\3
              - match:
                  path: /legacy
                route:
                  cluster: default/users-service
                  host_rewrite_literal: legacy.internal.svc.cluster.local
                  prefix_rewrite: /
              - match:
                  prefix: /legacy/
                route:
                  cluster: default/users-service
                  host_rewrite_literal: legacy.internal.svc.cluster.local
                  prefix_rewrite: /
              - match:
                  prefix: /
                direct_response:
                  status: 404
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/users-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

`/api/v1/users/123`은 `/users/123`으로, `/v2/users?active=1`은 기존 쿼리를 유지한 `/api/v2/users?active=1`로 바뀝니다. Legacy 루트와 하위 경로를 따로 매칭해 이중 슬래시를 피합니다. Host rewrite는 선택한 Cluster에 보내는 HTTP authority를 변경하며, 다른 백엔드 Service를 자동으로 조회하는 기능이 아닙니다.

### 헤더 조작

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: header-manipulation
  namespace: default
spec:
  services:
  - name: api-service
    namespace: default
    ports:
    - 8080
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: header-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api-service
          route_config:
            name: header_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              request_headers_to_add:
              - header:
                  key: X-Forwarded-By
                  value: cilium-envoy
                append_action: OVERWRITE_IF_EXISTS_OR_ADD
              response_headers_to_add:
              - header:
                  key: X-Served-By
                  value: cilium-service-mesh
                append_action: OVERWRITE_IF_EXISTS_OR_ADD
              response_headers_to_remove:
              - server
              - x-powered-by
              routes:
              - match:
                  prefix: /
                route:
                  cluster: default/api-service
                request_headers_to_add:
                - header:
                    key: X-Request-Start
                    value: '%START_TIME(%s.%3f)%'
                  append_action: OVERWRITE_IF_EXISTS_OR_ADD
                - header:
                    key: X-Envoy-Original-Path
                    value: '%REQ(:PATH)%'
                  append_action: OVERWRITE_IF_EXISTS_OR_ADD
                response_headers_to_add:
                - header:
                    key: X-Response-Time
                    value: '%RESPONSE_DURATION%ms'
                  append_action: OVERWRITE_IF_EXISTS_OR_ADD
                - header:
                    key: X-Upstream-Host
                    value: '%UPSTREAM_HOST%'
                  append_action: OVERWRITE_IF_EXISTS_OR_ADD
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

경로별 헤더 변경은 `RouteAction` 내부가 아니라 `route` 액션과 같은 레벨에 둡니다. 응답 시간 formatter는 응답 헤더 생성 시 평가하므로 아직 전송하지 않은 본문의 완료 시간을 보고할 수 없습니다. Upstream-host 진단값은 내부 라우팅 정보를 노출하므로 이러한 헤더는 적절한 테스트·내부 인터페이스에서 사용하세요.

## Gateway API 통합

### GatewayClass 및 Gateway

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: cilium
spec:
  controllerName: io.cilium/gateway-controller
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: api-gateway
  namespace: default
spec:
  gatewayClassName: cilium
  listeners:
  - name: http
    protocol: HTTP
    port: 80
    allowedRoutes:
      namespaces:
        from: Same
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: api-gateway-tls
    allowedRoutes:
      namespaces:
        from: Same
```

Gateway API 1.6.1 CRD와 Cilium의 `gatewayAPI.enabled: true`, `kubeProxyReplacement: true`, `l7Proxy: true`가 필요합니다. GatewayClass는 컨트롤러 연결을 설명합니다. 설치 도구가 이미 `cilium`을 소유한다면 별도 소유자를 만들지 말고 재사용하세요. `default`에 호스트 이름에 맞는 인증서가 담긴 유효한 TLS Secret `api-gateway-tls`를 준비해야 합니다. LoadBalancer 노출·주소 할당은 플랫폼별로 다릅니다. GatewayClass/Gateway의 Accepted·Programmed 조건과 Listener 참조를 확인하세요. 이 매니페스트가 완전한 EKS 노출 구성을 제공하지는 않습니다.

### HTTPRoute

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api-routes
  namespace: default
spec:
  parentRefs:
  - name: api-gateway
    namespace: default
    sectionName: https
  hostnames:
  - api.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /users
    backendRefs:
    - name: users-service
      port: 8080
  - matches:
    - path:
        type: PathPrefix
        value: /orders
    backendRefs:
    - name: orders-service
      port: 8080
  - matches:
    - path:
        type: PathPrefix
        value: /
      headers:
      - name: X-API-Version
        value: v2
    backendRefs:
    - name: api-v2
      port: 8080
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    - name: api-stable
      port: 8080
      weight: 90
    - name: api-canary
      port: 8080
      weight: 10
```

이 경로는 `https` Listener에만 연결합니다. 외부 Listener 포트 80/443과 백엔드 Service 포트 8080은 별개입니다. HTTP Listener가 자동 HTTPS 리다이렉트가 되는 것은 아니므로 필요하면 별도 HTTP 경로를 구성하세요. Gateway API는 경로 구체성·헤더 조건 등의 명세상 우선순위를 사용하며, 모든 규칙을 단순 YAML 순서대로 평가한다고 가정하면 안 됩니다. Accepted·ResolvedRefs와 실제 Listener 상태를 확인하세요.

### HTTPRoute 고급 기능

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: advanced-routes
  namespace: default
spec:
  parentRefs:
  - name: api-gateway
    sectionName: https
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    filters:
    - type: RequestHeaderModifier
      requestHeaderModifier:
        set:
        - name: X-Doc-Route
          value: api-v1
        remove:
        - X-Internal-Header
    - type: ResponseHeaderModifier
      responseHeaderModifier:
        add:
        - name: X-Frame-Options
          value: DENY
        - name: X-Content-Type-Options
          value: nosniff
    - type: URLRewrite
      urlRewrite:
        path:
          type: ReplacePrefixMatch
          replacePrefixMatch: /v1
    backendRefs:
    - name: api-service
      port: 8080
  - matches:
    - path:
        type: Exact
        value: /old-endpoint
      method: GET
    filters:
    - type: RequestRedirect
      requestRedirect:
        scheme: https
        hostname: new.example.com
        path:
          type: ReplaceFullPath
          replaceFullPath: /new-endpoint
        statusCode: 301
  hostnames:
  - api.example.com
```

여기의 헤더 값은 이식 가능한 Gateway API의 리터럴 설정입니다. API는 Envoy `%REQ(...)%` 템플릿 확장을 정의하지 않습니다. 요청 ID는 적절한 애플리케이션·프록시 계층에서 유지하거나 생성하세요. 실제 전송 방식과 무관하게 `X-Forwarded-Proto: https`를 강제하면 안 됩니다. URLRewrite는 클라이언트 리다이렉트 없이 upstream 경로를 바꿉니다. Legacy 리다이렉트는 GET에만 적용합니다. 301은 클라이언트에서 메서드를 바꿀 수 있으므로 임의의 쓰기를 그대로 리다이렉트하면 안 됩니다.

## 트래픽 미러링

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: traffic-mirror
  namespace: default
spec:
  services:
  - name: production-service
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: production-backend
    namespace: default
  - name: shadow-backend
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: mirror-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: production-service
          route_config:
            name: mirror_routes
            virtual_hosts:
            - name: production
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                  headers:
                  - name: :method
                    string_match:
                      safe_regex:
                        google_re2: {}
                        regex: ^(GET|HEAD)$
                route:
                  cluster: default/production-backend
                  request_mirror_policies:
                  - cluster: default/shadow-backend
                    runtime_fraction:
                      default_value:
                        numerator: 100
                        denominator: HUNDRED
                    trace_sampled: false
              - match:
                  prefix: /
                route:
                  cluster: default/production-backend
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/production-backend
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/shadow-backend
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

미러는 **선택한 GET/HEAD 요청의 100%**를 받고, 다른 메서드의 기본 경로에는 미러 정책이 없습니다. 합성 또는 승인된 읽기 전용 트래픽으로 시험하고, shadow 백엔드가 프로덕션 상태를 변경하거나 외부 부수 효과를 만들지 못하도록 격리하세요. 미러링은 리소스를 소비하고 요청 데이터를 복사하며, 별도 설정이 없으면 authority에 `-shadow`를 붙일 수 있습니다. 미러 응답을 호출자에게 반환하지 않는다는 사실이 사용자 영향 0을 보장하지는 않습니다.

## 다음 단계

- [보안](./03-security.md): 인증·암호화와 L7 네트워크 정책 검토
- [관측성](./04-observability.md): Hubble을 통한 트래픽 모니터링
- [인그레스 & 게이트웨이](./05-ingress-gateway.md): 외부 트래픽 관리

## 참고 자료

- [Cilium 1.20.1 L7 policy](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/policy/layer7.rst)
- [Cilium L3/FQDN policy](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/policy/layer3.rst)
- [Cilium CEC example](https://github.com/cilium/cilium/blob/v1.20.1/examples/kubernetes/servicemesh/envoy/envoy-traffic-management-test.yaml)
- [Cilium Envoy parser](https://github.com/cilium/cilium/blob/v1.20.1/pkg/ciliumenvoyconfig/cec_resource_parser.go)
- [Cilium kube-proxy replacement](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/kubernetes/kubeproxy-free.rst)
- [Cilium Gateway API installation](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/gateway-api/installation.rst)
- [Cilium 1.20.1 chart values](https://github.com/cilium/cilium/blob/v1.20.1/install/kubernetes/cilium/values.yaml)
- [Cilium proxy image extension list](https://github.com/cilium/proxy/blob/766ccfb37260a43e9d228837aa84ce3faf9f64e7/envoy_build_config/extensions_build_config.bzl)
- [Envoy 1.37.5 routing API](https://github.com/envoyproxy/envoy/blob/v1.37.5/api/envoy/config/route/v3/route_components.proto)
- [Envoy retry implementation](https://github.com/envoyproxy/envoy/blob/v1.37.5/source/common/router/retry_state_impl.cc)
- [Envoy router timing and header processing](https://github.com/envoyproxy/envoy/blob/v1.37.5/source/common/router/router.cc)
- [Envoy early header mutation](https://github.com/envoyproxy/envoy/blob/v1.37.5/api/envoy/extensions/http/early_header_mutation/header_mutation/v3/header_mutation.proto)
- [Envoy local rate limiting](https://github.com/envoyproxy/envoy/blob/v1.37.5/api/envoy/extensions/filters/http/local_ratelimit/v3/local_rate_limit.proto)
- [Envoy timeout definitions](https://github.com/envoyproxy/envoy/blob/v1.37.5/docs/root/faq/configuration/timeouts.rst)
- [Gateway API 1.6.1 HTTPRoute specification](https://github.com/kubernetes-sigs/gateway-api/blob/v1.6.1/apis/v1/httproute_types.go)
- [Kafka broker ACLs](https://kafka.apache.org/41/security/authorization-and-acls/)

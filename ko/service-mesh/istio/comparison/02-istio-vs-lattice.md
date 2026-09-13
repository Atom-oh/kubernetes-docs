# Istio vs VPC Lattice

> **마지막 검토**: 2026년 9월 11일
> **Istio API 기준**: 1.31.0; Kubernetes 호환성은 별도 확인 필요

앱의 통신, identity, protocol과 운영 요구사항을 비교합니다. Istio와 VPC Lattice는 배포·보안 경계가 다르며 기능 별점이나 근거 없는 “overhead 0” 주장으로 적합한 구조를 결정할 수 없습니다.

설정 예제는 권한이 있는 기존 resource와 실제 앱 endpoint를 가정합니다. 적절한 환경에서 사용하는 대안이며 하나로 결합한 운영 배포가 아닙니다. Identifier, role, namespace와 IdP URL을 의도한 값으로 바꿔야 합니다. 이번 감사는 로컬 설정/input 형식과 계산을 검증했으며 AWS·cluster resource를 배포하지 않았습니다.

## 목차

1. [아키텍처와 플랫폼](#아키텍처와-플랫폼)
2. [트래픽 관리](#트래픽-관리)
3. [보안과 Identity](#보안과-identity)
4. [관측성](#관측성)
5. [설치와 운영](#설치와-운영)
6. [비용과 과거 근거](#비용과-과거-근거)
7. [Hybrid와 Multicloud](#hybrid와-multicloud)
8. [선택 기준](#선택-기준)

## 아키텍처와 플랫폼

### Istio

Istio는 Kubernetes와 문서화된 VM 통합에 사용하는 control/data plane입니다. Sidecar mode는 등록한 workload Pod의 Envoy를, ambient는 노드별 ztunnel과 지원되는 L7 처리용 waypoint를 사용합니다. Sidecar는 앱 Pod가 아닌 **container**를 추가합니다.

![Sidecar mode의 개념도입니다. Istiod가 Envoy를 설정하고 proxy가 mesh 트래픽을 전달하며 구성된 관측 backend가 telemetry를 수집·조회합니다.](../../../.gitbook/assets/ko-service-mesh-istio-comparison-02-istio-vs-lattice-0.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-comparison-02-istio-vs-lattice-0.html)

그림은 sidecar mode를 설명합니다. Resource 표시는 과거 예시 추정값이며 실측 default나 현재 용량 권고가 아닙니다. Kiali는 telemetry/backend를 조회하며 trace collector 자체가 아닙니다.

Ambient capture는 문서화된 Linux network namespace/iptables를 사용하며 eBPF capture 계층이 아닙니다. 핵심 ambient는 1.24에서 GA가 되었지만 개별 기능·multicluster 토폴로지는 상태가 다릅니다. Sidecar 제거, workload 등록과 waypoint 통과 강제는 별도 작업입니다. Namespace label 하나로 모든 workload를 안전하게 migration하거나 97–98% 절감을 보장할 수 없습니다.

### VPC Lattice

VPC Lattice는 **service와 resource**를 위한 AWS 관리형 application networking입니다. Service 모델은 지원되는 IP/instance, Lambda, ALB target용 listener·rule·target group을 포함하며 ECS/EKS 통합이 해당 target을 관리합니다. Resource configuration/resource gateway는 TCP 연결 등을 위한 별도 private resource-access 모델입니다.

Service network는 논리적인 연결·접근 경계이며 sidecar나 Pod identity가 아닙니다. Client는 service-network VPC association 또는 service-network VPC endpoint를 사용할 수 있습니다. Endpoint 경로는 PrivateLink 기반이지만 모든 Lattice data path나 data plane 전체를 “AWS PrivateLink”로만 설명하면 부정확합니다.

VPC association과 endpoint association은 주소·연결 동작이 다릅니다. Service-network endpoint는 peering, Transit Gateway, Direct Connect, VPN을 통해 들어오는 지원 트래픽을 받을 수 있어 AWS 밖의 client도 접근할 수 있습니다. AWS service 자체는 AWS에서 운영되며 다른 cloud에 Lattice를 배포하는 것은 아닙니다.

| 항목 | Istio | VPC Lattice |
|---|---|---|
| Data plane | Sidecar 또는 ambient component와 선택한 gateway | 관리형 service/resource networking과 구성된 target/endpoint |
| Identity | Workload mesh identity와 앱/JWT 정책 | 활성화한 service IAM/SigV4 인가; resource 접근은 별도 제어 |
| 운영 | Control/proxy lifecycle, certificate, 용량, policy와 telemetry | AWS가 service 운영; 사용자는 IAM, DNS, association, target, controller, quota와 앱 관리 |
| 플랫폼 | 지원 Kubernetes/VM 배포와 mode별 요구사항 | 지원 AWS target type과 문서화된 client/network 경로 |
| 비용 | 실제 infrastructure, telemetry, support와 엔지니어링 | 해당 service/resource/traffic 비용과 앱 infrastructure, log·엔지니어링 |

“필수 sidecar가 없음”은 배포 특성이며 latency, CPU, signer/controller 작업이나 전체 인프라 비용이 0이라는 증명이 아닙니다.

## 트래픽 관리

### 가중치·조건 Routing

Istio는 HTTP 요청 속성을 일치시켜 label subset으로 routing할 수 있습니다. `mesh-demo`에 backend Service와 v1/v2 workload가 준비되어야 합니다.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: backend-canary
  namespace: mesh-demo
spec:
  hosts:
  - backend
  http:
  - match:
    - headers:
        x-release:
          exact: canary
    route:
    - destination:
        host: backend
        port:
          number: 8080
        subset: v2
      weight: 100
    retries:
      attempts: 0
  - route:
    - destination:
        host: backend
        port:
          number: 8080
        subset: v1
      weight: 90
    - destination:
        host: backend
        port:
          number: 8080
        subset: v2
      weight: 10
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: backend
  namespace: mesh-demo
spec:
  host: backend
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 60s
      maxEjectionPercent: 50
      minHealthPercent: 50
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

Route는 mesh retry를 명시적으로 비활성화합니다. Resource 제한값은 예시이며 `maxRequestsPerConnection: 2`는 재사용을 의도적으로 제한하므로 보편적인 성능 권고가 아닙니다. Outlier detection은 proxy가 upstream endpoint에 대해 판단합니다. minHealthPercent는 panic/fail-open 임계값이며 그 비율만큼 반드시 정상 endpoint가 남는다는 보장이 아닙니다.

Lattice HTTP/HTTPS listener rule은 method, header, path matching을 지원합니다. 다음 전체 **CreateRule input**은 누락된 service/name과 잘못된 pathMatch 예제를 바로잡습니다.

```json
{
  "serviceIdentifier": "svc-0123456789abcdef0",
  "listenerIdentifier": "listener-0123456789abcdef0",
  "name": "api-canary",
  "priority": 10,
  "match": {
    "httpMatch": {
      "method": "GET",
      "pathMatch": {
        "caseSensitive": true,
        "match": {
          "prefix": "/api/v1/"
        }
      }
    }
  },
  "action": {
    "forward": {
      "targetGroups": [
        {
          "targetGroupIdentifier": "tg-0123456789abcdef0",
          "weight": 90
        },
        {
          "targetGroupIdentifier": "tg-0123456789abcdef1",
          "weight": 10
        }
      ]
    }
  }
}
```

rule.json으로 저장하고 기존 service/listener 및 eligible target group 두 개의 실제 ID로 바꿉니다. 생성 전에 name·priority가 사용 중이 아닌지 확인하세요.

```bash
AWS_REGION=us-east-1
aws vpc-lattice create-rule --region "$AWS_REGION" --cli-input-json file://rule.json
```

작은 priority 숫자가 먼저 평가됩니다. pathMatch.match.prefix의 중첩 형식이 필요합니다. 이 rule은 `/api/v1/` 아래 GET을 선택하며 모든 Istio match의 동등한 구현이나 인증 정책은 아닙니다. Weight는 version을 배포·확장하지 않습니다. 같은 rule/target을 AWS controller와 CLI 예제가 경쟁해서 관리하지 않도록 하세요.

Lattice는 round-robin target 선택을 문서화하며 target group 사이 weight와는 별개입니다. 이 API에는 기존 문서가 주장한 “least connections” 선택 항목이 없습니다.

### Mirroring과 Fault

격리된 read-only mirror 실험에는 대안 VirtualService를 사용합니다.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: backend-mirror
  namespace: mesh-demo
spec:
  hosts:
  - backend
  http:
  - match:
    - method:
        exact: GET
      uri:
        prefix: /api/v1/
    route:
    - destination:
        host: backend
        port:
          number: 8080
        subset: v1
      weight: 100
    mirror:
      host: backend
      port:
        number: 8080
      subset: v2
    mirrorPercentage:
      value: 10
    retries:
      attempts: 0
  - route:
    - destination:
        host: backend
        port:
          number: 8080
        subset: v1
      weight: 100
    retries:
      attempts: 0
```

일치하는 GET만 mirror하며 다른 요청은 mirror 없이 v1으로 갑니다. Shadow 응답은 주 client 응답이 아니지만 실제로 read-only가 아닌 endpoint라면 중복 요청에 부작용이 생길 수 있습니다. Destination version과 용량이 있어야 합니다.

격리된 fault 실험에는 명시적인 요청 marker를 사용할 수 있습니다.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: backend-fault-lab
  namespace: mesh-demo
spec:
  hosts:
  - backend
  http:
  - match:
    - method:
        exact: GET
      headers:
        x-fault-lab:
          exact: enabled
    fault:
      delay:
        percentage:
          value: 10
        fixedDelay: 5s
      abort:
        percentage:
          value: 5
        httpStatus: 503
    route:
    - destination:
        host: backend
        port:
          number: 8080
        subset: v1
      weight: 100
  - route:
    - destination:
        host: backend
        port:
          number: 8080
        subset: v1
      weight: 100
    retries:
      attempts: 0
```

Marker는 인가가 아니므로 test workload와 caller 범위를 제한해야 합니다. 같은 route의 fault injection과 retry/timeout 동작을 서로 바꿔 해석하지 마세요. 어느 proxy가 오류를 만드는지 확인하고 raw 결과와 retry 후 결과를 분리해 측정합니다.

검증한 Lattice RuleAction API는 forwarding 또는 fixed response를 제공하며 Istio와 동등한 mirror·백분율 delay/abort action은 없습니다. Fixed response rule이 백분율 fault injection은 아닙니다. 앱/proxy 시험 방법이나 지원되는 AWS FIS action에는 별도 설계가 필요합니다. Lambda@Edge는 CloudFront event에서 실행되므로 “ALB + Lambda@Edge”는 내장 mirror 기능이 아닙니다.

### Health Check와 실패 동작

다음 **CreateTargetGroup input**은 지정한 VPC의 기존 non-meshed HTTP backend와 실제 `/health` endpoint를 가정합니다. 보안 예제의 STRICT Istio backend와 같은 대상이 아닙니다.

```json
{
  "name": "backend-v1",
  "type": "IP",
  "config": {
    "port": 8080,
    "protocol": "HTTP",
    "protocolVersion": "HTTP1",
    "vpcIdentifier": "vpc-0123456789abcdef0",
    "ipAddressType": "IPV4",
    "healthCheck": {
      "enabled": true,
      "protocol": "HTTP",
      "protocolVersion": "HTTP1",
      "port": 8080,
      "path": "/health",
      "healthCheckIntervalSeconds": 30,
      "healthCheckTimeoutSeconds": 5,
      "healthyThresholdCount": 2,
      "unhealthyThresholdCount": 3,
      "matcher": {
        "httpCode": "200"
      }
    }
  }
}
```

```bash
aws vpc-lattice create-target-group --region "$AWS_REGION"   --cli-input-json file://target-group.json
```

파일에는 실제 값으로 바꾼 전체 input이 있어야 합니다. Health check는 config 안에 있으며 healthCheckIntervalSeconds·healthCheckTimeoutSeconds 필드를 사용합니다. 이 operation에는 최상위 --health-check가 없습니다. 생성 후 실제 지원 target을 등록하세요. EKS Pod IP lifecycle은 일반적으로 수동 고정 IP 대신 적절한 AWS Gateway API Controller가 관리해야 합니다.

Lattice는 정상 target을 자동 사용하지만 group의 모든 target이 비정상이면 **fail open**하여 트래픽을 보냅니다. 수동 제거만 기다리는 동작이 아니며 health check가 앱 자체를 수리하지도 않습니다. Istio의 proxy별 connection-pool/outlier 제어와는 다른 메커니즘입니다.

Service idleTimeoutSeconds는 60–600초로 설정할 수 있으며 per-route request timeout이나 retry budget과는 다릅니다. 일반적인 승자를 정하지 말고 선택한 HTTP, gRPC, TLS 경로의 connection/request 제한과 실패 동작을 검증하세요.

## 보안과 Identity

### Istio: 필요한 조건을 함께 요구

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: backend-strict
  namespace: mesh-demo
spec:
  selector:
    matchLabels:
      app: backend
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: backend-jwt
  namespace: mesh-demo
spec:
  selector:
    matchLabels:
      app: backend
  jwtRules:
  - issuer: https://issuer.example.com
    jwksUri: https://issuer.example.com/.well-known/jwks.json
    audiences:
    - api.example.com
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-access
  namespace: mesh-demo
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/mesh-demo/sa/frontend
        requestPrincipals:
        - https://issuer.example.com/*
    to:
    - operation:
        methods:
        - GET
        - POST
        paths:
        - /api/v1/*
        ports:
        - '8080'
    when:
    - key: request.auth.claims[role]
      values:
      - admin
```

Issuer/JWKS/audience는 명시적 IdP placeholder이며 caller에는 실제 frontend ServiceAccount identity가 필요합니다. **같은 ALLOW rule**에서 mesh principal, 해당 issuer의 JWT principal, method/path/port와 admin claim을 함께 요구합니다. ALLOW policy를 나누면 OR로 평가되어 둘 다 요구하지 못합니다. RequestAuthentication만으로 JWT가 필수가 되지 않으며 raw user-role header도 인증된 identity가 아닙니다. 같은 workload에 다른 ALLOW policy가 별도 권한을 주는지도 검토해야 합니다.

Certificate rotation은 issuer lifetime과 proxy/CA 설정에 따르며 보편적인 15분 갱신 주기는 없습니다. External CA는 실제 지원되는 issuer 경로로 통합해야 합니다. Port-level mTLS는 workload port 기준이고 mode별 지원도 다릅니다. 주 앱 port 8080을 plaintext “metrics 예외”로 두면 이 보안 조건을 깨뜨릴 수 있습니다.

### Lattice: TLS 경계와 Service 인가

다음 **CreateListener input**은 준비된 기존 service와 target group에 HTTPS 종료점을 만듭니다.

```json
{
  "serviceIdentifier": "svc-0123456789abcdef0",
  "name": "https-main",
  "protocol": "HTTPS",
  "port": 443,
  "defaultAction": {
    "forward": {
      "targetGroups": [
        {
          "targetGroupIdentifier": "tg-0123456789abcdef0",
          "weight": 100
        }
      ]
    }
  }
}
```

```bash
aws vpc-lattice create-listener --region "$AWS_REGION" --cli-input-json file://listener.json
```

생성된 service DNS 이름에는 AWS 관리 certificate를 사용하며 custom domain에는 문서화된 certificate/domain 설정이 필요합니다. Frontend HTTPS가 backend HTTPS나 Istio SPIFFE mTLS를 뜻하지는 않습니다. Target-group protocol은 별도 선택입니다. Lattice가 target에 HTTPS 연결을 만들 때는 문서상 **target certificate를 검증하지 않으므로** 앱 계층의 peer-certificate 인증으로 설명하면 안 됩니다.

TLS_PASSTHROUGH는 Lattice에서 종료하지 않고 앱 자체 TLS/mTLS를 전달할 수 있습니다. Custom-domain/SNI와 TCP target 설정이 필요하고 default forwarding rule만 허용하며 연결은 10분으로 제한됩니다. Auth policy는 anonymous principal만 지원하며 Lambda target은 지원하지 않습니다. 암호화된 stream에 HTTP IAM/header policy 검사를 수행하지는 않습니다.

### 올바른 IAM Auth Policy

vpc-lattice-svcs:Invoke, service ARN+path와 명시적인 role을 사용합니다. Service/network auth policy 예제입니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/LatticeClient"
      },
      "Action": "vpc-lattice-svcs:Invoke",
      "Resource": "arn:aws:vpc-lattice:us-east-1:123456789012:service/svc-0123456789abcdef0/api/v1/*",
      "Condition": {
        "StringEquals": {
          "vpc-lattice-svcs:RequestMethod": [
            "GET",
            "POST"
          ]
        }
      }
    }
  ]
}
```

실제 ARN으로 바꾼 auth policy를 auth-policy.json에 저장합니다. Caller role에는 대응하는 identity-based 권한도 별도로 필요합니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "vpc-lattice-svcs:Invoke",
      "Resource": "arn:aws:vpc-lattice:us-east-1:123456789012:service/svc-0123456789abcdef0/api/v1/*",
      "Condition": {
        "StringEquals": {
          "vpc-lattice-svcs:RequestMethod": [
            "GET",
            "POST"
          ]
        }
      }
    }
  ]
}
```

예시 ARN을 바꾸고 활성화한 모든 service-network·service auth policy가 요청을 허용하는지 확인합니다. 어떤 policy의 explicit deny도 우선합니다. AWS_IAM은 평가를 활성화하며 authType NONE일 때 붙인 policy는 inactive입니다. Wildcard Principal과 SourceVpc만으로 anonymous traffic을 허용할 수 있으므로 IAM 인증의 증명이 아닙니다.

Operation은 **PutAuthPolicy**입니다. Newline 없는 compact policy string을 전체 CLI input 안에 넣습니다.

```bash
: "${SERVICE_ID:?Set the actual service ID}"
jq -n --arg resource "$SERVICE_ID" --slurpfile policy auth-policy.json   '{resourceIdentifier:$resource, policy:($policy[0] | tojson)}' > put-auth-policy.json
aws vpc-lattice put-auth-policy --region "$AWS_REGION"   --cli-input-json file://put-auth-policy.json
```

존재하지 않는 create-auth-policy/allowedPrincipals 문법을 대체합니다. 설정을 적용하는 management role과 service를 호출하는 workload role은 다릅니다. 앱 또는 지원되는 signer가 실제 요청을 workload credential로 SigV4 서명해야 하며 TLS 설정만으로 서명이 만들어지지 않습니다. 전달 중 서명된 요청 요소를 바꾸면 서명이 무효화될 수 있으므로 보존하거나 의도한 변환 이후 서명해야 합니다.

Lattice 인가는 L4/service 이름으로만 제한되지 않습니다. Principal/VPC/service context 외에 method, path, header, query string 조건도 문서화되어 있으며 protocol·anonymous caller별 사용 가능 여부가 다릅니다. 이 service auth policy는 service network의 resource configuration을 보호하지 않습니다.

현재 WAF AssociateWebACL resource 목록에는 Lattice service/network가 없습니다. 지원되는 WAF component를 별도 경로에 구성할 수는 있지만 기존 그림의 직접 “Lattice WAF 통합” 주장은 근거가 없습니다. IAM, WAF, network isolation과 앱 인가는 서로 다른 제어입니다.


## 관측성

### Istio Metric과 Trace

실제 metric family·label과 reporter 하나를 사용합니다. 예시 backend의 총 RPS, 5xx/zero-status 비율, 밀리초 단위 p95는 다음과 같이 별도로 조회합니다.

```promql
sum(rate(istio_requests_total{reporter="source",destination_service_name="backend",destination_service_namespace="mesh-demo"}[5m]))

(sum(rate(istio_requests_total{reporter="source",destination_service_name="backend",destination_service_namespace="mesh-demo",response_code=~"5..|0"}[5m])) or vector(0))
/
sum(rate(istio_requests_total{reporter="source",destination_service_name="backend",destination_service_namespace="mesh-demo"}[5m]))

histogram_quantile(0.95, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="backend",destination_service_namespace="mesh-demo"}[5m])))
```

분자 fallback은 실제 트래픽이 있을 때 5xx series가 없는 경우를 처리합니다. 분모 부재는 부재로 남으며 idle traffic이 정상의 증거가 되지 않습니다. 실제 label·scrape 범위를 확인하세요. Connection/outlier gauge·counter는 별도 Envoy metric이며 고정된 “기본 metric 50개”나 보편적인 cache/retry 의미를 만들어 쓰면 안 됩니다.

현재 Telemetry는 metrics overrides/tagOverrides와 선언된 tracing provider를 사용합니다.

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    enableTracing: true
    extensionProviders:
    - name: otel-tracing
      opentelemetry:
        service: otel-collector.observability.svc.cluster.local
        port: 4317
---
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: backend-observability
  namespace: mesh-demo
spec:
  selector:
    matchLabels:
      app: backend
  metrics:
  - providers:
    - name: prometheus
    overrides:
    - match:
        metric: REQUEST_COUNT
      tagOverrides:
        request_method:
          value: request.method
  tracing:
  - providers:
    - name: otel-tracing
    randomSamplingPercentage: 10
    customTags:
      environment:
        literal:
          value: lab
```

IstioOperator는 **istioctl 입력**이며 검토된 기존 설치값에 병합합니다. Live istio ConfigMap을 덮어쓰거나 다른 extension provider를 버리지 마세요. Collector Service가 실제로 4317에서 OTLP gRPC를 받고 backend/exporter pipeline이 있어야 하며 이 객체가 Collector를 설치하지는 않습니다. Telemetry provider 이름은 MeshConfig와 일치해야 합니다.

Metric dimension 추가가 임의의 업무 metric 생성과 같지는 않습니다. Cardinality를 제한하고 필요한 앱 metric과 호환 exemplar/tracing을 별도로 구성하세요. End-to-end trace에는 앱 context 전파, sampling과 collector/backend 전달이 필요하며 Istio 설치만으로 “모든 backend”나 baggage 자동 전파가 보장되지 않습니다.

### VPC Lattice Metric

문서화된 CloudWatch namespace는 대소문자까지 **AWS/VpcLattice**입니다. Service dimension은 Service·AvailabilityZone, target group은 TargetGroup·AvailabilityZone 등을 사용합니다. 실제로 emit된 metric/dimension 조합을 먼저 확인합니다.

```bash
aws cloudwatch list-metrics --region "$AWS_REGION"   --namespace AWS/VpcLattice --metric-name TotalRequestCount
```

| 문서화된 신호 | 의미 |
|---|---|
| TotalRequestCount | 요청 수이며 Sum이 유용함 |
| RequestTime | 밀리초 단위 Average/percentile; service/target-group별 측정 경계 확인 |
| HTTPCode_2XX_Count부터 HTTPCode_5XX_Count | 집계한 HTTP 응답 |
| HTTPCode_VpcLattice_403_Count 등의 세부 코드 | Lattice가 생성한 응답; access-log 원인과 함께 사용 |
| Target-group connection metric | Protocol별 connection/error/byte이며 앱 요청 metric과 구분 |

Resource가 트래픽을 받은 이후 1분 단위로 발행합니다. 5분 query period는 집계 선택입니다. Target health는 list-targets와 health-check 정보로 확인하며 HealthyTargetCount, TargetResponseTime 같은 ALB metric 이름을 이 namespace에 가정하지 마세요.

최근 1시간 조회를 위해 UTC 시각을 한 번 생성합니다. 다음 Bash/Python 코드는 AWS를 호출하지 않습니다.

```bash
read -r START_TIME END_TIME START_EPOCH END_EPOCH < <(python3 - <<'PYTIME'
from datetime import datetime, timedelta, timezone
end = datetime.now(timezone.utc).replace(microsecond=0)
start = end - timedelta(hours=1)
print(start.strftime('%Y-%m-%dT%H:%M:%SZ'),
      end.strftime('%Y-%m-%dT%H:%M:%SZ'),
      int(start.timestamp()), int(end.timestamp()))
PYTIME
)
```

list-metrics에서 Service-only metric을 선택해 정확한 Service dimension 값을 복사합니다. AZ별 metric을 선택했다면 AZ를 누락하지 말고 반환된 전체 dimension 집합을 사용하세요.

```bash
: "${SERVICE_DIMENSION:?Copy the exact Service dimension value from list-metrics}"
aws cloudwatch get-metric-statistics --region "$AWS_REGION"   --namespace AWS/VpcLattice --metric-name TotalRequestCount   --dimensions "Name=Service,Value=$SERVICE_DIMENSION"   --start-time "$START_TIME" --end-time "$END_TIME"   --period 60 --statistics Sum
```

Metric 누락이 자동으로 트래픽 0이나 정상 service를 뜻하지 않습니다. Lattice AWS namespace에는 제공되는 service metric이 있으며 앱은 custom metric이나 log metric을 별도로 발행할 수 있습니다. 따라서 “custom metric이 불가능하다”는 일반화는 부정확합니다.

### Access Log와 요청 연결

Lattice는 CloudWatch Logs, S3, Data Firehose로 access log를 보낼 수 있습니다. Delivery 권한, destination policy, retention과 비용을 구성해야 하며 전달 지연은 best effort입니다. 다음은 문서화된 field의 **예시**이며 운영에서 수집한 log가 아닙니다.

```json
{
  "startTime": "2025-01-15T12:34:56Z",
  "serviceArn": "arn:aws:vpc-lattice:us-east-1:123456789012:service/svc-0123456789abcdef0",
  "requestMethod": "GET",
  "requestPath": "/api/v1/items",
  "protocol": "HTTP/1.1",
  "responseCode": 200,
  "duration": 12,
  "requestId": "example-request-001"
}
```

authDeniedReason, failureReason, callerPrincipal/resolvedUser와 source/target 정보도 문서화되어 있습니다. Resource-access log는 별도의 TCP/resource 경로이므로 실제 log type을 구분하세요. 일반적인 timestamp/requestProtocol/responseCodeDetails/requestHeaders/traceparent field를 가정하면 안 됩니다.

requestId는 client가 지정할 수 있는 x-amzn-requestid와 연결되며 인증된 identity가 아닙니다. 앱이 전파하는 W3C trace header는 보장된 native log field나 자동으로 만들어진 distributed trace와 별개입니다. 앱 instrumentation은 적절한 tracing backend를 사용할 수 있으며 X-Ray로만 제한되지 않습니다.

설정된 log group에 두 time bound를 모두 지정하고 query 상태·결과를 확인합니다.

```bash
: "${LATTICE_LOG_GROUP:?Set the configured CloudWatch log group}"
QUERY_ID=$(aws logs start-query --region "$AWS_REGION"   --log-group-name "$LATTICE_LOG_GROUP"   --start-time "$START_EPOCH" --end-time "$END_EPOCH"   --query-string 'fields @timestamp, requestId, requestMethod, requestPath, responseCode, authDeniedReason, failureReason | filter responseCode >= 500 | sort @timestamp desc | limit 20'   --query queryId --output text)
aws logs get-query-results --region "$AWS_REGION" --query-id "$QUERY_ID"
```

Query가 Scheduled/Running일 수 있으므로 즉시 빈 결과가 나왔다고 오류가 없다는 뜻은 아닙니다. 조사에 맞게 접근·시간 범위를 제한하세요. Kiali/Grafana나 CloudWatch dashboard도 실제 data source와 접근 설정이 필요하며 이름만으로 동등한 가시성이 증명되지 않습니다.

## 설치와 운영

### 플랫폼 선택과 검증

Istio 1.31은 Kubernetes 1.32–1.36을 지원합니다. 실제 관리형 플랫폼과 필요한 proxy mode의 지원 교집합을 사용하세요. 내장 production profile은 없으며 istio.io/injection label도 sidecar 주입을 활성화하지 않습니다. 현재 artifact, revision label과 전제조건은 [설치 가이드](../01-installation.md)를 참고하세요. Demo addon은 운영 monitoring/HA stack이 아닙니다.

Lattice에서는 service/resource 모델, 실제 client association/endpoint 경로, target lifecycle, listener protocol과 인증 경계를 정의합니다. Service가 반드시 Lambda일 필요는 없으며 meshed EKS 앱도 별도로 지원되는 통합으로 Lambda를 호출할 수 있습니다. Lambda 자체에 Istio sidecar를 둘 수 없다는 것과 EKS+Lambda 구조 전체가 Istio와 호환되지 않는다는 것은 다릅니다.

전체 service 설정에는 각 owner에 맞는 순서로 다음이 필요합니다.

1. 기존 network 연결, DNS, security group과 허용된 management/client role.
2. Service network와 의도한 client VPC association 또는 service-network endpoint.
3. 의도한 auth mode의 service 및 network/service association.
4. Target group, 지원 target 등록과 검증한 health 동작.
5. Listener/rule과 domain/certificate 설정.
6. 필요한 모든 auth policy·caller identity 권한과 인증 요청을 위한 signer.
7. Log/metric, 실제 요청·거부 시험과 resource lifecycle/cleanup 계획.

앞의 operation input은 이 절차의 일부입니다. 전제조건을 만들거나 readiness를 입증하지 않습니다. 다음 operation 전에 비동기 resource 상태와 기존 ownership을 확인하세요. Kubernetes에서는 오래된 Pod IP를 수동 유지하기보다 적절한 controller를 사용합니다. 관리형 service update도 controller, SDK, IAM, DNS와 앱 호환성 책임을 없애지는 않습니다.

### Istio Upgrade와 Ambient 등록

설치된 release에서 지원하는 upgrade 경로를 사용하고 검토한 전체 values, trust와 policy를 보존합니다. 과거 1.23→1.24 그림은 현재 대상 버전이 아닙니다. Revision 전환으로 임의의 minor version을 건너뛸 수는 없습니다.

기준 설치/GitOps 설정과 관련 custom resource를 백업합니다. kubectl get all은 모든 객체를 포함하지 않아 완전한 복구 백업이 아닙니다. 실제 namespace/revision/Pod override를 확인하고 workload 집합을 단계적으로 전환하며 readiness, traffic, certificate와 telemetry를 검증합니다. 전환을 확인할 때까지 rollback 용량을 유지하세요.

모든 workload를 강제 restart하거나 모든 certificate 오류에 CA를 재발급하거나 고정된 shared webhook 이름을 수동 삭제하는 절차를 일반 cleanup으로 쓰면 안 됩니다. 관련 proxy/gateway가 모두 이동한 뒤 release의 지원되는 retirement 절차를 사용하세요. Control plane 제거는 복구 선택지를 바꾸지만 rollback이 영원히 불가능하다는 보편적인 뜻은 아닙니다.

Ambient는 sidecar가 없는 workload를 앱 restart 없이 등록할 수 있지만 기존 sidecar 제거에는 workload 교체가 필요합니다. CNI/ztunnel 전제조건과 waypoint 등록·보안도 적용해야 합니다. Ready가 항상 2/2인 것은 아니며 native sidecar는 initContainers 아래에 있을 수 있습니다.

### 실제 실패 경계 진단

| 계층 | 선택한 구조에 맞는 확인 |
|---|---|
| 앱/target | Listen protocol/port, readiness, replica/endpoint, 의존성과 오류 |
| Mesh/Lattice routing | 유효한 route, subset/target group, health/fail-open, timeout과 resource 상태 |
| Identity/policy | Certificate lifetime/trust, JWT/SigV4, 모든 auth policy와 IAM 거부 |
| Network/DNS | 올바른 association/endpoint, route, security group/NetworkPolicy와 실제 resolver 경로 |
| Control/telemetry | Revision/controller, API/config 전파, 실제 metric과 전달된 log |

![Istio 진단을 위한 계층별 확인 예시입니다. 모든 장애의 순서나 시간 보장이 아니며 실제 실패 경계에 따라 조사합니다.](../../../.gitbook/assets/ko-service-mesh-istio-comparison-02-istio-vs-lattice-10.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-comparison-02-istio-vs-lattice-10.html)

Istio에서는 proxy-status/config와 실제 workload log가 유용합니다. Proxy image에 curl, tcpdump, shell이 있다고 가정하지 말고 필요한 권한의 지원되는 디버깅 방법을 사용하세요. 진단 archive를 보호하고 일시적인 debug 설정을 복구합니다. Backend replica 0은 Deployment/endpoint의 사실이지 Service.spec.replicas field가 아닙니다.

Lattice의 실제 resource는 다음 read operation으로 확인합니다.

```bash
: "${SERVICE_NETWORK_ID:?Set the actual service-network ID}"
: "${TG_ID:?Set the actual target-group ID}"
aws vpc-lattice get-service --region "$AWS_REGION" --service-identifier "$SERVICE_ID"
aws vpc-lattice list-service-network-service-associations --region "$AWS_REGION"   --service-network-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice get-target-group --region "$AWS_REGION" --target-group-identifier "$TG_ID"
aws vpc-lattice list-targets --region "$AWS_REGION" --target-group-identifier "$TG_ID"
```

list-services에는 service-network filter가 없습니다. Network 분석 도구는 지원되는 network resource를 분석하며 Lattice service ID를 EC2 network-insights destination으로 넘기는 것이 앱/IAM 전체 진단은 아닙니다. 이 명령이 고정된 3계층 절차, 5분 복구나 관리형 auto healing을 보장하지는 않습니다.


## 비용과 과거 근거

### 같은 비용 범위를 비교

앱, 가용성 요구, network traffic, log/metric retention과 엔지니어링 범위를 양쪽에 동일하게 포함합니다. Lattice가 앱의 EC2/EKS/ECS/Lambda compute를 지불하거나 제거하지 않습니다. 관리형 networking 청구액만 전체 Istio 앱 fleet·인건비와 비교할 수는 없습니다.

기존 예제에는 서로 다른 문제가 있었습니다.

- CPU 합계는 앱 10 + sidecar 10 + Istiod 1 + Prometheus 2 + Jaeger 1 + Kiali 0.5 = 24.5 vCPU입니다. vCPU 4개인 m5.xlarge 5대는 예약 용량을 제외하기 전에도 20 vCPU뿐입니다. CPU만의 이상적인 하한도 7대이며 다른 제약을 추가로 고려해야 합니다.
- 영어 항목 합계는 compute $850 + storage $15 = **$865**였습니다. 한국어는 근거 없는 latency/network $10을 더해 $875로 계산했습니다. Latency 자체가 AWS 과금 단위는 아닙니다.
- 기존 Lattice 계산은 $209 ×12 + $300 ×12 + $1,000 = **$7,108**이며 $7,608이 아닙니다. Setup+운영도 $5,100이 아닌 $4,600입니다.
- 그 과거 가정만 사용하더라도 월 infrastructure $209·운영 $300의 5년 합계에 setup을 한 번 더하면 **$31,540**입니다. Setup이 포함된 연간 값을 다섯 번 복제하면 안 됩니다.
- 한국어 Istio 5년 계산은 한쪽에만 contingency $50,000을 추가하고 초기 설정을 반복 계상했습니다. 제품 고유 가격 차이를 증명하는 것이 아니라 비교 범위가 다른 모델입니다.

과거의 노드당 월 $140, resource·staffing은 근거 있는 견적이나 workload 실측이 아닌 가정이었습니다. Mi와 MB도 혼합되어 있습니다. 100 × 128 Mi = 12,800 Mi = 12.5 Gi이며 12.8 decimal GB가 아닙니다. Sidecar가 Pod 수를 두 배로 만들지도 않고 resource 여유가 곧바로 billed node 제거로 이어지지도 않습니다.

### 현재 날짜를 명시한 Service 가격 예제

2026년 9월 11일 확인한 공식 US East(N. Virginia) service 가격 예제는 service-hour당 $0.025, 처리 GB당 $0.025와 문서화된 service별 시간당 allowance 초과 request/connection 비용을 사용합니다. Service-network VPC association과 service-network endpoint는 추가 비용이 없다고 명시합니다. Resource configuration/resource endpoint는 **다른** 가격 모델이며 그 $0.01/GB tier를 service data-processing 단가로 사용할 수 없습니다. 이 service 가격 모델에 기존의 별도 service-network-hour 비용을 추가하지 마세요.

명시적으로 가정한 HTTP/HTTPS service workload입니다.

| 입력 | 계산 | 월 networking 비용 |
|---|---|---:|
| Service 5개, 각각 730시간 |5 ×730 ×$0.025|$91.25|
| Request·response를 포함해 해당 service에서 합계 10,000 billable GB |10,000 ×$0.025|$250.00|
| 각 service가 모든 시간에 시간당 300,000 request 이내 |시간당 allowance 초과 없음|$0.00|
| 명시한 입력의 합계 |$91.25 +$250.00|**$341.25**|

Allowance를 넘으면 service·시간별로 공개된 $0.10/million 단가를 적용합니다. 월평균 RPS로 burst 시간의 비용을 없애면 안 됩니다. TLS passthrough connection 과금은 다른 counter입니다. 모든 billable service hop, 실제 Region, 앱 infrastructure, log와 관련 비용을 포함하세요. 날짜와 가정을 명시한 예시이며 견적·미래 가격 보장이나 미측정 Istio fleet 대비 절감 주장이 아닙니다.

일회성 setup/migration과 반복 운영을 분리합니다. 할인, 구매 약정, 성장·불확실성과 동일 HA/support 요구도 다년 비교에 영향을 줍니다. 기존 표가 보편적인 연간 $42,000 또는 5년 $260,000 절감을 입증하지 않습니다.

### 과거 측정값의 정직한 보존

이전 성능 section은 Istio 1.24 맥락에서 **노드 2개 EKS, m5.xlarge, 1,000 RPS** 시험을 주장했지만 harness, raw sample, 정확한 EKS/patch/proxy 버전과 같은 조건의 설정을 제공하지 않았습니다.

| 원래 미검증 결과 | Baseline | Istio 전체 | Lattice 전체 |
|---|---:|---:|---:|
| p50 |1.0 ms|2.0 ms|1.5 ms|
| p95 |2.5 ms|5.0 ms|3.7 ms|
| p99 |5.0 ms|8.5 ms|7.0 ms|
| 최대 RPS |10,000|8,500|9,200|
| CPU 주장 |100%|115%|102%|
| 메모리 주장 |1 GB|1.5 GB|1.05 GB|

과거 미검증 주장으로 보존하며 새 1.31 측정값으로 바꾸지 않습니다. 전체 latency/throughput 차이가 sidecar 제거 때문이라는 증거도 아닙니다. 의미 있는 시험은 protocol, payload, TLS/authorization, placement, load, telemetry와 실패 동작을 맞추고 raw failure와 retry로 가려진 결과를 분리합니다.

이전 익명 고객 사례와 re:Invent 만족도 설문 주장에는 추적 가능한 출처·방법론이 없었습니다. Migration, staffing과 hybrid ownership에 관한 질문으로는 활용할 수 있지만 실측 성공률은 아닙니다. 확인한 **CNCF 2024 Annual Survey**는 container challenge, project 사용과 service-mesh 사용 현황을 묻습니다. “Istio 도입 실패 40%”나 나열한 실패 원인 비율의 근거가 아닙니다. 설문을 인용할 때 실제 질문·표본·의미를 사용하세요.

## Hybrid와 Multicloud

![Cluster 내부 Istio와 외부의 별도 Lattice service 경로를 조합한 구조 예시입니다. Signer, network, TLS와 선택적 egress-gateway 조건을 완성해야 합니다.](../../../.gitbook/assets/ko-service-mesh-istio-comparison-02-istio-vs-lattice-17.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-comparison-02-istio-vs-lattice-17.html)

개념적인 선택지이며 완전한 egress 설정이 아닙니다. Direct sidecar 경로 또는 명시적으로 구성한 egress gateway를 선택하고 모든 TLS/identity 경계를 정의합니다. Lattice가 STRICT backend에 Istio SPIFFE mTLS를 자동으로 시작하지는 않습니다. 명시적 ingress 경계에서 의도한 외부 경로를 인증하고 downstream mesh mTLS를 사용할 수 있으며, backend에는 원 IAM caller 대신 gateway identity가 보일 수 있습니다.

앱이 서명하고 HTTPS를 시작한다면 payment.vpclattice.aws를 만들지 말고 **실제** Lattice service DNS를 조회합니다.

```bash
aws vpc-lattice get-service --region "$AWS_REGION"   --service-identifier "$SERVICE_ID" > lattice-service.json
LATTICE_HOST=$(jq -er '.dnsEntry.domainName | select(type == "string" and length > 0)' lattice-service.json) || exit 1
jq -n --arg host "$LATTICE_HOST" '{
  apiVersion:"networking.istio.io/v1",kind:"ServiceEntry",
  metadata:{name:"payment-lattice",namespace:"mesh-demo"},
  spec:{hosts:[$host],location:"MESH_EXTERNAL",resolution:"DNS",
        ports:[{number:443,name:"https",protocol:"HTTPS"}]}
}' > lattice-service-entry.json
```

Workload의 정상 configuration owner가 검토·적용할 registry entry만 생성합니다. Lattice provisioning, egress-gateway 통과 강제, 서명이나 IAM 우회를 수행하지 않습니다. 앱 HTTPS는 sidecar에 불투명하므로 기존 불완전한 egress 예제처럼 HTTP VirtualService가 그 path를 읽을 수 없습니다. 이미 암호화한 앱 stream에 SIMPLE TLS를 한 겹 더 씌우지 마세요.

Service-network endpoint는 on-premises나 다른 연결 network의 지원되는 진입 경로가 될 수 있습니다. Routing, DNS, security group과 해당 service authorization이 필요합니다. “AWS에서 운영됨”이 AWS 밖 client는 무조건 불가능하다는 뜻은 아닙니다. Global service network를 만들거나 Region/cloud 사이 앱 데이터를 복제하지도 않습니다.

Migration에는 API, identity, certificate trust, route, telemetry와 복구 ownership을 대응시켜야 합니다. Namespace label 변경만으로 Lattice IAM에서 mesh identity로 완전히 전환되지 않습니다. 세부 조건은 [VPC Lattice 가이드](../../../networking/02-vpc-lattice.md), [AWS 통합](../04-aws-integration.md), [multicluster 가이드](../advanced/02-multi-cluster.md)를 참고하세요.

## 선택 기준

| 요구사항 | 판단 근거 |
|---|---|
| Kubernetes/VM workload mesh | 필요한 sidecar/ambient 기능, platform 지원, identity lifecycle과 실측 운영 용량 |
| AWS service/resource 연결 | 지원 target/resource type, 실제 client 경로, auth/TLS와 owner 책임 |
| 세밀한 traffic 동작 | 기능 별점보다 실제 rule/filter API, protocol 제한, retry, health와 실패 동작 |
| 강한 보안 | 우회를 포함해 모든 종료점의 end-to-end identity/encryption과 앱 인가 |
| 작은 팀·빠른 전달 | 임의의 최소 인력·고정 설치 시간보다 실제 팀의 반복 가능한 절차와 지원 계획 |
| 비용·성능 | 동일 범위 청구액, 재현 가능한 load/failure 측정과 날짜·가정 |
| Hybrid/multicloud | 제품 이름이 아닌 검증된 network/identity 경계와 앱·데이터 복구 |

실제 workload로 bounded PoC를 평가하고 근거를 보존합니다. 아키텍처만으로 “Istio는 항상 비싸고 복잡하다”거나 “Lattice는 항상 저렴하고 안전하다”고 결론낼 수 없습니다.


## 공식 근거

- [Istio supported releases](https://istio.io/latest/docs/releases/supported-releases/), [ambient](https://istio.io/latest/docs/ambient/overview/), [security](https://istio.io/latest/docs/concepts/security/) and [Telemetry API](https://istio.io/latest/docs/reference/config/telemetry/)
- [VPC Lattice components and responsibilities](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html) and [network associations/endpoints](https://docs.aws.amazon.com/vpc-lattice/latest/ug/service-network-associations.html)
- [CreateRule](https://docs.aws.amazon.com/vpc-lattice/latest/APIReference/API_CreateRule.html), [RuleAction](https://docs.aws.amazon.com/vpc-lattice/latest/APIReference/API_RuleAction.html), [CreateListener](https://docs.aws.amazon.com/vpc-lattice/latest/APIReference/API_CreateListener.html) and [CreateTargetGroup](https://docs.aws.amazon.com/vpc-lattice/latest/APIReference/API_CreateTargetGroup.html)
- [Target groups](https://docs.aws.amazon.com/vpc-lattice/latest/ug/target-groups.html) and [health checks](https://docs.aws.amazon.com/vpc-lattice/latest/ug/target-group-health-checks.html)
- [HTTPS listeners](https://docs.aws.amazon.com/vpc-lattice/latest/ug/https-listeners.html) and [TLS passthrough](https://docs.aws.amazon.com/vpc-lattice/latest/ug/tls-listeners.html)
- [Auth policies](https://docs.aws.amazon.com/vpc-lattice/latest/ug/auth-policies.html), [PutAuthPolicy](https://docs.aws.amazon.com/vpc-lattice/latest/APIReference/API_PutAuthPolicy.html) and [SigV4 requests](https://docs.aws.amazon.com/vpc-lattice/latest/ug/sigv4-authenticated-requests.html)
- [Lattice metrics](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-cloudwatch.html) and [access logs](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-access-logs.html)
- [Lattice pricing](https://aws.amazon.com/vpc/lattice/pricing/), [WAF association API](https://docs.aws.amazon.com/waf/latest/APIReference/API_AssociateWebACL.html) and [Lambda@Edge](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-at-the-edge.html)
- [CNCF 2024 survey](https://www.cncf.io/reports/cncf-annual-survey-2024/) and [original report](https://www.cncf.io/wp-content/uploads/2025/04/cncf_annual_survey24_031225a.pdf), especially questions 22, 32, 47 (pages 12, 16, 22)
- [Service-mesh comparison](01-service-mesh-comparison.md), [Istio architecture](../03-architecture.md) and [ambient guide](../advanced/01-ambient-mode.md)

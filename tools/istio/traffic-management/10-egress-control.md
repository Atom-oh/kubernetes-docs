# Egress 제어

Egress 제어는 메시 외부로 나가는 트래픽을 관리하고 보안을 강화하는 기능입니다.

## 목차

1. [Egress 개요](#egress-개요)
2. [ServiceEntry 설정](#serviceentry-설정)
3. [Egress Gateway](#egress-gateway)
4. [TLS Origination](#tls-origination)
5. [실전 예제](#실전-예제)

## Egress 개요

```mermaid
flowchart LR
    Pod[파드]
    
    subgraph Mesh["Service Mesh"]
        Sidecar[Envoy<br/>Sidecar]
        EgressGW[Egress<br/>Gateway]
    end
    
    External[외부 서비스<br/>api.external.com]
    
    Pod --> Sidecar
    Sidecar --> EgressGW
    EgressGW --> External
    
    %% 스타일 정의
    classDef pod fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef mesh fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef external fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    
    %% 클래스 적용
    class Pod pod;
    class Sidecar,EgressGW mesh;
    class External external;
```

## ServiceEntry 설정

### 외부 서비스 등록

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
spec:
  hosts:
  - api.external.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

### HTTP 외부 서비스

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: httpbin
spec:
  hosts:
  - httpbin.org
  ports:
  - number: 80
    name: http
    protocol: HTTP
  location: MESH_EXTERNAL
  resolution: DNS
```

## Egress Gateway

### Egress Gateway 설치

```bash
helm install istio-egressgateway istio/gateway \
  -n istio-system \
  --set labels.app=istio-egressgateway \
  --set labels.istio=egressgateway
```

### Egress Gateway 구성

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: istio-egressgateway
spec:
  selector:
    istio: egressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    hosts:
    - api.external.com
    tls:
      mode: PASSTHROUGH
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: direct-external-through-egress-gateway
spec:
  hosts:
  - api.external.com
  gateways:
  - mesh
  - istio-egressgateway
  http:
  - match:
    - gateways:
      - mesh
      port: 80
    route:
    - destination:
        host: istio-egressgateway.istio-system.svc.cluster.local
        port:
          number: 443
  - match:
    - gateways:
      - istio-egressgateway
      port: 443
    route:
    - destination:
        host: api.external.com
        port:
          number: 443
```

## 참고 자료

- [Istio Egress Traffic](https://istio.io/latest/docs/tasks/traffic-management/egress/)
- [Egress Gateway](https://istio.io/latest/docs/tasks/traffic-management/egress/egress-gateway/)

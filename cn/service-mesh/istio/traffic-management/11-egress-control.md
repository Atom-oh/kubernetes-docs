# 出口流量控制

出口流量控制是一项用于管理网格出站流量并增强安全性的功能。

## 目录

1. [出口流量概述](#egress-overview)
2. [ServiceEntry 配置](#serviceentry-configuration)
3. [Egress Gateway](#egress-gateway)
4. [TLS 发起](#tls-origination)
5. [实践示例](#practical-examples)

## 出口流量概述

```mermaid
flowchart LR
    Pod[Pod]

    subgraph Mesh["Service Mesh"]
        Sidecar[Envoy<br/>Sidecar]
        EgressGW[Egress<br/>Gateway]
    end

    External[External Service<br/>api.external.com]

    Pod --> Sidecar
    Sidecar --> EgressGW
    EgressGW --> External

    %% Style definitions
    classDef pod fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef mesh fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef external fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class Pod pod;
    class Sidecar,EgressGW mesh;
    class External external;
```

## ServiceEntry 配置

### 注册外部 Service

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

### HTTP 外部 Service

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

### 安装 Egress Gateway

```bash
helm install istio-egressgateway istio/gateway \
  -n istio-system \
  --set labels.app=istio-egressgateway \
  --set labels.istio=egressgateway
```

### 配置 Egress Gateway

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

## 参考资料

- [Istio 出口流量](https://istio.io/latest/docs/tasks/traffic-management/egress/)
- [Egress Gateway](https://istio.io/latest/docs/tasks/traffic-management/egress/egress-gateway/)

# 出口流量控制

出口流量控制用于管理网格的出站流量并增强安全性。

## 目录

1. [出口流量概述](#egress-overview)
2. [ServiceEntry 配置](#serviceentry-configuration)
3. [Egress Gateway](#egress-gateway)
4. [TLS 发起](#tls-origination)
5. [验证](#verification)

## 出口流量概述 {#egress-overview}

本示例将应用发起的 HTTPS 流量依次经由 sidecar 和网格中的 egress gateway 路由。请将 `api.external.com` 替换为你控制且可解析的端点，并使用兼容且已安装的 Istio 控制平面。ServiceEntry 用于注册目标；它不会强制流量经过网关，也不是防火墙。还应通过网络控制来实施出站限制。

![Pod 的出站流量先经过 Envoy sidecar 和服务网格中的 Istio egress gateway，再到达外部服务 api.external.com。](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-11-egress-control-0.png)

[🔍 查看交互式图示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-11-egress-control-0.html)

## ServiceEntry 配置 {#serviceentry-configuration}

### 注册外部服务

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

### HTTP 外部服务

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
  --version 1.31.0 \
  --set service.type=ClusterIP \
  --set labels.app=istio-egressgateway \
  --set labels.istio=egressgateway \
  --wait
```

### 配置 Egress Gateway

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: istio-egressgateway
  namespace: istio-system
spec:
  selector:
    istio: egressgateway
  servers:
  - port:
      number: 443
      name: tls
      protocol: TLS
    hosts:
    - api.external.com
    tls:
      mode: PASSTHROUGH
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: egressgateway-for-external
  namespace: default
spec:
  host: istio-egressgateway.istio-system.svc.cluster.local
  subsets:
  - name: external
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: direct-external-through-egress-gateway
  namespace: default
spec:
  hosts:
  - api.external.com
  gateways:
  - mesh
  - istio-system/istio-egressgateway
  tls:
  - match:
    - gateways:
      - mesh
      port: 443
      sniHosts:
      - api.external.com
    route:
    - destination:
        host: istio-egressgateway.istio-system.svc.cluster.local
        subset: external
        port:
          number: 443
  - match:
    - gateways:
      - istio-system/istio-egressgateway
      port: 443
      sniHosts:
      - api.external.com
    route:
    - destination:
        host: api.external.com
        port:
          number: 443
```

## TLS 发起 {#tls-origination}

该示例保留应用与外部服务之间的 TLS 连接；egress gateway 根据 SNI 路由。TLS 发起则是在应用发送 HTTP 后，由代理启动 TLS。这要求 HTTP ServiceEntry 的端口和 targetPort 与 DestinationRule 中的 TLS 策略匹配；请遵循 [TLS 发起指南](https://istio.io/latest/docs/tasks/traffic-management/egress/egress-tls-origination/)。如果应用连接已经加密，不要再发起第二层 TLS。

## 验证 {#verification}

请按照[安装指南](../01-installation.md)配置 chart 仓库和版本。将这些资源放在指定的命名空间中，并确保原始外部 ServiceEntry 位于 `default` 命名空间，或已导出到客户端命名空间。使用携带 SNI 的网格客户端，检查两侧代理的路由，并确认 egress gateway 收到连接。仅能到达外部端点并不能证明流量经过了网关。

```bash
istioctl analyze -A
kubectl get pods -n istio-system -l istio=egressgateway
istioctl proxy-config listeners <egress-pod> -n istio-system
istioctl proxy-config clusters <client-pod> -n default
```

## 参考资料

- [Istio 出口流量](https://istio.io/latest/docs/tasks/traffic-management/egress/)
- [Egress Gateway](https://istio.io/latest/docs/tasks/traffic-management/egress/egress-gateway/)

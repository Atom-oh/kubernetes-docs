# Egress 制御

Egress 制御は mesh からの outbound traffic を管理し、セキュリティを強化する機能です。

## 目次

1. [Egress の概要](#egress-overview)
2. [ServiceEntry の設定](#serviceentry-configuration)
3. [Egress Gateway](#egress-gateway)
4. [TLS Origination](#tls-origination)
5. [検証](#verification)

## Egress の概要 {#egress-overview}

この例では、アプリケーションからの HTTPS を sidecar と egress gateway 経由で routing します。`api.external.com` は、自分が管理し、名前解決可能な endpoint に置き換えてください。互換性のある Istio control plane をすでにインストールして使います。ServiceEntry は宛先を登録しますが、gateway 経由の traffic を強制するものでも、firewall として動作するものでもありません。egress の制限は、network control でも適用してください。

![Pod からの outbound traffic は、service mesh 内の Envoy sidecar と Istio egress gateway を通ってから、外部 service api.external.com に到達します。](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-11-egress-control-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-11-egress-control-0.html)

## ServiceEntry の設定 {#serviceentry-configuration}

### 外部 Service の登録

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

### Egress Gateway のインストール

```bash
helm install istio-egressgateway istio/gateway \
  -n istio-system \
  --version 1.31.0 \
  --set service.type=ClusterIP \
  --set labels.app=istio-egressgateway \
  --set labels.istio=egressgateway \
  --wait
```

### Egress Gateway の設定

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

## TLS Origination

この例では、アプリケーションから外部 service への TLS 接続を維持し、egress gateway は SNI を使って routing します。一方、TLS origination では、アプリケーションが HTTP を送信した後、proxy で TLS を開始します。その場合は、HTTP の ServiceEntry の `port`／`targetPort` と DestinationRule の TLS policy を一致させる必要があります。[TLS origination guide](https://istio.io/latest/docs/tasks/traffic-management/egress/egress-tls-origination/) に従い、すでに暗号化されたアプリケーション接続に TLS layer を重ねて origination しないでください。

## 検証 {#verification}

[インストールガイド](../01-installation.md)に従って chart repository と version を設定してください。resource は指定された namespace に配置し、元の外部 ServiceEntry が `default` namespace にあるか、client namespace に export されていることを確認します。mesh client から SNI を指定し、両方の proxy route を調べ、egress gateway が接続を受信したことを検証してください。外部 endpoint に到達できただけでは、gateway を経由した証明にはなりません。

```bash
istioctl analyze -A
kubectl get pods -n istio-system -l istio=egressgateway
istioctl proxy-config listeners <egress-pod> -n istio-system
istioctl proxy-config clusters <client-pod> -n default
```

## 参考資料

- [Istio Egress Traffic](https://istio.io/latest/docs/tasks/traffic-management/egress/)
- [Egress Gateway](https://istio.io/latest/docs/tasks/traffic-management/egress/egress-gateway/)

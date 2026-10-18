# 会话亲和性

会话亲和性（也称 Sticky Session）是一种基于相同哈希键为请求提供软亲和性的技术；它不保证请求会永久分配到同一个 Pod。

## 目录

1. [会话亲和性概述](#session-affinity-overview)
2. [基于一致性哈希](#consistent-hash-based)
3. [基于 Cookie](#cookie-based)
4. [基于 HTTP 请求头](#http-header-based)
5. [基于源 IP](#source-ip-based)
6. [运维注意事项](#operational-considerations)

<span id="session-affinity-overview"></span>

## 会话亲和性概述

![一致性哈希会话亲和性示意图：客户端请求携带用户 ID，经负载均衡器哈希后会始终路由到同一个 Pod；对于该会话，其他 Pod 副本不会处理请求。](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-10-session-affinity-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-10-session-affinity-0.html)

<span id="consistent-hash-based"></span>

## 基于一致性哈希

<span id="http-header-based"></span>

### 基于 HTTP 请求头

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-session-affinity
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      consistentHash:
        httpHeaderName: "x-user-id"
```

<span id="cookie-based"></span>

### 基于 Cookie

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-cookie-affinity
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      consistentHash:
        httpCookie:
          name: "session-id"
          ttl: 0s  # Cookie expiration time (0s = session cookie)
```

<span id="source-ip-based"></span>

### 基于源 IP

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-ip-affinity
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      consistentHash:
        useSourceIp: true
```

<span id="operational-considerations"></span>

## 运维注意事项

图示假设 endpoint 集合未发生变化，且每个代理看到的 endpoint 集合一致。添加或移除 Pod，或因本地性导致 endpoint 视图不同，都可能改变请求的映射结果。请保存会话状态，以便发生重新映射或 Pod 故障时仍能安全处理。

针对同一 host，应从这些 DestinationRule 中选择一个使用。基于 HTTP 请求头/Cookie 的哈希需要进行 HTTP 处理；缺少请求头时无法识别用户。如果 Cookie 尚不存在，`ttl: 0s` 会创建会话 Cookie，但浏览器必须在后续请求中回传该 Cookie。Cookie 属性和有效期应符合应用要求。

基于源 IP 的哈希使用代理实际看到的源地址。NAT 和中间负载均衡器可能使多个客户端共用一个地址；依赖此方式前，请检查受信任代理及客户端 IP 的处理配置。这些 DestinationRule 示例描述的是 sidecar 行为；waypoint 对相关特性的支持应另行确认。

## 参考资料

- [Istio 会话亲和性](https://istio.io/latest/docs/reference/config/networking/destination-rule/#LoadBalancerSettings-ConsistentHashLB)

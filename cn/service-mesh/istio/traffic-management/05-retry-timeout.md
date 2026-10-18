# 重试与超时

重试和超时是提升微服务韧性的核心机制。使用 Istio，您无需修改应用程序代码即可配置这些策略。

## 目录

1. [概述](#overview)
2. [超时配置](#timeout-configuration)
3. [重试配置](#retry-configuration)
4. [组合使用重试与超时](#combining-retry-and-timeout)
5. [实践示例](#practical-examples)
6. [重要警告](#important-warnings)
7. [最佳实践](#best-practices)
8. [故障排除](#troubleshooting)

<span id="overview"></span>

## 概述

以下示例是可选的 HTTP sidecar 策略；除非明确给出写入策略，否则假定操作可安全重试。原生 SQL 流量和不透明的应用 HTTPS 不能使用这些 HTTP 重试/超时规则。还应设置调用方截止时间；多个层级的重试会相乘增加后端尝试次数，而且可能超过某一层的本地超时时间。

### 为什么需要超时和重试？

![未配置超时/重试时，客户端会一直等待无响应的服务并浪费资源；使用 Istio 超时/重试后，它会在 1 秒后停止，重试另一个实例并成功。](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-05-retry-timeout-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-05-retry-timeout-0.html)

<span id="timeout-configuration"></span>

## 超时配置

### 基本超时

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-timeout
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
    timeout: 10s  # Timeout after 10 seconds
```

### 按路径配置超时

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-timeouts
spec:
  hosts:
  - api.example.com
  http:
  # Fast response API - short timeout
  - match:
    - uri:
        prefix: "/api/quick"
    route:
    - destination:
        host: api-service
    timeout: 1s

  # Standard API
  - match:
    - uri:
        prefix: "/api/standard"
    route:
    - destination:
        host: api-service
    timeout: 5s

  # Heavy operations - long timeout
  - match:
    - uri:
        prefix: "/api/batch"
    route:
    - destination:
        host: api-service
    timeout: 30s
```

<span id="retry-configuration"></span>

## 重试配置

> **重要：** 省略 `retries` 并不一定意味着禁用了重试。Istio 1.31.0 渲染出的默认值为 `attempts: 2`，且 `retryOn: connect-failure,refused-stream,unavailable,cancelled,retriable-status-codes`。`attempts` 统计的是**原始请求后的额外重试次数**，因此这可能导致总计三次发送。请在路由上设置 `attempts: 0`，以显式禁用代理重试。

HTTPRetry 参考文档对该列表作了缩写；已发布的重试实现还会对已配置的状态码启用 `retriable-status-codes`。群集默认值可以被覆盖。显式重试策略必须列明目标条件；不要假设所有超时都会触发重试，也不要假设始终有其他健康端点可用。

### 基本重试

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-retry
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
    retries:
      attempts: 3  # Maximum 3 retries
      perTryTimeout: 2s  # 2s timeout per attempt
      retryOn: 5xx,reset,connect-failure,refused-stream  # Retry conditions
```

### 重试条件

| 条件 | 描述 |
|-----------|-------------|
| `5xx` | HTTP 5xx 错误 |
| `gateway-error` | 502、503、504 错误 |
| `reset` | 连接重置 |
| `connect-failure` | 连接失败 |
| `refused-stream` | HTTP/2 REFUSED_STREAM |
| `retriable-4xx` | 409 Conflict |
| `retriable-status-codes` | 自定义状态码 |

### 高级重试配置

`payment-service` 接受非幂等写入（提交扣款），因此若对每种方法应用同一重试策略，mesh 就可能在出现 `reset`
或 `5xx` 时重放 POST——这正是本页警告的模糊重放风险。请改为按方法拆分
路由：对只读状态检查积极重试，对写入路径则完全禁用
mesh 重试。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: advanced-retry
spec:
  hosts:
  - payment-service
  http:
  - name: reads-retryable
    match:
    - method:
        regex: "^(GET|HEAD)$"
    route:
    - destination:
        host: payment-service
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: connect-failure,refused-stream
      retryRemoteLocalities: true  # Retry to other regions
  - name: writes-no-mesh-retry
    match:
    - method:
        regex: "^(POST|PUT|PATCH|DELETE)$"
    route:
    - destination:
        host: payment-service
    retries:
      attempts: 0
```

<span id="combining-retry-and-timeout"></span>

## 组合使用重试与超时

### 分层超时

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: layered-timeouts
spec:
  hosts:
  - frontend
  http:
  - route:
    - destination:
        host: frontend
    timeout: 10s  # Total timeout
    retries:
      attempts: 3
      perTryTimeout: 3s  # Timeout for each delivery, including the original
```

**计算**：理论上的发送时间上限为 `(1 + attempts) × perTryTimeout = 4 × 3s = 12s`，但路由级 `timeout: 10s` 会优先生效。退避和剩余路由超时可能会减少实际尝试的重试次数。

### 按 HTTP 方法拆分重试策略

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: order-service
spec:
  hosts:
  - order-service
  http:
  # POST/PATCH: do not replay an ambiguous write in the mesh
  - name: writes-no-mesh-retry
    match:
    - method:
        regex: "^(POST|PUT|PATCH|DELETE)$"
    route:
    - destination:
        host: order-service
    timeout: 10s
    retries:
      attempts: 0

  # GET/HEAD: retry only connection establishment and REFUSED_STREAM failures
  - name: reads-limited-retry
    match:
    - method:
        regex: "^(GET|HEAD)$"
    route:
    - destination:
        host: order-service
    timeout: 5s
    retries:
      attempts: 2
      perTryTimeout: 2s
      retryOn: connect-failure,refused-stream
```

默认对 POST/PATCH 以及领域定义为写入的任何操作禁用 mesh 重试。不要仅凭 HTTP 方法就推断 PUT 或 DELETE 是安全的：仅当应用程序的实际契约使重复执行安全时，才对它们进行重试。

<span id="practical-examples"></span>

## 实践示例

### 示例 1：微服务链

```yaml
# Frontend → Backend → Database
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: frontend
spec:
  hosts:
  - frontend
  http:
  - route:
    - destination:
        host: frontend
    timeout: 15s  # Consider entire chain
    retries:
      attempts: 2
      perTryTimeout: 7s
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: backend
spec:
  hosts:
  - backend
  http:
  - route:
    - destination:
        host: backend
    timeout: 10s  # Consider database call
    retries:
      attempts: 3
      perTryTimeout: 3s
      retryOn: 5xx,reset
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: database
spec:
  hosts:
  - database
  http:
  - route:
    - destination:
        host: database
    timeout: 5s
    retries:
      attempts: 2
      perTryTimeout: 2s
      retryOn: connect-failure,refused-stream
```

### 示例 2：外部 API 调用

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-api
spec:
  hosts:
  - api.external.com
  http:
  - route:
    - destination:
        host: api.external.com
    timeout: 30s  # External APIs can be slow
    retries:
      attempts: 5  # External APIs have frequent transient failures
      perTryTimeout: 5s
      retryOn: 5xx,reset,connect-failure,gateway-error
---
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
spec:
  hosts:
  - api.external.com
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
  resolution: DNS
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-api-tls
spec:
  host: api.external.com
  trafficPolicy:
    tls:
      mode: SIMPLE
      sni: api.external.com
      subjectAltNames:
      - api.external.com
```

此发起请求示例由应用调用 `http://api.external.com`；部署时应将主机名替换为实际服务地址。如果应用已经发起 HTTPS，请求中的加密 HTTP 消息就无法用于检查这些重试条件。

### 示例 3：与 Circuit Breaker 结合使用

`payment` 处理非幂等写入，因此此示例与前面的 `payment-service` 示例一样，按
方法拆分路由：读取会积极重试，写入会禁用 mesh 重试，以下 Circuit Breaker
则适用于两者。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: resilient-service
spec:
  hosts:
  - payment
  http:
  - name: reads-retryable
    match:
    - method:
        regex: "^(GET|HEAD)$"
    route:
    - destination:
        host: payment
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 3s
      retryOn: connect-failure,refused-stream
  - name: writes-no-mesh-retry
    match:
    - method:
        regex: "^(POST|PUT|PATCH|DELETE)$"
    route:
    - destination:
        host: payment
    timeout: 10s
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-circuit-breaker
spec:
  host: payment
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

<span id="important-warnings"></span>

## 重要警告

### 非幂等请求的重试风险

**核心原则**：对 POST/PATCH 和领域定义的非幂等写入进行自动 Istio Proxy 重试，可能导致**数据一致性问题**。只有在应用程序的真实契约保证幂等性时，才应将 PUT/DELETE 视为例外。

#### 问题场景

![POST 订单实际上已成功，但丢失的响应使 Istio proxy 自动重试，导致创建重复订单，而所有人都看到 200 OK。](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-05-retry-timeout-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-05-retry-timeout-1.html)

#### 为什么这很危险？

1. **重复创建**：POST 请求实际上已成功，但由于网络问题响应丢失，Proxy 重试会创建**重复记录**。
2. **错误的状态变更**：**支付、库存扣减**等业务关键操作可能会被执行多次。
3. **无法验证**：Istio Proxy 无法确认请求是否成功。

#### 安全的重试策略

**建议：禁用 mesh 重试并实施应用程序级去重**

```yaml
# Istio: explicitly do not retry a non-idempotent write
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: order-service
spec:
  hosts:
  - order-service
  http:
  - match:
    - method:
        exact: POST
    route:
    - destination:
        host: order-service
    timeout: 10s
    retries:
      attempts: 0  # No delivery after the original request
```

`reset`、`503` 和超时并不能证明服务器拒绝了请求。服务器可以提交数据库事务，然后仅丢失响应，因此 Proxy 无法确定重放是否安全。出现模糊结果后，应用程序应查询操作状态，而不是盲目地重新发送请求。

```python
# Client excerpt: requires an API with an atomic idempotency contract.
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def create_order_with_idempotency(order_data, idempotency_key):
    # Persist one key per logical order; reuse it after ambiguous failures.
    if not idempotency_key:
        raise ValueError("A persisted operation idempotency key is required")
    retries = Retry(
        total=3,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["POST"],
        backoff_factor=1,
    )
    with requests.Session() as session:
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        response = session.post(
            "http://order-service/orders",
            json=order_data,
            headers={"X-Idempotency-Key": idempotency_key},
            timeout=(3, 10),
        )
        response.raise_for_status()
        return response.json()
```

服务器必须以原子方式实施该契约。先执行 Redis `exists` 检查，再创建订单并单独写入缓存，会留下并发重复订单和崩溃时间窗；这不是安全的去重实现。

1. 验证幂等键，并将其绑定到经过身份验证的调用方和请求负载指纹。
2. 使用数据库唯一约束抢占该键；并发尝试必须串行化。
3. 在同一事务中提交订单变更以及该键对应的状态/响应。
4. 对相同键和负载返回已存储结果；若同一键被不同负载重复使用，则拒绝请求。
5. 通过事务型 outbox 或幂等下游 API 协调不可逆的外部副作用。保留时间应覆盖受支持的重试窗口。

客户端示例假定服务器已实现此契约。仅添加请求标头并不会让 POST 变得安全；Requests 的 timeout 作用于每次尝试的连接/读取阶段，而不是整个重试流程的总截止时间。

请为生产环境写入 API 组合使用以下保障措施：

- 使用由同一事务中数据库唯一约束支持的 `Idempotency-Key`
- 对更新使用 `ETag`/`If-Match` 或版本字段的 compare-and-swap
- 在超时/reset 后进行 transaction-ID 或 command-ID 状态查询
- 对支付或事件发布等不可逆下游影响使用 transactional outbox

#### HTTP 方法重试安全性

| 方法 | 幂等 | Istio 重试安全性 | 建议设置 |
|--------|------------|-------------------|---------------------|
| **GET** | 是 | 安全 | `attempts: 3, retryOn: 5xx,reset` |
| **HEAD** | 是 | 安全 | `attempts: 3, retryOn: 5xx,reset` |
| **OPTIONS** | 是 | 安全 | `attempts: 3, retryOn: 5xx,reset` |
| **PUT** | 取决于契约 | 谨慎 | 真实的幂等性契约 + 条件更新 |
| **DELETE** | 取决于契约 | 谨慎 | 真实的幂等性契约 + 结果查询 |
| **POST** | 通常不是 | 危险 | `attempts: 0`，Idempotency Key |
| **PATCH** | 通常不是 | 危险 | `attempts: 0`，版本/ETag |

#### 安全重试的情况

```yaml
# Read-only requests - safe
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-service-reads
spec:
  hosts:
  - api-service
  http:
  - match:
    - method:
        regex: "GET|HEAD|OPTIONS"
    route:
    - destination:
        host: api-service
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: 5xx,reset,connect-failure
```

```yaml
# Write requests with idempotency guaranteed
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: idempotent-writes
spec:
  hosts:
  - api-service
  http:
  - match:
    - method:
        exact: PUT
      headers:
        x-idempotency-key:
          regex: ".+"  # Only when Idempotency Key present
    route:
    - destination:
        host: api-service
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: 5xx,reset
```

#### 与 Circuit Breaker 配合使用时的注意事项

Circuit Breaker 对于**故障隔离**很有效，但它**无法阻止**非幂等请求的重复执行。

```yaml
# Bad example: POST + Circuit Breaker + Retry
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-service
spec:
  hosts:
  - payment-service
  http:
  - route:
    - destination:
        host: payment-service
    retries:
      attempts: 3  # 3 retries for POST is dangerous
      retryOn: 5xx
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-circuit-breaker
spec:
  host: payment-service
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      baseEjectionTime: 30s

# Result: Before the Circuit Breaker opens,
# duplicate payments can occur 3 times!
```

```yaml
# Good example: Use Circuit Breaker only, retry at application level
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-service
spec:
  hosts:
  - payment-service
  http:
  - route:
    - destination:
        host: payment-service
    timeout: 10s
    retries:
      attempts: 0  # Completely disable retry
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-circuit-breaker
spec:
  host: payment-service
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      baseEjectionTime: 30s
```

#### 实用指南

1. **GET/HEAD/OPTIONS**：可以使用 Istio Proxy Retry
2. **POST/PATCH**：禁用 Istio Retry，使用应用程序级 Retry + Idempotency Key
3. **PUT/DELETE**：仅在保证幂等性时使用 Istio Retry
4. **关键操作（支付/库存/积分）**：必须具备应用程序级验证 + Idempotency Key

<span id="best-practices"></span>

## 最佳实践

### 1. 超时配置指南

```yaml
# Good example: Appropriate timeout per layer
# Frontend: 15s
# API Gateway: 10s
# Backend Service: 5s
# Database: 3s

apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-gateway
spec:
  hosts:
  - api-gateway
  http:
  - route:
    - destination:
        host: api-gateway
    timeout: 10s
    retries:
      attempts: 2
      perTryTimeout: 4s
```

```yaml
# Bad example: Timeout too long
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-gateway
spec:
  hosts:
  - api-gateway
  http:
  - route:
    - destination:
        host: api-gateway
    timeout: 300s  # Illustrative poor fit for a short interactive request; streaming differs
```

### 2. 重试策略

```yaml
# Good example: Consider idempotency
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-service
spec:
  hosts:
  - api-service
  http:
  # GET - safe to retry
  - match:
    - method:
        exact: GET
    route:
    - destination:
        host: api-service
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: 5xx,reset,connect-failure

  # POST/PATCH - explicitly disable mesh retry
  - match:
    - method:
        regex: "^(POST|PUT|PATCH|DELETE)$"
    route:
    - destination:
        host: api-service
    retries:
      attempts: 0
```

### 3. 指数退避

Envoy 使用完全抖动的指数退避，默认基准间隔为 25ms；实际延迟不是固定的 25/50/100ms 序列。此示例为读取请求设置自定义基准，并明确禁用写入路径的重试：

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: backoff-retry
spec:
  hosts:
  - payment
  http:
  - match:
    - method:
        regex: "^(GET|HEAD)$"
    route:
    - destination:
        host: payment
    retries:
      attempts: 5
      perTryTimeout: 2s
      retryOn: connect-failure,refused-stream
      backoff: 100ms
  - route:
    - destination:
        host: payment
    retries:
      attempts: 0
```

### 4. 系统总超时计算

```yaml
# Frontend → API Gateway → Backend → Database
# Frontend: 20s
# API Gateway: 15s (must be less than Frontend)
# Backend: 10s (must be less than API Gateway)
# Database: 5s (must be less than Backend)

# Each layer should consider downstream timeout + overhead
```

<span id="troubleshooting"></span>

## 故障排除

### 超时未生效

```bash
# 1. Check VirtualService
kubectl get virtualservice -n <namespace>
kubectl describe virtualservice <name> -n <namespace>

# 2. Check Envoy configuration
istioctl proxy-config routes <pod-name> -n <namespace> -o json | grep timeout

# 3. Test actual timeout
kubectl exec -it <pod-name> -n <namespace> -c <app-container> -- \
  curl -v --max-time 15 http://backend-service
```

### 重试次数过多

请从安装了 curl 的应用容器生成流量，不要以 istio-proxy UID 发起测试（该 UID 可能绕过拦截）。为该测试设置高于路由配置超时的 curl 截止时间。使用由代理 stats matcher 启用的 Envoy 重试计数器测量重试；`UR` 响应标志表示上游远端重置，不是重试计数器。

```promql
sum(rate(envoy_cluster_upstream_rq_retry[5m]))
```

### 防止重试风暴

```yaml
# Use with Circuit Breaker
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: prevent-retry-storm
spec:
  host: backend
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 10  # Limit pending requests
        http2MaxRequests: 100
        maxRequestsPerConnection: 1
    outlierDetection:
      consecutive5xxErrors: 3  # Fast circuit break
      interval: 10s
      baseEjectionTime: 30s
```

## 参考资料

- [Istio Timeout](https://istio.io/latest/docs/reference/config/networking/virtual-service/#HTTPRoute)
- [Istio Retry](https://istio.io/latest/docs/reference/config/networking/virtual-service/#HTTPRetry)
- [Envoy Retry Policy](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/router_filter#config-http-filters-router-x-envoy-retry-on)
- [RFC 9110: Idempotent Methods](https://www.rfc-editor.org/rfc/rfc9110.html#name-idempotent-methods)
- [主要参考资料 1](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [主要参考资料 2](https://raw.githubusercontent.com/istio/istio/1.31.0/pilot/pkg/networking/core/route/retry/retry.go)
- [主要参考资料 3](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/router_filter)
- [主要参考资料 4](https://www.rfc-editor.org/rfc/rfc9110.html#name-idempotent-methods)
- [主要参考资料 5](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
- [主要参考资料 6](https://raw.githubusercontent.com/psf/requests/main/docs/user/advanced.rst)
- [主要参考资料 7](https://raw.githubusercontent.com/urllib3/urllib3/main/src/urllib3/util/retry.py)
- [主要参考资料 8](https://istio.io/latest/docs/tasks/traffic-management/egress/egress-tls-origination/)

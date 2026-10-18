# 故障注入

故障注入是通过有意引入故障来检验系统韧性的技术。

## 目录

1. [为什么要进行故障注入？](#why-fault-injection)
2. [何时使用故障注入](#when-to-use-fault-injection)
3. [故障注入概述](#fault-injection-overview)
4. [延迟注入](#delay-injection)
5. [中止注入](#abort-injection)
6. [实用示例](#practical-examples)
7. [真实场景](#real-world-scenarios)
8. [测试策略](#testing-strategies)
9. [最佳实践](#best-practices)

以下示例是在 HTTP 层实施的不同实验。请从隔离的命名空间开始，保留完整的无故障路由配置，并在安排测试前定义独立的清理路径。百分比适用于匹配的请求，而不是 Pod 的百分比。测试方标头不等于身份验证，且必须传递到目标下游调用。原生 SQL/TCP、丢包、Pod 就绪状态和节点故障需要采用不同的测试方式。

<span id="why-fault-injection"></span>

## 为什么要进行故障注入？

### 在生产环境中测试韧性

在微服务架构中，众多服务相互依赖，**单个服务发生故障就可能影响整个系统**。故障注入之所以重要，原因如下：

#### 1. **混沌工程的核心原则**

混沌工程因 Netflix 的 Chaos Monkey 等实践而广为人知，其目标是在生产环境中**主动体验故障**并发现系统弱点。

![传统测试从开发和预发布环境进入生产故障；混沌工程则持续注入故障以发现弱点、主动修复，并逐步提高系统韧性。](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-08-fault-injection-0.png)

[🔍 查看交互式图示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-08-fault-injection-0.html)

#### 2. **复现真实生产场景**

生产环境中可能发生以下问题：

| 场景 | 原因 | 故障注入测试 |
|----------|-------|---------------------|
| **网络延迟** | 跨区域网络延迟 | 延迟注入 |
| **服务超时** | 数据库查询缓慢 | 延迟注入 |
| **暂时性故障** | 服务重启、缩容 | 中止注入 |
| **部分故障** | 只有部分 Pod 发生故障 | 按百分比注入 |
| **级联故障** | 一个服务的故障传播到其他服务 | 组合故障注入 |

#### 3. **验证断路器和超时设置**

故障注入可测试调用方如何处理延迟和错误。若要测试代理重试/超时或端点剔除，必须在这些机制能够观测到的层级产生故障。

应将调用方行为与代理剔除分别验证：本地注入的中止发生在上游请求发送前，不代表上游端点发生故障。订单服务实际返回的响应决定其调用方观察到的结果。

#### 4. **验证安全发布**

部署新版本时，可以检验**依赖服务发生故障时新版本是否仍能安全运行**：

- 新版本能否正确处理超时？
- 依赖服务发生故障时，能否执行优雅降级？
- 错误处理逻辑是否正常工作？

<span id="when-to-use-fault-injection"></span>

## 何时使用故障注入

可在以下情形使用故障注入：

### 1. **开发和测试环境**

#### 场景：开发新的微服务

```yaml
# Inject faults into service under development
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-service-dev
  namespace: dev
spec:
  hosts:
  - payment-service
  http:
  - match:
    - headers:
        x-testing:
          exact: "true"  # Apply only to test traffic
    fault:
      delay:
        percentage:
          value: 50.0
        fixedDelay: 3s
      abort:
        percentage:
          value: 20.0
        httpStatus: 503
    route:
    - destination:
        host: payment-service
        subset: v2
  - route:
    - destination:
        host: payment-service
```

**使用场景**：
- 测试订单服务在支付服务变慢或发生故障时如何响应
- 验证是否向用户显示适当的错误消息

### 2. **预发布环境中的集成测试**

#### 场景：生产部署前的最终验证

```yaml
# Inject random faults into all dependent services
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: database-service-staging
spec:
  hosts:
  - database-service
  http:
  - fault:
      delay:
        percentage:
          value: 10.0  # 10% of requests delayed
        fixedDelay: 5s
      abort:
        percentage:
          value: 5.0   # 5% of requests fail
        httpStatus: 500
    route:
    - destination:
        host: database-service
```

**使用场景**：
- 在生产部署前验证整个系统的韧性
- 确认监控告警能够正常工作

### 3. **生产环境中的混沌测试**

#### 场景：定期进行生产韧性测试

```yaml
# Inject faults at very low rate in production
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: recommendation-service-prod
spec:
  hosts:
  - recommendation-service
  http:
  - match:
    - headers:
        x-canary:
          exact: "true"  # Apply only to canary users
    fault:
      abort:
        percentage:
          value: 1.0  # Only 1% of requests fail
        httpStatus: 503
    route:
    - destination:
        host: recommendation-service
  - route:
    - destination:
        host: recommendation-service
```

**使用场景**：
- 开展 Netflix 风格的混沌工程
- 验证生产环境实际处理故障的能力
- **注意**：从极低的故障比例（1–5%）开始，并监控影响

### 4. **调整超时和重试策略**

启用故障注入时，Istio 不会在同一条客户端路由上启用超时/重试处理。下方有意移除了路由超时；此测试中的调用方必须自行执行期限限制。

#### 场景：寻找合适的超时值

```yaml
# Test with various delay times
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: search-service-timeout-test
spec:
  hosts:
  - search-service
  http:
  - match:
    - headers:
        x-test-scenario:
          exact: "slow-response"
    fault:
      delay:
        percentage:
          value: 100.0
        fixedDelay: 10s  # 10 second delay
    route:
    - destination:
        host: search-service
  - route:
    - destination:
        host: search-service
```

**使用场景**：
- 测试应用/客户端的 5 秒期限是否能在代理注入 10 秒延迟时发挥作用
- 若要测试 Istio 路由超时，应使用确实缓慢的上游，或在不同的跳点注入故障
- 找到不会损害用户体验的合适值

### 5. **验证异常检测**

本地故障中止会在发送上游请求前返回，因此不会触发该代理针对每个端点的连续错误检测器。应使用确实返回 503 的受控 HTTP 后端，然后观察端点是否被剔除。例如，在测试命名空间部署 Istio httpbin 示例后：

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: httpbin-outlier-test
spec:
  host: httpbin
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 5s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

从网格内的应用客户端向 `http://httpbin:8000/status/503` 发送请求。这会有意导致所有测试端点均可能被剔除。恢复取决于剔除历史和后续健康状况，并不保证在固定的 30 秒内完成。不要将此配置用于无关工作负载。

### 6. **针对特定用户组进行测试**

#### 场景：仅为 Beta 测试人员注入故障

```yaml
# Inject faults only for specific users
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-service-beta
spec:
  hosts:
  - api-service
  http:
  - match:
    - headers:
        end-user:
          exact: "beta-tester"  # Beta testers only
    fault:
      delay:
        percentage:
          value: 20.0
        fixedDelay: 2s
    route:
    - destination:
        host: api-service
  - route:  # Normal routing for regular users
    - destination:
        host: api-service
```

**使用场景**：
- 在不影响真实用户的情况下安全测试
- 根据 Beta 测试人员的反馈改进

<span id="fault-injection-overview"></span>

## 故障注入概述

![客户端请求可以在故障注入区域中延迟 3 秒后再缓慢到达服务，也可以被中止，并直接向客户端返回 HTTP 503 错误。](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-08-fault-injection-2.png)

[🔍 查看交互式图示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-08-fault-injection-2.html)

<span id="delay-injection"></span>

## 延迟注入

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-delay
spec:
  hosts:
  - reviews
  http:
  - fault:
      delay:
        percentage:
          value: 10.0  # Inject delay in 10% of requests
        fixedDelay: 5s  # 5 second delay
    route:
    - destination:
        host: reviews
```

<span id="abort-injection"></span>

## 中止注入

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-abort
spec:
  hosts:
  - reviews
  http:
  - fault:
      abort:
        percentage:
          value: 10.0  # Abort 10% of requests
        httpStatus: 503  # Return HTTP 503 error
    route:
    - destination:
        host: reviews
```

<span id="practical-examples"></span>

## 实用示例

### 1. 组合延迟和中止

在真实生产环境中，延迟与故障可能同时发生：

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: ratings-combined-fault
spec:
  hosts:
  - ratings
  http:
  - fault:
      delay:
        percentage:
          value: 20.0  # 20% of requests delayed
        fixedDelay: 3s
      abort:
        percentage:
          value: 10.0  # 10% of requests fail
        httpStatus: 503
    route:
    - destination:
        host: ratings
```

**结果**：
- 20% 的请求会延迟 3 秒
- 中止注入可与延迟重叠，因此部分中止的请求会先经历延迟
- 不要将两种百分比直接相加并视为互不重叠的请求群体；应实际测量重叠情况

### 2. 条件性故障注入

仅在特定条件下注入故障：

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-conditional-fault
spec:
  hosts:
  - reviews
  http:
  # Inject faults only for mobile users
  - match:
    - headers:
        user-agent:
          regex: ".*Mobile.*"
    fault:
      delay:
        percentage:
          value: 30.0
        fixedDelay: 2s
    route:
    - destination:
        host: reviews
        subset: v2
  # Normal routing for regular users
  - route:
    - destination:
        host: reviews
        subset: v1
```

### 3. 渐进式故障注入

逐步提高故障比例进行测试：

```yaml
# Stage 1: 5% faults
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-fault
spec:
  hosts:
  - api-service
  http:
  - fault:
      abort:
        percentage:
          value: 5.0
        httpStatus: 500
    route:
    - destination:
        host: api-service
```

```yaml
# Stage 2: 10% faults (apply after monitoring)
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-fault
spec:
  hosts:
  - api-service
  http:
  - fault:
      abort:
        percentage:
          value: 10.0
        httpStatus: 500
    route:
    - destination:
        host: api-service
```

```yaml
# Stage 3: 20% faults (apply after sufficient validation)
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-fault
spec:
  hosts:
  - api-service
  http:
  - fault:
      abort:
        percentage:
          value: 20.0
        httpStatus: 500
    route:
    - destination:
        host: api-service
```

### 4. 按 HTTP 状态码测试

使用不同的 HTTP 错误状态码进行测试：

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-error-scenarios
spec:
  hosts:
  - payment-service
  http:
  # Scenario 1: Service overload (503)
  - match:
    - headers:
        x-test-scenario:
          exact: "overload"
    fault:
      abort:
        percentage:
          value: 50.0
        httpStatus: 503
    route:
    - destination:
        host: payment-service
  # Scenario 2: Internal server error (500)
  - match:
    - headers:
        x-test-scenario:
          exact: "server-error"
    fault:
      abort:
        percentage:
          value: 30.0
        httpStatus: 500
    route:
    - destination:
        host: payment-service
  # Scenario 3: Gateway timeout (504)
  - match:
    - headers:
        x-test-scenario:
          exact: "timeout"
    fault:
      abort:
        percentage:
          value: 20.0
        httpStatus: 504
    route:
    - destination:
        host: payment-service
  # Default routing
  - route:
    - destination:
        host: payment-service
```

<span id="real-world-scenarios"></span>

## 真实场景

### 场景 1：模拟缓慢的 HTTP 数据库代理

**情况**：数据库查询间歇性变慢

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: database-slow-query
  namespace: chaos-tests
spec:
  hosts:
  - database-service
  http:
  - fault:
      delay:
        percentage:
          value: 15.0  # 15% of HTTP requests are delayed
        fixedDelay: 8s   # 8 second delay
    route:
    - destination:
        host: database-service
```

**测试目标**：
1. 应用超时设置是否合适？
2. 连接池是否会耗尽？
3. 是否向用户显示适当的错误消息？

**预期结果**：
- 合适的超时设置可实现快速失败
- 连接池正常管理
- 若整个系统的响应均变慢，则可能需要断路器

### 场景 2：测试微服务级联故障

**情况**：验证一个服务的故障是否会传播到其他服务

应将调用方行为与代理剔除分别验证：本地注入的中止发生在上游请求发送前，不代表上游端点发生故障。订单服务实际返回的响应决定其调用方观察到的结果。

```yaml
# Inject faults into payment service
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-cascade-test
spec:
  hosts:
  - payment-service
  http:
  - fault:
      abort:
        percentage:
          value: 30.0  # 30% failure
        httpStatus: 503
    route:
    - destination:
        host: payment-service
---
# Configure Circuit Breaker for order service
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: order-circuit-breaker
spec:
  host: order-service
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

**测试目标**：
1. 订单服务能否优雅处理支付失败？
2. 订单服务能否保持面向调用方的响应行为？端点是否被剔除取决于订单服务实际返回的错误。
3. 前端是否向用户显示适当的消息？

### 场景 3：测试 API 速率限制

**情况**：模拟外部 API 达到速率限制

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-api-rate-limit
spec:
  hosts:
  - external-api-service
  http:
  - match:
    - headers:
        x-api-key:
          exact: "test-key"
    fault:
      abort:
        percentage:
          value: 40.0  # 40% of requests rate limited
        httpStatus: 429  # Too Many Requests
    route:
    - destination:
        host: external-api-service
  - route:
    - destination:
        host: external-api-service
```

**测试目标**：
1. 是否适当地处理了 429 错误？
2. 重试逻辑是否使用指数退避？
3. 是否使用缓存减少 API 调用？

### 场景 4：模拟跨区域网络延迟

**情况**：调用不同区域中的服务时产生延迟

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: cross-region-latency
spec:
  hosts:
  - us-east-service
  http:
  - match:
    - sourceLabels:
        region: "eu-west"  # Calling from EU to US
    fault:
      delay:
        percentage:
          value: 100.0
        fixedDelay: 150ms  # 150ms delay (transatlantic)
    route:
    - destination:
        host: us-east-service
  - route:
    - destination:
        host: us-east-service
```

**测试目标**：
1. 确认跨区域延迟对全球服务的影响
2. 确定能否通过缓存或 CDN 优化
3. 是否达到 SLA 目标（例如，95% 的请求在 500 毫秒内完成）？

### 场景 5：模拟发布期间的暂时性故障

**情况**：滚动更新期间部分 Pod 暂时不可用

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: deployment-transient-failure
spec:
  hosts:
  - app-service
  http:
  - match:
    - headers:
        x-deployment-test:
          exact: "true"
    fault:
      abort:
        percentage:
          value: 25.0  # 25% of matching requests fail; Pods remain running
        httpStatus: 503
      delay:
        percentage:
          value: 10.0
        fixedDelay: 5s   # Some start slowly
    route:
    - destination:
        host: app-service
        subset: v2
  - route:
    - destination:
        host: app-service
```

**测试目标**：
1. 测量调用方在注入请求错误时的行为
2. 使用受控的工作负载状态变更，单独测试就绪状态
3. 单独验证是否路由到健康端点；HTTP 中止不会令 Pod 变为未就绪

<span id="testing-strategies"></span>

## 测试策略

### 1. 渐进式混沌工程

逐步提高故障比例以发现系统极限：

![故障注入比例从 1% 逐步升至 50% 的四个阶段；只有监控无异常时才进入下一阶段，发现问题时则回到统一的修复和改进步骤。](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-08-fault-injection-4.png)

[🔍 查看交互式图示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-08-fault-injection-4.html)

**分步执行**：

```bash
# Stage 1: 1% fault injection
kubectl apply -f fault-injection-1percent.yaml
# Monitor for 15 minutes
kubectl logs -f deployment/monitoring

# If no issues, proceed to stage 2
kubectl apply -f fault-injection-5percent.yaml
# Monitor for 15 minutes

# Continue...
```

### 2. 按时间安排测试

这是一个调度模板；在准备好先决条件前，它会保持挂起状态：测试命名空间、包含 shell 和兼容 kubectl 的组织自有 runner 镜像（已构建并固定版本）、仅具备访问预先创建的同一 VirtualService 所需权限的现有 `chaos-tester` ServiceAccount，以及含有该资源完整故障/无故障清单的 `chaos-fixtures` ConfigMap。示例中的 registry 镜像只是占位符。遭遇 SIGKILL 或节点丢失后，trap 无法运行；请另行安排独立的清理检查。

仅在特定时间段内注入故障：

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: fault-injection-scheduler
  namespace: chaos-tests
spec:
  schedule: "0 2 * * *"
  timeZone: "Etc/UTC"
  suspend: true
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 300
  jobTemplate:
    spec:
      activeDeadlineSeconds: 420
      backoffLimit: 0
      template:
        metadata:
          labels:
            sidecar.istio.io/inject: "false"
        spec:
          serviceAccountName: chaos-tester
          restartPolicy: Never
          containers:
          - name: apply-fault
            image: registry.example.com/ops/chaos-runner:1.0.0
            command: ["/bin/sh", "-ec"]
            args:
            - |
              cleanup() { kubectl apply -n chaos-tests -f /config/no-fault.yaml; }
              trap cleanup EXIT
              trap 'exit 130' INT
              trap 'exit 143' TERM
              kubectl apply -n chaos-tests -f /config/fault-injection.yaml
              sleep 300
            volumeMounts:
            - name: fixtures
              mountPath: /config
              readOnly: true
          volumes:
          - name: fixtures
            configMap:
              name: chaos-fixtures
```

### 3. 自动化测试流水线

将测试集成到 CI/CD 流水线：

```yaml
stages: [fault-injection-test]

fault_injection_test:
  stage: fault-injection-test
  script:
    - kubectl apply -n chaos-tests -f tests/fault-injection.yaml
    - k6 run --vus 100 --duration 5m tests/load-test.js
    - ./tests/check-fault-metrics.sh
  after_script:
    - kubectl apply -n chaos-tests -f tests/no-fault.yaml
```

将以下内容保存为测试项目中的 `tests/check-fault-metrics.sh`。Runner 需要 kubectl、k6、curl 和 jq，以及已审核的清单/负载测试。应根据测试假设选择要测量的服务和阈值：有意注入到依赖项的错误并不自动等于用户侧 SLO 失败。响应缺失或为 NaN 时检查应失败。GitLab 的 after_script 不保证在 Runner 丢失后仍会运行，且有自己的超时；应独立验证基线是否恢复。

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${PROMETHEUS_URL:?Set the Prometheus base URL}"
: "${TEST_DESTINATION:?Set the exact destination_service label}"
: "${ERROR_THRESHOLD:?Set the error-fraction limit for the hypothesis}"
QUERY="sum(rate(istio_requests_total{reporter=\"source\",destination_service=\"${TEST_DESTINATION}\",response_code=~\"5..\"}[5m])) / sum(rate(istio_requests_total{reporter=\"source\",destination_service=\"${TEST_DESTINATION}\"}[5m]))"
curl -fsSG "$PROMETHEUS_URL/api/v1/query" --data-urlencode "query=$QUERY" |
  jq -e --argjson limit "$ERROR_THRESHOLD" '
    .status == "success" and
    (.data.result | length) == 1 and
    (.data.result[0].value[1] as $v |
      $v != "NaN" and $v != "+Inf" and $v != "-Inf" and
      (($v | tonumber) <= $limit))'
```

### 4. 监控和告警

将此规则文件挂载到 Prometheus，或使用已安装 Operator 的 PrometheusRule 资源。仅有 ConfigMap 不会启用告警。规则应限定于测试服务，并启用所引用的 Envoy 统计项。

故障注入期间监控关键指标：

```yaml
# Prometheus alert rules
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-alerts
data:
  fault-injection-alerts.yaml: |
    groups:
    - name: fault-injection
      rules:
      # Error rate increase
      - alert: HighErrorRate
        expr: sum by (destination_service) (rate(istio_requests_total{reporter="source",response_code=~"5.."}[5m])) / sum by (destination_service) (rate(istio_requests_total{reporter="source"}[5m])) > 0.1
        for: 2m
        annotations:
          summary: "High error rate during fault injection"

      # Circuit Breaker activation
      - alert: CircuitBreakerOpen
        expr: envoy_cluster_circuit_breakers_default_rq_open > 0
        for: 1m
        annotations:
          summary: "Circuit breaker opened"

      # Response time increase
      - alert: HighLatency
        expr: histogram_quantile(0.95, sum by (destination_service, le) (rate(istio_request_duration_milliseconds_bucket{reporter="source"}[5m]))) > 3000
        for: 5m
        annotations:
          summary: "95th percentile latency > 3s"
```

### 5. 蓝绿故障注入

在 Blue 环境注入故障，并与 Green 环境进行比较：

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: app-blue-green-test
spec:
  hosts:
  - app-service
  http:
  - match:
    - headers:
        x-version:
          exact: "blue"
    fault:
      delay:
        percentage:
          value: 20.0
        fixedDelay: 3s
    route:
    - destination:
        host: app-service
        subset: blue
  - route:
    - destination:
        host: app-service
        subset: green
```

**比较指标**：
- 错误率
- 响应时间（P50、P95、P99）
- 用户体验指标

<span id="best-practices"></span>

## 最佳实践

### 1. 从小规模开始

- 初始时**从 1–5% 的低比例开始**
- 在开发/预发布环境中充分测试
- 在业务影响较低的时段于生产环境执行

### 2. 监控至关重要

应用故障注入前准备好监控仪表板：

```yaml
# Grafana dashboard metrics
- istio_requests_total (Error rate)
- istio_request_duration_milliseconds (Latency)
- envoy_cluster_upstream_rq_retry (Retry count)
- envoy_cluster_circuit_breakers_* (Circuit Breaker status)
```

### 3. 使用清晰的标签

```yaml
# Metadata excerpt for the existing reviewed fault VirtualService
metadata:
  name: payment-fault
  labels:
    fault-injection: "true"
    test-type: "chaos-engineering"
    test-date: "2025-01-15"
  annotations:
    description: "Testing payment service resilience"
    owner: "platform-team"
```

### 4. 自动回滚机制

```bash
#!/usr/bin/env bash
set -euo pipefail
cleanup() { kubectl apply -n chaos-tests -f tests/no-fault.yaml; }
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
kubectl apply -n chaos-tests -f tests/fault-injection.yaml
sleep 300
./tests/check-fault-metrics.sh
# EXIT restores the full baseline on success or normal failure.
```

### 5. 文档记录

记录所有故障注入测试：

```yaml
# Metadata excerpt for the existing reviewed fault VirtualService
metadata:
  name: api-fault-test
  annotations:
    # Test purpose
    test-purpose: "Verify caller error handling; test upstream ejection separately"

    # Expected behavior
    expected-behavior: |
      - Caller handles the injected error according to the test hypothesis
      - Requests fail fast with 503 error
      - Restore baseline and verify recovery

    # Success criteria
    success-criteria: |
      - Error rate < 5%
      - P95 latency < 500ms
      - No cascading failures

    # Rollback plan
    rollback-plan: "Restore the reviewed complete no-fault VirtualService"
```

### 6. 生产环境注意事项

- **评估业务影响**：分析故障注入对真实用户的影响
- **逐步扩大范围**：缓慢地从 1% 提高到 5%、再到 10%
- **设置告警**：超出阈值时立即告警
- **准备回滚**：随时准备立即回滚
- **避开业务高峰期**：选择流量较低的时段

### 7. 定期测试

```bash
# Change the prepared scheduler to weekly; suspension/prerequisites still apply
kubectl patch cronjob fault-injection-scheduler -n chaos-tests --type=merge \
  -p '{"spec":{"schedule":"0 3 * * 0","timeZone":"Etc/UTC"}}'
```

## 参考资料

- [Istio 故障注入](https://istio.io/latest/docs/tasks/traffic-management/fault-injection/)
- [混沌工程原则](https://principlesofchaos.org/)
- [Netflix 混沌工程](https://netflix.github.io/chaosmonkey/)
- [Google SRE：可靠性测试](https://sre.google/sre-book/testing-reliability/)

- [主要参考资料 1](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [主要参考资料 2](https://istio.io/latest/docs/tasks/traffic-management/fault-injection/)
- [主要参考资料 3](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/fault_filter)
- [主要参考资料 4](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/outlier)
- [主要参考资料 5](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/)
- [主要参考资料 6](https://docs.gitlab.com/ci/yaml/)
- [主要参考资料 7](https://raw.githubusercontent.com/prometheus/prometheus/v3.14.0/docs/configuration/configuration.md)

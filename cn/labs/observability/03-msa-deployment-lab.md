# 第 3 部分：MSA 部署和金丝雀发布

<span id="application-structure"></span>
<span id="architecture-overview"></span>
<span id="canary-state-diagram"></span>
<span id="cleanup"></span>
<span id="exercise-1-msa-application-overview"></span>
<span id="exercise-2-karpenter-nodepool-configuration"></span>
<span id="exercise-3-keda-scaledobject-configuration"></span>
<span id="exercise-4-argocd-application-deployment"></span>
<span id="exercise-5-opentelemetry-auto-instrumentation"></span>
<span id="exercise-6-argo-rollouts-canary-deployment"></span>
<span id="exercise-7-intentional-failure-and-automatic-rollback"></span>
<span id="learning-objectives"></span>
<span id="next-steps"></span>
<span id="prerequisites"></span>
<span id="references"></span>
<span id="repository-structure"></span>
<span id="sample-code-snippets"></span>
<span id="service-call-flow"></span>
<span id="steps"></span>
<span id="steps-1"></span>
<span id="steps-2"></span>
<span id="steps-3"></span>
<span id="steps-4"></span>
<span id="steps-5"></span>
<span id="summary"></span>
<span id="troubleshooting"></span>
<span id="verification"></span>
<span id="verification-1"></span>
<span id="verification-2"></span>
<span id="verification-3"></span>
<span id="verification-4"></span>
<span id="verification-5"></span>

> **难度**：高级
> **最后更新**：September 13, 2026
将五个可运行的 Python 角色部署为独立工作负载。 [应用 README](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/labs/observability/application)定义了代码、DB、镜像和 chart 输入。支付和通知均为模拟操作；不会实际扣费或发送电子邮件/SMS。

![独立工作负载、事务性 outbox、SNS 扇出和消费者](../../.gitbook/assets/en-labs-observability-03-msa-deployment-lab-10.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-03-msa-deployment-lab-10.html)

## 1. 共享 API 和持久化契约 {#contracts}

| 请求/角色 | 契约 |
|---|---|
| `POST /orders` | 201 + `id`；订单和 outbox 一起提交 |
| `POST /payments` | 200 + `status: completed`；相同订单/金额/方法具有幂等性 |
| `GET /orders/{id}` | 200 + 相同 ID，或404 |
| `notification` | 自有 SQS 队列，持久化的模拟通知 |
| `analytics` | 独立 SQS 队列，独立持久化的结果 |

W3C 上下文会跨越 gateway/service HTTP 以及 producer/consumer 边界。在 outbox 发布后但 DB 标记前发生崩溃会导致重新投递，因此消费者会以事务方式去重事件 ID。这并不能使外部电子邮件/支付效果实现恰好一次。未包含针对订单 POST 的通用 Idempotency-Key 处理。

应用指标为 `lab_http_requests_total` 和 `lab_http_request_duration_seconds`，按 service/route/status/revision 添加标签。JSON 日志包含 service/level/trace_id/span_id；客户/支付载荷不是指标标签。

## 2. 数据库文件和镜像 {#image-database}

使用第 1 部分的专用运行时账户/私有连接文件。Pod 路径为 `/run/database-ca/global-bundle.pem` 和 `/run/database/connection.json`；将连接文件和公共 RDS CA 分别挂载为 Secret/ConfigMap。

```bash
cd examples/labs/observability/application
kubectl --context service create namespace msa --dry-run=client -o yaml | kubectl --context service apply -f -
kubectl --context service -n msa create secret generic lab-database --from-file=connection.json="$LAB_STATE/runtime-pod-connection.json"
kubectl --context service -n msa create configmap lab-database-ca --from-file=global-bundle.pem="$LAB_STATE/global-bundle.pem"
docker buildx build --platform linux/amd64 \
  --tag "$IMAGE_REPOSITORY:$IMAGE_TAG" --push .
docker buildx imagetools inspect "$IMAGE_REPOSITORY:$IMAGE_TAG"
```
使用第 1 部分选定的不可变版本。按照组织的轮换流程更新现有 Secret，不要打印其值，也不要将其放入 chart 文件。Dockerfile 固定了基础 digest、UID10001 和受限的构建上下文。

生成的 `m6i.large` 节点使用 AMD64。请使用 AMD64 或支持跨平台的 Buildx builder，并在部署前确认推送的 manifest 中包含 `linux/amd64`。审计中的本地 ARM64 smoke test 不验证 AMD64 构建。

## 3. 安装 controller 和 chart {#deployment}

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo add argo https://argoproj.github.io/argo-helm
helm upgrade --install keda kedacore/keda --version 2.20.2   --kube-context service -n keda --create-namespace -f "$LAB_STATE/helm-inputs/keda.yaml"
helm upgrade --install argo-rollouts argo/argo-rollouts --version 2.43.1   --kube-context service -n argo-rollouts --create-namespace
helm upgrade --install observability-lab ./chart --kube-context service -n msa   -f "$LAB_STATE/helm-inputs/application.yaml"
kubectl --context service -n msa get deployment,rollout,pods,svc,scaledobject
```
验证全部五个 ServiceAccount 和 IRSA subject。Gateway 没有 AWS role；publisher 访问 SNS，consumer 访问各自的队列，KEDA 仅访问队列属性。不要为一个工作负载配置重复的 Pod Identity/IRSA 路径。Readiness 检查 DB/schema，而不是成功的 SQS/IAM 投递。

ServiceMonitor 标签与 service Prometheus release 匹配，且 `honorLabels` 保留应用 service 标签。托管 node group 可以运行基线；仅在其[单独指南](../../autoscaling/02-karpenter.md)验证 IAM/discovery/EC2NodeClass/AMI/taints 后再添加 Karpenter。

![跨 management/service 范围的部署和可观测性](../../.gitbook/assets/en-labs-observability-03-msa-deployment-lab-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-03-msa-deployment-lab-0.html)

## 4. 验证 HTTP 和异步处理 {#verify}

```bash
kubectl --context service -n msa port-forward svc/api-gateway 8080:8080
# Run in another terminal from the repository root:
BASE_URL=http://127.0.0.1:8080 LOAD_PROFILE=smoke   k6 run --no-usage-report examples/labs/observability/load-test/k6-scenario.js
```
仅读取已创建的 ID，并验证模拟支付状态。验证独立队列投递以及持续增长的 consumer `/stats`/DB 计数/日志。通知和分析使用独立队列；同一队列上的竞争 consumer 不会实现扇出。失败/有毒消息保持未确认状态，以遵循 DLQ 策略。

对比 CloudWatch/Loki JSON trace_id、实际 Tempo span 和 Prometheus exemplar ID。安装 collector 并不等同于端到端验证。

## 5. 金丝雀发布和 GitOps 所有权 {#canary}


![手动检查、仅金丝雀分析、晋级或中止](../../.gitbook/assets/en-labs-observability-03-msa-deployment-lab-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-03-msa-deployment-lab-1.html)
单个 Rollout 管理 payment-service。使用五个副本时，20% 步骤基于副本数，并不保证实际请求的20%。在分析前的手动暂停期间，向新 revision 生成流量。查询选择 `rollouts-pod-template-hash`，要求至少五个近期请求和99%成功率，并拒绝空/NaN/Inf/多序列结果。

已测试实际的 Rollouts1.10.0 条件评估和 PromQL，但未执行 cluster 晋级。中止并不是 Git revert 或所需镜像恢复。对于可选的 ArgoCD，请遵循其[安装指南](../../gitops/argocd/01-installation.md)，指向本仓库实际的 chart 路径/已审核 revision，并避免同时由直接 Helm 管理。请引用现有 Secret，而不是提交它们。仅凭 app-of-apps sync wave 并不能保证子项就绪。

### 执行手动暂停

这些步骤使用 Helm 作为所需状态所有者。在 GitOps 下，请在 Git 中审核镜像更改和恢复，不要混用直接 Helm 写入。检查 [Argo Rollouts 1.10.0 release](https://github.com/argoproj/argo-rollouts/releases/tag/v1.10.0)二进制文件和校验和后，安装匹配的 OS/CPU plugin。

```bash
# ROLLOUTS_BINARY: checksum-verified binary for your OS/architecture.
: "${ROLLOUTS_BINARY:?Set the verified Argo Rollouts 1.10.0 binary path}"
mkdir -p "$HOME/.local/bin"
install -m 755 "$ROLLOUTS_BINARY" "$HOME/.local/bin/kubectl-argo-rollouts"
export PATH="$HOME/.local/bin:$PATH"
kubectl argo rollouts version --short
```

在使用第 3 部分构建流程，以新不可变 tag 发布经过实际审核的 AMD64 镜像之前，请确认一个稳定的 Rollout 并保留其完整 values。初始安装没有先前的稳定 revision，不适用于此更新练习。该 chart 在所有角色间共享一个镜像设置，因此更改它也会将其他角色作为普通 Deployment 更新；仅 payment 遵循 Rollout 步骤。

```bash
# Run from examples/labs/observability/application.
: "${CANARY_IMAGE_TAG:?Set an actually built and reviewed immutable AMD64 image tag}"
# Keep the original application.yaml as the stable revision's complete values.
CANARY_VALUES="$LAB_STATE/helm-inputs/canary-image.yaml"
python3 - "$CANARY_VALUES" "$CANARY_IMAGE_TAG" <<'PYIMAGE'
import sys, json
with open(sys.argv[1], "w") as output:
    json.dump({"image": {"tag": sys.argv[2]}}, output)
PYIMAGE
helm upgrade observability-lab ./chart --kube-context service -n msa \
  -f "$LAB_STATE/helm-inputs/application.yaml" -f "$CANARY_VALUES"
kubectl argo rollouts get rollout payment-service --context service -n msa --watch
```

将 --watch 显示保留在单独的终端中，并在需要时使用 Ctrl+C 停止它。在另一个终端中运行流量和晋级/中止命令。

处于 Paused 状态时，继续第4节的流量，并在 Prometheus 中验证至少五个近期请求已到达新的 rollouts-pod-template-hash revision。缺少流量/查询失败并不表示成功。检查后，推进下面的手动暂停，以便执行配置的 AnalysisRun 和后续步骤。不要使用 --full：它会跳过分析和暂停。

```bash
kubectl argo rollouts promote payment-service --context service -n msa
kubectl argo rollouts get rollout payment-service --context service -n msa --watch
kubectl --context service -n msa get analysisruns
```

如果发生问题，请中止而非晋级，然后通过原始完整 values 恢复所需镜像。仅中止不会恢复 spec.template 或 Git。

```bash
kubectl argo rollouts abort payment-service --context service -n msa
helm upgrade observability-lab ./chart --kube-context service -n msa \
  -f "$LAB_STATE/helm-inputs/application.yaml"
kubectl argo rollouts get rollout payment-service --context service -n msa --watch
```

成功晋级后，请在后续 Helm 命令中保留已批准的镜像 overlay，或将其纳入受管理的所需 values。保留失败分析证据并检查最终状态。此审计验证了 CLI 校验和/help 以及 chart/analysis 逻辑；未执行这些 cluster 更新/晋级/中止命令。

继续前往[第 4 部分](./04-load-testing-scaling-lab.md)。请遵循[第 6 部分](./06-distributed-tracing-lab.md#cleanup)进行考虑所有权/依赖关系的清理。

## 验证范围

检查覆盖了本地 SQLite/PostgreSQL、三个 HTTP service、OTel correlation、SNS/SQS SDK stub、container smoke、Helm/CRD 以及 PromQL/Argo 条件。未演练实际的 AuroraTLS、EKS/IRSA、SNS 扇出、KEDA/Karpenter 和金丝雀流量拆分。

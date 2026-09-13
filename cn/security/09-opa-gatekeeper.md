# OPA Gatekeeper

> **验证基线**: Gatekeeper/Gator 3.23.1 · Helm chart 3.23.1

> **最后更新**: September 13, 2026

## 概述

Gatekeeper 会在 Kubernetes 准入和定期审计期间评估策略。ConstraintTemplate 定义逻辑和参数 schema；Constraint 定义范围、值和 enforcementAction。 [完整示例](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/gatekeeper)使用专用的 `policy-lab` namespace 和本地测试。请勿将每个测试 fixture 都应用到生产集群。

![Gatekeeper 准入和定期审计，其中 Template 定义逻辑，而 Constraint 选择范围。](../.gitbook/assets/en-security-09-opa-gatekeeper-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-security-09-opa-gatekeeper-0.html)

<span id="gatekeeper-vs-kyverno-comparison"></span>

## 选择 Gatekeeper 和 Kyverno

请根据需求、测试和运营模型，在 Gatekeeper 的 Rego/Constraint 模型与 Kyverno 面向 Kubernetes 的策略模型之间做出选择。Gatekeeper 还支持可选的基于 CEL 的 Kubernetes 原生验证。避免使用没有依据的固定资源使用量排名，或声称其他引擎无法表达复杂逻辑。OPA 的 CNCF 毕业并不意味着 Gatekeeper 是一个单独毕业的项目。

<span id="installation-with-helm"></span>

<span id="installation-with-manifests"></span>

<span id="verify-installation"></span>

## 安装 Gatekeeper

使用示例目录中固定版本的 chart 和受支持的值。`auditInterval` 和 `logLevel` 是顶层 chart 字段；不要假定任意 `audit.replicas` 或 `audit.logLevel` 值都会生效。该配置文件会渲染三个 webhook 副本和一个 audit Deployment。验证 EKS control plane 到 webhook 的网络路径、证书、放置位置及可用资源。

```bash
helm repo add gatekeeper https://open-policy-agent.github.io/gatekeeper/charts
helm repo update gatekeeper
helm upgrade --install gatekeeper gatekeeper/gatekeeper --version 3.23.1 \
  --namespace gatekeeper-system --create-namespace --values values.yaml --wait
kubectl -n gatekeeper-system rollout status deployment/gatekeeper-controller-manager
kubectl -n gatekeeper-system rollout status deployment/gatekeeper-audit
```

对于分阶段推出，`values.yaml` 明确保留 webhook `failurePolicy: Ignore`。因此，即使 Constraint 指定 `deny`，webhook 调用失败也可能允许请求。请结合 API 可用性、恢复能力和豁免 namespace 来评估 `Fail`。webhook 范围可能比单个 Constraint 的范围更广。

### Template 和 Constraint 的顺序

Template 会生成相应的 Constraint CRD。应用 Constraint 前，请等待 CRD 处于 Established 状态并检查 Template Pod 状态。所有示例 Constraint 均从 `dryrun` 开始；请针对目标环境检查镜像前缀、参数和 namespace。

```bash
kubectl create namespace policy-lab --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f templates/
kubectl wait --for=condition=Established --timeout=90s \
  crd/docsrequiredlabels.constraints.gatekeeper.sh \
  crd/docsnoprivileged.constraints.gatekeeper.sh \
  crd/docsapprovedimages.constraints.gatekeeper.sh \
  crd/k8scontainerlimits.constraints.gatekeeper.sh \
  crd/docsuniqueingress.constraints.gatekeeper.sh
kubectl apply -f constraints/
```

<span id="rego-language-basics"></span>

<span id="rego-syntax-overview"></span>

<span id="rego-data-types"></span>

<span id="rego-operators-and-built-in-functions"></span>

## Rego 与输入契约

Gatekeeper 策略使用 `input.review`，而不是通用 OPA AdmissionReview 示例中的 `input.request`。`input.parameters` 提供 Constraint 值，`data.inventory` 提供已同步的 Kubernetes 对象。现有 `targets[].rego` 默认使用受支持的 Rego v0。Rego v1 需通过 `code[].source.version: v1` 显式选择；较旧的 v0 Template 不会自动失效。

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: docsrequiredlabels
spec:
  crd:
    spec:
      names:
        kind: DocsRequiredLabels
      validation:
        openAPIV3Schema:
          type: object
          properties:
            labels:
              type: array
              minItems: 1
              items:
                type: string
                minLength: 1
          required:
          - labels
  targets:
  - target: admission.k8s.gatekeeper.sh
    code:
    - engine: Rego
      source:
        version: v1
        rego: "package docsrequiredlabels\nvalid_label(key) if {\n  value := input.review.object.metadata.labels[key]\n\
          \  is_string(value)\n  value != \"\"\n}\nviolation contains {\"msg\": sprintf(\"\
          required nonempty label: %v\", [key])} if {\n  some key in input.parameters.labels\n\
          \  not valid_label(key)\n}\n"
```

`violation contains ... if` 是 v1 的部分集合规则。多个定义会共同构成该集合；这并不意味着相互冲突的完整文档规则总会以 OR 方式组合。规则主体内的条件必须全部成立。请区分递归的用户定义规则与 `walk` 等 JSON 遍历内置函数。

```rego
package examples
items := [x | some x in input.items; x > 10]
keys := object.keys(object.get(input, "labels", {}))
missing := {"app", "team"} - keys
```

`obj[_]` 选择对象值。当需要标签键时，请使用 `object.keys` 或显式绑定键。集合差集 `-`、交集 `&` 和并集 `|` 是实用的策略操作。

<span id="writing-constraint-templates"></span>

<span id="basic-structure"></span>

<span id="preventing-privileged-containers"></span>

<span id="enforcing-resource-limits"></span>

<span id="restricting-image-registries"></span>

<span id="defining-constraints"></span>

<span id="basic-constraint-writing"></span>

<span id="using-namespace-selectors"></span>

<span id="resource-limits-constraint"></span>

<span id="image-registry-constraint"></span>

## 策略和范围

| Template | 检查项 | 范围和限制 |
|---|---|---|
| DocsRequiredLabels | 必需的非空标签 | Pod metadata；Deployment metadata 与 Pod template 标签不同 |
| DocsNoPrivileged | 拒绝 privileged=true | 常规、init 和 ephemeral container；并非完整的 PSS 套件 |
| DocsApprovedImages | 已批准的 registry/path 前缀 | 所有三种 container 类型；schema 要求以结尾的 `/` 作为边界 |
| K8sContainerLimits | CPU/memory limit 的存在性和最大值 | 固定版本的上游策略；常规/init container，因为 ephemeral container 无法设置资源字段 |
| DocsUniqueIngress | 已同步 inventory 中的精确 host 冲突 | 排除同一对象更新；不保证 wildcard 或原子性的并发创建 |

### 镜像边界和例外

`registry.example.com/team/` 与 `registry.example.com/team-evil/` 及 `registry.example.com.evil/` 不同。前缀匹配需要分隔符边界和完整限定的镜像名称契约。该示例不提供工作负载可控的绕过标签，例如 `skip-privileged-check=true`。namespace 例外需要为标签变更实施受控的 RBAC、授权、到期机制和审计记录。

### 资源数量

仅支持 Gi/Mi/Ki 的解析器可能对 `9G` 或纯字节返回 undefined，并悄然漏报违规。该示例固定使用上游 `K8sContainerLimits` 策略，它会将不受支持的字符串报告为违规。它不接受 Kubernetes 允许的每种数量表示；请记录其格式限制。原生测试区分 millicore、十进制/二进制内存、纯字节、数值输入以及显式引用的指数格式字符串。请引用如 `8e9` 的字符串 fixture，以防 YAML 解析器将其转换为数字。

### PSS 和 Controller 资源

不要将少量 privileged/runAsNonRoot 检查标为完整的 Baseline/Restricted 强制执行。版本化 PSS 还涵盖 host namespace、seccomp、capability、OS 差异、Pod 级继承和 ephemeral container；请使用 [Pod Security Standards 指南](./03-pod-security-standards.md)。这些示例检查 Pod 准入。如需更早评估 controller Pod template，请配置单独的 Template 或 ExpansionTemplate 测试。

<span id="advanced-policy-patterns"></span>

<span id="external-data-reference"></span>

<span id="cross-namespace-policies"></span>

<span id="complex-condition-policies"></span>

## 同步数据和引用策略

`sync.yaml` 将 `networking.k8s.io/v1` Ingress 对象同步到 inventory。这不同于连接外部 HTTP provider 或任意 OPA bundle。仅同步必要的对象，并审查 RBAC、内存和敏感数据。

```yaml
apiVersion: config.gatekeeper.sh/v1alpha1
kind: Config
metadata:
  name: config
  namespace: gatekeeper-system
spec:
  sync:
    syncOnly:
    - group: networking.k8s.io
      version: v1
      kind: Ingress
```

同一 namespace 中不同的名称，或不同 namespace 中相同的名称，仍然可能冲突。要求 namespace 和名称都不同会漏掉这些情况。该示例只将相同 namespace/名称作为自身更新排除。由于 inventory 最终一致，它不能为并发创建以原子方式保证唯一性。

<span id="mutation-features"></span>

<span id="using-assignmetadata"></span>

<span id="using-assign"></span>

<span id="conditional-mutation"></span>

<span id="using-modifyset"></span>

## 变更

AssignMetadata 添加受支持的 metadata label/annotation；它不是通用覆盖机制。Assign 设置字段。分配整个 toleration 列表可能会丢弃现有条目，因此该示例使用 ModifySet merge。该 toleration 允许专用 lab taint；它不选择 Spot node。

```yaml
apiVersion: mutations.gatekeeper.sh/v1
kind: ModifySet
metadata:
  name: docs-dedicated-toleration
spec:
  applyTo:
  - groups:
    - ''
    versions:
    - v1
    kinds:
    - Pod
  match:
    scope: Namespaced
    namespaces:
    - policy-lab
  location: spec.tolerations
  parameters:
    operation: merge
    values:
      fromList:
      - key: dedicated
        operator: Equal
        value: policy-lab
        effect: NoSchedule
```

将 mutation/defaulting 与 validation 分开。审查 CREATE/UPDATE 范围、重复应用、与其他 mutator 的收敛性以及对现有对象的影响。创建 mutator 不会自动重写每个现有对象。

<span id="audit-configuration"></span>

<span id="checking-constraint-violations"></span>

<span id="prometheus-metrics"></span>

<span id="grafana-dashboard"></span>

## 审计和监控

使用 chart `auditInterval` 设置审计频率。Config `validation.traces` 用于调试选定的准入评估，而不是安排审计。准入输入和 Rego print 可能包含敏感对象数据；仅在所需范围内启用它们。`constraintViolationsLimit` 限制状态详情列表，其值可能不同于 totalViolations。

```bash
kubectl get constraints
kubectl describe docsrequiredlabels required-labels
kubectl get constrainttemplatepodstatuses -n gatekeeper-system
kubectl get constraintpodstatuses -n gatekeeper-system
```

chart webhook Service 仅暴露 HTTPS webhook 流量，而非 metrics。`podmonitor.yaml` 在 audit 和 webhook Deployment 上选择实际命名的 metrics:8888 container port。请先安装 Prometheus Operator CRD 并对齐 PodMonitor label/namespace selector。

| Metric | 含义 |
|---|---|
| gatekeeper_validation_request_count | 带有实际 admission_status label 的验证请求 |
| gatekeeper_validation_request_duration_seconds | 验证延迟直方图 |
| gatekeeper_violations | 按 enforcement_action 分类的已审计违规；不假定存在默认 constraint_name label |
| gatekeeper_audit_last_run_end_time | 上次完成审计的时间戳 |
| gatekeeper_constraint_templates | Template 状态计数 |

```promql
sum by (enforcement_action) (gatekeeper_violations)
histogram_quantile(0.99, sum by (le) (rate(gatekeeper_validation_request_duration_seconds_bucket[5m])))
```

<span id="testing-and-ci-cd-integration"></span>

<span id="gator-cli-testing"></span>

<span id="test-suite-definition"></span>

<span id="test-fixtures"></span>

<span id="github-actions-integration"></span>

## Gator 测试和 CI

安装官方 3.23.1 release asset 并验证其发布的 checksum。ARM64 binary 在 GitVersion 中报告 +dirty；审计验证了发布 archive 的 hash，而非假定该文本意味着本地修改。请勿用未固定版本的 @latest CLI 运行替代带版本证据的运行。

```bash
gator version
gator verify tests/suite.yaml --verbose
gator test -f templates/docsnoprivileged.yaml \
  -f constraints/no-privileged.yaml \
  -f tests/fixtures/tenant-skip-label-no-bypass.yaml --output=json
```

`verify` 检查 Suite 中的预期违规；`test -f` 根据 Template/Constraint 评估 manifest。Verify 可以忽略不含 Suite 的目录，因此请检查五个测试和 33 个 case 均已运行，而不要仅信任 exit status。fixture 镜像是策略输入，并非可拉取的工作负载。CI 在没有凭据的情况下运行本地 suite；任何集群 dry-run 都应属于拥有已授权访问权限的独立受信环境。

<span id="best-practices"></span>

<span id="policy-organization"></span>

<span id="gradual-policy-rollout"></span>

<span id="policy-exception-management"></span>

<span id="troubleshooting"></span>

<span id="common-issues"></span>

<span id="debugging-tips"></span>

## 推出和故障排除

将同一个已填充的 Constraint 依次经过 dryrun→warn→deny，并审查 audit/admission 结果和例外。请勿将三个无参数 Constraint 作为推出机制。Dryrun/warn 可能在 Gator 测试 exit status 为零时返回违规；deny 违规则返回一。请将 webhook 可用性失败与策略违规分开观察。

```bash
kubectl get validatingwebhookconfiguration gatekeeper-validating-webhook-configuration -o yaml
kubectl -n gatekeeper-system logs deployment/gatekeeper-controller-manager --tail=100
kubectl -n gatekeeper-system logs deployment/gatekeeper-audit --tail=100
```

检查策略输入、match 范围、CRD/Template 错误、webhook certificate/network、audit timestamp 和 inventory 新鲜度。在更改 webhook 强制执行或扩大 namespace 例外前，请先诊断原因。

<span id="summary"></span>

<span id="related-documentation"></span>

## 验证范围和相关阅读

Gator 3.23.1 执行了 33 个策略 case 和三种 enforcement mode。检查涵盖固定版本的 Helm render、八个 Gatekeeper CRD 对象以及 audit/webhook PodMonitor 绑定。它们没有执行 Kubernetes admission、EKS networking、实时 audit-cache 同步或 API failover。独立的原生 mutation 验证记录在审查报告中。

- [Gatekeeper 测验](../quizzes/security/09-opa-gatekeeper-quiz.md)
- [Kyverno](./01-kyverno-policy-management.md)
- [Pod Security Standards](./03-pod-security-standards.md)
- [EKS 安全实践](./06-eks-security-best-practices.md)

## 参考资料

- [Gatekeeper v3.23.1](https://github.com/open-policy-agent/gatekeeper/tree/v3.23.1)
- [ConstraintTemplate 和 Rego 版本](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/constrainttemplates.md)
- [Gator](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/gator.md)
- [Mutation](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/mutation.md)
- [Audit](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/audit.md)
- [Metrics](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/metrics.md)
- [固定版本的资源限制策略](https://github.com/open-policy-agent/gatekeeper-library/blob/bd333d4704647b1000cef5a92017257ee46fe2c8/library/general/containerlimits/template.yaml)

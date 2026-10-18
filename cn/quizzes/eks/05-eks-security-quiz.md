# Amazon EKS 安全测验

> **最后更新**：September 11, 2026

本测验考查你对 Amazon EKS 安全功能、最佳实践和配置的理解。

## 测验概览
- EKS 身份验证和授权
- 网络安全
- 容器安全
- 数据安全
- 合规性和审计
- 安全最佳实践

## 选择题

### 1. 对于 IAM 用户或角色，哪种 EKS 设置能够正确结合身份验证和 Kubernetes 授权？

- A) 仅使用 IAM 管理权限
- B) 创建 RBAC 规则，但不配置身份的身份验证路径
- C) 配置 IAM 集群访问，并添加适当的 RBAC 和/或 EKS 访问策略
- D) 仅使用 API 端点网络限制

<details>
<summary>显示答案</summary>

**答案：C) 配置 IAM 集群访问，并添加适当的 RBAC 和/或 EKS 访问策略**

**说明：**

IAM 通过配置的 EKS 访问路径对目标人员/自动化身份进行身份验证。Kubernetes RBAC 和 EKS 访问策略负责授权 Kubernetes 操作；两者授予的权限是累加的。网络限制是另一层控制，不能取代授权。Pod 到 Kubernetes 的身份验证通常使用其 ServiceAccount 令牌；IRSA/Pod Identity 则为工作负载提供 AWS 凭证。

EKS 集群服务角色和人类开发者角色用途不同。为开发者附加 AmazonEKSClusterPolicy 并不会授予 Kubernetes 访问权限，而 DescribeCluster/ListClusters 权限或 kubeconfig 文件也不会授予工作负载权限。

**限定范围的实施方式**：经过授权的平台运维人员为现有且已批准的开发者 IAM 角色准备以下命名空间和 RBAC。集群必须已经支持访问条目。保留现有管理员/节点映射，并审查身份验证模式迁移；不要用示例 ConfigMap 覆盖 aws-auth。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
```



```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set its Region}"
: "${DEVELOPER_ROLE_ARN:?Set a prepared IAM role ARN, not an STS session ARN}"
MODE=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.accessConfig.authenticationMode --output text)
case "$MODE" in
  API|API_AND_CONFIG_MAP) ;;
  *) echo "Access entries are not enabled; review the migration first"; exit 1 ;;
esac
aws eks list-access-entries --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --output json > security-access-entries.json
python3 - "$DEVELOPER_ROLE_ARN" <<'PY'
import json, sys
with open("security-access-entries.json") as stream:
    existing = json.load(stream)["accessEntries"]
if sys.argv[1] in existing:
    raise SystemExit("Entry already exists; inspect its groups/policies instead of overwriting")
PY
aws eks create-access-entry --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --principal-arn "$DEVELOPER_ROLE_ARN" --type STANDARD \
  --kubernetes-groups security-demo-developers
```



```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: developer
  namespace: security-demo
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - apps
  resources:
  - deployments
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
- apiGroups:
  - batch
  resources:
  - jobs
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer
  namespace: security-demo
subjects:
- kind: Group
  name: security-demo-developers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer
  apiGroup: rbac.authorization.k8s.io
```

访问条目中的组名必须与 RoleBinding subject 相匹配。此角色只允许在 security-demo 中执行列出的操作；其他现有授权可能会扩大访问范围。在该命名空间中创建 Deployment/Job，可能会间接使用 Secrets、PVC 和 ServiceAccount，因此没有直接读取 Secret 的规则并不能构成租户安全边界。应分隔租户，并通过准入和所有权控制限制工作负载身份及资源使用。

经过单独审查的只读用户也可以改为关联命名空间范围的 AmazonEKSViewPolicy。添加之前请检查现有访问策略；此操作不会撤销更广泛的 RBAC 或其他访问策略授权。`eks:namespaces` 用于筛选访问策略关联请求，而不是一般的 kubectl 请求。

**验证实际登录**：调用方必须能够发现集群并担任已批准的角色。此操作会创建临时 kubeconfig，而不会替换默认上下文：

```bash
set -euo pipefail
umask 077
: "${CLUSTER_NAME:?Set the reviewed cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${DEVELOPER_ROLE_ARN:?Set the intended IAM role ARN}"
review_dir=$(mktemp -d "${TMPDIR:-/tmp}/eks-login-check.XXXXXXXX")
trap 'rm -rf -- "$review_dir"' EXIT
aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --role-arn "$DEVELOPER_ROLE_ARN" --kubeconfig "$review_dir/config"
kubectl --kubeconfig "$review_dir/config" auth can-i list pods -n security-demo
kubectl --kubeconfig "$review_dir/config" auth can-i create jobs -n security-demo
kubectl --kubeconfig "$review_dir/config" auth can-i list pods -n another-team
```

根据预期授权检查结果，并调查意外的跨命名空间权限。`--as` 测试的是模拟身份/RBAC，并不能证明 IAM 访问策略路径有效。本测验未执行任何实际 IAM 登录或 Kubernetes 授权测试；本地证据包括架构/脚本检查和模拟的访问条目流程。

参考：[EKS 访问条目](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)、[EKS 访问策略](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)、[Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)。

</details>

### 2. 在支持策略强制执行的 EKS 网络上，哪种 Kubernetes 机制可通过标签表达 Pod 流量规则？

- A) 仅使用实例安全组
- B) 使用具有强制执行能力的网络实现来执行 NetworkPolicy 资源
- C) 仅使用 VPC 端点策略
- D) 仅使用主机防火墙命令

<details>
<summary>显示答案</summary>

**答案：B) 使用具有强制执行能力的网络实现来执行 NetworkPolicy 资源**

**说明：**

NetworkPolicy 使用 Kubernetes 标签和命名空间选择 Pod 并指定允许的流量。它需要具有强制执行能力的网络实现。安全组（包括受支持的 Pod 安全组）仍然是有用的 AWS 控制措施；它们并不限于整个实例。VPC 端点策略管理对受支持 AWS 服务的访问，而不是任意的基于标签的 Pod 流量。

**完整策略示例**：这些清单描述的是一个隔离的演示命名空间，不是应用安装程序，也不是 CNI 的替代方案。示例假设使用标准 Linux EC2 节点、受支持且能强制执行策略的 CNI，以及常见的 CoreDNS Deployment/Pod 标签。Auto Mode 或节点本地 DNS 需要针对实际使用的解析器路径配置规则。如果限制了 CoreDNS 入站流量，其所有者还必须允许这些查询。

由命名空间所有者保存并应用。默认拒绝会隔离两个方向的流量；明确允许客户端出站流量和目标端入站流量，适用于 frontend → API 和 API → database。DNS 需要同时允许 UDP 和 TCP：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-network-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
---
apiVersion: v1
kind: Namespace
metadata:
  name: security-monitoring-demo
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: security-network-demo
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: security-network-demo
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-to-api
  namespace: security-network-demo
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-ingress
  namespace: security-network-demo
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-to-database
  namespace: security-network-demo
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-ingress
  namespace: security-network-demo
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 5432
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: monitor-api
  namespace: security-network-demo
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: security-monitoring-demo
      podSelector:
        matchLabels:
          app: prometheus
    ports:
    - protocol: TCP
      port: 9090
```

监控对端在同一个 peer 中同时使用 namespaceSelector **和** podSelector，因此只会选中 security-monitoring-demo 中匹配的 Prometheus Pod。如果该客户端也受到出站隔离，它发起的连接同样需要允许：

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: prometheus-to-demo-api
  namespace: security-monitoring-demo
spec:
  podSelector:
    matchLabels:
      app: prometheus
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: security-network-demo
      podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 9090
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

| 流量 | 使用这些策略时的预期结果 |
|---|---|
| frontend → api TCP 8080 | 允许 |
| api → database TCP 5432 | 允许 |
| frontend → database TCP 5432 | 拒绝 |
| 无关 Pod → api TCP 8080 | 拒绝 |
| 被选中的 Prometheus → api TCP 9090 | 允许 |
| 监控命名空间中的其他 Pod → api TCP 9090 | 拒绝 |
| 工作负载 → 匹配的 CoreDNS Pod UDP/TCP 53 | 允许，但受解析器端控制措施约束 |
| 任意外部目标 | 拒绝，除非添加明确的出站规则 |

策略是累加且无顺序的。其他宽泛的允许规则可能扩大访问范围；默认拒绝不会覆盖它们。请在目标 CNI 上测试完整的已安装策略集、DNS 解析，以及新建的允许/拒绝连接。已建立连接、hostNetwork/节点流量和 NAT 行为存在实现特定的限制；简单的 NetworkPolicy 并不是通用的 IMDS 或主机防火墙边界。

对于外部服务，应限定实际目标地址/端口，或使用所选实现支持的 DNS 感知控制。允许所有目标访问 443 端口，或放行整个 10.0.0.0/8 范围，都不是服务允许列表。用任意替代的 Calico/Cilium 清单或部分 kube-proxy 替换标志来启用现有 EKS 网络上的策略，并不安全。

配套源文件的 18 个合成选择器/端口案例已在本地检查；未执行数据包/CNI 测试。参考：[Kubernetes NetworkPolicy 行为](https://kubernetes.io/docs/concepts/services-networking/network-policies/)。

</details>

### 3. 在 EKS 上，哪种方法能结合互补控制来保护容器映像？

- A) 仅依赖人工检查映像
- B) 假定所有官方映像都没有漏洞
- C) 结合扫描、签名/验证和准入控制
- D) 仅依赖容器内的防病毒软件

<details>
<summary>显示答案</summary>

**答案：C) 结合扫描、签名/验证和准入控制**

**说明：**

扫描器只能识别其规则和漏洞数据库涵盖的问题；它无法证明不存在任何后门或未来漏洞。签名可以根据配置的信任策略证明完整性和身份关联，但不能证明已签名的软件是安全的。准入控制负责强制执行所选部署策略。使用维护良好的精简基础映像，及时重建以应用补丁，跟踪例外情况，并选择合适的 ECR 基本/增强扫描模式或其他扫描模式。

**AWS Signer 和 Notation**：容器签名平台为 `Notation-OCI-SHA384-ECDSA`。使用 Notation AWS Signer 插件，按摘要为已推送的映像签名。`Aws::ECR::Image` 平台或 `start-signing-job --source-image` 并非受支持的工作流。经审查的 AWS CLI 不接受该选项。

当前 ECR 托管签名也是一种受支持的推送触发式替代方案，可通过注册表签名规则配置。若选择此方案，应配置正确的配置文件/权限，并在提升映像前等待实际签名状态。不能因为映像已推送，就认定异步签名已完成。

**信任配置**：准备经过验证的 Notation/Signer 插件安装、正确分区对应的 AWS Signer 根信任存储，以及经过审查的严格信任策略。以下商业区域示例将信任范围限制为一个仓库和一个已批准的配置文件。请一致地替换所有账户/区域/仓库/配置文件信息；不要仅因为签名者证书链接到 AWS 根证书，就信任该签名者。

```json
{
  "version": "1.0",
  "trustPolicies": [
    {
      "name": "reviewed-eks-repository",
      "registryScopes": [
        "123456789012.dkr.ecr.us-west-2.amazonaws.com/team/app"
      ],
      "signatureVerification": {
        "level": "strict"
      },
      "trustStores": [
        "signingAuthority:aws-signer-ts"
      ],
      "trustedIdentities": [
        "arn:aws:signer:us-west-2:123456789012:/signing-profiles/eks_images"
      ]
    }
  ]
}
```

使用 `notation policy import notation-trust-policy.json` 将该策略导入构建环境自有的 Notation 配置。替换前先审查任何现有策略；不要通过未经审查的脚本覆盖开发者共享的信任配置。构建角色需要仓库范围的 ECR 拉取/推送操作、ECR 身份验证，以及所需的 SignPayload/GetRevocationStatus 权限。创建签名配置文件是单独的配置工作；仅使用现有的已批准配置文件时，构建无需 PutSigningProfile。

**CodeBuild 示例**：这是一个 buildspec，不是 CodePipeline 定义。它要求使用自有 Linux 构建映像，并预先安装 Bash、Python、Docker/守护进程访问、AWS CLI、Trivy、Notation 和已固定版本的 AWS Signer 插件。请另行配置项目所需的运行时特权、网络访问、扫描器数据库、IAM 角色、信任存储/策略和现有 ECR 仓库。Dockerfile 和源代码是该构建角色的可信输入。此示例使用已解析的 Git 提交和一个商业 AWS 账户/区域；它没有实现跨账户签名设计。

```yaml
version: 0.2
env:
  shell: bash
phases:
  build:
    commands:
      - |
        set -euo pipefail
        umask 077
        # Reserve this generated artifact name; remove stale output before any build step.
        rm -f -- verified-image.json
        : "${AWS_REGION:?Set the commercial AWS Region}"
        : "${AWS_ACCOUNT_ID:?Set the expected ECR/signing account ID}"
        : "${ECR_REPOSITORY:?Set the complete repository name, including any path}"
        : "${SIGNING_PROFILE_ARN:?Set the approved AWS Signer profile ARN}"
        : "${CODEBUILD_RESOLVED_SOURCE_VERSION:?This example requires a resolved Git commit}"
        python3 - <<'PY'
        import os, re
        checks = {
            "AWS_ACCOUNT_ID": r"[0-9]{12}",
            "AWS_REGION": r"[a-z0-9-]+",
            "ECR_REPOSITORY": r"[a-z0-9]+(?:[._/-][a-z0-9]+)*",
            "CODEBUILD_RESOLVED_SOURCE_VERSION": r"(?:[0-9a-f]{40}|[0-9a-f]{64})",
        }
        for name, pattern in checks.items():
            if not re.fullmatch(pattern, os.environ[name]):
                raise SystemExit("Invalid example input: " + name)
        prefix = f"arn:aws:signer:{os.environ['AWS_REGION']}:{os.environ['AWS_ACCOUNT_ID']}:/signing-profiles/"
        profile = os.environ["SIGNING_PROFILE_ARN"]
        if not profile.startswith(prefix) or not re.fullmatch(r"[A-Za-z0-9_/]+", profile[len(prefix):]):
            raise SystemExit("Use an approved signing profile in this example's account/Region")
        PY
        REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        IMAGE_URI="${REGISTRY}/${ECR_REPOSITORY}:${CODEBUILD_RESOLVED_SOURCE_VERSION}"
        ACTUAL_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
        if [[ "$ACTUAL_ACCOUNT" != "$AWS_ACCOUNT_ID" ]]; then
          printf '%s\n' 'Unexpected build-role account' >&2
          exit 1
        fi
        aws ecr get-login-password --region "$AWS_REGION" |
          docker login --username AWS --password-stdin "$REGISTRY"
        docker build --tag "$IMAGE_URI" .
        trivy image --image-src docker --scanners vuln --severity HIGH,CRITICAL \
          --exit-code 1 --no-progress "$IMAGE_URI"
        docker push "$IMAGE_URI"
        DIGESTS_JSON=$(docker image inspect --format '{{json .RepoDigests}}' "$IMAGE_URI")
        IMAGE_REFERENCE=$(python3 - "$REGISTRY/$ECR_REPOSITORY" "$DIGESTS_JSON" <<'PY'
        import json, re, sys
        digests = json.loads(sys.argv[2])
        if not isinstance(digests, list):
            raise SystemExit("Expected Docker RepoDigests array")
        pattern = re.escape(sys.argv[1]) + r"@sha256:[0-9a-f]{64}"
        matching = {d for d in digests if isinstance(d, str) and re.fullmatch(pattern, d)}
        if len(matching) != 1:
            raise SystemExit("Expected exactly one pushed digest for this repository")
        print(matching.pop())
        PY
        )
        notation sign --plugin com.amazonaws.signer.notation.plugin \
          --id "$SIGNING_PROFILE_ARN" "$IMAGE_REFERENCE"
        notation verify "$IMAGE_REFERENCE"
        python3 - "$IMAGE_REFERENCE" "$CODEBUILD_RESOLVED_SOURCE_VERSION" <<'PY'
        import json, sys
        with open("verified-image.json", "x") as stream:
            json.dump({"image": sys.argv[1], "sourceCommit": sys.argv[2]}, stream)
            stream.write("\n")
        PY
artifacts:
  files:
    - verified-image.json
```

通过经过审查的项目配置设置 `AWS_ACCOUNT_ID`、`AWS_REGION`、`ECR_REPOSITORY`（例如 `team/app`）和 `SIGNING_PROFILE_ARN`。该命令会向注册表主机名进行身份验证，保留嵌套仓库路径，在推送前扫描本地构建的映像，并选择匹配的已推送 RepoDigest，而不是任意的第一个条目或可变标签。此处的 Trivy 用于拦截 HIGH/CRITICAL 漏洞发现；应根据明确设计添加其他秘密信息、配置和来源检查。

所有提升步骤都在同一个 Bash 构建块中，并启用了 `set -euo pipefail`。登录/构建/扫描/推送/签名/验证任何一步失败，都会在写入新构件前停止。构建失败后 CodeBuild 仍可能运行 post_build，因此单独设置未受保护的 post_build 推送/签名步骤并不安全。首先清理预留的构件路径，以防复用之前的输出。下游部署还必须要求构建成功并验证构件；JSON 文件本身既不是授权凭据，也不是已签名的证明材料。

`verified-image.json` 包含供 EKS 部署/GitOps 使用者使用的准确摘要引用。它不是 ECS `imagedefinitions.json`，本身也不会部署任何内容。即使签名/验证成功，仍取决于实际注册表访问、信任、撤销状态检查和 AWS Signer 可用性。

**准入**：生产环境的签名验证器必须能够理解所选的 Notation/Signer 签名和信任策略。AWS 文档介绍了 Gatekeeper 与 Ratify 的组合，以及 Kyverno 与 AWS Signer/Notation 的集成。安装通用策略引擎、使用没有 ConstraintTemplate 的裸 Gatekeeper constraint，或为其他签名方案填写公钥字段，都不能证明该集成已建立。在启用强制执行之前，应验证受信任/不受信任的配置文件、未签名映像、摘要不匹配、已撤销/过期的签名、验证器故障和准入失败策略。

以下独立的 Kyverno 1.19.1 规则仅在 security-demo 中限制**映像引用语法和仓库**。它会检查常规容器、init 容器和临时容器。它**并不**声称会验证签名：

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: demo-approved-image-reference
spec:
  validationActions:
  - Deny
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      resources:
      - pods
      - pods/ephemeralcontainers
      operations:
      - CREATE
      - UPDATE
      scope: Namespaced
  matchConditions:
  - name: demo-namespace
    expression: has(object.metadata.namespace) && object.metadata.namespace == 'security-demo'
  validations:
  - expression: object.spec.containers.all(c, c.image.matches('^123456789012[.]dkr[.]ecr[.]us-west-2[.]amazonaws[.]com/team/app@sha256:[0-9a-f]{64}$'))
      && (!has(object.spec.initContainers) || object.spec.initContainers.all(c, c.image.matches('^123456789012[.]dkr[.]ecr[.]us-west-2[.]amazonaws[.]com/team/app@sha256:[0-9a-f]{64}$')))
      && (!has(object.spec.ephemeralContainers) || object.spec.ephemeralContainers.all(c, c.image.matches('^123456789012[.]dkr[.]ecr[.]us-west-2[.]amazonaws[.]com/team/app@sha256:[0-9a-f]{64}$')))
    message: Use a sha256 digest from the approved team/app repository in security-demo.
```

验证情况：20 个模拟的流水线失败/顺序/构件案例，以及九个实际 Kyverno CLI 字符串策略案例。已检查 buildspec/Bash/Python/JSON 和发布的策略 CRD。未构建/扫描/推送任何映像，未生成或验证实际 AWS 签名，也未部署准入 webhook。这是一个经审查的教学工作流，具有明确的环境假设，并非经过测试的生产就绪方案。

参考：[Signer 签名](https://docs.aws.amazon.com/signer/latest/developerguide/image-signing-steps.html)、[Signer 验证](https://docs.aws.amazon.com/signer/latest/developerguide/image-verification.html)、[ECR 托管签名](https://docs.aws.amazon.com/AmazonECR/latest/userguide/managed-signing.html)、[EKS 准入验证](https://docs.aws.amazon.com/eks/latest/userguide/image-verification.html)、[CodeBuild buildspec](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html)、[Trivy 映像标志](https://trivy.dev/docs/latest/references/configuration/cli/trivy_image/)。

</details>

### 4. 哪种方法能够在 EKS 上应用一致且最新的 Pod 安全基线？

- A) 仅禁用特权模式
- B) 通过 PSA 使用带版本号的 PSS 配置文件，并在需要时添加经过审查的准入策略
- C) 仅设置非 root UID
- D) 仅将根文件系统设为只读

<details>
<summary>显示答案</summary>

**答案：B) 通过 PSA 使用带版本号的 PSS 配置文件，并在需要时添加经过审查的准入策略**

**说明：**

Pod Security Standards 定义了 Privileged、Baseline 和 Restricted 配置文件。Pod Security Admission 会强制执行由命名空间选择的配置文件。PSA 自 Kubernetes 1.25 起稳定；PodSecurityPolicy 在 1.21 中弃用，并且**已在 1.25 中移除**。当前集群无法部署该已移除的 API。Kyverno/Gatekeeper 策略是独立资源，即使旧示例在 constraint 名称中使用了“PSP”也是如此。

以下示例展示了使用经过审查的 v1.36 配置文件的隔离 Linux 环境：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
---
apiVersion: v1
kind: Pod
metadata:
  name: security-context-demo
  namespace: security-demo
spec:
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: busybox:1.38.0
    command:
    - sh
    - -c
    args:
    - id && sleep 3600
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    resources:
      requests:
        cpu: 10m
        memory: 16Mi
      limits:
        cpu: 100m
        memory: 64Mi
```

命名空间的 enforce 设置应用于 Pod 准入。Audit/warn 可以报告控制器模板违规，但 Deployment/Job 成功应用并不能证明其 Pod 符合强制执行要求。更改标签不会追溯性地驱逐现有 Pod。应为实际集群选择策略版本，并在强制执行前审查现有工作负载。

runAsNonRoot/runAsUser 和 seccomp 与 allowPrivilegeEscalation 和 capabilities 是不同的设置。fsGroup 是 Pod 级别的卷所有权设置，不是容器 capability。只读根文件系统是一项有用且需与应用兼容的加固措施，但它不是 PSS Restricted 的普遍要求，也不会使挂载的 PVC 变为只读。实际应用需要兼容的 UID/GID 和可写的临时/缓存/套接字路径；仅添加这些字段，并不能让面向 root 运行的通用 nginx 映像正常工作。

**另一项限定范围的准入规则**：此 Kyverno 1.19.1 ValidatingPolicy 会检查 security-demo 中所有常规容器、init 容器和临时容器。未设置 privileged 会被视为 false 并接受；设置为 true 则会被拒绝。它使用当前的 v1 policy API，而不是过时的安装清单：

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: demo-disallow-privileged
spec:
  validationActions:
  - Deny
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      resources:
      - pods
      - pods/ephemeralcontainers
      operations:
      - CREATE
      - UPDATE
      scope: Namespaced
  matchConditions:
  - name: demo-namespace
    expression: has(object.metadata.namespace) && object.metadata.namespace == 'security-demo'
  validations:
  - expression: object.spec.containers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged)
      || c.securityContext.privileged == false) && (!has(object.spec.initContainers)
      || object.spec.initContainers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged)
      || c.securityContext.privileged == false)) && (!has(object.spec.ephemeralContainers)
      || object.spec.ephemeralContainers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged)
      || c.securityContext.privileged == false))
    message: Privileged containers, including init and ephemeral containers, are not
      allowed in security-demo.
```

这条规则不能取代整个 PSS 配置文件或映像验证。应由其平台所有者管理具有特权的 CSI/监控代理和有意设置的例外；不要将演示策略一概应用于 kube-system。Gatekeeper 替代方案需要实际的 ConstraintTemplate、匹配的 constraint 和经过验证的行为。

清单/架构以及六个实际 Kyverno CLI 案例涵盖了省略/false、特权常规容器/init 容器/临时容器，以及其他命名空间。临时容器测试使用合成的 UPDATE 对象，而非创建 Pod。未执行实际准入 webhook 或 Pod 部署。

参考：[Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/)、[Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)。

</details>

### 5. 哪种方法能够为 EKS 工作负载提供互补的安全证据？

- A) 仅偶尔进行人工审查
- B) 仅使用 AWS Config 检查
- C) 仅使用 GuardDuty
- D) 结合安全状况发现、审计日志、运行时覆盖范围和经过验证的响应路径

<details>
<summary>显示答案</summary>

**答案：D) 结合安全状况发现、审计日志、运行时覆盖范围和经过验证的响应路径**

**说明：**

| 证据/控制 | 提供的内容及其无法证明的事项 |
|---|---|
| Security Hub CSPM / AWS Config | 受支持的配置控制和发现；并非完整的 Kubernetes 或法规认证 |
| GuardDuty EKS Protection | 通过独立数据流进行基于 Kubernetes 审计日志的威胁分析 |
| GuardDuty Runtime Monitoring | 在受支持节点上基于代理的运行时事件；仅启用并不代表覆盖已到位 |
| CloudTrail | AWS API 活动；不能取代 Kubernetes 审计或应用程序数据访问日志 |
| Kubernetes 审计日志 | 根据审计策略/级别选取的请求，不包括每项工作负载操作/请求正文 |
| CloudWatch / 事件响应路由 | 日志分析和向运维人员发送事件；必须验证投递、保留和响应情况 |

Security Hub CSPM 的 FSBP 标准并不是 CIS Kubernetes Benchmark。受支持的 CIS AWS Foundations 控制也不是完整的 CIS Kubernetes 审计。应记录适用的基准/版本、人工检查、托管服务例外，以及工作负载实际义务所需的证据。

应使用现有的组织/区域所有权来管理检测器、CSPM 标准、Config 记录器和 CloudTrail。不要创建另一个区域检测器、覆盖集中式配置，或在尚未准备好存储桶策略、加密、事件选择器和保留期的情况下启动 trail。CloudTrail 数据事件与默认的管理事件覆盖范围是分开的。本次审查没有配置账户级监控资源。

**EKS 特定检查**：按照源章节所示启用并确认预期的控制面日志类型、更新完成情况和日志到达情况。`eks-cluster-logging-enabled`（所有类型，定期检查）和 `eks-cluster-log-enabled`（可选的已选类型，配置变更触发）都是有效的 Config 规则。应维护 `oldestVersionSupported` 参数，不要假定版本目录会自动更新到当前版本。针对 encryptionConfig 的显式控制发现，并不意味着 EKS 1.28+ API 数据缺少默认 envelope encryption。

GuardDuty 审计分析不需要单独导出 CloudWatch 审计日志。Runtime Monitoring 需要受支持的安全代理/数据端点和实际覆盖范围；当前 EKS 支持 EC2 和 Auto Mode，不支持 Fargate 或 Hybrid Nodes。使用当前的 RUNTIME_MONITORING 功能，并审查旧版 EKS_RUNTIME_MONITORING 的迁移情况。不要将 EKS_AUDIT_LOGS 误认为运行时监控。

**CSPM 事件路由示例**：将其保存为 `security-event-pattern.json`。它会选取状态为 NEW/NOTIFIED 的活动 HIGH/CRITICAL ASFF 发现项。它有意不匹配使用不同 OCSF 事件架构的 `Findings Imported V2`：

```json
{
  "source": [
    "aws.securityhub"
  ],
  "detail-type": [
    "Security Hub Findings - Imported"
  ],
  "detail": {
    "findings": {
      "Severity": {
        "Label": [
          "HIGH",
          "CRITICAL"
        ]
      },
      "Workflow": {
        "Status": [
          "NEW",
          "NOTIFIED"
        ]
      },
      "RecordState": [
        "ACTIVE"
      ]
    }
  }
}
```

此合成事件仅用于模式检查；它并非真实发现，也不是完整的 ASFF 导入载荷。将以下内容保存为 `synthetic-security-event.json`：

```json
{
  "version": "0",
  "id": "00000000-0000-0000-0000-000000000001",
  "account": "123456789012",
  "region": "us-west-2",
  "time": "2026-09-11T00:00:00Z",
  "source": "aws.securityhub",
  "detail-type": "Security Hub Findings - Imported",
  "resources": [],
  "detail": {
    "findings": [
      {
        "Id": "synthetic-example-not-a-real-finding",
        "Severity": {
          "Label": "HIGH"
        },
        "Workflow": {
          "Status": "NEW"
        },
        "RecordState": "ACTIVE"
      }
    ]
  }
}
```

在经过授权的 AWS 测试中，`aws events test-event-pattern --event-pattern file://security-event-pattern.json --event file://synthetic-security-event.json --region us-west-2` 应匹配。还应测试 LOW 严重级别、RESOLVED/SUPPRESSED 工作流、ARCHIVED 状态、缺失字段和 V2 事件类型；这些都不应匹配此模式。本次审查检查的是 JSON/源架构，而不是 EventBridge 服务的匹配器或实时事件投递。

目标配置可以使用**现有且经过审查的 EventBridge 执行角色**，并授予其在自有 SNS 主题上发布的权限；当前 EventBridge 指南支持此方法。在替换为自有 ARN 后，将其保存为 `security-event-targets.json`：

```json
[
  {
    "Id": "SecurityAlerts",
    "Arn": "arn:aws:sns:us-west-2:123456789012:eks-security-alerts",
    "RoleArn": "arn:aws:iam::123456789012:role/EventBridgeSecurityAlerts"
  }
]
```

该角色需要正确的 EventBridge 信任关系和遵循最小权限原则的 sns:Publish 权限；应检查相关主题/密钥策略以及任何显式拒绝。或者，若目标不使用执行角色，则需要采用其支持的基于资源的权限路径。目标 JSON 本身不会授予权限，也不会创建规则、主题、角色或订阅。

使用 `aws events put-targets --rule eks-security-alerts --targets file://security-event-targets.json --region us-west-2` 前，应检查现有规则/目标的所有权。除了命令退出状态，还要检查 FailedEntryCount 和 FailedEntries。确认 SNS 订阅、加密权限、重试/死信行为，并执行受控端到端投递测试。本次审计期间未发送任何通知。

**审计调查**：在实际 EKS 日志组中，以下 Logs Insights 示例假设 Kubernetes 审计记录已进行 JSON 字段发现。它聚焦于 RBAC 修改请求；检查 responseStatus.code 以区分成功和被拒绝的请求：

```text
fields @timestamp, verb, user.username, objectRef.resource, objectRef.namespace, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter verb in ["create", "update", "patch", "delete", "deletecollection"]
| filter objectRef.resource in ["roles", "rolebindings", "clusterroles", "clusterrolebindings"]
| sort @timestamp desc
| limit 100
```

在依赖查询之前，应验证抽样记录的字段和流名称。保留相关证据，明确所有权/严重程度/升级路径，并测试响应流程。发现项仪表板和已启用的服务并不能证明修复已完成或合规义务已履行。

参考：[CSPM 标准](https://docs.aws.amazon.com/securityhub/latest/userguide/standards-view-manage.html)、[ASFF 事件](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-cwe-event-formats.html)、[V2 事件](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-v2-cwe-event-formats.html)、[EventBridge 目标权限](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html)、[EKS 审计日志](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)。

</details>

### 6. 对于需要集中管理 AWS 访问和生命周期的应用程序凭证，哪种方法更合适？

- A) 存储值，但不制定访问、轮换或重新加载计划
- B) 将环境变量视为加密机制
- C) 使用适当的 AWS 秘密/参数后端，并设计范围受限的身份及明确的交付/生命周期方案
- D) 将生产凭证硬编码到映像中

<details>
<summary>显示答案</summary>

**答案：C) 使用适当的 AWS 秘密/参数后端，并设计范围受限的身份及明确的交付/生命周期方案**

**说明：**

Secrets Manager 和 Parameter Store 可以集中管理 AWS 访问控制和审计，但如果没有工作负载身份、最小权限、交付和重新加载控制，外部后端并不会自动变得安全。Secrets Manager 可为受支持的凭证配置轮换；Parameter Store 不提供相同的内置凭证轮换工作流。SecureString 参数的 KMS 加密和版本控制，与更改目标数据库/服务中的凭证并不是一回事。

EKS 1.28+ 已使用默认的 KMS v2 envelope encryption 对所有 Kubernetes API 数据进行加密。Secret 清单中的 Base64 仍然只是编码，API/Pod 访问也可能暴露其值。环境变量是一种交付机制，而非加密方式；Secret 更改后，现有进程环境不会自动更新。

**审慎选择所有权和交付方式**：ESO 会写入 Kubernetes Secret。ASCP 与 Secrets Store CSI Driver 会将文件挂载到容器，并可选择同步 Kubernetes Secret。不要让两个控制器同时管理同一个目标 Secret。仅使用文件的 CSI 设计仍需要工作负载/节点访问控制；可选同步还会在 Kubernetes API 中额外生成一份值的副本。

**ASCP 示例**：这是针对经过审查的 EKS 1.36 示例新建的、自有 Linux EC2 安装，而不是在情况未知的现有集群上进行部署。首先检查现有版本/CSIDriver 所有权、节点兼容性、特权平台代理的准入、网络访问和调度情况。Fargate 无法运行 CSI 节点 DaemonSet。Hybrid/Auto Mode 的使用需要满足其当前的 provider/node 前提条件；以下本地渲染不能验证这些条件。

为单独管理的 CSI 1.6.1 driver 使用以下 `secrets-csi-values.yaml` 设置。它明确配置了两种 AWS 令牌受众、可选的 Secret 同步和轮换：

```yaml
tokenRequests:
- audience: sts.amazonaws.com
- audience: pods.eks.amazonaws.com
syncSecret:
  enabled: true
enableSecretRotation: true
rotationPollInterval: 2m
```

ASCP chart 3.1.3 通常会将 driver 作为依赖项包含在内，并配置其令牌受众。由于本示例单独安装 driver，请将以下内容保存为 `ascp-values.yaml`，以避免重复安装 driver：

```yaml
secrets-store-csi-driver:
  install: false
```



```bash
helm repo add secrets-store-csi-driver https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
helm repo add aws-secrets-manager https://aws.github.io/secrets-store-csi-driver-provider-aws
helm repo update secrets-store-csi-driver aws-secrets-manager
helm install csi-secrets-store secrets-store-csi-driver/secrets-store-csi-driver \
  --version 1.6.1 --namespace kube-system -f secrets-csi-values.yaml --wait --timeout 5m
helm install secrets-provider-aws aws-secrets-manager/secrets-store-csi-driver-provider-aws \
  --version 3.1.3 --namespace kube-system -f ascp-values.yaml --wait --timeout 5m
```

现有安装应遵循其所有者的版本/CRD 升级流程；不要运行这些全新安装命令，也不要在现有值无关的情况下执行部分 `helm upgrade`。固定 chart 版本并成功渲染，并不能证明节点插件兼容、网络连通或可以访问秘密。

准备一个自有的 Secrets Manager JSON secret，其中包含 username/password 字段；再准备一个作用范围精确限定为该 secret 的 `ASCPSecretReader` 角色，并在需要时授予适当的客户密钥解密权限。此 IRSA 信任关系使用精确的 ServiceAccount subject；请一致地替换完整的 OIDC issuer/provider 和账户信息：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/EXAMPLEOIDCID"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLEOIDCID:aud": "sts.amazonaws.com",
          "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLEOIDCID:sub": "system:serviceaccount:security-secrets-demo:ascp-reader"
        }
      }
    }
  ]
}
```

下面的 Namespace、ServiceAccount、SecretProviderClass 和 Pod 构成文件交付示例。应为实际集群选择适当的 PSS 版本。JMESPath 会将字段提取到别名中；secretObjects.data.objectName 指定这些挂载的别名。secretObjects.data 中不支持 property 字段。权限 0444 让这个非 root 演示进程可以读取文件；在实际应用中，应限制可以挂载/创建 Pod 的人员，并选择与应用 UID/GID/文件权限相兼容的设置。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-secrets-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ascp-reader
  namespace: security-secrets-demo
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ASCPSecretReader
automountServiceAccountToken: false
---
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: db-secrets-files
  namespace: security-secrets-demo
spec:
  provider: aws
  parameters:
    region: us-west-2
    usePodIdentity: 'false'
    objects: |
      - objectName: arn:aws:secretsmanager:us-west-2:123456789012:secret:training/db-credentials-ABC123
        objectType: secretsmanager
        objectAlias: credentials
        filePermission: '0444'
        jmesPath:
        - path: username
          objectAlias: db_username
        - path: password
          objectAlias: db_password
  secretObjects:
  - secretName: csi-db-credentials
    type: Opaque
    data:
    - objectName: db_username
      key: username
    - objectName: db_password
      key: password
---
apiVersion: v1
kind: Pod
metadata:
  name: secret-file-check
  namespace: security-secrets-demo
spec:
  serviceAccountName: ascp-reader
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: check
    image: busybox:1.37
    command:
    - sh
    - -c
    - test -s /mnt/secrets/db_username && test -s /mnt/secrets/db_password && sleep 3600
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    volumeMounts:
    - name: secrets
      mountPath: /mnt/secrets
      readOnly: true
  volumes:
  - name: secrets
    csi:
      driver: secrets-store.csi.k8s.io
      readOnly: true
      volumeAttributes:
        secretProviderClass: db-secrets-files
```

该 Pod 会检查文件是否存在，但不会打印其内容。`automountServiceAccountToken: false` 会禁用自动挂载的 Kubernetes API 令牌，但不会禁用 CSI driver 明确请求的令牌。若改用 Pod Identity 而不是此处的 IRSA 示例，应为工作负载 ServiceAccount 使用受支持的代理/关联，并设置 `usePodIdentity: "true"`；不要假定 IRSA 注解能提供该关联。

可选的 csi-db-credentials Secret 只有在 Pod 挂载卷后才会同步。其生命周期跟随使用该 Secret 的 Pod；删除所有使用者后，它可能会被删除。仅创建 SecretProviderClass 并不能独立生成 Secret。检查 SecretProviderClassPodStatus 和控制器/节点事件时，不要转储值。

对于 Parameter Store，可以将 objects 值替换为以下条目，同时为自有参数授予 provider 所需的 SSM 读取权限，并为 SecureString 授予适当的 KMS 访问权限。这是 objects 片段，而非完整的 SecretProviderClass：

```yaml
- objectName: /training/app/config
  objectType: ssmparameter
  objectAlias: app_config
  filePermission: "0444"
```

**ESO 替代方案**：使用源章节中为精确的 eso-reader ServiceAccount 准备的 EKSSecretReader IRSA 角色/信任关系。在其所有者已安装 ESO 2.10.0 和 v1 CRD 的前提下，以下内容会写入另一个目标 eso-db-credentials。后端 ARN、命名空间、角色和 JSON 属性必须引用实际准备好的 secret：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-secrets-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: eso-reader
  namespace: security-secrets-demo
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/EKSSecretReader
automountServiceAccountToken: false
---
apiVersion: external-secrets.io/v1
kind: SecretStore
metadata:
  name: aws-secretsmanager
  namespace: security-secrets-demo
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-west-2
      auth:
        jwt:
          serviceAccountRef:
            name: eso-reader
---
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: db-credentials
  namespace: security-secrets-demo
spec:
  refreshPolicy: Periodic
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: SecretStore
  target:
    name: eso-db-credentials
    creationPolicy: Owner
    deletionPolicy: Retain
  data:
    - secretKey: username
      remoteRef:
        key: arn:aws:secretsmanager:us-west-2:123456789012:secret:training/db-credentials-ABC123
        property: username
    - secretKey: password
      remoteRef:
        key: arn:aws:secretsmanager:us-west-2:123456789012:secret:training/db-credentials-ABC123
        property: password
```

这里的 Owner 会将目标 Secret 关联到 ExternalSecret；删除所有者可能会触发垃圾回收。Retain 针对的是后端消失的情况，并不能避免因所有者删除而被清理。ESO 的 serviceAccountRef JWT 方法使用的是 IRSA。控制器 Pod Identity 是另一种设计：应关联控制器的 ServiceAccount 并省略 store auth 块；ESO 无法使用 serviceAccountRef 来模拟另一个关联了 Pod Identity 的账户。

**轮换和重新加载**：CSI 1.6+ 使用 kubelet 的 RequiresRepublish 调用进行轮换。仅设置 requiresRepublish 并不会启用轮换；还必须启用 driver 的 enableSecretRotation 标志。此处的两分钟 rotationPollInterval 是最短缓存时长，并不保证端到端更新恰好在两分钟内完成；实际时间取决于 kubelet 的重新发布。ESO 的刷新间隔是另一个独立的协调周期。应用必须重新打开/监视已更新的文件，或执行受控滚动更新；subPath 挂载和现有环境变量不会自动刷新。

Secrets Manager 的 rotate-secret 默认会立即轮换。即使使用 `--no-rotate-immediately`，仍可能测试 Lambda 轮换函数并创建/删除 AWSPENDING，而较早设定的按频率/天数轮换计划也可能继续运行。这并不是无害的“仅设置计划”或只读检查。在调用轮换前，应审查目标凭证变更、有效期重叠、应用重新加载和回滚方案。

**不包含秘密值的 Terraform 示例**：Terraform 的 sensitive 仅会抑制所选输出的显示；普通的 secret_string/random_password 值仍可能存储在状态中。以下配置只管理 secret 元数据，并使用现有的已批准 KMS 密钥。对于已存在的 secret，应先通过所有者协调/导入，再由此配置管理：

```hcl
terraform {
  required_version = ">= 1.5.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.69.1"
    }
  }
}

variable "aws_region" {
  type    = string
  default = "us-west-2"
}

variable "kms_key_arn" {
  type        = string
  description = "Existing approved Secrets Manager encryption key ARN in this Region"
}

provider "aws" {
  region = var.aws_region
}

resource "aws_secretsmanager_secret" "credentials" {
  name                    = "training/db-credentials"
  kms_key_id              = var.kms_key_arn
  recovery_window_in_days = 30
  lifecycle {
    prevent_destroy = true
  }
}

output "secret_arn" {
  value = aws_secretsmanager_secret.credentials.arn
}
```

此配置不会创建 secret 版本/值，也不会启用轮换。应通过已批准的秘密输入流程提供初始值，而不要硬编码 Terraform 字符串或在明文命令参数中传递。即使预计仅处理元数据，也要保护状态文件和计划文件。prevent_destroy 是 Terraform 配置保护措施，并非不可逆的服务端保护；移除资源配置或在 Terraform 之外操作，都会改变其保护上下文。

验证覆盖了原生 Kubernetes 和已发布的 SecretProviderClass/ESO CRD、已发布 chart 的校验和、22 个渲染后的 CSI/ASCP 对象，以及对合成数据实际执行的 JMESPath 投影。仅在 Swagger 架构检查时省略生成的 null creationTimestamp 字段。Terraform fmt 检查通过；未运行 init/plan/apply。未获取、挂载、同步或轮换任何 AWS secret，也未测试应用重新加载。

参考：[ASCP 配置](https://github.com/aws/secrets-store-csi-driver-provider-aws)、[CSI 1.6.1](https://github.com/kubernetes-sigs/secrets-store-csi-driver/releases/tag/v1.6.1)、[CSI Secret 同步](https://secrets-store-csi-driver.sigs.k8s.io/topics/sync-as-kubernetes-secret)、[CSI 轮换](https://secrets-store-csi-driver.sigs.k8s.io/topics/secret-auto-rotation)、[ESO AWS 身份验证](https://github.com/external-secrets/external-secrets/blob/v2.10.0/docs/provider/aws-access.md)、[EKS envelope encryption](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html)、[Secrets Manager 轮换](https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/rotate-secret.html)。

</details>

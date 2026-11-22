# Amazon EKS 安全测验

> **最后更新**：2026年11月21日

本测验用于测试你对 Amazon EKS 安全功能、最佳实践和配置的理解。

## 测验概览
- 网络安全
- 容器安全
- 数据安全
- 合规与审计
- 安全最佳实践

有关集群访问身份验证、IRSA/OIDC 和 Pod Identity 的问题，请参阅各详细页面中的测验：[EKS 集群访问身份验证测验](./05-eks-security-cluster-access-quiz.md)、[IRSA 和 OIDC 提供商测验](./05-eks-security-irsa-oidc-quiz.md)、[EKS Pod Identity 测验](./05-eks-security-pod-identity-quiz.md)。

## 选择题

### 1. 在支持策略强制执行的 EKS 网络上，哪种 Kubernetes 机制可以表达基于标签的 Pod 流量规则？

- A) 仅使用实例安全组
- B) 使用具有强制执行能力的网络实现的 NetworkPolicy 资源
- C) 仅使用 VPC 端点策略
- D) 仅使用主机防火墙命令

<details>
<summary>显示答案</summary>

**答案：B) 使用具有强制执行能力的网络实现的 NetworkPolicy 资源**

**说明：**

NetworkPolicy 使用 Kubernetes 标签和命名空间选择 Pod 并规定允许的流量。它需要具有强制执行能力的网络实现。安全组（包括受支持的 Pod 安全组）仍然是有用的 AWS 控制措施；它们并非仅适用于整个实例。VPC 端点策略控制对受支持 AWS 服务的访问，而不是任意基于标签的 Pod 流量。

**完整策略示例**：这些清单描述的是一个隔离的演示命名空间，不是应用程序安装，也不能替代 CNI。示例假设使用标准 Linux EC2 节点、受支持且能够强制执行策略的 CNI，以及通常的 CoreDNS Deployment/Pod 标签。Auto Mode 或节点本地 DNS 需要针对实际使用的解析器路径配置规则。如果 CoreDNS 的入站流量受到限制，其所有者也必须允许这些查询。

请由命名空间所有者保存并应用这些清单。默认拒绝会隔离两个方向的流量；客户端出站流量和目标端入站流量已明确允许 frontend → API 和 API → database 的流量。DNS 需要同时允许 UDP 和 TCP：

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

监控端的对等项在同一个 peer 中同时使用 namespaceSelector **和** podSelector，因此只会选中 security-monitoring-demo 中匹配的 Prometheus Pod。如果该客户端被隔离了出站流量，其出站连接也需要获得许可：

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
| 选中的 Prometheus → api TCP 9090 | 允许 |
| 监控命名空间中的另一个 Pod → api TCP 9090 | 拒绝 |
| 工作负载 → 匹配的 CoreDNS Pod UDP/TCP 53 | 允许，但仍受解析器侧控制措施约束 |
| 任意外部目标 | 拒绝，除非添加了明确的出站规则 |

策略采用累加方式，不按顺序执行。其他宽泛的允许规则可能扩大允许范围；默认拒绝不会覆盖这些规则。请在目标 CNI 上测试完整的已安装策略集、DNS 解析以及新的允许/拒绝连接。已建立的连接、hostNetwork/节点流量和 NAT 行为都存在具体实现层面的限制；简单的 NetworkPolicy 不是通用的 IMDS 或主机防火墙边界。

对于外部服务，请限制实际目标地址/端口，或使用所选实现所支持的 DNS 感知型控制措施。允许目标为端口 443 上的所有地址或整个 10.0.0.0/8 范围，并不等于服务允许列表。在现有 EKS 网络上，任意替换成 Calico/Cilium 清单或使用不完整的 kube-proxy 替换标志，都不是启用策略的安全方法。

配套源材料中的 18 个合成选择器/端口用例已在本地检查；未执行数据包/CNI 测试。参考资料：[Kubernetes NetworkPolicy 行为](https://kubernetes.io/docs/concepts/services-networking/network-policies/)。

</details>

### 2. 哪种方法可以组合互补控制措施，保护 EKS 上的容器镜像安全？

- A) 仅依赖人工检查镜像
- B) 假设所有官方镜像都没有漏洞
- C) 组合使用扫描、签名/验证和准入控制
- D) 仅依赖容器内的防病毒软件

<details>
<summary>显示答案</summary>

**答案：C) 组合使用扫描、签名/验证和准入控制**

**说明：**

扫描器会识别其规则和漏洞数据库所覆盖的问题；它不能证明不存在任何后门或未来漏洞。签名可以根据配置的信任策略证明完整性以及身份关联，但不能证明签名的软件是安全的。准入控制会强制执行所选的部署策略。使用维护良好的精简基础镜像，及时重建以应用补丁，跟踪例外情况，并选择适当的 ECR 基础/增强型扫描模式或其他扫描模式。

**AWS Signer 和 Notation**：容器签名平台为 `Notation-OCI-SHA384-ECDSA`。使用 Notation AWS Signer 插件，按摘要对已推送的镜像进行签名。`Aws::ECR::Image` 平台或 `start-signing-job --source-image` 并非受支持的工作流。经审查的 AWS CLI 会拒绝该选项。

当前 ECR 托管式签名也是一种受支持的推送触发型替代方案，可使用注册表签名规则。如果选择这种方式，请配置正确的配置文件/权限，并在提升镜像之前等待实际签名状态。不要假设镜像已推送就代表异步签名已完成。

**信任配置**：准备经验证的 Notation/Signer 插件安装、正确分区的 AWS Signer 根信任存储，以及经审查的严格信任策略。下面的商业区域示例将信任范围限制为一个存储库和一个获准配置文件。请一致替换所有账户/区域/存储库/配置文件；不能仅仅因为签名者的证书链连接到 AWS 根证书就信任该签名者。

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

使用 `notation policy import notation-trust-policy.json` 将该策略导入构建环境所拥有的 Notation 配置。替换现有策略前应先审查；不要通过未经审查的脚本覆盖开发者共享的信任配置。构建角色需要限定到存储库范围的 ECR 拉取/推送操作、ECR 身份验证，以及所需的 SignPayload/GetRevocationStatus 权限。创建签名配置文件属于单独的预置工作；构建仅使用已有的获准配置文件时，无需 PutSigningProfile 权限。

**CodeBuild 示例**：这是一个 buildspec，不是 CodePipeline 定义。它要求使用一个自有的 Linux 构建镜像，并预先安装版本固定的 Bash、Python、Docker/守护进程访问、AWS CLI、Trivy、Notation 和 AWS Signer 插件。请分别配置项目所需的运行时特权、网络访问、扫描器数据库、IAM 角色、信任存储/策略和现有 ECR 存储库。Dockerfile 和源代码都是该构建角色所信任的输入。此示例使用已解析的 Git 提交和一个商业 AWS 账户/区域；它没有实现跨账户签名方案。

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

通过经审查的项目配置设置 `AWS_ACCOUNT_ID`、`AWS_REGION`、`ECR_REPOSITORY`（例如 `team/app`）和 `SIGNING_PROFILE_ARN`。该命令会对注册表主机名进行身份验证，保留嵌套存储库路径，在推送前扫描本地构建的镜像，并选择匹配的已推送 RepoDigest，而不是任意选择第一个条目或使用可变标签。此处的 Trivy 会阻止存在 HIGH/CRITICAL 漏洞发现的镜像；还应为机密、配置和来源证明添加其他经过明确设计的检查。

所有提升步骤都位于同一个 Bash 构建代码块中，并启用了 `set -euo pipefail`。登录/构建/扫描/推送/签名/验证任何一步失败，都会阻止写入新构件。CodeBuild 即使在构建失败后也可能运行 post_build，因此单独在 post_build 中执行未受保护的推送/签名步骤并不安全。预留的构件路径会先被清除，以防复用以前的输出。下游部署还必须要求构建成功并验证构件；JSON 文件本身既不是授权，也不是签名证明。

`verified-image.json` 包含供 EKS Deployment/GitOps 使用者使用的精确摘要引用。它不是 ECS `imagedefinitions.json`，也不会自行部署任何内容。签名/验证成功仍取决于实际的注册表访问权限、信任、吊销检查和 AWS Signer 可用性。

**准入**：生产环境中的签名验证器必须能够识别所选 Notation/Signer 签名和信任策略。AWS 记录了使用 Ratify 的 Gatekeeper 以及与 AWS Signer/Notation 集成的 Kyverno。仅安装通用策略引擎、使用没有 ConstraintTemplate 的 Gatekeeper 约束，或为不同签名方案配置公钥字段，都不能建立这种集成。在启用强制执行之前，应验证受信任/不受信任的配置文件、未签名镜像、摘要不匹配、已吊销/过期的签名、验证器中断和准入失败策略。

以下独立的 Kyverno 1.19.1 规则仅限制 security-demo 中的**镜像引用语法和存储库**。它会检查常规容器、init 容器和临时容器。它**并未**声称会验证签名：

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

验证情况：20 个模拟的流水线失败/顺序/构件用例，以及九个实际的 Kyverno CLI 字符串策略用例。已检查 buildspec/Bash/Python/JSON 和已发布的策略 CRD。没有构建/扫描/推送镜像，没有生成或验证真实 AWS 签名，也没有部署准入 Webhook。这是一个经过审查、明确列出环境假设的教学工作流，并非经过生产就绪性测试的工作流。

参考资料：[Signer 签名](https://docs.aws.amazon.com/signer/latest/developerguide/image-signing-steps.html)、[Signer 验证](https://docs.aws.amazon.com/signer/latest/developerguide/image-verification.html)、[ECR 托管式签名](https://docs.aws.amazon.com/AmazonECR/latest/userguide/managed-signing.html)、[EKS 准入验证](https://docs.aws.amazon.com/eks/latest/userguide/image-verification.html)、[CodeBuild buildspec](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html)、[Trivy 镜像标志](https://trivy.dev/docs/latest/references/configuration/cli/trivy_image/)。

</details>

### 3. 哪种方法可以在 EKS 上应用一致且与当前版本相符的 Pod 安全基线？

- A) 仅禁用特权模式
- B) 通过 PSA 使用带版本的 PSS 配置文件，并在需要时使用经审查的准入策略
- C) 仅设置非 root UID
- D) 仅将根文件系统设为只读

<details>
<summary>显示答案</summary>

**答案：B) 通过 PSA 使用带版本的 PSS 配置文件，并在需要时使用经审查的准入策略**

**说明：**

Pod Security Standards 定义了 Privileged、Baseline 和 Restricted 配置文件。Pod Security Admission 会强制执行按命名空间选择的配置文件。PSA 自 Kubernetes 1.25 起已成为稳定功能；PodSecurityPolicy 在 1.21 弃用，并且**已在 1.25 移除**。当前集群无法部署这个已移除的 API。Kyverno/Gatekeeper 策略是独立资源，即使较旧的示例在约束名称中使用了“PSP”也是如此。

以下是一个使用经审查的 v1.36 配置文件的隔离 Linux 示例：

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

Namespace 的 enforce 标签适用于 Pod 准入。Audit/warn 可以报告控制器模板违规，但 Deployment/Job 成功应用并不能证明其 Pod 能通过强制执行。更改标签不会追溯性地驱逐现有 Pod。应为实际集群选择策略版本，并在启用强制执行之前审查现有工作负载。

runAsNonRoot/runAsUser 和 seccomp 与 allowPrivilegeEscalation 和 capabilities 是不同的设置。fsGroup 是 Pod 级别的卷所有权设置，不是容器 capability。只读根文件系统是有用且兼容应用的加固措施，但并非 PSS Restricted 的通用要求，也不会使已挂载的 PVC 变为只读。实际应用需要兼容的 UID/GID 以及可写的临时文件/缓存/套接字路径；仅添加这些字段，并不能让面向 root 用户的通用 nginx 镜像正常运行。

**额外的范围限定准入规则**：此 Kyverno 1.19.1 ValidatingPolicy 会检查 security-demo 中所有常规、init 和临时容器。未设置 privileged 时按 false 处理；设置为 true 则拒绝。它使用当前 v1 策略 API，而不是过时的安装清单：

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

这条规则不能替代完整的 PSS 配置文件或镜像验证。应由平台所有者管理具有特权的 CSI/监控代理以及有意设置的例外；不要将演示策略一概应用于 kube-system。Gatekeeper 替代方案需要实际的 ConstraintTemplate、匹配约束和经过验证的行为。

清单/Schema 和六个实际的 Kyverno CLI 用例涵盖了未设置/false、特权常规/init/临时容器以及另一个命名空间。临时容器测试使用的是合成 UPDATE 对象，而不是创建 Pod。未执行实时准入 Webhook 或 Pod 部署。

参考资料：[Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/)、[Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)。

</details>

### 4. 哪种方法可以为 EKS 工作负载提供互补的安全证据？

- A) 仅进行偶尔的人工审查
- B) 仅使用 AWS Config 检查
- C) 仅使用 GuardDuty
- D) 结合安全态势发现、审计日志、运行时覆盖情况和经过验证的响应路径

<details>
<summary>显示答案</summary>

**答案：D) 结合安全态势发现、审计日志、运行时覆盖情况和经过验证的响应路径**

**说明：**

| 证据/控制措施 | 提供的内容及其不能证明的事项 |
|---|---|
| Security Hub CSPM / AWS Config | 受支持的配置控制措施和发现；不能证明 Kubernetes 或法规符合性已全面满足 |
| GuardDuty EKS Protection | 通过独立数据流对基于 Kubernetes 审计的威胁进行分析 |
| GuardDuty Runtime Monitoring | 在受支持节点上通过代理收集运行时事件；仅启用功能不能证明覆盖范围 |
| CloudTrail | AWS API 活动；不能替代 Kubernetes 审计日志或应用程序数据访问日志 |
| Kubernetes 审计日志 | 根据审计策略/级别选择的请求，不包括每项工作负载操作/请求正文 |
| CloudWatch / 事件升级路由 | 日志分析并将事件发送给运维人员；必须验证投递、保留和响应流程 |

Security Hub CSPM 的 FSBP 标准不是 CIS Kubernetes Benchmark。受支持的 CIS AWS Foundations 控制措施也不等于完整的 CIS Kubernetes 审计。请记录适用的基准/版本、人工检查、托管服务例外，以及工作负载实际义务所要求的证据。

请沿用现有的组织/区域所有权来管理检测器、CSPM 标准、Config 记录器和 CloudTrail。不要再创建一个区域检测器、覆盖集中式配置，或在未准备存储桶策略、加密、事件选择器和保留期限的情况下启动 trail。本次审查未预置账户级监控资源。

**EKS 专项检查**：按照源章节所述，启用并确认所需的控制平面日志类型、更新完成情况和日志到达情况。`eks-cluster-logging-enabled`（所有类型、定期检查）和 `eks-cluster-log-enabled`（可选指定类型、配置更改时检查）都是有效的 Config 规则。请维护 `oldestVersionSupported` 参数，不要假设版本目录会自动更新为当前版本。明确的 encryptionConfig 控制发现，并不意味着 EKS 1.28+ API 数据缺少默认信封加密。

GuardDuty 审计分析不需要单独导出 CloudWatch 审计日志。Runtime Monitoring 需要受支持的安全代理/数据端点和实际覆盖；当前 EKS 支持 EC2 和 Auto Mode，不支持 Fargate 或 Hybrid Nodes。请使用当前的 RUNTIME_MONITORING 功能，并审查从旧版 EKS_RUNTIME_MONITORING 迁移的情况。不要把 EKS_AUDIT_LOGS 误认为运行时监控。

**CSPM 事件路由示例**：将其保存为 `security-event-pattern.json`。它会选择状态为 NEW/NOTIFIED 的有效 HIGH/CRITICAL ASFF 发现。它有意不匹配不同的 `Findings Imported V2` OCSF 事件 Schema：

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

此合成事件仅用于模式检查；它不是真实发现，也不是完整的 ASFF 导入载荷。将其保存为 `synthetic-security-event.json`：

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

在经授权的 AWS 测试中，`aws events test-event-pattern --event-pattern file://security-event-pattern.json --event file://synthetic-security-event.json --region us-west-2` 应当匹配。还应测试 LOW 严重性、RESOLVED/SUPPRESSED 工作流、ARCHIVED 状态、字段缺失和 V2 事件类型；这些都不应匹配此模式。本次审查检查了 JSON/源 Schema，但未测试 EventBridge 服务的匹配器或实时事件投递。

目标配置可使用**现有且经过审查的 EventBridge 执行角色**，并授予其向自有 SNS 主题发布消息的权限；当前 EventBridge 指南支持此做法。替换为自有 ARN 后，将其保存为 `security-event-targets.json`：

```json
[
  {
    "Id": "SecurityAlerts",
    "Arn": "arn:aws:sns:us-west-2:123456789012:eks-security-alerts",
    "RoleArn": "arn:aws:iam::123456789012:role/EventBridgeSecurityAlerts"
  }
]
```

该角色需要正确的 EventBridge 信任关系和最小权限 sns:Publish 权限；检查适用的主题/密钥策略以及任何显式拒绝。或者，不使用执行角色的目标需要采用其受支持的基于资源的权限路径。目标 JSON 本身不会授予权限，也不会创建规则、主题、角色或订阅。

使用 `aws events put-targets --rule eks-security-alerts --targets file://security-event-targets.json --region us-west-2` 之前，应检查现有规则/目标的所有权。检查 FailedEntryCount 和 FailedEntries，而不只是命令的退出状态。确认 SNS 订阅、加密权限、重试/死信行为，并执行端到端的受控投递测试。本次审计期间未发送任何通知。

**审计调查**：在实际 EKS 日志组中，以下 Logs Insights 示例假设 Kubernetes 审计记录的 JSON 字段已被发现。它重点检查 RBAC 修改请求；请检查 responseStatus.code，以区分成功请求和被拒绝的请求：

```text
fields @timestamp, verb, user.username, objectRef.resource, objectRef.namespace, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter verb in ["create", "update", "patch", "delete", "deletecollection"]
| filter objectRef.resource in ["roles", "rolebindings", "clusterroles", "clusterrolebindings"]
| sort @timestamp desc
| limit 100
```

依赖此查询之前，请先验证抽样记录的字段和流名称。保留相关证据，明确所有权/严重性/升级流程，并测试响应流程。发现仪表板和已启用的服务并不能证明修复已完成或合规义务已履行。

参考资料：[CSPM 标准](https://docs.aws.amazon.com/securityhub/latest/userguide/standards-view-manage.html)、[ASFF 事件](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-cwe-event-formats.html)、[V2 事件](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-v2-cwe-event-formats.html)、[EventBridge 目标权限](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html)、[EKS 审计日志](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)。

</details>

### 5. 对于需要集中管理 AWS 访问权限和生命周期的应用程序凭证，哪种方法最合适？

- A) 存储值时不制定访问、轮换或重新加载方案
- B) 将环境变量视为一种加密机制
- C) 使用合适的 AWS 密钥/参数后端，并设计范围受限的身份以及明确的交付/生命周期方案
- D) 将生产凭证硬编码到镜像中

<details>
<summary>显示答案</summary>

**答案：C) 使用合适的 AWS 密钥/参数后端，并设计范围受限的身份以及明确的交付/生命周期方案**

**说明：**

Secrets Manager 和 Parameter Store 可以集中管理 AWS 访问控制和审计，但如果没有工作负载身份、最小权限、交付和重新加载控制，外部后端并不会自动变得安全。Secrets Manager 支持为受支持的凭证配置轮换；Parameter Store 不提供相同的内置凭证轮换工作流。SecureString 参数的 KMS 加密和版本控制，与更改目标数据库/服务中的凭证是两回事。

EKS 1.28+ 已通过默认 KMS v2 信封加密对所有 Kubernetes API 数据进行加密。Secret 清单中的 Base64 仍然只是编码，API/Pod 访问权限也可能暴露该值。环境变量是一种交付机制，不是加密方式；Secret 更改后，现有进程的环境变量不会更新。

**有意选择所有权和交付方式**：ESO 会写入 Kubernetes Secret。ASCP 与 Secrets Store CSI Driver 会挂载文件，并可选择同步 Kubernetes Secret。不要让两个控制器同时管理同一个目标 Secret。仅使用文件的 CSI 方案仍需要对工作负载/节点实施访问控制；启用可选同步也会在 Kubernetes API 中生成该值的副本。

**ASCP 示例**：这是为经审查的 EKS 1.36 示例新建、由自己管理的 Linux EC2 安装，并非向情况未知的现有集群推送更新。首先检查现有版本发布/CSIDriver 所有权、节点兼容性、特权平台代理的准入、网络访问和调度情况。Fargate 无法运行 CSI 节点 DaemonSet。Hybrid/Auto Mode 的使用需要符合当前的提供商/节点前提条件；以下本地渲染并未验证这些条件。

为单独管理的 CSI 1.6.1 驱动使用以下 `secrets-csi-values.yaml` 设置。它们会明确配置两个 AWS 令牌受众、可选的 Secret 同步和轮换：

```yaml
tokenRequests:
- audience: sts.amazonaws.com
- audience: pods.eks.amazonaws.com
syncSecret:
  enabled: true
enableSecretRotation: true
rotationPollInterval: 2m
```

ASCP Chart 3.1.3 通常会将该驱动作为依赖项包含在内，并配置其令牌受众。由于此示例单独安装驱动，请将以下内容保存为 `ascp-values.yaml`，以避免重复安装驱动：

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

现有安装需要遵循其所有者的版本/CRD 升级流程；不要对不相关的值运行这些全新安装命令或部分 `helm upgrade`。固定 Chart 版本并成功渲染，并不能证明节点插件兼容、网络连通或密钥访问正常。

准备一个由自己管理的 Secrets Manager JSON 密钥，其中包含 username/password 字段，以及一个将权限范围限制在该确切密钥的 `ASCPSecretReader` 角色；如有需要，还应授予相应的客户密钥解密权限。此 IRSA 信任关系使用精确的 ServiceAccount subject；请一致替换完整的 OIDC 签发者/提供商和账户：

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

以下 Namespace、ServiceAccount、SecretProviderClass 和 Pod 构成文件交付示例。请选择适用于实际集群的 PSS 版本。JMESPath 会将字段提取为别名；`secretObjects.data.objectName` 用于指定已挂载的别名。secretObjects.data 中不支持 property 字段。权限 0444 使这些文件可由此非 root 演示进程读取；对于真实应用，应限制可挂载/创建 Pod 的主体，并选择与应用兼容的 UID/GID/文件权限。

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

Pod 会检查文件是否存在，但不会打印其内容。`automountServiceAccountToken: false` 会禁用自动挂载 Kubernetes API 令牌，但不会禁用 CSI 驱动的显式令牌请求。如果使用 Pod Identity 代替此 IRSA 示例，请为工作负载 ServiceAccount 配置受支持的代理/关联，并将 `usePodIdentity: "true"`；不要假设 IRSA 注释会提供该关联。

可选的 csi-db-credentials Secret 只有在 Pod 挂载卷后才会同步。其生命周期取决于使用它的 Pod；删除所有使用者后，该 Secret 也可能被删除。仅创建 SecretProviderClass 并不会单独生成 Secret。在不转储值的情况下检查 SecretProviderClassPodStatus 和控制器/节点事件。

对于 Parameter Store，可以将 objects 值替换为以下条目，并为自有参数授予提供商所需的 SSM 读取权限，以及 SecureString 所需的适当 KMS 访问权限。这是 objects 片段，并非完整的 SecretProviderClass：

```yaml
- objectName: /training/app/config
  objectType: ssmparameter
  objectAlias: app_config
  filePermission: "0444"
```

**ESO 替代方案**：针对精确的 eso-reader ServiceAccount，使用源章节中预先准备的 EKSSecretReader IRSA 角色/信任关系。在安装并由其所有者管理 ESO 2.10.0 及其 v1 CRD 后，以下配置会写入另一个目标 eso-db-credentials。后端 ARN、命名空间、角色和 JSON 属性必须指向实际准备的密钥：

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

这里，Owner 会将目标 Secret 关联到 ExternalSecret；删除所有者可能触发垃圾回收。Retain 针对后端消失的情况，不代表不会因删除所有者而被删除。ESO 的 serviceAccountRef JWT 方法使用 IRSA。控制器 Pod Identity 是另一种设计：关联控制器 ServiceAccount，并省略 store auth 块；ESO 不能使用 serviceAccountRef 来模拟另一个关联了 Pod Identity 的账户。

**轮换和重新加载**：CSI 1.6+ 使用 kubelet 的 RequiresRepublish 调用进行轮换。单独设置 requiresRepublish 并不能启用轮换：还必须设置驱动的 enableSecretRotation 标志。此处的两分钟 rotationPollInterval 是最短缓存时长，并不保证端到端更新时间为两分钟；实际时机取决于 kubelet 的重新发布。ESO 的刷新间隔是另一套独立的协调计划。应用程序必须重新打开/监视更新后的文件，或执行受控滚动更新；subPath 挂载和现有环境变量不会自动刷新。

Secrets Manager 的 rotate-secret 默认会立即执行轮换。即使使用 `--no-rotate-immediately`，仍可能测试 Lambda 轮换函数并创建/删除 AWSPENDING，而较早设置的基于频率/日期的计划也可能继续运行。因此，这不是无害的仅计划或只读检查。调用轮换前，请审查目标凭证更改、有效期重叠、应用重新加载和回滚方案。

**不含密钥值的 Terraform 示例**：Terraform 的 sensitive 只能抑制选定的显示输出；普通的 secret_string/random_password 值仍可能存储在状态中。以下配置仅管理密钥元数据，并使用现有的获批 KMS 密钥。对于已存在的密钥，应先由其所有者协调/导入，再通过此配置管理：

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

此配置不会创建密钥版本/值，也不会启用轮换。请通过获批的密钥输入流程提供初始值，不要将其写成硬编码的 Terraform 字符串或明文命令行参数。即使预期只有元数据，也要保护状态和计划。prevent_destroy 是 Terraform 配置保护措施，并非不可逆的服务端保护；删除资源配置或在 Terraform 之外操作都会改变保护措施的适用情境。

验证涵盖原生 Kubernetes 以及已发布的 SecretProviderClass/ESO CRD、已发布的 Chart 校验和、22 个渲染后的 CSI/ASCP 对象，以及对合成数据执行的实际 JMESPath 投影。仅在 Swagger Schema 检查时省略了生成的 null creationTimestamp 字段。Terraform fmt 检查通过；未运行 init/plan/apply。没有获取、挂载、同步或轮换任何 AWS 密钥，也未测试应用重新加载。

参考资料：[ASCP 配置](https://github.com/aws/secrets-store-csi-driver-provider-aws)、[CSI 1.6.1](https://github.com/kubernetes-sigs/secrets-store-csi-driver/releases/tag/v1.6.1)、[CSI Secret 同步](https://secrets-store-csi-driver.sigs.k8s.io/topics/sync-as-kubernetes-secret)、[CSI 轮换](https://secrets-store-csi-driver.sigs.k8s.io/topics/secret-auto-rotation)、[ESO AWS 身份验证](https://github.com/external-secrets/external-secrets/blob/v2.10.0/docs/provider/aws-access.md)、[EKS 信封加密](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html)、[Secrets Manager 轮换](https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/rotate-secret.html)。

</details>

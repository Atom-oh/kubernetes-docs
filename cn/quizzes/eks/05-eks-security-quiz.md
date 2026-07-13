# Amazon EKS 安全测验

本测验用于检验你对 Amazon EKS 安全功能、最佳实践和配置的理解。

## 测验概览
- EKS 身份验证与授权
- 网络安全
- Container 安全
- 数据安全
- 合规与审计
- 安全最佳实践

## 多项选择题

### 1. 在 Amazon EKS 中，控制 Kubernetes API server 访问权限的最有效方式是什么？

A. 仅使用 IAM 用户和角色
B. 仅使用 Kubernetes RBAC
C. 使用集成的 IAM 和 Kubernetes RBAC
D. 仅使用对 API server 的网络访问限制

<details>
<summary>显示答案</summary>

**答案：C. 使用集成的 IAM 和 Kubernetes RBAC**

**解释：**
在 Amazon EKS 中，控制 Kubernetes API server 访问权限的最有效方式是使用 AWS IAM 与 Kubernetes RBAC（Role-Based Access Control）的集成。这种方法将 AWS 强大的身份管理能力与 Kubernetes 细粒度权限控制相结合，提供全面的安全模型。

**IAM 与 RBAC 集成的主要优势：**

1. **多层身份验证与授权**：
   - IAM 控制“谁”可以连接到 API server（身份验证）
   - RBAC 控制经过身份验证的用户“可以做什么”（授权）

2. **与 AWS Services 无缝集成**：
   - 利用现有的 AWS IAM policies 和 roles
   - 使用 AWS service accounts 和 workload identities

3. **细粒度权限控制**：
   - 为 namespaces、resource types 和特定 resources 定义详细权限
   - 实施最小权限原则

**实施方法：**

1. **配置 aws-auth ConfigMap**：
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: aws-auth
     namespace: kube-system
   data:
     mapRoles: |
       - rolearn: arn:aws:iam::123456789012:role/EKSAdminRole
         username: admin
         groups:
         - system:masters
       - rolearn: arn:aws:iam::123456789012:role/EKSDeveloperRole
         username: developer
         groups:
         - developers
     mapUsers: |
       - userarn: arn:aws:iam::123456789012:user/security-auditor
         username: security-auditor
         groups:
         - security-auditors
   ```

2. **定义 Kubernetes RBAC Roles 和 Bindings**：
   ```yaml
   # Developer role definition
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     namespace: dev
     name: developer
   rules:
   - apiGroups: ["", "apps", "batch"]
     resources: ["pods", "deployments", "jobs"]
     verbs: ["get", "list", "watch", "create", "update", "patch"]
   ---
   # Developer role binding
   apiVersion: rbac.authorization.k8s.io/v1
   kind: RoleBinding
   metadata:
     name: developer-binding
     namespace: dev
   subjects:
   - kind: Group
     name: developers
     apiGroup: rbac.authorization.k8s.io
   roleRef:
     kind: Role
     name: developer
     apiGroup: rbac.authorization.k8s.io
   ```

3. **IAM Policy 示例**：
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "eks:DescribeCluster",
           "eks:ListClusters"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

**最佳实践：**

1. **应用最小权限原则**：
   - 仅授予必要的最低权限
   - 定期审查和审计权限

2. **实施基于角色的访问**：
   - 根据工作职能定义 roles
   - 将权限分配给 roles，而不是个人

3. **使用临时凭证**：
   - 使用临时凭证而不是长期凭证
   - 利用 AWS STS (Security Token Service)

4. **定期审计和监控**：
   - 通过 CloudTrail 记录 API calls
   - 启用并分析 Kubernetes audit logs

**实际实施示例：**

1. **为 EKS Cluster 访问创建 IAM Role**：
   ```bash
   aws iam create-role \
     --role-name EKSDevRole \
     --assume-role-policy-document file://trust-policy.json

   aws iam attach-role-policy \
     --role-name EKSDevRole \
     --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy
   ```

2. **更新 kubeconfig**：
   ```bash
   aws eks update-kubeconfig \
     --name my-cluster \
     --role-arn arn:aws:iam::123456789012:role/EKSDevRole \
     --region us-west-2
   ```

3. **应用 RBAC Configuration**：
   ```bash
   kubectl apply -f rbac-config.yaml
   ```

其他选项的问题：
- **A. 仅使用 IAM 用户和角色**：IAM 可以控制 cluster 访问，但不能为 Kubernetes resources 提供细粒度权限。
- **B. 仅使用 Kubernetes RBAC**：RBAC 控制 cluster 内的权限，但缺少与 AWS Services 的集成，也不能提供 AWS infrastructure-level security。
- **D. 仅使用对 API server 的网络访问限制**：Network-level 控制很重要，但不能限制已验证用户的权限，也不能提供细粒度访问控制。
</details>
### 2. 在 Amazon EKS 中，限制 Pod 之间网络流量的最有效方式是什么？

A. 仅使用 security groups
B. 使用 Kubernetes Network Policies
C. 使用 VPC endpoint policies
D. 使用 host-based firewalls

<details>
<summary>显示答案</summary>

**答案：B. 使用 Kubernetes Network Policies**

**解释：**
在 Amazon EKS 中，限制 Pod 之间网络流量的最有效方式是使用 Kubernetes Network Policies。Network policies 在 Pod 级别提供微分段，允许对 Pod 之间的通信进行细粒度控制。

**Kubernetes Network Policies 的主要优势：**

1. **Pod 级别的细粒度控制**：
   - 基于 IP addresses、ports 和 protocols 进行过滤
   - 通过 label-based selectors 动态应用 policy
   - 同时控制 ingress 和 egress traffic

2. **声明式配置**：
   - 作为 Kubernetes resources 管理
   - 与 GitOps 和 IaC workflows 集成
   - 可进行版本控制和审计

3. **与 CNI Plugins 集成**：
   - 与 Amazon VPC CNI、Calico、Cilium 等集成
   - 提供多种 network policy enforcement 选项

**实施方法：**

1. **实施默认拒绝 Policy**：
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: default-deny
     namespace: prod
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     - Egress
   ```

2. **允许特定 Applications 之间通信**：
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: api-allow
     namespace: prod
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
   ```

3. **控制跨 namespace 通信**：
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: allow-from-monitoring
     namespace: prod
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     ingress:
     - from:
       - namespaceSelector:
           matchLabels:
             purpose: monitoring
       ports:
       - protocol: TCP
         port: 9090
   ```

**在 EKS 中实施 Network Policies：**

1. **选择兼容的 CNI Plugin**：
   - Amazon VPC CNI + Calico
   - Cilium
   - Antrea

2. **Calico 安装示例**：
   ```bash
   kubectl apply -f https://docs.projectcalico.org/manifests/calico-vxlan.yaml
   ```

3. **Cilium 安装示例**：
   ```bash
   helm repo add cilium https://helm.cilium.io/
   helm install cilium cilium/cilium \
     --namespace kube-system \
     --set nodeinit.enabled=true \
     --set kubeProxyReplacement=partial \
     --set hostServices.enabled=false \
     --set externalIPs.enabled=true \
     --set nodePort.enabled=true \
     --set hostPort.enabled=true \
     --set bpf.masquerade=false \
     --set image.pullPolicy=IfNotPresent
   ```

**最佳实践：**

1. **从默认拒绝 Policy 开始**：
   - 默认阻止所有流量
   - 仅显式允许必要通信

2. **应用最小权限原则**：
   - 仅允许必要的最低通信
   - 限制到特定 ports 和 protocols

3. **使用 Label-based Policies**：
   - 使用 labels 而不是 IP addresses
   - 在动态环境中提供灵活性

4. **测试和验证 Policies**：
   - 在非生产环境中测试 policies
   - 使用 network policy simulator tools

**实际实施示例：**

1. **用于 Microservices Architecture 的 Network Policy**：
   ```yaml
   # Allow only frontend to API communication
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: api-backend
     namespace: prod
   spec:
     podSelector:
       matchLabels:
         app: api
     policyTypes:
     - Ingress
     - Egress
     ingress:
     - from:
       - podSelector:
           matchLabels:
             app: frontend
       ports:
       - protocol: TCP
         port: 8080
     egress:
     - to:
       - podSelector:
           matchLabels:
             app: database
       ports:
       - protocol: TCP
         port: 5432
   ```

2. **限制 External Service 访问**：
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: limit-external
     namespace: prod
   spec:
     podSelector:
       matchLabels:
         app: backend
     policyTypes:
     - Egress
     egress:
     - to:
       - ipBlock:
           cidr: 10.0.0.0/8
     - to:
       - ipBlock:
           cidr: 0.0.0.0/0
           except:
           - 169.254.0.0/16
           - 10.0.0.0/8
       ports:
       - protocol: TCP
         port: 443
   ```

其他选项的问题：
- **A. 仅使用 security groups**：Security groups 在 instance 级别运行，不能提供 Pod 之间的细粒度流量控制。
- **C. 使用 VPC endpoint policies**：VPC endpoint policies 控制对 AWS Services 的访问，但不控制 Pod-to-Pod communication。
- **D. 使用 host-based firewalls**：Host-based firewalls 在 node 级别运行，无法有效控制同一 node 上运行的 Pod 之间的通信。
</details>
### 3. 在 Amazon EKS 中，增强 container image 安全性的最有效方法是什么？

A. 对所有 images 执行手动安全检查
B. 仅使用可信的 official images
C. 实施包含 image scanning、signature verification 和 admission policies 的集成 pipeline
D. 在 containers 内运行 antivirus software

<details>
<summary>显示答案</summary>

**答案：C. 实施包含 image scanning、signature verification 和 admission policies 的集成 pipeline**

**解释：**
在 Amazon EKS 中，增强 container image 安全性的最有效方法是实施一个包含 image scanning、signature verification 和 admission policies 的集成 pipeline。这种全面方法确保从 build 到 deployment 的整个 image 生命周期都具备安全性。

**集成 Image Security Pipeline 的关键组件：**

1. **Image Scanning**：
   - 检查已知 vulnerabilities (CVEs)
   - 检测 malware 和 backdoors
   - 识别 misconfigurations 和 security best practice violations

2. **Image Signing and Verification**：
   - 确保 image integrity
   - 验证 trusted sources
   - 防止篡改

3. **Admission Policies**：
   - 仅允许部署 approved images
   - 应用最低 base image 要求
   - 设置 vulnerability severity thresholds

**实施方法：**

1. **配置 Amazon ECR Image Scanning**：
   ```bash
   # Enable scanning when creating repository
   aws ecr create-repository \
     --repository-name my-app \
     --image-scanning-configuration scanOnPush=true

   # Enable scanning for existing repository
   aws ecr put-image-scanning-configuration \
     --repository-name my-app \
     --image-scanning-configuration scanOnPush=true
   ```

2. **使用 AWS Signer 签名 Images**：
   ```bash
   # Create signing profile
   aws signer put-signing-profile \
     --profile-name MyAppSigningProfile \
     --platform-id Aws::ECR::Image

   # Sign image
   aws signer start-signing-job \
     --source "s3={bucketName=my-bucket,key=my-image.tar}" \
     --destination "s3={bucketName=my-bucket,prefix=signed/}" \
     --profile-name MyAppSigningProfile
   ```

3. **使用 Kyverno 应用 Image Policies**：
   ```yaml
   apiVersion: kyverno.io/v1
   kind: ClusterPolicy
   metadata:
     name: require-signed-images
   spec:
     validationFailureAction: enforce
     rules:
     - name: verify-image-signature
       match:
         resources:
           kinds:
           - Pod
       verifyImages:
       - image: "*.dkr.ecr.*.amazonaws.com/*"
         key: "https://my-keystore.com/keys/my-key.pub"
   ```

4. **使用 OPA Gatekeeper 应用 Image Policies**：
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sTrustedImages
   metadata:
     name: trusted-repos
   spec:
     match:
       kinds:
       - apiGroups: [""]
         kinds: ["Pod"]
     parameters:
       repos:
       - "123456789012.dkr.ecr.us-west-2.amazonaws.com/*"
       - "docker.io/library/*"
   ```

**构建集成 Pipeline：**

1. **CI/CD Pipeline 集成**：
   ```yaml
   # AWS CodePipeline example
   version: 0.2
   phases:
     pre_build:
       commands:
         - echo Logging in to Amazon ECR...
         - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY_URI
     build:
       commands:
         - echo Building the Docker image...
         - docker build -t $ECR_REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION .
     post_build:
       commands:
         - echo Running security scan...
         - trivy image --exit-code 1 --severity HIGH,CRITICAL $ECR_REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION
         - echo Signing the image...
         - aws signer start-signing-job --profile-name MyAppSigningProfile --source-image $ECR_REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION
         - echo Pushing the Docker image...
         - docker push $ECR_REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION
   ```

2. **部署 Image Admission Controller**：
   ```bash
   # Install Kyverno
   kubectl create -f https://github.com/kyverno/kyverno/releases/download/v1.8.0/install.yaml

   # Apply policy
   kubectl apply -f image-policy.yaml
   ```

**最佳实践：**

1. **使用 Minimal Base Images**：
   - 最小化 attack surface
   - 仅包含必要 components
   - 使用 distroless 或 lightweight images

2. **实施 Defense in Depth**：
   - Build-time scanning
   - Pre-deployment validation
   - Runtime monitoring

3. **定期更新 Images**：
   - 应用最新 security patches
   - 定期更新 base images
   - 持续监控 vulnerabilities

4. **使用 Immutable Images**：
   - 部署后不要修改 images
   - 需要变更时 build 并 deploy 新 images
   - 支持 version management 和 rollback

**实际实施示例：**

1. **Amazon ECR、AWS CodePipeline 和 Kyverno 集成**：
   ```yaml
   # buildspec.yml
   version: 0.2
   phases:
     pre_build:
       commands:
         - echo Logging in to Amazon ECR...
         - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY_URI
         - COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)
         - IMAGE_TAG=${COMMIT_HASH:=latest}
     build:
       commands:
         - echo Building the Docker image...
         - docker build -t $ECR_REPOSITORY_URI:$IMAGE_TAG .
     post_build:
       commands:
         - echo Running Trivy security scan...
         - trivy image --exit-code 1 --severity HIGH,CRITICAL $ECR_REPOSITORY_URI:$IMAGE_TAG
         - echo Pushing the Docker image...
         - docker push $ECR_REPOSITORY_URI:$IMAGE_TAG
         - echo Creating image definition file...
         - aws ecr describe-images --repository-name $(echo $ECR_REPOSITORY_URI | cut -d'/' -f2) --image-ids imageTag=$IMAGE_TAG --query 'imageDetails[].imageTags[0]' --output text
   artifacts:
     files:
       - imagedefinitions.json
   ```

2. **Kyverno Image Policy**：
   ```yaml
   apiVersion: kyverno.io/v1
   kind: ClusterPolicy
   metadata:
     name: restrict-image-registries
   spec:
     validationFailureAction: enforce
     background: true
     rules:
     - name: allowed-registries
       match:
         resources:
           kinds:
           - Pod
       validate:
         message: "Only images from approved registries are allowed"
         pattern:
           spec:
             containers:
             - image: "{{ regex_match('123456789012.dkr.ecr.*.amazonaws.com/*|docker.io/library/*', '@@') }}"
   ```

其他选项的问题：
- **A. 对所有 images 执行手动安全检查**：Manual checks 不可扩展、缺乏一致性，并且在 continuous deployment environments 中不现实。
- **B. 仅使用可信的 official images**：即使 official images 也可能存在 vulnerabilities，而且通常需要 custom images。
- **D. 在 containers 内运行 antivirus software**：在 containers 内运行 antivirus 会使用大量 resources，违反 container design principles，并且无法解决 image build stage 的安全问题。
</details>
### 4. 在 Amazon EKS 中，增强 Pod 安全性的最有效方式是什么？

A. 对所有 Pod 禁用 privileged mode
B. 实施 Pod Security Standards (PSS) 和 Pod Security Policies (PSP)
C. 以 non-root users 运行所有 Pod
D. 对所有 Pod 使用 read-only file systems

<details>
<summary>显示答案</summary>

**答案：B. 实施 Pod Security Standards (PSS) 和 Pod Security Policies (PSP)**

**解释：**
在 Amazon EKS 中，增强 Pod 安全性的最有效方式是实施 Pod Security Standards (PSS) 和 Pod Security Policies (PSP)，或它们的替代机制。这些机制控制 Pod 的 security context，并在整个 cluster 中应用一致的安全标准。

**注意**：自 Kubernetes 1.25 起，PSP (Pod Security Policy) 已被弃用，建议改用带有 PSA (Pod Security Admission) 的 PSS (Pod Security Standards)。在 EKS 中，你可以使用 Kyverno 或 OPA Gatekeeper 等 policy engines 实现类似功能。

**Pod Security Standards 和 Policies 的主要优势：**

1. **应用一致的安全标准**：
   - 在整个 cluster 中应用一致的安全控制
   - 防止 privilege escalation
   - 降低 container escape risk

2. **支持多种安全级别**：
   - Privileged: 无限制
   - Baseline: 应用基本限制
   - Restricted: 应用严格安全控制

3. **细粒度安全控制**：
   - 限制 privilege escalation
   - 限制 host namespace access
   - 限制 volume types
   - 限制 user 和 group IDs

**实施方法：**

1. **应用 Pod Security Standards (PSS)**：
   ```yaml
   # Apply PSS labels to namespace
   apiVersion: v1
   kind: Namespace
   metadata:
     name: secure-ns
     labels:
       pod-security.kubernetes.io/enforce: restricted
       pod-security.kubernetes.io/audit: restricted
       pod-security.kubernetes.io/warn: restricted
   ```

2. **使用 Kyverno 实施 Pod Security Policy**：
   ```yaml
   apiVersion: kyverno.io/v1
   kind: ClusterPolicy
   metadata:
     name: restrict-privileged
   spec:
     validationFailureAction: enforce
     rules:
     - name: no-privileged-pods
       match:
         resources:
           kinds:
           - Pod
       validate:
         message: "Privileged mode is not allowed"
         pattern:
           spec:
             containers:
             - name: "*"
               securityContext:
                 privileged: false
   ```

3. **使用 OPA Gatekeeper 实施 Pod Security Policy**：
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sPSPPrivilegedContainer
   metadata:
     name: no-privileged-containers
   spec:
     match:
       kinds:
       - apiGroups: [""]
         kinds: ["Pod"]
   ```

**关键 Pod Security Controls：**

1. **限制 Privileged Mode**：
   ```yaml
   securityContext:
     privileged: false
   ```

2. **以 Non-root User 运行**：
   ```yaml
   securityContext:
     runAsUser: 1000
     runAsGroup: 3000
     fsGroup: 2000
   ```

3. **限制 Capabilities**：
   ```yaml
   securityContext:
     capabilities:
       drop:
       - ALL
       add:
       - NET_BIND_SERVICE
   ```

4. **Read-only Root Filesystem**：
   ```yaml
   securityContext:
     readOnlyRootFilesystem: true
   ```

5. **应用 seccomp Profile**：
   ```yaml
   securityContext:
     seccompProfile:
       type: RuntimeDefault
   ```

**最佳实践：**

1. **应用最小权限原则**：
   - 仅授予必要的最低权限
   - 限制 privileged mode 使用
   - 仅允许必要 capabilities

2. **实施 Defense in Depth**：
   - Namespace-level policies
   - Cluster-level policies
   - Runtime security monitoring

3. **显式定义 Security Context**：
   - 不要依赖 defaults
   - 为所有 containers 指定 security context
   - 定期审查 security configurations

4. **管理 Policy Exceptions**：
   - 需要 exceptions 时定义清晰流程
   - 定期审查和审计 exceptions
   - 尽量减少 exceptions

**实际实施示例：**

1. **安全增强的 Pod Definition**：
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: secure-pod
   spec:
     securityContext:
       fsGroup: 2000
       runAsNonRoot: true
       runAsUser: 1000
       seccompProfile:
         type: RuntimeDefault
     containers:
     - name: app
       image: my-secure-app:1.0
       securityContext:
         allowPrivilegeEscalation: false
         capabilities:
           drop:
           - ALL
         readOnlyRootFilesystem: true
         runAsNonRoot: true
         runAsUser: 1000
         seccompProfile:
           type: RuntimeDefault
   ```

2. **Kyverno Policy Collection**：
   ```yaml
   apiVersion: kyverno.io/v1
   kind: ClusterPolicy
   metadata:
     name: pod-security
   spec:
     validationFailureAction: enforce
     rules:
     - name: no-privileged
       match:
         resources:
           kinds:
           - Pod
       validate:
         message: "Privileged containers are not allowed"
         pattern:
           spec:
             containers:
             - name: "*"
               securityContext:
                 privileged: false
     - name: no-privilege-escalation
       match:
         resources:
           kinds:
           - Pod
       validate:
         message: "Privilege escalation is not allowed"
         pattern:
           spec:
             containers:
             - name: "*"
               securityContext:
                 allowPrivilegeEscalation: false
     - name: require-non-root
       match:
         resources:
           kinds:
           - Pod
       validate:
         message: "Running as root is not allowed"
         pattern:
           spec:
             containers:
             - name: "*"
               securityContext:
                 runAsNonRoot: true
   ```

其他选项的问题：
- **A. 对所有 Pod 禁用 privileged mode**：禁用 privileged mode 很重要，但它只是 Pod 安全性的一个方面，不能提供全面的安全策略。
- **C. 以 non-root users 运行所有 Pod**：以 non-root 运行是良好实践，但不能解决其他重要安全控制（例如 capabilities、volume mounts、host namespace access）。
- **D. 对所有 Pod 使用 read-only file systems**：Read-only file systems 是有用的安全控制，但并不适用于所有 applications，也不能解决其他重要安全方面。
</details>
### 5. 在 Amazon EKS 中，监控和审计安全合规性的最有效方法是什么？

A. 执行手动安全审查
B. 仅使用 AWS Config rules
C. 仅使用 AWS GuardDuty
D. 使用集成的 AWS Security Hub、GuardDuty、CloudTrail 和 Kubernetes audit logs

<details>
<summary>显示答案</summary>

**答案：D. 使用集成的 AWS Security Hub、GuardDuty、CloudTrail 和 Kubernetes audit logs**

**解释：**
在 Amazon EKS 中，监控和审计安全合规性的最有效方法是集成 AWS Security Hub、GuardDuty、CloudTrail 和 Kubernetes audit logs。这种集成方法在 infrastructure、cluster 和 application 层面提供全面的安全可见性。

**集成安全监控和审计的主要优势：**

1. **多层安全可见性**：
   - AWS infrastructure-level monitoring
   - Kubernetes cluster-level auditing
   - Container 和 application-level security events

2. **自动化合规检查**：
   - 验证是否符合行业标准和最佳实践
   - 检测 configuration drift
   - 持续合规监控

3. **集中式安全管理**：
   - 从单一 dashboard 查看安全状态
   - 集成 alerting 和 response
   - 全面的安全 reports

**实施方法：**

1. **启用 AWS Security Hub**：
   ```bash
   # Enable Security Hub
   aws securityhub enable-security-hub \
     --enable-default-standards \
     --tags Environment=Production
   ```

2. **启用 Amazon GuardDuty EKS Protection**：
   ```bash
   # Enable GuardDuty
   aws guardduty create-detector \
     --enable \
     --finding-publishing-frequency FIFTEEN_MINUTES

   # Enable EKS Protection
   aws guardduty update-detector \
     --detector-id $(aws guardduty list-detectors --query 'DetectorIds[0]' --output text) \
     --features '[{"Name": "EKS_RUNTIME_MONITORING", "Status": "ENABLED"}]'
   ```

3. **配置 CloudTrail Logging**：
   ```bash
   # Create CloudTrail trail
   aws cloudtrail create-trail \
     --name eks-audit-trail \
     --s3-bucket-name my-eks-audit-logs \
     --is-multi-region-trail \
     --enable-log-file-validation

   # Enable trail logging
   aws cloudtrail start-logging \
     --name eks-audit-trail
   ```

4. **启用 EKS Audit Logs**：
   ```bash
   # Enable audit logs when creating cluster
   aws eks create-cluster \
     --name my-cluster \
     --role-arn arn:aws:iam::123456789012:role/EKSClusterRole \
     --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345 \
     --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

   # Enable audit logs for existing cluster
   aws eks update-cluster-config \
     --name my-cluster \
     --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
   ```

**关键监控和审计组件：**

1. **AWS Security Hub**：
   - 应用 EKS best practice standards
   - CIS Kubernetes benchmark checks
   - 集中管理 security findings

2. **Amazon GuardDuty**：
   - EKS runtime monitoring
   - Container threat detection
   - Anomaly detection

3. **AWS CloudTrail**：
   - 记录 EKS control plane API calls
   - 跟踪 management events
   - 审计 user activity

4. **Kubernetes Audit Logs**：
   - 记录 in-cluster activity
   - 跟踪 API server requests
   - 监控 permission changes

5. **Amazon CloudWatch**：
   - 集中管理 logs
   - 监控 metrics
   - 配置 alerts

**最佳实践：**

1. **实施全面的 Logging Strategy**：
   - 启用所有相关 log sources
   - 设置适当的 log retention policies
   - 确保 log integrity

2. **配置自动化合规检查**：
   - 安排定期 compliance scans
   - 为 critical violations 配置 alerts
   - 自动生成 compliance reports

3. **为安全事件建立 Response Plans**：
   - 定义清晰的 escalation paths
   - 实施 automated responses
   - 定期测试 response plans

4. **应用最小权限原则**：
   - 限制对 audit logs 的访问
   - 对 security tools 使用 role-based access control
   - 定期审查权限

**实际实施示例：**

1. **AWS Security Hub 和 GuardDuty 集成**：
   ```bash
   # Send Security Hub findings to SNS topic
   aws events put-rule \
     --name SecurityHubFindings \
     --event-pattern '{"source":["aws.securityhub"],"detail-type":["Security Hub Findings - Imported"]}'

   aws events put-targets \
     --rule SecurityHubFindings \
     --targets 'Id"="1","Arn"="arn:aws:sns:us-west-2:123456789012:security-alerts"'
   ```

2. **使用 CloudWatch Logs Insights 分析 Audit Log**：
   ```
   fields @timestamp, @message
   | filter @logStream like /kube-apiserver-audit/
   | filter @message like "system:serviceaccount"
   | filter @message like "create" or @message like "update" or @message like "delete"
   | sort @timestamp desc
   | limit 100
   ```

3. **使用 AWS Config Rules 监控 EKS Configuration**：
   ```bash
   # Create Config rule to check if EKS cluster endpoint is public
   aws configservice put-config-rule \
     --config-rule file://eks-endpoint-rule.json
   ```

4. **使用 Terraform 配置 Security Monitoring Infrastructure**：
   ```hcl
   # Enable GuardDuty
   resource "aws_guardduty_detector" "main" {
     enable = true
     finding_publishing_frequency = "FIFTEEN_MINUTES"
   }

   # Enable EKS Protection
   resource "aws_guardduty_detector_feature" "eks_runtime" {
     detector_id = aws_guardduty_detector.main.id
     name        = "EKS_RUNTIME_MONITORING"
     status      = "ENABLED"
   }

   # Enable Security Hub
   resource "aws_securityhub_account" "main" {}

   # Enable EKS standards
   resource "aws_securityhub_standards_subscription" "cis_eks" {
     depends_on    = [aws_securityhub_account.main]
     standards_arn = "arn:aws:securityhub:${data.aws_region.current.name}::standards/aws-foundational-security-best-practices/v/1.0.0"
   }
   ```

其他选项的问题：
- **A. 执行手动安全审查**：Manual reviews 不可扩展，不能提供 real-time threat detection，并且容易出现人为错误。
- **B. 仅使用 AWS Config rules**：AWS Config 对监控 configuration compliance 很有用，但不能提供 runtime threat detection 或 comprehensive logging。
- **C. 仅使用 AWS GuardDuty**：GuardDuty 专注于 threat detection，但不能提供 configuration compliance checks 或 comprehensive audit logging。
</details>
### 6. 在 Amazon EKS 中，secrets management 的最安全方法是什么？

A. 使用默认设置的 Kubernetes Secrets
B. 将 secrets 作为 environment variables 传递
C. 与 AWS Secrets Manager 或 AWS Parameter Store 集成
D. 在 container images 中硬编码 secrets

<details>
<summary>显示答案</summary>

**答案：C. 与 AWS Secrets Manager 或 AWS Parameter Store 集成**

**解释：**
在 Amazon EKS 中，secrets management 的最安全方法是与 AWS Secrets Manager 或 AWS Parameter Store 等专用 secret management services 集成。这些服务提供高级安全功能，例如 encryption、access control、automatic rotation 和 auditing。

**AWS Secret Management Service 集成的主要优势：**

1. **强加密**：
   - 使用 AWS KMS 进行 encryption at rest
   - Encryption in transit
   - 细粒度 encryption key management

2. **细粒度访问控制**：
   - 通过 IAM policies 进行 access control
   - 应用最小权限原则
   - 支持 temporary credentials

3. **自动 Secret Rotation**：
   - 自动化定期 secret rotation
   - 在不中断 application 的情况下 rotate
   - 管理 rotation schedules 和 policies

4. **全面审计和日志记录**：
   - 审计 secret access
   - 与 CloudTrail 集成
   - 满足 compliance requirements

**实施方法：**

1. **与 AWS Secrets Manager 集成**：

   a. **安装 ASCP (AWS Secrets and Configuration Provider)**：
   ```bash
   helm repo add secrets-store-csi-driver https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
   helm install -n kube-system csi-secrets-store secrets-store-csi-driver/secrets-store-csi-driver

   kubectl apply -f https://raw.githubusercontent.com/aws/secrets-store-csi-driver-provider-aws/main/deployment/aws-provider-installer.yaml
   ```

   b. **创建 SecretProviderClass**：
   ```yaml
   apiVersion: secrets-store.csi.x-k8s.io/v1
   kind: SecretProviderClass
   metadata:
     name: aws-secrets
   spec:
     provider: aws
     parameters:
       objects: |
         - objectName: "prod/myapp/db-creds"
           objectType: "secretsmanager"
           objectAlias: "db-creds.json"
     secretObjects:
     - secretName: db-credentials
       type: Opaque
       data:
       - objectName: db-creds.json
         key: username
         property: username
       - objectName: db-creds.json
         key: password
         property: password
   ```

   c. **在 Pod 中挂载 Secrets**：
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: app
   spec:
     containers:
     - name: app
       image: myapp:1.0
       volumeMounts:
       - name: secrets-store
         mountPath: "/mnt/secrets"
         readOnly: true
       env:
       - name: DB_USERNAME
         valueFrom:
           secretKeyRef:
             name: db-credentials
             key: username
       - name: DB_PASSWORD
         valueFrom:
           secretKeyRef:
             name: db-credentials
             key: password
     volumes:
     - name: secrets-store
       csi:
         driver: secrets-store.csi.k8s.io
         readOnly: true
         volumeAttributes:
           secretProviderClass: aws-secrets
   ```

2. **与 AWS Parameter Store 集成**：

   a. **安装 External Secrets Operator**：
   ```bash
   helm repo add external-secrets https://charts.external-secrets.io
   helm install external-secrets external-secrets/external-secrets \
     -n external-secrets \
     --create-namespace
   ```

   b. **创建 SecretStore**：
   ```yaml
   apiVersion: external-secrets.io/v1beta1
   kind: SecretStore
   metadata:
     name: aws-parameter-store
   spec:
     provider:
       aws:
         service: ParameterStore
         region: us-west-2
         auth:
           jwt:
             serviceAccountRef:
               name: external-secrets-sa
   ```

   c. **创建 ExternalSecret**：
   ```yaml
   apiVersion: external-secrets.io/v1beta1
   kind: ExternalSecret
   metadata:
     name: db-credentials
   spec:
     refreshInterval: 1h
     secretStoreRef:
       name: aws-parameter-store
       kind: SecretStore
     target:
       name: db-credentials
     data:
     - secretKey: username
       remoteRef:
         key: /prod/myapp/db/username
     - secretKey: password
       remoteRef:
         key: /prod/myapp/db/password
   ```

**Secret Management 最佳实践：**

1. **应用最小权限原则**：
   - 仅授予对必要 secrets 的访问权限
   - 为每个 service account 使用 IAM roles
   - 定期权限审查

2. **实施 Automatic Secret Rotation**：
   ```bash
   # Configure AWS Secrets Manager automatic rotation
   aws secretsmanager rotate-secret \
     --secret-id prod/myapp/db-creds \
     --rotation-lambda-arn arn:aws:lambda:us-west-2:123456789012:function:RotateDBCreds \
     --rotation-rules '{"AutomaticallyAfterDays": 30}'
   ```

3. **增强 Secret Encryption**：
   ```bash
   # Encrypt secrets with customer-managed KMS key
   aws secretsmanager create-secret \
     --name prod/myapp/api-key \
     --secret-string '{"api-key": "abcdef12345"}' \
     --kms-key-id arn:aws:kms:us-west-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab
   ```

4. **审计 Secret Access**：
   ```bash
   # Filter CloudTrail events
   aws cloudtrail lookup-events \
     --lookup-attributes AttributeKey=EventName,AttributeValue=GetSecretValue
   ```

**实际实施示例：**

1. **AWS Secrets Manager 与 IRSA (IAM Roles for Service Accounts) 集成**：
   ```yaml
   # Create service account
   apiVersion: v1
   kind: ServiceAccount
   metadata:
     name: app-sa
     namespace: default
     annotations:
       eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/app-role
   ---
   # Deployment configuration
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: app
   spec:
     selector:
       matchLabels:
         app: myapp
     template:
       metadata:
         labels:
           app: myapp
       spec:
         serviceAccountName: app-sa
         containers:
         - name: app
           image: myapp:1.0
           volumeMounts:
           - name: secrets-store
             mountPath: "/mnt/secrets"
             readOnly: true
         volumes:
         - name: secrets-store
           csi:
             driver: secrets-store.csi.k8s.io
             readOnly: true
             volumeAttributes:
               secretProviderClass: aws-secrets
   ```

2. **使用 Terraform 配置 Secret Management Infrastructure**：
   ```hcl
   # Create AWS Secrets Manager secret
   resource "aws_secretsmanager_secret" "db_credentials" {
     name                    = "prod/myapp/db-creds"
     recovery_window_in_days = 7
     kms_key_id              = aws_kms_key.secrets_key.arn
   }

   resource "aws_secretsmanager_secret_version" "db_credentials" {
     secret_id     = aws_secretsmanager_secret.db_credentials.id
     secret_string = jsonencode({
       username = "dbuser",
       password = random_password.db_password.result
     })
   }

   # IAM role and policy
   resource "aws_iam_role" "app_role" {
     name = "app-role"
     assume_role_policy = jsonencode({
       Version = "2012-10-17",
       Statement = [{
         Effect = "Allow",
         Principal = {
           Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${module.eks.oidc_provider}"
         },
         Action = "sts:AssumeRoleWithWebIdentity",
         Condition = {
           StringEquals = {
             "${module.eks.oidc_provider}:sub" = "system:serviceaccount:default:app-sa"
           }
         }
       }]
     })
   }

   resource "aws_iam_policy" "secrets_access" {
     name = "secrets-access"
     policy = jsonencode({
       Version = "2012-10-17",
       Statement = [{
         Effect = "Allow",
         Action = [
           "secretsmanager:GetSecretValue",
           "secretsmanager:DescribeSecret"
         ],
         Resource = aws_secretsmanager_secret.db_credentials.arn
       }]
     })
   }

   resource "aws_iam_role_policy_attachment" "secrets_access" {
     role       = aws_iam_role.app_role.name
     policy_arn = aws_iam_policy.secrets_access.arn
   }
   ```

其他选项的问题：
- **A. 使用默认设置的 Kubernetes Secrets**：默认 Kubernetes Secrets 只是 base64-encoded（未加密），并且缺少 automatic rotation 或 fine-grained access control features。
- **B. 将 secrets 作为 environment variables 传递**：Environment variables 可能在 logs 中暴露，或通过 process information 被访问，并且缺少 automatic rotation 或 auditing features。
- **D. 在 container images 中硬编码 secrets**：在 images 中硬编码 secrets 会带来严重安全风险，并且在 secrets 需要 rotate 时需要 rebuild 和 redeploy images。
</details>

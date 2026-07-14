# Amazon EKS セキュリティクイズ

このクイズでは、Amazon EKS のセキュリティ機能、ベストプラクティス、設定に関する理解を確認します。

## クイズ概要
- EKS の認証と認可
- Network Security
- Container Security
- Data Security
- コンプライアンスと監査
- セキュリティのベストプラクティス

## 選択問題

### 1. Amazon EKS で Kubernetes API server へのアクセスを制御する最も効果的な方法は何ですか？

A. IAM users と roles のみを使用する
B. Kubernetes RBAC のみを使用する
C. 統合された IAM と Kubernetes RBAC を使用する
D. API server への network access restrictions のみを使用する

<details>
<summary>回答を表示</summary>

**回答: C. 統合された IAM と Kubernetes RBAC を使用する**

**解説:**
Amazon EKS で Kubernetes API server へのアクセスを制御する最も効果的な方法は、AWS IAM と Kubernetes RBAC (Role-Based Access Control) の統合を使用することです。このアプローチは、AWS の強力な identity management 機能と Kubernetes のきめ細かな permission control を組み合わせ、包括的な security model を提供します。

**IAM と RBAC 統合の主な利点:**

1. **多層の認証と認可**:
   - IAM は API server に接続できる「誰」を制御します（認証）
   - RBAC は認証済みユーザーが実行できる「何」を制御します（認可）

2. **AWS Services とのシームレスな統合**:
   - 既存の AWS IAM policies と roles を活用
   - AWS service accounts と workload identities を利用

3. **きめ細かな Permission Control**:
   - namespaces、resource types、特定の resources に対する詳細な permissions を定義
   - 最小権限の原則を実装

**実装方法:**

1. **aws-auth ConfigMap を設定する**:
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

2. **Kubernetes RBAC Roles と Bindings を定義する**:
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

3. **IAM Policy の例**:
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

**ベストプラクティス:**

1. **最小権限の原則を適用する**:
   - 必要最小限の permissions のみを付与
   - permissions を定期的にレビューおよび監査

2. **Role-based Access を実装する**:
   - 職務に基づいて roles を定義
   - 個人ではなく roles に permissions を割り当てる

3. **Temporary Credentials を使用する**:
   - 長期 credentials の代わりに temporary credentials を使用
   - AWS STS (Security Token Service) を活用

4. **定期的な監査と Monitoring**:
   - CloudTrail で API calls をログ記録
   - Kubernetes audit logs を有効化して分析

**実践的な実装例:**

1. **EKS Cluster Access 用の IAM Role を作成する**:
   ```bash
   aws iam create-role \
     --role-name EKSDevRole \
     --assume-role-policy-document file://trust-policy.json

   aws iam attach-role-policy \
     --role-name EKSDevRole \
     --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy
   ```

2. **kubeconfig を更新する**:
   ```bash
   aws eks update-kubeconfig \
     --name my-cluster \
     --role-arn arn:aws:iam::123456789012:role/EKSDevRole \
     --region us-west-2
   ```

3. **RBAC Configuration を適用する**:
   ```bash
   kubectl apply -f rbac-config.yaml
   ```

他の選択肢の問題点:
- **A. IAM users と roles のみを使用する**: IAM は cluster access を制御できますが、Kubernetes resources に対するきめ細かな permissions は提供しません。
- **B. Kubernetes RBAC のみを使用する**: RBAC は cluster 内の permissions を制御しますが、AWS services との統合がなく、AWS infrastructure-level security を提供しません。
- **D. API server への network access restrictions のみを使用する**: Network-level control は重要ですが、認証済みユーザーの permissions を制限せず、きめ細かな access control も提供しません。
</details>
### 2. Amazon EKS で pods 間の network traffic を制限する最も効果的な方法は何ですか？

A. security groups のみを使用する
B. Kubernetes Network Policies を使用する
C. VPC endpoint policies を使用する
D. host-based firewalls を使用する

<details>
<summary>回答を表示</summary>

**回答: B. Kubernetes Network Policies を使用する**

**解説:**
Amazon EKS で pods 間の network traffic を制限する最も効果的な方法は、Kubernetes Network Policies を使用することです。Network policies は pod レベルで microsegmentation を提供し、pods 間通信をきめ細かく制御できます。

**Kubernetes Network Policies の主な利点:**

1. **Pod レベルでのきめ細かな制御**:
   - IP addresses、ports、protocols に基づく filtering
   - label-based selectors による動的な policy application
   - ingress と egress traffic の両方を制御

2. **宣言的な設定**:
   - Kubernetes resources として管理
   - GitOps と IaC workflows との統合
   - version control と監査が可能

3. **CNI Plugins との統合**:
   - Amazon VPC CNI、Calico、Cilium などとの統合
   - network policy enforcement のためのさまざまな選択肢

**実装方法:**

1. **Default Deny Policy を実装する**:
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

2. **特定の Applications 間の通信を許可する**:
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

3. **namespace をまたぐ通信を制御する**:
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

**EKS での Network Policies の実装:**

1. **互換性のある CNI Plugin を選択する**:
   - Amazon VPC CNI + Calico
   - Cilium
   - Antrea

2. **Calico Installation Example**:
   ```bash
   kubectl apply -f https://docs.projectcalico.org/manifests/calico-vxlan.yaml
   ```

3. **Cilium Installation Example**:
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

**ベストプラクティス:**

1. **Default Deny Policy から開始する**:
   - デフォルトですべての traffic をブロック
   - 必要な通信のみを明示的に許可

2. **最小権限の原則を適用する**:
   - 必要最小限の通信のみを許可
   - 特定の ports と protocols に制限

3. **Label-based Policies を使用する**:
   - IP addresses ではなく labels を使用
   - 動的な環境で柔軟性を提供

4. **Policies をテストして検証する**:
   - non-production environments で policies をテスト
   - network policy simulator tools を利用

**実践的な実装例:**

1. **Microservices Architecture 用の Network Policy**:
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

2. **External Service Access を制限する**:
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

他の選択肢の問題点:
- **A. security groups のみを使用する**: security groups は instance レベルで動作し、pods 間のきめ細かな traffic control は提供しません。
- **C. VPC endpoint policies を使用する**: VPC endpoint policies は AWS services へのアクセスを制御しますが、pod-to-pod communication は制御しません。
- **D. host-based firewalls を使用する**: host-based firewalls は node レベルで動作し、同じ node 上で実行されている pods 間の通信を効果的に制御できません。
</details>
### 3. Amazon EKS で container image security を強化する最も効果的なアプローチは何ですか？

A. すべての images に手動の security checks を実施する
B. 信頼できる official images のみを使用する
C. image scanning、signature verification、admission policies を含む統合 pipeline を実装する
D. containers 内で antivirus software を実行する

<details>
<summary>回答を表示</summary>

**回答: C. image scanning、signature verification、admission policies を含む統合 pipeline を実装する**

**解説:**
Amazon EKS で container image security を強化する最も効果的なアプローチは、image scanning、signature verification、admission policies を含む統合 pipeline を実装することです。この包括的なアプローチにより、build から deployment まで image lifecycle 全体で security を確保できます。

**統合 Image Security Pipeline の主な構成要素:**

1. **Image Scanning**:
   - 既知の vulnerabilities (CVEs) を確認
   - malware と backdoors を検出
   - misconfigurations と security best practice violations を特定

2. **Image Signing and Verification**:
   - image integrity を確保
   - 信頼できる sources を検証
   - 改ざんを防止

3. **Admission Policies**:
   - approved images のみ deployment を許可
   - minimum base image requirements を適用
   - vulnerability severity thresholds を設定

**実装方法:**

1. **Amazon ECR Image Scanning を設定する**:
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

2. **AWS Signer を使用して Images に署名する**:
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

3. **Kyverno を使用して Image Policies を適用する**:
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

4. **OPA Gatekeeper を使用して Image Policies を適用する**:
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

**統合 Pipeline の構築:**

1. **CI/CD Pipeline Integration**:
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

2. **Image Admission Controller をデプロイする**:
   ```bash
   # Install Kyverno
   kubectl create -f https://github.com/kyverno/kyverno/releases/download/v1.8.0/install.yaml

   # Apply policy
   kubectl apply -f image-policy.yaml
   ```

**ベストプラクティス:**

1. **Minimal Base Images を使用する**:
   - attack surface を最小化
   - 必要な components のみを含める
   - distroless または lightweight images を使用

2. **Defense in Depth を実装する**:
   - build-time scanning
   - pre-deployment validation
   - runtime monitoring

3. **Images を定期的に更新する**:
   - 最新の security patches を適用
   - base images を定期的に更新
   - vulnerabilities を継続的に監視

4. **Immutable Images を使用する**:
   - deployment 後に images を変更しない
   - 変更が必要な場合は新しい images を build および deploy
   - version management と rollback をサポート

**実践的な実装例:**

1. **Amazon ECR、AWS CodePipeline、Kyverno の統合**:
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

2. **Kyverno Image Policy**:
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

他の選択肢の問題点:
- **A. すべての images に手動の security checks を実施する**: 手動チェックは scalable ではなく、一貫性に欠け、continuous deployment environments では実用的ではありません。
- **B. 信頼できる official images のみを使用する**: official images であっても vulnerabilities が存在する可能性があり、custom images が必要になることもよくあります。
- **D. containers 内で antivirus software を実行する**: containers 内で antivirus を実行すると多くの resources を使用し、container design principles に反し、image build stage の security issues に対処できません。
</details>
### 4. Amazon EKS で pod security を強化する最も効果的な方法は何ですか？

A. すべての pods で privileged mode を無効にする
B. Pod Security Standards (PSS) と Pod Security Policies (PSP) を実装する
C. すべての pods を non-root users として実行する
D. すべての pods で read-only file systems を使用する

<details>
<summary>回答を表示</summary>

**回答: B. Pod Security Standards (PSS) と Pod Security Policies (PSP) を実装する**

**解説:**
Amazon EKS で pod security を強化する最も効果的な方法は、Pod Security Standards (PSS) と Pod Security Policies (PSP)、またはそれらの replacement mechanisms を実装することです。これらの仕組みは pods の security context を制御し、cluster 全体に一貫した security standards を適用します。

**注記**: Kubernetes 1.25 以降、PSP (Pod Security Policy) は deprecated であり、代わりに PSS (Pod Security Standards) と PSA (Pod Security Admission) が推奨されています。EKS では、Kyverno や OPA Gatekeeper などの policy engines を使用して同様の機能を実装できます。

**Pod Security Standards and Policies の主な利点:**

1. **一貫した Security Standards を適用する**:
   - cluster 全体に一貫した security controls を適用
   - privilege escalation を防止
   - container escape risk を低減

2. **さまざまな Security Levels をサポート**:
   - Privileged: 制限なし
   - Baseline: 基本的な制限を適用
   - Restricted: 厳格な security controls を適用

3. **きめ細かな Security Controls**:
   - privilege escalation を制限
   - host namespace access を制限
   - volume types を制限
   - user and group IDs を制限

**実装方法:**

1. **Pod Security Standards (PSS) を適用する**:
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

2. **Kyverno を使用して Pod Security Policy を実装する**:
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

3. **OPA Gatekeeper を使用して Pod Security Policy を実装する**:
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

**主な Pod Security Controls:**

1. **Privileged Mode を制限する**:
   ```yaml
   securityContext:
     privileged: false
   ```

2. **Non-root User として実行する**:
   ```yaml
   securityContext:
     runAsUser: 1000
     runAsGroup: 3000
     fsGroup: 2000
   ```

3. **Capabilities を制限する**:
   ```yaml
   securityContext:
     capabilities:
       drop:
       - ALL
       add:
       - NET_BIND_SERVICE
   ```

4. **Read-only Root Filesystem**:
   ```yaml
   securityContext:
     readOnlyRootFilesystem: true
   ```

5. **seccomp Profile を適用する**:
   ```yaml
   securityContext:
     seccompProfile:
       type: RuntimeDefault
   ```

**ベストプラクティス:**

1. **最小権限の原則を適用する**:
   - 必要最小限の permissions のみを付与
   - privileged mode の使用を制限
   - 必要な capabilities のみを許可

2. **Defense in Depth を実装する**:
   - Namespace-level policies
   - Cluster-level policies
   - Runtime security monitoring

3. **Security Context を明示的に定義する**:
   - defaults に依存しない
   - すべての containers に security context を指定
   - security configurations を定期的にレビュー

4. **Policy Exceptions を管理する**:
   - exceptions が必要な場合の明確な processes を定義
   - exceptions を定期的にレビューおよび監査
   - exceptions を最小化

**実践的な実装例:**

1. **Security-enhanced Pod Definition**:
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

2. **Kyverno Policy Collection**:
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

他の選択肢の問題点:
- **A. すべての pods で privileged mode を無効にする**: privileged mode の無効化は重要ですが、pod security の一側面にすぎず、包括的な security strategy は提供しません。
- **C. すべての pods を non-root users として実行する**: non-root として実行することは良い practice ですが、他の重要な security controls（例: capabilities、volume mounts、host namespace access）には対応しません。
- **D. すべての pods で read-only file systems を使用する**: Read-only file systems は有用な security control ですが、すべての applications に適しているわけではなく、他の重要な security aspects には対応しません。
</details>
### 5. Amazon EKS で security compliance を監視および監査する最も効果的なアプローチは何ですか？

A. 手動の security reviews を実施する
B. AWS Config rules のみを使用する
C. AWS GuardDuty のみを使用する
D. 統合された AWS Security Hub、GuardDuty、CloudTrail、Kubernetes audit logs を使用する

<details>
<summary>回答を表示</summary>

**回答: D. 統合された AWS Security Hub、GuardDuty、CloudTrail、Kubernetes audit logs を使用する**

**解説:**
Amazon EKS で security compliance を監視および監査する最も効果的なアプローチは、AWS Security Hub、GuardDuty、CloudTrail、Kubernetes audit logs を統合することです。この統合アプローチにより、infrastructure、cluster、application レベルで包括的な security visibility を提供できます。

**統合 Security Monitoring and Auditing の主な利点:**

1. **多層の Security Visibility**:
   - AWS infrastructure-level monitoring
   - Kubernetes cluster-level auditing
   - Container and application-level security events

2. **自動化された Compliance Checks**:
   - industry standards と best practices への compliance を検証
   - configuration drift を検出
   - continuous compliance monitoring

3. **一元化された Security Management**:
   - 単一の dashboard から security status を確認
   - 統合された alerting と response
   - 包括的な security reports

**実装方法:**

1. **AWS Security Hub を有効化する**:
   ```bash
   # Enable Security Hub
   aws securityhub enable-security-hub \
     --enable-default-standards \
     --tags Environment=Production
   ```

2. **Amazon GuardDuty EKS Protection を有効化する**:
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

3. **CloudTrail Logging を設定する**:
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

4. **EKS Audit Logs を有効化する**:
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

**主な Monitoring and Auditing Components:**

1. **AWS Security Hub**:
   - EKS best practice standards を適用
   - CIS Kubernetes benchmark checks
   - security findings を一元化

2. **Amazon GuardDuty**:
   - EKS runtime monitoring
   - Container threat detection
   - Anomaly detection

3. **AWS CloudTrail**:
   - EKS control plane API calls をログ記録
   - management events を追跡
   - user activity を監査

4. **Kubernetes Audit Logs**:
   - in-cluster activity をログ記録
   - API server requests を追跡
   - permission changes を監視

5. **Amazon CloudWatch**:
   - logs を一元化
   - metrics を監視
   - alerts を設定

**ベストプラクティス:**

1. **包括的な Logging Strategy を実装する**:
   - すべての関連 log sources を有効化
   - 適切な log retention policies を設定
   - log integrity を確保

2. **自動化された Compliance Checks を設定する**:
   - 定期的な compliance scans をスケジュール
   - critical violations の alerts を設定
   - compliance reports を自動化

3. **Security Events への Response Plans を確立する**:
   - 明確な escalation paths を定義
   - automated responses を実装
   - response plans を定期的にテスト

4. **最小権限の原則を適用する**:
   - audit logs へのアクセスを制限
   - security tools に role-based access control を適用
   - permissions を定期的にレビュー

**実践的な実装例:**

1. **AWS Security Hub and GuardDuty Integration**:
   ```bash
   # Send Security Hub findings to SNS topic
   aws events put-rule \
     --name SecurityHubFindings \
     --event-pattern '{"source":["aws.securityhub"],"detail-type":["Security Hub Findings - Imported"]}'

   aws events put-targets \
     --rule SecurityHubFindings \
     --targets 'Id"="1","Arn"="arn:aws:sns:us-west-2:123456789012:security-alerts"'
   ```

2. **Audit Log Analysis with CloudWatch Logs Insights**:
   ```
   fields @timestamp, @message
   | filter @logStream like /kube-apiserver-audit/
   | filter @message like "system:serviceaccount"
   | filter @message like "create" or @message like "update" or @message like "delete"
   | sort @timestamp desc
   | limit 100
   ```

3. **AWS Config Rules で EKS Configuration を監視する**:
   ```bash
   # Create Config rule to check if EKS cluster endpoint is public
   aws configservice put-config-rule \
     --config-rule file://eks-endpoint-rule.json
   ```

4. **Terraform で Security Monitoring Infrastructure を設定する**:
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

他の選択肢の問題点:
- **A. 手動の security reviews を実施する**: 手動レビューは scalable ではなく、real-time threat detection を提供せず、human error が起こりやすいです。
- **B. AWS Config rules のみを使用する**: AWS Config は configuration compliance の監視に有用ですが、runtime threat detection や包括的な logging は提供しません。
- **C. AWS GuardDuty のみを使用する**: GuardDuty は threat detection に重点を置きますが、configuration compliance checks や包括的な audit logging は提供しません。
</details>
### 6. Amazon EKS で secrets management を行う最も安全なアプローチは何ですか？

A. default settings の Kubernetes Secrets を使用する
B. secrets を environment variables として渡す
C. AWS Secrets Manager または AWS Parameter Store と統合する
D. container images に secrets を hardcode する

<details>
<summary>回答を表示</summary>

**回答: C. AWS Secrets Manager または AWS Parameter Store と統合する**

**解説:**
Amazon EKS で secrets management を行う最も安全なアプローチは、AWS Secrets Manager や AWS Parameter Store のような専用の secret management services と統合することです。これらの services は、encryption、access control、automatic rotation、auditing などの高度な security features を提供します。

**AWS Secret Management Service Integration の主な利点:**

1. **強力な Encryption**:
   - AWS KMS を使用した encryption at rest
   - encryption in transit
   - きめ細かな encryption key management

2. **きめ細かな Access Control**:
   - IAM policies による access control
   - 最小権限の原則を適用
   - temporary credentials のサポート

3. **Automatic Secret Rotation**:
   - 定期的な secret rotation を自動化
   - application を中断せずに rotate
   - rotation schedules と policies を管理

4. **包括的な Auditing and Logging**:
   - secret access を監査
   - CloudTrail との統合
   - compliance requirements を満たす

**実装方法:**

1. **AWS Secrets Manager との統合**:

   a. **ASCP (AWS Secrets and Configuration Provider) をインストールする**:
   ```bash
   helm repo add secrets-store-csi-driver https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
   helm install -n kube-system csi-secrets-store secrets-store-csi-driver/secrets-store-csi-driver

   kubectl apply -f https://raw.githubusercontent.com/aws/secrets-store-csi-driver-provider-aws/main/deployment/aws-provider-installer.yaml
   ```

   b. **SecretProviderClass を作成する**:
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

   c. **Pod に Secrets をマウントする**:
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

2. **AWS Parameter Store との統合**:

   a. **External Secrets Operator をインストールする**:
   ```bash
   helm repo add external-secrets https://charts.external-secrets.io
   helm install external-secrets external-secrets/external-secrets \
     -n external-secrets \
     --create-namespace
   ```

   b. **SecretStore を作成する**:
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

   c. **ExternalSecret を作成する**:
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

**Secret Management のベストプラクティス:**

1. **最小権限の原則を適用する**:
   - 必要な secrets へのアクセスのみを付与
   - service account ごとに IAM roles を使用
   - 定期的な permission reviews

2. **Automatic Secret Rotation を実装する**:
   ```bash
   # Configure AWS Secrets Manager automatic rotation
   aws secretsmanager rotate-secret \
     --secret-id prod/myapp/db-creds \
     --rotation-lambda-arn arn:aws:lambda:us-west-2:123456789012:function:RotateDBCreds \
     --rotation-rules '{"AutomaticallyAfterDays": 30}'
   ```

3. **Secret Encryption を強化する**:
   ```bash
   # Encrypt secrets with customer-managed KMS key
   aws secretsmanager create-secret \
     --name prod/myapp/api-key \
     --secret-string '{"api-key": "abcdef12345"}' \
     --kms-key-id arn:aws:kms:us-west-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab
   ```

4. **Secret Access を監査する**:
   ```bash
   # Filter CloudTrail events
   aws cloudtrail lookup-events \
     --lookup-attributes AttributeKey=EventName,AttributeValue=GetSecretValue
   ```

**実践的な実装例:**

1. **AWS Secrets Manager と IRSA (IAM Roles for Service Accounts) の統合**:
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

2. **Terraform で Secret Management Infrastructure を設定する**:
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

他の選択肢の問題点:
- **A. default settings の Kubernetes Secrets を使用する**: default の Kubernetes Secrets は base64-encoded（encrypted ではない）だけであり、automatic rotation やきめ細かな access control features がありません。
- **B. secrets を environment variables として渡す**: Environment variables は logs に露出したり process information からアクセスされたりする可能性があり、automatic rotation や auditing features もありません。
- **D. container images に secrets を hardcode する**: images に secrets を hardcode すると深刻な security risks が生じ、secrets を rotate する必要がある場合に images の rebuild と redeploy が必要になります。
</details>

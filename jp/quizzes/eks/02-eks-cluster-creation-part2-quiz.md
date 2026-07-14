# EKS Cluster Creation クイズ - Part 2

このクイズでは、Amazon EKS cluster 作成に関連する高度な concepts、security settings、networking configurations についての理解を確認します。cluster security、network policies、service accounts などのトピックを扱います。

## 基本概念の問題

1. Amazon EKS cluster における IRSA (IAM Roles for Service Accounts) の主な目的は何ですか？
   * A) cluster administrators に IAM permissions を付与する
   * B) worker nodes に IAM roles を割り当てる
   * C) Kubernetes service accounts に AWS service access permissions を付与する
   * D) EKS control plane に IAM permissions を付与する

<details>

<summary>答えを表示</summary>

**答え: C) Kubernetes service accounts に AWS service access permissions を付与する**

**解説:** IRSA (IAM Roles for Service Accounts) の主な目的は、Kubernetes service accounts に AWS service access permissions を付与することです。この機能により、pod level で fine-grained permissions を提供でき、node-level IAM roles を共有する代わりに、各 application に必要最小限の permissions のみを付与できます。

**IRSA の仕組み:**

1.  **OpenID Connect (OIDC) Provider Setup**:

    * EKS cluster は OIDC provider として設定されます。
    * これにより、Kubernetes service account tokens が AWS IAM における信頼された authentication mechanism になります。

    ```bash
    # Associate OIDC provider
    eksctl utils associate-iam-oidc-provider --cluster my-cluster --approve
    ```
2.  **IAM Role の作成と Trust Policy の設定**:

    * Kubernetes service account が assume できる IAM role を作成します。
    * trust policy は、特定の namespaces 内の特定の service accounts のみが role を assume できるように制限します。

    ```json
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.region.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE"
          },
          "Action": "sts:AssumeRoleWithWebIdentity",
          "Condition": {
            "StringEquals": {
              "oidc.eks.region.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:sub": "system:serviceaccount:default:my-service-account"
            }
          }
        }
      ]
    }
    ```
3.  **Service Account の作成と IAM Role の関連付け**:

    * IAM role ARN を annotation として service account に追加します。

    ```yaml
    apiVersion: v1
    kind: ServiceAccount
    metadata:
      name: my-service-account
      namespace: default
      annotations:
        eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/my-role
    ```
4.  **Pod で Service Account を使用**:

    * pod manifest で service account を指定します。

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: my-pod
    spec:
      serviceAccountName: my-service-account
      containers:
      - name: my-container
        image: my-image
    ```

**IRSA の利点:**

1. **Principle of Least Privilege**:
   * 各 application に必要最小限の permissions のみを付与できます。
   * node-level IAM roles を共有する代わりに、pod ごとに異なる permission settings を使用できます。
2. **Enhanced Security**:
   * AWS credentials を code や environment variables に保存する必要がありません。
   * credential leakage のリスクを低減します。
3. **Permission Isolation**:
   * 同じ node 上で実行される異なる pods が、異なる IAM permissions を持つことができます。
   * multi-tenant environments で重要です。
4. **Simplified Credential Management**:
   * AWS credentials を直接管理する必要がありません。
   * credential rotation は自動的に処理されます。

**eksctl を使用した IRSA Setup の例:**

```bash
# Create service account and IAM role
eksctl create iamserviceaccount \
  --name my-service-account \
  --namespace default \
  --cluster my-cluster \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
  --approve

# Verify created service account
kubectl get serviceaccount my-service-account -o yaml
```

**その他の選択肢の問題点:**

* **cluster administrators に IAM permissions を付与する**: これは IRSA の目的ではありません。cluster administrator permissions は通常、aws-auth ConfigMap を通じて管理されます。
* **worker nodes に IAM roles を割り当てる**: これは node IAM roles を通じて行われ、IRSA とは別のものです。Node IAM roles はすべての pods で共有されるため、principle of least privilege に違反する可能性があります。
* **EKS control plane に IAM permissions を付与する**: EKS control plane permissions は cluster IAM role を通じて管理され、IRSA とは関係ありません。

IRSA は、Kubernetes workloads が AWS services に安全にアクセスできるようにする重要な機能であり、EKS clusters で applications を実行する際の推奨 approach です。

</details>

2\. Amazon EKS cluster における security groups の主な役割は何ですか？ - A) pods 間の network traffic を制御する - B) cluster API server と nodes 間の traffic を制御する - C) Kubernetes RBAC policies を適用する - D) user authentication を管理する

<details>

<summary>答えを表示</summary>

**答え: B) cluster API server と nodes 間の traffic を制御する**

**解説:** Amazon EKS cluster における security groups の主な役割は、cluster API server と nodes 間の traffic を制御することです。Security groups は、EC2 instance level で inbound と outbound traffic を制御する AWS virtual firewalls です。EKS には cluster security groups と node security groups があり、cluster components 間の communication を保護します。

**EKS Clusters における Security Groups の種類:**

1. **Cluster Security Group**:
   * EKS control plane に適用されます。
   * worker nodes と control plane 間の communication を許可します。
   * EKS cluster 作成時に default で自動作成されます。
   * 主要 rules:
     * node security group から port 443 への inbound traffic を許可
     * node security group への outbound traffic を許可
2. **Node Security Group**:
   * worker nodes に適用されます。
   * nodes 間、および nodes と control plane 間の communication を許可します。
   * 主要 rules:
     * nodes 間のすべての traffic を許可
     * cluster security group への port 443 の outbound traffic を許可
     * cluster security group からの inbound traffic を許可
     * kubelet 用に port 10250 を許可

**Security Group Configuration Examples:**

**Cluster Security Group Rules**:

```
Inbound:
- Protocol: TCP
- Port Range: 443
- Source: Node Security Group

Outbound:
- Protocol: All Traffic
- Port Range: All Ports
- Destination: 0.0.0.0/0
```

**Node Security Group Rules**:

```
Inbound:
- Protocol: All Traffic
- Source: Node Security Group itself (node-to-node communication)

- Protocol: TCP
- Port Range: 10250
- Source: Cluster Security Group (kubelet communication)

Outbound:
- Protocol: All Traffic
- Port Range: All Ports
- Destination: 0.0.0.0/0
```

**Security Groups のカスタマイズ:**

EKS cluster を作成する際に custom security groups を指定できます:

```bash
# Specifying custom security groups using AWS CLI
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
  --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345

# Specifying custom security groups using eksctl
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
vpc:
  id: vpc-12345
  securityGroup: sg-12345
  subnets:
    private:
      us-west-2a: subnet-12345
      us-west-2b: subnet-67890
```

**Pods 向け Security Groups:**

最近では、EKS は pod-level security groups (SecurityGroupsForPods feature) もサポートしています。これにより、individual pods に security groups を適用できます:

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: my-security-group-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: my-app
  securityGroups:
    groupIds:
      - sg-12345
```

**その他の選択肢の問題点:**

* **pods 間の network traffic を制御する**: default では、pods 間の network traffic は AWS security groups ではなく、Kubernetes Network Policies (NetworkPolicy) を通じて制御されます。SecurityGroupsForPods feature により pod level で security groups を適用できますが、これは security groups の primary role ではありません。
* **Kubernetes RBAC policies を適用する**: RBAC (Role-Based Access Control) は Kubernetes API resources への access を制御する mechanism であり、AWS security groups とは別のものです。
* **user authentication を管理する**: EKS clusters における user authentication は AWS IAM と Kubernetes RBAC の integration を通じて管理され、security groups とは関係ありません。

Security groups は EKS clusters の network security において重要な役割を果たし、cluster components 間の communication を保護し、不要な traffic を block します。適切な security group configuration は、EKS clusters の security posture を強化するために不可欠です。

</details>

3. Amazon EKS cluster で Kubernetes Network Policies を実装するために必要なものは何ですか？
   * A) AWS security group configuration
   * B) Calico や Cilium など、network policies をサポートする CNI plugin
   * C) AWS Network Firewall setup
   * D) VPC Flow Logs enabled

<details>

<summary>答えを表示</summary>

**答え: B) Calico や Cilium など、network policies をサポートする CNI plugin**

**解説:** Amazon EKS cluster で Kubernetes Network Policies を実装するには、Calico や Cilium など、network policies をサポートする CNI (Container Network Interface) plugin が必要です。default の Amazon VPC CNI plugin は network policies をサポートしていないため、additional components をインストールする必要があります。

**Network Policy Support を備えた CNI Options:**

1. **Calico**:
   * 広く使用されている open-source networking and network security solution
   * EKS で Amazon VPC CNI と併用できます。
   *   Installation method:

       ```bash
       # Install Calico using Helm
       helm repo add projectcalico https://docs.projectcalico.org/charts
       helm install calico projectcalico/tigera-operator --namespace tigera-operator --create-namespace

       # Or install using manifest files
       kubectl apply -f https://docs.projectcalico.org/manifests/calico-vxlan.yaml
       ```
2. **Cilium**:
   * eBPF-based networking, security, and observability solution
   * high performance と advanced features を提供します。
   *   Installation method:

       ```bash
       # Install Cilium using Helm
       helm repo add cilium https://helm.cilium.io/
       helm install cilium cilium/cilium --namespace kube-system
       ```
3. **AWS CNI with Cilium**:
   * Amazon VPC CNI と Cilium を併用する hybrid approach
   * VPC CNI が pod networking を処理し、Cilium が network policies を処理します。
   *   Installation method:

       ```bash
       # Install Cilium in network policy only mode
       helm install cilium cilium/cilium --namespace kube-system \
         --set enableIPv4Masquerade=false \
         --set tunnel=disabled \
         --set installIptablesRules=false \
         --set autoDirectNodeRoutes=false \
         --set policyEnforcementMode=default
       ```

**Network Policy Examples:**

```yaml
# Default deny policy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress

# Allow communication between specific applications
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: backend
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

**Network Policy Implementation の確認:**

```bash
# Verify network policy support
kubectl get pods -n kube-system | grep -E 'calico|cilium'

# Apply test network policy
kubectl apply -f test-network-policy.yaml

# Test connectivity
kubectl run -it --rm --restart=Never busybox --image=busybox -- wget -O- --timeout=2 http://service-name
```

**その他の選択肢の問題点:**

* **AWS security group configuration**: AWS security groups は EC2 instance level で動作し、Kubernetes pods 間の fine-grained network policies の実装には使用できません。SecurityGroupsForPods feature により security groups を pods に適用できますが、これは Kubernetes NetworkPolicy とは異なる mechanism です。
* **AWS Network Firewall setup**: AWS Network Firewall は VPC level で動作し、Kubernetes pods 間の fine-grained network policies の実装には使用できません。
* **VPC Flow Logs enabled**: VPC Flow Logs は network traffic の monitoring と logging に使用されますが、network policies の実装には使用できません。

Network policies は、microservices 間の communication を制御し、Kubernetes clusters 内の security を強化するための重要な tool です。EKS で network policies を実装するには、Calico や Cilium などの additional CNI plugins をインストールする必要があります。

</details>

4. Amazon EKS cluster で Secrets encryption を設定する正しい方法は何ですか？
   * A) EKS cluster 作成時に AWS KMS key を使用して encryption を有効化する
   * B) Kubernetes Secrets を AWS Secrets Manager に移行する
   * C) すべての Secrets を Base64 で encode する
   * D) EKS cluster に encryption sidecar container を deploy する

<details>

<summary>答えを表示</summary>

**答え: A) EKS cluster 作成時に AWS KMS key を使用して encryption を有効化する**

**解説:** Amazon EKS cluster で Secrets encryption を設定する正しい方法は、EKS cluster の作成時、または existing cluster で AWS KMS (Key Management Service) key を使用して encryption を有効化することです。この方法により、Kubernetes Secrets が etcd に保存される際に encrypted されます。

**EKS Secrets Encryption を設定する手順:**

1.  **KMS Key の作成または Existing Key の使用**:

    ```bash
    # Create KMS key
    aws kms create-key --description "EKS Secrets Encryption Key"

    # Store the created key ID
    KEY_ID=$(aws kms create-key --query KeyMetadata.KeyId --output text)
    ```
2.  **New Cluster 作成時に Encryption を有効化**:

    ```bash
    # Enable encryption using AWS CLI
    aws eks create-cluster \
      --name my-cluster \
      --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
      --resources-vpc-config subnetIds=subnet-12345,subnet-67890 \
      --encryption-config '[{"resources":["secrets"],"provider":{"keyArn":"arn:aws:kms:region:123456789012:key/'$KEY_ID'"}}]'

    # Enable encryption using eksctl
    cat > cluster.yaml << EOF
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig
    metadata:
      name: my-cluster
      region: us-west-2
    secretsEncryption:
      keyARN: arn:aws:kms:us-west-2:123456789012:key/$KEY_ID
    EOF

    eksctl create cluster -f cluster.yaml
    ```
3.  **Existing Cluster で Encryption を有効化**:

    ```bash
    # For existing clusters, you cannot update the encryption configuration, so you need to create a new cluster and migrate workloads.
    ```
4.  **Encryption Configuration の確認**:

    ```bash
    # Check cluster information
    aws eks describe-cluster --name my-cluster --query cluster.encryptionConfig
    ```

**Encrypted Secrets の使用:**

encryption が有効になると、Secrets を作成および使用する方法は変わりません。すべての encryption と decryption は EKS control plane によって自動的に処理されます。

```yaml
# Create Secret
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
type: Opaque
data:
  username: YWRtaW4=  # base64 encoded "admin"
  password: cGFzc3dvcmQ=  # base64 encoded "password"
```

```bash
# Create Secret
kubectl create secret generic my-secret --from-literal=username=admin --from-literal=password=password

# Verify Secret
kubectl get secret my-secret -o yaml
```

**KMS Key Permissions の設定:**

EKS cluster が KMS key を使用できるように、適切な permissions を設定する必要があります:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowEKSToUseKMSKey",
      "Effect": "Allow",
      "Principal": {
        "Service": "eks.amazonaws.com"
      },
      "Action": [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:ReEncrypt*",
        "kms:GenerateDataKey*",
        "kms:DescribeKey"
      ],
      "Resource": "*"
    }
  ]
}
```

**その他の選択肢の問題点:**

* **Kubernetes Secrets を AWS Secrets Manager に移行する**: これは可能な approach ですが、standard Kubernetes Secrets API との compatibility が低く、additional configuration と integration が必要です。また、すべての applications を AWS Secrets Manager から secrets を取得するように変更する必要があります。
* **すべての Secrets を Base64 で encode する**: Kubernetes Secrets は default ですでに Base64 encoded です。ただし、Base64 は encoding method であり encryption ではないため、security を提供しません。
* **EKS cluster に encryption sidecar container を deploy する**: これは standard approach ではなく、すべての pods に sidecars を追加すると complexity が増します。また、Kubernetes API server との integration も必要になります。

AWS KMS を使用した EKS Secrets encryption は、etcd に保存された Secrets を保護する最も効果的で integrated な方法です。これにより、sensitive data at rest を保護し、AWS の強力な key management capabilities を活用できます。

</details>

5\. Amazon EKS cluster の worker nodes 向け kubelet configuration をカスタマイズする正しい方法は何ですか？ - A) EKS console で cluster configuration を変更する - B) node group 作成時に --kubelet-extra-args parameter を使用する - C) kubectl edit node command を使用する - D) AWS Systems Manager を使用して node configuration を変更する

<details>

<summary>答えを表示</summary>

**答え: B) node group 作成時に --kubelet-extra-args parameter を使用する**

**解説:** Amazon EKS cluster の worker nodes 向け kubelet configuration をカスタマイズする正しい方法は、node group 作成時に `--kubelet-extra-args` parameter を使用することです。この方法により、node が bootstrapped されるときに kubelet へ additional arguments を渡すことができます。

**kubelet Configuration をカスタマイズする方法:**

1.  **Managed Node Groups で Launch Templates を使用**:

    * launch template の user data section で bootstrap script をカスタマイズします。

    ```bash
    #!/bin/bash
    set -o xtrace
    /etc/eks/bootstrap.sh my-cluster \
      --kubelet-extra-args '--max-pods=110 --kube-reserved memory=0.3Gi,cpu=100m --system-reserved memory=0.5Gi,cpu=200m --eviction-hard memory.available<500Mi'
    ```
2. **eksctl を使用して Node Groups を作成**:

```bash
# Create node group with kubelet arguments
eksctl create nodegroup \
  --cluster my-cluster \
  --name my-nodegroup \
  --node-type m5.large \
  --nodes 3 \
  --kubelet-extra-args "--max-pods=110 --kube-reserved memory=0.3Gi,cpu=100m"
```

3.  **eksctl configuration file を使用**:

    ```yaml
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig
    metadata:
      name: my-cluster
      region: us-west-2
    managedNodeGroups:
      - name: my-nodegroup
        instanceType: m5.large
        minSize: 2
        maxSize: 5
        kubeletExtraArgs:
          max-pods: "110"
          kube-reserved: "memory=0.3Gi,cpu=100m"
          system-reserved: "memory=0.5Gi,cpu=200m"
          eviction-hard: "memory.available<500Mi"
    ```
4.  **self-managed node groups で user data script を使用**:

    ```bash
    #!/bin/bash
    set -o xtrace
    /etc/eks/bootstrap.sh my-cluster \
      --kubelet-extra-args '--max-pods=110 --node-labels=node.kubernetes.io/role=worker,environment=prod'
    ```

**一般的にカスタマイズされる kubelet parameters:**

1. **max-pods**:
   * node ごとの pods の最大数を設定します。
   * Example: `--max-pods=110`
2. **node-labels**:
   * node に labels を追加します。
   * Example: `--node-labels=environment=prod,node-type=worker`
3. **kube-reserved**:
   * Kubernetes system components 用に resources を予約します。
   * Example: `--kube-reserved=cpu=100m,memory=0.3Gi,ephemeral-storage=1Gi`
4. **system-reserved**:
   * OS system daemons 用に resources を予約します。
   * Example: `--system-reserved=cpu=100m,memory=0.5Gi,ephemeral-storage=1Gi`
5. **eviction-hard**:
   * hard eviction thresholds を設定します。
   * Example: `--eviction-hard=memory.available<500Mi,nodefs.available<10%`
6. **cgroup-driver**:
   * cgroup driver を設定します。
   * Example: `--cgroup-driver=systemd`

**configuration を確認する方法:**

```bash
# SSH into the node
ssh -i ~/.ssh/id_rsa ec2-user@<node-ip>

# Check kubelet service configuration
sudo systemctl status kubelet
sudo cat /etc/systemd/system/kubelet.service.d/10-kubelet-args.conf

# Check running kubelet process arguments
ps aux | grep kubelet
```

**その他の選択肢の問題点:**

* **EKS console で cluster configuration を変更する**: EKS console では cluster-level configurations を変更できますが、individual nodes の kubelet configuration を直接変更する options は提供されません。
* **kubectl edit node command を使用する**: `kubectl edit node` command は node object metadata を変更できますが、kubelet configuration は変更できません。kubelet configuration は node OS 上の service として実行され、Kubernetes API を通じて直接変更することはできません。
* **AWS Systems Manager を使用して node configuration を変更する**: AWS Systems Manager は nodes 上で commands を実行したり configurations を変更したりするために使用できますが、この方法は nodes がすでに作成された後に適用されます。さらに、kubelet configuration を変更した後は service を restart する必要があり、running pods に影響する可能性があります。したがって、node group 作成時に設定する方が安全で推奨される approach です。

kubelet configuration のカスタマイズにより、workload requirements に合わせて node resource management、pod density、eviction policies などを最適化できます。ただし、変更は cluster stability に影響する可能性があるため、慎重にテストする必要があります。

</details>

6. Amazon EKS clusters で Pod Security Policy を置き換えるために推奨される mechanism は何ですか？
   * A) AWS Security Hub
   * B) Pod Security Admission または Kyverno のような policy engines
   * C) AWS Config Rules
   * D) EKS Security Groups

<details>

<summary>答えを表示</summary>

**答え: B) Pod Security Admission または Kyverno のような policy engines**

**解説:** Amazon EKS clusters で Pod Security Policy (PSP) を置き換えるために推奨される mechanism は、Pod Security Admission または Kyverno のような policy engines です。Kubernetes 1.21 以降、PSP は deprecated となり、Kubernetes 1.25 で完全に削除されました。代替として Pod Security Admission が導入され、Kyverno や OPA Gatekeeper などの policy engines も alternatives として使用できます。

**Pod Security Admission:**

Pod Security Admission は Kubernetes 1.23 から beta feature として導入され、version 1.25 で stable になりました。これは、3 つの security levels (Privileged, Baseline, Restricted) を提供する built-in Kubernetes feature です。

1.  **Configuration method**:

    ```yaml
    # Apply Pod Security standards to namespace
    apiVersion: v1
    kind: Namespace
    metadata:
      name: my-namespace
      labels:
        pod-security.kubernetes.io/enforce: restricted
        pod-security.kubernetes.io/audit: restricted
        pod-security.kubernetes.io/warn: restricted
    ```
2. **Security levels**:
   * **Privileged**: restrictions なし、すべての features が許可されます。
   * **Baseline**: 既知の privilege escalations を防止します。
   * **Restricted**: 強力な security hardening、principle of least privilege を適用します。
3. **Modes**:
   * **enforce**: violation 時に pod creation を拒否します。
   * **audit**: violations を audit logs に記録します。
   * **warn**: violation 時に warning messages を表示します。

**Kyverno:**

Kyverno は、YAML-based policies を使用して cluster resources を validate、mutate、generate する Kubernetes-native policy engine です。

1.  **Installation method**:

    ```bash
    # Install Kyverno using Helm
    helm repo add kyverno https://kyverno.github.io/kyverno/
    helm install kyverno kyverno/kyverno --namespace kyverno --create-namespace
    ```
2.  **Policy example**:

    ```yaml
    # Policy to prevent privileged containers
    apiVersion: kyverno.io/v1
    kind: ClusterPolicy
    metadata:
      name: disallow-privileged-containers
    spec:
      validationFailureAction: enforce
      rules:
      - name: privileged-containers
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
    ```

**OPA Gatekeeper:**

OPA (Open Policy Agent) Gatekeeper は、Kubernetes における policy management のもう 1 つの popular solution です。

1.  **Installation method**:

    ```bash
    # Install Gatekeeper
    kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/master/deploy/gatekeeper.yaml
    ```
2.  **Policy example**:

    ```yaml
    # ConstraintTemplate definition
    apiVersion: templates.gatekeeper.sh/v1beta1
    kind: ConstraintTemplate
    metadata:
      name: k8spsprivilegedcontainer
    spec:
      crd:
        spec:
          names:
            kind: K8sPSPPrivilegedContainer
      targets:
      - target: admission.k8s.gatekeeper.sh
        rego: |
          package k8spsprivilegedcontainer
          violation[{"msg": msg}] {
            c := input.review.object.spec.containers[_]
            c.securityContext.privileged
            msg := sprintf("Privileged container is not allowed: %v", [c.name])
          }

    # Apply Constraint
    apiVersion: constraints.gatekeeper.sh/v1beta1
    kind: K8sPSPPrivilegedContainer
    metadata:
      name: psp-privileged-container
    spec:
      match:
        kinds:
        - apiGroups: [""]
          kinds: ["Pod"]
    ```

**EKS における実装 recommendations:**

1. **Pod Security Admission を有効化**:
   * EKS 1.23 以降で default で利用可能です。
   * namespaces に適切な labels を適用します。
2. **Kyverno または Gatekeeper をインストール**:
   * より complex な policies が必要な場合
   * 複数の resource types に対する policies が必要な場合
3. **段階的な migration**:
   * PSP から new solutions へ段階的に migrate します。
   * audit mode で開始して issues を特定し、その後 enforce mode に切り替えます。

**その他の選択肢の問題点:**

* **AWS Security Hub**: AWS Security Hub は AWS resources の security posture を monitoring するための service ですが、Kubernetes の pod-level security policies を適用するためには使用できません。
* **AWS Config Rules**: AWS Config は AWS resource configurations を評価するための service ですが、Kubernetes の pod-level security policies を適用するためには使用できません。
* **EKS Security Groups**: EKS Security Groups は network traffic の制御に使用され、pod security contexts や privileges を制限するためには使用できません。

Pod Security Policy (PSP) の削除に伴い、EKS clusters は Pod Security Admission、Kyverno、OPA Gatekeeper などの alternative mechanisms を使用して pod security を強化する必要があります。これらの tools は privileged containers、host namespace access、host path mounts などを制限できます。

</details>

7\. Amazon EKS cluster で pod identity を AWS IAM と統合するために IRSA (IAM Roles for Service Accounts) を設定する最初の step は何ですか？ - A) IAM role を作成する - B) service account を作成する - C) OIDC provider を関連付ける - D) pod manifest を変更する

<details>

<summary>答えを表示</summary>

**答え: C) OIDC provider を関連付ける**

**解説:** Amazon EKS cluster で IRSA (IAM Roles for Service Accounts) を設定する最初の step は、OIDC (OpenID Connect) provider を関連付けることです。OIDC provider は、AWS IAM と Kubernetes service accounts の間に trust relationship を確立するために必要です。これにより、Kubernetes service account tokens が AWS IAM における信頼された authentication mechanism になります。

**IRSA configuration steps in order:**

1.  **OIDC provider を関連付ける**:

    * EKS cluster の OIDC issuer URL を確認します。
    * AWS IAM に OIDC provider を作成します。

    ```bash
    # Check OIDC issuer URL
    aws eks describe-cluster --name my-cluster --query "cluster.identity.oidc.issuer" --output text
    # Example output: https://oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE

    # Associate OIDC provider
    eksctl utils associate-iam-oidc-provider --cluster my-cluster --approve

    # Or use AWS CLI
    aws iam create-open-id-connect-provider \
      --url https://oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE \
      --thumbprint-list 9e99a48a9960b14926bb7f3b02e22da2b0ab7280 \
      --client-id-list sts.amazonaws.com
    ```
2.  **IAM role を作成する**:

    * service account が assume する IAM role を作成します。
    * trust policy に OIDC provider と service account conditions を含めます。

    ```json
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE"
          },
          "Action": "sts:AssumeRoleWithWebIdentity",
          "Condition": {
            "StringEquals": {
              "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:sub": "system:serviceaccount:default:my-service-account"
            }
          }
        }
      ]
    }
    ```
3.  **service account を作成する**:

    * IAM role ARN を annotation として持つ service account を作成します。

    ```yaml
    apiVersion: v1
    kind: ServiceAccount
    metadata:
      name: my-service-account
      namespace: default
      annotations:
        eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/my-role
    ```
4.  **pod manifest を変更する**:

    * pod manifest で service account を指定します。

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: my-pod
    spec:
      serviceAccountName: my-service-account
      containers:
      - name: my-container
        image: my-image
    ```

**eksctl を使用した簡素化された IRSA setup:**

eksctl は、上記すべての steps を automate する commands を提供します:

```bash
# Associate OIDC provider
eksctl utils associate-iam-oidc-provider --cluster my-cluster --approve

# Create service account and IAM role
eksctl create iamserviceaccount \
  --name my-service-account \
  --namespace default \
  --cluster my-cluster \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
  --approve
```

**IRSA が動作していることを確認:**

```bash
# Check service account
kubectl get serviceaccount my-service-account -o yaml

# Run test pod
kubectl run -it --rm \
  --image amazon/aws-cli \
  --serviceaccount my-service-account \
  aws-cli -- s3 ls
```

**その他の選択肢の問題点:**

* **IAM role を作成する**: IAM role の作成は IRSA configuration の 2 番目の step です。IAM role の trust policy が OIDC provider を参照できるように、OIDC provider を先に関連付ける必要があります。
* **service account を作成する**: service account の作成は IRSA configuration の 3 番目の step です。IAM role ARN を service account の annotation として追加できるように、IAM role を先に作成する必要があります。
* **pod manifest を変更する**: pod manifest の変更は IRSA configuration の最後の step です。pod がその service account を参照できるように、service account を先に作成する必要があります。

IRSA は、Kubernetes workloads に AWS services への fine-grained permissions を付与する安全で効率的な方法です。これにより、node-level IAM roles を共有する代わりに、各 application に必要最小限の permissions のみを付与できます。IRSA configuration の最初の step は OIDC provider を関連付けることであり、これは AWS IAM と Kubernetes service accounts の間の trust relationship を確立するために不可欠です。

</details>

8. Amazon EKS cluster で control plane logs を有効化する正しい方法は何ですか？
   * A) EKS control plane に CloudWatch agent をインストールする
   * B) AWS CLI または console 経由で cluster logging configuration を有効化する
   * C) Fluentd を使用して log forwarding を設定する
   * D) EKS control plane nodes に SSH して log configuration を変更する

<details>

<summary>答えを表示</summary>

**答え: B) AWS CLI または console 経由で cluster logging configuration を有効化する**

**解説:** Amazon EKS cluster で control plane logs を有効化する正しい方法は、AWS CLI または AWS Management Console 経由で cluster logging configuration を有効化することです。EKS は managed service であり、control plane は AWS によって管理されるため、直接 access したり agents をインストールしたりすることはできません。代わりに、AWS が提供する APIs を通じて logging を設定する必要があります。

**AWS CLI を使用して control plane logs を有効化:**

```bash
# Enable all log types
aws eks update-cluster-config \
  --name my-cluster \
  --region us-west-2 \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# Enable only specific log types
aws eks update-cluster-config \
  --name my-cluster \
  --region us-west-2 \
  --logging '{"clusterLogging":[{"types":["api","audit"],"enabled":true},{"types":["authenticator","controllerManager","scheduler"],"enabled":false}]}'
```

**eksctl を使用して control plane logs を有効化:**

```bash
# Enable all log types
eksctl utils update-cluster-logging \
  --enable-types api,audit,authenticator,controllerManager,scheduler \
  --cluster my-cluster \
  --region us-west-2

# Enable only specific log types
eksctl utils update-cluster-logging \
  --enable-types api,audit \
  --disable-types authenticator,controllerManager,scheduler \
  --cluster my-cluster \
  --region us-west-2
```

**AWS Management Console を使用して control plane logs を有効化:**

1. AWS Management Console にログインします。
2. EKS service に移動します。
3. cluster list から対象 cluster を選択します。
4. "Logging" tab を選択します。
5. "Manage" をクリックします。
6. 有効化する log types を選択します:
   * API server (api)
   * Audit (audit)
   * Authenticator (authenticator)
   * Controller manager (controllerManager)
   * Scheduler (scheduler)
7. "Save changes" をクリックします。

**利用可能な log types:**

1. **API server (api)**:
   * Kubernetes API server からの logs
   * API request と response information を含みます。
2. **Audit (audit)**:
   * cluster 内のすべての activities に対する audit logs
   * security と compliance purposes に重要です。
3. **Authenticator (authenticator)**:
   * AWS IAM Authenticator からの logs
   * authentication issues の troubleshooting に有用です。
4. **Controller manager (controllerManager)**:
   * Kubernetes controller manager からの logs
   * resource state management information を含みます。
5. **Scheduler (scheduler)**:
   * Kubernetes scheduler からの logs
   * pod scheduling decisions に関する information を含みます。

**logs を表示する方法:**

有効化された logs は CloudWatch Logs に保存され、次の log group で表示できます:

```
/aws/eks/my-cluster/cluster
```

各 log type は separate log stream として保存されます:

```
kube-apiserver-xxxxx
audit-xxxxx
authenticator-xxxxx
kube-controller-manager-xxxxx
kube-scheduler-xxxxx
```

**Cost considerations:**

* Control plane logs には CloudWatch Logs pricing が適用されます。
* すべての log types を有効にすると、significant amount of logs が生成される可能性があります。
* cost optimization のため、必要な log types のみを選択的に有効化することを推奨します。
* 適切な log retention periods を設定することで costs を管理できます。

**その他の選択肢の問題点:**

* **EKS control plane に CloudWatch agent をインストールする**: EKS control plane は AWS によって管理されるため、直接 access したり agents をインストールしたりすることはできません。
* **Fluentd を使用して log forwarding を設定する**: Fluentd は worker nodes から logs を収集するために使用できますが、EKS control plane logs には access できません。
* **EKS control plane nodes に SSH して log configuration を変更する**: EKS control plane nodes は AWS によって管理されるため、直接 SSH することはできません。

EKS control plane logs は、cluster troubleshooting、security audits、compliance に重要な information を提供します。AWS CLI または AWS Management Console を通じて必要な log types を選択的に有効化することで、効果的に monitor できます。

</details>

9. Amazon EKS cluster で node group の instance type を変更する正しい方法は何ですか？
   * A) AWS Management Console で node group instance type を直接変更する
   * B) 新しい instance type の新しい node group を作成し、workloads を migrate する
   * C) kubectl edit command で node specifications を変更する
   * D) AWS CLI update-nodegroup-config command を使用する

<details>

<summary>答えを表示</summary>

**答え: B) 新しい instance type の新しい node group を作成し、workloads を migrate する**

**解説:** Amazon EKS cluster で node group の instance type を変更する正しい方法は、新しい instance type の新しい node group を作成してから workloads を migrate することです。EKS managed node groups では、作成後に instance type を直接変更することはできないため、新しい node group を作成し、workloads を migrate し、その後 existing node group を削除する必要があります。

**node group instance type を変更する手順:**

1.  **新しい node group を作成**:

    ```bash
    # Create new node group using eksctl
    eksctl create nodegroup \
      --cluster my-cluster \
      --name my-new-nodegroup \
      --node-type m5.large \
      --nodes 3 \
      --nodes-min 1 \
     --nodes-max 5 \
     --node-labels "migration-target=true"
    ```

## AWS CLI を使用して新しい node group を作成

aws eks create-nodegroup\
\--cluster-name my-cluster\
\--nodegroup-name my-new-nodegroup\
\--subnets subnet-12345 subnet-67890\
\--instance-types m5.large\
\--scaling-config minSize=1,maxSize=5,desiredSize=3\
\--node-role arn:aws:iam::123456789012:role/EksNodeRole\
\--labels migration-target=true

````

2. **新しい node group status を確認**:
 ```bash
 # Check node group status
 aws eks describe-nodegroup \
   --cluster-name my-cluster \
   --nodegroup-name my-new-nodegroup \
   --query "nodegroup.status"

 # Check nodes
 kubectl get nodes --label-columns migration-target
````

3.  **workloads を migrate**:

    **Method 1: Cordoning と Draining を使用**

    ```bash
    # Identify nodes in the existing node group
    OLD_NODES=$(kubectl get nodes -l alpha.eksctl.io/nodegroup-name=my-old-nodegroup -o jsonpath='{.items[*].metadata.name}')

    # Cordon nodes (prevent new pod scheduling)
    for node in $OLD_NODES; do
      kubectl cordon $node
    done

    # Drain nodes (remove existing pods)
    for node in $OLD_NODES; do
      kubectl drain $node --ignore-daemonsets --delete-emptydir-data
    done
    ```

    **Method 2: Pod Selector を使用**

    ```yaml
    # Deploy to new nodes using node selector
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: my-app
    spec:
      template:
        spec:
          nodeSelector:
            migration-target: "true"
    ```

    **Method 3: Blue/Green Deployment**

    * new node group に new deployment version を deploy します。
    * traffic を new version に段階的に shift します。
    * existing deployment version を削除します。
4.  **existing node group を削除**:

    ```bash
    # Delete node group using eksctl
    eksctl delete nodegroup \
      --cluster my-cluster \
      --name my-old-nodegroup

    # Delete node group using AWS CLI
    aws eks delete-nodegroup \
      --cluster-name my-cluster \
      --nodegroup-name my-old-nodegroup
    ```

**migration 中の considerations:**

1.  **workload disruption を最小化**:

    * PodDisruptionBudget を設定します。

    ```yaml
    apiVersion: policy/v1
    kind: PodDisruptionBudget
    metadata:
      name: my-app-pdb
    spec:
      minAvailable: 2  # or maxUnavailable: 1
      selector:
        matchLabels:
          app: my-app
    ```

    * rolling update strategy を使用します。
2. **Resource requirements**:
   * new instance type が workload requirements を満たすことを確認します。
   * CPU、memory、storage、networking requirements を考慮します。
3. **Stateful workloads**:
   * persistent volumes を使用している workloads の data persistence を確認します。
   * 必要に応じて backups を実行します。
4. **Cost impact**:
   * new instance type の cost impact を評価します。
   * migration 中は両方の node groups が同時に running するため、costs が一時的に増加します。

**その他の選択肢の問題点:**

* **AWS Management Console で node group instance type を直接変更する**: EKS managed node groups では、作成後に instance type を直接変更することはできません。
* **kubectl edit command で node specifications を変更する**: kubectl は Kubernetes API objects を変更するために使用されますが、node の underlying instance type は AWS infrastructure level で決定され、kubectl では変更できません。
* **AWS CLI update-nodegroup-config command を使用する**: `update-nodegroup-config` command は node group の scaling configuration、labels、taints などを変更できますが、instance type は変更できません。

node group の instance type を変更することは、cluster performance の最適化、costs の削減、新しい workload requirements への対応のために必要になる場合があります。新しい node group を作成して workloads を migrate することは、disruption を最小限に抑えながら安全に instance types を変更するための推奨 approach です。

</details>

10\. Amazon EKS cluster の node group に Kubernetes taints を適用する正しい方法は何ですか？ - A) kubectl taint command を使用する - B) node group 作成時に --taints parameter を使用する - C) AWS Management Console で node group taints を設定する - D) node bootstrap script で kubelet configuration を変更する

<details>

<summary>答えを表示</summary>

**答え: B) node group 作成時に --taints parameter を使用する**

**解説:** Amazon EKS cluster の node group に Kubernetes taints を適用する正しい方法は、node group 作成時に `--taints` parameter を使用することです。EKS managed node groups は、作成時または updates 中に taints を設定する機能を提供します。この方法により、node group 内のすべての nodes に taints が一貫して適用され、nodes が replaced されたときにも維持されます。

**eksctl を使用した taints の設定:**

```bash
# Create node group with taints
eksctl create nodegroup \
  --cluster my-cluster \
  --name tainted-ng \
  --node-type m5.large \
  --nodes 3 \
  --taints "dedicated=gpu:NoSchedule,special=true:PreferNoSchedule"

# Configure taints using configuration file
cat > nodegroup.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: tainted-ng
    instanceType: m5.large
    minSize: 2
    maxSize: 5
    taints:
      - key: dedicated
        value: gpu
        effect: NoSchedule
      - key: special
        value: "true"
        effect: PreferNoSchedule
EOF

eksctl create nodegroup -f nodegroup.yaml
```

**AWS CLI を使用した taints の設定:**

```bash
# Create node group with taints
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name tainted-ng \
  --subnets subnet-12345 subnet-67890 \
  --instance-types m5.large \
  --scaling-config minSize=2,maxSize=5,desiredSize=3 \
  --node-role arn:aws:iam::123456789012:role/EksNodeRole \
  --taints "key=dedicated,value=gpu,effect=NoSchedule" "key=special,value=true,effect=PreferNoSchedule"

# Update taints on existing node group
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name tainted-ng \
  --taints "addOrUpdateTaints=[{key=dedicated,value=gpu,effect=NoSchedule}],removeTaints=[{key=special}]"
```

**AWS Management Console を使用した taints の設定:**

1. AWS Management Console にログインします。
2. EKS service に移動します。
3. cluster を選択します。
4. "Compute" tab を選択します。
5. "Add node group" をクリックします。
6. node group details を入力します。
7. "Kubernetes taints" section で "Add taint" をクリックします。
8. key、value、effect を入力します。
9. "Create" をクリックします。

**Taint effect types:**

1. **NoSchedule**:
   * taint に一致する toleration を持たない Pods は、その node に scheduled されません。
   * Existing pods には影響しません。
2. **PreferNoSchedule**:
   * taint に一致する toleration を持たない Pods は、可能な限りその node に scheduled されませんが、これは保証されません。
   * 他の nodes に schedule できない場合、その node に scheduled される可能性があります。
3. **NoExecute**:
   * taint に一致する toleration を持たない Pods は、その node に scheduled されません。
   * すでに running 中で、その taint に一致する toleration を持たない Pods は evicted されます。

**taints の一般的な use cases:**

1.  **特殊 hardware nodes の isolation**:

    ```bash
    # Apply taint to GPU nodes
    eksctl create nodegroup \
      --cluster my-cluster \
      --name gpu-nodes \
      --node-type p3.2xlarge \
      --taints "dedicated=gpu:NoSchedule"

    # Add toleration to GPU workload
    apiVersion: v1
    kind: Pod
    metadata:
      name: gpu-pod
    spec:
      tolerations:
      - key: "dedicated"
        operator: "Equal"
        value: "gpu"
        effect: "NoSchedule"
      containers:
      - name: gpu-container
        image: gpu-image
    ```
2.  **node maintenance の準備**:

    ```bash
    # Apply taint to node
    kubectl taint nodes node1 maintenance=planned:NoSchedule

    # Remove taint after maintenance
    kubectl taint nodes node1 maintenance=planned:NoSchedule-
    ```
3.  **特定 workloads 向け dedicated nodes の設定**:

    ```bash
    # Node group dedicated to production workloads
    eksctl create nodegroup \
      --cluster my-cluster \
      --name prod-nodes \
      --node-type m5.large \
      --taints "environment=production:NoSchedule"

    # Add toleration to production deployment
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: prod-app
    spec:
      template:
        spec:
          tolerations:
          - key: "environment"
            operator: "Equal"
            value: "production"
            effect: "NoSchedule"
    ```

**その他の選択肢の問題点:**

* **kubectl taint command を使用する**: `kubectl taint` command を使用して individual nodes に taints を適用できますが、これは temporary change であり、nodes が replaced されたときに taints は維持されません。また、node group 内のすべての nodes に一貫して適用することも困難です。
* **AWS Management Console で node group taints を設定する**: AWS Management Console で node group 作成時に taints を設定することもできますが、これは「node group 作成時に --taints parameter を使用する」と同じ approach です。したがって、この option も正解になり得ますが、technically には node group 作成時に taints を設定することと同じです。
* **node bootstrap script で kubelet configuration を変更する**: bootstrap script の `--register-with-taints` flag を使用して kubelet configuration を変更できますが、これは complex で error-prone な方法です。また、EKS managed node groups では推奨されません。

Taints は、特定の workloads のみを特定の nodes に deploy したり、特定の workloads を特定の nodes から除外したりするために役立つ Kubernetes feature です。EKS managed node groups では、node group の作成時または更新時に taints を設定することが最も効果的で管理しやすい方法です。

</details>

## ハンズオン演習

### Exercise 1: IRSA (IAM Roles for Service Accounts) の設定

**Scenario:** S3 bucket に access する必要がある application が EKS cluster で running しています。security best practices に従い、node IAM role を共有する代わりに、IRSA を使用して specific pods に必要な permissions のみを付与したいと考えています。

**Requirements:**

1. OIDC provider を関連付ける
2. S3 access permissions を持つ IAM role を作成する
3. service account を作成し、IAM role を関連付ける
4. service account を使用する pod を deploy する
5. S3 access を test する

**解決策:**

<details>

<summary>解決策を表示</summary>

**1. OIDC Provider を関連付ける**

```bash
# Get the cluster's OIDC issuer URL
OIDC_PROVIDER=$(aws eks describe-cluster --name my-cluster --query "cluster.identity.oidc.issuer" --output text | sed -e "s/^https:\/\///")

# Check if OIDC provider already exists
aws iam list-open-id-connect-providers | grep $OIDC_PROVIDER

# Create OIDC provider if it doesn't exist
eksctl utils associate-iam-oidc-provider --cluster my-cluster --approve
```

**2. S3 Access Permissions を持つ IAM Role を作成**

```bash
# Create trust policy
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):oidc-provider/${OIDC_PROVIDER}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${OIDC_PROVIDER}:sub": "system:serviceaccount:default:s3-access-sa"
        }
      }
    }
  ]
}
EOF

# Create IAM role
aws iam create-role --role-name s3-access-role --assume-role-policy-document file://trust-policy.json

# Attach S3 access policy
aws iam attach-role-policy --role-name s3-access-role --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
```

**3. Service Account を作成し IAM Role を関連付ける**

```bash
# Get IAM role ARN
ROLE_ARN=$(aws iam get-role --role-name s3-access-role --query Role.Arn --output text)

# Create service account
cat > service-account.yaml << EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-access-sa
  namespace: default
  annotations:
    eks.amazonaws.com/role-arn: ${ROLE_ARN}
EOF

kubectl apply -f service-account.yaml
```

**4. Service Account を使用して Pod を Deploy**

```bash
# Deploy test pod
cat > pod.yaml << EOF
apiVersion: v1
kind: Pod
metadata:
  name: s3-access-pod
  namespace: default
spec:
  serviceAccountName: s3-access-sa
  containers:
  - name: aws-cli
    image: amazon/aws-cli:latest
    command:
    - sleep
    - "3600"
  restartPolicy: Never
EOF

kubectl apply -f pod.yaml
```

**5. S3 Access を Test**

```bash
# Verify the pod is running
kubectl get pod s3-access-pod

# Test listing S3 buckets
kubectl exec -it s3-access-pod -- aws s3 ls

# Test listing objects in a specific S3 bucket
kubectl exec -it s3-access-pod -- aws s3 ls s3://my-bucket

# Verify AWS credentials
kubectl exec -it s3-access-pod -- aws sts get-caller-identity
```

**6. Cleanup**

```bash
# Delete pod
kubectl delete pod s3-access-pod

# Delete service account
kubectl delete serviceaccount s3-access-sa

# Clean up IAM role
aws iam detach-role-policy --role-name s3-access-role --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
aws iam delete-role --role-name s3-access-role
```

**追加説明:**

1. **OIDC Provider Association**:
   * OIDC provider は AWS IAM と Kubernetes service accounts の間に trust relationship を確立します。
   * これは cluster ごとに 1 回だけ setup すれば十分です。
2. **IAM Role Trust Policy**:
   * trust policy は、specific namespaces 内の specific service accounts のみが role を assume できるように制限します。
   * condition statements を使用して security を強化します。
3. **Service Account Annotation**:
   * `eks.amazonaws.com/role-arn` annotation は、service account が assume する IAM role を指定します。
   * この annotation は EKS Pod Identity Webhook によって処理されます。
4. **Environment Variables**:
   * EKS Pod Identity Webhook は、次の environment variables を pod に自動的に inject します:
     * `AWS_ROLE_ARN`
     * `AWS_WEB_IDENTITY_TOKEN_FILE`
     * `AWS_REGION`
   * AWS SDKs はこれらの environment variables を使用して credentials を取得します。
5. **Principle of Least Privilege**:
   * application が必要とする minimum permissions のみを付与します。
   * この例では、S3 read-only access permission のみを付与しました。

この演習を通じて、EKS cluster で running している specific pods のみに AWS services への fine-grained permissions を付与するための IRSA の設定方法を学びました。この approach は node IAM role を共有するよりも安全で、principle of least privilege に従っています。

</details>

\### Exercise 2: EKS Cluster Security の強化

**Scenario:** あなたは会社の security engineer で、新しく作成された EKS cluster の security を強化する必要があります。cluster はすでに作成され、default settings で設定されています。security best practices に従って cluster を harden したいと考えています。

**Requirements:**

1. cluster endpoint access を制限する
2. Secrets encryption を有効化する
3. network policies を実装する
4. Pod Security Standards を適用する
5. control plane logging を有効化する

**解決策:**

<details>

<summary>解決策を表示</summary>

**1. Cluster Endpoint Access を制限**

```bash
# Check current cluster endpoint configuration
aws eks describe-cluster --name my-cluster --query "cluster.resourcesVpcConfig.endpointPublicAccess"
aws eks describe-cluster --name my-cluster --query "cluster.resourcesVpcConfig.endpointPrivateAccess"

# Restrict public access (allow only specific CIDR blocks)
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=["203.0.113.0/24","198.51.100.0/24"]

# Or disable public access (private cluster)
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true
```

**2. Secrets Encryption を有効化**

```bash
# Create KMS key
aws kms create-key --description "EKS Secrets Encryption Key"
KEY_ID=$(aws kms create-key --query KeyMetadata.KeyId --output text)

# Add alias to KMS key
aws kms create-alias \
  --alias-name alias/eks-secrets \
  --target-key-id $KEY_ID

# Cannot enable encryption on current cluster, so a new cluster must be created
# Get existing cluster configuration
aws eks describe-cluster --name my-cluster > cluster-config.json

# Create new cluster (more parameters are needed in practice)
aws eks create-cluster \
  --name my-cluster-encrypted \
  --role-arn $(aws eks describe-cluster --name my-cluster --query cluster.roleArn --output text) \
  --resources-vpc-config subnetIds=$(aws eks describe-cluster --name my-cluster --query cluster.resourcesVpcConfig.subnetIds --output text | tr -d '[]" ' | tr ',' ' '),securityGroupIds=$(aws eks describe-cluster --name my-cluster --query cluster.resourcesVpcConfig.securityGroupIds --output text | tr -d '[]" ') \
  --encryption-config '[{"resources":["secrets"],"provider":{"keyArn":"arn:aws:kms:'$(aws configure get region)':'$(aws sts get-caller-identity --query Account --output text)':key/'$KEY_ID'"}}]'
```

**3. Network Policies を実装**

```bash
# Install Calico
kubectl create namespace tigera-operator
helm repo add projectcalico https://docs.projectcalico.org/charts
helm install calico projectcalico/tigera-operator --namespace tigera-operator

# Create default deny network policy
cat > default-deny.yaml << EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
EOF

kubectl apply -f default-deny.yaml

# Policy to allow communication between specific applications
cat > allow-app-communication.yaml << EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: backend
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
EOF

kubectl apply -f allow-app-communication.yaml
```

**4. Pod Security Standards を適用**

```bash
# Apply Pod Security Standards to namespace
cat > pod-security.yaml << EOF
apiVersion: v1
kind: Namespace
metadata:
  name: restricted-ns
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
EOF

kubectl apply -f pod-security.yaml

# Add labels to existing namespace
kubectl label namespace default \
  pod-security.kubernetes.io/enforce=baseline \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted

# Install Kyverno (for additional policy enforcement)
kubectl create namespace kyverno
helm repo add kyverno https://kyverno.github.io/kyverno/
helm install kyverno kyverno/kyverno --namespace kyverno

# Policy to prevent privileged containers
cat > restrict-privileged.yaml << EOF
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-privileged-containers
spec:
  validationFailureAction: enforce
  rules:
  - name: privileged-containers
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
EOF

kubectl apply -f restrict-privileged.yaml
```

**5. Control Plane Logging を有効化**

```bash
# Enable all control plane log types
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# Verify logging status
aws eks describe-cluster --name my-cluster --query "cluster.logging"

# Check logs in CloudWatch Logs
aws logs describe-log-groups --log-group-name-prefix /aws/eks/my-cluster
```

**6. Additional Security Hardening Measures**

```bash
# Restrict IAM policy for AWS Load Balancer Controller
cat > alb-controller-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeListeners"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name EksAlbControllerRestrictedPolicy \
  --policy-document file://alb-controller-policy.json

# Configure node group update for periodic node replacement
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --update-config '{"maxUnavailable": 1}'

# Start node group update
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup
```

**Security Hardening の解説:**

1. **Cluster Endpoint Access を制限**:
   * public endpoint access を specific IP ranges に制限するか、完全に無効化します。
   * private endpoint を有効化し、VPC 内から cluster access できるようにします。
   * これにより、cluster API server への unauthorized access を防ぎます。
2. **Secrets Encryption を有効化**:
   * AWS KMS keys を使用して、etcd に保存される Kubernetes Secrets を encrypt します。
   * sensitive data at rest を保護します。
   * Note: Encryption は existing clusters では有効化できないため、新しい cluster を作成する必要があります。
3. **Network Policies を実装**:
   * Kubernetes network policies をサポートするために Calico をインストールします。
   * explicitly allowed されていないすべての traffic を block する default deny policies を適用します。
   * 必要な communication のみを許可する fine-grained policies を実装します。
4. **Pod Security Standards を適用**:
   * Kubernetes 1.23 以降で利用可能な Pod Security Standards を適用します。
   * namespace level で security constraints を設定します。
   * Kyverno のような policy engines を使用して additional security policies を適用します。
5. **Control Plane Logging を有効化**:
   * すべての control plane log types を CloudWatch Logs に送信します。
   * audit logs を通じて cluster activity を monitor します。
   * security events と troubleshooting のために logs を保持します。

このハンズオン演習を通じて、EKS cluster の security を強化するさまざまな方法を学びました。これらの security measures は、cluster の security posture を改善し、unauthorized access や malicious activities から保護するのに役立ちます。

</details>

## Advanced Topics

以下は、Amazon EKS cluster 作成における advanced topics に関する問題です。この section では、EKS cluster 作成における advanced concepts と best practices についての理解を確認します。

1. 次のうち、Amazon EKS cluster で IPv6 support を設定するための requirement ではないものはどれですか？
   * A) IPv6 CIDR block が割り当てられた VPC
   * B) IPv6 をサポートする CNI plugin version
   * C) Dual-stack subnets
   * D) IPv6-only instance types

<details>

<summary>答えを表示</summary>

**答え: D) IPv6-only instance types**

**解説:** "IPv6-only instance types" は、Amazon EKS cluster で IPv6 support を設定するための requirement ではありません。ほとんどの EC2 instance types は IPv6 をサポートしているため、IPv6 support に特別な instance types は必要ありません。実際の requirements は、IPv6 CIDR block が割り当てられた VPC、IPv6 をサポートする CNI plugin version、dual-stack subnets です。

**EKS で IPv6 Support に必要な実際の Requirements:**

1.  **IPv6 CIDR block が割り当てられた VPC**:

    * VPC に IPv6 CIDR block を割り当てる必要があります。
    * これは AWS Management Console または AWS CLI を通じて設定できます。

    ```bash
    # Assign IPv6 CIDR block to existing VPC
    aws ec2 associate-vpc-cidr-block \
      --vpc-id vpc-12345 \
      --amazon-provided-ipv6-cidr-block
    ```
2.  **IPv6 をサポートする CNI plugin version**:

    * Amazon VPC CNI plugin version 1.10.0 以降が必要です。
    * IPv6 support の configuration が必要です。

    ```bash
    # Check CNI version
    kubectl describe daemonset aws-node --namespace kube-system | grep Image

    # Update CNI
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.10.0/config/master/aws-k8s-cni.yaml

    # Enable IPv6
    kubectl set env daemonset aws-node -n kube-system ENABLE_IPV6=true
    ```
3.  **Dual-stack subnets**:

    * Subnets には IPv4 と IPv6 の両方の CIDR blocks が割り当てられている必要があります。
    * route table で IPv6 routing を設定する必要があります。

    ```bash
    # Assign IPv6 CIDR block to subnet
    aws ec2 associate-subnet-cidr-block \
      --subnet-id subnet-12345 \
      --ipv6-cidr-block 2600:1f16:d93:e900::/64

    # Create IPv6 internet gateway
    aws ec2 create-egress-only-internet-gateway --vpc-id vpc-12345
    ```

**EKS IPv6 Cluster の作成:**

```bash
# Create IPv6 cluster using eksctl
cat > ipv6-cluster.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ipv6-cluster
  region: us-west-2
  version: '1.23'
vpc:
  id: vpc-12345
  subnets:
    private:
      us-west-2a:
        id: subnet-12345
      us-west-2b:
        id: subnet-67890
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
kubernetesNetworkConfig:
  ipFamily: IPv6
managedNodeGroups:
  - name: ng-1
    instanceType: m5.large
    desiredCapacity: 2
EOF

eksctl create cluster -f ipv6-cluster.yaml
```

**IPv6 Cluster Configuration の確認:**

```bash
# Check cluster information
aws eks describe-cluster --name ipv6-cluster --query "cluster.kubernetesNetworkConfig"

# Verify Pod IP assignment
kubectl get pods -o wide

# Verify Service IP assignment
kubectl get services -o wide
```

**IPv6 Clusters の特徴:**

1. **Pod IP Assignment**:
   * Pods には IPv6 addresses のみが割り当てられます。
   * cluster 内の communication は IPv6 over で行われます。
2. **Service IP Assignment**:
   * ClusterIP services は IPv6 addresses を使用します。
   * default service CIDR は fd00::/108 です。
3. **DNS Configuration**:
   * CoreDNS は IPv6 addresses で設定されます。
   * Service name resolution は AAAA records を通じて利用できます。
4. **External Communication**:
   * internet communication には Egress-Only Internet Gateway が必要です。
   * inbound communication には IPv6-enabled load balancer が必要です。

**IPv6 を使用する利点:**

1. **IP Address Exhaustion の解決**:
   * IPv4 address space の limitations を克服します。
   * large-scale clusters における IP address shortage problems を解決します。
2. **Simplified Networking**:
   * NAT が不要になり、network configuration が簡素化されます。
   * direct routing により network performance が向上する可能性があります。
3. **Future Compatibility**:
   * IPv6-only environments への transition に備えます。
   * new networking features と optimizations の活用を可能にします。

"IPv6-only instance types" は存在しない concept であり、ほとんどの EC2 instance types は IPv6 をサポートしています。EKS で IPv6 を設定するために special instance types を選択する必要はありません。

</details>

2\. Amazon EKS cluster で custom networking を設定する主な利点は何ですか？ - A) Pod IP address range を VPC CIDR から分離して IP address conflicts を防ぐ - B) cluster creation time を短縮する - C) control plane performance を向上させる - D) node-to-node communication を encrypt する

<details>

<summary>答えを表示</summary>

**答え: A) Pod IP address range を VPC CIDR から分離して IP address conflicts を防ぐ**

**解説:** Amazon EKS cluster で custom networking を設定する主な利点は、Pod IP address range を VPC CIDR から分離して IP address conflicts を防ぐことです。この機能により、existing network infrastructure との integration が容易になり、large-scale clusters でより効率的な IP address management が可能になります。

**Custom Networking の仕組み:**

default では、Amazon VPC CNI plugin は node の primary network interface から secondary IP addresses を割り当て、Pods に IP addresses を提供します。この approach では、Pod IP addresses は VPC CIDR range 内から割り当てられます。これに対して custom networking では、Pod IP addresses を VPC CIDR とは別の CIDR block から割り当てることができます。

**Custom Networking を設定する手順:**

1.  **Custom Networking を有効化**:

    ```bash
    # Modify CNI plugin configuration
    kubectl set env daemonset aws-node -n kube-system AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true
    ```
2.  **ENIConfig Resources を作成**:

    ```yaml
    # Create ENIConfig for each availability zone
    apiVersion: crd.k8s.amazonaws.com/v1alpha1
    kind: ENIConfig
    metadata:
      name: us-west-2a
    spec:
      subnet: subnet-12345
      securityGroups:
      - sg-12345
    ---
    apiVersion: crd.k8s.amazonaws.com/v1alpha1
    kind: ENIConfig
    metadata:
      name: us-west-2b
    spec:
      subnet: subnet-67890
      securityGroups:
      - sg-12345
    ```
3.  **Availability Zone-based ENIConfig Usage を有効化**:

    ```bash
    kubectl set env daemonset aws-node -n kube-system ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone
    ```
4.  **Node Labels を確認**:

    ```bash
    kubectl get nodes --show-labels | grep topology.kubernetes.io/zone
    ```

**Custom Networking の利点:**

1. **IP Address Conflicts の防止**:
   * Pod IP address range を VPC CIDR から分離して IP address conflicts を防ぎます。
   * existing network infrastructure との integration を容易にします。
   * on-premises networks と VPCs 間の peering または VPN connections に有用です。
2. **IP Address Management の柔軟性**:
   * Pod IP address ranges を別個に planning および management できます。
   * large-scale clusters でより効率的な IP address management を可能にします。
3. **Network Segmentation**:
   * Pods を specific subnets に配置することで network segmentation を可能にします。
   * security groups を通じた network access control が可能です。
4. **Multi-CIDR Support**:
   * 複数の CIDR blocks を使用して IP address space を拡張できます。
   * existing VPC CIDR が limited な場合でも large-scale clusters を構築できます。

**Custom Networking の Use Cases:**

1. **Hybrid Network Environments**:
   * on-premises networks と AWS VPC の間に connectivity がある場合
   * IP address space overlap を防ぐ必要がある場合
2. **Large-Scale Clusters**:
   * 大量の Pods を running する場合
   * VPC CIDR range が limited な場合
3. **Multi-tenant Environments**:
   * 各 tenant に separate subnets が必要な場合
   * network isolation が必要な場合
4. **Regulatory Requirements**:
   * regulations により specific workloads を specific subnets に配置する必要がある場合

**その他の選択肢の問題点:**

* **cluster creation time を短縮する**: Custom networking は cluster creation time に影響せず、additional configuration のため setup time が実際には増加する可能性があります。
* **control plane performance を向上させる**: Custom networking は data plane (worker nodes と Pods) networking のみに影響し、control plane performance には直接影響しません。
* **node-to-node communication を encrypt する**: Custom networking は IP addresses の割り当て方法を変更するだけであり、node-to-node communication encryption とは関係ありません。Node-to-node communication encryption は separate security mechanisms (例: Calico、Cilium encryption features) を通じて実装する必要があります。

Custom networking は EKS cluster networking をより柔軟に設定できる強力な feature ですが、configuration が complex で additional management overhead が発生する可能性があるため、実際に必要な場合にのみ使用すべきです。

</details>

3\. 次のうち、Amazon EKS cluster で Windows worker nodes をサポートするための requirement ではないものはどれですか？ - A) 少なくとも 2 つの Amazon Linux-based managed node groups が必要 - B) VPC-CNI、kube-proxy、CoreDNS add-ons installed - C) Windows Server 2019 以降の AMI - D) Cluster version 1.14 以上

<details>

<summary>答えを表示</summary>

**答え: A) 少なくとも 2 つの Amazon Linux-based managed node groups が必要**

**解説:** Amazon EKS cluster で Windows worker nodes をサポートするには、少なくとも 1 つ (2 つ以上ではない) の Amazon Linux-based managed node group が必要です。これは、CoreDNS のような essential system Pods が Linux nodes 上で実行される必要があるためです。ただし、少なくとも 2 つの Linux node groups が必要というのは正しくありません。

**EKS で Windows Worker Node Support に必要な実際の Requirements:**

1.  **Linux Node Group Required**:

    * cluster には少なくとも 1 つの Linux node が必要です。
    * CoreDNS、VPC CNI plugin、kube-proxy などの System Pods は Linux nodes 上でのみ実行されます。

    ```bash
    # Create Linux node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name linux-ng \
      --node-type m5.large \
      --nodes 2
    ```
2.  **VPC-CNI、kube-proxy、CoreDNS Add-ons Installed**:

    * これらの add-ons は EKS cluster の essential components です。
    * Windows node support には specific versions 以上が必要になる場合があります。

    ```bash
    # Check add-on versions
    aws eks describe-addon-versions \
      --addon-name vpc-cni \
      --kubernetes-version 1.23

    # Update add-on
    aws eks update-addon \
      --cluster-name my-cluster \
      --addon-name vpc-cni \
      --addon-version v1.10.4-eksbuild.1
    ```
3.  **Windows Server 2019 or Later AMI**:

    * Windows worker nodes は Windows Server 2019 以降の AMI を使用する必要があります。
    * EKS-optimized Windows AMI の使用が推奨されます。

    ```bash
    # Create Windows node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name windows-ng \
      --node-type m5.large \
      --nodes 2 \
      --node-ami-family WindowsServer2019FullContainer
    ```
4.  **Cluster Version 1.14 or Higher**:

    * Windows node support は Kubernetes 1.14 から正式にサポートされました。
    * latest features のため、より高い version の使用が推奨されます。

    ```bash
    # Check cluster version
    aws eks describe-cluster --name my-cluster --query "cluster.version"
    ```

**Windows Support を有効化する手順:**

1.  **Windows Support を有効化**:

    ```bash
    # Enable Windows support
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/vpc-resource-controller.yaml

    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/vpc-admission-webhook.yaml
    ```
2.  **Windows Node Group を作成**:

    ```bash
    # Create Windows node group using eksctl
    eksctl create nodegroup \
      --cluster my-cluster \
      --name windows-ng \
      --node-type m5.large \
      --nodes 2 \
      --node-ami-family WindowsServer2019FullContainer
    ```
3.  **Windows Nodes を確認**:

    ```bash
    # Verify nodes
    kubectl get nodes -o wide

    # Verify Windows node labels
    kubectl get nodes -l kubernetes.io/os=windows
    ```

**Windows Container Deployment Example:**

```yaml
# Windows Pod deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: windows-server-iis
spec:
  selector:
    matchLabels:
      app: windows-server-iis
      tier: backend
      track: stable
  replicas: 2
  template:
    metadata:
      labels:
        app: windows-server-iis
        tier: backend
        track: stable
    spec:
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: windows-server-iis
        image: mcr.microsoft.com/windows/servercore:ltsc2019
        ports:
        - containerPort: 80
        command:
        - powershell.exe
        - -command
        - "Add-WindowsFeature Web-Server; Invoke-WebRequest -UseBasicParsing -Uri 'https://dotnetbinaries.blob.core.windows.net/servicemonitor/2.0.1.6/ServiceMonitor.exe' -OutFile 'C:\\ServiceMonitor.exe'; echo '<html><body><br/><br/><center><h1>Hello from Windows Container</h1></center></body></html>' > C:\\inetpub\\wwwroot\\default.html; C:\\ServiceMonitor.exe 'w3svc';"
```

**Windows Node Limitations:**

1. **Networking Limitations**:
   * Windows nodes は HostPort と HostNetwork modes をサポートしていません。
   * Windows nodes は NodeLocal DNSCache をサポートしていません。
2. **Storage Limitations**:
   * Windows nodes は特定の storage drivers のみをサポートします。
   * host path volume mounts には limitations があります。
3. **Container Runtime**:
   * Windows nodes は containerd runtime のみをサポートします。
   * Linux containers は Windows nodes 上では実行できません。
4. **Feature Limitations**:
   * 一部の Kubernetes features は Windows nodes ではサポートされません。
   * privileged containers、process namespace sharing などには limitations があります。

EKS で Windows worker nodes をサポートするには、少なくとも 1 つの Linux node group が必要ですが、2 つ以上の Linux node groups は必須ではありません。したがって、「少なくとも 2 つの Amazon Linux-based managed node groups が必要」は正確な requirement ではありません。

</details>

3\. 次のうち、Amazon EKS cluster で Windows worker nodes をサポートするための requirement ではないものはどれですか？ - A) 少なくとも 2 つの Amazon Linux-based managed node groups が必要 - B) VPC-CNI、kube-proxy、CoreDNS add-ons installation - C) Windows Server 2019 以降の AMI usage - D) Cluster version 1.14 以降

<details>

<summary>答えを表示</summary>

**答え: A) 少なくとも 2 つの Amazon Linux-based managed node groups が必要**

**解説:** Amazon EKS cluster で Windows worker nodes をサポートするには、少なくとも 1 つ (2 つ以上ではない) の Amazon Linux-based managed node group が必要です。これは、CoreDNS などの essential system pods が Linux nodes 上で実行される必要があるためです。ただし、少なくとも 2 つの Linux node groups が必要というのは正確ではありません。

**EKS で Windows Worker Node Support に必要な実際の Requirements:**

1.  **Linux Node Group Required**:

    * cluster には少なくとも 1 つの Linux node が必要です。
    * CoreDNS、VPC CNI plugin、kube-proxy などの System pods は Linux nodes 上でのみ実行されます。

    ```bash
    # Create Linux node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name linux-ng \
      --node-type m5.large \
      --nodes 2
    ```
2.  **VPC-CNI、kube-proxy、CoreDNS Add-ons Installation**:

    * これらの add-ons は EKS cluster の fundamental components です。
    * Windows node support には specific versions 以上が必要になる場合があります。

    ```bash
    # Check add-on versions
    aws eks describe-addon-versions \
      --addon-name vpc-cni \
      --kubernetes-version 1.23

    # Update add-on
    aws eks update-addon \
      --cluster-name my-cluster \
      --addon-name vpc-cni \
      --addon-version v1.10.4-eksbuild.1
    ```
3.  **Windows Server 2019 or Later AMI Usage**:

    * Windows worker nodes は Windows Server 2019 以降の AMI を使用する必要があります。
    * EKS-optimized Windows AMI の使用が推奨されます。

    ```bash
    # Create Windows node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name windows-ng \
      --node-type m5.large \
      --nodes 2 \
      --node-ami-family WindowsServer2019FullContainer
    ```
4.  **Cluster Version 1.14 or Later**:

    * Windows node support は Kubernetes 1.14 から generally available になりました。
    * latest features のため、より高い version の使用が推奨されます。

    ```bash
    # Check cluster version
    aws eks describe-cluster --name my-cluster --query "cluster.version"
    ```

**Windows Support を有効化する手順:**

1.  **Windows Support を有効化**:

    ```bash
    # Enable Windows support
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/vpc-resource-controller.yaml

    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/vpc-admission-webhook.yaml
    ```
2.  **Windows Node Group を作成**:

    ```bash
    # Create Windows node group using eksctl
    eksctl create nodegroup \
      --cluster my-cluster \
      --name windows-ng \
      --node-type m5.large \
      --nodes 2 \
      --node-ami-family WindowsServer2019FullContainer
    ```
3.  **Windows Nodes を確認**:

    ```bash
    # Verify nodes
    kubectl get nodes -o wide

    # Verify Windows node labels
    kubectl get nodes -l kubernetes.io/os=windows
    ```

**Windows Container Deployment Example:**

```yaml
# Windows Pod deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: windows-server-iis
spec:
  selector:
    matchLabels:
      app: windows-server-iis
      tier: backend
      track: stable
  replicas: 2
  template:
    metadata:
      labels:
        app: windows-server-iis
        tier: backend
        track: stable
    spec:
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: windows-server-iis
        image: mcr.microsoft.com/windows/servercore:ltsc2019
        ports:
        - containerPort: 80
        command:
        - powershell.exe
        - -command
        - "Add-WindowsFeature Web-Server; Invoke-WebRequest -UseBasicParsing -Uri 'https://dotnetbinaries.blob.core.windows.net/servicemonitor/2.0.1.6/ServiceMonitor.exe' -OutFile 'C:\\ServiceMonitor.exe'; echo '<html><body><br/><br/><center><h1>Hello from Windows Container</h1></center></body></html>' > C:\\inetpub\\wwwroot\\default.html; C:\\ServiceMonitor.exe 'w3svc';"
```

**Windows Node Limitations:**

1. **Networking Limitations**:
   * Windows nodes は HostPort と HostNetwork modes をサポートしていません。
   * Windows nodes は NodeLocal DNSCache をサポートしていません。
2. **Storage Limitations**:
   * Windows nodes は特定の storage drivers のみをサポートします。
   * host path volume mounts には limitations があります。
3. **Container Runtime**:
   * Windows nodes は containerd runtime のみをサポートします。
   * Linux containers は Windows nodes 上では実行できません。
4. **Feature Limitations**:
   * 一部の Kubernetes features は Windows nodes ではサポートされません。
   * privileged containers、process namespace sharing などには limitations があります。

EKS で Windows worker nodes をサポートするには、少なくとも 1 つの Linux node group が必要ですが、2 つ以上の Linux node groups は必須ではありません。したがって、「少なくとも 2 つの Amazon Linux-based managed node groups が必要」は正確な requirement ではありません。

</details>

4. Amazon EKS cluster の node groups の Instance Metadata Service (IMDS) を保護する最も効果的な方法は何ですか？
   * A) IMDSv1 を無効化し、IMDSv2 を必須にする
   * B) security group rules で 169.254.169.254 への access を制限する
   * C) node IAM role に restrictive permissions を設定する
   * D) pod service accounts に IAM roles を attach する

<details>

<summary>答えを表示</summary>

**答え: A) IMDSv1 を無効化し、IMDSv2 を必須にする**

**解説:** Amazon EKS cluster の node groups の Instance Metadata Service (IMDS) を保護する最も効果的な方法は、IMDSv1 を無効化し、IMDSv2 を必須にすることです。IMDSv2 は session-based requests を使用して、Server-Side Request Forgery (SSRF) や類似の vulnerabilities から保護する enhanced security features を提供します。

**IMDS Security の重要性:**

Instance Metadata Service は、IAM role credentials を含む EC2 instances に関する重要な information を提供します。この service への unauthorized access は privilege escalation や security breaches につながる可能性があります。Kubernetes environments では、pods が node の IMDS に access できるため、security risk が高まります。

**IMDSv2 の設定方法:**

1.  **Launch Template を使用して IMDSv2 を設定**:

    ```bash
    # Create launch template
    aws ec2 create-launch-template \
      --launch-template-name eks-imdsv2-template \
      --version-description "IMDSv2 required" \
      --launch-template-data '{
        "MetadataOptions": {
          "HttpTokens": "required",
          "HttpPutResponseHopLimit": 1,
          "HttpEndpoint": "enabled"
        }
      }'

    # Create node group using launch template
    eksctl create nodegroup \
      --cluster my-cluster \
      --name ng-imdsv2 \
      --node-type m5.large \
      --nodes 3 \
      --launch-template-name eks-imdsv2-template \
      --launch-template-version 1
    ```
2.  **eksctl Configuration File を使用して IMDSv2 を設定**:

    ```yaml
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig
    metadata:
      name: my-cluster
      region: us-west-2
    managedNodeGroups:
      - name: ng-imdsv2
        instanceType: m5.large
        minSize: 2
        maxSize: 5
        disableIMDSv1: true
        metadataOptions:
          httpTokens: required
          httpPutResponseHopLimit: 1
    ```
3.  **Existing Node Groups を変更**: existing node groups の IMDS settings を変更するには、新しい node group を作成して workloads を migrate する必要があります。Existing EC2 instances の IMDS settings は次のように変更できます:

    ```bash
    aws ec2 modify-instance-metadata-options \
      --instance-id i-1234567890abcdef0 \
      --http-tokens required \
      --http-put-response-hop-limit 1 \
      --http-endpoint enabled
    ```

**IMDSv2 の Security Benefits:**

1. **Session-Based Authentication**:
   * IMDSv2 は PUT requests を通じて生成される tokens を使用し、subsequent requests を authenticate します。
   * これらの tokens は限られた時間だけ valid です。
2. **SSRF Attack Prevention**:
   * Server-Side Request Forgery (SSRF) vulnerabilities を通じた metadata access を防ぎます。
   * token なしでは metadata に access できません。
3. **Hop Limit Setting**:
   * HTTP PUT response hop limit を設定することで、metadata requests が instance 外に redirect されることを防ぎます。
   * default value は 1 であり、requests が instance 内でのみ処理されることを保証します。

**追加の IMDS Security Measures:**

1.  **IMDS を完全に無効化**: 特定 workloads で IMDS が不要な場合、完全に無効化できます:

    ```yaml
    metadataOptions:
      httpEndpoint: disabled
    ```
2.  **Pods から IMDS への Access を Block**: pods が host networking を使用していない場合、iptables rules を追加して IMDS access を block できます:

    ```bash
    iptables -t nat -A PREROUTING -d 169.254.169.254/32 -i eth0 -p tcp -m tcp --dport 80 -j DNAT --to-destination 127.0.0.1:1
    ```
3. **IRSA を使用**: IAM Roles for Service Accounts (IRSA) を使用して pods に必要な AWS permissions を提供し、node IMDS への dependency をなくします。

**その他の選択肢の問題点:**

* **security group rules で 169.254.169.254 への access を制限する**: Security groups は instance 外部から入ってくる traffic を制御しますが、IMDS は instance 内部から access されるため、security groups では制限できません。
* **node IAM role に restrictive permissions を設定する**: これは優れた security practice ですが、IMDS 自体の security を強化するものではありません。attacker が IMDS に access できる場合、limited permissions であっても悪用される可能性があります。
* **pod service accounts に IAM roles を attach する**: IRSA は pods が node IMDS に依存しないようにする優れた方法ですが、node IMDS 自体の security を直接強化するものではありません。

IMDSv1 を無効化し IMDSv2 を必須にすることは、EKS nodes の metadata service を保護する最も効果的な方法です。これは AWS security best practice であり、特に multi-tenant Kubernetes environments では重要です。

</details>

5. 次のうち、Amazon EKS cluster で node groups を作成する際に bootstrap scripts をカスタマイズする primary purpose ではないものはどれですか？
   * A) cluster control plane components を変更する
   * B) additional software をインストールする
   * C) kernel parameters を調整する
   * D) node labels と taints を設定する

<details>

<summary>答えを表示</summary>

**答え: A) cluster control plane components を変更する**

**解説:** Amazon EKS cluster で node groups を作成する際に bootstrap scripts をカスタマイズする primary purpose は、cluster control plane components を変更することではありません。EKS は control plane が AWS によって管理される managed service であり、users が直接変更することはできません。Bootstrap scripts は worker node configurations のみを変更できます。

**Bootstrap Scripts の実際の Use Cases:**

1.  **Additional Software のインストール**:

    * Monitoring agents (CloudWatch Agent、Prometheus Node Exporter など)
    * Logging tools (Fluentd、Fluent Bit など)
    * Security tools (Falco、Sysdig など)
    * Performance optimization tools

    ```bash
    #!/bin/bash
    # Install CloudWatch agent
    wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
    rpm -U amazon-cloudwatch-agent.rpm

    # Create configuration file
    cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
    {
      "metrics": {
        "metrics_collected": {
          "mem": {
            "measurement": ["mem_used_percent"]
          },
          "swap": {
            "measurement": ["swap_used_percent"]
          }
        }
      }
    }
    EOF

    # Start agent
    /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s
    ```
2.  **Kernel Parameters の調整**:

    * Network setting optimization
    * Memory management settings
    * File system and I/O settings

    ```bash
    #!/bin/bash
    # Adjust kernel parameters
    cat > /etc/sysctl.d/99-kubernetes.conf << EOF
    net.ipv4.ip_forward = 1
    net.bridge.bridge-nf-call-iptables = 1
    net.ipv4.tcp_keepalive_time = 600
    net.ipv4.tcp_max_syn_backlog = 40000
    net.core.somaxconn = 40000
    net.core.netdev_max_backlog = 40000
    vm.max_map_count = 262144
    EOF

    # Apply changes
    sysctl --system
    ```
3.  **Node Labels と Taints の設定**:

    * node role labels の設定
    * hardware characteristic labels の設定
    * specific workloads 向け taints の設定

    ```bash
    #!/bin/bash
    # Execute EKS bootstrap script
    /etc/eks/bootstrap.sh my-cluster \
      --kubelet-extra-args '--node-labels=node.kubernetes.io/role=worker,environment=prod,node-type=compute --register-with-taints=dedicated=compute:NoSchedule'
    ```
4.  **Disk and File System Configuration**:

    * additional volumes の mounting
    * file system optimization
    * temporary storage configuration

    ```bash
    #!/bin/bash
    # Format and mount additional EBS volume
    mkfs -t xfs /dev/nvme1n1
    mkdir -p /data
    mount /dev/nvme1n1 /data
    echo "/dev/nvme1n1 /data xfs defaults 0 0" >> /etc/fstab
    ```
5.  **Security Configuration**:

    * firewall rules の設定
    * security hardening settings
    * log audit configuration

    ```bash
    #!/bin/bash
    # Set firewall rules
    iptables -A INPUT -p tcp --dport 22 -s 10.0.0.0/8 -j ACCEPT
    iptables -A INPUT -p tcp --dport 22 -j DROP

    # Security hardening settings
    sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
    systemctl restart sshd
    ```

**Bootstrap Scripts の実装方法:**

1.  **Launch Template を使用した User Data Script**:

    ```bash
    # Create launch template
    aws ec2 create-launch-template \
      --launch-template-name eks-custom-bootstrap \
      --version-description "Custom bootstrap script" \
      --launch-template-data '{
        "UserData": "BASE64_ENCODED_USER_DATA_SCRIPT"
      }'

    # Create node group using launch template
    eksctl create nodegroup \
      --cluster my-cluster \
      --name custom-ng \
      --node-type m5.large \
      --nodes 3 \
      --launch-template-name eks-custom-bootstrap \
      --launch-template-version 1
    ```
2.  **eksctl Configuration File を使用した User Data Script**:

    ```yaml
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig
    metadata:
      name: my-cluster
      region: us-west-2
    managedNodeGroups:
      - name: custom-ng
        instanceType: m5.large
        minSize: 2
        maxSize: 5
        preBootstrapCommands:
          - "echo 'net.ipv4.ip_forward = 1' >> /etc/sysctl.d/99-kubernetes.conf"
          - "sysctl --system"
        kubeletExtraArgs:
          node-labels: "environment=prod,node-type=compute"
    ```

**Cluster Control Plane Components:**

EKS cluster の control plane components は AWS によって管理されており、bootstrap scripts を通じて変更することはできません:

* API Server
* Controller Manager
* Scheduler
* etcd
* CoreDNS

これらの components を変更するには、AWS が提供する APIs を通じて cluster level で設定する必要があります。たとえば、control plane logging は次のように設定できます:

```bash
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

bootstrap script は worker node configurations のみを変更でき、cluster control plane components を変更することはできません。したがって、「cluster control plane components を変更する」は bootstrap script の primary purpose ではありません。

</details>

# EKS Security Best Practices クイズ

以下の質問で、Amazon EKS security best practices についての理解を確認しましょう。

***

## 質問

### 1. IRSA (IAM Roles for Service Accounts) を使用して AWS APIs を呼び出すとき、Pod はどの認証方式を使用しますか？

* A) IAM User Access Key
* B) EC2 Instance Profile
* C) OIDC token-based AssumeRoleWithWebIdentity
* D) Kubernetes Secret に保存された認証情報

<details>

<summary>回答を表示</summary>

**回答: C) OIDC token-based AssumeRoleWithWebIdentity**

**解説:** IRSA の仕組み:

1. EKS cluster の OIDC Provider が ServiceAccount token を発行する
2. Pod が AWS STS `AssumeRoleWithWebIdentity` API を呼び出す
3. OIDC token が検証され、一時的な認証情報が発行される
4. Pod が一時的な認証情報を使用して AWS APIs を呼び出す

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-reader
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/S3ReaderRole
```

IRSA により、node level ではなく Pod level で、きめ細かな権限管理が可能になります。

</details>

***

### 2. IRSA と比較した EKS Pod Identity の主な利点は何ですか？

* A) より強力な暗号化
* B) より高速な性能
* C) OIDC Provider の設定が不要で、管理が簡素化される
* D) より多くの AWS services のサポート

<details>

<summary>回答を表示</summary>

**回答: C) OIDC Provider の設定が不要で、管理が簡素化される**

**解説:** EKS Pod Identity の利点:

* OIDC Provider の設定が不要
* IAM Role Trust Policy の簡素化
* Pod Identity Agent による自動的な認証情報管理
* cross-account access の簡素化

```bash
# Pod Identity association (simple CLI setup)
aws eks create-pod-identity-association \
  --cluster-name my-cluster \
  --namespace production \
  --service-account myapp-sa \
  --role-arn arn:aws:iam::123456789012:role/MyAppRole
```

IRSA では、各 cluster に OIDC Provider の設定と複雑な Trust Policy が必要です。

</details>

***

### 3. Security Groups for Pods を使用するための要件ではないものはどれですか？

* A) Nitro-based instance types
* B) Amazon VPC CNI plugin
* C) Fargate profile
* D) ENIConfig または SecurityGroupPolicy CRD

<details>

<summary>回答を表示</summary>

**回答: C) Fargate profile**

**解説:** Security Groups for Pods の要件:

* **必須**: Nitro-based EC2 instances (m5, c5, r5, etc.)
* **必須**: Amazon VPC CNI plugin v1.7.7+
* **必須**: SecurityGroupPolicy CRD の設定
* **任意**: Fargate (別の設定方法)

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: db-access-policy
spec:
  podSelector:
    matchLabels:
      app: backend
  securityGroups:
    groupIds:
      - sg-0123456789abcdef0
```

Fargate は各 Pod に ENI を自動的に割り当てるため、別の設定が必要です。

</details>

***

### 4. EKS cluster の Kubernetes API server endpoint を private only に設定すると、どのような影響がありますか？

* A) kubectl をまったく使用できない
* B) VPC 内または接続された networks からのみアクセス可能
* C) AWS Console から cluster を管理できない
* D) Worker nodes が API server に接続できない

<details>

<summary>回答を表示</summary>

**回答: B) VPC 内または接続された networks からのみアクセス可能**

**解説:** private endpoint が設定されている場合:

* VPC 内からアクセス可能
* VPN、Direct Connect、VPC Peering 経由で接続された networks からアクセス可能
* public internet からはアクセス不可

```bash
# Endpoint configuration
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config \
    endpointPublicAccess=false,endpointPrivateAccess=true
```

security のため、private endpoint のみを使用することが推奨されます。

</details>

***

### 5. AWS GuardDuty EKS Protection で検出されない threat type はどれですか？

* A) 悪意のある IPs との通信
* B) 暗号通貨マイニング活動
* C) Pod resource usage が limits を超過すること
* D) Tor network connections

<details>

<summary>回答を表示</summary>

**回答: C) Pod resource usage が limits を超過すること**

**解説:** GuardDuty EKS Protection が検出する threats:

* 悪意のある IP addresses との通信
* 暗号通貨マイニング (Kubernetes API abuse)
* Tor network connections
* DNS Rebinding attacks
* Privilege escalation attempts
* Abnormal API call patterns

Resource usage の監視は以下によって実行されます:

* Kubernetes Metrics Server
* Prometheus/Grafana
* CloudWatch Container Insights

</details>

***

### 6. EKS cluster で VPC endpoints を必要としない AWS service はどれですか？

* A) ECR (dkr, api)
* B) S3
* C) STS
* D) Route 53

<details>

<summary>回答を表示</summary>

**回答: D) Route 53**

**解説:** EKS に推奨される VPC endpoints:

* **ECR (dkr, api)**: Container image の取得
* **S3**: image layer の保存
* **STS**: IRSA/Pod Identity の認証
* **CloudWatch Logs**: log の送信
* **EC2, ELB, Auto Scaling**: Node の管理

Route 53 は、VPC endpoints ではなく標準の DNS resolution を使用する global DNS service です。

```bash
# Create required VPC endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxx \
  --service-name com.amazonaws.region.ecr.dkr \
  --vpc-endpoint-type Interface
```

</details>

***

### 7. kube-bench で EKS cluster security を確認する際に使用される benchmark は何ですか？

* A) PCI-DSS
* B) CIS Kubernetes Benchmark
* C) NIST Cybersecurity Framework
* D) SOC 2

<details>

<summary>回答を表示</summary>

**回答: B) CIS Kubernetes Benchmark**

**解説:** kube-bench は CIS (Center for Internet Security) Kubernetes Benchmark に照らして cluster security を確認します:

```bash
# Run kube-bench on EKS node
kubectl apply -f https://raw.githubusercontent.com/aquasecurity/kube-bench/main/job-eks.yaml

# Check results
kubectl logs job/kube-bench
```

検査項目:

* Control Plane の設定 (EKS managed のため一部 N/A)
* Worker Node の設定
* Policies と Pod security
* Network policies
* Logging と auditing

</details>

***

### 8. Service Account Token Volume Projection は EKS でどの security benefit を提供しますか？

* A) token size の削減
* B) Bound tokens と expiration time settings
* C) Token encryption
* D) 自動 token backup

<details>

<summary>回答を表示</summary>

**回答: B) Bound tokens と expiration time settings**

**解説:** Service Account Token Volume Projection の security benefits:

* **Bound tokens**: 特定の Pod に対してのみ有効
* **Expiration time**: 自動的な token expiration (default 1 hour)
* **Audience specification**: 特定の audience に対してのみ有効

```yaml
spec:
  containers:
    - name: app
      volumeMounts:
        - name: token
          mountPath: /var/run/secrets/tokens
  volumes:
    - name: token
      projected:
        sources:
          - serviceAccountToken:
              path: token
              expirationSeconds: 3600
              audience: sts.amazonaws.com
```

Legacy tokens は期限切れにならないため、漏洩した場合にリスクがあります。

</details>

***

### 9. Amazon Inspector は EKS environment で何をスキャンしますか？

* A) Kubernetes manifests
* B) Container image vulnerabilities
* C) IAM policies
* D) Network traffic

<details>

<summary>回答を表示</summary>

**回答: B) Container image vulnerabilities**

**解説:** Amazon Inspector の EKS integration:

* ECR に保存された container images をスキャン
* running workloads の images をスキャン
* OS package vulnerabilities を検出
* application package vulnerabilities (npm, pip, etc.) を検出

```bash
# Enable Inspector
aws inspector2 enable \
  --resource-types ECR

# Check scan results
aws inspector2 list-findings \
  --filter-criteria resourceType=AWS_ECR_CONTAINER_IMAGE
```

Continuous scanning により、新しい CVEs が発見されたときに alerts が提供されます。

</details>

***

### 10. EKS cluster Control Plane logs を CloudWatch に送信する際、有効化できない log type はどれですか？

* A) api
* B) audit
* C) controllerManager
* D) kubelet

<details>

<summary>回答を表示</summary>

**回答: D) kubelet**

**解説:** EKS Control Plane log types:

* **api**: API server logs
* **audit**: Audit logs (誰が何をしたか)
* **authenticator**: IAM authentication logs
* **controllerManager**: Controller manager logs
* **scheduler**: Scheduler logs

kubelet logs は worker nodes 上で生成されるため、Control Plane logs ではありません。

```bash
# Enable Control Plane logging
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

</details>

***

### 11. EKS で Node IAM Role と Pod IAM Role (IRSA) を分離すべき理由は何ですか？

* A) コスト削減
* B) 最小権限の原則の適用
* C) 性能向上
* D) network latency の削減

<details>

<summary>回答を表示</summary>

**回答: B) 最小権限の原則の適用**

**解説:** 権限分離の重要性:

**Node IAM Role (広い scope):**

* すべての Pods からアクセス可能 (Instance Metadata)
* ECR pull、CloudWatch logs などの基本的な permissions のみ

**IRSA (狭い scope):**

* 特定の ServiceAccount のみに接続
* application ごとに必要な permissions のみを付与

```yaml
# Wrong example: S3 full access on Node Role
# -> All Pods can access S3

# Correct example: Grant permissions only to specific Pod via IRSA
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-processor
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::xxx:role/S3ProcessorRole
```

</details>

***

### 12. EKS で Kubernetes RBAC と AWS IAM の統合を担当する component はどれですか？

* A) kube-apiserver
* B) aws-auth ConfigMap
* C) aws-iam-authenticator
* D) kube-proxy

<details>

<summary>回答を表示</summary>

**回答: C) aws-iam-authenticator**

**解説:** EKS authentication flow:

1. kubectl が AWS STS から token を取得する
2. aws-iam-authenticator が IAM credentials を検証する
3. aws-auth ConfigMap が IAM -> Kubernetes user/group を map する
4. Kubernetes RBAC が permissions を決定する

```yaml
# aws-auth ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: arn:aws:iam::123456789012:role/DevTeamRole
      username: dev-user
      groups:
        - dev-team
  mapUsers: |
    - userarn: arn:aws:iam::123456789012:user/admin
      username: admin
      groups:
        - system:masters
```

</details>

***

## スコア計算

各質問につき 1 点で計算します。

| スコア | 評価                                                     |
| ----- | ---------------------------------------------------------- |
| 11-12 | 優秀 - EKS security expert level                          |
| 8-10  | 良好 - 基本概念を理解済み、advanced features の復習を推奨 |
| 5-7   | 平均 - 追加学習を推奨                                     |
| 0-4   | 基礎学習が必要                                           |

***

## 関連ドキュメント

* [EKS Security Best Practices](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/security/06-eks-security-best-practices.md)
* [Pod Security Standards](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/security/03-pod-security-standards.md)
* [Secrets Management](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/security/05-secrets-management.md)

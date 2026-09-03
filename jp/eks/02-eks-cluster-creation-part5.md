# Part 5: Cluster Access、検証、アップグレード、削除

## Cluster Access の設定

EKS cluster を作成した後、cluster にアクセスするための設定が必要です。このセクションでは、cluster access の設定方法を学びます。

### Cluster Access の設定プロセス

![アクセス設定フローの図: kubeconfig、IAM principal、access entry、RBAC rules と binding、そして access test。](../.gitbook/assets/en-eks-02-eks-cluster-creation-part5-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part5-0.html)

### kubeconfig の設定

EKS cluster にアクセスするには、kubeconfig file を設定する必要があります。AWS CLI を使用して kubeconfig を設定できます。

```bash
aws eks update-kubeconfig \
  --name my-cluster \
  --region us-west-2
```

このコマンドは `~/.kube/config` file を更新し、EKS cluster へのアクセスを有効にします。

### IAM User および Role Access の設定

デフォルトでは、EKS cluster を作成した IAM entity（user または role）のみが cluster にアクセスできます。他の IAM user または role に cluster access を付与する方法は、従来の aws-auth ConfigMap method と新しい EKS Access Entry method の 2 つです。

![IAM principal が Kubernetes API にマッピングされる 2 つの方法を比較する図: EKS access entries と aws-auth ConfigMap。](../.gitbook/assets/en-eks-02-eks-cluster-creation-part5-1.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part5-1.html)

#### Method 1: EKS Access Entry（推奨）

EKS Access Entry は aws-auth ConfigMap に代わる新しい方法で、より安定し、管理しやすいアプローチを提供します。

1. cluster の Access Entry を有効にします。

```bash
aws eks update-cluster-config \
  --name my-cluster \
  --region us-west-2 \
  --access-config authenticationMode=API_AND_CONFIG_MAP
```

2. IAM role の Access Entry を作成します。

```bash
aws eks create-access-entry \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:role/MyRole \
  --username my-role \
  --kubernetes-groups system:masters
```

3. IAM user の Access Entry を作成します。

```bash
aws eks create-access-entry \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:user/my-user \
  --username my-user \
  --kubernetes-groups system:masters
```

4. Access Entry を一覧表示します。

```bash
aws eks list-access-entries --cluster-name my-cluster
```

5. Access Entry の詳細を確認します。

```bash
aws eks describe-access-entry \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:user/my-user
```

#### Method 2: aws-auth ConfigMap（レガシー）

aws-auth ConfigMap は従来の方法であり、現在もサポートされていますが、新しい cluster では Access Entry の使用が推奨されます。

1. 現在の `aws-auth` ConfigMap を取得します。

```bash
kubectl get configmap aws-auth -n kube-system -o yaml > aws-auth.yaml
```

2. `aws-auth.yaml` file を編集して、user または role を追加します。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: arn:aws:iam::123456789012:role/EKSNodeRole
      username: system:node:{{EC2PrivateDNSName}}
      groups:
        - system:bootstrappers
        - system:nodes
    # Additional role
    - rolearn: arn:aws:iam::123456789012:role/MyRole
      username: my-role
      groups:
        - system:masters
  mapUsers: |
    # IAM user
    - userarn: arn:aws:iam::123456789012:user/my-user
      username: my-user
      groups:
        - system:masters
```

3. 更新した ConfigMap を適用します。

```bash
kubectl apply -f aws-auth.yaml
```

> **注記**: EKS Access Entry は 2023 年に導入され、新しい cluster では Access Entry の使用が推奨されます。既存の cluster は、両方の方法をサポートする hybrid mode に移行できます。

### RBAC の設定

Kubernetes Role-Based Access Control（RBAC）を使用して、cluster 内の resource へのアクセスを制御できます。

1. namespace を作成します。

```bash
kubectl create namespace dev
```

2. role を作成します。

```yaml
# role.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: dev
  name: developer
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps", "secrets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "daemonsets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
```

```bash
kubectl apply -f role.yaml
```

3. role binding を作成します。

```yaml
# rolebinding.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer-binding
  namespace: dev
subjects:
- kind: User
  name: my-user
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer
  apiGroup: rbac.authorization.k8s.io
```

```bash
kubectl apply -f rolebinding.yaml
```

## Cluster の検証

EKS cluster を作成した後、cluster が正しく動作していることを確認する必要があります。このセクションでは、cluster の検証方法を学びます。

### Cluster の検証プロセス

![node と system Pod を確認し、test app を Deployment して公開した後、log を確認する cluster validation の図。](../.gitbook/assets/en-eks-02-eks-cluster-creation-part5-2.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part5-2.html)

### Node の確認

cluster 内の node を確認します。

```bash
kubectl get nodes
```

すべての node が `Ready` state であることを確認します。

### System Pod の確認

kube-system namespace の Pod を確認します。

```bash
kubectl get pods -n kube-system
```

すべての system Pod が `Running` state であることを確認します。

### Test Application の Deployment

cluster が正しく動作していることを確認するため、シンプルな test application を Deployment します。

```yaml
# nginx.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: nginx
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 80
  selector:
    app: nginx
```

```bash
kubectl apply -f nginx.yaml
```

Deployment と Service の status を確認します。

```bash
kubectl get deployments
kubectl get pods
kubectl get services
```

LoadBalancer Service の external IP を使用して application にアクセスできることを確認します。

```bash
curl http://<EXTERNAL-IP>
```

### Cluster Log の確認

CloudWatch Logs で cluster log を確認します。

```bash
aws logs describe-log-groups \
  --log-group-name-prefix /aws/eks/my-cluster
```

## Cluster のアップグレード

EKS cluster を最新の状態に保つには、定期的なアップグレードが必要です。このセクションでは、cluster のアップグレード方法を学びます。

### Cluster のアップグレードプロセス

![planning と version check から control plane、node group、add-on、function test へと進むアップグレードプロセスの図。](../.gitbook/assets/en-eks-02-eks-cluster-creation-part5-3.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part5-3.html)

### Control Plane のアップグレード

EKS control plane をアップグレードするには、次の手順に従います。

1. 利用可能な Kubernetes version を確認します。

```bash
aws eks describe-addon-versions \
  --kubernetes-version 1.27 \
  --query "addons[].addonVersions[].compatibilities[].clusterVersion"
```

2. cluster をアップグレードします。

```bash
aws eks update-cluster-version \
  --name my-cluster \
  --kubernetes-version 1.27
```

3. アップグレードの status を確認します。

```bash
aws eks describe-update \
  --name my-cluster \
  --update-id <UPDATE-ID>
```

### Node のアップグレード

control plane をアップグレードした後、node もアップグレードする必要があります。

#### Managed Node Group のアップグレード

```bash
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup
```

#### Self-Managed Node のアップグレード

self-managed node の場合、新しい node group を作成し、workload を移行してから、古い node group を削除する必要があります。

### Add-on のアップグレード

EKS add-on をアップグレードするには、次の手順に従います。

1. 利用可能な add-on version を確認します。

```bash
aws eks describe-addon-versions \
  --addon-name vpc-cni \
  --kubernetes-version 1.27
```

2. add-on をアップグレードします。

```bash
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version <VERSION>
```

## Cluster の削除

EKS cluster が不要になった場合、cost を削減するために削除できます。このセクションでは、cluster の削除方法を学びます。

### Cluster の削除プロセス

![LoadBalancer と PVC を削除し、node group と Fargate profile、cluster を削除してから、残存 resource を確認する削除プロセスの図。](../.gitbook/assets/en-eks-02-eks-cluster-creation-part5-4.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part5-4.html)

### Resource のクリーンアップ

cluster を削除する前に、cluster 内に作成されたすべての resource をクリーンアップする必要があります。

1. LoadBalancer Service を削除します。

```bash
kubectl get services --all-namespaces -o json | jq -r '.items[] | select(.spec.type == "LoadBalancer") | .metadata.name + " " + .metadata.namespace' | while read name namespace; do
  kubectl delete service $name -n $namespace
done
```

2. PersistentVolumeClaim を削除します。

```bash
kubectl delete pvc --all --all-namespaces
```

### eksctl を使用した Cluster の削除

cluster を eksctl で作成した場合は、次のコマンドで削除できます。

```bash
eksctl delete cluster --name my-cluster --region us-west-2
```

### AWS CLI を使用した Cluster の削除

AWS CLI を使用して cluster を削除するには、次の手順に従います。

1. node group を削除します。

```bash
aws eks delete-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup
```

2. Fargate profile を削除します。

```bash
aws eks delete-fargate-profile \
  --cluster-name my-cluster \
  --fargate-profile-name my-fargate-profile
```

3. cluster を削除します。

```bash
aws eks delete-cluster \
  --name my-cluster
```

### 関連 Resource のクリーンアップ

EKS cluster を削除した後、次の関連 resource が残る場合があります。

1. VPC と関連 resource:

```bash
aws ec2 delete-vpc --vpc-id vpc-xxxxxxxxxxxxxxxxx
```

2. IAM role と policy:

```bash
aws iam detach-role-policy \
  --role-name EKSClusterRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy

aws iam delete-role --role-name EKSClusterRole

aws iam detach-role-policy \
  --role-name EKSNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy

aws iam detach-role-policy \
  --role-name EKSNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy

aws iam detach-role-policy \
  --role-name EKSNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

aws iam delete-role --role-name EKSNodeRole
```

3. CloudWatch log group:

```bash
aws logs delete-log-group \
  --log-group-name /aws/eks/my-cluster/cluster
```

## クイズ

この章で学んだ内容を確認するには、[EKS Cluster Creation - Part 5 クイズ](../quizzes/eks/02-eks-cluster-creation-part5-quiz.md)に挑戦してください。

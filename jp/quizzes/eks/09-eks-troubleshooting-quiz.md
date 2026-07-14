# Amazon EKS トラブルシューティングクイズ

このクイズでは、Amazon EKS クラスターで発生する可能性があるさまざまな問題を診断し、解決する能力を確認します。

## クイズ概要
- クラスター作成と設定の問題
- ネットワークの問題
- Node と Pod の問題
- Storage の問題
- セキュリティとアクセスの問題
- パフォーマンスとスケーラビリティの問題

## 多肢選択問題

### 1. Amazon EKS クラスターの作成に失敗した場合、最初に何を確認すべきですか？

A. クラスター名が一意であるか確認する
B. IAM permissions、VPC configuration、service quotas を確認する
C. 別の region で再試行する
D. より大きな instance type を選択する

<details>
<summary>解答を表示</summary>

**解答: B. IAM permissions、VPC configuration、service quotas を確認する**

**解説:**
Amazon EKS クラスターの作成に失敗した場合、最初に確認すべきものは IAM permissions、VPC configuration、service quotas です。これらはクラスター作成失敗の最も一般的な原因であり、体系的に確認することで問題をすばやく特定し解決できます。

**確認すべき主な項目:**

1. **IAM permissions の確認**:
   - クラスター作成に必要な IAM permissions があるか
   - service-linked roles を作成する権限
   - Cluster role と policy configuration

2. **VPC configuration の確認**:
   - Subnet configuration（少なくとも 2 つの availability zones に分散された subnets）
   - Subnet CIDR size（最小 /28、推奨 /24）
   - Internet connectivity（NAT gateway または internet gateway）
   - Security group と network ACL settings

3. **Service quotas の確認**:
   - EKS cluster count quota
   - EC2 instance quota
   - VPC と subnet quotas
   - その他の関連 service quotas

**トラブルシューティング方法:**

1. **IAM permission issues の解決**:
   ```bash
   # Check IAM permissions
   aws sts get-caller-identity

   # Attach required policy
   aws iam attach-user-policy \
     --user-name myuser \
     --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy

   # Create service-linked role
   aws iam create-service-linked-role --aws-service-name eks.amazonaws.com
   ```

2. **VPC configuration issues の解決**:
   ```bash
   # Check VPC and subnets
   aws ec2 describe-vpcs --vpc-ids vpc-12345678
   aws ec2 describe-subnets --filters "Name=vpc-id,Values=vpc-12345678"

   # Check subnet tags
   aws ec2 describe-tags --filters "Name=resource-id,Values=subnet-12345678"

   # Add subnet tags
   aws ec2 create-tags \
     --resources subnet-12345678 subnet-87654321 \
     --tags Key=kubernetes.io/cluster/my-cluster,Value=shared
   ```

3. **Service quota issues の解決**:
   ```bash
   # Check service quotas
   aws service-quotas list-service-quotas --service-code eks

   # Request quota increase
   aws service-quotas request-service-quota-increase \
     --service-code eks \
     --quota-code L-1194D53C \
     --desired-value 10
   ```

**一般的なエラーメッセージと解決策:**

1. **IAM permissions 不足**:
   - エラー: "User: arn:aws:iam::123456789012:user/myuser is not authorized to perform: eks:CreateCluster"
   - 解決策: 必要な IAM permissions を追加する

2. **VPC subnet issues**:
   - エラー: "Cannot create cluster 'my-cluster' because us-west-2a, the targeted availability zone, does not have sufficient capacity to support the cluster. Retry after some time or try other availability zones."
   - 解決策: 別の availability zones の subnets を使用する、または新しい subnets を作成する

3. **Service quota 超過**:
   - エラー: "Account cannot create more EKS clusters in region us-west-2. Current limit is 5"
   - 解決策: service quota increase をリクエストする、または不要なクラスターを削除する

**ベストプラクティス:**

1. **クラスター作成前の準備**:
   - 必要な IAM permissions を確認する
   - 適切な VPC と subnets を設定する
   - Service quotas を確認する

2. **体系的なトラブルシューティングアプローチ**:
   - エラーメッセージを分析する
   - AWS CloudTrail logs を確認する
   - コンポーネントを段階的に検証する

3. **自動化された infrastructure configuration**:
   - AWS CloudFormation または Terraform を使用する
   - eksctl などの tools を活用する
   - Infrastructure configuration を version control する

**実践的な実装例:**

1. **eksctl によるクラスター作成のトラブルシューティング**:
   ```bash
   # Create cluster in debug mode
   eksctl create cluster --name my-cluster --region us-west-2 --verbose 4

   # Check cluster creation status
   eksctl get cluster --name my-cluster --region us-west-2
   ```

2. **AWS CLI によるクラスター作成のトラブルシューティング**:
   ```bash
   # Attempt cluster creation
   aws eks create-cluster \
     --name my-cluster \
     --role-arn arn:aws:iam::123456789012:role/eks-cluster-role \
     --resources-vpc-config subnetIds=subnet-12345678,subnet-87654321,securityGroupIds=sg-12345678

   # Check cluster status
   aws eks describe-cluster --name my-cluster
   ```

3. **Terraform によるクラスター作成のトラブルシューティング**:
   ```hcl
   # EKS cluster definition
   resource "aws_eks_cluster" "main" {
     name     = "my-cluster"
     role_arn = aws_iam_role.eks_cluster.arn

     vpc_config {
       subnet_ids         = var.subnet_ids
       security_group_ids = [aws_security_group.eks_cluster.id]
     }

     # Explicit dependencies
     depends_on = [
       aws_iam_role_policy_attachment.eks_cluster_policy,
       aws_iam_role_policy_attachment.eks_service_policy
     ]
   }

   # Debug output on error
   output "cluster_status" {
     value = aws_eks_cluster.main.status
   }
   ```

他の選択肢の問題点:
- **A. クラスター名が一意であるか確認する**: 一意でないクラスター名はエラーの原因になり得ますが、最も一般的な失敗原因ではありません。
- **C. 別の region で再試行する**: これは根本原因を解決しない回避策であり、他の regions でも同じ問題が発生する可能性があります。
- **D. より大きな instance type を選択する**: Instance type は node groups に適用されるものであり、クラスター作成自体には影響しません。
</details>
### 2. Amazon EKS クラスターで node が NotReady 状態の場合、最も効果的なトラブルシューティングアプローチは何ですか？

A. すぐに node を終了して置き換える
B. Node logs、resource usage、network connectivity を確認する
C. Cluster API server を再起動する
D. すべての pods を削除して再デプロイする

<details>
<summary>解答を表示</summary>

**解答: B. Node logs、resource usage、network connectivity を確認する**

**解説:**
Amazon EKS クラスターで node が NotReady 状態の場合、最も効果的なトラブルシューティングアプローチは node logs、resource usage、network connectivity を確認することです。この体系的なアプローチにより、問題の根本原因を特定し、適切な解決策を適用できます。

**確認すべき主な項目:**

1. **Node status と events の確認**:
   - Node status の詳細
   - Node 関連 events
   - Node conditions

2. **Node logs の分析**:
   - kubelet logs
   - System logs
   - Container runtime logs

3. **Resource usage の確認**:
   - CPU、memory、disk usage
   - Resource limits と pressure
   - System process status

4. **Network connectivity の確認**:
   - Control plane への接続
   - DNS resolution
   - VPC と subnet configuration

**トラブルシューティング方法:**

1. **Node status と events の確認**:
   ```bash
   # Check node status
   kubectl get nodes
   kubectl describe node <node-name>

   # Check node events
   kubectl get events --field-selector involvedObject.name=<node-name>
   ```

2. **Node logs の分析**:
   ```bash
   # SSH access to node (for self-managed nodes)
   ssh ec2-user@<node-ip>

   # Check kubelet logs
   sudo journalctl -u kubelet

   # Check system logs
   sudo tail -f /var/log/syslog

   # Check container runtime logs
   sudo journalctl -u docker  # When using Docker
   sudo journalctl -u containerd  # When using containerd
   ```

3. **Resource usage の確認**:
   ```bash
   # Check node resource usage
   kubectl top node <node-name>

   # Check resources via SSH
   ssh ec2-user@<node-ip>

   # Check disk usage
   df -h

   # Check memory usage
   free -m

   # Check CPU usage
   top
   ```

4. **Network connectivity の確認**:
   ```bash
   # Check API server connection from node
   curl -k https://<api-server-endpoint>

   # Check DNS resolution
   nslookup kubernetes.default.svc.cluster.local

   # Check network interfaces
   ip addr show

   # Check routing table
   ip route
   ```

**一般的な NotReady の原因と解決策:**

1. **kubelet issues**:
   - **症状**: kubelet service が実行されていない、または API server に接続できない
   - **解決策**:
     ```bash
     # Check kubelet service status
     sudo systemctl status kubelet

     # Restart kubelet service
     sudo systemctl restart kubelet

     # Check kubelet configuration
     sudo cat /etc/kubernetes/kubelet/kubelet-config.json
     ```

2. **Network issues**:
   - **症状**: Node が control plane と通信できない
   - **解決策**:
     ```bash
     # Check security groups
     aws ec2 describe-security-groups --group-ids sg-12345678

     # Check routing tables
     aws ec2 describe-route-tables --route-table-ids rtb-12345678

     # Check VPC CNI pod status
     kubectl get pods -n kube-system -l k8s-app=aws-node
     kubectl logs -n kube-system -l k8s-app=aws-node
     ```

3. **Resource shortage**:
   - **症状**: Node 上の CPU、memory、または disk space が不足している
   - **解決策**:
     ```bash
     # Free up disk space
     sudo du -sh /var/log/*
     sudo journalctl --vacuum-time=1d

     # Clean up unnecessary containers and images
     docker system prune -af  # When using Docker
     ```

4. **Certificate issues**:
   - **症状**: Certificate が期限切れ、または不一致
   - **解決策**:
     ```bash
     # Check certificates
     sudo ls -la /etc/kubernetes/pki/

     # Renew certificates (for self-managed nodes)
     sudo kubeadm alpha certs renew all

     # For managed node groups, replace nodes
     eksctl replace nodegroup --cluster=my-cluster --name=my-nodegroup
     ```

**ベストプラクティス:**

1. **体系的なトラブルシューティングアプローチ**:
   - 症状を特定して文書化する
   - 関連する logs と events を収集する
   - 考えられる原因を体系的に検証する

2. **Node status monitoring の実装**:
   - CloudWatch alarms を設定する
   - Node status dashboards を設定する
   - 自動 alerting system

3. **Auto-recovery mechanisms の実装**:
   - Self-healing node groups を設定する
   - Health checks と automatic replacement
   - Failed nodes の automatic draining

**実践的な実装例:**

1. **Node troubleshooting script**:
   ```bash
   #!/bin/bash
   # EKS node troubleshooting script

   NODE_NAME=$1

   if [ -z "$NODE_NAME" ]; then
     echo "Please specify a node name."
     exit 1
   fi

   echo "=== Troubleshooting node $NODE_NAME ==="

   # Check node status
   echo "=== Check node status ==="
   kubectl get node $NODE_NAME -o wide
   kubectl describe node $NODE_NAME

   # Check node events
   echo
   echo "=== Check node events ==="
   kubectl get events --field-selector involvedObject.name=$NODE_NAME --sort-by='.lastTimestamp'

   # Check node pods
   echo
   echo "=== Check node pods ==="
   kubectl get pods --all-namespaces -o wide --field-selector spec.nodeName=$NODE_NAME

   # Check system pod logs
   echo
   echo "=== Check system pod logs ==="
   NODE_IP=$(kubectl get node $NODE_NAME -o jsonpath='{.status.addresses[?(@.type=="InternalIP")].address}')
   KUBE_PROXY_POD=$(kubectl get pods -n kube-system -l k8s-app=kube-proxy -o wide | grep $NODE_IP | awk '{print $1}')
   AWS_NODE_POD=$(kubectl get pods -n kube-system -l k8s-app=aws-node -o wide | grep $NODE_IP | awk '{print $1}')

   if [ -n "$KUBE_PROXY_POD" ]; then
     echo "kube-proxy logs:"
     kubectl logs -n kube-system $KUBE_PROXY_POD --tail=50
   fi

   if [ -n "$AWS_NODE_POD" ]; then
     echo
     echo "aws-node (VPC CNI) logs:"
     kubectl logs -n kube-system $AWS_NODE_POD --tail=50
   fi

   # Node access instructions
   echo
   echo "=== Node access instructions ==="
   echo "To access the node directly, use the following command:"
   echo "aws ssm start-session --target <instance-id>"
   echo "or"
   echo "ssh ec2-user@$NODE_IP  # SSH key and security group configuration required"

   echo
   echo "=== Troubleshooting complete ==="
   ```

2. **Terraform による self-healing node group configuration**:
   ```hcl
   # Self-healing node group
   resource "aws_eks_node_group" "self_healing" {
     cluster_name    = aws_eks_cluster.main.name
     node_group_name = "self-healing"
     node_role_arn   = aws_iam_role.node_role.arn
     subnet_ids      = var.private_subnet_ids

     scaling_config {
       desired_size = 3
       min_size     = 3
       max_size     = 6
     }

     # Self-healing settings
     update_config {
       max_unavailable = 1
     }

     # Health check settings
     health_check {
       type = "EKS"
     }

     # Auto scaling group tags
     tags = {
       "k8s.io/cluster-autoscaler/enabled" = "true"
       "k8s.io/cluster-autoscaler/${aws_eks_cluster.main.name}" = "owned"
     }
   }
   ```

3. **CloudWatch alarms と automated recovery configuration**:
   ```bash
   # Create CloudWatch alarm
   aws cloudwatch put-metric-alarm \
     --alarm-name EKS-Node-NotReady \
     --metric-name NodeNotReady \
     --namespace AWS/EKS \
     --statistic Maximum \
     --period 60 \
     --threshold 0 \
     --comparison-operator GreaterThanThreshold \
     --dimensions Name=ClusterName,Value=my-cluster \
     --evaluation-periods 3 \
     --alarm-actions arn:aws:sns:us-west-2:123456789012:eks-alerts

   # Automated recovery using AWS Lambda function
   aws lambda create-function \
     --function-name EKS-Node-Recovery \
     --runtime python3.9 \
     --role arn:aws:iam::123456789012:role/EKS-Node-Recovery-Role \
     --handler index.handler \
     --zip-file fileb://node-recovery.zip
   ```

他の選択肢の問題点:
- **A. すぐに node を終了して置き換える**: 根本原因を特定せずに node を置き換えると、新しい node でも同じ問題が発生する可能性があり、診断情報も失われます。
- **C. Cluster API server を再起動する**: API server は node status と直接関係しておらず、再起動するとクラスター全体に影響する可能性があります。
- **D. すべての pods を削除して再デプロイする**: Pods を削除しても node 自体の問題は修正されず、不要な service disruption を引き起こす可能性があります。
</details>
### 3. Amazon EKS クラスターで pod が "ImagePullBackOff" 状態の場合、最も可能性の高い原因と解決策は何ですか？

A. Pod resource limit exceeded / Resource limits を増やす
B. Image name error または authentication issue / Image name を確認し image pull secrets を設定する
C. Node disk space shortage / Disk space を解放する
D. Network policy restrictions / Network policies を修正する

<details>
<summary>解答を表示</summary>

**解答: B. Image name error または authentication issue / Image name を確認し image pull secrets を設定する**

**解説:**
Amazon EKS クラスターで pod が "ImagePullBackOff" 状態の場合、最も可能性の高い原因は image name error または authentication issue です。これを解決するには、image name を確認し、必要に応じて image pull secrets を設定する必要があります。

**主な原因と解決策:**

1. **Image name error**:
   - 不正な image name または tag
   - 存在しない image
   - Registry URL error

   **解決策**:
   ```bash
   # Check pod definition
   kubectl describe pod <pod-name>

   # Fix image name and tag
   kubectl edit deployment <deployment-name>
   # or
   kubectl set image deployment/<deployment-name> container-name=image:tag
   ```

2. **Private registry authentication issues**:
   - Authentication credentials がない
   - Credentials の期限切れ
   - Permissions 不足

   **解決策**:
   ```bash
   # Create Docker registry secret
   kubectl create secret docker-registry regcred \
     --docker-server=<registry-server> \
     --docker-username=<username> \
     --docker-password=<password> \
     --docker-email=<email>

   # Link secret to pod or service account
   kubectl patch serviceaccount default -p '{"imagePullSecrets": [{"name": "regcred"}]}'
   # or
   kubectl patch pod <pod-name> -p '{"spec":{"imagePullSecrets":[{"name":"regcred"}]}}'
   ```

3. **Amazon ECR authentication issues**:
   - ECR permissions 不足
   - Token の期限切れ
   - Cross-account access issues

   **解決策**:
   ```bash
   # Get ECR authentication token
   aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-west-2.amazonaws.com

   # Create ECR pull secret
   TOKEN=$(aws ecr get-authorization-token --output text --query 'authorizationData[].authorizationToken')
   echo $TOKEN | base64 -d | cut -d: -f2 > password.txt

   kubectl create secret docker-registry ecr-secret \
     --docker-server=123456789012.dkr.ecr.us-west-2.amazonaws.com \
     --docker-username=AWS \
     --docker-password="$(cat password.txt)" \
     --docker-email=no-reply@example.com

   rm password.txt
   ```

4. **Network connectivity issues**:
   - Registry への network access が制限されている
   - DNS resolution issues
   - Proxy configuration issues

   **解決策**:
   ```bash
   # Check registry connection from node
   ssh ec2-user@<node-ip>
   curl -v https://<registry-url>

   # Check DNS resolution
   nslookup <registry-url>

   # Configure VPC endpoint for private registry
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-12345678 \
     --service-name com.amazonaws.us-west-2.ecr.dkr \
     --vpc-endpoint-type Interface \
     --subnet-ids subnet-12345678 \
     --security-group-ids sg-12345678
   ```

**トラブルシューティング手順:**

1. **Pod status と events の確認**:
   ```bash
   # Check pod status
   kubectl get pod <pod-name>

   # Check pod details and events
   kubectl describe pod <pod-name>
   ```

2. **Image name と registry の確認**:
   ```bash
   # Check image name
   kubectl get pod <pod-name> -o jsonpath='{.spec.containers[0].image}'

   # Verify image exists
   docker pull <image-name>  # In local environment
   # or
   aws ecr describe-images \
     --repository-name <repository-name> \
     --image-ids imageTag=<tag>  # For ECR
   ```

3. **Authentication configuration の確認**:
   ```bash
   # Check service account and image pull secrets
   kubectl get serviceaccount default -o yaml

   # Check secret contents
   kubectl get secret <secret-name> -o yaml
   ```

4. **一時的な回避策の適用**:
   ```bash
   # Pull image locally and transfer to node (for emergencies)
   docker pull <image-name>
   docker save <image-name> -o image.tar
   scp image.tar ec2-user@<node-ip>:~/
   ssh ec2-user@<node-ip> "docker load -i image.tar"
   ```

**ベストプラクティス:**

1. **Image tag management**:
   - 特定の tags の代わりに digests を使用する
   - `latest` tag の使用を避ける
   - Version management strategy を実装する

2. **Image pull secret management**:
   - Secrets を service accounts にリンクする
   - 定期的な secret renewal
   - Secret management を自動化する

3. **Image registry accessibility の確保**:
   - Private registries 用の VPC endpoints を設定する
   - Network policies と security groups を設定する
   - Image caching を検討する

4. **ECR 使用時のベストプラクティス**:
   - IAM role-based authentication を使用する
   - Automatic token renewal を実装する
   - Image scanning と lifecycle policies を設定する

他の選択肢の問題点:
- **A. Pod resource limit exceeded / Resource limits を増やす**: Resource limit issues は通常、"OOMKilled" または "Pending" 状態を引き起こし、"ImagePullBackOff" ではありません。
- **C. Node disk space shortage / Disk space を解放する**: Disk space shortage が "ImagePullBackOff" の原因になることはありますが、disk space 関連のエラーは通常 node events に表示され、最も一般的な原因ではありません。
- **D. Network policy restrictions / Network policies を修正する**: Network policies は pods 間の通信に影響しますが、通常 image pull issues の主な原因ではありません。
</details>
### 4. Amazon EKS クラスターで service が pods に traffic を routing していない場合、最も効果的なトラブルシューティング手順は何ですか？

A. すぐに新しい service を作成する
B. Service と pod labels、endpoints、network policies を確認する
C. すべての pods を再起動する
D. Cluster API server を再起動する

<details>
<summary>解答を表示</summary>

**解答: B. Service と pod labels、endpoints、network policies を確認する**

**解説:**
Amazon EKS クラスターで service が pods に traffic を routing していない場合、最も効果的なトラブルシューティング手順は service と pod labels、endpoints、network policies を確認することです。この体系的なアプローチにより、service discovery と traffic routing issues の根本原因を特定できます。

**確認すべき主な項目:**

1. **Service と pod labels の確認**:
   - Service selector と pod label の一致
   - Label syntax と typos
   - Namespace の確認

2. **Endpoints の確認**:
   - Service endpoint creation
   - Endpoint IP と pod IP の一致
   - Ready pods の数

3. **Network policies の確認**:
   - Traffic を制限している network policies
   - Ingress と egress rules
   - Inter-namespace communication restrictions

4. **Service と pod status の確認**:
   - Pod running と ready state
   - Service type と port configuration
   - Health check configuration

**トラブルシューティング方法:**

1. **Service と pod labels の確認**:
   ```bash
   # Check service selector
   kubectl get service <service-name> -o yaml | grep -A 5 selector

   # Check pod labels
   kubectl get pods --show-labels

   # Check pods matching selector
   kubectl get pods -l key=value
   ```

2. **Endpoints の確認**:
   ```bash
   # Check service endpoints
   kubectl get endpoints <service-name>

   # Check endpoint details
   kubectl describe endpoints <service-name>

   # Compare endpoint and pod IPs
   kubectl get pods -o wide
   ```

3. **Network policies の確認**:
   ```bash
   # Check network policies
   kubectl get networkpolicy

   # Check network policy details
   kubectl describe networkpolicy <policy-name>

   # Temporarily disable network policy
   kubectl delete networkpolicy <policy-name>
   ```

4. **Service connectivity のテスト**:
   ```bash
   # Create temporary debug pod
   kubectl run -it --rm debug --image=nicolaka/netshoot -- bash

   # Test service DNS resolution
   nslookup <service-name>.<namespace>.svc.cluster.local

   # Test service connectivity
   curl <service-ip>:<port>

   # Test direct pod connectivity
   curl <pod-ip>:<container-port>
   ```

**一般的な service issues と解決策:**

1. **Label mismatch**:
   - **症状**: Service endpoints が空である
   - **解決策**:
     ```bash
     # Modify service selector
     kubectl edit service <service-name>
     # or
     kubectl patch service <service-name> -p '{"spec":{"selector":{"app":"correct-label"}}}'

     # Modify pod labels
     kubectl label pods <pod-name> app=correct-label --overwrite
     ```

2. **Port configuration error**:
   - **症状**: Service は接続されるが application response がない
   - **解決策**:
     ```bash
     # Check service port configuration
     kubectl describe service <service-name>

     # Check pod container port
     kubectl describe pod <pod-name>

     # Modify service port
     kubectl edit service <service-name>
     ```

3. **Network policy restrictions**:
   - **症状**: 特定の sources からのみ service にアクセスできない
   - **解決策**:
     ```bash
     # Modify network policy
     kubectl edit networkpolicy <policy-name>

     # Add allow rule
     kubectl apply -f - <<EOF
     apiVersion: networking.k8s.io/v1
     kind: NetworkPolicy
     metadata:
       name: allow-service-access
       namespace: <namespace>
     spec:
       podSelector:
         matchLabels:
           app: <app-label>
       ingress:
       - from:
         - namespaceSelector: {}
       policyTypes:
       - Ingress
     EOF
     ```

4. **CoreDNS issues**:
   - **症状**: Service name resolution が失敗する
   - **解決策**:
     ```bash
     # Check CoreDNS pods
     kubectl get pods -n kube-system -l k8s-app=kube-dns

     # Check CoreDNS logs
     kubectl logs -n kube-system -l k8s-app=kube-dns

     # Check CoreDNS configuration
     kubectl get configmap -n kube-system coredns -o yaml
     ```

**ベストプラクティス:**

1. **体系的なトラブルシューティングアプローチ**:
   - Service configuration から始め、pods、network policies、DNS の順に確認する
   - 各ステップで明確な証拠を収集する
   - 一度に 1 つの変数だけを変更する

2. **Service debugging tools の活用**:
   ```bash
   # Check kube-proxy logs
   kubectl logs -n kube-system -l k8s-app=kube-proxy

   # Check iptables rules (for self-managed nodes)
   ssh ec2-user@<node-ip>
   sudo iptables-save | grep <service-ip>

   # DNS debugging
   kubectl run -it --rm dnsutils --image=tutum/dnsutils -- bash
   ```

3. **Service monitoring の実装**:
   - Service endpoint status を監視する
   - Service connectivity status を検証する
   - Traffic flow を可視化する

4. **Service configuration management**:
   - 一貫した labeling strategy
   - 明示的な port naming
   - Services の文書化

他の選択肢の問題点:
- **A. すぐに新しい service を作成する**: 根本原因を特定せずに新しい service を作成すると、同じ問題が発生する可能性があり、診断情報も失われます。
- **C. すべての pods を再起動する**: Pods の再起動では service configuration issues は修正されず、不要な service disruption を引き起こす可能性があります。
- **D. Cluster API server を再起動する**: API server の再起動は極端な対応であり、service routing issues とは直接関係ありません。クラスター全体にも影響する可能性があります。
</details>
### 5. Amazon EKS クラスターで PersistentVolumeClaim が "Pending" 状態のままになる場合、最も可能性の高い原因と解決策は何ですか？

A. Node resource shortage / より大きな nodes を追加する
B. Storage class issue または volume provisioning permissions 不足 / Storage class を確認し IAM permissions を設定する
C. Pod priority が低い / Pod priority を上げる
D. Cluster autoscaler が無効 / Autoscaler を有効にする

<details>
<summary>解答を表示</summary>

**解答: B. Storage class issue または volume provisioning permissions 不足 / Storage class を確認し IAM permissions を設定する**

**解説:**
Amazon EKS クラスターで PersistentVolumeClaim (PVC) が "Pending" 状態のままになる場合、最も可能性の高い原因は storage class issue または volume provisioning permissions 不足です。これを解決するには、storage class を確認し、必要な IAM permissions を設定する必要があります。

**主な原因と解決策:**

1. **Storage class issues**:
   - 存在しない storage class を指定している
   - Storage class parameter errors
   - Provisioner configuration issues

   **解決策**:
   ```bash
   # Check storage classes
   kubectl get storageclass

   # Check storage class details
   kubectl describe storageclass <storage-class-name>

   # Set default storage class
   kubectl patch storageclass <storage-class-name> -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
   ```

2. **IAM permissions 不足**:
   - EBS CSI driver service account に permissions がない
   - Node IAM role に permissions がない
   - Cross-account access issues

   **解決策**:
   ```bash
   # Check EBS CSI driver service account
   kubectl get serviceaccount -n kube-system ebs-csi-controller-sa

   # Check IAM role attachment
   kubectl describe serviceaccount -n kube-system ebs-csi-controller-sa

   # Attach required IAM policy
   aws iam attach-role-policy \
     --role-name <role-name> \
     --policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy
   ```

3. **Volume binding mode issues**:
   - Availability zone mismatch
   - WaitForFirstConsumer setting issues
   - Topology constraints

   **解決策**:
   ```bash
   # Check volume binding mode
   kubectl get storageclass <storage-class-name> -o jsonpath='{.volumeBindingMode}'

   # Modify storage class
   kubectl patch storageclass <storage-class-name> -p '{"volumeBindingMode":"WaitForFirstConsumer"}'

   # Create new storage class
   kubectl apply -f - <<EOF
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: ebs-sc-waitforfirstconsumer
   provisioner: ebs.csi.aws.com
   volumeBindingMode: WaitForFirstConsumer
   parameters:
     type: gp3
   EOF
   ```

4. **CSI driver issues**:
   - CSI driver がインストールされていない、またはエラーがある
   - Version compatibility issues
   - Controller pod errors

   **解決策**:
   ```bash
   # Check CSI driver pods
   kubectl get pods -n kube-system -l app=ebs-csi-controller

   # Check CSI driver logs
   kubectl logs -n kube-system -l app=ebs-csi-controller -c ebs-plugin

   # Reinstall CSI driver
   eksctl create addon --name aws-ebs-csi-driver --cluster <cluster-name> --force
   ```

**ベストプラクティス:**

1. **適切な storage class configuration**:
   ```yaml
   # gp3 storage class example
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: ebs-gp3
     annotations:
       storageclass.kubernetes.io/is-default-class: "true"
   provisioner: ebs.csi.aws.com
   volumeBindingMode: WaitForFirstConsumer
   parameters:
     type: gp3
     encrypted: "true"
   allowVolumeExpansion: true
   ```

2. **IRSA (IAM Roles for Service Accounts) configuration**:
   ```bash
   # Create IRSA for EBS CSI driver
   eksctl create iamserviceaccount \
     --name ebs-csi-controller-sa \
     --namespace kube-system \
     --cluster <cluster-name> \
     --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy \
     --approve \
     --override-existing-serviceaccounts
   ```

3. **最適化された PVC request**:
   ```yaml
   # Optimized PVC example
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: my-pvc
   spec:
     accessModes:
       - ReadWriteOnce
     storageClassName: ebs-gp3
     resources:
       requests:
         storage: 10Gi
   ```

4. **Volume binding mode optimization**:
   - WaitForFirstConsumer を使用する
   - Pod と PV の availability zone が一致していることを確認する
   - Topology-aware provisioning を活用する

他の選択肢の問題点:
- **A. Node resource shortage / より大きな nodes を追加する**: Node resource shortage は通常 pods が "Pending" 状態になる原因ですが、PVC が "Pending" 状態になることとは直接関係しません。
- **C. Pod priority が低い / Pod priority を上げる**: Pod priority は scheduling decisions に影響しますが、PVC provisioning には影響しません。
- **D. Cluster autoscaler が無効 / Autoscaler を有効にする**: Autoscaler は nodes の数を調整するのに役立ちますが、PVC provisioning issues とは直接関係しません。
</details>
### 6. Amazon EKS クラスターで autoscaling が期待どおりに動作しない場合、最も効果的なトラブルシューティングアプローチは何ですか？

A. すべての pods により多くの resources を割り当てる
B. 手動で nodes を追加する
C. HPA、CA、VPA configuration、metrics、permissions、events を確認する
D. クラスターを再作成する

<details>
<summary>解答を表示</summary>

**解答: C. HPA、CA、VPA configuration、metrics、permissions、events を確認する**

**解説:**
Amazon EKS クラスターで autoscaling が期待どおりに動作しない場合、最も効果的なトラブルシューティングアプローチは HPA (Horizontal Pod Autoscaler)、CA (Cluster Autoscaler)、VPA (Vertical Pod Autoscaler) configuration、metrics、permissions、events を確認することです。この体系的なアプローチにより、autoscaling issues の根本原因を特定し解決できます。

**確認すべき主な項目:**

1. **HPA (Horizontal Pod Autoscaler) の確認**:
   - HPA configuration と status
   - Metrics availability と values
   - Scaling limits と behavior

2. **CA (Cluster Autoscaler) の確認**:
   - CA deployment と configuration
   - IAM permissions と roles
   - Node group tags と settings

3. **VPA (Vertical Pod Autoscaler) の確認**:
   - VPA configuration と mode
   - Resource recommendations
   - Update policies

4. **Metrics と events の確認**:
   - Metrics server status
   - CloudWatch metrics availability
   - Autoscaling events と logs

**トラブルシューティング方法:**

1. **HPA troubleshooting**:
   ```bash
   # Check HPA status
   kubectl get hpa

   # Check HPA details
   kubectl describe hpa <hpa-name>

   # Check metrics
   kubectl get --raw "/apis/metrics.k8s.io/v1beta1/namespaces/<namespace>/pods"

   # Check metrics server status
   kubectl get pods -n kube-system -l k8s-app=metrics-server
   kubectl logs -n kube-system -l k8s-app=metrics-server
   ```

2. **CA troubleshooting**:
   ```bash
   # Check CA pod status
   kubectl get pods -n kube-system -l app=cluster-autoscaler

   # Check CA logs
   kubectl logs -n kube-system -l app=cluster-autoscaler

   # Check node group tags
   aws autoscaling describe-auto-scaling-groups \
     --auto-scaling-group-names <asg-name> \
     --query "AutoScalingGroups[].Tags"

   # Check CA events
   kubectl get events --sort-by='.lastTimestamp' | grep -i "cluster-autoscaler"
   ```

3. **VPA troubleshooting**:
   ```bash
   # Check VPA status
   kubectl get vpa

   # Check VPA details
   kubectl describe vpa <vpa-name>

   # Check VPA recommendations
   kubectl get vpa <vpa-name> -o jsonpath='{.status.recommendation}'

   # Check VPA component status
   kubectl get pods -n kube-system -l app=vpa-recommender
   ```

4. **Metrics と permissions のトラブルシューティング**:
   ```bash
   # Check metrics server status
   kubectl get apiservices v1beta1.metrics.k8s.io

   # Check IAM roles and policies
   aws iam get-role --role-name <role-name>
   aws iam list-attached-role-policies --role-name <role-name>

   # Check CloudWatch metrics
   aws cloudwatch list-metrics \
     --namespace AWS/EC2 \
     --metric-name CPUUtilization \
     --dimensions Name=AutoScalingGroupName,Value=<asg-name>
   ```

**一般的な autoscaling issues と解決策:**

1. **HPA metrics issues**:
   - **症状**: HPA が scaling decisions を行わない
   - **原因**: Metrics server error または metrics availability issue
   - **解決策**:
     ```bash
     # Reinstall metrics server
     kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

     # Verify metrics
     kubectl top pods
     kubectl top nodes
     ```

2. **CA permission issues**:
   - **症状**: CA が nodes を追加しない
   - **原因**: IAM permissions 不足、または ASG tags がない
   - **解決策**:
     ```bash
     # Attach CA IAM policy
     aws iam attach-role-policy \
       --role-name <role-name> \
       --policy-arn arn:aws:iam::aws:policy/AutoScalingFullAccess

     # Add ASG tags
     aws autoscaling create-or-update-tags \
       --tags "ResourceId=<asg-name>,ResourceType=auto-scaling-group,Key=k8s.io/cluster-autoscaler/enabled,Value=true,PropagateAtLaunch=true" \
       "ResourceId=<asg-name>,ResourceType=auto-scaling-group,Key=k8s.io/cluster-autoscaler/<cluster-name>,Value=owned,PropagateAtLaunch=true"
     ```

3. **Scaling limit issues**:
   - **症状**: Scaling が特定の値を超えない
   - **原因**: HPA または CA limit settings
   - **解決策**:
     ```bash
     # Modify HPA max replicas
     kubectl patch hpa <hpa-name> -p '{"spec":{"maxReplicas":20}}'

     # Modify ASG max size
     aws autoscaling update-auto-scaling-group \
       --auto-scaling-group-name <asg-name> \
       --max-size 10
     ```

4. **VPA update mode issues**:
   - **症状**: VPA が resources を更新しない
   - **原因**: Update mode が "Off" または "Initial" に設定されている
   - **解決策**:
     ```bash
     # Modify VPA update mode
     kubectl patch vpa <vpa-name> -p '{"spec":{"updatePolicy":{"updateMode":"Auto"}}}'
     ```

**ベストプラクティス:**

1. **体系的なトラブルシューティングアプローチ**:
   - 各 autoscaling component を個別に確認する
   - Logs と events を分析する
   - 段階的なトラブルシューティング

2. **Autoscaling monitoring の実装**:
   - Autoscaling activity を監視する
   - Scaling event notifications を設定する
   - Scaling metrics dashboard を設定する

3. **Autoscaling configuration の最適化**:
   - Workload characteristics に適した scaling thresholds を設定する
   - Scaling behavior と cooldown periods を調整する
   - Cost と performance のバランスを取る

4. **複数 autoscaling components の統合**:
   - HPA、CA、VPA の組み合わせを使用する
   - Components 間の conflict を防ぐ
   - 一貫した scaling strategy を実装する

他の選択肢の問題点:
- **A. すべての pods により多くの resources を割り当てる**: これは根本原因を解決せず、resources を浪費し、autoscaling issues の実際の原因を特定できません。
- **B. 手動で nodes を追加する**: これは一時的な解決策にすぎず、autoscaling system の根本的な問題を解決しません。
- **D. クラスターを再作成する**: これは根本原因を特定しない極端な対応であり、不要な downtime と作業を発生させます。
</details>
### 7. Amazon EKS クラスターで network policies が期待どおりに動作しない場合、最も効果的なトラブルシューティングアプローチは何ですか？

A. すべての network policies を削除して defaults を使用する
B. Cluster CNI plugin、network policy configuration、logs、events を確認する
C. すべての pods に hostNetwork: true を設定する
D. Cluster VPC を再設定する

<details>
<summary>解答を表示</summary>

**解答: B. Cluster CNI plugin、network policy configuration、logs、events を確認する**

**解説:**
Amazon EKS クラスターで network policies が期待どおりに動作しない場合、最も効果的なトラブルシューティングアプローチは cluster CNI plugin、network policy configuration、logs、events を体系的に確認することです。このアプローチにより、network policy issues の根本原因を特定し解決できます。

**確認すべき主な項目:**

1. **CNI plugin の確認**:
   - 使用中の CNI plugin の種類（AWS VPC CNI、Calico、Cilium など）
   - CNI plugin version と compatibility
   - Network policy support

2. **Network policy configuration の確認**:
   - Network policy syntax と selectors
   - Policy priority と conflicts
   - Namespace と label selectors

3. **Logs と events の確認**:
   - CNI plugin logs
   - Network policy controller logs
   - 関連 events と error messages

4. **Network connectivity のテスト**:
   - Pod-to-pod connectivity test
   - Service connectivity test
   - External connectivity test

**トラブルシューティング方法:**

1. **CNI plugin の確認**:
   ```bash
   # Check CNI plugin pods
   kubectl get pods -n kube-system -l k8s-app=aws-node  # AWS VPC CNI
   kubectl get pods -n kube-system -l k8s-app=calico-node  # Calico
   kubectl get pods -n kube-system -l k8s-app=cilium  # Cilium

   # Check CNI plugin logs
   kubectl logs -n kube-system -l k8s-app=aws-node
   kubectl logs -n kube-system -l k8s-app=calico-node
   kubectl logs -n kube-system -l k8s-app=cilium

   # Check CNI configuration
   kubectl describe daemonset -n kube-system aws-node
   kubectl describe daemonset -n kube-system calico-node
   kubectl describe daemonset -n kube-system cilium
   ```

2. **Network policies の確認**:
   ```bash
   # List network policies
   kubectl get networkpolicies --all-namespaces

   # Check specific network policy details
   kubectl describe networkpolicy <policy-name> -n <namespace>

   # Check network policy YAML
   kubectl get networkpolicy <policy-name> -n <namespace> -o yaml
   ```

3. **Pod network information の確認**:
   ```bash
   # Check pod IP and node information
   kubectl get pods -o wide

   # Check pod network interface
   kubectl exec -it <pod-name> -- ip addr

   # Check pod routing table
   kubectl exec -it <pod-name> -- ip route
   ```

4. **Network connectivity のテスト**:
   ```bash
   # Create debug pod
   kubectl run network-debug --rm -it --image=nicolaka/netshoot -- /bin/bash

   # Test pod-to-pod connectivity
   ping <target-pod-ip>
   nc -zv <target-pod-ip> <port>

   # Test DNS resolution
   nslookup <service-name>.<namespace>.svc.cluster.local

   # Packet capture
   tcpdump -i eth0 -n
   ```

**一般的な network policy issues と解決策:**

1. **CNI plugin compatibility issues**:
   - **症状**: Network policies が適用されない
   - **原因**: 使用中の CNI plugin が network policies をサポートしていない
   - **解決策**:
     ```bash
     # Add Calico policy engine to AWS VPC CNI
     kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
     kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml

     # Or switch to Cilium
     helm repo add cilium https://helm.cilium.io/
     helm install cilium cilium/cilium --namespace kube-system
     ```

2. **Network policy selector issues**:
   - **症状**: Policies が期待した pods に適用されない
   - **原因**: 不正な label selector または namespace selector
   - **解決策**:
     ```bash
     # Check pod labels
     kubectl get pods --show-labels

     # Modify network policy
     kubectl edit networkpolicy <policy-name> -n <namespace>
     ```

3. **Policy conflict issues**:
   - **症状**: 予期しない connection blocking または allowing
   - **原因**: 複数 policies 間の conflicts または priority issues
   - **解決策**:
     ```bash
     # Review all network policies
     kubectl get networkpolicies --all-namespaces -o yaml

     # Simplify or reconfigure policies
     kubectl apply -f updated-network-policy.yaml
     ```

4. **CNI plugin bugs または configuration errors**:
   - **症状**: 断続的な connection issues または一貫しない動作
   - **原因**: CNI plugin bugs または不正な configuration
   - **解決策**:
     ```bash
     # Update CNI plugin
     kubectl set image daemonset/aws-node -n kube-system aws-node=<new-image-version>

     # Check and modify CNI configuration
     kubectl edit configmap -n kube-system aws-node
     ```

**ベストプラクティス:**

1. **体系的な network policy design**:
   - Default deny policy から開始する
   - 必要な connections のみを明示的に許可する
   - Namespace と label-based policies を使用する

2. **Network policies のテストと検証**:
   - Policies を適用する前にテストする
   - Connectivity testing を自動化する
   - 段階的な policy rollout

3. **Network monitoring と logging**:
   - Network traffic を監視する
   - Connection denials を log に記録する
   - Network performance を監視する

4. **CNI plugin selection と configuration**:
   - Workload requirements に適した CNI を選択する
   - 最新状態を維持する
   - 適切な resources を割り当てる

他の選択肢の問題点:
- **A. すべての network policies を削除して defaults を使用する**: これは security risks を生み、必要な network isolation を削除し、根本原因を解決しません。
- **C. すべての pods に hostNetwork: true を設定する**: これは network policies を迂回し、security risks を生み、pods 間の isolation を削除します。
- **D. Cluster VPC を再設定する**: これは極端な対応であり、ほとんどの network policy issues は VPC レベルではなく、クラスター内の CNI と policy configuration に関連しています。
</details>
### 8. Amazon EKS クラスターで Helm chart deployment issues をトラブルシューティングする最も効果的なアプローチは何ですか？

A. すべての Helm charts を削除して再インストールする
B. クラスターを再作成する
C. Helm version、chart configuration、dependencies、permissions、logs を体系的に確認する
D. すべての resources を手動でデプロイする

<details>
<summary>解答を表示</summary>

**解答: C. Helm version、chart configuration、dependencies、permissions、logs を体系的に確認する**

**解説:**
Amazon EKS クラスターで Helm chart deployment issues をトラブルシューティングする最も効果的なアプローチは、Helm version、chart configuration、dependencies、permissions、logs を体系的に確認することです。このアプローチにより、Helm deployment issues の根本原因を特定し解決できます。

**確認すべき主な項目:**

1. **Helm version と compatibility の確認**:
   - Helm client と Tiller (Helm 2) version
   - Kubernetes API version compatibility
   - EKS version compatibility

2. **Chart configuration と values の確認**:
   - Chart syntax errors
   - Values file configuration
   - Template rendering issues

3. **Dependencies と repositories の確認**:
   - Chart dependency availability
   - Repository accessibility
   - Chart version compatibility

4. **Permissions と RBAC の確認**:
   - Service account permissions
   - RBAC rules
   - Namespace access

5. **Logs と events の確認**:
   - Helm debug logs
   - Kubernetes events
   - 関連 pod logs

**トラブルシューティング方法:**

1. **Helm version と configuration の確認**:
   ```bash
   # Check Helm version
   helm version

   # Check Helm environment variables
   env | grep HELM

   # Check Helm plugins
   helm plugin list

   # Check Helm repositories
   helm repo list
   helm repo update
   ```

2. **Charts の検証と debug**:
   ```bash
   # Validate chart syntax
   helm lint ./my-chart

   # Check template rendering
   helm template ./my-chart --debug

   # Update chart dependencies
   helm dependency update ./my-chart

   # Install with debug mode
   helm install my-release ./my-chart --debug
   ```

3. **Release status と history の確認**:
   ```bash
   # List releases
   helm list -A

   # Include failed releases
   helm list -A --failed

   # Check release status
   helm status my-release

   # Check release history
   helm history my-release

   # Check release details
   helm get all my-release
   ```

4. **Resources と events の確認**:
   ```bash
   # Check deployed resources
   kubectl get all -n <namespace> -l app.kubernetes.io/instance=my-release

   # Check events
   kubectl get events -n <namespace> --sort-by='.lastTimestamp'

   # Check pod logs
   kubectl logs -n <namespace> -l app.kubernetes.io/instance=my-release

   # Check pod status
   kubectl describe pods -n <namespace> -l app.kubernetes.io/instance=my-release
   ```

5. **Permissions と RBAC の確認**:
   ```bash
   # Check service accounts
   kubectl get serviceaccount -n <namespace>

   # Check roles and role bindings
   kubectl get roles,rolebindings -n <namespace>

   # Check cluster roles and bindings
   kubectl get clusterroles,clusterrolebindings -l app.kubernetes.io/instance=my-release

   # Check service account permissions
   kubectl auth can-i --list --as=system:serviceaccount:<namespace>:<serviceaccount>
   ```

**一般的な Helm deployment issues と解決策:**

1. **Chart syntax errors**:
   - **症状**: `helm install` または `helm template` command が失敗する
   - **原因**: YAML syntax errors、不正な template functions または variables
   - **解決策**:
     ```bash
     # Validate chart syntax
     helm lint ./my-chart

     # Check template rendering
     helm template ./my-chart --debug

     # Render template with specific values
     helm template ./my-chart --set key=value --debug
     ```

2. **Dependency issues**:
   - **症状**: Chart installation 中に dependency errors が発生する
   - **原因**: Missing dependencies、version mismatches、または repository access issues
   - **解決策**:
     ```bash
     # Update dependencies
     helm dependency update ./my-chart

     # Add and update repository
     helm repo add bitnami https://charts.bitnami.com/bitnami
     helm repo update

     # Build dependencies
     helm dependency build ./my-chart
     ```

3. **Permission issues**:
   - **症状**: Permission denied errors
   - **原因**: RBAC permissions 不足、または不正な service account configuration
   - **解決策**:
     ```bash
     # Create required RBAC resources
     kubectl apply -f rbac.yaml

     # Specify service account
     helm install my-release ./my-chart --service-account=my-service-account

     # Check permissions
     kubectl auth can-i create deployments --as=system:serviceaccount:<namespace>:<serviceaccount>
     ```

4. **Resource conflicts**:
   - **症状**: Resource already exists error
   - **原因**: 以前の installation の resources が残っている、または name conflicts
   - **解決策**:
     ```bash
     # Remove existing release
     helm uninstall my-release

     # Check and delete remaining resources
     kubectl get all -n <namespace> -l app.kubernetes.io/instance=my-release
     kubectl delete <resource-type> <resource-name> -n <namespace>

     # Install with different release name
     helm install new-release ./my-chart
     ```

5. **Values configuration issues**:
   - **症状**: デプロイされた application が期待どおりに動作しない
   - **原因**: 不正な configuration values、または必要な values の不足
   - **解決策**:
     ```bash
     # Check current values
     helm get values my-release

     # Check default values
     helm show values ./my-chart

     # Upgrade with values file
     helm upgrade my-release ./my-chart -f values.yaml

     # Set specific values
     helm upgrade my-release ./my-chart --set key=value
     ```

**ベストプラクティス:**

1. **体系的なトラブルシューティングアプローチ**:
   - 段階的な verification と validation
   - Log と event analysis
   - Symptom から cause まで追跡する

2. **Helm charts のテストと検証**:
   - Deployment 前に charts を検証する
   - まず test environment でテストする
   - CI/CD pipeline に validation steps を含める

3. **Version management と compatibility**:
   - 互換性のある Helm と Kubernetes versions を使用する
   - Chart versions を明示的に指定する
   - Dependency versions を固定する

4. **Documentation と values management**:
   - Chart values を文書化する
   - Environment-specific values files を管理する
   - Sensitive values に security practices を適用する

他の選択肢の問題点:
- **A. すべての Helm charts を削除して再インストールする**: これは data loss を引き起こす可能性のある極端な対応であり、根本原因を解決しません。
- **B. クラスターを再作成する**: これは非常に極端な対応であり、ほとんどの Helm deployment issues は cluster-level issues ではなく chart configuration または permissions に関連しています。
- **D. すべての resources を手動でデプロイする**: これは Helm の利点を放棄するものであり、complex applications ではエラーが起きやすく管理が困難です。
</details>
### 9. Amazon EKS クラスターで memory leak issues をトラブルシューティングする最も効果的なアプローチは何ですか？

A. すべての pods を再起動する
B. Cluster node size を増やす
C. Memory usage を profile し、container limits を review し、application code を analyze する
D. さらに nodes を追加する

<details>
<summary>解答を表示</summary>

**解答: C. Memory usage を profile し、container limits を review し、application code を analyze する**

**解説:**
Amazon EKS クラスターで memory leak issues をトラブルシューティングする最も効果的なアプローチは、memory usage profiling、container limits review、application code analysis を含む体系的なアプローチです。この方法により、memory leaks の根本原因を特定し解決できます。

**確認すべき主な項目:**

1. **Memory usage profiling**:
   - Pod と node レベルで memory usage を監視する
   - 時系列で memory usage patterns を分析する
   - Memory leaks の兆候を特定する

2. **Container limits の review**:
   - Memory request と limit settings を確認する
   - Container OOM (Out of Memory) events を分析する
   - Resource allocation を最適化する

3. **Application code analysis**:
   - Application 内部の memory usage patterns を review する
   - 潜在的な memory leaks がある code を特定する
   - Application profiling tools を使用する

4. **System components の review**:
   - kubelet memory management settings
   - Node system resource usage
   - Cluster component status

**トラブルシューティング方法:**

1. **Memory usage の監視と分析**:
   ```bash
   # Check node memory usage
   kubectl top nodes

   # Check pod memory usage
   kubectl top pods -A

   # Check pod memory usage in specific namespace
   kubectl top pods -n <namespace>

   # Check memory usage per container
   kubectl top pods -n <namespace> --containers

   # Identify pods with high memory usage
   kubectl top pods -A --sort-by=memory
   ```

2. **Container limits と OOM events の確認**:
   ```bash
   # Check pod memory limits
   kubectl get pods -n <namespace> -o jsonpath='{.items[*].spec.containers[*].resources}'

   # Check pod details
   kubectl describe pod <pod-name> -n <namespace>

   # Check OOM events
   kubectl get events -n <namespace> --sort-by='.lastTimestamp' | grep -i "OOMKilled"

   # Check node OOM events
   kubectl get events --field-selector involvedObject.kind=Node --sort-by='.lastTimestamp' | grep -i "memory"
   ```

3. **Application logs と profiling**:
   ```bash
   # Check application logs
   kubectl logs <pod-name> -n <namespace>

   # Check previous pod logs
   kubectl logs <pod-name> -n <namespace> --previous

   # Run application profiling tool
   kubectl exec -it <pod-name> -n <namespace> -- <profiling-command>

   # Generate memory dump
   kubectl exec -it <pod-name> -n <namespace> -- <memory-dump-command>
   ```

4. **Node と system resources の確認**:
   ```bash
   # Check node details
   kubectl describe node <node-name>

   # Check node memory pressure
   kubectl get nodes -o jsonpath='{.items[*].status.conditions[?(@.type=="MemoryPressure")]}'

   # Check kubelet logs
   kubectl logs -n kube-system <kubelet-pod-name>

   # Check system memory statistics
   kubectl debug node/<node-name> -it --image=busybox -- sh -c "cat /proc/meminfo"
   ```

**一般的な memory leak issues と解決策:**

1. **Application memory leaks**:
   - **症状**: Memory usage が時間とともに継続的に増加する
   - **原因**: Application code 内の memory leaks、cache management 不足
   - **解決策**:
     - Application code を review して修正する
     - Memory profiling tools を使用する
     - 定期的な garbage collection を設定する
     - Cache size limits と expiration policies を実装する

2. **Container memory limit issues**:
   - **症状**: 頻繁な OOM terminations、pod restarts
   - **原因**: 不適切な memory limit settings、resource requests と limits の差が大きい
   - **解決策**:
     ```yaml
     # Set appropriate memory requests and limits
     apiVersion: v1
     kind: Pod
     metadata:
       name: memory-optimized-pod
     spec:
       containers:
       - name: app
         image: app-image
         resources:
           requests:
             memory: "256Mi"
           limits:
             memory: "512Mi"
     ```

3. **System component memory issues**:
   - **症状**: Node instability、kubelet または他の system components による高い memory usage
   - **原因**: kubelet configuration issues、system component bugs
   - **解決策**:
     - kubelet configuration を最適化する
     - System components を更新する
     - Node resource reservations を調整する

4. **Memory fragmentation issues**:
   - **症状**: 十分な total available memory があるにもかかわらず OOM が発生する
   - **原因**: Memory fragmentation、large page allocation failures
   - **解決策**:
     - 定期的な node reboots をスケジュールする
     - High memory pressure の workloads を分散する
     - Node memory overcommit を減らす

**ベストプラクティス:**

1. **体系的な memory monitoring**:
   - Cluster、node、pod levels で memory を監視する
   - 時系列で memory usage patterns を追跡する
   - Anomalies に対する alerts を設定する

2. **適切な resource limits の設定**:
   - Workload characteristics に適した memory requests と limits を設定する
   - Memory requests と limits の適切な ratio を維持する
   - 定期的な resource usage review と adjustment

3. **Application optimization**:
   - Memory-efficient code を書く
   - 定期的な memory profiling と optimization
   - 適切な caching strategies を実装する

4. **Cluster configuration optimization**:
   - Node memory reservations を最適化する
   - 適切な kubelet memory management settings
   - Workload distribution と isolation

他の選択肢の問題点:
- **A. すべての pods を再起動する**: これは一時的な解決策にすぎず、memory leaks の根本原因を解決しません。Pods が再起動すると問題は再発します。
- **B. Cluster node size を増やす**: これは根本原因を解決せず、症状を隠すだけです。Memory leaks が続けば、より大きな nodes でも最終的に memory が不足します。
- **D. さらに nodes を追加する**: B と同様に、これは根本原因を解決せずに症状を隠すだけです。Memory leak issues は nodes の数に関係なく続きます。
</details>
### 10. Amazon EKS クラスターで DNS resolution issues をトラブルシューティングする最も効果的なアプローチは何ですか？

A. すべての pods に static IPs を割り当てる
B. CoreDNS configuration、network policies、DNS policies、connectivity を体系的に確認する
C. すべての services に ExternalName を使用する
D. Cluster VPC を再設定する

<details>
<summary>解答を表示</summary>

**解答: B. CoreDNS configuration、network policies、DNS policies、connectivity を体系的に確認する**

**解説:**
Amazon EKS クラスターで DNS resolution issues をトラブルシューティングする最も効果的なアプローチは、CoreDNS configuration、network policies、DNS policies、connectivity を体系的に確認することです。このアプローチにより、DNS issues の根本原因を特定し解決できます。

**確認すべき主な項目:**

1. **CoreDNS configuration と status の確認**:
   - CoreDNS pod status と logs
   - CoreDNS ConfigMap configuration
   - CoreDNS service と endpoints

2. **Network policies と connectivity の確認**:
   - DNS ports (53/UDP, 53/TCP) 用の network policies
   - Pods と CoreDNS 間の network connectivity
   - VPC DNS settings

3. **DNS policies と configuration の確認**:
   - Pod DNS policy settings
   - DNS configuration options
   - Host namespace settings

4. **Cluster と VPC configuration の確認**:
   - EKS cluster DNS settings
   - VPC DNS attributes
   - DHCP option sets

**トラブルシューティング方法:**

1. **CoreDNS status と configuration の確認**:
   ```bash
   # Check CoreDNS pod status
   kubectl get pods -n kube-system -l k8s-app=kube-dns

   # Check CoreDNS logs
   kubectl logs -n kube-system -l k8s-app=kube-dns

   # Check CoreDNS ConfigMap
   kubectl get configmap coredns -n kube-system -o yaml

   # Check CoreDNS service
   kubectl get service kube-dns -n kube-system

   # Check CoreDNS endpoints
   kubectl get endpoints kube-dns -n kube-system
   ```

2. **DNS resolution のテスト**:
   ```bash
   # Create debug pod
   kubectl run dns-test --rm -it --image=busybox -- sh

   # Test cluster internal DNS resolution
   nslookup kubernetes.default.svc.cluster.local

   # Test service DNS resolution
   nslookup <service-name>.<namespace>.svc.cluster.local

   # Test external domain resolution
   nslookup google.com

   # Check DNS server
   cat /etc/resolv.conf
   ```

3. **Network policies と connectivity の確認**:
   ```bash
   # Check DNS-related network policies
   kubectl get networkpolicies --all-namespaces

   # Test connection to CoreDNS
   kubectl run netcat-test --rm -it --image=busybox -- sh -c "nc -zv kube-dns.kube-system.svc.cluster.local 53"

   # Capture DNS packets
   kubectl run tcpdump-test --rm -it --image=nicolaka/netshoot -- tcpdump -i any port 53
   ```

4. **Pod DNS configuration の確認**:
   ```bash
   # Check pod DNS policy
   kubectl get pod <pod-name> -o jsonpath='{.spec.dnsPolicy}'

   # Check pod DNS configuration
   kubectl get pod <pod-name> -o jsonpath='{.spec.dnsConfig}'

   # Check pod internal resolv.conf
   kubectl exec -it <pod-name> -- cat /etc/resolv.conf
   ```

5. **VPC と cluster DNS settings の確認**:
   ```bash
   # Check VPC DNS attributes
   aws ec2 describe-vpcs --vpc-id <vpc-id> --query 'Vpcs[0].EnableDnsSupport'
   aws ec2 describe-vpcs --vpc-id <vpc-id> --query 'Vpcs[0].EnableDnsHostnames'

   # Check DHCP option set
   aws ec2 describe-vpcs --vpc-id <vpc-id> --query 'Vpcs[0].DhcpOptionsId'
   aws ec2 describe-dhcp-options --dhcp-options-id <dhcp-options-id>

   # Check node DNS configuration
   kubectl debug node/<node-name> -it --image=busybox -- cat /etc/resolv.conf
   ```

**一般的な DNS issues と解決策:**

1. **CoreDNS pod issues**:
   - **症状**: DNS queries が失敗し、CoreDNS pods が異常である
   - **原因**: CoreDNS pod crashes、resource shortage、configuration errors
   - **解決策**:
     ```bash
     # Restart CoreDNS pods
     kubectl rollout restart deployment coredns -n kube-system

     # Increase CoreDNS resources
     kubectl edit deployment coredns -n kube-system
     # Increase requests and limits in resources section

     # Check CoreDNS logs
     kubectl logs -n kube-system -l k8s-app=kube-dns
     ```

2. **Network policy issues**:
   - **症状**: 特定の namespaces または pods からのみ DNS resolution が失敗する
   - **原因**: Restrictive network policies が DNS traffic をブロックしている
   - **解決策**:
     ```yaml
     # Network policy allowing DNS traffic
     apiVersion: networking.k8s.io/v1
     kind: NetworkPolicy
     metadata:
       name: allow-dns
       namespace: <namespace>
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
     ```

3. **DNS policy と configuration issues**:
   - **症状**: 特定の種類の DNS queries のみ失敗する
   - **原因**: 不適切な DNS policy または configuration
   - **解決策**:
     ```yaml
     # Create pod with custom DNS configuration
     apiVersion: v1
     kind: Pod
     metadata:
       name: dns-custom-pod
     spec:
       containers:
       - name: app
         image: busybox
         command: ["sleep", "3600"]
       dnsPolicy: "None"
       dnsConfig:
         nameservers:
         - "169.254.20.10"  # VPC DNS server
         - "8.8.8.8"        # Backup DNS server
         searches:
         - <namespace>.svc.cluster.local
         - svc.cluster.local
         - cluster.local
         options:
         - name: ndots
           value: "5"
     ```

4. **VPC DNS settings issues**:
   - **症状**: External domain resolution が失敗する
   - **原因**: VPC DNS attributes が無効、または DHCP option set issues
   - **解決策**:
     ```bash
     # Enable VPC DNS attributes
     aws ec2 modify-vpc-attribute --vpc-id <vpc-id> --enable-dns-support
     aws ec2 modify-vpc-attribute --vpc-id <vpc-id> --enable-dns-hostnames

     # Create custom DHCP option set
     aws ec2 create-dhcp-options \
       --dhcp-configurations \
       "Key=domain-name-servers,Values=AmazonProvidedDNS" \
       "Key=domain-name,Values=<region>.compute.internal"

     # Associate DHCP option set with VPC
     aws ec2 associate-dhcp-options --dhcp-options-id <dhcp-options-id> --vpc-id <vpc-id>
     ```

5. **CoreDNS configuration issues**:
   - **症状**: 特定 domain の resolution が失敗する、または DNS resolution が遅い
   - **原因**: CoreDNS configuration errors または最適化されていない settings
   - **解決策**:
     ```yaml
     # Optimized CoreDNS ConfigMap
     apiVersion: v1
     kind: ConfigMap
     metadata:
       name: coredns
       namespace: kube-system
     data:
       Corefile: |
         .:53 {
             errors
             health {
                lameduck 5s
             }
             ready
             kubernetes cluster.local in-addr.arpa ip6.arpa {
                pods insecure
                fallthrough in-addr.arpa ip6.arpa
                ttl 30
             }
             prometheus :9153
             forward . /etc/resolv.conf {
                max_concurrent 1000
                health_check 5s
             }
             cache 30
             loop
             reload
             loadbalance
         }
     ```

**ベストプラクティス:**

1. **CoreDNS monitoring と scaling**:
   - CoreDNS performance と status を監視する
   - Cluster size に応じて CoreDNS replicas を scaling する
   - 適切な resources を割り当てる

2. **DNS caching と optimization**:
   - 適切な TTL と cache settings
   - Node-level DNS caching を実装する
   - Application-level DNS caching を検討する

3. **Network policy design**:
   - DNS traffic を明示的に許可する
   - Least privilege principle を適用する
   - Network policies をテストして検証する

4. **DNS troubleshooting tools と processes**:
   - DNS troubleshooting tools と scripts を準備する
   - 体系的な troubleshooting process を確立する
   - DNS 関連 events と logs を監視する

他の選択肢の問題点:
- **A. すべての pods に static IPs を割り当てる**: これは DNS issues を解決せず、pod IP allocation と DNS resolution は別の問題です。Pods に static IPs を割り当てることは Kubernetes の動的な性質にも反し、管理の複雑さを増します。
- **C. すべての services に ExternalName を使用する**: これは特定の use cases にのみ適しており、ほとんどの DNS issues を解決しません。ExternalName は external services の aliases を提供するために使用され、cluster internal DNS resolution issues を解決しません。
- **D. Cluster VPC を再設定する**: これは極端な対応であり、ほとんどの DNS issues は VPC レベルではなく、クラスター内の DNS configuration に関連しています。VPC reconfiguration は不要な downtime と complexity を引き起こす可能性があります。
</details>

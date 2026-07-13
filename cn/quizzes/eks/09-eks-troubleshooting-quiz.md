# Amazon EKS 故障排查测验

本测验用于检验你诊断和解决 Amazon EKS Cluster 中可能出现的各种问题的能力。

## 测验概览
- Cluster 创建和配置问题
- 网络问题
- Node 和 Pod 问题
- 存储问题
- 安全和访问问题
- 性能和可扩展性问题

## 选择题

### 1. 当 Amazon EKS Cluster 创建失败时，你应首先检查什么？

A. 检查 Cluster 名称是否唯一
B. 检查 IAM 权限、VPC 配置和服务配额
C. 在其他 Region 中重试
D. 选择更大的实例类型

<details>
<summary>显示答案</summary>

**答案：B. 检查 IAM 权限、VPC 配置和服务配额**

**解释：**
当 Amazon EKS Cluster 创建失败时，首先应检查 IAM 权限、VPC 配置和服务配额。这些因素是 Cluster 创建失败最常见的原因，系统化地检查它们可以帮助快速识别并解决问题。

**要检查的关键项：**

1. **检查 IAM 权限**：
   - 是否具备创建 Cluster 所需的 IAM 权限
   - 创建 service-linked role 的权限
   - Cluster role 和 policy 配置

2. **检查 VPC 配置**：
   - Subnet 配置（Subnet 至少分布在 2 个可用区）
   - Subnet CIDR 大小（最小 /28，推荐 /24）
   - Internet 连接（NAT gateway 或 internet gateway）
   - Security group 和 network ACL 设置

3. **检查服务配额**：
   - EKS Cluster 数量配额
   - EC2 实例配额
   - VPC 和 Subnet 配额
   - 其他相关服务配额

**故障排查方法：**

1. **解决 IAM 权限问题**：
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

2. **解决 VPC 配置问题**：
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

3. **解决服务配额问题**：
   ```bash
   # Check service quotas
   aws service-quotas list-service-quotas --service-code eks

   # Request quota increase
   aws service-quotas request-service-quota-increase \
     --service-code eks \
     --quota-code L-1194D53C \
     --desired-value 10
   ```

**常见错误消息和解决方案：**

1. **IAM 权限不足**：
   - 错误："User: arn:aws:iam::123456789012:user/myuser is not authorized to perform: eks:CreateCluster"
   - 解决方案：添加所需的 IAM 权限

2. **VPC Subnet 问题**：
   - 错误："Cannot create cluster 'my-cluster' because us-west-2a, the targeted availability zone, does not have sufficient capacity to support the cluster. Retry after some time or try other availability zones."
   - 解决方案：使用不同可用区中的 Subnet，或创建新的 Subnet

3. **超出服务配额**：
   - 错误："Account cannot create more EKS clusters in region us-west-2. Current limit is 5"
   - 解决方案：请求提高服务配额，或删除不需要的 Cluster

**最佳实践：**

1. **Cluster 创建前准备**：
   - 验证所需的 IAM 权限
   - 配置合适的 VPC 和 Subnet
   - 检查服务配额

2. **系统化故障排查方法**：
   - 分析错误消息
   - 检查 AWS CloudTrail 日志
   - 逐步验证组件

3. **自动化基础设施配置**：
   - 使用 AWS CloudFormation 或 Terraform
   - 利用 eksctl 等工具
   - 对基础设施配置进行版本控制

**实际实现示例：**

1. **使用 eksctl 排查 Cluster 创建问题**：
   ```bash
   # Create cluster in debug mode
   eksctl create cluster --name my-cluster --region us-west-2 --verbose 4

   # Check cluster creation status
   eksctl get cluster --name my-cluster --region us-west-2
   ```

2. **使用 AWS CLI 排查 Cluster 创建问题**：
   ```bash
   # Attempt cluster creation
   aws eks create-cluster \
     --name my-cluster \
     --role-arn arn:aws:iam::123456789012:role/eks-cluster-role \
     --resources-vpc-config subnetIds=subnet-12345678,subnet-87654321,securityGroupIds=sg-12345678

   # Check cluster status
   aws eks describe-cluster --name my-cluster
   ```

3. **使用 Terraform 排查 Cluster 创建问题**：
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

其他选项的问题：
- **A. 检查 Cluster 名称是否唯一**：虽然 Cluster 名称不唯一可能导致错误，但这不是最常见的失败原因。
- **C. 在其他 Region 中重试**：这是一种变通方法，无法解决根本原因，而且相同问题可能会在其他 Region 中出现。
- **D. 选择更大的实例类型**：实例类型适用于 node group，不影响 Cluster 本身的创建。
</details>
### 2. 当 Amazon EKS Cluster 中的 Node 处于 NotReady 状态时，最有效的故障排查方法是什么？

A. 立即终止并替换该 Node
B. 检查 Node 日志、资源使用情况和网络连接
C. 重启 Cluster API server
D. 删除并重新部署所有 Pod

<details>
<summary>显示答案</summary>

**答案：B. 检查 Node 日志、资源使用情况和网络连接**

**解释：**
当 Amazon EKS Cluster 中的 Node 处于 NotReady 状态时，最有效的故障排查方法是检查 Node 日志、资源使用情况和网络连接。这种系统化方法有助于识别问题的根本原因并应用合适的解决方案。

**要检查的关键项：**

1. **检查 Node 状态和事件**：
   - Node 状态详情
   - Node 相关事件
   - Node conditions

2. **分析 Node 日志**：
   - kubelet 日志
   - 系统日志
   - Container runtime 日志

3. **检查资源使用情况**：
   - CPU、内存、磁盘使用情况
   - 资源限制和 pressure
   - 系统进程状态

4. **检查网络连接**：
   - 到 control plane 的连接
   - DNS 解析
   - VPC 和 Subnet 配置

**故障排查方法：**

1. **检查 Node 状态和事件**：
   ```bash
   # Check node status
   kubectl get nodes
   kubectl describe node <node-name>

   # Check node events
   kubectl get events --field-selector involvedObject.name=<node-name>
   ```

2. **分析 Node 日志**：
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

3. **检查资源使用情况**：
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

4. **检查网络连接**：
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

**常见 NotReady 原因和解决方案：**

1. **kubelet 问题**：
   - **症状**：kubelet 服务未运行或无法连接到 API server
   - **解决方案**：
     ```bash
     # Check kubelet service status
     sudo systemctl status kubelet

     # Restart kubelet service
     sudo systemctl restart kubelet

     # Check kubelet configuration
     sudo cat /etc/kubernetes/kubelet/kubelet-config.json
     ```

2. **网络问题**：
   - **症状**：Node 无法与 control plane 通信
   - **解决方案**：
     ```bash
     # Check security groups
     aws ec2 describe-security-groups --group-ids sg-12345678

     # Check routing tables
     aws ec2 describe-route-tables --route-table-ids rtb-12345678

     # Check VPC CNI pod status
     kubectl get pods -n kube-system -l k8s-app=aws-node
     kubectl logs -n kube-system -l k8s-app=aws-node
     ```

3. **资源不足**：
   - **症状**：Node 上 CPU、内存或磁盘空间不足
   - **解决方案**：
     ```bash
     # Free up disk space
     sudo du -sh /var/log/*
     sudo journalctl --vacuum-time=1d

     # Clean up unnecessary containers and images
     docker system prune -af  # When using Docker
     ```

4. **证书问题**：
   - **症状**：证书过期或不匹配
   - **解决方案**：
     ```bash
     # Check certificates
     sudo ls -la /etc/kubernetes/pki/

     # Renew certificates (for self-managed nodes)
     sudo kubeadm alpha certs renew all

     # For managed node groups, replace nodes
     eksctl replace nodegroup --cluster=my-cluster --name=my-nodegroup
     ```

**最佳实践：**

1. **系统化故障排查方法**：
   - 识别并记录症状
   - 收集相关日志和事件
   - 系统化验证可能原因

2. **实现 Node 状态监控**：
   - 设置 CloudWatch alarms
   - 配置 Node 状态 dashboard
   - 自动化告警系统

3. **实现自动恢复机制**：
   - 配置 self-healing node group
   - Health check 和自动替换
   - 自动 drain 失败的 Node

**实际实现示例：**

1. **Node 故障排查脚本**：
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

2. **使用 Terraform 配置 self-healing node group**：
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

3. **CloudWatch alarms 和自动恢复配置**：
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

其他选项的问题：
- **A. 立即终止并替换该 Node**：在未识别根本原因的情况下替换 Node，可能会导致新 Node 出现同样问题，并且诊断信息会丢失。
- **C. 重启 Cluster API server**：API server 与 Node 状态没有直接关系，重启它可能影响整个 Cluster。
- **D. 删除并重新部署所有 Pod**：删除 Pod 无法修复 Node 本身的问题，并且可能造成不必要的服务中断。
</details>
### 3. 当 Amazon EKS Cluster 中的 Pod 处于 "ImagePullBackOff" 状态时，最可能的原因和解决方案是什么？

A. Pod 资源限制超出 / 增加资源限制
B. Image 名称错误或认证问题 / 验证 Image 名称并配置 image pull secrets
C. Node 磁盘空间不足 / 释放磁盘空间
D. Network policy 限制 / 修改 network policy

<details>
<summary>显示答案</summary>

**答案：B. Image 名称错误或认证问题 / 验证 Image 名称并配置 image pull secrets**

**解释：**
当 Amazon EKS Cluster 中的 Pod 处于 "ImagePullBackOff" 状态时，最可能的原因是 Image 名称错误或认证问题。要解决此问题，需要验证 Image 名称，并在必要时配置 image pull secrets。

**主要原因和解决方案：**

1. **Image 名称错误**：
   - Image 名称或 tag 不正确
   - Image 不存在
   - Registry URL 错误

   **解决方案**：
   ```bash
   # Check pod definition
   kubectl describe pod <pod-name>

   # Fix image name and tag
   kubectl edit deployment <deployment-name>
   # or
   kubectl set image deployment/<deployment-name> container-name=image:tag
   ```

2. **Private registry 认证问题**：
   - 缺少认证凭证
   - 凭证已过期
   - 权限不足

   **解决方案**：
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

3. **Amazon ECR 认证问题**：
   - ECR 权限不足
   - Token 已过期
   - 跨账户访问问题

   **解决方案**：
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

4. **网络连接问题**：
   - 到 Registry 的网络访问受限
   - DNS 解析问题
   - Proxy 配置问题

   **解决方案**：
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

**故障排查步骤：**

1. **检查 Pod 状态和事件**：
   ```bash
   # Check pod status
   kubectl get pod <pod-name>

   # Check pod details and events
   kubectl describe pod <pod-name>
   ```

2. **验证 Image 名称和 Registry**：
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

3. **检查认证配置**：
   ```bash
   # Check service account and image pull secrets
   kubectl get serviceaccount default -o yaml

   # Check secret contents
   kubectl get secret <secret-name> -o yaml
   ```

4. **应用临时变通方案**：
   ```bash
   # Pull image locally and transfer to node (for emergencies)
   docker pull <image-name>
   docker save <image-name> -o image.tar
   scp image.tar ec2-user@<node-ip>:~/
   ssh ec2-user@<node-ip> "docker load -i image.tar"
   ```

**最佳实践：**

1. **Image tag 管理**：
   - 使用 digest 而不是特定 tag
   - 避免使用 `latest` tag
   - 实施版本管理策略

2. **Image pull secret 管理**：
   - 将 secret 关联到 service account
   - 定期轮换 secret
   - 自动化 secret 管理

3. **确保 Image registry 可访问**：
   - 为 private registry 配置 VPC endpoint
   - 配置 network policy 和 security group
   - 考虑 Image 缓存

4. **使用 ECR 时的最佳实践**：
   - 使用基于 IAM role 的认证
   - 实施自动 token 续期
   - 配置 Image scanning 和 lifecycle policy

其他选项的问题：
- **A. Pod 资源限制超出 / 增加资源限制**：资源限制问题通常导致 "OOMKilled" 或 "Pending" 状态，而不是 "ImagePullBackOff"。
- **C. Node 磁盘空间不足 / 释放磁盘空间**：虽然磁盘空间不足可能导致 "ImagePullBackOff"，但磁盘空间相关错误通常会显示在 Node 事件中，而且不是最常见原因。
- **D. Network policy 限制 / 修改 network policy**：Network policy 影响 Pod 之间的通信，但通常不是 Image pull 问题的主要原因。
</details>
### 4. 当 Amazon EKS Cluster 中 Service 未将流量路由到 Pod 时，最有效的故障排查步骤是什么？

A. 立即创建新的 Service
B. 检查 Service 和 Pod labels、endpoints 以及 network policies
C. 重启所有 Pod
D. 重启 Cluster API server

<details>
<summary>显示答案</summary>

**答案：B. 检查 Service 和 Pod labels、endpoints 以及 network policies**

**解释：**
当 Amazon EKS Cluster 中 Service 未将流量路由到 Pod 时，最有效的故障排查步骤是检查 Service 和 Pod labels、endpoints 以及 network policies。这种系统化方法有助于识别服务发现和流量路由问题的根本原因。

**要检查的关键项：**

1. **检查 Service 和 Pod labels**：
   - Service selector 与 Pod label 是否匹配
   - Label 语法和拼写错误
   - Namespace 验证

2. **检查 endpoints**：
   - Service endpoint 创建情况
   - Endpoint IP 与 Pod IP 是否匹配
   - Ready Pod 数量

3. **检查 network policies**：
   - 限制流量的 Network policy
   - Ingress 和 egress 规则
   - 跨 Namespace 通信限制

4. **检查 Service 和 Pod 状态**：
   - Pod running 和 ready 状态
   - Service 类型和端口配置
   - Health check 配置

**故障排查方法：**

1. **检查 Service 和 Pod labels**：
   ```bash
   # Check service selector
   kubectl get service <service-name> -o yaml | grep -A 5 selector

   # Check pod labels
   kubectl get pods --show-labels

   # Check pods matching selector
   kubectl get pods -l key=value
   ```

2. **检查 endpoints**：
   ```bash
   # Check service endpoints
   kubectl get endpoints <service-name>

   # Check endpoint details
   kubectl describe endpoints <service-name>

   # Compare endpoint and pod IPs
   kubectl get pods -o wide
   ```

3. **检查 network policies**：
   ```bash
   # Check network policies
   kubectl get networkpolicy

   # Check network policy details
   kubectl describe networkpolicy <policy-name>

   # Temporarily disable network policy
   kubectl delete networkpolicy <policy-name>
   ```

4. **测试 Service 连接**：
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

**常见 Service 问题和解决方案：**

1. **Label 不匹配**：
   - **症状**：Service endpoints 为空
   - **解决方案**：
     ```bash
     # Modify service selector
     kubectl edit service <service-name>
     # or
     kubectl patch service <service-name> -p '{"spec":{"selector":{"app":"correct-label"}}}'

     # Modify pod labels
     kubectl label pods <pod-name> app=correct-label --overwrite
     ```

2. **端口配置错误**：
   - **症状**：Service 可连接但应用没有响应
   - **解决方案**：
     ```bash
     # Check service port configuration
     kubectl describe service <service-name>

     # Check pod container port
     kubectl describe pod <pod-name>

     # Modify service port
     kubectl edit service <service-name>
     ```

3. **Network policy 限制**：
   - **症状**：仅从特定来源无法访问 Service
   - **解决方案**：
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

4. **CoreDNS 问题**：
   - **症状**：Service 名称解析失败
   - **解决方案**：
     ```bash
     # Check CoreDNS pods
     kubectl get pods -n kube-system -l k8s-app=kube-dns

     # Check CoreDNS logs
     kubectl logs -n kube-system -l k8s-app=kube-dns

     # Check CoreDNS configuration
     kubectl get configmap -n kube-system coredns -o yaml
     ```

**最佳实践：**

1. **系统化故障排查方法**：
   - 从 Service 配置开始，然后按顺序检查 Pod、network policies 和 DNS
   - 在每一步收集明确证据
   - 每次只改变一个变量

2. **利用 Service 调试工具**：
   ```bash
   # Check kube-proxy logs
   kubectl logs -n kube-system -l k8s-app=kube-proxy

   # Check iptables rules (for self-managed nodes)
   ssh ec2-user@<node-ip>
   sudo iptables-save | grep <service-ip>

   # DNS debugging
   kubectl run -it --rm dnsutils --image=tutum/dnsutils -- bash
   ```

3. **实施 Service 监控**：
   - 监控 Service endpoint 状态
   - 验证 Service 连接状态
   - 可视化流量路径

4. **Service 配置管理**：
   - 一致的标签策略
   - 明确的端口命名
   - 记录 Service 文档

其他选项的问题：
- **A. 立即创建新的 Service**：在未识别根本原因的情况下创建新的 Service，可能会出现相同问题，并且诊断信息会丢失。
- **C. 重启所有 Pod**：重启 Pod 无法修复 Service 配置问题，并且可能造成不必要的服务中断。
- **D. 重启 Cluster API server**：重启 API server 是极端措施，与 Service 路由问题没有直接关系，也可能影响整个 Cluster。
</details>
### 5. 当 Amazon EKS Cluster 中 PersistentVolumeClaim 保持在 "Pending" 状态时，最可能的原因和解决方案是什么？

A. Node 资源不足 / 添加更大的 Node
B. Storage class 问题或 Volume provisioning 权限不足 / 检查 storage class 并配置 IAM 权限
C. Pod 优先级低 / 提高 Pod 优先级
D. Cluster autoscaler 已禁用 / 启用 autoscaler

<details>
<summary>显示答案</summary>

**答案：B. Storage class 问题或 Volume provisioning 权限不足 / 检查 storage class 并配置 IAM 权限**

**解释：**
当 Amazon EKS Cluster 中 PersistentVolumeClaim (PVC) 保持在 "Pending" 状态时，最可能的原因是 storage class 问题或 volume provisioning 权限不足。要解决此问题，需要检查 storage class 并配置必要的 IAM 权限。

**主要原因和解决方案：**

1. **Storage class 问题**：
   - 指定了不存在的 storage class
   - Storage class 参数错误
   - Provisioner 配置问题

   **解决方案**：
   ```bash
   # Check storage classes
   kubectl get storageclass

   # Check storage class details
   kubectl describe storageclass <storage-class-name>

   # Set default storage class
   kubectl patch storageclass <storage-class-name> -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
   ```

2. **IAM 权限不足**：
   - EBS CSI driver service account 缺少权限
   - Node IAM role 缺少权限
   - 跨账户访问问题

   **解决方案**：
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

3. **Volume binding mode 问题**：
   - 可用区不匹配
   - WaitForFirstConsumer 设置问题
   - Topology 约束

   **解决方案**：
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

4. **CSI driver 问题**：
   - CSI driver 未安装或出错
   - 版本兼容性问题
   - Controller Pod 错误

   **解决方案**：
   ```bash
   # Check CSI driver pods
   kubectl get pods -n kube-system -l app=ebs-csi-controller

   # Check CSI driver logs
   kubectl logs -n kube-system -l app=ebs-csi-controller -c ebs-plugin

   # Reinstall CSI driver
   eksctl create addon --name aws-ebs-csi-driver --cluster <cluster-name> --force
   ```

**最佳实践：**

1. **适当的 storage class 配置**：
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

2. **IRSA (IAM Roles for Service Accounts) 配置**：
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

3. **优化的 PVC 请求**：
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

4. **Volume binding mode 优化**：
   - 使用 WaitForFirstConsumer
   - 确保 Pod 和 PV 可用区匹配
   - 利用 topology-aware provisioning

其他选项的问题：
- **A. Node 资源不足 / 添加更大的 Node**：Node 资源不足通常会导致 Pod 处于 "Pending" 状态，但与 PVC 处于 "Pending" 状态没有直接关系。
- **C. Pod 优先级低 / 提高 Pod 优先级**：Pod 优先级会影响调度决策，但不会影响 PVC provisioning。
- **D. Cluster autoscaler 已禁用 / 启用 autoscaler**：Autoscaler 有助于调整 Node 数量，但与 PVC provisioning 问题没有直接关系。
</details>
### 6. 当 Amazon EKS Cluster 中 autoscaling 未按预期工作时，最有效的故障排查方法是什么？

A. 为所有 Pod 分配更多资源
B. 手动添加 Node
C. 检查 HPA、CA、VPA 配置、metrics、权限和事件
D. 重新创建 Cluster

<details>
<summary>显示答案</summary>

**答案：C. 检查 HPA、CA、VPA 配置、metrics、权限和事件**

**解释：**
当 Amazon EKS Cluster 中 autoscaling 未按预期工作时，最有效的故障排查方法是检查 HPA (Horizontal Pod Autoscaler)、CA (Cluster Autoscaler)、VPA (Vertical Pod Autoscaler) 配置、metrics、权限和事件。这种系统化方法有助于识别并解决 autoscaling 问题的根本原因。

**要检查的关键项：**

1. **检查 HPA (Horizontal Pod Autoscaler)**：
   - HPA 配置和状态
   - Metrics 可用性和值
   - Scaling 限制和行为

2. **检查 CA (Cluster Autoscaler)**：
   - CA Deployment 和配置
   - IAM 权限和 role
   - Node group tag 和设置

3. **检查 VPA (Vertical Pod Autoscaler)**：
   - VPA 配置和模式
   - 资源建议
   - 更新策略

4. **检查 metrics 和事件**：
   - Metrics server 状态
   - CloudWatch metrics 可用性
   - Autoscaling 事件和日志

**故障排查方法：**

1. **HPA 故障排查**：
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

2. **CA 故障排查**：
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

3. **VPA 故障排查**：
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

4. **Metrics 和权限故障排查**：
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

**常见 autoscaling 问题和解决方案：**

1. **HPA metrics 问题**：
   - **症状**：HPA 未做出 scaling 决策
   - **原因**：Metrics server 错误或 metrics 可用性问题
   - **解决方案**：
     ```bash
     # Reinstall metrics server
     kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

     # Verify metrics
     kubectl top pods
     kubectl top nodes
     ```

2. **CA 权限问题**：
   - **症状**：CA 未添加 Node
   - **原因**：IAM 权限不足或缺少 ASG tag
   - **解决方案**：
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

3. **Scaling 限制问题**：
   - **症状**：Scaling 无法超过某个值
   - **原因**：HPA 或 CA 限制设置
   - **解决方案**：
     ```bash
     # Modify HPA max replicas
     kubectl patch hpa <hpa-name> -p '{"spec":{"maxReplicas":20}}'

     # Modify ASG max size
     aws autoscaling update-auto-scaling-group \
       --auto-scaling-group-name <asg-name> \
       --max-size 10
     ```

4. **VPA update mode 问题**：
   - **症状**：VPA 未更新资源
   - **原因**：Update mode 设置为 "Off" 或 "Initial"
   - **解决方案**：
     ```bash
     # Modify VPA update mode
     kubectl patch vpa <vpa-name> -p '{"spec":{"updatePolicy":{"updateMode":"Auto"}}}'
     ```

**最佳实践：**

1. **系统化故障排查方法**：
   - 分别检查每个 autoscaling 组件
   - 分析日志和事件
   - 逐步故障排查

2. **实施 autoscaling 监控**：
   - 监控 autoscaling 活动
   - 设置 scaling 事件通知
   - 配置 scaling metrics dashboard

3. **优化 autoscaling 配置**：
   - 设置适合 workload 特征的 scaling 阈值
   - 调整 scaling 行为和 cooldown period
   - 平衡成本和性能

4. **集成多个 autoscaling 组件**：
   - 组合使用 HPA、CA、VPA
   - 防止组件之间冲突
   - 实施一致的 scaling 策略

其他选项的问题：
- **A. 为所有 Pod 分配更多资源**：这无法解决根本原因，并且可能浪费资源，无法识别 autoscaling 问题的实际原因。
- **B. 手动添加 Node**：这只是临时解决方案，无法解决 autoscaling 系统的根本问题。
- **D. 重新创建 Cluster**：这是极端措施，无法识别根本原因，并会造成不必要的停机和工作量。
</details>
### 7. 当 Amazon EKS Cluster 中 network policies 未按预期工作时，最有效的故障排查方法是什么？

A. 删除所有 network policies 并使用默认设置
B. 检查 Cluster CNI plugin、network policy 配置、日志和事件
C. 为所有 Pod 设置 hostNetwork: true
D. 重新配置 Cluster VPC

<details>
<summary>显示答案</summary>

**答案：B. 检查 Cluster CNI plugin、network policy 配置、日志和事件**

**解释：**
当 Amazon EKS Cluster 中 network policies 未按预期工作时，最有效的故障排查方法是系统化地检查 Cluster CNI plugin、network policy 配置、日志和事件。这种方法有助于识别并解决 network policy 问题的根本原因。

**要检查的关键项：**

1. **检查 CNI plugin**：
   - 正在使用的 CNI plugin 类型（AWS VPC CNI、Calico、Cilium 等）
   - CNI plugin 版本和兼容性
   - Network policy 支持情况

2. **检查 network policy 配置**：
   - Network policy 语法和 selector
   - Policy 优先级和冲突
   - Namespace 和 label selector

3. **检查日志和事件**：
   - CNI plugin 日志
   - Network policy controller 日志
   - 相关事件和错误消息

4. **测试网络连接**：
   - Pod 到 Pod 连接测试
   - Service 连接测试
   - 外部连接测试

**故障排查方法：**

1. **检查 CNI plugin**：
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

2. **检查 network policies**：
   ```bash
   # List network policies
   kubectl get networkpolicies --all-namespaces

   # Check specific network policy details
   kubectl describe networkpolicy <policy-name> -n <namespace>

   # Check network policy YAML
   kubectl get networkpolicy <policy-name> -n <namespace> -o yaml
   ```

3. **检查 Pod 网络信息**：
   ```bash
   # Check pod IP and node information
   kubectl get pods -o wide

   # Check pod network interface
   kubectl exec -it <pod-name> -- ip addr

   # Check pod routing table
   kubectl exec -it <pod-name> -- ip route
   ```

4. **测试网络连接**：
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

**常见 network policy 问题和解决方案：**

1. **CNI plugin 兼容性问题**：
   - **症状**：Network policies 未被应用
   - **原因**：正在使用的 CNI plugin 不支持 network policies
   - **解决方案**：
     ```bash
     # Add Calico policy engine to AWS VPC CNI
     kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
     kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml

     # Or switch to Cilium
     helm repo add cilium https://helm.cilium.io/
     helm install cilium cilium/cilium --namespace kube-system
     ```

2. **Network policy selector 问题**：
   - **症状**：Policy 未应用到预期的 Pod
   - **原因**：Label selector 或 namespace selector 不正确
   - **解决方案**：
     ```bash
     # Check pod labels
     kubectl get pods --show-labels

     # Modify network policy
     kubectl edit networkpolicy <policy-name> -n <namespace>
     ```

3. **Policy 冲突问题**：
   - **症状**：连接被意外阻止或允许
   - **原因**：多个 policy 之间存在冲突或优先级问题
   - **解决方案**：
     ```bash
     # Review all network policies
     kubectl get networkpolicies --all-namespaces -o yaml

     # Simplify or reconfigure policies
     kubectl apply -f updated-network-policy.yaml
     ```

4. **CNI plugin bug 或配置错误**：
   - **症状**：间歇性连接问题或行为不一致
   - **原因**：CNI plugin bug 或配置不正确
   - **解决方案**：
     ```bash
     # Update CNI plugin
     kubectl set image daemonset/aws-node -n kube-system aws-node=<new-image-version>

     # Check and modify CNI configuration
     kubectl edit configmap -n kube-system aws-node
     ```

**最佳实践：**

1. **系统化 network policy 设计**：
   - 从 default deny policy 开始
   - 仅显式允许必要连接
   - 使用基于 namespace 和 label 的 policy

2. **测试并验证 network policies**：
   - 应用 policy 前先测试
   - 自动化连接测试
   - 逐步 rollout policy

3. **网络监控和日志记录**：
   - 监控网络流量
   - 记录连接拒绝
   - 监控网络性能

4. **CNI plugin 选择和配置**：
   - 选择适合 workload 需求的 CNI
   - 保持更新
   - 分配适当资源

其他选项的问题：
- **A. 删除所有 network policies 并使用默认设置**：这会带来安全风险，移除必要的网络隔离，并且无法解决根本原因。
- **C. 为所有 Pod 设置 hostNetwork: true**：这会绕过 network policies，带来安全风险，并移除 Pod 之间的隔离。
- **D. 重新配置 Cluster VPC**：这是极端措施，大多数 network policy 问题与 Cluster 内部的 CNI 和 policy 配置有关，而不是 VPC 层面的问题。
</details>
### 8. 排查 Amazon EKS Cluster 中 Helm chart 部署问题的最有效方法是什么？

A. 删除所有 Helm chart 并重新安装
B. 重新创建 Cluster
C. 系统化检查 Helm 版本、chart 配置、依赖、权限和日志
D. 手动部署所有资源

<details>
<summary>显示答案</summary>

**答案：C. 系统化检查 Helm 版本、chart 配置、依赖、权限和日志**

**解释：**
排查 Amazon EKS Cluster 中 Helm chart 部署问题的最有效方法是系统化检查 Helm 版本、chart 配置、依赖、权限和日志。这种方法有助于识别并解决 Helm 部署问题的根本原因。

**要检查的关键项：**

1. **检查 Helm 版本和兼容性**：
   - Helm client 和 Tiller (Helm 2) 版本
   - Kubernetes API 版本兼容性
   - EKS 版本兼容性

2. **检查 chart 配置和值**：
   - Chart 语法错误
   - Values file 配置
   - Template rendering 问题

3. **检查依赖和 repository**：
   - Chart dependency 可用性
   - Repository 可访问性
   - Chart 版本兼容性

4. **检查权限和 RBAC**：
   - Service account 权限
   - RBAC 规则
   - Namespace 访问

5. **检查日志和事件**：
   - Helm debug 日志
   - Kubernetes 事件
   - 相关 Pod 日志

**故障排查方法：**

1. **检查 Helm 版本和配置**：
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

2. **验证和调试 chart**：
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

3. **检查 release 状态和历史**：
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

4. **检查资源和事件**：
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

5. **检查权限和 RBAC**：
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

**常见 Helm 部署问题和解决方案：**

1. **Chart 语法错误**：
   - **症状**：`helm install` 或 `helm template` 命令失败
   - **原因**：YAML 语法错误、无效的 template function 或变量
   - **解决方案**：
     ```bash
     # Validate chart syntax
     helm lint ./my-chart

     # Check template rendering
     helm template ./my-chart --debug

     # Render template with specific values
     helm template ./my-chart --set key=value --debug
     ```

2. **依赖问题**：
   - **症状**：Chart 安装期间出现依赖错误
   - **原因**：缺少依赖、版本不匹配或 repository 访问问题
   - **解决方案**：
     ```bash
     # Update dependencies
     helm dependency update ./my-chart

     # Add and update repository
     helm repo add bitnami https://charts.bitnami.com/bitnami
     helm repo update

     # Build dependencies
     helm dependency build ./my-chart
     ```

3. **权限问题**：
   - **症状**：Permission denied 错误
   - **原因**：RBAC 权限不足或 service account 配置不正确
   - **解决方案**：
     ```bash
     # Create required RBAC resources
     kubectl apply -f rbac.yaml

     # Specify service account
     helm install my-release ./my-chart --service-account=my-service-account

     # Check permissions
     kubectl auth can-i create deployments --as=system:serviceaccount:<namespace>:<serviceaccount>
     ```

4. **资源冲突**：
   - **症状**：Resource already exists 错误
   - **原因**：上一次安装留下的资源仍存在，或名称冲突
   - **解决方案**：
     ```bash
     # Remove existing release
     helm uninstall my-release

     # Check and delete remaining resources
     kubectl get all -n <namespace> -l app.kubernetes.io/instance=my-release
     kubectl delete <resource-type> <resource-name> -n <namespace>

     # Install with different release name
     helm install new-release ./my-chart
     ```

5. **Values 配置问题**：
   - **症状**：已部署的应用未按预期工作
   - **原因**：配置值不正确或缺少必需值
   - **解决方案**：
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

**最佳实践：**

1. **系统化故障排查方法**：
   - 逐步验证和校验
   - 日志和事件分析
   - 从症状追踪到原因

2. **测试并验证 Helm chart**：
   - 部署前验证 chart
   - 先在测试环境测试
   - 在 CI/CD pipeline 中包含验证步骤

3. **版本管理和兼容性**：
   - 使用兼容的 Helm 和 Kubernetes 版本
   - 明确指定 chart 版本
   - 固定依赖版本

4. **文档和 values 管理**：
   - 记录 chart values
   - 管理特定环境的 values file
   - 对敏感 values 应用安全实践

其他选项的问题：
- **A. 删除所有 Helm chart 并重新安装**：这是极端措施，可能导致数据丢失，并且无法解决根本原因。
- **B. 重新创建 Cluster**：这是非常极端的措施，大多数 Helm 部署问题与 chart 配置或权限有关，而不是 Cluster 级别问题。
- **D. 手动部署所有资源**：这放弃了 Helm 的优势，对于复杂应用来说容易出错且难以管理。
</details>
### 9. 排查 Amazon EKS Cluster 中内存泄漏问题的最有效方法是什么？

A. 重启所有 Pod
B. 增加 Cluster Node 大小
C. Profile 内存使用情况、审查 Container 限制、分析应用代码
D. 添加更多 Node

<details>
<summary>显示答案</summary>

**答案：C. Profile 内存使用情况、审查 Container 限制、分析应用代码**

**解释：**
排查 Amazon EKS Cluster 中内存泄漏问题的最有效方法是采用系统化方法，包括内存使用情况 profiling、Container 限制审查和应用代码分析。此方法有助于识别并解决内存泄漏的根本原因。

**要检查的关键项：**

1. **内存使用情况 profiling**：
   - 在 Pod 和 Node 级别监控内存使用情况
   - 分析一段时间内的内存使用模式
   - 识别内存泄漏迹象

2. **审查 Container 限制**：
   - 检查内存 request 和 limit 设置
   - 分析 Container OOM (Out of Memory) 事件
   - 优化资源分配

3. **应用代码分析**：
   - 审查应用内部内存使用模式
   - 识别可能存在内存泄漏的代码
   - 使用应用 profiling 工具

4. **审查系统组件**：
   - kubelet 内存管理设置
   - Node 系统资源使用情况
   - Cluster 组件状态

**故障排查方法：**

1. **监控并分析内存使用情况**：
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

2. **检查 Container 限制和 OOM 事件**：
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

3. **应用日志和 profiling**：
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

4. **检查 Node 和系统资源**：
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

**常见内存泄漏问题和解决方案：**

1. **应用内存泄漏**：
   - **症状**：内存使用量随时间持续增加
   - **原因**：应用代码中的内存泄漏，缺少缓存管理
   - **解决方案**：
     - 审查并修复应用代码
     - 使用内存 profiling 工具
     - 配置周期性 garbage collection
     - 实施缓存大小限制和过期策略

2. **Container 内存限制问题**：
   - **症状**：频繁 OOM 终止，Pod 重启
   - **原因**：内存 limit 设置不合适，resource request 和 limit 之间差距过大
   - **解决方案**：
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

3. **系统组件内存问题**：
   - **症状**：Node 不稳定，kubelet 或其他系统组件内存使用量高
   - **原因**：kubelet 配置问题，系统组件 bug
   - **解决方案**：
     - 优化 kubelet 配置
     - 更新系统组件
     - 调整 Node 资源预留

4. **内存碎片问题**：
   - **症状**：尽管总可用内存充足仍发生 OOM
   - **原因**：内存碎片、大页分配失败
   - **解决方案**：
     - 安排周期性 Node 重启
     - 分散高内存压力的 workload
     - 减少 Node 内存 overcommit

**最佳实践：**

1. **系统化内存监控**：
   - 在 Cluster、Node 和 Pod 级别监控内存
   - 跟踪一段时间内的内存使用模式
   - 为异常设置告警

2. **设置适当的资源限制**：
   - 设置适合 workload 特征的内存 request 和 limit
   - 保持内存 request 和 limit 之间的适当比例
   - 定期审查和调整资源使用情况

3. **应用优化**：
   - 编写内存高效的代码
   - 定期进行内存 profiling 和优化
   - 实施合适的缓存策略

4. **Cluster 配置优化**：
   - 优化 Node 内存预留
   - 适当的 kubelet 内存管理设置
   - Workload 分布和隔离

其他选项的问题：
- **A. 重启所有 Pod**：这只是临时解决方案，无法解决内存泄漏的根本原因。Pod 重启后问题会再次出现。
- **B. 增加 Cluster Node 大小**：这无法解决根本原因，只会掩盖症状。如果内存泄漏持续存在，更大的 Node 最终也会耗尽内存。
- **D. 添加更多 Node**：与 B 类似，这只是在不解决根本原因的情况下掩盖症状。无论 Node 数量多少，内存泄漏问题都会继续存在。
</details>
### 10. 排查 Amazon EKS Cluster 中 DNS 解析问题的最有效方法是什么？

A. 为所有 Pod 分配静态 IP
B. 系统化检查 CoreDNS 配置、network policies、DNS policies 和连接
C. 对所有 Service 使用 ExternalName
D. 重新配置 Cluster VPC

<details>
<summary>显示答案</summary>

**答案：B. 系统化检查 CoreDNS 配置、network policies、DNS policies 和连接**

**解释：**
排查 Amazon EKS Cluster 中 DNS 解析问题的最有效方法是系统化检查 CoreDNS 配置、network policies、DNS policies 和连接。这种方法有助于识别并解决 DNS 问题的根本原因。

**要检查的关键项：**

1. **检查 CoreDNS 配置和状态**：
   - CoreDNS Pod 状态和日志
   - CoreDNS ConfigMap 配置
   - CoreDNS Service 和 endpoints

2. **检查 network policies 和连接**：
   - DNS 端口 (53/UDP, 53/TCP) 的 Network policy
   - Pod 与 CoreDNS 之间的网络连接
   - VPC DNS 设置

3. **检查 DNS policies 和配置**：
   - Pod DNS policy 设置
   - DNS 配置选项
   - Host namespace 设置

4. **检查 Cluster 和 VPC 配置**：
   - EKS Cluster DNS 设置
   - VPC DNS 属性
   - DHCP option sets

**故障排查方法：**

1. **检查 CoreDNS 状态和配置**：
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

2. **测试 DNS 解析**：
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

3. **检查 network policies 和连接**：
   ```bash
   # Check DNS-related network policies
   kubectl get networkpolicies --all-namespaces

   # Test connection to CoreDNS
   kubectl run netcat-test --rm -it --image=busybox -- sh -c "nc -zv kube-dns.kube-system.svc.cluster.local 53"

   # Capture DNS packets
   kubectl run tcpdump-test --rm -it --image=nicolaka/netshoot -- tcpdump -i any port 53
   ```

4. **检查 Pod DNS 配置**：
   ```bash
   # Check pod DNS policy
   kubectl get pod <pod-name> -o jsonpath='{.spec.dnsPolicy}'

   # Check pod DNS configuration
   kubectl get pod <pod-name> -o jsonpath='{.spec.dnsConfig}'

   # Check pod internal resolv.conf
   kubectl exec -it <pod-name> -- cat /etc/resolv.conf
   ```

5. **检查 VPC 和 Cluster DNS 设置**：
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

**常见 DNS 问题和解决方案：**

1. **CoreDNS Pod 问题**：
   - **症状**：DNS 查询失败，CoreDNS Pod 异常
   - **原因**：CoreDNS Pod 崩溃、资源不足、配置错误
   - **解决方案**：
     ```bash
     # Restart CoreDNS pods
     kubectl rollout restart deployment coredns -n kube-system

     # Increase CoreDNS resources
     kubectl edit deployment coredns -n kube-system
     # Increase requests and limits in resources section

     # Check CoreDNS logs
     kubectl logs -n kube-system -l k8s-app=kube-dns
     ```

2. **Network policy 问题**：
   - **症状**：仅从特定 Namespace 或 Pod 发起 DNS 解析失败
   - **原因**：限制性的 network policies 阻止 DNS 流量
   - **解决方案**：
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

3. **DNS policy 和配置问题**：
   - **症状**：只有某些类型的 DNS 查询失败
   - **原因**：DNS policy 或配置不合适
   - **解决方案**：
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

4. **VPC DNS 设置问题**：
   - **症状**：外部域名解析失败
   - **原因**：VPC DNS 属性已禁用或 DHCP option set 问题
   - **解决方案**：
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

5. **CoreDNS 配置问题**：
   - **症状**：特定域名解析失败或 DNS 解析缓慢
   - **原因**：CoreDNS 配置错误或设置未优化
   - **解决方案**：
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

**最佳实践：**

1. **CoreDNS 监控和 scaling**：
   - 监控 CoreDNS 性能和状态
   - 根据 Cluster 大小扩展 CoreDNS replicas
   - 分配适当资源

2. **DNS 缓存和优化**：
   - 合适的 TTL 和 cache 设置
   - 实施 Node 级 DNS 缓存
   - 考虑应用级 DNS 缓存

3. **Network policy 设计**：
   - 显式允许 DNS 流量
   - 应用最小权限原则
   - 测试并验证 network policies

4. **DNS 故障排查工具和流程**：
   - 准备 DNS 故障排查工具和脚本
   - 建立系统化故障排查流程
   - 监控 DNS 相关事件和日志

其他选项的问题：
- **A. 为所有 Pod 分配静态 IP**：这无法解决 DNS 问题，Pod IP 分配和 DNS 解析是不同的问题。为 Pod 分配静态 IP 也违背 Kubernetes 的动态特性，并增加管理复杂度。
- **C. 对所有 Service 使用 ExternalName**：这只适用于特定用例，无法解决大多数 DNS 问题。ExternalName 用于为外部服务提供别名，无法解决 Cluster 内部 DNS 解析问题。
- **D. 重新配置 Cluster VPC**：这是极端措施，大多数 DNS 问题与 Cluster 内部 DNS 配置有关，而不是 VPC 层面的问题。重新配置 VPC 可能造成不必要的停机和复杂性。
</details>

# Amazon EKS Troubleshooting Quiz

This quiz tests your ability to diagnose and resolve various issues that may occur in Amazon EKS clusters.

## Quiz Overview
- Cluster creation and configuration issues
- Networking issues
- Node and pod issues
- Storage issues
- Security and access issues
- Performance and scalability issues

## Multiple Choice Questions

### 1. What should you check first when Amazon EKS cluster creation fails?

A. Check if the cluster name is unique
B. Check IAM permissions, VPC configuration, and service quotas
C. Try again in a different region
D. Select a larger instance type

<details>
<summary>Show Answer</summary>

**Answer: B. Check IAM permissions, VPC configuration, and service quotas**

**Explanation:**
When Amazon EKS cluster creation fails, the first things to check are IAM permissions, VPC configuration, and service quotas. These factors are the most common causes of cluster creation failure, and systematically checking them can help quickly identify and resolve issues.

**Key items to check:**

1. **Check IAM permissions**:
   - Whether you have the required IAM permissions for cluster creation
   - Permission to create service-linked roles
   - Cluster role and policy configuration

2. **Check VPC configuration**:
   - Subnet configuration (subnets distributed across at least 2 availability zones)
   - Subnet CIDR size (minimum /28, recommended /24)
   - Internet connectivity (NAT gateway or internet gateway)
   - Security group and network ACL settings

3. **Check service quotas**:
   - EKS cluster count quota
   - EC2 instance quota
   - VPC and subnet quotas
   - Other related service quotas

**Troubleshooting methods:**

1. **Resolving IAM permission issues**:
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

2. **Resolving VPC configuration issues**:
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

3. **Resolving service quota issues**:
   ```bash
   # Check service quotas
   aws service-quotas list-service-quotas --service-code eks

   # Request quota increase
   aws service-quotas request-service-quota-increase \
     --service-code eks \
     --quota-code L-1194D53C \
     --desired-value 10
   ```

**Common error messages and solutions:**

1. **Insufficient IAM permissions**:
   - Error: "User: arn:aws:iam::123456789012:user/myuser is not authorized to perform: eks:CreateCluster"
   - Solution: Add required IAM permissions

2. **VPC subnet issues**:
   - Error: "Cannot create cluster 'my-cluster' because us-west-2a, the targeted availability zone, does not have sufficient capacity to support the cluster. Retry after some time or try other availability zones."
   - Solution: Use subnets in different availability zones or create new subnets

3. **Service quota exceeded**:
   - Error: "Account cannot create more EKS clusters in region us-west-2. Current limit is 5"
   - Solution: Request service quota increase or delete unnecessary clusters

**Best practices:**

1. **Pre-cluster creation preparation**:
   - Verify required IAM permissions
   - Configure appropriate VPC and subnets
   - Check service quotas

2. **Systematic troubleshooting approach**:
   - Analyze error messages
   - Check AWS CloudTrail logs
   - Step-by-step component verification

3. **Automated infrastructure configuration**:
   - Use AWS CloudFormation or Terraform
   - Utilize tools like eksctl
   - Version control infrastructure configuration

**Practical implementation examples:**

1. **Troubleshooting cluster creation with eksctl**:
   ```bash
   # Create cluster in debug mode
   eksctl create cluster --name my-cluster --region us-west-2 --verbose 4

   # Check cluster creation status
   eksctl get cluster --name my-cluster --region us-west-2
   ```

2. **Troubleshooting cluster creation with AWS CLI**:
   ```bash
   # Attempt cluster creation
   aws eks create-cluster \
     --name my-cluster \
     --role-arn arn:aws:iam::123456789012:role/eks-cluster-role \
     --resources-vpc-config subnetIds=subnet-12345678,subnet-87654321,securityGroupIds=sg-12345678

   # Check cluster status
   aws eks describe-cluster --name my-cluster
   ```

3. **Troubleshooting cluster creation with Terraform**:
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

Issues with other options:
- **A. Check if the cluster name is unique**: While a non-unique cluster name can cause errors, this is not the most common cause of failure.
- **C. Try again in a different region**: This is a workaround that doesn't solve the root cause, and the same problem may occur in other regions.
- **D. Select a larger instance type**: Instance type applies to node groups and does not affect cluster creation itself.
</details>
### 2. What is the most effective troubleshooting approach when a node is in NotReady state in an Amazon EKS cluster?

A. Immediately terminate and replace the node
B. Check node logs, resource usage, and network connectivity
C. Restart the cluster API server
D. Delete and redeploy all pods

<details>
<summary>Show Answer</summary>

**Answer: B. Check node logs, resource usage, and network connectivity**

**Explanation:**
When a node is in NotReady state in an Amazon EKS cluster, the most effective troubleshooting approach is to check node logs, resource usage, and network connectivity. This systematic approach helps identify the root cause of the problem and apply appropriate solutions.

**Key items to check:**

1. **Check node status and events**:
   - Node status details
   - Node-related events
   - Node conditions

2. **Analyze node logs**:
   - kubelet logs
   - System logs
   - Container runtime logs

3. **Check resource usage**:
   - CPU, memory, disk usage
   - Resource limits and pressure
   - System process status

4. **Check network connectivity**:
   - Connection to control plane
   - DNS resolution
   - VPC and subnet configuration

**Troubleshooting methods:**

1. **Check node status and events**:
   ```bash
   # Check node status
   kubectl get nodes
   kubectl describe node <node-name>

   # Check node events
   kubectl get events --field-selector involvedObject.name=<node-name>
   ```

2. **Analyze node logs**:
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

3. **Check resource usage**:
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

4. **Check network connectivity**:
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

**Common NotReady causes and solutions:**

1. **kubelet issues**:
   - **Symptom**: kubelet service not running or cannot connect to API server
   - **Solution**:
     ```bash
     # Check kubelet service status
     sudo systemctl status kubelet

     # Restart kubelet service
     sudo systemctl restart kubelet

     # Check kubelet configuration
     sudo cat /etc/kubernetes/kubelet/kubelet-config.json
     ```

2. **Network issues**:
   - **Symptom**: Node cannot communicate with control plane
   - **Solution**:
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
   - **Symptom**: Insufficient CPU, memory, or disk space on node
   - **Solution**:
     ```bash
     # Free up disk space
     sudo du -sh /var/log/*
     sudo journalctl --vacuum-time=1d

     # Clean up unnecessary containers and images
     docker system prune -af  # When using Docker
     ```

4. **Certificate issues**:
   - **Symptom**: Certificate expired or mismatch
   - **Solution**:
     ```bash
     # Check certificates
     sudo ls -la /etc/kubernetes/pki/

     # Renew certificates (for self-managed nodes)
     sudo kubeadm alpha certs renew all

     # For managed node groups, replace nodes
     eksctl replace nodegroup --cluster=my-cluster --name=my-nodegroup
     ```

**Best practices:**

1. **Systematic troubleshooting approach**:
   - Identify and document symptoms
   - Collect relevant logs and events
   - Systematically verify possible causes

2. **Implement node status monitoring**:
   - Set up CloudWatch alarms
   - Configure node status dashboards
   - Automated alerting system

3. **Implement auto-recovery mechanisms**:
   - Configure self-healing node groups
   - Health checks and automatic replacement
   - Automatic draining of failed nodes

**Practical implementation examples:**

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

2. **Self-healing node group configuration with Terraform**:
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

3. **CloudWatch alarms and automated recovery configuration**:
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

Issues with other options:
- **A. Immediately terminate and replace the node**: Replacing the node without identifying the root cause may cause the same problem on the new node, and diagnostic information is lost.
- **C. Restart the cluster API server**: The API server is not directly related to node status, and restarting it can affect the entire cluster.
- **D. Delete and redeploy all pods**: Deleting pods won't fix issues with the node itself and can cause unnecessary service disruption.
</details>
### 3. What is the most likely cause and solution when a pod is in "ImagePullBackOff" state in an Amazon EKS cluster?

A. Pod resource limit exceeded / Increase resource limits
B. Image name error or authentication issue / Verify image name and configure image pull secrets
C. Node disk space shortage / Free up disk space
D. Network policy restrictions / Modify network policies

<details>
<summary>Show Answer</summary>

**Answer: B. Image name error or authentication issue / Verify image name and configure image pull secrets**

**Explanation:**
When a pod is in "ImagePullBackOff" state in an Amazon EKS cluster, the most likely cause is an image name error or authentication issue. To resolve this, you need to verify the image name and configure image pull secrets if necessary.

**Main causes and solutions:**

1. **Image name error**:
   - Incorrect image name or tag
   - Non-existent image
   - Registry URL error

   **Solution**:
   ```bash
   # Check pod definition
   kubectl describe pod <pod-name>

   # Fix image name and tag
   kubectl edit deployment <deployment-name>
   # or
   kubectl set image deployment/<deployment-name> container-name=image:tag
   ```

2. **Private registry authentication issues**:
   - Missing authentication credentials
   - Expired credentials
   - Insufficient permissions

   **Solution**:
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
   - Insufficient ECR permissions
   - Expired token
   - Cross-account access issues

   **Solution**:
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
   - Network access to registry restricted
   - DNS resolution issues
   - Proxy configuration issues

   **Solution**:
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

**Troubleshooting steps:**

1. **Check pod status and events**:
   ```bash
   # Check pod status
   kubectl get pod <pod-name>

   # Check pod details and events
   kubectl describe pod <pod-name>
   ```

2. **Verify image name and registry**:
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

3. **Check authentication configuration**:
   ```bash
   # Check service account and image pull secrets
   kubectl get serviceaccount default -o yaml

   # Check secret contents
   kubectl get secret <secret-name> -o yaml
   ```

4. **Apply temporary workaround**:
   ```bash
   # Pull image locally and transfer to node (for emergencies)
   docker pull <image-name>
   docker save <image-name> -o image.tar
   scp image.tar ec2-user@<node-ip>:~/
   ssh ec2-user@<node-ip> "docker load -i image.tar"
   ```

**Best practices:**

1. **Image tag management**:
   - Use digests instead of specific tags
   - Avoid using `latest` tag
   - Implement version management strategy

2. **Image pull secret management**:
   - Link secrets to service accounts
   - Regular secret renewal
   - Automate secret management

3. **Ensure image registry accessibility**:
   - Configure VPC endpoints for private registries
   - Configure network policies and security groups
   - Consider image caching

4. **Best practices when using ECR**:
   - Use IAM role-based authentication
   - Implement automatic token renewal
   - Configure image scanning and lifecycle policies

Issues with other options:
- **A. Pod resource limit exceeded / Increase resource limits**: Resource limit issues typically cause "OOMKilled" or "Pending" states, not "ImagePullBackOff".
- **C. Node disk space shortage / Free up disk space**: While disk space shortage can cause "ImagePullBackOff", disk space-related errors typically show in node events and is not the most common cause.
- **D. Network policy restrictions / Modify network policies**: Network policies affect communication between pods but are not typically the main cause of image pull issues.
</details>
### 4. What is the most effective troubleshooting step when a service is not routing traffic to pods in an Amazon EKS cluster?

A. Immediately create a new service
B. Check service and pod labels, endpoints, and network policies
C. Restart all pods
D. Restart the cluster API server

<details>
<summary>Show Answer</summary>

**Answer: B. Check service and pod labels, endpoints, and network policies**

**Explanation:**
When a service is not routing traffic to pods in an Amazon EKS cluster, the most effective troubleshooting step is to check service and pod labels, endpoints, and network policies. This systematic approach helps identify the root cause of service discovery and traffic routing issues.

**Key items to check:**

1. **Check service and pod labels**:
   - Service selector and pod label match
   - Label syntax and typos
   - Namespace verification

2. **Check endpoints**:
   - Service endpoint creation
   - Endpoint IP and pod IP match
   - Number of Ready pods

3. **Check network policies**:
   - Network policies restricting traffic
   - Ingress and egress rules
   - Inter-namespace communication restrictions

4. **Check service and pod status**:
   - Pod running and ready state
   - Service type and port configuration
   - Health check configuration

**Troubleshooting methods:**

1. **Check service and pod labels**:
   ```bash
   # Check service selector
   kubectl get service <service-name> -o yaml | grep -A 5 selector

   # Check pod labels
   kubectl get pods --show-labels

   # Check pods matching selector
   kubectl get pods -l key=value
   ```

2. **Check endpoints**:
   ```bash
   # Check service endpoints
   kubectl get endpoints <service-name>

   # Check endpoint details
   kubectl describe endpoints <service-name>

   # Compare endpoint and pod IPs
   kubectl get pods -o wide
   ```

3. **Check network policies**:
   ```bash
   # Check network policies
   kubectl get networkpolicy

   # Check network policy details
   kubectl describe networkpolicy <policy-name>

   # Temporarily disable network policy
   kubectl delete networkpolicy <policy-name>
   ```

4. **Test service connectivity**:
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

**Common service issues and solutions:**

1. **Label mismatch**:
   - **Symptom**: Service endpoints are empty
   - **Solution**:
     ```bash
     # Modify service selector
     kubectl edit service <service-name>
     # or
     kubectl patch service <service-name> -p '{"spec":{"selector":{"app":"correct-label"}}}'

     # Modify pod labels
     kubectl label pods <pod-name> app=correct-label --overwrite
     ```

2. **Port configuration error**:
   - **Symptom**: Service connects but no application response
   - **Solution**:
     ```bash
     # Check service port configuration
     kubectl describe service <service-name>

     # Check pod container port
     kubectl describe pod <pod-name>

     # Modify service port
     kubectl edit service <service-name>
     ```

3. **Network policy restrictions**:
   - **Symptom**: Service inaccessible only from specific sources
   - **Solution**:
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
   - **Symptom**: Service name resolution fails
   - **Solution**:
     ```bash
     # Check CoreDNS pods
     kubectl get pods -n kube-system -l k8s-app=kube-dns

     # Check CoreDNS logs
     kubectl logs -n kube-system -l k8s-app=kube-dns

     # Check CoreDNS configuration
     kubectl get configmap -n kube-system coredns -o yaml
     ```

**Best practices:**

1. **Systematic troubleshooting approach**:
   - Start with service configuration, then check pods, network policies, and DNS in order
   - Collect clear evidence at each step
   - Change only one variable at a time

2. **Utilize service debugging tools**:
   ```bash
   # Check kube-proxy logs
   kubectl logs -n kube-system -l k8s-app=kube-proxy

   # Check iptables rules (for self-managed nodes)
   ssh ec2-user@<node-ip>
   sudo iptables-save | grep <service-ip>

   # DNS debugging
   kubectl run -it --rm dnsutils --image=tutum/dnsutils -- bash
   ```

3. **Implement service monitoring**:
   - Monitor service endpoint status
   - Verify service connectivity status
   - Visualize traffic flow

4. **Service configuration management**:
   - Consistent labeling strategy
   - Explicit port naming
   - Document services

Issues with other options:
- **A. Immediately create a new service**: Creating a new service without identifying the root cause may result in the same problem, and diagnostic information is lost.
- **C. Restart all pods**: Restarting pods won't fix service configuration issues and can cause unnecessary service disruption.
- **D. Restart the cluster API server**: Restarting the API server is an extreme measure and is not directly related to service routing issues. It can also affect the entire cluster.
</details>
### 5. What is the most likely cause and solution when a PersistentVolumeClaim remains in "Pending" state in an Amazon EKS cluster?

A. Node resource shortage / Add larger nodes
B. Storage class issue or insufficient volume provisioning permissions / Check storage class and configure IAM permissions
C. Low pod priority / Increase pod priority
D. Cluster autoscaler disabled / Enable autoscaler

<details>
<summary>Show Answer</summary>

**Answer: B. Storage class issue or insufficient volume provisioning permissions / Check storage class and configure IAM permissions**

**Explanation:**
When a PersistentVolumeClaim (PVC) remains in "Pending" state in an Amazon EKS cluster, the most likely cause is a storage class issue or insufficient volume provisioning permissions. To resolve this, you need to check the storage class and configure the necessary IAM permissions.

**Main causes and solutions:**

1. **Storage class issues**:
   - Specifying a non-existent storage class
   - Storage class parameter errors
   - Provisioner configuration issues

   **Solution**:
   ```bash
   # Check storage classes
   kubectl get storageclass

   # Check storage class details
   kubectl describe storageclass <storage-class-name>

   # Set default storage class
   kubectl patch storageclass <storage-class-name> -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
   ```

2. **Insufficient IAM permissions**:
   - EBS CSI driver service account lacks permissions
   - Node IAM role lacks permissions
   - Cross-account access issues

   **Solution**:
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

   **Solution**:
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
   - CSI driver not installed or error
   - Version compatibility issues
   - Controller pod errors

   **Solution**:
   ```bash
   # Check CSI driver pods
   kubectl get pods -n kube-system -l app=ebs-csi-controller

   # Check CSI driver logs
   kubectl logs -n kube-system -l app=ebs-csi-controller -c ebs-plugin

   # Reinstall CSI driver
   eksctl create addon --name aws-ebs-csi-driver --cluster <cluster-name> --force
   ```

**Best practices:**

1. **Appropriate storage class configuration**:
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

3. **Optimized PVC request**:
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
   - Use WaitForFirstConsumer
   - Ensure pod and PV availability zone match
   - Utilize topology-aware provisioning

Issues with other options:
- **A. Node resource shortage / Add larger nodes**: Node resource shortage typically causes pods to be in "Pending" state, but is not directly related to PVCs being in "Pending" state.
- **C. Low pod priority / Increase pod priority**: Pod priority affects scheduling decisions but does not affect PVC provisioning.
- **D. Cluster autoscaler disabled / Enable autoscaler**: Autoscaler helps adjust the number of nodes but is not directly related to PVC provisioning issues.
</details>
### 6. What is the most effective troubleshooting approach when autoscaling is not working as expected in an Amazon EKS cluster?

A. Allocate more resources to all pods
B. Manually add nodes
C. Check HPA, CA, VPA configuration, metrics, permissions, and events
D. Recreate the cluster

<details>
<summary>Show Answer</summary>

**Answer: C. Check HPA, CA, VPA configuration, metrics, permissions, and events**

**Explanation:**
When autoscaling is not working as expected in an Amazon EKS cluster, the most effective troubleshooting approach is to check HPA (Horizontal Pod Autoscaler), CA (Cluster Autoscaler), VPA (Vertical Pod Autoscaler) configuration, metrics, permissions, and events. This systematic approach helps identify and resolve the root cause of autoscaling issues.

**Key items to check:**

1. **Check HPA (Horizontal Pod Autoscaler)**:
   - HPA configuration and status
   - Metrics availability and values
   - Scaling limits and behavior

2. **Check CA (Cluster Autoscaler)**:
   - CA deployment and configuration
   - IAM permissions and roles
   - Node group tags and settings

3. **Check VPA (Vertical Pod Autoscaler)**:
   - VPA configuration and mode
   - Resource recommendations
   - Update policies

4. **Check metrics and events**:
   - Metrics server status
   - CloudWatch metrics availability
   - Autoscaling events and logs

**Troubleshooting methods:**

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

4. **Metrics and permissions troubleshooting**:
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

**Common autoscaling issues and solutions:**

1. **HPA metrics issues**:
   - **Symptom**: HPA not making scaling decisions
   - **Cause**: Metrics server error or metrics availability issue
   - **Solution**:
     ```bash
     # Reinstall metrics server
     kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

     # Verify metrics
     kubectl top pods
     kubectl top nodes
     ```

2. **CA permission issues**:
   - **Symptom**: CA not adding nodes
   - **Cause**: Insufficient IAM permissions or missing ASG tags
   - **Solution**:
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
   - **Symptom**: Scaling not exceeding certain value
   - **Cause**: HPA or CA limit settings
   - **Solution**:
     ```bash
     # Modify HPA max replicas
     kubectl patch hpa <hpa-name> -p '{"spec":{"maxReplicas":20}}'

     # Modify ASG max size
     aws autoscaling update-auto-scaling-group \
       --auto-scaling-group-name <asg-name> \
       --max-size 10
     ```

4. **VPA update mode issues**:
   - **Symptom**: VPA not updating resources
   - **Cause**: Update mode set to "Off" or "Initial"
   - **Solution**:
     ```bash
     # Modify VPA update mode
     kubectl patch vpa <vpa-name> -p '{"spec":{"updatePolicy":{"updateMode":"Auto"}}}'
     ```

**Best practices:**

1. **Systematic troubleshooting approach**:
   - Check each autoscaling component individually
   - Analyze logs and events
   - Step-by-step troubleshooting

2. **Implement autoscaling monitoring**:
   - Monitor autoscaling activity
   - Set up scaling event notifications
   - Configure scaling metrics dashboard

3. **Optimize autoscaling configuration**:
   - Set scaling thresholds appropriate for workload characteristics
   - Adjust scaling behavior and cooldown periods
   - Balance cost and performance

4. **Integrate multiple autoscaling components**:
   - Use combination of HPA, CA, VPA
   - Prevent conflicts between components
   - Implement consistent scaling strategy

Issues with other options:
- **A. Allocate more resources to all pods**: This doesn't solve the root cause and can waste resources, failing to identify the actual cause of autoscaling issues.
- **B. Manually add nodes**: This is only a temporary solution and doesn't resolve fundamental issues with the autoscaling system.
- **D. Recreate the cluster**: This is an extreme measure that doesn't identify the root cause and causes unnecessary downtime and work.
</details>
### 7. What is the most effective troubleshooting approach when network policies are not working as expected in an Amazon EKS cluster?

A. Delete all network policies and use defaults
B. Check cluster CNI plugin, network policy configuration, logs, and events
C. Set hostNetwork: true for all pods
D. Reconfigure the cluster VPC

<details>
<summary>Show Answer</summary>

**Answer: B. Check cluster CNI plugin, network policy configuration, logs, and events**

**Explanation:**
When network policies are not working as expected in an Amazon EKS cluster, the most effective troubleshooting approach is to systematically check the cluster CNI plugin, network policy configuration, logs, and events. This approach helps identify and resolve the root cause of network policy issues.

**Key items to check:**

1. **Check CNI plugin**:
   - Type of CNI plugin in use (AWS VPC CNI, Calico, Cilium, etc.)
   - CNI plugin version and compatibility
   - Network policy support

2. **Check network policy configuration**:
   - Network policy syntax and selectors
   - Policy priority and conflicts
   - Namespace and label selectors

3. **Check logs and events**:
   - CNI plugin logs
   - Network policy controller logs
   - Related events and error messages

4. **Test network connectivity**:
   - Pod-to-pod connectivity test
   - Service connectivity test
   - External connectivity test

**Troubleshooting methods:**

1. **Check CNI plugin**:
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

2. **Check network policies**:
   ```bash
   # List network policies
   kubectl get networkpolicies --all-namespaces

   # Check specific network policy details
   kubectl describe networkpolicy <policy-name> -n <namespace>

   # Check network policy YAML
   kubectl get networkpolicy <policy-name> -n <namespace> -o yaml
   ```

3. **Check pod network information**:
   ```bash
   # Check pod IP and node information
   kubectl get pods -o wide

   # Check pod network interface
   kubectl exec -it <pod-name> -- ip addr

   # Check pod routing table
   kubectl exec -it <pod-name> -- ip route
   ```

4. **Test network connectivity**:
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

**Common network policy issues and solutions:**

1. **CNI plugin compatibility issues**:
   - **Symptom**: Network policies not being applied
   - **Cause**: CNI plugin in use doesn't support network policies
   - **Solution**:
     ```bash
     # Add Calico policy engine to AWS VPC CNI
     kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
     kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml

     # Or switch to Cilium
     helm repo add cilium https://helm.cilium.io/
     helm install cilium cilium/cilium --namespace kube-system
     ```

2. **Network policy selector issues**:
   - **Symptom**: Policies not applying to expected pods
   - **Cause**: Incorrect label selector or namespace selector
   - **Solution**:
     ```bash
     # Check pod labels
     kubectl get pods --show-labels

     # Modify network policy
     kubectl edit networkpolicy <policy-name> -n <namespace>
     ```

3. **Policy conflict issues**:
   - **Symptom**: Unexpected connection blocking or allowing
   - **Cause**: Conflicts or priority issues between multiple policies
   - **Solution**:
     ```bash
     # Review all network policies
     kubectl get networkpolicies --all-namespaces -o yaml

     # Simplify or reconfigure policies
     kubectl apply -f updated-network-policy.yaml
     ```

4. **CNI plugin bugs or configuration errors**:
   - **Symptom**: Intermittent connection issues or inconsistent behavior
   - **Cause**: CNI plugin bugs or incorrect configuration
   - **Solution**:
     ```bash
     # Update CNI plugin
     kubectl set image daemonset/aws-node -n kube-system aws-node=<new-image-version>

     # Check and modify CNI configuration
     kubectl edit configmap -n kube-system aws-node
     ```

**Best practices:**

1. **Systematic network policy design**:
   - Start with default deny policy
   - Explicitly allow only necessary connections
   - Use namespace and label-based policies

2. **Test and validate network policies**:
   - Test before applying policies
   - Automate connectivity testing
   - Gradual policy rollout

3. **Network monitoring and logging**:
   - Monitor network traffic
   - Log connection denials
   - Monitor network performance

4. **CNI plugin selection and configuration**:
   - Choose CNI appropriate for workload requirements
   - Keep up to date
   - Allocate appropriate resources

Issues with other options:
- **A. Delete all network policies and use defaults**: This creates security risks, removes necessary network isolation, and doesn't solve the root cause.
- **C. Set hostNetwork: true for all pods**: This bypasses network policies, creates security risks, and removes isolation between pods.
- **D. Reconfigure the cluster VPC**: This is an extreme measure, and most network policy issues are related to CNI and policy configuration within the cluster, not at the VPC level.
</details>
### 8. What is the most effective approach to troubleshoot Helm chart deployment issues in an Amazon EKS cluster?

A. Delete all Helm charts and reinstall
B. Recreate the cluster
C. Systematically check Helm version, chart configuration, dependencies, permissions, and logs
D. Manually deploy all resources

<details>
<summary>Show Answer</summary>

**Answer: C. Systematically check Helm version, chart configuration, dependencies, permissions, and logs**

**Explanation:**
The most effective approach to troubleshoot Helm chart deployment issues in an Amazon EKS cluster is to systematically check Helm version, chart configuration, dependencies, permissions, and logs. This approach helps identify and resolve the root cause of Helm deployment issues.

**Key items to check:**

1. **Check Helm version and compatibility**:
   - Helm client and Tiller (Helm 2) version
   - Kubernetes API version compatibility
   - EKS version compatibility

2. **Check chart configuration and values**:
   - Chart syntax errors
   - Values file configuration
   - Template rendering issues

3. **Check dependencies and repositories**:
   - Chart dependency availability
   - Repository accessibility
   - Chart version compatibility

4. **Check permissions and RBAC**:
   - Service account permissions
   - RBAC rules
   - Namespace access

5. **Check logs and events**:
   - Helm debug logs
   - Kubernetes events
   - Related pod logs

**Troubleshooting methods:**

1. **Check Helm version and configuration**:
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

2. **Validate and debug charts**:
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

3. **Check release status and history**:
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

4. **Check resources and events**:
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

5. **Check permissions and RBAC**:
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

**Common Helm deployment issues and solutions:**

1. **Chart syntax errors**:
   - **Symptom**: `helm install` or `helm template` command fails
   - **Cause**: YAML syntax errors, invalid template functions or variables
   - **Solution**:
     ```bash
     # Validate chart syntax
     helm lint ./my-chart

     # Check template rendering
     helm template ./my-chart --debug

     # Render template with specific values
     helm template ./my-chart --set key=value --debug
     ```

2. **Dependency issues**:
   - **Symptom**: Dependency errors during chart installation
   - **Cause**: Missing dependencies, version mismatches, or repository access issues
   - **Solution**:
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
   - **Symptom**: Permission denied errors
   - **Cause**: Insufficient RBAC permissions or incorrect service account configuration
   - **Solution**:
     ```bash
     # Create required RBAC resources
     kubectl apply -f rbac.yaml

     # Specify service account
     helm install my-release ./my-chart --service-account=my-service-account

     # Check permissions
     kubectl auth can-i create deployments --as=system:serviceaccount:<namespace>:<serviceaccount>
     ```

4. **Resource conflicts**:
   - **Symptom**: Resource already exists error
   - **Cause**: Resources from previous installation remain or name conflicts
   - **Solution**:
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
   - **Symptom**: Deployed application doesn't work as expected
   - **Cause**: Incorrect configuration values or missing required values
   - **Solution**:
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

**Best practices:**

1. **Systematic troubleshooting approach**:
   - Step-by-step verification and validation
   - Log and event analysis
   - Trace from symptom to cause

2. **Test and validate Helm charts**:
   - Validate charts before deployment
   - Test in test environment first
   - Include validation steps in CI/CD pipeline

3. **Version management and compatibility**:
   - Use compatible Helm and Kubernetes versions
   - Explicitly specify chart versions
   - Pin dependency versions

4. **Documentation and values management**:
   - Document chart values
   - Manage environment-specific values files
   - Apply security practices for sensitive values

Issues with other options:
- **A. Delete all Helm charts and reinstall**: This is an extreme measure that can cause data loss and doesn't solve the root cause.
- **B. Recreate the cluster**: This is a very extreme measure, and most Helm deployment issues are related to chart configuration or permissions, not cluster-level issues.
- **D. Manually deploy all resources**: This abandons the benefits of Helm and is error-prone and difficult to manage for complex applications.
</details>
### 9. What is the most effective approach to troubleshoot memory leak issues in an Amazon EKS cluster?

A. Restart all pods
B. Increase cluster node size
C. Profile memory usage, review container limits, analyze application code
D. Add more nodes

<details>
<summary>Show Answer</summary>

**Answer: C. Profile memory usage, review container limits, analyze application code**

**Explanation:**
The most effective approach to troubleshoot memory leak issues in an Amazon EKS cluster is a systematic approach including memory usage profiling, container limits review, and application code analysis. This method helps identify and resolve the root cause of memory leaks.

**Key items to check:**

1. **Memory usage profiling**:
   - Monitor memory usage at pod and node level
   - Analyze memory usage patterns over time
   - Identify signs of memory leaks

2. **Review container limits**:
   - Check memory request and limit settings
   - Analyze container OOM (Out of Memory) events
   - Optimize resource allocation

3. **Application code analysis**:
   - Review application internal memory usage patterns
   - Identify code with potential memory leaks
   - Use application profiling tools

4. **Review system components**:
   - kubelet memory management settings
   - Node system resource usage
   - Cluster component status

**Troubleshooting methods:**

1. **Monitor and analyze memory usage**:
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

2. **Check container limits and OOM events**:
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

3. **Application logs and profiling**:
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

4. **Check node and system resources**:
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

**Common memory leak issues and solutions:**

1. **Application memory leaks**:
   - **Symptom**: Memory usage continuously increases over time
   - **Cause**: Memory leaks in application code, lack of cache management
   - **Solution**:
     - Review and fix application code
     - Use memory profiling tools
     - Configure periodic garbage collection
     - Implement cache size limits and expiration policies

2. **Container memory limit issues**:
   - **Symptom**: Frequent OOM terminations, pod restarts
   - **Cause**: Inappropriate memory limit settings, large gap between resource requests and limits
   - **Solution**:
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
   - **Symptom**: Node instability, high memory usage by kubelet or other system components
   - **Cause**: kubelet configuration issues, system component bugs
   - **Solution**:
     - Optimize kubelet configuration
     - Update system components
     - Adjust node resource reservations

4. **Memory fragmentation issues**:
   - **Symptom**: OOM occurs despite sufficient total available memory
   - **Cause**: Memory fragmentation, large page allocation failures
   - **Solution**:
     - Schedule periodic node reboots
     - Distribute workloads with high memory pressure
     - Reduce node memory overcommit

**Best practices:**

1. **Systematic memory monitoring**:
   - Monitor memory at cluster, node, and pod levels
   - Track memory usage patterns over time
   - Set alerts for anomalies

2. **Set appropriate resource limits**:
   - Set memory requests and limits appropriate for workload characteristics
   - Maintain appropriate ratio between memory requests and limits
   - Regular resource usage review and adjustment

3. **Application optimization**:
   - Write memory-efficient code
   - Regular memory profiling and optimization
   - Implement appropriate caching strategies

4. **Cluster configuration optimization**:
   - Optimize node memory reservations
   - Appropriate kubelet memory management settings
   - Workload distribution and isolation

Issues with other options:
- **A. Restart all pods**: This is only a temporary solution and doesn't solve the root cause of memory leaks. The problem will recur once pods restart.
- **B. Increase cluster node size**: This doesn't solve the root cause and only hides the symptoms. Larger nodes will eventually run out of memory if memory leaks continue.
- **D. Add more nodes**: Similar to B, this only hides symptoms without solving the root cause. Memory leak issues will continue regardless of the number of nodes.
</details>
### 10. What is the most effective approach to troubleshoot DNS resolution issues in an Amazon EKS cluster?

A. Assign static IPs to all pods
B. Systematically check CoreDNS configuration, network policies, DNS policies, and connectivity
C. Use ExternalName for all services
D. Reconfigure the cluster VPC

<details>
<summary>Show Answer</summary>

**Answer: B. Systematically check CoreDNS configuration, network policies, DNS policies, and connectivity**

**Explanation:**
The most effective approach to troubleshoot DNS resolution issues in an Amazon EKS cluster is to systematically check CoreDNS configuration, network policies, DNS policies, and connectivity. This approach helps identify and resolve the root cause of DNS issues.

**Key items to check:**

1. **Check CoreDNS configuration and status**:
   - CoreDNS pod status and logs
   - CoreDNS ConfigMap configuration
   - CoreDNS service and endpoints

2. **Check network policies and connectivity**:
   - Network policies for DNS ports (53/UDP, 53/TCP)
   - Network connectivity between pods and CoreDNS
   - VPC DNS settings

3. **Check DNS policies and configuration**:
   - Pod DNS policy settings
   - DNS configuration options
   - Host namespace settings

4. **Check cluster and VPC configuration**:
   - EKS cluster DNS settings
   - VPC DNS attributes
   - DHCP option sets

**Troubleshooting methods:**

1. **Check CoreDNS status and configuration**:
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

2. **Test DNS resolution**:
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

3. **Check network policies and connectivity**:
   ```bash
   # Check DNS-related network policies
   kubectl get networkpolicies --all-namespaces

   # Test connection to CoreDNS
   kubectl run netcat-test --rm -it --image=busybox -- sh -c "nc -zv kube-dns.kube-system.svc.cluster.local 53"

   # Capture DNS packets
   kubectl run tcpdump-test --rm -it --image=nicolaka/netshoot -- tcpdump -i any port 53
   ```

4. **Check pod DNS configuration**:
   ```bash
   # Check pod DNS policy
   kubectl get pod <pod-name> -o jsonpath='{.spec.dnsPolicy}'

   # Check pod DNS configuration
   kubectl get pod <pod-name> -o jsonpath='{.spec.dnsConfig}'

   # Check pod internal resolv.conf
   kubectl exec -it <pod-name> -- cat /etc/resolv.conf
   ```

5. **Check VPC and cluster DNS settings**:
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

**Common DNS issues and solutions:**

1. **CoreDNS pod issues**:
   - **Symptom**: DNS queries fail, CoreDNS pods abnormal
   - **Cause**: CoreDNS pod crashes, resource shortage, configuration errors
   - **Solution**:
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
   - **Symptom**: DNS resolution fails only from specific namespaces or pods
   - **Cause**: Restrictive network policies blocking DNS traffic
   - **Solution**:
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

3. **DNS policy and configuration issues**:
   - **Symptom**: Only certain types of DNS queries fail
   - **Cause**: Inappropriate DNS policy or configuration
   - **Solution**:
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
   - **Symptom**: External domain resolution fails
   - **Cause**: VPC DNS attributes disabled or DHCP option set issues
   - **Solution**:
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
   - **Symptom**: Specific domain resolution fails or slow DNS resolution
   - **Cause**: CoreDNS configuration errors or non-optimized settings
   - **Solution**:
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

**Best practices:**

1. **CoreDNS monitoring and scaling**:
   - Monitor CoreDNS performance and status
   - Scale CoreDNS replicas according to cluster size
   - Allocate appropriate resources

2. **DNS caching and optimization**:
   - Appropriate TTL and cache settings
   - Implement node-level DNS caching
   - Consider application-level DNS caching

3. **Network policy design**:
   - Explicitly allow DNS traffic
   - Apply least privilege principle
   - Test and validate network policies

4. **DNS troubleshooting tools and processes**:
   - Prepare DNS troubleshooting tools and scripts
   - Establish systematic troubleshooting process
   - Monitor DNS-related events and logs

Issues with other options:
- **A. Assign static IPs to all pods**: This doesn't solve DNS issues, and pod IP allocation and DNS resolution are separate problems. Assigning static IPs to pods also goes against the dynamic nature of Kubernetes and increases management complexity.
- **C. Use ExternalName for all services**: This is only suitable for specific use cases and doesn't solve most DNS issues. ExternalName is used to provide aliases for external services and doesn't solve cluster internal DNS resolution issues.
- **D. Reconfigure the cluster VPC**: This is an extreme measure, and most DNS issues are related to DNS configuration within the cluster, not at the VPC level. VPC reconfiguration can cause unnecessary downtime and complexity.
</details>

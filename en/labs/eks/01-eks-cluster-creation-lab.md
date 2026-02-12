# EKS Cluster Creation Lab Guide

> **Difficulty**: Intermediate
> **Estimated Time**: 60 minutes
> **Last Updated**: February 2025

## Learning Objectives
- Create an EKS cluster using eksctl
- Access the cluster with kubectl and check its status
- Deploy a sample application
- Safely delete the cluster

## Prerequisites
- [ ] AWS account and AWS CLI configured (verify with `aws sts get-caller-identity`)
- [ ] eksctl installed (verify with `eksctl version`)
- [ ] kubectl installed
- [ ] Completed [EKS Cluster Creation](../../eks/02-eks-cluster-creation-part1.md) learning

> **Cost Warning**: Operating an EKS cluster incurs AWS costs. Be sure to delete the cluster after completing the lab.

---

## Exercise 1: eksctl Configuration Verification

### Steps

**Step 1.1: Check tool versions**
```bash
aws --version
eksctl version
kubectl version --client
```

**Step 1.2: Verify AWS credentials**
```bash
aws sts get-caller-identity
```

Expected output:
```json
{
    "UserId": "AIDACKCEVSQ6C2EXAMPLE",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-user"
}
```

**Step 1.3: Set default region**
```bash
export AWS_DEFAULT_REGION=ap-northeast-2
echo "Region: $AWS_DEFAULT_REGION"
```

<details>
<summary>Need a hint?</summary>

- Use `aws configure list` to check current configuration
- eksctl uses CloudFormation internally
- The IAM user needs EKS, EC2, CloudFormation, and IAM permissions
</details>

---

## Exercise 2: EKS Cluster Creation

### Steps

**Step 2.1: Write cluster configuration file**
```bash
cat > /tmp/eks-cluster.yaml << 'EOF'
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: lab-cluster
  region: ap-northeast-2
  version: "1.31"
managedNodeGroups:
  - name: workers
    instanceType: t3.medium
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    volumeSize: 20
EOF
```

**Step 2.2: Create cluster**
```bash
eksctl create cluster -f /tmp/eks-cluster.yaml
```

> Cluster creation takes 15-20 minutes.

**Step 2.3: Verify kubeconfig**
```bash
kubectl config current-context
kubectl cluster-info
```

### Verification
```bash
kubectl get nodes
# Should display 2 Ready nodes
```

---

## Exercise 3: Cluster Exploration

### Steps

**Step 3.1: Check node information**
```bash
kubectl get nodes -o wide
kubectl describe node $(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')
```

**Step 3.2: Check system components**
```bash
kubectl get pods -n kube-system
kubectl get svc -n kube-system
```

**Step 3.3: Check resource usage**
```bash
kubectl top nodes 2>/dev/null || echo "Metrics Server is not installed"
```

---

## Exercise 4: Sample App Deployment

### Steps

**Step 4.1: Deploy Nginx**
```bash
kubectl create deployment nginx --image=nginx:1.25 --replicas=2
kubectl expose deployment nginx --port=80 --type=LoadBalancer
kubectl wait --for=condition=available deployment/nginx --timeout=120s
```

**Step 4.2: Verify access**
```bash
# Check LoadBalancer External IP (ELB creation takes a few minutes)
kubectl get svc nginx -w
# Press Ctrl+C once EXTERNAL-IP is assigned

# Test access
ELB_URL=$(kubectl get svc nginx -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "ELB URL: $ELB_URL"
curl -s "$ELB_URL" | head -5
```

**Step 4.3: Scaling test**
```bash
kubectl scale deployment nginx --replicas=4
kubectl get pods -l app=nginx -o wide
```

<details>
<summary>Need a hint?</summary>

- It may take a few minutes for the ELB URL to propagate through DNS
- Use `kubectl get svc -w` to monitor EXTERNAL-IP assignment in real-time
- You can also verify in AWS Console under EC2 > Load Balancers
</details>

### Verification
```bash
kubectl get deployment nginx -o jsonpath='{.status.readyReplicas}'
# Output: 4
```

---

## Cleanup

> **Important**: Be sure to delete the cluster to prevent ongoing costs.

```bash
# 1. Clean up application (so LoadBalancer deletes the ELB)
kubectl delete svc nginx
kubectl delete deployment nginx

# 2. Wait for ELB deletion (about 1 minute)
sleep 60

# 3. Delete cluster
eksctl delete cluster -f /tmp/eks-cluster.yaml --wait

# 4. Clean up configuration file
rm -f /tmp/eks-cluster.yaml
```

## Troubleshooting

<details>
<summary>Cluster creation fails</summary>

- Check IAM permissions (AdministratorAccess or EKS-related policies required)
- Check VPC/subnet limits (per-region default VPC count limits)
- Get details with `eksctl utils describe-stacks --region=ap-northeast-2 --cluster=lab-cluster`
</details>

<details>
<summary>kubectl cannot connect to the cluster</summary>

Manually update kubeconfig:
```bash
aws eks update-kubeconfig --name lab-cluster --region ap-northeast-2
```
</details>

## Next Steps
- [EKS Cluster Creation Quiz](../../quizzes/eks/02-eks-cluster-creation-part1-quiz.md)
- Advanced topics: [EKS Networking](../../eks/03-eks-networking-part1.md)

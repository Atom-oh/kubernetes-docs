# Lab Guide

> **Last Updated**: February 22, 2026

This section provides hands-on lab guides for practicing Kubernetes and related technologies. Each lab includes step-by-step instructions and verification methods, allowing you to confirm what you learned in theory in a real environment.

## Lab List

| # | Lab | Difficulty | Prerequisites |
|---|-----|------------|---------------|
| 1 | [Linux Basics Lab](basics/01-linux-basics-lab.md) | Beginner | Linux terminal access |
| 2 | [Linux Advanced Skills Lab](basics/02-linux-advanced-lab.md) | Beginner | Linux basics completed |
| 3 | [Container Technology Lab](basics/03-container-technology-lab.md) | Beginner | Docker installed |
| 4 | [Pods and Workloads Lab](core/02-pods-and-workloads-lab.md) | Beginner | kubectl, K8s cluster |
| 5 | [Services and Networking Lab](core/03-services-networking-lab.md) | Intermediate | kubectl, K8s cluster |
| 6 | [Storage Lab](core/04-storage-lab.md) | Intermediate | kubectl, K8s cluster |
| 7 | [ConfigMap and Secret Lab](core/05-configuration-secrets-lab.md) | Beginner | kubectl, K8s cluster |
| 8 | [EKS Cluster Creation Lab](eks/01-eks-cluster-creation-lab.md) | Intermediate | AWS CLI, eksctl |
| 9 | [Observability E2E: Series Introduction](observability/README.md) | Advanced | AWS account, Terraform, Helm |
| 10 | [Observability E2E: Infrastructure Setup](observability/01-infrastructure-setup-lab.md) | Intermediate | Part 0 completed |
| 11 | [Observability E2E: Observability Stack](observability/02-observability-stack-lab.md) | Advanced | Part 1 completed |
| 12 | [Observability E2E: MSA Deployment and Canary](observability/03-msa-deployment-lab.md) | Advanced | Part 2 completed |
| 13 | [Observability E2E: Load Testing and Autoscaling](observability/04-load-testing-scaling-lab.md) | Intermediate | Part 3 completed |
| 14 | [Observability E2E: Alerting and AIOps](observability/05-alerting-aiops-lab.md) | Advanced | Part 4 completed |
| 15 | [Observability E2E: Distributed Tracing Analysis](observability/06-distributed-tracing-lab.md) | Advanced | Part 5 completed |

## Recommended Learning Path

1. **Basic Labs** (1→2→3): Learn Linux and container technology
2. **Core Labs** (4→7→5→6): Work with Kubernetes core resources
3. **EKS Labs** (8): Operate clusters in a real cloud environment
4. **Observability Labs** (9→10→11→12→13→14→15): Build and operate an end-to-end observability stack

## Lab Environment Setup

### Local Environment (for Basic/Container Labs)
- Linux terminal (WSL2, macOS Terminal, or Linux)
- Docker Desktop or Docker Engine

### Kubernetes Environment (for Core Labs)
```bash
# Install and start minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
minikube start

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install kubectl /usr/local/bin/kubectl
```

### AWS Environment (for EKS Labs)
- AWS account and AWS CLI configured
- eksctl installed

## Lab Tips

- Check the **Prerequisites** for each lab first
- After running commands, compare with the **Expected output** to verify correct operation
- Use **hints** when you get stuck
- After completing the lab, always run the commands in the **Cleanup** section to delete resources

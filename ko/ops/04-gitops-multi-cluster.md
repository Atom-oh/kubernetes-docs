# ArgoCD 멀티클러스터 배포와 IAM Identity Center

> **지원 버전**: ArgoCD 2.10+, EKS 1.28+, External Secrets Operator 0.9+
> **마지막 업데이트**: 2025년 6월

< [이전: CI 파이프라인](./03-ci-pipelines.md) | [목차](./README.md) | [다음: GitOps 자동화](./05-gitops-automation.md) >

---

이 문서에서는 ArgoCD를 사용하여 여러 EKS 클러스터에 애플리케이션을 배포하고, IAM Identity Center(AWS SSO)와 통합하여 중앙 집중식 인증 및 권한 관리를 구현하는 방법을 설명합니다.

## 목차

- [멀티클러스터 아키텍처](#멀티클러스터-아키텍처)
- [ArgoCD Terraform 설치](#argocd-terraform-설치)
- [NodePool GitOps 관리](#nodepool-gitops-관리)
- [ApplicationSet 전략](#applicationset-전략)
- [IAM Identity Center SSO](#iam-identity-center-sso)
- [시크릿 관리](#시크릿-관리)

---

## 멀티클러스터 아키텍처

멀티클러스터 GitOps 아키텍처는 중앙 관리 클러스터(Hub)에서 여러 워크로드 클러스터(Spoke)를 관리하는 Hub-Spoke 모델을 기반으로 합니다.

### Hub-Spoke 모델 개요

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Management Cluster (Hub)                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                            ArgoCD                                    │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │   │
│  │  │  API Server  │  │ Repo Server  │  │  Controller  │               │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │   │
│  │                                                                      │   │
│  │  ┌──────────────────────────────────────────────────┐               │   │
│  │  │              ApplicationSet Controller            │               │   │
│  │  └──────────────────────────────────────────────────┘               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
                    ▼                                 ▼
┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│     Blue Cluster (Spoke)        │   │     Green Cluster (Spoke)       │
│     ap-northeast-2a             │   │     ap-northeast-2c             │
│  ┌───────────────────────────┐  │   │  ┌───────────────────────────┐  │
│  │   Production Workloads    │  │   │  │   Production Workloads    │  │
│  ├───────────────────────────┤  │   │  ├───────────────────────────┤  │
│  │   - Frontend Apps         │  │   │  │   - Frontend Apps         │  │
│  │   - Backend Services      │  │   │  │   - Backend Services      │  │
│  │   - Data Processing       │  │   │  │   - Data Processing       │  │
│  └───────────────────────────┘  │   │  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │   │  ┌───────────────────────────┐  │
│  │   NodePools (Karpenter)   │  │   │  │   NodePools (Karpenter)   │  │
│  │   - general-purpose       │  │   │  │   - general-purpose       │  │
│  │   - compute-optimized     │  │   │  │   - compute-optimized     │  │
│  │   - data-processing       │  │   │  │   - data-processing       │  │
│  └───────────────────────────┘  │   │  └───────────────────────────┘  │
└─────────────────────────────────┘   └─────────────────────────────────┘
```

### Hub-Spoke 모델의 장점

| 장점 | 설명 |
|------|------|
| **중앙 집중식 관리** | 단일 ArgoCD 인스턴스에서 모든 클러스터의 배포를 관리하여 운영 복잡성 감소 |
| **일관된 배포** | ApplicationSet을 통해 여러 클러스터에 동일한 정책과 구성을 일관되게 적용 |
| **감사 추적** | 모든 배포 변경 사항이 Git에 기록되어 완전한 감사 추적 가능 |
| **권한 분리** | Hub 클러스터에서만 배포 권한을 관리하여 보안 강화 |
| **재해 복구** | 클러스터 간 독립성을 유지하면서 신속한 장애 복구 가능 |

### 클러스터 등록 패턴

```bash
# 클러스터 등록 스크립트
#!/bin/bash

# 변수 설정
MANAGEMENT_CLUSTER="management-cluster"
BLUE_CLUSTER="blue-cluster"
GREEN_CLUSTER="green-cluster"
ARGOCD_NAMESPACE="argocd"

# Management 클러스터 컨텍스트로 전환
kubectl config use-context ${MANAGEMENT_CLUSTER}

# ArgoCD CLI 로그인
argocd login argocd.example.com --username admin --password ${ARGOCD_PASSWORD}

# Blue 클러스터 등록
aws eks update-kubeconfig --name ${BLUE_CLUSTER} --region ap-northeast-2 --alias ${BLUE_CLUSTER}
argocd cluster add ${BLUE_CLUSTER} \
  --name blue-production \
  --label environment=production \
  --label region=ap-northeast-2 \
  --label zone=ap-northeast-2a

# Green 클러스터 등록
aws eks update-kubeconfig --name ${GREEN_CLUSTER} --region ap-northeast-2 --alias ${GREEN_CLUSTER}
argocd cluster add ${GREEN_CLUSTER} \
  --name green-production \
  --label environment=production \
  --label region=ap-northeast-2 \
  --label zone=ap-northeast-2c

# 등록된 클러스터 확인
argocd cluster list
```

---

## ArgoCD Terraform 설치

Terraform을 사용하여 고가용성(HA) ArgoCD를 설치하고 구성합니다.

### Helm Provider 설정

```hcl
# providers.tf - Terraform 프로바이더 설정

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.25"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
  }

  backend "s3" {
    bucket         = "terraform-state-bucket"
    key            = "argocd/terraform.tfstate"
    region         = "ap-northeast-2"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = "terraform"
      Project     = "gitops-platform"
    }
  }
}

# EKS 클러스터 데이터 소스
data "aws_eks_cluster" "management" {
  name = var.management_cluster_name
}

data "aws_eks_cluster_auth" "management" {
  name = var.management_cluster_name
}

provider "kubernetes" {
  host                   = data.aws_eks_cluster.management.endpoint
  cluster_ca_certificate = base64decode(data.aws_eks_cluster.management.certificate_authority[0].data)
  token                  = data.aws_eks_cluster_auth.management.token
}

provider "helm" {
  kubernetes {
    host                   = data.aws_eks_cluster.management.endpoint
    cluster_ca_certificate = base64decode(data.aws_eks_cluster.management.certificate_authority[0].data)
    token                  = data.aws_eks_cluster_auth.management.token
  }
}
```

### HA ArgoCD 배포

```hcl
# argocd.tf - ArgoCD HA 배포

locals {
  argocd_namespace = "argocd"
  argocd_version   = "7.3.6"  # Helm 차트 버전 (ArgoCD 2.12.x)
}

# ArgoCD 네임스페이스 생성
resource "kubernetes_namespace" "argocd" {
  metadata {
    name = local.argocd_namespace

    labels = {
      "app.kubernetes.io/managed-by" = "terraform"
      "istio-injection"              = "disabled"
    }
  }
}

# ArgoCD Helm 설치
resource "helm_release" "argocd" {
  name       = "argocd"
  namespace  = kubernetes_namespace.argocd.metadata[0].name
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"
  version    = local.argocd_version

  timeout = 600
  wait    = true

  values = [
    yamlencode({
      # 전역 설정
      global = {
        domain = var.argocd_domain
        logging = {
          level  = "info"
          format = "json"
        }
      }

      # HA 설정 - Controller
      controller = {
        replicas = 2

        resources = {
          limits = {
            cpu    = "2"
            memory = "2Gi"
          }
          requests = {
            cpu    = "500m"
            memory = "512Mi"
          }
        }

        # Controller 설정
        env = [
          {
            name  = "ARGOCD_CONTROLLER_REPLICAS"
            value = "2"
          }
        ]

        metrics = {
          enabled = true
          serviceMonitor = {
            enabled = true
          }
        }

        # Pod Anti-Affinity (HA)
        affinity = {
          podAntiAffinity = {
            preferredDuringSchedulingIgnoredDuringExecution = [
              {
                weight = 100
                podAffinityTerm = {
                  labelSelector = {
                    matchLabels = {
                      "app.kubernetes.io/name" = "argocd-application-controller"
                    }
                  }
                  topologyKey = "kubernetes.io/hostname"
                }
              }
            ]
          }
        }
      }

      # Server 설정
      server = {
        replicas = 3

        autoscaling = {
          enabled     = true
          minReplicas = 3
          maxReplicas = 10
          targetCPUUtilizationPercentage = 70
        }

        resources = {
          limits = {
            cpu    = "1"
            memory = "1Gi"
          }
          requests = {
            cpu    = "200m"
            memory = "256Mi"
          }
        }

        # Ingress 설정
        ingress = {
          enabled = true
          ingressClassName = "alb"
          annotations = {
            "alb.ingress.kubernetes.io/scheme"       = "internet-facing"
            "alb.ingress.kubernetes.io/target-type"  = "ip"
            "alb.ingress.kubernetes.io/listen-ports" = "[{\"HTTPS\":443}]"
            "alb.ingress.kubernetes.io/ssl-redirect" = "443"
            "alb.ingress.kubernetes.io/certificate-arn" = var.acm_certificate_arn
            "alb.ingress.kubernetes.io/healthcheck-path" = "/healthz"
          }
          hosts = [var.argocd_domain]
          tls = [
            {
              hosts = [var.argocd_domain]
            }
          ]
        }

        # HTTPS 비활성화 (ALB에서 TLS 종료)
        extraArgs = [
          "--insecure"
        ]

        metrics = {
          enabled = true
          serviceMonitor = {
            enabled = true
          }
        }

        # Pod Anti-Affinity
        affinity = {
          podAntiAffinity = {
            preferredDuringSchedulingIgnoredDuringExecution = [
              {
                weight = 100
                podAffinityTerm = {
                  labelSelector = {
                    matchLabels = {
                      "app.kubernetes.io/name" = "argocd-server"
                    }
                  }
                  topologyKey = "kubernetes.io/hostname"
                }
              }
            ]
          }
        }
      }

      # Repo Server 설정
      repoServer = {
        replicas = 3

        autoscaling = {
          enabled     = true
          minReplicas = 3
          maxReplicas = 10
          targetCPUUtilizationPercentage = 70
        }

        resources = {
          limits = {
            cpu    = "2"
            memory = "2Gi"
          }
          requests = {
            cpu    = "500m"
            memory = "512Mi"
          }
        }

        # Git 자격 증명 볼륨
        volumes = [
          {
            name = "custom-tools"
            emptyDir = {}
          }
        ]

        volumeMounts = [
          {
            name      = "custom-tools"
            mountPath = "/custom-tools"
          }
        ]

        # Init Container (Helm, Kustomize 등 도구 설치)
        initContainers = [
          {
            name  = "download-tools"
            image = "alpine:3.18"
            command = ["sh", "-c"]
            args = [<<-EOT
              # Helm 설치
              wget https://get.helm.sh/helm-v3.14.0-linux-amd64.tar.gz
              tar -xvf helm-v3.14.0-linux-amd64.tar.gz
              mv linux-amd64/helm /custom-tools/helm

              # AWS CLI 설치 (ECR 인증용)
              apk add --no-cache aws-cli

              chmod +x /custom-tools/*
              EOT
            ]
            volumeMounts = [
              {
                name      = "custom-tools"
                mountPath = "/custom-tools"
              }
            ]
          }
        ]

        metrics = {
          enabled = true
          serviceMonitor = {
            enabled = true
          }
        }
      }

      # Redis HA 설정
      redis-ha = {
        enabled = true

        replicas = 3

        haproxy = {
          enabled  = true
          replicas = 3
        }

        redis = {
          resources = {
            limits = {
              cpu    = "500m"
              memory = "512Mi"
            }
            requests = {
              cpu    = "100m"
              memory = "128Mi"
            }
          }
        }

        exporter = {
          enabled = true
        }
      }

      # 단일 Redis 비활성화 (redis-ha 사용)
      redis = {
        enabled = false
      }

      # ApplicationSet Controller
      applicationSet = {
        replicas = 2

        resources = {
          limits = {
            cpu    = "500m"
            memory = "512Mi"
          }
          requests = {
            cpu    = "100m"
            memory = "128Mi"
          }
        }

        metrics = {
          enabled = true
          serviceMonitor = {
            enabled = true
          }
        }
      }

      # Notifications Controller
      notifications = {
        enabled = true

        resources = {
          limits = {
            cpu    = "200m"
            memory = "256Mi"
          }
          requests = {
            cpu    = "50m"
            memory = "64Mi"
          }
        }

        metrics = {
          enabled = true
          serviceMonitor = {
            enabled = true
          }
        }
      }

      # Dex (OIDC) 비활성화 - IAM Identity Center 사용
      dex = {
        enabled = false
      }

      # 설정 ConfigMap
      configs = {
        cm = {
          # 애플리케이션 재동기화 주기
          "timeout.reconciliation" = "180s"

          # 리소스 추적 방법
          "application.resourceTrackingMethod" = "annotation"

          # 헬스 체크 사용자 정의
          "resource.customizations.health.argoproj.io_Application" = <<-EOT
            hs = {}
            hs.status = "Healthy"
            hs.message = ""
            if obj.status ~= nil then
              if obj.status.health ~= nil then
                hs.status = obj.status.health.status
                hs.message = obj.status.health.message
              end
            end
            return hs
            EOT
        }

        params = {
          # 서버 설정
          "server.insecure" = true

          # Controller 설정
          "controller.status.processors"   = "20"
          "controller.operation.processors" = "10"
          "controller.repo.server.timeout.seconds" = "180"

          # Repo Server 설정
          "reposerver.parallelism.limit" = "10"
        }

        # 저장소 자격 증명 템플릿
        credentialTemplates = {
          github-https = {
            url      = "https://github.com/myorg"
            username = "git"
            password = var.github_token
          }
        }

        # 저장소 등록
        repositories = {
          app-repo = {
            url  = "https://github.com/myorg/app-manifests"
            name = "app-manifests"
          }
          infra-repo = {
            url  = "https://github.com/myorg/infra-manifests"
            name = "infra-manifests"
          }
        }
      }

      # RBAC 설정
      rbac = {
        create = true

        policy = {
          csv = <<-EOT
            # 관리자 역할
            p, role:admin, applications, *, */*, allow
            p, role:admin, clusters, *, *, allow
            p, role:admin, repositories, *, *, allow
            p, role:admin, projects, *, *, allow
            p, role:admin, logs, *, *, allow
            p, role:admin, exec, *, *, allow

            # 개발자 역할
            p, role:developer, applications, get, */*, allow
            p, role:developer, applications, sync, */*, allow
            p, role:developer, applications, action/*, */*, allow
            p, role:developer, logs, get, */*, allow
            p, role:developer, repositories, get, *, allow
            p, role:developer, projects, get, *, allow

            # 읽기 전용 역할
            p, role:readonly, applications, get, */*, allow
            p, role:readonly, logs, get, */*, allow
            p, role:readonly, repositories, get, *, allow
            p, role:readonly, projects, get, *, allow
            p, role:readonly, clusters, get, *, allow

            # 그룹 매핑 (IAM Identity Center)
            g, PlatformAdmins, role:admin
            g, Developers, role:developer
            g, Viewers, role:readonly
            EOT

          default = "role:readonly"
        }
      }
    })
  ]
}
```

### 변수 정의

```hcl
# variables.tf

variable "aws_region" {
  description = "AWS 리전"
  type        = string
  default     = "ap-northeast-2"
}

variable "environment" {
  description = "환경 이름"
  type        = string
  default     = "production"
}

variable "management_cluster_name" {
  description = "Management EKS 클러스터 이름"
  type        = string
}

variable "argocd_domain" {
  description = "ArgoCD 도메인"
  type        = string
}

variable "acm_certificate_arn" {
  description = "ACM 인증서 ARN"
  type        = string
}

variable "github_token" {
  description = "GitHub Personal Access Token"
  type        = string
  sensitive   = true
}
```

---

## NodePool GitOps 관리

EKS Auto Mode의 NodePool은 Kubernetes CRD(Custom Resource Definition)로 정의되므로, Terraform이 아닌 ArgoCD를 통해 GitOps 방식으로 관리하는 것이 적합합니다. 이를 통해 NodePool 변경 사항을 Git에서 추적하고, 여러 클러스터에 일관되게 적용할 수 있습니다.

### 왜 NodePool을 ArgoCD로 관리하는가?

| Terraform 관리 | ArgoCD 관리 |
|---------------|-------------|
| 인프라 프로비저닝에 적합 | Kubernetes 리소스 관리에 적합 |
| 상태 파일 관리 필요 | Git이 단일 진실의 원천 |
| 수동 `terraform apply` 필요 | 자동 동기화 및 자체 치유 |
| 클러스터별 별도 관리 | 멀티클러스터 일관성 유지 |

### Blue 클러스터 NodePool 예제

```yaml
# manifests/nodepools/blue-cluster/general-purpose.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: general-purpose
  labels:
    cluster: blue
    environment: production
    managed-by: argocd
spec:
  template:
    metadata:
      labels:
        cluster: blue
        nodepool: general-purpose
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c", "m", "r"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]
        - key: topology.kubernetes.io/zone
          operator: In
          values: ["ap-northeast-2a"]  # Blue 클러스터 - AZ-a

      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default

  limits:
    cpu: 1000
    memory: 2000Gi

  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
      - nodes: "20%"

  weight: 100

---
# manifests/nodepools/blue-cluster/compute-optimized.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: compute-optimized
  labels:
    cluster: blue
    environment: production
    managed-by: argocd
spec:
  template:
    metadata:
      labels:
        cluster: blue
        nodepool: compute-optimized
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c"]
        - key: karpenter.k8s.aws/instance-family
          operator: In
          values: ["c7i", "c7a", "c6i"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["xlarge", "2xlarge", "4xlarge"]
        - key: topology.kubernetes.io/zone
          operator: In
          values: ["ap-northeast-2a"]

      taints:
        - key: workload-type
          value: compute-intensive
          effect: NoSchedule

      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default

  limits:
    cpu: 500
    memory: 1000Gi

  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 10m
    budgets:
      - nodes: "10%"

  weight: 50
```

### Green 클러스터 NodePool 예제

```yaml
# manifests/nodepools/green-cluster/general-purpose.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: general-purpose
  labels:
    cluster: green
    environment: production
    managed-by: argocd
spec:
  template:
    metadata:
      labels:
        cluster: green
        nodepool: general-purpose
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c", "m", "r"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]
        - key: topology.kubernetes.io/zone
          operator: In
          values: ["ap-northeast-2c"]  # Green 클러스터 - AZ-c

      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default

  limits:
    cpu: 1000
    memory: 2000Gi

  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
      - nodes: "20%"

  weight: 100

---
# manifests/nodepools/green-cluster/compute-optimized.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: compute-optimized
  labels:
    cluster: green
    environment: production
    managed-by: argocd
spec:
  template:
    metadata:
      labels:
        cluster: green
        nodepool: compute-optimized
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c"]
        - key: karpenter.k8s.aws/instance-family
          operator: In
          values: ["c7i", "c7a", "c6i"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["xlarge", "2xlarge", "4xlarge"]
        - key: topology.kubernetes.io/zone
          operator: In
          values: ["ap-northeast-2c"]

      taints:
        - key: workload-type
          value: compute-intensive
          effect: NoSchedule

      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default

  limits:
    cpu: 500
    memory: 1000Gi

  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 10m
    budgets:
      - nodes: "10%"

  weight: 50
```

### Data Processing NodePool (전용)

```yaml
# manifests/nodepools/shared/data-nodepool.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: data-processing
  labels:
    environment: production
    workload-type: data
    managed-by: argocd
spec:
  template:
    metadata:
      labels:
        nodepool: data-processing
        workload-type: data
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]  # 데이터 워크로드는 On-Demand만
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["r", "i"]  # 메모리/스토리지 최적화
        - key: karpenter.k8s.aws/instance-family
          operator: In
          values: ["r7i", "r7a", "i4i", "im4gn"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["2xlarge", "4xlarge", "8xlarge"]
        # Zone Affinity는 클러스터별로 오버라이드

      taints:
        - key: workload-type
          value: data-processing
          effect: NoSchedule

      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: data-optimized

  limits:
    cpu: 200
    memory: 800Gi

  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30m  # 데이터 워크로드는 더 긴 대기 시간
    budgets:
      - nodes: "5%"  # 보수적인 중단 예산

  weight: 30

---
# manifests/nodepools/shared/data-nodeclass.yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: data-optimized
spec:
  amiSelectorTerms:
    - alias: al2023@latest

  blockDeviceMappings:
    - deviceName: /dev/xvda
      rootVolume: true
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
        iops: 4000
        throughput: 250
        encrypted: true
        deleteOnTermination: true

    # 추가 데이터 볼륨
    - deviceName: /dev/xvdb
      ebs:
        volumeSize: 500Gi
        volumeType: gp3
        iops: 10000
        throughput: 500
        encrypted: true
        deleteOnTermination: true

  instanceStorePolicy: RAID0

  tags:
    Purpose: data-processing
    DataClassification: confidential
```

### NodePool 관리용 ArgoCD Application

```yaml
# applications/nodepool-management.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: nodepool-blue-cluster
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: infrastructure
  source:
    repoURL: https://github.com/myorg/infra-manifests
    targetRevision: main
    path: manifests/nodepools/blue-cluster

  destination:
    server: https://blue-cluster.ap-northeast-2.eks.amazonaws.com
    namespace: kube-system

  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
      - CreateNamespace=false
      - ServerSideApply=true
      - RespectIgnoreDifferences=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m

---
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: nodepool-green-cluster
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: infrastructure
  source:
    repoURL: https://github.com/myorg/infra-manifests
    targetRevision: main
    path: manifests/nodepools/green-cluster

  destination:
    server: https://green-cluster.ap-northeast-2.eks.amazonaws.com
    namespace: kube-system

  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - ServerSideApply=true
```

---

## ApplicationSet 전략

ApplicationSet은 여러 클러스터나 환경에 애플리케이션을 효율적으로 배포하기 위한 ArgoCD의 기능입니다. 다양한 Generator를 사용하여 동적으로 Application을 생성합니다.

### Cluster Generator

등록된 모든 클러스터 또는 특정 레이블의 클러스터에 애플리케이션을 배포합니다.

```yaml
# applicationsets/cluster-generator.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: platform-services
  namespace: argocd
spec:
  generators:
    # 모든 프로덕션 클러스터에 배포
    - clusters:
        selector:
          matchLabels:
            environment: production

  template:
    metadata:
      name: '{{name}}-platform-services'
      labels:
        cluster: '{{name}}'
        environment: '{{metadata.labels.environment}}'
    spec:
      project: platform
      source:
        repoURL: https://github.com/myorg/platform-manifests
        targetRevision: main
        path: platform-services/overlays/{{metadata.labels.environment}}
        kustomize:
          namePrefix: '{{name}}-'

      destination:
        server: '{{server}}'
        namespace: platform

      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
          - ServerSideApply=true

---
# 특정 클러스터 그룹에 배포
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: monitoring-stack
  namespace: argocd
spec:
  generators:
    - clusters:
        selector:
          matchExpressions:
            - key: environment
              operator: In
              values: ["production", "staging"]
            - key: region
              operator: In
              values: ["ap-northeast-2"]

  template:
    metadata:
      name: '{{name}}-monitoring'
    spec:
      project: observability
      source:
        repoURL: https://github.com/myorg/observability-manifests
        targetRevision: main
        path: monitoring
        helm:
          valueFiles:
            - values-{{metadata.labels.environment}}.yaml

      destination:
        server: '{{server}}'
        namespace: monitoring

      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

### Git Generator

Git 저장소의 디렉토리 구조 또는 파일을 기반으로 Application을 생성합니다.

```yaml
# applicationsets/git-directory-generator.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: microservices
  namespace: argocd
spec:
  generators:
    # 디렉토리 기반 생성
    - git:
        repoURL: https://github.com/myorg/app-manifests
        revision: main
        directories:
          - path: apps/*
          - path: apps/*/overlays/production
            exclude: true  # 직접 경로는 제외

  template:
    metadata:
      name: '{{path.basename}}'
      labels:
        app: '{{path.basename}}'
    spec:
      project: applications
      source:
        repoURL: https://github.com/myorg/app-manifests
        targetRevision: main
        path: '{{path}}/overlays/production'

      destination:
        server: https://kubernetes.default.svc
        namespace: '{{path.basename}}'

      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true

---
# 파일 기반 생성 (JSON/YAML 설정 파일)
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: apps-from-config
  namespace: argocd
spec:
  generators:
    - git:
        repoURL: https://github.com/myorg/app-manifests
        revision: main
        files:
          - path: config/apps/*.yaml

  template:
    metadata:
      name: '{{name}}'
      labels:
        team: '{{team}}'
        tier: '{{tier}}'
    spec:
      project: '{{project}}'
      source:
        repoURL: '{{repoURL}}'
        targetRevision: '{{targetRevision}}'
        path: '{{path}}'
        helm:
          valueFiles:
            - '{{valuesFile}}'

      destination:
        server: '{{destinationServer}}'
        namespace: '{{namespace}}'

      syncPolicy:
        automated:
          prune: '{{prune}}'
          selfHeal: '{{selfHeal}}'
```

```yaml
# config/apps/user-service.yaml (예제 설정 파일)
name: user-service
team: backend
tier: api
project: applications
repoURL: https://github.com/myorg/user-service
targetRevision: main
path: deploy/helm
valuesFile: values-production.yaml
destinationServer: https://kubernetes.default.svc
namespace: backend
prune: true
selfHeal: true
```

### Matrix Generator

여러 Generator를 조합하여 클러스터 × 애플리케이션 매트릭스를 생성합니다.

```yaml
# applicationsets/matrix-generator.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: multi-cluster-apps
  namespace: argocd
spec:
  generators:
    # Matrix: 클러스터 × 앱
    - matrix:
        generators:
          # 첫 번째: 클러스터 목록
          - clusters:
              selector:
                matchLabels:
                  environment: production

          # 두 번째: 앱 목록 (Git 디렉토리)
          - git:
              repoURL: https://github.com/myorg/app-manifests
              revision: main
              directories:
                - path: apps/*

  template:
    metadata:
      name: '{{name}}-{{path.basename}}'
      labels:
        cluster: '{{name}}'
        app: '{{path.basename}}'
    spec:
      project: applications
      source:
        repoURL: https://github.com/myorg/app-manifests
        targetRevision: main
        path: '{{path}}/overlays/{{metadata.labels.environment}}'
        kustomize:
          commonAnnotations:
            cluster: '{{name}}'
            zone: '{{metadata.labels.zone}}'

      destination:
        server: '{{server}}'
        namespace: '{{path.basename}}'

      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
          - ServerSideApply=true

---
# 중첩 Matrix (클러스터 × 환경 × 앱)
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: nested-matrix-apps
  namespace: argocd
spec:
  generators:
    - matrix:
        generators:
          - clusters:
              selector:
                matchLabels:
                  type: workload

          - matrix:
              generators:
                - list:
                    elements:
                      - environment: staging
                        namespace: staging
                      - environment: production
                        namespace: prod

                - git:
                    repoURL: https://github.com/myorg/app-manifests
                    revision: main
                    directories:
                      - path: microservices/*

  template:
    metadata:
      name: '{{name}}-{{environment}}-{{path.basename}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/myorg/app-manifests
        targetRevision: main
        path: '{{path}}/overlays/{{environment}}'

      destination:
        server: '{{server}}'
        namespace: '{{namespace}}-{{path.basename}}'
```

### PR Generator (프리뷰 환경)

Pull Request 기반으로 프리뷰 환경을 자동 생성합니다.

```yaml
# applicationsets/pr-generator.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: preview-environments
  namespace: argocd
spec:
  generators:
    - pullRequest:
        github:
          owner: myorg
          repo: myapp
          tokenRef:
            secretName: github-token
            key: token
          labels:
            - preview
            - deploy
        requeueAfterSeconds: 60

  template:
    metadata:
      name: 'preview-{{branch_slug}}-{{number}}'
      labels:
        app: myapp
        type: preview
        pr: '{{number}}'
      annotations:
        notifications.argoproj.io/subscribe.on-sync-succeeded.slack: preview-notifications
    spec:
      project: previews
      source:
        repoURL: https://github.com/myorg/myapp
        targetRevision: '{{head_sha}}'
        path: deploy/preview
        kustomize:
          namePrefix: 'pr-{{number}}-'
          commonLabels:
            app.kubernetes.io/instance: 'pr-{{number}}'
          images:
            - 'myapp={{head_short_sha}}'

      destination:
        server: https://kubernetes.default.svc
        namespace: 'preview-{{number}}'

      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true

      # TTL: PR 병합/닫힘 후 자동 삭제
      info:
        - name: PR
          value: 'https://github.com/myorg/myapp/pull/{{number}}'

---
# 프리뷰 환경 정리를 위한 Project 설정
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: previews
  namespace: argocd
spec:
  description: Preview environments for pull requests
  sourceRepos:
    - 'https://github.com/myorg/*'

  destinations:
    - namespace: 'preview-*'
      server: https://kubernetes.default.svc

  clusterResourceWhitelist:
    - group: ''
      kind: Namespace

  orphanedResources:
    warn: true
    ignore:
      - group: ''
        kind: ConfigMap
        name: kube-root-ca.crt
```

### Sync Wave 기반 배포

`sync-wave` 어노테이션을 사용하여 리소스 배포 순서를 제어합니다.

```yaml
# manifests/app/base/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  annotations:
    argocd.argoproj.io/sync-wave: "3"  # 마지막에 배포
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    # ...

---
# manifests/app/base/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: myapp-config
  annotations:
    argocd.argoproj.io/sync-wave: "1"  # 첫 번째로 생성
data:
  # ...

---
# manifests/app/base/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp
  annotations:
    argocd.argoproj.io/sync-wave: "2"  # 두 번째로 생성
spec:
  # ...

---
# manifests/app/base/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myapp
  annotations:
    argocd.argoproj.io/sync-wave: "4"  # Deployment 후 생성
spec:
  # ...
```

```yaml
# applicationsets/wave-based-deployment.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: staged-rollout
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - cluster: staging
            server: https://staging.eks.amazonaws.com
            wave: "1"
          - cluster: production-blue
            server: https://blue.eks.amazonaws.com
            wave: "2"
          - cluster: production-green
            server: https://green.eks.amazonaws.com
            wave: "3"

  template:
    metadata:
      name: 'myapp-{{cluster}}'
      annotations:
        argocd.argoproj.io/sync-wave: '{{wave}}'
    spec:
      project: applications
      source:
        repoURL: https://github.com/myorg/app-manifests
        targetRevision: main
        path: myapp/overlays/{{cluster}}

      destination:
        server: '{{server}}'
        namespace: myapp

      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - ApplyOutOfSyncOnly=true
```

---

## IAM Identity Center SSO

IAM Identity Center(이전 AWS SSO)를 ArgoCD와 통합하여 중앙 집중식 인증 및 권한 관리를 구현합니다.

### SAML 2.0 구성

```hcl
# iam-identity-center.tf - SAML Provider 설정

# SAML 메타데이터 다운로드 URL
# IAM Identity Center Console -> Settings -> Identity source -> SAML 2.0 metadata file

# SAML Identity Provider 생성
resource "aws_iam_saml_provider" "identity_center" {
  name                   = "IAMIdentityCenter"
  saml_metadata_document = file("${path.module}/saml-metadata.xml")

  tags = {
    Purpose = "ArgoCD SSO Integration"
  }
}

# ArgoCD용 IAM 역할 (SAML 인증용)
resource "aws_iam_role" "argocd_sso" {
  name = "ArgoCD-SSO-Role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_saml_provider.identity_center.arn
        }
        Action = "sts:AssumeRoleWithSAML"
        Condition = {
          StringEquals = {
            "SAML:aud" = "https://signin.aws.amazon.com/saml"
          }
        }
      }
    ]
  })
}
```

### ArgoCD SAML 설정

```yaml
# argocd-cm ConfigMap - SAML/OIDC 설정
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  # ArgoCD 서버 URL
  url: https://argocd.example.com

  # SAML 설정 (IAM Identity Center)
  dex.config: |
    connectors:
      - type: saml
        id: aws-sso
        name: AWS IAM Identity Center
        config:
          # IAM Identity Center SAML 엔드포인트
          ssoURL: https://portal.sso.ap-northeast-2.amazonaws.com/saml/assertion/xxxxxxxxxxxx

          # ArgoCD SAML Callback URL
          # IAM Identity Center 애플리케이션에 등록 필요
          redirectURI: https://argocd.example.com/api/dex/callback

          # Entity ID (IAM Identity Center에서 설정)
          entityIssuer: https://argocd.example.com/api/dex/callback

          # SAML 응답 서명 검증용 CA 인증서
          caData: |
            -----BEGIN CERTIFICATE-----
            MIIDXTCCAkWgAwIBAgIJAJC1...
            -----END CERTIFICATE-----

          # 사용자 속성 매핑
          usernameAttr: email
          emailAttr: email
          groupsAttr: groups

          # 그룹 구분자 (IAM Identity Center에서 그룹을 ','로 구분)
          groupsDelim: ","

  # OIDC 설정 (대안)
  oidc.config: |
    name: AWS IAM Identity Center
    issuer: https://portal.sso.ap-northeast-2.amazonaws.com/saml/assertion/xxxxxxxxxxxx
    clientID: arn:aws:sso::123456789012:application/ssoins-xxxxxxxxxx/apl-xxxxxxxxxx
    clientSecret: $oidc.aws-sso.clientSecret
    requestedScopes:
      - openid
      - email
      - groups
    requestedIDTokenClaims:
      groups:
        essential: true
```

```yaml
# argocd-secret - OIDC 클라이언트 시크릿
apiVersion: v1
kind: Secret
metadata:
  name: argocd-secret
  namespace: argocd
type: Opaque
stringData:
  oidc.aws-sso.clientSecret: "your-oidc-client-secret"
```

### 그룹-역할 매핑

```yaml
# argocd-rbac-cm ConfigMap - RBAC 설정
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  policy.default: role:readonly
  scopes: '[groups, email]'

  policy.csv: |
    # ========================================
    # 역할 정의
    # ========================================

    # 관리자 역할 - 모든 권한
    p, role:admin, applications, *, */*, allow
    p, role:admin, clusters, *, *, allow
    p, role:admin, repositories, *, *, allow
    p, role:admin, projects, *, *, allow
    p, role:admin, accounts, *, *, allow
    p, role:admin, gpgkeys, *, *, allow
    p, role:admin, logs, *, *, allow
    p, role:admin, exec, *, *, allow
    p, role:admin, extensions, *, *, allow

    # 개발자 역할 - 앱 관리 권한
    p, role:developer, applications, get, */*, allow
    p, role:developer, applications, create, */*, allow
    p, role:developer, applications, update, */*, allow
    p, role:developer, applications, delete, */*, allow
    p, role:developer, applications, sync, */*, allow
    p, role:developer, applications, override, */*, allow
    p, role:developer, applications, action/*, */*, allow
    p, role:developer, logs, get, */*, allow
    p, role:developer, repositories, get, *, allow
    p, role:developer, projects, get, *, allow
    p, role:developer, clusters, get, *, allow

    # SRE 역할 - 인프라 관리 권한
    p, role:sre, applications, *, */*, allow
    p, role:sre, clusters, get, *, allow
    p, role:sre, repositories, get, *, allow
    p, role:sre, projects, get, *, allow
    p, role:sre, logs, get, */*, allow
    p, role:sre, exec, create, */*, allow

    # 읽기 전용 역할
    p, role:readonly, applications, get, */*, allow
    p, role:readonly, logs, get, */*, allow
    p, role:readonly, repositories, get, *, allow
    p, role:readonly, projects, get, *, allow
    p, role:readonly, clusters, get, *, allow

    # ========================================
    # IAM Identity Center 그룹 매핑
    # ========================================

    # Platform Admins 그룹 -> admin 역할
    g, PlatformAdmins, role:admin

    # SRE Team 그룹 -> sre 역할
    g, SRETeam, role:sre

    # Developers 그룹 -> developer 역할
    g, Developers, role:developer

    # Viewers 그룹 -> readonly 역할
    g, Viewers, role:readonly

    # ========================================
    # 프로젝트별 세분화된 권한
    # ========================================

    # Backend 팀 - backend 프로젝트만 관리
    p, role:backend-dev, applications, *, backend/*, allow
    p, role:backend-dev, logs, get, backend/*, allow
    g, BackendTeam, role:backend-dev

    # Frontend 팀 - frontend 프로젝트만 관리
    p, role:frontend-dev, applications, *, frontend/*, allow
    p, role:frontend-dev, logs, get, frontend/*, allow
    g, FrontendTeam, role:frontend-dev

    # Data 팀 - data 프로젝트만 관리
    p, role:data-dev, applications, *, data/*, allow
    p, role:data-dev, logs, get, data/*, allow
    g, DataTeam, role:data-dev
```

### Kubernetes RBAC 통합

```yaml
# kubernetes-rbac.yaml - EKS 클러스터 RBAC 설정
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: argocd-application-controller-cluster-role
rules:
  - apiGroups:
      - '*'
    resources:
      - '*'
    verbs:
      - '*'
  - nonResourceURLs:
      - '*'
    verbs:
      - '*'

---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: argocd-application-controller-cluster-role-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: argocd-application-controller-cluster-role
subjects:
  - kind: ServiceAccount
    name: argocd-application-controller
    namespace: argocd

---
# 개발자용 제한된 ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: developer-role
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/log", "services", "configmaps"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments", "replicasets"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods/exec"]
    verbs: ["create"]

---
# SRE용 확장된 ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: sre-role
rules:
  - apiGroups: ["*"]
    resources: ["*"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods/exec", "pods/portforward"]
    verbs: ["create"]
  - apiGroups: ["apps"]
    resources: ["deployments", "replicasets", "statefulsets"]
    verbs: ["patch", "update"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["delete"]
```

### SSO 트러블슈팅

```yaml
# SSO 문제 해결을 위한 디버그 설정
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  # Dex 디버그 로깅 활성화
  dex.server.log.level: debug

  # ArgoCD Server 디버그 로깅
  server.log.level: debug
```

**일반적인 SSO 문제 및 해결 방법:**

| 문제 | 원인 | 해결 방법 |
|------|------|----------|
| "Invalid redirect_uri" | SAML ACS URL 불일치 | IAM Identity Center 앱 설정에서 ACS URL 확인 |
| "User not found" | 그룹 속성 미전달 | SAML 응답에 groups 속성 포함 확인 |
| "Access denied" | RBAC 매핑 오류 | policy.csv 그룹 이름 정확히 일치 확인 |
| "Certificate error" | CA 인증서 만료 | SAML 메타데이터 재다운로드 및 업데이트 |

```bash
# SSO 디버깅 명령어
# Dex 로그 확인
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-dex-server -f

# ArgoCD Server 로그 확인
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server -f

# SAML 응답 디코딩 (브라우저 개발자 도구에서 캡처 후)
echo "BASE64_ENCODED_SAML_RESPONSE" | base64 -d | xmllint --format -
```

---

## 시크릿 관리

External Secrets Operator(ESO)를 사용하여 AWS Secrets Manager의 시크릿을 Kubernetes Secret으로 동기화합니다.

### External Secrets Operator 설치

```hcl
# external-secrets.tf - ESO Helm 설치

resource "helm_release" "external_secrets" {
  name       = "external-secrets"
  namespace  = "external-secrets"
  repository = "https://charts.external-secrets.io"
  chart      = "external-secrets"
  version    = "0.9.13"

  create_namespace = true

  values = [
    yamlencode({
      installCRDs = true

      replicaCount = 2

      serviceAccount = {
        create = true
        name   = "external-secrets"
        annotations = {
          "eks.amazonaws.com/role-arn" = aws_iam_role.external_secrets.arn
        }
      }

      resources = {
        limits = {
          cpu    = "500m"
          memory = "512Mi"
        }
        requests = {
          cpu    = "100m"
          memory = "128Mi"
        }
      }

      webhook = {
        replicaCount = 2
        resources = {
          limits = {
            cpu    = "200m"
            memory = "256Mi"
          }
          requests = {
            cpu    = "50m"
            memory = "64Mi"
          }
        }
      }

      certController = {
        replicaCount = 2
        resources = {
          limits = {
            cpu    = "200m"
            memory = "256Mi"
          }
          requests = {
            cpu    = "50m"
            memory = "64Mi"
          }
        }
      }

      metrics = {
        enabled = true
        serviceMonitor = {
          enabled = true
        }
      }
    })
  ]
}

# IAM 역할 (Pod Identity 사용)
resource "aws_iam_role" "external_secrets" {
  name = "ExternalSecretsRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "pods.eks.amazonaws.com"
        }
        Action = [
          "sts:AssumeRole",
          "sts:TagSession"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "external_secrets" {
  name = "secrets-access"
  role = aws_iam_role.external_secrets.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SecretsManagerAccess"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret",
          "secretsmanager:ListSecretVersionIds"
        ]
        Resource = "arn:aws:secretsmanager:ap-northeast-2:*:secret:*"
      },
      {
        Sid    = "KMSDecrypt"
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "secretsmanager.ap-northeast-2.amazonaws.com"
          }
        }
      }
    ]
  })
}

resource "aws_eks_pod_identity_association" "external_secrets" {
  cluster_name    = var.cluster_name
  namespace       = "external-secrets"
  service_account = "external-secrets"
  role_arn        = aws_iam_role.external_secrets.arn
}
```

### SecretStore / ClusterSecretStore 설정

```yaml
# cluster-secret-store.yaml - 클러스터 전역 SecretStore
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: aws-secrets-manager
spec:
  provider:
    aws:
      service: SecretsManager
      region: ap-northeast-2
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets
            namespace: external-secrets

---
# namespace-scoped SecretStore
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets-manager
  namespace: myapp
spec:
  provider:
    aws:
      service: SecretsManager
      region: ap-northeast-2
      auth:
        jwt:
          serviceAccountRef:
            name: myapp-secrets-sa
            namespace: myapp

---
# Parameter Store 사용시
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: aws-parameter-store
spec:
  provider:
    aws:
      service: ParameterStore
      region: ap-northeast-2
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets
            namespace: external-secrets
```

### ExternalSecret CRD 예제

```yaml
# external-secret.yaml - 기본 사용 예제
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: myapp-secrets
  namespace: myapp
spec:
  refreshInterval: 1h  # 동기화 주기

  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore

  target:
    name: myapp-secrets  # 생성될 K8s Secret 이름
    creationPolicy: Owner
    deletionPolicy: Retain

  # 전체 시크릿 가져오기
  dataFrom:
    - extract:
        key: myapp/production/config

---
# 선택적 필드 매핑
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: database-credentials
  namespace: myapp
spec:
  refreshInterval: 30m

  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore

  target:
    name: database-credentials
    creationPolicy: Owner
    template:
      type: Opaque
      data:
        # 템플릿으로 데이터 변환
        DATABASE_URL: "postgresql://{{ .username }}:{{ .password }}@{{ .host }}:{{ .port }}/{{ .database }}"

  data:
    - secretKey: username
      remoteRef:
        key: myapp/production/database
        property: username

    - secretKey: password
      remoteRef:
        key: myapp/production/database
        property: password

    - secretKey: host
      remoteRef:
        key: myapp/production/database
        property: host

    - secretKey: port
      remoteRef:
        key: myapp/production/database
        property: port

    - secretKey: database
      remoteRef:
        key: myapp/production/database
        property: dbname

---
# 여러 시크릿 소스 조합
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: combined-secrets
  namespace: myapp
spec:
  refreshInterval: 1h

  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore

  target:
    name: combined-secrets
    creationPolicy: Owner

  data:
    # Secrets Manager에서 가져오기
    - secretKey: DB_PASSWORD
      remoteRef:
        key: myapp/production/database
        property: password

    - secretKey: API_KEY
      remoteRef:
        key: myapp/production/api-keys
        property: stripe-key

  dataFrom:
    # 전체 시크릿 가져오기
    - extract:
        key: myapp/production/feature-flags
```

### 시크릿 로테이션 전략

```yaml
# secret-rotation.yaml - 자동 로테이션 설정
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: rotating-secret
  namespace: myapp
  annotations:
    # ArgoCD 동기화에서 제외 (ESO가 관리)
    argocd.argoproj.io/compare-options: IgnoreExtraneous
spec:
  refreshInterval: 5m  # 짧은 주기로 로테이션된 값 반영

  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore

  target:
    name: rotating-credentials
    creationPolicy: Owner
    deletionPolicy: Retain

  data:
    - secretKey: current-password
      remoteRef:
        key: myapp/rotating/credentials
        property: password
        version: AWSCURRENT  # 현재 버전

    - secretKey: previous-password
      remoteRef:
        key: myapp/rotating/credentials
        property: password
        version: AWSPREVIOUS  # 이전 버전 (롤백용)
```

```hcl
# secrets-manager-rotation.tf - AWS Secrets Manager 자동 로테이션

resource "aws_secretsmanager_secret" "database_credentials" {
  name        = "myapp/production/database"
  description = "Database credentials for myapp"

  tags = {
    Application = "myapp"
    Environment = "production"
  }
}

resource "aws_secretsmanager_secret_rotation" "database_credentials" {
  secret_id           = aws_secretsmanager_secret.database_credentials.id
  rotation_lambda_arn = aws_lambda_function.secret_rotation.arn

  rotation_rules {
    automatically_after_days = 30
  }
}
```

### ESO Pod Identity 설정

```yaml
# eso-pod-identity.yaml - 네임스페이스별 Pod Identity
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myapp-secrets-sa
  namespace: myapp
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/MyAppSecretsRole

---
# 해당 ServiceAccount에 대한 SecretStore
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: myapp-secrets-store
  namespace: myapp
spec:
  provider:
    aws:
      service: SecretsManager
      region: ap-northeast-2
      auth:
        jwt:
          serviceAccountRef:
            name: myapp-secrets-sa
```

```hcl
# 네임스페이스별 IAM 역할 (최소 권한 원칙)
resource "aws_iam_role" "myapp_secrets" {
  name = "MyAppSecretsRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "pods.eks.amazonaws.com"
        }
        Action = [
          "sts:AssumeRole",
          "sts:TagSession"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "myapp_secrets" {
  name = "myapp-secrets-access"
  role = aws_iam_role.myapp_secrets.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        # 특정 시크릿만 접근 허용
        Resource = [
          "arn:aws:secretsmanager:ap-northeast-2:*:secret:myapp/*"
        ]
      }
    ]
  })
}

resource "aws_eks_pod_identity_association" "myapp_secrets" {
  cluster_name    = var.cluster_name
  namespace       = "myapp"
  service_account = "myapp-secrets-sa"
  role_arn        = aws_iam_role.myapp_secrets.arn
}
```

---

## 요약

이 문서에서 다룬 주요 내용:

1. **멀티클러스터 아키텍처**: Hub-Spoke 모델을 통한 중앙 집중식 GitOps 관리, 클러스터 등록 및 관리 패턴

2. **ArgoCD Terraform 설치**: Helm을 통한 HA ArgoCD 배포, Server/Controller/Repo Server/Redis 설정, Ingress 및 메트릭 구성

3. **NodePool GitOps 관리**: Kubernetes CRD인 NodePool을 ArgoCD로 관리하는 이유, 클러스터별 NodePool 설정, 데이터 처리 전용 NodePool

4. **ApplicationSet 전략**: Cluster/Git/Matrix/PR Generator 활용, 멀티클러스터 배포, Sync Wave 기반 순차 배포

5. **IAM Identity Center SSO**: SAML 2.0 구성, 그룹-역할 매핑, Kubernetes RBAC 통합, 트러블슈팅

6. **시크릿 관리**: External Secrets Operator 설치, SecretStore/ClusterSecretStore 설정, ExternalSecret CRD, 시크릿 로테이션

---

## 관련 문서

- [CI 파이프라인](./03-ci-pipelines.md)
- [ArgoCD 기초](../gitops/argocd/README.md)
- [NodePool 구성](../eks-auto-mode/02-nodepool-configuration.md)
- [GitOps 자동화](./05-gitops-automation.md)

---

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [ArgoCD 멀티클러스터 퀴즈](../quizzes/ops/04-gitops-multi-cluster-quiz.md)를 풀어보세요.

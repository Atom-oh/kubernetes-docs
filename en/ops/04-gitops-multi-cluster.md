# ArgoCD Multi-Cluster Deployment and IAM Identity Center

> **Supported Versions**: ArgoCD 2.10+, EKS 1.28+, External Secrets Operator 0.9+
> **Last Updated**: February 23, 2026

< [Previous: CI Pipelines](./03-ci-pipelines.md) | [Table of Contents](./README.md) | [Next: GitOps Automation](./05-gitops-automation.md) >

---

## Overview

Managing multiple EKS clusters through GitOps requires a centralized control plane with robust authentication and authorization. This guide covers deploying ArgoCD in a hub-spoke architecture, integrating with AWS IAM Identity Center for SSO, and implementing advanced deployment patterns using ApplicationSets.

**Architecture Goals:**
- Single ArgoCD instance managing multiple clusters
- SSO authentication via IAM Identity Center (AWS SSO)
- NodePool lifecycle management through GitOps
- Secure secret management with External Secrets Operator

---

## 1. Multi-Cluster Architecture

### 1.1 Hub-Spoke Model

```
                    ┌─────────────────────────────────────────┐
                    │         Management Cluster              │
                    │  ┌─────────────────────────────────┐    │
                    │  │           ArgoCD                 │    │
                    │  │  ┌─────────┐  ┌─────────────┐   │    │
                    │  │  │ Server  │  │ Application │   │    │
                    │  │  │         │  │ Controller  │   │    │
                    │  │  └────┬────┘  └──────┬──────┘   │    │
                    │  │       │              │          │    │
                    │  │  ┌────┴──────────────┴────┐     │    │
                    │  │  │    Redis HA Cluster    │     │    │
                    │  │  └───────────────────────┘     │    │
                    │  └─────────────────────────────────┘    │
                    │                  │                      │
                    └──────────────────┼──────────────────────┘
                                       │
          ┌────────────────────────────┼────────────────────────────┐
          │                            │                            │
          ▼                            ▼                            ▼
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│  Workload Cluster   │    │  Workload Cluster   │    │  Workload Cluster   │
│     (Dev/Test)      │    │     (Staging)       │    │    (Production)     │
│                     │    │                     │    │                     │
│  ┌───────────────┐  │    │  ┌───────────────┐  │    │  ┌───────────────┐  │
│  │  Applications │  │    │  │  Applications │  │    │  │  Applications │  │
│  └───────────────┘  │    │  └───────────────┘  │    │  └───────────────┘  │
│  ┌───────────────┐  │    │  ┌───────────────┐  │    │  ┌───────────────┐  │
│  │   NodePools   │  │    │  │   NodePools   │  │    │  │   NodePools   │  │
│  └───────────────┘  │    │  └───────────────┘  │    │  └───────────────┘  │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

### 1.2 Cluster Registration

Register workload clusters with ArgoCD:

```bash
# Get the management cluster context
kubectl config use-context management-cluster

# Add workload clusters
argocd cluster add dev-cluster --name dev --grpc-web
argocd cluster add staging-cluster --name staging --grpc-web
argocd cluster add prod-cluster --name prod --grpc-web

# Verify cluster registration
argocd cluster list
```

Alternatively, use declarative cluster secrets:

```yaml
# cluster-secret-dev.yaml
apiVersion: v1
kind: Secret
metadata:
  name: dev-cluster-secret
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
type: Opaque
stringData:
  name: dev
  server: https://DEV_CLUSTER_ENDPOINT.eks.amazonaws.com
  config: |
    {
      "awsAuthConfig": {
        "clusterName": "dev-cluster",
        "roleARN": "arn:aws:iam::123456789012:role/ArgoCD-Dev-Role"
      },
      "tlsClientConfig": {
        "insecure": false,
        "caData": "BASE64_ENCODED_CA_DATA"
      }
    }
```

### 1.3 Cross-Cluster IAM Role

```hcl
# argocd-cross-cluster-role.tf

# Role in workload cluster account
resource "aws_iam_role" "argocd_workload" {
  name = "ArgoCD-Workload-Role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${var.management_account_id}:role/ArgoCD-Management-Role"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "sts:ExternalId" = var.external_id
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "argocd_workload" {
  name = "eks-access"
  role = aws_iam_role.argocd_workload.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "eks:DescribeCluster",
          "eks:ListClusters"
        ]
        Resource = "*"
      }
    ]
  })
}

# aws-auth ConfigMap entry
resource "kubernetes_config_map_v1_data" "aws_auth" {
  metadata {
    name      = "aws-auth"
    namespace = "kube-system"
  }

  data = {
    mapRoles = yamlencode([
      {
        rolearn  = aws_iam_role.argocd_workload.arn
        username = "argocd"
        groups   = ["system:masters"]
      }
    ])
  }

  force = true
}
```

---

## 2. ArgoCD Terraform Installation

### 2.1 ArgoCD Helm Deployment

```hcl
# argocd.tf

resource "kubernetes_namespace" "argocd" {
  metadata {
    name = "argocd"
    labels = {
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
}

resource "helm_release" "argocd" {
  name       = "argocd"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"
  version    = "6.7.3"
  namespace  = kubernetes_namespace.argocd.metadata[0].name

  values = [
    templatefile("${path.module}/argocd-values.yaml", {
      domain                = var.argocd_domain
      certificate_arn       = var.certificate_arn
      oidc_issuer_url       = var.oidc_issuer_url
      oidc_client_id        = var.oidc_client_id
      redis_ha_enabled      = var.environment == "production"
      replicas              = var.environment == "production" ? 3 : 1
    })
  ]

  depends_on = [
    kubernetes_namespace.argocd
  ]
}

# ArgoCD admin password
resource "random_password" "argocd_admin" {
  length  = 32
  special = true
}

resource "aws_secretsmanager_secret" "argocd_admin" {
  name = "argocd/admin-password"
}

resource "aws_secretsmanager_secret_version" "argocd_admin" {
  secret_id     = aws_secretsmanager_secret.argocd_admin.id
  secret_string = bcrypt(random_password.argocd_admin.result)
}
```

### 2.2 ArgoCD Helm Values (HA Configuration)

```yaml
# argocd-values.yaml

global:
  domain: ${domain}
  logging:
    format: json
    level: info

# HA Configuration
controller:
  replicas: ${replicas}

  resources:
    limits:
      cpu: "2"
      memory: 4Gi
    requests:
      cpu: "500m"
      memory: 1Gi

  metrics:
    enabled: true
    serviceMonitor:
      enabled: true

  env:
    - name: ARGOCD_CONTROLLER_REPLICAS
      value: "${replicas}"

server:
  replicas: ${replicas}

  autoscaling:
    enabled: true
    minReplicas: ${replicas}
    maxReplicas: 5
    targetCPUUtilizationPercentage: 80

  resources:
    limits:
      cpu: "1"
      memory: 1Gi
    requests:
      cpu: "250m"
      memory: 256Mi

  ingress:
    enabled: true
    ingressClassName: alb
    annotations:
      alb.ingress.kubernetes.io/scheme: internet-facing
      alb.ingress.kubernetes.io/target-type: ip
      alb.ingress.kubernetes.io/backend-protocol: HTTPS
      alb.ingress.kubernetes.io/healthcheck-protocol: HTTPS
      alb.ingress.kubernetes.io/healthcheck-path: /healthz
      alb.ingress.kubernetes.io/certificate-arn: ${certificate_arn}
      alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS13-1-2-2021-06
      alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
      alb.ingress.kubernetes.io/ssl-redirect: '443'
    hosts:
      - ${domain}
    tls:
      - hosts:
          - ${domain}
        secretName: argocd-server-tls

  extraArgs:
    - --insecure  # TLS terminated at ALB

repoServer:
  replicas: ${replicas}

  autoscaling:
    enabled: true
    minReplicas: ${replicas}
    maxReplicas: 5

  resources:
    limits:
      cpu: "2"
      memory: 2Gi
    requests:
      cpu: "500m"
      memory: 512Mi

  env:
    - name: ARGOCD_EXEC_TIMEOUT
      value: "5m"

applicationSet:
  replicas: ${replicas}

  resources:
    limits:
      cpu: "500m"
      memory: 512Mi
    requests:
      cpu: "100m"
      memory: 128Mi

notifications:
  enabled: true

  resources:
    limits:
      cpu: "200m"
      memory: 256Mi
    requests:
      cpu: "50m"
      memory: 64Mi

%{ if redis_ha_enabled }
redis-ha:
  enabled: true
  replicas: 3

  haproxy:
    enabled: true
    replicas: 3

  persistence:
    enabled: true
    storageClass: gp3
    size: 10Gi

  resources:
    limits:
      cpu: "500m"
      memory: 512Mi
    requests:
      cpu: "100m"
      memory: 128Mi
%{ else }
redis:
  enabled: true
  resources:
    limits:
      cpu: "200m"
      memory: 256Mi
    requests:
      cpu: "50m"
      memory: 64Mi
%{ endif }

configs:
  cm:
    url: https://${domain}

    # Enable status badge
    statusbadge.enabled: "true"

    # Resource tracking method
    application.resourceTrackingMethod: annotation

    # Health checks
    resource.customizations.health.argoproj.io_Application: |
      hs = {}
      hs.status = "Progressing"
      hs.message = ""
      if obj.status ~= nil then
        if obj.status.health ~= nil then
          hs.status = obj.status.health.status
          if obj.status.health.message ~= nil then
            hs.message = obj.status.health.message
          end
        end
      end
      return hs

    # Kustomize build options
    kustomize.buildOptions: --enable-helm --load-restrictor LoadRestrictionsNone

  params:
    server.insecure: true
    controller.status.processors: 20
    controller.operation.processors: 10
    controller.self.heal.timeout.seconds: 5
    controller.repo.server.timeout.seconds: 60
    reposerver.parallelism.limit: 0

  rbac:
    policy.default: role:readonly
    policy.csv: |
      g, argocd-admins, role:admin
      g, platform-team, role:admin
      g, dev-team, role:developer

      p, role:developer, applications, get, */*, allow
      p, role:developer, applications, sync, */dev-*, allow
      p, role:developer, applications, sync, */staging-*, allow
      p, role:developer, logs, get, */*, allow
      p, role:developer, exec, create, */dev-*, allow
```

### 2.3 ArgoCD Service Account for AWS

```hcl
# argocd-iam.tf

resource "aws_iam_role" "argocd" {
  name = "ArgoCD-Management-Role"

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

resource "aws_iam_role_policy" "argocd_assume_role" {
  name = "assume-workload-roles"
  role = aws_iam_role.argocd.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "sts:AssumeRole"
        Resource = var.workload_cluster_role_arns
      }
    ]
  })
}

resource "aws_eks_pod_identity_association" "argocd_server" {
  cluster_name    = var.cluster_name
  namespace       = "argocd"
  service_account = "argocd-server"
  role_arn        = aws_iam_role.argocd.arn
}

resource "aws_eks_pod_identity_association" "argocd_controller" {
  cluster_name    = var.cluster_name
  namespace       = "argocd"
  service_account = "argocd-application-controller"
  role_arn        = aws_iam_role.argocd.arn
}
```

---

## 3. NodePool GitOps Management

### 3.1 NodePool as Kubernetes CRD

In EKS Auto Mode, NodePools are managed as Kubernetes custom resources rather than Terraform. This enables GitOps workflows for node configuration:

```yaml
# nodepools/base/general-purpose.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: general-purpose
spec:
  template:
    metadata:
      labels:
        workload-type: general
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values:
            - m6i.large
            - m6i.xlarge
            - m7g.large
            - m7g.xlarge
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default

  limits:
    cpu: 1000
    memory: 2000Gi

  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m

  weight: 100
```

### 3.2 Environment-Specific NodePool Overlays

```yaml
# nodepools/overlays/dev/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

patches:
  - patch: |
      - op: replace
        path: /spec/limits/cpu
        value: 100
      - op: replace
        path: /spec/limits/memory
        value: 200Gi
      - op: replace
        path: /spec/template/spec/requirements/1/values
        value: ["spot"]
    target:
      kind: NodePool
      name: general-purpose
```

```yaml
# nodepools/overlays/production/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

patches:
  - patch: |
      - op: replace
        path: /spec/limits/cpu
        value: 2000
      - op: replace
        path: /spec/limits/memory
        value: 4000Gi
      - op: replace
        path: /spec/template/spec/requirements/1/values
        value: ["on-demand"]
      - op: add
        path: /spec/disruption/budgets
        value:
          - nodes: "10%"
            schedule: "0 9 * * 1-5"
            duration: 8h
    target:
      kind: NodePool
      name: general-purpose
```

### 3.3 Specialized NodePools

```yaml
# nodepools/base/data-workloads.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: data-workloads
spec:
  template:
    metadata:
      labels:
        workload-type: data
        storage-optimized: "true"
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values:
            - i3.xlarge
            - i3.2xlarge
            - i3en.xlarge
            - i3en.2xlarge
        - key: topology.kubernetes.io/zone
          operator: In
          values:
            - us-east-1a
            - us-east-1b

      taints:
        - key: data-workload
          value: "true"
          effect: NoSchedule

      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: data-optimized

  limits:
    cpu: 500
    memory: 1000Gi

  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30m

  weight: 50
```

```yaml
# nodepools/base/gpu-workloads.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-workloads
spec:
  template:
    metadata:
      labels:
        workload-type: gpu
        nvidia.com/gpu.present: "true"
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values:
            - g5.xlarge
            - g5.2xlarge
            - p4d.24xlarge
        - key: topology.kubernetes.io/zone
          operator: In
          values:
            - us-east-1a
            - us-east-1b

      taints:
        - key: nvidia.com/gpu
          value: "true"
          effect: NoSchedule

      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: gpu-optimized

  limits:
    cpu: 200
    memory: 800Gi
    nvidia.com/gpu: 50

  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 1h

  weight: 25
```

### 3.4 NodePool ArgoCD Application

```yaml
# applications/nodepools.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: nodepools
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: infrastructure

  source:
    repoURL: https://github.com/myorg/eks-config.git
    targetRevision: HEAD
    path: nodepools/overlays/production

  destination:
    server: https://kubernetes.default.svc
    namespace: kube-system

  syncPolicy:
    automated:
      prune: false  # Don't auto-delete NodePools
      selfHeal: true

    syncOptions:
      - CreateNamespace=false
      - PruneLast=true
      - ApplyOutOfSyncOnly=true

    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m

  ignoreDifferences:
    - group: karpenter.sh
      kind: NodePool
      jsonPointers:
        - /status
```

---

## 4. ApplicationSet Strategies

### 4.1 Cluster Generator

Deploy applications across all registered clusters:

```yaml
# applicationsets/platform-services.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: platform-services
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]

  generators:
    - clusters:
        selector:
          matchLabels:
            environment: production
        values:
          revision: main
    - clusters:
        selector:
          matchLabels:
            environment: staging
        values:
          revision: develop
    - clusters:
        selector:
          matchLabels:
            environment: dev
        values:
          revision: develop

  template:
    metadata:
      name: '{{.name}}-platform-services'
      labels:
        cluster: '{{.name}}'
        environment: '{{.metadata.labels.environment}}'
    spec:
      project: platform

      source:
        repoURL: https://github.com/myorg/platform-services.git
        targetRevision: '{{.values.revision}}'
        path: 'clusters/{{.metadata.labels.environment}}'
        helm:
          valueFiles:
            - values.yaml
            - 'values-{{.name}}.yaml'

      destination:
        server: '{{.server}}'
        namespace: platform

      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
```

### 4.2 Git Generator (Directory)

Generate applications from directory structure:

```yaml
# applicationsets/microservices.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: microservices
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]

  generators:
    - git:
        repoURL: https://github.com/myorg/microservices.git
        revision: HEAD
        directories:
          - path: 'services/*'
          - path: 'services/internal/*'
            exclude: true

  template:
    metadata:
      name: '{{.path.basename}}'
      annotations:
        notifications.argoproj.io/subscribe.on-sync-succeeded.slack: deployments
    spec:
      project: microservices

      source:
        repoURL: https://github.com/myorg/microservices.git
        targetRevision: HEAD
        path: '{{.path.path}}'
        helm:
          valueFiles:
            - values.yaml

      destination:
        server: https://kubernetes.default.svc
        namespace: '{{.path.basename}}'

      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
          - PrunePropagationPolicy=foreground
```

### 4.3 Matrix Generator

Combine generators for complex deployments:

```yaml
# applicationsets/multi-cluster-apps.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: multi-cluster-apps
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]

  generators:
    - matrix:
        generators:
          # First generator: clusters
          - clusters:
              selector:
                matchExpressions:
                  - key: environment
                    operator: In
                    values: ["staging", "production"]

          # Second generator: applications from git
          - git:
              repoURL: https://github.com/myorg/apps.git
              revision: HEAD
              files:
                - path: 'apps/*/config.json'

  template:
    metadata:
      name: '{{.name}}-{{.path.basename}}'
      labels:
        app: '{{.path.basename}}'
        cluster: '{{.name}}'
        environment: '{{.metadata.labels.environment}}'
    spec:
      project: applications

      source:
        repoURL: https://github.com/myorg/apps.git
        targetRevision: '{{if eq .metadata.labels.environment "production"}}main{{else}}develop{{end}}'
        path: 'apps/{{.path.basename}}/overlays/{{.metadata.labels.environment}}'
        kustomize:
          images:
            - '{{.image.repository}}:{{.image.tag}}'

      destination:
        server: '{{.server}}'
        namespace: '{{.namespace}}'

      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
```

### 4.4 Pull Request Generator

Preview environments for pull requests:

```yaml
# applicationsets/pr-previews.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: pr-previews
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]

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
        requeueAfterSeconds: 60

  template:
    metadata:
      name: 'preview-{{.number}}'
      annotations:
        notifications.argoproj.io/subscribe.on-sync-succeeded.slack: previews
      labels:
        app.kubernetes.io/part-of: myapp
        preview: "true"
    spec:
      project: previews

      source:
        repoURL: 'https://github.com/myorg/myapp.git'
        targetRevision: '{{.head_sha}}'
        path: deploy/preview
        helm:
          parameters:
            - name: image.tag
              value: 'pr-{{.number}}'
            - name: ingress.host
              value: 'pr-{{.number}}.preview.example.com'

      destination:
        server: https://kubernetes.default.svc
        namespace: 'preview-{{.number}}'

      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true

      # Auto-delete after PR is closed
      info:
        - name: PR
          value: 'https://github.com/myorg/myapp/pull/{{.number}}'
```

### 4.5 Sync Policies and Waves

```yaml
# applicationsets/staged-rollout.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: staged-rollout
  namespace: argocd
spec:
  goTemplate: true

  generators:
    - list:
        elements:
          - cluster: dev
            server: https://dev.eks.amazonaws.com
            wave: "1"
            autoSync: true
          - cluster: staging
            server: https://staging.eks.amazonaws.com
            wave: "2"
            autoSync: true
          - cluster: prod-west
            server: https://prod-west.eks.amazonaws.com
            wave: "3"
            autoSync: false
          - cluster: prod-east
            server: https://prod-east.eks.amazonaws.com
            wave: "4"
            autoSync: false

  template:
    metadata:
      name: 'myapp-{{.cluster}}'
      annotations:
        argocd.argoproj.io/sync-wave: '{{.wave}}'
    spec:
      project: default

      source:
        repoURL: https://github.com/myorg/myapp.git
        targetRevision: HEAD
        path: 'deploy/{{.cluster}}'

      destination:
        server: '{{.server}}'
        namespace: myapp

      syncPolicy:
        '{{if eq .autoSync "true"}}':
          automated:
            prune: true
            selfHeal: true
        syncOptions:
          - CreateNamespace=true
          - PruneLast=true
        retry:
          limit: 5
          backoff:
            duration: 5s
            factor: 2
            maxDuration: 3m
```

---

## 5. IAM Identity Center SSO Integration

### 5.1 IAM Identity Center SAML Application

```hcl
# iam-identity-center.tf

data "aws_ssoadmin_instances" "this" {}

resource "aws_ssoadmin_application" "argocd" {
  name                     = "ArgoCD"
  application_provider_arn = "arn:aws:sso::aws:applicationProvider/custom"
  instance_arn            = tolist(data.aws_ssoadmin_instances.this.arns)[0]

  portal_options {
    sign_in_options {
      application_url = "https://argocd.example.com"
      origin          = "APPLICATION"
    }
    visibility = "ENABLED"
  }
}

resource "aws_ssoadmin_application_assignment" "argocd_admins" {
  application_arn = aws_ssoadmin_application.argocd.application_arn
  principal_id    = aws_identitystore_group.argocd_admins.group_id
  principal_type  = "GROUP"
}

resource "aws_ssoadmin_application_assignment" "argocd_developers" {
  application_arn = aws_ssoadmin_application.argocd.application_arn
  principal_id    = aws_identitystore_group.developers.group_id
  principal_type  = "GROUP"
}

# Identity Store groups
data "aws_identitystore_group" "argocd_admins" {
  identity_store_id = tolist(data.aws_ssoadmin_instances.this.identity_store_ids)[0]

  alternate_identifier {
    unique_attribute {
      attribute_path  = "DisplayName"
      attribute_value = "ArgoCD-Admins"
    }
  }
}

data "aws_identitystore_group" "developers" {
  identity_store_id = tolist(data.aws_ssoadmin_instances.this.identity_store_ids)[0]

  alternate_identifier {
    unique_attribute {
      attribute_path  = "DisplayName"
      attribute_value = "Developers"
    }
  }
}
```

### 5.2 ArgoCD OIDC Configuration

Configure ArgoCD to use IAM Identity Center as OIDC provider:

```yaml
# argocd-cm ConfigMap patch
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.com

  # OIDC configuration for IAM Identity Center
  oidc.config: |
    name: AWS SSO
    issuer: https://identitycenter.amazonaws.com/ssoins-XXXXXXXXXXXX
    clientID: <APPLICATION_CLIENT_ID>
    clientSecret: $oidc.aws-sso.clientSecret
    requestedScopes:
      - openid
      - email
      - profile
    requestedIDTokenClaims:
      email:
        essential: true
      groups:
        essential: true
    logoutURL: https://identitycenter.amazonaws.com/ssoins-XXXXXXXXXXXX/logout

  # Admin account settings
  admin.enabled: "false"  # Disable local admin when using SSO
```

### 5.3 OIDC Client Secret

```yaml
# argocd-secret patch
apiVersion: v1
kind: Secret
metadata:
  name: argocd-secret
  namespace: argocd
type: Opaque
stringData:
  oidc.aws-sso.clientSecret: <CLIENT_SECRET_FROM_IAM_IDENTITY_CENTER>
```

Or use External Secrets:

```yaml
# external-secret-oidc.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: argocd-oidc-secret
  namespace: argocd
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: argocd-secret
    creationPolicy: Merge
  data:
    - secretKey: oidc.aws-sso.clientSecret
      remoteRef:
        key: argocd/oidc-client-secret
        property: secret
```

### 5.4 Group-Role Mapping

```yaml
# argocd-rbac-cm ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  policy.default: role:readonly

  policy.csv: |
    # Admin access for ArgoCD-Admins group
    g, ArgoCD-Admins, role:admin

    # Platform team - full access to infrastructure projects
    g, Platform-Team, role:platform-admin
    p, role:platform-admin, applications, *, infrastructure/*, allow
    p, role:platform-admin, applications, *, platform/*, allow
    p, role:platform-admin, clusters, get, *, allow
    p, role:platform-admin, repositories, *, *, allow
    p, role:platform-admin, projects, get, *, allow

    # Developers - sync and view for their projects
    g, Developers, role:developer
    p, role:developer, applications, get, */*, allow
    p, role:developer, applications, sync, applications/*, allow
    p, role:developer, applications, action/*, applications/*, allow
    p, role:developer, logs, get, */*, allow
    p, role:developer, exec, create, applications/dev-*, allow

    # SRE team - operations access
    g, SRE-Team, role:sre
    p, role:sre, applications, *, */*, allow
    p, role:sre, clusters, *, *, allow
    p, role:sre, logs, get, */*, allow
    p, role:sre, exec, create, */*, allow

    # QA team - view and sync staging
    g, QA-Team, role:qa
    p, role:qa, applications, get, */*, allow
    p, role:qa, applications, sync, */staging-*, allow
    p, role:qa, logs, get, */*, allow

  scopes: '[groups, email]'
```

### 5.5 Terraform for RBAC ConfigMap

```hcl
# argocd-rbac.tf

resource "kubernetes_config_map" "argocd_rbac" {
  metadata {
    name      = "argocd-rbac-cm"
    namespace = "argocd"
  }

  data = {
    "policy.default" = "role:readonly"

    "policy.csv" = <<-EOT
      # SSO Group mappings
      g, ${var.admin_group}, role:admin
      g, ${var.platform_group}, role:platform-admin
      g, ${var.developer_group}, role:developer
      g, ${var.sre_group}, role:sre

      # Platform admin role
      p, role:platform-admin, applications, *, infrastructure/*, allow
      p, role:platform-admin, applications, *, platform/*, allow
      p, role:platform-admin, clusters, get, *, allow
      p, role:platform-admin, repositories, *, *, allow

      # Developer role
      p, role:developer, applications, get, */*, allow
      p, role:developer, applications, sync, applications/*, allow
      p, role:developer, logs, get, */*, allow

      # SRE role
      p, role:sre, applications, *, */*, allow
      p, role:sre, clusters, *, *, allow
      p, role:sre, exec, create, */*, allow
    EOT

    "scopes" = "[groups, email]"
  }

  depends_on = [helm_release.argocd]
}
```

---

## 6. Secret Management with External Secrets Operator

### 6.1 External Secrets Operator Installation

```hcl
# external-secrets.tf

resource "helm_release" "external_secrets" {
  name       = "external-secrets"
  repository = "https://charts.external-secrets.io"
  chart      = "external-secrets"
  version    = "0.9.13"
  namespace  = "external-secrets"

  create_namespace = true

  values = [<<-EOT
    installCRDs: true

    serviceAccount:
      create: true
      name: external-secrets
      annotations:
        eks.amazonaws.com/role-arn: ${aws_iam_role.external_secrets.arn}

    webhook:
      port: 9443

    certController:
      requeueInterval: 5m

    resources:
      limits:
        cpu: 200m
        memory: 256Mi
      requests:
        cpu: 50m
        memory: 64Mi
  EOT
  ]
}

# IAM Role for External Secrets
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
        Effect = "Allow"
        Action = [
          "secretsmanager:GetResourcePolicy",
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret",
          "secretsmanager:ListSecretVersionIds"
        ]
        Resource = "arn:aws:secretsmanager:*:${data.aws_caller_identity.current.account_id}:secret:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = "arn:aws:ssm:*:${data.aws_caller_identity.current.account_id}:parameter/*"
      },
      {
        Effect   = "Allow"
        Action   = "kms:Decrypt"
        Resource = var.kms_key_arns
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

### 6.2 SecretStore Configuration

```yaml
# secret-store.yaml
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: aws-secrets-manager
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets
            namespace: external-secrets
---
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: aws-parameter-store
spec:
  provider:
    aws:
      service: ParameterStore
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets
            namespace: external-secrets
```

### 6.3 ExternalSecret Examples

Database credentials:

```yaml
# external-secret-db.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: database-credentials
  namespace: myapp
spec:
  refreshInterval: 1h

  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore

  target:
    name: database-secret
    creationPolicy: Owner
    template:
      type: Opaque
      data:
        DATABASE_URL: "postgresql://{{ .username }}:{{ .password }}@{{ .host }}:{{ .port }}/{{ .database }}"

  data:
    - secretKey: username
      remoteRef:
        key: myapp/database
        property: username
    - secretKey: password
      remoteRef:
        key: myapp/database
        property: password
    - secretKey: host
      remoteRef:
        key: myapp/database
        property: host
    - secretKey: port
      remoteRef:
        key: myapp/database
        property: port
    - secretKey: database
      remoteRef:
        key: myapp/database
        property: dbname
```

API keys:

```yaml
# external-secret-api-keys.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: api-keys
  namespace: myapp
spec:
  refreshInterval: 15m

  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore

  target:
    name: api-keys-secret
    creationPolicy: Owner

  dataFrom:
    - extract:
        key: myapp/api-keys
```

TLS certificates:

```yaml
# external-secret-tls.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: tls-certificate
  namespace: myapp
spec:
  refreshInterval: 24h

  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore

  target:
    name: tls-secret
    creationPolicy: Owner
    template:
      type: kubernetes.io/tls
      data:
        tls.crt: "{{ .certificate }}"
        tls.key: "{{ .private_key }}"

  data:
    - secretKey: certificate
      remoteRef:
        key: myapp/tls-cert
        property: certificate
    - secretKey: private_key
      remoteRef:
        key: myapp/tls-cert
        property: private_key
```

### 6.4 PushSecret for Secret Sync

Sync Kubernetes secrets back to AWS Secrets Manager:

```yaml
# push-secret.yaml
apiVersion: external-secrets.io/v1alpha1
kind: PushSecret
metadata:
  name: backup-secrets
  namespace: myapp
spec:
  refreshInterval: 1h

  secretStoreRefs:
    - name: aws-secrets-manager
      kind: ClusterSecretStore

  selector:
    secret:
      name: generated-credentials

  data:
    - match:
        secretKey: password
        remoteRef:
          remoteKey: myapp/generated-credentials
          property: password
```

---

## Summary

This guide covered multi-cluster ArgoCD deployment with enterprise features:

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| Hub-Spoke Model | Centralized management | Single control plane, cross-cluster IAM |
| ArgoCD HA | High availability | Redis cluster, multiple replicas |
| NodePool GitOps | Node lifecycle management | Kustomize overlays, declarative config |
| ApplicationSets | Multi-cluster deployment | Cluster/Git/Matrix/PR generators |
| IAM Identity Center | SSO authentication | SAML/OIDC, group-role mapping |
| External Secrets | Secret management | AWS Secrets Manager integration |

**Best Practices:**
- Use declarative cluster registration with secrets
- Manage NodePools through GitOps, not Terraform
- Implement RBAC with SSO group mappings
- Use ApplicationSets for consistent multi-cluster deployments
- Centralize secrets in AWS Secrets Manager

---

## Related Documentation

- [ArgoCD Fundamentals](../gitops/argocd/README.md)
- [NodePool Configuration](../eks-auto-mode/02-nodepool-configuration.md)
- [EKS Cluster Access](../eks/02-eks-cluster-creation-part3.md)
- [CI Pipelines](./03-ci-pipelines.md)

---

< [Previous: CI Pipelines](./03-ci-pipelines.md) | [Table of Contents](./README.md) | [Next: GitOps Automation](./05-gitops-automation.md) >

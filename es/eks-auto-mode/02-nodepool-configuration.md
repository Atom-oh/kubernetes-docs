# Configuración y optimización de NodePool

> **Versiones compatibles**: EKS 1.29+, EKS Auto Mode GA
> **Última actualización**: July 3, 2026

Esta guía cubre los NodePools predeterminados proporcionados por EKS Auto Mode y cómo crear NodePools personalizados adaptados a los requisitos de tus workloads.

---

## Comprender los NodePools predeterminados

EKS Auto Mode proporciona dos NodePools predeterminados:

### NodePool general-purpose

NodePool predeterminado para workloads de propósito general.

```yaml
# general-purpose NodePool (AWS managed, for reference)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: general-purpose
spec:
  template:
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
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
```

### NodePool system

NodePool para componentes del sistema (CoreDNS, kube-proxy, etc.).

```yaml
# system NodePool (AWS managed, for reference)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: system
spec:
  template:
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["medium", "large", "xlarge"]
      taints:
        - key: CriticalAddonsOnly
          value: "true"
          effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

---

## Crear NodePools personalizados

Puedes crear NodePools personalizados adaptados a los requisitos de tus workloads.

### NodePool de cómputo de alto rendimiento

```yaml
# compute-optimized-nodepool.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: compute-optimized
  labels:
    workload-type: compute-intensive
spec:
  template:
    metadata:
      labels:
        workload-type: compute-intensive
    spec:
      requirements:
        # Use only CPU-optimized instances
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c"]
        # Latest generation instances
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["6"]
        # Limit instance sizes
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["xlarge", "2xlarge", "4xlarge"]
        # Use only x86_64
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        # Use only On-Demand (stability first)
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  # Limit maximum nodes
  limits:
    cpu: 1000
    memory: 4000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
  # Node weight (higher priority)
  weight: 10
```

### NodePool optimizado para memoria

```yaml
# memory-optimized-nodepool.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: memory-optimized
  labels:
    workload-type: memory-intensive
spec:
  template:
    metadata:
      labels:
        workload-type: memory-intensive
    spec:
      requirements:
        # Memory-optimized instances
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["r"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["2xlarge", "4xlarge", "8xlarge", "12xlarge"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: 500
    memory: 8000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
  weight: 5
```

---

## Configuración de NodeClass

NodeClass define la configuración específica de AWS para los nodes.

```yaml
# custom-nodeclass.yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: custom-nodeclass
spec:
  # Select AMI family
  amiFamily: AL2023

  # Subnet selection
  subnetSelectorTerms:
    - tags:
        kubernetes.io/role/internal-elb: "1"
        Environment: production

  # Security group selection
  securityGroupSelectorTerms:
    - tags:
        kubernetes.io/cluster/my-cluster: owned
        Type: worker-node

  # Instance profile
  instanceProfile: eks-node-instance-profile

  # Block device mappings
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
        iops: 3000
        throughput: 125
        encrypted: true
        deleteOnTermination: true

  # User data (additional bootstrap script)
  userData: |
    #!/bin/bash
    echo "Custom bootstrap script"
    # Kernel parameter tuning
    sysctl -w vm.max_map_count=262144

  # Metadata options
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 2
    httpTokens: required  # IMDSv2 required

  tags:
    Environment: production
    ManagedBy: eks-auto-mode
```

### Campos extendidos de seguridad y redes

NodeClass admite campos adicionales para cifrado de disco completo, cadenas de confianza de CA personalizadas y aislamiento del tráfico de Pod.

```yaml
# secure-network-nodeclass.yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: secure-network-nodeclass
spec:
  amiFamily: AL2023

  # Encrypt ephemeral instance storage + root EBS volume with a customer-managed KMS key
  # (no custom AMI required)
  kmsKeyID: arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab

  # Custom CA certificate bundle for enterprise PKI/proxy trust chains
  certificateBundles:
    - name: corporate-ca
      content: |
        -----BEGIN CERTIFICATE-----
        MIIDXTCCAkWgAwIBAgIJAK...
        -----END CERTIFICATE-----

  # Separate infrastructure traffic from application Pod traffic using
  # dedicated subnets/security groups (secondary ENI)
  subnetSelectorTerms:
    - tags:
        kubernetes.io/role/internal-elb: "1"
  securityGroupSelectorTerms:
    - tags:
        kubernetes.io/cluster/my-cluster: owned
  podSubnetSelectorTerms:
    - tags:
        Purpose: pod-network
  podSecurityGroupSelectorTerms:
    - tags:
        Purpose: pod-network
```

| Campo | Descripción |
|-------|--------------|
| `kmsKeyID` | ARN de una KMS key administrada por el cliente. Cifra el almacenamiento efímero de la instancia y el volumen raíz de EBS |
| `certificateBundles` | Lista de paquetes de certificados de CA personalizados. Se utiliza para cadenas de confianza de proxy/PKI empresariales |
| `podSubnetSelectorTerms` | Subnet dedicada para tráfico de Pod, aislada mediante una ENI secundaria |
| `podSecurityGroupSelectorTerms` | Security group dedicado para tráfico de Pod, aislado mediante una ENI secundaria |

Con `podSubnetSelectorTerms`/`podSecurityGroupSelectorTerms` configurados, el tráfico de infraestructura del node (kubelet, comunicación con el control plane, etc.) y el tráfico de aplicaciones originado por Pods utilizan subnets y security groups separados, de modo que puedes diseñar reglas de security group y network ACLs de forma independiente por tipo de tráfico.

---

## Estrategias de separación de NodePool

### Separación por workload

```yaml
# NodePool for frontend workloads
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: frontend
spec:
  template:
    metadata:
      labels:
        workload-tier: frontend
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
      taints:
        - key: workload-tier
          value: frontend
          effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  weight: 10
---
# NodePool for backend workloads
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: backend
spec:
  template:
    metadata:
      labels:
        workload-tier: backend
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "r"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      taints:
        - key: workload-tier
          value: backend
          effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  weight: 10
```

### Separación por entorno (desarrollo/staging/producción)

```yaml
# Development environment NodePool
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: dev-pool
spec:
  template:
    metadata:
      labels:
        environment: development
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["t", "m"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["medium", "large"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]  # Cost savings
      taints:
        - key: environment
          value: development
          effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: 100
  weight: 1
```

---

## Mejores prácticas para NodePool

### Límites de recursos

Establece siempre límites adecuados para evitar costos descontrolados:

```yaml
spec:
  limits:
    cpu: 1000        # Maximum 1000 vCPUs
    memory: 4000Gi   # Maximum 4TB memory
```

### Configuración de peso

Usa pesos para priorizar NodePools cuando varios pools coincidan:

```yaml
spec:
  weight: 10  # Higher weight = higher priority
```

### Estrategia de labels y taints

Usa labels y taints coherentes para el aislamiento de workloads:

| Caso de uso | Clave de label | Clave de taint | Efecto |
|----------|-----------|-----------|--------|
| Workload tier | `workload-tier` | `workload-tier` | NoSchedule |
| Entorno | `environment` | `environment` | NoSchedule |
| Equipo | `team` | `team` | NoSchedule |
| Workloads de GPU | `accelerator` | `nvidia.com/gpu` | NoSchedule |

---

< [Anterior: Primeros pasos](./01-getting-started.md) | [Tabla de contenidos](./README.md) | [Siguiente: Comportamiento de escalado](./03-scaling-behavior.md) >

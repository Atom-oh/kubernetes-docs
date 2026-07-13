# Cuestionario de configuración de NodePool de EKS Auto Mode

> **Documento relacionado**: [Configuración de NodePool](../../eks-auto-mode/02-nodepool-configuration.md)

## Preguntas de opción múltiple

### 1. ¿Cuáles son los NodePools predeterminados proporcionados por EKS Auto Mode?

- A) default, worker
- B) general-purpose, system
- C) compute, memory
- D) primary, secondary

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) general-purpose, system**

**Explicación:**
EKS Auto Mode proporciona dos NodePools predeterminados:
- **general-purpose**: NodePool predeterminado para workloads (cargas de trabajo) generales, compatible con varios tipos de instancia (c, m, r) y tanto Spot como On-Demand
- **system**: NodePool para componentes del sistema (CoreDNS, kube-proxy, etc.), que usa solo On-Demand con la taint CriticalAddonsOnly aplicada

```yaml
# Auto Mode activation example
autoModeConfig:
  enabled: true
  nodePools:
    - general-purpose
    - system
```

</details>

### 2. ¿Cómo se aplica IMDSv2 como obligatorio en NodeClass?

- A) `httpTokens: optional`
- B) `httpTokens: required`
- C) `httpEndpoint: disabled`
- D) `httpPutResponseHopLimit: 0`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `httpTokens: required`**

**Explicación:**
Establecer `httpTokens: required` en `metadataOptions` de NodeClass aplica solo IMDSv2, lo que mejora la seguridad.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: secure-nodeclass
spec:
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 2
    httpTokens: required  # IMDSv2 required
```

**Mejores prácticas de seguridad:**
- `httpTokens: required`: Aplicar el uso de IMDSv2
- `httpPutResponseHopLimit: 1`: Bloquear el acceso directo a IMDS desde Pods

</details>

### 3. ¿Qué familias de AMI admite EKS Auto Mode?

- A) Amazon Linux 2, Ubuntu
- B) AL2023, Bottlerocket
- C) Windows Server, Amazon Linux 2
- D) Red Hat Enterprise Linux, Ubuntu

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) AL2023, Bottlerocket**

**Explicación:**
EKS Auto Mode solo admite las familias de AMI AL2023 (Amazon Linux 2023) y Bottlerocket. Los nodes de Windows no son compatibles.

**Características de las familias de AMI:**
- **AL2023**: Uso de propósito general, amplio soporte de paquetes
- **Bottlerocket**: OS optimizado para contenedores, tiempo de arranque más rápido, seguridad mejorada

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: custom-nodeclass
spec:
  amiFamily: Bottlerocket  # or AL2023
```

</details>

### 4. ¿Cuál es la clave de label para especificar el fabricante de GPU en un NodePool para workloads de GPU?

- A) `karpenter.k8s.aws/gpu-vendor`
- B) `karpenter.k8s.aws/instance-gpu-manufacturer`
- C) `nvidia.com/gpu-family`
- D) `karpenter.sh/gpu-type`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `karpenter.k8s.aws/instance-gpu-manufacturer`**

**Explicación:**
Puedes especificar el fabricante al seleccionar instancias de GPU.

```yaml
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["g", "p"]
        - key: karpenter.k8s.aws/instance-gpu-manufacturer
          operator: In
          values: ["nvidia"]
```

</details>

### 5. ¿Cuál es la forma correcta de especificar la generación de instancia en un NodePool?

- A) `node.kubernetes.io/instance-generation: "6"`
- B) `karpenter.k8s.aws/instance-generation` with `operator: In`
- C) `eks.amazonaws.com/generation: "6"`
- D) `instance-generation: 6`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `karpenter.k8s.aws/instance-generation` con `operator: In`**

**Explicación:**
Usa labels de Karpenter para especificar la generación de instancia.

```yaml
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]  # Generation 6 or higher
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
```

</details>

### 6. ¿Cuál es la forma correcta de configurar NodeClass para usar solo subnets privadas?

- A) `subnetType: private`
- B) `subnetSelectorTerms` con la etiqueta internal-elb
- C) `privateSubnetsOnly: true`
- D) `networkType: private`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `subnetSelectorTerms` con la etiqueta internal-elb**

**Explicación:**
Usa `subnetSelectorTerms` para seleccionar subnets privadas.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: secure-nodeclass
spec:
  # Use private subnets only
  subnetSelectorTerms:
    - tags:
        kubernetes.io/role/internal-elb: "1"
```

Las subnets públicas usan la etiqueta `kubernetes.io/role/elb: "1"`.

</details>

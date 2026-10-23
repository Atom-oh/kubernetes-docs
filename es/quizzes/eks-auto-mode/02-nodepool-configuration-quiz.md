# Cuestionario sobre la configuración de NodePool de EKS Auto Mode

> **Documento relacionado**: [Configuración de NodePool](../../eks-auto-mode/02-nodepool-configuration.md)

## Preguntas de opción múltiple

### 1. ¿Cuáles son los NodePools integrados opcionales que proporciona EKS Auto Mode?

- A) default, worker
- B) general-purpose, system
- C) compute, memory
- D) primary, secondary

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) general-purpose, system**

**Explicación:**
Cuando se habilitan, `general-purpose` y `system` usan instancias C/M/R bajo demanda de la generación 5 o posterior. General-purpose usa amd64; system admite amd64 y arm64, y tiene un taint `CriticalAddonsOnly`. Para Spot, usa un pool personalizado. Las funciones locales de DNS y de redes de servicios de Auto Mode no son Pods ordinarios que deban programarse en el pool system.

```yaml
# eksctl configuration fragment
autoModeConfig:
  enabled: true
  nodePools: [general-purpose, system]
```

Quitar un nombre integrado elimina su NodePool y drena o termina los nodos administrados. Deshabilitar ambos también significa que debes proporcionar un NodeClass personalizado, en lugar de dar por sentado que existe `default`.

</details>

### 2. ¿Cómo se configura IMDS para los nodos de Auto Mode?

- A) Establecer `metadataOptions.httpTokens: optional` en NodeClass
- B) AWS exige IMDSv2 y un límite de saltos de 1; NodeClass no puede anular estos ajustes
- C) Establecer el límite de saltos en 0 para que funcione IMDSv2
- D) Seleccionar AL2023 para deshabilitar la autenticación de IMDS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) AWS exige IMDSv2 y un límite de saltos de 1; NodeClass no puede anular estos ajustes**

**Explicación:**
Los valores predeterminados de las instancias administradas requieren IMDSv2 y un límite de saltos de 1, y no se pueden cambiar en Auto Mode. El ejemplo anterior de `metadataOptions` correspondía a una API diferente. El límite de saltos restringe los Pods que no usan la red del host; no garantiza el aislamiento de todos los Pods, incluidos los que usan la red del host. Usa identidad de carga de trabajo y una región y configuración explícitas en lugar de depender de las credenciales del nodo. Consulta [restricciones de las instancias administradas](https://docs.aws.amazon.com/eks/latest/userguide/automode-learn-instances.html).

</details>

### 3. ¿Quién selecciona la imagen del sistema operativo para los nodos de Auto Mode?

- A) El usuario elige Amazon Linux 2 o Ubuntu en amiFamily
- B) AWS selecciona la variante administrada de Bottlerocket adecuada
- C) El usuario proporciona cualquier AMI de Windows
- D) El peso de NodePool selecciona AL2023 en lugar de Bottlerocket

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) AWS selecciona la variante administrada de Bottlerocket adecuada**

**Explicación:**
Auto Mode usa variantes de Bottlerocket administradas por AWS. No ofrece la opción `amiFamily: AL2023` ni `amiFamily: Bottlerocket` en AWS NodeClass. Usa los ajustes documentados de NodeClass para almacenamiento, redes, certificados y la configuración del kernel admitida. Estos son diferentes de la selección arbitraria de AMI o de los datos de usuario de shell.

</details>

### 4. ¿Qué etiqueta de NodePool selecciona el fabricante de GPU en Auto Mode?

- A) karpenter.k8s.aws/gpu-vendor
- B) eks.amazonaws.com/instance-gpu-manufacturer
- C) nvidia.com/gpu-family
- D) karpenter.sh/gpu-type

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) eks.amazonaws.com/instance-gpu-manufacturer**

**Explicación:**
Usa la etiqueta de AWS Auto Mode `eks.amazonaws.com/instance-gpu-manufacturer`. Para hardware de GPU de NVIDIA, los requisitos pueden incluir lo siguiente:

```yaml
# Requirements fragment inside a complete NodePool
requirements:
  - key: eks.amazonaws.com/instance-category
    operator: In
    values: ["g", "p"]
  - key: eks.amazonaws.com/instance-gpu-manufacturer
    operator: In
    values: ["nvidia"]
```

Seleccionar el hardware no asigna una GPU a un contenedor. El Pod debe solicitar el recurso extendido correspondiente, como `nvidia.com/gpu`, y usar una imagen o un runtime compatible. En esta auditoría no se ejecutó ninguna carga de trabajo en GPU.

</details>

### 5. ¿Qué condición selecciona la generación 6 de EC2 o una posterior?

- A) node.kubernetes.io/instance-generation: "6"
- B) eks.amazonaws.com/instance-generation con Gt y valor "5"
- C) eks.amazonaws.com/generation: "6"
- D) instance-generation: 6

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) eks.amazonaws.com/instance-generation con Gt y valor "5"**

**Explicación:**
`Gt` establece un límite inferior numérico estricto, por lo que `Gt ["5"]` selecciona la generación 6 y las posteriores. `In ["6"]` selecciona exactamente la generación 6; no es equivalente. Ninguna de las dos condiciones significa que se seleccione solo la generación más reciente disponible.

```yaml
# Requirements fragment inside a complete NodePool
requirements:
  - key: eks.amazonaws.com/instance-generation
    operator: Gt
    values: ["5"]
```

</details>

### 6. ¿Cómo se seleccionan subredes privadas para un NodeClass?

- A) Establecer subnetType: private
- B) Seleccionar IDs o etiquetas de subred revisados y verificar su enrutamiento y configuración de IP
- C) Establecer privateSubnetsOnly: true
- D) Establecer networkType: private

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Seleccionar IDs o etiquetas de subred revisados y verificar su enrutamiento y configuración de IP**

**Explicación:**
`subnetSelectorTerms` selecciona por ID o por etiquetas. Las etiquetas como `kubernetes.io/role/internal-elb` son una convención, no una prueba de que la tabla de rutas sea privada. Los términos son alternativas; varias etiquetas dentro de un mismo término deben coincidir todas. Revisa la selección de VPC y AZ, las rutas y el comportamiento de las IP públicas.

```yaml
# Selection fragment; a complete NodeClass also needs identity and security groups
subnetSelectorTerms:
  - tags:
      kubernetes.io/role/internal-elb: "1"
      Environment: production
advancedNetworking:
  associatePublicIPAddress: false
```

Establecer `associatePublicIPAddress: false` impide la asignación de IP públicas, pero no crea rutas NAT ni puntos de conexión de VPC. Proporciona la configuración completa de identidad y grupos de seguridad de NodeClass, y verifica que esté listo.

</details>

### 7. ¿Qué ocurre cuando cambias ajustes de kubelet, como `maxPods`, en un NodeClass de Auto Mode existente?

- A) EKS aplica parches a kubelet en los nodos en ejecución sin interrupciones
- B) Los nodos existentes conservan los ajustes anteriores y solo los nodos nuevos usan el cambio
- C) Los nodos que usan el NodeClass se marcan como desfasados y EKS los reemplaza por nodos que usan los nuevos ajustes
- D) Debes reiniciar kubelet en cada nodo mediante SSH

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Los nodos que usan el NodeClass se marcan como desfasados y EKS los reemplaza por nodos que usan los nuevos ajustes**

**Explicación:**
Los ajustes de kubelet en `spec.advancedCompute.kubelet` se aplican cuando se crea un nodo. Si los editas, los nodos existentes quedan desfasados, por lo que EKS los reemplaza en lugar de cambiar un nodo en ejecución; revisa primero los PDB y los presupuestos de interrupción. `maxPods` es solo un límite máximo: el valor efectivo es el menor entre el valor que configures, las direcciones IP que proporciona el tipo de instancia y el límite de Auto Mode de 110 Pods por nodo.

```yaml
# NodeClass fragment
advancedCompute:
  kubelet:
    maxPods: 60
    podPidsLimit: 4096
```

</details>

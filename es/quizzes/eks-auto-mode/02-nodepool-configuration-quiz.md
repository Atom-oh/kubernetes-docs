# Cuestionario de configuración de NodePool de EKS Auto Mode

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
Cuando están habilitados, `general-purpose` y `system` usan instancias On-Demand C/M/R de la generación 5 o posterior. `general-purpose` usa amd64; `system` admite amd64 y arm64, y tiene la taint `CriticalAddonsOnly`. Use un pool personalizado para Spot. Las funciones locales de DNS y redes de servicio de Auto Mode no son Pods ordinarios que deban programarse en el pool `system`.

```yaml
# eksctl configuration fragment
autoModeConfig:
  enabled: true
  nodePools: [general-purpose, system]
```

Eliminar un nombre integrado elimina su NodePool y drena/termina los nodos administrados. Si deshabilita ambos, también deberá proporcionar un NodeClass personalizado; no dé por hecho que existe uno llamado `default`.

</details>

### 2. ¿Cómo se configura IMDS para los nodos de Auto Mode?

- A) Establecer `metadataOptions.httpTokens: optional` en NodeClass
- B) AWS aplica IMDSv2 y el límite de saltos 1; NodeClass no puede anular estos ajustes
- C) Establecer el límite de saltos en 0 para que funcione IMDSv2
- D) Elegir AL2023 para desactivar la autenticación de IMDS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) AWS aplica IMDSv2 y el límite de saltos 1; NodeClass no puede anular estos ajustes**

**Explicación:**
Los valores predeterminados de las instancias administradas requieren IMDSv2 y un límite de saltos de 1, y no se pueden cambiar en Auto Mode. El ejemplo anterior de `metadataOptions` correspondía a otra API. El límite de saltos restringe los Pods que no usan la red del host; no garantiza el aislamiento de todos los Pods, incluidos los que usan la red del host. Use la identidad de carga de trabajo y configure la región de forma explícita, en vez de depender de las credenciales del nodo. Consulte las [restricciones de las instancias administradas](https://docs.aws.amazon.com/eks/latest/userguide/automode-learn-instances.html).

</details>

### 3. ¿Quién selecciona la imagen del sistema operativo para los nodos de Auto Mode?

- A) El usuario elige Amazon Linux 2 o Ubuntu en amiFamily
- B) AWS selecciona la variante de Bottlerocket administrada adecuada
- C) El usuario proporciona cualquier AMI de Windows
- D) El peso del NodePool selecciona AL2023 en vez de Bottlerocket

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) AWS selecciona la variante de Bottlerocket administrada adecuada**

**Explicación:**
Auto Mode usa variantes de Bottlerocket administradas por AWS. AWS NodeClass no ofrece una opción `amiFamily: AL2023` ni `amiFamily: Bottlerocket`. Use los ajustes de NodeClass documentados para el almacenamiento, las redes, los certificados y la configuración de kernel compatible. Son opciones distintas de seleccionar una AMI arbitraria o usar datos de usuario de shell.

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
Use la etiqueta de AWS Auto Mode `eks.amazonaws.com/instance-gpu-manufacturer`. Para hardware GPU de NVIDIA, los requisitos pueden incluir:

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

Seleccionar el hardware no asigna una GPU a un contenedor. El Pod debe solicitar el recurso extendido correspondiente, como `nvidia.com/gpu`, y usar una imagen/runtime compatible. En esta auditoría no se ejecutó ninguna carga de trabajo con GPU.

</details>

### 5. ¿Qué condición selecciona generaciones EC2 6 o posteriores?

- A) node.kubernetes.io/instance-generation: "6"
- B) eks.amazonaws.com/instance-generation con Gt y el valor "5"
- C) eks.amazonaws.com/generation: "6"
- D) instance-generation: 6

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) eks.amazonaws.com/instance-generation con Gt y el valor "5"**

**Explicación:**
`Gt` establece un límite inferior numérico estricto, por lo que `Gt ["5"]` selecciona la generación 6 y las posteriores. `In ["6"]` selecciona únicamente la generación 6; no es equivalente. Ninguna de estas condiciones significa que se seleccione solo la generación disponible más reciente.

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
- B) Seleccionar ID/etiquetas de subred revisados y verificar sus rutas y ajustes de IP
- C) Establecer privateSubnetsOnly: true
- D) Establecer networkType: private

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Seleccionar ID/etiquetas de subred revisados y verificar sus rutas y ajustes de IP**

**Explicación:**
`subnetSelectorTerms` selecciona subredes por ID o por etiquetas. Las etiquetas como `kubernetes.io/role/internal-elb` son convenciones, no pruebas de que la tabla de rutas sea privada. Los términos son alternativas; dentro de un mismo término deben coincidir todas las etiquetas. Revise la selección de VPC/AZ, las rutas y el comportamiento de la IP pública.

```yaml
# Selection fragment; a complete NodeClass also needs identity and security groups
subnetSelectorTerms:
  - tags:
      kubernetes.io/role/internal-elb: "1"
      Environment: production
advancedNetworking:
  associatePublicIPAddress: false
```

Establecer `associatePublicIPAddress: false` evita asignar una IP pública, pero no crea rutas NAT ni endpoints de VPC. Proporcione la configuración completa de identidad y grupos de seguridad del NodeClass, y verifique que esté listo.

</details>

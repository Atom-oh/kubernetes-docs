# Cuestionario avanzado de infraestructura

> **Documento relacionado**: [Infraestructura avanzada](../../ops/02-infrastructure-advanced.md)

## Preguntas de opción múltiple

### 1. ¿Cuál es el propósito principal de los target groups ponderados de NLB en un despliegue blue/green?

- A) Reducir costos usando menos load balancers
- B) Controlar la distribución del tráfico entre versiones del cluster
- C) Mejorar el rendimiento de la terminación SSL
- D) Eliminar la necesidad de health checks

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Controlar la distribución del tráfico entre versiones del cluster**

**Explicación:**
Los target groups ponderados de NLB permiten un cambio gradual de tráfico entre clusters blue (actual) y green (nuevo). Al ajustar los pesos (por ejemplo, 90:10, 50:50, 0:100), los operadores pueden realizar despliegues controlados y revertir rápidamente si se detectan problemas.

</details>

### 2. En una estrategia de cluster EKS de una sola zona, ¿por qué podrías desplegar data nodes solo en una Availability Zone?

- A) Para reducir los costos de transferencia de datos entre AZ
- B) Para simplificar la configuración de DNS
- C) Para evitar el uso de múltiples subnets
- D) Para eliminar la necesidad de persistent volumes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Para reducir los costos de transferencia de datos entre AZ**

**Explicación:**
La transferencia de datos entre AZ genera costos en AWS. Para workloads intensivos en datos con almacenamiento local (como bases de datos), mantener todas las réplicas en una sola AZ elimina estos costos mientras se depende de la replicación a nivel de aplicación para la durabilidad.

</details>

### 3. ¿Qué característica de Kubernetes garantiza que los pods se distribuyan entre diferentes zonas o nodes?

- A) PodAffinity
- B) TopologySpreadConstraints
- C) ResourceQuota
- D) LimitRange

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) TopologySpreadConstraints**

**Explicación:**
TopologySpreadConstraints controla cómo se distribuyen los pods entre dominios de topología (zonas, nodes, regiones). Garantiza una distribución uniforme para alta disponibilidad y puede configurarse con los parámetros `maxSkew`, `topologyKey` y `whenUnsatisfiable`.

</details>

### 4. ¿En qué se diferencia el enrutamiento ponderado de Route53 de los target groups ponderados de NLB?

- A) Route53 funciona a nivel de DNS, NLB funciona a nivel de conexión
- B) Route53 solo admite pesos iguales
- C) NLB no admite health checks
- D) Route53 requiere VPC peering

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Route53 funciona a nivel de DNS, NLB funciona a nivel de conexión**

**Explicación:**
El enrutamiento ponderado de Route53 distribuye el tráfico en el momento de la resolución DNS, mientras que los target groups ponderados de NLB lo distribuyen a nivel de conexión. El enrutamiento basado en DNS tiene consideraciones de TTL, mientras que NLB proporciona cambios de tráfico más inmediatos.

</details>

### 5. ¿Cuál es el valor recomendado de `maxSkew` para TopologySpreadConstraints en un despliegue de 3 AZ?

- A) 0
- B) 1
- C) 3
- D) 10

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 1**

**Explicación:**
Un `maxSkew` de 1 garantiza que los pods se distribuyan uniformemente con, como máximo, una diferencia de un pod entre dominios de topología. Esto proporciona un buen equilibrio y aun así permite flexibilidad de programación cuando los nodes tienen restricciones de recursos.

</details>

### 6. En una arquitectura de clusters blue/green, ¿qué debería compartirse entre clusters?

- A) Worker nodes
- B) DNS externo y load balancer
- C) Almacenamiento etcd
- D) Kubernetes API server

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) DNS externo y load balancer**

**Explicación:**
Los clusters blue/green son clusters EKS separados que comparten infraestructura externa como registros DNS y load balancers. Esto permite cambiar el tráfico entre clusters sin modificar los endpoints visibles para los clientes.

</details>

### 7. ¿Qué sucede cuando se establece `whenUnsatisfiable: DoNotSchedule` en TopologySpreadConstraints?

- A) Los pods se programan en cualquier lugar sin importar las restricciones
- B) Los pods permanecen pendientes si las restricciones no pueden satisfacerse
- C) Los pods se eliminan automáticamente
- D) La restricción se ignora

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los pods permanecen pendientes si las restricciones no pueden satisfacerse**

**Explicación:**
`DoNotSchedule` impide la programación de pods cuando se violaría la restricción de distribución. Esto garantiza el cumplimiento estricto de los requisitos de topología, pero puede provocar que haya pods pendientes si la topología del cluster no admite la restricción.

</details>

### 8. Para failover automatizado entre clusters blue/green, ¿qué servicio de AWS puede usarse con health checks?

- A) AWS Config
- B) Health checks de Route53 con enrutamiento de failover
- C) AWS Inspector
- D) AWS Trusted Advisor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Health checks de Route53 con enrutamiento de failover**

**Explicación:**
Los health checks de Route53 monitorean continuamente la disponibilidad de endpoints y pueden cambiar automáticamente el tráfico a un cluster saludable usando una política de enrutamiento de failover. Esto habilita la recuperación ante desastres automatizada sin intervención manual.

</details>

### 9. ¿Cuál es una consideración clave al usar load balancing entre zonas de NLB?

- A) Siempre es gratuito
- B) Puede generar cargos adicionales por transferencia de datos
- C) Requiere VPC peering
- D) Solo funciona con el protocolo TCP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Puede generar cargos adicionales por transferencia de datos**

**Explicación:**
Cuando el load balancing entre zonas está habilitado, NLB distribuye el tráfico de manera uniforme entre todos los targets registrados en todas las AZ habilitadas, lo que puede generar cargos por transferencia de datos entre AZ. Considera este costo al diseñar despliegues multi-AZ.

</details>

### 10. En un despliegue de cluster zonal (a-zone blue, c-zone green), ¿cuál es el beneficio principal?

- A) Menor complejidad de red
- B) Aislamiento de fallas y rutas de actualización independientes
- C) Menores costos de cómputo
- D) Replicación automática de datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aislamiento de fallas y rutas de actualización independientes**

**Explicación:**
Los clusters zonales proporcionan aislamiento de dominios de falla: un problema en una zona no afecta al otro cluster. Esto también permite pruebas de actualización independientes y despliegues graduales, lo que reduce el riesgo durante las actualizaciones de versión de Kubernetes.

</details>

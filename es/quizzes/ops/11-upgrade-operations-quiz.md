# Cuestionario sobre operaciones de actualización

> **Documento relacionado**: [Operaciones de actualización](../../ops/11-upgrade-operations.md)

## Preguntas de opción múltiple

### 1. ¿Durante cuánto tiempo AWS da soporte a cada versión de EKS Kubernetes bajo soporte estándar?

- A) 6 meses
- B) 12 meses
- C) 14 meses
- D) 24 meses

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) 14 meses**

**Explicación:**
AWS proporciona 14 meses de soporte estándar para cada versión de Kubernetes en EKS. Después de eso, los clusters pueden migrarse a soporte extendido (con costo adicional) o deben actualizarse. Se recomienda planificar las actualizaciones dentro del período de soporte estándar.

</details>

### 2. ¿Qué herramienta detecta APIs de Kubernetes obsoletas en tu cluster?

- A) kubectl
- B) Pluto
- C) Helm
- D) Terraform

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Pluto**

**Explicación:**
Pluto escanea manifests de Kubernetes, releases de Helm y clusters activos en busca de versiones de API obsoletas o eliminadas. Ayuda a identificar recursos que deben actualizarse antes de actualizar a una versión en la que esas APIs ya no existen.

</details>

### 3. ¿Cuál es el propósito de Velero en las operaciones de actualización de EKS?

- A) Actualizar la versión de Kubernetes
- B) Hacer backup y restaurar recursos del cluster antes de la actualización
- C) Monitorear el rendimiento del cluster
- D) Administrar node groups

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Hacer backup y restaurar recursos del cluster antes de la actualización**

**Explicación:**
Velero proporciona capacidades de backup y restauración para recursos de Kubernetes y persistent volumes. Realizar un backup de Velero antes de las actualizaciones permite la recuperación si la actualización causa problemas, proporcionando una red de seguridad para la operación.

</details>

### 4. En la arquitectura Terraform de 3 capas, ¿cuál es el orden correcto de actualización?

- A) Workload -> Platform -> Foundation
- B) Platform -> Foundation -> Workload
- C) Foundation -> Platform -> Workload
- D) Todas las capas simultáneamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Foundation -> Platform -> Workload**

**Explicación:**
El orden de actualización sigue las dependencias: primero Foundation (VPC, IAM), ya que Platform depende de ella; luego Platform (cluster de EKS), ya que Workload depende de ella; y finalmente Workload (aplicaciones). Esto asegura que las dependencias de cada capa ya estén actualizadas.

</details>

### 5. En EKS Auto Mode, ¿qué ocurre con los nodes durante una actualización de versión de Kubernetes?

- A) Los nodes se actualizan in-place sin reinicio
- B) Los nodes se reemplazan automáticamente por nodes de la nueva versión
- C) Los nodes deben eliminarse manualmente
- D) Los nodes no se ven afectados por las actualizaciones de versión

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los nodes se reemplazan automáticamente por nodes de la nueva versión**

**Explicación:**
Después de actualizar el control plane de EKS, Auto Mode rota automáticamente los nodes para que coincidan con la nueva versión. Este proceso cordona los nodes antiguos, drena los workloads y aprovisiona nuevos nodes con la versión actualizada de kubelet.

</details>

### 6. ¿Qué debe verificarse con los Pod Disruption Budgets (PDBs) antes de la actualización?

- A) Que no existan PDBs
- B) Que los PDBs permitan suficiente disrupción para el reemplazo progresivo de nodes
- C) Que los PDBs estén configurados en cero
- D) Que los PDBs referencien versiones de API correctas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Que los PDBs permitan suficiente disrupción para el reemplazo progresivo de nodes**

**Explicación:**
Los PDBs demasiado restrictivos (por ejemplo, maxUnavailable: 0 con minAvailable: 100%) pueden bloquear el drenado de nodes durante las actualizaciones. Antes de actualizar, asegúrate de que los PDBs permitan suficiente disrupción para que el proceso de reemplazo progresivo pueda continuar.

</details>

### 7. ¿Cuál es la estrategia de actualización blue/green para clusters de EKS?

- A) Actualizar ambos clusters simultáneamente
- B) Crear un nuevo cluster con la nueva versión y desplazar gradualmente el tráfico
- C) Actualizar in-place con capacidad de rollback
- D) Ejecutar ambas versiones en los mismos nodes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crear un nuevo cluster con la nueva versión y desplazar gradualmente el tráfico**

**Explicación:**
La actualización blue/green crea un nuevo cluster "green" que ejecuta la versión objetivo de Kubernetes junto al cluster "blue" existente. El tráfico se desplaza gradualmente usando enrutamiento ponderado, lo que permite un rollback sencillo al devolver el tráfico a blue si surgen problemas.

</details>

### 8. ¿Qué validación posterior a la actualización debe realizarse?

- A) Solo comprobar si los pods están en ejecución
- B) Verificar el estado de los nodes, la salud de los pods, la funcionalidad de los addons y el comportamiento de la aplicación
- C) No se necesita validación
- D) Solo ejecutar Pluto de nuevo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Verificar el estado de los nodes, la salud de los pods, la funcionalidad de los addons y el comportamiento de la aplicación**

**Explicación:**
La validación posterior a la actualización debe incluir: todos los nodes en Ready, pods en Running, addons del cluster (CoreDNS, kube-proxy, CNI) funcionales, ingress/egress funcionando, operaciones de storage exitosas y health checks específicos de la aplicación aprobados.

</details>

### 9. ¿En qué se diferencia el soporte extendido de EKS del soporte estándar?

- A) El soporte extendido es gratuito
- B) El soporte extendido proporciona meses adicionales más allá del estándar con costo adicional
- C) El soporte extendido solo cubre parches de seguridad
- D) El soporte extendido es solo para Fargate

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El soporte extendido proporciona meses adicionales más allá del estándar con costo adicional**

**Explicación:**
El soporte extendido de EKS permite que los clusters se ejecuten en versiones antiguas de Kubernetes más allá del período estándar de 14 meses, pero con un costo adicional por hora por cluster. Esto proporciona flexibilidad para organizaciones que necesitan más tiempo para actualizar.

</details>

### 10. Al actualizar, ¿por qué es importante comprobar la compatibilidad de los addons?

- A) Los addons se actualizan automáticamente
- B) Algunas versiones de addons solo son compatibles con versiones específicas de Kubernetes
- C) Los addons no afectan las actualizaciones
- D) Los addons deben eliminarse antes de la actualización

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Algunas versiones de addons solo son compatibles con versiones específicas de Kubernetes**

**Explicación:**
Los addons administrados de EKS (VPC CNI, CoreDNS, kube-proxy) y los addons de terceros tienen matrices de compatibilidad de versiones con versiones de Kubernetes. Actualizar a una versión incompatible de un addon puede romper la funcionalidad del cluster. Comprueba y planifica las actualizaciones de addons junto con la actualización del cluster.

</details>

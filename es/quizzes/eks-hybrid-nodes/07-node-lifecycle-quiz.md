# Cuestionario sobre la gestión del ciclo de vida de Node

> Este cuestionario evalúa tu comprensión del documento [Gestión del ciclo de vida de Node](../../eks-hybrid-nodes/07-node-lifecycle.md).

---

1. ¿Cuál es el propósito principal de configurar `systemReserved` y `kubeReserved` en la configuración kubelet de NodeConfig?
   - A) Ajustar automáticamente las solicitudes de recursos de los Pod
   - B) Reservar recursos para procesos del sistema y componentes de Kubernetes para garantizar la estabilidad del Node
   - C) Aumentar los recursos totales disponibles en el Node
   - D) Determinar la prioridad de programación de los Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Reservar recursos para procesos del sistema y componentes de Kubernetes para garantizar la estabilidad del Node**

**Explicación:**
`systemReserved` reserva recursos para el OS y los daemons del sistema (sshd, udev, etc.), mientras que `kubeReserved` reserva recursos para kubelet y containerd. Esto evita que los Pod consuman todos los recursos del Node, manteniendo la estabilidad del Node.

</details>

---

2. ¿Cuál es la diferencia entre `evictionHard` y `evictionSoft` de kubelet?
   - A) `evictionHard` es un límite blando y `evictionSoft` es un límite estricto
   - B) `evictionHard` desencadena el desalojo inmediato, mientras que `evictionSoft` desaloja después de un período de gracia
   - C) `evictionHard` solo desaloja Pod, mientras que `evictionSoft` apaga el Node
   - D) Ambas configuraciones se comportan de forma idéntica y solo tienen nombres diferentes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `evictionHard` desencadena el desalojo inmediato, mientras que `evictionSoft` desaloja después de un período de gracia**

**Explicación:**
Cuando se alcanza el umbral de `evictionHard`, kubelet desaloja inmediatamente los Pod. `evictionSoft` solo desaloja cuando el umbral persiste durante la duración especificada en `evictionSoftGracePeriod`, lo que evita terminaciones abruptas de Pod.

</details>

---

3. Según la política de desfase de versiones de Kubernetes, ¿cuál es la versión más antigua de kubelet que puede ejecutarse cuando el control plane de EKS está en la versión 1.31?
   - A) 1.27
   - B) 1.28
   - C) 1.29
   - D) 1.30

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 1.28**

**Explicación:**
Según la política de desfase de versiones de Kubernetes, kubelet puede tener hasta tres versiones menores menos que el API server. Con el API server en 1.31, kubelet es compatible con 1.31, 1.30, 1.29 y 1.28. La versión 1.27 es n-4 y no está soportada.

</details>

---

4. ¿Cuál es el principio fundamental de la estrategia de actualización canary?
   - A) Actualizar todos los Nodes simultáneamente
   - B) Actualizar primero un Node, validar y luego continuar con el resto
   - C) Eliminar Nodes y crear nuevos
   - D) Realizar actualizaciones in-place sin downtime

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Actualizar primero un Node, validar y luego continuar con el resto**

**Explicación:**
Una actualización canary actualiza primero un único Node "canary" y valida el resultado. Si no se encuentran problemas, se realiza una rolling upgrade para los Nodes restantes, minimizando el riesgo.

</details>

---

5. ¿Qué label asigna automáticamente nodeadm al inicializar hybrid nodes?
   - A) `node-role.kubernetes.io/hybrid=true`
   - B) `topology.kubernetes.io/zone=on-premises`
   - C) `eks.amazonaws.com/compute-type=hybrid`
   - D) `kubernetes.io/os=hybrid`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) `eks.amazonaws.com/compute-type=hybrid`**

**Explicación:**
nodeadm asigna automáticamente el label `eks.amazonaws.com/compute-type=hybrid` durante la inicialización de hybrid node. No es necesario añadir este label manualmente a `--node-labels` y se usa para la afinidad de Cilium, la colocación de workloads y más.

</details>

---

6. ¿Cuál es la acción correcta cuando una SSM Hybrid Activation ha expirado?
   - A) Extender la fecha de expiración de la activación existente
   - B) Crear una nueva SSM Hybrid Activation y actualizar nodeconfig.yaml
   - C) Cambiar a IAM Roles Anywhere
   - D) Reiniciar kubelet para la renovación automática

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crear una nueva SSM Hybrid Activation y actualizar nodeconfig.yaml**

**Explicación:**
Las SSM Hybrid Activations no pueden extender sus fechas de expiración una vez que han expirado. Debes crear una nueva activación, actualizar `activationCode` y `activationId` en nodeconfig.yaml, y volver a registrar los Nodes si es necesario.

</details>

---

7. ¿Cuál es el orden correcto para actualizar los componentes de Kubernetes?
   - A) Actualizar primero los Nodes y luego el control plane
   - B) Actualizar el control plane y los Nodes simultáneamente
   - C) Actualizar primero el control plane (EKS) y luego actualizar los Nodes
   - D) El orden no importa

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Actualizar primero el control plane (EKS) y luego actualizar los Nodes**

**Explicación:**
Según la política de desfase de versiones de Kubernetes, kubelet no puede ser más nuevo que el API server. Siempre debes actualizar primero el control plane y luego actualizar los Nodes. Actualizar los Nodes antes que el control plane causa problemas de compatibilidad.

</details>

---

8. Si `shutdownGracePeriod: 60s` y `shutdownGracePeriodCriticalPods: 20s` están configurados, ¿cuánto tiempo de gracia para la terminación reciben los Pod regulares?
   - A) 20 segundos
   - B) 40 segundos
   - C) 60 segundos
   - D) 80 segundos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 40 segundos**

**Explicación:**
`shutdownGracePeriodCriticalPods` está incluido dentro de `shutdownGracePeriod`. Al restar los 20 segundos reservados para los Pod críticos del período de gracia total de 60 segundos, quedan 40 segundos para la terminación de los Pod regulares. Los Pod críticos (con priority class system-cluster-critical o system-node-critical) se terminan durante los últimos 20 segundos.

</details>

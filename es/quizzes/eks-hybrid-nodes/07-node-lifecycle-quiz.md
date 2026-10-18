# Cuestionario sobre la gestión del ciclo de vida de los nodos

> Este cuestionario evalúa tu comprensión del documento [Gestión del ciclo de vida de los nodos](../../eks-hybrid-nodes/07-node-lifecycle.md).

---

1. ¿Cuál es el propósito principal de establecer `systemReserved` y `kubeReserved` en la configuración del kubelet de NodeConfig?
   - A) Ajustar automáticamente las solicitudes de recursos de los Pods
   - B) Reservar recursos para los procesos del sistema y los componentes de Kubernetes al calcular Node Allocatable
   - C) Aumentar la cantidad total de recursos disponibles en el nodo
   - D) Determinar la prioridad de programación de los Pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Reservar recursos para los procesos del sistema y los componentes de Kubernetes al calcular Node Allocatable**

**Explicación:**
`systemReserved` reserva recursos para el sistema operativo y los servicios del sistema (sshd, udev, entre otros), mientras que `kubeReserved` los reserva para kubelet y containerd. Estas reservas reducen la capacidad asignable. Para aplicar reservas de cgroups a los procesos del host se necesita configuración adicional; estos campos por sí solos no garantizan la estabilidad.

</details>

---

2. ¿Cuál es la diferencia entre `evictionHard` y `evictionSoft` de kubelet?
   - A) `evictionHard` es un límite blando y `evictionSoft` es un límite estricto
   - B) `evictionHard` no tiene un período de observación blando; `evictionSoft` requiere que el umbral se mantenga durante cierto tiempo
   - C) `evictionHard` solo expulsa Pods, mientras que `evictionSoft` apaga el nodo
   - D) Ambas opciones se comportan igual y solo tienen nombres distintos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `evictionHard` no tiene un período de observación blando; `evictionSoft` requiere que el umbral se mantenga durante cierto tiempo**

**Explicación:**
Primero, kubelet intenta recuperar recursos a nivel del nodo y, cuando es necesario, expulsa Pods. Los umbrales estrictos no tienen un período de observación blando y provocan la expulsión sin conceder a los Pods un período de gracia para terminar. Un umbral blando debe persistir durante `evictionSoftGracePeriod`, mientras que `evictionMaxPodGracePeriod` limita por separado el período de gracia para la terminación de los Pods. Esto no evita una expulsión por umbral estricto ni una terminación por falta de memoria (OOM).

</details>

---

3. Según la política de compatibilidad de versiones de Kubernetes, ¿cuál es la versión más antigua de kubelet que puede ejecutarse en el ejemplo histórico con un servidor de API en 1.31, sin tener en cuenta la disponibilidad actual de versiones de EKS?
   - A) 1.27
   - B) 1.28
   - C) 1.29
   - D) 1.30

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 1.28**

**Explicación:**
Según la política de compatibilidad de versiones de Kubernetes, kubelet puede tener hasta tres versiones menores menos que el servidor de API. Si el servidor de API está en 1.31, kubelet es compatible con las versiones 1.31, 1.30, 1.29 y 1.28. La versión 1.27 está cuatro versiones por detrás (n-4) y no es compatible.

</details>

---

4. ¿Cuál es el principio fundamental de una estrategia de actualización canary?
   - A) Actualizar todos los nodos a la vez
   - B) Actualizar primero un nodo, validar el resultado y luego continuar con los demás
   - C) Eliminar los nodos y crear otros nuevos
   - D) Actualizar los nodos en el sitio y sin tiempo de inactividad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Actualizar primero un nodo, validar el resultado y luego continuar con los demás**

**Explicación:**
En una actualización canary, primero se actualiza un único nodo canary y se valida el resultado. Si no se detectan problemas, se continúa con una actualización gradual de los nodos restantes para reducir el riesgo.

</details>

---

5. ¿Qué etiqueta asigna nodeadm automáticamente al inicializar nodos híbridos?
   - A) `node-role.kubernetes.io/hybrid=true`
   - B) `topology.kubernetes.io/zone=on-premises`
   - C) `eks.amazonaws.com/compute-type=hybrid`
   - D) `kubernetes.io/os=hybrid`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) `eks.amazonaws.com/compute-type=hybrid`**

**Explicación:**
nodeadm asigna automáticamente la etiqueta `eks.amazonaws.com/compute-type=hybrid` durante la inicialización de los nodos híbridos. No es necesario añadirla manualmente a `--node-labels`; se usa, entre otras cosas, para la afinidad de Cilium y la ubicación de las cargas de trabajo.

</details>

---

6. Una activación de SSM venció, pero sus nodos ya están registrados. ¿Qué acción corresponde?
   - A) Extender la fecha de vencimiento de la activación existente
   - B) Mantener los registros existentes y usar una activación nueva solo para los registros nuevos que se necesiten
   - C) Cambiar a IAM Roles Anywhere
   - D) Reiniciar kubelet para que renueve la activación automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Mantener los registros existentes y usar una activación nueva solo para los registros nuevos que se necesiten**

**Explicación:**
El vencimiento de una activación impide registrar nodos nuevos. Los nodos que ya están registrados siguen bajo administración hasta que se anule su registro de forma explícita. No desinstales ni vuelvas a registrar nodos en buen estado solo porque venció la activación; las credenciales del agente, los permisos del rol y la conectividad son cuestiones independientes.

</details>

---

7. Los nodos ya tienen la misma versión menor que el plano de control. ¿En qué orden se debe pasar a la siguiente versión menor?
   - A) Actualizar primero los nodos y luego el plano de control
   - B) Actualizar el plano de control y los nodos al mismo tiempo
   - C) Actualizar primero el plano de control de EKS y luego los nodos
   - D) El orden no importa

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Actualizar primero el plano de control de EKS y luego los nodos**

**Explicación:**
Según la política de compatibilidad de versiones de Kubernetes, kubelet no puede tener una versión más nueva que el servidor de API. Para pasar a la siguiente versión menor, actualiza primero el plano de control y luego los nodos. Si algunos nodos tienen una versión anterior a la actual del plano de control, puedes actualizarlos primero para ponerlos al día; esa actualización no infringe la política de compatibilidad.

</details>

---

8. Si se configuran `shutdownGracePeriod: 60s` y `shutdownGracePeriodCriticalPods: 20s`, ¿qué ventana total se asigna al grupo de Pods normales durante el apagado?
   - A) 20 segundos
   - B) 40 segundos
   - C) 60 segundos
   - D) 80 segundos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 40 segundos**

**Explicación:**
`shutdownGracePeriodCriticalPods` forma parte de `shutdownGracePeriod`. Al restar los 20 segundos reservados para los Pods críticos del período total de 60 segundos, quedan 40 segundos para terminar los Pods normales. Los últimos 20 segundos se reservan para los Pods críticos. Estas son las ventanas configuradas; no garantizan el período de gracia de cada Pod durante un apagado forzado. También se aplica el parámetro individual `terminationGracePeriodSeconds`.

</details>

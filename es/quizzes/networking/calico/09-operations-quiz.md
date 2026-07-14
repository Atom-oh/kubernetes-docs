# Cuestionario de operaciones

> **Documento relacionado**: [Operaciones](../../../networking/calico/09-operations.md)
> **Última actualización**: February 22, 2026

## Cuestionario

1. ¿Cuáles son los tres métodos principales de instalación de Calico?
   - A) Docker, Podman, containerd
   - B) Basado en manifiestos (kubectl), basado en Operator (Tigera), Helm
   - C) CLI, GUI, API
   - D) Binario, gestor de paquetes, compilación desde código fuente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Basado en manifiestos (kubectl), basado en Operator (Tigera), Helm**

**Explicación:**
Calico se puede instalar mediante: 1) instalación basada en manifiestos con kubectl apply en manifiestos YAML, 2) instalación basada en Operator mediante el Tigera Operator (recomendado), o 3) charts de Helm para Deployments personalizables. El método Operator generalmente se recomienda para producción, ya que administra el ciclo de vida de Calico.

</details>

2. ¿Qué comando de calicoctl muestra el estado de los nodos de Calico, incluido el estado de los pares BGP?
   - A) calicoctl get nodes
   - B) calicoctl node status
   - C) calicoctl describe node
   - D) calicoctl show peers

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) calicoctl node status**

**Explicación:**
El comando `calicoctl node status` muestra el estado del nodo de Calico, incluida la información de peering BGP, mostrando qué pares están establecidos, su estado y cualquier problema de conexión. Esto es esencial para solucionar problemas de enrutamiento BGP.

</details>

3. ¿Qué comando muestra la asignación de bloques IPAM entre los nodos?
   - A) calicoctl ipam show --show-blocks
   - B) calicoctl get ipamblocks
   - C) kubectl get ipamblocks -o wide
   - D) calicoctl describe ipam

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) calicoctl ipam show --show-blocks**

**Explicación:**
El comando `calicoctl ipam show --show-blocks` muestra información detallada de IPAM, incluidos qué bloques de IP están asignados a qué nodos, la utilización de cada bloque y las estadísticas generales del pool de IP. Esto es crucial para diagnosticar problemas de asignación de IP.

</details>

4. ¿Qué endpoint de métricas de Prometheus expone las estadísticas de rendimiento y políticas de Felix?
   - A) :9090/metrics
   - B) :9091/metrics
   - C) :9094/metrics
   - D) :8080/metrics

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) :9091/metrics**

**Explicación:**
Felix expone métricas de Prometheus en el puerto 9091 de forma predeterminada. Estas métricas incluyen recuentos de reglas de políticas, latencia de programación del dataplane, estadísticas de iptables/eBPF y recuentos de errores. Esto debe habilitarse en FelixConfiguration con `prometheusMetricsEnabled: true`.

</details>

5. ¿Qué puerto utiliza Typha para su endpoint de métricas de Prometheus?
   - A) :9091/metrics
   - B) :9093/metrics
   - C) :9094/metrics
   - D) :9095/metrics

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) :9093/metrics**

**Explicación:**
Typha expone métricas de Prometheus en el puerto 9093 de forma predeterminada. Las métricas de Typha incluyen recuentos de conexiones a instancias de Felix, latencia de sincronización del datastore y estadísticas de caché. Supervisar Typha es importante para comprender el rendimiento de fan-out del datastore en clústeres grandes.

</details>

6. Un Pod no puede obtener una dirección IP. ¿Qué es lo primero que se debe comprobar?
   - A) Registros de kube-proxy
   - B) Disponibilidad de IPPool y asignación de bloques IPAM
   - C) Configuración de DNS
   - D) Uso de CPU del nodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Disponibilidad de IPPool y asignación de bloques IPAM**

**Explicación:**
Cuando un Pod no obtiene una IP, primero compruebe si IPPool tiene direcciones disponibles usando `calicoctl ipam show`. Verifique que los bloques IPAM puedan asignarse al nodo y que el selector de IPPool coincida con el nodo. Compruebe también los registros de Felix en busca de errores relacionados con IPAM.

</details>

7. ¿Qué se debe verificar cuando no se establece el peering BGP entre nodos?
   - A) Resolución DNS de Pod
   - B) Conectividad de red en el puerto BGP (179), BGPConfiguration y selectores de nodos
   - C) Enlaces de volúmenes persistentes
   - D) Tokens de cuentas de Service

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Conectividad de red en el puerto BGP (179), BGPConfiguration y selectores de nodos**

**Explicación:**
Para problemas de peering BGP, verifique: 1) conectividad de red entre nodos en el puerto TCP 179, 2) que los recursos BGPConfiguration y BGPPeer estén definidos correctamente, 3) que los selectores de nodos coincidan con los nodos previstos, 4) revise `calicoctl node status` y los registros de BIRD para detectar errores específicos de peering.

</details>

8. Se aplica una política de red, pero el tráfico no se bloquea. ¿Cuál es una causa probable?
   - A) El clúster está usando demasiada memoria
   - B) Los selectores de la política no coinciden con los Pods objetivo, o el orden/nivel de la política es incorrecto
   - C) Los nodos deben reiniciarse
   - D) La versión de Kubernetes es demasiado antigua

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los selectores de la política no coinciden con los Pods objetivo, o el orden/nivel de la política es incorrecto**

**Explicación:**
Cuando las políticas no funcionan como se espera, verifique: 1) que los selectores de Pod coincidan correctamente con los Pods objetivo (compruebe las etiquetas), 2) que los selectores de Namespace sean correctos, 3) el orden de los niveles de políticas (los niveles de mayor prioridad se evalúan primero), 4) que no haya políticas Allow en conflicto antes en el orden de evaluación. Use `calicoctl get policy` para revisar las políticas aplicadas.

</details>

9. ¿Cuál es el procedimiento recomendado para actualizar versiones de Calico?
   - A) Eliminar todos los recursos y reinstalar
   - B) Actualizar en el mismo lugar siguiendo las guías de migración específicas de cada versión
   - C) Crear un nuevo clúster y migrar las cargas de trabajo
   - D) Calico se actualiza automáticamente con Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Actualizar en el mismo lugar siguiendo las guías de migración específicas de cada versión**

**Explicación:**
Las actualizaciones de Calico deben seguir la documentación oficial de actualización para su método de instalación. Esto normalmente implica actualizar el Operator o los manifiestos a la nueva versión. Revise las notas de migración específicas de la versión, ya que algunas actualizaciones requieren pasos adicionales. Pruebe primero en un entorno que no sea de producción.

</details>

10. ¿Cuál es la práctica recomendada de denegación predeterminada para las políticas de red de Calico?
    - A) No usar nunca políticas de denegación
    - B) Aplicar políticas de denegación predeterminada a los Namespaces y luego permitir explícitamente el tráfico requerido
    - C) Denegar únicamente el tráfico de fuentes externas
    - D) Denegar todo el tráfico de egreso, pero permitir todo el tráfico de ingreso

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aplicar políticas de denegación predeterminada a los Namespaces y luego permitir explícitamente el tráfico requerido**

**Explicación:**
La práctica recomendada de seguridad es aplicar una política de denegación predeterminada que bloquee todo el tráfico de ingreso (y opcionalmente de egreso) hacia los Pods en un Namespace, y luego crear políticas específicas para permitir únicamente los flujos de tráfico requeridos. Esto implementa el principio de mínimo privilegio para el acceso a la red.

</details>

11. ¿Cómo se configura Calico para exportar registros de flujos para la visibilidad de red?
   - A) Habilitar en las flags de kube-apiserver
   - B) Configurar FlowLogsFileReporter o FlowLogsNetworkReporter en FelixConfiguration
   - C) Los registros de flujos siempre están habilitados de forma predeterminada
   - D) Instalar un Operator independiente de registros de flujos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurar FlowLogsFileReporter o FlowLogsNetworkReporter en FelixConfiguration**

**Explicación:**
Los registros de flujos se configuran mediante FelixConfiguration habilitando FlowLogsFileReporter (escribe en archivos) o FlowLogsNetworkReporter (envía a un recopilador). Configure parámetros como el intervalo de registro, el nivel de agregación y qué flujos capturar. Nota: las funciones completas de registros de flujos requieren Calico Enterprise.

</details>

12. ¿Qué variables de entorno deben establecerse para que calicoctl se conecte al datastore?
    - A) CALICO_HOST y CALICO_PORT
    - B) DATASTORE_TYPE y KUBECONFIG (o ETCD_ENDPOINTS para el datastore etcd)
    - C) CALICO_API_SERVER y CALICO_TOKEN
    - D) CNI_PATH y CNI_CONFIG

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) DATASTORE_TYPE y KUBECONFIG (o ETCD_ENDPOINTS para el datastore etcd)**

**Explicación:**
Para que calicoctl se conecte al datastore, establezca `DATASTORE_TYPE=kubernetes` y asegúrese de que KUBECONFIG apunte a un archivo kubeconfig válido. Para el datastore etcd, establezca `DATASTORE_TYPE=etcdv3` junto con `ETCD_ENDPOINTS` y, opcionalmente, variables relacionadas con TLS para conexiones seguras.

</details>

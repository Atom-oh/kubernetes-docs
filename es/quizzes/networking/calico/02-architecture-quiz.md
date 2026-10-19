# Cuestionario sobre la arquitectura de Calico

> **Documento relacionado**: [Arquitectura de Calico](../../../networking/calico/02-architecture.md)
> **Última actualización**: 12 de septiembre de 2026

## Cuestionario

1. ¿Cuál es la función principal de Felix en la arquitectura de Calico?
   - A) Distribuir rutas BGP
   - B) Aplicar políticas y administrar interfaces en cada nodo
   - C) Agregar conexiones al almacén de datos
   - D) Procesar plantillas de configuración

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aplicar políticas y administrar interfaces en cada nodo**

**Explicación:**
Felix reconcilia la configuración de las interfaces de los endpoints, las rutas aplicables y las políticas del kernel. En la red Linux completa de Calico, el runtime de contenedores invoca la cadena CNI/IPAM para asignar direcciones y crear las interfaces veth de los Pods. Felix no recibe directamente la llamada CNI ADD ni administra la asignación de IP de los Pods.

</details>

2. ¿Qué significa BIRD y cuál es su función en Calico?
   - A) Basic Internet Routing Daemon: administra la resolución DNS
   - B) BIRD Internet Routing Daemon: administra el enrutamiento BGP
   - C) Binary Internet Relay Daemon: reenvía paquetes
   - D) Bridge Internet Routing Device: administra los túneles VXLAN

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) BIRD Internet Routing Daemon: administra el enrutamiento BGP**

**Explicación:**
BIRD administra las sesiones BGP y el intercambio de rutas cuando se habilita ese backend. Puede funcionar como reflector de rutas y sincronizarlas con el kernel mediante su protocolo de kernel. BGP puede coexistir con la encapsulación; habilitar BGP no garantiza por sí solo el reenvío sin encapsulación. Los paquetes de las cargas de trabajo no atraviesan el proceso BIRD.

</details>

3. ¿Cuál es el propósito de confd en la arquitectura de Calico?
   - A) Administrar las configuraciones de los contenedores
   - B) Generar dinámicamente los archivos de configuración de BIRD
   - C) Almacenar las políticas de red
   - D) Balancear el tráfico

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Generar dinámicamente los archivos de configuración de BIRD**

**Explicación:**
confd observa el estado pertinente del almacén de datos y genera la configuración a partir de las plantillas de BIRD instaladas. Comprueba el resultado e invoca el comando de recarga configurado. El archivo generado no es la fuente de configuración persistente; cambie los recursos de la API de BGP en vez de editar el archivo bird.cfg generado.

</details>

4. ¿Qué afirmación sobre el despliegue de Typha es correcta?
   - A) Siempre es necesario, sin importar el tamaño del clúster
   - B) Las instalaciones del operador pueden desplegar Typha con menos de 50 nodos; use la lógica de escalado de la versión instalada y los requisitos reales de la carga de trabajo
   - C) Solo es necesario al usar el modo eBPF
   - D) Solo es necesario en despliegues multiclúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Las instalaciones del operador pueden desplegar Typha con menos de 50 nodos; use la lógica de escalado de la versión instalada y los requisitos reales de la carga de trabajo**

**Explicación:**
Typha reduce la distribución de actualizaciones directas del almacén de datos hacia Felix. No es obligatorio universalmente solo a partir de 50 nodos ni se requiere en todas las instalaciones que no usan el operador. El operador 1.42.6 también lo escala en clústeres pequeños: cuenta los nodos y comprueba la capacidad de ubicación en nodos Linux.

</details>

5. ¿Qué opciones de almacén de datos admite Calico?
   - A) MySQL y PostgreSQL
   - B) etcd y la API de Kubernetes
   - C) MongoDB y Redis
   - D) Solo un clúster etcd dedicado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) etcd y la API de Kubernetes**

**Explicación:**
Calico ofrece rutas de almacén de datos mediante la API de Kubernetes y etcdv3 directo, con restricciones de instalación y funciones. La ruta de la API de Kubernetes sigue usando el almacenamiento subyacente de Kubernetes, pero no requiere un clúster Calico etcd separado. etcd directo necesita su propio diseño de TLS, credenciales, disponibilidad y copias de seguridad; el número de nodos por sí solo no es motivo para cambiar.

</details>

6. ¿Qué controladores selecciona el operador 1.42.6 para su despliegue estándar de código abierto de kube-controllers?
   - A) Solo el controlador de políticas
   - B) node y loadbalancer
   - C) Solo los controladores node y de políticas
   - D) Solo el controlador WorkloadEndpoint

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) node y loadbalancer**

**Explicación:**
El renderizador fijado del operador inicia node y loadbalancer en su despliegue estándar de código abierto. También existen controladores de políticas, espacios de nombres, cuentas de servicio y WorkloadEndpoint para las rutas pertinentes del almacén de datos y la configuración, pero no necesariamente se habilitan todos. Los perfiles de ServiceAccount no conceden permisos RBAC de Kubernetes.

</details>

7. Para 500 nodos contabilizados, ¿cuántas réplicas deseadas de Typha devuelve la función de escalado del operador 1.42.6?
   - A) Una réplica por cada 50 nodos
   - B) 4 réplicas, según floor(500 / 200) + 2
   - C) Un número fijo de 5 réplicas
   - D) Una réplica por cada 100 nodos, con un mínimo de 1

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 4 réplicas, según floor(500 / 200) + 2**

**Explicación:**
Para más de cuatro nodos contabilizados, esta versión calcula max(3, floor(N / 200) + 2), por lo que 500 da como resultado 4. Con uno o dos nodos devuelve 1; con tres o cuatro, 2. Para 1.000 nodos devuelve 7. El escalador excluye los nodos no programables y los nodos virtuales de AKS, y comprueba la disponibilidad de nodos Linux; el resultado no garantiza un nivel de rendimiento.

</details>

8. ¿Qué agente de Calico reconcilia el estado local de las rutas de las cargas de trabajo y las políticas del kernel?
   - A) BIRD
   - B) confd
   - C) Felix
   - D) Typha

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Felix**

**Explicación:**
Felix reconcilia localmente las rutas y políticas de las cargas de trabajo. Esto no significa que sea el único componente que modifica rutas: CNI crea la interfaz y las rutas iniciales, y el protocolo de kernel de BIRD puede instalar las rutas aprendidas por BGP. confd genera la configuración de BIRD; Typha distribuye el estado en caché.

</details>

9. ¿Qué puerto usa Typha para comunicarse con las instancias de Felix?
   - A) 443
   - B) 5473
   - C) 8080
   - D) 9090

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 5473**

**Explicación:**
TCP 5473 es el puerto de sincronización predeterminado donde Typha escucha a los clientes, como Felix. Es distinto de los puertos de métricas y estado de salud, y no actúa como proxy del tráfico de las aplicaciones. El operador también configura la confianza TLS y la identidad del cliente.

</details>

10. ¿Qué ajuste de FelixConfiguration habilita el modo eBPF?
    - A) ebpfEnabled: true
    - B) bpfEnabled: true
    - C) dataplaneMode: ebpf
    - D) useEbpf: true

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) bpfEnabled: true**

**Explicación:**
`bpfEnabled` es un campo válido de bajo nivel de FelixConfiguration. En una instalación administrada por el operador, use el ajuste compatible `linuxDataplane` de Installation y coordine el cambio con kube-proxy y la accesibilidad de la API. Cambiar un booleano no constituye una migración completa y validada ni garantiza que todas las funciones de eBPF estén disponibles.

</details>

11. ¿Qué les ocurre a las instancias de Felix cuando no se despliega Typha en un clúster grande?
    - A) Las instancias de Felix no se inician
    - B) Cada instancia de Felix se conecta directamente al almacén de datos, lo que puede sobrecargar el servidor de la API
    - C) No se aplican las políticas de red
    - D) Falla el emparejamiento BGP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cada instancia de Felix se conecta directamente al almacén de datos, lo que puede sobrecargar el servidor de la API**

**Explicación:**
Las observaciones directas pueden aumentar la carga del almacén de datos y de la API a medida que crecen el número de nodos y el volumen de actualizaciones. Es un problema de capacidad, no una garantía de que las políticas o BGP dejen de funcionar sin Typha. Incluso con Typha, otros componentes siguen accediendo a la API de Kubernetes.

</details>

12. ¿Cuál es el puerto de estado de salud predeterminado de Felix?
    - A) 8080
    - B) 9091
    - C) 9099
    - D) 10250

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) 9099**

**Explicación:**
El puerto de estado de salud predeterminado de Felix es 9099 cuando está habilitado el servidor de estado. De forma predeterminada, se enlaza a localhost. La configuración de sondas y red debe coincidir con el despliegue real; una solicitud a localhost desde el portátil de un administrador no inspecciona un nodo. El puerto de métricas habitual es 9091.

</details>

---

[Material de aprendizaje](../../../networking/calico/02-architecture.md) | [Cuestionario anterior](01-introduction-quiz.md) | [Cuestionario siguiente](03-networking-modes-quiz.md)

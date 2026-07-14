# Cuestionario de arquitectura de Calico

> **Documento relacionado**: [Arquitectura de Calico](../../../networking/calico/02-architecture.md)
> **Última actualización**: February 22, 2026

## Cuestionario

1. ¿Cuál es la función principal de Felix en la arquitectura de Calico?
   - A) Distribución de rutas BGP
   - B) Aplicación de políticas y gestión de interfaces en cada node
   - C) Agregación de conexiones al datastore
   - D) Procesamiento de plantillas de configuración

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aplicación de políticas y gestión de interfaces en cada node**

**Explicación:**
Felix es el agente central que se ejecuta en cada node de un clúster de Calico. Sus responsabilidades principales incluyen la gestión de interfaces (creación de pares veth de Pod), la programación de tablas de enrutamiento, la gestión de reglas de iptables/eBPF y la aplicación de políticas de red. Felix garantiza que el dataplane esté configurado correctamente para implementar las políticas de red deseadas.

</details>

2. ¿Qué significa BIRD y cuál es su función en Calico?
   - A) Basic Internet Routing Daemon - gestiona la resolución de DNS
   - B) BIRD Internet Routing Daemon - gestiona el enrutamiento BGP
   - C) Binary Internet Relay Daemon - gestiona el reenvío de paquetes
   - D) Bridge Internet Routing Device - gestiona la tunelización VXLAN

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) BIRD Internet Routing Daemon - gestiona el enrutamiento BGP**

**Explicación:**
BIRD (BIRD Internet Routing Daemon) es el agente BGP de Calico responsable de gestionar las conexiones entre pares BGP, intercambiar y propagar rutas entre nodes y, opcionalmente, funcionar como un Route Reflector. BIRD habilita las capacidades BGP nativas de Calico para el enrutamiento directo sin encapsulación.

</details>

3. ¿Cuál es el propósito de confd en la arquitectura de Calico?
   - A) Gestionar configuraciones de contenedores
   - B) Generar dinámicamente archivos de configuración de BIRD
   - C) Almacenar políticas de red
   - D) Equilibrar el tráfico de carga

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Generar dinámicamente archivos de configuración de BIRD**

**Explicación:**
confd se encarga de generar dinámicamente archivos de configuración de BIRD a partir de plantillas. Supervisa el datastore de Calico en busca de cambios en la configuración BGP, la información de nodes y los ajustes de pares, y después actualiza automáticamente la configuración de BIRD para reflejar esos cambios sin intervención manual.

</details>

4. ¿Cuándo se debe desplegar Typha en un clúster de Calico?
   - A) Siempre, independientemente del tamaño del clúster
   - B) Solo para clústeres con más de 50 nodes
   - C) Solo cuando se usa el modo eBPF
   - D) Solo para despliegues multi-clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Solo para clústeres con más de 50 nodes**

**Explicación:**
Typha se recomienda para clústeres con 50 nodes o más. Sin Typha, cada instancia de Felix se conecta directamente al datastore, lo que puede sobrecargar el API server en clústeres grandes. Typha agrega las conexiones al datastore y proporciona datos en caché a las instancias de Felix, lo que reduce significativamente la carga del API server.

</details>

5. ¿Qué opciones de datastore admite Calico?
   - A) MySQL y PostgreSQL
   - B) etcd y Kubernetes API
   - C) MongoDB y Redis
   - D) Solo etcd dedicado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) etcd y Kubernetes API**

**Explicación:**
Calico admite dos opciones de datastore: un clúster etcd dedicado o Kubernetes API (mediante CRDs). El datastore de Kubernetes API se recomienda para la mayoría de los despliegues, ya que simplifica las operaciones al usar la infraestructura de Kubernetes existente. El datastore de etcd se usa para despliegues que no son de Kubernetes o cuando se requieren funcionalidades específicas de etcd.

</details>

6. ¿Qué controllers se incluyen en kube-controllers?
   - A) Solo Policy Controller
   - B) Policy, Namespace, ServiceAccount, WorkloadEndpoint y Node Controllers
   - C) Solo Node y Policy Controllers
   - D) Solo WorkloadEndpoint Controller

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Policy, Namespace, ServiceAccount, WorkloadEndpoint y Node Controllers**

**Explicación:**
kube-controllers incluye varios controllers que se sincronizan entre Kubernetes y el datastore de Calico: Policy Controller (sincronización de NetworkPolicy), Namespace Controller (gestión de perfiles de namespace), ServiceAccount Controller (sincronización de service accounts), WorkloadEndpoint Controller (limpieza de endpoints) y Node Controller (sincronización de información de nodes).

</details>

7. ¿Cuál es la fórmula recomendada para calcular las réplicas de Typha en clústeres grandes?
   - A) 1 réplica por cada 50 nodes
   - B) Recuento de nodes dividido entre 200, mínimo 3
   - C) Fijo en 5 réplicas
   - D) 1 réplica por cada 100 nodes, mínimo 1

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Recuento de nodes dividido entre 200, mínimo 3**

**Explicación:**
La fórmula recomendada para las réplicas de Typha es: recuento de nodes / 200, con un mínimo de 3 réplicas para alta disponibilidad. Por ejemplo, un clúster de 500 nodes necesitaría al menos 3 réplicas (500/200 = 2.5, redondeado hacia arriba al mínimo de 3), mientras que un clúster de 1000 nodes necesitaría 5 réplicas.

</details>

8. En el flujo de paquetes de Calico, ¿qué componente se encarga de programar las tablas de enrutamiento en el node?
   - A) BIRD
   - B) confd
   - C) Felix
   - D) Typha

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Felix**

**Explicación:**
Felix se encarga de programar las tablas de enrutamiento en cada node. Mientras que BIRD gestiona el intercambio de rutas BGP entre nodes, Felix toma la información de rutas y la programa en las tablas de enrutamiento del kernel de Linux. Felix también gestiona las reglas de iptables/eBPF para la aplicación de políticas.

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
Typha escucha en el puerto 5473 (calico-typha) las conexiones de las instancias de Felix. Este es el puerto predeterminado configurado en los despliegues de Typha para recibir conexiones de los pods calico-node que se ejecutan en cada node del clúster.

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
Para habilitar el modo eBPF en Calico, se configura `bpfEnabled: true` en el recurso FelixConfiguration. Esto cambia el dataplane de iptables a eBPF, lo que mejora el rendimiento y habilita funcionalidades como Direct Server Return (DSR) y el reemplazo de kube-proxy.

</details>

11. ¿Qué ocurre con las instancias de Felix cuando Typha no se despliega en un clúster grande?
    - A) Las instancias de Felix no se inician
    - B) Cada Felix se conecta directamente al datastore, lo que podría sobrecargar el API server
    - C) Las políticas de red no se aplican
    - D) El emparejamiento BGP falla

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cada Felix se conecta directamente al datastore, lo que podría sobrecargar el API server**

**Explicación:**
Sin Typha, cada instancia de Felix en cada node mantiene su propia conexión con el datastore (Kubernetes API server). En clústeres grandes con cientos de nodes, esto puede sobrecargar el API server con conexiones de watch y transferencias de datos. Typha resuelve este problema agregando conexiones y almacenando datos en caché.

</details>

12. ¿Cuál es el puerto predeterminado para la comprobación de estado de Felix?
    - A) 8080
    - B) 9091
    - C) 9099
    - D) 10250

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) 9099**

**Explicación:**
De forma predeterminada, el endpoint de comprobación de estado de Felix escucha en el puerto 9099 cuando se establece `healthEnabled: true` en FelixConfiguration. Este puerto lo usan las liveness y readiness probes de Kubernetes para verificar que Felix se ejecute correctamente en cada node.

</details>

---

[Volver a los materiales de aprendizaje](../../../networking/calico/02-architecture.md) | [Cuestionario anterior: Introducción](./01-introduction-quiz.md) | [Siguiente cuestionario: Modos de red](./03-networking-modes-quiz.md)

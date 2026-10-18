# Funciones del kernel que hacen posibles los contenedores

> **Versiones compatibles**: Linux 6.1 / 6.12 / 6.18 (Amazon Linux 2023), Kubernetes 1.25+ (cgroup v2)
> **Última actualización**: 16 de octubre de 2026

## Qué cubre este documento

- Qué funciones del kernel se combinan para crear un contenedor y por qué no existe un objeto de kernel llamado «contenedor»
- Qué cambió en la práctica al pasar de cgroup v1 a v2 (en especial, el diagnóstico de OOM)
- Qué función cumplen netfilter y conntrack en las redes de Kubernetes

## Primero: en el kernel no existe el «contenedor»

Este es el punto de partida para entender los contenedores. No existe `struct container` ni una sola llamada al sistema que cree uno.

Un contenedor es **una convención que combina varias funciones independientes del kernel**. Cuando un runtime (containerd, runc) inicia un proceso, aplica todas estas funciones.

| Propósito | Función del kernel |
|---|---|
| **Qué puede ver** (aislamiento) | espacios de nombres |
| **Cuánto puede usar** (límites) | cgroups |
| **Qué puede hacer** (privilegios) | capabilities, seccomp, LSM (AppArmor/SELinux) |
| **Cómo se compone el sistema de archivos** | overlayfs (montaje de unión) |
| **Cómo circula el tráfico** | veth, bridge/ruta, netfilter |

De esta combinación se desprenden dos conclusiones prácticas.

**Primero, el aislamiento no es absoluto.** Algunos espacios de nombres se pueden compartir y otros se aíslan. Un Pod de Kubernetes funciona precisamente así: los contenedores del mismo Pod **comparten** los espacios de nombres de red e IPC, mientras que los de montaje y PID suelen estar **separados**. Por eso, los contenedores de un Pod pueden comunicarse entre sí mediante `localhost` (red compartida), pero no pueden ver los sistemas de archivos de los demás (montajes separados).

**Segundo, el aislamiento que se omite deja una brecha silenciosa.** El kernel no entiende «crear un contenedor», así que, si el runtime no aplica un perfil seccomp, la carga de trabajo se ejecuta sin él. Por eso, la seguridad de los contenedores depende de la configuración del runtime y de las políticas.

## Espacios de nombres: qué puede ver

Un espacio de nombres **separa el «espacio de nombres» de un recurso del kernel**; por eso, el mismo nombre o número puede referirse a cosas distintas en espacios de nombres diferentes.

| Espacio de nombres | Aísla | En un Pod |
|---|---|---|
| **mnt** | Puntos de montaje | Por contenedor |
| **pid** | ID de procesos | Por contenedor (`shareProcessNamespace: true` lo comparte dentro del Pod) |
| **net** | Interfaces, tablas de enrutamiento, reglas de netfilter, sockets y puertos | **Compartido por Pod** |
| **ipc** | IPC de System V y colas de mensajes POSIX | Compartido por Pod |
| **uts** | hostname y domainname | Compartido por Pod |
| **user** | Asignación de UID/GID | No se usa de forma predeterminada (consulta abajo) |
| **cgroup** | Ruta raíz del cgroup | Por contenedor |
| **time** | Hora de arranque y reloj monotónico (5.6+) | No se usa |

### Por qué el espacio de nombres de red marca el límite del Pod

La identidad de red de un Pod se define aquí. Kubernetes crea un espacio de nombres de red por Pod (que mantiene el contenedor pause) y coloca **todos los contenedores de ese Pod en el mismo espacio de nombres de red**.

De ahí se desprende lo siguiente:

- Los contenedores de un Pod comparten **la misma IP y el mismo espacio de puertos** → dos contenedores de un Pod no pueden enlazarse ambos al puerto 8080
- La comunicación mediante `localhost` funciona → es la base del patrón sidecar
- **Las reglas de netfilter también son propias de cada espacio de nombres de red** → por eso, el contenedor de inicialización de una malla sidecar puede instalar reglas de iptables dentro del espacio de nombres de red del Pod, y esas reglas no afectan a todo el nodo (consulta [Datapath del kernel de VPC Lattice](../service-mesh/vpc-lattice/07-kernel-datapath.md))
- Las tablas de enrutamiento también son independientes → `ip route` dentro de un Pod no muestra las rutas del nodo

### Espacios de nombres de usuario: por qué tardaron tanto en ser la opción predeterminada

Un espacio de nombres de usuario asigna los UID/GID del contenedor a un rango distinto en el host. Esto reduce los privilegios de muchas operaciones que escapan del contenedor, pero **no garantiza** el aislamiento frente a una vulnerabilidad del kernel u otra vía de escalada de privilegios.

Sin embargo, durante mucho tiempo no fue la opción predeterminada. El motivo era la **propiedad de los archivos**. Los archivos de un volumen se registran con los UID del host; si el contenedor ve otro UID, los permisos no coinciden. Para resolverlo, hay que traducir los UID al montar el sistema de archivos (montajes con ID asignados, kernel 5.12 o posterior), y los controladores de almacenamiento y CSI también deben admitirlo.

### Estado de la compatibilidad de Kubernetes con los espacios de nombres de usuario

Según la [referencia de feature gates de Kubernetes](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/) y el [anuncio de GA de v1.36](https://kubernetes.io/blog/2026/04/23/kubernetes-v1-36-userns-ga/), las etapas de madurez son las siguientes (diseño: [KEP-127](https://github.com/kubernetes/enhancements/blob/master/keps/sig-node/127-user-namespaces/kep.yaml)):

| Etapa | Versión |
|---|---|
| alpha | v1.25 |
| beta | v1.30 (habilitada de forma predeterminada desde v1.33) |
| **estable (GA)** | **v1.36** |

El feature gate es `UserNamespacesSupport` y se aplica a kubelet y kube-apiserver. **Desde la versión 1.36 es GA, así que `hostUsers: false` funciona sin habilitar un feature gate.**

::: warning Requiere verificación
Estas etapas de madurez corresponden a Kubernetes upstream. **Que EKS ofrezca esa versión y que tu runtime de contenedores y tus controladores CSI admitan montajes con ID asignados son cuestiones distintas.** Antes de adoptarlos, confirma la versión compatible de EKS y la combinación de runtime y almacenamiento.
:::
## cgroups: cuánto puede usar

Los cgroups (grupos de control) **miden y limitan el uso de recursos de un grupo de procesos**. En última instancia, aquí se aplican `requests` y `limits` de Kubernetes.

### Diferencias estructurales entre v1 y v2

| Elemento | cgroup v1 | cgroup v2 |
|---|---|---|
| **Jerarquía** | Un **árbol independiente por controlador** (cpu, memory, blkio…) | **Un único árbol unificado** |
| **Pertenencia de procesos** | Puede estar en distintos grupos según el controlador | Pertenece exactamente a un grupo |
| **Coordinación de memoria y E/S** | Difícil (los árboles separados no pueden coordinarse) | Posible (comparten el árbol) |
| **Información de presión** | Ninguna | **PSI** (`cpu.pressure`, `memory.pressure`, `io.pressure`) |
| **Representación del límite de CPU** | `cpu.cfs_quota_us` / `cpu.cfs_period_us` | `cpu.max` (un archivo: «cuota período») |
| **Representación del límite de memoria** | `memory.limit_in_bytes` | `memory.max`, además de `memory.high` (presión suave) |
| **AMI de EKS AL2023** | - | **Predeterminado** |

El problema práctico de los «árboles independientes por controlador» de v1 era **coordinar la recuperación de memoria con la E/S**. Cuando queda poca memoria y hay que descartar la caché de páginas, esa recuperación genera E/S de disco; en v1, los dos controladores no tenían conocimiento uno del otro. El árbol unificado de v2 gestiona ambos recursos en la misma jerarquía.

### Actualización de octubre de 2026: avanza la obsolescencia de cgroup v1

El blog de Kubernetes resumió el estado de la transición de cgroup v1 a v2 ([The Shift to cgroup v2 in Kubernetes](https://kubernetes.io/blog/2026/10/06/kubernetes-cgroups-v2-shift/), 6 de octubre de 2026). La administración de cgroup v2 es estable desde v1.25 y la compatibilidad con cgroup v1 está en modo de mantenimiento desde v1.31; **a partir de v1.35, `failCgroupV1` del kubelet tiene el valor predeterminado `true`, por lo que, de forma predeterminada, el kubelet ya no se inicia en un nodo con cgroup v1**. Establecer `failCgroupV1: false` en la configuración del kubelet es una excepción temporal; la eliminación completa se sigue en KEP-5573. En los clústeres de kubeadm, la comprobación previa SystemVerification considera cgroup v1 un error si se usa kubelet v1.35 o posterior (y una advertencia en versiones anteriores). Si ejecutas una versión anterior a v1.35, migra todos los nodos Linux a cgroup v2 antes de actualizar.

### El mayor cambio operativo: diagnóstico de OOM

Este es el dato que debes conocer sobre cgroup v2:

> **`memory.current` incluye la caché de páginas.**

Por eso, aunque la memoria que realmente ocupa la aplicación (anon/RSS) esté muy por debajo del límite, leer muchos archivos acumula caché de páginas y puede llevar `memory.current` hasta el límite.

Hay una distinción importante: **la caché de páginas se puede recuperar**. En condiciones normales, el kernel alcanza el límite y descarta caché de páginas para liberar espacio, sin que se produzca un OOM. El problema aparece **cuando la recuperación no puede seguir el ritmo de las asignaciones**. En ese momento actúa el OOM killer.

Implicaciones prácticas:

| Idea equivocada | Lo que ocurre en realidad |
|---|---|
| «Si `memory.current` se acerca al límite, el OOM es inminente» | Puede incluir caché de archivos recuperable; inspecciona el uso de anon, file y kernel, además de la presión, en vez de dar por sentada su composición |
| «Basta con mirar RSS» | Puede producirse un OOM con RSS bajo (si la recuperación no da abasto) |
| «Aumentar el límite lo arregla» | Si la causa es una recuperación lenta, el problema volverá |

**Valores que conviene revisar durante el diagnóstico:**

| Archivo/valor | Significado |
|---|---|
| `memory.current` | Uso actual (incluye la caché de páginas) |
| `memory.stat` → `anon` | Memoria anónima (la que realmente ocupa la aplicación) |
| `memory.stat` → `file` | Caché de páginas |
| `memory.events` → `oom` / `oom_kill` | Eventos OOM / terminaciones por OOM |
| `memory.events` → `high` / `max` | Veces que se alcanzó el límite suave o estricto |
| `memory.pressure` (PSI) | **Fracción del tiempo de espera** causada por presión de memoria |

**PSI resulta especialmente útil** porque informa sobre la **presión (cuánto tiempo se esperó como consecuencia)**, no sobre el uso (cuánto se está usando). Si aumenta `some avg10` en `memory.pressure`, significa que se está dedicando tiempo a recuperar memoria, algo que un gráfico de uso por sí solo no muestra.

### Límites de CPU y throttling: por qué un uso bajo puede seguir siendo lento

Un límite de CPU es un **límite de capacidad de procesamiento**. Un valor `cpu.max` de `20000 100000` significa «hasta 20 ms por cada período de 100 ms».

Esto tiene una consecuencia contraintuitiva. Si la aplicación realiza su trabajo en una ráfaga breve usando varios subprocesos, **agota la cuota al principio del período y queda detenida a la fuerza hasta que termine el período**. El uso promedio parece bajo, de un 20 %, mientras la latencia se dispara.

Con varios subprocesos, el efecto es aún mayor. Si se ejecutan 4 subprocesos en paralelo, una cuota de 20 ms se consume en 5 ms de tiempo real. Los 95 ms restantes se pasan esperando.

**Diagnóstico:** revisa `cpu.stat` → `nr_throttled` (períodos limitados) y `throttled_usec` (tiempo total de throttling). Si `nr_throttled` representa una fracción considerable de `nr_periods`, el límite es la causa.

**Opciones para responder** (consulta [Optimización de recursos](../ops/10-resource-optimization.md) para diseñar requests y limits):

- Aumentar o quitar el límite (a costa de la estabilidad del nodo)
- Ajustar el número de subprocesos de la aplicación al límite (JVM `-XX:ActiveProcessorCount`, Go `GOMAXPROCS`, etc.); **una discrepancia entre la cantidad de CPU que percibe el contenedor y su cuota real suele ser la causa principal**
- Comprobar el tiempo real de espera con PSI `cpu.pressure`

## Privilegios: qué puede hacer

Aunque ya se hayan aplicado el aislamiento (espacios de nombres) y los límites (cgroups), restringir las **acciones** que puede realizar un proceso es una capa aparte.

| Función | Qué hace | En Kubernetes |
|---|---|---|
| **capabilities** | Conceden o retiran privilegios de root en unidades granulares (`CAP_NET_ADMIN`, `CAP_SYS_ADMIN`, …) | `securityContext.capabilities.add/drop` |
| **seccomp** | Restringe el conjunto de **llamadas al sistema** permitidas | `securityContext.seccompProfile` (se recomienda `RuntimeDefault`) |
| **LSM** (AppArmor/SELinux) | Controla el acceso a archivos y a la red mediante políticas | `securityContext.appArmorProfile`, etc. |
| **no_new_privs** | Impide la escalada de privilegios mediante binarios setuid | `allowPrivilegeEscalation: false` |

Estas tres capas responden a preguntas distintas: capabilities pregunta «¿tienes este privilegio?»; seccomp, «¿puedes invocar esta llamada al sistema?»; y LSM, «¿puedes acceder a este objeto?». **Ninguna basta por sí sola; lo habitual es combinarlas.**

Conviene mencionar `CAP_NET_ADMIN`. El contenedor de inicialización de una malla sidecar lo necesita para instalar reglas de iptables. Por eso, al adoptar una malla surge esta pregunta durante la revisión de seguridad: «¿Por qué tiene este Pod NET_ADMIN?»
## netfilter y conntrack: la realidad de las redes de Kubernetes

### netfilter

netfilter es un marco que ofrece **hooks** en puntos definidos de la pila de red del kernel. `iptables`, `nftables` e `ipvs` son herramientas de espacio de usuario que utilizan esos hooks, o implementaciones construidas sobre ellos.

Principales puntos de conexión:

| Hook | Cuándo se ejecuta |
|---|---|
| `PREROUTING` | Al llegar un paquete, **antes** de la decisión de enrutamiento (punto de DNAT) |
| `INPUT` | Para paquetes destinados a procesos locales |
| `FORWARD` | Para paquetes que atraviesan el sistema |
| `OUTPUT` | Para paquetes que salen de forma local |
| `POSTROUTING` | **Después** del enrutamiento, justo antes de salir (punto de SNAT/MASQUERADE) |

En Kubernetes, estos hooks se usan para lo siguiente:

- **Traducción de ClusterIP del Service a la IP del Pod**: DNAT en `PREROUTING`/`OUTPUT`
- **Traducción de origen del tráfico del Pod hacia el exterior**: MASQUERADE en `POSTROUTING`
- **NetworkPolicy**: CNI inserta reglas en `FORWARD` y otros puntos (plano de datos de iptables de Calico)
- **Interceptación del tráfico de una malla sidecar**: REDIRECT en `OUTPUT`/`PREROUTING` dentro del espacio de nombres de red del Pod

### Modos de kube-proxy: iptables, IPVS y nftables

La implementación de Service tiene tres variantes, y **el panorama cambió en 2025–2026**.

| Modo | Evaluación de reglas | Estado |
|---|---|---|
| **iptables** | El costo de buscar en las cadenas depende de la organización de las reglas; la versión actual de kube-proxy optimiza las actualizaciones | Opción predeterminada si no se cambia explícitamente; verifica qué implementación está instalada |
| **IPVS** | Balanceador de carga L4 dentro del kernel, basado en hash O(1) | **Obsoleto en Kubernetes 1.35 (diciembre de 2025)**; se prevé deshabilitarlo de forma predeterminada en 1.40 y eliminarlo en 1.43 |
| **nftables** | Búsqueda O(1) y **actualizaciones incrementales de reglas** | **GA en Kubernetes 1.33** (alpha 1.29 → beta 1.31). Requiere **kernel 5.13 o posterior** en los nodos de trabajo |

Cómo interpretar esta información:

- **En clústeres grandes, el cuello de botella del modo iptables es la cantidad de reglas y el costo de actualizarlas.** Cuantos más Services y Endpoints, más tarda la sincronización de kube-proxy; mientras tanto, las reglas no están actualizadas.
- **Si usas IPVS, necesitas un plan de migración.** El proyecto upstream prevé deshabilitarlo de forma predeterminada en 1.40 y eliminarlo en 1.43; al planificar, confirma el calendario vigente de [KEP-5495](https://github.com/kubernetes/enhancements/blob/master/keps/sig-network/5495-deprecate-ipvs-mode-in-kube-proxy/README.md). Se recomienda migrar al modo nftables.
- Los nodos AL2023 ejecutan kernel 6.x, así que cumplen el requisito de versión del kernel para el modo nftables.
- Aunque nftables ya sea GA, **iptables sigue siendo la opción predeterminada**; tienes que cambiarla explícitamente.

### conntrack: la causa de incidentes más frecuente

Para que netfilter realice NAT, debe **recordar las conexiones**. Si reescribes la dirección a la salida, debes deshacer esa traducción al volver. La tabla del kernel que conserva esa información es `nf_conntrack`.

En los modos de netfilter de kube-proxy, el NAT de Service depende del seguimiento de conexiones. Sin embargo, **también puede haber seguimiento del tráfico que no usa NAT**, y los Services headless, los endpoints externos y las implementaciones eBPF siguen rutas distintas. No des por hecho que todos los Services de Kubernetes usan necesariamente una misma ruta DNAT.

**El aspecto crucial es lo que ocurre al agotarse la tabla.** No hay un error evidente. Las conexiones nuevas **se descartan silenciosamente**, y la aplicación ve tiempos de espera o rechazos de conexión. Desde la aplicación no hay forma de saber la causa.

| Punto de observación | Significado |
|---|---|
| `/proc/sys/net/netfilter/nf_conntrack_count` | Entradas actuales |
| `/proc/sys/net/netfilter/nf_conntrack_max` | Límite máximo |
| `conntrack -S` → `insert_failed` | Fallos de inserción; compáralos con count/max, los descartes y los registros del kernel en vez de tomarlos como prueba suficiente de agotamiento |
| `conntrack -S` → `drop` | Paquetes descartados |
| `dmesg` → `nf_conntrack: table full, dropping packet` | Advertencia del kernel |

**Una precaución específica de EKS.** kube-proxy también administra los valores de conntrack y **EKS incluye de forma predeterminada un ConfigMap `kube-proxy-config` que tiene prioridad sobre los argumentos de la línea de comandos**. Por eso, puedes aumentar el sysctl en el nodo y kube-proxy puede volver a cambiarlo. Lo correcto es ajustar `conntrack.maxPerCore`/`conntrack.min` en el ConfigMap y reiniciar el DaemonSet de kube-proxy.

Aumentar `nf_conntrack_max` **eleva el uso de memoria del nodo**. Cada entrada consume memoria, así que no se puede aumentarlo sin límite: el valor debe corresponder al tamaño del nodo. Encontrarás valores concretos en [Ajuste del kernel de los nodos de EKS](./03-eks-node-tuning.md).

::: warning Verifica la configuración activa de kube-proxy
Un informe histórico de Bottlerocket muestra que kube-proxy sobrescribía los valores de sysctl del nodo. Cuando se usa `--config`, edita la **configuración activa** (`conntrack.maxPerCore` y `conntrack.min`), no los indicadores CLI que esta anula. Si estableces ambos valores en 0, delegas intencionadamente el límite al sysctl del nodo; confirma el comportamiento con la versión del complemento implementada y comprueba el valor resultante en el nodo. Respeta el presupuesto de memoria del nodo.
:::

El problema histórico no demuestra que todas las versiones actuales de Bottlerocket se comporten igual. Después del despliegue, consulta la configuración efectiva y el valor real de sysctl.

### Cómo reducir la presión sobre conntrack

Hay varias maneras de reducir la carga.

- Los Services headless evitan el DNAT de la VIP de Service, pero **no eluden conntrack automáticamente**.
- Cilium puede sustituir funciones de kube-proxy/netfilter por mapas eBPF; mide la presión sobre sus propios mapas y su propio seguimiento, además de cualquier ruta netfilter que siga activa.
- Reutilizar conexiones reduce la rotación de conexiones; verifica tanto la capacidad de las conexiones establecidas como el comportamiento de los tiempos de espera.

## overlayfs: cómo se componen las capas de imagen

Las capas de las imágenes de contenedor aparecen como un único sistema de archivos mediante un **montaje de unión**, concretamente `overlayfs`.

Tiene tres partes:

| Capa | Función |
|---|---|
| **lowerdir** | Solo lectura: capas de imagen (se pueden apilar varias) |
| **upperdir** | Escritura: cambios del contenedor |
| **merged** | Vista combinada que ve el contenedor |

La propiedad importante en la operación es **copy-up**. Al modificar un archivo de lowerdir, primero se copia **el archivo completo a upperdir** y luego se modifica. Por tanto:

- **Incluso un cambio pequeño en un archivo grande tiene el costo de copiarlo completo.** Cambiar un byte de un archivo de 1 GB copia 1 GB
- Las escrituras intensivas dentro de un contenedor consumen el disco del nodo (almacenamiento efímero)
- **Las rutas con muchas escrituras deben estar en volúmenes** (`emptyDir`, PVC, etc.)

## Resumen

- En el kernel no existe el «contenedor». Es una **combinación** de espacios de nombres (aislamiento) + cgroups (límites) + capabilities/seccomp/LSM (privilegios) + overlayfs (sistema de archivos) + netfilter (red). Por eso el aislamiento es selectivo y las omisiones dejan brechas silenciosas.
- **El espacio de nombres net marca el límite del Pod.** De ahí se derivan la IP y el espacio de puertos compartidos, la comunicación mediante `localhost` y las reglas de netfilter propias del Pod.
- En cgroup v2, **`memory.current` incluye la caché de páginas**. Para diagnosticar OOM, consulta conjuntamente `memory.stat` → `anon`, `memory.events` y **PSI (`memory.pressure`)**.
- El límite de CPU es un **límite de capacidad de procesamiento**, así que el throttling puede elevar la latencia incluso con un uso bajo. `cpu.stat` → `nr_throttled` aporta evidencia.
- Para kube-proxy, **nftables es GA desde 1.33 e IPVS está obsoleto desde 1.35**; upstream prevé deshabilitar IPVS de forma predeterminada en 1.40 y eliminarlo en 1.43. iptables sigue siendo la opción predeterminada.
- El agotamiento de conntrack puede descartar conexiones nuevas. Para diagnosticarlo, revisa count/max, los contadores de descartes e inserciones y los registros; antes de cambiar límites, comprueba la configuración efectiva de kube-proxy.

Siguiente: [Pila de red del kernel](./02-network-stack.md) recorre la ruta completa que sigue un paquete.

## Referencias

- [Control Group v2: documentación del kernel de Linux](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- [PSI - Pressure Stall Information](https://docs.kernel.org/accounting/psi.html)
- [namespaces(7): manual de Linux](https://man7.org/linux/man-pages/man7/namespaces.7.html)
- [KEP-127: compatibilidad con espacios de nombres de usuario](https://github.com/kubernetes/enhancements/blob/master/keps/sig-node/127-user-namespaces/README.md)
- [bottlerocket-os/bottlerocket#4221: no se aplica el límite de conntrack](https://github.com/bottlerocket-os/bottlerocket/issues/4221)
- [Modo nftables de kube-proxy (blog de Kubernetes)](https://kubernetes.io/blog/2025/02/28/nftables-kube-proxy/)
- [KEP-5495: obsolescencia del modo IPVS en kube-proxy](https://github.com/kubernetes/enhancements/blob/master/keps/sig-network/5495-deprecate-ipvs-mode-in-kube-proxy/README.md)
- [Ejecución de kube-proxy en modo nftables: prácticas recomendadas de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/nftables.html)
- [Aumentar el límite de nf_conntrack_max en nodos de EKS](https://repost.aws/knowledge-center/eks-increase-nf-conntrack-max-limit)
- [AMI de Amazon Linux 2023 optimizadas para Amazon EKS](https://aws.amazon.com/blogs/containers/amazon-eks-optimized-amazon-linux-2023-amis-now-available/)

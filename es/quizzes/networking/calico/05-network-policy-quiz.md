# Cuestionario sobre políticas de red

> **Documento relacionado**: [Política de red](../../../networking/calico/05-network-policy.md)
> **Última actualización**: 12 de septiembre de 2026

## Cuestionario

1. ¿Qué limitación clave de NetworkPolicy estándar de Kubernetes aborda Calico?
   - A) No permite especificar números de puerto
   - B) No admite reglas de salida (egress)
   - C) No incluye reglas Deny, políticas globales ni selectores flexibles
   - D) No permite seleccionar Pods mediante etiquetas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) No incluye reglas Deny, políticas globales ni selectores flexibles**

**Explicación:**
El objeto NetworkPolicy estándar de Kubernetes define reglas Allow aditivas de capa 3 y 4, con alcance de espacio de nombres. Ya admite puertos con nombre y rangos numéricos mediante `endPort` cuando el complemento de red los implementa. Calico añade acciones explícitas, políticas globales, niveles (tiers) y selectores de expresiones. En la edición Open Source, las políticas HTTP requieren la integración con Istio/Dikastes; los dominios DNS son una extensión comercial.

</details>

2. ¿Qué sintaxis utilizan los selectores de NetworkPolicy de Calico?
   - A) Pares de clave y valor YAML, como en Kubernetes estándar
   - B) Expresiones como `app == 'frontend'`
   - C) Expresiones regulares
   - D) Expresiones JSONPath

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Expresiones como `app == 'frontend'`**

**Explicación:**
Calico usa una sintaxis de selectores basada en expresiones que admite operadores como `==`, `!=`, `in`, `not in`, `has()` y `!has()`. Por ejemplo: `app == 'frontend'`, `environment in {'prod', 'staging'}` y `has(role)`. Esto ofrece más flexibilidad que los selectores de etiquetas estándar de Kubernetes.

</details>

3. ¿Qué acciones válidas pueden usar las reglas de NetworkPolicy de Calico?
   - A) Accept, Reject
   - B) Allow, Deny, Log, Pass
   - C) Permit, Block, Audit
   - D) Enable, Disable, Monitor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Allow, Deny, Log, Pass**

**Explicación:**
Allow y Deny concluyen la decisión de política normal para ese endpoint y esa dirección del tráfico. Log permite que la evaluación continúe, por lo que después todavía puede aplicarse un Deny. Pass omite las políticas restantes del nivel actual y pasa al siguiente nivel aplicable; después del último nivel se consideran los perfiles. La política del otro endpoint también se aplica.

</details>

4. ¿Cuál es la diferencia entre GlobalNetworkPolicy y NetworkPolicy en Calico?
   - A) GlobalNetworkPolicy es más rápida
   - B) NetworkPolicy requiere un espacio de nombres; GlobalNetworkPolicy no está limitada a uno
   - C) GlobalNetworkPolicy solo funciona en modo eBPF
   - D) NetworkPolicy admite más funciones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) NetworkPolicy requiere un espacio de nombres; GlobalNetworkPolicy no está limitada a uno**

**Explicación:**
NetworkPolicy selecciona cargas de trabajo de su propio espacio de nombres. GlobalNetworkPolicy no está asociada a un espacio de nombres y puede seleccionar cargas de trabajo de varios espacios de nombres y HostEndpoints. Eso no significa que seleccione automáticamente todos los endpoints: delimite el alcance de los destinos y mantenga la conectividad del host y del sistema.

</details>

5. ¿Para qué se utiliza un NetworkSet en Calico?
   - A) Para agrupar interfaces de red
   - B) Para definir conjuntos reutilizables de direcciones IP y CIDR
   - C) Para configurar espacios de nombres de red
   - D) Para administrar complementos de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Para definir conjuntos reutilizables de direcciones IP y CIDR**

**Explicación:**
Un NetworkSet agrupa rangos de IP o CIDR etiquetados para poder reutilizarlos. Un NetworkSet con espacio de nombres y un GlobalNetworkSet tienen alcances de selección distintos. Al seleccionar recursos globales desde una política con espacio de nombres, use un `namespaceSelector: global()` independiente; `global(label-expression)` no es sintaxis válida.

</details>

6. ¿Cómo se evalúan los niveles (tiers) en el modelo de políticas de Calico?
   - A) Alfabéticamente por nombre
   - B) Según el campo order; los números menores se evalúan primero
   - C) En orden aleatorio
   - D) Según la fecha de creación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Según el campo order; los números menores se evalúan primero**

**Explicación:**
Primero se evalúan los niveles con menor order y, dentro de cada nivel, las políticas con menor order. Solo se aplican los niveles que contienen una política que selecciona el endpoint y la dirección del tráfico. Si no coincide ninguna regla de un nivel aplicable, se usa su `defaultAction`, que normalmente es Deny. El nivel integrado predeterminado tiene un valor fijo de 1 000 000; no equivale a un valor infinito implícito.

</details>

7. ¿Qué hace la acción Pass en una regla de política de Calico?
   - A) Permite el tráfico inmediatamente
   - B) Descarta el tráfico sin avisar
   - C) Pasa al siguiente nivel para continuar la evaluación
   - D) Registra el tráfico y lo permite

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Pasa al siguiente nivel para continuar la evaluación**

**Explicación:**
Pass omite las demás políticas de su nivel, incluidas las restricciones de seguridad que pudieran evaluarse después. Si se quiere comprobar primero todas las barreras que solo deniegan tráfico y luego delegar la decisión, puede ser más apropiado configurar `defaultAction: Pass` en el nivel que usar una regla Pass incondicional al principio.

</details>

8. ¿En qué campo se especifican los dominios permitidos para el tráfico de salida en Calico Enterprise 3.23?
   - A) En el campo `hosts` de las reglas de entrada
   - B) En el campo `domains` de la especificación de destino
   - C) Las políticas FQDN no son compatibles
   - D) En un CRD DNS NetworkPolicy

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) En el campo `domains` de la especificación de destino**

**Explicación:**
Calico Enterprise admite `destination.domains` en las reglas Allow de salida y aprende los dominios mediante DNS de confianza. Este campo no existe en el CRD de Open Source 3.32; habilitar `policySyncPathPrefix` o un proxy DNS arbitrario no lo añade. Un comodín de prefijo coincide con uno o más componentes del dominio, y una coincidencia basada en IP no autentica el nombre de host HTTPS.

</details>

9. ¿Qué controla el ajuste applyOnForward en una GlobalNetworkPolicy?
   - A) Si la política se aplica al tráfico que el host reenvía o enruta
   - B) Si la política se aplica en orden directo o inverso
   - C) Si se envían las infracciones de políticas a un SIEM
   - D) Si la política se aplica al reenvío de puertos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Si la política se aplica al tráfico que el host reenvía o enruta**

**Explicación:**
Para las políticas de HostEndpoint, `applyOnForward: true` también hace que se aplique al tráfico reenviado. Es obligatorio cuando `doNotTrack` o `preDNAT` es true. Una regla Allow para el host no omite la política aplicable al endpoint de la carga de trabajo.

</details>

10. ¿Para qué sirve doNotTrack en una política de Calico?
    - A) Desactiva el registro de políticas
    - B) Aplica la política antes del seguimiento de conexiones (sin estado)
    - C) Evita que la política aparezca en los registros de auditoría
    - D) Desactiva el seguimiento de endpoints

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aplica la política antes del seguimiento de conexiones (sin estado)**

**Explicación:**
`doNotTrack` es una opción para políticas del host, requiere `applyOnForward: true` y aplica la política antes del seguimiento de conexiones. Una regla Allow sin seguimiento evita que se rastree el tráfico coincidente; se necesitan reglas explícitas tanto para las solicitudes como para las respuestas. No mejora el rendimiento en todos los casos y puede entrar en conflicto con rutas de Service o NAT que dependen de conntrack.

</details>

11. ¿Para qué sirve preDNAT en una política de Calico?
    - A) Aplica la política antes de la resolución DNS
    - B) Aplica la política antes de Destination NAT y permite ver el destino original
    - C) Evita que se ejecute DNAT
    - D) Aplica la política únicamente al tráfico DNS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aplica la política antes de Destination NAT y permite ver el destino original**

**Explicación:**
`preDNAT` evalúa el tráfico de entrada del host antes de DNAT y usa la IP o el puerto de destino originales. Requiere `applyOnForward: true`, no puede incluir reglas egress y no se puede combinar con `doNotTrack`. Si ninguna regla coincide, no se descarta automáticamente el tráfico en esa etapa; después siguen aplicándose las políticas del host y de la carga de trabajo.

</details>

12. ¿Qué política base selecciona ambos sentidos del tráfico para las cargas de trabajo de demo-namespace después de las reglas Allow explícitas anteriores?
    - A) Establecer un indicador para todo el clúster en FelixConfiguration
    - B) Crear una GlobalNetworkPolicy de alcance limitado con `types: [Ingress, Egress]` y reglas vacías
    - C) Eliminar todas las NetworkPolicy existentes
    - D) Configurar la denegación predeterminada en el IPPool

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crear una GlobalNetworkPolicy de alcance limitado con `types: [Ingress, Egress]` y reglas vacías**

**Explicación:**
Seleccione el espacio de nombres o las cargas de trabajo deseadas, establezca explícitamente ambos tipos y deje las listas de reglas vacías. Si se omite order, la política se ordena después de las políticas que sí tienen un valor explícito. La política base no anula las acciones Allow terminales anteriores, y `selector: all()` por sí solo también puede incluir HostEndpoints. No aplique una política general sin limitar su alcance como paso genérico de un tutorial para tráfico del sistema.

</details>

13. ¿Qué controla el campo order de una política de Calico?
    - A) El orden en que se seleccionan los Pods
    - B) La prioridad de evaluación dentro de un nivel (un valor menor va antes)
    - C) El orden de aplicación de las reglas dentro de la política
    - D) El orden de las direcciones IP en los NetworkSets

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La prioridad de evaluación dentro de un nivel (un valor menor va antes)**

**Explicación:**
El campo `order` determina la prioridad de evaluación de las políticas dentro de un nivel. Primero se evalúan las políticas cuyo valor order es menor. Si una política coincide y ejecuta una acción terminal (Allow o Deny), la evaluación se detiene. Así se pueden definir excepciones de prioridad alta antes de las reglas generales.

</details>

14. ¿Qué es un HostEndpoint en Calico?
    - A) Un Pod que se ejecuta en la red del host
    - B) Una representación de una interfaz de red del host para aplicar políticas
    - C) El endpoint del servidor de la API
    - D) Un endpoint de Service en el host

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una representación de una interfaz de red del host para aplicar políticas**

**Explicación:**
HostEndpoint representa una interfaz de un host administrado y permite aplicar políticas a su tráfico. Los endpoints creados manualmente pueden causar un comportamiento de denegación predeterminada; los endpoints automáticos normalmente tienen un perfil de permiso predeterminado, y los puertos de seguridad de failsafe siguen siendo importantes. `Installation.hostPorts` no crea HostEndpoints automáticamente.

</details>

15. ¿Cómo se puede depurar por qué una política de red no funciona como se espera?
    - A) Leyendo únicamente el YAML de la política
    - B) Comprobando las etiquetas del endpoint, todos los niveles aplicables, el backend, los registros y las conexiones reales
    - C) Reiniciando todos los componentes de Calico
    - D) La depuración de políticas de red no es compatible

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Comprobando las etiquetas del endpoint, todos los niveles aplicables, el backend, los registros y las conexiones reales**

**Explicación:**
Enumere las políticas de Kubernetes y Calico, inspeccione explícitamente todos los niveles relevantes, compruebe las etiquetas de los endpoints y pruebe conexiones nuevas que deban permitirse o denegarse. Que Felix esté listo no demuestra que se cumpla un objetivo de latencia. Las acciones Log de iptables escriben en los registros del kernel. El comportamiento de Service o NAT en kube-proxy o en su reemplazo también puede explicar un fallo; una lista de programas tc por sí sola no muestra el rastro de la política efectiva.

</details>

16. ¿Qué estructura de permisos permite modificar el nivel de aplicación de Calico mediante el servidor de API estándar?
    - A) Usar únicamente NetworkPolicy ordinarias con resourceNames: ["application.*"]
    - B) Conceder get en el nivel application y acceso a tier.networkpolicies con application.* y vincularlo al espacio de nombres previsto
    - C) Cualquier Role con verbs: ["*"]
    - D) Crear un espacio de nombres llamado application

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Conceder get en el nivel application y acceso a tier.networkpolicies con application.* y vincularlo al espacio de nombres previsto**

**Explicación:**
Calico comprueba los permisos sobre el pseudorrecurso `tier.networkpolicies`, el nombre sintético `application.*` o el nombre de la política, y el permiso get sobre el nivel. No se trata de un comodín genérico `resourceNames` de Kubernetes. También hay que considerar los demás vínculos aditivos y las limitaciones de lectura de la API nativa v3.

</details>

17. Un cliente se conecta desde el puerto de origen 49152 al puerto 8080 del backend. ¿Qué coincidencia de puerto ingress expresa el puerto de escucha del servidor?
    - A) source.ports: [8080]
    - B) source.ports: [49152] para todos los clientes
    - C) destination.ports: [8080] con protocolo TCP
    - D) Sin protocolo y con un rango de puertos de origen que cubra todos los puertos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) destination.ports: [8080] con protocolo TCP**

**Explicación:**
El servicio escucha en el puerto de destino 8080; los puertos de origen de los clientes varían. Las coincidencias con puertos numéricos requieren un protocolo compatible con puertos. Una coincidencia del puerto de origen corresponde a otros casos, como una regla explícita para respuestas DNS sin seguimiento.

</details>

---

[Volver a los materiales de aprendizaje](../../../networking/calico/05-network-policy.md) | [Cuestionario anterior: Análisis detallado de BGP](./04-bgp-deep-dive-quiz.md)

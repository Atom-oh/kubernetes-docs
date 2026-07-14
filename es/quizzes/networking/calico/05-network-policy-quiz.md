# Cuestionario de Network Policy

> **Documento relacionado**: [Network Policy](../../../networking/calico/05-network-policy.md)
> **Última actualización**: February 22, 2026

## Cuestionario

1. ¿Cuál es una limitación clave de NetworkPolicy estándar de Kubernetes que Calico aborda?
   - A) No se pueden especificar números de puerto
   - B) No admite reglas de egress
   - C) No tiene reglas Deny, políticas globales y tiene opciones de selector limitadas
   - D) No se pueden seleccionar Pods por labels

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) No tiene reglas Deny, políticas globales y tiene opciones de selector limitadas**

**Explicación:**
NetworkPolicy estándar de Kubernetes tiene varias limitaciones: solo admite reglas Allow (sin Deny explícito), no puede crear políticas globales para todo el clúster, tiene opciones de selector limitadas y no admite filtrado L7 (capa de aplicación). Calico amplía NetworkPolicy con acciones explícitas Deny/Allow/Log/Pass, GlobalNetworkPolicy, selectores avanzados y compatibilidad con políticas L7.

</details>

2. ¿Cuál es la sintaxis de los selectores en Calico NetworkPolicy?
   - A) Pares clave-valor de YAML como en Kubernetes estándar
   - B) Sintaxis basada en expresiones como `app == 'frontend'`
   - C) Expresiones regulares
   - D) Expresiones de rutas JSON

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Sintaxis basada en expresiones como `app == 'frontend'`**

**Explicación:**
Calico utiliza una sintaxis de selectores basada en expresiones que admite operadores como `==`, `!=`, `in`, `not in`, `has()` y `!has()`. Por ejemplo: `app == 'frontend'`, `environment in {'prod', 'staging'}`, `has(role)`. Esto proporciona más flexibilidad que los selectores de labels estándar de Kubernetes.

</details>

3. ¿Cuáles son los tipos de acción válidos en las reglas de Calico NetworkPolicy?
   - A) Accept, Reject
   - B) Allow, Deny, Log, Pass
   - C) Permit, Block, Audit
   - D) Enable, Disable, Monitor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Allow, Deny, Log, Pass**

**Explicación:**
Calico NetworkPolicy admite cuatro tipos de acciones: `Allow` (permite el tráfico), `Deny` (descarta el tráfico), `Log` (registra el tráfico y continúa la evaluación) y `Pass` (salta al siguiente tier para su evaluación). Estas acciones proporcionan control detallado sobre el manejo del tráfico.

</details>

4. ¿Cuál es la diferencia entre GlobalNetworkPolicy y NetworkPolicy en Calico?
   - A) GlobalNetworkPolicy es más rápida
   - B) NetworkPolicy requiere un namespace; GlobalNetworkPolicy se aplica a todo el clúster
   - C) GlobalNetworkPolicy solo funciona con el modo eBPF
   - D) NetworkPolicy admite más características

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) NetworkPolicy requiere un namespace; GlobalNetworkPolicy se aplica a todo el clúster**

**Explicación:**
Calico NetworkPolicy tiene ámbito de namespace y se aplica solo a los Pods dentro de ese namespace, de forma similar a Kubernetes NetworkPolicy. GlobalNetworkPolicy tiene alcance para todo el clúster y puede aplicarse a todos los Pods de todos los namespaces, lo que la hace ideal para líneas base de seguridad, requisitos de cumplimiento y reglas para todo el clúster, como las políticas de denegación predeterminada.

</details>

5. ¿Para qué se utiliza un NetworkSet en Calico?
   - A) Agrupar interfaces de red
   - B) Definir conjuntos reutilizables de direcciones IP/CIDRs
   - C) Configurar namespaces de red
   - D) Gestionar plugins de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Definir conjuntos reutilizables de direcciones IP/CIDRs**

**Explicación:**
Un NetworkSet es un recurso de Calico que define un conjunto de direcciones IP o bloques CIDR que pueden referenciarse en políticas de red. Esto permite definir una vez grupos de IP externas (como servidores de bases de datos o partners de confianza) y referenciarlos en varias políticas, lo que facilita y mejora la mantenibilidad de la gestión de políticas.

</details>

6. ¿Cómo se evalúan los Tiers en el modelo de políticas de Calico?
   - A) Alfabéticamente por nombre
   - B) Por el campo order; los números más bajos se evalúan primero
   - C) Aleatoriamente
   - D) Por la marca de tiempo de creación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Por el campo order; los números más bajos se evalúan primero**

**Explicación:**
Los Tiers se evalúan en orden según su campo `order`, y los números más bajos se evalúan primero. Dentro de cada tier, las políticas también se evalúan por su campo order. Esta estructura jerárquica permite a las organizaciones separar las políticas de seguridad (orden bajo), las políticas de plataforma (orden medio) y las políticas de aplicación (orden alto).

</details>

7. ¿Qué hace la acción Pass en una regla de política de Calico?
   - A) Permite el tráfico de inmediato
   - B) Descarta el tráfico silenciosamente
   - C) Salta al siguiente tier para continuar la evaluación
   - D) Registra el tráfico y lo permite

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Salta al siguiente tier para continuar la evaluación**

**Explicación:**
La acción `Pass` hace que la evaluación de políticas omita las políticas restantes en el tier actual y continúe en el siguiente tier. Esto es útil cuando un tier de mayor prioridad (como seguridad) quiere permitir que determinado tráfico sea evaluado más adelante por tiers de menor prioridad (como las políticas de aplicación), en lugar de tomar una decisión final.

</details>

8. ¿Cómo se pueden implementar políticas basadas en FQDN (nombre de dominio) en Calico?
   - A) Mediante el campo `hosts` en las reglas de ingress
   - B) Mediante el campo `domains` en la especificación de destino
   - C) Las políticas FQDN no son compatibles
   - D) Mediante el CRD DNS NetworkPolicy

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Mediante el campo `domains` en la especificación de destino**

**Explicación:**
Calico admite políticas basadas en FQDN mediante el campo `domains` en las reglas de egress. Se pueden especificar patrones de dominio como `"*.amazonaws.com"` o dominios exactos. Calico resuelve estos dominios en direcciones IP y crea las reglas adecuadas. Esta característica está disponible en Calico Enterprise y requiere la configuración de un proxy DNS en Calico de código abierto.

</details>

9. ¿Qué controla la configuración applyOnForward en una GlobalNetworkPolicy?
   - A) Si la política se aplica al tráfico reenviado/enrutado a través del host
   - B) Si la política se aplica en orden directo o inverso
   - C) Si se reenvían las infracciones de políticas a un SIEM
   - D) Si la política se aplica al reenvío de puertos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Si la política se aplica al tráfico reenviado/enrutado a través del host**

**Explicación:**
La configuración `applyOnForward` determina si la política se aplica al tráfico que se reenvía a través del host (no al que tiene como destino u origen el propio host). Esto es importante para las políticas de Host Endpoint y los escenarios donde el nodo actúa como router para el tráfico entre otros endpoints.

</details>

10. ¿Cuál es el propósito de doNotTrack en una política de Calico?
    - A) Desactiva el registro de políticas
    - B) Aplica la política antes del seguimiento de conexiones (sin estado)
    - C) Evita que la política se registre en logs de auditoría
    - D) Desactiva el seguimiento de endpoints

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aplica la política antes del seguimiento de conexiones (sin estado)**

**Explicación:**
La opción `doNotTrack` aplica las reglas de la política antes del seguimiento de conexiones de Linux (conntrack). Esto crea reglas sin estado que no realizan el seguimiento del estado de la conexión, lo cual es útil para escenarios de alto rendimiento o cuando se necesita aplicar reglas al tráfico antes de que entre en el sistema de seguimiento de conexiones. Tanto el tráfico de solicitud como el de respuesta deben permitirse explícitamente.

</details>

11. ¿Cuál es el propósito de preDNAT en una política de Calico?
    - A) Aplica la política antes de la resolución DNS
    - B) Aplica la política antes de Destination NAT, viendo el destino original
    - C) Evita que ocurra DNAT
    - D) Aplica la política solo al tráfico DNS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aplica la política antes de Destination NAT, viendo el destino original**

**Explicación:**
La opción `preDNAT` aplica la política antes de que ocurra Destination NAT, lo que permite que la política vea la IP/puerto de destino original antes de que se traduzca. Esto es útil para las políticas en Host Endpoints donde se desea filtrar el tráfico según el destino original (como las IP externas) antes de que DNAT lo traduzca a una IP de Pod.

</details>

12. ¿Cómo se implementa una política de denegación predeterminada para todos los Pods en Calico?
   - A) Establecer un indicador para todo el clúster en FelixConfiguration
   - B) Crear una GlobalNetworkPolicy con el selector `all()` y sin reglas
   - C) Eliminar todas las NetworkPolicies existentes
   - D) Configurar la denegación predeterminada en el IPPool

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crear una GlobalNetworkPolicy con el selector `all()` y sin reglas**

**Explicación:**
Para implementar una denegación predeterminada, cree una GlobalNetworkPolicy que seleccione todos los Pods (`selector: all()`) con `types: [Ingress, Egress]` pero sin reglas Allow. Esta política debe tener un número de order alto para que se evalúe al final. Todo tráfico que no esté permitido explícitamente por otras políticas será denegado por esta política global.

</details>

13. ¿Qué controla el campo order en una política de Calico?
    - A) El orden en que se seleccionan los Pods
    - B) La prioridad de evaluación dentro de un tier (menor = antes)
    - C) El orden de aplicación de reglas dentro de la política
    - D) El orden de las direcciones IP en los NetworkSets

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La prioridad de evaluación dentro de un tier (menor = antes)**

**Explicación:**
El campo `order` determina la prioridad de evaluación de las políticas dentro de un tier. Las políticas con valores de order más bajos se evalúan primero. Si una política coincide y realiza una acción terminal (Allow o Deny), la evaluación se detiene. Esto permite crear excepciones de alta prioridad antes de las reglas generales.

</details>

14. ¿Qué es un Host Endpoint en Calico?
    - A) Un Pod que se ejecuta en la red del host
    - B) Una representación de la interfaz de red de un host para aplicar políticas
    - C) El endpoint del servidor de la API
    - D) Un endpoint de Service en el host

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una representación de la interfaz de red de un host para aplicar políticas**

**Explicación:**
Un Host Endpoint representa una interfaz de red en un nodo host y permite que las políticas de Calico se apliquen al tráfico que entra o sale del propio host (no solo al tráfico de Pods). Esto permite proteger las interfaces de red del host, controlar qué tráfico puede llegar a los Services del nodo e implementar reglas de firewall a nivel de host.

</details>

15. ¿Cómo se puede depurar por qué una política de red no funciona como se espera?
    - A) Solo leyendo el YAML de la política
    - B) Comprobar los workload endpoints, la evaluación de políticas con calicoctl y los logs de Felix
    - C) Reiniciar todos los componentes de Calico
    - D) La depuración de políticas de red no es compatible

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Comprobar los workload endpoints, la evaluación de políticas con calicoctl y los logs de Felix**

**Explicación:**
Para depurar políticas de red: 1) Use `calicoctl get workloadendpoint -n <namespace>` para verificar que el endpoint exista y tenga los labels correctos, 2) Use `calicoctl get networkpolicy -A` y `globalnetworkpolicy` para enumerar todas las políticas, 3) Revise los logs de Felix en busca de mensajes relacionados con políticas, 4) Verifique que las expresiones de selector coincidan con los labels del endpoint, 5) En el modo eBPF, use `tc filter show` para inspeccionar las reglas aplicadas.

</details>

---

[Volver a los materiales de aprendizaje](../../../networking/calico/05-network-policy.md) | [Cuestionario anterior: Análisis detallado de BGP](./04-bgp-deep-dive-quiz.md)

# Cuestionario sobre Network Policies

> **Última actualización**: 13 de septiembre de 2026

Este cuestionario evalúa su comprensión de las políticas de red de Kubernetes, las políticas de red de Cilium y la microsegmentación.

## Preguntas del cuestionario

### 1. ¿Cuál es el comportamiento predeterminado de NetworkPolicy de Kubernetes?

A. Bloquear todo el tráfico
B. No hay aislamiento mediante NetworkPolicy en una dirección si ninguna política selecciona los Pods
C. Bloquear solo el tráfico entrante
D. Bloquear solo el tráfico saliente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. No hay aislamiento mediante NetworkPolicy en una dirección si ninguna política selecciona los Pods**

**Explicación:**
Evalúe ingress y egress por separado. Si ninguna política selecciona los Pods para una dirección, NetworkPolicy no los aísla en esa dirección; aun así, CNI, rutas, grupos de seguridad (SG), listas de control de acceso a la red (NACL) u otras políticas pueden bloquear la conectividad. Una política que selecciona Pods solo para ingress tampoco los aísla para egress. En el tráfico entre Pods, tanto el egress del origen como el ingress del destino deben permitir la conexión.

</details>

### 2. ¿Qué campo selecciona Pods específicos en una NetworkPolicy?

A. selector
B. podSelector
C. matchLabels
D. targetPods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. podSelector**

**Explicación:**
El campo `spec.podSelector` de NetworkPolicy selecciona los Pods a los que se aplica la política:
```yaml
spec:
  podSelector:
    matchLabels:
      app: web
```

Un `podSelector` vacío (`{}`) selecciona todos los Pods del espacio de nombres.

</details>

### 3. ¿Qué campos definen las reglas entrantes y salientes en NetworkPolicy?

A. inbound/outbound
B. ingress/egress
C. input/output
D. incoming/outgoing

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. ingress/egress**

**Explicación:**
- **ingress**: reglas del tráfico entrante
- **egress**: reglas del tráfico saliente

```yaml
spec:
  ingress:
    - from:
        - podSelector:
            matchLabels:
              role: frontend
  egress:
    - to:
        - podSelector:
            matchLabels:
              role: database
```

</details>

### 4. ¿Dónde se definen las reglas HTTP de L7 en CiliumNetworkPolicy?

A. spec.http
B. spec.ingress[].toPorts[].rules.http
C. spec.rules.http
D. spec.layer7.http

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. spec.ingress[].toPorts[].rules.http**

**Explicación:**
Las reglas HTTP se anidan en `toPorts[].rules.http` dentro de una regla de ingress (o de una regla de egress para filtrar el tráfico saliente). Requieren una ruta compatible a través del proxy L7; el TLS de extremo a extremo no se inspecciona automáticamente, y los encabezados `role` o `API key` proporcionados por el usuario no sirven como autenticación. El modo de encadenamiento de Cilium con AWS VPC CNI tiene limitaciones documentadas para L7.

</details>

<span id="_5-what-is-the-correct-networkpolicy-for-implementing-a-default-deny-policy"></span>

### 5. ¿Qué crea una política base de denegación predeterminada para todo el espacio de nombres en ambas direcciones?

A. Especificar solo Ingress en policyTypes
B. Establecer podSelector como vacío y especificar Ingress y Egress en policyTypes
C. Dejar vacías las reglas de ingress y egress
D. Tanto B como C

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Tanto B como C**

**Explicación:**
Para una política base aplicable a todo el espacio de nombres en **ambas direcciones**, combine B y C. Un selector vacío selecciona todos los Pods del espacio de nombres al que pertenece la política, y los tipos explícitos Ingress/Egress sin reglas de permiso aíslan ambas direcciones. Otras NetworkPolicies de Kubernetes que seleccionen los Pods pueden agregar permisos; esta política base no las anula. También se puede crear una política base solo para ingress si se necesita un alcance más limitado.

</details>

### 6. ¿Cuál es la característica de CiliumClusterwideNetworkPolicy?

A. Requiere metadata.namespace para seleccionar su alcance
B. Un recurso de ámbito de clúster cuyo selector de endpoints controla los destinos
C. Controla solo el tráfico externo
D. Solo admite políticas L7

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Un recurso de ámbito de clúster cuyo selector de endpoints controla los destinos**

**Explicación:**
CiliumClusterwideNetworkPolicy no pertenece a un espacio de nombres. Su selector de endpoints puede abarcar varios espacios de nombres o limitar explícitamente el destino a un espacio de nombres o una aplicación. El ámbito de clúster no significa que se seleccionen todos los endpoints ni que una regla permisiva amplia para `cluster` o `world` aplique una denegación predeterminada.

</details>

### 7. ¿Cómo se permiten todos los Pods de un espacio de nombres específico en NetworkPolicy?

A. Usar solo namespaceSelector
B. Usar solo podSelector
C. Combinar namespaceSelector con podSelector que requiera app=api
D. Usar el campo namespace

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Usar solo namespaceSelector**

**Explicación:**
Use `namespaceSelector.matchLabels.kubernetes.io/metadata.name: monitoring` para seleccionar todos los Pods de ese espacio de nombres. Agregar un `podSelector` **vacío** en el mismo peer también los seleccionaría a todos; la opción C, en cambio, limita la selección a los Pods con `app=api`. Dentro de un mismo peer, los selectores se combinan mediante AND; las entradas de peer separadas se combinan mediante OR. Kubernetes no crea automáticamente una etiqueta personalizada `name`.

</details>

### 8. ¿Qué campo define las reglas de egress basadas en FQDN en CiliumNetworkPolicy?

A. toFQDNs
B. toDomains
C. toHosts
D. toEndpoints

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. toFQDNs**

**Explicación:**
`toFQDNs` utiliza direcciones IP obtenidas mediante DNS junto con las reglas de puerto especificadas. Permita por separado la comunicación con el resolvedor DNS real y las consultas DNS necesarias, incluido TCP además de UDP/53. También importan la caché y el TTL, los sufijos de búsqueda, las direcciones IP de destino compartidas y la autorización TLS o de la aplicación. Una coincidencia de dominio no demuestra la identidad del inquilino del servicio SaaS.

</details>

### 9. ¿Qué tráfico NO se ve afectado por NetworkPolicy?

A. Tráfico entre Pods
B. Tráfico entre contenedores en el mismo Pod (localhost)
C. Tráfico a través de Services
D. Tráfico desde fuentes externas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Tráfico entre contenedores en el mismo Pod (localhost)**

**Explicación:**
Los contenedores de un Pod comparten el espacio de nombres de red; la aplicación normal de Kubernetes NetworkPolicy no controla su comunicación mediante `localhost`. El tratamiento de los nodos y de `hostNetwork`, así como de los protocolos distintos de TCP/UDP/SCTP, tiene límites que dependen de la implementación. No infiera que una política de Pod proporciona aislamiento completo del host.

</details>

### 10. ¿Cuál es la ventaja de la política basada en identidad de Cilium?

A. No se ve afectada por cambios de dirección IP
B. Mayor velocidad de procesamiento
C. Menor uso de memoria
D. No requiere búsqueda DNS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. No se ve afectada por cambios de dirección IP**

**Explicación:**
La política de endpoints basada en etiquetas evita fijar las direcciones IP transitorias de los Pods. El plano de datos asigna los endpoints actuales a identidades de seguridad según los conjuntos de etiquetas pertinentes. Una identidad numérica puede reasignarse y no es un identificador permanente de una aplicación; también deben tenerse en cuenta los cambios de etiquetas, el contexto de espacio de nombres y clúster, y la propagación.

</details>

### 11. ¿Cuál es la política de red correcta para el nivel de backend en una arquitectura de 3 niveles?

A. Permitir todo el tráfico
B. Permitir solo ingress desde el frontend
C. Permitir ingress desde el frontend y egress hacia la base de datos
D. Permitir solo egress hacia la base de datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Permitir ingress desde el frontend y egress hacia la base de datos**

**Explicación:**
C describe la ruta de la aplicación del backend: ingress desde el frontend y egress hacia la base de datos en los puertos revisados. Permita también el egress del frontend y el ingress de la base de datos, además de las rutas de DNS, comprobaciones de estado y supervisión que se necesiten. De lo contrario, una política de denegación predeterminada en el otro extremo aún puede bloquear la conexión. El tráfico de respuesta de una conexión permitida se admite implícitamente.

</details>

### 12. ¿Qué campo excluye direcciones IP específicas al indicar rangos CIDR con ipBlock en NetworkPolicy?

A. exclude
B. except
C. notIn
D. excludeCIDR

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. except**

**Explicación:**
`except` resta bloques CIDR de la regla de permiso de ese `ipBlock`. No es una denegación global: otra política que seleccione los Pods aún puede permitir la dirección excluida. La traducción de direcciones puede cambiar qué IP evalúa un complemento; por eso, verifique la ruta real de CNI y del balanceador de carga o Service.

</details>

---

[Guía de políticas de red](../../security/04-network-policies.md)

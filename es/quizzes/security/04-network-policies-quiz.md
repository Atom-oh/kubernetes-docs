# Cuestionario sobre Network Policies

> **Última actualización**: September 13, 2026

Este cuestionario evalúa tu comprensión de las Kubernetes Network Policies, las Cilium Network Policies y la microsegmentación.

## Preguntas del cuestionario

### 1. ¿Cuál es el comportamiento predeterminado de Kubernetes NetworkPolicy?

A. Bloquear todo el tráfico
B. Sin aislamiento de NetworkPolicy en una dirección que no tenga una política selectora
C. Bloquear solo el tráfico entrante
D. Bloquear solo el tráfico saliente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Sin aislamiento de NetworkPolicy en una dirección que no tenga una política selectora**

**Explicación:**
Evalúa ingress y egress por separado. La ausencia de una política selectora para una dirección significa que NetworkPolicy no la aísla; CNI/route/SG/NACL u otras políticas aún pueden bloquear la conectividad. Una política selectora solo de ingress tampoco aísla egress. Para el tráfico de Pod a Pod, tanto el egress del origen como el ingress del destino deben permitir la conexión.

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

Un podSelector vacío (`{}`) selecciona todos los Pods del namespace.

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
- **ingress**: Reglas de tráfico entrante
- **egress**: Reglas de tráfico saliente

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
Las reglas HTTP están anidadas bajo `toPorts[].rules.http` de una regla de ingress (o bajo una regla de egress para el filtrado saliente). Requieren una ruta de proxy L7 compatible; TLS de extremo a extremo no se inspecciona automáticamente, y los encabezados role/API-key proporcionados por el usuario no constituyen autenticación. El modo de chaining de AWS VPC CNI de Cilium tiene limitaciones documentadas de L7.

</details>

<span id="_5-what-is-the-correct-networkpolicy-for-implementing-a-default-deny-policy"></span>

### 5. ¿Qué crea una línea base de default-deny para todo el namespace en ambas direcciones?

A. Especificar solo Ingress en policyTypes
B. Establecer podSelector como vacío y especificar Ingress y Egress en policyTypes
C. Dejar vacías las reglas de ingress y egress
D. Tanto B como C

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Tanto B como C**

**Explicación:**
Para una línea base para todo el namespace en **ambas direcciones**, combina B y C. Un selector vacío selecciona todos los Pods del namespace propio de la política, y los tipos explícitos Ingress/Egress sin permisos aíslan ambas direcciones. Otras Kubernetes NetworkPolicies selectoras pueden agregar permisos; una línea base no las reemplaza. También es posible una línea base solo de ingress cuando se pretende ese alcance más limitado.

</details>

### 6. ¿Cuál es la característica de CiliumClusterwideNetworkPolicy?

A. Requiere metadata.namespace para seleccionar su alcance
B. Un recurso con alcance de cluster cuyo selector de endpoints controla sus destinos
C. Controla solo el tráfico externo
D. Solo admite políticas L7

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Un recurso con alcance de cluster cuyo selector de endpoints controla sus destinos**

**Explicación:**
CiliumClusterwideNetworkPolicy no tiene namespace. Su selector de endpoints puede cubrir varios namespaces o limitar explícitamente el destino a un namespace/aplicación. El alcance de cluster no significa que se seleccione cada endpoint, ni que las reglas amplias de permiso `cluster`/`world` sean default deny.

</details>

### 7. ¿Cómo permites todos los Pods de un namespace específico en NetworkPolicy?

A. Usar solo namespaceSelector
B. Usar solo podSelector
C. Combinar namespaceSelector con podSelector que requiera app=api
D. Usar el campo namespace

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Usar solo namespaceSelector**

**Explicación:**
Usa `namespaceSelector.matchLabels.kubernetes.io/metadata.name: monitoring` para seleccionar todos los Pods de ese namespace. Agregar un podSelector **vacío** en el mismo peer también los seleccionaría a todos; la opción C, en cambio, restringe los Pods a `app=api`. En un peer, los selectores se combinan mediante AND; las entradas de peer separadas se combinan mediante OR. Una etiqueta `name` personalizada no se crea automáticamente.

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
`toFQDNs` utiliza IPs derivadas de DNS con las reglas de puerto especificadas. Permite la ruta real del resolvedor y las consultas DNS necesarias por separado, incluido TCP además de UDP53. La caché/TTL, los sufijos de búsqueda, las IP de destino compartidas y la autorización TLS/de aplicación siguen siendo relevantes. Una coincidencia de dominio no prueba la identidad del tenant de SaaS.

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
Los contenedores de un Pod comparten el namespace de red; su comunicación mediante localhost queda fuera de la aplicación ordinaria de Kubernetes NetworkPolicy. El manejo de Node/hostNetwork y los protocolos que no son TCP/UDP/SCTP tienen límites específicos de la implementación. No infieras un aislamiento completo del host a partir de una política de Pod.

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
La política de endpoint basada en etiquetas evita codificar de forma fija IPs transitorias de Pods. El datapath asigna los endpoints actuales a identidades de seguridad según sus conjuntos de etiquetas relevantes. Una identidad numérica puede reasignarse y no es un identificador permanente de aplicación; aún se deben considerar los cambios de etiquetas, el contexto de namespace/cluster y la propagación.

</details>

### 11. ¿Cuál es la política de red correcta para el nivel de backend en una arquitectura de 3 niveles?

A. Permitir todo el tráfico
B. Permitir ingress solo desde frontend
C. Permitir ingress desde frontend y permitir egress hacia database
D. Permitir egress solo hacia database

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Permitir ingress desde frontend y permitir egress hacia database**

**Explicación:**
C describe la ruta de aplicación del backend: ingress desde frontend y egress hacia database en los puertos revisados. Permite también el egress de frontend y el ingress de database, además de las rutas DNS/health/monitoring elegidas cuando sea necesario. De lo contrario, una política default-deny en el otro endpoint aún puede bloquear la conexión. El tráfico de retorno de una conexión permitida se permite implícitamente.

</details>

### 12. ¿Qué campo excluye IPs específicas al especificar rangos CIDR con ipBlock en NetworkPolicy?

A. exclude
B. except
C. notIn
D. excludeCIDR

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. except**

**Explicación:**
`except` resta CIDRs de la regla de permiso de ese ipBlock. No es una denegación global: otra política selectora puede permitir la dirección excluida. La traducción de direcciones puede cambiar qué IP evalúa un plugin, por lo que debes verificar la ruta real de CNI y del balanceador de carga/Service.

</details>

---

[Network policies guide](../../security/04-network-policies.md)

# Cuestionario de Network Policies

Este cuestionario evalúa tu comprensión de Kubernetes Network Policies, Cilium Network Policies y la microsegmentación.

## Preguntas del cuestionario

### 1. ¿Cuál es el comportamiento predeterminado de Kubernetes NetworkPolicy?

A. Bloquear todo el tráfico
B. Permitir todo el tráfico
C. Bloquear solo el tráfico entrante
D. Bloquear solo el tráfico saliente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Permitir todo el tráfico**

**Explicación:**
Sin NetworkPolicy, Kubernetes permite todo el tráfico entre Pods de forma predeterminada. Cuando creas una NetworkPolicy, habilita el comportamiento de "denegación predeterminada" para los Pods que coinciden con el podSelector de esa política.

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
El campo `spec.podSelector` en NetworkPolicy selecciona los Pods a los que se aplica la política:
```yaml
spec:
  podSelector:
    matchLabels:
      app: web
```

Un podSelector vacío (`{}`) selecciona todos los Pods en el namespace.

</details>

### 3. ¿Qué campos definen las reglas de tráfico entrante y saliente en NetworkPolicy?

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

### 4. ¿Dónde se definen las reglas HTTP L7 en CiliumNetworkPolicy?

A. spec.http
B. spec.ingress.toPorts.rules.http
C. spec.rules.http
D. spec.layer7.http

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. spec.ingress.toPorts.rules.http**

**Explicación:**
Las reglas L7 en CiliumNetworkPolicy se definen en la sección rules dentro de toPorts:
```yaml
spec:
  ingress:
    - toPorts:
        - ports:
            - port: "80"
          rules:
            http:
              - method: GET
                path: "/api/.*"
```

</details>

### 5. ¿Cuál es la NetworkPolicy correcta para implementar una política de denegación predeterminada?

A. Especificar solo Ingress en policyTypes
B. Establecer podSelector como vacío y especificar Ingress y Egress en policyTypes
C. Dejar vacías las reglas ingress y egress
D. Tanto B como C

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Tanto B como C**

**Explicación:**
Ejemplo de política de denegación predeterminada:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}  # Select all Pods
  policyTypes:
    - Ingress
    - Egress
  # No ingress and egress rules = block all traffic
```

Un podSelector vacío selecciona todos los Pods y, sin reglas, ese tipo de tráfico se bloquea.

</details>

### 6. ¿Cuál es la característica de CiliumClusterwideNetworkPolicy?

A. Se aplica solo a un namespace específico
B. Se aplica en todo el cluster
C. Controla solo el tráfico externo
D. Soporta solo políticas L7

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Se aplica en todo el cluster**

**Explicación:**
CiliumClusterwideNetworkPolicy se aplica en todo el cluster independientemente del namespace. Es útil para implementar reglas de seguridad comunes (por ejemplo, bloquear el acceso al servicio de metadatos desde todos los namespaces).

</details>

### 7. ¿Cómo permites todos los Pods desde un namespace específico en NetworkPolicy?

A. Usar solo namespaceSelector
B. Usar solo podSelector
C. Combinar namespaceSelector con un podSelector vacío
D. Usar el campo namespace

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Usar solo namespaceSelector**

**Explicación:**
```yaml
ingress:
  - from:
      - namespaceSelector:
          matchLabels:
            name: monitoring
```

Usar solo namespaceSelector permite todos los Pods desde ese namespace. Usar podSelector junto con namespaceSelector selecciona solo Pods específicos dentro de ese namespace.

</details>

### 8. ¿Qué campo define reglas de egress basadas en FQDN en CiliumNetworkPolicy?

A. toFQDNs
B. toDomains
C. toHosts
D. toEndpoints

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. toFQDNs**

**Explicación:**
toFQDNs de CiliumNetworkPolicy permite tráfico de egress basado en nombres DNS:
```yaml
spec:
  egress:
    - toFQDNs:
        - matchName: "api.example.com"
        - matchPattern: "*.amazonaws.com"
      toPorts:
        - ports:
            - port: "443"
```

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
NetworkPolicy se aplica al tráfico de red entre Pods. La comunicación localhost entre contenedores en el mismo Pod está fuera del alcance de NetworkPolicy. Además, los Pods que usan hostNetwork del node tienen algunas limitaciones.

</details>

### 10. ¿Cuál es la ventaja de la política basada en Identity de Cilium?

A. No se ve afectada por cambios de dirección IP
B. Mayor velocidad de procesamiento
C. Menor uso de memoria
D. No requiere búsqueda DNS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. No se ve afectada por cambios de dirección IP**

**Explicación:**
Cilium Identity se genera en función de las etiquetas del Pod. Aunque un Pod se reinicie y su IP cambie, mantiene la misma Identity si tiene las mismas etiquetas. Esto supera las limitaciones de las políticas basadas en IP.

</details>

### 11. ¿Cuál es la política de red correcta para el nivel backend en una arquitectura de 3 niveles?

A. Permitir todo el tráfico
B. Permitir ingress solo desde frontend
C. Permitir ingress desde frontend y permitir egress hacia database
D. Permitir egress solo hacia database

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Permitir ingress desde frontend y permitir egress hacia database**

**Explicación:**
En la microsegmentación de 3 niveles, para el backend:
- **Ingress**: Permitir solo desde el nivel frontend
- **Egress**: Permitir solo hacia el nivel database

Esto sigue el principio de privilegio mínimo y controla claramente el flujo de tráfico entre niveles.

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
El campo except de ipBlock puede excluir CIDRs específicos:
```yaml
ingress:
  - from:
      - ipBlock:
          cidr: 10.0.0.0/8
          except:
            - 10.0.1.0/24
            - 10.0.2.0/24
```

Esto permite tráfico desde el rango 10.0.0.0/8 excepto 10.0.1.0/24 y 10.0.2.0/24.

</details>

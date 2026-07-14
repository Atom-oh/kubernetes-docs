# Cuestionario de seguridad de Cilium Service Mesh

Este cuestionario evalúa tu comprensión de mTLS, políticas de red, cifrado, seguridad basada en identidad y redes de confianza cero en Cilium Service Mesh.

## Preguntas del cuestionario

### 1. ¿Qué tecnología utiliza Cilium Service Mesh para implementar mTLS transparente?

A. Istio sidecar
B. Integración de SPIFFE/SPIRE
C. Nginx proxy
D. HAProxy

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Integración de SPIFFE/SPIRE**

**Explicación:**
Cilium Service Mesh se integra con SPIFFE (Secure Production Identity Framework for Everyone) y SPIRE para implementar mTLS transparente. Esto permite la comunicación cifrada entre workloads sin cambios en el código de la aplicación.

</details>

### 2. ¿Cómo se comporta CiliumNetworkPolicy cuando el modo de autenticación se establece en 'required'?

A. Permite todo el tráfico sin autenticación
B. Solo permite el tráfico que supera la autenticación mutua
C. Solo registra advertencias ante errores de autenticación
D. Deshabilita mTLS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Solo permite el tráfico que supera la autenticación mutua**

**Explicación:**
Cuando el modo de autenticación se establece en 'required', solo se permite el tráfico que completa correctamente la autenticación mutua. El tráfico que no supera la autenticación se bloquea. Esto es esencial para implementar un modelo de seguridad de confianza cero.

</details>

### 3. ¿Cuál NO es una ventaja del cifrado WireGuard en Cilium?

A. Alto rendimiento al operar a nivel de kernel
B. Gestión automática de claves
C. Protocolo estándar de IETF
D. Cifrado ChaCha20Poly1305

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Protocolo estándar de IETF**

**Explicación:**
WireGuard no es un protocolo estándar. IPsec es el protocolo estándar de IETF. Sin embargo, WireGuard está integrado en el kernel de Linux 5.6+ y proporciona alto rendimiento, gestión automática de claves y cifrado ChaCha20Poly1305.

</details>

### 4. ¿Cuál es la configuración correcta para restringir rutas y métodos específicos con reglas HTTP L7 en CiliumNetworkPolicy?

A. Especificar la ruta y el método en toEndpoints
B. Especificar el método y la ruta en toPorts.rules.http
C. Especificar directamente en ingress.http
D. Definir reglas en spec.http

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Especificar el método y la ruta en toPorts.rules.http**

**Explicación:**
En CiliumNetworkPolicy, las reglas HTTP L7 se definen bajo rules.http dentro de la sección toPorts. Aquí puedes especificar el método (GET, POST, etc.) y la ruta (con compatibilidad con regex) para un control de acceso detallado.

</details>

### 5. ¿Cuál es la principal ventaja de la seguridad basada en Cilium Identity?

A. No se ve afectada por los cambios de dirección IP
B. Es más segura debido a que se basa en direcciones MAC
C. Es posible la gestión manual de ID
D. Compatibilidad con etiquetado VLAN

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. No se ve afectada por los cambios de dirección IP**

**Explicación:**
Cilium Identity se genera en función de las etiquetas de Pod, por lo que, aunque un Pod se reinicie y su dirección IP cambie, mantiene la misma Identity. Esto supera las limitaciones de las políticas de seguridad basadas en IP.

</details>

### 6. ¿Qué reglas se utilizan para restringir el acceso a dominios externos mediante políticas DNS L7 en Cilium?

A. Combinación de reglas toFQDNs y dns
B. Solo toEndpoints
C. Solo toCIDR
D. Solo toEntities

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Combinación de reglas toFQDNs y dns**

**Explicación:**
La restricción del acceso a dominios externos se configura en dos pasos: 1) Permitir solo consultas de dominios específicos con reglas DNS L7 (toPorts.rules.dns), 2) Permitir conexiones reales a esos dominios con toFQDNs. Esta combinación proporciona un control detallado sobre el acceso externo de los workloads.

</details>

### 7. ¿Qué tráfico normalmente debe permitirse al implementar una política de denegación predeterminada con CiliumClusterwideNetworkPolicy?

A. Todo el tráfico externo
B. Consultas DNS y tráfico de red del host
C. Todo el tráfico de internet
D. Solo rangos de IP específicos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Consultas DNS y tráfico de red del host**

**Explicación:**
Al implementar una política de denegación predeterminada, como mínimo debes permitir consultas DNS a kube-dns (puerto 53/UDP) y tráfico de red del host (reserved:host) para que el clúster funcione correctamente. Sin ellos, el descubrimiento de servicios y la comunicación entre nodos serían imposibles.

</details>

### 8. ¿Cuál es la función de la atestación de workloads en SPIRE?

A. Emisión de certificados
B. Verificación de la identidad del workload
C. Aplicación de políticas de red
D. Cifrado de tráfico

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Verificación de la identidad del workload**

**Explicación:**
La atestación de workloads es el proceso mediante el cual el SPIRE Agent verifica la identidad de un workload. En entornos de Kubernetes, valida la cuenta de servicio, el namespace, las etiquetas, etc. del Pod para emitir el SVID (SPIFFE Verifiable Identity Document) adecuado a ese workload.

</details>

### 9. ¿Cómo se comporta Cilium al probar políticas de red en modo de auditoría?

A. Bloquea todo el tráfico
B. Registra las infracciones de las políticas, pero permite el tráfico
C. Deshabilita por completo las políticas
D. Solo envía alertas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Registra las infracciones de las políticas, pero permite el tráfico**

**Explicación:**
En modo de auditoría (anotación cilium.io/audit-mode: "true"), el tráfico que infringe las políticas no se bloquea; solo se registra. Esto permite evaluar el impacto de las nuevas políticas antes de aplicarlas a producción.

</details>

### 10. ¿Cuál es la política correcta para los servicios backend al implementar microsegmentación en una arquitectura de 3 capas?

A. Permitir todo el tráfico
B. Permitir ingress solo desde frontend y egress solo hacia database
C. Bloquear todo el ingress
D. Permitir acceso a internet

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Permitir ingress solo desde frontend y egress solo hacia database**

**Explicación:**
En la microsegmentación, los servicios backend siguen el principio de privilegio mínimo: permiten ingress solo desde la capa frontend y egress solo hacia la capa database. Esto define y controla claramente el tráfico entre cada capa.

</details>

### 11. ¿Qué afirmación describe correctamente la diferencia entre el cifrado IPsec y WireGuard en Cilium?

A. Solo IPsec opera en el kernel
B. WireGuard requiere gestión manual de claves
C. IPsec es estándar de IETF; WireGuard no es estándar
D. Solo WireGuard admite cifrado de nodo a nodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. IPsec es estándar de IETF; WireGuard no es estándar**

**Explicación:**
IPsec es un protocolo estándar de IETF, mientras que WireGuard no es estándar. Ambos operan en el kernel y WireGuard proporciona gestión automática de claves. Ambos admiten cifrado de nodo a nodo.

</details>

### 12. ¿Qué comando se utiliza para monitorizar infracciones de políticas con Hubble?

A. hubble observe --verdict FORWARDED
B. hubble observe --verdict DROPPED
C. hubble policy list
D. hubble status --violations

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. hubble observe --verdict DROPPED**

**Explicación:**
El comando `hubble observe --verdict DROPPED` monitoriza el tráfico que ha sido denegado (DROPPED) por las políticas de red. Esto permite la detección y el análisis en tiempo real de las infracciones de políticas.

</details>

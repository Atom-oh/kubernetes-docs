# Cuestionario de seguridad de Linkerd

Este cuestionario evalúa tu comprensión de las características de seguridad de Linkerd.

## Preguntas del cuestionario

### 1. ¿Cómo se habilita mTLS en Linkerd?

A. Se requiere configuración manual para cada servicio
B. Se aplica automáticamente a todo el tráfico de la malla
C. Se requiere configuración mediante Kubernetes Secrets
D. Debe habilitarse por namespace

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Se aplica automáticamente a todo el tráfico de la malla**

**Explicación:**
Uno de los valores fundamentales de Linkerd es la «seguridad de forma predeterminada». A todo el tráfico entre servicios de la malla se le aplica mTLS automáticamente sin ninguna configuración.

</details>

### 2. ¿Cuál es la función del recurso Server?

A. Definir conexiones de servidores externos
B. Definir el puerto y el protocolo del tráfico entrante
C. Almacenar certificados de servidor
D. Configurar balanceadores de carga

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Definir el puerto y el protocolo del tráfico entrante**

**Explicación:**
El recurso Server define el tráfico entrante para Pods específicos. Especifica los Pods de destino con podSelector, el puerto con port y el protocolo (HTTP/1, HTTP/2, gRPC, opaque) con proxyProtocol.

</details>

### 3. ¿Qué especifica meshTLS.serviceAccounts en ServerAuthorization?

A. ServiceAccount que debe usar el servidor
B. ServiceAccounts de cliente a las que se permite el acceso
C. ServiceAccount con permiso de emisión de certificados
D. ServiceAccount con permiso de recopilación de métricas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. ServiceAccounts de cliente a las que se permite el acceso**

**Explicación:**
meshTLS.serviceAccounts de ServerAuthorization especifica qué ServiceAccounts de cliente pueden acceder al Server. Solo se permite el acceso a los workloads con las ServiceAccounts especificadas.

</details>

### 4. ¿Cómo se permite el tráfico en el modo de política default-deny?

A. Todo el tráfico se permite automáticamente
B. Se requiere una definición explícita de ServerAuthorization
C. Permitir mediante etiquetas de namespace
D. Configurar una lista blanca en ConfigMap

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Se requiere una definición explícita de ServerAuthorization**

**Explicación:**
En el modo default-deny, todo el tráfico se deniega de forma predeterminada. Para permitir tráfico, Server y ServerAuthorization deben definirse explícitamente. Este es un modelo de seguridad zero-trust.

</details>

### 5. ¿Cuál es el período de validez recomendado para Trust Anchor?

A. 24 horas
B. 1 año
C. 1-10 años
D. Ilimitado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. 1-10 años**

**Explicación:**
Trust Anchor (Root CA) debe ser válido durante un período prolongado. En general, se recomiendan 1-10 años. Dado que reemplazar Trust Anchor es complejo, establece un período de validez lo suficientemente largo, ajustándolo según los requisitos de seguridad.

</details>

### 6. ¿Qué configuración de ServerAuthorization permite clientes no autenticados (fuera de la malla)?

A. `meshTLS.identities: ["*"]`
B. `unauthenticated: true`
C. `external: allowed`
D. `client: any`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `unauthenticated: true`**

**Explicación:**
Configurar `client.unauthenticated: true` permite el acceso de clientes sin autenticación mTLS (fuera de la malla). Esto se utiliza para el tráfico de health checks o ingress.

</details>

### 7. ¿Qué se requiere al renovar el certificado de Identity Issuer?

A. Todos los proxies deben reiniciarse
B. Trust Anchor también debe reemplazarse
C. Actualizar Kubernetes Secret y reiniciar Identity Controller
D. Se requiere reiniciar todo el clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Actualizar Kubernetes Secret y reiniciar Identity Controller**

**Explicación:**
Al renovar Identity Issuer: 1) Actualiza el Secret con el certificado nuevo, 2) Reinicia Identity Controller. Los proxies se renuevan automáticamente con el certificado nuevo. No es necesario reemplazar Trust Anchor si sigue siendo el mismo.

</details>

### 8. ¿Qué modo de política permite solo tráfico mTLS desde dentro de la malla?

A. deny
B. all-unauthenticated
C. all-authenticated
D. cluster-unauthenticated

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. all-authenticated**

**Explicación:**
El modo `all-authenticated` permite solo tráfico autenticado mediante mTLS desde dentro de la malla. Se deniega el tráfico no autenticado desde fuera de la malla.

</details>

### 9. ¿Qué configuración se requiere en el recurso Certificate de cert-manager para la integración con Linkerd?

A. isCA: false
B. isCA: true
C. usages: [digital signature]
D. algorithm: RSA

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. isCA: true**

**Explicación:**
El Identity Issuer de Linkerd actúa como una CA intermedia, por lo que Certificate de cert-manager debe tener `isCA: true`. Este certificado firma certificados de workloads.

</details>

### 10. ¿Qué se puede verificar con el comando linkerd viz edges?

A. Estado del router de borde de red
B. Estado de la conexión mTLS entre servicios
C. Políticas de límites del clúster
D. Estado de la caché de borde DNS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Estado de la conexión mTLS entre servicios**

**Explicación:**
`linkerd viz edges` muestra las conexiones (edges) entre servicios, y la columna SECURED indica el estado de mTLS. El tráfico desde fuera de la malla muestra X en SECURED.

</details>

### 11. ¿Cuál es la relación correcta entre la seguridad de Linkerd y la seguridad de la aplicación?

A. Linkerd gestiona toda la seguridad, por lo que la seguridad de la aplicación no es necesaria
B. Linkerd gestiona la capa de transporte; las aplicaciones gestionan la seguridad de la lógica de negocio
C. La seguridad de la aplicación por sí sola es suficiente; la seguridad de Linkerd es opcional
D. Ambas seguridades son completamente independientes y no interactúan

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Linkerd gestiona la capa de transporte; las aplicaciones gestionan la seguridad de la lógica de negocio**

**Explicación:**
Siguiendo los principios de defensa en profundidad, Linkerd gestiona el cifrado de transporte (mTLS) y la autorización de servicios, mientras que las aplicaciones gestionan la seguridad de la lógica de negocio, como la autenticación de usuarios (JWT), RBAC y la validación de entradas.

</details>

### 12. ¿Cuál NO es una métrica de seguridad de Linkerd que se debe supervisar con alertas de Prometheus?

A. Tiempo de expiración del certificado
B. Proporción de tráfico no mTLS
C. Cantidad de fallos de inicio de sesión de la aplicación
D. Cantidad de solicitudes con autorización denegada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Cantidad de fallos de inicio de sesión de la aplicación**

**Explicación:**
Las métricas de seguridad de Linkerd incluyen: tiempo de expiración del certificado, proporción de tráfico no mTLS y cantidad de solicitudes con autorización denegada. Los fallos de inicio de sesión de la aplicación son métricas de nivel de aplicación que están fuera del alcance de Linkerd.

</details>

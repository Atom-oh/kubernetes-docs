# Cuestionario de seguridad de Linkerd

Basado en la [guía de seguridad](../../../service-mesh/linkerd/04-security.md), revisada el 11 de septiembre de 2026.

### 1. ¿Cómo habilita Linkerd mTLS en la malla?

- A. Cada servicio debe implementar Linkerd TLS por su cuenta
- B. Automáticamente para el tráfico TCP apto entre Pods participantes con la malla
- C. Cualquier Secret de Kubernetes cifra todas las rutas de red
- D. Todo el tráfico UDP queda protegido automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Ambos proxies deben participar y confiar en la cadena. Los endpoints que no están en la malla y los puertos excluidos no reciben automáticamente mTLS de Linkerd. De forma predeterminada aún se puede aceptar tráfico entrante sin cifrar; exige acceso autenticado mediante la política adecuada.

</details>

### 2. ¿Qué selecciona un recurso Server?

- A. Registros DNS externos
- B. Un puerto o protocolo entrante en los Pods coincidentes de su espacio de nombres
- C. Un Secret con un certificado
- D. Un algoritmo de balanceo de carga de salida

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Server selecciona el destino del Pod y el puerto. Declara los puertos de la aplicación y evita crear recursos Server que se solapen. El tráfico que no coincide se deniega de forma predeterminada, salvo que `accessPolicy` cambie ese comportamiento. Crear un Server en el puerto de administración 4191 del proxy no elimina la excepción de interceptación de ese puerto.

</details>

### 3. ¿Qué describe `meshTLS.serviceAccounts` en ServerAuthorization?

- A. El `serviceAccountName` del servidor
- B. Los ServiceAccounts de clientes autenticados a los que se permite el acceso
- C. La cuenta que emite todos los certificados
- D. Solo las cuentas que recopilan métricas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Esta autorización acepta las identidades de clientes de la malla que coinciden. Otras autorizaciones también pueden ampliar el acceso. La versión seleccionada sirve ServerAuthorization/v1beta1; AuthorizationPolicy también puede referirse directamente a un ServiceAccount, sin requerir esta autorización heredada.

</details>

### 4. ¿Cómo se permite el tráfico de negocio previsto cuando la política predeterminada es de denegación?

- A. Todas las solicitudes siguen permitidas automáticamente
- B. Definir el destino y las autorizaciones coincidentes
- C. Una etiqueta genérica de espacio de nombres concede acceso a cualquier cliente
- D. Basta con una lista de permitidos arbitraria en un ConfigMap

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Server junto con AuthorizationPolicy es un patrón actual; ServerAuthorization es una alternativa anterior. No son etapas obligatorias de una misma secuencia. Todas las referencias `requiredAuthenticationRefs` de una AuthorizationPolicy deben coincidir, y el acceso de las sondas necesita un tratamiento adecuado.

</details>

### 5. ¿Cómo se debe elegir la duración del ancla de confianza?

- A. Siempre debe ser exactamente 24 horas
- B. Siempre debe ser ilimitada
- C. Se elige según la política de CA y los requisitos de rotación y recuperación; el valor predeterminado de la CLI es un año
- D. Se aplica a todos los clústeres una recomendación universal obligatoria de 1 a 10 años

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Se puede usar una raíz manual con una duración de diez años, pero no es una práctica recomendada automáticamente. Lleva un seguimiento de los vencimientos de toda la cadena y comprueba que la duración de la entidad emisora sea compatible con su CA. Para rotar la raíz se necesita un periodo de solapamiento y distribuirla a todos los consumidores, incluidos los clústeres vinculados.

</details>

### 6. ¿Qué permite `client.unauthenticated: true` en un ServerAuthorization?

- A. Solo identidades autenticadas que coinciden con un comodín
- B. Clientes que no requieren autenticación de malla
- C. Solo clientes que usan un encabezado externo especial
- D. Solo la URL de disponibilidad declarada, sin importar el destino

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** El ajuste permite el acceso sin autenticación de la malla en todo su ámbito de destino. No limita automáticamente el acceso a una ruta de estado de salud. `meshTLS.identities: ["*"]` es distinto: permite ampliamente identidades de la malla, pero sigue requiriendo autenticación de malla.

</details>

### 7. ¿Qué ocurre normalmente cuando se renueva una entidad emisora válida bajo la misma raíz de confianza?

- A. Todos los proxies deben reiniciarse inmediatamente
- B. También debe cambiar siempre la raíz
- C. El propietario actualiza el Secret de la entidad emisora; Identity valida o vuelve a cargar sus archivos y los proxies renuevan normalmente los certificados hoja
- D. Se reinicia todo el clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Comprueba `IssuerUpdated` e investiga las actualizaciones omitidas o inválidas. Los certificados hoja existentes pueden seguir usando la entidad emisora anterior hasta su renovación normal, siempre que la cadena continúe siendo válida. No es obligatorio reiniciar Identity después de cada actualización de la entidad emisora; la rotación del ancla de confianza es un proceso gradual aparte.

</details>

### 8. ¿Qué política predeterminada exige clientes de malla autenticados, incluidos los clientes de multiclúster que sean de confianza?

- A. `deny`
- B. `all-unauthenticated`
- C. `all-authenticated`
- D. `cluster-unauthenticated`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** `all-authenticated` exige autenticación de la malla. No es una lista de permitidos limitada a clientes concretos. Las políticas Server explícitas y las autorizaciones siguen siendo relevantes, y las anotaciones predeterminadas del espacio de nombres se aplican cuando se inicializan los proxies.

</details>

### 9. ¿Qué se necesita cuando cert-manager emite el certificado de firma de la entidad emisora de Linkerd?

- A. `isCA: false`
- B. `isCA: true`, con credenciales ECDSA P-256 adecuadas y una cadena válida
- C. Solo el uso `digital-signature` en cualquier certificado hoja
- D. Siempre una clave privada RSA

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Identity necesita una CA intermedia que pueda firmar certificados de cargas de trabajo. También establece explícitamente `rotationPolicy`, verifica el formato y la propiedad del Secret y la duración de la CA, y confirma que Identity carga el resultado. Que una solicitud genérica de firma a Vault indique `isCA: true` no demuestra que esa ruta proporcione una CA.

</details>

### 10. ¿Qué pueden mostrar las conexiones de `linkerd viz edges`?

- A. El estado del hardware de cada router de borde
- B. Las conexiones observadas entre recursos y su estado mTLS o de seguridad
- C. La prueba de que todas las rutas posibles o inactivas están cifradas
- D. La auditoría completa de autenticación de usuarios finales

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** La vista SECURED es evidencia sobre conexiones observadas, no un inventario completo de la red. Usa `linkerd identity` para consultar certificados públicos y los diagnósticos o métricas de políticas para revisar decisiones de acceso. No confundas lo que muestra la CLI con los valores literales de las etiquetas TLS de Prometheus.

</details>

### 11. ¿Cómo se complementan la seguridad de Linkerd y la seguridad de la aplicación?

- A. mTLS de la malla elimina la necesidad de seguridad en la aplicación
- B. Los controles de cargas de trabajo y transporte de la malla complementan la autorización de usuarios, inquilinos y lógica de negocio
- C. Un ServiceAccount permitido demuestra que cada cliente es administrador
- D. La malla valida automáticamente las entradas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Linkerd aporta autenticación de cargas de trabajo, cifrado del transporte apto y autorización entrante. Las aplicaciones aún deben validar las credenciales, los permisos y las entradas de los usuarios. Los controles de red y admisión también cubren las rutas que evitan el proxy o que no están inscritas en la malla.

</details>

### 12. ¿Qué métrica requiere instrumentación en la aplicación u otra fuente que conozca la aplicación?

- A. El vencimiento del certificado de carga de trabajo del proxy
- B. Respuestas HTTP observadas sin identidad de cliente de la malla
- C. Fallos de inicio de sesión de la aplicación
- D. Contadores de denegación de autorización entrante del proxy

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Linkerd no conoce automáticamente los resultados de inicio de sesión de la aplicación. Para configurar sus propias alertas, distingue las marcas de tiempo de vencimiento de certificados hoja de la duración restante de la entidad emisora, usa proporciones de tráfico basadas en tasas y con ámbitos definidos, conserva las etiquetas de identidad y trata por separado la telemetría ausente o inactiva.

</details>

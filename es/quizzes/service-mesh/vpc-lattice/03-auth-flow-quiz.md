# Cuestionario sobre el flujo de autenticación de IAM

Este cuestionario evalúa tu comprensión del flujo de autenticación de IAM de Lattice en cuatro etapas, las dificultades de firma SigV4 y el diagnóstico de errores 403.

## Preguntas de opción múltiple

1. ¿Qué nombre de servicio se usa para firmar con SigV4 las solicitudes del plano de datos de VPC Lattice?
   - A) `vpc-lattice`
   - B) `vpc-lattice-svcs`
   - C) `lattice`
   - D) `execute-api`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `vpc-lattice-svcs`**

**Explicación:**
`vpc-lattice-svcs` es el nombre de servicio para firmar solicitudes del plano de datos. Es fácil confundirlo con `vpc-lattice`, que es el nombre de servicio de la API del plano de control de Lattice (para crear servicios, listeners, etc.). El nombre de servicio es una entrada para derivar la clave de firma (clave secreta → fecha → región → nombre de servicio → cadena de terminación, cuatro operaciones HMAC-SHA256 encadenadas), así que si es incorrecto no se validará la firma. Coincide con el propio nombre DNS del servicio, que tiene el formato `...vpc-lattice-svcs.<region>.on.aws`.
</details>

2. ¿Cuál es la causa más común de un 403 con la autenticación de IAM de Lattice?
   - A) Falta el principal en la política de autenticación del servicio de Lattice
   - B) La política basada en identidad del rol de IAM que hace la llamada no incluye `vpc-lattice-svcs:Invoke`
   - C) El grupo de seguridad del nodo no permite la lista de prefijos de Lattice
   - D) Falla la comprobación de estado del Target Group

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) La política basada en identidad del rol de IAM que hace la llamada no incluye `vpc-lattice-svcs:Invoke`**

**Explicación:**
Es natural pensar «la política de autenticación del servicio permite este rol, así que ya está», pero el propio rol que llama también necesita permiso Invoke; una política de recursos por sí sola no basta. El mensaje de error real termina con `because no identity-based policy allows the vpc-lattice-svcs:Invoke action`, que indica la causa; si encuentras un 403, lee primero esa parte. La opción C produciría un fallo de conexión o un tiempo de espera agotado, no un 403.
</details>

3. Si empiezan a aparecer 403 justo después de introducir un dominio personalizado, ¿qué se debe comprobar primero?
   - A) El ajuste de protocolo del Target Group
   - B) El encabezado `Host`: SigV4 siempre firma este encabezado, así que el Host usado al firmar debe coincidir con el Host de la solicitud real
   - C) Si se superaron las cuotas de Lattice
   - D) Los ajustes de resolución DNS de la VPC

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El encabezado `Host`: SigV4 siempre firma este encabezado, así que el Host usado al firmar debe coincidir con el Host de la solicitud real**

**Explicación:**
SigV4 siempre incluye el encabezado `Host` en la firma. Al asociar un dominio personalizado, los clientes envían solicitudes a ese dominio y deben firmar con ese valor; si la lógica de firma sigue usando el dominio generado por Lattice, la firma no coincide. Este problema aparece en el momento de asociar el dominio personalizado, no al comienzo de la migración, por lo que es fácil pasarlo por alto. Al introducir un dominio personalizado, hay que resolver al mismo tiempo el control de SNI, el valor de Host firmado y la gestión de certificados.
</details>

4. Si «solo los pods de un nodo específico tienen errores 403 intermitentes», ¿cuál es la causa más probable?
   - A) Una configuración incorrecta del grupo de seguridad de ese nodo
   - B) La sincronización del reloj de ese nodo: se firma `x-amz-date` y la tolerancia de SigV4 es de unos 5 minutos
   - C) Gateway API Controller no se está ejecutando en ese nodo
   - D) La versión de kubelet de ese nodo es demasiado antigua

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) La sincronización del reloj de ese nodo: se firma `x-amz-date` y la tolerancia de SigV4 es de unos 5 minutos**

**Explicación:**
La guía general de SigV4 de AWS indica que la mayoría de las solicitudes deben recibirse dentro de los cinco minutos de su marca de tiempo. Comprueba el error real del servicio y el reloj UTC; no presentes esto como una garantía independiente medida específicamente para Lattice.
</details>

5. ¿Qué se debe comprobar entre la firma y la verificación de Lattice?
   - A) Varios proxies aumentan la latencia
   - B) Cambiar los campos canónicos firmados puede interrumpir la verificación; Lattice requiere `UNSIGNED-PAYLOAD`, por lo que la integridad del cuerpo también necesita controles de TLS/aplicación
   - C) Un proxy no puede almacenar credenciales en caché
   - D) Un rol de IAM solo se puede asociar a un proxy

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Cambiar los campos canónicos firmados puede interrumpir la verificación; Lattice requiere `UNSIGNED-PAYLOAD`, por lo que la integridad del cuerpo también necesita controles de TLS/aplicación**

**Explicación:**
Los valores firmados de Host, ruta y consulta deben coincidir con la solicitud. La ordenación canónica implica que un orden equivalente de parámetros de consulta no necesariamente constituye un cambio. Lattice no admite la firma de la carga útil; requiere el encabezado `x-amz-content-sha256: UNSIGNED-PAYLOAD`.
</details>

6. ¿Por qué una política de autenticación podría no aplicarse al tráfico dentro del clúster?
   - A) Las políticas de autenticación no admiten tráfico IPv6
   - B) Si el cliente llama directamente al nombre DNS del Service de Kubernetes, omite Lattice y nunca se evalúa la política de autenticación
   - C) Las políticas de autenticación solo se aplican a llamadas entre cuentas
   - D) Gateway API Controller aún no reconcilió la política

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Si el cliente llama directamente al nombre DNS del Service de Kubernetes, omite Lattice y nunca se evalúa la política de autenticación**

**Explicación:**
La documentación de AWS Gateway API Controller lo indica explícitamente: `IAMAuthPolicy` autoriza solo el tráfico que pasa por Gateways, HTTPRoutes y GRPCRoutes. Enviar una solicitud a `http://svc.ns.svc.cluster.local` omite Lattice, así que no se evalúa ninguna política. Durante la migración, cuando coexisten ambas rutas, habrá rutas en las que se aplica la autorización y otras en las que no; se necesitan controles compensatorios, como NetworkPolicy. Otra causa frecuente es que `authType` sea `NONE` y no `AWS_IAM`.
</details>

7. ¿Cómo cambian el «alcance» y la «direccionalidad» de la autenticación de AS-IS (App Mesh + SPIRE mTLS) a TO-BE (IAM Auth de Lattice)?
   - A) Bidireccional y por conexión → bidireccional y por solicitud
   - B) Autenticación mutua bidireccional y por conexión → unidireccional y por solicitud (prueba del cliente), más un certificado de servidor TLS
   - C) Unidireccional y por solicitud → bidireccional y por conexión
   - D) No cambia ni el alcance ni la direccionalidad

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Autenticación mutua bidireccional y por conexión → unidireccional y por solicitud (prueba del cliente), más un certificado de servidor TLS**

**Explicación:**
mTLS autentica ambos extremos mediante sus SVID al establecer la conexión. IAM Auth de Lattice verifica la firma SigV4 de quien llama para cada solicitud y puede aplicar condiciones de política a ruta/método/encabezado. SigV4 protege los campos canónicos firmados; Lattice requiere `UNSIGNED-PAYLOAD` y no admite la firma de la carga útil. Protege el cuerpo mediante TLS y evalúa por separado el robo de credenciales, la vigencia de las solicitudes y los ataques de repetición, en vez de afirmar que la firma de solicitudes siempre evita el secuestro de conexiones. En el diseño de listener HTTPS, la autenticación del servidor usa el certificado de servidor TLS, no la identidad SPIFFE del otro extremo.
</details>

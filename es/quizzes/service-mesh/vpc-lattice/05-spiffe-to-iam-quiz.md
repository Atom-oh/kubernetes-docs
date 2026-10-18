# Cuestionario sobre la migración de identidad de cargas de trabajo

Este cuestionario evalúa tu comprensión de la estructura de SPIFFE/SPIRE, el principio de atestación y sus similitudes y diferencias decisivas respecto de IAM Auth.

## Preguntas de opción múltiple

1. ¿Por qué un SPIFFE ID no incluye información de red, como una dirección IP o un nombre de host?
   - A) El formato URI no puede expresar direcciones IP
   - B) La identidad debe seguir siendo la misma sin importar dónde se planifique la carga de trabajo ni cómo cambie su IP
   - C) La información de red se transporta por separado en el SVID
   - D) Exponer IP supone un riesgo de seguridad

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) La identidad debe seguir siendo la misma sin importar dónde se planifique la carga de trabajo ni cómo cambie su IP**

**Explicación:**
Un SPIFFE ID tiene el formato `spiffe://<trust-domain>/<workload-path>`, donde la ruta normalmente refleja el espacio de nombres y el ServiceAccount. Excluir la información de red es intencional: un pod puede reprogramarse y obtener una IP nueva, pero su identidad debe mantenerse. Este es el punto de partida para pasar del control basado en IP al control basado en identidad, la misma lógica que explica por qué el control basado en la IP de destino deja de tener sentido dentro del rango de enlace local de Lattice.
</details>

2. En la atestación de cargas de trabajo de SPIRE, ¿en qué momento se resuelve de manera decisiva el problema de inicialización de confianza?
   - A) Cuando la carga de trabajo presenta un token preinstalado
   - B) El agente usa información de pares proporcionada por el kernel bajo un modelo de kernel/atestador de confianza y contrasta los selectores de la carga de trabajo
   - C) Cuando el servidor firma el SVID
   - D) Cuando Envoy recibe el certificado mediante SDS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El agente usa información de pares proporcionada por el kernel bajo un modelo de kernel/atestador de confianza y contrasta los selectores de la carga de trabajo**

**Explicación:**
Esto evita pedirle a la carga de trabajo que inicie la confianza con un secreto compartido de aplicación preestablecido. No es una garantía incondicional contra la vulneración del host, selectores deficientes o una configuración incorrecta del atestador.
</details>

3. ¿Por qué los SVID se diseñan con tiempos de vida cortos?
   - A) Para ahorrar espacio de almacenamiento
   - B) Los tiempos de vida cortos limitan el tiempo de utilidad de las credenciales, pero no reemplazan la respuesta a vulneraciones ni los controles de autorización
   - C) Para distribuir la carga de firma de la CA
   - D) Para eliminar todos los secretos de runtime y cualquier requisito de respuesta a vulneraciones

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Los tiempos de vida cortos limitan el tiempo de utilidad de las credenciales, pero no reemplazan la respuesta a vulneraciones ni los controles de autorización**

**Explicación:**
Revisa la renovación, el almacenamiento en runtime, la exposición a repetición y el comportamiento de denegación/revocación de emergencia. Las credenciales que vencen siguen conteniendo secretos y no son seguras automáticamente hasta su vencimiento.
</details>

4. ¿Cuáles son las dos similitudes estructurales entre SPIFFE/SPIRE y IAM Auth de Lattice?
   - A) Ambos usan certificados X.509 y ambos realizan mTLS
   - B) Ambos pueden evitar secretos de larga duración incrustados, pero las claves privadas de runtime o las credenciales temporales secretas todavía se deben proteger
   - C) En ambos, el cliente opera una CA y ambos autentican por conexión
   - D) Ambos admiten cargas de trabajo fuera de AWS y ambos autentican por solicitud

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Ambos pueden evitar secretos de larga duración incrustados, pero las claves privadas de runtime o las credenciales temporales secretas todavía se deben proteger**

**Explicación:**
La entrega de X.509-SVID incluye material de clave; las credenciales de IAM incluyen una clave de acceso secreta y un token de sesión. La atestación de la plataforma cambia el aprovisionamiento, pero no elimina la necesidad de proteger sockets/endpoints, memoria y cachés.
</details>

5. ¿Cuál es la consecuencia práctica de la diferencia decisiva (a), el cambio en la direccionalidad de la autenticación?
   - A) La prueba del cliente se debilita, por lo que la aplicación debe compensarlo
   - B) La prueba de identidad del servidor se reduce al nivel de un certificado de servidor TLS, así que la defensa pasa de la autenticación mutua de cargas de trabajo al control de IAM sobre la creación de recursos de Lattice
   - C) Se conserva la autenticación bidireccional, así que no hay consecuencias para la revisión
   - D) La autenticación deja de ser necesaria

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) La prueba de identidad del servidor se reduce al nivel de un certificado de servidor TLS, así que la defensa pasa de la autenticación mutua de cargas de trabajo al control de IAM sobre la creación de recursos de Lattice**

**Explicación:**
La prueba del cliente se vuelve más granular (verificación SigV4 por solicitud). El problema es la prueba del servidor: el cliente solo puede confirmar que el certificado TLS es válido y el dominio coincide; no hay ningún paso que confirme «¿realmente es el servicio de ese equipo?» dentro de un sistema de identidad de cargas de trabajo. La respuesta es restringir estrictamente mediante IAM quién puede crear servicios de Lattice, controlar las asociaciones de redes de servicios y supervisar con CloudTrail. Si la documentación de revisión dice «autenticación mutua», se debe reescribir ese punto.
</details>

6. ¿Por qué la diferencia decisiva (b), la transferencia de la propiedad de la raíz de confianza, es una consideración importante en las revisiones del sector financiero?
   - A) IAM de AWS es menos seguro que SPIRE
   - B) Los estándares de seguridad de muchas organizaciones exigen, o se interpretan como si exigieran, que la raíz de confianza de un sistema de autenticación esté bajo su propio control, y operar una CA propia era la forma más directa de cumplirlo
   - C) CloudTrail no ofrece un registro de auditoría
   - D) La autoridad sobre las decisiones de políticas de IAM se transfiere a AWS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Los estándares de seguridad de muchas organizaciones exigen, o se interpretan como si exigieran, que la raíz de confianza de un sistema de autenticación esté bajo su propio control, y operar una CA propia era la forma más directa de cumplirlo**

**Explicación:**
Es probable que SPIRE se adoptara tras superar precisamente esa revisión. Pasar a IAM Auth de Lattice implica reconstruir el argumento con fundamentos disponibles, como el modelo de responsabilidad compartida, la autoridad de políticas que se conserva (el cliente sigue definiendo mediante IAM quién puede llamar a qué), los registros de auditoría mediante CloudTrail y los registros de acceso, y la ventaja de que el cliente no guarda una clave privada de CA y, por tanto, elimina el riesgo de fuga de esa clave. Sin embargo, el argumento es que «el control se ejerce de otra manera», no que «sea equivalente», y la aceptación depende de los estándares de la organización. D es incorrecta: la autoridad sobre las políticas sigue siendo del cliente.
</details>

7. ¿En qué situación podría ser necesario seguir operando SPIRE después de migrar a Lattice?
   - A) En cualquier caso en que se use IAM Auth
   - B) Cuando la arquitectura elegida todavía necesite identidades de endpoint SPIFFE, incluido mTLS de endpoint o cargas de trabajo admitidas fuera de AWS
   - C) Cuando se use Gateway API Controller
   - D) Cuando haya una implementación con varios clústeres

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Cuando la arquitectura elegida todavía necesite identidades de endpoint SPIFFE, incluido mTLS de endpoint o cargas de trabajo admitidas fuera de AWS**

**Explicación:**
Mantener SPIRE es una opción arquitectónica, no un requisito universal para todas las cargas de trabajo fuera de AWS. Se pueden evaluar otros proveedores de credenciales y rutas de red privada admitidas.
</details>

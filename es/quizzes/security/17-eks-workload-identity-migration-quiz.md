# Cuestionario sobre la migración de IAM de cargas de trabajo de EKS

> **Última actualización**: 21 de noviembre de 2026

[Lee el cuaderno de trabajo y consulta la demostración en vivo](../../security/17-eks-workload-identity-migration.md)

### 1. ¿Cuál es el principal problema de asociar el permiso de S3 de una aplicación al rol de IAM del nodo?

- A) Las solicitudes a S3 se vuelven más lentas
- B) Todos los Pod de ese nodo que puedan acceder a IMDS usan el mismo permiso
- C) El nodo ya no puede unirse al clúster
- D) El bucket de S3 se vuelve público

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Todos los Pod de ese nodo que puedan acceder a IMDS usan el mismo permiso**

**Explicación:** El rol del nodo se asocia a todo el nodo mediante el perfil de instancia. Con un límite de saltos de 2 o más, los Pod normales pueden obtener credenciales del rol del nodo a través de IMDSv2. CloudTrail solo registra la sesión de la instancia del nodo, por lo que es difícil distinguir las cargas de trabajo.

</details>

### 2. En la cadena de credenciales predeterminada del SDK de AWS, ¿dónde se sitúan los proveedores de IRSA y Pod Identity con respecto a IMDS?

- A) IMDS va primero
- B) IRSA (identidad web) y Pod Identity (proveedor de contenedores) van ambos antes que IMDS
- C) El orden es aleatorio
- D) Solo Pod Identity va antes que IMDS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) IRSA (identidad web) y Pod Identity (proveedor de contenedores) van ambos antes que IMDS**

**Explicación:** Las claves de entorno, el token de identidad web y el proveedor de credenciales de contenedor preceden a IMDS. Un Pod nuevo al que EKS haya inyectado las variables usa el nuevo rol sin cambios en el código; un Pod al que no se le haya inyectado nada recurre al rol del nodo obtenido de IMDS.

</details>

### 3. ¿Por qué puede STS confiar en el token proyectado de IRSA?

- A) El token contiene claves de acceso de IAM
- B) El emisor del clúster está registrado como proveedor OIDC de IAM y la política de confianza del rol comprueba `aud` y `sub`
- C) El Pod Identity Agent firma el token
- D) El rol del nodo llama a STS en nombre del Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El emisor del clúster está registrado como proveedor OIDC de IAM y la política de confianza del rol comprueba `aud` y `sub`**

**Explicación:** STS `AssumeRoleWithWebIdentity` verifica la firma del token con las claves del emisor registradas mediante el proveedor OIDC y comprueba las condiciones de confianza: `aud` es `sts.amazonaws.com` y `sub` es `system:serviceaccount:<namespace>:<serviceaccount>`.

</details>

### 4. Con Pod Identity, ¿qué permiso debe permanecer en el rol del nodo?

- A) El permiso de lectura de S3 de la aplicación
- B) `sts:AssumeRoleWithWebIdentity`
- C) `eks-auth:AssumeRoleForPodIdentity` para que el agente llame a EKS Auth (parte de `AmazonEKSWorkerNodePolicy`)
- D) Ninguno

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) `eks-auth:AssumeRoleForPodIdentity` para que el agente llame a EKS Auth (parte de `AmazonEKSWorkerNodePolicy`)**

**Explicación:** El Pod Identity Agent llama a EKS Auth con este permiso del rol del nodo. El permiso de negocio de la aplicación debe estar en el rol de Pod Identity indicado en la asociación.

</details>

### 5. En el `diff` de la demostración, ¿qué claim distinguía el token de IRSA del token de Pod Identity?

- A) `iss`
- B) `aud`
- C) `exp`
- D) Eran idénticos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `aud`**

**Explicación:** Ambos son tokens de ServiceAccount firmados por el mismo emisor del clúster. La audiencia del token de IRSA es `sts.amazonaws.com`; la del token de Pod Identity es `pods.eks.amazonaws.com`. `sub` varía según la ServiceAccount.

</details>

### 6. ¿Qué método permite que un solo rol de IAM sirva a diez clústeres nuevos sin cambios en la política de confianza?

- A) IRSA
- B) EKS Pod Identity
- C) Ninguno requiere cambios
- D) Ambos requieren modificaciones para cada clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) EKS Pod Identity**

**Explicación:** Un rol de Pod Identity solo confía en `pods.eks.amazonaws.com`; las asociaciones y las etiquetas de sesión establecen el ámbito del clúster. IRSA requiere un proveedor OIDC y una declaración de confianza por clúster, y la política de confianza predeterminada de 2.048 caracteres suele admitir unas cuatro vinculaciones.

</details>

### 7. Un Pod que se ejecuta en Fargate necesita un rol de carga de trabajo. ¿Qué método se debe usar?

- A) EKS Pod Identity
- B) IRSA
- C) El rol del nodo
- D) Ninguno funciona

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) IRSA**

**Explicación:** EKS Pod Identity solo admite nodos EC2 Linux en EKS. Usa IRSA en Fargate, en nodos EC2 Windows, en Outposts y en EKS Anywhere.

</details>

### 8. Creaste una asociación e implementaste los cambios inmediatamente, pero el Pod nuevo sigue usando el rol del nodo. ¿Cuál es la causa más probable?

- A) La política del bucket lo denegó
- B) La asociación aún no había llegado a la admisión del Pod, así que no se inyectó nada
- C) El Pod Identity Agent bloqueó IMDS
- D) También se requiere una anotación de IRSA

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La asociación aún no había llegado a la admisión del Pod, así que no se inyectó nada**

**Explicación:** Las asociaciones tienen consistencia eventual y pueden tardar varios segundos. En el primer ensayo de la demostración, una implementación justo después de la creación no recibió ninguna inyección; en el segundo, la inyección tardó 5 segundos en aparecer. Comprueba la plantilla del Pod con `kubectl create --dry-run=server` antes de implementarla.

</details>

### 9. Añades una asociación de Pod Identity a una ServiceAccount que ya tiene una anotación de IRSA y, después, creas un Pod nuevo. ¿Qué credenciales usa el Pod nuevo?

- A) Pod Identity: el webhook solo inyecta las variables de Pod Identity
- B) IRSA: el proveedor de identidad web va primero en la cadena
- C) Se alternan en cada solicitud
- D) El Pod no se inicia debido al conflicto

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Pod Identity: el webhook solo inyecta las variables de Pod Identity**

**Explicación:** Cuando hay una asociación, el webhook de EKS solo inyecta `AWS_CONTAINER_CREDENTIALS_FULL_URI` y `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE` en los Pod nuevos, no las variables de IRSA, tal como mostró la ejecución en seco en el clúster de demostración. El orden de la cadena (B) solo importa cuando están presentes ambos conjuntos; los Pod creados antes de la asociación siguen usando IRSA hasta que se vuelvan a crear.

</details>

### 10. Justo después de quitar la política de S3 del rol del nodo, se deniega la lectura del Pod heredado. ¿Puedes declarar que la migración ha terminado?

- A) Sí, una sola denegación es definitiva
- B) No, los cambios de IAM tienen consistencia eventual y los resultados pueden mezclarse durante minutos, así que sigue observando
- C) Sí, una vez que se reinicie el nodo
- D) No, debes eliminar el rol del nodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No, los cambios de IAM tienen consistencia eventual y los resultados pueden mezclarse durante minutos, así que sigue observando**

**Explicación:** En la demostración, se denegó la solicitud del Pod heredado después de 13 segundos, pero unos 4,5 minutos más tarde aparecieron otras dos lecturas permitidas. Observa durante varios minutos, incluidas las ejecuciones programadas, y conserva una copia exacta de la política para poder revertir los cambios.

</details>

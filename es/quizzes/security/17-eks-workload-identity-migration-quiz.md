# Cuestionario sobre la migración de IAM para cargas de trabajo de EKS

> **Última actualización**: 21 de noviembre de 2026

[Lee el cuaderno de trabajo y consulta la demostración en vivo](../../security/17-eks-workload-identity-migration.md)

### 1. ¿Cuál es el principal problema de asignar el permiso de S3 de una aplicación al rol de IAM del nodo?

- A) Las solicitudes de S3 se vuelven más lentas
- B) Todos los Pod de ese nodo que puedan acceder a IMDS usan el mismo permiso
- C) El nodo ya no puede unirse al clúster
- D) El bucket de S3 se vuelve público

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Todos los Pod de ese nodo que puedan acceder a IMDS usan el mismo permiso**

**Explicación:** El rol del nodo se asigna al nodo completo mediante el perfil de instancia. Con un límite de saltos de 2 o más, los Pod comunes pueden obtener credenciales del rol del nodo a través de IMDSv2. CloudTrail registra únicamente la sesión de la instancia del nodo, por lo que es difícil distinguir las cargas de trabajo.

</details>

### 2. En la cadena predeterminada de credenciales del SDK de AWS, ¿dónde se ubican los proveedores de IRSA y Pod Identity con respecto a IMDS?

- A) IMDS aparece primero
- B) IRSA (identidad web) y Pod Identity (proveedor de contenedores) aparecen ambos antes de IMDS
- C) El orden es aleatorio
- D) Solo Pod Identity aparece antes de IMDS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) IRSA (identidad web) y Pod Identity (proveedor de contenedores) aparecen ambos antes de IMDS**

**Explicación:** Las claves del entorno, el token de identidad web y el proveedor de credenciales de contenedor preceden a IMDS. Un Pod nuevo al que EKS inyectó las variables usa el nuevo rol sin cambios en el código; un Pod al que no se le inyectó nada recurre al rol del nodo obtenido de IMDS.

</details>

### 3. ¿Por qué STS puede confiar en el token proyectado en IRSA?

- A) El token contiene claves de acceso de IAM
- B) El emisor del clúster está registrado como proveedor OIDC de IAM, y la política de confianza del rol comprueba `aud` y `sub`
- C) El Pod Identity Agent firma el token
- D) El rol del nodo llama a STS en nombre del Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El emisor del clúster está registrado como proveedor OIDC de IAM, y la política de confianza del rol comprueba `aud` y `sub`**

**Explicación:** STS `AssumeRoleWithWebIdentity` verifica la firma del token con las claves del emisor registradas mediante el proveedor OIDC y comprueba las condiciones de confianza: `aud` es `sts.amazonaws.com` y `sub` es `system:serviceaccount:<namespace>:<serviceaccount>`.

</details>

### 4. Con Pod Identity, ¿qué permiso debe permanecer en el rol del nodo?

- A) El permiso de lectura de S3 de la aplicación
- B) `sts:AssumeRoleWithWebIdentity`
- C) `eks-auth:AssumeRoleForPodIdentity` para que el agente llame a EKS Auth (incluido en `AmazonEKSWorkerNodePolicy`)
- D) Ninguno

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) `eks-auth:AssumeRoleForPodIdentity` para que el agente llame a EKS Auth (incluido en `AmazonEKSWorkerNodePolicy`)**

**Explicación:** El Pod Identity Agent llama a EKS Auth con este permiso del rol del nodo. El permiso de negocio de la aplicación corresponde al rol de Pod Identity indicado en la asociación.

</details>

### 5. En el `diff` de la demostración, ¿qué atributo distinguía el token de IRSA del token de Pod Identity?

- A) `iss`
- B) `aud`
- C) `exp`
- D) Eran idénticos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `aud`**

**Explicación:** Ambos son tokens de ServiceAccount firmados por el mismo emisor del clúster. La audiencia del token de IRSA es `sts.amazonaws.com`; la del token de Pod Identity es `pods.eks.amazonaws.com`. `sub` varía según el ServiceAccount.

</details>

### 6. ¿Qué método permite que un solo rol de IAM sirva a diez clústeres nuevos sin cambios en la política de confianza?

- A) IRSA
- B) EKS Pod Identity
- C) Ninguno necesita cambios
- D) Ambos requieren modificaciones para cada clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) EKS Pod Identity**

**Explicación:** Un rol de Pod Identity confía únicamente en `pods.eks.amazonaws.com`; las asociaciones y las etiquetas de sesión establecen el ámbito del clúster. IRSA necesita un proveedor OIDC y una declaración de confianza para cada clúster, y la política de confianza predeterminada de 2.048 caracteres suele admitir unas cuatro vinculaciones.

</details>

### 7. Un Pod que se ejecuta en Fargate necesita un rol de carga de trabajo. ¿Qué método se usa?

- A) EKS Pod Identity
- B) IRSA
- C) El rol del nodo
- D) Ninguno funciona

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) IRSA**

**Explicación:** EKS Pod Identity admite nodos Linux EC2 en EKS y EKS Hybrid Nodes (con el DaemonSet híbrido del agente y el archivo de credenciales del nodo). Usa IRSA en Fargate, nodos Windows EC2, Outposts y EKS Anywhere.

</details>

### 8. Creaste una asociación e implementaste los cambios de inmediato, pero el nuevo Pod sigue usando el rol del nodo. ¿Cuál es la causa más probable?

- A) La política del bucket lo denegó
- B) La asociación aún no se había propagado a la admisión de Pod, así que no se inyectó nada
- C) El Pod Identity Agent bloqueó IMDS
- D) También se requiere una anotación de IRSA

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La asociación aún no se había propagado a la admisión de Pod, así que no se inyectó nada**

**Explicación:** Las asociaciones tienen coherencia eventual y pueden tardar varios segundos. En el primer ensayo de la demostración, una implementación justo después de crear la asociación no recibió ninguna inyección; en el segundo, la inyección tardó 5 segundos en aparecer. Antes de implementar los cambios, comprueba la plantilla de Pod con `kubectl create --dry-run=server`.

</details>

### 9. Añades una asociación de Pod Identity a un ServiceAccount que ya tiene una anotación de IRSA y, después, creas un Pod nuevo. ¿Qué credenciales usa el nuevo Pod?

- A) Pod Identity: el webhook inyecta únicamente las variables de Pod Identity
- B) IRSA: el proveedor de identidad web aparece primero en la cadena
- C) Se alternan en cada solicitud
- D) El Pod no se inicia debido al conflicto

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Pod Identity: el webhook inyecta únicamente las variables de Pod Identity**

**Explicación:** Cuando hay una asociación, el webhook de EKS inyecta en los Pod nuevos únicamente `AWS_CONTAINER_CREDENTIALS_FULL_URI` y `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`, no las variables de IRSA, tal como mostró la prueba en seco en el clúster de la demostración. El orden de la cadena (B) solo importa cuando están presentes ambos conjuntos; los Pod creados antes de la asociación siguen usando IRSA hasta que se vuelvan a crear.

</details>

### 10. Justo después de quitar la política de S3 del rol del nodo, se deniega una lectura del Pod heredado. ¿Puedes declarar que la migración está terminada?

- A) Sí, una sola denegación es concluyente
- B) No, los cambios de IAM tienen coherencia eventual y los resultados pueden variar durante varios minutos, así que sigue observando
- C) Sí, una vez que se reinicie el nodo
- D) No, debes eliminar el rol del nodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No, los cambios de IAM tienen coherencia eventual y los resultados pueden variar durante varios minutos, así que sigue observando**

**Explicación:** En la demostración, se denegó el acceso del Pod heredado después de 13 segundos; sin embargo, unos 4,5 minutos más tarde aparecieron otras dos lecturas permitidas. Observa durante varios minutos, incluidos los procesos programados, y conserva una copia exacta de la política para poder revertir los cambios.

</details>

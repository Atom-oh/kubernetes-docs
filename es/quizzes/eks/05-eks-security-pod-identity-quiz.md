# Cuestionario de EKS Pod Identity

> **Última actualización**: 21 de noviembre de 2026

Este cuestionario evalúa tu comprensión de [EKS Pod Identity](../../eks/05-eks-security-pod-identity.md).

## Resumen del cuestionario
- Qué hace una asociación
- Flujo del agente y las credenciales
- Confianza del rol y etiquetas de sesión
- Acceso entre cuentas y almacenamiento en caché
- Coexistencia con IRSA y migración desde IRSA

## Preguntas de opción múltiple

### 1. ¿Qué afirmación sobre una asociación de EKS Pod Identity es correcta?

- A) Al crearla, se crea automáticamente la ServiceAccount en el espacio de nombres
- B) Concede permisos de RBAC de Kubernetes junto con el rol de IAM
- C) Se almacena en Kubernetes como una anotación en el propio objeto ServiceAccount
- D) Asocia un clúster, un espacio de nombres y una ServiceAccount con un rol de IAM en la API de EKS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Asocia un clúster, un espacio de nombres y una ServiceAccount con un rol de IAM en la API de EKS**

**Explicación:**

Una asociación es una correspondencia entre un clúster, un espacio de nombres y una ServiceAccount, por un lado, y un rol de IAM, por otro; se almacena en la API de EKS. No crea la ServiceAccount, no concede permisos de RBAC de Kubernetes ni crea el rol de IAM o el agente. En el ejemplo de la página se comprueban las asociaciones existentes con `list-pod-identity-associations` antes de crear una, para no sobrescribir la configuración de otra persona.

</details>

### 2. ¿Cómo obtiene las credenciales de Pod Identity el SDK de AWS en un Pod recién creado que tiene una asociación?

- A) El SDK llama al agente del nodo, que obtiene las credenciales de EKS Auth
- B) El agente intercepta de forma transparente y firma todas las solicitudes de AWS del Pod
- C) El SDK llama a STS AssumeRoleWithWebIdentity con un token de identidad web
- D) El SDK usa las credenciales del rol de IAM del nodo que recibe de IMDSv2

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) El SDK llama al agente del nodo, que obtiene las credenciales de EKS Auth**

**Explicación:**

Para un Pod nuevo con una asociación, EKS inyecta un token con la audiencia `pods.eks.amazonaws.com`, una variable de entorno con la ruta al archivo del token y un URI de credenciales del contenedor. El SDK llama al punto de conexión del agente, que suele ser `169.254.170.23/v1/credentials`, y el agente llama a AssumeRoleForPodIdentity en EKS Auth y devuelve las credenciales al SDK. No es un interceptor de solicitudes: la aplicación sigue llamando directamente a los servicios de AWS con sus credenciales.

</details>

### 3. ¿Qué afirmación sobre el ejemplo de confianza del rol de Pod Identity es correcta?

- A) Nombra el proveedor OIDC de IAM del clúster como principal `Federated` en la relación de confianza
- B) Para Pod Identity, basta con permitir únicamente `sts:AssumeRoleWithWebIdentity`
- C) Confía en `pods.eks.amazonaws.com` para AssumeRole/TagSession, con alcance limitado mediante etiquetas
- D) Confiar en `pods.eks.amazonaws.com` sin condiciones aplica el principio de privilegio mínimo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Confía en `pods.eks.amazonaws.com` para AssumeRole/TagSession, con alcance limitado mediante etiquetas**

**Explicación:**

La política de confianza del ejemplo permite `sts:AssumeRole` y `sts:TagSession` para el principal de servicio `pods.eks.amazonaws.com`, con condiciones `aws:RequestTag/eks-cluster-arn`, `kubernetes-namespace` y `kubernetes-service-account`. Estas condiciones dependen de las etiquetas de sesión predeterminadas, por lo que, si se desactivan las etiquetas, hay que revisarlas. La persona o entidad que crea la asociación también necesita `iam:PassRole` para el rol previsto.

</details>

### 4. ¿Qué afirmación sobre el acceso a recursos de otra cuenta con Pod Identity es correcta?

- A) Se puede asociar directamente como rol de asociación cualquier rol de la otra cuenta
- B) Se mantiene el rol de asociación en la cuenta del clúster y se encadenan roles hasta llegar a un rol de destino
- C) Pod Identity no admite el acceso entre cuentas, así que siempre hay que cambiar esas cargas de trabajo a IRSA
- D) Si se usa un rol de destino, los cambios en la asociación restablecen de inmediato la caché de credenciales

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Se mantiene el rol de asociación en la cuenta del clúster y se encadenan roles hasta llegar a un rol de destino**

**Explicación:**

El rol de asociación debe estar en la cuenta del clúster de EKS. Un rol de IAM de destino opcional puede estar en otra cuenta; Pod Identity encadena el rol de la misma cuenta con ese rol de destino, siempre que se configuren la política de confianza y los permisos para asumir el rol. La guía actual indica que las credenciales almacenadas en caché duran 6 horas si no hay un rol de destino y 59 minutos si lo hay; los cambios en la asociación no restablecen esa caché. Si se vuelven a crear los Pods, se puede obtener antes la configuración nueva.

</details>

### 5. Si una ServiceAccount tiene tanto una anotación de IRSA como una asociación de Pod Identity, ¿cómo inyecta EKS las credenciales?

- A) Los Pods nuevos solo reciben las variables de Pod Identity; los Pods en ejecución conservan las variables de IRSA
- B) Los Pods nuevos reciben ambos conjuntos de variables y el SDK elige uno al azar
- C) Al crear la asociación, se reescribe de inmediato el entorno de los Pods en ejecución
- D) Siempre prevalece la anotación de IRSA, así que los Pods nuevos ignoran la asociación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Los Pods nuevos solo reciben las variables de Pod Identity; los Pods en ejecución conservan las variables de IRSA**

**Explicación:**

Como se confirma en [Migrar los permisos de IAM de los nodos de EKS a IRSA y Pod Identity](../../security/17-eks-workload-identity-migration.md#irsa-and-pod-identity-compared), cuando se configuran ambas opciones, el webhook de EKS inyecta únicamente `AWS_CONTAINER_CREDENTIALS_FULL_URI` y `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE` en los Pods nuevos. Los Pods en ejecución conservan sus variables de IRSA hasta que se vuelven a crear, por lo que hay que hacer el cambio mediante un despliegue controlado y eliminar la anotación que ya no se use. Un resultado de get-caller-identity que muestre el mismo rol no permite distinguir entre los dos mecanismos; por eso, hay que comprobar los nombres de las variables de entorno inyectadas.

</details>

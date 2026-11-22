# Cuestionario sobre IRSA y el proveedor OIDC

> **Última actualización**: 21 de noviembre de 2026

Este cuestionario comprueba tu comprensión de [IRSA y el proveedor OIDC](../../eks/05-eks-security-irsa-oidc.md).

## Resumen del cuestionario
- Emisor OIDC del clúster y proveedor OIDC de IAM
- Intercambio de tokens de IRSA
- Condiciones de confianza de los roles
- Descubrimiento/JWKS y rotación de claves

## Preguntas de opción múltiple

### 1. Un clúster de EKS publica un emisor OIDC y claves públicas de firma. ¿Qué más necesita IRSA para que una carga de trabajo pueda asumir un rol?

- A) Nada más; el endpoint del emisor por sí solo autoriza la asunción del rol
- B) Un proveedor de identidad OIDC externo asociado para el inicio de sesión de usuarios de Kubernetes
- C) Un proveedor OIDC de IAM, un rol con una relación de confianza coincidente y un SDK compatible
- D) Los permisos de S3 de destino de la carga de trabajo añadidos al rol de IAM del nodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Un proveedor OIDC de IAM, un rol con una relación de confianza coincidente y un SDK compatible**

**Explicación:**

El endpoint del emisor OIDC del clúster que publica EKS no crea por sí mismo un proveedor OIDC de IAM ni autoriza la asunción de roles. IRSA necesita el proveedor OIDC de IAM previsto en la cuenta del rol, un rol que confíe en él con las condiciones correctas para el emisor, el sujeto y la audiencia, y un SDK compatible. Un proveedor OIDC externo para el inicio de sesión de usuarios de Kubernetes es independiente de IRSA.

</details>

### 2. Con IRSA, ¿qué API llama el SDK para intercambiar el token de identidad web proyectado por credenciales temporales de AWS?

- A) EKS Auth AssumeRoleForPodIdentity
- B) STS AssumeRoleWithWebIdentity
- C) Credenciales del perfil de instancia de IMDSv2
- D) STS GetSessionToken

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) STS AssumeRoleWithWebIdentity**

**Explicación:**

El webhook de IRSA añade un token proyectado y la configuración del rol a un Pod apto, y el SDK intercambia el token con STS mediante AssumeRoleWithWebIdentity. STS valida el emisor, la firma, el token y la relación de confianza del rol, y luego devuelve credenciales temporales. AssumeRoleForPodIdentity es la API de EKS Auth que llama el agente de Pod Identity. Kubernetes rota el token proyectado y el SDK renueva las credenciales de AWS según ciclos de vida diferentes.

</details>

### 3. En el ejemplo de confianza de IRSA con alcance limitado, ¿qué condiciones restringen el rol al ServiceAccount `security-demo/irsa-reader`?

- A) Una condición de etiqueta de sesión `aws:RequestTag/kubernetes-service-account`
- B) Establecer `Principal.Service` en `pods.eks.amazonaws.com`
- C) Asignar al rol de IAM exactamente el mismo nombre que al ServiceAccount
- D) Condiciones StringEquals en `<issuer>:sub` y `<issuer>:aud`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Condiciones StringEquals en `<issuer>:sub` y `<issuer>:aud`**

**Explicación:**

Un rol de IRSA usa el proveedor OIDC de IAM como principal `Federated` y permite `sts:AssumeRoleWithWebIdentity`. Las condiciones StringEquals, cuyo prefijo es la ruta y el nombre de host completos del emisor, vinculan el ServiceAccount y la audiencia: `:sub` es `system:serviceaccount:security-demo:irsa-reader` y `:aud` es `sts.amazonaws.com`. Las condiciones `aws:RequestTag/...` y `pods.eks.amazonaws.com` pertenecen a la relación de confianza de Pod Identity. Un rol puede confiar en varios ServiceAccounts o emisores autorizados explícitamente; IRSA no exige un rol por ServiceAccount.

</details>

### 4. Al crear un validador que obtiene el documento de descubrimiento OIDC del clúster y JWKS para verificar tokens, ¿qué afirmación es correcta?

- A) Almacenar en caché las claves según Cache-Control y gestionar la rotación de claves y los valores `kid` desconocidos
- B) Obtener JWKS una sola vez, codificarlo de forma fija en el validador y reutilizarlo para siempre
- C) Considerar que una obtención correcta de JWKS demuestra que se validó la firma del token
- D) Omitir la comparación entre el emisor del documento de descubrimiento y el emisor del clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Almacenar en caché las claves según Cache-Control y gestionar la rotación de claves y los valores `kid` desconocidos**

**Explicación:**

El script de diagnóstico de la página obtiene el documento público de descubrimiento/JWKS y comprueba el emisor del documento de descubrimiento y el esquema HTTPS; no valida la firma de un token de carga de trabajo ni los permisos de IAM. Los validadores automatizados deben almacenar las claves en caché según Cache-Control y gestionar la rotación de claves de firma y los valores `kid` desconocidos mediante una biblioteca JWT revisada. EKS rota su clave de firma OIDC cada siete días.

</details>

### 5. ¿Cómo puede un validador sin salida a Internet acceder al documento de descubrimiento OIDC y a JWKS del clúster?

- A) Crear el endpoint de interfaz de la API de administración de EKS, que también sirve OIDC
- B) Abrir temporalmente la salida 0.0.0.0/0 en el grupo de seguridad cuando sea necesario
- C) Usar el endpoint de interfaz de PrivateLink `oidc-eks` para el descubrimiento y JWKS
- D) No preparar ninguna ruta de red, porque IRSA nunca necesita JWKS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Usar el endpoint de interfaz de PrivateLink `oidc-eks` para el descubrimiento y JWKS**

**Explicación:**

Las versiones actuales de EKS admiten un endpoint de interfaz de PrivateLink para el descubrimiento OIDC/JWKS del clúster, `com.amazonaws.region-code.oidc-eks`, destinado a validadores sin salida a Internet. Comprueba los requisitos de Región/DNS de ese endpoint; el endpoint de la API de administración de EKS es un servicio distinto.

</details>

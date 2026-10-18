# Cuestionario de gestión de Secrets

> **Última actualización**: 13 de septiembre de 2026

Este cuestionario evalúa tus conocimientos sobre los Secrets de Kubernetes, AWS Secrets Manager, External Secrets Operator y el cifrado.

## Preguntas del cuestionario

### 1. ¿Cuál es el método de codificación predeterminado para los Secrets de Kubernetes?

A. Cifrado AES-256
B. Codificación Base64
C. Hash SHA-256
D. Cifrado RSA

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Codificación Base64**

**Explicación:**
El campo `data` serializado de un Secret usa Base64. La codificación no es cifrado. Protege el acceso a la API, el almacenamiento y la aplicación consumidora; usar un almacén externo no elimina estos requisitos.

</details>

### 2. ¿Qué servicio de AWS se usa para cifrar etcd en EKS?

A. AWS Secrets Manager
B. AWS KMS (Key Management Service)
C. AWS Certificate Manager
D. AWS CloudHSM

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. AWS KMS (Key Management Service)**

**Explicación:**
A partir de EKS 1.28, el valor predeterminado es el cifrado de sobre con KMS de todos los datos de la API de Kubernetes mediante una clave propiedad de AWS. También hay una opción para usar una clave administrada por el cliente. Esto es distinto de configurar un servidor de API autoadministrado; no des por hecho que EKS almacena los datos de la API en texto sin cifrar ni que siempre se requiere una clave administrada por el cliente.

</details>

### 3. ¿Qué recursos hacen referencia a los Secrets de AWS Secrets Manager en External Secrets Operator?

A. SecretStore
B. ExternalSecret
C. ClusterSecretStore
D. A y B, o C y B

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. A y B, o C y B**

**Explicación:**
SecretStore/ClusterSecretStore describe el acceso y la identidad del proveedor; ExternalSecret selecciona los valores externos y define el Secret de destino. Un almacén con alcance de espacio de nombres referencia a una ServiceAccount de ese espacio de nombres. ClusterSecretStore necesita una referencia explícita al espacio de nombres y restricciones de uso.

</details>

### 4. ¿Cuál de estas NO es una forma de usar Secrets en un Pod?

A. Inyectarlos como variables de entorno
B. Montarlos como volúmenes
C. Usarlos como imagePullSecrets
D. Convertirlos en un ConfigMap

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Convertirlos en un ConfigMap**

**Explicación:**
Los Pods pueden consumir Secrets mediante referencias a claves, volúmenes e imagePullSecrets. Un ConfigMap es un objeto distinto, no un mecanismo para proteger Secrets. Las variables de entorno no se actualizan en contenedores en ejecución; la actualización de volúmenes y la recarga de la aplicación son procesos independientes.

</details>

<span id="_5-which-aws-service-is-used-to-configure-automatic-rotation-in-aws-secrets-manager"></span>

### 5. ¿Qué servicio de AWS ejecuta una función Lambda personalizada para rotar Secrets Manager?

A. AWS EventBridge
B. AWS Lambda
C. AWS Step Functions
D. AWS SNS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. AWS Lambda**

**Explicación:**
Un flujo de rotación personalizado basado en Lambda usa una función Lambda con lógica para actualizar el destino, permisos y acceso a la red. Secrets Manager también ofrece integraciones de rotación administrada, por lo que no toda rotación requiere que un operador gestione una función Lambda. ESO sincroniza valores, pero no rota por sí mismo la credencial de la base de datos.

</details>

### 6. ¿Cuál es la función principal de Sealed Secrets?

A. Cifrar datos en etcd
B. Permitir almacenar Secrets de forma segura en Git
C. Funcionar solo con AWS
D. Admitir la rotación automática

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Permitir almacenar Secrets de forma segura en Git**

**Explicación:**
Sealed Secrets cifra los valores para almacenarlos en Git usando un certificado de confianza. Cualquiera que tenga una clave privada adecuada, incluidos los operadores de recuperación autorizados, puede descifrarlos. Los metadatos siguen visibles; renovar la clave no rota la credencial de la aplicación ni borra del historial de Git el texto cifrado antiguo.

</details>

### 7. ¿Qué función cumple el campo refreshInterval de ExternalSecret?

A. Establecer la fecha de vencimiento del Secret
B. Establecer el intervalo de sincronización con el Secret externo
C. Establecer el tiempo de retención de la caché
D. Establecer el intervalo de reintento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Establecer el intervalo de sincronización con el Secret externo**

**Explicación:**
Con `refreshPolicy` Periodic y un `refreshInterval` positivo, ESO reconcilia periódicamente los valores externos. No garantiza que la operación termine dentro de un plazo determinado y su comportamiento difiere de OnChange y CreatedOnce. También hay que gestionar los errores del proveedor, la espera entre reintentos y la recarga de la aplicación.

</details>

### 8. ¿Qué ocurre cuando el campo immutable de un Secret de Kubernetes se establece en true?

A. El Secret no se puede eliminar
B. Los datos del Secret no se pueden modificar
C. El Secret no se puede leer
D. El Secret no se puede copiar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Los datos del Secret no se pueden modificar**

**Explicación:**
La inmutabilidad impide cambiar los datos del Secret y no se puede revertir para volverlo mutable. Los metadatos sí pueden cambiar y el Secret aún se puede eliminar. Para reemplazar una dependencia activa, es preferible crear un Secret con otro nombre y hacer un despliegue controlado.

</details>

### 9. ¿Cuál es la función principal de Secrets Store CSI Driver?

A. Cifrar Secrets en etcd
B. Montar Secrets externos como volúmenes
C. Generar Secrets automáticamente
D. Hacer copias de seguridad de Secrets

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Montar Secrets externos como volúmenes**

**Explicación:**
Secrets Store CSI Driver y un proveedor compatible montan valores externos como archivos. La sincronización con un Secret de Kubernetes es opcional y requiere la función de sincronización y un montaje que lo consuma. La rotación, la propagación de archivos y la recarga de la aplicación son aspectos independientes; la compatibilidad depende de la plataforma.

</details>

### 10. ¿Qué ventaja tiene usar External Secrets con IRSA (IAM Roles for Service Accounts)?

A. Acceder más rápido a los Secrets
B. No tener que codificar credenciales de IAM en los Pods
C. Rotar Secrets automáticamente
D. Usarlo sin costo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. No tener que codificar credenciales de IAM en los Pods**

**Explicación:**
IRSA intercambia un token de identidad proyectado por credenciales temporales de AWS mediante un enlace de confianza exacto para el rol. Evita las claves de acceso de larga duración codificadas en el Pod; no elimina las credenciales. La integración de ESO con Pod Identity usa la identidad del controlador; no sustituye la suplantación de identidad indicada con `serviceAccountRef`.

</details>

### 11. ¿Qué característica tiene definir datos de un Secret mediante stringData?

A. Se cifra
B. No se requiere codificación Base64
C. Es más seguro
D. Se comprime

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. No se requiere codificación Base64**

**Explicación:**
stringData acepta texto sin cifrar como entrada, sin necesidad de convertirlo manualmente a Base64, y luego lo combina con data. No es cifrado ni añade protección de acceso; las lecturas de la API exponen la representación de los datos a los usuarios autorizados. Evita incluir valores reales en YAML con seguimiento de Git y ten en cuenta las limitaciones de server-side apply.

</details>

### 12. ¿Cuál de estas NO es una práctica recomendada para gestionar Secrets?

A. Habilitar el cifrado de etcd
B. Restringir con RBAC el acceso a los Secrets
C. Confirmar credenciales en texto sin cifrar en el código fuente
D. Usar un sistema externo de gestión de Secrets

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Confirmar credenciales en texto sin cifrar en el código fuente**

**Explicación:**
Nunca confirmes credenciales en texto sin cifrar ni claves privadas para descifrar. Los artefactos cifrados de SOPS/SealedSecret y las referencias de ESO sin valores se pueden almacenar en Git si se revisan los destinatarios y se protegen las claves, se prueban los procedimientos de recuperación y se controlan los accesos. Ninguna herramienta garantiza por sí sola la seguridad o el cumplimiento.

</details>

---

[Guía de gestión de Secrets](../../security/05-secrets-management.md)

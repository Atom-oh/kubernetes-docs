# Cuestionario sobre gestión de Secrets

Este cuestionario evalúa tu comprensión de Kubernetes Secrets, AWS Secrets Manager, External Secrets Operator y el cifrado.

## Preguntas del cuestionario

### 1. ¿Cuál es el método de codificación predeterminado para Kubernetes Secrets?

A. Cifrado AES-256
B. Codificación Base64
C. Hash SHA-256
D. Cifrado RSA

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Codificación Base64**

**Explicación:**
Kubernetes Secrets se codifican en Base64 de forma predeterminada. Base64 es una codificación simple, no cifrado, por lo que debes habilitar el cifrado de etcd o usar un sistema externo de gestión de secrets.

</details>

### 2. ¿Qué servicio de AWS se usa para el cifrado de etcd en EKS?

A. AWS Secrets Manager
B. AWS KMS (Key Management Service)
C. AWS Certificate Manager
D. AWS CloudHSM

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. AWS KMS (Key Management Service)**

**Explicación:**
EKS usa AWS KMS para cifrar Kubernetes Secrets almacenados en etcd. El cifrado de sobre se puede habilitar durante la creación del cluster o después:
```bash
aws eks associate-encryption-config \
  --cluster-name my-cluster \
  --encryption-config '[{"resources":["secrets"],"provider":{"keyArn":"arn:aws:kms:..."}}]'
```

</details>

### 3. ¿Qué recursos referencian secrets de AWS Secrets Manager en External Secrets Operator?

A. SecretStore
B. ExternalSecret
C. ClusterSecretStore
D. A y B o C y B

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. A y B o C y B**

**Explicación:**
Componentes de External Secrets Operator:
- **SecretStore/ClusterSecretStore**: Configuración de conexión al almacén externo de secrets
- **ExternalSecret**: Referencia real al secret y creación de Kubernetes Secret

SecretStore tiene alcance de namespace, ClusterSecretStore tiene alcance de cluster.

</details>

### 4. ¿Cuál NO es una forma de usar Secrets en un Pod?

A. Inyectarlos como variables de entorno
B. Montarlos como volúmenes
C. Image pull secrets
D. Convertirlos en ConfigMap

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Convertirlos en ConfigMap**

**Explicación:**
Formas de usar Secrets en un Pod:
1. **Variables de entorno**: `envFrom.secretRef` o `env.valueFrom.secretKeyRef`
2. **Montaje de volumen**: Montarlos como archivos
3. **Image pull secrets**: `imagePullSecrets`

Secrets no se convierten automáticamente en ConfigMaps. Son recursos separados.

</details>

### 5. ¿Qué servicio de AWS se usa para configurar la rotación automática en AWS Secrets Manager?

A. AWS EventBridge
B. AWS Lambda
C. AWS Step Functions
D. AWS SNS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. AWS Lambda**

**Explicación:**
La rotación automática de AWS Secrets Manager usa funciones Lambda. AWS proporciona funciones de rotación preconstruidas para RDS, Redshift, etc., y la rotación personalizada se puede implementar con Lambda.

</details>

### 6. ¿Cuál es la característica principal de Sealed Secrets?

A. Cifrado en etcd
B. Seguro para almacenar en Git
C. Solo AWS
D. Compatibilidad con rotación automática

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Seguro para almacenar en Git**

**Explicación:**
Sealed Secrets cifra secrets con una clave pública para que puedan almacenarse de forma segura en repositorios Git. Solo el controlador de Sealed Secrets en el cluster puede descifrarlos con la clave privada. Es adecuado para flujos de trabajo GitOps.

</details>

### 7. ¿Cuál es la función del campo refreshInterval de ExternalSecret?

A. Establecer el tiempo de expiración del secret
B. Establecer el intervalo de sincronización con el secret externo
C. Establecer el tiempo de retención de caché
D. Establecer el intervalo de reintento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Establecer el intervalo de sincronización con el secret externo**

**Explicación:**
`refreshInterval` define con qué frecuencia External Secrets Operator se sincroniza con el almacén externo de secrets:
```yaml
spec:
  refreshInterval: 1h  # Sync every 1 hour
```

Cuando los secrets cambian externamente, Kubernetes Secret se actualiza según este intervalo.

</details>

### 8. ¿Qué sucede cuando el campo immutable de Kubernetes Secret se establece en true?

A. Secret no se puede eliminar
B. Secret no se puede modificar
C. Secret no se puede leer
D. Secret no se puede copiar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Secret no se puede modificar**

**Explicación:**
La configuración `immutable: true` impide modificaciones después de crear el Secret:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
immutable: true
data:
  password: cGFzc3dvcmQ=
```

Para cambiarlo, debes eliminar y volver a crear el Secret. Esto evita cambios accidentales y mejora el rendimiento.

</details>

### 9. ¿Cuál es la función principal de CSI Secrets Store Driver?

A. Cifrar secrets en etcd
B. Montar secrets externos como volúmenes
C. Generar secrets automáticamente
D. Hacer copias de seguridad de secrets

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Montar secrets externos como volúmenes**

**Explicación:**
Secrets Store CSI Driver monta secrets externos desde AWS Secrets Manager, Azure Key Vault, etc. directamente como volúmenes CSI. Los Pods pueden usar secrets sin crear Kubernetes Secrets.

</details>

### 10. ¿Cuál es la ventaja de usar External Secrets con IRSA (IAM Roles for Service Accounts)?

A. Acceso más rápido a secrets
B. No es necesario codificar credenciales de IAM de forma fija en Pods
C. Rotación automática de secrets
D. Uso gratuito

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. No es necesario codificar credenciales de IAM de forma fija en Pods**

**Explicación:**
IRSA permite asociar roles de IAM a Service Accounts. Los Pods de External Secrets Operator pueden acceder de forma segura a AWS Secrets Manager sin credenciales de AWS. Esta es una práctica recomendada de seguridad.

</details>

### 11. ¿Cuál es la característica de definir datos de Secret con stringData?

A. Cifrados
B. No se requiere codificación Base64
C. Más seguro
D. Comprimido

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. No se requiere codificación Base64**

**Explicación:**
El campo `stringData` permite especificar valores en texto plano:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
stringData:
  password: mypassword  # Plain text, auto Base64 encoded
```

Kubernetes gestiona automáticamente la codificación Base64. Sin embargo, cuando se consulta, aparece como Base64 en el campo data.

</details>

### 12. ¿Cuál NO es una práctica recomendada de gestión de secrets?

A. Habilitar el cifrado de etcd
B. Restringir el acceso a Secret con RBAC
C. Confirmar secrets en el código fuente
D. Usar un sistema externo de gestión de secrets

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Confirmar secrets en el código fuente**

**Explicación:**
Prácticas recomendadas de gestión de secrets:
- Habilitar el cifrado de etcd
- Restringir el acceso a Secret con RBAC
- Usar sistemas externos de gestión de secrets (AWS Secrets Manager, HashiCorp Vault, etc.)
- Habilitar el registro de auditoría
- Rotación regular de secrets

Nunca confirmes secrets en el código fuente. Los secrets en texto plano quedarían expuestos en los sistemas de control de versiones.

</details>

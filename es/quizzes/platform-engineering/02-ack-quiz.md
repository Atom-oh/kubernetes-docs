# Cuestionario sobre AWS Controllers for Kubernetes (ACK)

Este cuestionario evalúa tu comprensión de los conceptos, la arquitectura, la instalación, la seguridad y las operaciones de AWS Controllers for Kubernetes (ACK).

## Preguntas de opción múltiple

1. ¿Cuál es el propósito principal de ACK (AWS Controllers for Kubernetes)?
   - A) Administrar recursos de AWS solo mediante la consola de AWS
   - B) Administrar recursos de AWS de forma declarativa mediante la API de Kubernetes
   - C) Ejecutar clusters de Kubernetes solo en AWS
   - D) Reducir automáticamente los costos de AWS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Administrar recursos de AWS de forma declarativa mediante la API de Kubernetes**

**Explicación:**
ACK es un proyecto que permite a los usuarios de Kubernetes administrar servicios y recursos de AWS directamente usando API y herramientas familiares de Kubernetes (kubectl, Helm, etc.). Esto permite la integración con flujos de trabajo GitOps y la administración de infraestructura de AWS como código mediante configuración declarativa.
</details>

2. En la arquitectura de ACK, ¿qué componente se instala de forma individual para cada servicio de AWS?
   - A) Kubernetes API Server
   - B) Service controller
   - C) Base de datos etcd
   - D) kubelet

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Service controller**

**Explicación:**
ACK proporciona service controllers separados para cada servicio de AWS (S3, RDS, DynamoDB, etc.). Por ejemplo, para administrar buckets de S3 instalas el S3 controller, y para administrar bases de datos RDS instalas el RDS controller. Este enfoque modular te permite instalar controllers solo para los servicios que necesitas.
</details>

3. ¿Cuál es el método recomendado para configurar permisos de IAM para que los ACK controllers administren recursos de AWS?
   - A) Usar solo perfiles de instancia EC2
   - B) Almacenar claves de acceso de AWS en ConfigMap
   - C) Usar IRSA (IAM Roles for Service Accounts)
   - D) Usar la cuenta root con todos los permisos de AWS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Usar IRSA (IAM Roles for Service Accounts)**

**Explicación:**
IRSA (IAM Roles for Service Accounts) es el método recomendado para conceder permisos de administración de recursos de AWS a los ACK controllers asociando roles de IAM con service accounts de Kubernetes. Este enfoque sigue el principio de privilegio mínimo, permite una administración segura de credenciales y permite conceder solo los permisos necesarios a cada controller.
</details>

4. ¿Qué anotación debes usar en ACK para conservar el recurso de AWS al eliminar el recurso de Kubernetes?
   - A) services.k8s.aws/keep-resource: "true"
   - B) services.k8s.aws/deletion-policy: "orphan"
   - C) services.k8s.aws/preserve: "true"
   - D) services.k8s.aws/no-delete: "true"

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) services.k8s.aws/deletion-policy: "orphan"**

**Explicación:**
De forma predeterminada, ACK elimina el recurso de AWS correspondiente cuando se elimina el recurso de Kubernetes. Sin embargo, configurar la anotación `services.k8s.aws/deletion-policy: "orphan"` conserva el recurso de AWS incluso cuando se elimina el recurso de Kubernetes. Esto es útil para evitar la eliminación accidental de recursos importantes en entornos de producción.
</details>

5. ¿Cómo importas recursos de AWS existentes a Kubernetes usando ACK?
   - A) Usar el comando kubectl import
   - B) Usar la funcionalidad de exportación desde la consola de AWS
   - C) Agregar la anotación services.k8s.aws/resource-imported: "true" al manifest del recurso
   - D) Usar el comando ACK CLI import

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Agregar la anotación services.k8s.aws/resource-imported: "true" al manifest del recurso**

**Explicación:**
Para importar recursos de AWS existentes en ACK, crea el manifest del recurso y agrega la anotación `services.k8s.aws/resource-imported: "true"`. Esto hace que el ACK controller se conecte al recurso de AWS existente en lugar de crear uno nuevo. Esto permite una migración gradual de la infraestructura existente a flujos de trabajo GitOps.
</details>

6. ¿Qué nivel de madurez de los ACK service controllers es adecuado para uso en producción?
   - A) Alpha
   - B) Beta
   - C) GA (Generally Available)
   - D) Preview

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) GA (Generally Available)**

**Explicación:**
Los ACK service controllers pasan por tres niveles de madurez: Alpha, Beta y GA. Alpha es la etapa temprana de desarrollo en la que pueden producirse cambios en la API; Beta significa que la funcionalidad está completa, pero aún son posibles cambios en la API. GA (Generally Available) es la etapa lista para uso en producción, con API estables y funcionalidad completa.
</details>

7. ¿Qué tipo de Condition indica que un recurso de ACK se ha sincronizado correctamente?
   - A) ACK.Ready
   - B) ACK.ResourceSynced
   - C) ACK.Healthy
   - D) ACK.Available

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) ACK.ResourceSynced**

**Explicación:**
El estado de un recurso de ACK se puede comprobar en el campo `status.conditions`. Cuando la Condition `ACK.ResourceSynced` es True, significa que el estado deseado (spec) del recurso de Kubernetes se ha sincronizado correctamente con el estado real del recurso de AWS. Esto te permite verificar si el recurso se creó o actualizó correctamente.
</details>

8. ¿Cuál es el método recomendado para aislar permisos para varios equipos o entornos en ACK?
   - A) Administrar todos los entornos con un solo controller
   - B) Aislamiento usando namespaces y roles de IAM separados
   - C) Usar solo AWS Organizations
   - D) Usar solo aislamiento de VPC

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Aislamiento usando namespaces y roles de IAM separados**

**Explicación:**
Para aislar permisos para varios equipos o entornos (desarrollo, staging, producción) en ACK, se recomienda usar namespaces de Kubernetes y roles de IAM separados para cada uno. Instala controllers separados para cada namespace y asocia roles con políticas de IAM adecuadas para ese entorno. Además, Kubernetes RBAC puede usarse para controlar el acceso de los usuarios a los recursos de ACK.
</details>

## Preguntas de respuesta corta

9. ¿Cómo se llama el patrón en el que los ACK controllers llaman a las API de AWS para crear, actualizar y eliminar recursos mientras detectan y resuelven diferencias entre los estados deseado y real?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Reconciliation Loop o Reconciliation Pattern**

**Explicación:**
El reconciliation loop es un patrón central de los controllers de Kubernetes, y ACK también se basa en este patrón. Los ACK controllers comparan continuamente el estado deseado (spec) de los recursos de Kubernetes con el estado real de los recursos de AWS. Cuando se detectan diferencias, el controller llama a las API de AWS para hacer coincidir el estado real con el estado deseado. Este proceso se repite automáticamente para detectar y corregir desviaciones.
</details>

10. ¿Qué mecanismo de extensión de Kubernetes usa ACK para definir recursos de AWS mediante la API de Kubernetes?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: CRD (Custom Resource Definition)**

**Explicación:**
ACK usa CRD (Custom Resource Definition) para definir recursos de AWS mediante la API de Kubernetes. Por ejemplo, cuando instalas el S3 controller, se crean CRDs como `Bucket` y `BucketPolicy`, lo que te permite administrar buckets de S3 como recursos de Kubernetes. Cada service controller proporciona CRDs para los recursos del servicio de AWS correspondiente.
</details>

11. Al comprobar el estado de un recurso de ACK, ¿en qué campo puedes encontrar el ARN (Amazon Resource Name) del recurso de AWS?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: status.ackResourceMetadata.arn**

**Explicación:**
Cuando un recurso de ACK se crea correctamente, el ARN del recurso de AWS correspondiente se almacena en el campo `status.ackResourceMetadata.arn`. Puedes ver esta información al comprobar el estado del recurso con el comando `kubectl describe`. También puedes comprobar el ID de cuenta de AWS que posee el recurso en el campo `status.ackResourceMetadata.ownerAccountID`.
</details>

12. ¿Cómo se llama la funcionalidad que permite referenciar el mismo recurso de AWS desde varios clusters o administrar recursos en diferentes cuentas de AWS en ACK?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Cross-Account Resource Management o Multi-Cluster Support**

**Explicación:**
ACK proporciona funcionalidad para referenciar el mismo recurso de AWS desde varios clusters de Kubernetes o administrar recursos en diferentes cuentas de AWS. Para hacerlo, configura encadenamiento de roles de IAM o políticas de IAM entre cuentas para que los ACK controllers puedan acceder a recursos en otras cuentas. Esta funcionalidad permite la administración centralizada de recursos en entornos multi-cluster o multi-account.
</details>

## Preguntas prácticas

13. Escribe un manifest de Kubernetes para crear un bucket de S3 usando ACK. El nombre del bucket es "my-ack-demo-bucket-2025" y agrega el tag Environment: Development.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: my-ack-demo-bucket
  namespace: default
spec:
  name: my-ack-demo-bucket-2025
  tagging:
    tagSet:
      - key: Environment
        value: Development
  createBucketConfiguration:
    locationConstraint: us-west-2
```

**Explicación:**
Este es un manifest para crear un bucket de S3 usando el ACK S3 controller. `metadata.name` es el nombre del recurso de Kubernetes, y `spec.name` es el nombre real del bucket de AWS S3. Dado que los nombres de bucket deben ser únicos globalmente, usa un nombre único en el uso real. Los tags de recursos de AWS pueden configurarse mediante `tagging.tagSet`, y `createBucketConfiguration.locationConstraint` especifica la región donde se creará el bucket.
</details>

14. Escribe comandos para instalar el ACK S3 controller usando Helm y configurar IRSA. Usa el nombre de cluster "my-eks-cluster" y el namespace "ack-system".

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
# 1. Add Helm chart repository
helm repo add aws-controllers-k8s https://aws.github.io/eks-charts
helm repo update

# 2. Create IAM service account for IRSA
eksctl create iamserviceaccount \
  --cluster=my-eks-cluster \
  --namespace=ack-system \
  --name=ack-s3-controller \
  --attach-policy-arn=arn:aws:iam::aws:policy/AmazonS3FullAccess \
  --approve \
  --override-existing-serviceaccounts

# 3. Install S3 controller
helm install ack-s3-controller \
  aws-controllers-k8s/s3-chart \
  --namespace ack-system \
  --create-namespace \
  --set serviceAccount.create=false \
  --set serviceAccount.name=ack-s3-controller \
  --set aws.region=us-west-2
```

**Explicación:**
Primero, agrega el repositorio de charts de ACK Helm. Luego usa eksctl para crear una IAM service account para la configuración de IRSA. La política de IAM necesaria para la administración de S3 se adjunta a esta service account. Finalmente, instala el S3 controller usando Helm, configurado para usar la service account ya creada. Para entornos de producción, es mejor usar una política personalizada con privilegio mínimo en lugar de AmazonS3FullAccess.
</details>

15. Escribe comandos para revisar los logs del controller e inspeccionar el estado de los recursos para solucionar problemas en recursos creados por ACK.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
# 1. Check ACK controller logs
kubectl logs -n ack-system -l app.kubernetes.io/name=ack-s3-controller

# 2. Check specific resource status and events
kubectl describe bucket my-ack-demo-bucket

# 3. Check detailed resource status (JSON format)
kubectl get bucket my-ack-demo-bucket -o json | jq '.status'

# 4. Check resource-related events
kubectl get events --field-selector involvedObject.name=my-ack-demo-bucket

# 5. Check CRD installation status
kubectl get crd | grep services.k8s.aws

# 6. Check controller deployment status
kubectl get deployment -n ack-system
```

**Explicación:**
Al solucionar problemas de creación de recursos de ACK, revisa varios aspectos. Primero, revisa los logs del controller para identificar errores de llamadas a la API de AWS o problemas de permisos. Usa `kubectl describe` para comprobar el estado del recurso y las Conditions, y rastrea cambios recientes mediante eventos. También verifica que las CRDs estén instaladas correctamente y que los pods del controller se estén ejecutando normalmente. Los problemas comunes incluyen permisos de IAM insuficientes, configuración de región incorrecta y conflictos de nombres de recursos.
</details>

---

**Puntuación:**
- 13-15 correctas: Excelente (nivel experto en ACK)
- 10-12 correctas: Bueno (capaz de aplicación práctica)
- 7-9 correctas: Promedio (se recomienda aprendizaje adicional)
- 0-6 correctas: Insuficiente (se necesita revisar los conceptos básicos)

[Volver a los materiales de aprendizaje](../../platform-engineering/02-ack.md)

# Cuestionario de AWS Controllers for Kubernetes (ACK)

[ACK](../../platform-engineering/02-ack.md)

Estas preguntas conservan los 15 temas originales utilizando el comportamiento revisado del controlador.

## 1. ¿Cuál es el propósito principal de ACK?

<details>
<summary>Mostrar respuesta</summary>

Gestionar de forma declarativa los recursos de AWS a través de las APIs de Kubernetes y de recursos personalizados (custom resources). No garantiza ahorros de costos automáticos ni disponibilidad inmediata.

</details>

## 2. ¿Qué componente se instala para cada servicio?

<details>
<summary>Mostrar respuesta</summary>

Un controlador de servicio, con sus CRDs. Seleccione los servicios necesarios e inspeccione los recursos y campos compatibles en las CRDs versionadas.

</details>

## 3. ¿Cómo deben recibir los controladores las credenciales de AWS?

<details>
<summary>Mostrar respuesta</summary>

Configure una identidad de carga de trabajo (workload identity) como IRSA o EKS Pod Identity compatible. Verifique la confianza/asociación de OIDC, el ServiceAccount, la compatibilidad del SDK/agente y los permisos IAM mínimos. No almacene claves de acceso en ConfigMaps ni utilice credenciales de root.

</details>

## 4. ¿Qué valor conserva los recursos de AWS después de eliminar el CR?

<details>
<summary>Mostrar respuesta</summary>

`services.k8s.aws/deletion-policy: retain`. El runtime actual no acepta orphan. La precedencia es el CR, la anotación específica del servicio en el namespace y, después, el valor predeterminado del controlador. Los recursos de AWS conservados siguen requiriendo propiedad y operación.

</details>

## 5. ¿Cómo se adoptan los recursos existentes?

<details>
<summary>Mostrar respuesta</summary>

Utilice `adoption-policy: adopt` de ResourceAdoption y los adoption-fields específicos del servicio, verificando las condiciones de habilitación (gates), los identificadores, la región y la cuenta. resource-imported:true no es esta configuración; adopt-or-create puede crear un recurso inexistente. La reconciliación posterior puede modificar los recursos, así que distinga la adopción del comportamiento de solo lectura.

</details>

## 6. ¿Qué establece el estado GA?

<details>
<summary>Mostrar respuesta</summary>

Identifica la etapa oficial de madurez del controlador, no la compatibilidad con todas las APIs de AWS ni con todos los requisitos operativos. Distinga la madurez de la cadena v1alpha1 de una CRD y verifique los campos, las versiones publicadas y la idoneidad operativa.

</details>

## 7. ¿Qué condición indica sincronización y cuáles son sus límites?

<details>
<summary>Mostrar respuesta</summary>

ACK.ResourceSynced=True describe la sincronización del controlador. No es prueba de que la aplicación esté lista, de la conectividad con la base de datos ni de la entrega de mensajes. Inspeccione otras condiciones y el estado del servicio de AWS.

</details>

## 8. ¿Separar los namespaces de los equipos completa el aislamiento?

<details>
<summary>Mostrar respuesta</summary>

No. El valor predeterminado installScope=cluster observa los CRs en todos los namespaces. Restrinja conjuntamente watchNamespace/installScope, el ServiceAccount/IAM/RBAC y el comportamiento entre namespaces y de CARM. El modo namespace todavía puede tener permisos de lectura a nivel de clúster para la caché de su namespace.

</details>

## 9. ¿Qué patrón alinea el estado deseado y el estado observado en AWS?

<details>
<summary>Mostrar respuesta</summary>

El bucle de reconciliación procesa repetidamente los campos compatibles y la lógica del controlador. Los errores transitorios y las cuotas de AWS lo afectan; no repara de inmediato toda posible desviación (drift).

</details>

## 10. ¿Qué extensión de Kubernetes define las entradas de los recursos?

<details>
<summary>Mostrar respuesta</summary>

Las CRDs. El ejemplo de S3 usa Bucket.spec.policy. Las versiones revisadas no tienen CRDs separadas de BucketPolicy ni de RolePolicyAttachment de IAM; verifique los kinds y esquemas reales.

</details>

## 11. ¿Dónde se puede encontrar el ARN?

<details>
<summary>Mostrar respuesta</summary>

Cuando se proporciona para el recurso, utilice status.ackResourceMetadata.arn, incluidos NLB y TargetGroup. Los campos de status adicionales varían según el recurso.

</details>

## 12. ¿En qué se diferencia CARM de las referencias entre clústeres?

<details>
<summary>Mostrar respuesta</summary>

CARM configura un controlador para gestionar otra cuenta de AWS mediante la asunción de un rol de destino, lo que requiere confianza, permisos de AssumeRole, mapeos y ajustes del controlador. No hace que sea seguro que varios clústeres realicen mutaciones en competencia. Separe la propiedad de las mutaciones de las referencias de solo lectura.

</details>

## 13. ¿Qué debe incluir un ejemplo de S3 Bucket etiquetado como Development?

<details>
<summary>Mostrar respuesta</summary>

Utilice un nombre globalmente único, la región real, tagging.tagSet, los cuatro ajustes de Block Public Access y cifrado. El principal/IAM Role debe existir antes de aplicar la política del bucket. Reemplace los nombres e IDs de cuenta de ejemplo.

```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: app-data
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  name: replace-with-globally-unique-bucket-name
  createBucketConfiguration:
    locationConstraint: us-west-2
  publicAccessBlock:
    blockPublicACLs: true
    blockPublicPolicy: true
    ignorePublicACLs: true
    restrictPublicBuckets: true
  encryption:
    rules:
    - applyServerSideEncryptionByDefault:
        sseAlgorithm: AES256
  tagging:
    tagSet:
    - key: Environment
      value: Development
  policy: "{\n  \"Version\": \"2012-10-17\",\n  \"Statement\": [\n    {\n      \"\
    Effect\": \"Allow\",\n      \"Principal\": {\n        \"AWS\": \"arn:aws:iam::123456789012:role/MyApplicationRole\"\
    \n      },\n      \"Action\": \"s3:GetObject\",\n      \"Resource\": \"arn:aws:s3:::replace-with-globally-unique-bucket-name/*\"\
    \n    }\n  ]\n}"
```

</details>

## 14. ¿Cómo se inspecciona el chart de ACK para S3 y qué precede a la instalación?

<details>
<summary>Mostrar respuesta</summary>

El comando renderiza sin conexión un chart OCI con versión fijada. Prepare infra, su ServiceAccount, IRSA/Pod Identity y los permisos IAM antes de una instalación/actualización real. El renderizado no es una verificación del despliegue en AWS.

```bash
helm template ack-s3 \
  oci://public.ecr.aws/aws-controllers-k8s/s3-chart \
  --version 1.12.1 --namespace infra \
  --set aws.region=us-west-2 \
  --set installScope=namespace --set watchNamespace=infra \
  --set enableCARM=false --set enableCrossNamespace=false \
  --set serviceAccount.create=false \
  --set serviceAccount.name=ack-s3-controller \
  --set metrics.service.create=true --set deletionPolicy=retain
```

</details>

## 15. ¿Qué estado y qué logs se deben inspeccionar?

<details>
<summary>Mostrar respuesta</summary>

Especifique el namespace y los kinds completamente cualificados; inspeccione las condiciones/eventos, la imagen y los logs del controlador, la cuenta/región/permisos reales y las referencias. La etiqueta del chart es app.kubernetes.io/instance=ack-s3. Eliminar los finalizers no es una solución rutinaria.

```bash
kubectl get buckets.s3.services.k8s.aws -n infra
kubectl get bucket.s3.services.k8s.aws app-data -n infra -o json
kubectl describe bucket.s3.services.k8s.aws app-data -n infra
kubectl logs -n infra \
  -l app.kubernetes.io/instance=ack-s3 --all-containers --tail=100
kubectl get events -n infra \
  --field-selector involvedObject.name=app-data
```

</details>
